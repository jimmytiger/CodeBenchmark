"""
Tests for configuration validator.

This module contains comprehensive tests for the ConfigValidator class,
covering basic validation, model reference checks, and lm-eval task validation.
"""

import pytest
from unittest.mock import patch, MagicMock

from evaluation_engine.config.validator import ConfigValidator
from evaluation_engine.config.models import (
    EvaluationConfig,
    TaskConfig,
    ModelConfig,
    ConfigMetadata,
    DefaultConfig,
    OutputConfig,
    ValidationResult,
    ValidationError,
    ValidationSeverity
)


class TestConfigValidator:
    """Test cases for ConfigValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
        
        # Create a valid configuration for testing
        self.valid_config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test Config", version="1.0"),
            tasks=[
                TaskConfig(
                    name="test_task",
                    model_ref="test_model",
                    task_name="hellaswag",
                    num_fewshot=5,
                    batch_size=32
                )
            ],
            models={
                "test_model": ModelConfig(
                    name="test_model",
                    type="openai",
                    model_name="gpt-3.5-turbo",
                    parameters={"temperature": 0.7}
                )
            }
        )
    
    def test_validate_valid_config(self):
        """Test validation of a completely valid configuration."""
        result = self.validator.validate_config(self.valid_config)
        
        assert result.is_valid
        assert len(result.errors) == 0
        # May have warnings about task loading, which is acceptable
        # as long as there are no errors
    
    def test_validate_missing_metadata(self):
        """Test validation fails when metadata is missing."""
        config = EvaluationConfig(
            metadata=None,
            tasks=[TaskConfig(name="test", model_ref="model", task_name="hellaswag")],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("metadata is required" in error.message for error in result.errors)
    
    def test_validate_missing_metadata_name(self):
        """Test validation fails when metadata name is missing."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="model", task_name="hellaswag")],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("name is required" in error.message for error in result.errors)
    
    def test_validate_empty_tasks(self):
        """Test validation fails when no tasks are defined."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[],
            models={}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("At least one task must be defined" in error.message for error in result.errors)
    
    def test_validate_duplicate_task_names(self):
        """Test validation fails when duplicate task names exist."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(name="duplicate", model_ref="model", task_name="hellaswag"),
                TaskConfig(name="duplicate", model_ref="model", task_name="arc_easy")
            ],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("Duplicate task name" in error.message for error in result.errors)
    
    def test_validate_task_missing_required_fields(self):
        """Test validation of tasks with missing required fields."""
        # We need to bypass the __post_init__ validation to test the validator
        # Create tasks with invalid data directly
        task = TaskConfig.__new__(TaskConfig)
        task.name = ""
        task.model_ref = ""
        task.task_name = ""
        task.description = None
        task.task_config = None
        task.num_fewshot = None
        task.batch_size = None
        task.depends_on = []
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[task],
            models={}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        assert any("Task name is required" in msg for msg in error_messages)
        assert any("Model reference is required" in msg for msg in error_messages)
        assert any("Task name (lm-eval task) is required" in msg for msg in error_messages)
    
    def test_validate_task_invalid_numeric_parameters(self):
        """Test validation of tasks with invalid numeric parameters."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(
                    name="test",
                    model_ref="model",
                    task_name="hellaswag",
                    num_fewshot=-1,
                    batch_size=0
                )
            ],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        assert any("num_fewshot must be non-negative" in msg for msg in error_messages)
        assert any("batch_size must be positive" in msg for msg in error_messages)
    
    def test_validate_model_reference_integrity(self):
        """Test validation of model reference integrity."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(name="test", model_ref="nonexistent_model", task_name="hellaswag")
            ],
            models={"existing_model": ModelConfig(name="existing_model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("Model reference 'nonexistent_model' not found" in error.message for error in result.errors)
    
    def test_validate_unsupported_model_type(self):
        """Test validation fails for unsupported model types."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="model", task_name="hellaswag")],
            models={
                "model": ModelConfig(
                    name="model",
                    type="unsupported_type",
                    model_name="some-model"
                )
            }
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("Unsupported model type: unsupported_type" in error.message for error in result.errors)
    
    def test_validate_openai_model_parameters(self):
        """Test validation of OpenAI model parameters."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="model", task_name="hellaswag")],
            models={
                "model": ModelConfig(
                    name="model",
                    type="openai",
                    model_name="gpt-3.5-turbo",
                    parameters={"temperature": 3.0}  # Invalid temperature
                )
            }
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("temperature must be between 0 and 2" in error.message for error in result.errors)
    
    def test_validate_huggingface_model_name_format(self):
        """Test validation of Hugging Face model name format."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="model", task_name="hellaswag")],
            models={
                "model": ModelConfig(
                    name="model",
                    type="huggingface",
                    model_name="invalid-format"  # Should be "org/model"
                )
            }
        )
        
        result = self.validator.validate_config(config)
        
        # This should generate a warning, not an error
        assert result.is_valid  # Still valid, just a warning
        assert any("should be in format 'organization/model-name'" in warning.message for warning in result.warnings)
    
    @patch('lm_eval.api.registry.ALL_TASKS', {"hellaswag", "arc_easy", "truthfulqa_mc"})
    @patch('lm_eval.tasks.TaskManager')
    def test_validate_lm_eval_tasks_valid(self, mock_task_manager):
        """Test validation of valid lm-eval tasks."""
        # Mock the task registry and task manager
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="model", task_name="hellaswag")],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_lm_eval_tasks_invalid_fallback(self):
        """Test validation of invalid lm-eval tasks using fallback list."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="model", task_name="nonexistent_task")],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("Unknown lm-eval task: nonexistent_task" in error.message for error in result.errors)
    
    def test_validate_task_dependencies_missing(self):
        """Test validation of missing task dependencies."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(
                    name="test",
                    model_ref="model",
                    task_name="hellaswag",
                    depends_on=["nonexistent_task"]
                )
            ],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("Task dependency 'nonexistent_task' not found" in error.message for error in result.errors)
    
    def test_validate_circular_dependencies(self):
        """Test detection of circular task dependencies."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(name="task1", model_ref="model", task_name="hellaswag", depends_on=["task2"]),
                TaskConfig(name="task2", model_ref="model", task_name="arc_easy", depends_on=["task1"])
            ],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("Circular dependency detected" in error.message for error in result.errors)
    
    def test_validate_output_config_invalid_format(self):
        """Test validation of invalid output formats."""
        # Create output config with invalid format directly to bypass __post_init__
        output = OutputConfig.__new__(OutputConfig)
        output.directory = "./results"
        output.formats = ["invalid_format"]
        output.include_raw_responses = False
        output.generate_report = True
        output.compare_models = False
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="model", task_name="hellaswag")],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")},
            output=output
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("Unsupported output format: invalid_format" in error.message for error in result.errors)
    
    def test_validate_task_config_parameters(self):
        """Test validation of task-specific configuration parameters."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(
                    name="test",
                    model_ref="model",
                    task_name="hellaswag",
                    task_config={
                        "limit": -1,  # Invalid limit
                        "temperature": -0.5  # Invalid temperature
                    }
                )
            ],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        assert any("Task limit must be a positive integer" in msg for msg in error_messages)
        assert any("Task temperature must be a non-negative number" in msg for msg in error_messages)
    
    def test_check_model_availability(self):
        """Test model availability checking."""
        # Create invalid model directly to bypass __post_init__
        invalid_model = ModelConfig.__new__(ModelConfig)
        invalid_model.name = "invalid_model"
        invalid_model.type = "unsupported"
        invalid_model.model_name = ""
        invalid_model.parameters = {}
        invalid_model.prompt_template = None
        invalid_model.system_prompt = None
        
        models = {
            "valid_model": ModelConfig(name="valid_model", type="openai", model_name="gpt-3.5-turbo"),
            "invalid_model": invalid_model
        }
        
        # Should return False because one model is invalid
        assert not self.validator.check_model_availability(models)
        
        # Should return True for valid models only
        valid_models = {"valid_model": models["valid_model"]}
        assert self.validator.check_model_availability(valid_models)
    
    def test_check_lm_eval_tasks(self):
        """Test lm-eval task checking."""
        # Valid tasks (using fallback list)
        valid_tasks = ["hellaswag", "arc_easy", "truthfulqa_mc"]
        assert self.validator.check_lm_eval_tasks(valid_tasks)
        
        # Invalid tasks
        invalid_tasks = ["hellaswag", "nonexistent_task"]
        assert not self.validator.check_lm_eval_tasks(invalid_tasks)
    
    def test_get_invalid_lm_eval_tasks(self):
        """Test getting invalid lm-eval tasks."""
        task_names = ["hellaswag", "nonexistent_task", "arc_easy", "another_invalid"]
        invalid_tasks = self.validator.get_invalid_lm_eval_tasks(task_names)
        
        assert "nonexistent_task" in invalid_tasks
        assert "another_invalid" in invalid_tasks
        assert "hellaswag" not in invalid_tasks
        assert "arc_easy" not in invalid_tasks
    
    def test_get_task_suggestions(self):
        """Test getting task suggestions for invalid task names."""
        # Test substring matching
        suggestions = self.validator.get_task_suggestions("hella")
        assert any("hellaswag" in suggestion for suggestion in suggestions)
        
        # Test partial matching
        suggestions = self.validator.get_task_suggestions("arc")
        assert any("arc_easy" in suggestion or "arc_challenge" in suggestion for suggestion in suggestions)
        
        # Test no matches
        suggestions = self.validator.get_task_suggestions("completely_nonexistent_xyz")
        # Should return empty list or very few suggestions
        assert len(suggestions) <= 5
    
    def test_validate_task_specific_config_parameters(self):
        """Test validation of task-specific configuration parameters."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(
                    name="humaneval_test",
                    model_ref="model",
                    task_name="humaneval",
                    task_config={
                        "temperature": 0.7,
                        "max_tokens": 1024,
                        "limit": 100,
                        "invalid_param": "should_warn"
                    }
                )
            ],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        # Should have warning about invalid parameter
        assert any("Unknown parameter 'invalid_param'" in warning.message for warning in result.warnings)
    
    def test_validate_task_parameter_constraints(self):
        """Test validation of task parameter constraints."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(
                    name="gsm8k_test",
                    model_ref="model",
                    task_name="gsm8k",
                    task_config={
                        "temperature": 3.0,  # Too high
                        "max_tokens": -1,    # Invalid
                        "limit": 0           # Invalid
                    }
                )
            ],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        # Should have errors for invalid parameter values
        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        
        # Check for specific validation errors
        assert any("temperature" in msg and "must be <=" in msg for msg in error_messages)
        assert any("max_tokens" in msg and "must be >=" in msg for msg in error_messages)
        assert any("limit" in msg and ("must be positive" in msg or "must be >=" in msg) for msg in error_messages)
    
    def test_lm_eval_task_loading_validation(self):
        """Test validation of lm-eval task loading capability."""
        # Test with a task that should exist but might not load due to dependencies
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(
                    name="function_gen_test",
                    model_ref="model",
                    task_name="function_generation"
                )
            ],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        # Should be valid even if task can't load due to dependencies
        # (we only warn about loading issues, don't fail validation)
        assert result.is_valid
    
    def test_get_task_info(self):
        """Test getting detailed task information."""
        # Test with a known task
        task_info = self.validator.get_task_info("hellaswag")
        
        if task_info:
            assert task_info["name"] == "hellaswag"
            assert task_info["exists"] is True
            assert "can_load" in task_info
            assert "is_group" in task_info
            assert "is_tag" in task_info
            assert "is_subtask" in task_info
        
        # Test with non-existent task
        task_info = self.validator.get_task_info("nonexistent_task_xyz")
        assert task_info is None or task_info["exists"] is False
    
    def test_pattern_based_task_validation(self):
        """Test validation of tasks that follow naming patterns."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(
                    name="single_turn_test",
                    model_ref="model",
                    task_name="single_turn_scenarios_algorithm_design",
                    task_config={
                        "temperature": 0.7,
                        "max_tokens": 2048,
                        "limit": 100
                    }
                ),
                TaskConfig(
                    name="multi_turn_test",
                    model_ref="model",
                    task_name="multi_turn_coding_eval_openai",
                    task_config={
                        "temperature": 0.5,
                        "max_tokens": 4096,
                        "max_turns": 5,
                        "limit": 50
                    }
                )
            ],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        # Should be valid - pattern-based validation should work
        # May have warnings about task loading, but no errors for valid parameters
        error_messages = [error.message for error in result.errors if "parameter" in error.message.lower()]
        assert len(error_messages) == 0  # No parameter validation errors
    
    def test_enhanced_task_suggestions(self):
        """Test enhanced task suggestion functionality."""
        # Test suggestions for partial matches
        suggestions = self.validator.get_task_suggestions("single_turn")
        assert len(suggestions) > 0
        assert any("single_turn" in suggestion for suggestion in suggestions)
        
        # Test suggestions for coding tasks
        suggestions = self.validator.get_task_suggestions("coding")
        assert len(suggestions) > 0
        assert any("coding" in suggestion for suggestion in suggestions)
        
        # Test suggestions for math tasks
        suggestions = self.validator.get_task_suggestions("math")
        if suggestions:  # Only test if math tasks are available
            assert any("math" in suggestion for suggestion in suggestions)
    
    def test_comprehensive_lm_eval_integration(self):
        """Test comprehensive lm-eval integration with real tasks."""
        # Get available tasks
        available_tasks = self.validator._get_lm_eval_tasks()
        
        # Should have a reasonable number of tasks
        assert len(available_tasks) > 50  # Should have many more than fallback
        
        # Should include standard tasks
        standard_tasks = ["hellaswag", "arc_easy", "truthfulqa_mc"]
        for task in standard_tasks:
            assert task in available_tasks, f"Standard task {task} not found in available tasks"
        
        # Should include custom tasks
        custom_tasks = ["python_coding", "multi_turn_coding"]
        for task in custom_tasks:
            if task in available_tasks:
                # If custom task exists, test it
                task_info = self.validator.get_task_info(task)
                assert task_info is not None
                assert task_info["exists"] is True
    
    def test_check_model_references(self):
        """Test model reference checking."""
        tasks = [
            TaskConfig(name="task1", model_ref="model1", task_name="hellaswag"),
            TaskConfig(name="task2", model_ref="model2", task_name="arc_easy")
        ]
        
        models = {
            "model1": ModelConfig(name="model1", type="openai", model_name="gpt-3.5-turbo"),
            "model2": ModelConfig(name="model2", type="anthropic", model_name="claude-3-sonnet-20240229")
        }
        
        # All references exist
        assert self.validator.check_model_references(tasks, models)
        
        # Missing reference
        incomplete_models = {"model1": models["model1"]}
        assert not self.validator.check_model_references(tasks, incomplete_models)
    
    def test_validate_empty_model_reference(self):
        """Test validation of empty model references."""
        # Create task with empty model_ref directly to bypass __post_init__
        task = TaskConfig.__new__(TaskConfig)
        task.name = "test_task"
        task.model_ref = ""
        task.task_name = "hellaswag"
        task.description = None
        task.task_config = None
        task.num_fewshot = None
        task.batch_size = None
        task.depends_on = []
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[task],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("model reference cannot be empty" in error.message.lower() for error in result.errors)
    
    def test_validate_model_with_empty_fields(self):
        """Test validation of models with empty required fields."""
        # Create model with empty fields directly to bypass __post_init__
        model = ModelConfig.__new__(ModelConfig)
        model.name = ""
        model.type = ""
        model.model_name = ""
        model.parameters = {}
        model.prompt_template = None
        model.system_prompt = None
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="empty_model", task_name="hellaswag")],
            models={"empty_model": model}
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        assert any("Model name cannot be empty" in msg for msg in error_messages)
        assert any("Model type cannot be empty" in msg for msg in error_messages)
        assert any("Model model_name cannot be empty" in msg for msg in error_messages)
    
    def test_validate_task_model_compatibility(self):
        """Test validation of task-model compatibility."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[
                TaskConfig(
                    name="code_task",
                    model_ref="anthropic_model",
                    task_name="humaneval",  # Code generation task
                    task_config={"temperature": 0.8}
                )
            ],
            models={
                "anthropic_model": ModelConfig(
                    name="anthropic_model",
                    type="anthropic",
                    model_name="claude-3-sonnet-20240229",
                    parameters={"temperature": 0.2}  # Different temperature
                )
            }
        )
        
        result = self.validator.validate_config(config)
        
        # Should be valid but with warnings
        assert result.is_valid
        warning_messages = [warning.message for warning in result.warnings]
        assert any("code generation task" in msg for msg in warning_messages)
        assert any("temperature" in msg and "differs" in msg for msg in warning_messages)
    
    def test_validate_no_models_defined(self):
        """Test validation when no models are defined but tasks reference models."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="some_model", task_name="hellaswag")],
            models={}  # No models defined
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        assert any("No models defined but tasks reference models" in error.message for error in result.errors)
    
    def test_validate_prompt_templates(self):
        """Test prompt template validation."""
        models_with_valid_templates = {
            "model1": ModelConfig(
                name="model1",
                type="openai",
                model_name="gpt-3.5-turbo",
                prompt_template="Question: {question}\nAnswer:"
            )
        }
        
        models_with_invalid_templates = {
            "model1": ModelConfig(
                name="model1",
                type="openai",
                model_name="gpt-3.5-turbo",
                prompt_template="Question: {question\nAnswer:"  # Unbalanced braces
            )
        }
        
        assert self.validator.validate_prompt_templates(models_with_valid_templates)
        assert not self.validator.validate_prompt_templates(models_with_invalid_templates)
    
    def test_validate_defaults_config(self):
        """Test validation of defaults configuration."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Test", version="1.0"),
            tasks=[TaskConfig(name="test", model_ref="model", task_name="hellaswag")],
            models={"model": ModelConfig(name="model", type="openai", model_name="gpt-3.5-turbo")},
            defaults=DefaultConfig(num_fewshot=-1, batch_size=0)  # Invalid values
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        error_messages = [error.message for error in result.errors]
        assert any("Default num_fewshot must be non-negative" in msg for msg in error_messages)
        assert any("Default batch_size must be positive" in msg for msg in error_messages)
    
    def test_validation_result_methods(self):
        """Test ValidationResult helper methods."""
        result = ValidationResult(is_valid=True)
        
        # Add an error
        error = ValidationError(
            type="semantic",
            message="Test error",
            severity=ValidationSeverity.ERROR
        )
        result.add_error(error)
        
        assert not result.is_valid
        assert result.has_errors()
        assert not result.has_warnings()
        assert len(result.get_all_issues()) == 1
        
        # Add a warning
        warning = ValidationError(
            type="semantic",
            message="Test warning",
            severity=ValidationSeverity.WARNING
        )
        result.add_error(warning)
        
        assert result.has_warnings()
        assert len(result.get_all_issues()) == 2
    
    def test_validation_error_string_representation(self):
        """Test ValidationError string representation."""
        error = ValidationError(
            type="semantic",
            message="Test error message",
            severity=ValidationSeverity.ERROR,
            location="test.location",
            suggestion="Fix the error"
        )
        
        error_str = str(error)
        assert "ERROR: Test error message" in error_str
        assert "Location: test.location" in error_str
        assert "Suggestion: Fix the error" in error_str


class TestValidatorIntegration:
    """Integration tests for validator with real configurations."""
    
    def test_validate_complex_configuration(self):
        """Test validation of a complex, realistic configuration."""
        validator = ConfigValidator()
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(
                name="Multi-Model Evaluation",
                version="2.0",
                author="Test Team"
            ),
            variables={"output_dir": "./results", "batch_size": 16},
            models={
                "gpt35": ModelConfig(
                    name="gpt35",
                    type="openai",
                    model_name="gpt-3.5-turbo",
                    parameters={"temperature": 0.7, "max_tokens": 1000}
                ),
                "claude": ModelConfig(
                    name="claude",
                    type="anthropic",
                    model_name="claude-3-sonnet-20240229",
                    parameters={"temperature": 0.5, "max_tokens": 2000}
                )
            },
            tasks=[
                TaskConfig(
                    name="reasoning_gpt",
                    model_ref="gpt35",
                    task_name="hellaswag",
                    num_fewshot=10,
                    batch_size=32
                ),
                TaskConfig(
                    name="reasoning_claude",
                    model_ref="claude",
                    task_name="arc_easy",
                    num_fewshot=5,
                    batch_size=16,
                    depends_on=["reasoning_gpt"]
                )
            ],
            defaults=DefaultConfig(num_fewshot=5, batch_size=32),
            output=OutputConfig(
                directory="./results",
                formats=["json", "csv"],
                include_raw_responses=True
            )
        )
        
        result = validator.validate_config(config)
        
        # Should be valid with possible warnings
        assert result.is_valid
        # May have warnings about unknown model names, but no errors
        assert len(result.errors) == 0