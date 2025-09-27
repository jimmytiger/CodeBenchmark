#!/bin/bash

# AI Evaluation Engine API 快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 AI Evaluation Engine API 快速启动${NC}"
echo "=================================================="

# 检查Python环境
echo -e "\n${YELLOW}1️⃣ 检查Python环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3 已安装${NC}"

# 检查依赖
echo -e "\n${YELLOW}2️⃣ 检查依赖包...${NC}"
missing_deps=()

for dep in fastapi uvicorn pydantic; do
    if ! python3 -c "import $dep" 2>/dev/null; then
        missing_deps+=($dep)
    fi
done

if [ ${#missing_deps[@]} -ne 0 ]; then
    echo -e "${YELLOW}⚠️ 缺少依赖包: ${missing_deps[*]}${NC}"
    echo "正在安装..."
    pip install fastapi uvicorn pydantic PyJWT python-multipart
    echo -e "${GREEN}✅ 依赖包安装完成${NC}"
else
    echo -e "${GREEN}✅ 所有依赖包已安装${NC}"
fi

# 检查lm-eval
echo -e "\n${YELLOW}3️⃣ 检查lm-eval框架...${NC}"
if ! python3 -c "import lm_eval" 2>/dev/null; then
    echo -e "${YELLOW}⚠️ lm-eval未安装，正在安装...${NC}"
    pip install lm-eval
    echo -e "${GREEN}✅ lm-eval安装完成${NC}"
else
    echo -e "${GREEN}✅ lm-eval已安装${NC}"
fi

# 检查端口
echo -e "\n${YELLOW}4️⃣ 检查端口8000...${NC}"
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ 端口8000被占用，正在释放...${NC}"
    pkill -f "python.*api_server.py" 2>/dev/null || true
    sleep 2
fi
echo -e "${GREEN}✅ 端口8000可用${NC}"

# 启动服务器
echo -e "\n${YELLOW}5️⃣ 启动API服务器...${NC}"
if [ -f "real_api_server.py" ]; then
    echo "使用真实评估服务器..."
    python3 real_api_server.py &
    SERVER_PID=$!
    SERVER_TYPE="real"
elif [ -f "simple_api_server.py" ]; then
    echo "使用简化测试服务器..."
    python3 simple_api_server.py &
    SERVER_PID=$!
    SERVER_TYPE="simple"
else
    echo -e "${RED}❌ 找不到API服务器文件${NC}"
    exit 1
fi

# 等待服务器启动
echo "等待服务器启动..."
sleep 5

# 检查服务器状态
echo -e "\n${YELLOW}6️⃣ 验证服务器状态...${NC}"
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ API服务器启动成功！${NC}"
else
    echo -e "${RED}❌ API服务器启动失败${NC}"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# 显示服务信息
echo -e "\n${BLUE}🌐 服务信息${NC}"
echo "----------------------------------------"
echo "服务器类型: $SERVER_TYPE"
echo "服务地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "健康检查: http://localhost:8000/health"
echo "进程ID: $SERVER_PID"

echo -e "\n${BLUE}🔐 默认用户账号${NC}"
echo "----------------------------------------"
echo "管理员: admin / admin123"
echo "评估员: evaluator / eval123"

# 提供测试选项
echo -e "\n${YELLOW}选择下一步操作:${NC}"
echo "1) 运行API功能测试"
echo "2) 运行curl命令测试"
echo "3) 查看API文档（浏览器）"
echo "4) 仅保持服务器运行"
echo "5) 停止服务器并退出"

read -p "请选择 (1-5): " choice

case $choice in
    1)
        echo -e "\n${YELLOW}运行API功能测试...${NC}"
        if [ -f "test_real_lm_eval.py" ]; then
            python3 test_real_lm_eval.py
        else
            echo -e "${RED}❌ 找不到测试文件 test_real_lm_eval.py${NC}"
        fi
        ;;
    2)
        echo -e "\n${YELLOW}运行curl命令测试...${NC}"
        if [ -f "curl_test_examples.sh" ]; then
            chmod +x curl_test_examples.sh
            ./curl_test_examples.sh
        else
            echo -e "${RED}❌ 找不到测试文件 curl_test_examples.sh${NC}"
        fi
        ;;
    3)
        echo -e "\n${YELLOW}打开API文档...${NC}"
        if command -v open &> /dev/null; then
            open http://localhost:8000/docs
        elif command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:8000/docs
        else
            echo "请手动访问: http://localhost:8000/docs"
        fi
        ;;
    4)
        echo -e "\n${GREEN}✨ 服务器正在运行中...${NC}"
        echo "按 Ctrl+C 停止服务器"
        wait $SERVER_PID
        ;;
    5)
        echo -e "\n${YELLOW}停止服务器...${NC}"
        kill $SERVER_PID 2>/dev/null || true
        echo -e "${GREEN}✅ 服务器已停止${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ 无效选择${NC}"
        ;;
esac

# 清理函数
cleanup() {
    echo -e "\n${YELLOW}正在停止服务器...${NC}"
    kill $SERVER_PID 2>/dev/null || true
    echo -e "${GREEN}✅ 清理完成${NC}"
}

# 设置信号处理
trap cleanup EXIT INT TERM

# 如果选择了测试，询问是否保持服务器运行
if [ "$choice" = "1" ] || [ "$choice" = "2" ]; then
    echo -e "\n${YELLOW}是否保持服务器运行？ (y/n):${NC}"
    read -p "" keep_running
    
    if [ "$keep_running" = "y" ] || [ "$keep_running" = "Y" ]; then
        echo -e "\n${GREEN}✨ 服务器继续运行中...${NC}"
        echo "按 Ctrl+C 停止服务器"
        wait $SERVER_PID
    fi
fi