#!/usr/bin/env python3
"""
Standalone test for enhanced error handling functionality.
Tests requirements 1.5, 2.5, 3.5, 4.5 compliance without import dependencies.
"""

import sys
import json
import time
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Import only the error handler module directly
from core.error_handler import (
    ErrorHandler, RetryHandler, ErrorContextManager,
    ConfigurationError, DependencyError, ExecutionError, 
    AdapterError, APIError, NetworkError,
    handle_cli_error, handle_api_error, handle_adapter_error, handle_pipeline_error,
    create_error_context, ErrorSeverity, ErrorCategory
)


def test_error_classification():
    """Test comprehensive error classification."""
    print("Testing Error Classification...")
    
    # Test ConfigurationError
    config_error = ConfigurationError(
        message="Missing required field: model_name",
        config_path="/path/to/config.yaml",
        validation_errors=["model_name is required"]
    )
    
    assert config_error.error_code == "CONFIG_ERROR"
    assert config_error.severity == ErrorSeverity.HIGH
    assert config_error.category == ErrorCategory.CONFIGURATION
    assert len(config_error.recovery_actions) >= 2
    print("  ✓ ConfigurationError works correctly")
    
    # Test DependencyError
    dep_error = DependencyError(
        message="Missing lm-evaluation-harness",
        dependency_name="lm-evaluation-harness",
        installation_command="pip install lm-eval"
    )
    
    assert dep_error.is_transient is True
    assert "pip install lm-eval" in dep_error.user_guidance
    print("  ✓ DependencyError works correctly")
    
    # Test APIError
    api_error = APIError(
        message="Rate limited",
        endpoint="/api/v1/evaluations",
        status_code=429
    )
    
    assert api_error.is_transient is True
    assert any(action.action_type == "retry" for action in api_error.recovery_actions)
    print("  ✓ APIError works correctly")
    
    print("Error Classification: PASSED\n")


def test_error_handler():
    """Test enhanced error handler functionality."""
    print("Testing Error Handler...")
    
    handler = ErrorHandler("TestHandler")
    
    # Test error handling
    error = ConfigurationError("Test error")
    handler.handle_error(error, attempt_recovery=False)
    
    assert len(handler.error_history) == 1
    assert handler.error_counts["ConfigurationError"] == 1
    print("  ✓ Error handling works correctly")
    
    # Test graceful degradation
    handler.enable_graceful_degradation(True)
    
    low_error = ExecutionError("Minor issue")
    low_error.severity = ErrorSeverity.LOW
    assert handler.should_continue_after_error(low_error) is True
    
    critical_error = ExecutionError("Critical failure")
    critical_error.severity = ErrorSeverity.CRITICAL
    assert handler.should_continue_after_error(critical_error) is False
    print("  ✓ Graceful degradation works correctly")
    
    # Test error summary
    summary = handler.get_error_summary()
    assert summary["total_errors"] == 1
    assert "severity_counts" in summary
    assert "category_counts" in summary
    print("  ✓ Error summary works correctly")
    
    print("Error Handler: PASSED\n")


def test_retry_handler():
    """Test retry handler functionality."""
    print("Testing Retry Handler...")
    
    retry_handler = RetryHandler(max_retries=2, base_delay=0.01)
    
    # Test successful retry
    call_count = 0
    
    def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Temporary failure")
        return "success"
    
    result = retry_handler.retry_operation(flaky_operation, "test_op")
    assert result == "success"
    assert call_count == 2
    print("  ✓ Retry operation works correctly")
    
    # Test retry stats
    stats = retry_handler.get_retry_stats()
    assert "test_op" in stats
    assert stats["test_op"]["successful_attempts"] == 1
    print("  ✓ Retry statistics work correctly")
    
    print("Retry Handler: PASSED\n")


def test_error_formatting():
    """Test error formatting for different interfaces."""
    print("Testing Error Formatting...")
    
    # Test CLI formatting (Requirement 1.5)
    config_error = ConfigurationError("Config validation failed")
    cli_output = handle_cli_error(config_error)
    
    assert "ERROR: Config validation failed" in cli_output
    assert "CONFIG_ERROR" in cli_output
    assert "Guidance:" in cli_output
    print("  ✓ CLI error formatting works (Requirement 1.5)")
    
    # Test API formatting (Requirement 2.5)
    api_error = APIError("Server error", status_code=500)
    api_response = handle_api_error(api_error)
    
    assert "error" in api_response
    assert api_response["error"]["code"] == "API_ERROR"
    assert "recovery_actions" in api_response["error"]
    print("  ✓ API error formatting works (Requirement 2.5)")
    
    # Test adapter formatting (Requirement 3.5)
    adapter_error = AdapterError("Adapter failed", adapter_name="lm_eval_adapter")
    adapter_response = handle_adapter_error(adapter_error)
    
    assert "adapter_error" in adapter_response
    assert "diagnostic_info" in adapter_response["adapter_error"]
    assert "troubleshooting" in adapter_response["adapter_error"]
    print("  ✓ Adapter error formatting works (Requirement 3.5)")
    
    # Test pipeline formatting (Requirement 4.5)
    exec_error = ExecutionError("Pipeline failed", test_id="test_123")
    pipeline_response = handle_pipeline_error(exec_error, "validation_stage")
    
    assert "pipeline_error" in pipeline_response
    assert "detailed_context" in pipeline_response["pipeline_error"]
    assert "impact_assessment" in pipeline_response["pipeline_error"]
    print("  ✓ Pipeline error formatting works (Requirement 4.5)")
    
    print("Error Formatting: PASSED\n")


def test_context_manager():
    """Test error context manager."""
    print("Testing Context Manager...")
    
    handler = ErrorHandler("ContextTest")
    context = create_error_context(test_id="ctx_test")
    
    # Test with continue_on_error=True
    exception_suppressed = False
    try:
        with ErrorContextManager(
            handler, 
            "test_operation", 
            context,
            continue_on_error=True
        ):
            raise ValueError("Test exception")
    except ValueError:
        exception_suppressed = False
    else:
        exception_suppressed = True
    
    assert exception_suppressed is True
    assert len(handler.error_history) == 1
    print("  ✓ Context manager works correctly")
    
    print("Context Manager: PASSED\n")


def test_requirements_compliance():
    """Test specific requirements compliance."""
    print("Testing Requirements Compliance...")
    
    # Requirement 1.5: CLI tests encounter errors -> clear error messages and logs
    cli_error = ExecutionError("CLI test failed", test_id="cli_test")
    cli_output = handle_cli_error(cli_error)
    
    assert "ERROR:" in cli_output
    assert "Guidance:" in cli_output
    assert "Suggested Actions:" in cli_output
    print("  ✓ Requirement 1.5: CLI error messages and logs")
    
    # Requirement 2.5: API calls fail -> meaningful error responses
    api_error = APIError("API call failed", endpoint="/api/test", status_code=400)
    api_response = handle_api_error(api_error)
    
    assert "error" in api_response
    assert "guidance" in api_response["error"]
    assert "recovery_actions" in api_response["error"]
    print("  ✓ Requirement 2.5: Meaningful API error responses")
    
    # Requirement 3.5: Adapter validation fails -> specific error diagnostics
    adapter_error = AdapterError("Validation failed", adapter_name="test_adapter")
    adapter_response = handle_adapter_error(adapter_error)
    
    assert "diagnostic_info" in adapter_response["adapter_error"]
    assert "troubleshooting" in adapter_response["adapter_error"]
    print("  ✓ Requirement 3.5: Specific adapter error diagnostics")
    
    # Requirement 4.5: Pipeline errors -> detailed error context
    pipeline_error = ExecutionError("Pipeline stage failed")
    pipeline_response = handle_pipeline_error(pipeline_error, "test_stage")
    
    assert "detailed_context" in pipeline_response["pipeline_error"]
    assert "impact_assessment" in pipeline_response["pipeline_error"]
    print("  ✓ Requirement 4.5: Detailed pipeline error context")
    
    print("Requirements Compliance: PASSED\n")


def main():
    """Run all tests."""
    print("Enhanced Error Handling Test Suite")
    print("Testing requirements 1.5, 2.5, 3.5, 4.5 compliance")
    print("=" * 50)
    
    try:
        test_error_classification()
        test_error_handler()
        test_retry_handler()
        test_error_formatting()
        test_context_manager()
        test_requirements_compliance()
        
        print("=" * 50)
        print("ALL TESTS PASSED!")
        print("=" * 50)
        print("Enhanced error handling features verified:")
        print("✓ Comprehensive error classification system")
        print("✓ Graceful degradation for partial failures")
        print("✓ Retry logic for transient failures")
        print("✓ Detailed error reporting and user guidance")
        print("✓ Requirements 1.5, 2.5, 3.5, 4.5 compliance")
        
        return 0
        
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())