"""
Centralized logging configuration for the SRC to Application Generator.

This module sets up structured logging with support for file rotation,
different log levels, and integration with LangSmith for observability.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from rich.console import Console
from rich.logging import RichHandler

from config.config import get_settings


# Global console for rich formatting
console = Console()


def setup_logging() -> None:
    """
    Set up centralized logging configuration with structured logging.
    
    Configures both standard Python logging and structlog for structured
    logging with file rotation and console output.
    """
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure log level
    log_level = getattr(logging, settings.logging.level.upper(), logging.INFO)
    
    # Remove existing handlers
    logging.getLogger().handlers.clear()
    
    # Configure formatters
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler with rich formatting
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True
    )
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    
    # Main application log file with rotation
    main_file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "src_generator.log",
        maxBytes=settings.logging.file_max_size_mb * 1024 * 1024,
        backupCount=settings.logging.file_backup_count,
        encoding="utf-8"
    )
    main_file_handler.setLevel(log_level)
    main_file_handler.setFormatter(file_formatter)
    
    # Agent-specific log file
    agent_file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "agents.log",
        maxBytes=settings.logging.file_max_size_mb * 1024 * 1024,
        backupCount=settings.logging.file_backup_count,
        encoding="utf-8"
    )
    agent_file_handler.setLevel(log_level)
    agent_file_handler.setFormatter(file_formatter)
    
    # Error log file for errors and critical messages
    error_file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "errors.log",
        maxBytes=settings.logging.file_max_size_mb * 1024 * 1024,
        backupCount=settings.logging.file_backup_count,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(file_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(main_file_handler)
    root_logger.addHandler(error_file_handler)
    
    # Configure agent logger
    agent_logger = logging.getLogger("agents")
    agent_logger.addHandler(agent_file_handler)
    agent_logger.propagate = False  # Don't propagate to root logger
    agent_logger.setLevel(log_level)
    
    # Configure structured logging if enabled
    if settings.logging.format.lower() == "structured":
        _setup_structured_logging()
    
    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("autogen").setLevel(logging.INFO)
    
    # Log startup message
    logger = get_logger(__name__)
    logger.info(
        "Logging configuration initialized",
        extra={
            "log_level": settings.logging.level,
            "log_format": settings.logging.format,
            "environment": settings.environment
        }
    )


def _setup_structured_logging() -> None:
    """Set up structlog for structured logging."""
    
    def add_logger_name(logger, method_name, event_dict):
        """Add logger name to log events."""
        event_dict["logger"] = logger.name
        return event_dict
    
    def add_log_level(logger, method_name, event_dict):
        """Add log level to log events."""
        event_dict["level"] = method_name.upper()
        return event_dict
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_logger_name,
            add_log_level,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name, typically __name__
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_agent_event(
    agent_name: str,
    event_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    level: str = "INFO"
) -> None:
    """
    Log agent-specific events with structured data.
    
    Args:
        agent_name: Name of the agent
        event_type: Type of event (e.g., "START", "COMPLETE", "ERROR")
        message: Event message
        details: Additional event details
        level: Log level
    """
    logger = get_logger("agents")
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    extra_data = {
        "agent_name": agent_name,
        "event_type": event_type,
        "details": details or {}
    }
    
    logger.log(log_level, message, extra=extra_data)


def log_processing_step(
    step_name: str,
    status: str,
    duration: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log processing step events.
    
    Args:
        step_name: Name of the processing step
        status: Status of the step (e.g., "START", "COMPLETE", "FAILED")
        duration: Step duration in seconds
        details: Additional step details
    """
    logger = get_logger("processing")
    
    extra_data = {
        "step_name": step_name,
        "status": status,
        "duration": duration,
        "details": details or {}
    }
    
    if status.upper() == "FAILED":
        logger.error(f"Processing step failed: {step_name}", extra=extra_data)
    elif status.upper() == "COMPLETE":
        logger.info(f"Processing step completed: {step_name}", extra=extra_data)
    else:
        logger.info(f"Processing step {status.lower()}: {step_name}", extra=extra_data)


def log_human_interaction(
    interaction_type: str,
    user_action: str,
    context: Dict[str, Any]
) -> None:
    """
    Log human-in-the-loop interactions.
    
    Args:
        interaction_type: Type of interaction (e.g., "APPROVAL", "FEEDBACK", "EDIT")
        user_action: Action taken by the user
        context: Interaction context
    """
    logger = get_logger("human_interaction")
    
    extra_data = {
        "interaction_type": interaction_type,
        "user_action": user_action,
        "context": context
    }
    
    logger.info(f"Human interaction: {interaction_type}", extra=extra_data)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log info message with extra data."""
        self.logger.info(message, extra=kwargs)
    
    def log_error(self, message: str, **kwargs) -> None:
        """Log error message with extra data."""
        self.logger.error(message, extra=kwargs)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message with extra data."""
        self.logger.warning(message, extra=kwargs)
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message with extra data."""
        self.logger.debug(message, extra=kwargs)