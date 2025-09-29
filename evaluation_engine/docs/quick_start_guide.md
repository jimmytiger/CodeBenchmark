# Quick Start Guide - Config-Driven Evaluation

This guide will get you up and running with config-driven evaluation in just a few minutes.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Your First Evaluation](#your-first-evaluation)
4. [Understanding the Results](#understanding-the-results)
5. [Next Steps](#next-steps)

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.8+** installed
2. **API Keys** for the models you want to use:
   - OpenAI API key (for GPT models)
   - Anthropic API key (for Claude models)
   - Hugging Face token (for HF models, optional)

## Installation

### 1. Install the Evaluation Engine

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd evaluation-engine

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

### 2. Set Up Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required for OpenAI models
export OPENAI_API_KEY="your-openai-api-key-here"

# Required for Anthropic models
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"

# Optional: Set output directory
export EVAL_OUTPUT_DIR="./evaluation_results"
```

### 3. Verify Installation

```python
# Test the installation
from evaluation_engine import ConfigDrivenEvaluator

evaluator = ConfigDrivenEvaluator()
print("✅ Installation successful!")
```

## Your First Evaluation

### Step 1: Create a Simple Configuration

Create a file called `my_first_eval.yaml`:

```yaml
# my_first_eval.yaml
metadata:
  name: "My First Evaluation"
  version: "1.0"
  author: "Your Name"

# Define the model you want to test
models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.7
      max_tokens: 1000
    system_prompt: "You are a helpful assistant. Answer questions accurately."

# Define what tasks to run
tasks:
  - name: "commonsense_test"
    description: "Test commonsense reasoning"
    model_ref: "gpt35"
    task_name: "hellaswag"
    num_fewshot: 5
    batch_size: 4
    task_config:
      limit: 20  # Small number for quick testing

# Configure output
output:
  directory: "./my_first_results"
  formats: ["json", "html"]
  generate_report: true
```

### Step 2: Run the Evaluation

#### Option A: Using Python API

```python
from evaluation_engine import ConfigDrivenEvaluator

# Create evaluator
evaluator = ConfigDrivenEvaluator()

# Run the evaluation
print("🚀 Starting evaluation...")
result = evaluator.run_from_config("my_first_eval.yaml")

# Check results
if result.batch_result.is_successful:
    print("✅ Evaluation completed successfully!")
    print(f"📊 Results saved to: {result.output_directory}")
else:
    print("❌ Evaluation failed:")
    for error in result.batch_result.errors:
        print(f"  - {error}")
```

#### Option B: Using CLI (when available)

```bash
# Run the evaluation
eval-engine config run my_first_eval.yaml

# Run with verbose output
eval-engine config run my_first_eval.yaml --verbose

# Validate configuration without running
eval-engine config validate my_first_eval.yaml
```

### Step 3: Check Your Results

After the evaluation completes, you'll find:

```
my_first_results/
├── results/
│   └── commonsense_test_results.json    # Raw results
├── reports/
│   └── evaluation_report.html           # Interactive report
├── logs/
│   └── execution.log                    # Execution logs
└── metadata/
    ├── config.yaml                      # Your configuration
    └── execution_info.json              # Execution metadata
```

## Understanding the Results

### 1. View the HTML Report

Open `my_first_results/reports/evaluation_report.html` in your browser to see:

- **Executive Summary**: Overall performance metrics
- **Task Details**: Detailed results for each task
- **Model Performance**: Accuracy, response times, etc.
- **Sample Responses**: Examples of model outputs

### 2. Examine JSON Results

The JSON results file contains structured data:

```json
{
  "task_name": "commonsense_test",
  "model": "gpt35",
  "results": {
    "accuracy": 0.85,
    "num_examples": 20,
    "total_time": 45.2
  },
  "predictions": [
    {
      "question": "...",
      "prediction": "...",
      "correct": true
    }
  ]
}
```

### 3. Key Metrics to Look For

- **Accuracy**: Percentage of correct answers
- **Response Time**: Average time per question
- **Token Usage**: Number of tokens consumed
- **Error Rate**: Percentage of failed requests

## Next Steps

### 1. Try More Tasks

Expand your configuration to test different capabilities:

```yaml
tasks:
  - name: "commonsense_test"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      limit: 50

  - name: "reading_comprehension"
    model_ref: "gpt35"
    task_name: "arc_easy"
    task_config:
      limit: 30
    depends_on: ["commonsense_test"]  # Run after commonsense test

  - name: "math_reasoning"
    model_ref: "gpt35"
    task_name: "gsm8k"
    num_fewshot: 8
    task_config:
      limit: 25
      temperature: 0.1  # Lower temperature for math
    depends_on: ["reading_comprehension"]
```

### 2. Compare Multiple Models

Add more models to compare their performance:

```yaml
models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.7

  gpt4:
    type: "openai"
    model_name: "gpt-4"
    parameters:
      temperature: 0.7

  claude:
    type: "anthropic"
    model_name: "claude-3-sonnet-20240229"
    parameters:
      temperature: 0.7

tasks:
  # Test the same task with different models
  - name: "hellaswag_gpt35"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      limit: 50

  - name: "hellaswag_gpt4"
    model_ref: "gpt4"
    task_name: "hellaswag"
    task_config:
      limit: 50

  - name: "hellaswag_claude"
    model_ref: "claude"
    task_name: "hellaswag"
    task_config:
      limit: 50

output:
  compare_models: true  # Enable model comparison in reports
```

### 3. Use Variables for Flexibility

Make your configuration more flexible with variables:

```yaml
variables:
  test_limit: 100
  output_dir: "./results_${timestamp}"
  standard_temp: 0.7
  math_temp: 0.1

models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: "${standard_temp}"

tasks:
  - name: "reasoning_test"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      limit: "${test_limit}"

  - name: "math_test"
    model_ref: "gpt35"
    task_name: "gsm8k"
    task_config:
      limit: "${test_limit}"
      temperature: "${math_temp}"

output:
  directory: "${output_dir}"
```

### 4. Explore Example Configurations

Check out the example configurations in `evaluation_engine/config/examples/`:

- `basic_evaluation.yaml` - Simple starter configuration
- `multi_model_comparison.yaml` - Compare multiple models systematically
- `complex_task_dependencies.yaml` - Advanced dependency management
- `comprehensive_evaluation.yaml` - Full-featured evaluation setup

### 5. Learn Advanced Features

Explore more advanced features:

- **Task Dependencies**: Create complex evaluation workflows
- **Custom Prompt Templates**: Customize how questions are presented to models
- **Environment Variables**: Use environment variables for sensitive configuration
- **Batch Processing**: Optimize performance with appropriate batch sizes
- **Error Handling**: Configure how to handle failures and retries

## Common Issues and Solutions

### Issue: "Model not found" Error

**Problem**: The model name is incorrect or API key is missing.

**Solution**:
```yaml
# Make sure model names are correct
models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"  # Correct OpenAI model name
```

And ensure your API key is set:
```bash
export OPENAI_API_KEY="your-actual-api-key"
```

### Issue: "Task not found" Error

**Problem**: The task name doesn't exist in lm-evaluation-harness.

**Solution**: Use valid task names. Common ones include:
- `hellaswag` (commonsense reasoning)
- `arc_easy` (reading comprehension)
- `arc_challenge` (advanced reading comprehension)
- `gsm8k` (math word problems)
- `truthfulqa_mc` (truthfulness evaluation)

### Issue: Evaluation Takes Too Long

**Problem**: Large datasets or small batch sizes.

**Solution**:
```yaml
tasks:
  - name: "quick_test"
    model_ref: "gpt35"
    task_name: "hellaswag"
    batch_size: 8        # Increase batch size
    task_config:
      limit: 50          # Reduce number of examples for testing
```

### Issue: Out of Memory Errors

**Problem**: Batch size too large for available memory.

**Solution**:
```yaml
tasks:
  - name: "memory_friendly"
    model_ref: "gpt35"
    task_name: "hellaswag"
    batch_size: 2        # Reduce batch size
```

### Issue: API Rate Limits

**Problem**: Making requests too quickly.

**Solution**:
```yaml
models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      request_timeout: 60    # Increase timeout
      retry_attempts: 3      # Add retries

tasks:
  - name: "rate_limited_task"
    model_ref: "gpt35"
    task_name: "hellaswag"
    batch_size: 1          # Smaller batches to avoid rate limits
```

## Getting Help

### Documentation

- **Configuration Format**: See `config_file_format.md` for complete format reference
- **CLI Usage**: See `cli_usage_guide.md` for command-line interface details
- **Best Practices**: See `best_practices_guide.md` for optimization tips

### Validation

Always validate your configuration before running:

```python
from evaluation_engine import ConfigDrivenEvaluator

evaluator = ConfigDrivenEvaluator()
validation_result = evaluator.validate_config_file("my_config.yaml")

if not validation_result.is_valid:
    print("❌ Configuration errors:")
    for error in validation_result.errors:
        print(f"  - {error}")
else:
    print("✅ Configuration is valid!")
```

### Dry Run

Test your configuration without actually running the evaluation:

```python
# Dry run - validates and shows what would be executed
result = evaluator.run_from_config("my_config.yaml", dry_run=True)
print(f"Would execute {len(result.planned_tasks)} tasks")
```

## What's Next?

Now that you've completed your first evaluation:

1. **Experiment** with different models and tasks
2. **Compare** model performance on the same tasks
3. **Optimize** your configurations for your specific use cases
4. **Automate** evaluations in your development workflow
5. **Share** configurations with your team for consistent evaluation

Happy evaluating! 🚀