"""
Backup Manager for NLvoorelkaar Tool
Handles automatic backups and data recovery
"""

import os
import shutil
import sqlite3
import json
import zipfile
import re
from datetime import datetime, timedelta
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, data_dir="data", backup_dir="backups"):
        self.data_dir = data_dir
        self.backup_dir = backup_dir
        self.max_backups = 30  # Keep 30 days of backups
        self.sensitive_name_fragments = (
            "credential",
            "credentials",
            "client_secret",
            "secret",
            "token",
            "oauth",
            "session",
            "cookie"
        )
        self.sensitive_extensions = (".enc", ".key", ".pem", ".p12", ".pfx")
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
            backup_name = self._sanitize_backup_name(backup_name)
                
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.zip")
            included_files = []
            excluded_files = []
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                # Backup data directory
                if os.path.exists(self.data_dir):
                    for root, dirs, files in os.walk(self.data_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path, self.data_dir)
                            if self._should_exclude_file(relative_path):
                                excluded_files.append(relative_path)
                                continue
                            arcname = os.path.relpath(file_path, os.path.dirname(self.data_dir))
                            backup_zip.write(file_path, arcname)
                            included_files.append(relative_path)
                            
                # Add metadata
                metadata = {
                    "backup_date": datetime.now().isoformat(),
                    "version": "2.0",
                    "data_dir": self.data_dir,
                    "included_files": included_files,
                    "excluded_files": excluded_files,
                    "exclusion_policy": "credential/token/session-like files are excluded from backups"
                }
                backup_zip.writestr("backup_metadata.json", json.dumps(metadata, indent=2))
                
            logger.info(f"Backup created successfully: {backup_path}")
            return backup_path
            
        except (OSError, ValueError, TypeError, json.JSONDecodeError, zipfile.BadZipFile, sqlite3.DatabaseError) as e:
            logger.error(f"Failed to create backup: {e}")
            return None
            
    def restore_backup(self, backup_path: str) -> bool:
        """Restore data from backup"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
                
            # Create backup of current data before restore
            pre_restore_backup = self.create_backup("pre_restore_backup")
            if not pre_restore_backup:
                logger.warning("Pre-restore backup could not be created before restore.")
            
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                # Verify backup metadata
                try:
                    metadata_content = backup_zip.read("backup_metadata.json")
                    metadata = json.loads(metadata_content)
                    logger.info(f"Restoring backup from {metadata['backup_date']}")
                except (KeyError, json.JSONDecodeError, TypeError, ValueError):
                    logger.warning("Backup metadata not found, proceeding anyway")

                restore_root = os.path.dirname(self.data_dir)
                os.makedirs(restore_root, exist_ok=True)
                self._validate_zip_members(backup_zip, restore_root)
                    
                # Clear current data directory
                if os.path.exists(self.data_dir):
                    shutil.rmtree(self.data_dir)
                    
                # Extract backup
                self._safe_extract(backup_zip, restore_root)
                
            logger.info(f"Backup restored successfully from: {backup_path}")
            return True
            
        except (FileNotFoundError, ValueError, zipfile.BadZipFile, OSError, KeyError, json.JSONDecodeError) as e:
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
            
        except (OSError, ValueError) as e:
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
                    
        except (OSError, ValueError) as e:
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
            
        except (OSError, ValueError, zipfile.BadZipFile) as e:
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
            
        except (FileNotFoundError, OSError, zipfile.BadZipFile, ValueError) as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def read_backup_metadata(self, backup_path: str) -> dict:
        """Read backup metadata without extracting data."""
        try:
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                metadata_content = backup_zip.read("backup_metadata.json")
                return json.loads(metadata_content)
        except (KeyError, json.JSONDecodeError, FileNotFoundError, TypeError, ValueError) as e:
            logger.error(f"Failed to read backup metadata: {e}")
            return {}

    def _sanitize_backup_name(self, backup_name: str) -> str:
        """Return a filesystem-safe backup name."""
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", str(backup_name).strip())
        safe_name = safe_name.strip("._") or "backup"
        return safe_name[:200]

    def _should_exclude_file(self, relative_path: str) -> bool:
        """Return True when a path likely contains credentials or session material."""
        normalized = relative_path.replace("\\", "/").lower()
        filename = os.path.basename(normalized)
        _, extension = os.path.splitext(filename)
        if extension in self.sensitive_extensions:
            return True
        return any(fragment in filename for fragment in self.sensitive_name_fragments)

    def _safe_extract(self, backup_zip: zipfile.ZipFile, target_dir: str):
        """Extract a zip while preventing path traversal."""
        self._validate_zip_members(backup_zip, target_dir)
        backup_zip.extractall(os.path.abspath(target_dir))

    def _validate_zip_members(self, backup_zip: zipfile.ZipFile, target_dir: str):
        """Validate that all zip members stay inside the target directory."""
        target_root = os.path.abspath(target_dir)
        for member in backup_zip.infolist():
            destination = os.path.abspath(os.path.join(target_root, member.filename))
            if not destination.startswith(target_root + os.sep) and destination != target_root:
                raise ValueError(f"Unsafe backup member path: {member.filename}")
            
    def export_data(self, export_path: str, format="json") -> bool:
        """Export volunteer data from the local SQLite database.

        This method intentionally fails closed when no database can be found. A successful
        return means an export file was actually written by the schema-aware DataExporter.
        """
        try:
            selected_format = format.lower().strip()
            if selected_format not in {"json", "csv"}:
                logger.error(f"Unsupported export format: {format}")
                return False

            database_path = self._find_database_path()
            if not database_path:
                logger.error("No SQLite database found for export")
                return False

            os.makedirs(os.path.dirname(os.path.abspath(export_path)) or ".", exist_ok=True)

            from services.data_management import DataExporter, ExportConfig, ExportFormat

            exporter = DataExporter(database_path)
            record_count = exporter.export_volunteers(
                export_path,
                ExportConfig(format=ExportFormat(selected_format))
            )
            logger.info(f"Exported {record_count} volunteer records to {export_path}")
            return os.path.exists(export_path)

        except (OSError, ValueError, TypeError, KeyError, ImportError) as e:
            logger.error(f"Failed to export data: {e}")
            return False

    def _find_database_path(self) -> Optional[str]:
        """Find the most likely non-sensitive SQLite database managed by this app."""
        candidates = []
        if os.path.isfile(self.data_dir):
            candidates.append(self.data_dir)
        elif os.path.isdir(self.data_dir):
            for root, _, files in os.walk(self.data_dir):
                for file in files:
                    relative_path = os.path.relpath(os.path.join(root, file), self.data_dir)
                    if self._should_exclude_file(relative_path):
                        continue
                    if file.lower().endswith((".db", ".sqlite", ".sqlite3")):
                        candidates.append(os.path.join(root, file))

        if not candidates:
            return None

        priority_names = ("nlvoorelkaar.db", "volunteers.db", "database.db", "app.db")
        candidates.sort(
            key=lambda path: (
                priority_names.index(os.path.basename(path).lower())
                if os.path.basename(path).lower() in priority_names
                else len(priority_names),
                path
            )
        )
        return candidates[0]

