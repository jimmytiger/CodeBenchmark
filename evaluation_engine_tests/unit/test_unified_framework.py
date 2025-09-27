"""
Unit tests for UnifiedEvaluationFramework.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from pathlib import Path

from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework


class TestUnifiedEvaluationFramework:
    """Test cases for UnifiedEvaluationFramework."""

    def test_framework_initialization(self, temp_dir):
        """Test framework initialization with valid config."""
        config = {
            "data_dir": str(temp_dir),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results"),
            "log_level": "INFO"
        }
        
        framework = UnifiedEvaluationFramework(config)
        
        assert framework.config == config
        assert framework.data_dir == Path(config["data_dir"])
        assert framework.cache_dir == Path(config["cache_dir"])
        assert framework.results_dir == Path(config["results_dir"])

    def test_framework_initialization_creates_directories(self, temp_dir):
        """Test that framework creates necessary directories."""
        config = {
            "data_dir": str(temp_dir / "data"),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results")
        }
        
        framework = UnifiedEvaluationFramework(config)
        
        assert framework.data_dir.exists()
        assert framework.cache_dir.exists()
        assert framework.results_dir.exists()

    def test_framework_initialization_invalid_config(self):
        """Test framework initialization with invalid config."""
        with pytest.raises(ValueError, match="data_dir is required"):
            UnifiedEvaluationFramework({})

    @patch('evaluation_engine.core.unified_framework.TaskRegistry')
    @patch('evaluation_engine.core.unified_framework.ModelConfigurationManager')
    def test_component_initialization(self, mock_model_manager, mock_task_registry, temp_dir):
        """Test that all components are properly initialized."""
        config = {
            "data_dir": str(temp_dir),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results")
        }
        
        framework = UnifiedEvaluationFramework(config)
        
        # Verify components are initialized
        assert framework.task_registry is not None
        assert framework.model_manager is not None
        assert framework.prompt_engine is not None
        assert framework.metrics_engine is not None
        assert framework.analysis_engine is not None

    def test_register_task(self, unified_framework, sample_task_config):
        """Test task registration."""
        task_id = unified_framework.register_task(sample_task_config)
        
        assert task_id is not None
        assert task_id in unified_framework.task_registry.tasks

    def test_register_model_adapter(self, unified_framework, mock_model_adapter):
        """Test model adapter registration."""
        result = unified_framework.register_model_adapter(mock_model_adapter)
        
        assert result is True
        assert mock_model_adapter.model_id in unified_framework.model_manager.adapters

    @pytest.mark.asyncio
    async def test_run_evaluation_single_task(self, unified_framework, sample_task_config, sample_evaluation_data):
        """Test running evaluation on a single task."""
        # Register task
        task_id = unified_framework.register_task(sample_task_config)
        
        # Mock evaluation data
        with patch.object(unified_framework, '_load_evaluation_data', return_value=sample_evaluation_data):
            with patch.object(unified_framework, '_execute_task', return_value={"accuracy": 0.85, "bleu": 0.72}):
                result = await unified_framework.run_evaluation(
                    task_ids=[task_id],
                    model_id="mock_model"
                )
        
        assert result is not None
        assert "results" in result
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_run_evaluation_multiple_tasks(self, unified_framework, sample_task_config, sample_evaluation_data):
        """Test running evaluation on multiple tasks."""
        # Register multiple tasks
        task_configs = [
            {**sample_task_config, "task_id": f"test_task_{i}"}
            for i in range(3)
        ]
        task_ids = [unified_framework.register_task(config) for config in task_configs]
        
        with patch.object(unified_framework, '_load_evaluation_data', return_value=sample_evaluation_data):
            with patch.object(unified_framework, '_execute_task', return_value={"accuracy": 0.85}):
                result = await unified_framework.run_evaluation(
                    task_ids=task_ids,
                    model_id="mock_model"
                )
        
        assert len(result["results"]) == 3

    def test_get_available_tasks(self, unified_framework, sample_task_config):
        """Test getting available tasks."""
        # Register some tasks
        for i in range(3):
            config = {**sample_task_config, "task_id": f"test_task_{i}"}
            unified_framework.register_task(config)
        
        tasks = unified_framework.get_available_tasks()
        
        assert len(tasks) >= 3
        assert all("test_task_" in task["task_id"] for task in tasks if "test_task_" in task["task_id"])

    def test_get_available_models(self, unified_framework, mock_model_adapter):
        """Test getting available models."""
        unified_framework.register_model_adapter(mock_model_adapter)
        
        models = unified_framework.get_available_models()
        
        assert len(models) >= 1
        assert any(model["model_id"] == "mock_model" for model in models)

    def test_save_results(self, unified_framework, temp_dir):
        """Test saving evaluation results."""
        results = {
            "evaluation_id": "test_eval_123",
            "timestamp": "2024-01-01T00:00:00Z",
            "results": [
                {
                    "task_id": "test_task",
                    "metrics": {"accuracy": 0.85}
                }
            ]
        }
        
        file_path = unified_framework.save_results(results)
        
        assert file_path.exists()
        with open(file_path, 'r') as f:
            saved_results = json.load(f)
        assert saved_results == results

    def test_load_results(self, unified_framework, temp_dir):
        """Test loading evaluation results."""
        results = {
            "evaluation_id": "test_eval_123",
            "results": [{"task_id": "test_task", "metrics": {"accuracy": 0.85}}]
        }
        
        # Save results first
        file_path = unified_framework.save_results(results)
        
        # Load results
        loaded_results = unified_framework.load_results(file_path.name.replace('.json', ''))
        
        assert loaded_results == results

    def test_cleanup_resources(self, unified_framework):
        """Test resource cleanup."""
        # This should not raise any exceptions
        unified_framework.cleanup_resources()

    def test_framework_context_manager(self, temp_dir):
        """Test framework as context manager."""
        config = {
            "data_dir": str(temp_dir),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results")
        }
        
        with UnifiedEvaluationFramework(config) as framework:
            assert framework is not None
            assert hasattr(framework, 'task_registry')

    def test_error_handling_invalid_task_id(self, unified_framework):
        """Test error handling for invalid task ID."""
        with pytest.raises(ValueError, match="Task not found"):
            unified_framework.get_task_config("invalid_task_id")

    def test_error_handling_invalid_model_id(self, unified_framework):
        """Test error handling for invalid model ID."""
        with pytest.raises(ValueError, match="Model adapter not found"):
            unified_framework.get_model_adapter("invalid_model_id")

    @pytest.mark.asyncio
    async def test_concurrent_evaluations(self, unified_framework, sample_task_config, sample_evaluation_data):
        """Test running concurrent evaluations."""
        import asyncio
        
        # Register task
        task_id = unified_framework.register_task(sample_task_config)
        
        async def run_single_evaluation():
            with patch.object(unified_framework, '_load_evaluation_data', return_value=sample_evaluation_data):
                with patch.object(unified_framework, '_execute_task', return_value={"accuracy": 0.85}):
                    return await unified_framework.run_evaluation(
                        task_ids=[task_id],
                        model_id="mock_model"
                    )
        
        # Run multiple evaluations concurrently
        tasks = [run_single_evaluation() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(result is not None for result in results)

    def test_configuration_validation(self, temp_dir):
        """Test configuration validation."""
        # Valid config
        valid_config = {
            "data_dir": str(temp_dir),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results"),
            "log_level": "INFO"
        }
        framework = UnifiedEvaluationFramework(valid_config)
        assert framework is not None
        
        # Invalid log level
        invalid_config = {
            "data_dir": str(temp_dir),
            "cache_dir": str(temp_dir / "cache"),
            "results_dir": str(temp_dir / "results"),
            "log_level": "INVALID"
        }
        with pytest.raises(ValueError, match="Invalid log level"):
            UnifiedEvaluationFramework(invalid_config)

    def test_metrics_aggregation(self, unified_framework):
        """Test metrics aggregation functionality."""
        task_results = [
            {"task_id": "task1", "metrics": {"accuracy": 0.8, "bleu": 0.7}},
            {"task_id": "task2", "metrics": {"accuracy": 0.9, "bleu": 0.8}},
            {"task_id": "task3", "metrics": {"accuracy": 0.85, "bleu": 0.75}}
        ]
        
        aggregated = unified_framework.aggregate_metrics(task_results)
        
        assert "accuracy" in aggregated
        assert "bleu" in aggregated
        assert aggregated["accuracy"]["mean"] == pytest.approx(0.85, rel=1e-2)
        assert aggregated["bleu"]["mean"] == pytest.approx(0.75, rel=1e-2)

    def test_task_filtering(self, unified_framework, sample_task_config):
        """Test task filtering functionality."""
        # Register tasks with different properties
        configs = [
            {**sample_task_config, "task_id": "easy_task", "difficulty": "easy"},
            {**sample_task_config, "task_id": "medium_task", "difficulty": "medium"},
            {**sample_task_config, "task_id": "hard_task", "difficulty": "hard"}
        ]
        
        for config in configs:
            unified_framework.register_task(config)
        
        # Filter by difficulty
        easy_tasks = unified_framework.filter_tasks({"difficulty": "easy"})
        assert len(easy_tasks) >= 1
        assert all(task.get("difficulty") == "easy" for task in easy_tasks)

    def test_memory_management(self, unified_framework, performance_test_data):
        """Test memory management with large datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process large dataset
        with patch.object(unified_framework, '_load_evaluation_data', return_value=performance_test_data):
            unified_framework._process_large_dataset(performance_test_data)
        
        # Force garbage collection
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for test data)
        assert memory_increase < 100 * 1024 * 1024  # 100MB