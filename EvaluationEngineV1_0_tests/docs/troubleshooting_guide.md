# EvaluationEngineV1_0 Testing Framework - Troubleshooting Guide

## Table of Contents

1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Configuration Issues](#configuration-issues)
4. [Execution Errors](#execution-errors)
5. [API Problems](#api-problems)
6. [Adapter Issues](#adapter-issues)
7. [Performance Problems](#performance-problems)
8. [Security and Permissions](#security-and-permissions)
9. [Debugging Tools](#debugging-tools)
10. [Getting Help](#getting-help)

## Common Issues

### Issue: "Module not found" errors

**Symptoms**:
```
ModuleNotFoundError: No module named 'evaluation_engine'
ImportError: cannot import name 'TestOrchestrator'
```

**Causes**:
- Missing dependencies
- Incorrect Python path
- Virtual environment not activated

**Solutions**:

1. **Install missing dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r test_requirements.txt
   ```

2. **Check Python path**:
   ```python
   import sys
   print(sys.path)
   
   # Add current directory to path
   sys.path.append('.')
   ```

3. **Activate virtual environment**:
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate (Linux/Mac)
   source venv/bin/activate
   
   # Activate (Windows)
   venv\Scripts\activate
   ```

4. **Verify installation**:
   ```bash
   python -c "import evaluation_engine; print('Success')"
   ```

### Issue: "Permission denied" errors

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: '/path/to/file'
OSError: [Errno 1] Operation not permitted
```

**Causes**:
- Insufficient file permissions
- Running without proper privileges
- File system restrictions

**Solutions**:

1. **Check file permissions**:
   ```bash
   ls -la /path/to/file
   chmod 755 /path/to/file
   ```

2. **Run with appropriate permissions**:
   ```bash
   # Linux/Mac
   sudo python script.py
   
   # Or change ownership
   sudo chown $USER:$USER /path/to/directory
   ```

3. **Use proper directories**:
   ```python
   import tempfile
   import os
   
   # Use temporary directory for testing
   temp_dir = tempfile.mkdtemp()
   os.environ['TEST_OUTPUT_DIR'] = temp_dir
   ```

### Issue: API connection failures

**Symptoms**:
```
ConnectionError: Failed to establish a new connection
requests.exceptions.ConnectTimeout: HTTPSConnectionPool
```

**Causes**:
- API server not running
- Incorrect URL or port
- Network connectivity issues
- Firewall blocking connections

**Solutions**:

1. **Verify API server is running**:
   ```bash
   # Check if server is running
   curl http://localhost:8000/api/v1/health
   
   # Start API server
   python api/api_test_server.py --host localhost --port 8000
   ```

2. **Check network connectivity**:
   ```bash
   # Test basic connectivity
   ping localhost
   telnet localhost 8000
   ```

3. **Verify configuration**:
   ```python
   # Check API configuration
   import requests
   
   try:
       response = requests.get("http://localhost:8000/api/v1/health", timeout=10)
       print(f"API Status: {response.status_code}")
   except Exception as e:
       print(f"Connection error: {e}")
   ```

### Issue: Tests hanging or timing out

**Symptoms**:
- Tests run indefinitely without completing
- Timeout errors after long waits
- No progress updates

**Causes**:
- Infinite loops in test code
- Blocked API calls
- Resource exhaustion
- Deadlocks

**Solutions**:

1. **Set appropriate timeouts**:
   ```yaml
   # In configuration file
   execution:
     timeout: 600  # 10 minutes
     task_timeout: 300  # 5 minutes per task
   ```

2. **Monitor resource usage**:
   ```bash
   # Monitor CPU and memory
   top -p $(pgrep -f python)
   
   # Check for hanging processes
   ps aux | grep python
   ```

3. **Enable debug logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   # Or in configuration
   logging:
     level: DEBUG
     detailed: true
   ```

4. **Use timeout decorators**:
   ```python
   import signal
   
   def timeout_handler(signum, frame):
       raise TimeoutError("Test timed out")
   
   signal.signal(signal.SIGALRM, timeout_handler)
   signal.alarm(300)  # 5 minute timeout
   ```

## Installation Problems

### Issue: Dependency conflicts

**Symptoms**:
```
ERROR: pip's dependency resolver does not currently consider all the packages
ERROR: Cannot install package due to conflicting dependencies
```

**Solutions**:

1. **Use fresh virtual environment**:
   ```bash
   # Remove existing environment
   rm -rf venv
   
   # Create new environment
   python -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Install dependencies individually**:
   ```bash
   # Install core dependencies first
   pip install requests pyyaml
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   pip install lm_eval
   ```

3. **Use conda environment**:
   ```bash
   conda create -n eval_engine python=3.9
   conda activate eval_engine
   pip install -r requirements.txt
   ```

### Issue: lm_eval installation problems

**Symptoms**:
```
ERROR: Failed building wheel for lm_eval
ModuleNotFoundError: No module named 'lm_eval'
```

**Solutions**:

1. **Install from source**:
   ```bash
   git clone https://github.com/EleutherAI/lm-evaluation-harness
   cd lm-evaluation-harness
   pip install -e .
   ```

2. **Install specific version**:
   ```bash
   pip install lm_eval==0.4.0
   ```

3. **Install with specific extras**:
   ```bash
   pip install lm_eval[api,openai]
   ```

### Issue: SWE-bench dependencies

**Symptoms**:
```
Docker not found
Git command failed
SWE-bench environment setup failed
```

**Solutions**:

1. **Install Docker**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install docker.io
   sudo systemctl start docker
   sudo usermod -aG docker $USER
   
   # Mac
   brew install docker
   
   # Verify installation
   docker --version
   ```

2. **Install Git**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install git
   
   # Mac
   brew install git
   
   # Verify installation
   git --version
   ```

3. **Configure SWE-bench**:
   ```bash
   # Clone SWE-bench repository
   git clone https://github.com/princeton-nlp/SWE-bench
   cd SWE-bench
   pip install -e .
   ```

## Configuration Issues

### Issue: Invalid configuration files

**Symptoms**:
```
yaml.scanner.ScannerError: mapping values are not allowed here
ConfigurationError: Invalid configuration format
```

**Solutions**:

1. **Validate YAML syntax**:
   ```python
   import yaml
   
   try:
       with open('config.yaml', 'r') as f:
           config = yaml.safe_load(f)
       print("Configuration is valid")
   except yaml.YAMLError as e:
       print(f"YAML error: {e}")
   ```

2. **Use configuration validator**:
   ```python
   from core.config_manager import ConfigManager
   
   config_manager = ConfigManager()
   validation_result = config_manager.validate_config('config.yaml')
   
   if not validation_result.is_valid:
       print(f"Configuration errors: {validation_result.errors}")
   ```

3. **Check indentation**:
   ```yaml
   # Correct indentation
   test_config:
     execution:
       timeout: 600
       max_retries: 3
   
   # Incorrect indentation (will cause error)
   test_config:
   execution:
     timeout: 600
   ```

### Issue: Missing API keys

**Symptoms**:
```
AuthenticationError: No API key provided
OpenAI API key not found
```

**Solutions**:

1. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   export ANTHROPIC_API_KEY="your_anthropic_key"
   
   # Verify
   echo $OPENAI_API_KEY
   ```

2. **Use .env file**:
   ```bash
   # Create .env file
   cat > .env << EOF
   OPENAI_API_KEY=your_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_key
   EOF
   
   # Load in Python
   from dotenv import load_dotenv
   load_dotenv()
   ```

3. **Configure in settings**:
   ```yaml
   # config.yaml
   model:
     name: "gpt-3.5-turbo"
     api_key: "${OPENAI_API_KEY}"
   ```

### Issue: Path configuration problems

**Symptoms**:
```
FileNotFoundError: No such file or directory
Path does not exist: /path/to/tasks
```

**Solutions**:

1. **Use absolute paths**:
   ```python
   import os
   from pathlib import Path
   
   # Get absolute path
   config_path = Path(__file__).parent / "configs" / "test_config.yaml"
   task_dir = os.path.abspath("../lm_eval/tasks")
   ```

2. **Verify paths exist**:
   ```python
   import os
   
   paths_to_check = [
       "configs/test_config.yaml",
       "../lm_eval/tasks",
       "./test_results"
   ]
   
   for path in paths_to_check:
       if os.path.exists(path):
           print(f"✓ {path} exists")
       else:
           print(f"✗ {path} missing")
   ```

3. **Create missing directories**:
   ```python
   import os
   
   # Create directories if they don't exist
   os.makedirs("test_results", exist_ok=True)
   os.makedirs("logs", exist_ok=True)
   ```

## Execution Errors

### Issue: Model API failures

**Symptoms**:
```
OpenAI API error: Rate limit exceeded
Anthropic API error: Invalid request
Model timeout error
```

**Solutions**:

1. **Implement retry logic**:
   ```python
   import time
   import random
   
   def retry_with_backoff(func, max_retries=3):
       for attempt in range(max_retries):
           try:
               return func()
           except Exception as e:
               if attempt == max_retries - 1:
                   raise e
               
               wait_time = (2 ** attempt) + random.uniform(0, 1)
               print(f"Retry {attempt + 1} after {wait_time:.2f}s")
               time.sleep(wait_time)
   ```

2. **Handle rate limits**:
   ```python
   import openai
   
   try:
       response = openai.ChatCompletion.create(...)
   except openai.error.RateLimitError:
       print("Rate limit exceeded, waiting...")
       time.sleep(60)
       response = openai.ChatCompletion.create(...)
   ```

3. **Configure timeouts**:
   ```python
   import openai
   
   openai.api_timeout = 60  # 60 second timeout
   
   # Or in configuration
   model:
     timeout: 60
     max_retries: 3
     backoff_factor: 2
   ```

### Issue: Task execution failures

**Symptoms**:
```
TaskExecutionError: Failed to execute task
ValueError: Invalid task configuration
KeyError: Required field missing
```

**Solutions**:

1. **Validate task configuration**:
   ```python
   from core.task_validator import TaskValidator
   
   validator = TaskValidator()
   result = validator.validate_task_config(task_config)
   
   if not result.is_valid:
       print(f"Task validation errors: {result.errors}")
   ```

2. **Check task dependencies**:
   ```python
   # Verify task files exist
   import os
   
   task_files = [
       "task_definition.py",
       "dataset.json",
       "config.yaml"
   ]
   
   for file in task_files:
       if not os.path.exists(file):
           print(f"Missing task file: {file}")
   ```

3. **Debug task execution**:
   ```python
   import logging
   
   # Enable debug logging for tasks
   logging.getLogger('task_executor').setLevel(logging.DEBUG)
   
   # Run single task with debug info
   result = executor.execute_task(task, config, debug=True)
   ```

### Issue: Memory and resource errors

**Symptoms**:
```
MemoryError: Unable to allocate memory
OSError: [Errno 28] No space left on device
ResourceExhaustedError: Out of memory
```

**Solutions**:

1. **Monitor resource usage**:
   ```python
   import psutil
   
   # Check memory usage
   memory = psutil.virtual_memory()
   print(f"Memory usage: {memory.percent}%")
   
   # Check disk space
   disk = psutil.disk_usage('/')
   print(f"Disk usage: {disk.percent}%")
   ```

2. **Optimize batch sizes**:
   ```yaml
   # Reduce batch size for memory-constrained environments
   task_config:
     batch_size: 1  # Instead of 4 or 8
     limit: 100     # Limit number of examples
   ```

3. **Clean up resources**:
   ```python
   import gc
   import torch
   
   # Clear GPU memory
   if torch.cuda.is_available():
       torch.cuda.empty_cache()
   
   # Force garbage collection
   gc.collect()
   ```

## API Problems

### Issue: API server startup failures

**Symptoms**:
```
Address already in use
Port 8000 is already in use
Failed to bind to address
```

**Solutions**:

1. **Find and kill existing processes**:
   ```bash
   # Find process using port 8000
   lsof -i :8000
   
   # Kill process
   kill -9 <PID>
   
   # Or use different port
   python api/api_test_server.py --port 8001
   ```

2. **Check port availability**:
   ```python
   import socket
   
   def is_port_available(port):
       with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
           try:
               s.bind(('localhost', port))
               return True
           except OSError:
               return False
   
   # Find available port
   for port in range(8000, 8010):
       if is_port_available(port):
           print(f"Port {port} is available")
           break
   ```

### Issue: API authentication problems

**Symptoms**:
```
401 Unauthorized
403 Forbidden
Invalid API key
```

**Solutions**:

1. **Verify API key format**:
   ```python
   import requests
   
   api_key = "your_api_key"
   headers = {"Authorization": f"Bearer {api_key}"}
   
   response = requests.get(
       "http://localhost:8000/api/v1/health",
       headers=headers
   )
   
   print(f"Status: {response.status_code}")
   ```

2. **Generate new API key**:
   ```bash
   python api/api_test_server.py --generate-key --user "test_user"
   ```

3. **Check API key permissions**:
   ```python
   # Verify API key has required permissions
   response = requests.get(
       "http://localhost:8000/api/v1/user/permissions",
       headers=headers
   )
   
   permissions = response.json()
   print(f"Permissions: {permissions}")
   ```

### Issue: API request/response problems

**Symptoms**:
```
400 Bad Request
422 Unprocessable Entity
JSON decode error
```

**Solutions**:

1. **Validate request format**:
   ```python
   import json
   
   # Validate JSON format
   request_data = {
       "tasks": ["hellaswag"],
       "model": "gpt-3.5-turbo"
   }
   
   try:
       json_str = json.dumps(request_data)
       print("JSON is valid")
   except json.JSONEncodeError as e:
       print(f"JSON error: {e}")
   ```

2. **Check required fields**:
   ```python
   # Ensure all required fields are present
   required_fields = ["tasks", "model"]
   
   for field in required_fields:
       if field not in request_data:
           print(f"Missing required field: {field}")
   ```

3. **Debug API responses**:
   ```python
   import requests
   
   response = requests.post(
       "http://localhost:8000/api/v1/evaluations",
       json=request_data,
       headers=headers
   )
   
   print(f"Status: {response.status_code}")
   print(f"Headers: {response.headers}")
   print(f"Response: {response.text}")
   ```

## Adapter Issues

### Issue: lm_eval adapter problems

**Symptoms**:
```
lm_eval module not found
Task not found in lm_eval
lm_eval configuration error
```

**Solutions**:

1. **Verify lm_eval installation**:
   ```python
   try:
       import lm_eval
       print(f"lm_eval version: {lm_eval.__version__}")
       
       from lm_eval import tasks
       print(f"Available tasks: {len(tasks.ALL_TASKS)}")
   except ImportError as e:
       print(f"lm_eval import error: {e}")
   ```

2. **Check task availability**:
   ```python
   from lm_eval import tasks
   
   # List all available tasks
   available_tasks = list(tasks.ALL_TASKS.keys())
   print(f"Available tasks: {available_tasks}")
   
   # Check specific task
   task_name = "hellaswag"
   if task_name in available_tasks:
       print(f"Task {task_name} is available")
   else:
       print(f"Task {task_name} not found")
   ```

3. **Test lm_eval adapter**:
   ```python
   from adapters.lm_eval_adapter_validator import LMEvalAdapterValidator
   
   validator = LMEvalAdapterValidator()
   result = validator.validate_integration()
   
   if result.is_valid:
       print("lm_eval adapter is working")
   else:
       print(f"lm_eval adapter issues: {result.errors}")
   ```

### Issue: SWE-bench adapter problems

**Symptoms**:
```
Docker not available
SWE-bench repository not found
Environment setup failed
```

**Solutions**:

1. **Check Docker installation**:
   ```bash
   # Test Docker
   docker --version
   docker run hello-world
   
   # Check Docker daemon
   sudo systemctl status docker
   ```

2. **Verify SWE-bench setup**:
   ```python
   from adapters.swe_bench_adapter_validator import SWEBenchAdapterValidator
   
   validator = SWEBenchAdapterValidator()
   
   # Check environment
   env_status = validator.check_environment()
   print(f"Environment status: {env_status}")
   
   # Setup if needed
   if not env_status.is_ready:
       validator.setup_environment()
   ```

3. **Test SWE-bench task**:
   ```python
   # Run simple SWE-bench test
   result = validator.test_software_tasks(task_count=1)
   
   if result.success:
       print("SWE-bench adapter is working")
   else:
       print(f"SWE-bench issues: {result.errors}")
   ```

## Performance Problems

### Issue: Slow execution times

**Symptoms**:
- Tests taking much longer than expected
- High CPU or memory usage
- Unresponsive system

**Solutions**:

1. **Profile execution**:
   ```python
   import cProfile
   import pstats
   
   # Profile test execution
   profiler = cProfile.Profile()
   profiler.enable()
   
   # Run your test
   run_test()
   
   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative').print_stats(10)
   ```

2. **Optimize batch sizes**:
   ```yaml
   # Experiment with different batch sizes
   task_config:
     batch_size: 1   # Start small
     limit: 10       # Limit examples for testing
   ```

3. **Enable parallel execution**:
   ```yaml
   execution:
     parallel_execution: true
     max_workers: 2  # Start with 2, increase if stable
   ```

### Issue: Memory leaks

**Symptoms**:
- Memory usage continuously increasing
- Out of memory errors after long runs
- System becoming unresponsive

**Solutions**:

1. **Monitor memory usage**:
   ```python
   import psutil
   import time
   
   def monitor_memory():
       process = psutil.Process()
       while True:
           memory_mb = process.memory_info().rss / 1024 / 1024
           print(f"Memory usage: {memory_mb:.2f} MB")
           time.sleep(10)
   ```

2. **Force garbage collection**:
   ```python
   import gc
   
   # Force garbage collection between tasks
   gc.collect()
   
   # Check for memory leaks
   print(f"Garbage objects: {len(gc.garbage)}")
   ```

3. **Use memory profiling**:
   ```python
   from memory_profiler import profile
   
   @profile
   def run_evaluation():
       # Your evaluation code here
       pass
   ```

## Security and Permissions

### Issue: Sandbox execution problems

**Symptoms**:
```
Sandbox initialization failed
Permission denied in sandbox
Sandbox timeout
```

**Solutions**:

1. **Check sandbox configuration**:
   ```yaml
   security:
     enable_sandbox: true
     max_memory_mb: 2048
     max_execution_time: 1800
     allowed_network_hosts: ["api.openai.com"]
   ```

2. **Test sandbox functionality**:
   ```python
   from security.sandbox_executor import SandboxExecutor
   
   executor = SandboxExecutor()
   
   # Test basic execution
   result = executor.execute_safe("print('Hello, World!')")
   print(f"Sandbox test: {result}")
   ```

3. **Debug sandbox issues**:
   ```python
   # Enable sandbox debugging
   import logging
   logging.getLogger('sandbox').setLevel(logging.DEBUG)
   
   # Check sandbox status
   status = executor.get_sandbox_status()
   print(f"Sandbox status: {status}")
   ```

### Issue: File permission problems

**Symptoms**:
```
Permission denied writing to file
Cannot create directory
File access denied
```

**Solutions**:

1. **Check file permissions**:
   ```bash
   # Check current permissions
   ls -la test_results/
   
   # Fix permissions
   chmod -R 755 test_results/
   chown -R $USER:$USER test_results/
   ```

2. **Use appropriate directories**:
   ```python
   import tempfile
   import os
   
   # Use user's home directory
   home_dir = os.path.expanduser("~")
   test_dir = os.path.join(home_dir, "evaluation_tests")
   os.makedirs(test_dir, exist_ok=True)
   
   # Or use temporary directory
   temp_dir = tempfile.mkdtemp()
   ```

## Debugging Tools

### Enable Debug Logging

```python
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

# Enable specific loggers
logging.getLogger('evaluation_engine').setLevel(logging.DEBUG)
logging.getLogger('api_client').setLevel(logging.DEBUG)
```

### Use Debug Configuration

```yaml
# debug_config.yaml
logging:
  level: DEBUG
  detailed: true
  include_timestamps: true
  file: debug.log

execution:
  timeout: 3600  # Longer timeout for debugging
  max_retries: 1  # Fewer retries to see errors quickly
  
validation:
  validate_real_execution: true
  debug_mode: true
  save_intermediate_results: true
```

### Debug Scripts

```python
# debug_test.py
import sys
import traceback
from core.test_orchestrator import TestOrchestrator

def debug_test():
    try:
        # Your test code here
        orchestrator = TestOrchestrator()
        result = orchestrator.run_test()
        print(f"Test result: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Full traceback:")
        traceback.print_exc()
        
        # Additional debug info
        print(f"Python version: {sys.version}")
        print(f"Python path: {sys.path}")

if __name__ == "__main__":
    debug_test()
```

### Health Check Script

```python
# health_check.py
import os
import sys
import importlib

def check_health():
    """Comprehensive health check"""
    
    print("=== EvaluationEngine Testing Framework Health Check ===")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check required modules
    required_modules = [
        'requests', 'yaml', 'torch', 'lm_eval', 
        'psutil', 'docker', 'git'
    ]
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module} is available")
        except ImportError:
            print(f"✗ {module} is missing")
    
    # Check file permissions
    test_dirs = ['test_results', 'logs', 'configs']
    for dir_name in test_dirs:
        if os.path.exists(dir_name):
            if os.access(dir_name, os.W_OK):
                print(f"✓ {dir_name} is writable")
            else:
                print(f"✗ {dir_name} is not writable")
        else:
            print(f"? {dir_name} does not exist")
    
    # Check API connectivity
    try:
        import requests
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        print(f"✓ API server is responding ({response.status_code})")
    except:
        print("✗ API server is not responding")
    
    # Check environment variables
    env_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    for var in env_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"? {var} is not set")

if __name__ == "__main__":
    check_health()
```

## Getting Help

### Log Analysis

When reporting issues, include relevant log information:

```bash
# Collect logs
tail -n 100 debug.log > issue_logs.txt
tail -n 100 api_server.log >> issue_logs.txt

# System information
python --version >> issue_logs.txt
pip list >> issue_logs.txt
```

### Issue Reporting Template

When reporting issues, please include:

1. **Environment Information**:
   - Operating system and version
   - Python version
   - Installed packages (`pip list`)

2. **Error Details**:
   - Full error message and stack trace
   - Steps to reproduce the issue
   - Expected vs actual behavior

3. **Configuration**:
   - Configuration files used
   - Environment variables
   - Command line arguments

4. **Logs**:
   - Relevant log entries
   - Debug output if available

### Common Solutions Checklist

Before reporting an issue, try these common solutions:

- [ ] Restart the API server
- [ ] Clear temporary files and caches
- [ ] Update dependencies (`pip install --upgrade -r requirements.txt`)
- [ ] Check file permissions
- [ ] Verify configuration files
- [ ] Test with minimal configuration
- [ ] Check system resources (memory, disk space)
- [ ] Review recent changes to configuration or code

### Support Resources

1. **Documentation**: Check the usage guide and API specification
2. **Examples**: Review working examples in the examples/ directory
3. **Tests**: Look at unit tests for usage patterns
4. **Logs**: Enable debug logging for detailed information
5. **Health Check**: Run the health check script to identify issues

### Performance Optimization Tips

1. **Start Small**: Begin with single tasks and small datasets
2. **Monitor Resources**: Keep an eye on memory and CPU usage
3. **Use Appropriate Batch Sizes**: Balance speed and resource usage
4. **Enable Caching**: Cache results when appropriate
5. **Parallel Execution**: Use parallel processing for independent tasks
6. **Regular Cleanup**: Clean up temporary files and clear caches

This troubleshooting guide should help you resolve most common issues with the EvaluationEngineV1_0 Testing Framework. If you continue to experience problems, please use the issue reporting template to provide detailed information for further assistance.