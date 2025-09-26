# AI Evaluation Engine

A comprehensive evaluation framework built on top of lm-evaluation-harness, designed to assess language models across diverse programming and problem-solving scenarios with advanced multi-turn conversation support and secure code execution.

## 🚀 Quick Start

### One-Click Installation

**Linux/macOS:**
```bash
./install.sh
```

**Windows:**
```powershell
.\install.ps1
```

### Manual Installation

1. **Prerequisites:**
   - Python 3.9+
   - Docker (optional, for secure code execution)
   - Git

2. **Install:**
   ```bash
   # Clone and install
   git clone <repository-url>
   cd ai-evaluation-engine
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install with all dependencies
   pip install -e ".[dev,api,testing,tasks]"
   ```

3. **Configure:**
   ```bash
   # Copy environment template
   cp lm_eval/tasks/single_turn_scenarios/.env.template .env
   
   # Edit .env to add your API keys
   nano .env
   ```

## 🏗️ Architecture

The AI Evaluation Engine extends lm-evaluation-harness with:

- **Extended Task Registry**: Hierarchical task organization with metadata
- **Multi-Turn Conversations**: Complex dialogue scenarios with context retention
- **Secure Code Execution**: Docker-based sandboxed execution environment
- **Advanced Metrics**: Comprehensive evaluation metrics and analysis
- **Model Adapters**: Support for multiple model backends (OpenAI, Anthropic, DashScope, etc.)
- **Real-time Monitoring**: Progress tracking and performance monitoring

## 📋 Available Tasks

### Single-Turn Scenarios
- `single_turn_scenarios_code_completion` - Code completion tasks
- `single_turn_scenarios_bug_fix` - Bug fixing scenarios
- `single_turn_scenarios_function_generation` - Function generation from specs
- `single_turn_scenarios_algorithm_implementation` - Algorithm implementation
- `single_turn_scenarios_api_design` - API design tasks
- `single_turn_scenarios_system_design` - System architecture design
- `single_turn_scenarios_security` - Security implementation
- `single_turn_scenarios_performance_optimization` - Performance tuning
- And more...

### Multi-Turn Scenarios
- `multi_turn_scenarios_code_review` - Interactive code review process
- `multi_turn_scenarios_debug_session` - Debugging conversations
- `multi_turn_scenarios_quantitative_strategy_development` - Trading strategy development
- `multi_turn_scenarios_teaching_dialogue` - Educational conversations
- And more...

## 🔧 Usage

### Basic Evaluation

```bash
# Evaluate a single task
python -m lm_eval --model claude_local --tasks single_turn_scenarios_function_generation --limit 5

# Evaluate multiple tasks
python -m lm_eval --model openai --tasks single_turn_scenarios_code_completion,single_turn_scenarios_bug_fix --limit 10

# Multi-turn evaluation
python -m lm_eval --model anthropic --tasks multi_turn_scenarios_code_review --limit 3
```

### Using the Unified Framework

```python
from evaluation_engine import UnifiedEvaluationFramework
from evaluation_engine.core.unified_framework import EvaluationRequest

# Create framework instance
framework = UnifiedEvaluationFramework()

# Create evaluation request
request = EvaluationRequest(
    model="claude_local",
    tasks=["single_turn_scenarios_function_generation"],
    limit=5,
    log_samples=True
)

# Run evaluation
result = framework.evaluate(request)

# Access results
print(f"Status: {result.status}")
print(f"Metrics: {result.metrics_summary}")
print(f"Analysis: {result.analysis}")
```

### Docker Deployment

```bash
# Start full stack with monitoring
docker-compose --profile monitoring up -d

# Start basic evaluation engine
docker-compose up ai-evaluation-engine

# Run evaluation in container
docker-compose exec ai-evaluation-engine python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation --limit 1
```

## 🔒 Security Features

- **Sandboxed Execution**: Docker containers with no network access
- **Resource Limits**: CPU, memory, disk, and time constraints
- **Static Analysis**: Pre-execution code scanning
- **Runtime Monitoring**: System call and resource monitoring
- **Security Auditing**: Comprehensive security logging

## 📊 Metrics and Analysis

### Standard Metrics
- **Code Quality**: Syntax validity, style compliance, maintainability
- **Functional**: Pass@K, execution success, correctness
- **Performance**: Execution time, memory usage, optimization
- **Security**: Vulnerability detection, best practices compliance

### Advanced Analysis
- **Cross-Model Comparison**: Benchmark positioning
- **Performance Patterns**: Strength and weakness identification
- **Statistical Analysis**: Significance testing, confidence intervals
- **Trend Analysis**: Performance over time

## 🔌 Model Support

### Supported Models
- **OpenAI**: GPT-4, GPT-3.5, GPT-4o
- **Anthropic**: Claude-3 Opus, Sonnet, Haiku
- **DashScope**: Qwen-Max, Qwen-Plus, Qwen-Turbo, Qwen-Coder
- **Google**: Gemini Pro, Gemini Ultra
- **Cohere**: Command models
- **HuggingFace**: Llama, Mistral, CodeLlama
- **Local**: Ollama, vLLM, TGI deployments

### Adding Custom Models

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

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest lm_eval/tasks/single_turn_scenarios/tests/unit/
pytest lm_eval/tasks/single_turn_scenarios/tests/integration/
pytest lm_eval/tasks/single_turn_scenarios/tests/security/

# Run performance benchmarks
pytest lm_eval/tasks/single_turn_scenarios/tests/performance/ --benchmark-only
```

## 📈 Monitoring and Observability

### Prometheus Metrics
- Evaluation success/failure rates
- Task execution times
- Model performance metrics
- Resource utilization

### Grafana Dashboards
- Real-time evaluation monitoring
- Performance trends
- Model comparison views
- System health metrics

### Logging
- Structured JSON logging
- Security event logging
- Performance profiling
- Error tracking

## 🔧 Configuration

### Environment Variables
```bash
# API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
DASHSCOPE_API_KEY=your_dashscope_key

# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost/ai_eval

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Security
ENABLE_SANDBOX=true
MAX_EXECUTION_TIME=300
MAX_MEMORY_MB=1024
```

### Task Configuration
```yaml
# tasks/my_custom_task/config.yml
task_name: "my_custom_task"
task_type: "single_turn"
description: "Custom evaluation task"

metadata:
  task_id: "custom_001"
  category: "custom"
  difficulty: "intermediate"
  tags: ["custom", "example"]

dataset:
  path: "problems.jsonl"
  format: "jsonl"

metrics:
  - "accuracy"
  - "code_quality"
  - "execution_success"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev,testing]"

# Install pre-commit hooks
pre-commit install

# Run linting
ruff check .
black .
isort .

# Run type checking
mypy lm_eval evaluation_engine
```

## 📚 Documentation

- [CLI Usage Guide](lm_eval/tasks/single_turn_scenarios/CLI_USAGE.md)
- [Multi-Turn Scenarios](lm_eval/tasks/multi_turn_scenarios/USAGE_GUIDE.md)
- [API Documentation](docs/API_guide.md)
- [Task Development Guide](docs/new_task_guide.md)
- [Security Best Practices](lm_eval/tasks/single_turn_scenarios/SECURITY_BEST_PRACTICES.md)

## 🐛 Troubleshooting

### Common Issues

1. **Docker not available**: Install Docker or use `--skip-docker` flag
2. **API key errors**: Check `.env` file configuration
3. **Memory issues**: Reduce batch size or limit
4. **Task not found**: Check task name spelling and availability

### Debug Mode
```bash
# Enable verbose logging
python -m lm_eval --model dummy --tasks single_turn_scenarios_function_generation --verbosity DEBUG

# Check environment
python lm_eval/tasks/single_turn_scenarios/diagnose_environment.py

# Validate configuration
python lm_eval/tasks/single_turn_scenarios/validate_config.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 🙏 Acknowledgments

- Built on top of [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
- Inspired by the open-source AI evaluation community
- Thanks to all contributors and maintainers

## 📞 Support

- GitHub Issues: [Report bugs and request features](https://github.com/your-repo/issues)
- Documentation: [Comprehensive guides and API docs](docs/)
- Community: [Join our discussions](https://github.com/your-repo/discussions)

---

**Ready to evaluate AI models comprehensively? Get started with the AI Evaluation Engine today! 🚀**