#!/bin/bash

# EvaluationEngineV1.0 自定义任务快速启动脚本

set -e

echo "🚀 EvaluationEngineV1.0 自定义任务快速启动"
echo "=" * 50

# 检查环境变量
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ 请设置 ANTHROPIC_API_KEY 环境变量"
    echo "   export ANTHROPIC_API_KEY='your-api-key-here'"
    exit 1
fi

echo "✅ API Key 已设置: ${ANTHROPIC_API_KEY:0:10}..."

# 检查 Python 依赖
echo "🔍 检查依赖..."
python -c "import flask, requests; print('✅ Flask 和 requests 可用')" || {
    echo "📦 安装缺失依赖..."
    pip install flask flask-cors requests
}

# 创建结果目录
mkdir -p ./results/quick_start

echo ""
echo "选择启动模式:"
echo "1. Python 直接调用测试"
echo "2. 启动 API 服务器"
echo "3. 运行完整集成测试"
echo "4. 生成 curl 示例"

read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo "🐍 Python 直接调用测试..."
        python -c "
import sys
sys.path.insert(0, '.')
from custom_task_integration import evaluate_custom_task

print('📝 测试单轮任务...')
result = evaluate_custom_task(
    task_name='single_turn_scenarios_code_completion',
    model='anthropic-chat',
    model_args='model=claude-3-haiku-20240307,max_tokens=512,temperature=0.0',
    limit=2,
    output_path='./results/quick_start/single_turn'
)
print(f'✅ 单轮任务完成: {result.status}')

print('🔄 测试多轮任务...')
result = evaluate_custom_task(
    task_name='multi_turn_scenarios.code_review_3_turn',
    model='anthropic-chat',
    model_args='model=claude-3-haiku-20240307,max_tokens=512,temperature=0.0',
    limit=1,
    output_path='./results/quick_start/multi_turn'
)
print(f'✅ 多轮任务完成: {result.status}')
print('🎉 Python 直接调用测试完成！')
"
        ;;
    2)
        echo "🌐 启动 API 服务器..."
        echo "📡 服务器将在 http://localhost:5000 启动"
        echo "🎯 演示页面: http://localhost:5000/demo"
        echo "⏹️  按 Ctrl+C 停止服务器"
        python custom_task_api_server.py
        ;;
    3)
        echo "🧪 运行完整集成测试..."
        python test_custom_integration.py
        ;;
    4)
        echo "📋 生成 curl 示例..."
        cat > ./results/quick_start/curl_examples.sh << 'EOF'
#!/bin/bash

# EvaluationEngineV1.0 自定义任务 API curl 示例

API_BASE="http://localhost:5000"

echo "🔍 健康检查"
curl -X GET $API_BASE/health -H "Content-Type: application/json"

echo -e "\n📋 列出可用任务"
curl -X GET $API_BASE/tasks -H "Content-Type: application/json"

echo -e "\n🚀 启动单轮任务评估"
curl -X POST $API_BASE/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic-chat",
    "model_args": "model=claude-3-haiku-20240307,max_tokens=1024,temperature=0.0",
    "tasks": ["single_turn_scenarios_code_completion"],
    "limit": 5,
    "num_fewshot": 0,
    "batch_size": 1
  }'

echo -e "\n🔄 启动多轮任务评估"
curl -X POST $API_BASE/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic-chat",
    "model_args": "model=claude-3-haiku-20240307,max_tokens=1024,temperature=0.0",
    "tasks": ["multi_turn_scenarios.code_review_3_turn"],
    "limit": 3,
    "apply_chat_template": true
  }'

echo -e "\n📦 启动任务套件评估"
curl -X POST $API_BASE/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic-chat",
    "model_args": "model=claude-3-haiku-20240307",
    "tasks": [
      "single_turn_scenarios_code_completion",
      "single_turn_scenarios_bug_fix",
      "multi_turn_scenarios.code_review_3_turn"
    ],
    "limit": 3
  }'

# 注意: 实际使用时需要先启动 API 服务器
# python EvaluationEngineV1_0/custom_task_api_server.py
EOF
        chmod +x ./results/quick_start/curl_examples.sh
        echo "✅ curl 示例已生成: ./results/quick_start/curl_examples.sh"
        echo "💡 使用方法:"
        echo "   1. 启动 API 服务器: python custom_task_api_server.py"
        echo "   2. 运行示例: ./results/quick_start/curl_examples.sh"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "🎉 快速启动完成！"
echo "📚 更多信息请查看: README.md"