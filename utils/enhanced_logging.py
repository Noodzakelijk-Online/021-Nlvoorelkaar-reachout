"""
Enhanced Logging System
Addresses TODO items #16: Architecture Improvements - Logging levels
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional
import json


class LogFormatter(logging.Formatter):
    """Custom log formatter with color support for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, use_colors: bool = True, include_location: bool = False):
        self.use_colors = use_colors
        self.include_location = include_location
        
        if include_location:
            fmt = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        else:
            fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        super().__init__(fmt, datefmt='%Y-%m-%d %H:%M:%S')
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional colors"""
        formatted = super().format(record)
        
        if self.use_colors and sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            formatted = f"{color}{formatted}{self.COLORS['RESET']}"
        
        return formatted


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        return json.dumps(log_data)


class LoggerManager:
    """
    Centralized logging manager
    
    Features:
    - Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - File rotation by size and time
    - Console and file output
    - JSON structured logging option
    - Performance logging
    """
    
    _instance = None
    _initialized = False
    
    # Default configuration
    DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    DEFAULT_LOG_FILE = 'nlvoorelkaar.log'
    DEFAULT_ERROR_FILE = 'errors.log'
    DEFAULT_LEVEL = logging.INFO
    DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    DEFAULT_BACKUP_COUNT = 5
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._loggers = {}
        self._log_dir = self.DEFAULT_LOG_DIR
        self._ensure_log_directory()
    
    def _ensure_log_directory(self) -> None:
        """Ensure log directory exists"""
        os.makedirs(self._log_dir, exist_ok=True)
    
    def configure(
        self,
        log_dir: Optional[str] = None,
        level: int = DEFAULT_LEVEL,
        console_output: bool = True,
        file_output: bool = True,
        json_output: bool = False,
        max_bytes: int = DEFAULT_MAX_BYTES,
        backup_count: int = DEFAULT_BACKUP_COUNT
    ) -> None:
        """
        Configure the logging system
        
        Args:
            log_dir: Directory for log files
            level: Minimum log level
            console_output: Enable console output
            file_output: Enable file output
            json_output: Use JSON format for file output
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        if log_dir:
            self._log_dir = log_dir
            self._ensure_log_directory()
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
        
        # Add console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(LogFormatter(use_colors=True))
            root_logger.addHandler(console_handler)
        
        # Add file handler
        if file_output:
            log_path = os.path.join(self._log_dir, self.DEFAULT_LOG_FILE)
            
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setLevel(level)
            
            if json_output:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(LogFormatter(use_colors=False, include_location=True))
            
            root_logger.addHandler(file_handler)
            
            # Add separate error log file
            error_path = os.path.join(self._log_dir, self.DEFAULT_ERROR_FILE)
            error_handler = RotatingFileHandler(
                error_path,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(LogFormatter(use_colors=False, include_location=True))
            root_logger.addHandler(error_handler)
        
        logging.info("Logging system configured")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create a logger
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            Logger instance
        """
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        
        return self._loggers[name]
    
    def set_level(self, level: int, logger_name: Optional[str] = None) -> None:
        """
        Set log level
        
        Args:
            level: Log level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
            logger_name: Optional specific logger name, or None for root
        """
        if logger_name:
            logging.getLogger(logger_name).setLevel(level)
        else:
            logging.getLogger().setLevel(level)
    
    def add_file_handler(
        self,
        filename: str,
        level: int = logging.DEBUG,
        max_bytes: int = DEFAULT_MAX_BYTES,
        backup_count: int = DEFAULT_BACKUP_COUNT
    ) -> None:
        """
        Add an additional file handler
        
        Args:
            filename: Log file name
            level: Minimum log level for this handler
            max_bytes: Maximum file size before rotation
            backup_count: Number of backup files
        """
        log_path = os.path.join(self._log_dir, filename)
        
        handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        handler.setLevel(level)
        handler.setFormatter(LogFormatter(use_colors=False, include_location=True))
        
        logging.getLogger().addHandler(handler)
    
    def add_daily_handler(
        self,
        filename: str,
        level: int = logging.INFO,
        backup_count: int = 30
    ) -> None:
        """
        Add a daily rotating file handler
        
        Args:
            filename: Base log file name
            level: Minimum log level
            backup_count: Number of days to keep logs
        """
        log_path = os.path.join(self._log_dir, filename)
        
        handler = TimedRotatingFileHandler(
            log_path,
            when='midnight',
            interval=1,
            backupCount=backup_count
        )
        handler.setLevel(level)
        handler.setFormatter(LogFormatter(use_colors=False, include_location=True))
        handler.suffix = '%Y-%m-%d'
        
        logging.getLogger().addHandler(handler)


class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self, name: str = 'performance'):
        self.logger = logging.getLogger(name)
        self._timers = {}
    
    def start_timer(self, operation: str) -> None:
        """Start a timer for an operation"""
        self._timers[operation] = datetime.now()
    
    def end_timer(self, operation: str, log_level: int = logging.DEBUG) -> float:
        """
        End a timer and log the duration
        
        Args:
            operation: Operation name
            log_level: Level to log at
            
        Returns:
            Duration in seconds
        """
        if operation not in self._timers:
            return 0.0
        
        start_time = self._timers.pop(operation)
        duration = (datetime.now() - start_time).total_seconds()
        
        self.logger.log(
            log_level,
            f"Operation '{operation}' completed in {duration:.3f}s"
        )
        
        return duration
    
    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = '',
        level: int = logging.INFO
    ) -> None:
        """
        Log a performance metric
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Optional unit of measurement
            level: Log level
        """
        message = f"Metric '{metric_name}': {value}"
        if unit:
            message += f" {unit}"
        
        self.logger.log(level, message)


# Convenience functions
def setup_logging(
    level: int = logging.INFO,
    console: bool = True,
    file: bool = True,
    log_file: Optional[str] = None
) -> logging.Logger:
    """Quick setup for logging"""
    manager = LoggerManager()
    log_dir = os.path.dirname(log_file) if log_file else None
    if log_file:
        manager.DEFAULT_LOG_FILE = os.path.basename(log_file)
    manager.configure(
        log_dir=log_dir,
        level=level,
        console_output=console,
        file_output=file
    )
    return logging.getLogger()


def get_logger(name: str) -> logging.Logger:
    """Get a logger by name"""
    return LoggerManager().get_logger(name)


# Initialize logging on import
logger_manager = LoggerManager()
