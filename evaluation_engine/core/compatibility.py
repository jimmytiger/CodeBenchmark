"""
Backward Compatibility Layer for AI Evaluation Engine

This module ensures that the extended evaluation engine maintains full
backward compatibility with existing lm-eval tasks, models, and workflows
while providing enhanced functionality.
"""

import logging
import time
import warnings
from typing import Any, Dict, List, Optional, Type, Union
from functools import wraps

from lm_eval.api.task import Task, TaskConfig
from lm_eval.api.model import LM
from lm_eval.api.instance import Instance

from .extended_tasks import AdvancedTask, ExtendedTaskConfig, ScenarioConfig, ScenarioType
from .model_adapters import ModelAdapter, ModelType, ModelCapabilities, RateLimitConfig


eval_logger = logging.getLogger(__name__)


class CompatibilityWarning(UserWarning):
    """Warning for compatibility issues."""
    pass


def deprecated(reason: str):
    """Decorator to mark functions as deprecated."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated: {reason}",
                CompatibilityWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


class LegacyTaskWrapper(AdvancedTask):
    """
    Wrapper for legacy lm-eval tasks to support extended functionality.
    
    This wrapper allows existing lm-eval tasks to work with the extended
    evaluation engine without modification while providing access to
    enhanced features when needed.
    """
    
    def __init__(self, legacy_task: Task, extended_config: Optional[ExtendedTaskConfig] = None):
        """Initialize wrapper with legacy task."""
        self.legacy_task = legacy_task
        
        # Convert legacy config to extended config
        if extended_config:
            config = extended_config
        else:
            config = self._convert_legacy_config(legacy_task.config)
        
        # Initialize AdvancedTask without calling legacy task's __init__
        super(Task, self).__init__()
        self._config = config
        self.scenario_config = None
        self._conversation_history = []
        self._current_turn = 0
        
        # Copy attributes from legacy task
        self.dataset = getattr(legacy_task, 'dataset', None)
        self._training_docs = getattr(legacy_task, '_training_docs', None)
        self._fewshot_docs = getattr(legacy_task, '_fewshot_docs', None)
        self._instances = getattr(legacy_task, '_instances', None)
    
    def _convert_legacy_config(self, legacy_config: TaskConfig) -> ExtendedTaskConfig:
        """Convert legacy TaskConfig to ExtendedTaskConfig."""
        # Extract base config as dict
        base_config = legacy_config.to_dict() if hasattr(legacy_config, 'to_dict') else {}
        
        # Add default extended fields
        extended_fields = {
            'context_mode': 'full_context',
            'difficulty_level': 'intermediate',
            'supported_languages': ['python'],
            'max_turns': 1,
            'conversation_timeout': 300,
            'enable_context_retention': False,
            'custom_metrics': [],
            'composite_metrics': {},
            'security_analysis_enabled': False,
            'code_execution_enabled': False,
            'sandbox_config': {},
            'domain': None,
            'domain_knowledge_base': None
        }
        
        # Merge configurations
        merged_config = {**base_config, **extended_fields}
        
        return ExtendedTaskConfig(**merged_config)
    
    # Delegate methods to legacy task
    def has_training_docs(self) -> bool:
        """Delegate to legacy task."""
        return self.legacy_task.has_training_docs()
    
    def has_validation_docs(self) -> bool:
        """Delegate to legacy task."""
        return self.legacy_task.has_validation_docs()
    
    def has_test_docs(self) -> bool:
        """Delegate to legacy task."""
        return self.legacy_task.has_test_docs()
    
    def training_docs(self):
        """Delegate to legacy task."""
        return self.legacy_task.training_docs()
    
    def validation_docs(self):
        """Delegate to legacy task."""
        return self.legacy_task.validation_docs()
    
    def test_docs(self):
        """Delegate to legacy task."""
        return self.legacy_task.test_docs()
    
    def doc_to_text(self, doc):
        """Delegate to legacy task with enhanced context if available."""
        if hasattr(self.legacy_task, 'doc_to_text'):
            return self.legacy_task.doc_to_text(doc)
        return str(doc)
    
    def doc_to_target(self, doc):
        """Delegate to legacy task."""
        if hasattr(self.legacy_task, 'doc_to_target'):
            return self.legacy_task.doc_to_target(doc)
        return None
    
    def process_results(self, doc, results):
        """Delegate to legacy task."""
        if hasattr(self.legacy_task, 'process_results'):
            return self.legacy_task.process_results(doc, results)
        return results
    
    def aggregation(self):
        """Delegate to legacy task."""
        if hasattr(self.legacy_task, 'aggregation'):
            return self.legacy_task.aggregation()
        return {}
    
    def higher_is_better(self):
        """Delegate to legacy task."""
        if hasattr(self.legacy_task, 'higher_is_better'):
            return self.legacy_task.higher_is_better()
        return {}
    
    # Enhanced functionality
    def supports_multi_turn(self) -> bool:
        """Legacy tasks don't support multi-turn by default."""
        return False
    
    def get_context_modes(self) -> List[str]:
        """Return supported context modes."""
        return ['full_context']  # Default for legacy tasks
    
    def validate_scenario_config(self, config: Dict[str, Any]) -> bool:
        """Accept all configurations for legacy tasks."""
        return True
    
    def process_advanced_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """No advanced metrics for legacy tasks."""
        return {}


class LegacyModelWrapper(ModelAdapter):
    """
    Wrapper for legacy lm-eval models to support extended functionality.
    
    This wrapper allows existing lm-eval models to work with the extended
    evaluation engine while providing enhanced features like rate limiting
    and performance monitoring.
    """
    
    def __init__(self, legacy_model: LM, model_id: Optional[str] = None):
        """Initialize wrapper with legacy model."""
        self.legacy_model = legacy_model
        
        # Determine model type and capabilities
        model_type = self._detect_model_type(legacy_model)
        capabilities = self._detect_model_capabilities(legacy_model)
        
        # Initialize ModelAdapter
        super().__init__(
            model_id=model_id or self._get_model_id(legacy_model),
            model_type=model_type,
            rate_limit_config=RateLimitConfig(),  # Default rate limiting
            model_kwargs={}
        )
        
        self.capabilities = capabilities
    
    def _detect_model_type(self, model: LM) -> ModelType:
        """Detect model type from legacy model."""
        model_class_name = model.__class__.__name__.lower()
        
        if 'openai' in model_class_name or 'gpt' in model_class_name:
            return ModelType.OPENAI
        elif 'anthropic' in model_class_name or 'claude' in model_class_name:
            return ModelType.ANTHROPIC
        elif 'huggingface' in model_class_name or 'hf' in model_class_name:
            return ModelType.HUGGINGFACE
        elif 'local' in model_class_name:
            return ModelType.LOCAL
        else:
            return ModelType.CUSTOM
    
    def _detect_model_capabilities(self, model: LM) -> ModelCapabilities:
        """Detect model capabilities from legacy model."""
        # Default capabilities - can be enhanced based on model inspection
        return ModelCapabilities(
            max_context_length=4096,
            max_output_length=2048,
            supports_function_calling=False,
            supports_streaming=False,
            supports_chat_templates=hasattr(model, 'apply_chat_template'),
            supports_system_messages=True,
            supports_multimodal=False,
            supported_languages=["en"]
        )
    
    def _get_model_id(self, model: LM) -> str:
        """Get model ID from legacy model."""
        if hasattr(model, 'model_id'):
            return model.model_id
        elif hasattr(model, 'model_name'):
            return model.model_name
        else:
            return model.__class__.__name__
    
    def _get_model_capabilities(self) -> ModelCapabilities:
        """Return detected capabilities."""
        return self.capabilities
    
    # Delegate core methods to legacy model
    def loglikelihood(self, requests) -> List[tuple[float, bool]]:
        """Delegate to legacy model with monitoring."""
        try:
            start_time = time.time()
            result = self.legacy_model.loglikelihood(requests)
            response_time = time.time() - start_time
            
            # Update metrics
            self.metrics.update_request(True, 0, response_time, 0.0)
            
            return result
        except Exception as e:
            self.metrics.update_request(False)
            raise
    
    def loglikelihood_rolling(self, requests) -> List[float]:
        """Delegate to legacy model with monitoring."""
        try:
            start_time = time.time()
            result = self.legacy_model.loglikelihood_rolling(requests)
            response_time = time.time() - start_time
            
            # Update metrics
            self.metrics.update_request(True, 0, response_time, 0.0)
            
            return result
        except Exception as e:
            self.metrics.update_request(False)
            raise
    
    def generate_until(self, requests) -> List[str]:
        """Delegate to legacy model with monitoring."""
        try:
            start_time = time.time()
            result = self.legacy_model.generate_until(requests)
            response_time = time.time() - start_time
            
            # Estimate token usage
            total_tokens = sum(len(response.split()) for response in result)
            
            # Update metrics
            self.metrics.update_request(True, total_tokens, response_time, 0.0)
            
            return result
        except Exception as e:
            self.metrics.update_request(False)
            raise
    
    def apply_chat_template(self, chat_history: List[Dict[str, str]], add_generation_prompt=True) -> str:
        """Delegate to legacy model if supported."""
        if hasattr(self.legacy_model, 'apply_chat_template'):
            return self.legacy_model.apply_chat_template(chat_history, add_generation_prompt)
        else:
            # Fallback implementation
            formatted_messages = []
            for message in chat_history:
                role = message.get('role', 'user')
                content = message.get('content', '')
                formatted_messages.append(f"{role}: {content}")
            
            result = "\n".join(formatted_messages)
            if add_generation_prompt:
                result += "\nassistant:"
            
            return result


class CompatibilityManager:
    """
    Manages compatibility between legacy and extended components.
    
    This class provides utilities for converting between legacy and extended
    formats, detecting compatibility issues, and providing migration guidance.
    """
    
    def __init__(self):
        self._wrapped_tasks: Dict[str, LegacyTaskWrapper] = {}
        self._wrapped_models: Dict[str, LegacyModelWrapper] = {}
    
    def wrap_legacy_task(self, task: Task, task_name: Optional[str] = None) -> LegacyTaskWrapper:
        """Wrap a legacy task for use with extended engine."""
        task_name = task_name or getattr(task, '__class__.__name__', 'unknown_task')
        
        if task_name not in self._wrapped_tasks:
            wrapped_task = LegacyTaskWrapper(task)
            self._wrapped_tasks[task_name] = wrapped_task
            eval_logger.info(f"Wrapped legacy task: {task_name}")
        
        return self._wrapped_tasks[task_name]
    
    def wrap_legacy_model(self, model: LM, model_id: Optional[str] = None) -> LegacyModelWrapper:
        """Wrap a legacy model for use with extended engine."""
        model_id = model_id or getattr(model, '__class__.__name__', 'unknown_model')
        
        if model_id not in self._wrapped_models:
            wrapped_model = LegacyModelWrapper(model, model_id)
            self._wrapped_models[model_id] = wrapped_model
            eval_logger.info(f"Wrapped legacy model: {model_id}")
        
        return self._wrapped_models[model_id]
    
    def convert_legacy_config(self, legacy_config: Union[Dict[str, Any], TaskConfig]) -> ExtendedTaskConfig:
        """Convert legacy configuration to extended format."""
        if isinstance(legacy_config, TaskConfig):
            base_config = legacy_config.to_dict()
        else:
            base_config = legacy_config.copy()
        
        # Add extended fields with defaults
        extended_fields = {
            'context_mode': 'full_context',
            'difficulty_level': 'intermediate',
            'supported_languages': ['python'],
            'max_turns': 1,
            'conversation_timeout': 300,
            'enable_context_retention': False,
            'custom_metrics': [],
            'composite_metrics': {},
            'security_analysis_enabled': False,
            'code_execution_enabled': False,
            'sandbox_config': {},
            'domain': None,
            'domain_knowledge_base': None
        }
        
        # Merge configurations
        merged_config = {**base_config, **extended_fields}
        
        return ExtendedTaskConfig(**merged_config)
    
    def check_compatibility(self, component: Any) -> Dict[str, Any]:
        """Check compatibility of a component with extended engine."""
        compatibility_report = {
            'compatible': True,
            'issues': [],
            'recommendations': [],
            'component_type': type(component).__name__
        }
        
        # Check if it's a legacy task
        if isinstance(component, Task) and not isinstance(component, AdvancedTask):
            compatibility_report['recommendations'].append(
                "Consider wrapping with LegacyTaskWrapper for enhanced functionality"
            )
        
        # Check if it's a legacy model
        if isinstance(component, LM) and not isinstance(component, ModelAdapter):
            compatibility_report['recommendations'].append(
                "Consider wrapping with LegacyModelWrapper for enhanced functionality"
            )
        
        # Check for deprecated methods
        deprecated_methods = ['old_method_name']  # Add actual deprecated methods
        for method_name in deprecated_methods:
            if hasattr(component, method_name):
                compatibility_report['issues'].append(
                    f"Uses deprecated method: {method_name}"
                )
        
        return compatibility_report
    
    def migrate_task_config(self, legacy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate legacy task configuration to extended format."""
        migrated_config = legacy_config.copy()
        
        # Handle metric format changes
        if 'metric' in migrated_config and isinstance(migrated_config['metric'], str):
            migrated_config['metric_list'] = [{'metric': migrated_config.pop('metric')}]
        
        # Handle output type changes
        if 'output_type' in migrated_config:
            output_type = migrated_config['output_type']
            if output_type == 'acc':
                migrated_config['output_type'] = 'loglikelihood'
                migrated_config['metric_list'] = [{'metric': 'accuracy'}]
        
        # Add extended fields
        extended_defaults = {
            'context_mode': 'full_context',
            'difficulty_level': 'intermediate',
            'supported_languages': ['python']
        }
        
        for key, default_value in extended_defaults.items():
            if key not in migrated_config:
                migrated_config[key] = default_value
        
        return migrated_config
    
    def get_migration_guide(self, component_type: str) -> str:
        """Get migration guide for a component type."""
        guides = {
            'task': """
            Migration Guide for Tasks:
            1. Inherit from AdvancedTask instead of Task
            2. Update configuration to use ExtendedTaskConfig
            3. Implement extended methods for enhanced functionality
            4. Consider adding multi-turn support if applicable
            """,
            'model': """
            Migration Guide for Models:
            1. Inherit from ModelAdapter instead of LM
            2. Implement rate limiting and monitoring
            3. Add model capabilities definition
            4. Consider plugin architecture for custom models
            """,
            'metric': """
            Migration Guide for Metrics:
            1. Use new metric plugin system
            2. Implement MetricPlugin interface
            3. Add metadata and configuration support
            4. Consider composite metrics for complex evaluations
            """
        }
        
        return guides.get(component_type, "No migration guide available for this component type.")


# Global compatibility manager
compatibility_manager = CompatibilityManager()


# Utility functions for backward compatibility
def ensure_compatibility(func):
    """Decorator to ensure function maintains backward compatibility."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log compatibility issue
            eval_logger.warning(f"Compatibility issue in {func.__name__}: {e}")
            # Try to provide fallback behavior
            return None
    return wrapper


def convert_legacy_task(task: Task) -> AdvancedTask:
    """Convert a legacy task to an advanced task."""
    return compatibility_manager.wrap_legacy_task(task)


def convert_legacy_model(model: LM) -> ModelAdapter:
    """Convert a legacy model to a model adapter."""
    return compatibility_manager.wrap_legacy_model(model)


@deprecated("Use ExtendedTaskConfig instead")
def create_legacy_config(**kwargs) -> TaskConfig:
    """Create a legacy task configuration (deprecated)."""
    return TaskConfig(**kwargs)


# Version compatibility checks
def check_lm_eval_version() -> bool:
    """Check if lm-eval version is compatible."""
    try:
        import lm_eval
        version = getattr(lm_eval, '__version__', '0.0.0')
        # Add version compatibility logic here
        return True
    except ImportError:
        eval_logger.error("lm-eval not found")
        return False


def get_compatibility_info() -> Dict[str, Any]:
    """Get comprehensive compatibility information."""
    return {
        'lm_eval_compatible': check_lm_eval_version(),
        'wrapped_tasks': len(compatibility_manager._wrapped_tasks),
        'wrapped_models': len(compatibility_manager._wrapped_models),
        'supported_features': [
            'legacy_task_wrapping',
            'legacy_model_wrapping',
            'config_migration',
            'backward_compatibility'
        ]
    }