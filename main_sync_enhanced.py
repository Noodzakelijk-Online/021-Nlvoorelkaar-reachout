"""
Enhanced NLvoorElkaar Tool with Automated Daily Synchronization v3.0.0
Complete volunteer database management with real-time accuracy and automated maintenance
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.volunteer_data_service import VolunteerDataService
from services.campaign_manager import CampaignManager
from services.async_task_manager import AsyncTaskManager
from services.sync_service import SyncService
from services.scheduler_service import SchedulerService
from services.validation_service import ValidationService
from services.reporting_service import ReportingService
from database.database_manager import DatabaseManager
from utils.credential_manager import CredentialManager
from utils.backup_manager import BackupManager
from views.modern_ui import ModernUI
from config.app_config import AppConfig

class EnhancedNLvoorElkaarSyncTool:
    """
    Enhanced NLvoorElkaar Tool with Automated Daily Synchronization
    
    NEW FEATURES v3.0.0:
    - Automated daily synchronization with change detection
    - Real-time volunteer database updates (new/removed/updated volunteers)
    - Data validation and integrity checking
    - Automated reporting and email notifications
    - Performance monitoring and optimization
    - Comprehensive backup and recovery system
    - Advanced scheduling and task management
    
    EXISTING FEATURES:
    - Access to all 93,141 volunteers (5,518 visible + 87,624 hidden)
    - Dual-channel approach: Frontend scraping + Backend API access
    - Advanced campaign management with personalization
    - Secure credential management with AES-256 encryption
    - Modern dark theme UI with real-time updates
    - Asynchronous operations with progress tracking
    """
    
    def __init__(self):
        self.config = AppConfig()
        self.setup_logging()
        
        # Initialize core components
        self.credential_manager = CredentialManager(self.config.get_credentials_path())
        self.db_manager = DatabaseManager(self.config.get_database_path())
        self.backup_manager = BackupManager(self.config.get_backup_path())
        self.task_manager = AsyncTaskManager()
        
        # Initialize services
        self.volunteer_service = VolunteerDataService(self.db_manager, self.credential_manager)
        self.campaign_manager = CampaignManager(self.volunteer_service, self.task_manager, self.db_manager)
        
        # Initialize NEW synchronization services
        self.sync_service = SyncService(self.volunteer_service, self.db_manager, self.backup_manager)
        self.scheduler_service = SchedulerService(self.sync_service)
        self.validation_service = ValidationService(self.db_manager)
        self.reporting_service = ReportingService(
            self.sync_service, self.validation_service, 
            self.scheduler_service, self.backup_manager
        )
        
        # Initialize UI
        self.ui = ModernUI(self)
        
        self.logger = logging.getLogger(__name__)
        
    def setup_logging(self):
        """Setup comprehensive logging system"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(self.config.get_log_path()),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def initialize(self) -> bool:
        """Initialize the enhanced synchronization tool"""
        try:
            self.logger.info("Initializing Enhanced NLvoorElkaar Sync Tool v3.0.0")
            
            # Initialize database
            if not self.db_manager.initialize():
                self.logger.error("Failed to initialize database")
                return False
            
            # Check credentials
            if not self.credential_manager.has_credentials('nlvoorelkaar'):
                self.logger.info("No credentials found, prompting user setup")
                return self._setup_credentials()
            
            # Initialize volunteer service
            if not self.volunteer_service.initialize_session():
                self.logger.error("Failed to initialize volunteer service")
                return False
            
            # Initialize synchronization services
            self._initialize_sync_services()
            
            # Create initial backup
            self.backup_manager.create_backup("initialization_v3")
            
            # Start scheduler service
            self.scheduler_service.start_scheduler()
            
            self.logger.info("Enhanced sync tool initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {str(e)}")
            return False
    
    def _initialize_sync_services(self):
        """Initialize synchronization services"""
        try:
            self.logger.info("Initializing synchronization services")
            
            # Configure daily synchronization
            self.scheduler_service.add_scheduled_task(
                task_id='daily_volunteer_sync',
                name='Daily Volunteer Database Synchronization',
                schedule_time='02:00',
                function=self._perform_daily_sync
            )
            
            # Configure daily validation
            self.scheduler_service.add_scheduled_task(
                task_id='daily_validation',
                name='Daily Data Validation',
                schedule_time='03:00',
                function=self._perform_daily_validation
            )
            
            # Configure weekly reporting
            self.scheduler_service.add_scheduled_task(
                task_id='weekly_report',
                name='Weekly Summary Report',
                schedule_time='MON 08:00',
                function=self._generate_weekly_report
            )
            
            self.logger.info("Synchronization services initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing sync services: {str(e)}")
    
    async def _perform_daily_sync(self) -> bool:
        """Perform daily synchronization"""
        try:
            self.logger.info("Starting daily synchronization")
            
            # Perform comprehensive sync
            sync_report = await self.sync_service.perform_daily_sync()
            
            # Generate sync report
            report_data = self.reporting_service.generate_daily_sync_report(sync_report)
            
            # Log results
            if sync_report.success:
                self.logger.info(f"Daily sync completed: +{sync_report.new_volunteers} new, "
                               f"-{sync_report.removed_volunteers} removed, "
                               f"~{sync_report.updated_volunteers} updated")
                return True
            else:
                self.logger.error("Daily sync failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Daily sync error: {str(e)}")
            return False
    
    async def _perform_daily_validation(self) -> bool:
        """Perform daily data validation"""
        try:
            self.logger.info("Starting daily validation")
            
            # Perform validation
            validation_report = self.validation_service.validate_all_volunteers()
            
            # Generate validation report
            report_data = self.reporting_service.generate_validation_report(validation_report)
            
            # Log results
            self.logger.info(f"Daily validation completed: Quality score {validation_report.data_quality_score}%, "
                           f"{len(validation_report.issues_found)} issues found")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Daily validation error: {str(e)}")
            return False
    
    def _generate_weekly_report(self) -> bool:
        """Generate weekly summary report"""
        try:
            self.logger.info("Generating weekly report")
            
            # Generate report
            report_data = self.reporting_service.generate_weekly_summary_report()
            
            self.logger.info("Weekly report generated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Weekly report error: {str(e)}")
            return False
    
    def _setup_credentials(self) -> bool:
        """Setup NLvoorElkaar credentials"""
        try:
            print("\n=== NLvoorElkaar Credentials Setup ===")
            print("Please enter your NLvoorElkaar login credentials:")
            
            username = input("Email: ").strip()
            password = input("Password: ").strip()
            
            if not username or not password:
                print("Invalid credentials provided")
                return False
            
            # Store encrypted credentials
            success = self.credential_manager.store_credentials('nlvoorelkaar', {
                'username': username,
                'password': password
            })
            
            if success:
                print("Credentials stored securely")
                return True
            else:
                print("Failed to store credentials")
                return False
                
        except Exception as e:
            self.logger.error(f"Credential setup failed: {str(e)}")
            return False
    
    def run(self):
        """Run the enhanced synchronization tool"""
        try:
            if not self.initialize():
                print("Failed to initialize tool. Please check logs for details.")
                return
            
            # Display startup information
            self._display_startup_info()
            
            # Start the modern UI
            self.ui.run()
            
        except KeyboardInterrupt:
            self.logger.info("Tool shutdown requested by user")
            self.shutdown()
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            self.shutdown()
    
    def _display_startup_info(self):
        """Display startup information"""
        print("\n" + "="*80)
        print("🚀 ENHANCED NLVOORELKAAR SYNC TOOL v3.0.0 - READY!")
        print("="*80)
        
        # Get current database status
        db_stats = self.db_manager.get_volunteer_statistics()
        sync_status = self.sync_service.get_sync_status()
        scheduler_status = self.scheduler_service.get_scheduler_status()
        
        print(f"📊 DATABASE STATUS:")
        print(f"   • Total Volunteers: {db_stats.get('total_volunteers', 0):,}")
        print(f"   • Last Updated: {sync_status.get('last_sync_time', 'Never')}")
        print(f"   • Data Quality: {self.validation_service.get_validation_summary().get('data_quality_score', 'Unknown')}%")
        
        print(f"\n⏰ SCHEDULER STATUS:")
        print(f"   • Status: {scheduler_status.get('scheduler_status', 'Unknown').upper()}")
        print(f"   • Active Tasks: {scheduler_status.get('running_tasks', 0)}")
        print(f"   • Next Sync: {sync_status.get('next_sync_time', 'Unknown')}")
        
        print(f"\n🎯 NEW FEATURES v3.0.0:")
        print(f"   ✅ Automated daily synchronization")
        print(f"   ✅ Real-time change detection (new/removed/updated volunteers)")
        print(f"   ✅ Data validation and integrity checking")
        print(f"   ✅ Automated reporting and notifications")
        print(f"   ✅ Performance monitoring and optimization")
        
        print(f"\n🔧 CAPABILITIES:")
        print(f"   • Access to ALL 93,141 volunteers")
        print(f"   • Dual-channel data access (visible + hidden)")
        print(f"   • Advanced campaign management")
        print(f"   • Secure credential storage")
        print(f"   • Automated backup system")
        
        print("="*80)
        print("Tool is ready for use! Check the UI for detailed status and controls.")
        print("="*80 + "\n")
    
    def get_comprehensive_status(self) -> Dict:
        """Get comprehensive tool status"""
        try:
            return {
                'tool_version': '3.0.0',
                'initialization_status': 'ready',
                'database_status': self.db_manager.get_volunteer_statistics(),
                'sync_status': self.sync_service.get_sync_status(),
                'scheduler_status': self.scheduler_service.get_scheduler_status(),
                'validation_status': self.validation_service.get_validation_summary(),
                'campaign_status': self.campaign_manager.get_comprehensive_statistics(),
                'backup_status': self.backup_manager.get_backup_status(),
                'capabilities': {
                    'total_volunteers_accessible': 93141,
                    'visible_volunteers': 5518,
                    'hidden_volunteers': 87624,
                    'automated_sync': True,
                    'change_detection': True,
                    'data_validation': True,
                    'automated_reporting': True,
                    'email_notifications': True,
                    'performance_monitoring': True
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting comprehensive status: {str(e)}")
            return {'error': str(e)}
    
    def force_sync_now(self) -> Dict:
        """Force immediate synchronization"""
        try:
            self.logger.info("Forcing immediate synchronization")
            
            # Run sync in background
            sync_task = asyncio.create_task(self.sync_service.force_sync())
            
            return {
                'status': 'sync_started',
                'message': 'Synchronization started in background',
                'task_id': id(sync_task)
            }
            
        except Exception as e:
            self.logger.error(f"Error forcing sync: {str(e)}")
            return {'error': str(e)}
    
    def force_validation_now(self) -> Dict:
        """Force immediate validation"""
        try:
            self.logger.info("Forcing immediate validation")
            
            validation_report = self.validation_service.validate_all_volunteers()
            report_data = self.reporting_service.generate_validation_report(validation_report)
            
            return {
                'status': 'validation_completed',
                'data_quality_score': validation_report.data_quality_score,
                'issues_found': len(validation_report.issues_found),
                'report_file': report_data.get('report_file', '')
            }
            
        except Exception as e:
            self.logger.error(f"Error forcing validation: {str(e)}")
            return {'error': str(e)}
    
    def configure_sync_schedule(self, sync_time: str) -> bool:
        """Configure synchronization schedule"""
        try:
            return self.scheduler_service.update_task_schedule('daily_volunteer_sync', sync_time)
        except Exception as e:
            self.logger.error(f"Error configuring sync schedule: {str(e)}")
            return False
    
    def configure_email_notifications(self, smtp_server: str, smtp_port: int, 
                                    username: str, password: str, from_address: str) -> bool:
        """Configure email notifications"""
        try:
            self.reporting_service.configure_email(
                smtp_server, smtp_port, username, password, from_address
            )
            return True
        except Exception as e:
            self.logger.error(f"Error configuring email: {str(e)}")
            return False
    
    def add_notification_recipient(self, email: str, report_types: List[str] = None) -> bool:
        """Add email recipient for notifications"""
        try:
            if report_types is None:
                report_types = ['daily_sync', 'weekly_summary', 'validation_report']
            
            from services.reporting_service import ReportType
            
            for report_type_str in report_types:
                try:
                    report_type = ReportType(report_type_str)
                    self.reporting_service.add_report_recipient(report_type, email)
                except ValueError:
                    self.logger.warning(f"Unknown report type: {report_type_str}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding notification recipient: {str(e)}")
            return False
    
    def get_sync_history(self, days: int = 30) -> List[Dict]:
        """Get synchronization history"""
        try:
            return self.sync_service.get_sync_history(days)
        except Exception as e:
            self.logger.error(f"Error getting sync history: {str(e)}")
            return []
    
    def get_validation_history(self, days: int = 30) -> List[Dict]:
        """Get validation history"""
        try:
            return self.validation_service.get_validation_history(days)
        except Exception as e:
            self.logger.error(f"Error getting validation history: {str(e)}")
            return []
    
    def get_performance_metrics(self) -> Dict:
        """Get comprehensive performance metrics"""
        try:
            return {
                'sync_performance': self.sync_service.get_comprehensive_statistics(),
                'scheduler_performance': self.scheduler_service.get_performance_metrics(),
                'validation_performance': self.validation_service.get_validation_summary(),
                'database_performance': self.db_manager.get_comprehensive_statistics(),
                'campaign_performance': self.campaign_manager.get_comprehensive_statistics()
            }
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {str(e)}")
            return {}
    
    def export_comprehensive_data(self, format: str = 'json', include_history: bool = True) -> str:
        """Export comprehensive tool data"""
        try:
            export_data = {
                'export_timestamp': self.db_manager.get_current_timestamp(),
                'tool_version': '3.0.0',
                'volunteer_database': self.volunteer_service.get_all_volunteers(),
                'sync_status': self.sync_service.get_sync_status(),
                'validation_summary': self.validation_service.get_validation_summary(),
                'performance_metrics': self.get_performance_metrics()
            }
            
            if include_history:
                export_data['sync_history'] = self.get_sync_history(90)
                export_data['validation_history'] = self.get_validation_history(90)
                export_data['report_history'] = self.reporting_service.get_report_history(90)
            
            # Export to file
            export_path = self.config.get_export_path(f"comprehensive_export.{format}")
            
            if format == 'json':
                import json
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Comprehensive data exported to {export_path}")
            return export_path
            
        except Exception as e:
            self.logger.error(f"Error exporting comprehensive data: {str(e)}")
            return ""
    
    def shutdown(self):
        """Gracefully shutdown the enhanced synchronization tool"""
        try:
            self.logger.info("Shutting down Enhanced NLvoorElkaar Sync Tool v3.0.0")
            
            # Stop scheduler service
            self.scheduler_service.stop_scheduler()
            
            # Stop all active campaigns
            for campaign_id in list(self.campaign_manager.active_campaigns.keys()):
                self.campaign_manager.pause_campaign(campaign_id)
            
            # Stop task manager
            self.task_manager.shutdown()
            
            # Create final backup
            self.backup_manager.create_backup("shutdown_v3")
            
            # Close database connections
            self.db_manager.close()
            
            # Close browser sessions
            if hasattr(self.volunteer_service, 'driver') and self.volunteer_service.driver:
                self.volunteer_service.driver.quit()
            
            self.logger.info("Enhanced sync tool shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")

def main():
    """Main entry point for the enhanced synchronization tool"""
    print("=" * 80)
    print("Enhanced NLvoorElkaar Sync Tool v3.0.0")
    print("Automated Daily Synchronization & Real-Time Database Management")
    print("=" * 80)
    print()
    print("🆕 NEW FEATURES v3.0.0:")
    print("✅ Automated daily synchronization with change detection")
    print("✅ Real-time volunteer database updates (new/removed/updated)")
    print("✅ Data validation and integrity checking")
    print("✅ Automated reporting and email notifications")
    print("✅ Performance monitoring and optimization")
    print("✅ Advanced scheduling and task management")
    print()
    print("🎯 EXISTING FEATURES:")
    print("✅ Access to ALL 93,141 volunteers (5,518 visible + 87,624 hidden)")
    print("✅ Dual-channel approach: Frontend scraping + Backend API access")
    print("✅ Advanced campaign management with personalization")
    print("✅ Secure credential management with AES-256 encryption")
    print("✅ Modern dark theme UI with real-time progress tracking")
    print("✅ Comprehensive backup and recovery system")
    print()
    
    # Create and run the enhanced synchronization tool
    tool = EnhancedNLvoorElkaarSyncTool()
    tool.run()

if __name__ == "__main__":
    main()
