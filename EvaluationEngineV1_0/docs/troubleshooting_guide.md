# Multi-Turn Evaluation Engine Troubleshooting Guide

## Table of Contents

1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Configuration Issues](#configuration-issues)
4. [API Errors](#api-errors)
5. [CLI Problems](#cli-problems)
6. [Adapter Integration Issues](#adapter-integration-issues)
7. [Performance Problems](#performance-problems)
8. [Safety and Security Issues](#safety-and-security-issues)
9. [Debugging Tools](#debugging-tools)
10. [FAQ](#faq)

## Common Issues

### Issue: Evaluation Stuck in "Initializing" Status

**Symptoms:**
- Evaluation remains in "initializing" status for extended periods
- No progress updates via WebSocket
- API status endpoint shows no advancement

**Possible Causes:**
1. Task registry initialization failure
2. Adapter connection issues
3. Resource constraints
4. Configuration validation errors

**Solutions:**

1. **Check Task Registry:**
   ```bash
   # Verify task registry status
   multi-turn list-tasks --format json
   
   # Check specific task
   multi-turn describe-task <task_id>
   ```

2. **Validate Configuration:**
   ```bash
   # Validate your configuration file
   multi-turn validate-config config.yaml
   ```

3. **Check Logs:**
   ```bash
   # Check application logs
   tail -f multi_turn_evaluation.log
   
   # Check system logs
   journalctl -u evaluation-engine -f
   ```

4. **Resource Check:**
   ```bash
   # Check system resources
   htop
   df -h
   free -m
   ```

### Issue: High Memory Usage During Evaluation

**Symptoms:**
- System becomes unresponsive
- Out of memory errors
- Evaluation failures with resource exhaustion

**Solutions:**

1. **Adjust Feedback Configuration:**
   ```yaml
   feedback_config:
     max_feedback_length: 5000  # Reduce from default 10000
     context_strategy: "minimal"  # Use minimal instead of full
     max_context_length: 25000  # Reduce from default 50000
   ```

2. **Limit Concurrent Evaluations:**
   ```python
   # In your configuration
   max_concurrent_evaluations: 2  # Reduce from default
   ```

3. **Enable Garbage Collection:**
   ```python
   import gc
   gc.set_threshold(700, 10, 10)  # More aggressive GC
   ```

### Issue: WebSocket Connection Failures

**Symptoms:**
- Real-time updates not received
- WebSocket connection drops frequently
- "Connection refused" errors

**Solutions:**

1. **Check WebSocket URL:**
   ```javascript
   // Correct WebSocket URL format
   const ws = new WebSocket('ws://localhost:8000/ws/multi-turn/evaluation_id');
   ```

2. **Verify Authentication:**
   ```javascript
   // Include authentication token
   const ws = new WebSocket('ws://localhost:8000/ws/multi-turn/evaluation_id', [], {
     headers: {
       'Authorization': 'Bearer your_token_here'
     }
   });
   ```

3. **Check Firewall Settings:**
   ```bash
   # Allow WebSocket port
   sudo ufw allow 8000
   ```

## Installation Problems

### Issue: Package Dependencies Conflict

**Error Message:**
```
ERROR: pip's dependency resolver does not currently consider all the packages that are installed
```

**Solution:**
```bash
# Create clean virtual environment
python -m venv evaluation_env
source evaluation_env/bin/activate  # On Windows: evaluation_env\Scripts\activate

# Install with specific versions
pip install -r requirements.txt --no-deps
pip install -r requirements.txt --force-reinstall
```

### Issue: Missing System Dependencies

**Error Message:**
```
ModuleNotFoundError: No module named '_ctypes'
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install build-essential libffi-dev python3-dev

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install libffi-devel python3-devel

# macOS
xcode-select --install
brew install libffi
```

### Issue: Docker Container Startup Failures

**Error Message:**
```
docker: Error response from daemon: driver failed programming external connectivity
```

**Solution:**
```bash
# Stop conflicting services
sudo systemctl stop apache2
sudo systemctl stop nginx

# Use different port
docker run -p 8001:8000 evaluation-engine

# Check port usage
netstat -tulpn | grep :8000
```

## Configuration Issues

### Issue: Invalid YAML Configuration

**Error Message:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solution:**
```yaml
# Correct YAML format
model_id: "gpt-4"
task_ids:
  - "swe_bench_lite_001"
  - "intercode_python_001"
max_turns: 10

# Common mistakes to avoid:
# Wrong: task_ids: ["task1", "task2"]  # Don't mix formats
# Wrong: model_id: gpt-4  # Missing quotes for special characters
```

### Issue: Task Not Found Errors

**Error Message:**
```
HTTPException: Task not found: my_custom_task
```

**Solutions:**

1. **Check Task Registration:**
   ```python
   from EvaluationEngineV1_0.core.unified_task_registry import UnifiedTaskRegistry
   
   registry = UnifiedTaskRegistry()
   print(registry.get_all_tasks())  # List all available tasks
   ```

2. **Register Custom Tasks:**
   ```python
   # Register your custom task
   registry.register_task_from_config({
       'task_id': 'my_custom_task',
       'name': 'My Custom Task',
       'type': 'multi_turn',
       'adapter': 'custom_adapter'
   })
   ```

3. **Check Adapter Status:**
   ```bash
   # Verify adapter is loaded
   multi-turn list-tasks --category all
   ```

## API Errors

### Issue: Authentication Failures

**Error Message:**
```
401 Unauthorized: Authentication required
```

**Solutions:**

1. **Check Token Format:**
   ```bash
   # Correct format
   curl -H "Authorization: Bearer your_jwt_token" \
        http://localhost:8000/api/v1/multi-turn/evaluations
   ```

2. **Verify Token Validity:**
   ```python
   import jwt
   
   try:
       decoded = jwt.decode(token, verify=False)
       print(f"Token expires: {decoded.get('exp')}")
   except jwt.InvalidTokenError as e:
       print(f"Invalid token: {e}")
   ```

3. **Generate New Token:**
   ```bash
   # Request new token from admin
   curl -X POST http://localhost:8000/auth/token \
        -H "Content-Type: application/json" \
        -d '{"username": "your_username", "password": "your_password"}'
   ```

### Issue: Rate Limit Exceeded

**Error Message:**
```
429 Too Many Requests: Rate limit exceeded
```

**Solutions:**

1. **Implement Exponential Backoff:**
   ```python
   import time
   import random
   
   def api_call_with_backoff(func, max_retries=5):
       for attempt in range(max_retries):
           try:
               return func()
           except RateLimitError:
               if attempt == max_retries - 1:
                   raise
               wait_time = (2 ** attempt) + random.uniform(0, 1)
               time.sleep(wait_time)
   ```

2. **Batch Requests:**
   ```python
   # Instead of multiple single requests
   for task_id in task_ids:
       create_evaluation(task_id)
   
   # Use batch creation
   create_batch_evaluation(task_ids)
   ```

### Issue: Request Timeout Errors

**Error Message:**
```
TimeoutError: Request timed out after 30 seconds
```

**Solutions:**

1. **Increase Timeout:**
   ```python
   import httpx
   
   client = httpx.Client(timeout=300.0)  # 5 minutes
   ```

2. **Use Async Requests:**
   ```python
   import asyncio
   import httpx
   
   async def async_api_call():
       async with httpx.AsyncClient(timeout=300.0) as client:
           response = await client.post(url, json=data)
           return response.json()
   ```

## CLI Problems

### Issue: Command Not Found

**Error Message:**
```
multi-turn: command not found
```

**Solutions:**

1. **Check Installation:**
   ```bash
   # Verify package is installed
   pip list | grep evaluation-engine
   
   # Reinstall if necessary
   pip install -e .
   ```

2. **Check PATH:**
   ```bash
   # Add to PATH if needed
   export PATH=$PATH:~/.local/bin
   
   # Make permanent
   echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Use Python Module:**
   ```bash
   # Alternative execution method
   python -m EvaluationEngineV1_0.cli.multi_turn_cli --help
   ```

### Issue: Configuration File Not Found

**Error Message:**
```
FileNotFoundError: Configuration file not found: config.yaml
```

**Solutions:**

1. **Use Absolute Path:**
   ```bash
   multi-turn run-config /full/path/to/config.yaml
   ```

2. **Check Current Directory:**
   ```bash
   ls -la *.yaml *.yml
   pwd
   ```

3. **Create Configuration:**
   ```bash
   # Generate template
   multi-turn init-config --output config.yaml --template basic
   ```

## Adapter Integration Issues

### Issue: Adapter Import Errors

**Error Message:**
```
ImportError: cannot import name 'SWEBenchAdapter' from 'EvaluationEngineV1_0.core.swe_bench_adapter'
```

**Solutions:**

1. **Check Module Structure:**
   ```bash
   # Verify file exists
   ls -la EvaluationEngineV1_0/core/swe_bench_adapter.py
   
   # Check imports
   python -c "from EvaluationEngineV1_0.core.swe_bench_adapter import SWEBenchAdapter"
   ```

2. **Reinstall Package:**
   ```bash
   pip uninstall evaluation-engine
   pip install -e .
   ```

### Issue: Adapter Connection Failures

**Error Message:**
```
ConnectionError: Failed to connect to benchmark API
```

**Solutions:**

1. **Check Network Connectivity:**
   ```bash
   # Test connection
   curl -I https://api.benchmark.com/health
   ping api.benchmark.com
   ```

2. **Verify Credentials:**
   ```python
   # Test API credentials
   import requests
   
   response = requests.get(
       'https://api.benchmark.com/auth/test',
       headers={'Authorization': f'Bearer {api_key}'}
   )
   print(response.status_code, response.text)
   ```

3. **Check Proxy Settings:**
   ```bash
   # Set proxy if needed
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

## Performance Problems

### Issue: Slow Evaluation Execution

**Symptoms:**
- Evaluations take much longer than expected
- High CPU usage
- Frequent timeouts

**Solutions:**

1. **Profile Performance:**
   ```python
   import cProfile
   import pstats
   
   # Profile evaluation
   cProfile.run('run_evaluation()', 'evaluation_profile.prof')
   
   # Analyze results
   stats = pstats.Stats('evaluation_profile.prof')
   stats.sort_stats('cumulative').print_stats(20)
   ```

2. **Optimize Configuration:**
   ```yaml
   # Reduce feedback processing
   feedback_config:
     context_strategy: "minimal"
     max_feedback_length: 2000
   
   # Limit turn count
   max_turns: 5
   
   # Reduce timeout
   timeout_seconds: 1800
   ```

3. **Enable Parallel Processing:**
   ```python
   # Use async execution
   import asyncio
   
   async def run_parallel_evaluations(task_ids):
       tasks = [run_single_evaluation(task_id) for task_id in task_ids]
       results = await asyncio.gather(*tasks)
       return results
   ```

### Issue: Memory Leaks

**Symptoms:**
- Memory usage continuously increases
- System becomes unresponsive over time
- Out of memory errors

**Solutions:**

1. **Monitor Memory Usage:**
   ```python
   import psutil
   import gc
   
   def monitor_memory():
       process = psutil.Process()
       memory_info = process.memory_info()
       print(f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
       print(f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
       print(f"Objects: {len(gc.get_objects())}")
   ```

2. **Force Garbage Collection:**
   ```python
   import gc
   
   # After each evaluation
   gc.collect()
   
   # More aggressive collection
   gc.set_threshold(700, 10, 10)
   ```

3. **Use Context Managers:**
   ```python
   class EvaluationContext:
       def __enter__(self):
           return self
       
       def __exit__(self, exc_type, exc_val, exc_tb):
           # Cleanup resources
           gc.collect()
   
   with EvaluationContext():
       run_evaluation()
   ```

## Safety and Security Issues

### Issue: Safety Violations Not Detected

**Symptoms:**
- Dangerous commands executed without blocking
- Security policies not enforced
- No safety incident logging

**Solutions:**

1. **Check Safety Configuration:**
   ```yaml
   safety_config:
     allowed_tools: ["python", "bash", "git"]
     enable_sandboxing: true
     max_execution_time: 300
     dangerous_patterns:
       - "rm -rf"
       - "del /f /q"
       - "eval("
       - "exec("
   ```

2. **Verify Safety Guard:**
   ```python
   from EvaluationEngineV1_0.core.safety_guard import SafetyGuard
   
   guard = SafetyGuard(safety_config)
   
   # Test safety validation
   action = {"type": "shell_command", "command": "rm -rf /"}
   is_safe, reason = guard.validate_action(action)
   print(f"Safe: {is_safe}, Reason: {reason}")
   ```

3. **Enable Logging:**
   ```python
   import logging
   
   # Enable safety logging
   logging.getLogger('safety_guard').setLevel(logging.DEBUG)
   ```

### Issue: Sandbox Escape Attempts

**Error Message:**
```
SecurityError: Attempted to access restricted resource
```

**Solutions:**

1. **Strengthen Sandbox:**
   ```yaml
   safety_config:
     enable_sandboxing: true
     sandbox_type: "docker"  # Use Docker for stronger isolation
     resource_limits:
       memory: "1GB"
       cpu: "1.0"
       disk: "10GB"
   ```

2. **Monitor System Calls:**
   ```bash
   # Use strace to monitor system calls
   strace -f -e trace=file python evaluation_script.py
   ```

## Debugging Tools

### Enable Debug Logging

```python
import logging

# Enable debug logging for all components
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

# Enable specific component logging
logging.getLogger('orchestrator').setLevel(logging.DEBUG)
logging.getLogger('safety_guard').setLevel(logging.DEBUG)
logging.getLogger('metrics_engine').setLevel(logging.DEBUG)
```

### Use Interactive Debugger

```python
import pdb

# Add breakpoint in code
def problematic_function():
    pdb.set_trace()  # Debugger will stop here
    # Your code here
```

### Performance Profiling

```python
import cProfile
import pstats
from pstats import SortKey

# Profile function execution
cProfile.run('your_function()', 'profile_output.prof')

# Analyze profile
p = pstats.Stats('profile_output.prof')
p.sort_stats(SortKey.CUMULATIVE)
p.print_stats(20)  # Top 20 functions by cumulative time
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    # Your code here
    pass

# Run with: python -m memory_profiler your_script.py
```

## FAQ

### Q: How do I add a new benchmark adapter?

**A:** Follow these steps:

1. Create a new adapter class inheriting from `BenchmarkAdapter`
2. Implement required methods: `create_environment()`, `load_tasks()`, `convert_results()`
3. Register the adapter with the task registry
4. Test thoroughly with unit and integration tests

See the [Developer Guide](developer_guide.md) for detailed instructions.

### Q: Can I run multiple evaluations simultaneously?

**A:** Yes, the system supports concurrent evaluations. However, consider:

- System resource limitations
- API rate limits
- Memory usage
- Safety implications

Configure `max_concurrent_evaluations` in your settings.

### Q: How do I customize the feedback processing?

**A:** You can customize feedback processing by:

1. Modifying the `FeedbackConfig`:
   ```yaml
   feedback_config:
     context_strategy: "adaptive"  # or "full", "minimal", "top_k"
     max_feedback_length: 10000
     enable_stack_summarization: true
   ```

2. Creating a custom `FeedbackProcessor` subclass
3. Implementing custom feedback filters

### Q: What safety measures are in place?

**A:** The system includes multiple safety layers:

- Tool whitelisting
- Command filtering
- Resource monitoring
- Execution sandboxing
- Safety incident logging
- Configurable safety policies

### Q: How do I backup and restore evaluation data?

**A:** Use the built-in export functionality:

```bash
# Export evaluations
multi-turn export --format json --output backup.json

# Import evaluations
multi-turn import --input backup.json
```

### Q: Can I integrate with my existing CI/CD pipeline?

**A:** Yes, the system provides:

- REST API for programmatic access
- CLI tools for script integration
- Docker containers for deployment
- Webhook support for notifications

Example CI/CD integration:
```yaml
# .github/workflows/evaluation.yml
- name: Run Multi-Turn Evaluation
  run: |
    multi-turn run \
      --model-id ${{ matrix.model }} \
      --task-id ${{ matrix.task }} \
      --output results.json
```

### Q: How do I troubleshoot WebSocket connection issues?

**A:** Common solutions:

1. Check WebSocket URL format
2. Verify authentication tokens
3. Test network connectivity
4. Check firewall settings
5. Monitor browser console for errors

### Q: What are the system requirements?

**A:** Minimum requirements:

- Python 3.8+
- 4GB RAM (8GB recommended)
- 10GB disk space
- Network connectivity for external adapters

Recommended for production:
- Python 3.10+
- 16GB RAM
- SSD storage
- Load balancer for high availability

### Q: How do I contribute to the project?

**A:** To contribute:

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request
5. Follow the coding standards and documentation requirements

See `CONTRIBUTING.md` for detailed guidelines.

### Q: Where can I get additional support?

**A:** Support options:

- GitHub Issues: Bug reports and feature requests
- Documentation: Comprehensive guides and API reference
- Community Forum: Discussion and Q&A
- Email Support: support@evaluation-engine.com (for enterprise users)

---

For additional troubleshooting help, please check the logs, enable debug mode, and consult the developer documentation. If issues persist, please file a detailed bug report with reproduction steps.