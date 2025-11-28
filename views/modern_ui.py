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
            except Exception as e:
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
        
    def update_activity(self, activities: List[str]):
        """Update recent activity"""
        self.activity_text.delete("1.0", "end")
        
        if activities:
            for activity in activities[-10:]:  # Show last 10 activities
                self.activity_text.insert("end", f"• {activity}\n")
        else:
            self.activity_text.insert("end", "No recent activity")

class CampaignView(ctk.CTkFrame):
    """Modern campaign management view"""
    
    def __init__(self, parent, campaign_callback: Callable = None):
        super().__init__(parent)
        self.campaign_callback = campaign_callback
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.setup_ui()
        
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
        
        new_campaign_button = ctk.CTkButton(
            header_frame,
            text="+ New Campaign",
            command=self.create_new_campaign,
            width=150
        )
        new_campaign_button.grid(row=0, column=1, padx=15, pady=15, sticky="e")
        
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
        self.details_text.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        
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
            
        # Add campaigns (placeholder)
        campaigns = [
            {"name": "Summer Volunteers", "status": "Active", "contacts": 45},
            {"name": "Event Helpers", "status": "Paused", "contacts": 23},
            {"name": "Regular Support", "status": "Active", "contacts": 67}
        ]
        
        for campaign in campaigns:
            self.add_campaign_item(campaign)
            
    def add_campaign_item(self, campaign: Dict[str, Any]):
        """Add campaign item to list"""
        item_frame = ctk.CTkFrame(self.campaign_list)
        item_frame.pack(fill="x", padx=5, pady=5)
        item_frame.grid_columnconfigure(1, weight=1)
        
        # Campaign name
        name_label = ctk.CTkLabel(
            item_frame,
            text=campaign["name"],
            font=ModernTheme.FONT_MEDIUM
        )
        name_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Status
        status_color = ModernTheme.SUCCESS_COLOR if campaign["status"] == "Active" else ModernTheme.WARNING_COLOR
        status_label = ctk.CTkLabel(
            item_frame,
            text=campaign["status"],
            font=ModernTheme.FONT_SMALL,
            text_color=status_color
        )
        status_label.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        # Contacts count
        contacts_label = ctk.CTkLabel(
            item_frame,
            text=f"{campaign['contacts']} contacts",
            font=ModernTheme.FONT_SMALL,
            text_color=ModernTheme.TEXT_SECONDARY
        )
        contacts_label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")

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

class MainApplication(ctk.CTk):
    """Main application window with modern UI"""
    
    def __init__(self):
        super().__init__()
        
        self.title("NLvoorelkaar Outreach Tool - Enhanced")
        self.geometry("1200x800")
        self.minsize(1000, 600)
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup main application UI"""
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
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
            ("Campaigns", "campaigns"),
            ("Volunteers", "volunteers"),
            ("Messages", "messages"),
            ("Settings", "settings")
        ]
        
        for i, (text, key) in enumerate(nav_items, 1):
            button = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=lambda k=key: self.show_view(k),
                width=160,
                height=40
            )
            button.grid(row=i, column=0, padx=20, pady=5)
            self.nav_buttons[key] = button
            
        # Status section
        status_frame = ctk.CTkFrame(self.sidebar)
        status_frame.grid(row=7, column=0, padx=20, pady=20, sticky="ew")
        
        status_title = ctk.CTkLabel(
            status_frame,
            text="Status",
            font=ModernTheme.FONT_SMALL
        )
        status_title.pack(pady=(10, 5))
        
        self.connection_status = ctk.CTkLabel(
            status_frame,
            text="● Connected",
            text_color=ModernTheme.SUCCESS_COLOR,
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
            elif view_name == "campaigns":
                self.views[view_name] = CampaignView(
                    self.content_frame,
                    campaign_callback=self.handle_campaign_action
                )
            else:
                # Placeholder for other views
                self.views[view_name] = ctk.CTkLabel(
                    self.content_frame,
                    text=f"{view_name.title()} View\n(Coming Soon)",
                    font=ModernTheme.FONT_LARGE
                )
                
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
        """Get data for dashboard (placeholder)"""
        return {
            'total_volunteers': 1234,
            'total_contacts': 567,
            'response_rate': 23.5,
            'total_campaigns': 8,
            'recent_activity': [
                f"{datetime.now().strftime('%H:%M')} - Campaign 'Summer Volunteers' started",
                f"{datetime.now().strftime('%H:%M')} - 15 new volunteers discovered",
                f"{datetime.now().strftime('%H:%M')} - Message sent to volunteer #1234"
            ]
        }
        
    def handle_campaign_action(self, action: str, data: Dict[str, Any]):
        """Handle campaign actions"""
        if action == "create":
            logger.info(f"Creating campaign: {data['name']}")
            self.status_bar.set_status(f"Campaign '{data['name']}' created", "success")
            
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

