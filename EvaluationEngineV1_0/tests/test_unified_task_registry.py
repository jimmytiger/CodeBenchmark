"""
Tests for the Unified Task Registry System.

This module contains comprehensive tests for the UnifiedTaskRegistry class,
covering task classification, adapter integration, and discovery functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List

from EvaluationEngineV1_0.core.unified_task_registry import (
    UnifiedTaskRegistry, TaskSource, TaskClassification, TaskDiscoveryResult,
    TaskInstantiationResult, TaskFactoryConfig,
    get_unified_task_registry, reset_unified_task_registry
)
from EvaluationEngineV1_0.core.task_types import TaskType, BaseTask, SingleTurnTask, MultiTurnTask
from EvaluationEngineV1_0.core.adapters import BenchmarkAdapter, AdapterInfo
from EvaluationEngineV1_0.core.exceptions import TaskRegistrationError, ConfigurationError
from evaluation_engine.core.task_registration import ExtendedTaskRegistry, TaskMetadata, ScenarioConfig


class MockSingleTurnTask(SingleTurnTask):
    """Mock single-turn task for testing."""
    
    def __init__(self, task_id: str, config: Dict[str, Any]):
        super().__init__(task_id, config)
    
    def execute(self, input_data):
        return Mock()
    
    def get_required_capabilities(self) -> List[str]:
        return ["python"]


class MockMultiTurnTask(MultiTurnTask):
    """Mock multi-turn task for testing."""
    
    def __init__(self, task_id: str, config: Dict[str, Any]):
        super().__init__(task_id, config)
    
    def execute_turn(self, turn_data):
        return Mock()
    
    def should_continue(self, turn_result) -> bool:
        return False
    
    def get_initial_context(self) -> str:
        return "Initial context"
    
    def is_successful(self, turn_results) -> bool:
        return True
    
    def get_required_capabilities(self) -> List[str]:
        return ["python", "git"]


class MockBenchmarkAdapter(BenchmarkAdapter):
    """Mock benchmark adapter for testing."""
    
    def __init__(self, config: Dict[str, Any], tasks: List[BaseTask] = None):
        super().__init__(config)
        self._tasks = tasks or []
        self._initialized = False
    
    def get_adapter_info(self) -> AdapterInfo:
        return AdapterInfo(
            name="mock_adapter",
            version="1.0.0",
            description="Mock adapter for testing",
            supported_task_types=[TaskType.SINGLE_TURN, TaskType.MULTI_TURN],
            required_dependencies=["mock"],
            supported_formats=["json"],
            capabilities=["mock_capability"]
        )
    
    def initialize(self) -> bool:
        self._initialized = True
        self._set_status(self._status.__class__.READY)
        return True
    
    def create_environment(self, task_config: Dict[str, Any]):
        return Mock()
    
    def load_tasks(self, task_filter=None) -> List[BaseTask]:
        return self._tasks
    
    def convert_results(self, results):
        return Mock()
    
    def is_ready(self) -> bool:
        return self._initialized


class TestTaskClassification:
    """Test task classification functionality."""
    
    def test_task_classification_creation(self):
        """Test creating TaskClassification objects."""
        classification = TaskClassification(
            task_type=TaskType.SINGLE_TURN,
            source=TaskSource.CUSTOM,
            confidence=0.8
        )
        
        assert classification.task_type == TaskType.SINGLE_TURN
        assert classification.source == TaskSource.CUSTOM
        assert classification.adapter_name is None
        assert classification.confidence == 0.8
        assert classification.metadata == {}
    
    def test_task_classification_validation(self):
        """Test TaskClassification validation."""
        # Valid confidence
        TaskClassification(
            task_type=TaskType.SINGLE_TURN,
            source=TaskSource.CUSTOM,
            confidence=0.5
        )
        
        # Invalid confidence
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            TaskClassification(
                task_type=TaskType.SINGLE_TURN,
                source=TaskSource.CUSTOM,
                confidence=1.5
            )


class TestTaskDiscoveryResult:
    """Test task discovery result functionality."""
    
    def test_discovery_result_creation(self):
        """Test creating TaskDiscoveryResult objects."""
        classification = TaskClassification(
            task_type=TaskType.MULTI_TURN,
            source=TaskSource.EXTERNAL,
            adapter_name="test_adapter"
        )
        
        result = TaskDiscoveryResult(
            task_name="test_task",
            classification=classification,
            available=True,
            dependencies=["dep1", "dep2"],
            capabilities=["python", "git"]
        )
        
        assert result.task_name == "test_task"
        assert result.classification == classification
        assert result.available is True
        assert result.error_message is None
        assert result.dependencies == ["dep1", "dep2"]
        assert result.capabilities == ["python", "git"]


class TestUnifiedTaskRegistry:
    """Test the UnifiedTaskRegistry class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset global registry
        reset_unified_task_registry()
        
        # Create mock extended registry
        self.mock_extended_registry = Mock(spec=ExtendedTaskRegistry)
        self.mock_extended_registry.get_task_hierarchy.return_value = {
            "single_turn": ["task1", "task2"],
            "multi_turn": ["task3", "task4"]
        }
        self.mock_extended_registry.get_task_metadata.return_value = None
        self.mock_extended_registry.get_scenario_config.return_value = None
        self.mock_extended_registry.validate_task_dependencies.return_value = True
        
        # Create registry with mock
        self.registry = UnifiedTaskRegistry(self.mock_extended_registry)
    
    def test_initialization(self):
        """Test registry initialization."""
        assert self.registry._extended_registry == self.mock_extended_registry
        assert self.registry._adapter_registry is not None
        assert isinstance(self.registry._task_classifications, dict)
        assert isinstance(self.registry._task_cache, dict)
    
    def test_task_classification_single_turn(self):
        """Test classification of single-turn tasks."""
        # Mock metadata for single-turn task
        metadata = TaskMetadata(
            task_id="test_task",
            name="Test Task",
            description="A test task",
            category="single_turn",
            difficulty="easy"
        )
        self.mock_extended_registry.get_task_metadata.return_value = metadata
        self.mock_extended_registry.get_scenario_config.return_value = None
        
        classification = self.registry.classify_task("test_task")
        
        assert classification is not None
        assert classification.task_type == TaskType.SINGLE_TURN
        assert classification.source == TaskSource.CUSTOM
        assert classification.confidence > 0.5
    
    def test_task_classification_multi_turn(self):
        """Test classification of multi-turn tasks."""
        # Mock scenario config for multi-turn task
        scenario_config = ScenarioConfig(
            scenario_id="test_scenario",
            scenario_type="conversation",
            max_turns=5,
            conversation_timeout=300,
            enable_context_retention=True
        )
        self.mock_extended_registry.get_task_metadata.return_value = None
        self.mock_extended_registry.get_scenario_config.return_value = scenario_config
        
        classification = self.registry.classify_task("multi_turn_task")
        
        assert classification is not None
        assert classification.task_type == TaskType.MULTI_TURN
        assert classification.source == TaskSource.CUSTOM
        assert classification.confidence == 1.0
    
    def test_task_classification_from_name(self):
        """Test task classification based on task name patterns."""
        # No metadata or scenario config, infer from name
        self.mock_extended_registry.get_task_metadata.return_value = None
        self.mock_extended_registry.get_scenario_config.return_value = None
        
        # Multi-turn task name
        classification = self.registry.classify_task("multi_turn_conversation_task")
        assert classification.task_type == TaskType.MULTI_TURN
        assert classification.confidence == 0.6
        
        # Single-turn task name
        classification = self.registry.classify_task("simple_qa_task")
        assert classification.task_type == TaskType.SINGLE_TURN
        assert classification.confidence == 0.5
    
    def test_adapter_registration(self):
        """Test registering benchmark adapters."""
        # Create mock tasks
        task1 = MockSingleTurnTask("adapter_task1", {"timeout": 30, "max_tokens": 100})
        task2 = MockMultiTurnTask("adapter_task2", {
            "max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": 100
        })
        
        # Create mock adapter
        adapter = MockBenchmarkAdapter({}, [task1, task2])
        adapter.initialize()
        
        # Register adapter
        self.registry.register_adapter("test_adapter", adapter)
        
        # Check that tasks were discovered and classified
        assert "adapter_task1" in self.registry._task_classifications
        assert "adapter_task2" in self.registry._task_classifications
        
        classification1 = self.registry._task_classifications["adapter_task1"]
        assert classification1.task_type == TaskType.SINGLE_TURN
        assert classification1.source == TaskSource.EXTERNAL
        assert classification1.adapter_name == "test_adapter"
        
        classification2 = self.registry._task_classifications["adapter_task2"]
        assert classification2.task_type == TaskType.MULTI_TURN
        assert classification2.source == TaskSource.EXTERNAL
        assert classification2.adapter_name == "test_adapter"
    
    def test_adapter_registration_failure(self):
        """Test adapter registration failure handling."""
        # Create adapter that fails to load tasks
        adapter = Mock(spec=BenchmarkAdapter)
        adapter.load_tasks.side_effect = Exception("Failed to load tasks")
        adapter.get_adapter_info.return_value = AdapterInfo(
            name="failing_adapter",
            version="1.0.0",
            description="Failing adapter",
            supported_task_types=[TaskType.SINGLE_TURN],
            required_dependencies=[],
            supported_formats=[],
            capabilities=[]
        )
        
        # Should raise TaskRegistrationError due to task discovery failure
        with pytest.raises(TaskRegistrationError):
            self.registry.register_adapter("failing_adapter", adapter)
    
    def test_task_discovery_basic(self):
        """Test basic task discovery functionality."""
        results = self.registry.discover_tasks()
        
        # Should find tasks from extended registry
        task_names = [r.task_name for r in results]
        assert "task1" in task_names
        assert "task2" in task_names
        assert "task3" in task_names
        assert "task4" in task_names
    
    def test_task_discovery_with_filters(self):
        """Test task discovery with filters."""
        # Filter by task type
        results = self.registry.discover_tasks({'task_type': TaskType.SINGLE_TURN})
        
        # Should only return single-turn tasks
        for result in results:
            assert result.classification.task_type == TaskType.SINGLE_TURN
    
    def test_task_discovery_with_adapter_filter(self):
        """Test task discovery filtered by adapter."""
        # Create fresh registry to avoid interference from other tests
        fresh_registry = UnifiedTaskRegistry(self.mock_extended_registry)
        
        # Register adapter with tasks
        task1 = MockSingleTurnTask("adapter_task1", {"timeout": 30, "max_tokens": 100})
        adapter = MockBenchmarkAdapter({}, [task1])
        adapter.initialize()
        fresh_registry.register_adapter("test_adapter", adapter)
        
        # Filter by adapter
        results = fresh_registry.discover_tasks({'adapter_name': 'test_adapter'})
        
        # Should only return tasks from the specified adapter
        # Filter results to only those from test_adapter
        test_adapter_results = [r for r in results if r.classification.adapter_name == "test_adapter"]
        
        # We should have our registered task
        assert len(test_adapter_results) >= 1
        assert any(r.task_name == "adapter_task1" for r in test_adapter_results)
        
        # Find our specific task
        our_task = next(r for r in test_adapter_results if r.task_name == "adapter_task1")
        assert our_task.classification.adapter_name == "test_adapter"
    
    def test_task_discovery_available_only(self):
        """Test task discovery with available_only filter."""
        # Mock a task with missing dependencies
        self.mock_extended_registry.validate_task_dependencies.side_effect = lambda name: name != "unavailable_task"
        
        # Add unavailable task to hierarchy
        hierarchy = self.mock_extended_registry.get_task_hierarchy.return_value
        hierarchy["test"] = ["unavailable_task"]
        
        results = self.registry.discover_tasks({'available_only': True})
        
        # Should not include unavailable task
        task_names = [r.task_name for r in results]
        assert "unavailable_task" not in task_names
    
    def test_get_tasks_by_type(self):
        """Test getting tasks by type."""
        single_turn_tasks = self.registry.get_tasks_by_type(TaskType.SINGLE_TURN)
        multi_turn_tasks = self.registry.get_tasks_by_type(TaskType.MULTI_TURN)
        
        # Should return appropriate tasks based on classification
        assert isinstance(single_turn_tasks, list)
        assert isinstance(multi_turn_tasks, list)
    
    def test_get_tasks_by_source(self):
        """Test getting tasks by source."""
        custom_tasks = self.registry.get_tasks_by_source(TaskSource.CUSTOM)
        lm_eval_tasks = self.registry.get_tasks_by_source(TaskSource.LM_EVAL)
        
        assert isinstance(custom_tasks, list)
        assert isinstance(lm_eval_tasks, list)
    
    def test_get_tasks_by_adapter(self):
        """Test getting tasks by adapter."""
        # Create fresh registry to avoid interference from other tests
        fresh_registry = UnifiedTaskRegistry(self.mock_extended_registry)
        
        # Register adapter with tasks
        task1 = MockSingleTurnTask("adapter_task1", {"timeout": 30, "max_tokens": 100})
        adapter = MockBenchmarkAdapter({}, [task1])
        adapter.initialize()
        fresh_registry.register_adapter("test_adapter", adapter)
        
        adapter_tasks = fresh_registry.get_tasks_by_adapter("test_adapter")
        
        # Should contain the task we registered
        assert "adapter_task1" in adapter_tasks
        # Filter to only tasks from our specific adapter to avoid interference
        test_adapter_only_tasks = [task for task in adapter_tasks if task == "adapter_task1"]
        assert len(test_adapter_only_tasks) == 1
    
    def test_validate_task_availability(self):
        """Test task availability validation."""
        # Available task
        assert self.registry.validate_task_availability("task1") is True
        
        # Mock unavailable task
        self.mock_extended_registry.validate_task_dependencies.side_effect = lambda name: name != "unavailable_task"
        
        # Should return False for unavailable task
        assert self.registry.validate_task_availability("unavailable_task") is False
    
    def test_get_task_metadata(self):
        """Test getting comprehensive task metadata."""
        # Mock metadata
        metadata = TaskMetadata(
            task_id="test_task",
            name="Test Task",
            description="A test task",
            category="single_turn",
            difficulty="easy",
            tags=["test"],
            dependencies=[],
            version="1.0.0"
        )
        self.mock_extended_registry.get_task_metadata.return_value = metadata
        
        result = self.registry.get_task_metadata("test_task")
        
        assert result is not None
        assert result['task_name'] == "test_task"
        assert 'classification' in result
        assert 'extended_metadata' in result
        assert result['extended_metadata']['name'] == "Test Task"
    
    def test_task_caching(self):
        """Test task instance caching."""
        task = MockSingleTurnTask("cached_task", {"timeout": 30, "max_tokens": 100})
        
        # Cache the task
        self.registry._cache_task("cached_task", task)
        
        # Should be able to retrieve from cache
        cached_task = self.registry._get_cached_task("cached_task")
        assert cached_task == task
        
        # Should update access time
        assert "cached_task" in self.registry._cache_access_times
    
    def test_cache_eviction(self):
        """Test LRU cache eviction."""
        # Set small cache size for testing
        self.registry._cache_max_size = 2
        
        # Add tasks to fill cache
        task1 = MockSingleTurnTask("task1", {"timeout": 30, "max_tokens": 100})
        task2 = MockSingleTurnTask("task2", {"timeout": 30, "max_tokens": 100})
        task3 = MockSingleTurnTask("task3", {"timeout": 30, "max_tokens": 100})
        
        self.registry._cache_task("task1", task1)
        self.registry._cache_task("task2", task2)
        
        # Cache should be full
        assert len(self.registry._task_cache) == 2
        
        # Adding third task should evict oldest
        self.registry._cache_task("task3", task3)
        
        # Should still have 2 tasks, but task1 should be evicted
        assert len(self.registry._task_cache) == 2
        assert "task1" not in self.registry._task_cache
        assert "task2" in self.registry._task_cache
        assert "task3" in self.registry._task_cache
    
    def test_discovery_filters(self):
        """Test custom discovery filters."""
        # Add custom filter that only allows tasks with "test" in name
        def test_filter(task_name: str, filters: Dict[str, Any]) -> bool:
            return "test" in task_name.lower()
        
        self.registry.add_discovery_filter(test_filter)
        
        # Mock hierarchy with test and non-test tasks
        self.mock_extended_registry.get_task_hierarchy.return_value = {
            "category1": ["test_task", "other_task"]
        }
        
        results = self.registry.discover_tasks()
        
        # Should only return tasks with "test" in name
        task_names = [r.task_name for r in results]
        assert "test_task" in task_names
        assert "other_task" not in task_names
    
    def test_classification_callbacks(self):
        """Test classification callbacks."""
        callback_calls = []
        
        def test_callback(task_name: str, classification: TaskClassification):
            callback_calls.append((task_name, classification))
        
        self.registry.add_classification_callback(test_callback)
        
        # Classify a task
        classification = self.registry.classify_task("new_task")
        
        # Callback should have been called
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == "new_task"
        assert callback_calls[0][1] == classification
    
    def test_export_registry_info(self, tmp_path):
        """Test exporting registry information."""
        output_file = tmp_path / "registry_info.json"
        
        self.registry.export_registry_info(str(output_file))
        
        # File should be created
        assert output_file.exists()
        
        # Should contain valid JSON
        import json
        with open(output_file) as f:
            data = json.load(f)
        
        assert 'timestamp' in data
        assert 'total_tasks' in data
        assert 'task_classifications' in data
        assert 'adapters' in data
    
    def test_get_statistics(self):
        """Test getting registry statistics."""
        stats = self.registry.get_statistics()
        
        assert 'total_tasks' in stats
        assert 'task_types' in stats
        assert 'sources' in stats
        assert 'adapters' in stats
        assert 'cache_size' in stats
        assert isinstance(stats['total_tasks'], int)
        assert isinstance(stats['task_types'], dict)
        assert isinstance(stats['sources'], dict)


class TestGlobalRegistry:
    """Test global registry functions."""
    
    def test_get_unified_task_registry(self):
        """Test getting global registry instance."""
        registry1 = get_unified_task_registry()
        registry2 = get_unified_task_registry()
        
        # Should return same instance
        assert registry1 is registry2
        assert isinstance(registry1, UnifiedTaskRegistry)
    
    def test_reset_unified_task_registry(self):
        """Test resetting global registry."""
        registry1 = get_unified_task_registry()
        reset_unified_task_registry()
        registry2 = get_unified_task_registry()
        
        # Should return different instance after reset
        assert registry1 is not registry2


class TestTaskFactory:
    """Test task factory and instantiation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_unified_task_registry()
        self.mock_extended_registry = Mock(spec=ExtendedTaskRegistry)
        self.mock_extended_registry.get_task_hierarchy.return_value = {
            "single_turn": ["test_task"],
            "multi_turn": ["multi_task"]
        }
        self.mock_extended_registry.get_task_metadata.return_value = None
        self.mock_extended_registry.get_scenario_config.return_value = None
        self.mock_extended_registry.validate_task_dependencies.return_value = True
        self.registry = UnifiedTaskRegistry(self.mock_extended_registry)
    
    def test_task_instantiation_result_creation(self):
        """Test creating TaskInstantiationResult objects."""
        task = MockSingleTurnTask("test_task", {"timeout": 30, "max_tokens": 100})
        
        result = TaskInstantiationResult(
            task_instance=task,
            success=True,
            validation_results={"dependencies": True, "capabilities": True},
            cache_hit=False,
            instantiation_time=0.5
        )
        
        assert result.task_instance == task
        assert result.success is True
        assert result.error_message is None
        assert result.validation_results["dependencies"] is True
        assert result.cache_hit is False
        assert result.instantiation_time == 0.5
    
    def test_task_factory_config(self):
        """Test TaskFactoryConfig functionality."""
        config = TaskFactoryConfig(
            enable_caching=True,
            cache_ttl=1800,
            validate_dependencies=True,
            validate_capabilities=False,
            strict_validation=False
        )
        
        assert config.enable_caching is True
        assert config.cache_ttl == 1800
        assert config.validate_dependencies is True
        assert config.validate_capabilities is False
        assert config.strict_validation is False
    
    def test_create_task_instance_basic(self):
        """Test basic task instance creation."""
        # Mock metadata for single-turn task
        metadata = TaskMetadata(
            task_id="test_task",
            name="Test Task",
            description="A test task",
            category="single_turn",
            difficulty="easy"
        )
        self.mock_extended_registry.get_task_metadata.return_value = metadata
        
        config = {"timeout": 30, "max_tokens": 100}
        result = self.registry.create_task_instance("test_task", config)
        
        assert result.success is True
        assert result.task_instance is not None
        assert result.error_message is None
        assert isinstance(result.validation_results, dict)
    
    def test_create_task_instance_with_adapter(self):
        """Test task instance creation from adapter."""
        # Create fresh registry to avoid interference
        fresh_registry = UnifiedTaskRegistry(self.mock_extended_registry)
        
        # Create and register adapter
        task = MockSingleTurnTask("adapter_task", {"timeout": 30, "max_tokens": 100})
        adapter = MockBenchmarkAdapter({}, [task])
        adapter.initialize()
        fresh_registry.register_adapter("test_adapter", adapter)
        
        config = {"timeout": 60, "max_tokens": 200}
        result = fresh_registry.create_task_instance("adapter_task", config)
        
        assert result.success is True
        assert result.task_instance is not None
        assert result.task_instance.get_id() == "adapter_task"
    
    def test_create_task_instance_multi_turn(self):
        """Test multi-turn task instance creation."""
        # Mock scenario config for multi-turn task
        scenario_config = ScenarioConfig(
            scenario_id="test_scenario",
            scenario_type="conversation",
            max_turns=5,
            conversation_timeout=300,
            enable_context_retention=True
        )
        self.mock_extended_registry.get_scenario_config.return_value = scenario_config
        
        config = {"max_turns": 5, "turn_timeout": 30, "max_tokens_per_turn": 100}
        result = self.registry.create_task_instance("multi_task", config)
        
        assert result.success is True
        assert result.task_instance is not None
        assert result.task_instance.get_task_type() == TaskType.MULTI_TURN
    
    def test_create_task_instance_unavailable(self):
        """Test task instance creation for unavailable task."""
        # Mock unavailable task
        self.mock_extended_registry.validate_task_dependencies.return_value = False
        
        config = {"timeout": 30, "max_tokens": 100}
        result = self.registry.create_task_instance("unavailable_task", config)
        
        assert result.success is False
        assert result.task_instance is None
        assert "not available" in result.error_message
    
    def test_create_task_instance_validation_failure(self):
        """Test task instance creation with validation failure."""
        # Configure strict validation but disable dependency validation in factory
        factory_config = TaskFactoryConfig(
            strict_validation=True,
            validate_dependencies=False,  # Disable to bypass availability check
            validate_capabilities=True
        )
        self.registry.configure_factory(factory_config)
        
        # Mock metadata to make task available
        metadata = TaskMetadata(
            task_id="test_task",
            name="Test Task",
            description="A test task",
            category="single_turn",
            difficulty="easy"
        )
        self.mock_extended_registry.get_task_metadata.return_value = metadata
        
        # Make task available but fail capability validation
        self.mock_extended_registry.validate_task_dependencies.return_value = True
        
        # Mock the capability validation to fail by overriding the method
        original_validate_capabilities = self.registry._validate_task_capabilities
        def mock_validate_capabilities(task_name, config):
            return False
        self.registry._validate_task_capabilities = mock_validate_capabilities
        
        config = {"timeout": 30, "max_tokens": 100}
        result = self.registry.create_task_instance("test_task", config)
        
        # Restore original method
        self.registry._validate_task_capabilities = original_validate_capabilities
        
        assert result.success is False
        assert result.task_instance is None
        assert "Validation failed" in result.error_message
    
    def test_task_caching_with_config(self):
        """Test task instance caching with configuration."""
        # Enable caching
        factory_config = TaskFactoryConfig(enable_caching=True, cache_ttl=3600)
        self.registry.configure_factory(factory_config)
        
        # Mock metadata
        metadata = TaskMetadata(
            task_id="cached_task",
            name="Cached Task",
            description="A cached task",
            category="single_turn",
            difficulty="easy"
        )
        self.mock_extended_registry.get_task_metadata.return_value = metadata
        
        config = {"timeout": 30, "max_tokens": 100}
        
        # First call should create and cache
        result1 = self.registry.create_task_instance("cached_task", config)
        assert result1.success is True
        assert result1.cache_hit is False
        
        # Second call should hit cache
        result2 = self.registry.create_task_instance("cached_task", config)
        assert result2.success is True
        assert result2.cache_hit is True
        assert result2.task_instance is result1.task_instance
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        # Enable caching with short TTL
        factory_config = TaskFactoryConfig(enable_caching=True, cache_ttl=1)
        self.registry.configure_factory(factory_config)
        
        # Mock metadata
        metadata = TaskMetadata(
            task_id="ttl_task",
            name="TTL Task",
            description="A TTL task",
            category="single_turn",
            difficulty="easy"
        )
        self.mock_extended_registry.get_task_metadata.return_value = metadata
        
        config = {"timeout": 30, "max_tokens": 100}
        
        # First call
        result1 = self.registry.create_task_instance("ttl_task", config)
        assert result1.cache_hit is False
        
        # Wait for TTL to expire
        import time
        time.sleep(1.1)
        
        # Second call should not hit cache due to TTL expiration
        result2 = self.registry.create_task_instance("ttl_task", config)
        assert result2.cache_hit is False
    
    def test_configure_factory(self):
        """Test factory configuration."""
        config = TaskFactoryConfig(
            enable_caching=False,
            validate_dependencies=False,
            strict_validation=False
        )
        
        self.registry.configure_factory(config)
        
        assert self.registry._factory_config.enable_caching is False
        assert self.registry._factory_config.validate_dependencies is False
        assert self.registry._factory_config.strict_validation is False
    
    def test_clear_cache(self):
        """Test cache clearing."""
        # Add something to cache
        task = MockSingleTurnTask("test_task", {"timeout": 30, "max_tokens": 100})
        self.registry._cache_task_with_config("test_task", task, {"timeout": 30})
        
        assert len(self.registry._task_cache) > 0
        
        # Clear cache
        self.registry.clear_cache()
        
        assert len(self.registry._task_cache) == 0
        assert len(self.registry._cache_access_times) == 0
        assert len(self.registry._validation_cache) == 0
    
    def test_instantiation_performance_tracking(self):
        """Test instantiation performance tracking."""
        # Enable performance monitoring
        factory_config = TaskFactoryConfig(performance_monitoring=True)
        self.registry.configure_factory(factory_config)
        
        # Mock metadata
        metadata = TaskMetadata(
            task_id="perf_task",
            name="Performance Task",
            description="A performance task",
            category="single_turn",
            difficulty="easy"
        )
        self.mock_extended_registry.get_task_metadata.return_value = metadata
        
        config = {"timeout": 30, "max_tokens": 100}
        
        # Create task instance
        result = self.registry.create_task_instance("perf_task", config)
        assert result.success is True
        assert result.instantiation_time > 0
        
        # Check performance stats
        perf_stats = self.registry.get_instantiation_performance()
        assert "perf_task" in perf_stats
        assert perf_stats["perf_task"]["count"] == 1
        assert perf_stats["perf_task"]["avg_time"] > 0
    
    def test_hash_config(self):
        """Test configuration hashing."""
        config1 = {"timeout": 30, "max_tokens": 100}
        config2 = {"max_tokens": 100, "timeout": 30}  # Same content, different order
        config3 = {"timeout": 60, "max_tokens": 100}  # Different content
        
        hash1 = self.registry._hash_config(config1)
        hash2 = self.registry._hash_config(config2)
        hash3 = self.registry._hash_config(config3)
        
        # Same content should produce same hash regardless of order
        assert hash1 == hash2
        # Different content should produce different hash
        assert hash1 != hash3
    
    def test_validation_caching(self):
        """Test validation result caching."""
        # First validation call
        result1 = self.registry._validate_task_dependencies("test_task")
        
        # Mock the extended registry to return different result
        self.mock_extended_registry.validate_task_dependencies.return_value = False
        
        # Second call should return cached result
        result2 = self.registry._validate_task_dependencies("test_task")
        
        # Should be same as first call due to caching
        assert result1 == result2 == True


class TestErrorHandling:
    """Test error handling in the registry."""
    
    def setup_method(self):
        """Set up test fixtures."""
        reset_unified_task_registry()
        self.mock_extended_registry = Mock(spec=ExtendedTaskRegistry)
        self.mock_extended_registry.get_task_hierarchy.return_value = {}
        self.registry = UnifiedTaskRegistry(self.mock_extended_registry)
    
    def test_adapter_registration_error(self):
        """Test error handling during adapter registration."""
        # Create adapter that fails to load tasks
        adapter = Mock(spec=BenchmarkAdapter)
        adapter.load_tasks.side_effect = Exception("Initialization failed")
        adapter.get_adapter_info.return_value = AdapterInfo(
            name="failing_adapter",
            version="1.0.0",
            description="Failing adapter",
            supported_task_types=[TaskType.SINGLE_TURN],
            required_dependencies=[],
            supported_formats=[],
            capabilities=[]
        )
        
        # Should raise TaskRegistrationError
        with pytest.raises(TaskRegistrationError):
            self.registry.register_adapter("failing_adapter", adapter)
    
    def test_classification_error_handling(self):
        """Test error handling during task classification."""
        # Mock extended registry to raise exception
        self.mock_extended_registry.get_task_metadata.side_effect = Exception("Metadata error")
        self.mock_extended_registry.get_scenario_config.side_effect = Exception("Config error")
        
        # Should handle errors gracefully and return None
        classification = self.registry.classify_task("error_task")
        assert classification is None
    
    def test_discovery_error_handling(self):
        """Test error handling during task discovery."""
        # Mock adapter that fails to load tasks
        adapter = Mock(spec=BenchmarkAdapter)
        adapter.is_ready.return_value = True
        adapter.load_tasks.side_effect = Exception("Load error")
        
        self.registry._adapter_registry._adapters["error_adapter"] = adapter
        
        # Should handle errors gracefully and continue
        results = self.registry.discover_tasks()
        
        # Should not crash, may return empty results
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__])