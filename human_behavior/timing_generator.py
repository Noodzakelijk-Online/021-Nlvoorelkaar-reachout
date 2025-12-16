"""
Human-Like Timing Generator

Generates realistic timing patterns that mimic human behavior
for messaging and navigation activities.

Operating hours: 09:00 - 22:00
"""

import random
import time
import math
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ActivityLevel(Enum):
    """Activity intensity levels"""
    VERY_LOW = 0.3
    LOW = 0.5
    NORMAL = 1.0
    HIGH = 1.3
    VERY_HIGH = 1.5


@dataclass
class TimingConfig:
    """Configuration for timing generator"""
    # Operating hours (09:00 - 22:00)
    start_hour: int = 9
    end_hour: int = 22
    
    # Message delays (in seconds)
    min_message_delay: float = 45.0
    avg_message_delay: float = 150.0  # 2.5 minutes
    max_message_delay: float = 480.0  # 8 minutes
    
    # Typing simulation
    min_char_delay_ms: int = 50
    max_char_delay_ms: int = 150
    
    # Session parameters
    min_session_minutes: int = 15
    max_session_minutes: int = 45
    min_break_minutes: int = 5
    max_break_minutes: int = 30
    
    # Daily limits
    max_messages_per_day: int = 40
    max_sessions_per_day: int = 5


@dataclass
class DaySchedule:
    """Activity schedule for a specific day"""
    day_name: str
    activity_multiplier: float
    peak_hours: list = field(default_factory=list)
    
    # Default schedules per day of week
    @staticmethod
    def get_schedule(weekday: int) -> 'DaySchedule':
        schedules = {
            0: DaySchedule("Monday", 1.0, [(10, 12), (14, 17), (19, 21)]),
            1: DaySchedule("Tuesday", 1.0, [(9, 12), (14, 17), (19, 21)]),
            2: DaySchedule("Wednesday", 0.9, [(10, 12), (14, 16), (19, 21)]),
            3: DaySchedule("Thursday", 0.85, [(10, 12), (14, 16), (19, 20)]),
            4: DaySchedule("Friday", 0.7, [(10, 12), (14, 15), (19, 21)]),
            5: DaySchedule("Saturday", 0.5, [(11, 13), (15, 17), (19, 21)]),
            6: DaySchedule("Sunday", 0.4, [(12, 14), (16, 18), (19, 21)]),
        }
        return schedules.get(weekday, schedules[0])


class GaussianDelay:
    """
    Generates delays following a Gaussian (normal) distribution
    with configurable bounds.
    """
    
    def __init__(
        self,
        mean: float,
        std_dev: float,
        min_value: float,
        max_value: float
    ):
        self.mean = mean
        self.std_dev = std_dev
        self.min_value = min_value
        self.max_value = max_value
    
    def generate(self) -> float:
        """Generate a delay value"""
        # Generate Gaussian value
        value = random.gauss(self.mean, self.std_dev)
        
        # Clamp to bounds
        value = max(self.min_value, min(self.max_value, value))
        
        # Add small random noise for naturalness
        noise = random.uniform(-0.1, 0.1) * value
        value += noise
        
        return max(self.min_value, value)


class MessageDelayGenerator:
    """
    Generates realistic delays between messages based on
    message length and context.
    """
    
    def __init__(self, config: TimingConfig):
        self.config = config
        
        # Base delay generator
        self._base_delay = GaussianDelay(
            mean=config.avg_message_delay,
            std_dev=config.avg_message_delay * 0.4,
            min_value=config.min_message_delay,
            max_value=config.max_message_delay
        )
    
    def get_delay(
        self,
        message_length: int = 100,
        is_reply: bool = False,
        activity_level: ActivityLevel = ActivityLevel.NORMAL
    ) -> float:
        """
        Calculate delay before sending next message
        
        Args:
            message_length: Length of message to send
            is_reply: Whether this is a reply to received message
            activity_level: Current activity intensity
        
        Returns:
            Delay in seconds
        """
        # Base delay
        delay = self._base_delay.generate()
        
        # Adjust for message length (longer = more delay)
        length_factor = 1.0 + (message_length / 500)  # Up to 2x for long messages
        delay *= length_factor
        
        # Replies are typically faster
        if is_reply:
            delay *= 0.6
        
        # Adjust for activity level
        delay /= activity_level.value
        
        # Add reading time simulation
        reading_time = self._simulate_reading_time(message_length)
        delay += reading_time
        
        # Ensure within bounds
        delay = max(self.config.min_message_delay, 
                   min(self.config.max_message_delay, delay))
        
        return delay
    
    def _simulate_reading_time(self, char_count: int) -> float:
        """Simulate time to read/compose message"""
        # Average reading speed: 200-300 words per minute
        # Average word length: 5 characters
        words = char_count / 5
        reading_wpm = random.uniform(150, 250)
        reading_time = (words / reading_wpm) * 60
        
        # Add thinking time
        thinking_time = random.uniform(2, 10)
        
        return reading_time + thinking_time


class TypingSimulator:
    """
    Simulates human typing patterns with realistic
    character-by-character delays.
    """
    
    def __init__(self, config: TimingConfig):
        self.config = config
        self._fatigue_factor = 1.0
        self._chars_typed = 0
    
    def get_char_delay(self) -> float:
        """Get delay for next character in milliseconds"""
        # Base delay
        base = random.uniform(
            self.config.min_char_delay_ms,
            self.config.max_char_delay_ms
        )
        
        # Apply fatigue (typing slows over time)
        delay = base * self._fatigue_factor
        
        # Occasional pause (thinking)
        if random.random() < 0.02:  # 2% chance
            delay += random.uniform(200, 800)
        
        # Update fatigue
        self._chars_typed += 1
        if self._chars_typed > 100:
            self._fatigue_factor = min(1.5, self._fatigue_factor + 0.001)
        
        return delay
    
    def get_word_pause(self) -> float:
        """Get pause after completing a word"""
        return random.uniform(50, 200)
    
    def get_sentence_pause(self) -> float:
        """Get pause after completing a sentence"""
        return random.uniform(200, 600)
    
    def get_paragraph_pause(self) -> float:
        """Get pause after completing a paragraph"""
        return random.uniform(500, 1500)
    
    def reset_fatigue(self) -> None:
        """Reset fatigue after break"""
        self._fatigue_factor = 1.0
        self._chars_typed = 0
    
    def simulate_typing(self, text: str) -> list:
        """
        Generate timing sequence for typing text
        
        Returns:
            List of (character, delay_ms) tuples
        """
        sequence = []
        
        for i, char in enumerate(text):
            delay = self.get_char_delay()
            
            # Add pauses at word/sentence boundaries
            if char == ' ':
                delay += self.get_word_pause()
            elif char in '.!?':
                delay += self.get_sentence_pause()
            elif char == '\n':
                delay += self.get_paragraph_pause()
            
            sequence.append((char, delay))
        
        return sequence


class TimeOfDayManager:
    """
    Manages activity based on time of day within
    the 09:00-22:00 operating window.
    """
    
    def __init__(self, config: TimingConfig):
        self.config = config
    
    def is_operating_hours(self, dt: Optional[datetime] = None) -> bool:
        """Check if current time is within operating hours"""
        dt = dt or datetime.now()
        return self.config.start_hour <= dt.hour < self.config.end_hour
    
    def get_activity_level(self, dt: Optional[datetime] = None) -> ActivityLevel:
        """Get activity level for current time"""
        dt = dt or datetime.now()
        hour = dt.hour
        
        if not self.is_operating_hours(dt):
            return ActivityLevel.VERY_LOW
        
        # Get day schedule
        schedule = DaySchedule.get_schedule(dt.weekday())
        
        # Check if in peak hours
        in_peak = any(start <= hour < end for start, end in schedule.peak_hours)
        
        if in_peak:
            return ActivityLevel.HIGH
        
        # Morning ramp-up (09:00-10:00)
        if hour == self.config.start_hour:
            return ActivityLevel.LOW
        
        # Evening wind-down (21:00-22:00)
        if hour == self.config.end_hour - 1:
            return ActivityLevel.LOW
        
        return ActivityLevel.NORMAL
    
    def get_next_operating_time(self, dt: Optional[datetime] = None) -> datetime:
        """Get next time when operations can resume"""
        dt = dt or datetime.now()
        
        if self.is_operating_hours(dt):
            return dt
        
        # If before start hour today
        if dt.hour < self.config.start_hour:
            return dt.replace(
                hour=self.config.start_hour,
                minute=random.randint(0, 30),
                second=0,
                microsecond=0
            )
        
        # After end hour - next day
        next_day = dt + timedelta(days=1)
        return next_day.replace(
            hour=self.config.start_hour,
            minute=random.randint(0, 30),
            second=0,
            microsecond=0
        )
    
    def get_delay_multiplier(self, dt: Optional[datetime] = None) -> float:
        """Get delay multiplier based on time of day"""
        activity = self.get_activity_level(dt)
        
        # Higher activity = shorter delays
        multipliers = {
            ActivityLevel.VERY_LOW: 2.0,
            ActivityLevel.LOW: 1.5,
            ActivityLevel.NORMAL: 1.0,
            ActivityLevel.HIGH: 0.8,
            ActivityLevel.VERY_HIGH: 0.7
        }
        
        return multipliers.get(activity, 1.0)
    
    def should_take_break(self, session_duration_minutes: float) -> bool:
        """Determine if a break should be taken"""
        # More likely to take breaks in evening
        hour = datetime.now().hour
        
        if hour >= 20:  # After 8 PM
            break_threshold = 20  # minutes
        elif hour >= 17:  # After 5 PM
            break_threshold = 30
        else:
            break_threshold = 40
        
        if session_duration_minutes >= break_threshold:
            return random.random() < 0.7  # 70% chance
        
        # Random chance of early break
        return random.random() < 0.1  # 10% chance


class SessionTimer:
    """
    Tracks session timing and manages work/break cycles.
    """
    
    def __init__(self, config: TimingConfig):
        self.config = config
        self._session_start: Optional[datetime] = None
        self._session_messages: int = 0
        self._total_messages_today: int = 0
        self._sessions_today: int = 0
        self._last_reset_date: Optional[datetime] = None
        self._in_break: bool = False
        self._break_end: Optional[datetime] = None
    
    def start_session(self) -> None:
        """Start a new session"""
        self._check_daily_reset()
        
        self._session_start = datetime.now()
        self._session_messages = 0
        self._sessions_today += 1
        self._in_break = False
        
        logger.info(f"Session {self._sessions_today} started")
    
    def end_session(self) -> None:
        """End current session"""
        if self._session_start:
            duration = (datetime.now() - self._session_start).total_seconds() / 60
            logger.info(f"Session ended after {duration:.1f} minutes, "
                       f"{self._session_messages} messages")
        
        self._session_start = None
    
    def start_break(self, duration_minutes: Optional[float] = None) -> float:
        """
        Start a break
        
        Returns:
            Break duration in minutes
        """
        if duration_minutes is None:
            duration_minutes = random.uniform(
                self.config.min_break_minutes,
                self.config.max_break_minutes
            )
        
        self._in_break = True
        self._break_end = datetime.now() + timedelta(minutes=duration_minutes)
        
        logger.info(f"Break started for {duration_minutes:.1f} minutes")
        return duration_minutes
    
    def is_in_break(self) -> bool:
        """Check if currently in break"""
        if not self._in_break:
            return False
        
        if datetime.now() >= self._break_end:
            self._in_break = False
            return False
        
        return True
    
    def get_break_remaining(self) -> float:
        """Get remaining break time in seconds"""
        if not self._in_break or not self._break_end:
            return 0
        
        remaining = (self._break_end - datetime.now()).total_seconds()
        return max(0, remaining)
    
    def record_message(self) -> None:
        """Record that a message was sent"""
        self._session_messages += 1
        self._total_messages_today += 1
    
    def get_session_duration(self) -> float:
        """Get current session duration in minutes"""
        if not self._session_start:
            return 0
        return (datetime.now() - self._session_start).total_seconds() / 60
    
    def should_end_session(self) -> Tuple[bool, str]:
        """
        Check if session should end
        
        Returns:
            (should_end, reason)
        """
        # Check daily limits
        if self._total_messages_today >= self.config.max_messages_per_day:
            return True, "daily_message_limit"
        
        if self._sessions_today >= self.config.max_sessions_per_day:
            return True, "daily_session_limit"
        
        # Check session duration
        duration = self.get_session_duration()
        max_duration = random.uniform(
            self.config.min_session_minutes,
            self.config.max_session_minutes
        )
        
        if duration >= max_duration:
            return True, "session_duration"
        
        # Random chance of ending (fatigue simulation)
        if duration > 20 and random.random() < 0.05:
            return True, "fatigue"
        
        return False, ""
    
    def can_send_message(self) -> Tuple[bool, str]:
        """
        Check if a message can be sent
        
        Returns:
            (can_send, reason_if_not)
        """
        self._check_daily_reset()
        
        if self._in_break:
            return False, "in_break"
        
        if self._total_messages_today >= self.config.max_messages_per_day:
            return False, "daily_limit_reached"
        
        if not self._session_start:
            return False, "no_active_session"
        
        return True, ""
    
    def get_stats(self) -> dict:
        """Get session statistics"""
        return {
            'session_active': self._session_start is not None,
            'session_duration_minutes': self.get_session_duration(),
            'session_messages': self._session_messages,
            'total_messages_today': self._total_messages_today,
            'sessions_today': self._sessions_today,
            'in_break': self._in_break,
            'break_remaining_seconds': self.get_break_remaining(),
            'messages_remaining_today': max(0, 
                self.config.max_messages_per_day - self._total_messages_today)
        }
    
    def _check_daily_reset(self) -> None:
        """Reset daily counters if new day"""
        today = datetime.now().date()
        
        if self._last_reset_date != today:
            self._total_messages_today = 0
            self._sessions_today = 0
            self._last_reset_date = today
            logger.info("Daily counters reset")


class HumanTimingEngine:
    """
    Main timing engine that coordinates all timing components
    for human-like behavior.
    """
    
    def __init__(self, config: Optional[TimingConfig] = None):
        self.config = config or TimingConfig()
        
        self.message_delay = MessageDelayGenerator(self.config)
        self.typing = TypingSimulator(self.config)
        self.time_of_day = TimeOfDayManager(self.config)
        self.session = SessionTimer(self.config)
        
        self._last_action_time: Optional[datetime] = None
    
    def wait_for_operating_hours(self) -> bool:
        """
        Wait until operating hours if necessary
        
        Returns:
            True if waited, False if already in operating hours
        """
        if self.time_of_day.is_operating_hours():
            return False
        
        next_time = self.time_of_day.get_next_operating_time()
        wait_seconds = (next_time - datetime.now()).total_seconds()
        
        logger.info(f"Outside operating hours. Waiting until {next_time}")
        
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        
        return True
    
    def get_message_delay(
        self,
        message_length: int = 100,
        is_reply: bool = False
    ) -> float:
        """Get delay before sending next message"""
        # Base delay
        delay = self.message_delay.get_delay(
            message_length=message_length,
            is_reply=is_reply,
            activity_level=self.time_of_day.get_activity_level()
        )
        
        # Apply time-of-day multiplier
        delay *= self.time_of_day.get_delay_multiplier()
        
        return delay
    
    def wait_before_message(
        self,
        message_length: int = 100,
        is_reply: bool = False,
        callback: Optional[Callable[[float], None]] = None
    ) -> None:
        """
        Wait appropriate time before sending message
        
        Args:
            message_length: Length of message to send
            is_reply: Whether this is a reply
            callback: Optional callback with remaining time
        """
        delay = self.get_message_delay(message_length, is_reply)
        
        logger.debug(f"Waiting {delay:.1f}s before message")
        
        if callback:
            # Wait with progress updates
            start = time.monotonic()
            while time.monotonic() - start < delay:
                remaining = delay - (time.monotonic() - start)
                callback(remaining)
                time.sleep(min(1.0, remaining))
        else:
            time.sleep(delay)
        
        self._last_action_time = datetime.now()
    
    def simulate_typing_delay(self, text: str) -> float:
        """
        Get total time to simulate typing text
        
        Returns:
            Total delay in seconds
        """
        sequence = self.typing.simulate_typing(text)
        total_ms = sum(delay for _, delay in sequence)
        return total_ms / 1000
    
    def should_take_break(self) -> bool:
        """Check if a break should be taken"""
        duration = self.session.get_session_duration()
        return self.time_of_day.should_take_break(duration)
    
    def get_break_duration(self) -> float:
        """Get recommended break duration in minutes"""
        base = random.uniform(
            self.config.min_break_minutes,
            self.config.max_break_minutes
        )
        
        # Longer breaks in evening
        hour = datetime.now().hour
        if hour >= 20:
            base *= 1.3
        
        return base
    
    def start_session(self) -> bool:
        """
        Start a new session
        
        Returns:
            True if session started, False if cannot start
        """
        # Wait for operating hours
        self.wait_for_operating_hours()
        
        # Check if can start
        if self.session._sessions_today >= self.config.max_sessions_per_day:
            logger.warning("Daily session limit reached")
            return False
        
        self.session.start_session()
        self.typing.reset_fatigue()
        
        return True
    
    def end_session(self, take_break: bool = True) -> Optional[float]:
        """
        End current session
        
        Args:
            take_break: Whether to start a break
        
        Returns:
            Break duration in minutes if break started
        """
        self.session.end_session()
        
        if take_break:
            duration = self.get_break_duration()
            self.session.start_break(duration)
            return duration
        
        return None
    
    def can_continue(self) -> Tuple[bool, str]:
        """
        Check if operations can continue
        
        Returns:
            (can_continue, reason_if_not)
        """
        # Check operating hours
        if not self.time_of_day.is_operating_hours():
            return False, "outside_operating_hours"
        
        # Check session
        can_send, reason = self.session.can_send_message()
        if not can_send:
            return False, reason
        
        # Check if session should end
        should_end, reason = self.session.should_end_session()
        if should_end:
            return False, f"session_should_end:{reason}"
        
        return True, ""
    
    def get_status(self) -> dict:
        """Get comprehensive timing status"""
        return {
            'operating_hours': self.time_of_day.is_operating_hours(),
            'activity_level': self.time_of_day.get_activity_level().name,
            'session': self.session.get_stats(),
            'current_time': datetime.now().isoformat(),
            'next_operating_time': self.time_of_day.get_next_operating_time().isoformat()
        }


# Global instance
_timing_engine: Optional[HumanTimingEngine] = None


def get_timing_engine(config: Optional[TimingConfig] = None) -> HumanTimingEngine:
    """Get global timing engine instance"""
    global _timing_engine
    if _timing_engine is None:
        _timing_engine = HumanTimingEngine(config)
    return _timing_engine
