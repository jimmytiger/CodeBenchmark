"""
Data models for the testing framework.
"""

from .test_models import (
    TestConfiguration,
    TestResult,
    ValidationResult,
    ExecutionMetrics,
    CLITestConfig,
    APITestConfig,
    AdapterTestConfig,
    TestSuiteResults
)

__all__ = [
    "TestConfiguration",
    "TestResult", 
    "ValidationResult",
    "ExecutionMetrics",
    "CLITestConfig",
    "APITestConfig",
    "AdapterTestConfig",
    "TestSuiteResults"
]