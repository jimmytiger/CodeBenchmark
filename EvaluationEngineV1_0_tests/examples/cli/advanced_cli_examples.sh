#!/bin/bash
# Advanced CLI Examples for EvaluationEngineV1_0 Testing Framework
# This script demonstrates advanced command-line usage patterns

set -e  # Exit on any error

echo "=== EvaluationEngineV1_0 Advanced CLI Examples ==="
echo "This script demonstrates advanced CLI testing capabilities"
echo

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$(dirname "$SCRIPT_DIR")"
TEST_FRAMEWORK_DIR="$(dirname "$EXAMPLES_DIR")"
RESULTS_DIR="$EXAMPLES_DIR/results/cli_advanced"

# Create results directory
mkdir -p "$RESULTS_DIR"

echo "Results will be saved to: $RESULTS_DIR"
echo

# Function to run advanced CLI test
run_advanced_test() {
    local test_name="$1"
    local command="$2"
    local description="$3"
    
    echo "=== $test_name ==="
    echo "Description: $description"
    echo "Command: $command"
    echo
    
    # Run the command and capture output
    if eval "$command" > "$RESULTS_DIR/${test_name,,}.log" 2>&1; then
        echo "✓ $test_name completed successfully"
        echo "  Results saved to: $RESULTS_DIR/${test_name,,}.log"
        
        # Show summary if available
        if grep -q "Test Summary" "$RESULTS_DIR/${test_name,,}.log"; then
            echo "  Summary:"
            grep -A 10 "Test Summary" "$RESULTS_DIR/${test_name,,}.log" | head -5 | sed 's/^/    /'
        fi
    else
        echo "✗ $test_name failed"
        echo "  Error log saved to: $RESULTS_DIR/${test_name,,}.log"
        echo "  Last few lines of error:"
        tail -5 "$RESULTS_DIR/${test_name,,}.log" | sed 's/^/    /'
    fi
    echo
}

# Example 1: Multiple Task Testing
echo "1. Multiple Task Testing"
echo "======================="
run_advanced_test "Multiple_Tasks" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
import json
import time

runner = CLITestRunner()
config = {
    \"timeout\": 300,
    \"verbose\": True,
    \"output_format\": \"json\",
    \"limit\": 2  # Small sample for each task
}

tasks = [\"hellaswag\", \"arc_easy\"]
print(f\"Testing multiple tasks: {tasks}\")

start_time = time.time()
result = runner.run_builtin_tasks(tasks, config)
total_time = time.time() - start_time

print(\"=== Multiple Task Test Summary ===\")
print(f\"Tasks tested: {len(tasks)}\")
print(f\"Overall success: {result[\"success\"]}\")
print(f\"Total execution time: {total_time:.2f}s\")
print(f\"Average time per task: {total_time/len(tasks):.2f}s\")

if result.get(\"metrics\"):
    print(\"Combined metrics:\")
    for key, value in result[\"metrics\"].items():
        print(f\"  {key}: {value}\")
'" \
    "Test multiple tasks in a single run"

# Example 2: Custom Task Discovery and Testing
echo "2. Custom Task Discovery and Testing"
echo "===================================="
run_advanced_test "Custom_Task_Discovery" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
from pathlib import Path
import os

runner = CLITestRunner()

# Check for custom task directory
custom_task_dir = Path(\"lm_eval/tasks\")
if custom_task_dir.exists():
    print(f\"Found custom task directory: {custom_task_dir}\")
    
    # Discover custom tasks
    custom_tasks = runner.discover_custom_tasks(custom_task_dir)
    print(f\"Discovered {len(custom_tasks)} custom tasks:\")
    for task in custom_tasks[:5]:  # Show first 5
        print(f\"  - {task}\")
    
    if custom_tasks:
        # Test first custom task
        config = {
            \"timeout\": 180,
            \"verbose\": True,
            \"output_format\": \"json\",
            \"limit\": 1
        }
        
        print(f\"\\nTesting custom task: {custom_tasks[0]}\")
        result = runner.run_custom_tasks(custom_task_dir, config)
        print(f\"Custom task test result: {result[\"success\"]}\")
        
        if result.get(\"metrics\"):
            print(\"Custom task metrics:\")
            for key, value in result[\"metrics\"].items():
                print(f\"  {key}: {value}\")
    else:
        print(\"No custom tasks found to test\")
else:
    print(f\"Custom task directory not found: {custom_task_dir}\")
    print(\"Skipping custom task discovery test\")
'" \
    "Discover and test custom tasks from lm_eval/tasks directory"

# Example 3: Performance Benchmarking
echo "3. Performance Benchmarking"
echo "==========================="
run_advanced_test "Performance_Benchmark" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
from core.metrics_collector import MetricsCollector
import time
import psutil
import os

runner = CLITestRunner()
metrics_collector = MetricsCollector()

# Start metrics collection
metrics_collector.start_collection()

# Benchmark configuration
config = {
    \"timeout\": 180,
    \"verbose\": False,  # Reduce output for cleaner benchmark
    \"output_format\": \"json\",
    \"limit\": 5
}

print(\"Starting performance benchmark...\")
print(f\"Process ID: {os.getpid()}\")
print(f\"Initial memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB\")

# Run benchmark
start_time = time.time()
result = runner.run_builtin_tasks([\"hellaswag\"], config)
end_time = time.time()

# Stop metrics collection
metrics = metrics_collector.stop_collection()

print(\"=== Performance Benchmark Results ===\")
print(f\"Execution time: {end_time - start_time:.2f}s\")
print(f\"Success: {result[\"success\"]}\")

if metrics:
    print(\"Resource usage:\")
    if \"peak_memory_mb\" in metrics:
        print(f\"  Peak memory: {metrics[\"peak_memory_mb\"]:.1f} MB\")
    if \"avg_cpu_percent\" in metrics:
        print(f\"  Average CPU: {metrics[\"avg_cpu_percent\"]:.1f}%\")
    if \"total_api_calls\" in metrics:
        print(f\"  API calls: {metrics[\"total_api_calls\"]}\")

print(f\"Final memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB\")
'" \
    "Benchmark CLI performance with resource monitoring"

# Example 4: Parallel Task Execution
echo "4. Parallel Task Execution"
echo "=========================="
run_advanced_test "Parallel_Execution" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
import concurrent.futures
import time

runner = CLITestRunner()

def run_single_task(task_name):
    \"\"\"Run a single task and return results.\"\"\"
    config = {
        \"timeout\": 120,
        \"verbose\": False,
        \"output_format\": \"json\",
        \"limit\": 2
    }
    
    start_time = time.time()
    result = runner.run_builtin_tasks([task_name], config)
    execution_time = time.time() - start_time
    
    return {
        \"task\": task_name,
        \"success\": result[\"success\"],
        \"execution_time\": execution_time,
        \"metrics\": result.get(\"metrics\", {})
    }

# Tasks to run in parallel
tasks = [\"hellaswag\", \"arc_easy\"]
print(f\"Running {len(tasks)} tasks in parallel: {tasks}\")

# Sequential execution for comparison
print(\"\\n=== Sequential Execution ===\")
sequential_start = time.time()
sequential_results = []
for task in tasks:
    result = run_single_task(task)
    sequential_results.append(result)
    print(f\"  {task}: {result[\"success\"]} ({result[\"execution_time\"]:.2f}s)\")
sequential_total = time.time() - sequential_start

# Parallel execution
print(\"\\n=== Parallel Execution ===\")
parallel_start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    parallel_results = list(executor.map(run_single_task, tasks))
parallel_total = time.time() - parallel_start

for result in parallel_results:
    print(f\"  {result[\"task\"]}: {result[\"success\"]} ({result[\"execution_time\"]:.2f}s)\")

print(\"\\n=== Performance Comparison ===\")
print(f\"Sequential total time: {sequential_total:.2f}s\")
print(f\"Parallel total time: {parallel_total:.2f}s\")
print(f\"Time saved: {sequential_total - parallel_total:.2f}s ({((sequential_total - parallel_total) / sequential_total * 100):.1f}%)\")
'" \
    "Compare sequential vs parallel task execution"

# Example 5: Configuration Validation and Testing
echo "5. Configuration Validation and Testing"
echo "======================================="

# Create advanced config file
cat > "$RESULTS_DIR/advanced_config.yaml" << EOF
# Advanced CLI Test Configuration
test_type: "cli"
name: "Advanced CLI Test Suite"
description: "Advanced CLI testing with multiple configurations"
timeout: 300

# Multiple test scenarios
test_scenarios:
  quick_test:
    tasks: ["hellaswag"]
    limit: 1
    timeout: 60
  
  comprehensive_test:
    tasks: ["hellaswag", "arc_easy"]
    limit: 3
    timeout: 180
  
  performance_test:
    tasks: ["hellaswag"]
    limit: 10
    timeout: 300
    benchmark: true

cli_config:
  execution_timeout: 240
  output_format: "json"
  verbose: true
  parallel_execution: false
  max_workers: 2

execution_params:
  timeout: 240
  verbose: true
  log_level: "INFO"
  save_artifacts: true

output_config:
  format: "json"
  include_logs: true
  include_artifacts: true
  output_directory: "$RESULTS_DIR"

metrics_config:
  collection_interval: 1.0
  enable_system_metrics: true
  memory_tracking: true
EOF

run_advanced_test "Config_Validation" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
from core.config_manager import ConfigManager
import yaml

# Load and validate configuration
config_path = \"$RESULTS_DIR/advanced_config.yaml\"
with open(config_path, \"r\") as f:
    config = yaml.safe_load(f)

print(f\"Loaded configuration: {config[\"name\"]}\")
print(f\"Description: {config[\"description\"]}\")

# Validate configuration structure
required_sections = [\"cli_config\", \"execution_params\", \"output_config\"]
for section in required_sections:
    if section in config:
        print(f\"✓ {section} section found\")
    else:
        print(f\"✗ {section} section missing\")

# Test each scenario
runner = CLITestRunner()
scenarios = config.get(\"test_scenarios\", {})

print(f\"\\nTesting {len(scenarios)} scenarios:\")
for scenario_name, scenario_config in scenarios.items():
    print(f\"\\n--- Testing {scenario_name} ---\")
    
    # Merge with base CLI config
    test_config = config[\"cli_config\"].copy()
    test_config.update(scenario_config)
    
    print(f\"Tasks: {test_config.get(\"tasks\", [])}\")
    print(f\"Limit: {test_config.get(\"limit\", \"unlimited\")}\")
    print(f\"Timeout: {test_config.get(\"timeout\", \"default\")}\")
    
    try:
        result = runner.run_builtin_tasks(test_config[\"tasks\"], test_config)
        print(f\"Result: {\"SUCCESS\" if result[\"success\"] else \"FAILED\"}\")
        print(f\"Execution time: {result[\"execution_time\"]:.2f}s\")
    except Exception as e:
        print(f\"Error: {e}\")

print(\"\\nConfiguration validation and testing completed\")
'" \
    "Validate and test advanced configuration scenarios"

# Example 6: Error Recovery and Retry Logic
echo "6. Error Recovery and Retry Logic"
echo "================================="
run_advanced_test "Error_Recovery" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
import time

runner = CLITestRunner()

def test_with_retry(task_name, max_retries=3):
    \"\"\"Test with retry logic for error recovery.\"\"\"
    config = {
        \"timeout\": 30,  # Short timeout to potentially cause failures
        \"verbose\": True,
        \"output_format\": \"json\",
        \"limit\": 1
    }
    
    for attempt in range(max_retries + 1):
        print(f\"Attempt {attempt + 1}/{max_retries + 1} for task: {task_name}\")
        
        try:
            result = runner.run_builtin_tasks([task_name], config)
            
            if result[\"success\"]:
                print(f\"✓ Task {task_name} succeeded on attempt {attempt + 1}\")
                return result
            else:
                print(f\"✗ Task {task_name} failed on attempt {attempt + 1}: {result.get(\"error\", \"Unknown error\")}\")
                
                if attempt < max_retries:
                    # Increase timeout for retry
                    config[\"timeout\"] = min(config[\"timeout\"] * 2, 300)
                    print(f\"  Retrying with increased timeout: {config[\"timeout\"]}s\")
                    time.sleep(2)  # Brief pause before retry
                
        except Exception as e:
            print(f\"✗ Exception on attempt {attempt + 1}: {e}\")
            if attempt < max_retries:
                print(\"  Retrying after exception...\")
                time.sleep(2)
    
    print(f\"✗ Task {task_name} failed after {max_retries + 1} attempts\")
    return {\"success\": False, \"error\": \"Max retries exceeded\"}

# Test error recovery
print(\"Testing error recovery with retry logic...\")
print(\"\\n=== Testing Valid Task ===\")
valid_result = test_with_retry(\"hellaswag\", max_retries=2)

print(\"\\n=== Testing Invalid Task ===\")
invalid_result = test_with_retry(\"nonexistent_task\", max_retries=2)

print(\"\\n=== Error Recovery Summary ===\")
print(f\"Valid task result: {valid_result[\"success\"]}\")
print(f\"Invalid task result: {invalid_result[\"success\"]}\")
print(\"Error recovery testing completed\")
'" \
    "Test error recovery and retry logic for failed operations"

# Example 7: Real Execution Validation
echo "7. Real Execution Validation"
echo "============================"
run_advanced_test "Real_Execution_Validation" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
from core.real_execution_validator import RealExecutionValidator
from models.test_models import TestConfiguration, TestType

runner = CLITestRunner()
validator = RealExecutionValidator()

# Configure validation
validator.configure_validation(
    mock_detection=True,
    resource_tracking=True,
    api_call_tracking=True
)

print(\"Starting real execution validation test...\")

# Start tracking
validator.start_tracking()

# Run test
config = {
    \"timeout\": 120,
    \"verbose\": True,
    \"output_format\": \"json\",
    \"limit\": 2
}

print(\"Running test with real execution validation...\")
result = runner.run_builtin_tasks([\"hellaswag\"], config)

# Create test configuration for validation
test_config = TestConfiguration(
    test_id=\"real_execution_validation\",
    test_type=TestType.CLI,
    name=\"Real Execution Validation Test\",
    description=\"Test to validate real execution\",
    real_execution_required=True
)

# Create test result for validation
from models.test_models import TestResult, TestStatus
test_result = TestResult(
    test_id=\"real_execution_validation\",
    test_type=TestType.CLI,
    name=\"Real Execution Validation Test\",
    status=TestStatus.PASSED if result[\"success\"] else TestStatus.FAILED,
    execution_time=result[\"execution_time\"],
    real_execution_validated=False,
    logs=[\"Test executed\"],
    metrics=result.get(\"metrics\", {})
)

# Validate real execution
is_real = validator.validate_real_execution(test_result, test_config)
validator.stop_tracking()

# Get validation report
validation_report = validator.get_validation_report()

print(\"\\n=== Real Execution Validation Results ===\")
print(f\"Test success: {result[\"success\"]}\")
print(f\"Real execution validated: {is_real}\")
print(f\"Mock objects detected: {validation_report[\"mock_objects_found\"]}\")
print(f\"API calls recorded: {validation_report[\"api_calls_recorded\"]}\")
print(f\"Resource snapshots: {validation_report[\"resource_snapshots\"]}\")

if validation_report[\"memory_growth\"] is not None:
    print(f\"Memory growth: {validation_report[\"memory_growth\"]} bytes\")

if validation_report[\"errors\"]:
    print(\"Validation errors:\")
    for error in validation_report[\"errors\"]:
        print(f\"  - {error}\")

print(\"Real execution validation completed\")
'" \
    "Validate that tests perform real execution without mock data"

# Summary
echo "=== Advanced CLI Examples Summary ==="
echo "All advanced CLI examples have been executed."
echo
echo "Results saved in: $RESULTS_DIR"
echo "Files created:"
ls -la "$RESULTS_DIR" | grep -v "^total" | awk '{print "  " $9 " (" $5 " bytes)"}'
echo
echo "Advanced features demonstrated:"
echo "  ✓ Multiple task testing"
echo "  ✓ Custom task discovery"
echo "  ✓ Performance benchmarking"
echo "  ✓ Parallel execution"
echo "  ✓ Configuration validation"
echo "  ✓ Error recovery and retry logic"
echo "  ✓ Real execution validation"
echo
echo "Next steps:"
echo "1. Review the detailed log files for execution information"
echo "2. Try adapter validation examples: ./adapter_validation_examples.sh"
echo "3. Explore API examples: ../api/basic_api_examples.sh"
echo "4. Test complete workflows: ../workflows/quick_validation.py"
echo
echo "For troubleshooting, check the individual log files in $RESULTS_DIR"