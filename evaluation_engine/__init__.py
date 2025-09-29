"""
AI Evaluation Engine - Extended lm-evaluation-harness Framework

This package extends the lm-evaluation-harness with advanced evaluation capabilities
including multi-turn conversations, secure code execution, comprehensive metrics,
and configuration-driven evaluation.
"""

__version__ = "0.1.0"
__author__ = "AI Evaluation Engine Team"

from .core.unified_framework import UnifiedEvaluationFramework
from .core.task_registration import ExtendedTaskRegistry

# Configuration-driven evaluation components
from .config import (
    EvaluationConfig,
    TaskConfig,
    ModelConfig,
    ConfigParser,
    ConfigFormatDetector,
    ConfigDrivenEvaluator
)

__all__ = [
    "UnifiedEvaluationFramework",
    "ExtendedTaskRegistry",
    "EvaluationConfig",
    "TaskConfig", 
    "ModelConfig",
    "ConfigParser",
    "ConfigFormatDetector",
    "ConfigDrivenEvaluator"
]