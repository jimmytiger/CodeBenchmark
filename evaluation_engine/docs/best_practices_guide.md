# Best Practices Guide - Config-Driven Evaluation

This guide provides best practices, optimization tips, and recommendations for effective use of the config-driven evaluation system.

## Table of Contents

1. [Configuration Design](#configuration-design)
2. [Model Configuration](#model-configuration)
3. [Task Organization](#task-organization)
4. [Performance Optimization](#performance-optimization)
5. [Resource Management](#resource-management)
6. [Error Handling](#error-handling)
7. [Security and Privacy](#security-and-privacy)
8. [Development Workflow](#development-workflow)
9. [Production Deployment](#production-deployment)
10. [Monitoring and Debugging](#monitoring-and-debugging)

## Configuration Design

### Use Descriptive Names

**✅ Good:**
```yaml
models:
  gpt4_reasoning_optimized:
    name: "GPT-4 for Complex Reasoning Tasks"
    type: "openai"
    model_name: "gpt-4"

tasks:
  - name: "commonsense_reasoning_hellaswag"
    description: "Evaluate commonsense reasoning using HellaSwag dataset"
    model_ref: "gpt4_reasoning_optimized"
    task_name: "hellaswag"
```

**❌ Avoid:**
```yaml
models:
  m1:
    type: "openai"
    model_name: "gpt-4"

tasks:
  - name: "t1"
    model_ref: "m1"
    task_name: "hellaswag"
```

### Organize with Variables

**✅ Good:**
```yaml
variables:
  # Environment configuration
  output_base: "${env:HOME}/evaluations"
  project_name: "llm_comparison_2024"
  
  # Model parameters
  reasoning_temperature: 0.1
  creative_temperature: 0.7
  standard_max_tokens: 1500
  
  # Task parameters
  quick_test_limit: 50
  standard_limit: 200
  comprehensive_limit: 1000
  
  # Batch sizes optimized for different model types
  openai_batch_size: 8
  anthropic_batch_size: 4
  huggingface_batch_size: 2

models:
  gpt4:
    type: "openai"
    model_name: "gpt-4"
    parameters:
      temperature: "${reasoning_temperature}"
      max_tokens: "${standard_max_tokens}"

tasks:
  - name: "reasoning_test"
    model_ref: "gpt4"
    task_name: "hellaswag"
    batch_size: "${openai_batch_size}"
    task_config:
      limit: "${standard_limit}"
```

### Version Your Configurations

```yaml
metadata:
  name: "Production LLM Evaluation Suite"
  version: "2.1.0"
  author: "AI Research Team"
  created_at: "2024-01-15"
  last_modified: "2024-01-20"
  changelog:
    - "v2.1.0: Added Claude-3 models and safety evaluations"
    - "v2.0.0: Restructured task dependencies"
    - "v1.0.0: Initial production configuration"
```

### Document Your Intent

```yaml
# Production evaluation configuration for Q1 2024 model comparison
# This configuration compares GPT-4, Claude-3, and Llama-2 across
# reasoning, math, and code generation tasks.
# 
# Expected runtime: ~2 hours
# Expected cost: ~$50 (primarily GPT-4 usage)
# 
# Usage:
#   eval-engine config run production_q1_2024.yaml

metadata:
  name: "Q1 2024 Model Comparison"
  description: |
    Comprehensive evaluation comparing latest models across key capabilities:
    - Commonsense reasoning (HellaSwag, ARC)
    - Mathematical reasoning (GSM8K)
    - Code generation (HumanEval)
    - Safety and truthfulness (TruthfulQA)
```

## Model Configuration

### Use Environment Variables for API Keys

**✅ Good:**
```yaml
variables:
  openai_api_key: "${env:OPENAI_API_KEY}"
  anthropic_api_key: "${env:ANTHROPIC_API_KEY}"

models:
  gpt4:
    type: "openai"
    model_name: "gpt-4"
    # API key automatically used from environment
```

**❌ Never do this:**
```yaml
models:
  gpt4:
    type: "openai"
    model_name: "gpt-4"
    api_key: "sk-1234567890abcdef"  # Never hardcode API keys!
```

### Optimize Model Parameters by Use Case

```yaml
models:
  # For consistent, factual responses
  gpt4_factual:
    type: "openai"
    model_name: "gpt-4"
    parameters:
      temperature: 0.1      # Low temperature for consistency
      max_tokens: 1500
      top_p: 0.95
    system_prompt: "Provide accurate, factual responses. Be concise and precise."

  # For mathematical reasoning
  gpt4_math:
    type: "openai"
    model_name: "gpt-4"
    parameters:
      temperature: 0.0      # Deterministic for math
      max_tokens: 2000      # More tokens for step-by-step reasoning
    system_prompt: "Solve math problems step by step. Show your work clearly."

  # For creative tasks
  claude_creative:
    type: "anthropic"
    model_name: "claude-3-opus-20240229"
    parameters:
      temperature: 0.7      # Higher temperature for creativity
      max_tokens: 2500
    system_prompt: "Be creative and thoughtful in your responses."
```

### Use Model-Specific Prompt Templates

```yaml
models:
  gpt4:
    type: "openai"
    model_name: "gpt-4"
    prompt_template: |
      Question: {question}
      
      Please provide a clear and accurate answer:

  claude:
    type: "anthropic"
    model_name: "claude-3-sonnet-20240229"
    prompt_template: |
      Human: {question}
      
      Assistant: I'll provide a thoughtful and accurate response:

  llama2:
    type: "huggingface"
    model_name: "meta-llama/Llama-2-7b-chat-hf"
    prompt_template: "[INST] {question} [/INST]"
```

## Task Organization

### Structure Tasks by Capability

```yaml
tasks:
  # === FOUNDATION CAPABILITIES ===
  - name: "foundation_commonsense"
    description: "Basic commonsense reasoning validation"
    model_ref: "gpt35_fast"
    task_name: "hellaswag"
    task_config:
      limit: 100
    depends_on: []

  # === REASONING CAPABILITIES ===
  - name: "reasoning_reading_comprehension"
    description: "Reading comprehension and logical reasoning"
    model_ref: "gpt4_reasoning"
    task_name: "arc_easy"
    depends_on: ["foundation_commonsense"]

  - name: "reasoning_advanced"
    description: "Advanced reasoning challenges"
    model_ref: "gpt4_reasoning"
    task_name: "arc_challenge"
    depends_on: ["reasoning_reading_comprehension"]

  # === MATHEMATICAL CAPABILITIES ===
  - name: "math_word_problems"
    description: "Grade school math word problems"
    model_ref: "gpt4_math"
    task_name: "gsm8k"
    depends_on: ["foundation_commonsense"]

  # === CODE GENERATION ===
  - name: "code_generation_basic"
    description: "Basic Python code generation"
    model_ref: "gpt4_code"
    task_name: "humaneval"
    depends_on: ["reasoning_reading_comprehension"]
```

### Use Logical Dependencies

```yaml
tasks:
  # Start with quick validation
  - name: "system_validation"
    model_ref: "gpt35"
    task_name: "piqa"
    task_config:
      limit: 20  # Quick validation
    depends_on: []

  # Basic capabilities (can run in parallel)
  - name: "basic_reasoning"
    model_ref: "gpt35"
    task_name: "hellaswag"
    depends_on: ["system_validation"]

  - name: "basic_comprehension"
    model_ref: "gpt35"
    task_name: "arc_easy"
    depends_on: ["system_validation"]

  # Advanced capabilities (depend on basics)
  - name: "advanced_reasoning"
    model_ref: "gpt4"
    task_name: "arc_challenge"
    depends_on: ["basic_reasoning", "basic_comprehension"]

  # Specialized tasks (depend on advanced)
  - name: "specialized_math"
    model_ref: "gpt4"
    task_name: "gsm8k"
    depends_on: ["advanced_reasoning"]

  # Final validation (depends on all)
  - name: "comprehensive_validation"
    model_ref: "gpt4"
    task_name: "truthfulqa_mc"
    depends_on: ["specialized_math"]
```

### Use Appropriate Test Limits

```yaml
variables:
  # Different limits for different purposes
  development_limit: 10      # Quick testing during development
  validation_limit: 50       # Validation and debugging
  standard_limit: 200        # Standard evaluation
  comprehensive_limit: 1000  # Thorough evaluation
  full_dataset: -1           # Use entire dataset

tasks:
  - name: "development_test"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      limit: "${development_limit}"  # Quick test

  - name: "production_evaluation"
    model_ref: "gpt4"
    task_name: "hellaswag"
    task_config:
      limit: "${comprehensive_limit}"  # Thorough evaluation
```

## Performance Optimization

### Optimize Batch Sizes by Model Type

```yaml
variables:
  # Batch sizes optimized for different model types and costs
  openai_gpt4_batch: 2       # Expensive model, small batches
  openai_gpt35_batch: 8      # Balanced cost/speed
  anthropic_batch: 4         # Medium batches
  huggingface_batch: 16      # Can handle larger batches
  
  # Task-specific batch sizes
  code_generation_batch: 1   # Code generation needs batch_size=1
  math_batch: 2              # Math tasks benefit from smaller batches
  reasoning_batch: 4         # Standard reasoning tasks

models:
  gpt4:
    type: "openai"
    model_name: "gpt-4"
  
  gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"

tasks:
  - name: "expensive_gpt4_task"
    model_ref: "gpt4"
    task_name: "hellaswag"
    batch_size: "${openai_gpt4_batch}"

  - name: "efficient_gpt35_task"
    model_ref: "gpt35"
    task_name: "hellaswag"
    batch_size: "${openai_gpt35_batch}"

  - name: "code_generation"
    model_ref: "gpt4"
    task_name: "humaneval"
    batch_size: "${code_generation_batch}"  # Always 1 for code generation
```

### Use Progressive Evaluation

```yaml
# Start with quick validation, then progressively more comprehensive
tasks:
  # Phase 1: Quick validation (5 minutes)
  - name: "phase1_quick_validation"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      limit: 20
    depends_on: []

  # Phase 2: Standard evaluation (30 minutes)
  - name: "phase2_standard_eval"
    model_ref: "gpt4"
    task_name: "hellaswag"
    task_config:
      limit: 200
    depends_on: ["phase1_quick_validation"]

  # Phase 3: Comprehensive evaluation (2 hours)
  - name: "phase3_comprehensive"
    model_ref: "gpt4"
    task_name: "arc_challenge"
    task_config:
      limit: 1000
    depends_on: ["phase2_standard_eval"]
```

### Parallel Task Execution

```yaml
tasks:
  # These can run in parallel (no dependencies)
  - name: "parallel_task_1"
    model_ref: "gpt35"
    task_name: "hellaswag"
    depends_on: []

  - name: "parallel_task_2"
    model_ref: "claude"
    task_name: "arc_easy"
    depends_on: []

  - name: "parallel_task_3"
    model_ref: "gpt4"
    task_name: "gsm8k"
    depends_on: []

  # This runs after all parallel tasks complete
  - name: "convergent_task"
    model_ref: "gpt4"
    task_name: "truthfulqa_mc"
    depends_on: ["parallel_task_1", "parallel_task_2", "parallel_task_3"]
```

## Resource Management

### Monitor Costs

```yaml
# Add cost tracking and limits
variables:
  # Estimated costs per 1K tokens (update regularly)
  gpt4_cost_per_1k: 0.03
  gpt35_cost_per_1k: 0.002
  claude_cost_per_1k: 0.015

  # Budget limits
  max_daily_budget: 100.00
  max_task_budget: 20.00

models:
  gpt4_budget_aware:
    type: "openai"
    model_name: "gpt-4"
    parameters:
      max_tokens: 1000  # Limit tokens to control costs
    # Note: Actual budget enforcement would be implemented in the system

tasks:
  - name: "cost_controlled_task"
    model_ref: "gpt4_budget_aware"
    task_name: "hellaswag"
    task_config:
      limit: 100  # Limit examples to control costs
```

### Memory Management

```yaml
# Configure for available memory
variables:
  # Adjust based on available system memory
  low_memory_batch: 2
  standard_memory_batch: 8
  high_memory_batch: 16

tasks:
  - name: "memory_intensive_task"
    model_ref: "large_model"
    task_name: "long_context_task"
    batch_size: "${low_memory_batch}"  # Reduce batch size for memory

  - name: "memory_efficient_task"
    model_ref: "efficient_model"
    task_name: "simple_task"
    batch_size: "${high_memory_batch}"  # Can use larger batches
```

### Rate Limit Management

```yaml
models:
  gpt4_rate_limited:
    type: "openai"
    model_name: "gpt-4"
    parameters:
      request_timeout: 60
      retry_attempts: 3
      retry_delay: 5

tasks:
  - name: "rate_limit_friendly"
    model_ref: "gpt4_rate_limited"
    task_name: "hellaswag"
    batch_size: 2  # Smaller batches to avoid rate limits
    task_config:
      request_delay: 1  # Add delay between requests
```

## Error Handling

### Graceful Degradation

```yaml
tasks:
  # Critical path with fallback
  - name: "primary_evaluation"
    model_ref: "gpt4"
    task_name: "hellaswag"
    task_config:
      limit: 1000
    depends_on: []

  # Fallback if primary fails
  - name: "fallback_evaluation"
    model_ref: "gpt35"  # Cheaper, more reliable fallback
    task_name: "hellaswag"
    task_config:
      limit: 500
    depends_on: []  # Independent of primary

  # Final task that can use either result
  - name: "analysis_task"
    model_ref: "gpt35"
    task_name: "arc_easy"
    depends_on: ["primary_evaluation"]  # Will use fallback if primary fails
```

### Retry Configuration

```yaml
models:
  robust_gpt4:
    type: "openai"
    model_name: "gpt-4"
    parameters:
      retry_attempts: 5
      retry_delay: 10
      retry_exponential_backoff: true
      timeout: 120

tasks:
  - name: "robust_task"
    model_ref: "robust_gpt4"
    task_name: "hellaswag"
    # Task will automatically retry on failures
```

### Error Recovery

```yaml
# Configure tasks to continue on errors
defaults:
  continue_on_error: true
  max_failures_per_task: 10  # Stop task if too many failures

tasks:
  - name: "fault_tolerant_task"
    model_ref: "gpt4"
    task_name: "hellaswag"
    task_config:
      skip_on_error: true      # Skip failed examples
      error_threshold: 0.1     # Stop if >10% of examples fail
```

## Security and Privacy

### Secure API Key Management

```bash
# Use environment variables
export OPENAI_API_KEY="$(cat ~/.secrets/openai_key)"
export ANTHROPIC_API_KEY="$(cat ~/.secrets/anthropic_key)"

# Or use a secrets management system
export OPENAI_API_KEY="$(vault kv get -field=api_key secret/openai)"
```

### Data Privacy

```yaml
# Configure data handling for privacy
output:
  include_raw_responses: false  # Don't save raw responses if privacy-sensitive
  anonymize_data: true          # Remove identifying information
  encrypt_output: true          # Encrypt output files

tasks:
  - name: "privacy_aware_task"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      strip_personal_info: true  # Remove any personal information
      hash_identifiers: true     # Hash any remaining identifiers
```

### Access Control

```yaml
metadata:
  access_level: "internal"      # Mark configuration access level
  data_classification: "confidential"
  approved_users: ["team@company.com"]
  
# Use environment variables for access control
variables:
  authorized_user: "${env:USER}"
  access_token: "${env:EVAL_ACCESS_TOKEN}"
```

## Development Workflow

### Development vs Production Configurations

```yaml
# development.yaml
variables:
  test_limit: 10
  batch_size: 2
  output_dir: "./dev_results"

tasks:
  - name: "dev_test"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      limit: "${test_limit}"
```

```yaml
# production.yaml
variables:
  production_limit: 1000
  batch_size: 8
  output_dir: "${env:PRODUCTION_OUTPUT_DIR}"

tasks:
  - name: "production_eval"
    model_ref: "gpt4"
    task_name: "hellaswag"
    task_config:
      limit: "${production_limit}"
```

### Configuration Testing

```yaml
# test_config.yaml - for validating configuration changes
metadata:
  name: "Configuration Test Suite"
  
variables:
  test_mode: true
  quick_limit: 5

tasks:
  # Test each model type
  - name: "test_openai"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      limit: "${quick_limit}"

  - name: "test_anthropic"
    model_ref: "claude"
    task_name: "hellaswag"
    task_config:
      limit: "${quick_limit}"

  # Test task dependencies
  - name: "test_dependencies"
    model_ref: "gpt35"
    task_name: "arc_easy"
    task_config:
      limit: "${quick_limit}"
    depends_on: ["test_openai"]
```

### Version Control Best Practices

```bash
# .gitignore
*.log
results/
*.env
.secrets/

# Track configuration files
git add *.yaml
git add configs/

# Use meaningful commit messages
git commit -m "Add Claude-3 models to evaluation suite"
git commit -m "Optimize batch sizes for cost efficiency"
git commit -m "Add safety evaluation tasks"
```

## Production Deployment

### Environment Configuration

```yaml
# production.yaml
variables:
  # Use production environment variables
  output_dir: "${env:PRODUCTION_OUTPUT_DIR}"
  log_level: "${env:LOG_LEVEL}"
  max_parallel: "${env:MAX_PARALLEL_TASKS}"
  
  # Production-specific settings
  comprehensive_limit: 2000
  production_batch_size: 4
  
models:
  production_gpt4:
    type: "openai"
    model_name: "gpt-4"
    parameters:
      temperature: 0.1
      max_tokens: 2000
      request_timeout: 120
      retry_attempts: 5

output:
  directory: "${output_dir}"
  formats: ["json", "html"]
  generate_report: true
  compress_output: true
  timestamp_dirs: true
```

### Monitoring and Alerting

```yaml
# Add monitoring configuration
metadata:
  monitoring:
    enabled: true
    alert_on_failure: true
    alert_email: "team@company.com"
    max_execution_time: 7200  # 2 hours
    
output:
  monitoring:
    track_costs: true
    track_performance: true
    alert_thresholds:
      error_rate: 0.05      # Alert if >5% error rate
      cost_per_hour: 50     # Alert if >$50/hour
      memory_usage: 0.8     # Alert if >80% memory usage
```

### Backup and Recovery

```yaml
output:
  backup:
    enabled: true
    backup_dir: "${env:BACKUP_DIR}"
    retention_days: 30
    
  recovery:
    checkpoint_interval: 100  # Save progress every 100 examples
    resume_on_failure: true
    max_resume_attempts: 3
```

## Monitoring and Debugging

### Comprehensive Logging

```yaml
# Enable detailed logging for debugging
variables:
  log_level: "DEBUG"
  log_dir: "./logs"

output:
  logging:
    level: "${log_level}"
    file: "${log_dir}/evaluation_$(date).log"
    include_timestamps: true
    include_task_details: true
    include_model_responses: true  # Only for debugging
```

### Performance Monitoring

```yaml
output:
  performance_monitoring:
    enabled: true
    track_metrics:
      - "response_time"
      - "token_usage"
      - "memory_usage"
      - "error_rate"
      - "cost_per_task"
    
  profiling:
    enabled: true
    profile_memory: true
    profile_cpu: true
    save_profiles: true
```

### Health Checks

```yaml
tasks:
  # Add health check tasks
  - name: "health_check_openai"
    description: "Verify OpenAI API connectivity"
    model_ref: "gpt35"
    task_name: "hellaswag"
    task_config:
      limit: 1  # Single example for health check
    depends_on: []

  - name: "health_check_anthropic"
    description: "Verify Anthropic API connectivity"
    model_ref: "claude"
    task_name: "hellaswag"
    task_config:
      limit: 1
    depends_on: []

  # Main tasks depend on health checks
  - name: "main_evaluation"
    model_ref: "gpt4"
    task_name: "comprehensive_eval"
    depends_on: ["health_check_openai", "health_check_anthropic"]
```

### Debugging Configuration

```yaml
# debug.yaml - for troubleshooting issues
metadata:
  name: "Debug Configuration"
  
variables:
  debug_mode: true
  single_example: 1
  verbose_logging: true

models:
  debug_gpt35:
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.0  # Deterministic for debugging
      max_tokens: 100   # Short responses for debugging

tasks:
  - name: "debug_task"
    model_ref: "debug_gpt35"
    task_name: "hellaswag"
    batch_size: 1  # Process one at a time
    task_config:
      limit: "${single_example}"
      verbose: "${verbose_logging}"

output:
  include_raw_responses: true  # Include full responses for debugging
  save_intermediate_results: true
  debug_info: true
```

## Summary Checklist

### Before Running Evaluations

- [ ] Validate configuration syntax
- [ ] Check API keys are set
- [ ] Verify model names are correct
- [ ] Confirm task names exist
- [ ] Test with small limits first
- [ ] Check available disk space
- [ ] Estimate costs and runtime

### Configuration Quality

- [ ] Use descriptive names for models and tasks
- [ ] Document complex configurations
- [ ] Use variables for repeated values
- [ ] Set appropriate batch sizes
- [ ] Configure proper error handling
- [ ] Use environment variables for secrets
- [ ] Version your configurations

### Performance Optimization

- [ ] Optimize batch sizes by model type
- [ ] Use task dependencies efficiently
- [ ] Set appropriate test limits
- [ ] Monitor resource usage
- [ ] Configure retry policies
- [ ] Use parallel execution where possible

### Production Readiness

- [ ] Set up monitoring and alerting
- [ ] Configure backup and recovery
- [ ] Use production-appropriate limits
- [ ] Set up proper logging
- [ ] Test error scenarios
- [ ] Document operational procedures

Following these best practices will help you create robust, efficient, and maintainable evaluation configurations that scale from development to production use.