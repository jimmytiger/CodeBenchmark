#!/bin/bash

# 动态任务创建 - Curl 示例脚本
# 展示如何通过API动态创建、管理和执行评估任务

set -e

BASE_URL="http://localhost:8000"
ACCESS_TOKEN=""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 动态任务创建 - Curl 示例${NC}"
echo "=================================================="

# 1. 健康检查
echo -e "\n${YELLOW}1️⃣ 健康检查${NC}"
echo "curl -X GET $BASE_URL/health"
curl -s -X GET "$BASE_URL/health" | python3 -m json.tool
echo ""

# 2. 用户登录获取Token
echo -e "\n${YELLOW}2️⃣ 用户登录获取访问令牌${NC}"
LOGIN_CMD="curl -s -X POST $BASE_URL/auth/login -H 'Content-Type: application/json' -d '{\"username\": \"admin\", \"password\": \"admin123\"}'"
echo "$LOGIN_CMD"

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}')

echo "登录响应:"
echo "$LOGIN_RESPONSE" | python3 -m json.tool

# 提取访问令牌
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "
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
    echo -e "${RED}❌ 登录失败${NC}"
    exit 1
fi

# 3. 查看现有任务列表
echo -e "\n${YELLOW}3️⃣ 查看现有任务列表${NC}"
LIST_TASKS_CMD="curl -s -X GET '$BASE_URL/tasks' -H 'Authorization: Bearer $ACCESS_TOKEN'"
echo "$LIST_TASKS_CMD"

TASKS_RESPONSE=$(curl -s -X GET "$BASE_URL/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "现有任务:"
echo "$TASKS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'总任务数: {data[\"total\"]}')
    print(f'动态任务: {data[\"dynamic_tasks\"]}')
    print(f'静态任务: {data[\"static_tasks\"]}')
    print('\\n前5个任务:')
    for i, task in enumerate(data['tasks'][:5]):
        print(f'  {i+1}. {task[\"task_id\"]} ({task[\"type\"]})')
except Exception as e:
    print(f'解析失败: {e}')
"

# 4. 创建简单的动态任务
echo -e "\n${YELLOW}4️⃣ 创建简单的动态任务${NC}"

SIMPLE_TASK_DATA='{
  "task_id": "dynamic_simple_math",
  "name": "Simple Math Task",
  "description": "A simple math problem solving task",
  "category": "mathematics",
  "difficulty": "easy",
  "tags": ["math", "arithmetic", "dynamic"],
  "task_config": {
    "output_type": "generate_until",
    "doc_to_text": "Solve this math problem: {{problem}}",
    "doc_to_target": "{{answer}}",
    "generation_kwargs": {
      "temperature": 0.1,
      "max_gen_toks": 100,
      "until": ["\\n", ".", "Answer:"]
    },
    "metric_list": [
      {
        "metric": "exact_match",
        "aggregation": "mean",
        "higher_is_better": true
      }
    ]
  },
  "metadata": {
    "author": "Dynamic Task Creator",
    "version": "1.0.0"
  }
}'

CREATE_TASK_CMD="curl -s -X POST $BASE_URL/tasks -H 'Authorization: Bearer $ACCESS_TOKEN' -H 'Content-Type: application/json' -d '$SIMPLE_TASK_DATA'"
echo "创建简单数学任务:"
echo "$CREATE_TASK_CMD"

CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$SIMPLE_TASK_DATA")

echo "创建响应:"
echo "$CREATE_RESPONSE" | python3 -m json.tool

# 5. 创建复杂的编程任务
echo -e "\n${YELLOW}5️⃣ 创建复杂的编程任务${NC}"

CODING_TASK_DATA='{
  "task_id": "dynamic_python_coding",
  "name": "Python Coding Challenge",
  "description": "Dynamic Python coding task with multiple test cases",
  "category": "programming",
  "difficulty": "intermediate",
  "tags": ["python", "coding", "algorithms", "dynamic"],
  "task_config": {
    "output_type": "generate_until",
    "doc_to_text": "Write a Python function to solve: {{problem_description}}\\n\\nRequirements:\\n{{requirements}}\\n\\nFunction signature: {{function_signature}}",
    "doc_to_target": "{{expected_code}}",
    "generation_kwargs": {
      "temperature": 0.2,
      "max_gen_toks": 500,
      "until": ["\\n\\n", "# Test", "if __name__"]
    },
    "metric_list": [
      {
        "metric": "code_execution",
        "aggregation": "mean",
        "higher_is_better": true
      },
      {
        "metric": "syntax_validity",
        "aggregation": "mean", 
        "higher_is_better": true
      }
    ],
    "filter_list": [
      {
        "name": "extract_code",
        "filter": [
          {
            "function": "regex",
            "regex_pattern": "```python\\n(.*)\\n```",
            "group_select": 1
          }
        ]
      }
    ]
  },
  "metadata": {
    "author": "Dynamic Task Creator",
    "version": "1.0.0",
    "programming_language": "python"
  }
}'

echo "创建Python编程任务:"
CREATE_CODING_RESPONSE=$(curl -s -X POST "$BASE_URL/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$CODING_TASK_DATA")

echo "创建响应:"
echo "$CREATE_CODING_RESPONSE" | python3 -m json.tool

# 6. 创建多轮对话任务
echo -e "\n${YELLOW}6️⃣ 创建多轮对话任务${NC}"

MULTI_TURN_TASK_DATA='{
  "task_id": "dynamic_multi_turn_conversation",
  "name": "Multi-Turn Conversation Task",
  "description": "Dynamic multi-turn conversation evaluation",
  "category": "conversation",
  "difficulty": "advanced",
  "tags": ["conversation", "multi-turn", "dialogue", "dynamic"],
  "task_config": {
    "output_type": "generate_until",
    "doc_to_text": "Continue this conversation:\\n{{conversation_history}}\\n\\nUser: {{user_input}}\\nAssistant:",
    "doc_to_target": "{{expected_response}}",
    "generation_kwargs": {
      "temperature": 0.7,
      "max_gen_toks": 200,
      "until": ["\\nUser:", "\\n\\n"]
    },
    "metric_list": [
      {
        "metric": "conversation_coherence",
        "aggregation": "mean",
        "higher_is_better": true
      },
      {
        "metric": "response_relevance",
        "aggregation": "mean",
        "higher_is_better": true
      }
    ]
  },
  "scenario_config": {
    "scenario_id": "multi_turn_conversation",
    "scenario_type": "dialogue",
    "max_turns": 5,
    "conversation_timeout": 300,
    "enable_context_retention": true
  },
  "metadata": {
    "author": "Dynamic Task Creator",
    "version": "1.0.0",
    "conversation_type": "general"
  }
}'

echo "创建多轮对话任务:"
CREATE_MULTI_TURN_RESPONSE=$(curl -s -X POST "$BASE_URL/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$MULTI_TURN_TASK_DATA")

echo "创建响应:"
echo "$CREATE_MULTI_TURN_RESPONSE" | python3 -m json.tool

# 7. 查看更新后的任务列表
echo -e "\n${YELLOW}7️⃣ 查看更新后的任务列表${NC}"

UPDATED_TASKS_RESPONSE=$(curl -s -X GET "$BASE_URL/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "更新后的任务列表:"
echo "$UPDATED_TASKS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'总任务数: {data[\"total\"]}')
    print(f'动态任务: {data[\"dynamic_tasks\"]}')
    print(f'静态任务: {data[\"static_tasks\"]}')
    print('\\n动态任务:')
    dynamic_count = 0
    for task in data['tasks']:
        if task['type'] == 'dynamic':
            dynamic_count += 1
            print(f'  {dynamic_count}. {task[\"task_id\"]} - {task[\"name\"]} ({task[\"difficulty\"]})')
except Exception as e:
    print(f'解析失败: {e}')
"

# 8. 查看特定任务详情
echo -e "\n${YELLOW}8️⃣ 查看动态任务详情${NC}"

TASK_DETAIL_CMD="curl -s -X GET '$BASE_URL/tasks/dynamic_python_coding' -H 'Authorization: Bearer $ACCESS_TOKEN'"
echo "$TASK_DETAIL_CMD"

TASK_DETAIL_RESPONSE=$(curl -s -X GET "$BASE_URL/tasks/dynamic_python_coding" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "任务详情:"
echo "$TASK_DETAIL_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'任务ID: {data[\"task_id\"]}')
    print(f'名称: {data[\"name\"]}')
    print(f'描述: {data[\"description\"]}')
    print(f'类别: {data[\"category\"]}')
    print(f'难度: {data[\"difficulty\"]}')
    print(f'标签: {data[\"tags\"]}')
    print(f'创建时间: {data[\"created_at\"]}')
except Exception as e:
    print(f'解析失败: {e}')
"

# 9. 执行动态任务
echo -e "\n${YELLOW}9️⃣ 执行动态任务${NC}"

EXECUTE_TASK_DATA='{
  "limit": 1,
  "gen_kwargs": {
    "temperature": 0.2,
    "max_gen_toks": 200
  }
}'

EXECUTE_CMD="curl -s -X POST '$BASE_URL/tasks/dynamic_simple_math/execute?model_id=dummy' -H 'Authorization: Bearer $ACCESS_TOKEN' -H 'Content-Type: application/json' -d '$EXECUTE_TASK_DATA'"
echo "执行动态任务:"
echo "$EXECUTE_CMD"

# 注意：这里需要修改API以支持这种调用方式
echo "（注意：实际执行需要服务器支持此端点）"

# 10. 过滤查询任务
echo -e "\n${YELLOW}🔟 过滤查询任务${NC}"

# 只查询动态任务
echo "查询所有动态任务:"
DYNAMIC_TASKS_CMD="curl -s -X GET '$BASE_URL/tasks?task_type=dynamic' -H 'Authorization: Bearer $ACCESS_TOKEN'"
echo "$DYNAMIC_TASKS_CMD"

DYNAMIC_TASKS_RESPONSE=$(curl -s -X GET "$BASE_URL/tasks?task_type=dynamic" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$DYNAMIC_TASKS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'动态任务数量: {len(data[\"tasks\"])}')
    for i, task in enumerate(data['tasks'], 1):
        print(f'  {i}. {task[\"task_id\"]} - {task[\"name\"]}')
except Exception as e:
    print(f'解析失败: {e}')
"

# 按类别查询
echo -e "\n查询编程类任务:"
PROGRAMMING_TASKS_CMD="curl -s -X GET '$BASE_URL/tasks?category=programming' -H 'Authorization: Bearer $ACCESS_TOKEN'"
echo "$PROGRAMMING_TASKS_CMD"

PROGRAMMING_TASKS_RESPONSE=$(curl -s -X GET "$BASE_URL/tasks?category=programming" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$PROGRAMMING_TASKS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'编程任务数量: {len(data[\"tasks\"])}')
    for i, task in enumerate(data['tasks'], 1):
        print(f'  {i}. {task[\"task_id\"]} - {task[\"name\"]} ({task[\"difficulty\"]})')
except Exception as e:
    print(f'解析失败: {e}')
"

# 11. 删除动态任务
echo -e "\n${YELLOW}1️⃣1️⃣ 删除动态任务${NC}"

DELETE_TASK_CMD="curl -s -X DELETE '$BASE_URL/tasks/dynamic_simple_math' -H 'Authorization: Bearer $ACCESS_TOKEN'"
echo "删除简单数学任务:"
echo "$DELETE_TASK_CMD"

DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/tasks/dynamic_simple_math" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "删除响应:"
echo "$DELETE_RESPONSE" | python3 -m json.tool

# 12. 验证删除结果
echo -e "\n${YELLOW}1️⃣2️⃣ 验证删除结果${NC}"

FINAL_TASKS_RESPONSE=$(curl -s -X GET "$BASE_URL/tasks?task_type=dynamic" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "删除后的动态任务:"
echo "$FINAL_TASKS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'剩余动态任务数量: {len(data[\"tasks\"])}')
    for i, task in enumerate(data['tasks'], 1):
        print(f'  {i}. {task[\"task_id\"]} - {task[\"name\"]}')
except Exception as e:
    print(f'解析失败: {e}')
"

echo -e "\n${GREEN}✨ 动态任务创建演示完成！${NC}"
echo "=================================================="

echo -e "\n${BLUE}📋 总结${NC}"
echo "✅ 成功演示了以下功能:"
echo "  1. 用户认证和令牌获取"
echo "  2. 查看现有任务列表"
echo "  3. 创建简单动态任务"
echo "  4. 创建复杂编程任务"
echo "  5. 创建多轮对话任务"
echo "  6. 查看任务详情"
echo "  7. 过滤查询任务"
echo "  8. 删除动态任务"

echo -e "\n${BLUE}🔧 可用的curl命令模板${NC}"
echo "# 登录获取令牌"
echo "curl -X POST $BASE_URL/auth/login -H 'Content-Type: application/json' -d '{\"username\": \"admin\", \"password\": \"admin123\"}'"

echo -e "\n# 创建动态任务"
echo "curl -X POST $BASE_URL/tasks -H 'Authorization: Bearer \$TOKEN' -H 'Content-Type: application/json' -d @task_config.json"

echo -e "\n# 查看所有任务"
echo "curl -X GET $BASE_URL/tasks -H 'Authorization: Bearer \$TOKEN'"

echo -e "\n# 查看特定任务"
echo "curl -X GET $BASE_URL/tasks/TASK_ID -H 'Authorization: Bearer \$TOKEN'"

echo -e "\n# 删除动态任务"
echo "curl -X DELETE $BASE_URL/tasks/TASK_ID -H 'Authorization: Bearer \$TOKEN'"

echo -e "\n${YELLOW}💡 提示${NC}"
echo "- 将 \$TOKEN 替换为实际的访问令牌"
echo "- 将 TASK_ID 替换为实际的任务ID"
echo "- 可以通过修改JSON配置创建不同类型的任务"
echo "- 支持过滤查询：?task_type=dynamic&category=programming"