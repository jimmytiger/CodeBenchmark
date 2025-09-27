#!/bin/bash

# AI Evaluation Engine - 一键安装设置脚本
# 快速设置evaluation engine执行环境

set -e  # 遇到错误立即退出

echo "🚀 AI Evaluation Engine 一键安装开始..."

# 颜色代码
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 打印函数
print_status() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 检查Python版本
check_python() {
    print_status "检查Python版本..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
            print_success "Python $PYTHON_VERSION 已找到"
            PYTHON_CMD="python3"
        else
            print_error "需要Python 3.9+，当前版本: $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "未找到Python 3。请安装Python 3.9+"
        exit 1
    fi
}

# 检查Docker
check_docker() {
    print_status "检查Docker安装..."
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            print_success "Docker可用且正在运行"
            DOCKER_AVAILABLE=true
        else
            print_warning "Docker已安装但未运行"
            DOCKER_AVAILABLE=false
        fi
    else
        print_warning "未找到Docker。安全代码执行功能将受限。"
        DOCKER_AVAILABLE=false
    fi
}

# 创建虚拟环境
setup_venv() {
    print_status "设置Python虚拟环境..."
    
    # 回到项目根目录
    cd "$(dirname "$0")/../.."
    
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        print_success "虚拟环境已创建"
    else
        print_status "虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    print_success "虚拟环境已激活"
    
    # 升级pip
    print_status "升级pip..."
    pip install --upgrade pip
}

# 安装依赖
install_dependencies() {
    print_status "安装核心依赖..."
    
    # 安装基础依赖
    pip install -e ".[dev,api,testing,evaluation_engine]"
    
    # 安装API相关依赖
    if [ -f "requirements_api.txt" ]; then
        pip install -r requirements_api.txt
    fi
    
    print_success "核心依赖安装完成"
    
    # 安装可选依赖
    print_status "安装可选依赖..."
    pip install jupyter notebook ipywidgets plotly pandas seaborn
    
    if [ "$DOCKER_AVAILABLE" = true ]; then
        pip install docker
        print_success "Docker客户端已安装"
    fi
    
    print_success "所有依赖安装完成"
}

# 设置配置文件
setup_config() {
    print_status "设置配置文件..."
    
    # 创建环境配置文件
    if [ ! -f ".env" ]; then
        cat > .env << 'EOF'
# AI Evaluation Engine 环境配置

# API Keys (请填入您的API密钥)
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
DASHSCOPE_API_KEY=your_dashscope_key_here

# 数据库配置
DATABASE_URL=sqlite:///evaluation_engine.db

# Redis配置 (可选)
REDIS_URL=redis://localhost:6379

# 安全设置
SECRET_KEY=your_secret_key_here
ENABLE_SECURE_EXECUTION=true

# 日志级别
LOG_LEVEL=INFO

# 结果存储路径
RESULTS_DIR=results
LOGS_DIR=logs
CACHE_DIR=cache
EOF
        print_success "环境配置文件已创建 (.env)"
        print_warning "请编辑 .env 文件添加您的API密钥"
    else
        print_status "环境配置文件已存在"
    fi
    
    # 创建目录结构
    mkdir -p results logs cache
    mkdir -p evaluation_engine/data
    
    print_success "目录结构已创建"
}

# 运行基础测试
run_tests() {
    print_status "运行基础功能测试..."
    
    # 测试lm-eval集成
    if python -c "import lm_eval; print('lm-eval导入成功')" 2>/dev/null; then
        print_success "lm-eval集成正常"
    else
        print_error "lm-eval集成失败"
        exit 1
    fi
    
    # 测试evaluation engine
    if python -c "import evaluation_engine; print('Evaluation engine导入成功')" 2>/dev/null; then
        print_success "Evaluation engine正常"
    else
        print_error "Evaluation engine导入失败"
        exit 1
    fi
    
    # 运行简单测试
    print_status "运行简单测试..."
    if python -c "
from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
framework = UnifiedEvaluationFramework()
print('框架初始化成功')
" 2>/dev/null; then
        print_success "框架测试通过"
    else
        print_warning "框架测试有问题（可能由于缺少API密钥）"
    fi
}

# 主安装流程
main() {
    echo "🔧 AI Evaluation Engine 一键安装"
    echo "=================================="
    
    check_python
    check_docker
    setup_venv
    install_dependencies
    setup_config
    run_tests
    
    echo ""
    echo "🎉 安装完成！"
    echo "============="
    echo ""
    echo "下一步操作："
    echo "1. 编辑 .env 文件添加您的API密钥"
    echo "2. 激活虚拟环境: source venv/bin/activate"
    echo "3. 查看用户菜单: cat evaluation_engine/docs/user_menu.md"
    echo "4. 运行快速测试: python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation --limit 1 --predict_only"
    echo ""
    echo "完整使用流程："
    echo "- evaluation_engine/docs/user_menu.md - 详细使用菜单和命令"
    echo "- evaluation_engine/tests/README.md - 测试套件说明"
    echo "- README.md - 项目总体说明"
    echo ""
    echo "快速验证命令："
    echo "export ANTHROPIC_API_KEY='your_key_here'"
    echo "python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \\"
    echo "  --tasks single_turn_scenarios_function_generation --limit 1"
    echo ""
    print_success "准备开始评估AI模型！🚀"
}

# 运行主函数
main "$@"