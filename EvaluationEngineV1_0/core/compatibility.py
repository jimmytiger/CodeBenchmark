"""
Backward Compatibility Layer

This module provides compatibility wrappers that allow the new multi-turn evaluation engine
to interface with existing evaluation workflows without modification. It includes:
- Configuration adapters that translate between old and new formats
- Bridge classes that interface with existing code
- Compatibility wrappers for existing evaluation workflows

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import json
import logging
import warnings
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import sys
import os

# Import existing evaluation engine components
try:
    from evaluation_engine.config.models import EvaluationConfig as LegacyEvaluationConfig
    from evaluation_engine.config.parser import ConfigParser as LegacyConfigParser
    from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
    from evaluation_engine.core.task_registration import ExtendedTaskRegistry
except ImportError:
    # Fallback for testing or when legacy components are not available
    LegacyEvaluationConfig = None
    LegacyConfigParser = None
    UnifiedEvaluationFramework = None
    ExtendedTaskRegistry = None

# Import lm-eval components
try:
    from lm_eval import evaluator
    from lm_eval.tasks import TaskManager
    from lm_eval.utils import make_table
except ImportError:
    evaluator = None
    TaskManager = None
    make_table = None

# Import new multi-turn components
from .data_models import (
    EvaluationConfig, TaskConfig, ModelConfig, MultiTurnConfig,
    EvaluationResult, TurnResult, AggregatedMetrics
)

# Import orchestrator and registry with fallbacks
try:
    from .orchestrator import MultiTurnOrchestrator
except ImportError:
    MultiTurnOrchestrator = None

try:
    from .unified_task_registry import UnifiedTaskRegistry
except ImportError:
    UnifiedTaskRegistry = None

logger = logging.getLogger(__name__)


@dataclass
class CompatibilityResult:
    """Result of compatibility operation with migration information."""
    success: bool
    result: Any
    warnings: List[str]
    migration_notes: List[str]
    deprecated_features: List[str]


class ConfigurationAdapter:
    """
    Adapter that translates between old and new configuration formats.
    
    Supports bidirectional translation to maintain compatibility with existing
    configuration files while enabling new multi-turn features.
    """
    
    def __init__(self):
        self.format_mappings = {
            # Legacy -> New format mappings
            'model_name': 'model_id',
            'task_name': 'task_id',
            'num_fewshot': 'few_shot_count',
            'batch_size': 'batch_size',
            'output_path': 'output_directory',
            'log_samples': 'save_samples',
            'use_cache': 'enable_caching',
            'device': 'device',
            'limit': 'sample_limit'
        }
        
        self.reverse_mappings = {v: k for k, v in self.format_mappings.items()}
    
    def adapt_legacy_config(self, legacy_config: Dict[str, Any]) -> EvaluationConfig:
        """
        Convert legacy configuration format to new multi-turn format.
        
        Args:
            legacy_config: Configuration in legacy format
            
        Returns:
            EvaluationConfig: Configuration in new format
            
        Raises:
            ValueError: If configuration cannot be adapted
        """
        try:
            adapted_config = {}
            warnings_list = []
            
            # Handle model configuration
            if 'model' in legacy_config:
                model_config = ModelConfig(
                    model_id=legacy_config.get('model', 'default'),
                    model_type='auto',  # Auto-detect model type
                    parameters=legacy_config.get('model_args', {}),
                    device=legacy_config.get('device', 'auto')
                )
                adapted_config['models'] = {'default': model_config}
            
            # Handle task configuration
            if 'tasks' in legacy_config:
                tasks = []
                task_list = legacy_config['tasks']
                if isinstance(task_list, str):
                    task_list = task_list.split(',')
                
                for task_name in task_list:
                    task_config = TaskConfig(
                        task_id=task_name.strip(),
                        task_type='single_turn',  # Default to single-turn
                        model_ref='default',
                        parameters={
                            'num_fewshot': legacy_config.get('num_fewshot', 0),
                            'batch_size': legacy_config.get('batch_size', 1)
                        }
                    )
                    tasks.append(task_config)
                
                adapted_config['tasks'] = tasks
            
            # Handle evaluation settings
            eval_settings = {}
            if 'output_path' in legacy_config:
                eval_settings['output_directory'] = legacy_config['output_path']
            if 'log_samples' in legacy_config:
                eval_settings['save_samples'] = legacy_config['log_samples']
            if 'use_cache' in legacy_config:
                eval_settings['enable_caching'] = legacy_config['use_cache']
            if 'limit' in legacy_config:
                eval_settings['sample_limit'] = legacy_config['limit']
            
            adapted_config['evaluation_settings'] = eval_settings
            
            # Create new configuration object
            new_config = EvaluationConfig(**adapted_config)
            
            if warnings_list:
                for warning in warnings_list:
                    warnings.warn(warning, DeprecationWarning)
            
            return new_config
            
        except Exception as e:
            logger.error(f"Failed to adapt legacy configuration: {e}")
            raise ValueError(f"Configuration adaptation failed: {e}")
    
    def adapt_new_to_legacy(self, new_config: EvaluationConfig) -> Dict[str, Any]:
        """
        Convert new configuration format back to legacy format for compatibility.
        
        Args:
            new_config: Configuration in new format
            
        Returns:
            Dict[str, Any]: Configuration in legacy format
        """
        try:
            legacy_config = {}
            
            # Handle model configuration
            if new_config.models:
                default_model = list(new_config.models.values())[0]
                legacy_config['model'] = default_model.model_type
                legacy_config['model_args'] = default_model.parameters
                if default_model.device:
                    legacy_config['device'] = default_model.device
            
            # Handle task configuration
            if new_config.tasks:
                task_names = [task.task_id for task in new_config.tasks]
                legacy_config['tasks'] = ','.join(task_names)
                
                # Use first task's parameters as defaults
                first_task = new_config.tasks[0]
                if 'num_fewshot' in first_task.parameters:
                    legacy_config['num_fewshot'] = first_task.parameters['num_fewshot']
                if 'batch_size' in first_task.parameters:
                    legacy_config['batch_size'] = first_task.parameters['batch_size']
            
            # Handle evaluation settings
            if hasattr(new_config, 'evaluation_settings') and new_config.evaluation_settings:
                settings = new_config.evaluation_settings
                if 'output_directory' in settings:
                    legacy_config['output_path'] = settings['output_directory']
                if 'save_samples' in settings:
                    legacy_config['log_samples'] = settings['save_samples']
                if 'enable_caching' in settings:
                    legacy_config['use_cache'] = settings['enable_caching']
                if 'sample_limit' in settings:
                    legacy_config['limit'] = settings['sample_limit']
            
            return legacy_config
            
        except Exception as e:
            logger.error(f"Failed to adapt new configuration to legacy: {e}")
            raise ValueError(f"Configuration adaptation failed: {e}")


class LegacyEvaluationBridge:
    """
    Bridge class that interfaces with existing evaluation code without modification.
    
    This class wraps the new multi-turn orchestrator to provide the same interface
    as the existing evaluation engine, ensuring backward compatibility.
    """
    
    def __init__(self):
        self.config_adapter = ConfigurationAdapter()
        self.orchestrator = None
        self.task_registry = None
        self._legacy_framework = None
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize evaluation components with fallbacks."""
        try:
            # Try to initialize new components
            if UnifiedTaskRegistry:
                self.task_registry = UnifiedTaskRegistry()
            
            # Try to initialize legacy framework if available
            if UnifiedEvaluationFramework:
                self._legacy_framework = UnifiedEvaluationFramework()
                
        except Exception as e:
            logger.warning(f"Failed to initialize some components: {e}")
    
    def evaluate(self, 
                 model: str,
                 tasks: Union[str, List[str]],
                 model_args: Optional[Union[str, Dict[str, Any]]] = None,
                 **kwargs) -> CompatibilityResult:
        """
        Main evaluation method that maintains compatibility with existing interface.
        
        Args:
            model: Model identifier
            tasks: Task name(s) to evaluate
            model_args: Model arguments
            **kwargs: Additional evaluation parameters
            
        Returns:
            CompatibilityResult: Evaluation results with compatibility information
        """
        warnings_list = []
        migration_notes = []
        deprecated_features = []
        
        try:
            # Build legacy-style configuration
            legacy_config = {
                'model': model,
                'tasks': tasks,
                'model_args': model_args or {},
                **kwargs
            }
            
            # Check for deprecated features
            deprecated_params = ['write_out', 'check_integrity', 'predict_only']
            for param in deprecated_params:
                if param in kwargs:
                    deprecated_features.append(f"Parameter '{param}' is deprecated")
                    warnings_list.append(f"Parameter '{param}' is deprecated and may be removed in future versions")
            
            # Determine if this is a multi-turn evaluation
            is_multi_turn = self._detect_multi_turn_tasks(tasks)
            
            if is_multi_turn:
                # Use new multi-turn orchestrator
                result = self._evaluate_multi_turn(legacy_config)
                migration_notes.append("Evaluation used new multi-turn orchestrator")
            else:
                # Use legacy single-turn evaluation
                result = self._evaluate_single_turn(legacy_config)
                migration_notes.append("Evaluation used legacy single-turn method")
            
            return CompatibilityResult(
                success=True,
                result=result,
                warnings=warnings_list,
                migration_notes=migration_notes,
                deprecated_features=deprecated_features
            )
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return CompatibilityResult(
                success=False,
                result=None,
                warnings=warnings_list + [f"Evaluation failed: {e}"],
                migration_notes=migration_notes,
                deprecated_features=deprecated_features
            )
    
    def _detect_multi_turn_tasks(self, tasks: Union[str, List[str]]) -> bool:
        """
        Detect if tasks require multi-turn evaluation.
        
        Args:
            tasks: Task name(s)
            
        Returns:
            bool: True if multi-turn evaluation is needed
        """
        if isinstance(tasks, str):
            tasks = [tasks]
        
        multi_turn_indicators = [
            'multi_turn', 'conversation', 'interactive', 'swe_bench',
            'intercode', 'convcode', 'bugs_in_py', 'defects4j'
        ]
        
        for task in tasks:
            task_lower = task.lower()
            if any(indicator in task_lower for indicator in multi_turn_indicators):
                return True
        
        return False
    
    def _evaluate_single_turn(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate using legacy single-turn method.
        
        Args:
            config: Legacy configuration
            
        Returns:
            Dict[str, Any]: Evaluation results
        """
        try:
            # Try to use existing lm-eval if available
            if evaluator and evaluator.simple_evaluate:
                # Convert config to lm-eval format
                lm_eval_args = self._convert_to_lm_eval_args(config)
                
                # Call lm-eval
                results = evaluator.simple_evaluate(**lm_eval_args)
                
                # Add compatibility metadata
                if results:
                    results['_compatibility'] = {
                        'evaluation_method': 'lm_eval',
                        'version': 'legacy',
                        'multi_turn': False
                    }
                
                return results
            
            # Fallback to legacy framework if available
            elif self._legacy_framework:
                return self._legacy_framework.evaluate(config)
            
            else:
                raise RuntimeError("No evaluation backend available")
                
        except Exception as e:
            logger.error(f"Single-turn evaluation failed: {e}")
            raise
    
    def _evaluate_multi_turn(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate using new multi-turn orchestrator.
        
        Args:
            config: Legacy configuration
            
        Returns:
            Dict[str, Any]: Evaluation results
        """
        try:
            # Convert to new configuration format
            new_config = self.config_adapter.adapt_legacy_config(config)
            
            # Initialize orchestrator if needed
            if not self.orchestrator and MultiTurnOrchestrator:
                try:
                    from .policy_engine import PolicyEngine
                    from .feedback_processor import FeedbackProcessor
                    from .safety_guard import SafetyGuard
                    from .metrics_engine import MetricsEngine
                    
                    self.orchestrator = MultiTurnOrchestrator(
                        policy_engine=PolicyEngine(),
                        feedback_processor=FeedbackProcessor(),
                        safety_guard=SafetyGuard(),
                        metrics_engine=MetricsEngine()
                    )
                except ImportError as e:
                    logger.warning(f"Failed to initialize orchestrator: {e}")
                    raise RuntimeError("Multi-turn orchestrator not available")
            
            # Run multi-turn evaluation
            results = self.orchestrator.evaluate_batch(new_config)
            
            # Convert results to legacy format
            legacy_results = self._convert_results_to_legacy_format(results)
            
            # Add compatibility metadata
            legacy_results['_compatibility'] = {
                'evaluation_method': 'multi_turn_orchestrator',
                'version': 'v1.0',
                'multi_turn': True
            }
            
            return legacy_results
            
        except Exception as e:
            logger.error(f"Multi-turn evaluation failed: {e}")
            raise
    
    def _convert_to_lm_eval_args(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert configuration to lm-eval arguments."""
        lm_eval_args = {}
        
        # Direct mappings
        direct_mappings = {
            'model': 'model',
            'tasks': 'tasks',
            'model_args': 'model_args',
            'num_fewshot': 'num_fewshot',
            'batch_size': 'batch_size',
            'device': 'device',
            'output_path': 'output_path',
            'limit': 'limit',
            'use_cache': 'use_cache',
            'log_samples': 'log_samples'
        }
        
        for legacy_key, lm_eval_key in direct_mappings.items():
            if legacy_key in config:
                lm_eval_args[lm_eval_key] = config[legacy_key]
        
        # Handle task manager
        if TaskManager:
            lm_eval_args['task_manager'] = TaskManager()
        
        return lm_eval_args
    
    def _convert_results_to_legacy_format(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Convert new results format to legacy format."""
        if not results:
            return {}
        
        # Aggregate results
        legacy_results = {
            'results': {},
            'configs': {},
            'versions': {},
            'n-shot': {},
            'samples': {},
            'config': {
                'model': 'multi_turn_model',
                'model_args': {},
                'batch_sizes': [],
                'device': 'auto',
                'use_cache': False,
                'limit': None,
                'bootstrap_iters': 100000,
                'gen_kwargs': {}
            }
        }
        
        for result in results:
            task_id = result.task_id
            
            # Convert metrics to legacy format
            if result.aggregated_metrics:
                metrics = asdict(result.aggregated_metrics)
                legacy_results['results'][task_id] = {
                    'acc': metrics.get('resolved_percentage', 0.0),
                    'acc_stderr': 0.0,  # Not calculated in multi-turn
                    'turns': metrics.get('avg_turns', 0),
                    'steps': metrics.get('avg_steps', 0),
                    'cost': metrics.get('cost_per_solved', 0.0),
                    'wall_time': metrics.get('wall_time_per_solved', 0.0)
                }
            
            # Add configuration
            legacy_results['configs'][task_id] = {
                'task': task_id,
                'group': 'multi_turn',
                'dataset_path': task_id,
                'training_split': None,
                'validation_split': 'test',
                'test_split': 'test',
                'fewshot_split': None,
                'num_fewshot': 0,
                'metric_list': ['acc', 'turns', 'steps', 'cost', 'wall_time'],
                'output_type': 'multiple_choice',
                'repeats': 1,
                'should_decontaminate': False,
                'metadata': {'version': '1.0'}
            }
            
            # Add version info
            legacy_results['versions'][task_id] = '1.0'
            legacy_results['n-shot'][task_id] = 0
        
        return legacy_results


class DeprecationManager:
    """
    Manages deprecation warnings and migration guidance.
    
    Provides clear guidance on deprecated features and migration paths.
    """
    
    def __init__(self):
        self.deprecated_features = {
            'write_out': {
                'replacement': 'log_samples',
                'version': '2.0',
                'message': 'Use log_samples instead for detailed output'
            },
            'check_integrity': {
                'replacement': 'validation_mode',
                'version': '2.0',
                'message': 'Use validation_mode for integrity checking'
            },
            'predict_only': {
                'replacement': 'evaluation_mode',
                'version': '2.0',
                'message': 'Use evaluation_mode="predict" instead'
            }
        }
    
    def warn_deprecated(self, feature: str, **kwargs):
        """Issue deprecation warning for a feature."""
        if feature in self.deprecated_features:
            info = self.deprecated_features[feature]
            message = f"{feature} is deprecated and will be removed in version {info['version']}. {info['message']}"
            warnings.warn(message, DeprecationWarning, stacklevel=2)
    
    def get_migration_guide(self, feature: str) -> Optional[str]:
        """Get migration guidance for a deprecated feature."""
        if feature in self.deprecated_features:
            info = self.deprecated_features[feature]
            return f"Replace '{feature}' with '{info['replacement']}'. {info['message']}"
        return None


# Compatibility functions that maintain the existing API
def simple_evaluate(model: str,
                   tasks: Union[str, List[str]],
                   model_args: Optional[Union[str, Dict[str, Any]]] = None,
                   **kwargs) -> Dict[str, Any]:
    """
    Backward-compatible evaluation function that maintains the lm-eval interface.
    
    This function provides the same interface as lm_eval.evaluator.simple_evaluate
    but routes to the appropriate evaluation backend (single-turn or multi-turn).
    
    Args:
        model: Model identifier
        tasks: Task name(s) to evaluate
        model_args: Model arguments
        **kwargs: Additional evaluation parameters
        
    Returns:
        Dict[str, Any]: Evaluation results in legacy format
    """
    bridge = LegacyEvaluationBridge()
    result = bridge.evaluate(model, tasks, model_args, **kwargs)
    
    if not result.success:
        raise RuntimeError(f"Evaluation failed: {result.warnings}")
    
    # Issue warnings for deprecated features
    for warning in result.warnings:
        warnings.warn(warning, UserWarning)
    
    return result.result


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration file with automatic format detection and adaptation.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dict[str, Any]: Loaded and adapted configuration
    """
    try:
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Load configuration based on file extension
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        elif config_path.suffix.lower() == '.json':
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            raise ValueError(f"Unsupported configuration format: {config_path.suffix}")
        
        # Adapt configuration if needed
        adapter = ConfigurationAdapter()
        
        # Check if this is a legacy configuration
        if 'model' in config and 'tasks' in config:
            # This looks like a legacy configuration, adapt it
            adapted_config = adapter.adapt_legacy_config(config)
            return asdict(adapted_config)
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise


# Export compatibility interface
__all__ = [
    'ConfigurationAdapter',
    'LegacyEvaluationBridge', 
    'DeprecationManager',
    'CompatibilityResult',
    'simple_evaluate',
    'load_config'
]