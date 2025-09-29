"""
Unit tests for the Policy Engine.

This module contains comprehensive tests for the PolicyEngine class,
including termination condition checking, custom rule support, and
policy configuration management.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from EvaluationEngineV1_0.core.policy_engine import (
    PolicyEngine, PolicyRule, PolicyConfig, PolicyType,
    create_reward_threshold_rule, create_execution_time_rule, create_token_limit_rule
)
from EvaluationEngineV1_0.core.data_models import TerminationReason, TurnResult
from EvaluationEngineV1_0.core.environment import MockEnvironment
from EvaluationEngineV1_0.core.exceptions import ConfigurationError


class TestPolicyConfig:
    """Test the PolicyConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = PolicyConfig()
        
        assert config.max_turns == 10
        assert config.conversation_timeout == 3600
        assert config.enable_success_detection is True
        assert config.enable_error_detection is True
        assert config.enable_safety_checks is True
        assert config.quality_threshold == 0.0
        assert config.stagnation_window == 3
        assert config.stagnation_threshold == 0.1
        assert config.custom_rules == []
    
    def test_config_validation_valid(self):
        """Test validation with valid configuration."""
        config = PolicyConfig(
            max_turns=5,
            conversation_timeout=1800,
            quality_threshold=0.5,
            stagnation_window=2,
            stagnation_threshold=0.05
        )
        
        assert config.validate() is True
    
    def test_config_validation_invalid_max_turns(self):
        """Test validation with invalid max_turns."""
        config = PolicyConfig(max_turns=0)
        
        with pytest.raises(ConfigurationError, match="max_turns must be positive"):
            config.validate()
    
    def test_config_validation_invalid_timeout(self):
        """Test validation with invalid timeout."""
        config = PolicyConfig(conversation_timeout=-1)
        
        with pytest.raises(ConfigurationError, match="conversation_timeout must be positive"):
            config.validate()
    
    def test_config_validation_invalid_quality_threshold(self):
        """Test validation with invalid quality threshold."""
        config = PolicyConfig(quality_threshold=1.5)
        
        with pytest.raises(ConfigurationError, match="quality_threshold must be between 0.0 and 1.0"):
            config.validate()
    
    def test_config_validation_invalid_stagnation_window(self):
        """Test validation with invalid stagnation window."""
        config = PolicyConfig(stagnation_window=0)
        
        with pytest.raises(ConfigurationError, match="stagnation_window must be positive"):
            config.validate()
    
    def test_config_validation_invalid_stagnation_threshold(self):
        """Test validation with invalid stagnation threshold."""
        config = PolicyConfig(stagnation_threshold=-0.1)
        
        with pytest.raises(ConfigurationError, match="stagnation_threshold must be between 0.0 and 1.0"):
            config.validate()


class TestPolicyRule:
    """Test the PolicyRule class."""
    
    def test_rule_creation(self):
        """Test policy rule creation."""
        def test_condition(turn_results, environment, context):
            return len(turn_results) > 5
        
        rule = PolicyRule(
            policy_type=PolicyType.CUSTOM,
            condition=test_condition,
            reason=TerminationReason.MAX_TURNS,
            priority=50,
            metadata={"description": "Test rule"}
        )
        
        assert rule.policy_type == PolicyType.CUSTOM
        assert rule.condition == test_condition
        assert rule.reason == TerminationReason.MAX_TURNS
        assert rule.priority == 50
        assert rule.enabled is True
        assert rule.metadata["description"] == "Test rule"
    
    def test_rule_evaluation_enabled(self):
        """Test rule evaluation when enabled."""
        def always_true(turn_results, environment, context):
            return True
        
        rule = PolicyRule(
            policy_type=PolicyType.CUSTOM,
            condition=always_true,
            reason=TerminationReason.SUCCESS,
            enabled=True
        )
        
        assert rule.evaluate([], None, {}) is True
    
    def test_rule_evaluation_disabled(self):
        """Test rule evaluation when disabled."""
        def always_true(turn_results, environment, context):
            return True
        
        rule = PolicyRule(
            policy_type=PolicyType.CUSTOM,
            condition=always_true,
            reason=TerminationReason.SUCCESS,
            enabled=False
        )
        
        assert rule.evaluate([], None, {}) is False
    
    def test_rule_evaluation_exception_handling(self):
        """Test rule evaluation with exception in condition."""
        def error_condition(turn_results, environment, context):
            raise Exception("Test error")
        
        rule = PolicyRule(
            policy_type=PolicyType.CUSTOM,
            condition=error_condition,
            reason=TerminationReason.ERROR
        )
        
        # Should return False and not raise exception
        assert rule.evaluate([], None, {}) is False


class TestPolicyEngine:
    """Test the PolicyEngine class."""
    
    def test_engine_initialization_default(self):
        """Test policy engine initialization with default config."""
        engine = PolicyEngine()
        
        assert engine.config.max_turns == 10
        assert len(engine._builtin_rules) > 0
        assert len(engine._custom_rules) == 0
    
    def test_engine_initialization_custom_config(self):
        """Test policy engine initialization with custom config."""
        config = PolicyConfig(
            max_turns=5,
            enable_success_detection=False,
            enable_error_detection=False
        )
        
        engine = PolicyEngine(config)
        
        assert engine.config.max_turns == 5
        # Should have fewer built-in rules due to disabled features
        success_rules = [r for r in engine._builtin_rules if r.policy_type == PolicyType.SUCCESS]
        error_rules = [r for r in engine._builtin_rules if r.policy_type == PolicyType.ERROR]
        assert len(success_rules) == 0
        assert len(error_rules) == 0
    
    @pytest.mark.asyncio
    async def test_should_terminate_no_conditions(self):
        """Test should_terminate with no termination conditions met."""
        engine = PolicyEngine()
        
        # Create turn results that don't meet any termination conditions
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.5,
                done=False,
                info={},
                execution_time=0.1
            )
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        assert should_terminate is False
        assert reason == TerminationReason.SUCCESS
    
    @pytest.mark.asyncio
    async def test_should_terminate_max_turns(self):
        """Test should_terminate with max turns condition."""
        config = PolicyConfig(max_turns=2)
        engine = PolicyEngine(config)
        
        # Create turn results that exceed max turns
        turn_results = [
            TurnResult(
                turn=i,
                action=f"action{i}",
                observation=f"obs{i}",
                reward=0.5,
                done=False,
                info={},
                execution_time=0.1
            )
            for i in range(1, 3)  # 2 turns
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        assert should_terminate is True
        assert reason == TerminationReason.MAX_TURNS
    
    @pytest.mark.asyncio
    async def test_should_terminate_success(self):
        """Test should_terminate with success condition."""
        engine = PolicyEngine()
        
        # Create successful environment
        env = MockEnvironment({"max_steps": 10, "success_probability": 1.0})
        env.reset()
        env.step("test_action")  # This should make it successful
        
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.8,
                done=True,
                info={},
                execution_time=0.1
            )
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, env)
        
        assert should_terminate is True
        assert reason == TerminationReason.SUCCESS
    
    @pytest.mark.asyncio
    async def test_should_terminate_error(self):
        """Test should_terminate with error condition."""
        engine = PolicyEngine()
        
        turn_results = [
            TurnResult(
                turn=1,
                action="ERROR",
                observation="Error occurred",
                reward=0.0,
                done=True,
                info={"error_occurred": True},
                execution_time=0.1
            )
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        assert should_terminate is True
        assert reason == TerminationReason.ERROR
    
    @pytest.mark.asyncio
    async def test_should_terminate_safety_violation(self):
        """Test should_terminate with safety violation condition."""
        engine = PolicyEngine()
        
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.5,
                done=False,
                info={},
                execution_time=0.1,
                safety_violations=["dangerous_command"]
            )
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        assert should_terminate is True
        assert reason == TerminationReason.SAFETY_VIOLATION
    
    @pytest.mark.asyncio
    async def test_should_terminate_timeout(self):
        """Test should_terminate with timeout condition."""
        config = PolicyConfig(conversation_timeout=1)  # 1 second timeout
        engine = PolicyEngine(config)
        
        # Set start time to simulate timeout
        engine._start_time = datetime.now() - timedelta(seconds=2)
        
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.5,
                done=False,
                info={},
                execution_time=0.1,
                timestamp=engine._start_time
            )
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        assert should_terminate is True
        assert reason == TerminationReason.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_should_terminate_quality_threshold(self):
        """Test should_terminate with quality threshold condition."""
        config = PolicyConfig(quality_threshold=0.7)
        engine = PolicyEngine(config)
        
        # Create turn results with low quality (low rewards)
        turn_results = [
            TurnResult(
                turn=i,
                action=f"action{i}",
                observation=f"obs{i}",
                reward=0.2,  # Below threshold
                done=False,
                info={},
                execution_time=0.1
            )
            for i in range(1, 4)  # 3 turns with low rewards
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        assert should_terminate is True
        assert reason == TerminationReason.ERROR
    
    @pytest.mark.asyncio
    async def test_should_terminate_stagnation(self):
        """Test should_terminate with stagnation condition."""
        config = PolicyConfig(stagnation_window=3, stagnation_threshold=0.01)
        engine = PolicyEngine(config)
        
        # Create turn results with very similar rewards (stagnation)
        turn_results = [
            TurnResult(
                turn=i,
                action=f"action{i}",
                observation=f"obs{i}",
                reward=0.5,  # Same reward for all turns
                done=False,
                info={},
                execution_time=0.1
            )
            for i in range(1, 4)  # 3 turns with identical rewards
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        assert should_terminate is True
        assert reason == TerminationReason.ERROR
    
    @pytest.mark.asyncio
    async def test_should_terminate_custom_rule(self):
        """Test should_terminate with custom rule."""
        def custom_condition(turn_results, environment, context):
            return len(turn_results) >= 2 and turn_results[-1].reward < 0.3
        
        custom_rule = PolicyRule(
            policy_type=PolicyType.CUSTOM,
            condition=custom_condition,
            reason=TerminationReason.ERROR,
            priority=100  # High priority
        )
        
        config = PolicyConfig(custom_rules=[custom_rule])
        engine = PolicyEngine(config)
        
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.5,
                done=False,
                info={},
                execution_time=0.1
            ),
            TurnResult(
                turn=2,
                action="action2",
                observation="obs2",
                reward=0.2,  # Low reward triggers custom rule
                done=False,
                info={},
                execution_time=0.1
            )
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        assert should_terminate is True
        assert reason == TerminationReason.ERROR
    
    @pytest.mark.asyncio
    async def test_rule_priority_ordering(self):
        """Test that rules are evaluated in priority order."""
        # Create two custom rules with different priorities
        def low_priority_condition(turn_results, environment, context):
            return True  # Always triggers
        
        def high_priority_condition(turn_results, environment, context):
            return True  # Always triggers
        
        low_priority_rule = PolicyRule(
            policy_type=PolicyType.CUSTOM,
            condition=low_priority_condition,
            reason=TerminationReason.ERROR,
            priority=10
        )
        
        high_priority_rule = PolicyRule(
            policy_type=PolicyType.CUSTOM,
            condition=high_priority_condition,
            reason=TerminationReason.TIMEOUT,
            priority=90
        )
        
        config = PolicyConfig(
            custom_rules=[low_priority_rule, high_priority_rule],
            enable_success_detection=False,
            enable_error_detection=False,
            enable_safety_checks=False
        )
        engine = PolicyEngine(config)
        
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.5,
                done=False,
                info={},
                execution_time=0.1
            )
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        # Should return the high priority rule's reason
        assert should_terminate is True
        assert reason == TerminationReason.TIMEOUT
    
    def test_add_custom_rule(self):
        """Test adding custom rules."""
        engine = PolicyEngine()
        initial_count = len(engine._custom_rules)
        
        def test_condition(turn_results, environment, context):
            return False
        
        rule = PolicyRule(
            policy_type=PolicyType.CUSTOM,
            condition=test_condition,
            reason=TerminationReason.ERROR
        )
        
        engine.add_custom_rule(rule)
        
        assert len(engine._custom_rules) == initial_count + 1
        assert rule in engine._custom_rules
    
    def test_remove_custom_rule(self):
        """Test removing custom rules."""
        def test_condition(turn_results, environment, context):
            return False
        
        rule = PolicyRule(
            policy_type=PolicyType.CUSTOM,
            condition=test_condition,
            reason=TerminationReason.ERROR
        )
        
        config = PolicyConfig(custom_rules=[rule])
        engine = PolicyEngine(config)
        
        assert len(engine._custom_rules) == 1
        
        removed = engine.remove_custom_rule(PolicyType.CUSTOM)
        assert removed is True
        assert len(engine._custom_rules) == 0
        
        # Try to remove non-existent rule
        removed = engine.remove_custom_rule(PolicyType.CUSTOM)
        assert removed is False
    
    def test_enable_disable_rules(self):
        """Test enabling and disabling rules."""
        engine = PolicyEngine()
        
        # Disable max turns rule
        disabled = engine.disable_rule(PolicyType.MAX_TURNS)
        assert disabled is True
        
        # Check that rule is disabled
        max_turns_rules = [r for r in engine._builtin_rules if r.policy_type == PolicyType.MAX_TURNS]
        assert len(max_turns_rules) == 1
        assert max_turns_rules[0].enabled is False
        
        # Re-enable the rule
        enabled = engine.enable_rule(PolicyType.MAX_TURNS)
        assert enabled is True
        assert max_turns_rules[0].enabled is True
        
        # Try to disable non-existent rule
        disabled = engine.disable_rule(PolicyType.CUSTOM)
        assert disabled is False
    
    def test_get_active_rules(self):
        """Test getting active rules."""
        engine = PolicyEngine()
        
        # All rules should be active initially
        active_rules = engine.get_active_rules()
        assert len(active_rules) > 0
        assert all(rule.enabled for rule in active_rules)
        
        # Disable a rule
        engine.disable_rule(PolicyType.MAX_TURNS)
        
        # Should have one fewer active rule
        new_active_rules = engine.get_active_rules()
        assert len(new_active_rules) == len(active_rules) - 1
        
        # Check that rules are sorted by priority
        priorities = [rule.priority for rule in new_active_rules]
        assert priorities == sorted(priorities, reverse=True)
    
    def test_get_rule_status(self):
        """Test getting rule status."""
        engine = PolicyEngine()
        
        status = engine.get_rule_status()
        assert isinstance(status, dict)
        assert len(status) > 0
        
        # All built-in rules should be enabled initially
        for rule_type, enabled in status.items():
            if rule_type != PolicyType.CUSTOM.value:  # Custom rules might not exist
                assert enabled is True
        
        # Disable a rule and check status
        engine.disable_rule(PolicyType.MAX_TURNS)
        new_status = engine.get_rule_status()
        assert new_status[PolicyType.MAX_TURNS.value] is False
    
    def test_reset(self):
        """Test resetting engine state."""
        engine = PolicyEngine()
        
        # Set some state
        engine._start_time = datetime.now()
        engine._evaluation_context = {"test": "value"}
        
        # Reset
        engine.reset()
        
        assert engine._start_time is None
        assert engine._evaluation_context == {}
    
    def test_update_config(self):
        """Test updating configuration."""
        engine = PolicyEngine()
        original_max_turns = engine.config.max_turns
        
        new_config = PolicyConfig(max_turns=original_max_turns + 5)
        engine.update_config(new_config)
        
        assert engine.config.max_turns == original_max_turns + 5
        
        # Built-in rules should be reinitialized
        assert len(engine._builtin_rules) > 0


class TestUtilityFunctions:
    """Test utility functions for creating custom rules."""
    
    def test_create_reward_threshold_rule(self):
        """Test creating reward threshold rule."""
        rule = create_reward_threshold_rule(threshold=0.5, window_size=2, priority=60)
        
        assert rule.policy_type == PolicyType.CUSTOM
        assert rule.reason == TerminationReason.ERROR
        assert rule.priority == 60
        assert rule.metadata["threshold"] == 0.5
        assert rule.metadata["window_size"] == 2
        
        # Test condition with rewards below threshold
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.3,  # Below threshold
                done=False,
                info={},
                execution_time=0.1
            ),
            TurnResult(
                turn=2,
                action="action2",
                observation="obs2",
                reward=0.4,  # Below threshold
                done=False,
                info={},
                execution_time=0.1
            )
        ]
        
        assert rule.evaluate(turn_results, None, {}) is True
        
        # Test condition with rewards above threshold
        turn_results[0].reward = 0.6
        turn_results[1].reward = 0.7
        
        assert rule.evaluate(turn_results, None, {}) is False
    
    def test_create_execution_time_rule(self):
        """Test creating execution time rule."""
        rule = create_execution_time_rule(max_time_per_turn=1.0, priority=80)
        
        assert rule.policy_type == PolicyType.CUSTOM
        assert rule.reason == TerminationReason.TIMEOUT
        assert rule.priority == 80
        assert rule.metadata["max_time_per_turn"] == 1.0
        
        # Test condition with turn exceeding time limit
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.5,
                done=False,
                info={},
                execution_time=1.5  # Exceeds limit
            )
        ]
        
        assert rule.evaluate(turn_results, None, {}) is True
        
        # Test condition with turn within time limit
        turn_results[0].execution_time = 0.5
        
        assert rule.evaluate(turn_results, None, {}) is False
    
    def test_create_token_limit_rule(self):
        """Test creating token limit rule."""
        rule = create_token_limit_rule(max_tokens=1000, priority=75)
        
        assert rule.policy_type == PolicyType.CUSTOM
        assert rule.reason == TerminationReason.RESOURCE_EXHAUSTION
        assert rule.priority == 75
        assert rule.metadata["max_tokens"] == 1000
        
        # Test condition with tokens exceeding limit
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.5,
                done=False,
                info={},
                execution_time=0.1,
                tokens_used=600
            ),
            TurnResult(
                turn=2,
                action="action2",
                observation="obs2",
                reward=0.5,
                done=False,
                info={},
                execution_time=0.1,
                tokens_used=500  # Total: 1100, exceeds limit
            )
        ]
        
        assert rule.evaluate(turn_results, None, {}) is True
        
        # Test condition with tokens within limit
        turn_results[1].tokens_used = 300  # Total: 900, within limit
        
        assert rule.evaluate(turn_results, None, {}) is False


class TestPolicyEngineIntegration:
    """Integration tests for policy engine."""
    
    @pytest.mark.asyncio
    async def test_complex_evaluation_scenario(self):
        """Test complex evaluation scenario with multiple conditions."""
        # Create config with multiple features enabled
        config = PolicyConfig(
            max_turns=5,
            conversation_timeout=10,
            quality_threshold=0.3,
            stagnation_window=2,
            stagnation_threshold=0.05
        )
        
        # Add custom rule
        custom_rule = create_reward_threshold_rule(threshold=0.2, window_size=2)
        config.custom_rules.append(custom_rule)
        
        engine = PolicyEngine(config)
        
        # Create turn results that should trigger quality threshold
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.1,  # Below quality threshold
                done=False,
                info={},
                execution_time=0.1
            ),
            TurnResult(
                turn=2,
                action="action2",
                observation="obs2",
                reward=0.15,  # Below quality threshold
                done=False,
                info={},
                execution_time=0.1
            ),
            TurnResult(
                turn=3,
                action="action3",
                observation="obs3",
                reward=0.1,  # Below quality threshold
                done=False,
                info={},
                execution_time=0.1
            )
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        # Should terminate due to quality threshold (or custom rule)
        assert should_terminate is True
        assert reason == TerminationReason.ERROR
    
    @pytest.mark.asyncio
    async def test_rule_interaction_and_precedence(self):
        """Test interaction between different rules and their precedence."""
        # Create config that could trigger multiple conditions
        config = PolicyConfig(
            max_turns=2,  # Low max turns
            quality_threshold=0.8  # High quality threshold
        )
        
        engine = PolicyEngine(config)
        
        # Create turn results that meet max turns but have good quality
        turn_results = [
            TurnResult(
                turn=1,
                action="action1",
                observation="obs1",
                reward=0.9,  # High reward
                done=False,
                info={},
                execution_time=0.1
            ),
            TurnResult(
                turn=2,
                action="action2",
                observation="obs2",
                reward=0.9,  # High reward
                done=False,
                info={},
                execution_time=0.1
            )
        ]
        
        should_terminate, reason = await engine.should_terminate(turn_results, None)
        
        # Should terminate due to max turns (higher priority than quality)
        assert should_terminate is True
        assert reason == TerminationReason.MAX_TURNS


if __name__ == "__main__":
    pytest.main([__file__])