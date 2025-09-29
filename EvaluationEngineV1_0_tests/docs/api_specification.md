# EvaluationEngineV1_0 Testing Framework - API Specification

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL and Versioning](#base-url-and-versioning)
4. [Request/Response Format](#requestresponse-format)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Evaluation Endpoints](#evaluation-endpoints)
8. [Task Management Endpoints](#task-management-endpoints)
9. [Adapter Management Endpoints](#adapter-management-endpoints)
10. [System Management Endpoints](#system-management-endpoints)
11. [WebSocket API](#websocket-api)
12. [Data Models](#data-models)
13. [Examples](#examples)
14. [SDK and Client Libraries](#sdk-and-client-libraries)

## Overview

The EvaluationEngineV1_0 Testing Framework provides a comprehensive REST API for managing and executing evaluation tests. The API supports both synchronous and asynchronous operations, real-time monitoring through WebSockets, and comprehensive validation of evaluation results.

### Key Features

- **RESTful Design**: Standard HTTP methods and status codes
- **Asynchronous Operations**: Long-running evaluations with status tracking
- **Real-time Updates**: WebSocket support for live progress monitoring
- **Comprehensive Validation**: Real execution validation and result verification
- **Security**: Authentication, rate limiting, and input validation
- **Extensibility**: Support for custom tasks and adapters

### API Capabilities

- Start and manage evaluation jobs
- Monitor evaluation progress in real-time
- Retrieve detailed results and metrics
- Manage custom tasks and adapters
- System health and performance monitoring
- Batch operations and concurrent evaluations

## Authentication

### API Key Authentication

The API uses API key authentication for secure access:

```http
Authorization: Bearer YOUR_API_KEY
```

### Obtaining API Keys

API keys can be generated through the admin interface or CLI:

```bash
# Generate new API key
python api/api_test_server.py --generate-key --user "test_user"

# List existing keys
python api/api_test_server.py --list-keys

# Revoke API key
python api/api_test_server.py --revoke-key "key_id"
```

### Authentication Examples

```bash
# Using curl with API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/api/v1/evaluations

# Using Python requests
import requests

headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

response = requests.get("http://localhost:8000/api/v1/evaluations", headers=headers)
```

## Base URL and Versioning

### Base URL

```
http://localhost:8000/api/v1
```

### API Versioning

The API uses URL path versioning:

- `v1`: Current stable version
- `v2`: Future version (in development)

### Version Compatibility

- **v1**: Stable, backward compatible
- **v2**: Beta, may have breaking changes

## Request/Response Format

### Content Types

- **Request**: `application/json`
- **Response**: `application/json`
- **File Upload**: `multipart/form-data`

### Standard Response Format

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "tasks",
      "reason": "Required field missing"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `202 Accepted`: Request accepted for processing
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request validation failed |
| `AUTHENTICATION_ERROR` | Authentication failed |
| `AUTHORIZATION_ERROR` | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | Requested resource not found |
| `RESOURCE_CONFLICT` | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `EXECUTION_ERROR` | Evaluation execution failed |
| `TIMEOUT_ERROR` | Request timeout |
| `DEPENDENCY_ERROR` | Missing dependencies |
| `CONFIGURATION_ERROR` | Invalid configuration |

### Error Handling Examples

```python
import requests

try:
    response = requests.post(
        "http://localhost:8000/api/v1/evaluations",
        json={"tasks": ["invalid_task"]},
        headers={"Authorization": "Bearer YOUR_API_KEY"}
    )
    response.raise_for_status()
    
except requests.exceptions.HTTPError as e:
    if response.status_code == 422:
        error_data = response.json()
        print(f"Validation error: {error_data['error']['message']}")
    elif response.status_code == 429:
        print("Rate limit exceeded, please wait")
    else:
        print(f"HTTP error: {e}")
        
except requests.exceptions.RequestException as e:
    print(f"Request error: {e}")
```

## Rate Limiting

### Rate Limits

- **Default**: 60 requests per minute per API key
- **Burst**: Up to 10 requests per second
- **Evaluation**: 5 concurrent evaluations per API key

### Rate Limit Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642248600
X-RateLimit-Retry-After: 15
```

### Rate Limit Handling

```python
import time
import requests

def make_request_with_retry(url, **kwargs):
    while True:
        response = requests.get(url, **kwargs)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('X-RateLimit-Retry-After', 60))
            print(f"Rate limited, waiting {retry_after} seconds")
            time.sleep(retry_after)
            continue
            
        return response
```

## Evaluation Endpoints

### Start Evaluation

Start a new evaluation job.

**Endpoint**: `POST /api/v1/evaluations`

**Request Body**:
```json
{
  "tasks": ["hellaswag", "arc_easy"],
  "model": "gpt-3.5-turbo",
  "config": {
    "num_fewshot": 5,
    "batch_size": 1,
    "limit": 100,
    "temperature": 0.0
  },
  "validation": {
    "validate_real_execution": true,
    "check_performance": true,
    "verify_no_mocks": true
  },
  "metadata": {
    "description": "Test evaluation",
    "tags": ["test", "validation"]
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "evaluation_id": "eval_123456789",
    "status": "queued",
    "created_at": "2024-01-15T10:30:00Z",
    "estimated_duration": 1800,
    "tasks": ["hellaswag", "arc_easy"],
    "model": "gpt-3.5-turbo"
  }
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": ["hellaswag"],
    "model": "gpt-3.5-turbo",
    "config": {
      "num_fewshot": 5,
      "batch_size": 1
    }
  }'
```

### Get Evaluation Status

Get the current status of an evaluation.

**Endpoint**: `GET /api/v1/evaluations/{evaluation_id}/status`

**Response**:
```json
{
  "success": true,
  "data": {
    "evaluation_id": "eval_123456789",
    "status": "running",
    "progress": {
      "completed_tasks": 1,
      "total_tasks": 2,
      "percentage": 50,
      "current_task": "arc_easy",
      "estimated_remaining": 900
    },
    "started_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:45:00Z"
  }
}
```

**Status Values**:
- `queued`: Evaluation is queued for execution
- `running`: Evaluation is currently running
- `completed`: Evaluation completed successfully
- `failed`: Evaluation failed with errors
- `cancelled`: Evaluation was cancelled
- `timeout`: Evaluation timed out

### Get Evaluation Results

Retrieve the results of a completed evaluation.

**Endpoint**: `GET /api/v1/evaluations/{evaluation_id}/results`

**Response**:
```json
{
  "success": true,
  "data": {
    "evaluation_id": "eval_123456789",
    "status": "completed",
    "results": {
      "hellaswag": {
        "acc": 0.7234,
        "acc_stderr": 0.0123,
        "acc_norm": 0.7456,
        "acc_norm_stderr": 0.0134
      },
      "arc_easy": {
        "acc": 0.8123,
        "acc_stderr": 0.0098,
        "acc_norm": 0.8234,
        "acc_norm_stderr": 0.0087
      }
    },
    "metadata": {
      "total_execution_time": 1654.32,
      "model_calls": 1250,
      "tokens_used": 125000,
      "cost_estimate": 0.25
    },
    "validation": {
      "real_execution_validated": true,
      "no_mocks_detected": true,
      "performance_validated": true
    }
  }
}
```

### List Evaluations

List all evaluations with optional filtering.

**Endpoint**: `GET /api/v1/evaluations`

**Query Parameters**:
- `status`: Filter by status (queued, running, completed, failed)
- `model`: Filter by model name
- `limit`: Number of results to return (default: 50, max: 200)
- `offset`: Number of results to skip (default: 0)
- `sort`: Sort field (created_at, updated_at, status)
- `order`: Sort order (asc, desc)

**Response**:
```json
{
  "success": true,
  "data": {
    "evaluations": [
      {
        "evaluation_id": "eval_123456789",
        "status": "completed",
        "tasks": ["hellaswag", "arc_easy"],
        "model": "gpt-3.5-turbo",
        "created_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T11:00:00Z"
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 50,
      "offset": 0,
      "has_more": true
    }
  }
}
```

### Cancel Evaluation

Cancel a running evaluation.

**Endpoint**: `DELETE /api/v1/evaluations/{evaluation_id}`

**Response**:
```json
{
  "success": true,
  "data": {
    "evaluation_id": "eval_123456789",
    "status": "cancelled",
    "cancelled_at": "2024-01-15T10:45:00Z"
  }
}
```

### Batch Evaluations

Start multiple evaluations in batch.

**Endpoint**: `POST /api/v1/evaluations/batch`

**Request Body**:
```json
{
  "evaluations": [
    {
      "tasks": ["hellaswag"],
      "model": "gpt-3.5-turbo",
      "config": {"num_fewshot": 5}
    },
    {
      "tasks": ["arc_easy"],
      "model": "gpt-4",
      "config": {"num_fewshot": 10}
    }
  ],
  "batch_config": {
    "max_concurrent": 2,
    "fail_fast": false
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "batch_id": "batch_123456789",
    "evaluation_ids": ["eval_111", "eval_222"],
    "status": "queued",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

## Task Management Endpoints

### List Available Tasks

Get a list of all available tasks.

**Endpoint**: `GET /api/v1/tasks`

**Query Parameters**:
- `type`: Filter by task type (builtin, custom)
- `category`: Filter by category
- `search`: Search in task names and descriptions

**Response**:
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "name": "hellaswag",
        "type": "builtin",
        "category": "multiple_choice",
        "description": "HellaSwag dataset for commonsense reasoning",
        "version": "1.0",
        "metrics": ["acc", "acc_norm"],
        "config_options": {
          "num_fewshot": {"type": "int", "default": 10, "range": [0, 25]},
          "batch_size": {"type": "int", "default": 1, "range": [1, 8]}
        }
      }
    ]
  }
}
```

### Get Task Details

Get detailed information about a specific task.

**Endpoint**: `GET /api/v1/tasks/{task_name}`

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "hellaswag",
    "type": "builtin",
    "category": "multiple_choice",
    "description": "HellaSwag dataset for commonsense reasoning",
    "version": "1.0",
    "dataset_info": {
      "size": 10042,
      "splits": ["validation", "test"],
      "languages": ["en"]
    },
    "metrics": [
      {
        "name": "acc",
        "description": "Accuracy",
        "higher_is_better": true
      }
    ],
    "examples": [
      {
        "input": "A woman is outside with a bucket and a dog...",
        "target": "C",
        "choices": ["A", "B", "C", "D"]
      }
    ]
  }
}
```

### Validate Custom Task

Validate a custom task definition.

**Endpoint**: `POST /api/v1/tasks/validate`

**Request Body**:
```json
{
  "task_definition": {
    "task": "custom_task",
    "dataset_path": "path/to/dataset",
    "description": "Custom task description",
    "output_type": "generate_until",
    "doc_to_text": "Question: {{question}}\nAnswer:",
    "doc_to_target": "{{answer}}",
    "metric_list": [
      {"metric": "exact_match"},
      {"metric": "bleu"}
    ]
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "valid": true,
    "task_name": "custom_task",
    "validation_results": {
      "structure_valid": true,
      "dataset_accessible": true,
      "metrics_valid": true,
      "examples_valid": true
    },
    "warnings": [
      "Dataset size is small (< 100 examples)"
    ]
  }
}
```

### Upload Custom Task

Upload a custom task file.

**Endpoint**: `POST /api/v1/tasks/upload`

**Request**: Multipart form data with task file

**Response**:
```json
{
  "success": true,
  "data": {
    "task_name": "uploaded_task",
    "file_path": "/tasks/custom/uploaded_task.py",
    "validation_status": "valid",
    "uploaded_at": "2024-01-15T10:30:00Z"
  }
}
```

## Adapter Management Endpoints

### List Available Adapters

Get a list of all available adapters.

**Endpoint**: `GET /api/v1/adapters`

**Response**:
```json
{
  "success": true,
  "data": {
    "adapters": [
      {
        "name": "lm_eval",
        "type": "builtin",
        "description": "lm-evaluation-harness adapter",
        "version": "1.0",
        "status": "active",
        "supported_tasks": ["hellaswag", "arc_easy", "winogrande"],
        "dependencies": ["lm_eval", "torch"],
        "last_validated": "2024-01-15T09:00:00Z"
      },
      {
        "name": "swe_bench",
        "type": "builtin",
        "description": "SWE-bench adapter for software engineering tasks",
        "version": "1.0",
        "status": "active",
        "supported_tasks": ["swe_bench_lite"],
        "dependencies": ["docker", "git"],
        "last_validated": "2024-01-15T08:30:00Z"
      }
    ]
  }
}
```

### Get Adapter Details

Get detailed information about a specific adapter.

**Endpoint**: `GET /api/v1/adapters/{adapter_name}`

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "lm_eval",
    "type": "builtin",
    "description": "lm-evaluation-harness adapter",
    "version": "1.0",
    "status": "active",
    "configuration": {
      "model_support": ["openai", "anthropic", "huggingface"],
      "batch_sizes": [1, 2, 4, 8],
      "max_tokens": 4096
    },
    "dependencies": [
      {"name": "lm_eval", "version": ">=0.4.0", "status": "installed"},
      {"name": "torch", "version": ">=1.9.0", "status": "installed"}
    ],
    "validation_history": [
      {
        "timestamp": "2024-01-15T09:00:00Z",
        "status": "passed",
        "tests_run": 5,
        "tests_passed": 5
      }
    ]
  }
}
```

### Test Adapter

Test an adapter's functionality.

**Endpoint**: `POST /api/v1/adapters/{adapter_name}/test`

**Request Body**:
```json
{
  "test_config": {
    "task_count": 1,
    "install_dependencies": true,
    "validate_integration": true,
    "test_tasks": ["hellaswag"]
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "test_id": "test_123456789",
    "adapter_name": "lm_eval",
    "status": "running",
    "started_at": "2024-01-15T10:30:00Z",
    "estimated_duration": 300
  }
}
```

### Get Adapter Test Results

Get the results of an adapter test.

**Endpoint**: `GET /api/v1/adapters/{adapter_name}/test/{test_id}`

**Response**:
```json
{
  "success": true,
  "data": {
    "test_id": "test_123456789",
    "adapter_name": "lm_eval",
    "status": "completed",
    "results": {
      "integration_test": "passed",
      "dependency_check": "passed",
      "task_execution": "passed",
      "performance_test": "passed"
    },
    "details": {
      "tasks_tested": ["hellaswag"],
      "execution_time": 245.67,
      "memory_usage": "512MB",
      "errors": []
    }
  }
}
```

## System Management Endpoints

### Health Check

Check the health status of the API server.

**Endpoint**: `GET /api/v1/health`

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0",
    "uptime": 86400,
    "checks": {
      "database": "healthy",
      "redis": "healthy",
      "disk_space": "healthy",
      "memory": "healthy"
    }
  }
}
```

### System Status

Get detailed system status information.

**Endpoint**: `GET /api/v1/status`

**Response**:
```json
{
  "success": true,
  "data": {
    "system": {
      "cpu_usage": 25.5,
      "memory_usage": 68.2,
      "disk_usage": 45.1,
      "load_average": [1.2, 1.5, 1.8]
    },
    "api": {
      "active_evaluations": 3,
      "queued_evaluations": 7,
      "total_requests": 15420,
      "error_rate": 0.02
    },
    "adapters": {
      "lm_eval": "active",
      "swe_bench": "active"
    }
  }
}
```

### Performance Metrics

Get performance metrics for the system.

**Endpoint**: `GET /api/v1/metrics`

**Query Parameters**:
- `period`: Time period (1h, 24h, 7d, 30d)
- `metrics`: Comma-separated list of metrics

**Response**:
```json
{
  "success": true,
  "data": {
    "period": "24h",
    "metrics": {
      "requests_per_hour": [45, 52, 38, 67, 89, 76],
      "response_time_avg": [120, 135, 98, 156, 203, 145],
      "error_rate": [0.01, 0.02, 0.01, 0.03, 0.04, 0.02],
      "evaluations_completed": [12, 15, 8, 20, 25, 18]
    },
    "summary": {
      "total_requests": 1250,
      "avg_response_time": 142.5,
      "total_evaluations": 98,
      "success_rate": 0.98
    }
  }
}
```

## WebSocket API

### Connection

Connect to the WebSocket endpoint for real-time updates.

**Endpoint**: `ws://localhost:8000/ws/v1/evaluations/{evaluation_id}`

**Authentication**: Include API key in query parameter or header

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/v1/evaluations/eval_123?api_key=YOUR_API_KEY');

ws.onopen = function(event) {
    console.log('Connected to evaluation updates');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Evaluation update:', data);
};
```

### Message Types

#### Status Update

```json
{
  "type": "status_update",
  "evaluation_id": "eval_123456789",
  "status": "running",
  "progress": {
    "completed_tasks": 1,
    "total_tasks": 2,
    "percentage": 50
  },
  "timestamp": "2024-01-15T10:45:00Z"
}
```

#### Task Completion

```json
{
  "type": "task_completed",
  "evaluation_id": "eval_123456789",
  "task_name": "hellaswag",
  "results": {
    "acc": 0.7234,
    "acc_stderr": 0.0123
  },
  "timestamp": "2024-01-15T10:45:00Z"
}
```

#### Error Notification

```json
{
  "type": "error",
  "evaluation_id": "eval_123456789",
  "error": {
    "code": "EXECUTION_ERROR",
    "message": "Task execution failed",
    "details": "Model API rate limit exceeded"
  },
  "timestamp": "2024-01-15T10:45:00Z"
}
```

#### Evaluation Complete

```json
{
  "type": "evaluation_complete",
  "evaluation_id": "eval_123456789",
  "status": "completed",
  "results": {
    "hellaswag": {"acc": 0.7234},
    "arc_easy": {"acc": 0.8123}
  },
  "timestamp": "2024-01-15T11:00:00Z"
}
```

## Data Models

### Evaluation Model

```json
{
  "evaluation_id": "string",
  "status": "queued|running|completed|failed|cancelled",
  "tasks": ["string"],
  "model": "string",
  "config": {
    "num_fewshot": "integer",
    "batch_size": "integer",
    "limit": "integer|null",
    "temperature": "number"
  },
  "validation": {
    "validate_real_execution": "boolean",
    "check_performance": "boolean",
    "verify_no_mocks": "boolean"
  },
  "metadata": {
    "description": "string",
    "tags": ["string"]
  },
  "created_at": "datetime",
  "started_at": "datetime|null",
  "completed_at": "datetime|null",
  "updated_at": "datetime"
}
```

### Task Model

```json
{
  "name": "string",
  "type": "builtin|custom",
  "category": "string",
  "description": "string",
  "version": "string",
  "dataset_info": {
    "size": "integer",
    "splits": ["string"],
    "languages": ["string"]
  },
  "metrics": [
    {
      "name": "string",
      "description": "string",
      "higher_is_better": "boolean"
    }
  ],
  "config_options": {
    "parameter_name": {
      "type": "string",
      "default": "any",
      "range": ["any"]
    }
  }
}
```

### Adapter Model

```json
{
  "name": "string",
  "type": "builtin|custom",
  "description": "string",
  "version": "string",
  "status": "active|inactive|error",
  "supported_tasks": ["string"],
  "dependencies": [
    {
      "name": "string",
      "version": "string",
      "status": "installed|missing|outdated"
    }
  ],
  "configuration": {
    "model_support": ["string"],
    "batch_sizes": ["integer"],
    "max_tokens": "integer"
  },
  "last_validated": "datetime"
}
```

### Result Model

```json
{
  "evaluation_id": "string",
  "task_name": "string",
  "metrics": {
    "metric_name": "number"
  },
  "metadata": {
    "execution_time": "number",
    "model_calls": "integer",
    "tokens_used": "integer",
    "cost_estimate": "number"
  },
  "validation": {
    "real_execution_validated": "boolean",
    "no_mocks_detected": "boolean",
    "performance_validated": "boolean"
  },
  "raw_data": "object|null"
}
```

## Examples

### Complete Evaluation Workflow

```python
import requests
import time

# Configuration
API_BASE = "http://localhost:8000/api/v1"
API_KEY = "your_api_key_here"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 1. Start evaluation
evaluation_request = {
    "tasks": ["hellaswag", "arc_easy"],
    "model": "gpt-3.5-turbo",
    "config": {
        "num_fewshot": 5,
        "batch_size": 1,
        "limit": 10
    },
    "validation": {
        "validate_real_execution": True,
        "check_performance": True
    }
}

response = requests.post(
    f"{API_BASE}/evaluations",
    json=evaluation_request,
    headers=HEADERS
)

evaluation_data = response.json()
evaluation_id = evaluation_data["data"]["evaluation_id"]
print(f"Started evaluation: {evaluation_id}")

# 2. Monitor progress
while True:
    status_response = requests.get(
        f"{API_BASE}/evaluations/{evaluation_id}/status",
        headers=HEADERS
    )
    
    status_data = status_response.json()
    status = status_data["data"]["status"]
    
    if status == "completed":
        print("Evaluation completed!")
        break
    elif status == "failed":
        print("Evaluation failed!")
        break
    elif status == "running":
        progress = status_data["data"]["progress"]
        print(f"Progress: {progress['percentage']}%")
    
    time.sleep(30)

# 3. Get results
results_response = requests.get(
    f"{API_BASE}/evaluations/{evaluation_id}/results",
    headers=HEADERS
)

results_data = results_response.json()
results = results_data["data"]["results"]

for task, metrics in results.items():
    print(f"{task}: {metrics}")
```

### Batch Evaluation Example

```python
# Start multiple evaluations
batch_request = {
    "evaluations": [
        {
            "tasks": ["hellaswag"],
            "model": "gpt-3.5-turbo",
            "config": {"num_fewshot": 5}
        },
        {
            "tasks": ["arc_easy"],
            "model": "gpt-4",
            "config": {"num_fewshot": 10}
        }
    ],
    "batch_config": {
        "max_concurrent": 2,
        "fail_fast": False
    }
}

response = requests.post(
    f"{API_BASE}/evaluations/batch",
    json=batch_request,
    headers=HEADERS
)

batch_data = response.json()
evaluation_ids = batch_data["data"]["evaluation_ids"]

# Monitor all evaluations
for eval_id in evaluation_ids:
    print(f"Monitoring evaluation: {eval_id}")
    # Monitor logic here...
```

### Custom Task Upload Example

```python
# Upload custom task file
with open("custom_task.py", "rb") as f:
    files = {"task_file": f}
    
    response = requests.post(
        f"{API_BASE}/tasks/upload",
        files=files,
        headers={"Authorization": f"Bearer {API_KEY}"}
    )

upload_data = response.json()
print(f"Uploaded task: {upload_data['data']['task_name']}")

# Validate custom task
validation_request = {
    "task_definition": {
        "task": "custom_task",
        "dataset_path": "path/to/dataset",
        "description": "Custom task description"
    }
}

response = requests.post(
    f"{API_BASE}/tasks/validate",
    json=validation_request,
    headers=HEADERS
)

validation_data = response.json()
print(f"Task validation: {validation_data['data']['valid']}")
```

## SDK and Client Libraries

### Python SDK

```python
from evaluation_engine_client import EvaluationEngineClient

# Initialize client
client = EvaluationEngineClient(
    base_url="http://localhost:8000",
    api_key="your_api_key"
)

# Start evaluation
evaluation = client.evaluations.create(
    tasks=["hellaswag", "arc_easy"],
    model="gpt-3.5-turbo",
    config={"num_fewshot": 5}
)

# Wait for completion
evaluation.wait_for_completion()

# Get results
results = evaluation.get_results()
print(results)
```

### JavaScript SDK

```javascript
import { EvaluationEngineClient } from 'evaluation-engine-client';

const client = new EvaluationEngineClient({
    baseUrl: 'http://localhost:8000',
    apiKey: 'your_api_key'
});

// Start evaluation
const evaluation = await client.evaluations.create({
    tasks: ['hellaswag', 'arc_easy'],
    model: 'gpt-3.5-turbo',
    config: { num_fewshot: 5 }
});

// Monitor with WebSocket
evaluation.onStatusUpdate((status) => {
    console.log('Status:', status);
});

// Get results when complete
const results = await evaluation.getResults();
console.log(results);
```

### CLI Tool

```bash
# Install CLI tool
pip install evaluation-engine-cli

# Configure API key
eval-engine config set-api-key YOUR_API_KEY

# Start evaluation
eval-engine evaluate --tasks hellaswag,arc_easy --model gpt-3.5-turbo

# List evaluations
eval-engine list

# Get results
eval-engine results eval_123456789

# Monitor evaluation
eval-engine monitor eval_123456789
```

This comprehensive API specification provides all the information needed to integrate with and use the EvaluationEngineV1_0 Testing Framework API effectively.