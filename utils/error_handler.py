"""
Global Error Handler
Addresses TODO items #3: Error Handling improvements
"""

import sys
import logging
import traceback
from typing import Callable, Optional, Dict, Any, Type
from functools import wraps
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    PARSING = "parsing"
    DATABASE = "database"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    PLATFORM = "platform"
    UNKNOWN = "unknown"


class AppError(Exception):
    """Base application error with additional context"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        recoverable: bool = True,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.user_message = user_message or self._get_user_friendly_message()
        self.recoverable = recoverable
        self.original_error = original_error
        self.timestamp = datetime.now()
    
    def _get_user_friendly_message(self) -> str:
        """Get a user-friendly error message"""
        messages = {
            ErrorCategory.NETWORK: "Er is een netwerkprobleem opgetreden. Controleer uw internetverbinding.",
            ErrorCategory.AUTHENTICATION: "Inloggen mislukt. Controleer uw inloggegevens.",
            ErrorCategory.PARSING: "Er is een probleem met het verwerken van de gegevens.",
            ErrorCategory.DATABASE: "Er is een databasefout opgetreden.",
            ErrorCategory.VALIDATION: "De ingevoerde gegevens zijn ongeldig.",
            ErrorCategory.CONFIGURATION: "Er is een configuratiefout opgetreden.",
            ErrorCategory.PLATFORM: "NLvoorElkaar is mogelijk gewijzigd. Neem contact op met ondersteuning.",
            ErrorCategory.UNKNOWN: "Er is een onverwachte fout opgetreden."
        }
        return messages.get(self.category, messages[ErrorCategory.UNKNOWN])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/storage"""
        return {
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'user_message': self.user_message,
            'recoverable': self.recoverable,
            'timestamp': self.timestamp.isoformat(),
            'original_error': str(self.original_error) if self.original_error else None
        }


class NetworkError(AppError):
    """Network-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class AuthenticationError(AppError):
    """Authentication-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ParsingError(AppError):
    """Parsing-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.PARSING,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class PlatformChangeError(AppError):
    """Platform change detection errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.PLATFORM,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            **kwargs
        )


class ErrorHandler:
    """
    Global error handler for the application
    Provides centralized error handling, logging, and recovery
    """
    
    _instance = None
    _error_callbacks: list = []
    _error_history: list = []
    _max_history = 100
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_global_handler()
        return cls._instance
    
    def _setup_global_handler(self) -> None:
        """Setup global exception handler"""
        sys.excepthook = self._global_exception_handler
        logger.info("Global error handler initialized")
    
    def _global_exception_handler(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_traceback
    ) -> None:
        """Handle uncaught exceptions globally"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow keyboard interrupt to pass through
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Log the error
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Create AppError wrapper
        error = AppError(
            message=str(exc_value),
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            original_error=exc_value
        )
        
        # Store in history
        self._add_to_history(error)
        
        # Notify callbacks
        self._notify_callbacks(error)
    
    def _add_to_history(self, error: AppError) -> None:
        """Add error to history"""
        self._error_history.append(error.to_dict())
        
        # Trim history if needed
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history:]
    
    def _notify_callbacks(self, error: AppError) -> None:
        """Notify registered error callbacks"""
        for callback in self._error_callbacks:
            try:
                callback(error)
            except (AttributeError, RuntimeError, TypeError, ValueError) as e:
                logger.error(f"Error in error callback: {e}")
    
    def register_callback(self, callback: Callable[[AppError], None]) -> None:
        """Register a callback for error notifications"""
        self._error_callbacks.append(callback)

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Infer a broad category for a raw exception."""
        if isinstance(error, AppError):
            return error.category
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK
        if isinstance(error, PermissionError):
            return ErrorCategory.AUTHENTICATION
        if isinstance(error, ValueError):
            return ErrorCategory.VALIDATION
        return ErrorCategory.UNKNOWN

    def get_user_message(self, category: ErrorCategory) -> str:
        """Return a user-facing message for an error category."""
        return AppError("", category=category)._get_user_friendly_message()
    
    def handle_error(
        self,
        error: Exception,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        recoverable: bool = True
    ) -> AppError:
        """
        Handle an error with proper logging and notification
        
        Args:
            error: The exception to handle
            category: Error category for classification
            severity: Error severity level
            user_message: Optional user-friendly message
            recoverable: Whether the error is recoverable
            
        Returns:
            AppError instance
        """
        # Create or wrap error
        if isinstance(error, AppError):
            app_error = error
        else:
            app_error = AppError(
                message=str(error),
                category=category,
                severity=severity,
                user_message=user_message,
                recoverable=recoverable,
                original_error=error
            )
        
        # Log based on severity
        log_message = f"[{app_error.category.value}] {app_error.message}"
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Store in history
        self._add_to_history(app_error)
        
        # Notify callbacks
        self._notify_callbacks(app_error)
        
        return app_error
    
    def get_error_history(self, limit: int = 50) -> list:
        """Get recent error history"""
        return self._error_history[-limit:]
    
    def clear_history(self) -> None:
        """Clear error history"""
        self._error_history = []


def handle_errors(
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    default_return: Any = None,
    reraise: bool = False
):
    """
    Decorator for handling errors in functions
    
    Args:
        category: Error category for classification
        severity: Error severity level
        default_return: Value to return on error (if not reraising)
        reraise: Whether to reraise the error after handling
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (AppError, AttributeError, RuntimeError, TypeError, ValueError, OSError) as e:
                handler = ErrorHandler()
                app_error = handler.handle_error(
                    error=e,
                    category=category,
                    severity=severity
                )
                
                if reraise:
                    raise app_error from e
                
                return default_return
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    *args,
    default: Any = None,
    error_message: str = "Operation failed",
    **kwargs
) -> Any:
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        *args: Arguments to pass to function
        default: Default value to return on error
        error_message: Error message for logging
        **kwargs: Keyword arguments to pass to function
        
    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except (AppError, AttributeError, RuntimeError, TypeError, ValueError, OSError) as e:
        handler = ErrorHandler()
        handler.handle_error(
            error=e,
            severity=ErrorSeverity.LOW,
            user_message=error_message
        )
        return default


# Initialize global error handler
error_handler = ErrorHandler()
