#!/bin/bash

# AI Evaluation Engine - 检查评估任务状态和结果
# 获取评估状态和结果的curl请求

API_BASE="http://localhost:8000"
USERNAME="admin"
PASSWORD="admin123"

# 检查是否提供了evaluation_id参数
if [ -z "$1" ]; then
    echo "❌ 请提供evaluation_id参数"
    echo "用法: $0 <evaluation_id>"
    echo "示例: $0 eval_abc123def456"
    exit 1
fi

EVALUATION_ID="$1"

echo "🔐 步骤1: 用户登录获取访问令牌..."

# 登录获取token
LOGIN_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"${USERNAME}\",
    \"password\": \"${PASSWORD}\"
  }")

# 提取access_token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ 登录失败，无法获取访问令牌"
    exit 1
fi

echo "✅ 登录成功"
echo ""

echo "📊 步骤2: 获取评估状态..."
echo "评估ID: $EVALUATION_ID"
echo ""

# 获取评估状态
STATUS_RESPONSE=$(curl -s -X GET "${API_BASE}/evaluations/${EVALUATION_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "✅ 评估状态响应:"
echo "$STATUS_RESPONSE" | python3 -m json.tool
echo ""

# 检查状态是否为completed
STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*' | cut -d'"' -f4)

if [ "$STATUS" = "completed" ]; then
    echo "🎉 评估已完成，获取结果..."
    echo ""
    
    # 获取评估结果
    RESULTS_RESPONSE=$(curl -s -X GET "${API_BASE}/results/${EVALUATION_ID}?include_details=true" \
      -H "Authorization: Bearer ${ACCESS_TOKEN}")
    
    echo "📈 评估结果:"
    echo "$RESULTS_RESPONSE" | python3 -m json.tool
    
elif [ "$STATUS" = "running" ]; then
    echo "⏳ 评估正在运行中，请稍后再次检查"
    echo ""
    echo "重新检查命令:"
    echo "$0 $EVALUATION_ID"
    
elif [ "$STATUS" = "failed" ]; then
    echo "❌ 评估失败"
    ERROR=$(echo $STATUS_RESPONSE | grep -o '"error":"[^"]*' | cut -d'"' -f4)
    if [ -n "$ERROR" ]; then
        echo "错误信息: $ERROR"
    fi
    
else
    echo "📋 当前状态: $STATUS"
    echo "请稍后再次检查"
fi

echo ""
echo "🔧 手动curl命令:"
echo ""
echo "获取状态:"
echo "curl -H \"Authorization: Bearer ${ACCESS_TOKEN}\" ${API_BASE}/evaluations/${EVALUATION_ID}"
echo ""
echo "获取结果:"
echo "curl -H \"Authorization: Bearer ${ACCESS_TOKEN}\" ${API_BASE}/results/${EVALUATION_ID}?include_details=true"