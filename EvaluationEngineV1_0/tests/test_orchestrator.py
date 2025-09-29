"""
Unit tests for the Multi-Turn Orchestrator Engine.

This module contains comprehensive tests for the orchestrator framework,
including turn loop management, termination condition checking, state tracking,
and async execution support.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from EvaluationEngineV1_0.core.orchestrator import (
    MultiTurnOrchestrator, OrchestrationContext, OrchestrationState
)
from EvaluationEngineV1_0.core.data_models import (
    MultiTurnConfig, FeedbackConfig, SafetyConfig, TerminationReason,
    ProcessedFeedback, TurnResult
)
from EvaluationEngineV1_0.core.task_types import MultiTurnTask, TurnData
from EvaluationEngineV1_0.core.environment import MockEnvironment
from EvaluationEngineV1_0.core.policy_engine import PolicyEngine, PolicyConfig
from EvaluationEngineV1_0.core.exceptions import (
    TaskExecutionError, SafetyViolationError, ConfigurationError
)


class MockMultiTurnTask(MultiTurnTask):
    """Mock multi-turn task for testing."""
    
    def __init__(self, task_id: str = "test_task", config: dict = None):
        if config is None:
            config = {
                "max_turns": 5,
                "turn_timeout": 30,
                "max_tokens_per_turn": 1000
            }
        super().__init__(task_id, config)
        self._should_continue = True
        self._is_successful = False
    
    def execute_turn(self, turn_data: TurnData) -> TurnResult:
        """Mock turn execution."""
        from EvaluationEngineV1_0.core.data_models import TurnResult
        return TurnResult(
            turn=turn_data.turn_number,
            action=f"action_{turn_data.turn_number}",
            observation=f"observation_{turn_data.turn_number}",
            reward=0.5,
            done=turn_data.turn_number >= 3,  # Complete after 3 turns
            info={"mock": True},
            execution_time=0.1
        )
    
    def should_continue(self, turn_result: TurnResult) -> bool:
        """Mock continuation check."""
        return self._should_continue and not turn_result.done
    
    def get_initial_context(self) -> str:
        """Mock initial context."""
        return "Initial context for test task"
    
    def is_successful(self, turn_results: list) -> bool:
        """Mock success check."""
        return self._is_successful or (len(turn_results) >= 3 and turn_results[-1].done)
    
    def get_required_capabilities(self) -> list:
        """Mock required capabilities."""
        return ["python", "filesystem"]


class MockModelAdapter:
    """Mock model adapter for testing."""
    
    def __init__(self, model_id: str = "test_model"):
        self.model_id = model_id
        self.call_count = 0
    
    async def generate_action(self, turn_data: TurnData) -> str:
        """Mock action generation."""
        self.call_count += 1
        await asyncio.sleep(0.01)  # Simulate async operation
        return f"generated_action_{turn_data.turn_number}"


class MockPolicyEngine:
    """Mock policy engine for testing."""
    
    def __init__(self, should_terminate: bool = False, reason: TerminationReason = TerminationReason.SUCCESS):
        self.should_terminate_flag = should_terminate
        self.termination_reason = reason
        self.call_count = 0
    
    async def should_terminate(self, turn_results: list, environment, context=None) -> tuple:
        """Mock termination check."""
        self.call_count += 1
        return self.should_terminate_flag, self.termination_reason


class MockFeedbackProcessor:
    """Mock feedback processor for testing."""
    
    def __init__(self):
        self.call_count = 0
    
    async def process(self, observation, info, config) -> ProcessedFeedback:
        """Mock feedback processing."""
        self.call_count += 1
        return ProcessedFeedback(
            original={"observation": observation, "info": info},
            filtered={"observation": observation, "info": info},
            contextualized={"observation": observation, "info": info},
            final={"observation": observation, "info": info}
        )


class MockSafetyGuard:
    """Mock safety guard for testing."""
    
    def __init__(self, is_safe: bool = True):
        self.is_safe_flag = is_safe
        self.call_count = 0
    
    async def is_safe_to_continue(self, environment, observation) -> bool:
        """Mock safety check."""
        self.call_count += 1
        return self.is_safe_flag


class MockMetricsEngine:
    """Mock metrics engine for testing."""
    
    def __init__(self):
        self.call_count = 0
    
    async def calculate_metrics(self, turn_results: list, environment) -> dict:
        """Mock metrics calculation."""
        self.call_count += 1
        return {
            "total_turns": float(len(turn_results)),
            "success_rate": 1.0 if environment and environment.success() else 0.0,
            "average_reward": sum(tr.reward for tr in turn_results) / len(turn_results) if turn_results else 0.0
        }


@pytest.fixture
def orchestrator():
    """Create a basic orchestrator for testing."""
    return MultiTurnOrchestrator()


@pytest.fixture
def full_orchestrator():
    """Create an orchestrator with all components for testing."""
    policy_engine = MockPolicyEngine()
    feedback_processor = MockFeedbackProcessor()
    safety_guard = MockSafetyGuard()
    metrics_engine = MockMetricsEngine()
    
    return MultiTurnOrchestrator(
        policy_engine=policy_engine,
        feedback_processor=feedback_processor,
        safety_guard=safety_guard,
        metrics_engine=metrics_engine
    )


@pytest.fixture
def mock_task():
    """Create a mock multi-turn task."""
    return MockMultiTurnTask()


@pytest.fixture
def mock_model():
    """Create a mock model adapter."""
    return MockModelAdapter()


@pytest.fixture
def basic_config():
    """Create a basic multi-turn configuration."""
    return MultiTurnConfig(
        max_turns=5,
        conversation_timeout=60,
        enable_context_retention=True
    )


class TestOrchestrationContext:
    """Test the OrchestrationContext class."""
    
    def test_context_creation(self, mock_task, mock_model, basic_config):
        """Test context creation with valid parameters."""
        context = OrchestrationContext(
            evaluation_id="test_eval",
            task=mock_task,
            model_adapter=mock_model,
            config=basic_config,
            start_time=datetime.now()
        )
        
        assert context.evaluation_id == "test_eval"
        assert context.task == mock_task
        assert context.model_adapter == mock_model
        assert context.config == basic_config
        assert context.current_turn == 1
        assert context.turn_results == []
        assert context.state == OrchestrationState.IDLE
        assert isinstance(context.metadata, dict)
    
    def test_elapsed_time_property(self, mock_task, mock_model, basic_config):
        """Test elapsed time calculation."""
        start_time = datetime.now() - timedelta(seconds=5)
        context = OrchestrationContext(
            evaluation_id="test_eval",
            task=mock_task,
            model_adapter=mock_model,
            config=basic_config,
            start_time=start_time
        )
        
        elapsed = context.elapsed_time
        assert elapsed >= 5.0
        assert elapsed < 10.0  # Should be close to 5 seconds
    
    def test_is_active_property(self, mock_task, mock_model, basic_config):
        """Test is_active property for different states."""
        context = OrchestrationContext(
            evaluation_id="test_eval",
            task=mock_task,
            model_adapter=mock_model,
            config=basic_config,
            start_time=datetime.now()
        )
        
        # Test different states
        context.state = OrchestrationState.IDLE
        assert not context.is_active
        
        context.state = OrchestrationState.RUNNING
        assert context.is_active
        
        context.state = OrchestrationState.PAUSED
        assert context.is_active
        
        context.state = OrchestrationState.COMPLETED
        assert not context.is_active
    
    def test_is_terminal_property(self, mock_task, mock_model, basic_config):
        """Test is_terminal property for different states."""
        context = OrchestrationContext(
            evaluation_id="test_eval",
            task=mock_task,
            model_adapter=mock_model,
            config=basic_config,
            start_time=datetime.now()
        )
        
        # Test different states
        context.state = OrchestrationState.RUNNING
        assert not context.is_terminal
        
        context.state = OrchestrationState.COMPLETED
        assert context.is_terminal
        
        context.state = OrchestrationState.FAILED
        assert context.is_terminal


class TestMultiTurnOrchestrator:
    """Test the MultiTurnOrchestrator class."""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = MultiTurnOrchestrator()
        
        assert orchestrator.policy_engine is None
        assert orchestrator.feedback_processor is None
        assert orchestrator.safety_guard is None
        assert orchestrator.metrics_engine is None
        assert orchestrator._active_contexts == {}
        assert orchestrator._turn_callbacks == []
        assert orchestrator._completion_callbacks == []
        assert orchestrator._max_concurrent_evaluations == 10
    
    def test_orchestrator_with_components(self):
        """Test orchestrator initialization with all components."""
        policy_engine = MockPolicyEngine()
        feedback_processor = MockFeedbackProcessor()
        safety_guard = MockSafetyGuard()
        metrics_engine = MockMetricsEngine()
        
        orchestrator = MultiTurnOrchestrator(
            policy_engine=policy_engine,
            feedback_processor=feedback_processor,
            safety_guard=safety_guard,
            metrics_engine=metrics_engine
        )
        
        assert orchestrator.policy_engine == policy_engine
        assert orchestrator.feedback_processor == feedback_processor
        assert orchestrator.safety_guard == safety_guard
        assert orchestrator.metrics_engine == metrics_engine
    
    @pytest.mark.asyncio
    async def test_basic_evaluation_execution(self, orchestrator, mock_task, mock_model, basic_config):
        """Test basic evaluation execution."""
        result = await orchestrator.execute_evaluation(mock_task, mock_model, basic_config)
        
        assert result.task_id == mock_task.get_id()
        assert result.model_id == mock_model.model_id
        assert result.total_turns > 0
        assert result.termination_reason in [TerminationReason.SUCCESS, TerminationReason.MAX_TURNS]
        assert isinstance(result.final_metrics, dict)
        assert result.aggregated_metrics is not None
    
    @pytest.mark.asyncio
    async def test_evaluation_with_custom_id(self, orchestrator, mock_task, mock_model, basic_config):
        """Test evaluation with custom evaluation ID."""
        custom_id = "custom_eval_123"
        result = await orchestrator.execute_evaluation(
            mock_task, mock_model, basic_config, evaluation_id=custom_id
        )
        
        assert result.evaluation_id == custom_id
    
    @pytest.mark.asyncio
    async def test_evaluation_with_invalid_config(self, orchestrator, mock_task, mock_model):
        """Test evaluation with invalid configuration."""
        invalid_config = MultiTurnConfig(max_turns=-1)  # Invalid
        
        with pytest.raises(ValueError):
            await orchestrator.execute_evaluation(mock_task, mock_model, invalid_config)
    
    @pytest.mark.asyncio
    async def test_concurrent_evaluations(self, orchestrator, mock_task, mock_model, basic_config):
        """Test concurrent evaluation execution."""
        # Create multiple tasks
        tasks = [MockMultiTurnTask(f"task_{i}") for i in range(3)]
        models = [MockModelAdapter(f"model_{i}") for i in range(3)]
        
        # Execute concurrently
        results = await asyncio.gather(*[
            orchestrator.execute_evaluation(task, model, basic_config)
            for task, model in zip(tasks, models)
        ])
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.task_id == f"task_{i}"
            assert result.model_id == f"model_{i}"
    
    @pytest.mark.asyncio
    async def test_evaluation_with_all_components(self, full_orchestrator, mock_task, mock_model, basic_config):
        """Test evaluation with all orchestrator components."""
        result = await full_orchestrator.execute_evaluation(mock_task, mock_model, basic_config)
        
        # Verify components were called
        assert full_orchestrator.policy_engine.call_count > 0
        assert full_orchestrator.feedback_processor.call_count > 0
        assert full_orchestrator.safety_guard.call_count > 0
        assert full_orchestrator.metrics_engine.call_count > 0
        
        assert result.task_id == mock_task.get_id()
        assert result.success or result.termination_reason != TerminationReason.ERROR
    
    @pytest.mark.asyncio
    async def test_safety_violation_termination(self, mock_task, mock_model, basic_config):
        """Test evaluation termination due to safety violation."""
        # Create orchestrator with unsafe safety guard
        safety_guard = MockSafetyGuard(is_safe=False)
        orchestrator = MultiTurnOrchestrator(safety_guard=safety_guard)
        
        result = await orchestrator.execute_evaluation(mock_task, mock_model, basic_config)
        
        assert result.termination_reason == TerminationReason.SAFETY_VIOLATION
        assert not result.success
    
    @pytest.mark.asyncio
    async def test_timeout_termination(self, orchestrator, mock_task, mock_model):
        """Test evaluation termination due to timeout."""
        # Create config with very short timeout
        timeout_config = MultiTurnConfig(
            max_turns=10,
            conversation_timeout=0.1  # 0.1 seconds
        )
        
        # Mock task that takes longer than timeout
        def slow_turn(turn_data):
            time.sleep(0.2)  # Longer than timeout
            return TurnResult(
                turn=turn_data.turn_number,
                action="slow_action",
                observation="slow_observation",
                reward=0.0,
                done=False,
                info={},
                execution_time=0.2
            )
        
        mock_task.execute_turn = slow_turn
        
        result = await orchestrator.execute_evaluation(mock_task, mock_model, timeout_config)
        
        assert result.termination_reason == TerminationReason.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_max_turns_termination(self, orchestrator, mock_task, mock_model):
        """Test evaluation termination due to max turns."""
        # Create config with very few turns
        max_turns_config = MultiTurnConfig(max_turns=2)
        
        # Mock task that never completes
        mock_task._is_successful = False
        def never_done_turn(turn_data):
            return TurnResult(
                turn=turn_data.turn_number,
                action=f"action_{turn_data.turn_number}",
                observation=f"observation_{turn_data.turn_number}",
                reward=0.5,
                done=False,  # Never done
                info={},
                execution_time=0.1
            )
        
        mock_task.execute_turn = never_done_turn
        
        # Create a simple environment that doesn't interfere
        def create_simple_env():
            from EvaluationEngineV1_0.core.environment import MockEnvironment
            env = MockEnvironment({"max_steps": 10, "success_probability": 0.0})
            return env
        
        mock_task.create_environment = create_simple_env
        
        result = await orchestrator.execute_evaluation(mock_task, mock_model, max_turns_config)
        
        assert result.termination_reason == TerminationReason.MAX_TURNS
        assert result.total_turns == 2
    
    @pytest.mark.asyncio
    async def test_policy_engine_termination(self, mock_task, mock_model, basic_config):
        """Test evaluation termination by policy engine."""
        # Create policy engine with very low max turns
        policy_config = PolicyConfig(max_turns=1)
        policy_engine = PolicyEngine(policy_config)
        orchestrator = MultiTurnOrchestrator(policy_engine=policy_engine)
        
        result = await orchestrator.execute_evaluation(mock_task, mock_model, basic_config)
        
        assert result.termination_reason == TerminationReason.MAX_TURNS
        assert result.total_turns == 1
    
    def test_callback_registration(self, orchestrator):
        """Test callback registration."""
        async def turn_callback(context, turn_result):
            pass
        
        async def completion_callback(context, result):
            pass
        
        orchestrator.register_turn_callback(turn_callback)
        orchestrator.register_completion_callback(completion_callback)
        
        assert turn_callback in orchestrator._turn_callbacks
        assert completion_callback in orchestrator._completion_callbacks
    
    @pytest.mark.asyncio
    async def test_callback_execution(self, orchestrator, mock_task, mock_model, basic_config):
        """Test that callbacks are executed during evaluation."""
        turn_callback_calls = []
        completion_callback_calls = []
        
        async def turn_callback(context, turn_result):
            turn_callback_calls.append((context.evaluation_id, turn_result.turn))
        
        async def completion_callback(context, result):
            completion_callback_calls.append((context.evaluation_id, result.success))
        
        orchestrator.register_turn_callback(turn_callback)
        orchestrator.register_completion_callback(completion_callback)
        
        result = await orchestrator.execute_evaluation(mock_task, mock_model, basic_config)
        
        assert len(turn_callback_calls) == result.total_turns
        assert len(completion_callback_calls) == 1
        assert completion_callback_calls[0][0] == result.evaluation_id
    
    def test_active_evaluations_tracking(self, orchestrator):
        """Test tracking of active evaluations."""
        # Initially no active evaluations
        assert orchestrator.get_active_evaluations() == []
        
        # Test status of non-existent evaluation
        assert orchestrator.get_evaluation_status("nonexistent") is None
    
    @pytest.mark.asyncio
    async def test_evaluation_control_methods(self, orchestrator):
        """Test pause, resume, and terminate methods."""
        # Test with non-existent evaluation
        assert not await orchestrator.pause_evaluation("nonexistent")
        assert not await orchestrator.resume_evaluation("nonexistent")
        assert not await orchestrator.terminate_evaluation("nonexistent")
    
    def test_max_concurrent_evaluations_setting(self, orchestrator):
        """Test setting maximum concurrent evaluations."""
        orchestrator.set_max_concurrent_evaluations(5)
        assert orchestrator._max_concurrent_evaluations == 5
        
        with pytest.raises(ValueError):
            orchestrator.set_max_concurrent_evaluations(0)
        
        with pytest.raises(ValueError):
            orchestrator.set_max_concurrent_evaluations(-1)


class TestOrchestrationIntegration:
    """Integration tests for orchestration components."""
    
    @pytest.mark.asyncio
    async def test_full_evaluation_flow(self):
        """Test complete evaluation flow with all components."""
        # Create all components
        task = MockMultiTurnTask("integration_task")
        model = MockModelAdapter("integration_model")
        config = MultiTurnConfig(max_turns=3)
        
        policy_engine = MockPolicyEngine()
        feedback_processor = MockFeedbackProcessor()
        safety_guard = MockSafetyGuard()
        metrics_engine = MockMetricsEngine()
        
        orchestrator = MultiTurnOrchestrator(
            policy_engine=policy_engine,
            feedback_processor=feedback_processor,
            safety_guard=safety_guard,
            metrics_engine=metrics_engine
        )
        
        # Execute evaluation
        result = await orchestrator.execute_evaluation(task, model, config)
        
        # Verify result structure
        assert result.evaluation_id is not None
        assert result.task_id == "integration_task"
        assert result.model_id == "integration_model"
        assert result.start_time <= result.end_time
        assert result.total_turns > 0
        assert len(result.turn_results) == result.total_turns
        assert result.final_metrics is not None
        assert result.aggregated_metrics is not None
        assert result.termination_reason is not None
        
        # Verify turn results structure
        for i, turn_result in enumerate(result.turn_results, 1):
            assert turn_result.turn == i
            assert turn_result.action is not None
            assert turn_result.observation is not None
            assert isinstance(turn_result.reward, (int, float))
            assert isinstance(turn_result.done, bool)
            assert isinstance(turn_result.info, dict)
            assert turn_result.execution_time >= 0
        
        # Verify components were used
        assert policy_engine.call_count > 0
        assert feedback_processor.call_count > 0
        assert safety_guard.call_count > 0
        assert metrics_engine.call_count > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        task = MockMultiTurnTask("error_task")
        model = MockModelAdapter("error_model")
        config = MultiTurnConfig(max_turns=5)
        
        orchestrator = MultiTurnOrchestrator()
        
        # Mock an error in turn execution
        def error_turn(turn_data):
            raise Exception("Test error")
        
        task.execute_turn = error_turn
        
        result = await orchestrator.execute_evaluation(task, model, config)
        
        # Should handle error gracefully
        assert result.termination_reason == TerminationReason.ERROR
        assert not result.success
    
    @pytest.mark.asyncio
    async def test_metrics_calculation_accuracy(self):
        """Test accuracy of metrics calculation."""
        task = MockMultiTurnTask("metrics_task")
        model = MockModelAdapter("metrics_model")
        config = MultiTurnConfig(max_turns=4)
        
        # Mock specific turn results
        expected_rewards = [0.1, 0.3, 0.7, 0.9]
        expected_times = [0.1, 0.2, 0.15, 0.25]
        
        def mock_turn(turn_data):
            idx = turn_data.turn_number - 1
            return TurnResult(
                turn=turn_data.turn_number,
                action=f"action_{turn_data.turn_number}",
                observation=f"observation_{turn_data.turn_number}",
                reward=expected_rewards[idx],
                done=turn_data.turn_number == 4,
                info={},
                execution_time=expected_times[idx]
            )
        
        task.execute_turn = mock_turn
        
        # Create environment that doesn't interfere with timing
        def create_simple_env():
            from EvaluationEngineV1_0.core.environment import MockEnvironment
            env = MockEnvironment({"max_steps": 10, "success_probability": 0.0})
            return env
        
        task.create_environment = create_simple_env
        
        orchestrator = MultiTurnOrchestrator()
        result = await orchestrator.execute_evaluation(task, model, config)
        
        # Verify metrics
        assert result.total_turns == 4
        expected_avg_reward = sum(expected_rewards) / len(expected_rewards)
        
        # Check that the rewards match (execution time will be different due to orchestrator overhead)
        assert abs(result.final_metrics["average_reward"] - expected_avg_reward) < 0.01
        assert result.final_metrics["total_turns"] == 4.0
        
        # Verify turn results have the expected rewards
        for i, turn_result in enumerate(result.turn_results):
            assert abs(turn_result.reward - expected_rewards[i]) < 0.01


if __name__ == "__main__":
    pytest.main([__file__])