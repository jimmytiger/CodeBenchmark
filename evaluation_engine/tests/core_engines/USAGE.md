# 核心引擎测试使用指南

## 🔧 测试文件概览

| 测试文件 | 功能描述 | 主要测试内容 |
|---------|----------|-------------|
| test_analysis_engine.py | 分析引擎测试 | 趋势识别、异常检测、跨模型比较、模式识别 |
| test_metrics_engine.py | 指标引擎测试 | NLP指标、代码质量指标、功能指标、多轮对话指标 |
| test_prompt_engine.py | 提示引擎测试 | 上下文感知生成、模型适配、模板系统、A/B测试 |
| test_visualization_engine.py | 可视化引擎测试 | 交互图表、性能仪表板、比较可视化、报告导出 |

## 🚀 快速运行

### 运行所有核心引擎测试
```bash
python -m pytest evaluation_engine/tests/core_engines/ -v
```

### 运行单个测试文件
```bash
# 分析引擎测试
python evaluation_engine/tests/core_engines/test_analysis_engine.py

# 指标引擎测试  
python evaluation_engine/tests/core_engines/test_metrics_engine.py

# 提示引擎测试
python -m pytest evaluation_engine/tests/core_engines/test_prompt_engine.py -v

# 可视化引擎测试
python evaluation_engine/tests/core_engines/test_visualization_engine.py
```

## 📊 详细测试说明

### test_analysis_engine.py
**核心功能测试**:
- 趋势分析算法验证
- 异常检测准确性测试
- 跨模型性能比较功能
- 统计模式识别能力

**运行示例**:
```bash
python evaluation_engine/tests/core_engines/test_analysis_engine.py
```

### test_metrics_engine.py
**指标计算测试**:
- 标准NLP指标 (BLEU, ROUGE, BERTScore)
- 代码质量评估指标
- 功能性评估指标
- 多轮对话评估指标

**运行示例**:
```bash
python evaluation_engine/tests/core_engines/test_metrics_engine.py
```

### test_prompt_engine.py
**智能提示测试**:
- 上下文感知提示生成
- 模型特定适配策略
- 模板系统和条件逻辑
- A/B测试框架验证
- 提示优化算法测试

**运行示例**:
```bash
python -m pytest evaluation_engine/tests/core_engines/test_prompt_engine.py -v
```

### test_visualization_engine.py
**可视化功能测试**:
- 交互式图表生成
- 实时性能仪表板
- 多维度比较可视化
- 多格式报告导出

**运行示例**:
```bash
python evaluation_engine/tests/core_engines/test_visualization_engine.py
```

## 🔧 测试配置

### 环境要求
```bash
pip install -r requirements_api.txt
export PYTHONPATH="${PYTHONPATH}:."
```

### 调试模式
```bash
python -m pytest evaluation_engine/tests/core_engines/ -v -s --tb=long
```

### 生成报告
```bash
python -m pytest evaluation_engine/tests/core_engines/ --html=core_engines_report.html
```