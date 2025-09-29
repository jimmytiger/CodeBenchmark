# Configuration Examples

This directory contains example configuration files demonstrating the configuration-driven evaluation capabilities of the evaluation engine.

## Examples

### 1. Basic Evaluation (`basic_evaluation.yaml`)

A simple starter example showing:
- Single model configuration (OpenAI GPT-3.5)
- Basic task definitions with simple dependencies
- Variable usage for common parameters
- Minimal output configuration
- Small test limits for quick validation

**Usage:**
```bash
# Using CLI (when implemented)
eval-engine config run basic_evaluation.yaml

# Using Python API
from evaluation_engine import ConfigDrivenEvaluator

evaluator = ConfigDrivenEvaluator()
result = evaluator.run_from_config("basic_evaluation.yaml")
```

### 2. Multi-Model Comparison (`multi_model_comparison.yaml`)

A systematic comparison example demonstrating:
- Multiple model types (OpenAI, Anthropic, Hugging Face)
- Same tasks executed across different models
- Consistent parameters for fair comparison
- Model-specific prompt templates and system prompts
- Comparison-optimized output configuration

**Key Features:**
- **Fair Comparison**: Same tasks, same parameters across models
- **Multiple Providers**: OpenAI GPT-4/3.5, Claude Opus/Sonnet, Llama 2
- **Standardized Evaluation**: Consistent few-shot examples and batch sizes
- **Comparison Metrics**: Built-in model comparison reporting

### 3. Complex Task Dependencies (`complex_task_dependencies.yaml`)

An advanced example showcasing:
- Multi-layered task dependency architecture
- Foundation → Basic → Intermediate → Advanced → Integration → Final layers
- Model specialization (reasoning, code, safety)
- Advanced variable system with nested references
- Comprehensive execution planning and resource management

**Dependency Layers:**
- **Foundation Layer**: Basic system validation
- **Basic Capability Layer**: Core competency testing
- **Intermediate Layer**: Advanced reasoning and specialized tasks
- **Advanced Layer**: Complex synthesis and domain-specific evaluation
- **Integration Layer**: Cross-domain validation
- **Final Layer**: Comprehensive evaluation summary

### 4. Comprehensive Evaluation (`comprehensive_evaluation.yaml`)

An advanced example demonstrating:
- Multiple model types (OpenAI, Anthropic, Hugging Face)
- Complex task dependencies and execution ordering
- Domain-specific task organization (reasoning, math, code, safety)
- Advanced variable usage with environment variables
- Comprehensive output configuration
- Task-specific parameter overrides

**Features Demonstrated:**
- **Variable System**: Environment variables, nested variable references
- **Model Templates**: Different prompt templates for different model types
- **Task Dependencies**: Complex dependency chains ensuring proper execution order
- **Parameter Overrides**: Task-specific temperature, batch size, and limit settings
- **Multi-Domain Evaluation**: Reasoning, math, code generation, and safety tasks

## Example Selection Guide

### Choose `basic_evaluation.yaml` if you:
- Are new to config-driven evaluation
- Want to test the system quickly
- Need a simple template to modify
- Have limited computational resources

### Choose `multi_model_comparison.yaml` if you:
- Want to compare different models systematically
- Need standardized evaluation across providers
- Are conducting model selection research
- Want to generate comparison reports

### Choose `complex_task_dependencies.yaml` if you:
- Need sophisticated execution ordering
- Want to demonstrate advanced dependency management
- Are building complex evaluation pipelines
- Need specialized model configurations for different tasks

### Choose `comprehensive_evaluation.yaml` if you:
- Want a full-featured evaluation setup
- Need production-ready configuration
- Are conducting comprehensive model assessment
- Want to explore all available features

## Configuration File Structure

### Required Sections

1. **metadata**: Basic information about the evaluation
2. **models**: Model configurations with parameters and templates
3. **tasks**: Evaluation tasks with model references and dependencies

### Optional Sections

1. **variables**: Reusable variables and environment variable references
2. **defaults**: Default values for common parameters
3. **output**: Output format and directory configuration

## Variable System

The configuration system supports:

- **Simple variables**: `"${variable_name}"`
- **Environment variables**: `"${env:ENV_VAR_NAME}"`
- **Nested references**: Variables can reference other variables

Example:
```yaml
variables:
  base_dir: "${env:HOME}/evaluations"
  timestamp: "20240115"
  output_dir: "${base_dir}/results_${timestamp}"

output:
  directory: "${output_dir}"
```

## Model Configuration

Models are defined with:
- **type**: Model provider (openai, anthropic, huggingface, custom)
- **model_name**: Actual model identifier
- **parameters**: Model-specific parameters (temperature, max_tokens, etc.)
- **prompt_template**: Optional custom prompt formatting
- **system_prompt**: Optional system message

## Task Dependencies

Tasks can depend on other tasks using the `depends_on` field:

```yaml
tasks:
  - name: "base_task"
    model_ref: "gpt4"
    task_name: "hellaswag"
    depends_on: []

  - name: "dependent_task"
    model_ref: "claude"
    task_name: "arc_easy"
    depends_on: ["base_task"]  # Runs after base_task completes
```

## Running Evaluations

### Dry Run (Validation Only)

```python
from evaluation_engine import ConfigDrivenEvaluator

evaluator = ConfigDrivenEvaluator()

# Validate configuration without execution
result = evaluator.run_from_config("config.yaml", dry_run=True)
print(f"Validation successful: {result.batch_result.is_successful}")
```

### Full Execution

```python
# Run all tasks
result = evaluator.run_from_config("config.yaml")

# Run specific tasks only
result = evaluator.run_from_config("config.yaml", task_filter=["task1", "task2"])

# Run with parameter overrides
overrides = {
    "defaults": {"batch_size": 4},
    "output": {"directory": "./custom_results"}
}
result = evaluator.run_from_config("config.yaml", parameter_overrides=overrides)
```

### Error Handling

```python
# Fail-fast mode (stop on first error)
result = evaluator.run_from_config("config.yaml", fail_fast=True)

# Continue on errors (default)
result = evaluator.run_from_config("config.yaml", fail_fast=False)
```

## Best Practices

1. **Use Variables**: Define reusable values in the variables section
2. **Environment Variables**: Use environment variables for sensitive data (API keys)
3. **Task Dependencies**: Organize tasks with proper dependencies for logical execution order
4. **Batch Sizes**: Adjust batch sizes based on model capabilities and memory constraints
5. **Temperature Settings**: Use lower temperatures for consistency, higher for creativity
6. **Limits**: Use task limits for faster testing and development
7. **Descriptive Names**: Use clear, descriptive names for tasks and models

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**: Ensure all referenced environment variables are set
2. **Invalid Task Names**: Verify task names exist in lm-evaluation-harness
3. **Circular Dependencies**: Check task dependencies for circular references
4. **Model Configuration**: Ensure model parameters are valid for the model type

### Validation

Always validate configurations before running:

```python
validation_result = evaluator.validate_config_file("config.yaml")
if not validation_result.is_valid:
    for error in validation_result.errors:
        print(f"Error: {error}")
```