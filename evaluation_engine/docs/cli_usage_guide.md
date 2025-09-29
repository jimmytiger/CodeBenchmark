# CLI Usage Guide - Config-Driven Evaluation

This guide covers the command-line interface (CLI) for the config-driven evaluation system.

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Basic Commands](#basic-commands)
3. [Configuration Management](#configuration-management)
4. [Execution Commands](#execution-commands)
5. [Validation and Testing](#validation-and-testing)
6. [Advanced Usage](#advanced-usage)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

## Installation and Setup

### Prerequisites

Ensure the evaluation engine is installed and the CLI is available:

```bash
# Install the evaluation engine
pip install -e .

# Verify CLI is available
eval-engine --help
```

### Environment Setup

Set up required environment variables:

```bash
# Required API keys
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

# Optional: Default output directory
export EVAL_OUTPUT_DIR="./evaluation_results"

# Optional: Default configuration directory
export EVAL_CONFIG_DIR="./configs"
```

## Basic Commands

### Help and Version

```bash
# Show general help
eval-engine --help

# Show version information
eval-engine --version

# Show help for config commands
eval-engine config --help

# Show help for specific command
eval-engine config run --help
```

### Command Structure

The CLI follows this structure:
```bash
eval-engine <command_group> <command> [options] [arguments]
```

Where:
- `command_group`: Currently `config` for configuration-driven evaluation
- `command`: Specific action like `run`, `validate`, `list-tasks`
- `options`: Command-line flags and parameters
- `arguments`: Required arguments like configuration file paths

## Configuration Management

### Running Evaluations

#### Basic Execution

```bash
# Run evaluation with configuration file
eval-engine config run my_config.yaml

# Run with specific output directory
eval-engine config run my_config.yaml --output-dir ./custom_results

# Run with verbose logging
eval-engine config run my_config.yaml --verbose

# Run in quiet mode (minimal output)
eval-engine config run my_config.yaml --quiet
```

#### Parameter Overrides

```bash
# Override specific configuration values
eval-engine config run my_config.yaml \
  --override defaults.batch_size=4 \
  --override output.directory=./new_results

# Override multiple values
eval-engine config run my_config.yaml \
  --override defaults.num_fewshot=10 \
  --override defaults.batch_size=2 \
  --override output.formats=json,csv

# Override nested values
eval-engine config run my_config.yaml \
  --override models.gpt35.parameters.temperature=0.5 \
  --override output.generate_report=false
```

#### Task Filtering

```bash
# Run only specific tasks
eval-engine config run my_config.yaml --tasks task1,task2,task3

# Run all tasks except specific ones
eval-engine config run my_config.yaml --exclude-tasks slow_task,expensive_task

# Run tasks matching a pattern
eval-engine config run my_config.yaml --task-pattern "*_gpt4"
```

#### Execution Control

```bash
# Dry run (validate and plan without executing)
eval-engine config run my_config.yaml --dry-run

# Fail fast (stop on first error)
eval-engine config run my_config.yaml --fail-fast

# Continue on errors (default behavior)
eval-engine config run my_config.yaml --continue-on-error

# Set maximum parallel tasks
eval-engine config run my_config.yaml --max-parallel 4
```

### Configuration Validation

```bash
# Validate configuration file
eval-engine config validate my_config.yaml

# Validate with detailed output
eval-engine config validate my_config.yaml --verbose

# Validate multiple files
eval-engine config validate config1.yaml config2.yaml config3.yaml

# Validate and show execution plan
eval-engine config validate my_config.yaml --show-plan
```

### Information Commands

```bash
# List available lm-eval tasks
eval-engine config list-tasks

# List tasks with descriptions
eval-engine config list-tasks --detailed

# Search for specific tasks
eval-engine config list-tasks --search "math"
eval-engine config list-tasks --search "reasoning"

# List supported model types
eval-engine config list-models

# Show model configuration examples
eval-engine config list-models --examples

# Show configuration template
eval-engine config template

# Show template for specific use case
eval-engine config template --type basic
eval-engine config template --type multi-model
eval-engine config template --type complex-dependencies
```

## Execution Commands

### Standard Execution

```bash
# Basic execution
eval-engine config run evaluation.yaml

# With custom output directory
eval-engine config run evaluation.yaml --output-dir ./results_$(date +%Y%m%d)

# With logging configuration
eval-engine config run evaluation.yaml \
  --log-level DEBUG \
  --log-file ./logs/evaluation.log
```

### Advanced Execution Options

```bash
# Resource management
eval-engine config run evaluation.yaml \
  --max-memory 8GB \
  --max-parallel 2 \
  --timeout 3600

# Retry configuration
eval-engine config run evaluation.yaml \
  --retry-attempts 3 \
  --retry-delay 5 \
  --retry-exponential-backoff

# Output control
eval-engine config run evaluation.yaml \
  --no-reports \
  --no-raw-responses \
  --compress-output
```

### Monitoring and Progress

```bash
# Show progress bar
eval-engine config run evaluation.yaml --progress

# Show detailed execution information
eval-engine config run evaluation.yaml --verbose --progress

# Save execution metadata
eval-engine config run evaluation.yaml --save-metadata

# Enable profiling
eval-engine config run evaluation.yaml --profile
```

## Validation and Testing

### Configuration Validation

```bash
# Basic validation
eval-engine config validate config.yaml

# Comprehensive validation
eval-engine config validate config.yaml \
  --check-models \
  --check-tasks \
  --check-dependencies

# Validation with warnings
eval-engine config validate config.yaml --show-warnings

# Validate syntax only
eval-engine config validate config.yaml --syntax-only
```

### Dry Run Testing

```bash
# Dry run with execution plan
eval-engine config run config.yaml --dry-run --show-plan

# Dry run with resource estimation
eval-engine config run config.yaml --dry-run --estimate-resources

# Dry run with timing estimation
eval-engine config run config.yaml --dry-run --estimate-time
```

### Quick Testing

```bash
# Run with reduced limits for testing
eval-engine config run config.yaml \
  --override "tasks.*.task_config.limit=10" \
  --test-mode

# Run single task for testing
eval-engine config run config.yaml \
  --tasks single_task \
  --override "tasks.single_task.task_config.limit=5"
```

## Advanced Usage

### Environment Variable Integration

```bash
# Use environment variables in overrides
export BATCH_SIZE=8
export OUTPUT_DIR="./results_$(date +%Y%m%d)"

eval-engine config run config.yaml \
  --override "defaults.batch_size=${BATCH_SIZE}" \
  --override "output.directory=${OUTPUT_DIR}"
```

### Configuration Composition

```bash
# Merge multiple configuration files
eval-engine config run base_config.yaml \
  --include additional_models.yaml \
  --include extra_tasks.yaml

# Override with external configuration
eval-engine config run config.yaml \
  --override-file overrides.yaml
```

### Batch Processing

```bash
# Run multiple configurations
for config in configs/*.yaml; do
  eval-engine config run "$config" \
    --output-dir "./results/$(basename "$config" .yaml)"
done

# Parallel execution of multiple configs
parallel eval-engine config run {} --output-dir ./results/{/.} ::: configs/*.yaml
```

### Integration with CI/CD

```bash
# CI-friendly execution
eval-engine config run config.yaml \
  --quiet \
  --no-progress \
  --output-format json \
  --exit-code-on-failure

# Generate reports for CI
eval-engine config run config.yaml \
  --generate-junit-xml \
  --generate-coverage-report \
  --output-dir ./ci_results
```

## Examples

### Basic Usage Examples

```bash
# Simple evaluation
eval-engine config run basic_eval.yaml

# Quick test with small limits
eval-engine config run comprehensive_eval.yaml \
  --override "tasks.*.task_config.limit=20" \
  --tasks "hellaswag_*"

# Compare models on same task
eval-engine config run model_comparison.yaml \
  --override "output.compare_models=true"
```

### Development Workflow Examples

```bash
# Validate before running
eval-engine config validate my_config.yaml && \
eval-engine config run my_config.yaml

# Test configuration with dry run
eval-engine config run my_config.yaml --dry-run --verbose

# Run with development settings
eval-engine config run my_config.yaml \
  --override "tasks.*.task_config.limit=10" \
  --override "defaults.batch_size=2" \
  --verbose
```

### Production Workflow Examples

```bash
# Production run with full logging
eval-engine config run production_config.yaml \
  --log-level INFO \
  --log-file ./logs/production_$(date +%Y%m%d_%H%M%S).log \
  --save-metadata \
  --compress-output

# Automated evaluation with error handling
eval-engine config run config.yaml \
  --continue-on-error \
  --retry-attempts 3 \
  --timeout 7200 \
  --output-dir ./results/$(date +%Y%m%d) || \
  echo "Evaluation failed, check logs"

# Resource-constrained execution
eval-engine config run large_config.yaml \
  --max-parallel 2 \
  --max-memory 4GB \
  --batch-size-limit 4
```

### Debugging Examples

```bash
# Debug configuration issues
eval-engine config validate config.yaml --verbose --show-warnings

# Debug execution with detailed logging
eval-engine config run config.yaml \
  --log-level DEBUG \
  --verbose \
  --no-parallel \
  --tasks problematic_task

# Profile performance
eval-engine config run config.yaml \
  --profile \
  --save-timing-info \
  --verbose
```

## Command Reference

### `eval-engine config run`

Execute evaluation from configuration file.

**Syntax:**
```bash
eval-engine config run <config_file> [options]
```

**Options:**
- `--output-dir DIR`: Output directory (default: from config or ./results)
- `--override KEY=VALUE`: Override configuration values
- `--override-file FILE`: Load overrides from file
- `--tasks TASKS`: Comma-separated list of tasks to run
- `--exclude-tasks TASKS`: Comma-separated list of tasks to exclude
- `--task-pattern PATTERN`: Run tasks matching pattern
- `--dry-run`: Validate and plan without executing
- `--verbose`: Verbose output
- `--quiet`: Minimal output
- `--progress`: Show progress bar
- `--fail-fast`: Stop on first error
- `--continue-on-error`: Continue despite errors
- `--max-parallel N`: Maximum parallel tasks
- `--timeout SECONDS`: Maximum execution time
- `--log-level LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `--log-file FILE`: Log to file
- `--save-metadata`: Save execution metadata
- `--profile`: Enable performance profiling

### `eval-engine config validate`

Validate configuration file.

**Syntax:**
```bash
eval-engine config validate <config_file> [options]
```

**Options:**
- `--verbose`: Detailed validation output
- `--show-warnings`: Show validation warnings
- `--show-plan`: Show execution plan
- `--check-models`: Validate model availability
- `--check-tasks`: Validate task names
- `--check-dependencies`: Validate task dependencies
- `--syntax-only`: Check syntax only

### `eval-engine config list-tasks`

List available evaluation tasks.

**Syntax:**
```bash
eval-engine config list-tasks [options]
```

**Options:**
- `--detailed`: Show task descriptions
- `--search TERM`: Search for tasks containing term
- `--category CATEGORY`: Filter by category
- `--format FORMAT`: Output format (table, json, yaml)

### `eval-engine config list-models`

List supported model types.

**Syntax:**
```bash
eval-engine config list-models [options]
```

**Options:**
- `--examples`: Show configuration examples
- `--detailed`: Show detailed information
- `--format FORMAT`: Output format (table, json, yaml)

### `eval-engine config template`

Generate configuration templates.

**Syntax:**
```bash
eval-engine config template [options]
```

**Options:**
- `--type TYPE`: Template type (basic, multi-model, complex-dependencies)
- `--output FILE`: Save template to file
- `--format FORMAT`: Template format (yaml, json)

## Troubleshooting

### Common Issues

#### Configuration File Not Found
```bash
# Error: Configuration file 'config.yaml' not found
# Solution: Check file path and current directory
ls -la config.yaml
eval-engine config run ./path/to/config.yaml
```

#### Invalid Configuration Format
```bash
# Error: YAML parsing error
# Solution: Validate YAML syntax
eval-engine config validate config.yaml --syntax-only
```

#### Missing API Keys
```bash
# Error: OpenAI API key not found
# Solution: Set environment variable
export OPENAI_API_KEY="your-key-here"
eval-engine config run config.yaml
```

#### Task Not Found
```bash
# Error: Task 'invalid_task' not found
# Solution: List available tasks
eval-engine config list-tasks --search "task_name"
```

#### Permission Denied
```bash
# Error: Permission denied writing to output directory
# Solution: Check permissions or use different directory
eval-engine config run config.yaml --output-dir ./writable_directory
```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Full debug information
eval-engine config run config.yaml \
  --log-level DEBUG \
  --verbose \
  --save-metadata \
  --no-parallel

# Debug specific task
eval-engine config run config.yaml \
  --tasks problematic_task \
  --log-level DEBUG \
  --verbose
```

### Getting Help

```bash
# General help
eval-engine --help

# Command-specific help
eval-engine config run --help
eval-engine config validate --help

# Show examples
eval-engine config template --type basic
eval-engine config list-tasks --detailed
```

### Exit Codes

The CLI uses standard exit codes:

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Validation error
- `4`: Execution error
- `5`: Resource error (memory, timeout, etc.)

Use exit codes in scripts:

```bash
if eval-engine config run config.yaml --quiet; then
    echo "Evaluation successful"
else
    echo "Evaluation failed with exit code $?"
    exit 1
fi
```

## Best Practices

### Configuration Management
- Use version control for configuration files
- Validate configurations before committing
- Use environment variables for sensitive data
- Document configuration changes

### Development Workflow
- Start with dry runs and small limits
- Use verbose mode during development
- Validate configurations frequently
- Test with different parameter combinations

### Production Usage
- Use appropriate logging levels
- Set reasonable timeouts and retry policies
- Monitor resource usage
- Archive results with timestamps

### Performance Optimization
- Adjust batch sizes based on model capabilities
- Use parallel execution appropriately
- Monitor memory usage with large evaluations
- Use task limits for development and testing