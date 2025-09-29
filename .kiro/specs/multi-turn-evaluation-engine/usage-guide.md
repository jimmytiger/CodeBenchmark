# Multi-Turn Evaluation Engine Usage Guide

## Quick Start

### Installation and Setup

```bash
# Clone and setup
cd EvaluationEngineV1.0
pip install -r requirements.txt

# Install benchmark dependencies
pip install swe-bench intercode-bench bugs-in-py defects4j-py

# Setup environment
export EVALUATION_ENGINE_V1_ROOT=$(pwd)
export OPENAI_API_KEY="your-api-key"
```

### Basic Usage

```python
from EvaluationEngineV1.orchestrator import MultiTurnOrchestrator
from EvaluationEngineV1.adapters import SWEBenchAdapter, InterCodeAdapter
from EvaluationEngineV1.agents import OpenAIAgent

# Initialize orchestrator
orchestrator = MultiTurnOrchestrator()

# Create agent
agent = OpenAIAgent(model="gpt-4", temperature=0.1)

# Run SWE-bench evaluation
adapter = SWEBenchAdapter(variant="lite", max_samples=25)
results = orchestrator.run_benchmark(
    adapter=adapter,
    agent=agent,
    scenario="repository_bug_fix",
    max_turns=10
)

print(f"Resolved: {results.metrics['resolved_percent']:.1f}%")
print(f"Average turns: {results.metrics['avg_turns']:.1f}")
```

## Scenario Configurations

### 1. Repository-Level Bug Fixing (SWE-bench)

**最适合真实研发场景的评估**

```python
# Configuration
config = {
    "scenario": "repository_bug_fix",
    "benchmark": "swe_bench_lite",
    "max_turns": 15,
    "max_wall_time": 1800,  # 30 minutes
    "feedback_config": {
        "include_test_output": True,
        "include_stack_trace": True,
        "max_feedback_length": 8000,
        "summarize_long_outputs": True
    },
    "safety_config": {
        "allowed_commands": ["git", "python", "pip", "pytest", "bash"],
        "forbidden_patterns": ["rm -rf", "sudo", "curl", "wget"],
        "max_file_modifications": 10
    }
}

# Usage
from EvaluationEngineV1.scenarios import RepositoryBugFixScenario

scenario = RepositoryBugFixScenario(config)
results = orchestrator.evaluate(
    scenario=scenario,
    agent=agent,
    sample_count=25
)

# Expected metrics
# Resolved%: 15-30% (depending on agent capability)
# Avg Turns: 8-12
# Files Touched: 2-5
# Wall Time per Solved: 600-1200s
```

**Sample Task Flow:**
1. **Turn 1**: Agent reads issue description and repository structure
2. **Turn 2-3**: Agent explores relevant files and understands the bug
3. **Turn 4-6**: Agent makes initial fix attempts
4. **Turn 7-8**: Agent runs tests and gets failure feedback
5. **Turn 9-12**: Agent iterates based on test feedback
6. **Turn 13-15**: Final refinements and validation

### 2. Interactive Debugging (InterCode)

**强调利用执行反馈的迭代修复**

```python
# InterCode Python Configuration
config = {
    "scenario": "interactive_debugging",
    "benchmark": "intercode_python",
    "max_turns": 20,
    "feedback_config": {
        "execution_timeout": 30,
        "capture_stdout": True,
        "capture_stderr": True,
        "include_variable_state": True
    }
}

# Usage
from EvaluationEngineV1.adapters import InterCodeAdapter

adapter = InterCodeAdapter(subtask="python", max_samples=50)
results = orchestrator.run_benchmark(
    adapter=adapter,
    agent=agent,
    config=config
)

# Expected metrics
# Solved%: 40-60%
# Avg Steps: 15-25
# Recovery Rate: 70-85%
# Redundancy Rate: 20-35%
```

**Sample Debugging Session:**
```python
# Initial failing code
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Turn 1: Agent runs code
action = Action(type="CODE_RUN", content="print(fibonacci(10))")
# Observation: TimeoutError (too slow)

# Turn 2: Agent identifies performance issue
action = Action(type="CODE_EDIT", content="""
def fibonacci(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fibonacci(n-1, memo) + fibonacci(n-2, memo)
    return memo[n]
""")

# Turn 3: Agent tests optimized version
action = Action(type="CODE_RUN", content="print(fibonacci(10))")
# Observation: 55 (correct, fast)
```

### 3. Requirement Clarification + Implementation

**需求模糊→澄清问答→补齐实现与测试**

```python
config = {
    "scenario": "requirement_clarification",
    "benchmark": "conv_code_bench",
    "max_turns": 25,
    "clarification_config": {
        "max_clarification_rounds": 5,
        "require_test_cases": True,
        "acceptance_criteria_validation": True
    }
}

# Usage
from EvaluationEngineV1.scenarios import RequirementClarificationScenario

scenario = RequirementClarificationScenario(config)
results = orchestrator.evaluate(
    scenario=scenario,
    agent=agent,
    sample_count=100
)
```

**Sample Clarification Flow:**
```
Initial Requirement: "Create a function to process user data"

Turn 1 (Agent): "What type of user data should be processed?"
Turn 2 (Environment): "User profiles with name, email, and preferences"

Turn 3 (Agent): "What processing is needed?"
Turn 4 (Environment): "Validate email format and normalize names"

Turn 5 (Agent): "Should invalid data be filtered or raise errors?"
Turn 6 (Environment): "Filter invalid entries and log warnings"

Turn 7-15: Agent implements solution with tests
Turn 16-20: Agent refines based on acceptance criteria feedback
```

### 4. Data Science Script Development

**读数据→编写/修复 Pandas/Numpy/可视化代码→比对期望输出**

```python
config = {
    "scenario": "data_science_script",
    "data_path": "./datasets/sample_data.csv",
    "task_description": "Analyze sales data and create visualization",
    "expected_output_path": "./expected_outputs/sales_analysis.png",
    "allowed_libraries": ["pandas", "numpy", "matplotlib", "seaborn"],
    "max_turns": 15
}

# Usage
from EvaluationEngineV1.scenarios import DataScienceScenario

scenario = DataScienceScenario(config)
results = orchestrator.evaluate(
    scenario=scenario,
    agent=agent,
    sample_count=30
)
```

**Sample Data Science Task:**
```python
# Turn 1: Agent explores data
action = Action(type="CODE_RUN", content="""
import pandas as pd
df = pd.read_csv('sales_data.csv')
print(df.head())
print(df.info())
""")

# Turn 2-5: Agent analyzes data patterns
# Turn 6-10: Agent creates visualizations
# Turn 11-15: Agent compares with expected output and refines
```

### 5. Command Line Environment Manipulation

**Bash/SQL 步骤式任务→逐步执行与回退**

```python
config = {
    "scenario": "command_line",
    "environment_type": "bash",  # or "sql", "docker"
    "task_steps": [
        "Setup development environment",
        "Clone repository and install dependencies", 
        "Run tests and fix any failures",
        "Deploy to staging environment"
    ],
    "allow_rollback": True,
    "max_turns": 30
}

# Usage
from EvaluationEngineV1.scenarios import CommandLineScenario

scenario = CommandLineScenario(config)
results = orchestrator.evaluate(
    scenario=scenario,
    agent=agent,
    sample_count=20
)
```

### 6. Cross-Language Bug Fixing

**同类缺陷在 Python/Java/TS 的迁移与对齐**

```python
config = {
    "scenario": "cross_language_fix",
    "languages": ["python", "java", "typescript"],
    "bug_description": "Off-by-one error in array indexing",
    "test_consistency": True,
    "max_turns": 20
}

# Usage
from EvaluationEngineV1.scenarios import CrossLanguageFixScenario

scenario = CrossLanguageFixScenario(config)
results = orchestrator.evaluate(
    scenario=scenario,
    agent=agent,
    sample_count=15
)
```

## Benchmark Integration Guide

### SWE-bench Setup

```bash
# Install SWE-bench
pip install swe-bench

# Download dataset
python -c "
from swe_bench import get_dataset
dataset = get_dataset('princeton-nlp/SWE-bench_Lite')
print(f'Loaded {len(dataset)} tasks')
"
```

```python
# Custom SWE-bench configuration
from EvaluationEngineV1.adapters import SWEBenchAdapter

adapter = SWEBenchAdapter(
    variant="lite",  # "lite", "verified", "bash_only"
    max_samples=25,
    timeout_per_task=1800,
    include_patch_analysis=True
)

# Run evaluation
results = orchestrator.run_benchmark(
    adapter=adapter,
    agent=your_agent,
    parallel_workers=4
)
```

### InterCode Setup

```bash
# Install InterCode
pip install intercode-bench

# Setup environments
intercode-setup --env python bash sql
```

```python
# InterCode configuration for different subtasks
configs = {
    "python": {
        "max_samples": 50,
        "execution_timeout": 30,
        "memory_limit": "1GB"
    },
    "bash": {
        "max_samples": 50,
        "command_timeout": 10,
        "sandbox_mode": True
    },
    "sql": {
        "max_samples": 30,
        "database": "sqlite",
        "query_timeout": 15
    }
}

for subtask, config in configs.items():
    adapter = InterCodeAdapter(subtask=subtask, **config)
    results = orchestrator.run_benchmark(adapter, agent)
    print(f"{subtask}: {results.metrics['solved_percent']:.1f}% solved")
```

### ConvCodeBench Setup

```bash
# Download ConvCodeBench dataset
wget https://github.com/ConvCodeBench/dataset/releases/latest/download/conv_code_bench.tar.gz
tar -xzf conv_code_bench.tar.gz
```

```python
# ConvCodeBench replay configuration
from EvaluationEngineV1.adapters import ConvCodeBenchAdapter

adapter = ConvCodeBenchAdapter(
    dataset_path="./conv_code_bench",
    max_samples=100,
    replay_mode="interactive",  # "interactive" or "batch"
    feedback_types=["compile", "execution", "test"]
)

results = orchestrator.run_benchmark(adapter, agent)
```

### BugsInPy / Defects4J Setup

```bash
# BugsInPy setup
git clone https://github.com/soarsmu/BugsInPy.git
cd BugsInPy
pip install -r requirements.txt

# Defects4J setup (requires Java)
git clone https://github.com/rjust/defects4j.git
cd defects4j
./init.sh
```

```python
# BugsInPy configuration
from EvaluationEngineV1.adapters import BugsInPyAdapter

adapter = BugsInPyAdapter(
    bugs_in_py_path="./BugsInPy",
    max_samples=25,
    include_test_analysis=True
)

# Defects4J configuration  
from EvaluationEngineV1.adapters import Defects4JAdapter

adapter = Defects4JAdapter(
    defects4j_path="./defects4j",
    max_samples=25,
    projects=["Lang", "Math", "Time"]  # Focus on specific projects
)
```

## Predefined Baseline Configurations

### 1. Regression Baseline (Daily/PR)

```python
# Quick regression test - runs in ~30 minutes
regression_config = {
    "name": "daily_regression",
    "benchmarks": [
        {
            "adapter": "conv_code_bench",
            "samples": 100,
            "feedback_types": ["compile_only", "exec_only"],
            "max_turns": 5
        }
    ],
    "metrics": ["recall", "mrr", "avg_turns", "cost_usd"],
    "alert_thresholds": {
        "recall_drop": 5.0,  # Alert if recall drops >5%
        "cost_increase": 20.0  # Alert if cost increases >20%
    }
}

# Run regression
results = orchestrator.run_baseline("regression", regression_config)
```

### 2. Mid-Fidelity Baseline (Weekly)

```python
# Comprehensive weekly evaluation - runs in ~4 hours
mid_fidelity_config = {
    "name": "weekly_comprehensive",
    "benchmarks": [
        {
            "adapter": "intercode_python",
            "samples": 50,
            "max_turns": 15
        },
        {
            "adapter": "intercode_bash", 
            "samples": 50,
            "max_turns": 20
        }
    ],
    "metrics": ["solved_percent", "avg_steps", "recovery_rate", "wall_time"],
    "generate_report": True,
    "compare_with_previous": True
}

results = orchestrator.run_baseline("mid_fidelity", mid_fidelity_config)
```

### 3. Milestone Baseline (Monthly)

```python
# Full milestone evaluation - runs in ~24 hours
milestone_config = {
    "name": "monthly_milestone",
    "benchmarks": [
        {
            "adapter": "swe_bench_lite",
            "samples": 25,
            "max_turns": 15
        },
        {
            "adapter": "swe_bench_verified",
            "samples": 25, 
            "max_turns": 15
        }
    ],
    "metrics": ["resolved_percent", "avg_turns", "edit_churn", "cost_per_solved", "stability"],
    "multiple_runs": 3,  # For stability calculation
    "detailed_analysis": True,
    "generate_benchmark_report": True
}

results = orchestrator.run_baseline("milestone", milestone_config)
```

## CLI Usage

### Basic Commands

```bash
# List available scenarios and benchmarks
evaluation-engine list-scenarios
evaluation-engine list-benchmarks

# Run single evaluation
evaluation-engine run \
    --scenario repository_bug_fix \
    --benchmark swe_bench_lite \
    --agent openai-gpt4 \
    --samples 10 \
    --max-turns 15 \
    --output results.json

# Run predefined baseline
evaluation-engine baseline regression --config daily_config.yaml

# Monitor running evaluation
evaluation-engine status <evaluation_id>
evaluation-engine logs <evaluation_id> --follow

# Calculate metrics from results
evaluation-engine metrics calculate \
    --input results.json \
    --metrics resolved_percent,avg_turns,cost_per_solved \
    --output metrics_report.json
```

### Configuration Files

```yaml
# evaluation_config.yaml
scenario: repository_bug_fix
benchmark: swe_bench_lite
agent:
  type: openai
  model: gpt-4
  temperature: 0.1
  max_tokens: 4000

evaluation:
  max_turns: 15
  max_wall_time: 1800
  sample_count: 25

feedback:
  max_length: 8000
  include_stack_trace: true
  summarize_long_outputs: true
  top_k_assertions: 5

safety:
  allowed_commands: [git, python, pip, pytest, bash]
  forbidden_patterns: [rm -rf, sudo, curl]
  max_file_modifications: 10
  sandbox_mode: true

output:
  format: [json, csv]
  include_turn_details: true
  generate_summary: true
```

```bash
# Run with config file
evaluation-engine run --config evaluation_config.yaml
```

## API Usage

### REST API Examples

```python
import requests

# Start evaluation
response = requests.post("http://localhost:8000/api/v1/multi-turn/evaluations", json={
    "scenario": "repository_bug_fix",
    "benchmark": "swe_bench_lite", 
    "agent_config": {
        "type": "openai",
        "model": "gpt-4",
        "temperature": 0.1
    },
    "evaluation_config": {
        "max_turns": 15,
        "sample_count": 25
    }
})

evaluation_id = response.json()["evaluation_id"]

# Monitor progress
while True:
    status = requests.get(f"http://localhost:8000/api/v1/multi-turn/evaluations/{evaluation_id}")
    if status.json()["status"] == "completed":
        break
    time.sleep(30)

# Get results
results = requests.get(f"http://localhost:8000/api/v1/multi-turn/evaluations/{evaluation_id}")
print(f"Success rate: {results.json()['metrics']['resolved_percent']:.1f}%")
```

### WebSocket Real-time Monitoring

```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    if data["type"] == "turn_completed":
        print(f"Turn {data['turn']}: {data['action_type']} -> {data['result']}")
    elif data["type"] == "evaluation_completed":
        print(f"Evaluation completed: {data['success_rate']:.1f}% success")

ws = websocket.WebSocketApp(
    f"ws://localhost:8000/api/v1/multi-turn/evaluations/{evaluation_id}/stream",
    on_message=on_message
)
ws.run_forever()
```

## Custom Agent Integration

### Agent Interface

```python
from EvaluationEngineV1.agents import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, model_config):
        self.model_config = model_config
    
    async def generate_action(self, 
                            observation: Observation,
                            turn_history: List[TurnResult],
                            allowed_actions: List[ActionType]) -> Action:
        """Generate next action based on observation and history"""
        # Your agent logic here
        pass
    
    def get_token_usage(self) -> Dict[str, int]:
        """Return token usage statistics"""
        return {"input_tokens": 0, "output_tokens": 0}
    
    def get_cost(self) -> float:
        """Return cost in USD"""
        return 0.0

# Register custom agent
from EvaluationEngineV1.registry import agent_registry
agent_registry.register("custom_agent", CustomAgent)
```

### Using Custom Agent

```python
# Initialize custom agent
agent = CustomAgent({
    "model_path": "./my_model",
    "temperature": 0.2
})

# Run evaluation
results = orchestrator.evaluate(
    scenario=scenario,
    agent=agent,
    config=config
)
```

## Metrics and Analysis

### Comprehensive Metrics Dashboard

```python
from EvaluationEngineV1.analysis import MetricsDashboard

dashboard = MetricsDashboard()

# Load results from multiple evaluations
dashboard.load_results([
    "swe_bench_results.json",
    "intercode_results.json", 
    "bugs_in_py_results.json"
])

# Generate comprehensive report
report = dashboard.generate_report(
    include_plots=True,
    compare_benchmarks=True,
    trend_analysis=True
)

# Save report
dashboard.save_report(report, "evaluation_report.html")
```

### Custom Metrics

```python
from EvaluationEngineV1.metrics import MetricsCalculator

class CustomMetricsCalculator(MetricsCalculator):
    def calculate_code_quality_score(self, results: List[EvaluationResult]) -> float:
        """Custom metric: code quality based on edit patterns"""
        # Your custom metric logic
        pass

# Use custom metrics
calculator = CustomMetricsCalculator()
metrics = calculator.calculate_all_metrics(results)
```

This usage guide provides comprehensive examples for all the scenarios and tools you mentioned, with practical configurations and expected performance ranges for each benchmark.