#!/usr/bin/env python3
"""
Comprehensive test runner for all test categories.

Executes unit tests, integration tests, end-to-end tests, and performance benchmarks.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import argparse

# Add the project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.metrics_collector import MetricsCollector
from core.error_handler import ErrorHandler


class ComprehensiveTestRunner:
    """Comprehensive test runner for all test categories."""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.error_handler = ErrorHandler()
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run all unit tests."""
        print("🧪 Running Unit Tests...")
        
        unit_test_dir = Path(__file__).parent / "tests" / "unit"
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(unit_test_dir),
                "-v",
                "--tb=short",
                "--json-report",
                "--json-report-file=unit_test_results.json"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            return {
                'category': 'unit',
                'status': 'passed' if result.returncode == 0 else 'failed',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': self._extract_execution_time(result.stdout)
            }
        except Exception as e:
            return {
                'category': 'unit',
                'status': 'error',
                'error': str(e),
                'execution_time': 0
            }
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        print("🔗 Running Integration Tests...")
        
        integration_test_dir = Path(__file__).parent / "tests" / "integration"
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(integration_test_dir),
                "-v",
                "--tb=short",
                "--json-report",
                "--json-report-file=integration_test_results.json"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            return {
                'category': 'integration',
                'status': 'passed' if result.returncode == 0 else 'failed',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': self._extract_execution_time(result.stdout)
            }
        except Exception as e:
            return {
                'category': 'integration',
                'status': 'error',
                'error': str(e),
                'execution_time': 0
            }
    
    def run_e2e_tests(self) -> Dict[str, Any]:
        """Run all end-to-end tests."""
        print("🎯 Running End-to-End Tests...")
        
        e2e_test_dir = Path(__file__).parent / "tests" / "e2e"
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(e2e_test_dir),
                "-v",
                "--tb=short",
                "--json-report",
                "--json-report-file=e2e_test_results.json"
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            return {
                'category': 'e2e',
                'status': 'passed' if result.returncode == 0 else 'failed',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': self._extract_execution_time(result.stdout)
            }
        except Exception as e:
            return {
                'category': 'e2e',
                'status': 'error',
                'error': str(e),
                'execution_time': 0
            }
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run all performance benchmark tests."""
        print("⚡ Running Performance Tests...")
        
        performance_test_dir = Path(__file__).parent / "tests" / "performance"
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(performance_test_dir),
                "-v",
                "--tb=short",
                "--json-report",
                "--json-report-file=performance_test_results.json",
                "--benchmark-only"  # If using pytest-benchmark
            ], capture_output=True, text=True, cwd=Path(__file__).parent)
            
            return {
                'category': 'performance',
                'status': 'passed' if result.returncode == 0 else 'failed',
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': self._extract_execution_time(result.stdout)
            }
        except Exception as e:
            return {
                'category': 'performance',
                'status': 'error',
                'error': str(e),
                'execution_time': 0
            }
    
    def run_all_tests(self, categories: List[str] = None) -> Dict[str, Any]:
        """Run all test categories or specified categories."""
        if categories is None:
            categories = ['unit', 'integration', 'e2e', 'performance']
        
        self.start_time = time.time()
        print(f"🚀 Starting Comprehensive Test Suite - Categories: {', '.join(categories)}")
        print("=" * 80)
        
        test_runners = {
            'unit': self.run_unit_tests,
            'integration': self.run_integration_tests,
            'e2e': self.run_e2e_tests,
            'performance': self.run_performance_tests
        }
        
        results = {}
        
        for category in categories:
            if category in test_runners:
                print(f"\n📋 Executing {category.upper()} tests...")
                category_start = time.time()
                
                try:
                    result = test_runners[category]()
                    results[category] = result
                    
                    category_end = time.time()
                    category_time = category_end - category_start
                    
                    status_emoji = "✅" if result['status'] == 'passed' else "❌"
                    print(f"{status_emoji} {category.upper()} tests {result['status']} in {category_time:.2f}s")
                    
                    # Record metrics
                    self.metrics_collector.record_metric(f'{category}_execution_time', category_time)
                    self.metrics_collector.record_metric(f'{category}_status', 1 if result['status'] == 'passed' else 0)
                    
                except Exception as e:
                    error_result = {
                        'category': category,
                        'status': 'error',
                        'error': str(e),
                        'execution_time': 0
                    }
                    results[category] = error_result
                    print(f"❌ {category.upper()} tests failed with error: {str(e)}")
            else:
                print(f"⚠️  Unknown test category: {category}")
        
        self.end_time = time.time()
        self.test_results = results
        
        return results
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        if not self.test_results:
            return {'error': 'No test results available'}
        
        total_time = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        summary = {
            'overall': {
                'total_execution_time': total_time,
                'categories_run': len(self.test_results),
                'categories_passed': sum(1 for r in self.test_results.values() if r['status'] == 'passed'),
                'categories_failed': sum(1 for r in self.test_results.values() if r['status'] == 'failed'),
                'categories_error': sum(1 for r in self.test_results.values() if r['status'] == 'error'),
                'overall_success_rate': sum(1 for r in self.test_results.values() if r['status'] == 'passed') / len(self.test_results)
            },
            'category_details': self.test_results,
            'metrics': self.metrics_collector.get_metrics(),
            'recommendations': self._generate_recommendations()
        }
        
        return summary
    
    def print_summary_report(self):
        """Print formatted summary report to console."""
        summary = self.generate_summary_report()
        
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST SUITE SUMMARY")
        print("=" * 80)
        
        overall = summary['overall']
        print(f"⏱️  Total Execution Time: {overall['total_execution_time']:.2f} seconds")
        print(f"📈 Overall Success Rate: {overall['overall_success_rate']:.1%}")
        print(f"✅ Categories Passed: {overall['categories_passed']}")
        print(f"❌ Categories Failed: {overall['categories_failed']}")
        print(f"⚠️  Categories Error: {overall['categories_error']}")
        
        print("\n📋 Category Details:")
        print("-" * 40)
        
        for category, result in summary['category_details'].items():
            status_emoji = {
                'passed': '✅',
                'failed': '❌',
                'error': '⚠️'
            }.get(result['status'], '❓')
            
            print(f"{status_emoji} {category.upper()}: {result['status']} ({result.get('execution_time', 0):.2f}s)")
            
            if result['status'] == 'failed' and 'stderr' in result:
                print(f"   Error: {result['stderr'][:100]}...")
            elif result['status'] == 'error' and 'error' in result:
                print(f"   Error: {result['error']}")
        
        if summary['recommendations']:
            print("\n💡 Recommendations:")
            print("-" * 40)
            for i, rec in enumerate(summary['recommendations'], 1):
                print(f"{i}. {rec}")
        
        print("\n" + "=" * 80)
    
    def save_detailed_report(self, output_file: str = "comprehensive_test_report.json"):
        """Save detailed report to JSON file."""
        summary = self.generate_summary_report()
        
        output_path = Path(__file__).parent / output_file
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"📄 Detailed report saved to: {output_path}")
    
    def _extract_execution_time(self, stdout: str) -> float:
        """Extract execution time from pytest output."""
        try:
            # Look for pytest timing information
            lines = stdout.split('\n')
            for line in lines:
                if 'seconds' in line and ('passed' in line or 'failed' in line):
                    # Extract time from lines like "2 passed in 1.23s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.endswith('s') and i > 0:
                            return float(part[:-1])
            return 0.0
        except:
            return 0.0
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_categories = [cat for cat, result in self.test_results.items() if result['status'] == 'failed']
        error_categories = [cat for cat, result in self.test_results.items() if result['status'] == 'error']
        
        if failed_categories:
            recommendations.append(f"Review and fix failing tests in: {', '.join(failed_categories)}")
        
        if error_categories:
            recommendations.append(f"Investigate test execution errors in: {', '.join(error_categories)}")
        
        # Performance recommendations
        if 'performance' in self.test_results:
            perf_result = self.test_results['performance']
            if perf_result.get('execution_time', 0) > 300:  # 5 minutes
                recommendations.append("Performance tests are taking longer than expected - consider optimization")
        
        # Integration test recommendations
        if 'integration' in self.test_results and self.test_results['integration']['status'] == 'failed':
            recommendations.append("Integration test failures may indicate adapter compatibility issues")
        
        if not recommendations:
            recommendations.append("All tests passed successfully! Consider adding more test coverage.")
        
        return recommendations


def main():
    """Main entry point for comprehensive test runner."""
    parser = argparse.ArgumentParser(description='Run comprehensive test suite')
    parser.add_argument(
        '--categories', 
        nargs='+', 
        choices=['unit', 'integration', 'e2e', 'performance'],
        default=['unit', 'integration', 'e2e', 'performance'],
        help='Test categories to run'
    )
    parser.add_argument(
        '--output', 
        default='comprehensive_test_report.json',
        help='Output file for detailed report'
    )
    parser.add_argument(
        '--no-report', 
        action='store_true',
        help='Skip generating detailed report file'
    )
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner()
    
    try:
        # Run tests
        results = runner.run_all_tests(args.categories)
        
        # Print summary
        runner.print_summary_report()
        
        # Save detailed report
        if not args.no_report:
            runner.save_detailed_report(args.output)
        
        # Exit with appropriate code
        failed_categories = sum(1 for r in results.values() if r['status'] != 'passed')
        sys.exit(failed_categories)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()