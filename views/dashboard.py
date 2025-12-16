"""
Dashboard and Notification System
Addresses TODO items #11-12: Dashboard and Notification Improvements
"""

import tkinter as tk
from tkinter import ttk
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from views.enhanced_ui_components import (
    ThemeColors, ThemeFonts, apply_dark_theme,
    Toast, ToastType, show_toast
)


# ============================================================================
# DASHBOARD STATISTICS
# ============================================================================

@dataclass
class DashboardStats:
    """Dashboard statistics data"""
    total_volunteers: int = 0
    new_volunteers_today: int = 0
    new_volunteers_week: int = 0
    active_volunteers: int = 0
    
    total_messages_sent: int = 0
    messages_sent_today: int = 0
    messages_sent_week: int = 0
    
    total_responses: int = 0
    response_rate: float = 0.0
    avg_response_time_hours: float = 0.0
    
    pending_reminders: int = 0
    blacklisted_count: int = 0
    
    campaigns_active: int = 0
    campaigns_completed: int = 0
    
    last_sync: Optional[str] = None
    sync_status: str = "unknown"


class DashboardDataProvider:
    """
    Provides data for the dashboard
    
    Features:
    - Aggregates data from multiple sources
    - Caches results for performance
    - Real-time updates
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._cache: Optional[DashboardStats] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
    
    def get_stats(self, force_refresh: bool = False) -> DashboardStats:
        """Get dashboard statistics"""
        now = datetime.now()
        
        # Return cached if valid
        if not force_refresh and self._cache and self._cache_time:
            if now - self._cache_time < self._cache_ttl:
                return self._cache
        
        stats = DashboardStats()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Volunteer stats
                stats.total_volunteers = self._get_count(
                    conn, 'volunteers', 'is_active = 1'
                )
                
                today = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                
                stats.new_volunteers_today = self._get_count(
                    conn, 'volunteers', f"first_seen >= '{today}'"
                )
                stats.new_volunteers_week = self._get_count(
                    conn, 'volunteers', f"first_seen >= '{week_ago}'"
                )
                
                # Message stats
                stats.total_messages_sent = self._get_count(
                    conn, 'scheduled_messages', "status = 'sent'"
                )
                stats.messages_sent_today = self._get_count(
                    conn, 'scheduled_messages', 
                    f"status = 'sent' AND sent_at >= '{today}'"
                )
                stats.messages_sent_week = self._get_count(
                    conn, 'scheduled_messages',
                    f"status = 'sent' AND sent_at >= '{week_ago}'"
                )
                
                # Response stats
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM reminders WHERE status = 'responded'
                ''')
                stats.total_responses = cursor.fetchone()[0] or 0
                
                if stats.total_messages_sent > 0:
                    stats.response_rate = (
                        stats.total_responses / stats.total_messages_sent * 100
                    )
                
                # Pending reminders
                stats.pending_reminders = self._get_count(
                    conn, 'reminders', "status = 'pending'"
                )
                
                # Blacklist count
                stats.blacklisted_count = self._get_count(conn, 'blacklist')
                
                # Sync status
                cursor = conn.execute('''
                    SELECT status, last_updated FROM scrape_sessions 
                    ORDER BY last_updated DESC LIMIT 1
                ''')
                row = cursor.fetchone()
                if row:
                    stats.sync_status = row[0]
                    stats.last_sync = row[1]
                
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
        
        # Cache results
        self._cache = stats
        self._cache_time = now
        
        return stats
    
    def _get_count(
        self, 
        conn: sqlite3.Connection, 
        table: str, 
        where: str = "1=1"
    ) -> int:
        """Get count from table"""
        try:
            cursor = conn.execute(f'SELECT COUNT(*) FROM {table} WHERE {where}')
            return cursor.fetchone()[0] or 0
        except:
            return 0


class StatCard(ttk.Frame):
    """
    Statistics card widget
    
    Features:
    - Title and value display
    - Trend indicator
    - Click action
    """
    
    def __init__(
        self,
        parent,
        title: str,
        value: str = "0",
        subtitle: str = "",
        trend: Optional[str] = None,
        trend_positive: bool = True,
        on_click: Optional[Callable] = None
    ):
        super().__init__(parent, style='Card.TFrame')
        
        self.on_click = on_click
        
        # Container
        container = ttk.Frame(self, style='Card.TFrame')
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title
        title_label = ttk.Label(
            container,
            text=title,
            style='Muted.TLabel',
            font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_SM)
        )
        title_label.pack(anchor=tk.W)
        
        # Value row
        value_frame = ttk.Frame(container, style='Card.TFrame')
        value_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Value
        self._value_label = ttk.Label(
            value_frame,
            text=value,
            font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_3XL, 'bold')
        )
        self._value_label.pack(side=tk.LEFT)
        
        # Trend
        if trend:
            trend_color = ThemeColors.ACCENT_SUCCESS if trend_positive else ThemeColors.ACCENT_ERROR
            trend_label = ttk.Label(
                value_frame,
                text=trend,
                foreground=trend_color,
                font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_SM)
            )
            trend_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Subtitle
        if subtitle:
            subtitle_label = ttk.Label(
                container,
                text=subtitle,
                style='Muted.TLabel',
                font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_XS)
            )
            subtitle_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Bind click
        if on_click:
            self.bind('<Button-1>', lambda e: on_click())
            for child in self.winfo_children():
                child.bind('<Button-1>', lambda e: on_click())
    
    def update_value(self, value: str) -> None:
        """Update the displayed value"""
        self._value_label.configure(text=value)


class Dashboard(ttk.Frame):
    """
    Main dashboard view
    
    Features:
    - Statistics overview
    - Quick actions
    - Recent activity
    - Auto-refresh
    """
    
    def __init__(self, parent, db_path: str):
        super().__init__(parent)
        
        self.db_path = db_path
        self.data_provider = DashboardDataProvider(db_path)
        
        self._stat_cards: Dict[str, StatCard] = {}
        self._refresh_interval = 60000  # 1 minute
        
        self._create_widgets()
        self._start_auto_refresh()
    
    def _create_widgets(self) -> None:
        """Create dashboard widgets"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        title_label = ttk.Label(
            header_frame,
            text="Dashboard",
            style='Title.TLabel'
        )
        title_label.pack(side=tk.LEFT)
        
        refresh_btn = ttk.Button(
            header_frame,
            text="⟳ Vernieuwen",
            command=self.refresh
        )
        refresh_btn.pack(side=tk.RIGHT)
        
        # Stats grid
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Configure grid
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1, uniform='stat')
        
        # Create stat cards
        stats = self.data_provider.get_stats()
        
        # Row 1
        self._stat_cards['volunteers'] = StatCard(
            stats_frame,
            title="Totaal Vrijwilligers",
            value=str(stats.total_volunteers),
            subtitle=f"+{stats.new_volunteers_week} deze week"
        )
        self._stat_cards['volunteers'].grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        self._stat_cards['messages'] = StatCard(
            stats_frame,
            title="Berichten Verzonden",
            value=str(stats.total_messages_sent),
            subtitle=f"{stats.messages_sent_today} vandaag"
        )
        self._stat_cards['messages'].grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        
        self._stat_cards['responses'] = StatCard(
            stats_frame,
            title="Reacties",
            value=str(stats.total_responses),
            subtitle=f"{stats.response_rate:.1f}% response rate"
        )
        self._stat_cards['responses'].grid(row=0, column=2, padx=5, pady=5, sticky='nsew')
        
        self._stat_cards['reminders'] = StatCard(
            stats_frame,
            title="Openstaande Herinneringen",
            value=str(stats.pending_reminders)
        )
        self._stat_cards['reminders'].grid(row=0, column=3, padx=5, pady=5, sticky='nsew')
        
        # Quick Actions section
        actions_frame = ttk.LabelFrame(self, text="Snelle Acties")
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        actions_inner = ttk.Frame(actions_frame)
        actions_inner.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            actions_inner,
            text="🔄 Synchroniseren",
            style='Primary.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            actions_inner,
            text="✉ Nieuwe Campagne"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            actions_inner,
            text="📊 Rapport Exporteren"
        ).pack(side=tk.LEFT, padx=5)
        
        # Recent Activity section
        activity_frame = ttk.LabelFrame(self, text="Recente Activiteit")
        activity_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Activity list
        self._activity_tree = ttk.Treeview(
            activity_frame,
            columns=('time', 'type', 'description'),
            show='headings',
            height=8
        )
        
        self._activity_tree.heading('time', text='Tijd')
        self._activity_tree.heading('type', text='Type')
        self._activity_tree.heading('description', text='Beschrijving')
        
        self._activity_tree.column('time', width=120)
        self._activity_tree.column('type', width=100)
        self._activity_tree.column('description', width=400)
        
        self._activity_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self._status_label = ttk.Label(
            status_frame,
            text=f"Laatste sync: {stats.last_sync or 'Nooit'}",
            style='Muted.TLabel'
        )
        self._status_label.pack(side=tk.LEFT)
    
    def refresh(self) -> None:
        """Refresh dashboard data"""
        stats = self.data_provider.get_stats(force_refresh=True)
        
        # Update stat cards
        self._stat_cards['volunteers'].update_value(str(stats.total_volunteers))
        self._stat_cards['messages'].update_value(str(stats.total_messages_sent))
        self._stat_cards['responses'].update_value(str(stats.total_responses))
        self._stat_cards['reminders'].update_value(str(stats.pending_reminders))
        
        # Update status
        self._status_label.configure(
            text=f"Laatste sync: {stats.last_sync or 'Nooit'} | Vernieuwd: {datetime.now().strftime('%H:%M:%S')}"
        )
    
    def _start_auto_refresh(self) -> None:
        """Start auto-refresh timer"""
        self.refresh()
        self.after(self._refresh_interval, self._start_auto_refresh)


# ============================================================================
# NOTIFICATION SYSTEM
# ============================================================================

class NotificationType(Enum):
    """Notification types"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYNC_COMPLETE = "sync_complete"
    NEW_RESPONSE = "new_response"
    REMINDER_DUE = "reminder_due"


@dataclass
class Notification:
    """Notification data"""
    id: Optional[int] = None
    type: NotificationType = NotificationType.INFO
    title: str = ""
    message: str = ""
    created_at: str = ""
    read_at: Optional[str] = None
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationService:
    """
    Notification service for in-app and email notifications
    
    Features:
    - In-app notifications
    - Email notifications
    - Notification history
    - Read/unread tracking
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._callbacks: List[Callable[[Notification], None]] = []
        self._email_config: Optional[Dict[str, str]] = None
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize notification database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT,
                    created_at TEXT NOT NULL,
                    read_at TEXT,
                    action_url TEXT,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_notification_read 
                ON notifications(read_at)
            ''')
            
            conn.commit()
    
    def configure_email(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str
    ) -> None:
        """Configure email notifications"""
        self._email_config = {
            'host': smtp_host,
            'port': smtp_port,
            'username': username,
            'password': password,
            'from_email': from_email
        }
    
    def add_callback(self, callback: Callable[[Notification], None]) -> None:
        """Add notification callback"""
        self._callbacks.append(callback)
    
    def notify(
        self,
        type: NotificationType,
        title: str,
        message: str = "",
        action_url: Optional[str] = None,
        send_email: bool = False,
        email_to: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Create and send a notification
        
        Args:
            type: Notification type
            title: Notification title
            message: Notification message
            action_url: Optional action URL
            send_email: Whether to send email
            email_to: Email recipient
            metadata: Additional metadata
            
        Returns:
            Notification ID
        """
        now = datetime.now().isoformat()
        
        notification = Notification(
            type=type,
            title=title,
            message=message,
            created_at=now,
            action_url=action_url,
            metadata=metadata or {}
        )
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO notifications 
                (type, title, message, created_at, action_url, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                type.value,
                title,
                message,
                now,
                action_url,
                json.dumps(metadata or {})
            ))
            conn.commit()
            notification.id = cursor.lastrowid
        
        # Trigger callbacks
        for callback in self._callbacks:
            try:
                callback(notification)
            except Exception as e:
                print(f"Notification callback error: {e}")
        
        # Send email if requested
        if send_email and email_to and self._email_config:
            self._send_email(email_to, title, message)
        
        return notification.id
    
    def _send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email notification"""
        if not self._email_config:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self._email_config['from_email']
            msg['To'] = to
            msg['Subject'] = f"[NLvoorElkaar] {subject}"
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(
                self._email_config['host'],
                self._email_config['port']
            ) as server:
                server.starttls()
                server.login(
                    self._email_config['username'],
                    self._email_config['password']
                )
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Email send error: {e}")
            return False
    
    def get_notifications(
        self,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = 'SELECT * FROM notifications'
            params = []
            
            if unread_only:
                query += ' WHERE read_at IS NULL'
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            notifications = []
            for row in cursor:
                data = dict(row)
                data['type'] = NotificationType(data['type'])
                data['metadata'] = json.loads(data.get('metadata') or '{}')
                notifications.append(Notification(**{
                    k: v for k, v in data.items()
                    if k in Notification.__dataclass_fields__
                }))
            
            return notifications
    
    def mark_read(self, notification_id: int) -> None:
        """Mark notification as read"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'UPDATE notifications SET read_at = ? WHERE id = ?',
                (datetime.now().isoformat(), notification_id)
            )
            conn.commit()
    
    def mark_all_read(self) -> None:
        """Mark all notifications as read"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'UPDATE notifications SET read_at = ? WHERE read_at IS NULL',
                (datetime.now().isoformat(),)
            )
            conn.commit()
    
    def get_unread_count(self) -> int:
        """Get unread notification count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT COUNT(*) FROM notifications WHERE read_at IS NULL'
            )
            return cursor.fetchone()[0] or 0
    
    def delete_old_notifications(self, days: int = 30) -> int:
        """Delete notifications older than specified days"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'DELETE FROM notifications WHERE created_at < ?',
                (cutoff,)
            )
            conn.commit()
            return cursor.rowcount


class NotificationCenter(ttk.Frame):
    """
    Notification center widget
    
    Features:
    - Notification list
    - Mark as read
    - Clear all
    """
    
    def __init__(self, parent, notification_service: NotificationService):
        super().__init__(parent)
        
        self.service = notification_service
        
        self._create_widgets()
        self._load_notifications()
        
        # Register callback
        self.service.add_callback(self._on_new_notification)
    
    def _create_widgets(self) -> None:
        """Create notification center widgets"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = ttk.Label(
            header_frame,
            text="Meldingen",
            style='Subtitle.TLabel'
        )
        title_label.pack(side=tk.LEFT)
        
        self._badge_label = ttk.Label(
            header_frame,
            text="0",
            foreground=ThemeColors.ACCENT_ERROR,
            font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_SM, 'bold')
        )
        self._badge_label.pack(side=tk.LEFT, padx=(5, 0))
        
        clear_btn = ttk.Button(
            header_frame,
            text="Alles gelezen",
            command=self._mark_all_read
        )
        clear_btn.pack(side=tk.RIGHT)
        
        # Notification list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self._notification_list = tk.Listbox(
            list_frame,
            bg=ThemeColors.BG_SECONDARY,
            fg=ThemeColors.TEXT_PRIMARY,
            selectbackground=ThemeColors.ACCENT_PRIMARY,
            font=(ThemeFonts.FAMILY, ThemeFonts.SIZE_BASE),
            height=10
        )
        self._notification_list.pack(fill=tk.BOTH, expand=True)
        
        # Bind click
        self._notification_list.bind('<Double-1>', self._on_notification_click)
    
    def _load_notifications(self) -> None:
        """Load notifications into list"""
        self._notification_list.delete(0, tk.END)
        
        notifications = self.service.get_notifications(limit=20)
        
        for notif in notifications:
            prefix = "● " if notif.read_at is None else "○ "
            self._notification_list.insert(
                tk.END,
                f"{prefix}{notif.title}"
            )
        
        # Update badge
        unread = self.service.get_unread_count()
        self._badge_label.configure(text=str(unread))
    
    def _on_new_notification(self, notification: Notification) -> None:
        """Handle new notification"""
        self._load_notifications()
    
    def _on_notification_click(self, event) -> None:
        """Handle notification click"""
        selection = self._notification_list.curselection()
        if selection:
            notifications = self.service.get_notifications(limit=20)
            if selection[0] < len(notifications):
                notif = notifications[selection[0]]
                self.service.mark_read(notif.id)
                self._load_notifications()
    
    def _mark_all_read(self) -> None:
        """Mark all notifications as read"""
        self.service.mark_all_read()
        self._load_notifications()
