#!/usr/bin/env python3
"""
演示如何使用single-turn-scenarios任务进行评估

这个脚本展示了如何：
1. 运行不同的single-turn-scenarios任务
2. 使用不同的模型
3. 应用不同的过滤器
4. 查看结果
"""

import subprocess
import json
import os
from datetime import datetime

def run_evaluation(model, model_args, task, limit=1, output_dir="results"):
    """运行单个评估任务"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/{task}_{model.replace('-', '_')}_{timestamp}.json"
    
    cmd = [
        "python", "-m", "lm_eval",
        "--model", model,
        "--model_args", model_args,
        "--tasks", task,
        "--limit", str(limit),
        "--output_path", output_file,
        "--predict_only"  # 只生成预测，不计算复杂的metrics
    ]
    
    print(f"🚀 运行评估: {task}")
    print(f"   模型: {model} ({model_args})")
    print(f"   输出: {output_file}")
    print(f"   命令: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ 评估成功完成: {task}")
            return output_file, True
        else:
            print(f"❌ 评估失败: {task}")
            print(f"错误输出: {result.stderr}")
            return None, False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ 评估超时: {task}")
        return None, False
    except Exception as e:
        print(f"💥 评估异常: {task} - {e}")
        return None, False

def main():
    """主函数 - 演示single-turn-scenarios的使用"""
    
    print("=" * 60)
    print("🧪 Single Turn Scenarios 评估演示")
    print("=" * 60)
    print()
    
    # 确保结果目录存在
    os.makedirs("results", exist_ok=True)
    
    # 配置评估参数
    model = "claude-local"
    model_args = "model=claude-3-haiku-20240307"
    
    # 要测试的任务列表
    tasks_to_test = [
        "single_turn_scenarios_function_generation",
        "single_turn_scenarios_code_completion", 
        # "single_turn_scenarios_bug_fix",  # 暂时跳过，因为metrics有问题
        # "single_turn_scenarios_algorithm_implementation",
    ]
    
    successful_evaluations = []
    failed_evaluations = []
    
    # 运行每个任务
    for task in tasks_to_test:
        output_file, success = run_evaluation(
            model=model,
            model_args=model_args,
            task=task,
            limit=1  # 只测试1个样本
        )
        
        if success:
            successful_evaluations.append((task, output_file))
        else:
            failed_evaluations.append(task)
        
        print("-" * 40)
        print()
    
    # 总结结果
    print("📊 评估总结")
    print("=" * 60)
    print(f"✅ 成功: {len(successful_evaluations)} 个任务")
    print(f"❌ 失败: {len(failed_evaluations)} 个任务")
    print()
    
    if successful_evaluations:
        print("成功的评估:")
        for task, output_file in successful_evaluations:
            print(f"  - {task}")
            print(f"    结果文件: {output_file}")
        print()
    
    if failed_evaluations:
        print("失败的评估:")
        for task in failed_evaluations:
            print(f"  - {task}")
        print()
    
    # 展示如何查看结果
    if successful_evaluations:
        print("🔍 如何查看结果:")
        print("=" * 60)
        
        task, output_file = successful_evaluations[0]
        print(f"示例: 查看 {task} 的结果")
        print()
        
        # 查找实际的输出文件（带时间戳）
        import glob
        pattern = output_file.replace('.json', '_*.json')
        actual_files = glob.glob(pattern)
        
        if actual_files:
            actual_file = actual_files[0]
            print(f"主要结果文件: {actual_file}")
            
            # 查找样本文件
            sample_pattern = actual_file.replace('.json', '').replace('results/', 'results/samples_') + '.jsonl'
            sample_files = glob.glob(sample_pattern)
            
            if sample_files:
                sample_file = sample_files[0]
                print(f"样本输出文件: {sample_file}")
                
                print()
                print("查看样本输出的命令:")
                print(f"  cat {sample_file}")
                print()
                print("或者用Python查看:")
                print(f"  python -c \"import json; print(json.load(open('{sample_file}'))['resps'][0][0][:200])\"")
    
    print()
    print("🎯 更多使用示例:")
    print("=" * 60)
    print()
    
    print("1. 运行特定难度的任务:")
    print("   python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \\")
    print("     --tasks single_turn_scenarios_function_generation \\")
    print("     --metadata '{\"difficulty\":\"simple\"}' --limit 2")
    print()
    
    print("2. 运行特定编程语言的任务:")
    print("   python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \\")
    print("     --tasks single_turn_scenarios_code_completion \\")
    print("     --metadata '{\"language\":\"python\"}' --limit 2")
    print()
    
    print("3. 运行多个任务:")
    print("   python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \\")
    print("     --tasks single_turn_scenarios_function_generation,single_turn_scenarios_code_completion \\")
    print("     --limit 2")
    print()
    
    print("4. 使用不同的上下文模式:")
    print("   python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \\")
    print("     --tasks single_turn_scenarios_function_generation \\")
    print("     --metadata '{\"context_mode\":\"minimal_context\"}' --limit 2")
    print()
    
    print("✨ 评估演示完成!")

if __name__ == "__main__":
    main()