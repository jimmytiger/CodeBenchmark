#!/usr/bin/env python3
"""Simple test script for single_turn_scenarios tasks."""

import sys
import os
sys.path.append('.')

from lm_eval import evaluator
from lm_eval.tasks import TaskManager

def test_task_loading():
    """Test if single_turn_scenarios tasks can be loaded."""
    print("Testing task loading...")
    
    try:
        task_manager = TaskManager()
        
        # List all single_turn_scenarios tasks
        all_tasks = task_manager.all_tasks
        single_turn_tasks = [name for name in all_tasks if 'single_turn_scenarios' in name]
        
        print(f"Found {len(single_turn_tasks)} single_turn_scenarios tasks:")
        for task in sorted(single_turn_tasks):
            print(f"  - {task}")
        
        # Try to load a simple task
        print("\nTrying to load single_turn_scenarios_function_generation...")
        task_dict = task_manager.load_task_or_group("single_turn_scenarios_function_generation")
        print(f"Task loaded successfully: {list(task_dict.keys())}")
        
        return True
        
    except Exception as e:
        print(f"Error loading tasks: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dataset_loading():
    """Test if the dataset can be loaded directly."""
    print("\nTesting dataset loading...")
    
    try:
        sys.path.append('lm_eval/tasks/single_turn_scenarios')
        from utils import load_dataset
        
        # Test loading with function_generation filter
        dataset_dict = load_dataset({'scenario': 'function_generation'})
        dataset = dataset_dict['test']
        print(f"Dataset loaded: {len(dataset)} items")
        
        if len(dataset) > 0:
            print(f"First item keys: {list(dataset[0].keys())}")
            print(f"First item ID: {dataset[0]['id']}")
            print(f"First item scenario: {dataset[0]['scenario']}")
        
        return True
        
    except Exception as e:
        print(f"Error loading dataset: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing Single Turn Scenarios")
    print("=" * 50)
    
    success = True
    
    # Test dataset loading first
    if not test_dataset_loading():
        success = False
    
    # Test task loading
    if not test_task_loading():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    sys.exit(0 if success else 1)