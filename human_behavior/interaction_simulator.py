"""
Human-Like Interaction Simulator

Simulates realistic mouse movements, keyboard input, and scroll behavior
to mimic human interaction patterns with the browser.
"""

import random
import time
import math
import logging
from typing import Optional, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class Point:
    """2D point for mouse coordinates"""
    x: float
    y: float
    
    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Point':
        return Point(self.x * scalar, self.y * scalar)


class MouseMovementType(Enum):
    """Types of mouse movement patterns"""
    DIRECT = "direct"  # Relatively straight
    CURVED = "curved"  # Natural curve
    HESITANT = "hesitant"  # With pauses
    OVERSHOOT = "overshoot"  # Goes past target


class BezierCurve:
    """
    Bezier curve generator for natural mouse paths
    """
    
    @staticmethod
    def quadratic(p0: Point, p1: Point, p2: Point, t: float) -> Point:
        """Calculate point on quadratic Bezier curve"""
        x = (1-t)**2 * p0.x + 2*(1-t)*t * p1.x + t**2 * p2.x
        y = (1-t)**2 * p0.y + 2*(1-t)*t * p1.y + t**2 * p2.y
        return Point(x, y)
    
    @staticmethod
    def cubic(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
        """Calculate point on cubic Bezier curve"""
        x = (1-t)**3 * p0.x + 3*(1-t)**2*t * p1.x + 3*(1-t)*t**2 * p2.x + t**3 * p3.x
        y = (1-t)**3 * p0.y + 3*(1-t)**2*t * p1.y + 3*(1-t)*t**2 * p2.y + t**3 * p3.y
        return Point(x, y)
    
    @staticmethod
    def generate_control_points(start: Point, end: Point) -> Tuple[Point, Point]:
        """Generate random control points for natural curve"""
        dx = end.x - start.x
        dy = end.y - start.y
        distance = start.distance_to(end)
        
        # Control point offset (perpendicular to line)
        offset_magnitude = distance * random.uniform(0.1, 0.3)
        
        # Random perpendicular direction
        if random.random() < 0.5:
            offset_x = -dy / distance * offset_magnitude
            offset_y = dx / distance * offset_magnitude
        else:
            offset_x = dy / distance * offset_magnitude
            offset_y = -dx / distance * offset_magnitude
        
        # First control point (closer to start)
        cp1 = Point(
            start.x + dx * random.uniform(0.2, 0.4) + offset_x * random.uniform(0.5, 1.5),
            start.y + dy * random.uniform(0.2, 0.4) + offset_y * random.uniform(0.5, 1.5)
        )
        
        # Second control point (closer to end)
        cp2 = Point(
            start.x + dx * random.uniform(0.6, 0.8) + offset_x * random.uniform(-0.5, 0.5),
            start.y + dy * random.uniform(0.6, 0.8) + offset_y * random.uniform(-0.5, 0.5)
        )
        
        return cp1, cp2


class MousePathGenerator:
    """
    Generates realistic mouse movement paths
    """
    
    def __init__(self):
        self._last_position = Point(0, 0)
    
    def generate_path(
        self,
        start: Point,
        end: Point,
        movement_type: Optional[MouseMovementType] = None,
        num_points: int = 50
    ) -> List[Tuple[Point, float]]:
        """
        Generate mouse path with timing
        
        Args:
            start: Starting position
            end: Target position
            movement_type: Type of movement (random if None)
            num_points: Number of points in path
        
        Returns:
            List of (point, delay_ms) tuples
        """
        if movement_type is None:
            movement_type = self._select_movement_type()
        
        distance = start.distance_to(end)
        
        # Generate base path
        if movement_type == MouseMovementType.DIRECT:
            path = self._generate_direct_path(start, end, num_points)
        elif movement_type == MouseMovementType.CURVED:
            path = self._generate_curved_path(start, end, num_points)
        elif movement_type == MouseMovementType.HESITANT:
            path = self._generate_hesitant_path(start, end, num_points)
        else:  # OVERSHOOT
            path = self._generate_overshoot_path(start, end, num_points)
        
        # Add timing
        timed_path = self._add_timing(path, distance)
        
        # Add micro-movements (jitter)
        timed_path = self._add_jitter(timed_path)
        
        self._last_position = end
        return timed_path
    
    def _select_movement_type(self) -> MouseMovementType:
        """Select random movement type based on probability"""
        r = random.random()
        if r < 0.1:
            return MouseMovementType.DIRECT
        elif r < 0.7:
            return MouseMovementType.CURVED
        elif r < 0.9:
            return MouseMovementType.HESITANT
        else:
            return MouseMovementType.OVERSHOOT
    
    def _generate_direct_path(
        self,
        start: Point,
        end: Point,
        num_points: int
    ) -> List[Point]:
        """Generate relatively straight path with slight variation"""
        path = []
        
        for i in range(num_points):
            t = i / (num_points - 1)
            
            # Linear interpolation with small noise
            x = start.x + (end.x - start.x) * t
            y = start.y + (end.y - start.y) * t
            
            # Add small perpendicular noise
            noise = random.gauss(0, 2)
            x += noise
            y += noise
            
            path.append(Point(x, y))
        
        return path
    
    def _generate_curved_path(
        self,
        start: Point,
        end: Point,
        num_points: int
    ) -> List[Point]:
        """Generate natural curved path using Bezier curves"""
        cp1, cp2 = BezierCurve.generate_control_points(start, end)
        
        path = []
        for i in range(num_points):
            t = i / (num_points - 1)
            point = BezierCurve.cubic(start, cp1, cp2, end, t)
            path.append(point)
        
        return path
    
    def _generate_hesitant_path(
        self,
        start: Point,
        end: Point,
        num_points: int
    ) -> List[Point]:
        """Generate path with hesitation points"""
        # Generate base curved path
        path = self._generate_curved_path(start, end, num_points)
        
        # Add hesitation points (small loops or pauses)
        hesitation_point = random.randint(num_points // 3, 2 * num_points // 3)
        
        # Insert small deviation at hesitation point
        if hesitation_point < len(path):
            hp = path[hesitation_point]
            deviation = Point(
                random.uniform(-10, 10),
                random.uniform(-10, 10)
            )
            
            # Insert deviation and return
            path.insert(hesitation_point, hp + deviation)
            path.insert(hesitation_point + 1, hp + deviation * 0.5)
        
        return path
    
    def _generate_overshoot_path(
        self,
        start: Point,
        end: Point,
        num_points: int
    ) -> List[Point]:
        """Generate path that overshoots and corrects"""
        # Calculate overshoot point
        direction = end - start
        overshoot_distance = random.uniform(10, 30)
        overshoot_point = Point(
            end.x + (direction.x / start.distance_to(end)) * overshoot_distance,
            end.y + (direction.y / start.distance_to(end)) * overshoot_distance
        )
        
        # Path to overshoot
        path1 = self._generate_curved_path(start, overshoot_point, num_points * 2 // 3)
        
        # Correction path
        path2 = self._generate_direct_path(overshoot_point, end, num_points // 3)
        
        return path1 + path2
    
    def _add_timing(
        self,
        path: List[Point],
        total_distance: float
    ) -> List[Tuple[Point, float]]:
        """Add timing to path points"""
        # Base movement time (faster for longer distances, but not linear)
        base_time_ms = 200 + total_distance * 1.5
        base_time_ms = min(base_time_ms, 1500)  # Cap at 1.5 seconds
        
        timed_path = []
        
        for i, point in enumerate(path):
            # Ease-in-ease-out timing
            t = i / (len(path) - 1) if len(path) > 1 else 0
            
            # Slow at start and end, fast in middle
            if t < 0.2:
                speed_factor = 0.5 + t * 2.5  # Accelerating
            elif t > 0.8:
                speed_factor = 0.5 + (1 - t) * 2.5  # Decelerating
            else:
                speed_factor = 1.0
            
            delay = (base_time_ms / len(path)) / speed_factor
            delay *= random.uniform(0.8, 1.2)  # Add variance
            
            timed_path.append((point, delay))
        
        return timed_path
    
    def _add_jitter(
        self,
        path: List[Tuple[Point, float]]
    ) -> List[Tuple[Point, float]]:
        """Add micro-movements (hand tremor simulation)"""
        jittered = []
        
        for point, delay in path:
            # Small random offset (1-2 pixels)
            jitter = Point(
                random.gauss(0, 0.5),
                random.gauss(0, 0.5)
            )
            jittered.append((point + jitter, delay))
        
        return jittered


class ScrollSimulator:
    """
    Simulates human-like scrolling behavior
    """
    
    def __init__(self):
        self._scroll_position = 0
        self._page_height = 0
    
    def generate_scroll_sequence(
        self,
        target_position: int,
        current_position: int = 0,
        viewport_height: int = 800
    ) -> List[Tuple[int, float]]:
        """
        Generate scroll sequence to reach target
        
        Args:
            target_position: Target scroll position
            current_position: Current scroll position
            viewport_height: Height of viewport
        
        Returns:
            List of (scroll_delta, delay_ms) tuples
        """
        sequence = []
        position = current_position
        
        while abs(position - target_position) > 50:
            # Calculate scroll amount
            remaining = target_position - position
            
            # Variable scroll amounts (100-400 pixels typically)
            max_scroll = min(abs(remaining), random.randint(100, 400))
            
            if remaining > 0:
                scroll = max_scroll
            else:
                scroll = -max_scroll
            
            # Occasional overshoot
            if random.random() < 0.1 and abs(remaining) < 200:
                scroll *= 1.3
            
            position += scroll
            
            # Delay between scrolls
            delay = random.uniform(50, 200)
            
            # Longer pause occasionally (reading)
            if random.random() < 0.2:
                delay += random.uniform(500, 2000)
            
            sequence.append((int(scroll), delay))
        
        # Final adjustment
        final_scroll = target_position - position
        if abs(final_scroll) > 5:
            sequence.append((int(final_scroll), random.uniform(100, 300)))
        
        return sequence
    
    def generate_reading_scroll(
        self,
        content_height: int,
        viewport_height: int = 800,
        reading_speed: float = 1.0
    ) -> List[Tuple[int, float]]:
        """
        Generate scroll sequence for reading content
        
        Args:
            content_height: Total content height
            viewport_height: Viewport height
            reading_speed: Multiplier for reading speed
        
        Returns:
            List of (scroll_delta, delay_ms) tuples
        """
        sequence = []
        position = 0
        
        while position < content_height - viewport_height:
            # Scroll amount (roughly half viewport)
            scroll = random.randint(
                int(viewport_height * 0.3),
                int(viewport_height * 0.6)
            )
            
            # Reading time (based on content amount)
            reading_time = random.uniform(2000, 5000) / reading_speed
            
            # Sometimes scroll back up slightly
            if random.random() < 0.1:
                sequence.append((-random.randint(50, 150), 200))
                sequence.append((random.randint(100, 200), reading_time * 0.5))
            
            sequence.append((scroll, reading_time))
            position += scroll
        
        return sequence


class KeyboardSimulator:
    """
    Simulates human-like keyboard input
    """
    
    # Common typo patterns (adjacent keys on QWERTY)
    ADJACENT_KEYS = {
        'a': ['s', 'q', 'w', 'z'],
        'b': ['v', 'g', 'h', 'n'],
        'c': ['x', 'd', 'f', 'v'],
        'd': ['s', 'e', 'r', 'f', 'c', 'x'],
        'e': ['w', 'r', 'd', 's'],
        'f': ['d', 'r', 't', 'g', 'v', 'c'],
        'g': ['f', 't', 'y', 'h', 'b', 'v'],
        'h': ['g', 'y', 'u', 'j', 'n', 'b'],
        'i': ['u', 'o', 'k', 'j'],
        'j': ['h', 'u', 'i', 'k', 'm', 'n'],
        'k': ['j', 'i', 'o', 'l', 'm'],
        'l': ['k', 'o', 'p'],
        'm': ['n', 'j', 'k'],
        'n': ['b', 'h', 'j', 'm'],
        'o': ['i', 'p', 'l', 'k'],
        'p': ['o', 'l'],
        'q': ['w', 'a'],
        'r': ['e', 't', 'f', 'd'],
        's': ['a', 'w', 'e', 'd', 'x', 'z'],
        't': ['r', 'y', 'g', 'f'],
        'u': ['y', 'i', 'j', 'h'],
        'v': ['c', 'f', 'g', 'b'],
        'w': ['q', 'e', 's', 'a'],
        'x': ['z', 's', 'd', 'c'],
        'y': ['t', 'u', 'h', 'g'],
        'z': ['a', 's', 'x'],
    }
    
    def __init__(self, typo_rate: float = 0.03, correction_rate: float = 0.9):
        self.typo_rate = typo_rate
        self.correction_rate = correction_rate
        self._fatigue = 0
    
    def generate_typing_sequence(
        self,
        text: str,
        include_typos: bool = True
    ) -> List[Tuple[str, float, str]]:
        """
        Generate typing sequence with timing and potential typos
        
        Args:
            text: Text to type
            include_typos: Whether to include typos
        
        Returns:
            List of (character, delay_ms, action) tuples
            action is 'type', 'backspace', or 'pause'
        """
        sequence = []
        
        for i, char in enumerate(text):
            # Base delay
            delay = self._get_char_delay(char)
            
            # Check for typo
            if include_typos and self._should_make_typo():
                typo_char = self._generate_typo(char)
                sequence.append((typo_char, delay, 'type'))
                
                # Correction
                if random.random() < self.correction_rate:
                    # Pause before noticing
                    notice_delay = random.uniform(100, 500)
                    sequence.append(('', notice_delay, 'pause'))
                    
                    # Backspace
                    sequence.append(('', random.uniform(50, 150), 'backspace'))
                    
                    # Type correct character
                    sequence.append((char, delay * 1.2, 'type'))
            else:
                sequence.append((char, delay, 'type'))
            
            # Occasional pause (thinking)
            if random.random() < 0.02:
                sequence.append(('', random.uniform(300, 1000), 'pause'))
            
            # Update fatigue
            self._fatigue += 0.001
        
        return sequence
    
    def _get_char_delay(self, char: str) -> float:
        """Get delay for typing a character"""
        # Base delay
        base = random.uniform(50, 150)
        
        # Slower for special characters
        if char in '.,!?;:':
            base *= 1.3
        elif char.isupper():
            base *= 1.2  # Shift key
        elif char in '@#$%^&*()':
            base *= 1.5
        
        # Apply fatigue
        base *= (1 + self._fatigue)
        
        # Word boundary pause
        if char == ' ':
            base += random.uniform(20, 80)
        
        return base
    
    def _should_make_typo(self) -> bool:
        """Determine if a typo should occur"""
        # Typo rate increases with fatigue
        adjusted_rate = self.typo_rate * (1 + self._fatigue * 2)
        return random.random() < adjusted_rate
    
    def _generate_typo(self, char: str) -> str:
        """Generate a realistic typo for a character"""
        char_lower = char.lower()
        
        if char_lower in self.ADJACENT_KEYS:
            typo = random.choice(self.ADJACENT_KEYS[char_lower])
            # Preserve case
            if char.isupper():
                typo = typo.upper()
            return typo
        
        # Double character
        if random.random() < 0.3:
            return char + char
        
        # Skip character (return empty, will be handled as missing)
        return char  # Fallback to correct
    
    def reset_fatigue(self) -> None:
        """Reset typing fatigue"""
        self._fatigue = 0


class ClickSimulator:
    """
    Simulates human-like click behavior
    """
    
    def __init__(self):
        self._click_count = 0
    
    def generate_click(
        self,
        target: Point,
        button: str = 'left'
    ) -> dict:
        """
        Generate click parameters
        
        Args:
            target: Target click position
            button: 'left', 'right', or 'middle'
        
        Returns:
            Click parameters dict
        """
        # Slight position variance (humans don't click exact center)
        actual_x = target.x + random.gauss(0, 3)
        actual_y = target.y + random.gauss(0, 3)
        
        # Pre-click hesitation
        pre_delay = random.uniform(50, 200)
        
        # Occasional hesitation before important clicks
        if random.random() < 0.1:
            pre_delay += random.uniform(200, 500)
        
        # Click duration (press and release)
        hold_duration = random.uniform(50, 150)
        
        # Post-click delay
        post_delay = random.uniform(100, 300)
        
        self._click_count += 1
        
        return {
            'x': actual_x,
            'y': actual_y,
            'button': button,
            'pre_delay_ms': pre_delay,
            'hold_duration_ms': hold_duration,
            'post_delay_ms': post_delay
        }
    
    def generate_double_click(self, target: Point) -> List[dict]:
        """Generate double-click sequence"""
        click1 = self.generate_click(target)
        click1['post_delay_ms'] = random.uniform(50, 150)  # Short delay between
        
        click2 = self.generate_click(target)
        click2['pre_delay_ms'] = 0  # No pre-delay for second click
        
        # Slight position shift between clicks
        click2['x'] += random.gauss(0, 2)
        click2['y'] += random.gauss(0, 2)
        
        return [click1, click2]


class InteractionSimulator:
    """
    Main interaction simulator combining all components
    """
    
    def __init__(self):
        self.mouse = MousePathGenerator()
        self.scroll = ScrollSimulator()
        self.keyboard = KeyboardSimulator()
        self.click = ClickSimulator()
        
        self._current_position = Point(0, 0)
    
    def move_to(
        self,
        target: Point,
        movement_type: Optional[MouseMovementType] = None
    ) -> List[Tuple[Point, float]]:
        """Generate mouse movement to target"""
        path = self.mouse.generate_path(
            self._current_position,
            target,
            movement_type
        )
        self._current_position = target
        return path
    
    def click_at(
        self,
        target: Point,
        move_first: bool = True
    ) -> dict:
        """
        Generate click at target
        
        Args:
            target: Click target
            move_first: Whether to move mouse first
        
        Returns:
            Dict with 'path' (if move_first) and 'click' data
        """
        result = {}
        
        if move_first:
            result['path'] = self.move_to(target)
        
        result['click'] = self.click.generate_click(target)
        
        return result
    
    def type_text(
        self,
        text: str,
        include_typos: bool = True
    ) -> List[Tuple[str, float, str]]:
        """Generate typing sequence"""
        return self.keyboard.generate_typing_sequence(text, include_typos)
    
    def scroll_to(
        self,
        target_position: int,
        current_position: int = 0
    ) -> List[Tuple[int, float]]:
        """Generate scroll sequence"""
        return self.scroll.generate_scroll_sequence(
            target_position,
            current_position
        )
    
    def read_page(
        self,
        content_height: int,
        viewport_height: int = 800
    ) -> List[Tuple[int, float]]:
        """Generate reading scroll sequence"""
        return self.scroll.generate_reading_scroll(
            content_height,
            viewport_height
        )
    
    def reset(self) -> None:
        """Reset all simulators"""
        self._current_position = Point(0, 0)
        self.keyboard.reset_fatigue()


# Global instance
_simulator: Optional[InteractionSimulator] = None


def get_interaction_simulator() -> InteractionSimulator:
    """Get global interaction simulator"""
    global _simulator
    if _simulator is None:
        _simulator = InteractionSimulator()
    return _simulator
