# Multi-Turn Evaluation Engine Usage Guide

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Evaluation Scenarios](#evaluation-scenarios)
4. [Configuration Examples](#configuration-examples)
5. [CLI Usage Examples](#cli-usage-examples)
6. [API Usage Examples](#api-usage-examples)
7. [Custom Agent Integration](#custom-agent-integration)
8. [Metrics Analysis](#metrics-analysis)
9. [Best Practices](#best-practices)
10. [Advanced Usage](#advanced-usage)

## Overview

The Multi-Turn Evaluation Engine supports six primary evaluation scenarios, each designed to test different aspects of AI agent capabilities:

1. **Repository Bug Fixing** (SWE-bench) - Real-world software engineering tasks
2. **Interactive Code Debugging** (InterCode) - Multi-turn coding with immediate feedback
3. **Conversational Code Generation** (ConvCodeBench) - Dialogue-based programming
4. **Cross-Language Bug Fixing** (BugsInPy, Defects4J) - Language-specific debugging
5. **Requirement Clarification** - Interactive specification gathering
6. **Custom Evaluation Scenarios** - Domain-specific evaluations

This guide provides comprehensive examples for each scenario, showing how to configure, execute, and analyze evaluations.

## Getting Started

### Installation and Setup

```bash
# Install the evaluation engine
pip install multi-turn-evaluation-engine

# Verify installation
multi-turn --version

# Create workspace directory
mkdir my_evaluations
cd my_evaluations

# Initialize basic configuration
multi-turn init-config --output config.yaml --template basic
```

### Basic Configuration Structure

```yaml
# config.yaml - Basic structure
model_id: "your-model-id"
task_ids:
  - "task_1"
  - "task_2"

max_turns: 10
timeout_seconds: 3600
feedback_strategy: "adaptive"
safety_level: "moderate"

# Optional sections
feedback_config: {}
safety_config: {}
export_config: {}
metadata: {}
```

## Evaluation Scenarios

### 1. Repository Bug Fixing (SWE-bench)

SWE-bench evaluates AI agents on real-world software engineering tasks, including bug fixing, feature implementation, and code maintenance.

#### Configuration Example

```yaml
# swe_bench_config.yaml
model_id: "gpt-4"
task_ids:
  - "swe_bench_lite_django_001"
  - "swe_bench_lite_requests_002"
  - "swe_bench_lite_scikit_003"

max_turns: 15
timeout_seconds: 7200  # 2 hours

feedback_strategy: "adaptive"
safety_level: "moderate"

feedback_config:
  context_strategy: "adaptive"
  max_feedback_length: 15000
  enable_stack_summarization: true
  enable_file_context: true
  top_k_assertions: 5

safety_config:
  allowed_tools: ["python", "bash", "git", "pytest", "pip"]
  enable_sandboxing: true
  max_execution_time: 600
  resource_limits:
    memory: "4GB"
    cpu_time: "300s"

export_config:
  formats: ["json", "csv"]
  include_turn_details: true
  generate_summary_report: true

metadata:
  scenario: "swe_bench"
  experiment_name: "bug_fixing_evaluation"
  description: "Evaluating AI agents on real-world software engineering tasks"
```

#### CLI Usage

```bash
# Run SWE-bench evaluation
multi-turn run-config swe_bench_config.yaml --interactive

# Run specific SWE-bench tasks
multi-turn run \
  --model-id gpt-4 \
  --task-id swe_bench_lite_django_001 \
  --task-id swe_bench_lite_requests_002 \
  --max-turns 15 \
  --timeout 7200 \
  --output swe_bench_results.json

# Monitor running evaluation
multi-turn monitor --host localhost --port 8000
```

#### Expected Workflow

1. **Repository Setup**: Clone target repository and checkout specific commit
2. **Issue Analysis**: Analyze bug report and failing tests
3. **Code Exploration**: Navigate and understand codebase structure
4. **Solution Development**: Implement fix through multiple iterations
5. **Testing**: Run tests to validate solution
6. **Refinement**: Iterate based on test feedback

#### Sample Task Configuration

```json
{
  "task_id": "swe_bench_lite_django_001",
  "repository": "django/django",
  "commit": "a1b2c3d4e5f6",
  "issue_description": "Fix QuerySet.distinct() with ordering",
  "failing_tests": [
    "tests.queries.test_distinct.DistinctTest.test_distinct_with_ordering"
  ],
  "files_to_modify": [
    "django/db/models/query.py",
    "django/db/models/sql/query.py"
  ],
  "difficulty": "medium",
  "estimated_turns": 8
}
```

### 2. Interactive Code Debugging (InterCode)

InterCode provides interactive coding environments where agents can execute code and receive immediate feedback.

#### Configuration Example

```yaml
# intercode_config.yaml
model_id: "claude-3-sonnet"
task_ids:
  - "intercode_python_basic_001"
  - "intercode_python_intermediate_002"
  - "intercode_bash_scripting_001"
  - "intercode_sql_queries_001"

max_turns: 12
timeout_seconds: 3600

feedback_strategy: "full"
safety_level: "moderate"

feedback_config:
  context_strategy: "full"
  max_feedback_length: 12000
  enable_stack_summarization: true
  enable_file_context: true

safety_config:
  allowed_tools: ["python", "bash", "sqlite3", "psql"]
  enable_sandboxing: true
  max_execution_time: 120
  dangerous_patterns:
    - "rm -rf"
    - "del /f /q"
    - "format"
    - "eval("

export_config:
  formats: ["json", "yaml"]
  include_execution_logs: true

metadata:
  scenario: "intercode"
  experiment_name: "interactive_coding_evaluation"
  focus_areas: ["debugging", "algorithm_implementation", "data_processing"]
```

#### CLI Usage

```bash
# Run InterCode evaluation
multi-turn run-config intercode_config.yaml

# Run specific InterCode environment
multi-turn run \
  --model-id claude-3-sonnet \
  --task-id intercode_python_basic_001 \
  --max-turns 12 \
  --feedback-strategy full \
  --interactive

# List available InterCode tasks
multi-turn list-tasks --category intercode
```

#### Expected Workflow

1. **Problem Understanding**: Analyze the coding challenge
2. **Initial Implementation**: Write initial code solution
3. **Execution & Feedback**: Run code and analyze output/errors
4. **Iterative Debugging**: Fix issues based on execution feedback
5. **Testing**: Validate solution with test cases
6. **Optimization**: Improve performance or code quality

#### Sample Task Configuration

```json
{
  "task_id": "intercode_python_basic_001",
  "environment": "python",
  "problem_statement": "Implement a function to find the longest palindromic substring",
  "initial_code": "def longest_palindrome(s: str) -> str:\n    # TODO: Implement this function\n    pass",
  "test_cases": [
    {"input": "babad", "expected": "bab"},
    {"input": "cbbd", "expected": "bb"},
    {"input": "a", "expected": "a"}
  ],
  "success_criteria": "All test cases pass",
  "difficulty": "easy",
  "estimated_turns": 5
}
```

### 3. Conversational Code Generation (ConvCodeBench)

ConvCodeBench evaluates agents on dialogue-based programming assistance, simulating realistic developer-AI interactions.

#### Configuration Example

```yaml
# convcode_config.yaml
model_id: "gpt-4"
task_ids:
  - "convcode_web_development_001"
  - "convcode_data_analysis_002"
  - "convcode_api_integration_003"

max_turns: 20
timeout_seconds: 5400  # 1.5 hours

feedback_strategy: "adaptive"
safety_level: "moderate"

feedback_config:
  context_strategy: "adaptive"
  max_feedback_length: 10000
  enable_conversation_history: true
  conversation_window: 10  # Keep last 10 turns

safety_config:
  allowed_tools: ["python", "node", "npm", "curl", "git"]
  enable_sandboxing: true
  max_execution_time: 300

export_config:
  formats: ["json", "html"]
  include_conversation_flow: true
  generate_conversation_summary: true

metadata:
  scenario: "convcode_bench"
  experiment_name: "conversational_programming"
  interaction_style: "collaborative"
```

#### CLI Usage

```bash
# Run ConvCodeBench evaluation
multi-turn run-config convcode_config.yaml --interactive

# Run with specific conversation style
multi-turn run \
  --model-id gpt-4 \
  --task-id convcode_web_development_001 \
  --max-turns 20 \
  --enable-context-retention \
  --output convcode_results.json
```

#### Expected Workflow

1. **Initial Request**: User presents programming problem or requirement
2. **Clarification**: Agent asks clarifying questions
3. **Solution Planning**: Discuss approach and architecture
4. **Iterative Development**: Code generation with user feedback
5. **Testing & Refinement**: Test code and make improvements
6. **Documentation**: Generate documentation and usage examples

#### Sample Task Configuration

```json
{
  "task_id": "convcode_web_development_001",
  "scenario": "Build a REST API for a todo application",
  "initial_user_message": "I need to create a REST API for managing todo items. Can you help me build this?",
  "conversation_flow": [
    {
      "turn": 1,
      "user": "I need to create a REST API for managing todo items. Can you help me build this?",
      "expected_agent_actions": ["ask_clarifying_questions", "suggest_technology_stack"]
    },
    {
      "turn": 2,
      "user": "I want to use Python with Flask. The todos should have title, description, and completion status.",
      "expected_agent_actions": ["create_project_structure", "implement_basic_models"]
    }
  ],
  "success_criteria": [
    "Working REST API with CRUD operations",
    "Proper error handling",
    "Basic tests included",
    "Clear documentation"
  ],
  "difficulty": "medium",
  "estimated_turns": 15
}
```

### 4. Cross-Language Bug Fixing (BugsInPy, Defects4J)

Evaluate agents on language-specific debugging challenges with real-world bugs from open-source projects.

#### Configuration Example

```yaml
# cross_language_config.yaml
model_id: "claude-3-sonnet"
task_ids:
  # Python bugs from BugsInPy
  - "bugs_in_py_pandas_001"
  - "bugs_in_py_numpy_002"
  - "bugs_in_py_requests_003"
  # Java bugs from Defects4J
  - "defects4j_commons_lang_001"
  - "defects4j_commons_math_002"
  - "defects4j_gson_003"

max_turns: 18
timeout_seconds: 9000  # 2.5 hours

feedback_strategy: "full"
safety_level: "moderate"

feedback_config:
  context_strategy: "adaptive"
  max_feedback_length: 20000
  enable_stack_summarization: true
  enable_file_context: true
  language_specific_processing: true

safety_config:
  allowed_tools: ["python", "java", "javac", "maven", "gradle", "pytest", "junit"]
  enable_sandboxing: true
  max_execution_time: 900

export_config:
  formats: ["json", "csv", "xml"]
  include_language_metrics: true
  cross_language_analysis: true

metadata:
  scenario: "cross_language_debugging"
  experiment_name: "multi_language_bug_fixing"
  languages: ["python", "java"]
  focus: "real_world_bugs"
```

#### CLI Usage

```bash
# Run cross-language evaluation
multi-turn run-config cross_language_config.yaml

# Run Python-specific bugs
multi-turn run \
  --model-id claude-3-sonnet \
  --task-id bugs_in_py_pandas_001 \
  --task-id bugs_in_py_numpy_002 \
  --max-turns 18 \
  --safety-level moderate

# Run Java-specific bugs
multi-turn run \
  --model-id gpt-4 \
  --task-id defects4j_commons_lang_001 \
  --max-turns 15 \
  --output java_results.json
```

#### Expected Workflow

1. **Bug Analysis**: Understand the reported bug and symptoms
2. **Environment Setup**: Configure language-specific tools and dependencies
3. **Reproduction**: Reproduce the bug using provided test cases
4. **Root Cause Analysis**: Identify the underlying cause
5. **Fix Implementation**: Develop and apply the fix
6. **Validation**: Ensure fix resolves issue without breaking other functionality

#### Sample Task Configurations

**BugsInPy Task:**
```json
{
  "task_id": "bugs_in_py_pandas_001",
  "language": "python",
  "project": "pandas",
  "version": "1.2.0",
  "bug_description": "DataFrame.groupby().sum() returns incorrect results with NaN values",
  "failing_test": "pandas/tests/groupby/test_groupby.py::test_sum_with_nan",
  "files_involved": [
    "pandas/core/groupby/groupby.py",
    "pandas/core/groupby/ops.py"
  ],
  "bug_type": "logic_error",
  "difficulty": "medium"
}
```

**Defects4J Task:**
```json
{
  "task_id": "defects4j_commons_lang_001",
  "language": "java",
  "project": "commons-lang",
  "version": "3.1",
  "bug_description": "StringUtils.isNumeric() incorrectly handles empty strings",
  "failing_test": "org.apache.commons.lang3.StringUtilsTest::testIsNumeric_String",
  "files_involved": [
    "src/main/java/org/apache/commons/lang3/StringUtils.java"
  ],
  "bug_type": "boundary_condition",
  "difficulty": "easy"
}
```

### 5. Requirement Clarification

Evaluate agents on their ability to gather and clarify ambiguous requirements through interactive dialogue.

#### Configuration Example

```yaml
# requirement_clarification_config.yaml
model_id: "gpt-4"
task_ids:
  - "req_clarification_ecommerce_001"
  - "req_clarification_mobile_app_002"
  - "req_clarification_data_pipeline_003"

max_turns: 25
timeout_seconds: 3600

feedback_strategy: "adaptive"
safety_level: "permissive"  # More lenient for requirement gathering

feedback_config:
  context_strategy: "full"
  max_feedback_length: 8000
  enable_conversation_history: true
  conversation_window: 15
  stakeholder_simulation: true

safety_config:
  allowed_tools: ["documentation_generator", "diagram_creator", "requirement_validator"]
  enable_sandboxing: false  # Not needed for requirement gathering

export_config:
  formats: ["json", "markdown", "pdf"]
  include_requirement_trace: true
  generate_specification_document: true

metadata:
  scenario: "requirement_clarification"
  experiment_name: "requirement_gathering_evaluation"
  stakeholder_types: ["product_owner", "end_user", "technical_lead"]
```

#### CLI Usage

```bash
# Run requirement clarification evaluation
multi-turn run-config requirement_clarification_config.yaml --interactive

# Run specific requirement scenario
multi-turn run \
  --model-id gpt-4 \
  --task-id req_clarification_ecommerce_001 \
  --max-turns 25 \
  --enable-context-retention \
  --output requirements_results.json
```

#### Expected Workflow

1. **Initial Requirement**: Receive vague or incomplete requirement
2. **Stakeholder Identification**: Identify key stakeholders to consult
3. **Question Generation**: Ask targeted clarifying questions
4. **Information Gathering**: Collect detailed requirements through dialogue
5. **Requirement Validation**: Confirm understanding with stakeholders
6. **Documentation**: Generate clear, comprehensive requirement specification

#### Sample Task Configuration

```json
{
  "task_id": "req_clarification_ecommerce_001",
  "initial_requirement": "We need an e-commerce website that can handle online sales",
  "stakeholders": [
    {
      "role": "product_owner",
      "knowledge_areas": ["business_goals", "user_needs", "market_requirements"],
      "communication_style": "business_focused"
    },
    {
      "role": "end_user",
      "knowledge_areas": ["user_experience", "pain_points", "preferences"],
      "communication_style": "casual"
    },
    {
      "role": "technical_lead",
      "knowledge_areas": ["technical_constraints", "architecture", "scalability"],
      "communication_style": "technical"
    }
  ],
  "hidden_requirements": [
    "Must support mobile devices",
    "Integration with existing inventory system required",
    "Multi-currency support needed",
    "GDPR compliance required"
  ],
  "success_criteria": [
    "All hidden requirements discovered",
    "Clear functional requirements documented",
    "Non-functional requirements identified",
    "Stakeholder sign-off obtained"
  ],
  "difficulty": "hard",
  "estimated_turns": 20
}
```

### 6. Custom Evaluation Scenarios

Create domain-specific evaluation scenarios tailored to your specific use cases.

#### Configuration Example

```yaml
# custom_scenario_config.yaml
model_id: "your-custom-model"
task_ids:
  - "custom_financial_analysis_001"
  - "custom_medical_diagnosis_002"
  - "custom_legal_research_003"

max_turns: 30
timeout_seconds: 10800  # 3 hours

feedback_strategy: "custom"
safety_level: "strict"  # Higher safety for sensitive domains

feedback_config:
  context_strategy: "domain_specific"
  max_feedback_length: 25000
  domain_specific_processing: true
  expert_validation: true

safety_config:
  allowed_tools: ["domain_specific_tool_1", "domain_specific_tool_2"]
  enable_sandboxing: true
  max_execution_time: 1800
  domain_safety_policies: ["financial_compliance", "medical_privacy", "legal_ethics"]

custom_metrics:
  - name: "domain_accuracy"
    calculator: "custom_domain_accuracy"
    weight: 0.4
  - name: "expert_agreement"
    calculator: "expert_validation"
    weight: 0.3
  - name: "compliance_score"
    calculator: "compliance_checker"
    weight: 0.3

export_config:
  formats: ["json", "pdf", "xml"]
  include_expert_annotations: true
  generate_compliance_report: true

metadata:
  scenario: "custom_domain"
  experiment_name: "domain_specific_evaluation"
  domain: "financial_analysis"
  compliance_requirements: ["SOX", "GDPR", "PCI_DSS"]
```

#### Creating Custom Tasks

```python
# custom_task_example.py
from EvaluationEngineV1_0.core.scenario_environments import UnifiedEnv
from EvaluationEngineV1_0.core.data_models import MultiTurnTask

class CustomFinancialAnalysisTask(MultiTurnTask):
    """Custom task for financial analysis evaluation."""
    
    def __init__(self, task_config):
        super().__init__(task_config)
        self.financial_data = task_config['financial_data']
        self.analysis_requirements = task_config['analysis_requirements']
    
    def create_environment(self, config):
        return CustomFinancialEnvironment(config, self.financial_data)
    
    def get_initial_context(self):
        return {
            'financial_data_summary': self.financial_data['summary'],
            'analysis_objectives': self.analysis_requirements,
            'available_tools': ['financial_calculator', 'chart_generator', 'report_writer']
        }

class CustomFinancialEnvironment(UnifiedEnv):
    """Custom environment for financial analysis tasks."""
    
    def __init__(self, config, financial_data):
        super().__init__(config)
        self.financial_data = financial_data
        self.analysis_state = {}
        self.compliance_checker = ComplianceChecker()
    
    def step(self, action):
        # Implement custom step logic
        if action['type'] == 'analyze_financial_data':
            result = self._analyze_data(action['parameters'])
            observation = {'analysis_result': result}
            reward = self._calculate_analysis_reward(result)
            done = self._check_analysis_complete()
            info = {'compliance_status': self.compliance_checker.check(result)}
            return observation, reward, done, info
        
        # Handle other action types...
```

## Configuration Examples

### Baseline Configurations

#### Regression Testing Configuration
```yaml
# regression_baseline.yaml
model_id: "baseline-model"
task_ids:
  - "regression_test_suite_001"
  - "regression_test_suite_002"

max_turns: 5
timeout_seconds: 1800
feedback_strategy: "minimal"
safety_level: "moderate"

metadata:
  baseline_type: "regression"
  purpose: "Ensure no performance degradation"
  comparison_baseline: "previous_version"
```

#### Mid-Fidelity Configuration
```yaml
# mid_fidelity_baseline.yaml
model_id: "production-model"
task_ids:
  - "representative_task_sample"

max_turns: 10
timeout_seconds: 3600
feedback_strategy: "adaptive"
safety_level: "moderate"

feedback_config:
  context_strategy: "adaptive"
  max_feedback_length: 10000

metadata:
  baseline_type: "mid_fidelity"
  purpose: "Balanced evaluation for regular testing"
  sample_size: "medium"
```

#### Milestone Configuration
```yaml
# milestone_baseline.yaml
model_id: "candidate-model"
task_ids:
  - "comprehensive_task_suite"

max_turns: 20
timeout_seconds: 7200
feedback_strategy: "full"
safety_level: "strict"

feedback_config:
  context_strategy: "full"
  max_feedback_length: 20000
  enable_all_features: true

custom_metrics:
  - name: "comprehensive_analysis"
    calculator: "full_analysis"
    weight: 1.0

metadata:
  baseline_type: "milestone"
  purpose: "Comprehensive evaluation for major releases"
  thoroughness: "maximum"
```

## CLI Usage Examples

### Basic Commands

```bash
# List available tasks
multi-turn list-tasks

# Describe specific task
multi-turn describe-task swe_bench_lite_001

# Validate configuration
multi-turn validate-config config.yaml

# Run evaluation
multi-turn run-config config.yaml

# Monitor evaluation
multi-turn monitor --host localhost --port 8000
```

### Advanced CLI Usage

```bash
# Run with custom parameters
multi-turn run \
  --model-id gpt-4 \
  --task-id swe_bench_lite_001 \
  --task-id intercode_python_001 \
  --max-turns 15 \
  --timeout 7200 \
  --feedback-strategy adaptive \
  --safety-level moderate \
  --output results.json \
  --format json \
  --interactive

# Batch evaluation with multiple configurations
for config in configs/*.yaml; do
  echo "Running evaluation with $config"
  multi-turn run-config "$config" --output "results/$(basename $config .yaml)_results.json"
done

# Export results in different formats
multi-turn export \
  --input results.json \
  --output report.pdf \
  --format pdf \
  --include-charts \
  --include-summary

# Generate configuration from template
multi-turn init-config \
  --output advanced_config.yaml \
  --template advanced \
  --model-id gpt-4 \
  --scenario swe_bench
```

## API Usage Examples

### REST API Examples

#### Create Evaluation

```python
import requests
import json

# Create evaluation
evaluation_request = {
    "model_id": "gpt-4",
    "task_ids": ["swe_bench_lite_001", "intercode_python_001"],
    "max_turns": 10,
    "timeout_seconds": 3600,
    "feedback_strategy": "adaptive",
    "safety_level": "moderate",
    "enable_context_retention": True,
    "metadata": {
        "experiment_name": "api_test_evaluation",
        "researcher": "api_user"
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/multi-turn/evaluations",
    headers={
        "Authorization": "Bearer your_token_here",
        "Content-Type": "application/json"
    },
    json=evaluation_request
)

evaluation_data = response.json()
evaluation_id = evaluation_data["evaluation_id"]
print(f"Created evaluation: {evaluation_id}")
```

#### Monitor Evaluation

```python
import time

# Monitor evaluation progress
while True:
    status_response = requests.get(
        f"http://localhost:8000/api/v1/multi-turn/evaluations/{evaluation_id}/status",
        headers={"Authorization": "Bearer your_token_here"}
    )
    
    status_data = status_response.json()
    print(f"Status: {status_data['status']}, Progress: {status_data['progress']:.2%}")
    
    if status_data["status"] in ["completed", "failed", "cancelled"]:
        break
    
    time.sleep(30)  # Check every 30 seconds
```

#### Get Results

```python
# Get evaluation results
results_response = requests.get(
    f"http://localhost:8000/api/v1/multi-turn/evaluations/{evaluation_id}/results",
    headers={"Authorization": "Bearer your_token_here"}
)

results_data = results_response.json()
print(f"Overall success rate: {results_data['overall_success_rate']:.2%}")
print(f"Average turns per task: {results_data['average_turns_per_task']:.1f}")
print(f"Total cost: ${results_data['total_cost']:.2f}")
```

### WebSocket Usage

```javascript
// WebSocket connection for real-time updates
const ws = new WebSocket(`ws://localhost:8000/ws/multi-turn/${evaluationId}`, [], {
    headers: {
        'Authorization': 'Bearer your_token_here'
    }
});

ws.onopen = function(event) {
    console.log('WebSocket connected');
    
    // Subscribe to evaluation progress
    ws.send(JSON.stringify({
        type: 'subscribe',
        subscription_type: 'evaluation',
        evaluation_id: evaluationId
    }));
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'evaluation_progress':
            console.log(`Progress: ${message.data.progress}%`);
            updateProgressBar(message.data.progress);
            break;
            
        case 'turn_executed':
            console.log(`Turn ${message.data.turn_number} completed`);
            displayTurnResult(message.data);
            break;
            
        case 'evaluation_completed':
            console.log('Evaluation completed!');
            displayFinalResults(message.data);
            break;
            
        case 'safety_incident':
            console.warn('Safety incident detected:', message.data);
            handleSafetyIncident(message.data);
            break;
    }
};
```

### Python SDK Usage

```python
from evaluation_engine_sdk import MultiTurnEvaluationClient

# Initialize client
client = MultiTurnEvaluationClient(
    base_url="http://localhost:8000",
    api_token="your_token_here"
)

# Create and run evaluation
evaluation = client.create_evaluation(
    model_id="gpt-4",
    task_ids=["swe_bench_lite_001"],
    max_turns=10,
    feedback_strategy="adaptive"
)

# Wait for completion with progress updates
for progress_update in client.monitor_evaluation(evaluation.id):
    print(f"Progress: {progress_update.progress:.1%}")
    if progress_update.current_task:
        print(f"Current task: {progress_update.current_task}")

# Get results
results = client.get_results(evaluation.id)
print(f"Success rate: {results.overall_success_rate:.2%}")

# Export results
client.export_results(
    evaluation.id,
    format="pdf",
    output_path="evaluation_report.pdf"
)
```

## Custom Agent Integration

### Agent Interface Implementation

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class CustomAgent(ABC):
    """Base class for custom agent implementations."""
    
    @abstractmethod
    async def generate_action(self, 
                            observation: Dict[str, Any], 
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate next action based on observation and context."""
        pass
    
    @abstractmethod
    def reset(self):
        """Reset agent state for new evaluation."""
        pass

class MyCustomAgent(CustomAgent):
    """Example custom agent implementation."""
    
    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.conversation_history = []
        self.current_strategy = "exploration"
    
    async def generate_action(self, observation, context):
        # Add observation to history
        self.conversation_history.append({
            'type': 'observation',
            'content': observation,
            'timestamp': time.time()
        })
        
        # Analyze current situation
        situation_analysis = self._analyze_situation(observation, context)
        
        # Choose strategy based on analysis
        if situation_analysis['needs_exploration']:
            action = self._generate_exploration_action(observation)
        elif situation_analysis['needs_implementation']:
            action = self._generate_implementation_action(observation)
        else:
            action = self._generate_refinement_action(observation)
        
        # Add action to history
        self.conversation_history.append({
            'type': 'action',
            'content': action,
            'timestamp': time.time()
        })
        
        return action
    
    def _analyze_situation(self, observation, context):
        """Analyze current situation to determine strategy."""
        return {
            'needs_exploration': 'error' in observation and not self._has_explored_recently(),
            'needs_implementation': 'task_description' in observation and not self._has_implementation(),
            'needs_refinement': 'test_results' in observation and not observation.get('all_tests_passed', False)
        }
    
    def _generate_exploration_action(self, observation):
        """Generate action for exploration phase."""
        if 'file_list' in observation:
            return {
                'type': 'read_file',
                'filename': self._select_most_relevant_file(observation['file_list'])
            }
        else:
            return {
                'type': 'list_files',
                'directory': '.'
            }
    
    def _generate_implementation_action(self, observation):
        """Generate action for implementation phase."""
        return {
            'type': 'write_code',
            'filename': self._determine_target_file(observation),
            'content': self._generate_code_solution(observation)
        }
    
    def _generate_refinement_action(self, observation):
        """Generate action for refinement phase."""
        if 'test_failures' in observation:
            return {
                'type': 'fix_code',
                'filename': self._identify_buggy_file(observation['test_failures']),
                'fix_strategy': self._determine_fix_strategy(observation['test_failures'])
            }
        else:
            return {
                'type': 'run_tests',
                'test_suite': 'all'
            }
```

### Agent Registration

```python
from evaluation_engine import register_custom_agent

# Register your custom agent
register_custom_agent(
    agent_name="my_custom_agent",
    agent_class=MyCustomAgent,
    default_config={
        'temperature': 0.7,
        'max_tokens': 2000,
        'strategy': 'adaptive'
    }
)

# Use in evaluation configuration
config = {
    'model_id': 'my_custom_agent',
    'model_config': {
        'temperature': 0.5,
        'strategy': 'conservative'
    },
    'task_ids': ['swe_bench_lite_001']
}
```

## Metrics Analysis

### Understanding Metrics

The evaluation engine provides comprehensive metrics across multiple dimensions:

#### Task Success Metrics
- **Resolved%**: Percentage of tasks completed successfully
- **Recall**: Ability to identify and address all aspects of a task
- **MRR (Mean Reciprocal Rank)**: Quality of solution ranking

#### Efficiency Metrics
- **Average Turns**: Mean number of interaction turns per task
- **Average Steps**: Mean number of actions per task
- **Redundancy Rate**: Percentage of redundant or unnecessary actions

#### Quality Metrics
- **Edit Churn**: Amount of code modification relative to final solution
- **Files Touched**: Number of files modified during evaluation
- **Solution Elegance**: Measure of solution simplicity and effectiveness

#### Cost Metrics
- **Wall Time per Solved**: Average time spent per successfully completed task
- **Tokens per Solved**: Average token usage per successful completion
- **Cost per Solved**: Average monetary cost per successful task

### Metrics Analysis Examples

```python
import pandas as pd
import matplotlib.pyplot as plt
from evaluation_engine.analysis import MetricsAnalyzer

# Load evaluation results
results = pd.read_json('evaluation_results.json')

# Initialize metrics analyzer
analyzer = MetricsAnalyzer(results)

# Generate comprehensive analysis
analysis = analyzer.generate_comprehensive_analysis()

# Plot success rate by task category
analyzer.plot_success_rate_by_category()
plt.title('Success Rate by Task Category')
plt.show()

# Analyze efficiency trends
efficiency_analysis = analyzer.analyze_efficiency_trends()
print(f"Average turns per task: {efficiency_analysis['avg_turns']:.1f}")
print(f"Redundancy rate: {efficiency_analysis['redundancy_rate']:.2%}")

# Cost analysis
cost_analysis = analyzer.analyze_costs()
print(f"Total cost: ${cost_analysis['total_cost']:.2f}")
print(f"Cost per successful task: ${cost_analysis['cost_per_success']:.2f}")

# Generate comparison report
comparison_report = analyzer.compare_with_baseline('baseline_results.json')
analyzer.export_comparison_report(comparison_report, 'comparison_report.pdf')
```

### Custom Metrics Implementation

```python
from evaluation_engine.metrics import CustomMetricsCalculator

class DomainSpecificMetrics(CustomMetricsCalculator):
    """Custom metrics for domain-specific evaluation."""
    
    def calculate_domain_accuracy(self, turn_results):
        """Calculate domain-specific accuracy metric."""
        correct_predictions = 0
        total_predictions = 0
        
        for turn in turn_results:
            if 'domain_prediction' in turn.info:
                total_predictions += 1
                if turn.info['domain_prediction'] == turn.info['ground_truth']:
                    correct_predictions += 1
        
        return correct_predictions / total_predictions if total_predictions > 0 else 0.0
    
    def calculate_expert_agreement(self, turn_results):
        """Calculate agreement with expert annotations."""
        agreements = []
        
        for turn in turn_results:
            if 'expert_annotation' in turn.info and 'agent_response' in turn.info:
                agreement = self._calculate_semantic_similarity(
                    turn.info['expert_annotation'],
                    turn.info['agent_response']
                )
                agreements.append(agreement)
        
        return sum(agreements) / len(agreements) if agreements else 0.0

# Register custom metrics
from evaluation_engine import register_custom_metrics

register_custom_metrics('domain_specific', DomainSpecificMetrics())
```

## Best Practices

### Configuration Best Practices

1. **Start with Templates**: Use provided templates as starting points
2. **Incremental Complexity**: Begin with simple configurations and gradually add complexity
3. **Environment-Specific Settings**: Adjust timeouts and resource limits based on your environment
4. **Safety First**: Always configure appropriate safety measures for your use case
5. **Metadata Documentation**: Include comprehensive metadata for tracking and analysis

### Evaluation Best Practices

1. **Baseline Establishment**: Always establish baseline performance before making changes
2. **Reproducible Configurations**: Use version-controlled configuration files
3. **Comprehensive Logging**: Enable detailed logging for debugging and analysis
4. **Regular Monitoring**: Monitor evaluations in real-time to catch issues early
5. **Result Validation**: Validate results against expected outcomes

### Performance Best Practices

1. **Resource Management**: Monitor and limit resource usage appropriately
2. **Parallel Execution**: Use parallel evaluation for independent tasks
3. **Caching**: Enable caching for repeated operations
4. **Batch Processing**: Group similar tasks for efficient processing
5. **Cleanup**: Regularly clean up old evaluation data and logs

### Security Best Practices

1. **Principle of Least Privilege**: Grant minimal necessary permissions
2. **Input Validation**: Validate all inputs and configurations
3. **Secure Communication**: Use HTTPS and secure WebSocket connections
4. **Token Management**: Rotate API tokens regularly
5. **Audit Logging**: Maintain comprehensive audit logs

## Advanced Usage

### Custom Adapter Development

```python
from evaluation_engine.adapters import BenchmarkAdapter

class MyCustomBenchmarkAdapter(BenchmarkAdapter):
    """Custom adapter for proprietary benchmark."""
    
    def __init__(self, config):
        super().__init__(config)
        self.benchmark_client = MyBenchmarkClient(config['api_key'])
    
    def load_tasks(self, task_filter=None):
        """Load tasks from custom benchmark."""
        raw_tasks = self.benchmark_client.get_tasks(task_filter)
        return [self._convert_task(task) for task in raw_tasks]
    
    def create_environment(self, task_config):
        """Create custom environment."""
        return MyCustomEnvironment(task_config, self.benchmark_client)
    
    def convert_results(self, results):
        """Convert results to standard format."""
        return StandardizedResult(
            task_id=results['id'],
            success=results['passed'],
            score=results['score'],
            metrics=results['metrics'],
            execution_time=results['duration']
        )

# Register custom adapter
from evaluation_engine import register_adapter
register_adapter('my_benchmark', MyCustomBenchmarkAdapter)
```

### Distributed Evaluation

```yaml
# distributed_config.yaml
distributed_execution:
  enabled: true
  worker_nodes:
    - host: "worker1.example.com"
      port: 8001
      capacity: 4
    - host: "worker2.example.com"
      port: 8001
      capacity: 4
  
  load_balancing: "round_robin"
  fault_tolerance: true
  result_aggregation: "centralized"

task_distribution:
  strategy: "by_complexity"
  max_tasks_per_worker: 2
  timeout_multiplier: 1.5
```

### Integration with CI/CD

```yaml
# .github/workflows/evaluation.yml
name: Multi-Turn Evaluation

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install multi-turn-evaluation-engine
        pip install -r requirements.txt
    
    - name: Run evaluation
      run: |
        multi-turn run-config ci_config.yaml --output results.json
      env:
        EVALUATION_API_KEY: ${{ secrets.EVALUATION_API_KEY }}
    
    - name: Upload results
      uses: actions/upload-artifact@v2
      with:
        name: evaluation-results
        path: results.json
    
    - name: Generate report
      run: |
        multi-turn export --input results.json --output report.html --format html
    
    - name: Comment PR
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const results = JSON.parse(fs.readFileSync('results.json'));
          const comment = `## Evaluation Results
          
          - Success Rate: ${(results.overall_success_rate * 100).toFixed(1)}%
          - Average Turns: ${results.average_turns_per_task.toFixed(1)}
          - Total Cost: $${results.total_cost.toFixed(2)}
          
          [Full Report](${results.report_url})`;
          
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          });
```

This comprehensive usage guide provides detailed examples and best practices for all six evaluation scenarios supported by the Multi-Turn Evaluation Engine. Use these examples as starting points for your own evaluations, and adapt them to your specific requirements and use cases.