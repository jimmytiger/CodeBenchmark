# SWE-bench Adapter Validator Guide

## Overview

The SWE-bench Adapter Validator is a comprehensive testing component designed to validate the integration and functionality of the SWE-bench adapter within the EvaluationEngineV1_0 testing framework. It provides automated testing capabilities for software engineering tasks, environment setup validation, and dependency management.

## Features

### Core Capabilities

1. **Integration Validation**: Comprehensive validation of SWE-bench adapter integration
2. **Dependency Management**: Automatic installation and validation of required dependencies
3. **Environment Setup**: Automated setup and teardown of testing environments
4. **Real Task Execution**: Testing with actual SWE-bench software engineering tasks
5. **Performance Metrics**: Collection of execution metrics and performance data
6. **Error Handling**: Robust error handling with detailed diagnostics

### Supported Operations

- **Module Loading**: Validates SWE-bench adapter module availability
- **Dependency Checking**: Verifies git, python, pip, and pytest availability
- **Environment Creation**: Sets up isolated testing environments
- **Task Execution**: Executes real SWE-bench tasks with validation
- **Result Analysis**: Analyzes task results and validates real execution

## Usage

### Basic Usage

```python
from EvaluationEngineV1_0_tests.core.swe_bench_adapter_validator import SWEBenchAdapterValidator

# Initialize validator
config = {
    "timeout": 600,
    "test_task_count": 1
}
validator = SWEBenchAdapterValidator(config)

# Run full integration validation
validation_result = validator.validate_integration()

# Check results
if validation_result.integration_status.value == "passed":
    print("SWE-bench adapter validation successful!")
else:
    print(f"Validation failed: {validation_result.issues_found}")
```

### Advanced Usage

```python
# Test specific functionality
validator = SWEBenchAdapterValidator()

# 1. Check dependencies
deps_ok = validator.install_dependencies()
print(f"Dependencies: {validator.dependency_status}")

# 2. Setup environment
env_ok = validator.setup_environment()
print(f"Environment: {validator.work_dir}")

# 3. Test software tasks
task_results = validator.test_software_tasks(task_count=2)
for result in task_results:
    print(f"Task {result.name}: {result.status.value}")

# 4. Get adapter information
adapter_info = validator.get_adapter_info()
print(f"Adapter: {adapter_info.name} v{adapter_info.version}")
```

## Configuration

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `timeout` | int | 600 | Maximum execution time in seconds |
| `test_task_count` | int | 1 | Number of tasks to test |
| `work_dir` | str | None | Custom work directory path |
| `max_file_size` | int | 1048576 | Maximum file size in bytes |

### Example Configuration

```python
config = {
    "timeout": 900,  # 15 minutes
    "test_task_count": 3,
    "max_file_size": 2 * 1024 * 1024,  # 2MB
}
```

## Dependencies

### Required Dependencies

1. **git**: Version control system for repository operations
2. **python**: Python interpreter (3.8+)
3. **pip**: Python package installer

### Optional Dependencies

1. **pytest**: Python testing framework for test execution

### Dependency Installation

The validator automatically checks and installs dependencies:

```python
validator = SWEBenchAdapterValidator()
success = validator.install_dependencies()

# Check status
for dep_name, status in validator.dependency_status.items():
    print(f"{dep_name}: {status}")
```

## Testing Process

### Validation Steps

1. **Module Check**: Verifies SWE-bench adapter module can be imported
2. **Dependency Validation**: Checks all required dependencies are available
3. **Basic Functionality**: Tests adapter instantiation and basic methods
4. **Environment Setup**: Validates environment creation and file operations
5. **Real Task Execution**: Executes actual SWE-bench tasks
6. **Performance Analysis**: Collects metrics and generates recommendations

### Test Results

Each validation produces a `ValidationResult` object containing:

```python
@dataclass
class ValidationResult:
    adapter_name: str
    adapter_type: AdapterType
    integration_status: TestStatus
    dependencies_installed: bool
    test_results: List[TestResult]
    performance_metrics: Dict[str, float]
    issues_found: List[str]
    recommendations: List[str]
    validation_time: float
    validated_at: datetime
```

## Error Handling

### Common Issues

1. **Missing Dependencies**: Install git, python, or pip
2. **Module Import Errors**: Ensure EvaluationEngineV1_0 is in Python path
3. **Environment Setup Failures**: Check file system permissions
4. **Task Execution Timeouts**: Increase timeout configuration

### Error Resolution

```python
try:
    validation_result = validator.validate_integration()
except Exception as e:
    print(f"Validation error: {e}")
    # Check specific issues
    if "git" in str(e):
        print("Install git: brew install git")
    elif "python" in str(e):
        print("Check Python installation")
```

## Performance Metrics

### Collected Metrics

- **Dependency Success Rate**: Percentage of dependencies successfully installed
- **Test Success Rate**: Percentage of tests that passed
- **Execution Time**: Time taken for various operations
- **Memory Usage**: Peak memory consumption during testing
- **Task Completion Rate**: Percentage of tasks completed successfully

### Accessing Metrics

```python
validation_result = validator.validate_integration()
metrics = validation_result.performance_metrics

print(f"Success Rate: {metrics.get('test_success_rate', 0):.1%}")
print(f"Dependency Rate: {metrics.get('dependency_success_rate', 0):.1%}")
```

## Integration with Test Framework

### Using with Test Orchestrator

```python
from EvaluationEngineV1_0_tests.core.test_orchestrator import TestOrchestrator
from EvaluationEngineV1_0_tests.models.test_models import TestConfiguration, TestType, AdapterType

# Create test configuration
test_config = TestConfiguration(
    test_id="swe_bench_validation",
    test_type=TestType.ADAPTER,
    name="SWE-bench Adapter Validation",
    description="Validate SWE-bench adapter functionality",
    target_adapters=[AdapterType.SWE_BENCH],
    timeout=600
)

# Execute through orchestrator
orchestrator = TestOrchestrator()
result = orchestrator.execute_single_test(test_config)
```

### Custom Test Suites

```python
# Create custom test suite
suite_config = {
    "suite_name": "SWE-bench Validation Suite",
    "adapter_tests": {
        "adapters": ["swe_bench"],
        "execution_params": {
            "test_task_count": 2,
            "timeout": 900
        }
    }
}

# Execute suite
suite_results = orchestrator.execute_test_suite(suite_config)
```

## Best Practices

### Testing Guidelines

1. **Start Small**: Begin with single task testing before scaling up
2. **Check Dependencies**: Always validate dependencies before testing
3. **Monitor Resources**: Watch memory and CPU usage during testing
4. **Handle Timeouts**: Set appropriate timeouts for different task types
5. **Clean Up**: Ensure proper cleanup of temporary resources

### Performance Optimization

1. **Parallel Execution**: Use parallel testing for independent tasks
2. **Resource Limits**: Set appropriate memory and time limits
3. **Caching**: Cache dependency checks and environment setups
4. **Incremental Testing**: Build on previous test results

### Error Prevention

1. **Validate Configuration**: Check configuration before starting tests
2. **Test Environment**: Verify environment setup before task execution
3. **Monitor Logs**: Watch logs for early warning signs
4. **Graceful Degradation**: Handle partial failures gracefully

## Troubleshooting

### Common Problems and Solutions

#### Problem: "SWE-bench adapter module not found"
**Solution**: Ensure EvaluationEngineV1_0 is in your Python path:
```python
import sys
sys.path.insert(0, '/path/to/EvaluationEngineV1_0')
```

#### Problem: "Git not available"
**Solution**: Install git:
```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt-get install git

# Windows
# Download from https://git-scm.com/
```

#### Problem: "Environment setup failed"
**Solution**: Check file system permissions and available disk space:
```bash
# Check disk space
df -h

# Check permissions
ls -la /tmp
```

#### Problem: "Task execution timeout"
**Solution**: Increase timeout or optimize task selection:
```python
config = {
    "timeout": 1200,  # 20 minutes
    "test_task_count": 1  # Reduce task count
}
```

## Examples

### Complete Validation Example

```python
#!/usr/bin/env python3
"""Complete SWE-bench adapter validation example."""

import logging
from EvaluationEngineV1_0_tests.core.swe_bench_adapter_validator import SWEBenchAdapterValidator

# Setup logging
logging.basicConfig(level=logging.INFO)

def main():
    # Initialize validator
    validator = SWEBenchAdapterValidator({
        "timeout": 600,
        "test_task_count": 1
    })
    
    print("Starting SWE-bench adapter validation...")
    
    # Run validation
    result = validator.validate_integration()
    
    # Display results
    print(f"Status: {result.integration_status.value}")
    print(f"Dependencies: {result.dependencies_installed}")
    print(f"Tests: {len(result.test_results)}")
    
    if result.issues_found:
        print("Issues:")
        for issue in result.issues_found:
            print(f"  - {issue}")
    
    if result.recommendations:
        print("Recommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")
    
    return 0 if result.integration_status.value == "passed" else 1

if __name__ == "__main__":
    exit(main())
```

### Task-Specific Testing Example

```python
"""Test specific SWE-bench tasks."""

def test_specific_tasks():
    validator = SWEBenchAdapterValidator()
    
    # Test multiple tasks
    results = validator.test_software_tasks(task_count=3)
    
    # Analyze results
    passed = sum(1 for r in results if r.status.value == "passed")
    total = len(results)
    
    print(f"Task Results: {passed}/{total} passed")
    
    # Show detailed results
    for result in results:
        print(f"Task: {result.name}")
        print(f"  Status: {result.status.value}")
        print(f"  Time: {result.execution_time:.2f}s")
        print(f"  Real Execution: {result.real_execution_validated}")
        
        if result.metrics:
            print("  Metrics:")
            for metric, value in result.metrics.items():
                print(f"    {metric}: {value}")
```

## API Reference

### SWEBenchAdapterValidator Class

#### Constructor
```python
SWEBenchAdapterValidator(config: Optional[Dict[str, Any]] = None)
```

#### Methods

##### validate_integration() -> ValidationResult
Performs complete integration validation.

##### test_software_tasks(task_count: int = 1) -> List[TestResult]
Tests SWE-bench adapter with real software engineering tasks.

##### setup_environment() -> bool
Sets up the testing environment for SWE-bench tasks.

##### install_dependencies() -> bool
Installs and validates required dependencies.

##### get_adapter_info() -> AdapterInfo
Returns information about the SWE-bench adapter.

### Data Models

#### ValidationResult
Contains the results of adapter validation.

#### TestResult
Contains the results of individual test execution.

#### AdapterInfo
Contains information about the adapter capabilities.

## Contributing

### Adding New Tests

1. Create test methods following the pattern `_test_<functionality>`
2. Update the validation workflow in `validate_integration()`
3. Add appropriate error handling and logging
4. Update documentation and examples

### Extending Functionality

1. Add new configuration options to the constructor
2. Implement new validation methods
3. Update the data models if needed
4. Add comprehensive tests and documentation

For more information, see the [Contributing Guide](../CONTRIBUTING.md).