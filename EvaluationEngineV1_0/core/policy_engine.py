"""
Policy Engine for Multi-Turn Evaluation Termination Logic.

This module implements the PolicyEngine class that handles termination decision
making for multi-turn evaluations, including configurable termination policies
and custom rule support.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable, Union

from .data_models import TerminationReason, MultiTurnConfig
from .task_types import TurnResult
from .environment import UnifiedEnv
from .exceptions import ConfigurationError, SafetyViolationError


class PolicyType(Enum):
    """Types of termination policies."""
    SUCCESS = "success"
    MAX_TURNS = "max_turns"
    TIMEOUT = "timeout"
    SAFETY_VIOLATION = "safety_violation"
    ERROR = "error"
    CUSTOM = "custom"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    QUALITY_THRESHOLD = "quality_threshold"
    STAGNATION = "stagnation"


@dataclass
class PolicyRule:
    """A single policy rule for termination decisions.
    
    Attributes:
        policy_type: Type of policy this rule implements
        condition: Function that evaluates the termination condition
        reason: Termination reason to return if condition is met
        priority: Priority of this rule (higher = evaluated first)
        enabled: Whether this rule is currently enabled
        metadata: Additional metadata for the rule
    """
    policy_type: PolicyType
    condition: Callable[[List[TurnResult], Optional[UnifiedEnv], Dict[str, Any]], bool]
    reason: TerminationReason
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def evaluate(self, 
                turn_results: List[TurnResult], 
                environment: Optional[UnifiedEnv],
                context: Dict[str, Any]) -> bool:
        """Evaluate this policy rule.
        
        Args:
            turn_results: List of turn results
            environment: Current environment (if available)
            context: Additional context for evaluation
            
        Returns:
            True if termination condition is met
        """
        if not self.enabled:
            return False
        
        try:
            return self.condition(turn_results, environment, context)
        except Exception as e:
            # Log error but don't fail the evaluation
            logging.getLogger(__name__).error(f"Policy rule evaluation failed: {str(e)}")
            return False


@dataclass
class PolicyConfig:
    """Configuration for policy engine behavior.
    
    Attributes:
        max_turns: Maximum number of turns allowed
        conversation_timeout: Maximum conversation time in seconds
        enable_success_detection: Whether to check for task success
        enable_error_detection: Whether to check for errors
        enable_safety_checks: Whether to perform safety checks
        quality_threshold: Minimum quality threshold for continuation
        stagnation_window: Number of turns to check for stagnation
        stagnation_threshold: Threshold for detecting stagnation
        custom_rules: List of custom policy rules
    """
    max_turns: int = 10
    conversation_timeout: int = 3600
    enable_success_detection: bool = True
    enable_error_detection: bool = True
    enable_safety_checks: bool = True
    quality_threshold: float = 0.0
    stagnation_window: int = 3
    stagnation_threshold: float = 0.1
    custom_rules: List[PolicyRule] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate configuration values."""
        if self.max_turns <= 0:
            raise ConfigurationError("max_turns must be positive")
        if self.conversation_timeout <= 0:
            raise ConfigurationError("conversation_timeout must be positive")
        if not 0.0 <= self.quality_threshold <= 1.0:
            raise ConfigurationError("quality_threshold must be between 0.0 and 1.0")
        if self.stagnation_window <= 0:
            raise ConfigurationError("stagnation_window must be positive")
        if not 0.0 <= self.stagnation_threshold <= 1.0:
            raise ConfigurationError("stagnation_threshold must be between 0.0 and 1.0")
        return True


class PolicyEngine:
    """Engine for termination decision making in multi-turn evaluations.
    
    This class implements configurable termination policies and custom rule
    support for determining when multi-turn evaluations should terminate.
    
    Requirements addressed:
    - 7.3: Termination policies and safety guards
    - 7.4: Policy-based termination conditions
    """
    
    def __init__(self, 
                 config: Optional[PolicyConfig] = None,
                 logger: Optional[logging.Logger] = None):
        """Initialize the policy engine.
        
        Args:
            config: Policy configuration
            logger: Logger for policy events
        """
        self.config = config or PolicyConfig()
        self.config.validate()
        self.logger = logger or logging.getLogger(__name__)
        
        # Built-in policy rules
        self._builtin_rules: List[PolicyRule] = []
        self._initialize_builtin_rules()
        
        # Custom policy rules
        self._custom_rules: List[PolicyRule] = self.config.custom_rules.copy()
        
        # Evaluation context
        self._start_time: Optional[datetime] = None
        self._evaluation_context: Dict[str, Any] = {}
    
    def _initialize_builtin_rules(self) -> None:
        """Initialize built-in policy rules."""
        # Success detection rule
        if self.config.enable_success_detection:
            self._builtin_rules.append(PolicyRule(
                policy_type=PolicyType.SUCCESS,
                condition=self._check_success_condition,
                reason=TerminationReason.SUCCESS,
                priority=100,
                metadata={"description": "Task completed successfully"}
            ))
        
        # Max turns rule
        self._builtin_rules.append(PolicyRule(
            policy_type=PolicyType.MAX_TURNS,
            condition=self._check_max_turns_condition,
            reason=TerminationReason.MAX_TURNS,
            priority=90,
            metadata={"description": "Maximum turns reached"}
        ))
        
        # Timeout rule
        self._builtin_rules.append(PolicyRule(
            policy_type=PolicyType.TIMEOUT,
            condition=self._check_timeout_condition,
            reason=TerminationReason.TIMEOUT,
            priority=95,
            metadata={"description": "Conversation timeout exceeded"}
        ))
        
        # Error detection rule
        if self.config.enable_error_detection:
            self._builtin_rules.append(PolicyRule(
                policy_type=PolicyType.ERROR,
                condition=self._check_error_condition,
                reason=TerminationReason.ERROR,
                priority=85,
                metadata={"description": "Error detected in turn execution"}
            ))
        
        # Safety violation rule
        if self.config.enable_safety_checks:
            self._builtin_rules.append(PolicyRule(
                policy_type=PolicyType.SAFETY_VIOLATION,
                condition=self._check_safety_condition,
                reason=TerminationReason.SAFETY_VIOLATION,
                priority=99,
                metadata={"description": "Safety violation detected"}
            ))
        
        # Quality threshold rule
        if self.config.quality_threshold > 0.0:
            self._builtin_rules.append(PolicyRule(
                policy_type=PolicyType.QUALITY_THRESHOLD,
                condition=self._check_quality_threshold_condition,
                reason=TerminationReason.ERROR,
                priority=70,
                metadata={"description": "Quality below threshold"}
            ))
        
        # Stagnation detection rule
        if self.config.stagnation_window > 0:
            self._builtin_rules.append(PolicyRule(
                policy_type=PolicyType.STAGNATION,
                condition=self._check_stagnation_condition,
                reason=TerminationReason.ERROR,
                priority=60,
                metadata={"description": "Progress stagnation detected"}
            ))
    
    async def should_terminate(self, 
                              turn_results: List[TurnResult], 
                              environment: Optional[UnifiedEnv],
                              context: Optional[Dict[str, Any]] = None) -> Tuple[bool, TerminationReason]:
        """Determine if evaluation should terminate.
        
        Args:
            turn_results: List of turn results from the evaluation
            environment: Current evaluation environment
            context: Additional context for decision making
            
        Returns:
            Tuple of (should_terminate, termination_reason)
        """
        if context is None:
            context = {}
        
        # Update evaluation context
        self._evaluation_context.update(context)
        
        # Set start time if not already set
        if self._start_time is None and turn_results:
            self._start_time = turn_results[0].timestamp
        
        # Get all rules sorted by priority (highest first)
        all_rules = sorted(
            self._builtin_rules + self._custom_rules,
            key=lambda r: r.priority,
            reverse=True
        )
        
        # Evaluate rules in priority order
        for rule in all_rules:
            if not rule.enabled:
                continue
            
            try:
                if rule.evaluate(turn_results, environment, self._evaluation_context):
                    self.logger.info(
                        f"Termination triggered by {rule.policy_type.value} policy: "
                        f"{rule.metadata.get('description', 'No description')}"
                    )
                    return True, rule.reason
            except Exception as e:
                self.logger.error(f"Error evaluating policy rule {rule.policy_type.value}: {str(e)}")
                continue
        
        # No termination condition met
        return False, TerminationReason.SUCCESS
    
    def _check_success_condition(self, 
                                turn_results: List[TurnResult], 
                                environment: Optional[UnifiedEnv],
                                context: Dict[str, Any]) -> bool:
        """Check if task has been completed successfully."""
        if not turn_results:
            return False
        
        # Check if environment reports success
        if environment and environment.success():
            return True
        
        # Check if last turn is marked as done with positive reward
        last_turn = turn_results[-1]
        if last_turn.done and last_turn.reward > 0:
            return True
        
        return False
    
    def _check_max_turns_condition(self, 
                                  turn_results: List[TurnResult], 
                                  environment: Optional[UnifiedEnv],
                                  context: Dict[str, Any]) -> bool:
        """Check if maximum turns have been reached."""
        return len(turn_results) >= self.config.max_turns
    
    def _check_timeout_condition(self, 
                                turn_results: List[TurnResult], 
                                environment: Optional[UnifiedEnv],
                                context: Dict[str, Any]) -> bool:
        """Check if conversation timeout has been exceeded."""
        if not self._start_time or not turn_results:
            return False
        
        elapsed_time = (datetime.now() - self._start_time).total_seconds()
        return elapsed_time > self.config.conversation_timeout
    
    def _check_error_condition(self, 
                              turn_results: List[TurnResult], 
                              environment: Optional[UnifiedEnv],
                              context: Dict[str, Any]) -> bool:
        """Check if an error has occurred."""
        if not turn_results:
            return False
        
        # Check if any turn has error information
        for turn_result in turn_results:
            if turn_result.info.get("error_occurred", False):
                return True
            if "error" in turn_result.info:
                return True
            if turn_result.action == "ERROR":
                return True
        
        return False
    
    def _check_safety_condition(self, 
                               turn_results: List[TurnResult], 
                               environment: Optional[UnifiedEnv],
                               context: Dict[str, Any]) -> bool:
        """Check if a safety violation has occurred."""
        if not turn_results:
            return False
        
        # Check for safety violations in turn results
        for turn_result in turn_results:
            if turn_result.safety_violations:
                return True
            if turn_result.info.get("safety_violation", False):
                return True
        
        return False
    
    def _check_quality_threshold_condition(self, 
                                          turn_results: List[TurnResult], 
                                          environment: Optional[UnifiedEnv],
                                          context: Dict[str, Any]) -> bool:
        """Check if quality has fallen below threshold."""
        if not turn_results or self.config.quality_threshold <= 0.0:
            return False
        
        # Calculate average reward over recent turns
        recent_turns = turn_results[-min(3, len(turn_results)):]
        avg_reward = sum(tr.reward for tr in recent_turns) / len(recent_turns)
        
        return avg_reward < self.config.quality_threshold
    
    def _check_stagnation_condition(self, 
                                   turn_results: List[TurnResult], 
                                   environment: Optional[UnifiedEnv],
                                   context: Dict[str, Any]) -> bool:
        """Check if progress has stagnated."""
        if len(turn_results) < self.config.stagnation_window:
            return False
        
        # Check reward variance in recent window
        recent_turns = turn_results[-self.config.stagnation_window:]
        rewards = [tr.reward for tr in recent_turns]
        
        if not rewards:
            return False
        
        # Calculate variance
        mean_reward = sum(rewards) / len(rewards)
        variance = sum((r - mean_reward) ** 2 for r in rewards) / len(rewards)
        
        # Consider stagnant if variance is very low
        return variance < self.config.stagnation_threshold
    
    # Public API methods
    
    def add_custom_rule(self, rule: PolicyRule) -> None:
        """Add a custom policy rule.
        
        Args:
            rule: Custom policy rule to add
        """
        self._custom_rules.append(rule)
        self.logger.info(f"Added custom policy rule: {rule.policy_type.value}")
    
    def remove_custom_rule(self, policy_type: PolicyType) -> bool:
        """Remove a custom policy rule by type.
        
        Args:
            policy_type: Type of policy rule to remove
            
        Returns:
            True if rule was removed, False if not found
        """
        for i, rule in enumerate(self._custom_rules):
            if rule.policy_type == policy_type:
                del self._custom_rules[i]
                self.logger.info(f"Removed custom policy rule: {policy_type.value}")
                return True
        return False
    
    def enable_rule(self, policy_type: PolicyType) -> bool:
        """Enable a policy rule by type.
        
        Args:
            policy_type: Type of policy rule to enable
            
        Returns:
            True if rule was found and enabled
        """
        for rule in self._builtin_rules + self._custom_rules:
            if rule.policy_type == policy_type:
                rule.enabled = True
                self.logger.info(f"Enabled policy rule: {policy_type.value}")
                return True
        return False
    
    def disable_rule(self, policy_type: PolicyType) -> bool:
        """Disable a policy rule by type.
        
        Args:
            policy_type: Type of policy rule to disable
            
        Returns:
            True if rule was found and disabled
        """
        for rule in self._builtin_rules + self._custom_rules:
            if rule.policy_type == policy_type:
                rule.enabled = False
                self.logger.info(f"Disabled policy rule: {policy_type.value}")
                return True
        return False
    
    def get_active_rules(self) -> List[PolicyRule]:
        """Get list of currently active (enabled) rules.
        
        Returns:
            List of enabled policy rules sorted by priority
        """
        active_rules = [rule for rule in self._builtin_rules + self._custom_rules if rule.enabled]
        return sorted(active_rules, key=lambda r: r.priority, reverse=True)
    
    def get_rule_status(self) -> Dict[str, bool]:
        """Get status of all policy rules.
        
        Returns:
            Dictionary mapping policy type names to enabled status
        """
        status = {}
        for rule in self._builtin_rules + self._custom_rules:
            status[rule.policy_type.value] = rule.enabled
        return status
    
    def reset(self) -> None:
        """Reset the policy engine state."""
        self._start_time = None
        self._evaluation_context.clear()
        self.logger.debug("Policy engine state reset")
    
    def update_config(self, config: PolicyConfig) -> None:
        """Update the policy configuration.
        
        Args:
            config: New policy configuration
        """
        config.validate()
        self.config = config
        
        # Reinitialize built-in rules with new config
        self._builtin_rules.clear()
        self._initialize_builtin_rules()
        
        self.logger.info("Policy engine configuration updated")


# Utility functions for creating common custom rules

def create_reward_threshold_rule(threshold: float, 
                                window_size: int = 3,
                                priority: int = 50) -> PolicyRule:
    """Create a custom rule that terminates if average reward falls below threshold.
    
    Args:
        threshold: Minimum average reward threshold
        window_size: Number of recent turns to consider
        priority: Rule priority
        
    Returns:
        PolicyRule for reward threshold checking
    """
    def condition(turn_results: List[TurnResult], 
                 environment: Optional[UnifiedEnv],
                 context: Dict[str, Any]) -> bool:
        if len(turn_results) < window_size:
            return False
        
        recent_turns = turn_results[-window_size:]
        avg_reward = sum(tr.reward for tr in recent_turns) / len(recent_turns)
        return avg_reward < threshold
    
    return PolicyRule(
        policy_type=PolicyType.CUSTOM,
        condition=condition,
        reason=TerminationReason.ERROR,
        priority=priority,
        metadata={
            "description": f"Average reward below {threshold} over {window_size} turns",
            "threshold": threshold,
            "window_size": window_size
        }
    )


def create_execution_time_rule(max_time_per_turn: float,
                              priority: int = 80) -> PolicyRule:
    """Create a custom rule that terminates if any turn takes too long.
    
    Args:
        max_time_per_turn: Maximum execution time per turn in seconds
        priority: Rule priority
        
    Returns:
        PolicyRule for execution time checking
    """
    def condition(turn_results: List[TurnResult], 
                 environment: Optional[UnifiedEnv],
                 context: Dict[str, Any]) -> bool:
        if not turn_results:
            return False
        
        # Check if any turn exceeded the time limit
        for turn_result in turn_results:
            if turn_result.execution_time > max_time_per_turn:
                return True
        
        return False
    
    return PolicyRule(
        policy_type=PolicyType.CUSTOM,
        condition=condition,
        reason=TerminationReason.TIMEOUT,
        priority=priority,
        metadata={
            "description": f"Turn execution time exceeded {max_time_per_turn}s",
            "max_time_per_turn": max_time_per_turn
        }
    )


def create_token_limit_rule(max_tokens: int,
                           priority: int = 75) -> PolicyRule:
    """Create a custom rule that terminates if token usage exceeds limit.
    
    Args:
        max_tokens: Maximum total tokens allowed
        priority: Rule priority
        
    Returns:
        PolicyRule for token limit checking
    """
    def condition(turn_results: List[TurnResult], 
                 environment: Optional[UnifiedEnv],
                 context: Dict[str, Any]) -> bool:
        if not turn_results:
            return False
        
        total_tokens = sum(tr.tokens_used for tr in turn_results)
        return total_tokens > max_tokens
    
    return PolicyRule(
        policy_type=PolicyType.CUSTOM,
        condition=condition,
        reason=TerminationReason.RESOURCE_EXHAUSTION,
        priority=priority,
        metadata={
            "description": f"Token usage exceeded {max_tokens}",
            "max_tokens": max_tokens
        }
    )