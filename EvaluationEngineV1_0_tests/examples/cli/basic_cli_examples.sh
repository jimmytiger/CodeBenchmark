#!/bin/bash
# Basic CLI Examples for EvaluationEngineV1_0 Testing Framework
# This script demonstrates basic command-line usage patterns

set -e  # Exit on any error

echo "=== EvaluationEngineV1_0 Basic CLI Examples ==="
echo "This script demonstrates basic CLI testing capabilities"
echo

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$(dirname "$SCRIPT_DIR")"
TEST_FRAMEWORK_DIR="$(dirname "$EXAMPLES_DIR")"
RESULTS_DIR="$EXAMPLES_DIR/results/cli_basic"

# Create results directory
mkdir -p "$RESULTS_DIR"

echo "Results will be saved to: $RESULTS_DIR"
echo

# Function to run CLI test and capture results
run_cli_test() {
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
    else
        echo "✗ $test_name failed"
        echo "  Error log saved to: $RESULTS_DIR/${test_name,,}.log"
        echo "  Last few lines of error:"
        tail -5 "$RESULTS_DIR/${test_name,,}.log" | sed 's/^/    /'
    fi
    echo
}

# Example 1: Basic Health Check
echo "1. Basic Framework Health Check"
echo "==============================="
run_cli_test "Health_Check" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c 'from cli.cli_test_runner import CLITestRunner; print(\"CLI Test Runner imported successfully\")'" \
    "Verify that the CLI test runner can be imported and initialized"

# Example 2: List Available Tasks
echo "2. List Available Tasks"
echo "======================="
run_cli_test "List_Tasks" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
runner = CLITestRunner()
tasks = runner.list_available_tasks()
print(f\"Found {len(tasks)} available tasks:\")
for task in tasks[:10]:  # Show first 10
    print(f\"  - {task}\")
if len(tasks) > 10:
    print(f\"  ... and {len(tasks) - 10} more\")
'" \
    "List all available tasks that can be tested"

# Example 3: Simple Builtin Task Test
echo "3. Simple Builtin Task Test"
echo "==========================="
run_cli_test "Builtin_Task_Test" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
import json

runner = CLITestRunner()
config = {
    \"timeout\": 120,
    \"verbose\": True,
    \"output_format\": \"json\",
    \"limit\": 3  # Small sample for demo
}

print(\"Testing hellaswag task with 3 samples...\")
result = runner.run_builtin_tasks([\"hellaswag\"], config)
print(f\"Test result: {json.dumps(result, indent=2)}\")
'" \
    "Run a simple builtin task test with hellaswag"

# Example 4: Configuration File Usage
echo "4. Configuration File Usage"
echo "==========================="

# Create a sample config file
cat > "$RESULTS_DIR/sample_config.yaml" << EOF
# Sample CLI Test Configuration
test_type: "cli"
name: "Basic CLI Test"
description: "Basic CLI testing example"
timeout: 180

cli_config:
  tasks:
    - "hellaswag"
  execution_timeout: 120
  output_format: "json"
  verbose: true
  limit: 2  # Small sample for demo

execution_params:
  timeout: 120
  verbose: true
  log_level: "INFO"

output_config:
  format: "json"
  include_logs: true
  output_directory: "$RESULTS_DIR"
EOF

run_cli_test "Config_File_Test" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
from core.config_manager import ConfigManager
import yaml

# Load config
with open(\"$RESULTS_DIR/sample_config.yaml\", \"r\") as f:
    config = yaml.safe_load(f)

print(f\"Loaded configuration: {config[\"name\"]}\")
print(f\"Description: {config[\"description\"]}\")

runner = CLITestRunner()
cli_config = config[\"cli_config\"]
result = runner.run_builtin_tasks(cli_config[\"tasks\"], cli_config)
print(f\"Configuration-based test completed: {result[\"success\"]}\")
'" \
    "Use a configuration file to run CLI tests"

# Example 5: Verbose Output Test
echo "5. Verbose Output Test"
echo "====================="
run_cli_test "Verbose_Output_Test" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner

runner = CLITestRunner()
config = {
    \"timeout\": 60,
    \"verbose\": True,
    \"output_format\": \"json\",
    \"limit\": 1,
    \"debug\": True
}

print(\"Running verbose test with detailed output...\")
result = runner.run_builtin_tasks([\"hellaswag\"], config)

print(\"=== Test Summary ===\")
print(f\"Success: {result[\"success\"]}\")
print(f\"Execution Time: {result[\"execution_time\"]:.2f}s\")
print(f\"Command: {result.get(\"command\", \"N/A\")}\")

if result.get(\"metrics\"):
    print(\"Metrics:\")
    for key, value in result[\"metrics\"].items():
        print(f\"  {key}: {value}\")

if result.get(\"logs\"):
    print(\"Logs (last 5 lines):\")
    for log in result[\"logs\"][-5:]:
        print(f\"  {log}\")
'" \
    "Run a test with verbose output to see detailed execution information"

# Example 6: Error Handling Test
echo "6. Error Handling Test"
echo "====================="
run_cli_test "Error_Handling_Test" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner

runner = CLITestRunner()
config = {
    \"timeout\": 30,  # Short timeout to potentially cause timeout
    \"verbose\": True,
    \"output_format\": \"json\"
}

print(\"Testing error handling with invalid task...\")
try:
    result = runner.run_builtin_tasks([\"nonexistent_task\"], config)
    print(f\"Unexpected success: {result}\")
except Exception as e:
    print(f\"Expected error caught: {type(e).__name__}: {e}\")
    print(\"Error handling working correctly\")

print(\"Testing with very short timeout...\")
config[\"timeout\"] = 1  # 1 second timeout
try:
    result = runner.run_builtin_tasks([\"hellaswag\"], config)
    if not result[\"success\"]:
        print(f\"Timeout handled correctly: {result.get(\"error\", \"Unknown error\")}\")
    else:
        print(\"Test completed within timeout (unexpected but okay)\")
except Exception as e:
    print(f\"Timeout error caught: {type(e).__name__}: {e}\")
'" \
    "Test error handling with invalid tasks and timeouts"

# Example 7: Output Format Test
echo "7. Output Format Test"
echo "===================="
run_cli_test "Output_Format_Test" \
    "cd '$TEST_FRAMEWORK_DIR' && python -c '
from cli.cli_test_runner import CLITestRunner
from cli.cli_result_formatter import CLIResultFormatter
import json

runner = CLITestRunner()
formatter = CLIResultFormatter()

# Test with JSON format
config_json = {
    \"timeout\": 60,
    \"verbose\": False,
    \"output_format\": \"json\",
    \"limit\": 1
}

print(\"Testing JSON output format...\")
result = runner.run_builtin_tasks([\"hellaswag\"], config_json)

# Save in different formats
import os
results_dir = \"$RESULTS_DIR\"

# JSON format
json_path = os.path.join(results_dir, \"format_test.json\")
formatter.save_results(result, json_path, \"json\")
print(f\"JSON results saved to: {json_path}\")

# YAML format
yaml_path = os.path.join(results_dir, \"format_test.yaml\")
formatter.save_results(result, yaml_path, \"yaml\")
print(f\"YAML results saved to: {yaml_path}\")

# CSV format (if applicable)
try:
    csv_path = os.path.join(results_dir, \"format_test.csv\")
    formatter.save_results(result, csv_path, \"csv\")
    print(f\"CSV results saved to: {csv_path}\")
except Exception as e:
    print(f\"CSV format not available: {e}\")

print(\"Output format test completed\")
'" \
    "Test different output formats (JSON, YAML, CSV)"

# Summary
echo "=== CLI Examples Summary ==="
echo "All basic CLI examples have been executed."
echo
echo "Results saved in: $RESULTS_DIR"
echo "Files created:"
ls -la "$RESULTS_DIR" | grep -v "^total" | awk '{print "  " $9 " (" $5 " bytes)"}'
echo
echo "Next steps:"
echo "1. Review the log files for detailed execution information"
echo "2. Try the advanced CLI examples: ./advanced_cli_examples.sh"
echo "3. Test adapter validation: ./adapter_validation_examples.sh"
echo "4. Explore API examples: ../api/basic_api_examples.sh"
echo
echo "For troubleshooting, check the individual log files in $RESULTS_DIR"