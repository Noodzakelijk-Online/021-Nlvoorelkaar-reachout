"""
Enhanced Messaging Service with Templates, Scheduling, and Preview
Addresses TODO items #5: Messaging Service Improvements
"""

import os
import re
import json
import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class TemplateVariable(Enum):
    """Available template variables"""
    NAME = "{name}"
    FIRST_NAME = "{first_name}"
    LOCATION = "{location}"
    SKILLS = "{skills}"
    DATE = "{date}"
    TIME = "{time}"
    ORGANIZATION = "{organization}"
    CUSTOM_1 = "{custom_1}"
    CUSTOM_2 = "{custom_2}"
    CUSTOM_3 = "{custom_3}"


@dataclass
class MessageTemplate:
    """Message template with variable support"""
    id: Optional[int] = None
    name: str = ""
    subject: str = ""
    body: str = ""
    category: str = "general"
    variables: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    use_count: int = 0
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageTemplate':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_variables(self) -> List[str]:
        """Extract variables from template body"""
        pattern = r'\{(\w+)\}'
        return list(set(re.findall(pattern, self.body + self.subject)))


@dataclass
class ScheduledMessage:
    """Scheduled message data"""
    id: Optional[int] = None
    template_id: Optional[int] = None
    recipient_id: str = ""
    recipient_name: str = ""
    subject: str = ""
    body: str = ""
    scheduled_time: str = ""
    status: str = "scheduled"  # scheduled, sent, failed, cancelled
    created_at: str = ""
    sent_at: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['metadata'] = json.dumps(self.metadata)
        return data


class MessageTemplateManager:
    """
    Manages message templates with variable substitution
    
    Features:
    - Create and manage message templates
    - Variable substitution ({name}, {location}, etc.)
    - Template categories
    - Usage tracking
    """
    
    # Default templates
    DEFAULT_TEMPLATES = [
        {
            'name': 'Eerste Contact',
            'subject': 'Interesse in vrijwilligerswerk',
            'body': '''Beste {name},

Ik zag uw profiel op NLvoorElkaar en ben geïnteresseerd in uw aanbod voor vrijwilligerswerk in {location}.

Zou u mij meer kunnen vertellen over de mogelijkheden?

Met vriendelijke groet''',
            'category': 'outreach'
        },
        {
            'name': 'Follow-up',
            'subject': 'Opvolging - Vrijwilligerswerk',
            'body': '''Beste {name},

Ik had u eerder benaderd over vrijwilligerswerk. Ik wilde even opvolgen of u mijn eerdere bericht heeft ontvangen.

Ik hoor graag van u.

Met vriendelijke groet''',
            'category': 'follow_up'
        },
        {
            'name': 'Bedankt',
            'subject': 'Bedankt voor uw reactie',
            'body': '''Beste {name},

Hartelijk dank voor uw reactie. Ik waardeer het zeer dat u de tijd heeft genomen om te reageren.

{custom_1}

Met vriendelijke groet''',
            'category': 'thank_you'
        }
    ]
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        self._init_default_templates()
    
    def _init_db(self) -> None:
        """Initialize template database"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS message_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    subject TEXT,
                    body TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    variables TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    use_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            conn.commit()
    
    def _init_default_templates(self) -> None:
        """Initialize default templates if none exist"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM message_templates')
            if cursor.fetchone()[0] == 0:
                now = datetime.now().isoformat()
                for template in self.DEFAULT_TEMPLATES:
                    variables = self._extract_variables(template['body'] + template.get('subject', ''))
                    conn.execute('''
                        INSERT INTO message_templates 
                        (name, subject, body, category, variables, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        template['name'],
                        template.get('subject', ''),
                        template['body'],
                        template.get('category', 'general'),
                        json.dumps(variables),
                        now,
                        now
                    ))
                conn.commit()
                logger.info(f"Initialized {len(self.DEFAULT_TEMPLATES)} default templates")
    
    def _extract_variables(self, text: str) -> List[str]:
        """Extract variable names from text"""
        pattern = r'\{(\w+)\}'
        return list(set(re.findall(pattern, text)))
    
    def create_template(
        self,
        name: str,
        body: str,
        subject: str = "",
        category: str = "general"
    ) -> int:
        """Create a new template"""
        now = datetime.now().isoformat()
        variables = self._extract_variables(body + subject)
        
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute('''
                INSERT INTO message_templates 
                (name, subject, body, category, variables, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, subject, body, category, json.dumps(variables), now, now))
            conn.commit()
            return cursor.lastrowid
    
    def update_template(
        self,
        template_id: int,
        name: Optional[str] = None,
        body: Optional[str] = None,
        subject: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """Update an existing template"""
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if body is not None:
            updates.append('body = ?')
            params.append(body)
        if subject is not None:
            updates.append('subject = ?')
            params.append(subject)
        if category is not None:
            updates.append('category = ?')
            params.append(category)
        
        if not updates:
            return False
        
        # Update variables if body or subject changed
        if body is not None or subject is not None:
            template = self.get_template(template_id)
            if template:
                new_body = body if body is not None else template.body
                new_subject = subject if subject is not None else template.subject
                variables = self._extract_variables(new_body + new_subject)
                updates.append('variables = ?')
                params.append(json.dumps(variables))
        
        updates.append('updated_at = ?')
        params.append(datetime.now().isoformat())
        params.append(template_id)
        
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                f'UPDATE message_templates SET {", ".join(updates)} WHERE id = ?',
                params
            )
            conn.commit()
        
        return True
    
    def get_template(self, template_id: int) -> Optional[MessageTemplate]:
        """Get a template by ID"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM message_templates WHERE id = ?',
                (template_id,)
            )
            row = cursor.fetchone()
            if row:
                data = dict(row)
                data['variables'] = json.loads(data.get('variables') or '[]')
                data['is_active'] = bool(data.get('is_active', 1))
                return MessageTemplate.from_dict(data)
        return None
    
    def get_templates(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[MessageTemplate]:
        """Get all templates"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            query = 'SELECT * FROM message_templates WHERE 1=1'
            params = []
            
            if active_only:
                query += ' AND is_active = 1'
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            query += ' ORDER BY use_count DESC, name ASC'
            
            cursor = conn.execute(query, params)
            templates = []
            for row in cursor:
                data = dict(row)
                data['variables'] = json.loads(data.get('variables') or '[]')
                data['is_active'] = bool(data.get('is_active', 1))
                templates.append(MessageTemplate.from_dict(data))
            
            return templates
    
    def delete_template(self, template_id: int) -> bool:
        """Soft delete a template"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                'UPDATE message_templates SET is_active = 0 WHERE id = ?',
                (template_id,)
            )
            conn.commit()
        return True
    
    def increment_use_count(self, template_id: int) -> None:
        """Increment template use count"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                'UPDATE message_templates SET use_count = use_count + 1 WHERE id = ?',
                (template_id,)
            )
            conn.commit()
    
    def render_template(
        self,
        template_id: int,
        variables: Dict[str, str]
    ) -> tuple[str, str]:
        """
        Render a template with variable substitution
        
        Args:
            template_id: Template ID
            variables: Dictionary of variable values
            
        Returns:
            Tuple of (rendered_subject, rendered_body)
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        subject = template.subject
        body = template.body
        
        # Substitute variables
        for var_name, var_value in variables.items():
            placeholder = '{' + var_name + '}'
            subject = subject.replace(placeholder, str(var_value))
            body = body.replace(placeholder, str(var_value))
        
        # Remove any remaining unsubstituted variables
        pattern = r'\{(\w+)\}'
        subject = re.sub(pattern, '', subject)
        body = re.sub(pattern, '', body)
        
        self.increment_use_count(template_id)
        
        return subject, body


class MessageScheduler:
    """
    Message scheduling system
    
    Features:
    - Schedule messages for future delivery
    - Recurring message support
    - Smart timing (avoid off-hours)
    - Batch scheduling
    """
    
    # Business hours (when messages should be sent)
    BUSINESS_HOURS_START = 9
    BUSINESS_HOURS_END = 18
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._send_callback: Optional[Callable[[ScheduledMessage], bool]] = None
        self._is_running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize scheduler database"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id INTEGER,
                    recipient_id TEXT NOT NULL,
                    recipient_name TEXT,
                    subject TEXT,
                    body TEXT NOT NULL,
                    scheduled_time TEXT NOT NULL,
                    status TEXT DEFAULT 'scheduled',
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_scheduled_time 
                ON scheduled_messages(scheduled_time)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status 
                ON scheduled_messages(status)
            ''')
            
            conn.commit()
    
    def set_send_callback(self, callback: Callable[[ScheduledMessage], bool]) -> None:
        """Refuse legacy callback-based sending outside the outreach ledger."""
        raise RuntimeError(
            "Scheduled message callback sending is disabled. Use OutreachLedger.send_approved_drafts "
            "or approved follow-up confirmation so delivery has approval, evidence, and audit history."
        )
    
    def schedule_message(
        self,
        recipient_id: str,
        body: str,
        scheduled_time: datetime,
        recipient_name: str = "",
        subject: str = "",
        template_id: Optional[int] = None,
        respect_business_hours: bool = True,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Schedule a message for future delivery
        
        Args:
            recipient_id: Recipient ID
            body: Message body
            scheduled_time: When to send the message
            recipient_name: Recipient name
            subject: Message subject
            template_id: Optional template ID used
            respect_business_hours: Adjust time to business hours
            metadata: Additional metadata
            
        Returns:
            Scheduled message ID
        """
        # Adjust to business hours if requested
        if respect_business_hours:
            scheduled_time = self._adjust_to_business_hours(scheduled_time)
        
        now = datetime.now().isoformat()
        
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute('''
                INSERT INTO scheduled_messages 
                (template_id, recipient_id, recipient_name, subject, body,
                 scheduled_time, status, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, 'scheduled', ?, ?)
            ''', (
                template_id,
                recipient_id,
                recipient_name,
                subject,
                body,
                scheduled_time.isoformat(),
                now,
                json.dumps(metadata or {})
            ))
            conn.commit()
            
            logger.info(f"Scheduled message {cursor.lastrowid} for {scheduled_time}")
            return cursor.lastrowid
    
    def schedule_batch(
        self,
        messages: List[Dict[str, Any]],
        interval_minutes: int = 5,
        start_time: Optional[datetime] = None
    ) -> List[int]:
        """
        Schedule multiple messages with intervals
        
        Args:
            messages: List of message dictionaries
            interval_minutes: Minutes between each message
            start_time: When to start sending (default: now)
            
        Returns:
            List of scheduled message IDs
        """
        if not start_time:
            start_time = datetime.now()
        
        message_ids = []
        current_time = start_time
        
        for msg in messages:
            msg_id = self.schedule_message(
                recipient_id=msg['recipient_id'],
                body=msg['body'],
                scheduled_time=current_time,
                recipient_name=msg.get('recipient_name', ''),
                subject=msg.get('subject', ''),
                template_id=msg.get('template_id'),
                metadata=msg.get('metadata')
            )
            message_ids.append(msg_id)
            current_time += timedelta(minutes=interval_minutes)
        
        logger.info(f"Scheduled batch of {len(message_ids)} messages")
        return message_ids
    
    def _adjust_to_business_hours(self, dt: datetime) -> datetime:
        """Adjust datetime to business hours"""
        # If before business hours, move to start
        if dt.hour < self.BUSINESS_HOURS_START:
            dt = dt.replace(hour=self.BUSINESS_HOURS_START, minute=0, second=0)
        # If after business hours, move to next day
        elif dt.hour >= self.BUSINESS_HOURS_END:
            dt = dt + timedelta(days=1)
            dt = dt.replace(hour=self.BUSINESS_HOURS_START, minute=0, second=0)
        
        # Skip weekends
        while dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
            dt = dt + timedelta(days=1)
            dt = dt.replace(hour=self.BUSINESS_HOURS_START, minute=0, second=0)
        
        return dt
    
    def get_pending_messages(self) -> List[ScheduledMessage]:
        """Get messages ready to be sent"""
        now = datetime.now().isoformat()
        
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM scheduled_messages 
                WHERE status = 'scheduled' AND scheduled_time <= ?
                ORDER BY scheduled_time ASC
            ''', (now,))
            
            messages = []
            for row in cursor:
                data = dict(row)
                data['metadata'] = json.loads(data.get('metadata') or '{}')
                messages.append(ScheduledMessage(**{
                    k: v for k, v in data.items() 
                    if k in ScheduledMessage.__dataclass_fields__
                }))
            
            return messages
    
    def get_scheduled_messages(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[ScheduledMessage]:
        """Get scheduled messages"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            query = 'SELECT * FROM scheduled_messages'
            params = []
            
            if status:
                query += ' WHERE status = ?'
                params.append(status)
            
            query += ' ORDER BY scheduled_time DESC LIMIT ?'
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            messages = []
            for row in cursor:
                data = dict(row)
                data['metadata'] = json.loads(data.get('metadata') or '{}')
                messages.append(ScheduledMessage(**{
                    k: v for k, v in data.items() 
                    if k in ScheduledMessage.__dataclass_fields__
                }))
            
            return messages
    
    def cancel_message(self, message_id: int) -> bool:
        """Cancel a scheduled message"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute(
                'UPDATE scheduled_messages SET status = ? WHERE id = ? AND status = ?',
                ('cancelled', message_id, 'scheduled')
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def update_status(
        self,
        message_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Update message status"""
        if status == 'sent':
            raise RuntimeError(
                "Scheduled messages cannot be marked sent directly. Use the outreach ledger "
                "so delivery state has approval, evidence, and audit history."
            )

        with closing(sqlite3.connect(self.db_path)) as conn:
            if status == 'sent':
                conn.execute(
                    'UPDATE scheduled_messages SET status = ?, sent_at = ? WHERE id = ?',
                    (status, datetime.now().isoformat(), message_id)
                )
            elif error_message:
                conn.execute(
                    'UPDATE scheduled_messages SET status = ?, error_message = ? WHERE id = ?',
                    (status, error_message, message_id)
                )
            else:
                conn.execute(
                    'UPDATE scheduled_messages SET status = ? WHERE id = ?',
                    (status, message_id)
                )
            conn.commit()
    
    def start_scheduler(self, check_interval: int = 60) -> None:
        """Refuse legacy scheduled sending outside the outreach ledger."""
        raise RuntimeError(
            "Scheduled message processing is disabled. Use the outreach ledger so every external "
            "message has review, approval, evidence, and audit history."
        )
    
    def stop_scheduler(self) -> None:
        """Stop the scheduler"""
        self._is_running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("Message scheduler stopped")
    
    def _scheduler_loop(self, check_interval: int) -> None:
        """Main scheduler loop"""
        import time
        
        while self._is_running:
            try:
                pending = self.get_pending_messages()
                
                for message in pending:
                    if not self._is_running:
                        break
                    
                    if self._send_callback:
                        try:
                            success = self._send_callback(message)
                            if success:
                                self.update_status(message.id, 'sent')
                            else:
                                self.update_status(message.id, 'failed', 'Send callback returned False')
                        except (AttributeError, TypeError, RuntimeError, sqlite3.DatabaseError) as e:
                            self.update_status(message.id, 'failed', type(e).__name__)
                    else:
                        logger.warning("No send callback configured")

            except (json.JSONDecodeError, KeyError, AttributeError, TypeError, sqlite3.DatabaseError, RuntimeError) as e:
                logger.error("Scheduler error: %s", type(e).__name__)
            
            time.sleep(check_interval)


class MessagePreview:
    """
    Message preview system
    
    Features:
    - Preview personalized messages before sending
    - Validate message content
    - Check for common issues
    """
    
    # Common issues to check
    ISSUE_CHECKS = [
        ('empty_name', r'\{name\}', 'Naam variabele niet ingevuld'),
        ('empty_location', r'\{location\}', 'Locatie variabele niet ingevuld'),
        ('too_short', None, 'Bericht is te kort (minimaal 50 tekens)'),
        ('too_long', None, 'Bericht is te lang (maximaal 2000 tekens)'),
        ('no_greeting', None, 'Geen aanhef gevonden'),
        ('no_closing', None, 'Geen afsluiting gevonden'),
    ]
    
    MIN_LENGTH = 50
    MAX_LENGTH = 2000
    
    @classmethod
    def preview(
        cls,
        body: str,
        subject: str = "",
        recipient_data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a preview of the message
        
        Args:
            body: Message body (may contain variables)
            subject: Message subject
            recipient_data: Data for variable substitution
            
        Returns:
            Preview dictionary with rendered content and issues
        """
        recipient_data = recipient_data or {}
        
        # Render with sample data if no recipient data
        sample_data = {
            'name': recipient_data.get('name', 'Jan Jansen'),
            'first_name': recipient_data.get('first_name', 'Jan'),
            'location': recipient_data.get('location', 'Amsterdam'),
            'skills': recipient_data.get('skills', 'diverse vaardigheden'),
            'date': recipient_data.get('date', datetime.now().strftime('%d-%m-%Y')),
            'time': recipient_data.get('time', datetime.now().strftime('%H:%M')),
            'organization': recipient_data.get('organization', 'Uw Organisatie'),
            'custom_1': recipient_data.get('custom_1', ''),
            'custom_2': recipient_data.get('custom_2', ''),
            'custom_3': recipient_data.get('custom_3', ''),
        }
        
        # Render message
        rendered_subject = subject
        rendered_body = body
        
        for var_name, var_value in sample_data.items():
            placeholder = '{' + var_name + '}'
            rendered_subject = rendered_subject.replace(placeholder, var_value)
            rendered_body = rendered_body.replace(placeholder, var_value)
        
        # Check for issues
        issues = cls._check_issues(rendered_body, rendered_subject)
        
        # Calculate statistics
        word_count = len(rendered_body.split())
        char_count = len(rendered_body)
        
        return {
            'subject': rendered_subject,
            'body': rendered_body,
            'issues': issues,
            'is_valid': len([i for i in issues if i['severity'] == 'error']) == 0,
            'statistics': {
                'word_count': word_count,
                'char_count': char_count,
                'estimated_read_time': f"{max(1, word_count // 200)} min"
            },
            'variables_used': cls._extract_variables(body + subject),
            'sample_data_used': not bool(recipient_data)
        }
    
    @classmethod
    def _check_issues(cls, body: str, subject: str) -> List[Dict[str, str]]:
        """Check for common issues in message"""
        issues = []
        
        # Check for unfilled variables
        unfilled = re.findall(r'\{(\w+)\}', body + subject)
        for var in unfilled:
            issues.append({
                'type': 'unfilled_variable',
                'message': f'Variabele {{{var}}} is niet ingevuld',
                'severity': 'warning'
            })
        
        # Check length
        if len(body) < cls.MIN_LENGTH:
            issues.append({
                'type': 'too_short',
                'message': f'Bericht is te kort ({len(body)} tekens, minimaal {cls.MIN_LENGTH})',
                'severity': 'warning'
            })
        
        if len(body) > cls.MAX_LENGTH:
            issues.append({
                'type': 'too_long',
                'message': f'Bericht is te lang ({len(body)} tekens, maximaal {cls.MAX_LENGTH})',
                'severity': 'error'
            })
        
        # Check for greeting
        greetings = ['beste', 'geachte', 'hallo', 'dag', 'goedemorgen', 'goedemiddag']
        has_greeting = any(g in body.lower()[:50] for g in greetings)
        if not has_greeting:
            issues.append({
                'type': 'no_greeting',
                'message': 'Geen aanhef gevonden (bijv. "Beste", "Geachte")',
                'severity': 'warning'
            })
        
        # Check for closing
        closings = ['groet', 'groeten', 'mvg', 'hoogachtend']
        has_closing = any(c in body.lower()[-100:] for c in closings)
        if not has_closing:
            issues.append({
                'type': 'no_closing',
                'message': 'Geen afsluiting gevonden (bijv. "Met vriendelijke groet")',
                'severity': 'warning'
            })
        
        return issues
    
    @classmethod
    def _extract_variables(cls, text: str) -> List[str]:
        """Extract variable names from text"""
        return list(set(re.findall(r'\{(\w+)\}', text)))


class EnhancedMessagingService:
    """
    Combined enhanced messaging service
    
    Features:
    - Template management
    - Message scheduling
    - Message preview
    - Delivery tracking
    """
    
    def __init__(self, db_path: Optional[str] = None, send_callback: Optional[Callable] = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            'messaging.db'
        )
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize components
        self.templates = MessageTemplateManager(self.db_path)
        self.scheduler = MessageScheduler(self.db_path)
        self.preview = MessagePreview()
        if send_callback:
            raise RuntimeError(
                "EnhancedMessagingService send callbacks are disabled. Use OutreachLedger.send_approved_drafts "
                "so every external message has approval, evidence, and audit history."
            )

    def render_template(self, template: str, variables: Dict[str, str]) -> str:
        """Render an ad-hoc template string with variable substitution."""
        rendered = template
        for name, value in variables.items():
            rendered = rendered.replace("{" + name + "}", str(value))
        return rendered

    def validate_template(self, template: str) -> Dict[str, Any]:
        """Validate basic brace balance and preview constraints for an ad-hoc template."""
        if template.count("{") != template.count("}"):
            return {
                "is_valid": False,
                "errors": ["Template contains unmatched braces"]
            }

        preview = self.preview.preview(template)
        return {
            "is_valid": preview["is_valid"],
            "errors": [issue["message"] for issue in preview["issues"] if issue["severity"] == "error"],
            "warnings": [issue["message"] for issue in preview["issues"] if issue["severity"] == "warning"]
        }
    
    def create_and_schedule_message(
        self,
        template_id: int,
        recipient_id: str,
        recipient_data: Dict[str, str],
        scheduled_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a message from template and schedule it
        
        Args:
            template_id: Template ID to use
            recipient_id: Recipient ID
            recipient_data: Data for variable substitution
            scheduled_time: When to send (default: immediately)
            
        Returns:
            Result dictionary with preview and schedule info
        """
        # Render template
        subject, body = self.templates.render_template(template_id, recipient_data)
        
        # Generate preview
        preview_result = self.preview.preview(
            body=body,
            subject=subject,
            recipient_data=recipient_data
        )
        
        # Schedule if valid
        if preview_result['is_valid']:
            if scheduled_time is None:
                scheduled_time = datetime.now()
            
            message_id = self.scheduler.schedule_message(
                recipient_id=recipient_id,
                body=body,
                subject=subject,
                scheduled_time=scheduled_time,
                recipient_name=recipient_data.get('name', ''),
                template_id=template_id
            )
            
            return {
                'success': True,
                'message_id': message_id,
                'preview': preview_result,
                'scheduled_time': scheduled_time.isoformat()
            }
        else:
            return {
                'success': False,
                'preview': preview_result,
                'error': 'Message validation failed'
            }
    
    def start(self) -> None:
        """Start the messaging service"""
        self.scheduler.start_scheduler()
    
    def stop(self) -> None:
        """Stop the messaging service"""
        self.scheduler.stop_scheduler()

