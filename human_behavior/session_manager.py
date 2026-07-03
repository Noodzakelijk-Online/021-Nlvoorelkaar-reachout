"""
Human-Like Session Manager

Manages work sessions with realistic patterns including warm-up periods,
breaks, wind-down, and daily/weekly quota tracking.
"""

import random
import time
import json
import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session states"""
    IDLE = "idle"
    WARMING_UP = "warming_up"
    ACTIVE = "active"
    COOLING_DOWN = "cooling_down"
    ON_BREAK = "on_break"
    ENDED = "ended"


class ActivityType(Enum):
    """Types of activities for quota tracking"""
    MESSAGE_SENT = "message_sent"
    PROFILE_VIEWED = "profile_viewed"
    SEARCH_PERFORMED = "search_performed"
    PAGE_NAVIGATED = "page_navigated"


@dataclass
class QuotaLimits:
    """Daily and session quota limits"""
    # Daily limits
    max_messages_per_day: int = 40
    max_profiles_per_day: int = 150
    max_searches_per_day: int = 50
    max_active_hours_per_day: float = 4.0
    
    # Session limits
    max_messages_per_session: int = 15
    max_profiles_per_session: int = 50
    max_session_minutes: int = 45
    min_session_minutes: int = 15
    
    # Weekly limits
    max_messages_per_week: int = 200
    max_active_days_per_week: int = 6
    
    # Break requirements
    min_break_minutes: int = 5
    max_break_minutes: int = 30
    break_after_messages: int = 10


@dataclass
class SessionStats:
    """Statistics for current session"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    messages_sent: int = 0
    profiles_viewed: int = 0
    searches_performed: int = 0
    pages_navigated: int = 0
    breaks_taken: int = 0
    total_break_minutes: float = 0
    
    def duration_minutes(self) -> float:
        if not self.start_time:
            return 0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() / 60


@dataclass
class DailyStats:
    """Statistics for a single day"""
    date: str
    sessions: int = 0
    messages_sent: int = 0
    profiles_viewed: int = 0
    searches_performed: int = 0
    active_minutes: float = 0
    break_minutes: float = 0
    
    @classmethod
    def for_today(cls) -> 'DailyStats':
        return cls(date=date.today().isoformat())


@dataclass
class WeeklyStats:
    """Statistics for a week"""
    week_start: str
    days_active: int = 0
    total_messages: int = 0
    total_profiles: int = 0
    total_active_minutes: float = 0


class QuotaTracker:
    """
    Tracks and enforces activity quotas
    """
    
    def __init__(
        self,
        limits: Optional[QuotaLimits] = None,
        storage_path: Optional[str] = None
    ):
        self.limits = limits or QuotaLimits()
        self.storage_path = Path(storage_path) if storage_path else None
        
        self._daily_stats: Dict[str, DailyStats] = {}
        self._weekly_stats: Dict[str, WeeklyStats] = {}
        self._session_stats: Optional[SessionStats] = None
        
        self._load_stats()
    
    def start_session(self) -> SessionStats:
        """Start a new session"""
        self._session_stats = SessionStats(start_time=datetime.now())
        
        # Update daily stats
        today = self._get_today_stats()
        today.sessions += 1
        
        self._save_stats()
        return self._session_stats
    
    def end_session(self) -> SessionStats:
        """End current session"""
        if self._session_stats:
            self._session_stats.end_time = datetime.now()
            
            # Update daily stats
            today = self._get_today_stats()
            today.active_minutes += self._session_stats.duration_minutes()
            today.break_minutes += self._session_stats.total_break_minutes
            
            self._save_stats()
        
        stats = self._session_stats
        self._session_stats = None
        return stats
    
    def record_activity(self, activity_type: ActivityType) -> bool:
        """
        Record an activity and check if within limits
        
        Returns:
            True if activity allowed, False if quota exceeded
        """
        if not self._session_stats:
            return False
        
        # Check limits before recording
        if not self.can_perform_activity(activity_type):
            return False
        
        # Record activity
        today = self._get_today_stats()
        
        if activity_type == ActivityType.MESSAGE_SENT:
            self._session_stats.messages_sent += 1
            today.messages_sent += 1
        elif activity_type == ActivityType.PROFILE_VIEWED:
            self._session_stats.profiles_viewed += 1
            today.profiles_viewed += 1
        elif activity_type == ActivityType.SEARCH_PERFORMED:
            self._session_stats.searches_performed += 1
            today.searches_performed += 1
        elif activity_type == ActivityType.PAGE_NAVIGATED:
            self._session_stats.pages_navigated += 1
        
        self._save_stats()
        return True
    
    def can_perform_activity(self, activity_type: ActivityType) -> bool:
        """Check if activity is within quota limits"""
        if not self._session_stats:
            return False
        
        today = self._get_today_stats()
        week = self._get_week_stats()
        
        if activity_type == ActivityType.MESSAGE_SENT:
            # Check all message limits
            if self._session_stats.messages_sent >= self.limits.max_messages_per_session:
                logger.warning("Session message limit reached")
                return False
            if today.messages_sent >= self.limits.max_messages_per_day:
                logger.warning("Daily message limit reached")
                return False
            if week.total_messages >= self.limits.max_messages_per_week:
                logger.warning("Weekly message limit reached")
                return False
        
        elif activity_type == ActivityType.PROFILE_VIEWED:
            if self._session_stats.profiles_viewed >= self.limits.max_profiles_per_session:
                return False
            if today.profiles_viewed >= self.limits.max_profiles_per_day:
                return False
        
        elif activity_type == ActivityType.SEARCH_PERFORMED:
            if today.searches_performed >= self.limits.max_searches_per_day:
                return False
        
        # Check time limits
        if today.active_minutes >= self.limits.max_active_hours_per_day * 60:
            logger.warning("Daily active time limit reached")
            return False
        
        if self._session_stats.duration_minutes() >= self.limits.max_session_minutes:
            logger.warning("Session time limit reached")
            return False
        
        return True
    
    def should_take_break(self) -> Tuple[bool, str]:
        """
        Check if a break should be taken
        
        Returns:
            (should_break, reason)
        """
        if not self._session_stats:
            return False, ""
        
        # Check message count
        if self._session_stats.messages_sent > 0:
            if self._session_stats.messages_sent % self.limits.break_after_messages == 0:
                return True, "message_count"
        
        # Check session duration
        duration = self._session_stats.duration_minutes()
        if duration >= self.limits.min_session_minutes:
            # Increasing probability of break as session goes on
            break_probability = (duration - self.limits.min_session_minutes) / 30
            if random.random() < break_probability:
                return True, "duration"
        
        return False, ""
    
    def record_break(self, duration_minutes: float) -> None:
        """Record a break"""
        if self._session_stats:
            self._session_stats.breaks_taken += 1
            self._session_stats.total_break_minutes += duration_minutes
            self._save_stats()
    
    def get_remaining_quota(self) -> Dict[str, int]:
        """Get remaining quota for today"""
        today = self._get_today_stats()
        
        return {
            'messages': max(0, self.limits.max_messages_per_day - today.messages_sent),
            'profiles': max(0, self.limits.max_profiles_per_day - today.profiles_viewed),
            'searches': max(0, self.limits.max_searches_per_day - today.searches_performed),
            'active_minutes': max(0, int(self.limits.max_active_hours_per_day * 60 - today.active_minutes))
        }
    
    def get_session_stats(self) -> Optional[SessionStats]:
        """Get current session statistics"""
        return self._session_stats
    
    def get_daily_stats(self, date_str: Optional[str] = None) -> DailyStats:
        """Get statistics for a specific day"""
        if date_str is None:
            return self._get_today_stats()
        return self._daily_stats.get(date_str, DailyStats(date=date_str))
    
    def _get_today_stats(self) -> DailyStats:
        """Get or create today's stats"""
        today = date.today().isoformat()
        if today not in self._daily_stats:
            self._daily_stats[today] = DailyStats.for_today()
        return self._daily_stats[today]
    
    def _get_week_stats(self) -> WeeklyStats:
        """Get or create this week's stats"""
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()
        
        if week_start not in self._weekly_stats:
            self._weekly_stats[week_start] = WeeklyStats(week_start=week_start)
        
        # Update from daily stats
        week = self._weekly_stats[week_start]
        week.total_messages = sum(
            d.messages_sent for d in self._daily_stats.values()
            if d.date >= week_start
        )
        week.total_profiles = sum(
            d.profiles_viewed for d in self._daily_stats.values()
            if d.date >= week_start
        )
        week.days_active = len([
            d for d in self._daily_stats.values()
            if d.date >= week_start and d.active_minutes > 0
        ])
        
        return week
    
    def _load_stats(self) -> None:
        """Load stats from storage"""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            for date_str, stats in data.get('daily', {}).items():
                self._daily_stats[date_str] = DailyStats(**stats)
            
            for week_str, stats in data.get('weekly', {}).items():
                self._weekly_stats[week_str] = WeeklyStats(**stats)
        except (json.JSONDecodeError, OSError, AttributeError, TypeError) as e:
            logger.error(f"Failed to load stats: {e}")
    
    def _save_stats(self) -> None:
        """Save stats to storage"""
        if not self.storage_path:
            return
        
        try:
            # Keep only last 30 days
            cutoff = (date.today() - timedelta(days=30)).isoformat()
            daily = {k: asdict(v) for k, v in self._daily_stats.items() if k >= cutoff}
            
            # Keep only last 8 weeks
            week_cutoff = (date.today() - timedelta(weeks=8)).isoformat()
            weekly = {k: asdict(v) for k, v in self._weekly_stats.items() if k >= week_cutoff}
            
            data = {'daily': daily, 'weekly': weekly}
            
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except (OSError, AttributeError, TypeError, ValueError) as e:
            logger.error(f"Failed to save stats: {e}")


class SessionManager:
    """
    Manages human-like work sessions with warm-up, breaks, and wind-down
    """
    
    def __init__(
        self,
        quota_limits: Optional[QuotaLimits] = None,
        storage_path: Optional[str] = None
    ):
        self.quota = QuotaTracker(quota_limits, storage_path)
        self.limits = quota_limits or QuotaLimits()
        
        self._state = SessionState.IDLE
        self._session_start: Optional[datetime] = None
        self._break_end: Optional[datetime] = None
        self._warmup_end: Optional[datetime] = None
        self._cooldown_start: Optional[datetime] = None
        
        self._activity_callbacks: List[Callable] = []
        self._state_callbacks: List[Callable] = []
    
    @property
    def state(self) -> SessionState:
        return self._state
    
    def start_session(self) -> bool:
        """
        Start a new session with warm-up period
        
        Returns:
            True if session started, False if cannot start
        """
        if self._state not in [SessionState.IDLE, SessionState.ENDED]:
            logger.warning(f"Cannot start session in state {self._state}")
            return False
        
        # Check if we can start (daily limits)
        remaining = self.quota.get_remaining_quota()
        if remaining['messages'] <= 0:
            logger.warning("Daily message quota exhausted")
            return False
        
        if remaining['active_minutes'] <= 0:
            logger.warning("Daily active time exhausted")
            return False
        
        # Start session
        self.quota.start_session()
        self._session_start = datetime.now()
        
        # Warm-up period (2-5 minutes of slower activity)
        warmup_duration = random.uniform(2, 5)
        self._warmup_end = datetime.now() + timedelta(minutes=warmup_duration)
        
        self._set_state(SessionState.WARMING_UP)
        
        logger.info(f"Session started with {warmup_duration:.1f}min warm-up")
        return True
    
    def end_session(self) -> SessionStats:
        """End the current session"""
        stats = self.quota.end_session()
        
        self._set_state(SessionState.ENDED)
        self._session_start = None
        self._warmup_end = None
        self._cooldown_start = None
        
        logger.info(f"Session ended: {stats.messages_sent} messages, "
                   f"{stats.duration_minutes():.1f} minutes")
        
        return stats
    
    def start_break(self, duration_minutes: Optional[float] = None) -> float:
        """
        Start a break
        
        Args:
            duration_minutes: Break duration (random if None)
        
        Returns:
            Actual break duration in minutes
        """
        if duration_minutes is None:
            duration_minutes = random.uniform(
                self.limits.min_break_minutes,
                self.limits.max_break_minutes
            )
        
        self._break_end = datetime.now() + timedelta(minutes=duration_minutes)
        self._set_state(SessionState.ON_BREAK)
        
        self.quota.record_break(duration_minutes)
        
        logger.info(f"Break started for {duration_minutes:.1f} minutes")
        return duration_minutes
    
    def check_break_ended(self) -> bool:
        """Check if break has ended"""
        if self._state != SessionState.ON_BREAK:
            return True
        
        if datetime.now() >= self._break_end:
            self._set_state(SessionState.ACTIVE)
            logger.info("Break ended, resuming activity")
            return True
        
        return False
    
    def get_break_remaining(self) -> float:
        """Get remaining break time in seconds"""
        if self._state != SessionState.ON_BREAK or not self._break_end:
            return 0
        
        remaining = (self._break_end - datetime.now()).total_seconds()
        return max(0, remaining)
    
    def update_state(self) -> SessionState:
        """
        Update and return current session state
        
        Handles automatic state transitions
        """
        if self._state == SessionState.WARMING_UP:
            if datetime.now() >= self._warmup_end:
                self._set_state(SessionState.ACTIVE)
                logger.info("Warm-up complete, now active")
        
        elif self._state == SessionState.ON_BREAK:
            self.check_break_ended()
        
        elif self._state == SessionState.ACTIVE:
            # Check if should transition to cooling down
            stats = self.quota.get_session_stats()
            if stats:
                duration = stats.duration_minutes()
                time_remaining = self.limits.max_session_minutes - duration
                
                if time_remaining <= 5:  # Last 5 minutes
                    self._cooldown_start = datetime.now()
                    self._set_state(SessionState.COOLING_DOWN)
                    logger.info("Entering cool-down phase")
        
        elif self._state == SessionState.COOLING_DOWN:
            # Check if session should end
            stats = self.quota.get_session_stats()
            if stats and stats.duration_minutes() >= self.limits.max_session_minutes:
                self.end_session()
        
        return self._state
    
    def can_send_message(self) -> Tuple[bool, str]:
        """
        Check if a message can be sent
        
        Returns:
            (can_send, reason_if_not)
        """
        self.update_state()
        
        if self._state == SessionState.IDLE:
            return False, "no_active_session"
        
        if self._state == SessionState.ON_BREAK:
            return False, "on_break"
        
        if self._state == SessionState.ENDED:
            return False, "session_ended"
        
        if not self.quota.can_perform_activity(ActivityType.MESSAGE_SENT):
            return False, "quota_exceeded"
        
        return True, ""
    
    def record_message_sent(self) -> bool:
        """Record that a message was sent"""
        success = self.quota.record_activity(ActivityType.MESSAGE_SENT)
        
        if success:
            # Check if break needed
            should_break, reason = self.quota.should_take_break()
            if should_break:
                logger.info(f"Break recommended: {reason}")
        
        return success
    
    def record_profile_viewed(self) -> bool:
        """Record that a profile was viewed"""
        return self.quota.record_activity(ActivityType.PROFILE_VIEWED)
    
    def record_search(self) -> bool:
        """Record that a search was performed"""
        return self.quota.record_activity(ActivityType.SEARCH_PERFORMED)
    
    def get_activity_speed_multiplier(self) -> float:
        """
        Get speed multiplier based on session phase
        
        Returns:
            Multiplier (< 1 = slower, > 1 = faster)
        """
        if self._state == SessionState.WARMING_UP:
            # Gradually increase speed during warm-up
            if self._warmup_end:
                progress = 1 - (self._warmup_end - datetime.now()).total_seconds() / 300
                return 0.5 + (0.5 * progress)  # 0.5 -> 1.0
            return 0.5
        
        elif self._state == SessionState.COOLING_DOWN:
            # Gradually decrease speed during cool-down
            if self._cooldown_start:
                elapsed = (datetime.now() - self._cooldown_start).total_seconds() / 60
                return max(0.5, 1.0 - (elapsed * 0.1))  # 1.0 -> 0.5
            return 0.7
        
        elif self._state == SessionState.ACTIVE:
            # Normal speed with slight variation
            return random.uniform(0.9, 1.1)
        
        return 1.0
    
    def get_recommended_delay(self, base_delay: float) -> float:
        """
        Get recommended delay adjusted for session phase
        
        Args:
            base_delay: Base delay in seconds
        
        Returns:
            Adjusted delay in seconds
        """
        multiplier = self.get_activity_speed_multiplier()
        
        # Invert multiplier for delays (slower = longer delays)
        delay_multiplier = 1 / multiplier if multiplier > 0 else 2.0
        
        return base_delay * delay_multiplier
    
    def should_take_break(self) -> Tuple[bool, str]:
        """Check if a break should be taken"""
        return self.quota.should_take_break()
    
    def get_status(self) -> Dict:
        """Get comprehensive session status"""
        stats = self.quota.get_session_stats()
        remaining = self.quota.get_remaining_quota()
        
        return {
            'state': self._state.value,
            'session_active': self._state not in [SessionState.IDLE, SessionState.ENDED],
            'session_duration_minutes': stats.duration_minutes() if stats else 0,
            'messages_sent_session': stats.messages_sent if stats else 0,
            'profiles_viewed_session': stats.profiles_viewed if stats else 0,
            'breaks_taken': stats.breaks_taken if stats else 0,
            'remaining_messages_today': remaining['messages'],
            'remaining_profiles_today': remaining['profiles'],
            'remaining_minutes_today': remaining['active_minutes'],
            'speed_multiplier': self.get_activity_speed_multiplier(),
            'break_remaining_seconds': self.get_break_remaining()
        }
    
    def on_state_change(self, callback: Callable[[SessionState], None]) -> None:
        """Register callback for state changes"""
        self._state_callbacks.append(callback)
    
    def _set_state(self, new_state: SessionState) -> None:
        """Set state and notify callbacks"""
        old_state = self._state
        self._state = new_state
        
        for callback in self._state_callbacks:
            try:
                callback(new_state)
            except (TypeError, RuntimeError, ValueError) as e:
                logger.error(f"State callback error: {e}")


class GradualScaling:
    """
    Manages gradual scaling of activity for new accounts
    """
    
    def __init__(self, account_created: datetime):
        self.account_created = account_created
    
    def get_scaling_factor(self) -> float:
        """
        Get activity scaling factor based on account age
        
        Returns:
            Factor between 0.3 and 1.0
        """
        age_days = (datetime.now() - self.account_created).days
        
        if age_days < 7:
            # Week 1: Very conservative (30-50%)
            return 0.3 + (age_days / 7) * 0.2
        elif age_days < 14:
            # Week 2: Building up (50-70%)
            return 0.5 + ((age_days - 7) / 7) * 0.2
        elif age_days < 30:
            # Weeks 3-4: Almost normal (70-90%)
            return 0.7 + ((age_days - 14) / 16) * 0.2
        else:
            # After 1 month: Full capacity
            return 1.0
    
    def apply_to_limits(self, limits: QuotaLimits) -> QuotaLimits:
        """Apply scaling to quota limits"""
        factor = self.get_scaling_factor()
        
        return QuotaLimits(
            max_messages_per_day=int(limits.max_messages_per_day * factor),
            max_profiles_per_day=int(limits.max_profiles_per_day * factor),
            max_searches_per_day=int(limits.max_searches_per_day * factor),
            max_active_hours_per_day=limits.max_active_hours_per_day * factor,
            max_messages_per_session=int(limits.max_messages_per_session * factor),
            max_profiles_per_session=int(limits.max_profiles_per_session * factor),
            max_session_minutes=limits.max_session_minutes,  # Keep same
            min_session_minutes=limits.min_session_minutes,
            max_messages_per_week=int(limits.max_messages_per_week * factor),
            max_active_days_per_week=limits.max_active_days_per_week,
            min_break_minutes=limits.min_break_minutes,
            max_break_minutes=limits.max_break_minutes,
            break_after_messages=max(5, int(limits.break_after_messages * factor))
        )


# Global instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(
    storage_path: Optional[str] = None
) -> SessionManager:
    """Get global session manager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(storage_path=storage_path)
    return _session_manager
