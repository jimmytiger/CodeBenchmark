#!/usr/bin/env python3
"""
Test script for Task 2 implementation: lm-eval Compatible Data Models and Task Structure

This script tests the implementation of:
- Task directory structure
- Extended data structures
- Plugin system and interfaces
- Backward compatibility
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_directory_structure():
    """Test that the task directory structure is properly created."""
    print("Testing directory structure...")
    
    # Check single-turn scenario directories
    single_turn_base = Path("lm_eval/tasks/single_turn_scenarios")
    expected_single_turn = [
        "code_completion", "bug_fix", "function_generation", "code_translation",
        "algorithm_implementation", "api_design", "system_design", "database_design",
        "security_implementation", "performance_optimization", "documentation_generation",
        "testing_strategy", "full_stack_development"
    ]
    
    for scenario in expected_single_turn:
        scenario_dir = single_turn_base / scenario
        init_file = scenario_dir / "__init__.py"
        config_file = scenario_dir / "config.yml"
        
        assert scenario_dir.exists(), f"Missing directory: {scenario_dir}"
        assert init_file.exists(), f"Missing __init__.py: {init_file}"
        
        if scenario in ["code_completion", "bug_fix", "algorithm_implementation"]:
            assert config_file.exists(), f"Missing config.yml: {config_file}"
    
    # Check multi-turn scenario directories
    multi_turn_base = Path("lm_eval/tasks/multi_turn_scenarios")
    expected_multi_turn = [
        "code_review_process", "debugging_session", "design_iteration", "teaching_dialogue",
        "collaborative_development", "requirements_refinement", "architecture_discussion",
        "performance_tuning"
    ]
    
    for scenario in expected_multi_turn:
        scenario_dir = multi_turn_base / scenario
        init_file = scenario_dir / "__init__.py"
        
        assert scenario_dir.exists(), f"Missing directory: {scenario_dir}"
        assert init_file.exists(), f"Missing __init__.py: {init_file}"
    
    # Check quantitative trading subdirectories
    quant_base = multi_turn_base / "quantitative_trading"
    expected_quant = [
        "strategy_development", "multifactor_model_construction", "market_research_analysis",
        "portfolio_risk_assessment", "execution_algorithm_optimization", "high_frequency_trading",
        "fundamental_quant_analysis", "technical_quant_analysis"
    ]
    
    for scenario in expected_quant:
        scenario_dir = quant_base / scenario
        init_file = scenario_dir / "__init__.py"
        
        assert scenario_dir.exists(), f"Missing directory: {scenario_dir}"
        assert init_file.exists(), f"Missing __init__.py: {init_file}"
    
    print("✓ Directory structure test passed")

def test_dataset_formats():
    """Test dataset format loading and validation."""
    print("Testing dataset formats...")
    
    try:
        from evaluation_engine.core.dataset_formats import (
            SingleTurnProblem, MultiTurnScenario, DatasetLoader, TestCase, TurnData
        )
        
        # Test SingleTurnProblem creation
        test_case = TestCase(input=5, expected=120, description="Test factorial")
        problem = SingleTurnProblem(
            id="test_001",
            scenario="code_completion",
            difficulty="simple",
            language="python",
            context_mode="minimal_context",
            problem="Complete the factorial function",
            test_cases=[test_case]
        )
        
        # Test serialization
        problem_dict = problem.to_dict()
        assert problem_dict['id'] == "test_001"
        assert len(problem_dict['test_cases']) == 1
        
        # Test deserialization
        reconstructed = SingleTurnProblem.from_dict(problem_dict)
        assert reconstructed.id == problem.id
        assert reconstructed.scenario == problem.scenario
        
        # Test MultiTurnScenario creation
        turn_data = TurnData(
            turn_id="initial_review",
            turn_type="review",
            role="reviewer"
        )
        scenario = MultiTurnScenario(
            id="review_001",
            scenario="code_review_process",
            difficulty="intermediate",
            turns=[turn_data]
        )
        
        scenario_dict = scenario.to_dict()
        assert scenario_dict['id'] == "review_001"
        assert len(scenario_dict['turns']) == 1
        
        print("✓ Dataset formats test passed")
        
    except ImportError as e:
        print(f"✗ Dataset formats test failed: {e}")
        return False
    
    return True

def test_extended_tasks():
    """Test extended task classes."""
    print("Testing extended task classes...")
    
    try:
        from evaluation_engine.core.extended_tasks import (
            AdvancedTask, MultiTurnTask, ExtendedTaskConfig, ScenarioConfig,
            TurnConfig, ScenarioType, ContextMode, DifficultyLevel
        )
        
        # Test configuration classes
        turn_config = TurnConfig(
            turn_id="test_turn",
            turn_type="review",
            role="reviewer",
            prompt_template="Test prompt",
            expected_format="structured"
        )
        
        scenario_config = ScenarioConfig(
            scenario_id="test_scenario",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=3,
            turns=[turn_config]
        )
        
        extended_config = ExtendedTaskConfig(
            task="test_task",
            scenario_config=scenario_config,
            context_mode=ContextMode.FULL_CONTEXT,
            difficulty_level=DifficultyLevel.INTERMEDIATE
        )
        
        # Test serialization
        config_dict = extended_config.to_dict()
        assert config_dict['task'] == "test_task"
        assert config_dict['context_mode'] == "full_context"
        
        print("✓ Extended tasks test passed")
        
    except ImportError as e:
        print(f"✗ Extended tasks test failed: {e}")
        return False
    
    return True

def test_model_adapters():
    """Test model adapter system."""
    print("Testing model adapter system...")
    
    try:
        from evaluation_engine.core.model_adapters import (
            ModelAdapter, ModelType, ModelCapabilities, RateLimitConfig,
            plugin_registry, register_model_adapter
        )
        
        # Test configuration classes
        capabilities = ModelCapabilities(
            max_context_length=8192,
            max_output_length=4096,
            supports_chat_templates=True
        )
        
        rate_config = RateLimitConfig(
            requests_per_minute=100,
            tokens_per_minute=50000
        )
        
        # Test serialization
        cap_dict = capabilities.to_dict()
        assert cap_dict['max_context_length'] == 8192
        
        rate_dict = rate_config.to_dict()
        assert rate_dict['requests_per_minute'] == 100
        
        print("✓ Model adapters test passed")
        
    except ImportError as e:
        print(f"✗ Model adapters test failed: {e}")
        return False
    
    return True

def test_plugin_system():
    """Test plugin system."""
    print("Testing plugin system...")
    
    try:
        from evaluation_engine.core.plugin_system import (
            PluginManager, PluginInterface, PluginType, PluginMetadata,
            ModelAdapterPlugin, TaskPlugin, MetricPlugin
        )
        
        # Test plugin metadata
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            plugin_type=PluginType.MODEL_ADAPTER
        )
        
        metadata_dict = metadata.to_dict()
        assert metadata_dict['name'] == "test_plugin"
        assert metadata_dict['plugin_type'] == "model_adapter"
        
        # Test plugin manager
        manager = PluginManager()
        discovered = manager.discover_plugins()
        # Should return empty list since no plugins are installed yet
        assert isinstance(discovered, list)
        
        print("✓ Plugin system test passed")
        
    except ImportError as e:
        print(f"✗ Plugin system test failed: {e}")
        return False
    
    return True

def test_compatibility_layer():
    """Test backward compatibility layer."""
    print("Testing compatibility layer...")
    
    try:
        from evaluation_engine.core.compatibility import (
            CompatibilityManager, LegacyTaskWrapper, LegacyModelWrapper,
            compatibility_manager
        )
        
        # Test compatibility manager
        manager = CompatibilityManager()
        
        # Test compatibility info
        info = manager.get_migration_guide("task")
        assert "Migration Guide for Tasks" in info
        
        print("✓ Compatibility layer test passed")
        
    except ImportError as e:
        print(f"✗ Compatibility layer test failed: {e}")
        return False
    
    return True

def test_sample_datasets():
    """Test sample dataset files."""
    print("Testing sample dataset files...")
    
    # Test single-turn problems.jsonl files
    single_turn_files = [
        "lm_eval/tasks/single_turn_scenarios/code_completion/problems.jsonl",
        "lm_eval/tasks/single_turn_scenarios/bug_fix/problems.jsonl"
    ]
    
    for file_path in single_turn_files:
        if Path(file_path).exists():
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        assert 'id' in data, f"Missing 'id' in {file_path}:{line_num}"
                        assert 'scenario' in data, f"Missing 'scenario' in {file_path}:{line_num}"
                        assert 'problem' in data, f"Missing 'problem' in {file_path}:{line_num}"
                    except json.JSONDecodeError as e:
                        print(f"✗ Invalid JSON in {file_path}:{line_num}: {e}")
                        return False
    
    # Test multi-turn scenarios.jsonl files
    multi_turn_files = [
        "lm_eval/tasks/multi_turn_scenarios/code_review_process/scenarios.jsonl",
        "lm_eval/tasks/multi_turn_scenarios/quantitative_trading/strategy_development/scenarios.jsonl"
    ]
    
    for file_path in multi_turn_files:
        if Path(file_path).exists():
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        assert 'id' in data, f"Missing 'id' in {file_path}:{line_num}"
                        assert 'scenario' in data, f"Missing 'scenario' in {file_path}:{line_num}"
                    except json.JSONDecodeError as e:
                        print(f"✗ Invalid JSON in {file_path}:{line_num}: {e}")
                        return False
    
    print("✓ Sample datasets test passed")
    return True

def main():
    """Run all tests."""
    print("Running Task 2 Implementation Tests")
    print("=" * 50)
    
    tests = [
        test_directory_structure,
        test_dataset_formats,
        test_extended_tasks,
        test_model_adapters,
        test_plugin_system,
        test_compatibility_layer,
        test_sample_datasets
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = test()
            if result is None or result is True:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Task 2 implementation is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())