#!/usr/bin/env python3
"""
Final Validation Test Runner

This script runs the complete final integration and validation test suite
for the EvaluationEngineV1_0_tests framework.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from final_integration_validator import FinalIntegrationValidator


def setup_logging():
    """Set up comprehensive logging for validation"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('final_validation.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


async def run_validation():
    """Run the complete validation suite"""
    print("🚀 Starting Final Integration and Validation Testing")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Initialize validator
        validator = FinalIntegrationValidator()
        
        # Run complete validation
        test_suite = await validator.run_complete_validation()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Display results
        print("\n" + "=" * 60)
        print("🏁 FINAL VALIDATION RESULTS")
        print("=" * 60)
        
        # Overall status
        status_emoji = "✅" if test_suite.final_status == "passed" else "❌"
        print(f"{status_emoji} Overall Status: {test_suite.final_status.upper()}")
        print(f"⏱️  Total Execution Time: {total_time:.2f} seconds")
        print()
        
        # Test summary
        print("📊 Test Summary:")
        print(f"   Total Tests: {test_suite.total_tests}")
        print(f"   ✅ Passed: {test_suite.passed_tests}")
        print(f"   ❌ Failed: {test_suite.failed_tests}")
        print(f"   ⏭️  Skipped: {test_suite.skipped_tests}")
        print()
        
        # Requirements coverage
        total_reqs = len(test_suite.requirements_coverage)
        covered_reqs = sum(1 for covered in test_suite.requirements_coverage.values() if covered)
        coverage_pct = (covered_reqs / total_reqs) * 100 if total_reqs > 0 else 0
        
        print("📋 Requirements Coverage:")
        print(f"   Coverage: {coverage_pct:.1f}% ({covered_reqs}/{total_reqs})")
        
        uncovered = [req for req, covered in test_suite.requirements_coverage.items() if not covered]
        if uncovered:
            print(f"   ⚠️  Uncovered: {', '.join(uncovered)}")
        print()
        
        # Component status
        print("🔧 Component Status:")
        for component, status in test_suite.component_status.items():
            emoji = "✅" if status == "passed" else "❌"
            print(f"   {emoji} {component}: {status}")
        print()
        
        # Failed tests details
        failed_results = [r for r in test_suite.validation_results if r.status == "failed"]
        if failed_results:
            print("❌ Failed Tests:")
            for result in failed_results:
                print(f"   • {result.test_name} ({result.component})")
                if result.errors:
                    for error in result.errors[:2]:  # Show first 2 errors
                        print(f"     - {error}")
            print()
        
        # Success message or failure details
        if test_suite.final_status == "passed":
            print("🎉 All validation tests passed! The framework is ready for use.")
        else:
            print("⚠️  Some validation tests failed. Please review the detailed report.")
        
        print("\n📄 Detailed reports saved:")
        print("   • final_integration_validation_report.json")
        print("   • FINAL_INTEGRATION_VALIDATION_REPORT.md")
        print("   • final_validation.log")
        
        return test_suite.final_status == "passed"
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {str(e)}")
        logging.error(f"Validation failed: {str(e)}", exc_info=True)
        return False


def main():
    """Main entry point"""
    setup_logging()
    
    try:
        success = asyncio.run(run_validation())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()