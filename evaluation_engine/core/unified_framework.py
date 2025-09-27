"""
Unified Evaluation Framework for AI Evaluation Engine

This module provides a comprehensive framework that integrates all evaluation components
while maintaining full compatibility with lm-evaluation-harness.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import time
from pathlib import Path
from datetime import datetime

from lm_eval.evaluator import simple_evaluate
from lm_eval.tasks import get_task_dict
from lm_eval.api.model import LM

logger = logging.getLogger(__name__)


class EvaluationMode(Enum):
    """Evaluation mode enumeration"""
    SINGLE_TURN = "single_turn"
    MULTI_TURN = "multi_turn"
    AGENTIC = "agentic"
    MULTI_AGENT = "multi_agent"


class BusinessScenario(Enum):
    """Business scenario enumeration"""
    CODE_COMPLETION = "code_completion"
    CODE_REPAIR = "code_repair"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTORING = "refactoring"
    ALGORITHM_IMPLEMENTATION = "algorithm_implementation"
    API_DESIGN = "api_design"
    SYSTEM_DESIGN = "system_design"
    DATABASE_DESIGN = "database_design"
    SECURITY_IMPLEMENTATION = "security_implementation"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    FULL_STACK_DEVELOPMENT = "full_stack_development"


class ExecutionStatus(Enum):
    """Execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class EvaluationConfig:
    """Unified evaluation configuration"""
    task_name: str
    scenario: BusinessScenario
    mode: EvaluationMode
    model_config: Dict[str, Any]
    dataset_config: Dict[str, Any]
    metrics_config: Dict[str, Any]
    execution_config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationRequest:
    """Evaluation request with lm-eval integration"""
    model: Union[str, LM]
    tasks: List[str]
    limit: Optional[int] = None
    num_fewshot: Optional[int] = None
    batch_size: Optional[int] = None
    device: Optional[str] = None
    use_cache: bool = True
    cache_requests: bool = False
    rewrite_requests_cache: bool = False
    delete_requests_cache: bool = False
    description: Optional[str] = None
    write_out: bool = False
    output_base_path: Optional[str] = None
    verbosity: str = "INFO"
    log_samples: bool = False
    show_config: bool = False
    include_path: Optional[str] = None
    gen_kwargs: Optional[Dict[str, Any]] = None
    task_manager: Optional[Any] = None
    predict_only: bool = False
    random_seed: int = 0
    numpy_random_seed: int = 1234
    torch_random_seed: int = 1234
    fewshot_random_seed: int = 1234


@dataclass
class EvaluationResult:
    """Comprehensive evaluation result"""
    evaluation_id: str
    request: EvaluationRequest
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None
    samples: Optional[List[Dict[str, Any]]] = None
    config: Optional[Dict[str, Any]] = None
    versions: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metrics_summary: Optional[Dict[str, float]] = None
    analysis: Optional[Dict[str, Any]] = None


class UnifiedEvaluationFramework:
    """Unified evaluation framework main class with lm-eval integration"""
    
    def __init__(self):
        self.task_registry = {}
        self.model_registry = {}
        self.metrics_registry = {}
        self.scenario_handlers = {}
        self.active_evaluations: Dict[str, EvaluationResult] = {}
        
        # Import task registry
        from .task_registration import extended_registry
        self.extended_registry = extended_registry
        
    def register_scenario_handler(self, scenario: BusinessScenario, handler: Callable):
        """Register scenario handler"""
        self.scenario_handlers[scenario] = handler
        logger.info(f"Registered handler for scenario: {scenario.value}")
        
    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """Unified evaluation entry point with lm-eval integration"""
        evaluation_id = self._generate_evaluation_id()
        start_time = datetime.now()
        
        # Create evaluation result object
        result = EvaluationResult(
            evaluation_id=evaluation_id,
            request=request,
            status=ExecutionStatus.PENDING,
            start_time=start_time
        )
        
        self.active_evaluations[evaluation_id] = result
        
        try:
            logger.info(f"Starting evaluation {evaluation_id} for tasks: {request.tasks}")
            result.status = ExecutionStatus.RUNNING
            
            # Validate tasks exist by attempting to load them
            try:
                task_dict = get_task_dict(request.tasks)
                available_tasks = set(task_dict.keys())
            except Exception as e:
                raise ValueError(f"Error loading tasks {request.tasks}: {e}")
            
            # Execute evaluation using lm-eval (filter out unsupported parameters)
            eval_params = {
                "model": request.model,
                "tasks": request.tasks,
                "limit": request.limit,
                "num_fewshot": request.num_fewshot,
                "batch_size": request.batch_size,
                "device": request.device,
                "use_cache": request.use_cache,
                "cache_requests": request.cache_requests,
                "rewrite_requests_cache": request.rewrite_requests_cache,
                "delete_requests_cache": request.delete_requests_cache,
                "write_out": request.write_out,
                # "output_base_path": request.output_base_path,  # 这个参数在某些版本中不支持
                "verbosity": request.verbosity,
                "log_samples": request.log_samples,
                # "show_config": request.show_config,  # 这个参数在某些版本中不支持
                "include_path": request.include_path,
                "gen_kwargs": request.gen_kwargs,
                "task_manager": request.task_manager,
                "predict_only": request.predict_only,
                "random_seed": request.random_seed,
                "numpy_random_seed": request.numpy_random_seed,
                "torch_random_seed": request.torch_random_seed,
                "fewshot_random_seed": request.fewshot_random_seed
            }
            
            # Filter out None values
            eval_params = {k: v for k, v in eval_params.items() if v is not None}
            
            lm_eval_results = simple_evaluate(**eval_params)
            
            # Process and enhance results
            result.results = lm_eval_results.get("results", {})
            result.samples = lm_eval_results.get("samples", [])
            result.config = lm_eval_results.get("config", {})
            result.versions = lm_eval_results.get("versions", {})
            
            # Generate metrics summary
            result.metrics_summary = self._extract_metrics_summary(result.results)
            
            # Generate analysis
            result.analysis = self._generate_comprehensive_analysis(result)
            
            result.status = ExecutionStatus.COMPLETED
            result.end_time = datetime.now()
            
            logger.info(f"Evaluation {evaluation_id} completed successfully")
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            result.end_time = datetime.now()
            logger.error(f"Evaluation {evaluation_id} failed: {e}")
            
        return result
    
    def evaluate_with_config(self, config: EvaluationConfig) -> Dict[str, Any]:
        """Legacy evaluation method for backward compatibility"""
        logger.info(f"Starting evaluation for {config.task_name}")
        
        # Convert to EvaluationRequest
        request = EvaluationRequest(
            model=config.model_config.get("model", "dummy"),
            tasks=[config.task_name],
            **config.execution_config
        )
        
        result = self.evaluate(request)
        
        return {
            "task_name": config.task_name,
            "scenario": config.scenario.value,
            "mode": config.mode.value,
            "raw_results": result.results,
            "analysis": result.analysis,
            "metadata": config.metadata,
            "status": result.status.value,
            "execution_time": self._calculate_execution_time(result)
        }
    
    def get_evaluation_status(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """Get status of a running evaluation"""
        return self.active_evaluations.get(evaluation_id)
    
    def cancel_evaluation(self, evaluation_id: str) -> bool:
        """Cancel a running evaluation"""
        if evaluation_id in self.active_evaluations:
            result = self.active_evaluations[evaluation_id]
            if result.status == ExecutionStatus.RUNNING:
                result.status = ExecutionStatus.CANCELLED
                result.end_time = datetime.now()
                logger.info(f"Evaluation {evaluation_id} cancelled")
                return True
        return False
    
    def list_available_tasks(self, category: Optional[str] = None) -> List[str]:
        """List available tasks, optionally filtered by category"""
        if category:
            return self.extended_registry.discover_tasks({"category": category})
        else:
            # Get all available tasks from task manager
            from lm_eval.tasks import TaskManager
            task_manager = TaskManager()
            return task_manager.all_tasks
    
    def get_task_info(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a task"""
        metadata = self.extended_registry.get_task_metadata(task_name)
        scenario_config = self.extended_registry.get_scenario_config(task_name)
        
        try:
            # 检查任务是否可用
            task_dict = get_task_dict([task_name])
            available = task_name in task_dict
        except:
            available = False
        
        info = {
            "task_name": task_name,
            "available": available,
            "metadata": metadata.__dict__ if metadata else None,
            "scenario_config": scenario_config.__dict__ if scenario_config else None,
            "is_multi_turn": scenario_config is not None
        }
        
        return info
    
    def validate_evaluation_request(self, request: EvaluationRequest) -> List[str]:
        """Validate evaluation request and return list of issues"""
        issues = []
        
        # Check if tasks exist by attempting to load them
        try:
            task_dict = get_task_dict(request.tasks)
        except Exception as e:
            issues.append(f"Error loading tasks {request.tasks}: {e}")
        
        # Check task dependencies
        for task_name in request.tasks:
            if not self.extended_registry.validate_task_dependencies(task_name):
                issues.append(f"Task {task_name} has unmet dependencies")
        
        # Validate model configuration
        if isinstance(request.model, str) and not request.model:
            issues.append("Model name cannot be empty")
        
        # Validate limits
        if request.limit is not None and request.limit <= 0:
            issues.append("Limit must be positive")
        
        if request.batch_size is not None and request.batch_size <= 0:
            issues.append("Batch size must be positive")
        
        return issues
    
    def _generate_evaluation_id(self) -> str:
        """Generate unique evaluation ID"""
        import uuid
        return f"eval_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    
    def _extract_metrics_summary(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Extract key metrics from evaluation results"""
        summary = {}
        
        for task_name, task_results in results.items():
            if isinstance(task_results, dict):
                for metric_name, metric_value in task_results.items():
                    if isinstance(metric_value, (int, float)):
                        summary[f"{task_name}_{metric_name}"] = float(metric_value)
        
        return summary
    
    def _generate_comprehensive_analysis(self, result: EvaluationResult) -> Dict[str, Any]:
        """Generate comprehensive analysis of evaluation results"""
        analysis = {
            "summary": self._generate_summary(result),
            "key_metrics": result.metrics_summary or {},
            "task_analysis": self._analyze_individual_tasks(result.results or {}),
            "recommendations": self._generate_recommendations(result),
            "performance_insights": self._generate_performance_insights(result),
            "execution_metadata": {
                "execution_time": self._calculate_execution_time(result),
                "tasks_evaluated": len(result.request.tasks),
                "model_used": str(result.request.model),
                "evaluation_id": result.evaluation_id
            }
        }
        
        return analysis
    
    def _generate_summary(self, result: EvaluationResult) -> str:
        """Generate evaluation summary"""
        if result.status == ExecutionStatus.COMPLETED:
            return f"Evaluation completed successfully for {len(result.request.tasks)} tasks"
        elif result.status == ExecutionStatus.FAILED:
            return f"Evaluation failed: {result.error}"
        else:
            return f"Evaluation status: {result.status.value}"
    
    def _analyze_individual_tasks(self, results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Analyze results for individual tasks"""
        task_analysis = {}
        
        for task_name, task_results in results.items():
            if isinstance(task_results, dict):
                task_analysis[task_name] = {
                    "metrics": {k: v for k, v in task_results.items() if isinstance(v, (int, float))},
                    "performance_level": self._assess_performance_level(task_results),
                    "strengths": self._identify_strengths(task_results),
                    "areas_for_improvement": self._identify_improvements(task_results)
                }
        
        return task_analysis
    
    def _assess_performance_level(self, task_results: Dict[str, Any]) -> str:
        """Assess performance level for a task"""
        # Simple heuristic - can be enhanced with domain-specific logic
        numeric_metrics = [v for v in task_results.values() if isinstance(v, (int, float))]
        if not numeric_metrics:
            return "unknown"
        
        avg_score = sum(numeric_metrics) / len(numeric_metrics)
        if avg_score >= 0.8:
            return "excellent"
        elif avg_score >= 0.6:
            return "good"
        elif avg_score >= 0.4:
            return "fair"
        else:
            return "needs_improvement"
    
    def _identify_strengths(self, task_results: Dict[str, Any]) -> List[str]:
        """Identify strengths based on task results"""
        strengths = []
        
        for metric, value in task_results.items():
            if isinstance(value, (int, float)) and value >= 0.7:
                strengths.append(f"Strong performance in {metric}")
        
        return strengths
    
    def _identify_improvements(self, task_results: Dict[str, Any]) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        
        for metric, value in task_results.items():
            if isinstance(value, (int, float)) and value < 0.5:
                improvements.append(f"Improvement needed in {metric}")
        
        return improvements
    
    def _generate_recommendations(self, result: EvaluationResult) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if result.status == ExecutionStatus.COMPLETED and result.metrics_summary:
            avg_performance = sum(result.metrics_summary.values()) / len(result.metrics_summary)
            
            if avg_performance < 0.5:
                recommendations.append("Consider fine-tuning the model on domain-specific data")
                recommendations.append("Review prompt engineering strategies")
            elif avg_performance < 0.7:
                recommendations.append("Experiment with different few-shot examples")
                recommendations.append("Consider adjusting model parameters")
            else:
                recommendations.append("Performance is good - consider testing on more challenging scenarios")
        
        return recommendations
    
    def _generate_performance_insights(self, result: EvaluationResult) -> Dict[str, Any]:
        """Generate performance insights"""
        insights = {
            "overall_performance": "unknown",
            "best_performing_tasks": [],
            "worst_performing_tasks": [],
            "consistency_score": 0.0
        }
        
        if result.metrics_summary:
            # Calculate overall performance
            avg_performance = sum(result.metrics_summary.values()) / len(result.metrics_summary)
            insights["overall_performance"] = self._performance_level_from_score(avg_performance)
            
            # Find best and worst performing tasks
            sorted_tasks = sorted(result.metrics_summary.items(), key=lambda x: x[1], reverse=True)
            insights["best_performing_tasks"] = [task for task, score in sorted_tasks[:3]]
            insights["worst_performing_tasks"] = [task for task, score in sorted_tasks[-3:]]
            
            # Calculate consistency (inverse of standard deviation)
            if len(result.metrics_summary) > 1:
                import statistics
                std_dev = statistics.stdev(result.metrics_summary.values())
                insights["consistency_score"] = max(0, 1 - std_dev)
        
        return insights
    
    def _performance_level_from_score(self, score: float) -> str:
        """Convert numeric score to performance level"""
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        else:
            return "needs_improvement"
    
    def _calculate_execution_time(self, result: EvaluationResult) -> float:
        """Calculate execution time in seconds"""
        if result.end_time and result.start_time:
            return (result.end_time - result.start_time).total_seconds()
        return 0.0
    
    def export_results(self, evaluation_id: str, output_path: str) -> bool:
        """Export evaluation results to file"""
        result = self.active_evaluations.get(evaluation_id)
        if not result:
            return False
        
        try:
            export_data = {
                "evaluation_id": result.evaluation_id,
                "status": result.status.value,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "execution_time": self._calculate_execution_time(result),
                "request": {
                    "model": str(result.request.model),
                    "tasks": result.request.tasks,
                    "limit": result.request.limit,
                    "num_fewshot": result.request.num_fewshot
                },
                "results": result.results,
                "metrics_summary": result.metrics_summary,
                "analysis": result.analysis,
                "error": result.error
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Results exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export results: {e}")
            return False


# Global framework instance
unified_framework = UnifiedEvaluationFramework()