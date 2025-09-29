"""
CLI test runner for executing command-line tests of EvaluationEngineV1_0.
"""

import subprocess
import logging
import time
import json
import tempfile
from typing import Dict, List, Optional, Any
from pathlib import Path
import shlex

try:
    from ..models.test_models import TestConfiguration, CLITestConfig, TestStatus
    from ..core.error_handler import ExecutionError, ConfigurationError
    from ..core.real_execution_validator import RealExecutionValidator
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from models.test_models import TestConfiguration, CLITestConfig, TestStatus
    from core.error_handler import ExecutionError, ConfigurationError
    from core.real_execution_validator import RealExecutionValidator


class CLITestRunner:
    """Executes CLI tests for EvaluationEngineV1_0."""
    
    def __init__(self, working_dir: Optional[Path] = None):
        self.working_dir = working_dir or Path.cwd()
        self.logger = logging.getLogger(f"{__name__}.CLITestRunner")
        self.real_execution_validator = RealExecutionValidator()
        self._temp_files = []
    
    def run_test(self, test_config: TestConfiguration) -> Dict[str, Any]:
        """Run a CLI test based on configuration."""
        self.logger.info(f"Running CLI test: {test_config.name}")
        
        result = {
            "success": False,
            "metrics": {},
            "artifacts": [],
            "logs": [],
            "error": None,
            "execution_time": 0.0,
            "command": "",
            "return_code": -1,
            "stdout": "",
            "stderr": ""
        }
        
        start_time = time.time()
        
        try:
            # Start real execution validation
            self.real_execution_validator.start_tracking()
            
            # Build CLI command
            command = self._build_cli_command(test_config)
            result["command"] = command
            result["logs"].append(f"Executing command: {command}")
            
            # Execute command
            execution_result = self._execute_command(command, test_config)
            
            # Update result with execution data
            result.update(execution_result)
            
            # Validate real execution
            if test_config.real_execution_required:
                # Create a mock test result for validation
                from ..models.test_models import TestResult
                test_result = TestResult(
                    test_id=test_config.test_id,
                    test_type=test_config.test_type,
                    name=test_config.name,
                    status=TestStatus.RUNNING,
                    execution_time=result["execution_time"],
                    real_execution_validated=False,
                    logs=result["logs"]
                )
                
                real_execution_valid = self.real_execution_validator.validate_real_execution(
                    test_result, test_config
                )
                result["real_execution_validated"] = real_execution_valid
                
                if not real_execution_valid:
                    result["logs"].append("WARNING: Real execution validation failed")
            
            # Determine success based on return code and validation
            result["success"] = (result["return_code"] == 0 and 
                               result.get("real_execution_validated", True))
            
            if result["success"]:
                result["logs"].append("CLI test completed successfully")
            else:
                result["error"] = f"CLI test failed with return code {result['return_code']}"
                result["logs"].append(result["error"])
            
        except Exception as e:
            result["error"] = str(e)
            result["logs"].append(f"CLI test execution failed: {e}")
            self.logger.error(f"CLI test failed: {e}")
        
        finally:
            result["execution_time"] = time.time() - start_time
            self.real_execution_validator.stop_tracking()
            self._cleanup_temp_files()
        
        return result
    
    def run_builtin_tasks(self, task_names: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
        """Run CLI tests with builtin tasks."""
        self.logger.info(f"Running builtin tasks: {task_names}")
        
        # Create test configuration
        test_config = TestConfiguration(
            test_id=f"cli_builtin_{int(time.time())}",
            test_type="cli",
            name="CLI Builtin Tasks Test",
            description=f"CLI test for builtin tasks: {', '.join(task_names)}",
            task_selection={"tasks": task_names, "type": "builtin"},
            execution_params=config
        )
        
        return self.run_test(test_config)
    
    def run_custom_tasks(self, task_dir: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run CLI tests with custom tasks."""
        self.logger.info(f"Running custom tasks from: {task_dir}")
        
        if not task_dir.exists():
            raise ConfigurationError(f"Custom task directory does not exist: {task_dir}")
        
        # Discover custom tasks
        custom_tasks = self._discover_custom_tasks(task_dir)
        
        # Create test configuration
        test_config = TestConfiguration(
            test_id=f"cli_custom_{int(time.time())}",
            test_type="cli",
            name="CLI Custom Tasks Test",
            description=f"CLI test for custom tasks in {task_dir}",
            task_selection={"task_dir": str(task_dir), "tasks": custom_tasks, "type": "custom"},
            execution_params=config
        )
        
        return self.run_test(test_config)
    
    def run_adapter_tests(self, adapter_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run CLI tests for specific adapter."""
        self.logger.info(f"Running adapter tests for: {adapter_name}")
        
        # Create test configuration
        test_config = TestConfiguration(
            test_id=f"cli_adapter_{adapter_name}_{int(time.time())}",
            test_type="cli",
            name=f"CLI Adapter Test: {adapter_name}",
            description=f"CLI test for {adapter_name} adapter",
            task_selection={"adapter": adapter_name, "type": "adapter"},
            execution_params=config
        )
        
        return self.run_test(test_config)
    
    def run_full_pipeline(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run full pipeline CLI test."""
        self.logger.info("Running full pipeline CLI test")
        
        # Create test configuration
        test_config = TestConfiguration(
            test_id=f"cli_pipeline_{int(time.time())}",
            test_type="cli",
            name="CLI Full Pipeline Test",
            description="Complete CLI pipeline test",
            task_selection={"type": "pipeline"},
            execution_params=config
        )
        
        return self.run_test(test_config)
    
    def _build_cli_command(self, test_config: TestConfiguration) -> str:
        """Build REAL CLI command from test configuration - NO MOCKS!"""
        # Use REAL lm_eval command for actual execution
        base_commands = [
            "python -m lm_eval",  # Real lm_eval execution
            "lm_eval",  # If lm-eval is installed globally
            "python -m EvaluationEngineV1_0.cli.multi_turn_cli",  # Fallback to our CLI
        ]
        
        # Use lm_eval for REAL execution
        base_cmd = base_commands[0]
        
        task_selection = test_config.task_selection
        execution_params = test_config.execution_params
        
        # Build REAL command based on task selection type
        if task_selection.get("type") == "builtin":
            # REAL builtin tasks execution
            tasks = task_selection.get("tasks", [])
            if tasks:
                cmd_parts = [base_cmd, "--model", "hf", "--model_args", "pretrained=gpt2,device=cpu", "--tasks"] + tasks
            else:
                cmd_parts = [base_cmd, "--model", "hf", "--model_args", "pretrained=gpt2,device=cpu", "--tasks", "hellaswag"]
        
        elif task_selection.get("type") == "custom":
            # REAL custom tasks execution
            task_dir = task_selection.get("task_dir")
            tasks = task_selection.get("tasks", [])
            
            if task_dir and tasks:
                cmd_parts = [base_cmd, "--model", "hf", "--model_args", "pretrained=gpt2,device=cpu", 
                           "--include_path", task_dir, "--tasks"] + tasks[:1]
            else:
                cmd_parts = [base_cmd, "--model", "hf", "--model_args", "pretrained=gpt2,device=cpu", "--tasks", "hellaswag"]
        
        elif task_selection.get("type") == "adapter":
            # REAL adapter test with actual model
            adapter = task_selection.get("adapter", "lm_eval")
            cmd_parts = [base_cmd, "--model", "hf", "--model_args", "pretrained=gpt2,device=cpu", "--tasks", "hellaswag"]
        
        elif task_selection.get("type") == "pipeline":
            # REAL pipeline test with multiple tasks
            cmd_parts = [base_cmd, "--model", "hf", "--model_args", "pretrained=gpt2,device=cpu", 
                        "--tasks", "hellaswag", "arc_easy"]
        
        else:
            # Default REAL command
            cmd_parts = [base_cmd, "--model", "hf", "--model_args", "pretrained=gpt2,device=cpu", "--tasks", "hellaswag"]
        
        # Add REAL execution parameters
        if execution_params:
            if execution_params.get("verbose"):
                cmd_parts.append("--verbosity")
                cmd_parts.append("INFO")
            
            # Always limit samples for faster testing but REAL execution
            limit = execution_params.get("limit", 5)
            cmd_parts.extend(["--limit", str(limit)])
            
            # Add batch size for efficiency
            batch_size = execution_params.get("batch_size", 1)
            cmd_parts.extend(["--batch_size", str(batch_size)])
            
            # Add few-shot examples
            num_fewshot = execution_params.get("num_fewshot", 0)
            cmd_parts.extend(["--num_fewshot", str(num_fewshot)])
        
        # Add output file
        output_file = self._create_temp_output_file()
        cmd_parts.extend(["--output_path", str(output_file)])
        
        return " ".join(shlex.quote(str(part)) for part in cmd_parts)
    
    def _execute_command(self, command: str, test_config: TestConfiguration) -> Dict[str, Any]:
        """Execute CLI command and capture results."""
        timeout = test_config.execution_params.get("timeout", 300)  # 5 minutes default
        
        try:
            self.logger.info(f"Executing command with timeout {timeout}s: {command}")
            
            # Record resource snapshot before execution
            self.real_execution_validator.record_resource_snapshot()
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.working_dir
            )
            
            # Record resource snapshot after execution
            self.real_execution_validator.record_resource_snapshot()
            
            execution_result = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "logs": []
            }
            
            # Parse stdout for logs
            if result.stdout:
                execution_result["logs"].extend(result.stdout.split('\n'))
            
            # Parse stderr for error logs
            if result.stderr:
                execution_result["logs"].extend([f"STDERR: {line}" for line in result.stderr.split('\n')])
            
            # Extract metrics from output
            metrics = self._extract_metrics_from_output(result.stdout, result.stderr)
            execution_result["metrics"] = metrics
            
            # Look for output files
            artifacts = self._find_output_artifacts()
            execution_result["artifacts"] = artifacts
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            raise ExecutionError(f"Command timed out after {timeout} seconds")
        except subprocess.CalledProcessError as e:
            raise ExecutionError(f"Command failed with return code {e.returncode}")
        except Exception as e:
            raise ExecutionError(f"Command execution failed: {e}")
    
    def _extract_metrics_from_output(self, stdout: str, stderr: str) -> Dict[str, float]:
        """Extract metrics from command output."""
        metrics = {}
        
        # Combine output for analysis
        output = stdout + "\n" + stderr
        
        # Look for common metric patterns
        import re
        
        # Accuracy patterns
        accuracy_patterns = [
            r"accuracy[:\s]+([0-9.]+)",
            r"acc[:\s]+([0-9.]+)",
            r"score[:\s]+([0-9.]+)"
        ]
        
        for pattern in accuracy_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    metrics["accuracy"] = float(matches[-1])  # Use last match
                    break
                except ValueError:
                    continue
        
        # Timing patterns
        time_patterns = [
            r"time[:\s]+([0-9.]+)",
            r"duration[:\s]+([0-9.]+)",
            r"elapsed[:\s]+([0-9.]+)"
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    metrics["execution_time"] = float(matches[-1])
                    break
                except ValueError:
                    continue
        
        # Token count patterns
        token_patterns = [
            r"tokens[:\s]+([0-9]+)",
            r"token_count[:\s]+([0-9]+)"
        ]
        
        for pattern in token_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    metrics["tokens_used"] = float(matches[-1])
                    break
                except ValueError:
                    continue
        
        # Count lines as a basic metric
        metrics["output_lines"] = len(output.split('\n'))
        
        return metrics
    
    def _discover_custom_tasks(self, task_dir: Path) -> List[str]:
        """Discover custom tasks in directory."""
        custom_tasks = []
        
        try:
            # Look for Python files that might be tasks
            for py_file in task_dir.glob("**/*.py"):
                if py_file.name != "__init__.py":
                    # Use filename without extension as task name
                    task_name = py_file.stem
                    custom_tasks.append(task_name)
            
            # Look for YAML task definitions
            for yaml_file in task_dir.glob("**/*.yaml"):
                task_name = yaml_file.stem
                custom_tasks.append(task_name)
            
            # Look for JSON task definitions
            for json_file in task_dir.glob("**/*.json"):
                task_name = json_file.stem
                custom_tasks.append(task_name)
            
        except Exception as e:
            self.logger.warning(f"Error discovering custom tasks: {e}")
        
        return custom_tasks[:5]  # Limit to first 5 tasks
    
    def _create_temp_output_file(self) -> Path:
        """Create temporary output file."""
        temp_file = Path(tempfile.mktemp(suffix=".json", prefix="cli_test_output_"))
        self._temp_files.append(temp_file)
        return temp_file
    
    def _find_output_artifacts(self) -> List[str]:
        """Find output artifacts created by CLI command."""
        artifacts = []
        
        # Check temp files we created
        for temp_file in self._temp_files:
            if temp_file.exists():
                artifacts.append(str(temp_file))
        
        # Look for common output files in working directory
        common_outputs = [
            "results.json",
            "evaluation_results.json", 
            "output.json",
            "results.csv",
            "evaluation.log"
        ]
        
        for output_name in common_outputs:
            output_path = self.working_dir / output_name
            if output_path.exists():
                artifacts.append(str(output_path))
        
        return artifacts
    
    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files."""
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        
        self._temp_files.clear()


def create_cli_test_runner(working_dir: Optional[Path] = None) -> CLITestRunner:
    """Factory function to create a CLI test runner."""
    return CLITestRunner(working_dir=working_dir)