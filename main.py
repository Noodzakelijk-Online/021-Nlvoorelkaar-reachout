"""
Enhanced NLvoorelkaar Outreach Tool
Main application integrating all enhanced features
"""

import sys
import os
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import enhanced components
from utils.credential_manager import CredentialManager
from utils.backup_manager import BackupManager
from database.database_manager import DatabaseManager
from models.data_models import Volunteer, Campaign, Contact, VolunteerFilter
from services.enhanced_scraper import EnhancedScraper, ScrapingConfig
from services.async_task_manager import AsyncTaskManager, TaskWrappers
from views.modern_ui import MainApplication, ProgressDialog
import customtkinter as ctk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nlvoorelkaar.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class EnhancedNLvoorelkaarApp:
    """Enhanced NLvoorelkaar application with all improvements"""
    
    def __init__(self):
        self.credential_manager = CredentialManager()
        self.backup_manager = BackupManager()
        self.database_manager = DatabaseManager()
        self.scraper = None
        self.task_manager = AsyncTaskManager(max_concurrent_tasks=2)
        self.ui = None
        self.logged_in = False
        
        # Setup task callbacks
        self.task_manager.add_progress_callback(self._on_task_progress)
        self.task_manager.add_completion_callback(self._on_task_completion)
        
        # Auto-backup on startup
        self._schedule_auto_backup()
        
    def start(self):
        """Start the application"""
        try:
            logger.info("Starting Enhanced NLvoorelkaar Tool")
            
            # Initialize UI
            self.ui = EnhancedMainApplication(self)
            
            # Check for existing credentials
            if self.credential_manager.credentials_exist():
                self.ui.show_login_dialog()
            else:
                self.ui.show_setup_dialog()
                
            # Start UI main loop
            self.ui.mainloop()
            
        except Exception as e:
            logger.error(f"Error starting application: {e}")
            raise
        finally:
            self.shutdown()
            
    def login(self, username: str, password: str, master_password: str) -> bool:
        """Login with credentials"""
        try:
            # Load credentials
            if self.credential_manager.credentials_exist():
                stored_creds = self.credential_manager.load_credentials(master_password)
                if not stored_creds:
                    return False
                username = stored_creds['username']
                password = stored_creds['password']
            else:
                # Save new credentials
                if not self.credential_manager.save_credentials(username, password, master_password):
                    return False
                    
            # Initialize scraper
            config = ScrapingConfig()
            self.scraper = EnhancedScraper(config)
            
            # Attempt login
            if self.scraper.login(username, password):
                self.logged_in = True
                logger.info("Login successful")
                
                # Update UI status
                if self.ui:
                    self.ui.set_connection_status("Connected", "success")
                    
                return True
            else:
                logger.error("Login failed")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
            
    def search_volunteers(self, search_params: Dict[str, Any]) -> str:
        """Start volunteer search task"""
        try:
            task_id = self.task_manager.add_task(
                name="Search Volunteers",
                function=TaskWrappers.scrape_volunteers,
                args=(self.scraper, search_params),
                description=f"Searching for volunteers in {search_params.get('location', 'all locations')}",
                callback=self._on_volunteers_found
            )
            
            logger.info(f"Started volunteer search task: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error starting volunteer search: {e}")
            raise
            
    def send_campaign_messages(self, campaign_id: int, volunteer_ids: List[str]) -> str:
        """Start campaign message sending task"""
        try:
            # Get campaign details
            campaigns = self.database_manager.get_campaigns()
            campaign = next((c for c in campaigns if c['id'] == campaign_id), None)
            
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
                
            # Get volunteers
            volunteers = []
            for volunteer_id in volunteer_ids:
                volunteer_data = self.database_manager.get_volunteers({'volunteer_id': volunteer_id})
                if volunteer_data:
                    volunteers.extend(volunteer_data)
                    
            if not volunteers:
                raise ValueError("No volunteers found")
                
            # Prepare message data
            message_data = {
                'volunteers': volunteers,
                'message_template': campaign['message_template'],
                'campaign_id': campaign_id
            }
            
            task_id = self.task_manager.add_task(
                name="Send Campaign Messages",
                function=TaskWrappers.send_messages,
                args=(self.scraper, message_data),
                description=f"Sending messages for campaign '{campaign['name']}'",
                callback=self._on_messages_sent
            )
            
            logger.info(f"Started message sending task: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error starting message sending: {e}")
            raise
            
    def create_campaign(self, campaign_data: Dict[str, Any]) -> int:
        """Create new campaign"""
        try:
            campaign_id = self.database_manager.add_campaign(campaign_data)
            logger.info(f"Created campaign: {campaign_data['name']} (ID: {campaign_id})")
            
            # Update UI
            if self.ui:
                self.ui.refresh_campaigns()
                
            return campaign_id
            
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            raise
            
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard"""
        try:
            stats = self.database_manager.get_statistics()
            
            # Add recent activity
            recent_contacts = self.database_manager.get_contacts()[:5]
            recent_activity = []
            
            for contact in recent_contacts:
                activity = f"Message sent to {contact.get('volunteer_name', 'volunteer')} "
                activity += f"for campaign {contact.get('campaign_name', 'Unknown')}"
                recent_activity.append(activity)
                
            stats['recent_activity'] = recent_activity
            return stats
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {}
            
    def backup_data(self, backup_name: str = None) -> str:
        """Start data backup task"""
        try:
            task_id = self.task_manager.add_task(
                name="Backup Data",
                function=TaskWrappers.backup_data,
                args=(self.backup_manager, backup_name),
                description="Creating data backup",
                callback=self._on_backup_completed
            )
            
            logger.info(f"Started backup task: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error starting backup: {e}")
            raise
            
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        task = self.task_manager.get_task(task_id)
        if task:
            return {
                'id': task.id,
                'name': task.name,
                'status': task.status.value,
                'progress': {
                    'current': task.progress.current,
                    'total': task.progress.total,
                    'percentage': task.progress.percentage,
                    'message': task.progress.message
                },
                'error': str(task.error) if task.error else None
            }
        return None
        
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        return self.task_manager.cancel_task(task_id)
        
    def _on_task_progress(self, task):
        """Handle task progress updates"""
        if self.ui:
            self.ui.update_task_progress(task)
            
    def _on_task_completion(self, task):
        """Handle task completion"""
        if self.ui:
            self.ui.on_task_completed(task)
            
    def _on_volunteers_found(self, task):
        """Handle volunteers found callback"""
        if task.result and task.status.value == "completed":
            volunteers = task.result
            
            # Save volunteers to database
            for volunteer_data in volunteers:
                volunteer = Volunteer.from_dict(volunteer_data)
                self.database_manager.add_volunteer(volunteer.to_dict())
                
            logger.info(f"Saved {len(volunteers)} volunteers to database")
            
            # Update UI
            if self.ui:
                self.ui.refresh_volunteers()
                self.ui.show_success(
                    "Search Complete",
                    f"Found and saved {len(volunteers)} volunteers"
                )
                
    def _on_messages_sent(self, task):
        """Handle messages sent callback"""
        if task.result and task.status.value == "completed":
            result = task.result
            
            logger.info(f"Message sending completed: {result}")
            
            # Update UI
            if self.ui:
                self.ui.show_success(
                    "Messages Sent",
                    f"Sent {result['sent_count']} messages successfully\\n"
                    f"Failed: {result['failed_count']}"
                )
                
    def _on_backup_completed(self, task):
        """Handle backup completion callback"""
        if task.result and task.status.value == "completed":
            backup_path = task.result
            logger.info(f"Backup completed: {backup_path}")
            
            # Update UI
            if self.ui:
                self.ui.show_success(
                    "Backup Complete",
                    f"Data backed up successfully to:\\n{backup_path}"
                )
                
    def _schedule_auto_backup(self):
        """Schedule automatic daily backup"""
        def auto_backup():
            try:
                self.backup_manager.auto_backup()
                logger.info("Auto backup completed")
            except Exception as e:
                logger.error(f"Auto backup failed: {e}")
                
        # Schedule backup in a separate thread
        backup_thread = threading.Timer(3600, auto_backup)  # 1 hour delay
        backup_thread.daemon = True
        backup_thread.start()
        
    def shutdown(self):
        """Shutdown the application"""
        try:
            logger.info("Shutting down application")
            
            # Shutdown task manager
            self.task_manager.shutdown()
            
            # Close database connections
            # (SQLite connections are automatically closed)
            
            logger.info("Application shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

class EnhancedMainApplication(MainApplication):
    """Enhanced main application with integrated functionality"""
    
    def __init__(self, app_controller: EnhancedNLvoorelkaarApp):
        self.app_controller = app_controller
        super().__init__()
        
        # Override data callback
        if 'dashboard' in self.views:
            self.views['dashboard'].data_callback = self.app_controller.get_dashboard_data
            
    def show_login_dialog(self):
        """Show login dialog"""
        dialog = LoginDialog(self)
        if dialog.result:
            username, password, master_password = dialog.result
            if self.app_controller.login(username, password, master_password):
                self.set_connection_status("Connected", "success")
            else:
                self.show_error("Login Failed", "Invalid credentials or connection error")
                
    def show_setup_dialog(self):
        """Show initial setup dialog"""
        dialog = SetupDialog(self)
        if dialog.result:
            username, password, master_password = dialog.result
            if self.app_controller.login(username, password, master_password):
                self.set_connection_status("Connected", "success")
            else:
                self.show_error("Setup Failed", "Could not connect with provided credentials")
                
    def set_connection_status(self, status: str, status_type: str):
        """Set connection status"""
        self.connection_status.configure(
            text=f"● {status}",
            text_color=self.get_status_color(status_type)
        )
        
    def get_status_color(self, status_type: str) -> str:
        """Get color for status type"""
        colors = {
            "success": "#2d5a27",
            "warning": "#8b6914",
            "error": "#8b1538",
            "info": "#b0b0b0"
        }
        return colors.get(status_type, "#b0b0b0")
        
    def refresh_volunteers(self):
        """Refresh volunteers view"""
        # Implementation would update volunteers view
        pass
        
    def refresh_campaigns(self):
        """Refresh campaigns view"""
        if 'campaigns' in self.views:
            self.views['campaigns'].refresh_campaigns()
            
    def update_task_progress(self, task):
        """Update task progress in UI"""
        # Implementation would update progress indicators
        pass
        
    def on_task_completed(self, task):
        """Handle task completion in UI"""
        # Implementation would update UI state
        pass

class LoginDialog(ctk.CTkToplevel):
    """Login dialog for existing users"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Login - NLvoorelkaar Tool")
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup login UI"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Login to NLvoorelkaar",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=(20, 30))
        
        # Master password
        password_label = ctk.CTkLabel(main_frame, text="Master Password:")
        password_label.pack(pady=(10, 5))
        
        self.password_entry = ctk.CTkEntry(main_frame, show="*", width=300)
        self.password_entry.pack(pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=30)
        
        login_button = ctk.CTkButton(
            button_frame,
            text="Login",
            command=self.login,
            width=100
        )
        login_button.pack(side="left", padx=5)
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.cancel,
            width=100
        )
        cancel_button.pack(side="left", padx=5)
        
    def login(self):
        """Handle login"""
        master_password = self.password_entry.get()
        if master_password:
            self.result = (None, None, master_password)  # Username/password loaded from storage
            self.destroy()
            
    def cancel(self):
        """Cancel login"""
        self.result = None
        self.destroy()

class SetupDialog(ctk.CTkToplevel):
    """Setup dialog for new users"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Setup - NLvoorelkaar Tool")
        self.geometry("450x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup dialog UI"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Setup NLvoorelkaar Tool",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=(20, 30))
        
        # Username
        username_label = ctk.CTkLabel(main_frame, text="NLvoorelkaar Username:")
        username_label.pack(pady=(10, 5))
        
        self.username_entry = ctk.CTkEntry(main_frame, width=300)
        self.username_entry.pack(pady=5)
        
        # Password
        password_label = ctk.CTkLabel(main_frame, text="NLvoorelkaar Password:")
        password_label.pack(pady=(10, 5))
        
        self.password_entry = ctk.CTkEntry(main_frame, show="*", width=300)
        self.password_entry.pack(pady=5)
        
        # Master password
        master_label = ctk.CTkLabel(main_frame, text="Master Password (for encryption):")
        master_label.pack(pady=(10, 5))
        
        self.master_entry = ctk.CTkEntry(main_frame, show="*", width=300)
        self.master_entry.pack(pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=30)
        
        setup_button = ctk.CTkButton(
            button_frame,
            text="Setup",
            command=self.setup,
            width=100
        )
        setup_button.pack(side="left", padx=5)
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.cancel,
            width=100
        )
        cancel_button.pack(side="left", padx=5)
        
    def setup(self):
        """Handle setup"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        master_password = self.master_entry.get()
        
        if username and password and master_password:
            self.result = (username, password, master_password)
            self.destroy()
            
    def cancel(self):
        """Cancel setup"""
        self.result = None
        self.destroy()

def main():
    """Main entry point"""
    try:
        app = EnhancedNLvoorelkaarApp()
        app.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()

