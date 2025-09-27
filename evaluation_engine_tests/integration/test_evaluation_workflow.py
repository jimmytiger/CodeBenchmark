"""
Integration tests for complete evaluation workflows.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
from evaluation_engine.core.task_registration import TaskRegistry
from evaluation_engine.core.model_adapters import ModelAdapter


class TestEvaluationWorkflow:
    """Test complete evaluation workflows."""

    @pytest.fixture
    def evaluation_framework(self, temp_dir):
        """Create evaluation framework for integration testing."""
        config = {
            "data_dir": str(temp_dir),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results"),
            "log_level": "DEBUG"
        }
        return UnifiedEvaluationFramework(config)

    @pytest.fixture
    def sample_dataset(self, temp_dir):
        """Create sample dataset file."""
        dataset = [
            {
                "id": "test_1",
                "input": "Write a function to calculate the factorial of a number",
                "expected_output": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
                "test_cases": [
                    {"input": 5, "expected": 120},
                    {"input": 0, "expected": 1},
                    {"input": 1, "expected": 1}
                ]
            },
            {
                "id": "test_2",
                "input": "Implement a binary search function",
                "expected_output": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
                "test_cases": [
                    {"input": ([1, 2, 3, 4, 5], 3), "expected": 2},
                    {"input": ([1, 2, 3, 4, 5], 6), "expected": -1}
                ]
            }
        ]
        
        dataset_file = temp_dir / "test_dataset.jsonl"
        with open(dataset_file, 'w') as f:
            for item in dataset:
                f.write(json.dumps(item) + '\n')
        
        return str(dataset_file)

    @pytest.fixture
    def mock_model_responses(self):
        """Mock model responses for testing."""
        return {
            "test_1": {
                "response": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
                "usage": {"prompt_tokens": 50, "completion_tokens": 30}
            },
            "test_2": {
                "response": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
                "usage": {"prompt_tokens": 60, "completion_tokens": 45}
            }
        }

    @pytest.mark.asyncio
    async def test_single_turn_evaluation_workflow(self, evaluation_framework, sample_dataset, mock_model_responses):
        """Test complete single-turn evaluation workflow."""
        # Register a mock model adapter
        mock_adapter = Mock(spec=ModelAdapter)
        mock_adapter.model_id = "test_model"
        mock_adapter.generate_response = AsyncMock()
        
        # Configure mock responses
        def mock_generate(prompt, config=None):
            # Extract test ID from prompt (simplified)
            if "factorial" in prompt:
                return mock_model_responses["test_1"]
            else:
                return mock_model_responses["test_2"]
        
        mock_adapter.generate_response.side_effect = mock_generate
        evaluation_framework.register_model_adapter(mock_adapter)
        
        # Register a test task
        task_config = {
            "task_id": "integration_test_task",
            "task_type": "single_turn",
            "description": "Integration test task",
            "dataset_path": sample_dataset,
            "metrics": ["accuracy", "bleu", "code_quality"],
            "context_mode": "full_context"
        }
        
        task_id = evaluation_framework.register_task(task_config)
        
        # Run evaluation
        result = await evaluation_framework.run_evaluation(
            task_ids=[task_id],
            model_id="test_model"
        )
        
        # Verify results
        assert result is not None
        assert "evaluation_id" in result
        assert "results" in result
        assert len(result["results"]) == 1
        
        task_result = result["results"][0]
        assert task_result["task_id"] == task_id
        assert "metrics" in task_result
        assert "execution_time" in task_result
        assert "outputs" in task_result

    @pytest.mark.asyncio
    async def test_multi_turn_evaluation_workflow(self, evaluation_framework, temp_dir):
        """Test multi-turn evaluation workflow."""
        # Create multi-turn dataset
        multi_turn_dataset = [
            {
                "conversation_id": "conv_1",
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
                        "content": "The code is functional but could benefit from type hints and documentation.",
                        "expected_response_type": "improvement_suggestion"
                    },
                    {
                        "turn_id": 3,
                        "role": "user",
                        "content": "Please implement the improvements you suggested",
                        "expected_response_type": "improved_code"
                    }
                ]
            }
        ]
        
        dataset_file = temp_dir / "multi_turn_dataset.jsonl"
        with open(dataset_file, 'w') as f:
            for item in multi_turn_dataset:
                f.write(json.dumps(item) + '\n')
        
        # Register mock model adapter
        mock_adapter = Mock(spec=ModelAdapter)
        mock_adapter.model_id = "test_model"
        mock_adapter.generate_response = AsyncMock()
        
        # Mock multi-turn responses
        turn_responses = [
            {"response": "The code looks good but could use type hints and documentation.", "usage": {"prompt_tokens": 30, "completion_tokens": 15}},
            {"response": "def add(a: int, b: int) -> int:\n    \"\"\"Add two integers and return the result.\"\"\"\n    return a + b", "usage": {"prompt_tokens": 40, "completion_tokens": 25}}
        ]
        
        mock_adapter.generate_response.side_effect = turn_responses
        evaluation_framework.register_model_adapter(mock_adapter)
        
        # Register multi-turn task
        task_config = {
            "task_id": "multi_turn_test_task",
            "task_type": "multi_turn",
            "description": "Multi-turn integration test",
            "dataset_path": str(dataset_file),
            "metrics": ["coherence", "context_retention", "goal_achievement"],
            "max_turns": 3,
            "conversation_timeout": 300
        }
        
        task_id = evaluation_framework.register_task(task_config)
        
        # Run evaluation
        result = await evaluation_framework.run_evaluation(
            task_ids=[task_id],
            model_id="test_model"
        )
        
        # Verify results
        assert result is not None
        assert len(result["results"]) == 1
        
        task_result = result["results"][0]
        assert task_result["task_id"] == task_id
        assert "metrics" in task_result
        assert "conversation_results" in task_result

    @pytest.mark.asyncio
    async def test_model_adapter_integration(self, evaluation_framework, sample_dataset):
        """Test integration with different model adapters."""
        # Register multiple model adapters
        adapters = []
        for i in range(3):
            adapter = Mock(spec=ModelAdapter)
            adapter.model_id = f"test_model_{i}"
            adapter.generate_response = AsyncMock(return_value={
                "response": f"Response from model {i}",
                "usage": {"prompt_tokens": 10 + i, "completion_tokens": 20 + i}
            })
            adapters.append(adapter)
            evaluation_framework.register_model_adapter(adapter)
        
        # Register task
        task_config = {
            "task_id": "multi_model_test",
            "task_type": "single_turn",
            "description": "Multi-model test",
            "dataset_path": sample_dataset,
            "metrics": ["accuracy"]
        }
        
        task_id = evaluation_framework.register_task(task_config)
        
        # Run evaluation with different models
        results = []
        for adapter in adapters:
            result = await evaluation_framework.run_evaluation(
                task_ids=[task_id],
                model_id=adapter.model_id
            )
            results.append(result)
        
        # Verify all models were evaluated
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["model_id"] == f"test_model_{i}"

    @pytest.mark.asyncio
    async def test_metrics_calculation_integration(self, evaluation_framework, sample_dataset):
        """Test integration of metrics calculation."""
        # Register model adapter with specific responses
        mock_adapter = Mock(spec=ModelAdapter)
        mock_adapter.model_id = "metrics_test_model"
        mock_adapter.generate_response = AsyncMock()
        
        # Responses that will generate different metric scores
        responses = [
            {"response": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)", "usage": {"prompt_tokens": 50, "completion_tokens": 30}},
            {"response": "def binary_search(arr, target):\n    for i, val in enumerate(arr):\n        if val == target:\n            return i\n    return -1", "usage": {"prompt_tokens": 60, "completion_tokens": 25}}
        ]
        
        mock_adapter.generate_response.side_effect = responses
        evaluation_framework.register_model_adapter(mock_adapter)
        
        # Register task with multiple metrics
        task_config = {
            "task_id": "metrics_integration_test",
            "task_type": "single_turn",
            "description": "Metrics integration test",
            "dataset_path": sample_dataset,
            "metrics": ["accuracy", "bleu", "rouge", "code_quality", "security_score"],
            "enable_code_execution": True
        }
        
        task_id = evaluation_framework.register_task(task_config)
        
        # Run evaluation
        result = await evaluation_framework.run_evaluation(
            task_ids=[task_id],
            model_id="metrics_test_model"
        )
        
        # Verify metrics were calculated
        task_result = result["results"][0]
        metrics = task_result["metrics"]
        
        expected_metrics = ["accuracy", "bleu", "rouge", "code_quality", "security_score"]
        for metric in expected_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))

    @pytest.mark.asyncio
    async def test_sandbox_execution_integration(self, evaluation_framework, temp_dir):
        """Test integration with sandbox execution."""
        # Create dataset with executable code
        code_dataset = [
            {
                "id": "exec_test_1",
                "input": "Write a function to calculate fibonacci numbers",
                "expected_output": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                "test_cases": [
                    {"input": 5, "expected": 5},
                    {"input": 0, "expected": 0},
                    {"input": 1, "expected": 1}
                ],
                "language": "python"
            }
        ]
        
        dataset_file = temp_dir / "code_dataset.jsonl"
        with open(dataset_file, 'w') as f:
            for item in code_dataset:
                f.write(json.dumps(item) + '\n')
        
        # Mock sandbox executor
        with patch('evaluation_engine.core.sandbox_executor.SandboxExecutor') as mock_executor:
            mock_instance = Mock()
            mock_instance.execute_code.return_value = {
                "success": True,
                "output": "5",
                "execution_time": 0.1,
                "memory_usage": 1024,
                "test_results": [
                    {"passed": True, "output": 5, "expected": 5},
                    {"passed": True, "output": 0, "expected": 0},
                    {"passed": True, "output": 1, "expected": 1}
                ]
            }
            mock_executor.return_value = mock_instance
            
            # Register model adapter
            mock_adapter = Mock(spec=ModelAdapter)
            mock_adapter.model_id = "sandbox_test_model"
            mock_adapter.generate_response = AsyncMock(return_value={
                "response": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                "usage": {"prompt_tokens": 40, "completion_tokens": 35}
            })
            evaluation_framework.register_model_adapter(mock_adapter)
            
            # Register task with sandbox execution
            task_config = {
                "task_id": "sandbox_integration_test",
                "task_type": "single_turn",
                "description": "Sandbox integration test",
                "dataset_path": str(dataset_file),
                "metrics": ["accuracy", "pass_at_k", "execution_success"],
                "enable_sandbox": True,
                "sandbox_timeout": 30
            }
            
            task_id = evaluation_framework.register_task(task_config)
            
            # Run evaluation
            result = await evaluation_framework.run_evaluation(
                task_ids=[task_id],
                model_id="sandbox_test_model"
            )
            
            # Verify sandbox execution was used
            mock_instance.execute_code.assert_called()
            
            # Verify execution metrics
            task_result = result["results"][0]
            assert "execution_success" in task_result["metrics"]
            assert "pass_at_k" in task_result["metrics"]

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, evaluation_framework, sample_dataset):
        """Test error handling in complete workflow."""
        # Register model adapter that raises errors
        mock_adapter = Mock(spec=ModelAdapter)
        mock_adapter.model_id = "error_test_model"
        mock_adapter.generate_response = AsyncMock()
        
        # First call succeeds, second call fails
        mock_adapter.generate_response.side_effect = [
            {"response": "Success response", "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
            Exception("Model API error")
        ]
        
        evaluation_framework.register_model_adapter(mock_adapter)
        
        # Register task
        task_config = {
            "task_id": "error_handling_test",
            "task_type": "single_turn",
            "description": "Error handling test",
            "dataset_path": sample_dataset,
            "metrics": ["accuracy"],
            "max_retries": 2,
            "retry_delay": 0.1
        }
        
        task_id = evaluation_framework.register_task(task_config)
        
        # Run evaluation (should handle errors gracefully)
        result = await evaluation_framework.run_evaluation(
            task_ids=[task_id],
            model_id="error_test_model"
        )
        
        # Verify partial results and error handling
        assert result is not None
        task_result = result["results"][0]
        assert "errors" in task_result
        assert len(task_result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_concurrent_evaluation_integration(self, evaluation_framework, sample_dataset):
        """Test concurrent evaluation workflows."""
        # Register model adapter
        mock_adapter = Mock(spec=ModelAdapter)
        mock_adapter.model_id = "concurrent_test_model"
        mock_adapter.generate_response = AsyncMock()
        
        # Add delay to simulate real API calls
        async def delayed_response(prompt, config=None):
            await asyncio.sleep(0.1)  # Small delay
            return {"response": "Test response", "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        
        mock_adapter.generate_response.side_effect = delayed_response
        evaluation_framework.register_model_adapter(mock_adapter)
        
        # Register multiple tasks
        task_configs = [
            {
                "task_id": f"concurrent_task_{i}",
                "task_type": "single_turn",
                "description": f"Concurrent test task {i}",
                "dataset_path": sample_dataset,
                "metrics": ["accuracy"]
            }
            for i in range(3)
        ]
        
        task_ids = []
        for config in task_configs:
            task_id = evaluation_framework.register_task(config)
            task_ids.append(task_id)
        
        # Run concurrent evaluations
        import time
        start_time = time.time()
        
        tasks = [
            evaluation_framework.run_evaluation(
                task_ids=[task_id],
                model_id="concurrent_test_model"
            )
            for task_id in task_ids
        ]
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify all evaluations completed
        assert len(results) == 3
        for result in results:
            assert result is not None
            assert len(result["results"]) == 1
        
        # Concurrent execution should be faster than sequential
        # (This is a rough check - actual timing may vary)
        total_time = end_time - start_time
        assert total_time < 1.0  # Should complete in less than 1 second

    @pytest.mark.asyncio
    async def test_data_flow_integration(self, evaluation_framework, temp_dir):
        """Test data flow through all components."""
        # Create comprehensive dataset
        dataset = [
            {
                "id": "flow_test_1",
                "input": "Create a simple calculator function",
                "expected_output": "def calculator(a, b, operation):\n    if operation == 'add':\n        return a + b\n    elif operation == 'subtract':\n        return a - b\n    elif operation == 'multiply':\n        return a * b\n    elif operation == 'divide':\n        return a / b if b != 0 else None",
                "context": "Python programming",
                "difficulty": "medium",
                "tags": ["programming", "calculator", "functions"]
            }
        ]
        
        dataset_file = temp_dir / "flow_test_dataset.jsonl"
        with open(dataset_file, 'w') as f:
            for item in dataset:
                f.write(json.dumps(item) + '\n')
        
        # Register model adapter
        mock_adapter = Mock(spec=ModelAdapter)
        mock_adapter.model_id = "flow_test_model"
        mock_adapter.generate_response = AsyncMock(return_value={
            "response": "def calculator(a, b, operation):\n    operations = {\n        'add': lambda x, y: x + y,\n        'subtract': lambda x, y: x - y,\n        'multiply': lambda x, y: x * y,\n        'divide': lambda x, y: x / y if y != 0 else None\n    }\n    return operations.get(operation, lambda x, y: None)(a, b)",
            "usage": {"prompt_tokens": 80, "completion_tokens": 60}
        })
        evaluation_framework.register_model_adapter(mock_adapter)
        
        # Register comprehensive task
        task_config = {
            "task_id": "data_flow_test",
            "task_type": "single_turn",
            "description": "Data flow integration test",
            "dataset_path": str(dataset_file),
            "metrics": ["accuracy", "bleu", "rouge", "code_quality"],
            "context_mode": "full_context",
            "enable_analysis": True,
            "enable_visualization": True
        }
        
        task_id = evaluation_framework.register_task(task_config)
        
        # Run evaluation with full pipeline
        result = await evaluation_framework.run_evaluation(
            task_ids=[task_id],
            model_id="flow_test_model",
            enable_analysis=True
        )
        
        # Verify complete data flow
        assert result is not None
        assert "evaluation_id" in result
        assert "results" in result
        assert "analysis" in result
        assert "metadata" in result
        
        task_result = result["results"][0]
        assert "metrics" in task_result
        assert "outputs" in task_result
        assert "analysis" in task_result

    def test_configuration_integration(self, temp_dir):
        """Test configuration integration across components."""
        # Create configuration file
        config = {
            "data_dir": str(temp_dir),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results"),
            "log_level": "INFO",
            "max_concurrent_evaluations": 5,
            "default_timeout": 300,
            "enable_caching": True,
            "metrics": {
                "default_metrics": ["accuracy", "bleu"],
                "code_metrics": ["code_quality", "security_score"],
                "multi_turn_metrics": ["coherence", "context_retention"]
            },
            "sandbox": {
                "enabled": True,
                "timeout": 30,
                "memory_limit": "512MB",
                "cpu_limit": "1.0"
            }
        }
        
        config_file = temp_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        # Initialize framework with config file
        framework = UnifiedEvaluationFramework.from_config_file(str(config_file))
        
        # Verify configuration was applied
        assert framework.config["log_level"] == "INFO"
        assert framework.config["max_concurrent_evaluations"] == 5
        assert framework.config["enable_caching"] is True
        
        # Verify directories were created
        assert framework.data_dir.exists()
        assert framework.cache_dir.exists()
        assert framework.results_dir.exists()

    @pytest.mark.asyncio
    async def test_result_persistence_integration(self, evaluation_framework, sample_dataset):
        """Test result persistence and loading."""
        # Register model and task
        mock_adapter = Mock(spec=ModelAdapter)
        mock_adapter.model_id = "persistence_test_model"
        mock_adapter.generate_response = AsyncMock(return_value={
            "response": "Test response for persistence",
            "usage": {"prompt_tokens": 20, "completion_tokens": 10}
        })
        evaluation_framework.register_model_adapter(mock_adapter)
        
        task_config = {
            "task_id": "persistence_test",
            "task_type": "single_turn",
            "description": "Persistence test",
            "dataset_path": sample_dataset,
            "metrics": ["accuracy"]
        }
        
        task_id = evaluation_framework.register_task(task_config)
        
        # Run evaluation
        result = await evaluation_framework.run_evaluation(
            task_ids=[task_id],
            model_id="persistence_test_model"
        )
        
        evaluation_id = result["evaluation_id"]
        
        # Verify result was saved
        saved_file = evaluation_framework.results_dir / f"{evaluation_id}.json"
        assert saved_file.exists()
        
        # Load and verify saved result
        loaded_result = evaluation_framework.load_results(evaluation_id)
        assert loaded_result is not None
        assert loaded_result["evaluation_id"] == evaluation_id
        assert len(loaded_result["results"]) == 1