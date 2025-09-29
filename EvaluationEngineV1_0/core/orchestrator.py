"""
Multi-Turn Orchestrator Engine for the Multi-Turn Evaluation Engine.

This module implements the core orchestration framework that manages multi-turn
evaluation execution, including turn loop management, termination condition
checking, state tracking, and async execution support.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from .data_models import (
    EvaluationResult, TurnResult, AggregatedMetrics, MultiTurnConfig,
    TerminationReason, ProcessedFeedback
)
from .task_types import MultiTurnTask, TurnData
from .environment import UnifiedEnv, StepResult
from .policy_engine import PolicyEngine
from .performance_optimizer import performance_optimizer
from .exceptions import (
    TaskExecutionError, SafetyViolationError, ConfigurationError,
    ResourceExhaustionError
)


# Type aliases for clarity
ModelAdapter = Any  # Will be defined in future tasks
FeedbackProcessor = Any  # Will be defined in future tasks
SafetyGuard = Any  # Will be defined in future tasks
MetricsEngine = Any  # Will be defined in future tasks


class OrchestrationState(Enum):
    """States of the orchestration process."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATING = "terminating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OrchestrationContext:
    """Context information for orchestration execution.
    
    Attributes:
        evaluation_id: Unique identifier for this evaluation
        task: The multi-turn task being executed
        model_adapter: Adapter for the model being evaluated
        config: Configuration for the evaluation
        start_time: When the evaluation started
        current_turn: Current turn number (1-based)
        turn_results: Results from completed turns
        environment: The task environment
        state: Current orchestration state
        metadata: Additional context information
    """
    evaluation_id: str
    task: MultiTurnTask
    model_adapter: ModelAdapter
    config: MultiTurnConfig
    start_time: datetime
    current_turn: int = 1
    turn_results: List[TurnResult] = field(default_factory=list)
    environment: Optional[UnifiedEnv] = None
    state: OrchestrationState = OrchestrationState.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def is_active(self) -> bool:
        """Check if orchestration is actively running."""
        return self.state in [OrchestrationState.RUNNING, OrchestrationState.PAUSED]
    
    @property
    def is_terminal(self) -> bool:
        """Check if orchestration is in a terminal state."""
        return self.state in [
            OrchestrationState.COMPLETED, 
            OrchestrationState.FAILED
        ]


class MultiTurnOrchestrator:
    """Orchestrates multi-turn evaluation execution.
    
    This class manages the complete lifecycle of multi-turn evaluations,
    including turn loop management, termination condition checking,
    state tracking, and async execution support.
    
    Requirements addressed:
    - 7.1: Multi-turn orchestration engine with turn loop management
    - 7.2: Feedback shaping and context management
    - 7.3: Termination policies and safety guards
    """
    
    def __init__(self,
                 policy_engine: Optional[PolicyEngine] = None,
                 feedback_processor: Optional[FeedbackProcessor] = None,
                 safety_guard: Optional[SafetyGuard] = None,
                 metrics_engine: Optional[MetricsEngine] = None,
                 logger: Optional[logging.Logger] = None):
        """Initialize the orchestrator.
        
        Args:
            policy_engine: Engine for termination decision making
            feedback_processor: Processor for feedback shaping
            safety_guard: Safety guard for secure execution
            metrics_engine: Engine for metrics calculation
            logger: Logger for orchestration events
        """
        self.policy_engine = policy_engine
        self.feedback_processor = feedback_processor
        self.safety_guard = safety_guard
        self.metrics_engine = metrics_engine
        self.logger = logger or logging.getLogger(__name__)
        
        # Active orchestration contexts
        self._active_contexts: Dict[str, OrchestrationContext] = {}
        
        # Event callbacks
        self._turn_callbacks: List[Callable[[OrchestrationContext, TurnResult], Awaitable[None]]] = []
        self._completion_callbacks: List[Callable[[OrchestrationContext, EvaluationResult], Awaitable[None]]] = []
        
        # Concurrency control
        self._max_concurrent_evaluations = 10
        self._evaluation_semaphore = asyncio.Semaphore(self._max_concurrent_evaluations)
    
    @performance_optimizer.profiler.profile_async_function
    async def execute_evaluation(self,
                                task: MultiTurnTask,
                                model_adapter: ModelAdapter,
                                config: MultiTurnConfig,
                                evaluation_id: Optional[str] = None) -> EvaluationResult:
        """Execute a complete multi-turn evaluation.
        
        Args:
            task: The multi-turn task to execute
            model_adapter: Adapter for the model being evaluated
            config: Configuration for the evaluation
            evaluation_id: Optional custom evaluation ID
            
        Returns:
            EvaluationResult containing the complete evaluation outcome
            
        Raises:
            TaskExecutionError: If evaluation execution fails
            SafetyViolationError: If safety violations occur
            ConfigurationError: If configuration is invalid
        """
        # Generate evaluation ID if not provided
        if evaluation_id is None:
            evaluation_id = f"eval_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        
        # Check cache for similar evaluation
        cache_key = performance_optimizer.create_cache_key(
            task.get_id(), str(model_adapter.model_id), str(config.__dict__)
        )
        cached_result = performance_optimizer.get_cached_result(f"evaluation_{cache_key}")
        if cached_result:
            self.logger.debug(f"Using cached result for evaluation {evaluation_id}")
            return cached_result
        
        # Validate configuration
        config.validate()
        
        # Create orchestration context
        context = OrchestrationContext(
            evaluation_id=evaluation_id,
            task=task,
            model_adapter=model_adapter,
            config=config,
            start_time=datetime.now()
        )
        
        self.logger.info(f"Starting evaluation {evaluation_id} for task {task.get_id()}")
        
        try:
            # Acquire semaphore for concurrency control
            async with self._evaluation_semaphore:
                # Register context
                self._active_contexts[evaluation_id] = context
                
                # Execute the evaluation
                result = await self._execute_evaluation_internal(context)
                
                # Cache the result if successful
                if result.success:
                    performance_optimizer.cache_result(
                        f"evaluation_{cache_key}", result, ttl=1800  # 30 minutes
                    )
                
                # Notify completion callbacks
                await self._notify_completion_callbacks(context, result)
                
                return result
                
        except Exception as e:
            self.logger.error(f"Evaluation {evaluation_id} failed: {str(e)}")
            context.state = OrchestrationState.FAILED
            raise
        finally:
            # Clean up context
            if evaluation_id in self._active_contexts:
                del self._active_contexts[evaluation_id]
    
    async def _execute_evaluation_internal(self, context: OrchestrationContext) -> EvaluationResult:
        """Internal method for executing evaluation.
        
        Args:
            context: Orchestration context
            
        Returns:
            EvaluationResult
        """
        context.state = OrchestrationState.INITIALIZING
        
        try:
            # Initialize environment
            context.environment = await self._initialize_environment(context)
            context.state = OrchestrationState.RUNNING
            
            # Get initial observation
            initial_observation = context.environment.reset()
            self.logger.debug(f"Environment initialized for {context.evaluation_id}")
            
            # Execute turn loop
            termination_reason = await self._execute_turn_loop(context, initial_observation)
            
            # Calculate final metrics
            final_metrics = await self._calculate_final_metrics(context)
            aggregated_metrics = await self._calculate_aggregated_metrics(context)
            
            # Create evaluation result
            result = EvaluationResult(
                evaluation_id=context.evaluation_id,
                task_id=context.task.get_id(),
                model_id=getattr(context.model_adapter, 'model_id', 'unknown'),
                start_time=context.start_time,
                end_time=datetime.now(),
                success=context.environment.success() if context.environment else False,
                total_turns=len(context.turn_results),
                turn_results=context.turn_results,
                final_metrics=final_metrics,
                aggregated_metrics=aggregated_metrics,
                termination_reason=termination_reason,
                metadata=context.metadata
            )
            
            context.state = OrchestrationState.COMPLETED
            self.logger.info(f"Evaluation {context.evaluation_id} completed successfully")
            
            return result
            
        except Exception as e:
            context.state = OrchestrationState.FAILED
            self.logger.error(f"Evaluation {context.evaluation_id} failed during execution: {str(e)}")
            raise
    
    async def _initialize_environment(self, context: OrchestrationContext) -> UnifiedEnv:
        """Initialize the task environment.
        
        Args:
            context: Orchestration context
            
        Returns:
            Initialized UnifiedEnv instance
        """
        # This would typically create the environment based on the task type
        # For now, we'll use a placeholder that would be implemented by adapters
        self.logger.debug(f"Initializing environment for task {context.task.get_id()}")
        
        # Check if task has a custom environment creation method
        if hasattr(context.task, 'create_environment'):
            return context.task.create_environment()
        
        # In a real implementation, this would delegate to the task's adapter
        # to create the appropriate environment
        env_config = {
            "task_id": context.task.get_id(),
            "config": context.task.get_config(),
            "evaluation_id": context.evaluation_id,
            "max_steps": context.config.max_turns,
            "success_probability": 0.2  # Lower probability for more realistic testing
        }
        
        # Placeholder - would be replaced with actual environment creation
        from .environment import MockEnvironment
        return MockEnvironment(env_config)
    
    async def _execute_turn_loop(self, 
                                context: OrchestrationContext, 
                                initial_observation: Any) -> TerminationReason:
        """Execute the main turn loop.
        
        Args:
            context: Orchestration context
            initial_observation: Initial observation from environment
            
        Returns:
            TerminationReason indicating why the loop terminated
        """
        current_observation = initial_observation
        
        while context.current_turn <= context.config.max_turns:
            self.logger.debug(f"Executing turn {context.current_turn} for {context.evaluation_id}")
            
            # Check timeout
            if context.elapsed_time > context.config.conversation_timeout:
                self.logger.warning(f"Evaluation {context.evaluation_id} timed out")
                return TerminationReason.TIMEOUT
            
            # Safety check
            if self.safety_guard and not await self._check_safety(context, current_observation):
                self.logger.warning(f"Safety violation in evaluation {context.evaluation_id}")
                return TerminationReason.SAFETY_VIOLATION
            
            try:
                # Execute turn
                turn_result = await self._execute_turn(context, current_observation)
                context.turn_results.append(turn_result)
                
                # Notify turn callbacks
                await self._notify_turn_callbacks(context, turn_result)
                
                # Check termination conditions
                termination_reason = await self._check_termination_conditions(context, turn_result)
                if termination_reason != TerminationReason.SUCCESS:
                    return termination_reason
                
                # Check if task is complete
                if turn_result.done or (context.environment and context.environment.success()):
                    self.logger.info(f"Task completed successfully in {context.current_turn} turns")
                    return TerminationReason.SUCCESS
                
                # Prepare for next turn
                current_observation = turn_result.observation
                context.current_turn += 1
                
            except SafetyViolationError as e:
                self.logger.error(f"Safety violation in turn {context.current_turn}: {str(e)}")
                return TerminationReason.SAFETY_VIOLATION
            except Exception as e:
                self.logger.error(f"Error in turn {context.current_turn}: {str(e)}")
                return TerminationReason.ERROR
        
        # Reached maximum turns
        self.logger.info(f"Evaluation {context.evaluation_id} reached maximum turns")
        return TerminationReason.MAX_TURNS
    
    async def _execute_turn(self, 
                           context: OrchestrationContext, 
                           observation: Any) -> TurnResult:
        """Execute a single turn.
        
        Args:
            context: Orchestration context
            observation: Current observation
            
        Returns:
            TurnResult for this turn
        """
        turn_start_time = time.time()
        
        try:
            # Create turn data
            turn_data = TurnData(
                turn_number=context.current_turn,
                input_context=str(observation),
                previous_actions=[tr.action for tr in context.turn_results],
                environment_state=context.environment.get_state().__dict__ if context.environment else {}
            )
            
            # Check if task has a custom execute_turn method (for testing)
            if hasattr(context.task, 'execute_turn'):
                # Use task's execute_turn method directly
                turn_result = context.task.execute_turn(turn_data)
                # Update execution time
                turn_result.execution_time = time.time() - turn_start_time
                
                # Process feedback if processor available (for testing completeness)
                if self.feedback_processor:
                    processed_feedback = await self._process_feedback(
                        context, turn_result.observation, turn_result.info
                    )
                    turn_result.processed_feedback = processed_feedback
                
                return turn_result
            
            # Generate action using model adapter
            action = await self._generate_action(context, turn_data)
            
            # Execute action in environment
            if context.environment:
                obs, reward, done, info = context.environment.step(action)
            else:
                # Fallback for testing
                obs, reward, done, info = f"Mock response to {action}", 0.5, False, {}
            
            # Process feedback if processor available
            processed_feedback = None
            if self.feedback_processor:
                processed_feedback = await self._process_feedback(context, obs, info)
            
            execution_time = time.time() - turn_start_time
            
            # Create turn result
            turn_result = TurnResult(
                turn=context.current_turn,
                action=action,
                observation=obs,
                reward=reward,
                done=done,
                info=info,
                execution_time=execution_time,
                processed_feedback=processed_feedback
            )
            
            return turn_result
            
        except Exception as e:
            execution_time = time.time() - turn_start_time
            self.logger.error(f"Turn {context.current_turn} execution failed: {str(e)}")
            
            # Return error turn result - this should trigger ERROR termination
            return TurnResult(
                turn=context.current_turn,
                action="ERROR",
                observation=f"Turn execution failed: {str(e)}",
                reward=0.0,
                done=True,  # Mark as done to trigger termination
                info={"error": str(e), "error_occurred": True},
                execution_time=execution_time
            )
    
    async def _generate_action(self, 
                              context: OrchestrationContext, 
                              turn_data: TurnData) -> Any:
        """Generate action using the model adapter.
        
        Args:
            context: Orchestration context
            turn_data: Data for the current turn
            
        Returns:
            Generated action
        """
        # Placeholder implementation - would delegate to model adapter
        if hasattr(context.model_adapter, 'generate_action'):
            return await context.model_adapter.generate_action(turn_data)
        else:
            # Mock action for testing
            return f"mock_action_turn_{context.current_turn}"
    
    async def _process_feedback(self, 
                               context: OrchestrationContext, 
                               observation: Any, 
                               info: Dict[str, Any]) -> ProcessedFeedback:
        """Process feedback using the feedback processor.
        
        Args:
            context: Orchestration context
            observation: Raw observation
            info: Additional information
            
        Returns:
            ProcessedFeedback
        """
        # Placeholder implementation - would delegate to feedback processor
        if hasattr(self.feedback_processor, 'process'):
            return await self.feedback_processor.process(observation, info, context.config.feedback_config)
        else:
            # Mock processed feedback for testing
            return ProcessedFeedback(
                original={"observation": observation, "info": info},
                filtered={"observation": observation, "info": info},
                contextualized={"observation": observation, "info": info},
                final={"observation": observation, "info": info}
            )
    
    async def _check_safety(self, 
                           context: OrchestrationContext, 
                           observation: Any) -> bool:
        """Check safety conditions.
        
        Args:
            context: Orchestration context
            observation: Current observation
            
        Returns:
            True if safe to continue
        """
        if hasattr(self.safety_guard, 'is_safe_to_continue'):
            return await self.safety_guard.is_safe_to_continue(context.environment, observation)
        return True
    
    async def _check_termination_conditions(self, 
                                           context: OrchestrationContext, 
                                           turn_result: TurnResult) -> TerminationReason:
        """Check if evaluation should terminate.
        
        Args:
            context: Orchestration context
            turn_result: Result of the current turn
            
        Returns:
            TerminationReason if should terminate, SUCCESS if should continue
        """
        # Check for errors first
        if turn_result.info.get("error_occurred", False):
            return TerminationReason.ERROR
        
        # Check policy engine if available
        if self.policy_engine:
            should_terminate, reason = await self.policy_engine.should_terminate(
                context.turn_results, context.environment
            )
            if should_terminate:
                return reason
        
        # Default termination logic
        if turn_result.done:
            return TerminationReason.SUCCESS
        
        return TerminationReason.SUCCESS  # Continue
    
    async def _calculate_final_metrics(self, context: OrchestrationContext) -> Dict[str, float]:
        """Calculate final metrics for the evaluation.
        
        Args:
            context: Orchestration context
            
        Returns:
            Dictionary of final metrics
        """
        if self.metrics_engine and hasattr(self.metrics_engine, 'calculate_metrics'):
            return await self.metrics_engine.calculate_metrics(
                context.turn_results, context.environment
            )
        
        # Basic metrics calculation
        total_time = sum(tr.execution_time for tr in context.turn_results)
        avg_reward = sum(tr.reward for tr in context.turn_results) / len(context.turn_results) if context.turn_results else 0.0
        
        return {
            "total_execution_time": total_time,
            "average_reward": avg_reward,
            "total_turns": float(len(context.turn_results)),
            "success_rate": 1.0 if (context.environment and context.environment.success()) else 0.0
        }
    
    async def _calculate_aggregated_metrics(self, context: OrchestrationContext) -> AggregatedMetrics:
        """Calculate aggregated metrics across all dimensions.
        
        Args:
            context: Orchestration context
            
        Returns:
            AggregatedMetrics instance
        """
        # Basic aggregated metrics calculation
        success = context.environment.success() if context.environment else False
        total_turns = len(context.turn_results)
        total_time = sum(tr.execution_time for tr in context.turn_results)
        
        return AggregatedMetrics(
            resolved_percentage=100.0 if success else 0.0,
            recall=1.0 if success else 0.0,
            mrr=1.0 / total_turns if success and total_turns > 0 else 0.0,
            avg_turns=float(total_turns),
            avg_steps=float(total_turns),  # Assuming 1 step per turn for now
            redundancy_rate=0.0,  # Would need more sophisticated calculation
            wall_time_per_solved=total_time if success else 0.0,
            tokens_per_solved=sum(tr.tokens_used for tr in context.turn_results) if success else 0,
            cost_per_solved=sum(tr.cost for tr in context.turn_results) if success else 0.0
        )
    
    async def _notify_turn_callbacks(self, 
                                    context: OrchestrationContext, 
                                    turn_result: TurnResult) -> None:
        """Notify registered turn callbacks.
        
        Args:
            context: Orchestration context
            turn_result: Result of the completed turn
        """
        for callback in self._turn_callbacks:
            try:
                await callback(context, turn_result)
            except Exception as e:
                self.logger.error(f"Turn callback failed: {str(e)}")
    
    async def _notify_completion_callbacks(self, 
                                          context: OrchestrationContext, 
                                          result: EvaluationResult) -> None:
        """Notify registered completion callbacks.
        
        Args:
            context: Orchestration context
            result: Final evaluation result
        """
        for callback in self._completion_callbacks:
            try:
                await callback(context, result)
            except Exception as e:
                self.logger.error(f"Completion callback failed: {str(e)}")
    
    # Public API methods
    
    def register_turn_callback(self, 
                              callback: Callable[[OrchestrationContext, TurnResult], Awaitable[None]]) -> None:
        """Register a callback to be called after each turn.
        
        Args:
            callback: Async callback function
        """
        self._turn_callbacks.append(callback)
    
    def register_completion_callback(self, 
                                    callback: Callable[[OrchestrationContext, EvaluationResult], Awaitable[None]]) -> None:
        """Register a callback to be called after evaluation completion.
        
        Args:
            callback: Async callback function
        """
        self._completion_callbacks.append(callback)
    
    def get_active_evaluations(self) -> List[str]:
        """Get list of active evaluation IDs.
        
        Returns:
            List of evaluation IDs currently running
        """
        return list(self._active_contexts.keys())
    
    def get_evaluation_status(self, evaluation_id: str) -> Optional[OrchestrationState]:
        """Get the status of a specific evaluation.
        
        Args:
            evaluation_id: ID of the evaluation
            
        Returns:
            OrchestrationState if evaluation exists, None otherwise
        """
        context = self._active_contexts.get(evaluation_id)
        return context.state if context else None
    
    async def pause_evaluation(self, evaluation_id: str) -> bool:
        """Pause a running evaluation.
        
        Args:
            evaluation_id: ID of the evaluation to pause
            
        Returns:
            True if successfully paused
        """
        context = self._active_contexts.get(evaluation_id)
        if context and context.state == OrchestrationState.RUNNING:
            context.state = OrchestrationState.PAUSED
            self.logger.info(f"Evaluation {evaluation_id} paused")
            return True
        return False
    
    async def resume_evaluation(self, evaluation_id: str) -> bool:
        """Resume a paused evaluation.
        
        Args:
            evaluation_id: ID of the evaluation to resume
            
        Returns:
            True if successfully resumed
        """
        context = self._active_contexts.get(evaluation_id)
        if context and context.state == OrchestrationState.PAUSED:
            context.state = OrchestrationState.RUNNING
            self.logger.info(f"Evaluation {evaluation_id} resumed")
            return True
        return False
    
    async def terminate_evaluation(self, evaluation_id: str) -> bool:
        """Terminate a running evaluation.
        
        Args:
            evaluation_id: ID of the evaluation to terminate
            
        Returns:
            True if successfully terminated
        """
        context = self._active_contexts.get(evaluation_id)
        if context and context.is_active:
            context.state = OrchestrationState.TERMINATING
            self.logger.info(f"Evaluation {evaluation_id} terminated by request")
            return True
        return False
    
    def set_max_concurrent_evaluations(self, max_concurrent: int) -> None:
        """Set the maximum number of concurrent evaluations.
        
        Args:
            max_concurrent: Maximum number of concurrent evaluations
        """
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive")
        
        self._max_concurrent_evaluations = max_concurrent
        self._evaluation_semaphore = asyncio.Semaphore(max_concurrent)
        self.logger.info(f"Max concurrent evaluations set to {max_concurrent}")