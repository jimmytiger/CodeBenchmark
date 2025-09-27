"""
Plugin System Architecture for AI Evaluation Engine

This module provides a comprehensive plugin system that allows for easy
extension of the evaluation engine with custom model adapters, metrics,
and evaluation scenarios while maintaining compatibility with lm-eval.
"""

import abc
import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from .model_adapters import ModelAdapter, plugin_registry
from .extended_tasks import AdvancedTask, MultiTurnTask


eval_logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins supported by the system."""
    MODEL_ADAPTER = "model_adapter"
    TASK = "task"
    METRIC = "metric"
    FILTER = "filter"
    PREPROCESSOR = "preprocessor"
    POSTPROCESSOR = "postprocessor"


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    compatibility: Dict[str, str] = field(default_factory=dict)
    config_schema: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'plugin_type': self.plugin_type.value,
            'dependencies': self.dependencies,
            'requirements': self.requirements,
            'compatibility': self.compatibility,
            'config_schema': self.config_schema
        }


class PluginInterface(abc.ABC):
    """Base interface for all plugins."""
    
    @abc.abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass
    
    @abc.abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize the plugin with configuration."""
        pass
    
    @abc.abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        return True
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for the plugin."""
        return {}


class ModelAdapterPlugin(PluginInterface):
    """Base class for model adapter plugins."""
    
    @abc.abstractmethod
    def create_adapter(self, model_id: str, **kwargs) -> ModelAdapter:
        """Create a model adapter instance."""
        pass
    
    @abc.abstractmethod
    def get_supported_models(self) -> List[str]:
        """Get list of supported model identifiers."""
        pass
    
    def test_connection(self, model_id: str, **kwargs) -> bool:
        """Test connection to the model service."""
        try:
            adapter = self.create_adapter(model_id, **kwargs)
            # Perform a simple test request
            test_requests = [type('TestInstance', (), {'args': ('test', 'test')})()]
            adapter.loglikelihood(test_requests)
            return True
        except Exception as e:
            eval_logger.warning(f"Connection test failed for {model_id}: {e}")
            return False


class TaskPlugin(PluginInterface):
    """Base class for task plugins."""
    
    @abc.abstractmethod
    def create_task(self, config: Dict[str, Any]) -> Union[AdvancedTask, MultiTurnTask]:
        """Create a task instance."""
        pass
    
    @abc.abstractmethod
    def get_supported_scenarios(self) -> List[str]:
        """Get list of supported scenario types."""
        pass
    
    def validate_dataset(self, dataset_path: str) -> bool:
        """Validate dataset format for this task type."""
        return True


class MetricPlugin(PluginInterface):
    """Base class for metric plugins."""
    
    @abc.abstractmethod
    def calculate_metric(self, predictions: List[str], references: List[str], **kwargs) -> float:
        """Calculate the metric value."""
        pass
    
    @abc.abstractmethod
    def get_metric_name(self) -> str:
        """Get the metric name."""
        pass
    
    def is_higher_better(self) -> bool:
        """Whether higher values are better for this metric."""
        return True
    
    def get_aggregation_method(self) -> str:
        """Get the aggregation method for this metric."""
        return "mean"


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""
    
    def __init__(self, plugin_directories: Optional[List[str]] = None):
        """Initialize plugin manager."""
        self.plugin_directories = plugin_directories or []
        self._loaded_plugins: Dict[str, PluginInterface] = {}
        self._plugin_metadata: Dict[str, PluginMetadata] = {}
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        # Add default plugin directories
        self._add_default_plugin_directories()
    
    def _add_default_plugin_directories(self):
        """Add default plugin directories."""
        # Add built-in plugins directory
        builtin_dir = Path(__file__).parent / "plugins"
        if builtin_dir.exists():
            self.plugin_directories.append(str(builtin_dir))
        
        # Add user plugins directory
        user_dir = Path.home() / ".lm_eval" / "plugins"
        if user_dir.exists():
            self.plugin_directories.append(str(user_dir))
        
        # Add environment-specified directory
        env_dir = os.environ.get("LM_EVAL_PLUGINS_DIR")
        if env_dir and Path(env_dir).exists():
            self.plugin_directories.append(env_dir)
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins in plugin directories."""
        discovered_plugins = []
        
        for plugin_dir in self.plugin_directories:
            plugin_path = Path(plugin_dir)
            if not plugin_path.exists():
                continue
            
            # Look for Python files and packages
            for item in plugin_path.iterdir():
                if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
                    plugin_name = item.stem
                    discovered_plugins.append(plugin_name)
                elif item.is_dir() and not item.name.startswith("_"):
                    init_file = item / "__init__.py"
                    if init_file.exists():
                        plugin_name = item.name
                        discovered_plugins.append(plugin_name)
        
        return discovered_plugins
    
    def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Load a specific plugin."""
        if plugin_name in self._loaded_plugins:
            eval_logger.info(f"Plugin {plugin_name} already loaded")
            return True
        
        try:
            # Find and import the plugin module
            plugin_module = self._import_plugin_module(plugin_name)
            if not plugin_module:
                eval_logger.error(f"Could not import plugin module: {plugin_name}")
                return False
            
            # Find the plugin class
            plugin_class = self._find_plugin_class(plugin_module)
            if not plugin_class:
                eval_logger.error(f"Could not find plugin class in module: {plugin_name}")
                return False
            
            # Create plugin instance
            plugin_instance = plugin_class()
            
            # Validate and store metadata
            metadata = plugin_instance.get_metadata()
            if not isinstance(metadata, PluginMetadata):
                eval_logger.error(f"Invalid metadata for plugin: {plugin_name}")
                return False
            
            # Initialize plugin
            plugin_config = config or plugin_instance.get_default_config()
            if not plugin_instance.validate_config(plugin_config):
                eval_logger.error(f"Invalid configuration for plugin: {plugin_name}")
                return False
            
            if not plugin_instance.initialize(plugin_config):
                eval_logger.error(f"Failed to initialize plugin: {plugin_name}")
                return False
            
            # Store plugin
            self._loaded_plugins[plugin_name] = plugin_instance
            self._plugin_metadata[plugin_name] = metadata
            self._plugin_configs[plugin_name] = plugin_config
            
            eval_logger.info(f"Successfully loaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            eval_logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    def _import_plugin_module(self, plugin_name: str):
        """Import a plugin module."""
        for plugin_dir in self.plugin_directories:
            plugin_path = Path(plugin_dir)
            
            # Try as a Python file
            py_file = plugin_path / f"{plugin_name}.py"
            if py_file.exists():
                spec = importlib.util.spec_from_file_location(plugin_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    return module
            
            # Try as a package
            package_dir = plugin_path / plugin_name
            if package_dir.is_dir() and (package_dir / "__init__.py").exists():
                # Add plugin directory to sys.path temporarily
                if str(plugin_path) not in sys.path:
                    sys.path.insert(0, str(plugin_path))
                try:
                    return importlib.import_module(plugin_name)
                finally:
                    if str(plugin_path) in sys.path:
                        sys.path.remove(str(plugin_path))
        
        return None
    
    def _find_plugin_class(self, module) -> Optional[Type[PluginInterface]]:
        """Find the plugin class in a module."""
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, PluginInterface) and 
                obj != PluginInterface and 
                obj.__module__ == module.__name__):
                return obj
        return None
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin."""
        if plugin_name not in self._loaded_plugins:
            eval_logger.warning(f"Plugin {plugin_name} not loaded")
            return False
        
        try:
            plugin = self._loaded_plugins[plugin_name]
            plugin.cleanup()
            
            del self._loaded_plugins[plugin_name]
            del self._plugin_metadata[plugin_name]
            del self._plugin_configs[plugin_name]
            
            eval_logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            eval_logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """Get a loaded plugin instance."""
        return self._loaded_plugins.get(plugin_name)
    
    def list_loaded_plugins(self) -> List[str]:
        """List all loaded plugins."""
        return list(self._loaded_plugins.keys())
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[str]:
        """Get plugins of a specific type."""
        return [
            name for name, metadata in self._plugin_metadata.items()
            if metadata.plugin_type == plugin_type
        ]
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a plugin."""
        return self._plugin_metadata.get(plugin_name)
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin."""
        config = self._plugin_configs.get(plugin_name)
        if self.unload_plugin(plugin_name):
            return self.load_plugin(plugin_name, config)
        return False
    
    def load_all_plugins(self, plugin_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> int:
        """Load all discovered plugins."""
        plugin_configs = plugin_configs or {}
        discovered = self.discover_plugins()
        loaded_count = 0
        
        for plugin_name in discovered:
            config = plugin_configs.get(plugin_name)
            if self.load_plugin(plugin_name, config):
                loaded_count += 1
        
        eval_logger.info(f"Loaded {loaded_count}/{len(discovered)} plugins")
        return loaded_count
    
    def create_model_adapter(self, plugin_name: str, model_id: str, **kwargs) -> Optional[ModelAdapter]:
        """Create a model adapter using a plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin or not isinstance(plugin, ModelAdapterPlugin):
            eval_logger.error(f"Model adapter plugin not found: {plugin_name}")
            return None
        
        try:
            return plugin.create_adapter(model_id, **kwargs)
        except Exception as e:
            eval_logger.error(f"Error creating model adapter: {e}")
            return None
    
    def create_task(self, plugin_name: str, config: Dict[str, Any]) -> Optional[Union[AdvancedTask, MultiTurnTask]]:
        """Create a task using a plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin or not isinstance(plugin, TaskPlugin):
            eval_logger.error(f"Task plugin not found: {plugin_name}")
            return None
        
        try:
            return plugin.create_task(config)
        except Exception as e:
            eval_logger.error(f"Error creating task: {e}")
            return None
    
    def calculate_metric(self, plugin_name: str, predictions: List[str], references: List[str], **kwargs) -> Optional[float]:
        """Calculate a metric using a plugin."""
        plugin = self.get_plugin(plugin_name)
        if not plugin or not isinstance(plugin, MetricPlugin):
            eval_logger.error(f"Metric plugin not found: {plugin_name}")
            return None
        
        try:
            return plugin.calculate_metric(predictions, references, **kwargs)
        except Exception as e:
            eval_logger.error(f"Error calculating metric: {e}")
            return None


class PluginValidator:
    """Validates plugin implementations and configurations."""
    
    @staticmethod
    def validate_plugin_class(plugin_class: Type[PluginInterface]) -> List[str]:
        """Validate a plugin class implementation."""
        issues = []
        
        # Check if it inherits from PluginInterface
        if not issubclass(plugin_class, PluginInterface):
            issues.append("Plugin must inherit from PluginInterface")
        
        # Check required methods
        required_methods = ['get_metadata', 'initialize', 'cleanup']
        for method_name in required_methods:
            if not hasattr(plugin_class, method_name):
                issues.append(f"Missing required method: {method_name}")
        
        # Check metadata method
        try:
            instance = plugin_class()
            metadata = instance.get_metadata()
            if not isinstance(metadata, PluginMetadata):
                issues.append("get_metadata() must return PluginMetadata instance")
        except Exception as e:
            issues.append(f"Error calling get_metadata(): {e}")
        
        return issues
    
    @staticmethod
    def validate_plugin_metadata(metadata: PluginMetadata) -> List[str]:
        """Validate plugin metadata."""
        issues = []
        
        # Check required fields
        if not metadata.name:
            issues.append("Plugin name is required")
        if not metadata.version:
            issues.append("Plugin version is required")
        if not metadata.description:
            issues.append("Plugin description is required")
        if not metadata.author:
            issues.append("Plugin author is required")
        
        # Validate version format (basic check)
        if metadata.version and not metadata.version.replace('.', '').replace('-', '').isalnum():
            issues.append("Invalid version format")
        
        return issues


# Global plugin manager instance
plugin_manager = PluginManager()


def register_plugin(plugin_type: PluginType, metadata: Optional[Dict[str, Any]] = None):
    """Decorator for registering plugins."""
    def decorator(cls):
        # Validate plugin class
        issues = PluginValidator.validate_plugin_class(cls)
        if issues:
            raise ValueError(f"Plugin validation failed: {issues}")
        
        # Auto-load the plugin
        plugin_name = cls.__name__.lower().replace('plugin', '')
        try:
            instance = cls()
            plugin_metadata = instance.get_metadata()
            plugin_manager._loaded_plugins[plugin_name] = instance
            plugin_manager._plugin_metadata[plugin_name] = plugin_metadata
            plugin_manager._plugin_configs[plugin_name] = instance.get_default_config()
            eval_logger.info(f"Auto-registered plugin: {plugin_name}")
        except Exception as e:
            eval_logger.error(f"Failed to auto-register plugin {plugin_name}: {e}")
        
        return cls
    return decorator


# Utility functions for plugin development
def create_simple_model_adapter_plugin(
    name: str,
    version: str,
    description: str,
    author: str,
    supported_models: List[str],
    adapter_factory: Callable[[str], ModelAdapter]
) -> Type[ModelAdapterPlugin]:
    """Create a simple model adapter plugin."""
    
    class SimpleModelAdapterPlugin(ModelAdapterPlugin):
        def get_metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name=name,
                version=version,
                description=description,
                author=author,
                plugin_type=PluginType.MODEL_ADAPTER
            )
        
        def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
            return True
        
        def cleanup(self) -> None:
            pass
        
        def create_adapter(self, model_id: str, **kwargs) -> ModelAdapter:
            return adapter_factory(model_id, **kwargs)
        
        def get_supported_models(self) -> List[str]:
            return supported_models
    
    return SimpleModelAdapterPlugin


def create_simple_metric_plugin(
    name: str,
    version: str,
    description: str,
    author: str,
    metric_name: str,
    metric_function: Callable[[List[str], List[str]], float],
    higher_is_better: bool = True
) -> Type[MetricPlugin]:
    """Create a simple metric plugin."""
    
    class SimpleMetricPlugin(MetricPlugin):
        def get_metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name=name,
                version=version,
                description=description,
                author=author,
                plugin_type=PluginType.METRIC
            )
        
        def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
            return True
        
        def cleanup(self) -> None:
            pass
        
        def calculate_metric(self, predictions: List[str], references: List[str], **kwargs) -> float:
            return metric_function(predictions, references)
        
        def get_metric_name(self) -> str:
            return metric_name
        
        def is_higher_better(self) -> bool:
            return higher_is_better
    
    return SimpleMetricPlugin