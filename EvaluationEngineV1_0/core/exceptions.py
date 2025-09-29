"""
Exception classes for the Multi-Turn Evaluation Engine.

This module defines the exception hierarchy used throughout the evaluation system
to provide clear error classification and recovery strategies.
"""

from datetime import datetime
from typing import Optional, Dict, Any


class EvaluationError(Exception):
    """Base class for all evaluation-related errors.
    
    This exception provides a foundation for error handling with classification
    and recovery information.
    
    Attributes:
        message: Human-readable error description
        error_type: Classification of the error type
        recoverable: Whether the error allows for recovery attempts
        timestamp: When the error occurred
        context: Additional context information
    """
    
    def __init__(
        self, 
        message: str, 
        error_type: str, 
        recoverable: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.recoverable = recoverable
        self.timestamp = datetime.now()
        self.context = (context or {}).copy()
    
    def __str__(self) -> str:
        return f"{self.error_type}: {self.message}"
    
    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(message='{self.message}', "
                f"error_type='{self.error_type}', recoverable={self.recoverable})")


class TaskExecutionError(EvaluationError):
    """Error that occurs during task execution.
    
    This exception is raised when a task fails to execute properly,
    such as environment setup failures or execution timeouts.
    """
    
    def __init__(
        self, 
        message: str, 
        task_id: Optional[str] = None,
        recoverable: bool = True,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "task_execution", recoverable=recoverable, context=context)
        self.task_id = task_id


class SafetyViolationError(EvaluationError):
    """Error raised when safety policies are violated.
    
    This exception is raised when the evaluation system detects
    potentially dangerous operations or policy violations.
    Safety violations are never recoverable.
    """
    
    def __init__(
        self, 
        message: str, 
        violation_type: str,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "safety_violation", recoverable=False, context=context)
        self.violation_type = violation_type


class ResourceExhaustionError(EvaluationError):
    """Error raised when system resources are exhausted.
    
    This exception is raised when the evaluation exceeds
    resource limits such as memory, CPU time, or disk space.
    """
    
    def __init__(
        self, 
        message: str, 
        resource_type: str,
        current_usage: Optional[float] = None,
        limit: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "resource_exhaustion", recoverable=True, context=context)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit


class ConfigurationError(EvaluationError):
    """Error raised when configuration is invalid.
    
    This exception is raised when task or system configuration
    is malformed or contains invalid values.
    """
    
    def __init__(
        self, 
        message: str, 
        config_field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "configuration", recoverable=False, context=context)
        self.config_field = config_field


class AdapterError(EvaluationError):
    """Error raised by benchmark adapters.
    
    This exception is raised when external benchmark integration
    fails or encounters compatibility issues.
    """
    
    def __init__(
        self, 
        message: str, 
        adapter_name: Optional[str] = None,
        recoverable: bool = True,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "adapter", recoverable=recoverable, context=context)
        self.adapter_name = adapter_name


class TaskRegistrationError(EvaluationError):
    """Error raised during task registration.
    
    This exception is raised when task registration fails,
    such as when registering adapters or discovering tasks.
    """
    
    def __init__(
        self, 
        message: str, 
        task_name: Optional[str] = None,
        recoverable: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "task_registration", recoverable=recoverable, context=context)
        self.task_name = task_name


class ValidationError(EvaluationError):
    """Error raised when data validation fails.
    
    This exception is raised when data structures fail validation
    checks, such as schema compliance or constraint violations.
    """
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        expected_value: Optional[Any] = None,
        actual_value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "validation", recoverable=False, context=context)
        self.field_name = field_name
        self.expected_value = expected_value
        self.actual_value = actual_value


class ConversionError(EvaluationError):
    """Error raised when result conversion fails.
    
    This exception is raised when converting results between different
    formats fails due to incompatible data or missing converters.
    """
    
    def __init__(
        self, 
        message: str, 
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "conversion", recoverable=False, context=context)
        self.source_type = source_type
        self.target_type = target_type


class PerformanceError(EvaluationError):
    """Error related to performance issues.
    
    This exception is raised when performance degradation is detected
    or when performance thresholds are exceeded.
    """
    
    def __init__(
        self, 
        message: str, 
        performance_metric: Optional[str] = None,
        threshold: Optional[float] = None,
        actual_value: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "performance", recoverable=True, context=context)
        self.performance_metric = performance_metric
        self.threshold = threshold
        self.actual_value = actual_value