"""
Tests for TaskBuilder module.

This module tests the task building functionality including configuration
conversion, dependency resolution, and framework integration.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from evaluation_engine.config.builder import (
    TaskBuilder, EvaluationTask, ExecutionPlan, DependencyStatus
)
from evaluation_engine.config.models import (
    EvaluationConfig, TaskConfig, ModelConfig, ConfigMetadata,
    DefaultConfig, OutputConfig, ValidationError, ValidationSeverity
)
from evaluation_engine.core.unified_framework import EvaluationRequest


class TestTaskBuilder:
    """Test cases for TaskBuilder class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_framework = Mock()
        self.builder = TaskBuilder(self.mock_framework)
        
        # Create sample configurations
        self.sample_model_config = ModelConfig(
            name="test_model",
            type="openai",
            model_name="gpt-3.5-turbo",
            parameters={"temperature": 0.7, "max_tokens": 1000}
        )
        
        self.sample_task_config = TaskConfig(
            name="test_task",
            model_ref="test_model",
            task_name="hellaswag",
            description="Test task",
            num_fewshot=5,
            batch_size=16
        )
        
        self.sample_eval_config = EvaluationConfig(
            metadata=ConfigMetadata(name="test_config", version="1.0"),
            models={"test_model": self.sample_model_config},
            tasks=[self.sample_task_config],
            defaults=DefaultConfig(num_fewshot=10, batch_size=32),
            output=OutputConfig(directory="./test_results")
        )
    
    def test_init_with_framework(self):
        """Test TaskBuilder initialization with provided framework."""
        builder = TaskBuilder(self.mock_framework)
        assert builder.framework is self.mock_framework
    
    def test_init_without_framework(self):
        """Test TaskBuilder initialization without framework creates new one."""
        builder = TaskBuilder()
        assert builder.framework is not None
    
    def test_build_tasks_success(self):
        """Test successful task building from configuration."""
        tasks = self.builder.build_tasks(self.sample_eval_config)
        
        assert len(tasks) == 1
        task = tasks[0]
        
        assert isinstance(task, EvaluationTask)
        assert task.name == "test_task"
        assert task.task_config == self.sample_task_config
        assert task.model_config == self.sample_model_config
        assert task.status == DependencyStatus.PENDING
        assert "model" in task.framework_params
        assert "tasks" in task.framework_params
        assert task.framework_params["tasks"] == ["hellaswag"]
    
    def test_build_tasks_invalid_model_reference(self):
        """Test task building with invalid model reference."""
        # Create task with invalid model reference
        invalid_task = TaskConfig(
            name="invalid_task",
            model_ref="nonexistent_model",
            task_name="hellaswag"
        )
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="test", version="1.0"),
            models={"test_model": self.sample_model_config},
            tasks=[invalid_task]
        )
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            self.builder.build_tasks(config)
    
    def test_build_tasks_duplicate_names(self):
        """Test task building with duplicate task names."""
        duplicate_task = TaskConfig(
            name="test_task",  # Same name as sample_task_config
            model_ref="test_model",
            task_name="arc_easy"
        )
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="test", version="1.0"),
            models={"test_model": self.sample_model_config},
            tasks=[self.sample_task_config, duplicate_task]
        )
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            self.builder.build_tasks(config)
    
    def test_resolve_dependencies_simple(self):
        """Test dependency resolution with simple linear dependencies."""
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=[])
        task2 = TaskConfig(name="task2", model_ref="model1", task_name="task2", depends_on=["task1"])
        task3 = TaskConfig(name="task3", model_ref="model1", task_name="task3", depends_on=["task2"])
        
        tasks = [task3, task1, task2]  # Intentionally out of order
        resolved = self.builder.resolve_dependencies(tasks)
        
        assert len(resolved) == 3
        assert resolved[0].name == "task1"
        assert resolved[1].name == "task2"
        assert resolved[2].name == "task3"
    
    def test_resolve_dependencies_complex(self):
        """Test dependency resolution with complex dependencies."""
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=[])
        task2 = TaskConfig(name="task2", model_ref="model1", task_name="task2", depends_on=[])
        task3 = TaskConfig(name="task3", model_ref="model1", task_name="task3", depends_on=["task1", "task2"])
        task4 = TaskConfig(name="task4", model_ref="model1", task_name="task4", depends_on=["task3"])
        
        tasks = [task4, task3, task1, task2]  # Out of order
        resolved = self.builder.resolve_dependencies(tasks)
        
        assert len(resolved) == 4
        # task1 and task2 can be in any order, but must come before task3
        first_two = {resolved[0].name, resolved[1].name}
        assert first_two == {"task1", "task2"}
        assert resolved[2].name == "task3"
        assert resolved[3].name == "task4"
    
    def test_resolve_dependencies_circular(self):
        """Test dependency resolution with circular dependencies."""
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=["task2"])
        task2 = TaskConfig(name="task2", model_ref="model1", task_name="task2", depends_on=["task1"])
        
        tasks = [task1, task2]
        
        with pytest.raises(ValueError, match="Circular dependencies detected"):
            self.builder.resolve_dependencies(tasks)
    
    def test_resolve_dependencies_missing_dependency(self):
        """Test dependency resolution with missing dependency."""
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=["nonexistent"])
        
        tasks = [task1]
        
        with pytest.raises(ValueError, match="depends on unknown task"):
            self.builder.resolve_dependencies(tasks)
    
    def test_create_execution_plan(self):
        """Test execution plan creation."""
        # Create evaluation tasks with dependencies
        task1 = EvaluationTask(
            name="task1",
            task_config=TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=[]),
            model_config=self.sample_model_config,
            framework_params={"model": "test", "tasks": ["task1"]}
        )
        
        task2 = EvaluationTask(
            name="task2",
            task_config=TaskConfig(name="task2", model_ref="model1", task_name="task2", depends_on=["task1"]),
            model_config=self.sample_model_config,
            framework_params={"model": "test", "tasks": ["task2"]},
            dependencies=["task1"]
        )
        
        tasks = [task2, task1]  # Out of order
        plan = self.builder.create_execution_plan(tasks)
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.tasks) == 2
        assert plan.execution_order == ["task1", "task2"]
        assert plan.dependency_graph == {"task1": [], "task2": ["task1"]}
        
        # Check that all tasks are marked as resolved
        for task in plan.tasks:
            assert task.status == DependencyStatus.RESOLVED
    
    def test_convert_to_framework_format_basic(self):
        """Test basic configuration conversion to framework format."""
        params = self.builder.convert_to_framework_format(
            self.sample_task_config,
            self.sample_model_config,
            self.sample_eval_config
        )
        
        assert params["model"] == "gpt-3.5-turbo"
        assert params["tasks"] == ["hellaswag"]
        assert params["num_fewshot"] == 5  # From task config
        assert params["batch_size"] == 16  # From task config
        assert params["description"] == "Test task"
        assert params["use_cache"] is True
        assert params["verbosity"] == "INFO"
    
    def test_convert_to_framework_format_with_defaults(self):
        """Test configuration conversion using default values."""
        # Create task without specific values
        task_config = TaskConfig(
            name="test_task",
            model_ref="test_model",
            task_name="hellaswag"
        )
        
        params = self.builder.convert_to_framework_format(
            task_config,
            self.sample_model_config,
            self.sample_eval_config
        )
        
        assert params["num_fewshot"] == 10  # From defaults
        assert params["batch_size"] == 32  # From defaults
    
    def test_convert_to_framework_format_with_task_config(self):
        """Test configuration conversion with task-specific configuration."""
        task_config = TaskConfig(
            name="test_task",
            model_ref="test_model",
            task_name="hellaswag",
            task_config={
                "limit": 1000,
                "temperature": 0.2,
                "max_tokens": 500
            }
        )
        
        params = self.builder.convert_to_framework_format(
            task_config,
            self.sample_model_config,
            self.sample_eval_config
        )
        
        assert params["limit"] == 1000
        assert "gen_kwargs" in params
        assert params["gen_kwargs"]["temperature"] == 0.2
        assert params["gen_kwargs"]["max_tokens"] == 500
    
    def test_convert_to_framework_format_with_model_params(self):
        """Test configuration conversion with model parameters."""
        params = self.builder.convert_to_framework_format(
            self.sample_task_config,
            self.sample_model_config,
            self.sample_eval_config
        )
        
        assert "gen_kwargs" in params
        assert params["gen_kwargs"]["temperature"] == 0.7
        assert params["gen_kwargs"]["max_tokens"] == 1000
    
    def test_convert_to_framework_format_with_output_config(self):
        """Test configuration conversion with output configuration."""
        params = self.builder.convert_to_framework_format(
            self.sample_task_config,
            self.sample_model_config,
            self.sample_eval_config
        )
        
        assert params["output_base_path"] == "./test_results"
        
        # Test with raw responses enabled
        output_config = OutputConfig(
            directory="./results",
            include_raw_responses=True
        )
        
        eval_config = EvaluationConfig(
            metadata=ConfigMetadata(name="test", version="1.0"),
            models={"test_model": self.sample_model_config},
            tasks=[self.sample_task_config],
            output=output_config
        )
        
        params = self.builder.convert_to_framework_format(
            self.sample_task_config,
            self.sample_model_config,
            eval_config
        )
        
        assert params["log_samples"] is True
    
    def test_build_model_identifier(self):
        """Test model identifier building."""
        identifier = self.builder._build_model_identifier(self.sample_model_config)
        assert identifier == "gpt-3.5-turbo"
    
    def test_validate_task_dependencies_valid(self):
        """Test task dependency validation with valid dependencies."""
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=[])
        task2 = TaskConfig(name="task2", model_ref="model1", task_name="task2", depends_on=["task1"])
        
        is_valid, errors = self.builder.validate_task_dependencies([task1, task2])
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_task_dependencies_missing(self):
        """Test task dependency validation with missing dependencies."""
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=["nonexistent"])
        
        is_valid, errors = self.builder.validate_task_dependencies([task1])
        
        assert is_valid is False
        assert len(errors) == 1
        assert "depends on unknown task" in errors[0]
    
    def test_validate_task_dependencies_circular(self):
        """Test task dependency validation with circular dependencies."""
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=["task2"])
        task2 = TaskConfig(name="task2", model_ref="model1", task_name="task2", depends_on=["task1"])
        
        is_valid, errors = self.builder.validate_task_dependencies([task1, task2])
        
        assert is_valid is False
        assert len(errors) == 1
        assert "Circular dependencies" in errors[0]


class TestEvaluationTask:
    """Test cases for EvaluationTask class."""
    
    def test_to_evaluation_request(self):
        """Test conversion to EvaluationRequest."""
        framework_params = {
            "model": "gpt-3.5-turbo",
            "tasks": ["hellaswag"],
            "num_fewshot": 5,
            "batch_size": 16
        }
        
        task = EvaluationTask(
            name="test_task",
            task_config=Mock(),
            model_config=Mock(),
            framework_params=framework_params
        )
        
        request = task.to_evaluation_request()
        
        assert isinstance(request, EvaluationRequest)
        assert request.model == "gpt-3.5-turbo"
        assert request.tasks == ["hellaswag"]
        assert request.num_fewshot == 5
        assert request.batch_size == 16


class TestExecutionPlan:
    """Test cases for ExecutionPlan class."""
    
    def test_get_next_executable_tasks_empty(self):
        """Test getting next executable tasks with no completed tasks."""
        task1 = EvaluationTask(
            name="task1",
            task_config=Mock(),
            model_config=Mock(),
            framework_params={},
            dependencies=[],
            status=DependencyStatus.RESOLVED
        )
        
        task2 = EvaluationTask(
            name="task2",
            task_config=Mock(),
            model_config=Mock(),
            framework_params={},
            dependencies=["task1"],
            status=DependencyStatus.RESOLVED
        )
        
        plan = ExecutionPlan(
            tasks=[task1, task2],
            execution_order=["task1", "task2"],
            dependency_graph={"task1": [], "task2": ["task1"]}
        )
        
        executable = plan.get_next_executable_tasks(set())
        
        assert len(executable) == 1
        assert executable[0].name == "task1"
    
    def test_get_next_executable_tasks_with_completed(self):
        """Test getting next executable tasks with some completed."""
        task1 = EvaluationTask(
            name="task1",
            task_config=Mock(),
            model_config=Mock(),
            framework_params={},
            dependencies=[],
            status=DependencyStatus.RESOLVED
        )
        
        task2 = EvaluationTask(
            name="task2",
            task_config=Mock(),
            model_config=Mock(),
            framework_params={},
            dependencies=["task1"],
            status=DependencyStatus.RESOLVED
        )
        
        plan = ExecutionPlan(
            tasks=[task1, task2],
            execution_order=["task1", "task2"],
            dependency_graph={"task1": [], "task2": ["task1"]}
        )
        
        executable = plan.get_next_executable_tasks({"task1"})
        
        assert len(executable) == 1
        assert executable[0].name == "task2"
    
    def test_get_next_executable_tasks_all_completed(self):
        """Test getting next executable tasks with all completed."""
        task1 = EvaluationTask(
            name="task1",
            task_config=Mock(),
            model_config=Mock(),
            framework_params={},
            dependencies=[],
            status=DependencyStatus.RESOLVED
        )
        
        plan = ExecutionPlan(
            tasks=[task1],
            execution_order=["task1"],
            dependency_graph={"task1": []}
        )
        
        executable = plan.get_next_executable_tasks({"task1"})
        
        assert len(executable) == 0


class TestDependencyManagement:
    """Additional tests for dependency management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.builder = TaskBuilder()
    
    def test_complex_dependency_graph(self):
        """Test complex dependency graph with multiple levels."""
        # Create a diamond dependency pattern
        task_a = TaskConfig(name="task_a", model_ref="model1", task_name="task_a", depends_on=[])
        task_b = TaskConfig(name="task_b", model_ref="model1", task_name="task_b", depends_on=["task_a"])
        task_c = TaskConfig(name="task_c", model_ref="model1", task_name="task_c", depends_on=["task_a"])
        task_d = TaskConfig(name="task_d", model_ref="model1", task_name="task_d", depends_on=["task_b", "task_c"])
        
        tasks = [task_d, task_c, task_b, task_a]  # Intentionally scrambled
        resolved = self.builder.resolve_dependencies(tasks)
        
        # task_a should be first
        assert resolved[0].name == "task_a"
        
        # task_b and task_c should be next (in any order)
        middle_tasks = {resolved[1].name, resolved[2].name}
        assert middle_tasks == {"task_b", "task_c"}
        
        # task_d should be last
        assert resolved[3].name == "task_d"
    
    def test_execution_plan_with_parallel_tasks(self):
        """Test execution plan generation with tasks that can run in parallel."""
        # Create tasks where some can run in parallel
        task1 = EvaluationTask(
            name="task1",
            task_config=TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=[]),
            model_config=Mock(),
            framework_params={"model": "test", "tasks": ["task1"]}
        )
        
        task2 = EvaluationTask(
            name="task2", 
            task_config=TaskConfig(name="task2", model_ref="model1", task_name="task2", depends_on=[]),
            model_config=Mock(),
            framework_params={"model": "test", "tasks": ["task2"]}
        )
        
        task3 = EvaluationTask(
            name="task3",
            task_config=TaskConfig(name="task3", model_ref="model1", task_name="task3", depends_on=["task1", "task2"]),
            model_config=Mock(),
            framework_params={"model": "test", "tasks": ["task3"]},
            dependencies=["task1", "task2"]
        )
        
        tasks = [task3, task1, task2]
        plan = self.builder.create_execution_plan(tasks)
        
        # Initially, task1 and task2 can run
        executable = plan.get_next_executable_tasks(set())
        executable_names = {task.name for task in executable}
        assert executable_names == {"task1", "task2"}
        
        # After task1 completes, task2 should still be available
        executable = plan.get_next_executable_tasks({"task1"})
        executable_names = {task.name for task in executable}
        assert executable_names == {"task2"}
        
        # After both complete, task3 should be available
        executable = plan.get_next_executable_tasks({"task1", "task2"})
        executable_names = {task.name for task in executable}
        assert executable_names == {"task3"}
    
    def test_self_dependency_detection(self):
        """Test detection of self-dependencies."""
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=["task1"])
        
        with pytest.raises(ValueError, match="Circular dependencies detected"):
            self.builder.resolve_dependencies([task1])
    
    def test_three_way_circular_dependency(self):
        """Test detection of three-way circular dependencies."""
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=["task3"])
        task2 = TaskConfig(name="task2", model_ref="model1", task_name="task2", depends_on=["task1"])
        task3 = TaskConfig(name="task3", model_ref="model1", task_name="task3", depends_on=["task2"])
        
        with pytest.raises(ValueError, match="Circular dependencies detected"):
            self.builder.resolve_dependencies([task1, task2, task3])
    
    def test_dependency_validation_comprehensive(self):
        """Test comprehensive dependency validation."""
        # Valid complex dependency structure
        task1 = TaskConfig(name="base", model_ref="model1", task_name="base", depends_on=[])
        task2 = TaskConfig(name="level1_a", model_ref="model1", task_name="level1_a", depends_on=["base"])
        task3 = TaskConfig(name="level1_b", model_ref="model1", task_name="level1_b", depends_on=["base"])
        task4 = TaskConfig(name="level2", model_ref="model1", task_name="level2", depends_on=["level1_a", "level1_b"])
        
        is_valid, errors = self.builder.validate_task_dependencies([task1, task2, task3, task4])
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid - missing dependency
        task5 = TaskConfig(name="invalid", model_ref="model1", task_name="invalid", depends_on=["nonexistent"])
        
        is_valid, errors = self.builder.validate_task_dependencies([task1, task2, task3, task4, task5])
        assert is_valid is False
        assert len(errors) == 1
        assert "depends on unknown task 'nonexistent'" in errors[0]


if __name__ == "__main__":
    pytest.main([__file__])