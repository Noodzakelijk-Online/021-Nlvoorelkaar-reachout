"""Fail-safe runtime configuration for external and destructive operations."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be one of: 1, 0, true, false, yes, no, on, off")


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    value = default if raw is None else int(raw)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class RuntimeSettings:
    """Operator-controlled feature flags with conservative defaults."""

    environment: str = "production"
    live_search_enabled: bool = False
    live_send_enabled: bool = False
    google_drive_enabled: bool = False
    max_search_pages: int = 5
    max_send_batch: int = 5
    daily_send_limit: int = 20

    @classmethod
    def from_environment(cls) -> "RuntimeSettings":
        settings = cls(
            environment=os.environ.get("NLVE_ENV", "production").strip().lower(),
            live_search_enabled=_env_bool("NLVE_LIVE_SEARCH_ENABLED"),
            live_send_enabled=_env_bool("NLVE_LIVE_SEND_ENABLED"),
            google_drive_enabled=_env_bool("NLVE_GOOGLE_DRIVE_ENABLED"),
            max_search_pages=_env_int("NLVE_MAX_SEARCH_PAGES", 5, 1, 20),
            max_send_batch=_env_int("NLVE_MAX_SEND_BATCH", 5, 1, 20),
            daily_send_limit=_env_int("NLVE_DAILY_SEND_LIMIT", 20, 1, 100),
        )
        errors = settings.validate()
        if errors:
            raise ValueError("; ".join(errors))
        return settings

    def validate(self) -> List[str]:
        errors: List[str] = []
        if self.environment not in {"production", "development", "test"}:
            errors.append("NLVE_ENV must be production, development, or test")
        if self.environment == "test" and (
            self.live_search_enabled or self.live_send_enabled or self.google_drive_enabled
        ):
            errors.append("External provider features cannot be enabled when NLVE_ENV=test")
        return errors

    def public_status(self) -> Dict[str, object]:
        """Return non-secret configuration suitable for the UI and support bundles."""
        return {
            "environment": self.environment,
            "live_search_enabled": self.live_search_enabled,
            "live_send_enabled": self.live_send_enabled,
            "google_drive_enabled": self.google_drive_enabled,
            "max_search_pages": self.max_search_pages,
            "max_send_batch": self.max_send_batch,
            "daily_send_limit": self.daily_send_limit,
        }

