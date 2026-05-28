"""
Enhanced Session Manager with timeout handling, retry logic, and connection pooling.
Addresses TODO items #1: Session Management Improvements
"""

import requests
import logging
import time
from typing import Optional, Dict, Any
from functools import wraps
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class SessionConfig:
    """Configuration for session management"""
    
    # Timeout settings (in seconds)
    CONNECT_TIMEOUT = 10
    READ_TIMEOUT = 30
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 0.5
    RETRY_STATUS_CODES = [429, 500, 502, 503, 504]
    
    # Rate limiting
    MIN_REQUEST_INTERVAL = 1.0  # Minimum seconds between requests
    
    # Session refresh
    SESSION_MAX_AGE = 3600  # Refresh session after 1 hour
    
    # Connection pooling
    POOL_CONNECTIONS = 10
    POOL_MAXSIZE = 20


def retry_on_failure(max_retries: int = 3, backoff_factor: float = 0.5):
    """Decorator for retrying failed requests with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, ConnectionError) as e:
                    last_exception = e
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
            
            logger.error(f"All {max_retries} retry attempts failed")
            raise last_exception
        return wrapper
    return decorator


class EnhancedSessionManager:
    """
    Enhanced session manager with:
    - Connection pooling for better performance
    - Automatic retry with exponential backoff
    - Session timeout handling
    - Rate limiting to prevent blocking
    - Automatic session refresh
    """
    
    _instance = None
    _session: Optional[requests.Session] = None
    _session_created_at: float = 0
    _last_request_time: float = 0
    _request_count: int = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_session(cls) -> requests.Session:
        """Get or create a session with proper configuration"""
        current_time = time.time()
        
        # Check if session needs refresh
        if cls._session is None or cls._should_refresh_session(current_time):
            cls._create_session()
        
        return cls._session
    
    @classmethod
    def _should_refresh_session(cls, current_time: float) -> bool:
        """Check if session should be refreshed"""
        if cls._session is None:
            return True
        
        session_age = current_time - cls._session_created_at
        return session_age > SessionConfig.SESSION_MAX_AGE
    
    @classmethod
    def _create_session(cls) -> None:
        """Create a new session with retry logic and connection pooling"""
        logger.info("Creating new session with enhanced configuration")
        
        # Close existing session if any
        if cls._session is not None:
            try:
                cls._session.close()
            except Exception as e:
                logger.warning(f"Error closing existing session: {e}")
        
        # Create new session
        cls._session = requests.Session()
        cls._session_created_at = time.time()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=SessionConfig.MAX_RETRIES,
            backoff_factor=SessionConfig.RETRY_BACKOFF_FACTOR,
            status_forcelist=SessionConfig.RETRY_STATUS_CODES,
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=SessionConfig.POOL_CONNECTIONS,
            pool_maxsize=SessionConfig.POOL_MAXSIZE
        )
        
        # Mount adapter for both HTTP and HTTPS
        cls._session.mount("http://", adapter)
        cls._session.mount("https://", adapter)
        
        logger.info("Session created successfully with retry and pooling configuration")
    
    @classmethod
    def _apply_rate_limiting(cls) -> None:
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - cls._last_request_time
        
        if time_since_last_request < SessionConfig.MIN_REQUEST_INTERVAL:
            sleep_time = SessionConfig.MIN_REQUEST_INTERVAL - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        cls._last_request_time = time.time()
        cls._request_count += 1

    @classmethod
    def _apply_rate_limit(cls) -> None:
        """Backward-compatible alias for older tests and callers."""
        cls._apply_rate_limiting()
    
    @classmethod
    @retry_on_failure(max_retries=SessionConfig.MAX_RETRIES)
    def get(cls, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        Make a GET request with automatic retry and rate limiting
        
        Args:
            url: The URL to request
            headers: Optional headers to include
            **kwargs: Additional arguments passed to requests.get
            
        Returns:
            requests.Response object
        """
        cls._apply_rate_limiting()
        session = cls.get_session()
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = (SessionConfig.CONNECT_TIMEOUT, SessionConfig.READ_TIMEOUT)
        
        logger.debug(f"GET request to {url}")
        response = session.get(url, headers=headers, **kwargs)
        
        # Check for session expiration indicators
        if cls._is_session_expired(response):
            logger.warning("Session appears to be expired, refreshing...")
            cls._session = None
            session = cls.get_session()
            response = session.get(url, headers=headers, **kwargs)
        
        return response

    @classmethod
    def get_with_retry(cls, url: str, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Backward-compatible alias for GET requests with retry behavior."""
        return cls.get(url, headers=headers, **kwargs)
    
    @classmethod
    @retry_on_failure(max_retries=SessionConfig.MAX_RETRIES)
    def post(cls, url: str, data: Optional[Dict] = None, headers: Optional[Dict] = None, **kwargs) -> requests.Response:
        """
        Make a POST request with automatic retry and rate limiting
        
        Args:
            url: The URL to request
            data: Optional data to post
            headers: Optional headers to include
            **kwargs: Additional arguments passed to requests.post
            
        Returns:
            requests.Response object
        """
        cls._apply_rate_limiting()
        session = cls.get_session()
        
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = (SessionConfig.CONNECT_TIMEOUT, SessionConfig.READ_TIMEOUT)
        
        logger.debug(f"POST request to {url}")
        response = session.post(url, data=data, headers=headers, **kwargs)
        
        # Check for session expiration indicators
        if cls._is_session_expired(response):
            logger.warning("Session appears to be expired, refreshing...")
            cls._session = None
            session = cls.get_session()
            response = session.post(url, data=data, headers=headers, **kwargs)
        
        return response
    
    @classmethod
    def _is_session_expired(cls, response: requests.Response) -> bool:
        """
        Check if the response indicates an expired session
        
        Args:
            response: The response to check
            
        Returns:
            True if session appears expired, False otherwise
        """
        # Check for redirect to login page
        if response.history:
            for r in response.history:
                if 'inloggen' in r.url or 'login' in r.url:
                    return True
        
        # Check current URL
        if 'inloggen' in response.url or 'login' in response.url:
            return True
        
        # Check for 401 or 403 status codes
        if response.status_code in [401, 403]:
            return True
        
        return False
    
    @classmethod
    def close(cls) -> None:
        """Close the session and clean up resources"""
        if cls._session is not None:
            try:
                cls._session.close()
                logger.info("Session closed successfully")
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                cls._session = None
                cls._session_created_at = 0
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get session statistics"""
        return {
            'request_count': cls._request_count,
            'session_age': time.time() - cls._session_created_at if cls._session else 0,
            'session_active': cls._session is not None
        }
    
    @classmethod
    def reset(cls) -> None:
        """Reset the session manager completely"""
        cls.close()
        cls._request_count = 0
        cls._last_request_time = 0
        logger.info("Session manager reset")


# Backward compatibility - alias for existing code
class SessionManager:
    """Backward compatible wrapper for EnhancedSessionManager"""
    
    @staticmethod
    def get_session() -> requests.Session:
        return EnhancedSessionManager.get_session()
