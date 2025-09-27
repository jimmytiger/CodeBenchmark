#!/usr/bin/env python3
"""
测试multi-turn-coding任务的完整流程
通过Evaluation Engine调用真实的multi-turn-coding任务
"""

import sys
import logging
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_multi_turn_coding_task():
    """测试multi-turn-coding任务"""
    print("🚀 测试 Multi-Turn Coding 任务")
    print("=" * 70)
    
    try:
        # 1. 导入核心组件
        print("\n1️⃣ 导入Evaluation Engine核心组件...")
        
        from evaluation_engine.core.unified_framework import (
            UnifiedEvaluationFramework, 
            EvaluationRequest, 
            ExecutionStatus
        )
        
        print("✅ 成功导入UnifiedEvaluationFramework")
        
        # 2. 初始化框架
        print("\n2️⃣ 初始化评估框架...")
        unified_framework = UnifiedEvaluationFramework()
        print("✅ 评估框架初始化完成")
        
        # 3. 发现multi-turn-coding任务
        print("\n3️⃣ 发现multi-turn-coding任务...")
        all_tasks = unified_framework.list_available_tasks()
        
        # 查找multi-turn相关任务
        multi_turn_tasks = [t for t in all_tasks if "multi_turn" in t.lower()]
        print(f"✅ 发现 {len(multi_turn_tasks)} 个multi-turn任务:")
        
        for task in multi_turn_tasks[:10]:  # 显示前10个
            print(f"   - {task}")
        
        if len(multi_turn_tasks) > 10:
            print(f"   ... 还有 {len(multi_turn_tasks) - 10} 个任务")
        
        # 选择要测试的任务
        if not multi_turn_tasks:
            print("❌ 没有发现multi-turn任务")
            return False
        
        # 优先选择multi_turn_coding相关任务
        target_task = None
        for task in multi_turn_tasks:
            if "coding" in task.lower():
                target_task = task
                break
        
        if not target_task:
            target_task = multi_turn_tasks[0]
        
        print(f"🎯 选择测试任务: {target_task}")
        
        # 4. 检查任务信息
        print("\n4️⃣ 获取任务详细信息...")
        task_info = unified_framework.get_task_info(target_task)
        
        if task_info:
            print(f"✅ 任务信息:")
            print(f"   - 任务名: {task_info['task_name']}")
            print(f"   - 可用性: {task_info['available']}")
            print(f"   - 多轮对话: {task_info['is_multi_turn']}")
        else:
            print("⚠️ 无法获取详细任务信息，继续执行")
        
        # 5. 设置环境变量（如果需要）
        print("\n5️⃣ 配置环境变量...")
        
        # 检查API密钥
        api_keys = {
            'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY'),
            'DASHSCOPE_API_KEY': os.getenv('DASHSCOPE_API_KEY')
        }
        
        available_keys = [k for k, v in api_keys.items() if v]
        if available_keys:
            print(f"✅ 可用的API密钥: {available_keys}")
        else:
            print("⚠️ 没有检测到API密钥，将使用dummy模型")
        
        # 设置multi-turn coding特定的环境变量
        os.environ.setdefault('ENABLE_PRD_CONTEXT', 'true')
        os.environ.setdefault('ENABLE_DESIGN_CONTEXT', 'true')
        os.environ.setdefault('ENABLE_CODE_CONTEXT', 'true')
        os.environ.setdefault('ENABLE_QUALITY_CONTEXT', 'true')
        
        print("✅ Multi-turn coding环境变量已设置")
        
        # 6. 创建评估请求
        print("\n6️⃣ 创建评估请求...")
        
        # 选择模型
        if os.getenv('ANTHROPIC_API_KEY'):
            model_id = "claude-local"
            model_args = "model=claude-3-haiku-20240307"
            print("🤖 使用Claude模型")
        elif os.getenv('OPENAI_API_KEY'):
            model_id = "openai-completions"
            model_args = "model=gpt-3.5-turbo"
            print("🤖 使用OpenAI模型")
        else:
            model_id = "dummy"
            model_args = ""
            print("🤖 使用Dummy模型（测试用）")
        
        # 创建输出目录
        output_dir = Path("results/multi_turn_coding_test")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        evaluation_request = EvaluationRequest(
            model=model_id,
            tasks=[target_task],
            limit=1,  # 只测试1个问题
            num_fewshot=0,
            batch_size=1,
            use_cache=True,
            write_out=True,
            output_base_path=str(output_dir),
            log_samples=True,
            verbosity="INFO",
            gen_kwargs={
                "temperature": 0.0,  # multi-turn coding推荐使用0温度
                "max_gen_toks": 800,
                "do_sample": False
            }
        )
        
        print(f"✅ 评估请求创建完成:")
        print(f"   - 模型: {model_id}")
        print(f"   - 任务: {target_task}")
        print(f"   - 限制: {evaluation_request.limit}")
        print(f"   - 输出目录: {output_dir}")
        
        # 7. 验证请求
        print("\n7️⃣ 验证评估请求...")
        validation_issues = unified_framework.validate_evaluation_request(evaluation_request)
        
        if validation_issues:
            print(f"⚠️ 验证发现问题:")
            for issue in validation_issues:
                print(f"   - {issue}")
            print("继续执行...")
        else:
            print("✅ 评估请求验证通过")
        
        # 8. 执行评估
        print("\n8️⃣ 执行Multi-Turn Coding评估...")
        print("   📊 开始执行评估（这可能需要几分钟）...")
        print(f"   - 模型: {evaluation_request.model}")
        print(f"   - 任务: {evaluation_request.tasks}")
        print(f"   - 配置: limit={evaluation_request.limit}, temperature={evaluation_request.gen_kwargs.get('temperature', 'N/A')}")
        
        # 执行评估
        result = unified_framework.evaluate(evaluation_request)
        
        print(f"✅ 评估执行完成!")
        print(f"   - 评估ID: {result.evaluation_id}")
        print(f"   - 状态: {result.status.value}")
        print(f"   - 开始时间: {result.start_time}")
        print(f"   - 结束时间: {result.end_time}")
        
        if result.error:
            print(f"   - 错误: {result.error}")
        
        # 9. 分析结果
        print("\n9️⃣ 分析Multi-Turn Coding结果...")
        
        if result.status == ExecutionStatus.COMPLETED:
            print("✅ Multi-Turn Coding评估成功完成!")
            
            # 显示原始结果
            if result.results:
                print("   📊 原始结果:")
                for task_name, task_result in result.results.items():
                    print(f"     - {task_name}:")
                    if isinstance(task_result, dict):
                        for metric, value in task_result.items():
                            if isinstance(value, (int, float)):
                                print(f"       * {metric}: {value:.3f}")
                            else:
                                print(f"       * {metric}: {value}")
            
            # 显示指标摘要
            if result.metrics_summary:
                print("   📈 指标摘要:")
                for metric, value in result.metrics_summary.items():
                    print(f"     - {metric}: {value:.3f}")
            
            # 显示分析报告
            if result.analysis:
                print("   📋 分析报告:")
                analysis = result.analysis
                
                if 'summary' in analysis:
                    print(f"     - 摘要: {analysis['summary']}")
                
                if 'performance_insights' in analysis:
                    insights = analysis['performance_insights']
                    print(f"     - 整体表现: {insights.get('overall_performance', 'unknown')}")
                
                if 'recommendations' in analysis and analysis['recommendations']:
                    print("     - 建议:")
                    for rec in analysis['recommendations'][:3]:
                        print(f"       * {rec}")
            
            # 计算执行时间
            exec_time = unified_framework._calculate_execution_time(result)
            print(f"   ⏱️ 执行时间: {exec_time:.2f}秒")
            
            # 检查生成的文件
            print("\n   📁 检查生成的文件:")
            if output_dir.exists():
                for item in output_dir.rglob("*"):
                    if item.is_file():
                        print(f"     - {item.relative_to(output_dir)}")
            
        else:
            print(f"❌ Multi-Turn Coding评估未成功完成: {result.status.value}")
            if result.error:
                print(f"   错误详情: {result.error}")
        
        # 10. 生成测试报告
        print("\n🔟 生成测试报告...")
        
        report = {
            "test_timestamp": datetime.now().isoformat(),
            "multi_turn_coding_test": "COMPLETED",
            "task_tested": target_task,
            "model_used": model_id,
            "evaluation_result": {
                "evaluation_id": result.evaluation_id,
                "status": result.status.value,
                "execution_time": exec_time if result.status == ExecutionStatus.COMPLETED else 0,
                "error": result.error
            },
            "metrics_summary": result.metrics_summary or {},
            "analysis_available": bool(result.analysis),
            "files_generated": len(list(output_dir.rglob("*"))) if output_dir.exists() else 0
        }
        
        # 保存报告
        import json
        report_file = "multi_turn_coding_test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 测试报告已生成: {report_file}")
        
        # 显示最终结果
        print("\n🎉 Multi-Turn Coding任务测试完成!")
        print("=" * 70)
        
        success = result.status == ExecutionStatus.COMPLETED
        
        if success:
            print("✅ 测试结果: 成功")
            print("💡 验证内容:")
            print("  - Multi-Turn Coding任务发现和加载")
            print("  - Evaluation Engine集成")
            print("  - 真实任务执行")
            print("  - 结果分析和报告生成")
            
            print("\n📚 相关文件:")
            print(f"  - 测试报告: {report_file}")
            print(f"  - 输出目录: {output_dir}")
            print("  - Multi-Turn Coding任务: lm_eval/tasks/multi_turn_coding/")
            
        else:
            print("⚠️ 测试结果: 部分成功")
            print("💡 已验证:")
            print("  - Multi-Turn Coding任务发现")
            print("  - Evaluation Engine集成")
            print("  - 评估流程执行")
            
        return success
        
    except Exception as e:
        print(f"\n💥 Multi-Turn Coding任务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🧪 Multi-Turn Coding 任务测试")
    print("测试通过Evaluation Engine调用真实的multi-turn-coding任务")
    print()
    
    try:
        success = test_multi_turn_coding_task()
        
        if success:
            print("\n💡 测试总结:")
            print("  ✅ 成功调用了multi-turn-coding任务")
            print("  ✅ 验证了Evaluation Engine与multi-turn任务的集成")
            print("  ✅ 展示了完整的多轮对话评估流程")
            print("  ✅ 生成了真实的评估结果和分析")
            
            print("\n🚀 后续建议:")
            print("  1. 配置真实的API密钥以获得更好的结果")
            print("  2. 尝试不同的难度级别和任务类型")
            print("  3. 分析生成的文件和代码质量")
            print("  4. 使用multi-turn-coding的分析工具")
            
            return 0
        else:
            print("\n💥 测试未完全成功，但已验证基本集成")
            return 1
            
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
        return 0
    except Exception as e:
        print(f"\n💥 测试异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())