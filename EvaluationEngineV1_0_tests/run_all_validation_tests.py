#!/usr/bin/env python3
"""
Run All Validation Tests

This script runs all validation tests in the correct order to ensure
complete system validation and requirements coverage.
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path


def setup_logging(verbose: bool = False):
    """Set up logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('all_validation_tests.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def print_section_header(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")


def run_command(command: list, description: str, timeout: int = 300) -> bool:
    """Run a command and return success status"""
    print(f"\n🚀 {description}")
    print(f"   Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path.cwd()
        )
        
        if result.returncode == 0:
            print(f"   ✅ {description} - PASSED")
            if result.stdout.strip():
                print(f"   📄 Output: {result.stdout.strip()[:200]}...")
            return True
        else:
            print(f"   ❌ {description} - FAILED")
            if result.stderr.strip():
                print(f"   ⚠️  Error: {result.stderr.strip()[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ {description} - TIMEOUT ({timeout}s)")
        return False
    except Exception as e:
        print(f"   💥 {description} - ERROR: {str(e)}")
        return False


async def run_async_validation(script_path: str, description: str) -> bool:
    """Run an async validation script"""
    print(f"\n🚀 {description}")
    print(f"   Script: {script_path}")
    
    try:
        # Import and run the validation
        if script_path == "quick_validation_check.py":
            from quick_validation_check import main as quick_main
            return quick_main()
        elif script_path == "validate_complete_system.py":
            from validate_complete_system import SystemValidator
            validator = SystemValidator(verbose=False)
            return await validator.validate_system()
        elif script_path == "run_final_validation.py":
            from run_final_validation import run_validation
            return await run_validation()
        else:
            print(f"   ⚠️  Unknown async script: {script_path}")
            return False
            
    except Exception as e:
        print(f"   ❌ {description} - FAILED: {str(e)}")
        return False


def run_pytest_tests(test_path: str, description: str) -> bool:
    """Run pytest tests"""
    if not Path(test_path).exists():
        print(f"   ⚠️  Test path not found: {test_path}")
        return False
    
    command = ["python", "-m", "pytest", test_path, "-v", "--tb=short"]
    return run_command(command, description, timeout=600)


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Run All Validation Tests")
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run only quick validation tests'
    )
    parser.add_argument(
        '--skip-integration',
        action='store_true',
        help='Skip integration tests that require external dependencies'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    print("🎯 EvaluationEngineV1_0_tests - Complete Validation Test Suite")
    print("=" * 60)
    
    start_time = time.time()
    test_results = {}
    
    try:
        # Phase 1: Quick Validation Check
        print_section_header("Phase 1: Quick Validation Check")
        test_results['quick_validation'] = asyncio.run(
            run_async_validation("quick_validation_check.py", "Quick Validation Check")
        )
        
        if not test_results['quick_validation'] and not args.quick:
            print("⚠️  Quick validation failed. Continuing with other tests...")
        
        if args.quick:
            print("\n🏃 Quick mode enabled - skipping comprehensive tests")
        else:
            # Phase 2: Unit Tests
            print_section_header("Phase 2: Unit Tests")
            test_results['unit_tests'] = run_pytest_tests(
                "tests/unit/",
                "Unit Tests"
            )
            
            # Phase 3: Integration Tests
            if not args.skip_integration:
                print_section_header("Phase 3: Integration Tests")
                test_results['integration_tests'] = run_pytest_tests(
                    "tests/integration/",
                    "Integration Tests"
                )
            else:
                print_section_header("Phase 3: Integration Tests (SKIPPED)")
                test_results['integration_tests'] = True  # Skip but don't fail
            
            # Phase 4: End-to-End Tests
            print_section_header("Phase 4: End-to-End Tests")
            test_results['e2e_tests'] = run_pytest_tests(
                "tests/e2e/",
                "End-to-End Tests"
            )
            
            # Phase 5: Performance Tests
            print_section_header("Phase 5: Performance Tests")
            test_results['performance_tests'] = run_pytest_tests(
                "tests/performance/",
                "Performance Tests"
            )
            
            # Phase 6: Final Integration Validation
            print_section_header("Phase 6: Final Integration Validation")
            test_results['final_integration'] = asyncio.run(
                run_async_validation("run_final_validation.py", "Final Integration Validation")
            )
            
            # Phase 7: Complete System Validation
            print_section_header("Phase 7: Complete System Validation")
            test_results['system_validation'] = asyncio.run(
                run_async_validation("validate_complete_system.py", "Complete System Validation")
            )
        
        # Generate Summary
        end_time = time.time()
        total_time = end_time - start_time
        
        print_section_header("VALIDATION SUMMARY")
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        
        print(f"📊 Test Results:")
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status} {test_name.replace('_', ' ').title()}")
        
        print(f"\n📈 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {total_tests - passed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"   Execution Time: {total_time:.2f} seconds")
        
        # Final Status
        if passed_tests == total_tests:
            print(f"\n🎉 ALL VALIDATION TESTS PASSED!")
            print(f"✅ The EvaluationEngineV1_0_tests framework is fully validated and ready for use.")
            
            print(f"\n📄 Generated Reports:")
            report_files = [
                "final_integration_validation_report.json",
                "FINAL_INTEGRATION_VALIDATION_REPORT.md",
                "complete_system_validation_report.json",
                "COMPLETE_SYSTEM_VALIDATION_REPORT.md",
                "all_validation_tests.log"
            ]
            
            for report_file in report_files:
                if Path(report_file).exists():
                    print(f"   📋 {report_file}")
            
            print(f"\n🚀 Next Steps:")
            print(f"   1. Review the generated reports for detailed results")
            print(f"   2. Use the testing framework for your evaluation needs")
            print(f"   3. Refer to docs/usage.md for usage instructions")
            
            return True
            
        else:
            failed_tests = [name for name, result in test_results.items() if not result]
            print(f"\n⚠️  {len(failed_tests)} VALIDATION TESTS FAILED!")
            print(f"❌ Failed tests: {', '.join(failed_tests)}")
            
            print(f"\n🔧 Recommended Actions:")
            print(f"   1. Review the test logs for specific error details")
            print(f"   2. Fix the issues in the failed test categories")
            print(f"   3. Re-run the validation tests")
            print(f"   4. Do not use the framework until all tests pass")
            
            return False
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Validation interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Validation failed with error: {str(e)}")
        print(f"\n💥 Validation failed with unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Critical error: {str(e)}")
        sys.exit(1)