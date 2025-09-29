"""
Comprehensive test runner for configuration-driven evaluation system.

This module provides a comprehensive test suite runner that executes all
unit tests, integration tests, and performance tests with detailed reporting.
"""

import pytest
import sys
import time
import os
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess


class ComprehensiveTestRunner:
    """Comprehensive test runner for the configuration system."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
        # Define test categories and their paths
        self.test_categories = {
            "unit_tests": [
                "evaluation_engine/tests/config/test_models.py",
                "evaluation_engine/tests/config/test_parser.py", 
                "evaluation_engine/tests/config/test_validator.py",
                "evaluation_engine/tests/config/test_builder.py",
                "evaluation_engine/tests/config/test_templates.py",
                "evaluation_engine/tests/config/test_evaluator.py",
                "evaluation_engine/tests/config/test_comprehensive_unit.py"
            ],
            "integration_tests": [
                "evaluation_engine/tests/integration/test_config_end_to_end.py",
                "evaluation_engine/tests/config/test_framework_integration.py"
            ],
            "api_tests": [
                "evaluation_engine/tests/api/test_config_basic.py",
                "evaluation_engine/tests/api/test_config_integration.py",
                "evaluation_engine/tests/api/test_config_endpoints.py"
            ],
            "cli_tests": [
                "evaluation_engine/tests/cli/test_config_cli_comprehensive.py"
            ],
            "performance_tests": [
                "evaluation_engine/tests/performance/test_config_performance.py"
            ]
        }
    
    def run_test_category(self, category: str, test_paths: List[str]) -> Dict:
        """Run tests for a specific category."""
        print(f"\n{'='*60}")
        print(f"Running {category.replace('_', ' ').title()}")
        print(f"{'='*60}")
        
        category_results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "duration": 0,
            "coverage": 0
        }
        
        start_time = time.time()
        
        for test_path in test_paths:
            if not os.path.exists(test_path):
                print(f"⚠️  Test file not found: {test_path}")
                category_results["skipped"] += 1
                continue
            
            print(f"\n📋 Running: {test_path}")
            
            try:
                # Run pytest with detailed output
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    test_path,
                    "-v",
                    "--tb=short",
                    "--durations=10",
                    "--cov=evaluation_engine.config",
                    "--cov-report=term-missing"
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print(f"✅ PASSED: {test_path}")
                    category_results["passed"] += 1
                else:
                    print(f"❌ FAILED: {test_path}")
                    category_results["failed"] += 1
                    category_results["errors"].append({
                        "test_path": test_path,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    })
                
                # Extract coverage information if available
                if "--cov" in result.stdout:
                    # Simple coverage extraction (could be improved)
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "TOTAL" in line and "%" in line:
                            try:
                                coverage = int(line.split()[-1].replace('%', ''))
                                category_results["coverage"] = max(category_results["coverage"], coverage)
                            except:
                                pass
                
            except subprocess.TimeoutExpired:
                print(f"⏰ TIMEOUT: {test_path}")
                category_results["failed"] += 1
                category_results["errors"].append({
                    "test_path": test_path,
                    "error": "Test execution timeout (300s)"
                })
            
            except Exception as e:
                print(f"💥 ERROR: {test_path} - {e}")
                category_results["failed"] += 1
                category_results["errors"].append({
                    "test_path": test_path,
                    "error": str(e)
                })
        
        category_results["duration"] = time.time() - start_time
        return category_results
    
    def run_all_tests(self) -> Dict:
        """Run all test categories."""
        print("🚀 Starting Comprehensive Configuration System Test Suite")
        print(f"Python: {sys.version}")
        print(f"Working Directory: {os.getcwd()}")
        
        self.start_time = time.time()
        
        # Run each test category
        for category, test_paths in self.test_categories.items():
            self.test_results[category] = self.run_test_category(category, test_paths)
        
        self.end_time = time.time()
        
        return self.generate_summary()
    
    def generate_summary(self) -> Dict:
        """Generate comprehensive test summary."""
        total_duration = self.end_time - self.start_time
        
        summary = {
            "total_duration": total_duration,
            "categories": {},
            "overall": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "success_rate": 0,
                "average_coverage": 0
            }
        }
        
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print(f"{'='*80}")
        
        total_coverage = 0
        coverage_count = 0
        
        for category, results in self.test_results.items():
            category_total = results["passed"] + results["failed"] + results["skipped"]
            success_rate = (results["passed"] / category_total * 100) if category_total > 0 else 0
            
            summary["categories"][category] = {
                "total": category_total,
                "passed": results["passed"],
                "failed": results["failed"],
                "skipped": results["skipped"],
                "success_rate": success_rate,
                "duration": results["duration"],
                "coverage": results["coverage"]
            }
            
            # Update overall stats
            summary["overall"]["total_tests"] += category_total
            summary["overall"]["passed"] += results["passed"]
            summary["overall"]["failed"] += results["failed"]
            summary["overall"]["skipped"] += results["skipped"]
            
            if results["coverage"] > 0:
                total_coverage += results["coverage"]
                coverage_count += 1
            
            # Print category summary
            status_icon = "✅" if results["failed"] == 0 else "❌"
            print(f"\n{status_icon} {category.replace('_', ' ').title()}")
            print(f"   Tests: {results['passed']} passed, {results['failed']} failed, {results['skipped']} skipped")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Duration: {results['duration']:.2f}s")
            if results["coverage"] > 0:
                print(f"   Coverage: {results['coverage']}%")
            
            # Print errors if any
            if results["errors"]:
                print(f"   ⚠️  Errors:")
                for error in results["errors"][:3]:  # Show first 3 errors
                    print(f"      - {error['test_path']}: {error.get('error', 'See logs')}")
                if len(results["errors"]) > 3:
                    print(f"      ... and {len(results['errors']) - 3} more errors")
        
        # Calculate overall metrics
        if summary["overall"]["total_tests"] > 0:
            summary["overall"]["success_rate"] = (
                summary["overall"]["passed"] / summary["overall"]["total_tests"] * 100
            )
        
        if coverage_count > 0:
            summary["overall"]["average_coverage"] = total_coverage / coverage_count
        
        # Print overall summary
        print(f"\n{'='*40}")
        print("🎯 OVERALL RESULTS")
        print(f"{'='*40}")
        print(f"Total Tests: {summary['overall']['total_tests']}")
        print(f"Passed: {summary['overall']['passed']}")
        print(f"Failed: {summary['overall']['failed']}")
        print(f"Skipped: {summary['overall']['skipped']}")
        print(f"Success Rate: {summary['overall']['success_rate']:.1f}%")
        print(f"Average Coverage: {summary['overall']['average_coverage']:.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")
        
        # Overall status
        if summary["overall"]["failed"] == 0:
            print(f"\n🎉 ALL TESTS PASSED! Configuration system is ready for production.")
        else:
            print(f"\n⚠️  {summary['overall']['failed']} tests failed. Review errors above.")
        
        return summary
    
    def run_specific_category(self, category: str) -> Dict:
        """Run tests for a specific category only."""
        if category not in self.test_categories:
            raise ValueError(f"Unknown test category: {category}")
        
        print(f"🎯 Running specific category: {category}")
        self.start_time = time.time()
        
        self.test_results[category] = self.run_test_category(
            category, self.test_categories[category]
        )
        
        self.end_time = time.time()
        return self.generate_summary()
    
    def run_quick_tests(self) -> Dict:
        """Run a quick subset of tests for rapid feedback."""
        quick_tests = {
            "quick_unit": [
                "evaluation_engine/tests/config/test_models.py",
                "evaluation_engine/tests/config/test_parser.py"
            ],
            "quick_integration": [
                "evaluation_engine/tests/config/test_framework_integration.py"
            ]
        }
        
        print("⚡ Running Quick Test Suite")
        self.start_time = time.time()
        
        for category, test_paths in quick_tests.items():
            self.test_results[category] = self.run_test_category(category, test_paths)
        
        self.end_time = time.time()
        return self.generate_summary()


def main():
    """Main entry point for test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Configuration System Test Runner")
    parser.add_argument(
        "--category", 
        choices=["unit_tests", "integration_tests", "api_tests", "cli_tests", "performance_tests"],
        help="Run tests for specific category only"
    )
    parser.add_argument(
        "--quick", 
        action="store_true",
        help="Run quick test suite for rapid feedback"
    )
    parser.add_argument(
        "--output", 
        help="Save detailed results to JSON file"
    )
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner()
    
    try:
        if args.quick:
            results = runner.run_quick_tests()
        elif args.category:
            results = runner.run_specific_category(args.category)
        else:
            results = runner.run_all_tests()
        
        # Save results if requested
        if args.output:
            import json
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n📄 Detailed results saved to: {args.output}")
        
        # Exit with appropriate code
        if results["overall"]["failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⏹️  Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()