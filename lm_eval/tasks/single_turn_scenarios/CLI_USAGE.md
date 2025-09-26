# Single Turn Scenarios CLI Usage Guide

## Overview

The `single_turn_scenarios` task provides comprehensive programming evaluation with support for multiple scenarios, languages, difficulty levels, and context modes.

## Basic Usage

### API-Based Models

#### OpenAI Models
```bash
# GPT-4 full suite evaluation
export OPENAI_API_KEY="your-openai-api-key"
lm_eval --model openai-chat \
    --model_args model=gpt-4,temperature=0.0 \
    --tasks single_turn_scenarios_suite \
    --limit 50 \
    --output_path ./results/gpt4_results.json

# GPT-3.5-turbo code completion
lm_eval --model openai-chat \
    --model_args model=gpt-3.5-turbo \
    --tasks single_turn_scenarios_code_completion \
    --limit 20
```

#### Anthropic Claude Models
```bash
# Claude-3 Sonnet evaluation
export ANTHROPIC_API_KEY="your-anthropic-api-key"
lm_eval --model anthropic \
    --model_args model=claude-3-sonnet-20240229 \
    --tasks single_turn_scenarios_algorithm_implementation \
    --limit 30 \
    --output_path ./results/claude_results.json

# Claude-3 Haiku for simple tasks
lm_eval --model anthropic \
    --model_args model=claude-3-haiku-20240307 \
    --tasks single_turn_scenarios_function_generation \
    --metadata '{"difficulty":"simple"}' \
    --limit 25
```

#### Claude Code SDK
```bash
# Claude Code with Haiku for code completion
export ANTHROPIC_API_KEY="your-anthropic-api-key"
lm_eval --model claude-code-local \
    --model_args model=claude-3-haiku-20240307 \
    --tasks single_turn_scenarios_code_completion \
    --limit 20 \
    --output_path ./results/claude_code_completion.json

# Claude Code with Sonnet for algorithm implementation
lm_eval --model claude-code-local \
    --model_args model=claude-3-sonnet-20240229,temperature=0.0 \
    --tasks single_turn_scenarios_algorithm_implementation \
    --limit 15 \
    --output_path ./results/claude_code_algorithms.json

# Claude Code with Opus for system design
lm_eval --model claude-code-local \
    --model_args model=claude-3-opus-20240229,temperature=0.1 \
    --tasks single_turn_scenarios_system_design \
    --limit 8 \
    --output_path ./results/claude_code_system_design.json
```

#### DashScope (Qwen Models)
```bash
# Qwen Coder Plus evaluation
export DASHSCOPE_API_KEY="your-dashscope-api-key"
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus,temperature=0.0 \
    --tasks single_turn_scenarios_suite \
    --limit 50 \
    --output_path ./results/qwen_results.json

# Qwen Max for complex tasks
lm_eval --model dashscope \
    --model_args model=qwen-max,temperature=0.1 \
    --tasks single_turn_scenarios_system_design \
    --metadata '{"difficulty":"complex"}' \
    --limit 15

# Qwen Turbo for high-throughput evaluation
lm_eval --model dashscope \
    --model_args model=qwen-turbo \
    --tasks single_turn_scenarios_code_completion \
    --limit 100 \
    --batch_size 15
```

### Local/HuggingFace Models
```bash
# DeepSeek Coder
lm_eval --model hf \
    --model_args pretrained=deepseek-ai/deepseek-coder-6.7b-instruct \
    --tasks single_turn_scenarios_suite \
    --output_path ./results/deepseek_results.json

# CodeLlama
lm_eval --model hf \
    --model_args pretrained=codellama/CodeLlama-7b-Instruct-hf \
    --tasks single_turn_scenarios_code_completion \
    --limit 30
```

### Run Individual Scenarios
```bash
# Code completion tasks
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus \
    --tasks single_turn_scenarios_code_completion \
    --limit 20

# Bug fixing tasks  
lm_eval --model openai-chat \
    --model_args model=gpt-4 \
    --tasks single_turn_scenarios_bug_fix \
    --limit 15

# Algorithm implementation tasks
lm_eval --model anthropic \
    --model_args model=claude-3-sonnet-20240229 \
    --tasks single_turn_scenarios_algorithm_implementation \
    --limit 25
```

### Run Multiple Scenarios
```bash
# Multiple scenarios with DashScope
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus \
    --tasks single_turn_scenarios_code_completion,single_turn_scenarios_bug_fix,single_turn_scenarios_function_generation \
    --limit 30 \
    --output_path ./results/multi_scenario.json
```

## Metadata Filtering

### Filter by Programming Language
```bash
# Python-only tasks with DashScope
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus \
    --tasks single_turn_scenarios_python \
    --limit 30

# JavaScript-specific evaluation
lm_eval --model openai-chat \
    --model_args model=gpt-4 \
    --tasks single_turn_scenarios_code_completion \
    --metadata '{"language":"javascript"}' \
    --limit 20

# Multi-language code translation
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus \
    --tasks single_turn_scenarios_code_translation \
    --metadata '{"source_language":"python","target_language":"java"}' \
    --limit 15
```

### Filter by Difficulty Level
```bash
# Intermediate difficulty with DashScope
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus \
    --tasks single_turn_scenarios_intermediate \
    --limit 40

# Complex problems with Claude
lm_eval --model anthropic \
    --model_args model=claude-3-opus-20240229 \
    --tasks single_turn_scenarios_suite \
    --metadata '{"difficulty":"complex"}' \
    --limit 20

# Simple tasks for quick evaluation
lm_eval --model dashscope \
    --model_args model=qwen-turbo \
    --tasks single_turn_scenarios_function_generation \
    --metadata '{"difficulty":"simple"}' \
    --limit 50
```

### Filter by Context Mode
```bash
# Full context evaluation with DashScope
lm_eval --model dashscope \
    --model_args model=qwen-max \
    --tasks single_turn_scenarios_system_design \
    --metadata '{"context_mode":"full_context"}' \
    --limit 10

# Minimal context for baseline comparison
lm_eval --model openai-chat \
    --model_args model=gpt-4 \
    --tasks single_turn_scenarios_minimal_context \
    --limit 30

# Domain-specific context
lm_eval --model anthropic \
    --model_args model=claude-3-sonnet-20240229 \
    --tasks single_turn_scenarios_security \
    --metadata '{"context_mode":"domain_context"}' \
    --limit 12
```

### Filter by Context Mode
```bash
# Minimal context tasks
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_minimal_context

# No context tasks
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_suite --task_config '{"dataset_kwargs": {"metadata": {"context_mode": "no_context"}}}'
```

### Complex Filtering (Multiple Criteria)
```bash
# Python intermediate difficulty with minimal context
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_suite --task_config '{"dataset_kwargs": {"metadata": {"language": "python", "difficulty": "intermediate", "context_mode": "minimal_context"}}}'

# Multiple scenarios with specific criteria
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_code_completion,single_turn_scenarios_bug_fix --task_config '{"dataset_kwargs": {"metadata": {"language": ["python", "javascript"], "difficulty": ["simple", "intermediate"]}}}'
```

## Standard lm-eval Parameters

### Limit Number of Samples (Testing Only)
```bash
# Run only 10 samples for quick testing
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_code_completion --limit 10
```

### Output Path and Logging
```bash
# Save detailed results and logs
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_suite --output_path ./results --log_samples

# Save predictions for analysis
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_suite --output_path ./results --predict_only
```

### Batch Size and Performance
```bash
# Adjust batch size for memory constraints
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_suite --batch_size 4

# Use device specification
lm_eval --model hf --model_args pretrained=model_name,device=cuda:0 --tasks single_turn_scenarios_suite
```

## Available Task Names

### Individual Scenarios
- `single_turn_scenarios_code_completion` - Code completion tasks
- `single_turn_scenarios_bug_fix` - Bug fixing tasks
- `single_turn_scenarios_code_translation` - Code translation tasks
- `single_turn_scenarios_documentation` - Documentation generation tasks
- `single_turn_scenarios_function_generation` - Function generation tasks
- `single_turn_scenarios_system_design` - System design tasks
- `single_turn_scenarios_algorithm_implementation` - Algorithm implementation tasks
- `single_turn_scenarios_api_design` - API design tasks
- `single_turn_scenarios_database_design` - Database design tasks
- `single_turn_scenarios_performance_optimization` - Performance optimization tasks
- `single_turn_scenarios_full_stack` - Full-stack development tasks
- `single_turn_scenarios_testing_strategy` - Testing strategy tasks
- `single_turn_scenarios_security` - Security-focused tasks

### Suite and Filtered Tasks
- `single_turn_scenarios_suite` - All scenarios combined
- `single_turn_scenarios_python` - Python-only tasks
- `single_turn_scenarios_intermediate` - Intermediate difficulty tasks
- `single_turn_scenarios_minimal_context` - Minimal context tasks

### Supported Filter Values

#### Languages
- `python`
- `javascript`
- `typescript`
- `java`
- `cpp`
- `go`
- `rust`

#### Difficulty Levels
- `simple` - Single-skill, direct output tasks
- `intermediate` - Multi-step thinking with structured output
- `complex` - Complete analysis→design→implementation workflows

#### Context Modes
- `no_context` - Pure problems with no additional information
- `minimal_context` - Basic constraints and requirements
- `full_context` - Complete company standards and best practices
- `domain_context` - Domain-specific professional requirements

#### Scenarios
- `code_completion`
- `bug_fix`
- `code_translation`
- `documentation`
- `function_generation`
- `system_design`
- `algorithm_implementation`
- `api_design`
- `database_design`
- `performance_optimization`
- `full_stack`
- `testing_strategy`
- `security`

## Examples for Different Use Cases

### Research Evaluation
```bash
# Comprehensive evaluation for research paper
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_suite --output_path ./research_results --log_samples

# Compare context impact
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_suite --task_config '{"dataset_kwargs": {"metadata": {"context_mode": "no_context"}}}' --output_path ./no_context_results
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_suite --task_config '{"dataset_kwargs": {"metadata": {"context_mode": "full_context"}}}' --output_path ./full_context_results
```

### Model Development
```bash
# Quick smoke test during development
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_code_completion --limit 5

# Language-specific evaluation
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_python --output_path ./python_results
```

### Production Validation
```bash
# Comprehensive production validation
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_suite --output_path ./production_validation --batch_size 8

# Security-focused evaluation
lm_eval --model hf --model_args pretrained=model_name --tasks single_turn_scenarios_security --output_path ./security_results
```

## Troubleshooting

### Common Issues

1. **Memory Issues**: Reduce `--batch_size` or use `--limit` for testing
2. **Timeout Issues**: Check sandbox configuration and increase timeout limits
3. **Missing Dependencies**: Run `./setupEvaluationEnvironment.sh` to install requirements
4. **API Key Issues**: Check `.env` file and run `python check_api_keys.py`

### Validation Commands
```bash
# Validate environment setup
python lm_eval/tasks/single_turn_scenarios/smoke_test.py

# Check dataset integrity
python lm_eval/tasks/single_turn_scenarios/validate_problems.py

# Validate configuration
python lm_eval/tasks/single_turn_scenarios/validate_config.py
```

## DashScope (Qwen Models) Configuration

### API Key Setup
```bash
# Set DashScope API key
export DASHSCOPE_API_KEY="your-dashscope-api-key"

# Verify API key format (should start with 'sk-')
echo $DASHSCOPE_API_KEY | grep -E '^sk-' && echo "✅ Valid format" || echo "❌ Invalid format"

# Test API connectivity
curl -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
     -H "Content-Type: application/json" \
     https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
```

### DashScope Model Selection
```bash
# Qwen Coder Plus (recommended for code tasks)
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus,temperature=0.0 \
    --tasks single_turn_scenarios_code_completion

# Qwen Max (for complex reasoning tasks)
lm_eval --model dashscope \
    --model_args model=qwen-max,temperature=0.1,max_tokens=4096 \
    --tasks single_turn_scenarios_system_design

# Qwen Turbo (for high-throughput evaluation)
lm_eval --model dashscope \
    --model_args model=qwen-turbo,max_tokens=1024 \
    --tasks single_turn_scenarios_function_generation \
    --batch_size 20

# Qwen Coder (specialized for code generation)
lm_eval --model dashscope \
    --model_args model=qwen-coder \
    --tasks single_turn_scenarios_bug_fix

# Qwen Plus (balanced performance and cost)
lm_eval --model dashscope \
    --model_args model=qwen-plus \
    --tasks single_turn_scenarios_documentation
```

### DashScope Performance Optimization
```bash
# High-throughput batch processing
lm_eval --model dashscope \
    --model_args model=qwen-turbo,max_tokens=512 \
    --tasks single_turn_scenarios_code_completion \
    --limit 200 \
    --batch_size 25 \
    --output_path results/high_throughput.json

# Cost-optimized evaluation (using Turbo model)
lm_eval --model dashscope \
    --model_args model=qwen-turbo,temperature=0.0 \
    --tasks single_turn_scenarios_function_generation \
    --metadata '{"difficulty":"simple"}' \
    --limit 100

# Quality-focused evaluation (using Max model)
lm_eval --model dashscope \
    --model_args model=qwen-max,temperature=0.05 \
    --tasks single_turn_scenarios_algorithm_implementation \
    --metadata '{"difficulty":"complex"}' \
    --limit 30
```

### DashScope Custom Configuration
```bash
# Using custom configuration file
lm_eval --model dashscope \
    --model_args config_file=model_configs/dashscope.yaml,model=qwen-coder-plus \
    --tasks single_turn_scenarios_suite \
    --limit 50

# Custom generation parameters
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus,temperature=0.1,top_p=0.9,repetition_penalty=1.1 \
    --tasks single_turn_scenarios_code_completion \
    --limit 25

# Chinese context evaluation
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus \
    --tasks single_turn_scenarios_function_generation \
    --metadata '{"context_mode":"full_context","language":"python"}' \
    --limit 15
```

### DashScope Troubleshooting
```bash
# Test basic connectivity
python -c "
import os
import requests
api_key = os.getenv('DASHSCOPE_API_KEY')
if not api_key:
    print('❌ DASHSCOPE_API_KEY not set')
else:
    print(f'✅ API key found: {api_key[:8]}...')
    # Test API call
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    data = {'model': 'qwen-turbo', 'input': {'messages': [{'role': 'user', 'content': 'Hello'}]}, 'parameters': {'max_tokens': 5}}
    try:
        response = requests.post('https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation', headers=headers, json=data, timeout=10)
        print(f'✅ API test: {response.status_code}')
    except Exception as e:
        print(f'❌ API test failed: {e}')
"

# Run DashScope example
python lm_eval/tasks/single_turn_scenarios/examples/dashscope_example.py

# Minimal test evaluation
lm_eval --model dashscope \
    --model_args model=qwen-turbo \
    --tasks single_turn_scenarios_code_completion \
    --limit 1 \
    --show_config
```

### DashScope Best Practices

1. **Model Selection**:
   - Use `qwen-coder-plus` for code generation tasks
   - Use `qwen-max` for complex reasoning and system design
   - Use `qwen-turbo` for high-throughput or cost-sensitive evaluations

2. **Performance Optimization**:
   - Increase `batch_size` for faster processing with Turbo model
   - Use appropriate `max_tokens` limits to control costs
   - Set `temperature=0.0` for deterministic results

3. **Cost Management**:
   - Use `qwen-turbo` for development and testing
   - Limit `max_tokens` for simple tasks
   - Use metadata filtering to focus on specific problem types

4. **Quality Optimization**:
   - Use `qwen-max` or `qwen-coder-plus` for production evaluations
   - Enable `full_context` mode for better results
   - Use lower temperature (0.0-0.1) for code generation

## Analysis Tools

After running evaluations, use the built-in analysis tools to analyze results:

### Standalone Analysis Runner
```bash
# Analyze evaluation results
python lm_eval/tasks/single_turn_scenarios/analysis_tools/run_analysis_standalone.py \
  results/your_evaluation.json --output-dir analysis_output

# Skip specific analyses
python lm_eval/tasks/single_turn_scenarios/analysis_tools/run_analysis_standalone.py \
  results/your_evaluation.json --output-dir analysis_output \
  --skip-model-comparison --skip-context-analysis
```

### Python Analysis Tools
```python
from lm_eval.tasks.single_turn_scenarios.analysis_tools import ScenarioAnalyzer, ModelComparator

# Scenario analysis
analyzer = ScenarioAnalyzer(results_data)
report = analyzer.analyze_scenarios_and_difficulty()

# Model comparison
comparator = ModelComparator(results_data)
comparison = comparator.compare_models()
```

### Available Analysis Tools
- **ScenarioAnalyzer** - Performance by scenario and difficulty
- **ModelComparator** - Compare multiple models
- **ContextAnalyzer** - Context mode impact analysis
- **ReportGenerator** - Comprehensive HTML/CSV reports

For more detailed information, see the main README.md file in the single_turn_scenarios directory.