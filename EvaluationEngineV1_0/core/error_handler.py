"""
Error handling and recovery system for the Multi-Turn Evaluation Engine.

This module provides comprehensive error handling with recovery strategies,
graceful degradation, and incident tracking capabilities.
"""

import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field

from .exceptions import (
    EvaluationError, TaskExecutionError, SafetyViolationError,
    ResourceExhaustionError, ConfigurationError, AdapterError,
    TaskRegistrationError, ValidationError, ConversionError
)


class RecoveryAction(Enum):
    """Available recovery actions for error handling."""
    TERMINATE = "terminate"
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    CONTINUE = "continue"
    RESET = "reset"


@dataclass
class ErrorResponse:
    """Response from error handling containing recovery instructions."""
    action: RecoveryAction
    reason: str
    allow_retry: bool = False
    retry_count: int = 0
    max_retries: int = 3
    fallback_config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IncidentReport:
    """Detailed incident report for error tracking."""
    incident_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    severity: str
    context: Dict[str, Any]
    stack_trace: str
    recovery_action: RecoveryAction
    resolved: bool = False
    resolution_notes: Optional[str] = None


class IncidentLogger:
    """Centralized incident logging and tracking system."""
    
    def __init__(self, log_level: int = logging.ERROR):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.incidents: List[IncidentReport] = []
        self._incident_counter = 0
    
    def log_incident(
        self,
        error: Union[EvaluationError, Exception],
        severity: str = "ERROR",
        context: Optional[Dict[str, Any]] = None,
        recovery_action: RecoveryAction = RecoveryAction.TERMINATE
    ) -> str:
        """Log an incident and return incident ID."""
        self._incident_counter += 1
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{self._incident_counter:04d}"
        
        # Extract error information
        if isinstance(error, EvaluationError):
            error_type = error.error_type
            error_message = error.message
            error_context = error.context
        else:
            error_type = type(error).__name__
            error_message = str(error)
            error_context = {}
        
        # Merge contexts
        full_context = {**(context or {}), **error_context}
        
        # Create incident report
        incident = IncidentReport(
            incident_id=incident_id,
            timestamp=datetime.now(),
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            context=full_context,
            stack_trace=traceback.format_exc(),
            recovery_action=recovery_action
        )
        
        self.incidents.append(incident)
        
        # Log to standard logger
        self.logger.error(
            f"Incident {incident_id}: {error_type} - {error_message}",
            extra={
                "incident_id": incident_id,
                "error_type": error_type,
                "severity": severity,
                "context": full_context
            }
        )
        
        return incident_id
    
    def get_incident(self, incident_id: str) -> Optional[IncidentReport]:
        """Retrieve incident by ID."""
        for incident in self.incidents:
            if incident.incident_id == incident_id:
                return incident
        return None
    
    def get_incidents_by_type(self, error_type: str) -> List[IncidentReport]:
        """Get all incidents of a specific type."""
        return [inc for inc in self.incidents if inc.error_type == error_type]
    
    def get_unresolved_incidents(self) -> List[IncidentReport]:
        """Get all unresolved incidents."""
        return [inc for inc in self.incidents if not inc.resolved]
    
    def resolve_incident(self, incident_id: str, resolution_notes: str):
        """Mark an incident as resolved."""
        incident = self.get_incident(incident_id)
        if incident:
            incident.resolved = True
            incident.resolution_notes = resolution_notes
            self.logger.info(f"Incident {incident_id} resolved: {resolution_notes}")


class RecoveryStrategy:
    """Base class for error recovery strategies."""
    
    def can_handle(self, error: EvaluationError, context: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the error."""
        raise NotImplementedError
    
    def recover(self, error: EvaluationError, context: Dict[str, Any]) -> ErrorResponse:
        """Attempt to recover from the error."""
        raise NotImplementedError


class SafetyViolationStrategy(RecoveryStrategy):
    """Recovery strategy for safety violations - always terminate."""
    
    def can_handle(self, error: EvaluationError, context: Dict[str, Any]) -> bool:
        return isinstance(error, SafetyViolationError)
    
    def recover(self, error: EvaluationError, context: Dict[str, Any]) -> ErrorResponse:
        return ErrorResponse(
            action=RecoveryAction.TERMINATE,
            reason=f"Safety violation: {error.violation_type}",
            allow_retry=False,
            metadata={"violation_type": error.violation_type}
        )


class ResourceExhaustionStrategy(RecoveryStrategy):
    """Recovery strategy for resource exhaustion."""
    
    def can_handle(self, error: EvaluationError, context: Dict[str, Any]) -> bool:
        return isinstance(error, ResourceExhaustionError)
    
    def recover(self, error: EvaluationError, context: Dict[str, Any]) -> ErrorResponse:
        # Try to free resources and retry
        return ErrorResponse(
            action=RecoveryAction.RETRY,
            reason=f"Resource exhaustion: {error.resource_type}",
            allow_retry=True,
            max_retries=2,
            metadata={
                "resource_type": error.resource_type,
                "current_usage": error.current_usage,
                "limit": error.limit
            }
        )


class TaskExecutionStrategy(RecoveryStrategy):
    """Recovery strategy for task execution errors."""
    
    def can_handle(self, error: EvaluationError, context: Dict[str, Any]) -> bool:
        return isinstance(error, TaskExecutionError)
    
    def recover(self, error: EvaluationError, context: Dict[str, Any]) -> ErrorResponse:
        if error.recoverable:
            return ErrorResponse(
                action=RecoveryAction.RETRY,
                reason=f"Task execution failed: {error.message}",
                allow_retry=True,
                max_retries=3,
                metadata={"task_id": error.task_id}
            )
        else:
            return ErrorResponse(
                action=RecoveryAction.SKIP,
                reason=f"Non-recoverable task error: {error.message}",
                allow_retry=False,
                metadata={"task_id": error.task_id}
            )


class AdapterErrorStrategy(RecoveryStrategy):
    """Recovery strategy for adapter errors."""
    
    def can_handle(self, error: EvaluationError, context: Dict[str, Any]) -> bool:
        return isinstance(error, AdapterError)
    
    def recover(self, error: EvaluationError, context: Dict[str, Any]) -> ErrorResponse:
        if error.recoverable:
            return ErrorResponse(
                action=RecoveryAction.FALLBACK,
                reason=f"Adapter error: {error.message}",
                allow_retry=True,
                max_retries=2,
                fallback_config={"use_default_adapter": True},
                metadata={"adapter_name": error.adapter_name}
            )
        else:
            return ErrorResponse(
                action=RecoveryAction.SKIP,
                reason=f"Non-recoverable adapter error: {error.message}",
                allow_retry=False,
                metadata={"adapter_name": error.adapter_name}
            )


class ConfigurationErrorStrategy(RecoveryStrategy):
    """Recovery strategy for configuration errors."""
    
    def can_handle(self, error: EvaluationError, context: Dict[str, Any]) -> bool:
        return isinstance(error, ConfigurationError)
    
    def recover(self, error: EvaluationError, context: Dict[str, Any]) -> ErrorResponse:
        return ErrorResponse(
            action=RecoveryAction.TERMINATE,
            reason=f"Configuration error: {error.message}",
            allow_retry=False,
            metadata={"config_field": error.config_field}
        )


class ErrorHandler:
    """Centralized error handling and recovery system."""
    
    def __init__(self, incident_logger: Optional[IncidentLogger] = None):
        self.incident_logger = incident_logger or IncidentLogger()
        self.strategies: List[RecoveryStrategy] = [
            SafetyViolationStrategy(),
            ResourceExhaustionStrategy(),
            TaskExecutionStrategy(),
            AdapterErrorStrategy(),
            ConfigurationErrorStrategy()
        ]
        self.error_counts: Dict[str, int] = {}
        self.recovery_callbacks: Dict[RecoveryAction, List[Callable]] = {
            action: [] for action in RecoveryAction
        }
    
    def register_strategy(self, strategy: RecoveryStrategy):
        """Register a custom recovery strategy."""
        self.strategies.append(strategy)
    
    def register_recovery_callback(
        self, 
        action: RecoveryAction, 
        callback: Callable[[ErrorResponse, Dict[str, Any]], None]
    ):
        """Register a callback for specific recovery actions."""
        self.recovery_callbacks[action].append(callback)
    
    def handle_error(
        self, 
        error: Union[EvaluationError, Exception], 
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorResponse:
        """Handle evaluation error with appropriate recovery strategy."""
        context = context or {}
        
        # Convert generic exceptions to EvaluationError
        if not isinstance(error, EvaluationError):
            error = EvaluationError(
                message=str(error),
                error_type=type(error).__name__,
                recoverable=True,
                context=context
            )
        
        # Track error frequency
        error_key = f"{error.error_type}:{error.message}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Find appropriate recovery strategy
        recovery_strategy = None
        for strategy in self.strategies:
            if strategy.can_handle(error, context):
                recovery_strategy = strategy
                break
        
        # Generate error response
        if recovery_strategy:
            response = recovery_strategy.recover(error, context)
        else:
            response = self._default_recovery(error, context)
        
        # Log incident
        incident_id = self.incident_logger.log_incident(
            error=error,
            severity=self._determine_severity(error),
            context=context,
            recovery_action=response.action
        )
        response.metadata["incident_id"] = incident_id
        
        # Execute recovery callbacks
        for callback in self.recovery_callbacks[response.action]:
            try:
                callback(response, context)
            except Exception as callback_error:
                self.incident_logger.log_incident(
                    error=callback_error,
                    severity="WARNING",
                    context={"original_error": str(error), "callback": str(callback)}
                )
        
        return response
    
    def _default_recovery(self, error: EvaluationError, context: Dict[str, Any]) -> ErrorResponse:
        """Default recovery strategy for unhandled errors."""
        if error.recoverable:
            return ErrorResponse(
                action=RecoveryAction.RETRY,
                reason=f"Unhandled recoverable error: {error.message}",
                allow_retry=True,
                max_retries=1
            )
        else:
            return ErrorResponse(
                action=RecoveryAction.TERMINATE,
                reason=f"Unhandled non-recoverable error: {error.message}",
                allow_retry=False
            )
    
    def _determine_severity(self, error: EvaluationError) -> str:
        """Determine error severity based on error type."""
        if isinstance(error, SafetyViolationError):
            return "CRITICAL"
        elif isinstance(error, (ResourceExhaustionError, ConfigurationError)):
            return "ERROR"
        elif isinstance(error, (TaskExecutionError, AdapterError)):
            return "WARNING"
        else:
            return "INFO"
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        total_errors = sum(self.error_counts.values())
        incident_stats = {}
        
        for incident in self.incident_logger.incidents:
            error_type = incident.error_type
            if error_type not in incident_stats:
                incident_stats[error_type] = {
                    "count": 0,
                    "resolved": 0,
                    "unresolved": 0
                }
            
            incident_stats[error_type]["count"] += 1
            if incident.resolved:
                incident_stats[error_type]["resolved"] += 1
            else:
                incident_stats[error_type]["unresolved"] += 1
        
        return {
            "total_errors": total_errors,
            "error_counts": self.error_counts.copy(),
            "incident_statistics": incident_stats,
            "total_incidents": len(self.incident_logger.incidents),
            "unresolved_incidents": len(self.incident_logger.get_unresolved_incidents())
        }
    
    def reset_statistics(self):
        """Reset error handling statistics."""
        self.error_counts.clear()
        self.incident_logger.incidents.clear()
        self.incident_logger._incident_counter = 0


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_error_handler(handler: ErrorHandler):
    """Set the global error handler instance."""
    global _global_error_handler
    _global_error_handler = handler


def handle_error(
    error: Union[EvaluationError, Exception], 
    context: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """Convenience function to handle errors using the global handler."""
    return get_error_handler().handle_error(error, context)