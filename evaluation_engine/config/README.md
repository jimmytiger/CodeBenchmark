# Configuration Module

The configuration module provides configuration-driven evaluation capabilities for the evaluation_engine. This allows users to define evaluation tasks through declarative configuration files instead of manual API calls.

## Features

- **Multiple Format Support**: YAML and JSON configuration files
- **Data Model Validation**: Comprehensive validation of configuration structure and content
- **Format Detection**: Automatic detection of configuration file formats
- **Error Handling**: Detailed error messages with suggestions for fixes
- **Type Safety**: Strong typing with dataclasses and validation

## Quick Start

### 1. Create a Configuration File

Create a YAML or JSON configuration file defining your evaluation setup:

```yaml
# evaluation_config.yaml
metadata:
  name: "My Evaluation"
  version: "1.0"
  author: "Your Name"

models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.7

tasks:
  - name: "hellaswag_test"
    model_ref: "gpt35"
    task_name: "hellaswag"
    num_fewshot: 5
```

### 2. Parse the Configuration

```python
from evaluation_engine.config import ConfigParser

parser = ConfigParser()
config = parser.parse_config("evaluation_config.yaml")

print(f"Config: {config.metadata.name}")
print(f"Tasks: {len(config.tasks)}")
print(f"Models: {len(config.models)}")
```

### 3. Validate Configuration Syntax

```python
result = parser.validate_syntax("evaluation_config.yaml")

if result.is_valid:
    print("Configuration is valid!")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

## Configuration Structure

### Required Fields

- `metadata.name`: Configuration name
- `tasks`: List of evaluation tasks (at least one required)

### Optional Fields

- `models`: Model definitions referenced by tasks
- `variables`: Reusable variables
- `defaults`: Default values for tasks
- `output`: Output configuration

### Example Configuration

```yaml
metadata:
  name: "Comprehensive Evaluation"
  version: "1.0"

variables:
  output_dir: "./results"
  batch_size: 32

models:
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.7
      max_tokens: 1000
    system_prompt: "You are a helpful assistant."

defaults:
  num_fewshot: 5
  batch_size: "${batch_size}"

tasks:
  - name: "hellaswag_evaluation"
    description: "HellaSwag commonsense reasoning"
    model_ref: "gpt35"
    task_name: "hellaswag"
    num_fewshot: 10
    batch_size: 16

output:
  directory: "${output_dir}"
  formats: ["json", "csv"]
  include_raw_responses: true
```

## Data Models

### EvaluationConfig
Main configuration container with metadata, tasks, models, and settings.

### TaskConfig
Individual evaluation task configuration:
- `name`: Unique task identifier
- `model_ref`: Reference to model in models section
- `task_name`: lm-eval task name (e.g., "hellaswag", "arc_easy")
- `num_fewshot`: Number of few-shot examples
- `batch_size`: Batch size for evaluation
- `depends_on`: List of task dependencies

### ModelConfig
Model configuration:
- `name`: Model identifier
- `type`: Model type ("openai", "anthropic", "huggingface", etc.)
- `model_name`: Actual model name
- `parameters`: Model-specific parameters
- `prompt_template`: Custom prompt template
- `system_prompt`: System prompt for the model

## Error Handling

The configuration system provides detailed error messages:

```python
try:
    config = parser.parse_config("config.yaml")
except ValueError as e:
    print(f"Configuration error: {e}")
```

Common error types:
- **Syntax errors**: Invalid YAML/JSON syntax
- **Validation errors**: Missing required fields, invalid data types
- **Reference errors**: Invalid model references in tasks

## Format Detection

The system automatically detects configuration file formats:

```python
from evaluation_engine.config import ConfigFormatDetector

detector = ConfigFormatDetector()
format_type = detector.detect_format("config.yaml")
print(f"Detected format: {format_type}")
```

Supported formats:
- **YAML**: `.yaml`, `.yml` extensions
- **JSON**: `.json` extension
- **Auto-detection**: Based on file content when extension is ambiguous

## Examples

See the `examples/` directory for complete configuration examples:
- `basic_config.yaml`: Basic YAML configuration
- `basic_config.json`: Basic JSON configuration

## Testing

Run the configuration module tests:

```bash
python -m pytest evaluation_engine/tests/config/ -v
```

## Integration

The configuration module is designed to be non-invasive and works alongside existing evaluation_engine functionality:

```python
# Existing API usage (unchanged)
from evaluation_engine import UnifiedEvaluationFramework
framework = UnifiedEvaluationFramework()

# New config-driven usage
from evaluation_engine.config import ConfigParser
parser = ConfigParser()
config = parser.parse_config("config.yaml")
```