"""
End-to-end integration tests for configuration-driven evaluation system.

This module provides comprehensive integration tests that verify the complete
workflow from configuration parsing to result generation.
"""

import pytest
import tempfile
import json
import yaml
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from evaluation_engine.config.parser import ConfigParser
from evaluation_engine.config.validator import ConfigValidator
from evaluation_engine.config.builder import TaskBuilder
from evaluation_engine.config.evaluator import ConfigDrivenEvaluator
from evaluation_engine.config.templates import ModelTemplateManager
from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
from evaluation_engine.config.models import (
    EvaluationConfig, ConfigMetadata, TaskConfig, ModelConfig,
    DefaultConfig, OutputConfig
)


class TestEndToEndConfigurationWorkflow:
    """Test complete end-to-end configuration workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Complete configuration for testing
        self.complete_config = {
            "metadata": {
                "name": "End-to-End Integration Test",
                "version": "1.0",
                "author": "Integration Test Suite",
                "description": "Complete configuration for integration testing"
            },
            "variables": {
                "output_dir": f"{self.temp_dir}/results",
                "model_temperature": 0.7,
                "default_batch_size": 16
            },
            "models": {
                "gpt35_turbo": {
                    "name": "gpt35_turbo",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "parameters": {
                        "temperature": "${model_temperature}",
                        "max_tokens": 1000,
                        "top_p": 0.9
                    },
                    "system_prompt": "You are a helpful assistant for evaluation tasks.",
                    "prompt_template": "Question: {question}\\nAnswer:"
                },
                "claude_sonnet": {
                    "name": "claude_sonnet",
                    "type": "anthropic",
                    "model_name": "claude-3-sonnet-20240229",
                    "parameters": {
                        "temperature": 0.5,
                        "max_tokens": 1500
                    },
                    "system_prompt": "You are Claude, an AI assistant created by Anthropic.",
                    "prompt_template": "Human: {question}\\n\\nAssistant:"
                }
            },
            "defaults": {
                "num_fewshot": 5,
                "batch_size": "${default_batch_size}",
                "output": {
                    "format": ["json", "csv"],
                    "save_predictions": True
                }
            },
            "tasks": [
                {
                    "name": "hellaswag_gpt35",
                    "description": "HellaSwag commonsense reasoning with GPT-3.5",
                    "model_ref": "gpt35_turbo",
                    "task_name": "hellaswag",
                    "num_fewshot": 10,
                    "batch_size": 8,
                    "task_config": {
                        "limit": 100
                    },
                    "depends_on": []
                },
                {
                    "name": "arc_easy_claude",
                    "description": "ARC Easy reasoning with Claude",
                    "model_ref": "claude_sonnet",
                    "task_name": "arc_easy",
                    "num_fewshot": 25,
                    "batch_size": 4,
                    "task_config": {
                        "limit": 50
                    },
                    "depends_on": []
                },
                {
                    "name": "comparison_task",
                    "description": "Comparison task that depends on previous tasks",
                    "model_ref": "gpt35_turbo",
                    "task_name": "truthfulqa_mc",
                    "num_fewshot": 0,
                    "task_config": {
                        "limit": 25
                    },
                    "depends_on": ["hellaswag_gpt35", "arc_easy_claude"]
                }
            ],
            "output": {
                "directory": "${output_dir}",
                "formats": ["json", "html", "csv"],
                "include_raw_responses": True,
                "generate_report": True,
                "compare_models": True
            }
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_complete_yaml_workflow(self):
        """Test complete workflow with YAML configuration."""
        # Create YAML config file
        config_path = os.path.join(self.temp_dir, "test_config.yaml")
        with open(config_path, 'w') as f:
            yaml.dump(self.complete_config, f)
        
        # Step 1: Parse configuration
        parser = ConfigParser()
        config = parser.parse_config(config_path)
        
        # Verify parsing
        assert config.metadata.name == "End-to-End Integration Test"
        assert len(config.models) == 2
        assert len(config.tasks) == 3
        assert config.models["gpt35_turbo"].parameters["temperature"] == "0.7"  # Variable resolved
        assert config.output.directory == f"{self.temp_dir}/results"  # Variable resolved
        
        # Step 2: Validate configuration
        validator = ConfigValidator()
        validation_result = validator.validate_config(config)
        
        # Should be valid (may have warnings about task loading)
        assert validation_result.is_valid
        
        # Step 3: Build tasks
        builder = TaskBuilder()
        evaluation_tasks = builder.build_tasks(config)
        
        # Verify task building
        assert len(evaluation_tasks) == 3
        task_names = [task.name for task in evaluation_tasks]
        assert "hellaswag_gpt35" in task_names
        assert "arc_easy_claude" in task_names
        assert "comparison_task" in task_names
        
        # Verify dependency resolution
        execution_plan = builder.create_execution_plan(evaluation_tasks)
        assert execution_plan.execution_order[0] in ["hellaswag_gpt35", "arc_easy_claude"]
        assert execution_plan.execution_order[1] in ["hellaswag_gpt35", "arc_easy_claude"]
        assert execution_plan.execution_order[2] == "comparison_task"
        
        # Step 4: Test with mock evaluator
        mock_framework = Mock(spec=UnifiedEvaluationFramework)
        
        def mock_evaluate(request):
            result = Mock()
            result.evaluation_id = f"eval_{int(time.time())}"
            result.status = "completed"
            result.start_time = datetime.now()
            result.end_time = datetime.now()
            result.results = {"test_task": {"accuracy": 0.85}}
            result.metrics_summary = {"test_task_accuracy": 0.85}
            result.analysis = {"summary": "Test completed successfully"}
            result.error = None
            return result
        
        mock_framework.evaluate.side_effect = mock_evaluate
        
        evaluator = ConfigDrivenEvaluator(framework=mock_framework)
        
        # Run evaluation (dry run to avoid actual model calls)
        result = evaluator.run_from_config(config_path, dry_run=True)
        
        # Verify results
        assert result.config_metadata.name == "End-to-End Integration Test"
        assert result.batch_result.total_tasks == 3
        assert result.batch_result.skipped_tasks == 3  # Dry run skips all tasks
        assert result.validation_result.is_valid
    
    def test_complete_json_workflow(self):
        """Test complete workflow with JSON configuration."""
        # Create JSON config file
        config_path = os.path.join(self.temp_dir, "test_config.json")
        with open(config_path, 'w') as f:
            json.dump(self.complete_config, f, indent=2)
        
        # Test the complete workflow
        evaluator = ConfigDrivenEvaluator()
        
        # Mock the framework to avoid actual model calls
        with patch.object(evaluator.framework, 'evaluate') as mock_evaluate:
            mock_result = Mock()
            mock_result.evaluation_id = "test_eval_123"
            mock_result.status = "completed"
            mock_result.start_time = datetime.now()
            mock_result.end_time = datetime.now()
            mock_result.results = {"test": {"accuracy": 0.9}}
            mock_result.metrics_summary = {"test_accuracy": 0.9}
            mock_result.analysis = {"summary": "Success"}
            mock_result.error = None
            mock_evaluate.return_value = mock_result
            
            # Run evaluation (dry run)
            result = evaluator.run_from_config(config_path, dry_run=True)
            
            # Verify complete workflow
            assert result.config_metadata.name == "End-to-End Integration Test"
            assert result.batch_result.total_tasks == 3
            assert result.validation_result.is_valid
    
    def test_workflow_with_template_inheritance(self):
        """Test workflow with template inheritance."""
        # Create base template
        base_template = {
            "metadata": {"name": "Base Template", "version": "1.0"},
            "defaults": {"num_fewshot": 5, "batch_size": 32},
            "models": {
                "base_model": {
                    "name": "base_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "parameters": {"temperature": 0.7}
                }
            }
        }
        
        # Create child configuration that extends base
        child_config = {
            "extends": "base_template.json",
            "metadata": {"name": "Child Configuration"},
            "tasks": [{
                "name": "child_task",
                "model_ref": "base_model",
                "task_name": "hellaswag"
            }]
        }
        
        # Save templates
        base_path = os.path.join(self.temp_dir, "base_template.json")
        child_path = os.path.join(self.temp_dir, "child_config.json")
        
        with open(base_path, 'w') as f:
            json.dump(base_template, f)
        
        with open(child_path, 'w') as f:
            json.dump(child_config, f)
        
        # Test workflow
        parser = ConfigParser()
        config = parser.parse_config(child_path)
        
        # Verify inheritance
        assert config.metadata.name == "Child Configuration"
        assert config.metadata.version == "1.0"  # Inherited from base
        assert config.defaults.num_fewshot == 5   # Inherited from base
        assert "base_model" in config.models      # Inherited from base
        assert len(config.tasks) == 1             # From child
        
        # Validate and build
        validator = ConfigValidator()
        validation_result = validator.validate_config(config)
        assert validation_result.is_valid
        
        builder = TaskBuilder()
        tasks = builder.build_tasks(config)
        assert len(tasks) == 1
        assert tasks[0].name == "child_task"
    
    def test_workflow_with_includes(self):
        """Test workflow with configuration includes."""
        # Create separate model definitions
        models_config = {
            "shared_model": {
                "name": "shared_model",
                "type": "openai",
                "model_name": "gpt-3.5-turbo",
                "parameters": {"temperature": 0.8}
            },
            "another_model": {
                "name": "another_model",
                "type": "anthropic",
                "model_name": "claude-3-sonnet"
            }
        }
        
        # Create main configuration with includes
        main_config = {
            "metadata": {"name": "Configuration with Includes"},
            "models": {"include": "models.json"},
            "tasks": [{
                "name": "include_test_task",
                "model_ref": "shared_model",
                "task_name": "hellaswag"
            }]
        }
        
        # Save files
        models_path = os.path.join(self.temp_dir, "models.json")
        main_path = os.path.join(self.temp_dir, "main_config.json")
        
        with open(models_path, 'w') as f:
            json.dump(models_config, f)
        
        with open(main_path, 'w') as f:
            json.dump(main_config, f)
        
        # Test workflow
        parser = ConfigParser()
        config = parser.parse_config(main_path)
        
        # Verify includes were processed
        assert "shared_model" in config.models
        assert "another_model" in config.models
        assert config.models["shared_model"].parameters["temperature"] == 0.8
        
        # Complete validation and building
        validator = ConfigValidator()
        validation_result = validator.validate_config(config)
        assert validation_result.is_valid
        
        builder = TaskBuilder()
        tasks = builder.build_tasks(config)
        assert len(tasks) == 1
        assert tasks[0].model_config.name == "shared_model"
    
    def test_workflow_with_parameter_overrides(self):
        """Test workflow with runtime parameter overrides."""
        config_path = os.path.join(self.temp_dir, "override_test.json")
        with open(config_path, 'w') as f:
            json.dump(self.complete_config, f)
        
        evaluator = ConfigDrivenEvaluator()
        
        # Define parameter overrides
        overrides = {
            "variables": {
                "model_temperature": 0.2,
                "default_batch_size": 8
            },
            "defaults": {
                "num_fewshot": 15
            },
            "tasks": {
                "hellaswag_gpt35": {
                    "batch_size": 4
                }
            },
            "output": {
                "directory": f"{self.temp_dir}/custom_output"
            }
        }
        
        with patch.object(evaluator.framework, 'evaluate') as mock_evaluate:
            mock_result = Mock()
            mock_result.evaluation_id = "override_test"
            mock_result.status = "completed"
            mock_result.start_time = datetime.now()
            mock_result.end_time = datetime.now()
            mock_result.results = {}
            mock_result.metrics_summary = {}
            mock_result.analysis = {}
            mock_result.error = None
            mock_evaluate.return_value = mock_result
            
            # Run with overrides (dry run)
            result = evaluator.run_from_config(
                config_path,
                dry_run=True,
                parameter_overrides=overrides
            )
            
            # Verify overrides were applied
            assert result.config_metadata.name == "End-to-End Integration Test"
            assert result.batch_result.total_tasks == 3
    
    def test_workflow_with_task_filtering(self):
        """Test workflow with task filtering."""
        config_path = os.path.join(self.temp_dir, "filter_test.json")
        with open(config_path, 'w') as f:
            json.dump(self.complete_config, f)
        
        evaluator = ConfigDrivenEvaluator()
        
        with patch.object(evaluator.framework, 'evaluate') as mock_evaluate:
            mock_result = Mock()
            mock_result.evaluation_id = "filter_test"
            mock_result.status = "completed"
            mock_result.start_time = datetime.now()
            mock_result.end_time = datetime.now()
            mock_result.results = {}
            mock_result.metrics_summary = {}
            mock_result.analysis = {}
            mock_result.error = None
            mock_evaluate.return_value = mock_result
            
            # Run with task filter
            result = evaluator.run_from_config(
                config_path,
                dry_run=True,
                task_filter=["hellaswag_gpt35", "arc_easy_claude"]
            )
            
            # Should only execute filtered tasks
            assert result.batch_result.total_tasks == 2  # Filtered to 2 tasks
    
    def test_workflow_error_recovery(self):
        """Test workflow error recovery and handling."""
        config_path = os.path.join(self.temp_dir, "error_test.json")
        with open(config_path, 'w') as f:
            json.dump(self.complete_config, f)
        
        evaluator = ConfigDrivenEvaluator()
        
        # Mock framework that fails on specific tasks
        def mock_evaluate_with_failures(request):
            # Fail on arc_easy task
            if "arc_easy" in str(request.tasks):
                result = Mock()
                result.status = "failed"
                result.error = "Simulated task failure"
                result.start_time = datetime.now()
                result.end_time = datetime.now()
                return result
            else:
                result = Mock()
                result.status = "completed"
                result.start_time = datetime.now()
                result.end_time = datetime.now()
                result.results = {"test": {"accuracy": 0.8}}
                result.metrics_summary = {"test_accuracy": 0.8}
                result.analysis = {"summary": "Success"}
                result.error = None
                return result
        
        with patch.object(evaluator.framework, 'evaluate', side_effect=mock_evaluate_with_failures):
            # Run with fail_fast=False to continue after failures
            result = evaluator.run_from_config(
                config_path,
                fail_fast=False
            )
            
            # Should have some completed and some failed tasks
            assert result.batch_result.total_tasks == 3
            assert result.batch_result.failed_tasks > 0
            assert result.batch_result.completed_tasks > 0


class TestFrameworkIntegration:
    """Test integration with existing UnifiedEvaluationFramework."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_framework_parameter_compatibility(self):
        """Test that configuration parameters are compatible with framework."""
        config = {
            "metadata": {"name": "Framework Compatibility Test"},
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "parameters": {
                        "temperature": 0.7,
                        "max_tokens": 1000,
                        "top_p": 0.9,
                        "frequency_penalty": 0.1,
                        "presence_penalty": 0.1
                    }
                }
            },
            "tasks": [{
                "name": "compatibility_task",
                "model_ref": "test_model",
                "task_name": "hellaswag",
                "num_fewshot": 5,
                "batch_size": 16,
                "task_config": {
                    "limit": 100,
                    "temperature": 0.5,  # Task-level override
                    "max_tokens": 2000   # Task-level override
                }
            }]
        }
        
        config_path = os.path.join(self.temp_dir, "compatibility_test.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Build tasks and verify parameter conversion
        parser = ConfigParser()
        parsed_config = parser.parse_config(config_path)
        
        builder = TaskBuilder()
        tasks = builder.build_tasks(parsed_config)
        
        # Verify framework parameters
        task = tasks[0]
        framework_params = task.framework_params
        
        # Check required framework parameters
        assert "model" in framework_params
        assert "tasks" in framework_params
        assert "num_fewshot" in framework_params
        assert "batch_size" in framework_params
        assert "gen_kwargs" in framework_params
        
        # Check parameter values
        assert framework_params["model"] == "gpt-3.5-turbo"
        assert framework_params["tasks"] == ["hellaswag"]
        assert framework_params["num_fewshot"] == 5
        assert framework_params["batch_size"] == 16
        
        # Check generation parameters
        gen_kwargs = framework_params["gen_kwargs"]
        assert gen_kwargs["temperature"] == 0.5  # Task override
        assert gen_kwargs["max_tokens"] == 2000  # Task override
        assert gen_kwargs["top_p"] == 0.9        # From model
        assert gen_kwargs["frequency_penalty"] == 0.1  # From model
    
    def test_framework_request_creation(self):
        """Test creation of framework evaluation requests."""
        config = {
            "metadata": {"name": "Request Creation Test"},
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                }
            },
            "tasks": [{
                "name": "request_task",
                "model_ref": "test_model",
                "task_name": "hellaswag",
                "description": "Test task for request creation"
            }]
        }
        
        config_path = os.path.join(self.temp_dir, "request_test.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Build tasks and create requests
        parser = ConfigParser()
        parsed_config = parser.parse_config(config_path)
        
        builder = TaskBuilder()
        tasks = builder.build_tasks(parsed_config)
        
        # Convert to evaluation request
        task = tasks[0]
        request = task.to_evaluation_request()
        
        # Verify request structure
        assert hasattr(request, 'model')
        assert hasattr(request, 'tasks')
        assert hasattr(request, 'num_fewshot')
        assert hasattr(request, 'batch_size')
        
        assert request.model == "gpt-3.5-turbo"
        assert request.tasks == ["hellaswag"]
    
    def test_framework_result_handling(self):
        """Test handling of framework evaluation results."""
        config = {
            "metadata": {"name": "Result Handling Test"},
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                }
            },
            "tasks": [{
                "name": "result_task",
                "model_ref": "test_model",
                "task_name": "hellaswag"
            }]
        }
        
        config_path = os.path.join(self.temp_dir, "result_test.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Mock framework with realistic results
        mock_framework = Mock(spec=UnifiedEvaluationFramework)
        
        def mock_evaluate(request):
            result = Mock()
            result.evaluation_id = "result_test_123"
            result.status = "completed"
            result.start_time = datetime.now()
            result.end_time = datetime.now()
            result.results = {
                "hellaswag": {
                    "accuracy": 0.75,
                    "accuracy_stderr": 0.02,
                    "num_samples": 100
                }
            }
            result.metrics_summary = {
                "hellaswag_accuracy": 0.75,
                "hellaswag_accuracy_stderr": 0.02
            }
            result.analysis = {
                "summary": "Task completed successfully",
                "performance": "Good accuracy on commonsense reasoning"
            }
            result.error = None
            return result
        
        mock_framework.evaluate.side_effect = mock_evaluate
        
        # Run evaluation
        evaluator = ConfigDrivenEvaluator(framework=mock_framework)
        result = evaluator.run_from_config(config_path)
        
        # Verify result handling
        assert result.config_metadata.name == "Result Handling Test"
        assert result.batch_result.completed_tasks == 1
        assert result.batch_result.failed_tasks == 0
        assert result.batch_result.success_rate == 100.0


class TestMultiTaskDependencyExecution:
    """Test execution of tasks with complex dependencies."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_linear_dependency_execution(self):
        """Test execution of tasks with linear dependencies."""
        config = {
            "metadata": {"name": "Linear Dependencies Test"},
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                }
            },
            "tasks": [
                {
                    "name": "task_1",
                    "model_ref": "test_model",
                    "task_name": "hellaswag",
                    "depends_on": []
                },
                {
                    "name": "task_2",
                    "model_ref": "test_model",
                    "task_name": "arc_easy",
                    "depends_on": ["task_1"]
                },
                {
                    "name": "task_3",
                    "model_ref": "test_model",
                    "task_name": "truthfulqa_mc",
                    "depends_on": ["task_2"]
                }
            ]
        }
        
        config_path = os.path.join(self.temp_dir, "linear_deps.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Test dependency resolution
        parser = ConfigParser()
        parsed_config = parser.parse_config(config_path)
        
        builder = TaskBuilder()
        tasks = builder.build_tasks(parsed_config)
        execution_plan = builder.create_execution_plan(tasks)
        
        # Verify execution order
        assert execution_plan.execution_order == ["task_1", "task_2", "task_3"]
        
        # Test execution with mock framework
        execution_order = []
        
        def mock_evaluate(request):
            task_name = request.tasks[0] if request.tasks else "unknown"
            execution_order.append(task_name)
            
            result = Mock()
            result.status = "completed"
            result.start_time = datetime.now()
            result.end_time = datetime.now()
            result.results = {task_name: {"accuracy": 0.8}}
            result.metrics_summary = {f"{task_name}_accuracy": 0.8}
            result.analysis = {"summary": "Success"}
            result.error = None
            return result
        
        mock_framework = Mock(spec=UnifiedEvaluationFramework)
        mock_framework.evaluate.side_effect = mock_evaluate
        
        evaluator = ConfigDrivenEvaluator(framework=mock_framework)
        result = evaluator.run_from_config(config_path)
        
        # Verify execution order was respected
        assert execution_order == ["hellaswag", "arc_easy", "truthfulqa_mc"]
        assert result.batch_result.completed_tasks == 3
    
    def test_parallel_dependency_execution(self):
        """Test execution of tasks with parallel dependencies."""
        config = {
            "metadata": {"name": "Parallel Dependencies Test"},
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                }
            },
            "tasks": [
                {
                    "name": "base_task",
                    "model_ref": "test_model",
                    "task_name": "hellaswag",
                    "depends_on": []
                },
                {
                    "name": "parallel_1",
                    "model_ref": "test_model",
                    "task_name": "arc_easy",
                    "depends_on": ["base_task"]
                },
                {
                    "name": "parallel_2",
                    "model_ref": "test_model",
                    "task_name": "truthfulqa_mc",
                    "depends_on": ["base_task"]
                },
                {
                    "name": "final_task",
                    "model_ref": "test_model",
                    "task_name": "gsm8k",
                    "depends_on": ["parallel_1", "parallel_2"]
                }
            ]
        }
        
        config_path = os.path.join(self.temp_dir, "parallel_deps.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Test dependency resolution
        parser = ConfigParser()
        parsed_config = parser.parse_config(config_path)
        
        builder = TaskBuilder()
        tasks = builder.build_tasks(parsed_config)
        execution_plan = builder.create_execution_plan(tasks)
        
        # Verify execution order
        order = execution_plan.execution_order
        assert order[0] == "base_task"
        assert set(order[1:3]) == {"parallel_1", "parallel_2"}  # Can be in any order
        assert order[3] == "final_task"
        
        # Test parallel execution capability
        completed_tasks = set()
        
        def mock_evaluate(request):
            task_name = request.tasks[0] if request.tasks else "unknown"
            
            # Simulate execution time
            time.sleep(0.01)
            
            result = Mock()
            result.status = "completed"
            result.start_time = datetime.now()
            result.end_time = datetime.now()
            result.results = {task_name: {"accuracy": 0.8}}
            result.metrics_summary = {f"{task_name}_accuracy": 0.8}
            result.analysis = {"summary": "Success"}
            result.error = None
            return result
        
        mock_framework = Mock(spec=UnifiedEvaluationFramework)
        mock_framework.evaluate.side_effect = mock_evaluate
        
        evaluator = ConfigDrivenEvaluator(framework=mock_framework)
        result = evaluator.run_from_config(config_path)
        
        assert result.batch_result.completed_tasks == 4
        assert result.batch_result.failed_tasks == 0
    
    def test_dependency_failure_handling(self):
        """Test handling of dependency failures."""
        config = {
            "metadata": {"name": "Dependency Failure Test"},
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                }
            },
            "tasks": [
                {
                    "name": "failing_task",
                    "model_ref": "test_model",
                    "task_name": "hellaswag",
                    "depends_on": []
                },
                {
                    "name": "dependent_task",
                    "model_ref": "test_model",
                    "task_name": "arc_easy",
                    "depends_on": ["failing_task"]
                }
            ]
        }
        
        config_path = os.path.join(self.temp_dir, "dep_failure.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Mock framework that fails on first task
        def mock_evaluate_with_failure(request):
            task_name = request.tasks[0] if request.tasks else "unknown"
            
            if task_name == "hellaswag":
                result = Mock()
                result.status = "failed"
                result.error = "Simulated failure"
                result.start_time = datetime.now()
                result.end_time = datetime.now()
                return result
            else:
                result = Mock()
                result.status = "completed"
                result.start_time = datetime.now()
                result.end_time = datetime.now()
                result.results = {task_name: {"accuracy": 0.8}}
                result.metrics_summary = {f"{task_name}_accuracy": 0.8}
                result.analysis = {"summary": "Success"}
                result.error = None
                return result
        
        mock_framework = Mock(spec=UnifiedEvaluationFramework)
        mock_framework.evaluate.side_effect = mock_evaluate_with_failure
        
        evaluator = ConfigDrivenEvaluator(framework=mock_framework)
        result = evaluator.run_from_config(config_path, fail_fast=False)
        
        # First task should fail, second should be skipped due to dependency
        assert result.batch_result.failed_tasks >= 1
        assert result.batch_result.completed_tasks == 0


class TestCLIIntegrationWorkflow:
    """Test CLI integration with the complete workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cli_workflow_integration(self):
        """Test CLI commands work with the complete system."""
        from click.testing import CliRunner
        from evaluation_engine.cli.config_cli import run_command, validate_command
        
        config = {
            "metadata": {"name": "CLI Integration Test"},
            "models": {
                "test_model": {
                    "name": "test_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                }
            },
            "tasks": [{
                "name": "cli_task",
                "model_ref": "test_model",
                "task_name": "hellaswag"
            }]
        }
        
        config_path = os.path.join(self.temp_dir, "cli_test.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        runner = CliRunner()
        
        # Test validation command
        with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
            mock_evaluator = Mock()
            mock_evaluator_class.return_value = mock_evaluator
            
            mock_validation = Mock()
            mock_validation.is_valid = True
            mock_validation.errors = []
            mock_validation.warnings = []
            mock_evaluator.validate_config_file.return_value = mock_validation
            
            validate_result = runner.invoke(validate_command, [config_path])
            assert validate_result.exit_code == 0
            assert "Configuration is valid" in validate_result.output
        
        # Test run command
        with patch('evaluation_engine.cli.config_cli.ConfigDrivenEvaluator') as mock_evaluator_class:
            mock_evaluator = Mock()
            mock_evaluator_class.return_value = mock_evaluator
            
            mock_result = Mock()
            mock_result.config_metadata.name = "CLI Integration Test"
            mock_result.batch_result.total_tasks = 1
            mock_result.batch_result.completed_tasks = 1
            mock_result.batch_result.failed_tasks = 0
            mock_result.batch_result.success_rate = 100.0
            mock_evaluator.run_from_config.return_value = mock_result
            
            run_result = runner.invoke(run_command, [config_path, '--dry-run'])
            assert run_result.exit_code == 0
            assert "CLI Integration Test" in run_result.output


if __name__ == "__main__":
    pytest.main([__file__])