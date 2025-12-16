"""
Human Imperfections Generator

Introduces controlled imperfections to make behavior appear more human-like,
including typos, navigation mistakes, hesitations, and natural errors.
"""

import random
import re
import logging
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ImperfectionType(Enum):
    """Types of imperfections"""
    TYPO = "typo"
    DOUBLE_CHAR = "double_char"
    MISSING_CHAR = "missing_char"
    TRANSPOSED_CHARS = "transposed_chars"
    WRONG_CASE = "wrong_case"
    EXTRA_SPACE = "extra_space"
    MISSING_SPACE = "missing_space"
    PUNCTUATION_ERROR = "punctuation_error"
    NAVIGATION_MISTAKE = "navigation_mistake"
    HESITATION = "hesitation"
    CORRECTION = "correction"


@dataclass
class ImperfectionConfig:
    """Configuration for imperfection rates"""
    # Text imperfections (per character/word probability)
    typo_rate: float = 0.02  # 2% of characters
    double_char_rate: float = 0.005  # 0.5%
    missing_char_rate: float = 0.005
    transposition_rate: float = 0.003
    case_error_rate: float = 0.01
    
    # Spacing imperfections
    extra_space_rate: float = 0.02  # Per space
    missing_space_rate: float = 0.01
    
    # Punctuation imperfections
    missing_period_rate: float = 0.05  # End of message
    extra_comma_rate: float = 0.02
    
    # Correction behavior
    correction_rate: float = 0.8  # How often typos are corrected
    immediate_correction_rate: float = 0.6  # Corrected immediately vs later
    
    # Navigation imperfections
    wrong_click_rate: float = 0.02
    back_button_rate: float = 0.05  # After wrong navigation
    scroll_overshoot_rate: float = 0.1
    
    # Hesitation
    hesitation_rate: float = 0.05  # Before actions
    long_pause_rate: float = 0.02  # Random long pauses


class TypoGenerator:
    """
    Generates realistic typos based on keyboard layout
    """
    
    # QWERTY keyboard adjacency map
    ADJACENT_KEYS = {
        'a': ['q', 'w', 's', 'z'],
        'b': ['v', 'g', 'h', 'n'],
        'c': ['x', 'd', 'f', 'v'],
        'd': ['s', 'e', 'r', 'f', 'c', 'x'],
        'e': ['w', 's', 'd', 'r'],
        'f': ['d', 'r', 't', 'g', 'v', 'c'],
        'g': ['f', 't', 'y', 'h', 'b', 'v'],
        'h': ['g', 'y', 'u', 'j', 'n', 'b'],
        'i': ['u', 'j', 'k', 'o'],
        'j': ['h', 'u', 'i', 'k', 'm', 'n'],
        'k': ['j', 'i', 'o', 'l', 'm'],
        'l': ['k', 'o', 'p'],
        'm': ['n', 'j', 'k'],
        'n': ['b', 'h', 'j', 'm'],
        'o': ['i', 'k', 'l', 'p'],
        'p': ['o', 'l'],
        'q': ['w', 'a'],
        'r': ['e', 'd', 'f', 't'],
        's': ['a', 'w', 'e', 'd', 'x', 'z'],
        't': ['r', 'f', 'g', 'y'],
        'u': ['y', 'h', 'j', 'i'],
        'v': ['c', 'f', 'g', 'b'],
        'w': ['q', 'a', 's', 'e'],
        'x': ['z', 's', 'd', 'c'],
        'y': ['t', 'g', 'h', 'u'],
        'z': ['a', 's', 'x'],
    }
    
    # Common Dutch typo patterns
    DUTCH_COMMON_TYPOS = {
        'ij': ['ij', 'y'],  # Common confusion
        'ei': ['ij', 'ie'],
        'ie': ['ei', 'i'],
        'oe': ['ou', 'oo'],
        'ou': ['oe', 'au'],
        'au': ['ou', 'ao'],
        'ch': ['g', 'sch'],
        'sch': ['ch', 'sg'],
    }
    
    def __init__(self, config: ImperfectionConfig):
        self.config = config
    
    def generate_typo(self, char: str) -> str:
        """Generate a typo for a single character"""
        char_lower = char.lower()
        
        if char_lower in self.ADJACENT_KEYS:
            typo = random.choice(self.ADJACENT_KEYS[char_lower])
            # Preserve case
            if char.isupper():
                typo = typo.upper()
            return typo
        
        return char
    
    def apply_typos(self, text: str) -> Tuple[str, List[Dict]]:
        """
        Apply typos to text
        
        Returns:
            (modified_text, list of typo records)
        """
        result = []
        typos = []
        
        i = 0
        while i < len(text):
            char = text[i]
            
            # Check for Dutch digraph typos
            if i < len(text) - 1:
                digraph = text[i:i+2].lower()
                if digraph in self.DUTCH_COMMON_TYPOS:
                    if random.random() < self.config.typo_rate * 2:
                        replacement = random.choice(self.DUTCH_COMMON_TYPOS[digraph])
                        result.append(replacement)
                        typos.append({
                            'type': 'digraph',
                            'position': i,
                            'original': digraph,
                            'replacement': replacement
                        })
                        i += 2
                        continue
            
            # Single character typos
            if char.isalpha() and random.random() < self.config.typo_rate:
                typo_char = self.generate_typo(char)
                result.append(typo_char)
                typos.append({
                    'type': 'single',
                    'position': i,
                    'original': char,
                    'replacement': typo_char
                })
            
            # Double character
            elif char.isalpha() and random.random() < self.config.double_char_rate:
                result.append(char + char)
                typos.append({
                    'type': 'double',
                    'position': i,
                    'original': char
                })
            
            # Missing character
            elif char.isalpha() and random.random() < self.config.missing_char_rate:
                typos.append({
                    'type': 'missing',
                    'position': i,
                    'original': char
                })
                # Don't append the character
            
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result), typos


class SpacingImperfections:
    """
    Generates spacing-related imperfections
    """
    
    def __init__(self, config: ImperfectionConfig):
        self.config = config
    
    def apply_spacing_errors(self, text: str) -> str:
        """Apply spacing imperfections to text"""
        words = text.split(' ')
        result = []
        
        for i, word in enumerate(words):
            result.append(word)
            
            if i < len(words) - 1:
                # Extra space
                if random.random() < self.config.extra_space_rate:
                    result.append(' ')  # Double space
                
                # Missing space (join with next word)
                elif random.random() < self.config.missing_space_rate:
                    continue  # Don't add space
                
                result.append(' ')
        
        return ''.join(result)


class PunctuationImperfections:
    """
    Generates punctuation-related imperfections
    """
    
    def __init__(self, config: ImperfectionConfig):
        self.config = config
    
    def apply_punctuation_errors(self, text: str) -> str:
        """Apply punctuation imperfections"""
        # Missing final period
        if text.endswith('.') and random.random() < self.config.missing_period_rate:
            text = text[:-1]
        
        # Extra commas
        words = text.split()
        result = []
        
        for i, word in enumerate(words):
            result.append(word)
            
            # Random extra comma after word
            if (not word.endswith((',', '.', '!', '?', ';', ':')) and 
                random.random() < self.config.extra_comma_rate):
                result[-1] = word + ','
        
        return ' '.join(result)


class NavigationImperfections:
    """
    Generates navigation-related imperfections
    """
    
    def __init__(self, config: ImperfectionConfig):
        self.config = config
    
    def should_make_wrong_click(self) -> bool:
        """Determine if a wrong click should occur"""
        return random.random() < self.config.wrong_click_rate
    
    def should_go_back(self) -> bool:
        """Determine if back button should be pressed (after mistake)"""
        return random.random() < self.config.back_button_rate
    
    def should_overshoot_scroll(self) -> bool:
        """Determine if scroll should overshoot"""
        return random.random() < self.config.scroll_overshoot_rate
    
    def generate_wrong_click_offset(self) -> Tuple[int, int]:
        """Generate offset for a wrong click"""
        # Usually clicks near intended target
        offset_x = random.gauss(0, 30)
        offset_y = random.gauss(0, 30)
        
        # Occasionally way off
        if random.random() < 0.1:
            offset_x *= 3
            offset_y *= 3
        
        return int(offset_x), int(offset_y)
    
    def generate_scroll_overshoot(self, intended_scroll: int) -> int:
        """Generate overshoot amount for scrolling"""
        overshoot = random.uniform(0.1, 0.3) * abs(intended_scroll)
        return int(overshoot) if intended_scroll > 0 else -int(overshoot)


class HesitationGenerator:
    """
    Generates hesitation patterns
    """
    
    def __init__(self, config: ImperfectionConfig):
        self.config = config
    
    def should_hesitate(self) -> bool:
        """Determine if hesitation should occur"""
        return random.random() < self.config.hesitation_rate
    
    def should_long_pause(self) -> bool:
        """Determine if a long pause should occur"""
        return random.random() < self.config.long_pause_rate
    
    def get_hesitation_duration(self) -> float:
        """Get hesitation duration in milliseconds"""
        return random.uniform(200, 800)
    
    def get_long_pause_duration(self) -> float:
        """Get long pause duration in milliseconds"""
        return random.uniform(2000, 5000)


class CorrectionSimulator:
    """
    Simulates error correction behavior
    """
    
    def __init__(self, config: ImperfectionConfig):
        self.config = config
    
    def should_correct(self) -> bool:
        """Determine if a typo should be corrected"""
        return random.random() < self.config.correction_rate
    
    def is_immediate_correction(self) -> bool:
        """Determine if correction is immediate or delayed"""
        return random.random() < self.config.immediate_correction_rate
    
    def generate_correction_sequence(
        self,
        typo_position: int,
        current_position: int,
        correct_char: str
    ) -> List[Dict]:
        """
        Generate sequence of actions to correct a typo
        
        Returns:
            List of action dicts
        """
        actions = []
        
        # Calculate backspaces needed
        backspaces = current_position - typo_position
        
        if self.is_immediate_correction():
            # Immediate: just backspace and retype
            for _ in range(backspaces):
                actions.append({
                    'type': 'backspace',
                    'delay': random.uniform(50, 150)
                })
            
            # Retype correct character
            actions.append({
                'type': 'type',
                'char': correct_char,
                'delay': random.uniform(80, 200)
            })
        else:
            # Delayed: notice later, go back, fix, return
            actions.append({
                'type': 'pause',
                'duration': random.uniform(300, 800),
                'reason': 'noticing_error'
            })
            
            # Multiple backspaces
            for _ in range(backspaces):
                actions.append({
                    'type': 'backspace',
                    'delay': random.uniform(50, 150)
                })
            
            # Retype everything
            actions.append({
                'type': 'retype_needed',
                'from_position': typo_position
            })
        
        return actions


class ImperfectionEngine:
    """
    Main engine that coordinates all imperfection generators
    """
    
    def __init__(self, config: Optional[ImperfectionConfig] = None):
        self.config = config or ImperfectionConfig()
        
        self.typo = TypoGenerator(self.config)
        self.spacing = SpacingImperfections(self.config)
        self.punctuation = PunctuationImperfections(self.config)
        self.navigation = NavigationImperfections(self.config)
        self.hesitation = HesitationGenerator(self.config)
        self.correction = CorrectionSimulator(self.config)
        
        self._imperfection_log: List[Dict] = []
    
    def process_text(
        self,
        text: str,
        apply_typos: bool = True,
        apply_spacing: bool = True,
        apply_punctuation: bool = True
    ) -> Tuple[str, List[Dict]]:
        """
        Process text with imperfections
        
        Returns:
            (processed_text, imperfection_log)
        """
        imperfections = []
        
        # Apply typos
        if apply_typos:
            text, typo_log = self.typo.apply_typos(text)
            imperfections.extend(typo_log)
        
        # Apply spacing errors
        if apply_spacing:
            text = self.spacing.apply_spacing_errors(text)
        
        # Apply punctuation errors
        if apply_punctuation:
            text = self.punctuation.apply_punctuation_errors(text)
        
        self._imperfection_log.extend(imperfections)
        
        return text, imperfections
    
    def generate_typing_with_corrections(
        self,
        text: str
    ) -> List[Dict]:
        """
        Generate typing sequence with typos and corrections
        
        Returns:
            List of typing actions
        """
        actions = []
        
        for i, char in enumerate(text):
            # Check for hesitation
            if self.hesitation.should_hesitate():
                actions.append({
                    'type': 'pause',
                    'duration': self.hesitation.get_hesitation_duration()
                })
            
            # Check for long pause
            if self.hesitation.should_long_pause():
                actions.append({
                    'type': 'pause',
                    'duration': self.hesitation.get_long_pause_duration()
                })
            
            # Check for typo
            if char.isalpha() and random.random() < self.config.typo_rate:
                typo_char = self.typo.generate_typo(char)
                
                actions.append({
                    'type': 'type',
                    'char': typo_char,
                    'delay': random.uniform(50, 150)
                })
                
                # Correction
                if self.correction.should_correct():
                    if self.correction.is_immediate_correction():
                        # Immediate correction
                        actions.append({
                            'type': 'pause',
                            'duration': random.uniform(100, 300)
                        })
                        actions.append({
                            'type': 'backspace',
                            'delay': random.uniform(50, 150)
                        })
                        actions.append({
                            'type': 'type',
                            'char': char,
                            'delay': random.uniform(80, 200)
                        })
                    # Else: typo remains (will be corrected later or not at all)
            else:
                actions.append({
                    'type': 'type',
                    'char': char,
                    'delay': random.uniform(50, 150)
                })
        
        return actions
    
    def should_make_navigation_mistake(self) -> bool:
        """Check if navigation mistake should occur"""
        return self.navigation.should_make_wrong_click()
    
    def generate_navigation_mistake(self) -> Dict:
        """Generate a navigation mistake"""
        offset_x, offset_y = self.navigation.generate_wrong_click_offset()
        
        return {
            'type': 'wrong_click',
            'offset': (offset_x, offset_y),
            'will_go_back': self.navigation.should_go_back(),
            'recovery_delay': random.uniform(500, 1500)
        }
    
    def get_imperfection_stats(self) -> Dict:
        """Get statistics about generated imperfections"""
        stats = {
            'total': len(self._imperfection_log),
            'by_type': {}
        }
        
        for imp in self._imperfection_log:
            imp_type = imp.get('type', 'unknown')
            stats['by_type'][imp_type] = stats['by_type'].get(imp_type, 0) + 1
        
        return stats
    
    def clear_log(self) -> None:
        """Clear imperfection log"""
        self._imperfection_log = []
    
    def adjust_rates(self, fatigue_level: float) -> None:
        """
        Adjust imperfection rates based on fatigue
        
        Args:
            fatigue_level: 0.0 (fresh) to 1.0 (exhausted)
        """
        multiplier = 1 + fatigue_level
        
        self.config.typo_rate = min(0.1, 0.02 * multiplier)
        self.config.double_char_rate = min(0.02, 0.005 * multiplier)
        self.config.missing_char_rate = min(0.02, 0.005 * multiplier)
        self.config.hesitation_rate = min(0.15, 0.05 * multiplier)


# Global instance
_imperfection_engine: Optional[ImperfectionEngine] = None


def get_imperfection_engine(
    config: Optional[ImperfectionConfig] = None
) -> ImperfectionEngine:
    """Get global imperfection engine"""
    global _imperfection_engine
    if _imperfection_engine is None:
        _imperfection_engine = ImperfectionEngine(config)
    return _imperfection_engine


def add_imperfections(text: str) -> str:
    """Quick function to add imperfections to text"""
    engine = get_imperfection_engine()
    result, _ = engine.process_text(text)
    return result
