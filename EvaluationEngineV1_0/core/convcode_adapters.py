"""
ConvCodeBench and language-specific adapters for multi-turn evaluation.

This module implements adapters for ConvCodeBench (offline conversation log replay),
BugsInPy, and Defects4J benchmarks, providing cross-language bug fixing capabilities.
"""

import json
import os
import re
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import shutil

from .adapters import BenchmarkAdapter, AdapterInfo, StandardizedResult, AdapterStatus
from .data_models import TurnResult, ProcessedFeedback, TerminationReason
from .environment import UnifiedEnv
from .exceptions import AdapterError, TaskExecutionError, ConfigurationError
from .task_types import BaseTask, TaskType, TaskResult, TurnData


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation log.
    
    Attributes:
        turn_id: Unique identifier for this turn
        role: Role of the speaker (user, assistant, system)
        content: Content of the message
        timestamp: When this turn occurred
        metadata: Additional turn-specific information
    """
    turn_id: int
    role: str
    content: str
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ConversationLog:
    """Complete conversation log for replay.
    
    Attributes:
        conversation_id: Unique identifier for the conversation
        task_description: Description of the task being solved
        turns: List of conversation turns
        expected_outcome: Expected final outcome
        metadata: Additional conversation-level information
    """
    conversation_id: str
    task_description: str
    turns: List[ConversationTurn]
    expected_outcome: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationReplayEnvironment(UnifiedEnv):
    """Environment for replaying conversation logs with agent output replacement.
    
    This environment replays conversation logs from ConvCodeBench, allowing
    the evaluation of different agents by replacing their outputs while
    maintaining the conversation structure.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the conversation replay environment.
        
        Args:
            config: Configuration containing conversation log and replay settings
        """
        super().__init__(config)
        self.conversation_log: Optional[ConversationLog] = None
        self.current_turn = 0
        self.agent_role = config.get('agent_role', 'assistant')
        self.user_role = config.get('user_role', 'user')
        self.system_role = config.get('system_role', 'system')
        self.replace_agent_outputs = config.get('replace_agent_outputs', True)
        self.conversation_history: List[ConversationTurn] = []
        self.original_agent_outputs: List[str] = []
        self.replaced_outputs: List[str] = []
        self.task_completed = False
        self.success_criteria = config.get('success_criteria', {})
        
        # Load conversation log
        if 'conversation_log' in config:
            self.load_conversation_log(config['conversation_log'])
        elif 'conversation_file' in config:
            self.load_conversation_from_file(config['conversation_file'])
        else:
            raise ConfigurationError("Must provide either 'conversation_log' or 'conversation_file'")
    
    def load_conversation_log(self, log_data: Dict[str, Any]) -> None:
        """Load conversation log from dictionary data.
        
        Args:
            log_data: Dictionary containing conversation log data
        """
        turns = []
        for turn_data in log_data.get('turns', []):
            turn = ConversationTurn(
                turn_id=turn_data['turn_id'],
                role=turn_data['role'],
                content=turn_data['content'],
                timestamp=datetime.fromisoformat(turn_data.get('timestamp', datetime.now().isoformat())),
                metadata=turn_data.get('metadata', {})
            )
            turns.append(turn)
        
        self.conversation_log = ConversationLog(
            conversation_id=log_data['conversation_id'],
            task_description=log_data['task_description'],
            turns=turns,
            expected_outcome=log_data.get('expected_outcome', {}),
            metadata=log_data.get('metadata', {})
        )
        
        # Extract original agent outputs for comparison
        self.original_agent_outputs = [
            turn.content for turn in turns if turn.role == self.agent_role
        ]
    
    def load_conversation_from_file(self, file_path: str) -> None:
        """Load conversation log from JSON file.
        
        Args:
            file_path: Path to the conversation log file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            self.load_conversation_log(log_data)
        except Exception as e:
            raise ConfigurationError(f"Failed to load conversation from {file_path}: {e}")
    
    def reset(self) -> Dict[str, Any]:
        """Reset the environment to the beginning of the conversation.
        
        Returns:
            Initial observation containing task description and first user message
        """
        if not self.conversation_log:
            raise TaskExecutionError("No conversation log loaded")
        
        self.current_turn = 0
        self.conversation_history = []
        self.replaced_outputs = []
        self.task_completed = False
        
        # Find the first user message to start the conversation
        initial_context = {
            'task_description': self.conversation_log.task_description,
            'conversation_id': self.conversation_log.conversation_id,
            'total_turns': len(self.conversation_log.turns),
            'current_turn': self.current_turn,
            'conversation_history': []
        }
        
        # Add system messages and initial user message to context
        for turn in self.conversation_log.turns:
            if turn.role == self.system_role:
                initial_context['system_message'] = turn.content
            elif turn.role == self.user_role:
                initial_context['user_message'] = turn.content
                break
        
        return initial_context
    
    def step(self, action: Any) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """Execute a step in the conversation replay.
        
        Args:
            action: Agent's response to the current conversation state
            
        Returns:
            Tuple of (observation, reward, done, info)
        """
        if not self.conversation_log:
            raise TaskExecutionError("No conversation log loaded")
        
        if self.current_turn >= len(self.conversation_log.turns):
            return {}, 0.0, True, {'error': 'Conversation completed'}
        
        # Record the agent's output
        agent_output = str(action)
        self.replaced_outputs.append(agent_output)
        
        # Find the next agent turn in the original conversation
        agent_turn_found = False
        original_agent_output = ""
        
        while self.current_turn < len(self.conversation_log.turns):
            current_original_turn = self.conversation_log.turns[self.current_turn]
            
            if current_original_turn.role == self.agent_role:
                original_agent_output = current_original_turn.content
                agent_turn_found = True
                self.current_turn += 1
                break
            else:
                # Add non-agent turns to conversation history
                self.conversation_history.append(current_original_turn)
                self.current_turn += 1
        
        if not agent_turn_found:
            return {}, 0.0, True, {'error': 'No more agent turns in conversation'}
        
        # Create new turn with replaced output
        replaced_turn = ConversationTurn(
            turn_id=len(self.conversation_history),
            role=self.agent_role,
            content=agent_output,
            timestamp=datetime.now(),
            metadata={'original_content': original_agent_output}
        )
        self.conversation_history.append(replaced_turn)
        
        # Calculate reward based on similarity to original output
        reward = self._calculate_turn_reward(agent_output, original_agent_output)
        
        # Check if conversation is complete
        done = self.current_turn >= len(self.conversation_log.turns)
        if done:
            self.task_completed = True
        
        # Prepare next observation
        observation = self._get_next_observation()
        
        info = {
            'original_output': original_agent_output,
            'replaced_output': agent_output,
            'turn_reward': reward,
            'conversation_progress': self.current_turn / len(self.conversation_log.turns),
            'turns_remaining': len(self.conversation_log.turns) - self.current_turn
        }
        
        return observation, reward, done, info
    
    def success(self) -> bool:
        """Check if the conversation replay was successful.
        
        Returns:
            True if the conversation was completed successfully
        """
        if not self.task_completed:
            return False
        
        # Check success criteria if provided
        if self.success_criteria:
            return self._evaluate_success_criteria()
        
        # Default: successful if conversation completed
        return True
    
    def info(self) -> Dict[str, Any]:
        """Get current environment information.
        
        Returns:
            Dictionary containing current state information
        """
        return {
            'conversation_id': self.conversation_log.conversation_id if self.conversation_log else None,
            'current_turn': self.current_turn,
            'total_turns': len(self.conversation_log.turns) if self.conversation_log else 0,
            'conversation_progress': (
                self.current_turn / len(self.conversation_log.turns) 
                if self.conversation_log and len(self.conversation_log.turns) > 0 else 0.0
            ),
            'task_completed': self.task_completed,
            'original_agent_outputs': len(self.original_agent_outputs),
            'replaced_outputs': len(self.replaced_outputs),
            'conversation_history_length': len(self.conversation_history)
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.conversation_log:
            return {}
        
        total_turns = len(self.conversation_log.turns)
        agent_turns = len([t for t in self.conversation_log.turns if t.role == self.agent_role])
        
        metrics = {
            'conversation_completion': self.current_turn / total_turns if total_turns > 0 else 0.0,
            'agent_turns_completed': len(self.replaced_outputs) / agent_turns if agent_turns > 0 else 0.0,
            'average_turn_similarity': self._calculate_average_similarity(),
            'conversation_coherence': self._calculate_coherence_score()
        }
        
        return metrics
    
    def _get_next_observation(self) -> Dict[str, Any]:
        """Get the next observation for the agent.
        
        Returns:
            Dictionary containing the next conversation context
        """
        if not self.conversation_log or self.current_turn >= len(self.conversation_log.turns):
            return {'conversation_complete': True}
        
        # Find the next user message or system message
        next_messages = []
        temp_turn = self.current_turn
        
        while temp_turn < len(self.conversation_log.turns):
            turn = self.conversation_log.turns[temp_turn]
            if turn.role in [self.user_role, self.system_role]:
                next_messages.append({
                    'role': turn.role,
                    'content': turn.content,
                    'metadata': turn.metadata
                })
                temp_turn += 1
            else:
                break
        
        return {
            'conversation_history': [
                {'role': turn.role, 'content': turn.content} 
                for turn in self.conversation_history[-5:]  # Last 5 turns for context
            ],
            'next_messages': next_messages,
            'task_description': self.conversation_log.task_description,
            'conversation_progress': self.current_turn / len(self.conversation_log.turns)
        }
    
    def _calculate_turn_reward(self, agent_output: str, original_output: str) -> float:
        """Calculate reward for a single turn based on output similarity.
        
        Args:
            agent_output: Output from the agent being evaluated
            original_output: Original output from the conversation log
            
        Returns:
            Reward score between 0.0 and 1.0
        """
        # Simple similarity based on common words and structure
        agent_words = set(agent_output.lower().split())
        original_words = set(original_output.lower().split())
        
        if not original_words:
            return 1.0 if not agent_words else 0.5
        
        # Jaccard similarity
        intersection = len(agent_words.intersection(original_words))
        union = len(agent_words.union(original_words))
        
        jaccard_similarity = intersection / union if union > 0 else 0.0
        
        # Length similarity
        length_ratio = min(len(agent_output), len(original_output)) / max(len(agent_output), len(original_output))
        
        # Combined score
        return (jaccard_similarity * 0.7 + length_ratio * 0.3)
    
    def _calculate_average_similarity(self) -> float:
        """Calculate average similarity across all replaced outputs.
        
        Returns:
            Average similarity score
        """
        if not self.replaced_outputs or not self.original_agent_outputs:
            return 0.0
        
        similarities = []
        for i, replaced in enumerate(self.replaced_outputs):
            if i < len(self.original_agent_outputs):
                similarity = self._calculate_turn_reward(replaced, self.original_agent_outputs[i])
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _calculate_coherence_score(self) -> float:
        """Calculate conversation coherence score.
        
        Returns:
            Coherence score between 0.0 and 1.0
        """
        # Simple coherence based on conversation flow
        if len(self.conversation_history) < 2:
            return 1.0
        
        # Check for consistent role alternation and reasonable response lengths
        coherence_factors = []
        
        for i in range(1, len(self.conversation_history)):
            prev_turn = self.conversation_history[i-1]
            curr_turn = self.conversation_history[i]
            
            # Role alternation (good if roles alternate)
            role_alternation = 1.0 if prev_turn.role != curr_turn.role else 0.5
            coherence_factors.append(role_alternation)
            
            # Response length reasonableness
            if curr_turn.role == self.agent_role:
                length_score = min(1.0, len(curr_turn.content) / 100)  # Normalize to reasonable length
                coherence_factors.append(length_score)
        
        return sum(coherence_factors) / len(coherence_factors) if coherence_factors else 1.0
    
    def _evaluate_success_criteria(self) -> bool:
        """Evaluate custom success criteria.
        
        Returns:
            True if success criteria are met
        """
        # Implement custom success criteria evaluation
        # This could include checking for specific patterns, code correctness, etc.
        
        min_similarity = self.success_criteria.get('min_similarity', 0.5)
        min_coherence = self.success_criteria.get('min_coherence', 0.7)
        
        avg_similarity = self._calculate_average_similarity()
        coherence = self._calculate_coherence_score()
        
        return avg_similarity >= min_similarity and coherence >= min_coherence


class ConvCodeBenchAdapter(BenchmarkAdapter):
    """Adapter for ConvCodeBench offline conversation log replay.
    
    This adapter enables evaluation of agents by replaying conversation logs
    from ConvCodeBench and replacing agent outputs with new agent responses.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the ConvCodeBench adapter.
        
        Args:
            config: Configuration for the adapter
        """
        super().__init__(config)
        self.dataset_path = config.get('dataset_path', '')
        self.conversation_logs: List[ConversationLog] = []
        self.supported_languages = config.get('supported_languages', ['python', 'java', 'javascript'])
        self.logger = logging.getLogger(__name__)
    
    def get_adapter_info(self) -> AdapterInfo:
        """Get information about this adapter.
        
        Returns:
            AdapterInfo describing the ConvCodeBench adapter
        """
        return AdapterInfo(
            name="convcodebench",
            version="1.0.0",
            description="ConvCodeBench adapter for offline conversation log replay",
            supported_task_types=[TaskType.MULTI_TURN],
            required_dependencies=["json", "pathlib"],
            supported_formats=["json", "jsonl"],
            capabilities=[
                "conversation_replay",
                "agent_output_replacement", 
                "multi_language_support",
                "similarity_scoring",
                "coherence_evaluation"
            ],
            metadata={
                "supported_languages": self.supported_languages,
                "dataset_path": self.dataset_path
            }
        )
    
    def initialize(self) -> bool:
        """Initialize the adapter and load conversation logs.
        
        Returns:
            True if initialization was successful
        """
        try:
            self._set_status(AdapterStatus.INITIALIZING)
            
            # Validate dataset path
            if not self.dataset_path:
                raise ConfigurationError("dataset_path is required for ConvCodeBench adapter")
            
            if not os.path.exists(self.dataset_path):
                raise ConfigurationError(f"Dataset path does not exist: {self.dataset_path}")
            
            # Load conversation logs
            self._load_conversation_logs()
            
            self._set_status(AdapterStatus.READY)
            self.logger.info(f"ConvCodeBench adapter initialized with {len(self.conversation_logs)} conversation logs")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize ConvCodeBench adapter: {e}"
            self._set_status(AdapterStatus.ERROR, error_msg)
            return False
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create a conversation replay environment.
        
        Args:
            task_config: Configuration for the specific task
            
        Returns:
            ConversationReplayEnvironment instance
        """
        if not self.is_ready():
            raise AdapterError("Adapter is not ready")
        
        # Validate task configuration
        self.validate_task_config(task_config)
        
        # Find the conversation log for this task
        conversation_id = task_config.get('conversation_id')
        conversation_log = None
        
        if conversation_id:
            conversation_log = next(
                (log for log in self.conversation_logs if log.conversation_id == conversation_id),
                None
            )
            if not conversation_log:
                raise ConfigurationError(f"Conversation log not found: {conversation_id}")
        else:
            # Use the first available conversation log
            if self.conversation_logs:
                conversation_log = self.conversation_logs[0]
            else:
                raise ConfigurationError("No conversation logs available")
        
        # Create environment configuration
        env_config = {
            'conversation_log': {
                'conversation_id': conversation_log.conversation_id,
                'task_description': conversation_log.task_description,
                'turns': [
                    {
                        'turn_id': turn.turn_id,
                        'role': turn.role,
                        'content': turn.content,
                        'timestamp': turn.timestamp.isoformat(),
                        'metadata': turn.metadata
                    }
                    for turn in conversation_log.turns
                ],
                'expected_outcome': conversation_log.expected_outcome,
                'metadata': conversation_log.metadata
            },
            'agent_role': task_config.get('agent_role', 'assistant'),
            'user_role': task_config.get('user_role', 'user'),
            'system_role': task_config.get('system_role', 'system'),
            'replace_agent_outputs': task_config.get('replace_agent_outputs', True),
            'success_criteria': task_config.get('success_criteria', {})
        }
        
        return ConversationReplayEnvironment(env_config)
    
    def load_tasks(self, task_filter: Optional[Dict[str, Any]] = None) -> List[BaseTask]:
        """Load available conversation replay tasks.
        
        Args:
            task_filter: Optional filter criteria
            
        Returns:
            List of available tasks
        """
        if not self.is_ready():
            raise AdapterError("Adapter is not ready")
        
        tasks = []
        for log in self.conversation_logs:
            # Apply filters if provided
            if task_filter:
                if 'language' in task_filter:
                    log_language = log.metadata.get('language', 'unknown')
                    if log_language not in task_filter['language']:
                        continue
                
                if 'difficulty' in task_filter:
                    log_difficulty = log.metadata.get('difficulty', 'unknown')
                    if log_difficulty not in task_filter['difficulty']:
                        continue
            
            task = ConvCodeBenchTask(
                task_id=f"convcodebench_{log.conversation_id}",
                conversation_log=log,
                adapter=self
            )
            tasks.append(task)
        
        return tasks
    
    def convert_results(self, results: Any) -> StandardizedResult:
        """Convert conversation replay results to standardized format.
        
        Args:
            results: Raw results from conversation replay
            
        Returns:
            StandardizedResult object
        """
        if isinstance(results, dict):
            return StandardizedResult(
                task_id=results.get('task_id', 'unknown'),
                adapter_name=self.get_adapter_info().name,
                success=results.get('success', False),
                score=results.get('score', 0.0),
                execution_time=results.get('execution_time', 0.0),
                turns=results.get('turns', 0),
                tokens_used=results.get('tokens_used', 0),
                cost=results.get('cost', 0.0),
                metadata={
                    'conversation_id': results.get('conversation_id'),
                    'similarity_score': results.get('similarity_score', 0.0),
                    'coherence_score': results.get('coherence_score', 0.0),
                    'original_outputs': results.get('original_outputs', 0),
                    'replaced_outputs': results.get('replaced_outputs', 0)
                },
                raw_result=results
            )
        else:
            raise AdapterError(f"Cannot convert results of type {type(results)}")
    
    def validate_task_config(self, task_config: Dict[str, Any]) -> bool:
        """Validate task configuration for ConvCodeBench.
        
        Args:
            task_config: Task configuration to validate
            
        Returns:
            True if configuration is valid
        """
        # Basic validation
        if not isinstance(task_config, dict):
            raise ConfigurationError("Task configuration must be a dictionary")
        
        # ConvCodeBench-specific validation
        if 'conversation_id' not in task_config and not self.conversation_logs:
            raise ConfigurationError("Either conversation_id must be specified or conversation logs must be loaded")
        
        return True
    
    def _load_conversation_logs(self) -> None:
        """Load conversation logs from the dataset path."""
        dataset_path = Path(self.dataset_path)
        
        if dataset_path.is_file():
            # Single file
            if dataset_path.suffix == '.json':
                self._load_json_file(dataset_path)
            elif dataset_path.suffix == '.jsonl':
                self._load_jsonl_file(dataset_path)
            else:
                raise ConfigurationError(f"Unsupported file format: {dataset_path.suffix}")
        elif dataset_path.is_dir():
            # Directory of files
            for file_path in dataset_path.glob('*.json'):
                self._load_json_file(file_path)
            for file_path in dataset_path.glob('*.jsonl'):
                self._load_jsonl_file(file_path)
        else:
            raise ConfigurationError(f"Invalid dataset path: {dataset_path}")
        
        if not self.conversation_logs:
            raise ConfigurationError("No conversation logs found in dataset path")
    
    def _load_json_file(self, file_path: Path) -> None:
        """Load conversation logs from a JSON file.
        
        Args:
            file_path: Path to the JSON file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                # Multiple conversation logs
                for log_data in data:
                    self._parse_conversation_log(log_data)
            else:
                # Single conversation log
                self._parse_conversation_log(data)
                
        except Exception as e:
            self.logger.warning(f"Failed to load JSON file {file_path}: {e}")
    
    def _load_jsonl_file(self, file_path: Path) -> None:
        """Load conversation logs from a JSONL file.
        
        Args:
            file_path: Path to the JSONL file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            log_data = json.loads(line)
                            self._parse_conversation_log(log_data)
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"Invalid JSON on line {line_num} in {file_path}: {e}")
                            
        except Exception as e:
            self.logger.warning(f"Failed to load JSONL file {file_path}: {e}")
    
    def _parse_conversation_log(self, log_data: Dict[str, Any]) -> None:
        """Parse a conversation log from dictionary data.
        
        Args:
            log_data: Dictionary containing conversation log data
        """
        try:
            turns = []
            for turn_data in log_data.get('turns', []):
                turn = ConversationTurn(
                    turn_id=turn_data.get('turn_id', len(turns)),
                    role=turn_data['role'],
                    content=turn_data['content'],
                    timestamp=datetime.fromisoformat(
                        turn_data.get('timestamp', datetime.now().isoformat())
                    ),
                    metadata=turn_data.get('metadata', {})
                )
                turns.append(turn)
            
            conversation_log = ConversationLog(
                conversation_id=log_data['conversation_id'],
                task_description=log_data.get('task_description', ''),
                turns=turns,
                expected_outcome=log_data.get('expected_outcome', {}),
                metadata=log_data.get('metadata', {})
            )
            
            self.conversation_logs.append(conversation_log)
            
        except KeyError as e:
            self.logger.warning(f"Missing required field in conversation log: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to parse conversation log: {e}")


class ConvCodeBenchTask(BaseTask):
    """Task implementation for ConvCodeBench conversation replay."""
    
    def __init__(self, task_id: str, conversation_log: ConversationLog, adapter: ConvCodeBenchAdapter):
        """Initialize the task.
        
        Args:
            task_id: Unique identifier for the task
            conversation_log: Conversation log to replay
            adapter: Parent adapter instance
        """
        self.task_id = task_id
        self.conversation_log = conversation_log
        self.adapter = adapter
    
    def get_task_type(self) -> TaskType:
        """Get the task type.
        
        Returns:
            TaskType.MULTI_TURN
        """
        return TaskType.MULTI_TURN
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate task configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        return self.adapter.validate_task_config(config)
    
    def get_required_capabilities(self) -> List[str]:
        """Get required capabilities for this task.
        
        Returns:
            List of required capabilities
        """
        return [
            "conversation_replay",
            "multi_turn_interaction",
            "text_generation"
        ]
    
    def get_id(self) -> str:
        """Get task identifier.
        
        Returns:
            Task ID string
        """
        return self.task_id
    
    def get_description(self) -> str:
        """Get task description.
        
        Returns:
            Task description string
        """
        return self.conversation_log.task_description
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get task metadata.
        
        Returns:
            Dictionary of task metadata
        """
        return {
            'conversation_id': self.conversation_log.conversation_id,
            'total_turns': len(self.conversation_log.turns),
            'agent_turns': len([t for t in self.conversation_log.turns if t.role == 'assistant']),
            'language': self.conversation_log.metadata.get('language', 'unknown'),
            'difficulty': self.conversation_log.metadata.get('difficulty', 'unknown'),
            'expected_outcome': self.conversation_log.expected_outcome
        }

# Language-specific adapters for cross-language bug fixing

class BugFixEnvironment(UnifiedEnv):
    """Base environment for bug fixing tasks.
    
    This environment provides common functionality for bug fixing across
    different programming languages and frameworks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the bug fix environment.
        
        Args:
            config: Configuration containing bug information and test setup
        """
        super().__init__(config)
        self.bug_id = config['bug_id']
        self.project_path = config.get('project_path', '')
        self.test_command = config.get('test_command', '')
        self.build_command = config.get('build_command', '')
        self.language = config.get('language', 'unknown')
        self.bug_description = config.get('bug_description', '')
        self.failing_tests = config.get('failing_tests', [])
        self.expected_fix = config.get('expected_fix', {})
        
        # State tracking
        self.current_step = 0
        self.max_steps = config.get('max_steps', 50)
        self.files_modified = []
        self.test_results = {}
        self.build_successful = False
        self.bug_fixed = False
        self.working_directory = None
        
        # Setup working directory
        self._setup_working_directory()
    
    def _setup_working_directory(self) -> None:
        """Setup isolated working directory for bug fixing."""
        if self.project_path and os.path.exists(self.project_path):
            # Create temporary working directory
            self.working_directory = tempfile.mkdtemp(prefix=f"bugfix_{self.bug_id}_")
            
            # Copy project to working directory
            shutil.copytree(self.project_path, 
                          os.path.join(self.working_directory, 'project'),
                          dirs_exist_ok=True)
            
            self.project_path = os.path.join(self.working_directory, 'project')
        else:
            raise ConfigurationError(f"Invalid project path: {self.project_path}")
    
    def reset(self) -> Dict[str, Any]:
        """Reset the environment to initial bug state.
        
        Returns:
            Initial observation with bug information
        """
        self.current_step = 0
        self.files_modified = []
        self.test_results = {}
        self.build_successful = False
        self.bug_fixed = False
        
        # Run initial tests to confirm bug exists
        initial_test_results = self._run_tests()
        
        return {
            'bug_id': self.bug_id,
            'bug_description': self.bug_description,
            'language': self.language,
            'project_path': self.project_path,
            'failing_tests': self.failing_tests,
            'initial_test_results': initial_test_results,
            'step': self.current_step,
            'max_steps': self.max_steps
        }
    
    def step(self, action: Any) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """Execute a bug fixing action.
        
        Args:
            action: Action to take (file modification, test run, etc.)
            
        Returns:
            Tuple of (observation, reward, done, info)
        """
        self.current_step += 1
        
        if self.current_step > self.max_steps:
            return {}, 0.0, True, {'error': 'Maximum steps exceeded'}
        
        # Parse and execute action
        try:
            result = self._execute_action(action)
            observation = result.get('observation', {})
            reward = result.get('reward', 0.0)
            info = result.get('info', {})
            
            # Check if bug is fixed
            if result.get('test_passed', False):
                self.bug_fixed = True
                reward += 10.0  # Bonus for fixing the bug
            
            done = self.bug_fixed or self.current_step >= self.max_steps
            
            # Add step information
            observation.update({
                'step': self.current_step,
                'max_steps': self.max_steps,
                'files_modified': len(self.files_modified),
                'bug_fixed': self.bug_fixed
            })
            
            info.update({
                'action_type': result.get('action_type', 'unknown'),
                'execution_time': result.get('execution_time', 0.0),
                'files_modified_this_step': result.get('files_modified', [])
            })
            
            return observation, reward, done, info
            
        except Exception as e:
            error_info = {
                'error': str(e),
                'action_failed': True,
                'step': self.current_step
            }
            return {}, -1.0, False, error_info
    
    def success(self) -> bool:
        """Check if the bug has been successfully fixed.
        
        Returns:
            True if bug is fixed and all tests pass
        """
        return self.bug_fixed
    
    def info(self) -> Dict[str, Any]:
        """Get current environment information.
        
        Returns:
            Dictionary containing current state
        """
        return {
            'bug_id': self.bug_id,
            'language': self.language,
            'current_step': self.current_step,
            'max_steps': self.max_steps,
            'files_modified': len(self.files_modified),
            'bug_fixed': self.bug_fixed,
            'build_successful': self.build_successful,
            'working_directory': self.working_directory,
            'test_results': self.test_results
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        return {
            'steps_taken': float(self.current_step),
            'step_efficiency': 1.0 - (self.current_step / self.max_steps),
            'files_modified': float(len(self.files_modified)),
            'bug_fixed': 1.0 if self.bug_fixed else 0.0,
            'test_pass_rate': self._calculate_test_pass_rate()
        }
    
    def _execute_action(self, action: Any) -> Dict[str, Any]:
        """Execute a specific action.
        
        Args:
            action: Action to execute
            
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        action_str = str(action)
        
        # Parse action type and parameters
        if action_str.startswith('modify_file:'):
            return self._handle_file_modification(action_str)
        elif action_str.startswith('run_tests'):
            return self._handle_test_execution()
        elif action_str.startswith('build'):
            return self._handle_build()
        elif action_str.startswith('read_file:'):
            return self._handle_file_read(action_str)
        else:
            # Treat as general code modification
            return self._handle_code_modification(action_str)
    
    def _handle_file_modification(self, action: str) -> Dict[str, Any]:
        """Handle file modification action.
        
        Args:
            action: File modification action string
            
        Returns:
            Dictionary with modification results
        """
        # Parse file modification command
        # Format: modify_file:path/to/file.py:line_start:line_end:new_content
        parts = action.split(':', 4)
        if len(parts) < 5:
            return {'error': 'Invalid file modification format'}
        
        file_path = parts[1]
        try:
            line_start = int(parts[2])
            line_end = int(parts[3])
            new_content = parts[4]
        except ValueError:
            return {'error': 'Invalid line numbers'}
        
        full_path = os.path.join(self.project_path, file_path)
        
        try:
            # Read current file content
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Modify lines
            lines[line_start-1:line_end] = [new_content + '\n']
            
            # Write back to file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            if file_path not in self.files_modified:
                self.files_modified.append(file_path)
            
            return {
                'action_type': 'file_modification',
                'observation': {'file_modified': file_path, 'lines_changed': line_end - line_start + 1},
                'reward': 0.1,  # Small reward for taking action
                'files_modified': [file_path],
                'execution_time': time.time() - time.time()
            }
            
        except Exception as e:
            return {'error': f'File modification failed: {e}'}
    
    def _handle_test_execution(self) -> Dict[str, Any]:
        """Handle test execution action.
        
        Returns:
            Dictionary with test results
        """
        test_results = self._run_tests()
        
        # Calculate reward based on test results
        reward = 0.0
        if test_results.get('all_passed', False):
            reward = 5.0
            self.bug_fixed = True
        elif test_results.get('some_passed', False):
            reward = 1.0
        
        return {
            'action_type': 'test_execution',
            'observation': {'test_results': test_results},
            'reward': reward,
            'test_passed': test_results.get('all_passed', False),
            'execution_time': test_results.get('execution_time', 0.0)
        }
    
    def _handle_build(self) -> Dict[str, Any]:
        """Handle build action.
        
        Returns:
            Dictionary with build results
        """
        build_results = self._run_build()
        
        reward = 1.0 if build_results.get('success', False) else -0.5
        self.build_successful = build_results.get('success', False)
        
        return {
            'action_type': 'build',
            'observation': {'build_results': build_results},
            'reward': reward,
            'execution_time': build_results.get('execution_time', 0.0)
        }
    
    def _handle_file_read(self, action: str) -> Dict[str, Any]:
        """Handle file read action.
        
        Args:
            action: File read action string
            
        Returns:
            Dictionary with file content
        """
        # Format: read_file:path/to/file.py
        parts = action.split(':', 1)
        if len(parts) < 2:
            return {'error': 'Invalid file read format'}
        
        file_path = parts[1]
        full_path = os.path.join(self.project_path, file_path)
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                'action_type': 'file_read',
                'observation': {'file_content': content, 'file_path': file_path},
                'reward': 0.0,  # No reward for reading
                'execution_time': 0.0
            }
            
        except Exception as e:
            return {'error': f'File read failed: {e}'}
    
    def _handle_code_modification(self, action: str) -> Dict[str, Any]:
        """Handle general code modification.
        
        Args:
            action: Code modification string
            
        Returns:
            Dictionary with modification results
        """
        # This is a simplified handler - in practice, this would need
        # more sophisticated parsing and application of code changes
        return {
            'action_type': 'code_modification',
            'observation': {'modification_attempted': True},
            'reward': 0.1,
            'execution_time': 0.0
        }
    
    def _run_tests(self) -> Dict[str, Any]:
        """Run tests to check bug status.
        
        Returns:
            Dictionary with test results
        """
        if not self.test_command:
            return {'error': 'No test command configured'}
        
        start_time = time.time()
        
        try:
            # Run test command in project directory
            result = subprocess.run(
                self.test_command,
                shell=True,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            # Parse test results
            all_passed = result.returncode == 0
            output = result.stdout + result.stderr
            
            # Count passed/failed tests (simplified)
            passed_count = output.count('PASSED') + output.count('OK')
            failed_count = output.count('FAILED') + output.count('ERROR')
            
            test_results = {
                'all_passed': all_passed,
                'some_passed': passed_count > 0,
                'passed_count': passed_count,
                'failed_count': failed_count,
                'output': output,
                'return_code': result.returncode,
                'execution_time': execution_time
            }
            
            self.test_results = test_results
            return test_results
            
        except subprocess.TimeoutExpired:
            return {'error': 'Test execution timed out'}
        except Exception as e:
            return {'error': f'Test execution failed: {e}'}
    
    def _run_build(self) -> Dict[str, Any]:
        """Run build command.
        
        Returns:
            Dictionary with build results
        """
        if not self.build_command:
            return {'success': True, 'message': 'No build command configured'}
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                self.build_command,
                shell=True,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout + result.stderr,
                'return_code': result.returncode,
                'execution_time': execution_time
            }
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Build timed out'}
        except Exception as e:
            return {'success': False, 'error': f'Build failed: {e}'}
    
    def _calculate_test_pass_rate(self) -> float:
        """Calculate current test pass rate.
        
        Returns:
            Test pass rate between 0.0 and 1.0
        """
        if not self.test_results:
            return 0.0
        
        passed = self.test_results.get('passed_count', 0)
        failed = self.test_results.get('failed_count', 0)
        total = passed + failed
        
        return passed / total if total > 0 else 0.0
    
    def cleanup(self) -> None:
        """Clean up working directory."""
        if self.working_directory and os.path.exists(self.working_directory):
            try:
                shutil.rmtree(self.working_directory)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to cleanup working directory: {e}")


class BugsInPyAdapter(BenchmarkAdapter):
    """Adapter for BugsInPy benchmark - Python bug fixing tasks.
    
    BugsInPy is a collection of reproducible bugs in Python projects
    for evaluating automated program repair techniques.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the BugsInPy adapter.
        
        Args:
            config: Configuration for the adapter
        """
        super().__init__(config)
        self.dataset_path = config.get('dataset_path', '')
        self.bugs_data: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
    
    def get_adapter_info(self) -> AdapterInfo:
        """Get information about this adapter.
        
        Returns:
            AdapterInfo describing the BugsInPy adapter
        """
        return AdapterInfo(
            name="bugsinpy",
            version="1.0.0",
            description="BugsInPy adapter for Python bug fixing evaluation",
            supported_task_types=[TaskType.MULTI_TURN],
            required_dependencies=["subprocess", "tempfile", "shutil"],
            supported_formats=["json", "csv"],
            capabilities=[
                "python_bug_fixing",
                "test_execution",
                "code_modification",
                "build_verification"
            ],
            metadata={
                "language": "python",
                "dataset_path": self.dataset_path
            }
        )
    
    def initialize(self) -> bool:
        """Initialize the adapter and load bug data.
        
        Returns:
            True if initialization was successful
        """
        try:
            self._set_status(AdapterStatus.INITIALIZING)
            
            # Validate dataset path
            if not self.dataset_path:
                raise ConfigurationError("dataset_path is required for BugsInPy adapter")
            
            if not os.path.exists(self.dataset_path):
                raise ConfigurationError(f"Dataset path does not exist: {self.dataset_path}")
            
            # Load bug data
            self._load_bugs_data()
            
            self._set_status(AdapterStatus.READY)
            self.logger.info(f"BugsInPy adapter initialized with {len(self.bugs_data)} bugs")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize BugsInPy adapter: {e}"
            self._set_status(AdapterStatus.ERROR, error_msg)
            return False
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create a bug fixing environment for Python.
        
        Args:
            task_config: Configuration for the specific bug
            
        Returns:
            BugFixEnvironment instance configured for Python
        """
        if not self.is_ready():
            raise AdapterError("Adapter is not ready")
        
        self.validate_task_config(task_config)
        
        # Find bug data
        bug_id = task_config['bug_id']
        bug_data = next((bug for bug in self.bugs_data if bug['bug_id'] == bug_id), None)
        
        if not bug_data:
            raise ConfigurationError(f"Bug not found: {bug_id}")
        
        # Create environment configuration
        env_config = {
            'bug_id': bug_id,
            'project_path': bug_data['project_path'],
            'test_command': bug_data.get('test_command', 'python -m pytest'),
            'build_command': bug_data.get('build_command', ''),
            'language': 'python',
            'bug_description': bug_data.get('description', ''),
            'failing_tests': bug_data.get('failing_tests', []),
            'expected_fix': bug_data.get('expected_fix', {}),
            'max_steps': task_config.get('max_steps', 50)
        }
        
        return BugFixEnvironment(env_config)
    
    def load_tasks(self, task_filter: Optional[Dict[str, Any]] = None) -> List[BaseTask]:
        """Load available Python bug fixing tasks.
        
        Args:
            task_filter: Optional filter criteria
            
        Returns:
            List of available tasks
        """
        if not self.is_ready():
            raise AdapterError("Adapter is not ready")
        
        tasks = []
        for bug_data in self.bugs_data:
            # Apply filters if provided
            if task_filter:
                if 'project' in task_filter:
                    if bug_data.get('project') not in task_filter['project']:
                        continue
                
                if 'difficulty' in task_filter:
                    if bug_data.get('difficulty') not in task_filter['difficulty']:
                        continue
            
            task = BugFixTask(
                task_id=f"bugsinpy_{bug_data['bug_id']}",
                bug_data=bug_data,
                adapter=self
            )
            tasks.append(task)
        
        return tasks
    
    def convert_results(self, results: Any) -> StandardizedResult:
        """Convert bug fixing results to standardized format.
        
        Args:
            results: Raw results from bug fixing
            
        Returns:
            StandardizedResult object
        """
        if isinstance(results, dict):
            return StandardizedResult(
                task_id=results.get('task_id', 'unknown'),
                adapter_name=self.get_adapter_info().name,
                success=results.get('bug_fixed', False),
                score=1.0 if results.get('bug_fixed', False) else 0.0,
                execution_time=results.get('execution_time', 0.0),
                turns=results.get('steps_taken', 0),
                tokens_used=results.get('tokens_used', 0),
                cost=results.get('cost', 0.0),
                metadata={
                    'bug_id': results.get('bug_id'),
                    'files_modified': results.get('files_modified', 0),
                    'test_pass_rate': results.get('test_pass_rate', 0.0),
                    'build_successful': results.get('build_successful', False),
                    'language': 'python'
                },
                raw_result=results
            )
        else:
            raise AdapterError(f"Cannot convert results of type {type(results)}")
    
    def validate_task_config(self, task_config: Dict[str, Any]) -> bool:
        """Validate task configuration for BugsInPy.
        
        Args:
            task_config: Task configuration to validate
            
        Returns:
            True if configuration is valid
        """
        # Basic validation
        if not isinstance(task_config, dict):
            raise ConfigurationError("Task configuration must be a dictionary")
        
        if 'bug_id' not in task_config:
            raise ConfigurationError("bug_id is required for BugsInPy tasks")
        
        return True
    
    def _load_bugs_data(self) -> None:
        """Load bug data from the dataset path."""
        dataset_path = Path(self.dataset_path)
        
        if dataset_path.is_file():
            if dataset_path.suffix == '.json':
                self._load_json_bugs(dataset_path)
            elif dataset_path.suffix == '.csv':
                self._load_csv_bugs(dataset_path)
            else:
                raise ConfigurationError(f"Unsupported file format: {dataset_path.suffix}")
        elif dataset_path.is_dir():
            # Look for bugs data files
            for file_path in dataset_path.glob('*.json'):
                self._load_json_bugs(file_path)
            for file_path in dataset_path.glob('*.csv'):
                self._load_csv_bugs(file_path)
        else:
            raise ConfigurationError(f"Invalid dataset path: {dataset_path}")
        
        if not self.bugs_data:
            raise ConfigurationError("No bug data found in dataset path")
    
    def _load_json_bugs(self, file_path: Path) -> None:
        """Load bug data from JSON file.
        
        Args:
            file_path: Path to the JSON file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                self.bugs_data.extend(data)
            else:
                self.bugs_data.append(data)
                
        except Exception as e:
            self.logger.warning(f"Failed to load JSON bugs file {file_path}: {e}")
    
    def _load_csv_bugs(self, file_path: Path) -> None:
        """Load bug data from CSV file.
        
        Args:
            file_path: Path to the CSV file
        """
        try:
            import csv
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.bugs_data.append(dict(row))
                    
        except Exception as e:
            self.logger.warning(f"Failed to load CSV bugs file {file_path}: {e}")


class Defects4JAdapter(BenchmarkAdapter):
    """Adapter for Defects4J benchmark - Java bug fixing tasks.
    
    Defects4J is a collection of reproducible bugs in Java projects
    for evaluating automated program repair techniques.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Defects4J adapter.
        
        Args:
            config: Configuration for the adapter
        """
        super().__init__(config)
        self.dataset_path = config.get('dataset_path', '')
        self.defects4j_home = config.get('defects4j_home', '')
        self.bugs_data: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
    
    def get_adapter_info(self) -> AdapterInfo:
        """Get information about this adapter.
        
        Returns:
            AdapterInfo describing the Defects4J adapter
        """
        return AdapterInfo(
            name="defects4j",
            version="1.0.0",
            description="Defects4J adapter for Java bug fixing evaluation",
            supported_task_types=[TaskType.MULTI_TURN],
            required_dependencies=["subprocess", "tempfile", "shutil", "java", "maven"],
            supported_formats=["json", "csv"],
            capabilities=[
                "java_bug_fixing",
                "maven_build",
                "junit_testing",
                "code_modification"
            ],
            metadata={
                "language": "java",
                "dataset_path": self.dataset_path,
                "defects4j_home": self.defects4j_home
            }
        )
    
    def initialize(self) -> bool:
        """Initialize the adapter and load bug data.
        
        Returns:
            True if initialization was successful
        """
        try:
            self._set_status(AdapterStatus.INITIALIZING)
            
            # Validate configuration
            if not self.dataset_path:
                raise ConfigurationError("dataset_path is required for Defects4J adapter")
            
            if not os.path.exists(self.dataset_path):
                raise ConfigurationError(f"Dataset path does not exist: {self.dataset_path}")
            
            # Check for Defects4J installation
            if self.defects4j_home and not os.path.exists(self.defects4j_home):
                self.logger.warning(f"Defects4J home not found: {self.defects4j_home}")
            
            # Load bug data
            self._load_bugs_data()
            
            self._set_status(AdapterStatus.READY)
            self.logger.info(f"Defects4J adapter initialized with {len(self.bugs_data)} bugs")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize Defects4J adapter: {e}"
            self._set_status(AdapterStatus.ERROR, error_msg)
            return False
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create a bug fixing environment for Java.
        
        Args:
            task_config: Configuration for the specific bug
            
        Returns:
            BugFixEnvironment instance configured for Java
        """
        if not self.is_ready():
            raise AdapterError("Adapter is not ready")
        
        self.validate_task_config(task_config)
        
        # Find bug data
        bug_id = task_config['bug_id']
        bug_data = next((bug for bug in self.bugs_data if bug['bug_id'] == bug_id), None)
        
        if not bug_data:
            raise ConfigurationError(f"Bug not found: {bug_id}")
        
        # Create environment configuration
        env_config = {
            'bug_id': bug_id,
            'project_path': bug_data['project_path'],
            'test_command': bug_data.get('test_command', 'mvn test'),
            'build_command': bug_data.get('build_command', 'mvn compile'),
            'language': 'java',
            'bug_description': bug_data.get('description', ''),
            'failing_tests': bug_data.get('failing_tests', []),
            'expected_fix': bug_data.get('expected_fix', {}),
            'max_steps': task_config.get('max_steps', 50)
        }
        
        return BugFixEnvironment(env_config)
    
    def load_tasks(self, task_filter: Optional[Dict[str, Any]] = None) -> List[BaseTask]:
        """Load available Java bug fixing tasks.
        
        Args:
            task_filter: Optional filter criteria
            
        Returns:
            List of available tasks
        """
        if not self.is_ready():
            raise AdapterError("Adapter is not ready")
        
        tasks = []
        for bug_data in self.bugs_data:
            # Apply filters if provided
            if task_filter:
                if 'project' in task_filter:
                    if bug_data.get('project') not in task_filter['project']:
                        continue
                
                if 'difficulty' in task_filter:
                    if bug_data.get('difficulty') not in task_filter['difficulty']:
                        continue
            
            task = BugFixTask(
                task_id=f"defects4j_{bug_data['bug_id']}",
                bug_data=bug_data,
                adapter=self
            )
            tasks.append(task)
        
        return tasks
    
    def convert_results(self, results: Any) -> StandardizedResult:
        """Convert bug fixing results to standardized format.
        
        Args:
            results: Raw results from bug fixing
            
        Returns:
            StandardizedResult object
        """
        if isinstance(results, dict):
            return StandardizedResult(
                task_id=results.get('task_id', 'unknown'),
                adapter_name=self.get_adapter_info().name,
                success=results.get('bug_fixed', False),
                score=1.0 if results.get('bug_fixed', False) else 0.0,
                execution_time=results.get('execution_time', 0.0),
                turns=results.get('steps_taken', 0),
                tokens_used=results.get('tokens_used', 0),
                cost=results.get('cost', 0.0),
                metadata={
                    'bug_id': results.get('bug_id'),
                    'files_modified': results.get('files_modified', 0),
                    'test_pass_rate': results.get('test_pass_rate', 0.0),
                    'build_successful': results.get('build_successful', False),
                    'language': 'java'
                },
                raw_result=results
            )
        else:
            raise AdapterError(f"Cannot convert results of type {type(results)}")
    
    def validate_task_config(self, task_config: Dict[str, Any]) -> bool:
        """Validate task configuration for Defects4J.
        
        Args:
            task_config: Task configuration to validate
            
        Returns:
            True if configuration is valid
        """
        # Basic validation
        if not isinstance(task_config, dict):
            raise ConfigurationError("Task configuration must be a dictionary")
        
        if 'bug_id' not in task_config:
            raise ConfigurationError("bug_id is required for Defects4J tasks")
        
        return True
    
    def _load_bugs_data(self) -> None:
        """Load bug data from the dataset path."""
        # Similar to BugsInPy but for Java projects
        dataset_path = Path(self.dataset_path)
        
        if dataset_path.is_file():
            if dataset_path.suffix == '.json':
                self._load_json_bugs(dataset_path)
            elif dataset_path.suffix == '.csv':
                self._load_csv_bugs(dataset_path)
            else:
                raise ConfigurationError(f"Unsupported file format: {dataset_path.suffix}")
        elif dataset_path.is_dir():
            for file_path in dataset_path.glob('*.json'):
                self._load_json_bugs(file_path)
            for file_path in dataset_path.glob('*.csv'):
                self._load_csv_bugs(file_path)
        else:
            raise ConfigurationError(f"Invalid dataset path: {dataset_path}")
        
        if not self.bugs_data:
            raise ConfigurationError("No bug data found in dataset path")
    
    def _load_json_bugs(self, file_path: Path) -> None:
        """Load bug data from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                self.bugs_data.extend(data)
            else:
                self.bugs_data.append(data)
                
        except Exception as e:
            self.logger.warning(f"Failed to load JSON bugs file {file_path}: {e}")
    
    def _load_csv_bugs(self, file_path: Path) -> None:
        """Load bug data from CSV file."""
        try:
            import csv
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.bugs_data.append(dict(row))
                    
        except Exception as e:
            self.logger.warning(f"Failed to load CSV bugs file {file_path}: {e}")


class BugFixTask(BaseTask):
    """Generic task implementation for bug fixing."""
    
    def __init__(self, task_id: str, bug_data: Dict[str, Any], adapter: BenchmarkAdapter):
        """Initialize the bug fix task.
        
        Args:
            task_id: Unique identifier for the task
            bug_data: Bug information and configuration
            adapter: Parent adapter instance
        """
        self.task_id = task_id
        self.bug_data = bug_data
        self.adapter = adapter
    
    def get_task_type(self) -> TaskType:
        """Get the task type.
        
        Returns:
            TaskType.MULTI_TURN
        """
        return TaskType.MULTI_TURN
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate task configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        return self.adapter.validate_task_config(config)
    
    def get_required_capabilities(self) -> List[str]:
        """Get required capabilities for this task.
        
        Returns:
            List of required capabilities
        """
        language = self.bug_data.get('language', 'unknown')
        return [
            f"{language}_programming",
            "bug_fixing",
            "test_execution",
            "code_modification",
            "multi_turn_interaction"
        ]
    
    def get_id(self) -> str:
        """Get task identifier.
        
        Returns:
            Task ID string
        """
        return self.task_id
    
    def get_description(self) -> str:
        """Get task description.
        
        Returns:
            Task description string
        """
        return self.bug_data.get('description', f"Fix bug {self.bug_data.get('bug_id', 'unknown')}")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get task metadata.
        
        Returns:
            Dictionary of task metadata
        """
        return {
            'bug_id': self.bug_data.get('bug_id'),
            'project': self.bug_data.get('project'),
            'language': self.bug_data.get('language'),
            'difficulty': self.bug_data.get('difficulty'),
            'failing_tests': self.bug_data.get('failing_tests', []),
            'expected_fix': self.bug_data.get('expected_fix', {})
        }


# Register adapters with the global registry
from .adapters import register_adapter_class

register_adapter_class("convcodebench", ConvCodeBenchAdapter)
register_adapter_class("bugsinpy", BugsInPyAdapter)
register_adapter_class("defects4j", Defects4JAdapter)