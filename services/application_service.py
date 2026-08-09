"""Shared application boundary for desktop, web, CLI, and HAI adapters."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from config.runtime import RuntimeSettings
from database.database_manager import DatabaseManager
from services.outreach_ledger import OutreachLedger


class ApplicationService:
    """Expose validated use cases without UI or transport dependencies."""

    def __init__(
        self,
        database: Optional[DatabaseManager] = None,
        settings: Optional[RuntimeSettings] = None,
    ) -> None:
        self.database = database or DatabaseManager()
        self.settings = settings or RuntimeSettings.from_environment()
        self.ledger = OutreachLedger(self.database, self.settings)

    def status(self) -> Dict[str, Any]:
        return {
            "runtime": self.settings.public_status(),
            "database": self.database.get_database_health(),
            "safety_stop_active": bool(self.database.get_runtime_control("safety_stop", False)),
            "hai_feed": {"available": True, "mode": "read_only"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def dashboard(self) -> Dict[str, Any]:
        result = self.database.get_statistics()
        result.update(self.database.get_operating_statistics())
        result["campaigns"] = self.database.get_campaigns()[:20]
        result["review_queue"] = self.ledger.get_review_queue(limit=20)
        result["responses"] = self.ledger.get_response_inbox(limit=20)
        result["follow_ups"] = self.ledger.get_follow_up_queue(limit=20)
        return result

    def list_volunteers(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self.database.get_volunteers(limit=limit, offset=offset)

    def list_campaigns(self) -> List[Dict[str, Any]]:
        return self.database.get_campaigns()

    def create_campaign(self, data: Dict[str, Any]) -> int:
        name = str(data.get("name") or "").strip()
        template = str(data.get("message_template") or "").strip()
        if not name:
            raise ValueError("Campaign name is required")
        if not template:
            raise ValueError("Message template is required")
        campaign_id = self.database.add_campaign({**data, "name": name, "message_template": template})
        if not campaign_id:
            raise RuntimeError("Campaign could not be created")
        self.database.record_audit_event(
            "campaign", str(campaign_id), "campaign_created", actor="web_operator"
        )
        return int(campaign_id)

    def create_drafts(self, campaign_id: int, volunteer_ids: Optional[List[str]] = None) -> List[int]:
        return self.ledger.create_message_drafts(campaign_id, volunteer_ids)

    def review_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.ledger.get_review_queue(limit=limit)

    def message_drafts(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        allowed = {"draft", "approved", "rejected", "sent", "failed"}
        if status not in allowed:
            raise ValueError("Unsupported message status")
        return self.database.get_message_drafts(status=status, limit=limit)

    def approve_message(self, draft_id: int, reason: str, actor: str = "web_operator") -> int:
        return self.ledger.approve_message(draft_id, reason, actor=actor)

    def reject_message(self, draft_id: int, reason: str, actor: str = "web_operator") -> int:
        return self.ledger.reject_message(draft_id, reason, actor=actor)

    def confirm_manual_send(self, draft_id: int, evidence: str, actor: str = "web_operator") -> int:
        if self.safety_stop_active():
            raise RuntimeError("Safety stop is active")
        return self.ledger.confirm_manual_send(draft_id, evidence, actor=actor)

    def responses(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.ledger.get_response_inbox(limit=limit)

    def record_response(
        self,
        volunteer_id: str,
        campaign_id: int,
        content: str,
        source: str = "web_operator",
    ) -> int:
        return self.ledger.record_response(volunteer_id, campaign_id, content, source=source)

    def follow_ups(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.ledger.get_follow_up_queue(limit=limit)

    def approve_follow_up(self, follow_up_id: int, actor: str = "web_operator") -> bool:
        return self.ledger.approve_follow_up(follow_up_id, actor=actor)

    def confirm_follow_up(self, follow_up_id: int, evidence: str, actor: str = "web_operator") -> int:
        if self.safety_stop_active():
            raise RuntimeError("Safety stop is active")
        return self.ledger.confirm_follow_up_sent(follow_up_id, evidence, actor=actor)

    def privacy_candidates(self, days: int = 365, limit: int = 100) -> List[Dict[str, Any]]:
        return self.ledger.get_privacy_retention_candidates(days=days, limit=limit)

    def archive_volunteer(self, volunteer_id: str, reason: str, actor: str = "web_operator") -> None:
        if not self.ledger.archive_volunteer_for_retention(volunteer_id, reason, actor=actor):
            raise ValueError("Volunteer was not found")

    def redact_volunteer(self, volunteer_id: str, reason: str, actor: str = "web_operator") -> None:
        if not self.ledger.redact_volunteer_personal_data(volunteer_id, reason, actor=actor):
            raise ValueError("Volunteer was not found")

    def safety_stop_active(self) -> bool:
        return bool(self.database.get_runtime_control("safety_stop", False))

    def set_safety_stop(self, active: bool, actor: str = "web_operator") -> None:
        self.database.set_runtime_control("safety_stop", bool(active), actor=actor)

    @staticmethod
    def _feed_item(
        kind: str,
        identifier: object,
        revision: object,
        title: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        revision_digest = hashlib.sha256(str(revision).encode("utf-8")).hexdigest()[:16]
        return {
            "externalId": f"nlve-{kind}-{identifier}-{revision_digest}",
            "title": title,
            "content": content,
            "sourceUri": f"nlve://{kind}/{identifier}",
            "itemType": "card",
            "provider": "generic_json_feed",
            "accountLabel": "nlvoorelkaar-reachout",
            "projectKey": "021-Nlvoorelkaar-reachout",
            "metadata": metadata,
        }

    def hai_feed(self, limit: int = 100) -> Dict[str, Any]:
        """Return a privacy-minimized, read-only feed compatible with HAI."""
        items: List[Dict[str, Any]] = []
        for draft in self.ledger.get_review_queue(limit=limit):
            items.append(self._feed_item(
                "message-review",
                draft["id"],
                draft.get("updated_at") or draft.get("created_at"),
                f"Review outreach draft #{draft['id']}",
                f"An outreach draft is in state {draft.get('status', 'unknown')} and requires operator review.",
                {
                    "recordType": "message_draft",
                    "recordId": draft["id"],
                    "campaignId": draft.get("campaign_id"),
                    "status": draft.get("status"),
                    "requiresHumanReview": True,
                    "executionAuthority": "none",
                },
            ))
        remaining = max(0, limit - len(items))
        responses = self.ledger.get_response_inbox(limit=remaining) if remaining else []
        for response in responses:
            items.append(self._feed_item(
                "response-review",
                response["id"],
                response.get("received_at") or response.get("created_at"),
                f"Review volunteer response #{response['id']}",
                "A volunteer response is available for an operator decision. Personal content stays in NLVE.",
                {
                    "recordType": "volunteer_response",
                    "recordId": response["id"],
                    "campaignId": response.get("campaign_id"),
                    "requiresHumanReview": True,
                    "executionAuthority": "none",
                },
            ))
        canonical = json.dumps(items, sort_keys=True, separators=(",", ":"))
        return {
            "cursor": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "items": items,
        }
