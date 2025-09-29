#!/usr/bin/env python3
"""
Unit tests for enhanced error handling functionality.
Standalone tests without complex import dependencies.
"""

import pytest
import json
import time
import tempfile
from unittest.mock import Mock, patch
from datetime import datetime

# Import the error handler module directly
from core.error_handler import (
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
        
    def test_error_report_export(self):
        """Test error report export functionality."""
        error = TestFrameworkError(message="Test error")
        self.handler.handle_error(error, attempt_recovery=False)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            report_file = f.name
            
        self.handler.export_error_report(report_file)
        
        with open(report_file) as f:
            report = json.load(f)
            
        assert "summary" in report
        assert "detailed_errors" in report
        assert report["summary"]["total_errors"] == 1


class TestRetryHandler:
    """Test enhanced RetryHandler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.retry_handler = RetryHandler(max_retries=2, base_delay=0.01)
        
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
        
    def test_retry_stats_tracking(self):
        """Test retry statistics tracking."""
        def failing_operation():
            raise ValueError("Always fails")
            
        try:
            self.retry_handler.retry_operation(failing_operation, "stats_test")
        except:
            pass
                
        stats = self.retry_handler.get_retry_stats()
        assert "stats_test" in stats
        assert stats["stats_test"]["failed_attempts"] > 0


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


def test_requirements_compliance():
    """Test specific requirements compliance."""
    
    # Requirement 1.5: CLI tests encounter errors -> clear error messages and logs
    cli_error = ExecutionError("CLI test failed", test_id="cli_test")
    cli_output = handle_cli_error(cli_error)
    
    assert "ERROR:" in cli_output
    assert "Guidance:" in cli_output
    assert "Suggested Actions:" in cli_output
    
    # Requirement 2.5: API calls fail -> meaningful error responses
    api_error = APIError("API call failed", endpoint="/api/test", status_code=400)
    api_response = handle_api_error(api_error)
    
    assert "error" in api_response
    assert "guidance" in api_response["error"]
    assert "recovery_actions" in api_response["error"]
    
    # Requirement 3.5: Adapter validation fails -> specific error diagnostics
    adapter_error = AdapterError("Validation failed", adapter_name="test_adapter")
    adapter_response = handle_adapter_error(adapter_error)
    
    assert "diagnostic_info" in adapter_response["adapter_error"]
    assert "troubleshooting" in adapter_response["adapter_error"]
    
    # Requirement 4.5: Pipeline errors -> detailed error context
    pipeline_error = ExecutionError("Pipeline stage failed")
    pipeline_response = handle_pipeline_error(pipeline_error, "test_stage")
    
    assert "detailed_context" in pipeline_response["pipeline_error"]
    assert "impact_assessment" in pipeline_response["pipeline_error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])