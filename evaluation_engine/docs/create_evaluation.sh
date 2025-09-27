#!/bin/bash

# AI Evaluation Engine - 创建评估任务脚本
# 使用curl异步提交评估任务

API_BASE="http://localhost:8000"
USERNAME="admin"
PASSWORD="admin123"

echo "🔐 步骤1: 用户登录获取访问令牌..."

# 登录获取token
LOGIN_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"${USERNAME}\",
    \"password\": \"${PASSWORD}\"
  }")

echo "登录响应: $LOGIN_RESPONSE"

# 提取access_token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ 登录失败，无法获取访问令牌"
    exit 1
fi

echo "✅ 登录成功，获取到访问令牌"
echo ""

echo "📋 步骤2: 创建评估任务..."

# 创建评估任务 - 使用Claude Haiku
EVALUATION_REQUEST='{
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
}'

echo "发送评估请求..."
echo "请求内容: $EVALUATION_REQUEST"
echo ""

# 异步提交评估任务
EVALUATION_RESPONSE=$(curl -s -X POST "${API_BASE}/evaluations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d "$EVALUATION_REQUEST")

echo "✅ 评估任务创建响应:"
echo "$EVALUATION_RESPONSE" | python3 -m json.tool

# 提取evaluation_id
EVALUATION_ID=$(echo $EVALUATION_RESPONSE | grep -o '"evaluation_id":"[^"]*' | cut -d'"' -f4)

if [ -n "$EVALUATION_ID" ]; then
    echo ""
    echo "🎯 评估任务已创建，ID: $EVALUATION_ID"
    echo ""
    echo "📊 可以使用以下命令查看状态:"
    echo "curl -H \"Authorization: Bearer ${ACCESS_TOKEN}\" ${API_BASE}/evaluations/${EVALUATION_ID}"
    echo ""
    echo "📈 可以使用以下命令查看结果:"
    echo "curl -H \"Authorization: Bearer ${ACCESS_TOKEN}\" ${API_BASE}/results/${EVALUATION_ID}"
else
    echo "❌ 创建评估任务失败"
fi