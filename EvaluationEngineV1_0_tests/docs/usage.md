# EvaluationEngineV1_0 Testing Framework - Complete Usage Guide

## Table of Contents

1. [Overview](#overview)
2. [Installation and Setup](#installation-and-setup)
3. [Quick Start](#quick-start)
4. [CLI Testing Interface](#cli-testing-interface)
5. [API Testing Interface](#api-testing-interface)
6. [Adapter Validation](#adapter-validation)
7. [Configuration Management](#configuration-management)
8. [Real Execution Validation](#real-execution-validation)
9. [Custom Task Testing](#custom-task-testing)
10. [Performance Testing](#performance-testing)
11. [Report Generation](#report-generation)
12. [Best Practices](#best-practices)
13. [Common Use Cases](#common-use-cases)

## Overview

The EvaluationEngineV1_0 Testing Framework provides comprehensive testing capabilities for the evaluation engine through both command-line and API interfaces. It validates core adapters, ensures real execution without mock data, and generates detailed reports.

### Key Features

- **Real Execution Testing**: All tests perform actual evaluations without mock data
- **Dual Interface Support**: Both CLI and REST API testing capabilities
- **Adapter Validation**: Specialized validators for lm_eval and swe_bench adapters
- **Custom Task Support**: Automatic discovery and testing of custom tasks
- **Comprehensive Reporting**: Detailed execution reports and performance analysis
- **Security Features**: Sandboxed execution and resource management
- **Error Handling**: Robust error detection and recovery mechanisms

## Installation and Setup

### Prerequisites

- Python 3.8 or higher
- EvaluationEngineV1_0 installed and configured
- Sufficient system resources for real execution testing
- Internet connection for downloading dependencies

### Installation Steps

1. **Clone or Navigate to the Testing Framework**:
   ```bash
   cd EvaluationEngineV1_0_tests
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r test_requirements.txt
   ```

3. **Verify Installation**:
   ```bash
   python simple_validation_demo.py
   ```

4. **Run Setup Validation**:
   ```bash
   python -m pytest tests/unit/test_config_manager.py -v
   ```

### Environment Configuration

Create a `.env` file in the testing framework root:

```bash
# API Configuration
API_HOST=localhost
API_PORT=8000
API_TIMEOUT=300

# Testing Configuration
TEST_TIMEOUT=600
MAX_CONCURRENT_TESTS=4
ENABLE_PERFORMANCE_MONITORING=true

# Security Configuration
ENABLE_SANDBOX=true
MAX_MEMORY_MB=2048
MAX_EXECUTION_TIME=1800

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=tests.log
ENABLE_DETAILED_LOGGING=true
```

## Quick Start

### 1. Basic CLI Testing

Test builtin tasks using the CLI interface:

```bash
# Run basic CLI test with builtin tasks
python cli/cli_main.py --test-type builtin --tasks "hellaswag,arc_easy" --config configs/basic_test_config.yaml

# Run with verbose output
python cli/cli_main.py --test-type builtin --tasks "hellaswag" --config configs/basic_test_config.yaml --verbose

# Test custom tasks
python cli/cli_main.py --test-type custom --task-dir ../lm_eval/tasks --config configs/basic_test_config.yaml
```

### 2. Basic API Testing

Start the API server and run tests:

```bash
# Start API test server
python api/api_test_server.py --host localhost --port 8000 &

# Run basic API tests using curl
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": ["hellaswag"],
    "model": "gpt-3.5-turbo",
    "config": {
      "num_fewshot": 5,
      "batch_size": 1
    }
  }'

# Check evaluation status
curl http://localhost:8000/api/v1/evaluations/{evaluation_id}/status

# Get results
curl http://localhost:8000/api/v1/evaluations/{evaluation_id}/results
```

### 3. Adapter Validation

Validate core adapters:

```bash
# Test lm_eval adapter
python adapters/lm_eval_adapter_validator.py --test-count 1 --install-deps

# Test swe_bench adapter
python adapters/swe_bench_adapter_validator.py --test-count 1 --setup-env

# Run comprehensive adapter validation
python demo_comprehensive_testing.py --adapters lm_eval,swe_bench
```

## CLI Testing Interface

### Command Structure

The CLI interface provides several testing modes:

```bash
python cli/cli_main.py [OPTIONS] COMMAND [ARGS]
```

### Available Commands

#### 1. Builtin Task Testing

Test built-in lm_eval tasks:

```bash
# Test specific tasks
python cli/cli_main.py --test-type builtin --tasks "hellaswag,arc_easy,winogrande" --config configs/basic_test_config.yaml

# Test with custom parameters
python cli/cli_main.py --test-type builtin --tasks "hellaswag" --config configs/advanced_test_config.yaml --num-fewshot 10 --batch-size 4

# Test with performance monitoring
python cli/cli_main.py --test-type builtin --tasks "arc_easy" --config configs/performance_test_config.yaml --monitor-performance
```

#### 2. Custom Task Testing

Test custom tasks from specified directories:

```bash
# Test all custom tasks in directory
python cli/cli_main.py --test-type custom --task-dir ../lm_eval/tasks --config configs/basic_test_config.yaml

# Test specific custom task
python cli/cli_main.py --test-type custom --task-dir ../lm_eval/tasks --task-name my_custom_task --config configs/basic_test_config.yaml

# Test with validation
python cli/cli_main.py --test-type custom --task-dir ../lm_eval/tasks --config configs/basic_test_config.yaml --validate-real-execution
```

#### 3. Adapter Testing

Test specific adapters:

```bash
# Test lm_eval adapter
python cli/cli_main.py --test-type adapter --adapter lm_eval --config configs/adapter_test_config.yaml

# Test swe_bench adapter
python cli/cli_main.py --test-type adapter --adapter swe_bench --config configs/adapter_test_config.yaml --setup-env

# Test all adapters
python cli/cli_main.py --test-type adapter --adapter all --config configs/comprehensive_test_config.yaml
```

#### 4. Pipeline Testing

Test complete evaluation pipeline:

```bash
# Run full pipeline test
python cli/cli_main.py --test-type pipeline --config configs/pipeline_test_config.yaml

# Pipeline with performance analysis
python cli/cli_main.py --test-type pipeline --config configs/performance_test_config.yaml --analyze-performance

# Pipeline with detailed reporting
python cli/cli_main.py --test-type pipeline --config configs/comprehensive_test_config.yaml --generate-reports
```

### CLI Configuration Options

#### Command Line Arguments

- `--test-type`: Type of test (builtin, custom, adapter, pipeline)
- `--tasks`: Comma-separated list of task names
- `--task-dir`: Directory containing custom tasks
- `--adapter`: Adapter name to test
- `--config`: Configuration file path
- `--verbose`: Enable verbose output
- `--monitor-performance`: Enable performance monitoring
- `--validate-real-execution`: Validate real execution
- `--generate-reports`: Generate detailed reports
- `--output-dir`: Output directory for results
- `--timeout`: Test timeout in seconds

#### Configuration File Format

```yaml
# Basic CLI Test Configuration
test_config:
  execution:
    timeout: 600
    max_retries: 3
    parallel_execution: false
  
  validation:
    validate_real_execution: true
    check_resource_usage: true
    verify_no_mocks: true
  
  output:
    format: "json"
    save_logs: true
    generate_reports: true
    output_directory: "./test_results"
  
  performance:
    monitor_memory: true
    monitor_cpu: true
    benchmark_execution: true
    
model_config:
  model_name: "gpt-3.5-turbo"
  api_key: "${OPENAI_API_KEY}"
  max_tokens: 1024
  temperature: 0.0

task_config:
  num_fewshot: 5
  batch_size: 1
  limit: null
  
logging:
  level: "INFO"
  file: "cli_tests.log"
  detailed: true
```

## API Testing Interface

### API Server Setup

#### Starting the API Server

```bash
# Start with default settings
python api/api_test_server.py

# Start with custom host and port
python api/api_test_server.py --host 0.0.0.0 --port 9000

# Start with authentication enabled
python api/api_test_server.py --enable-auth --auth-token your_secret_token

# Start with performance monitoring
python api/api_test_server.py --monitor-performance --log-requests
```

#### Server Configuration

```python
# api_server_config.py
API_CONFIG = {
    "host": "localhost",
    "port": 8000,
    "debug": False,
    "enable_cors": True,
    "max_request_size": "16MB",
    "request_timeout": 300,
    "enable_authentication": False,
    "rate_limiting": {
        "enabled": True,
        "requests_per_minute": 60
    },
    "monitoring": {
        "enable_metrics": True,
        "log_requests": True,
        "track_performance": True
    }
}
```

### API Endpoints

#### 1. Evaluation Management

**Start Evaluation**
```bash
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": ["hellaswag", "arc_easy"],
    "model": "gpt-3.5-turbo",
    "config": {
      "num_fewshot": 5,
      "batch_size": 1,
      "limit": 10
    },
    "validation": {
      "validate_real_execution": true,
      "check_performance": true
    }
  }'
```

**Check Evaluation Status**
```bash
curl http://localhost:8000/api/v1/evaluations/{evaluation_id}/status
```

**Get Evaluation Results**
```bash
curl http://localhost:8000/api/v1/evaluations/{evaluation_id}/results
```

**Cancel Evaluation**
```bash
curl -X DELETE http://localhost:8000/api/v1/evaluations/{evaluation_id}
```

#### 2. Task Management

**List Available Tasks**
```bash
curl http://localhost:8000/api/v1/tasks
```

**Get Task Details**
```bash
curl http://localhost:8000/api/v1/tasks/{task_name}
```

**Validate Custom Task**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/validate \
  -H "Content-Type: application/json" \
  -d '{
    "task_definition": {
      "task": "custom_task",
      "dataset_path": "path/to/dataset",
      "description": "Custom task description"
    }
  }'
```

#### 3. Adapter Management

**List Available Adapters**
```bash
curl http://localhost:8000/api/v1/adapters
```

**Test Adapter**
```bash
curl -X POST http://localhost:8000/api/v1/adapters/{adapter_name}/test \
  -H "Content-Type: application/json" \
  -d '{
    "test_config": {
      "task_count": 1,
      "install_dependencies": true,
      "validate_integration": true
    }
  }'
```

**Get Adapter Status**
```bash
curl http://localhost:8000/api/v1/adapters/{adapter_name}/status
```

#### 4. System Management

**Health Check**
```bash
curl http://localhost:8000/api/v1/health
```

**System Status**
```bash
curl http://localhost:8000/api/v1/status
```

**Performance Metrics**
```bash
curl http://localhost:8000/api/v1/metrics
```

### API Client Usage

#### Python API Client

```python
from api.api_test_client import APITestClient

# Initialize client
client = APITestClient(base_url="http://localhost:8000")

# Start evaluation
evaluation_id = client.start_evaluation(
    tasks=["hellaswag", "arc_easy"],
    model="gpt-3.5-turbo",
    config={
        "num_fewshot": 5,
        "batch_size": 1
    }
)

# Monitor evaluation
status = client.get_evaluation_status(evaluation_id)
while status["state"] == "running":
    time.sleep(30)
    status = client.get_evaluation_status(evaluation_id)

# Get results
results = client.get_evaluation_results(evaluation_id)
print(f"Evaluation completed with results: {results}")
```

#### Concurrent Testing

```python
import asyncio
from api.async_evaluation_manager import AsyncEvaluationManager

async def run_concurrent_evaluations():
    manager = AsyncEvaluationManager(base_url="http://localhost:8000")
    
    # Define multiple evaluation configs
    configs = [
        {"tasks": ["hellaswag"], "model": "gpt-3.5-turbo"},
        {"tasks": ["arc_easy"], "model": "gpt-3.5-turbo"},
        {"tasks": ["winogrande"], "model": "gpt-3.5-turbo"}
    ]
    
    # Run evaluations concurrently
    results = await manager.run_concurrent_evaluations(configs)
    
    for result in results:
        print(f"Evaluation {result['id']}: {result['status']}")

# Run concurrent tests
asyncio.run(run_concurrent_evaluations())
```

## Adapter Validation

### lm_eval Adapter Validation

#### Basic Validation

```python
from adapters.lm_eval_adapter_validator import LMEvalAdapterValidator

# Initialize validator
validator = LMEvalAdapterValidator()

# Install dependencies
validator.install_dependencies()

# Validate integration
result = validator.validate_integration()
print(f"Integration status: {result.status}")

# Test builtin tasks
test_results = validator.test_builtin_tasks(task_count=2)
for result in test_results:
    print(f"Task {result.task_name}: {result.status}")
```

#### Advanced Validation

```python
# Test with custom configuration
config = {
    "model": "gpt-3.5-turbo",
    "num_fewshot": 10,
    "batch_size": 4,
    "limit": 50
}

validator = LMEvalAdapterValidator(config=config)

# Test specific tasks
tasks = ["hellaswag", "arc_easy", "winogrande"]
results = validator.test_specific_tasks(tasks)

# Validate real execution
for result in results:
    is_real = validator.validate_real_execution(result)
    print(f"Task {result.task_name} real execution: {is_real}")
```

#### Custom Task Testing

```python
# Test custom tasks from directory
custom_task_dir = "../lm_eval/tasks"
custom_results = validator.test_custom_tasks(custom_task_dir)

for result in custom_results:
    print(f"Custom task {result.task_name}: {result.status}")
    if result.errors:
        print(f"Errors: {result.errors}")
```

### swe_bench Adapter Validation

#### Basic Validation

```python
from adapters.swe_bench_adapter_validator import SWEBenchAdapterValidator

# Initialize validator
validator = SWEBenchAdapterValidator()

# Setup environment
validator.setup_environment()

# Install dependencies
validator.install_dependencies()

# Validate integration
result = validator.validate_integration()
print(f"SWE-bench integration: {result.status}")

# Test software engineering tasks
test_results = validator.test_software_tasks(task_count=1)
for result in test_results:
    print(f"SWE task {result.task_id}: {result.status}")
```

#### Environment Setup

```python
# Custom environment setup
env_config = {
    "python_version": "3.9",
    "install_requirements": True,
    "setup_git": True,
    "configure_ssh": False
}

validator = SWEBenchAdapterValidator(env_config=env_config)
validator.setup_environment()

# Test with specific repository
repo_config = {
    "repo_url": "https://github.com/example/repo",
    "branch": "main",
    "commit": "abc123"
}

result = validator.test_repository_task(repo_config)
print(f"Repository test: {result.status}")
```

## Configuration Management

### Configuration File Structure

#### Basic Configuration

```yaml
# basic_test_config.yaml
test_framework:
  name: "EvaluationEngineV1_0_Tests"
  version: "1.0"
  
execution:
  timeout: 600
  max_retries: 3
  parallel_execution: false
  validate_real_execution: true
  
model:
  name: "gpt-3.5-turbo"
  api_key: "${OPENAI_API_KEY}"
  max_tokens: 1024
  temperature: 0.0
  
tasks:
  builtin:
    - "hellaswag"
    - "arc_easy"
  custom_task_dir: "../lm_eval/tasks"
  
output:
  format: "json"
  directory: "./test_results"
  save_logs: true
  generate_reports: true
  
logging:
  level: "INFO"
  file: "tests.log"
  detailed: true
```

#### Advanced Configuration

```yaml
# advanced_test_config.yaml
test_framework:
  name: "Advanced_EvaluationEngine_Tests"
  version: "1.0"
  
execution:
  timeout: 1800
  max_retries: 5
  parallel_execution: true
  max_parallel_tasks: 4
  validate_real_execution: true
  check_resource_usage: true
  
model:
  name: "gpt-4"
  api_key: "${OPENAI_API_KEY}"
  max_tokens: 2048
  temperature: 0.0
  top_p: 1.0
  frequency_penalty: 0.0
  presence_penalty: 0.0
  
tasks:
  builtin:
    - name: "hellaswag"
      config:
        num_fewshot: 10
        batch_size: 4
        limit: 100
    - name: "arc_easy"
      config:
        num_fewshot: 25
        batch_size: 2
        limit: 50
  
  custom:
    task_dir: "../lm_eval/tasks"
    include_patterns: ["*.py", "*.yaml"]
    exclude_patterns: ["*test*", "*debug*"]
  
adapters:
  lm_eval:
    enabled: true
    install_dependencies: true
    test_count: 3
    validate_integration: true
  
  swe_bench:
    enabled: true
    setup_environment: true
    test_count: 1
    validate_integration: true
  
performance:
  monitor_memory: true
  monitor_cpu: true
  monitor_network: true
  benchmark_execution: true
  profile_code: false
  
security:
  enable_sandbox: true
  max_memory_mb: 4096
  max_execution_time: 3600
  allowed_network_hosts: ["api.openai.com"]
  
output:
  format: "json"
  directory: "./advanced_test_results"
  save_logs: true
  generate_reports: true
  include_performance_data: true
  include_security_audit: true
  
logging:
  level: "DEBUG"
  file: "advanced_tests.log"
  detailed: true
  include_timestamps: true
  rotate_logs: true
  max_log_size_mb: 100
```

### Configuration Validation

```python
from core.config_manager import ConfigManager

# Load and validate configuration
config_manager = ConfigManager()
config = config_manager.load_config("configs/advanced_test_config.yaml")

# Validate configuration
validation_result = config_manager.validate_config(config)
if not validation_result.is_valid:
    print(f"Configuration errors: {validation_result.errors}")
    exit(1)

# Get validated configuration
validated_config = config_manager.get_validated_config()
print(f"Configuration loaded successfully: {validated_config.test_framework.name}")
```

## Real Execution Validation

### Validation Components

The framework includes comprehensive real execution validation to ensure no mock data is used:

#### 1. Mock Detection

```python
from core.real_execution_validator import RealExecutionValidator

validator = RealExecutionValidator()

# Check for mock objects
has_mocks = validator.detect_mock_usage(execution_context)
if has_mocks:
    print("Warning: Mock objects detected in execution")

# Validate API calls
api_calls = validator.validate_api_calls(request_logs)
print(f"Real API calls made: {len(api_calls)}")
```

#### 2. Resource Consumption Validation

```python
# Monitor resource usage
metrics = validator.monitor_resource_usage(execution_id)
print(f"Memory usage: {metrics.memory_mb}MB")
print(f"CPU usage: {metrics.cpu_percent}%")
print(f"Network requests: {metrics.network_requests}")

# Validate realistic resource patterns
is_realistic = validator.validate_resource_patterns(metrics)
print(f"Resource usage realistic: {is_realistic}")
```

#### 3. Result Authenticity Validation

```python
# Validate result authenticity
results = get_evaluation_results(evaluation_id)
is_authentic = validator.validate_result_authenticity(results)

if is_authentic:
    print("Results validated as authentic")
else:
    print("Warning: Results may not be from real execution")
```

### Validation Configuration

```yaml
# real_execution_validation.yaml
validation:
  mock_detection:
    enabled: true
    check_unittest_mock: true
    check_pytest_mock: true
    check_custom_mocks: true
    
  api_validation:
    enabled: true
    verify_network_calls: true
    check_response_authenticity: true
    validate_rate_limiting: true
    
  resource_monitoring:
    enabled: true
    monitor_memory: true
    monitor_cpu: true
    monitor_network: true
    monitor_disk_io: true
    
  result_validation:
    enabled: true
    check_result_variance: true
    validate_execution_time: true
    verify_model_responses: true
    
thresholds:
  min_memory_usage_mb: 50
  min_execution_time_seconds: 5
  min_network_requests: 1
  max_result_similarity: 0.95
```

## Custom Task Testing

### Task Discovery

The framework automatically discovers custom tasks in specified directories:

```python
from core.task_discovery import TaskDiscovery

# Initialize task discovery
discovery = TaskDiscovery()

# Discover tasks in directory
tasks = discovery.discover_tasks("../lm_eval/tasks")
print(f"Found {len(tasks)} custom tasks")

for task in tasks:
    print(f"Task: {task.name}, Type: {task.type}, Path: {task.path}")
```

### Task Validation

```python
from core.task_validator import TaskValidator

validator = TaskValidator()

# Validate task structure
for task in tasks:
    validation_result = validator.validate_task(task)
    if validation_result.is_valid:
        print(f"Task {task.name} is valid")
    else:
        print(f"Task {task.name} validation errors: {validation_result.errors}")
```

### Custom Task Execution

```python
from core.custom_task_executor import CustomTaskExecutor

executor = CustomTaskExecutor()

# Execute custom task
config = {
    "model": "gpt-3.5-turbo",
    "num_fewshot": 5,
    "batch_size": 1
}

result = executor.execute_task(task, config)
print(f"Task {task.name} result: {result.score}")
```

### Task Format Support

The framework supports multiple custom task formats:

#### 1. Python Task Files

```python
# custom_task.py
from lm_eval.api.task import Task

class CustomTask(Task):
    VERSION = 1
    DATASET_PATH = "path/to/dataset"
    DATASET_NAME = "custom_dataset"
    
    def has_training_docs(self):
        return False
    
    def has_validation_docs(self):
        return True
    
    def has_test_docs(self):
        return True
    
    def validation_docs(self):
        # Return validation documents
        pass
    
    def test_docs(self):
        # Return test documents
        pass
    
    def doc_to_text(self, doc):
        # Convert document to text
        pass
    
    def doc_to_target(self, doc):
        # Extract target from document
        pass
```

#### 2. YAML Task Definitions

```yaml
# custom_task.yaml
task: custom_task
dataset_path: path/to/dataset
dataset_name: custom_dataset
description: "Custom task description"

output_type: generate_until
training_split: null
validation_split: validation
test_split: test

doc_to_text: "Question: {{question}}\nAnswer:"
doc_to_target: "{{answer}}"

generation_kwargs:
  max_gen_toks: 100
  temperature: 0.0
  do_sample: false

metric_list:
  - metric: exact_match
  - metric: bleu

metadata:
  version: 1.0
  author: "Test Framework"
```

## Performance Testing

### Performance Monitoring

```python
from core.performance_monitor import PerformanceMonitor

# Initialize performance monitor
monitor = PerformanceMonitor()

# Start monitoring
monitor.start_monitoring(evaluation_id)

# Execute evaluation
results = run_evaluation(config)

# Stop monitoring and get metrics
metrics = monitor.stop_monitoring(evaluation_id)

print(f"Execution time: {metrics.total_time}s")
print(f"Memory peak: {metrics.peak_memory_mb}MB")
print(f"CPU average: {metrics.avg_cpu_percent}%")
```

### Performance Benchmarking

```python
from core.performance_benchmarker import PerformanceBenchmarker

benchmarker = PerformanceBenchmarker()

# Define benchmark configuration
benchmark_config = {
    "tasks": ["hellaswag", "arc_easy"],
    "models": ["gpt-3.5-turbo", "gpt-4"],
    "batch_sizes": [1, 2, 4],
    "iterations": 3
}

# Run benchmark
benchmark_results = benchmarker.run_benchmark(benchmark_config)

# Analyze results
analysis = benchmarker.analyze_results(benchmark_results)
print(f"Best configuration: {analysis.best_config}")
print(f"Performance improvement: {analysis.improvement_percent}%")
```

### Performance Configuration

```yaml
# performance_test_config.yaml
performance:
  monitoring:
    enabled: true
    sample_interval: 1.0
    metrics:
      - memory
      - cpu
      - network
      - disk_io
  
  benchmarking:
    enabled: true
    iterations: 3
    warmup_iterations: 1
    
  profiling:
    enabled: false
    profile_code: false
    profile_memory: false
    
  optimization:
    parallel_execution: true
    max_workers: 4
    batch_optimization: true
    cache_results: true
    
thresholds:
  max_execution_time: 1800
  max_memory_mb: 4096
  max_cpu_percent: 90
  min_throughput_tasks_per_hour: 10
```

## Report Generation

### Automated Report Generation

```python
from reports.test_report_generator import TestReportGenerator

# Initialize report generator
generator = TestReportGenerator()

# Generate comprehensive report
report = generator.generate_comprehensive_report(test_results)

# Save report
generator.save_report(report, "test_report.html")
print(f"Report saved to: test_report.html")
```

### Report Types

#### 1. Execution Summary Report

```python
# Generate execution summary
summary_report = generator.generate_execution_summary(test_results)
print(summary_report.to_string())
```

#### 2. Performance Analysis Report

```python
# Generate performance report
performance_report = generator.generate_performance_report(performance_metrics)
generator.save_report(performance_report, "performance_report.pdf")
```

#### 3. Adapter Validation Report

```python
# Generate adapter validation report
adapter_report = generator.generate_adapter_report(adapter_results)
generator.save_report(adapter_report, "adapter_validation.json")
```

### Custom Report Templates

```python
# Create custom report template
template = {
    "title": "Custom Evaluation Report",
    "sections": [
        "executive_summary",
        "test_results",
        "performance_metrics",
        "error_analysis",
        "recommendations"
    ],
    "format": "html",
    "include_charts": True,
    "include_raw_data": False
}

custom_report = generator.generate_custom_report(test_results, template)
```

## Best Practices

### 1. Test Organization

- **Separate Test Types**: Keep CLI, API, and adapter tests in separate directories
- **Use Descriptive Names**: Name test files and functions clearly
- **Group Related Tests**: Organize tests by functionality or component
- **Version Control**: Track test configurations and results

### 2. Configuration Management

- **Environment-Specific Configs**: Use different configs for dev, test, and prod
- **Secure Credentials**: Use environment variables for API keys
- **Validate Configurations**: Always validate configs before execution
- **Document Settings**: Comment configuration files thoroughly

### 3. Real Execution Validation

- **Always Validate**: Enable real execution validation for all tests
- **Monitor Resources**: Track memory, CPU, and network usage
- **Check API Calls**: Verify actual API calls are made
- **Validate Results**: Ensure results are authentic and varied

### 4. Error Handling

- **Comprehensive Logging**: Log all errors with context
- **Graceful Degradation**: Continue testing when possible
- **Retry Logic**: Implement retries for transient failures
- **Clear Error Messages**: Provide actionable error information

### 5. Performance Optimization

- **Parallel Execution**: Use parallel processing when appropriate
- **Batch Operations**: Group similar operations together
- **Resource Management**: Monitor and limit resource usage
- **Caching**: Cache results when appropriate

### 6. Security Considerations

- **Sandbox Execution**: Use sandboxed environments for testing
- **Resource Limits**: Set appropriate resource limits
- **Input Validation**: Validate all inputs thoroughly
- **Secure Storage**: Protect sensitive test data

## Common Use Cases

### 1. Continuous Integration Testing

```bash
#!/bin/bash
# ci_test_script.sh

# Set up environment
export OPENAI_API_KEY=$CI_OPENAI_API_KEY
export TEST_TIMEOUT=1800

# Run basic validation
python simple_validation_demo.py

# Run CLI tests
python cli/cli_main.py --test-type builtin --tasks "hellaswag" --config configs/ci_config.yaml

# Run API tests
python api/api_test_server.py --host localhost --port 8000 &
SERVER_PID=$!
sleep 10

curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Content-Type: application/json" \
  -d '{"tasks": ["hellaswag"], "model": "gpt-3.5-turbo"}'

kill $SERVER_PID

# Run adapter validation
python adapters/lm_eval_adapter_validator.py --test-count 1

echo "CI tests completed successfully"
```

### 2. Development Testing

```python
# dev_test_suite.py
import sys
from pathlib import Path

# Add testing framework to path
sys.path.append(str(Path(__file__).parent))

from core.test_orchestrator import TestOrchestrator
from core.config_manager import ConfigManager

def run_development_tests():
    """Run comprehensive development test suite"""
    
    # Load development configuration
    config_manager = ConfigManager()
    config = config_manager.load_config("configs/dev_config.yaml")
    
    # Initialize test orchestrator
    orchestrator = TestOrchestrator(config)
    
    # Run quick validation tests
    print("Running quick validation tests...")
    quick_results = orchestrator.run_quick_validation()
    
    if not quick_results.all_passed:
        print("Quick validation failed, stopping tests")
        return False
    
    # Run adapter tests
    print("Running adapter validation...")
    adapter_results = orchestrator.run_adapter_validation()
    
    # Run custom task tests
    print("Running custom task tests...")
    custom_results = orchestrator.run_custom_task_tests()
    
    # Generate development report
    print("Generating development report...")
    report = orchestrator.generate_development_report()
    
    print(f"Development tests completed: {report.summary}")
    return report.all_passed

if __name__ == "__main__":
    success = run_development_tests()
    sys.exit(0 if success else 1)
```

### 3. Production Validation

```python
# production_validation.py
from core.production_validator import ProductionValidator
from core.security_validator import SecurityValidator

def validate_production_deployment():
    """Validate production deployment"""
    
    # Initialize validators
    prod_validator = ProductionValidator()
    security_validator = SecurityValidator()
    
    # Run security validation
    security_results = security_validator.validate_security()
    if not security_results.passed:
        print(f"Security validation failed: {security_results.issues}")
        return False
    
    # Run production readiness tests
    prod_results = prod_validator.validate_production_readiness()
    if not prod_results.ready:
        print(f"Production validation failed: {prod_results.issues}")
        return False
    
    # Run load testing
    load_results = prod_validator.run_load_tests()
    if not load_results.passed:
        print(f"Load testing failed: {load_results.issues}")
        return False
    
    print("Production validation completed successfully")
    return True

if __name__ == "__main__":
    validate_production_deployment()
```

### 4. Custom Adapter Development

```python
# custom_adapter_development.py
from adapters.adapter_validator import AdapterValidator
from core.custom_adapter_tester import CustomAdapterTester

def develop_custom_adapter():
    """Develop and test custom adapter"""
    
    # Create custom adapter
    adapter_code = """
    class CustomAdapter:
        def __init__(self, config):
            self.config = config
        
        def execute_task(self, task, model_config):
            # Custom adapter implementation
            pass
    """
    
    # Save adapter code
    with open("custom_adapter.py", "w") as f:
        f.write(adapter_code)
    
    # Test custom adapter
    tester = CustomAdapterTester()
    test_results = tester.test_adapter("custom_adapter.py")
    
    # Validate adapter
    validator = AdapterValidator()
    validation_results = validator.validate_adapter("custom_adapter.py")
    
    print(f"Custom adapter test results: {test_results.summary}")
    print(f"Custom adapter validation: {validation_results.summary}")
    
    return test_results.passed and validation_results.passed

if __name__ == "__main__":
    develop_custom_adapter()
```

This comprehensive usage guide provides detailed instructions for using all aspects of the EvaluationEngineV1_0 Testing Framework. For additional help, refer to the API documentation, troubleshooting guide, and developer guide in this documentation folder.