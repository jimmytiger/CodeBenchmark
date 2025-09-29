"""
Configuration-Driven Evaluator for evaluation_engine.

This module provides the main entry point for configuration-driven evaluation,
integrating configuration parsing, validation, task building, and execution.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import traceback

from .models import (
    EvaluationConfig, ValidationResult, ValidationError, 
    ValidationSeverity, ConfigMetadata
)
from .parser import ConfigParser
from .validator import ConfigValidator
from .builder import TaskBuilder, EvaluationTask, ExecutionPlan, DependencyStatus
from ..core.unified_framework import UnifiedEvaluationFramework, EvaluationResult, ExecutionStatus

logger = logging.getLogger(__name__)


@dataclass
class BatchExecutionResult:
    """Result of batch task execution."""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    execution_time: float
    task_results: Dict[str, EvaluationResult] = field(default_factory=dict)
    task_errors: Dict[str, str] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100.0
    
    @property
    def is_successful(self) -> bool:
        """Check if batch execution was successful (all tasks completed)."""
        return self.failed_tasks == 0 and self.completed_tasks == self.total_tasks


@dataclass
class ConfigDrivenEvaluationResult:
    """Complete result of configuration-driven evaluation."""
    config_metadata: ConfigMetadata
    validation_result: ValidationResult
    batch_result: BatchExecutionResult
    start_time: datetime
    end_time: datetime
    config_path: Optional[str] = None
    
    @property
    def total_execution_time(self) -> float:
        """Total execution time in seconds."""
        return (self.end_time - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "config_metadata": {
                "name": self.config_metadata.name,
                "version": self.config_metadata.version,
                "author": self.config_metadata.author,
                "description": self.config_metadata.description
            },
            "validation": {
                "is_valid": self.validation_result.is_valid,
                "errors": [str(error) for error in self.validation_result.errors],
                "warnings": [str(warning) for warning in self.validation_result.warnings]
            },
            "execution": {
                "total_tasks": self.batch_result.total_tasks,
                "completed_tasks": self.batch_result.completed_tasks,
                "failed_tasks": self.batch_result.failed_tasks,
                "skipped_tasks": self.batch_result.skipped_tasks,
                "success_rate": self.batch_result.success_rate,
                "execution_time": self.batch_result.execution_time,
                "execution_order": self.batch_result.execution_order
            },
            "timing": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "total_execution_time": self.total_execution_time
            },
            "config_path": self.config_path,
            "task_summaries": self._generate_task_summaries()
        }
    
    def _generate_task_summaries(self) -> Dict[str, Dict[str, Any]]:
        """Generate summary information for each task."""
        summaries = {}
        
        for task_name, result in self.batch_result.task_results.items():
            summaries[task_name] = {
                "status": result.status.value,
                "execution_time": result.end_time.timestamp() - result.start_time.timestamp() if result.end_time else 0,
                "metrics_summary": result.metrics_summary or {},
                "error": result.error
            }
        
        # Add error information for failed tasks
        for task_name, error in self.batch_result.task_errors.items():
            if task_name not in summaries:
                summaries[task_name] = {
                    "status": "failed",
                    "execution_time": 0,
                    "metrics_summary": {},
                    "error": error
                }
        
        return summaries


class ConfigDrivenEvaluator:
    """
    Main entry point for configuration-driven evaluation.
    
    This class integrates configuration parsing, validation, task building,
    and execution to provide a complete configuration-driven evaluation workflow.
    """
    
    def __init__(self, framework: Optional[UnifiedEvaluationFramework] = None):
        """
        Initialize ConfigDrivenEvaluator.
        
        Args:
            framework: UnifiedEvaluationFramework instance. If None, creates a new one.
        """
        self.framework = framework or UnifiedEvaluationFramework()
        self.parser = ConfigParser()
        self.validator = ConfigValidator()
        self.builder = TaskBuilder(self.framework)
        self.logger = logging.getLogger(__name__)
        
        # Execution state
        self._current_execution: Optional[ConfigDrivenEvaluationResult] = None
        self._execution_callbacks: List[Callable[[str, Any], None]] = []
    
    def run_from_config(self, config_path: str, 
                       task_filter: Optional[List[str]] = None,
                       parameter_overrides: Optional[Dict[str, Any]] = None,
                       fail_fast: bool = False,
                       dry_run: bool = False) -> ConfigDrivenEvaluationResult:
        """
        Run evaluation from configuration file.
        
        Args:
            config_path: Path to configuration file
            task_filter: Optional list of task names to execute (executes only these tasks)
            parameter_overrides: Optional parameter overrides
            fail_fast: If True, stop execution on first task failure
            dry_run: If True, validate and build tasks but don't execute
            
        Returns:
            ConfigDrivenEvaluationResult with complete execution results
            
        Raises:
            ValueError: If configuration is invalid
            FileNotFoundError: If configuration file doesn't exist
            RuntimeError: If execution fails
        """
        start_time = datetime.now()
        self.logger.info(f"Starting configuration-driven evaluation from: {config_path}")
        
        try:
            # Step 1: Parse configuration
            self.logger.info("Parsing configuration file...")
            config = self.parser.parse_config(config_path)
            
            # Apply parameter overrides if provided
            if parameter_overrides:
                config = self._apply_parameter_overrides(config, parameter_overrides)
            
            # Step 2: Validate configuration
            self.logger.info("Validating configuration...")
            validation_result = self.validator.validate_config(config)
            
            if not validation_result.is_valid:
                error_messages = [str(error) for error in validation_result.errors]
                raise ValueError(f"Configuration validation failed: {'; '.join(error_messages)}")
            
            # Log warnings if any
            if validation_result.has_warnings():
                for warning in validation_result.warnings:
                    self.logger.warning(f"Configuration warning: {warning}")
            
            # Step 3: Build tasks
            self.logger.info("Building evaluation tasks...")
            tasks = self.builder.build_tasks(config)
            
            # Filter tasks if requested
            if task_filter:
                tasks = [task for task in tasks if task.name in task_filter]
                self.logger.info(f"Filtered to {len(tasks)} tasks: {[task.name for task in tasks]}")
            
            # Step 4: Create execution plan
            execution_plan = self.builder.create_execution_plan(tasks)
            self.logger.info(f"Created execution plan with {len(execution_plan.tasks)} tasks")
            
            # Step 5: Execute tasks (unless dry run)
            if dry_run:
                self.logger.info("Dry run mode - skipping task execution")
                batch_result = BatchExecutionResult(
                    total_tasks=len(tasks),
                    completed_tasks=0,
                    failed_tasks=0,
                    skipped_tasks=len(tasks),
                    execution_time=0.0,
                    execution_order=[task.name for task in execution_plan.tasks]
                )
            else:
                self.logger.info("Executing tasks...")
                batch_result = self._execute_batch_tasks(execution_plan, fail_fast)
            
            # Step 6: Create final result
            end_time = datetime.now()
            result = ConfigDrivenEvaluationResult(
                config_metadata=config.metadata,
                validation_result=validation_result,
                batch_result=batch_result,
                start_time=start_time,
                end_time=end_time,
                config_path=config_path
            )
            
            self._current_execution = result
            
            # Log summary
            self._log_execution_summary(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Configuration-driven evaluation failed: {e}")
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
            
            # Create error result
            end_time = datetime.now()
            error_batch_result = BatchExecutionResult(
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=1,
                skipped_tasks=0,
                execution_time=(end_time - start_time).total_seconds()
            )
            
            # Create minimal validation result for error case
            error_validation = ValidationResult(is_valid=False)
            error_validation.add_error(ValidationError(
                type="runtime",
                message=str(e),
                severity=ValidationSeverity.ERROR
            ))
            
            # Create minimal metadata for error case
            error_metadata = ConfigMetadata(name="failed_evaluation")
            
            error_result = ConfigDrivenEvaluationResult(
                config_metadata=error_metadata,
                validation_result=error_validation,
                batch_result=error_batch_result,
                start_time=start_time,
                end_time=end_time,
                config_path=config_path
            )
            
            self._current_execution = error_result
            raise RuntimeError(f"Configuration-driven evaluation failed: {e}") from e
    
    def run_from_config_dict(self, config_dict: Dict[str, Any],
                           task_filter: Optional[List[str]] = None,
                           parameter_overrides: Optional[Dict[str, Any]] = None,
                           fail_fast: bool = False,
                           dry_run: bool = False) -> ConfigDrivenEvaluationResult:
        """
        Run evaluation from configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary
            task_filter: Optional list of task names to execute
            parameter_overrides: Optional parameter overrides
            fail_fast: If True, stop execution on first task failure
            dry_run: If True, validate and build tasks but don't execute
            
        Returns:
            ConfigDrivenEvaluationResult with complete execution results
        """
        start_time = datetime.now()
        self.logger.info("Starting configuration-driven evaluation from dictionary")
        
        try:
            # Parse configuration from dictionary
            config = self.parser._parse_raw_config(config_dict)
            
            # Apply parameter overrides if provided
            if parameter_overrides:
                config = self._apply_parameter_overrides(config, parameter_overrides)
            
            # Continue with validation and execution (same as file-based)
            validation_result = self.validator.validate_config(config)
            
            if not validation_result.is_valid:
                error_messages = [str(error) for error in validation_result.errors]
                raise ValueError(f"Configuration validation failed: {'; '.join(error_messages)}")
            
            # Build and execute tasks
            tasks = self.builder.build_tasks(config)
            
            if task_filter:
                tasks = [task for task in tasks if task.name in task_filter]
            
            execution_plan = self.builder.create_execution_plan(tasks)
            
            if dry_run:
                batch_result = BatchExecutionResult(
                    total_tasks=len(tasks),
                    completed_tasks=0,
                    failed_tasks=0,
                    skipped_tasks=len(tasks),
                    execution_time=0.0,
                    execution_order=[task.name for task in execution_plan.tasks]
                )
            else:
                batch_result = self._execute_batch_tasks(execution_plan, fail_fast)
            
            end_time = datetime.now()
            result = ConfigDrivenEvaluationResult(
                config_metadata=config.metadata,
                validation_result=validation_result,
                batch_result=batch_result,
                start_time=start_time,
                end_time=end_time,
                config_path=None  # No file path for dictionary-based config
            )
            
            self._current_execution = result
            self._log_execution_summary(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Configuration-driven evaluation failed: {e}")
            raise RuntimeError(f"Configuration-driven evaluation failed: {e}") from e
    
    def validate_config_file(self, config_path: str) -> ValidationResult:
        """
        Validate configuration file without executing tasks.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            ValidationResult with validation details
        """
        self.logger.info(f"Validating configuration file: {config_path}")
        
        try:
            # Parse configuration
            config = self.parser.parse_config(config_path)
            
            # Validate configuration
            result = self.validator.validate_config(config)
            
            self.logger.info(f"Configuration validation complete. Valid: {result.is_valid}")
            if result.has_errors():
                for error in result.errors:
                    self.logger.error(f"Validation error: {error}")
            if result.has_warnings():
                for warning in result.warnings:
                    self.logger.warning(f"Validation warning: {warning}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            
            # Return error result
            error_result = ValidationResult(is_valid=False)
            error_result.add_error(ValidationError(
                type="runtime",
                message=str(e),
                severity=ValidationSeverity.ERROR,
                location=config_path
            ))
            
            return error_result
    
    def get_current_execution(self) -> Optional[ConfigDrivenEvaluationResult]:
        """Get the current/last execution result."""
        return self._current_execution
    
    def add_execution_callback(self, callback: Callable[[str, Any], None]):
        """
        Add callback for execution events.
        
        Args:
            callback: Function that receives (event_type, event_data)
        """
        self._execution_callbacks.append(callback)
    
    def remove_execution_callback(self, callback: Callable[[str, Any], None]):
        """Remove execution callback."""
        if callback in self._execution_callbacks:
            self._execution_callbacks.remove(callback)
    
    def export_results(self, output_path: str, 
                      result: Optional[ConfigDrivenEvaluationResult] = None) -> bool:
        """
        Export evaluation results to file.
        
        Args:
            output_path: Path to output file
            result: Result to export (uses current execution if None)
            
        Returns:
            True if export successful, False otherwise
        """
        if result is None:
            result = self._current_execution
        
        if result is None:
            self.logger.error("No evaluation result to export")
            return False
        
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Export result
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Results exported to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export results: {e}")
            return False
    
    def _execute_batch_tasks(self, execution_plan: ExecutionPlan, 
                           fail_fast: bool = False) -> BatchExecutionResult:
        """
        Execute batch of tasks according to execution plan.
        
        Args:
            execution_plan: Execution plan with dependency-ordered tasks
            fail_fast: If True, stop on first failure
            
        Returns:
            BatchExecutionResult with execution statistics and results
        """
        start_time = datetime.now()
        completed_tasks: Set[str] = set()
        task_results: Dict[str, EvaluationResult] = {}
        task_errors: Dict[str, str] = {}
        execution_order: List[str] = []
        
        self.logger.info(f"Executing {len(execution_plan.tasks)} tasks in dependency order")
        
        # Execute tasks in dependency order
        remaining_tasks = execution_plan.tasks.copy()
        
        while remaining_tasks:
            # Find tasks that can be executed (all dependencies completed)
            executable_tasks = []
            for task in remaining_tasks:
                if all(dep in completed_tasks for dep in task.dependencies):
                    executable_tasks.append(task)
            
            if not executable_tasks:
                # No tasks can be executed - check for circular dependencies or errors
                remaining_task_names = [task.name for task in remaining_tasks]
                error_msg = f"Cannot execute remaining tasks due to unmet dependencies: {remaining_task_names}"
                self.logger.error(error_msg)
                
                # Mark remaining tasks as failed
                for task in remaining_tasks:
                    task_errors[task.name] = "Unmet dependencies"
                
                break
            
            # Execute available tasks
            for task in executable_tasks:
                self.logger.info(f"Executing task: {task.name}")
                execution_order.append(task.name)
                
                # Notify callbacks
                self._notify_callbacks("task_started", {"task_name": task.name})
                
                try:
                    # Execute the task using the framework
                    eval_request = task.to_evaluation_request()
                    result = self.framework.evaluate(eval_request)
                    
                    if result.status == ExecutionStatus.COMPLETED:
                        task_results[task.name] = result
                        completed_tasks.add(task.name)
                        self.logger.info(f"Task {task.name} completed successfully")
                        
                        # Notify callbacks
                        self._notify_callbacks("task_completed", {
                            "task_name": task.name,
                            "result": result
                        })
                        
                    else:
                        error_msg = result.error or f"Task failed with status: {result.status.value}"
                        task_errors[task.name] = error_msg
                        self.logger.error(f"Task {task.name} failed: {error_msg}")
                        
                        # Notify callbacks
                        self._notify_callbacks("task_failed", {
                            "task_name": task.name,
                            "error": error_msg
                        })
                        
                        if fail_fast:
                            self.logger.info("Fail-fast mode enabled, stopping execution")
                            break
                
                except Exception as e:
                    error_msg = f"Task execution error: {str(e)}"
                    task_errors[task.name] = error_msg
                    self.logger.error(f"Task {task.name} failed with exception: {e}")
                    self.logger.debug(f"Task {task.name} traceback: {traceback.format_exc()}")
                    
                    # Notify callbacks
                    self._notify_callbacks("task_failed", {
                        "task_name": task.name,
                        "error": error_msg
                    })
                    
                    if fail_fast:
                        self.logger.info("Fail-fast mode enabled, stopping execution")
                        break
                
                # Remove executed task from remaining tasks
                remaining_tasks.remove(task)
            
            # If fail_fast and we have errors, stop
            if fail_fast and task_errors:
                # Mark remaining tasks as skipped
                for task in remaining_tasks:
                    task_errors[task.name] = "Skipped due to previous failure (fail-fast mode)"
                break
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        total_tasks = len(execution_plan.tasks)
        completed_count = len(completed_tasks)
        failed_count = len(task_errors)
        skipped_count = total_tasks - completed_count - failed_count
        
        batch_result = BatchExecutionResult(
            total_tasks=total_tasks,
            completed_tasks=completed_count,
            failed_tasks=failed_count,
            skipped_tasks=skipped_count,
            execution_time=execution_time,
            task_results=task_results,
            task_errors=task_errors,
            execution_order=execution_order
        )
        
        self.logger.info(f"Batch execution completed. "
                        f"Total: {total_tasks}, "
                        f"Completed: {completed_count}, "
                        f"Failed: {failed_count}, "
                        f"Skipped: {skipped_count}")
        
        return batch_result
    
    def _apply_parameter_overrides(self, config: EvaluationConfig, 
                                 overrides: Dict[str, Any]) -> EvaluationConfig:
        """
        Apply parameter overrides to configuration.
        
        Args:
            config: Original configuration
            overrides: Parameter overrides
            
        Returns:
            Configuration with overrides applied
        """
        self.logger.info(f"Applying {len(overrides)} parameter overrides")
        
        # Create a copy of the config to avoid modifying the original
        # Note: This is a shallow copy approach - for deep copy we'd need more complex logic
        
        # Apply overrides to variables
        if 'variables' in overrides:
            config.variables.update(overrides['variables'])
        
        # Apply overrides to defaults
        if 'defaults' in overrides and config.defaults:
            defaults_overrides = overrides['defaults']
            if 'num_fewshot' in defaults_overrides:
                config.defaults.num_fewshot = defaults_overrides['num_fewshot']
            if 'batch_size' in defaults_overrides:
                config.defaults.batch_size = defaults_overrides['batch_size']
        
        # Apply overrides to output configuration
        if 'output' in overrides and config.output:
            output_overrides = overrides['output']
            if 'directory' in output_overrides:
                config.output.directory = output_overrides['directory']
            if 'formats' in output_overrides:
                config.output.formats = output_overrides['formats']
        
        # Apply task-specific overrides
        if 'tasks' in overrides:
            task_overrides = overrides['tasks']
            for task in config.tasks:
                if task.name in task_overrides:
                    task_override = task_overrides[task.name]
                    if 'num_fewshot' in task_override:
                        task.num_fewshot = task_override['num_fewshot']
                    if 'batch_size' in task_override:
                        task.batch_size = task_override['batch_size']
        
        return config
    
    def _notify_callbacks(self, event_type: str, event_data: Any):
        """Notify all registered callbacks of an event."""
        for callback in self._execution_callbacks:
            try:
                callback(event_type, event_data)
            except Exception as e:
                self.logger.warning(f"Callback error for event {event_type}: {e}")
    
    def _log_execution_summary(self, result: ConfigDrivenEvaluationResult):
        """Log execution summary."""
        self.logger.info("=" * 60)
        self.logger.info("CONFIGURATION-DRIVEN EVALUATION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Configuration: {result.config_metadata.name}")
        self.logger.info(f"Total execution time: {result.total_execution_time:.2f} seconds")
        self.logger.info(f"Tasks - Total: {result.batch_result.total_tasks}, "
                        f"Completed: {result.batch_result.completed_tasks}, "
                        f"Failed: {result.batch_result.failed_tasks}, "
                        f"Skipped: {result.batch_result.skipped_tasks}")
        self.logger.info(f"Success rate: {result.batch_result.success_rate:.1f}%")
        
        if result.batch_result.task_errors:
            self.logger.info("Failed tasks:")
            for task_name, error in result.batch_result.task_errors.items():
                self.logger.info(f"  - {task_name}: {error}")
        
        if result.validation_result.has_warnings():
            self.logger.info(f"Validation warnings: {len(result.validation_result.warnings)}")
        
        self.logger.info("=" * 60)