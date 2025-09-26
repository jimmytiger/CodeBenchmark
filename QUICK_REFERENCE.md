# Single Turn Scenarios - Quick Reference Guide

## 🚀 Quick Start Commands

### Basic Task Execution
```bash
# Function generation (most common)
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation --limit 5

# Code completion
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_code_completion --limit 5

# Bug fixing
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_bug_fix --limit 5
```

### Multiple Tasks
```bash
# Run multiple related tasks
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation,single_turn_scenarios_code_completion \
  --limit 5

# Run all Python tasks
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_python --limit 10
```

## 🎯 Filtering Options

### By Difficulty
```bash
# Simple tasks only
--metadata '{"difficulty":"simple"}'

# Intermediate tasks only  
--metadata '{"difficulty":"intermediate"}'

# Complex tasks only
--metadata '{"difficulty":"complex"}'
```

### By Programming Language
```bash
# Python only
--metadata '{"language":"python"}'

# JavaScript only
--metadata '{"language":"javascript"}'

# Java only
--metadata '{"language":"java"}'
```

### By Context Mode
```bash
# No context
--metadata '{"context_mode":"no_context"}'

# Minimal context
--metadata '{"context_mode":"minimal_context"}'

# Full context
--metadata '{"context_mode":"full_context"}'
```

### Combined Filters
```bash
# Complex Python with full context
--metadata '{"difficulty":"complex","language":"python","context_mode":"full_context"}'
```

## 📋 All Available Tasks

### Core Tasks
- `single_turn_scenarios_function_generation`
- `single_turn_scenarios_code_completion`
- `single_turn_scenarios_bug_fix`
- `single_turn_scenarios_algorithm_implementation`
- `single_turn_scenarios_code_translation`

### Advanced Tasks
- `single_turn_scenarios_api_design`
- `single_turn_scenarios_system_design`
- `single_turn_scenarios_database_design`
- `single_turn_scenarios_security`
- `single_turn_scenarios_performance_optimization`
- `single_turn_scenarios_full_stack`
- `single_turn_scenarios_testing_strategy`
- `single_turn_scenarios_documentation`

### Suite Tasks
- `single_turn_scenarios_python` (Python-only tasks)
- `single_turn_scenarios_intermediate` (Intermediate difficulty)
- `single_turn_scenarios_minimal_context` (Minimal context tasks)

## 🤖 Model Configurations

### Claude (Anthropic)
```bash
--model claude-local --model_args model=claude-3-haiku-20240307
--model claude-local --model_args model=claude-3-sonnet-20240229
--model claude-local --model_args model=claude-3-opus-20240229
```

### OpenAI
```bash
--model openai-chat --model_args model=gpt-4
--model openai-chat --model_args model=gpt-3.5-turbo
```

### DashScope (Qwen)
```bash
--model dashscope --model_args model=qwen-coder-plus
--model dashscope --model_args model=qwen-max
--model dashscope --model_args model=qwen-turbo
```

### HuggingFace Local Models
```bash
--model hf --model_args pretrained=deepseek-ai/deepseek-coder-6.7b-instruct,device_map=auto
--model hf --model_args pretrained=codellama/CodeLlama-7b-Instruct-hf,device_map=auto
```

## 🔧 Common Parameters

### Essential Parameters
- `--limit N` - Number of samples to evaluate (start with 1-5 for testing)
- `--output_path path/to/results.json` - Save results to file
- `--predict_only` - Skip metrics computation (faster for testing)
- `--batch_size N` - Batch size for processing (default: 1)

### Example with All Parameters
```bash
python -m lm_eval --model claude-local \
  --model_args model=claude-3-haiku-20240307,temperature=0.0 \
  --tasks single_turn_scenarios_function_generation \
  --metadata '{"difficulty":"simple","language":"python"}' \
  --limit 10 \
  --batch_size 1 \
  --output_path results/my_evaluation.json \
  --predict_only
```

## 📊 Result Files

Each evaluation creates:
1. **Main results**: `results/task_name_TIMESTAMP.json`
2. **Sample outputs**: `results/samples_task_name_TIMESTAMP.jsonl`

### View Results
```bash
# View main metrics
cat results/function_generation_*.json | jq '.results'

# View first sample output
head -n 1 results/samples_function_generation_*.jsonl | jq '.resps[0][0]'
```

## 🚨 Troubleshooting

### Common Issues
```bash
# Task not found
python -m lm_eval --tasks list | grep single_turn_scenarios

# API key not set
export ANTHROPIC_API_KEY="your-key-here"

# Memory issues with local models
--batch_size 1 --limit 1

# Test basic functionality
python -m lm_eval --model claude-local --model_args model=claude-3-haiku-20240307 \
  --tasks single_turn_scenarios_function_generation --limit 1 --predict_only
```

## 🎯 Best Practices

1. **Start small**: Use `--limit 1-2` for initial testing
2. **Use predict_only**: Add `--predict_only` for faster testing
3. **Save results**: Always specify `--output_path`
4. **Monitor costs**: Be mindful of API usage with commercial models
5. **Test incrementally**: Validate with small limits before full runs

## 📈 Performance Tips

- **Fast testing**: Use Claude Haiku or GPT-3.5-turbo with `--predict_only`
- **Production**: Use Claude Sonnet, GPT-4, or Qwen Max for quality results
- **Local models**: Reduce `--batch_size` and `--limit` to avoid memory issues
- **Parallel runs**: Execute different tasks simultaneously on separate machines

## 🔍 Analysis Tools Quick Reference

### Available Analysis Tools
- **ScenarioAnalyzer** - Analyze performance by scenario and difficulty
- **ModelComparator** - Compare performance across models
- **ContextAnalyzer** - Analyze impact of context modes
- **ReportGenerator** - Generate comprehensive reports

### Basic Usage
```python
from lm_eval.tasks.single_turn_scenarios.analysis_tools import ScenarioAnalyzer

# Initialize and analyze
analyzer = ScenarioAnalyzer(results_data)
report = analyzer.analyze_scenarios_and_difficulty()
```

### Standalone Runner
```bash
# Run comprehensive analysis
python lm_eval/tasks/single_turn_scenarios/analysis_tools/run_analysis_standalone.py \
  results/your_results.json --output-dir analysis_output

# Skip specific analyses
python lm_eval/tasks/single_turn_scenarios/analysis_tools/run_analysis_standalone.py \
  results/your_results.json --output-dir analysis_output \
  --skip-model-comparison --skip-context-analysis
```

### Check Available Tools
```python
from lm_eval.tasks.single_turn_scenarios.analysis_tools import get_available_tools
print(f"Available tools: {get_available_tools()}")
```