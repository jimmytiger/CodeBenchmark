#!/usr/bin/env python3
"""
AI Evaluation Engine 快速演示
展示如何运行评估并生成分析报告
"""

import subprocess
import json
import os
import sys
import glob
from datetime import datetime
from pathlib import Path

def print_status(message):
    print(f"🔍 {message}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def run_evaluation_demo():
    """运行评估演示"""
    print("🚀 AI Evaluation Engine 快速演示")
    print("=" * 50)
    
    # 确保结果目录存在
    os.makedirs("results", exist_ok=True)
    
    # 检查API密钥
    api_available = False
    model_config = None
    
    if os.getenv('ANTHROPIC_API_KEY'):
        model_config = ('claude-local', 'model=claude-3-haiku-20240307', 'Claude Haiku')
        api_available = True
    elif os.getenv('OPENAI_API_KEY'):
        model_config = ('openai-completions', 'model=gpt-3.5-turbo', 'GPT-3.5 Turbo')
        api_available = True
    elif os.getenv('DEEPSEEK_API_KEY'):
        model_config = ('deepseek', 'model=deepseek-coder', 'DeepSeek Coder')
        api_available = True
    elif os.getenv('DASHSCOPE_API_KEY'):
        model_config = ('dashscope', 'model=qwen-turbo', 'Qwen Turbo')
        api_available = True
    
    if not api_available:
        print_warning("未检测到API密钥，将使用dummy模型演示")
        model_config = ('dummy', '', 'Dummy Model')
    
    model, model_args, model_name = model_config
    
    print_status(f"使用模型: {model_name}")
    print()
    
    # 运行评估
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"results/demo_{timestamp}.json"
    
    cmd = [
        sys.executable, "-m", "lm_eval",
        "--model", model,
        "--tasks", "single_turn_scenarios_function_generation",
        "--limit", "2",  # 只测试2个样本
        "--output_path", output_file,
        "--log_samples"
    ]
    
    if model_args:
        cmd.extend(["--model_args", model_args])
    
    print_status("运行评估...")
    print(f"命令: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print_success("评估完成！")
            
            # 查找实际生成的文件
            actual_files = glob.glob(f"{output_file}_*.json")
            if actual_files:
                actual_file = actual_files[0]
                print_status(f"结果文件: {actual_file}")
                
                # 显示结果摘要
                try:
                    with open(actual_file, 'r') as f:
                        data = json.load(f)
                    
                    print("\n📊 评估结果摘要:")
                    print("-" * 30)
                    
                    if 'results' in data:
                        for task_name, task_results in data['results'].items():
                            print(f"任务: {task_name}")
                            for metric, value in task_results.items():
                                if isinstance(value, (int, float)):
                                    print(f"  {metric}: {value}")
                                else:
                                    print(f"  {metric}: {str(value)[:50]}...")
                    
                    if 'config' in data:
                        config = data['config']
                        print(f"\n配置信息:")
                        print(f"  模型: {config.get('model', 'unknown')}")
                        print(f"  样本数: {config.get('limit', 'unknown')}")
                    
                except Exception as e:
                    print_warning(f"无法解析结果文件: {e}")
                
                # 查找样本文件
                sample_pattern = actual_file.replace('.json', '').replace('results/', 'results/samples_') + '.jsonl'
                sample_files = glob.glob(sample_pattern)
                
                if sample_files:
                    sample_file = sample_files[0]
                    print_status(f"样本文件: {sample_file}")
                    
                    # 显示第一个样本
                    try:
                        with open(sample_file, 'r') as f:
                            first_line = f.readline().strip()
                            if first_line:
                                sample_data = json.loads(first_line)
                                print("\n📝 样本示例:")
                                print("-" * 30)
                                print(f"输入: {sample_data.get('doc', {}).get('prompt', 'N/A')[:100]}...")
                                if 'resps' in sample_data and sample_data['resps']:
                                    response = sample_data['resps'][0][0] if sample_data['resps'][0] else 'N/A'
                                    print(f"输出: {response[:200]}...")
                    except Exception as e:
                        print_warning(f"无法读取样本文件: {e}")
                
                return actual_file
            else:
                print_warning("未找到结果文件")
                return None
        else:
            print_error("评估失败")
            print(f"错误信息: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print_error("评估超时")
        return None
    except Exception as e:
        print_error(f"评估异常: {e}")
        return None

def run_analysis_demo(result_file=None):
    """运行分析工具演示"""
    print("\n🔍 分析工具演示")
    print("=" * 50)
    
    # 查找结果文件
    if not result_file:
        result_files = glob.glob("results/demo_*.json") + glob.glob("results/validation_*.json")
        if not result_files:
            print_warning("未找到结果文件，跳过分析演示")
            return
        result_file = result_files[0]
    
    print_status(f"分析文件: {result_file}")
    
    try:
        # 添加分析工具路径
        sys.path.append('lm_eval/tasks/single_turn_scenarios/analysis_tools')
        
        # 加载结果数据
        with open(result_file, 'r') as f:
            data = json.load(f)
        
        # 转换为分析工具期望的格式
        sample_data = []
        if 'results' in data:
            for task_name, task_results in data['results'].items():
                sample_data.append({
                    'task': task_name,
                    'model': data.get('config', {}).get('model', 'unknown'),
                    'scenario': task_name.replace('single_turn_scenarios_', ''),
                    'difficulty': 'simple',
                    'language': 'python',
                    'context_mode': 'no_context',
                    'metrics': task_results
                })
        
        if not sample_data:
            print_warning("未找到有效的分析数据")
            return
        
        print_success(f"加载了 {len(sample_data)} 个分析样本")
        
        # 测试分析工具
        tools_tested = 0
        
        # 测试 ScenarioAnalyzer
        try:
            from scenario_analysis import ScenarioAnalyzer
            analyzer = ScenarioAnalyzer(sample_data)
            print_success("ScenarioAnalyzer - 初始化成功")
            
            if hasattr(analyzer, 'df') and len(analyzer.df) > 0:
                print(f"  数据框形状: {analyzer.df.shape}")
            tools_tested += 1
        except Exception as e:
            print_warning(f"ScenarioAnalyzer - 失败: {e}")
        
        # 测试 ModelComparator
        try:
            from compare_models import ModelComparator
            comparator = ModelComparator(sample_data)
            print_success("ModelComparator - 初始化成功")
            tools_tested += 1
        except Exception as e:
            print_warning(f"ModelComparator - 失败: {e}")
        
        # 测试 ContextAnalyzer
        try:
            from context_impact import ContextAnalyzer
            context_analyzer = ContextAnalyzer(sample_data)
            print_success("ContextAnalyzer - 初始化成功")
            tools_tested += 1
        except Exception as e:
            print_warning(f"ContextAnalyzer - 失败: {e}")
        
        # 测试 ReportGenerator
        try:
            from generate_report import ReportGenerator
            generator = ReportGenerator(sample_data)
            print_success("ReportGenerator - 初始化成功")
            tools_tested += 1
        except Exception as e:
            print_warning(f"ReportGenerator - 失败: {e}")
        
        print(f"\n📊 分析工具测试完成: {tools_tested}/4 个工具可用")
        
        if tools_tested > 0:
            print_success("分析工具演示成功！")
            print("\n可用的分析功能:")
            print("- 场景分析 (ScenarioAnalyzer)")
            print("- 模型比较 (ModelComparator)")
            print("- 上下文影响分析 (ContextAnalyzer)")
            print("- 报告生成 (ReportGenerator)")
        else:
            print_warning("分析工具不可用，请检查安装")
        
    except Exception as e:
        print_error(f"分析演示失败: {e}")

def show_next_steps():
    """显示后续步骤"""
    print("\n🎯 后续步骤")
    print("=" * 50)
    
    print("1. 查看完整用户菜单:")
    print("   cat evaluation_engine/docs/user_menu.md")
    
    print("\n2. 运行更多评估:")
    print("   python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \\")
    print("     --tasks single_turn_scenarios_function_generation,single_turn_scenarios_code_completion \\")
    print("     --limit 5 --output_path results/my_test.json")
    
    print("\n3. 运行完整演示:")
    print("   python demo_single_turn_scenarios.py")
    
    print("\n4. 运行分析工具:")
    print("   python demo_analysis_tools.py")
    
    print("\n5. 查看测试套件:")
    print("   python -m pytest evaluation_engine/tests/ -v")
    
    print("\n6. 配置更多API密钥:")
    print("   export ANTHROPIC_API_KEY='your_key'")
    print("   export OPENAI_API_KEY='your_key'")
    print("   export DEEPSEEK_API_KEY='your_key'")
    print("   export DASHSCOPE_API_KEY='your_key'")

def main():
    """主演示流程"""
    try:
        # 运行评估演示
        result_file = run_evaluation_demo()
        
        # 运行分析演示
        run_analysis_demo(result_file)
        
        # 显示后续步骤
        show_next_steps()
        
        print("\n🎉 快速演示完成！")
        print("AI Evaluation Engine 已准备就绪，可以开始使用了！")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中出现异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()