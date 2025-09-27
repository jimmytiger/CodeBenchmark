# 分析工具测试使用指南

## 📊 测试文件概览

| 测试文件 | 功能描述 | 主要测试内容 |
|---------|----------|-------------|
| test_analysis_tools.py | 分析工具核心测试 | 单轮场景分析工具功能验证 |
| test_analysis_tools_documentation.py | 分析工具文档测试 | 文档完整性和准确性验证 |
| test_analysis_visualization_integration.py | 分析可视化集成测试 | 分析结果可视化集成功能 |
| test_fixed_analysis_tools.py | 修复后分析工具测试 | 修复版本的分析工具验证 |

## 🚀 快速运行

### 运行所有分析工具测试
```bash
python -m pytest evaluation_engine/tests/analysis_tools/ -v
```

### 运行单个测试文件
```bash
# 分析工具核心测试
python evaluation_engine/tests/analysis_tools/test_analysis_tools.py

# 分析工具文档测试
python -m pytest evaluation_engine/tests/analysis_tools/test_analysis_tools_documentation.py -v

# 分析可视化集成测试
python -m pytest evaluation_engine/tests/analysis_tools/test_analysis_visualization_integration.py -v

# 修复后分析工具测试
python evaluation_engine/tests/analysis_tools/test_fixed_analysis_tools.py
```

## 📊 详细测试说明

### test_analysis_tools.py
**分析工具核心功能测试**:
- 单轮场景数据分析
- 结果文件处理和解析
- 样本数据分析验证
- 分析工具API接口测试

**测试数据要求**:
- 需要 `results/validation_*.json` 文件
- 需要 `results/samples_*.jsonl` 文件

**运行示例**:
```bash
python evaluation_engine/tests/analysis_tools/test_analysis_tools.py
```

### test_analysis_tools_documentation.py
**文档完整性测试**:
- API文档完整性检查
- 使用示例验证
- 参数说明准确性
- 返回值格式验证

**运行示例**:
```bash
python -m pytest evaluation_engine/tests/analysis_tools/test_analysis_tools_documentation.py -v
```

### test_analysis_visualization_integration.py
**可视化集成功能测试**:
- 分析结果可视化生成
- 图表数据准确性验证
- 多种图表类型支持
- 交互式可视化功能

**运行示例**:
```bash
python -m pytest evaluation_engine/tests/analysis_tools/test_analysis_visualization_integration.py -v
```

### test_fixed_analysis_tools.py
**修复版本验证测试**:
- 修复后功能正确性验证
- 回归测试确保无新问题
- 性能改进验证
- 兼容性测试

**运行示例**:
```bash
python evaluation_engine/tests/analysis_tools/test_fixed_analysis_tools.py
```

## 🔧 测试配置

### 环境要求
```bash
pip install -r requirements_api.txt
pip install matplotlib seaborn plotly  # 可视化依赖
export PYTHONPATH="${PYTHONPATH}:."
```

### 测试数据准备
```bash
# 确保有测试数据文件
mkdir -p results/
# 运行验证生成测试数据（如果需要）
python scripts/generate_test_data.py  # 如果存在此脚本
```

### 调试模式
```bash
python -m pytest evaluation_engine/tests/analysis_tools/ -v -s --tb=long
```

### 生成报告
```bash
python -m pytest evaluation_engine/tests/analysis_tools/ --html=analysis_tools_report.html
```

## 📈 分析工具功能说明

### 数据分析功能
- **统计分析**: 描述性统计、分布分析
- **趋势分析**: 时间序列分析、趋势识别
- **比较分析**: 多模型性能对比
- **异常检测**: 异常值识别和分析

### 可视化功能
- **基础图表**: 柱状图、折线图、散点图
- **高级图表**: 热力图、箱线图、小提琴图
- **交互式图表**: 可缩放、可筛选的动态图表
- **报告生成**: PDF、HTML格式的分析报告

### 数据处理功能
- **数据清洗**: 缺失值处理、异常值过滤
- **数据转换**: 格式转换、数据聚合
- **结果导出**: 多种格式的结果导出
- **批量处理**: 大规模数据批量分析

## 🐛 常见问题

| 问题 | 解决方案 |
|------|----------|
| 测试数据文件不存在 | 运行数据生成脚本或手动创建测试数据 |
| 可视化库导入失败 | `pip install matplotlib seaborn plotly` |
| 内存不足错误 | 减少测试数据量或增加系统内存 |
| 图表显示异常 | 检查显示环境和图形后端配置 |

## 📋 测试数据格式

### 结果文件格式 (validation_*.json)
```json
{
  "model": "model_name",
  "task": "task_name",
  "metrics": {
    "accuracy": 0.85,
    "f1_score": 0.82
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 样本文件格式 (samples_*.jsonl)
```json
{"input": "sample input", "output": "sample output", "score": 0.9}
{"input": "another input", "output": "another output", "score": 0.8}
```

## 🎯 测试覆盖范围

- ✅ 核心分析算法
- ✅ 数据处理流程
- ✅ 可视化生成
- ✅ 错误处理机制
- ✅ 性能基准测试
- ✅ 兼容性验证