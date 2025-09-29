# Multi-Turn Evaluation Engine API Specification

## Overview

This document defines the API interfaces for the Multi-Turn Evaluation Engine V1.0, designed specifically for coding agent evaluation across various multi-turn scenarios.

## Core Interfaces

### 1. Unified Environment Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum

class ActionType(Enum):
    """Types of actions an agent can perform"""
    CODE_EDIT = "code_edit"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    BASH_COMMAND = "bash_command"
    TEST_RUN = "test_run"
    GIT_OPERATION = "git_operation"
    QUERY_CLARIFICATION = "query_clarification"
    ENVIRONMENT_SETUP = "environment_setup"

@dataclass
class Action:
    """Represents an agent action"""
    type: ActionType
    content: str
    parameters: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

@dataclass
class Observation:
    """Environment observation after action execution"""
    stdout: str = ""
    stderr: str = ""
    files_changed: List[str] = None
    test_results: Dict[str, Any] = None
    execution_time: float = 0.0
    return_code: int = 0
    environment_state: Dict[str, Any] = None
    feedback_type: str = "execution"  # "execution", "compilation", "test", "clarification"

class UnifiedEnv(ABC):
    """Unified environment interface for all evaluation scenarios"""
    
    @abstractmethod
    def reset(self) -> Observation:
        """Reset environment to initial state and return initial observation"""
        pass
    
    @abstractmethod
    def step(self, action: Action) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        """
        Execute action and return (observation, reward, done, info)
        
        Args:
            action: Agent action to execute
            
        Returns:
            observation: Environment feedback
            reward: Immediate reward (0.0 for intermediate steps, 1.0 for success)
            done: Whether episode is complete
            info: Additional metadata
        """
        pass
    
    @abstractmethod
    def success(self) -> bool:
        """Check if task has been completed successfully"""
        pass
    
    @abstractmethod
    def info(self) -> Dict[str, Any]:
        """Get current environment information and metadata"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        pass
    
    @abstractmethod
    def get_allowed_actions(self) -> List[ActionType]:
        """Get list of allowed action types in current state"""
        pass
    
    @abstractmethod
    def validate_action(self, action: Action) -> Tuple[bool, Optional[str]]:
        """Validate action before execution"""
        pass
```

### 2. Scenario-Specific Environment Implementations

```python
class RepositoryBugFixEnv(UnifiedEnv):
    """Environment for repository-level bug fixing scenarios"""
    
    def __init__(self, 
                 repo_path: str,
                 issue_description: str,
                 test_command: str,
                 max_files_to_modify: int = 10):
        self.repo_path = repo_path
        self.issue_description = issue_description
        self.test_command = test_command
        self.max_files_to_modify = max_files_to_modify
        self.modified_files = set()
        self.test_history = []
    
    def reset(self) -> Observation:
        """Initialize repository and return issue description"""
        # Git checkout, dependency installation, initial test run
        pass
    
    def step(self, action: Action) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        """Execute repository modification action"""
        pass

class InteractiveDebuggingEnv(UnifiedEnv):
    """Environment for interactive debugging scenarios"""
    
    def __init__(self, 
                 initial_code: str,
                 expected_behavior: str,
                 test_cases: List[Dict[str, Any]]):
        self.initial_code = initial_code
        self.expected_behavior = expected_behavior
        self.test_cases = test_cases
        self.debug_history = []
    
    def reset(self) -> Observation:
        """Start with failing code and error messages"""
        pass

class RequirementClarificationEnv(UnifiedEnv):
    """Environment for requirement clarification and implementation"""
    
    def __init__(self, 
                 vague_requirement: str,
                 clarification_qa: List[Dict[str, str]],
                 acceptance_criteria: List[str]):
        self.vague_requirement = vague_requirement
        self.clarification_qa = clarification_qa
        self.acceptance_criteria = acceptance_criteria
        self.clarification_round = 0
    
    def reset(self) -> Observation:
        """Present vague requirement"""
        pass

class DataScienceScriptEnv(UnifiedEnv):
    """Environment for data science script development"""
    
    def __init__(self, 
                 data_path: str,
                 task_description: str,
                 expected_output: Any,
                 allowed_libraries: List[str] = None):
        self.data_path = data_path
        self.task_description = task_description
        self.expected_output = expected_output
        self.allowed_libraries = allowed_libraries or ["pandas", "numpy", "matplotlib", "seaborn"]
    
    def reset(self) -> Observation:
        """Load data and present task"""
        pass

class CommandLineEnv(UnifiedEnv):
    """Environment for command-line and environment manipulation"""
    
    def __init__(self, 
                 task_steps: List[str],
                 environment_type: str = "bash",  # "bash", "sql", "docker"
                 allow_rollback: bool = True):
        self.task_steps = task_steps
        self.environment_type = environment_type
        self.allow_rollback = allow_rollback
        self.command_history = []
        self.checkpoints = []
    
    def reset(self) -> Observation:
        """Initialize command environment"""
        pass

class CrossLanguageFixEnv(UnifiedEnv):
    """Environment for cross-language bug fixing"""
    
    def __init__(self, 
                 bug_description: str,
                 language_implementations: Dict[str, str],  # language -> code
                 test_suites: Dict[str, List[str]]):
        self.bug_description = bug_description
        self.language_implementations = language_implementations
        self.test_suites = test_suites
        self.current_language = None
    
    def reset(self) -> Observation:
        """Present bug description and language options"""
        pass
```

### 3. Benchmark Adapter Interfaces

```python
class BenchmarkAdapter(ABC):
    """Base adapter for integrating external benchmark tools"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get adapter name"""
        pass
    
    @abstractmethod
    def get_supported_scenarios(self) -> List[str]:
        """Get list of supported scenario types"""
        pass
    
    @abstractmethod
    def load_tasks(self, 
                   scenario_filter: Optional[str] = None,
                   difficulty_filter: Optional[str] = None,
                   sample_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load tasks from benchmark"""
        pass
    
    @abstractmethod
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create environment for specific task"""
        pass
    
    @abstractmethod
    def convert_results(self, results: Any) -> Dict[str, Any]:
        """Convert benchmark results to standard format"""
        pass

class SWEBenchAdapter(BenchmarkAdapter):
    """Adapter for SWE-bench integration"""
    
    def __init__(self, 
                 variant: str = "lite",  # "lite", "verified", "bash_only", "multimodal"
                 max_samples: int = 50):
        self.variant = variant
        self.max_samples = max_samples
    
    def get_name(self) -> str:
        return f"swe_bench_{self.variant}"
    
    def get_supported_scenarios(self) -> List[str]:
        return ["repository_bug_fix", "interactive_debugging"]
    
    def load_tasks(self, **kwargs) -> List[Dict[str, Any]]:
        """Load SWE-bench tasks with git checkout and dependency setup"""
        pass
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create SWE-bench repository environment"""
        return SWEBenchEnvironment(task_config)

class InterCodeAdapter(BenchmarkAdapter):
    """Adapter for InterCode integration"""
    
    def __init__(self, 
                 subtask: str = "python",  # "python", "bash", "sql", "swe"
                 max_samples: int = 100):
        self.subtask = subtask
        self.max_samples = max_samples
    
    def get_name(self) -> str:
        return f"intercode_{self.subtask}"
    
    def get_supported_scenarios(self) -> List[str]:
        scenarios = {
            "python": ["interactive_debugging", "data_science_script"],
            "bash": ["command_line"],
            "sql": ["command_line"],
            "swe": ["repository_bug_fix"]
        }
        return scenarios.get(self.subtask, [])
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create InterCode environment with step() adapter"""
        return InterCodeEnvironment(task_config, self.subtask)

class ConvCodeBenchAdapter(BenchmarkAdapter):
    """Adapter for ConvCodeBench offline log replay"""
    
    def __init__(self, max_samples: int = 200):
        self.max_samples = max_samples
    
    def get_name(self) -> str:
        return "conv_code_bench"
    
    def get_supported_scenarios(self) -> List[str]:
        return ["requirement_clarification", "interactive_debugging"]
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create conversation replay environment"""
        return ConvCodeBenchEnvironment(task_config)

class BugsInPyAdapter(BenchmarkAdapter):
    """Adapter for BugsInPy Python bug fixing"""
    
    def get_name(self) -> str:
        return "bugs_in_py"
    
    def get_supported_scenarios(self) -> List[str]:
        return ["repository_bug_fix", "interactive_debugging"]
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create Python bug fixing environment"""
        return BugsInPyEnvironment(task_config)

class Defects4JAdapter(BenchmarkAdapter):
    """Adapter for Defects4J Java bug fixing"""
    
    def get_name(self) -> str:
        return "defects4j"
    
    def get_supported_scenarios(self) -> List[str]:
        return ["repository_bug_fix", "cross_language_fix"]
    
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        """Create Java bug fixing environment"""
        return Defects4JEnvironment(task_config)
```

### 4. Multi-Turn Orchestrator Interface

```python
@dataclass
class EvaluationConfig:
    """Configuration for multi-turn evaluation"""
    max_turns: int = 10
    max_wall_time: int = 3600  # seconds
    feedback_config: Dict[str, Any] = None
    safety_config: Dict[str, Any] = None
    metrics_config: Dict[str, Any] = None
    termination_conditions: List[str] = None

@dataclass
class TurnResult:
    """Result of a single turn"""
    turn_number: int
    action: Action
    observation: Observation
    reward: float
    done: bool
    execution_time: float
    tokens_used: int
    cost_usd: float
    safety_violations: List[str] = None

@dataclass
class EvaluationResult:
    """Complete evaluation result"""
    run_id: str
    task_id: str
    sample_id: str
    success: bool
    total_turns: int
    total_steps: int
    wall_time_s: float
    token_in: int
    token_out: int
    cost_usd: float
    files_touched: int
    edit_added: int
    edit_deleted: int
    redundancy_rate: float
    recovered: bool
    safety_incidents: int
    turn_results: List[TurnResult]
    final_metrics: Dict[str, float]
    notes: str = ""

class MultiTurnOrchestrator:
    """Orchestrates multi-turn evaluation execution"""
    
    def __init__(self, 
                 safety_guard: 'SafetyGuard',
                 feedback_processor: 'FeedbackProcessor',
                 metrics_calculator: 'MetricsCalculator'):
        self.safety_guard = safety_guard
        self.feedback_processor = feedback_processor
        self.metrics_calculator = metrics_calculator
    
    async def execute_evaluation(self, 
                               env: UnifiedEnv,
                               agent: 'Agent',
                               config: EvaluationConfig) -> EvaluationResult:
        """Execute complete multi-turn evaluation"""
        pass
    
    def should_terminate(self, 
                        turn_results: List[TurnResult],
                        env: UnifiedEnv,
                        config: EvaluationConfig) -> Tuple[bool, str]:
        """Determine if evaluation should terminate"""
        pass
```

### 5. Metrics Calculation Interface

```python
class MetricsCalculator:
    """Calculates comprehensive metrics for multi-turn evaluation"""
    
    def calculate_task_success_metrics(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate task success metrics:
        - Resolved%: Percentage of successfully completed tasks
        - Recall: Same as Resolved% for ConvCodeBench compatibility
        - MRR: Mean Reciprocal Rank (1/turns for successful tasks)
        """
        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r.success)
        
        resolved_percent = (successful_tasks / total_tasks) * 100 if total_tasks > 0 else 0.0
        recall = resolved_percent  # Same metric, different name
        
        # MRR calculation
        mrr_sum = 0.0
        for result in results:
            if result.success:
                mrr_sum += 1.0 / result.total_turns
        mrr = mrr_sum / total_tasks if total_tasks > 0 else 0.0
        
        return {
            "resolved_percent": resolved_percent,
            "recall": recall,
            "mrr": mrr
        }
    
    def calculate_efficiency_metrics(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate efficiency metrics:
        - Avg Turns: Average number of turns per task
        - Avg Steps: Average number of steps per task
        - Redundancy Rate: Percentage of ineffective actions
        """
        if not results:
            return {"avg_turns": 0.0, "avg_steps": 0.0, "redundancy_rate": 0.0}
        
        avg_turns = sum(r.total_turns for r in results) / len(results)
        avg_steps = sum(r.total_steps for r in results) / len(results)
        avg_redundancy = sum(r.redundancy_rate for r in results) / len(results)
        
        return {
            "avg_turns": avg_turns,
            "avg_steps": avg_steps,
            "redundancy_rate": avg_redundancy
        }
    
    def calculate_quality_metrics(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate repair quality metrics:
        - Edit Churn: Average lines changed per successful task
        - Files Touched: Average files modified per task
        """
        successful_results = [r for r in results if r.success]
        if not successful_results:
            return {"edit_churn": 0.0, "avg_files_touched": 0.0}
        
        edit_churn = sum(r.edit_added + r.edit_deleted for r in successful_results) / len(successful_results)
        avg_files_touched = sum(r.files_touched for r in results) / len(results)
        
        return {
            "edit_churn": edit_churn,
            "avg_files_touched": avg_files_touched
        }
    
    def calculate_robustness_metrics(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate robustness metrics:
        - Recovery Rate: Percentage of tasks that recovered from errors
        - Stability: Consistency across multiple runs (requires multiple runs)
        """
        total_tasks = len(results)
        recovered_tasks = sum(1 for r in results if r.recovered)
        
        recovery_rate = (recovered_tasks / total_tasks) * 100 if total_tasks > 0 else 0.0
        
        return {
            "recovery_rate": recovery_rate,
            "stability_score": 0.0  # Requires multiple runs to calculate
        }
    
    def calculate_cost_metrics(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate cost metrics:
        - Wall Time per Solved: Average time per successful task
        - Token/Cost per Solved: Average tokens/cost per successful task
        """
        successful_results = [r for r in results if r.success]
        if not successful_results:
            return {
                "wall_time_per_solved": 0.0,
                "tokens_per_solved": 0.0,
                "cost_per_solved": 0.0
            }
        
        wall_time_per_solved = sum(r.wall_time_s for r in successful_results) / len(successful_results)
        tokens_per_solved = sum(r.token_in + r.token_out for r in successful_results) / len(successful_results)
        cost_per_solved = sum(r.cost_usd for r in successful_results) / len(successful_results)
        
        return {
            "wall_time_per_solved": wall_time_per_solved,
            "tokens_per_solved": tokens_per_solved,
            "cost_per_solved": cost_per_solved
        }
    
    def calculate_safety_metrics(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate safety metrics:
        - Safety Incidents per 100 tasks
        """
        total_tasks = len(results)
        total_incidents = sum(r.safety_incidents for r in results)
        
        incidents_per_100 = (total_incidents / total_tasks) * 100 if total_tasks > 0 else 0.0
        
        return {
            "safety_incidents_per_100": incidents_per_100
        }
```

### 6. REST API Endpoints

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional

router = APIRouter(prefix="/api/v1/multi-turn", tags=["Multi-Turn Evaluation"])

@router.post("/evaluations", response_model=Dict[str, str])
async def create_evaluation(
    background_tasks: BackgroundTasks,
    scenario: str,
    benchmark: str,
    agent_config: Dict[str, Any],
    evaluation_config: Optional[EvaluationConfig] = None,
    sample_filter: Optional[Dict[str, Any]] = None
):
    """Create and start a new multi-turn evaluation"""
    pass

@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResult)
async def get_evaluation_status(evaluation_id: str):
    """Get status and results of an evaluation"""
    pass

@router.get("/evaluations/{evaluation_id}/turns", response_model=List[TurnResult])
async def get_evaluation_turns(evaluation_id: str):
    """Get detailed turn-by-turn results"""
    pass

@router.post("/evaluations/{evaluation_id}/cancel")
async def cancel_evaluation(evaluation_id: str):
    """Cancel a running evaluation"""
    pass

@router.get("/scenarios", response_model=List[str])
async def list_scenarios():
    """List available evaluation scenarios"""
    pass

@router.get("/benchmarks", response_model=List[Dict[str, Any]])
async def list_benchmarks():
    """List available benchmark adapters"""
    pass

@router.get("/benchmarks/{benchmark_name}/tasks")
async def list_benchmark_tasks(
    benchmark_name: str,
    scenario_filter: Optional[str] = None,
    difficulty_filter: Optional[str] = None,
    limit: Optional[int] = None
):
    """List tasks available in a benchmark"""
    pass

@router.post("/metrics/calculate", response_model=Dict[str, float])
async def calculate_metrics(
    results: List[EvaluationResult],
    metric_types: List[str] = ["all"]
):
    """Calculate metrics for a set of evaluation results"""
    pass

@router.get("/baselines/{baseline_name}/run")
async def run_baseline(
    baseline_name: str,  # "regression", "mid_fidelity", "milestone"
    background_tasks: BackgroundTasks
):
    """Run predefined baseline evaluations"""
    pass
```

## Data Models

### Standard Output Schema

```python
@dataclass
class StandardizedOutput:
    """Standardized output format for all evaluations"""
    # Identification
    run_id: str
    task_id: str
    sample_id: str
    benchmark: str
    scenario: str
    
    # Results
    success: bool
    turns: int
    steps: int
    wall_time_s: float
    
    # Token and Cost Tracking
    token_in: int
    token_out: int
    cost_usd: float
    
    # Code Quality Metrics
    files_touched: int
    edit_added: int
    edit_deleted: int
    redundancy_rate: float
    
    # Robustness
    recovered: bool
    safety_incidents: int
    
    # Additional Information
    notes: str
    metadata: Dict[str, Any]
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to CSV-compatible dictionary"""
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "sample_id": self.sample_id,
            "benchmark": self.benchmark,
            "scenario": self.scenario,
            "success": self.success,
            "turns": self.turns,
            "steps": self.steps,
            "wall_time_s": self.wall_time_s,
            "token_in": self.token_in,
            "token_out": self.token_out,
            "cost_usd": self.cost_usd,
            "files_touched": self.files_touched,
            "edit_added": self.edit_added,
            "edit_deleted": self.edit_deleted,
            "redundancy_rate": self.redundancy_rate,
            "recovered": self.recovered,
            "safety_incidents": self.safety_incidents,
            "notes": self.notes
        }
```

This API specification provides a comprehensive interface for the Multi-Turn Evaluation Engine, covering all the scenarios and tools you mentioned while maintaining compatibility with existing systems.