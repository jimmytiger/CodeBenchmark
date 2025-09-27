# AI Evaluation Engine API Documentation

## Overview

The AI Evaluation Engine provides a comprehensive REST API for evaluating language models across diverse programming and problem-solving scenarios. The API supports both single-turn and multi-turn evaluations with advanced metrics, secure code execution, and real-time monitoring.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All API endpoints require authentication using JWT tokens:

```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/v1/evaluations
```

## Core Endpoints

### Evaluation Management

#### Create Evaluation

**POST** `/evaluations`

Create a new evaluation job for one or more models and tasks.

**Request Body:**
```json
{
  "model_configs": [
    {
      "model_id": "openai/gpt-4",
      "model_type": "openai",
      "config": {
        "temperature": 0.7,
        "max_tokens": 2048,
        "api_key": "your-api-key"
      }
    }
  ],
  "task_configs": [
    {
      "task_id": "single_turn_scenarios_code_completion",
      "context_mode": "full_context",
      "num_samples": 100
    }
  ],
  "evaluation_config": {
    "timeout": 3600,
    "parallel_workers": 4,
    "enable_sandbox": true
  }
}
```

**Response:**
```json
{
  "evaluation_id": "eval_123456",
  "status": "queued",
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_duration": 1800
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_configs": [{
      "model_id": "openai/gpt-4",
      "model_type": "openai",
      "config": {"temperature": 0.7}
    }],
    "task_configs": [{
      "task_id": "single_turn_scenarios_code_completion",
      "context_mode": "full_context"
    }]
  }'
```

#### Get Evaluation Status

**GET** `/evaluations/{evaluation_id}`

Retrieve the current status and results of an evaluation.

**Response:**
```json
{
  "evaluation_id": "eval_123456",
  "status": "running",
  "progress": 0.65,
  "started_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T11:00:00Z",
  "task_results": [
    {
      "task_id": "single_turn_scenarios_code_completion",
      "status": "completed",
      "metrics": {
        "pass_at_1": 0.85,
        "pass_at_5": 0.92,
        "syntax_validity": 0.98,
        "code_quality_score": 0.78
      }
    }
  ]
}
```

#### List Evaluations

**GET** `/evaluations`

List all evaluations with optional filtering.

**Query Parameters:**
- `status`: Filter by status (queued, running, completed, failed)
- `model_id`: Filter by model ID
- `task_id`: Filter by task ID
- `limit`: Number of results (default: 50)
- `offset`: Pagination offset (default: 0)

**Example:**
```bash
curl "http://localhost:8000/api/v1/evaluations?status=completed&limit=10" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

#### Cancel Evaluation

**DELETE** `/evaluations/{evaluation_id}`

Cancel a running evaluation.

**Response:**
```json
{
  "evaluation_id": "eval_123456",
  "status": "cancelled",
  "cancelled_at": "2024-01-15T10:45:00Z"
}
```

### Task Management

#### List Available Tasks

**GET** `/tasks`

Retrieve all available evaluation tasks.

**Response:**
```json
{
  "single_turn_scenarios": [
    {
      "task_id": "single_turn_scenarios_code_completion",
      "name": "Code Completion",
      "description": "Complete partial function implementations",
      "languages": ["python", "javascript", "java", "cpp"],
      "metrics": ["pass_at_k", "syntax_validity", "code_quality"]
    }
  ],
  "multi_turn_scenarios": [
    {
      "task_id": "multi_turn_scenarios_code_review",
      "name": "Code Review Process",
      "description": "Interactive code review and improvement",
      "max_turns": 5,
      "metrics": ["review_thoroughness", "improvement_quality"]
    }
  ]
}
```

#### Get Task Details

**GET** `/tasks/{task_id}`

Get detailed information about a specific task.

**Response:**
```json
{
  "task_id": "single_turn_scenarios_code_completion",
  "name": "Code Completion",
  "description": "Complete partial function implementations",
  "task_type": "single_turn",
  "languages": ["python", "javascript", "java"],
  "dataset_size": 500,
  "metrics": [
    {
      "name": "pass_at_k",
      "description": "Percentage of problems solved in k attempts"
    }
  ],
  "context_modes": ["no_context", "minimal_context", "full_context"],
  "sample_problem": {
    "prompt": "Complete the following function...",
    "expected_output": "def fibonacci(n): ..."
  }
}
```

### Model Management

#### List Supported Models

**GET** `/models`

Get all supported model types and configurations.

**Response:**
```json
{
  "openai": {
    "models": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
    "config_schema": {
      "temperature": {"type": "float", "range": [0, 2]},
      "max_tokens": {"type": "integer", "range": [1, 4096]}
    }
  },
  "anthropic": {
    "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
    "config_schema": {
      "temperature": {"type": "float", "range": [0, 1]},
      "max_tokens": {"type": "integer", "range": [1, 4096]}
    }
  }
}
```

#### Validate Model Configuration

**POST** `/models/validate`

Validate a model configuration before creating an evaluation.

**Request Body:**
```json
{
  "model_id": "openai/gpt-4",
  "model_type": "openai",
  "config": {
    "temperature": 0.7,
    "max_tokens": 2048
  }
}
```

**Response:**
```json
{
  "valid": true,
  "estimated_cost": 0.15,
  "rate_limits": {
    "requests_per_minute": 60,
    "tokens_per_minute": 90000
  }
}
```

### Results and Analytics

#### Get Evaluation Results

**GET** `/evaluations/{evaluation_id}/results`

Get detailed results for a completed evaluation.

**Response:**
```json
{
  "evaluation_id": "eval_123456",
  "model_results": [
    {
      "model_id": "openai/gpt-4",
      "overall_score": 0.82,
      "task_results": [
        {
          "task_id": "single_turn_scenarios_code_completion",
          "metrics": {
            "pass_at_1": 0.85,
            "pass_at_5": 0.92,
            "syntax_validity": 0.98,
            "code_quality_score": 0.78,
            "execution_time_avg": 2.3
          },
          "sample_outputs": [
            {
              "problem_id": "prob_001",
              "input": "def fibonacci(n):",
              "output": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
              "correct": true,
              "execution_result": "passed"
            }
          ]
        }
      ]
    }
  ]
}
```

#### Compare Models

**POST** `/analytics/compare`

Compare performance across multiple models and tasks.

**Request Body:**
```json
{
  "evaluation_ids": ["eval_123456", "eval_789012"],
  "comparison_metrics": ["pass_at_1", "code_quality_score"],
  "statistical_tests": true
}
```

**Response:**
```json
{
  "comparison_results": {
    "models": ["openai/gpt-4", "anthropic/claude-3-opus"],
    "metrics_comparison": {
      "pass_at_1": {
        "gpt-4": 0.85,
        "claude-3-opus": 0.82,
        "statistical_significance": 0.03
      }
    },
    "recommendations": [
      "GPT-4 shows significantly better performance on code completion tasks"
    ]
  }
}
```

#### Export Results

**GET** `/evaluations/{evaluation_id}/export`

Export evaluation results in various formats.

**Query Parameters:**
- `format`: Export format (json, csv, pdf, html)
- `include_samples`: Include sample outputs (default: false)

**Example:**
```bash
curl "http://localhost:8000/api/v1/evaluations/eval_123456/export?format=pdf" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -o evaluation_report.pdf
```

## WebSocket API

### Real-time Updates

Connect to WebSocket for real-time evaluation updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/evaluations/eval_123456');

ws.onmessage = function(event) {
  const update = JSON.parse(event.data);
  console.log('Progress:', update.progress);
  console.log('Current task:', update.current_task);
};
```

**Message Types:**
- `progress_update`: Evaluation progress information
- `task_completed`: Individual task completion
- `evaluation_completed`: Full evaluation completion
- `error`: Error notifications

## Error Handling

All API endpoints return standard HTTP status codes:

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

**Error Response Format:**
```json
{
  "error": {
    "code": "INVALID_MODEL_CONFIG",
    "message": "Temperature must be between 0 and 2",
    "details": {
      "field": "temperature",
      "value": 3.0,
      "allowed_range": [0, 2]
    }
  }
}
```

## Rate Limits

API endpoints are rate-limited to ensure fair usage:

- Authentication: 10 requests/minute
- Evaluation creation: 5 requests/minute
- Status checks: 100 requests/minute
- Results retrieval: 50 requests/minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
```

## SDK Examples

### Python SDK

```python
from evaluation_engine import EvaluationClient

client = EvaluationClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Create evaluation
evaluation = client.create_evaluation(
    models=[{
        "model_id": "openai/gpt-4",
        "model_type": "openai",
        "config": {"temperature": 0.7}
    }],
    tasks=["single_turn_scenarios_code_completion"]
)

# Monitor progress
for update in client.stream_progress(evaluation.id):
    print(f"Progress: {update.progress:.1%}")

# Get results
results = client.get_results(evaluation.id)
print(f"Overall score: {results.overall_score}")
```

### JavaScript SDK

```javascript
import { EvaluationClient } from '@evaluation-engine/client';

const client = new EvaluationClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

// Create evaluation
const evaluation = await client.createEvaluation({
  models: [{
    modelId: 'openai/gpt-4',
    modelType: 'openai',
    config: { temperature: 0.7 }
  }],
  tasks: ['single_turn_scenarios_code_completion']
});

// Get results
const results = await client.getResults(evaluation.id);
console.log('Overall score:', results.overallScore);
```

## Interactive Examples

### Complete Code Completion Evaluation

This example demonstrates a complete workflow for evaluating code completion:

```bash
# 1. Create evaluation
EVAL_ID=$(curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_configs": [{
      "model_id": "openai/gpt-4",
      "model_type": "openai",
      "config": {"temperature": 0.7, "max_tokens": 1024}
    }],
    "task_configs": [{
      "task_id": "single_turn_scenarios_code_completion",
      "context_mode": "full_context",
      "num_samples": 50
    }]
  }' | jq -r '.evaluation_id')

# 2. Monitor progress
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/v1/evaluations/$EVAL_ID" \
    -H "Authorization: Bearer $JWT_TOKEN" | jq -r '.status')
  
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  
  PROGRESS=$(curl -s "http://localhost:8000/api/v1/evaluations/$EVAL_ID" \
    -H "Authorization: Bearer $JWT_TOKEN" | jq -r '.progress')
  
  echo "Progress: $(echo "$PROGRESS * 100" | bc)%"
  sleep 10
done

# 3. Get results
curl "http://localhost:8000/api/v1/evaluations/$EVAL_ID/results" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.model_results[0].task_results[0].metrics'
```

### Multi-Turn Conversation Evaluation

```bash
# Evaluate multi-turn code review process
curl -X POST http://localhost:8000/api/v1/evaluations \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_configs": [{
      "model_id": "anthropic/claude-3-opus",
      "model_type": "anthropic",
      "config": {"temperature": 0.5}
    }],
    "task_configs": [{
      "task_id": "multi_turn_scenarios_code_review",
      "context_mode": "full_context",
      "max_turns": 5,
      "num_scenarios": 20
    }]
  }'
```

## Best Practices

### Performance Optimization

1. **Batch Evaluations**: Group multiple tasks in a single evaluation request
2. **Parallel Processing**: Use multiple workers for faster evaluation
3. **Caching**: Enable result caching for repeated evaluations
4. **Resource Limits**: Set appropriate timeouts and resource limits

### Security Considerations

1. **API Keys**: Store API keys securely and rotate regularly
2. **Rate Limiting**: Respect rate limits to avoid service disruption
3. **Input Validation**: Validate all inputs before sending requests
4. **Secure Connections**: Always use HTTPS in production

### Error Handling

1. **Retry Logic**: Implement exponential backoff for transient errors
2. **Timeout Handling**: Set appropriate timeouts for long-running evaluations
3. **Graceful Degradation**: Handle partial failures gracefully
4. **Logging**: Log all API interactions for debugging

## Support and Resources

- **Documentation**: [https://docs.evaluation-engine.ai](https://docs.evaluation-engine.ai)
- **GitHub**: [https://github.com/evaluation-engine/api](https://github.com/evaluation-engine/api)
- **Support**: support@evaluation-engine.ai
- **Status Page**: [https://status.evaluation-engine.ai](https://status.evaluation-engine.ai)