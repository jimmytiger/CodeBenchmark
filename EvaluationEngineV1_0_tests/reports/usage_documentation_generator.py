"""
UsageDocumentationGenerator for creating comprehensive usage documentation.

This module generates usage.md documentation with step-by-step instructions,
examples, and troubleshooting guides based on test execution results.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from models.test_models import TestResult, ValidationResult


class UsageDocumentationGenerator:
    """
    Generates comprehensive usage documentation for the testing framework.
    
    Creates usage.md files with examples, troubleshooting guides, and
    step-by-step instructions based on successful test executions.
    """
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize the usage documentation generator.
        
        Args:
            output_dir: Directory to save generated documentation
        """
        self.output_dir = output_dir or Path("docs")
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def generate_usage_guide(self, test_results: List[TestResult]) -> str:
        """
        Generate comprehensive usage guide based on test results.
        
        Args:
            test_results: List of test results to extract examples from
            
        Returns:
            Complete usage guide as markdown string
        """
        successful_tests = [r for r in test_results if (r.status.value if hasattr(r.status, 'value') else str(r.status)) == 'passed']
        
        content = f"""# EvaluationEngineV1_0 Testing Framework Usage Guide

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Overview

This guide provides comprehensive instructions for using the EvaluationEngineV1_0 testing framework. The framework supports both CLI and API testing interfaces, validates core adapters, and ensures real execution validation.

## Quick Start

### Prerequisites

1. Python 3.8 or higher
2. EvaluationEngineV1_0 installed and configured
3. Required dependencies (automatically installed by the framework)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd EvaluationEngineV1_0_tests

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m pytest tests/unit/test_config_manager.py -v
```

## CLI Testing Interface

The CLI interface provides command-line testing capabilities for automated and manual testing scenarios.

### Basic CLI Commands

{self._generate_cli_examples(successful_tests)}

### CLI Configuration

Create a configuration file `config.yaml`:

```yaml
# Example CLI configuration
test_config:
  execution_timeout: 300
  output_format: "detailed"
  verbose: true
  
tasks:
  - "hellaswag"
  - "arc_easy"
  
adapters:
  - "lm_eval_adapter"
  - "swe_bench_adapter"
```

### Running CLI Tests

```bash
# Run builtin tasks
python -m EvaluationEngineV1_0_tests.cli.cli_main builtin --tasks hellaswag,arc_easy --config config.yaml

# Run custom tasks
python -m EvaluationEngineV1_0_tests.cli.cli_main custom --task-dir ./custom_tasks --config config.yaml

# Run adapter tests
python -m EvaluationEngineV1_0_tests.cli.cli_main adapters --adapter lm_eval_adapter --config config.yaml

# Run full pipeline
python -m EvaluationEngineV1_0_tests.cli.cli_main pipeline --config config.yaml
```

## API Testing Interface

The API interface provides REST API testing capabilities with curl support and programmatic access.

### Starting the API Server

```bash
# Start the test API server
python -m EvaluationEngineV1_0_tests.api.api_test_server --host localhost --port 8080

# Server will be available at http://localhost:8080
```

### API Endpoints

{self._generate_api_examples(successful_tests)}

### Using curl Commands

```bash
# Start an evaluation
curl -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{
    "tasks": ["hellaswag"],
    "model": "gpt-3.5-turbo",
    "config": {{
      "num_fewshot": 5,
      "batch_size": 1
    }}
  }}'

# Check evaluation status
curl -X GET http://localhost:8080/api/v1/evaluations/${{evaluation_id}}/status

# Get evaluation results
curl -X GET http://localhost:8080/api/v1/evaluations/${{evaluation_id}}/results
```

### Programmatic API Usage

```python
from EvaluationEngineV1_0_tests.api.api_test_client import APITestClient

# Initialize client
client = APITestClient(base_url="http://localhost:8080")

# Start evaluation
evaluation_id = client.start_evaluation({{
    "tasks": ["hellaswag"],
    "model": "gpt-3.5-turbo",
    "config": {{"num_fewshot": 5}}
}})

# Wait for completion and get results
results = client.wait_for_completion(evaluation_id)
print("Results:", results)
```

## Adapter Validation

The framework validates core adapters to ensure proper integration with external evaluation frameworks.

### LM Eval Adapter Validation

```python
from EvaluationEngineV1_0_tests.adapters.lm_eval_adapter_validator import LMEvalAdapterValidator

# Initialize validator
validator = LMEvalAdapterValidator()

# Validate integration
result = validator.validate_integration()
print("Integration status:", result.integration_status)

# Test builtin tasks
test_results = validator.test_builtin_tasks(task_count=2)
print("Tested", len(test_results), "tasks")

# Test custom tasks
custom_results = validator.test_custom_tasks(Path("./custom_tasks"))
```

### SWE-bench Adapter Validation

```python
from EvaluationEngineV1_0_tests.adapters.swe_bench_adapter_validator import SWEBenchAdapterValidator

# Initialize validator
validator = SWEBenchAdapterValidator()

# Setup environment
validator.setup_environment()

# Validate integration
result = validator.validate_integration()

# Test software engineering tasks
test_results = validator.test_software_tasks(task_count=1)
```

## Real Execution Validation

The framework ensures all tests perform real execution without mock data.

### Validation Features

- **Mock Detection**: Automatically detects and prevents mock data usage
- **API Call Validation**: Verifies real model API calls are made
- **Resource Monitoring**: Tracks actual resource consumption
- **Result Verification**: Confirms results are from genuine evaluation

### Example Validation

```python
from EvaluationEngineV1_0_tests.core.real_execution_validator import RealExecutionValidator

# Initialize validator
validator = RealExecutionValidator()

# Validate execution
is_real = validator.validate_no_mocks(execution_context)
api_calls_real = validator.validate_actual_model_calls(api_logs)
results_genuine = validator.validate_genuine_results(results)

print("Real execution validated:", is_real and api_calls_real and results_genuine)
```

## Custom Task Support

The framework supports custom tasks located in the lm_eval/tasks directory.

### Custom Task Structure

```python
# custom_tasks/my_task.py
from lm_eval.api.task import Task

class MyCustomTask(Task):
    VERSION = 1.0
    DATASET_PATH = "path/to/dataset"
    
    def has_training_docs(self):
        return False
        
    def has_validation_docs(self):
        return True
        
    def validation_docs(self):
        # Return validation documents
        pass
        
    def doc_to_text(self, doc):
        # Convert document to text
        pass
        
    def doc_to_target(self, doc):
        # Extract target from document
        pass
```

### Using Custom Tasks

```bash
# Place custom tasks in lm_eval/tasks directory
mkdir -p lm_eval/tasks/custom
cp my_task.py lm_eval/tasks/custom/

# Run custom task tests
python -m EvaluationEngineV1_0_tests.cli.cli_main custom --task-dir lm_eval/tasks/custom
```

## Performance Analysis

The framework provides comprehensive performance analysis and reporting.

### Performance Metrics

- Execution times per task
- Memory usage patterns
- API response times
- Success/error rates
- Resource consumption

### Generating Performance Reports

```python
from EvaluationEngineV1_0_tests.reports.performance_analyzer import PerformanceAnalyzer

# Initialize analyzer
analyzer = PerformanceAnalyzer()

# Analyze execution metrics
analysis = analyzer.analyze_execution_metrics(metrics)

# Generate performance report
report = analyzer.generate_performance_report(analysis)

# Save report
analyzer.save_analysis_report(report, "performance_analysis.json")
```

## Troubleshooting

{self.generate_troubleshooting_guide([t for t in test_results if (t.status.value if hasattr(t.status, 'value') else str(t.status)) == 'failed'])}

## Best Practices

### Configuration Management

1. **Use Configuration Files**: Store test configurations in YAML files for reusability
2. **Environment Variables**: Use environment variables for sensitive data like API keys
3. **Validation**: Always validate configurations before running tests

### Test Execution

1. **Start Small**: Begin with single task tests before running full pipelines
2. **Monitor Resources**: Keep an eye on memory and CPU usage during long-running tests
3. **Log Analysis**: Review logs for detailed execution information

### Error Handling

1. **Check Dependencies**: Ensure all required dependencies are installed
2. **Validate Configurations**: Verify configuration files are properly formatted
3. **Review Logs**: Check detailed logs for specific error information

## Advanced Usage

### Batch Testing

```python
# Run multiple test configurations
configs = [
    {{"tasks": ["hellaswag"], "model": "gpt-3.5-turbo"}},
    {{"tasks": ["arc_easy"], "model": "gpt-4"}},
]

for config in configs:
    result = run_evaluation(config)
    print("Config", config, "completed with status", result.status)
```

### Custom Metrics

```python
# Define custom metrics
def custom_accuracy_metric(predictions, references):
    correct = sum(p == r for p, r in zip(predictions, references))
    return correct / len(predictions)

# Register custom metric
register_metric("custom_accuracy", custom_accuracy_metric)
```

### Integration with CI/CD

```yaml
# .github/workflows/evaluation.yml
name: Evaluation Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run evaluation tests
      run: python -m EvaluationEngineV1_0_tests.cli.cli_main pipeline --config ci_config.yaml
```

## Support and Contributing

### Getting Help

1. Check the troubleshooting guide above
2. Review the API documentation
3. Check existing issues in the repository
4. Create a new issue with detailed information

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Appendix

### Configuration Reference

{self._generate_configuration_reference()}

### API Reference

See the API documentation generated by APIDocumentationGenerator for complete endpoint specifications.

### Performance Benchmarks

{self._generate_performance_benchmarks(successful_tests)}

---

*This documentation was automatically generated by the EvaluationEngineV1_0 testing framework.*
"""
        
        self.logger.info(f"Generated usage guide with {len(successful_tests)} successful test examples")
        return content
        
    def generate_examples(self, successful_tests: List[TestResult]) -> str:
        """
        Generate working code examples from successful tests.
        
        Args:
            successful_tests: List of successful test results
            
        Returns:
            Examples section as markdown string
        """
        examples = []
        
        # Group tests by type
        test_types = {}
        for test in successful_tests:
            test_type = test.test_type.value if hasattr(test.test_type, 'value') else str(test.test_type)
            if test_type not in test_types:
                test_types[test_type] = []
            test_types[test_type].append(test)
        
        for test_type, tests in test_types.items():
            example = self._generate_example_for_type(test_type, tests[:3])  # Limit to 3 examples per type
            if example:
                examples.append(example)
        
        return "\n\n".join(examples)
        
    def generate_troubleshooting_guide(self, failed_tests: List[TestResult]) -> str:
        """
        Generate troubleshooting guide from failed tests.
        
        Args:
            failed_tests: List of failed test results
            
        Returns:
            Troubleshooting guide as markdown string
        """
        if not failed_tests:
            return "## Troubleshooting\n\nNo common issues found. All tests passed successfully!"
        
        # Analyze error patterns
        error_patterns = {}
        for test in failed_tests:
            if test.error_details:
                error_type = test.error_details.split(':')[0] if ':' in test.error_details else 'Unknown Error'
                if error_type not in error_patterns:
                    error_patterns[error_type] = []
                error_patterns[error_type].append(test)
        
        guide_sections = []
        
        for error_type, error_tests in error_patterns.items():
            section = self._generate_troubleshooting_section(error_type, error_tests)
            guide_sections.append(section)
        
        return "\n\n".join(guide_sections)
        
    def save_usage_guide(self, content: str, filename: str = "usage.md") -> Path:
        """
        Save usage guide to file.
        
        Args:
            content: Usage guide content
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(content)
        
        self.logger.info(f"Saved usage guide to {filepath}")
        return filepath
        
    def _generate_cli_examples(self, successful_tests: List[TestResult]) -> str:
        """Generate CLI examples from successful tests."""
        cli_tests = [t for t in successful_tests if (t.test_type.value if hasattr(t.test_type, 'value') else str(t.test_type)) == 'cli']
        
        if not cli_tests:
            return "```bash\n# No CLI examples available\n```"
        
        examples = []
        for test in cli_tests[:5]:  # Limit to 5 examples
            if test.artifacts:
                # Extract command from artifacts if available
                command = f"# Example from test {test.test_id}\npython -m EvaluationEngineV1_0_tests.cli.cli_main --config example_config.yaml"
                examples.append(command)
        
        return f"```bash\n{chr(10).join(examples)}\n```"
        
    def _generate_api_examples(self, successful_tests: List[TestResult]) -> str:
        """Generate API examples from successful tests."""
        api_tests = [t for t in successful_tests if (t.test_type.value if hasattr(t.test_type, 'value') else str(t.test_type)) == 'api']
        
        if not api_tests:
            return "No API examples available"
        
        return """
#### Available Endpoints

- `POST /api/v1/evaluations` - Start a new evaluation
- `GET /api/v1/evaluations/{id}/status` - Check evaluation status  
- `GET /api/v1/evaluations/{id}/results` - Get evaluation results
- `GET /api/v1/tasks` - List available tasks
- `GET /api/v1/adapters` - List available adapters
- `GET /api/v1/health` - Health check endpoint
"""
        
    def _generate_troubleshooting_section(self, error_type: str, error_tests: List[TestResult]) -> str:
        """Generate troubleshooting section for specific error type."""
        solutions = {
            'ConfigurationError': [
                "Check that configuration file exists and is valid YAML/JSON",
                "Verify all required configuration parameters are provided",
                "Ensure file paths in configuration are correct and accessible"
            ],
            'DependencyError': [
                "Run `pip install -r requirements.txt` to install dependencies",
                "Check that Python version is 3.8 or higher",
                "Verify that external tools (if required) are installed and in PATH"
            ],
            'ExecutionError': [
                "Check system resources (memory, disk space)",
                "Verify network connectivity for API calls",
                "Review logs for specific error details"
            ],
            'ValidationError': [
                "Ensure test data is properly formatted",
                "Check that model endpoints are accessible",
                "Verify API keys and authentication are correct"
            ]
        }
        
        default_solutions = [
            "Check the logs for detailed error information",
            "Verify system requirements are met",
            "Try running with verbose logging enabled"
        ]
        
        error_solutions = solutions.get(error_type, default_solutions)
        
        section = f"""### {error_type}

**Symptoms:** {len(error_tests)} test(s) failed with this error type

**Common Solutions:**
"""
        
        for i, solution in enumerate(error_solutions, 1):
            section += f"{i}. {solution}\n"
        
        # Add specific examples if available
        if error_tests:
            example_error = error_tests[0].error_details
            section += f"\n**Example Error:**\n```\n{example_error}\n```\n"
        
        return section
        
    def _generate_example_for_type(self, test_type: str, tests: List[TestResult]) -> str:
        """Generate example for specific test type."""
        if test_type == 'cli':
            return f"""### CLI Testing Example

```python
from EvaluationEngineV1_0_tests.cli.cli_test_runner import CLITestRunner

# Initialize CLI test runner
runner = CLITestRunner()

# Run builtin tasks
results = runner.run_builtin_tasks(['hellaswag'], {{'verbose': True}})
print("Completed", len(results), "tests")
```"""
        
        elif test_type == 'api':
            return f"""### API Testing Example

```python
from EvaluationEngineV1_0_tests.api.api_test_client import APITestClient

# Initialize API client
client = APITestClient('http://localhost:8080')

# Start evaluation
eval_id = client.start_evaluation({{'tasks': ['hellaswag']}})

# Get results
results = client.get_results(eval_id)
```"""
        
        elif test_type == 'adapter':
            return f"""### Adapter Testing Example

```python
from EvaluationEngineV1_0_tests.adapters.lm_eval_adapter_validator import LMEvalAdapterValidator

# Validate adapter
validator = LMEvalAdapterValidator()
result = validator.validate_integration()
print("Adapter status:", result.integration_status)
```"""
        
        return ""
        
    def _generate_configuration_reference(self) -> str:
        """Generate configuration reference documentation."""
        return """
#### CLI Configuration

```yaml
test_config:
  execution_timeout: 300      # Maximum execution time in seconds
  output_format: "detailed"   # Output format: "brief", "detailed", "json"
  verbose: true              # Enable verbose logging
  
tasks:                       # List of tasks to run
  - "hellaswag"
  - "arc_easy"
  
adapters:                    # List of adapters to test
  - "lm_eval_adapter"
  - "swe_bench_adapter"
```

#### API Configuration

```yaml
api_config:
  host: "localhost"          # API server host
  port: 8080                # API server port
  timeout: 300              # Request timeout in seconds
  max_concurrent: 5         # Maximum concurrent requests
```
"""
        
    def _generate_performance_benchmarks(self, successful_tests: List[TestResult]) -> str:
        """Generate performance benchmarks from successful tests."""
        if not successful_tests:
            return "No performance benchmarks available."
        
        # Calculate average execution times by test type
        test_types = {}
        for test in successful_tests:
            if test.execution_time:
                test_type = test.test_type
                if test_type not in test_types:
                    test_types[test_type] = []
                test_types[test_type].append(test.execution_time)
        
        benchmark_text = "#### Performance Benchmarks\n\n"
        
        for test_type, times in test_types.items():
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            benchmark_text += f"""**{test_type.title() if isinstance(test_type, str) else str(test_type).title()} Tests:**
- Average execution time: {avg_time:.2f}s
- Fastest execution: {min_time:.2f}s  
- Slowest execution: {max_time:.2f}s
- Total tests: {len(times)}

"""
        
        return benchmark_text