"""
Volunteer outreach operating ledger.

Coordinates campaign readiness, message drafts, explicit approval, send
attempt evidence, responses, follow-ups, duplicate checks, and audit events.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.database_manager import DatabaseManager
from models.data_models import Campaign, Volunteer
from services.data_management import DataExporter, ExportConfig, ExportFormat
from config.runtime import RuntimeSettings

logger = logging.getLogger(__name__)


class OutreachLedger:
    """Application service for review-gated volunteer outreach operations."""

    def __init__(
        self,
        database_manager: DatabaseManager,
        runtime_settings: Optional[RuntimeSettings] = None,
    ):
        self.db = database_manager
        self.runtime_settings = runtime_settings or RuntimeSettings()

    def check_campaign_readiness(self, campaign_id: int) -> Dict[str, Any]:
        """Return whether a campaign has enough local state to safely operate."""
        campaigns = self.db.get_campaigns()
        campaign = next((c for c in campaigns if c.get("id") == campaign_id), None)
        issues: List[Dict[str, str]] = []

        if not campaign:
            return {
                "campaign_id": campaign_id,
                "ready": False,
                "status": "blocked",
                "issues": [{"severity": "error", "message": "Campaign not found"}],
                "next_actions": ["Create or select a campaign before outreach."]
            }

        if not campaign.get("message_template", "").strip():
            issues.append({
                "severity": "error",
                "message": "Campaign is missing a message template."
            })

        if not campaign.get("target_categories", "").strip() and not campaign.get("target_location", "").strip():
            issues.append({
                "severity": "warning",
                "message": "Campaign has no target category or location filter."
            })

        snapshot = self._campaign_candidate_snapshot(campaign)
        volunteers = snapshot["eligible"]
        self.db.record_campaign_exclusions(
            campaign_id,
            snapshot["exclusions"],
            actor="system"
        )
        if not volunteers:
            issues.append({
                "severity": "error",
                "message": "No eligible volunteers are available for this campaign."
            })

        duplicates = self.db.find_duplicate_volunteers()
        if duplicates:
            issues.append({
                "severity": "warning",
                "message": f"{len(duplicates)} possible duplicate volunteer group(s) need review."
            })

        draft_counts = self._draft_counts(campaign_id)
        match_counts = self._match_counts(campaign_id)
        ready = not any(issue["severity"] == "error" for issue in issues)
        next_actions = []
        if ready and not match_counts:
            next_actions.append("Assess volunteer matches for this campaign.")
        if ready and draft_counts.get("draft", 0) == 0 and draft_counts.get("approved", 0) == 0:
            next_actions.append("Create message drafts for matching volunteers.")
        if draft_counts.get("draft", 0) > 0:
            next_actions.append("Review and approve drafted messages.")
        if draft_counts.get("approved", 0) > 0:
            next_actions.append("Send approved messages when ready.")

        return {
            "campaign_id": campaign_id,
            "ready": ready,
            "status": "ready" if ready else "blocked",
            "eligible_volunteers": len(volunteers),
            "excluded_volunteers": snapshot["excluded_volunteers"],
            "exclusion_counts": snapshot["exclusion_counts"],
            "draft_counts": draft_counts,
            "match_counts": match_counts,
            "issues": issues,
            "next_actions": next_actions
        }

    def create_message_drafts(
        self,
        campaign_id: int,
        volunteer_ids: Optional[List[str]] = None
    ) -> List[int]:
        """Create personalized drafts for a campaign without sending anything."""
        campaign_data = next((c for c in self.db.get_campaigns() if c.get("id") == campaign_id), None)
        if not campaign_data:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign = Campaign.from_dict(campaign_data)
        volunteers = self._campaign_candidate_pool(campaign_data, volunteer_ids)
        draft_ids: List[int] = []

        for volunteer_data in volunteers:
            volunteer = Volunteer.from_dict(volunteer_data)
            body = campaign.personalize_message(volunteer)
            subject = campaign.name
            draft_id = self.db.create_message_draft({
                "campaign_id": campaign_id,
                "volunteer_id": volunteer.volunteer_id,
                "subject": subject,
                "body": body,
                "template_id": "campaign.message_template",
                "personalization": {
                    "name": volunteer.name,
                    "location": volunteer.location,
                    "skills": volunteer.skills,
                    "categories": volunteer.categories
                }
            })
            draft_ids.append(draft_id)

        self.db.record_audit_event(
            "campaign",
            campaign_id,
            "message_drafts_created",
            after_state={"draft_count": len(draft_ids)}
        )
        return draft_ids

    def get_review_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return drafts needing operator review."""
        return self.db.get_message_drafts(status="draft", limit=limit)

    def approve_message(self, draft_id: int, reason: str = "", actor: str = "user") -> int:
        """Approve a draft and persist the exact sendable snapshot."""
        return self.db.approve_message_draft(draft_id, reason, actor)

    def edit_message_draft(
        self,
        draft_id: int,
        subject: Optional[str] = None,
        body: Optional[str] = None
    ) -> bool:
        """Edit a draft before approval and return it to draft review."""
        return self.db.update_message_draft(draft_id, subject=subject, body=body)

    def reject_message(self, draft_id: int, reason: str = "", actor: str = "user") -> int:
        """Reject a draft with an optional operator reason."""
        return self.db.reject_message_draft(draft_id, reason, actor)

    def get_approved_drafts(
        self,
        campaign_id: int,
        volunteer_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get approved drafts ready for an explicit send action."""
        drafts = self.db.get_message_drafts(status="approved", campaign_id=campaign_id, limit=1000)
        if volunteer_ids:
            allowed = set(volunteer_ids)
            drafts = [draft for draft in drafts if draft.get("volunteer_id") in allowed]
        return drafts

    def send_approved_drafts(
        self,
        scraper: Any,
        draft_ids: List[int],
        progress_callback=None,
        cancellation_token=None
    ) -> Dict[str, int]:
        """Send only approved drafts and record deterministic attempt outcomes."""
        if not draft_ids:
            return {"sent_count": 0, "failed_count": 0, "total_count": 0}
        if len(draft_ids) > self.runtime_settings.max_send_batch:
            raise ValueError(
                f"One send action is limited to {self.runtime_settings.max_send_batch} messages"
            )
        sent_today = self.db.get_daily_sent_count()
        if sent_today + len(draft_ids) > self.runtime_settings.daily_send_limit:
            raise ValueError(
                f"Daily send limit of {self.runtime_settings.daily_send_limit} would be exceeded"
            )

        sent_count = 0
        failed_count = 0

        for index, draft_id in enumerate(draft_ids):
            if cancellation_token and cancellation_token.is_set():
                break

            draft = self.db.get_message_draft(draft_id)
            if not draft:
                failed_count += 1
                continue

            if draft.get("status") != "approved":
                failed_count += 1
                self.db.record_audit_event(
                    "message_draft",
                    draft_id,
                    "send_blocked_unapproved",
                    after_state={"status": draft.get("status")},
                    risk_level="high"
                )
                continue

            if progress_callback:
                progress_callback(
                    index,
                    len(draft_ids),
                    f"Sending approved draft {draft_id} for campaign {draft.get('campaign_id')}..."
                )

            try:
                attempt_id = self.db.record_send_attempt(draft_id, status="started")
            except ValueError:
                failed_count += 1
                self.db.record_audit_event(
                    "message_draft",
                    draft_id,
                    "duplicate_or_stale_send_blocked",
                    after_state={"status": self.db.get_message_draft(draft_id).get("status")},
                    risk_level="high",
                )
                continue
            try:
                success = scraper.send_message(
                    draft["volunteer_id"],
                    draft["body"],
                    approval_token="outreach_ledger_approved_send"
                )
                if success:
                    evidence = "scraper_send_message_returned_true"
                    self.db.finish_send_attempt(attempt_id, "sent", delivery_evidence=evidence)
                    self.db.add_contact({
                        "volunteer_id": draft["volunteer_id"],
                        "campaign_id": draft["campaign_id"],
                        "message_sent": draft["body"],
                        "status": "sent",
                        "notes": f"Sent from approved draft {draft_id}; evidence={evidence}"
                    })
                    sent_count += 1
                else:
                    self.db.finish_send_attempt(
                        attempt_id,
                        "failed",
                        error_message="Scraper did not return send confirmation"
                    )
                    failed_count += 1
            except (KeyError, TypeError, AttributeError, RuntimeError, ValueError) as exc:
                logger.error("Approved send failed for draft %s: %s", draft_id, type(exc).__name__)
                self.db.finish_send_attempt(attempt_id, "failed", error_message=type(exc).__name__)
                failed_count += 1

        if progress_callback:
            progress_callback(
                len(draft_ids),
                len(draft_ids),
                f"Completed: {sent_count} sent, {failed_count} failed"
            )

        return {
            "sent_count": sent_count,
            "failed_count": failed_count,
            "total_count": len(draft_ids)
        }

    def record_response(
        self,
        volunteer_id: str,
        campaign_id: Optional[int],
        raw_content: str,
        contact_id: Optional[int] = None,
        source: str = "manual"
    ) -> int:
        """Record and classify a volunteer response."""
        classification, confidence = self.classify_response(raw_content)
        response_id = self.db.record_volunteer_response(
            volunteer_id=volunteer_id,
            campaign_id=campaign_id,
            raw_content=raw_content,
            classification=classification,
            confidence=confidence,
            contact_id=contact_id,
            source=source
        )

        if classification in {"more_info", "unknown"}:
            self.create_follow_up(
                volunteer_id,
                campaign_id,
                previous_message_id=None,
                days_until_due=3,
                suggested_message="Beste {name}, dank voor uw reactie. Mag ik u nog een korte vervolgvraag stellen?"
            )

        return response_id

    def create_follow_up(
        self,
        volunteer_id: str,
        campaign_id: Optional[int],
        previous_message_id: Optional[int],
        days_until_due: int,
        suggested_message: str
    ) -> int:
        """Create a due follow-up suggestion; it is not sent automatically."""
        due_at = (datetime.now() + timedelta(days=days_until_due)).isoformat()
        return self.db.create_follow_up(
            volunteer_id=volunteer_id,
            campaign_id=campaign_id,
            previous_message_id=previous_message_id,
            due_at=due_at,
            suggested_message=suggested_message
        )

    def classify_response(self, content: str) -> tuple[str, float]:
        """Small transparent classifier for manual response triage."""
        lowered = (content or "").lower()
        if any(word in lowered for word in ["ja", "interesse", "graag", "kan", "beschikbaar"]):
            return "interested", 0.75
        if any(word in lowered for word in ["nee", "geen interesse", "niet beschikbaar", "stop"]):
            return "declined", 0.75
        if any(word in lowered for word in ["meer informatie", "info", "vraag", "vertel"]):
            return "more_info", 0.65
        if any(word in lowered for word in ["later", "nu niet", "druk"]):
            return "unavailable", 0.65
        return "unknown", 0.25

    def get_operating_summary(self) -> Dict[str, Any]:
        """Dashboard-ready operating ledger summary."""
        summary = self.db.get_operating_statistics()
        summary["review_queue"] = self.get_review_queue(limit=10)
        summary["failed_send_attempts"] = self.db.get_send_attempts(limit=10)
        summary["follow_ups_due_items"] = self.db.get_follow_ups_due(limit=10)
        summary["strong_matches"] = self.db.get_match_assessments(status="strong", limit=10)
        summary["duplicates"] = self.db.find_duplicate_volunteers()
        summary["recent_search_sessions"] = self.db.get_search_sessions(limit=10)
        summary["recent_audit_events"] = self.db.get_audit_events(limit=10)
        return summary

    def get_search_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return recent search sessions with captured result membership."""
        return self.db.get_search_sessions(limit=limit)

    def get_search_session_results(
        self,
        search_session_id: Optional[int] = None,
        task_id: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Return volunteers captured for one search session or task."""
        return self.db.get_search_session_results(
            search_session_id=search_session_id,
            task_id=task_id,
            limit=limit
        )

    def get_campaign_operating_summary(self, campaign_id: int) -> Dict[str, Any]:
        """Return one campaign's operating ledger status for campaign detail."""
        summary = self.db.get_campaign_operating_summary(campaign_id, limit=10)
        if not summary:
            raise ValueError(f"Campaign {campaign_id} not found")

        readiness = self.check_campaign_readiness(campaign_id)
        counts = summary.setdefault("counts", {})
        counts["eligible_volunteers"] = readiness.get("eligible_volunteers", 0)
        counts["excluded_volunteers"] = readiness.get("excluded_volunteers", 0)
        counts["exclusions"] = readiness.get("exclusion_counts", counts.get("exclusions", {}))
        summary["exclusions"] = self.db.get_campaign_exclusions(campaign_id, limit=10)
        summary["readiness"] = readiness
        summary["next_actions"] = self._campaign_next_actions(summary)
        return summary

    def assess_campaign_matches(self, campaign_id: int) -> List[Dict[str, Any]]:
        """Score eligible volunteers against campaign criteria with explainable reasons."""
        campaign_data = next((c for c in self.db.get_campaigns() if c.get("id") == campaign_id), None)
        if not campaign_data:
            raise ValueError(f"Campaign {campaign_id} not found")

        volunteers = self._campaign_candidate_pool(campaign_data)
        assessment_ids: List[int] = []
        for volunteer in volunteers:
            score, status, reasons = self._score_campaign_match(campaign_data, volunteer)
            assessment_id = self.db.record_match_assessment(
                campaign_id=campaign_id,
                volunteer_id=volunteer["volunteer_id"],
                score=score,
                reasons=reasons,
                status=status
            )
            assessment_ids.append(assessment_id)

        self.db.record_audit_event(
            "campaign",
            campaign_id,
            "campaign_matches_assessed",
            after_state={"assessment_count": len(assessment_ids)}
        )
        return self.db.get_match_assessments(campaign_id=campaign_id, limit=1000)

    def get_match_assessments(
        self,
        campaign_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return persisted volunteer fit assessments."""
        return self.db.get_match_assessments(campaign_id=campaign_id, status=status, limit=limit)

    def get_campaign_exclusions(
        self,
        campaign_id: int,
        reason_code: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return volunteers excluded from a campaign with persisted reasons."""
        return self.db.get_campaign_exclusions(campaign_id, reason_code=reason_code, limit=limit)

    def get_volunteers(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Return volunteers for local review."""
        return self.db.get_volunteers()[:limit]

    def get_volunteer_operating_profile(self, volunteer_id: str) -> Optional[Dict[str, Any]]:
        """Return one volunteer with contact, response, match, follow-up, and duplicate context."""
        return self.db.get_volunteer_operating_profile(volunteer_id)

    def get_send_attempt_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return message and follow-up send attempt history for operational review."""
        message_attempts = self.db.get_send_attempts(limit=limit)
        for attempt in message_attempts:
            attempt["attempt_type"] = "message"

        follow_up_attempts = self.db.get_follow_up_send_attempts(limit=limit)
        for attempt in follow_up_attempts:
            attempt["attempt_type"] = "follow_up"
            attempt["message_draft_id"] = None

        combined = message_attempts + follow_up_attempts
        combined.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return combined[:limit]

    def confirm_manual_send(
        self,
        draft_id: int,
        delivery_evidence: str,
        actor: str = "user"
    ) -> int:
        """Record explicit manual evidence that an approved draft was sent."""
        return self.db.confirm_manual_send(draft_id, delivery_evidence, actor=actor)

    def propose_duplicate_identities(self) -> List[int]:
        """Persist current duplicate volunteer groups for review."""
        return self.db.propose_duplicate_identities()

    def get_duplicate_identity_proposals(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return duplicate identity proposals or confirmed groups."""
        return self.db.get_volunteer_identities(status=status, limit=limit)

    def confirm_duplicate_identity(
        self,
        identity_id: int,
        canonical_volunteer_id: str,
        actor: str = "user"
    ) -> bool:
        """Confirm a duplicate identity group without deleting volunteer records."""
        return self.db.confirm_volunteer_identity(identity_id, canonical_volunteer_id, actor=actor)

    def get_response_inbox(
        self,
        campaign_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return volunteer responses for operator triage."""
        return self.db.get_volunteer_responses(campaign_id=campaign_id, limit=limit)

    def record_outreach_outcome(
        self,
        volunteer_id: str,
        campaign_id: Optional[int],
        outcome_type: str,
        notes: str = "",
        response_id: Optional[int] = None,
        follow_up_id: Optional[int] = None,
        actor: str = "user"
    ) -> int:
        """Record an operator-reviewed outreach outcome."""
        return self.db.record_outreach_outcome(
            volunteer_id=volunteer_id,
            campaign_id=campaign_id,
            outcome_type=outcome_type,
            notes=notes,
            response_id=response_id,
            follow_up_id=follow_up_id,
            actor=actor
        )

    def get_outreach_outcomes(
        self,
        campaign_id: Optional[int] = None,
        volunteer_id: Optional[str] = None,
        outcome_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return recorded outreach outcomes."""
        return self.db.get_outreach_outcomes(
            campaign_id=campaign_id,
            volunteer_id=volunteer_id,
            outcome_type=outcome_type,
            limit=limit
        )

    def get_follow_up_queue(
        self,
        status: Optional[str] = None,
        include_future: bool = True,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return follow-ups that still require human handling."""
        return self.db.get_follow_ups(status=status, include_future=include_future, limit=limit)

    def complete_follow_up(self, follow_up_id: int, actor: str = "user") -> bool:
        """Mark a follow-up as completed after a human handles it."""
        return self.db.update_follow_up_status(follow_up_id, "completed", actor=actor)

    def approve_follow_up(
        self,
        follow_up_id: int,
        message_snapshot: Optional[str] = None,
        actor: str = "user"
    ) -> bool:
        """Approve a follow-up message before send confirmation."""
        return self.db.approve_follow_up(follow_up_id, message_snapshot=message_snapshot, actor=actor)

    def confirm_follow_up_sent(
        self,
        follow_up_id: int,
        delivery_evidence: str,
        actor: str = "user"
    ) -> int:
        """Record manual evidence that an approved follow-up was sent."""
        return self.db.confirm_follow_up_sent(follow_up_id, delivery_evidence, actor=actor)

    def get_follow_up_send_attempts(
        self,
        follow_up_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return follow-up send attempt history."""
        return self.db.get_follow_up_send_attempts(follow_up_id=follow_up_id, limit=limit)

    def cancel_follow_up(self, follow_up_id: int, actor: str = "user") -> bool:
        """Cancel a follow-up that should no longer be pursued."""
        return self.db.update_follow_up_status(follow_up_id, "cancelled", actor=actor)

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return recent audit events for review."""
        return self.db.get_audit_events(limit=limit)

    def get_privacy_retention_candidates(
        self,
        days: int = 365,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return stale records for retention/privacy review."""
        return self.db.get_privacy_retention_candidates(days=days, limit=limit)

    def get_privacy_retention_records(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return proposed and completed retention actions."""
        return self.db.get_privacy_retention_records(status=status, limit=limit)

    def get_task_runs(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return durable background task history."""
        return self.db.get_task_runs(status=status, limit=limit)

    def record_task_run(self, task_data: Dict[str, Any]) -> None:
        """Persist one task state update."""
        self.db.record_task_run(task_data)

    def propose_retention_actions(self, days: int = 365, actor: str = "user") -> bool:
        """Record retention proposals without deleting data."""
        return self.db.cleanup_old_data(days=days, confirm=False, actor=actor)

    def archive_volunteer_for_retention(
        self,
        volunteer_id: str,
        reason: str,
        actor: str = "user"
    ) -> bool:
        """Archive stale volunteer data while keeping ledger history intact."""
        if not volunteer_id:
            raise ValueError("volunteer_id is required")
        return self.db.archive_volunteer_for_retention(volunteer_id, reason, actor=actor)

    def redact_volunteer_personal_data(
        self,
        volunteer_id: str,
        reason: str,
        actor: str = "user"
    ) -> bool:
        """Minimize personal profile data while preserving outreach references."""
        if not volunteer_id:
            raise ValueError("volunteer_id is required")
        return self.db.redact_volunteer_personal_data(volunteer_id, reason, actor=actor)

    def export_volunteer_data(
        self,
        output_path: str,
        export_format: str = "json",
        actor: str = "user"
    ) -> Dict[str, Any]:
        """Export non-redacted volunteer data with an audit event."""
        try:
            selected_format = ExportFormat(export_format.lower())
        except ValueError as exc:
            raise ValueError(f"Unsupported export format: {export_format}") from exc

        exporter = DataExporter(self.db.db_path)
        count = exporter.export_volunteers(
            output_path,
            ExportConfig(format=selected_format, exclude_redacted=True),
            actor=actor
        )
        return {
            "path": output_path,
            "format": selected_format.value,
            "record_count": count
        }

    def _campaign_candidate_pool(
        self,
        campaign: Dict[str, Any],
        volunteer_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        return self._campaign_candidate_snapshot(campaign, volunteer_ids=volunteer_ids)["eligible"]

    def _campaign_candidate_snapshot(
        self,
        campaign: Dict[str, Any],
        volunteer_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Return eligible volunteers and durable exclusion reasons for a campaign."""
        volunteers = self.db.get_volunteers()
        if volunteer_ids:
            allowed = set(volunteer_ids)
            volunteers = [volunteer for volunteer in volunteers if volunteer.get("volunteer_id") in allowed]

        blacklist = {entry.get("volunteer_id") for entry in self.db.get_blacklist()}
        confirmed_duplicates = self.db.get_confirmed_duplicate_member_map()
        contacted = {
            contact.get("volunteer_id")
            for contact in self.db.get_contacts(campaign.get("id"))
            if contact.get("status") in {"sent", "responded"}
        }
        unsuitable_outcomes = {
            outcome.get("volunteer_id")
            for outcome in self.db.get_outreach_outcomes(campaign_id=campaign.get("id"), limit=10000)
            if outcome.get("outcome_type") in {"declined", "unavailable", "not_suitable", "do_not_contact"}
        }

        target_categories = (campaign.get("target_categories") or "").strip().lower()
        target_location = (campaign.get("target_location") or "").strip().lower()
        eligible: List[Dict[str, Any]] = []
        exclusions: List[Dict[str, Any]] = []
        excluded_volunteers = set()
        exclusion_counts: Dict[str, int] = {}

        def add_exclusion(
            volunteer: Dict[str, Any],
            reason_code: str,
            reason_message: str,
            evidence: Dict[str, Any]
        ) -> None:
            exclusions.append({
                "volunteer_id": volunteer.get("volunteer_id"),
                "reason_code": reason_code,
                "reason_message": reason_message,
                "evidence": evidence
            })
            if volunteer.get("volunteer_id"):
                excluded_volunteers.add(volunteer["volunteer_id"])
            exclusion_counts[reason_code] = exclusion_counts.get(reason_code, 0) + 1

        for volunteer in volunteers:
            volunteer_id = volunteer.get("volunteer_id")
            reasons_before = len(exclusions)
            retention_status = (volunteer.get("retention_status") or "active").lower()
            volunteer_categories = (volunteer.get("categories") or "").lower()
            volunteer_location = (volunteer.get("location") or "").lower()

            if retention_status == "redacted":
                add_exclusion(
                    volunteer,
                    "redacted",
                    "Volunteer personal data has been redacted for retention/privacy.",
                    {"retention_status": retention_status}
                )
            elif retention_status == "archived":
                add_exclusion(
                    volunteer,
                    "archived",
                    "Volunteer is archived for retention/privacy review.",
                    {"retention_status": retention_status}
                )

            if volunteer_id in blacklist:
                add_exclusion(
                    volunteer,
                    "blacklisted",
                    "Volunteer is on the local do-not-contact list.",
                    {"source": "blacklist"}
                )

            if volunteer_id in confirmed_duplicates:
                duplicate = confirmed_duplicates[volunteer_id]
                add_exclusion(
                    volunteer,
                    "duplicate_identity",
                    "Volunteer is a confirmed duplicate; use the canonical profile instead.",
                    {
                        "identity_id": duplicate.get("identity_id"),
                        "canonical_volunteer_id": duplicate.get("canonical_volunteer_id")
                    }
                )

            if volunteer_id in contacted:
                add_exclusion(
                    volunteer,
                    "already_contacted",
                    "Volunteer already has a sent/responded contact for this campaign.",
                    {"campaign_id": campaign.get("id")}
                )

            if volunteer_id in unsuitable_outcomes:
                add_exclusion(
                    volunteer,
                    "unsuitable_outcome",
                    "Volunteer has an outcome indicating they should not be pursued for this campaign.",
                    {"campaign_id": campaign.get("id")}
                )

            if target_categories and target_categories not in volunteer_categories:
                add_exclusion(
                    volunteer,
                    "category_mismatch",
                    "Volunteer categories do not match the campaign target category.",
                    {
                        "target_categories": campaign.get("target_categories"),
                        "volunteer_categories": volunteer.get("categories")
                    }
                )

            if target_location and target_location not in volunteer_location:
                add_exclusion(
                    volunteer,
                    "location_mismatch",
                    "Volunteer location does not match the campaign target location.",
                    {
                        "target_location": campaign.get("target_location"),
                        "volunteer_location": volunteer.get("location")
                    }
                )

            if len(exclusions) == reasons_before:
                eligible.append(volunteer)

        return {
            "eligible": eligible,
            "exclusions": exclusions,
            "excluded_volunteers": len(excluded_volunteers),
            "exclusion_counts": exclusion_counts
        }

    def _score_campaign_match(
        self,
        campaign: Dict[str, Any],
        volunteer: Dict[str, Any]
    ) -> tuple[float, str, List[str]]:
        """Score a campaign-volunteer match with human-readable reasons."""
        score = 0.0
        reasons: List[str] = []

        target_categories = (campaign.get("target_categories") or "").lower()
        volunteer_categories = (volunteer.get("categories") or "").lower()
        if target_categories and target_categories in volunteer_categories:
            score += 40
            reasons.append("Category matches campaign target.")
        elif target_categories:
            reasons.append("Category does not clearly match campaign target.")
        else:
            score += 10
            reasons.append("Campaign accepts any category.")

        target_location = (campaign.get("target_location") or "").lower()
        volunteer_location = (volunteer.get("location") or "").lower()
        if target_location and target_location in volunteer_location:
            score += 30
            reasons.append("Location matches campaign target.")
        elif target_location:
            reasons.append("Location does not clearly match campaign target.")
        else:
            score += 10
            reasons.append("Campaign accepts any location.")

        if volunteer.get("skills"):
            score += 15
            reasons.append("Volunteer profile includes skills.")
        if volunteer.get("availability"):
            score += 10
            reasons.append("Volunteer profile includes availability.")
        if volunteer.get("profile_url"):
            score += 5
            reasons.append("Source profile URL is available.")

        if score >= 70:
            status = "strong"
        elif score >= 40:
            status = "possible"
        else:
            status = "weak"

        return min(score, 100.0), status, reasons

    def _draft_counts(self, campaign_id: int) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for status in ["draft", "approved", "rejected", "sending", "sent", "failed"]:
            counts[status] = len(self.db.get_message_drafts(status=status, campaign_id=campaign_id, limit=1000))
        return counts

    def _match_counts(self, campaign_id: int) -> Dict[str, int]:
        assessments = self.db.get_match_assessments(campaign_id=campaign_id, limit=10000)
        counts: Dict[str, int] = {}
        for assessment in assessments:
            status = assessment.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _campaign_next_actions(self, summary: Dict[str, Any]) -> List[str]:
        """Produce compact operator next actions from campaign ledger state."""
        readiness = summary.get("readiness") or {}
        counts = summary.get("counts") or {}
        draft_counts = counts.get("message_drafts") or {}
        send_counts = counts.get("send_attempts") or {}
        response_counts = counts.get("responses") or {}
        follow_up_counts = counts.get("follow_ups") or {}
        match_counts = counts.get("matches") or {}
        outcome_counts = counts.get("outcomes") or {}

        if outcome_counts:
            return ["Campaign has recorded outreach outcomes; continue monitoring only if new replies arrive."]
        if draft_counts.get("draft", 0):
            return ["Review drafted messages before any external outreach."]
        if draft_counts.get("approved", 0):
            return ["Send or manually confirm approved messages when ready."]
        if send_counts.get("failed", 0):
            return ["Inspect failed send attempts and decide whether to retry manually."]
        if follow_up_counts.get("due", 0):
            return ["Approve or cancel due follow-ups."]
        if follow_up_counts.get("approved", 0):
            return ["Confirm approved follow-ups only after they are sent."]
        if response_counts and not follow_up_counts:
            return ["Review responses and create follow-ups where appropriate."]
        if not readiness.get("ready"):
            issues = readiness.get("issues") or []
            return [issue.get("message", "Resolve campaign readiness issue.") for issue in issues]
        if not match_counts:
            return ["Assess matches to explain which volunteers fit this campaign."]
        return ["Campaign ledger is current; continue monitoring responses and follow-ups."]
