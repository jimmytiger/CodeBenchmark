"""
Dataset Format Definitions for AI Evaluation Engine

This module defines the standard dataset formats for single-turn and multi-turn
evaluation scenarios, ensuring compatibility with lm-eval while extending
capabilities for advanced evaluation patterns.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class DatasetFormat(Enum):
    """Supported dataset formats."""
    JSONL = "jsonl"
    CSV = "csv"
    PARQUET = "parquet"


@dataclass
class TestCase:
    """Represents a test case for code evaluation."""
    input: Any
    expected: Any
    description: Optional[str] = None
    weight: float = 1.0
    timeout: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'input': self.input,
            'expected': self.expected,
            'description': self.description,
            'weight': self.weight,
            'timeout': self.timeout
        }


@dataclass
class SingleTurnProblem:
    """
    Standard format for single-turn evaluation problems.
    
    This format is used in problems.jsonl files for single-turn scenarios.
    """
    id: str
    scenario: str
    difficulty: str
    language: str
    context_mode: str
    problem: str
    expected_output: Optional[str] = None
    test_cases: List[TestCase] = field(default_factory=list)
    
    # Scenario-specific fields
    code_template: Optional[str] = None  # For code completion
    buggy_code: Optional[str] = None     # For bug fixing
    bug_description: Optional[str] = None
    security_issue: bool = False
    
    # Domain-specific fields
    domain: Optional[str] = None
    domain_knowledge: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSONL serialization."""
        result = {
            'id': self.id,
            'scenario': self.scenario,
            'difficulty': self.difficulty,
            'language': self.language,
            'context_mode': self.context_mode,
            'problem': self.problem,
            'expected_output': self.expected_output,
            'test_cases': [tc.to_dict() if isinstance(tc, TestCase) else tc for tc in self.test_cases]
        }
        
        # Add optional fields if present
        optional_fields = [
            'code_template', 'buggy_code', 'bug_description', 'domain',
            'domain_knowledge', 'constraints', 'metadata'
        ]
        
        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None and value != {} and value != []:
                result[field_name] = value
        
        if self.security_issue:
            result['security_issue'] = True
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SingleTurnProblem':
        """Create from dictionary format."""
        # Convert test_cases to TestCase objects if they're dictionaries
        test_cases = []
        for tc in data.get('test_cases', []):
            if isinstance(tc, dict):
                test_cases.append(TestCase(**tc))
            else:
                test_cases.append(tc)
        
        return cls(
            id=data['id'],
            scenario=data['scenario'],
            difficulty=data['difficulty'],
            language=data['language'],
            context_mode=data['context_mode'],
            problem=data['problem'],
            expected_output=data.get('expected_output'),
            test_cases=test_cases,
            code_template=data.get('code_template'),
            buggy_code=data.get('buggy_code'),
            bug_description=data.get('bug_description'),
            security_issue=data.get('security_issue', False),
            domain=data.get('domain'),
            domain_knowledge=data.get('domain_knowledge', {}),
            constraints=data.get('constraints', {}),
            metadata=data.get('metadata', {})
        )


@dataclass
class TurnData:
    """Represents data for a single turn in a multi-turn scenario."""
    turn_id: str
    turn_type: str
    role: str
    prompt_data: Dict[str, Any] = field(default_factory=dict)
    expected_response_format: Optional[str] = None
    validation_criteria: List[str] = field(default_factory=list)
    success_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'turn_id': self.turn_id,
            'turn_type': self.turn_type,
            'role': self.role,
            'prompt_data': self.prompt_data,
            'expected_response_format': self.expected_response_format,
            'validation_criteria': self.validation_criteria,
            'success_metrics': self.success_metrics
        }


@dataclass
class MultiTurnScenario:
    """
    Standard format for multi-turn evaluation scenarios.
    
    This format is used in scenarios.jsonl files for multi-turn scenarios.
    """
    id: str
    scenario: str
    difficulty: str
    language: Optional[str] = None
    context_mode: str = "full_context"
    
    # Scenario description and setup
    description: str = ""
    initial_context: Dict[str, Any] = field(default_factory=dict)
    
    # Turn configuration
    turns: List[TurnData] = field(default_factory=list)
    max_turns: int = 5
    conversation_timeout: int = 300
    
    # Success criteria
    success_metrics: Dict[str, float] = field(default_factory=dict)
    completion_criteria: List[str] = field(default_factory=list)
    
    # Domain-specific fields
    domain: Optional[str] = None
    domain_knowledge: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    # Scenario-specific data
    scenario_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSONL serialization."""
        return {
            'id': self.id,
            'scenario': self.scenario,
            'difficulty': self.difficulty,
            'language': self.language,
            'context_mode': self.context_mode,
            'description': self.description,
            'initial_context': self.initial_context,
            'turns': [turn.to_dict() if isinstance(turn, TurnData) else turn for turn in self.turns],
            'max_turns': self.max_turns,
            'conversation_timeout': self.conversation_timeout,
            'success_metrics': self.success_metrics,
            'completion_criteria': self.completion_criteria,
            'domain': self.domain,
            'domain_knowledge': self.domain_knowledge,
            'constraints': self.constraints,
            'scenario_data': self.scenario_data,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MultiTurnScenario':
        """Create from dictionary format."""
        # Convert turns to TurnData objects if they're dictionaries
        turns = []
        for turn in data.get('turns', []):
            if isinstance(turn, dict):
                turns.append(TurnData(**turn))
            else:
                turns.append(turn)
        
        return cls(
            id=data['id'],
            scenario=data['scenario'],
            difficulty=data['difficulty'],
            language=data.get('language'),
            context_mode=data.get('context_mode', 'full_context'),
            description=data.get('description', ''),
            initial_context=data.get('initial_context', {}),
            turns=turns,
            max_turns=data.get('max_turns', 5),
            conversation_timeout=data.get('conversation_timeout', 300),
            success_metrics=data.get('success_metrics', {}),
            completion_criteria=data.get('completion_criteria', []),
            domain=data.get('domain'),
            domain_knowledge=data.get('domain_knowledge', {}),
            constraints=data.get('constraints', {}),
            scenario_data=data.get('scenario_data', {}),
            metadata=data.get('metadata', {})
        )


class DatasetLoader:
    """Utility class for loading and validating datasets."""
    
    @staticmethod
    def load_single_turn_problems(file_path: str) -> List[SingleTurnProblem]:
        """Load single-turn problems from JSONL file."""
        problems = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    problem = SingleTurnProblem.from_dict(data)
                    problems.append(problem)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON on line {line_num}: {e}")
                except Exception as e:
                    raise ValueError(f"Error processing line {line_num}: {e}")
        
        return problems
    
    @staticmethod
    def load_multi_turn_scenarios(file_path: str) -> List[MultiTurnScenario]:
        """Load multi-turn scenarios from JSONL file."""
        scenarios = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    scenario = MultiTurnScenario.from_dict(data)
                    scenarios.append(scenario)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON on line {line_num}: {e}")
                except Exception as e:
                    raise ValueError(f"Error processing line {line_num}: {e}")
        
        return scenarios
    
    @staticmethod
    def save_single_turn_problems(problems: List[SingleTurnProblem], file_path: str) -> None:
        """Save single-turn problems to JSONL file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            for problem in problems:
                json.dump(problem.to_dict(), f, ensure_ascii=False)
                f.write('\n')
    
    @staticmethod
    def save_multi_turn_scenarios(scenarios: List[MultiTurnScenario], file_path: str) -> None:
        """Save multi-turn scenarios to JSONL file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            for scenario in scenarios:
                json.dump(scenario.to_dict(), f, ensure_ascii=False)
                f.write('\n')
    
    @staticmethod
    def validate_single_turn_dataset(file_path: str) -> Dict[str, Any]:
        """Validate single-turn dataset and return validation report."""
        try:
            problems = DatasetLoader.load_single_turn_problems(file_path)
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'problems_count': 0
            }
        
        # Validation checks
        scenarios = set()
        difficulties = set()
        languages = set()
        context_modes = set()
        
        validation_issues = []
        
        for i, problem in enumerate(problems):
            # Collect statistics
            scenarios.add(problem.scenario)
            difficulties.add(problem.difficulty)
            languages.add(problem.language)
            context_modes.add(problem.context_mode)
            
            # Validate required fields
            if not problem.id:
                validation_issues.append(f"Problem {i}: Missing ID")
            if not problem.problem:
                validation_issues.append(f"Problem {i}: Missing problem description")
            
            # Validate test cases
            if not problem.test_cases and problem.scenario in ['code_completion', 'bug_fix', 'function_generation']:
                validation_issues.append(f"Problem {i}: Missing test cases for code scenario")
        
        return {
            'valid': len(validation_issues) == 0,
            'issues': validation_issues,
            'problems_count': len(problems),
            'scenarios': list(scenarios),
            'difficulties': list(difficulties),
            'languages': list(languages),
            'context_modes': list(context_modes)
        }
    
    @staticmethod
    def validate_multi_turn_dataset(file_path: str) -> Dict[str, Any]:
        """Validate multi-turn dataset and return validation report."""
        try:
            scenarios = DatasetLoader.load_multi_turn_scenarios(file_path)
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'scenarios_count': 0
            }
        
        # Validation checks
        scenario_types = set()
        difficulties = set()
        domains = set()
        
        validation_issues = []
        
        for i, scenario in enumerate(scenarios):
            # Collect statistics
            scenario_types.add(scenario.scenario)
            difficulties.add(scenario.difficulty)
            if scenario.domain:
                domains.add(scenario.domain)
            
            # Validate required fields
            if not scenario.id:
                validation_issues.append(f"Scenario {i}: Missing ID")
            if not scenario.turns:
                validation_issues.append(f"Scenario {i}: No turns defined")
            
            # Validate turns
            turn_ids = set()
            for j, turn in enumerate(scenario.turns):
                if not turn.turn_id:
                    validation_issues.append(f"Scenario {i}, Turn {j}: Missing turn_id")
                elif turn.turn_id in turn_ids:
                    validation_issues.append(f"Scenario {i}, Turn {j}: Duplicate turn_id '{turn.turn_id}'")
                else:
                    turn_ids.add(turn.turn_id)
        
        return {
            'valid': len(validation_issues) == 0,
            'issues': validation_issues,
            'scenarios_count': len(scenarios),
            'scenario_types': list(scenario_types),
            'difficulties': list(difficulties),
            'domains': list(domains)
        }


# Example usage and format documentation
SINGLE_TURN_EXAMPLE = {
    "id": "code_completion_001",
    "scenario": "code_completion",
    "difficulty": "simple",
    "language": "python",
    "context_mode": "minimal_context",
    "problem": "Complete the following function that calculates the factorial of a number:",
    "code_template": "def factorial(n):\n    # TODO: Implement factorial calculation\n    pass",
    "expected_output": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
    "test_cases": [
        {"input": 5, "expected": 120},
        {"input": 0, "expected": 1},
        {"input": 3, "expected": 6}
    ]
}

MULTI_TURN_EXAMPLE = {
    "id": "code_review_001",
    "scenario": "code_review_process",
    "difficulty": "intermediate",
    "language": "python",
    "context_mode": "full_context",
    "description": "Interactive code review process for a function with security issues",
    "initial_context": {
        "code": "def process_user_input(user_input):\n    result = eval(user_input)\n    return result * 2",
        "review_criteria": ["security", "input_validation", "error_handling"]
    },
    "turns": [
        {
            "turn_id": "initial_review",
            "turn_type": "review",
            "role": "reviewer",
            "expected_response_format": "structured_feedback",
            "validation_criteria": ["identifies_security_issues", "provides_recommendations"]
        },
        {
            "turn_id": "code_revision",
            "turn_type": "implementation",
            "role": "developer",
            "expected_response_format": "code_with_explanation",
            "validation_criteria": ["fixes_security_issues", "maintains_functionality"]
        }
    ],
    "max_turns": 3,
    "success_metrics": {
        "review_thoroughness": 0.8,
        "improvement_quality": 0.7,
        "standards_compliance": 0.9
    }
}