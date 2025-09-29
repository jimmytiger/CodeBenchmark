"""
Unified Task Registry System for Multi-Turn Evaluation Engine.

This module provides a unified task registry that wraps the existing ExtendedTaskRegistry
and adds support for automatic task type classification, adapter integration, and
enhanced task discovery capabilities without modifying existing code.
"""

from typing import Any, Dict, List, Optional, Type, Union, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import traceback
from pathlib import Path
import json
import yaml
import hashlib
import time

# Import existing registry
from evaluation_engine.core.task_registration import (
    ExtendedTaskRegistry, TaskMetadata, ScenarioConfig, AdvancedTask, MultiTurnTask
)

# Import our new components
from .task_types import BaseTask, SingleTurnTask, MultiTurnTask as NewMultiTurnTask, TaskType
from .adapters import BenchmarkAdapter, AdapterRegistry, get_adapter_registry
from .exceptions import ConfigurationError, TaskRegistrationError
from .data_models import MultiTurnConfig, FeedbackConfig, SafetyConfig


class TaskSource(Enum):
    """Source of a task definition."""
    CUSTOM = "custom"           # Custom internal DSL/YAML
    LM_EVAL = "lm_eval"        # lm-eval native tasks
    EXTERNAL = "external"       # External benchmark tools


@dataclass
class TaskClassification:
    """Classification information for a task.
    
    Attributes:
        task_type: Whether task is single-turn or multi-turn
        source: Source of the task definition
        adapter_name: Name of adapter if from external source
        confidence: Confidence level of classification (0.0 to 1.0)
        metadata: Additional classification metadata
    """
    task_type: TaskType
    source: TaskSource
    adapter_name: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class TaskDiscoveryResult:
    """Result of task discovery operation.
    
    Attributes:
        task_name: Name of the discovered task
        classification: Task classification information
        available: Whether task is currently available
        error_message: Error message if task is not available
        dependencies: List of task dependencies
        capabilities: Required capabilities for the task
    """
    task_name: str
    classification: TaskClassification
    available: bool
    error_message: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


@dataclass
class TaskInstantiationResult:
    """Result of task instantiation operation.
    
    Attributes:
        task_instance: The created task instance
        success: Whether instantiation was successful
        error_message: Error message if instantiation failed
        validation_results: Results of dependency and requirement validation
        cache_hit: Whether the instance was retrieved from cache
        instantiation_time: Time taken to instantiate the task
    """
    task_instance: Optional[BaseTask]
    success: bool
    error_message: Optional[str] = None
    validation_results: Dict[str, bool] = field(default_factory=dict)
    cache_hit: bool = False
    instantiation_time: float = 0.0


@dataclass
class TaskFactoryConfig:
    """Configuration for task factory operations.
    
    Attributes:
        enable_caching: Whether to enable task instance caching
        cache_ttl: Time-to-live for cached instances in seconds
        validate_dependencies: Whether to validate task dependencies
        validate_capabilities: Whether to validate required capabilities
        strict_validation: Whether to fail on validation errors
        performance_monitoring: Whether to monitor instantiation performance
    """
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour
    validate_dependencies: bool = True
    validate_capabilities: bool = True
    strict_validation: bool = True
    performance_monitoring: bool = True


class UnifiedTaskRegistry:
    """Unified task registry that wraps ExtendedTaskRegistry with enhanced capabilities.
    
    This registry provides automatic task type classification, adapter integration,
    and enhanced discovery capabilities while maintaining compatibility with
    existing lm-eval tasks and the ExtendedTaskRegistry.
    
    Requirements addressed:
    - 1.1: Unified task type architecture
    - 1.2: Task type classification
    - 2.1: Multi-source task integration
    - 2.2: External benchmark support
    """
    
    def __init__(self, extended_registry: Optional[ExtendedTaskRegistry] = None):
        """Initialize the unified task registry.
        
        Args:
            extended_registry: Optional existing ExtendedTaskRegistry to wrap.
                              If None, creates a new instance.
        """
        # Wrap existing registry
        self._extended_registry = extended_registry or ExtendedTaskRegistry()
        
        # Get adapter registry
        self._adapter_registry = get_adapter_registry()
        
        # Task classification cache
        self._task_classifications: Dict[str, TaskClassification] = {}
        
        # Task instance cache for performance
        self._task_cache: Dict[str, BaseTask] = {}
        self._cache_max_size = 100
        self._cache_access_times: Dict[str, datetime] = {}
        self._cache_creation_times: Dict[str, datetime] = {}
        
        # Task factory configuration
        self._factory_config = TaskFactoryConfig()
        
        # Performance monitoring
        self._instantiation_stats: Dict[str, List[float]] = {}
        self._validation_cache: Dict[str, Dict[str, bool]] = {}
        
        # Discovery filters and callbacks
        self._discovery_filters: List[Callable[[str, Dict[str, Any]], bool]] = []
        self._classification_callbacks: List[Callable[[str, TaskClassification], None]] = []
        
        # Logger
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Initialize with existing tasks
        self._initialize_existing_tasks()
    
    def _initialize_existing_tasks(self) -> None:
        """Initialize classifications for existing tasks."""
        self._logger.info("Initializing task classifications for existing tasks")
        
        try:
            # Get tasks from extended registry
            hierarchy = self._extended_registry.get_task_hierarchy()
            
            for category, task_names in hierarchy.items():
                for task_name in task_names:
                    try:
                        classification = self._classify_task(task_name)
                        self._task_classifications[task_name] = classification
                        
                        # Notify callbacks
                        for callback in self._classification_callbacks:
                            try:
                                callback(task_name, classification)
                            except Exception as e:
                                self._logger.warning(f"Classification callback failed: {e}")
                                
                    except Exception as e:
                        self._logger.warning(f"Failed to classify task {task_name}: {e}")
            
            self._logger.info(f"Initialized classifications for {len(self._task_classifications)} tasks")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize existing tasks: {e}")
    
    def register_adapter(self, name: str, adapter: BenchmarkAdapter) -> None:
        """Register a benchmark adapter and discover its tasks.
        
        Args:
            name: Unique name for the adapter
            adapter: Adapter instance to register
            
        Raises:
            TaskRegistrationError: If adapter registration fails
        """
        try:
            # Register with adapter registry if not already registered
            if not self._adapter_registry.get_adapter(name):
                # Note: We assume the adapter is already initialized
                self._adapter_registry._adapters[name] = adapter
            
            # Discover tasks from adapter
            self._discover_adapter_tasks(name, adapter)
            
            self._logger.info(f"Successfully registered adapter: {name}")
            
        except Exception as e:
            error_msg = f"Failed to register adapter {name}: {str(e)}"
            self._logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise TaskRegistrationError(error_msg) from e
    
    def _discover_adapter_tasks(self, adapter_name: str, adapter: BenchmarkAdapter) -> None:
        """Discover tasks from a registered adapter.
        
        Args:
            adapter_name: Name of the adapter
            adapter: Adapter instance
        """
        try:
            # Load tasks from adapter
            tasks = adapter.load_tasks()
            
            for task in tasks:
                task_name = task.get_id()
                
                # Classify the task
                classification = TaskClassification(
                    task_type=task.get_task_type(),
                    source=TaskSource.EXTERNAL,
                    adapter_name=adapter_name,
                    confidence=1.0,
                    metadata={
                        "adapter_info": adapter.get_adapter_info(),
                        "capabilities": task.get_required_capabilities()
                    }
                )
                
                self._task_classifications[task_name] = classification
                
                # Cache the task instance
                self._cache_task(task_name, task)
                
                self._logger.debug(f"Discovered task {task_name} from adapter {adapter_name}")
            
            self._logger.info(f"Discovered {len(tasks)} tasks from adapter {adapter_name}")
            
        except Exception as e:
            error_msg = f"Failed to discover tasks from adapter {adapter_name}: {e}"
            self._logger.error(error_msg)
            raise TaskRegistrationError(error_msg) from e
    
    def classify_task(self, task_name: str) -> Optional[TaskClassification]:
        """Get the classification for a task.
        
        Args:
            task_name: Name of the task to classify
            
        Returns:
            TaskClassification object or None if task not found
        """
        # Check cache first
        if task_name in self._task_classifications:
            return self._task_classifications[task_name]
        
        # Try to classify the task
        try:
            classification = self._classify_task(task_name)
            self._task_classifications[task_name] = classification
            
            # Notify callbacks
            for callback in self._classification_callbacks:
                try:
                    callback(task_name, classification)
                except Exception as e:
                    self._logger.warning(f"Classification callback failed: {e}")
            
            return classification
        except Exception as e:
            self._logger.warning(f"Failed to classify task {task_name}: {e}")
            return None
    
    def _classify_task(self, task_name: str) -> TaskClassification:
        """Classify a task based on its name and available metadata.
        
        Args:
            task_name: Name of the task to classify
            
        Returns:
            TaskClassification object
        """
        # Check if it's from an adapter
        for adapter_name in self._adapter_registry.list_adapters():
            adapter = self._adapter_registry.get_adapter(adapter_name)
            if adapter and adapter.is_ready():
                try:
                    tasks = adapter.load_tasks()
                    for task in tasks:
                        if task.get_id() == task_name:
                            return TaskClassification(
                                task_type=task.get_task_type(),
                                source=TaskSource.EXTERNAL,
                                adapter_name=adapter_name,
                                confidence=1.0
                            )
                except Exception:
                    continue
        
        # Check extended registry metadata
        metadata = self._extended_registry.get_task_metadata(task_name)
        scenario_config = self._extended_registry.get_scenario_config(task_name)
        
        # Determine task type
        if scenario_config is not None:
            task_type = TaskType.MULTI_TURN
            confidence = 1.0
        elif metadata and hasattr(metadata, 'category'):
            # Infer from category
            if 'multi_turn' in metadata.category.lower():
                task_type = TaskType.MULTI_TURN
                confidence = 0.8
            else:
                task_type = TaskType.SINGLE_TURN
                confidence = 0.7
        else:
            # Infer from task name
            if any(keyword in task_name.lower() for keyword in ['multi_turn', 'conversation', 'dialog']):
                task_type = TaskType.MULTI_TURN
                confidence = 0.6
            else:
                task_type = TaskType.SINGLE_TURN
                confidence = 0.5
        
        # Determine source - if we have metadata or scenario config, it's custom
        # Otherwise, check if it's in the extended registry hierarchy
        if metadata or scenario_config:
            source = TaskSource.CUSTOM
        else:
            # Check if task is in extended registry hierarchy
            hierarchy = self._extended_registry.get_task_hierarchy()
            found_in_hierarchy = any(task_name in tasks for tasks in hierarchy.values())
            if found_in_hierarchy:
                source = TaskSource.CUSTOM  # Tasks in hierarchy are custom
            else:
                source = TaskSource.LM_EVAL
        
        return TaskClassification(
            task_type=task_type,
            source=source,
            confidence=confidence,
            metadata={
                "has_metadata": metadata is not None,
                "has_scenario_config": scenario_config is not None
            }
        )
    
    def discover_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[TaskDiscoveryResult]:
        """Discover tasks based on filters with enhanced information.
        
        Args:
            filters: Optional filter criteria including:
                    - task_type: TaskType enum value
                    - source: TaskSource enum value
                    - adapter_name: Name of specific adapter
                    - category: Task category
                    - capabilities: Required capabilities
                    - available_only: Only return available tasks
        
        Returns:
            List of TaskDiscoveryResult objects
        """
        results = []
        
        # Get all known task names
        all_task_names = set()
        
        # From extended registry
        hierarchy = self._extended_registry.get_task_hierarchy()
        for task_names in hierarchy.values():
            all_task_names.update(task_names)
        
        # From adapters
        for adapter_name in self._adapter_registry.list_adapters():
            adapter = self._adapter_registry.get_adapter(adapter_name)
            if adapter and adapter.is_ready():
                try:
                    tasks = adapter.load_tasks()
                    all_task_names.update(task.get_id() for task in tasks)
                except Exception as e:
                    self._logger.warning(f"Failed to load tasks from adapter {adapter_name}: {e}")
        
        # From task cache
        all_task_names.update(self._task_cache.keys())
        
        # Process each task
        for task_name in all_task_names:
            try:
                result = self._create_discovery_result(task_name, filters)
                if result and self._passes_filters(result, filters):
                    results.append(result)
            except Exception as e:
                self._logger.warning(f"Failed to create discovery result for {task_name}: {e}")
        
        # Apply custom discovery filters
        for filter_func in self._discovery_filters:
            try:
                results = [r for r in results if filter_func(r.task_name, filters or {})]
            except Exception as e:
                self._logger.warning(f"Discovery filter failed: {e}")
        
        self._logger.info(f"Discovered {len(results)} tasks matching filters")
        return results
    
    def _create_discovery_result(self, task_name: str, filters: Optional[Dict[str, Any]]) -> Optional[TaskDiscoveryResult]:
        """Create a discovery result for a task.
        
        Args:
            task_name: Name of the task
            filters: Filter criteria
            
        Returns:
            TaskDiscoveryResult or None if task cannot be processed
        """
        # Get or create classification
        classification = self.classify_task(task_name)
        if not classification:
            return None
        
        # Check availability
        available = True
        error_message = None
        dependencies = []
        capabilities = []
        
        try:
            # Check if task can be loaded
            if classification.source == TaskSource.EXTERNAL and classification.adapter_name:
                adapter = self._adapter_registry.get_adapter(classification.adapter_name)
                if not adapter or not adapter.is_ready():
                    available = False
                    error_message = f"Adapter {classification.adapter_name} not available"
                else:
                    # Get task details from adapter
                    tasks = adapter.load_tasks()
                    for task in tasks:
                        if task.get_id() == task_name:
                            capabilities = task.get_required_capabilities()
                            break
            else:
                # Check extended registry
                metadata = self._extended_registry.get_task_metadata(task_name)
                if metadata:
                    dependencies = metadata.dependencies or []
                    
                # Validate dependencies
                if not self._extended_registry.validate_task_dependencies(task_name):
                    available = False
                    error_message = "Missing dependencies"
        
        except Exception as e:
            available = False
            error_message = f"Error checking availability: {str(e)}"
        
        return TaskDiscoveryResult(
            task_name=task_name,
            classification=classification,
            available=available,
            error_message=error_message,
            dependencies=dependencies,
            capabilities=capabilities
        )
    
    def _passes_filters(self, result: TaskDiscoveryResult, filters: Optional[Dict[str, Any]]) -> bool:
        """Check if a discovery result passes the given filters.
        
        Args:
            result: TaskDiscoveryResult to check
            filters: Filter criteria
            
        Returns:
            True if result passes all filters
        """
        if not filters:
            return True
        
        # Task type filter
        if 'task_type' in filters:
            if result.classification.task_type != filters['task_type']:
                return False
        
        # Source filter
        if 'source' in filters:
            if result.classification.source != filters['source']:
                return False
        
        # Adapter name filter
        if 'adapter_name' in filters:
            if result.classification.adapter_name != filters['adapter_name']:
                return False
        
        # Available only filter
        if filters.get('available_only', False):
            if not result.available:
                return False
        
        # Capabilities filter
        if 'capabilities' in filters:
            required_caps = set(filters['capabilities'])
            task_caps = set(result.capabilities)
            if not required_caps.issubset(task_caps):
                return False
        
        # Category filter (for extended registry tasks)
        if 'category' in filters:
            metadata = self._extended_registry.get_task_metadata(result.task_name)
            if metadata and metadata.category != filters['category']:
                return False
        
        return True
    
    def get_tasks_by_type(self, task_type: TaskType) -> List[str]:
        """Get all tasks of a specific type.
        
        Args:
            task_type: TaskType to filter by
            
        Returns:
            List of task names
        """
        results = self.discover_tasks({'task_type': task_type, 'available_only': True})
        return [r.task_name for r in results]
    
    def get_tasks_by_source(self, source: TaskSource) -> List[str]:
        """Get all tasks from a specific source.
        
        Args:
            source: TaskSource to filter by
            
        Returns:
            List of task names
        """
        results = self.discover_tasks({'source': source, 'available_only': True})
        return [r.task_name for r in results]
    
    def get_tasks_by_adapter(self, adapter_name: str) -> List[str]:
        """Get all tasks from a specific adapter.
        
        Args:
            adapter_name: Name of the adapter
            
        Returns:
            List of task names
        """
        results = self.discover_tasks({'adapter_name': adapter_name, 'available_only': True})
        return [r.task_name for r in results]
    
    def validate_task_availability(self, task_name: str) -> bool:
        """Validate that a task is available for execution.
        
        Args:
            task_name: Name of the task to validate
            
        Returns:
            True if task is available
        """
        result = self._create_discovery_result(task_name, None)
        return result is not None and result.available
    
    def get_task_metadata(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive metadata for a task.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Dictionary containing task metadata or None if not found
        """
        classification = self.classify_task(task_name)
        if not classification:
            return None
        
        metadata = {
            'task_name': task_name,
            'classification': {
                'task_type': classification.task_type.value,
                'source': classification.source.value,
                'adapter_name': classification.adapter_name,
                'confidence': classification.confidence
            }
        }
        
        # Add extended registry metadata if available
        ext_metadata = self._extended_registry.get_task_metadata(task_name)
        if ext_metadata:
            metadata['extended_metadata'] = {
                'task_id': ext_metadata.task_id,
                'name': ext_metadata.name,
                'description': ext_metadata.description,
                'category': ext_metadata.category,
                'difficulty': ext_metadata.difficulty,
                'tags': ext_metadata.tags,
                'dependencies': ext_metadata.dependencies,
                'version': ext_metadata.version
            }
        
        # Add scenario config if available
        scenario_config = self._extended_registry.get_scenario_config(task_name)
        if scenario_config:
            metadata['scenario_config'] = {
                'scenario_id': scenario_config.scenario_id,
                'scenario_type': scenario_config.scenario_type,
                'max_turns': scenario_config.max_turns,
                'conversation_timeout': scenario_config.conversation_timeout,
                'enable_context_retention': scenario_config.enable_context_retention
            }
        
        return metadata
    
    def _cache_task(self, task_name: str, task: BaseTask) -> None:
        """Cache a task instance for performance.
        
        Args:
            task_name: Name of the task
            task: Task instance to cache
        """
        # Implement LRU cache eviction if needed
        if len(self._task_cache) >= self._cache_max_size:
            # Remove oldest accessed task
            oldest_task = min(self._cache_access_times.items(), key=lambda x: x[1])[0]
            del self._task_cache[oldest_task]
            del self._cache_access_times[oldest_task]
        
        self._task_cache[task_name] = task
        self._cache_access_times[task_name] = datetime.now()
    
    def _get_cached_task(self, task_name: str) -> Optional[BaseTask]:
        """Get a cached task instance.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Cached task instance or None
        """
        if task_name in self._task_cache:
            self._cache_access_times[task_name] = datetime.now()
            return self._task_cache[task_name]
        return None
    
    def add_discovery_filter(self, filter_func: Callable[[str, Dict[str, Any]], bool]) -> None:
        """Add a custom discovery filter function.
        
        Args:
            filter_func: Function that takes (task_name, filters) and returns bool
        """
        self._discovery_filters.append(filter_func)
    
    def add_classification_callback(self, callback: Callable[[str, TaskClassification], None]) -> None:
        """Add a callback for task classification events.
        
        Args:
            callback: Function that takes (task_name, classification)
        """
        self._classification_callbacks.append(callback)
    
    def export_registry_info(self, output_path: str) -> None:
        """Export comprehensive registry information.
        
        Args:
            output_path: Path to save the registry information
        """
        # Helper function to make objects JSON serializable
        def make_serializable(obj):
            if hasattr(obj, '__dict__'):
                return str(obj)
            elif hasattr(obj, 'value'):
                return obj.value
            else:
                return str(obj)
        
        info = {
            'timestamp': datetime.now().isoformat(),
            'total_tasks': len(self._task_classifications),
            'task_classifications': {
                name: {
                    'task_type': cls.task_type.value,
                    'source': cls.source.value,
                    'adapter_name': cls.adapter_name,
                    'confidence': cls.confidence,
                    'metadata': {k: make_serializable(v) for k, v in cls.metadata.items()}
                }
                for name, cls in self._task_classifications.items()
            },
            'adapters': {},
            'extended_registry_info': {}
        }
        
        # Safely get adapter status summary
        try:
            adapter_summary = self._adapter_registry.get_status_summary()
            # Make adapter summary JSON serializable
            for adapter_name, adapter_info in adapter_summary.items():
                info['adapters'][adapter_name] = {
                    k: make_serializable(v) for k, v in adapter_info.items()
                }
        except Exception as e:
            self._logger.warning(f"Failed to get adapter status summary: {e}")
            info['adapters'] = {}
        
        # Add extended registry information
        try:
            hierarchy = self._extended_registry.get_task_hierarchy()
            info['extended_registry_info'] = {
                'task_hierarchy': hierarchy,
                'total_categories': len(hierarchy)
            }
        except Exception as e:
            self._logger.warning(f"Failed to export extended registry info: {e}")
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(info, f, indent=2)
        
        self._logger.info(f"Registry information exported to {output_path}")
    
    # Task Factory and Instantiation Methods
    
    def create_task_instance(self, task_name: str, config: Dict[str, Any]) -> TaskInstantiationResult:
        """Create a task instance from configuration.
        
        This is the main factory method that handles task instantiation with
        dependency validation, caching, and performance monitoring.
        
        Args:
            task_name: Name of the task to instantiate
            config: Configuration dictionary for the task
            
        Returns:
            TaskInstantiationResult containing the task instance and metadata
        """
        start_time = time.time()
        
        try:
            # Check cache first if enabled
            if self._factory_config.enable_caching:
                cached_instance = self._get_cached_task_with_ttl(task_name, config)
                if cached_instance:
                    return TaskInstantiationResult(
                        task_instance=cached_instance,
                        success=True,
                        cache_hit=True,
                        instantiation_time=time.time() - start_time
                    )
            
            # Validate task availability
            if not self.validate_task_availability(task_name):
                return TaskInstantiationResult(
                    task_instance=None,
                    success=False,
                    error_message=f"Task {task_name} is not available",
                    instantiation_time=time.time() - start_time
                )
            
            # Get task classification
            classification = self.classify_task(task_name)
            if not classification:
                return TaskInstantiationResult(
                    task_instance=None,
                    success=False,
                    error_message=f"Could not classify task {task_name}",
                    instantiation_time=time.time() - start_time
                )
            
            # Validate dependencies and capabilities
            validation_results = {}
            if self._factory_config.validate_dependencies:
                validation_results['dependencies'] = self._validate_task_dependencies(task_name)
            if self._factory_config.validate_capabilities:
                validation_results['capabilities'] = self._validate_task_capabilities(task_name, config)
            
            # Check validation results
            if self._factory_config.strict_validation:
                for validation_type, result in validation_results.items():
                    if not result:
                        return TaskInstantiationResult(
                            task_instance=None,
                            success=False,
                            error_message=f"Validation failed for {validation_type}",
                            validation_results=validation_results,
                            instantiation_time=time.time() - start_time
                        )
            
            # Create the task instance
            task_instance = self._instantiate_task(task_name, classification, config)
            
            # Cache the instance if enabled
            if self._factory_config.enable_caching and task_instance:
                self._cache_task_with_config(task_name, task_instance, config)
            
            # Record performance metrics
            instantiation_time = time.time() - start_time
            if self._factory_config.performance_monitoring:
                self._record_instantiation_performance(task_name, instantiation_time)
            
            return TaskInstantiationResult(
                task_instance=task_instance,
                success=task_instance is not None,
                error_message=None if task_instance else "Failed to instantiate task",
                validation_results=validation_results,
                cache_hit=False,
                instantiation_time=instantiation_time
            )
            
        except Exception as e:
            error_msg = f"Error creating task instance for {task_name}: {str(e)}"
            self._logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            return TaskInstantiationResult(
                task_instance=None,
                success=False,
                error_message=error_msg,
                instantiation_time=time.time() - start_time
            )
    
    def _instantiate_task(self, task_name: str, classification: TaskClassification, config: Dict[str, Any]) -> Optional[BaseTask]:
        """Instantiate a task based on its classification.
        
        Args:
            task_name: Name of the task
            classification: Task classification information
            config: Task configuration
            
        Returns:
            Task instance or None if instantiation fails
        """
        try:
            if classification.source == TaskSource.EXTERNAL and classification.adapter_name:
                # Create task from adapter
                return self._create_task_from_adapter(task_name, classification.adapter_name, config)
            elif classification.source == TaskSource.CUSTOM:
                # Create task from extended registry
                return self._create_task_from_extended_registry(task_name, config)
            elif classification.source == TaskSource.LM_EVAL:
                # Create task from lm-eval
                return self._create_task_from_lm_eval(task_name, config)
            else:
                self._logger.error(f"Unknown task source: {classification.source}")
                return None
                
        except Exception as e:
            self._logger.error(f"Failed to instantiate task {task_name}: {e}")
            return None
    
    def _create_task_from_adapter(self, task_name: str, adapter_name: str, config: Dict[str, Any]) -> Optional[BaseTask]:
        """Create a task instance from an adapter.
        
        Args:
            task_name: Name of the task
            adapter_name: Name of the adapter
            config: Task configuration
            
        Returns:
            Task instance or None if creation fails
        """
        adapter = self._adapter_registry.get_adapter(adapter_name)
        if not adapter or not adapter.is_ready():
            self._logger.error(f"Adapter {adapter_name} not available")
            return None
        
        try:
            # Load tasks from adapter to find the specific task
            tasks = adapter.load_tasks()
            for task in tasks:
                if task.get_id() == task_name:
                    # Create a new instance with the provided config
                    task_class = type(task)
                    return task_class(task_name, config)
            
            self._logger.error(f"Task {task_name} not found in adapter {adapter_name}")
            return None
            
        except Exception as e:
            self._logger.error(f"Failed to create task from adapter {adapter_name}: {e}")
            return None
    
    def _create_task_from_extended_registry(self, task_name: str, config: Dict[str, Any]) -> Optional[BaseTask]:
        """Create a task instance from the extended registry.
        
        Args:
            task_name: Name of the task
            config: Task configuration
            
        Returns:
            Task instance or None if creation fails
        """
        try:
            # Try to create based on scenario config first
            scenario_config = self._extended_registry.get_scenario_config(task_name)
            if scenario_config:
                # Create a multi-turn task wrapper
                return self._create_multi_turn_task_wrapper(task_name, config, scenario_config)
            
            # Try to create based on metadata
            metadata = self._extended_registry.get_task_metadata(task_name)
            if metadata:
                return self._create_basic_task_wrapper(task_name, config, metadata)
            
            # Try to load task from extended registry config file
            if 'config_path' in config:
                task = self._extended_registry.load_task_from_config(config['config_path'])
                if task and task.get_id() == task_name:
                    return task
            
            # If task is in hierarchy but no metadata, create basic wrapper
            hierarchy = self._extended_registry.get_task_hierarchy()
            found_in_hierarchy = any(task_name in tasks for tasks in hierarchy.values())
            if found_in_hierarchy:
                # Create a basic task wrapper with minimal metadata
                basic_metadata = TaskMetadata(
                    task_id=task_name,
                    name=task_name,
                    description=f"Task {task_name}",
                    category="general",
                    difficulty="unknown"
                )
                return self._create_basic_task_wrapper(task_name, config, basic_metadata)
            
            return None
            
        except Exception as e:
            self._logger.error(f"Failed to create task from extended registry: {e}")
            return None
    
    def _create_task_from_lm_eval(self, task_name: str, config: Dict[str, Any]) -> Optional[BaseTask]:
        """Create a task instance from lm-eval.
        
        Args:
            task_name: Name of the task
            config: Task configuration
            
        Returns:
            Task instance or None if creation fails
        """
        try:
            # Import lm-eval task loading
            from lm_eval.tasks import get_task_dict
            
            # Try to get task dict - handle different lm-eval versions
            try:
                task_dict = get_task_dict([task_name])
            except TypeError:
                # Older version might not need task_name_list
                task_dict = get_task_dict()
            
            if task_name in task_dict:
                # Create a wrapper for the lm-eval task
                return self._create_lm_eval_task_wrapper(task_name, config, task_dict[task_name])
            
            return None
            
        except Exception as e:
            self._logger.error(f"Failed to create task from lm-eval: {e}")
            return None
    
    def _create_multi_turn_task_wrapper(self, task_name: str, config: Dict[str, Any], scenario_config: ScenarioConfig) -> BaseTask:
        """Create a multi-turn task wrapper.
        
        Args:
            task_name: Name of the task
            config: Task configuration
            scenario_config: Scenario configuration
            
        Returns:
            MultiTurnTask instance
        """
        # Create a dynamic multi-turn task class
        class DynamicMultiTurnTask(NewMultiTurnTask):
            def __init__(self, task_id: str, task_config: Dict[str, Any]):
                super().__init__(task_id, task_config)
                self.scenario_config = scenario_config
            
            def execute_turn(self, turn_data):
                # Basic implementation - subclasses should override
                from .data_models import TurnResult
                return TurnResult(
                    turn=turn_data.turn_number,
                    action="default_action",
                    observation="default_observation",
                    reward=0.0,
                    done=False,
                    info={},
                    execution_time=0.0
                )
            
            def should_continue(self, turn_result) -> bool:
                return not turn_result.done and turn_result.turn < self.scenario_config.max_turns
            
            def get_initial_context(self) -> str:
                return f"Multi-turn task: {self.task_id}"
            
            def is_successful(self, turn_results) -> bool:
                return any(tr.done and tr.reward > 0 for tr in turn_results)
            
            def get_required_capabilities(self) -> List[str]:
                return ["multi_turn", "conversation"]
        
        return DynamicMultiTurnTask(task_name, config)
    
    def _create_basic_task_wrapper(self, task_name: str, config: Dict[str, Any], metadata: TaskMetadata) -> BaseTask:
        """Create a basic task wrapper.
        
        Args:
            task_name: Name of the task
            config: Task configuration
            metadata: Task metadata
            
        Returns:
            SingleTurnTask instance
        """
        # Create a dynamic single-turn task class
        class DynamicSingleTurnTask(SingleTurnTask):
            def __init__(self, task_id: str, task_config: Dict[str, Any]):
                super().__init__(task_id, task_config)
                self.metadata = metadata
            
            def execute(self, input_data):
                # Basic implementation - subclasses should override
                from .task_types import TaskResult
                return TaskResult(
                    task_id=self.task_id,
                    success=True,
                    score=1.0,
                    execution_time=0.0,
                    metadata={"input": str(input_data)}
                )
            
            def get_required_capabilities(self) -> List[str]:
                return getattr(self.metadata, 'dependencies', [])
        
        return DynamicSingleTurnTask(task_name, config)
    
    def _create_lm_eval_task_wrapper(self, task_name: str, config: Dict[str, Any], lm_eval_task) -> BaseTask:
        """Create an lm-eval task wrapper.
        
        Args:
            task_name: Name of the task
            config: Task configuration
            lm_eval_task: The lm-eval task object
            
        Returns:
            SingleTurnTask instance
        """
        # Create a wrapper for lm-eval tasks
        class LMEvalTaskWrapper(SingleTurnTask):
            def __init__(self, task_id: str, task_config: Dict[str, Any]):
                super().__init__(task_id, task_config)
                self.lm_eval_task = lm_eval_task
            
            def execute(self, input_data):
                # Basic implementation - would need to integrate with lm-eval properly
                from .task_types import TaskResult
                return TaskResult(
                    task_id=self.task_id,
                    success=True,
                    score=1.0,
                    execution_time=0.0,
                    metadata={"lm_eval_task": str(self.lm_eval_task)}
                )
            
            def get_required_capabilities(self) -> List[str]:
                return ["lm_eval"]
        
        return LMEvalTaskWrapper(task_name, config)
    
    def _validate_task_dependencies(self, task_name: str) -> bool:
        """Validate task dependencies.
        
        Args:
            task_name: Name of the task to validate
            
        Returns:
            True if all dependencies are satisfied
        """
        # Check validation cache first
        cache_key = f"deps_{task_name}"
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
        
        try:
            # Use extended registry validation
            result = self._extended_registry.validate_task_dependencies(task_name)
            
            # Cache the result
            self._validation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            self._logger.warning(f"Failed to validate dependencies for {task_name}: {e}")
            return False
    
    def _validate_task_capabilities(self, task_name: str, config: Dict[str, Any]) -> bool:
        """Validate task capabilities.
        
        Args:
            task_name: Name of the task
            config: Task configuration
            
        Returns:
            True if all required capabilities are available
        """
        # Check validation cache first
        config_hash = self._hash_config(config)
        cache_key = f"caps_{task_name}_{config_hash}"
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
        
        try:
            # Get required capabilities
            classification = self.classify_task(task_name)
            if not classification:
                return False
            
            # For now, assume all capabilities are available
            # In a real implementation, this would check system capabilities
            result = True
            
            # Cache the result
            self._validation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            self._logger.warning(f"Failed to validate capabilities for {task_name}: {e}")
            return False
    
    def _hash_config(self, config: Dict[str, Any]) -> str:
        """Create a hash of the configuration for caching.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Hash string
        """
        try:
            config_str = json.dumps(config, sort_keys=True)
            return hashlib.md5(config_str.encode()).hexdigest()[:8]
        except Exception:
            return "default"
    
    def _cache_task_with_config(self, task_name: str, task: BaseTask, config: Dict[str, Any]) -> None:
        """Cache a task instance with configuration.
        
        Args:
            task_name: Name of the task
            task: Task instance to cache
            config: Configuration used to create the task
        """
        config_hash = self._hash_config(config)
        cache_key = f"{task_name}_{config_hash}"
        
        # Implement LRU cache eviction if needed
        if len(self._task_cache) >= self._cache_max_size:
            # Remove oldest accessed task
            oldest_task = min(self._cache_access_times.items(), key=lambda x: x[1])[0]
            del self._task_cache[oldest_task]
            del self._cache_access_times[oldest_task]
            if oldest_task in self._cache_creation_times:
                del self._cache_creation_times[oldest_task]
        
        self._task_cache[cache_key] = task
        self._cache_access_times[cache_key] = datetime.now()
        self._cache_creation_times[cache_key] = datetime.now()
    
    def _get_cached_task_with_ttl(self, task_name: str, config: Dict[str, Any]) -> Optional[BaseTask]:
        """Get a cached task instance with TTL check.
        
        Args:
            task_name: Name of the task
            config: Configuration used to create the task
            
        Returns:
            Cached task instance or None
        """
        config_hash = self._hash_config(config)
        cache_key = f"{task_name}_{config_hash}"
        
        if cache_key in self._task_cache:
            # Check TTL
            creation_time = self._cache_creation_times.get(cache_key)
            if creation_time:
                age = (datetime.now() - creation_time).total_seconds()
                if age > self._factory_config.cache_ttl:
                    # Remove expired entry
                    del self._task_cache[cache_key]
                    del self._cache_access_times[cache_key]
                    del self._cache_creation_times[cache_key]
                    return None
            
            # Update access time and return cached instance
            self._cache_access_times[cache_key] = datetime.now()
            return self._task_cache[cache_key]
        
        return None
    
    def _record_instantiation_performance(self, task_name: str, instantiation_time: float) -> None:
        """Record performance metrics for task instantiation.
        
        Args:
            task_name: Name of the task
            instantiation_time: Time taken to instantiate
        """
        if task_name not in self._instantiation_stats:
            self._instantiation_stats[task_name] = []
        
        self._instantiation_stats[task_name].append(instantiation_time)
        
        # Keep only last 100 measurements
        if len(self._instantiation_stats[task_name]) > 100:
            self._instantiation_stats[task_name] = self._instantiation_stats[task_name][-100:]
    
    def configure_factory(self, config: TaskFactoryConfig) -> None:
        """Configure the task factory.
        
        Args:
            config: Factory configuration
        """
        self._factory_config = config
        self._logger.info(f"Task factory configured: caching={config.enable_caching}, "
                         f"validation={config.validate_dependencies}")
    
    def clear_cache(self) -> None:
        """Clear the task instance cache."""
        self._task_cache.clear()
        self._cache_access_times.clear()
        self._cache_creation_times.clear()
        self._validation_cache.clear()
        self._logger.info("Task cache cleared")
    
    def get_instantiation_performance(self) -> Dict[str, Dict[str, float]]:
        """Get instantiation performance statistics.
        
        Returns:
            Dictionary mapping task names to performance statistics
        """
        stats = {}
        for task_name, times in self._instantiation_stats.items():
            if times:
                stats[task_name] = {
                    'count': len(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'total_time': sum(times)
                }
        return stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics.
        
        Returns:
            Dictionary containing registry statistics
        """
        stats = {
            'total_tasks': len(self._task_classifications),
            'task_types': {},
            'sources': {},
            'adapters': {},
            'cache_size': len(self._task_cache),
            'cache_hit_rate': 0.0,
            'factory_config': {
                'enable_caching': self._factory_config.enable_caching,
                'cache_ttl': self._factory_config.cache_ttl,
                'validate_dependencies': self._factory_config.validate_dependencies,
                'validate_capabilities': self._factory_config.validate_capabilities
            },
            'instantiation_performance': self.get_instantiation_performance()
        }
        
        # Count by task type
        for classification in self._task_classifications.values():
            task_type = classification.task_type.value
            stats['task_types'][task_type] = stats['task_types'].get(task_type, 0) + 1
        
        # Count by source
        for classification in self._task_classifications.values():
            source = classification.source.value
            stats['sources'][source] = stats['sources'].get(source, 0) + 1
        
        # Count by adapter
        for classification in self._task_classifications.values():
            if classification.adapter_name:
                adapter = classification.adapter_name
                stats['adapters'][adapter] = stats['adapters'].get(adapter, 0) + 1
        
        return stats


# Global unified registry instance
_global_unified_registry: Optional[UnifiedTaskRegistry] = None


def get_unified_task_registry() -> UnifiedTaskRegistry:
    """Get the global unified task registry instance.
    
    Returns:
        Global UnifiedTaskRegistry instance
    """
    global _global_unified_registry
    if _global_unified_registry is None:
        _global_unified_registry = UnifiedTaskRegistry()
    return _global_unified_registry


def reset_unified_task_registry() -> None:
    """Reset the global unified task registry (mainly for testing)."""
    global _global_unified_registry
    _global_unified_registry = None