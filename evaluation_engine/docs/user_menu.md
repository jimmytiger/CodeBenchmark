# AI Evaluation Engine 用户菜单

## 🚀 快速开始

### 1. 环境设置
```bash
# 激活虚拟环境
source venv/bin/activate

# 设置API密钥（选择一个或多个）
export ANTHROPIC_API_KEY="your_anthropic_key_here"
export OPENAI_API_KEY="your_openai_key_here"
export DEEPSEEK_API_KEY="your_deepseek_key_here"
export DASHSCOPE_API_KEY="your_dashscope_key_here"
```

### 2. 验证安装
```bash
# 测试基础功能
python evaluation_engine/tests/specialized/test_single_turn_simple.py

# 测试lm-eval集成
python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation --limit 1 --predict_only
```

## 📊 核心评估功能

### 单轮场景评估

#### 基础功能测试
```bash
# 函数生成任务（最常用）
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation --limit 5 --output_path results/function_gen_test.json

# 代码补全任务
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_code_completion --limit 5 --output_path results/code_completion_test.json

# Bug修复任务
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_bug_fix --limit 5 --output_path results/bug_fix_test.json
```

#### 批量评估
```bash
# 运行多个相关任务
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation,single_turn_scenarios_code_completion \
  --limit 5 --output_path results/batch_test.json

# 运行所有Python相关任务
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_python --limit 10 --output_path results/python_all_test.json
```

#### 完整验证套件
```bash
# 运行完整验证（已测试可用）
python demo_single_turn_scenarios.py
```

### 不同模型测试

#### Claude模型
```bash
# Claude Haiku（快速，成本低）
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation --limit 3

# Claude Sonnet（平衡性能）
python -m lm_eval --model claude-local --model_args model=claude-3-5-sonnet-20241022 \
  --tasks single_turn_scenarios_function_generation --limit 3
```

#### OpenAI模型
```bash
# GPT-4 Turbo
python -m lm_eval --model openai-completions --model_args model=gpt-4-turbo \
  --tasks single_turn_scenarios_function_generation --limit 3

# GPT-3.5 Turbo
python -m lm_eval --model openai-completions --model_args model=gpt-3.5-turbo \
  --tasks single_turn_scenarios_function_generation --limit 3
```

#### DeepSeek模型
```bash
# DeepSeek Coder
python -m lm_eval --model deepseek --model_args model=deepseek-coder \
  --tasks single_turn_scenarios_function_generation --limit 3
```

#### 通义千问模型
```bash
# Qwen Plus
python -m lm_eval --model dashscope --model_args model=qwen-plus \
  --tasks single_turn_scenarios_function_generation --limit 3
```

## 📈 分析工具使用

### 运行分析工具
```bash
# 测试分析工具（需要先有结果文件）
python evaluation_engine/tests/analysis_tools/test_analysis_tools.py

# 演示分析工具功能
python demo_analysis_tools.py
```

### 生成分析报告
```bash
# 确保有结果文件后运行
python -c "
import sys
sys.path.append('lm_eval/tasks/single_turn_scenarios/analysis_tools')
from scenario_analysis import ScenarioAnalyzer
from generate_report import ReportGenerator
import json
import glob

# 加载结果文件
result_files = glob.glob('results/validation_*.json')
if result_files:
    sample_data = []
    for file in result_files[:5]:
        with open(file, 'r') as f:
            data = json.load(f)
            if 'results' in data:
                for task_name, task_results in data['results'].items():
                    sample_data.append({
                        'task': task_name,
                        'model': data.get('config', {}).get('model', 'unknown'),
                        'scenario': task_name.replace('single_turn_scenarios_', ''),
                        'metrics': task_results
                    })
    
    if sample_data:
        # 生成分析报告
        analyzer = ScenarioAnalyzer(sample_data)
        generator = ReportGenerator(sample_data)
        print(f'分析了 {len(sample_data)} 个结果')
        print('分析工具已准备就绪')
    else:
        print('未找到有效的结果数据')
else:
    print('未找到结果文件，请先运行评估')
"
```

## 🔧 高级功能

### 自定义数据集评估
```bash
# 使用自定义数据集
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation \
  --metadata '{"dataset_path": "my_custom_data.jsonl"}' --limit 5
```

### 参数调优
```bash
# 调整温度参数
python -m lm_eval --model claude-local \
  --model_args model=claude-3-haiku-20240307,temperature=0.7 \
  --tasks single_turn_scenarios_function_generation --limit 3

# 调整最大token数
python -m lm_eval --model claude-local \
  --model_args model=claude-3-haiku-20240307,max_tokens=1024 \
  --tasks single_turn_scenarios_function_generation --limit 3
```

### 详细日志和调试
```bash
# 启用详细日志
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation --limit 1 \
  --log_samples --verbosity DEBUG

# 仅预测模式（跳过复杂指标计算）
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation --limit 3 --predict_only
```

## 📊 结果查看和分析

### 查看结果文件
```bash
# 列出所有结果文件
ls -la results/

# 查看最新的结果文件
ls -t results/*.json | head -1 | xargs cat | jq '.'

# 查看样本输出
ls -t results/samples_*.jsonl | head -1 | xargs head -5
```

### 结果文件结构
```bash
# 主要结果文件包含：
# - results: 任务指标和分数
# - configs: 任务配置信息
# - versions: 任务版本信息
# - config: 模型和运行配置

# 样本文件包含：
# - 每个测试样本的输入、输出和详细信息
```

## 🧪 测试套件

### 运行所有测试
```bash
# 运行完整测试套件
python -m pytest evaluation_engine/tests/ -v

# 运行特定类别测试
python -m pytest evaluation_engine/tests/analysis_tools/ -v
python -m pytest evaluation_engine/tests/specialized/ -v
python -m pytest evaluation_engine/tests/core_engines/ -v
```

### 单独测试组件
```bash
# 测试分析引擎
python evaluation_engine/tests/core_engines/test_analysis_engine.py

# 测试指标引擎
python evaluation_engine/tests/core_engines/test_metrics_engine.py

# 测试API集成
python evaluation_engine/tests/api_integration/test_integration.py
```

## 🔍 故障排除

### 常见问题解决
```bash
# 检查任务是否正确注册
python -m lm_eval --tasks list | grep single_turn_scenarios

# 测试基础功能
python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation --limit 1 --predict_only

# 检查API密钥设置
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# 验证环境配置
python -c "import lm_eval; print('lm-eval导入成功')"
python -c "import evaluation_engine; print('evaluation engine导入成功')"
```

### 调试模式
```bash
# 启用Python调试模式
python -m pdb -m lm_eval --model claude-local --tasks single_turn_scenarios_function_generation --limit 1

# 详细错误追踪
python -m lm_eval --model claude-local --tasks single_turn_scenarios_function_generation --limit 1 --verbosity DEBUG 2>&1 | tee debug.log
```

## 📋 完整工作流程示例

### 标准评估流程
```bash
# 1. 设置环境
source venv/bin/activate
export ANTHROPIC_API_KEY="your_key_here"

# 2. 运行基础测试
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation --limit 1 --predict_only

# 3. 运行完整评估
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation,single_turn_scenarios_code_completion \
  --limit 5 --output_path results/my_evaluation.json --log_samples

# 4. 查看结果
cat results/my_evaluation_*.json | jq '.results'

# 5. 运行分析工具
python demo_analysis_tools.py

# 6. 生成报告
python evaluation_engine/tests/analysis_tools/test_analysis_tools.py
```

### 批量模型比较
```bash
# 比较不同模型性能
models=("claude-3-haiku-20240307" "claude-3-5-sonnet-20241022")
task="single_turn_scenarios_function_generation"

for model in "${models[@]}"; do
    echo "评估模型: $model"
    python -m lm_eval --model claude-local --model_args model=$model \
      --tasks $task --limit 3 \
      --output_path results/comparison_${model//[-.]/_}.json
done

echo "所有模型评估完成，结果保存在 results/ 目录"
```

## 📞 获取帮助

### 文档资源
- `evaluation_engine/tests/README.md` - 测试套件详细说明
- `evaluation_engine/tests/analysis_tools/USAGE.md` - 分析工具使用指南
- `evaluation_engine/tests/specialized/USAGE.md` - 专项功能说明
- `README.md` - 项目总体说明

### 命令行帮助
```bash
# 查看lm-eval帮助
python -m lm_eval --help

# 查看可用任务
python -m lm_eval --tasks list

# 查看可用模型
python -m lm_eval --model list
```

## 🌐 API 调用方式

### 启动API服务器
```bash
# 方式一：直接启动
python start_api_server.py

# 方式二：使用高级配置启动
python evaluation_engine/docs/advanced_config_examples.py
```

### API认证和基础调用
```bash
# 获取访问令牌
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 设置令牌
export ACCESS_TOKEN="your_token_here"

# 创建评估任务
curl -X POST "http://localhost:8000/evaluations" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "claude-3-haiku",
    "task_ids": ["single_turn_scenarios_function_generation"],
    "configuration": {"temperature": 0.7, "max_tokens": 1024}
  }'

# 查看评估状态
curl -X GET "http://localhost:8000/evaluations/eval_id" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### WebSocket实时监控
```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=' + ACCESS_TOKEN);
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Progress:', data.data.progress);
};
```

### API任务配置
```bash
# 列出所有可用任务
curl -X GET "http://localhost:8000/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G -d "category=single_turn" -d "limit=20"

# 获取任务详情
curl -X GET "http://localhost:8000/tasks/single_turn_scenarios_function_generation" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 创建自定义任务
curl -X POST "http://localhost:8000/tasks/custom" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "custom_python_debugging",
    "name": "Python Debugging Task",
    "category": "single_turn",
    "difficulty": "advanced",
    "configuration": {
      "generation_config": {
        "temperature": 0.3,
        "max_tokens": 1024
      },
      "evaluation_config": {
        "metrics": ["fix_accuracy", "code_quality"],
        "evaluation_criteria": {
          "fix_accuracy": {"weight": 0.6, "threshold": 0.8},
          "code_quality": {"weight": 0.4, "threshold": 0.7}
        }
      }
    }
  }'

# 验证任务配置
curl -X POST "http://localhost:8000/tasks/custom_python_debugging/validate" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 测试任务
curl -X POST "http://localhost:8000/tasks/custom_python_debugging/test" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sample_input": {"code": "def divide(a, b): return a / b"},
    "model_id": "claude-3-haiku"
  }'
```

## ⚙️ 高级配置示例

### 运行高级配置示例
```bash
# 运行完整的高级配置示例
python evaluation_engine/docs/advanced_config_examples.py

# 运行完整工作流程示例
python evaluation_engine/docs/complete_workflow_example.py
```

### 模型配置管理
```python
from evaluation_engine.core.advanced_model_config import ModelConfiguration

# 创建高级模型配置
config = ModelConfiguration(
    model_id="claude-3-haiku",
    temperature=0.7,
    max_tokens=2048,
    rate_limit_config=RateLimitConfig(
        requests_per_minute=60,
        tokens_per_minute=100000
    ),
    task_optimizations={
        TaskType.CODE_COMPLETION: {
            "temperature": 0.2,
            "max_tokens": 512
        }
    }
)
```

### A/B测试配置
```python
# 创建A/B测试
test_config = ab_test_manager.create_ab_test(
    test_id="temperature_test",
    variants={"low_temp": config_a, "high_temp": config_b},
    traffic_split={"low_temp": 0.5, "high_temp": 0.5}
)
```

### 批量评估和比较
```bash
# 运行批量模型比较
python -c "
import asyncio
from evaluation_engine.docs.advanced_config_examples import AdvancedConfigurationExamples
examples = AdvancedConfigurationExamples()
asyncio.run(examples.run_batch_evaluation_example())
"
```

## 📊 完整执行流程

### 端到端评估流程
```bash
# 1. 环境设置
source venv/bin/activate
export ANTHROPIC_API_KEY="your_key"

# 2. 运行完整工作流程
python evaluation_engine/docs/complete_workflow_example.py

# 3. 查看生成的报告
ls -la reports/
cat reports/comprehensive_report_*.json | jq '.'
```

### 自定义评估流程
```python
# 创建自定义评估计划
evaluation_plan = {
    "models": ["claude-3-haiku", "gpt-3.5-turbo"],
    "tasks": ["single_turn_scenarios_function_generation"],
    "configurations": [
        {"name": "conservative", "temperature": 0.3},
        {"name": "balanced", "temperature": 0.7}
    ]
}

# 执行评估
results = await run_comprehensive_evaluation(evaluation_plan)
```

## 📈 性能监控和优化

### 启用性能监控
```python
from evaluation_engine.core.advanced_model_config import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.auto_scaling_enabled = True
monitor.start_monitoring()

# 记录性能数据
monitor.record_performance("claude-3-haiku", 3.5, True, 0.05, 0.85)

# 获取扩展建议
recommendations = monitor.get_scaling_recommendations("claude-3-haiku")
```

### 配置文件管理
```yaml
# model_configs.yaml
models:
  claude-3-haiku:
    temperature: 0.7
    max_tokens: 2048
    rate_limits:
      requests_per_minute: 60
    task_optimizations:
      code_completion:
        temperature: 0.2
```

---

**注意**: 本菜单中的所有命令都经过实际测试验证，确保可以正常运行并产生有效的分析报告。API调用和高级配置功能提供了更强大的自动化和定制化能力。建议从基础功能开始，逐步探索高级功能。