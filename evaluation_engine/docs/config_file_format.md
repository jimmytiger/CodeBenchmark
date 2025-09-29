# Configuration File Format Guide

This document provides a comprehensive guide to the configuration file format used by the evaluation engine's config-driven evaluation system.

## Table of Contents

1. [File Format Overview](#file-format-overview)
2. [Configuration Structure](#configuration-structure)
3. [Section Definitions](#section-definitions)
4. [Variable System](#variable-system)
5. [Model Configuration](#model-configuration)
6. [Task Configuration](#task-configuration)
7. [Output Configuration](#output-configuration)
8. [Advanced Features](#advanced-features)
9. [Validation Rules](#validation-rules)
10. [Examples](#examples)

## File Format Overview

The evaluation engine supports configuration files in two formats:

- **YAML** (recommended): `.yaml` or `.yml` extension
- **JSON**: `.json` extension

The system automatically detects the format based on the file extension and content.

### YAML Example
```yaml
metadata:
  name: "My Evaluation"
  version: "1.0"

models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"
```

### JSON Example
```json
{
  "metadata": {
    "name": "My Evaluation",
    "version": "1.0"
  },
  "models": {
    "gpt35": {
      "type": "openai",
      "model_name": "gpt-3.5-turbo"
    }
  }
}
```

## Configuration Structure

A complete configuration file consists of the following sections:

```yaml
metadata:          # Required: Basic information about the evaluation
variables:         # Optional: Variable definitions and environment references
models:            # Required: Model configurations
defaults:          # Optional: Default values for tasks
tasks:             # Required: Task definitions
output:            # Optional: Output configuration
```

### Minimal Configuration

The minimal required configuration includes:

```yaml
metadata:
  name: "Minimal Evaluation"

models:
  my_model:
    type: "openai"
    model_name: "gpt-3.5-turbo"

tasks:
  - name: "simple_task"
    model_ref: "my_model"
    task_name: "hellaswag"
```

## Section Definitions

### Metadata Section

The `metadata` section provides basic information about the evaluation configuration.

```yaml
metadata:
  name: "Evaluation Name"           # Required: Human-readable name
  version: "1.0"                    # Optional: Configuration version
  author: "Author Name"             # Optional: Configuration author
  description: "Description text"   # Optional: Detailed description
  created_at: "2024-01-15"         # Optional: Creation date
  tags: ["research", "comparison"]  # Optional: Classification tags
```

**Required Fields:**
- `name`: String identifying the evaluation

**Optional Fields:**
- `version`: Version string for tracking changes
- `author`: Author or team name
- `description`: Detailed description of the evaluation purpose
- `created_at`: Creation or last modified date
- `tags`: List of tags for categorization

### Variables Section

The `variables` section defines reusable values and environment variable references.

```yaml
variables:
  # Simple variables
  output_dir: "./results"
  batch_size: 8
  
  # Environment variables
  api_key: "${env:OPENAI_API_KEY}"
  home_dir: "${env:HOME}"
  
  # Nested variable references
  base_dir: "${home_dir}/evaluations"
  timestamped_dir: "${base_dir}/run_${timestamp}"
  
  # Complex values
  model_params:
    temperature: 0.7
    max_tokens: 1000
```

**Variable Types:**
- **Simple Values**: Strings, numbers, booleans
- **Environment References**: `${env:VARIABLE_NAME}`
- **Variable References**: `${variable_name}`
- **Complex Objects**: Nested dictionaries and lists

**Variable Resolution Order:**
1. Environment variables (`${env:...}`)
2. Defined variables in order of appearance
3. Nested variable references are resolved recursively

### Models Section

The `models` section defines all models used in the evaluation.

```yaml
models:
  model_id:                        # Unique identifier for the model
    name: "display_name"           # Optional: Display name
    type: "provider_type"          # Required: Model provider
    model_name: "actual_model"     # Required: Provider-specific model name
    parameters:                    # Optional: Model parameters
      temperature: 0.7
      max_tokens: 1000
      top_p: 0.95
    system_prompt: "prompt_text"   # Optional: System prompt
    prompt_template: "template"    # Optional: Prompt template
```

**Required Fields:**
- `type`: Model provider (`openai`, `anthropic`, `huggingface`, `custom`)
- `model_name`: Provider-specific model identifier

**Optional Fields:**
- `name`: Human-readable display name
- `parameters`: Dictionary of model-specific parameters
- `system_prompt`: System message or instruction
- `prompt_template`: Template for formatting prompts

**Supported Model Types:**

#### OpenAI Models
```yaml
openai_model:
  type: "openai"
  model_name: "gpt-4"
  parameters:
    temperature: 0.7
    max_tokens: 2000
    top_p: 0.95
    frequency_penalty: 0.0
    presence_penalty: 0.0
```

#### Anthropic Models
```yaml
anthropic_model:
  type: "anthropic"
  model_name: "claude-3-opus-20240229"
  parameters:
    temperature: 0.7
    max_tokens: 2000
    top_p: 0.95
```

#### Hugging Face Models
```yaml
huggingface_model:
  type: "huggingface"
  model_name: "meta-llama/Llama-2-7b-chat-hf"
  parameters:
    temperature: 0.7
    max_tokens: 1000
    do_sample: true
    top_p: 0.95
```

### Tasks Section

The `tasks` section defines the evaluation tasks to be executed.

```yaml
tasks:
  - name: "task_identifier"        # Required: Unique task name
    description: "task_description" # Optional: Human-readable description
    model_ref: "model_id"          # Required: Reference to model in models section
    task_name: "lm_eval_task"      # Required: lm-evaluation-harness task name
    num_fewshot: 5                 # Optional: Number of few-shot examples
    batch_size: 8                  # Optional: Batch size for processing
    task_config:                   # Optional: Task-specific configuration
      limit: 1000
      temperature: 0.1
    depends_on: ["other_task"]     # Optional: Task dependencies
```

**Required Fields:**
- `name`: Unique identifier for the task
- `model_ref`: Reference to a model defined in the `models` section
- `task_name`: Valid lm-evaluation-harness task name

**Optional Fields:**
- `description`: Human-readable description
- `num_fewshot`: Number of few-shot examples (overrides defaults)
- `batch_size`: Batch size for processing (overrides defaults)
- `task_config`: Dictionary of task-specific parameters
- `depends_on`: List of task names that must complete before this task

**Task Dependencies:**
Tasks can specify dependencies using the `depends_on` field:

```yaml
tasks:
  - name: "foundation_task"
    model_ref: "gpt35"
    task_name: "hellaswag"
    depends_on: []  # No dependencies

  - name: "dependent_task"
    model_ref: "gpt4"
    task_name: "arc_easy"
    depends_on: ["foundation_task"]  # Runs after foundation_task

  - name: "final_task"
    model_ref: "claude"
    task_name: "gsm8k"
    depends_on: ["foundation_task", "dependent_task"]  # Runs after both
```

### Defaults Section

The `defaults` section provides default values for task parameters.

```yaml
defaults:
  num_fewshot: 5                   # Default few-shot examples
  batch_size: 8                    # Default batch size
  output:                          # Default output configuration
    format: ["json"]
    save_predictions: true
  task_config:                     # Default task configuration
    temperature: 0.7
```

**Available Defaults:**
- `num_fewshot`: Default number of few-shot examples
- `batch_size`: Default batch size for all tasks
- `output`: Default output configuration
- `task_config`: Default task-specific parameters

### Output Section

The `output` section configures result storage and formatting.

```yaml
output:
  directory: "./results"           # Output directory path
  formats: ["json", "csv", "html"] # Output formats
  include_raw_responses: true      # Include raw model responses
  generate_report: true            # Generate HTML report
  compare_models: true             # Enable model comparison
  
  # Advanced options
  compression: "gzip"              # Compress output files
  timestamp_dirs: true             # Create timestamped subdirectories
  
  # Report customization
  report_title: "Custom Title"     # Custom report title
  report_sections:                 # Custom report sections
    - "executive_summary"
    - "detailed_results"
    - "model_comparison"
```

**Output Formats:**
- `json`: Structured JSON results
- `csv`: Tabular CSV format
- `html`: Interactive HTML report
- `yaml`: YAML format results

**Advanced Options:**
- `compression`: Compress output files (`gzip`, `zip`, `none`)
- `timestamp_dirs`: Create timestamped subdirectories
- `include_raw_responses`: Include full model responses
- `generate_report`: Generate comprehensive HTML report
- `compare_models`: Enable model comparison features

## Variable System

The variable system provides powerful templating and reuse capabilities.

### Variable Definition

Variables are defined in the `variables` section:

```yaml
variables:
  # Simple values
  project_name: "my_evaluation"
  batch_size: 8
  temperature: 0.7
  
  # Environment variables
  api_key: "${env:OPENAI_API_KEY}"
  home_dir: "${env:HOME}"
  
  # Computed values
  output_dir: "${home_dir}/results/${project_name}"
  
  # Complex objects
  model_defaults:
    temperature: 0.7
    max_tokens: 1000
```

### Variable Usage

Variables are referenced using `${variable_name}` syntax:

```yaml
models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: "${temperature}"
      max_tokens: "${model_defaults.max_tokens}"

output:
  directory: "${output_dir}"
```

### Environment Variables

Environment variables are accessed using `${env:VARIABLE_NAME}`:

```yaml
variables:
  openai_key: "${env:OPENAI_API_KEY}"
  anthropic_key: "${env:ANTHROPIC_API_KEY}"
  output_base: "${env:EVAL_OUTPUT_DIR}"
```

### Nested References

Variables can reference other variables:

```yaml
variables:
  base_dir: "${env:HOME}/evaluations"
  project: "llm_comparison"
  timestamp: "20240115"
  output_dir: "${base_dir}/${project}_${timestamp}"
  
  # This resolves to: /home/user/evaluations/llm_comparison_20240115
```

### Variable Validation

The system validates variables during parsing:

- **Undefined Variables**: Error if referenced variable doesn't exist
- **Circular References**: Error if variables reference each other in a loop
- **Type Consistency**: Warning if variable types don't match usage context

## Model Configuration

### Model Types

#### OpenAI Configuration
```yaml
openai_model:
  type: "openai"
  model_name: "gpt-4"  # or "gpt-3.5-turbo", "gpt-4-turbo", etc.
  parameters:
    temperature: 0.7
    max_tokens: 2000
    top_p: 0.95
    frequency_penalty: 0.0
    presence_penalty: 0.0
    stop: ["\n\n"]  # Optional stop sequences
  system_prompt: "You are a helpful assistant."
  prompt_template: "Question: {question}\nAnswer:"
```

#### Anthropic Configuration
```yaml
anthropic_model:
  type: "anthropic"
  model_name: "claude-3-opus-20240229"  # or "claude-3-sonnet-20240229"
  parameters:
    temperature: 0.7
    max_tokens: 2000
    top_p: 0.95
  system_prompt: "You are Claude, an AI assistant."
  prompt_template: "Human: {question}\n\nAssistant:"
```

#### Hugging Face Configuration
```yaml
huggingface_model:
  type: "huggingface"
  model_name: "meta-llama/Llama-2-7b-chat-hf"
  parameters:
    temperature: 0.7
    max_tokens: 1000
    do_sample: true
    top_p: 0.95
    repetition_penalty: 1.1
  system_prompt: "You are a helpful assistant."
  prompt_template: "[INST] {question} [/INST]"
```

### Prompt Templates

Prompt templates define how questions are formatted for each model:

```yaml
models:
  gpt4:
    type: "openai"
    model_name: "gpt-4"
    prompt_template: |
      Context: You are evaluating the model's reasoning ability.
      
      Question: {question}
      
      Please provide a clear and accurate answer:
```

**Template Variables:**
- `{question}`: The main question or prompt
- `{context}`: Additional context (if provided by task)
- `{examples}`: Few-shot examples (automatically inserted)

### System Prompts

System prompts provide consistent instructions across all tasks:

```yaml
models:
  reasoning_model:
    type: "openai"
    model_name: "gpt-4"
    system_prompt: |
      You are an expert reasoning assistant. For each question:
      1. Read carefully and understand what is being asked
      2. Think through the problem step by step
      3. Provide a clear, accurate answer
      4. Be concise but thorough in your reasoning
```

## Task Configuration

### Task Names

Tasks must use valid lm-evaluation-harness task names. Common tasks include:

**Reasoning Tasks:**
- `hellaswag`: Commonsense reasoning
- `arc_easy`: Easy reading comprehension
- `arc_challenge`: Challenging reading comprehension
- `winogrande`: Pronoun resolution reasoning

**Math Tasks:**
- `gsm8k`: Grade school math word problems
- `math_algebra`: Algebraic reasoning
- `math_geometry`: Geometric reasoning

**Code Tasks:**
- `humaneval`: Python code generation
- `mbpp`: Basic Python programming

**Safety Tasks:**
- `truthfulqa_mc`: Truthfulness evaluation
- `ethics_cm`: Commonsense morality

### Task-Specific Configuration

Tasks can have specific configuration parameters:

```yaml
tasks:
  - name: "math_evaluation"
    model_ref: "gpt4"
    task_name: "gsm8k"
    task_config:
      limit: 1000          # Limit number of examples
      temperature: 0.0     # Override model temperature
      max_gen_toks: 512    # Maximum generation tokens
      batch_size: 4        # Override batch size
      num_fewshot: 8       # Override few-shot count
```

### Dependency Management

Complex dependency patterns:

```yaml
tasks:
  # Parallel foundation tasks
  - name: "foundation_a"
    model_ref: "gpt35"
    task_name: "hellaswag"
    depends_on: []

  - name: "foundation_b"
    model_ref: "gpt4"
    task_name: "arc_easy"
    depends_on: []

  # Convergent dependency
  - name: "intermediate"
    model_ref: "claude"
    task_name: "gsm8k"
    depends_on: ["foundation_a", "foundation_b"]

  # Sequential chain
  - name: "advanced"
    model_ref: "gpt4"
    task_name: "arc_challenge"
    depends_on: ["intermediate"]

  # Final task depends on all
  - name: "final"
    model_ref: "gpt4"
    task_name: "truthfulqa_mc"
    depends_on: ["foundation_a", "foundation_b", "intermediate", "advanced"]
```

## Output Configuration

### Directory Structure

The output directory structure is automatically created:

```
output_directory/
├── results/
│   ├── task1_results.json
│   ├── task2_results.json
│   └── ...
├── raw_responses/
│   ├── task1_responses.json
│   └── ...
├── reports/
│   ├── evaluation_report.html
│   ├── model_comparison.html
│   └── ...
├── logs/
│   ├── execution.log
│   └── errors.log
└── metadata/
    ├── config.yaml
    ├── execution_info.json
    └── dependency_graph.json
```

### Report Generation

HTML reports include:

- **Executive Summary**: High-level results and insights
- **Task Results**: Detailed results for each task
- **Model Comparison**: Side-by-side model performance
- **Dependency Analysis**: Task execution flow and timing
- **Error Analysis**: Failed tasks and error details

## Advanced Features

### Template Inheritance

Configuration files can extend other configurations:

```yaml
# base_config.yaml
metadata:
  name: "Base Configuration"

models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"

defaults:
  num_fewshot: 5
  batch_size: 8
```

```yaml
# extended_config.yaml
extends: "base_config.yaml"

metadata:
  name: "Extended Configuration"  # Overrides base

models:
  gpt4:  # Adds to base models
    type: "openai"
    model_name: "gpt-4"

tasks:
  - name: "new_task"
    model_ref: "gpt4"
    task_name: "hellaswag"
```

### Configuration Includes

Include other configuration files:

```yaml
# main_config.yaml
metadata:
  name: "Main Configuration"

include:
  - "models/openai_models.yaml"
  - "models/anthropic_models.yaml"
  - "tasks/reasoning_tasks.yaml"

variables:
  output_dir: "./results"
```

### Conditional Configuration

Use environment variables for conditional configuration:

```yaml
variables:
  # Use different models based on environment
  primary_model: "${env:PRIMARY_MODEL}"
  test_mode: "${env:TEST_MODE}"
  
  # Conditional limits
  task_limit: |
    {% if test_mode == "true" %}
    50
    {% else %}
    1000
    {% endif %}

tasks:
  - name: "adaptive_task"
    model_ref: "${primary_model}"
    task_name: "hellaswag"
    task_config:
      limit: "${task_limit}"
```

## Validation Rules

### Required Fields Validation

The system validates that all required fields are present:

- `metadata.name`: Must be a non-empty string
- `models`: Must contain at least one model
- `models.*.type`: Must be a valid model type
- `models.*.model_name`: Must be a non-empty string
- `tasks`: Must contain at least one task
- `tasks.*.name`: Must be unique within the configuration
- `tasks.*.model_ref`: Must reference an existing model
- `tasks.*.task_name`: Must be a valid lm-eval task name

### Reference Validation

- **Model References**: All `model_ref` values must exist in `models`
- **Task Dependencies**: All `depends_on` values must reference existing tasks
- **Variable References**: All `${variable_name}` must be defined
- **Environment Variables**: All `${env:VAR}` should exist (warning if missing)

### Circular Dependency Detection

The system detects and prevents circular dependencies:

```yaml
# This will cause a validation error
tasks:
  - name: "task_a"
    model_ref: "gpt35"
    task_name: "hellaswag"
    depends_on: ["task_b"]

  - name: "task_b"
    model_ref: "gpt35"
    task_name: "arc_easy"
    depends_on: ["task_a"]  # Circular dependency!
```

### Data Type Validation

- **Strings**: Must be valid strings where expected
- **Numbers**: Must be valid numbers for numeric fields
- **Booleans**: Must be true/false for boolean fields
- **Lists**: Must be arrays where lists are expected
- **Objects**: Must be dictionaries where objects are expected

## Examples

### Complete Example

```yaml
# complete_example.yaml
metadata:
  name: "Complete Evaluation Example"
  version: "1.0"
  author: "Evaluation Team"
  description: "Demonstrates all configuration features"

variables:
  # Environment setup
  output_base: "${env:HOME}/evaluations"
  project_name: "complete_eval"
  timestamp: "20240115"
  output_dir: "${output_base}/${project_name}_${timestamp}"
  
  # Model parameters
  reasoning_temp: 0.1
  creative_temp: 0.7
  standard_tokens: 1500
  
  # Task parameters
  quick_limit: 50
  standard_limit: 200
  comprehensive_limit: 1000

models:
  gpt4_reasoning:
    name: "GPT-4 Reasoning"
    type: "openai"
    model_name: "gpt-4"
    parameters:
      temperature: "${reasoning_temp}"
      max_tokens: "${standard_tokens}"
    system_prompt: "You are an expert reasoning assistant."
    prompt_template: "Question: {question}\n\nThinking step by step:\n\nAnswer:"

  claude_creative:
    name: "Claude Creative"
    type: "anthropic"
    model_name: "claude-3-opus-20240229"
    parameters:
      temperature: "${creative_temp}"
      max_tokens: "${standard_tokens}"
    system_prompt: "You are Claude, a creative and helpful AI assistant."
    prompt_template: "Human: {question}\n\nAssistant:"

defaults:
  num_fewshot: 5
  batch_size: 4
  output:
    format: ["json", "csv"]
    save_predictions: true

tasks:
  - name: "reasoning_foundation"
    description: "Foundation reasoning test"
    model_ref: "gpt4_reasoning"
    task_name: "hellaswag"
    num_fewshot: 10
    task_config:
      limit: "${standard_limit}"
    depends_on: []

  - name: "creative_reasoning"
    description: "Creative reasoning test"
    model_ref: "claude_creative"
    task_name: "arc_easy"
    task_config:
      limit: "${standard_limit}"
    depends_on: ["reasoning_foundation"]

  - name: "comprehensive_evaluation"
    description: "Final comprehensive test"
    model_ref: "gpt4_reasoning"
    task_name: "gsm8k"
    num_fewshot: 8
    batch_size: 2
    task_config:
      limit: "${comprehensive_limit}"
      temperature: 0.0  # Override for math
    depends_on: ["reasoning_foundation", "creative_reasoning"]

output:
  directory: "${output_dir}"
  formats: ["json", "html", "csv"]
  include_raw_responses: true
  generate_report: true
  compare_models: true
  report_title: "Complete Evaluation Results"
```

This configuration demonstrates:
- Complete metadata with all optional fields
- Advanced variable system with environment variables and nested references
- Multiple model types with different configurations
- Complex task dependencies
- Comprehensive output configuration
- Parameter overrides at task level
- All major configuration features

## Best Practices

1. **Use Descriptive Names**: Choose clear, descriptive names for tasks and models
2. **Organize with Variables**: Use variables for repeated values and configuration
3. **Environment Variables**: Use environment variables for sensitive data like API keys
4. **Logical Dependencies**: Structure task dependencies to reflect logical evaluation flow
5. **Appropriate Limits**: Use task limits for development and testing
6. **Temperature Settings**: Use low temperatures for consistency, higher for creativity
7. **Batch Size Optimization**: Adjust batch sizes based on model capabilities and memory
8. **Documentation**: Include descriptions for complex tasks and configurations
9. **Version Control**: Use version numbers and timestamps for tracking changes
10. **Validation**: Always validate configurations before running evaluations