# AI Evaluation Engine - lm-evaluation-harness Integration

This document describes how the AI Evaluation Engine extends and integrates with the lm-evaluation-harness framework.

## Overview

The AI Evaluation Engine is built as an extension of the lm-evaluation-harness (lm-eval) framework, maintaining full backward compatibility while adding advanced evaluation capabilities including:

- Multi-turn conversation evaluation
- Secure code execution environments
- Advanced metrics and analysis
- Business scenario-specific evaluations
- Extended model adapter support

## Architecture Integration

### Core Integration Points

1. **Task Registry Extension**: Our `ExtendedTaskRegistry` builds upon lm-eval's task registry
2. **Model Adapter Framework**: Extended model adapters for additional providers
3. **Evaluation Engine**: `UnifiedEvaluationFramework` wraps lm-eval's `simple_evaluate`
4. **Task Classes**: `AdvancedTask` and `MultiTurnTask` extend lm-eval's `Task` class

### Directory Structure

```
lm_eval/
├── tasks/                          # lm-eval task directory
│   ├── single_turn_scenarios/      # Our single-turn evaluations
│   ├── multi_turn_scenarios/       # Our multi-turn evaluations
│   ├── python_coding/              # Python-specific coding tasks
│   └── multi_turn_coding/          # Multi-turn coding scenarios
evaluation_engine/
├── core/
│   ├── unified_framework.py        # Main evaluation framework
│   └── task_registration.py        # Extended task registry
```

## Task Integration

### Single-Turn Tasks

All single-turn tasks follow lm-eval conventions and are fully compatible:

```python
from lm_eval.api.task import Task
from lm_eval.api.registry import register_task

@register_task("single_turn_scenarios_function_generation")
class FunctionGenerationTask(Task):
    VERSION = 1.0
    DATASET_PATH = "problems.jsonl"
    
    def has_training_docs(self):
        return False
    
    def has_validation_docs(self):
        return False
    
    def has_test_docs(self):
        return True
```

### Multi-Turn Tasks

Multi-turn tasks extend the base functionality:

```python
from evaluation_engine.core.task_registration import MultiTurnTask, register_multi_turn_task

@register_multi_turn_task(
    "multi_turn_scenarios_code_review",
    scenario_config=ScenarioConfig(
        scenario_id="code_review",
        scenario_type="multi_turn",
        max_turns=5,
        conversation_timeout=300,
        enable_context_retention=True
    )
)
class CodeReviewTask(MultiTurnTask):
    def _execute_turn(self, turn_data):
        # Multi-turn specific logic
        pass
```

## Usage Examples

### Basic lm-eval Compatible Usage

```bash
# Standard lm-eval command line interface
python -m lm_eval \
    --model claude_local \
    --tasks single_turn_scenarios_function_generation \
    --limit 10 \
    --log_samples

# Multiple tasks
python -m lm_eval \
    --model openai-chat-completions \
    --model_args model=gpt-4 \
    --tasks single_turn_scenarios_code_completion,single_turn_scenarios_bug_fix \
    --batch_size 1
```

### Extended Framework Usage

```python
from evaluation_engine.core.unified_framework import unified_framework, EvaluationRequest

# Create evaluation request
request = EvaluationRequest(
    model="claude_local",
    tasks=["single_turn_scenarios_function_generation"],
    limit=10,
    log_samples=True
)

# Run evaluation
result = unified_framework.evaluate(request)

# Access results
print(f"Status: {result.status}")
print(f"Metrics: {result.metrics_summary}")
print(f"Analysis: {result.analysis}")
```

### Multi-Turn Evaluation

```python
# Multi-turn scenario evaluation
request = EvaluationRequest(
    model="claude_local",
    tasks=["multi_turn_scenarios_code_review"],
    limit=5
)

result = unified_framework.evaluate(request)

# Multi-turn specific analysis
for task_name, analysis in result.analysis["task_analysis"].items():
    print(f"Task: {task_name}")
    print(f"Performance: {analysis['performance_level']}")
    print(f"Strengths: {analysis['strengths']}")
```

## Model Adapter Integration

### Supported Models

The system extends lm-eval's model support:

```python
# OpenAI models (lm-eval native)
python -m lm_eval --model openai-chat-completions --model_args model=gpt-4

# Anthropic models (our extension)
python -m lm_eval --model claude_local

# DashScope models (our extension)
python -m lm_eval --model dashscope --model_args model=qwen-max

# DeepSeek models (our extension)
python -m lm_eval --model deepseek --model_args model=deepseek-coder

# HuggingFace models (lm-eval native)
python -m lm_eval --model hf --model_args pretrained=microsoft/DialoGPT-medium
```

### Custom Model Adapters

```python
from lm_eval.api.model import LM
from lm_eval.api.registry import register_model

@register_model("my_custom_model")
class MyCustomModel(LM):
    def __init__(self, **kwargs):
        super().__init__()
        # Initialize your model
    
    def generate_until(self, requests):
        # Implement generation logic
        pass
    
    def loglikelihood(self, requests):
        # Implement loglikelihood calculation
        pass
```

## Configuration Integration

### Task Configuration

Tasks can be configured using YAML files that extend lm-eval's configuration:

```yaml
# single_turn_scenarios/function_generation.yaml
task: single_turn_scenarios_function_generation
dataset_path: problems.jsonl
description: "Generate Python functions from specifications"

# Extended configuration
metadata:
  category: "single_turn_scenarios"
  difficulty: "intermediate"
  tags: ["python", "function_generation", "coding"]
  estimated_time: 300

context_modes:
  - no_context
  - minimal_context
  - full_context

metrics:
  - syntax_validity
  - functional_correctness
  - code_quality
```

### Multi-Turn Configuration

```yaml
# multi_turn_scenarios/code_review.yaml
task: multi_turn_scenarios_code_review
dataset_path: scenarios.jsonl
description: "Interactive code review process"

scenario_config:
  max_turns: 5
  conversation_timeout: 300
  enable_context_retention: true

turns:
  - turn_id: "initial_review"
    prompt_template: "templates/initial_review.txt"
    expected_format: "structured_feedback"
  - turn_id: "code_revision"
    prompt_template: "templates/code_revision.txt"
    depends_on: ["initial_review"]

metrics:
  - review_thoroughness
  - improvement_quality
  - code_standards_compliance
```

## Data Format Integration

### Single-Turn Data Format

Compatible with lm-eval's JSONL format:

```jsonl
{"input": "Write a function to calculate fibonacci numbers", "output": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)", "metadata": {"difficulty": "easy", "language": "python"}}
```

### Multi-Turn Data Format

Extended format for conversation scenarios:

```jsonl
{
  "scenario_id": "code_review_001",
  "initial_context": "Review this Python function for bugs and improvements",
  "turns": [
    {
      "turn": 1,
      "input": "def process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n    return result",
      "expected_response_type": "code_review"
    },
    {
      "turn": 2,
      "input": "Please implement the suggested improvements",
      "expected_response_type": "code_implementation"
    }
  ],
  "success_criteria": {
    "identifies_issues": 0.8,
    "provides_solutions": 0.7,
    "code_quality": 0.9
  }
}
```

## Metrics Integration

### Standard lm-eval Metrics

All standard lm-eval metrics are supported:

- `exact_match`
- `bleu`
- `rouge`
- `bertscore`

### Extended Metrics

Additional metrics for code evaluation:

```python
from evaluation_engine.metrics import CodeMetrics

metrics = CodeMetrics()

# Code-specific metrics
syntax_score = metrics.calculate_syntax_validity(code)
functional_score = metrics.calculate_functional_correctness(code, test_cases)
quality_score = metrics.calculate_code_quality(code)

# Multi-turn metrics
context_retention = metrics.calculate_context_retention(conversation)
goal_achievement = metrics.calculate_goal_achievement(conversation, criteria)
```

## Testing Integration

### lm-eval Compatibility Tests

```python
# Test basic lm-eval functionality
def test_lm_eval_compatibility():
    from lm_eval.api.registry import get_task_dict
    from lm_eval.evaluator import simple_evaluate
    
    # Test task discovery
    tasks = get_task_dict()
    assert len(tasks) > 0
    
    # Test evaluation
    results = simple_evaluate(
        model="dummy",
        tasks=["single_turn_scenarios_function_generation"],
        limit=1
    )
    assert "results" in results

# Test extended functionality
def test_extended_functionality():
    from evaluation_engine.core.unified_framework import unified_framework
    
    # Test framework
    tasks = unified_framework.list_available_tasks()
    assert len(tasks) > 0
    
    # Test evaluation
    request = EvaluationRequest(
        model="dummy",
        tasks=["single_turn_scenarios_function_generation"],
        limit=1
    )
    result = unified_framework.evaluate(request)
    assert result.status == ExecutionStatus.COMPLETED
```

## Migration Guide

### From Pure lm-eval

If you're migrating from pure lm-eval usage:

1. **No changes needed** for basic task evaluation
2. **Optional**: Use extended framework for advanced features
3. **Optional**: Add multi-turn scenarios for complex evaluations

### Adding Custom Tasks

1. **Single-turn**: Follow lm-eval conventions
2. **Multi-turn**: Use our `MultiTurnTask` class
3. **Registration**: Use our extended registry for metadata

### Configuration Migration

1. **Basic**: lm-eval YAML configs work as-is
2. **Extended**: Add metadata and scenario configs for enhanced features

## Best Practices

### Task Development

1. **Inherit from appropriate base class**: `Task` for single-turn, `MultiTurnTask` for conversations
2. **Follow lm-eval conventions**: Use standard methods and patterns
3. **Add metadata**: Enhance discoverability and organization
4. **Test compatibility**: Ensure tasks work with both frameworks

### Model Integration

1. **Use existing adapters** when possible
2. **Follow lm-eval patterns** for custom adapters
3. **Test thoroughly** with different model types
4. **Document configuration** options clearly

### Evaluation Workflows

1. **Start simple**: Use basic lm-eval commands first
2. **Add complexity gradually**: Move to extended framework for advanced features
3. **Monitor performance**: Use built-in analysis and metrics
4. **Validate results**: Cross-check with multiple evaluation methods

## Troubleshooting

### Common Issues

1. **Task not found**: Check task registration and imports
2. **Model errors**: Verify model adapter configuration
3. **Import errors**: Ensure all dependencies are installed
4. **Performance issues**: Check resource limits and batch sizes

### Debug Commands

```bash
# List available tasks
python -c "from lm_eval.api.registry import get_task_dict; print(list(get_task_dict().keys()))"

# Test task loading
python -c "from lm_eval.api.task import get_task; task = get_task('single_turn_scenarios_function_generation'); print(task)"

# Validate setup
python setup_validation.py
```

## Contributing

### Adding New Tasks

1. Create task class following lm-eval conventions
2. Add to appropriate directory (`single_turn_scenarios/` or `multi_turn_scenarios/`)
3. Register with both lm-eval and extended registry
4. Add tests and documentation
5. Update task lists and examples

### Extending Framework

1. Follow existing patterns and interfaces
2. Maintain backward compatibility with lm-eval
3. Add comprehensive tests
4. Document new features and APIs
5. Update integration examples

For more information, see the main README.md and individual task documentation.