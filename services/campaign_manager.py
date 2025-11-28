"""
Enhanced Campaign Manager
Manages outreach campaigns to all 93,141 volunteers using both visible and hidden databases
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .volunteer_data_service import VolunteerDataService
from .async_task_manager import AsyncTaskManager
from ..database.database_manager import DatabaseManager
from ..utils.credential_manager import CredentialManager

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
    """Target criteria for campaign"""
    locations: List[str]
    categories: List[str]
    skills: List[str]
    volunteer_types: List[str]  # ['visible', 'hidden', 'both']
    max_volunteers: int
    exclude_contacted: bool = True

@dataclass
class CampaignMessage:
    """Campaign message template"""
    subject: str
    content: str
    message_type: MessageType
    personalization_fields: List[str]
    
class CampaignManager:
    """
    Comprehensive campaign management for reaching all volunteers
    Handles both visible volunteer direct contact and hidden volunteer triggering
    """
    
    def __init__(self, volunteer_service: VolunteerDataService, 
                 task_manager: AsyncTaskManager, db_manager: DatabaseManager):
        self.volunteer_service = volunteer_service
        self.task_manager = task_manager
        self.db_manager = db_manager
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Campaign tracking
        self.active_campaigns = {}
        self.campaign_stats = {}
    
    def create_campaign(self, name: str, target: CampaignTarget, 
                       message: CampaignMessage, schedule: Optional[Dict] = None) -> str:
        """
        Create a new outreach campaign
        """
        try:
            campaign_id = f"campaign_{int(time.time())}"
            
            campaign_data = {
                'id': campaign_id,
                'name': name,
                'target': target,
                'message': message,
                'schedule': schedule,
                'status': CampaignStatus.DRAFT,
                'created_at': datetime.now().isoformat(),
                'statistics': {
                    'total_targeted': 0,
                    'visible_targeted': 0,
                    'hidden_targeted': 0,
                    'messages_sent': 0,
                    'responses_received': 0,
                    'success_rate': 0.0
                }
            }
            
            # Store campaign in database
            self.db_manager.create_campaign(campaign_data)
            self.active_campaigns[campaign_id] = campaign_data
            
            self.logger.info(f"Created campaign: {name} ({campaign_id})")
            return campaign_id
            
        except Exception as e:
            self.logger.error(f"Error creating campaign: {str(e)}")
            return ""
    
    def start_campaign(self, campaign_id: str) -> bool:
        """
        Start executing a campaign
        """
        try:
            if campaign_id not in self.active_campaigns:
                self.logger.error(f"Campaign {campaign_id} not found")
                return False
                
            campaign = self.active_campaigns[campaign_id]
            campaign['status'] = CampaignStatus.ACTIVE
            campaign['started_at'] = datetime.now().isoformat()
            
            # Get target volunteers
            target_volunteers = self._get_target_volunteers(campaign['target'])
            campaign['statistics']['total_targeted'] = len(target_volunteers['all'])
            campaign['statistics']['visible_targeted'] = len(target_volunteers['visible'])
            campaign['statistics']['hidden_targeted'] = len(target_volunteers['hidden'])
            
            # Execute campaign based on volunteer types
            if target_volunteers['visible']:
                self._execute_visible_volunteer_campaign(campaign_id, target_volunteers['visible'])
                
            if target_volunteers['hidden']:
                self._execute_hidden_volunteer_campaign(campaign_id, target_volunteers['hidden'])
            
            self.logger.info(f"Started campaign {campaign_id} targeting {len(target_volunteers['all'])} volunteers")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting campaign: {str(e)}")
            return False
    
    def _get_target_volunteers(self, target: CampaignTarget) -> Dict[str, List[Dict]]:
        """
        Get volunteers matching campaign target criteria
        """
        target_volunteers = {
            'all': [],
            'visible': [],
            'hidden': []
        }
        
        try:
            # Build search criteria
            search_criteria = {
                'locations': target.locations,
                'categories': target.categories,
                'skills': target.skills,
                'limit': target.max_volunteers,
                'exclude_contacted': target.exclude_contacted
            }
            
            # Get all volunteers matching criteria
            all_volunteers = self.volunteer_service.get_all_volunteers(
                location=','.join(target.locations) if target.locations else "",
                category=','.join(target.categories) if target.categories else ""
            )
            
            # Filter by volunteer types requested
            if 'visible' in target.volunteer_types or 'both' in target.volunteer_types:
                visible_volunteers = all_volunteers['visible_volunteers']
                target_volunteers['visible'] = self._filter_volunteers(visible_volunteers, search_criteria)
                
            if 'hidden' in target.volunteer_types or 'both' in target.volunteer_types:
                hidden_volunteers = all_volunteers['hidden_volunteers']
                target_volunteers['hidden'] = self._filter_volunteers(hidden_volunteers, search_criteria)
            
            # Combine all targeted volunteers
            target_volunteers['all'] = target_volunteers['visible'] + target_volunteers['hidden']
            
            return target_volunteers
            
        except Exception as e:
            self.logger.error(f"Error getting target volunteers: {str(e)}")
            return target_volunteers
    
    def _filter_volunteers(self, volunteers: List[Dict], criteria: Dict) -> List[Dict]:
        """
        Filter volunteers based on search criteria
        """
        filtered = []
        
        for volunteer in volunteers:
            # Location filter
            if criteria.get('locations'):
                if not any(loc.lower() in volunteer.get('location', '').lower() 
                          for loc in criteria['locations']):
                    continue
            
            # Category filter
            if criteria.get('categories'):
                volunteer_skills = volunteer.get('skills', [])
                if not any(cat.lower() in skill.lower() 
                          for cat in criteria['categories'] 
                          for skill in volunteer_skills):
                    continue
            
            # Skills filter
            if criteria.get('skills'):
                volunteer_skills = volunteer.get('skills', [])
                if not any(skill.lower() in volunteer_skill.lower() 
                          for skill in criteria['skills'] 
                          for volunteer_skill in volunteer_skills):
                    continue
            
            # Exclude previously contacted
            if criteria.get('exclude_contacted'):
                if self.db_manager.was_volunteer_contacted(volunteer.get('id')):
                    continue
            
            filtered.append(volunteer)
            
            # Limit results
            if len(filtered) >= criteria.get('limit', 1000):
                break
        
        return filtered
    
    def _execute_visible_volunteer_campaign(self, campaign_id: str, volunteers: List[Dict]):
        """
        Execute campaign for visible volunteers (direct messaging)
        """
        try:
            campaign = self.active_campaigns[campaign_id]
            message_template = campaign['message']
            
            # Create async tasks for each volunteer
            tasks = []
            for volunteer in volunteers:
                task = self.task_manager.create_task(
                    name=f"message_volunteer_{volunteer.get('id')}",
                    function=self._send_direct_message,
                    args=(campaign_id, volunteer, message_template),
                    priority=1
                )
                tasks.append(task)
            
            # Execute tasks with rate limiting
            self.task_manager.execute_batch(tasks, max_concurrent=5, delay_between=2)
            
            self.logger.info(f"Queued {len(tasks)} direct messages for campaign {campaign_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing visible volunteer campaign: {str(e)}")
    
    def _execute_hidden_volunteer_campaign(self, campaign_id: str, volunteers: List[Dict]):
        """
        Execute campaign for hidden volunteers (strategic request posting)
        """
        try:
            campaign = self.active_campaigns[campaign_id]
            message_template = campaign['message']
            
            # Group hidden volunteers by category for strategic requests
            volunteer_groups = self._group_volunteers_by_category(volunteers)
            
            # Create strategic requests for each group
            tasks = []
            for category, group_volunteers in volunteer_groups.items():
                task = self.task_manager.create_task(
                    name=f"strategic_request_{category}",
                    function=self._post_strategic_request,
                    args=(campaign_id, category, group_volunteers, message_template),
                    priority=2
                )
                tasks.append(task)
            
            # Execute strategic request tasks
            self.task_manager.execute_batch(tasks, max_concurrent=2, delay_between=10)
            
            self.logger.info(f"Queued {len(tasks)} strategic requests for campaign {campaign_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing hidden volunteer campaign: {str(e)}")
    
    def _group_volunteers_by_category(self, volunteers: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group volunteers by their primary category for strategic targeting
        """
        groups = {}
        
        for volunteer in volunteers:
            skills = volunteer.get('skills', [])
            primary_category = skills[0] if skills else 'general'
            
            if primary_category not in groups:
                groups[primary_category] = []
            groups[primary_category].append(volunteer)
        
        return groups
    
    async def _send_direct_message(self, campaign_id: str, volunteer: Dict, message_template: CampaignMessage):
        """
        Send direct message to visible volunteer
        """
        try:
            # Personalize message
            personalized_message = self._personalize_message(message_template, volunteer)
            
            # Get volunteer contact information
            contact_info = self.volunteer_service.get_volunteer_contact_info(volunteer.get('id'))
            
            if not contact_info:
                self.logger.warning(f"No contact info for volunteer {volunteer.get('id')}")
                return False
            
            # Send message through platform
            success = await self._send_platform_message(contact_info, personalized_message)
            
            if success:
                # Record successful contact
                self.db_manager.record_volunteer_contact(
                    volunteer_id=volunteer.get('id'),
                    campaign_id=campaign_id,
                    message_type='direct_message',
                    success=True
                )
                
                # Update campaign statistics
                campaign = self.active_campaigns[campaign_id]
                campaign['statistics']['messages_sent'] += 1
                
                self.logger.info(f"Sent message to volunteer {volunteer.get('name')}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error sending direct message: {str(e)}")
            return False
    
    async def _post_strategic_request(self, campaign_id: str, category: str, 
                                    volunteers: List[Dict], message_template: CampaignMessage):
        """
        Post strategic request to trigger hidden volunteer responses
        """
        try:
            # Create strategic request based on volunteer category
            strategic_request = self._create_strategic_request(category, volunteers, message_template)
            
            # Post request through volunteer service
            success = await self._post_platform_request(strategic_request)
            
            if success:
                # Record strategic request
                for volunteer in volunteers:
                    self.db_manager.record_volunteer_contact(
                        volunteer_id=volunteer.get('id'),
                        campaign_id=campaign_id,
                        message_type='strategic_request',
                        success=True
                    )
                
                # Update campaign statistics
                campaign = self.active_campaigns[campaign_id]
                campaign['statistics']['messages_sent'] += 1
                
                self.logger.info(f"Posted strategic request for {category} targeting {len(volunteers)} volunteers")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error posting strategic request: {str(e)}")
            return False
    
    def _personalize_message(self, message_template: CampaignMessage, volunteer: Dict) -> Dict:
        """
        Personalize message content for specific volunteer
        """
        personalized = {
            'subject': message_template.subject,
            'content': message_template.content
        }
        
        # Replace personalization fields
        for field in message_template.personalization_fields:
            placeholder = f"{{{field}}}"
            value = volunteer.get(field, f"[{field}]")
            
            personalized['subject'] = personalized['subject'].replace(placeholder, str(value))
            personalized['content'] = personalized['content'].replace(placeholder, str(value))
        
        return personalized
    
    def _create_strategic_request(self, category: str, volunteers: List[Dict], 
                                message_template: CampaignMessage) -> Dict:
        """
        Create strategic request to appeal to specific volunteer category
        """
        # Strategic request templates by category
        strategic_templates = {
            'Computerhulp & ICT': {
                'title': 'Hulp bij digitale vaardigheden voor senioren',
                'description': 'Zoeken vrijwilligers om senioren te helpen met computers, smartphones en internet'
            },
            'Boodschappen': {
                'title': 'Begeleiding bij boodschappen doen',
                'description': 'Hulp nodig bij wekelijkse boodschappen voor mensen met beperkte mobiliteit'
            },
            'Taal & lezen': {
                'title': 'Nederlandse taalondersteuning',
                'description': 'Taalles en conversatie voor mensen die Nederlands willen leren'
            },
            'Klussen buiten & tuin': {
                'title': 'Tuinonderhoud en kleine klusjes',
                'description': 'Hulp bij tuinwerk en onderhoud buitenshuis'
            },
            'Maatje, buddy & gezelschap': {
                'title': 'Gezelschap en sociale activiteiten',
                'description': 'Zoek iemand voor gezellige gesprekken en sociale activiteiten'
            }
        }
        
        template = strategic_templates.get(category, {
            'title': 'Vrijwilligershulp gezocht',
            'description': 'Zoeken enthousiaste vrijwilligers voor diverse activiteiten'
        })
        
        return {
            'title': template['title'],
            'description': template['description'],
            'category': category,
            'target_volunteers': len(volunteers)
        }
    
    async def _send_platform_message(self, contact_info: Dict, message: Dict) -> bool:
        """
        Send message through NLvoorElkaar platform
        """
        try:
            # Implementation would use the volunteer service to send actual messages
            # This is a placeholder for the actual messaging implementation
            
            # Simulate message sending with rate limiting
            await asyncio.sleep(1)
            
            # In real implementation, this would:
            # 1. Navigate to volunteer profile
            # 2. Click message button
            # 3. Fill message form
            # 4. Send message
            # 5. Confirm delivery
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending platform message: {str(e)}")
            return False
    
    async def _post_platform_request(self, request_data: Dict) -> bool:
        """
        Post request through NLvoorElkaar platform
        """
        try:
            # Implementation would use the volunteer service to post actual requests
            # This is a placeholder for the actual request posting implementation
            
            # Simulate request posting with rate limiting
            await asyncio.sleep(5)
            
            # In real implementation, this would:
            # 1. Navigate to request posting page
            # 2. Fill request form
            # 3. Submit request
            # 4. Monitor for responses
            # 5. Extract responding volunteer information
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error posting platform request: {str(e)}")
            return False
    
    def get_campaign_status(self, campaign_id: str) -> Optional[Dict]:
        """
        Get current status and statistics for a campaign
        """
        try:
            if campaign_id not in self.active_campaigns:
                return None
                
            campaign = self.active_campaigns[campaign_id]
            
            # Update statistics from database
            stats = self.db_manager.get_campaign_statistics(campaign_id)
            campaign['statistics'].update(stats)
            
            return campaign
            
        except Exception as e:
            self.logger.error(f"Error getting campaign status: {str(e)}")
            return None
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """
        Pause an active campaign
        """
        try:
            if campaign_id not in self.active_campaigns:
                return False
                
            campaign = self.active_campaigns[campaign_id]
            campaign['status'] = CampaignStatus.PAUSED
            campaign['paused_at'] = datetime.now().isoformat()
            
            # Cancel pending tasks
            self.task_manager.cancel_campaign_tasks(campaign_id)
            
            self.logger.info(f"Paused campaign {campaign_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error pausing campaign: {str(e)}")
            return False
    
    def resume_campaign(self, campaign_id: str) -> bool:
        """
        Resume a paused campaign
        """
        try:
            if campaign_id not in self.active_campaigns:
                return False
                
            campaign = self.active_campaigns[campaign_id]
            if campaign['status'] != CampaignStatus.PAUSED:
                return False
                
            campaign['status'] = CampaignStatus.ACTIVE
            campaign['resumed_at'] = datetime.now().isoformat()
            
            # Restart campaign execution
            return self.start_campaign(campaign_id)
            
        except Exception as e:
            self.logger.error(f"Error resuming campaign: {str(e)}")
            return False
    
    def get_all_campaigns(self) -> List[Dict]:
        """
        Get all campaigns with their current status
        """
        try:
            campaigns = []
            for campaign_id, campaign_data in self.active_campaigns.items():
                # Update statistics
                stats = self.db_manager.get_campaign_statistics(campaign_id)
                campaign_data['statistics'].update(stats)
                campaigns.append(campaign_data)
                
            return campaigns
            
        except Exception as e:
            self.logger.error(f"Error getting all campaigns: {str(e)}")
            return []
    
    def get_comprehensive_statistics(self) -> Dict:
        """
        Get comprehensive statistics across all campaigns
        """
        try:
            stats = {
                'total_campaigns': len(self.active_campaigns),
                'active_campaigns': len([c for c in self.active_campaigns.values() 
                                       if c['status'] == CampaignStatus.ACTIVE]),
                'total_volunteers_targeted': 0,
                'total_messages_sent': 0,
                'total_responses_received': 0,
                'overall_success_rate': 0.0,
                'volunteer_database_access': {
                    'total_accessible': 93141,
                    'visible_accessible': 5518,
                    'hidden_accessible': 87624,
                    'access_methods': [
                        'Direct messaging (visible volunteers)',
                        'Strategic request posting (hidden volunteers)',
                        'API endpoint analysis',
                        'Network request monitoring'
                    ]
                }
            }
            
            # Aggregate statistics from all campaigns
            for campaign in self.active_campaigns.values():
                campaign_stats = campaign['statistics']
                stats['total_volunteers_targeted'] += campaign_stats['total_targeted']
                stats['total_messages_sent'] += campaign_stats['messages_sent']
                stats['total_responses_received'] += campaign_stats['responses_received']
            
            # Calculate overall success rate
            if stats['total_messages_sent'] > 0:
                stats['overall_success_rate'] = (stats['total_responses_received'] / 
                                                stats['total_messages_sent']) * 100
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting comprehensive statistics: {str(e)}")
            return {}
