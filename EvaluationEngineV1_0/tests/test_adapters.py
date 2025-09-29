"""
Tests for the adapter architecture and registry system.

This module contains comprehensive tests for the benchmark adapter framework,
including adapter registration, lifecycle management, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List

from EvaluationEngineV1_0.core.adapters import (
    BenchmarkAdapter,
    AdapterRegistry,
    AdapterInfo,
    AdapterStatus,
    StandardizedResult,
    get_adapter_registry,
    register_adapter_class,
    create_adapter,
    get_adapter
)
from EvaluationEngineV1_0.core.environment import UnifiedEnv
from EvaluationEngineV1_0.core.task_types import BaseTask, TaskType, TaskResult
from EvaluationEngineV1_0.core.exceptions import AdapterError, ConfigurationError


class MockAdapter(BenchmarkAdapter):
    """Mock adapter for testing purposes."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._initialized = False
        self._should_fail_init = config.get("fail_init", False)
        self._should_fail_create_env = config.get("fail_create_env", False)
    
    def get_adapter_info(self) -> AdapterInfo:
        return AdapterInfo(
            name="mock_adapter",
            version="1.0.0",
            description="Mock adapter for testing",
            supported_task_types=[TaskType.SINGLE_TURN, TaskType.MULTI_TURN],
            required_dependencies=["pytest"],
            supported_formats=["json", "yaml"],
            capabilities=["mock_execution", "test_support"]
        )
    
    def initialize(self) -> bool:
        if self._should_fail_init:
            self._set_status(AdapterStatus.ERROR, "Initialization failed")
            return False
        
        self._set_status(AdapterStatus.READY)
        self._initialized = True
        return True
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        if self._should_fail_create_env:
            raise AdapterError("Failed to create environment")
        
        # Return a mock environment
        mock_env = Mock(spec=UnifiedEnv)
        return mock_env
    
    def load_tasks(self, task_filter: Dict[str, Any] = None) -> List[BaseTask]:
        # Return mock tasks
        mock_task = Mock(spec=BaseTask)
        mock_task.get_id.return_value = "mock_task_1"
        mock_task.get_task_type.return_value = TaskType.SINGLE_TURN
        return [mock_task]
    
    def convert_results(self, results: Any) -> StandardizedResult:
        return StandardizedResult(
            task_id="mock_task",
            adapter_name="mock_adapter",
            success=True,
            score=0.85,
            execution_time=1.5,
            turns=1,
            tokens_used=100,
            cost=0.01,
            metadata={"test": True},
            raw_result=results
        )


class FailingAdapter(BenchmarkAdapter):
    """Adapter that always fails for testing error handling."""
    
    def get_adapter_info(self) -> AdapterInfo:
        return AdapterInfo(
            name="failing_adapter",
            version="1.0.0",
            description="Adapter that always fails",
            supported_task_types=[TaskType.SINGLE_TURN],
            required_dependencies=[],
            supported_formats=[],
            capabilities=[]
        )
    
    def initialize(self) -> bool:
        raise AdapterError("This adapter always fails")
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        raise AdapterError("Cannot create environment")
    
    def load_tasks(self, task_filter: Dict[str, Any] = None) -> List[BaseTask]:
        raise AdapterError("Cannot load tasks")
    
    def convert_results(self, results: Any) -> StandardizedResult:
        raise AdapterError("Cannot convert results")


class TestAdapterInfo:
    """Test cases for AdapterInfo dataclass."""
    
    def test_adapter_info_creation(self):
        """Test creating AdapterInfo with all fields."""
        info = AdapterInfo(
            name="test_adapter",
            version="2.1.0",
            description="Test adapter description",
            supported_task_types=[TaskType.MULTI_TURN],
            required_dependencies=["numpy", "pandas"],
            supported_formats=["csv", "json"],
            capabilities=["data_processing", "visualization"]
        )
        
        assert info.name == "test_adapter"
        assert info.version == "2.1.0"
        assert info.description == "Test adapter description"
        assert info.supported_task_types == [TaskType.MULTI_TURN]
        assert info.required_dependencies == ["numpy", "pandas"]
        assert info.supported_formats == ["csv", "json"]
        assert info.capabilities == ["data_processing", "visualization"]
        assert info.metadata == {}
    
    def test_adapter_info_with_metadata(self):
        """Test creating AdapterInfo with custom metadata."""
        metadata = {"author": "test", "license": "MIT"}
        info = AdapterInfo(
            name="test",
            version="1.0",
            description="test",
            supported_task_types=[],
            required_dependencies=[],
            supported_formats=[],
            capabilities=[],
            metadata=metadata
        )
        
        assert info.metadata == metadata


class TestStandardizedResult:
    """Test cases for StandardizedResult dataclass."""
    
    def test_standardized_result_creation(self):
        """Test creating StandardizedResult with valid data."""
        result = StandardizedResult(
            task_id="task_123",
            adapter_name="test_adapter",
            success=True,
            score=0.95,
            execution_time=2.5,
            turns=3,
            tokens_used=150,
            cost=0.05,
            metadata={"complexity": "high"},
            raw_result={"original": "data"}
        )
        
        assert result.task_id == "task_123"
        assert result.adapter_name == "test_adapter"
        assert result.success is True
        assert result.score == 0.95
        assert result.execution_time == 2.5
        assert result.turns == 3
        assert result.tokens_used == 150
        assert result.cost == 0.05
        assert result.metadata == {"complexity": "high"}
        assert result.raw_result == {"original": "data"}
        assert isinstance(result.timestamp, datetime)
    
    def test_standardized_result_invalid_score(self):
        """Test that invalid scores raise ValueError."""
        with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
            StandardizedResult(
                task_id="test",
                adapter_name="test",
                success=True,
                score=1.5,  # Invalid score > 1.0
                execution_time=1.0,
                turns=1,
                tokens_used=10,
                cost=0.01,
                metadata={},
                raw_result={}
            )
        
        with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
            StandardizedResult(
                task_id="test",
                adapter_name="test",
                success=True,
                score=-0.1,  # Invalid score < 0.0
                execution_time=1.0,
                turns=1,
                tokens_used=10,
                cost=0.01,
                metadata={},
                raw_result={}
            )


class TestBenchmarkAdapter:
    """Test cases for BenchmarkAdapter base class."""
    
    def test_adapter_initialization(self):
        """Test adapter initialization with valid config."""
        config = {"timeout": 30, "max_retries": 3}
        adapter = MockAdapter(config)
        
        assert adapter.config == config
        assert adapter.get_status() == AdapterStatus.UNINITIALIZED
        assert adapter.get_error_message() is None
        assert not adapter.is_ready()
    
    def test_adapter_initialization_invalid_config(self):
        """Test adapter initialization with invalid config."""
        with pytest.raises(ConfigurationError):
            MockAdapter("not_a_dict")
    
    def test_adapter_successful_initialization(self):
        """Test successful adapter initialization."""
        adapter = MockAdapter({})
        
        assert adapter.initialize()
        assert adapter.get_status() == AdapterStatus.READY
        assert adapter.is_ready()
        assert adapter.get_error_message() is None
    
    def test_adapter_failed_initialization(self):
        """Test failed adapter initialization."""
        adapter = MockAdapter({"fail_init": True})
        
        assert not adapter.initialize()
        assert adapter.get_status() == AdapterStatus.ERROR
        assert not adapter.is_ready()
        assert adapter.get_error_message() == "Initialization failed"
    
    def test_adapter_info(self):
        """Test getting adapter information."""
        adapter = MockAdapter({})
        info = adapter.get_adapter_info()
        
        assert info.name == "mock_adapter"
        assert info.version == "1.0.0"
        assert TaskType.SINGLE_TURN in info.supported_task_types
        assert TaskType.MULTI_TURN in info.supported_task_types
        assert "pytest" in info.required_dependencies
    
    def test_create_environment_success(self):
        """Test successful environment creation."""
        adapter = MockAdapter({})
        adapter.initialize()
        
        task_config = {"task_id": "test", "task_type": "single_turn"}
        env = adapter.create_environment(task_config)
        
        assert env is not None
    
    def test_create_environment_failure(self):
        """Test environment creation failure."""
        adapter = MockAdapter({"fail_create_env": True})
        adapter.initialize()
        
        task_config = {"task_id": "test", "task_type": "single_turn"}
        
        with pytest.raises(AdapterError, match="Failed to create environment"):
            adapter.create_environment(task_config)
    
    def test_load_tasks(self):
        """Test loading tasks from adapter."""
        adapter = MockAdapter({})
        adapter.initialize()
        
        tasks = adapter.load_tasks()
        
        assert len(tasks) == 1
        assert tasks[0].get_id() == "mock_task_1"
        assert tasks[0].get_task_type() == TaskType.SINGLE_TURN
    
    def test_convert_results(self):
        """Test result conversion."""
        adapter = MockAdapter({})
        raw_result = {"score": 0.85, "time": 1.5}
        
        standardized = adapter.convert_results(raw_result)
        
        assert standardized.task_id == "mock_task"
        assert standardized.adapter_name == "mock_adapter"
        assert standardized.success is True
        assert standardized.score == 0.85
        assert standardized.raw_result == raw_result
    
    def test_validate_task_config_valid(self):
        """Test task config validation with valid config."""
        adapter = MockAdapter({})
        config = {"task_id": "test", "task_type": "single_turn"}
        
        assert adapter.validate_task_config(config)
    
    def test_validate_task_config_invalid(self):
        """Test task config validation with invalid config."""
        adapter = MockAdapter({})
        
        # Test non-dict config
        with pytest.raises(ConfigurationError, match="must be a dictionary"):
            adapter.validate_task_config("not_a_dict")
        
        # Test missing required fields
        with pytest.raises(ConfigurationError, match="Missing required field"):
            adapter.validate_task_config({"task_id": "test"})  # Missing task_type
    
    def test_adapter_cleanup(self):
        """Test adapter cleanup."""
        adapter = MockAdapter({})
        
        # Should not raise any exceptions
        adapter.cleanup()


class TestAdapterRegistry:
    """Test cases for AdapterRegistry."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = AdapterRegistry()
    
    def test_register_adapter_class(self):
        """Test registering an adapter class."""
        self.registry.register_adapter_class("mock", MockAdapter)
        
        assert "mock" in self.registry.list_adapter_classes()
    
    def test_register_adapter_class_duplicate(self):
        """Test registering duplicate adapter class names."""
        self.registry.register_adapter_class("mock", MockAdapter)
        
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register_adapter_class("mock", MockAdapter)
    
    def test_register_adapter_class_invalid_type(self):
        """Test registering invalid adapter class."""
        class NotAnAdapter:
            pass
        
        with pytest.raises(ValueError, match="must inherit from BenchmarkAdapter"):
            self.registry.register_adapter_class("invalid", NotAnAdapter)
    
    def test_create_adapter_success(self):
        """Test successful adapter creation."""
        self.registry.register_adapter_class("mock", MockAdapter)
        
        adapter = self.registry.create_adapter("mock", {})
        
        assert adapter is not None
        assert adapter.is_ready()
        assert "mock" in self.registry.list_adapters()
    
    def test_create_adapter_unregistered(self):
        """Test creating adapter from unregistered class."""
        with pytest.raises(ValueError, match="not registered"):
            self.registry.create_adapter("nonexistent", {})
    
    def test_create_adapter_initialization_failure(self):
        """Test adapter creation with initialization failure."""
        self.registry.register_adapter_class("failing", FailingAdapter)
        
        with pytest.raises(AdapterError, match="This adapter always fails"):
            self.registry.create_adapter("failing", {})
    
    def test_get_adapter(self):
        """Test getting adapter by name."""
        self.registry.register_adapter_class("mock", MockAdapter)
        created_adapter = self.registry.create_adapter("mock", {})
        
        retrieved_adapter = self.registry.get_adapter("mock")
        
        assert retrieved_adapter is created_adapter
    
    def test_get_adapter_nonexistent(self):
        """Test getting nonexistent adapter."""
        adapter = self.registry.get_adapter("nonexistent")
        
        assert adapter is None
    
    def test_get_adapter_info(self):
        """Test getting adapter information."""
        self.registry.register_adapter_class("mock", MockAdapter)
        self.registry.create_adapter("mock", {})
        
        info = self.registry.get_adapter_info("mock")
        
        assert info is not None
        assert info.name == "mock_adapter"
        assert info.version == "1.0.0"
    
    def test_get_adapters_by_task_type(self):
        """Test filtering adapters by task type."""
        self.registry.register_adapter_class("mock", MockAdapter)
        self.registry.create_adapter("mock", {})
        
        single_turn_adapters = self.registry.get_adapters_by_task_type(TaskType.SINGLE_TURN)
        multi_turn_adapters = self.registry.get_adapters_by_task_type(TaskType.MULTI_TURN)
        
        assert "mock" in single_turn_adapters
        assert "mock" in multi_turn_adapters
    
    def test_remove_adapter(self):
        """Test removing an adapter."""
        self.registry.register_adapter_class("mock", MockAdapter)
        self.registry.create_adapter("mock", {})
        
        assert "mock" in self.registry.list_adapters()
        
        removed = self.registry.remove_adapter("mock")
        
        assert removed is True
        assert "mock" not in self.registry.list_adapters()
    
    def test_remove_nonexistent_adapter(self):
        """Test removing nonexistent adapter."""
        removed = self.registry.remove_adapter("nonexistent")
        
        assert removed is False
    
    def test_cleanup_all(self):
        """Test cleaning up all adapters."""
        self.registry.register_adapter_class("mock1", MockAdapter)
        self.registry.register_adapter_class("mock2", MockAdapter)
        self.registry.create_adapter("mock1", {})
        self.registry.create_adapter("mock2", {})
        
        assert len(self.registry.list_adapters()) == 2
        
        self.registry.cleanup_all()
        
        assert len(self.registry.list_adapters()) == 0
    
    def test_callbacks(self):
        """Test initialization and error callbacks."""
        init_callback = Mock()
        error_callback = Mock()
        
        self.registry.add_initialization_callback(init_callback)
        self.registry.add_error_callback(error_callback)
        
        # Test successful initialization callback
        self.registry.register_adapter_class("mock", MockAdapter)
        adapter = self.registry.create_adapter("mock", {})
        
        init_callback.assert_called_once_with("mock", adapter)
        error_callback.assert_not_called()
        
        # Reset mocks
        init_callback.reset_mock()
        error_callback.reset_mock()
        
        # Test error callback
        self.registry.register_adapter_class("failing", FailingAdapter)
        
        with pytest.raises(AdapterError):
            self.registry.create_adapter("failing", {})
        
        init_callback.assert_not_called()
        error_callback.assert_called_once()
        assert "failing" in error_callback.call_args[0][0]
    
    def test_get_status_summary(self):
        """Test getting status summary of all adapters."""
        self.registry.register_adapter_class("mock", MockAdapter)
        self.registry.create_adapter("mock", {})
        
        summary = self.registry.get_status_summary()
        
        assert "mock" in summary
        assert summary["mock"]["status"] == "ready"
        assert summary["mock"]["version"] == "1.0.0"
        assert "single_turn" in summary["mock"]["supported_task_types"]
        assert "multi_turn" in summary["mock"]["supported_task_types"]


class TestGlobalRegistry:
    """Test cases for global registry functions."""
    
    def test_get_adapter_registry(self):
        """Test getting global adapter registry."""
        registry = get_adapter_registry()
        
        assert isinstance(registry, AdapterRegistry)
        
        # Should return the same instance
        registry2 = get_adapter_registry()
        assert registry is registry2
    
    def test_register_adapter_class_global(self):
        """Test registering adapter class globally."""
        register_adapter_class("global_mock", MockAdapter)
        
        registry = get_adapter_registry()
        assert "global_mock" in registry.list_adapter_classes()
    
    def test_create_adapter_global(self):
        """Test creating adapter using global functions."""
        register_adapter_class("global_mock2", MockAdapter)
        
        adapter = create_adapter("global_mock2", {})
        
        assert adapter is not None
        assert adapter.is_ready()
    
    def test_get_adapter_global(self):
        """Test getting adapter using global function."""
        register_adapter_class("global_mock3", MockAdapter)
        created_adapter = create_adapter("global_mock3", {})
        
        retrieved_adapter = get_adapter("global_mock3")
        
        assert retrieved_adapter is created_adapter


class TestAdapterErrorHandling:
    """Test cases for adapter error handling."""
    
    def test_safe_execute_success(self):
        """Test successful operation execution."""
        adapter = MockAdapter({})
        
        def test_operation(x, y):
            return x + y
        
        result = adapter._safe_execute(test_operation, "addition", 2, 3)
        
        assert result == 5
    
    def test_safe_execute_failure(self):
        """Test failed operation execution."""
        adapter = MockAdapter({})
        
        def failing_operation():
            raise ValueError("Test error")
        
        with pytest.raises(AdapterError, match="Failed to execute test_op"):
            adapter._safe_execute(failing_operation, "test_op")
    
    def test_adapter_status_transitions(self):
        """Test adapter status transitions."""
        adapter = MockAdapter({})
        
        # Initial status
        assert adapter.get_status() == AdapterStatus.UNINITIALIZED
        
        # Successful initialization
        adapter.initialize()
        assert adapter.get_status() == AdapterStatus.READY
        
        # Manual error status
        adapter._set_status(AdapterStatus.ERROR, "Test error")
        assert adapter.get_status() == AdapterStatus.ERROR
        assert adapter.get_error_message() == "Test error"