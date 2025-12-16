"""
Human Behavior Engine

A comprehensive system for mimicking human behavior in automated messaging,
including realistic timing, content variation, interaction patterns,
session management, and controlled imperfections.

Operating Hours: 09:00 - 22:00
"""

import logging
import time
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Callable, Any
from dataclasses import dataclass
from pathlib import Path

from .timing_generator import (
    HumanTimingEngine,
    TimingConfig,
    ActivityLevel,
    get_timing_engine
)
from .content_variator import (
    ContentVariator,
    VolunteerProfile,
    PersonalizationLevel,
    DutchSynonyms,
    DutchGreetings,
    DutchClosings
)
from .interaction_simulator import (
    InteractionSimulator,
    MousePathGenerator,
    KeyboardSimulator,
    ScrollSimulator,
    Point,
    get_interaction_simulator
)
from .session_manager import (
    SessionManager,
    SessionState,
    QuotaLimits,
    QuotaTracker,
    ActivityType,
    GradualScaling,
    get_session_manager
)
from .imperfections import (
    ImperfectionEngine,
    ImperfectionConfig,
    get_imperfection_engine,
    add_imperfections
)

logger = logging.getLogger(__name__)


@dataclass
class HumanBehaviorConfig:
    """Master configuration for human behavior engine"""
    
    # Operating hours (09:00 - 22:00)
    start_hour: int = 9
    end_hour: int = 22
    
    # Message timing
    min_message_delay_seconds: float = 45
    avg_message_delay_seconds: float = 150
    max_message_delay_seconds: float = 480
    
    # Session settings
    max_messages_per_day: int = 40
    max_messages_per_session: int = 15
    max_session_minutes: int = 45
    min_session_minutes: int = 15
    
    # Break settings
    min_break_minutes: int = 5
    max_break_minutes: int = 30
    break_after_messages: int = 10
    
    # Imperfection rates
    typo_rate: float = 0.02
    correction_rate: float = 0.8
    hesitation_rate: float = 0.05
    
    # Content variation
    synonym_intensity: float = 0.2
    personalization_level: str = "location"
    formal_language: bool = True
    
    # Storage
    stats_storage_path: Optional[str] = None


class HumanBehaviorEngine:
    """
    Master engine that coordinates all human behavior components
    for realistic automated messaging.
    """
    
    def __init__(
        self,
        config: Optional[HumanBehaviorConfig] = None,
        sender_name: str = ""
    ):
        self.config = config or HumanBehaviorConfig()
        self.sender_name = sender_name
        
        # Initialize sub-components
        self._init_timing()
        self._init_session()
        self._init_content()
        self._init_interaction()
        self._init_imperfections()
        
        self._message_count = 0
        self._last_message_time: Optional[datetime] = None
        self._callbacks: Dict[str, List[Callable]] = {
            'before_message': [],
            'after_message': [],
            'on_break': [],
            'on_session_end': [],
            'on_error': []
        }
    
    def _init_timing(self) -> None:
        """Initialize timing components"""
        timing_config = TimingConfig(
            start_hour=self.config.start_hour,
            end_hour=self.config.end_hour,
            min_message_delay=self.config.min_message_delay_seconds,
            avg_message_delay=self.config.avg_message_delay_seconds,
            max_message_delay=self.config.max_message_delay_seconds,
            min_session_minutes=self.config.min_session_minutes,
            max_session_minutes=self.config.max_session_minutes,
            min_break_minutes=self.config.min_break_minutes,
            max_break_minutes=self.config.max_break_minutes,
            max_messages_per_day=self.config.max_messages_per_day
        )
        self.timing = HumanTimingEngine(timing_config)
    
    def _init_session(self) -> None:
        """Initialize session management"""
        quota_limits = QuotaLimits(
            max_messages_per_day=self.config.max_messages_per_day,
            max_messages_per_session=self.config.max_messages_per_session,
            max_session_minutes=self.config.max_session_minutes,
            min_session_minutes=self.config.min_session_minutes,
            min_break_minutes=self.config.min_break_minutes,
            max_break_minutes=self.config.max_break_minutes,
            break_after_messages=self.config.break_after_messages
        )
        self.session = SessionManager(
            quota_limits=quota_limits,
            storage_path=self.config.stats_storage_path
        )
    
    def _init_content(self) -> None:
        """Initialize content variation"""
        self.content = ContentVariator(self.sender_name)
    
    def _init_interaction(self) -> None:
        """Initialize interaction simulation"""
        self.interaction = InteractionSimulator()
    
    def _init_imperfections(self) -> None:
        """Initialize imperfection generation"""
        imp_config = ImperfectionConfig(
            typo_rate=self.config.typo_rate,
            correction_rate=self.config.correction_rate,
            hesitation_rate=self.config.hesitation_rate
        )
        self.imperfections = ImperfectionEngine(imp_config)
    
    # ==================== Session Management ====================
    
    def start_session(self) -> bool:
        """
        Start a new messaging session
        
        Returns:
            True if session started successfully
        """
        # Wait for operating hours if needed
        if not self.is_operating_hours():
            logger.info("Outside operating hours, waiting...")
            self._wait_for_operating_hours()
        
        # Start session
        success = self.session.start_session()
        
        if success:
            self.timing.start_session()
            self.interaction.reset()
            self.imperfections.clear_log()
            logger.info("Human behavior session started")
        
        return success
    
    def end_session(self) -> Dict:
        """
        End current session
        
        Returns:
            Session statistics
        """
        stats = self.session.end_session()
        self.timing.end_session(take_break=False)
        
        for callback in self._callbacks['on_session_end']:
            try:
                callback(stats)
            except Exception as e:
                logger.error(f"Session end callback error: {e}")
        
        logger.info(f"Session ended: {stats.messages_sent if stats else 0} messages")
        
        return {
            'messages_sent': stats.messages_sent if stats else 0,
            'duration_minutes': stats.duration_minutes() if stats else 0,
            'profiles_viewed': stats.profiles_viewed if stats else 0,
            'breaks_taken': stats.breaks_taken if stats else 0
        }
    
    def is_operating_hours(self) -> bool:
        """Check if current time is within operating hours"""
        hour = datetime.now().hour
        return self.config.start_hour <= hour < self.config.end_hour
    
    def _wait_for_operating_hours(self) -> None:
        """Wait until operating hours begin"""
        now = datetime.now()
        
        if now.hour >= self.config.end_hour:
            # Wait until tomorrow
            next_start = now.replace(
                hour=self.config.start_hour,
                minute=random.randint(0, 30),
                second=0,
                microsecond=0
            ) + timedelta(days=1)
        else:
            # Wait until start hour today
            next_start = now.replace(
                hour=self.config.start_hour,
                minute=random.randint(0, 30),
                second=0,
                microsecond=0
            )
        
        wait_seconds = (next_start - now).total_seconds()
        logger.info(f"Waiting {wait_seconds/3600:.1f} hours until {next_start}")
        
        if wait_seconds > 0:
            time.sleep(wait_seconds)
    
    # ==================== Message Sending ====================
    
    def can_send_message(self) -> Tuple[bool, str]:
        """
        Check if a message can be sent
        
        Returns:
            (can_send, reason_if_not)
        """
        # Check operating hours
        if not self.is_operating_hours():
            return False, "outside_operating_hours"
        
        # Check session state
        can_send, reason = self.session.can_send_message()
        if not can_send:
            return False, reason
        
        return True, ""
    
    def prepare_message(
        self,
        volunteer_name: str,
        volunteer_location: Optional[str],
        body: str,
        volunteer_skills: Optional[List[str]] = None,
        message_type: str = "initial"
    ) -> str:
        """
        Prepare a message with human-like variations
        
        Args:
            volunteer_name: Recipient name
            volunteer_location: Recipient location
            body: Main message body
            volunteer_skills: Recipient skills
            message_type: "initial", "follow_up", or "reply"
        
        Returns:
            Prepared message with variations
        """
        # Create volunteer profile
        volunteer = VolunteerProfile(
            name=volunteer_name,
            location=volunteer_location,
            skills=volunteer_skills or []
        )
        
        # Determine personalization level
        level_map = {
            "none": PersonalizationLevel.NONE,
            "name": PersonalizationLevel.NAME_ONLY,
            "location": PersonalizationLevel.LOCATION,
            "skills": PersonalizationLevel.SKILLS,
            "detailed": PersonalizationLevel.DETAILED
        }
        level = level_map.get(
            self.config.personalization_level,
            PersonalizationLevel.LOCATION
        )
        
        # Generate varied message
        message = self.content.generate_message(
            volunteer=volunteer,
            body=body,
            message_type=message_type,
            personalization_level=level,
            formal=self.config.formal_language
        )
        
        # Apply imperfections (controlled typos, etc.)
        message, _ = self.imperfections.process_text(
            message,
            apply_typos=True,
            apply_spacing=True,
            apply_punctuation=True
        )
        
        return message
    
    def wait_before_message(
        self,
        message_length: int = 100,
        is_reply: bool = False,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> float:
        """
        Wait appropriate time before sending message
        
        Args:
            message_length: Length of message to send
            is_reply: Whether this is a reply
            progress_callback: Optional callback with remaining time
        
        Returns:
            Actual wait time in seconds
        """
        # Get base delay
        delay = self.timing.get_message_delay(message_length, is_reply)
        
        # Adjust for session phase (warm-up/cool-down)
        delay = self.session.get_recommended_delay(delay)
        
        # Add hesitation chance
        if self.imperfections.hesitation.should_hesitate():
            delay += self.imperfections.hesitation.get_hesitation_duration() / 1000
        
        # Long pause chance
        if self.imperfections.hesitation.should_long_pause():
            delay += self.imperfections.hesitation.get_long_pause_duration() / 1000
        
        logger.debug(f"Waiting {delay:.1f}s before message")
        
        # Wait with progress updates
        start = time.monotonic()
        while time.monotonic() - start < delay:
            remaining = delay - (time.monotonic() - start)
            if progress_callback:
                progress_callback(remaining)
            time.sleep(min(1.0, remaining))
        
        return delay
    
    def record_message_sent(self) -> bool:
        """
        Record that a message was sent
        
        Returns:
            True if recorded successfully
        """
        success = self.session.record_message_sent()
        
        if success:
            self._message_count += 1
            self._last_message_time = datetime.now()
            
            # Check if break needed
            should_break, reason = self.session.should_take_break()
            if should_break:
                self._handle_break(reason)
            
            # Trigger callbacks
            for callback in self._callbacks['after_message']:
                try:
                    callback(self._message_count)
                except Exception as e:
                    logger.error(f"After message callback error: {e}")
        
        return success
    
    def _handle_break(self, reason: str) -> None:
        """Handle taking a break"""
        duration = random.uniform(
            self.config.min_break_minutes,
            self.config.max_break_minutes
        )
        
        logger.info(f"Taking break for {duration:.1f} minutes (reason: {reason})")
        
        self.session.start_break(duration)
        
        for callback in self._callbacks['on_break']:
            try:
                callback(duration, reason)
            except Exception as e:
                logger.error(f"Break callback error: {e}")
        
        # Wait for break
        time.sleep(duration * 60)
    
    # ==================== Profile Viewing ====================
    
    def simulate_profile_viewing(
        self,
        profile_content_length: int = 500
    ) -> float:
        """
        Simulate viewing a volunteer profile
        
        Args:
            profile_content_length: Approximate content length
        
        Returns:
            Time spent viewing in seconds
        """
        # Base reading time
        words = profile_content_length / 5
        reading_wpm = random.uniform(150, 250)
        reading_time = (words / reading_wpm) * 60
        
        # Add scroll simulation time
        scroll_time = random.uniform(2, 5)
        
        # Add thinking time
        thinking_time = random.uniform(3, 10)
        
        total_time = reading_time + scroll_time + thinking_time
        
        # Record activity
        self.session.record_profile_viewed()
        
        logger.debug(f"Simulating profile view for {total_time:.1f}s")
        time.sleep(total_time)
        
        return total_time
    
    # ==================== Typing Simulation ====================
    
    def get_typing_sequence(
        self,
        text: str,
        include_typos: bool = True
    ) -> List[Dict]:
        """
        Get typing sequence for text
        
        Args:
            text: Text to type
            include_typos: Whether to include typos
        
        Returns:
            List of typing actions
        """
        if include_typos:
            return self.imperfections.generate_typing_with_corrections(text)
        else:
            return self.interaction.type_text(text, include_typos=False)
    
    def get_typing_duration(self, text: str) -> float:
        """
        Get estimated typing duration for text
        
        Args:
            text: Text to type
        
        Returns:
            Duration in seconds
        """
        return self.timing.simulate_typing_delay(text)
    
    # ==================== Status & Statistics ====================
    
    def get_status(self) -> Dict:
        """Get comprehensive status"""
        session_status = self.session.get_status()
        timing_status = self.timing.get_status()
        
        return {
            'operating_hours': self.is_operating_hours(),
            'current_time': datetime.now().isoformat(),
            'session': session_status,
            'timing': timing_status,
            'messages_sent_total': self._message_count,
            'last_message_time': self._last_message_time.isoformat() if self._last_message_time else None,
            'imperfection_stats': self.imperfections.get_imperfection_stats()
        }
    
    def get_remaining_quota(self) -> Dict:
        """Get remaining quota for today"""
        return self.session.quota.get_remaining_quota()
    
    # ==================== Callbacks ====================
    
    def on_before_message(self, callback: Callable) -> None:
        """Register callback before message send"""
        self._callbacks['before_message'].append(callback)
    
    def on_after_message(self, callback: Callable[[int], None]) -> None:
        """Register callback after message send"""
        self._callbacks['after_message'].append(callback)
    
    def on_break(self, callback: Callable[[float, str], None]) -> None:
        """Register callback when break starts"""
        self._callbacks['on_break'].append(callback)
    
    def on_session_end(self, callback: Callable) -> None:
        """Register callback when session ends"""
        self._callbacks['on_session_end'].append(callback)
    
    def on_error(self, callback: Callable[[Exception], None]) -> None:
        """Register callback on error"""
        self._callbacks['on_error'].append(callback)


# ==================== Convenience Functions ====================

def create_human_engine(
    sender_name: str = "",
    config: Optional[HumanBehaviorConfig] = None
) -> HumanBehaviorEngine:
    """Create a new human behavior engine"""
    return HumanBehaviorEngine(config=config, sender_name=sender_name)


def prepare_human_message(
    volunteer_name: str,
    body: str,
    sender_name: str,
    volunteer_location: Optional[str] = None
) -> str:
    """Quick function to prepare a human-like message"""
    engine = HumanBehaviorEngine(sender_name=sender_name)
    return engine.prepare_message(
        volunteer_name=volunteer_name,
        volunteer_location=volunteer_location,
        body=body
    )


def get_message_delay(message_length: int = 100) -> float:
    """Get recommended delay before sending message"""
    engine = get_timing_engine()
    return engine.get_message_delay(message_length)


# ==================== Module Exports ====================

__all__ = [
    # Main engine
    'HumanBehaviorEngine',
    'HumanBehaviorConfig',
    'create_human_engine',
    
    # Timing
    'HumanTimingEngine',
    'TimingConfig',
    'ActivityLevel',
    'get_timing_engine',
    
    # Content
    'ContentVariator',
    'VolunteerProfile',
    'PersonalizationLevel',
    'DutchSynonyms',
    'DutchGreetings',
    'DutchClosings',
    
    # Interaction
    'InteractionSimulator',
    'MousePathGenerator',
    'KeyboardSimulator',
    'ScrollSimulator',
    'Point',
    'get_interaction_simulator',
    
    # Session
    'SessionManager',
    'SessionState',
    'QuotaLimits',
    'QuotaTracker',
    'ActivityType',
    'GradualScaling',
    'get_session_manager',
    
    # Imperfections
    'ImperfectionEngine',
    'ImperfectionConfig',
    'get_imperfection_engine',
    'add_imperfections',
    
    # Convenience
    'prepare_human_message',
    'get_message_delay',
]


# Version info
__version__ = '1.0.0'
__author__ = 'NLvoorElkaar Tool'
