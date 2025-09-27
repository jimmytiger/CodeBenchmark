# AI Code Evaluation Framework

## Project Structure

```
Benchmark/
├── 📋 Core Files
│   ├── README.md                           # This guide
│   ├── LICENSE.md                          # Project license
│   ├── install.sh                          # Linux/macOS installation
│   ├── install.ps1                         # Windows installation
│   ├── setupEvaluationEnvironment.sh       # Linux/macOS environment setup
│   └── setupEvaluationEnvironment.ps1      # Windows environment setup
│
├── Core Components
│   ├── lm_eval/                            # lm-evaluation-harness framework
│   │   ├── tasks/                          # Task definitions
│   │   │   ├── single_turn_scenarios/      # Single-turn coding tasks
│   │   │   ├── multi_turn_scenarios/       # Multi-turn coding tasks
│   │   │   └── python_coding/              # Python-specific tasks
│   │   ├── models/                         # Model integrations
│   │   └── api/                            # Core evaluation API
│   │
│   └── evaluation_engine/                  # Evaluation Engine API
│       ├── api/                            # REST API endpoints
│       ├── core/                           # Core evaluation logic
│       ├── docs/                           # Documentation & scripts
│       │   ├── create_evaluation.sh        # Create evaluation script
│       │   ├── check_evaluation.sh         # Check status script
│       │   └── api_interface_summary.md    # API documentation
│       └── security/                       # Security components
│
├── Data & Results
│   ├── results/                            # Evaluation results storage
│   ├── task_templates/                     # Task template definitions
│   └── dynamic_tasks/                      # Dynamic task configurations
│
├── Tools & Scripts
│   ├── scripts/                            # Utility scripts
│   ├── monitoring/                         # Monitoring tools
│   └── temp/                               # Temporary files & archives
│
└── Testing & Deployment
    ├── tests/                              # Test suites
    ├── deployment/                         # Deployment configurations
    └── docs/                               # Additional documentation
```

## Quick Start

### 1. Environment Setup

Choose your platform and run the appropriate setup script:

**Linux/macOS:**
```bash
# Make scripts executable
chmod +x install.sh setupEvaluationEnvironment.sh

# Install dependencies
./install.sh

# Setup evaluation environment
./setupEvaluationEnvironment.sh
```

**Windows (PowerShell as Administrator):**
```powershell
# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
.\install.ps1

# Setup evaluation environment
.\setupEvaluationEnvironment.ps1
```

### 2. Verify Installation

```bash
# Test lm-eval installation
python -m lm_eval --help

# Test with dummy model
python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation --limit 1
```

## l*m-eval Framework Usage

### Basic Commands

**Simple Evaluation:**
```bash
# Basic single-turn scenario evaluation
python -m lm_eval \
  --model claude-local \
  --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation \
  --limit 2

# Multiple tasks evaluation
python -m lm_eval \
  --model claude-local \
  --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_code_completion,single_turn_scenarios_bug_fix \
  --limit 3 \
  --output_path results/my_evaluation
```

### Advanced Parameter Configuration

**Comprehensive Evaluation with Custom Settings:**
```bash
python -m lm_eval \
  --model claude-local \
  --model_args model=claude-3-haiku-20240307,temperature=0.7,max_tokens=1000 \
  --tasks single_turn_scenarios_function_generation \
  --num_fewshot 0 \
  --batch_size 1 \
  --limit 10 \
  --output_path results/detailed_evaluation \
  --log_samples \
  --show_config \
  --verbosity INFO
```

**Model-Specific Configurations:**

*Claude (Anthropic):*
```bash
export ANTHROPIC_API_KEY="your_api_key"
python -m lm_eval \
  --model claude-local \
  --model_args model=claude-3-haiku-20240307,temperature=0.0 \
  --tasks single_turn_scenarios_code_completion \
  --limit 5
```

*DeepSeek Coder:*
```bash
export DEEPSEEK_API_KEY="your_api_key"
python -m lm_eval \
  --model deepseek \
  --model_args model=deepseek-coder \
  --tasks single_turn_scenarios_algorithm_implementation \
  --limit 5
```

*OpenAI GPT:*
```bash
export OPENAI_API_KEY="your_api_key"
python -m lm_eval \
  --model openai-completions \
  --model_args model=gpt-3.5-turbo \
  --tasks single_turn_scenarios_bug_fix \
  --limit 5
```

*DashScope (Qwen Models):*
```bash
export DASHSCOPE_API_KEY="your_api_key"
python -m lm_eval \
  --model dashscope \
  --model_args model=qwen-turbo \
  --tasks single_turn_scenarios_function_generation \
  --limit 5
```

### Available Tasks

**Single-Turn Scenarios:**
- `single_turn_scenarios_function_generation` - Generate complete functions
- `single_turn_scenarios_code_completion` - Complete partial code
- `single_turn_scenarios_bug_fix` - Fix buggy code
- `single_turn_scenarios_algorithm_implementation` - Implement algorithms
- `single_turn_scenarios_api_design` - Design API interfaces
- `single_turn_scenarios_system_design` - System architecture design
- `single_turn_scenarios_security` - Security implementation
- `single_turn_scenarios_performance_optimization` - Performance optimization
- `single_turn_scenarios_testing_strategy` - Testing strategies
- `single_turn_scenarios_documentation` - Code documentation

**Multi-Turn Scenarios:**
- `multi_turn_scenarios_project_development` - Full project development
- `multi_turn_scenarios_code_review` - Code review processes
- `multi_turn_scenarios_debugging_session` - Interactive debugging

### Parameter Reference

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--model` | Model backend to use | `claude-local`, `deepseek`, `dummy` |
| `--model_args` | Model-specific arguments | `model=claude-3-haiku-20240307,temperature=0.7` |
| `--tasks` | Tasks to evaluate (comma-separated) | `single_turn_scenarios_function_generation` |
| `--limit` | Number of samples to evaluate | `10` |
| `--num_fewshot` | Number of few-shot examples | `0`, `3`, `5` |
| `--batch_size` | Batch size for evaluation | `1`, `4`, `8` |
| `--output_path` | Output directory for results | `results/my_evaluation` |
| `--log_samples` | Save individual sample results | (flag) |
| `--show_config` | Display task configuration | (flag) |
| `--verbosity` | Logging level | `DEBUG`, `INFO`, `WARNING` |

## Evaluation Engine API

The Evaluation Engine provides a REST API for managing evaluation tasks asynchronously.

### Starting the API Server

```bash
# Start the evaluation engine API server
python temp/real_api_server.py
```

The server will start on `http://localhost:8000` with the following endpoints:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### API Authentication

Default credentials:
- **Admin**: `admin` / `admin123`
- **Evaluator**: `evaluator` / `eval123`

### Using the API

**1. Login and Get Token:**

*Request:*
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

*Response:*
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_info": {
    "user_id": "admin_001",
    "username": "admin",
    "roles": ["admin"]
  }
}
```

**2. Create Evaluation Task:**

*Request:*
```bash
curl -X POST http://localhost:8000/evaluations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "model_id": "claude-local",
    "task_ids": [
      "single_turn_scenarios_code_completion",
      "single_turn_scenarios_bug_fix"
    ],
    "configuration": {
      "limit": 5,
      "temperature": 0.7
    },
    "metadata": {
      "description": "Code evaluation test"
    }
  }'
```

*Response:*
```json
{
  "evaluation_id": "eval_8b954c845e36",
  "status": "created",
  "message": "Evaluation created and started",
  "created_at": "2025-09-27T16:43:11.599906"
}
```

**3. Check Evaluation Status:**

*Request:*
```bash
curl -X GET http://localhost:8000/evaluations/EVALUATION_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

*Response (Running):*
```json
{
  "evaluation_id": "eval_8b954c845e36",
  "status": "running",
  "progress": 0.6,
  "model_id": "claude-local",
  "task_ids": [
    "single_turn_scenarios_code_completion",
    "single_turn_scenarios_bug_fix"
  ],
  "created_at": "2025-09-27T16:43:11.598836",
  "start_time": "2025-09-27T16:43:11.602708",
  "completed_at": null,
  "error": null
}
```

*Response (Completed):*
```json
{
  "evaluation_id": "eval_8b954c845e36",
  "status": "completed",
  "progress": 1.0,
  "model_id": "claude-local",
  "task_ids": [
    "single_turn_scenarios_code_completion",
    "single_turn_scenarios_bug_fix"
  ],
  "created_at": "2025-09-27T16:43:11.598836",
  "start_time": "2025-09-27T16:43:11.602708",
  "completed_at": "2025-09-27T16:43:50.600035",
  "error": null
}
```

*Response (Failed):*
```json
{
  "evaluation_id": "eval_8b954c845e36",
  "status": "failed",
  "progress": 0.3,
  "model_id": "claude-local",
  "task_ids": ["single_turn_scenarios_code_completion"],
  "created_at": "2025-09-27T16:43:11.598836",
  "start_time": "2025-09-27T16:43:11.602708",
  "completed_at": null,
  "error": "API key not found or invalid"
}
```

**4. Get Evaluation Results:**

*Request:*
```bash
curl -X GET http://localhost:8000/results/EVALUATION_ID?include_details=true \
  -H "Authorization: Bearer YOUR_TOKEN"
```

*Response:*
```json
{
  "evaluation_id": "eval_8b954c845e36",
  "model_id": "claude-local",
  "task_results": [
    {
      "task_id": "single_turn_scenarios_code_completion",
      "status": "completed",
      "score": 0.75,
      "metrics": {
        "exact_match": 0.0,
        "syntax_validity": 0.85,
        "runtime_correctness": 0.65
      },
      "execution_time": 45.2
    },
    {
      "task_id": "single_turn_scenarios_bug_fix",
      "status": "completed",
      "score": 0.82,
      "metrics": {
        "exact_match": 0.0,
        "syntax_validity": 0.90,
        "runtime_correctness": 0.75
      },
      "execution_time": 38.7
    }
  ],
  "summary_metrics": {
    "overall_score": 0.785,
    "total_tasks": 2,
    "completed_tasks": 2,
    "average_execution_time": 41.95
  },
  "raw_output": "claude-local (model=claude-3-haiku-20240307), gen_kwargs: (None), limit: 5.0, num_fewshot: None, batch_size: 1\n|Tasks|Version|Filter|n-shot|Metric|Value|Stderr|\n|-----|-------|------|------|------|-----|------|\n|single_turn_scenarios_code_completion|1|extract_code|0|exact_match|0.00|±0|\n|single_turn_scenarios_code_completion|1|extract_code|0|syntax_validity|0.85|±0.15|\n..."
}
```

### API Error Responses

**Authentication Error (401):**
```json
{
  "detail": "Invalid token"
}
```

**Resource Not Found (404):**
```json
{
  "detail": "Evaluation not found"
}
```

**Validation Error (400):**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "model_id"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Invalid Model/Task (400):**
```json
{
  "detail": "Invalid tasks: ['invalid_task_name']"
}
```

### Additional API Endpoints

**5. Health Check (No Authentication Required):**

*Request:*
```bash
curl -X GET http://localhost:8000/health
```

*Response:*
```json
{
  "status": "healthy",
  "timestamp": "2025-09-27T16:43:11.123456",
  "version": "1.0.0-real",
  "active_evaluations": 3,
  "available_tasks": 18,
  "available_models": 4
}
```

**6. List Available Tasks:**

*Request:*
```bash
curl -X GET http://localhost:8000/tasks \
  -H "Authorization: Bearer YOUR_TOKEN"
```

*Response:*
```json
[
  {
    "task_id": "single_turn_scenarios_function_generation",
    "name": "Function Generation",
    "category": "single_turn",
    "difficulty": "intermediate",
    "description": "Generate complete functions from descriptions",
    "languages": ["python"],
    "tags": ["coding", "function_generation"],
    "estimated_duration": 60
  },
  {
    "task_id": "single_turn_scenarios_code_completion",
    "name": "Code Completion",
    "category": "single_turn", 
    "difficulty": "beginner",
    "description": "Complete partial code implementations",
    "languages": ["python"],
    "tags": ["coding", "code_completion"],
    "estimated_duration": 45
  }
]
```

**7. List Available Models:**

*Request:*
```bash
curl -X GET http://localhost:8000/models \
  -H "Authorization: Bearer YOUR_TOKEN"
```

*Response:*
```json
[
  {
    "model_id": "claude-local",
    "name": "Claude 3 Haiku",
    "provider": "anthropic",
    "version": "3-haiku",
    "capabilities": ["text_generation", "code_completion"],
    "supported_tasks": ["single_turn_scenarios"],
    "rate_limits": {
      "requests_per_minute": 60,
      "tokens_per_minute": 100000
    },
    "cost_per_token": 0.00025
  },
  {
    "model_id": "deepseek",
    "name": "DeepSeek Coder",
    "provider": "deepseek",
    "version": "latest",
    "capabilities": ["text_generation", "code_completion"],
    "supported_tasks": ["single_turn_scenarios"],
    "rate_limits": {
      "requests_per_minute": 100,
      "tokens_per_minute": 200000
    },
    "cost_per_token": 0.0001
  },
  {
    "model_id": "dashscope",
    "name": "Qwen Models",
    "provider": "alibaba_cloud",
    "version": "qwen-turbo",
    "capabilities": ["text_generation", "code_completion", "multilingual"],
    "supported_tasks": ["single_turn_scenarios"],
    "rate_limits": {
      "requests_per_minute": 120,
      "tokens_per_minute": 150000
    },
    "cost_per_token": 0.0002
  },
  {
    "model_id": "dummy",
    "name": "Dummy Model (测试用)",
    "provider": "lm-eval",
    "version": "1.0",
    "capabilities": ["text_generation", "code_completion"],
    "supported_tasks": ["single_turn_scenarios"],
    "rate_limits": {
      "requests_per_minute": 1000,
      "tokens_per_minute": 1000000
    },
    "cost_per_token": 0.0
  }
]
```

### Using Convenience Scripts

The framework includes ready-to-use scripts in `evaluation_engine/docs/`:

```bash
# Create an evaluation task
./evaluation_engine/docs/create_evaluation.sh

# Check evaluation status (replace with actual ID)
./evaluation_engine/docs/check_evaluation.sh eval_abc123def456

# View all available curl commands
./evaluation_engine/docs/curl_commands.sh
```

### Supported Models

| Model ID | Description | Provider |
|----------|-------------|----------|
| `claude-local` | Claude 3 Haiku | Anthropic |
| `openai-completions` | GPT-3.5 Turbo | OpenAI |
| `deepseek` | DeepSeek Coder | DeepSeek |
| `dashscope` | Qwen Models (Qwen-Turbo, Qwen-Plus, etc.) | Alibaba Cloud |
| `dummy` | Test Model | Built-in |

## Dataset Format & Examples

### Dataset Structure

The framework uses JSONL (JSON Lines) format for datasets. Each line contains a complete problem definition.

**Location:** `lm_eval/tasks/single_turn_scenarios/problems.jsonl`

### Dataset Schema

Each problem must include these required fields:

```json
{
  "id": "unique_problem_identifier",
  "title": "Human-readable problem title",
  "language": "programming_language",
  "scenario": "task_type",
  "difficulty": "simple|intermediate|advanced|expert",
  "context_mode": "no_context|minimal_context|full_context",
  "prompt": "Problem description and requirements",
  "reference": ["expected_solution_code"],
  "tests": [{"cmd": "test_command", "file": "test_file", "type": "unit"}],
  "metadata": {
    "author": "creator_name",
    "license": "MIT",
    "memory_limit_mb": 100,
    "time_limit_s": 5,
    "seed": 1234
  }
}
```

### Example Datasets

**1. Function Generation Example:**
```json
{
  "id": "fg_001",
  "title": "Fibonacci Sequence Generator",
  "language": "python",
  "scenario": "function_generation",
  "difficulty": "intermediate",
  "context_mode": "minimal_context",
  "prompt": "Write a function `fibonacci(n)` that returns the nth Fibonacci number. Use dynamic programming for efficiency. Handle edge cases for n <= 0.",
  "reference": [
    "def fibonacci(n):\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    \n    dp = [0] * (n + 1)\n    dp[1] = 1\n    \n    for i in range(2, n + 1):\n        dp[i] = dp[i-1] + dp[i-2]\n    \n    return dp[n]"
  ],
  "tests": [
    {"cmd": "python -m pytest tests/test_fibonacci.py -v", "file": "tests/test_fibonacci.py", "type": "unit"}
  ],
  "metadata": {
    "author": "system",
    "license": "MIT",
    "memory_limit_mb": 50,
    "time_limit_s": 3,
    "seed": 1001
  }
}
```

**2. Bug Fix Example:**
```json
{
  "id": "bf_001", 
  "title": "Fix Division by Zero",
  "language": "python",
  "scenario": "bug_fix",
  "difficulty": "simple",
  "context_mode": "full_context",
  "prompt": "The following function has a bug that causes runtime errors. Fix the issue:\n\n```python\ndef safe_divide(a, b):\n    return a / b\n```\n\nThe function should handle division by zero gracefully.",
  "reference": [
    "def safe_divide(a, b):\n    if b == 0:\n        raise ValueError('Cannot divide by zero')\n    return a / b"
  ],
  "tests": [
    {"cmd": "python -m pytest tests/test_safe_divide.py -v", "file": "tests/test_safe_divide.py", "type": "unit"}
  ],
  "metadata": {
    "author": "system",
    "license": "MIT", 
    "memory_limit_mb": 25,
    "time_limit_s": 2,
    "seed": 2001
  }
}
```

**3. Code Completion Example:**
```json
{
  "id": "cc_001",
  "title": "Complete Binary Search Implementation", 
  "language": "python",
  "scenario": "code_completion",
  "difficulty": "intermediate",
  "context_mode": "minimal_context",
  "prompt": "Complete the binary search function:\n\n```python\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    \n    while left <= right:\n        mid = (left + right) // 2\n        # TODO: Complete the implementation\n```",
  "reference": [
    "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    \n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    \n    return -1"
  ],
  "tests": [
    {"cmd": "python -m pytest tests/test_binary_search.py -v", "file": "tests/test_binary_search.py", "type": "unit"}
  ],
  "metadata": {
    "author": "system",
    "license": "MIT",
    "memory_limit_mb": 30,
    "time_limit_s": 3,
    "seed": 3001
  }
}
```

### Scenario Types

| Scenario | Description | Key Fields |
|----------|-------------|------------|
| `function_generation` | Generate complete functions from description | `prompt` with requirements |
| `code_completion` | Complete partial code implementations | `prompt` with incomplete code |
| `bug_fix` | Fix buggy code | `prompt` with broken code |
| `algorithm_implementation` | Implement specific algorithms | `prompt` with algorithm specs |
| `api_design` | Design API interfaces | `prompt` with API requirements |
| `system_design` | Architecture design tasks | `prompt` with system requirements |

### Context Modes

- **`no_context`**: Minimal problem statement only
- **`minimal_context`**: Basic context and hints
- **`full_context`**: Complete context with examples and detailed requirements

### Creating Custom Datasets

1. **Create your JSONL file:**
```bash
# Create a new dataset file
touch my_custom_problems.jsonl
```

2. **Add problems following the schema:**
```json
{"id": "custom_001", "title": "My Problem", "language": "python", "scenario": "function_generation", "difficulty": "simple", "context_mode": "no_context", "prompt": "Write a function that...", "reference": ["def solution():..."], "tests": [{"cmd": "pytest test.py", "file": "test.py", "type": "unit"}], "metadata": {"author": "me", "license": "MIT", "memory_limit_mb": 100, "time_limit_s": 5, "seed": 1234}}
```

3. **Use with lm-eval:**
```bash
# Copy to task directory
cp my_custom_problems.jsonl lm_eval/tasks/single_turn_scenarios/

# Run evaluation
python -m lm_eval \
  --model claude-local \
  --tasks single_turn_scenarios_function_generation \
  --metadata '{"dataset_path": "my_custom_problems.jsonl"}' \
  --limit 5
```

## 📈 Understanding Results

### Result Files Structure

After evaluation, results are stored in the `results/` directory:

```
results/
├── eval_YYYYMMDD_HHMMSS/              # Timestamped evaluation directory
│   └── model_name/                    # Model-specific results
│       ├── results_timestamp.json     # Summary metrics
│       └── samples_task_name.jsonl    # Detailed sample results
```

### Key Metrics

| Metric | Range | Description |
|--------|-------|-------------|
| `exact_match` | 0.0-1.0 | Exact string match with reference |
| `syntax_validity` | 0.0-1.0 | Syntactically valid code percentage |
| `runtime_correctness` | 0.0-1.0 | Code executes without errors |
| `bleu_score` | 0.0-1.0 | BLEU similarity to reference |
| `code_quality` | 0.0-1.0 | Overall code quality assessment |

### Sample Result Analysis

**Summary Results (`results_*.json`):**
```json
{
  "results": {
    "single_turn_scenarios_function_generation": {
      "exact_match,extract_code": 0.0,
      "syntax_validity,extract_code": 0.85,
      "runtime_correctness,extract_code": 0.75
    }
  }
}
```

**Individual Samples (`samples_*.jsonl`):**
```json
{
  "doc_id": 0,
  "doc": {
    "id": "fg_001",
    "prompt": "Write a function to calculate factorial...",
    "reference": ["def factorial(n): ..."]
  },
  "resps": [["def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)"]],
  "filtered_resps": ["def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)"],
  "exact_match": 0.0,
  "syntax_validity": 1.0,
  "runtime_correctness": 1.0
}
```

## 🔧 Troubleshooting

### Common Issues & Solutions

**Installation Issues:**
```bash
# Permission denied on scripts
chmod +x *.sh

# Python module not found
pip install -e .

# API key not set
export ANTHROPIC_API_KEY="your_key_here"
```

**Evaluation Issues:**
```bash
# Task not found
python -m lm_eval --tasks list | grep single_turn

# Connection timeout
# Check if API server is running and accessible

# Memory issues with large evaluations
# Reduce batch_size or limit parameters
```

**API Server Issues:**
```bash
# Port already in use
# Kill existing process: pkill -f "real_api_server.py"

# Authentication failed
# Check credentials: admin/admin123 or evaluator/eval123
```

### Debug Commands

```bash
# Test basic functionality
python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation --limit 1

# Verbose logging
python -m lm_eval --model claude-local --tasks single_turn_scenarios_bug_fix --verbosity DEBUG --limit 1

# Check task configuration
python -m lm_eval --model dummy --tasks single_turn_scenarios_code_completion --show_config
```

### Getting Help

- **Documentation**: Check `evaluation_engine/docs/` for detailed guides
- **API Reference**: Visit http://localhost:8000/docs when server is running
- **Task Examples**: See `lm_eval/tasks/single_turn_scenarios/problems.jsonl`
- **Configuration**: Review task YAML files in task directories

## 📚 Additional Resources

### Key Documentation Files

- `evaluation_engine/docs/api_interface_summary.md` - Complete API reference
- `evaluation_engine/docs/evaluation_results_storage_guide.md` - Results storage guide
- `lm_eval/tasks/single_turn_scenarios/README.md` - Task-specific documentation

### Example Workflows

1. **Quick Model Comparison:**
```bash
# Test multiple models on same task
for model in claude-local deepseek dummy; do
  python -m lm_eval --model $model --tasks single_turn_scenarios_function_generation --limit 3 --output_path results/${model}_test
done
```

2. **Custom Dataset Evaluation:**
```bash
# Create custom dataset and evaluate
echo '{"id":"test_001","title":"Test","language":"python","scenario":"function_generation","difficulty":"simple","context_mode":"no_context","prompt":"Write hello world","reference":["print(\"Hello World\")"],"tests":[],"metadata":{"author":"test","license":"MIT","memory_limit_mb":50,"time_limit_s":5,"seed":1}}' > custom_test.jsonl

python -m lm_eval --model claude-local --tasks single_turn_scenarios_function_generation --metadata '{"dataset_path": "custom_test.jsonl"}' --limit 1
```

3. **API-based Evaluation:**
```bash
# Start server, create evaluation, monitor progress
python temp/real_api_server.py &
./evaluation_engine/docs/create_evaluation.sh
./evaluation_engine/docs/check_evaluation.sh eval_your_id_here
```

## 🏁 Quick Examples

### Example 1: Simple Function Generation
```bash
# Evaluate Claude on function generation tasks
export ANTHROPIC_API_KEY="your_key_here"
python -m lm_eval \
  --model claude-local \
  --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation \
  --limit 3 \
  --output_path results/claude_function_test
```

### Example 2: Multi-Task Evaluation via API
```bash
# Start API server
python temp/real_api_server.py &

# Create evaluation using convenience script
./evaluation_engine/docs/create_evaluation.sh

# Check results (replace with actual evaluation ID)
./evaluation_engine/docs/check_evaluation.sh eval_abc123def456
```

### Example 3: Custom Dataset Evaluation
```bash
# Create a simple custom problem
echo '{"id":"custom_001","title":"Hello World","language":"python","scenario":"function_generation","difficulty":"simple","context_mode":"no_context","prompt":"Write a function that prints Hello World","reference":["def hello():\n    print(\"Hello World\")"],"tests":[],"metadata":{"author":"user","license":"MIT","memory_limit_mb":50,"time_limit_s":5,"seed":1}}' > my_problems.jsonl

# Evaluate with custom dataset
python -m lm_eval \
  --model claude-local \
  --tasks single_turn_scenarios_function_generation \
  --metadata '{"dataset_path": "my_problems.jsonl"}' \
  --limit 1
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Happy Evaluating! 🚀**

