"""
Adapter architecture for external benchmark integration.

This module provides the base adapter framework that enables seamless integration
of different benchmark tools and task sources into the unified evaluation engine.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import traceback
from enum import Enum

from .environment import UnifiedEnv
from .task_types import BaseTask, TaskType, TaskResult
from .exceptions import AdapterError, ConfigurationError, TaskExecutionError


class AdapterStatus(Enum):
    """Status of an adapter."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class AdapterInfo:
    """Information about a benchmark adapter.
    
    Attributes:
        name: Unique name of the adapter
        version: Version string of the adapter
        description: Human-readable description
        supported_task_types: List of supported task types
        required_dependencies: List of required Python packages
        supported_formats: List of supported input/output formats
        capabilities: List of capabilities provided by this adapter
    """
    name: str
    version: str
    description: str
    supported_task_types: List[TaskType]
    required_dependencies: List[str]
    supported_formats: List[str]
    capabilities: List[str]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StandardizedResult:
    """Standardized result format for cross-benchmark comparison.
    
    Attributes:
        task_id: Unique identifier for the task
        adapter_name: Name of the adapter that produced this result
        success: Whether the task was completed successfully
        score: Normalized score (0.0 to 1.0)
        execution_time: Total execution time in seconds
        turns: Number of turns taken (for multi-turn tasks)
        tokens_used: Total tokens consumed
        cost: Total cost incurred
        metadata: Additional adapter-specific information
        raw_result: Original result from the benchmark tool
    """
    task_id: str
    adapter_name: str
    success: bool
    score: float
    execution_time: float
    turns: int
    tokens_used: int
    cost: float
    metadata: Dict[str, Any]
    raw_result: Any
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # Validate score range
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")


class BenchmarkAdapter(ABC):
    """Abstract base class for benchmark tool adapters.
    
    This class defines the interface that all benchmark adapters must implement
    to integrate with the unified evaluation engine. Adapters serve as bridges
    between the unified interface and specific benchmark tools.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the adapter.
        
        Args:
            config: Configuration dictionary for the adapter
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate configuration first
        self._validate_config(config)
        
        self.config = config.copy()
        self._status = AdapterStatus.UNINITIALIZED
        self._error_message: Optional[str] = None
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._initialization_time: Optional[datetime] = None
    
    @abstractmethod
    def get_adapter_info(self) -> AdapterInfo:
        """Get information about this adapter.
        
        Returns:
            AdapterInfo object describing the adapter
        """
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the adapter and its dependencies.
        
        This method should perform any necessary setup, such as checking
        for required dependencies, validating configurations, or establishing
        connections to external services.
        
        Returns:
            True if initialization was successful
            
        Raises:
            AdapterError: If initialization fails
        """
        pass
    
    @abstractmethod
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create an environment instance for the benchmark.
        
        Args:
            task_config: Configuration for the specific task
            
        Returns:
            UnifiedEnv instance configured for the task
            
        Raises:
            AdapterError: If environment creation fails
        """
        pass
    
    @abstractmethod
    def load_tasks(self, task_filter: Optional[Dict[str, Any]] = None) -> List[BaseTask]:
        """Load available tasks from the benchmark.
        
        Args:
            task_filter: Optional filter criteria for task selection
            
        Returns:
            List of available tasks
            
        Raises:
            AdapterError: If task loading fails
        """
        pass
    
    @abstractmethod
    def convert_results(self, results: Any) -> StandardizedResult:
        """Convert benchmark-specific results to standardized format.
        
        Args:
            results: Raw results from the benchmark tool
            
        Returns:
            StandardizedResult object
            
        Raises:
            AdapterError: If result conversion fails
        """
        pass
    
    def get_status(self) -> AdapterStatus:
        """Get the current status of the adapter.
        
        Returns:
            Current AdapterStatus
        """
        return self._status
    
    def get_error_message(self) -> Optional[str]:
        """Get the last error message, if any.
        
        Returns:
            Error message string or None
        """
        return self._error_message
    
    def is_ready(self) -> bool:
        """Check if the adapter is ready for use.
        
        Returns:
            True if adapter is initialized and ready
        """
        return self._status == AdapterStatus.READY
    
    def validate_task_config(self, task_config: Dict[str, Any]) -> bool:
        """Validate a task configuration for this adapter.
        
        Args:
            task_config: Task configuration to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Basic validation - subclasses should override for specific checks
        if not isinstance(task_config, dict):
            raise ConfigurationError("Task configuration must be a dictionary")
        
        required_fields = ["task_id", "task_type"]
        for field in required_fields:
            if field not in task_config:
                raise ConfigurationError(f"Missing required field: {field}")
        
        return True
    
    def cleanup(self) -> None:
        """Clean up adapter resources.
        
        This method should be called when the adapter is no longer needed
        to ensure proper cleanup of resources.
        """
        self._logger.info(f"Cleaning up adapter {self.get_adapter_info().name}")
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate the adapter configuration.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not isinstance(config, dict):
            raise ConfigurationError("Adapter configuration must be a dictionary")
    
    def _set_status(self, status: AdapterStatus, error_message: Optional[str] = None) -> None:
        """Set the adapter status.
        
        Args:
            status: New status to set
            error_message: Optional error message for error status
        """
        self._status = status
        self._error_message = error_message
        
        if status == AdapterStatus.READY and self._initialization_time is None:
            self._initialization_time = datetime.now()
        
        self._logger.info(f"Adapter status changed to {status.value}")
        if error_message:
            self._logger.error(f"Adapter error: {error_message}")
    
    def _safe_execute(self, operation: Callable, operation_name: str, *args, **kwargs) -> Any:
        """Safely execute an operation with error handling.
        
        Args:
            operation: Function to execute
            operation_name: Name of the operation for logging
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            AdapterError: If operation fails
        """
        try:
            self._logger.debug(f"Executing {operation_name}")
            result = operation(*args, **kwargs)
            self._logger.debug(f"Successfully completed {operation_name}")
            return result
        except Exception as e:
            error_msg = f"Failed to execute {operation_name}: {str(e)}"
            self._logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise AdapterError(error_msg) from e


class AdapterRegistry:
    """Registry for managing benchmark adapters.
    
    This class provides centralized management of adapter instances,
    including registration, discovery, lifecycle management, and error handling.
    """
    
    def __init__(self):
        """Initialize the adapter registry."""
        self._adapters: Dict[str, BenchmarkAdapter] = {}
        self._adapter_classes: Dict[str, Type[BenchmarkAdapter]] = {}
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._initialization_callbacks: List[Callable[[str, BenchmarkAdapter], None]] = []
        self._error_callbacks: List[Callable[[str, str], None]] = []
    
    def register_adapter_class(self, name: str, adapter_class: Type[BenchmarkAdapter]) -> None:
        """Register an adapter class for later instantiation.
        
        Args:
            name: Unique name for the adapter
            adapter_class: Adapter class to register
            
        Raises:
            ValueError: If name is already registered
        """
        if name in self._adapter_classes:
            raise ValueError(f"Adapter class '{name}' is already registered")
        
        if not issubclass(adapter_class, BenchmarkAdapter):
            raise ValueError(f"Adapter class must inherit from BenchmarkAdapter")
        
        self._adapter_classes[name] = adapter_class
        self._logger.info(f"Registered adapter class: {name}")
    
    def create_adapter(self, name: str, config: Dict[str, Any]) -> BenchmarkAdapter:
        """Create an adapter instance from a registered class.
        
        Args:
            name: Name of the adapter class to instantiate
            config: Configuration for the adapter
            
        Returns:
            Initialized adapter instance
            
        Raises:
            ValueError: If adapter class is not registered
            AdapterError: If adapter creation or initialization fails
        """
        if name not in self._adapter_classes:
            raise ValueError(f"Adapter class '{name}' is not registered")
        
        try:
            adapter_class = self._adapter_classes[name]
            adapter = adapter_class(config)
            
            # Initialize the adapter
            if adapter.initialize():
                self._adapters[name] = adapter
                self._logger.info(f"Successfully created and initialized adapter: {name}")
                
                # Notify callbacks
                for callback in self._initialization_callbacks:
                    try:
                        callback(name, adapter)
                    except Exception as e:
                        self._logger.warning(f"Initialization callback failed: {e}")
                
                return adapter
            else:
                error_msg = f"Failed to initialize adapter: {name}"
                self._logger.error(error_msg)
                raise AdapterError(error_msg)
                
        except Exception as e:
            error_msg = f"Failed to create adapter '{name}': {str(e)}"
            self._logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            # Notify error callbacks
            for callback in self._error_callbacks:
                try:
                    callback(name, error_msg)
                except Exception as cb_error:
                    self._logger.warning(f"Error callback failed: {cb_error}")
            
            raise AdapterError(error_msg) from e
    
    def get_adapter(self, name: str) -> Optional[BenchmarkAdapter]:
        """Get an adapter instance by name.
        
        Args:
            name: Name of the adapter
            
        Returns:
            Adapter instance or None if not found
        """
        return self._adapters.get(name)
    
    def list_adapters(self) -> List[str]:
        """List all registered adapter names.
        
        Returns:
            List of adapter names
        """
        return list(self._adapters.keys())
    
    def list_adapter_classes(self) -> List[str]:
        """List all registered adapter class names.
        
        Returns:
            List of adapter class names
        """
        return list(self._adapter_classes.keys())
    
    def get_adapter_info(self, name: str) -> Optional[AdapterInfo]:
        """Get information about an adapter.
        
        Args:
            name: Name of the adapter
            
        Returns:
            AdapterInfo object or None if adapter not found
        """
        adapter = self._adapters.get(name)
        if adapter:
            return adapter.get_adapter_info()
        return None
    
    def get_adapters_by_task_type(self, task_type: TaskType) -> List[str]:
        """Get adapters that support a specific task type.
        
        Args:
            task_type: Task type to filter by
            
        Returns:
            List of adapter names that support the task type
        """
        matching_adapters = []
        for name, adapter in self._adapters.items():
            if adapter.is_ready():
                info = adapter.get_adapter_info()
                if task_type in info.supported_task_types:
                    matching_adapters.append(name)
        return matching_adapters
    
    def remove_adapter(self, name: str) -> bool:
        """Remove an adapter from the registry.
        
        Args:
            name: Name of the adapter to remove
            
        Returns:
            True if adapter was removed, False if not found
        """
        if name in self._adapters:
            adapter = self._adapters[name]
            try:
                adapter.cleanup()
            except Exception as e:
                self._logger.warning(f"Error during adapter cleanup: {e}")
            
            del self._adapters[name]
            self._logger.info(f"Removed adapter: {name}")
            return True
        return False
    
    def cleanup_all(self) -> None:
        """Clean up all registered adapters."""
        for name in list(self._adapters.keys()):
            self.remove_adapter(name)
    
    def add_initialization_callback(self, callback: Callable[[str, BenchmarkAdapter], None]) -> None:
        """Add a callback to be called when adapters are initialized.
        
        Args:
            callback: Function to call with (adapter_name, adapter_instance)
        """
        self._initialization_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add a callback to be called when adapter errors occur.
        
        Args:
            callback: Function to call with (adapter_name, error_message)
        """
        self._error_callbacks.append(callback)
    
    def get_status_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get a summary of all adapter statuses.
        
        Returns:
            Dictionary mapping adapter names to status information
        """
        summary = {}
        for name, adapter in self._adapters.items():
            info = adapter.get_adapter_info()
            summary[name] = {
                "status": adapter.get_status().value,
                "error_message": adapter.get_error_message(),
                "version": info.version,
                "supported_task_types": [tt.value for tt in info.supported_task_types],
                "capabilities": info.capabilities
            }
        return summary


# Global adapter registry instance
_global_registry = AdapterRegistry()


def get_adapter_registry() -> AdapterRegistry:
    """Get the global adapter registry instance.
    
    Returns:
        Global AdapterRegistry instance
    """
    return _global_registry


def register_adapter_class(name: str, adapter_class: Type[BenchmarkAdapter]) -> None:
    """Register an adapter class with the global registry.
    
    Args:
        name: Unique name for the adapter
        adapter_class: Adapter class to register
    """
    _global_registry.register_adapter_class(name, adapter_class)


def create_adapter(name: str, config: Dict[str, Any]) -> BenchmarkAdapter:
    """Create an adapter instance using the global registry.
    
    Args:
        name: Name of the adapter class to instantiate
        config: Configuration for the adapter
        
    Returns:
        Initialized adapter instance
    """
    return _global_registry.create_adapter(name, config)


def get_adapter(name: str) -> Optional[BenchmarkAdapter]:
    """Get an adapter instance from the global registry.
    
    Args:
        name: Name of the adapter
        
    Returns:
        Adapter instance or None if not found
    """
    return _global_registry.get_adapter(name)