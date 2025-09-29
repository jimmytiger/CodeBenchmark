"""
Core components for the Multi-Turn Evaluation Engine.

This module contains the fundamental interfaces and base classes that form
the foundation of the evaluation system.
"""

from .task_types import BaseTask, SingleTurnTask, MultiTurnTask, TaskType
from .environment import UnifiedEnv, Observation, Action, Reward
from .exceptions import EvaluationError, TaskExecutionError, SafetyViolationError
from .data_models import (
    TerminationReason,
    ContextStrategy,
    ProcessedFeedback,
    EvaluationResult,
    AggregatedMetrics,
    StandardizedOutput,
    FeedbackConfig,
    SafetyConfig,
    MultiTurnConfig,
    TurnResult,
    DataValidator
)
from .scenario_environments import (
    RepositoryBugFixEnv,
    InteractiveDebuggingEnv,
    RequirementClarificationEnv,
    DataScienceScriptEnv,
    CommandLineEnv,
    CrossLanguageFixEnv,
    RepositoryState,
    DebuggingState,
    RequirementState
)

__all__ = [
    # Task Types
    "BaseTask",
    "SingleTurnTask",
    "MultiTurnTask", 
    "TaskType",
    
    # Environment Interface
    "UnifiedEnv",
    "Observation",
    "Action",
    "Reward",
    
    # Exceptions
    "EvaluationError",
    "TaskExecutionError",
    "SafetyViolationError",
    
    # Data Models
    "TerminationReason",
    "ContextStrategy",
    "ProcessedFeedback",
    "EvaluationResult",
    "AggregatedMetrics",
    "StandardizedOutput",
    "FeedbackConfig",
    "SafetyConfig",
    "MultiTurnConfig",
    "TurnResult",
    "DataValidator",
    
    # Scenario Environments
    "RepositoryBugFixEnv",
    "InteractiveDebuggingEnv",
    "RequirementClarificationEnv",
    "DataScienceScriptEnv",
    "CommandLineEnv",
    "CrossLanguageFixEnv",
    "RepositoryState",
    "DebuggingState",
    "RequirementState"
]