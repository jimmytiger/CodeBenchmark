#!/usr/bin/env python3
"""
EvaluationEngineV1.0 自定义任务集成模块

本模块实现了使用 EvaluationEngineV1.0 框架调用自定义 lm-eval 任务的完整流程，
包括单轮和多轮场景的统一接口。
"""

import json
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

from .core.task_types import BaseTask, SingleTurnTask, MultiTurnTask, TaskResult, TurnResult
from .core.environment import UnifiedEnv, EnvironmentState, StepResult
from .core.exceptions import EvaluationError, TaskExecutionError, ConfigurationError


class TaskType(Enum):
    """任务类型枚举"""
    SINGLE_TURN = "single_turn"
    MULTI_TURN = "multi_turn"
    CUSTOM = "custom"


@dataclass
class CustomTaskConfig:
    """自定义任务配置"""
    task_name: str
    model: str
    model_args: Dict[str, Any]
    num_fewshot: int = 0
    batch_size: int = 1
    limit: Optional[int] = None
    apply_chat_template: bool = False
    metadata: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None
    verbosity: str = "INFO"


@dataclass
class EvaluationResult:
    """评估结果数据模型"""
    task_id: str
    task_type: TaskType
    status: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_path: Optional[str] = None


class CustomSingleTurnTask(SingleTurnTask):
    """自定义单轮任务实现"""
    
    def __init__(self, task_id: str, config: CustomTaskConfig):
        super().__init__(task_id, asdict(config))
        self.config = config
        self.task_type = TaskType.SINGLE_TURN
    
    def execute(self, input_data: Any = None) -> TaskResult:
        """执行单轮任务"""
        start_time = datetime.now()
        
        try:
            # 构建 lm_eval 命令
            cmd = self._build_lm_eval_command()
            
            # 执行评估
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                # 解析结果
                results = self._parse_results()
                
                return TaskResult(
                    task_id=self.task_id,
                    success=True,
                    score=self._extract_score(results),
                    execution_time=execution_time,
                    metadata={
                        "results": results,
                        "config": asdict(self.config),
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                )
            else:
                raise TaskExecutionError(
                    f"lm_eval execution failed: {result.stderr}",
                    error_type="execution_failure",
                    context={"returncode": result.returncode, "stderr": result.stderr}
                )
                
        except subprocess.TimeoutExpired:
            raise TaskExecutionError(
                "Task execution timeout",
                error_type="timeout",
                context={"timeout": 3600}
            )
        except Exception as e:
            raise TaskExecutionError(
                f"Task execution error: {str(e)}",
                error_type="unknown_error",
                context={"exception": str(e)}
            )
    
    def _build_lm_eval_command(self) -> List[str]:
        """构建 lm_eval 命令"""
        cmd = [
            "lm_eval",
            "--model", self.config.model,
            "--model_args", self._format_model_args(),
            "--tasks", self.config.task_name,
            "--num_fewshot", str(self.config.num_fewshot),
            "--batch_size", str(self.config.batch_size),
            "--verbosity", self.config.verbosity
        ]
        
        if self.config.limit:
            cmd.extend(["--limit", str(self.config.limit)])
        
        if self.config.output_path:
            cmd.extend(["--output_path", self.config.output_path])
        
        if self.config.apply_chat_template:
            cmd.append("--apply_chat_template")
        
        return cmd
    
    def _format_model_args(self) -> str:
        """格式化模型参数"""
        if isinstance(self.config.model_args, dict):
            return ",".join([f"{k}={v}" for k, v in self.config.model_args.items()])
        return str(self.config.model_args)
    
    def _parse_results(self) -> Dict[str, Any]:
        """解析评估结果"""
        if not self.config.output_path:
            return {}
        
        # 查找结果文件
        output_dir = Path(self.config.output_path)
        result_files = list(output_dir.glob("**/results_*.json"))
        
        if not result_files:
            return {}
        
        # 读取最新的结果文件
        result_file = max(result_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(result_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _extract_score(self, results: Dict[str, Any]) -> float:
        """提取评估分数"""
        if not results or 'results' not in results:
            return 0.0
        
        # 尝试提取第一个任务的第一个指标
        task_results = results['results']
        for task_name, metrics in task_results.items():
            if isinstance(metrics, dict):
                for metric_name, value in metrics.items():
                    if isinstance(value, (int, float)) and not metric_name.endswith('_stderr'):
                        return float(value)
        
        return 0.0
    
    def get_required_capabilities(self) -> List[str]:
        """获取所需能力"""
        return ["lm_eval", "subprocess", "file_system"]


class CustomMultiTurnTask(MultiTurnTask):
    """自定义多轮任务实现"""
    
    def __init__(self, task_id: str, config: CustomTaskConfig):
        super().__init__(task_id, asdict(config))
        self.config = config
        self.task_type = TaskType.MULTI_TURN
        self.turn_results = []
    
    def execute_turn(self, turn_data: Any) -> TurnResult:
        """执行单轮交互"""
        start_time = datetime.now()
        
        try:
            # 为当前轮次创建输出路径
            turn_output_path = None
            if self.config.output_path:
                turn_output_path = f"{self.config.output_path}/turn_{turn_data.turn_number}"
                Path(turn_output_path).mkdir(parents=True, exist_ok=True)
            
            # 更新配置用于当前轮次
            turn_config = CustomTaskConfig(
                task_name=self.config.task_name,
                model=self.config.model,
                model_args=self.config.model_args,
                num_fewshot=self.config.num_fewshot,
                batch_size=self.config.batch_size,
                limit=self.config.limit,
                apply_chat_template=self.config.apply_chat_template,
                output_path=turn_output_path,
                verbosity=self.config.verbosity
            )
            
            # 创建临时单轮任务执行
            single_task = CustomSingleTurnTask(f"{self.task_id}_turn_{turn_data.turn_number}", turn_config)
            task_result = single_task.execute(turn_data.input_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            turn_result = TurnResult(
                turn=turn_data.turn_number,
                action=f"executed_{self.config.task_name}",
                observation=task_result.metadata.get("results", {}),
                reward=task_result.score,
                done=turn_data.turn_number >= 3,  # 默认3轮完成
                info={
                    "task_success": task_result.success,
                    "execution_time": execution_time,
                    "config": asdict(turn_config)
                },
                execution_time=execution_time
            )
            
            self.turn_results.append(turn_result)
            return turn_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            turn_result = TurnResult(
                turn=turn_data.turn_number,
                action=f"failed_{self.config.task_name}",
                observation={"error": str(e)},
                reward=0.0,
                done=True,  # 错误时结束
                info={"error": str(e)},
                execution_time=execution_time
            )
            
            self.turn_results.append(turn_result)
            return turn_result
    
    def should_continue(self, turn_result: TurnResult) -> bool:
        """判断是否继续下一轮"""
        return not turn_result.done and turn_result.turn < 5  # 最多5轮
    
    def get_initial_context(self) -> str:
        """获取初始上下文"""
        return f"Starting multi-turn evaluation for task: {self.config.task_name}"
    
    def is_successful(self, turn_results: List[TurnResult]) -> bool:
        """判断整体任务是否成功"""
        if not turn_results:
            return False
        
        # 如果最后一轮成功完成，且没有错误
        last_turn = turn_results[-1]
        return last_turn.done and "error" not in last_turn.info


class CustomTaskEnvironment(UnifiedEnv):
    """自定义任务环境"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.current_task: Optional[BaseTask] = None
        self.evaluation_results: List[EvaluationResult] = []
        self.state = EnvironmentState(
            step_count=0,
            is_done=False,
            current_observation="Environment initialized",
            metadata={"config": config}
        )
    
    def reset(self) -> Any:
        """重置环境"""
        self.state = EnvironmentState(
            step_count=0,
            is_done=False,
            current_observation="Environment reset",
            metadata=self.state.metadata
        )
        self.current_task = None
        return self.state.current_observation
    
    def step(self, action: Any) -> StepResult:
        """执行一步操作"""
        self.state.step_count += 1
        
        try:
            if isinstance(action, dict) and "task_config" in action:
                # 创建并执行任务
                task_config = CustomTaskConfig(**action["task_config"])
                result = self._execute_task(task_config)
                
                observation = {
                    "task_id": result.task_id,
                    "status": result.status,
                    "results": result.results
                }
                
                reward = 1.0 if result.status == "completed" else 0.0
                done = True  # 单次任务执行后完成
                
                info = {
                    "execution_time": result.execution_time,
                    "task_type": result.task_type.value,
                    "output_path": result.output_path
                }
                
                self.state.current_observation = observation
                self.state.is_done = done
                
                return StepResult(
                    observation=observation,
                    reward=reward,
                    done=done,
                    info=info
                )
            else:
                # 无效操作
                return StepResult(
                    observation={"error": "Invalid action format"},
                    reward=0.0,
                    done=True,
                    info={"error": "Action must contain task_config"}
                )
                
        except Exception as e:
            return StepResult(
                observation={"error": str(e)},
                reward=0.0,
                done=True,
                info={"exception": str(e)}
            )
    
    def _execute_task(self, config: CustomTaskConfig) -> EvaluationResult:
        """执行任务"""
        task_id = str(uuid.uuid4())[:8]
        
        # 判断任务类型
        if "multi_turn" in config.task_name:
            task = CustomMultiTurnTask(task_id, config)
            task_type = TaskType.MULTI_TURN
        else:
            task = CustomSingleTurnTask(task_id, config)
            task_type = TaskType.SINGLE_TURN
        
        self.current_task = task
        
        result = EvaluationResult(
            task_id=task_id,
            task_type=task_type,
            status="running",
            created_at=datetime.now()
        )
        
        try:
            result.started_at = datetime.now()
            
            if isinstance(task, SingleTurnTask):
                task_result = task.execute()
                result.results = task_result.metadata.get("results", {})
                result.execution_time = task_result.execution_time
                result.status = "completed" if task_result.success else "failed"
                
            elif isinstance(task, MultiTurnTask):
                # 执行多轮任务
                from .core.task_types import TurnData
                
                turn_results = []
                for turn_num in range(1, 4):  # 执行3轮
                    turn_data = TurnData(
                        turn_number=turn_num,
                        input_data={"turn": turn_num, "context": task.get_initial_context()}
                    )
                    
                    turn_result = task.execute_turn(turn_data)
                    turn_results.append(turn_result)
                    
                    if not task.should_continue(turn_result):
                        break
                
                result.results = {
                    "turn_results": [asdict(tr) for tr in turn_results],
                    "success": task.is_successful(turn_results),
                    "total_turns": len(turn_results)
                }
                result.execution_time = sum(tr.execution_time for tr in turn_results)
                result.status = "completed" if task.is_successful(turn_results) else "failed"
            
            result.completed_at = datetime.now()
            result.output_path = config.output_path
            
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.completed_at = datetime.now()
        
        self.evaluation_results.append(result)
        return result
    
    def success(self) -> bool:
        """判断环境是否成功"""
        if not self.evaluation_results:
            return False
        
        latest_result = self.evaluation_results[-1]
        return latest_result.status == "completed"
    
    def info(self) -> Dict[str, Any]:
        """获取环境信息"""
        return {
            "total_evaluations": len(self.evaluation_results),
            "successful_evaluations": len([r for r in self.evaluation_results if r.status == "completed"]),
            "current_state": asdict(self.state),
            "latest_result": asdict(self.evaluation_results[-1]) if self.evaluation_results else None
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取环境指标"""
        if not self.evaluation_results:
            return {}
        
        completed_results = [r for r in self.evaluation_results if r.status == "completed"]
        
        return {
            "total_tasks": len(self.evaluation_results),
            "success_rate": len(completed_results) / len(self.evaluation_results),
            "average_execution_time": sum(r.execution_time or 0 for r in completed_results) / len(completed_results) if completed_results else 0,
            "task_types": {
                task_type.value: len([r for r in self.evaluation_results if r.task_type == task_type])
                for task_type in TaskType
            }
        }


class CustomTaskEvaluationEngine:
    """自定义任务评估引擎"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.environment = CustomTaskEnvironment(self.config)
        self.results: List[EvaluationResult] = []
    
    def evaluate_single_turn_task(
        self,
        task_name: str,
        model: str,
        model_args: Union[str, Dict[str, Any]],
        **kwargs
    ) -> EvaluationResult:
        """评估单轮任务"""
        
        # 处理 model_args
        if isinstance(model_args, str):
            # 解析字符串格式的参数
            args_dict = {}
            for pair in model_args.split(','):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    args_dict[key.strip()] = value.strip()
        else:
            args_dict = model_args
        
        config = CustomTaskConfig(
            task_name=task_name,
            model=model,
            model_args=args_dict,
            **kwargs
        )
        
        action = {"task_config": asdict(config)}
        
        self.environment.reset()
        step_result = self.environment.step(action)
        
        # 获取最新的评估结果
        latest_result = self.environment.evaluation_results[-1]
        self.results.append(latest_result)
        
        return latest_result
    
    def evaluate_multi_turn_task(
        self,
        task_name: str,
        model: str,
        model_args: Union[str, Dict[str, Any]],
        **kwargs
    ) -> EvaluationResult:
        """评估多轮任务"""
        
        # 确保启用 chat template
        kwargs.setdefault("apply_chat_template", True)
        
        return self.evaluate_single_turn_task(task_name, model, model_args, **kwargs)
    
    def evaluate_task_suite(
        self,
        task_names: List[str],
        model: str,
        model_args: Union[str, Dict[str, Any]],
        **kwargs
    ) -> List[EvaluationResult]:
        """评估任务套件"""
        
        results = []
        
        for task_name in task_names:
            try:
                if "multi_turn" in task_name:
                    result = self.evaluate_multi_turn_task(task_name, model, model_args, **kwargs)
                else:
                    result = self.evaluate_single_turn_task(task_name, model, model_args, **kwargs)
                
                results.append(result)
                
            except Exception as e:
                # 创建失败结果
                failed_result = EvaluationResult(
                    task_id=str(uuid.uuid4())[:8],
                    task_type=TaskType.CUSTOM,
                    status="failed",
                    error=str(e),
                    created_at=datetime.now(),
                    completed_at=datetime.now()
                )
                results.append(failed_result)
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """获取评估摘要"""
        if not self.results:
            return {"message": "No evaluations completed"}
        
        completed = [r for r in self.results if r.status == "completed"]
        failed = [r for r in self.results if r.status == "failed"]
        
        return {
            "total_evaluations": len(self.results),
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": len(completed) / len(self.results) if self.results else 0,
            "average_execution_time": sum(r.execution_time or 0 for r in completed) / len(completed) if completed else 0,
            "task_types": {
                task_type.value: len([r for r in self.results if r.task_type == task_type])
                for task_type in TaskType
            },
            "environment_metrics": self.environment.get_metrics()
        }


# 便捷函数
def evaluate_custom_task(
    task_name: str,
    model: str = "anthropic-chat",
    model_args: Union[str, Dict[str, Any]] = "model=claude-3-haiku-20240307,max_tokens=1024,temperature=0.0",
    limit: int = 5,
    output_path: Optional[str] = None,
    **kwargs
) -> EvaluationResult:
    """便捷的自定义任务评估函数"""
    
    engine = CustomTaskEvaluationEngine()
    
    if "multi_turn" in task_name:
        return engine.evaluate_multi_turn_task(
            task_name=task_name,
            model=model,
            model_args=model_args,
            limit=limit,
            output_path=output_path,
            **kwargs
        )
    else:
        return engine.evaluate_single_turn_task(
            task_name=task_name,
            model=model,
            model_args=model_args,
            limit=limit,
            output_path=output_path,
            **kwargs
        )


def evaluate_custom_task_suite(
    task_names: List[str],
    model: str = "anthropic-chat",
    model_args: Union[str, Dict[str, Any]] = "model=claude-3-haiku-20240307,max_tokens=1024,temperature=0.0",
    limit: int = 5,
    output_path: Optional[str] = None,
    **kwargs
) -> List[EvaluationResult]:
    """便捷的任务套件评估函数"""
    
    engine = CustomTaskEvaluationEngine()
    
    return engine.evaluate_task_suite(
        task_names=task_names,
        model=model,
        model_args=model_args,
        limit=limit,
        output_path=output_path,
        **kwargs
    )


if __name__ == "__main__":
    # 示例用法
    print("🚀 EvaluationEngineV1.0 自定义任务集成示例")
    
    # 单轮任务评估
    print("\n1. 单轮任务评估示例:")
    result = evaluate_custom_task(
        task_name="single_turn_scenarios_code_completion",
        limit=2,
        output_path="./results/single_turn_test"
    )
    print(f"任务状态: {result.status}")
    print(f"执行时间: {result.execution_time}秒")
    
    # 多轮任务评估
    print("\n2. 多轮任务评估示例:")
    result = evaluate_custom_task(
        task_name="multi_turn_scenarios.code_review_3_turn",
        limit=1,
        output_path="./results/multi_turn_test"
    )
    print(f"任务状态: {result.status}")
    print(f"执行时间: {result.execution_time}秒")
    
    # 任务套件评估
    print("\n3. 任务套件评估示例:")
    results = evaluate_custom_task_suite(
        task_names=[
            "single_turn_scenarios_code_completion",
            "single_turn_scenarios_bug_fix",
            "multi_turn_scenarios.code_review_3_turn"
        ],
        limit=2,
        output_path="./results/suite_test"
    )
    
    print(f"套件评估完成，共 {len(results)} 个任务")
    for i, result in enumerate(results, 1):
        print(f"  任务 {i}: {result.status}")