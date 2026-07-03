"""
Enhanced NLvoorelkaar Outreach Tool
Main application integrating all enhanced features
"""

import sys
import os
import logging
import sqlite3
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
from services.outreach_ledger import OutreachLedger
from views.modern_ui import MainApplication, ProgressDialog, ResponseDialog
import customtkinter as ctk

# Configure logging
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(APP_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'nlvoorelkaar.log'), encoding='utf-8'),
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
        self.outreach_ledger = OutreachLedger(self.database_manager)
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
            
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Error starting application: %s", type(e).__name__)
            raise
        finally:
            self.shutdown()
            
    def _audit_credential_event(
        self,
        action: str,
        *,
        actor: str = "user",
        source: Optional[str] = None,
        success: Optional[bool] = None,
        error: Optional[BaseException] = None,
        risk_level: str = "medium"
    ) -> Optional[int]:
        """Record credential/session lifecycle events without storing secrets."""
        db = getattr(self, "database_manager", None)
        if not db or not hasattr(db, "record_audit_event"):
            return None

        state: Dict[str, Any] = {}
        if source:
            state["source"] = source
        if success is not None:
            state["success"] = bool(success)
        if error is not None:
            state["error_type"] = type(error).__name__

        try:
            return db.record_audit_event(
                "credentials",
                "nlvoorelkaar",
                action,
                actor=actor,
                after_state=state or None,
                risk_level=risk_level
            )
        except (AttributeError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as audit_error:
            logger.warning("Could not record credential audit event: %s", type(audit_error).__name__)
            return None

    def login(self, username: str, password: str, master_password: str) -> bool:
        """Login with credentials and record non-secret credential/session audit events."""
        credential_source = "stored_credentials" if self.credential_manager.credentials_exist() else "setup_dialog"
        try:
            # Load credentials
            if credential_source == "stored_credentials":
                self._audit_credential_event("credentials_load_requested", source=credential_source)
                stored_creds = self.credential_manager.load_credentials(master_password)
                if not stored_creds:
                    self._audit_credential_event(
                        "credentials_load_failed",
                        source=credential_source,
                        success=False,
                        risk_level="high"
                    )
                    return False
                username = stored_creds['username']
                password = stored_creds['password']
                self._audit_credential_event(
                    "credentials_loaded",
                    source=credential_source,
                    success=True
                )
            else:
                # Save new credentials
                if not self.credential_manager.save_credentials(username, password, master_password):
                    self._audit_credential_event(
                        "credentials_store_failed",
                        source=credential_source,
                        success=False,
                        risk_level="high"
                    )
                    return False
                self._audit_credential_event(
                    "credentials_stored",
                    source=credential_source,
                    success=True,
                    risk_level="high"
                )
                    
            # Initialize scraper
            config = ScrapingConfig()
            self.scraper = EnhancedScraper(config)
            
            # Attempt login
            if self.scraper.login(username, password):
                self.logged_in = True
                logger.info("Login successful")
                self._audit_credential_event(
                    "login_success",
                    source=credential_source,
                    success=True
                )
                
                # Update UI status
                if self.ui:
                    self.ui.set_connection_status("Connected", "success")
                    
                return True
            else:
                logger.error("Login failed")
                self._audit_credential_event(
                    "login_failed",
                    source=credential_source,
                    success=False,
                    risk_level="high"
                )
                return False
                
        except (AttributeError, RuntimeError, TypeError, ValueError, OSError, sqlite3.DatabaseError) as e:
            logger.error("Login error: %s", type(e).__name__)
            self._audit_credential_event(
                "login_error",
                source=credential_source,
                success=False,
                error=e,
                risk_level="high"
            )
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
            self.database_manager.record_search_session(search_params, task_id=task_id, status="started")
            
            logger.info(f"Started volunteer search task: {task_id}")
            return task_id
            
        except (AttributeError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Error starting volunteer search: %s", type(e).__name__)
            raise
            
    def send_campaign_messages(self, campaign_id: int, volunteer_ids: List[str]) -> str:
        """Start approved campaign message sending task"""
        try:
            approved_drafts = self.outreach_ledger.get_approved_drafts(campaign_id, volunteer_ids)
            if not approved_drafts:
                raise ValueError(
                    "No approved message drafts found. Create drafts and approve them before sending."
                )
            
            task_id = self.task_manager.add_task(
                name="Send Approved Campaign Messages",
                function=self.outreach_ledger.send_approved_drafts,
                args=(self.scraper, [draft['id'] for draft in approved_drafts]),
                description=f"Sending {len(approved_drafts)} approved message(s)",
                callback=self._on_messages_sent
            )
            
            logger.info(f"Started message sending task: {task_id}")
            return task_id
            
        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Error starting message sending: %s", type(e).__name__)
            raise
            
    def create_campaign(self, campaign_data: Dict[str, Any]) -> int:
        """Create new campaign"""
        try:
            campaign_id = self.database_manager.add_campaign(campaign_data)
            logger.info("Created campaign ID %s", campaign_id)
            
            # Update UI
            if self.ui:
                self.ui.refresh_campaigns()
                
            return campaign_id
            
        except (AttributeError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Error creating campaign: %s", type(e).__name__)
            raise

    def create_campaign_message_drafts(self, campaign_id: int, volunteer_ids: Optional[List[str]] = None) -> List[int]:
        """Create reviewable message drafts for a campaign."""
        draft_ids = self.outreach_ledger.create_message_drafts(campaign_id, volunteer_ids)
        logger.info(f"Created {len(draft_ids)} message draft(s) for campaign {campaign_id}")
        if self.ui:
            self.ui.refresh_messages()
            self.ui.refresh_campaigns()
            self.ui.refresh_dashboard()
        return draft_ids

    def approve_message_draft(self, draft_id: int, reason: str = "") -> int:
        """Approve a draft for explicit sending."""
        approval_id = self.outreach_ledger.approve_message(draft_id, reason, actor="user")
        if self.ui:
            self.ui.refresh_messages()
            self.ui.refresh_dashboard()
        return approval_id

    def edit_message_draft(
        self,
        draft_id: int,
        subject: Optional[str] = None,
        body: Optional[str] = None
    ) -> bool:
        """Edit a message draft before approval."""
        updated = self.outreach_ledger.edit_message_draft(draft_id, subject=subject, body=body)
        if self.ui:
            self.ui.refresh_messages()
            self.ui.refresh_dashboard()
        return updated

    def reject_message_draft(self, draft_id: int, reason: str = "") -> int:
        """Reject a draft so it cannot be sent."""
        approval_id = self.outreach_ledger.reject_message(draft_id, reason, actor="user")
        if self.ui:
            self.ui.refresh_messages()
            self.ui.refresh_dashboard()
        return approval_id

    def get_message_review_queue(self) -> List[Dict[str, Any]]:
        """Get drafts waiting for review."""
        return self.outreach_ledger.get_review_queue()

    def get_campaign_readiness(self, campaign_id: int) -> Dict[str, Any]:
        """Get campaign readiness status."""
        return self.outreach_ledger.check_campaign_readiness(campaign_id)

    def get_campaign_operating_summary(self, campaign_id: int) -> Dict[str, Any]:
        """Get campaign-level operating ledger status."""
        return self.outreach_ledger.get_campaign_operating_summary(campaign_id)

    def get_campaigns(self) -> List[Dict[str, Any]]:
        """Get saved campaigns for the campaign view."""
        return self.database_manager.get_campaigns()

    def assess_campaign_matches(self, campaign_id: int) -> List[Dict[str, Any]]:
        """Assess volunteer matches for a campaign."""
        return self.outreach_ledger.assess_campaign_matches(campaign_id)

    def get_match_assessments(self) -> List[Dict[str, Any]]:
        """Get recent match assessments."""
        return self.outreach_ledger.get_match_assessments(limit=100)

    def get_volunteers(self) -> List[Dict[str, Any]]:
        """Get volunteers for review."""
        return self.outreach_ledger.get_volunteers()

    def get_volunteer_operating_profile(self, volunteer_id: str) -> Optional[Dict[str, Any]]:
        """Get one volunteer with operating ledger context."""
        return self.outreach_ledger.get_volunteer_operating_profile(volunteer_id)

    def get_send_attempt_history(self) -> List[Dict[str, Any]]:
        """Get send attempt history."""
        return self.outreach_ledger.get_send_attempt_history()

    def confirm_manual_send(self, draft_id: int, delivery_evidence: str) -> int:
        """Record manual evidence that an approved draft was sent."""
        return self.outreach_ledger.confirm_manual_send(draft_id, delivery_evidence, actor="user")

    def propose_duplicate_identities(self) -> List[int]:
        """Record duplicate identity proposals for review."""
        return self.outreach_ledger.propose_duplicate_identities()

    def get_duplicate_identity_proposals(self) -> List[Dict[str, Any]]:
        """Get duplicate identity proposals and confirmations."""
        return self.outreach_ledger.get_duplicate_identity_proposals()

    def confirm_duplicate_identity(self, identity_id: int, canonical_volunteer_id: str) -> bool:
        """Confirm a duplicate identity proposal."""
        return self.outreach_ledger.confirm_duplicate_identity(
            identity_id,
            canonical_volunteer_id,
            actor="user"
        )

    def get_response_inbox(self) -> List[Dict[str, Any]]:
        """Get recorded volunteer responses."""
        return self.outreach_ledger.get_response_inbox()

    def record_volunteer_response(
        self,
        volunteer_id: str,
        campaign_id: Optional[int],
        raw_content: str,
        source: str = "manual"
    ) -> int:
        """Record a manually entered volunteer response."""
        response_id = self.outreach_ledger.record_response(
            volunteer_id=volunteer_id,
            campaign_id=campaign_id,
            raw_content=raw_content,
            source=source
        )
        if self.ui:
            self.ui.refresh_ledger_view("responses")
            self.ui.refresh_ledger_view("followups")
            self.ui.refresh_campaigns()
            self.ui.refresh_dashboard()
        return response_id

    def record_outreach_outcome(
        self,
        volunteer_id: str,
        campaign_id: Optional[int],
        outcome_type: str,
        notes: str = "",
        response_id: Optional[int] = None,
        follow_up_id: Optional[int] = None
    ) -> int:
        """Record a reviewed outreach outcome."""
        outcome_id = self.outreach_ledger.record_outreach_outcome(
            volunteer_id=volunteer_id,
            campaign_id=campaign_id,
            outcome_type=outcome_type,
            notes=notes,
            response_id=response_id,
            follow_up_id=follow_up_id,
            actor="user"
        )
        if self.ui:
            self.ui.refresh_campaigns()
            self.ui.refresh_dashboard()
        return outcome_id

    def get_follow_up_queue(self) -> List[Dict[str, Any]]:
        """Get follow-ups that need operator attention."""
        return self.outreach_ledger.get_follow_up_queue(status=None, include_future=True)

    def complete_follow_up(self, follow_up_id: int) -> bool:
        """Mark a follow-up complete."""
        return self.outreach_ledger.complete_follow_up(follow_up_id, actor="user")

    def approve_follow_up(self, follow_up_id: int, message_snapshot: Optional[str] = None) -> bool:
        """Approve a follow-up message before it can be confirmed sent."""
        return self.outreach_ledger.approve_follow_up(
            follow_up_id,
            message_snapshot=message_snapshot,
            actor="user"
        )

    def confirm_follow_up_sent(self, follow_up_id: int, delivery_evidence: str) -> int:
        """Record manual send evidence for an approved follow-up."""
        return self.outreach_ledger.confirm_follow_up_sent(
            follow_up_id,
            delivery_evidence,
            actor="user"
        )

    def cancel_follow_up(self, follow_up_id: int) -> bool:
        """Cancel a follow-up."""
        return self.outreach_ledger.cancel_follow_up(follow_up_id, actor="user")

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get recent audit events."""
        return self.outreach_ledger.get_audit_log()

    def get_privacy_retention_candidates(self) -> List[Dict[str, Any]]:
        """Get stale volunteer records for privacy review."""
        return self.outreach_ledger.get_privacy_retention_candidates()

    def get_privacy_retention_records(self) -> List[Dict[str, Any]]:
        """Get proposed and completed retention actions."""
        return self.outreach_ledger.get_privacy_retention_records()

    def propose_privacy_retention_actions(self) -> bool:
        """Record proposed retention actions without deleting data."""
        return self.outreach_ledger.propose_retention_actions(actor="user")

    def archive_volunteer_for_retention(self, volunteer_id: str, reason: str) -> bool:
        """Archive stale volunteer data while preserving ledger history."""
        return self.outreach_ledger.archive_volunteer_for_retention(
            volunteer_id,
            reason,
            actor="user"
        )

    def redact_volunteer_personal_data(self, volunteer_id: str, reason: str) -> bool:
        """Redact personal volunteer fields while preserving ledger history."""
        return self.outreach_ledger.redact_volunteer_personal_data(
            volunteer_id,
            reason,
            actor="user"
        )

    def export_volunteer_data(self, export_format: str = "json") -> Dict[str, Any]:
        """Export non-redacted volunteer data to a local audited file."""
        export_dir = os.path.join(os.path.dirname(self.database_manager.db_path), "exports")
        os.makedirs(export_dir, mode=0o700, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(export_dir, f"volunteers_{timestamp}.{export_format}")
        return self.outreach_ledger.export_volunteer_data(
            output_path,
            export_format=export_format,
            actor="user"
        )

    def get_task_runs(self) -> List[Dict[str, Any]]:
        """Get durable background task history."""
        return self.outreach_ledger.get_task_runs()

    def get_search_sessions(self) -> List[Dict[str, Any]]:
        """Get recent search sessions with captured result membership."""
        return self.outreach_ledger.get_search_sessions()
            
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard"""
        try:
            stats = self.database_manager.get_statistics()
            stats.update(self.database_manager.get_operating_statistics())
            
            # Add recent activity
            recent_contacts = self.database_manager.get_contacts()[:5]
            recent_activity = []
            
            for contact in recent_contacts:
                activity = f"Message sent to {contact.get('volunteer_name', 'volunteer')} "
                activity += f"for campaign {contact.get('campaign_name', 'Unknown')}"
                recent_activity.append(activity)
                
            stats['recent_activity'] = recent_activity
            return stats
            
        except (AttributeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Error getting dashboard data: %s", type(e).__name__)
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
            
        except (OSError, AttributeError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Error starting backup: %s", type(e).__name__)
            raise

    def restore_backup(self, backup_path: str, actor: str = "user") -> bool:
        """Restore a local backup with explicit audit logging."""
        try:
            metadata = self.backup_manager.read_backup_metadata(backup_path)
            self.database_manager.record_audit_event(
                "backup",
                backup_path,
                "restore_requested",
                actor=actor,
                after_state={
                    "backup_path": backup_path,
                    "backup_date": metadata.get("backup_date"),
                    "included_files": len(metadata.get("included_files", [])),
                    "excluded_files": len(metadata.get("excluded_files", []))
                },
                risk_level="high"
            )
            restored = self.backup_manager.restore_backup(backup_path)
            self.database_manager.record_audit_event(
                "backup",
                backup_path,
                "restore_completed" if restored else "restore_failed",
                actor=actor,
                after_state={"backup_path": backup_path, "restored": restored},
                risk_level="high"
            )
            return restored
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Error restoring backup: %s", type(e).__name__)
            self.database_manager.record_audit_event(
                "backup",
                backup_path,
                "restore_failed",
                actor=actor,
                after_state={"backup_path": backup_path, "error_type": type(e).__name__},
                risk_level="high"
            )
            return False
            
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
                'error': type(task.error).__name__ if task.error else None
            }
        return None
        
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        return self.task_manager.cancel_task(task_id)
        
    def _on_task_progress(self, task):
        """Handle task progress updates"""
        self._record_task_state(task)
        if self.ui:
            self.ui.update_task_progress(task)
            
    def _on_task_completion(self, task):
        """Handle task completion"""
        self._record_task_state(task)
        if task.name == "Search Volunteers":
            result_count = len(task.result or []) if task.result else 0
            self.database_manager.finish_search_session(
                task.id,
                task.status.value,
                result_count=result_count,
                error_message=type(task.error).__name__ if task.error else None
            )
        if self.ui:
            self.ui.on_task_completed(task)
            
    def _on_volunteers_found(self, task):
        """Handle volunteers found callback"""
        if task.result and task.status.value == "completed":
            volunteers = task.result
            
            # Save volunteers to database
            saved_volunteers = []
            for volunteer_data in volunteers:
                volunteer = Volunteer.from_dict(volunteer_data)
                volunteer_dict = volunteer.to_dict()
                self.database_manager.add_volunteer(volunteer_dict)
                saved_volunteers.append(volunteer_dict)

            self.database_manager.record_search_session_results(task.id, saved_volunteers)
            logger.info(f"Saved {len(volunteers)} volunteers to database")
            
            # Update UI
            if self.ui:
                self.ui.refresh_volunteers()
                self.ui.refresh_dashboard()
                self.ui.show_success(
                    "Search Complete",
                    f"Found and saved {len(volunteers)} volunteers"
                )
                
    def _on_messages_sent(self, task):
        """Handle messages sent callback"""
        if not task.result or task.status.value != "completed":
            return

        result = task.result
        logger.info(f"Message sending completed: {result}")

        if self.ui:
            self.ui.refresh_dashboard()
            self.ui.refresh_campaigns()
            self.ui.refresh_messages()
            self.ui.refresh_ledger_view("sends")
            self.ui.show_success(
                "Messages Sent",
                f"Sent {result['sent_count']} messages successfully\n"
                f"Failed: {result['failed_count']}"
            )
                
    def _on_backup_completed(self, task):
        """Handle backup completion callback"""
        if task.result and task.status.value == "completed":
            backup_path = task.result
            logger.info(f"Backup completed: {backup_path}")
            metadata = self.backup_manager.read_backup_metadata(backup_path)
            self.database_manager.record_audit_event(
                "backup",
                backup_path,
                "backup_completed",
                after_state={
                    "backup_path": backup_path,
                    "included_files": len(metadata.get("included_files", [])),
                    "excluded_files": len(metadata.get("excluded_files", []))
                },
                risk_level="medium"
            )
            
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
                backup_path = self.backup_manager.auto_backup()
                if backup_path:
                    metadata = self.backup_manager.read_backup_metadata(backup_path)
                    self.database_manager.record_audit_event(
                        "backup",
                        backup_path,
                        "auto_backup_completed",
                        after_state={
                            "backup_path": backup_path,
                            "included_files": len(metadata.get("included_files", [])),
                            "excluded_files": len(metadata.get("excluded_files", []))
                        },
                        risk_level="medium"
                    )
                logger.info("Auto backup completed")
            except (AttributeError, OSError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
                logger.error("Auto backup failed: %s", type(e).__name__)
                self.database_manager.record_audit_event(
                    "backup",
                    "auto_backup",
                    "auto_backup_failed",
                    after_state={"error_type": type(e).__name__},
                    risk_level="medium"
                )
                
        # Schedule backup in a separate thread
        backup_thread = threading.Timer(3600, auto_backup)  # 1 hour delay
        backup_thread.daemon = True
        backup_thread.start()

    def _record_task_state(self, task):
        """Persist background task state in the local operating ledger."""
        try:
            self.outreach_ledger.record_task_run({
                "task_id": task.id,
                "name": task.name,
                "description": task.description,
                "status": task.status.value,
                "progress": {
                    "current": task.progress.current,
                    "total": task.progress.total,
                    "percentage": task.progress.percentage,
                    "message": task.progress.message
                },
                "result": task.result if isinstance(task.result, (dict, list, str, int, float, bool, type(None))) else str(task.result),
                "error_message": type(task.error).__name__ if task.error else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            })
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Error recording task state: %s", type(e).__name__)
        
    def shutdown(self):
        """Shutdown the application"""
        try:
            logger.info("Shutting down application")
            
            # Shutdown task manager
            self.task_manager.shutdown()
            
            # Close database connections
            # (SQLite connections are automatically closed)
            
            logger.info("Application shutdown complete")
            
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
            logger.error("Error during shutdown: %s", type(e).__name__)

class EnhancedMainApplication(MainApplication):
    """Enhanced main application with integrated functionality"""
    
    def __init__(self, app_controller: EnhancedNLvoorelkaarApp):
        self.app_controller = app_controller
        super().__init__()
        self._wire_operating_view_callbacks()
        
    def show_view(self, view_name: str):
        """Show a view and ensure it uses controller-backed callbacks."""
        super().show_view(view_name)
        self._wire_operating_view_callbacks(view_name)

    def _wire_operating_view_callbacks(self, view_name: Optional[str] = None):
        """Wire all operating-ledger views to controller-backed data/actions."""
        view_names = [view_name] if view_name else list(self.views.keys())
        refresh_methods = {
            "dashboard": "refresh_data",
            "campaigns": "refresh_campaigns",
            "messages": "refresh_messages",
            "volunteers": "refresh_volunteers",
            "matches": "refresh_items",
            "duplicates": "refresh_items",
            "sends": "refresh_items",
            "responses": "refresh_items",
            "followups": "refresh_items",
            "searches": "refresh_items",
            "tasks": "refresh_items",
            "audit": "refresh_items",
            "privacy": "refresh_items",
        }

        for name in view_names:
            view = self.views.get(name)
            if not view:
                continue

            if name == "dashboard":
                view.data_callback = self.app_controller.get_dashboard_data
            elif name == "campaigns":
                view.campaign_callback = self.handle_campaign_action
                view.data_callback = self.get_campaign_data
                view.readiness_callback = self.get_campaign_readiness
                view.operating_summary_callback = self.get_campaign_operating_summary
            elif name == "messages":
                view.data_callback = self.get_message_review_data
                view.action_callback = self.handle_message_action
            elif name == "volunteers":
                view.data_callback = self.get_volunteer_data
                view.detail_callback = self.get_volunteer_detail_data
            elif name == "matches":
                view.data_callback = self.get_match_assessment_data
            elif name == "duplicates":
                view.data_callback = self.get_duplicate_identity_data
                view.action_callback = self.handle_duplicate_action
            elif name == "sends":
                view.data_callback = self.get_send_attempt_data
                view.action_callback = self.handle_send_attempt_action
            elif name == "responses":
                view.data_callback = self.get_response_inbox_data
                view.action_callback = self.handle_response_action
            elif name == "followups":
                view.data_callback = self.get_follow_up_data
                view.action_callback = self.handle_follow_up_action
            elif name == "searches":
                view.data_callback = self.get_search_session_data
            elif name == "tasks":
                view.data_callback = self.get_task_run_data
            elif name == "audit":
                view.data_callback = self.get_audit_log_data
            elif name == "privacy":
                view.data_callback = self.get_privacy_review_data
                view.action_callback = self.handle_privacy_action

            refresh_method = refresh_methods.get(name)
            if refresh_method and hasattr(view, refresh_method):
                try:
                    getattr(view, refresh_method)()
                except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                    logger.error("Error refreshing %s after wiring callbacks: %s", name, type(exc).__name__)
            
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
        if 'volunteers' in self.views and hasattr(self.views['volunteers'], 'refresh_volunteers'):
            self.views['volunteers'].refresh_volunteers()

    def refresh_dashboard(self):
        """Refresh dashboard view."""
        if 'dashboard' in self.views and hasattr(self.views['dashboard'], 'refresh_data'):
            self.views['dashboard'].refresh_data()

    def refresh_campaigns(self):
        """Refresh campaigns view"""
        if 'campaigns' in self.views:
            self.views['campaigns'].refresh_campaigns()

    def refresh_messages(self):
        """Refresh message review view"""
        if 'messages' in self.views and hasattr(self.views['messages'], 'refresh_messages'):
            self.views['messages'].refresh_messages()

    def refresh_ledger_view(self, view_name: str):
        """Refresh a simple ledger list view if it is loaded."""
        if view_name in self.views and hasattr(self.views[view_name], 'refresh_items'):
            self.views[view_name].refresh_items()

    def get_campaign_data(self) -> List[Dict[str, Any]]:
        """Get saved campaigns for the campaign screen."""
        return self.app_controller.get_campaigns()

    def get_campaign_readiness(self, campaign_id: int) -> Dict[str, Any]:
        """Get readiness for a selected campaign."""
        return self.app_controller.get_campaign_readiness(campaign_id)

    def get_campaign_operating_summary(self, campaign_id: int) -> Dict[str, Any]:
        """Get operating ledger status for a selected campaign."""
        return self.app_controller.get_campaign_operating_summary(campaign_id)

    def get_volunteer_data(self) -> List[Dict[str, Any]]:
        """Get saved volunteers for the volunteer detail view."""
        return self.app_controller.get_volunteers()

    def get_volunteer_detail_data(self, volunteer_id: str) -> Optional[Dict[str, Any]]:
        """Get one volunteer with operating ledger context."""
        return self.app_controller.get_volunteer_operating_profile(volunteer_id)

    def handle_campaign_action(self, action: str, data: Dict[str, Any]):
        """Route campaign actions to the controller."""
        if action == "create":
            self.app_controller.create_campaign(data)
            self.status_bar.set_status(f"Campaign '{data['name']}' created", "success")
            self.refresh_campaigns()
        elif action == "create_drafts":
            campaign_id = data.get("campaign_id")
            if not campaign_id:
                return
            draft_ids = self.app_controller.create_campaign_message_drafts(campaign_id)
            self.status_bar.set_status(f"Created {len(draft_ids)} draft message(s)", "success")
            self.refresh_campaigns()
            self.refresh_messages()
        elif action == "assess_matches":
            campaign_id = data.get("campaign_id")
            if not campaign_id:
                return
            assessments = self.app_controller.assess_campaign_matches(campaign_id)
            self.status_bar.set_status(f"Assessed {len(assessments)} volunteer match(es)", "success")
            self.refresh_campaigns()
            self.refresh_ledger_view("matches")

    def get_message_review_data(self) -> List[Dict[str, Any]]:
        """Get drafts waiting for explicit approval."""
        return self.app_controller.get_message_review_queue()

    def handle_message_action(self, action: str, data: Dict[str, Any]):
        """Approve or reject a message draft from the review queue."""
        draft_id = data.get("draft_id")
        if not draft_id:
            return

        if action == "approve":
            self.app_controller.approve_message_draft(draft_id, "Approved in message review queue")
            self.status_bar.set_status(f"Draft {draft_id} approved", "success")
        elif action == "reject":
            self.app_controller.reject_message_draft(draft_id, "Rejected in message review queue")
            self.status_bar.set_status(f"Draft {draft_id} rejected", "warning")
        elif action == "edit":
            self.app_controller.edit_message_draft(
                draft_id,
                subject=data.get("subject"),
                body=data.get("body")
            )
            self.status_bar.set_status(f"Draft {draft_id} updated", "success")

    def get_match_assessment_data(self) -> List[Dict[str, Any]]:
        """Get match assessments."""
        return self.app_controller.get_match_assessments()

    def get_send_attempt_data(self) -> List[Dict[str, Any]]:
        """Get send attempt history."""
        return self.app_controller.get_send_attempt_history()

    def handle_send_attempt_action(self, action: str, data: Dict[str, Any]):
        """Handle manual send evidence from send history."""
        if action == "confirm_sent":
            draft_id = data.get("draft_id")
            if not draft_id:
                return
            self.app_controller.confirm_manual_send(
                draft_id,
                "Operator confirmed manually from Send Attempt History"
            )
            self.status_bar.set_status(f"Draft {draft_id} manually confirmed sent", "success")
            self.refresh_ledger_view("sends")

    def get_duplicate_identity_data(self) -> List[Dict[str, Any]]:
        """Get duplicate identity proposals."""
        return self.app_controller.get_duplicate_identity_proposals()

    def handle_duplicate_action(self, action: str, data: Dict[str, Any]):
        """Handle duplicate identity review actions."""
        if action == "header_action":
            identity_ids = self.app_controller.propose_duplicate_identities()
            self.status_bar.set_status(f"Recorded {len(identity_ids)} duplicate proposal(s)", "warning")
        elif action == "confirm":
            identity_id = data.get("identity_id")
            canonical_volunteer_id = data.get("canonical_volunteer_id")
            if not identity_id or not canonical_volunteer_id:
                return
            self.app_controller.confirm_duplicate_identity(identity_id, canonical_volunteer_id)
            self.status_bar.set_status(f"Duplicate group {identity_id} confirmed", "success")
        self.refresh_ledger_view("duplicates")

    def get_response_inbox_data(self) -> List[Dict[str, Any]]:
        """Get response inbox data."""
        return self.app_controller.get_response_inbox()

    def handle_response_action(self, action: str, data: Dict[str, Any]):
        """Handle manual response entry and outcome closure from the response inbox."""
        if action == "header_action":
            dialog = ResponseDialog(
                self,
                volunteers=self.app_controller.get_volunteers(),
                campaigns=self.app_controller.get_campaigns()
            )
            if not dialog.result:
                return

            response_id = self.app_controller.record_volunteer_response(
                volunteer_id=dialog.result["volunteer_id"],
                campaign_id=dialog.result.get("campaign_id"),
                raw_content=dialog.result["raw_content"],
                source="manual_ui"
            )
            self.status_bar.set_status(f"Recorded response {response_id}", "success")
        elif action == "record_outcome":
            volunteer_id = data.get("volunteer_id")
            outcome_type = data.get("outcome_type")
            if not volunteer_id or not outcome_type:
                self.status_bar.set_status("Cannot record outcome without volunteer and outcome type", "error")
                return

            outcome_id = self.app_controller.record_outreach_outcome(
                volunteer_id=volunteer_id,
                campaign_id=data.get("campaign_id"),
                outcome_type=outcome_type,
                notes=data.get("notes") or "Outcome recorded from Response Inbox",
                response_id=data.get("response_id")
            )
            self.status_bar.set_status(f"Recorded {outcome_type} outcome {outcome_id}", "success")
        else:
            return

        self.refresh_ledger_view("responses")
        self.refresh_ledger_view("followups")
        self.refresh_campaigns()

    def get_follow_up_data(self) -> List[Dict[str, Any]]:
        """Get follow-up queue data."""
        return self.app_controller.get_follow_up_queue()

    def get_audit_log_data(self) -> List[Dict[str, Any]]:
        """Get audit log data."""
        return self.app_controller.get_audit_log()

    def get_task_run_data(self) -> List[Dict[str, Any]]:
        """Get durable task run data."""
        return self.app_controller.get_task_runs()

    def get_search_session_data(self) -> List[Dict[str, Any]]:
        """Get search session data."""
        return self.app_controller.get_search_sessions()

    def get_privacy_review_data(self) -> List[Dict[str, Any]]:
        """Get retention records first, then stale candidates."""
        records = self.app_controller.get_privacy_retention_records()
        return records or self.app_controller.get_privacy_retention_candidates()

    def handle_follow_up_action(self, action: str, data: Dict[str, Any]):
        """Complete or cancel follow-up work items."""
        follow_up_id = data.get("follow_up_id")
        if not follow_up_id:
            return

        if action == "complete":
            self.app_controller.complete_follow_up(follow_up_id)
            self.status_bar.set_status(f"Follow-up {follow_up_id} completed", "success")
        elif action == "approve":
            self.app_controller.approve_follow_up(follow_up_id)
            self.status_bar.set_status(f"Follow-up {follow_up_id} approved", "success")
        elif action == "confirm_sent":
            self.app_controller.confirm_follow_up_sent(
                follow_up_id,
                "Operator confirmed manually from Follow-up Queue"
            )
            self.status_bar.set_status(f"Follow-up {follow_up_id} confirmed sent", "success")
            self.refresh_ledger_view("sends")
        elif action == "cancel":
            self.app_controller.cancel_follow_up(follow_up_id)
            self.status_bar.set_status(f"Follow-up {follow_up_id} cancelled", "warning")
        elif action == "record_outcome":
            volunteer_id = data.get("volunteer_id")
            outcome_type = data.get("outcome_type")
            if not volunteer_id or not outcome_type:
                self.status_bar.set_status("Cannot record outcome without volunteer and outcome type", "error")
                return
            outcome_id = self.app_controller.record_outreach_outcome(
                volunteer_id=volunteer_id,
                campaign_id=data.get("campaign_id"),
                outcome_type=outcome_type,
                notes=data.get("notes") or "Outcome recorded from Follow-up Queue",
                follow_up_id=follow_up_id
            )
            self.status_bar.set_status(f"Recorded {outcome_type} outcome {outcome_id}", "success")

        self.refresh_ledger_view("followups")
        self.refresh_campaigns()

    def handle_privacy_action(self, action: str, data: Dict[str, Any]):
        """Handle retention review actions."""
        if action == "header_action":
            self.app_controller.propose_privacy_retention_actions()
            self.status_bar.set_status("Recorded retention proposals; no data deleted", "warning")
            self.refresh_ledger_view("privacy")
        elif action == "export_json":
            result = self.app_controller.export_volunteer_data("json")
            self.status_bar.set_status(
                f"Exported {result['record_count']} volunteer records to {result['path']}",
                "success"
            )
            self.refresh_ledger_view("audit")
        elif action == "archive":
            volunteer_id = data.get("volunteer_id")
            if not volunteer_id:
                self.status_bar.set_status("Cannot archive without volunteer id", "error")
                return
            self.app_controller.archive_volunteer_for_retention(
                volunteer_id,
                "Archived from Privacy / Retention review"
            )
            self.status_bar.set_status(f"Archived volunteer {volunteer_id}", "success")
            self.refresh_ledger_view("privacy")
            self.refresh_volunteers()
        elif action == "redact":
            volunteer_id = data.get("volunteer_id")
            if not volunteer_id:
                self.status_bar.set_status("Cannot redact without volunteer id", "error")
                return
            self.app_controller.redact_volunteer_personal_data(
                volunteer_id,
                "Personal data redacted from Privacy / Retention review"
            )
            self.status_bar.set_status(f"Redacted volunteer {volunteer_id}", "warning")
            self.refresh_ledger_view("privacy")
            self.refresh_volunteers()
            
    def update_task_progress(self, task):
        """Update task progress in UI"""
        if self.ui:
            self.refresh_ledger_view("tasks")
            task_name = getattr(task, "name", "Task")
            status = getattr(getattr(task, "status", None), "value", "running")
            progress = getattr(task, "progress", None)
            current = getattr(progress, "current", "?")
            total = getattr(progress, "total", "?")
            self.status_bar.set_status(
                f"{task_name}: {status.title()} ({current}/{total})",
                "info"
            )
        
    def on_task_completed(self, task):
        """Handle task completion in UI"""
        if self.ui:
            self.refresh_ledger_view("tasks")

            status_value = getattr(getattr(task, "status", None), "value", "warning")
            status_type = "success" if status_value == "completed" else "warning"
            self.status_bar.set_status(
                f"{getattr(task, 'name', 'Task')}: {status_value}",
                status_type
            )

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
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError, sqlite3.DatabaseError) as e:
        logger.error("Application error: %s", type(e).__name__)
        raise

if __name__ == "__main__":
    main()

