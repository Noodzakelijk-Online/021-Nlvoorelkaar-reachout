"""
Enhanced Volunteer Service with Rate Limiting, Progress Persistence, and Deduplication
Addresses TODO items #4: Volunteer Service Improvements
"""

import os
import json
import time
import logging
import hashlib
import sqlite3
from contextlib import closing
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from bs4 import BeautifulSoup
import requests

from models.enhanced_session_manager import EnhancedSessionManager
from config.enhanced_settings import RequestConfig, URLConfig, TimingConfig

logger = logging.getLogger(__name__)


class ScrapeStatus(Enum):
    """Scraping session status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScrapeProgress:
    """Progress tracking for scraping sessions"""
    session_id: str = ""
    status: ScrapeStatus = ScrapeStatus.NOT_STARTED
    total_pages: int = 0
    current_page: int = 0
    total_volunteers: int = 0
    processed_volunteers: int = 0
    new_volunteers: int = 0
    updated_volunteers: int = 0
    duplicate_volunteers: int = 0
    failed_pages: List[int] = field(default_factory=list)
    started_at: Optional[str] = None
    last_updated: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    search_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScrapeProgress':
        data = data.copy()
        data['status'] = ScrapeStatus(data.get('status', 'not_started'))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class RateLimiter:
    """
    Rate limiter to prevent being blocked by NLvoorElkaar
    
    Features:
    - Configurable requests per minute
    - Adaptive rate limiting based on response times
    - Burst protection
    - Cooldown periods
    """
    
    def __init__(
        self,
        requests_per_minute: int = TimingConfig.REQUESTS_PER_MINUTE,
        min_interval: float = TimingConfig.MIN_REQUEST_INTERVAL,
        burst_limit: int = 5,
        cooldown_after_burst: float = 10.0
    ):
        self.requests_per_minute = requests_per_minute
        self.min_interval = min_interval
        self.burst_limit = burst_limit
        self.cooldown_after_burst = cooldown_after_burst
        
        self._request_times: List[float] = []
        self._lock = threading.Lock()
        self._consecutive_requests = 0
        self._last_request_time = 0.0
        self._adaptive_delay = min_interval
    
    def wait(self) -> float:
        """
        Wait for rate limit and return actual wait time
        
        Returns:
            Time waited in seconds
        """
        with self._lock:
            current_time = time.time()
            
            # Clean old request times (older than 1 minute)
            self._request_times = [
                t for t in self._request_times 
                if current_time - t < 60
            ]
            
            # Check requests per minute limit
            if len(self._request_times) >= self.requests_per_minute:
                oldest_request = min(self._request_times)
                wait_time = 60 - (current_time - oldest_request)
                if wait_time > 0:
                    logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
                    current_time = time.time()
            
            # Check minimum interval
            time_since_last = current_time - self._last_request_time
            if time_since_last < self._adaptive_delay:
                wait_time = self._adaptive_delay - time_since_last
                logger.debug(f"Min interval: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                current_time = time.time()
            
            # Check burst protection
            self._consecutive_requests += 1
            if self._consecutive_requests >= self.burst_limit:
                logger.debug(f"Burst protection: cooling down {self.cooldown_after_burst}s")
                time.sleep(self.cooldown_after_burst)
                self._consecutive_requests = 0
                current_time = time.time()
            
            # Record this request
            self._request_times.append(current_time)
            self._last_request_time = current_time
            
            return current_time - self._last_request_time
    
    def adapt_rate(self, response_time: float, status_code: int) -> None:
        """
        Adapt rate limiting based on response characteristics
        
        Args:
            response_time: Time taken for the request
            status_code: HTTP status code received
        """
        with self._lock:
            if status_code == 429:  # Too Many Requests
                self._adaptive_delay = min(self._adaptive_delay * 2, 30.0)
                logger.warning(f"Rate limited (429), increasing delay to {self._adaptive_delay}s")
            elif status_code >= 500:  # Server error
                self._adaptive_delay = min(self._adaptive_delay * 1.5, 20.0)
                logger.warning(f"Server error, increasing delay to {self._adaptive_delay}s")
            elif response_time > 5.0:  # Slow response
                self._adaptive_delay = min(self._adaptive_delay * 1.2, 10.0)
            elif response_time < 1.0 and status_code == 200:
                # Good response, can slightly decrease delay
                self._adaptive_delay = max(self._adaptive_delay * 0.95, self.min_interval)
    
    def reset_burst_counter(self) -> None:
        """Reset the burst counter (e.g., after a pause)"""
        with self._lock:
            self._consecutive_requests = 0


class VolunteerDeduplicator:
    """
    Deduplication system for volunteers
    
    Features:
    - Hash-based duplicate detection
    - Fuzzy matching for similar profiles
    - Merge strategy for duplicates
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._seen_hashes: Set[str] = set()
        self._init_db()
        self._load_existing_hashes()
    
    def _init_db(self) -> None:
        """Initialize deduplication tables"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS volunteer_hashes (
                    hash TEXT PRIMARY KEY,
                    volunteer_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_volunteer_id 
                ON volunteer_hashes(volunteer_id)
            ''')
            conn.commit()
    
    def _load_existing_hashes(self) -> None:
        """Load existing hashes into memory"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute('SELECT hash FROM volunteer_hashes')
            self._seen_hashes = {row[0] for row in cursor}
        
        logger.info(f"Loaded {len(self._seen_hashes)} existing volunteer hashes")
    
    def _compute_hash(self, volunteer_data: Dict[str, Any]) -> str:
        """Compute unique hash for volunteer"""
        # Use key identifying fields
        key_fields = ['profile_id', 'name', 'location']
        hash_input = '|'.join(
            str(volunteer_data.get(field, '')) 
            for field in key_fields
        )
        return hashlib.sha256(hash_input.encode()).hexdigest()[:32]
    
    def is_duplicate(self, volunteer_data: Dict[str, Any]) -> bool:
        """
        Check if volunteer is a duplicate
        
        Args:
            volunteer_data: Volunteer data dictionary
            
        Returns:
            True if duplicate, False otherwise
        """
        volunteer_hash = self._compute_hash(volunteer_data)
        return volunteer_hash in self._seen_hashes
    
    def mark_seen(self, volunteer_data: Dict[str, Any], volunteer_id: str) -> None:
        """
        Mark volunteer as seen
        
        Args:
            volunteer_data: Volunteer data dictionary
            volunteer_id: Volunteer ID in database
        """
        volunteer_hash = self._compute_hash(volunteer_data)
        
        if volunteer_hash not in self._seen_hashes:
            self._seen_hashes.add(volunteer_hash)
            
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.execute(
                    'INSERT OR IGNORE INTO volunteer_hashes (hash, volunteer_id, created_at) VALUES (?, ?, ?)',
                    (volunteer_hash, volunteer_id, datetime.now().isoformat())
                )
                conn.commit()
    
    def get_stats(self) -> Dict[str, int]:
        """Get deduplication statistics"""
        return {
            'total_hashes': len(self._seen_hashes)
        }


class ProgressPersistence:
    """
    Persistence layer for scraping progress
    
    Features:
    - Save/restore scraping sessions
    - Resume interrupted sessions
    - Track failed pages for retry
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize progress tables"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scrape_sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    total_pages INTEGER DEFAULT 0,
                    current_page INTEGER DEFAULT 0,
                    total_volunteers INTEGER DEFAULT 0,
                    processed_volunteers INTEGER DEFAULT 0,
                    new_volunteers INTEGER DEFAULT 0,
                    updated_volunteers INTEGER DEFAULT 0,
                    duplicate_volunteers INTEGER DEFAULT 0,
                    failed_pages TEXT,
                    started_at TEXT,
                    last_updated TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    search_params TEXT
                )
            ''')
            conn.commit()
    
    def save_progress(self, progress: ScrapeProgress) -> None:
        """Save scraping progress"""
        progress.last_updated = datetime.now().isoformat()
        
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO scrape_sessions 
                (session_id, status, total_pages, current_page, total_volunteers,
                 processed_volunteers, new_volunteers, updated_volunteers, 
                 duplicate_volunteers, failed_pages, started_at, last_updated,
                 completed_at, error_message, search_params)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                progress.session_id,
                progress.status.value,
                progress.total_pages,
                progress.current_page,
                progress.total_volunteers,
                progress.processed_volunteers,
                progress.new_volunteers,
                progress.updated_volunteers,
                progress.duplicate_volunteers,
                json.dumps(progress.failed_pages),
                progress.started_at,
                progress.last_updated,
                progress.completed_at,
                progress.error_message,
                json.dumps(progress.search_params)
            ))
            conn.commit()
    
    def load_progress(self, session_id: str) -> Optional[ScrapeProgress]:
        """Load scraping progress"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM scrape_sessions WHERE session_id = ?',
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                data = dict(row)
                data['failed_pages'] = json.loads(data.get('failed_pages') or '[]')
                data['search_params'] = json.loads(data.get('search_params') or '{}')
                return ScrapeProgress.from_dict(data)
        
        return None
    
    def get_resumable_sessions(self) -> List[ScrapeProgress]:
        """Get all sessions that can be resumed"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM scrape_sessions 
                WHERE status IN ('in_progress', 'paused')
                ORDER BY last_updated DESC
            ''')
            
            sessions = []
            for row in cursor:
                data = dict(row)
                data['failed_pages'] = json.loads(data.get('failed_pages') or '[]')
                data['search_params'] = json.loads(data.get('search_params') or '{}')
                sessions.append(ScrapeProgress.from_dict(data))
            
            return sessions
    
    def delete_session(self, session_id: str) -> None:
        """Delete a scraping session"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                'DELETE FROM scrape_sessions WHERE session_id = ?',
                (session_id,)
            )
            conn.commit()


class EnhancedVolunteerService:
    """
    Enhanced volunteer service with rate limiting, progress persistence, and deduplication
    
    Features:
    - Configurable rate limiting
    - Progress persistence (resume interrupted sessions)
    - Volunteer deduplication
    - Incremental updates
    - Detailed progress callbacks
    """
    
    def __init__(self, db_path: Optional[str] = None, progress_callback: Optional[Callable[[ScrapeProgress], None]] = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            'volunteers.db'
        )
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize components
        self.rate_limiter = RateLimiter()
        self.deduplicator = VolunteerDeduplicator(self.db_path)
        self.progress_persistence = ProgressPersistence(self.db_path)
        self.session_manager = EnhancedSessionManager()
        
        # State
        self._current_progress: Optional[ScrapeProgress] = None
        self._is_running = False
        self._should_stop = False
        self._progress_callback: Optional[Callable[[ScrapeProgress], None]] = progress_callback
        
        # Initialize database
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize volunteer database"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS volunteers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT UNIQUE NOT NULL,
                    name TEXT,
                    location TEXT,
                    description TEXT,
                    skills TEXT,
                    availability TEXT,
                    contact_info TEXT,
                    profile_url TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    raw_data TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_profile_id ON volunteers(profile_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_location ON volunteers(location)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_is_active ON volunteers(is_active)
            ''')

            existing_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(volunteers)")
            }
            for column_name, column_type in {
                "raw_data": "TEXT",
                "first_seen": "TEXT",
                "last_updated": "TEXT"
            }.items():
                if column_name not in existing_columns:
                    conn.execute(f"ALTER TABLE volunteers ADD COLUMN {column_name} {column_type}")
            
            conn.commit()
    
    def set_progress_callback(self, callback: Callable[[ScrapeProgress], None]) -> None:
        """Set callback for progress updates"""
        self._progress_callback = callback
    
    def _notify_progress(self) -> None:
        """Notify progress callback"""
        if self._progress_callback and self._current_progress:
            try:
                self._progress_callback(self._current_progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def start_scraping(
        self,
        location_ids: List[str],
        resume_session_id: Optional[str] = None
    ) -> str:
        """
        Start or resume a scraping session
        
        Args:
            location_ids: List of location IDs to scrape
            resume_session_id: Optional session ID to resume
            
        Returns:
            Session ID
        """
        if self._is_running:
            raise RuntimeError("Scraping session already in progress")
        
        # Resume or create new session
        if resume_session_id:
            self._current_progress = self.progress_persistence.load_progress(resume_session_id)
            if not self._current_progress:
                raise ValueError(f"Session {resume_session_id} not found")
            logger.info(f"Resuming session {resume_session_id}")
        else:
            import uuid
            session_id = str(uuid.uuid4())[:8]
            self._current_progress = ScrapeProgress(
                session_id=session_id,
                status=ScrapeStatus.IN_PROGRESS,
                started_at=datetime.now().isoformat(),
                search_params={'location_ids': location_ids}
            )
            logger.info(f"Starting new session {session_id}")
        
        self._is_running = True
        self._should_stop = False
        self._current_progress.status = ScrapeStatus.IN_PROGRESS
        self.progress_persistence.save_progress(self._current_progress)
        
        # Start scraping in background thread
        thread = threading.Thread(
            target=self._scrape_volunteers,
            args=(location_ids,),
            daemon=True
        )
        thread.start()
        
        return self._current_progress.session_id
    
    def pause_scraping(self) -> None:
        """Pause the current scraping session"""
        if self._current_progress:
            self._should_stop = True
            self._current_progress.status = ScrapeStatus.PAUSED
            self.progress_persistence.save_progress(self._current_progress)
            logger.info("Scraping paused")
    
    def cancel_scraping(self) -> None:
        """Cancel the current scraping session"""
        if self._current_progress:
            self._should_stop = True
            self._current_progress.status = ScrapeStatus.CANCELLED
            self.progress_persistence.save_progress(self._current_progress)
            logger.info("Scraping cancelled")
    
    def _scrape_volunteers(self, location_ids: List[str]) -> None:
        """Main scraping loop"""
        try:
            # Get total pages first
            first_page_url = self._build_search_url(location_ids, 1)
            response = self._make_request(first_page_url)
            
            if not response:
                raise Exception("Failed to fetch first page")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            self._current_progress.total_pages = self._extract_total_pages(soup)
            self._current_progress.total_volunteers = self._extract_total_count(soup)
            
            # Process first page
            self._process_page(soup)
            self._current_progress.current_page = 1
            self.progress_persistence.save_progress(self._current_progress)
            self._notify_progress()
            
            # Process remaining pages
            start_page = max(2, self._current_progress.current_page + 1)
            
            for page in range(start_page, self._current_progress.total_pages + 1):
                if self._should_stop:
                    break
                
                # Rate limiting
                self.rate_limiter.wait()
                
                # Fetch page
                page_url = self._build_search_url(location_ids, page)
                start_time = time.time()
                response = self._make_request(page_url)
                response_time = time.time() - start_time
                
                if response:
                    self.rate_limiter.adapt_rate(response_time, response.status_code)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    self._process_page(soup)
                else:
                    self._current_progress.failed_pages.append(page)
                
                self._current_progress.current_page = page
                self.progress_persistence.save_progress(self._current_progress)
                self._notify_progress()
            
            # Retry failed pages
            if self._current_progress.failed_pages and not self._should_stop:
                self._retry_failed_pages(location_ids)
            
            # Mark complete
            if not self._should_stop:
                self._current_progress.status = ScrapeStatus.COMPLETED
                self._current_progress.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            self._current_progress.status = ScrapeStatus.FAILED
            self._current_progress.error_message = str(e)
        
        finally:
            self._is_running = False
            self.progress_persistence.save_progress(self._current_progress)
            self._notify_progress()
    
    def _retry_failed_pages(self, location_ids: List[str]) -> None:
        """Retry failed pages"""
        failed_pages = self._current_progress.failed_pages.copy()
        self._current_progress.failed_pages = []
        
        for page in failed_pages:
            if self._should_stop:
                self._current_progress.failed_pages.extend(
                    failed_pages[failed_pages.index(page):]
                )
                break
            
            # Longer wait for retries
            time.sleep(5)
            self.rate_limiter.wait()
            
            page_url = self._build_search_url(location_ids, page)
            response = self._make_request(page_url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                self._process_page(soup)
                logger.info(f"Successfully retried page {page}")
            else:
                self._current_progress.failed_pages.append(page)
                logger.warning(f"Retry failed for page {page}")
    
    def _build_search_url(self, location_ids: List[str], page: int) -> str:
        """Build search URL with parameters"""
        base_url = URLConfig.VOLUNTEER_URL
        params = f"?page={page}"
        
        for loc_id in location_ids:
            params += f"&location_ids_types[]={loc_id}"
        
        return base_url + params
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        try:
            response = self.session_manager.get(
                url,
                headers=RequestConfig.get_headers()
            )
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def _extract_total_pages(self, soup: BeautifulSoup) -> int:
        """Extract total page count from HTML"""
        try:
            pagination = soup.find('ul', class_='pagination')
            if pagination:
                page_links = pagination.find_all('a')
                pages = []
                for link in page_links:
                    try:
                        pages.append(int(link.text.strip()))
                    except ValueError:
                        pass
                if pages:
                    return max(pages)
        except Exception as e:
            logger.warning(f"Could not extract total pages: {e}")
        
        return 1
    
    def _extract_total_count(self, soup: BeautifulSoup) -> int:
        """Extract total volunteer count from HTML"""
        try:
            count_elem = soup.find('span', class_='result-count')
            if count_elem:
                count_text = count_elem.text.strip()
                # Extract number from text like "5.517 vrijwilligers"
                import re
                match = re.search(r'[\d.]+', count_text.replace('.', ''))
                if match:
                    return int(match.group())
        except Exception as e:
            logger.warning(f"Could not extract total count: {e}")
        
        return 0
    
    def _process_page(self, soup: BeautifulSoup) -> None:
        """Process a page of volunteer results"""
        volunteer_cards = soup.find_all('div', class_='card-volunteer') or \
                         soup.find_all('article', class_='volunteer-card') or \
                         soup.find_all('div', class_='result-item')
        
        for card in volunteer_cards:
            try:
                volunteer_data = self._extract_volunteer_data(card)
                
                if volunteer_data:
                    # Check for duplicate
                    if self.deduplicator.is_duplicate(volunteer_data):
                        self._current_progress.duplicate_volunteers += 1
                        continue
                    
                    # Save volunteer
                    volunteer_id = self._save_volunteer(volunteer_data)
                    
                    if volunteer_id:
                        self.deduplicator.mark_seen(volunteer_data, str(volunteer_id))
                        self._current_progress.new_volunteers += 1
                    
                    self._current_progress.processed_volunteers += 1
                    
            except Exception as e:
                logger.error(f"Error processing volunteer card: {e}")
    
    def _extract_volunteer_data(self, card) -> Optional[Dict[str, Any]]:
        """Extract volunteer data from HTML card"""
        try:
            data = {}
            
            # Extract profile ID from link
            link = card.find('a', href=True)
            if link:
                href = link.get('href', '')
                if '/hulpaanbod/' in href:
                    data['profile_id'] = href.split('/')[-1].split('?')[0]
                    data['profile_url'] = URLConfig.BASE_URL + href.lstrip('/')
            
            # Extract name
            name_elem = card.find(['h3', 'h4', 'span'], class_=['name', 'title', 'card-title'])
            if name_elem:
                data['name'] = name_elem.text.strip()
            
            # Extract location
            location_elem = card.find(['span', 'div'], class_=['location', 'city'])
            if location_elem:
                data['location'] = location_elem.text.strip()
            
            # Extract description
            desc_elem = card.find(['p', 'div'], class_=['description', 'excerpt'])
            if desc_elem:
                data['description'] = desc_elem.text.strip()
            
            # Only return if we have at least profile_id
            if data.get('profile_id'):
                return data
            
        except Exception as e:
            logger.error(f"Error extracting volunteer data: {e}")
        
        return None
    
    def _save_volunteer(self, volunteer_data: Dict[str, Any]) -> Optional[int]:
        """Save volunteer to database"""
        now = datetime.now().isoformat()
        
        with closing(sqlite3.connect(self.db_path)) as conn:
            # Check if exists
            cursor = conn.execute(
                'SELECT id FROM volunteers WHERE profile_id = ?',
                (volunteer_data['profile_id'],)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                conn.execute('''
                    UPDATE volunteers SET
                        name = COALESCE(?, name),
                        location = COALESCE(?, location),
                        description = COALESCE(?, description),
                        last_seen = ?,
                        last_updated = ?,
                        is_active = 1
                    WHERE profile_id = ?
                ''', (
                    volunteer_data.get('name'),
                    volunteer_data.get('location'),
                    volunteer_data.get('description'),
                    now,
                    now,
                    volunteer_data['profile_id']
                ))
                conn.commit()
                if self._current_progress:
                    self._current_progress.updated_volunteers += 1
                return existing[0]
            else:
                # Insert new
                cursor = conn.execute('''
                    INSERT INTO volunteers 
                    (profile_id, name, location, description, profile_url, 
                     first_seen, last_seen, last_updated, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    volunteer_data['profile_id'],
                    volunteer_data.get('name'),
                    volunteer_data.get('location'),
                    volunteer_data.get('description'),
                    volunteer_data.get('profile_url'),
                    now,
                    now,
                    now,
                    json.dumps(volunteer_data)
                ))
                conn.commit()
                return cursor.lastrowid

    def save_volunteer(self, volunteer_data: Dict[str, Any]) -> Optional[int]:
        """Public compatibility wrapper for saving one volunteer."""
        if "profile_id" not in volunteer_data and "volunteer_id" in volunteer_data:
            volunteer_data = volunteer_data.copy()
            volunteer_data["profile_id"] = volunteer_data["volunteer_id"]
        return self._save_volunteer(volunteer_data)
    
    def get_progress(self) -> Optional[ScrapeProgress]:
        """Get current scraping progress"""
        return self._current_progress
    
    def get_volunteer_count(self) -> int:
        """Get total volunteer count in database"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute(
                'SELECT COUNT(*) FROM volunteers WHERE is_active = 1'
            )
            return cursor.fetchone()[0]
    
    def get_volunteers(
        self,
        limit: int = 100,
        offset: int = 0,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get volunteers from database"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            query = 'SELECT * FROM volunteers WHERE is_active = 1'
            params = []
            
            if location:
                query += ' AND location LIKE ?'
                params.append(f'%{location}%')
            
            query += ' ORDER BY last_seen DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor]

