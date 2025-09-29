"""
EvaluationEngineV1_0 Comprehensive Testing Framework

This package provides comprehensive testing capabilities for EvaluationEngineV1_0,
including CLI testing, API testing, adapter validation, and real execution verification.
"""

__version__ = "1.0.0"
__author__ = "EvaluationEngine Testing Team"

from .core.test_orchestrator import TestOrchestrator
from .core.real_execution_validator import RealExecutionValidator
from .core.metrics_collector import MetricsCollector
from .models.test_models import TestResult, TestConfiguration, ValidationResult

__all__ = [
    "TestOrchestrator",
    "RealExecutionValidator", 
    "MetricsCollector",
    "TestResult",
    "TestConfiguration",
    "ValidationResult"
]