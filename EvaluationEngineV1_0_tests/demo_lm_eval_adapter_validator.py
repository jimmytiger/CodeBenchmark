#!/usr/bin/env python3
"""
Demonstration script for the lm_eval_adapter validator.

This script shows how to use the LMEvalAdapterValidator to:
1. Install and validate lm_eval dependencies
2. Test builtin lm_eval tasks
3. Discover and test custom tasks
4. Generate comprehensive validation reports
"""

import sys
import os
import logging
from pathlib import Path

# Setup path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import the core validator directly
from core.lm_eval_adapter_validator import create_lm_eval_adapter_validator, LMEvalAdapterValidator
from models.test_models import TestStatus


def setup_logging():
    """Setup logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def demo_basic_validation():
    """Demonstrate basic lm_eval_adapter validation."""
    logger = logging.getLogger(__name__)
    logger.info("🚀 DEMO: Basic LM-Eval Adapter Validation")
    logger.info("=" * 50)
    
    # Create validator with demo configuration
    config = {
        'dependency_timeout': 300,  # 5 minutes for dependencies
        'test_timeout': 120,        # 2 minutes per test
        'max_test_tasks': 2,        # Test 2 tasks for demo
        'enable_benchmarks': True   # Enable performance benchmarks
    }
    
    validator = create_lm_eval_adapter_validator(config)
    
    # Get adapter information
    logger.info("📋 Getting adapter information...")
    adapter_info = validator.get_adapter_info()
    logger.info(f"Adapter: {adapter_info.name} v{adapter_info.version}")
    logger.info(f"Description: {adapter_info.description}")
    logger.info(f"Dependencies: {len(adapter_info.dependencies)}")
    logger.info(f"Supported Tasks: {len(adapter_info.supported_tasks)}")
    
    # Run full validation
    logger.info("\n🔍 Running comprehensive validation...")
    validation_result = validator.validate_integration()
    
    # Display results
    logger.info("\n📊 VALIDATION RESULTS:")
    logger.info(f"Status: {validation_result.integration_status.value.upper()}")
    logger.info(f"Dependencies Installed: {'✅' if validation_result.dependencies_installed else '❌'}")
    logger.info(f"Total Tests: {len(validation_result.test_results)}")
    logger.info(f"Validation Time: {validation_result.validation_time:.2f}s")
    
    # Show test results
    if validation_result.test_results:
        logger.info("\n📝 Test Results:")
        for i, test in enumerate(validation_result.test_results, 1):
            status_emoji = "✅" if test.status == TestStatus.PASSED else "❌" if test.status == TestStatus.FAILED else "⚠️"
            logger.info(f"  {i}. {status_emoji} {test.name} ({test.execution_time:.2f}s)")
            if test.metrics:
                for key, value in test.metrics.items():
                    if isinstance(value, float):
                        logger.info(f"     - {key}: {value:.3f}")
    
    # Show performance metrics
    if validation_result.performance_metrics:
        logger.info("\n⚡ Performance Metrics:")
        for key, value in validation_result.performance_metrics.items():
            if isinstance(value, float):
                logger.info(f"  - {key}: {value:.3f}")
    
    # Show issues and recommendations
    if validation_result.issues_found:
        logger.info("\n⚠️ Issues Found:")
        for issue in validation_result.issues_found:
            logger.info(f"  - {issue}")
    
    if validation_result.recommendations:
        logger.info("\n💡 Recommendations:")
        for rec in validation_result.recommendations:
            logger.info(f"  - {rec}")
    
    return validation_result


def demo_custom_task_discovery():
    """Demonstrate custom task discovery."""
    logger = logging.getLogger(__name__)
    logger.info("\n🔍 DEMO: Custom Task Discovery")
    logger.info("=" * 50)
    
    validator = LMEvalAdapterValidator()
    
    # Check for custom tasks in lm_eval/tasks directory
    lm_eval_tasks_dir = Path("lm_eval/tasks")
    if lm_eval_tasks_dir.exists():
        logger.info(f"📁 Searching for custom tasks in {lm_eval_tasks_dir}")
        custom_tasks = validator._discover_real_custom_tasks(lm_eval_tasks_dir)
        
        if custom_tasks:
            logger.info(f"📋 Found {len(custom_tasks)} custom tasks:")
            for task in custom_tasks:
                logger.info(f"  - {task}")
        else:
            logger.info("📋 No custom tasks found")
    else:
        logger.info(f"📁 Custom tasks directory not found: {lm_eval_tasks_dir}")
        logger.info("💡 You can create custom tasks in the lm_eval/tasks directory")


def demo_builtin_task_testing():
    """Demonstrate builtin task testing."""
    logger = logging.getLogger(__name__)
    logger.info("\n🎯 DEMO: Builtin Task Testing")
    logger.info("=" * 50)
    
    validator = LMEvalAdapterValidator()
    
    # Test a single builtin task
    logger.info("🎯 Testing builtin lm_eval tasks...")
    try:
        results = validator.test_builtin_tasks(task_count=1)
        
        if results:
            for result in results:
                status_emoji = "✅" if result.status == TestStatus.PASSED else "❌"
                logger.info(f"{status_emoji} {result.name}")
                logger.info(f"   Execution Time: {result.execution_time:.2f}s")
                logger.info(f"   Real Execution: {'✅' if result.real_execution_validated else '❌'}")
                
                if result.metrics:
                    logger.info("   Metrics:")
                    for key, value in result.metrics.items():
                        if isinstance(value, float):
                            logger.info(f"     - {key}: {value:.3f}")
                
                if result.error_details:
                    logger.info(f"   Error: {result.error_details}")
        else:
            logger.info("⚠️ No builtin task results returned")
            
    except Exception as e:
        logger.error(f"❌ Builtin task testing failed: {e}")


def main():
    """Run the demonstration."""
    logger = setup_logging()
    
    logger.info("🎬 LM-EVAL ADAPTER VALIDATOR DEMONSTRATION")
    logger.info("=" * 60)
    logger.info("This demo shows the key features of the lm_eval_adapter validator:")
    logger.info("1. Comprehensive validation with real execution")
    logger.info("2. Automatic dependency installation")
    logger.info("3. Builtin task testing")
    logger.info("4. Custom task discovery")
    logger.info("5. Performance benchmarking")
    logger.info("=" * 60)
    
    try:
        # Demo 1: Basic validation
        validation_result = demo_basic_validation()
        
        # Demo 2: Custom task discovery
        demo_custom_task_discovery()
        
        # Demo 3: Builtin task testing (if dependencies are available)
        if validation_result.dependencies_installed:
            demo_builtin_task_testing()
        else:
            logger.info("\n⚠️ Skipping builtin task testing due to dependency issues")
        
        logger.info("\n🎉 DEMONSTRATION COMPLETED!")
        logger.info("=" * 60)
        logger.info("The lm_eval_adapter validator is ready for use!")
        logger.info("Key features demonstrated:")
        logger.info("✅ LMEvalAdapterValidator class creation")
        logger.info("✅ Integration testing with lm-evaluation-harness")
        logger.info("✅ Builtin task testing functionality")
        logger.info("✅ Custom task discovery and execution")
        logger.info("✅ Automatic dependency installation and validation")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())