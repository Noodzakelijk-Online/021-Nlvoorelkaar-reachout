import json
import sqlite3
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from config.runtime import RuntimeSettings
from database.database_manager import DatabaseManager
from google_drive.google_api_services import GoogleDriveManager, SCOPES
from services.data_management import DataImporter
from services.diagnostics import SupportBundleBuilder, verify_local_critical_path
from services.enhanced_scraper import EnhancedScraper, ScrapingConfig
from services.outreach_ledger import OutreachLedger
from services.provider_policy import TERMS_URL, TERMS_VERSION, validate_provider_authorization
from utils.backup_manager import BackupManager


def create_approved_draft(tmp_path: Path):
    database = DatabaseManager(str(tmp_path / "data" / "app.db"))
    assert database.add_volunteer({
        "volunteer_id": "v-1",
        "name": "Ada",
        "location": "Arnhem",
        "categories": "maatjes",
        "skills": "luisteren",
    })
    campaign_id = database.add_campaign({
        "name": "Campaign",
        "target_categories": "maatjes",
        "target_location": "Arnhem",
        "message_template": "Beste {name}",
    })
    ledger = OutreachLedger(database)
    draft_id = ledger.create_message_drafts(campaign_id)[0]
    ledger.approve_message(draft_id, "test approval", actor="test")
    return database, ledger, campaign_id, draft_id


def test_runtime_defaults_fail_closed(monkeypatch):
    for name in (
        "NLVE_LIVE_SEARCH_ENABLED",
        "NLVE_LIVE_SEND_ENABLED",
        "NLVE_GOOGLE_DRIVE_ENABLED",
        "NLVE_PROVIDER_APPROVAL_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = RuntimeSettings.from_environment()
    assert settings.live_search_enabled is False
    assert settings.live_send_enabled is False
    assert settings.google_drive_enabled is False


def _write_provider_approval(path: Path, actions=("login", "search", "send")) -> None:
    today = date.today()
    path.write_text(json.dumps({
        "schema_version": 1,
        "provider": "nlvoorelkaar",
        "authorization_type": "written_platform_approval",
        "approved_by": "NLvoorelkaar test approver",
        "approval_reference": "TEST-123",
        "evidence_sha256": "a" * 64,
        "approved_actions": list(actions),
        "terms_url": TERMS_URL,
        "terms_version": TERMS_VERSION,
        "terms_checked_at": today.isoformat(),
        "expires_at": (today + timedelta(days=30)).isoformat(),
        "acknowledgements": {
            "personal_account_only": True,
            "intended_use_only": True,
            "no_credential_sharing": True,
            "bounded_rate_limits": True,
            "personal_data_protected": True,
        },
    }), encoding="utf-8")


def test_live_provider_flags_require_current_written_approval(monkeypatch, tmp_path):
    monkeypatch.setenv("NLVE_ENV", "production")
    monkeypatch.setenv("NLVE_LIVE_SEARCH_ENABLED", "1")
    monkeypatch.delenv("NLVE_PROVIDER_APPROVAL_PATH", raising=False)
    with pytest.raises(ValueError, match="PROVIDER_APPROVAL_PATH"):
        RuntimeSettings.from_environment()

    approval = tmp_path / "provider-approval.json"
    _write_provider_approval(approval, actions=("login", "search"))
    monkeypatch.setenv("NLVE_PROVIDER_APPROVAL_PATH", str(approval))
    settings = RuntimeSettings.from_environment()
    assert settings.provider_authorization_status()["ready"] is True


def test_provider_approval_rejects_stale_terms_review(tmp_path):
    approval = tmp_path / "provider-approval.json"
    _write_provider_approval(approval)
    payload = json.loads(approval.read_text(encoding="utf-8"))
    payload["terms_checked_at"] = (date.today() - timedelta(days=31)).isoformat()
    approval.write_text(json.dumps(payload), encoding="utf-8")
    status = validate_provider_authorization(str(approval), {"login", "send"})
    assert status.ready is False
    assert any("older than 30 days" in error for error in status.errors)


def test_test_environment_rejects_external_features(monkeypatch):
    monkeypatch.setenv("NLVE_ENV", "test")
    monkeypatch.setenv("NLVE_LIVE_SEND_ENABLED", "1")
    with pytest.raises(ValueError, match="cannot be enabled"):
        RuntimeSettings.from_environment()


def test_scraper_rejects_cross_origin_requests():
    scraper = EnhancedScraper(ScrapingConfig(min_delay=1, max_delay=1))
    with pytest.raises(ValueError, match="outside"):
        scraper._validate_provider_url("https://example.org/steal")


def test_scraper_supports_bounded_single_page_search(monkeypatch):
    scraper = EnhancedScraper(ScrapingConfig(min_delay=1, max_delay=1))

    class Response:
        text = '<article class="volunteer-card"><a href="/vrijwilliger/123"><h2>Ada</h2></a></article>'

    monkeypatch.setattr(scraper, "_make_request", lambda _url: Response())
    results = scraper.search_volunteers_page({"location": "Arnhem"}, 1)
    assert results[0]["volunteer_id"] == "123"
    with pytest.raises(ValueError, match="between 1 and 20"):
        scraper.search_volunteers_page({}, 21)


def test_current_schema_candidate_import(tmp_path):
    database = DatabaseManager(str(tmp_path / "data" / "app.db"))
    source = tmp_path / "candidates.csv"
    source.write_text(
        "volunteer_id,name,location,categories\nv-1,Ada,Arnhem,maatjes\n",
        encoding="utf-8",
    )
    stats = DataImporter(database.db_path).import_volunteers(str(source))
    assert stats == {"imported": 1, "updated": 0, "skipped": 0, "errors": 0}
    assert database.get_volunteers()[0]["volunteer_id"] == "v-1"
    assert database.get_audit_events(limit=1)[0]["action"] == "volunteers_imported"


def test_large_volunteer_dataset_uses_database_pagination(tmp_path):
    database = DatabaseManager(str(tmp_path / "data" / "large.db"))
    with sqlite3.connect(database.db_path) as conn:
        conn.executemany(
            """
            INSERT INTO volunteers (volunteer_id, name, location, categories, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                (f"v-{index:05d}", f"Volunteer {index}", "Arnhem", "maatjes", f"2026-01-{(index % 28) + 1:02d}")
                for index in range(10000)
            ),
        )
    started = time.monotonic()
    page = database.get_volunteers({"location": "Arnhem"}, limit=100, offset=4900)
    elapsed = time.monotonic() - started
    assert len(page) == 100
    assert len({row["volunteer_id"] for row in page}) == 100
    assert elapsed < 2.0
    with pytest.raises(ValueError, match="limit"):
        database.get_volunteers(limit=5001)


def test_send_claim_is_atomic_and_blocks_duplicate_attempt(tmp_path):
    database, _, _, draft_id = create_approved_draft(tmp_path)
    first_attempt = database.record_send_attempt(draft_id, status="started")
    assert first_attempt
    with pytest.raises(ValueError, match="already being sent"):
        database.record_send_attempt(draft_id, status="started")


def test_sent_draft_cannot_be_reapproved(tmp_path):
    database, ledger, _, draft_id = create_approved_draft(tmp_path)
    ledger.confirm_manual_send(draft_id, "manual test evidence", actor="test")
    with pytest.raises(ValueError, match="Only draft"):
        ledger.approve_message(draft_id, "approve again", actor="test")


def test_ambiguous_send_reconciliation_requires_human_review(tmp_path):
    database, _, _, draft_id = create_approved_draft(tmp_path)
    attempt_id = database.record_send_attempt(draft_id, status="started")
    with sqlite3.connect(database.db_path) as conn:
        conn.execute(
            "UPDATE message_send_attempts SET started_at = datetime('now', '-30 minutes') WHERE id = ?",
            (attempt_id,),
        )
    assert database.reconcile_ambiguous_send_attempts(15, actor="test") == 1
    assert database.get_message_draft(draft_id)["status"] == "failed"
    attempt = database.get_send_attempts(draft_id=draft_id, limit=1)[0]
    assert attempt["error_message"] == "external_outcome_unknown"


def test_daily_send_limit_is_enforced_before_external_action(tmp_path):
    database, ledger, campaign_id, draft_id = create_approved_draft(tmp_path)
    ledger.confirm_manual_send(draft_id, "manual test evidence", actor="test")
    database.add_volunteer({
        "volunteer_id": "v-2", "name": "Ben", "location": "Arnhem", "categories": "maatjes"
    })
    second_id = database.create_message_draft({
        "campaign_id": campaign_id,
        "volunteer_id": "v-2",
        "subject": "Campaign",
        "body": "Beste Ben",
    })
    database.approve_message_draft(second_id, "test", actor="test")
    limited = OutreachLedger(database, RuntimeSettings(max_send_batch=5, daily_send_limit=1))
    with pytest.raises(ValueError, match="Daily send limit"):
        limited.send_approved_drafts(object(), [second_id])


def test_google_drive_constructor_has_no_auth_or_remote_side_effects(tmp_path):
    token = tmp_path / "private" / "token.json"
    secret = tmp_path / "private" / "client.json"
    manager = GoogleDriveManager(str(token), str(secret))
    assert manager.service is None
    assert manager.status()["connected"] is False
    assert not token.parent.exists()
    assert SCOPES == ["https://www.googleapis.com/auth/drive.file"]


def test_support_bundle_excludes_private_runtime_files(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "private.log").write_text("volunteer personal data", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "google_token.json").write_text("secret", encoding="utf-8")
    bundle = tmp_path / "support.zip"
    SupportBundleBuilder(str(tmp_path)).create(str(bundle))
    with zipfile.ZipFile(bundle) as archive:
        assert set(archive.namelist()) == {"diagnostics.json", "README.txt"}
        content = archive.read("diagnostics.json").decode("utf-8")
    assert "volunteer personal data" not in content
    assert '"secret"' not in content


def test_backup_excludes_credentials_and_absolute_paths(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "app.db").write_bytes(b"database")
    (data_dir / "google_token.json").write_text("secret", encoding="utf-8")
    manager = BackupManager(str(data_dir), str(tmp_path / "backups"))
    backup_path = manager.create_backup("safe")
    with zipfile.ZipFile(backup_path) as archive:
        names = archive.namelist()
        metadata = json.loads(archive.read("backup_metadata.json"))
    assert "data/app.db" in names
    assert all("token" not in name for name in names)
    assert metadata["data_dir"] == "data"
    assert str(tmp_path) not in json.dumps(metadata)


def test_restore_aborts_when_rollback_backup_fails(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    original = data_dir / "app.db"
    original.write_text("original", encoding="utf-8")
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("data/app.db", "replacement")
        archive.writestr("backup_metadata.json", "{}")
    manager = BackupManager(str(data_dir), str(tmp_path / "backups"))
    monkeypatch.setattr(manager, "create_backup", lambda _name: None)
    assert manager.restore_backup(str(source)) is False
    assert original.read_text(encoding="utf-8") == "original"


def test_local_critical_path_smoke_is_network_free():
    result = verify_local_critical_path()
    assert result["status"] == "pass"
    assert result["network_used"] is False
    assert result["external_messages_sent"] == 0
    assert result["backup_verified"] is True
    assert result["database_ready"] is True


def test_description_sanitizer_removes_active_content():
    from utils.bug_fixes import InputValidator

    value = InputValidator.sanitize_description(
        '<p>Hello <strong>volunteer</strong></p><script>alert("secret")</script>'
        '<style>body { display: none; }</style>'
    )

    assert value == "Hello volunteer"
    assert "alert" not in value
    assert "display" not in value
