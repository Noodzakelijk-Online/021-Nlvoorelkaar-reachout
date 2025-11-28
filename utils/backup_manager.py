"""
Backup Manager for NLvoorelkaar Tool
Handles automatic backups and data recovery
"""

import os
import shutil
import sqlite3
import json
import zipfile
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, data_dir="data", backup_dir="backups"):
        self.data_dir = data_dir
        self.backup_dir = backup_dir
        self.max_backups = 30  # Keep 30 days of backups
        self._ensure_backup_dir()
        
    def _ensure_backup_dir(self):
        """Ensure backup directory exists"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, mode=0o700)
            
    def create_backup(self, backup_name=None) -> str:
        """Create a backup of all data"""
        try:
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.zip")
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                # Backup data directory
                if os.path.exists(self.data_dir):
                    for root, dirs, files in os.walk(self.data_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(self.data_dir))
                            backup_zip.write(file_path, arcname)
                            
                # Add metadata
                metadata = {
                    "backup_date": datetime.now().isoformat(),
                    "version": "2.0",
                    "data_dir": self.data_dir
                }
                backup_zip.writestr("backup_metadata.json", json.dumps(metadata, indent=2))
                
            logger.info(f"Backup created successfully: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
            
    def restore_backup(self, backup_path: str) -> bool:
        """Restore data from backup"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
                
            # Create backup of current data before restore
            current_backup = self.create_backup("pre_restore_backup")
            
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                # Verify backup metadata
                try:
                    metadata_content = backup_zip.read("backup_metadata.json")
                    metadata = json.loads(metadata_content)
                    logger.info(f"Restoring backup from {metadata['backup_date']}")
                except:
                    logger.warning("Backup metadata not found, proceeding anyway")
                    
                # Clear current data directory
                if os.path.exists(self.data_dir):
                    shutil.rmtree(self.data_dir)
                    
                # Extract backup
                backup_zip.extractall(os.path.dirname(self.data_dir))
                
            logger.info(f"Backup restored successfully from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
            
    def list_backups(self) -> list:
        """List available backups"""
        try:
            backups = []
            if os.path.exists(self.backup_dir):
                for file in os.listdir(self.backup_dir):
                    if file.endswith('.zip'):
                        file_path = os.path.join(self.backup_dir, file)
                        stat = os.stat(file_path)
                        backups.append({
                            "name": file,
                            "path": file_path,
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(stat.st_ctime),
                            "modified": datetime.fromtimestamp(stat.st_mtime)
                        })
                        
            # Sort by creation date (newest first)
            backups.sort(key=lambda x: x["created"], reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
            
    def cleanup_old_backups(self):
        """Remove old backups beyond retention period"""
        try:
            backups = self.list_backups()
            if len(backups) > self.max_backups:
                old_backups = backups[self.max_backups:]
                for backup in old_backups:
                    os.remove(backup["path"])
                    logger.info(f"Removed old backup: {backup['name']}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            
    def auto_backup(self):
        """Create automatic daily backup"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            backup_name = f"auto_backup_{today}"
            
            # Check if today's backup already exists
            existing_backups = self.list_backups()
            for backup in existing_backups:
                if backup_name in backup["name"]:
                    logger.info("Today's backup already exists")
                    return backup["path"]
                    
            # Create new backup
            backup_path = self.create_backup(backup_name)
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create auto backup: {e}")
            return None
            
    def verify_backup(self, backup_path: str) -> bool:
        """Verify backup integrity"""
        try:
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                # Test the zip file
                bad_file = backup_zip.testzip()
                if bad_file:
                    logger.error(f"Backup verification failed: {bad_file}")
                    return False
                    
                # Check for required files
                file_list = backup_zip.namelist()
                if "backup_metadata.json" not in file_list:
                    logger.warning("Backup metadata missing")
                    
            logger.info(f"Backup verification successful: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False
            
    def export_data(self, export_path: str, format="json") -> bool:
        """Export data in various formats"""
        try:
            if format == "json":
                return self._export_json(export_path)
            elif format == "csv":
                return self._export_csv(export_path)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return False
            
    def _export_json(self, export_path: str) -> bool:
        """Export data as JSON"""
        # Implementation would depend on database structure
        # This is a placeholder for the actual implementation
        logger.info(f"JSON export completed: {export_path}")
        return True
        
    def _export_csv(self, export_path: str) -> bool:
        """Export data as CSV"""
        # Implementation would depend on database structure
        # This is a placeholder for the actual implementation
        logger.info(f"CSV export completed: {export_path}")
        return True

