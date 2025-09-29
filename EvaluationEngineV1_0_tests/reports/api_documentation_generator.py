"""
APIDocumentationGenerator for creating comprehensive API documentation.

This module generates API specifications, endpoint documentation, and
OpenAPI/Swagger specifications based on the testing framework's API interface.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from models.test_models import TestResult


class APIDocumentationGenerator:
    """
    Generates comprehensive API documentation for the testing framework.
    
    Creates OpenAPI specifications, endpoint documentation, and usage examples
    based on the API testing interface and successful API test results.
    """
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize the API documentation generator.
        
        Args:
            output_dir: Directory to save generated documentation
        """
        self.output_dir = output_dir or Path("docs/api")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def generate_openapi_specification(self, api_test_results: List[TestResult] = None) -> Dict[str, Any]:
        """
        Generate OpenAPI 3.0 specification for the testing framework API.
        
        Args:
            api_test_results: Optional API test results to enhance documentation
            
        Returns:
            OpenAPI specification as dictionary
        """
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "EvaluationEngineV1_0 Testing Framework API",
                "description": "REST API for testing and validating EvaluationEngineV1_0 functionality",
                "version": "1.0.0",
                "contact": {
                    "name": "EvaluationEngineV1_0 Testing Framework",
                    "url": "https://github.com/your-repo/EvaluationEngineV1_0"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8080",
                    "description": "Local development server"
                },
                {
                    "url": "https://api.evaluation-engine.example.com",
                    "description": "Production server"
                }
            ],
            "paths": self._generate_api_paths(),
            "components": self._generate_api_components(),
            "tags": [
                {
                    "name": "evaluations",
                    "description": "Evaluation management operations"
                },
                {
                    "name": "tasks",
                    "description": "Task discovery and management"
                },
                {
                    "name": "adapters",
                    "description": "Adapter validation operations"
                },
                {
                    "name": "system",
                    "description": "System health and status"
                }
            ]
        }
        
        self.logger.info("Generated OpenAPI specification")
        return spec
        
    def generate_endpoint_documentation(self, api_test_results: List[TestResult] = None) -> str:
        """
        Generate detailed endpoint documentation.
        
        Args:
            api_test_results: Optional API test results for examples
            
        Returns:
            Endpoint documentation as markdown string
        """
        content = f"""# API Endpoint Documentation

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Overview

The EvaluationEngineV1_0 Testing Framework provides a REST API for programmatic access to testing functionality. This API allows you to start evaluations, check status, retrieve results, and manage testing configurations.

## Base URL

```
http://localhost:8080/api/v1
```

## Authentication

Currently, the API does not require authentication for local testing. In production environments, implement appropriate authentication mechanisms.

## Content Type

All API requests and responses use JSON format:

```
Content-Type: application/json
```

## Endpoints

### Evaluations

#### Start Evaluation

**POST** `/evaluations`

Start a new evaluation with specified configuration.

**Request Body:**
```json
{{
  "tasks": ["hellaswag", "arc_easy"],
  "model": "gpt-3.5-turbo",
  "config": {{
    "num_fewshot": 5,
    "batch_size": 1,
    "limit": 100
  }},
  "adapters": ["lm_eval_adapter"],
  "real_execution": true
}}
```

**Response:**
```json
{{
  "evaluation_id": "eval_123456789",
  "status": "started",
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_duration": 300
}}
```

**Status Codes:**
- `201 Created` - Evaluation started successfully
- `400 Bad Request` - Invalid request parameters
- `500 Internal Server Error` - Server error

#### Get Evaluation Status

**GET** `/evaluations/{{evaluation_id}}/status`

Check the status of a running evaluation.

**Response:**
```json
{{
  "evaluation_id": "eval_123456789",
  "status": "running",
  "progress": {{
    "completed_tasks": 1,
    "total_tasks": 2,
    "percentage": 50
  }},
  "started_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T10:35:00Z"
}}
```

**Status Values:**
- `started` - Evaluation has been queued
- `running` - Evaluation is currently executing
- `completed` - Evaluation finished successfully
- `failed` - Evaluation failed with errors
- `cancelled` - Evaluation was cancelled

#### Get Evaluation Results

**GET** `/evaluations/{{evaluation_id}}/results`

Retrieve results from a completed evaluation.

**Response:**
```json
{{
  "evaluation_id": "eval_123456789",
  "status": "completed",
  "results": {{
    "hellaswag": {{
      "accuracy": 0.85,
      "num_samples": 100,
      "execution_time": 120.5
    }},
    "arc_easy": {{
      "accuracy": 0.92,
      "num_samples": 100,
      "execution_time": 95.2
    }}
  }},
  "summary": {{
    "total_execution_time": 215.7,
    "average_accuracy": 0.885,
    "real_execution_validated": true
  }},
  "completed_at": "2024-01-15T10:33:37Z"
}}
```

#### List Evaluations

**GET** `/evaluations`

List all evaluations with optional filtering.

**Query Parameters:**
- `status` - Filter by status (optional)
- `limit` - Maximum number of results (default: 50)
- `offset` - Pagination offset (default: 0)

**Response:**
```json
{{
  "evaluations": [
    {{
      "evaluation_id": "eval_123456789",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:33:37Z"
    }}
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}}
```

#### Cancel Evaluation

**DELETE** `/evaluations/{{evaluation_id}}`

Cancel a running evaluation.

**Response:**
```json
{{
  "evaluation_id": "eval_123456789",
  "status": "cancelled",
  "cancelled_at": "2024-01-15T10:32:00Z"
}}
```

### Tasks

#### List Available Tasks

**GET** `/tasks`

Get list of available tasks for evaluation.

**Query Parameters:**
- `type` - Filter by task type (builtin, custom)
- `adapter` - Filter by adapter compatibility

**Response:**
```json
{{
  "tasks": [
    {{
      "name": "hellaswag",
      "type": "builtin",
      "description": "Common sense reasoning task",
      "adapters": ["lm_eval_adapter"],
      "metrics": ["accuracy"]
    }},
    {{
      "name": "arc_easy",
      "type": "builtin", 
      "description": "Science questions (easy)",
      "adapters": ["lm_eval_adapter"],
      "metrics": ["accuracy"]
    }}
  ],
  "total": 2
}}
```

#### Get Task Details

**GET** `/tasks/{{task_name}}`

Get detailed information about a specific task.

**Response:**
```json
{{
  "name": "hellaswag",
  "type": "builtin",
  "description": "Common sense reasoning task",
  "version": "1.0",
  "adapters": ["lm_eval_adapter"],
  "metrics": ["accuracy"],
  "config_options": {{
    "num_fewshot": {{
      "type": "integer",
      "default": 10,
      "description": "Number of few-shot examples"
    }},
    "limit": {{
      "type": "integer", 
      "default": null,
      "description": "Limit number of samples"
    }}
  }},
  "sample_count": 10042
}}
```

### Adapters

#### List Available Adapters

**GET** `/adapters`

Get list of available adapters for validation.

**Response:**
```json
{{
  "adapters": [
    {{
      "name": "lm_eval_adapter",
      "description": "Integration with lm-evaluation-harness",
      "status": "available",
      "supported_tasks": ["hellaswag", "arc_easy", "mmlu"],
      "dependencies": ["lm_eval"]
    }},
    {{
      "name": "swe_bench_adapter",
      "description": "Software engineering task adapter",
      "status": "available", 
      "supported_tasks": ["swe_bench"],
      "dependencies": ["swe_bench"]
    }}
  ],
  "total": 2
}}
```

#### Validate Adapter

**POST** `/adapters/{{adapter_name}}/validate`

Validate an adapter's integration and functionality.

**Request Body:**
```json
{{
  "install_dependencies": true,
  "test_task_count": 1,
  "performance_benchmark": false
}}
```

**Response:**
```json
{{
  "adapter_name": "lm_eval_adapter",
  "validation_id": "validation_123456",
  "status": "started",
  "started_at": "2024-01-15T10:40:00Z"
}}
```

#### Get Adapter Validation Results

**GET** `/adapters/{{adapter_name}}/validate/{{validation_id}}`

Get results from adapter validation.

**Response:**
```json
{{
  "validation_id": "validation_123456",
  "adapter_name": "lm_eval_adapter",
  "status": "completed",
  "integration_status": "success",
  "dependencies_installed": true,
  "test_results": [
    {{
      "task": "hellaswag",
      "status": "passed",
      "execution_time": 45.2,
      "metrics": {{"accuracy": 0.85}}
    }}
  ],
  "performance_metrics": {{
    "avg_execution_time": 45.2,
    "memory_usage": 512.5
  }},
  "issues_found": [],
  "completed_at": "2024-01-15T10:41:30Z"
}}
```

### System

#### Health Check

**GET** `/health`

Check API server health and status.

**Response:**
```json
{{
  "status": "healthy",
  "timestamp": "2024-01-15T10:45:00Z",
  "version": "1.0.0",
  "uptime": 3600,
  "dependencies": {{
    "database": "connected",
    "evaluation_engine": "available"
  }}
}}
```

#### System Information

**GET** `/info`

Get system information and capabilities.

**Response:**
```json
{{
  "version": "1.0.0",
  "api_version": "v1",
  "supported_formats": ["json"],
  "max_concurrent_evaluations": 5,
  "available_adapters": ["lm_eval_adapter", "swe_bench_adapter"],
  "available_tasks": 150,
  "system_resources": {{
    "cpu_cores": 8,
    "memory_gb": 32,
    "disk_space_gb": 500
  }}
}}
```

## Error Handling

The API uses standard HTTP status codes and returns error details in JSON format:

```json
{{
  "error": {{
    "code": "VALIDATION_ERROR",
    "message": "Invalid task name provided",
    "details": {{
      "field": "tasks",
      "value": "invalid_task",
      "allowed_values": ["hellaswag", "arc_easy"]
    }}
  }},
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}}
```

### Common Error Codes

- `VALIDATION_ERROR` - Request validation failed
- `NOT_FOUND` - Requested resource not found
- `EXECUTION_ERROR` - Error during evaluation execution
- `DEPENDENCY_ERROR` - Missing or invalid dependencies
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Internal server error

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Evaluation requests**: 10 per minute per client
- **Status checks**: 60 per minute per client
- **General requests**: 100 per minute per client

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1642248600
```

## Pagination

List endpoints support pagination using `limit` and `offset` parameters:

```
GET /evaluations?limit=20&offset=40
```

Response includes pagination metadata:

```json
{{
  "data": [...],
  "pagination": {{
    "limit": 20,
    "offset": 40,
    "total": 150,
    "has_next": true,
    "has_previous": true
  }}
}}
```

## WebSocket Support

For real-time updates on evaluation progress, the API supports WebSocket connections:

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/evaluations/eval_123456789');

ws.onmessage = function(event) {{
  const update = JSON.parse(event.data);
  console.log('Progress update:', update);
}};
```

## SDK Examples

### Python SDK

```python
import requests

class EvaluationAPI:
    def __init__(self, base_url="http://localhost:8080/api/v1"):
        self.base_url = base_url
    
    def start_evaluation(self, config):
        response = requests.post(f"{{self.base_url}}/evaluations", json=config)
        return response.json()
    
    def get_status(self, evaluation_id):
        response = requests.get(f"{{self.base_url}}/evaluations/{{evaluation_id}}/status")
        return response.json()
    
    def get_results(self, evaluation_id):
        response = requests.get(f"{{self.base_url}}/evaluations/{{evaluation_id}}/results")
        return response.json()

# Usage
api = EvaluationAPI()
result = api.start_evaluation({{
    "tasks": ["hellaswag"],
    "model": "gpt-3.5-turbo"
}})
print(f"Started evaluation: {{result['evaluation_id']}}")
```

### JavaScript SDK

```javascript
class EvaluationAPI {{
    constructor(baseUrl = 'http://localhost:8080/api/v1') {{
        this.baseUrl = baseUrl;
    }}
    
    async startEvaluation(config) {{
        const response = await fetch(`${{this.baseUrl}}/evaluations`, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(config)
        }});
        return response.json();
    }}
    
    async getStatus(evaluationId) {{
        const response = await fetch(`${{this.baseUrl}}/evaluations/${{evaluationId}}/status`);
        return response.json();
    }}
    
    async getResults(evaluationId) {{
        const response = await fetch(`${{this.baseUrl}}/evaluations/${{evaluationId}}/results`);
        return response.json();
    }}
}}

// Usage
const api = new EvaluationAPI();
const result = await api.startEvaluation({{
    tasks: ['hellaswag'],
    model: 'gpt-3.5-turbo'
}});
console.log(`Started evaluation: ${{result.evaluation_id}}`);
```

## Testing the API

### Using curl

```bash
# Start evaluation
curl -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{"tasks": ["hellaswag"], "model": "gpt-3.5-turbo"}}'

# Check status
curl http://localhost:8080/api/v1/evaluations/eval_123456789/status

# Get results
curl http://localhost:8080/api/v1/evaluations/eval_123456789/results
```

### Using Postman

Import the OpenAPI specification into Postman for interactive testing:

1. Open Postman
2. Click "Import"
3. Select "Link" and enter: `http://localhost:8080/api/v1/openapi.json`
4. Postman will create a collection with all endpoints

## Changelog

### Version 1.0.0
- Initial API release
- Basic evaluation management
- Task and adapter discovery
- Real-time status updates

---

*This documentation was automatically generated by the EvaluationEngineV1_0 testing framework.*
"""
        
        self.logger.info("Generated endpoint documentation")
        return content
        
    def generate_curl_examples(self, api_test_results: List[TestResult] = None) -> str:
        """
        Generate curl command examples for API testing.
        
        Args:
            api_test_results: Optional API test results for realistic examples
            
        Returns:
            Curl examples as markdown string
        """
        content = f"""# API Testing with curl

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

This document provides curl command examples for testing the EvaluationEngineV1_0 Testing Framework API.

## Prerequisites

1. API server running on `http://localhost:8080`
2. curl installed on your system
3. jq (optional, for JSON formatting)

## Basic Examples

### Start an Evaluation

```bash
# Start a simple evaluation
curl -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{
    "tasks": ["hellaswag"],
    "model": "gpt-3.5-turbo",
    "config": {{
      "num_fewshot": 5,
      "limit": 10
    }}
  }}'
```

### Check Evaluation Status

```bash
# Replace eval_123456789 with actual evaluation ID
curl http://localhost:8080/api/v1/evaluations/eval_123456789/status | jq
```

### Get Evaluation Results

```bash
# Get results (only works for completed evaluations)
curl http://localhost:8080/api/v1/evaluations/eval_123456789/results | jq
```

## Advanced Examples

### Multiple Tasks Evaluation

```bash
curl -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{
    "tasks": ["hellaswag", "arc_easy", "mmlu"],
    "model": "gpt-4",
    "config": {{
      "num_fewshot": 10,
      "batch_size": 1,
      "limit": 100
    }},
    "adapters": ["lm_eval_adapter"],
    "real_execution": true
  }}'
```

### Custom Task Evaluation

```bash
curl -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{
    "tasks": ["custom_task_1"],
    "model": "gpt-3.5-turbo",
    "config": {{
      "task_dir": "./custom_tasks",
      "num_fewshot": 0
    }},
    "adapters": ["lm_eval_adapter"]
  }}'
```

### SWE-bench Evaluation

```bash
curl -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{
    "tasks": ["swe_bench_lite"],
    "model": "gpt-4",
    "config": {{
      "limit": 5,
      "timeout": 600
    }},
    "adapters": ["swe_bench_adapter"]
  }}'
```

## Task Management

### List Available Tasks

```bash
# List all tasks
curl http://localhost:8080/api/v1/tasks | jq

# Filter by type
curl "http://localhost:8080/api/v1/tasks?type=builtin" | jq

# Filter by adapter
curl "http://localhost:8080/api/v1/tasks?adapter=lm_eval_adapter" | jq
```

### Get Task Details

```bash
curl http://localhost:8080/api/v1/tasks/hellaswag | jq
```

## Adapter Management

### List Available Adapters

```bash
curl http://localhost:8080/api/v1/adapters | jq
```

### Validate Adapter

```bash
# Start adapter validation
curl -X POST http://localhost:8080/api/v1/adapters/lm_eval_adapter/validate \\
  -H "Content-Type: application/json" \\
  -d '{{
    "install_dependencies": true,
    "test_task_count": 2,
    "performance_benchmark": true
  }}'

# Check validation status (replace validation_123456 with actual ID)
curl http://localhost:8080/api/v1/adapters/lm_eval_adapter/validate/validation_123456 | jq
```

## System Information

### Health Check

```bash
curl http://localhost:8080/api/v1/health | jq
```

### System Information

```bash
curl http://localhost:8080/api/v1/info | jq
```

## Evaluation Management

### List All Evaluations

```bash
# List all evaluations
curl http://localhost:8080/api/v1/evaluations | jq

# Filter by status
curl "http://localhost:8080/api/v1/evaluations?status=completed" | jq

# Pagination
curl "http://localhost:8080/api/v1/evaluations?limit=10&offset=20" | jq
```

### Cancel Evaluation

```bash
curl -X DELETE http://localhost:8080/api/v1/evaluations/eval_123456789 | jq
```

## Error Handling Examples

### Invalid Task Name

```bash
curl -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{
    "tasks": ["invalid_task"],
    "model": "gpt-3.5-turbo"
  }}' | jq
```

### Missing Required Fields

```bash
curl -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{
    "model": "gpt-3.5-turbo"
  }}' | jq
```

## Batch Testing Script

```bash
#!/bin/bash

# batch_test.sh - Test multiple configurations

BASE_URL="http://localhost:8080/api/v1"

# Array of test configurations
declare -a configs=(
  '{{"tasks": ["hellaswag"], "model": "gpt-3.5-turbo", "config": {{"limit": 5}}}}'
  '{{"tasks": ["arc_easy"], "model": "gpt-3.5-turbo", "config": {{"limit": 5}}}}'
  '{{"tasks": ["mmlu"], "model": "gpt-4", "config": {{"limit": 3}}}}'
)

# Run tests
for config in "${{configs[@]}}"; do
  echo "Starting evaluation with config: $config"
  
  # Start evaluation
  response=$(curl -s -X POST "$BASE_URL/evaluations" \\
    -H "Content-Type: application/json" \\
    -d "$config")
  
  eval_id=$(echo "$response" | jq -r '.evaluation_id')
  echo "Started evaluation: $eval_id"
  
  # Wait for completion
  while true; do
    status=$(curl -s "$BASE_URL/evaluations/$eval_id/status" | jq -r '.status')
    echo "Status: $status"
    
    if [[ "$status" == "completed" || "$status" == "failed" ]]; then
      break
    fi
    
    sleep 10
  done
  
  # Get results
  if [[ "$status" == "completed" ]]; then
    echo "Getting results..."
    curl -s "$BASE_URL/evaluations/$eval_id/results" | jq
  fi
  
  echo "---"
done
```

## Performance Testing

### Load Testing with curl

```bash
#!/bin/bash

# load_test.sh - Simple load testing

BASE_URL="http://localhost:8080/api/v1"
CONCURRENT_REQUESTS=5

# Function to start evaluation
start_evaluation() {{
  curl -s -X POST "$BASE_URL/evaluations" \\
    -H "Content-Type: application/json" \\
    -d '{{"tasks": ["hellaswag"], "model": "gpt-3.5-turbo", "config": {{"limit": 1}}}}'
}}

# Start multiple evaluations concurrently
for i in $(seq 1 $CONCURRENT_REQUESTS); do
  start_evaluation &
done

# Wait for all background jobs to complete
wait

echo "Load test completed"
```

## Monitoring and Debugging

### Monitor Evaluation Progress

```bash
#!/bin/bash

# monitor.sh - Monitor evaluation progress

EVAL_ID=$1

if [[ -z "$EVAL_ID" ]]; then
  echo "Usage: $0 <evaluation_id>"
  exit 1
fi

BASE_URL="http://localhost:8080/api/v1"

while true; do
  response=$(curl -s "$BASE_URL/evaluations/$EVAL_ID/status")
  status=$(echo "$response" | jq -r '.status')
  progress=$(echo "$response" | jq -r '.progress.percentage // 0')
  
  echo "$(date): Status=$status, Progress=$progress%"
  
  if [[ "$status" == "completed" || "$status" == "failed" ]]; then
    break
  fi
  
  sleep 5
done

echo "Evaluation finished with status: $status"
```

### Debug API Responses

```bash
# Enable verbose output for debugging
curl -v -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{"tasks": ["hellaswag"], "model": "gpt-3.5-turbo"}}'

# Save response headers and body
curl -D headers.txt -o response.json \\
  -X POST http://localhost:8080/api/v1/evaluations \\
  -H "Content-Type: application/json" \\
  -d '{{"tasks": ["hellaswag"], "model": "gpt-3.5-turbo"}}'
```

---

*This documentation was automatically generated by the EvaluationEngineV1_0 testing framework.*
"""
        
        self.logger.info("Generated curl examples documentation")
        return content
        
    def save_openapi_specification(self, spec: Dict[str, Any], filename: str = "openapi.json") -> Path:
        """
        Save OpenAPI specification to file.
        
        Args:
            spec: OpenAPI specification dictionary
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(spec, f, indent=2)
        
        self.logger.info(f"Saved OpenAPI specification to {filepath}")
        return filepath
        
    def save_endpoint_documentation(self, content: str, filename: str = "api_endpoints.md") -> Path:
        """
        Save endpoint documentation to file.
        
        Args:
            content: Documentation content
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(content)
        
        self.logger.info(f"Saved endpoint documentation to {filepath}")
        return filepath
        
    def save_curl_examples(self, content: str, filename: str = "curl_examples.md") -> Path:
        """
        Save curl examples to file.
        
        Args:
            content: Curl examples content
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(content)
        
        self.logger.info(f"Saved curl examples to {filepath}")
        return filepath
        
    def _generate_api_paths(self) -> Dict[str, Any]:
        """Generate OpenAPI paths specification."""
        return {
            "/evaluations": {
                "post": {
                    "tags": ["evaluations"],
                    "summary": "Start a new evaluation",
                    "description": "Start a new evaluation with specified tasks and configuration",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/EvaluationRequest"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Evaluation started successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EvaluationResponse"}
                                }
                            }
                        },
                        "400": {
                            "description": "Invalid request parameters",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            }
                        }
                    }
                },
                "get": {
                    "tags": ["evaluations"],
                    "summary": "List evaluations",
                    "description": "Get list of evaluations with optional filtering",
                    "parameters": [
                        {
                            "name": "status",
                            "in": "query",
                            "description": "Filter by evaluation status",
                            "schema": {"type": "string", "enum": ["started", "running", "completed", "failed", "cancelled"]}
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "description": "Maximum number of results",
                            "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 100}
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "description": "Pagination offset",
                            "schema": {"type": "integer", "default": 0, "minimum": 0}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List of evaluations",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EvaluationListResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/evaluations/{evaluation_id}/status": {
                "get": {
                    "tags": ["evaluations"],
                    "summary": "Get evaluation status",
                    "description": "Check the status of a running evaluation",
                    "parameters": [
                        {
                            "name": "evaluation_id",
                            "in": "path",
                            "required": True,
                            "description": "Evaluation ID",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Evaluation status",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EvaluationStatusResponse"}
                                }
                            }
                        },
                        "404": {
                            "description": "Evaluation not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/evaluations/{evaluation_id}/results": {
                "get": {
                    "tags": ["evaluations"],
                    "summary": "Get evaluation results",
                    "description": "Retrieve results from a completed evaluation",
                    "parameters": [
                        {
                            "name": "evaluation_id",
                            "in": "path",
                            "required": True,
                            "description": "Evaluation ID",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Evaluation results",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EvaluationResultsResponse"}
                                }
                            }
                        },
                        "404": {
                            "description": "Evaluation not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/tasks": {
                "get": {
                    "tags": ["tasks"],
                    "summary": "List available tasks",
                    "description": "Get list of available tasks for evaluation",
                    "parameters": [
                        {
                            "name": "type",
                            "in": "query",
                            "description": "Filter by task type",
                            "schema": {"type": "string", "enum": ["builtin", "custom"]}
                        },
                        {
                            "name": "adapter",
                            "in": "query",
                            "description": "Filter by adapter compatibility",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List of available tasks",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TaskListResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/adapters": {
                "get": {
                    "tags": ["adapters"],
                    "summary": "List available adapters",
                    "description": "Get list of available adapters for validation",
                    "responses": {
                        "200": {
                            "description": "List of available adapters",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/AdapterListResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/health": {
                "get": {
                    "tags": ["system"],
                    "summary": "Health check",
                    "description": "Check API server health and status",
                    "responses": {
                        "200": {
                            "description": "Server is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HealthResponse"}
                                }
                            }
                        }
                    }
                }
            }
        }
        
    def _generate_api_components(self) -> Dict[str, Any]:
        """Generate OpenAPI components specification."""
        return {
            "schemas": {
                "EvaluationRequest": {
                    "type": "object",
                    "required": ["tasks", "model"],
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of tasks to evaluate"
                        },
                        "model": {
                            "type": "string",
                            "description": "Model to use for evaluation"
                        },
                        "config": {
                            "type": "object",
                            "description": "Evaluation configuration parameters"
                        },
                        "adapters": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of adapters to use"
                        },
                        "real_execution": {
                            "type": "boolean",
                            "default": True,
                            "description": "Ensure real execution validation"
                        }
                    }
                },
                "EvaluationResponse": {
                    "type": "object",
                    "properties": {
                        "evaluation_id": {"type": "string"},
                        "status": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "estimated_duration": {"type": "number"}
                    }
                },
                "EvaluationStatusResponse": {
                    "type": "object",
                    "properties": {
                        "evaluation_id": {"type": "string"},
                        "status": {"type": "string"},
                        "progress": {
                            "type": "object",
                            "properties": {
                                "completed_tasks": {"type": "integer"},
                                "total_tasks": {"type": "integer"},
                                "percentage": {"type": "number"}
                            }
                        },
                        "started_at": {"type": "string", "format": "date-time"},
                        "estimated_completion": {"type": "string", "format": "date-time"}
                    }
                },
                "EvaluationResultsResponse": {
                    "type": "object",
                    "properties": {
                        "evaluation_id": {"type": "string"},
                        "status": {"type": "string"},
                        "results": {"type": "object"},
                        "summary": {"type": "object"},
                        "completed_at": {"type": "string", "format": "date-time"}
                    }
                },
                "TaskListResponse": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Task"}
                        },
                        "total": {"type": "integer"}
                    }
                },
                "Task": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "description": {"type": "string"},
                        "adapters": {"type": "array", "items": {"type": "string"}},
                        "metrics": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "AdapterListResponse": {
                    "type": "object",
                    "properties": {
                        "adapters": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Adapter"}
                        },
                        "total": {"type": "integer"}
                    }
                },
                "Adapter": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string"},
                        "supported_tasks": {"type": "array", "items": {"type": "string"}},
                        "dependencies": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "HealthResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "version": {"type": "string"},
                        "uptime": {"type": "number"}
                    }
                },
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                                "details": {"type": "object"}
                            }
                        },
                        "timestamp": {"type": "string", "format": "date-time"},
                        "request_id": {"type": "string"}
                    }
                }
            }
        }