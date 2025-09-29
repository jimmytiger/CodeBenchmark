"""
Pytest configuration and fixtures for the Multi-Turn Evaluation Engine tests.

This module provides common test fixtures and configuration for the test suite.
"""

import pytest
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_single_turn_config():
    """Fixture providing a valid single-turn task configuration."""
    return {
        "timeout": 30,
        "max_tokens": 1000,
        "temperature": 0.7,
        "model": "test-model"
    }


@pytest.fixture
def sample_multi_turn_config():
    """Fixture providing a valid multi-turn task configuration."""
    return {
        "max_turns": 5,
        "turn_timeout": 30,
        "max_tokens_per_turn": 1000,
        "temperature": 0.7,
        "model": "test-model",
        "enable_context_retention": True
    }


@pytest.fixture
def sample_environment_config():
    """Fixture providing a valid environment configuration."""
    return {
        "max_steps": 10,
        "success_probability": 0.2,
        "reward_range": (0.0, 1.0),
        "timeout": 60
    }