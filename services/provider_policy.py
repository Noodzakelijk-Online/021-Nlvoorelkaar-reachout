"""Offline validation for written NLvoorelkaar automation authorization."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Optional


PROVIDER = "nlvoorelkaar"
TERMS_VERSION = "2025-12-15"
TERMS_URL = "https://www.nlvoorelkaar.nl/helpcentrum/artikel/209596769"
ALLOWED_ACTIONS = {"login", "search", "send"}
REQUIRED_ACKNOWLEDGEMENTS = {
    "personal_account_only",
    "intended_use_only",
    "no_credential_sharing",
    "bounded_rate_limits",
    "personal_data_protected",
}
SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


@dataclass(frozen=True)
class ProviderAuthorizationStatus:
    ready: bool
    approved_actions: tuple[str, ...] = ()
    expires_at: Optional[str] = None
    terms_version: Optional[str] = None
    checked_at: Optional[str] = None
    errors: tuple[str, ...] = ()

    def public_status(self) -> dict[str, object]:
        """Return metadata that is safe for diagnostics and support bundles."""
        return asdict(self)


def _parse_date(value: object, field_name: str, errors: list[str]) -> Optional[date]:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name} is required")
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        errors.append(f"{field_name} must use YYYY-MM-DD")
        return None


def validate_provider_authorization(
    approval_path: Optional[str],
    required_actions: Iterable[str] = (),
    *,
    today: Optional[date] = None,
) -> ProviderAuthorizationStatus:
    """Validate a private approval record without contacting the provider."""
    errors: list[str] = []
    requested = {str(action).strip().lower() for action in required_actions}
    unknown_requested = requested - ALLOWED_ACTIONS
    if unknown_requested:
        errors.append("Unknown provider action(s): " + ", ".join(sorted(unknown_requested)))

    if not approval_path:
        return ProviderAuthorizationStatus(
            ready=False,
            errors=("NLVE_PROVIDER_APPROVAL_PATH is required for live provider actions",),
        )

    path = Path(approval_path).expanduser()
    if not path.is_absolute():
        errors.append("NLVE_PROVIDER_APPROVAL_PATH must be an absolute private path")
    if not path.is_file():
        errors.append("Provider approval record was not found")
        return ProviderAuthorizationStatus(ready=False, errors=tuple(errors))
    if path.stat().st_size > 64 * 1024:
        errors.append("Provider approval record exceeds 64 KiB")
        return ProviderAuthorizationStatus(ready=False, errors=tuple(errors))

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ProviderAuthorizationStatus(
            ready=False,
            errors=tuple(errors + ["Provider approval record is not valid UTF-8 JSON"]),
        )
    if not isinstance(payload, dict):
        return ProviderAuthorizationStatus(
            ready=False,
            errors=tuple(errors + ["Provider approval record must be a JSON object"]),
        )

    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if str(payload.get("provider", "")).strip().lower() != PROVIDER:
        errors.append(f"provider must be {PROVIDER}")
    if payload.get("authorization_type") != "written_platform_approval":
        errors.append("authorization_type must be written_platform_approval")
    if not str(payload.get("approved_by", "")).strip():
        errors.append("approved_by is required")
    if not str(payload.get("approval_reference", "")).strip():
        errors.append("approval_reference is required")

    evidence_hash = str(payload.get("evidence_sha256", "")).strip()
    if not SHA256_PATTERN.fullmatch(evidence_hash):
        errors.append("evidence_sha256 must be the SHA-256 of the written approval evidence")

    actions_value = payload.get("approved_actions")
    actions = {
        str(action).strip().lower()
        for action in actions_value
    } if isinstance(actions_value, list) else set()
    if not actions:
        errors.append("approved_actions must contain at least one provider action")
    unknown_actions = actions - ALLOWED_ACTIONS
    if unknown_actions:
        errors.append("approved_actions contains unsupported action(s): " + ", ".join(sorted(unknown_actions)))
    missing_actions = requested - actions
    if missing_actions:
        errors.append("Written approval does not cover: " + ", ".join(sorted(missing_actions)))

    if payload.get("terms_url") != TERMS_URL:
        errors.append("terms_url does not match the reviewed NLvoorelkaar terms")
    if payload.get("terms_version") != TERMS_VERSION:
        errors.append(f"terms_version must be {TERMS_VERSION}; review changed terms before live use")

    acknowledgements = payload.get("acknowledgements")
    acknowledgements = acknowledgements if isinstance(acknowledgements, dict) else {}
    missing_acknowledgements = sorted(
        name for name in REQUIRED_ACKNOWLEDGEMENTS if acknowledgements.get(name) is not True
    )
    if missing_acknowledgements:
        errors.append("Required acknowledgement(s) missing: " + ", ".join(missing_acknowledgements))

    current_date = today or date.today()
    checked_at = _parse_date(payload.get("terms_checked_at"), "terms_checked_at", errors)
    expires_at = _parse_date(payload.get("expires_at"), "expires_at", errors)
    if checked_at and checked_at > current_date:
        errors.append("terms_checked_at cannot be in the future")
    if checked_at and (current_date - checked_at).days > 30:
        errors.append("NLvoorelkaar terms review is older than 30 days")
    if expires_at and expires_at < current_date:
        errors.append("Written provider approval has expired")

    return ProviderAuthorizationStatus(
        ready=not errors,
        approved_actions=tuple(sorted(actions)),
        expires_at=expires_at.isoformat() if expires_at else None,
        terms_version=str(payload.get("terms_version") or "") or None,
        checked_at=checked_at.isoformat() if checked_at else None,
        errors=tuple(errors),
    )


def approval_evidence_sha256(path: str) -> str:
    """Hash a provider approval artifact for the private authorization record."""
    evidence = Path(path).expanduser()
    if not evidence.is_file():
        raise ValueError("Approval evidence file was not found")
    digest = hashlib.sha256()
    with evidence.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
