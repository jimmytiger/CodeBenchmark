#!/bin/bash

# AI Evaluation Engine API 测试脚本
# 使用curl命令验证API功能

set -e  # 遇到错误时退出

BASE_URL="http://localhost:8000"
ACCESS_TOKEN=""

echo "🧪 AI Evaluation Engine API 测试"
echo "=================================="
echo "确保API服务器已在 $BASE_URL 启动"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试函数
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local headers="$5"
    
    echo -e "${BLUE}测试: $name${NC}"
    echo "----------------------------------------"
    
    # 构建curl命令
    local cmd="curl -s -w '\nHTTP Status: %{http_code}\n' -X $method"
    
    if [ ! -z "$headers" ]; then
        cmd="$cmd $headers"
    fi
    
    if [ ! -z "$data" ]; then
        cmd="$cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    
    cmd="$cmd $BASE_URL$endpoint"
    
    echo "命令: $cmd"
    echo ""
    
    # 执行命令
    local response=$(eval $cmd)
    local http_code=$(echo "$response" | tail -n1 | grep -o '[0-9]*')
    local body=$(echo "$response" | head -n -1)
    
    echo "响应:"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    echo ""
    
    if [[ $http_code -ge 200 && $http_code -lt 300 ]]; then
        echo -e "${GREEN}✅ 成功 (HTTP $http_code)${NC}"
    else
        echo -e "${RED}❌ 失败 (HTTP $http_code)${NC}"
    fi
    
    echo ""
    return $http_code
}

# 1. 健康检查
echo "1️⃣ 健康检查"
test_endpoint "健康检查" "GET" "/health"

# 2. 用户登录
echo "2️⃣ 用户登录"
login_data='{"username": "admin", "password": "admin123"}'
response=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "$login_data")

echo "登录响应:"
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"

# 提取访问令牌
ACCESS_TOKEN=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('access_token', ''))
except:
    pass
" 2>/dev/null)

if [ ! -z "$ACCESS_TOKEN" ]; then
    echo -e "${GREEN}✅ 登录成功，获得访问令牌${NC}"
    echo "Token: ${ACCESS_TOKEN:0:50}..."
else
    echo -e "${RED}❌ 登录失败，无法获取访问令牌${NC}"
    echo "后续需要认证的测试将跳过"
fi

echo ""

# 3. 获取任务列表
if [ ! -z "$ACCESS_TOKEN" ]; then
    echo "3️⃣ 获取任务列表"
    test_endpoint "任务列表" "GET" "/tasks?limit=5" "" "-H 'Authorization: Bearer $ACCESS_TOKEN'"
fi

# 4. 获取模型列表
if [ ! -z "$ACCESS_TOKEN" ]; then
    echo "4️⃣ 获取模型列表"
    test_endpoint "模型列表" "GET" "/models" "" "-H 'Authorization: Bearer $ACCESS_TOKEN'"
fi

# 5. 创建评估任务
if [ ! -z "$ACCESS_TOKEN" ]; then
    echo "5️⃣ 创建评估任务"
    eval_data='{
        "model_id": "claude-3-haiku",
        "task_ids": ["single_turn_scenarios_function_generation"],
        "configuration": {
            "temperature": 0.7,
            "max_tokens": 1024,
            "limit": 3
        },
        "metadata": {
            "experiment_name": "curl_test_evaluation",
            "description": "Test evaluation via curl"
        }
    }'
    
    response=$(curl -s -X POST "$BASE_URL/evaluations" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$eval_data")
    
    echo "创建评估响应:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    
    # 提取评估ID
    EVALUATION_ID=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('evaluation_id', ''))
except:
    pass
" 2>/dev/null)
    
    if [ ! -z "$EVALUATION_ID" ]; then
        echo -e "${GREEN}✅ 评估创建成功${NC}"
        echo "Evaluation ID: $EVALUATION_ID"
        
        # 6. 查看评估状态
        echo ""
        echo "6️⃣ 查看评估状态"
        test_endpoint "评估状态" "GET" "/evaluations/$EVALUATION_ID" "" "-H 'Authorization: Bearer $ACCESS_TOKEN'"
        
        # 7. 获取评估结果
        echo "7️⃣ 获取评估结果"
        test_endpoint "评估结果" "GET" "/results/$EVALUATION_ID?include_details=true" "" "-H 'Authorization: Bearer $ACCESS_TOKEN'"
    else
        echo -e "${RED}❌ 评估创建失败${NC}"
    fi
fi

echo ""
echo "🎯 完整的curl命令示例"
echo "======================"

echo ""
echo "1. 健康检查:"
echo "curl -X GET $BASE_URL/health"

echo ""
echo "2. 用户登录:"
echo "curl -X POST $BASE_URL/auth/login \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"username\": \"admin\", \"password\": \"admin123\"}'"

if [ ! -z "$ACCESS_TOKEN" ]; then
    echo ""
    echo "3. 获取任务列表 (需要token):"
    echo "curl -X GET '$BASE_URL/tasks?limit=10&category=single_turn' \\"
    echo "  -H 'Authorization: Bearer $ACCESS_TOKEN'"
    
    echo ""
    echo "4. 获取模型列表 (需要token):"
    echo "curl -X GET $BASE_URL/models \\"
    echo "  -H 'Authorization: Bearer $ACCESS_TOKEN'"
    
    echo ""
    echo "5. 创建评估任务 (需要token):"
    echo "curl -X POST $BASE_URL/evaluations \\"
    echo "  -H 'Authorization: Bearer $ACCESS_TOKEN' \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{"
    echo "    \"model_id\": \"claude-3-haiku\","
    echo "    \"task_ids\": [\"single_turn_scenarios_function_generation\"],"
    echo "    \"configuration\": {"
    echo "      \"temperature\": 0.7,"
    echo "      \"max_tokens\": 1024,"
    echo "      \"limit\": 3"
    echo "    },"
    echo "    \"metadata\": {"
    echo "      \"experiment_name\": \"test_evaluation\""
    echo "    }"
    echo "  }'"
    
    if [ ! -z "$EVALUATION_ID" ]; then
        echo ""
        echo "6. 查看评估状态 (需要token):"
        echo "curl -X GET $BASE_URL/evaluations/$EVALUATION_ID \\"
        echo "  -H 'Authorization: Bearer $ACCESS_TOKEN'"
        
        echo ""
        echo "7. 获取评估结果 (需要token):"
        echo "curl -X GET '$BASE_URL/results/$EVALUATION_ID?include_details=true' \\"
        echo "  -H 'Authorization: Bearer $ACCESS_TOKEN'"
    fi
fi

echo ""
echo "🔧 环境变量设置 (可选):"
echo "export ANTHROPIC_API_KEY='your_anthropic_key'"
echo "export OPENAI_API_KEY='your_openai_key'"
echo "export DEEPSEEK_API_KEY='your_deepseek_key'"
echo "export DASHSCOPE_API_KEY='your_dashscope_key'"

echo ""
echo "✨ 测试完成！"