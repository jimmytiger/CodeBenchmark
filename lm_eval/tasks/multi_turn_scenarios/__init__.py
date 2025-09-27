"""
Multi-Turn Scenarios Framework

This package provides a comprehensive framework for evaluating models across
different multi-turn scenarios with chat-template support and extended capabilities
for complex conversational evaluation patterns.

Supported Multi-Turn Scenarios:
- Code Review Process: Interactive code review and improvement
- Debugging Session: Problem diagnosis and resolution
- Design Iteration: Iterative design refinement
- Teaching Dialogue: Educational conversation patterns
- Quantitative Trading: Financial analysis and strategy development
- Collaborative Development: Team-based development scenarios
- Requirements Refinement: Requirement analysis and specification
- Architecture Discussion: System architecture design conversations
- Performance Tuning: Optimization and performance improvement

Directory Structure:
Each scenario has its own subdirectory containing:
- __init__.py: Task module initialization
- config.yml: Multi-turn task configuration
- scenarios.jsonl: Dataset with multi-turn conversation scenarios
- turn_configs.yml: Turn-specific configuration and templates
"""

# Import existing framework components
from .base_scenario import MultiTurnScenario, TurnConfig, ScenarioConfig
from .scenario_registry import register_scenario, get_scenario, get_scenario_registry
from .chat_template_support import ChatTemplateManager
from .evaluation_engine import MultiTurnEvaluationEngine
from .base_scenario import ScenarioType

# Import new scenario modules for automatic discovery
from . import code_review_process
from . import debugging_session
from . import design_iteration
from . import teaching_dialogue
from . import quantitative_trading
from . import collaborative_development
from . import requirements_refinement
from . import architecture_discussion
from . import performance_tuning

# Import specific task classes for registration
from .design_iteration.design_iteration import DesignIterationTask
from .architecture_discussion.architecture_discussion import ArchitectureDiscussionTask
from .collaborative_development.collaborative_development import CollaborativeDevelopmentTask
from .requirements_refinement.requirements_refinement import RequirementsRefinementTask
from .performance_tuning.performance_tuning import PerformanceTuningTask
from .quantitative_trading.strategy_development.strategy_development import QuantitativeStrategyDevelopmentTask

__all__ = [
    'MultiTurnScenario',
    'TurnConfig', 
    'ScenarioConfig',
    'ScenarioType',
    'register_scenario',
    'get_scenario',
    'get_scenario_registry',
    'ChatTemplateManager',
    'MultiTurnEvaluationEngine'
]