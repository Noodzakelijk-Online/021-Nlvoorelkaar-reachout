"""Retired campaign compatibility types.

Campaign execution moved to ``OutreachLedger``. This module keeps old imports
loadable while refusing every external mutation path.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class CampaignStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MessageType(Enum):
    DIRECT_MESSAGE = "direct_message"
    REQUEST_POST = "request_post"
    RESPONSE_TRIGGER = "response_trigger"


@dataclass
class CampaignTarget:
    locations: List[str]
    categories: List[str]
    skills: List[str]
    volunteer_types: List[str]
    max_volunteers: int
    exclude_contacted: bool = True


@dataclass
class CampaignMessage:
    subject: str
    content: str
    message_type: MessageType
    personalization_fields: List[str]


class CampaignManager:
    """Compatibility shell that directs callers to the review-gated ledger."""

    RETIRED_MESSAGE = (
        "Legacy CampaignManager execution is retired. Use the outreach ledger so every "
        "message has a reviewed draft, explicit approval, evidence, and audit history."
    )

    def __init__(self, *args, **kwargs):
        self.active_campaigns = {}

    def create_campaign(self, *args, **kwargs):
        raise RuntimeError(self.RETIRED_MESSAGE)

    def start_campaign(self, *args, **kwargs):
        raise RuntimeError(self.RETIRED_MESSAGE)

    async def _send_platform_message(self, volunteer, message):
        raise RuntimeError(self.RETIRED_MESSAGE)

    async def _post_platform_request(self, request_data):
        raise RuntimeError(self.RETIRED_MESSAGE)
