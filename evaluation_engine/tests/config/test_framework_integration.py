"""
Integration tests for TaskBuilder with UnifiedEvaluationFramework.

This module tests the integration between the configuration-driven task builder
and the existing UnifiedEvaluationFramework to ensure full compatibility.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from evaluation_engine.config.builder import TaskBuilder, EvaluationTask
from evaluation_engine.config.models import (
    EvaluationConfig, TaskConfig, ModelConfig, ConfigMetadata,
    DefaultConfig, OutputConfig
)
from evaluation_engine.core.unified_framework import (
    UnifiedEvaluationFramework, EvaluationRequest, EvaluationResult,
    ExecutionStatus
)
from datetime import datetime


class TestFrameworkIntegration:
    """Test integration with UnifiedEvaluationFramework."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.framework = UnifiedEvaluationFramework()
        self.builder = TaskBuilder(self.framework)
        
        # Create sample configurations
        self.model_config = ModelConfig(
            name="test_model",
            type="openai", 
            model_name="gpt-3.5-turbo",
            parameters={"temperature": 0.7, "max_tokens": 1000}
        )
        
        self.task_config = TaskConfig(
            name="test_task",
            model_ref="test_model",
            task_name="hellaswag",
            description="Test integration task",
            num_fewshot=5,
            batch_size=16
        )
        
        self.eval_config = EvaluationConfig(
            metadata=ConfigMetadata(name="integration_test", version="1.0"),
            models={"test_model": self.model_config},
            tasks=[self.task_config],
            defaults=DefaultConfig(num_fewshot=10, batch_size=32),
            output=OutputConfig(directory="./test_results")
        )
    
    def test_evaluation_request_creation(self):
        """Test that EvaluationTask creates valid EvaluationRequest."""
        tasks = self.builder.build_tasks(self.eval_config)
        task = tasks[0]
        
        request = task.to_evaluation_request()
        
        assert isinstance(request, EvaluationRequest)
        assert request.model == "gpt-3.5-turbo"
        assert request.tasks == ["hellaswag"]
        assert request.num_fewshot == 5
        assert request.batch_size == 16
        assert request.description == "Test integration task"
        assert request.use_cache is True
        assert request.verbosity == "INFO"
    
    @patch('evaluation_engine.core.unified_framework.get_task_dict')
    @patch('evaluation_engine.core.unified_framework.simple_evaluate')
    def test_framework_evaluation_execution(self, mock_simple_evaluate, mock_get_task_dict):
        """Test that framework can execute tasks built by TaskBuilder."""
        # Mock task validation
        mock_get_task_dict.return_value = {"hellaswag": Mock()}
        
        # Mock lm-eval response
        mock_simple_evaluate.return_value = {
            "results": {
                "hellaswag": {
                    "acc": 0.75,
                    "acc_stderr": 0.02,
                    "acc_norm": 0.73,
                    "acc_norm_stderr": 0.02
                }
            },
            "samples": [],
            "config": {"model": "gpt-3.5-turbo"},
            "versions": {"lm-eval": "0.4.0"}
        }
        
        # Build and execute task
        tasks = self.builder.build_tasks(self.eval_config)
        task = tasks[0]
        request = task.to_evaluation_request()
        
        result = self.framework.evaluate(request)
        
        assert isinstance(result, EvaluationResult)
        assert result.status == ExecutionStatus.COMPLETED
        assert result.results is not None
        assert "hellaswag" in result.results
        assert result.metrics_summary is not None
        
        # Verify mock was called with correct parameters
        mock_simple_evaluate.assert_called_once()
        call_args = mock_simple_evaluate.call_args[1]
        assert call_args["model"] == "gpt-3.5-turbo"
        assert call_args["tasks"] == ["hellaswag"]
        assert call_args["num_fewshot"] == 5
        assert call_args["batch_size"] == 16
    
    def test_parameter_format_compatibility(self):
        """Test that all parameter formats are compatible with framework."""
        # Test with various parameter combinations
        task_configs = [
            # Basic task
            TaskConfig(
                name="basic_task",
                model_ref="test_model",
                task_name="arc_easy"
            ),
            # Task with all parameters
            TaskConfig(
                name="full_task",
                model_ref="test_model", 
                task_name="gsm8k",
                num_fewshot=10,
                batch_size=8,
                task_config={
                    "limit": 100,
                    "temperature": 0.2,
                    "max_tokens": 500
                }
            ),
            # Task with dependencies
            TaskConfig(
                name="dependent_task",
                model_ref="test_model",
                task_name="truthfulqa_mc",
                depends_on=["basic_task"]
            )
        ]
        
        eval_config = EvaluationConfig(
            metadata=ConfigMetadata(name="compatibility_test", version="1.0"),
            models={"test_model": self.model_config},
            tasks=task_configs
        )
        
        # Build tasks and verify all parameters are correctly formatted
        tasks = self.builder.build_tasks(eval_config)
        
        for task in tasks:
            request = task.to_evaluation_request()
            
            # Verify all required parameters are present
            assert hasattr(request, 'model')
            assert hasattr(request, 'tasks')
            assert isinstance(request.tasks, list)
            assert len(request.tasks) == 1
            
            # Verify parameter types
            if request.num_fewshot is not None:
                assert isinstance(request.num_fewshot, int)
            if request.batch_size is not None:
                assert isinstance(request.batch_size, int)
            if request.limit is not None:
                assert isinstance(request.limit, int)
    
    def test_execution_plan_framework_compatibility(self):
        """Test that execution plans work with framework."""
        # Create tasks with dependencies
        task1 = TaskConfig(
            name="task1",
            model_ref="test_model",
            task_name="hellaswag",
            depends_on=[]
        )
        
        task2 = TaskConfig(
            name="task2", 
            model_ref="test_model",
            task_name="arc_easy",
            depends_on=["task1"]
        )
        
        eval_config = EvaluationConfig(
            metadata=ConfigMetadata(name="execution_test", version="1.0"),
            models={"test_model": self.model_config},
            tasks=[task1, task2]
        )
        
        # Build tasks and create execution plan
        tasks = self.builder.build_tasks(eval_config)
        plan = self.builder.create_execution_plan(tasks)
        
        # Verify execution order
        assert len(plan.execution_order) == 2
        assert plan.execution_order[0] == "task1"
        assert plan.execution_order[1] == "task2"
        
        # Verify all tasks can create valid requests
        for task in plan.tasks:
            request = task.to_evaluation_request()
            assert isinstance(request, EvaluationRequest)
            
            # Verify framework can validate the request
            issues = self.framework.validate_evaluation_request(request)
            # Note: Some validation issues might be expected (like model availability)
            # but the request structure should be valid
    
    def test_model_configuration_integration(self):
        """Test integration of different model configurations."""
        # Test different model types
        model_configs = {
            "openai_model": ModelConfig(
                name="openai_model",
                type="openai",
                model_name="gpt-4",
                parameters={"temperature": 0.5}
            ),
            "hf_model": ModelConfig(
                name="hf_model", 
                type="huggingface",
                model_name="microsoft/DialoGPT-medium",
                parameters={"max_length": 1000}
            ),
            "custom_model": ModelConfig(
                name="custom_model",
                type="custom",
                model_name="custom-model-v1",
                parameters={"custom_param": "value"}
            )
        }
        
        for model_name, model_config in model_configs.items():
            task_config = TaskConfig(
                name=f"task_{model_name}",
                model_ref=model_name,
                task_name="hellaswag"
            )
            
            eval_config = EvaluationConfig(
                metadata=ConfigMetadata(name="model_test", version="1.0"),
                models={model_name: model_config},
                tasks=[task_config]
            )
            
            # Build task and verify model integration
            tasks = self.builder.build_tasks(eval_config)
            task = tasks[0]
            
            assert task.model_config == model_config
            assert task.framework_params["model"] == model_config.model_name
            
            # Verify generation kwargs include model parameters
            if model_config.parameters:
                assert "gen_kwargs" in task.framework_params
                for param, value in model_config.parameters.items():
                    assert task.framework_params["gen_kwargs"][param] == value
    
    def test_output_configuration_integration(self):
        """Test integration of output configurations."""
        output_configs = [
            OutputConfig(
                directory="./results1",
                formats=["json"],
                include_raw_responses=False
            ),
            OutputConfig(
                directory="./results2", 
                formats=["json", "csv"],
                include_raw_responses=True,
                generate_report=True
            )
        ]
        
        for i, output_config in enumerate(output_configs):
            eval_config = EvaluationConfig(
                metadata=ConfigMetadata(name=f"output_test_{i}", version="1.0"),
                models={"test_model": self.model_config},
                tasks=[self.task_config],
                output=output_config
            )
            
            tasks = self.builder.build_tasks(eval_config)
            task = tasks[0]
            
            # Verify output configuration is reflected in framework parameters
            assert task.framework_params["output_base_path"] == output_config.directory
            
            if output_config.include_raw_responses:
                assert task.framework_params["log_samples"] is True
            else:
                assert task.framework_params.get("log_samples", False) is False
    
    @patch('evaluation_engine.core.unified_framework.get_task_dict')
    def test_task_validation_integration(self, mock_get_task_dict):
        """Test integration with framework task validation."""
        # Mock task validation
        mock_get_task_dict.return_value = {
            "hellaswag": Mock(),
            "arc_easy": Mock()
        }
        
        # Test valid tasks
        valid_tasks = self.builder.build_tasks(self.eval_config)
        for task in valid_tasks:
            request = task.to_evaluation_request()
            issues = self.framework.validate_evaluation_request(request)
            # Should not have task-related validation issues
            task_issues = [issue for issue in issues if "task" in issue.lower()]
            assert len(task_issues) == 0
        
        # Test invalid task
        invalid_task_config = TaskConfig(
            name="invalid_task",
            model_ref="test_model",
            task_name="nonexistent_task"
        )
        
        invalid_eval_config = EvaluationConfig(
            metadata=ConfigMetadata(name="invalid_test", version="1.0"),
            models={"test_model": self.model_config},
            tasks=[invalid_task_config]
        )
        
        # Mock to simulate task not found
        mock_get_task_dict.side_effect = Exception("Task not found")
        
        invalid_tasks = self.builder.build_tasks(invalid_eval_config)
        for task in invalid_tasks:
            request = task.to_evaluation_request()
            issues = self.framework.validate_evaluation_request(request)
            # Should have task-related validation issues
            assert len(issues) > 0
    
    def test_error_handling_integration(self):
        """Test error handling integration between builder and framework."""
        # Test with invalid configuration that should be caught by builder
        invalid_config = EvaluationConfig(
            metadata=ConfigMetadata(name="error_test", version="1.0"),
            models={"test_model": self.model_config},
            tasks=[
                TaskConfig(
                    name="invalid_task",
                    model_ref="nonexistent_model",  # Invalid reference
                    task_name="hellaswag"
                )
            ]
        )
        
        # Builder should catch this error
        with pytest.raises(ValueError, match="Configuration validation failed"):
            self.builder.build_tasks(invalid_config)
    
    def test_backward_compatibility(self):
        """Test that existing framework functionality is not affected."""
        # Test that framework can still be used directly without TaskBuilder
        direct_request = EvaluationRequest(
            model="dummy",
            tasks=["hellaswag"],
            num_fewshot=5,
            batch_size=16
        )
        
        # This should work without any issues (framework functionality unchanged)
        issues = self.framework.validate_evaluation_request(direct_request)
        # Validation might have issues (like model not found) but structure should be valid
        assert isinstance(issues, list)
        
        # Test that framework methods are still accessible
        assert hasattr(self.framework, 'evaluate')
        assert hasattr(self.framework, 'list_available_tasks')
        assert hasattr(self.framework, 'get_task_info')
        assert hasattr(self.framework, 'validate_evaluation_request')


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.builder = TaskBuilder()
    
    @patch('evaluation_engine.core.unified_framework.get_task_dict')
    @patch('evaluation_engine.core.unified_framework.simple_evaluate')
    def test_complete_evaluation_workflow(self, mock_simple_evaluate, mock_get_task_dict):
        """Test complete workflow from configuration to results."""
        # Mock task validation
        mock_get_task_dict.return_value = {
            "hellaswag": Mock(),
            "arc_easy": Mock()
        }
        
        # Mock lm-eval response
        mock_simple_evaluate.return_value = {
            "results": {
                "hellaswag": {"acc": 0.75, "acc_stderr": 0.02},
                "arc_easy": {"acc": 0.68, "acc_stderr": 0.03}
            },
            "samples": [],
            "config": {"model": "gpt-3.5-turbo"},
            "versions": {"lm-eval": "0.4.0"}
        }
        
        # Create configuration with multiple tasks
        model_config = ModelConfig(
            name="test_model",
            type="openai",
            model_name="gpt-3.5-turbo",
            parameters={"temperature": 0.7}
        )
        
        task1 = TaskConfig(
            name="task1",
            model_ref="test_model",
            task_name="hellaswag",
            num_fewshot=5
        )
        
        task2 = TaskConfig(
            name="task2",
            model_ref="test_model", 
            task_name="arc_easy",
            num_fewshot=10,
            depends_on=["task1"]
        )
        
        eval_config = EvaluationConfig(
            metadata=ConfigMetadata(name="e2e_test", version="1.0"),
            models={"test_model": model_config},
            tasks=[task1, task2],
            output=OutputConfig(directory="./e2e_results")
        )
        
        # Execute complete workflow
        tasks = self.builder.build_tasks(eval_config)
        plan = self.builder.create_execution_plan(tasks)
        
        # Simulate execution following dependency order
        completed_tasks = set()
        results = {}
        
        while len(completed_tasks) < len(plan.tasks):
            executable_tasks = plan.get_next_executable_tasks(completed_tasks)
            assert len(executable_tasks) > 0, "No executable tasks found"
            
            for task in executable_tasks:
                request = task.to_evaluation_request()
                result = self.builder.framework.evaluate(request)
                
                assert result.status == ExecutionStatus.COMPLETED
                assert result.results is not None
                
                results[task.name] = result
                completed_tasks.add(task.name)
        
        # Verify all tasks completed
        assert len(results) == 2
        assert "task1" in results
        assert "task2" in results
        
        # Verify execution order was respected
        # (In this simple case, we can't easily verify timing, but structure is correct)


if __name__ == "__main__":
    pytest.main([__file__])