# 专项功能测试使用指南

## 🎯 测试文件概览

| 测试文件 | 功能描述 | 主要测试内容 |
|---------|----------|-------------|
| test_advanced_model_config.py | 高级模型配置测试 | 复杂模型配置、参数调优、配置验证 |
| test_concrete_model_adapters.py | 具体模型适配器测试 | 模型特定实现、适配器模式、兼容性 |
| test_composite_metrics.py | 复合指标测试 | 多维度指标计算、指标组合、权重分配 |
| test_single_turn_simple.py | 简单单轮测试 | 基础单轮对话评估、简化流程验证 |
| test_task_2_implementation.py | 任务2实现测试 | 特定任务实现、功能验证、性能测试 |

## 🚀 快速运行

### 运行所有专项功能测试
```bash
python -m pytest evaluation_engine/tests/specialized/ -v
```

### 运行单个测试文件
```bash
# 高级模型配置测试
python -m pytest evaluation_engine/tests/specialized/test_advanced_model_config.py -v

# 具体模型适配器测试
python -m pytest evaluation_engine/tests/specialized/test_concrete_model_adapters.py -v

# 复合指标测试
python -m pytest evaluation_engine/tests/specialized/test_composite_metrics.py -v

# 简单单轮测试
python evaluation_engine/tests/specialized/test_single_turn_simple.py

# 任务2实现测试
python evaluation_engine/tests/specialized/test_task_2_implementation.py
```

## 📊 详细测试说明

### test_advanced_model_config.py
**高级模型配置功能测试**:
- 复杂模型参数配置
- 动态配置加载和验证
- 配置文件格式支持
- 参数优化和调优
- 配置继承和覆盖机制

**配置文件支持**:
- JSON格式配置
- YAML格式配置
- 环境变量配置
- 命令行参数配置

**运行示例**:
```bash
python -m pytest evaluation_engine/tests/specialized/test_advanced_model_config.py -v
```

### test_concrete_model_adapters.py
**模型适配器功能测试**:
- 不同模型API适配
- 统一接口实现
- 模型特定优化
- 兼容性验证
- 适配器模式实现

**支持的模型类型**:
- OpenAI GPT系列
- Anthropic Claude
- Google PaLM/Gemini
- 开源模型 (Llama, Mistral等)
- 自定义模型接口

**运行示例**:
```bash
python -m pytest evaluation_engine/tests/specialized/test_concrete_model_adapters.py -v
```

### test_composite_metrics.py
**复合指标计算测试**:
- 多维度指标组合
- 权重分配算法
- 指标聚合策略
- 自定义指标定义
- 指标相关性分析

**支持的指标类型**:
- 准确性指标
- 流畅性指标
- 相关性指标
- 创新性指标
- 综合评分

**运行示例**:
```bash
python -m pytest evaluation_engine/tests/specialized/test_composite_metrics.py -v
```

### test_single_turn_simple.py
**简单单轮评估测试**:
- 基础单轮对话处理
- 简化评估流程
- 快速验证功能
- 基准性能测试
- 错误处理验证

**测试场景**:
- 问答对话
- 文本生成
- 翻译任务
- 摘要生成

**运行示例**:
```bash
python evaluation_engine/tests/specialized/test_single_turn_simple.py
```

### test_task_2_implementation.py
**任务2特定实现测试**:
- 特定任务逻辑验证
- 实现正确性测试
- 性能基准验证
- 边界条件测试
- 集成功能验证

**运行示例**:
```bash
python evaluation_engine/tests/specialized/test_task_2_implementation.py
```

## 🔧 测试配置

### 环境要求
```bash
pip install -r requirements_api.txt
pip install pyyaml  # YAML配置支持
export PYTHONPATH="${PYTHONPATH}:."
```

### 模型配置
```bash
# 设置模型API密钥（如果需要）
export OPENAI_API_KEY="your_api_key"
export ANTHROPIC_API_KEY="your_api_key"
export GOOGLE_API_KEY="your_api_key"
```

### 测试配置文件
创建测试配置文件 `test_config.yaml`:
```yaml
models:
  gpt-4:
    provider: openai
    temperature: 0.7
    max_tokens: 1000
  claude-3:
    provider: anthropic
    temperature: 0.7
    max_tokens: 1000

metrics:
  composite:
    accuracy_weight: 0.4
    fluency_weight: 0.3
    relevance_weight: 0.3
```

### 调试模式
```bash
python -m pytest evaluation_engine/tests/specialized/ -v -s --tb=long
```

### 生成报告
```bash
python -m pytest evaluation_engine/tests/specialized/ --html=specialized_report.html
```

## 🎯 专项功能说明

### 高级模型配置
- **动态配置**: 运行时配置加载和修改
- **配置验证**: 参数有效性检查
- **配置继承**: 基础配置和特定配置组合
- **环境适配**: 不同环境下的配置适配

### 模型适配器
- **统一接口**: 不同模型的统一调用接口
- **参数映射**: 模型特定参数的标准化映射
- **错误处理**: 模型特定错误的统一处理
- **性能优化**: 模型特定的性能优化策略

### 复合指标
- **指标组合**: 多个基础指标的智能组合
- **权重优化**: 基于数据的权重自动调整
- **相关性分析**: 指标间相关性分析和去重
- **可解释性**: 复合指标的可解释性分析

## 🐛 常见问题

| 问题 | 解决方案 |
|------|----------|
| 配置文件格式错误 | 检查YAML/JSON语法 |
| 模型API调用失败 | 验证API密钥和网络连接 |
| 指标计算异常 | 检查输入数据格式和范围 |
| 适配器加载失败 | 确保模型库正确安装 |

## 📋 测试数据要求

### 模型配置测试数据
```json
{
  "model_configs": [
    {
      "name": "test_model",
      "provider": "openai",
      "parameters": {
        "temperature": 0.7,
        "max_tokens": 1000
      }
    }
  ]
}
```

### 复合指标测试数据
```json
{
  "metrics": {
    "accuracy": 0.85,
    "fluency": 0.90,
    "relevance": 0.88
  },
  "weights": {
    "accuracy": 0.4,
    "fluency": 0.3,
    "relevance": 0.3
  }
}
```

## 🔍 性能基准

| 测试类型 | 预期执行时间 | 内存使用 |
|---------|-------------|----------|
| 模型配置测试 | < 5秒 | < 100MB |
| 适配器测试 | < 10秒 | < 200MB |
| 复合指标测试 | < 3秒 | < 50MB |
| 单轮简单测试 | < 2秒 | < 30MB |