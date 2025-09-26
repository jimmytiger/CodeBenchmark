"""
Extended Task Registration System for AI Evaluation Engine

This module extends lm-evaluation-harness task registry with advanced capabilities
for hierarchical task organization, multi-turn scenarios, and dynamic task discovery.
"""

from typing import Dict, List, Optional, Any, Type, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import yaml
import json
from pathlib import Path
import logging

from lm_eval.api.task import Task
from lm_eval.api.registry import register_task, get_task_dict
from lm_eval.api.instance import Instance

logger = logging.getLogger(__name__)


@dataclass
class TaskMetadata:
    """Enhanced metadata for evaluation tasks"""
    task_id: str
    name: str
    description: str
    category: str
    difficulty: str
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_time: Optional[int] = None  # in seconds
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"


@dataclass
class ScenarioConfig:
    """Configuration for multi-turn scenarios"""
    scenario_id: str
    scenario_type: str
    max_turns: int
    conversation_timeout: int
    enable_context_retention: bool
    turns: List[Dict[str, Any]] = field(default_factory=list)
    scenario_metrics: List[str] = field(default_factory=list)
    success_criteria: Dict[str, float] = field(default_factory=dict)


class AdvancedTask(Task):
    """Extended Task class for complex evaluation scenarios"""
    
    def __init__(self, config_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.metadata: Optional[TaskMetadata] = None
        self.scenario_config: Optional[ScenarioConfig] = None
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> None:
        """Load task configuration from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Load metadata
        if 'metadata' in config:
            self.metadata = TaskMetadata(**config['metadata'])
        
        # Load scenario config for multi-turn tasks
        if 'scenario_config' in config:
            self.scenario_config = ScenarioConfig(**config['scenario_config'])
    
    def get_metadata(self) -> Optional[TaskMetadata]:
        """Get task metadata"""
        return self.metadata
    
    def get_scenario_config(self) -> Optional[ScenarioConfig]:
        """Get scenario configuration for multi-turn tasks"""
        return self.scenario_config
    
    def is_multi_turn(self) -> bool:
        """Check if this is a multi-turn task"""
        return self.scenario_config is not None
    
    def validate_dependencies(self) -> bool:
        """Validate task dependencies are available"""
        if not self.metadata or not self.metadata.dependencies:
            return True
        
        available_tasks = set(get_task_dict().keys())
        missing_deps = set(self.metadata.dependencies) - available_tasks
        
        if missing_deps:
            logger.warning(f"Missing dependencies for {self.metadata.task_id}: {missing_deps}")
            return False
        
        return True


class MultiTurnTask(AdvancedTask):
    """Specialized task class for multi-turn conversations"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_turn: int = 0
    
    def process_turn(self, turn_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single turn in the conversation"""
        self.current_turn += 1
        
        # Add turn to conversation history
        self.conversation_history.append({
            'turn': self.current_turn,
            'data': turn_data,
            'timestamp': self._get_timestamp()
        })
        
        return self._execute_turn(turn_data)
    
    def _execute_turn(self, turn_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the logic for a single turn (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement _execute_turn")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def reset_conversation(self) -> None:
        """Reset conversation state"""
        self.conversation_history = []
        self.current_turn = 0
    
    def get_conversation_context(self) -> str:
        """Get formatted conversation context"""
        if not self.conversation_history:
            return ""
        
        context_parts = []
        for entry in self.conversation_history:
            turn_num = entry['turn']
            data = entry['data']
            context_parts.append(f"Turn {turn_num}: {data.get('input', '')}")
            if 'output' in data:
                context_parts.append(f"Response {turn_num}: {data['output']}")
        
        return "\n".join(context_parts)


class ExtendedTaskRegistry:
    """Enhanced task registry with hierarchical organization and advanced features"""
    
    def __init__(self):
        self.task_metadata: Dict[str, TaskMetadata] = {}
        self.task_hierarchy: Dict[str, List[str]] = {}
        self.scenario_configs: Dict[str, ScenarioConfig] = {}
        self._load_existing_tasks()
    
    def _load_existing_tasks(self) -> None:
        """Load metadata for existing lm-eval tasks"""
        existing_tasks = get_task_dict()
        logger.info(f"Found {len(existing_tasks)} existing lm-eval tasks")
        
        # Categorize existing tasks
        for task_name in existing_tasks.keys():
            category = self._infer_category(task_name)
            if category not in self.task_hierarchy:
                self.task_hierarchy[category] = []
            self.task_hierarchy[category].append(task_name)
    
    def _infer_category(self, task_name: str) -> str:
        """Infer task category from task name"""
        if 'single_turn_scenarios' in task_name:
            return 'single_turn_scenarios'
        elif 'multi_turn_scenarios' in task_name:
            return 'multi_turn_scenarios'
        elif 'python_coding' in task_name:
            return 'python_coding'
        elif 'multi_turn_coding' in task_name:
            return 'multi_turn_coding'
        else:
            return 'general'
    
    def register_advanced_task(
        self, 
        task_class: Type[AdvancedTask], 
        task_name: str,
        metadata: Optional[TaskMetadata] = None
    ) -> None:
        """Register an advanced task with metadata"""
        
        # Register with lm-eval registry
        register_task(task_name)(task_class)
        
        # Store metadata
        if metadata:
            self.task_metadata[task_name] = metadata
            
            # Update hierarchy
            category = metadata.category
            if category not in self.task_hierarchy:
                self.task_hierarchy[category] = []
            if task_name not in self.task_hierarchy[category]:
                self.task_hierarchy[category].append(task_name)
        
        logger.info(f"Registered advanced task: {task_name}")
    
    def register_multi_turn_task(
        self,
        task_class: Type[MultiTurnTask],
        task_name: str,
        scenario_config: ScenarioConfig,
        metadata: Optional[TaskMetadata] = None
    ) -> None:
        """Register a multi-turn task with scenario configuration"""
        
        # Register the task
        self.register_advanced_task(task_class, task_name, metadata)
        
        # Store scenario configuration
        self.scenario_configs[task_name] = scenario_config
        
        logger.info(f"Registered multi-turn task: {task_name}")
    
    def discover_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[str]:
        """Discover tasks based on filters"""
        all_tasks = list(get_task_dict().keys())
        
        if not filters:
            return all_tasks
        
        filtered_tasks = []
        
        for task_name in all_tasks:
            metadata = self.task_metadata.get(task_name)
            
            # Apply filters
            if self._matches_filters(task_name, metadata, filters):
                filtered_tasks.append(task_name)
        
        return filtered_tasks
    
    def _matches_filters(
        self, 
        task_name: str, 
        metadata: Optional[TaskMetadata], 
        filters: Dict[str, Any]
    ) -> bool:
        """Check if task matches the given filters"""
        
        # Category filter
        if 'category' in filters:
            if metadata and metadata.category != filters['category']:
                return False
            elif not metadata:
                # Infer category for tasks without metadata
                inferred_category = self._infer_category(task_name)
                if inferred_category != filters['category']:
                    return False
        
        # Difficulty filter
        if 'difficulty' in filters and metadata:
            if metadata.difficulty != filters['difficulty']:
                return False
        
        # Tags filter
        if 'tags' in filters and metadata:
            required_tags = set(filters['tags'])
            task_tags = set(metadata.tags)
            if not required_tags.issubset(task_tags):
                return False
        
        # Multi-turn filter
        if 'multi_turn' in filters:
            is_multi_turn = task_name in self.scenario_configs
            if filters['multi_turn'] != is_multi_turn:
                return False
        
        return True
    
    def get_task_hierarchy(self) -> Dict[str, List[str]]:
        """Get the task hierarchy"""
        return self.task_hierarchy.copy()
    
    def get_task_metadata(self, task_name: str) -> Optional[TaskMetadata]:
        """Get metadata for a specific task"""
        return self.task_metadata.get(task_name)
    
    def get_scenario_config(self, task_name: str) -> Optional[ScenarioConfig]:
        """Get scenario configuration for a multi-turn task"""
        return self.scenario_configs.get(task_name)
    
    def validate_task_dependencies(self, task_name: str) -> bool:
        """Validate dependencies for a specific task"""
        metadata = self.task_metadata.get(task_name)
        if not metadata or not metadata.dependencies:
            return True
        
        available_tasks = set(get_task_dict().keys())
        missing_deps = set(metadata.dependencies) - available_tasks
        
        if missing_deps:
            logger.error(f"Missing dependencies for {task_name}: {missing_deps}")
            return False
        
        return True
    
    def load_task_from_config(self, config_path: str) -> Optional[AdvancedTask]:
        """Load a task from configuration file"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.error(f"Config file not found: {config_path}")
                return None
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Determine task type
            task_type = config.get('task_type', 'single_turn')
            
            if task_type == 'multi_turn':
                task = MultiTurnTask(config_path=config_path)
            else:
                task = AdvancedTask(config_path=config_path)
            
            return task
            
        except Exception as e:
            logger.error(f"Error loading task from config {config_path}: {e}")
            return None
    
    def export_registry_info(self, output_path: str) -> None:
        """Export registry information to JSON file"""
        registry_info = {
            'task_hierarchy': self.task_hierarchy,
            'task_metadata': {
                name: {
                    'task_id': meta.task_id,
                    'name': meta.name,
                    'description': meta.description,
                    'category': meta.category,
                    'difficulty': meta.difficulty,
                    'tags': meta.tags,
                    'dependencies': meta.dependencies,
                    'version': meta.version
                }
                for name, meta in self.task_metadata.items()
            },
            'scenario_configs': {
                name: {
                    'scenario_id': config.scenario_id,
                    'scenario_type': config.scenario_type,
                    'max_turns': config.max_turns,
                    'conversation_timeout': config.conversation_timeout,
                    'enable_context_retention': config.enable_context_retention
                }
                for name, config in self.scenario_configs.items()
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(registry_info, f, indent=2)
        
        logger.info(f"Registry information exported to {output_path}")


# Global registry instance
extended_registry = ExtendedTaskRegistry()


def register_advanced_task(task_name: str, metadata: Optional[TaskMetadata] = None):
    """Decorator for registering advanced tasks"""
    def decorator(task_class: Type[AdvancedTask]):
        extended_registry.register_advanced_task(task_class, task_name, metadata)
        return task_class
    return decorator


def register_multi_turn_task(
    task_name: str, 
    scenario_config: ScenarioConfig,
    metadata: Optional[TaskMetadata] = None
):
    """Decorator for registering multi-turn tasks"""
    def decorator(task_class: Type[MultiTurnTask]):
        extended_registry.register_multi_turn_task(task_class, task_name, scenario_config, metadata)
        return task_class
    return decorator