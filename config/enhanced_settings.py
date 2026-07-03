"""
Enhanced Configuration Settings
Addresses TODO items related to configuration management and security
"""

import os
from dataclasses import dataclass
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class RequestConfig:
    """Configuration for HTTP requests"""
    
    # Updated User-Agent (Chrome 120 - December 2024)
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # Request headers
    HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    @classmethod
    def get_headers(cls) -> dict:
        """Get headers with current User-Agent"""
        headers = cls.HEADERS.copy()
        headers['User-Agent'] = cls.USER_AGENT
        return headers


@dataclass
class URLConfig:
    """URL configuration for NLvoorElkaar"""
    
    BASE_URL = 'https://www.nlvoorelkaar.nl/'
    VOLUNTEER_URL = f'{BASE_URL}hulpaanbod/'
    AUTOCOMPLETE_URL = f'{BASE_URL}location/autocomplete?s=3&term='
    LOGOUT_URL = f'{BASE_URL}uitloggen'
    LOGIN_PAGE_URL = f'{BASE_URL}inloggen'
    LOGIN_CHECK_URL = f'{BASE_URL}login_check'
    MESSAGES_URL = f'{BASE_URL}mijn-pagina/berichten'
    PROFILE_URL = f'{BASE_URL}mijn-pagina/profiel'
    
    # API endpoints discovered during testing
    API_SETTINGS_URL = f'{BASE_URL}api/site/settings'
    RESULT_MARKERS_URL = f'{BASE_URL}aanbod/update/resultmarkers.json'
    MARKER_DETAILS_URL = f'{BASE_URL}aanbod/update/markerdetails.json'


@dataclass
class TimingConfig:
    """Timing configuration for rate limiting and delays"""
    
    # Delay before starting message sending (randomized)
    DELAY_TO_START_MIN = 10.0
    DELAY_TO_START_MAX = 30.0
    
    # Delay between messages (randomized)
    MESSAGE_DELAY_MIN = 30
    MESSAGE_DELAY_MAX = 60
    
    # Delay between page requests
    PAGE_REQUEST_DELAY_MIN = 1.0
    PAGE_REQUEST_DELAY_MAX = 3.0
    
    # Reminder delays
    REMINDER_DELAY_MIN = 45
    REMINDER_DELAY_MAX = 75
    
    # Rate limiting
    REQUESTS_PER_MINUTE = 20
    MIN_REQUEST_INTERVAL = 1.0


@dataclass
class DatabaseConfig:
    """Database configuration"""
    
    DB_NAME = 'nlvoorelkaar.db'
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', DB_NAME)
    
    # Backup settings
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
    MAX_BACKUPS = 10
    AUTO_BACKUP_INTERVAL = 86400  # 24 hours in seconds


@dataclass
class LoggingConfig:
    """Logging configuration"""
    
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    LOG_FILE = 'nlvoorelkaar.log'
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5


@dataclass
class AppConfig:
    """Application configuration"""
    
    APP_NAME = 'NLvoorElkaar Outreach Tool'
    APP_VERSION = '3.1.0'
    
    # UI settings
    WINDOW_WIDTH = 1300
    WINDOW_HEIGHT = 700
    THEME = 'dark'  # 'dark' or 'light'
    
    # Feature flags
    ENABLE_AUTO_BACKUP = True
    ENABLE_NOTIFICATIONS = True
    ENABLE_ANALYTICS = True
    
    # Sync settings
    SYNC_TIME = '02:00'  # Default daily sync time
    SYNC_ENABLED = True


class ConfigManager:
    """
    Centralized configuration manager
    Loads configuration from environment variables and config files
    """
    
    _instance = None
    _config_file = 'config.json'
    _config_data: dict = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """Load configuration from file and environment"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self._config_file
        )
        
        # Load from file if exists
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self._config_data = json.load(f)
                logger.info(f"Configuration loaded from {config_path}")
            except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error loading config file: {e}")
                self._config_data = {}
        
        # Override with environment variables
        self._load_env_overrides()
    
    def _load_env_overrides(self) -> None:
        """Load configuration overrides from environment variables"""
        env_mappings = {
            'NLVE_SYNC_TIME': ('sync', 'time'),
            'NLVE_SYNC_ENABLED': ('sync', 'enabled'),
            'NLVE_THEME': ('ui', 'theme'),
            'NLVE_LOG_LEVEL': ('logging', 'level'),
            'NLVE_AUTO_BACKUP': ('backup', 'enabled'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                self._set_nested(config_path, value)
    
    def _set_nested(self, path: tuple, value: str) -> None:
        """Set a nested configuration value"""
        current = self._config_data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Convert value to appropriate type
        if value.lower() in ('true', 'false'):
            value = value.lower() == 'true'
        elif value.isdigit():
            value = int(value)
        
        current[path[-1]] = value
    
    def get(self, key: str, default: Optional[any] = None) -> any:
        """Get a configuration value"""
        keys = key.split('.')
        current = self._config_data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def set(self, key: str, value: any) -> None:
        """Set a configuration value"""
        keys = key.split('.')
        self._set_nested(tuple(keys), str(value) if not isinstance(value, (bool, int, float)) else value)
    
    def save(self) -> bool:
        """Save configuration to file"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self._config_file
        )
        
        try:
            with open(config_path, 'w') as f:
                json.dump(self._config_data, f, indent=2)
            logger.info(f"Configuration saved to {config_path}")
            return True
        except (OSError, TypeError, ValueError) as e:
            logger.error(f"Error saving config: {e}")
            return False


# Backward compatibility - expose old-style variables
headers = RequestConfig.get_headers()
url_base = URLConfig.BASE_URL
url_volunteer = URLConfig.VOLUNTEER_URL
url_autocomplete = URLConfig.AUTOCOMPLETE_URL
url_logout = URLConfig.LOGOUT_URL
url_login_page = URLConfig.LOGIN_PAGE_URL
url_login = URLConfig.LOGIN_CHECK_URL
delay_to_start_sending = (TimingConfig.DELAY_TO_START_MIN + TimingConfig.DELAY_TO_START_MAX) / 2
minimum_time = TimingConfig.MESSAGE_DELAY_MIN
maximum_time = TimingConfig.MESSAGE_DELAY_MAX
