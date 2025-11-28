"""
Automated Synchronization Service
Maintains up-to-date volunteer database with daily change detection
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import hashlib

from .volunteer_data_service import VolunteerDataService
from ..database.database_manager import DatabaseManager
from ..utils.backup_manager import BackupManager

class ChangeType(Enum):
    NEW_VOLUNTEER = "new_volunteer"
    REMOVED_VOLUNTEER = "removed_volunteer"
    UPDATED_VOLUNTEER = "updated_volunteer"
    PROFILE_CHANGE = "profile_change"
    CONTACT_CHANGE = "contact_change"

@dataclass
class VolunteerChange:
    """Represents a change in volunteer data"""
    volunteer_id: str
    change_type: ChangeType
    old_data: Optional[Dict]
    new_data: Optional[Dict]
    detected_at: datetime
    field_changes: List[str]

@dataclass
class SyncReport:
    """Daily synchronization report"""
    sync_date: datetime
    total_volunteers_before: int
    total_volunteers_after: int
    new_volunteers: int
    removed_volunteers: int
    updated_volunteers: int
    changes_detected: List[VolunteerChange]
    sync_duration: float
    success: bool
    errors: List[str]

class SyncService:
    """
    Automated synchronization service for maintaining up-to-date volunteer database
    
    Features:
    - Daily automated synchronization
    - New volunteer detection
    - Removed account identification
    - Profile change tracking
    - Data integrity validation
    - Automated reporting
    """
    
    def __init__(self, volunteer_service: VolunteerDataService, 
                 db_manager: DatabaseManager, backup_manager: BackupManager):
        self.volunteer_service = volunteer_service
        self.db_manager = db_manager
        self.backup_manager = backup_manager
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Sync configuration
        self.sync_config = {
            'daily_sync_time': '02:00',  # 2 AM daily sync
            'max_sync_duration': 3600,   # 1 hour max sync time
            'batch_size': 100,           # Process 100 volunteers at a time
            'retry_attempts': 3,         # Retry failed operations 3 times
            'change_detection_fields': [
                'name', 'location', 'skills', 'description', 
                'contact_info', 'availability', 'last_active'
            ]
        }
        
        # Sync state tracking
        self.last_sync_time = None
        self.sync_in_progress = False
        self.sync_history = []
    
    async def perform_daily_sync(self) -> SyncReport:
        """
        Perform comprehensive daily synchronization
        """
        sync_start_time = datetime.now()
        self.sync_in_progress = True
        
        try:
            self.logger.info("Starting daily volunteer database synchronization")
            
            # Create pre-sync backup
            backup_id = self.backup_manager.create_backup(f"pre_sync_{sync_start_time.strftime('%Y%m%d_%H%M%S')}")
            
            # Get current database state
            current_volunteers = self.db_manager.get_all_volunteers()
            total_before = len(current_volunteers)
            
            # Get fresh volunteer data from platform
            fresh_data = await self._fetch_fresh_volunteer_data()
            
            # Detect changes
            changes = await self._detect_changes(current_volunteers, fresh_data)
            
            # Apply changes to database
            await self._apply_changes(changes)
            
            # Get updated database state
            updated_volunteers = self.db_manager.get_all_volunteers()
            total_after = len(updated_volunteers)
            
            # Calculate statistics
            new_count = len([c for c in changes if c.change_type == ChangeType.NEW_VOLUNTEER])
            removed_count = len([c for c in changes if c.change_type == ChangeType.REMOVED_VOLUNTEER])
            updated_count = len([c for c in changes if c.change_type == ChangeType.UPDATED_VOLUNTEER])
            
            sync_duration = (datetime.now() - sync_start_time).total_seconds()
            
            # Create sync report
            report = SyncReport(
                sync_date=sync_start_time,
                total_volunteers_before=total_before,
                total_volunteers_after=total_after,
                new_volunteers=new_count,
                removed_volunteers=removed_count,
                updated_volunteers=updated_count,
                changes_detected=changes,
                sync_duration=sync_duration,
                success=True,
                errors=[]
            )
            
            # Store sync report
            self._store_sync_report(report)
            
            # Update sync state
            self.last_sync_time = sync_start_time
            self.sync_history.append(report)
            
            self.logger.info(f"Daily sync completed successfully in {sync_duration:.2f} seconds")
            self.logger.info(f"Changes: +{new_count} new, -{removed_count} removed, ~{updated_count} updated")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Daily sync failed: {str(e)}")
            
            # Create error report
            report = SyncReport(
                sync_date=sync_start_time,
                total_volunteers_before=len(current_volunteers) if 'current_volunteers' in locals() else 0,
                total_volunteers_after=0,
                new_volunteers=0,
                removed_volunteers=0,
                updated_volunteers=0,
                changes_detected=[],
                sync_duration=(datetime.now() - sync_start_time).total_seconds(),
                success=False,
                errors=[str(e)]
            )
            
            return report
            
        finally:
            self.sync_in_progress = False
    
    async def _fetch_fresh_volunteer_data(self) -> Dict[str, List[Dict]]:
        """
        Fetch fresh volunteer data from the platform
        """
        try:
            self.logger.info("Fetching fresh volunteer data from platform")
            
            # Get all volunteers using both visible and hidden access methods
            fresh_data = self.volunteer_service.get_all_volunteers()
            
            # Add data freshness timestamp
            timestamp = datetime.now().isoformat()
            for volunteer in fresh_data['visible_volunteers']:
                volunteer['data_fetched_at'] = timestamp
                volunteer['data_hash'] = self._calculate_volunteer_hash(volunteer)
            
            for volunteer in fresh_data['hidden_volunteers']:
                volunteer['data_fetched_at'] = timestamp
                volunteer['data_hash'] = self._calculate_volunteer_hash(volunteer)
            
            self.logger.info(f"Fetched {fresh_data['total_count']} volunteers from platform")
            return fresh_data
            
        except Exception as e:
            self.logger.error(f"Error fetching fresh volunteer data: {str(e)}")
            raise
    
    async def _detect_changes(self, current_volunteers: List[Dict], 
                            fresh_data: Dict[str, List[Dict]]) -> List[VolunteerChange]:
        """
        Detect changes between current database and fresh platform data
        """
        changes = []
        
        try:
            self.logger.info("Detecting changes in volunteer database")
            
            # Create lookup dictionaries
            current_lookup = {v.get('id', v.get('name', '')): v for v in current_volunteers}
            
            # Combine fresh data
            fresh_volunteers = fresh_data['visible_volunteers'] + fresh_data['hidden_volunteers']
            fresh_lookup = {v.get('id', v.get('name', '')): v for v in fresh_volunteers}
            
            # Detect new volunteers
            for volunteer_id, volunteer_data in fresh_lookup.items():
                if volunteer_id not in current_lookup:
                    changes.append(VolunteerChange(
                        volunteer_id=volunteer_id,
                        change_type=ChangeType.NEW_VOLUNTEER,
                        old_data=None,
                        new_data=volunteer_data,
                        detected_at=datetime.now(),
                        field_changes=['all']
                    ))
            
            # Detect removed volunteers
            for volunteer_id, volunteer_data in current_lookup.items():
                if volunteer_id not in fresh_lookup:
                    # Verify removal by checking if profile still exists
                    if await self._verify_volunteer_removal(volunteer_data):
                        changes.append(VolunteerChange(
                            volunteer_id=volunteer_id,
                            change_type=ChangeType.REMOVED_VOLUNTEER,
                            old_data=volunteer_data,
                            new_data=None,
                            detected_at=datetime.now(),
                            field_changes=['all']
                        ))
            
            # Detect updated volunteers
            for volunteer_id in set(current_lookup.keys()) & set(fresh_lookup.keys()):
                current_data = current_lookup[volunteer_id]
                fresh_data_item = fresh_lookup[volunteer_id]
                
                field_changes = self._detect_field_changes(current_data, fresh_data_item)
                
                if field_changes:
                    changes.append(VolunteerChange(
                        volunteer_id=volunteer_id,
                        change_type=ChangeType.UPDATED_VOLUNTEER,
                        old_data=current_data,
                        new_data=fresh_data_item,
                        detected_at=datetime.now(),
                        field_changes=field_changes
                    ))
            
            self.logger.info(f"Detected {len(changes)} changes in volunteer database")
            return changes
            
        except Exception as e:
            self.logger.error(f"Error detecting changes: {str(e)}")
            raise
    
    def _detect_field_changes(self, old_data: Dict, new_data: Dict) -> List[str]:
        """
        Detect specific field changes between old and new volunteer data
        """
        field_changes = []
        
        for field in self.sync_config['change_detection_fields']:
            old_value = old_data.get(field)
            new_value = new_data.get(field)
            
            # Handle different data types
            if isinstance(old_value, list) and isinstance(new_value, list):
                if set(old_value) != set(new_value):
                    field_changes.append(field)
            elif old_value != new_value:
                field_changes.append(field)
        
        # Check data hash for comprehensive change detection
        old_hash = old_data.get('data_hash')
        new_hash = self._calculate_volunteer_hash(new_data)
        
        if old_hash != new_hash and not field_changes:
            field_changes.append('data_hash')
        
        return field_changes
    
    def _calculate_volunteer_hash(self, volunteer_data: Dict) -> str:
        """
        Calculate hash of volunteer data for change detection
        """
        # Create normalized data for hashing
        hash_data = {}
        for field in self.sync_config['change_detection_fields']:
            value = volunteer_data.get(field)
            if isinstance(value, list):
                hash_data[field] = sorted(value)
            else:
                hash_data[field] = value
        
        # Calculate hash
        data_string = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.md5(data_string.encode()).hexdigest()
    
    async def _verify_volunteer_removal(self, volunteer_data: Dict) -> bool:
        """
        Verify if a volunteer has actually been removed from the platform
        """
        try:
            # Check if volunteer profile still exists
            profile_url = volunteer_data.get('profile_url')
            if not profile_url:
                return True  # No profile URL means we can't verify, assume removed
            
            # Try to access the volunteer's profile
            contact_info = self.volunteer_service.get_volunteer_contact_info(volunteer_data.get('id'))
            
            # If we can't get contact info, the volunteer might be removed
            return contact_info is None
            
        except Exception as e:
            self.logger.warning(f"Could not verify volunteer removal: {str(e)}")
            return False  # Conservative approach - don't remove if we can't verify
    
    async def _apply_changes(self, changes: List[VolunteerChange]):
        """
        Apply detected changes to the database
        """
        try:
            self.logger.info(f"Applying {len(changes)} changes to database")
            
            for change in changes:
                if change.change_type == ChangeType.NEW_VOLUNTEER:
                    self.db_manager.add_volunteer(change.new_data)
                    self.logger.info(f"Added new volunteer: {change.new_data.get('name')}")
                
                elif change.change_type == ChangeType.REMOVED_VOLUNTEER:
                    self.db_manager.remove_volunteer(change.volunteer_id)
                    self.logger.info(f"Removed volunteer: {change.old_data.get('name')}")
                
                elif change.change_type == ChangeType.UPDATED_VOLUNTEER:
                    self.db_manager.update_volunteer(change.volunteer_id, change.new_data)
                    self.logger.info(f"Updated volunteer: {change.new_data.get('name')} (fields: {', '.join(change.field_changes)})")
                
                # Record change in history
                self.db_manager.record_volunteer_change(change)
            
            self.logger.info("Successfully applied all changes to database")
            
        except Exception as e:
            self.logger.error(f"Error applying changes: {str(e)}")
            raise
    
    def _store_sync_report(self, report: SyncReport):
        """
        Store synchronization report in database
        """
        try:
            report_data = {
                'sync_date': report.sync_date.isoformat(),
                'total_volunteers_before': report.total_volunteers_before,
                'total_volunteers_after': report.total_volunteers_after,
                'new_volunteers': report.new_volunteers,
                'removed_volunteers': report.removed_volunteers,
                'updated_volunteers': report.updated_volunteers,
                'sync_duration': report.sync_duration,
                'success': report.success,
                'errors': report.errors,
                'changes_count': len(report.changes_detected)
            }
            
            self.db_manager.store_sync_report(report_data)
            self.logger.info("Stored sync report in database")
            
        except Exception as e:
            self.logger.error(f"Error storing sync report: {str(e)}")
    
    def get_sync_status(self) -> Dict:
        """
        Get current synchronization status
        """
        try:
            status = {
                'sync_in_progress': self.sync_in_progress,
                'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
                'next_sync_time': self._calculate_next_sync_time().isoformat(),
                'sync_history_count': len(self.sync_history),
                'database_stats': self.db_manager.get_volunteer_statistics(),
                'sync_config': self.sync_config
            }
            
            # Add recent sync results
            if self.sync_history:
                recent_sync = self.sync_history[-1]
                status['last_sync_result'] = {
                    'success': recent_sync.success,
                    'new_volunteers': recent_sync.new_volunteers,
                    'removed_volunteers': recent_sync.removed_volunteers,
                    'updated_volunteers': recent_sync.updated_volunteers,
                    'duration': recent_sync.sync_duration
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting sync status: {str(e)}")
            return {}
    
    def _calculate_next_sync_time(self) -> datetime:
        """
        Calculate the next scheduled sync time
        """
        now = datetime.now()
        sync_time_parts = self.sync_config['daily_sync_time'].split(':')
        sync_hour = int(sync_time_parts[0])
        sync_minute = int(sync_time_parts[1])
        
        # Calculate next sync time
        next_sync = now.replace(hour=sync_hour, minute=sync_minute, second=0, microsecond=0)
        
        # If sync time has passed today, schedule for tomorrow
        if next_sync <= now:
            next_sync += timedelta(days=1)
        
        return next_sync
    
    def get_sync_history(self, days: int = 30) -> List[Dict]:
        """
        Get synchronization history for the specified number of days
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            history = []
            for report in self.sync_history:
                if report.sync_date >= cutoff_date:
                    history.append({
                        'sync_date': report.sync_date.isoformat(),
                        'success': report.success,
                        'new_volunteers': report.new_volunteers,
                        'removed_volunteers': report.removed_volunteers,
                        'updated_volunteers': report.updated_volunteers,
                        'total_changes': len(report.changes_detected),
                        'duration': report.sync_duration,
                        'errors': report.errors
                    })
            
            return sorted(history, key=lambda x: x['sync_date'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error getting sync history: {str(e)}")
            return []
    
    def get_change_details(self, sync_date: str) -> List[Dict]:
        """
        Get detailed change information for a specific sync date
        """
        try:
            target_date = datetime.fromisoformat(sync_date)
            
            for report in self.sync_history:
                if report.sync_date.date() == target_date.date():
                    changes = []
                    for change in report.changes_detected:
                        changes.append({
                            'volunteer_id': change.volunteer_id,
                            'volunteer_name': (change.new_data or change.old_data or {}).get('name', 'Unknown'),
                            'change_type': change.change_type.value,
                            'field_changes': change.field_changes,
                            'detected_at': change.detected_at.isoformat()
                        })
                    return changes
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting change details: {str(e)}")
            return []
    
    async def force_sync(self) -> SyncReport:
        """
        Force an immediate synchronization (outside of scheduled time)
        """
        try:
            if self.sync_in_progress:
                raise Exception("Synchronization already in progress")
            
            self.logger.info("Starting forced synchronization")
            return await self.perform_daily_sync()
            
        except Exception as e:
            self.logger.error(f"Forced sync failed: {str(e)}")
            raise
    
    def get_volunteer_change_history(self, volunteer_id: str) -> List[Dict]:
        """
        Get change history for a specific volunteer
        """
        try:
            return self.db_manager.get_volunteer_change_history(volunteer_id)
        except Exception as e:
            self.logger.error(f"Error getting volunteer change history: {str(e)}")
            return []
    
    def get_database_integrity_report(self) -> Dict:
        """
        Generate database integrity report
        """
        try:
            all_volunteers = self.db_manager.get_all_volunteers()
            
            integrity_report = {
                'total_volunteers': len(all_volunteers),
                'volunteers_with_contact_info': 0,
                'volunteers_with_skills': 0,
                'volunteers_with_location': 0,
                'duplicate_volunteers': 0,
                'orphaned_records': 0,
                'data_quality_score': 0.0,
                'last_updated_distribution': {},
                'issues_found': []
            }
            
            # Analyze data quality
            seen_names = set()
            for volunteer in all_volunteers:
                # Check for contact info
                if volunteer.get('contact_info') or volunteer.get('email') or volunteer.get('phone'):
                    integrity_report['volunteers_with_contact_info'] += 1
                
                # Check for skills
                if volunteer.get('skills'):
                    integrity_report['volunteers_with_skills'] += 1
                
                # Check for location
                if volunteer.get('location'):
                    integrity_report['volunteers_with_location'] += 1
                
                # Check for duplicates
                name = volunteer.get('name', '').lower()
                if name in seen_names:
                    integrity_report['duplicate_volunteers'] += 1
                    integrity_report['issues_found'].append(f"Duplicate volunteer name: {volunteer.get('name')}")
                seen_names.add(name)
            
            # Calculate data quality score
            if len(all_volunteers) > 0:
                quality_factors = [
                    integrity_report['volunteers_with_contact_info'] / len(all_volunteers),
                    integrity_report['volunteers_with_skills'] / len(all_volunteers),
                    integrity_report['volunteers_with_location'] / len(all_volunteers),
                    1 - (integrity_report['duplicate_volunteers'] / len(all_volunteers))
                ]
                integrity_report['data_quality_score'] = sum(quality_factors) / len(quality_factors) * 100
            
            return integrity_report
            
        except Exception as e:
            self.logger.error(f"Error generating integrity report: {str(e)}")
            return {}
