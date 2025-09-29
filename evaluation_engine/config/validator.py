"""
Configuration validator for evaluation_engine.

This module provides comprehensive validation functionality for configuration files,
including basic validation, model reference integrity checks, and lm-eval task validation.
"""

import os
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass

from .models import (
    EvaluationConfig,
    TaskConfig,
    ModelConfig,
    ValidationResult,
    ValidationError,
    ValidationSeverity
)


@dataclass
class ModelTypeInfo:
    """Information about supported model types."""
    name: str
    required_parameters: Set[str]
    optional_parameters: Set[str]
    valid_parameter_types: Dict[str, type]


class ConfigValidator:
    """Validator for evaluation configuration files."""
    
    def __init__(self):
        """Initialize the configuration validator."""
        self._supported_model_types = self._get_supported_model_types()
        self._lm_eval_tasks = None  # Will be loaded lazily
    
    def validate_config(self, config: EvaluationConfig) -> ValidationResult:
        """
        Validate complete configuration for correctness and completeness.
        
        Args:
            config: EvaluationConfig object to validate
            
        Returns:
            ValidationResult with validation results
        """
        result = ValidationResult(is_valid=True)
        
        # Perform basic configuration validation
        self._validate_basic_config(config, result)
        
        # Validate model reference integrity
        self._validate_model_references(config, result)
        
        # Validate model configurations
        self._validate_model_configs(config, result)
        
        # Validate lm-eval tasks
        self._validate_lm_eval_tasks(config, result)
        
        # Validate task dependencies
        self._validate_task_dependencies(config, result)
        
        # Validate output configuration
        self._validate_output_config(config, result)
        
        return result
    
    def check_model_availability(self, model_configs: Dict[str, ModelConfig]) -> bool:
        """
        Check if all specified models are available and properly configured.
        
        Args:
            model_configs: Dictionary of model configurations
            
        Returns:
            True if all models are available, False otherwise
        """
        for model_name, model_config in model_configs.items():
            if not self._is_model_available(model_config):
                return False
        return True
    
    def check_lm_eval_tasks(self, task_names: List[str]) -> bool:
        """
        Check if all specified task names are valid lm-eval tasks.
        
        Args:
            task_names: List of task names to validate
            
        Returns:
            True if all tasks are valid, False otherwise
        """
        valid_tasks = self._get_lm_eval_tasks()
        return all(task_name in valid_tasks for task_name in task_names)
    
    def get_invalid_lm_eval_tasks(self, task_names: List[str]) -> List[str]:
        """
        Get list of invalid lm-eval task names.
        
        Args:
            task_names: List of task names to validate
            
        Returns:
            List of invalid task names
        """
        valid_tasks = self._get_lm_eval_tasks()
        return [task_name for task_name in task_names if task_name not in valid_tasks]
    
    def get_task_suggestions(self, invalid_task: str) -> List[str]:
        """
        Get suggestions for similar valid task names.
        
        Args:
            invalid_task: Invalid task name
            
        Returns:
            List of suggested valid task names
        """
        valid_tasks = self._get_lm_eval_tasks()
        suggestions = []
        
        # Simple similarity matching
        invalid_lower = invalid_task.lower()
        
        # Exact substring matches
        for task in valid_tasks:
            if invalid_lower in task.lower() or task.lower() in invalid_lower:
                suggestions.append(task)
        
        # If no substring matches, try prefix/suffix matching
        if not suggestions:
            for task in valid_tasks:
                task_lower = task.lower()
                if (invalid_lower.startswith(task_lower[:3]) or 
                    task_lower.startswith(invalid_lower[:3]) or
                    invalid_lower.endswith(task_lower[-3:]) or
                    task_lower.endswith(invalid_lower[-3:])):
                    suggestions.append(task)
        
        return sorted(suggestions[:5])  # Return top 5 suggestions
    
    def get_task_info(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific lm-eval task.
        
        Args:
            task_name: Name of the task to get info for
            
        Returns:
            Dictionary with task information or None if task not found
        """
        try:
            from lm_eval.tasks import TaskManager
            
            task_manager = TaskManager()
            
            # Check if task exists
            if task_name not in self._get_lm_eval_tasks():
                return None
            
            # Try to get task information
            task_info = {
                "name": task_name,
                "exists": True,
                "can_load": self._can_load_lm_eval_task(task_name),
                "is_group": task_name in task_manager.all_groups,
                "is_tag": task_name in task_manager.all_tags,
                "is_subtask": task_name in task_manager.all_subtasks
            }
            
            # Try to get more detailed info if possible
            try:
                task_dict = task_manager.load_task_or_group([task_name])
                if task_dict:
                    task_obj = list(task_dict.values())[0]
                    if hasattr(task_obj, 'DATASET_PATH'):
                        task_info["dataset_path"] = task_obj.DATASET_PATH
                    if hasattr(task_obj, 'DATASET_NAME'):
                        task_info["dataset_name"] = task_obj.DATASET_NAME
                    if hasattr(task_obj, 'description'):
                        task_info["description"] = task_obj.description
            except Exception:
                # If we can't load detailed info, that's okay
                pass
            
            return task_info
            
        except ImportError:
            # If lm_eval is not available, return basic info
            return {
                "name": task_name,
                "exists": task_name in self._get_lm_eval_tasks(),
                "can_load": False,
                "is_group": False,
                "is_tag": False,
                "is_subtask": False
            }
        except Exception:
            return None
    
    def check_model_references(self, tasks: List[TaskConfig], models: Dict[str, ModelConfig]) -> bool:
        """
        Check if all model references in tasks exist in the models configuration.
        
        Args:
            tasks: List of task configurations
            models: Dictionary of model configurations
            
        Returns:
            True if all references are valid, False otherwise
        """
        for task in tasks:
            if task.model_ref not in models:
                return False
        return True
    
    def validate_prompt_templates(self, model_configs: Dict[str, ModelConfig]) -> bool:
        """
        Validate prompt templates in model configurations.
        
        Args:
            model_configs: Dictionary of model configurations
            
        Returns:
            True if all templates are valid, False otherwise
        """
        for model_config in model_configs.values():
            if model_config.prompt_template and not self._is_valid_prompt_template(model_config.prompt_template):
                return False
        return True
    
    def _validate_basic_config(self, config: EvaluationConfig, result: ValidationResult):
        """Validate basic configuration structure and required fields."""
        
        # Validate metadata
        if not config.metadata:
            result.add_error(ValidationError(
                type="semantic",
                message="Configuration metadata is required",
                severity=ValidationSeverity.ERROR,
                suggestion="Add metadata section with at least 'name' field"
            ))
        elif not config.metadata.name:
            result.add_error(ValidationError(
                type="semantic",
                message="Configuration name is required in metadata",
                severity=ValidationSeverity.ERROR,
                location="metadata.name",
                suggestion="Provide a descriptive name for the configuration"
            ))
        
        # Validate tasks
        if not config.tasks:
            result.add_error(ValidationError(
                type="semantic",
                message="At least one task must be defined",
                severity=ValidationSeverity.ERROR,
                location="tasks",
                suggestion="Add at least one task configuration"
            ))
        else:
            # Validate individual tasks
            task_names = set()
            for i, task in enumerate(config.tasks):
                self._validate_task_config(task, i, result)
                
                # Check for duplicate task names
                if task.name in task_names:
                    result.add_error(ValidationError(
                        type="semantic",
                        message=f"Duplicate task name: {task.name}",
                        severity=ValidationSeverity.ERROR,
                        location=f"tasks[{i}].name",
                        suggestion="Use unique names for all tasks"
                    ))
                task_names.add(task.name)
        
        # Validate defaults if present
        if config.defaults:
            self._validate_defaults_config(config.defaults, result)
    
    def _validate_task_config(self, task: TaskConfig, index: int, result: ValidationResult):
        """Validate individual task configuration."""
        
        # Required fields validation
        if not task.name:
            result.add_error(ValidationError(
                type="semantic",
                message="Task name is required",
                severity=ValidationSeverity.ERROR,
                location=f"tasks[{index}].name",
                suggestion="Provide a unique name for the task"
            ))
        
        if not task.model_ref:
            result.add_error(ValidationError(
                type="semantic",
                message="Model reference is required",
                severity=ValidationSeverity.ERROR,
                location=f"tasks[{index}].model_ref",
                suggestion="Specify which model to use for this task"
            ))
        
        if not task.task_name:
            result.add_error(ValidationError(
                type="semantic",
                message="Task name (lm-eval task) is required",
                severity=ValidationSeverity.ERROR,
                location=f"tasks[{index}].task_name",
                suggestion="Specify a valid lm-eval task name"
            ))
        
        # Validate numeric parameters
        if task.num_fewshot is not None and task.num_fewshot < 0:
            result.add_error(ValidationError(
                type="semantic",
                message="num_fewshot must be non-negative",
                severity=ValidationSeverity.ERROR,
                location=f"tasks[{index}].num_fewshot",
                suggestion="Use 0 for zero-shot or positive integer for few-shot"
            ))
        
        if task.batch_size is not None and task.batch_size <= 0:
            result.add_error(ValidationError(
                type="semantic",
                message="batch_size must be positive",
                severity=ValidationSeverity.ERROR,
                location=f"tasks[{index}].batch_size",
                suggestion="Use a positive integer for batch size"
            ))
        
        # Validate task_config if present
        if task.task_config is not None and not isinstance(task.task_config, dict):
            result.add_error(ValidationError(
                type="semantic",
                message="task_config must be a dictionary",
                severity=ValidationSeverity.ERROR,
                location=f"tasks[{index}].task_config",
                suggestion="Use key-value pairs for task-specific configuration"
            ))
    
    def _validate_defaults_config(self, defaults, result: ValidationResult):
        """Validate defaults configuration."""
        
        if defaults.num_fewshot < 0:
            result.add_error(ValidationError(
                type="semantic",
                message="Default num_fewshot must be non-negative",
                severity=ValidationSeverity.ERROR,
                location="defaults.num_fewshot",
                suggestion="Use 0 for zero-shot or positive integer for few-shot"
            ))
        
        if defaults.batch_size <= 0:
            result.add_error(ValidationError(
                type="semantic",
                message="Default batch_size must be positive",
                severity=ValidationSeverity.ERROR,
                location="defaults.batch_size",
                suggestion="Use a positive integer for batch size"
            ))
    
    def _validate_model_references(self, config: EvaluationConfig, result: ValidationResult):
        """Validate that all model references in tasks exist in models configuration."""
        
        model_names = set(config.models.keys())
        
        # Check if models section is empty but tasks reference models
        if not model_names and config.tasks:
            result.add_error(ValidationError(
                type="semantic",
                message="No models defined but tasks reference models",
                severity=ValidationSeverity.ERROR,
                location="models",
                suggestion="Define at least one model in the models section"
            ))
            return
        
        # Validate each task's model reference
        for i, task in enumerate(config.tasks):
            if not task.model_ref:
                result.add_error(ValidationError(
                    type="semantic",
                    message="Task model reference cannot be empty",
                    severity=ValidationSeverity.ERROR,
                    location=f"tasks[{i}].model_ref",
                    suggestion="Specify a valid model reference"
                ))
                continue
                
            if task.model_ref not in model_names:
                result.add_error(ValidationError(
                    type="semantic",
                    message=f"Model reference '{task.model_ref}' not found in models configuration",
                    severity=ValidationSeverity.ERROR,
                    location=f"tasks[{i}].model_ref",
                    suggestion=f"Define model '{task.model_ref}' in models section or use existing model: {', '.join(sorted(model_names)) if model_names else 'none defined'}"
                ))
            else:
                # Additional validation: check if the referenced model is properly configured
                referenced_model = config.models[task.model_ref]
                self._validate_model_reference_compatibility(task, referenced_model, i, result)
    
    def _validate_model_configs(self, config: EvaluationConfig, result: ValidationResult):
        """Validate model configurations for completeness and correctness."""
        
        for model_name, model_config in config.models.items():
            self._validate_single_model_config(model_name, model_config, result)
    
    def _validate_single_model_config(self, model_name: str, model_config: ModelConfig, result: ValidationResult):
        """Validate a single model configuration."""
        
        # Validate basic model configuration fields
        if not model_config.name:
            result.add_error(ValidationError(
                type="semantic",
                message="Model name cannot be empty",
                severity=ValidationSeverity.ERROR,
                location=f"models.{model_name}.name",
                suggestion="Provide a valid model name"
            ))
        
        if not model_config.model_name:
            result.add_error(ValidationError(
                type="semantic",
                message="Model model_name cannot be empty",
                severity=ValidationSeverity.ERROR,
                location=f"models.{model_name}.model_name",
                suggestion="Provide a valid model identifier"
            ))
        
        # Validate model type
        if not model_config.type:
            result.add_error(ValidationError(
                type="semantic",
                message="Model type cannot be empty",
                severity=ValidationSeverity.ERROR,
                location=f"models.{model_name}.type",
                suggestion=f"Specify one of supported types: {', '.join(self._supported_model_types.keys())}"
            ))
            return
            
        if model_config.type not in self._supported_model_types:
            result.add_error(ValidationError(
                type="semantic",
                message=f"Unsupported model type: {model_config.type}",
                severity=ValidationSeverity.ERROR,
                location=f"models.{model_name}.type",
                suggestion=f"Use one of supported types: {', '.join(self._supported_model_types.keys())}"
            ))
            return  # Skip further validation if type is invalid
        
        model_type_info = self._supported_model_types[model_config.type]
        
        # Validate required parameters
        for required_param in model_type_info.required_parameters:
            if required_param not in model_config.parameters:
                result.add_error(ValidationError(
                    type="semantic",
                    message=f"Required parameter '{required_param}' missing for model type '{model_config.type}'",
                    severity=ValidationSeverity.ERROR,
                    location=f"models.{model_name}.parameters.{required_param}",
                    suggestion=f"Add required parameter '{required_param}' to model parameters"
                ))
        
        # Validate parameter types
        for param_name, param_value in model_config.parameters.items():
            if param_name in model_type_info.valid_parameter_types:
                expected_type = model_type_info.valid_parameter_types[param_name]
                if not isinstance(param_value, expected_type):
                    result.add_error(ValidationError(
                        type="semantic",
                        message=f"Parameter '{param_name}' must be of type {expected_type.__name__}, got {type(param_value).__name__}",
                        severity=ValidationSeverity.ERROR,
                        location=f"models.{model_name}.parameters.{param_name}",
                        suggestion=f"Convert parameter value to {expected_type.__name__}"
                    ))
        
        # Validate prompt template if present
        if model_config.prompt_template and not self._is_valid_prompt_template(model_config.prompt_template):
            result.add_error(ValidationError(
                type="semantic",
                message="Invalid prompt template format",
                severity=ValidationSeverity.WARNING,
                location=f"models.{model_name}.prompt_template",
                suggestion="Ensure prompt template contains valid placeholder syntax"
            ))
        
        # Validate system prompt if present
        if model_config.system_prompt and not isinstance(model_config.system_prompt, str):
            result.add_error(ValidationError(
                type="semantic",
                message="System prompt must be a string",
                severity=ValidationSeverity.ERROR,
                location=f"models.{model_name}.system_prompt",
                suggestion="Provide system prompt as a string"
            ))
        
        # Model-specific validations
        self._validate_model_specific_config(model_name, model_config, result)
    
    def _validate_model_reference_compatibility(self, task: TaskConfig, model: ModelConfig, task_index: int, result: ValidationResult):
        """Validate compatibility between task and referenced model."""
        
        # Check if model is properly configured for the task
        if not model.model_name:
            result.add_error(ValidationError(
                type="semantic",
                message=f"Referenced model '{task.model_ref}' has no model_name configured",
                severity=ValidationSeverity.ERROR,
                location=f"tasks[{task_index}].model_ref",
                suggestion=f"Configure model_name for model '{task.model_ref}'"
            ))
        
        # Check if model type is supported
        if model.type not in self._supported_model_types:
            result.add_error(ValidationError(
                type="semantic",
                message=f"Task '{task.name}' references model '{task.model_ref}' with unsupported type '{model.type}'",
                severity=ValidationSeverity.ERROR,
                location=f"tasks[{task_index}].model_ref",
                suggestion=f"Use a model with supported type: {', '.join(self._supported_model_types.keys())}"
            ))
        
        # Validate task-specific model requirements
        self._validate_task_model_requirements(task, model, task_index, result)
    
    def _validate_task_model_requirements(self, task: TaskConfig, model: ModelConfig, task_index: int, result: ValidationResult):
        """Validate task-specific model requirements."""
        
        # Check if certain tasks require specific model capabilities
        task_model_requirements = {
            "humaneval": {"code_generation": True},
            "mbpp": {"code_generation": True},
            "gsm8k": {"math_reasoning": True},
            "truthfulqa_gen": {"text_generation": True}
        }
        
        if task.task_name in task_model_requirements:
            requirements = task_model_requirements[task.task_name]
            
            # For code generation tasks, warn if using non-code models
            if requirements.get("code_generation") and model.type == "anthropic":
                result.add_error(ValidationError(
                    type="semantic",
                    message=f"Task '{task.task_name}' is a code generation task, consider using a model optimized for code",
                    severity=ValidationSeverity.WARNING,
                    location=f"tasks[{task_index}].model_ref",
                    suggestion="Consider using OpenAI Codex or similar code-optimized models"
                ))
        
        # Validate model parameters are compatible with task requirements
        if task.task_config and "temperature" in task.task_config:
            task_temp = task.task_config["temperature"]
            model_temp = model.parameters.get("temperature")
            
            if model_temp is not None and abs(task_temp - model_temp) > 0.1:
                result.add_error(ValidationError(
                    type="semantic",
                    message=f"Task temperature ({task_temp}) differs significantly from model temperature ({model_temp})",
                    severity=ValidationSeverity.WARNING,
                    location=f"tasks[{task_index}].task_config.temperature",
                    suggestion="Consider aligning task and model temperature settings"
                ))
    
    def _validate_model_specific_config(self, model_name: str, model_config: ModelConfig, result: ValidationResult):
        """Perform model-type-specific validations."""
        
        if model_config.type == "openai":
            self._validate_openai_model(model_name, model_config, result)
        elif model_config.type == "anthropic":
            self._validate_anthropic_model(model_name, model_config, result)
        elif model_config.type == "huggingface":
            self._validate_huggingface_model(model_name, model_config, result)
    
    def _validate_openai_model(self, model_name: str, model_config: ModelConfig, result: ValidationResult):
        """Validate OpenAI-specific model configuration."""
        
        # Check for common OpenAI model names
        common_openai_models = {
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k", 
            "gpt-4-turbo-preview", "gpt-4-vision-preview", "text-davinci-003"
        }
        
        if model_config.model_name not in common_openai_models:
            result.add_error(ValidationError(
                type="semantic",
                message=f"Unknown OpenAI model: {model_config.model_name}",
                severity=ValidationSeverity.WARNING,
                location=f"models.{model_name}.model_name",
                suggestion=f"Verify model name. Common models: {', '.join(sorted(common_openai_models))}"
            ))
        
        # Validate temperature parameter
        if "temperature" in model_config.parameters:
            temp = model_config.parameters["temperature"]
            if not (0 <= temp <= 2):
                result.add_error(ValidationError(
                    type="semantic",
                    message="OpenAI temperature must be between 0 and 2",
                    severity=ValidationSeverity.ERROR,
                    location=f"models.{model_name}.parameters.temperature",
                    suggestion="Use a value between 0 (deterministic) and 2 (very random)"
                ))
    
    def _validate_anthropic_model(self, model_name: str, model_config: ModelConfig, result: ValidationResult):
        """Validate Anthropic-specific model configuration."""
        
        # Check for common Anthropic model names
        common_anthropic_models = {
            "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
            "claude-2.1", "claude-2.0", "claude-instant-1.2"
        }
        
        if model_config.model_name not in common_anthropic_models:
            result.add_error(ValidationError(
                type="semantic",
                message=f"Unknown Anthropic model: {model_config.model_name}",
                severity=ValidationSeverity.WARNING,
                location=f"models.{model_name}.model_name",
                suggestion=f"Verify model name. Common models: {', '.join(sorted(common_anthropic_models))}"
            ))
    
    def _validate_huggingface_model(self, model_name: str, model_config: ModelConfig, result: ValidationResult):
        """Validate Hugging Face-specific model configuration."""
        
        # Validate model name format (should be in format "organization/model-name")
        if "/" not in model_config.model_name:
            result.add_error(ValidationError(
                type="semantic",
                message="Hugging Face model name should be in format 'organization/model-name'",
                severity=ValidationSeverity.WARNING,
                location=f"models.{model_name}.model_name",
                suggestion="Use format like 'meta-llama/Llama-2-7b-chat-hf'"
            ))
    
    def _validate_lm_eval_tasks(self, config: EvaluationConfig, result: ValidationResult):
        """Validate that all specified tasks are valid lm-eval tasks."""
        
        valid_tasks = self._get_lm_eval_tasks()
        
        for i, task in enumerate(config.tasks):
            if task.task_name not in valid_tasks:
                # Get suggestions for similar task names
                suggestions = self.get_task_suggestions(task.task_name)
                suggestion_text = f"Use a valid lm-eval task name. Available tasks can be listed with 'lm_eval --tasks list'"
                
                if suggestions:
                    suggestion_text += f". Did you mean: {', '.join(suggestions[:3])}?"
                
                result.add_error(ValidationError(
                    type="semantic",
                    message=f"Unknown lm-eval task: {task.task_name}",
                    severity=ValidationSeverity.ERROR,
                    location=f"tasks[{i}].task_name",
                    suggestion=suggestion_text
                ))
            else:
                # Validate that the task can actually be loaded
                if not self._can_load_lm_eval_task(task.task_name):
                    result.add_error(ValidationError(
                        type="semantic",
                        message=f"Task '{task.task_name}' exists but cannot be loaded",
                        severity=ValidationSeverity.WARNING,
                        location=f"tasks[{i}].task_name",
                        suggestion="Check if task dependencies are installed or if task configuration is valid"
                    ))
            
            # Validate task-specific configuration
            if task.task_config:
                self._validate_task_specific_config(task.task_name, task.task_config, i, result)
    
    def _can_load_lm_eval_task(self, task_name: str) -> bool:
        """
        Check if a task can actually be loaded by the lm-eval framework.
        
        Args:
            task_name: Name of the task to check
            
        Returns:
            True if task can be loaded, False otherwise
        """
        try:
            from lm_eval.tasks import TaskManager
            
            task_manager = TaskManager()
            
            # Try to load the task
            task_dict = task_manager.load_task_or_group([task_name])
            return len(task_dict) > 0
            
        except ImportError:
            # If lm_eval is not available, assume task can be loaded if it's in our list
            return task_name in self._get_lm_eval_tasks()
        except Exception as e:
            # Log specific errors for debugging but don't fail validation
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Could not load task '{task_name}': {e}")
            
            # For certain known issues, still consider the task valid
            error_str = str(e).lower()
            if any(known_issue in error_str for known_issue in [
                "unitxt", "missing file", "file not found", "no such file",
                "dataset not found", "connection error", "timeout"
            ]):
                # These are typically dependency or data issues, not task definition issues
                return True
            
            # For other errors, return False
            return False
    
    def _validate_task_specific_config(self, task_name: str, task_config: Dict[str, Any], task_index: int, result: ValidationResult):
        """Validate task-specific configuration parameters."""
        
        # Common task configuration parameters
        if "limit" in task_config:
            limit = task_config["limit"]
            if not isinstance(limit, int) or limit <= 0:
                result.add_error(ValidationError(
                    type="semantic",
                    message="Task limit must be a positive integer",
                    severity=ValidationSeverity.ERROR,
                    location=f"tasks[{task_index}].task_config.limit",
                    suggestion="Use a positive integer to limit the number of test samples"
                ))
        
        if "temperature" in task_config:
            temp = task_config["temperature"]
            if not isinstance(temp, (int, float)) or temp < 0:
                result.add_error(ValidationError(
                    type="semantic",
                    message="Task temperature must be a non-negative number",
                    severity=ValidationSeverity.ERROR,
                    location=f"tasks[{task_index}].task_config.temperature",
                    suggestion="Use a non-negative number for temperature"
                ))
        
        # Validate task-specific parameters based on lm-eval task requirements
        self._validate_lm_eval_task_parameters(task_name, task_config, task_index, result)
    
    def _validate_lm_eval_task_parameters(self, task_name: str, task_config: Dict[str, Any], task_index: int, result: ValidationResult):
        """Validate parameters specific to lm-eval tasks."""
        
        # Get task-specific parameter requirements
        task_requirements = self._get_task_parameter_requirements(task_name)
        
        # Validate required parameters
        for param_name, param_info in task_requirements.get("required", {}).items():
            if param_name not in task_config:
                result.add_error(ValidationError(
                    type="semantic",
                    message=f"Required parameter '{param_name}' missing for task '{task_name}'",
                    severity=ValidationSeverity.ERROR,
                    location=f"tasks[{task_index}].task_config.{param_name}",
                    suggestion=f"Add required parameter '{param_name}': {param_info.get('description', 'No description available')}"
                ))
        
        # Validate parameter types and values
        for param_name, param_value in task_config.items():
            if param_name in task_requirements.get("valid_params", {}):
                param_info = task_requirements["valid_params"][param_name]
                
                # Check parameter type
                expected_type = param_info.get("type")
                if expected_type and not isinstance(param_value, expected_type):
                    result.add_error(ValidationError(
                        type="semantic",
                        message=f"Parameter '{param_name}' must be of type {expected_type.__name__}, got {type(param_value).__name__}",
                        severity=ValidationSeverity.ERROR,
                        location=f"tasks[{task_index}].task_config.{param_name}",
                        suggestion=f"Convert parameter value to {expected_type.__name__}"
                    ))
                    continue
                
                # Check parameter value constraints
                if "min_value" in param_info and isinstance(param_value, (int, float)):
                    if param_value < param_info["min_value"]:
                        result.add_error(ValidationError(
                            type="semantic",
                            message=f"Parameter '{param_name}' must be >= {param_info['min_value']}, got {param_value}",
                            severity=ValidationSeverity.ERROR,
                            location=f"tasks[{task_index}].task_config.{param_name}",
                            suggestion=f"Use a value >= {param_info['min_value']}"
                        ))
                
                if "max_value" in param_info and isinstance(param_value, (int, float)):
                    if param_value > param_info["max_value"]:
                        result.add_error(ValidationError(
                            type="semantic",
                            message=f"Parameter '{param_name}' must be <= {param_info['max_value']}, got {param_value}",
                            severity=ValidationSeverity.ERROR,
                            location=f"tasks[{task_index}].task_config.{param_name}",
                            suggestion=f"Use a value <= {param_info['max_value']}"
                        ))
                
                if "valid_values" in param_info:
                    if param_value not in param_info["valid_values"]:
                        result.add_error(ValidationError(
                            type="semantic",
                            message=f"Parameter '{param_name}' must be one of {param_info['valid_values']}, got {param_value}",
                            severity=ValidationSeverity.ERROR,
                            location=f"tasks[{task_index}].task_config.{param_name}",
                            suggestion=f"Use one of: {', '.join(map(str, param_info['valid_values']))}"
                        ))
            
            elif param_name not in {"limit", "temperature"}:  # Skip common parameters we already validated
                # Warn about unknown parameters
                result.add_error(ValidationError(
                    type="semantic",
                    message=f"Unknown parameter '{param_name}' for task '{task_name}'",
                    severity=ValidationSeverity.WARNING,
                    location=f"tasks[{task_index}].task_config.{param_name}",
                    suggestion=f"Verify parameter name or remove if not needed. Check lm-eval documentation for '{task_name}'"
                ))
    
    def _get_task_parameter_requirements(self, task_name: str) -> Dict[str, Any]:
        """Get parameter requirements for a specific lm-eval task."""
        
        # Define parameter requirements for common lm-eval tasks
        task_parameters = {
            # Code generation tasks
            "humaneval": {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 4096},
                    "top_p": {"type": (int, float), "min_value": 0, "max_value": 1},
                    "stop": {"type": (str, list)},
                    "limit": {"type": int, "min_value": 1}
                }
            },
            "mbpp": {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 4096},
                    "top_p": {"type": (int, float), "min_value": 0, "max_value": 1},
                    "limit": {"type": int, "min_value": 1}
                }
            },
            
            # Math reasoning tasks
            "gsm8k": {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 2048},
                    "limit": {"type": int, "min_value": 1}
                }
            },
            
            # Multiple choice tasks
            "hellaswag": {
                "valid_params": {
                    "limit": {"type": int, "min_value": 1}
                }
            },
            "arc_easy": {
                "valid_params": {
                    "limit": {"type": int, "min_value": 1}
                }
            },
            "arc_challenge": {
                "valid_params": {
                    "limit": {"type": int, "min_value": 1}
                }
            },
            "mmlu": {
                "valid_params": {
                    "limit": {"type": int, "min_value": 1}
                }
            },
            
            # Text generation tasks
            "truthfulqa_gen": {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 1024},
                    "limit": {"type": int, "min_value": 1}
                }
            },
            "truthfulqa_mc": {
                "valid_params": {
                    "limit": {"type": int, "min_value": 1}
                }
            },
            
            # Custom single-turn scenarios
            "single_turn_scenarios_function_generation": {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 4096},
                    "context_type": {"type": str, "valid_values": ["no_context", "minimal_context", "full_context"]},
                    "difficulty": {"type": str, "valid_values": ["easy", "medium", "hard"]},
                    "limit": {"type": int, "min_value": 1}
                }
            },
            "single_turn_scenarios_code_completion": {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 2048},
                    "completion_type": {"type": str, "valid_values": ["function", "class", "snippet"]},
                    "limit": {"type": int, "min_value": 1}
                }
            },
            
            # Multi-turn tasks
            "multi_turn_coding": {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 4096},
                    "max_turns": {"type": int, "min_value": 1, "max_value": 10},
                    "limit": {"type": int, "min_value": 1}
                }
            },
            
            # Python coding tasks
            "python_coding": {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 4096},
                    "limit": {"type": int, "min_value": 1}
                }
            },
            
            # Function generation task
            "function_generation": {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 4096},
                    "limit": {"type": int, "min_value": 1}
                }
            }
        }
        
        # Check for pattern-based parameter requirements
        # This handles tasks that follow naming patterns
        if task_name.startswith("single_turn_scenarios_"):
            return {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 4096},
                    "limit": {"type": int, "min_value": 1}
                }
            }
        elif task_name.startswith("multi_turn_"):
            return {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 4096},
                    "max_turns": {"type": int, "min_value": 1, "max_value": 10},
                    "limit": {"type": int, "min_value": 1}
                }
            }
        elif task_name.startswith("mmlu_"):
            return {
                "valid_params": {
                    "limit": {"type": int, "min_value": 1}
                }
            }
        elif "coding" in task_name or "code" in task_name:
            return {
                "valid_params": {
                    "temperature": {"type": (int, float), "min_value": 0, "max_value": 2},
                    "max_tokens": {"type": int, "min_value": 1, "max_value": 4096},
                    "limit": {"type": int, "min_value": 1}
                }
            }
        
        # Return specific requirements or default empty dict
        return task_parameters.get(task_name, {"valid_params": {}})
    
    def _validate_task_dependencies(self, config: EvaluationConfig, result: ValidationResult):
        """Validate task dependencies for circular references and existence."""
        
        task_names = {task.name for task in config.tasks}
        
        # Check that all dependencies exist
        for i, task in enumerate(config.tasks):
            for dep in task.depends_on:
                if dep not in task_names:
                    result.add_error(ValidationError(
                        type="semantic",
                        message=f"Task dependency '{dep}' not found",
                        severity=ValidationSeverity.ERROR,
                        location=f"tasks[{i}].depends_on",
                        suggestion=f"Ensure dependency task exists. Available tasks: {', '.join(sorted(task_names))}"
                    ))
        
        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies(config.tasks)
        if circular_deps:
            result.add_error(ValidationError(
                type="semantic",
                message=f"Circular dependency detected: {' -> '.join(circular_deps)}",
                severity=ValidationSeverity.ERROR,
                location="tasks.depends_on",
                suggestion="Remove circular dependencies between tasks"
            ))
    
    def _validate_output_config(self, config: EvaluationConfig, result: ValidationResult):
        """Validate output configuration."""
        
        if config.output:
            # Validate output directory
            if config.output.directory:
                # Check if parent directory exists or can be created
                parent_dir = os.path.dirname(config.output.directory)
                if parent_dir and not os.path.exists(parent_dir):
                    result.add_error(ValidationError(
                        type="semantic",
                        message=f"Output directory parent does not exist: {parent_dir}",
                        severity=ValidationSeverity.WARNING,
                        location="output.directory",
                        suggestion="Ensure parent directory exists or will be created"
                    ))
            
            # Validate output formats
            supported_formats = {"json", "csv", "html", "yaml"}
            for fmt in config.output.formats:
                if fmt not in supported_formats:
                    result.add_error(ValidationError(
                        type="semantic",
                        message=f"Unsupported output format: {fmt}",
                        severity=ValidationSeverity.ERROR,
                        location="output.formats",
                        suggestion=f"Use supported formats: {', '.join(sorted(supported_formats))}"
                    ))
    
    def _detect_circular_dependencies(self, tasks: List[TaskConfig]) -> Optional[List[str]]:
        """
        Detect circular dependencies in task list.
        
        Args:
            tasks: List of task configurations
            
        Returns:
            List representing circular dependency path, or None if no cycles
        """
        # Build dependency graph
        graph = {}
        for task in tasks:
            graph[task.name] = task.depends_on
        
        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            if node in rec_stack:
                # Found cycle, return the cycle path
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                cycle = dfs(neighbor, path + [node])
                if cycle:
                    return cycle
            
            rec_stack.remove(node)
            return None
        
        for task_name in graph:
            if task_name not in visited:
                cycle = dfs(task_name, [])
                if cycle:
                    return cycle
        
        return None
    
    def _get_supported_model_types(self) -> Dict[str, ModelTypeInfo]:
        """Get information about supported model types."""
        
        return {
            "openai": ModelTypeInfo(
                name="openai",
                required_parameters=set(),
                optional_parameters={"temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"},
                valid_parameter_types={
                    "temperature": (int, float),
                    "max_tokens": int,
                    "top_p": (int, float),
                    "frequency_penalty": (int, float),
                    "presence_penalty": (int, float)
                }
            ),
            "anthropic": ModelTypeInfo(
                name="anthropic",
                required_parameters=set(),
                optional_parameters={"temperature", "max_tokens", "top_p", "top_k"},
                valid_parameter_types={
                    "temperature": (int, float),
                    "max_tokens": int,
                    "top_p": (int, float),
                    "top_k": int
                }
            ),
            "huggingface": ModelTypeInfo(
                name="huggingface",
                required_parameters=set(),
                optional_parameters={"temperature", "max_tokens", "top_p", "top_k", "do_sample", "device"},
                valid_parameter_types={
                    "temperature": (int, float),
                    "max_tokens": int,
                    "top_p": (int, float),
                    "top_k": int,
                    "do_sample": bool,
                    "device": str
                }
            ),
            "custom": ModelTypeInfo(
                name="custom",
                required_parameters=set(),
                optional_parameters=set(),
                valid_parameter_types={}
            )
        }
    
    def _get_lm_eval_tasks(self) -> Set[str]:
        """
        Get set of valid lm-eval task names.
        
        Returns:
            Set of valid task names
        """
        if self._lm_eval_tasks is None:
            self._lm_eval_tasks = self._load_lm_eval_tasks()
        return self._lm_eval_tasks
    
    def _load_lm_eval_tasks(self) -> Set[str]:
        """
        Load valid lm-eval task names from the lm-evaluation-harness.
        
        Returns:
            Set of valid task names including individual tasks, groups, and tags
        """
        try:
            # Try to import lm_eval to get available tasks
            from lm_eval.tasks import TaskManager
            from lm_eval.api.registry import ALL_TASKS
            
            # Initialize task manager to get all available tasks
            task_manager = TaskManager()
            
            # Get all registered tasks from the task manager
            available_tasks = set()
            
            # Add all individual tasks (subtasks)
            available_tasks.update(task_manager.all_subtasks)
            
            # Add all groups
            available_tasks.update(task_manager.all_groups)
            
            # Add all tags
            available_tasks.update(task_manager.all_tags)
            
            # Also add tasks from the registry (ALL_TASKS)
            if isinstance(ALL_TASKS, set):
                available_tasks.update(ALL_TASKS)
            elif hasattr(ALL_TASKS, '__iter__'):
                available_tasks.update(set(ALL_TASKS))
            
            # If we don't have standard lm-eval tasks, add them to the available set
            # This handles cases where only custom tasks are installed
            standard_tasks = {
                "hellaswag", "arc_easy", "arc_challenge", "truthfulqa_mc", "truthfulqa_gen",
                "mmlu", "gsm8k", "humaneval", "mbpp", "winogrande", "piqa", "boolq",
                "rte", "cb", "copa", "wic", "wsc", "multirc", "record", "squad2",
                "drop", "quac", "coqa", "narrativeqa", "race", "openbookqa", "sciq",
                "lambada_openai", "lambada_standard", "wikitext", "ptb", "c4",
                "pile_arxiv", "pile_books3", "pile_github", "pile_stackexchange",
                "anli_r1", "anli_r2", "anli_r3", "mnli", "mnli_mismatched",
                "qnli", "qqp", "sst", "mrpc", "cola", "wnli"
            }
            
            # Check if we have any standard tasks, if not, add them all
            if not any(task in available_tasks for task in standard_tasks):
                available_tasks.update(standard_tasks)
            
            # Add common task aliases and variations that might not be in the registry
            common_task_aliases = {
                # MMLU variations
                "mmlu_abstract_algebra", "mmlu_anatomy", "mmlu_astronomy",
                "mmlu_business_ethics", "mmlu_clinical_knowledge", "mmlu_college_biology",
                "mmlu_college_chemistry", "mmlu_college_computer_science", "mmlu_college_mathematics",
                "mmlu_college_medicine", "mmlu_college_physics", "mmlu_computer_security",
                
                # HellaSwag variations
                "hellaswag_10", "hellaswag_0",
                
                # ARC variations  
                "arc_easy_25", "arc_challenge_25",
                
                # TruthfulQA variations
                "truthfulqa_mc1", "truthfulqa_mc2",
                
                # Math tasks
                "math_algebra", "math_counting_and_prob", "math_geometry",
                "math_intermediate_algebra", "math_num_theory", "math_prealgebra", "math_precalc",
                
                # Code tasks
                "humaneval_python", "mbpp_python",
                
                # Single turn scenarios (custom tasks)
                "single_turn_scenarios_function_generation",
                "single_turn_scenarios_code_completion", 
                "single_turn_scenarios_bug_fixing",
                "single_turn_scenarios_code_explanation",
                "single_turn_scenarios_algorithm_design",
                "single_turn_scenarios_data_structure_implementation",
                "single_turn_scenarios_api_usage",
                "single_turn_scenarios_code_optimization",
                "single_turn_scenarios_test_generation",
                "single_turn_scenarios_code_review",
                "single_turn_scenarios_refactoring",
                "single_turn_scenarios_documentation",
                "single_turn_scenarios_debugging",
                "single_turn_scenarios_performance_analysis",
                "single_turn_scenarios_security_analysis",
                "single_turn_scenarios_code_translation",
                "single_turn_scenarios_design_patterns",
                "single_turn_scenarios_system_design",
                
                # Multi-turn scenarios
                "multi_turn_coding", "multi_turn_generic", "multi_turn_scenarios",
                
                # Python coding tasks
                "python_coding"
            }
            
            available_tasks.update(common_task_aliases)
            
            return available_tasks
            
        except ImportError as e:
            # Fallback to a predefined list of common tasks if lm_eval is not available
            return {
                # Core evaluation tasks
                "hellaswag", "arc_easy", "arc_challenge", "truthfulqa_mc", "truthfulqa_gen",
                "mmlu", "gsm8k", "humaneval", "mbpp", "winogrande", "piqa", "boolq",
                "rte", "cb", "copa", "wic", "wsc", "multirc", "record", "squad2",
                "drop", "quac", "coqa", "narrativeqa", "race", "openbookqa", "sciq",
                "lambada_openai", "lambada_standard", "wikitext", "ptb", "c4",
                "pile_arxiv", "pile_books3", "pile_github", "pile_stackexchange",
                "anli_r1", "anli_r2", "anli_r3", "mnli", "mnli_mismatched",
                "qnli", "qqp", "sst", "mrpc", "cola", "wnli",
                
                # Math tasks
                "math_algebra", "math_counting_and_prob", "math_geometry",
                "math_intermediate_algebra", "math_num_theory", "math_prealgebra", "math_precalc",
                
                # Custom single-turn scenarios
                "single_turn_scenarios_function_generation",
                "single_turn_scenarios_code_completion", 
                "single_turn_scenarios_bug_fixing",
                "single_turn_scenarios_code_explanation",
                "single_turn_scenarios_algorithm_design",
                "single_turn_scenarios_data_structure_implementation",
                "single_turn_scenarios_api_usage",
                "single_turn_scenarios_code_optimization",
                "single_turn_scenarios_test_generation",
                "single_turn_scenarios_code_review",
                "single_turn_scenarios_refactoring",
                "single_turn_scenarios_documentation",
                "single_turn_scenarios_debugging",
                "single_turn_scenarios_performance_analysis",
                "single_turn_scenarios_security_analysis",
                "single_turn_scenarios_code_translation",
                "single_turn_scenarios_design_patterns",
                "single_turn_scenarios_system_design",
                
                # Multi-turn and other custom tasks
                "multi_turn_coding", "multi_turn_generic", "multi_turn_scenarios",
                "python_coding"
            }
        except Exception as e:
            # Log the error but continue with fallback
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error loading lm-eval tasks: {e}. Using fallback task list.")
            
            return {
                "hellaswag", "arc_easy", "arc_challenge", "truthfulqa_mc", "truthfulqa_gen",
                "mmlu", "gsm8k", "humaneval", "mbpp", "winogrande", "piqa", "boolq"
            }
    
    def _is_model_available(self, model_config: ModelConfig) -> bool:
        """
        Check if a model is available for use.
        
        Args:
            model_config: Model configuration to check
            
        Returns:
            True if model is available, False otherwise
        """
        # For now, we assume all properly configured models are available
        # In a real implementation, this would check API availability, 
        # local model files, etc.
        return (
            model_config.type in self._supported_model_types and
            bool(model_config.model_name)
        )
    
    def _is_valid_prompt_template(self, template: str) -> bool:
        """
        Validate prompt template format.
        
        Args:
            template: Prompt template string
            
        Returns:
            True if template is valid, False otherwise
        """
        # Basic validation - check for common placeholder patterns
        # This is a simple implementation; a more sophisticated version
        # would parse the template syntax more thoroughly
        
        if not isinstance(template, str):
            return False
        
        # Check for balanced braces (simple check)
        open_braces = template.count('{')
        close_braces = template.count('}')
        
        return open_braces == close_braces