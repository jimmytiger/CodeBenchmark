# Configuration-Driven Evaluation API Guide

This guide explains how to use the configuration-driven evaluation API endpoints to upload, validate, execute, and manage evaluation configurations.

## Overview

The Configuration API provides REST endpoints for:
- **Configuration Management**: Upload, validate, and manage configuration files
- **Execution Control**: Execute evaluations from configurations with real-time monitoring
- **Result Management**: Retrieve results and export in multiple formats
- **Task Status Tracking**: Monitor individual task progress and status

## API Endpoints

### Configuration Management

#### Upload Configuration
```http
POST /api/v1/config/upload
Content-Type: application/json

{
  "config_content": "metadata:\n  name: \"My Config\"\n...",
  "format": "yaml",
  "name": "My Configuration",
  "description": "Optional description"
}
```

#### Upload Configuration File
```http
POST /api/v1/config/upload-file
Content-Type: multipart/form-data

file: config.yaml
name: "My Configuration"
description: "Optional description"
```

#### Validate Configuration
```http
POST /api/v1/config/validate
Content-Type: application/json

{
  "config_content": "metadata:\n  name: \"My Config\"\n...",
  "format": "yaml"
}
```

#### List Configurations
```http
GET /api/v1/config/?page=1&page_size=20
```

#### Get Configuration Details
```http
GET /api/v1/config/{config_id}
```

#### Delete Configuration
```http
DELETE /api/v1/config/{config_id}
```

### Execution Management

#### Execute Configuration
```http
POST /api/v1/config/execute
Content-Type: application/json

{
  "config_id": "config-uuid",
  "task_filter": ["task1", "task2"],
  "parameter_overrides": {
    "variables": {
      "temperature": 0.5
    }
  },
  "fail_fast": false,
  "dry_run": false
}
```

#### Execute Inline Configuration
```http
POST /api/v1/config/execute
Content-Type: application/json

{
  "config_content": "metadata:\n  name: \"Inline Config\"\n...",
  "format": "yaml",
  "dry_run": true
}
```

#### List Executions
```http
GET /api/v1/config/executions?page=1&page_size=20&status=running
```

#### Get Execution Status
```http
GET /api/v1/config/executions/{evaluation_id}
```

#### Get Execution Results
```http
GET /api/v1/config/executions/{evaluation_id}/results
```

#### Cancel Execution
```http
POST /api/v1/config/executions/{evaluation_id}/cancel
```

### Result Export

#### Export Results
```http
POST /api/v1/config/executions/{evaluation_id}/export
Content-Type: application/json

{
  "evaluation_id": "eval-uuid",
  "format": "json",
  "include_raw_results": true,
  "include_config": true
}
```

#### Get Export Status
```http
GET /api/v1/config/exports/{export_id}/status
```

#### Download Export
```http
GET /api/v1/config/exports/{export_id}/download
```

## Configuration Format

### Basic Structure
```yaml
metadata:
  name: "My Evaluation Configuration"
  version: "1.0"
  author: "Your Name"
  description: "Description of the evaluation"

variables:
  output_dir: "./results"
  temperature: 0.7
  batch_size: 16

models:
  gpt35:
    name: "gpt35"
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: "${temperature}"
      max_tokens: 1000
    system_prompt: "You are a helpful assistant."
    prompt_template: "Question: {question}\\nAnswer:"

defaults:
  num_fewshot: 5
  batch_size: "${batch_size}"

tasks:
  - name: "hellaswag_test"
    description: "HellaSwag commonsense reasoning"
    model_ref: "gpt35"
    task_name: "hellaswag"
    num_fewshot: 10
    batch_size: 8
    task_config:
      limit: 100
    depends_on: []

output:
  directory: "${output_dir}"
  formats: ["json", "csv"]
  include_raw_responses: true
```

### Variable Substitution
- Use `${variable_name}` to reference variables
- Use `${env:ENV_VAR_NAME}` to reference environment variables
- Variables are resolved at execution time

### Task Dependencies
Tasks can depend on other tasks using the `depends_on` field:
```yaml
tasks:
  - name: "base_task"
    model_ref: "gpt35"
    task_name: "hellaswag"
    depends_on: []

  - name: "dependent_task"
    model_ref: "gpt35"
    task_name: "arc_easy"
    depends_on: ["base_task"]
```

## Parameter Overrides

You can override configuration parameters at execution time:

```json
{
  "parameter_overrides": {
    "variables": {
      "temperature": 0.1,
      "batch_size": 32
    },
    "defaults": {
      "num_fewshot": 10
    },
    "tasks": {
      "hellaswag_test": {
        "batch_size": 4
      }
    }
  }
}
```

## Response Models

### Configuration Upload Response
```json
{
  "config_id": "uuid",
  "name": "Configuration Name",
  "format": "yaml",
  "validation": {
    "is_valid": true,
    "status": "valid",
    "errors": [],
    "warnings": [],
    "task_count": 3,
    "model_count": 2
  },
  "uploaded_at": "2024-01-01T12:00:00Z",
  "size_bytes": 1024
}
```

### Execution Status Response
```json
{
  "evaluation_id": "uuid",
  "config_id": "uuid",
  "status": "running",
  "progress": 0.65,
  "start_time": "2024-01-01T12:00:00Z",
  "total_tasks": 3,
  "completed_tasks": 2,
  "failed_tasks": 0,
  "running_tasks": 1,
  "pending_tasks": 0,
  "current_task": "task3",
  "task_details": [
    {
      "task_name": "task1",
      "status": "completed",
      "progress": 1.0,
      "execution_time": 45.2
    }
  ],
  "dry_run": false,
  "fail_fast": false
}
```

### Execution Results Response
```json
{
  "evaluation_id": "uuid",
  "config_id": "uuid",
  "status": "completed",
  "total_execution_time": 120.5,
  "total_tasks": 3,
  "completed_tasks": 3,
  "failed_tasks": 0,
  "success_rate": 100.0,
  "task_results": {
    "task1": {
      "status": "completed",
      "metrics": {...}
    }
  },
  "task_summaries": {
    "task1": {
      "status": "completed",
      "execution_time": 45.2,
      "metrics_summary": {...}
    }
  },
  "execution_order": ["task1", "task2", "task3"]
}
```

## Error Handling

### Validation Errors
```json
{
  "is_valid": false,
  "status": "invalid",
  "errors": [
    {
      "type": "validation",
      "message": "Model 'nonexistent_model' referenced in task 'task1' not found",
      "severity": "error",
      "location": "tasks[0].model_ref",
      "suggestion": "Define the model in the 'models' section"
    }
  ]
}
```

### HTTP Error Responses
```json
{
  "detail": "Configuration not found",
  "error": "not_found",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Authentication

All endpoints require authentication. Include the JWT token in the Authorization header:

```http
Authorization: Bearer <your-jwt-token>
```

## Rate Limiting

API requests are rate-limited. Check response headers for rate limit information:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

## Best Practices

### Configuration Design
1. **Use descriptive names** for tasks and models
2. **Leverage variables** for reusable values
3. **Set appropriate dependencies** between tasks
4. **Include descriptions** for documentation

### Execution Management
1. **Use dry runs** to validate configurations before execution
2. **Filter tasks** for targeted testing
3. **Monitor progress** using status endpoints
4. **Handle failures** gracefully with appropriate error handling

### Performance Optimization
1. **Batch similar tasks** to reduce overhead
2. **Use appropriate batch sizes** for your models
3. **Consider task dependencies** for optimal execution order
4. **Monitor resource usage** during execution

### Error Recovery
1. **Validate configurations** before execution
2. **Use fail-fast mode** for quick error detection
3. **Check task dependencies** to avoid circular references
4. **Monitor execution logs** for debugging

## Examples

See `evaluation_engine/docs/config_api_examples.py` for complete Python examples demonstrating:
- Basic configuration workflow
- Inline configuration execution
- Batch operations
- Export workflow
- Error handling

## WebSocket Support

For real-time updates during execution, connect to the WebSocket endpoint:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?token=YOUR_TOKEN');
ws.send(JSON.stringify({
  type: 'subscribe_evaluation',
  evaluation_id: 'your-evaluation-id'
}));
```

## Integration with Existing API

The Configuration API is fully compatible with the existing evaluation API. You can:
- Use both APIs simultaneously
- Mix configuration-driven and programmatic evaluations
- Access the same underlying evaluation framework
- Share results and analysis tools

For more information, see the main API documentation and the configuration system documentation.