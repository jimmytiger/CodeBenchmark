#!/bin/bash

# 简化的curl命令示例
# 使用方法：先运行登录命令获取token，然后使用token执行其他命令

API_BASE="http://localhost:8000"

echo "=== AI Evaluation Engine Curl 命令集合 ==="
echo ""

echo "1️⃣ 登录获取Token:"
echo "curl -X POST ${API_BASE}/auth/login \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"username\": \"admin\", \"password\": \"admin123\"}'"
echo ""

echo "2️⃣ 创建评估任务 (使用Claude Haiku):"
echo "curl -X POST ${API_BASE}/evaluations \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN_HERE' \\"
echo "  -d '{"
echo "    \"model_id\": \"claude-local\","
echo "    \"task_ids\": ["
echo "      \"single_turn_scenarios_code_completion\","
echo "      \"single_turn_scenarios_bug_fix\","
echo "      \"single_turn_scenarios_function_generation\""
echo "    ],"
echo "    \"configuration\": {"
echo "      \"limit\": 3,"
echo "      \"temperature\": 0.7,"
echo "      \"max_tokens\": 1000"
echo "    },"
echo "    \"metadata\": {"
echo "      \"description\": \"Claude Haiku 评估任务\","
echo "      \"model\": \"claude-3-haiku-20240307\""
echo "    }"
echo "  }'"
echo ""

echo "3️⃣ 获取评估状态:"
echo "curl -X GET ${API_BASE}/evaluations/EVALUATION_ID_HERE \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN_HERE'"
echo ""

echo "4️⃣ 获取评估结果:"
echo "curl -X GET ${API_BASE}/results/EVALUATION_ID_HERE?include_details=true \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN_HERE'"
echo ""

echo "5️⃣ 健康检查 (无需认证):"
echo "curl -X GET ${API_BASE}/health"
echo ""

echo "6️⃣ 获取可用任务列表:"
echo "curl -X GET ${API_BASE}/tasks \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN_HERE'"
echo ""

echo "7️⃣ 获取可用模型列表:"
echo "curl -X GET ${API_BASE}/models \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN_HERE'"
echo ""

echo "💡 使用提示:"
echo "1. 先执行登录命令获取access_token"
echo "2. 将YOUR_TOKEN_HERE替换为实际的token"
echo "3. 将EVALUATION_ID_HERE替换为实际的评估ID"
echo "4. 可以使用 | python3 -m json.tool 格式化JSON输出"