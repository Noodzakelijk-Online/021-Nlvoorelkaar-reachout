"""
Bug Fixes and Edge Case Handling
Addresses TODO items #17: Bug Fixes
"""

import re
import html
import unicodedata
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, urljoin
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# INPUT VALIDATION AND SANITIZATION
# ============================================================================

class InputValidator:
    """
    Input validation and sanitization
    
    Fixes:
    - Special characters in volunteer names
    - Invalid URLs
    - Malformed data
    """
    
    # Patterns for validation
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    PHONE_PATTERN = re.compile(
        r'^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{4,10}$'
    )
    
    URL_PATTERN = re.compile(
        r'^https?://[^\s<>"{}|\\^`\[\]]+$'
    )
    
    @staticmethod
    def sanitize_name(name: str) -> str:
        """
        Sanitize volunteer name
        
        Fixes:
        - HTML entities
        - Control characters
        - Excessive whitespace
        - Invalid Unicode
        """
        if not name:
            return ""
        
        # Decode HTML entities
        name = html.unescape(name)
        
        # Normalize Unicode
        name = unicodedata.normalize('NFKC', name)
        
        # Remove control characters
        name = ''.join(char for char in name if unicodedata.category(char) != 'Cc')
        
        # Remove excessive whitespace
        name = ' '.join(name.split())
        
        # Limit length
        if len(name) > 200:
            name = name[:200]
        
        return name.strip()
    
    @staticmethod
    def sanitize_description(description: str) -> str:
        """
        Sanitize volunteer description
        
        Fixes:
        - HTML tags
        - Script injection
        - Excessive length
        """
        if not description:
            return ""
        
        # Decode HTML entities
        description = html.unescape(description)
        
        # Remove HTML tags
        description = re.sub(r'<[^>]+>', '', description)
        
        # Remove script content
        description = re.sub(r'<script[^>]*>.*?</script>', '', description, flags=re.DOTALL | re.IGNORECASE)
        
        # Normalize whitespace
        description = re.sub(r'\s+', ' ', description)
        
        # Limit length
        if len(description) > 5000:
            description = description[:5000] + '...'
        
        return description.strip()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address"""
        if not email:
            return False
        return bool(InputValidator.EMAIL_PATTERN.match(email.strip()))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number"""
        if not phone:
            return False
        # Remove common formatting
        cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)
        return bool(InputValidator.PHONE_PATTERN.match(cleaned))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL"""
        if not url:
            return False
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except (TypeError, AttributeError, ValueError):
            return False
    
    @staticmethod
    def sanitize_url(url: str, base_url: str = 'https://www.nlvoorelkaar.nl') -> Optional[str]:
        """
        Sanitize and normalize URL
        
        Fixes:
        - Relative URLs
        - Missing protocol
        - Invalid characters
        """
        if not url:
            return None
        
        url = url.strip()
        
        # Handle relative URLs
        if url.startswith('/'):
            url = urljoin(base_url, url)
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Validate
        if InputValidator.validate_url(url):
            return url
        
        return None
    
    @staticmethod
    def sanitize_profile_id(profile_id: str) -> Optional[str]:
        """
        Sanitize profile ID
        
        Fixes:
        - Whitespace
        - Invalid characters
        """
        if not profile_id:
            return None
        
        # Remove whitespace
        profile_id = profile_id.strip()
        
        # Remove invalid characters
        profile_id = re.sub(r'[^\w\-]', '', profile_id)
        
        if not profile_id:
            return None
        
        return profile_id


# ============================================================================
# HTML PARSING FIXES
# ============================================================================

class HTMLParsingFixes:
    """
    Fixes for HTML parsing edge cases
    
    Fixes:
    - Malformed HTML
    - Missing elements
    - Changed page structure
    """
    
    @staticmethod
    def safe_find_text(element, selector: str, default: str = "") -> str:
        """
        Safely find text in HTML element
        
        Fixes:
        - Missing elements
        - Empty elements
        - Whitespace-only content
        """
        if element is None:
            return default
        
        try:
            found = element.select_one(selector)
            if found:
                text = found.get_text(strip=True)
                return text if text else default
        except (AttributeError, TypeError) as e:
            logger.debug(f"Error finding text with selector '{selector}': {e}")
        
        return default
    
    @staticmethod
    def safe_find_attr(element, selector: str, attr: str, default: str = "") -> str:
        """
        Safely find attribute in HTML element
        
        Fixes:
        - Missing elements
        - Missing attributes
        """
        if element is None:
            return default
        
        try:
            found = element.select_one(selector)
            if found and found.has_attr(attr):
                return found[attr]
        except (AttributeError, TypeError) as e:
            logger.debug(f"Error finding attr '{attr}' with selector '{selector}': {e}")
        
        return default
    
    @staticmethod
    def extract_profile_id_from_url(url: str) -> Optional[str]:
        """
        Extract profile ID from URL
        
        Handles multiple URL formats:
        - /hulpaanbod/12345
        - /profiel/12345
        - /volunteer/12345
        - ?id=12345
        """
        if not url:
            return None
        
        patterns = [
            r'/hulpaanbod/(\d+)',
            r'/profiel/(\d+)',
            r'/volunteer/(\d+)',
            r'/aanbod/(\d+)',
            r'\?id=(\d+)',
            r'/(\d+)/?$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def parse_availability(text: str) -> Dict[str, Any]:
        """
        Parse availability text into structured data
        
        Handles formats:
        - "Maandag t/m vrijdag"
        - "Weekenden"
        - "Flexibel"
        - "2-4 uur per week"
        """
        result = {
            'days': [],
            'hours_per_week': None,
            'flexible': False,
            'raw': text
        }
        
        if not text:
            return result
        
        text_lower = text.lower()
        
        # Check for flexible
        if 'flexibel' in text_lower or 'overleg' in text_lower:
            result['flexible'] = True
        
        # Parse days
        day_patterns = {
            'maandag': 'monday',
            'dinsdag': 'tuesday',
            'woensdag': 'wednesday',
            'donderdag': 'thursday',
            'vrijdag': 'friday',
            'zaterdag': 'saturday',
            'zondag': 'sunday',
            'weekend': ['saturday', 'sunday'],
            'doordeweeks': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        }
        
        for dutch, english in day_patterns.items():
            if dutch in text_lower:
                if isinstance(english, list):
                    result['days'].extend(english)
                else:
                    result['days'].append(english)
        
        # Parse hours
        hours_match = re.search(r'(\d+)[\s\-]+(\d+)?\s*uur', text_lower)
        if hours_match:
            min_hours = int(hours_match.group(1))
            max_hours = int(hours_match.group(2)) if hours_match.group(2) else min_hours
            result['hours_per_week'] = (min_hours + max_hours) / 2
        
        return result


# ============================================================================
# SESSION HANDLING FIXES
# ============================================================================

class SessionFixes:
    """
    Fixes for session handling edge cases
    
    Fixes:
    - Session expiration detection
    - Login redirect handling
    - Cookie issues
    """
    
    LOGIN_INDICATORS = [
        '/login',
        '/inloggen',
        'Inloggen',
        'Log in',
        'niet ingelogd',
        'sessie verlopen'
    ]
    
    @staticmethod
    def is_login_required(response) -> bool:
        """
        Check if response indicates login is required
        
        Fixes:
        - Redirect to login page
        - Login form in response
        - Session expired messages
        """
        # Check URL redirect
        if hasattr(response, 'url'):
            url_str = str(response.url).lower()
            if any(indicator.lower() in url_str for indicator in ['/login', '/inloggen']):
                return True
        
        # Check response content
        if hasattr(response, 'text'):
            content = response.text.lower()
            
            # Check for login form
            if '<form' in content and ('inloggen' in content or 'wachtwoord' in content):
                # Make sure it's not just a page with a login link
                if 'type="password"' in content:
                    return True
            
            # Check for session expired message
            if 'sessie verlopen' in content or 'opnieuw inloggen' in content:
                return True
        
        return False
    
    @staticmethod
    def extract_csrf_token(html_content: str) -> Optional[str]:
        """
        Extract CSRF token from HTML
        
        Handles multiple token formats:
        - <input name="_token" value="...">
        - <meta name="csrf-token" content="...">
        - window.csrfToken = "..."
        """
        patterns = [
            r'<input[^>]*name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'<input[^>]*value=["\']([^"\']+)["\'][^>]*name=["\']_token["\']',
            r'<meta[^>]*name=["\']csrf-token["\'][^>]*content=["\']([^"\']+)["\']',
            r'window\.csrfToken\s*=\s*["\']([^"\']+)["\']',
            r'"_token"\s*:\s*"([^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None


# ============================================================================
# DATA CONSISTENCY FIXES
# ============================================================================

class DataConsistencyFixes:
    """
    Fixes for data consistency issues
    
    Fixes:
    - Duplicate records
    - Orphaned records
    - Data integrity
    """
    
    @staticmethod
    def merge_volunteer_records(existing: Dict, new: Dict) -> Dict:
        """
        Merge two volunteer records intelligently
        
        Fixes:
        - Preserving non-null values
        - Updating timestamps correctly
        - Handling conflicting data
        """
        merged = existing.copy()
        
        # Fields to always update if new value exists
        update_fields = [
            'name', 'location', 'description', 'skills',
            'availability', 'contact_info', 'profile_url'
        ]
        
        for field in update_fields:
            new_value = new.get(field)
            if new_value and str(new_value).strip():
                merged[field] = new_value
        
        # Always update last_seen
        merged['last_seen'] = new.get('last_seen', merged.get('last_seen'))
        
        # Keep earliest first_seen
        if existing.get('first_seen') and new.get('first_seen'):
            merged['first_seen'] = min(existing['first_seen'], new['first_seen'])
        
        # Update is_active based on new data
        if 'is_active' in new:
            merged['is_active'] = new['is_active']
        
        return merged
    
    @staticmethod
    def detect_duplicate_volunteers(volunteers: List[Dict]) -> List[List[Dict]]:
        """
        Detect potential duplicate volunteers
        
        Uses multiple criteria:
        - Same profile_id
        - Similar name + location
        - Same contact info
        """
        duplicates = []
        seen = {}
        
        for vol in volunteers:
            # Check by profile_id
            profile_id = vol.get('profile_id')
            if profile_id:
                if profile_id in seen:
                    duplicates.append([seen[profile_id], vol])
                else:
                    seen[profile_id] = vol
            
            # Check by name + location
            name = vol.get('name', '').lower().strip()
            location = vol.get('location', '').lower().strip()
            if name and location:
                key = f"{name}|{location}"
                if key in seen:
                    duplicates.append([seen[key], vol])
                else:
                    seen[key] = vol
        
        return duplicates


# ============================================================================
# ERROR RECOVERY
# ============================================================================

class ErrorRecovery:
    """
    Error recovery mechanisms
    
    Fixes:
    - Graceful degradation
    - Partial data recovery
    - Automatic retry with backoff
    """
    
    @staticmethod
    def recover_partial_scrape(db_path: str) -> Dict[str, Any]:
        """
        Recover from partial scrape failure
        
        Returns:
        - Last successful page
        - Volunteers found so far
        - Recommended resume point
        """
        import sqlite3
        
        result = {
            'last_page': 0,
            'volunteers_found': 0,
            'resume_page': 1,
            'session_id': None
        }
        
        try:
            with sqlite3.connect(db_path) as conn:
                # Find last incomplete session
                cursor = conn.execute('''
                    SELECT id, current_page, volunteers_found
                    FROM scrape_sessions
                    WHERE status IN ('in_progress', 'interrupted')
                    ORDER BY last_updated DESC
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                
                if row:
                    result['session_id'] = row[0]
                    result['last_page'] = row[1] or 0
                    result['volunteers_found'] = row[2] or 0
                    result['resume_page'] = result['last_page'] + 1
        
        except (sqlite3.DatabaseError, TypeError, ValueError) as e:
            logger.error(f"Error recovering partial scrape: {e}")
        
        return result
    
    @staticmethod
    def safe_database_operation(func):
        """
        Decorator for safe database operations
        
        Fixes:
        - Connection errors
        - Lock timeouts
        - Transaction rollback
        """
        def wrapper(*args, **kwargs):
            import sqlite3
            max_retries = 3
            retry_delay = 1.0
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if 'locked' in str(e).lower() and attempt < max_retries - 1:
                        import time
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    raise
            
            return None
        
        return wrapper


# ============================================================================
# UNICODE AND ENCODING FIXES
# ============================================================================

class EncodingFixes:
    """
    Fixes for encoding and Unicode issues
    
    Fixes:
    - UTF-8 encoding errors
    - Special Dutch characters
    - Emoji handling
    """
    
    @staticmethod
    def safe_encode(text: str, encoding: str = 'utf-8') -> bytes:
        """Safely encode text to bytes"""
        if not text:
            return b''
        
        try:
            return text.encode(encoding)
        except UnicodeEncodeError:
            # Replace problematic characters
            return text.encode(encoding, errors='replace')
    
    @staticmethod
    def safe_decode(data: bytes, encoding: str = 'utf-8') -> str:
        """Safely decode bytes to text"""
        if not data:
            return ''
        
        # Try multiple encodings
        encodings = [encoding, 'utf-8', 'latin-1', 'cp1252']
        
        for enc in encodings:
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        
        # Last resort: decode with replacement
        return data.decode('utf-8', errors='replace')
    
    @staticmethod
    def normalize_dutch_text(text: str) -> str:
        """
        Normalize Dutch text
        
        Handles:
        - Diacritics (é, ë, etc.)
        - IJ ligature
        - Common abbreviations
        """
        if not text:
            return ''
        
        # Normalize Unicode
        text = unicodedata.normalize('NFC', text)
        
        # Handle IJ ligature
        text = text.replace('Ĳ', 'IJ').replace('ĳ', 'ij')
        
        return text
    
    @staticmethod
    def remove_emoji(text: str) -> str:
        """Remove emoji from text"""
        if not text:
            return ''
        
        # Remove emoji using Unicode categories
        return ''.join(
            char for char in text
            if unicodedata.category(char) not in ('So', 'Sk')
        )


# ============================================================================
# PAGINATION FIXES
# ============================================================================

class PaginationFixes:
    """
    Fixes for pagination edge cases
    
    Fixes:
    - Last page detection
    - Empty pages
    - Page number extraction
    """
    
    @staticmethod
    def extract_total_pages(html_content: str) -> int:
        """
        Extract total pages from pagination
        
        Handles multiple formats:
        - "Pagina 1 van 100"
        - "1 / 100"
        - Last page link
        """
        patterns = [
            r'pagina\s*\d+\s*van\s*(\d+)',
            r'page\s*\d+\s*of\s*(\d+)',
            r'\d+\s*/\s*(\d+)',
            r'data-total-pages=["\'](\d+)["\']',
            r'"totalPages"\s*:\s*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Try to find last page link
        last_page_match = re.search(
            r'<a[^>]*href=[^>]*page=(\d+)[^>]*>[^<]*(?:laatste|last)',
            html_content,
            re.IGNORECASE
        )
        if last_page_match:
            return int(last_page_match.group(1))
        
        return 1
    
    @staticmethod
    def is_empty_page(html_content: str, expected_selector: str = '.volunteer-card') -> bool:
        """
        Check if page has no results
        
        Fixes:
        - Empty result detection
        - "No results" message detection
        """
        # Check for no results message
        no_results_patterns = [
            'geen resultaten',
            'no results',
            'niets gevonden',
            'nothing found'
        ]
        
        content_lower = html_content.lower()
        for pattern in no_results_patterns:
            if pattern in content_lower:
                return True
        
        # Check if expected elements exist
        if expected_selector not in html_content:
            return True
        
        return False
    
    @staticmethod
    def get_next_page_url(html_content: str, current_url: str) -> Optional[str]:
        """
        Extract next page URL
        
        Handles:
        - Relative URLs
        - Query parameters
        - JavaScript pagination
        """
        patterns = [
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(?:volgende|next|›|»)',
            r'<a[^>]*class=["\'][^"\']*next[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
            r'"nextPage"\s*:\s*"([^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                next_url = match.group(1)
                return InputValidator.sanitize_url(next_url, current_url)
        
        return None
