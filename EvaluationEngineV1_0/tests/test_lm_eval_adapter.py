"""
Tests for the LM-Eval compatibility adapter.

This module contains comprehensive tests for the lm-eval integration adapter,
including task detection, environment wrapping, and result conversion.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import json

from EvaluationEngineV1_0.core.lm_eval_adapter import (
    LMEvalAdapter,
    LMEvalEnvironment,
    LMEvalTaskWrapper,
    LMEvalTaskInfo,
    LM_EVAL_AVAILABLE
)
from EvaluationEngineV1_0.core.adapters import AdapterInfo, StandardizedResult, AdapterStatus
from EvaluationEngineV1_0.core.task_types import TaskType
from EvaluationEngineV1_0.core.exceptions import AdapterError, ConfigurationError, TaskExecutionError


# Mock lm-eval components for testing
class MockLMEvalTask:
    """Mock lm-eval task for testing."""
    
    def __init__(self, name: str, output_type: str = "generate_until"):
        self.name = name
        self.OUTPUT_TYPE = output_type
        self.DESCRIPTION = f"Mock task {name}"
        self.VERSION = "1.0"
        self.DATASET_PATH = f"mock/{name}"
        self.DATASET_NAME = name
        self.num_fewshot = 0
        
        # Mock evaluation documents
        self.eval_docs = [
            {"input": f"Question {i}", "target": f"Answer {i}"}
            for i in range(3)
        ]
    
    def doc_to_text(self, doc):
        return doc.get("input", "")
    
    def doc_to_target(self, doc):
        return doc.get("target", "")


class MockTaskManager:
    """Mock TaskManager for testing."""
    
    def __init__(self):
        self.tasks = {
            "test_task": MockLMEvalTask("test_task"),
            "mock_single_turn": MockLMEvalTask("mock_single_turn"),
            "mock_multi_turn_conversation": MockLMEvalTask("mock_multi_turn_conversation"),
            "mock_dialogue_task": MockLMEvalTask("mock_dialogue_task"),
            "hellaswag": MockLMEvalTask("hellaswag", "multiple_choice"),
            "gsm8k": MockLMEvalTask("gsm8k", "generate_until")
        }
    
    def load_task_or_group(self, task_names: List[str]) -> Dict[str, MockLMEvalTask]:
        result = {}
        for name in task_names:
            if name in self.tasks:
                result[name] = self.tasks[name]
        return result


@pytest.fixture
def mock_lm_eval():
    """Fixture to mock lm-eval components."""
    with patch('EvaluationEngineV1_0.core.lm_eval_adapter.LM_EVAL_AVAILABLE', True):
        with patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager):
            with patch('EvaluationEngineV1_0.core.lm_eval_adapter.get_task_dict') as mock_get_task_dict:
                mock_get_task_dict.return_value = {
                    "test_task": MockLMEvalTask("test_task"),
                    "mock_single_turn": MockLMEvalTask("mock_single_turn"),
                    "mock_multi_turn_conversation": MockLMEvalTask("mock_multi_turn_conversation"),
                    "mock_dialogue_task": MockLMEvalTask("mock_dialogue_task"),
                    "hellaswag": MockLMEvalTask("hellaswag", "multiple_choice"),
                    "gsm8k": MockLMEvalTask("gsm8k", "generate_until")
                }
                yield


class TestLMEvalTaskInfo:
    """Test cases for LMEvalTaskInfo dataclass."""
    
    def test_task_info_creation(self):
        """Test creating LMEvalTaskInfo."""
        task_info = LMEvalTaskInfo(
            name="test_task",
            task_class=MockLMEvalTask,
            config={"output_type": "generate_until"},
            output_type="generate_until",
            is_multi_turn=False,
            metadata={"version": "1.0"}
        )
        
        assert task_info.name == "test_task"
        assert task_info.task_class == MockLMEvalTask
        assert task_info.config["output_type"] == "generate_until"
        assert task_info.output_type == "generate_until"
        assert task_info.is_multi_turn is False
        assert task_info.metadata["version"] == "1.0"


class TestLMEvalEnvironment:
    """Test cases for LMEvalEnvironment."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.task_info = LMEvalTaskInfo(
            name="test_task",
            task_class=MockLMEvalTask,
            config={"output_type": "generate_until"},
            output_type="generate_until",
            is_multi_turn=False,
            metadata={}
        )
        self.config = {"timeout": 30}
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    def test_environment_initialization(self):
        """Test environment initialization."""
        env = LMEvalEnvironment(self.task_info, self.config)
        
        assert env.task_info == self.task_info
        assert env.config == self.config
        assert env.task_instance is not None
        assert env.total_docs == 3  # MockLMEvalTask has 3 docs
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    def test_environment_reset(self):
        """Test environment reset."""
        env = LMEvalEnvironment(self.task_info, self.config)
        
        observation = env.reset()
        
        assert env.is_initialized()
        assert env.current_doc_index == 0
        assert len(env.results) == 0
        assert isinstance(observation, dict)
        assert "text" in observation
        assert observation["doc_index"] == 0
        assert observation["total_docs"] == 3
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    def test_environment_step(self):
        """Test environment step execution."""
        env = LMEvalEnvironment(self.task_info, self.config)
        env.reset()
        
        action = "Answer 0"  # Correct answer for first document
        observation, reward, done, info = env.step(action)
        
        assert reward == 1.0  # Exact match
        assert not done  # Not finished yet
        assert info["doc_index"] == 0
        assert info["total_docs"] == 3
        assert len(env.results) == 1
        assert env.current_doc_index == 1
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    def test_environment_complete_evaluation(self):
        """Test completing full evaluation."""
        env = LMEvalEnvironment(self.task_info, self.config)
        env.reset()
        
        # Process all documents
        for i in range(3):
            action = f"Answer {i}"
            observation, reward, done, info = env.step(action)
            
            if i < 2:
                assert not done
            else:
                assert done
                assert observation == "Evaluation complete"
        
        assert env.success()
        assert len(env.results) == 3
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    def test_environment_partial_credit(self):
        """Test partial credit for incorrect answers."""
        env = LMEvalEnvironment(self.task_info, self.config)
        env.reset()
        
        action = "Wrong answer"
        observation, reward, done, info = env.step(action)
        
        assert 0.0 <= reward < 1.0  # Partial credit based on similarity
        assert not env.success()  # Not successful with wrong answer
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    def test_environment_info(self):
        """Test environment info method."""
        env = LMEvalEnvironment(self.task_info, self.config)
        env.reset()
        
        info = env.info()
        
        assert info["task_name"] == "test_task"
        assert info["task_type"] == "single_turn"
        assert info["total_docs"] == 3
        assert info["current_doc_index"] == 0
        assert info["completed_docs"] == 0
        assert info["initialized"] is True
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    def test_environment_metrics(self):
        """Test environment metrics calculation."""
        env = LMEvalEnvironment(self.task_info, self.config)
        env.reset()
        
        # Process one document correctly
        env.step("Answer 0")
        
        metrics = env.get_metrics()
        
        assert metrics["progress"] == 1.0 / 3.0  # 1 out of 3 docs
        assert metrics["success_rate"] == 1.0  # 100% success so far
        assert metrics["average_reward"] == 1.0
        assert metrics["completed_docs"] == 1.0
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    def test_environment_step_without_reset(self):
        """Test stepping without reset raises error."""
        env = LMEvalEnvironment(self.task_info, self.config)
        
        with pytest.raises(TaskExecutionError, match="not initialized"):
            env.step("test action")


class TestLMEvalTaskWrapper:
    """Test cases for LMEvalTaskWrapper."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.task_info = LMEvalTaskInfo(
            name="test_task",
            task_class=MockLMEvalTask,
            config={"output_type": "generate_until"},
            output_type="generate_until",
            is_multi_turn=False,
            metadata={}
        )
        self.config = {"task_name": "test_task"}
    
    def test_task_wrapper_initialization(self):
        """Test task wrapper initialization."""
        wrapper = LMEvalTaskWrapper(self.task_info, self.config)
        
        assert wrapper.task_info == self.task_info
        assert wrapper.get_id() == "test_task"
        assert wrapper.config == self.config
    
    def test_task_wrapper_single_turn_type(self):
        """Test single-turn task type detection."""
        wrapper = LMEvalTaskWrapper(self.task_info, self.config)
        
        assert wrapper.get_task_type() == TaskType.SINGLE_TURN
    
    def test_task_wrapper_multi_turn_type(self):
        """Test multi-turn task type detection."""
        multi_turn_info = LMEvalTaskInfo(
            name="conversation_task",
            task_class=MockLMEvalTask,
            config={"output_type": "generate_until"},
            output_type="generate_until",
            is_multi_turn=True,
            metadata={}
        )
        
        wrapper = LMEvalTaskWrapper(multi_turn_info, self.config)
        
        assert wrapper.get_task_type() == TaskType.MULTI_TURN
    
    def test_task_wrapper_capabilities(self):
        """Test required capabilities."""
        wrapper = LMEvalTaskWrapper(self.task_info, self.config)
        
        capabilities = wrapper.get_required_capabilities()
        
        assert "text_generation" in capabilities
        assert "text_completion" in capabilities
    
    def test_task_wrapper_multi_turn_capabilities(self):
        """Test multi-turn task capabilities."""
        multi_turn_info = LMEvalTaskInfo(
            name="conversation_task",
            task_class=MockLMEvalTask,
            config={"output_type": "generate_until"},
            output_type="generate_until",
            is_multi_turn=True,
            metadata={}
        )
        
        wrapper = LMEvalTaskWrapper(multi_turn_info, self.config)
        capabilities = wrapper.get_required_capabilities()
        
        assert "conversation_management" in capabilities
    
    def test_task_wrapper_validate_config(self):
        """Test configuration validation."""
        wrapper = LMEvalTaskWrapper(self.task_info, self.config)
        
        assert wrapper.validate_config({"valid": "config"})
        
        with pytest.raises(ConfigurationError):
            wrapper.validate_config("not_a_dict")
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    def test_task_wrapper_create_environment(self):
        """Test environment creation."""
        wrapper = LMEvalTaskWrapper(self.task_info, self.config)
        
        env = wrapper.create_environment()
        
        assert isinstance(env, LMEvalEnvironment)
        assert env.task_info == self.task_info


class TestLMEvalAdapter:
    """Test cases for LMEvalAdapter."""
    
    def test_adapter_info(self, mock_lm_eval):
        """Test adapter information."""
        adapter = LMEvalAdapter({})
        info = adapter.get_adapter_info()
        
        assert info.name == "lm_eval_adapter"
        assert info.version == "1.0.0"
        assert TaskType.SINGLE_TURN in info.supported_task_types
        assert TaskType.MULTI_TURN in info.supported_task_types
        assert "lm-eval" in info.required_dependencies
        assert "automatic_task_detection" in info.capabilities
        assert info.metadata["modifies_lm_eval"] is False
    
    def test_adapter_initialization_success(self, mock_lm_eval):
        """Test successful adapter initialization."""
        adapter = LMEvalAdapter({})
        
        assert adapter.initialize()
        assert adapter.is_ready()
        assert adapter.get_status() == AdapterStatus.READY
    
    def test_adapter_initialization_without_lm_eval(self):
        """Test adapter initialization without lm-eval."""
        with patch('EvaluationEngineV1_0.core.lm_eval_adapter.LM_EVAL_AVAILABLE', False):
            with pytest.raises(AdapterError, match="lm-eval is not available"):
                LMEvalAdapter({})
    
    def test_adapter_load_tasks(self, mock_lm_eval):
        """Test loading tasks from lm-eval."""
        adapter = LMEvalAdapter({})
        adapter.initialize()
        
        tasks = adapter.load_tasks()
        
        assert len(tasks) == 6  # Number of mock tasks
        assert all(isinstance(task, LMEvalTaskWrapper) for task in tasks)
        
        task_names = [task.get_id() for task in tasks]
        assert "mock_single_turn" in task_names
        assert "hellaswag" in task_names
    
    def test_adapter_load_tasks_with_filter(self, mock_lm_eval):
        """Test loading tasks with filters."""
        adapter = LMEvalAdapter({})
        adapter.initialize()
        
        # Filter by pattern
        tasks = adapter.load_tasks({"pattern": "mock"})
        task_names = [task.get_id() for task in tasks]
        assert all("mock" in name for name in task_names)
        
        # Filter by task type
        tasks = adapter.load_tasks({"task_type": "multi_turn"})
        assert len(tasks) >= 2  # Should include conversation and dialogue tasks
        
        # Limit results
        tasks = adapter.load_tasks({"limit": 2})
        assert len(tasks) == 2
    
    def test_adapter_create_environment(self, mock_lm_eval):
        """Test creating environment for a task."""
        adapter = LMEvalAdapter({})
        adapter.initialize()
        
        task_config = {"task_id": "mock_single_turn"}
        env = adapter.create_environment(task_config)
        
        assert isinstance(env, LMEvalEnvironment)
        assert env.task_info.name == "mock_single_turn"
    
    def test_adapter_create_environment_invalid_task(self, mock_lm_eval):
        """Test creating environment for invalid task."""
        adapter = LMEvalAdapter({})
        adapter.initialize()
        
        task_config = {"task_id": "nonexistent_task"}
        
        with pytest.raises(AdapterError, match="not found in available tasks"):
            adapter.create_environment(task_config)
    
    def test_adapter_create_environment_missing_task_id(self, mock_lm_eval):
        """Test creating environment without task ID."""
        adapter = LMEvalAdapter({})
        adapter.initialize()
        
        task_config = {}
        
        with pytest.raises(ConfigurationError, match="task_id or task_name must be specified"):
            adapter.create_environment(task_config)
    
    def test_adapter_multi_turn_detection(self, mock_lm_eval):
        """Test multi-turn task detection."""
        adapter = LMEvalAdapter({})
        adapter.initialize()
        
        # Test detection by name
        assert adapter._detect_multi_turn("conversation_task", None) is True
        assert adapter._detect_multi_turn("dialogue_system", None) is True
        assert adapter._detect_multi_turn("multi_turn_chat", None) is True
        assert adapter._detect_multi_turn("single_qa", None) is False
        
        # Test with simple task objects
        class SimpleTask:
            def __init__(self, description):
                self.DESCRIPTION = description
        
        conversation_task = SimpleTask("This is a conversation task")
        assert adapter._detect_multi_turn("simple_task", conversation_task) is True
        
        qa_task = SimpleTask("Simple question answering")
        assert adapter._detect_multi_turn("simple_task", qa_task) is False
    
    def test_adapter_convert_results_dict_format(self, mock_lm_eval):
        """Test converting dictionary results."""
        adapter = LMEvalAdapter({})
        
        results = {
            "task_name": "test_task",
            "success": True,
            "score": 0.85,
            "execution_time": 2.5,
            "tokens_used": 100,
            "cost": 0.01
        }
        
        standardized = adapter.convert_results(results)
        
        assert standardized.task_id == "test_task"
        assert standardized.adapter_name == "lm_eval_adapter"
        assert standardized.success is True
        assert standardized.score == 0.85
        assert standardized.execution_time == 2.5
        assert standardized.tokens_used == 100
        assert standardized.cost == 0.01
        assert standardized.turns == 1
    
    def test_adapter_convert_results_lm_eval_format(self, mock_lm_eval):
        """Test converting lm-eval standard format results."""
        adapter = LMEvalAdapter({})
        
        results = {
            "results": {
                "hellaswag": {
                    "acc": 0.75,
                    "acc_norm": 0.73
                }
            },
            "config": {"model": "test"}
        }
        
        standardized = adapter.convert_results(results)
        
        assert standardized.task_id == "unknown"  # No task_name in this format
        assert standardized.score == 0.75  # First metric value
        assert standardized.success is True  # Score > 0.5
        assert standardized.metadata["lm_eval_format"] is True
    
    def test_adapter_convert_results_unsupported_format(self, mock_lm_eval):
        """Test converting unsupported result format."""
        adapter = LMEvalAdapter({})
        
        results = "unsupported string format"
        
        standardized = adapter.convert_results(results)
        
        assert standardized.task_id == "unknown"
        assert standardized.success is False
        assert standardized.score == 0.0
        assert "conversion_error" in standardized.metadata
    
    def test_adapter_not_ready_operations(self, mock_lm_eval):
        """Test operations when adapter is not ready."""
        adapter = LMEvalAdapter({})
        # Don't initialize
        
        with pytest.raises(AdapterError, match="not initialized"):
            adapter.create_environment({"task_id": "test"})
        
        with pytest.raises(AdapterError, match="not initialized"):
            adapter.load_tasks()
    
    def test_adapter_task_info_caching(self, mock_lm_eval):
        """Test task info caching."""
        adapter = LMEvalAdapter({})
        adapter.initialize()
        
        # First call should create and cache
        task_info1 = adapter._get_task_info("mock_single_turn")
        
        # Second call should return cached version
        task_info2 = adapter._get_task_info("mock_single_turn")
        
        assert task_info1 is task_info2  # Same object reference
        assert "mock_single_turn" in adapter._task_info_cache


class TestLMEvalIntegration:
    """Integration tests for lm-eval adapter."""
    
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.TaskManager', MockTaskManager)
    @patch('EvaluationEngineV1_0.core.lm_eval_adapter.get_task_dict')
    def test_end_to_end_evaluation(self, mock_get_task_dict):
        """Test end-to-end evaluation workflow."""
        # Setup mock
        mock_get_task_dict.return_value = {
            "test_task": MockLMEvalTask("test_task")
        }
        
        # Initialize adapter
        adapter = LMEvalAdapter({})
        assert adapter.initialize()
        
        # Load tasks
        tasks = adapter.load_tasks({"pattern": "test_task"})
        assert len(tasks) == 1
        
        task = tasks[0]
        assert task.get_id() == "test_task"
        
        # Create environment
        env = adapter.create_environment({"task_id": "test_task"})
        
        # Run evaluation
        observation = env.reset()
        assert env.is_initialized()
        
        results = []
        while not env.get_state().is_done:
            # Simulate correct answers
            doc_index = env.current_doc_index
            action = f"Answer {doc_index}"
            
            obs, reward, done, info = env.step(action)
            results.append((obs, reward, done, info))
            
            if done:
                break
        
        # Verify results
        assert len(results) == 3  # 3 documents in mock task
        assert env.success()
        assert all(r[1] == 1.0 for r in results)  # All correct answers
        
        # Get final metrics
        metrics = env.get_metrics()
        assert metrics["success_rate"] == 1.0
        assert metrics["completion_rate"] == 1.0
        
        # Convert to standardized result
        final_result = {
            "task_name": "test_task",
            "success": env.success(),
            "score": metrics["success_rate"],
            "execution_time": sum(r[3]["execution_time"] for r in results)
        }
        
        standardized = adapter.convert_results(final_result)
        assert standardized.success is True
        assert standardized.score == 1.0