"""
Enhanced Reminder and Blacklist Services
Addresses TODO items #6 and #7: Reminder and Blacklist Service Improvements
"""

import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# ENHANCED REMINDER SERVICE
# ============================================================================

class ReminderStatus(Enum):
    """Reminder status"""
    PENDING = "pending"
    SENT = "sent"
    RESPONDED = "responded"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class Reminder:
    """Reminder data structure"""
    id: Optional[int] = None
    volunteer_id: str = ""
    volunteer_name: str = ""
    original_message_id: Optional[int] = None
    reminder_count: int = 0
    max_reminders: int = 3
    interval_days: int = 7
    next_reminder_date: str = ""
    status: ReminderStatus = ReminderStatus.PENDING
    template_id: Optional[int] = None
    created_at: str = ""
    last_sent_at: Optional[str] = None
    responded_at: Optional[str] = None
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        return data


class ReminderTemplate:
    """Pre-built reminder templates with escalation"""
    
    TEMPLATES = {
        1: {
            'name': 'Eerste Herinnering',
            'subject': 'Herinnering: Vrijwilligerswerk',
            'body': '''Beste {name},

Ik had u eerder benaderd over vrijwilligerswerk. Ik wilde even opvolgen of u mijn bericht heeft ontvangen.

Ik hoor graag van u!

Met vriendelijke groet'''
        },
        2: {
            'name': 'Tweede Herinnering',
            'subject': 'Opvolging: Vrijwilligerswerk aanvraag',
            'body': '''Beste {name},

Dit is een vriendelijke herinnering over mijn eerdere berichten. Ik begrijp dat u het druk heeft, maar ik zou het zeer op prijs stellen als u even kon reageren.

Als u niet geïnteresseerd bent, laat het me dan ook weten zodat ik u niet meer lastig val.

Met vriendelijke groet'''
        },
        3: {
            'name': 'Laatste Herinnering',
            'subject': 'Laatste opvolging: Vrijwilligerswerk',
            'body': '''Beste {name},

Dit is mijn laatste poging om contact met u op te nemen over vrijwilligerswerk. 

Als ik niets van u hoor, ga ik ervan uit dat u niet geïnteresseerd bent en zal ik u niet meer benaderen.

Bedankt voor uw tijd.

Met vriendelijke groet'''
        }
    }


class EnhancedReminderService:
    """
    Enhanced reminder service with configurable intervals and smart timing
    
    Features:
    - Configurable reminder intervals
    - Smart timing (avoid off-hours)
    - Reminder effectiveness tracking
    - Multiple reminder templates
    - Escalation logic
    """
    
    # Smart timing settings
    BUSINESS_HOURS_START = 9
    BUSINESS_HOURS_END = 18
    PREFERRED_DAYS = [0, 1, 2, 3, 4]  # Monday to Friday
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize reminder database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    volunteer_id TEXT NOT NULL,
                    volunteer_name TEXT,
                    original_message_id INTEGER,
                    reminder_count INTEGER DEFAULT 0,
                    max_reminders INTEGER DEFAULT 3,
                    interval_days INTEGER DEFAULT 7,
                    next_reminder_date TEXT,
                    status TEXT DEFAULT 'pending',
                    template_id INTEGER,
                    created_at TEXT NOT NULL,
                    last_sent_at TEXT,
                    responded_at TEXT,
                    notes TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reminder_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reminder_id INTEGER,
                    reminder_number INTEGER,
                    sent_at TEXT,
                    response_received INTEGER DEFAULT 0,
                    response_time_hours REAL,
                    FOREIGN KEY (reminder_id) REFERENCES reminders(id)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_reminder_status 
                ON reminders(status)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_next_reminder 
                ON reminders(next_reminder_date)
            ''')
            
            conn.commit()
    
    def create_reminder(
        self,
        volunteer_id: str,
        volunteer_name: str = "",
        original_message_id: Optional[int] = None,
        interval_days: int = 7,
        max_reminders: int = 3,
        notes: str = ""
    ) -> int:
        """
        Create a new reminder schedule
        
        Args:
            volunteer_id: Volunteer ID
            volunteer_name: Volunteer name
            original_message_id: ID of original message sent
            interval_days: Days between reminders
            max_reminders: Maximum number of reminders
            notes: Optional notes
            
        Returns:
            Reminder ID
        """
        now = datetime.now()
        next_date = self._calculate_next_reminder_date(now, interval_days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO reminders 
                (volunteer_id, volunteer_name, original_message_id, interval_days,
                 max_reminders, next_reminder_date, status, created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            ''', (
                volunteer_id,
                volunteer_name,
                original_message_id,
                interval_days,
                max_reminders,
                next_date.isoformat(),
                now.isoformat(),
                notes
            ))
            conn.commit()
            
            logger.info(f"Created reminder {cursor.lastrowid} for {volunteer_id}")
            return cursor.lastrowid
    
    def _calculate_next_reminder_date(
        self,
        from_date: datetime,
        interval_days: int
    ) -> datetime:
        """Calculate next reminder date with smart timing"""
        next_date = from_date + timedelta(days=interval_days)
        
        # Adjust to business hours
        if next_date.hour < self.BUSINESS_HOURS_START:
            next_date = next_date.replace(
                hour=self.BUSINESS_HOURS_START,
                minute=0,
                second=0
            )
        elif next_date.hour >= self.BUSINESS_HOURS_END:
            next_date = next_date + timedelta(days=1)
            next_date = next_date.replace(
                hour=self.BUSINESS_HOURS_START,
                minute=0,
                second=0
            )
        
        # Avoid weekends
        while next_date.weekday() not in self.PREFERRED_DAYS:
            next_date = next_date + timedelta(days=1)
        
        return next_date
    
    def get_due_reminders(self) -> List[Reminder]:
        """Get reminders that are due to be sent"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM reminders 
                WHERE status = 'pending' 
                AND next_reminder_date <= ?
                AND reminder_count < max_reminders
                ORDER BY next_reminder_date ASC
            ''', (now,))
            
            reminders = []
            for row in cursor:
                data = dict(row)
                data['status'] = ReminderStatus(data['status'])
                reminders.append(Reminder(**{
                    k: v for k, v in data.items() 
                    if k in Reminder.__dataclass_fields__
                }))
            
            return reminders
    
    def mark_reminder_sent(self, reminder_id: int) -> None:
        """Mark a reminder as sent and schedule next"""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            # Get current reminder
            cursor = conn.execute(
                'SELECT * FROM reminders WHERE id = ?',
                (reminder_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return
            
            reminder_count = row[4] + 1  # Increment count
            max_reminders = row[5]
            interval_days = row[6]
            
            # Calculate next reminder date
            if reminder_count < max_reminders:
                next_date = self._calculate_next_reminder_date(now, interval_days)
                status = 'pending'
            else:
                next_date = None
                status = 'expired'
            
            # Update reminder
            conn.execute('''
                UPDATE reminders SET
                    reminder_count = ?,
                    next_reminder_date = ?,
                    status = ?,
                    last_sent_at = ?
                WHERE id = ?
            ''', (
                reminder_count,
                next_date.isoformat() if next_date else None,
                status,
                now.isoformat(),
                reminder_id
            ))
            
            # Record stats
            conn.execute('''
                INSERT INTO reminder_stats (reminder_id, reminder_number, sent_at)
                VALUES (?, ?, ?)
            ''', (reminder_id, reminder_count, now.isoformat()))
            
            conn.commit()
            
            logger.info(f"Reminder {reminder_id} sent (count: {reminder_count})")
    
    def mark_response_received(self, reminder_id: int) -> None:
        """Mark that a response was received"""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            # Update reminder status
            conn.execute('''
                UPDATE reminders SET
                    status = 'responded',
                    responded_at = ?
                WHERE id = ?
            ''', (now.isoformat(), reminder_id))
            
            # Update stats with response time
            cursor = conn.execute('''
                SELECT id, sent_at FROM reminder_stats 
                WHERE reminder_id = ? 
                ORDER BY reminder_number DESC LIMIT 1
            ''', (reminder_id,))
            
            row = cursor.fetchone()
            if row:
                sent_at = datetime.fromisoformat(row[1])
                response_hours = (now - sent_at).total_seconds() / 3600
                
                conn.execute('''
                    UPDATE reminder_stats SET
                        response_received = 1,
                        response_time_hours = ?
                    WHERE id = ?
                ''', (response_hours, row[0]))
            
            conn.commit()
            
            logger.info(f"Response received for reminder {reminder_id}")
    
    def cancel_reminder(self, reminder_id: int) -> bool:
        """Cancel a reminder"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'UPDATE reminders SET status = ? WHERE id = ? AND status = ?',
                ('cancelled', reminder_id, 'pending')
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_reminder_template(self, reminder_count: int) -> Dict[str, str]:
        """Get appropriate template based on reminder count"""
        template_num = min(reminder_count + 1, 3)
        return ReminderTemplate.TEMPLATES.get(template_num, ReminderTemplate.TEMPLATES[1])
    
    def get_effectiveness_stats(self) -> Dict[str, Any]:
        """Get reminder effectiveness statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Overall response rate
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'responded' THEN 1 ELSE 0 END) as responded
                FROM reminders
            ''')
            row = cursor.fetchone()
            total = row[0] or 1
            responded = row[1] or 0
            
            # Response rate by reminder number
            cursor = conn.execute('''
                SELECT 
                    reminder_number,
                    COUNT(*) as sent,
                    SUM(response_received) as responses,
                    AVG(response_time_hours) as avg_response_time
                FROM reminder_stats
                GROUP BY reminder_number
            ''')
            
            by_reminder = []
            for row in cursor:
                by_reminder.append({
                    'reminder_number': row[0],
                    'sent': row[1],
                    'responses': row[2] or 0,
                    'response_rate': (row[2] or 0) / row[1] * 100 if row[1] > 0 else 0,
                    'avg_response_time_hours': row[3]
                })
            
            return {
                'total_reminders': total,
                'total_responses': responded,
                'overall_response_rate': responded / total * 100,
                'by_reminder_number': by_reminder
            }


# ============================================================================
# ENHANCED BLACKLIST SERVICE
# ============================================================================

class BlacklistReason(Enum):
    """Reasons for blacklisting"""
    NO_RESPONSE = "no_response"
    REQUESTED_REMOVAL = "requested_removal"
    INVALID_CONTACT = "invalid_contact"
    DUPLICATE = "duplicate"
    SPAM_REPORTED = "spam_reported"
    OTHER = "other"


@dataclass
class BlacklistEntry:
    """Blacklist entry data structure"""
    id: Optional[int] = None
    profile_id: str = ""
    name: str = ""
    reason: BlacklistReason = BlacklistReason.OTHER
    notes: str = ""
    added_at: str = ""
    added_by: str = ""
    expires_at: Optional[str] = None
    is_permanent: bool = True
    contact_attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['reason'] = self.reason.value
        return data


class EnhancedBlacklistService:
    """
    Enhanced blacklist service with categories and temporary blacklisting
    
    Features:
    - Bulk import/export
    - Blacklist categories
    - Temporary blacklist with auto-removal
    - Search functionality
    - Notes for each entry
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize blacklist database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT UNIQUE NOT NULL,
                    name TEXT,
                    reason TEXT DEFAULT 'other',
                    notes TEXT,
                    added_at TEXT NOT NULL,
                    added_by TEXT,
                    expires_at TEXT,
                    is_permanent INTEGER DEFAULT 1,
                    contact_attempts INTEGER DEFAULT 0
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_blacklist_profile 
                ON blacklist(profile_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_blacklist_expires 
                ON blacklist(expires_at)
            ''')
            
            conn.commit()
    
    def add_to_blacklist(
        self,
        profile_id: str,
        name: str = "",
        reason: BlacklistReason = BlacklistReason.OTHER,
        notes: str = "",
        added_by: str = "",
        temporary_days: Optional[int] = None
    ) -> int:
        """
        Add a profile to the blacklist
        
        Args:
            profile_id: Profile ID to blacklist
            name: Profile name
            reason: Reason for blacklisting
            notes: Additional notes
            added_by: Who added this entry
            temporary_days: If set, entry expires after this many days
            
        Returns:
            Blacklist entry ID
        """
        profile_id = profile_id.strip()
        now = datetime.now()
        
        expires_at = None
        is_permanent = True
        
        if temporary_days:
            expires_at = (now + timedelta(days=temporary_days)).isoformat()
            is_permanent = False
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                cursor = conn.execute('''
                    INSERT INTO blacklist 
                    (profile_id, name, reason, notes, added_at, added_by, expires_at, is_permanent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    profile_id,
                    name,
                    reason.value,
                    notes,
                    now.isoformat(),
                    added_by,
                    expires_at,
                    1 if is_permanent else 0
                ))
                conn.commit()
                
                logger.info(f"Added {profile_id} to blacklist (reason: {reason.value})")
                return cursor.lastrowid
                
            except sqlite3.IntegrityError:
                # Already exists, update instead
                conn.execute('''
                    UPDATE blacklist SET
                        name = COALESCE(?, name),
                        reason = ?,
                        notes = ?,
                        expires_at = ?,
                        is_permanent = ?
                    WHERE profile_id = ?
                ''', (name, reason.value, notes, expires_at, 1 if is_permanent else 0, profile_id))
                conn.commit()
                
                logger.info(f"Updated blacklist entry for {profile_id}")
                return -1
    
    def remove_from_blacklist(self, profile_id: str) -> bool:
        """Remove a profile from the blacklist"""
        profile_id = profile_id.strip()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'DELETE FROM blacklist WHERE profile_id = ?',
                (profile_id,)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Removed {profile_id} from blacklist")
                return True
            return False
    
    def is_blacklisted(self, profile_id: str) -> bool:
        """Check if a profile is blacklisted"""
        profile_id = profile_id.strip()
        
        # First, clean up expired entries
        self._cleanup_expired()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT id FROM blacklist WHERE profile_id = ?',
                (profile_id,)
            )
            return cursor.fetchone() is not None
    
    def _cleanup_expired(self) -> int:
        """Remove expired temporary blacklist entries"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                DELETE FROM blacklist 
                WHERE is_permanent = 0 AND expires_at IS NOT NULL AND expires_at < ?
            ''', (now,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Cleaned up {cursor.rowcount} expired blacklist entries")
            
            return cursor.rowcount
    
    def get_blacklist_entry(self, profile_id: str) -> Optional[BlacklistEntry]:
        """Get blacklist entry details"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM blacklist WHERE profile_id = ?',
                (profile_id.strip(),)
            )
            row = cursor.fetchone()
            
            if row:
                data = dict(row)
                data['reason'] = BlacklistReason(data['reason'])
                data['is_permanent'] = bool(data['is_permanent'])
                return BlacklistEntry(**{
                    k: v for k, v in data.items() 
                    if k in BlacklistEntry.__dataclass_fields__
                })
        
        return None
    
    def search_blacklist(
        self,
        query: str = "",
        reason: Optional[BlacklistReason] = None,
        include_expired: bool = False,
        limit: int = 100
    ) -> List[BlacklistEntry]:
        """
        Search the blacklist
        
        Args:
            query: Search query (matches profile_id, name, notes)
            reason: Filter by reason
            include_expired: Include expired temporary entries
            limit: Maximum results
            
        Returns:
            List of matching blacklist entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            conditions = []
            params = []
            
            if query:
                conditions.append(
                    '(profile_id LIKE ? OR name LIKE ? OR notes LIKE ?)'
                )
                query_param = f'%{query}%'
                params.extend([query_param, query_param, query_param])
            
            if reason:
                conditions.append('reason = ?')
                params.append(reason.value)
            
            if not include_expired:
                conditions.append(
                    '(is_permanent = 1 OR expires_at IS NULL OR expires_at > ?)'
                )
                params.append(datetime.now().isoformat())
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            
            cursor = conn.execute(f'''
                SELECT * FROM blacklist 
                WHERE {where_clause}
                ORDER BY added_at DESC
                LIMIT ?
            ''', params + [limit])
            
            entries = []
            for row in cursor:
                data = dict(row)
                data['reason'] = BlacklistReason(data['reason'])
                data['is_permanent'] = bool(data['is_permanent'])
                entries.append(BlacklistEntry(**{
                    k: v for k, v in data.items() 
                    if k in BlacklistEntry.__dataclass_fields__
                }))
            
            return entries
    
    def bulk_import(
        self,
        entries: List[Dict[str, Any]],
        default_reason: BlacklistReason = BlacklistReason.OTHER
    ) -> Dict[str, int]:
        """
        Bulk import blacklist entries
        
        Args:
            entries: List of entry dictionaries with at least 'profile_id'
            default_reason: Default reason if not specified
            
        Returns:
            Statistics dictionary
        """
        stats = {'added': 0, 'updated': 0, 'failed': 0}
        
        for entry in entries:
            try:
                profile_id = entry.get('profile_id', '').strip()
                if not profile_id:
                    stats['failed'] += 1
                    continue
                
                reason = BlacklistReason(entry.get('reason', default_reason.value))
                
                result = self.add_to_blacklist(
                    profile_id=profile_id,
                    name=entry.get('name', ''),
                    reason=reason,
                    notes=entry.get('notes', ''),
                    added_by=entry.get('added_by', 'bulk_import'),
                    temporary_days=entry.get('temporary_days')
                )
                
                if result > 0:
                    stats['added'] += 1
                else:
                    stats['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error importing blacklist entry: {e}")
                stats['failed'] += 1
        
        logger.info(f"Bulk import complete: {stats}")
        return stats
    
    def bulk_export(
        self,
        reason: Optional[BlacklistReason] = None
    ) -> List[Dict[str, Any]]:
        """
        Export blacklist entries
        
        Args:
            reason: Optional filter by reason
            
        Returns:
            List of entry dictionaries
        """
        entries = self.search_blacklist(reason=reason, include_expired=True, limit=100000)
        return [e.to_dict() for e in entries]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get blacklist statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Total count
            cursor = conn.execute('SELECT COUNT(*) FROM blacklist')
            total = cursor.fetchone()[0]
            
            # By reason
            cursor = conn.execute('''
                SELECT reason, COUNT(*) as count 
                FROM blacklist 
                GROUP BY reason
            ''')
            by_reason = {row[0]: row[1] for row in cursor}
            
            # Temporary vs permanent
            cursor = conn.execute('''
                SELECT is_permanent, COUNT(*) as count 
                FROM blacklist 
                GROUP BY is_permanent
            ''')
            by_type = {
                'permanent': 0,
                'temporary': 0
            }
            for row in cursor:
                if row[0]:
                    by_type['permanent'] = row[1]
                else:
                    by_type['temporary'] = row[1]
            
            return {
                'total': total,
                'by_reason': by_reason,
                'by_type': by_type
            }
    
    def increment_contact_attempts(self, profile_id: str) -> None:
        """Increment contact attempt counter"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE blacklist 
                SET contact_attempts = contact_attempts + 1 
                WHERE profile_id = ?
            ''', (profile_id.strip(),))
            conn.commit()
