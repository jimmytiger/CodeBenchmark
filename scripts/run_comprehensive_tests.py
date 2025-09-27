#!/usr/bin/env python3
"""
Comprehensive test runner script for AI Evaluation Engine.
"""

import argparse
import subprocess
import sys
import time
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import concurrent.futures
from dataclasses import dataclass


@dataclass
class TestResult:
    """Test result data structure."""
    name: str
    status: str  # 'passed', 'failed', 'skipped'
    duration: float
    output: str
    error: Optional[str] = None


class ComprehensiveTestRunner:
    """Comprehensive test runner for evaluation engine."""
    
    def __init__(self, verbose: bool = False, parallel: bool = True):
        self.verbose = verbose
        self.parallel = parallel
        self.results: Dict[str, TestResult] = {}
        self.start_time = time.time()
    
    def run_command(self, command: List[str], name: str, timeout: int = 300) -> TestResult:
        """Run a command and return test result."""
        if self.verbose:
            print(f"Running {name}: {' '.join(command)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                status = 'passed'
                error = None
            else:
                status = 'failed'
                error = result.stderr
            
            return TestResult(
                name=name,
                status=status,
                duration=duration,
                output=result.stdout,
                error=error
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                name=name,
                status='failed',
                duration=duration,
                output='',
                error=f'Test timed out after {timeout} seconds'
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name=name,
                status='failed',
                duration=duration,
                output='',
                error=str(e)
            )
    
    def run_unit_tests(self) -> TestResult:
        """Run unit tests."""
        command = [
            'pytest',
            'evaluation_engine_tests/unit/',
            '--cov=evaluation_engine',
            '--cov-report=html:htmlcov/unit',
            '--cov-report=xml:coverage-unit.xml',
            '--cov-fail-under=90',
            '--junitxml=junit/unit-results.xml',
            '-v'
        ]
        
        if not self.verbose:
            command.append('-q')
        
        return self.run_command(command, 'Unit Tests', timeout=600)
    
    def run_integration_tests(self) -> TestResult:
        """Run integration tests."""
        command = [
            'pytest',
            'evaluation_engine_tests/integration/',
            '--junitxml=junit/integration-results.xml',
            '-v'
        ]
        
        if not self.verbose:
            command.append('-q')
        
        return self.run_command(command, 'Integration Tests', timeout=900)
    
    def run_e2e_tests(self) -> TestResult:
        """Run end-to-end tests."""
        command = [
            'pytest',
            'evaluation_engine_tests/e2e/',
            '--junitxml=junit/e2e-results.xml',
            '-v',
            '-m', 'e2e and not slow'
        ]
        
        if not self.verbose:
            command.append('-q')
        
        return self.run_command(command, 'E2E Tests', timeout=1200)
    
    def run_performance_tests(self) -> TestResult:
        """Run performance tests."""
        command = [
            'pytest',
            'evaluation_engine_tests/performance/',
            '--benchmark-only',
            '--benchmark-json=benchmark-results.json',
            '--junitxml=junit/performance-results.xml',
            '-v'
        ]
        
        if not self.verbose:
            command.append('-q')
        
        return self.run_command(command, 'Performance Tests', timeout=1800)
    
    def run_security_tests(self) -> TestResult:
        """Run security tests."""
        command = [
            'pytest',
            'evaluation_engine_tests/security/',
            '--junitxml=junit/security-results.xml',
            '-v',
            '-m', 'security and not slow'
        ]
        
        if not self.verbose:
            command.append('-q')
        
        return self.run_command(command, 'Security Tests', timeout=900)
    
    def run_code_quality_checks(self) -> TestResult:
        """Run code quality checks."""
        checks = [
            (['black', '--check', 'evaluation_engine/', 'evaluation_engine_tests/'], 'Black formatting'),
            (['isort', '--check-only', 'evaluation_engine/', 'evaluation_engine_tests/'], 'Import sorting'),
            (['flake8', 'evaluation_engine/', 'evaluation_engine_tests/', '--max-line-length=100'], 'Flake8 linting'),
            (['mypy', 'evaluation_engine/', '--ignore-missing-imports'], 'Type checking'),
        ]
        
        all_passed = True
        combined_output = []
        combined_errors = []
        start_time = time.time()
        
        for command, check_name in checks:
            if self.verbose:
                print(f"Running {check_name}...")
            
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                all_passed = False
                combined_errors.append(f"{check_name} failed:\n{result.stderr}")
            
            combined_output.append(f"{check_name}: {'PASSED' if result.returncode == 0 else 'FAILED'}")
        
        duration = time.time() - start_time
        
        return TestResult(
            name='Code Quality Checks',
            status='passed' if all_passed else 'failed',
            duration=duration,
            output='\n'.join(combined_output),
            error='\n'.join(combined_errors) if combined_errors else None
        )
    
    def run_security_scans(self) -> TestResult:
        """Run security scanning tools."""
        scans = [
            (['bandit', '-r', 'evaluation_engine/', '-f', 'json', '-o', 'bandit-report.json'], 'Bandit security scan'),
            (['safety', 'check', '--json', '--output', 'safety-report.json'], 'Safety dependency scan'),
        ]
        
        all_passed = True
        combined_output = []
        combined_errors = []
        start_time = time.time()
        
        for command, scan_name in scans:
            if self.verbose:
                print(f"Running {scan_name}...")
            
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            
            # Bandit and Safety return non-zero on findings, which is expected
            if scan_name == 'Bandit security scan':
                # Check if bandit found high severity issues
                try:
                    with open('bandit-report.json', 'r') as f:
                        bandit_data = json.load(f)
                        high_severity = sum(1 for issue in bandit_data.get('results', []) 
                                          if issue.get('issue_severity') == 'HIGH')
                        if high_severity > 0:
                            all_passed = False
                            combined_errors.append(f"Bandit found {high_severity} high severity issues")
                except Exception as e:
                    combined_errors.append(f"Failed to parse Bandit results: {e}")
            
            elif scan_name == 'Safety dependency scan':
                # Check if safety found vulnerabilities
                try:
                    with open('safety-report.json', 'r') as f:
                        safety_data = json.load(f)
                        if safety_data:  # Non-empty means vulnerabilities found
                            all_passed = False
                            combined_errors.append(f"Safety found {len(safety_data)} vulnerabilities")
                except Exception as e:
                    combined_errors.append(f"Failed to parse Safety results: {e}")
            
            combined_output.append(f"{scan_name}: {'PASSED' if result.returncode == 0 else 'COMPLETED'}")
        
        duration = time.time() - start_time
        
        return TestResult(
            name='Security Scans',
            status='passed' if all_passed else 'failed',
            duration=duration,
            output='\n'.join(combined_output),
            error='\n'.join(combined_errors) if combined_errors else None
        )
    
    def run_all_tests(self, test_types: List[str]) -> Dict[str, TestResult]:
        """Run all specified test types."""
        test_functions = {
            'unit': self.run_unit_tests,
            'integration': self.run_integration_tests,
            'e2e': self.run_e2e_tests,
            'performance': self.run_performance_tests,
            'security': self.run_security_tests,
            'quality': self.run_code_quality_checks,
            'security-scan': self.run_security_scans,
        }
        
        # Create output directories
        os.makedirs('junit', exist_ok=True)
        os.makedirs('htmlcov', exist_ok=True)
        
        if self.parallel and len(test_types) > 1:
            # Run tests in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                future_to_test = {
                    executor.submit(test_functions[test_type]): test_type
                    for test_type in test_types
                    if test_type in test_functions
                }
                
                for future in concurrent.futures.as_completed(future_to_test):
                    test_type = future_to_test[future]
                    try:
                        result = future.result()
                        self.results[test_type] = result
                        if self.verbose:
                            print(f"{test_type} completed: {result.status}")
                    except Exception as e:
                        self.results[test_type] = TestResult(
                            name=test_type,
                            status='failed',
                            duration=0,
                            output='',
                            error=str(e)
                        )
        else:
            # Run tests sequentially
            for test_type in test_types:
                if test_type in test_functions:
                    if self.verbose:
                        print(f"Starting {test_type}...")
                    
                    result = test_functions[test_type]()
                    self.results[test_type] = result
                    
                    if self.verbose:
                        print(f"{test_type} completed: {result.status}")
        
        return self.results
    
    def generate_report(self, output_file: str = 'test-report.html'):
        """Generate HTML test report."""
        total_duration = time.time() - self.start_time
        
        passed_tests = sum(1 for result in self.results.values() if result.status == 'passed')
        failed_tests = sum(1 for result in self.results.values() if result.status == 'failed')
        total_tests = len(self.results)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Comprehensive Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .test-result {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .test-output {{ background: #f9f9f9; padding: 10px; margin-top: 10px; font-family: monospace; white-space: pre-wrap; }}
        .error {{ background: #ffe6e6; }}
    </style>
</head>
<body>
    <h1>Comprehensive Test Report</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Tests:</strong> {total_tests}</p>
        <p><strong>Passed:</strong> <span class="passed">{passed_tests}</span></p>
        <p><strong>Failed:</strong> <span class="failed">{failed_tests}</span></p>
        <p><strong>Success Rate:</strong> {(passed_tests/total_tests*100):.1f}%</p>
        <p><strong>Total Duration:</strong> {total_duration:.2f} seconds</p>
        <p><strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <h2>Test Results</h2>
"""
        
        for test_name, result in self.results.items():
            status_class = result.status
            html_content += f"""
    <div class="test-result">
        <h3>{result.name} - <span class="{status_class}">{result.status.upper()}</span></h3>
        <p><strong>Duration:</strong> {result.duration:.2f} seconds</p>
        
        {f'<div class="test-output">{result.output}</div>' if result.output else ''}
        
        {f'<div class="test-output error"><strong>Error:</strong><br>{result.error}</div>' if result.error else ''}
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"Test report generated: {output_file}")
    
    def print_summary(self):
        """Print test summary to console."""
        total_duration = time.time() - self.start_time
        
        print("\n" + "="*60)
        print("COMPREHENSIVE TEST SUMMARY")
        print("="*60)
        
        passed_tests = 0
        failed_tests = 0
        
        for test_name, result in self.results.items():
            status_symbol = "✓" if result.status == 'passed' else "✗"
            status_color = '\033[92m' if result.status == 'passed' else '\033[91m'
            reset_color = '\033[0m'
            
            print(f"{status_color}{status_symbol} {result.name:<25} {result.duration:>8.2f}s{reset_color}")
            
            if result.status == 'passed':
                passed_tests += 1
            else:
                failed_tests += 1
                if result.error and self.verbose:
                    print(f"  Error: {result.error[:100]}...")
        
        print("-" * 60)
        print(f"Total: {len(self.results)} | Passed: {passed_tests} | Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/len(self.results)*100):.1f}%")
        print(f"Total Duration: {total_duration:.2f} seconds")
        print("="*60)
        
        return failed_tests == 0


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Run comprehensive tests for AI Evaluation Engine')
    
    parser.add_argument(
        '--tests',
        nargs='+',
        choices=['unit', 'integration', 'e2e', 'performance', 'security', 'quality', 'security-scan', 'all'],
        default=['all'],
        help='Test types to run'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--sequential',
        action='store_true',
        help='Run tests sequentially instead of in parallel'
    )
    
    parser.add_argument(
        '--report',
        default='test-report.html',
        help='Output file for HTML report'
    )
    
    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Skip generating HTML report'
    )
    
    args = parser.parse_args()
    
    # Expand 'all' to all test types
    if 'all' in args.tests:
        test_types = ['unit', 'integration', 'e2e', 'performance', 'security', 'quality', 'security-scan']
    else:
        test_types = args.tests
    
    # Initialize test runner
    runner = ComprehensiveTestRunner(
        verbose=args.verbose,
        parallel=not args.sequential
    )
    
    print(f"Starting comprehensive tests: {', '.join(test_types)}")
    print(f"Parallel execution: {not args.sequential}")
    print("-" * 60)
    
    # Run tests
    results = runner.run_all_tests(test_types)
    
    # Print summary
    success = runner.print_summary()
    
    # Generate report
    if not args.no_report:
        runner.generate_report(args.report)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()