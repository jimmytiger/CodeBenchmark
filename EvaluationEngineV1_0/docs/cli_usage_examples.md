# CLI Usage Examples

This document provides comprehensive examples of using the Multi-Turn Evaluation Engine command-line interface.

## Table of Contents

1. [Basic Commands](#basic-commands)
2. [Configuration Management](#configuration-management)
3. [Running Evaluations](#running-evaluations)
4. [Monitoring and Results](#monitoring-and-results)
5. [Task Management](#task-management)
6. [Advanced Usage](#advanced-usage)
7. [Batch Operations](#batch-operations)
8. [Integration Examples](#integration-examples)

## Basic Commands

### Getting Help

```bash
# Show general help
multi-turn --help

# Show help for specific command
multi-turn run --help
multi-turn list-tasks --help
multi-turn monitor --help

# Show version information
multi-turn --version
```

### Quick Start

```bash
# Initialize a basic configuration
multi-turn init-config --output my_config.yaml --template basic

# List available tasks
multi-turn list-tasks

# Run a simple evaluation
multi-turn run --model-id gpt-4 --task-id swe_bench_lite_001 --max-turns 10
```

## Configuration Management

### Creating Configurations

```bash
# Create basic configuration
multi-turn init-config --output basic_config.yaml --template basic

# Create advanced configuration with specific model
multi-turn init-config \
  --output advanced_config.yaml \
  --template advanced \
  --model-id claude-3-sonnet \
  --scenario swe_bench

# Create configuration for specific benchmark
multi-turn init-config \
  --output intercode_config.yaml \
  --template intercode \
  --model-id gpt-4

# Create custom configuration from scratch
multi-turn init-config \
  --output custom_config.yaml \
  --template custom \
  --interactive
```

### Validating Configurations

```bash
# Validate configuration file
multi-turn validate-config config.yaml

# Validate with verbose output
multi-turn validate-config config.yaml --verbose

# Validate multiple configurations
for config in configs/*.yaml; do
  echo "Validating $config"
  multi-turn validate-config "$config"
done

# Validate and show configuration summary
multi-turn validate-config config.yaml --show-summary
```

## Running Evaluations

### Basic Evaluation Runs

```bash
# Run with configuration file
multi-turn run-config config.yaml

# Run with configuration file and custom output
multi-turn run-config config.yaml --output results.json

# Run with configuration file in interactive mode
multi-turn run-config config.yaml --interactive

# Run with specific output format
multi-turn run-config config.yaml --output results.csv --format csv
```

### Direct Parameter Runs

```bash
# Simple single-task evaluation
multi-turn run \
  --model-id gpt-4 \
  --task-id swe_bench_lite_001 \
  --max-turns 10 \
  --timeout 3600

# Multi-task evaluation
multi-turn run \
  --model-id claude-3-sonnet \
  --task-id swe_bench_lite_001 \
  --task-id intercode_python_001 \
  --task-id convcode_web_dev_001 \
  --max-turns 15 \
  --timeout 7200

# Evaluation with custom feedback strategy
multi-turn run \
  --model-id gpt-4 \
  --task-id bugs_in_py_pandas_001 \
  --max-turns 20 \
  --feedback-strategy full \
  --safety-level strict \
  --output detailed_results.json

# Evaluation with context retention disabled
multi-turn run \
  --model-id claude-3-sonnet \
  --task-id convcode_bench_001 \
  --max-turns 25 \
  --no-context \
  --interactive
```

### Scenario-Specific Runs

```bash
# SWE-bench evaluation
multi-turn run \
  --model-id gpt-4 \
  --task-id swe_bench_lite_django_001 \
  --task-id swe_bench_lite_requests_002 \
  --max-turns 15 \
  --timeout 7200 \
  --feedback-strategy adaptive \
  --safety-level moderate \
  --output swe_bench_results.json

# InterCode evaluation
multi-turn run \
  --model-id claude-3-sonnet \
  --task-id intercode_python_basic_001 \
  --task-id intercode_bash_intermediate_001 \
  --max-turns 12 \
  --timeout 3600 \
  --feedback-strategy full \
  --interactive

# ConvCodeBench evaluation
multi-turn run \
  --model-id gpt-4 \
  --task-id convcode_web_development_001 \
  --task-id convcode_data_analysis_002 \
  --max-turns 20 \
  --timeout 5400 \
  --enable-context-retention \
  --output convcode_results.json

# BugsInPy evaluation
multi-turn run \
  --model-id claude-3-sonnet \
  --task-id bugs_in_py_pandas_001 \
  --task-id bugs_in_py_numpy_002 \
  --max-turns 18 \
  --timeout 9000 \
  --feedback-strategy full \
  --safety-level moderate

# Defects4J evaluation
multi-turn run \
  --model-id gpt-4 \
  --task-id defects4j_lang_001 \
  --task-id defects4j_math_002 \
  --max-turns 20 \
  --timeout 10800 \
  --feedback-strategy full \
  --safety-level moderate
```

## Monitoring and Results

### Real-time Monitoring

```bash
# Monitor local evaluation
multi-turn monitor

# Monitor remote evaluation
multi-turn monitor --host api.example.com --port 8000

# Monitor with authentication
multi-turn monitor --host api.example.com --port 8000 --token your_token

# Monitor specific evaluation
multi-turn monitor --evaluation-id mt_eval_20241201_143022

# Monitor with custom refresh rate
multi-turn monitor --refresh-interval 10
```

### Exporting Results

```bash
# Export results to different formats
multi-turn export --input results.json --output report.pdf --format pdf
multi-turn export --input results.json --output report.html --format html
multi-turn export --input results.json --output report.csv --format csv

# Export with charts and analysis
multi-turn export \
  --input results.json \
  --output comprehensive_report.pdf \
  --format pdf \
  --include-charts \
  --include-analysis \
  --include-summary

# Export comparison report
multi-turn export \
  --input current_results.json \
  --baseline baseline_results.json \
  --output comparison_report.html \
  --format html \
  --comparison-mode
```

### Results Analysis

```bash
# Analyze results
multi-turn analyze results.json

# Analyze with specific metrics
multi-turn analyze results.json --metrics success_rate,avg_turns,cost

# Compare with baseline
multi-turn analyze results.json --baseline baseline_results.json

# Generate detailed analysis report
multi-turn analyze results.json --output analysis_report.html --detailed
```

## Task Management

### Listing and Describing Tasks

```bash
# List all available tasks
multi-turn list-tasks

# List tasks by category
multi-turn list-tasks --category multi_turn
multi-turn list-tasks --category single_turn
multi-turn list-tasks --category swe_bench
multi-turn list-tasks --category intercode

# List tasks with specific format
multi-turn list-tasks --format table
multi-turn list-tasks --format json
multi-turn list-tasks --format yaml

# Describe specific task
multi-turn describe-task swe_bench_lite_001
multi-turn describe-task intercode_python_basic_001

# Describe task with detailed information
multi-turn describe-task swe_bench_lite_001 --format json --detailed
```

### Task Filtering and Search

```bash
# Search tasks by keyword
multi-turn list-tasks --search "python"
multi-turn list-tasks --search "bug fixing"
multi-turn list-tasks --search "web development"

# Filter tasks by difficulty
multi-turn list-tasks --difficulty easy
multi-turn list-tasks --difficulty medium
multi-turn list-tasks --difficulty hard

# Filter tasks by estimated time
multi-turn list-tasks --max-time 3600  # Tasks taking less than 1 hour
multi-turn list-tasks --min-time 7200  # Tasks taking more than 2 hours

# Combine filters
multi-turn list-tasks \
  --category swe_bench \
  --difficulty medium \
  --search "django" \
  --format table
```

## Advanced Usage

### Custom Model Integration

```bash
# Run with custom model configuration
multi-turn run \
  --model-id custom_model \
  --model-config '{"temperature": 0.7, "max_tokens": 2000}' \
  --task-id swe_bench_lite_001

# Run with model-specific parameters
multi-turn run \
  --model-id gpt-4 \
  --model-config-file model_config.json \
  --task-id intercode_python_001

# Run with multiple model configurations for comparison
multi-turn run \
  --model-id gpt-4 \
  --model-config '{"temperature": 0.5}' \
  --task-id swe_bench_lite_001 \
  --output gpt4_temp05_results.json

multi-turn run \
  --model-id gpt-4 \
  --model-config '{"temperature": 0.9}' \
  --task-id swe_bench_lite_001 \
  --output gpt4_temp09_results.json
```

### Environment Configuration

```bash
# Run with custom environment variables
EVALUATION_DEBUG=true \
EVALUATION_LOG_LEVEL=DEBUG \
multi-turn run-config config.yaml

# Run with resource limits
multi-turn run \
  --model-id gpt-4 \
  --task-id swe_bench_lite_001 \
  --memory-limit 4GB \
  --cpu-limit 2.0 \
  --timeout 7200

# Run with custom working directory
multi-turn run-config config.yaml --work-dir /tmp/evaluation_workspace

# Run with specific Python version
PYTHON_VERSION=3.9 multi-turn run-config python_config.yaml
```

### Debugging and Troubleshooting

```bash
# Run with verbose logging
multi-turn run-config config.yaml --verbose

# Run with debug mode
multi-turn run-config config.yaml --debug

# Run with dry-run mode (validate without executing)
multi-turn run-config config.yaml --dry-run

# Run with step-by-step execution
multi-turn run-config config.yaml --step-by-step

# Run with safety checks disabled (use with caution)
multi-turn run-config config.yaml --disable-safety-checks
```

## Batch Operations

### Running Multiple Evaluations

```bash
# Run multiple configurations sequentially
for config in configs/*.yaml; do
  echo "Running evaluation with $config"
  multi-turn run-config "$config" --output "results/$(basename $config .yaml)_results.json"
done

# Run evaluations in parallel (be careful with resource usage)
parallel -j 4 multi-turn run-config {} --output results/{/.}_results.json ::: configs/*.yaml

# Run with different models on same tasks
models=("gpt-4" "claude-3-sonnet" "custom-model")
for model in "${models[@]}"; do
  multi-turn run \
    --model-id "$model" \
    --task-id swe_bench_lite_001 \
    --max-turns 10 \
    --output "results/${model}_results.json"
done
```

### Batch Analysis

```bash
# Analyze multiple result files
multi-turn analyze results/*.json --output batch_analysis.html

# Compare multiple models
multi-turn compare \
  --results results/gpt4_results.json \
  --results results/claude_results.json \
  --results results/custom_results.json \
  --output model_comparison.html

# Generate summary report for all evaluations
multi-turn summarize results/*.json --output summary_report.pdf
```

### Automated Evaluation Pipeline

```bash
#!/bin/bash
# automated_evaluation.sh

set -e

# Configuration
MODELS=("gpt-4" "claude-3-sonnet")
SCENARIOS=("swe_bench" "intercode" "convcode_bench")
RESULTS_DIR="results/$(date +%Y%m%d_%H%M%S)"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Run evaluations
for model in "${MODELS[@]}"; do
  for scenario in "${SCENARIOS[@]}"; do
    echo "Running $scenario evaluation with $model"
    
    config_file="configs/${scenario}_config.yaml"
    output_file="$RESULTS_DIR/${model}_${scenario}_results.json"
    
    # Update model in config (using yq or sed)
    sed "s/model_id: .*/model_id: \"$model\"/" "$config_file" > "/tmp/${model}_${scenario}_config.yaml"
    
    # Run evaluation
    multi-turn run-config "/tmp/${model}_${scenario}_config.yaml" --output "$output_file"
    
    # Clean up temporary config
    rm "/tmp/${model}_${scenario}_config.yaml"
  done
done

# Generate comparison report
multi-turn compare --results "$RESULTS_DIR"/*.json --output "$RESULTS_DIR/comparison_report.html"

# Generate summary
multi-turn summarize "$RESULTS_DIR"/*.json --output "$RESULTS_DIR/summary.pdf"

echo "Evaluation pipeline completed. Results in $RESULTS_DIR"
```

## Integration Examples

### CI/CD Integration

```bash
# GitHub Actions example
name: Multi-Turn Evaluation
on: [push, pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install multi-turn-evaluation-engine
        pip install -r requirements.txt
    - name: Run evaluation
      run: |
        multi-turn run-config ci_config.yaml --output results.json
      env:
        EVALUATION_API_KEY: ${{ secrets.EVALUATION_API_KEY }}
    - name: Upload results
      uses: actions/upload-artifact@v2
      with:
        name: evaluation-results
        path: results.json
```

### Jenkins Pipeline

```bash
# Jenkinsfile
pipeline {
    agent any
    
    environment {
        EVALUATION_API_KEY = credentials('evaluation-api-key')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install multi-turn-evaluation-engine'
            }
        }
        
        stage('Validate Config') {
            steps {
                sh 'multi-turn validate-config evaluation_config.yaml'
            }
        }
        
        stage('Run Evaluation') {
            steps {
                sh '''
                    multi-turn run-config evaluation_config.yaml \
                        --output results.json \
                        --format json
                '''
            }
        }
        
        stage('Generate Report') {
            steps {
                sh '''
                    multi-turn export \
                        --input results.json \
                        --output evaluation_report.html \
                        --format html \
                        --include-charts
                '''
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: '.',
                    reportFiles: 'evaluation_report.html',
                    reportName: 'Evaluation Report'
                ])
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'results.json,evaluation_report.html'
        }
    }
}
```

### Docker Integration

```bash
# Run evaluation in Docker container
docker run -it \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/results:/app/results \
  -e EVALUATION_API_KEY=your_key \
  evaluation-engine:latest \
  multi-turn run-config /app/config/config.yaml --output /app/results/results.json

# Docker Compose for distributed evaluation
version: '3.8'
services:
  evaluation-coordinator:
    image: evaluation-engine:latest
    command: multi-turn coordinate --workers 3
    environment:
      - EVALUATION_API_KEY=${EVALUATION_API_KEY}
    volumes:
      - ./config:/app/config
      - ./results:/app/results
  
  evaluation-worker-1:
    image: evaluation-engine:latest
    command: multi-turn worker --coordinator evaluation-coordinator:8000
    depends_on:
      - evaluation-coordinator
  
  evaluation-worker-2:
    image: evaluation-engine:latest
    command: multi-turn worker --coordinator evaluation-coordinator:8000
    depends_on:
      - evaluation-coordinator
  
  evaluation-worker-3:
    image: evaluation-engine:latest
    command: multi-turn worker --coordinator evaluation-coordinator:8000
    depends_on:
      - evaluation-coordinator
```

### Kubernetes Deployment

```yaml
# kubernetes/evaluation-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: multi-turn-evaluation
spec:
  template:
    spec:
      containers:
      - name: evaluation
        image: evaluation-engine:latest
        command: ["multi-turn", "run-config", "/config/config.yaml"]
        env:
        - name: EVALUATION_API_KEY
          valueFrom:
            secretKeyRef:
              name: evaluation-secrets
              key: api-key
        volumeMounts:
        - name: config-volume
          mountPath: /config
        - name: results-volume
          mountPath: /results
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
      volumes:
      - name: config-volume
        configMap:
          name: evaluation-config
      - name: results-volume
        persistentVolumeClaim:
          claimName: evaluation-results-pvc
      restartPolicy: Never
  backoffLimit: 3
```

### Monitoring Integration

```bash
# Prometheus metrics collection
multi-turn run-config config.yaml --enable-metrics --metrics-port 9090

# Grafana dashboard setup
multi-turn setup-monitoring --grafana-url http://grafana:3000 --prometheus-url http://prometheus:9090

# Custom monitoring script
#!/bin/bash
# monitor_evaluation.sh

EVALUATION_ID=$1
WEBHOOK_URL=$2

while true; do
  status=$(multi-turn status --evaluation-id "$EVALUATION_ID" --format json)
  
  # Send status to monitoring system
  curl -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "$status"
  
  # Check if evaluation is complete
  if echo "$status" | jq -r '.status' | grep -E "(completed|failed|cancelled)"; then
    break
  fi
  
  sleep 30
done
```

These CLI examples provide comprehensive coverage of the Multi-Turn Evaluation Engine's command-line interface, from basic usage to advanced integration scenarios. Use these examples as templates for your own evaluation workflows.