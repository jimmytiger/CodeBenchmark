#!/usr/bin/env python3
"""
AI Evaluation Engine 高级配置示例

这个文件包含了各种高级配置的完整示例，展示如何：
1. 配置不同类型的模型
2. 设置任务特定的优化参数
3. 实现A/B测试
4. 配置性能监控和自动扩展
5. 批量评估和比较分析
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any

# 导入evaluation engine组件
from evaluation_engine.core.unified_framework import (
    UnifiedEvaluationFramework, 
    EvaluationRequest,
    EvaluationMode,
    BusinessScenario
)
from evaluation_engine.core.advanced_model_config import (
    AdvancedModelConfigurationManager,
    ModelConfiguration,
    TaskType,
    OptimizationStrategy,
    RateLimitConfig,
    ABTestManager,
    PerformanceMonitor
)
from evaluation_engine.core.model_adapters import ModelType


class AdvancedConfigurationExamples:
    """高级配置示例类"""
    
    def __init__(self):
        self.framework = UnifiedEvaluationFramework()
        self.config_manager = AdvancedModelConfigurationManager()
        self.ab_test_manager = ABTestManager()
        self.performance_monitor = PerformanceMonitor()
        
    def setup_claude_configurations(self) -> Dict[str, ModelConfiguration]:
        """设置Claude模型的各种配置"""
        
        configurations = {}
        
        # 1. 基础Claude配置
        base_claude_config = ModelConfiguration(
            model_id="claude-3-haiku",
            model_type=ModelType.ANTHROPIC_CLAUDE,
            
            # 生成参数
            temperature=0.7,
            max_tokens=2048,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop_sequences=["```", "\n\n"],
            
            # API配置
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            timeout=30.0,
            
            # 速率限制
            rate_limit_config=RateLimitConfig(
                requests_per_minute=60,
                tokens_per_minute=100000,
                concurrent_requests=5,
                retry_attempts=3,
                backoff_factor=2.0
            ),
            
            # 成本管理
            max_cost_per_request=1.0,
            daily_budget=100.0,
            
            # 性能目标
            target_response_time=5.0,
            target_success_rate=0.95
        )
        
        # 2. 代码补全优化配置
        code_completion_config = ModelConfiguration(**base_claude_config.to_dict())
        code_completion_config.model_id = "claude-3-haiku-code-completion"
        code_completion_config.temperature = 0.2
        code_completion_config.max_tokens = 512
        code_completion_config.stop_sequences = ["\n\n", "```", "def ", "class "]
        code_completion_config.task_optimizations = {
            TaskType.CODE_COMPLETION: {
                "temperature": 0.2,
                "max_tokens": 512,
                "top_p": 0.8,
                "stop_sequences": ["\n\n", "```"]
            }
        }
        
        # 3. 函数生成优化配置
        function_generation_config = ModelConfiguration(**base_claude_config.to_dict())
        function_generation_config.model_id = "claude-3-haiku-function-gen"
        function_generation_config.temperature = 0.3
        function_generation_config.max_tokens = 1024
        function_generation_config.task_optimizations = {
            TaskType.FUNCTION_GENERATION: {
                "temperature": 0.3,
                "max_tokens": 1024,
                "top_p": 0.9,
                "stop_sequences": ["\n\ndef ", "\n\nclass "]
            }
        }
        
        # 4. Bug修复优化配置
        bug_fix_config = ModelConfiguration(**base_claude_config.to_dict())
        bug_fix_config.model_id = "claude-3-haiku-bug-fix"
        bug_fix_config.temperature = 0.1
        bug_fix_config.max_tokens = 1024
        bug_fix_config.top_p = 0.8
        bug_fix_config.task_optimizations = {
            TaskType.BUG_FIX: {
                "temperature": 0.1,
                "max_tokens": 1024,
                "top_p": 0.8,
                "stop_sequences": ["```"]
            }
        }
        
        # 5. 高性能配置（更快响应）
        high_performance_config = ModelConfiguration(**base_claude_config.to_dict())
        high_performance_config.model_id = "claude-3-haiku-high-perf"
        high_performance_config.max_tokens = 512
        high_performance_config.target_response_time = 3.0
        high_performance_config.rate_limit_config.concurrent_requests = 10
        
        # 6. 成本优化配置
        cost_optimized_config = ModelConfiguration(**base_claude_config.to_dict())
        cost_optimized_config.model_id = "claude-3-haiku-cost-opt"
        cost_optimized_config.max_tokens = 256
        cost_optimized_config.max_cost_per_request = 0.5
        cost_optimized_config.daily_budget = 50.0
        
        configurations.update({
            "base": base_claude_config,
            "code_completion": code_completion_config,
            "function_generation": function_generation_config,
            "bug_fix": bug_fix_config,
            "high_performance": high_performance_config,
            "cost_optimized": cost_optimized_config
        })
        
        return configurations
    
    def setup_multi_model_configurations(self) -> Dict[str, ModelConfiguration]:
        """设置多种模型的配置"""
        
        configurations = {}
        
        # Claude配置
        claude_config = ModelConfiguration(
            model_id="claude-3-haiku",
            model_type=ModelType.ANTHROPIC_CLAUDE,
            temperature=0.7,
            max_tokens=2048,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            rate_limit_config=RateLimitConfig(
                requests_per_minute=60,
                tokens_per_minute=100000
            )
        )
        
        # OpenAI配置
        openai_config = ModelConfiguration(
            model_id="gpt-3.5-turbo",
            model_type=ModelType.OPENAI_GPT,
            temperature=0.7,
            max_tokens=2048,
            api_key=os.getenv("OPENAI_API_KEY"),
            rate_limit_config=RateLimitConfig(
                requests_per_minute=60,
                tokens_per_minute=90000
            ),
            max_cost_per_request=0.5
        )
        
        # DeepSeek配置
        deepseek_config = ModelConfiguration(
            model_id="deepseek-coder",
            model_type=ModelType.DEEPSEEK,
            temperature=0.7,
            max_tokens=2048,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            rate_limit_config=RateLimitConfig(
                requests_per_minute=100,
                tokens_per_minute=200000
            ),
            max_cost_per_request=0.1
        )
        
        # 通义千问配置
        qwen_config = ModelConfiguration(
            model_id="qwen-plus",
            model_type=ModelType.DASHSCOPE,
            temperature=0.7,
            max_tokens=2048,
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            rate_limit_config=RateLimitConfig(
                requests_per_minute=60,
                tokens_per_minute=120000
            ),
            max_cost_per_request=0.3
        )
        
        configurations.update({
            "claude": claude_config,
            "openai": openai_config,
            "deepseek": deepseek_config,
            "qwen": qwen_config
        })
        
        return configurations
    
    def setup_ab_testing_example(self):
        """设置A/B测试示例"""
        
        print("🧪 设置A/B测试示例")
        
        # 创建不同温度设置的变体
        low_temp_config = ModelConfiguration(
            model_id="claude-3-haiku",
            model_type=ModelType.ANTHROPIC_CLAUDE,
            temperature=0.2,
            max_tokens=1024,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        medium_temp_config = ModelConfiguration(
            model_id="claude-3-haiku",
            model_type=ModelType.ANTHROPIC_CLAUDE,
            temperature=0.5,
            max_tokens=1024,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        high_temp_config = ModelConfiguration(
            model_id="claude-3-haiku",
            model_type=ModelType.ANTHROPIC_CLAUDE,
            temperature=0.8,
            max_tokens=1024,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # 创建A/B测试
        test_config = self.ab_test_manager.create_ab_test(
            test_id="temperature_optimization_001",
            description="优化代码补全任务的温度参数",
            variants={
                "low_temp": low_temp_config,
                "medium_temp": medium_temp_config,
                "high_temp": high_temp_config
            },
            traffic_split={
                "low_temp": 0.33,
                "medium_temp": 0.33,
                "high_temp": 0.34
            },
            success_metric="quality_score",
            minimum_samples=30,  # 降低样本要求以便演示
            confidence_level=0.95,
            max_duration_hours=2  # 2小时测试
        )
        
        # 启动测试
        self.ab_test_manager.start_ab_test("temperature_optimization_001")
        print("✅ A/B测试已启动")
        
        return test_config
    
    def run_ab_test_simulation(self, test_id: str, num_samples: int = 30):
        """模拟运行A/B测试"""
        
        print(f"🔄 模拟运行A/B测试: {test_id}")
        
        import random
        import time
        
        for i in range(num_samples):
            # 选择变体
            variant_name, config = self.ab_test_manager.select_variant(test_id)
            
            # 模拟评估结果
            # 低温度通常有更好的代码质量但可能缺乏创造性
            if variant_name == "low_temp":
                quality = random.uniform(0.8, 0.95)
                response_time = random.uniform(2.0, 4.0)
                success = random.random() > 0.05
            elif variant_name == "medium_temp":
                quality = random.uniform(0.75, 0.90)
                response_time = random.uniform(2.5, 5.0)
                success = random.random() > 0.08
            else:  # high_temp
                quality = random.uniform(0.65, 0.85)
                response_time = random.uniform(3.0, 6.0)
                success = random.random() > 0.12
            
            cost = random.uniform(0.01, 0.05)
            
            # 记录结果
            self.ab_test_manager.record_test_result(
                test_id=test_id,
                variant_name=variant_name,
                response_time=response_time,
                success=success,
                cost=cost,
                quality=quality
            )
            
            if (i + 1) % 10 == 0:
                print(f"  已完成 {i + 1}/{num_samples} 个样本")
        
        print("✅ A/B测试模拟完成")
    
    def analyze_ab_test_results(self, test_id: str):
        """分析A/B测试结果"""
        
        print(f"📊 分析A/B测试结果: {test_id}")
        
        analysis = self.ab_test_manager.analyze_ab_test(test_id)
        
        print(f"\n测试描述: {analysis['description']}")
        print(f"测试状态: {'进行中' if analysis['is_active'] else '已完成'}")
        print(f"获胜变体: {analysis['winner']}")
        print(f"统计显著性: {'是' if analysis['significant'] else '否'}")
        print(f"置信度: {analysis['confidence']:.1%}")
        
        print("\n各变体详细结果:")
        print("-" * 60)
        
        for variant_name, metrics in analysis['variants'].items():
            print(f"\n{variant_name}:")
            print(f"  样本数量: {metrics['sample_size']}")
            print(f"  平均响应时间: {metrics['response_time_avg']:.2f}s")
            print(f"  成功率: {metrics['success_rate']:.1%}")
            print(f"  平均成本: ${metrics['cost_per_request']:.4f}")
            print(f"  质量分数: {metrics['quality_score']:.3f}")
            print(f"  综合性能分数: {metrics['performance_score']:.3f}")
        
        # 获取最佳配置
        best_config = self.ab_test_manager.get_best_configuration(test_id)
        if best_config:
            print(f"\n🏆 最佳配置:")
            print(f"  温度: {best_config.temperature}")
            print(f"  最大令牌数: {best_config.max_tokens}")
        
        return analysis
    
    def setup_performance_monitoring(self):
        """设置性能监控"""
        
        print("📈 设置性能监控")
        
        # 配置监控阈值
        self.performance_monitor.scaling_thresholds = {
            'response_time_high': 8.0,  # 8秒响应时间阈值
            'error_rate_high': 0.05,    # 5%错误率阈值
            'success_rate_low': 0.9     # 90%成功率阈值
        }
        
        # 启用自动扩展
        self.performance_monitor.auto_scaling_enabled = True
        
        # 开始监控
        self.performance_monitor.start_monitoring()
        
        print("✅ 性能监控已启动")
    
    def simulate_performance_data(self, model_id: str, num_requests: int = 50):
        """模拟性能数据"""
        
        print(f"📊 为模型 {model_id} 模拟 {num_requests} 个请求的性能数据")
        
        import random
        import time
        
        for i in range(num_requests):
            # 模拟不同的性能场景
            if i < 20:  # 前20个请求表现良好
                response_time = random.uniform(2.0, 4.0)
                success = random.random() > 0.02
                cost = random.uniform(0.01, 0.03)
                quality = random.uniform(0.8, 0.95)
            elif i < 35:  # 中间15个请求性能下降
                response_time = random.uniform(5.0, 8.0)
                success = random.random() > 0.08
                cost = random.uniform(0.02, 0.05)
                quality = random.uniform(0.7, 0.85)
            else:  # 最后15个请求恢复正常
                response_time = random.uniform(3.0, 5.0)
                success = random.random() > 0.03
                cost = random.uniform(0.015, 0.035)
                quality = random.uniform(0.75, 0.9)
            
            # 记录性能数据
            self.performance_monitor.record_performance(
                model_id=model_id,
                response_time=response_time,
                success=success,
                cost=cost,
                quality=quality
            )
            
            if (i + 1) % 10 == 0:
                print(f"  已记录 {i + 1}/{num_requests} 个请求")
        
        print("✅ 性能数据模拟完成")
    
    def analyze_performance_data(self, model_id: str):
        """分析性能数据"""
        
        print(f"📈 分析模型 {model_id} 的性能数据")
        
        # 获取性能摘要
        summary = self.performance_monitor.get_performance_summary(model_id)
        
        print(f"\n性能摘要:")
        print(f"  平均响应时间: {summary['response_time_avg']:.2f}s")
        print(f"  95%响应时间: {summary['response_time_p95']:.2f}s")
        print(f"  成功率: {summary['success_rate']:.1%}")
        print(f"  错误率: {summary['error_rate']:.1%}")
        print(f"  平均成本: ${summary['cost_per_request']:.4f}")
        print(f"  质量分数: {summary['quality_score']:.3f}")
        print(f"  总请求数: {summary['total_requests']}")
        
        # 获取扩展建议
        recommendations = self.performance_monitor.get_scaling_recommendations(model_id)
        
        if recommendations:
            print(f"\n🔧 扩展建议:")
            for rec in recommendations:
                print(f"  • {rec['reason']}: {rec['action']}")
                print(f"    当前值: {rec['current_value']:.3f}, 阈值: {rec['threshold']:.3f}")
        else:
            print(f"\n✅ 性能良好，无需扩展调整")
        
        return summary, recommendations
    
    async def run_batch_evaluation_example(self):
        """运行批量评估示例"""
        
        print("🚀 运行批量评估示例")
        
        # 定义要测试的模型和配置
        test_scenarios = [
            {
                "name": "claude_conservative",
                "model": "claude-local",
                "model_args": "model=claude-3-haiku-20240307",
                "config": {"temperature": 0.3, "max_gen_toks": 512}
            },
            {
                "name": "claude_balanced",
                "model": "claude-local", 
                "model_args": "model=claude-3-haiku-20240307",
                "config": {"temperature": 0.7, "max_gen_toks": 1024}
            },
            {
                "name": "claude_creative",
                "model": "claude-local",
                "model_args": "model=claude-3-haiku-20240307", 
                "config": {"temperature": 0.9, "max_gen_toks": 1024}
            }
        ]
        
        # 定义测试任务
        test_tasks = [
            "single_turn_scenarios_function_generation",
            "single_turn_scenarios_code_completion"
        ]
        
        results = {}
        
        # 并行执行评估
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            for scenario in test_scenarios:
                # 创建评估请求
                request = EvaluationRequest(
                    model=scenario["model"],
                    tasks=test_tasks,
                    limit=3,  # 限制样本数量
                    gen_kwargs=scenario["config"],
                    output_base_path=f"results/batch_{scenario['name']}",
                    log_samples=True,
                    verbosity="INFO"
                )
                
                # 提交评估任务
                future = executor.submit(self.framework.evaluate, request)
                futures.append((scenario["name"], future))
            
            # 收集结果
            for scenario_name, future in futures:
                try:
                    result = future.result(timeout=300)  # 5分钟超时
                    results[scenario_name] = result
                    
                    if result.status.value == "completed":
                        exec_time = self.framework._calculate_execution_time(result)
                        avg_score = sum(result.metrics_summary.values()) / len(result.metrics_summary) if result.metrics_summary else 0
                        print(f"✅ {scenario_name}: 平均分数 {avg_score:.3f}, 时间 {exec_time:.1f}s")
                    else:
                        print(f"❌ {scenario_name}: {result.error}")
                        
                except Exception as e:
                    print(f"💥 {scenario_name}: {e}")
        
        # 生成比较报告
        self.generate_comparison_report(results, test_scenarios)
        
        return results
    
    def generate_comparison_report(self, results: Dict, scenarios: List[Dict]):
        """生成比较报告"""
        
        print("\n📊 生成比较报告")
        print("=" * 60)
        
        # 收集性能数据
        performance_data = []
        
        for scenario in scenarios:
            scenario_name = scenario["name"]
            if scenario_name in results:
                result = results[scenario_name]
                
                if result.status.value == "completed" and result.metrics_summary:
                    avg_score = sum(result.metrics_summary.values()) / len(result.metrics_summary)
                    exec_time = self.framework._calculate_execution_time(result)
                    
                    performance_data.append({
                        "name": scenario_name,
                        "config": scenario["config"],
                        "avg_score": avg_score,
                        "exec_time": exec_time,
                        "tasks_completed": len(result.request.tasks)
                    })
        
        # 排序并显示结果
        performance_data.sort(key=lambda x: x["avg_score"], reverse=True)
        
        print("🏆 性能排名:")
        for i, data in enumerate(performance_data, 1):
            print(f"\n{i}. {data['name']}")
            print(f"   平均分数: {data['avg_score']:.3f}")
            print(f"   执行时间: {data['exec_time']:.1f}s")
            print(f"   配置: {data['config']}")
        
        # 生成建议
        if performance_data:
            best_performer = performance_data[0]
            fastest = min(performance_data, key=lambda x: x["exec_time"])
            
            print(f"\n💡 建议:")
            print(f"• 最佳性能配置: {best_performer['name']} (分数: {best_performer['avg_score']:.3f})")
            print(f"• 最快执行配置: {fastest['name']} (时间: {fastest['exec_time']:.1f}s)")
            
            if best_performer != fastest:
                print(f"• 如需平衡性能和速度，考虑调整参数介于两者之间")
    
    def save_configuration_templates(self):
        """保存配置模板"""
        
        print("💾 保存配置模板")
        
        # Claude配置模板
        claude_templates = self.setup_claude_configurations()
        
        # 多模型配置模板
        multi_model_templates = self.setup_multi_model_configurations()
        
        # 保存为JSON文件
        templates = {
            "claude_configurations": {k: v.to_dict() for k, v in claude_templates.items()},
            "multi_model_configurations": {k: v.to_dict() for k, v in multi_model_templates.items()},
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "description": "AI Evaluation Engine configuration templates",
                "version": "1.0.0"
            }
        }
        
        with open("evaluation_engine/docs/config_templates.json", "w") as f:
            json.dump(templates, f, indent=2, default=str)
        
        print("✅ 配置模板已保存到 evaluation_engine/docs/config_templates.json")


async def main():
    """主函数 - 运行所有示例"""
    
    print("🎯 AI Evaluation Engine 高级配置示例")
    print("=" * 60)
    
    # 创建示例实例
    examples = AdvancedConfigurationExamples()
    
    try:
        # 1. 设置模型配置
        print("\n1️⃣ 设置模型配置")
        claude_configs = examples.setup_claude_configurations()
        multi_model_configs = examples.setup_multi_model_configurations()
        
        # 注册配置到管理器
        for config_name, config in claude_configs.items():
            examples.config_manager.register_model_configuration(f"claude_{config_name}", config)
        
        for config_name, config in multi_model_configs.items():
            examples.config_manager.register_model_configuration(config_name, config)
        
        print(f"✅ 已注册 {len(claude_configs) + len(multi_model_configs)} 个模型配置")
        
        # 2. A/B测试示例
        print("\n2️⃣ A/B测试示例")
        test_config = examples.setup_ab_testing_example()
        examples.run_ab_test_simulation("temperature_optimization_001", 30)
        analysis = examples.analyze_ab_test_results("temperature_optimization_001")
        
        # 3. 性能监控示例
        print("\n3️⃣ 性能监控示例")
        examples.setup_performance_monitoring()
        examples.simulate_performance_data("claude-3-haiku", 50)
        summary, recommendations = examples.analyze_performance_data("claude-3-haiku")
        
        # 4. 批量评估示例（如果有API密钥）
        if os.getenv("ANTHROPIC_API_KEY"):
            print("\n4️⃣ 批量评估示例")
            batch_results = await examples.run_batch_evaluation_example()
        else:
            print("\n4️⃣ 跳过批量评估示例（需要ANTHROPIC_API_KEY）")
        
        # 5. 保存配置模板
        print("\n5️⃣ 保存配置模板")
        examples.save_configuration_templates()
        
        print("\n🎉 所有高级配置示例运行完成！")
        
    except Exception as e:
        print(f"\n❌ 运行示例时出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        examples.performance_monitor.stop_monitoring()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())