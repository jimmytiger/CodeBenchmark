#!/bin/bash

# AI Evaluation Engine - One-Click Installation Script
# This script sets up the complete evaluation environment with lm-eval integration

set -e  # Exit on any error

echo "🚀 AI Evaluation Engine Installation Starting..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.9+ is available
check_python() {
    print_status "Checking Python version..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
            print_success "Python $PYTHON_VERSION found"
            PYTHON_CMD="python3"
        else
            print_error "Python 3.9+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.9+"
        exit 1
    fi
}

# Check if Docker is available
check_docker() {
    print_status "Checking Docker installation..."
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            print_success "Docker is available and running"
            DOCKER_AVAILABLE=true
        else
            print_warning "Docker is installed but not running"
            print_status "Starting Docker..."
            # Try to start Docker (works on some systems)
            if sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null; then
                print_success "Docker started successfully"
                DOCKER_AVAILABLE=true
            else
                print_warning "Could not start Docker automatically. Please start Docker manually."
                DOCKER_AVAILABLE=false
            fi
        fi
    else
        print_warning "Docker not found. Secure code execution will be limited."
        DOCKER_AVAILABLE=false
    fi
}

# Create virtual environment
setup_venv() {
    print_status "Setting up Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        print_success "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    print_success "Virtual environment activated"
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip
}

# Install dependencies
install_dependencies() {
    print_status "Installing core dependencies..."
    
    # Install the package in development mode with all dependencies
    pip install -e ".[dev,api,testing,tasks]"
    
    print_success "Core dependencies installed"
    
    # Install additional dependencies for secure execution
    if [ "$DOCKER_AVAILABLE" = true ]; then
        print_status "Installing Docker Python client..."
        pip install docker
        print_success "Docker client installed"
    fi
    
    # Install optional dependencies for enhanced functionality
    print_status "Installing optional dependencies..."
    pip install jupyter notebook ipywidgets plotly pandas seaborn
    print_success "Optional dependencies installed"
}

# Setup Docker containers for secure execution
setup_docker_containers() {
    if [ "$DOCKER_AVAILABLE" = true ]; then
        print_status "Setting up Docker containers for secure code execution..."
        
        # Build language-specific containers
        docker build -f lm_eval/tasks/single_turn_scenarios/docker/python.Dockerfile -t ai-eval-python:latest lm_eval/tasks/single_turn_scenarios/docker/ || print_warning "Failed to build Python container"
        docker build -f lm_eval/tasks/single_turn_scenarios/docker/node.Dockerfile -t ai-eval-node:latest lm_eval/tasks/single_turn_scenarios/docker/ || print_warning "Failed to build Node.js container"
        docker build -f lm_eval/tasks/single_turn_scenarios/docker/java.Dockerfile -t ai-eval-java:latest lm_eval/tasks/single_turn_scenarios/docker/ || print_warning "Failed to build Java container"
        docker build -f lm_eval/tasks/single_turn_scenarios/docker/gcc.Dockerfile -t ai-eval-gcc:latest lm_eval/tasks/single_turn_scenarios/docker/ || print_warning "Failed to build GCC container"
        docker build -f lm_eval/tasks/single_turn_scenarios/docker/go.Dockerfile -t ai-eval-go:latest lm_eval/tasks/single_turn_scenarios/docker/ || print_warning "Failed to build Go container"
        docker build -f lm_eval/tasks/single_turn_scenarios/docker/rust.Dockerfile -t ai-eval-rust:latest lm_eval/tasks/single_turn_scenarios/docker/ || print_warning "Failed to build Rust container"
        
        print_success "Docker containers setup completed"
    else
        print_warning "Skipping Docker container setup (Docker not available)"
    fi
}

# Create configuration files
setup_config() {
    print_status "Setting up configuration files..."
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        cp lm_eval/tasks/single_turn_scenarios/.env.template .env
        print_success "Environment configuration created (.env)"
        print_warning "Please edit .env file to add your API keys"
    else
        print_status "Environment configuration already exists"
    fi
    
    # Create results directory
    mkdir -p results
    mkdir -p logs
    mkdir -p cache
    
    print_success "Directory structure created"
}

# Run basic tests
run_tests() {
    print_status "Running basic functionality tests..."
    
    # Test lm-eval integration
    if python -c "import lm_eval; print('lm-eval import successful')" 2>/dev/null; then
        print_success "lm-eval integration working"
    else
        print_error "lm-eval integration failed"
        exit 1
    fi
    
    # Test evaluation engine
    if python -c "import evaluation_engine; print('Evaluation engine import successful')" 2>/dev/null; then
        print_success "Evaluation engine working"
    else
        print_error "Evaluation engine import failed"
        exit 1
    fi
    
    # Run smoke test
    if [ -f "lm_eval/tasks/single_turn_scenarios/smoke_test.py" ]; then
        print_status "Running smoke test..."
        python lm_eval/tasks/single_turn_scenarios/smoke_test.py || print_warning "Smoke test had issues (may be due to missing API keys)"
    fi
}

# Main installation flow
main() {
    echo "🔧 AI Evaluation Engine Installation"
    echo "===================================="
    
    check_python
    check_docker
    setup_venv
    install_dependencies
    setup_docker_containers
    setup_config
    run_tests
    
    echo ""
    echo "🎉 Installation Complete!"
    echo "========================"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file to add your API keys"
    echo "2. Activate the virtual environment: source venv/bin/activate"
    echo "3. Run a test evaluation: python -m lm_eval --model claude_local --tasks single_turn_scenarios_function_generation --limit 1"
    echo ""
    echo "For more information, see:"
    echo "- README.md for general usage"
    echo "- lm_eval/tasks/single_turn_scenarios/CLI_USAGE.md for CLI examples"
    echo "- lm_eval/tasks/multi_turn_scenarios/USAGE_GUIDE.md for multi-turn scenarios"
    echo ""
    print_success "Ready to evaluate AI models! 🚀"
}

# Run main function
main "$@"