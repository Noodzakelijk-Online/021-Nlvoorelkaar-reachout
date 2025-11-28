"""
Data Models for NLvoorelkaar Tool
Provides clean interfaces for database operations
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
import json

@dataclass
class Volunteer:
    """Volunteer data model"""
    volunteer_id: str
    name: str = ""
    description: str = ""
    location: str = ""
    skills: str = ""
    categories: str = ""
    availability: str = ""
    contact_info: str = ""
    profile_url: str = ""
    scraped_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'volunteer_id': self.volunteer_id,
            'name': self.name,
            'description': self.description,
            'location': self.location,
            'skills': self.skills,
            'categories': self.categories,
            'availability': self.availability,
            'contact_info': self.contact_info,
            'profile_url': self.profile_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Volunteer':
        """Create from dictionary"""
        return cls(
            volunteer_id=data.get('volunteer_id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            location=data.get('location', ''),
            skills=data.get('skills', ''),
            categories=data.get('categories', ''),
            availability=data.get('availability', ''),
            contact_info=data.get('contact_info', ''),
            profile_url=data.get('profile_url', ''),
            scraped_at=data.get('scraped_at', datetime.now()),
            updated_at=data.get('updated_at', datetime.now())
        )
    
    def get_categories_list(self) -> List[str]:
        """Get categories as a list"""
        if self.categories:
            return [cat.strip() for cat in self.categories.split(',')]
        return []
    
    def get_skills_list(self) -> List[str]:
        """Get skills as a list"""
        if self.skills:
            return [skill.strip() for skill in self.skills.split(',')]
        return []
    
    def matches_criteria(self, categories: List[str] = None, location: str = None) -> bool:
        """Check if volunteer matches search criteria"""
        if categories:
            volunteer_categories = self.get_categories_list()
            if not any(cat in volunteer_categories for cat in categories):
                return False
        
        if location:
            if location.lower() not in self.location.lower():
                return False
        
        return True

@dataclass
class Campaign:
    """Campaign data model"""
    name: str
    description: str = ""
    target_categories: str = ""
    target_location: str = ""
    target_distance: int = 0
    message_template: str = ""
    status: str = "active"
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'name': self.name,
            'description': self.description,
            'target_categories': self.target_categories,
            'target_location': self.target_location,
            'target_distance': self.target_distance,
            'message_template': self.message_template,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Campaign':
        """Create from dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            target_categories=data.get('target_categories', ''),
            target_location=data.get('target_location', ''),
            target_distance=data.get('target_distance', 0),
            message_template=data.get('message_template', ''),
            status=data.get('status', 'active'),
            created_at=data.get('created_at', datetime.now()),
            updated_at=data.get('updated_at', datetime.now())
        )
    
    def get_target_categories_list(self) -> List[str]:
        """Get target categories as a list"""
        if self.target_categories:
            return [cat.strip() for cat in self.target_categories.split(',')]
        return []
    
    def personalize_message(self, volunteer: Volunteer) -> str:
        """Personalize message template for specific volunteer"""
        message = self.message_template
        
        # Replace placeholders with volunteer data
        replacements = {
            '{name}': volunteer.name or 'there',
            '{location}': volunteer.location or 'your area',
            '{skills}': volunteer.skills or 'your skills',
            '{categories}': volunteer.categories or 'volunteer work'
        }
        
        for placeholder, value in replacements.items():
            message = message.replace(placeholder, value)
        
        return message

@dataclass
class Contact:
    """Contact record data model"""
    volunteer_id: str
    campaign_id: Optional[int] = None
    message_sent: str = ""
    status: str = "sent"
    notes: str = ""
    response_received: bool = False
    response_date: Optional[datetime] = None
    response_content: str = ""
    id: Optional[int] = None
    contact_date: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'volunteer_id': self.volunteer_id,
            'campaign_id': self.campaign_id,
            'message_sent': self.message_sent,
            'status': self.status,
            'notes': self.notes,
            'response_received': self.response_received,
            'response_date': self.response_date,
            'response_content': self.response_content
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contact':
        """Create from dictionary"""
        return cls(
            id=data.get('id'),
            volunteer_id=data.get('volunteer_id', ''),
            campaign_id=data.get('campaign_id'),
            message_sent=data.get('message_sent', ''),
            status=data.get('status', 'sent'),
            notes=data.get('notes', ''),
            response_received=data.get('response_received', False),
            response_date=data.get('response_date'),
            response_content=data.get('response_content', ''),
            contact_date=data.get('contact_date', datetime.now())
        )
    
    def mark_response_received(self, response_content: str = ""):
        """Mark contact as having received a response"""
        self.response_received = True
        self.response_date = datetime.now()
        self.response_content = response_content
        self.status = "responded"

@dataclass
class BlacklistEntry:
    """Blacklist entry data model"""
    volunteer_id: str
    reason: str = ""
    id: Optional[int] = None
    added_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'volunteer_id': self.volunteer_id,
            'reason': self.reason
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlacklistEntry':
        """Create from dictionary"""
        return cls(
            id=data.get('id'),
            volunteer_id=data.get('volunteer_id', ''),
            reason=data.get('reason', ''),
            added_at=data.get('added_at', datetime.now())
        )

@dataclass
class CampaignStats:
    """Campaign statistics data model"""
    campaign_id: int
    campaign_name: str
    total_contacts: int = 0
    responses_received: int = 0
    response_rate: float = 0.0
    last_contact_date: Optional[datetime] = None
    
    def calculate_response_rate(self):
        """Calculate response rate percentage"""
        if self.total_contacts > 0:
            self.response_rate = (self.responses_received / self.total_contacts) * 100
        else:
            self.response_rate = 0.0

@dataclass
class VolunteerFilter:
    """Filter criteria for volunteer searches"""
    categories: List[str] = field(default_factory=list)
    location: str = ""
    distance: int = 0
    skills: List[str] = field(default_factory=list)
    not_contacted: bool = False
    not_blacklisted: bool = True
    search_term: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database queries"""
        filters = {}
        
        if self.categories:
            filters['categories'] = ','.join(self.categories)
        
        if self.location:
            filters['location'] = self.location
        
        if self.not_contacted:
            filters['not_contacted'] = True
        
        if self.not_blacklisted:
            filters['not_blacklisted'] = True
        
        return filters

class MessageTemplate:
    """Message template with personalization capabilities"""
    
    def __init__(self, template: str):
        self.template = template
        
    def personalize(self, volunteer: Volunteer, campaign: Campaign = None) -> str:
        """Personalize message for specific volunteer"""
        message = self.template
        
        # Basic personalizations
        replacements = {
            '{name}': volunteer.name or 'there',
            '{location}': volunteer.location or 'your area',
            '{skills}': volunteer.skills or 'your skills',
            '{categories}': volunteer.categories or 'volunteer work'
        }
        
        # Campaign-specific personalizations
        if campaign:
            replacements['{campaign_name}'] = campaign.name
            replacements['{campaign_description}'] = campaign.description
        
        # Apply replacements
        for placeholder, value in replacements.items():
            message = message.replace(placeholder, value)
        
        return message
    
    @staticmethod
    def get_default_templates() -> Dict[str, str]:
        """Get default message templates"""
        return {
            "general": """Hello {name},

I hope this message finds you well. I came across your volunteer profile and was impressed by your interest in {categories}.

We have an opportunity that might interest you in {location}. Your skills in {skills} would be valuable for our cause.

Would you be interested in learning more about this volunteer opportunity?

Best regards""",
            
            "event": """Hi {name},

We're organizing an upcoming event in {location} and would love to have volunteers like you involved.

Given your background in {categories}, I think you'd be a great fit for this opportunity.

The event will make use of skills like {skills}, which I noticed you have experience with.

Would you be available to help out? I'd be happy to provide more details.

Looking forward to hearing from you!""",
            
            "ongoing": """Dear {name},

I hope you're doing well. We have an ongoing volunteer program in {location} that could benefit from your expertise.

Your experience with {categories} and skills in {skills} make you an ideal candidate for this opportunity.

This is a flexible commitment that can work around your schedule.

Would you be interested in discussing this further?

Best wishes"""
        }

class DataValidator:
    """Validates data before database operations"""
    
    @staticmethod
    def validate_volunteer(volunteer_data: Dict[str, Any]) -> tuple[bool, str]:
        """Validate volunteer data"""
        if not volunteer_data.get('volunteer_id'):
            return False, "Volunteer ID is required"
        
        if len(volunteer_data.get('volunteer_id', '')) < 3:
            return False, "Volunteer ID must be at least 3 characters"
        
        return True, ""
    
    @staticmethod
    def validate_campaign(campaign_data: Dict[str, Any]) -> tuple[bool, str]:
        """Validate campaign data"""
        if not campaign_data.get('name'):
            return False, "Campaign name is required"
        
        if not campaign_data.get('message_template'):
            return False, "Message template is required"
        
        return True, ""
    
    @staticmethod
    def validate_contact(contact_data: Dict[str, Any]) -> tuple[bool, str]:
        """Validate contact data"""
        if not contact_data.get('volunteer_id'):
            return False, "Volunteer ID is required"
        
        if not contact_data.get('message_sent'):
            return False, "Message content is required"
        
        return True, ""

