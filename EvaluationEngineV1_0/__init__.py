"""
Multi-Turn Evaluation Engine V1.0

A comprehensive evaluation orchestration layer that supports unified single-turn 
and multi-turn evaluation capabilities while maintaining compatibility with 
existing lm-evaluation-harness framework.
"""

__version__ = "1.0.0"
__author__ = "Evaluation Engine Team"

from .core.task_types import BaseTask, SingleTurnTask, MultiTurnTask, TaskType
from .core.environment import UnifiedEnv, Observation, Action, Reward
from .core.exceptions import EvaluationError, TaskExecutionError, SafetyViolationError

__all__ = [
    "BaseTask",
    "SingleTurnTask", 
    "MultiTurnTask",
    "TaskType",
    "UnifiedEnv",
    "Observation",
    "Action", 
    "Reward",
    "EvaluationError",
    "TaskExecutionError",
    "SafetyViolationError"
]