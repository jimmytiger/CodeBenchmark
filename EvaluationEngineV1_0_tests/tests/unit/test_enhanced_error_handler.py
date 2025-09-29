"""
Unit tests for enhanced error handling and recovery mechanisms.
Tests requirements 1.5, 2.5, 3.5, 4.5 compliance.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch
from datetime import datetime

from EvaluationEngineV1_0_tests.core.error_handler import (
    ErrorHandler, RetryHandler, ErrorContextManager,
    TestFrameworkError, ConfigurationError, DependencyError,
    ExecutionError, ValidationError, AdapterError, APIError,
    NetworkError, ResourceError, PermissionError, DataError,
    ErrorSeverity, ErrorCategory, ErrorContext, RecoveryAction,
    handle_cli_error, handle_api_error, handle_adapter_error, handle_pipeline_error,
    create_error_context, get_global_error_handler
)


class TestErrorClassification:
    """Test comprehensive error classification system."""
    
    def test_configuration_error_creation(self):
        """Test ConfigurationError with recovery actions."""
        error = ConfigurationError(
            message="Invalid configuration file",
            config_path="/path/to/config.yaml",
            validation_errors=["Missing required field: model_name"]
        )
        
        assert error.error_code == "CONFIG_ERROR"
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.config_path == "/path/to/config.yaml"
        assert len(error.recovery_actions) >= 2
        assert error.user_guidance is not None
        
    def test_dependency_error_with_installation_command(self):
        """Test DependencyError with installation guidance."""
        error = DependencyError(
            message="Missing lm-evaluation-harness",
            dependency_name="lm-evaluation-harness",
            installation_command="pip install lm-eval"
        )
        
        assert error.error_code == "DEPENDENCY_ERROR"
        assert error.is_transient is True
        assert any(action.action_type == "retry" for action in error.recovery_actions)
        assert "pip install lm-eval" in error.user_guidance
        
    def test_execution_error_with_exit_code(self):
        """Test ExecutionError with specific exit code handling."""
        error = ExecutionError(
            message="Command failed",
            test_id="test_123",
            exit_code=137,
            command="python test.py"
        )
        
        assert error.context.test_id == "test_123"
        assert error.context.command == "python test.py"
        assert "killed" in error.user_guidance.lower()
        assert "memory" in error.user_guidance.lower()
        
    def test_api_error_with_status_codes(self):
        """Test APIError with different HTTP status codes."""
        # Test 429 (Rate Limited)
        error_429 = APIError(
            message="Rate limited",
            endpoint="/api/v1/evaluations",
            status_code=429
        )
        
        assert error_429.is_transient is True
        assert any(action.action_type == "retry" for action in error_429.recovery_actions)
        
        # Test 500 (Server Error)
        error_500 = APIError(
            message="Internal server error",
            endpoint="/api/v1/evaluations",
            status_code=500
        )
        
        assert error_500.is_transient is True
        assert "server error" in error_500.user_guidance.lower()
        
    def test_adapter_error_with_specific_guidance(self):
        """Test AdapterError with adapter-specific guidance."""
        error = AdapterError(
            message="lm_eval adapter failed",
            adapter_name="lm_eval_adapter",
            adapter_method="run_evaluation"
        )
        
        assert error.context.adapter_name == "lm_eval_adapter"
        assert "lm-evaluation-harness" in error.user_guidance
        assert error.severity == ErrorSeverity.HIGH


class TestErrorHandler:
    """Test enhanced ErrorHandler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler("TestErrorHandler")
        
    def test_error_handling_with_context(self):
        """Test error handling with comprehensive context."""
        context = create_error_context(
            test_id="test_123",
            adapter_name="lm_eval_adapter",
            config_path="/path/to/config.yaml"
        )
        
        error = ConfigurationError(
            message="Test error",
            config_path="/path/to/config.yaml"
        )
        
        self.handler.handle_error(error, attempt_recovery=False)
        
        assert len(self.handler.error_history) == 1
        assert self.handler.error_counts["ConfigurationError"] == 1
        
        summary = self.handler.get_error_summary()
        assert summary["total_errors"] == 1
        assert "severity_counts" in summary
        assert "category_counts" in summary
        
    def test_graceful_degradation(self):
        """Test graceful degradation for partial failures."""
        self.handler.enable_graceful_degradation(True)
        
        # Low severity error should allow continuation
        low_error = TestFrameworkError(
            message="Minor issue",
            severity=ErrorSeverity.LOW
        )
        assert self.handler.should_continue_after_error(low_error) is True
        
        # Critical error should stop execution
        critical_error = TestFrameworkError(
            message="Critical failure",
            severity=ErrorSeverity.CRITICAL
        )
        assert self.handler.should_continue_after_error(critical_error) is False
        
    def test_exception_classification(self):
        """Test automatic exception classification."""
        # Test network error classification
        network_exception = ConnectionError("Connection timeout")
        classified_error = self.handler._classify_exception(
            network_exception, 
            {"url": "https://api.example.com"}
        )
        
        assert isinstance(classified_error, NetworkError)
        assert classified_error.category == ErrorCategory.NETWORK
        
        # Test permission error classification
        permission_exception = PermissionError("Access denied")
        classified_error = self.handler._classify_exception(
            permission_exception,
            {"file_path": "/restricted/file.txt"}
        )
        
        assert isinstance(classified_error, PermissionError)
        assert classified_error.category == ErrorCategory.PERMISSION
        
    def test_error_report_export(self, tmp_path):
        """Test error report export functionality."""
        error = TestFrameworkError(message="Test error")
        self.handler.handle_error(error, attempt_recovery=False)
        
        report_file = tmp_path / "error_report.json"
        self.handler.export_error_report(str(report_file))
        
        assert report_file.exists()
        
        with open(report_file) as f:
            report = json.load(f)
            
        assert "summary" in report
        assert "detailed_errors" in report
        assert report["summary"]["total_errors"] == 1
        
    def test_troubleshooting_guide_generation(self):
        """Test troubleshooting guide generation."""
        # Add various types of errors
        errors = [
            ConfigurationError("Config error", config_path="/config.yaml"),
            DependencyError("Missing dependency", dependency_name="test-lib"),
            APIError("API error", endpoint="/api/test", status_code=500)
        ]
        
        for error in errors:
            self.handler.handle_error(error, attempt_recovery=False)
            
        guide = self.handler.get_troubleshooting_guide()
        
        assert "Troubleshooting Guide" in guide
        assert "Configuration Errors" in guide
        assert "Dependency Errors" in guide
        assert "Api Errors" in guide


class TestRetryHandler:
    """Test enhanced RetryHandler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.retry_handler = RetryHandler(max_retries=2, base_delay=0.1)
        
    def test_successful_retry_operation(self):
        """Test successful operation after retries."""
        call_count = 0
        
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
            
        result = self.retry_handler.retry_operation(
            failing_operation, 
            "test_operation"
        )
        
        assert result == "success"
        assert call_count == 2
        
        stats = self.retry_handler.get_retry_stats()
        assert "test_operation" in stats
        assert stats["test_operation"]["successful_attempts"] == 1
        
    def test_retry_with_circuit_breaker(self):
        """Test circuit breaker pattern."""
        def always_failing_operation():
            raise ConnectionError("Always fails")
            
        # Fail enough times to open circuit breaker
        for _ in range(6):
            try:
                self.retry_handler.retry_operation(
                    always_failing_operation,
                    "circuit_test"
                )
            except:
                pass
                
        # Circuit breaker should now be open
        with pytest.raises(TestFrameworkError) as exc_info:
            self.retry_handler.retry_with_circuit_breaker(
                always_failing_operation,
                "circuit_test",
                failure_threshold=5
            )
            
        assert "CIRCUIT_BREAKER_OPEN" in str(exc_info.value)
        
    def test_retry_stats_tracking(self):
        """Test retry statistics tracking."""
        def sometimes_failing_operation():
            import random
            if random.random() < 0.7:
                raise ValueError("Random failure")
            return "success"
            
        # Run multiple operations
        for _ in range(5):
            try:
                self.retry_handler.retry_operation(
                    sometimes_failing_operation,
                    "stats_test"
                )
            except:
                pass
                
        stats = self.retry_handler.get_retry_stats()
        assert "stats_test" in stats
        assert stats["stats_test"]["total_attempts"] > 0


class TestErrorContextManager:
    """Test ErrorContextManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler("TestContextManager")
        
    def test_context_manager_with_exception(self):
        """Test context manager handling exceptions."""
        context = create_error_context(test_id="ctx_test")
        
        with pytest.raises(ValueError):
            with ErrorContextManager(
                self.handler, 
                "test_operation", 
                context,
                continue_on_error=False
            ):
                raise ValueError("Test exception")
                
        assert len(self.handler.error_history) == 1
        
    def test_context_manager_continue_on_error(self):
        """Test context manager with continue_on_error=True."""
        context = create_error_context(test_id="ctx_test")
        
        # Should not raise exception due to continue_on_error=True
        with ErrorContextManager(
            self.handler,
            "test_operation",
            context,
            continue_on_error=True
        ):
            raise ValueError("Test exception")
            
        assert len(self.handler.error_history) == 1


class TestErrorFormatting:
    """Test error formatting for different interfaces."""
    
    def test_cli_error_formatting(self):
        """Test CLI error formatting (Requirement 1.5)."""
        error = ConfigurationError(
            message="Configuration validation failed",
            config_path="/path/to/config.yaml"
        )
        
        cli_output = handle_cli_error(error)
        
        assert "ERROR: Configuration validation failed" in cli_output
        assert "CONFIG_ERROR" in cli_output
        assert "HIGH" in cli_output
        assert "Guidance:" in cli_output
        assert "Suggested Actions:" in cli_output
        
    def test_api_error_formatting(self):
        """Test API error formatting (Requirement 2.5)."""
        error = APIError(
            message="Internal server error",
            endpoint="/api/v1/evaluations",
            status_code=500
        )
        
        api_response = handle_api_error(error)
        
        assert "error" in api_response
        assert api_response["error"]["message"] == "Internal server error"
        assert api_response["error"]["code"] == "API_ERROR"
        assert api_response["error"]["is_transient"] is True
        assert "recovery_actions" in api_response["error"]
        
    def test_adapter_error_formatting(self):
        """Test adapter error formatting (Requirement 3.5)."""
        error = AdapterError(
            message="Adapter integration failed",
            adapter_name="lm_eval_adapter"
        )
        
        adapter_response = handle_adapter_error(error)
        
        assert "adapter_error" in adapter_response
        assert adapter_response["adapter_error"]["adapter_name"] == "lm_eval_adapter"
        assert "diagnostic_info" in adapter_response["adapter_error"]
        assert "troubleshooting" in adapter_response["adapter_error"]
        
    def test_pipeline_error_formatting(self):
        """Test pipeline error formatting (Requirement 4.5)."""
        error = ExecutionError(
            message="Pipeline stage failed",
            test_id="pipeline_test"
        )
        
        pipeline_response = handle_pipeline_error(error, "validation_stage")
        
        assert "pipeline_error" in pipeline_response
        assert pipeline_response["pipeline_error"]["stage"] == "validation_stage"
        assert "detailed_context" in pipeline_response["pipeline_error"]
        assert "impact_assessment" in pipeline_response["pipeline_error"]
        assert "recovery_options" in pipeline_response["pipeline_error"]


class TestGlobalErrorHandler:
    """Test global error handler functionality."""
    
    def test_global_error_handler_singleton(self):
        """Test global error handler singleton pattern."""
        handler1 = get_global_error_handler()
        handler2 = get_global_error_handler()
        
        assert handler1 is handler2
        
    def test_set_global_error_handler(self):
        """Test setting custom global error handler."""
        custom_handler = ErrorHandler("CustomHandler")
        set_global_error_handler(custom_handler)
        
        retrieved_handler = get_global_error_handler()
        assert retrieved_handler is custom_handler


if __name__ == "__main__":
    pytest.main([__file__, "-v"])