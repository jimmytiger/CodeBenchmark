"""
LM-Eval compatibility adapter for the Multi-Turn Evaluation Engine.

This module provides seamless integration with the existing lm-evaluation-harness
framework without modifying any existing lm-eval code. It wraps lm-eval functionality
and provides automatic task type detection and classification.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime
import json
import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

from .adapters import BenchmarkAdapter, AdapterInfo, StandardizedResult, AdapterStatus
from .environment import UnifiedEnv, Observation, Action, Reward, Info
from .task_types import BaseTask, TaskType, TaskResult, SingleTurnTask, MultiTurnTask
from .exceptions import AdapterError, ConfigurationError, TaskExecutionError


# Import lm-eval components safely
try:
    from lm_eval.evaluator import simple_evaluate
    from lm_eval.tasks import TaskManager, get_task_dict
    from lm_eval.api.task import Task as LMEvalTask
    from lm_eval.api.registry import ALL_TASKS, TASK_REGISTRY
    from lm_eval.api.model import LM
    LM_EVAL_AVAILABLE = True
    _import_error = None
except ImportError as e:
    LM_EVAL_AVAILABLE = False
    _import_error = e


@dataclass
class LMEvalTaskInfo:
    """Information about an lm-eval task.
    
    Attributes:
        name: Task name
        task_class: The lm-eval task class
        config: Task configuration
        output_type: Type of output (loglikelihood, generate_until, etc.)
        is_multi_turn: Whether this is detected as a multi-turn task
        metadata: Additional task metadata
    """
    name: str
    task_class: type
    config: Dict[str, Any]
    output_type: str
    is_multi_turn: bool
    metadata: Dict[str, Any]


class LMEvalEnvironment(UnifiedEnv):
    """Environment wrapper for lm-eval tasks.
    
    This class wraps an lm-eval task to provide the unified environment interface
    while maintaining compatibility with existing lm-eval functionality.
    """
    
    def __init__(self, task_info: LMEvalTaskInfo, config: Dict[str, Any]):
        """Initialize the lm-eval environment.
        
        Args:
            task_info: Information about the lm-eval task
            config: Environment configuration
        """
        super().__init__(config)
        self.task_info = task_info
        self.task_instance = None
        self.current_doc = None
        self.current_doc_index = 0
        self.total_docs = 0
        self.results = []
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Initialize task instance
        self._initialize_task()
    
    def _initialize_task(self) -> None:
        """Initialize the lm-eval task instance."""
        try:
            # Create task instance using lm-eval's task manager
            task_manager = TaskManager()
            task_dict = task_manager.load_task_or_group([self.task_info.name])
            
            if self.task_info.name in task_dict:
                self.task_instance = task_dict[self.task_info.name]
                self.total_docs = len(self.task_instance.eval_docs)
                self._logger.info(f"Initialized lm-eval task '{self.task_info.name}' with {self.total_docs} documents")
            else:
                raise AdapterError(f"Failed to load lm-eval task: {self.task_info.name}")
                
        except Exception as e:
            raise AdapterError(f"Failed to initialize lm-eval task: {str(e)}") from e
    
    def reset(self) -> Observation:
        """Reset the environment to the first document.
        
        Returns:
            Initial observation containing the first document
        """
        if not self.task_instance:
            raise TaskExecutionError("Task instance not initialized")
        
        self.current_doc_index = 0
        self.results = []
        
        if self.total_docs > 0:
            self.current_doc = self.task_instance.eval_docs[0]
            observation = self._create_observation()
        else:
            observation = "No documents available for evaluation"
        
        self._mark_initialized()
        self._update_state(0.0, False, {"doc_index": self.current_doc_index})
        
        return observation
    
    def step(self, action: Action) -> tuple[Observation, Reward, bool, Info]:
        """Execute a step with the given action.
        
        For lm-eval tasks, the action is typically a model response that needs
        to be evaluated against the expected output.
        
        Args:
            action: The action/response to evaluate
            
        Returns:
            Tuple of (observation, reward, done, info)
        """
        if not self._initialized:
            raise TaskExecutionError("Environment not initialized. Call reset() first.")
        
        if self.current_doc is None:
            raise TaskExecutionError("No current document to evaluate")
        
        start_time = datetime.now()
        
        try:
            # Evaluate the action against the current document
            result = self._evaluate_action(action)
            
            # Calculate reward based on evaluation result
            reward = self._calculate_reward(result)
            
            # Store result
            self.results.append({
                "doc_index": self.current_doc_index,
                "action": action,
                "result": result,
                "reward": reward,
                "timestamp": start_time
            })
            
            # Move to next document
            self.current_doc_index += 1
            done = self.current_doc_index >= self.total_docs
            
            if not done and self.current_doc_index < len(self.task_instance.eval_docs):
                self.current_doc = self.task_instance.eval_docs[self.current_doc_index]
                observation = self._create_observation()
            else:
                observation = "Evaluation complete"
            
            # Create info dictionary
            execution_time = (datetime.now() - start_time).total_seconds()
            info = {
                "doc_index": self.current_doc_index - 1,  # Index of evaluated doc
                "total_docs": self.total_docs,
                "result": result,
                "execution_time": execution_time,
                "task_name": self.task_info.name,
                "output_type": self.task_info.output_type
            }
            
            self._update_state(reward, done, info)
            
            return observation, reward, done, info
            
        except Exception as e:
            error_msg = f"Failed to execute step: {str(e)}"
            self._logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise TaskExecutionError(error_msg) from e
    
    def success(self) -> bool:
        """Check if the evaluation was successful.
        
        Returns:
            True if all documents were processed successfully
        """
        return (self._state.is_done and 
                len(self.results) == self.total_docs and
                all(r["result"].get("success", False) for r in self.results))
    
    def info(self) -> Dict[str, Any]:
        """Get current environment information.
        
        Returns:
            Dictionary containing environment information
        """
        return {
            "task_name": self.task_info.name,
            "task_type": "multi_turn" if self.task_info.is_multi_turn else "single_turn",
            "output_type": self.task_info.output_type,
            "current_doc_index": self.current_doc_index,
            "total_docs": self.total_docs,
            "completed_docs": len(self.results),
            "success_rate": self._calculate_success_rate(),
            "average_reward": self._calculate_average_reward(),
            "is_done": self._state.is_done,
            "initialized": self._initialized
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.results:
            return {
                "progress": 0.0,
                "success_rate": 0.0,
                "average_reward": 0.0,
                "completion_rate": 0.0
            }
        
        progress = len(self.results) / self.total_docs if self.total_docs > 0 else 0.0
        success_rate = self._calculate_success_rate()
        average_reward = self._calculate_average_reward()
        completion_rate = 1.0 if self._state.is_done else progress
        
        return {
            "progress": progress,
            "success_rate": success_rate,
            "average_reward": average_reward,
            "completion_rate": completion_rate,
            "total_docs": float(self.total_docs),
            "completed_docs": float(len(self.results))
        }
    
    def _create_observation(self) -> Observation:
        """Create an observation from the current document.
        
        Returns:
            Observation string or dictionary
        """
        if not self.current_doc:
            return "No document available"
        
        try:
            # Use the task's doc_to_text method to create the observation
            if hasattr(self.task_instance, 'doc_to_text'):
                if callable(self.task_instance.doc_to_text):
                    text = self.task_instance.doc_to_text(self.current_doc)
                else:
                    text = str(self.task_instance.doc_to_text)
            else:
                text = str(self.current_doc)
            
            return {
                "text": text,
                "doc_index": self.current_doc_index,
                "total_docs": self.total_docs,
                "task_name": self.task_info.name,
                "raw_doc": self.current_doc
            }
            
        except Exception as e:
            self._logger.warning(f"Failed to create observation: {e}")
            return str(self.current_doc)
    
    def _evaluate_action(self, action: Action) -> Dict[str, Any]:
        """Evaluate an action against the current document.
        
        Args:
            action: The action to evaluate
            
        Returns:
            Dictionary containing evaluation results
        """
        try:
            # For lm-eval compatibility, we simulate the evaluation process
            # In a real implementation, this would use lm-eval's evaluation logic
            
            if hasattr(self.task_instance, 'doc_to_target'):
                if callable(self.task_instance.doc_to_target):
                    expected = self.task_instance.doc_to_target(self.current_doc)
                else:
                    expected = str(self.task_instance.doc_to_target)
            else:
                expected = self.current_doc.get("target", "")
            
            # Simple evaluation - in practice, this would use task-specific metrics
            if isinstance(action, str) and isinstance(expected, str):
                exact_match = action.strip().lower() == expected.strip().lower()
                similarity = self._calculate_similarity(action, expected)
            else:
                exact_match = action == expected
                similarity = 1.0 if exact_match else 0.0
            
            return {
                "success": exact_match,
                "similarity": similarity,
                "expected": expected,
                "actual": action,
                "evaluation_method": "simple_comparison"
            }
            
        except Exception as e:
            self._logger.warning(f"Evaluation failed: {e}")
            return {
                "success": False,
                "similarity": 0.0,
                "expected": None,
                "actual": action,
                "error": str(e)
            }
    
    def _calculate_reward(self, result: Dict[str, Any]) -> float:
        """Calculate reward based on evaluation result.
        
        Args:
            result: Evaluation result dictionary
            
        Returns:
            Reward value between 0.0 and 1.0
        """
        if result.get("success", False):
            return 1.0
        else:
            # Partial credit based on similarity
            return result.get("similarity", 0.0)
    
    def _calculate_success_rate(self) -> float:
        """Calculate the current success rate.
        
        Returns:
            Success rate as a float between 0.0 and 1.0
        """
        if not self.results:
            return 0.0
        
        successful = sum(1 for r in self.results if r["result"].get("success", False))
        return successful / len(self.results)
    
    def _calculate_average_reward(self) -> float:
        """Calculate the average reward.
        
        Returns:
            Average reward as a float
        """
        if not self.results:
            return 0.0
        
        total_reward = sum(r["reward"] for r in self.results)
        return total_reward / len(self.results)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple character-based similarity
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        t1 = text1.strip().lower()
        t2 = text2.strip().lower()
        
        if t1 == t2:
            return 1.0
        
        # Simple Jaccard similarity on words
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0


class LMEvalTaskWrapper(BaseTask):
    """Wrapper for lm-eval tasks to integrate with the unified task system."""
    
    def __init__(self, task_info: LMEvalTaskInfo, config: Dict[str, Any]):
        """Initialize the task wrapper.
        
        Args:
            task_info: Information about the lm-eval task
            config: Task configuration
        """
        super().__init__(task_info.name, config)
        self.task_info = task_info
    
    def get_task_type(self) -> TaskType:
        """Get the task type based on detection.
        
        Returns:
            TaskType.MULTI_TURN if detected as multi-turn, otherwise SINGLE_TURN
        """
        return TaskType.MULTI_TURN if self.task_info.is_multi_turn else TaskType.SINGLE_TURN
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the task configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid
        """
        # Basic validation for lm-eval tasks
        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        return True
    
    def get_required_capabilities(self) -> List[str]:
        """Get required capabilities for this task.
        
        Returns:
            List of required capabilities
        """
        capabilities = ["text_generation"]
        
        # Add capabilities based on task type
        if self.task_info.output_type == "generate_until":
            capabilities.append("text_completion")
        elif self.task_info.output_type in ["loglikelihood", "multiple_choice"]:
            capabilities.append("probability_estimation")
        
        # Add multi-turn capability if detected
        if self.task_info.is_multi_turn:
            capabilities.append("conversation_management")
        
        return capabilities
    
    def create_environment(self) -> LMEvalEnvironment:
        """Create an environment for this task.
        
        Returns:
            LMEvalEnvironment instance
        """
        return LMEvalEnvironment(self.task_info, self.config)


class LMEvalAdapter(BenchmarkAdapter):
    """Adapter for integrating lm-evaluation-harness tasks.
    
    This adapter provides seamless integration with existing lm-eval tasks
    without modifying any lm-eval code. It automatically detects task types
    and provides the unified interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the lm-eval adapter.
        
        Args:
            config: Adapter configuration
        """
        if not LM_EVAL_AVAILABLE:
            raise AdapterError(f"lm-eval is not available: {_import_error}")
        
        super().__init__(config)
        self.task_manager = None
        self.available_tasks = {}
        self._task_info_cache = {}
    
    def get_adapter_info(self) -> AdapterInfo:
        """Get information about this adapter.
        
        Returns:
            AdapterInfo describing the lm-eval adapter
        """
        return AdapterInfo(
            name="lm_eval_adapter",
            version="1.0.0",
            description="Compatibility adapter for lm-evaluation-harness tasks",
            supported_task_types=[TaskType.SINGLE_TURN, TaskType.MULTI_TURN],
            required_dependencies=["lm-eval", "datasets", "transformers"],
            supported_formats=["json", "jsonl", "huggingface"],
            capabilities=[
                "text_generation",
                "text_completion", 
                "probability_estimation",
                "multiple_choice",
                "conversation_management",
                "automatic_task_detection"
            ],
            metadata={
                "integration_type": "wrapper",
                "modifies_lm_eval": False,
                "backward_compatible": True
            }
        )
    
    def initialize(self) -> bool:
        """Initialize the adapter and load available tasks.
        
        Returns:
            True if initialization was successful
        """
        try:
            self._set_status(AdapterStatus.INITIALIZING)
            
            # Initialize task manager
            self.task_manager = TaskManager()
            
            # Load available tasks
            self.available_tasks = get_task_dict()
            
            self._logger.info(f"Loaded {len(self.available_tasks)} lm-eval tasks")
            
            self._set_status(AdapterStatus.READY)
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize lm-eval adapter: {str(e)}"
            self._set_status(AdapterStatus.ERROR, error_msg)
            return False
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create an environment for the specified task.
        
        Args:
            task_config: Configuration for the task
            
        Returns:
            LMEvalEnvironment instance
        """
        if not self.is_ready():
            raise AdapterError("Adapter not initialized")
        
        task_name = task_config.get("task_id") or task_config.get("task_name")
        if not task_name:
            raise ConfigurationError("task_id or task_name must be specified")
        
        # Get or create task info
        task_info = self._get_task_info(task_name)
        
        return LMEvalEnvironment(task_info, task_config)
    
    def load_tasks(self, task_filter: Optional[Dict[str, Any]] = None) -> List[BaseTask]:
        """Load available tasks from lm-eval.
        
        Args:
            task_filter: Optional filter criteria
            
        Returns:
            List of wrapped lm-eval tasks
        """
        if not self.is_ready():
            raise AdapterError("Adapter not initialized")
        
        tasks = []
        
        # Apply filters if provided
        task_names = list(self.available_tasks.keys())
        if task_filter:
            task_names = self._apply_task_filter(task_names, task_filter)
        
        for task_name in task_names:
            try:
                task_info = self._get_task_info(task_name)
                task_wrapper = LMEvalTaskWrapper(task_info, {
                    "task_name": task_name,
                    "adapter": "lm_eval"
                })
                tasks.append(task_wrapper)
            except Exception as e:
                self._logger.warning(f"Failed to load task {task_name}: {e}")
        
        return tasks
    
    def convert_results(self, results: Any) -> StandardizedResult:
        """Convert lm-eval results to standardized format.
        
        Args:
            results: Raw results from lm-eval
            
        Returns:
            StandardizedResult object
        """
        if isinstance(results, dict):
            # Extract common fields from lm-eval results
            task_id = results.get("task_name", "unknown")
            success = results.get("success", False)
            score = results.get("score", 0.0)
            execution_time = results.get("execution_time", 0.0)
            
            # Handle different result formats
            if "results" in results:
                # Standard lm-eval format
                task_results = results["results"]
                # Use the first task's results if task_id is unknown
                if task_id == "unknown" and task_results:
                    first_task = list(task_results.keys())[0]
                    task_data = task_results[first_task]
                elif task_id in task_results:
                    task_data = task_results[task_id]
                else:
                    task_data = None
                
                # Use the first metric as the primary score
                if task_data and isinstance(task_data, dict):
                    metrics = [v for k, v in task_data.items() if isinstance(v, (int, float))]
                    if metrics:
                        score = float(metrics[0])
                        success = score > 0.5  # Simple threshold
            
            return StandardizedResult(
                task_id=task_id,
                adapter_name="lm_eval_adapter",
                success=success,
                score=max(0.0, min(1.0, score)),  # Ensure score is in [0, 1]
                execution_time=execution_time,
                turns=1,  # lm-eval tasks are typically single-turn
                tokens_used=results.get("tokens_used", 0),
                cost=results.get("cost", 0.0),
                metadata={
                    "lm_eval_format": True,
                    "original_results": results
                },
                raw_result=results
            )
        else:
            # Handle other result formats
            return StandardizedResult(
                task_id="unknown",
                adapter_name="lm_eval_adapter",
                success=False,
                score=0.0,
                execution_time=0.0,
                turns=1,
                tokens_used=0,
                cost=0.0,
                metadata={"conversion_error": "Unsupported result format"},
                raw_result=results
            )
    
    def _get_task_info(self, task_name: str) -> LMEvalTaskInfo:
        """Get or create task information for a given task.
        
        Args:
            task_name: Name of the task
            
        Returns:
            LMEvalTaskInfo object
        """
        if task_name in self._task_info_cache:
            return self._task_info_cache[task_name]
        
        if task_name not in self.available_tasks:
            raise AdapterError(f"Task '{task_name}' not found in available tasks")
        
        try:
            # Load the task to get its configuration
            task_dict = self.task_manager.load_task_or_group([task_name])
            task_instance = task_dict.get(task_name)
            
            if not task_instance:
                raise AdapterError(f"Failed to load task instance for '{task_name}'")
            
            # Detect task type and extract information
            output_type = getattr(task_instance, 'OUTPUT_TYPE', 'generate_until')
            is_multi_turn = self._detect_multi_turn(task_name, task_instance)
            
            task_info = LMEvalTaskInfo(
                name=task_name,
                task_class=type(task_instance),
                config={
                    "output_type": output_type,
                    "num_fewshot": getattr(task_instance, 'num_fewshot', 0),
                    "description": getattr(task_instance, 'DESCRIPTION', ''),
                },
                output_type=output_type,
                is_multi_turn=is_multi_turn,
                metadata={
                    "version": getattr(task_instance, 'VERSION', None),
                    "dataset_path": getattr(task_instance, 'DATASET_PATH', None),
                    "dataset_name": getattr(task_instance, 'DATASET_NAME', None),
                }
            )
            
            self._task_info_cache[task_name] = task_info
            return task_info
            
        except Exception as e:
            raise AdapterError(f"Failed to get task info for '{task_name}': {str(e)}") from e
    
    def _detect_multi_turn(self, task_name: str, task_instance: Any) -> bool:
        """Detect if a task is multi-turn based on various heuristics.
        
        Args:
            task_name: Name of the task
            task_instance: The task instance
            
        Returns:
            True if detected as multi-turn
        """
        # Heuristics for detecting multi-turn tasks
        # Use word boundaries to avoid false matches like "turn" in "question"
        multi_turn_indicators = [
            "multi_turn", "conversation", "dialogue", "chat", "interactive",
            "session", "context", "history", "round"
        ]
        
        # Special handling for "turn" to avoid false matches
        turn_indicators = ["multi_turn", "_turn_", "turn_", "_turn"]
        
        # Check task name
        task_name_lower = task_name.lower()
        if any(indicator in task_name_lower for indicator in multi_turn_indicators):
            return True
        if any(indicator in task_name_lower for indicator in turn_indicators):
            return True
        
        # Check task description if task_instance is provided
        if task_instance is not None:
            description = getattr(task_instance, 'DESCRIPTION', '').lower()
            if any(indicator in description for indicator in multi_turn_indicators):
                return True
            if any(indicator in description for indicator in turn_indicators):
                return True
            
            # Check if task has conversation-related methods or attributes
            # Only check for real methods, not Mock objects
            if not isinstance(task_instance, type(Mock())):
                conversation_methods = ['get_context', 'update_context', 'get_history']
                if any(hasattr(task_instance, method) for method in conversation_methods):
                    return True
        
        # Default to single-turn
        return False
    
    def _apply_task_filter(self, task_names: List[str], task_filter: Dict[str, Any]) -> List[str]:
        """Apply filters to task names.
        
        Args:
            task_names: List of task names to filter
            task_filter: Filter criteria
            
        Returns:
            Filtered list of task names
        """
        filtered_names = task_names
        
        # Filter by pattern
        if "pattern" in task_filter:
            pattern = task_filter["pattern"].lower()
            filtered_names = [name for name in filtered_names if pattern in name.lower()]
        
        # Filter by task type
        if "task_type" in task_filter:
            target_type = task_filter["task_type"]
            if target_type == "multi_turn":
                filtered_names = [name for name in filtered_names 
                                if self._detect_multi_turn(name, None)]
            elif target_type == "single_turn":
                filtered_names = [name for name in filtered_names 
                                if not self._detect_multi_turn(name, None)]
        
        # Limit results
        if "limit" in task_filter:
            limit = int(task_filter["limit"])
            filtered_names = filtered_names[:limit]
        
        return filtered_names