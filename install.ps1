# AI Evaluation Engine - Windows Installation Script
# PowerShell script for Windows users

param(
    [switch]$SkipDocker,
    [switch]$Verbose
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Color functions for output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

Write-Host "🚀 AI Evaluation Engine Installation Starting..." -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Check Python version
function Test-Python {
    Write-Status "Checking Python version..."
    
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            
            if ($major -eq 3 -and $minor -ge 9) {
                Write-Success "Python $($matches[0]) found"
                return $true
            } else {
                Write-Error "Python 3.9+ required, found $($matches[0])"
                return $false
            }
        }
    } catch {
        Write-Error "Python not found. Please install Python 3.9+"
        return $false
    }
}

# Check Docker availability
function Test-Docker {
    if ($SkipDocker) {
        Write-Warning "Skipping Docker check (--SkipDocker specified)"
        return $false
    }
    
    Write-Status "Checking Docker installation..."
    
    try {
        $dockerVersion = docker --version 2>&1
        docker info | Out-Null
        Write-Success "Docker is available and running"
        return $true
    } catch {
        Write-Warning "Docker not available. Secure code execution will be limited."
        return $false
    }
}

# Setup virtual environment
function Setup-VirtualEnvironment {
    Write-Status "Setting up Python virtual environment..."
    
    if (-not (Test-Path "venv")) {
        python -m venv venv
        Write-Success "Virtual environment created"
    } else {
        Write-Status "Virtual environment already exists"
    }
    
    # Activate virtual environment
    & "venv\Scripts\Activate.ps1"
    Write-Success "Virtual environment activated"
    
    # Upgrade pip
    Write-Status "Upgrading pip..."
    python -m pip install --upgrade pip
}

# Install dependencies
function Install-Dependencies {
    Write-Status "Installing core dependencies..."
    
    # Install the package in development mode with all dependencies
    pip install -e ".[dev,api,testing,tasks]"
    Write-Success "Core dependencies installed"
    
    # Install additional dependencies
    Write-Status "Installing optional dependencies..."
    pip install jupyter notebook ipywidgets plotly pandas seaborn
    Write-Success "Optional dependencies installed"
}

# Setup Docker containers
function Setup-DockerContainers {
    param([bool]$DockerAvailable)
    
    if ($DockerAvailable) {
        Write-Status "Setting up Docker containers for secure code execution..."
        
        $dockerFiles = @(
            @{Name="python"; File="lm_eval/tasks/single_turn_scenarios/docker/python.Dockerfile"; Tag="ai-eval-python:latest"},
            @{Name="node"; File="lm_eval/tasks/single_turn_scenarios/docker/node.Dockerfile"; Tag="ai-eval-node:latest"},
            @{Name="java"; File="lm_eval/tasks/single_turn_scenarios/docker/java.Dockerfile"; Tag="ai-eval-java:latest"},
            @{Name="gcc"; File="lm_eval/tasks/single_turn_scenarios/docker/gcc.Dockerfile"; Tag="ai-eval-gcc:latest"},
            @{Name="go"; File="lm_eval/tasks/single_turn_scenarios/docker/go.Dockerfile"; Tag="ai-eval-go:latest"},
            @{Name="rust"; File="lm_eval/tasks/single_turn_scenarios/docker/rust.Dockerfile"; Tag="ai-eval-rust:latest"}
        )
        
        foreach ($container in $dockerFiles) {
            try {
                docker build -f $container.File -t $container.Tag lm_eval/tasks/single_turn_scenarios/docker/
                Write-Success "$($container.Name) container built successfully"
            } catch {
                Write-Warning "Failed to build $($container.Name) container"
            }
        }
        
        Write-Success "Docker containers setup completed"
    } else {
        Write-Warning "Skipping Docker container setup (Docker not available)"
    }
}

# Setup configuration
function Setup-Configuration {
    Write-Status "Setting up configuration files..."
    
    # Create .env file if it doesn't exist
    if (-not (Test-Path ".env")) {
        Copy-Item "lm_eval/tasks/single_turn_scenarios/.env.template" ".env"
        Write-Success "Environment configuration created (.env)"
        Write-Warning "Please edit .env file to add your API keys"
    } else {
        Write-Status "Environment configuration already exists"
    }
    
    # Create directories
    $directories = @("results", "logs", "cache")
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir | Out-Null
        }
    }
    
    Write-Success "Directory structure created"
}

# Run tests
function Test-Installation {
    Write-Status "Running basic functionality tests..."
    
    # Test lm-eval integration
    try {
        python -c "import lm_eval; print('lm-eval import successful')"
        Write-Success "lm-eval integration working"
    } catch {
        Write-Error "lm-eval integration failed"
        throw
    }
    
    # Test evaluation engine
    try {
        python -c "import evaluation_engine; print('Evaluation engine import successful')"
        Write-Success "Evaluation engine working"
    } catch {
        Write-Error "Evaluation engine import failed"
        throw
    }
    
    # Run smoke test if available
    if (Test-Path "lm_eval/tasks/single_turn_scenarios/smoke_test.py") {
        Write-Status "Running smoke test..."
        try {
            python lm_eval/tasks/single_turn_scenarios/smoke_test.py
        } catch {
            Write-Warning "Smoke test had issues (may be due to missing API keys)"
        }
    }
}

# Main installation function
function Main {
    try {
        if (-not (Test-Python)) {
            exit 1
        }
        
        $dockerAvailable = Test-Docker
        
        Setup-VirtualEnvironment
        Install-Dependencies
        
        if ($dockerAvailable) {
            pip install docker
            Write-Success "Docker client installed"
        }
        
        Setup-DockerContainers -DockerAvailable $dockerAvailable
        Setup-Configuration
        Test-Installation
        
        Write-Host ""
        Write-Host "🎉 Installation Complete!" -ForegroundColor Green
        Write-Host "========================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:"
        Write-Host "1. Edit .env file to add your API keys"
        Write-Host "2. Activate the virtual environment: venv\Scripts\Activate.ps1"
        Write-Host "3. Run a test evaluation: python -m lm_eval --model claude_local --tasks single_turn_scenarios_function_generation --limit 1"
        Write-Host ""
        Write-Host "For more information, see:"
        Write-Host "- README.md for general usage"
        Write-Host "- lm_eval/tasks/single_turn_scenarios/CLI_USAGE.md for CLI examples"
        Write-Host "- lm_eval/tasks/multi_turn_scenarios/USAGE_GUIDE.md for multi-turn scenarios"
        Write-Host ""
        Write-Success "Ready to evaluate AI models! 🚀"
        
    } catch {
        Write-Error "Installation failed: $($_.Exception.Message)"
        exit 1
    }
}

# Run main function
Main