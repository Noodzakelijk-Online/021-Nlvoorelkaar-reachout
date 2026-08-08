"""Compatibility types for the retired automated reporting runtime.

Operational reporting in the maintained app is local and operator initiated.
Email delivery is intentionally unavailable until it has its own approval,
credential, evidence, and retry boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class ReportType(Enum):
    DAILY_SYNC = "daily_sync"
    WEEKLY_SUMMARY = "weekly_summary"
    MONTHLY_ANALYSIS = "monthly_analysis"
    VALIDATION_REPORT = "validation_report"
    PERFORMANCE_REPORT = "performance_report"
    ALERT_REPORT = "alert_report"


class NotificationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ReportConfig:
    report_type: ReportType
    enabled: bool
    schedule: str
    recipients: List[str]
    include_charts: bool
    include_raw_data: bool
    notification_level: NotificationLevel


class ReportingService:
    """Retired compatibility shell that never sends email or invents metrics."""

    RETIRED_MESSAGE = (
        "Automated reporting/email is retired. Use local exports and review the result "
        "before sharing it manually."
    )

    def __init__(self, *args, **kwargs):
        self.report_configs = {}
        self.email_config = None

    def generate_report(self, *args, **kwargs):
        raise RuntimeError(self.RETIRED_MESSAGE)

    def send_notification(self, *args, **kwargs):
        raise RuntimeError(self.RETIRED_MESSAGE)

    def configure_email(self, *args, **kwargs):
        raise RuntimeError(self.RETIRED_MESSAGE)
