"""
Modern UI for NLvoorelkaar Tool
Dark theme with clean, organized interface and improved UX
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ModernTheme:
    """Modern dark theme configuration"""
    
    # Colors
    PRIMARY_COLOR = "#1f538d"
    SECONDARY_COLOR = "#14375e"
    ACCENT_COLOR = "#36719f"
    SUCCESS_COLOR = "#2d5a27"
    WARNING_COLOR = "#8b6914"
    ERROR_COLOR = "#8b1538"
    
    # Background colors
    BG_PRIMARY = "#212121"
    BG_SECONDARY = "#2b2b2b"
    BG_TERTIARY = "#3a3a3a"
    
    # Text colors
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#b0b0b0"
    TEXT_MUTED = "#808080"
    
    # Fonts
    FONT_LARGE = ("Segoe UI", 16, "bold")
    FONT_MEDIUM = ("Segoe UI", 12)
    FONT_SMALL = ("Segoe UI", 10)
    FONT_MONO = ("Consolas", 10)

class StatusBar(ctk.CTkFrame):
    """Modern status bar with connection and activity indicators"""
    
    def __init__(self, parent):
        super().__init__(parent, height=30)
        self.grid_columnconfigure(1, weight=1)
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            self, 
            text="● Ready", 
            text_color=ModernTheme.SUCCESS_COLOR,
            font=ModernTheme.FONT_SMALL
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Activity indicator
        self.activity_label = ctk.CTkLabel(
            self, 
            text="", 
            font=ModernTheme.FONT_SMALL
        )
        self.activity_label.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
    def set_status(self, status: str, status_type: str = "info"):
        """Set status with color coding"""
        colors = {
            "success": ModernTheme.SUCCESS_COLOR,
            "warning": ModernTheme.WARNING_COLOR,
            "error": ModernTheme.ERROR_COLOR,
            "info": ModernTheme.TEXT_SECONDARY
        }
        
        self.status_label.configure(
            text=f"● {status}",
            text_color=colors.get(status_type, ModernTheme.TEXT_SECONDARY)
        )
        
    def set_activity(self, activity: str):
        """Set activity text"""
        self.activity_label.configure(text=activity)

class MetricsCard(ctk.CTkFrame):
    """Modern metrics card widget"""
    
    def __init__(self, parent, title: str, value: str = "0", subtitle: str = "", color: str = None):
        super().__init__(parent, corner_radius=10)
        
        self.grid_columnconfigure(0, weight=1)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=ModernTheme.FONT_SMALL,
            text_color=ModernTheme.TEXT_SECONDARY
        )
        self.title_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        # Value
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=ModernTheme.FONT_LARGE,
            text_color=color or ModernTheme.TEXT_PRIMARY
        )
        self.value_label.grid(row=1, column=0, padx=15, pady=5, sticky="w")
        
        # Subtitle
        if subtitle:
            self.subtitle_label = ctk.CTkLabel(
                self,
                text=subtitle,
                font=ModernTheme.FONT_SMALL,
                text_color=ModernTheme.TEXT_MUTED
            )
            self.subtitle_label.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="w")
            
    def update_value(self, value: str, subtitle: str = None):
        """Update card value and subtitle"""
        self.value_label.configure(text=value)
        if subtitle and hasattr(self, 'subtitle_label'):
            self.subtitle_label.configure(text=subtitle)

class ProgressDialog(ctk.CTkToplevel):
    """Modern progress dialog"""
    
    def __init__(self, parent, title: str, message: str):
        super().__init__(parent)
        
        self.title(title)
        self.geometry("400x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")
        
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Message
        self.message_label = ctk.CTkLabel(
            main_frame,
            text=message,
            font=ModernTheme.FONT_MEDIUM,
            wraplength=350
        )
        self.message_label.pack(pady=(20, 10))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(main_frame, width=300)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Starting...",
            font=ModernTheme.FONT_SMALL,
            text_color=ModernTheme.TEXT_SECONDARY
        )
        self.status_label.pack(pady=5)
        
        # Cancel button
        self.cancel_button = ctk.CTkButton(
            main_frame,
            text="Cancel",
            command=self.cancel_operation,
            width=100
        )
        self.cancel_button.pack(pady=(10, 20))
        
        self.cancelled = False
        
    def update_progress(self, progress: float, status: str = ""):
        """Update progress and status"""
        self.progress_bar.set(progress)
        if status:
            self.status_label.configure(text=status)
        self.update()
        
    def cancel_operation(self):
        """Cancel the operation"""
        self.cancelled = True
        self.destroy()

class DashboardView(ctk.CTkFrame):
    """Modern dashboard with metrics and recent activity"""
    
    def __init__(self, parent, data_callback: Callable = None):
        super().__init__(parent)
        self.data_callback = data_callback
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.setup_ui()
        self.refresh_data()
        
    def setup_ui(self):
        """Setup dashboard UI"""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Dashboard",
            font=ModernTheme.FONT_LARGE
        )
        title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")
        
        # Metrics grid (2x2)
        metrics_frame = ctk.CTkFrame(self)
        metrics_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        metrics_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Metrics cards
        self.total_volunteers_card = MetricsCard(
            metrics_frame, 
            "Total Volunteers", 
            "0", 
            "In database"
        )
        self.total_volunteers_card.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.total_contacts_card = MetricsCard(
            metrics_frame, 
            "Total Contacts", 
            "0", 
            "Messages sent"
        )
        self.total_contacts_card.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.response_rate_card = MetricsCard(
            metrics_frame, 
            "Response Rate", 
            "0%", 
            "Average response",
            ModernTheme.SUCCESS_COLOR
        )
        self.response_rate_card.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        self.active_campaigns_card = MetricsCard(
            metrics_frame, 
            "Active Campaigns", 
            "0", 
            "Currently running"
        )
        self.active_campaigns_card.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.awaiting_approval_card = MetricsCard(
            metrics_frame,
            "Awaiting Approval",
            "0",
            "Drafts to review",
            ModernTheme.WARNING_COLOR
        )
        self.awaiting_approval_card.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.sent_messages_card = MetricsCard(
            metrics_frame,
            "Approved/Sent",
            "0 / 0",
            "Ready and sent"
        )
        self.sent_messages_card.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.followups_due_card = MetricsCard(
            metrics_frame,
            "Follow-ups Due",
            "0",
            "Need review",
            ModernTheme.WARNING_COLOR
        )
        self.followups_due_card.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.failed_sends_card = MetricsCard(
            metrics_frame,
            "Failed Sends",
            "0",
            "Needs attention",
            ModernTheme.ERROR_COLOR
        )
        self.failed_sends_card.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        self.strong_matches_card = MetricsCard(
            metrics_frame,
            "Strong Matches",
            "0",
            "Assessed fit",
            ModernTheme.SUCCESS_COLOR
        )
        self.strong_matches_card.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        self.retention_actions_card = MetricsCard(
            metrics_frame,
            "Retention Review",
            "0",
            "Proposed actions",
            ModernTheme.WARNING_COLOR
        )
        self.retention_actions_card.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        
        # Recent activity section
        activity_frame = ctk.CTkFrame(self)
        activity_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        activity_frame.grid_columnconfigure(0, weight=1)
        
        activity_title = ctk.CTkLabel(
            activity_frame,
            text="Recent Activity",
            font=ModernTheme.FONT_MEDIUM
        )
        activity_title.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        # Activity list
        self.activity_text = ctk.CTkTextbox(
            activity_frame,
            height=150,
            font=ModernTheme.FONT_SMALL
        )
        self.activity_text.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        
    def refresh_data(self):
        """Refresh dashboard data"""
        if self.data_callback:
            try:
                data = self.data_callback()
                self.update_metrics(data)
                self.update_activity(data.get('recent_activity', []))
            except (AttributeError, KeyError, TypeError, RuntimeError) as e:
                logger.error(f"Error refreshing dashboard data: {e}")
                
    def update_metrics(self, data: Dict[str, Any]):
        """Update metrics cards"""
        self.total_volunteers_card.update_value(
            str(data.get('total_volunteers', 0)),
            "In database"
        )
        
        self.total_contacts_card.update_value(
            str(data.get('total_contacts', 0)),
            "Messages sent"
        )
        
        response_rate = data.get('response_rate', 0)
        self.response_rate_card.update_value(
            f"{response_rate:.1f}%",
            "Average response"
        )
        
        self.active_campaigns_card.update_value(
            str(data.get('total_campaigns', 0)),
            "Currently running"
        )

        self.awaiting_approval_card.update_value(
            str(data.get('message_drafts_draft', 0)),
            "Drafts to review"
        )

        self.sent_messages_card.update_value(
            f"{data.get('message_drafts_approved', 0)} / {data.get('message_drafts_sent', 0)}",
            "Approved / sent"
        )

        self.followups_due_card.update_value(
            str(data.get('follow_ups_due', 0)),
            "Need review"
        )

        self.failed_sends_card.update_value(
            str(data.get('failed_sends', 0)),
            "Needs attention"
        )

        self.strong_matches_card.update_value(
            str(data.get('strong_matches', 0)),
            "Assessed fit"
        )

        self.retention_actions_card.update_value(
            str(data.get('retention_actions_proposed', 0)),
            "Proposed actions"
        )
        
    def update_activity(self, activities: List[str]):
        """Update recent activity"""
        self.activity_text.delete("1.0", "end")
        
        if activities:
            for activity in activities[-10:]:  # Show last 10 activities
                self.activity_text.insert("end", f"• {activity}\n")
        else:
            self.activity_text.insert("end", "No recent activity")


class SearchWorkspaceView(ctk.CTkFrame):
    """Operator-controlled live search and local candidate import."""

    def __init__(self, parent, action_callback: Callable = None, status_callback: Callable = None):
        super().__init__(parent)
        self.action_callback = action_callback
        self.status_callback = status_callback
        self.grid_columnconfigure(0, weight=1)
        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Candidate Intake", font=ModernTheme.FONT_LARGE).grid(
            row=0, column=0, padx=15, pady=15, sticky="w"
        )
        ctk.CTkButton(header, text="Refresh Status", command=self.refresh_status, width=120).grid(
            row=0, column=1, padx=15, pady=15
        )

        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        fields = [
            ("Location", "location", ""),
            ("Categories", "categories", ""),
            ("Distance (km)", "distance", "10"),
            ("Maximum pages", "max_pages", "5"),
        ]
        self.entries = {}
        for row, (label, key, default) in enumerate(fields):
            ctk.CTkLabel(form, text=label, font=ModernTheme.FONT_SMALL).grid(
                row=row, column=0, padx=15, pady=8, sticky="w"
            )
            entry = ctk.CTkEntry(form)
            entry.grid(row=row, column=1, padx=15, pady=8, sticky="ew")
            entry.insert(0, default)
            self.entries[key] = entry

        actions = ctk.CTkFrame(self)
        actions.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkButton(
            actions,
            text="Start Live Search",
            command=self.start_search,
            width=150,
        ).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(
            actions,
            text="Import CSV / JSON",
            command=self.import_candidates,
            width=150,
        ).pack(side="left", padx=10, pady=10)

        self.status_text = ctk.CTkTextbox(self, height=180, font=ModernTheme.FONT_SMALL)
        self.status_text.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.grid_rowconfigure(3, weight=1)

    def refresh_status(self):
        status = self.status_callback() if self.status_callback else {}
        runtime = status.get("runtime") or {}
        lines = [
            f"Live search enabled: {runtime.get('live_search_enabled', False)}",
            f"NLvoorelkaar connected: {status.get('nlvoorelkaar_connected', False)}",
            f"Safety stop active: {status.get('safety_stop_active', False)}",
            f"Maximum configured pages: {runtime.get('max_search_pages', 5)}",
            "",
            "Local CSV/JSON import does not contact NLvoorelkaar.",
            "Live search requires explicit configuration and a connected account.",
        ]
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", "\n".join(lines))

    def start_search(self):
        try:
            categories = [
                value.strip()
                for value in self.entries["categories"].get().split(",")
                if value.strip()
            ]
            payload = {
                "location": self.entries["location"].get().strip(),
                "categories": categories,
                "distance": int(self.entries["distance"].get()),
                "max_pages": int(self.entries["max_pages"].get()),
            }
            result = self.action_callback("live_search", payload) if self.action_callback else None
            self._show_result(f"Search task started: {result}")
        except (TypeError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Search not started", str(exc))
        self.refresh_status()

    def import_candidates(self):
        path = filedialog.askopenfilename(
            title="Import reviewed candidate data",
            filetypes=[("Candidate data", "*.csv *.json"), ("CSV", "*.csv"), ("JSON", "*.json")],
        )
        if not path:
            return
        try:
            result = self.action_callback("import", {"path": path}) if self.action_callback else None
            self._show_result(f"Import completed: {result}")
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Import failed", str(exc))

    def _show_result(self, message: str):
        self.status_text.insert("end", f"\n{message}")


class OperationsView(ctk.CTkFrame):
    """Provider readiness, backup, recovery, and emergency controls."""

    def __init__(self, parent, data_callback: Callable = None, action_callback: Callable = None):
        super().__init__(parent)
        self.data_callback = data_callback
        self.action_callback = action_callback
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Operations & Safety", font=ModernTheme.FONT_LARGE).grid(
            row=0, column=0, padx=15, pady=15, sticky="w"
        )
        ctk.CTkButton(header, text="Refresh", command=self.refresh_status, width=100).grid(
            row=0, column=1, padx=15, pady=15
        )

        controls = ctk.CTkFrame(self)
        controls.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        buttons = [
            ("Safety Stop", "safety_stop", ModernTheme.ERROR_COLOR),
            ("Clear Stop", "clear_stop", ModernTheme.WARNING_COLOR),
            ("Local Backup", "local_backup", ModernTheme.PRIMARY_COLOR),
            ("Backup to Drive", "drive_backup", ModernTheme.PRIMARY_COLOR),
            ("Reconcile Sends", "reconcile_sends", ModernTheme.SECONDARY_COLOR),
        ]
        for label, action, color in buttons:
            ctk.CTkButton(
                controls,
                text=label,
                command=lambda selected=action: self.run_action(selected),
                fg_color=color,
                width=130,
            ).pack(side="left", padx=6, pady=10)

        self.status_text = ctk.CTkTextbox(self, font=ModernTheme.FONT_SMALL)
        self.status_text.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")

    def refresh_status(self):
        status = self.data_callback() if self.data_callback else {}
        runtime = status.get("runtime") or {}
        drive = status.get("google_drive") or {}
        database = status.get("database") or {}
        lines = [
            f"Environment: {runtime.get('environment', 'unknown')}",
            f"Safety stop: {'ACTIVE' if status.get('safety_stop_active') else 'clear'}",
            f"NLvoorelkaar connection: {'connected' if status.get('nlvoorelkaar_connected') else 'not connected'}",
            f"Live search: {'enabled' if runtime.get('live_search_enabled') else 'disabled'}",
            f"Live send: {'enabled' if runtime.get('live_send_enabled') else 'disabled; manual assist only'}",
            f"Google Drive: {'connected' if drive.get('connected') else 'not connected'}",
            f"Google Drive opt-in: {'enabled' if runtime.get('google_drive_enabled') else 'disabled'}",
            f"Database integrity: {database.get('integrity', 'unknown')}",
            f"Schema version: {database.get('schema_version', 'unknown')}",
            f"Running tasks: {status.get('running_tasks', 0)}",
            f"Pending tasks: {status.get('pending_tasks', 0)}",
        ]
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", "\n".join(lines))

    def run_action(self, action: str):
        if action == "safety_stop" and not messagebox.askyesno(
            "Activate safety stop",
            "Block new provider actions and request cancellation of active tasks?",
        ):
            return
        if action == "drive_backup" and not messagebox.askyesno(
            "Upload backup",
            "Create a verified local backup and upload it to the app's Google Drive folder?",
        ):
            return
        try:
            result = self.action_callback(action, {}) if self.action_callback else None
            self.refresh_status()
            self.status_text.insert("end", f"\n\nAction result: {result}")
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Operation failed", str(exc))

class CampaignView(ctk.CTkFrame):
    """Modern campaign management view"""
    
    def __init__(
        self,
        parent,
        campaign_callback: Callable = None,
        data_callback: Callable = None,
        readiness_callback: Callable = None,
        operating_summary_callback: Callable = None
    ):
        super().__init__(parent)
        self.campaign_callback = campaign_callback
        self.data_callback = data_callback
        self.readiness_callback = readiness_callback
        self.operating_summary_callback = operating_summary_callback
        self.selected_campaign_id = None
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.setup_ui()
        self.refresh_campaigns()
        
    def setup_ui(self):
        """Setup campaign management UI"""
        # Title and controls
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="Campaign Management",
            font=ModernTheme.FONT_LARGE
        )
        title_label.grid(row=0, column=0, padx=15, pady=15, sticky="w")
        
        refresh_button = ctk.CTkButton(
            header_frame,
            text="Refresh",
            command=self.refresh_campaigns,
            width=100
        )
        refresh_button.grid(row=0, column=1, padx=(15, 5), pady=15, sticky="e")

        new_campaign_button = ctk.CTkButton(
            header_frame,
            text="+ New Campaign",
            command=self.create_new_campaign,
            width=150
        )
        new_campaign_button.grid(row=0, column=2, padx=(5, 15), pady=15, sticky="e")
        
        # Campaign list
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)
        
        list_title = ctk.CTkLabel(
            list_frame,
            text="Campaigns",
            font=ModernTheme.FONT_MEDIUM
        )
        list_title.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        # Campaign list with scrollbar
        self.campaign_list = ctk.CTkScrollableFrame(list_frame)
        self.campaign_list.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        
        # Campaign details
        details_frame = ctk.CTkFrame(self)
        details_frame.grid(row=1, column=1, padx=(10, 20), pady=10, sticky="nsew")
        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_rowconfigure(1, weight=1)
        
        details_title = ctk.CTkLabel(
            details_frame,
            text="Campaign Details",
            font=ModernTheme.FONT_MEDIUM
        )
        details_title.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        self.details_text = ctk.CTkTextbox(
            details_frame,
            font=ModernTheme.FONT_SMALL
        )
        self.details_text.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="nsew")

        self.details_text.insert("1.0", "Select a campaign to inspect readiness.")
        self.details_text.configure(state="disabled")

        action_frame = ctk.CTkFrame(details_frame)
        action_frame.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="ew")

        self.create_drafts_button = ctk.CTkButton(
            action_frame,
            text="Create Drafts",
            command=self.create_drafts_for_selected,
            width=130,
            state="disabled"
        )
        self.create_drafts_button.pack(side="right", padx=8, pady=8)

        self.assess_matches_button = ctk.CTkButton(
            action_frame,
            text="Assess Matches",
            command=self.assess_matches_for_selected,
            width=130,
            state="disabled"
        )
        self.assess_matches_button.pack(side="right", padx=8, pady=8)

        self.send_approved_button = ctk.CTkButton(
            action_frame,
            text="Send Approved",
            command=self.send_approved_for_selected,
            width=130,
            state="disabled",
            fg_color=ModernTheme.WARNING_COLOR,
        )
        self.send_approved_button.pack(side="right", padx=8, pady=8)
        
    def create_new_campaign(self):
        """Open new campaign dialog"""
        dialog = CampaignDialog(self, "New Campaign")
        if dialog.result:
            if self.campaign_callback:
                self.campaign_callback('create', dialog.result)
            self.refresh_campaigns()
            
    def refresh_campaigns(self):
        """Refresh campaign list"""
        # Clear existing campaigns
        for widget in self.campaign_list.winfo_children():
            widget.destroy()
            
        campaigns = []
        if self.data_callback:
            try:
                campaigns = self.data_callback() or []
            except (AttributeError, TypeError, RuntimeError, ValueError) as exc:
                logger.error(f"Error loading campaigns: {exc}")

        if not campaigns:
            empty_label = ctk.CTkLabel(
                self.campaign_list,
                text="No campaigns yet.",
                font=ModernTheme.FONT_MEDIUM,
                text_color=ModernTheme.TEXT_SECONDARY
            )
            empty_label.grid(row=0, column=0, padx=15, pady=20, sticky="w")
            self.show_campaign_details(None)
            return

        for campaign in campaigns:
            self.add_campaign_item(campaign)

        if self.selected_campaign_id:
            selected = next((c for c in campaigns if c.get("id") == self.selected_campaign_id), None)
            self.show_campaign_details(selected)
            
    def add_campaign_item(self, campaign: Dict[str, Any]):
        """Add campaign item to list"""
        item_frame = ctk.CTkFrame(self.campaign_list)
        item_frame.pack(fill="x", padx=5, pady=5)
        item_frame.grid_columnconfigure(1, weight=1)
        
        # Campaign name
        name_label = ctk.CTkLabel(
            item_frame,
            text=campaign.get("name", "Untitled campaign"),
            font=ModernTheme.FONT_MEDIUM
        )
        name_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Status
        status = campaign.get("status", "active")
        status_color = ModernTheme.SUCCESS_COLOR if str(status).lower() == "active" else ModernTheme.WARNING_COLOR
        status_label = ctk.CTkLabel(
            item_frame,
            text=str(status).title(),
            font=ModernTheme.FONT_SMALL,
            text_color=status_color
        )
        status_label.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        target_text = campaign.get("target_categories") or "Any category"
        location_text = campaign.get("target_location") or "Any location"
        target_label = ctk.CTkLabel(
            item_frame,
            text=f"{target_text} | {location_text}",
            font=ModernTheme.FONT_SMALL,
            text_color=ModernTheme.TEXT_SECONDARY
        )
        target_label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 6), sticky="w")

        select_button = ctk.CTkButton(
            item_frame,
            text="Select",
            command=lambda selected=campaign: self.show_campaign_details(selected),
            width=90
        )
        select_button.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="e")

    def show_campaign_details(self, campaign: Optional[Dict[str, Any]]):
        """Show details and readiness for the selected campaign."""
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", "end")

        if not campaign:
            self.selected_campaign_id = None
            self.create_drafts_button.configure(state="disabled")
            self.assess_matches_button.configure(state="disabled")
            self.send_approved_button.configure(state="disabled")
            self.details_text.insert("1.0", "Select a campaign to inspect readiness.")
            self.details_text.configure(state="disabled")
            return

        self.selected_campaign_id = campaign.get("id")
        readiness = {}
        if self.readiness_callback and self.selected_campaign_id:
            try:
                readiness = self.readiness_callback(self.selected_campaign_id) or {}
            except (AttributeError, TypeError, RuntimeError, ValueError) as exc:
                logger.error(f"Error loading campaign readiness: {exc}")
                readiness = {"ready": False, "issues": [{"severity": "error", "message": str(exc)}]}

        operating_summary = {}
        if self.operating_summary_callback and self.selected_campaign_id:
            try:
                operating_summary = self.operating_summary_callback(self.selected_campaign_id) or {}
            except (AttributeError, TypeError, RuntimeError, ValueError) as exc:
                logger.error(f"Error loading campaign operating summary: {exc}")

        lines = [
            f"Name: {campaign.get('name', 'Untitled campaign')}",
            f"Status: {campaign.get('status', 'active')}",
            f"Target categories: {campaign.get('target_categories') or 'Any'}",
            f"Target location: {campaign.get('target_location') or 'Any'}",
            "",
            "Message template:",
            campaign.get("message_template") or "Missing message template.",
            "",
            "Readiness:",
            f"- State: {readiness.get('status', 'unknown')}",
            f"- Eligible volunteers: {readiness.get('eligible_volunteers', 0)}"
        ]

        draft_counts = readiness.get("draft_counts") or {}
        if draft_counts:
            lines.extend([
                f"- Drafts awaiting approval: {draft_counts.get('draft', 0)}",
                f"- Approved drafts: {draft_counts.get('approved', 0)}",
                f"- Sent drafts: {draft_counts.get('sent', 0)}",
                f"- Failed drafts: {draft_counts.get('failed', 0)}"
            ])

        match_counts = readiness.get("match_counts") or {}
        if match_counts:
            lines.extend([
                f"- Strong matches: {match_counts.get('strong', 0)}",
                f"- Possible matches: {match_counts.get('possible', 0)}",
                f"- Weak matches: {match_counts.get('weak', 0)}"
            ])

        issues = readiness.get("issues") or []
        if issues:
            lines.append("")
            lines.append("Issues:")
            lines.extend(f"- {issue.get('severity', 'info')}: {issue.get('message', '')}" for issue in issues)

        next_actions = readiness.get("next_actions") or []
        summary_actions = operating_summary.get("next_actions") or []
        for action in summary_actions:
            if action not in next_actions:
                next_actions.append(action)
        if next_actions:
            lines.append("")
            lines.append("Next actions:")
            lines.extend(f"- {action}" for action in next_actions)

        if operating_summary:
            lines.extend(self.format_operating_summary(operating_summary))

        self.details_text.insert("1.0", "\n".join(lines))
        self.details_text.configure(state="disabled")

        button_state = "normal" if readiness.get("ready") else "disabled"
        self.create_drafts_button.configure(state=button_state)
        self.assess_matches_button.configure(state=button_state)
        approved_count = int((readiness.get("draft_counts") or {}).get("approved", 0))
        self.send_approved_button.configure(state="normal" if approved_count else "disabled")

    def format_operating_summary(self, summary: Dict[str, Any]) -> List[str]:
        """Format campaign ledger state for compact operator review."""
        counts = summary.get("counts") or {}
        draft_counts = counts.get("message_drafts") or {}
        send_counts = counts.get("send_attempts") or {}
        response_counts = counts.get("responses") or {}
        follow_up_counts = counts.get("follow_ups") or {}
        match_counts = counts.get("matches") or {}
        outcome_counts = counts.get("outcomes") or {}
        exclusion_counts = counts.get("exclusions") or {}

        lines = [
            "",
            "Operating ledger:",
            f"- Eligible volunteers: {counts.get('eligible_volunteers', 0)}",
            f"- Contacts recorded: {counts.get('contacts', 0)}",
            f"- Drafts: {self.format_counts(draft_counts)}",
            f"- Send attempts: {self.format_counts(send_counts)}",
            f"- Responses: {self.format_counts(response_counts)}",
            f"- Follow-ups: {self.format_counts(follow_up_counts)}",
            f"- Matches: {self.format_counts(match_counts)}",
            f"- Exclusions: {counts.get('excluded_volunteers', 0)} volunteers; {self.format_counts(exclusion_counts)}",
            f"- Outcomes: {self.format_counts(outcome_counts)}"
        ]

        recent_sections = [
            ("Recent matches", summary.get("matches") or [], self.format_match_line),
            ("Recent exclusions", summary.get("exclusions") or [], self.format_exclusion_line),
            ("Recent drafts", summary.get("message_drafts") or [], self.format_draft_line),
            ("Recent send attempts", summary.get("send_attempts") or [], self.format_send_line),
            ("Recent responses", summary.get("responses") or [], self.format_response_line),
            ("Upcoming follow-ups", summary.get("follow_ups") or [], self.format_follow_up_line),
            ("Recorded outcomes", summary.get("outcomes") or [], self.format_outcome_line),
            ("Recent audit", summary.get("audit_events") or [], self.format_audit_line)
        ]

        for title, items, formatter in recent_sections:
            if not items:
                continue
            lines.extend(["", f"{title}:"])
            lines.extend(f"- {formatter(item)}" for item in items[:5])

        return lines

    def format_counts(self, counts: Dict[str, int]) -> str:
        """Format status buckets for display."""
        if not counts:
            return "none"
        return ", ".join(f"{key} {value}" for key, value in sorted(counts.items()))

    def format_match_line(self, item: Dict[str, Any]) -> str:
        return (
            f"{item.get('volunteer_name') or item.get('volunteer_id')} "
            f"{item.get('status', 'unknown')} ({item.get('score', 0):.0f})"
        )

    def format_exclusion_line(self, item: Dict[str, Any]) -> str:
        return (
            f"{item.get('volunteer_name') or item.get('volunteer_id')} | "
            f"{item.get('reason_code', 'excluded')} | "
            f"{item.get('reason_message') or 'No reason saved.'}"
        )

    def format_draft_line(self, item: Dict[str, Any]) -> str:
        return (
            f"{item.get('volunteer_name') or item.get('volunteer_id')} | "
            f"{item.get('status', 'draft')} | {item.get('updated_at') or 'unknown date'}"
        )

    def format_send_line(self, item: Dict[str, Any]) -> str:
        detail = item.get("error_message") or item.get("delivery_evidence") or "no evidence saved"
        return (
            f"{item.get('volunteer_name') or item.get('volunteer_id')} | "
            f"{item.get('status', 'unknown')} | {detail}"
        )

    def format_response_line(self, item: Dict[str, Any]) -> str:
        return (
            f"{item.get('volunteer_name') or item.get('volunteer_id')} | "
            f"{item.get('classification', 'unknown')} | {item.get('received_at') or 'unknown date'}"
        )

    def format_follow_up_line(self, item: Dict[str, Any]) -> str:
        return (
            f"{item.get('volunteer_name') or item.get('volunteer_id')} | "
            f"{item.get('status', 'due')} | due {item.get('due_at') or 'unknown'}"
        )

    def format_outcome_line(self, item: Dict[str, Any]) -> str:
        return (
            f"{item.get('volunteer_name') or item.get('volunteer_id')} | "
            f"{item.get('outcome_type', 'unknown')} | "
            f"{item.get('notes') or 'no notes'}"
        )

    def format_audit_line(self, item: Dict[str, Any]) -> str:
        return (
            f"{item.get('action', 'event')} | "
            f"{item.get('entity_type', 'entity')} #{item.get('entity_id', '')} | "
            f"{item.get('created_at') or 'unknown date'}"
        )

    def create_drafts_for_selected(self):
        """Create reviewable message drafts for the selected campaign."""
        if not self.selected_campaign_id:
            return
        if self.campaign_callback:
            self.campaign_callback("create_drafts", {"campaign_id": self.selected_campaign_id})
        self.refresh_campaigns()

    def assess_matches_for_selected(self):
        """Assess eligible volunteer matches for the selected campaign."""
        if not self.selected_campaign_id:
            return
        if self.campaign_callback:
            self.campaign_callback("assess_matches", {"campaign_id": self.selected_campaign_id})
        self.refresh_campaigns()

    def send_approved_for_selected(self):
        """Request one bounded send batch after a final safety confirmation."""
        if not self.selected_campaign_id:
            return
        if not messagebox.askyesno(
            "Send approved messages",
            "Send the approved message snapshots for this campaign now? "
            "Live sending must be explicitly enabled; otherwise use the manual assist path.",
        ):
            return
        try:
            if self.campaign_callback:
                self.campaign_callback("send_approved", {"campaign_id": self.selected_campaign_id})
        except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Messages not sent", str(exc))
        self.refresh_campaigns()

class CampaignDialog(ctk.CTkToplevel):
    """Modern campaign creation/editing dialog"""
    
    def __init__(self, parent, title: str, campaign_data: Dict = None):
        super().__init__(parent)
        
        self.title(title)
        self.geometry("500x600")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")
        
        self.result = None
        self.setup_ui(campaign_data)
        
    def setup_ui(self, campaign_data: Dict = None):
        """Setup dialog UI"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Campaign name
        name_label = ctk.CTkLabel(main_frame, text="Campaign Name:")
        name_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.name_entry = ctk.CTkEntry(main_frame, width=300)
        self.name_entry.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="ew")
        
        # Description
        desc_label = ctk.CTkLabel(main_frame, text="Description:")
        desc_label.grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        
        self.desc_text = ctk.CTkTextbox(main_frame, height=100, width=300)
        self.desc_text.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Target categories
        cat_label = ctk.CTkLabel(main_frame, text="Target Categories:")
        cat_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.categories_entry = ctk.CTkEntry(main_frame, width=300)
        self.categories_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Location
        loc_label = ctk.CTkLabel(main_frame, text="Location:")
        loc_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        self.location_entry = ctk.CTkEntry(main_frame, width=300)
        self.location_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        # Message template
        msg_label = ctk.CTkLabel(main_frame, text="Message Template:")
        msg_label.grid(row=4, column=0, padx=10, pady=5, sticky="nw")
        
        self.message_text = ctk.CTkTextbox(main_frame, height=200, width=300)
        self.message_text.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20, sticky="ew")
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.cancel,
            width=100
        )
        cancel_button.pack(side="right", padx=(10, 0))
        
        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self.save,
            width=100
        )
        save_button.pack(side="right")
        
        # Load existing data
        if campaign_data:
            self.load_campaign_data(campaign_data)
            
    def load_campaign_data(self, data: Dict):
        """Load existing campaign data"""
        self.name_entry.insert(0, data.get('name', ''))
        self.desc_text.insert("1.0", data.get('description', ''))
        self.categories_entry.insert(0, data.get('target_categories', ''))
        self.location_entry.insert(0, data.get('target_location', ''))
        self.message_text.insert("1.0", data.get('message_template', ''))
        
    def save(self):
        """Save campaign data"""
        self.result = {
            'name': self.name_entry.get(),
            'description': self.desc_text.get("1.0", "end-1c"),
            'target_categories': self.categories_entry.get(),
            'target_location': self.location_entry.get(),
            'message_template': self.message_text.get("1.0", "end-1c")
        }
        self.destroy()
        
    def cancel(self):
        """Cancel dialog"""
        self.result = None
        self.destroy()

class ResponseDialog(ctk.CTkToplevel):
    """Dialog for manually recording a volunteer response."""

    def __init__(
        self,
        parent,
        volunteers: List[Dict[str, Any]],
        campaigns: List[Dict[str, Any]]
    ):
        super().__init__(parent)
        self.title("Record Response")
        self.geometry("560x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.volunteers = volunteers or []
        self.campaigns = campaigns or []
        self.volunteer_options: Dict[str, str] = {}
        self.campaign_options: Dict[str, Optional[int]] = {"No campaign": None}
        self.result = None

        self.setup_ui()
        self.wait_window()

    def setup_ui(self):
        """Build response-entry controls."""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        main_frame.grid_columnconfigure(1, weight=1)

        volunteer_label = ctk.CTkLabel(main_frame, text="Volunteer:")
        volunteer_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        volunteer_values = []
        for volunteer in self.volunteers:
            volunteer_id = volunteer.get("volunteer_id")
            if not volunteer_id:
                continue
            label = f"{volunteer.get('name') or 'Unknown volunteer'} ({volunteer_id})"
            volunteer_values.append(label)
            self.volunteer_options[label] = volunteer_id

        self.volunteer_combo = ctk.CTkComboBox(main_frame, values=volunteer_values, state="readonly")
        self.volunteer_combo.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="ew")
        if volunteer_values:
            self.volunteer_combo.set(volunteer_values[0])

        campaign_label = ctk.CTkLabel(main_frame, text="Campaign:")
        campaign_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        campaign_values = ["No campaign"]
        for campaign in self.campaigns:
            campaign_id = campaign.get("id")
            if campaign_id is None:
                continue
            label = f"{campaign.get('name') or 'Campaign'} (#{campaign_id})"
            campaign_values.append(label)
            self.campaign_options[label] = campaign_id

        self.campaign_combo = ctk.CTkComboBox(main_frame, values=campaign_values, state="readonly")
        self.campaign_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.campaign_combo.set(campaign_values[0])

        response_label = ctk.CTkLabel(main_frame, text="Response:")
        response_label.grid(row=2, column=0, padx=10, pady=5, sticky="nw")

        self.response_text = ctk.CTkTextbox(main_frame, height=260, width=360)
        self.response_text.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        button_frame = ctk.CTkFrame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20, sticky="ew")

        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.cancel, width=100)
        cancel_button.pack(side="right", padx=(10, 0))

        save_button = ctk.CTkButton(button_frame, text="Record", command=self.save, width=100)
        save_button.pack(side="right")

    def save(self):
        """Validate and store dialog result."""
        selected_volunteer = self.volunteer_combo.get()
        volunteer_id = self.volunteer_options.get(selected_volunteer)
        raw_content = self.response_text.get("1.0", "end-1c").strip()

        if not volunteer_id:
            messagebox.showerror("Validation Error", "Select a volunteer.")
            return
        if not raw_content:
            messagebox.showerror("Validation Error", "Enter the volunteer response.")
            return

        self.result = {
            "volunteer_id": volunteer_id,
            "campaign_id": self.campaign_options.get(self.campaign_combo.get()),
            "raw_content": raw_content
        }
        self.destroy()

    def cancel(self):
        """Close without recording a response."""
        self.destroy()

class MessageReviewView(ctk.CTkFrame):
    """Review queue for generated volunteer outreach drafts."""

    def __init__(self, parent, data_callback: Callable = None, action_callback: Callable = None):
        super().__init__(parent)
        self.data_callback = data_callback
        self.action_callback = action_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.setup_ui()
        self.refresh_messages()

    def setup_ui(self):
        """Setup message review UI."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="Message Review Queue",
            font=ModernTheme.FONT_LARGE
        )
        title_label.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        refresh_button = ctk.CTkButton(
            header_frame,
            text="Refresh",
            command=self.refresh_messages,
            width=100
        )
        refresh_button.grid(row=0, column=1, padx=15, pady=15, sticky="e")

        self.message_list = ctk.CTkScrollableFrame(self)
        self.message_list.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.message_list.grid_columnconfigure(0, weight=1)

    def refresh_messages(self):
        """Refresh draft list from callback."""
        for widget in self.message_list.winfo_children():
            widget.destroy()

        drafts = []
        if self.data_callback:
            try:
                drafts = self.data_callback() or []
            except (AttributeError, TypeError, RuntimeError, ValueError) as exc:
                logger.error(f"Error loading message review data: {exc}")

        if not drafts:
            empty_label = ctk.CTkLabel(
                self.message_list,
                text="No draft messages are waiting for approval.",
                font=ModernTheme.FONT_MEDIUM,
                text_color=ModernTheme.TEXT_SECONDARY
            )
            empty_label.grid(row=0, column=0, padx=15, pady=20, sticky="w")
            return

        for row_index, draft in enumerate(drafts):
            self.add_message_item(row_index, draft)

    def add_message_item(self, row_index: int, draft: Dict[str, Any]):
        """Add one draft review item."""
        item_frame = ctk.CTkFrame(self.message_list)
        item_frame.grid(row=row_index, column=0, padx=5, pady=6, sticky="ew")
        item_frame.grid_columnconfigure(0, weight=1)

        title = f"{draft.get('volunteer_name') or draft.get('volunteer_id')} - {draft.get('campaign_name') or 'Campaign'}"
        title_label = ctk.CTkLabel(
            item_frame,
            text=title,
            font=ModernTheme.FONT_MEDIUM
        )
        title_label.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        meta_label = ctk.CTkLabel(
            item_frame,
            text=f"Status: {draft.get('status', 'draft')} | Location: {draft.get('volunteer_location') or 'unknown'}",
            font=ModernTheme.FONT_SMALL,
            text_color=ModernTheme.TEXT_SECONDARY
        )
        meta_label.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")

        subject_entry = ctk.CTkEntry(item_frame, font=ModernTheme.FONT_SMALL)
        subject_entry.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="ew")
        subject_entry.insert(0, draft.get("subject") or "")

        body_text = ctk.CTkTextbox(item_frame, height=150, font=ModernTheme.FONT_SMALL)
        body_text.grid(row=3, column=0, padx=12, pady=6, sticky="ew")
        body_text.insert("1.0", (draft.get('body') or '').strip())

        button_frame = ctk.CTkFrame(item_frame)
        button_frame.grid(row=4, column=0, padx=12, pady=(6, 12), sticky="e")

        ctk.CTkButton(
            button_frame,
            text="Copy Message",
            command=lambda body=body_text: self.copy_message(body),
            width=110,
        ).pack(side="left", padx=5)

        status = draft.get("status", "draft")
        if status in {"draft", "approved", "failed"}:
            ctk.CTkButton(
                button_frame,
                text="Save Edits",
                command=lambda draft_id=draft['id'], subject=subject_entry, body=body_text: self.handle_edit(draft_id, subject, body),
                width=110,
            ).pack(side="left", padx=5)

        if status in {"draft", "failed"}:
            ctk.CTkButton(
                button_frame,
                text="Approve",
                command=lambda draft_id=draft['id']: self.handle_action("approve", draft_id),
                width=100,
            ).pack(side="left", padx=5)

        if status == "approved":
            ctk.CTkButton(
                button_frame,
                text="Confirm Manual Send",
                command=lambda draft_id=draft['id']: self.handle_action("confirm_manual_send", draft_id),
                width=150,
                fg_color=ModernTheme.WARNING_COLOR,
            ).pack(side="left", padx=5)

        if status != "approved":
            ctk.CTkButton(
                button_frame,
                text="Reject",
                command=lambda draft_id=draft['id']: self.handle_action("reject", draft_id),
                width=100,
                fg_color=ModernTheme.ERROR_COLOR,
            ).pack(side="left", padx=5)

    def handle_action(self, action: str, draft_id: int):
        """Handle approve/reject action."""
        if self.action_callback:
            self.action_callback(action, {"draft_id": draft_id})
        self.refresh_messages()

    def handle_edit(self, draft_id: int, subject_entry, body_text):
        """Persist operator edits to a draft."""
        if self.action_callback:
            self.action_callback("edit", {
                "draft_id": draft_id,
                "subject": subject_entry.get(),
                "body": body_text.get("1.0", "end-1c")
            })
        self.refresh_messages()

    def copy_message(self, body_text):
        """Copy the exact reviewed message body for the assisted manual-send path."""
        self.clipboard_clear()
        self.clipboard_append(body_text.get("1.0", "end-1c"))
        self.update_idletasks()

class VolunteerDetailView(ctk.CTkFrame):
    """Volunteer profile and outreach ledger detail view."""

    def __init__(self, parent, data_callback: Callable = None, detail_callback: Callable = None):
        super().__init__(parent)
        self.data_callback = data_callback
        self.detail_callback = detail_callback
        self.selected_volunteer_id = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.setup_ui()
        self.refresh_volunteers()

    def setup_ui(self):
        """Setup volunteer detail UI."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="Volunteer Profiles",
            font=ModernTheme.FONT_LARGE
        )
        title_label.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        refresh_button = ctk.CTkButton(
            header_frame,
            text="Refresh",
            command=self.refresh_volunteers,
            width=100
        )
        refresh_button.grid(row=0, column=1, padx=15, pady=15, sticky="e")

        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        list_title = ctk.CTkLabel(
            list_frame,
            text="Saved Volunteers",
            font=ModernTheme.FONT_MEDIUM
        )
        list_title.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        self.volunteer_list = ctk.CTkScrollableFrame(list_frame, width=320)
        self.volunteer_list.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.volunteer_list.grid_columnconfigure(0, weight=1)

        detail_frame = ctk.CTkFrame(self)
        detail_frame.grid(row=1, column=1, padx=(10, 20), pady=10, sticky="nsew")
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(1, weight=1)

        detail_title = ctk.CTkLabel(
            detail_frame,
            text="Volunteer Detail",
            font=ModernTheme.FONT_MEDIUM
        )
        detail_title.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        self.detail_text = ctk.CTkTextbox(detail_frame, font=ModernTheme.FONT_SMALL)
        self.detail_text.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.show_empty_detail()

    def refresh_volunteers(self):
        """Refresh volunteer list."""
        for widget in self.volunteer_list.winfo_children():
            widget.destroy()

        volunteers = []
        if self.data_callback:
            try:
                volunteers = self.data_callback() or []
            except (AttributeError, TypeError, RuntimeError, ValueError) as exc:
                logger.error(f"Error loading volunteers: {exc}")

        if not volunteers:
            empty_label = ctk.CTkLabel(
                self.volunteer_list,
                text="No volunteers saved yet.",
                font=ModernTheme.FONT_MEDIUM,
                text_color=ModernTheme.TEXT_SECONDARY
            )
            empty_label.grid(row=0, column=0, padx=15, pady=20, sticky="w")
            self.show_empty_detail()
            return

        for row_index, volunteer in enumerate(volunteers):
            self.add_volunteer_item(row_index, volunteer)

        if self.selected_volunteer_id:
            self.show_volunteer_detail(self.selected_volunteer_id)

    def add_volunteer_item(self, row_index: int, volunteer: Dict[str, Any]):
        """Add one volunteer list item."""
        item_frame = ctk.CTkFrame(self.volunteer_list)
        item_frame.grid(row=row_index, column=0, padx=5, pady=6, sticky="ew")
        item_frame.grid_columnconfigure(0, weight=1)

        title = volunteer.get("name") or volunteer.get("volunteer_id") or "Unknown volunteer"
        title_label = ctk.CTkLabel(
            item_frame,
            text=title,
            font=ModernTheme.FONT_MEDIUM
        )
        title_label.grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")

        meta_label = ctk.CTkLabel(
            item_frame,
            text=f"{volunteer.get('location') or 'Unknown location'} | {volunteer.get('categories') or 'No categories'}",
            font=ModernTheme.FONT_SMALL,
            text_color=ModernTheme.TEXT_SECONDARY
        )
        meta_label.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="w")

        select_button = ctk.CTkButton(
            item_frame,
            text="Select",
            command=lambda volunteer_id=volunteer.get("volunteer_id"): self.show_volunteer_detail(volunteer_id),
            width=90
        )
        select_button.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="e")

    def show_empty_detail(self):
        """Show empty-state detail copy."""
        self.selected_volunteer_id = None
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", "Select a volunteer to inspect profile, match, contact, response, follow-up, and duplicate context.")
        self.detail_text.configure(state="disabled")

    def show_volunteer_detail(self, volunteer_id: str):
        """Load and render one volunteer operating profile."""
        if not volunteer_id:
            self.show_empty_detail()
            return

        self.selected_volunteer_id = volunteer_id
        profile = None
        if self.detail_callback:
            try:
                profile = self.detail_callback(volunteer_id)
            except (AttributeError, TypeError, RuntimeError, ValueError) as exc:
                logger.error(f"Error loading volunteer detail: {exc}")

        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", self.format_profile(profile))
        self.detail_text.configure(state="disabled")

    def format_profile(self, profile: Optional[Dict[str, Any]]) -> str:
        """Format one volunteer operating profile."""
        if not profile:
            return "Volunteer profile could not be loaded."

        volunteer = profile.get("volunteer") or {}
        lines = [
            f"Name: {volunteer.get('name') or 'Unknown volunteer'}",
            f"Volunteer ID: {volunteer.get('volunteer_id') or ''}",
            f"Location: {volunteer.get('location') or 'Unknown'}",
            f"Categories: {volunteer.get('categories') or 'Unknown'}",
            f"Skills: {volunteer.get('skills') or 'Unknown'}",
            f"Availability: {volunteer.get('availability') or 'Unknown'}",
            f"Source URL: {volunteer.get('profile_url') or 'Not saved'}",
            f"Updated: {volunteer.get('updated_at') or 'Unknown'}",
            "",
            "Description:",
            volunteer.get("description") or "No description saved."
        ]

        self.append_section(lines, "Match Assessments", profile.get("match_assessments") or [], self.format_match)
        self.append_section(lines, "Contact History", profile.get("contacts") or [], self.format_contact)
        self.append_section(lines, "Responses", profile.get("responses") or [], self.format_response)
        self.append_section(lines, "Follow-ups", profile.get("follow_ups") or [], self.format_follow_up)
        self.append_section(lines, "Outcomes", profile.get("outcomes") or [], self.format_outcome)
        self.append_section(lines, "Duplicate Groups", profile.get("duplicate_identities") or [], self.format_duplicate)

        return "\n".join(lines)

    def append_section(self, lines: List[str], title: str, items: List[Dict[str, Any]], formatter: Callable):
        """Append a compact profile section."""
        lines.extend(["", title + ":"])
        if not items:
            lines.append("- None recorded")
            return
        for item in items[:10]:
            lines.append(formatter(item))

    def format_match(self, item: Dict[str, Any]) -> str:
        return (
            f"- {item.get('campaign_name') or 'Campaign'}: "
            f"{item.get('status', 'unknown')} fit, score {item.get('score', 0):.0f}; "
            f"reasons {item.get('reasons_json') or '[]'}"
        )

    def format_contact(self, item: Dict[str, Any]) -> str:
        return (
            f"- {item.get('contact_date') or 'Unknown date'} | "
            f"{item.get('campaign_name') or 'No campaign'} | "
            f"status {item.get('status', 'unknown')}"
        )

    def format_response(self, item: Dict[str, Any]) -> str:
        return (
            f"- {item.get('received_at') or 'Unknown date'} | "
            f"{item.get('campaign_name') or 'No campaign'} | "
            f"{item.get('classification', 'unknown')}: {item.get('raw_content') or ''}"
        )

    def format_follow_up(self, item: Dict[str, Any]) -> str:
        return (
            f"- Due {item.get('due_at') or 'unknown'} | "
            f"{item.get('campaign_name') or 'No campaign'} | "
            f"status {item.get('status', 'unknown')}: {item.get('suggested_message') or ''}"
        )

    def format_duplicate(self, item: Dict[str, Any]) -> str:
        return (
            f"- Group {item.get('id')} | status {item.get('status', 'unknown')} | "
            f"canonical {item.get('canonical_volunteer_id')}; members {item.get('volunteer_ids') or ''}"
        )

class LedgerListView(ctk.CTkFrame):
    """Reusable read-first view for operational ledger queues."""

    def __init__(
        self,
        parent,
        title: str,
        empty_text: str,
        data_callback: Callable = None,
        action_callback: Callable = None,
        item_kind: str = "ledger",
        header_action_text: str = "",
        secondary_header_action_text: str = "",
        secondary_header_action_name: str = "secondary_header_action"
    ):
        super().__init__(parent)
        self.title = title
        self.empty_text = empty_text
        self.data_callback = data_callback
        self.action_callback = action_callback
        self.item_kind = item_kind
        self.header_action_text = header_action_text
        self.secondary_header_action_text = secondary_header_action_text
        self.secondary_header_action_name = secondary_header_action_name

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.setup_ui()
        self.refresh_items()

    def setup_ui(self):
        """Setup generic ledger list UI."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text=self.title,
            font=ModernTheme.FONT_LARGE
        )
        title_label.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        next_column = 1
        if self.header_action_text and self.action_callback:
            action_button = ctk.CTkButton(
                header_frame,
                text=self.header_action_text,
                command=self.handle_header_action,
                width=140
            )
            action_button.grid(row=0, column=next_column, padx=(15, 5), pady=15, sticky="e")
            next_column += 1

        if self.secondary_header_action_text and self.action_callback:
            secondary_action_button = ctk.CTkButton(
                header_frame,
                text=self.secondary_header_action_text,
                command=self.handle_secondary_header_action,
                width=120
            )
            secondary_action_button.grid(row=0, column=next_column, padx=5, pady=15, sticky="e")
            next_column += 1

        refresh_button = ctk.CTkButton(
            header_frame,
            text="Refresh",
            command=self.refresh_items,
            width=100
        )
        refresh_button.grid(row=0, column=next_column, padx=15, pady=15, sticky="e")

        self.item_list = ctk.CTkScrollableFrame(self)
        self.item_list.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.item_list.grid_columnconfigure(0, weight=1)

    def refresh_items(self):
        """Refresh list data from callback."""
        for widget in self.item_list.winfo_children():
            widget.destroy()

        items = []
        if self.data_callback:
            try:
                items = self.data_callback() or []
            except (AttributeError, TypeError, RuntimeError, ValueError) as exc:
                logger.error(f"Error loading {self.title}: {exc}")

        if not items:
            empty_label = ctk.CTkLabel(
                self.item_list,
                text=self.empty_text,
                font=ModernTheme.FONT_MEDIUM,
                text_color=ModernTheme.TEXT_SECONDARY
            )
            empty_label.grid(row=0, column=0, padx=15, pady=20, sticky="w")
            return

        for row_index, item in enumerate(items):
            self.add_item(row_index, item)

    def add_item(self, row_index: int, item: Dict[str, Any]):
        """Add one ledger item."""
        item_frame = ctk.CTkFrame(self.item_list)
        item_frame.grid(row=row_index, column=0, padx=5, pady=6, sticky="ew")
        item_frame.grid_columnconfigure(0, weight=1)

        title, subtitle, body = self.format_item(item)

        title_label = ctk.CTkLabel(
            item_frame,
            text=title,
            font=ModernTheme.FONT_MEDIUM
        )
        title_label.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        subtitle_label = ctk.CTkLabel(
            item_frame,
            text=subtitle,
            font=ModernTheme.FONT_SMALL,
            text_color=ModernTheme.TEXT_SECONDARY
        )
        subtitle_label.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")

        body_text = ctk.CTkTextbox(item_frame, height=90, font=ModernTheme.FONT_SMALL)
        body_text.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")
        body_text.insert("1.0", body)
        body_text.configure(state="disabled")

        if self.item_kind == "responses" and self.action_callback:
            button_frame = ctk.CTkFrame(item_frame)
            button_frame.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="e")

            outcome_buttons = [
                ("Interested", "interested", ModernTheme.SUCCESS_COLOR),
                ("Declined", "declined", ModernTheme.WARNING_COLOR),
                ("Unavailable", "unavailable", ModernTheme.TEXT_SECONDARY)
            ]
            for label, outcome_type, color in outcome_buttons:
                outcome_button = ctk.CTkButton(
                    button_frame,
                    text=label,
                    command=lambda current=item, selected=outcome_type: self.handle_item_action(
                        "record_outcome",
                        {
                            "volunteer_id": current.get("volunteer_id"),
                            "campaign_id": current.get("campaign_id"),
                            "response_id": current.get("id"),
                            "outcome_type": selected,
                            "notes": f"Outcome recorded from response {current.get('id')} in Response Inbox"
                        }
                    ),
                    width=110,
                    fg_color=color
                )
                outcome_button.pack(side="left", padx=5)
        elif self.item_kind == "followups" and self.action_callback:
            button_frame = ctk.CTkFrame(item_frame)
            button_frame.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="e")

            status = item.get("status", "due")
            if status == "due":
                approve_button = ctk.CTkButton(
                    button_frame,
                    text="Approve",
                    command=lambda item_id=item["id"]: self.handle_follow_up_action("approve", item_id),
                    width=100
                )
                approve_button.pack(side="left", padx=5)

            if status == "approved":
                confirm_button = ctk.CTkButton(
                    button_frame,
                    text="Confirm Sent",
                    command=lambda item_id=item["id"]: self.handle_follow_up_action("confirm_sent", item_id),
                    width=120
                )
                confirm_button.pack(side="left", padx=5)

            if status == "sent":
                complete_button = ctk.CTkButton(
                    button_frame,
                    text="Complete",
                    command=lambda item_id=item["id"]: self.handle_follow_up_action("complete", item_id),
                    width=100
                )
                complete_button.pack(side="left", padx=5)

            if status in {"sent", "completed"}:
                for label, outcome_type, color in [
                    ("Interested", "interested", ModernTheme.SUCCESS_COLOR),
                    ("Declined", "declined", ModernTheme.WARNING_COLOR),
                    ("Unavailable", "unavailable", ModernTheme.TEXT_SECONDARY)
                ]:
                    outcome_button = ctk.CTkButton(
                        button_frame,
                        text=label,
                        command=lambda current=item, selected=outcome_type: self.handle_item_action(
                            "record_outcome",
                            {
                                "follow_up_id": current.get("id"),
                                "volunteer_id": current.get("volunteer_id"),
                                "campaign_id": current.get("campaign_id"),
                                "outcome_type": selected,
                                "notes": f"Outcome recorded from follow-up {current.get('id')} in Follow-up Queue"
                            }
                        ),
                        width=110,
                        fg_color=color
                    )
                    outcome_button.pack(side="left", padx=5)

            if status not in {"completed", "cancelled"}:
                cancel_button = ctk.CTkButton(
                    button_frame,
                    text="Cancel",
                    command=lambda item_id=item["id"]: self.handle_follow_up_action("cancel", item_id),
                    width=100,
                    fg_color=ModernTheme.WARNING_COLOR
                )
                cancel_button.pack(side="left", padx=5)
        elif (
            self.item_kind == "send_attempts"
            and self.action_callback
            and item.get("status") != "sent"
            and item.get("message_draft_id") is not None
        ):
            button_frame = ctk.CTkFrame(item_frame)
            button_frame.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="e")

            confirm_button = ctk.CTkButton(
                button_frame,
                text="Confirm Sent",
                command=lambda draft_id=item["message_draft_id"]: self.handle_item_action(
                    "confirm_sent",
                    {"draft_id": draft_id}
                ),
                width=120
            )
            confirm_button.pack(side="left", padx=5)
        elif self.item_kind == "duplicates" and self.action_callback and item.get("status") != "confirmed":
            button_frame = ctk.CTkFrame(item_frame)
            button_frame.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="e")

            confirm_button = ctk.CTkButton(
                button_frame,
                text="Confirm Group",
                command=lambda current=item: self.handle_item_action(
                    "confirm",
                    {
                        "identity_id": current["id"],
                        "canonical_volunteer_id": current["canonical_volunteer_id"]
                    }
                ),
                width=130
            )
            confirm_button.pack(side="left", padx=5)
        elif (
            self.item_kind == "privacy"
            and self.action_callback
            and item.get("volunteer_id")
            and item.get("status") != "completed"
            and item.get("retention_status") not in {"archived", "redacted"}
        ):
            button_frame = ctk.CTkFrame(item_frame)
            button_frame.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="e")

            archive_button = ctk.CTkButton(
                button_frame,
                text="Archive",
                command=lambda volunteer_id=item["volunteer_id"]: self.handle_item_action(
                    "archive",
                    {"volunteer_id": volunteer_id}
                ),
                width=100
            )
            archive_button.pack(side="left", padx=5)

            redact_button = ctk.CTkButton(
                button_frame,
                text="Redact",
                command=lambda volunteer_id=item["volunteer_id"]: self.handle_item_action(
                    "redact",
                    {"volunteer_id": volunteer_id}
                ),
                width=100,
                fg_color=ModernTheme.WARNING_COLOR
            )
            redact_button.pack(side="left", padx=5)

    def handle_follow_up_action(self, action: str, follow_up_id: int):
        """Handle a follow-up queue action."""
        if self.action_callback:
            self.action_callback(action, {"follow_up_id": follow_up_id})
        self.refresh_items()

    def handle_header_action(self):
        """Handle a view-level action."""
        if self.action_callback:
            self.action_callback("header_action", {})
        self.refresh_items()

    def handle_secondary_header_action(self):
        """Handle a secondary view-level action."""
        if self.action_callback:
            self.action_callback(self.secondary_header_action_name, {})
        self.refresh_items()

    def handle_item_action(self, action: str, data: Dict[str, Any]):
        """Handle a record-level action."""
        if self.action_callback:
            self.action_callback(action, data)
        self.refresh_items()

    def format_item(self, item: Dict[str, Any]) -> tuple[str, str, str]:
        """Format one item for compact display."""
        if self.item_kind == "responses":
            title = item.get("volunteer_name") or item.get("volunteer_id") or "Unknown volunteer"
            subtitle = (
                f"{item.get('classification', 'unknown')} "
                f"({item.get('confidence', 0):.2f}) | "
                f"{item.get('campaign_name') or 'No campaign'} | "
                f"{item.get('received_at') or 'Unknown date'}"
            )
            body = item.get("raw_content") or ""
        elif self.item_kind == "followups":
            title = item.get("volunteer_name") or item.get("volunteer_id") or "Unknown volunteer"
            subtitle = (
                f"Due: {item.get('due_at') or 'unknown'} | "
                f"{item.get('campaign_name') or 'No campaign'} | "
                f"Status: {item.get('status', 'due')}"
            )
            body = item.get("suggested_message") or "No suggested message saved."
        elif self.item_kind == "audit":
            title = f"{item.get('action', 'event')} on {item.get('entity_type', 'entity')} #{item.get('entity_id', '')}"
            subtitle = (
                f"Actor: {item.get('actor', 'system')} | "
                f"Risk: {item.get('risk_level', 'low')} | "
                f"{item.get('created_at') or 'Unknown date'}"
            )
            body = "\n".join([
                f"Before: {item.get('before_state') or '{}'}",
                f"After: {item.get('after_state') or '{}'}"
            ])
        elif self.item_kind == "privacy":
            if item.get("action"):
                title = item.get("volunteer_name") or item.get("volunteer_id") or "Retention action"
                subtitle = (
                    f"{item.get('action', 'action')} | "
                    f"Status: {item.get('status', 'proposed')} | "
                    f"{item.get('created_at') or 'Unknown date'}"
                )
                body = "\n".join([
                    f"Reason: {item.get('reason') or 'No reason saved.'}",
                    f"Actor: {item.get('actor') or 'system'}",
                    f"Evidence: {item.get('evidence_json') or '{}'}"
                ])
            else:
                title = item.get("name") or item.get("volunteer_id") or "Unknown volunteer"
                subtitle = (
                    f"Updated: {item.get('updated_at') or 'unknown'} | "
                    f"{item.get('location') or 'Unknown location'}"
                )
                body = "\n".join([
                    f"Volunteer ID: {item.get('volunteer_id')}",
                    f"Retention status: {item.get('retention_status') or 'active'}",
                    f"Categories: {item.get('categories') or 'unknown'}",
                    f"Contacts: {item.get('contact_count', 0)}; responses: {item.get('response_count', 0)}",
                    f"Last contact: {item.get('last_contact_at') or 'never'}",
                    f"Last response: {item.get('last_response_at') or 'never'}"
                ])
        elif self.item_kind == "privacy_actions":
            title = item.get("volunteer_name") or item.get("volunteer_id") or "Retention action"
            subtitle = (
                f"{item.get('action', 'action')} | "
                f"Status: {item.get('status', 'proposed')} | "
                f"{item.get('created_at') or 'Unknown date'}"
            )
            body = "\n".join([
                f"Reason: {item.get('reason') or 'No reason saved.'}",
                f"Actor: {item.get('actor') or 'system'}",
                f"Evidence: {item.get('evidence_json') or '{}'}"
            ])
        elif self.item_kind == "matches":
            title = item.get("volunteer_name") or item.get("volunteer_id") or "Unknown volunteer"
            subtitle = (
                f"Score: {item.get('score', 0):.0f} | "
                f"Fit: {item.get('status', 'possible')} | "
                f"{item.get('campaign_name') or 'Campaign'}"
            )
            body = "\n".join([
                f"Location: {item.get('volunteer_location') or 'unknown'}",
                f"Categories: {item.get('volunteer_categories') or 'unknown'}",
                f"Skills: {item.get('volunteer_skills') or 'unknown'}",
                f"Reasons: {item.get('reasons_json') or '[]'}"
            ])
        elif self.item_kind == "send_attempts":
            title = item.get("volunteer_name") or item.get("volunteer_id") or "Unknown volunteer"
            subtitle = (
                f"Type: {item.get('attempt_type', 'message')} | "
                f"Status: {item.get('status', 'unknown')} | "
                f"{item.get('campaign_name') or 'Campaign'} | "
                f"Started: {item.get('started_at') or 'unknown'}"
            )
            body = "\n".join([
                f"Draft ID: {item.get('message_draft_id')}",
                f"Follow-up ID: {item.get('follow_up_id') or 'none'}",
                f"Finished: {item.get('finished_at') or 'not finished'}",
                f"Retry count: {item.get('retry_count', 0)}",
                f"Evidence: {item.get('delivery_evidence') or 'none'}",
                f"Error: {item.get('error_message') or 'none'}"
            ])
        elif self.item_kind == "searches":
            title = item.get("task_id") or f"Search #{item.get('id')}"
            subtitle = (
                f"Status: {item.get('status', 'unknown')} | "
                f"Results: {item.get('linked_result_count', item.get('result_count', 0))} | "
                f"Started: {item.get('started_at') or item.get('created_at') or 'unknown'}"
            )
            body = "\n".join([
                f"Criteria: {item.get('criteria_json') or '{}'}",
                f"Volunteer IDs: {item.get('volunteer_ids') or 'none'}",
                f"Finished: {item.get('finished_at') or 'not finished'}",
                f"Error: {item.get('error_message') or 'none'}"
            ])
        elif self.item_kind == "tasks":
            title = item.get("name") or item.get("task_id") or "Task"
            subtitle = (
                f"Status: {item.get('status', 'unknown')} | "
                f"Updated: {item.get('updated_at') or 'unknown'}"
            )
            body = "\n".join([
                f"Task ID: {item.get('task_id')}",
                f"Description: {item.get('description') or ''}",
                f"Started: {item.get('started_at') or 'not started'}",
                f"Completed: {item.get('completed_at') or 'not completed'}",
                f"Progress: {item.get('progress_json') or '{}'}",
                f"Error: {item.get('error_message') or 'none'}"
            ])
        elif self.item_kind == "duplicates":
            title = item.get("canonical_name") or item.get("canonical_volunteer_id") or "Duplicate group"
            subtitle = (
                f"Status: {item.get('status', 'proposed')} | "
                f"Canonical: {item.get('canonical_volunteer_id')}"
            )
            body = "\n".join([
                f"Volunteer IDs: {item.get('volunteer_ids') or ''}",
                f"Volunteer names: {item.get('volunteer_names') or ''}",
                f"Notes: {item.get('notes') or ''}"
            ])
        else:
            title = str(item.get("id", "Item"))
            subtitle = self.item_kind
            body = "\n".join(f"{key}: {value}" for key, value in item.items())

        return title, subtitle, body

class MainApplication(ctk.CTk):
    """Main application window with modern UI"""
    
    def __init__(self):
        super().__init__()
        
        self.title("NLvoorelkaar Outreach Tool - Enhanced")
        self.geometry("1200x840")
        self.minsize(1000, 700)
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup main application UI"""
        # Sidebar
        self.sidebar = ctk.CTkScrollableFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        
        # Logo/Title
        logo_label = ctk.CTkLabel(
            self.sidebar,
            text="NLvoorelkaar\nTool",
            font=ModernTheme.FONT_LARGE
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Candidate Intake", "intake"),
            ("Campaigns", "campaigns"),
            ("Volunteers", "volunteers"),
            ("Matches", "matches"),
            ("Duplicates", "duplicates"),
            ("Messages", "messages"),
            ("Send History", "sends"),
            ("Responses", "responses"),
            ("Follow-ups", "followups"),
            ("Searches", "searches"),
            ("Tasks", "tasks"),
            ("Audit", "audit"),
            ("Privacy", "privacy"),
            ("Operations", "operations")
        ]
        for i, (text, key) in enumerate(nav_items, 1):
            button = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=lambda k=key: self.show_view(k),
                width=160,
                height=36
            )
            button.grid(row=i, column=0, padx=20, pady=3)
            self.nav_buttons[key] = button
            
        # Status section
        status_frame = ctk.CTkFrame(self.sidebar)
        status_frame.grid(row=len(nav_items) + 2, column=0, padx=20, pady=20, sticky="ew")
        
        status_title = ctk.CTkLabel(
            status_frame,
            text="Status",
            font=ModernTheme.FONT_SMALL
        )
        status_title.pack(pady=(10, 5))
        
        self.connection_status = ctk.CTkLabel(
            status_frame,
            text="Not connected",
            text_color=ModernTheme.WARNING_COLOR,
            font=ModernTheme.FONT_SMALL
        )
        self.connection_status.pack(pady=5)
        
        # Main content area
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Status bar
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        # Initialize views
        self.views = {}
        self.current_view = None
        
        # Show dashboard by default
        self.show_view("dashboard")
        
    def show_view(self, view_name: str):
        """Show specified view"""
        # Hide current view
        if self.current_view:
            self.current_view.grid_remove()
            
        # Create view if it doesn't exist
        if view_name not in self.views:
            if view_name == "dashboard":
                self.views[view_name] = DashboardView(
                    self.content_frame,
                    data_callback=self.get_dashboard_data
                )
            elif view_name == "intake":
                self.views[view_name] = SearchWorkspaceView(
                    self.content_frame,
                    action_callback=self.handle_intake_action,
                    status_callback=self.get_operational_status,
                )
            elif view_name == "campaigns":
                self.views[view_name] = CampaignView(
                    self.content_frame,
                    campaign_callback=self.handle_campaign_action,
                    data_callback=self.get_campaign_data,
                    readiness_callback=self.get_campaign_readiness,
                    operating_summary_callback=self.get_campaign_operating_summary
                )
            elif view_name == "messages":
                self.views[view_name] = MessageReviewView(
                    self.content_frame,
                    data_callback=self.get_message_review_data,
                    action_callback=self.handle_message_action
                )
            elif view_name == "volunteers":
                self.views[view_name] = VolunteerDetailView(
                    self.content_frame,
                    data_callback=self.get_volunteer_data,
                    detail_callback=self.get_volunteer_detail_data
                )
            elif view_name == "matches":
                self.views[view_name] = LedgerListView(
                    self.content_frame,
                    title="Match Assessments",
                    empty_text="No volunteer matches have been assessed.",
                    data_callback=self.get_match_assessment_data,
                    item_kind="matches"
                )
            elif view_name == "duplicates":
                self.views[view_name] = LedgerListView(
                    self.content_frame,
                    title="Duplicate Review",
                    empty_text="No duplicate identity proposals have been recorded.",
                    data_callback=self.get_duplicate_identity_data,
                    action_callback=self.handle_duplicate_action,
                    item_kind="duplicates",
                    header_action_text="Find Duplicates"
                )
            elif view_name == "sends":
                self.views[view_name] = LedgerListView(
                    self.content_frame,
                    title="Send Attempt History",
                    empty_text="No send attempts have been recorded.",
                    data_callback=self.get_send_attempt_data,
                    action_callback=self.handle_send_attempt_action,
                    item_kind="send_attempts"
                )
            elif view_name == "responses":
                self.views[view_name] = LedgerListView(
                    self.content_frame,
                    title="Response Inbox",
                    empty_text="No volunteer responses have been recorded.",
                    data_callback=self.get_response_inbox_data,
                    action_callback=self.handle_response_action,
                    item_kind="responses",
                    header_action_text="Record Response"
                )
            elif view_name == "followups":
                self.views[view_name] = LedgerListView(
                    self.content_frame,
                    title="Follow-up Queue",
                    empty_text="No follow-ups are due or scheduled.",
                    data_callback=self.get_follow_up_data,
                    action_callback=self.handle_follow_up_action,
                    item_kind="followups"
                )
            elif view_name == "searches":
                self.views[view_name] = LedgerListView(
                    self.content_frame,
                    title="Search Sessions",
                    empty_text="No volunteer search sessions have been recorded.",
                    data_callback=self.get_search_session_data,
                    item_kind="searches"
                )
            elif view_name == "tasks":
                self.views[view_name] = LedgerListView(
                    self.content_frame,
                    title="Task Runs",
                    empty_text="No background task runs have been recorded.",
                    data_callback=self.get_task_run_data,
                    item_kind="tasks"
                )
            elif view_name == "audit":
                self.views[view_name] = LedgerListView(
                    self.content_frame,
                    title="Audit Log",
                    empty_text="No audit events have been recorded.",
                    data_callback=self.get_audit_log_data,
                    item_kind="audit"
                )
            elif view_name == "privacy":
                self.views[view_name] = LedgerListView(
                    self.content_frame,
                    title="Privacy Review",
                    empty_text="No stale volunteer records need retention review.",
                    data_callback=self.get_privacy_review_data,
                    action_callback=self.handle_privacy_action,
                    item_kind="privacy",
                    header_action_text="Record Proposals",
                    secondary_header_action_text="Export JSON",
                    secondary_header_action_name="export_json"
                )
            elif view_name == "operations":
                self.views[view_name] = OperationsView(
                    self.content_frame,
                    data_callback=self.get_operational_status,
                    action_callback=self.handle_operations_action,
                )
            else:
                raise ValueError(f"Unknown view: {view_name}")
                
        # Show selected view
        self.current_view = self.views[view_name]
        self.current_view.grid(row=0, column=0, sticky="nsew")
        
        # Update navigation button states
        for key, button in self.nav_buttons.items():
            if key == view_name:
                button.configure(fg_color=ModernTheme.PRIMARY_COLOR)
            else:
                button.configure(fg_color=ModernTheme.SECONDARY_COLOR)
                
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Return a truthful disconnected state when no controller adapter is installed."""
        return {
            'total_volunteers': 0,
            'total_contacts': 0,
            'response_rate': 0,
            'total_campaigns': 0,
            'recent_activity': ["No application controller is connected. Launch with python main.py."]
        }
        
    def handle_campaign_action(self, action: str, data: Dict[str, Any]):
        """Refuse actions when this base view is launched without the real controller."""
        raise RuntimeError("Campaign actions require the application controller. Launch with python main.py.")

    def handle_intake_action(self, action: str, data: Dict[str, Any]):
        raise RuntimeError("Candidate intake requires the application controller. Launch with python main.py.")

    def get_operational_status(self) -> Dict[str, Any]:
        return {"runtime": {}, "database": {}, "google_drive": {}, "controller_connected": False}

    def handle_operations_action(self, action: str, data: Dict[str, Any]):
        raise RuntimeError("Operational actions require the application controller. Launch with python main.py.")

    def get_campaign_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for campaign data."""
        return []

    def get_campaign_readiness(self, campaign_id: int) -> Dict[str, Any]:
        """Controller adapter for campaign readiness."""
        return {"ready": False, "status": "unknown", "issues": [], "next_actions": []}

    def get_campaign_operating_summary(self, campaign_id: int) -> Dict[str, Any]:
        """Controller adapter for campaign operating summary."""
        return {}

    def get_message_review_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for message review data."""
        return []

    def handle_message_action(self, action: str, data: Dict[str, Any]):
        raise RuntimeError("Message actions require the application controller")

    def handle_response_action(self, action: str, data: Dict[str, Any]):
        raise RuntimeError("Response actions require the application controller")

    def get_match_assessment_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for match assessment data."""
        return []

    def get_volunteer_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for volunteer data."""
        return []

    def get_volunteer_detail_data(self, volunteer_id: str) -> Optional[Dict[str, Any]]:
        """Controller adapter for volunteer detail data."""
        return None

    def get_send_attempt_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for send attempt data."""
        return []

    def handle_send_attempt_action(self, action: str, data: Dict[str, Any]):
        raise RuntimeError("Send-attempt actions require the application controller")

    def get_duplicate_identity_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for duplicate identity data."""
        return []

    def handle_duplicate_action(self, action: str, data: Dict[str, Any]):
        raise RuntimeError("Duplicate actions require the application controller")

    def get_response_inbox_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for response inbox data."""
        return []

    def get_follow_up_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for follow-up data."""
        return []

    def get_audit_log_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for audit log data."""
        return []

    def get_task_run_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for task run data."""
        return []

    def get_search_session_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for search session data."""
        return []

    def get_privacy_review_data(self) -> List[Dict[str, Any]]:
        """Controller adapter for privacy review data."""
        return []

    def handle_follow_up_action(self, action: str, data: Dict[str, Any]):
        raise RuntimeError("Follow-up actions require the application controller")

    def handle_privacy_action(self, action: str, data: Dict[str, Any]):
        raise RuntimeError("Privacy actions require the application controller")
            
    def show_progress_dialog(self, title: str, message: str) -> ProgressDialog:
        """Show progress dialog"""
        return ProgressDialog(self, title, message)
        
    def show_error(self, title: str, message: str):
        """Show error dialog"""
        messagebox.showerror(title, message)
        
    def show_success(self, title: str, message: str):
        """Show success dialog"""
        messagebox.showinfo(title, message)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()
