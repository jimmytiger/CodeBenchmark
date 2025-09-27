"""Single Turn Scenarios evaluation tasks for lm_eval.

This module provides a comprehensive evaluation framework that extends lm-eval
with advanced single-turn scenario evaluation capabilities, supporting multiple
programming languages, contextual configurations, and comprehensive metrics.

Task Registration:
- Individual scenario tasks: single_turn_scenarios_<scenario>
- Full suite evaluation: single_turn_scenarios_suite
- Metadata filtering support for difficulty, language, context_mode

Supported Scenarios:
- Basic: code_completion, bug_fix, code_translation, documentation_generation, function_generation
- Advanced: system_design, algorithm_implementation, api_design, database_design, performance_optimization  
- Comprehensive: full_stack_development, testing_strategy, security_implementation

Directory Structure:
Each scenario has its own subdirectory containing:
- __init__.py: Task module initialization
- config.yml: Task configuration following lm-eval conventions
- problems.jsonl: Dataset with problems for evaluation
- templates/: Prompt templates for different context modes (optional)
"""

# Import scenario-specific task modules for automatic discovery
# These imports ensure that the task subdirectories are discoverable by lm-eval
from . import code_completion
from . import bug_fix
from . import code_translation
from . import documentation_generation
from . import function_generation
from . import algorithm_implementation
from . import system_design
from . import api_design
from . import database_design
from . import performance_optimization
from . import full_stack_development
from . import testing_strategy
from . import security_implementation

# Task registration is handled automatically by lm-eval's TaskManager
# which discovers YAML files in subdirectories and registers them based on their 'task' field