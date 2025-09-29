"""
Task Builder for Configuration-Driven Evaluation

This module implements the TaskBuilder class that converts configuration files
into executable evaluation tasks compatible with the UnifiedEvaluationFramework.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx

from .models import (
    EvaluationConfig, TaskConfig, ModelConfig, ValidationError, 
    ValidationSeverity, ValidationResult
)
from ..core.unified_framework import EvaluationRequest, UnifiedEvaluationFramework

logger = logging.getLogger(__name__)


class DependencyStatus(Enum):
    """Task dependency resolution status."""
    PENDING = "pending"
    RESOLVED = "resolved"
    FAILED = "failed"


@dataclass
class EvaluationTask:
    """Represents a fully resolved evaluation task ready for execution."""
    name: str
    task_config: TaskConfig
    model_config: ModelConfig
    framework_params: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: DependencyStatus = DependencyStatus.PENDING
    
    def to_evaluation_request(self) -> EvaluationRequest:
        """Convert to EvaluationRequest for framework execution."""
        return EvaluationRequest(**self.framework_params)


@dataclass
class ExecutionPlan:
    """Represents an execution plan with dependency-ordered tasks."""
    tasks: List[EvaluationTask]
    execution_order: List[str]
    dependency_graph: Dict[str, List[str]]
    
    def get_next_executable_tasks(self, completed_tasks: Set[str]) -> List[EvaluationTask]:
        """Get tasks that can be executed next based on completed dependencies."""
        executable = []
        for task in self.tasks:
            if (task.name not in completed_tasks and 
                task.status == DependencyStatus.RESOLVED and
                all(dep in completed_tasks for dep in task.dependencies)):
                executable.append(task)
        return executable


class TaskBuilder:
    """
    Builds executable evaluation tasks from configuration files.
    
    This class serves as an adapter layer between configuration files and the
    UnifiedEvaluationFramework, converting declarative configurations into
    the format expected by the existing framework.
    """
    
    def __init__(self, framework: Optional[UnifiedEvaluationFramework] = None):
        """
        Initialize TaskBuilder.
        
        Args:
            framework: UnifiedEvaluationFramework instance. If None, creates a new one.
        """
        self.framework = framework or UnifiedEvaluationFramework()
        self.logger = logging.getLogger(__name__)
    
    def build_tasks(self, config: EvaluationConfig) -> List[EvaluationTask]:
        """
        Build executable tasks from evaluation configuration.
        
        Args:
            config: Complete evaluation configuration
            
        Returns:
            List of EvaluationTask objects ready for execution
            
        Raises:
            ValueError: If configuration is invalid or has unresolvable references
        """
        self.logger.info(f"Building tasks from configuration with {len(config.tasks)} task definitions")
        
        # Validate configuration first
        validation_result = self._validate_configuration(config)
        if not validation_result.is_valid:
            error_messages = [str(error) for error in validation_result.errors]
            raise ValueError(f"Configuration validation failed: {'; '.join(error_messages)}")
        
        tasks = []
        for task_config in config.tasks:
            try:
                # Resolve model reference
                model_config = self._resolve_model_reference(task_config, config.models)
                
                # Convert to framework format
                framework_params = self._convert_to_framework_format(task_config, model_config, config)
                
                # Create evaluation task
                eval_task = EvaluationTask(
                    name=task_config.name,
                    task_config=task_config,
                    model_config=model_config,
                    framework_params=framework_params,
                    dependencies=task_config.depends_on.copy()
                )
                
                tasks.append(eval_task)
                self.logger.debug(f"Built task: {task_config.name}")
                
            except Exception as e:
                self.logger.error(f"Failed to build task {task_config.name}: {e}")
                raise ValueError(f"Failed to build task {task_config.name}: {e}")
        
        self.logger.info(f"Successfully built {len(tasks)} tasks")
        return tasks
    
    def resolve_dependencies(self, tasks: List[TaskConfig]) -> List[TaskConfig]:
        """
        Resolve task dependencies and return tasks in dependency order.
        
        Args:
            tasks: List of task configurations
            
        Returns:
            List of tasks ordered by dependencies
            
        Raises:
            ValueError: If circular dependencies are detected
        """
        self.logger.info(f"Resolving dependencies for {len(tasks)} tasks")
        
        # Create dependency graph
        graph = nx.DiGraph()
        task_map = {task.name: task for task in tasks}
        
        # Add nodes
        for task in tasks:
            graph.add_node(task.name)
        
        # Add edges (dependencies)
        for task in tasks:
            for dependency in task.depends_on:
                if dependency not in task_map:
                    raise ValueError(f"Task {task.name} depends on unknown task: {dependency}")
                graph.add_edge(dependency, task.name)
        
        # Check for circular dependencies
        if not nx.is_directed_acyclic_graph(graph):
            cycles = list(nx.simple_cycles(graph))
            raise ValueError(f"Circular dependencies detected: {cycles}")
        
        # Get topological order
        try:
            ordered_names = list(nx.topological_sort(graph))
            ordered_tasks = [task_map[name] for name in ordered_names]
            
            self.logger.info(f"Dependency resolution complete. Execution order: {ordered_names}")
            return ordered_tasks
            
        except nx.NetworkXError as e:
            raise ValueError(f"Failed to resolve dependencies: {e}")
    
    def create_execution_plan(self, tasks: List[EvaluationTask]) -> ExecutionPlan:
        """
        Create an execution plan with dependency-ordered tasks.
        
        Args:
            tasks: List of evaluation tasks
            
        Returns:
            ExecutionPlan with ordered tasks and dependency information
        """
        self.logger.info(f"Creating execution plan for {len(tasks)} tasks")
        
        # Extract task configs for dependency resolution
        task_configs = [task.task_config for task in tasks]
        ordered_configs = self.resolve_dependencies(task_configs)
        
        # Create ordered task list
        task_map = {task.name: task for task in tasks}
        ordered_tasks = [task_map[config.name] for config in ordered_configs]
        
        # Mark all tasks as resolved (dependencies are valid)
        for task in ordered_tasks:
            task.status = DependencyStatus.RESOLVED
        
        # Build dependency graph for execution plan
        dependency_graph = {}
        for task in ordered_tasks:
            dependency_graph[task.name] = task.dependencies.copy()
        
        execution_order = [task.name for task in ordered_tasks]
        
        plan = ExecutionPlan(
            tasks=ordered_tasks,
            execution_order=execution_order,
            dependency_graph=dependency_graph
        )
        
        self.logger.info(f"Execution plan created with order: {execution_order}")
        return plan
    
    def convert_to_framework_format(self, task_config: TaskConfig, model_config: ModelConfig, 
                                  eval_config: EvaluationConfig) -> Dict[str, Any]:
        """
        Convert task configuration to UnifiedEvaluationFramework format.
        
        Args:
            task_config: Task configuration
            model_config: Associated model configuration
            eval_config: Complete evaluation configuration
            
        Returns:
            Dictionary of parameters compatible with EvaluationRequest
        """
        return self._convert_to_framework_format(task_config, model_config, eval_config)
    
    def _validate_configuration(self, config: EvaluationConfig) -> ValidationResult:
        """Validate configuration for task building."""
        result = ValidationResult(is_valid=True)
        
        # Check that all model references exist
        for task in config.tasks:
            if task.model_ref not in config.models:
                error = ValidationError(
                    type="semantic",
                    message=f"Task '{task.name}' references unknown model '{task.model_ref}'",
                    severity=ValidationSeverity.ERROR,
                    location=f"tasks.{task.name}.model_ref"
                )
                result.add_error(error)
        
        # Check for duplicate task names
        task_names = [task.name for task in config.tasks]
        duplicates = set([name for name in task_names if task_names.count(name) > 1])
        for duplicate in duplicates:
            error = ValidationError(
                type="semantic",
                message=f"Duplicate task name: '{duplicate}'",
                severity=ValidationSeverity.ERROR,
                location="tasks"
            )
            result.add_error(error)
        
        return result
    
    def _resolve_model_reference(self, task_config: TaskConfig, 
                               models: Dict[str, ModelConfig]) -> ModelConfig:
        """Resolve model reference in task configuration."""
        if task_config.model_ref not in models:
            raise ValueError(f"Model reference '{task_config.model_ref}' not found in models")
        
        return models[task_config.model_ref]
    
    def _convert_to_framework_format(self, task_config: TaskConfig, model_config: ModelConfig,
                                   eval_config: EvaluationConfig) -> Dict[str, Any]:
        """
        Convert configuration to UnifiedEvaluationFramework parameters.
        
        This method maps configuration parameters to the format expected by
        EvaluationRequest, ensuring compatibility with the existing framework.
        """
        # Start with model configuration
        framework_params = {
            "model": self._build_model_identifier(model_config),
            "tasks": [task_config.task_name],
            "description": task_config.description
        }
        
        # Add task-specific parameters
        if task_config.num_fewshot is not None:
            framework_params["num_fewshot"] = task_config.num_fewshot
        elif eval_config.defaults and eval_config.defaults.num_fewshot is not None:
            framework_params["num_fewshot"] = eval_config.defaults.num_fewshot
        
        if task_config.batch_size is not None:
            framework_params["batch_size"] = task_config.batch_size
        elif eval_config.defaults and eval_config.defaults.batch_size is not None:
            framework_params["batch_size"] = eval_config.defaults.batch_size
        
        # Start with model parameters as generation kwargs
        gen_kwargs = {}
        if model_config.parameters:
            gen_kwargs.update(model_config.parameters)
        
        # Add task-specific configuration (overrides model parameters)
        if task_config.task_config:
            # Handle task-specific parameters
            if "limit" in task_config.task_config:
                framework_params["limit"] = task_config.task_config["limit"]
            
            # Add generation parameters if present (these override model parameters)
            for key in ["temperature", "max_tokens", "top_p", "top_k"]:
                if key in task_config.task_config:
                    gen_kwargs[key] = task_config.task_config[key]
        
        # Set gen_kwargs if we have any
        if gen_kwargs:
            framework_params["gen_kwargs"] = gen_kwargs
        
        # Add output configuration
        if eval_config.output:
            if eval_config.output.directory:
                framework_params["output_base_path"] = eval_config.output.directory
            
            # Enable sample logging if raw responses are requested
            if eval_config.output.include_raw_responses:
                framework_params["log_samples"] = True
        
        # Set default values for framework compatibility
        framework_params.setdefault("use_cache", True)
        framework_params.setdefault("verbosity", "INFO")
        framework_params.setdefault("random_seed", 0)
        framework_params.setdefault("numpy_random_seed", 1234)
        framework_params.setdefault("torch_random_seed", 1234)
        framework_params.setdefault("fewshot_random_seed", 1234)
        
        return framework_params
    
    def _build_model_identifier(self, model_config: ModelConfig) -> str:
        """
        Build model identifier for the framework.
        
        For now, this returns the model_name directly. In the future,
        this could be enhanced to handle different model types and
        create appropriate model instances.
        """
        return model_config.model_name
    
    def validate_task_dependencies(self, tasks: List[TaskConfig]) -> Tuple[bool, List[str]]:
        """
        Validate task dependencies without resolving them.
        
        Args:
            tasks: List of task configurations
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        task_names = {task.name for task in tasks}
        
        # Check that all dependencies exist
        for task in tasks:
            for dependency in task.depends_on:
                if dependency not in task_names:
                    errors.append(f"Task '{task.name}' depends on unknown task '{dependency}'")
        
        # Check for circular dependencies
        try:
            self.resolve_dependencies(tasks)
        except ValueError as e:
            if "Circular dependencies" in str(e):
                errors.append(str(e))
        
        return len(errors) == 0, errors