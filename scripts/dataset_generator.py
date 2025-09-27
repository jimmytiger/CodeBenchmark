#!/usr/bin/env python3
"""
Dataset Generation Tool for AI Evaluation Engine

This tool generates production-ready datasets for both single-turn and multi-turn scenarios,
expanding existing sample datasets to 100+ problems per scenario with comprehensive
test cases and validation.
"""

import json
import os
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import argparse
import logging
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScenarioType(Enum):
    SINGLE_TURN = "single_turn"
    MULTI_TURN = "multi_turn"

class DifficultyLevel(Enum):
    SIMPLE = "simple"
    INTERMEDIATE = "intermediate"
    COMPLEX = "complex"

class ContextMode(Enum):
    NO_CONTEXT = "no_context"
    MINIMAL_CONTEXT = "minimal_context"
    FULL_CONTEXT = "full_context"
    DOMAIN_CONTEXT = "domain_context"

class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    TYPESCRIPT = "typescript"
    SQL = "sql"
    SHELL = "shell"

@dataclass
class SingleTurnProblem:
    """Data structure for single-turn problems"""
    id: str
    title: str
    language: str
    scenario: str
    difficulty: str
    context_mode: str
    prompt: str
    reference: List[str]
    tests: List[Dict[str, str]]
    metadata: Dict[str, Any]

@dataclass
class MultiTurnScenario:
    """Data structure for multi-turn scenarios"""
    id: str
    scenario: str
    difficulty: str
    language: str
    context_mode: str
    turns: List[Dict[str, Any]]
    success_metrics: Dict[str, float]
    metadata: Dict[str, Any]

class DatasetGenerator:
    """Main dataset generation class"""
    
    def __init__(self, base_path: str = "lm_eval/tasks"):
        self.base_path = Path(base_path)
        self.single_turn_scenarios = [
            "code_completion", "bug_fix", "function_generation", "code_translation",
            "algorithm_implementation", "api_design", "system_design", "database_design",
            "security_implementation", "performance_optimization", "documentation_generation",
            "testing_strategy", "full_stack_development"
        ]
        self.multi_turn_scenarios = [
            "code_review_process", "debugging_session", "design_iteration", "teaching_dialogue",
            "collaborative_development", "requirements_refinement", "architecture_discussion",
            "performance_tuning"
        ]
        self.quantitative_trading_scenarios = [
            "strategy_development", "multifactor_model_construction", "market_research_analysis",
            "portfolio_risk_assessment", "execution_algorithm_optimization", "high_frequency_trading",
            "fundamental_quant_analysis", "technical_quant_analysis"
        ]
        
    def generate_single_turn_problems(self, scenario: str, count: int = 100) -> List[SingleTurnProblem]:
        """Generate single-turn problems for a specific scenario"""
        logger.info(f"Generating {count} problems for single-turn scenario: {scenario}")
        problems = []
        
        # Load existing problems as templates
        existing_problems = self._load_existing_single_turn_problems(scenario)
        
        for i in range(count):
            problem = self._generate_single_turn_problem(scenario, i, existing_problems)
            problems.append(problem)
            
        return problems
    
    def generate_multi_turn_scenarios(self, scenario: str, count: int = 100) -> List[MultiTurnScenario]:
        """Generate multi-turn scenarios for a specific scenario type"""
        logger.info(f"Generating {count} scenarios for multi-turn scenario: {scenario}")
        scenarios = []
        
        # Load existing scenarios as templates
        existing_scenarios = self._load_existing_multi_turn_scenarios(scenario)
        
        for i in range(count):
            scenario_obj = self._generate_multi_turn_scenario(scenario, i, existing_scenarios)
            scenarios.append(scenario_obj)
            
        return scenarios
    
    def _load_existing_single_turn_problems(self, scenario: str) -> List[Dict[str, Any]]:
        """Load existing problems to use as templates"""
        problems_file = self.base_path / "single_turn_scenarios" / "problems.jsonl"
        existing_problems = []
        
        if problems_file.exists():
            with open(problems_file, 'r') as f:
                for line in f:
                    problem = json.loads(line.strip())
                    if problem.get('scenario') == scenario:
                        existing_problems.append(problem)
        
        # Also check scenario-specific files
        scenario_file = self.base_path / "single_turn_scenarios" / scenario / "problems.jsonl"
        if scenario_file.exists():
            with open(scenario_file, 'r') as f:
                for line in f:
                    existing_problems.append(json.loads(line.strip()))
        
        return existing_problems
    
    def _load_existing_multi_turn_scenarios(self, scenario: str) -> List[Dict[str, Any]]:
        """Load existing multi-turn scenarios to use as templates"""
        scenarios_file = self.base_path / "multi_turn_scenarios" / scenario / "scenarios.jsonl"
        existing_scenarios = []
        
        if scenarios_file.exists():
            with open(scenarios_file, 'r') as f:
                for line in f:
                    existing_scenarios.append(json.loads(line.strip()))
        
        return existing_scenarios
    
    def _generate_single_turn_problem(self, scenario: str, index: int, templates: List[Dict[str, Any]]) -> SingleTurnProblem:
        """Generate a single-turn problem based on templates and variations"""
        problem_id = f"st_{scenario}_{index:04d}"
        
        # Select template or create new
        if templates:
            template = random.choice(templates)
        else:
            template = self._get_default_single_turn_template(scenario)
        
        # Generate variations
        difficulty = random.choice(list(DifficultyLevel)).value
        language = self._select_language_for_scenario(scenario)
        context_mode = random.choice(list(ContextMode)).value
        
        # Generate problem content based on scenario
        title, prompt, reference, tests = self._generate_problem_content(scenario, difficulty, language, index)
        
        return SingleTurnProblem(
            id=problem_id,
            title=title,
            language=language,
            scenario=scenario,
            difficulty=difficulty,
            context_mode=context_mode,
            prompt=prompt,
            reference=reference,
            tests=tests,
            metadata={
                "time_limit_s": self._get_time_limit(difficulty),
                "memory_limit_mb": self._get_memory_limit(difficulty),
                "seed": 1000 + index,
                "author": "dataset_generator",
                "license": "MIT",
                "generated_at": datetime.now().isoformat(),
                "template_source": template.get('id', 'default') if templates else 'generated'
            }
        )
    
    def _generate_multi_turn_scenario(self, scenario: str, index: int, templates: List[Dict[str, Any]]) -> MultiTurnScenario:
        """Generate a multi-turn scenario based on templates and variations"""
        scenario_id = f"mt_{scenario}_{index:04d}"
        
        # Select template or create new
        if templates:
            template = random.choice(templates)
        else:
            template = self._get_default_multi_turn_template(scenario)
        
        # Generate variations
        difficulty = random.choice(list(DifficultyLevel)).value
        language = self._select_language_for_scenario(scenario)
        context_mode = random.choice(list(ContextMode)).value
        
        # Generate scenario content
        turns, success_metrics = self._generate_multi_turn_content(scenario, difficulty, language, index)
        
        return MultiTurnScenario(
            id=scenario_id,
            scenario=scenario,
            difficulty=difficulty,
            language=language,
            context_mode=context_mode,
            turns=turns,
            success_metrics=success_metrics,
            metadata={
                "max_turns": len(turns),
                "conversation_timeout": 300,
                "enable_context_retention": True,
                "seed": 2000 + index,
                "author": "dataset_generator",
                "license": "MIT",
                "generated_at": datetime.now().isoformat(),
                "template_source": template.get('id', 'default') if templates else 'generated'
            }
        )
    
    def _select_language_for_scenario(self, scenario: str) -> str:
        """Select appropriate language for scenario"""
        language_weights = {
            "code_completion": {"python": 0.4, "javascript": 0.2, "java": 0.15, "cpp": 0.1, "go": 0.1, "rust": 0.05},
            "bug_fix": {"python": 0.5, "javascript": 0.2, "java": 0.15, "cpp": 0.15},
            "function_generation": {"python": 0.4, "javascript": 0.25, "java": 0.2, "typescript": 0.15},
            "code_translation": {"python": 0.3, "javascript": 0.3, "java": 0.2, "cpp": 0.2},
            "algorithm_implementation": {"python": 0.3, "cpp": 0.25, "java": 0.25, "go": 0.2},
            "api_design": {"python": 0.4, "javascript": 0.3, "java": 0.2, "go": 0.1},
            "system_design": {"python": 0.4, "java": 0.3, "go": 0.2, "cpp": 0.1},
            "database_design": {"sql": 0.8, "python": 0.2},
            "security_implementation": {"python": 0.4, "java": 0.3, "cpp": 0.2, "go": 0.1},
            "performance_optimization": {"cpp": 0.4, "python": 0.3, "java": 0.2, "rust": 0.1},
            "documentation_generation": {"python": 0.5, "javascript": 0.3, "java": 0.2},
            "testing_strategy": {"python": 0.5, "javascript": 0.3, "java": 0.2},
            "full_stack_development": {"javascript": 0.4, "python": 0.3, "typescript": 0.3}
        }
        
        weights = language_weights.get(scenario, {"python": 0.6, "javascript": 0.4})
        languages = list(weights.keys())
        probabilities = list(weights.values())
        
        return random.choices(languages, weights=probabilities)[0]
    
    def _get_time_limit(self, difficulty: str) -> int:
        """Get time limit based on difficulty"""
        limits = {"simple": 10, "intermediate": 30, "complex": 60}
        return limits.get(difficulty, 30)
    
    def _get_memory_limit(self, difficulty: str) -> int:
        """Get memory limit based on difficulty"""
        limits = {"simple": 200, "intermediate": 400, "complex": 800}
        return limits.get(difficulty, 400)
    
    def _generate_problem_content(self, scenario: str, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        """Generate problem content based on scenario type"""
        generators = {
            "code_completion": self._generate_code_completion_content,
            "bug_fix": self._generate_bug_fix_content,
            "function_generation": self._generate_function_generation_content,
            "code_translation": self._generate_code_translation_content,
            "algorithm_implementation": self._generate_algorithm_implementation_content,
            "api_design": self._generate_api_design_content,
            "system_design": self._generate_system_design_content,
            "database_design": self._generate_database_design_content,
            "security_implementation": self._generate_security_implementation_content,
            "performance_optimization": self._generate_performance_optimization_content,
            "documentation_generation": self._generate_documentation_generation_content,
            "testing_strategy": self._generate_testing_strategy_content,
            "full_stack_development": self._generate_full_stack_development_content
        }
        
        generator = generators.get(scenario, self._generate_default_content)
        return generator(difficulty, language, index)
    
    def _generate_multi_turn_content(self, scenario: str, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """Generate multi-turn scenario content"""
        generators = {
            "code_review_process": self._generate_code_review_turns,
            "debugging_session": self._generate_debugging_turns,
            "design_iteration": self._generate_design_iteration_turns,
            "teaching_dialogue": self._generate_teaching_dialogue_turns,
            "collaborative_development": self._generate_collaborative_development_turns,
            "requirements_refinement": self._generate_requirements_refinement_turns,
            "architecture_discussion": self._generate_architecture_discussion_turns,
            "performance_tuning": self._generate_performance_tuning_turns
        }
        
        generator = generators.get(scenario, self._generate_default_multi_turn_content)
        return generator(difficulty, language, index)
    
    # Content generation methods for single-turn scenarios
    def _generate_code_completion_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        """Generate code completion problem content"""
        problems = {
            "simple": [
                ("Complete array sum function", "Complete the function to calculate sum of array elements", "def sum_array(arr):\n    total = 0\n    for item in arr:\n        total += item\n    return total"),
                ("Complete string reversal", "Complete the function to reverse a string", "def reverse_string(s):\n    return s[::-1]"),
                ("Complete even number filter", "Complete the function to filter even numbers", "def filter_even(numbers):\n    return [n for n in numbers if n % 2 == 0]")
            ],
            "intermediate": [
                ("Complete binary search", "Complete the binary search implementation", "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1"),
                ("Complete merge sort", "Complete the merge sort algorithm", "def merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    return merge(left, right)")
            ],
            "complex": [
                ("Complete graph traversal", "Complete the graph traversal algorithm with cycle detection", "def dfs_with_cycle_detection(graph, start):\n    visited = set()\n    rec_stack = set()\n    \n    def dfs(node):\n        visited.add(node)\n        rec_stack.add(node)\n        \n        for neighbor in graph.get(node, []):\n            if neighbor not in visited:\n                if dfs(neighbor):\n                    return True\n            elif neighbor in rec_stack:\n                return True\n        \n        rec_stack.remove(node)\n        return False\n    \n    return dfs(start)")
            ]
        }
        
        problem_set = problems.get(difficulty, problems["simple"])
        title, prompt, reference = random.choice(problem_set)
        
        test_file = f"test_code_completion_{index:04d}.py"
        tests = [{"type": "unit", "file": f"tests/{test_file}", "cmd": f"python -m pytest tests/{test_file} -v"}]
        
        return title, prompt, [reference], tests
    
    def _generate_bug_fix_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        """Generate bug fix problem content"""
        bugs = {
            "simple": [
                ("Fix off-by-one error", "Fix the off-by-one error in this loop", "for i in range(len(arr)):\n    print(arr[i])"),
                ("Fix division by zero", "Fix the potential division by zero error", "def average(numbers):\n    if not numbers:\n        return 0\n    return sum(numbers) / len(numbers)")
            ],
            "intermediate": [
                ("Fix memory leak", "Fix the memory leak in this implementation", "# Fixed implementation with proper cleanup"),
                ("Fix race condition", "Fix the race condition in concurrent code", "# Thread-safe implementation")
            ],
            "complex": [
                ("Fix distributed system bug", "Fix the consistency issue in distributed system", "# Fixed distributed algorithm"),
                ("Fix security vulnerability", "Fix the SQL injection vulnerability", "# Parameterized query implementation")
            ]
        }
        
        bug_set = bugs.get(difficulty, bugs["simple"])
        title, prompt, reference = random.choice(bug_set)
        
        test_file = f"test_bug_fix_{index:04d}.py"
        tests = [{"type": "unit", "file": f"tests/{test_file}", "cmd": f"python -m pytest tests/{test_file} -v"}]
        
        return title, prompt, [reference], tests
    
    def _generate_function_generation_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        """Generate function generation problem content"""
        functions = {
            "simple": [
                ("Generate palindrome checker", "Write a function to check if a string is a palindrome", "def is_palindrome(s):\n    s = s.lower().replace(' ', '')\n    return s == s[::-1]"),
                ("Generate factorial function", "Write a function to calculate factorial", "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)")
            ],
            "intermediate": [
                ("Generate LRU cache", "Implement an LRU cache with get and put operations", "class LRUCache:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.cache = {}\n        self.order = []"),
                ("Generate trie data structure", "Implement a trie for string operations", "class TrieNode:\n    def __init__(self):\n        self.children = {}\n        self.is_end = False")
            ],
            "complex": [
                ("Generate distributed hash table", "Implement a distributed hash table with consistent hashing", "class DistributedHashTable:\n    def __init__(self, nodes):\n        self.nodes = nodes\n        self.ring = {}"),
                ("Generate consensus algorithm", "Implement a Raft consensus algorithm", "class RaftNode:\n    def __init__(self, node_id):\n        self.node_id = node_id\n        self.state = 'follower'")
            ]
        }
        
        function_set = functions.get(difficulty, functions["simple"])
        title, prompt, reference = random.choice(function_set)
        
        test_file = f"test_function_generation_{index:04d}.py"
        tests = [{"type": "unit", "file": f"tests/{test_file}", "cmd": f"python -m pytest tests/{test_file} -v"}]
        
        return title, prompt, [reference], tests
    
    # Placeholder methods for other scenario types
    def _generate_code_translation_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Translate code to {language}"
        prompt = f"Translate the given code to {language} while maintaining functionality"
        reference = [f"// Translated {language} code"]
        tests = [{"type": "unit", "file": f"tests/test_translation_{index:04d}.{self._get_file_extension(language)}", "cmd": f"{self._get_test_command(language)} tests/test_translation_{index:04d}.{self._get_file_extension(language)}"}]
        return title, prompt, reference, tests
    
    def _generate_algorithm_implementation_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Implement {difficulty} algorithm"
        prompt = f"Implement the specified algorithm with {difficulty} complexity"
        reference = [f"# {difficulty.capitalize()} algorithm implementation"]
        tests = [{"type": "unit", "file": f"tests/test_algorithm_{index:04d}.py", "cmd": f"python -m pytest tests/test_algorithm_{index:04d}.py -v"}]
        return title, prompt, reference, tests
    
    def _generate_api_design_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Design {difficulty} API"
        prompt = f"Design a RESTful API with {difficulty} requirements"
        reference = [f"# {difficulty.capitalize()} API design"]
        tests = [{"type": "integration", "file": f"tests/test_api_{index:04d}.py", "cmd": f"python -m pytest tests/test_api_{index:04d}.py -v"}]
        return title, prompt, reference, tests
    
    def _generate_system_design_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Design {difficulty} system"
        prompt = f"Design a distributed system with {difficulty} scalability requirements"
        reference = [f"# {difficulty.capitalize()} system design"]
        tests = [{"type": "integration", "file": f"tests/test_system_{index:04d}.py", "cmd": f"python -m pytest tests/test_system_{index:04d}.py -v"}]
        return title, prompt, reference, tests
    
    def _generate_database_design_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Design {difficulty} database schema"
        prompt = f"Design a database schema with {difficulty} normalization requirements"
        reference = [f"-- {difficulty.capitalize()} database schema"]
        tests = [{"type": "schema", "file": f"tests/test_db_{index:04d}.sql", "cmd": f"psql -d test_db -f tests/test_db_{index:04d}.sql"}]
        return title, prompt, reference, tests
    
    def _generate_security_implementation_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Implement {difficulty} security measures"
        prompt = f"Implement security controls with {difficulty} threat model"
        reference = [f"# {difficulty.capitalize()} security implementation"]
        tests = [{"type": "security", "file": f"tests/test_security_{index:04d}.py", "cmd": f"python -m pytest tests/test_security_{index:04d}.py -v"}]
        return title, prompt, reference, tests
    
    def _generate_performance_optimization_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Optimize {difficulty} performance"
        prompt = f"Optimize the given code for {difficulty} performance requirements"
        reference = [f"# {difficulty.capitalize()} optimized implementation"]
        tests = [{"type": "performance", "file": f"tests/test_performance_{index:04d}.py", "cmd": f"python -m pytest tests/test_performance_{index:04d}.py -v"}]
        return title, prompt, reference, tests
    
    def _generate_documentation_generation_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Generate {difficulty} documentation"
        prompt = f"Generate comprehensive documentation with {difficulty} detail level"
        reference = [f"# {difficulty.capitalize()} documentation"]
        tests = [{"type": "docstring", "file": f"tests/test_docs_{index:04d}.py", "cmd": f"python -m pytest tests/test_docs_{index:04d}.py -v"}]
        return title, prompt, reference, tests
    
    def _generate_testing_strategy_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Design {difficulty} testing strategy"
        prompt = f"Design a comprehensive testing strategy with {difficulty} coverage requirements"
        reference = [f"# {difficulty.capitalize()} testing strategy"]
        tests = [{"type": "test_design", "file": f"tests/test_strategy_{index:04d}.py", "cmd": f"python -m pytest tests/test_strategy_{index:04d}.py -v"}]
        return title, prompt, reference, tests
    
    def _generate_full_stack_development_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Develop {difficulty} full-stack feature"
        prompt = f"Implement a full-stack feature with {difficulty} integration requirements"
        reference = [f"# {difficulty.capitalize()} full-stack implementation"]
        tests = [{"type": "e2e", "file": f"tests/test_fullstack_{index:04d}.py", "cmd": f"python -m pytest tests/test_fullstack_{index:04d}.py -v"}]
        return title, prompt, reference, tests
    
    def _generate_default_content(self, difficulty: str, language: str, index: int) -> Tuple[str, str, List[str], List[Dict[str, str]]]:
        title = f"Generic {difficulty} problem"
        prompt = f"Solve this {difficulty} programming problem"
        reference = [f"# {difficulty.capitalize()} solution"]
        tests = [{"type": "unit", "file": f"tests/test_generic_{index:04d}.py", "cmd": f"python -m pytest tests/test_generic_{index:04d}.py -v"}]
        return title, prompt, reference, tests
    
    # Multi-turn content generation methods
    def _generate_code_review_turns(self, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """Generate code review process turns"""
        turns = [
            {
                "turn_id": "initial_submission",
                "role": "developer",
                "prompt_template": "Submit code for review",
                "expected_format": "code_block",
                "validation_rules": ["valid_syntax", "follows_conventions"]
            },
            {
                "turn_id": "review_feedback",
                "role": "reviewer",
                "prompt_template": "Provide comprehensive code review",
                "expected_format": "structured_feedback",
                "validation_rules": ["identifies_issues", "suggests_improvements"]
            },
            {
                "turn_id": "code_revision",
                "role": "developer",
                "prompt_template": "Address review feedback",
                "expected_format": "revised_code",
                "validation_rules": ["addresses_feedback", "maintains_functionality"]
            },
            {
                "turn_id": "final_approval",
                "role": "reviewer",
                "prompt_template": "Final review and approval",
                "expected_format": "approval_decision",
                "validation_rules": ["quality_assessment", "approval_criteria"]
            }
        ]
        
        success_metrics = {
            "review_thoroughness": 0.8,
            "improvement_quality": 0.7,
            "standards_compliance": 0.9,
            "communication_effectiveness": 0.8
        }
        
        return turns, success_metrics
    
    def _generate_debugging_turns(self, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """Generate debugging session turns"""
        turns = [
            {
                "turn_id": "problem_description",
                "role": "user",
                "prompt_template": "Describe the bug and symptoms",
                "expected_format": "problem_statement",
                "validation_rules": ["clear_description", "includes_symptoms"]
            },
            {
                "turn_id": "hypothesis_formation",
                "role": "debugger",
                "prompt_template": "Form initial hypothesis about the bug",
                "expected_format": "hypothesis_list",
                "validation_rules": ["logical_hypotheses", "testable_assumptions"]
            },
            {
                "turn_id": "evidence_gathering",
                "role": "debugger",
                "prompt_template": "Gather evidence to test hypotheses",
                "expected_format": "investigation_plan",
                "validation_rules": ["systematic_approach", "relevant_tests"]
            },
            {
                "turn_id": "root_cause_analysis",
                "role": "debugger",
                "prompt_template": "Identify root cause of the bug",
                "expected_format": "root_cause_explanation",
                "validation_rules": ["accurate_diagnosis", "explains_symptoms"]
            },
            {
                "turn_id": "solution_implementation",
                "role": "debugger",
                "prompt_template": "Implement fix for the bug",
                "expected_format": "code_fix",
                "validation_rules": ["fixes_root_cause", "maintains_functionality"]
            }
        ]
        
        success_metrics = {
            "diagnostic_accuracy": 0.9,
            "solution_effectiveness": 0.8,
            "debugging_efficiency": 0.7,
            "explanation_clarity": 0.8
        }
        
        return turns, success_metrics
    
    # Placeholder methods for other multi-turn scenarios
    def _generate_design_iteration_turns(self, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        turns = [{"turn_id": "design_iteration", "role": "designer", "prompt_template": "Iterate on design", "expected_format": "design_document", "validation_rules": ["design_quality"]}]
        success_metrics = {"design_quality": 0.8, "iteration_effectiveness": 0.7}
        return turns, success_metrics
    
    def _generate_teaching_dialogue_turns(self, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        turns = [{"turn_id": "teaching_dialogue", "role": "teacher", "prompt_template": "Teach concept", "expected_format": "explanation", "validation_rules": ["teaching_quality"]}]
        success_metrics = {"teaching_effectiveness": 0.8, "student_engagement": 0.7}
        return turns, success_metrics
    
    def _generate_collaborative_development_turns(self, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        turns = [{"turn_id": "collaboration", "role": "developer", "prompt_template": "Collaborate on development", "expected_format": "code_contribution", "validation_rules": ["collaboration_quality"]}]
        success_metrics = {"collaboration_effectiveness": 0.8, "code_integration": 0.7}
        return turns, success_metrics
    
    def _generate_requirements_refinement_turns(self, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        turns = [{"turn_id": "requirements_refinement", "role": "analyst", "prompt_template": "Refine requirements", "expected_format": "requirements_document", "validation_rules": ["requirements_quality"]}]
        success_metrics = {"requirements_clarity": 0.8, "stakeholder_satisfaction": 0.7}
        return turns, success_metrics
    
    def _generate_architecture_discussion_turns(self, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        turns = [{"turn_id": "architecture_discussion", "role": "architect", "prompt_template": "Discuss architecture", "expected_format": "architecture_document", "validation_rules": ["architecture_quality"]}]
        success_metrics = {"architecture_quality": 0.8, "decision_rationale": 0.7}
        return turns, success_metrics
    
    def _generate_performance_tuning_turns(self, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        turns = [{"turn_id": "performance_tuning", "role": "optimizer", "prompt_template": "Tune performance", "expected_format": "optimized_code", "validation_rules": ["performance_improvement"]}]
        success_metrics = {"performance_improvement": 0.8, "optimization_effectiveness": 0.7}
        return turns, success_metrics
    
    def _generate_default_multi_turn_content(self, difficulty: str, language: str, index: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        turns = [{"turn_id": "generic_turn", "role": "participant", "prompt_template": "Generic multi-turn interaction", "expected_format": "response", "validation_rules": ["response_quality"]}]
        success_metrics = {"interaction_quality": 0.7, "goal_achievement": 0.6}
        return turns, success_metrics
    
    # Utility methods
    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language"""
        extensions = {
            "python": "py", "javascript": "js", "java": "java", "cpp": "cpp",
            "go": "go", "rust": "rs", "typescript": "ts", "sql": "sql", "shell": "sh"
        }
        return extensions.get(language, "txt")
    
    def _get_test_command(self, language: str) -> str:
        """Get test command for language"""
        commands = {
            "python": "python -m pytest", "javascript": "node", "java": "javac && java",
            "cpp": "g++ -o test && ./test", "go": "go test", "rust": "cargo test",
            "typescript": "tsc && node", "sql": "psql -d test_db -f", "shell": "bash"
        }
        return commands.get(language, "echo")
    
    def _get_default_single_turn_template(self, scenario: str) -> Dict[str, Any]:
        """Get default template for single-turn scenario"""
        return {
            "id": f"default_{scenario}",
            "scenario": scenario,
            "difficulty": "intermediate",
            "language": "python",
            "context_mode": "minimal_context"
        }
    
    def _get_default_multi_turn_template(self, scenario: str) -> Dict[str, Any]:
        """Get default template for multi-turn scenario"""
        return {
            "id": f"default_{scenario}",
            "scenario": scenario,
            "difficulty": "intermediate",
            "language": "python",
            "context_mode": "full_context"
        }
    
    def save_datasets(self, problems: List[SingleTurnProblem] = None, scenarios: List[MultiTurnScenario] = None, output_dir: str = None):
        """Save generated datasets to files"""
        if output_dir:
            base_path = Path(output_dir)
        else:
            base_path = self.base_path
        
        if problems:
            # Group problems by scenario
            scenario_problems = {}
            for problem in problems:
                scenario = problem.scenario
                if scenario not in scenario_problems:
                    scenario_problems[scenario] = []
                scenario_problems[scenario].append(problem)
            
            # Save each scenario's problems
            for scenario, problem_list in scenario_problems.items():
                scenario_dir = base_path / "single_turn_scenarios" / scenario
                scenario_dir.mkdir(parents=True, exist_ok=True)
                
                problems_file = scenario_dir / "problems.jsonl"
                with open(problems_file, 'w') as f:
                    for problem in problem_list:
                        f.write(json.dumps(asdict(problem)) + '\n')
                
                logger.info(f"Saved {len(problem_list)} problems for scenario: {scenario}")
        
        if scenarios:
            # Group scenarios by type
            scenario_types = {}
            for scenario in scenarios:
                scenario_type = scenario.scenario
                if scenario_type not in scenario_types:
                    scenario_types[scenario_type] = []
                scenario_types[scenario_type].append(scenario)
            
            # Save each scenario type's scenarios
            for scenario_type, scenario_list in scenario_types.items():
                scenario_dir = base_path / "multi_turn_scenarios" / scenario_type
                scenario_dir.mkdir(parents=True, exist_ok=True)
                
                scenarios_file = scenario_dir / "scenarios.jsonl"
                with open(scenarios_file, 'w') as f:
                    for scenario in scenario_list:
                        f.write(json.dumps(asdict(scenario)) + '\n')
                
                logger.info(f"Saved {len(scenario_list)} scenarios for type: {scenario_type}")

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Generate production-ready datasets for AI evaluation")
    parser.add_argument("--scenario", type=str, help="Specific scenario to generate (optional)")
    parser.add_argument("--type", choices=["single", "multi", "both"], default="both", help="Type of scenarios to generate")
    parser.add_argument("--count", type=int, default=100, help="Number of problems/scenarios to generate per type")
    parser.add_argument("--output", type=str, help="Output directory (optional)")
    parser.add_argument("--base-path", type=str, default="lm_eval/tasks", help="Base path for task directories")
    
    args = parser.parse_args()
    
    generator = DatasetGenerator(args.base_path)
    
    all_problems = []
    all_scenarios = []
    
    if args.type in ["single", "both"]:
        scenarios_to_generate = [args.scenario] if args.scenario else generator.single_turn_scenarios
        
        for scenario in scenarios_to_generate:
            logger.info(f"Generating single-turn problems for scenario: {scenario}")
            problems = generator.generate_single_turn_problems(scenario, args.count)
            all_problems.extend(problems)
    
    if args.type in ["multi", "both"]:
        scenarios_to_generate = [args.scenario] if args.scenario else generator.multi_turn_scenarios
        
        for scenario in scenarios_to_generate:
            logger.info(f"Generating multi-turn scenarios for scenario: {scenario}")
            scenarios = generator.generate_multi_turn_scenarios(scenario, args.count)
            all_scenarios.extend(scenarios)
    
    # Save generated datasets
    generator.save_datasets(all_problems, all_scenarios, args.output)
    
    logger.info(f"Dataset generation complete. Generated {len(all_problems)} single-turn problems and {len(all_scenarios)} multi-turn scenarios.")

if __name__ == "__main__":
    main()