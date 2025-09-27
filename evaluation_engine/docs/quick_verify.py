#!/usr/bin/env python3
"""
快速验证 AI Evaluation Engine 安装和配置
"""

import sys
import os
import subprocess
import json
from pathlib import Path

def print_status(message):
    print(f"🔍 {message}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def check_python_environment():
    """检查Python环境"""
    print_status("检查Python环境...")
    
    # 检查Python版本
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print_success(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    else:
        print_error(f"Python版本过低: {version.major}.{version.minor}.{version.micro}，需要3.9+")
        return False
    
    # 检查虚拟环境
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_success("虚拟环境已激活")
    else:
        print_warning("未检测到虚拟环境，建议使用虚拟环境")
    
    return True

def check_dependencies():
    """检查关键依赖"""
    print_status("检查关键依赖...")
    
    dependencies = [
        ('lm_eval', 'lm-eval核心库'),
        ('datasets', 'HuggingFace datasets'),
        ('transformers', 'HuggingFace transformers'),
    ]
    
    # evaluation_engine 可能不在Python路径中，单独检查
    try:
        import evaluation_engine
        print_success("evaluation engine - 已安装")
    except ImportError:
        print_warning("evaluation engine - 未安装（可能在开发模式下正常）")
    
    all_good = True
    for module, description in dependencies:
        try:
            __import__(module)
            print_success(f"{description} - 已安装")
        except ImportError:
            print_error(f"{description} - 未安装")
            all_good = False
    
    return all_good

def check_api_keys():
    """检查API密钥配置"""
    print_status("检查API密钥配置...")
    
    api_keys = [
        ('ANTHROPIC_API_KEY', 'Anthropic Claude'),
        ('OPENAI_API_KEY', 'OpenAI GPT'),
        ('DEEPSEEK_API_KEY', 'DeepSeek'),
        ('DASHSCOPE_API_KEY', '通义千问'),
    ]
    
    configured_keys = 0
    for key, service in api_keys:
        if os.getenv(key):
            print_success(f"{service} API密钥 - 已配置")
            configured_keys += 1
        else:
            print_warning(f"{service} API密钥 - 未配置")
    
    if configured_keys == 0:
        print_warning("未配置任何API密钥，只能使用dummy模型测试")
    else:
        print_success(f"已配置 {configured_keys} 个API密钥")
    
    return configured_keys > 0

def check_tasks():
    """检查任务注册"""
    print_status("检查任务注册...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'lm_eval', '--tasks', 'list'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            tasks = result.stdout
            single_turn_tasks = [line for line in tasks.split('\n') if 'single_turn_scenarios' in line]
            
            if single_turn_tasks:
                print_success(f"找到 {len(single_turn_tasks)} 个single_turn_scenarios任务")
                print("  主要任务:")
                for task in single_turn_tasks[:5]:  # 显示前5个
                    print(f"    - {task.strip()}")
                if len(single_turn_tasks) > 5:
                    print(f"    ... 还有 {len(single_turn_tasks) - 5} 个任务")
                return True
            else:
                print_error("未找到single_turn_scenarios任务")
                return False
        else:
            print_error(f"任务列表获取失败: {result.stderr}")
            return False
            
    except Exception as e:
        print_error(f"任务检查失败: {e}")
        return False

def run_dummy_test():
    """运行dummy模型测试"""
    print_status("运行dummy模型测试...")
    
    try:
        cmd = [
            sys.executable, '-m', 'lm_eval',
            '--model', 'dummy',
            '--tasks', 'single_turn_scenarios_function_generation',
            '--limit', '1',
            '--predict_only',
            '--output_path', 'results/dummy_test'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print_success("Dummy模型测试通过")
            return True
        else:
            print_error(f"Dummy模型测试失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print_error("Dummy模型测试超时")
        return False
    except Exception as e:
        print_error(f"Dummy模型测试异常: {e}")
        return False

def run_api_test():
    """运行API模型测试（如果有API密钥）"""
    print_status("运行API模型测试...")
    
    # 检查可用的API密钥
    if os.getenv('ANTHROPIC_API_KEY'):
        model = 'claude-local'
        model_args = 'model=claude-3-haiku-20240307'
        service = 'Claude'
    elif os.getenv('OPENAI_API_KEY'):
        model = 'openai-completions'
        model_args = 'model=gpt-3.5-turbo'
        service = 'OpenAI'
    elif os.getenv('DEEPSEEK_API_KEY'):
        model = 'deepseek'
        model_args = 'model=deepseek-coder'
        service = 'DeepSeek'
    elif os.getenv('DASHSCOPE_API_KEY'):
        model = 'dashscope'
        model_args = 'model=qwen-turbo'
        service = '通义千问'
    else:
        print_warning("未配置API密钥，跳过API模型测试")
        return True
    
    try:
        cmd = [
            sys.executable, '-m', 'lm_eval',
            '--model', model,
            '--model_args', model_args,
            '--tasks', 'single_turn_scenarios_function_generation',
            '--limit', '1',
            '--predict_only',
            '--output_path', f'results/api_test_{service.lower().replace(" ", "_")}'
        ]
        
        print_status(f"测试 {service} 模型...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print_success(f"{service} 模型测试通过")
            return True
        else:
            print_error(f"{service} 模型测试失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print_error(f"{service} 模型测试超时")
        return False
    except Exception as e:
        print_error(f"{service} 模型测试异常: {e}")
        return False

def check_analysis_tools():
    """检查分析工具"""
    print_status("检查分析工具...")
    
    try:
        # 检查分析工具是否可以导入
        sys.path.append('lm_eval/tasks/single_turn_scenarios/analysis_tools')
        
        tools = [
            ('scenario_analysis', 'ScenarioAnalyzer'),
            ('compare_models', 'ModelComparator'),
            ('context_impact', 'ContextAnalyzer'),
            ('generate_report', 'ReportGenerator'),
        ]
        
        available_tools = 0
        for module, class_name in tools:
            try:
                mod = __import__(module)
                if hasattr(mod, class_name):
                    print_success(f"{class_name} - 可用")
                    available_tools += 1
                else:
                    print_warning(f"{class_name} - 类未找到")
            except ImportError:
                print_warning(f"{module} - 模块未找到")
        
        if available_tools > 0:
            print_success(f"分析工具检查完成，{available_tools}/{len(tools)} 个工具可用")
            return True
        else:
            print_error("分析工具不可用")
            return False
            
    except Exception as e:
        print_error(f"分析工具检查失败: {e}")
        return False

def main():
    """主验证流程"""
    print("🔧 AI Evaluation Engine 快速验证")
    print("=" * 50)
    
    checks = [
        ("Python环境", check_python_environment),
        ("依赖包", check_dependencies),
        ("API密钥", check_api_keys),
        ("任务注册", check_tasks),
        ("Dummy测试", run_dummy_test),
        ("API测试", run_api_test),
        ("分析工具", check_analysis_tools),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\n--- {name} ---")
        try:
            if check_func():
                passed += 1
        except Exception as e:
            print_error(f"{name} 检查异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"验证完成: {passed}/{total} 项检查通过")
    
    if passed == total:
        print_success("🎉 所有检查通过！系统已准备就绪")
        print("\n下一步:")
        print("1. 查看用户菜单: cat evaluation_engine/docs/user_menu.md")
        print("2. 运行完整评估: python demo_single_turn_scenarios.py")
        print("3. 运行分析工具: python demo_analysis_tools.py")
    elif passed >= total - 2:
        print_success("✅ 基本功能正常，可以开始使用")
        print("\n建议:")
        print("1. 配置更多API密钥以测试不同模型")
        print("2. 查看用户菜单了解完整功能")
    else:
        print_error("❌ 存在重要问题，请检查安装")
        print("\n建议:")
        print("1. 重新运行安装脚本: bash evaluation_engine/docs/quick_setup.sh")
        print("2. 检查依赖安装: pip install -e .[dev,api,testing,evaluation_engine]")
        print("3. 查看详细错误信息")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)