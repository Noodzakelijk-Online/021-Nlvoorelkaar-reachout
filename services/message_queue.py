"""
Message Queue System for Reliable Message Delivery
Addresses TODO items #5: Messaging Service Improvements
"""

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from queue import PriorityQueue
import sqlite3
import os
from contextlib import closing

logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    """Message delivery status"""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


@dataclass
class Message:
    """Message data structure"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recipient_id: str = ""
    recipient_name: str = ""
    subject: str = ""
    body: str = ""
    phone_number: str = ""
    campaign_id: Optional[int] = None
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    scheduled_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['sent_at'] = self.sent_at.isoformat() if self.sent_at else None
        data['delivered_at'] = self.delivered_at.isoformat() if self.delivered_at else None
        data['scheduled_time'] = self.scheduled_time.isoformat() if self.scheduled_time else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        data = data.copy()
        data['priority'] = MessagePriority(data.get('priority', 2))
        data['status'] = MessageStatus(data.get('status', 'pending'))
        
        for field_name in ['created_at', 'sent_at', 'delivered_at', 'scheduled_time']:
            if data.get(field_name):
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)
    
    def __lt__(self, other):
        """Compare messages by priority for queue ordering"""
        return self.priority.value < other.priority.value


class MessageQueue:
    """
    Persistent message queue with priority support
    
    Features:
    - Priority-based message ordering
    - Persistent storage (survives restarts)
    - Automatic retry on failure
    - Scheduled message support
    - Delivery confirmation tracking
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            'message_queue.db'
        )
        self._queue = PriorityQueue()
        self._lock = threading.Lock()
        self._processing = False
        self._processor_thread: Optional[threading.Thread] = None
        self._send_callback: Optional[Callable] = None
        self._status_callbacks: List[Callable] = []
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        # Load pending messages from database
        self._load_pending_messages()
    
    def _init_db(self) -> None:
        """Initialize the message queue database"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    recipient_id TEXT NOT NULL,
                    recipient_name TEXT,
                    subject TEXT,
                    body TEXT NOT NULL,
                    phone_number TEXT,
                    campaign_id INTEGER,
                    priority INTEGER DEFAULT 2,
                    status TEXT DEFAULT 'pending',
                    scheduled_time TEXT,
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    delivered_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status ON messages(status)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_scheduled ON messages(scheduled_time)
            ''')
            
            conn.commit()
        
        logger.info("Message queue database initialized")
    
    def _load_pending_messages(self) -> None:
        """Load pending messages from database into queue"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM messages 
                WHERE status IN ('pending', 'queued', 'scheduled')
                ORDER BY priority ASC, created_at ASC
            ''')
            
            for row in cursor:
                message = self._row_to_message(row)
                self._queue.put((message.priority.value, message))
        
        logger.info(f"Loaded {self._queue.qsize()} pending messages from database")
    
    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """Convert database row to Message object"""
        data = dict(row)
        data['metadata'] = json.loads(data.get('metadata') or '{}')
        return Message.from_dict(data)
    
    def _save_message(self, message: Message) -> None:
        """Save message to database"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO messages 
                (id, recipient_id, recipient_name, subject, body, phone_number,
                 campaign_id, priority, status, scheduled_time, created_at,
                 sent_at, delivered_at, retry_count, max_retries, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message.id,
                message.recipient_id,
                message.recipient_name,
                message.subject,
                message.body,
                message.phone_number,
                message.campaign_id,
                message.priority.value,
                message.status.value,
                message.scheduled_time.isoformat() if message.scheduled_time else None,
                message.created_at.isoformat(),
                message.sent_at.isoformat() if message.sent_at else None,
                message.delivered_at.isoformat() if message.delivered_at else None,
                message.retry_count,
                message.max_retries,
                message.error_message,
                json.dumps(message.metadata)
            ))
            conn.commit()
    
    def enqueue(
        self,
        recipient_id: str,
        body: str,
        recipient_name: str = "",
        subject: str = "",
        phone_number: str = "",
        campaign_id: Optional[int] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        scheduled_time: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a message to the queue
        
        Args:
            recipient_id: Volunteer ID to send message to
            body: Message body text
            recipient_name: Optional recipient name for personalization
            subject: Optional message subject
            phone_number: Optional phone number
            campaign_id: Optional campaign ID
            priority: Message priority
            scheduled_time: Optional scheduled send time
            metadata: Optional additional metadata
            
        Returns:
            Message ID
        """
        message = Message(
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            subject=subject,
            body=body,
            phone_number=phone_number,
            campaign_id=campaign_id,
            priority=priority,
            status=MessageStatus.SCHEDULED if scheduled_time else MessageStatus.QUEUED,
            scheduled_time=scheduled_time,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._save_message(message)
            self._queue.put((message.priority.value, message))
        
        logger.info("Message %s enqueued for ledger review", message.id)
        self._notify_status_change(message)
        
        return message.id
    
    def enqueue_batch(
        self,
        messages: List[Dict[str, Any]],
        campaign_id: Optional[int] = None
    ) -> List[str]:
        """
        Add multiple messages to the queue
        
        Args:
            messages: List of message dictionaries
            campaign_id: Optional campaign ID to associate with all messages
            
        Returns:
            List of message IDs
        """
        message_ids = []
        
        for msg_data in messages:
            msg_id = self.enqueue(
                recipient_id=msg_data['recipient_id'],
                body=msg_data['body'],
                recipient_name=msg_data.get('recipient_name', ''),
                subject=msg_data.get('subject', ''),
                phone_number=msg_data.get('phone_number', ''),
                campaign_id=campaign_id or msg_data.get('campaign_id'),
                priority=msg_data.get('priority', MessagePriority.NORMAL),
                scheduled_time=msg_data.get('scheduled_time'),
                metadata=msg_data.get('metadata')
            )
            message_ids.append(msg_id)
        
        logger.info(f"Batch enqueued {len(message_ids)} messages")
        return message_ids
    
    def get_message(self, message_id: str) -> Optional[Message]:
        """Get a message by ID"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM messages WHERE id = ?',
                (message_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_message(row)
        
        return None

    def get_pending(self, limit: int = 100) -> List[Message]:
        """Compatibility helper: return pending, queued, or scheduled messages."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM messages
                WHERE status IN ('pending', 'queued', 'scheduled')
                ORDER BY priority ASC, created_at ASC
                LIMIT ?
            ''', (limit,))
            return [self._row_to_message(row) for row in cursor]

    def mark_sent(self, message_id: str) -> None:
        """Refuse unaudited sent marking outside the outreach ledger."""
        raise RuntimeError(
            "MessageQueue cannot mark messages as sent directly. Use OutreachLedger.confirm_manual_send "
            "or OutreachLedger.send_approved_drafts so sent state has approval, evidence, and audit history."
        )
    
    def update_status(
        self,
        message_id: str,
        status: MessageStatus,
        error_message: Optional[str] = None
    ) -> None:
        """Update message status"""
        if status in {MessageStatus.SENT, MessageStatus.DELIVERED}:
            raise RuntimeError(
                "MessageQueue cannot set sent/delivered status directly. Use the outreach ledger "
                "so delivery state has approval, evidence, and audit history."
            )

        with closing(sqlite3.connect(self.db_path)) as conn:
            updates = {'status': status.value}
            
            if status == MessageStatus.SENT:
                updates['sent_at'] = datetime.now().isoformat()
            elif status == MessageStatus.DELIVERED:
                updates['delivered_at'] = datetime.now().isoformat()
            elif status == MessageStatus.FAILED and error_message:
                updates['error_message'] = error_message
            
            set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
            values = list(updates.values()) + [message_id]
            
            conn.execute(
                f'UPDATE messages SET {set_clause} WHERE id = ?',
                values
            )
            conn.commit()
        
        # Notify callbacks
        message = self.get_message(message_id)
        if message:
            self._notify_status_change(message)
    
    def cancel_message(self, message_id: str) -> bool:
        """Cancel a pending message"""
        message = self.get_message(message_id)
        
        if message and message.status in [MessageStatus.PENDING, MessageStatus.QUEUED, MessageStatus.SCHEDULED]:
            self.update_status(message_id, MessageStatus.CANCELLED)
            logger.info(f"Message {message_id} cancelled")
            return True
        
        return False
    
    def set_send_callback(self, callback: Callable[[Message], bool]) -> None:
        """Refuse legacy callback-based sending outside the outreach ledger."""
        raise RuntimeError(
            "MessageQueue callback sending is disabled. Use OutreachLedger.send_approved_drafts "
            "so every external message has approval, send evidence, and audit history."
        )
    
    def add_status_callback(self, callback: Callable[[Message], None]) -> None:
        """Add a callback for status changes"""
        self._status_callbacks.append(callback)
    
    def _notify_status_change(self, message: Message) -> None:
        """Notify all status callbacks"""
        for callback in self._status_callbacks:
            try:
                callback(message)
            except (AttributeError, TypeError, RuntimeError, ValueError) as e:
                logger.error("Error in status callback: %s", type(e).__name__)
    
    def start_processing(self) -> None:
        """Refuse legacy queue processing outside the outreach ledger."""
        raise RuntimeError(
            "MessageQueue processing is disabled. Use OutreachLedger.send_approved_drafts "
            "so every external message has approval, send evidence, and audit history."
        )
    
    def stop_processing(self) -> None:
        """Stop the message processing thread"""
        self._processing = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5)
        logger.info("Message queue processing stopped")
    
    def _process_queue(self) -> None:
        """Process messages from the queue"""
        while self._processing:
            try:
                if self._queue.empty():
                    time.sleep(1)
                    continue
                
                # Get next message
                priority, message = self._queue.get(timeout=1)
                
                # Check if scheduled for later
                if message.scheduled_time and message.scheduled_time > datetime.now():
                    self._queue.put((priority, message))
                    time.sleep(1)
                    continue
                
                # Check if cancelled
                current = self.get_message(message.id)
                if current and current.status == MessageStatus.CANCELLED:
                    continue
                
                # Send the message
                self._send_message(message)
                
            except (AttributeError, TypeError, RuntimeError, ValueError, KeyError) as e:
                logger.error("Error processing queue: %s", type(e).__name__)
                time.sleep(1)
    
    def _send_message(self, message: Message) -> None:
        """Refuse legacy single-message sending outside the outreach ledger."""
        raise RuntimeError(
            "MessageQueue direct sending is disabled. Use OutreachLedger.send_approved_drafts "
            "so every external message has approval, send evidence, and audit history."
        )
    
    def _handle_send_failure(self, message: Message, error: str) -> None:
        """Handle message send failure"""
        message.retry_count += 1
        
        if message.retry_count < message.max_retries:
            # Re-queue for retry
            logger.warning(
                f"Message {message.id} failed (attempt {message.retry_count}), "
                f"retrying... Error: {error}"
            )
            message.status = MessageStatus.QUEUED
            self._save_message(message)
            self._queue.put((message.priority.value, message))
        else:
            # Max retries reached
            logger.error(
                f"Message {message.id} failed after {message.retry_count} attempts: {error}"
            )
            self.update_status(message.id, MessageStatus.FAILED, error)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute('''
                SELECT status, COUNT(*) as count 
                FROM messages 
                GROUP BY status
            ''')
            
            status_counts = {row[0]: row[1] for row in cursor}
        
        return {
            'queue_size': self._queue.qsize(),
            'processing': self._processing,
            'status_counts': status_counts,
            'total_messages': sum(status_counts.values())
        }
    
    def get_campaign_stats(self, campaign_id: int) -> Dict[str, Any]:
        """Get statistics for a specific campaign"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute('''
                SELECT status, COUNT(*) as count 
                FROM messages 
                WHERE campaign_id = ?
                GROUP BY status
            ''', (campaign_id,))
            
            status_counts = {row[0]: row[1] for row in cursor}
        
        return {
            'campaign_id': campaign_id,
            'status_counts': status_counts,
            'total_messages': sum(status_counts.values()),
            'sent_count': status_counts.get('sent', 0) + status_counts.get('delivered', 0),
            'failed_count': status_counts.get('failed', 0),
            'pending_count': status_counts.get('pending', 0) + status_counts.get('queued', 0)
        }

