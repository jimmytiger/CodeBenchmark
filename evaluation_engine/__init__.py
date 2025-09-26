"""
AI Evaluation Engine - Extended lm-evaluation-harness Framework

This package extends the lm-evaluation-harness with advanced evaluation capabilities
including multi-turn conversations, secure code execution, and comprehensive metrics.
"""

__version__ = "0.1.0"
__author__ = "AI Evaluation Engine Team"

from .core.unified_framework import UnifiedEvaluationFramework
from .core.task_registration import ExtendedTaskRegistry

__all__ = [
    "UnifiedEvaluationFramework",
    "ExtendedTaskRegistry",
]