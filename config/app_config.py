"""
Application Configuration for Enhanced NLvoorelkaar Tool
Centralized configuration management
"""

import os
from typing import Dict, Any

class AppConfig:
    """Application configuration class"""
    
    # Application Info
    APP_NAME = "Enhanced NLvoorelkaar Tool"
    APP_VERSION = "2.0.0"
    APP_AUTHOR = "Enhanced Development Team"
    
    # Directories
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    BACKUP_DIR = os.path.join(BASE_DIR, "backups")
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    CONFIG_DIR = os.path.join(BASE_DIR, "config")
    
    # Database Configuration
    DATABASE_CONFIG = {
        "path": os.path.join(DATA_DIR, "nlvoorelkaar.db"),
        "backup_retention_days": 30,
        "auto_cleanup_enabled": True,
        "cleanup_interval_hours": 24
    }
    
    # Scraping Configuration
    SCRAPING_CONFIG = {
        "base_url": "https://www.nlvoorelkaar.nl",
        "min_delay": 1.0,
        "max_delay": 3.0,
        "max_retries": 3,
        "timeout": 30,
        "max_concurrent_requests": 2,
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
    }
    
    # Security Configuration
    SECURITY_CONFIG = {
        "encryption_algorithm": "AES-256",
        "key_derivation_iterations": 100000,
        "salt_length": 16,
        "credential_file_permissions": 0o600,
        "data_file_permissions": 0o700
    }
    
    # UI Configuration
    UI_CONFIG = {
        "theme": "dark",
        "color_theme": "blue",
        "window_size": "1200x800",
        "min_window_size": "1000x600",
        "font_family": "Segoe UI",
        "font_sizes": {
            "large": 16,
            "medium": 12,
            "small": 10
        }
    }
    
    # Task Management Configuration
    TASK_CONFIG = {
        "max_concurrent_tasks": 3,
        "task_timeout_minutes": 30,
        "progress_update_interval": 1.0,
        "auto_cleanup_completed_tasks": True
    }
    
    # Backup Configuration
    BACKUP_CONFIG = {
        "auto_backup_enabled": True,
        "auto_backup_interval_hours": 24,
        "max_backup_files": 30,
        "backup_compression": True,
        "backup_verification": True
    }
    
    # Logging Configuration
    LOGGING_CONFIG = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file_max_size": 10 * 1024 * 1024,  # 10MB
        "file_backup_count": 5,
        "console_logging": True,
        "file_logging": True
    }
    
    # Campaign Configuration
    CAMPAIGN_CONFIG = {
        "max_campaigns": 50,
        "max_message_length": 2000,
        "default_message_templates": {
            "general": """Hello {name},

I hope this message finds you well. I came across your volunteer profile and was impressed by your interest in {categories}.

We have an opportunity that might interest you in {location}. Your skills in {skills} would be valuable for our cause.

Would you be interested in learning more about this volunteer opportunity?

Best regards""",
            
            "event": """Hi {name},

We're organizing an upcoming event in {location} and would love to have volunteers like you involved.

Given your background in {categories}, I think you'd be a great fit for this opportunity.

The event will make use of skills like {skills}, which I noticed you have experience with.

Would you be available to help out? I'd be happy to provide more details.

Looking forward to hearing from you!""",
            
            "ongoing": """Dear {name},

I hope you're doing well. We have an ongoing volunteer program in {location} that could benefit from your expertise.

Your experience with {categories} and skills in {skills} make you an ideal candidate for this opportunity.

This is a flexible commitment that can work around your schedule.

Would you be interested in discussing this further?

Best wishes"""
        }
    }
    
    @classmethod
    def get_config(cls, section: str) -> Dict[str, Any]:
        """Get configuration section"""
        config_map = {
            "database": cls.DATABASE_CONFIG,
            "scraping": cls.SCRAPING_CONFIG,
            "security": cls.SECURITY_CONFIG,
            "ui": cls.UI_CONFIG,
            "task": cls.TASK_CONFIG,
            "backup": cls.BACKUP_CONFIG,
            "logging": cls.LOGGING_CONFIG,
            "campaign": cls.CAMPAIGN_CONFIG
        }
        return config_map.get(section, {})
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        directories = [
            cls.DATA_DIR,
            cls.BACKUP_DIR,
            cls.LOG_DIR,
            cls.CONFIG_DIR
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, mode=0o700)
    
    @classmethod
    def get_database_path(cls) -> str:
        """Get database file path"""
        cls.ensure_directories()
        return cls.DATABASE_CONFIG["path"]
    
    @classmethod
    def get_log_path(cls, log_name: str = "nlvoorelkaar.log") -> str:
        """Get log file path"""
        cls.ensure_directories()
        return os.path.join(cls.LOG_DIR, log_name)
    
    @classmethod
    def get_backup_path(cls) -> str:
        """Get backup directory path"""
        cls.ensure_directories()
        return cls.BACKUP_DIR

# Environment-specific configurations
class DevelopmentConfig(AppConfig):
    """Development environment configuration"""
    
    LOGGING_CONFIG = AppConfig.LOGGING_CONFIG.copy()
    LOGGING_CONFIG["level"] = "DEBUG"
    
    SCRAPING_CONFIG = AppConfig.SCRAPING_CONFIG.copy()
    SCRAPING_CONFIG["min_delay"] = 0.5
    SCRAPING_CONFIG["max_delay"] = 1.0

class ProductionConfig(AppConfig):
    """Production environment configuration"""
    
    LOGGING_CONFIG = AppConfig.LOGGING_CONFIG.copy()
    LOGGING_CONFIG["level"] = "WARNING"
    LOGGING_CONFIG["console_logging"] = False
    
    SCRAPING_CONFIG = AppConfig.SCRAPING_CONFIG.copy()
    SCRAPING_CONFIG["min_delay"] = 2.0
    SCRAPING_CONFIG["max_delay"] = 5.0

# Configuration factory
def get_config(environment: str = "production") -> AppConfig:
    """Get configuration based on environment"""
    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "default": AppConfig
    }
    
    return config_map.get(environment, AppConfig)

