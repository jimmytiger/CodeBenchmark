# Evaluation Engine 测试套件使用指南

本目录包含了AI评估引擎的完整测试套件，涵盖了系统的各个核心组件。所有测试文件已从根目录迁移至此，并按功能分类到不同子目录中，便于统一管理和维护。

## 📁 测试目录结构

```
evaluation_engine/tests/
├── core_engines/           # 🔧 核心引擎测试
├── api_integration/        # 🌐 API和集成测试  
├── security/              # 🔒 安全和合规测试
├── analysis_tools/        # 📊 分析工具测试
├── specialized/           # 🎯 专项功能测试
├── README.md             # 详细使用指南
├── USAGE.md              # 快速参考指南
└── __init__.py           # 测试套件索引
```

## 📂 各子目录详细说明

### 🔧 core_engines/ - 核心引擎测试
- **test_analysis_engine.py** - 分析引擎测试，包括趋势识别、异常检测、跨模型比较和模式识别
- **test_metrics_engine.py** - 指标引擎测试，涵盖标准NLP指标、代码质量指标、功能指标和多轮对话指标
- **test_prompt_engine.py** - 智能提示引擎测试，包括上下文感知提示生成、模型特定适配、模板系统和A/B测试框架
- **test_visualization_engine.py** - 可视化引擎测试，包括交互式图表、性能仪表板、比较可视化和可导出报告

### 🌐 api_integration/ - API和集成测试
- **test_api_minimal.py** - API网关最小化测试，验证基本结构和功能
- **test_api_basic.py** - API基础功能测试
- **test_api_gateway.py** - API网关完整测试
- **test_integration.py** - 集成测试，验证lm-eval集成和基础功能
- **test_lm_eval_integration.py** - lm-eval集成专项测试

### 🔒 security/ - 安全和合规测试
- **test_security_basic.py** - 基础安全功能测试
- **test_security_framework.py** - 完整安全框架测试，包括漏洞扫描、加密管理、审计日志、事件检测、合规管理和访问控制

### 📊 analysis_tools/ - 分析工具测试
- **test_analysis_tools.py** - 单轮场景分析工具测试
- **test_analysis_tools_documentation.py** - 分析工具文档测试
- **test_analysis_visualization_integration.py** - 分析可视化集成测试
- **test_fixed_analysis_tools.py** - 修复后的分析工具测试

### 🎯 specialized/ - 专项功能测试
- **test_advanced_model_config.py** - 高级模型配置测试
- **test_concrete_model_adapters.py** - 具体模型适配器测试
- **test_composite_metrics.py** - 复合指标测试
- **test_single_turn_simple.py** - 简单单轮测试
- **test_task_2_implementation.py** - 任务2实现测试

## 🚀 快速开始

### 运行所有测试
```bash
# 在项目根目录下运行
python -m pytest evaluation_engine/tests/ -v
```

### 按目录运行测试

#### 核心引擎测试
```bash
python -m pytest evaluation_engine/tests/core_engines/ -v
```

#### API和集成测试
```bash
python -m pytest evaluation_engine/tests/api_integration/ -v
```

#### 安全测试
```bash
python -m pytest evaluation_engine/tests/security/ -v
```

#### 分析工具测试
```bash
python -m pytest evaluation_engine/tests/analysis_tools/ -v
```

#### 专项功能测试
```bash
python -m pytest evaluation_engine/tests/specialized/ -v
```

## 📋 测试详细说明

### core_engines/test_analysis_engine.py
**功能**: 测试统计分析能力
- 趋势识别和分析
- 异常检测算法
- 跨模型性能比较
- 模式识别功能

**运行方式**:
```bash
python evaluation_engine/tests/core_engines/test_analysis_engine.py
```

### core_engines/test_metrics_engine.py
**功能**: 测试综合指标计算能力
- 标准NLP指标 (BLEU, ROUGE, BERTScore等)
- 代码质量指标
- 功能性指标
- 多轮对话指标

**运行方式**:
```bash
python evaluation_engine/tests/core_engines/test_metrics_engine.py
```

### core_engines/test_prompt_engine.py
**功能**: 测试智能提示引擎
- 上下文感知提示生成
- 模型特定适配
- 模板系统和条件逻辑
- A/B测试框架
- 提示优化算法

**运行方式**:
```bash
python -m pytest evaluation_engine/tests/core_engines/test_prompt_engine.py -v
```

### core_engines/test_visualization_engine.py
**功能**: 测试可视化引擎
- 交互式图表生成
- 性能仪表板
- 比较可视化
- 多格式报告导出

**运行方式**:
```bash
python evaluation_engine/tests/core_engines/test_visualization_engine.py
```

### api_integration/test_api_minimal.py
**功能**: API网关最小化验证
- 文件结构验证
- 基础功能测试
- 无外部依赖测试

**运行方式**:
```bash
python evaluation_engine/tests/api_integration/test_api_minimal.py
```

### api_integration/test_integration.py
**功能**: 集成测试
- lm-eval集成验证
- 核心组件导入测试
- 基础功能验证

**运行方式**:
```bash
python evaluation_engine/tests/api_integration/test_integration.py
```

### security/test_security_framework.py
**功能**: 完整安全框架测试
- 漏洞扫描系统
- 加密管理
- 审计日志记录
- 安全事件检测
- 合规性管理
- 访问控制系统

**运行方式**:
```bash
python -m pytest evaluation_engine/tests/security/test_security_framework.py -v
```

### api_integration/test_lm_eval_integration.py
**功能**: lm-eval集成专项测试
- 基础lm-eval功能验证
- 任务管理器测试
- 任务加载验证

**运行方式**:
```bash
python evaluation_engine/tests/api_integration/test_lm_eval_integration.py
```

## 🔧 测试环境配置

### 依赖安装
```bash
pip install -r requirements_api.txt
pip install pytest pytest-asyncio
```

### 环境变量
某些测试可能需要特定的环境变量：
```bash
export PYTHONPATH="${PYTHONPATH}:."
export TEST_ENV=development
```

## 📊 测试报告

### 生成测试报告
```bash
python -m pytest evaluation_engine/tests/ --html=test_report.html --self-contained-html
```

### 覆盖率报告
```bash
pip install pytest-cov
python -m pytest evaluation_engine/tests/ --cov=evaluation_engine --cov-report=html
```

## 🐛 故障排除

### 常见问题

1. **导入错误**: 确保PYTHONPATH包含项目根目录
2. **依赖缺失**: 运行 `pip install -r requirements_api.txt`
3. **权限问题**: 确保有足够的文件系统权限
4. **端口冲突**: API测试可能需要特定端口，确保端口可用

### 调试模式
```bash
python -m pytest evaluation_engine/tests/ -v -s --tb=long
```

## 📈 持续集成

这些测试可以集成到CI/CD流水线中：

```yaml
# .github/workflows/test.yml 示例
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    - name: Install dependencies
      run: pip install -r requirements_api.txt
    - name: Run tests
      run: python -m pytest evaluation_engine/tests/ -v
```

## 📝 贡献指南

添加新测试时请遵循以下规范：
1. 文件命名: `test_<component_name>.py`
2. 包含详细的docstring说明测试目的
3. 使用适当的断言和错误处理
4. 添加到本README的相应部分

## 📞 支持

如有问题或建议，请：
1. 查看现有测试文件的实现
2. 检查项目文档
3. 提交issue或pull request