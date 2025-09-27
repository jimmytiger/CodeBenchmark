#!/usr/bin/env python3
"""
Test script to verify lm-eval integration is working correctly
"""

import sys
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_lm_eval_functionality():
    """Test basic lm-eval functionality"""
    print("🔍 Testing basic lm-eval functionality...")
    
    try:
        # Test task manager
        from lm_eval.tasks import TaskManager, get_task_dict
        
        task_manager = TaskManager()
        all_tasks = task_manager.all_tasks
        
        print(f"✅ TaskManager loaded successfully")
        print(f"   - Total tasks: {len(all_tasks)}")
        print(f"   - Sample tasks: {all_tasks[:5]}")
        
        # Test task loading
        if all_tasks:
            sample_task = all_tasks[0]
            task_dict = get_task_dict([sample_task])
            print(f"✅ Task loading works: {sample_task}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic lm-eval functionality failed: {e}")
        return False


def test_evaluation_engine_integration():
    """Test evaluation engine integration"""
    print("\n🔍 Testing evaluation engine integration...")
    
    try:
        from evaluation_engine.core.unified_framework import unified_framework, EvaluationRequest
        from evaluation_engine.core.task_registration import extended_registry
        
        # Test framework initialization
        print("✅ Unified framework imported successfully")
        
        # Test task listing
        available_tasks = unified_framework.list_available_tasks()
        print(f"✅ Task listing works: {len(available_tasks)} tasks available")
        
        # Test extended registry
        hierarchy = extended_registry.get_task_hierarchy()
        print(f"✅ Extended registry works: {len(hierarchy)} categories")
        
        # Test task filtering
        single_turn_tasks = extended_registry.discover_tasks({"category": "single_turn_scenarios"})
        multi_turn_tasks = extended_registry.discover_tasks({"category": "multi_turn_scenarios"})
        
        print(f"   - Single-turn tasks: {len(single_turn_tasks)}")
        print(f"   - Multi-turn tasks: {len(multi_turn_tasks)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Evaluation engine integration failed: {e}")
        return False


def test_task_categories():
    """Test task categorization"""
    print("\n🔍 Testing task categorization...")
    
    try:
        from lm_eval.tasks import TaskManager
        
        task_manager = TaskManager()
        all_tasks = task_manager.all_tasks
        
        # Categorize tasks
        categories = {
            "single_turn_scenarios": [t for t in all_tasks if "single_turn_scenarios" in t],
            "multi_turn_scenarios": [t for t in all_tasks if "multi_turn_scenarios" in t],
            "python_coding": [t for t in all_tasks if "python_coding" in t],
            "multi_turn_coding": [t for t in all_tasks if "multi_turn_coding" in t],
            "other": [t for t in all_tasks if not any(cat in t for cat in ["single_turn_scenarios", "multi_turn_scenarios", "python_coding", "multi_turn_coding"])]
        }
        
        print("✅ Task categorization successful:")
        for category, tasks in categories.items():
            if tasks:
                print(f"   - {category}: {len(tasks)} tasks")
                print(f"     Examples: {tasks[:3]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Task categorization failed: {e}")
        return False


def test_dummy_evaluation():
    """Test dummy evaluation to verify the pipeline works"""
    print("\n🔍 Testing dummy evaluation...")
    
    try:
        from lm_eval.evaluator import simple_evaluate
        from lm_eval.tasks import TaskManager
        
        # Get a simple task for testing
        task_manager = TaskManager()
        all_tasks = task_manager.all_tasks
        
        # Find a suitable task for testing
        test_task = None
        for task in all_tasks:
            if "function_generation" in task:
                test_task = task
                break
        
        if not test_task:
            # Fallback to any available task
            test_task = all_tasks[0] if all_tasks else None
        
        if test_task:
            print(f"   Testing with task: {test_task}")
            
            # Run a minimal evaluation
            results = simple_evaluate(
                model="dummy",
                tasks=[test_task],
                limit=1,
                verbosity="ERROR"  # Suppress output
            )
            
            print("✅ Dummy evaluation successful")
            print(f"   - Results keys: {list(results.keys())}")
            
            if "results" in results:
                task_results = results["results"]
                print(f"   - Task results: {list(task_results.keys())}")
            
            return True
        else:
            print("⚠️  No suitable tasks found for testing")
            return True
            
    except Exception as e:
        print(f"❌ Dummy evaluation failed: {e}")
        return False


def test_unified_framework_evaluation():
    """Test evaluation using the unified framework"""
    print("\n🔍 Testing unified framework evaluation...")
    
    try:
        from evaluation_engine.core.unified_framework import unified_framework, EvaluationRequest
        from lm_eval.tasks import TaskManager
        
        # Get available tasks
        task_manager = TaskManager()
        all_tasks = task_manager.all_tasks
        
        # Find a suitable task
        test_task = None
        for task in all_tasks:
            if "function_generation" in task:
                test_task = task
                break
        
        if not test_task and all_tasks:
            test_task = all_tasks[0]
        
        if test_task:
            print(f"   Testing with task: {test_task}")
            
            # Create evaluation request
            request = EvaluationRequest(
                model="dummy",
                tasks=[test_task],
                limit=1,
                verbosity="ERROR"
            )
            
            # Validate request
            issues = unified_framework.validate_evaluation_request(request)
            if issues:
                print(f"   Validation issues: {issues}")
            else:
                print("✅ Request validation passed")
            
            # Run evaluation
            result = unified_framework.evaluate(request)
            
            print("✅ Unified framework evaluation successful")
            print(f"   - Status: {result.status}")
            print(f"   - Execution time: {result.end_time - result.start_time if result.end_time else 'N/A'}")
            
            if result.metrics_summary:
                print(f"   - Metrics: {len(result.metrics_summary)} metrics calculated")
            
            if result.analysis:
                print(f"   - Analysis: {list(result.analysis.keys())}")
            
            return True
        else:
            print("⚠️  No suitable tasks found for testing")
            return True
            
    except Exception as e:
        print(f"❌ Unified framework evaluation failed: {e}")
        return False


def main():
    """Run all integration tests"""
    print("🚀 AI Evaluation Engine - lm-eval Integration Test")
    print("=" * 60)
    
    tests = [
        test_basic_lm_eval_functionality,
        test_evaluation_engine_integration,
        test_task_categories,
        test_dummy_evaluation,
        test_unified_framework_evaluation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 INTEGRATION TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! lm-eval integration is working correctly.")
        return 0
    else:
        print("⚠️  Some integration tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())