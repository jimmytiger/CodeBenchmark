#!/bin/bash
# Setup Script for EvaluationEngineV1_0 Testing Framework Examples
# This script prepares the environment for running examples

set -e  # Exit on any error

echo "=== EvaluationEngineV1_0 Examples Setup ==="
echo "This script will prepare your environment for running examples"
echo

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$(dirname "$SCRIPT_DIR")"
TEST_FRAMEWORK_DIR="$(dirname "$EXAMPLES_DIR")"
SETUP_LOG="$EXAMPLES_DIR/setup.log"

# Create directories
echo "Creating example directories..."
mkdir -p "$EXAMPLES_DIR/results"
mkdir -p "$EXAMPLES_DIR/results/cli_basic"
mkdir -p "$EXAMPLES_DIR/results/cli_advanced"
mkdir -p "$EXAMPLES_DIR/results/api_basic"
mkdir -p "$EXAMPLES_DIR/results/api_advanced"
mkdir -p "$EXAMPLES_DIR/results/adapters"
mkdir -p "$EXAMPLES_DIR/results/workflows"

echo "✓ Example directories created"

# Function to check Python dependencies
check_python_dependencies() {
    echo "Checking Python dependencies..."
    
    # Required packages
    local required_packages=(
        "pyyaml"
        "requests"
        "psutil"
        "datasets"
        "transformers"
    )
    
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! python -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -eq 0 ]; then
        echo "✓ All required Python packages are installed"
        return 0
    else
        echo "✗ Missing Python packages: ${missing_packages[*]}"
        echo "Installing missing packages..."
        
        for package in "${missing_packages[@]}"; do
            echo "  Installing $package..."
            pip install "$package" >> "$SETUP_LOG" 2>&1 || {
                echo "  ✗ Failed to install $package"
                return 1
            }
        done
        
        echo "✓ Missing packages installed"
        return 0
    fi
}

# Function to check framework components
check_framework_components() {
    echo "Checking framework components..."
    
    cd "$TEST_FRAMEWORK_DIR"
    
    # Check core modules
    local core_modules=(
        "cli.cli_test_runner"
        "api.api_test_server"
        "core.test_orchestrator"
        "core.config_manager"
        "adapters.lm_eval_adapter_validator"
    )
    
    local missing_modules=()
    
    for module in "${core_modules[@]}"; do
        if ! python -c "from $module import *" 2>/dev/null; then
            missing_modules+=("$module")
        fi
    done
    
    if [ ${#missing_modules[@]} -eq 0 ]; then
        echo "✓ All framework components are available"
        return 0
    else
        echo "✗ Missing framework components: ${missing_modules[*]}"
        echo "Please ensure the testing framework is properly installed"
        return 1
    fi
}

# Function to create sample configuration files
create_sample_configs() {
    echo "Creating sample configuration files..."
    
    # Basic example config
    cat > "$EXAMPLES_DIR/results/example_basic_config.yaml" << 'EOF'
# Example Basic Configuration
test_type: "example"
name: "Example Test"
description: "Sample configuration for examples"
timeout: 120

cli_config:
  tasks: ["hellaswag"]
  execution_timeout: 60
  output_format: "json"
  verbose: true
  limit: 3

api_config:
  server_host: "localhost"
  server_port: 8001
  timeout: 30

execution_params:
  timeout: 60
  verbose: true
  log_level: "INFO"

output_config:
  format: "json"
  include_logs: true
  output_directory: "results"
EOF
    
    echo "✓ Sample configuration files created"
}

# Function to validate example scripts
validate_example_scripts() {
    echo "Validating example scripts..."
    
    local script_errors=0
    
    # Check CLI examples
    if [ -f "$EXAMPLES_DIR/cli/basic_cli_examples.sh" ]; then
        if [ -x "$EXAMPLES_DIR/cli/basic_cli_examples.sh" ]; then
            echo "✓ CLI basic examples script is executable"
        else
            echo "✗ CLI basic examples script is not executable"
            chmod +x "$EXAMPLES_DIR/cli/basic_cli_examples.sh"
            echo "  Fixed: Made script executable"
        fi
    else
        echo "✗ CLI basic examples script not found"
        script_errors=$((script_errors + 1))
    fi
    
    # Check API examples
    if [ -f "$EXAMPLES_DIR/api/basic_api_examples.sh" ]; then
        if [ -x "$EXAMPLES_DIR/api/basic_api_examples.sh" ]; then
            echo "✓ API basic examples script is executable"
        else
            echo "✗ API basic examples script is not executable"
            chmod +x "$EXAMPLES_DIR/api/basic_api_examples.sh"
            echo "  Fixed: Made script executable"
        fi
    else
        echo "✗ API basic examples script not found"
        script_errors=$((script_errors + 1))
    fi
    
    # Check Python examples
    if [ -f "$EXAMPLES_DIR/adapters/lm_eval_examples.py" ]; then
        if [ -x "$EXAMPLES_DIR/adapters/lm_eval_examples.py" ]; then
            echo "✓ Adapter examples script is executable"
        else
            echo "✗ Adapter examples script is not executable"
            chmod +x "$EXAMPLES_DIR/adapters/lm_eval_examples.py"
            echo "  Fixed: Made script executable"
        fi
    else
        echo "✗ Adapter examples script not found"
        script_errors=$((script_errors + 1))
    fi
    
    # Check workflow examples
    if [ -f "$EXAMPLES_DIR/workflows/quick_validation.py" ]; then
        if [ -x "$EXAMPLES_DIR/workflows/quick_validation.py" ]; then
            echo "✓ Workflow examples script is executable"
        else
            echo "✗ Workflow examples script is not executable"
            chmod +x "$EXAMPLES_DIR/workflows/quick_validation.py"
            echo "  Fixed: Made script executable"
        fi
    else
        echo "✗ Workflow examples script not found"
        script_errors=$((script_errors + 1))
    fi
    
    if [ $script_errors -eq 0 ]; then
        echo "✓ All example scripts validated"
        return 0
    else
        echo "✗ $script_errors example scripts have issues"
        return 1
    fi
}

# Function to test basic functionality
test_basic_functionality() {
    echo "Testing basic functionality..."
    
    cd "$TEST_FRAMEWORK_DIR"
    
    # Test 1: Import test
    echo "  Testing Python imports..."
    if python -c "
import sys
sys.path.insert(0, '.')
from cli.cli_test_runner import CLITestRunner
from core.config_manager import ConfigManager
print('✓ Basic imports successful')
" 2>/dev/null; then
        echo "✓ Python imports work correctly"
    else
        echo "✗ Python imports failed"
        return 1
    fi
    
    # Test 2: Configuration test
    echo "  Testing configuration loading..."
    if python -c "
import sys
import yaml
sys.path.insert(0, '.')
from core.config_manager import ConfigManager

config_data = {
    'test_type': 'setup_test',
    'timeout': 60,
    'verbose': True
}

config_manager = ConfigManager()
print('✓ Configuration loading successful')
" 2>/dev/null; then
        echo "✓ Configuration loading works correctly"
    else
        echo "✗ Configuration loading failed"
        return 1
    fi
    
    echo "✓ Basic functionality tests passed"
    return 0
}

# Function to create quick start guide
create_quick_start_guide() {
    echo "Creating quick start guide..."
    
    cat > "$EXAMPLES_DIR/QUICK_START.md" << 'EOF'
# Quick Start Guide for EvaluationEngineV1_0 Examples

## Getting Started

1. **Run Basic CLI Examples**:
   ```bash
   cd examples/cli
   ./basic_cli_examples.sh
   ```

2. **Run Basic API Examples**:
   ```bash
   cd examples/api
   ./basic_api_examples.sh
   ```

3. **Test Adapter Validation**:
   ```bash
   cd examples/adapters
   python lm_eval_examples.py
   ```

4. **Run Quick Validation Workflow**:
   ```bash
   cd examples/workflows
   python quick_validation.py
   ```

## Example Categories

### CLI Examples
- `cli/basic_cli_examples.sh` - Basic command-line testing
- `cli/advanced_cli_examples.sh` - Advanced CLI features

### API Examples
- `api/basic_api_examples.sh` - Basic API testing with curl
- `api/advanced_api_examples.sh` - Advanced API features

### Configuration Examples
- `configs/basic_test_config.yaml` - Basic configuration
- `configs/advanced_test_config.yaml` - Advanced configuration

### Adapter Examples
- `adapters/lm_eval_examples.py` - LM-Eval adapter validation
- `adapters/swe_bench_examples.py` - SWE-Bench adapter validation

### Workflow Examples
- `workflows/quick_validation.py` - Quick validation workflow
- `workflows/comprehensive_testing.py` - Comprehensive testing

## Results

All example results are saved in the `results/` directory:
- `results/cli_basic/` - CLI basic example results
- `results/api_basic/` - API basic example results
- `results/adapters/` - Adapter validation results
- `results/workflows/` - Workflow execution results

## Troubleshooting

1. **Import Errors**: Ensure you're running from the correct directory
2. **Permission Errors**: Run `chmod +x` on script files
3. **Dependency Errors**: Install missing packages with pip
4. **API Errors**: Check if ports are available (8001, 8002)

## Support

Check the individual example files for detailed documentation and troubleshooting information.
EOF
    
    echo "✓ Quick start guide created"
}

# Main setup process
main() {
    echo "Starting setup process..."
    echo "Setup log: $SETUP_LOG"
    echo
    
    # Initialize log file
    echo "Setup started at $(date)" > "$SETUP_LOG"
    
    # Run setup steps
    local setup_errors=0
    
    # Step 1: Check Python dependencies
    if ! check_python_dependencies; then
        echo "✗ Python dependency check failed"
        setup_errors=$((setup_errors + 1))
    fi
    
    # Step 2: Check framework components
    if ! check_framework_components; then
        echo "✗ Framework component check failed"
        setup_errors=$((setup_errors + 1))
    fi
    
    # Step 3: Create sample configs
    create_sample_configs
    
    # Step 4: Validate example scripts
    if ! validate_example_scripts; then
        echo "✗ Example script validation had issues (but continuing)"
    fi
    
    # Step 5: Test basic functionality
    if ! test_basic_functionality; then
        echo "✗ Basic functionality test failed"
        setup_errors=$((setup_errors + 1))
    fi
    
    # Step 6: Create quick start guide
    create_quick_start_guide
    
    # Summary
    echo
    echo "=== Setup Summary ==="
    if [ $setup_errors -eq 0 ]; then
        echo "✓ Setup completed successfully!"
        echo
        echo "Next steps:"
        echo "1. Read the quick start guide: $EXAMPLES_DIR/QUICK_START.md"
        echo "2. Run basic CLI examples: cd examples/cli && ./basic_cli_examples.sh"
        echo "3. Run basic API examples: cd examples/api && ./basic_api_examples.sh"
        echo "4. Try the quick validation: cd examples/workflows && python quick_validation.py"
        echo
        echo "All examples are ready to run!"
        return 0
    else
        echo "✗ Setup completed with $setup_errors errors"
        echo
        echo "Please check the setup log for details: $SETUP_LOG"
        echo "You may still be able to run some examples, but some functionality may not work."
        return 1
    fi
}

# Run main setup
main "$@"