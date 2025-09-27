# API任务配置详细指南

## 🎯 概述

本指南详细说明如何通过API调用配置和管理evaluation engine中的任务。包括任务发现、配置、创建自定义任务以及高级任务管理功能。

## 📋 任务管理API端点

### 1. 任务发现和查询

#### 列出所有可用任务
```bash
curl -X GET "http://localhost:8000/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G \
  -d "limit=50" \
  -d "offset=0"

# 响应示例
{
  "items": [
    {
      "task_id": "single_turn_scenarios_function_generation",
      "name": "Function Generation",
      "category": "single_turn",
      "difficulty": "intermediate",
      "description": "Generate Python functions based on specifications",
      "languages": ["python"],
      "tags": ["coding", "generation"],
      "estimated_duration": 30
    }
  ],
  "total": 18,
  "page": 1,
  "page_size": 50,
  "has_next": false,
  "has_previous": false
}
```

#### 按类别筛选任务
```bash
curl -X GET "http://localhost:8000/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G \
  -d "category=single_turn" \
  -d "difficulty=intermediate" \
  -d "language=python"
```

#### 按标签筛选任务
```bash
curl -X GET "http://localhost:8000/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G \
  -d "tags=coding,generation" \
  -d "limit=20"
```

### 2. 获取任务详细信息

#### 获取单个任务详情
```bash
curl -X GET "http://localhost:8000/tasks/single_turn_scenarios_function_generation" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 响应示例
{
  "task_id": "single_turn_scenarios_function_generation",
  "name": "Function Generation",
  "category": "single_turn",
  "difficulty": "intermediate",
  "description": "Generate Python functions based on specifications",
  "languages": ["python"],
  "tags": ["coding", "generation"],
  "estimated_duration": 30,
  "requirements": [
    "Generate syntactically correct Python functions",
    "Follow PEP 8 style guidelines",
    "Include appropriate docstrings"
  ],
  "evaluation_criteria": [
    "Syntax correctness",
    "Functional correctness",
    "Code quality",
    "Documentation completeness"
  ],
  "sample_input": {
    "prompt": "Write a function to calculate the factorial of a number",
    "context": "def factorial(n):",
    "expected_signature": "factorial(n: int) -> int"
  },
  "sample_output": {
    "code": "def factorial(n: int) -> int:\n    \"\"\"Calculate factorial of n.\"\"\"\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
    "explanation": "Recursive implementation with base case"
  },
  "metrics": ["syntax_correctness", "functional_correctness", "code_quality"],
  "dependencies": []
}
```

### 3. 任务配置管理

#### 创建自定义任务配置
```bash
curl -X POST "http://localhost:8000/tasks/custom" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "custom_python_debugging",
    "name": "Python Debugging Task",
    "category": "single_turn",
    "difficulty": "advanced",
    "description": "Debug Python code and fix errors",
    "languages": ["python"],
    "tags": ["debugging", "error-fixing"],
    "configuration": {
      "dataset_path": "custom_datasets/debugging_tasks.jsonl",
      "metrics": ["fix_accuracy", "code_quality", "explanation_quality"],
      "evaluation_criteria": {
        "fix_accuracy": 0.8,
        "code_quality": 0.7,
        "explanation_quality": 0.6
      },
      "generation_params": {
        "temperature": 0.3,
        "max_tokens": 1024,
        "stop_sequences": ["```"]
      }
    },
    "requirements": [
      "Identify bugs in Python code",
      "Provide correct fixes",
      "Explain the reasoning"
    ],
    "sample_data": [
      {
        "input": "def divide(a, b):\n    return a / b",
        "expected_fix": "def divide(a, b):\n    if b == 0:\n        raise ValueError(\"Cannot divide by zero\")\n    return a / b",
        "explanation": "Added zero division check"
      }
    ]
  }'

# 响应示例
{
  "task_id": "custom_python_debugging",
  "status": "created",
  "message": "Custom task created successfully",
  "validation_results": {
    "is_valid": true,
    "warnings": [],
    "errors": []
  }
}
```

#### 更新任务配置
```bash
curl -X PUT "http://localhost:8000/tasks/custom_python_debugging" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      "generation_params": {
        "temperature": 0.2,
        "max_tokens": 1536
      },
      "evaluation_criteria": {
        "fix_accuracy": 0.85,
        "code_quality": 0.75
      }
    }
  }'
```

#### 验证任务配置
```bash
curl -X POST "http://localhost:8000/tasks/custom_python_debugging/validate" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 响应示例
{
  "is_valid": true,
  "validation_results": {
    "dataset_accessible": true,
    "metrics_available": true,
    "dependencies_satisfied": true,
    "configuration_valid": true
  },
  "warnings": [
    "Temperature is quite low, may reduce creativity"
  ],
  "errors": []
}
```

## 🔧 任务配置参数详解

### 1. 基础任务配置

#### 任务元数据配置
```json
{
  "task_id": "unique_task_identifier",
  "name": "Human-readable task name",
  "category": "single_turn|multi_turn|domain_specific",
  "difficulty": "beginner|intermediate|advanced|expert",
  "description": "Detailed task description",
  "languages": ["python", "javascript", "java"],
  "tags": ["coding", "debugging", "generation"],
  "estimated_duration": 60,
  "version": "1.0.0"
}
```

#### 数据集配置
```json
{
  "dataset_config": {
    "dataset_path": "path/to/dataset.jsonl",
    "dataset_format": "jsonl|json|csv",
    "sample_size": 1000,
    "validation_split": 0.1,
    "preprocessing": {
      "normalize_whitespace": true,
      "remove_comments": false,
      "filter_by_length": {
        "min_length": 10,
        "max_length": 5000
      }
    },
    "data_schema": {
      "input_field": "prompt",
      "output_field": "expected_output",
      "metadata_fields": ["difficulty", "language", "context"]
    }
  }
}
```

#### 评估配置
```json
{
  "evaluation_config": {
    "metrics": [
      "syntax_correctness",
      "functional_correctness", 
      "code_quality",
      "performance_efficiency"
    ],
    "evaluation_criteria": {
      "syntax_correctness": {
        "weight": 0.3,
        "threshold": 0.9
      },
      "functional_correctness": {
        "weight": 0.4,
        "threshold": 0.8
      },
      "code_quality": {
        "weight": 0.2,
        "threshold": 0.7
      },
      "performance_efficiency": {
        "weight": 0.1,
        "threshold": 0.6
      }
    },
    "aggregation_method": "weighted_average",
    "pass_threshold": 0.75
  }
}
```

#### 生成参数配置
```json
{
  "generation_config": {
    "temperature": 0.7,
    "max_tokens": 2048,
    "top_p": 0.9,
    "top_k": 50,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "stop_sequences": ["```", "\n\n", "def ", "class "],
    "retry_attempts": 3,
    "timeout": 30
  }
}
```

### 2. 高级任务配置

#### 多轮对话任务配置
```json
{
  "multi_turn_config": {
    "max_turns": 5,
    "conversation_timeout": 300,
    "enable_context_retention": true,
    "turn_templates": [
      {
        "turn": 1,
        "role": "user",
        "template": "Please implement a {function_type} function that {requirements}",
        "required_fields": ["function_type", "requirements"]
      },
      {
        "turn": 2,
        "role": "assistant",
        "template": "Here's the implementation:\n```python\n{code}\n```",
        "validation": {
          "code_syntax": true,
          "function_signature": true
        }
      },
      {
        "turn": 3,
        "role": "user", 
        "template": "Can you add error handling and improve the documentation?",
        "depends_on": [2]
      }
    ],
    "success_criteria": {
      "all_turns_completed": true,
      "final_code_quality": 0.8,
      "conversation_coherence": 0.7
    }
  }
}
```

#### 上下文配置
```json
{
  "context_config": {
    "context_mode": "full_context|minimal_context|no_context|domain_context",
    "context_sources": [
      {
        "type": "documentation",
        "path": "docs/api_reference.md",
        "weight": 0.3
      },
      {
        "type": "code_examples", 
        "path": "examples/",
        "weight": 0.4
      },
      {
        "type": "previous_solutions",
        "dynamic": true,
        "weight": 0.3
      }
    ],
    "context_injection": {
      "position": "before_prompt|after_prompt|interleaved",
      "max_context_length": 4000,
      "context_template": "Context:\n{context}\n\nTask:\n{prompt}"
    }
  }
}
```

#### 安全和限制配置
```json
{
  "security_config": {
    "enable_code_execution": false,
    "sandbox_environment": "docker",
    "allowed_imports": ["os", "sys", "json", "math"],
    "blocked_patterns": [
      "import subprocess",
      "eval\\(",
      "exec\\(",
      "__import__"
    ],
    "resource_limits": {
      "max_execution_time": 10,
      "max_memory_mb": 256,
      "max_file_size_kb": 100
    }
  }
}
```

## 🚀 实际API调用示例

### 1. 创建完整的自定义任务

```python
import requests
import json

# API配置
API_BASE = "http://localhost:8000"
ACCESS_TOKEN = "your_access_token_here"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# 创建自定义任务
custom_task_config = {
    "task_id": "advanced_python_refactoring",
    "name": "Advanced Python Code Refactoring",
    "category": "single_turn",
    "difficulty": "expert",
    "description": "Refactor Python code to improve readability, performance, and maintainability",
    "languages": ["python"],
    "tags": ["refactoring", "optimization", "best-practices"],
    "estimated_duration": 120,
    
    "configuration": {
        "dataset_config": {
            "dataset_path": "datasets/refactoring_tasks.jsonl",
            "sample_size": 500,
            "preprocessing": {
                "normalize_whitespace": True,
                "validate_syntax": True
            }
        },
        
        "evaluation_config": {
            "metrics": [
                "code_quality_improvement",
                "performance_gain",
                "readability_score",
                "maintainability_index"
            ],
            "evaluation_criteria": {
                "code_quality_improvement": {"weight": 0.3, "threshold": 0.7},
                "performance_gain": {"weight": 0.25, "threshold": 0.1},
                "readability_score": {"weight": 0.25, "threshold": 0.8},
                "maintainability_index": {"weight": 0.2, "threshold": 0.75}
            }
        },
        
        "generation_config": {
            "temperature": 0.4,
            "max_tokens": 3000,
            "top_p": 0.9,
            "stop_sequences": ["```", "\n\n# End of refactoring"]
        },
        
        "context_config": {
            "context_mode": "domain_context",
            "context_sources": [
                {
                    "type": "best_practices",
                    "path": "knowledge/python_best_practices.md",
                    "weight": 0.4
                },
                {
                    "type": "performance_patterns",
                    "path": "knowledge/performance_patterns.md", 
                    "weight": 0.3
                },
                {
                    "type": "refactoring_examples",
                    "path": "examples/refactoring/",
                    "weight": 0.3
                }
            ]
        }
    },
    
    "requirements": [
        "Improve code structure and organization",
        "Optimize performance where possible",
        "Enhance readability and documentation",
        "Follow Python best practices and PEP standards",
        "Maintain original functionality"
    ],
    
    "sample_data": [
        {
            "input": {
                "original_code": "def process_data(data):\n    result = []\n    for i in range(len(data)):\n        if data[i] > 0:\n            result.append(data[i] * 2)\n    return result",
                "requirements": "Optimize for performance and readability"
            },
            "expected_output": {
                "refactored_code": "def process_data(data: List[float]) -> List[float]:\n    \"\"\"Process positive numbers by doubling them.\"\"\"\n    return [x * 2 for x in data if x > 0]",
                "improvements": [
                    "Used list comprehension for better performance",
                    "Added type hints for clarity",
                    "Added docstring for documentation",
                    "Eliminated manual indexing"
                ]
            }
        }
    ]
}

# 发送创建请求
response = requests.post(
    f"{API_BASE}/tasks/custom",
    headers=headers,
    json=custom_task_config
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ 任务创建成功: {result['task_id']}")
    print(f"状态: {result['status']}")
    
    # 验证任务配置
    validation_response = requests.post(
        f"{API_BASE}/tasks/{result['task_id']}/validate",
        headers=headers
    )
    
    if validation_response.status_code == 200:
        validation = validation_response.json()
        print(f"验证结果: {'✅ 通过' if validation['is_valid'] else '❌ 失败'}")
        
        if validation['warnings']:
            print("⚠️ 警告:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
                
        if validation['errors']:
            print("❌ 错误:")
            for error in validation['errors']:
                print(f"  - {error}")
    
else:
    print(f"❌ 任务创建失败: {response.status_code}")
    print(response.text)
```

### 2. 使用自定义任务进行评估

```python
# 使用创建的自定义任务进行评估
evaluation_request = {
    "model_id": "claude-3-haiku",
    "task_ids": ["advanced_python_refactoring"],
    "configuration": {
        "limit": 10,
        "temperature": 0.4,
        "max_tokens": 3000,
        "context_mode": "domain_context"
    },
    "metadata": {
        "experiment_name": "refactoring_evaluation_v1",
        "description": "Testing advanced refactoring capabilities"
    }
}

# 创建评估
eval_response = requests.post(
    f"{API_BASE}/evaluations",
    headers=headers,
    json=evaluation_request
)

if eval_response.status_code == 200:
    eval_result = eval_response.json()
    evaluation_id = eval_result['evaluation_id']
    print(f"✅ 评估已创建: {evaluation_id}")
    
    # 监控评估进度
    import time
    while True:
        status_response = requests.get(
            f"{API_BASE}/evaluations/{evaluation_id}",
            headers=headers
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"进度: {status['progress']:.1%} - {status['status']}")
            
            if status['status'] in ['completed', 'failed', 'cancelled']:
                break
                
        time.sleep(5)
    
    # 获取评估结果
    if status['status'] == 'completed':
        results_response = requests.get(
            f"{API_BASE}/results/{evaluation_id}",
            headers=headers,
            params={"include_details": True}
        )
        
        if results_response.status_code == 200:
            results = results_response.json()
            print(f"✅ 评估完成!")
            print(f"总体分数: {results['overall_score']:.3f}")
            print(f"执行时间: {results['execution_time']:.1f}s")
            
            for task_result in results['task_results']:
                print(f"\n任务: {task_result['task_id']}")
                print(f"分数: {task_result['score']:.3f}")
                for metric, value in task_result['metrics'].items():
                    print(f"  {metric}: {value:.3f}")

else:
    print(f"❌ 评估创建失败: {eval_response.status_code}")
    print(eval_response.text)
```

### 3. 批量任务管理

```python
# 批量创建多个相关任务
task_templates = [
    {
        "base_id": "python_code_review",
        "variants": [
            {"difficulty": "beginner", "max_tokens": 1024},
            {"difficulty": "intermediate", "max_tokens": 2048},
            {"difficulty": "advanced", "max_tokens": 3072}
        ]
    },
    {
        "base_id": "javascript_debugging",
        "variants": [
            {"language": "javascript", "framework": "vanilla"},
            {"language": "javascript", "framework": "react"},
            {"language": "javascript", "framework": "node"}
        ]
    }
]

created_tasks = []

for template in task_templates:
    base_id = template["base_id"]
    
    for i, variant in enumerate(template["variants"]):
        task_id = f"{base_id}_{i+1}"
        
        task_config = {
            "task_id": task_id,
            "name": f"{base_id.replace('_', ' ').title()} - Variant {i+1}",
            "category": "single_turn",
            "difficulty": variant.get("difficulty", "intermediate"),
            "description": f"Specialized {base_id} task with {variant}",
            "configuration": {
                "generation_config": {
                    "max_tokens": variant.get("max_tokens", 2048),
                    "temperature": 0.5
                },
                "variant_config": variant
            }
        }
        
        response = requests.post(
            f"{API_BASE}/tasks/custom",
            headers=headers,
            json=task_config
        )
        
        if response.status_code == 200:
            created_tasks.append(task_id)
            print(f"✅ 创建任务: {task_id}")
        else:
            print(f"❌ 创建任务失败: {task_id}")

print(f"\n总共创建了 {len(created_tasks)} 个任务")

# 批量验证任务
validation_results = {}
for task_id in created_tasks:
    response = requests.post(
        f"{API_BASE}/tasks/{task_id}/validate",
        headers=headers
    )
    
    if response.status_code == 200:
        validation_results[task_id] = response.json()

# 显示验证摘要
valid_tasks = [tid for tid, result in validation_results.items() if result['is_valid']]
print(f"\n验证摘要: {len(valid_tasks)}/{len(created_tasks)} 个任务通过验证")
```

## 📊 任务配置最佳实践

### 1. 任务设计原则
- **单一职责**: 每个任务专注于一个特定的评估目标
- **可测量性**: 确保任务结果可以客观量化
- **可重现性**: 相同输入应产生一致的评估结果
- **渐进难度**: 提供不同难度级别的任务变体

### 2. 配置参数优化
- **温度设置**: 代码生成任务使用较低温度(0.2-0.4)，创意任务使用较高温度(0.7-0.9)
- **令牌限制**: 根据任务复杂度合理设置，避免过长或过短
- **停止序列**: 设置合适的停止条件，防止生成无关内容
- **上下文长度**: 平衡上下文信息量和处理效率

### 3. 评估指标选择
- **语法正确性**: 对于代码生成任务必须包含
- **功能正确性**: 通过测试用例验证
- **代码质量**: 考虑可读性、维护性、性能
- **创新性**: 对于开放性任务评估解决方案的创新程度

### 4. 数据集管理
- **数据质量**: 确保训练数据的准确性和多样性
- **版本控制**: 对数据集进行版本管理
- **隐私保护**: 避免包含敏感信息
- **平衡性**: 确保不同类型样本的均衡分布

## 🔧 故障排除

### 常见配置错误
1. **数据集路径错误**: 确保路径正确且文件可访问
2. **指标配置冲突**: 检查指标权重总和是否为1.0
3. **生成参数超限**: 确保参数值在合理范围内
4. **依赖项缺失**: 验证所有依赖任务都已注册

### 调试技巧
```bash
# 启用详细日志
curl -X POST "http://localhost:8000/tasks/debug/enable" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 获取任务配置详情
curl -X GET "http://localhost:8000/tasks/{task_id}/config" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 测试任务配置
curl -X POST "http://localhost:8000/tasks/{task_id}/test" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"sample_input": "test input"}'
```

通过这个详细的API任务配置指南，你可以完全通过API调用来管理和配置evaluation engine中的任务，实现高度自动化和定制化的评估流程。