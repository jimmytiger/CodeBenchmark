#!/bin/bash
# Run All Examples Script for EvaluationEngineV1_0 Testing Framework
# This script runs all available examples in sequence

set -e  # Exit on any error

echo "=== EvaluationEngineV1_0 Run All Examples ==="
echo "This script will run all available examples in sequence"
echo

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLES_DIR="$(dirname "$SCRIPT_DIR")"
TEST_FRAMEWORK_DIR="$(dirname "$EXAMPLES_DIR")"
RUN_LOG="$EXAMPLES_DIR/run_all_examples.log"

# Initialize log
echo "Run all examples started at $(date)" > "$RUN_LOG"

# Results tracking
declare -A EXAMPLE_RESULTS
TOTAL_EXAMPLES=0
SUCCESSFUL_EXAMPLES=0

# Function to run example and track results
run_example() {
    local category="$1"
    local name="$2"
    local command="$3"
    local description="$4"
    
    echo "=== Running $category: $name ==="
    echo "Description: $description"
    echo "Command: $command"
    echo
    
    TOTAL_EXAMPLES=$((TOTAL_EXAMPLES + 1))
    
    # Create category results directory
    mkdir -p "$EXAMPLES_DIR/results/$category"
    
    local start_time=$(date +%s)
    local result_key="${category}_${name}"
    
    # Run the example
    if eval "$command" >> "$RUN_LOG" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        EXAMPLE_RESULTS["$result_key"]="SUCCESS:${duration}s"
        SUCCESSFUL_EXAMPLES=$((SUCCESSFUL_EXAMPLES + 1))
        
        echo "✓ $name completed successfully (${duration}s)"
        echo "  Logs appended to: $RUN_LOG"
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        EXAMPLE_RESULTS["$result_key"]="FAILED:${duration}s"
        
        echo "✗ $name failed (${duration}s)"
        echo "  Check logs for details: $RUN_LOG"
        echo "  Last few lines of error:"
        tail -5 "$RUN_LOG" | sed 's/^/    /'
    fi
    echo
}

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    # Check if we're in the right directory
    if [ ! -d "$TEST_FRAMEWORK_DIR/cli" ] || [ ! -d "$TEST_FRAMEWORK_DIR/api" ]; then
        echo "✗ Not in the correct directory structure"
        echo "Please run this script from the examples directory"
        return 1
    fi
    
    # Check Python availability
    if ! command -v python &> /dev/null; then
        echo "✗ Python is not available"
        return 1
    fi
    
    # Check basic imports
    if ! python -c "import sys; sys.path.insert(0, '$TEST_FRAMEWORK_DIR'); from cli.cli_test_runner import CLITestRunner" 2>/dev/null; then
        echo "✗ Testing framework components not available"
        echo "Please ensure the framework is properly installed"
        return 1
    fi
    
    echo "✓ Prerequisites check passed"
    return 0
}

# Function to setup environment
setup_environment() {
    echo "Setting up environment..."
    
    # Run setup script if available
    if [ -f "$SCRIPT_DIR/setup_examples.sh" ]; then
        echo "Running setup script..."
        if "$SCRIPT_DIR/setup_examples.sh" >> "$RUN_LOG" 2>&1; then
            echo "✓ Setup completed successfully"
        else
            echo "⚠️  Setup had issues, but continuing..."
        fi
    else
        echo "⚠️  Setup script not found, continuing without setup"
    fi
    
    # Create results directories
    mkdir -p "$EXAMPLES_DIR/results/cli"
    mkdir -p "$EXAMPLES_DIR/results/api"
    mkdir -p "$EXAMPLES_DIR/results/adapters"
    mkdir -p "$EXAMPLES_DIR/results/workflows"
    mkdir -p "$EXAMPLES_DIR/results/configs"
    
    echo "✓ Environment setup completed"
}

# Main execution
main() {
    echo "Starting comprehensive example execution..."
    echo "Log file: $RUN_LOG"
    echo
    
    # Check prerequisites
    if ! check_prerequisites; then
        echo "Prerequisites check failed. Exiting."
        exit 1
    fi
    
    # Setup environment
    setup_environment
    
    echo "Beginning example execution..."
    echo
    
    # 1. CLI Examples
    echo "1. CLI EXAMPLES"
    echo "==============="
    
    if [ -f "$EXAMPLES_DIR/cli/basic_cli_examples.sh" ]; then
        run_example "cli" "basic" \
            "cd '$EXAMPLES_DIR/cli' && ./basic_cli_examples.sh" \
            "Basic CLI functionality and command examples"
    else
        echo "⚠️  Basic CLI examples not found, skipping"
    fi
    
    if [ -f "$EXAMPLES_DIR/cli/advanced_cli_examples.sh" ]; then
        run_example "cli" "advanced" \
            "cd '$EXAMPLES_DIR/cli' && ./advanced_cli_examples.sh" \
            "Advanced CLI features and complex scenarios"
    else
        echo "⚠️  Advanced CLI examples not found, skipping"
    fi
    
    # 2. API Examples
    echo "2. API EXAMPLES"
    echo "==============="
    
    if [ -f "$EXAMPLES_DIR/api/basic_api_examples.sh" ]; then
        run_example "api" "basic" \
            "cd '$EXAMPLES_DIR/api' && timeout 300 ./basic_api_examples.sh" \
            "Basic API testing with curl commands"
    else
        echo "⚠️  Basic API examples not found, skipping"
    fi
    
    if [ -f "$EXAMPLES_DIR/api/comprehensive_curl_examples.sh" ]; then
        # Check if API server is running, if not skip this test
        if curl -s "http://localhost:8001/health" > /dev/null 2>&1; then
            run_example "api" "comprehensive" \
                "cd '$EXAMPLES_DIR/api' && timeout 600 ./comprehensive_curl_examples.sh" \
                "Comprehensive API testing with all endpoints"
        else
            echo "⚠️  API server not running, skipping comprehensive API examples"
            echo "   Start server manually or run basic API examples first"
        fi
    else
        echo "⚠️  Comprehensive API examples not found, skipping"
    fi
    
    # 3. Adapter Examples
    echo "3. ADAPTER EXAMPLES"
    echo "==================="
    
    if [ -f "$EXAMPLES_DIR/adapters/lm_eval_examples.py" ]; then
        run_example "adapters" "lm_eval" \
            "cd '$EXAMPLES_DIR/adapters' && timeout 600 python lm_eval_examples.py" \
            "LM-Eval adapter validation and testing"
    else
        echo "⚠️  LM-Eval adapter examples not found, skipping"
    fi
    
    # 4. Workflow Examples
    echo "4. WORKFLOW EXAMPLES"
    echo "===================="
    
    if [ -f "$EXAMPLES_DIR/workflows/quick_validation.py" ]; then
        run_example "workflows" "quick_validation" \
            "cd '$EXAMPLES_DIR/workflows' && timeout 900 python quick_validation.py" \
            "Quick validation workflow for framework testing"
    else
        echo "⚠️  Quick validation workflow not found, skipping"
    fi
    
    # 5. Configuration Examples
    echo "5. CONFIGURATION EXAMPLES"
    echo "========================="
    
    run_example "configs" "validation" \
        "cd '$EXAMPLES_DIR' && python -c '
import yaml
import sys
configs = [\"configs/basic_test_config.yaml\", \"configs/advanced_test_config.yaml\"]
for config_file in configs:
    try:
        with open(config_file, \"r\") as f:
            config = yaml.safe_load(f)
        print(f\"✓ {config_file}: Valid YAML with {len(config)} sections\")
    except Exception as e:
        print(f\"✗ {config_file}: {e}\")
        sys.exit(1)
print(\"All configuration files validated successfully\")
'" \
        "Validate all configuration file examples"
    
    # Summary Report
    echo "=== EXECUTION SUMMARY ==="
    echo "Total examples attempted: $TOTAL_EXAMPLES"
    echo "Successful examples: $SUCCESSFUL_EXAMPLES"
    echo "Failed examples: $((TOTAL_EXAMPLES - SUCCESSFUL_EXAMPLES))"
    echo "Success rate: $(( SUCCESSFUL_EXAMPLES * 100 / TOTAL_EXAMPLES ))%" 2>/dev/null || echo "Success rate: N/A"
    echo
    
    # Detailed results
    echo "Detailed Results:"
    for key in "${!EXAMPLE_RESULTS[@]}"; do
        local category=$(echo "$key" | cut -d'_' -f1)
        local name=$(echo "$key" | cut -d'_' -f2-)
        local result="${EXAMPLE_RESULTS[$key]}"
        local status=$(echo "$result" | cut -d':' -f1)
        local duration=$(echo "$result" | cut -d':' -f2)
        
        if [ "$status" = "SUCCESS" ]; then
            echo "  ✓ $category/$name: $status ($duration)"
        else
            echo "  ✗ $category/$name: $status ($duration)"
        fi
    done
    echo
    
    # Generate summary report file
    cat > "$EXAMPLES_DIR/execution_summary.json" << EOF
{
  "execution_date": "$(date -Iseconds)",
  "total_examples": $TOTAL_EXAMPLES,
  "successful_examples": $SUCCESSFUL_EXAMPLES,
  "failed_examples": $((TOTAL_EXAMPLES - SUCCESSFUL_EXAMPLES)),
  "success_rate": $(echo "scale=2; $SUCCESSFUL_EXAMPLES * 100 / $TOTAL_EXAMPLES" | bc 2>/dev/null || echo "0"),
  "results": {
EOF
    
    local first=true
    for key in "${!EXAMPLE_RESULTS[@]}"; do
        local category=$(echo "$key" | cut -d'_' -f1)
        local name=$(echo "$key" | cut -d'_' -f2-)
        local result="${EXAMPLE_RESULTS[$key]}"
        local status=$(echo "$result" | cut -d':' -f1)
        local duration=$(echo "$result" | cut -d':' -f2)
        
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> "$EXAMPLES_DIR/execution_summary.json"
        fi
        
        echo "    \"${category}_${name}\": {" >> "$EXAMPLES_DIR/execution_summary.json"
        echo "      \"category\": \"$category\"," >> "$EXAMPLES_DIR/execution_summary.json"
        echo "      \"name\": \"$name\"," >> "$EXAMPLES_DIR/execution_summary.json"
        echo "      \"status\": \"$status\"," >> "$EXAMPLES_DIR/execution_summary.json"
        echo "      \"duration\": \"$duration\"" >> "$EXAMPLES_DIR/execution_summary.json"
        echo -n "    }" >> "$EXAMPLES_DIR/execution_summary.json"
    done
    
    cat >> "$EXAMPLES_DIR/execution_summary.json" << EOF

  }
}
EOF
    
    echo "Summary report saved to: $EXAMPLES_DIR/execution_summary.json"
    echo "Detailed logs saved to: $RUN_LOG"
    echo
    
    # Final recommendations
    echo "Recommendations:"
    if [ $SUCCESSFUL_EXAMPLES -eq $TOTAL_EXAMPLES ]; then
        echo "  🎉 All examples completed successfully!"
        echo "  • The testing framework is fully functional"
        echo "  • All components are working as expected"
        echo "  • You can proceed with confidence to use the framework"
    elif [ $SUCCESSFUL_EXAMPLES -ge $((TOTAL_EXAMPLES * 80 / 100)) ]; then
        echo "  ✅ Most examples completed successfully"
        echo "  • The framework is largely functional"
        echo "  • Review failed examples for minor issues"
        echo "  • Consider addressing failures for complete functionality"
    elif [ $SUCCESSFUL_EXAMPLES -ge $((TOTAL_EXAMPLES * 50 / 100)) ]; then
        echo "  ⚠️  Some examples failed"
        echo "  • The framework has significant issues"
        echo "  • Review the logs carefully for error details"
        echo "  • Consider reinstalling or checking dependencies"
    else
        echo "  ❌ Many examples failed"
        echo "  • The framework has major issues"
        echo "  • Check the installation and environment setup"
        echo "  • Review prerequisites and dependencies"
        echo "  • Consider seeking support or reinstalling"
    fi
    echo
    
    # Exit with appropriate code
    if [ $SUCCESSFUL_EXAMPLES -eq $TOTAL_EXAMPLES ]; then
        echo "All examples completed successfully! 🎉"
        exit 0
    else
        echo "Some examples failed. Check the logs for details. ⚠️"
        exit 1
    fi
}

# Handle interruption
trap 'echo ""; echo "Example execution interrupted by user"; exit 1' INT

# Run main function
main "$@"