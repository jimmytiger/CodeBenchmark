"""
Unit tests for the exception hierarchy.

This module tests the exception classes to ensure they provide proper
error classification and recovery information.
"""

import pytest
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from EvaluationEngineV1_0.core.exceptions import (
    EvaluationError, TaskExecutionError, SafetyViolationError,
    ResourceExhaustionError, ConfigurationError, AdapterError
)


class TestEvaluationError:
    """Test cases for the base EvaluationError class."""
    
    def test_evaluation_error_creation(self):
        """Test basic EvaluationError creation."""
        error = EvaluationError(
            message="Test error",
            error_type="test_type",
            recoverable=True
        )
        
        assert str(error) == "test_type: Test error"
        assert error.message == "Test error"
        assert error.error_type == "test_type"
        assert error.recoverable is True
        assert isinstance(error.timestamp, datetime)
        assert error.context == {}
    
    def test_evaluation_error_with_context(self):
        """Test EvaluationError with context information."""
        context = {"task_id": "test_task", "step": 5}
        error = EvaluationError(
            message="Context error",
            error_type="context_type",
            context=context
        )
        
        assert error.context == context
        assert error.context is not context  # Should be a copy
    
    def test_evaluation_error_defaults(self):
        """Test EvaluationError with default values."""
        error = EvaluationError("Default error", "default_type")
        
        assert error.recoverable is False
        assert error.context == {}
        assert isinstance(error.timestamp, datetime)
    
    def test_evaluation_error_repr(self):
        """Test EvaluationError string representation."""
        error = EvaluationError("Test", "test", True)
        repr_str = repr(error)
        
        assert "EvaluationError" in repr_str
        assert "message='Test'" in repr_str
        assert "error_type='test'" in repr_str
        assert "recoverable=True" in repr_str
    
    def test_evaluation_error_inheritance(self):
        """Test that EvaluationError inherits from Exception."""
        error = EvaluationError("Test", "test")
        
        assert isinstance(error, Exception)
        assert isinstance(error, EvaluationError)


class TestTaskExecutionError:
    """Test cases for TaskExecutionError."""
    
    def test_task_execution_error_creation(self):
        """Test TaskExecutionError creation."""
        error = TaskExecutionError(
            message="Task failed",
            task_id="test_task"
        )
        
        assert error.message == "Task failed"
        assert error.error_type == "task_execution"
        assert error.recoverable is True  # Default for task execution errors
        assert error.task_id == "test_task"
    
    def test_task_execution_error_without_task_id(self):
        """Test TaskExecutionError without task_id."""
        error = TaskExecutionError("Generic task error")
        
        assert error.task_id is None
        assert error.error_type == "task_execution"
    
    def test_task_execution_error_non_recoverable(self):
        """Test TaskExecutionError with recoverable=False."""
        error = TaskExecutionError(
            message="Fatal task error",
            recoverable=False
        )
        
        assert error.recoverable is False
    
    def test_task_execution_error_with_context(self):
        """Test TaskExecutionError with context."""
        context = {"step": 3, "action": "test_action"}
        error = TaskExecutionError(
            message="Context error",
            task_id="task1",
            context=context
        )
        
        assert error.context == context
        assert error.task_id == "task1"


class TestSafetyViolationError:
    """Test cases for SafetyViolationError."""
    
    def test_safety_violation_error_creation(self):
        """Test SafetyViolationError creation."""
        error = SafetyViolationError(
            message="Dangerous command detected",
            violation_type="command_filter"
        )
        
        assert error.message == "Dangerous command detected"
        assert error.error_type == "safety_violation"
        assert error.recoverable is False  # Safety violations are never recoverable
        assert error.violation_type == "command_filter"
    
    def test_safety_violation_error_with_context(self):
        """Test SafetyViolationError with context."""
        context = {"command": "rm -rf /", "user": "test_user"}
        error = SafetyViolationError(
            message="Destructive command",
            violation_type="dangerous_command",
            context=context
        )
        
        assert error.context == context
        assert error.violation_type == "dangerous_command"
        assert error.recoverable is False
    
    def test_safety_violation_error_inheritance(self):
        """Test SafetyViolationError inheritance."""
        error = SafetyViolationError("Test", "test_type")
        
        assert isinstance(error, EvaluationError)
        assert isinstance(error, SafetyViolationError)


class TestResourceExhaustionError:
    """Test cases for ResourceExhaustionError."""
    
    def test_resource_exhaustion_error_creation(self):
        """Test ResourceExhaustionError creation."""
        error = ResourceExhaustionError(
            message="Memory limit exceeded",
            resource_type="memory",
            current_usage=1024.0,
            limit=512.0
        )
        
        assert error.message == "Memory limit exceeded"
        assert error.error_type == "resource_exhaustion"
        assert error.recoverable is True  # Default for resource errors
        assert error.resource_type == "memory"
        assert error.current_usage == 1024.0
        assert error.limit == 512.0
    
    def test_resource_exhaustion_error_minimal(self):
        """Test ResourceExhaustionError with minimal parameters."""
        error = ResourceExhaustionError(
            message="CPU timeout",
            resource_type="cpu"
        )
        
        assert error.resource_type == "cpu"
        assert error.current_usage is None
        assert error.limit is None
    
    def test_resource_exhaustion_error_with_context(self):
        """Test ResourceExhaustionError with context."""
        context = {"process_id": 1234, "duration": 300}
        error = ResourceExhaustionError(
            message="Process timeout",
            resource_type="time",
            current_usage=350.0,
            limit=300.0,
            context=context
        )
        
        assert error.context == context
        assert error.current_usage == 350.0
        assert error.limit == 300.0


class TestConfigurationError:
    """Test cases for ConfigurationError."""
    
    def test_configuration_error_creation(self):
        """Test ConfigurationError creation."""
        error = ConfigurationError(
            message="Invalid timeout value",
            config_field="timeout"
        )
        
        assert error.message == "Invalid timeout value"
        assert error.error_type == "configuration"
        assert error.recoverable is False  # Config errors are not recoverable
        assert error.config_field == "timeout"
    
    def test_configuration_error_without_field(self):
        """Test ConfigurationError without config_field."""
        error = ConfigurationError("General config error")
        
        assert error.config_field is None
        assert error.error_type == "configuration"
    
    def test_configuration_error_with_context(self):
        """Test ConfigurationError with context."""
        context = {"config_file": "test.yaml", "line": 15}
        error = ConfigurationError(
            message="Parse error",
            config_field="max_turns",
            context=context
        )
        
        assert error.context == context
        assert error.config_field == "max_turns"


class TestAdapterError:
    """Test cases for AdapterError."""
    
    def test_adapter_error_creation(self):
        """Test AdapterError creation."""
        error = AdapterError(
            message="SWE-bench connection failed",
            adapter_name="swe_bench"
        )
        
        assert error.message == "SWE-bench connection failed"
        assert error.error_type == "adapter"
        assert error.recoverable is True  # Default for adapter errors
        assert error.adapter_name == "swe_bench"
    
    def test_adapter_error_non_recoverable(self):
        """Test AdapterError with recoverable=False."""
        error = AdapterError(
            message="Adapter initialization failed",
            adapter_name="test_adapter",
            recoverable=False
        )
        
        assert error.recoverable is False
        assert error.adapter_name == "test_adapter"
    
    def test_adapter_error_without_name(self):
        """Test AdapterError without adapter_name."""
        error = AdapterError("Generic adapter error")
        
        assert error.adapter_name is None
        assert error.error_type == "adapter"
    
    def test_adapter_error_with_context(self):
        """Test AdapterError with context."""
        context = {"url": "https://api.example.com", "status_code": 500}
        error = AdapterError(
            message="API error",
            adapter_name="api_adapter",
            context=context
        )
        
        assert error.context == context
        assert error.adapter_name == "api_adapter"


class TestExceptionHierarchy:
    """Test cases for the overall exception hierarchy."""
    
    def test_all_exceptions_inherit_from_evaluation_error(self):
        """Test that all custom exceptions inherit from EvaluationError."""
        exceptions = [
            TaskExecutionError("test"),
            SafetyViolationError("test", "test_type"),
            ResourceExhaustionError("test", "memory"),
            ConfigurationError("test"),
            AdapterError("test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, EvaluationError)
            assert isinstance(exc, Exception)
    
    def test_exception_error_types(self):
        """Test that each exception has the correct error_type."""
        test_cases = [
            (TaskExecutionError("test"), "task_execution"),
            (SafetyViolationError("test", "test"), "safety_violation"),
            (ResourceExhaustionError("test", "memory"), "resource_exhaustion"),
            (ConfigurationError("test"), "configuration"),
            (AdapterError("test"), "adapter")
        ]
        
        for exception, expected_type in test_cases:
            assert exception.error_type == expected_type
    
    def test_exception_recoverability(self):
        """Test default recoverability settings for each exception type."""
        # Recoverable by default
        recoverable_exceptions = [
            TaskExecutionError("test"),
            ResourceExhaustionError("test", "memory"),
            AdapterError("test")
        ]
        
        for exc in recoverable_exceptions:
            assert exc.recoverable is True
        
        # Not recoverable by default
        non_recoverable_exceptions = [
            SafetyViolationError("test", "test"),
            ConfigurationError("test")
        ]
        
        for exc in non_recoverable_exceptions:
            assert exc.recoverable is False
    
    def test_exception_timestamps(self):
        """Test that all exceptions have timestamps."""
        exceptions = [
            EvaluationError("test", "test"),
            TaskExecutionError("test"),
            SafetyViolationError("test", "test"),
            ResourceExhaustionError("test", "memory"),
            ConfigurationError("test"),
            AdapterError("test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc.timestamp, datetime)
            # Timestamp should be recent (within last second)
            time_diff = datetime.now() - exc.timestamp
            assert time_diff.total_seconds() < 1.0