"""
Delta Synchronization System
Implements efficient incremental updates by only syncing changes
since the last synchronization.
"""

import time
import hashlib
import json
import logging
from typing import Optional, Dict, List, Any, Set, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
import sqlite3

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes detected"""
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"


@dataclass
class VolunteerFingerprint:
    """Fingerprint for change detection"""
    profile_id: str
    content_hash: str
    last_seen: datetime
    
    @staticmethod
    def compute_hash(data: Dict) -> str:
        """Compute hash of volunteer data"""
        # Normalize data for consistent hashing
        normalized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(normalized.encode()).hexdigest()


@dataclass
class SyncResult:
    """Result of a sync operation"""
    added: List[Dict] = field(default_factory=list)
    modified: List[Dict] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    unchanged: int = 0
    duration_seconds: float = 0
    
    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.modified) + len(self.removed)
    
    @property
    def summary(self) -> str:
        return (f"Added: {len(self.added)}, Modified: {len(self.modified)}, "
                f"Removed: {len(self.removed)}, Unchanged: {self.unchanged}")


class FingerprintStore:
    """
    Stores fingerprints for change detection
    
    Maintains a database of content hashes to detect
    what has changed since last sync.
    """
    
    def __init__(self, db_path: str = 'data/fingerprints.db'):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize fingerprint database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS fingerprints (
                    profile_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    last_seen REAL NOT NULL,
                    first_seen REAL NOT NULL,
                    sync_count INTEGER DEFAULT 1
                );
                
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_time REAL NOT NULL,
                    total_profiles INTEGER,
                    added INTEGER,
                    modified INTEGER,
                    removed INTEGER,
                    duration_seconds REAL
                );
                
                CREATE INDEX IF NOT EXISTS idx_fp_hash ON fingerprints(content_hash);
                CREATE INDEX IF NOT EXISTS idx_fp_seen ON fingerprints(last_seen);
            ''')
    
    def get_fingerprint(self, profile_id: str) -> Optional[VolunteerFingerprint]:
        """Get fingerprint for a profile"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT profile_id, content_hash, last_seen FROM fingerprints WHERE profile_id = ?',
                (profile_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return VolunteerFingerprint(
                    profile_id=row[0],
                    content_hash=row[1],
                    last_seen=datetime.fromtimestamp(row[2])
                )
        return None
    
    def get_all_fingerprints(self) -> Dict[str, str]:
        """Get all fingerprints as dict {profile_id: content_hash}"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT profile_id, content_hash FROM fingerprints')
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def update_fingerprint(self, profile_id: str, content_hash: str) -> ChangeType:
        """
        Update fingerprint and return change type
        
        Returns:
            ChangeType indicating what changed
        """
        now = time.time()
        
        with sqlite3.connect(self.db_path) as conn:
            # Check existing
            cursor = conn.execute(
                'SELECT content_hash FROM fingerprints WHERE profile_id = ?',
                (profile_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                # New profile
                conn.execute('''
                    INSERT INTO fingerprints (profile_id, content_hash, last_seen, first_seen)
                    VALUES (?, ?, ?, ?)
                ''', (profile_id, content_hash, now, now))
                return ChangeType.ADDED
            
            elif row[0] != content_hash:
                # Modified profile
                conn.execute('''
                    UPDATE fingerprints 
                    SET content_hash = ?, last_seen = ?, sync_count = sync_count + 1
                    WHERE profile_id = ?
                ''', (content_hash, now, profile_id))
                return ChangeType.MODIFIED
            
            else:
                # Unchanged
                conn.execute(
                    'UPDATE fingerprints SET last_seen = ? WHERE profile_id = ?',
                    (now, profile_id)
                )
                return ChangeType.UNCHANGED
    
    def batch_update_fingerprints(
        self,
        fingerprints: List[Tuple[str, str]]
    ) -> Dict[str, ChangeType]:
        """
        Batch update fingerprints
        
        Args:
            fingerprints: List of (profile_id, content_hash) tuples
        
        Returns:
            Dict mapping profile_id to ChangeType
        """
        results = {}
        now = time.time()
        
        # Get existing fingerprints
        existing = self.get_all_fingerprints()
        
        with sqlite3.connect(self.db_path) as conn:
            for profile_id, content_hash in fingerprints:
                if profile_id not in existing:
                    # New
                    conn.execute('''
                        INSERT INTO fingerprints (profile_id, content_hash, last_seen, first_seen)
                        VALUES (?, ?, ?, ?)
                    ''', (profile_id, content_hash, now, now))
                    results[profile_id] = ChangeType.ADDED
                
                elif existing[profile_id] != content_hash:
                    # Modified
                    conn.execute('''
                        UPDATE fingerprints 
                        SET content_hash = ?, last_seen = ?, sync_count = sync_count + 1
                        WHERE profile_id = ?
                    ''', (content_hash, now, profile_id))
                    results[profile_id] = ChangeType.MODIFIED
                
                else:
                    # Unchanged
                    conn.execute(
                        'UPDATE fingerprints SET last_seen = ? WHERE profile_id = ?',
                        (now, profile_id)
                    )
                    results[profile_id] = ChangeType.UNCHANGED
        
        return results
    
    def find_removed(self, current_ids: Set[str]) -> List[str]:
        """Find profiles that no longer exist"""
        existing_ids = set(self.get_all_fingerprints().keys())
        return list(existing_ids - current_ids)
    
    def mark_removed(self, profile_ids: List[str]) -> int:
        """Mark profiles as removed"""
        if not profile_ids:
            return 0
        
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join(['?' for _ in profile_ids])
            cursor = conn.execute(
                f'DELETE FROM fingerprints WHERE profile_id IN ({placeholders})',
                profile_ids
            )
            return cursor.rowcount
    
    def record_sync(self, result: SyncResult) -> None:
        """Record sync in history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO sync_history 
                (sync_time, total_profiles, added, modified, removed, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                time.time(),
                len(result.added) + len(result.modified) + result.unchanged,
                len(result.added),
                len(result.modified),
                len(result.removed),
                result.duration_seconds
            ))
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """Get timestamp of last sync"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT MAX(sync_time) FROM sync_history'
            )
            row = cursor.fetchone()
            if row and row[0]:
                return datetime.fromtimestamp(row[0])
        return None
    
    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """Get recent sync history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM sync_history 
                ORDER BY sync_time DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stale_profiles(self, days: int = 7) -> List[str]:
        """Get profiles not seen in specified days"""
        cutoff = time.time() - (days * 86400)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT profile_id FROM fingerprints WHERE last_seen < ?',
                (cutoff,)
            )
            return [row[0] for row in cursor.fetchall()]


class DeltaSyncEngine:
    """
    Delta Synchronization Engine
    
    Efficiently syncs only changes since last sync,
    dramatically reducing time and network usage.
    
    Features:
    - Content-based change detection
    - Incremental updates
    - Removal detection
    - Sync history tracking
    - Progress callbacks
    """
    
    def __init__(
        self,
        fingerprint_store: Optional[FingerprintStore] = None,
        db_path: str = 'data/fingerprints.db'
    ):
        self.store = fingerprint_store or FingerprintStore(db_path)
        self._lock = threading.Lock()
    
    def sync(
        self,
        fetch_func: Callable[[int], List[Dict]],
        total_pages: int,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_change: Optional[Callable[[ChangeType, Dict], None]] = None
    ) -> SyncResult:
        """
        Perform delta synchronization
        
        Args:
            fetch_func: Function to fetch page of volunteers (page_num) -> [volunteers]
            total_pages: Total number of pages to fetch
            on_progress: Progress callback (current, total, message)
            on_change: Callback for each change detected
        
        Returns:
            SyncResult with all changes
        """
        start_time = time.monotonic()
        result = SyncResult()
        
        # Track all seen profile IDs
        seen_ids: Set[str] = set()
        
        # Fetch and process each page
        for page in range(1, total_pages + 1):
            if on_progress:
                on_progress(page, total_pages, f"Fetching page {page}/{total_pages}")
            
            try:
                volunteers = fetch_func(page)
                
                for volunteer in volunteers:
                    profile_id = volunteer.get('profile_id') or volunteer.get('id')
                    if not profile_id:
                        continue
                    
                    seen_ids.add(profile_id)
                    
                    # Compute content hash
                    content_hash = VolunteerFingerprint.compute_hash(volunteer)
                    
                    # Check for changes
                    change_type = self.store.update_fingerprint(profile_id, content_hash)
                    
                    if change_type == ChangeType.ADDED:
                        result.added.append(volunteer)
                        if on_change:
                            on_change(change_type, volunteer)
                    
                    elif change_type == ChangeType.MODIFIED:
                        result.modified.append(volunteer)
                        if on_change:
                            on_change(change_type, volunteer)
                    
                    else:
                        result.unchanged += 1
            
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                continue
        
        # Detect removed profiles
        if on_progress:
            on_progress(total_pages, total_pages, "Detecting removed profiles...")
        
        removed_ids = self.store.find_removed(seen_ids)
        result.removed = removed_ids
        
        if removed_ids:
            self.store.mark_removed(removed_ids)
            if on_change:
                for profile_id in removed_ids:
                    on_change(ChangeType.REMOVED, {'profile_id': profile_id})
        
        result.duration_seconds = time.monotonic() - start_time
        
        # Record sync
        self.store.record_sync(result)
        
        logger.info(f"Delta sync completed: {result.summary}")
        return result
    
    def quick_sync(
        self,
        fetch_recent_func: Callable[[], List[Dict]],
        on_change: Optional[Callable[[ChangeType, Dict], None]] = None
    ) -> SyncResult:
        """
        Quick sync - only check recently updated profiles
        
        For use between full syncs to catch recent changes.
        
        Args:
            fetch_recent_func: Function to fetch recently updated profiles
            on_change: Callback for each change
        
        Returns:
            SyncResult with changes
        """
        start_time = time.monotonic()
        result = SyncResult()
        
        try:
            recent_volunteers = fetch_recent_func()
            
            for volunteer in recent_volunteers:
                profile_id = volunteer.get('profile_id') or volunteer.get('id')
                if not profile_id:
                    continue
                
                content_hash = VolunteerFingerprint.compute_hash(volunteer)
                change_type = self.store.update_fingerprint(profile_id, content_hash)
                
                if change_type == ChangeType.ADDED:
                    result.added.append(volunteer)
                elif change_type == ChangeType.MODIFIED:
                    result.modified.append(volunteer)
                else:
                    result.unchanged += 1
                
                if on_change and change_type != ChangeType.UNCHANGED:
                    on_change(change_type, volunteer)
        
        except Exception as e:
            logger.error(f"Quick sync error: {e}")
        
        result.duration_seconds = time.monotonic() - start_time
        return result
    
    def get_changes_since(self, since: datetime) -> Dict[str, List]:
        """Get all changes since a specific time"""
        # This would require storing change history
        # For now, return sync history
        history = self.store.get_sync_history(limit=100)
        
        since_ts = since.timestamp()
        recent = [h for h in history if h['sync_time'] > since_ts]
        
        return {
            'syncs': len(recent),
            'total_added': sum(h['added'] for h in recent),
            'total_modified': sum(h['modified'] for h in recent),
            'total_removed': sum(h['removed'] for h in recent)
        }
    
    def needs_full_sync(self, max_age_hours: int = 24) -> bool:
        """Check if a full sync is needed"""
        last_sync = self.store.get_last_sync_time()
        
        if last_sync is None:
            return True
        
        age = datetime.now() - last_sync
        return age > timedelta(hours=max_age_hours)
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics"""
        history = self.store.get_sync_history(limit=10)
        
        if not history:
            return {'status': 'no_syncs'}
        
        last_sync = history[0]
        
        return {
            'last_sync': datetime.fromtimestamp(last_sync['sync_time']).isoformat(),
            'last_duration_seconds': last_sync['duration_seconds'],
            'last_changes': {
                'added': last_sync['added'],
                'modified': last_sync['modified'],
                'removed': last_sync['removed']
            },
            'total_profiles': last_sync['total_profiles'],
            'sync_count': len(history)
        }


class IncrementalUpdater:
    """
    Incremental Update Manager
    
    Manages incremental updates for specific data types
    with configurable update strategies.
    """
    
    def __init__(self, delta_engine: DeltaSyncEngine):
        self.engine = delta_engine
        self._update_callbacks: Dict[str, Callable] = {}
    
    def register_callback(
        self,
        data_type: str,
        callback: Callable[[ChangeType, Dict], None]
    ) -> None:
        """Register callback for specific data type changes"""
        self._update_callbacks[data_type] = callback
    
    def process_change(
        self,
        data_type: str,
        change_type: ChangeType,
        data: Dict
    ) -> None:
        """Process a change and trigger callbacks"""
        if data_type in self._update_callbacks:
            try:
                self._update_callbacks[data_type](change_type, data)
            except Exception as e:
                logger.error(f"Callback error for {data_type}: {e}")
    
    def apply_changes(
        self,
        sync_result: SyncResult,
        apply_func: Callable[[ChangeType, Dict], None]
    ) -> Dict[str, int]:
        """
        Apply sync changes to database
        
        Args:
            sync_result: Result from delta sync
            apply_func: Function to apply each change
        
        Returns:
            Summary of applied changes
        """
        applied = {'added': 0, 'modified': 0, 'removed': 0, 'errors': 0}
        
        # Apply additions
        for volunteer in sync_result.added:
            try:
                apply_func(ChangeType.ADDED, volunteer)
                applied['added'] += 1
            except Exception as e:
                logger.error(f"Error applying addition: {e}")
                applied['errors'] += 1
        
        # Apply modifications
        for volunteer in sync_result.modified:
            try:
                apply_func(ChangeType.MODIFIED, volunteer)
                applied['modified'] += 1
            except Exception as e:
                logger.error(f"Error applying modification: {e}")
                applied['errors'] += 1
        
        # Apply removals
        for profile_id in sync_result.removed:
            try:
                apply_func(ChangeType.REMOVED, {'profile_id': profile_id})
                applied['removed'] += 1
            except Exception as e:
                logger.error(f"Error applying removal: {e}")
                applied['errors'] += 1
        
        return applied


# Global instance
_delta_engine: Optional[DeltaSyncEngine] = None


def get_delta_engine(db_path: str = 'data/fingerprints.db') -> DeltaSyncEngine:
    """Get global delta sync engine"""
    global _delta_engine
    if _delta_engine is None:
        _delta_engine = DeltaSyncEngine(db_path=db_path)
    return _delta_engine
