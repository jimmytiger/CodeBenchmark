#!/usr/bin/env python3
"""
Demonstration of enhanced error handling and recovery mechanisms.
Shows compliance with requirements 1.5, 2.5, 3.5, 4.5.
"""

import sys
import json
import time
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from core.error_handler import (
    ErrorHandler, RetryHandler, ErrorContextManager,
    ConfigurationError, DependencyError, ExecutionError, 
    AdapterError, APIError, NetworkError,
    handle_cli_error, handle_api_error, handle_adapter_error, handle_pipeline_error,
    create_error_context, get_global_error_handler
)


def demo_error_classification():
    """Demonstrate comprehensive error classification."""
    print("=" * 60)
    print("DEMO: Comprehensive Error Classification")
    print("=" * 60)
    
    # Configuration Error
    config_error = ConfigurationError(
        message="Missing required configuration field: model_name",
        config_path="/path/to/config.yaml",
        validation_errors=["model_name is required", "invalid task format"]
    )
    
    print("Configuration Error:")
    print(f"  Message: {config_error.message}")
    print(f"  Severity: {config_error.severity.value}")
    print(f"  Recovery Actions: {len(config_error.recovery_actions)}")
    print(f"  User Guidance: {config_error.user_guidance[:100]}...")
    print()
    
    # Dependency Error
    dep_error = DependencyError(
        message="lm-evaluation-harness not installed",
        dependency_name="lm-evaluation-harness",
        installation_command="pip install lm-eval"
    )
    
    print("Dependency Error:")
    print(f"  Message: {dep_error.message}")
    print(f"  Is Transient: {dep_error.is_transient}")
    print(f"  Installation Command: {dep_error.installation_command}")
    print()
    
    # API Error
    api_error = APIError(
        message="Rate limit exceeded",
        endpoint="/api/v1/evaluations",
        status_code=429,
        response_data={"error": "Too many requests", "retry_after": 60}
    )
    
    print("API Error:")
    print(f"  Message: {api_error.message}")
    print(f"  Status Code: {api_error.status_code}")
    print(f"  Is Transient: {api_error.is_transient}")
    print(f"  Recovery Actions: {len(api_error.recovery_actions)}")
    print()


def demo_error_handler():
    """Demonstrate enhanced error handler functionality."""
    print("=" * 60)
    print("DEMO: Enhanced Error Handler")
    print("=" * 60)
    
    handler = ErrorHandler("DemoHandler")
    handler.enable_graceful_degradation(True)
    
    # Simulate various errors
    errors = [
        ConfigurationError("Invalid config", config_path="/config.yaml"),
        DependencyError("Missing dependency", dependency_name="test-lib"),
        APIError("Server error", endpoint="/api/test", status_code=500),
        AdapterError("Adapter failed", adapter_name="lm_eval_adapter")
    ]
    
    print("Handling multiple errors...")
    for error in errors:
        handler.handle_error(error, attempt_recovery=False)
        print(f"  Handled: {type(error).__name__}")
    
    # Get error summary
    summary = handler.get_error_summary()
    print(f"\nError Summary:")
    print(f"  Total Errors: {summary['total_errors']}")
    print(f"  Error Types: {list(summary['error_counts'].keys())}")
    print(f"  Severity Distribution: {summary['severity_counts']}")
    print(f"  Category Distribution: {summary['category_counts']}")
    
    # Generate troubleshooting guide
    print("\nGenerating troubleshooting guide...")
    guide = handler.get_troubleshooting_guide()
    print(f"Guide length: {len(guide)} characters")
    print("First 200 characters:")
    print(guide[:200] + "...")
    print()


def demo_retry_handler():
    """Demonstrate retry handler with circuit breaker."""
    print("=" * 60)
    print("DEMO: Retry Handler with Circuit Breaker")
    print("=" * 60)
    
    retry_handler = RetryHandler(max_retries=3, base_delay=0.1)
    
    # Simulate operation that succeeds after retries
    call_count = 0
    
    def flaky_operation():
        nonlocal call_count
        call_count += 1
        print(f"    Attempt {call_count}")
        if call_count < 3:
            raise ConnectionError("Temporary network issue")
        return "Success!"
    
    print("Testing retry operation...")
    try:
        result = retry_handler.retry_operation(flaky_operation, "demo_operation")
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  Failed: {e}")
    
    # Show retry statistics
    stats = retry_handler.get_retry_stats()
    if "demo_operation" in stats:
        op_stats = stats["demo_operation"]
        print(f"  Total Attempts: {op_stats['total_attempts']}")
        print(f"  Successful: {op_stats['successful_attempts']}")
        print(f"  Failed: {op_stats['failed_attempts']}")
    
    print()


def demo_context_manager():
    """Demonstrate error context manager."""
    print("=" * 60)
    print("DEMO: Error Context Manager")
    print("=" * 60)
    
    handler = ErrorHandler("ContextDemo")
    
    # Test with continue_on_error=True
    print("Testing context manager with continue_on_error=True...")
    context = create_error_context(
        test_id="demo_test",
        adapter_name="demo_adapter"
    )
    
    try:
        with ErrorContextManager(
            handler, 
            "demo_operation", 
            context,
            continue_on_error=True
        ):
            print("  Raising exception inside context manager...")
            raise ValueError("Demo exception")
        print("  Context manager suppressed the exception!")
    except Exception as e:
        print(f"  Exception not suppressed: {e}")
    
    print(f"  Errors recorded: {len(handler.error_history)}")
    print()


def demo_error_formatting():
    """Demonstrate error formatting for different interfaces."""
    print("=" * 60)
    print("DEMO: Error Formatting for Different Interfaces")
    print("=" * 60)
    
    # Create sample errors
    config_error = ConfigurationError(
        message="Configuration validation failed",
        config_path="/path/to/config.yaml"
    )
    
    api_error = APIError(
        message="Internal server error",
        endpoint="/api/v1/evaluations",
        status_code=500
    )
    
    adapter_error = AdapterError(
        message="lm_eval adapter integration failed",
        adapter_name="lm_eval_adapter"
    )
    
    # CLI Error Formatting (Requirement 1.5)
    print("CLI Error Format:")
    cli_output = handle_cli_error(config_error)
    print(cli_output[:300] + "..." if len(cli_output) > 300 else cli_output)
    
    # API Error Formatting (Requirement 2.5)
    print("API Error Format:")
    api_response = handle_api_error(api_error)
    print(json.dumps(api_response, indent=2)[:400] + "...")
    
    # Adapter Error Formatting (Requirement 3.5)
    print("\nAdapter Error Format:")
    adapter_response = handle_adapter_error(adapter_error)
    print(json.dumps(adapter_response, indent=2)[:400] + "...")
    
    # Pipeline Error Formatting (Requirement 4.5)
    print("\nPipeline Error Format:")
    pipeline_response = handle_pipeline_error(config_error, "configuration_stage")
    print(json.dumps(pipeline_response, indent=2)[:400] + "...")
    print()


def demo_graceful_degradation():
    """Demonstrate graceful degradation for partial failures."""
    print("=" * 60)
    print("DEMO: Graceful Degradation")
    print("=" * 60)
    
    handler = ErrorHandler("GracefulDemo")
    handler.enable_graceful_degradation(True)
    
    # Simulate a test pipeline with various errors
    test_stages = [
        ("initialization", "success"),
        ("configuration", "config_error"),
        ("dependency_check", "dependency_error"),
        ("adapter_validation", "success"),
        ("execution", "execution_error"),
        ("results_processing", "success")
    ]
    
    successful_stages = []
    failed_stages = []
    
    print("Simulating test pipeline with graceful degradation...")
    
    for stage, outcome in test_stages:
        print(f"  Stage: {stage}")
        
        if outcome == "success":
            successful_stages.append(stage)
            print(f"    ✓ Success")
        else:
            # Create appropriate error
            if outcome == "config_error":
                error = ConfigurationError(f"Error in {stage}")
            elif outcome == "dependency_error":
                error = DependencyError(f"Missing dependency in {stage}")
            else:
                error = ExecutionError(f"Execution failed in {stage}")
            
            handler.handle_error(error, attempt_recovery=False)
            
            # Check if we should continue
            if handler.should_continue_after_error(error):
                failed_stages.append(stage)
                print(f"    ✗ Failed (continuing)")
            else:
                failed_stages.append(stage)
                print(f"    ✗ Failed (stopping)")
                break
    
    print(f"\nPipeline Results:")
    print(f"  Successful stages: {len(successful_stages)}")
    print(f"  Failed stages: {len(failed_stages)}")
    print(f"  Total errors: {len(handler.error_history)}")
    
    # Show final error summary
    summary = handler.get_error_summary()
    print(f"  Error distribution: {summary['category_counts']}")
    print()


def main():
    """Run all demonstrations."""
    print("Enhanced Error Handling and Recovery Mechanisms Demo")
    print("Demonstrating compliance with requirements 1.5, 2.5, 3.5, 4.5")
    print()
    
    try:
        demo_error_classification()
        demo_error_handler()
        demo_retry_handler()
        demo_context_manager()
        demo_error_formatting()
        demo_graceful_degradation()
        
        print("=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("All error handling features demonstrated:")
        print("✓ Comprehensive error classification system")
        print("✓ Graceful degradation for partial failures")
        print("✓ Retry logic for transient failures")
        print("✓ Detailed error reporting and user guidance")
        print("✓ Requirements 1.5, 2.5, 3.5, 4.5 compliance")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())