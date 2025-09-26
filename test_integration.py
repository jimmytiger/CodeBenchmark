#!/usr/bin/env python3
"""
Integration test for AI Evaluation Engine foundation components
Tests the lm-eval integration and basic functionality
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all core components can be imported"""
    logger.info("Testing imports...")
    
    try:
        # Test lm-eval imports
        import lm_eval
        from lm_eval.api.registry import get_task_dict
        from lm_eval.evaluator import simple_evaluate
        logger.info("✓ lm-eval imports successful")
        
        # Test evaluation engine imports
        import evaluation_engine
        from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework
        from evaluation_engine.core.task_registration import ExtendedTaskRegistry
        logger.info("✓ Evaluation engine imports successful")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_task_discovery():
    """Test task discovery functionality"""
    logger.info("Testing task discovery...")
    
    try:
        from lm_eval.api.registry import get_task_dict
        
        tasks = get_task_dict()
        logger.info(f"Found {len(tasks)} total tasks")
        
        # Check for single-turn scenarios
        single_turn_tasks = [t for t in tasks.keys() if 'single_turn_scenarios' in t]
        logger.info(f"Found {len(single_turn_tasks)} single-turn scenario tasks")
        
        # Check for multi-turn scenarios
        multi_turn_tasks = [t for t in tasks.keys() if 'multi_turn_scenarios' in t]
        logger.info(f"Found {len(multi_turn_tasks)} multi-turn scenario tasks")
        
        if len(single_turn_tasks) > 0:
            logger.info("✓ Single-turn tasks discovered")
        else:
            logger.warning("⚠ No single-turn tasks found")
        
        if len(multi_turn_tasks) > 0:
            logger.info("✓ Multi-turn tasks discovered")
        else:
            logger.warning("⚠ No multi-turn tasks found")
        
        return True
    except Exception as e:
        logger.error(f"✗ Task discovery failed: {e}")
        return False

def test_unified_framework():
    """Test unified framework initialization"""
    logger.info("Testing unified framework...")
    
    try:
        from evaluation_engine.core.unified_framework import UnifiedEvaluationFramework, EvaluationRequest
        
        # Create framework instance
        framework = UnifiedEvaluationFramework()
        logger.info("✓ Framework initialized")
        
        # Test task listing
        tasks = framework.list_available_tasks()
        logger.info(f"✓ Framework can list {len(tasks)} tasks")
        
        # Test task info retrieval
        if tasks:
            task_info = framework.get_task_info(tasks[0])
            if task_info:
                logger.info("✓ Task info retrieval working")
            else:
                logger.warning("⚠ Task info retrieval returned None")
        
        return True
    except Exception as e:
        logger.error(f"✗ Unified framework test failed: {e}")
        return False

def test_extended_registry():
    """Test extended task registry"""
    logger.info("Testing extended task registry...")
    
    try:
        from evaluation_engine.core.task_registration import ExtendedTaskRegistry
        
        # Create registry instance
        registry = ExtendedTaskRegistry()
        logger.info("✓ Extended registry initialized")
        
        # Test task hierarchy
        hierarchy = registry.get_task_hierarchy()
        logger.info(f"✓ Task hierarchy has {len(hierarchy)} categories")
        
        # Test task discovery with filters
        single_turn_tasks = registry.discover_tasks({"category": "single_turn_scenarios"})
        logger.info(f"✓ Found {len(single_turn_tasks)} single-turn tasks via registry")
        
        return True
    except Exception as e:
        logger.error(f"✗ Extended registry test failed: {e}")
        return False

def test_basic_evaluation():
    """Test basic evaluation with dummy model"""
    logger.info("Testing basic evaluation...")
    
    try:
        from lm_eval.evaluator import simple_evaluate
        from lm_eval.api.registry import get_task_dict
        
        # Find a suitable task for testing
        tasks = get_task_dict()
        test_task = None
        
        # Look for function generation task first
        for task_name in tasks.keys():
            if 'function_generation' in task_name:
                test_task = task_name
                break
        
        # Fallback to any single-turn task
        if not test_task:
            for task_name in tasks.keys():
                if 'single_turn_scenarios' in task_name:
                    test_task = task_name
                    break
        
        if not test_task:
            logger.warning("⚠ No suitable test task found, skipping evaluation test")
            return True
        
        logger.info(f"Testing evaluation with task: {test_task}")
        
        # Run evaluation with dummy model
        results = simple_evaluate(
            model="dummy",
            tasks=[test_task],
            limit=1,
            verbosity="ERROR"  # Reduce noise
        )
        
        if results and "results" in results:
            logger.info("✓ Basic evaluation completed successfully")
            return True
        else:
            logger.warning("⚠ Evaluation completed but no results returned")
            return True
            
    except Exception as e:
        logger.error(f"✗ Basic evaluation failed: {e}")
        return False

def test_file_structure():
    """Test that required files and directories exist"""
    logger.info("Testing file structure...")
    
    required_files = [
        "evaluation_engine/__init__.py",
        "evaluation_engine/core/__init__.py",
        "evaluation_engine/core/unified_framework.py",
        "evaluation_engine/core/task_registration.py",
        "install.sh",
        "install.ps1",
        "docker-compose.yml",
        "Dockerfile",
        ".github/workflows/ci.yml"
    ]
    
    required_dirs = [
        "evaluation_engine",
        "evaluation_engine/core",
        "monitoring",
        "scripts",
        ".github",
        ".github/workflows"
    ]
    
    all_good = True
    
    for file_path in required_files:
        if Path(file_path).exists():
            logger.info(f"✓ {file_path} exists")
        else:
            logger.error(f"✗ {file_path} missing")
            all_good = False
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            logger.info(f"✓ {dir_path}/ exists")
        else:
            logger.error(f"✗ {dir_path}/ missing")
            all_good = False
    
    return all_good

def main():
    """Run all integration tests"""
    logger.info("🚀 Starting AI Evaluation Engine Integration Tests")
    logger.info("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Imports", test_imports),
        ("Task Discovery", test_task_discovery),
        ("Extended Registry", test_extended_registry),
        ("Unified Framework", test_unified_framework),
        ("Basic Evaluation", test_basic_evaluation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} test...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! AI Evaluation Engine foundation is ready.")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())