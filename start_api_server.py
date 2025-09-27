#!/usr/bin/env python3
"""
AI Evaluation Engine API Server 启动脚本
简化版本，用于本地部署和测试
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from evaluation_engine.api.gateway import APIGateway
    from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
    from evaluation_engine.core.task_registration import TaskRegistry
    from evaluation_engine.core.advanced_model_config import AdvancedModelConfigurationManager
    from evaluation_engine.core.analysis_engine import AnalysisEngine
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖包")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """检查环境变量和依赖"""
    logger.info("检查环境配置...")
    
    # 检查API密钥（可选）
    api_keys = {
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY'),
        'DASHSCOPE_API_KEY': os.getenv('DASHSCOPE_API_KEY')
    }
    
    missing_keys = [key for key, value in api_keys.items() if not value]
    if missing_keys:
        logger.warning(f"缺少API密钥: {missing_keys}")
        logger.info("某些模型功能可能受限，但服务仍可启动")
    else:
        logger.info("所有API密钥已配置")
    
    return True

def main():
    """主函数"""
    try:
        logger.info("🚀 启动 AI Evaluation Engine API 服务器")
        logger.info("=" * 60)
        
        # 检查环境
        if not check_environment():
            logger.error("环境检查失败")
            return 1
        
        # 初始化组件
        logger.info("1️⃣ 初始化评估框架...")
        framework = UnifiedEvaluationFramework()
        
        logger.info("2️⃣ 初始化任务注册表...")
        task_registry = TaskRegistry()
        
        logger.info("3️⃣ 初始化模型配置管理器...")
        model_config_manager = AdvancedModelConfigurationManager()
        
        logger.info("4️⃣ 初始化分析引擎...")
        analysis_engine = AnalysisEngine()
        
        # 创建API网关
        logger.info("5️⃣ 创建API网关...")
        gateway = APIGateway(framework, task_registry, model_config_manager, analysis_engine)
        
        # 显示启动信息
        logger.info("🌐 服务器配置:")
        logger.info(f"   - 主机: 0.0.0.0")
        logger.info(f"   - 端口: 8000")
        logger.info(f"   - API文档: http://localhost:8000/docs")
        logger.info(f"   - 健康检查: http://localhost:8000/health")
        
        logger.info("🔐 默认用户账号:")
        logger.info(f"   - 管理员: admin / admin123")
        logger.info(f"   - 评估员: evaluator / eval123")
        
        logger.info("🚀 启动服务器...")
        logger.info("按 Ctrl+C 停止服务器")
        
        # 启动服务器
        gateway.run(host='0.0.0.0', port=8000, reload=False)
        
    except KeyboardInterrupt:
        logger.info("\n👋 服务器已停止")
        return 0
    except Exception as e:
        logger.error(f"💥 启动失败: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)