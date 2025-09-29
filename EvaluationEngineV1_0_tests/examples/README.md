# EvaluationEngineV1_0 Testing Framework Examples

This directory contains comprehensive working examples and demonstrations for the EvaluationEngineV1_0 testing framework.

## Directory Structure

```
examples/
├── README.md                           # This file
├── cli/                               # CLI usage examples
│   ├── basic_cli_examples.sh          # Basic CLI command examples
│   ├── advanced_cli_examples.sh       # Advanced CLI usage patterns
│   ├── builtin_task_examples.sh       # Builtin task testing examples
│   ├── custom_task_examples.sh        # Custom task testing examples
│   └── adapter_validation_examples.sh # Adapter validation examples
├── api/                               # API testing examples
│   ├── basic_api_examples.sh          # Basic API curl commands
│   ├── advanced_api_examples.sh       # Advanced API testing patterns
│   ├── concurrent_testing.sh          # Concurrent evaluation examples
│   ├── workflow_examples.sh           # Complete workflow examples
│   └── monitoring_examples.sh         # Evaluation monitoring examples
├── configs/                           # Sample configuration files
│   ├── basic_test_config.yaml         # Basic test configuration
│   ├── advanced_test_config.yaml      # Advanced test configuration
│   ├── cli_specific_config.yaml       # CLI-specific configuration
│   ├── api_specific_config.yaml       # API-specific configuration
│   ├── adapter_test_config.yaml       # Adapter testing configuration
│   ├── performance_test_config.yaml   # Performance testing configuration
│   └── production_config.yaml         # Production-ready configuration
├── adapters/                          # Adapter validation examples
│   ├── lm_eval_examples.py            # lm_eval adapter examples
│   ├── swe_bench_examples.py          # swe_bench adapter examples
│   └── adapter_comparison.py          # Adapter comparison examples
├── workflows/                         # Complete workflow examples
│   ├── quick_validation.py            # Quick validation workflow
│   ├── comprehensive_testing.py       # Comprehensive testing workflow
│   ├── performance_benchmarking.py    # Performance benchmarking workflow
│   └── continuous_integration.py      # CI/CD integration examples
└── scripts/                           # Utility scripts
    ├── setup_examples.sh              # Setup script for examples
    ├── run_all_examples.sh            # Run all examples
    ├── validate_examples.sh           # Validate example outputs
    └── cleanup_examples.sh            # Cleanup example artifacts
```

## Quick Start

1. **Setup Examples Environment**:
   ```bash
   cd EvaluationEngineV1_0_tests/examples
   ./scripts/setup_examples.sh
   ```

2. **Run Basic CLI Examples**:
   ```bash
   ./cli/basic_cli_examples.sh
   ```

3. **Run Basic API Examples**:
   ```bash
   ./api/basic_api_examples.sh
   ```

4. **Test Adapter Validation**:
   ```bash
   python adapters/lm_eval_examples.py
   ```

5. **Run Complete Workflow**:
   ```bash
   python workflows/quick_validation.py
   ```

## Example Categories

### CLI Examples
- Basic command-line testing
- Builtin task execution
- Custom task discovery and testing
- Adapter validation through CLI
- Configuration file usage
- Output formatting options

### API Examples
- REST API endpoint testing
- Curl command examples
- Concurrent evaluation requests
- Asynchronous evaluation monitoring
- Error handling and recovery
- Authentication and security

### Configuration Examples
- Basic test configurations
- Advanced parameter tuning
- Environment-specific settings
- Performance optimization
- Security configurations
- Production deployment settings

### Adapter Examples
- lm_eval adapter integration
- swe_bench adapter validation
- Custom adapter development
- Adapter performance comparison
- Error handling and debugging
- Real execution validation

### Workflow Examples
- Quick validation workflows
- Comprehensive testing suites
- Performance benchmarking
- Continuous integration setup
- Production deployment validation
- Monitoring and alerting

## Usage Guidelines

1. **Start with Basic Examples**: Begin with basic CLI and API examples to understand the framework
2. **Use Sample Configurations**: Modify the provided configuration files for your specific needs
3. **Test Incrementally**: Start with simple tests and gradually increase complexity
4. **Validate Real Execution**: Always ensure tests perform real execution, not mock data
5. **Monitor Performance**: Use performance examples to understand resource usage
6. **Check Documentation**: Each example includes detailed comments and documentation

## Requirements

- Python 3.8+
- EvaluationEngineV1_0 installed and configured
- Required dependencies (see requirements.txt)
- Sufficient system resources for real execution testing

## Support

For questions or issues with examples:
1. Check the troubleshooting section in each example
2. Review the main documentation
3. Check the logs for detailed error information
4. Ensure all dependencies are properly installed

## Contributing

When adding new examples:
1. Follow the existing directory structure
2. Include comprehensive documentation
3. Add error handling and validation
4. Test with real execution scenarios
5. Update this README with new examples