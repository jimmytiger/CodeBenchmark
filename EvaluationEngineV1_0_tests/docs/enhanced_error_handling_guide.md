# Enhanced Error Handling and Recovery Mechanisms

This document describes the comprehensive error handling and recovery mechanisms implemented for the EvaluationEngineV1_0 testing framework, ensuring compliance with requirements 1.5, 2.5, 3.5, and 4.5.

## Overview

The enhanced error handling system provides:

- **Comprehensive error classification** with specific error types and categories
- **Graceful degradation** for partial failures to continue testing when possible
- **Intelligent retry logic** for transient failures with exponential backoff
- **Detailed error reporting** with user guidance and recovery suggestions
- **Interface-specific formatting** for CLI, API, adapter, and pipeline contexts

## Error Classification System

### Error Severity Levels

```python
class ErrorSeverity(Enum):
    LOW = "low"          # Minor issues that don't affect core functionality
    MEDIUM = "medium"    # Moderate issues that may impact some features
    HIGH = "high"        # Serious issues that significantly impact functionality
    CRITICAL = "critical" # Critical failures that stop execution
```

### Error Categories

```python
class ErrorCategory(Enum):
    CONFIGURATION = "configuration"  # Config file and parameter errors
    DEPENDENCY = "dependency"        # Missing or incompatible dependencies
    EXECUTION = "execution"          # Runtime execution failures
    VALIDATION = "validation"        # Data and result validation errors
    ADAPTER = "adapter"              # Adapter integration failures
    API = "api"                      # API server and client errors
    NETWORK = "network"              # Network connectivity issues
    RESOURCE = "resource"            # Resource exhaustion (memory, disk, etc.)
    PERMISSION = "permission"        # File system and access permissions
    DATA = "data"                    # Data format and structure errors
```

### Specialized Error Classes

#### ConfigurationError
Handles configuration file validation and parsing errors.

```python
config_error = ConfigurationError(
    message="Missing required field: model_name",
    config_path="/path/to/config.yaml",
    validation_errors=["model_name is required", "invalid task format"]
)
```

**Features:**
- Automatic recovery actions (check syntax, use defaults)
- Specific guidance for configuration issues
- Validation error details

#### DependencyError
Manages missing or incompatible dependency issues.

```python
dep_error = DependencyError(
    message="lm-evaluation-harness not installed",
    dependency_name="lm-evaluation-harness",
    installation_command="pip install lm-eval"
)
```

**Features:**
- Installation command suggestions
- Automatic retry with dependency installation
- System requirement checks

#### APIError
Handles API server and client communication errors.

```python
api_error = APIError(
    message="Rate limit exceeded",
    endpoint="/api/v1/evaluations",
    status_code=429,
    response_data={"error": "Too many requests", "retry_after": 60}
)
```

**Features:**
- HTTP status code specific handling
- Automatic retry for transient errors (5xx, 429)
- Server response data preservation

#### AdapterError
Manages adapter integration and testing failures.

```python
adapter_error = AdapterError(
    message="lm_eval adapter integration failed",
    adapter_name="lm_eval_adapter",
    adapter_method="run_evaluation"
)
```

**Features:**
- Adapter-specific troubleshooting guidance
- Method-level error context
- Integration fallback options

## Recovery Mechanisms

### Recovery Actions

Each error includes structured recovery actions:

```python
@dataclass
class RecoveryAction:
    action_type: str  # 'retry', 'fallback', 'skip', 'manual'
    description: str
    command: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    success_probability: float = 0.5
    estimated_time: Optional[int] = None  # seconds
```

### Retry Handler

Intelligent retry logic with exponential backoff and circuit breaker pattern:

```python
retry_handler = RetryHandler(max_retries=3, base_delay=1.0)

# Retry with exponential backoff
result = retry_handler.retry_operation(
    operation=flaky_function,
    operation_name="api_call",
    retry_on=(ConnectionError, TimeoutError)
)

# Circuit breaker pattern
result = retry_handler.retry_with_circuit_breaker(
    operation=unreliable_function,
    operation_name="external_service",
    failure_threshold=5,
    recovery_timeout=60
)
```

**Features:**
- Exponential backoff with jitter
- Circuit breaker for repeated failures
- Operation-specific retry statistics
- Configurable retry conditions

### Graceful Degradation

The system can continue operation after non-critical errors:

```python
handler = ErrorHandler()
handler.enable_graceful_degradation(True)

# Check if execution should continue after an error
if handler.should_continue_after_error(error):
    # Continue with remaining tests
    continue_execution()
else:
    # Stop execution for critical errors
    stop_execution()
```

**Degradation Rules:**
- Critical errors stop execution
- High-severity configuration errors stop execution
- Too many errors (>50) stop execution
- Other errors allow continuation

## Requirements Compliance

### Requirement 1.5: CLI Error Messages and Logs

CLI errors are formatted with comprehensive information:

```python
cli_output = handle_cli_error(error)
```

**Output Format:**
```
============================================================
ERROR: Configuration validation failed
============================================================
Error Code: CONFIG_ERROR
Severity: HIGH
Category: Configuration
Time: 2024-01-15 10:30:45
Test ID: test_123
Adapter: lm_eval_adapter

Guidance:
Configuration validation failed with the following issues:
  - Missing required field: model_name
  - Invalid task format
Please fix these issues and try again.

Suggested Actions:
  1. Check configuration file syntax and required fields
     Command: cat /path/to/config.yaml
  2. Use default configuration
============================================================
```

### Requirement 2.5: Meaningful API Error Responses

API errors return structured JSON responses:

```python
api_response = handle_api_error(error)
```

**Response Format:**
```json
{
  "error": {
    "message": "Internal server error",
    "code": "API_ERROR",
    "severity": "medium",
    "category": "api",
    "timestamp": "2024-01-15T10:30:45.123456",
    "context": {
      "endpoint": "/api/v1/evaluations",
      "test_id": null,
      "adapter_name": null
    },
    "guidance": "API error for endpoint: /api/v1/evaluations (HTTP 500)...",
    "recovery_actions": [
      {
        "type": "retry",
        "description": "Retry request (server error)",
        "command": null,
        "success_probability": 0.6
      }
    ],
    "is_transient": true
  }
}
```

### Requirement 3.5: Specific Adapter Error Diagnostics

Adapter errors provide detailed diagnostic information:

```python
adapter_response = handle_adapter_error(error)
```

**Response Format:**
```json
{
  "adapter_error": {
    "adapter_name": "lm_eval_adapter",
    "error_message": "Adapter integration failed",
    "error_code": "ADAPTER_ERROR",
    "severity": "high",
    "timestamp": "2024-01-15T10:30:45.123456",
    "diagnostic_info": {
      "category": "adapter",
      "context": {...},
      "is_transient": false
    },
    "troubleshooting": {
      "guidance": "Adapter error in: lm_eval_adapter...",
      "recovery_actions": [
        {
          "action": "manual",
          "description": "Check lm_eval_adapter configuration and dependencies",
          "command": null,
          "success_rate": "70.0%"
        }
      ]
    }
  }
}
```

### Requirement 4.5: Detailed Pipeline Error Context

Pipeline errors include comprehensive context information:

```python
pipeline_response = handle_pipeline_error(error, "validation_stage")
```

**Response Format:**
```json
{
  "pipeline_error": {
    "stage": "validation_stage",
    "error_message": "Pipeline stage failed",
    "error_code": "EXECUTION_ERROR",
    "severity": "medium",
    "category": "execution",
    "timestamp": "2024-01-15T10:30:45.123456",
    "detailed_context": {
      "test_id": "pipeline_test",
      "config_path": null,
      "command": null,
      "file_path": null,
      "system_state": null,
      "additional_info": {...}
    },
    "impact_assessment": {
      "can_continue": true,
      "is_transient": true,
      "recovery_possible": true
    },
    "user_guidance": "Test execution failed...",
    "recovery_options": [...]
  }
}
```

## Usage Examples

### Basic Error Handling

```python
from core.error_handler import ErrorHandler, ConfigurationError

# Create error handler
handler = ErrorHandler("MyTestFramework")
handler.enable_graceful_degradation(True)

# Handle an error
try:
    # Some operation that might fail
    validate_configuration(config_file)
except Exception as e:
    # Convert and handle the error
    framework_error = handler.handle_exception(e, {
        "config_path": config_file,
        "operation": "configuration_validation"
    })
    
    # Check if we should continue
    if handler.should_continue_after_error(framework_error):
        print("Continuing with default configuration...")
    else:
        print("Stopping due to critical error")
        exit(1)
```

### Context Manager Usage

```python
from core.error_handler import ErrorContextManager, create_error_context

# Use context manager for automatic error handling
context = create_error_context(
    test_id="test_123",
    adapter_name="lm_eval_adapter"
)

with ErrorContextManager(
    handler, 
    "adapter_validation", 
    context,
    continue_on_error=True
) as ctx:
    # Operations that might fail
    validate_adapter()
    run_adapter_tests()
```

### Retry Operations

```python
from core.error_handler import RetryHandler

retry_handler = RetryHandler(max_retries=3, base_delay=1.0)

# Retry a flaky operation
def call_external_api():
    # Might fail with network errors
    return requests.get("https://api.example.com/data")

try:
    result = retry_handler.retry_operation(
        call_external_api,
        "external_api_call",
        (requests.ConnectionError, requests.Timeout)
    )
    print(f"Success: {result}")
except Exception as e:
    print(f"Failed after retries: {e}")
```

## Error Reporting and Analysis

### Error Summary

```python
# Get comprehensive error summary
summary = handler.get_error_summary()
print(f"Total errors: {summary['total_errors']}")
print(f"Error types: {summary['error_counts']}")
print(f"Severity distribution: {summary['severity_counts']}")
print(f"Category distribution: {summary['category_counts']}")
```

### Export Error Report

```python
# Export detailed error report
handler.export_error_report("error_report.json")
```

### Generate Troubleshooting Guide

```python
# Generate troubleshooting guide based on encountered errors
guide = handler.get_troubleshooting_guide()
print(guide)
```

## Best Practices

### Error Handling Guidelines

1. **Use specific error types** instead of generic exceptions
2. **Provide actionable recovery suggestions** in error messages
3. **Include sufficient context** for debugging and resolution
4. **Enable graceful degradation** for non-critical failures
5. **Log errors appropriately** based on severity level

### Recovery Strategy

1. **Classify errors correctly** to determine appropriate recovery actions
2. **Implement retry logic** for transient failures
3. **Provide fallback options** when primary operations fail
4. **Guide users** with clear instructions for manual resolution
5. **Monitor error patterns** to identify systemic issues

### Testing Error Handling

1. **Test error scenarios** explicitly in your test suites
2. **Verify error formatting** for different interfaces
3. **Validate recovery mechanisms** work as expected
4. **Check graceful degradation** behavior
5. **Monitor error statistics** during test execution

## Integration with Testing Framework

The enhanced error handling is integrated throughout the testing framework:

- **CLI Interface**: Uses `handle_cli_error()` for user-friendly error display
- **API Interface**: Uses `handle_api_error()` for structured JSON responses
- **Adapter Validation**: Uses `handle_adapter_error()` for diagnostic information
- **Pipeline Execution**: Uses `handle_pipeline_error()` for detailed context
- **Test Orchestration**: Uses graceful degradation for partial test failures
- **Retry Logic**: Automatically retries transient failures in network operations

This comprehensive error handling system ensures robust, user-friendly, and maintainable error management throughout the testing framework.