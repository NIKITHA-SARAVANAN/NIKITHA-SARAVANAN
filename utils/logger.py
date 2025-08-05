"""
Logging utilities for the SRS to Angular+FastAPI generator.

This module provides structured logging capabilities with support for agent
activity tracking, performance monitoring, and integration with external
logging services like LangSmith.
"""

import logging
import json
import time
from typing import Any, Dict, Optional, Union
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from functools import wraps

from config.config import settings


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted logs with additional metadata.
    
    This logger adds context information like timestamps, request IDs, agent names,
    and custom fields to all log messages.
    """
    
    def __init__(self, name: str, extra_fields: Optional[Dict[str, Any]] = None):
        """
        Initialize the structured logger.
        
        Args:
            name: Logger name (usually module name)
            extra_fields: Additional fields to include in all log messages
        """
        self.logger = logging.getLogger(name)
        self.extra_fields = extra_fields or {}
        self.context = {}
    
    def _format_message(
        self, 
        level: str, 
        message: str, 
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format log message with structured data."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "logger": self.logger.name,
            "message": message,
            **self.extra_fields,
            **self.context
        }
        
        if extra:
            log_data.update(extra)
        
        return log_data
    
    def set_context(self, **kwargs):
        """Set context fields that will be included in all subsequent log messages."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context fields."""
        self.context.clear()
    
    def debug(self, message: str, **extra):
        """Log debug message."""
        if self.logger.isEnabledFor(logging.DEBUG):
            log_data = self._format_message("DEBUG", message, extra)
            self.logger.debug(json.dumps(log_data) if settings.log_format.value == "json" else message)
    
    def info(self, message: str, **extra):
        """Log info message."""
        if self.logger.isEnabledFor(logging.INFO):
            log_data = self._format_message("INFO", message, extra)
            self.logger.info(json.dumps(log_data) if settings.log_format.value == "json" else message)
    
    def warning(self, message: str, **extra):
        """Log warning message."""
        if self.logger.isEnabledFor(logging.WARNING):
            log_data = self._format_message("WARNING", message, extra)
            self.logger.warning(json.dumps(log_data) if settings.log_format.value == "json" else message)
    
    def error(self, message: str, **extra):
        """Log error message."""
        if self.logger.isEnabledFor(logging.ERROR):
            log_data = self._format_message("ERROR", message, extra)
            self.logger.error(json.dumps(log_data) if settings.log_format.value == "json" else message)
    
    def critical(self, message: str, **extra):
        """Log critical message."""
        if self.logger.isEnabledFor(logging.CRITICAL):
            log_data = self._format_message("CRITICAL", message, extra)
            self.logger.critical(json.dumps(log_data) if settings.log_format.value == "json" else message)


class AgentActivityLogger:
    """
    Specialized logger for tracking agent activities and decision trees.
    
    This logger provides specific methods for logging agent executions, decisions,
    performance metrics, and workflow states.
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize the agent activity logger.
        
        Args:
            agent_name: Name of the agent being tracked
        """
        self.agent_name = agent_name
        self.logger = get_logger(f"agents.{agent_name}")
        self.start_time = None
        self.decision_tree = []
    
    def start_execution(self, task: str, **context):
        """
        Log the start of agent execution.
        
        Args:
            task: Description of the task being executed
            **context: Additional context information
        """
        self.start_time = time.time()
        self.logger.set_context(
            agent_name=self.agent_name,
            task=task,
            execution_id=id(self),
            **context
        )
        self.logger.info(
            f"Agent {self.agent_name} starting execution",
            task=task,
            start_time=self.start_time
        )
    
    def log_decision(
        self, 
        decision_point: str, 
        chosen_option: str, 
        reasoning: str,
        alternatives: Optional[list] = None,
        confidence: Optional[float] = None
    ):
        """
        Log an agent decision with reasoning.
        
        Args:
            decision_point: Description of what decision was made
            chosen_option: The option that was chosen
            reasoning: Explanation of why this option was chosen
            alternatives: Other options that were considered
            confidence: Confidence score (0.0 to 1.0) in the decision
        """
        decision = {
            "timestamp": time.time(),
            "decision_point": decision_point,
            "chosen_option": chosen_option,
            "reasoning": reasoning,
            "alternatives": alternatives or [],
            "confidence": confidence
        }
        
        self.decision_tree.append(decision)
        self.logger.info(
            f"Agent decision: {decision_point}",
            decision=decision
        )
    
    def log_performance_metric(self, metric_name: str, value: Union[int, float], unit: str = ""):
        """
        Log a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
        """
        self.logger.info(
            f"Performance metric: {metric_name}",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            timestamp=time.time()
        )
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Log an agent execution error.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
        """
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        
        if hasattr(error, "to_dict"):
            error_data.update(error.to_dict())
        
        self.logger.error(
            f"Agent {self.agent_name} execution error",
            **error_data
        )
    
    def end_execution(self, status: str, result: Optional[Dict[str, Any]] = None):
        """
        Log the end of agent execution.
        
        Args:
            status: Execution status (success, failure, timeout, etc.)
            result: Summary of execution results
        """
        end_time = time.time()
        duration = end_time - self.start_time if self.start_time else 0
        
        self.logger.info(
            f"Agent {self.agent_name} execution completed",
            status=status,
            duration=duration,
            decision_tree_length=len(self.decision_tree),
            result=result or {}
        )
        
        # Clear context for next execution
        self.logger.clear_context()
    
    def get_decision_tree(self) -> list:
        """Get the complete decision tree for this execution."""
        return self.decision_tree.copy()


class LangSmithIntegration:
    """
    Integration with LangSmith for advanced logging and monitoring.
    
    This class provides methods to send logs and traces to LangSmith
    for visualization and analysis.
    """
    
    def __init__(self):
        """Initialize LangSmith integration."""
        self.enabled = bool(settings.langsmith_api_key)
        self.project = settings.langsmith_project
        
        if self.enabled:
            try:
                from langsmith import Client
                self.client = Client(api_key=settings.langsmith_api_key)
            except ImportError:
                self.enabled = False
                logging.warning("LangSmith client not available. Install langsmith package to enable.")
    
    def log_agent_run(
        self, 
        agent_name: str, 
        inputs: Dict[str, Any], 
        outputs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log an agent run to LangSmith.
        
        Args:
            agent_name: Name of the agent
            inputs: Agent inputs
            outputs: Agent outputs
            metadata: Additional metadata
        """
        if not self.enabled:
            return
        
        try:
            self.client.create_run(
                name=agent_name,
                run_type="agent",
                inputs=inputs,
                outputs=outputs,
                extra=metadata or {},
                project_name=self.project
            )
        except Exception as e:
            logging.warning(f"Failed to log to LangSmith: {e}")


# Global instances
_loggers = {}
_langsmith = LangSmithIntegration()


def get_logger(name: str, extra_fields: Optional[Dict[str, Any]] = None) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name
        extra_fields: Additional fields to include in all log messages
        
    Returns:
        StructuredLogger instance
    """
    key = f"{name}:{json.dumps(extra_fields or {}, sort_keys=True)}"
    
    if key not in _loggers:
        _loggers[key] = StructuredLogger(name, extra_fields)
    
    return _loggers[key]


def setup_structured_logging():
    """
    Setup structured logging for the entire application.
    
    This function configures the root logger and sets up file rotation,
    console output, and integration with external services.
    """
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Configure root logger
    from config.config import setup_logging
    setup_logging(settings)
    
    # Log startup message
    logger = get_logger(__name__)
    logger.info("Structured logging initialized", 
                log_level=settings.log_level, 
                log_format=settings.log_format)


def log_agent_activity(agent_name: str):
    """
    Decorator to automatically log agent activity.
    
    This decorator wraps agent methods to automatically log start/end times,
    performance metrics, and errors.
    
    Args:
        agent_name: Name of the agent
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            activity_logger = AgentActivityLogger(agent_name)
            
            try:
                activity_logger.start_execution(
                    task=func.__name__,
                    function=f"{func.__module__}.{func.__qualname__}",
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )
                
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                activity_logger.log_performance_metric(
                    "execution_time", 
                    end_time - start_time, 
                    "seconds"
                )
                
                activity_logger.end_execution("success", {"result_type": type(result).__name__})
                
                # Log to LangSmith if enabled
                _langsmith.log_agent_run(
                    agent_name=agent_name,
                    inputs={"args": str(args)[:1000], "kwargs": str(kwargs)[:1000]},
                    outputs={"result": str(result)[:1000]},
                    metadata={
                        "function": func.__name__,
                        "duration": end_time - start_time,
                        "decision_tree": activity_logger.get_decision_tree()
                    }
                )
                
                return result
                
            except Exception as e:
                activity_logger.log_error(e, {"function": func.__name__})
                activity_logger.end_execution("failure", {"error": str(e)})
                raise
        
        return wrapper
    return decorator


@contextmanager
def log_execution_time(logger: StructuredLogger, operation: str):
    """
    Context manager to log execution time of operations.
    
    Args:
        logger: Logger instance to use
        operation: Description of the operation
    """
    start_time = time.time()
    logger.info(f"Starting {operation}")
    
    try:
        yield
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Completed {operation}", duration=duration, status="success")
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        logger.error(f"Failed {operation}", duration=duration, status="failure", error=str(e))
        raise