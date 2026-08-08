"""Compatibility model for the retired autonomous synchronization service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class ChangeType(Enum):
    NEW_VOLUNTEER = "new_volunteer"
    REMOVED_VOLUNTEER = "removed_volunteer"
    UPDATED_VOLUNTEER = "updated_volunteer"
    PROFILE_CHANGE = "profile_change"
    CONTACT_CHANGE = "contact_change"


@dataclass
class VolunteerChange:
    volunteer_id: str
    change_type: ChangeType
    old_data: Optional[Dict]
    new_data: Optional[Dict]
    detected_at: datetime
    field_changes: List[str]


@dataclass
class SyncReport:
    sync_date: datetime
    total_volunteers_before: int
    total_volunteers_after: int
    new_volunteers: int
    removed_volunteers: int
    updated_volunteers: int
    changes_detected: List[VolunteerChange]
    sync_duration: float
    success: bool
    errors: List[str]


class SyncService:
    """Read-only compatibility surface; provider synchronization is disabled."""

    def __init__(self, volunteer_service=None, db_manager=None, backup_manager=None):
        self.volunteer_service = volunteer_service
        self.db_manager = db_manager
        self.backup_manager = backup_manager
        self.last_sync_time = None
        self.sync_in_progress = False
        self.sync_history: List[SyncReport] = []

    async def perform_daily_sync(self) -> SyncReport:
        raise RuntimeError(
            "Autonomous provider synchronization is retired. Use Candidate Intake with explicit "
            "operator control and review-gated persistence."
        )

    def get_sync_history(self, days: int = 30) -> List[SyncReport]:
        cutoff = datetime.now() - timedelta(days=max(1, int(days)))
        return [report for report in self.sync_history if report.sync_date >= cutoff]

    def get_comprehensive_statistics(self) -> Dict:
        return {
            "status": "retired",
            "automatic_provider_sync": False,
            "sync_in_progress": False,
            "completed_runs": len(self.sync_history),
        }

    def get_database_integrity_report(self) -> Dict:
        if self.db_manager and hasattr(self.db_manager, "get_database_health"):
            return self.db_manager.get_database_health()
        return {"ready": False, "reason": "database health adapter unavailable"}
