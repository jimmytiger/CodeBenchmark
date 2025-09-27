# AI Evaluation Engine API 接口汇总

## 基础信息
- **Base URL**: `http://localhost:8000`
- **认证方式**: Bearer Token (通过登录获取)
- **Content-Type**: `application/json`

---

## 1. 创建评估任务 (POST /evaluations)

### 请求格式
```http
POST /evaluations
Authorization: Bearer {access_token}
Content-Type: application/json
```

### 输入参数 (Request Body)
```json
{
  "model_id": "claude-local",
  "task_ids": [
    "single_turn_scenarios_code_completion",
    "single_turn_scenarios_bug_fix", 
    "single_turn_scenarios_function_generation"
  ],
  "configuration": {
    "limit": 3,
    "temperature": 0.7,
    "max_tokens": 1000
  },
  "metadata": {
    "description": "Claude Haiku 评估任务",
    "created_by": "curl_script",
    "model": "claude-3-haiku-20240307",
    "tags": ["claude", "haiku", "real_model"]
  }
}
```

### 返回格式 (Response)
```json
{
  "evaluation_id": "eval_5a7155ca25d4",
  "status": "created",
  "message": "Evaluation created and started",
  "created_at": "2025-09-27T06:26:47.568592"
}
```

### 字段说明
**输入字段**:
- `model_id` (必需): 模型ID，可选值: `dummy`, `claude-local`, `openai-completions`, `deepseek`
- `task_ids` (必需): 任务ID列表，支持的任务包括各种single_turn_scenarios
- `configuration` (可选): 评估配置参数
  - `limit`: 限制评估样本数量 (仅用于测试)
  - `temperature`: 生成温度参数
  - `max_tokens`: 最大生成token数
- `metadata` (可选): 元数据信息

**返回字段**:
- `evaluation_id`: 唯一的评估任务ID
- `status`: 任务状态 (`created`)
- `message`: 状态描述信息
- `created_at`: 创建时间 (ISO格式)

---

## 2. 获取评估状态 (GET /evaluations/{evaluation_id})

### 请求格式
```http
GET /evaluations/{evaluation_id}
Authorization: Bearer {access_token}
```

### 输入参数
- **路径参数**: `evaluation_id` - 评估任务ID

### 返回格式 (Response)
```json
{
  "evaluation_id": "eval_5a7155ca25d4",
  "status": "completed",
  "progress": 0.0,
  "model_id": "claude-local",
  "task_ids": [
    "single_turn_scenarios_code_completion",
    "single_turn_scenarios_bug_fix",
    "single_turn_scenarios_function_generation"
  ],
  "created_at": "2025-09-27T06:26:47.568426",
  "start_time": "2025-09-27T06:26:47.568932",
  "completed_at": "2025-09-27T06:27:23.853631",
  "error": null
}
```

### 字段说明
**返回字段**:
- `evaluation_id`: 评估任务ID
- `status`: 任务状态 (`created`, `running`, `completed`, `failed`)
- `progress`: 执行进度 (0.0-1.0)
- `model_id`: 使用的模型ID
- `task_ids`: 任务ID列表
- `created_at`: 创建时间
- `start_time`: 开始执行时间
- `completed_at`: 完成时间 (如果已完成)
- `error`: 错误信息 (如果失败)

---

## 3. 获取评估结果 (GET /results/{evaluation_id})

### 请求格式
```http
GET /results/{evaluation_id}?include_details=true
Authorization: Bearer {access_token}
```

### 输入参数
- **路径参数**: `evaluation_id` - 评估任务ID
- **查询参数**: `include_details` (可选) - 是否包含详细信息 (`true`/`false`)

### 返回格式 (Response)
```json
{
  "evaluation_id": "unknown",
  "model_id": "claude-local",
  "task_results": [
    {
      "task_id": "single_turn_scenarios_code_completion",
      "status": "completed",
      "score": 0.75,
      "metrics": {
        "accuracy": 0.7,
        "completeness": 0.8,
        "quality": 0.75
      },
      "execution_time": 30.0
    },
    {
      "task_id": "single_turn_scenarios_bug_fix",
      "status": "completed", 
      "score": 0.75,
      "metrics": {
        "accuracy": 0.7,
        "completeness": 0.8,
        "quality": 0.75
      },
      "execution_time": 30.0
    }
  ],
  "summary_metrics": {
    "overall_score": 0.75,
    "total_tasks": 3,
    "completed_tasks": 3
  },
  "raw_output": "详细的lm-eval输出结果..."
}
```

### 字段说明
**返回字段**:
- `evaluation_id`: 评估任务ID
- `model_id`: 使用的模型ID
- `task_results`: 各任务的详细结果
  - `task_id`: 任务ID
  - `status`: 任务状态
  - `score`: 任务得分 (0.0-1.0)
  - `metrics`: 详细指标
  - `execution_time`: 执行时间(秒)
- `summary_metrics`: 汇总指标
  - `overall_score`: 总体得分
  - `total_tasks`: 总任务数
  - `completed_tasks`: 完成任务数
- `raw_output`: 原始lm-eval输出 (当`include_details=true`时包含)

---

## 错误响应格式

### 认证错误 (401)
```json
{
  "detail": "Invalid token"
}
```

### 资源未找到 (404)
```json
{
  "detail": "Evaluation not found"
}
```

### 参数错误 (400)
```json
{
  "detail": "Invalid tasks: ['invalid_task_name']"
}
```

---

## 使用示例

### 完整的评估流程
```bash
# 1. 登录获取token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | \
  jq -r '.access_token')

# 2. 创建评估任务
EVAL_ID=$(curl -s -X POST http://localhost:8000/evaluations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "claude-local",
    "task_ids": ["single_turn_scenarios_code_completion"],
    "configuration": {"limit": 3}
  }' | jq -r '.evaluation_id')

# 3. 检查状态
curl -X GET http://localhost:8000/evaluations/$EVAL_ID \
  -H "Authorization: Bearer $TOKEN"

# 4. 获取结果 (等待完成后)
curl -X GET http://localhost:8000/results/$EVAL_ID?include_details=true \
  -H "Authorization: Bearer $TOKEN"
```

---

## 支持的模型和任务

### 可用模型
- `dummy`: 测试用模型
- `claude-local`: Claude 3 Haiku
- `openai-completions`: GPT-3.5 Turbo  
- `deepseek`: DeepSeek Coder

### 可用任务
- `single_turn_scenarios_code_completion`: 代码补全
- `single_turn_scenarios_bug_fix`: Bug修复
- `single_turn_scenarios_function_generation`: 函数生成
- `single_turn_scenarios_algorithm_implementation`: 算法实现
- `single_turn_scenarios_api_design`: API设计
- 等等...

### 评估指标
- `exact_match`: 精确匹配
- `syntax_validity`: 语法有效性
- `runtime_correctness`: 运行时正确性
- `bleu_score`: BLEU分数
- `code_quality`: 代码质量