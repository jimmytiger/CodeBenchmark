# AI Evaluation Engine API 完整使用指南

## 🎯 概述

本指南详细介绍如何启动AI Evaluation Engine API服务器，并通过API执行真实的lm-eval评估任务。

## 📋 目录

1. [环境准备](#环境准备)
2. [启动API服务器](#启动api服务器)
3. [API认证](#api认证)
4. [获取可用任务和模型](#获取可用任务和模型)
5. [创建和执行评估任务](#创建和执行评估任务)
6. [监控评估进度](#监控评估进度)
7. [获取评估结果](#获取评估结果)
8. [完整示例](#完整示例)
9. [故障排除](#故障排除)

## 🔧 环境准备

### 1. 安装依赖

```bash
# 安装基础依赖
pip install fastapi uvicorn pydantic PyJWT python-multipart

# 确保lm-eval框架已安装
pip install lm-eval
```

### 2. 配置API密钥（可选）

如果要使用真实的AI模型，需要配置相应的API密钥：

```bash
# 创建.env文件或设置环境变量
export ANTHROPIC_API_KEY="your_anthropic_key"
export OPENAI_API_KEY="your_openai_key"
export DEEPSEEK_API_KEY="your_deepseek_key"
export DASHSCOPE_API_KEY="your_dashscope_key"
```

### 3. 验证环境

```bash
# 验证lm-eval安装
python -m lm_eval --help

# 验证任务可用性
python -c "from lm_eval.tasks import TaskManager; tm = TaskManager(); print(f'可用任务数: {len(tm.all_tasks)}')"
```

## 🚀 启动API服务器

### 方法1：使用真实评估服务器（推荐）

```bash
# 启动真实的API服务器
python real_api_server.py
```

### 方法2：使用简化测试服务器

```bash
# 启动简化版服务器（仅用于测试API接口）
python simple_api_server.py
```

### 服务器启动信息

启动成功后，你会看到类似输出：

```
🚀 启动真实的 AI Evaluation Engine API 服务器
============================================================
🌐 服务器配置:
   - 主机: 0.0.0.0
   - 端口: 8000
   - API文档: http://localhost:8000/docs
   - 健康检查: http://localhost:8000/health
🔐 默认用户账号:
   - 管理员: admin / admin123
   - 评估员: evaluator / eval123
📋 可用任务:
   - single_turn_scenarios_function_generation: Function Generation
   - single_turn_scenarios_code_completion: Code Completion
   - single_turn_scenarios_bug_fix: Bug Fix
   ... 还有 15 个任务
🤖 可用模型:
   - claude-local: Claude (Local)
   - openai-completions: GPT-3.5 Turbo
   - deepseek: DeepSeek Coder
🚀 启动服务器...
```

## 🔐 API认证

### 1. 健康检查（无需认证）

```bash
curl -X GET http://localhost:8000/health
```

响应示例：
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "version": "1.0.0-real",
  "active_evaluations": 0,
  "available_tasks": 18,
  "available_models": 3
}
```

### 2. 用户登录获取访问令牌

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

响应示例：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_info": {
    "user_id": "admin_001",
    "username": "admin",
    "roles": ["admin"]
  }
}
```

### 3. 保存访问令牌

```bash
# 保存令牌到环境变量
export ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 或者在后续请求中直接使用
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 📋 获取可用任务和模型

### 1. 获取任务列表

```bash
curl -X GET "http://localhost:8000/tasks?limit=10&category=single_turn" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

响应示例：
```json
[
  {
    "task_id": "single_turn_scenarios_function_generation",
    "name": "Function Generation",
    "category": "single_turn",
    "difficulty": "intermediate",
    "description": "Evaluate function generation capabilities",
    "languages": ["python"],
    "tags": ["coding", "function_generation"],
    "estimated_duration": 60
  },
  {
    "task_id": "single_turn_scenarios_code_completion",
    "name": "Code Completion",
    "category": "single_turn",
    "difficulty": "beginner",
    "description": "Evaluate code completion capabilities",
    "languages": ["python"],
    "tags": ["coding", "code_completion"],
    "estimated_duration": 60
  }
]
```

### 2. 获取模型列表

```bash
curl -X GET http://localhost:8000/models \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

响应示例：
```json
[
  {
    "model_id": "claude-local",
    "name": "Claude (Local)",
    "provider": "anthropic",
    "version": "3-haiku",
    "capabilities": ["text_generation", "code_completion"],
    "supported_tasks": ["single_turn_scenarios"],
    "rate_limits": {
      "requests_per_minute": 60,
      "tokens_per_minute": 100000
    },
    "cost_per_token": 0.00025,
    "model_args": "model=claude-3-haiku-20240307"
  }
]
```

## 🎯 创建和执行评估任务

### 1. 创建评估任务

```bash
curl -X POST http://localhost:8000/evaluations \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "claude-local",
    "task_ids": [
      "single_turn_scenarios_function_generation",
      "single_turn_scenarios_code_completion"
    ],
    "configuration": {
      "temperature": 0.7,
      "max_tokens": 1024,
      "limit": 3
    },
    "metadata": {
      "experiment_name": "api_demo_evaluation",
      "description": "通过API执行的演示评估",
      "tags": ["demo", "api"]
    }
  }'
```

响应示例：
```json
{
  "evaluation_id": "eval_a1b2c3d4e5f6",
  "status": "created",
  "message": "Evaluation created and started",
  "created_at": "2024-01-01T12:00:00.000000"
}
```

### 2. 任务配置参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `model_id` | string | 是 | 要使用的模型ID |
| `task_ids` | array | 是 | 要执行的任务ID列表 |
| `configuration.limit` | integer | 否 | 每个任务的样本数量限制（默认3） |
| `configuration.temperature` | float | 否 | 模型温度参数（0.0-1.0） |
| `configuration.max_tokens` | integer | 否 | 最大生成token数 |
| `metadata` | object | 否 | 评估元数据 |

## 📊 监控评估进度

### 1. 查看评估状态

```bash
EVAL_ID="eval_a1b2c3d4e5f6"

curl -X GET http://localhost:8000/evaluations/$EVAL_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

响应示例：
```json
{
  "evaluation_id": "eval_a1b2c3d4e5f6",
  "status": "running",
  "progress": 0.5,
  "model_id": "claude-local",
  "task_ids": [
    "single_turn_scenarios_function_generation",
    "single_turn_scenarios_code_completion"
  ],
  "created_at": "2024-01-01T12:00:00.000000",
  "start_time": "2024-01-01T12:00:05.000000",
  "error": null
}
```

### 2. 状态说明

| 状态 | 说明 |
|------|------|
| `created` | 评估已创建，等待执行 |
| `running` | 评估正在执行中 |
| `completed` | 评估已完成 |
| `failed` | 评估执行失败 |

### 3. 轮询状态（Shell脚本示例）

```bash
#!/bin/bash
EVAL_ID="eval_a1b2c3d4e5f6"
TOKEN="your_access_token"

echo "监控评估进度..."
while true; do
    STATUS=$(curl -s -X GET http://localhost:8000/evaluations/$EVAL_ID \
        -H "Authorization: Bearer $TOKEN" | \
        python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    
    echo "当前状态: $STATUS"
    
    if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then
        break
    fi
    
    sleep 10
done

echo "评估完成，状态: $STATUS"
```

## 📈 获取评估结果

### 1. 获取基础结果

```bash
curl -X GET http://localhost:8000/results/$EVAL_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 2. 获取详细结果

```bash
curl -X GET "http://localhost:8000/results/$EVAL_ID?include_details=true" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

响应示例：
```json
{
  "evaluation_id": "eval_a1b2c3d4e5f6",
  "model_id": "claude-local",
  "task_results": [
    {
      "task_id": "single_turn_scenarios_function_generation",
      "status": "completed",
      "score": 0.85,
      "metrics": {
        "accuracy": 0.8,
        "completeness": 0.9,
        "quality": 0.85
      },
      "execution_time": 45.2
    },
    {
      "task_id": "single_turn_scenarios_code_completion",
      "status": "completed",
      "score": 0.78,
      "metrics": {
        "accuracy": 0.75,
        "completeness": 0.8,
        "quality": 0.78
      },
      "execution_time": 32.1
    }
  ],
  "summary_metrics": {
    "overall_score": 0.815,
    "total_tasks": 2,
    "completed_tasks": 2
  }
}
```

## 🔄 完整示例

### Python脚本示例

```python
#!/usr/bin/env python3
"""
完整的API使用示例
"""

import requests
import json
import time

class LMEvalAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def login(self, username="admin", password="admin123"):
        """登录获取访问令牌"""
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            print(f"✅ 登录成功: {data['user_info']['username']}")
            return True
        else:
            print(f"❌ 登录失败: {response.text}")
            return False
    
    def get_tasks(self, category=None, limit=10):
        """获取任务列表"""
        params = {"limit": limit}
        if category:
            params["category"] = category
        
        response = self.session.get(f"{self.base_url}/tasks", params=params)
        if response.status_code == 200:
            return response.json()
        return []
    
    def get_models(self):
        """获取模型列表"""
        response = self.session.get(f"{self.base_url}/models")
        if response.status_code == 200:
            return response.json()
        return []
    
    def create_evaluation(self, model_id, task_ids, config=None):
        """创建评估任务"""
        payload = {
            "model_id": model_id,
            "task_ids": task_ids,
            "configuration": config or {"limit": 3, "temperature": 0.7},
            "metadata": {"experiment_name": "python_api_demo"}
        }
        
        response = self.session.post(f"{self.base_url}/evaluations", json=payload)
        if response.status_code == 200:
            return response.json()["evaluation_id"]
        else:
            print(f"❌ 创建评估失败: {response.text}")
            return None
    
    def wait_for_completion(self, evaluation_id, timeout=300):
        """等待评估完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.session.get(f"{self.base_url}/evaluations/{evaluation_id}")
            if response.status_code == 200:
                status_data = response.json()
                status = status_data["status"]
                
                print(f"状态: {status}")
                
                if status in ["completed", "failed"]:
                    return status
                
                time.sleep(10)
            else:
                print(f"❌ 获取状态失败: {response.text}")
                break
        
        return "timeout"
    
    def get_results(self, evaluation_id, include_details=True):
        """获取评估结果"""
        params = {"include_details": include_details}
        response = self.session.get(f"{self.base_url}/results/{evaluation_id}", params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ 获取结果失败: {response.text}")
            return None

def main():
    """主函数"""
    print("🎯 LM-Eval API 完整示例")
    print("=" * 50)
    
    # 创建客户端
    client = LMEvalAPIClient()
    
    # 1. 登录
    if not client.login():
        return
    
    # 2. 获取可用资源
    print("\n📋 获取可用任务...")
    tasks = client.get_tasks(category="single_turn", limit=5)
    for task in tasks:
        print(f"  - {task['task_id']}: {task['name']}")
    
    print("\n🤖 获取可用模型...")
    models = client.get_models()
    for model in models:
        print(f"  - {model['model_id']}: {model['name']}")
    
    # 3. 创建评估
    print("\n🚀 创建评估任务...")
    evaluation_id = client.create_evaluation(
        model_id="claude-local",
        task_ids=[
            "single_turn_scenarios_function_generation",
            "single_turn_scenarios_code_completion"
        ],
        config={"limit": 2, "temperature": 0.7}
    )
    
    if not evaluation_id:
        return
    
    print(f"✅ 评估任务已创建: {evaluation_id}")
    
    # 4. 等待完成
    print("\n⏳ 等待评估完成...")
    final_status = client.wait_for_completion(evaluation_id)
    
    # 5. 获取结果
    if final_status == "completed":
        print("\n📊 获取评估结果...")
        results = client.get_results(evaluation_id)
        
        if results:
            print(f"总体分数: {results['summary_metrics']['overall_score']:.3f}")
            print("任务结果:")
            for task_result in results["task_results"]:
                print(f"  - {task_result['task_id']}: {task_result['score']:.3f}")
    else:
        print(f"❌ 评估未成功完成: {final_status}")

if __name__ == "__main__":
    main()
```

### Bash脚本示例

```bash
#!/bin/bash

# 配置
BASE_URL="http://localhost:8000"
USERNAME="admin"
PASSWORD="admin123"

echo "🎯 LM-Eval API 完整示例"
echo "=========================="

# 1. 登录获取令牌
echo "🔐 正在登录..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['access_token'])
except:
    print('')
")

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ 登录失败"
    exit 1
fi

echo "✅ 登录成功"

# 2. 获取任务列表
echo -e "\n📋 获取任务列表..."
curl -s -X GET "$BASE_URL/tasks?limit=5" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for task in data:
    print(f\"  - {task['task_id']}: {task['name']}\")
"

# 3. 创建评估
echo -e "\n🚀 创建评估任务..."
EVAL_RESPONSE=$(curl -s -X POST "$BASE_URL/evaluations" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "claude-local",
    "task_ids": ["single_turn_scenarios_function_generation"],
    "configuration": {"limit": 2, "temperature": 0.7},
    "metadata": {"experiment_name": "bash_api_demo"}
  }')

EVAL_ID=$(echo "$EVAL_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['evaluation_id'])
except:
    print('')
")

if [ -z "$EVAL_ID" ]; then
    echo "❌ 创建评估失败"
    exit 1
fi

echo "✅ 评估任务已创建: $EVAL_ID"

# 4. 监控进度
echo -e "\n⏳ 监控评估进度..."
while true; do
    STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/evaluations/$EVAL_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN")
    
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['status'])
except:
    print('error')
")
    
    echo "当前状态: $STATUS"
    
    if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then
        break
    fi
    
    sleep 10
done

# 5. 获取结果
if [ "$STATUS" == "completed" ]; then
    echo -e "\n📊 获取评估结果..."
    curl -s -X GET "$BASE_URL/results/$EVAL_ID?include_details=false" \
      -H "Authorization: Bearer $ACCESS_TOKEN" | \
      python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"总体分数: {data['summary_metrics']['overall_score']:.3f}\")
print(\"任务结果:\")
for task in data['task_results']:
    print(f\"  - {task['task_id']}: {task['score']:.3f}\")
"
else
    echo "❌ 评估失败"
fi

echo -e "\n✨ 示例完成！"
```

## 🔧 故障排除

### 常见问题

#### 1. 服务器启动失败

**问题**: `ModuleNotFoundError: No module named 'fastapi'`

**解决方案**:
```bash
pip install fastapi uvicorn pydantic PyJWT python-multipart
```

#### 2. 任务发现失败

**问题**: 可用任务数为0

**解决方案**:
```bash
# 检查lm-eval安装
python -m lm_eval --help

# 检查任务目录
ls -la lm_eval/tasks/single_turn_scenarios/

# 重新安装lm-eval
pip uninstall lm-eval
pip install lm-eval
```

#### 3. 模型调用失败

**问题**: 评估任务失败，错误信息显示API密钥问题

**解决方案**:
```bash
# 设置API密钥
export ANTHROPIC_API_KEY="your_key"
export OPENAI_API_KEY="your_key"

# 或者使用dummy模型进行测试
# 在评估请求中使用 "model_id": "dummy"
```

#### 4. 认证失败

**问题**: `401 Unauthorized`

**解决方案**:
```bash
# 检查令牌是否过期（有效期1小时）
# 重新登录获取新令牌
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 调试技巧

#### 1. 启用详细日志

```bash
# 设置日志级别
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
" real_api_server.py
```

#### 2. 检查API文档

访问 http://localhost:8000/docs 查看完整的API文档和交互式测试界面。

#### 3. 验证请求格式

```bash
# 使用jq验证JSON格式
echo '{"model_id": "claude-local", "task_ids": ["single_turn_scenarios_function_generation"]}' | jq .
```

## 📚 进阶用法

### 1. 批量评估

```python
# 批量创建多个评估任务
models = ["claude-local", "openai-completions", "deepseek"]
tasks = ["single_turn_scenarios_function_generation", "single_turn_scenarios_code_completion"]

evaluation_ids = []
for model in models:
    eval_id = client.create_evaluation(model, tasks)
    if eval_id:
        evaluation_ids.append(eval_id)

# 等待所有评估完成
for eval_id in evaluation_ids:
    status = client.wait_for_completion(eval_id)
    print(f"评估 {eval_id}: {status}")
```

### 2. 自定义配置

```python
# 高级配置示例
config = {
    "limit": 10,           # 每个任务的样本数
    "temperature": 0.3,    # 较低温度，更确定性的输出
    "max_tokens": 2048,    # 更大的输出长度
    "batch_size": 1,       # 批处理大小
    "num_fewshot": 0       # few-shot示例数量
}

eval_id = client.create_evaluation("claude-local", task_ids, config)
```

### 3. 结果分析

```python
# 分析多个评估结果
def analyze_results(evaluation_ids):
    results = []
    for eval_id in evaluation_ids:
        result = client.get_results(eval_id)
        if result:
            results.append(result)
    
    # 计算平均分数
    avg_scores = {}
    for result in results:
        model_id = result["model_id"]
        overall_score = result["summary_metrics"]["overall_score"]
        
        if model_id not in avg_scores:
            avg_scores[model_id] = []
        avg_scores[model_id].append(overall_score)
    
    # 输出比较结果
    for model_id, scores in avg_scores.items():
        avg_score = sum(scores) / len(scores)
        print(f"{model_id}: 平均分数 {avg_score:.3f}")
```

## 📖 相关文档

- [lm-eval官方文档](https://github.com/EleutherAI/lm-evaluation-harness)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [API交互式文档](http://localhost:8000/docs)（服务器启动后访问）

## 🤝 支持

如果遇到问题，请：

1. 检查服务器日志输出
2. 访问 http://localhost:8000/docs 查看API文档
3. 运行健康检查确认服务状态
4. 查看本指南的故障排除部分

---

**最后更新**: 2024年1月1日
**版本**: 1.0.0