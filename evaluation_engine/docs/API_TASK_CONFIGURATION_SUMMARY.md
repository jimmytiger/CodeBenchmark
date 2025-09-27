# API任务配置功能总结

## 🎯 概述

通过API调用配置task是AI Evaluation Engine的核心功能之一，提供了完整的任务生命周期管理能力。用户可以通过REST API端点发现、创建、配置、验证和管理评估任务。

## 📋 核心功能

### 1. 任务发现和查询
- **列出所有任务**: 支持分页和多维度筛选
- **任务详情查询**: 获取任务的完整配置信息
- **智能筛选**: 按类别、难度、语言、标签等筛选
- **元数据管理**: 丰富的任务元数据支持

### 2. 自定义任务创建
- **灵活配置**: 支持完全自定义的任务配置
- **多种任务类型**: 单轮、多轮、领域特定任务
- **配置验证**: 自动验证配置的正确性和完整性
- **模板系统**: 基于模板快速创建任务变体

### 3. 任务配置管理
- **动态更新**: 运行时更新任务配置
- **版本控制**: 任务配置的版本管理
- **配置继承**: 基于基础配置创建变体
- **批量操作**: 支持批量创建和管理任务

### 4. 任务验证和测试
- **配置验证**: 验证任务配置的有效性
- **依赖检查**: 检查任务依赖是否满足
- **实时测试**: 使用样本数据测试任务
- **性能评估**: 评估任务的执行性能

## 🔧 API端点详解

### 任务查询端点
```
GET /tasks                    # 列出所有任务
GET /tasks/{task_id}          # 获取任务详情
```

### 任务管理端点
```
POST /tasks/custom            # 创建自定义任务
PUT /tasks/{task_id}          # 更新任务配置
DELETE /tasks/{task_id}       # 删除自定义任务
```

### 任务验证端点
```
POST /tasks/{task_id}/validate  # 验证任务配置
POST /tasks/{task_id}/test      # 测试任务
```

## ⚙️ 配置参数体系

### 1. 基础元数据配置
```json
{
  "task_id": "unique_identifier",
  "name": "Human readable name",
  "category": "single_turn|multi_turn|domain_specific",
  "difficulty": "beginner|intermediate|advanced|expert",
  "description": "Task description",
  "languages": ["python", "javascript"],
  "tags": ["coding", "debugging"],
  "estimated_duration": 120
}
```

### 2. 数据集配置
```json
{
  "dataset_config": {
    "dataset_path": "path/to/dataset.jsonl",
    "sample_size": 1000,
    "preprocessing": {
      "normalize_whitespace": true,
      "validate_syntax": true
    },
    "data_schema": {
      "input_field": "prompt",
      "output_field": "expected_output"
    }
  }
}
```

### 3. 评估配置
```json
{
  "evaluation_config": {
    "metrics": ["accuracy", "quality", "performance"],
    "evaluation_criteria": {
      "accuracy": {"weight": 0.4, "threshold": 0.8},
      "quality": {"weight": 0.3, "threshold": 0.7},
      "performance": {"weight": 0.3, "threshold": 0.6}
    },
    "aggregation_method": "weighted_average",
    "pass_threshold": 0.75
  }
}
```

### 4. 生成参数配置
```json
{
  "generation_config": {
    "temperature": 0.7,
    "max_tokens": 2048,
    "top_p": 0.9,
    "stop_sequences": ["```", "\n\n"],
    "retry_attempts": 3,
    "timeout": 30
  }
}
```

### 5. 上下文配置
```json
{
  "context_config": {
    "context_mode": "full_context",
    "context_sources": [
      {
        "type": "documentation",
        "path": "docs/api_reference.md",
        "weight": 0.4
      }
    ],
    "max_context_length": 4000
  }
}
```

### 6. 多轮对话配置
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
        "template": "Please implement {function_type}"
      }
    ],
    "success_criteria": {
      "all_turns_completed": true,
      "final_code_quality": 0.8
    }
  }
}
```

## 🚀 实际使用示例

### 1. 创建代码优化任务
```python
task_config = {
    "task_id": "python_code_optimization",
    "name": "Python代码优化任务",
    "category": "single_turn",
    "difficulty": "advanced",
    "configuration": {
        "generation_config": {
            "temperature": 0.3,
            "max_tokens": 2048
        },
        "evaluation_config": {
            "metrics": ["performance_improvement", "code_quality"],
            "evaluation_criteria": {
                "performance_improvement": {"weight": 0.6, "threshold": 0.2},
                "code_quality": {"weight": 0.4, "threshold": 0.8}
            }
        }
    }
}

# 通过API创建任务
response = requests.post(
    "http://localhost:8000/tasks/custom",
    headers={"Authorization": f"Bearer {token}"},
    json=task_config
)
```

### 2. 批量创建任务变体
```python
# 创建不同难度级别的任务
difficulties = ["beginner", "intermediate", "advanced"]
for difficulty in difficulties:
    task_config = {
        "task_id": f"debugging_task_{difficulty}",
        "difficulty": difficulty,
        "configuration": {
            "generation_config": {
                "temperature": 0.2 + (difficulties.index(difficulty) * 0.1),
                "max_tokens": 1024 + (difficulties.index(difficulty) * 512)
            }
        }
    }
    # 创建任务...
```

### 3. 任务配置优化
```python
# A/B测试不同的温度设置
temperatures = [0.2, 0.5, 0.8]
for temp in temperatures:
    variant_config = base_config.copy()
    variant_config["task_id"] = f"task_temp_{int(temp*10)}"
    variant_config["configuration"]["generation_config"]["temperature"] = temp
    # 创建变体...
```

## 📊 配置最佳实践

### 1. 任务设计原则
- **单一职责**: 每个任务专注于一个特定目标
- **可测量性**: 确保结果可以客观量化
- **可重现性**: 相同输入产生一致结果
- **渐进难度**: 提供不同难度级别

### 2. 参数优化策略
- **温度设置**: 代码任务用低温度(0.2-0.4)，创意任务用高温度(0.7-0.9)
- **令牌限制**: 根据任务复杂度合理设置
- **停止序列**: 设置合适的停止条件
- **评估权重**: 根据任务重要性分配权重

### 3. 性能优化
- **缓存策略**: 合理使用缓存减少重复计算
- **批处理**: 批量处理相似任务
- **并发控制**: 控制并发数量避免资源竞争
- **超时设置**: 设置合理的超时时间

## 🔍 监控和调试

### 1. 任务验证
```bash
# 验证任务配置
curl -X POST "http://localhost:8000/tasks/{task_id}/validate" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. 任务测试
```bash
# 测试任务执行
curl -X POST "http://localhost:8000/tasks/{task_id}/test" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"sample_input": {"prompt": "test"}}'
```

### 3. 性能监控
```python
# 监控任务执行性能
performance_data = {
    "response_time": 3.5,
    "success_rate": 0.95,
    "quality_score": 0.88
}
```

## 🛠️ 故障排除

### 常见问题
1. **配置验证失败**: 检查配置参数格式和取值范围
2. **任务创建失败**: 确认任务ID唯一性和权限
3. **测试执行失败**: 检查样本数据格式和模型可用性
4. **性能问题**: 优化配置参数和资源分配

### 调试技巧
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 检查任务状态
curl -X GET "http://localhost:8000/tasks/{task_id}" \
  -H "Authorization: Bearer $TOKEN"

# 查看系统健康状态
curl -X GET "http://localhost:8000/system/health"
```

## 📈 高级功能

### 1. 动态任务生成
- 基于模板动态生成任务
- 参数化任务配置
- 条件逻辑支持

### 2. 任务编排
- 任务依赖管理
- 工作流定义
- 并行执行控制

### 3. 智能优化
- 自动参数调优
- 性能基准测试
- 配置推荐系统

## 🎯 总结

通过API配置task提供了强大而灵活的任务管理能力：

1. **完整的生命周期管理**: 从创建到删除的全流程支持
2. **丰富的配置选项**: 支持各种类型和复杂度的任务
3. **实时验证和测试**: 确保配置的正确性和有效性
4. **批量操作支持**: 提高任务管理效率
5. **性能监控**: 实时监控任务执行状态
6. **扩展性**: 支持自定义扩展和集成

这套API任务配置系统为用户提供了完全的控制权，可以根据具体需求创建和管理各种评估任务，实现高度定制化的AI模型评估流程。

---

**相关文档**:
- `api_task_configuration.md` - 详细API使用指南
- `task_api_implementation.py` - API端点实现示例
- `api_task_usage_examples.py` - 完整使用示例