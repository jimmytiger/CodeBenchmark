# Dataset Expansion Tools for AI Evaluation Engine

This directory contains comprehensive tools for expanding and validating datasets to production-ready size (100+ problems per scenario) with multi-language support and quality assurance.

## Overview

The dataset expansion system consists of several interconnected tools:

1. **Dataset Generator** - Generates single-turn and multi-turn scenarios
2. **Dataset Validator** - Validates dataset integrity and completeness
3. **Multilingual Dataset Generator** - Creates multi-language and cross-language datasets
4. **Dataset Quality Assurance** - Comprehensive quality checking system
5. **Dataset Expansion Orchestrator** - Coordinates the entire expansion process

## Quick Start

### 1. Test the Tools

Before running the full expansion, test that all tools work correctly:

```bash
# Run unit tests
python scripts/test_dataset_expansion.py

# Run integration test
python scripts/test_dataset_expansion.py --integration
```

### 2. Expand All Datasets

Run the complete dataset expansion process:

```bash
# Expand all datasets to 100 problems per scenario
python scripts/expand_datasets.py --target-size 100 --include-multilingual --quality-level production

# Expand only single-turn scenarios
python scripts/expand_datasets.py --type single --target-size 150

# Expand specific scenarios
python scripts/expand_datasets.py --scenarios code_completion bug_fix --target-size 200
```

### 3. Generate Datasets Individually

Generate datasets for specific scenarios:

```bash
# Generate single-turn problems
python scripts/dataset_generator.py --scenario code_completion --count 100 --type single

# Generate multi-turn scenarios
python scripts/dataset_generator.py --scenario code_review_process --count 50 --type multi

# Generate both types
python scripts/dataset_generator.py --count 100 --type both
```

### 4. Create Multilingual Datasets

Generate datasets with multi-language support:

```bash
# Generate multilingual datasets
python scripts/multilingual_dataset_generator.py --scenario code_completion --count 100 \
  --programming-languages python javascript java cpp go \
  --natural-languages en zh es fr

# Generate cross-language evaluation dataset
python scripts/multilingual_dataset_generator.py --cross-language-only --count 50
```

### 5. Validate Datasets

Validate dataset quality and integrity:

```bash
# Validate specific dataset
python scripts/dataset_validator.py --dataset lm_eval/tasks/single_turn_scenarios/problems.jsonl --level comprehensive

# Validate all datasets
python scripts/dataset_validator.py --level production --output validation_report.md

# Get JSON output
python scripts/dataset_validator.py --format json --output validation_results.json
```

### 6. Run Quality Assurance

Perform comprehensive quality assurance:

```bash
# Run QA on specific dataset
python scripts/dataset_quality_assurance.py --dataset lm_eval/tasks/single_turn_scenarios/problems.jsonl --level production

# Run QA with detailed report
python scripts/dataset_quality_assurance.py --dataset path/to/dataset.jsonl --level premium --output qa_report.md
```

## Tool Details

### Dataset Generator (`dataset_generator.py`)

Generates production-ready datasets with comprehensive problem sets.

**Features:**
- Single-turn and multi-turn scenario generation
- Multiple programming languages (Python, JavaScript, Java, C++, Go, Rust, TypeScript)
- Difficulty levels (simple, intermediate, complex)
- Context modes (no_context, minimal_context, full_context, domain_context)
- Comprehensive test case generation
- Metadata management

**Usage:**
```bash
python scripts/dataset_generator.py [options]

Options:
  --scenario SCENARIO     Specific scenario to generate
  --type {single,multi,both}  Type of scenarios to generate
  --count COUNT          Number of problems/scenarios to generate
  --output OUTPUT        Output directory
  --base-path BASE_PATH  Base path for task directories
```

**Example:**
```bash
# Generate 150 code completion problems
python scripts/dataset_generator.py --scenario code_completion --count 150 --type single

# Generate all scenario types with 100 items each
python scripts/dataset_generator.py --count 100 --type both
```

### Dataset Validator (`dataset_validator.py`)

Validates dataset integrity, completeness, and compliance with schema requirements.

**Validation Levels:**
- **Basic**: Schema validation, required fields, ID uniqueness
- **Comprehensive**: Content quality, distribution analysis, test validation
- **Production**: Size requirements, metadata completeness, security checks

**Usage:**
```bash
python scripts/dataset_validator.py [options]

Options:
  --dataset DATASET      Specific dataset file to validate
  --level {basic,comprehensive,production}  Validation level
  --output OUTPUT        Output file for validation report
  --format {text,json}   Output format
```

**Example:**
```bash
# Validate all datasets with comprehensive checks
python scripts/dataset_validator.py --level comprehensive --output validation_report.md

# Validate specific dataset for production
python scripts/dataset_validator.py --dataset lm_eval/tasks/single_turn_scenarios/problems.jsonl --level production
```

### Multilingual Dataset Generator (`multilingual_dataset_generator.py`)

Creates datasets with multi-language support and cross-language evaluation capabilities.

**Features:**
- Multi-programming language support
- Natural language translations (English, Chinese, Spanish, French, German)
- Cross-language code translation scenarios
- Language-specific prompt adaptations

**Usage:**
```bash
python scripts/multilingual_dataset_generator.py [options]

Options:
  --scenario SCENARIO    Specific scenario to generate
  --count COUNT         Number of problems to generate
  --programming-languages LANGS  Target programming languages
  --natural-languages LANGS     Natural languages for prompts
  --cross-language-only Generate only cross-language evaluation dataset
```

**Example:**
```bash
# Generate multilingual code completion dataset
python scripts/multilingual_dataset_generator.py --scenario code_completion --count 100 \
  --programming-languages python javascript java \
  --natural-languages en zh es

# Generate cross-language evaluation dataset
python scripts/multilingual_dataset_generator.py --cross-language-only --count 50
```

### Dataset Quality Assurance (`dataset_quality_assurance.py`)

Comprehensive quality assurance system with multiple quality levels.

**Quality Levels:**
- **Basic**: Data completeness, schema validation, ID uniqueness
- **Standard**: Content quality, language/difficulty distribution, syntax validation
- **Premium**: Code execution validation, reference solution quality, prompt engineering
- **Production**: Performance benchmarking, security assessment, compliance validation

**Quality Grades:**
- A (90-100): Excellent quality, production ready
- B (80-89): Good quality, minor improvements needed
- C (70-79): Acceptable quality, some issues to address
- D (60-69): Poor quality, significant improvements needed
- F (0-59): Failing quality, major issues

**Usage:**
```bash
python scripts/dataset_quality_assurance.py [options]

Options:
  --dataset DATASET      Dataset file to validate
  --level {basic,standard,premium,production}  Quality assurance level
  --output OUTPUT        Output file for quality report
  --format {text,json}   Output format
```

**Example:**
```bash
# Run production-level QA on dataset
python scripts/dataset_quality_assurance.py \
  --dataset lm_eval/tasks/single_turn_scenarios/problems.jsonl \
  --level production --output qa_report.md

# Get JSON output for automated processing
python scripts/dataset_quality_assurance.py \
  --dataset path/to/dataset.jsonl --level standard --format json
```

### Dataset Expansion Orchestrator (`expand_datasets.py`)

Coordinates the complete dataset expansion process using all tools.

**Features:**
- Automated expansion of all scenario types
- Parallel processing for efficiency
- Comprehensive validation and quality assurance
- Detailed reporting and summaries
- Error handling and recovery

**Usage:**
```bash
python scripts/expand_datasets.py [options]

Options:
  --target-size SIZE     Target size per scenario (default: 100)
  --scenarios SCENARIOS  Specific scenarios to expand
  --type {single,multi,both}  Type of scenarios to expand
  --include-multilingual Include multilingual datasets
  --quality-level LEVEL  Quality assurance level
  --output-dir DIR       Output directory for expanded datasets
  --parallel            Run expansions in parallel
```

**Example:**
```bash
# Complete dataset expansion to production standards
python scripts/expand_datasets.py --target-size 100 --include-multilingual --quality-level production

# Expand only single-turn scenarios with higher target
python scripts/expand_datasets.py --type single --target-size 200 --quality-level premium

# Expand specific scenarios
python scripts/expand_datasets.py --scenarios code_completion bug_fix function_generation --target-size 150
```

## Dataset Structure

### Single-Turn Problems

```json
{
  "id": "st_code_completion_0001",
  "title": "Complete array sum function",
  "language": "python",
  "scenario": "code_completion",
  "difficulty": "simple",
  "context_mode": "minimal_context",
  "prompt": "Complete the function to calculate sum of array elements",
  "reference": ["def sum_array(arr):\n    total = 0\n    for item in arr:\n        total += item\n    return total"],
  "tests": [{"type": "unit", "file": "tests/test_code_completion_0001.py", "cmd": "python -m pytest tests/test_code_completion_0001.py -v"}],
  "metadata": {
    "time_limit_s": 10,
    "memory_limit_mb": 200,
    "seed": 1001,
    "author": "dataset_generator",
    "license": "MIT",
    "generated_at": "2025-01-01T12:00:00"
  }
}
```

### Multi-Turn Scenarios

```json
{
  "id": "mt_code_review_0001",
  "scenario": "code_review_process",
  "difficulty": "intermediate",
  "language": "python",
  "context_mode": "full_context",
  "turns": [
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
    }
  ],
  "success_metrics": {
    "review_thoroughness": 0.8,
    "improvement_quality": 0.7,
    "standards_compliance": 0.9
  },
  "metadata": {
    "max_turns": 4,
    "conversation_timeout": 300,
    "enable_context_retention": true,
    "author": "dataset_generator",
    "license": "MIT"
  }
}
```

### Multilingual Problems

```json
{
  "id": "ml_code_completion_0001",
  "base_language": "python",
  "natural_language": "en",
  "scenario": "code_completion",
  "difficulty": "intermediate",
  "context_mode": "minimal_context",
  "translations": {
    "python": {
      "prompt": "Complete the binary search implementation",
      "reference": ["def binary_search(arr, target): ..."],
      "tests": [{"type": "unit", "file": "tests/test_ml_0001.py", "cmd": "python -m pytest tests/test_ml_0001.py"}]
    },
    "javascript": {
      "prompt": "Complete the binary search implementation",
      "reference": ["function binarySearch(arr, target) { ... }"],
      "tests": [{"type": "unit", "file": "tests/test_ml_0001.js", "cmd": "node tests/test_ml_0001.js"}]
    }
  },
  "cross_language_pairs": [["python", "javascript"], ["python", "java"]],
  "metadata": {
    "supported_languages": ["python", "javascript", "java"],
    "natural_language": "en",
    "cross_language_evaluation": true
  }
}
```

## Supported Scenarios

### Single-Turn Scenarios (13 types)

1. **code_completion** - Complete partial code implementations
2. **bug_fix** - Fix bugs in existing code
3. **function_generation** - Generate complete functions from specifications
4. **code_translation** - Translate code between programming languages
5. **algorithm_implementation** - Implement algorithms from descriptions
6. **api_design** - Design RESTful APIs
7. **system_design** - Design distributed systems and architectures
8. **database_design** - Design database schemas and queries
9. **security_implementation** - Implement security measures and controls
10. **performance_optimization** - Optimize code for better performance
11. **documentation_generation** - Generate comprehensive documentation
12. **testing_strategy** - Design and implement testing strategies
13. **full_stack_development** - Develop complete full-stack features

### Multi-Turn Scenarios (12 types)

1. **code_review_process** - Interactive code review and improvement
2. **debugging_session** - Step-by-step debugging process
3. **design_iteration** - Iterative design refinement
4. **teaching_dialogue** - Educational programming conversations
5. **collaborative_development** - Team development workflows
6. **requirements_refinement** - Requirements analysis and clarification
7. **architecture_discussion** - Architecture design discussions
8. **performance_tuning** - Performance analysis and optimization

### Quantitative Trading Scenarios (8 types)

1. **strategy_development** - Trading strategy development
2. **multifactor_model_construction** - Multi-factor model building
3. **market_research_analysis** - Market research and analysis
4. **portfolio_risk_assessment** - Portfolio risk evaluation
5. **execution_algorithm_optimization** - Execution algorithm tuning
6. **high_frequency_trading** - HFT system development
7. **fundamental_quant_analysis** - Fundamental analysis workflows
8. **technical_quant_analysis** - Technical analysis implementations

## Programming Language Support

- **Python** - Primary language with comprehensive support
- **JavaScript** - Full support including Node.js and browser environments
- **TypeScript** - Type-safe JavaScript variant
- **Java** - Enterprise-grade object-oriented programming
- **C++** - Systems programming and performance-critical applications
- **Go** - Modern systems programming language
- **Rust** - Memory-safe systems programming
- **SQL** - Database query and schema design
- **Shell** - Command-line scripting and automation

## Natural Language Support

- **English (en)** - Primary language for prompts and documentation
- **Chinese (zh)** - Simplified Chinese translations
- **Spanish (es)** - Spanish translations
- **French (fr)** - French translations
- **German (de)** - German translations
- **Japanese (ja)** - Japanese translations (planned)
- **Korean (ko)** - Korean translations (planned)

## Quality Assurance Metrics

### Content Quality Metrics
- Prompt clarity and completeness
- Reference solution correctness
- Test case coverage and validity
- Metadata completeness

### Distribution Metrics
- Programming language distribution
- Difficulty level balance
- Context mode variety
- Scenario type coverage

### Technical Metrics
- Syntax validation for all code
- Code execution validation
- Performance benchmarking
- Security vulnerability assessment

### Production Readiness Metrics
- Dataset size requirements (100+ items per scenario)
- Comprehensive metadata
- Complete test coverage
- Quality grade assessment

## Best Practices

### Dataset Generation
1. **Balanced Distribution**: Ensure balanced distribution across languages, difficulties, and context modes
2. **Quality Over Quantity**: Focus on high-quality problems rather than just meeting size requirements
3. **Comprehensive Testing**: Include comprehensive test cases for all generated problems
4. **Metadata Completeness**: Ensure all metadata fields are properly populated

### Validation and QA
1. **Multi-Level Validation**: Run validation at multiple levels (basic, comprehensive, production)
2. **Regular Quality Checks**: Perform regular quality assurance checks during development
3. **Automated Testing**: Use automated testing to catch issues early
4. **Continuous Improvement**: Use validation results to improve generation algorithms

### Multilingual Support
1. **Cultural Sensitivity**: Ensure prompts are culturally appropriate for target languages
2. **Technical Accuracy**: Maintain technical accuracy across language translations
3. **Consistent Terminology**: Use consistent technical terminology across languages
4. **Native Review**: Have native speakers review translations when possible

## Troubleshooting

### Common Issues

1. **Generation Failures**
   - Check that base directories exist
   - Verify write permissions
   - Ensure sufficient disk space

2. **Validation Errors**
   - Review schema requirements
   - Check for missing required fields
   - Validate JSON format

3. **Quality Assurance Failures**
   - Review content quality guidelines
   - Check syntax validation requirements
   - Ensure metadata completeness

4. **Performance Issues**
   - Use parallel processing for large datasets
   - Monitor memory usage during generation
   - Consider batch processing for very large datasets

### Error Recovery

1. **Partial Failures**: The system handles partial failures gracefully and continues processing
2. **Resume Capability**: Failed expansions can be resumed from the last successful point
3. **Backup and Recovery**: Always backup existing datasets before expansion
4. **Rollback Support**: Failed expansions can be rolled back to previous state

## Integration with lm-eval

The expanded datasets are fully compatible with the lm-evaluation-harness framework:

1. **Task Registration**: All generated tasks are properly registered with lm-eval
2. **Evaluation Compatibility**: Datasets work with existing evaluation workflows
3. **Metric Integration**: Custom metrics are integrated with lm-eval's metric system
4. **Configuration Support**: Support for lm-eval configuration files and parameters

## Contributing

To contribute to the dataset expansion tools:

1. **Test Changes**: Always run the test suite before submitting changes
2. **Follow Standards**: Follow the established coding and documentation standards
3. **Add Tests**: Add tests for new functionality
4. **Update Documentation**: Update documentation for any changes

## License

All dataset expansion tools are released under the MIT License, ensuring compatibility with the broader lm-evaluation-harness ecosystem.