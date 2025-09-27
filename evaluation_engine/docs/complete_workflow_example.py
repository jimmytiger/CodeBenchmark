#!/usr/bin/env python3
"""
AI Evaluation Engine 完整工作流程示例

这个脚本展示了一个完整的AI模型评估工作流程，包括：
1. 环境初始化和配置
2. 模型配置和注册
3. 任务选择和配置
4. 批量评估执行
5. 结果分析和报告生成
6. 性能监控和优化建议
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到Python路径
sys.path.append('.')

# 导入evaluation engine组件
from evaluation_engine.core.unified_framework import (
    UnifiedEvaluationFramework,
    EvaluationRequest,
    EvaluationResult,
    ExecutionStatus
)
from evaluation_engine.core.advanced_model_config import (
    AdvancedModelConfigurationManager,
    ModelConfiguration,
    TaskType,
    OptimizationStrategy,
    RateLimitConfig,
    PerformanceMonitor
)
from evaluation_engine.core.model_adapters import ModelType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompleteWorkflowManager:
    """完整工作流程管理器"""
    
    def __init__(self):
        self.framework = UnifiedEvaluationFramework()
        self.config_manager = AdvancedModelConfigurationManager()
        self.performance_monitor = PerformanceMonitor()
        self.results: Dict[str, EvaluationResult] = {}
        self.workflow_config = {}
        
    def initialize_environment(self) -> bool:
        """初始化评估环境"""
        
        logger.info("🔧 初始化评估环境")
        
        try:
            # 检查必要的环境变量
            required_env_vars = {
                'ANTHROPIC_API_KEY': 'Anthropic Claude API',
                'OPENAI_API_KEY': 'OpenAI GPT API',
                'DEEPSEEK_API_KEY': 'DeepSeek API',
                'DASHSCOPE_API_KEY': '通义千问 API'
            }
            
            available_apis = {}
            for env_var, description in required_env_vars.items():
                if os.getenv(env_var):
                    available_apis[env_var] = description
                    logger.info(f"✅ {description} - 已配置")
                else:
                    logger.warning(f"⚠️  {description} - 未配置")
            
            if not available_apis:
                logger.error("❌ 未找到任何API密钥，无法进行实际评估")
                return False
            
            # 创建必要的目录
            directories = ['results', 'logs', 'cache', 'reports']
            for directory in directories:
                Path(directory).mkdir(exist_ok=True)
                logger.info(f"📁 创建目录: {directory}")
            
            # 启动性能监控
            self.performance_monitor.start_monitoring()
            logger.info("📈 性能监控已启动")
            
            logger.info(f"✅ 环境初始化完成，可用API: {len(available_apis)}个")
            return True
            
        except Exception as e:
            logger.error(f"❌ 环境初始化失败: {e}")
            return False
    
    def setup_model_configurations(self) -> Dict[str, ModelConfiguration]:
        """设置模型配置"""
        
        logger.info("⚙️ 设置模型配置")
        
        configurations = {}
        
        # Claude配置
        if os.getenv('ANTHROPIC_API_KEY'):
            claude_config = ModelConfiguration(
                model_id="claude-3-haiku",
                model_type=ModelType.ANTHROPIC_CLAUDE,
                temperature=0.7,
                max_tokens=2048,
                top_p=0.9,
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                rate_limit_config=RateLimitConfig(
                    requests_per_minute=60,
                    tokens_per_minute=100000,
                    concurrent_requests=3
                ),
                max_cost_per_request=1.0,
                daily_budget=50.0,
                target_response_time=5.0,
                target_success_rate=0.95
            )
            configurations['claude'] = claude_config
            self.config_manager.register_model_configuration('claude', claude_config)
            logger.info("✅ Claude配置已注册")
        
        # OpenAI配置
        if os.getenv('OPENAI_API_KEY'):
            openai_config = ModelConfiguration(
                model_id="gpt-3.5-turbo",
                model_type=ModelType.OPENAI_GPT,
                temperature=0.7,
                max_tokens=2048,
                api_key=os.getenv('OPENAI_API_KEY'),
                rate_limit_config=RateLimitConfig(
                    requests_per_minute=60,
                    tokens_per_minute=90000,
                    concurrent_requests=3
                ),
                max_cost_per_request=0.5,
                daily_budget=30.0
            )
            configurations['openai'] = openai_config
            self.config_manager.register_model_configuration('openai', openai_config)
            logger.info("✅ OpenAI配置已注册")
        
        # DeepSeek配置
        if os.getenv('DEEPSEEK_API_KEY'):
            deepseek_config = ModelConfiguration(
                model_id="deepseek-coder",
                model_type=ModelType.DEEPSEEK,
                temperature=0.7,
                max_tokens=2048,
                api_key=os.getenv('DEEPSEEK_API_KEY'),
                rate_limit_config=RateLimitConfig(
                    requests_per_minute=100,
                    tokens_per_minute=200000,
                    concurrent_requests=5
                ),
                max_cost_per_request=0.1,
                daily_budget=20.0
            )
            configurations['deepseek'] = deepseek_config
            self.config_manager.register_model_configuration('deepseek', deepseek_config)
            logger.info("✅ DeepSeek配置已注册")
        
        # 通义千问配置
        if os.getenv('DASHSCOPE_API_KEY'):
            qwen_config = ModelConfiguration(
                model_id="qwen-plus",
                model_type=ModelType.DASHSCOPE,
                temperature=0.7,
                max_tokens=2048,
                api_key=os.getenv('DASHSCOPE_API_KEY'),
                rate_limit_config=RateLimitConfig(
                    requests_per_minute=60,
                    tokens_per_minute=120000,
                    concurrent_requests=3
                ),
                max_cost_per_request=0.3,
                daily_budget=25.0
            )
            configurations['qwen'] = qwen_config
            self.config_manager.register_model_configuration('qwen', qwen_config)
            logger.info("✅ 通义千问配置已注册")
        
        logger.info(f"✅ 模型配置完成，共注册 {len(configurations)} 个模型")
        return configurations
    
    def define_evaluation_plan(self) -> Dict[str, Any]:
        """定义评估计划"""
        
        logger.info("📋 定义评估计划")
        
        # 基础评估计划
        plan = {
            "experiment_name": "comprehensive_ai_evaluation",
            "description": "全面的AI模型评估实验",
            "timestamp": datetime.now().isoformat(),
            
            # 模型配置
            "models": [],
            
            # 任务组
            "task_groups": [
                {
                    "name": "basic_coding",
                    "description": "基础编程任务",
                    "tasks": [
                        "single_turn_scenarios_function_generation",
                        "single_turn_scenarios_code_completion"
                    ],
                    "priority": 1
                },
                {
                    "name": "advanced_coding", 
                    "description": "高级编程任务",
                    "tasks": [
                        "single_turn_scenarios_bug_fix",
                        "single_turn_scenarios_algorithm_implementation"
                    ],
                    "priority": 2
                },
                {
                    "name": "specialized_tasks",
                    "description": "专业化任务",
                    "tasks": [
                        "single_turn_scenarios_api_design",
                        "single_turn_scenarios_system_design"
                    ],
                    "priority": 3
                }
            ],
            
            # 评估配置
            "evaluation_configs": [
                {
                    "name": "conservative",
                    "description": "保守配置 - 低温度，高确定性",
                    "parameters": {
                        "temperature": 0.3,
                        "max_gen_toks": 1024,
                        "top_p": 0.8
                    }
                },
                {
                    "name": "balanced",
                    "description": "平衡配置 - 中等温度",
                    "parameters": {
                        "temperature": 0.7,
                        "max_gen_toks": 1024,
                        "top_p": 0.9
                    }
                },
                {
                    "name": "creative",
                    "description": "创造性配置 - 高温度，更多随机性",
                    "parameters": {
                        "temperature": 0.9,
                        "max_gen_toks": 1024,
                        "top_p": 0.95
                    }
                }
            ],
            
            # 执行配置
            "execution": {
                "limit": 3,  # 每个任务的样本数量
                "batch_size": 1,
                "timeout": 300,  # 5分钟超时
                "max_concurrent": 3,
                "retry_attempts": 2
            }
        }
        
        # 根据可用的API添加模型
        model_mappings = {
            'ANTHROPIC_API_KEY': {
                "name": "claude",
                "model": "claude-local",
                "model_args": "model=claude-3-haiku-20240307",
                "provider": "anthropic"
            },
            'OPENAI_API_KEY': {
                "name": "openai",
                "model": "openai-completions", 
                "model_args": "model=gpt-3.5-turbo",
                "provider": "openai"
            },
            'DEEPSEEK_API_KEY': {
                "name": "deepseek",
                "model": "deepseek",
                "model_args": "model=deepseek-coder",
                "provider": "deepseek"
            },
            'DASHSCOPE_API_KEY': {
                "name": "qwen",
                "model": "dashscope",
                "model_args": "model=qwen-plus",
                "provider": "dashscope"
            }
        }
        
        for env_var, model_info in model_mappings.items():
            if os.getenv(env_var):
                plan["models"].append(model_info)
        
        self.workflow_config = plan
        logger.info(f"✅ 评估计划已定义: {len(plan['models'])} 个模型, {len(plan['task_groups'])} 个任务组")
        
        return plan
    
    async def execute_evaluation_batch(self, 
                                     model_info: Dict[str, str],
                                     task_group: Dict[str, Any],
                                     config: Dict[str, Any]) -> Optional[EvaluationResult]:
        """执行单个评估批次"""
        
        batch_name = f"{model_info['name']}_{task_group['name']}_{config['name']}"
        logger.info(f"🚀 开始评估批次: {batch_name}")
        
        try:
            # 创建评估请求
            request = EvaluationRequest(
                model=model_info["model"],
                tasks=task_group["tasks"],
                limit=self.workflow_config["execution"]["limit"],
                batch_size=self.workflow_config["execution"]["batch_size"],
                gen_kwargs=config["parameters"],
                output_base_path=f"results/{batch_name}",
                log_samples=True,
                verbosity="INFO",
                predict_only=False,
                random_seed=42
            )
            
            # 如果有model_args，添加到请求中
            if "model_args" in model_info and model_info["model_args"]:
                # 这里需要根据实际的lm_eval接口调整
                pass
            
            # 执行评估
            start_time = datetime.now()
            result = self.framework.evaluate(request)
            end_time = datetime.now()
            
            # 记录性能数据
            execution_time = (end_time - start_time).total_seconds()
            success = result.status == ExecutionStatus.COMPLETED
            
            self.performance_monitor.record_performance(
                model_id=model_info["name"],
                response_time=execution_time,
                success=success,
                cost=0.01,  # 模拟成本
                quality=0.8 if success else 0.0  # 模拟质量分数
            )
            
            # 存储结果
            self.results[batch_name] = result
            
            if success:
                avg_score = sum(result.metrics_summary.values()) / len(result.metrics_summary) if result.metrics_summary else 0
                logger.info(f"✅ {batch_name} 完成 - 平均分数: {avg_score:.3f}, 时间: {execution_time:.1f}s")
            else:
                logger.error(f"❌ {batch_name} 失败: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 {batch_name} 异常: {e}")
            return None
    
    async def run_comprehensive_evaluation(self) -> Dict[str, Any]:
        """运行全面评估"""
        
        logger.info("🎯 开始全面评估")
        
        plan = self.workflow_config
        total_batches = len(plan["models"]) * len(plan["task_groups"]) * len(plan["evaluation_configs"])
        completed_batches = 0
        
        logger.info(f"📊 计划执行 {total_batches} 个评估批次")
        
        # 使用线程池执行评估
        max_workers = min(plan["execution"]["max_concurrent"], total_batches)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有评估任务
            futures = []
            
            for model_info in plan["models"]:
                for task_group in plan["task_groups"]:
                    for config in plan["evaluation_configs"]:
                        future = executor.submit(
                            asyncio.run,
                            self.execute_evaluation_batch(model_info, task_group, config)
                        )
                        futures.append((f"{model_info['name']}_{task_group['name']}_{config['name']}", future))
            
            # 收集结果
            for batch_name, future in futures:
                try:
                    result = future.result(timeout=plan["execution"]["timeout"])
                    completed_batches += 1
                    
                    progress = (completed_batches / total_batches) * 100
                    logger.info(f"📈 进度: {completed_batches}/{total_batches} ({progress:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"❌ 批次 {batch_name} 执行失败: {e}")
        
        logger.info(f"✅ 全面评估完成: {completed_batches}/{total_batches} 个批次成功")
        
        return {
            "total_batches": total_batches,
            "completed_batches": completed_batches,
            "success_rate": completed_batches / total_batches if total_batches > 0 else 0,
            "results": self.results
        }
    
    def generate_comprehensive_report(self, evaluation_summary: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合报告"""
        
        logger.info("📊 生成综合分析报告")
        
        report = {
            "experiment_info": {
                "name": self.workflow_config["experiment_name"],
                "description": self.workflow_config["description"],
                "timestamp": datetime.now().isoformat(),
                "execution_summary": evaluation_summary
            },
            "model_performance": {},
            "task_analysis": {},
            "configuration_analysis": {},
            "performance_insights": {},
            "recommendations": []
        }
        
        # 分析模型性能
        model_scores = {}
        model_times = {}
        
        for batch_name, result in self.results.items():
            if result.status == ExecutionStatus.COMPLETED and result.metrics_summary:
                parts = batch_name.split('_')
                model_name = parts[0]
                task_group = parts[1]
                config_name = parts[2]
                
                # 收集分数数据
                if model_name not in model_scores:
                    model_scores[model_name] = []
                    model_times[model_name] = []
                
                avg_score = sum(result.metrics_summary.values()) / len(result.metrics_summary)
                exec_time = self.framework._calculate_execution_time(result)
                
                model_scores[model_name].append(avg_score)
                model_times[model_name].append(exec_time)
        
        # 计算模型统计
        for model_name in model_scores:
            scores = model_scores[model_name]
            times = model_times[model_name]
            
            if scores:
                report["model_performance"][model_name] = {
                    "average_score": sum(scores) / len(scores),
                    "best_score": max(scores),
                    "worst_score": min(scores),
                    "score_std": self._calculate_std(scores),
                    "average_time": sum(times) / len(times),
                    "total_evaluations": len(scores),
                    "consistency": 1.0 - (max(scores) - min(scores)) if len(scores) > 1 else 1.0
                }
        
        # 分析任务组性能
        task_group_performance = {}
        for batch_name, result in self.results.items():
            if result.status == ExecutionStatus.COMPLETED and result.metrics_summary:
                parts = batch_name.split('_')
                task_group = parts[1]
                
                if task_group not in task_group_performance:
                    task_group_performance[task_group] = []
                
                avg_score = sum(result.metrics_summary.values()) / len(result.metrics_summary)
                task_group_performance[task_group].append(avg_score)
        
        for task_group, scores in task_group_performance.items():
            if scores:
                report["task_analysis"][task_group] = {
                    "average_score": sum(scores) / len(scores),
                    "best_score": max(scores),
                    "difficulty_level": self._assess_difficulty(sum(scores) / len(scores))
                }
        
        # 分析配置性能
        config_performance = {}
        for batch_name, result in self.results.items():
            if result.status == ExecutionStatus.COMPLETED and result.metrics_summary:
                parts = batch_name.split('_')
                config_name = parts[2]
                
                if config_name not in config_performance:
                    config_performance[config_name] = []
                
                avg_score = sum(result.metrics_summary.values()) / len(result.metrics_summary)
                config_performance[config_name].append(avg_score)
        
        for config_name, scores in config_performance.items():
            if scores:
                report["configuration_analysis"][config_name] = {
                    "average_score": sum(scores) / len(scores),
                    "effectiveness": "high" if sum(scores) / len(scores) > 0.8 else "medium" if sum(scores) / len(scores) > 0.6 else "low"
                }
        
        # 生成性能洞察
        if model_scores:
            best_model = max(model_scores.keys(), key=lambda m: sum(model_scores[m]) / len(model_scores[m]))
            fastest_model = min(model_times.keys(), key=lambda m: sum(model_times[m]) / len(model_times[m]))
            
            report["performance_insights"] = {
                "best_overall_model": best_model,
                "fastest_model": fastest_model,
                "most_consistent_model": max(model_scores.keys(), 
                                           key=lambda m: report["model_performance"][m]["consistency"]),
                "total_models_tested": len(model_scores),
                "total_successful_evaluations": sum(len(scores) for scores in model_scores.values())
            }
        
        # 生成建议
        recommendations = []
        
        if model_scores:
            best_model = report["performance_insights"]["best_overall_model"]
            recommendations.append(f"推荐使用 {best_model} 模型，整体性能最佳")
            
            # 检查一致性
            for model_name, perf in report["model_performance"].items():
                if perf["consistency"] < 0.7:
                    recommendations.append(f"{model_name} 模型性能不够稳定，建议调优参数")
        
        if config_performance:
            best_config = max(config_performance.keys(), 
                            key=lambda c: sum(config_performance[c]) / len(config_performance[c]))
            recommendations.append(f"推荐使用 {best_config} 配置，平均性能最佳")
        
        if task_group_performance:
            difficult_tasks = [task for task, perf in report["task_analysis"].items() 
                             if perf["difficulty_level"] == "hard"]
            if difficult_tasks:
                recommendations.append(f"以下任务组较为困难，可能需要特殊优化: {', '.join(difficult_tasks)}")
        
        report["recommendations"] = recommendations
        
        logger.info("✅ 综合报告生成完成")
        return report
    
    def _calculate_std(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _assess_difficulty(self, avg_score: float) -> str:
        """评估任务难度"""
        if avg_score >= 0.8:
            return "easy"
        elif avg_score >= 0.6:
            return "medium"
        else:
            return "hard"
    
    def save_results_and_report(self, report: Dict[str, Any]):
        """保存结果和报告"""
        
        logger.info("💾 保存结果和报告")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存综合报告
        report_file = f"reports/comprehensive_report_{timestamp}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📄 综合报告已保存: {report_file}")
        
        # 保存详细结果
        detailed_results = {}
        for batch_name, result in self.results.items():
            detailed_results[batch_name] = {
                "evaluation_id": result.evaluation_id,
                "status": result.status.value,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "execution_time": self.framework._calculate_execution_time(result),
                "metrics_summary": result.metrics_summary,
                "analysis": result.analysis,
                "error": result.error
            }
        
        results_file = f"reports/detailed_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📊 详细结果已保存: {results_file}")
        
        # 生成简化的Markdown报告
        self._generate_markdown_report(report, f"reports/summary_report_{timestamp}.md")
        
        return report_file, results_file
    
    def _generate_markdown_report(self, report: Dict[str, Any], filename: str):
        """生成Markdown格式的报告"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# {report['experiment_info']['name']}\n\n")
            f.write(f"**描述**: {report['experiment_info']['description']}\n\n")
            f.write(f"**生成时间**: {report['experiment_info']['timestamp']}\n\n")
            
            # 执行摘要
            exec_summary = report['experiment_info']['execution_summary']
            f.write("## 执行摘要\n\n")
            f.write(f"- 总批次数: {exec_summary['total_batches']}\n")
            f.write(f"- 完成批次数: {exec_summary['completed_batches']}\n")
            f.write(f"- 成功率: {exec_summary['success_rate']:.1%}\n\n")
            
            # 模型性能
            if report['model_performance']:
                f.write("## 模型性能排名\n\n")
                sorted_models = sorted(report['model_performance'].items(),
                                     key=lambda x: x[1]['average_score'], reverse=True)
                
                for i, (model_name, perf) in enumerate(sorted_models, 1):
                    f.write(f"### {i}. {model_name}\n")
                    f.write(f"- 平均分数: {perf['average_score']:.3f}\n")
                    f.write(f"- 最佳分数: {perf['best_score']:.3f}\n")
                    f.write(f"- 平均执行时间: {perf['average_time']:.1f}s\n")
                    f.write(f"- 一致性: {perf['consistency']:.3f}\n")
                    f.write(f"- 总评估数: {perf['total_evaluations']}\n\n")
            
            # 任务分析
            if report['task_analysis']:
                f.write("## 任务组分析\n\n")
                for task_group, analysis in report['task_analysis'].items():
                    f.write(f"### {task_group}\n")
                    f.write(f"- 平均分数: {analysis['average_score']:.3f}\n")
                    f.write(f"- 最佳分数: {analysis['best_score']:.3f}\n")
                    f.write(f"- 难度等级: {analysis['difficulty_level']}\n\n")
            
            # 建议
            if report['recommendations']:
                f.write("## 建议\n\n")
                for rec in report['recommendations']:
                    f.write(f"- {rec}\n")
                f.write("\n")
        
        logger.info(f"📝 Markdown报告已保存: {filename}")
    
    def display_summary(self, report: Dict[str, Any]):
        """显示评估摘要"""
        
        print("\n" + "="*80)
        print("🎉 AI Evaluation Engine 完整工作流程执行完成")
        print("="*80)
        
        # 基本信息
        print(f"\n📋 实验信息:")
        print(f"   名称: {report['experiment_info']['name']}")
        print(f"   描述: {report['experiment_info']['description']}")
        
        # 执行摘要
        exec_summary = report['experiment_info']['execution_summary']
        print(f"\n📊 执行摘要:")
        print(f"   总批次数: {exec_summary['total_batches']}")
        print(f"   完成批次数: {exec_summary['completed_batches']}")
        print(f"   成功率: {exec_summary['success_rate']:.1%}")
        
        # 模型性能排名
        if report['model_performance']:
            print(f"\n🏆 模型性能排名:")
            sorted_models = sorted(report['model_performance'].items(),
                                 key=lambda x: x[1]['average_score'], reverse=True)
            
            for i, (model_name, perf) in enumerate(sorted_models, 1):
                print(f"   {i}. {model_name}: {perf['average_score']:.3f} "
                      f"(时间: {perf['average_time']:.1f}s, 一致性: {perf['consistency']:.3f})")
        
        # 性能洞察
        if report['performance_insights']:
            insights = report['performance_insights']
            print(f"\n💡 性能洞察:")
            print(f"   最佳整体模型: {insights['best_overall_model']}")
            print(f"   最快模型: {insights['fastest_model']}")
            print(f"   最一致模型: {insights['most_consistent_model']}")
            print(f"   测试模型总数: {insights['total_models_tested']}")
            print(f"   成功评估总数: {insights['total_successful_evaluations']}")
        
        # 建议
        if report['recommendations']:
            print(f"\n🔧 建议:")
            for rec in report['recommendations']:
                print(f"   • {rec}")
        
        print(f"\n📁 详细报告和结果文件已保存到 reports/ 目录")
        print("="*80)
    
    def cleanup(self):
        """清理资源"""
        
        logger.info("🧹 清理资源")
        
        try:
            self.performance_monitor.stop_monitoring()
            logger.info("✅ 性能监控已停止")
        except Exception as e:
            logger.error(f"❌ 清理资源时出错: {e}")


async def main():
    """主函数"""
    
    print("🚀 AI Evaluation Engine 完整工作流程")
    print("="*80)
    
    workflow_manager = CompleteWorkflowManager()
    
    try:
        # 1. 初始化环境
        if not workflow_manager.initialize_environment():
            print("❌ 环境初始化失败，退出程序")
            return
        
        # 2. 设置模型配置
        configurations = workflow_manager.setup_model_configurations()
        if not configurations:
            print("❌ 未找到可用的模型配置，退出程序")
            return
        
        # 3. 定义评估计划
        plan = workflow_manager.define_evaluation_plan()
        
        # 4. 运行全面评估
        evaluation_summary = await workflow_manager.run_comprehensive_evaluation()
        
        # 5. 生成综合报告
        report = workflow_manager.generate_comprehensive_report(evaluation_summary)
        
        # 6. 保存结果和报告
        report_file, results_file = workflow_manager.save_results_and_report(report)
        
        # 7. 显示摘要
        workflow_manager.display_summary(report)
        
        print(f"\n✅ 工作流程执行完成！")
        print(f"📄 主要报告: {report_file}")
        print(f"📊 详细结果: {results_file}")
        
    except KeyboardInterrupt:
        print("\n⏹️  用户中断执行")
    except Exception as e:
        logger.error(f"❌ 工作流程执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        workflow_manager.cleanup()


if __name__ == "__main__":
    # 运行完整工作流程
    asyncio.run(main())