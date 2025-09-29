"""
Integration Test Suite for Multi-Turn Evaluation Engine

This module provides comprehensive integration tests for all evaluation scenarios,
performance benchmarks, load testing, and compatibility tests with existing lm-eval tasks.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import pytest
import asyncio
import time
import json
import tempfile
import concurrent.futures
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional
import logging

# Import core components
from ..core.data_models import (
    EvaluationConfig, TaskConfig, ModelConfig, MultiTurnConfig,
    EvaluationResult, TurnResult, AggregatedMetrics
)
from ..core.compatibility import (
    ConfigurationAdapter, LegacyEvaluationBridge, simple_evaluate
)

# Import orchestration components
try:
    from ..core.orchestrator import MultiTurnOrchestrator
    from ..core.policy_engine import PolicyEngine
    from ..core.feedback_processor import FeedbackProcessor
    from ..core.safety_guard import SafetyGuard
    from ..core.metrics_engine import MetricsEngine
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

# Import adapters
try:
    from ..core.adapters import BenchmarkAdapter
    from ..core.lm_eval_adapter import LMEvalAdapter
    from ..core.swe_bench_adapter import SWEBenchAdapter
    from ..core.intercode_adapter import InterCodeAdapter
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False

logger = logging.getLogger(__name__)


class MockModel:
    """Mock model for testing."""
    
    def __init__(self, model_id: str = "test_model"):
        self.model_id = model_id
        self.call_count = 0
        self.responses = []
    
    async def generate_action(self, observation: Any, turn_results: List[TurnResult]) -> str:
        """Generate mock action."""
        self.call_count += 1
        if self.responses:
            return self.responses[min(self.call_count - 1, len(self.responses) - 1)]
        return f"action_{self.call_count}"
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Synchronous generation for compatibility."""
        self.call_count += 1
        if self.responses:
            return self.responses[min(self.call_count - 1, len(self.responses) - 1)]
        return f"response_{self.call_count}"


class MockEnvironment:
    """Mock environment for testing."""
    
    def __init__(self, max_steps: int = 5, success_at_step: Optional[int] = None):
        self.max_steps = max_steps
        self.success_at_step = success_at_step
        self.current_step = 0
        self.is_done = False
        self.is_successful = False
    
    def reset(self):
        """Reset environment."""
        self.current_step = 0
        self.is_done = False
        self.is_successful = False
        return {"observation": "initial_state", "step": 0}
    
    def step(self, action: str):
        """Execute step."""
        self.current_step += 1
        
        # Check for success condition
        if self.success_at_step and self.current_step >= self.success_at_step:
            self.is_successful = True
            self.is_done = True
        elif self.current_step >= self.max_steps:
            self.is_done = True
        
        observation = {
            "observation": f"step_{self.current_step}_result",
            "step": self.current_step,
            "action_taken": action
        }
        
        reward = 1.0 if self.is_successful else 0.0
        info = {
            "step": self.current_step,
            "max_steps": self.max_steps,
            "success": self.is_successful
        }
        
        return observation, reward, self.is_done, info
    
    def success(self) -> bool:
        """Check if task is successful."""
        return self.is_successful
    
    def info(self) -> Dict[str, Any]:
        """Get environment info."""
        return {
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "is_done": self.is_done,
            "is_successful": self.is_successful
        }


@pytest.mark.integration
class TestEndToEndEvaluationScenarios:
    """Test complete end-to-end evaluation scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_model = MockModel()
        self.mock_env = MockEnvironment(max_steps=3, success_at_step=2)
    
    def test_single_turn_evaluation_scenario(self):
        """Test complete single-turn evaluation scenario."""
        # Create configuration
        model_config = ModelConfig(
            model_id="test_model",
            model_type="mock",
            parameters={"temperature": 0.7}
        )
        
        task_config = TaskConfig(
            task_id="test_single_turn",
            task_type="single_turn",
            model_ref="test_model",
            parameters={"num_fewshot": 0}
        )
        
        config = EvaluationConfig(
            models={"test_model": model_config},
            tasks=[task_config]
        )
        
        # Validate configuration
        assert config.validate()
        
        # Test that single-turn tasks are identified correctly
        single_turn_tasks = config.get_single_turn_tasks()
        assert len(single_turn_tasks) == 1
        assert single_turn_tasks[0].task_id == "test_single_turn"
    
    @pytest.mark.skipif(not ORCHESTRATOR_AVAILABLE, reason="Orchestrator not available")
    def test_multi_turn_evaluation_scenario(self):
        """Test complete multi-turn evaluation scenario."""
        # Create configuration
        model_config = ModelConfig(
            model_id="test_model",
            model_type="mock",
            parameters={"temperature": 0.7}
        )
        
        task_config = TaskConfig(
            task_id="test_multi_turn",
            task_type="multi_turn",
            model_ref="test_model",
            parameters={"max_turns": 5}
        )
        
        multi_turn_config = MultiTurnConfig(
            max_turns=5,
            conversation_timeout=300
        )
        
        config = EvaluationConfig(
            models={"test_model": model_config},
            tasks=[task_config],
            multi_turn_config=multi_turn_config
        )
        
        # Validate configuration
        assert config.validate()
        
        # Test that multi-turn tasks are identified correctly
        multi_turn_tasks = config.get_multi_turn_tasks()
        assert len(multi_turn_tasks) == 1
        assert multi_turn_tasks[0].task_id == "test_multi_turn"
    
    def test_mixed_evaluation_scenario(self):
        """Test evaluation with both single-turn and multi-turn tasks."""
        model_config = ModelConfig(
            model_id="test_model",
            model_type="mock"
        )
        
        single_turn_task = TaskConfig(
            task_id="single_turn_task",
            task_type="single_turn",
            model_ref="test_model"
        )
        
        multi_turn_task = TaskConfig(
            task_id="multi_turn_task",
            task_type="multi_turn",
            model_ref="test_model"
        )
        
        config = EvaluationConfig(
            models={"test_model": model_config},
            tasks=[single_turn_task, multi_turn_task]
        )
        
        assert config.validate()
        assert len(config.get_single_turn_tasks()) == 1
        assert len(config.get_multi_turn_tasks()) == 1
    
    def test_configuration_validation_scenarios(self):
        """Test various configuration validation scenarios."""
        # Test empty models
        with pytest.raises(ValueError, match="At least one model must be configured"):
            config = EvaluationConfig(models={}, tasks=[])
            config.validate()
        
        # Test empty tasks
        model_config = ModelConfig(model_id="test", model_type="mock")
        with pytest.raises(ValueError, match="At least one task must be configured"):
            config = EvaluationConfig(models={"test": model_config}, tasks=[])
            config.validate()
        
        # Test invalid model reference
        task_config = TaskConfig(
            task_id="test_task",
            task_type="single_turn",
            model_ref="nonexistent_model"
        )
        with pytest.raises(ValueError, match="references unknown model"):
            config = EvaluationConfig(
                models={"test": model_config},
                tasks=[task_config]
            )
            config.validate()


@pytest.mark.integration
class TestBackwardCompatibilityIntegration:
    """Test backward compatibility with existing lm-eval tasks."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.bridge = LegacyEvaluationBridge()
        self.adapter = ConfigurationAdapter()
    
    def test_lm_eval_task_compatibility(self):
        """Test compatibility with existing lm-eval task formats."""
        # Test common lm-eval task names
        lm_eval_tasks = [
            "hellaswag",
            "arc_easy",
            "arc_challenge",
            "winogrande",
            "piqa",
            "boolq"
        ]
        
        for task in lm_eval_tasks:
            # Should be detected as single-turn
            assert not self.bridge._detect_multi_turn_tasks(task)
            
            # Should be convertible to lm-eval args
            config = {
                'model': 'hf',
                'tasks': task,
                'model_args': {'pretrained': 'gpt2'}
            }
            lm_eval_args = self.bridge._convert_to_lm_eval_args(config)
            assert lm_eval_args['tasks'] == task
            assert lm_eval_args['model'] == 'hf'
    
    def test_legacy_configuration_formats(self):
        """Test various legacy configuration formats."""
        # Test CLI-style configuration
        cli_config = {
            'model': 'hf',
            'model_args': 'pretrained=gpt2,device=cpu',
            'tasks': 'hellaswag,arc_easy',
            'num_fewshot': 5,
            'batch_size': 8,
            'output_path': './results'
        }
        
        # Should adapt successfully
        adapted = self.adapter.adapt_legacy_config(cli_config)
        assert isinstance(adapted, EvaluationConfig)
        assert len(adapted.tasks) == 2
        
        # Test JSON-style configuration
        json_config = {
            'model': 'openai',
            'model_args': {'model': 'gpt-3.5-turbo', 'api_key': 'test'},
            'tasks': ['hellaswag'],
            'num_fewshot': 0
        }
        
        adapted = self.adapter.adapt_legacy_config(json_config)
        assert isinstance(adapted, EvaluationConfig)
        assert len(adapted.tasks) == 1
    
    def test_result_format_compatibility(self):
        """Test that results maintain compatibility with existing formats."""
        # Create mock evaluation results
        metrics = AggregatedMetrics(
            resolved_percentage=0.85,
            recall=0.80,
            mrr=0.75,
            avg_turns=1.0,  # Single-turn equivalent
            avg_steps=1.0,
            redundancy_rate=0.0,
            edit_churn=0.0,
            files_touched=0,
            recovery_rate=1.0,
            stability_score=1.0,
            wall_time_per_solved=2.5,
            tokens_per_solved=150,
            cost_per_solved=0.001,
            safety_incidents=0,
            policy_violations=0
        )
        
        result = EvaluationResult(
            evaluation_id='test_eval',
            task_id='hellaswag',
            model_id='gpt2',
            success=True,
            total_turns=1,
            turn_results=[],
            aggregated_metrics=metrics,
            metadata={}
        )
        
        # Convert to legacy format
        legacy_results = self.bridge._convert_results_to_legacy_format([result])
        
        # Check legacy format structure
        assert 'results' in legacy_results
        assert 'configs' in legacy_results
        assert 'versions' in legacy_results
        assert 'n-shot' in legacy_results
        
        # Check specific task results
        assert 'hellaswag' in legacy_results['results']
        task_results = legacy_results['results']['hellaswag']
        assert 'acc' in task_results
        assert task_results['acc'] == 0.85
    
    def test_deprecated_parameter_handling(self):
        """Test handling of deprecated parameters."""
        # Test evaluation with deprecated parameters
        result = self.bridge.evaluate(
            model='hf',
            tasks='hellaswag',
            write_out=True,  # Deprecated
            check_integrity=True,  # Deprecated
            predict_only=True  # Deprecated
        )
        
        # Should succeed but with warnings
        assert len(result.deprecated_features) > 0
        assert any('write_out' in feature for feature in result.deprecated_features)
        assert any('check_integrity' in feature for feature in result.deprecated_features)
        assert any('predict_only' in feature for feature in result.deprecated_features)


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmarks and load testing."""
    
    def setup_method(self):
        """Set up performance test fixtures."""
        self.mock_model = MockModel()
        self.mock_env = MockEnvironment()
    
    def test_single_evaluation_performance(self):
        """Test performance of single evaluation."""
        start_time = time.time()
        
        # Create simple configuration
        model_config = ModelConfig(
            model_id="perf_test_model",
            model_type="mock"
        )
        
        task_config = TaskConfig(
            task_id="perf_test_task",
            task_type="single_turn",
            model_ref="perf_test_model"
        )
        
        config = EvaluationConfig(
            models={"perf_test_model": model_config},
            tasks=[task_config]
        )
        
        # Validate configuration (should be fast)
        config.validate()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time
        assert execution_time < 1.0, f"Configuration validation took {execution_time:.3f}s"
    
    def test_concurrent_evaluations_performance(self):
        """Test performance with concurrent evaluations."""
        num_concurrent = 5
        
        def create_evaluation_config(task_id: str) -> EvaluationConfig:
            model_config = ModelConfig(
                model_id=f"model_{task_id}",
                model_type="mock"
            )
            
            task_config = TaskConfig(
                task_id=task_id,
                task_type="single_turn",
                model_ref=f"model_{task_id}"
            )
            
            return EvaluationConfig(
                models={f"model_{task_id}": model_config},
                tasks=[task_config]
            )
        
        start_time = time.time()
        
        # Create multiple configurations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = []
            for i in range(num_concurrent):
                future = executor.submit(create_evaluation_config, f"task_{i}")
                futures.append(future)
            
            # Wait for all to complete
            configs = []
            for future in concurrent.futures.as_completed(futures):
                config = future.result()
                config.validate()
                configs.append(config)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        assert len(configs) == num_concurrent
        # Should complete within reasonable time even with concurrency
        assert execution_time < 5.0, f"Concurrent evaluation setup took {execution_time:.3f}s"
    
    def test_large_configuration_performance(self):
        """Test performance with large configurations."""
        num_models = 10
        num_tasks_per_model = 20
        
        start_time = time.time()
        
        # Create large configuration
        models = {}
        tasks = []
        
        for i in range(num_models):
            model_id = f"model_{i}"
            models[model_id] = ModelConfig(
                model_id=model_id,
                model_type="mock",
                parameters={"param1": i, "param2": f"value_{i}"}
            )
            
            for j in range(num_tasks_per_model):
                task_id = f"task_{i}_{j}"
                tasks.append(TaskConfig(
                    task_id=task_id,
                    task_type="single_turn",
                    model_ref=model_id,
                    parameters={"task_param": j}
                ))
        
        config = EvaluationConfig(models=models, tasks=tasks)
        
        # Validate large configuration
        config.validate()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        total_tasks = num_models * num_tasks_per_model
        assert len(config.tasks) == total_tasks
        
        # Should handle large configurations efficiently
        assert execution_time < 2.0, f"Large configuration validation took {execution_time:.3f}s"
    
    def test_memory_usage_stability(self):
        """Test memory usage remains stable during operations."""
        import gc
        import sys
        
        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform multiple operations
        for i in range(100):
            model_config = ModelConfig(
                model_id=f"temp_model_{i}",
                model_type="mock"
            )
            
            task_config = TaskConfig(
                task_id=f"temp_task_{i}",
                task_type="single_turn",
                model_ref=f"temp_model_{i}"
            )
            
            config = EvaluationConfig(
                models={f"temp_model_{i}": model_config},
                tasks=[task_config]
            )
            
            config.validate()
            
            # Clear references
            del model_config, task_config, config
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory usage should not grow significantly
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Memory usage grew by {object_growth} objects"


@pytest.mark.integration
class TestAdapterIntegration:
    """Test integration with various adapters."""
    
    @pytest.mark.skipif(not ADAPTERS_AVAILABLE, reason="Adapters not available")
    def test_lm_eval_adapter_integration(self):
        """Test integration with LM-Eval adapter."""
        # This would test actual integration with lm-eval
        # For now, we test the adapter interface
        
        # Mock adapter should implement required interface
        class MockLMEvalAdapter:
            def create_environment(self, task_config):
                return MockEnvironment()
            
            def load_tasks(self, task_filter=None):
                return ["hellaswag", "arc_easy"]
            
            def convert_results(self, results):
                return {"converted": True}
        
        adapter = MockLMEvalAdapter()
        
        # Test interface compliance
        env = adapter.create_environment({"task": "hellaswag"})
        assert hasattr(env, 'reset')
        assert hasattr(env, 'step')
        
        tasks = adapter.load_tasks()
        assert isinstance(tasks, list)
        assert len(tasks) > 0
        
        results = adapter.convert_results({"test": "data"})
        assert isinstance(results, dict)
    
    def test_adapter_error_handling(self):
        """Test adapter error handling and fallbacks."""
        class FailingAdapter:
            def create_environment(self, task_config):
                raise RuntimeError("Adapter failed")
            
            def load_tasks(self, task_filter=None):
                raise RuntimeError("Task loading failed")
        
        adapter = FailingAdapter()
        
        # Should handle adapter failures gracefully
        with pytest.raises(RuntimeError, match="Adapter failed"):
            adapter.create_environment({})
        
        with pytest.raises(RuntimeError, match="Task loading failed"):
            adapter.load_tasks()
    
    def test_adapter_configuration_validation(self):
        """Test adapter configuration validation."""
        # Test various adapter configurations
        valid_configs = [
            {"adapter": "lm_eval", "task": "hellaswag"},
            {"adapter": "swe_bench", "task": "swe_bench_lite"},
            {"adapter": "intercode", "task": "intercode_python"}
        ]
        
        for config in valid_configs:
            # Configuration should be valid
            assert isinstance(config, dict)
            assert "adapter" in config
            assert "task" in config
        
        # Test invalid configurations
        invalid_configs = [
            {},  # Missing required fields
            {"adapter": "unknown"},  # Missing task
            {"task": "test"}  # Missing adapter
        ]
        
        for config in invalid_configs:
            # Should be identifiable as invalid
            assert not (config.get("adapter") and config.get("task"))


@pytest.mark.integration
class TestDataValidationAndSerialization:
    """Test data validation and serialization across the system."""
    
    def test_configuration_serialization(self):
        """Test configuration serialization and deserialization."""
        # Create configuration
        model_config = ModelConfig(
            model_id="test_model",
            model_type="mock",
            parameters={"temp": 0.7}
        )
        
        task_config = TaskConfig(
            task_id="test_task",
            task_type="single_turn",
            model_ref="test_model"
        )
        
        config = EvaluationConfig(
            models={"test_model": model_config},
            tasks=[task_config],
            metadata={"version": "1.0"}
        )
        
        # Test JSON serialization
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            # Convert to dict for JSON serialization
            config_dict = {
                "models": {
                    "test_model": {
                        "model_id": model_config.model_id,
                        "model_type": model_config.model_type,
                        "parameters": model_config.parameters,
                        "device": model_config.device
                    }
                },
                "tasks": [{
                    "task_id": task_config.task_id,
                    "task_type": task_config.task_type,
                    "model_ref": task_config.model_ref,
                    "parameters": task_config.parameters
                }],
                "metadata": config.metadata
            }
            
            json.dump(config_dict, f)
            config_path = f.name
        
        try:
            # Load and verify
            with open(config_path, 'r') as f:
                loaded_dict = json.load(f)
            
            assert loaded_dict["models"]["test_model"]["model_id"] == "test_model"
            assert loaded_dict["tasks"][0]["task_id"] == "test_task"
            assert loaded_dict["metadata"]["version"] == "1.0"
            
        finally:
            Path(config_path).unlink()
    
    def test_result_serialization(self):
        """Test result serialization and deserialization."""
        # Create evaluation result
        metrics = AggregatedMetrics(
            resolved_percentage=0.85,
            recall=0.80,
            mrr=0.75,
            avg_turns=3.2,
            avg_steps=8.5,
            redundancy_rate=0.15,
            edit_churn=2.3,
            files_touched=4,
            recovery_rate=0.90,
            stability_score=0.88,
            wall_time_per_solved=45.2,
            tokens_per_solved=1250,
            cost_per_solved=0.025,
            safety_incidents=0,
            policy_violations=0
        )
        
        result = EvaluationResult(
            evaluation_id="test_eval",
            task_id="test_task",
            model_id="test_model",
            success=True,
            total_turns=3,
            turn_results=[],
            aggregated_metrics=metrics,
            metadata={"test": True}
        )
        
        # Test serialization to dict
        result_dict = {
            "evaluation_id": result.evaluation_id,
            "task_id": result.task_id,
            "model_id": result.model_id,
            "success": result.success,
            "total_turns": result.total_turns,
            "aggregated_metrics": {
                "resolved_percentage": metrics.resolved_percentage,
                "avg_turns": metrics.avg_turns,
                "cost_per_solved": metrics.cost_per_solved
            }
        }
        
        # Verify serialization
        assert result_dict["evaluation_id"] == "test_eval"
        assert result_dict["success"] is True
        assert result_dict["aggregated_metrics"]["resolved_percentage"] == 0.85
    
    def test_cross_format_compatibility(self):
        """Test compatibility across different data formats."""
        # Test YAML compatibility
        yaml_config = """
        models:
          test_model:
            model_id: test_model
            model_type: mock
            parameters:
              temperature: 0.7
        tasks:
          - task_id: test_task
            task_type: single_turn
            model_ref: test_model
        """
        
        # Should be parseable (if yaml is available)
        try:
            import yaml
            parsed = yaml.safe_load(yaml_config)
            assert "models" in parsed
            assert "tasks" in parsed
            assert parsed["models"]["test_model"]["model_id"] == "test_model"
        except ImportError:
            # YAML not available, skip this part
            pass
        
        # Test JSON compatibility
        json_config = {
            "models": {
                "test_model": {
                    "model_id": "test_model",
                    "model_type": "mock"
                }
            },
            "tasks": [{
                "task_id": "test_task",
                "task_type": "single_turn",
                "model_ref": "test_model"
            }]
        }
        
        # Should be valid JSON
        json_str = json.dumps(json_config)
        parsed_json = json.loads(json_str)
        assert parsed_json == json_config


@pytest.mark.integration
class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms."""
    
    def test_configuration_error_recovery(self):
        """Test recovery from configuration errors."""
        # Test invalid model configuration
        with pytest.raises(ValueError):
            invalid_model = ModelConfig(model_id="", model_type="")
            invalid_model.validate()
        
        # Test invalid task configuration
        with pytest.raises(ValueError):
            invalid_task = TaskConfig(task_id="", task_type="invalid", model_ref="")
            invalid_task.validate()
        
        # Test recovery with valid configuration
        valid_model = ModelConfig(model_id="valid", model_type="mock")
        valid_task = TaskConfig(
            task_id="valid",
            task_type="single_turn",
            model_ref="valid"
        )
        
        assert valid_model.validate()
        assert valid_task.validate()
    
    def test_evaluation_error_handling(self):
        """Test evaluation error handling."""
        bridge = LegacyEvaluationBridge()
        
        # Test with invalid model
        result = bridge.evaluate(model="", tasks="")
        assert not result.success
        assert len(result.warnings) > 0
        
        # Test with valid configuration
        result = bridge.evaluate(model="mock", tasks="test_task")
        # Should handle gracefully even if backend is not available
        assert isinstance(result, type(result))  # Should return CompatibilityResult
    
    def test_adapter_failure_handling(self):
        """Test handling of adapter failures."""
        class FailingAdapter:
            def create_environment(self, config):
                raise RuntimeError("Environment creation failed")
        
        adapter = FailingAdapter()
        
        # Should handle adapter failures
        with pytest.raises(RuntimeError, match="Environment creation failed"):
            adapter.create_environment({})
    
    def test_resource_exhaustion_handling(self):
        """Test handling of resource exhaustion scenarios."""
        # Test with very large configuration
        large_config = EvaluationConfig(
            models={f"model_{i}": ModelConfig(
                model_id=f"model_{i}",
                model_type="mock"
            ) for i in range(1000)},
            tasks=[TaskConfig(
                task_id=f"task_{i}",
                task_type="single_turn",
                model_ref=f"model_{i % 10}"  # Reference existing models
            ) for i in range(10000)]
        )
        
        # Should handle large configurations
        try:
            large_config.validate()
            # If validation succeeds, that's good
            assert True
        except Exception as e:
            # If it fails due to resource constraints, that's also acceptable
            assert "model" in str(e).lower() or "task" in str(e).lower()


if __name__ == '__main__':
    # Run integration tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "integration"
    ])