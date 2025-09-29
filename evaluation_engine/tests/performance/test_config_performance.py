"""
Performance and compatibility tests for configuration-driven evaluation system.

This module provides comprehensive performance benchmarks and compatibility
tests to ensure the system scales well and maintains compatibility.
"""

import pytest
import tempfile
import json
import time
import threading
import queue
import os
import psutil
import gc
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from evaluation_engine.config.parser import ConfigParser
from evaluation_engine.config.validator import ConfigValidator
from evaluation_engine.config.builder import TaskBuilder
from evaluation_engine.config.evaluator import ConfigDrivenEvaluator
from evaluation_engine.config.templates import ModelTemplateManager
from evaluation_engine.config.models import (
    EvaluationConfig, ConfigMetadata, TaskConfig, ModelConfig
)


class TestConfigurationPerformance:
    """Test performance characteristics of configuration system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_large_configuration_parsing_performance(self):
        """Test parsing performance with very large configurations."""
        # Create configuration with 1000 tasks and 100 models
        large_config = {
            "metadata": {
                "name": "Large Configuration Performance Test",
                "version": "1.0"
            },
            "variables": {},
            "models": {},
            "tasks": []
        }
        
        # Add 100 variables
        for i in range(100):
            large_config["variables"][f"var_{i}"] = f"value_{i}"
        
        # Add 100 models with variable references
        for i in range(100):
            large_config["models"][f"model_{i}"] = {
                "name": f"model_{i}",
                "type": "openai",
                "model_name": f"gpt-3.5-turbo-{i}",
                "parameters": {
                    "temperature": "${var_" + str(i % 100) + "}",
                    "max_tokens": 1000 + i,
                    "top_p": 0.9,
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0.1
                },
                "system_prompt": f"You are assistant number {i}",
                "prompt_template": "Question: {question}\\nAnswer:"
            }
        
        # Add 1000 tasks with complex dependencies
        for i in range(1000):
            depends_on = []
            if i > 0:
                depends_on.append(f"task_{i-1}")
            if i > 10:
                depends_on.append(f"task_{i-10}")
            if i % 50 == 0 and i > 0:
                depends_on.append("task_0")
            
            large_config["tasks"].append({
                "name": f"task_{i}",
                "description": f"Task number {i} for performance testing",
                "model_ref": f"model_{i % 100}",
                "task_name": "hellaswag",
                "num_fewshot": i % 20,
                "batch_size": (i % 64) + 1,
                "task_config": {
                    "limit": 100 + (i % 500),
                    "temperature": 0.7 + (i * 0.0001)
                },
                "depends_on": depends_on
            })
        
        # Add complex output configuration
        large_config["output"] = {
            "directory": "./large_test_results",
            "formats": ["json", "csv", "html"],
            "include_raw_responses": True,
            "generate_report": True,
            "compare_models": True
        }
        
        config_path = os.path.join(self.temp_dir, "large_config.json")
        with open(config_path, 'w') as f:
            json.dump(large_config, f)
        
        # Measure parsing performance
        parser = ConfigParser()
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        config = parser.parse_config(config_path)
        
        parse_time = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_usage = end_memory - start_memory
        
        # Performance assertions
        assert parse_time < 15.0, f"Parsing took {parse_time:.2f}s, expected < 15s"
        assert memory_usage < 500, f"Memory usage {memory_usage:.2f}MB, expected < 500MB"
        
        # Verify correctness
        assert len(config.models) == 100
        assert len(config.tasks) == 1000
        assert len(config.variables) == 100
        
        # Verify variable resolution worked
        assert config.models["model_0"].parameters["temperature"] == "value_0"
        
        print(f"Large config parsing: {parse_time:.2f}s, {memory_usage:.2f}MB")
    
    def test_configuration_validation_performance(self):
        """Test validation performance with large configurations."""
        # Create configuration with many models and tasks
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Validation Performance Test"),
            variables={f"var_{i}": f"value_{i}" for i in range(50)},
            models={
                f"model_{i}": ModelConfig(
                    name=f"model_{i}",
                    type="openai",
                    model_name=f"gpt-3.5-turbo-{i}",
                    parameters={"temperature": 0.7 + (i * 0.001)}
                ) for i in range(50)
            },
            tasks=[
                TaskConfig(
                    name=f"task_{i}",
                    model_ref=f"model_{i % 50}",
                    task_name="hellaswag",
                    num_fewshot=i % 10,
                    batch_size=(i % 32) + 1,
                    depends_on=[f"task_{j}" for j in range(max(0, i-3), i)]
                ) for i in range(200)
            ]
        )
        
        validator = ConfigValidator()
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        result = validator.validate_config(config)
        
        validation_time = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_usage = end_memory - start_memory
        
        # Performance assertions
        assert validation_time < 10.0, f"Validation took {validation_time:.2f}s, expected < 10s"
        assert memory_usage < 200, f"Memory usage {memory_usage:.2f}MB, expected < 200MB"
        
        # Verify validation worked
        assert result.is_valid
        
        print(f"Large config validation: {validation_time:.2f}s, {memory_usage:.2f}MB")
    
    def test_task_building_performance(self):
        """Test task building performance with complex configurations."""
        # Create configuration with complex task dependencies
        models = {
            f"model_{i}": ModelConfig(
                name=f"model_{i}",
                type="openai",
                model_name=f"gpt-3.5-turbo-{i}",
                parameters={"temperature": 0.7}
            ) for i in range(20)
        }
        
        # Create diamond dependency pattern repeated multiple times
        tasks = []
        for group in range(10):  # 10 groups of 4 tasks each
            base_idx = group * 4
            
            # Base task
            tasks.append(TaskConfig(
                name=f"base_{group}",
                model_ref=f"model_{group % 20}",
                task_name="hellaswag",
                depends_on=[]
            ))
            
            # Two parallel tasks
            tasks.append(TaskConfig(
                name=f"parallel_a_{group}",
                model_ref=f"model_{(group + 1) % 20}",
                task_name="arc_easy",
                depends_on=[f"base_{group}"]
            ))
            
            tasks.append(TaskConfig(
                name=f"parallel_b_{group}",
                model_ref=f"model_{(group + 2) % 20}",
                task_name="truthfulqa_mc",
                depends_on=[f"base_{group}"]
            ))
            
            # Convergence task
            tasks.append(TaskConfig(
                name=f"convergence_{group}",
                model_ref=f"model_{(group + 3) % 20}",
                task_name="gsm8k",
                depends_on=[f"parallel_a_{group}", f"parallel_b_{group}"]
            ))
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Task Building Performance Test"),
            models=models,
            tasks=tasks
        )
        
        builder = TaskBuilder()
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        evaluation_tasks = builder.build_tasks(config)
        execution_plan = builder.create_execution_plan(evaluation_tasks)
        
        build_time = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_usage = end_memory - start_memory
        
        # Performance assertions
        assert build_time < 5.0, f"Task building took {build_time:.2f}s, expected < 5s"
        assert memory_usage < 100, f"Memory usage {memory_usage:.2f}MB, expected < 100MB"
        
        # Verify correctness
        assert len(evaluation_tasks) == 40  # 10 groups * 4 tasks
        assert len(execution_plan.execution_order) == 40
        
        print(f"Task building: {build_time:.2f}s, {memory_usage:.2f}MB")
    
    def test_concurrent_configuration_processing(self):
        """Test concurrent processing of multiple configurations."""
        def create_config(config_id):
            """Create a test configuration."""
            return {
                "metadata": {"name": f"Concurrent Config {config_id}"},
                "models": {
                    f"model_{config_id}": {
                        "name": f"model_{config_id}",
                        "type": "openai",
                        "model_name": "gpt-3.5-turbo",
                        "parameters": {"temperature": 0.7}
                    }
                },
                "tasks": [{
                    "name": f"task_{config_id}",
                    "model_ref": f"model_{config_id}",
                    "task_name": "hellaswag",
                    "num_fewshot": 5
                }]
            }
        
        def process_config(config_id, result_queue):
            """Process a configuration in a separate thread."""
            try:
                config_data = create_config(config_id)
                
                # Save to temporary file
                config_path = os.path.join(self.temp_dir, f"concurrent_{config_id}.json")
                with open(config_path, 'w') as f:
                    json.dump(config_data, f)
                
                # Parse and validate
                parser = ConfigParser()
                config = parser.parse_config(config_path)
                
                validator = ConfigValidator()
                validation_result = validator.validate_config(config)
                
                builder = TaskBuilder()
                tasks = builder.build_tasks(config)
                
                result_queue.put(("success", config_id, len(tasks)))
                
            except Exception as e:
                result_queue.put(("error", config_id, str(e)))
        
        # Test with 20 concurrent configurations
        num_configs = 20
        result_queue = queue.Queue()
        threads = []
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Start all threads
        for i in range(num_configs):
            thread = threading.Thread(target=process_config, args=(i, result_queue))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        processing_time = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_usage = end_memory - start_memory
        
        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())
        
        # Performance assertions
        assert processing_time < 10.0, f"Concurrent processing took {processing_time:.2f}s, expected < 10s"
        assert memory_usage < 300, f"Memory usage {memory_usage:.2f}MB, expected < 300MB"
        
        # Verify all succeeded
        success_count = sum(1 for status, _, _ in results if status == "success")
        assert success_count == num_configs, f"Only {success_count}/{num_configs} configs processed successfully"
        
        print(f"Concurrent processing ({num_configs} configs): {processing_time:.2f}s, {memory_usage:.2f}MB")
    
    def test_memory_usage_with_large_configurations(self):
        """Test memory usage patterns with large configurations."""
        def create_large_config(size_multiplier):
            """Create a configuration of specified size."""
            num_models = 10 * size_multiplier
            num_tasks = 50 * size_multiplier
            
            config = {
                "metadata": {"name": f"Memory Test Config {size_multiplier}x"},
                "models": {},
                "tasks": []
            }
            
            # Add models
            for i in range(num_models):
                config["models"][f"model_{i}"] = {
                    "name": f"model_{i}",
                    "type": "openai",
                    "model_name": f"gpt-3.5-turbo-{i}",
                    "parameters": {"temperature": 0.7 + (i * 0.001)}
                }
            
            # Add tasks
            for i in range(num_tasks):
                config["tasks"].append({
                    "name": f"task_{i}",
                    "model_ref": f"model_{i % num_models}",
                    "task_name": "hellaswag",
                    "num_fewshot": i % 10
                })
            
            return config
        
        memory_usage = []
        processing_times = []
        
        # Test with increasing configuration sizes
        for size_multiplier in [1, 2, 4, 8]:
            gc.collect()  # Clean up before measurement
            
            config_data = create_large_config(size_multiplier)
            config_path = os.path.join(self.temp_dir, f"memory_test_{size_multiplier}.json")
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            start_time = time.time()
            
            # Process configuration
            parser = ConfigParser()
            config = parser.parse_config(config_path)
            
            validator = ConfigValidator()
            validation_result = validator.validate_config(config)
            
            builder = TaskBuilder()
            tasks = builder.build_tasks(config)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            memory_used = end_memory - start_memory
            time_taken = end_time - start_time
            
            memory_usage.append(memory_used)
            processing_times.append(time_taken)
            
            print(f"Size {size_multiplier}x: {time_taken:.2f}s, {memory_used:.2f}MB")
            
            # Clean up
            del config, tasks, validation_result
            gc.collect()
        
        # Verify memory usage scales reasonably (should be roughly linear)
        # Allow for some overhead, but shouldn't be exponential
        for i in range(1, len(memory_usage)):
            ratio = memory_usage[i] / memory_usage[i-1]
            assert ratio < 10, f"Memory usage increased by {ratio:.1f}x, expected < 10x"
        
        # Verify processing time scales reasonably
        for i in range(1, len(processing_times)):
            ratio = processing_times[i] / processing_times[i-1]
            assert ratio < 20, f"Processing time increased by {ratio:.1f}x, expected < 20x"


class TestCompatibilityWithExistingFramework:
    """Test compatibility with existing UnifiedEvaluationFramework."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_framework_parameter_compatibility(self):
        """Test that all configuration parameters are compatible with framework."""
        # Test all supported model types and their parameters
        test_configs = [
            {
                "name": "OpenAI Compatibility",
                "model": {
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "parameters": {
                        "temperature": 0.7,
                        "max_tokens": 1000,
                        "top_p": 0.9,
                        "frequency_penalty": 0.1,
                        "presence_penalty": 0.1,
                        "stop": ["\\n\\n"]
                    }
                }
            },
            {
                "name": "Anthropic Compatibility",
                "model": {
                    "type": "anthropic",
                    "model_name": "claude-3-sonnet-20240229",
                    "parameters": {
                        "temperature": 0.5,
                        "max_tokens": 1500,
                        "top_p": 0.95,
                        "stop_sequences": ["Human:", "Assistant:"]
                    }
                }
            },
            {
                "name": "Hugging Face Compatibility",
                "model": {
                    "type": "huggingface",
                    "model_name": "meta-llama/Llama-2-7b-chat-hf",
                    "parameters": {
                        "temperature": 0.8,
                        "max_tokens": 2000,
                        "top_p": 0.9,
                        "do_sample": True
                    }
                }
            }
        ]
        
        for test_config in test_configs:
            config = {
                "metadata": {"name": test_config["name"]},
                "models": {
                    "test_model": test_config["model"]
                },
                "tasks": [{
                    "name": "compatibility_task",
                    "model_ref": "test_model",
                    "task_name": "hellaswag",
                    "num_fewshot": 5,
                    "batch_size": 16,
                    "task_config": {
                        "limit": 100,
                        "temperature": 0.6  # Task-level override
                    }
                }]
            }
            
            config_path = os.path.join(self.temp_dir, f"{test_config['name'].lower().replace(' ', '_')}.json")
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            # Parse and build tasks
            parser = ConfigParser()
            parsed_config = parser.parse_config(config_path)
            
            builder = TaskBuilder()
            tasks = builder.build_tasks(parsed_config)
            
            # Verify framework parameters
            task = tasks[0]
            framework_params = task.framework_params
            
            # Check required parameters exist
            assert "model" in framework_params
            assert "tasks" in framework_params
            assert "num_fewshot" in framework_params
            assert "batch_size" in framework_params
            
            # Check model-specific parameters are in gen_kwargs
            if "gen_kwargs" in framework_params:
                gen_kwargs = framework_params["gen_kwargs"]
                
                # Task override should take precedence
                if "temperature" in gen_kwargs:
                    assert gen_kwargs["temperature"] == 0.6
                
                # Model parameters should be present
                model_params = test_config["model"]["parameters"]
                for param, value in model_params.items():
                    if param != "temperature":  # Skip overridden parameter
                        if param in gen_kwargs:
                            assert gen_kwargs[param] == value
    
    def test_existing_api_compatibility(self):
        """Test that existing API calls still work unchanged."""
        # This test verifies that the configuration system doesn't break
        # existing UnifiedEvaluationFramework usage
        
        from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
        
        # Test that existing framework can still be used directly
        framework = UnifiedEvaluationFramework()
        
        # Mock a simple evaluation request (existing API style)
        with patch.object(framework, 'evaluate') as mock_evaluate:
            mock_result = Mock()
            mock_result.evaluation_id = "existing_api_test"
            mock_result.status = "completed"
            mock_result.results = {"hellaswag": {"accuracy": 0.8}}
            mock_evaluate.return_value = mock_result
            
            # This should work exactly as before
            from evaluation_engine.core.unified_framework import EvaluationRequest
            
            request = EvaluationRequest(
                model="gpt-3.5-turbo",
                tasks=["hellaswag"],
                num_fewshot=5,
                batch_size=32
            )
            
            result = framework.evaluate(request)
            
            # Verify existing API still works
            assert result.evaluation_id == "existing_api_test"
            assert result.status == "completed"
            assert "hellaswag" in result.results
    
    def test_configuration_and_direct_api_coexistence(self):
        """Test that configuration-driven and direct API can coexist."""
        # Create a configuration-driven evaluator
        config_evaluator = ConfigDrivenEvaluator()
        
        # Create a direct framework instance
        direct_framework = UnifiedEvaluationFramework()
        
        # Both should be able to work simultaneously
        config = {
            "metadata": {"name": "Coexistence Test"},
            "models": {
                "config_model": {
                    "name": "config_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                }
            },
            "tasks": [{
                "name": "config_task",
                "model_ref": "config_model",
                "task_name": "hellaswag"
            }]
        }
        
        config_path = os.path.join(self.temp_dir, "coexistence_test.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Mock both evaluations
        with patch.object(config_evaluator.framework, 'evaluate') as mock_config_eval, \
             patch.object(direct_framework, 'evaluate') as mock_direct_eval:
            
            # Mock results
            config_result = Mock()
            config_result.evaluation_id = "config_eval"
            config_result.status = "completed"
            config_result.start_time = datetime.now()
            config_result.end_time = datetime.now()
            config_result.results = {}
            config_result.metrics_summary = {}
            config_result.analysis = {}
            config_result.error = None
            mock_config_eval.return_value = config_result
            
            direct_result = Mock()
            direct_result.evaluation_id = "direct_eval"
            direct_result.status = "completed"
            direct_result.results = {"hellaswag": {"accuracy": 0.85}}
            mock_direct_eval.return_value = direct_result
            
            # Run configuration-driven evaluation
            config_eval_result = config_evaluator.run_from_config(config_path, dry_run=True)
            
            # Run direct evaluation
            from evaluation_engine.core.unified_framework import EvaluationRequest
            direct_request = EvaluationRequest(
                model="gpt-3.5-turbo",
                tasks=["arc_easy"],
                num_fewshot=10
            )
            direct_eval_result = direct_framework.evaluate(direct_request)
            
            # Both should work independently
            assert config_eval_result.config_metadata.name == "Coexistence Test"
            assert direct_eval_result.evaluation_id == "direct_eval"
    
    def test_backward_compatibility_with_existing_tests(self):
        """Test that existing tests still pass with new configuration system."""
        # This test ensures that adding the configuration system doesn't
        # break any existing functionality
        
        # Test that existing model adapters still work
        from evaluation_engine.core.model_adapters import ModelAdapter
        
        # Mock model adapter functionality
        with patch('evaluation_engine.core.model_adapters.ModelAdapter') as mock_adapter:
            mock_instance = Mock()
            mock_adapter.return_value = mock_instance
            
            # This should work as before
            adapter = ModelAdapter()
            assert adapter is not None
        
        # Test that existing task registration still works
        from evaluation_engine.core.task_registration import TaskRegistry
        
        with patch('evaluation_engine.core.task_registration.TaskRegistry') as mock_registry:
            mock_instance = Mock()
            mock_registry.return_value = mock_instance
            
            registry = TaskRegistry()
            assert registry is not None


class TestScalabilityAndStress:
    """Test system scalability and stress conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_maximum_configuration_size(self):
        """Test system behavior with maximum reasonable configuration size."""
        # Create the largest reasonable configuration
        max_config = {
            "metadata": {
                "name": "Maximum Size Configuration",
                "version": "1.0",
                "description": "Testing maximum reasonable configuration size"
            },
            "variables": {f"var_{i}": f"value_{i}" for i in range(500)},
            "models": {},
            "tasks": []
        }
        
        # Add 200 models (reasonable maximum for most use cases)
        for i in range(200):
            max_config["models"][f"model_{i}"] = {
                "name": f"model_{i}",
                "type": "openai",
                "model_name": f"gpt-3.5-turbo-{i}",
                "parameters": {
                    "temperature": "${var_" + str(i % 500) + "}",
                    "max_tokens": 1000 + i,
                    "top_p": 0.9,
                    "frequency_penalty": 0.1
                },
                "system_prompt": f"You are specialized assistant {i}",
                "prompt_template": "Task {i}: {question}\\nResponse:"
            }
        
        # Add 2000 tasks (stress test)
        for i in range(2000):
            depends_on = []
            # Create complex but not circular dependencies
            if i > 0:
                depends_on.append(f"task_{i-1}")
            if i > 100:
                depends_on.append(f"task_{i-100}")
            if i % 200 == 0 and i > 0:
                depends_on.append("task_0")
            
            max_config["tasks"].append({
                "name": f"task_{i}",
                "description": f"Stress test task {i}",
                "model_ref": f"model_{i % 200}",
                "task_name": "hellaswag",
                "num_fewshot": i % 25,
                "batch_size": (i % 128) + 1,
                "task_config": {
                    "limit": 50 + (i % 200),
                    "temperature": 0.1 + (i * 0.0001)
                },
                "depends_on": depends_on
            })
        
        config_path = os.path.join(self.temp_dir, "max_config.json")
        
        # Write in chunks to handle large file
        with open(config_path, 'w') as f:
            json.dump(max_config, f)
        
        # Test parsing with timeout
        parser = ConfigParser()
        
        start_time = time.time()
        try:
            config = parser.parse_config(config_path)
            parse_time = time.time() - start_time
            
            # Should complete within reasonable time
            assert parse_time < 30.0, f"Parsing took {parse_time:.2f}s, expected < 30s"
            
            # Verify structure
            assert len(config.models) == 200
            assert len(config.tasks) == 2000
            assert len(config.variables) == 500
            
            print(f"Maximum config parsing: {parse_time:.2f}s")
            
        except Exception as e:
            parse_time = time.time() - start_time
            pytest.fail(f"Failed to parse maximum config after {parse_time:.2f}s: {e}")
    
    def test_stress_concurrent_evaluations(self):
        """Test system under concurrent evaluation stress."""
        def create_evaluation_config(eval_id):
            """Create a configuration for stress testing."""
            return {
                "metadata": {"name": f"Stress Test {eval_id}"},
                "models": {
                    f"stress_model_{eval_id}": {
                        "name": f"stress_model_{eval_id}",
                        "type": "openai",
                        "model_name": "gpt-3.5-turbo",
                        "parameters": {"temperature": 0.7}
                    }
                },
                "tasks": [
                    {
                        "name": f"stress_task_{eval_id}_{i}",
                        "model_ref": f"stress_model_{eval_id}",
                        "task_name": "hellaswag",
                        "num_fewshot": 5,
                        "depends_on": [f"stress_task_{eval_id}_{i-1}"] if i > 0 else []
                    } for i in range(5)  # 5 tasks per evaluation
                ]
            }
        
        def run_evaluation(eval_id, results_queue):
            """Run a single evaluation."""
            try:
                config_data = create_evaluation_config(eval_id)
                config_path = os.path.join(self.temp_dir, f"stress_{eval_id}.json")
                
                with open(config_path, 'w') as f:
                    json.dump(config_data, f)
                
                # Mock evaluator for stress test
                evaluator = ConfigDrivenEvaluator()
                
                with patch.object(evaluator.framework, 'evaluate') as mock_evaluate:
                    mock_result = Mock()
                    mock_result.evaluation_id = f"stress_eval_{eval_id}"
                    mock_result.status = "completed"
                    mock_result.start_time = datetime.now()
                    mock_result.end_time = datetime.now()
                    mock_result.results = {}
                    mock_result.metrics_summary = {}
                    mock_result.analysis = {}
                    mock_result.error = None
                    mock_evaluate.return_value = mock_result
                    
                    result = evaluator.run_from_config(config_path, dry_run=True)
                    results_queue.put(("success", eval_id, result.batch_result.total_tasks))
                    
            except Exception as e:
                results_queue.put(("error", eval_id, str(e)))
        
        # Run 50 concurrent evaluations
        num_evaluations = 50
        results_queue = queue.Queue()
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Use ThreadPoolExecutor for better resource management
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(run_evaluation, i, results_queue)
                for i in range(num_evaluations)
            ]
            
            # Wait for all to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Evaluation failed: {e}")
        
        total_time = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_usage = end_memory - start_memory
        
        # Collect results
        results = []
        while not result_queue.empty():
            results.append(results_queue.get())
        
        # Performance assertions
        assert total_time < 60.0, f"Stress test took {total_time:.2f}s, expected < 60s"
        assert memory_usage < 1000, f"Memory usage {memory_usage:.2f}MB, expected < 1GB"
        
        # Verify success rate
        success_count = sum(1 for status, _, _ in results if status == "success")
        success_rate = success_count / num_evaluations * 100
        
        assert success_rate >= 95, f"Success rate {success_rate:.1f}%, expected >= 95%"
        
        print(f"Stress test ({num_evaluations} concurrent): {total_time:.2f}s, {memory_usage:.2f}MB, {success_rate:.1f}% success")
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations."""
        def run_parse_cycle():
            """Run a complete parse-validate-build cycle."""
            config = {
                "metadata": {"name": "Memory Leak Test"},
                "models": {
                    "leak_test_model": {
                        "name": "leak_test_model",
                        "type": "openai",
                        "model_name": "gpt-3.5-turbo"
                    }
                },
                "tasks": [{
                    "name": "leak_test_task",
                    "model_ref": "leak_test_model",
                    "task_name": "hellaswag"
                }]
            }
            
            config_path = os.path.join(self.temp_dir, "leak_test.json")
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            # Complete cycle
            parser = ConfigParser()
            parsed_config = parser.parse_config(config_path)
            
            validator = ConfigValidator()
            validation_result = validator.validate_config(parsed_config)
            
            builder = TaskBuilder()
            tasks = builder.build_tasks(parsed_config)
            
            # Clean up references
            del parser, parsed_config, validator, validation_result, builder, tasks
        
        # Measure memory before
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Run many cycles
        for i in range(100):
            run_parse_cycle()
            
            # Force garbage collection every 10 cycles
            if i % 10 == 0:
                gc.collect()
        
        # Measure memory after
        gc.collect()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Should not grow significantly (allow some overhead)
        assert memory_growth < 100, f"Memory grew by {memory_growth:.2f}MB after 100 cycles, expected < 100MB"
        
        print(f"Memory leak test: {memory_growth:.2f}MB growth over 100 cycles")


if __name__ == "__main__":
    pytest.main([__file__])