"""
Integration tests for swe_bench_adapter validation.

Tests integration with SWE-bench tasks and software engineering evaluations.
"""

import pytest
import os
import tempfile
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from adapters.swe_bench_adapter_validator import SWEBenchAdapterValidator
from core.error_handler import DependencyError, ExecutionError
from models.test_models import ValidationResult, TestResult


class TestSWEBenchAdapterIntegration:
    """Integration tests for SWEBenchAdapterValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SWEBenchAdapterValidator()
        self.temp_dir = tempfile.mkdtemp()
        self.test_repo_dir = Path(self.temp_dir) / "test_repo"
        self.test_repo_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_validate_integration_success(self):
        """Test successful SWE-bench integration validation."""
        with patch('subprocess.run') as mock_run:
            # Mock successful SWE-bench installation check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "swe-bench 1.0.0"
            
            result = self.validator.validate_integration()
            
            assert isinstance(result, ValidationResult)
            assert result.adapter_name == 'swe_bench'
            assert result.integration_status == 'success'
            assert result.dependencies_installed is True
    
    def test_validate_integration_missing_dependency(self):
        """Test integration validation with missing dependencies."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("swe-bench not found")
            
            result = self.validator.validate_integration()
            
            assert result.integration_status == 'failed'
            assert result.dependencies_installed is False
            assert len(result.issues_found) > 0
    
    def test_setup_environment_success(self):
        """Test successful environment setup."""
        with patch('subprocess.run') as mock_run, \
             patch('os.makedirs') as mock_makedirs:
            
            mock_run.return_value.returncode = 0
            
            success = self.validator.setup_environment()
            
            assert success is True
            # Should have created necessary directories
            mock_makedirs.assert_called()
    
    def test_install_dependencies_success(self):
        """Test successful dependency installation."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            success = self.validator.install_dependencies()
            
            assert success is True
            # Should have called pip install for SWE-bench
            mock_run.assert_called()
            call_args = mock_run.call_args[0][0]
            assert 'pip' in call_args
            assert 'install' in call_args
    
    def test_install_dependencies_failure(self):
        """Test dependency installation failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Installation failed"
            
            success = self.validator.install_dependencies()
            
            assert success is False
    
    def test_test_software_tasks_success(self):
        """Test successful software engineering task execution."""
        with patch('subprocess.run') as mock_run:
            # Mock successful SWE-bench task execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "django__django-12345": {
                        "resolved": True,
                        "test_passed": True,
                        "execution_time": 45.2
                    }
                }
            })
            
            results = self.validator.test_software_tasks(task_count=1)
            
            assert isinstance(results, list)
            assert len(results) > 0
            assert all(isinstance(r, TestResult) for r in results)
            assert results[0].status == 'passed'
            assert results[0].real_execution_validated is True
    
    def test_test_software_tasks_execution_failure(self):
        """Test software task execution failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Task execution failed"
            
            results = self.validator.test_software_tasks(task_count=1)
            
            assert len(results) > 0
            assert results[0].status == 'failed'
            assert 'Task execution failed' in results[0].error_details
    
    def test_create_test_repository(self):
        """Test creation of test repository for SWE-bench tasks."""
        repo_config = {
            'name': 'test_repo',
            'language': 'python',
            'files': {
                'main.py': 'def hello(): return "Hello, World!"',
                'test_main.py': 'import main\ndef test_hello(): assert main.hello() == "Hello, World!"'
            }
        }
        
        repo_path = self.validator.create_test_repository(repo_config, self.temp_dir)
        
        assert repo_path.exists()
        assert (repo_path / 'main.py').exists()
        assert (repo_path / 'test_main.py').exists()
        
        # Verify file contents
        main_content = (repo_path / 'main.py').read_text()
        assert 'def hello()' in main_content
    
    def test_execute_code_changes(self):
        """Test execution of code changes in repository."""
        # Create a simple test repository
        test_file = self.test_repo_dir / "calculator.py"
        test_file.write_text("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b  # Bug: should be a - b
""")
        
        # Define code changes to fix the bug
        changes = {
            'calculator.py': {
                'line': 5,
                'old_code': 'return a - b  # Bug: should be a - b',
                'new_code': 'return a - b'
            }
        }
        
        success = self.validator.execute_code_changes(self.test_repo_dir, changes)
        
        assert success is True
        
        # Verify changes were applied
        updated_content = test_file.read_text()
        assert '# Bug:' not in updated_content
    
    def test_run_test_suite(self):
        """Test running test suite in repository."""
        # Create test files
        test_file = self.test_repo_dir / "test_example.py"
        test_file.write_text("""
import pytest

def test_addition():
    assert 2 + 2 == 4

def test_subtraction():
    assert 5 - 3 == 2
""")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "2 passed, 0 failed"
            
            result = self.validator.run_test_suite(self.test_repo_dir)
            
            assert result['success'] is True
            assert result['tests_passed'] > 0
            assert result['tests_failed'] == 0
    
    def test_validate_code_quality(self):
        """Test code quality validation."""
        # Create code file with quality issues
        code_file = self.test_repo_dir / "bad_code.py"
        code_file.write_text("""
def function_with_long_name_that_violates_pep8():
    x=1+2+3+4+5+6+7+8+9+10  # Long line
    return x

def unused_function():
    pass
""")
        
        with patch('subprocess.run') as mock_run:
            # Mock pylint/flake8 output
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = """
bad_code.py:2:0: C0103: Function name doesn't conform to snake_case
bad_code.py:3:0: E501: line too long (80 > 79 characters)
bad_code.py:6:0: W0613: Unused function 'unused_function'
"""
            
            quality_report = self.validator.validate_code_quality(self.test_repo_dir)
            
            assert 'issues' in quality_report
            assert len(quality_report['issues']) > 0
            assert quality_report['score'] < 10.0  # Should have quality issues
    
    def test_benchmark_performance(self):
        """Test performance benchmarking of SWE-bench tasks."""
        with patch('subprocess.run') as mock_run, \
             patch('time.time') as mock_time:
            
            # Mock timing - 30 second execution
            mock_time.side_effect = [1000.0, 1030.0]
            
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    "django__django-12345": {
                        "resolved": True,
                        "execution_time": 30.0
                    }
                }
            })
            
            benchmark_result = self.validator.benchmark_performance(['django__django-12345'])
            
            assert 'execution_time' in benchmark_result
            assert 'memory_usage' in benchmark_result
            assert 'success_rate' in benchmark_result
            assert benchmark_result['execution_time'] > 0
    
    def test_docker_environment_setup(self):
        """Test Docker environment setup for isolated execution."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Container created successfully"
            
            container_id = self.validator.setup_docker_environment()
            
            assert container_id is not None
            # Should have called docker commands
            mock_run.assert_called()
            call_args = mock_run.call_args[0][0]
            assert 'docker' in call_args
    
    def test_execute_in_docker(self):
        """Test execution of tasks in Docker container."""
        container_id = "test_container_123"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Task completed successfully"
            
            result = self.validator.execute_in_docker(
                container_id, 
                "python test_script.py"
            )
            
            assert result['success'] is True
            assert 'Task completed successfully' in result['output']
    
    def test_multi_language_support(self):
        """Test support for multiple programming languages."""
        languages = ['python', 'java', 'javascript', 'go']
        
        for language in languages:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = f"{language} task completed"
                
                result = self.validator.test_language_specific_tasks(language, task_count=1)
                
                assert len(result) > 0
                assert result[0].status == 'passed'
                assert language in result[0].test_id
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        with patch('subprocess.run') as mock_run:
            # First call fails, second succeeds (retry logic)
            mock_run.side_effect = [
                MagicMock(returncode=1, stderr="Temporary failure"),
                MagicMock(returncode=0, stdout=json.dumps({
                    "results": {"django__django-12345": {"resolved": True}}
                }))
            ]
            
            results = self.validator.test_software_tasks_with_retry(['django__django-12345'], max_retries=2)
            
            assert len(results) > 0
            assert results[0].status == 'passed'
            assert mock_run.call_count == 2
    
    def test_concurrent_task_execution(self):
        """Test concurrent execution of multiple SWE-bench tasks."""
        tasks = ['django__django-12345', 'flask__flask-67890', 'requests__requests-11111']
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({
                "results": {
                    task: {"resolved": True, "execution_time": 25.0}
                    for task in tasks
                }
            })
            
            results = self.validator.test_tasks_concurrent(tasks, max_workers=2)
            
            assert len(results) == len(tasks)
            assert all(r.status == 'passed' for r in results)
    
    def test_integration_with_evaluation_engine(self):
        """Test integration with the main evaluation engine."""
        with patch('sys.path'), \
             patch('importlib.import_module') as mock_import:
            
            # Mock the evaluation engine module
            mock_engine = MagicMock()
            mock_engine.run_swe_evaluation.return_value = {
                'results': {'django__django-12345': {'resolved': True}},
                'metadata': {'execution_time': 30.5}
            }
            mock_import.return_value = mock_engine
            
            result = self.validator.test_integration_with_engine(['django__django-12345'])
            
            assert result.status == 'passed'
            assert result.real_execution_validated is True
            assert 'resolved' in result.metrics
    
    def test_cleanup_after_tests(self):
        """Test cleanup operations after test execution."""
        # Create some temporary files and directories
        temp_files = [
            self.test_repo_dir / "temp_result_1.json",
            self.test_repo_dir / "temp_result_2.json"
        ]
        temp_dir = self.test_repo_dir / "temp_workspace"
        temp_dir.mkdir()
        
        for temp_file in temp_files:
            temp_file.write_text('{"test": "data"}')
        
        # Run cleanup
        self.validator.cleanup_test_artifacts(str(self.test_repo_dir))
        
        # Verify files and directories are cleaned up
        for temp_file in temp_files:
            assert not temp_file.exists()
        assert not temp_dir.exists()
    
    def test_generate_integration_report(self):
        """Test generation of integration test report."""
        # Mock some test results
        test_results = [
            TestResult('swe_bench_001', 'integration', 'passed', 30.2, True, 
                      {'resolved': True}, None, ['result.json']),
            TestResult('swe_bench_002', 'integration', 'failed', 15.1, False, 
                      {'resolved': False}, 'Task failed', [])
        ]
        
        validation_result = ValidationResult(
            adapter_name='swe_bench',
            integration_status='partial',
            dependencies_installed=True,
            test_results=test_results,
            performance_metrics={'avg_execution_time': 22.65},
            issues_found=['One task failed to resolve']
        )
        
        report = self.validator.generate_integration_report(validation_result)
        
        assert 'summary' in report
        assert 'test_results' in report
        assert 'performance_analysis' in report
        assert 'recommendations' in report
        assert report['summary']['total_tests'] == 2
        assert report['summary']['passed_tests'] == 1
        assert report['summary']['resolution_rate'] == 0.5
    
    def test_security_validation(self):
        """Test security validation of code changes."""
        # Create code with potential security issues
        insecure_code = self.test_repo_dir / "insecure.py"
        insecure_code.write_text("""
import os
import subprocess

def execute_command(user_input):
    # Security issue: command injection
    os.system(user_input)
    
def sql_query(user_id):
    # Security issue: SQL injection
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query
""")
        
        with patch('subprocess.run') as mock_run:
            # Mock security scanner output
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = """
insecure.py:6: B602 subprocess call with shell=True identified
insecure.py:10: B608 Possible SQL injection vector through string-based query construction
"""
            
            security_report = self.validator.validate_security(self.test_repo_dir)
            
            assert 'vulnerabilities' in security_report
            assert len(security_report['vulnerabilities']) > 0
            assert security_report['risk_level'] == 'HIGH'