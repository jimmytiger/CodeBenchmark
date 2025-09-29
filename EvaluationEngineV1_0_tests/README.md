# EvaluationEngineV1_0 Testing Framework

A comprehensive testing framework for EvaluationEngineV1_0 that provides CLI testing, API testing, adapter validation, and real execution verification.

## Features

- **CLI Testing**: Test command-line interfaces with builtin and custom tasks
- **API Testing**: REST API testing with curl command generation and programmatic clients
- **Adapter Validation**: Validate core adapters (lm_eval, swe_bench, etc.)
- **Real Execution Validation**: Ensure tests perform actual execution without mocks
- **Pipeline Testing**: End-to-end pipeline validation
- **Comprehensive Reporting**: Generate detailed reports in multiple formats

## Quick Start

### 1. Installation

```bash
# Install required dependencies
pip install -r requirements.txt

# Install additional packages for full functionality
pip install flask flask-cors aiohttp requests psutil pyyaml click
```

### 2. Run the Demonstration

```bash
# Run comprehensive demonstration
python -m EvaluationEngineV1_0_tests.demo_comprehensive_testing
```

### 3. CLI Testing

```bash
# Test builtin tasks
python -m EvaluationEngineV1_0_tests.cli.cli_main builtin --tasks hellaswag arc_easy --verbose

# Test custom tasks
python -m EvaluationEngineV1_0_tests.cli.cli_main custom --task-dir lm_eval/tasks --verbose

# Test specific adapter
python -m EvaluationEngineV1_0_tests.cli.cli_main adapters --adapter lm_eval --verbose

# Test full pipeline
python -m EvaluationEngineV1_0_tests.cli.cli_main pipeline --verbose
```

### 4. API Testing

```python
from EvaluationEngineV1_0_tests.api import APITestServer, APITestClient

# Start test server
server = APITestServer(host="localhost", port=8000)
server.start_server()

# Test with client
client = APITestClient(base_url="http://localhost:8000")
success, result = client.test_health_check()
print(f"Health check: {success}")

# Clean up
client.close()
server.stop_server()
```

### 5. Generate Curl Commands

```python
from EvaluationEngineV1_0_tests.api import CurlTestGenerator

generator = CurlTestGenerator(base_url="http://localhost:8000")

# Generate individual commands
health_cmd = generator.generate_health_check()
print(health_cmd)

# Generate comprehensive test script
config = {"model_id": "test_model", "tasks": ["hellaswag"]}
script = generator.generate_comprehensive_test_script(config)

# Save script
from pathlib import Path
generator.save_test_script(script, Path("api_test.sh"))
```

## Directory Structure

```
EvaluationEngineV1_0_tests/
├── __init__.py                 # Package initialization
├── README.md                   # This file
├── demo_comprehensive_testing.py  # Comprehensive demonstration
├── models/                     # Data models
│   ├── __init__.py
│   └── test_models.py         # Core data models
├── core/                       # Core testing framework
│   ├── __init__.py
│   ├── test_orchestrator.py   # Central test orchestration
│   ├── real_execution_validator.py  # Real execution validation
│   ├── pipeline_validator.py  # Pipeline validation
│   ├── metrics_collector.py   # Performance metrics
│   ├── config_manager.py      # Configuration management
│   ├── error_handler.py       # Error handling
│   ├── lm_eval_adapter_validator.py  # LM-eval adapter validation
│   └── swe_bench_adapter_validator.py  # SWE-bench adapter validation
├── cli/                        # CLI testing interface
│   ├── __init__.py
│   ├── cli_main.py            # CLI entry point
│   ├── cli_test_runner.py     # CLI test execution
│   ├── cli_config_manager.py  # CLI configuration
│   └── cli_result_formatter.py # Result formatting
├── api/                        # API testing interface
│   ├── __init__.py
│   ├── api_test_server.py     # Test API server
│   ├── curl_test_generator.py # Curl command generation
│   ├── api_test_client.py     # Programmatic API client
│   └── async_evaluation_manager.py # Async API testing
├── adapters/                   # Adapter validation (to be implemented)
│   └── __init__.py
└── configs/                    # Configuration files
    └── default_config.yaml    # Default configuration
```

## Configuration

### Default Configuration

The framework uses YAML configuration files. See `configs/default_config.yaml` for the default configuration.

### CLI Configuration

```yaml
cli_config:
  tasks:
    - "hellaswag"
    - "arc_easy"
  adapters:
    - "lm_eval"
  execution_timeout: 300
  output_format: "json"
  verbose: true
```

### API Configuration

```yaml
api_config:
  server_host: "localhost"
  server_port: 8000
  test_endpoints:
    - "/api/v1/evaluations"
    - "/api/v1/tasks"
    - "/api/v1/adapters"
  concurrent_requests: 5
  timeout: 30
```

## Testing Components

### 1. CLI Testing

Test command-line interfaces with various task types:

- **Builtin Tasks**: Test with standard evaluation tasks
- **Custom Tasks**: Test with tasks from custom directories
- **Adapter Tests**: Validate specific adapters
- **Pipeline Tests**: End-to-end pipeline validation

### 2. API Testing

Test REST API endpoints:

- **Health Checks**: Verify server status
- **Evaluation Management**: Create, monitor, and retrieve evaluations
- **Task Discovery**: List available tasks and adapters
- **Concurrent Testing**: Test multiple simultaneous requests

### 3. Real Execution Validation

Ensure tests perform actual execution:

- **Mock Detection**: Identify and flag mock objects
- **Resource Monitoring**: Track memory and CPU usage
- **API Call Validation**: Verify actual API calls are made
- **Timing Analysis**: Validate realistic execution times

### 4. Adapter Validation

Validate core adapters:

- **lm_eval Adapter**: Integration with lm-evaluation-harness
- **SWE-bench Adapter**: Software engineering task validation with real repository operations
- **Dependency Checking**: Verify required dependencies (git, python, pip, pytest)
- **Performance Benchmarking**: Measure adapter performance and resource usage
- **Environment Setup**: Automated testing environment creation and cleanup

## Examples

### Basic CLI Test

```bash
python -m EvaluationEngineV1_0_tests.cli.cli_main builtin \
  --tasks hellaswag \
  --timeout 300 \
  --output results.json \
  --format json \
  --verbose
```

### API Test with Curl

```bash
# Generated curl command
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"model_id": "test_model", "tasks": ["hellaswag"]}' \
  http://localhost:8000/api/v1/evaluations
```

### Programmatic Testing

```python
from EvaluationEngineV1_0_tests.core import TestOrchestrator

# Create orchestrator
orchestrator = TestOrchestrator()

# Define test suite
suite_config = {
    "suite_name": "My Test Suite",
    "cli_tests": {"tasks": ["hellaswag"]},
    "api_tests": {"endpoints": ["/health"]},
    "parallel": False
}

# Execute tests
results = orchestrator.execute_test_suite(suite_config)
print(f"Success rate: {results.success_rate:.1%}")
```

### SWE-bench Adapter Testing

```python
from EvaluationEngineV1_0_tests.core.swe_bench_adapter_validator import SWEBenchAdapterValidator

# Initialize validator
validator = SWEBenchAdapterValidator({
    "timeout": 600,
    "test_task_count": 1
})

# Run full validation
validation_result = validator.validate_integration()
print(f"Status: {validation_result.integration_status.value}")
print(f"Dependencies: {validation_result.dependencies_installed}")

# Test specific software tasks
task_results = validator.test_software_tasks(1)
for result in task_results:
    print(f"Task: {result.name} - {result.status.value}")
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Port Conflicts**: Change API server port if 8000 is in use
3. **Timeout Issues**: Increase timeout values for slow systems
4. **Permission Errors**: Ensure write permissions for output directories

### Debug Mode

Enable verbose logging for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Log Files

Check log files for detailed execution information:
- `demo_testing.log`: Demonstration execution log
- `test_framework.log`: General framework log

## Contributing

1. Follow the existing code structure
2. Add comprehensive tests for new features
3. Update documentation for new functionality
4. Ensure real execution validation works with new components

## License

This testing framework is part of the EvaluationEngineV1_0 project.