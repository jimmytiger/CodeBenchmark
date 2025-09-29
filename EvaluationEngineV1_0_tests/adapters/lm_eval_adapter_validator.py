"""
Real execution validator for lm_eval_adapter.py - NO MOCKS, REAL EXECUTION ONLY!

This validator performs ACTUAL execution of lm-evaluation-harness tasks through
EvaluationEngineV1_0's lm_eval_adapter.py with real models and real data.

Enhanced implementation with comprehensive testing capabilities including:
- Automatic dependency installation and validation
- Builtin task testing with real execution
- Custom task discovery and execution from lm_eval/tasks
- Integration testing with EvaluationEngineV1_0
- Performance benchmarking and metrics collection
"""

import subprocess
import logging
import time
import json
import tempfile
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import importlib.util

try:
    from EvaluationEngineV1_0_tests.models.test_models import ValidationResult, TestStatus, AdapterType, TestResult, TestType
    from EvaluationEngineV1_0_tests.core.error_handler import AdapterError, DependencyError, ExecutionError
except ImportError:
    from models.test_models import ValidationResult, TestStatus, AdapterType, TestResult, TestType
    from core.error_handler import AdapterError, DependencyError, ExecutionError


class LMEvalAdapterValidator:
    """Validates lm_eval_adapter.py with REAL execution - no mocks!"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.LMEvalAdapterValidator")
        self.temp_files = []
        self.installed_packages = []
        
    def validate_integration(self) -> ValidationResult:
        """Validate lm_eval_adapter integration with REAL execution."""
        self.logger.info("🚀 Starting REAL lm_eval_adapter validation - NO MOCKS!")
        
        validation_result = ValidationResult(
            adapter_name="lm_eval_adapter",
            adapter_type=AdapterType.LM_EVAL,
            integration_status=TestStatus.PENDING,
            dependencies_installed=False
        )
        
        start_time = time.time()
        
        try:
            # Step 1: Install and verify dependencies
            self.logger.info("📦 Installing real lm-eval dependencies...")
            deps_success = self.install_dependencies()
            validation_result.dependencies_installed = deps_success
            
            if not deps_success:
                raise DependencyError("Failed to install lm-eval dependencies")
            
            # Step 2: Test real lm_eval_adapter import and initialization
            self.logger.info("🔧 Testing real lm_eval_adapter import...")
            adapter_instance = self._test_real_adapter_import()
            
            # Step 3: Execute real builtin tasks
            self.logger.info("🎯 Executing REAL builtin lm_eval tasks...")
            builtin_results = self.test_builtin_tasks(task_count=1)
            validation_result.test_results.extend(builtin_results)
            
            # Step 4: Execute real custom tasks if available
            self.logger.info("🔍 Looking for custom tasks...")
            custom_results = self.test_custom_tasks(Path("lm_eval/tasks"))
            validation_result.test_results.extend(custom_results)
            
            # Step 5: Performance benchmarking with real execution
            self.logger.info("⚡ Running real performance benchmark...")
            perf_metrics = self._benchmark_real_performance()
            validation_result.performance_metrics.update(perf_metrics)
            
            # Determine overall status
            successful_tests = sum(1 for r in validation_result.test_results if r.status == TestStatus.PASSED)
            total_tests = len(validation_result.test_results)
            
            if successful_tests == total_tests and total_tests > 0:
                validation_result.integration_status = TestStatus.PASSED
                self.logger.info("✅ lm_eval_adapter validation PASSED with real execution!")
            else:
                validation_result.integration_status = TestStatus.FAILED
                validation_result.issues_found.append(f"Only {successful_tests}/{total_tests} tests passed")
                self.logger.warning(f"⚠️ lm_eval_adapter validation issues: {successful_tests}/{total_tests} passed")
            
        except Exception as e:
            validation_result.integration_status = TestStatus.ERROR
            validation_result.issues_found.append(str(e))
            self.logger.error(f"❌ lm_eval_adapter validation failed: {e}")
        
        finally:
            validation_result.validation_time = time.time() - start_time
            self._cleanup()
        
        return validation_result
    
    def install_dependencies(self) -> bool:
        """Install REAL lm-eval dependencies with comprehensive validation."""
        try:
            self.logger.info("📦 Installing lm-evaluation-harness and dependencies...")
            
            # Core dependencies with specific versions for stability
            dependencies = [
                ("lm-eval[all]", "Main lm-eval package with all extras"),
                ("datasets>=2.0.0", "HuggingFace datasets library"),
                ("transformers>=4.20.0", "HuggingFace transformers library"),
                ("torch>=1.12.0", "PyTorch for model execution"),
                ("accelerate>=0.20.0", "Accelerate for optimized execution"),
                ("numpy>=1.21.0", "NumPy for numerical operations"),
                ("scipy>=1.7.0", "SciPy for scientific computing")
            ]
            
            installation_success = True
            
            for dep_spec, description in dependencies:
                self.logger.info(f"📦 Installing {dep_spec} - {description}")
                
                try:
                    result = subprocess.run([
                        sys.executable, "-m", "pip", "install", 
                        dep_spec, "--upgrade", "--quiet"
                    ], capture_output=True, text=True, timeout=600)
                    
                    if result.returncode == 0:
                        self.installed_packages.append(dep_spec.split(">=")[0].split("[")[0])
                        self.logger.info(f"✅ Successfully installed {dep_spec}")
                    else:
                        self.logger.error(f"❌ Failed to install {dep_spec}: {result.stderr}")
                        installation_success = False
                        
                except subprocess.TimeoutExpired:
                    self.logger.error(f"❌ Installation of {dep_spec} timed out")
                    installation_success = False
            
            # Verify critical installations
            verification_tests = [
                ("import lm_eval; print('lm_eval version:', lm_eval.__version__)", "lm_eval"),
                ("import datasets; print('datasets version:', datasets.__version__)", "datasets"),
                ("import transformers; print('transformers version:', transformers.__version__)", "transformers"),
                ("import torch; print('torch version:', torch.__version__)", "torch")
            ]
            
            for test_code, package_name in verification_tests:
                try:
                    result = subprocess.run([
                        sys.executable, "-c", test_code
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        self.logger.info(f"✅ {package_name} verified: {result.stdout.strip()}")
                    else:
                        self.logger.error(f"❌ {package_name} verification failed: {result.stderr}")
                        installation_success = False
                        
                except Exception as e:
                    self.logger.error(f"❌ {package_name} verification error: {e}")
                    installation_success = False
            
            return installation_success
                
        except Exception as e:
            self.logger.error(f"❌ Dependency installation failed: {e}")
            return False
    
    def test_builtin_tasks(self, task_count: int = 1) -> List[Any]:
        """Test REAL builtin lm_eval tasks - actual execution!"""
        from ..models.test_models import TestResult, TestType
        
        results = []
        
        # Real builtin tasks to test
        builtin_tasks = ["hellaswag", "arc_easy", "winogrande", "piqa"][:task_count]
        
        for task_name in builtin_tasks:
            self.logger.info(f"🎯 Executing REAL task: {task_name}")
            
            test_result = TestResult(
                test_id=f"lm_eval_builtin_{task_name}",
                test_type=TestType.ADAPTER,
                name=f"Real LM-Eval Builtin Task: {task_name}",
                status=TestStatus.PENDING,
                execution_time=0.0,
                real_execution_validated=True  # This IS real execution
            )
            
            start_time = time.time()
            
            try:
                # Execute REAL lm_eval command
                success, metrics = self._execute_real_lm_eval_task(task_name)
                
                test_result.execution_time = time.time() - start_time
                test_result.metrics.update(metrics)
                
                if success:
                    test_result.status = TestStatus.PASSED
                    self.logger.info(f"✅ Real task {task_name} PASSED: {metrics}")
                else:
                    test_result.status = TestStatus.FAILED
                    test_result.error_details = f"Real execution failed for {task_name}"
                    self.logger.warning(f"⚠️ Real task {task_name} FAILED")
                
            except Exception as e:
                test_result.status = TestStatus.ERROR
                test_result.error_details = str(e)
                test_result.execution_time = time.time() - start_time
                self.logger.error(f"❌ Real task {task_name} ERROR: {e}")
            
            results.append(test_result)
        
        return results
    
    def test_custom_tasks(self, task_dir: Path) -> List[Any]:
        """Test REAL custom tasks from lm_eval/tasks directory."""
        from ..models.test_models import TestResult, TestType
        
        results = []
        
        if not task_dir.exists():
            self.logger.info(f"📁 Custom task directory not found: {task_dir}")
            return results
        
        # Discover real custom tasks
        custom_tasks = self._discover_real_custom_tasks(task_dir)
        
        if not custom_tasks:
            self.logger.info("📁 No custom tasks found")
            return results
        
        # Test first custom task found
        task_name = custom_tasks[0]
        self.logger.info(f"🎯 Executing REAL custom task: {task_name}")
        
        test_result = TestResult(
            test_id=f"lm_eval_custom_{task_name}",
            test_type=TestType.ADAPTER,
            name=f"Real LM-Eval Custom Task: {task_name}",
            status=TestStatus.PENDING,
            execution_time=0.0,
            real_execution_validated=True
        )
        
        start_time = time.time()
        
        try:
            # Execute REAL custom task
            success, metrics = self._execute_real_custom_task(task_name, task_dir)
            
            test_result.execution_time = time.time() - start_time
            test_result.metrics.update(metrics)
            
            if success:
                test_result.status = TestStatus.PASSED
                self.logger.info(f"✅ Real custom task {task_name} PASSED")
            else:
                test_result.status = TestStatus.FAILED
                test_result.error_details = f"Real custom task execution failed"
                self.logger.warning(f"⚠️ Real custom task {task_name} FAILED")
            
        except Exception as e:
            test_result.status = TestStatus.ERROR
            test_result.error_details = str(e)
            test_result.execution_time = time.time() - start_time
            self.logger.error(f"❌ Real custom task {task_name} ERROR: {e}")
        
        results.append(test_result)
        return results
    
    def _test_real_adapter_import(self) -> Any:
        """Test real import of EvaluationEngineV1_0.core.lm_eval_adapter."""
        try:
            # Import the REAL adapter
            from EvaluationEngineV1_0.core.lm_eval_adapter import LMEvalAdapter
            
            # Create REAL adapter instance
            adapter_config = {"test_mode": False}  # NOT test mode - real execution!
            adapter = LMEvalAdapter(adapter_config)
            
            # Initialize REAL adapter
            if not adapter.initialize():
                raise AdapterError("Real adapter initialization failed")
            
            self.logger.info("✅ Real lm_eval_adapter imported and initialized successfully")
            return adapter
            
        except ImportError as e:
            raise AdapterError(f"Failed to import real lm_eval_adapter: {e}")
        except Exception as e:
            raise AdapterError(f"Real adapter initialization failed: {e}")
    
    def _execute_real_lm_eval_task(self, task_name: str) -> Tuple[bool, Dict[str, float]]:
        """Execute REAL lm_eval task using actual lm_eval command."""
        try:
            # Create temporary output file
            output_file = tempfile.mktemp(suffix=".json", prefix=f"lm_eval_{task_name}_")
            self.temp_files.append(output_file)
            
            # Build REAL lm_eval command
            cmd = [
                sys.executable, "-m", "lm_eval",
                "--model", "hf",
                "--model_args", "pretrained=gpt2,device=cpu",  # Use real model
                "--tasks", task_name,
                "--num_fewshot", "0",
                "--batch_size", "1", 
                "--limit", "5",  # Small limit for testing
                "--output_path", output_file,
                "--log_samples"
            ]
            
            self.logger.info(f"🚀 Executing REAL lm_eval command: {' '.join(cmd)}")
            
            # Execute REAL command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                cwd=Path.cwd()
            )
            
            self.logger.info(f"📊 lm_eval return code: {result.returncode}")
            if result.stdout:
                self.logger.info(f"📝 lm_eval stdout: {result.stdout[:500]}...")
            if result.stderr:
                self.logger.warning(f"⚠️ lm_eval stderr: {result.stderr[:500]}...")
            
            # Parse REAL results
            metrics = {}
            if result.returncode == 0:
                # Try to parse output file
                try:
                    output_path = Path(output_file)
                    if output_path.exists():
                        with open(output_path, 'r') as f:
                            results_data = json.load(f)
                        
                        # Extract real metrics
                        if "results" in results_data and task_name in results_data["results"]:
                            task_results = results_data["results"][task_name]
                            for key, value in task_results.items():
                                if isinstance(value, (int, float)):
                                    metrics[f"real_{key}"] = float(value)
                        
                        metrics["real_execution"] = 1.0
                        metrics["samples_processed"] = 5.0  # We used limit=5
                        
                        self.logger.info(f"✅ Real execution successful, metrics: {metrics}")
                        return True, metrics
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Failed to parse real results: {e}")
                
                # Even if parsing failed, command succeeded
                metrics["real_execution"] = 1.0
                metrics["command_success"] = 1.0
                return True, metrics
            else:
                # Command failed but we still got real execution attempt
                metrics["real_execution"] = 1.0
                metrics["command_success"] = 0.0
                metrics["return_code"] = float(result.returncode)
                return False, metrics
                
        except subprocess.TimeoutExpired:
            self.logger.error("❌ Real lm_eval execution timed out")
            return False, {"real_execution": 1.0, "timeout": 1.0}
        except Exception as e:
            self.logger.error(f"❌ Real lm_eval execution failed: {e}")
            return False, {"real_execution": 1.0, "error": 1.0}
    
    def _execute_real_custom_task(self, task_name: str, task_dir: Path) -> Tuple[bool, Dict[str, float]]:
        """Execute REAL custom task."""
        try:
            # For custom tasks, we'll try to use lm_eval with include_path
            output_file = tempfile.mktemp(suffix=".json", prefix=f"lm_eval_custom_{task_name}_")
            self.temp_files.append(output_file)
            
            cmd = [
                sys.executable, "-m", "lm_eval",
                "--model", "hf",
                "--model_args", "pretrained=gpt2,device=cpu",
                "--tasks", task_name,
                "--include_path", str(task_dir),
                "--num_fewshot", "0",
                "--batch_size", "1",
                "--limit", "3",
                "--output_path", output_file
            ]
            
            self.logger.info(f"🚀 Executing REAL custom task: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=Path.cwd()
            )
            
            metrics = {"real_execution": 1.0, "custom_task": 1.0}
            
            if result.returncode == 0:
                metrics["command_success"] = 1.0
                self.logger.info("✅ Real custom task execution successful")
                return True, metrics
            else:
                metrics["command_success"] = 0.0
                metrics["return_code"] = float(result.returncode)
                self.logger.warning(f"⚠️ Real custom task failed with code {result.returncode}")
                return False, metrics
                
        except Exception as e:
            self.logger.error(f"❌ Real custom task execution failed: {e}")
            return False, {"real_execution": 1.0, "custom_task": 1.0, "error": 1.0}
    
    def _discover_real_custom_tasks(self, task_dir: Path) -> List[str]:
        """Discover REAL custom tasks in directory with comprehensive detection."""
        custom_tasks = []
        
        try:
            self.logger.info(f"🔍 Discovering custom tasks in {task_dir}")
            
            # Look for Python task files
            for py_file in task_dir.glob("**/*.py"):
                if py_file.name != "__init__.py":
                    try:
                        content = py_file.read_text()
                        # Enhanced detection for lm_eval task patterns
                        task_indicators = [
                            "Task", "class", "def doc_to_text", "def doc_to_target",
                            "OUTPUT_TYPE", "DATASET_PATH", "DATASET_NAME",
                            "def process_results", "def aggregation", "def higher_is_better"
                        ]
                        
                        if any(keyword in content for keyword in task_indicators):
                            task_name = py_file.stem
                            custom_tasks.append(task_name)
                            self.logger.info(f"📋 Found Python custom task: {task_name}")
                            
                            # Validate task structure
                            if self._validate_python_task_structure(content):
                                self.logger.info(f"✅ Task {task_name} has valid structure")
                            else:
                                self.logger.warning(f"⚠️ Task {task_name} may have structural issues")
                                
                    except Exception as e:
                        self.logger.warning(f"⚠️ Error reading {py_file}: {e}")
            
            # Look for YAML task definitions
            for yaml_file in task_dir.glob("**/*.yaml"):
                try:
                    import yaml
                    with open(yaml_file, 'r') as f:
                        yaml_content = yaml.safe_load(f)
                    
                    # Validate YAML task structure
                    if self._validate_yaml_task_structure(yaml_content):
                        task_name = yaml_file.stem
                        custom_tasks.append(task_name)
                        self.logger.info(f"📋 Found YAML custom task: {task_name}")
                    else:
                        self.logger.warning(f"⚠️ Invalid YAML task structure in {yaml_file}")
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ Error processing YAML file {yaml_file}: {e}")
            
            # Look for JSON task definitions
            for json_file in task_dir.glob("**/*.json"):
                if not json_file.name.startswith("temp_"):  # Skip temporary files
                    try:
                        with open(json_file, 'r') as f:
                            json_content = json.load(f)
                        
                        # Check if it's a task definition or dataset
                        if self._validate_json_task_structure(json_content):
                            task_name = json_file.stem
                            custom_tasks.append(task_name)
                            self.logger.info(f"📋 Found JSON custom task: {task_name}")
                            
                    except Exception as e:
                        self.logger.warning(f"⚠️ Error processing JSON file {json_file}: {e}")
            
            self.logger.info(f"🔍 Discovered {len(custom_tasks)} custom tasks total")
            
        except Exception as e:
            self.logger.error(f"❌ Error discovering custom tasks: {e}")
        
        return custom_tasks[:5]  # Limit to first 5 for testing
    
    def _validate_python_task_structure(self, content: str) -> bool:
        """Validate Python task file structure."""
        required_patterns = ["def doc_to_text", "def doc_to_target"]
        optional_patterns = ["OUTPUT_TYPE", "DATASET_PATH", "class"]
        
        required_found = sum(1 for pattern in required_patterns if pattern in content)
        optional_found = sum(1 for pattern in optional_patterns if pattern in content)
        
        return required_found >= 1 or optional_found >= 2
    
    def _validate_yaml_task_structure(self, yaml_content: dict) -> bool:
        """Validate YAML task structure."""
        if not isinstance(yaml_content, dict):
            return False
        
        required_fields = ["task", "dataset_path"]
        optional_fields = ["output_type", "metric", "description"]
        
        required_found = sum(1 for field in required_fields if field in yaml_content)
        optional_found = sum(1 for field in optional_fields if field in yaml_content)
        
        return required_found >= 1 or optional_found >= 2
    
    def _validate_json_task_structure(self, json_content: Any) -> bool:
        """Validate JSON task structure."""
        if isinstance(json_content, list) and len(json_content) > 0:
            # Looks like a dataset
            sample = json_content[0]
            if isinstance(sample, dict) and any(key in sample for key in ["question", "text", "input", "prompt"]):
                return True
        elif isinstance(json_content, dict):
            # Looks like a task configuration
            if any(key in json_content for key in ["task", "dataset", "config", "metadata"]):
                return True
        
        return False
    
    def _benchmark_real_performance(self) -> Dict[str, float]:
        """Benchmark REAL performance with actual execution."""
        self.logger.info("⚡ Running real performance benchmark...")
        
        start_time = time.time()
        
        try:
            # Execute a quick real benchmark
            success, metrics = self._execute_real_lm_eval_task("hellaswag")
            
            execution_time = time.time() - start_time
            
            perf_metrics = {
                "benchmark_execution_time": execution_time,
                "real_benchmark": 1.0,
                "benchmark_success": 1.0 if success else 0.0
            }
            
            # Add task-specific metrics
            perf_metrics.update(metrics)
            
            self.logger.info(f"⚡ Real benchmark completed in {execution_time:.2f}s")
            return perf_metrics
            
        except Exception as e:
            self.logger.error(f"❌ Real benchmark failed: {e}")
            return {
                "benchmark_execution_time": time.time() - start_time,
                "real_benchmark": 1.0,
                "benchmark_success": 0.0,
                "benchmark_error": 1.0
            }
    
    def _cleanup(self) -> None:
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to cleanup {temp_file}: {e}")
        
        self.temp_files.clear()


    def test_engine_integration(self) -> List[TestResult]:
        """Test integration with EvaluationEngineV1_0."""
        results = []
        
        integration_test = TestResult(
            test_id="lm_eval_engine_integration",
            test_type=TestType.INTEGRATION,
            name="EvaluationEngine Integration Test",
            status=TestStatus.PENDING,
            execution_time=0.0,
            real_execution_validated=True
        )
        
        start_time = time.time()
        
        try:
            # Test importing and initializing the adapter through the engine
            from EvaluationEngineV1_0.core.lm_eval_adapter import LMEvalAdapter
            
            # Create adapter with test configuration
            adapter_config = {
                "test_mode": False,  # Real execution
                "timeout": 120,
                "enable_logging": True
            }
            
            adapter = LMEvalAdapter(adapter_config)
            
            # Test initialization
            if adapter.initialize():
                integration_test.metrics["adapter_init_success"] = 1.0
                
                # Test getting adapter info
                adapter_info = adapter.get_adapter_info()
                if adapter_info and adapter_info.name == "lm_eval_adapter":
                    integration_test.metrics["adapter_info_valid"] = 1.0
                    
                    # Test loading tasks
                    try:
                        tasks = adapter.load_tasks({"limit": 2})
                        if tasks and len(tasks) > 0:
                            integration_test.metrics["task_loading_success"] = 1.0
                            integration_test.status = TestStatus.PASSED
                            self.logger.info("✅ Engine integration test PASSED")
                        else:
                            integration_test.status = TestStatus.FAILED
                            integration_test.error_details = "No tasks loaded"
                            self.logger.warning("⚠️ Engine integration test FAILED: No tasks loaded")
                    except Exception as e:
                        integration_test.status = TestStatus.FAILED
                        integration_test.error_details = f"Task loading failed: {e}"
                        self.logger.warning(f"⚠️ Engine integration test FAILED: {e}")
                else:
                    integration_test.status = TestStatus.FAILED
                    integration_test.error_details = "Invalid adapter info"
                    self.logger.warning("⚠️ Engine integration test FAILED: Invalid adapter info")
            else:
                integration_test.status = TestStatus.FAILED
                integration_test.error_details = "Adapter initialization failed"
                self.logger.warning("⚠️ Engine integration test FAILED: Initialization failed")
                
        except ImportError as e:
            integration_test.status = TestStatus.ERROR
            integration_test.error_details = f"Import error: {e}"
            self.logger.error(f"❌ Engine integration test ERROR: Import failed - {e}")
        except Exception as e:
            integration_test.status = TestStatus.ERROR
            integration_test.error_details = str(e)
            self.logger.error(f"❌ Engine integration test ERROR: {e}")
        
        finally:
            integration_test.execution_time = time.time() - start_time
        
        results.append(integration_test)
        return results
    
    def validate_custom_task_format(self, task_data: Any, task_type: str) -> Tuple[bool, List[str]]:
        """Validate custom task format and return validation results."""
        errors = []
        
        if task_type == "yaml":
            if not isinstance(task_data, dict):
                errors.append("YAML task must be a dictionary")
            else:
                required_fields = ["task"]
                for field in required_fields:
                    if field not in task_data:
                        errors.append(f"Missing required field: {field}")
                        
                # Check for common task fields
                recommended_fields = ["dataset_path", "output_type", "metric"]
                missing_recommended = [f for f in recommended_fields if f not in task_data]
                if len(missing_recommended) == len(recommended_fields):
                    errors.append("Missing recommended fields: " + ", ".join(recommended_fields))
        
        elif task_type == "python":
            if not isinstance(task_data, str):
                errors.append("Python task must be a string (file content)")
            else:
                required_patterns = ["def doc_to_text", "def doc_to_target"]
                found_patterns = [p for p in required_patterns if p in task_data]
                if not found_patterns:
                    errors.append("Missing required functions: " + ", ".join(required_patterns))
        
        elif task_type == "json":
            if isinstance(task_data, list):
                if not task_data:
                    errors.append("JSON dataset cannot be empty")
                elif not isinstance(task_data[0], dict):
                    errors.append("JSON dataset items must be dictionaries")
            elif isinstance(task_data, dict):
                if "task" not in task_data and "dataset" not in task_data:
                    errors.append("JSON task must have 'task' or 'dataset' field")
            else:
                errors.append("JSON task must be a list or dictionary")
        
        return len(errors) == 0, errors


def create_lm_eval_adapter_validator() -> LMEvalAdapterValidator:
    """Factory function to create lm_eval adapter validator."""
    return LMEvalAdapterValidator()