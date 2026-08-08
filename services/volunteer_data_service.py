"""Retired provider-enumeration compatibility service.

The maintained candidate path is the bounded ``EnhancedScraper`` behind
runtime feature flags, or reviewed local CSV/JSON import.
"""

from __future__ import annotations

import logging
from typing import Dict, List


class VolunteerDataService:
    """Compatibility shell that refuses hidden or autonomous provider access."""

    def __init__(self, db_manager=None, credential_manager=None):
        self.db_manager = db_manager
        self.credential_manager = credential_manager
        self.logger = logging.getLogger(__name__)

    def initialize_session(self) -> bool:
        self.logger.warning("Legacy provider session initialization is disabled")
        return False

    def get_visible_volunteers(self, *args, **kwargs) -> List[Dict]:
        raise RuntimeError(
            "Legacy volunteer enumeration is retired. Use the explicitly enabled Candidate Intake workflow."
        )

    def access_hidden_volunteers_via_api(self) -> List[Dict]:
        self.logger.warning("Hidden/private volunteer enumeration is disabled")
        return []

    def _trigger_hidden_volunteer_responses(self) -> List[Dict]:
        self.logger.warning("Hidden-volunteer request posting is disabled; use the approval ledger")
        return []

    def _post_strategic_request(self, request_data):
        raise RuntimeError(
            "Request posting is disabled. Use the approval ledger and an explicit compliant provider action."
        )

    def get_all_volunteers(self):
        raise RuntimeError(
            "Autonomous all-volunteer synchronization is retired. Use bounded live search or local import."
        )

    def get_statistics(self) -> Dict:
        stats = {}
        if self.db_manager:
            getter = getattr(self.db_manager, "get_volunteer_statistics", None)
            if getter:
                stats.update(getter() or {})
        stats.update({
            "access_methods": [
                "Reviewed CSV/JSON import",
                "Bounded live search through Candidate Intake when explicitly enabled",
                "Hidden/private profile enumeration disabled",
                "Autonomous request posting disabled",
            ],
            "provider_automation_status": "review_gated",
        })
        return stats

    def close(self) -> None:
        return None
