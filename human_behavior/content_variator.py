"""
Human-Like Content Variator

Generates varied message content that mimics human writing patterns
with Dutch language support, synonym substitution, and personalization.
"""

import random
import re
import logging
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from string import Template

logger = logging.getLogger(__name__)


class PersonalizationLevel(Enum):
    """Levels of message personalization"""
    NONE = 0
    NAME_ONLY = 1
    LOCATION = 2
    SKILLS = 3
    DETAILED = 4
    CUSTOM = 5


@dataclass
class VolunteerProfile:
    """Volunteer profile data for personalization"""
    name: str
    location: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    availability: Optional[str] = None
    description: Optional[str] = None
    profile_url: Optional[str] = None


class DutchSynonyms:
    """
    Dutch synonym database for natural variation
    """
    
    SYNONYMS = {
        # Greetings
        "hallo": ["hoi", "hey", "dag"],
        "goedemorgen": ["goedenmorgen", "goede morgen"],
        "goedemiddag": ["goede middag"],
        "goedenavond": ["goede avond"],
        
        # Positive adjectives
        "interessant": ["boeiend", "leuk", "mooi", "fijn"],
        "geweldig": ["fantastisch", "prachtig", "uitstekend", "super"],
        "goed": ["prima", "fijn", "mooi", "uitstekend"],
        "leuk": ["fijn", "prettig", "aangenaam", "tof"],
        
        # Verbs
        "zoeken": ["op zoek zijn naar", "willen vinden"],
        "helpen": ["bijstaan", "ondersteunen", "assisteren"],
        "contact opnemen": ["bereiken", "benaderen", "aanschrijven"],
        "reageren": ["antwoorden", "terugkomen op"],
        
        # Phrases
        "ik zou graag": ["ik wil graag", "graag zou ik", "het lijkt me leuk om"],
        "met vriendelijke groet": ["hartelijke groet", "groeten", "met vriendelijke groeten"],
        "bij voorbaat dank": ["alvast bedankt", "dank bij voorbaat", "alvast hartelijk dank"],
        "ik hoop": ["hopelijk", "ik verwacht", "naar ik hoop"],
        
        # Connectors
        "daarom": ["vandaar", "om die reden", "dat is waarom"],
        "ook": ["eveneens", "tevens", "daarnaast"],
        "maar": ["echter", "alleen", "wel"],
        "omdat": ["aangezien", "doordat", "daar"],
        
        # Time references
        "binnenkort": ["spoedig", "op korte termijn", "in de nabije toekomst"],
        "snel": ["spoedig", "vlug", "gauw"],
    }
    
    @classmethod
    def get_synonym(cls, word: str, probability: float = 0.3) -> str:
        """
        Get a synonym for a word with given probability
        
        Args:
            word: Original word
            probability: Chance of substitution (0-1)
        
        Returns:
            Original word or synonym
        """
        if random.random() > probability:
            return word
        
        word_lower = word.lower()
        if word_lower in cls.SYNONYMS:
            synonym = random.choice(cls.SYNONYMS[word_lower])
            
            # Preserve capitalization
            if word[0].isupper():
                synonym = synonym.capitalize()
            
            return synonym
        
        return word
    
    @classmethod
    def vary_text(cls, text: str, intensity: float = 0.3) -> str:
        """
        Apply synonym variation to text
        
        Args:
            text: Original text
            intensity: How aggressively to substitute (0-1)
        
        Returns:
            Varied text
        """
        words = text.split()
        varied_words = []
        
        for word in words:
            # Strip punctuation for lookup
            stripped = word.rstrip('.,!?;:')
            punct = word[len(stripped):]
            
            varied = cls.get_synonym(stripped, intensity)
            varied_words.append(varied + punct)
        
        return ' '.join(varied_words)


class DutchGreetings:
    """
    Dutch greeting variations based on time of day
    """
    
    MORNING = [
        "Goedemorgen",
        "Goede morgen",
        "Hallo",
        "Beste",
    ]
    
    AFTERNOON = [
        "Goedemiddag",
        "Goede middag",
        "Hallo",
        "Beste",
    ]
    
    EVENING = [
        "Goedenavond",
        "Goede avond",
        "Hallo",
        "Beste",
    ]
    
    NEUTRAL = [
        "Hallo",
        "Beste",
        "Dag",
        "Hi",
        "Hey",
    ]
    
    @classmethod
    def get_greeting(cls, hour: Optional[int] = None, formal: bool = True) -> str:
        """
        Get appropriate greeting for time of day
        
        Time-based greetings (Dutch convention):
        - Goedemorgen: 06:00 - 12:00
        - Goedemiddag: 12:00 - 18:00
        - Goedenavond: 18:00 - 22:00 (operating hours end at 22:00)
        
        NOTE: Messages are ONLY sent during operating hours (09:00 - 22:00)
        so we will never need greetings for 00:00 - 06:00.
        
        Args:
            hour: Hour of day (0-23), None for current
            formal: Whether to prefer formal greetings
        
        Raises:
            ValueError: If called outside operating hours (should never happen)
        """
        from datetime import datetime
        
        if hour is None:
            hour = datetime.now().hour
        
        # Safety check: We should NEVER be sending messages outside 09:00-22:00
        if hour < 9 or hour >= 22:
            logger.warning(f"get_greeting called outside operating hours (hour={hour}). This should not happen!")
            # Fallback to neutral greeting if somehow called outside hours
            return "Beste" if formal else "Hallo"
        
        if formal:
            # Formal greetings - use time-appropriate Dutch greetings
            if 9 <= hour < 12:
                # Morning: 09:00 - 12:00
                options = cls.MORNING[:2]  # Goedemorgen, Goede morgen
            elif 12 <= hour < 18:
                # Afternoon: 12:00 - 18:00
                options = cls.AFTERNOON[:2]  # Goedemiddag, Goede middag
            else:
                # Evening: 18:00 - 22:00
                options = cls.EVENING[:2]  # Goedenavond, Goede avond
        else:
            # Informal greetings - include casual options
            if 9 <= hour < 12:
                # Morning: 09:00 - 12:00
                options = cls.MORNING
            elif 12 <= hour < 18:
                # Afternoon: 12:00 - 18:00
                options = cls.AFTERNOON
            else:
                # Evening: 18:00 - 22:00
                options = cls.EVENING
        
        return random.choice(options)


class DutchClosings:
    """
    Dutch closing variations
    """
    
    FORMAL = [
        "Met vriendelijke groet",
        "Met vriendelijke groeten",
        "Hartelijke groet",
        "Hartelijke groeten",
        "Met hartelijke groet",
    ]
    
    SEMI_FORMAL = [
        "Groeten",
        "Groetjes",
        "Vriendelijke groet",
        "Met groet",
    ]
    
    INFORMAL = [
        "Groetjes",
        "Liefs",
        "Tot snel",
        "Tot gauw",
    ]
    
    @classmethod
    def get_closing(cls, formal: bool = True) -> str:
        """Get appropriate closing"""
        if formal:
            return random.choice(cls.FORMAL)
        else:
            return random.choice(cls.SEMI_FORMAL + cls.INFORMAL)


class MessageTemplates:
    """
    Message templates with variation support
    """
    
    # Initial outreach templates
    INITIAL_OUTREACH = [
        {
            "template": """{greeting} {name},

{intro_line}

{body}

{closing_line}

{closing},
{sender_name}""",
            "variations": {
                "intro_line": [
                    "Ik zag uw profiel op NLvoorElkaar en wilde graag contact met u opnemen.",
                    "Via NLvoorElkaar kwam ik uw profiel tegen en dat sprak me aan.",
                    "Uw profiel op NLvoorElkaar trok mijn aandacht.",
                    "Ik kwam uw profiel tegen op NLvoorElkaar en vond het interessant.",
                ],
                "closing_line": [
                    "Ik hoor graag van u.",
                    "Hopelijk tot snel!",
                    "Ik kijk uit naar uw reactie.",
                    "Laat gerust weten als u interesse heeft.",
                    "Ik ben benieuwd naar uw reactie.",
                ]
            }
        },
        {
            "template": """{greeting} {name},

{personalized_intro}

{body}

{question}

{closing},
{sender_name}""",
            "variations": {
                "personalized_intro": [
                    "Leuk dat u zich als vrijwilliger heeft aangemeld{location_ref}.",
                    "Fijn om te zien dat u vrijwilligerswerk doet{location_ref}.",
                    "Mooi dat u actief bent als vrijwilliger{location_ref}.",
                ],
                "question": [
                    "Zou u interesse hebben om hierover te praten?",
                    "Heeft u tijd voor een kort gesprek hierover?",
                    "Kunnen we hierover in contact komen?",
                    "Zou u hier meer over willen weten?",
                ]
            }
        }
    ]
    
    # Follow-up templates
    FOLLOW_UP = [
        {
            "template": """{greeting} {name},

{follow_up_intro}

{body}

{closing},
{sender_name}""",
            "variations": {
                "follow_up_intro": [
                    "Ik wilde even terugkomen op mijn eerdere bericht.",
                    "Naar aanleiding van mijn vorige bericht wilde ik nog even contact opnemen.",
                    "Ik hoop dat mijn eerdere bericht goed is aangekomen.",
                ]
            }
        }
    ]
    
    # Reply templates
    REPLY = [
        {
            "template": """{greeting} {name},

{thanks_line}

{body}

{closing},
{sender_name}""",
            "variations": {
                "thanks_line": [
                    "Bedankt voor uw reactie!",
                    "Dank voor uw bericht.",
                    "Fijn dat u reageert!",
                    "Leuk om van u te horen.",
                ]
            }
        }
    ]


class ContentVariator:
    """
    Main content variation engine
    """
    
    def __init__(self, sender_name: str = ""):
        self.sender_name = sender_name
        self.synonyms = DutchSynonyms()
        self.greetings = DutchGreetings()
        self.closings = DutchClosings()
        self.templates = MessageTemplates()
        
        # Track used variations to avoid repetition
        self._used_templates: List[int] = []
        self._used_greetings: List[str] = []
        self._message_count = 0
    
    def generate_message(
        self,
        volunteer: VolunteerProfile,
        body: str,
        message_type: str = "initial",
        personalization_level: PersonalizationLevel = PersonalizationLevel.LOCATION,
        formal: bool = True
    ) -> str:
        """
        Generate a varied message
        
        Args:
            volunteer: Volunteer profile data
            body: Main message body
            message_type: "initial", "follow_up", or "reply"
            personalization_level: How much to personalize
            formal: Use formal language
        
        Returns:
            Generated message
        """
        # Select template
        if message_type == "initial":
            templates = self.templates.INITIAL_OUTREACH
        elif message_type == "follow_up":
            templates = self.templates.FOLLOW_UP
        else:
            templates = self.templates.REPLY
        
        template_data = self._select_template(templates)
        
        # Build message components
        greeting = self._get_greeting(volunteer.name, formal)
        closing = self.closings.get_closing(formal)
        
        # Build personalization
        location_ref = self._build_location_ref(volunteer, personalization_level)
        skill_ref = self._build_skill_ref(volunteer, personalization_level)
        
        # Select variations
        variations = {}
        for key, options in template_data.get("variations", {}).items():
            selected = random.choice(options)
            # Apply location reference if placeholder exists
            selected = selected.replace("{location_ref}", location_ref)
            variations[key] = selected
        
        # Apply synonym variation to body
        varied_body = self.synonyms.vary_text(body, intensity=0.2)
        
        # Add personalization to body if appropriate
        if personalization_level.value >= PersonalizationLevel.SKILLS.value and skill_ref:
            varied_body = f"{skill_ref} {varied_body}"
        
        # Build final message
        message = template_data["template"].format(
            greeting=greeting,
            name=volunteer.name,
            body=varied_body,
            closing=closing,
            sender_name=self.sender_name,
            **variations
        )
        
        # Apply final variations
        message = self._apply_punctuation_variation(message)
        message = self._apply_spacing_variation(message)
        
        self._message_count += 1
        
        return message.strip()
    
    def vary_existing_message(
        self,
        message: str,
        intensity: float = 0.3
    ) -> str:
        """
        Apply variation to an existing message
        
        Args:
            message: Original message
            intensity: Variation intensity (0-1)
        
        Returns:
            Varied message
        """
        # Apply synonym variation
        varied = self.synonyms.vary_text(message, intensity)
        
        # Apply punctuation variation
        varied = self._apply_punctuation_variation(varied)
        
        return varied
    
    def personalize_template(
        self,
        template: str,
        volunteer: VolunteerProfile,
        extra_vars: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Fill in a template with volunteer data
        
        Args:
            template: Template string with {placeholders}
            volunteer: Volunteer profile
            extra_vars: Additional variables
        
        Returns:
            Filled template
        """
        vars_dict = {
            "name": volunteer.name,
            "voornaam": volunteer.name.split()[0] if volunteer.name else "",
            "location": volunteer.location or "",
            "stad": volunteer.location or "",
            "skills": ", ".join(volunteer.skills) if volunteer.skills else "",
            "vaardigheden": ", ".join(volunteer.skills) if volunteer.skills else "",
        }
        
        if extra_vars:
            vars_dict.update(extra_vars)
        
        # Use safe substitution to handle missing keys
        t = Template(template)
        try:
            result = t.safe_substitute(vars_dict)
        except Exception:
            result = template
        
        return result
    
    def get_message_length_category(self) -> str:
        """
        Get random message length category based on distribution
        
        Returns:
            "short", "medium", or "long"
        """
        r = random.random()
        if r < 0.2:
            return "short"
        elif r < 0.8:
            return "medium"
        else:
            return "long"
    
    def adjust_message_length(
        self,
        message: str,
        target_category: str
    ) -> str:
        """
        Adjust message to fit target length category
        
        Args:
            message: Original message
            target_category: "short", "medium", or "long"
        
        Returns:
            Adjusted message
        """
        current_length = len(message)
        
        targets = {
            "short": (50, 150),
            "medium": (150, 300),
            "long": (300, 500)
        }
        
        min_len, max_len = targets.get(target_category, (150, 300))
        
        if current_length < min_len:
            # Add filler phrases
            fillers = [
                " Ik hoop dat dit duidelijk is.",
                " Laat gerust weten als u vragen heeft.",
                " Ik kijk uit naar uw reactie.",
            ]
            while len(message) < min_len and fillers:
                message += random.choice(fillers)
                fillers.remove(fillers[-1])
        
        elif current_length > max_len:
            # Truncate at sentence boundary
            sentences = re.split(r'(?<=[.!?])\s+', message)
            truncated = ""
            for sentence in sentences:
                if len(truncated) + len(sentence) <= max_len:
                    truncated += sentence + " "
                else:
                    break
            message = truncated.strip()
        
        return message
    
    def _select_template(self, templates: List[dict]) -> dict:
        """Select a template, avoiding recent ones"""
        available = list(range(len(templates)))
        
        # Remove recently used
        for used in self._used_templates[-3:]:
            if used in available and len(available) > 1:
                available.remove(used)
        
        idx = random.choice(available)
        self._used_templates.append(idx)
        
        return templates[idx]
    
    def _get_greeting(self, name: str, formal: bool) -> str:
        """Get greeting, avoiding recent ones"""
        greeting = self.greetings.get_greeting(formal=formal)
        
        # Avoid repetition
        attempts = 0
        while greeting in self._used_greetings[-3:] and attempts < 5:
            greeting = self.greetings.get_greeting(formal=formal)
            attempts += 1
        
        self._used_greetings.append(greeting)
        return greeting
    
    def _build_location_ref(
        self,
        volunteer: VolunteerProfile,
        level: PersonalizationLevel
    ) -> str:
        """Build location reference if appropriate"""
        if level.value < PersonalizationLevel.LOCATION.value:
            return ""
        
        if not volunteer.location:
            return ""
        
        options = [
            f" in {volunteer.location}",
            f" uit {volunteer.location}",
            f" in de regio {volunteer.location}",
        ]
        
        return random.choice(options)
    
    def _build_skill_ref(
        self,
        volunteer: VolunteerProfile,
        level: PersonalizationLevel
    ) -> str:
        """Build skill reference if appropriate"""
        if level.value < PersonalizationLevel.SKILLS.value:
            return ""
        
        if not volunteer.skills:
            return ""
        
        skill = random.choice(volunteer.skills)
        
        options = [
            f"Ik zag dat u ervaring heeft met {skill}.",
            f"Uw ervaring met {skill} viel me op.",
            f"Interessant dat u actief bent in {skill}.",
        ]
        
        return random.choice(options)
    
    def _apply_punctuation_variation(self, text: str) -> str:
        """Apply natural punctuation variation"""
        # Occasionally miss final period (5% chance)
        if random.random() < 0.05 and text.endswith('.'):
            text = text[:-1]
        
        # Variable exclamation marks
        if random.random() < 0.1:
            text = text.replace('!', '.')
        
        return text
    
    def _apply_spacing_variation(self, text: str) -> str:
        """Apply natural spacing variation"""
        # Occasional double space (3% chance per space)
        words = text.split(' ')
        result = []
        
        for i, word in enumerate(words):
            result.append(word)
            if i < len(words) - 1 and random.random() < 0.03:
                result.append('')  # Creates double space
        
        return ' '.join(result)
    
    def reset_tracking(self) -> None:
        """Reset variation tracking for new session"""
        self._used_templates = []
        self._used_greetings = []
        self._message_count = 0


# Convenience functions

def create_varied_message(
    volunteer_name: str,
    volunteer_location: Optional[str],
    body: str,
    sender_name: str,
    formal: bool = True
) -> str:
    """
    Quick function to create a varied message
    
    Args:
        volunteer_name: Recipient name
        volunteer_location: Recipient location
        body: Message body
        sender_name: Sender name
        formal: Use formal language
    
    Returns:
        Generated message
    """
    variator = ContentVariator(sender_name)
    volunteer = VolunteerProfile(
        name=volunteer_name,
        location=volunteer_location
    )
    
    return variator.generate_message(
        volunteer=volunteer,
        body=body,
        formal=formal
    )


def vary_text(text: str, intensity: float = 0.3) -> str:
    """Apply synonym variation to text"""
    return DutchSynonyms.vary_text(text, intensity)
