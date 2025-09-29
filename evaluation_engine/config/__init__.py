"""
Configuration module for evaluation_engine.

This module provides configuration-driven evaluation capabilities,
allowing users to define evaluation tasks through configuration files
instead of manual API calls.
"""

from .models import (
    EvaluationConfig,
    TaskConfig,
    ModelConfig,
    ConfigMetadata,
    DefaultConfig,
    OutputConfig,
    ValidationResult,
    ValidationError
)

from .parser import ConfigParser
from .detector import ConfigFormatDetector
from .validator import ConfigValidator
from .templates import (
    ModelTemplateManager,
    ModelTemplate,
    TemplateVariable,
    ModelType,
    TemplateVariableType,
    TemplateValidationResult
)

from .builder import (
    TaskBuilder,
    EvaluationTask,
    ExecutionPlan,
    DependencyStatus
)

from .evaluator import (
    ConfigDrivenEvaluator,
    BatchExecutionResult,
    ConfigDrivenEvaluationResult
)

__all__ = [
    'EvaluationConfig',
    'TaskConfig', 
    'ModelConfig',
    'ConfigMetadata',
    'DefaultConfig',
    'OutputConfig',
    'ValidationResult',
    'ValidationError',
    'ConfigParser',
    'ConfigFormatDetector',
    'ConfigValidator',
    'ModelTemplateManager',
    'ModelTemplate',
    'TemplateVariable',
    'ModelType',
    'TemplateVariableType',
    'TemplateValidationResult',
    'TaskBuilder',
    'EvaluationTask',
    'ExecutionPlan',
    'DependencyStatus',
    'ConfigDrivenEvaluator',
    'BatchExecutionResult',
    'ConfigDrivenEvaluationResult'
]