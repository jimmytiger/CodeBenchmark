"""
Extended Task Classes for AI Evaluation Engine

This module provides extended task classes that build upon lm-eval's Task base class
to support advanced evaluation scenarios including multi-turn conversations,
scenario-specific configurations, and enhanced metrics.
"""

import abc
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum

from lm_eval.api.task import Task, TaskConfig
from lm_eval.api.instance import Instance


eval_logger = logging.getLogger(__name__)


class ScenarioType(Enum):
    """Enumeration of supported scenario types."""
    SINGLE_TURN = "single_turn"
    MULTI_TURN = "multi_turn"
    DOMAIN_SPECIFIC = "domain_specific"


class ContextMode(Enum):
    """Enumeration of context modes for evaluation."""
    NO_CONTEXT = "no_context"
    MINIMAL_CONTEXT = "minimal_context"
    FULL_CONTEXT = "full_context"
    DOMAIN_CONTEXT = "domain_context"


class DifficultyLevel(Enum):
    """Enumeration of difficulty levels."""
    SIMPLE = "simple"
    INTERMEDIATE = "intermediate"
    COMPLEX = "complex"


@dataclass
class TurnConfig:
    """Configuration for a single turn in a multi-turn scenario."""
    turn_id: str
    turn_type: str
    role: str
    prompt_template: str
    expected_format: str
    validation_rules: List[str] = field(default_factory=list)
    evaluation_metrics: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    temperature: float = 0.1
    max_tokens: int = 1024
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TurnConfig to dictionary."""
        return {
            'turn_id': self.turn_id,
            'turn_type': self.turn_type,
            'role': self.role,
            'prompt_template': self.prompt_template,
            'expected_format': self.expected_format,
            'validation_rules': self.validation_rules,
            'evaluation_metrics': self.evaluation_metrics,
            'depends_on': self.depends_on,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }


@dataclass
class ScenarioConfig:
    """Configuration for evaluation scenarios."""
    scenario_id: str
    scenario_type: ScenarioType
    max_turns: int = 1
    conversation_timeout: int = 300
    enable_context_retention: bool = False
    turns: List[TurnConfig] = field(default_factory=list)
    scenario_metrics: List[str] = field(default_factory=list)
    success_criteria: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ScenarioConfig to dictionary."""
        return {
            'scenario_id': self.scenario_id,
            'scenario_type': self.scenario_type.value,
            'max_turns': self.max_turns,
            'conversation_timeout': self.conversation_timeout,
            'enable_context_retention': self.enable_context_retention,
            'turns': [turn.to_dict() for turn in self.turns],
            'scenario_metrics': self.scenario_metrics,
            'success_criteria': self.success_criteria
        }


@dataclass
class ModelConfiguration:
    """Extended model configuration for different backends."""
    model_id: str
    model_type: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model_kwargs: Dict[str, Any] = field(default_factory=dict)
    rate_limit_config: Dict[str, Any] = field(default_factory=dict)
    retry_config: Dict[str, Any] = field(default_factory=dict)
    performance_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ModelConfiguration to dictionary."""
        return {
            'model_id': self.model_id,
            'model_type': self.model_type,
            'api_base': self.api_base,
            'api_key': self.api_key,
            'model_kwargs': self.model_kwargs,
            'rate_limit_config': self.rate_limit_config,
            'retry_config': self.retry_config,
            'performance_config': self.performance_config
        }


@dataclass
class ExtendedTaskConfig(TaskConfig):
    """Extended task configuration with additional fields for advanced scenarios."""
    # Scenario-specific configuration
    scenario_config: Optional[ScenarioConfig] = None
    context_mode: ContextMode = ContextMode.FULL_CONTEXT
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    supported_languages: List[str] = field(default_factory=list)
    
    # Multi-turn specific
    max_turns: int = 1
    conversation_timeout: int = 300
    enable_context_retention: bool = False
    
    # Advanced metrics
    custom_metrics: List[str] = field(default_factory=list)
    composite_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Security and validation
    security_analysis_enabled: bool = False
    code_execution_enabled: bool = False
    sandbox_config: Dict[str, Any] = field(default_factory=dict)
    
    # Domain-specific settings
    domain: Optional[str] = None
    domain_knowledge_base: Optional[str] = None
    
    def to_dict(self, keep_callable: bool = False) -> Dict[str, Any]:
        """Extended to_dict method that includes new fields."""
        base_dict = super().to_dict(keep_callable=keep_callable)
        
        # Add extended fields
        extended_fields = {
            'scenario_config': self.scenario_config.to_dict() if self.scenario_config else None,
            'context_mode': self.context_mode.value,
            'difficulty_level': self.difficulty_level.value,
            'supported_languages': self.supported_languages,
            'max_turns': self.max_turns,
            'conversation_timeout': self.conversation_timeout,
            'enable_context_retention': self.enable_context_retention,
            'custom_metrics': self.custom_metrics,
            'composite_metrics': self.composite_metrics,
            'security_analysis_enabled': self.security_analysis_enabled,
            'code_execution_enabled': self.code_execution_enabled,
            'sandbox_config': self.sandbox_config,
            'domain': self.domain,
            'domain_knowledge_base': self.domain_knowledge_base
        }
        
        # Remove None values
        extended_fields = {k: v for k, v in extended_fields.items() if v is not None}
        
        return {**base_dict, **extended_fields}


class AdvancedTask(Task):
    """
    Extended Task class that supports advanced evaluation scenarios.
    
    This class extends lm-eval's Task base class with additional capabilities:
    - Multi-turn conversation support
    - Context mode management
    - Advanced metrics calculation
    - Security analysis integration
    - Domain-specific evaluation
    """
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        cache_dir: Optional[str] = None,
        download_mode=None,
        config: Optional[Dict] = None,
        scenario_config: Optional[ScenarioConfig] = None
    ):
        """Initialize AdvancedTask with extended configuration."""
        # Convert config to ExtendedTaskConfig if needed
        if config and not isinstance(config, ExtendedTaskConfig):
            config = ExtendedTaskConfig(**config)
        elif not config:
            config = ExtendedTaskConfig()
            
        super().__init__(data_dir, cache_dir, download_mode, config)
        
        self.scenario_config = scenario_config or config.scenario_config
        self._conversation_history: List[Dict[str, Any]] = []
        self._current_turn: int = 0
        
    @property
    def is_multi_turn(self) -> bool:
        """Check if this is a multi-turn task."""
        return (self.scenario_config and 
                self.scenario_config.scenario_type == ScenarioType.MULTI_TURN)
    
    @property
    def max_turns(self) -> int:
        """Get maximum number of turns for multi-turn scenarios."""
        if self.scenario_config:
            return self.scenario_config.max_turns
        return self.config.max_turns
    
    def get_turn_config(self, turn_id: str) -> Optional[TurnConfig]:
        """Get configuration for a specific turn."""
        if not self.scenario_config:
            return None
        
        for turn in self.scenario_config.turns:
            if turn.turn_id == turn_id:
                return turn
        return None
    
    def validate_turn_dependencies(self, turn_id: str) -> bool:
        """Validate that turn dependencies are satisfied."""
        turn_config = self.get_turn_config(turn_id)
        if not turn_config or not turn_config.depends_on:
            return True
        
        completed_turns = {turn['turn_id'] for turn in self._conversation_history}
        return all(dep in completed_turns for dep in turn_config.depends_on)
    
    def add_turn_to_history(self, turn_data: Dict[str, Any]) -> None:
        """Add a turn to the conversation history."""
        self._conversation_history.append(turn_data)
        self._current_turn += 1
    
    def get_conversation_context(self) -> List[Dict[str, Any]]:
        """Get the current conversation context."""
        return self._conversation_history.copy()
    
    def reset_conversation(self) -> None:
        """Reset conversation state for new evaluation."""
        self._conversation_history.clear()
        self._current_turn = 0
    
    def process_multi_turn_doc(self, doc: Dict[str, Any]) -> List[Instance]:
        """Process a document for multi-turn evaluation."""
        if not self.is_multi_turn:
            return [self.process_single_turn_doc(doc)]
        
        instances = []
        self.reset_conversation()
        
        for turn_config in self.scenario_config.turns:
            if not self.validate_turn_dependencies(turn_config.turn_id):
                eval_logger.warning(f"Skipping turn {turn_config.turn_id} due to unmet dependencies")
                continue
            
            # Create instance for this turn
            turn_instance = self.create_turn_instance(doc, turn_config)
            instances.append(turn_instance)
            
            # Add placeholder for turn result (will be filled during evaluation)
            self.add_turn_to_history({
                'turn_id': turn_config.turn_id,
                'turn_type': turn_config.turn_type,
                'role': turn_config.role,
                'prompt': turn_instance.args[0] if turn_instance.args else "",
                'response': None  # Will be filled during evaluation
            })
        
        return instances
    
    def process_single_turn_doc(self, doc: Dict[str, Any]) -> Instance:
        """Process a document for single-turn evaluation."""
        # Use the standard lm-eval processing with extended context
        context = self.build_context(doc)
        prompt = self.doc_to_text(doc, context)
        target = self.doc_to_target(doc) if hasattr(self, 'doc_to_target') else None
        
        return Instance(
            request_type=self.config.output_type,
            doc=doc,
            arguments=(prompt,),
            idx=doc.get('id', 0),
            metadata={
                'context_mode': self.config.context_mode.value,
                'difficulty_level': self.config.difficulty_level.value,
                'scenario': self.config.task,
                'target': target
            }
        )
    
    def create_turn_instance(self, doc: Dict[str, Any], turn_config: TurnConfig) -> Instance:
        """Create an Instance for a specific turn."""
        context = self.build_multi_turn_context(doc, turn_config)
        prompt = self.format_turn_prompt(doc, turn_config, context)
        
        return Instance(
            request_type=self.config.output_type,
            doc=doc,
            arguments=(prompt,),
            idx=f"{doc.get('id', 0)}_{turn_config.turn_id}",
            metadata={
                'turn_id': turn_config.turn_id,
                'turn_type': turn_config.turn_type,
                'role': turn_config.role,
                'context_mode': self.config.context_mode.value,
                'conversation_history': self.get_conversation_context(),
                'scenario': self.config.task
            }
        )
    
    def build_context(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Build context based on context mode."""
        context = {}
        
        if self.config.context_mode == ContextMode.NO_CONTEXT:
            return context
        
        if self.config.context_mode in [ContextMode.MINIMAL_CONTEXT, ContextMode.FULL_CONTEXT, ContextMode.DOMAIN_CONTEXT]:
            # Add basic context information
            context.update({
                'scenario': doc.get('scenario', ''),
                'difficulty': doc.get('difficulty', ''),
                'language': doc.get('language', '')
            })
        
        if self.config.context_mode in [ContextMode.FULL_CONTEXT, ContextMode.DOMAIN_CONTEXT]:
            # Add comprehensive context
            context.update({
                'problem_description': doc.get('problem', ''),
                'expected_format': doc.get('expected_format', ''),
                'constraints': doc.get('constraints', {}),
                'test_cases': doc.get('test_cases', [])
            })
        
        if self.config.context_mode == ContextMode.DOMAIN_CONTEXT:
            # Add domain-specific context
            context.update({
                'domain': self.config.domain,
                'domain_knowledge': doc.get('domain_knowledge', {}),
                'best_practices': doc.get('best_practices', []),
                'compliance_requirements': doc.get('compliance_requirements', [])
            })
        
        return context
    
    def build_multi_turn_context(self, doc: Dict[str, Any], turn_config: TurnConfig) -> Dict[str, Any]:
        """Build context for multi-turn scenarios."""
        context = self.build_context(doc)
        
        # Add conversation history if context retention is enabled
        if self.config.enable_context_retention:
            context['conversation_history'] = self.get_conversation_context()
        
        # Add turn-specific context
        context.update({
            'current_turn': self._current_turn,
            'max_turns': self.max_turns,
            'turn_role': turn_config.role,
            'expected_format': turn_config.expected_format
        })
        
        return context
    
    def format_turn_prompt(self, doc: Dict[str, Any], turn_config: TurnConfig, context: Dict[str, Any]) -> str:
        """Format prompt for a specific turn using the turn's template."""
        template = turn_config.prompt_template
        
        # Replace template variables with actual values
        template_vars = {
            **doc,
            **context,
            'turn_id': turn_config.turn_id,
            'role': turn_config.role
        }
        
        try:
            return template.format(**template_vars)
        except KeyError as e:
            eval_logger.warning(f"Missing template variable {e} in turn {turn_config.turn_id}")
            return template
    
    # Abstract methods from base Task class - must be implemented by subclasses
    @abc.abstractmethod
    def has_training_docs(self) -> bool:
        """Whether the task has a training set."""
        pass
    
    @abc.abstractmethod
    def has_validation_docs(self) -> bool:
        """Whether the task has a validation set."""
        pass
    
    @abc.abstractmethod
    def has_test_docs(self) -> bool:
        """Whether the task has a test set."""
        pass
    
    @abc.abstractmethod
    def training_docs(self):
        """Return training documents."""
        pass
    
    @abc.abstractmethod
    def validation_docs(self):
        """Return validation documents."""
        pass
    
    @abc.abstractmethod
    def test_docs(self):
        """Return test documents."""
        pass


class MultiTurnTask(AdvancedTask):
    """
    Specialized task class for multi-turn scenarios.
    
    This class provides specific implementations for multi-turn conversation
    evaluation with turn management, context retention, and conversation flow control.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize MultiTurnTask."""
        super().__init__(*args, **kwargs)
        
        # Ensure this is configured as a multi-turn task
        if not self.scenario_config:
            self.scenario_config = ScenarioConfig(
                scenario_id=self.config.task or "multi_turn_task",
                scenario_type=ScenarioType.MULTI_TURN,
                max_turns=self.config.max_turns
            )
        
        self.scenario_config.scenario_type = ScenarioType.MULTI_TURN
    
    def process_docs(self, dataset):
        """Process documents for multi-turn evaluation."""
        processed_docs = []
        
        for doc in dataset:
            # Each document becomes a multi-turn conversation
            turn_instances = self.process_multi_turn_doc(doc)
            processed_docs.extend(turn_instances)
        
        return processed_docs
    
    def evaluate_conversation(self, conversation_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Evaluate a complete multi-turn conversation."""
        metrics = {}
        
        # Calculate turn-specific metrics
        for turn_result in conversation_results:
            turn_metrics = self.evaluate_turn(turn_result)
            for metric_name, value in turn_metrics.items():
                if metric_name not in metrics:
                    metrics[metric_name] = []
                metrics[metric_name].append(value)
        
        # Calculate conversation-level metrics
        if self.config.enable_context_retention:
            metrics['context_retention_score'] = self.calculate_context_retention(conversation_results)
        
        metrics['goal_achievement_score'] = self.calculate_goal_achievement(conversation_results)
        metrics['conversation_coherence'] = self.calculate_coherence(conversation_results)
        
        # Aggregate turn metrics
        aggregated_metrics = {}
        for metric_name, values in metrics.items():
            if isinstance(values, list):
                aggregated_metrics[metric_name] = sum(values) / len(values) if values else 0.0
            else:
                aggregated_metrics[metric_name] = values
        
        return aggregated_metrics
    
    def evaluate_turn(self, turn_result: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate a single turn."""
        # Placeholder implementation - should be overridden by specific task implementations
        return {
            'turn_quality': 0.5,  # Placeholder
            'format_compliance': 1.0 if self.validate_turn_format(turn_result) else 0.0
        }
    
    def validate_turn_format(self, turn_result: Dict[str, Any]) -> bool:
        """Validate that turn result matches expected format."""
        turn_config = self.get_turn_config(turn_result.get('turn_id', ''))
        if not turn_config:
            return False
        
        # Basic validation - can be extended by subclasses
        return 'response' in turn_result and turn_result['response'] is not None
    
    def calculate_context_retention(self, conversation_results: List[Dict[str, Any]]) -> float:
        """Calculate context retention score across turns."""
        # Placeholder implementation
        return 0.8
    
    def calculate_goal_achievement(self, conversation_results: List[Dict[str, Any]]) -> float:
        """Calculate goal achievement score for the conversation."""
        # Placeholder implementation
        return 0.7
    
    def calculate_coherence(self, conversation_results: List[Dict[str, Any]]) -> float:
        """Calculate conversation coherence score."""
        # Placeholder implementation
        return 0.75