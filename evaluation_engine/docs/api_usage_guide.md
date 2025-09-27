# AI Evaluation Engine API 使用指南

## 🌐 API 调用方式

### 1. 启动API服务器

#### 方式一：直接启动
```bash
# 激活虚拟环境
source venv/bin/activate

# 启动API服务器
python -c "
from evaluation_engine.api.gateway import APIGateway
from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
from evaluation_engine.core.task_registration import TaskRegistry
from evaluation_engine.core.advanced_model_config import AdvancedModelConfigurationManager
from evaluation_engine.core.analysis_engine import AnalysisEngine

# 初始化组件
framework = UnifiedEvaluationFramework()
task_registry = TaskRegistry()
model_config_manager = AdvancedModelConfigurationManager()
analysis_engine = AnalysisEngine()

# 创建API网关
gateway = APIGateway(framework, task_registry, model_config_manager, analysis_engine)

# 启动服务器
gateway.run(host='0.0.0.0', port=8000)
"
```

#### 方式二：使用配置文件启动
```bash
# 创建启动脚本
cat > start_api_server.py << 'EOF'
#!/usr/bin/env python3
"""
AI Evaluation Engine API Server
"""

import os
import logging
from evaluation_engine.api.gateway import APIGateway
from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
from evaluation_engine.core.task_registration import TaskRegistry
from evaluation_engine.core.advanced_model_config import AdvancedModelConfigurationManager
from evaluation_engine.core.analysis_engine import AnalysisEngine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # 检查环境变量
    required_env_vars = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY', 'DASHSCOPE_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
        logger.info("Some API functionality may be limited")
    
    try:
        # 初始化组件
        logger.info("Initializing evaluation framework...")
        framework = UnifiedEvaluationFramework()
        
        logger.info("Initializing task registry...")
        task_registry = TaskRegistry()
        
        logger.info("Initializing model configuration manager...")
        model_config_manager = AdvancedModelConfigurationManager()
        
        logger.info("Initializing analysis engine...")
        analysis_engine = AnalysisEngine()
        
        # 创建API网关
        logger.info("Creating API gateway...")
        gateway = APIGateway(framework, task_registry, model_config_manager, analysis_engine)
        
        # 启动服务器
        logger.info("Starting API server on http://0.0.0.0:8000")
        logger.info("API documentation available at http://0.0.0.0:8000/docs")
        gateway.run(host='0.0.0.0', port=8000, reload=False)
        
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        raise

if __name__ == "__main__":
    main()
EOF

# 运行启动脚本
python start_api_server.py
```

### 2. API 认证

#### 获取访问令牌
```bash
# 登录获取令牌
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'

# 响应示例
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_here",
  "user_info": {
    "user_id": "admin",
    "username": "admin",
    "roles": ["admin"],
    "permissions": ["evaluation:create", "analytics:read"]
  }
}
```

#### 使用令牌访问API
```bash
# 设置令牌变量
export ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 使用令牌访问API
curl -X GET "http://localhost:8000/health" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 3. 基础API调用

#### 系统健康检查
```bash
curl -X GET "http://localhost:8000/health"

# 响应
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "active_evaluations": 0
}
```

#### 列出可用任务
```bash
curl -X GET "http://localhost:8000/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G -d "limit=10" -d "category=single_turn"

# 响应
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
  "page_size": 10
}
```

#### 列出可用模型
```bash
curl -X GET "http://localhost:8000/models" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 响应
[
  {
    "model_id": "claude-3-haiku",
    "name": "Claude 3 Haiku",
    "provider": "anthropic",
    "version": "20240307",
    "capabilities": ["text_generation", "code_completion"],
    "supported_tasks": ["single_turn_scenarios", "multi_turn_scenarios"],
    "rate_limits": {
      "requests_per_minute": 60,
      "tokens_per_minute": 100000
    },
    "cost_per_token": 0.00025
  }
]
```

### 4. 创建和管理评估

#### 创建评估任务
```bash
curl -X POST "http://localhost:8000/evaluations" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "claude-3-haiku",
    "task_ids": [
      "single_turn_scenarios_function_generation",
      "single_turn_scenarios_code_completion"
    ],
    "configuration": {
      "temperature": 0.7,
      "max_tokens": 1024,
      "limit": 5
    },
    "context_mode": "full_context",
    "metadata": {
      "experiment_name": "baseline_test",
      "description": "Baseline performance test"
    }
  }'

# 响应
{
  "evaluation_id": "eval_1234567890_abcd1234",
  "status": "created",
  "message": "Evaluation created successfully",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 查看评估状态
```bash
curl -X GET "http://localhost:8000/evaluations/eval_1234567890_abcd1234" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 响应
{
  "evaluation_id": "eval_1234567890_abcd1234",
  "status": "running",
  "progress": 0.6,
  "current_task": "single_turn_scenarios_code_completion",
  "completed_tasks": 1,
  "total_tasks": 2,
  "start_time": "2024-01-01T12:00:00Z",
  "estimated_completion": "2024-01-01T12:05:00Z",
  "error_message": null
}
```

#### 获取评估结果
```bash
curl -X GET "http://localhost:8000/results/eval_1234567890_abcd1234" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G -d "include_details=true"

# 响应
{
  "evaluation_id": "eval_1234567890_abcd1234",
  "model_id": "claude-3-haiku",
  "task_results": [
    {
      "task_id": "single_turn_scenarios_function_generation",
      "status": "completed",
      "score": 0.85,
      "metrics": {
        "accuracy": 0.8,
        "completeness": 0.9,
        "code_quality": 0.85
      },
      "execution_time": 45.2,
      "output": "Generated function code...",
      "error_message": null
    }
  ],
  "summary_metrics": {
    "overall_score": 0.83,
    "average_execution_time": 42.5
  },
  "completed_at": "2024-01-01T12:04:30Z",
  "execution_time": 270.5
}
```

### 5. WebSocket 实时通信

#### JavaScript WebSocket 客户端
```javascript
// 连接WebSocket
const ws = new WebSocket('ws://localhost:8000/ws?token=' + ACCESS_TOKEN);

// 监听消息
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    
    if (data.type === 'evaluation_progress') {
        updateProgressBar(data.data.progress);
    } else if (data.type === 'evaluation_completed') {
        showResults(data.data.evaluation_id);
    }
};

// 订阅评估更新
ws.onopen = function() {
    ws.send(JSON.stringify({
        type: 'subscribe_evaluation',
        evaluation_id: 'eval_1234567890_abcd1234'
    }));
};

// 错误处理
ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};
```

#### Python WebSocket 客户端
```python
import asyncio
import websockets
import json

async def websocket_client():
    uri = f"ws://localhost:8000/ws?token={ACCESS_TOKEN}"
    
    async with websockets.connect(uri) as websocket:
        # 订阅评估更新
        await websocket.send(json.dumps({
            "type": "subscribe_evaluation",
            "evaluation_id": "eval_1234567890_abcd1234"
        }))
        
        # 监听消息
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")
            
            if data["type"] == "evaluation_completed":
                print(f"Evaluation {data['data']['evaluation_id']} completed!")
                break

# 运行客户端
asyncio.run(websocket_client())
```

## ⚙️ 高级配置

### 1. 模型配置管理

#### 创建高级模型配置
```python
from evaluation_engine.core.advanced_model_config import (
    ModelConfiguration, 
    TaskType, 
    OptimizationStrategy,
    RateLimitConfig
)

# 创建基础配置
base_config = ModelConfiguration(
    model_id="claude-3-haiku",
    model_type=ModelType.ANTHROPIC_CLAUDE,
    
    # 生成参数
    temperature=0.7,
    max_tokens=2048,
    top_p=0.9,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    stop_sequences=["```", "\n\n"],
    
    # API配置
    api_key="your_api_key_here",
    timeout=30.0,
    
    # 速率限制
    rate_limit_config=RateLimitConfig(
        requests_per_minute=60,
        tokens_per_minute=100000,
        concurrent_requests=5
    ),
    
    # 成本管理
    max_cost_per_request=1.0,
    daily_budget=100.0,
    
    # 性能目标
    target_response_time=5.0,
    target_success_rate=0.95
)

# 任务特定优化
base_config.task_optimizations = {
    TaskType.CODE_COMPLETION: {
        "temperature": 0.2,
        "max_tokens": 512,
        "stop_sequences": ["\n\n", "```"]
    },
    TaskType.FUNCTION_GENERATION: {
        "temperature": 0.3,
        "max_tokens": 1024,
        "stop_sequences": ["\n\ndef ", "\n\nclass "]
    },
    TaskType.BUG_FIX: {
        "temperature": 0.1,
        "max_tokens": 1024,
        "top_p": 0.8
    }
}
```

#### 注册和使用配置
```python
from evaluation_engine.core.advanced_model_config import AdvancedModelConfigurationManager

# 创建配置管理器
config_manager = AdvancedModelConfigurationManager()

# 注册配置
config_manager.register_model_configuration("claude-3-haiku", base_config)

# 获取优化配置
optimized_config = config_manager.get_optimized_configuration(
    model_id="claude-3-haiku",
    task_type=TaskType.CODE_COMPLETION,
    optimization_strategy=OptimizationStrategy.PERFORMANCE
)

print(f"Optimized temperature: {optimized_config.temperature}")
print(f"Optimized max_tokens: {optimized_config.max_tokens}")
```

### 2. A/B 测试配置

#### 创建A/B测试
```python
from evaluation_engine.core.advanced_model_config import ABTestManager

# 创建A/B测试管理器
ab_test_manager = ABTestManager()

# 定义测试变体
variant_a = ModelConfiguration(
    model_id="claude-3-haiku",
    temperature=0.3,
    max_tokens=1024
)

variant_b = ModelConfiguration(
    model_id="claude-3-haiku", 
    temperature=0.7,
    max_tokens=1024
)

# 创建A/B测试
test_config = ab_test_manager.create_ab_test(
    test_id="temperature_test_001",
    description="Test different temperature settings for code completion",
    variants={
        "low_temp": variant_a,
        "high_temp": variant_b
    },
    traffic_split={
        "low_temp": 0.5,
        "high_temp": 0.5
    },
    success_metric="quality_score",
    minimum_samples=100,
    confidence_level=0.95,
    max_duration_hours=24
)

# 启动测试
ab_test_manager.start_ab_test("temperature_test_001")

# 在评估中使用A/B测试
variant_name, config = ab_test_manager.select_variant("temperature_test_001")
print(f"Selected variant: {variant_name}")
```

#### 分析A/B测试结果
```python
# 分析测试结果
analysis = ab_test_manager.analyze_ab_test("temperature_test_001")

print(f"Test winner: {analysis['winner']}")
print(f"Statistical significance: {analysis['significant']}")
print(f"Confidence level: {analysis['confidence']}")

for variant, metrics in analysis['variants'].items():
    print(f"\n{variant}:")
    print(f"  Sample size: {metrics['sample_size']}")
    print(f"  Success rate: {metrics['success_rate']:.2%}")
    print(f"  Quality score: {metrics['quality_score']:.3f}")
    print(f"  Performance score: {metrics['performance_score']:.3f}")

# 获取最佳配置
best_config = ab_test_manager.get_best_configuration("temperature_test_001")
if best_config:
    print(f"Best configuration temperature: {best_config.temperature}")
```

### 3. 性能监控和自动扩展

#### 配置性能监控
```python
from evaluation_engine.core.advanced_model_config import PerformanceMonitor

# 创建性能监控器
monitor = PerformanceMonitor()

# 配置扩展阈值
monitor.scaling_thresholds = {
    'response_time_high': 8.0,  # 8秒响应时间阈值
    'error_rate_high': 0.05,    # 5%错误率阈值
    'success_rate_low': 0.9     # 90%成功率阈值
}

# 启用自动扩展
monitor.auto_scaling_enabled = True

# 开始监控
monitor.start_monitoring()

# 记录性能数据
monitor.record_performance(
    model_id="claude-3-haiku",
    response_time=3.5,
    success=True,
    cost=0.05,
    quality=0.85
)

# 获取性能摘要
summary = monitor.get_performance_summary("claude-3-haiku")
print(f"Average response time: {summary['response_time_avg']:.2f}s")
print(f"Success rate: {summary['success_rate']:.2%}")
print(f"Quality score: {summary['quality_score']:.3f}")

# 获取扩展建议
recommendations = monitor.get_scaling_recommendations("claude-3-haiku")
for rec in recommendations:
    print(f"Recommendation: {rec['action']}")
    print(f"Reason: {rec['reason']}")
```

### 4. 完整的评估配置

#### 创建完整的评估请求
```python
from evaluation_engine.core.unified_framework import EvaluationRequest, UnifiedEvaluationFramework

# 创建评估框架
framework = UnifiedEvaluationFramework()

# 创建完整的评估请求
request = EvaluationRequest(
    model="claude-local",
    tasks=[
        "single_turn_scenarios_function_generation",
        "single_turn_scenarios_code_completion",
        "single_turn_scenarios_bug_fix"
    ],
    
    # 基础参数
    limit=10,
    num_fewshot=0,
    batch_size=1,
    device=None,
    
    # 缓存配置
    use_cache=True,
    cache_requests=True,
    rewrite_requests_cache=False,
    delete_requests_cache=False,
    
    # 输出配置
    write_out=True,
    output_base_path="results/api_evaluation",
    log_samples=True,
    show_config=True,
    
    # 生成参数
    gen_kwargs={
        "temperature": 0.7,
        "max_gen_toks": 1024,
        "do_sample": False
    },
    
    # 其他配置
    predict_only=False,
    verbosity="INFO",
    random_seed=42,
    numpy_random_seed=1234,
    torch_random_seed=1234,
    fewshot_random_seed=1234
)

# 执行评估
result = framework.evaluate(request)

print(f"Evaluation ID: {result.evaluation_id}")
print(f"Status: {result.status.value}")
print(f"Execution time: {framework._calculate_execution_time(result):.2f}s")

if result.status.value == "completed":
    print(f"Results: {result.results}")
    print(f"Analysis: {result.analysis}")
```

### 5. 批量评估和比较

#### 批量模型比较
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def batch_evaluation():
    """批量评估多个模型"""
    
    models_to_test = [
        ("claude-local", "model=claude-3-haiku-20240307"),
        ("claude-local", "model=claude-3-5-sonnet-20241022"),
        ("openai-completions", "model=gpt-3.5-turbo"),
        ("deepseek", "model=deepseek-coder")
    ]
    
    tasks = [
        "single_turn_scenarios_function_generation",
        "single_turn_scenarios_code_completion"
    ]
    
    results = {}
    
    # 并行执行评估
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        
        for model, model_args in models_to_test:
            request = EvaluationRequest(
                model=model,
                tasks=tasks,
                limit=5,
                gen_kwargs={"temperature": 0.7, "max_gen_toks": 1024},
                output_base_path=f"results/batch_{model.replace('-', '_')}"
            )
            
            future = executor.submit(framework.evaluate, request)
            futures.append((f"{model}_{model_args}", future))
        
        # 收集结果
        for model_name, future in futures:
            try:
                result = future.result(timeout=300)  # 5分钟超时
                results[model_name] = result
                print(f"✅ {model_name}: {result.status.value}")
            except Exception as e:
                print(f"❌ {model_name}: {e}")
    
    return results

# 运行批量评估
batch_results = asyncio.run(batch_evaluation())

# 比较结果
print("\n📊 模型比较结果:")
print("-" * 60)

for model_name, result in batch_results.items():
    if result.status.value == "completed" and result.metrics_summary:
        avg_score = sum(result.metrics_summary.values()) / len(result.metrics_summary)
        exec_time = framework._calculate_execution_time(result)
        
        print(f"{model_name}:")
        print(f"  平均分数: {avg_score:.3f}")
        print(f"  执行时间: {exec_time:.1f}s")
        print(f"  任务数量: {len(result.request.tasks)}")
        print()
```

## 🔧 配置文件管理

### 1. 创建配置文件

#### 模型配置文件 (model_configs.yaml)
```yaml
models:
  claude-3-haiku:
    model_type: "anthropic_claude"
    api_key: "${ANTHROPIC_API_KEY}"
    temperature: 0.7
    max_tokens: 2048
    top_p: 0.9
    rate_limits:
      requests_per_minute: 60
      tokens_per_minute: 100000
      concurrent_requests: 5
    cost_management:
      max_cost_per_request: 1.0
      daily_budget: 100.0
    performance_targets:
      target_response_time: 5.0
      target_success_rate: 0.95
    task_optimizations:
      code_completion:
        temperature: 0.2
        max_tokens: 512
      function_generation:
        temperature: 0.3
        max_tokens: 1024
      bug_fix:
        temperature: 0.1
        max_tokens: 1024

  gpt-3.5-turbo:
    model_type: "openai_gpt"
    api_key: "${OPENAI_API_KEY}"
    temperature: 0.7
    max_tokens: 2048
    rate_limits:
      requests_per_minute: 60
      tokens_per_minute: 90000
    cost_management:
      max_cost_per_request: 0.5
      daily_budget: 50.0

  deepseek-coder:
    model_type: "deepseek"
    api_key: "${DEEPSEEK_API_KEY}"
    temperature: 0.7
    max_tokens: 2048
    rate_limits:
      requests_per_minute: 100
      tokens_per_minute: 200000
    cost_management:
      max_cost_per_request: 0.1
      daily_budget: 20.0
```

#### 评估配置文件 (evaluation_configs.yaml)
```yaml
evaluations:
  baseline_test:
    description: "Baseline performance evaluation"
    models:
      - "claude-3-haiku"
      - "gpt-3.5-turbo"
    tasks:
      - "single_turn_scenarios_function_generation"
      - "single_turn_scenarios_code_completion"
      - "single_turn_scenarios_bug_fix"
    configuration:
      limit: 10
      num_fewshot: 0
      batch_size: 1
      log_samples: true
      output_base_path: "results/baseline"
    
  performance_comparison:
    description: "Comprehensive performance comparison"
    models:
      - "claude-3-haiku"
      - "claude-3-5-sonnet"
      - "gpt-3.5-turbo"
      - "deepseek-coder"
    tasks:
      - "single_turn_scenarios_python"
    configuration:
      limit: 20
      temperature: 0.7
      max_tokens: 1024
      output_base_path: "results/comparison"

ab_tests:
  temperature_optimization:
    description: "Optimize temperature for code completion"
    base_model: "claude-3-haiku"
    variants:
      low_temp:
        temperature: 0.2
      medium_temp:
        temperature: 0.5
      high_temp:
        temperature: 0.8
    traffic_split:
      low_temp: 0.33
      medium_temp: 0.33
      high_temp: 0.34
    success_metric: "quality_score"
    minimum_samples: 50
    max_duration_hours: 12
```

### 2. 使用配置文件

#### 加载和使用配置
```python
import yaml
import os
from evaluation_engine.core.advanced_model_config import ModelConfiguration

def load_model_configs(config_file: str) -> dict:
    """加载模型配置文件"""
    with open(config_file, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # 替换环境变量
    def replace_env_vars(obj):
        if isinstance(obj, dict):
            return {k: replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            env_var = obj[2:-1]
            return os.getenv(env_var, obj)
        else:
            return obj
    
    return replace_env_vars(config_data)

# 加载配置
config_data = load_model_configs('model_configs.yaml')

# 创建模型配置对象
model_configs = {}
for model_id, config in config_data['models'].items():
    model_configs[model_id] = ModelConfiguration.from_dict({
        'model_id': model_id,
        **config
    })

# 注册配置
config_manager = AdvancedModelConfigurationManager()
for model_id, config in model_configs.items():
    config_manager.register_model_configuration(model_id, config)

print(f"Loaded {len(model_configs)} model configurations")
```

## 📊 完整的执行流程

### 1. 端到端评估流程

```python
#!/usr/bin/env python3
"""
完整的AI评估执行流程示例
"""

import asyncio
import json
import yaml
from datetime import datetime
from pathlib import Path

from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework, EvaluationRequest
from evaluation_engine.core.advanced_model_config import AdvancedModelConfigurationManager
from evaluation_engine.core.task_registration import TaskRegistry

async def complete_evaluation_workflow():
    """完整的评估工作流程"""
    
    print("🚀 开始完整评估流程")
    print("=" * 60)
    
    # 1. 初始化组件
    print("1️⃣ 初始化评估组件...")
    framework = UnifiedEvaluationFramework()
    config_manager = AdvancedModelConfigurationManager()
    task_registry = TaskRegistry()
    
    # 2. 加载配置
    print("2️⃣ 加载模型配置...")
    # 这里可以加载配置文件或使用默认配置
    
    # 3. 定义评估计划
    evaluation_plan = {
        "experiment_name": "comprehensive_evaluation",
        "description": "Comprehensive AI model evaluation",
        "models": [
            {
                "name": "claude-3-haiku",
                "model": "claude-local",
                "model_args": "model=claude-3-haiku-20240307"
            },
            {
                "name": "gpt-3.5-turbo", 
                "model": "openai-completions",
                "model_args": "model=gpt-3.5-turbo"
            }
        ],
        "task_groups": [
            {
                "name": "basic_coding",
                "tasks": [
                    "single_turn_scenarios_function_generation",
                    "single_turn_scenarios_code_completion"
                ]
            },
            {
                "name": "advanced_coding",
                "tasks": [
                    "single_turn_scenarios_bug_fix",
                    "single_turn_scenarios_algorithm_implementation"
                ]
            }
        ],
        "configurations": [
            {
                "name": "conservative",
                "temperature": 0.3,
                "max_tokens": 1024
            },
            {
                "name": "balanced",
                "temperature": 0.7,
                "max_tokens": 1024
            }
        ]
    }
    
    # 4. 执行评估
    print("3️⃣ 执行评估任务...")
    results = {}
    
    for model_info in evaluation_plan["models"]:
        model_name = model_info["name"]
        print(f"\n📊 评估模型: {model_name}")
        
        for task_group in evaluation_plan["task_groups"]:
            group_name = task_group["name"]
            print(f"  📋 任务组: {group_name}")
            
            for config in evaluation_plan["configurations"]:
                config_name = config["name"]
                print(f"    ⚙️ 配置: {config_name}")
                
                # 创建评估请求
                request = EvaluationRequest(
                    model=model_info["model"],
                    tasks=task_group["tasks"],
                    limit=3,  # 限制样本数量以加快演示
                    gen_kwargs={
                        "temperature": config["temperature"],
                        "max_gen_toks": config["max_tokens"]
                    },
                    output_base_path=f"results/{model_name}_{group_name}_{config_name}",
                    log_samples=True,
                    verbosity="INFO"
                )
                
                # 执行评估
                try:
                    result = framework.evaluate(request)
                    
                    # 存储结果
                    result_key = f"{model_name}_{group_name}_{config_name}"
                    results[result_key] = result
                    
                    if result.status.value == "completed":
                        exec_time = framework._calculate_execution_time(result)
                        avg_score = sum(result.metrics_summary.values()) / len(result.metrics_summary) if result.metrics_summary else 0
                        print(f"      ✅ 完成 - 平均分数: {avg_score:.3f}, 时间: {exec_time:.1f}s")
                    else:
                        print(f"      ❌ 失败: {result.error}")
                        
                except Exception as e:
                    print(f"      💥 异常: {e}")
    
    # 5. 生成综合报告
    print("\n4️⃣ 生成综合分析报告...")
    report = generate_comprehensive_report(results, evaluation_plan)
    
    # 6. 保存报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"results/comprehensive_report_{timestamp}.json"
    
    Path("results").mkdir(exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"📄 报告已保存: {report_file}")
    
    # 7. 显示摘要
    print("\n5️⃣ 评估摘要:")
    print("=" * 60)
    display_evaluation_summary(report)
    
    return results, report

def generate_comprehensive_report(results: dict, evaluation_plan: dict) -> dict:
    """生成综合评估报告"""
    
    report = {
        "experiment_info": {
            "name": evaluation_plan["experiment_name"],
            "description": evaluation_plan["description"],
            "timestamp": datetime.now().isoformat(),
            "total_evaluations": len(results)
        },
        "model_performance": {},
        "task_analysis": {},
        "configuration_analysis": {},
        "recommendations": []
    }
    
    # 分析模型性能
    model_scores = {}
    for result_key, result in results.items():
        if result.status.value == "completed" and result.metrics_summary:
            parts = result_key.split('_')
            model_name = parts[0]
            
            if model_name not in model_scores:
                model_scores[model_name] = []
            
            avg_score = sum(result.metrics_summary.values()) / len(result.metrics_summary)
            model_scores[model_name].append(avg_score)
    
    # 计算模型平均性能
    for model_name, scores in model_scores.items():
        report["model_performance"][model_name] = {
            "average_score": sum(scores) / len(scores),
            "best_score": max(scores),
            "worst_score": min(scores),
            "consistency": 1.0 - (max(scores) - min(scores)),  # 简单的一致性指标
            "total_evaluations": len(scores)
        }
    
    # 生成建议
    if model_scores:
        best_model = max(model_scores.keys(), 
                        key=lambda m: sum(model_scores[m]) / len(model_scores[m]))
        report["recommendations"].append(f"最佳整体性能模型: {best_model}")
        
        for model_name, perf in report["model_performance"].items():
            if perf["consistency"] < 0.8:
                report["recommendations"].append(f"{model_name} 性能不够稳定，建议调优参数")
    
    return report

def display_evaluation_summary(report: dict):
    """显示评估摘要"""
    
    print(f"实验名称: {report['experiment_info']['name']}")
    print(f"总评估数: {report['experiment_info']['total_evaluations']}")
    print()
    
    print("📊 模型性能排名:")
    model_perf = report["model_performance"]
    sorted_models = sorted(model_perf.items(), 
                          key=lambda x: x[1]["average_score"], 
                          reverse=True)
    
    for i, (model_name, perf) in enumerate(sorted_models, 1):
        print(f"  {i}. {model_name}")
        print(f"     平均分数: {perf['average_score']:.3f}")
        print(f"     最佳分数: {perf['best_score']:.3f}")
        print(f"     一致性: {perf['consistency']:.3f}")
        print()
    
    print("💡 建议:")
    for rec in report["recommendations"]:
        print(f"  • {rec}")

# 运行完整流程
if __name__ == "__main__":
    results, report = asyncio.run(complete_evaluation_workflow())
    print("\n🎉 评估流程完成！")
```

### 2. 运行完整流程

```bash
# 1. 确保环境已设置
source venv/bin/activate
export ANTHROPIC_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"

# 2. 运行完整评估流程
python complete_evaluation_workflow.py

# 3. 查看结果
ls -la results/
cat results/comprehensive_report_*.json | jq '.'
```

这个完整的指南涵盖了：

1. **API服务器启动和配置**
2. **认证和授权机制**
3. **基础和高级API调用**
4. **WebSocket实时通信**
5. **高级模型配置管理**
6. **A/B测试和性能监控**
7. **批量评估和比较**
8. **配置文件管理**
9. **完整的端到端执行流程**

所有示例都是基于实际的代码结构，可以直接使用和扩展。