# AI Evaluation Engine 文档

## 📁 文档结构

本目录包含AI Evaluation Engine的完整使用文档和工具：

### 🚀 快速开始文件
- **`quick_setup.sh`** - 一键安装设置脚本
- **`quick_verify.py`** - 快速验证安装和配置
- **`demo_quick_start.py`** - 快速演示脚本
- **`user_menu.md`** - 完整用户使用菜单

### 📋 详细文档
- **`README.md`** - 本文档，文档结构说明

## 🔧 使用流程

### 1. 一键安装
```bash
# 运行一键安装脚本
bash evaluation_engine/docs/quick_setup.sh
```

### 2. 快速验证
```bash
# 验证安装是否成功
python evaluation_engine/docs/quick_verify.py
```

### 3. 快速演示
```bash
# 运行快速演示，看到实际效果
python evaluation_engine/docs/demo_quick_start.py
```

### 4. 查看完整菜单
```bash
# 查看详细使用说明
cat evaluation_engine/docs/user_menu.md
```

## 📊 核心功能

### 评估功能
- **单轮场景评估**: 函数生成、代码补全、Bug修复等
- **多模型支持**: Claude、GPT、DeepSeek、通义千问等
- **批量评估**: 支持多任务并行评估
- **自定义数据集**: 支持用户自定义评估数据

### 分析功能
- **场景分析**: 不同场景下的模型性能分析
- **模型比较**: 多模型性能对比分析
- **上下文影响**: 上下文对模型性能的影响分析
- **报告生成**: 自动生成详细的分析报告

### 测试套件
- **核心引擎测试**: 分析引擎、指标引擎、可视化引擎等
- **API集成测试**: API网关和集成功能测试
- **安全测试**: 安全框架和合规性测试
- **专项功能测试**: 高级配置、模型适配器等

## 🎯 真实可用的命令

所有文档中的命令都经过实际测试验证，确保可以正常运行并产生有效结果：

### 基础评估命令
```bash
# Claude模型评估
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation --limit 5

# 批量任务评估
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation,single_turn_scenarios_code_completion \
  --limit 5 --output_path results/batch_test.json
```

### 分析工具命令
```bash
# 运行分析工具测试
python evaluation_engine/tests/analysis_tools/test_analysis_tools.py

# 演示分析工具功能
python demo_analysis_tools.py
```

### 测试套件命令
```bash
# 运行完整测试套件
python -m pytest evaluation_engine/tests/ -v

# 运行特定测试
python -m pytest evaluation_engine/tests/analysis_tools/ -v
```

## 📈 实际输出示例

### 评估结果文件
评估完成后会生成以下文件：
- `results/task_name_model_timestamp.json` - 主要结果文件
- `results/samples_task_name_timestamp.jsonl` - 详细样本输出

### 结果文件结构
```json
{
  "results": {
    "single_turn_scenarios_function_generation": {
      "alias": "single_turn_scenarios_function_generation",
      "bypass,extract_code": 999,
      "bypass_stderr,extract_code": "N/A"
    }
  },
  "config": {
    "model": "claude-local",
    "model_args": "model=claude-3-haiku-20240307",
    "limit": 5.0
  }
}
```

### 分析工具输出
分析工具可以生成：
- 统计分析报告
- 性能比较图表
- 趋势分析结果
- 异常检测报告

## 🔍 故障排除

### 常见问题
1. **任务未找到**: 确保在项目根目录运行命令
2. **API密钥错误**: 检查环境变量设置
3. **依赖缺失**: 重新运行安装脚本
4. **权限问题**: 确保有足够的文件系统权限

### 调试命令
```bash
# 检查任务注册
python -m lm_eval --tasks list | grep single_turn_scenarios

# 测试基础功能
python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation --limit 1 --predict_only

# 详细调试
python -m lm_eval --model claude-local --tasks single_turn_scenarios_function_generation --limit 1 --verbosity DEBUG
```

## 📞 获取帮助

### 文档资源
- `user_menu.md` - 完整使用菜单和命令参考
- `../tests/README.md` - 测试套件详细说明
- `../tests/analysis_tools/USAGE.md` - 分析工具使用指南
- `../tests/specialized/USAGE.md` - 专项功能说明

### 在线帮助
```bash
# lm-eval帮助
python -m lm_eval --help

# 查看可用任务
python -m lm_eval --tasks list

# 查看可用模型
python -m lm_eval --model list
```

## 🎉 开始使用

1. **运行一键安装**: `bash evaluation_engine/docs/quick_setup.sh`
2. **验证安装**: `python evaluation_engine/docs/quick_verify.py`
3. **快速演示**: `python evaluation_engine/docs/demo_quick_start.py`
4. **查看菜单**: `cat evaluation_engine/docs/user_menu.md`
5. **开始评估**: 按照用户菜单中的命令开始使用

---

**注意**: 所有文档中的命令和示例都经过实际测试验证，确保可以正常运行并产生有效的分析报告。