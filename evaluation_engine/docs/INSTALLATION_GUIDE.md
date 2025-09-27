# AI Evaluation Engine 安装和使用指南

## 🎯 概述

本指南提供了AI Evaluation Engine的完整安装、配置和使用流程。所有命令都经过实际测试验证，确保可以正常运行并产生有效的分析报告。

## 📁 文件说明

### 安装和验证文件
- **`quick_setup.sh`** - 一键安装脚本，自动设置完整环境
- **`quick_verify.py`** - 安装验证脚本，检查所有组件是否正常
- **`demo_quick_start.py`** - 快速演示脚本，展示完整评估流程

### 使用文档
- **`user_menu.md`** - 完整用户菜单，包含所有可用命令
- **`README.md`** - 文档结构说明
- **`INSTALLATION_GUIDE.md`** - 本安装指南

## 🚀 快速开始

### 第一步：运行一键安装
```bash
# 给脚本添加执行权限（如果需要）
chmod +x evaluation_engine/docs/quick_setup.sh

# 运行一键安装
bash evaluation_engine/docs/quick_setup.sh
```

安装脚本会自动：
- 检查Python版本（需要3.9+）
- 检查Docker可用性
- 创建虚拟环境
- 安装所有依赖包
- 设置配置文件
- 创建必要的目录结构
- 运行基础测试

### 第二步：配置API密钥
编辑 `.env` 文件，添加您的API密钥：
```bash
# 编辑环境配置文件
nano .env

# 或者直接设置环境变量
export ANTHROPIC_API_KEY="your_anthropic_key_here"
export OPENAI_API_KEY="your_openai_key_here"
export DEEPSEEK_API_KEY="your_deepseek_key_here"
export DASHSCOPE_API_KEY="your_dashscope_key_here"
```

### 第三步：验证安装
```bash
# 激活虚拟环境
source venv/bin/activate

# 运行验证脚本
python evaluation_engine/docs/quick_verify.py
```

验证脚本会检查：
- Python环境和虚拟环境
- 关键依赖包安装
- API密钥配置
- 任务注册状态
- 基础功能测试
- 分析工具可用性

### 第四步：运行快速演示
```bash
# 运行快速演示
python evaluation_engine/docs/demo_quick_start.py
```

演示脚本会：
- 自动选择可用的模型
- 运行实际的评估任务
- 生成结果文件
- 展示分析工具功能
- 显示后续使用步骤

## 📊 验证成功标准

### 安装成功标志
- ✅ Python 3.9+ 版本检查通过
- ✅ 虚拟环境创建成功
- ✅ 所有依赖包安装完成
- ✅ 配置文件创建成功
- ✅ 基础功能测试通过

### 验证成功标志
- ✅ 至少1个API密钥配置成功
- ✅ 找到18个single_turn_scenarios任务
- ✅ Dummy模型测试通过
- ✅ API模型测试通过（如果有API密钥）
- ✅ 4个分析工具全部可用

### 演示成功标志
- ✅ 评估任务成功运行
- ✅ 生成结果文件（JSON格式）
- ✅ 生成样本文件（JSONL格式）
- ✅ 分析工具成功初始化
- ✅ 显示结果摘要和样本示例

## 🔧 实际可用的命令

### 基础评估命令（已测试）
```bash
# 函数生成任务
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation --limit 5 \
  --output_path results/function_gen_test.json

# 代码补全任务
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_code_completion --limit 5 \
  --output_path results/code_completion_test.json

# 批量任务评估
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation,single_turn_scenarios_code_completion \
  --limit 5 --output_path results/batch_test.json --log_samples
```

### 分析工具命令（已测试）
```bash
# 测试分析工具
python evaluation_engine/tests/analysis_tools/test_analysis_tools.py

# 演示分析工具
python demo_analysis_tools.py

# 运行完整演示
python demo_single_turn_scenarios.py
```

### 测试套件命令（已测试）
```bash
# 运行所有测试
python -m pytest evaluation_engine/tests/ -v

# 运行分析工具测试
python -m pytest evaluation_engine/tests/analysis_tools/ -v

# 运行专项功能测试
python -m pytest evaluation_engine/tests/specialized/ -v
```

## 📈 实际输出示例

### 评估结果文件结构
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
    "batch_size": 1,
    "limit": 5.0
  },
  "versions": {
    "single_turn_scenarios_function_generation": 1.0
  }
}
```

### 样本文件结构
```json
{"doc": {"id": "func_001", "prompt": "Write a function to..."}, "resps": [["def solution():\n    # Generated code\n    pass"]], "filtered_resps": ["def solution():\n    # Generated code\n    pass"]}
```

### 分析工具输出
```
🔍 分析工具测试完成，4/4 个工具可用
✅ ScenarioAnalyzer - 初始化成功
✅ ModelComparator - 初始化成功  
✅ ContextAnalyzer - 初始化成功
✅ ReportGenerator - 初始化成功
```

## 🔍 故障排除

### 常见问题及解决方案

#### 1. Python版本问题
```bash
# 错误：Python版本过低
# 解决：安装Python 3.9+
brew install python@3.9  # macOS
sudo apt install python3.9  # Ubuntu
```

#### 2. 虚拟环境问题
```bash
# 错误：虚拟环境创建失败
# 解决：手动创建虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

#### 3. 依赖安装问题
```bash
# 错误：依赖安装失败
# 解决：手动安装依赖
pip install -e ".[dev,api,testing,evaluation_engine]"
pip install -r requirements_api.txt
```

#### 4. 任务未找到
```bash
# 错误：Task 'single_turn_scenarios_function_generation' not found
# 解决：检查当前目录和任务注册
pwd  # 确保在项目根目录
python -m lm_eval --tasks list | grep single_turn_scenarios
```

#### 5. API密钥问题
```bash
# 错误：API key not found
# 解决：检查环境变量设置
echo $ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY="your_key_here"
```

#### 6. 输出路径问题
```bash
# 错误：Specify --output_path if providing --predict_only
# 解决：添加输出路径参数
python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation \
  --limit 1 --predict_only --output_path results/test
```

### 调试命令
```bash
# 详细调试模式
python -m lm_eval --model claude-local --tasks single_turn_scenarios_function_generation \
  --limit 1 --verbosity DEBUG --output_path results/debug_test

# 检查任务配置
python -c "
from lm_eval.tasks import TaskManager
tm = TaskManager()
task = tm.load_task_or_group('single_turn_scenarios_function_generation')
print(list(task.keys()))
"

# 检查模型可用性
python -c "
from lm_eval.models import get_model
model = get_model('claude-local')
print('Model loaded successfully')
"
```

## 📋 完整工作流程

### 标准使用流程
1. **安装**: `bash evaluation_engine/docs/quick_setup.sh`
2. **配置**: 编辑 `.env` 文件添加API密钥
3. **验证**: `python evaluation_engine/docs/quick_verify.py`
4. **演示**: `python evaluation_engine/docs/demo_quick_start.py`
5. **使用**: 参考 `user_menu.md` 中的详细命令

### 开发测试流程
1. **运行测试**: `python -m pytest evaluation_engine/tests/ -v`
2. **分析工具**: `python demo_analysis_tools.py`
3. **完整演示**: `python demo_single_turn_scenarios.py`
4. **自定义评估**: 按需修改参数和任务

## 📞 获取帮助

### 文档资源
- `user_menu.md` - 完整命令参考
- `evaluation_engine/tests/README.md` - 测试套件说明
- `evaluation_engine/tests/analysis_tools/USAGE.md` - 分析工具详细说明

### 在线帮助
```bash
python -m lm_eval --help
python -m lm_eval --tasks list
python -m lm_eval --model list
```

### 社区支持
- 查看项目README.md
- 检查现有的issue和文档
- 运行测试套件确认功能状态

---

**重要提示**: 本指南中的所有命令和示例都经过实际测试验证，在正确安装和配置的环境中可以正常运行并产生有效的分析报告。如果遇到问题，请按照故障排除部分的建议进行检查和修复。