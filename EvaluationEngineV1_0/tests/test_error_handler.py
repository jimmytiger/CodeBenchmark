"""
Tests for the error handling and recovery system.

This module tests all aspects of error handling including error classification,
recovery strategies, incident logging, and graceful degradation.
"""

import pytest
import logging
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from EvaluationEngineV1_0.core.error_handler import (
    ErrorHandler, IncidentLogger, RecoveryAction, ErrorResponse,
    IncidentReport, RecoveryStrategy, SafetyViolationStrategy,
    ResourceExhaustionStrategy, TaskExecutionStrategy, AdapterErrorStrategy,
    ConfigurationErrorStrategy, get_error_handler, set_error_handler, handle_error
)
from EvaluationEngineV1_0.core.exceptions import (
    EvaluationError, TaskExecutionError, SafetyViolationError,
    ResourceExhaustionError, ConfigurationError, AdapterError,
    TaskRegistrationError, ValidationError, ConversionError
)


class TestIncidentLogger:
    """Test cases for the IncidentLogger class."""
    
    def test_init(self):
        """Test IncidentLogger initialization."""
        logger = IncidentLogger()
        assert logger.incidents == []
        assert logger._incident_counter == 0
        assert logger.logger.level == logging.ERROR
    
    def test_log_incident_with_evaluation_error(self):
        """Test logging an incident with EvaluationError."""
        logger = IncidentLogger()
        error = SafetyViolationError("Test violation", "command_injection")
        
        incident_id = logger.log_incident(error, "CRITICAL")
        
        assert len(logger.incidents) == 1
        incident = logger.incidents[0]
        assert incident.incident_id == incident_id
        assert incident.error_type == "safety_violation"
        assert incident.error_message == "Test violation"
        assert incident.severity == "CRITICAL"
        assert not incident.resolved
    
    def test_log_incident_with_generic_exception(self):
        """Test logging an incident with generic Exception."""
        logger = IncidentLogger()
        error = ValueError("Test value error")
        
        incident_id = logger.log_incident(error, "ERROR")
        
        assert len(logger.incidents) == 1
        incident = logger.incidents[0]
        assert incident.error_type == "ValueError"
        assert incident.error_message == "Test value error"
        assert incident.severity == "ERROR"
    
    def test_get_incident(self):
        """Test retrieving incident by ID."""
        logger = IncidentLogger()
        error = TaskExecutionError("Test error")
        incident_id = logger.log_incident(error)
        
        retrieved = logger.get_incident(incident_id)
        assert retrieved is not None
        assert retrieved.incident_id == incident_id
        
        # Test non-existent incident
        assert logger.get_incident("non-existent") is None
    
    def test_get_incidents_by_type(self):
        """Test retrieving incidents by error type."""
        logger = IncidentLogger()
        
        # Log different types of incidents
        logger.log_incident(TaskExecutionError("Error 1"))
        logger.log_incident(SafetyViolationError("Error 2", "test"))
        logger.log_incident(TaskExecutionError("Error 3"))
        
        task_incidents = logger.get_incidents_by_type("task_execution")
        safety_incidents = logger.get_incidents_by_type("safety_violation")
        
        assert len(task_incidents) == 2
        assert len(safety_incidents) == 1
    
    def test_resolve_incident(self):
        """Test resolving an incident."""
        logger = IncidentLogger()
        error = TaskExecutionError("Test error")
        incident_id = logger.log_incident(error)
        
        logger.resolve_incident(incident_id, "Fixed by restarting service")
        
        incident = logger.get_incident(incident_id)
        assert incident.resolved
        assert incident.resolution_notes == "Fixed by restarting service"
    
    def test_get_unresolved_incidents(self):
        """Test getting unresolved incidents."""
        logger = IncidentLogger()
        
        # Log incidents
        id1 = logger.log_incident(TaskExecutionError("Error 1"))
        id2 = logger.log_incident(TaskExecutionError("Error 2"))
        id3 = logger.log_incident(TaskExecutionError("Error 3"))
        
        # Resolve one incident
        logger.resolve_incident(id2, "Resolved")
        
        unresolved = logger.get_unresolved_incidents()
        assert len(unresolved) == 2
        assert all(not inc.resolved for inc in unresolved)


class TestRecoveryStrategies:
    """Test cases for recovery strategies."""
    
    def test_safety_violation_strategy(self):
        """Test SafetyViolationStrategy."""
        strategy = SafetyViolationStrategy()
        error = SafetyViolationError("Dangerous command", "command_injection")
        
        assert strategy.can_handle(error, {})
        
        response = strategy.recover(error, {})
        assert response.action == RecoveryAction.TERMINATE
        assert not response.allow_retry
        assert "Safety violation" in response.reason
    
    def test_resource_exhaustion_strategy(self):
        """Test ResourceExhaustionStrategy."""
        strategy = ResourceExhaustionStrategy()
        error = ResourceExhaustionError("Memory limit exceeded", "memory", 1024, 512)
        
        assert strategy.can_handle(error, {})
        
        response = strategy.recover(error, {})
        assert response.action == RecoveryAction.RETRY
        assert response.allow_retry
        assert response.max_retries == 2
    
    def test_task_execution_strategy_recoverable(self):
        """Test TaskExecutionStrategy with recoverable error."""
        strategy = TaskExecutionStrategy()
        error = TaskExecutionError("Timeout", "task_1", recoverable=True)
        
        assert strategy.can_handle(error, {})
        
        response = strategy.recover(error, {})
        assert response.action == RecoveryAction.RETRY
        assert response.allow_retry
        assert response.max_retries == 3
    
    def test_task_execution_strategy_non_recoverable(self):
        """Test TaskExecutionStrategy with non-recoverable error."""
        strategy = TaskExecutionStrategy()
        error = TaskExecutionError("Fatal error", "task_1", recoverable=False)
        
        response = strategy.recover(error, {})
        assert response.action == RecoveryAction.SKIP
        assert not response.allow_retry
    
    def test_adapter_error_strategy_recoverable(self):
        """Test AdapterErrorStrategy with recoverable error."""
        strategy = AdapterErrorStrategy()
        error = AdapterError("Connection failed", "swe_bench", recoverable=True)
        
        assert strategy.can_handle(error, {})
        
        response = strategy.recover(error, {})
        assert response.action == RecoveryAction.FALLBACK
        assert response.allow_retry
        assert response.fallback_config is not None
    
    def test_configuration_error_strategy(self):
        """Test ConfigurationErrorStrategy."""
        strategy = ConfigurationErrorStrategy()
        error = ConfigurationError("Invalid config", "max_turns")
        
        assert strategy.can_handle(error, {})
        
        response = strategy.recover(error, {})
        assert response.action == RecoveryAction.TERMINATE
        assert not response.allow_retry


class TestErrorHandler:
    """Test cases for the ErrorHandler class."""
    
    def test_init(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        assert handler.incident_logger is not None
        assert len(handler.strategies) > 0
        assert handler.error_counts == {}
    
    def test_init_with_custom_logger(self):
        """Test ErrorHandler initialization with custom logger."""
        custom_logger = IncidentLogger()
        handler = ErrorHandler(custom_logger)
        assert handler.incident_logger is custom_logger
    
    def test_register_strategy(self):
        """Test registering custom recovery strategy."""
        handler = ErrorHandler()
        initial_count = len(handler.strategies)
        
        custom_strategy = Mock(spec=RecoveryStrategy)
        handler.register_strategy(custom_strategy)
        
        assert len(handler.strategies) == initial_count + 1
        assert custom_strategy in handler.strategies
    
    def test_register_recovery_callback(self):
        """Test registering recovery callback."""
        handler = ErrorHandler()
        callback = Mock()
        
        handler.register_recovery_callback(RecoveryAction.RETRY, callback)
        
        assert callback in handler.recovery_callbacks[RecoveryAction.RETRY]
    
    def test_handle_evaluation_error(self):
        """Test handling EvaluationError."""
        handler = ErrorHandler()
        error = SafetyViolationError("Test violation", "test_type")
        
        response = handler.handle_error(error)
        
        assert response.action == RecoveryAction.TERMINATE
        assert not response.allow_retry
        assert len(handler.incident_logger.incidents) == 1
    
    def test_handle_generic_exception(self):
        """Test handling generic Exception."""
        handler = ErrorHandler()
        error = ValueError("Test error")
        
        response = handler.handle_error(error)
        
        assert response.action in [RecoveryAction.RETRY, RecoveryAction.TERMINATE]
        assert len(handler.incident_logger.incidents) == 1
    
    def test_error_counting(self):
        """Test error frequency tracking."""
        handler = ErrorHandler()
        error1 = TaskExecutionError("Same error")
        error2 = TaskExecutionError("Same error")
        error3 = TaskExecutionError("Different error")
        
        handler.handle_error(error1)
        handler.handle_error(error2)
        handler.handle_error(error3)
        
        assert handler.error_counts["task_execution:Same error"] == 2
        assert handler.error_counts["task_execution:Different error"] == 1
    
    def test_recovery_callbacks_execution(self):
        """Test that recovery callbacks are executed."""
        handler = ErrorHandler()
        callback = Mock()
        handler.register_recovery_callback(RecoveryAction.TERMINATE, callback)
        
        error = SafetyViolationError("Test", "test")
        response = handler.handle_error(error)
        
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == response
    
    def test_callback_error_handling(self):
        """Test that callback errors are handled gracefully."""
        handler = ErrorHandler()
        
        def failing_callback(response, context):
            raise ValueError("Callback failed")
        
        handler.register_recovery_callback(RecoveryAction.TERMINATE, failing_callback)
        
        error = SafetyViolationError("Test", "test")
        response = handler.handle_error(error)
        
        # Should still return response despite callback failure
        assert response.action == RecoveryAction.TERMINATE
        # Should log the callback error as an incident
        assert len(handler.incident_logger.incidents) == 2
    
    def test_default_recovery_recoverable(self):
        """Test default recovery for recoverable errors."""
        handler = ErrorHandler()
        # Clear all strategies to test default recovery
        handler.strategies = []
        
        error = EvaluationError("Test", "unknown", recoverable=True)
        response = handler.handle_error(error)
        
        assert response.action == RecoveryAction.RETRY
        assert response.allow_retry
        assert response.max_retries == 1
    
    def test_default_recovery_non_recoverable(self):
        """Test default recovery for non-recoverable errors."""
        handler = ErrorHandler()
        # Clear all strategies to test default recovery
        handler.strategies = []
        
        error = EvaluationError("Test", "unknown", recoverable=False)
        response = handler.handle_error(error)
        
        assert response.action == RecoveryAction.TERMINATE
        assert not response.allow_retry
    
    def test_severity_determination(self):
        """Test error severity determination."""
        handler = ErrorHandler()
        
        # Test different error types
        safety_error = SafetyViolationError("Test", "test")
        resource_error = ResourceExhaustionError("Test", "memory")
        task_error = TaskExecutionError("Test")
        generic_error = EvaluationError("Test", "unknown")
        
        assert handler._determine_severity(safety_error) == "CRITICAL"
        assert handler._determine_severity(resource_error) == "ERROR"
        assert handler._determine_severity(task_error) == "WARNING"
        assert handler._determine_severity(generic_error) == "INFO"
    
    def test_get_error_statistics(self):
        """Test getting error statistics."""
        handler = ErrorHandler()
        
        # Generate some errors
        handler.handle_error(TaskExecutionError("Error 1"))
        handler.handle_error(TaskExecutionError("Error 2"))
        handler.handle_error(SafetyViolationError("Error 3", "test"))
        
        # Resolve one incident
        incidents = handler.incident_logger.incidents
        handler.incident_logger.resolve_incident(incidents[0].incident_id, "Resolved")
        
        stats = handler.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert stats["total_incidents"] == 3
        assert stats["unresolved_incidents"] == 2
        assert "task_execution" in stats["incident_statistics"]
        assert "safety_violation" in stats["incident_statistics"]
    
    def test_reset_statistics(self):
        """Test resetting error statistics."""
        handler = ErrorHandler()
        
        # Generate some errors
        handler.handle_error(TaskExecutionError("Error 1"))
        handler.handle_error(TaskExecutionError("Error 2"))
        
        assert len(handler.error_counts) > 0
        assert len(handler.incident_logger.incidents) > 0
        
        handler.reset_statistics()
        
        assert len(handler.error_counts) == 0
        assert len(handler.incident_logger.incidents) == 0
        assert handler.incident_logger._incident_counter == 0


class TestGlobalErrorHandler:
    """Test cases for global error handler functions."""
    
    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns singleton."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        assert handler1 is handler2
    
    def test_set_error_handler(self):
        """Test setting custom global error handler."""
        custom_handler = ErrorHandler()
        set_error_handler(custom_handler)
        
        retrieved_handler = get_error_handler()
        assert retrieved_handler is custom_handler
    
    def test_handle_error_convenience_function(self):
        """Test convenience handle_error function."""
        error = TaskExecutionError("Test error")
        response = handle_error(error)
        
        assert isinstance(response, ErrorResponse)
        assert response.action in RecoveryAction


class TestErrorHandlerIntegration:
    """Integration tests for error handling system."""
    
    def test_safety_violation_immediate_termination(self):
        """Test that safety violations cause immediate termination."""
        handler = ErrorHandler()
        error = SafetyViolationError("Dangerous command detected", "command_injection")
        
        response = handler.handle_error(error, {"task_id": "test_task"})
        
        assert response.action == RecoveryAction.TERMINATE
        assert not response.allow_retry
        assert "Safety violation" in response.reason
        
        # Check incident was logged with correct severity
        incidents = handler.incident_logger.incidents
        assert len(incidents) == 1
        assert incidents[0].severity == "CRITICAL"
        assert incidents[0].error_type == "safety_violation"
    
    def test_resource_exhaustion_retry_logic(self):
        """Test resource exhaustion retry logic."""
        handler = ErrorHandler()
        error = ResourceExhaustionError("Memory limit exceeded", "memory", 1024, 512)
        
        response = handler.handle_error(error, {"evaluation_id": "eval_123"})
        
        assert response.action == RecoveryAction.RETRY
        assert response.allow_retry
        assert response.max_retries == 2
        
        # Check incident was logged
        incidents = handler.incident_logger.incidents
        assert len(incidents) == 1
        assert incidents[0].severity == "ERROR"
    
    def test_graceful_degradation_on_turns_exceeded(self):
        """Test graceful degradation when turns exceed limits."""
        handler = ErrorHandler()
        
        # Simulate a task execution error that represents turns exceeded
        error = TaskExecutionError(
            "Maximum turns exceeded", 
            "multi_turn_task", 
            recoverable=False
        )
        
        response = handler.handle_error(error, {
            "current_turns": 10,
            "max_turns": 10,
            "partial_results": {"completed_steps": 5}
        })
        
        assert response.action == RecoveryAction.SKIP
        assert not response.allow_retry
        
        # Verify partial results are preserved in context
        incident = handler.incident_logger.incidents[0]
        assert "partial_results" in incident.context
    
    def test_multiple_error_handling_sequence(self):
        """Test handling multiple errors in sequence."""
        handler = ErrorHandler()
        
        errors = [
            TaskExecutionError("Timeout", recoverable=True),
            ResourceExhaustionError("CPU limit", "cpu"),
            SafetyViolationError("Dangerous operation", "file_access"),
            AdapterError("Connection failed", "swe_bench", recoverable=True)
        ]
        
        responses = []
        for error in errors:
            response = handler.handle_error(error)
            responses.append(response)
        
        # Verify different recovery actions
        assert responses[0].action == RecoveryAction.RETRY  # Task error
        assert responses[1].action == RecoveryAction.RETRY  # Resource error
        assert responses[2].action == RecoveryAction.TERMINATE  # Safety error
        assert responses[3].action == RecoveryAction.FALLBACK  # Adapter error
        
        # Verify all incidents were logged
        assert len(handler.incident_logger.incidents) == 4
    
    @patch('logging.Logger.error')
    def test_logging_integration(self, mock_logger_error):
        """Test integration with logging system."""
        handler = ErrorHandler()
        error = TaskExecutionError("Test error", "task_123")
        
        handler.handle_error(error)
        
        # Verify logging was called
        mock_logger_error.assert_called_once()
        call_args = mock_logger_error.call_args
        assert "task_execution" in call_args[0][0]
        assert "Test error" in call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__])