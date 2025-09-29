"""
Tests for backward compatibility layer.

This module tests the compatibility wrappers, configuration adapters,
and bridge classes to ensure existing evaluation workflows continue to work.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import pytest
import json
import tempfile
import warnings
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from ..core.compatibility import (
    ConfigurationAdapter,
    LegacyEvaluationBridge,
    DeprecationManager,
    CompatibilityResult,
    simple_evaluate,
    load_config
)
from ..core.data_models import (
    EvaluationConfig, TaskConfig, ModelConfig, MultiTurnConfig,
    EvaluationResult, TurnResult, AggregatedMetrics
)


class TestConfigurationAdapter:
    """Test configuration format adaptation between legacy and new formats."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = ConfigurationAdapter()
        
        self.legacy_config = {
            'model': 'hf',
            'model_args': {'pretrained': 'gpt2', 'device': 'cpu'},
            'tasks': 'hellaswag,arc_easy',
            'num_fewshot': 5,
            'batch_size': 8,
            'output_path': './results',
            'log_samples': True,
            'use_cache': False,
            'device': 'cpu',
            'limit': 100
        }
        
        self.new_config_dict = {
            'models': {
                'default': {
                    'model_id': 'hf',
                    'model_type': 'auto',
                    'parameters': {'pretrained': 'gpt2', 'device': 'cpu'},
                    'device': 'cpu'
                }
            },
            'tasks': [
                {
                    'task_id': 'hellaswag',
                    'task_type': 'single_turn',
                    'model_ref': 'default',
                    'parameters': {'num_fewshot': 5, 'batch_size': 8}
                },
                {
                    'task_id': 'arc_easy',
                    'task_type': 'single_turn',
                    'model_ref': 'default',
                    'parameters': {'num_fewshot': 5, 'batch_size': 8}
                }
            ],
            'evaluation_settings': {
                'output_directory': './results',
                'save_samples': True,
                'enable_caching': False,
                'sample_limit': 100
            }
        }
    
    def test_adapt_legacy_config_basic(self):
        """Test basic legacy configuration adaptation."""
        result = self.adapter.adapt_legacy_config(self.legacy_config)
        
        assert isinstance(result, EvaluationConfig)
        assert len(result.models) == 1
        assert 'default' in result.models
        assert result.models['default'].model_id == 'hf'
        assert len(result.tasks) == 2
        assert result.tasks[0].task_id == 'hellaswag'
        assert result.tasks[1].task_id == 'arc_easy'
    
    def test_adapt_legacy_config_model_args(self):
        """Test model arguments adaptation."""
        result = self.adapter.adapt_legacy_config(self.legacy_config)
        
        model = result.models['default']
        assert model.parameters['pretrained'] == 'gpt2'
        assert model.parameters['device'] == 'cpu'
        assert model.device == 'cpu'
    
    def test_adapt_legacy_config_tasks_string(self):
        """Test task list as string adaptation."""
        config = self.legacy_config.copy()
        config['tasks'] = 'hellaswag,arc_easy,winogrande'
        
        result = self.adapter.adapt_legacy_config(config)
        
        assert len(result.tasks) == 3
        task_ids = [task.task_id for task in result.tasks]
        assert 'hellaswag' in task_ids
        assert 'arc_easy' in task_ids
        assert 'winogrande' in task_ids
    
    def test_adapt_legacy_config_tasks_list(self):
        """Test task list as list adaptation."""
        config = self.legacy_config.copy()
        config['tasks'] = ['hellaswag', 'arc_easy']
        
        result = self.adapter.adapt_legacy_config(config)
        
        assert len(result.tasks) == 2
        assert result.tasks[0].task_id == 'hellaswag'
        assert result.tasks[1].task_id == 'arc_easy'
    
    def test_adapt_legacy_config_missing_fields(self):
        """Test adaptation with missing fields."""
        minimal_config = {
            'model': 'hf',
            'tasks': 'hellaswag'
        }
        
        result = self.adapter.adapt_legacy_config(minimal_config)
        
        assert isinstance(result, EvaluationConfig)
        assert len(result.models) == 1
        assert len(result.tasks) == 1
        assert result.tasks[0].parameters.get('num_fewshot', 0) == 0
    
    def test_adapt_legacy_config_invalid(self):
        """Test adaptation with invalid configuration."""
        invalid_config = {}
        
        # Empty config should create a minimal valid config
        result = self.adapter.adapt_legacy_config(invalid_config)
        assert isinstance(result, EvaluationConfig)
        
        # But validation should fail
        with pytest.raises(ValueError):
            result.validate()
    
    def test_adapt_new_to_legacy_basic(self):
        """Test new to legacy configuration adaptation."""
        # Create new config object
        model_config = ModelConfig(
            model_id='hf',
            model_type='huggingface',
            parameters={'pretrained': 'gpt2'},
            device='cpu'
        )
        
        task_configs = [
            TaskConfig(
                task_id='hellaswag',
                task_type='single_turn',
                model_ref='default',
                parameters={'num_fewshot': 5, 'batch_size': 8}
            )
        ]
        
        new_config = EvaluationConfig(
            models={'default': model_config},
            tasks=task_configs,
            evaluation_settings={
                'output_directory': './results',
                'save_samples': True
            }
        )
        
        result = self.adapter.adapt_new_to_legacy(new_config)
        
        assert result['model'] == 'huggingface'
        assert result['tasks'] == 'hellaswag'
        assert result['num_fewshot'] == 5
        assert result['batch_size'] == 8
        assert result['output_path'] == './results'
        assert result['log_samples'] is True
    
    def test_adapt_new_to_legacy_multiple_tasks(self):
        """Test new to legacy with multiple tasks."""
        model_config = ModelConfig(
            model_id='gpt-4',
            model_type='openai',
            parameters={}
        )
        
        task_configs = [
            TaskConfig(
                task_id='hellaswag',
                task_type='single_turn',
                model_ref='default',
                parameters={'num_fewshot': 3}
            ),
            TaskConfig(
                task_id='arc_easy',
                task_type='single_turn',
                model_ref='default',
                parameters={'num_fewshot': 5}
            )
        ]
        
        new_config = EvaluationConfig(
            models={'default': model_config},
            tasks=task_configs
        )
        
        result = self.adapter.adapt_new_to_legacy(new_config)
        
        assert result['tasks'] == 'hellaswag,arc_easy'
        assert result['num_fewshot'] == 3  # Uses first task's parameters


class TestLegacyEvaluationBridge:
    """Test the legacy evaluation bridge functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.bridge = LegacyEvaluationBridge()
    
    def test_initialization(self):
        """Test bridge initialization."""
        assert self.bridge.config_adapter is not None
        assert isinstance(self.bridge.config_adapter, ConfigurationAdapter)
    
    def test_detect_multi_turn_tasks_single_turn(self):
        """Test detection of single-turn tasks."""
        single_turn_tasks = ['hellaswag', 'arc_easy', 'winogrande']
        
        for task in single_turn_tasks:
            assert not self.bridge._detect_multi_turn_tasks(task)
        
        assert not self.bridge._detect_multi_turn_tasks(single_turn_tasks)
    
    def test_detect_multi_turn_tasks_multi_turn(self):
        """Test detection of multi-turn tasks."""
        multi_turn_tasks = [
            'multi_turn_coding',
            'swe_bench_lite',
            'intercode_python',
            'convcode_bench',
            'bugs_in_py',
            'defects4j'
        ]
        
        for task in multi_turn_tasks:
            assert self.bridge._detect_multi_turn_tasks(task)
        
        assert self.bridge._detect_multi_turn_tasks(multi_turn_tasks)
    
    def test_detect_multi_turn_tasks_mixed(self):
        """Test detection with mixed task types."""
        mixed_tasks = ['hellaswag', 'swe_bench_lite', 'arc_easy']
        
        assert self.bridge._detect_multi_turn_tasks(mixed_tasks)
    
    def test_convert_to_lm_eval_args(self):
        """Test conversion to lm-eval arguments."""
        config = {
            'model': 'hf',
            'tasks': 'hellaswag',
            'model_args': {'pretrained': 'gpt2'},
            'num_fewshot': 5,
            'batch_size': 8,
            'device': 'cpu',
            'output_path': './results',
            'limit': 100,
            'use_cache': False,
            'log_samples': True
        }
        
        result = self.bridge._convert_to_lm_eval_args(config)
        
        assert result['model'] == 'hf'
        assert result['tasks'] == 'hellaswag'
        assert result['model_args'] == {'pretrained': 'gpt2'}
        assert result['num_fewshot'] == 5
        assert result['batch_size'] == 8
        assert result['device'] == 'cpu'
        assert result['output_path'] == './results'
        assert result['limit'] == 100
        assert result['use_cache'] is False
        assert result['log_samples'] is True
    
    def test_convert_results_to_legacy_format(self):
        """Test conversion of new results to legacy format."""
        # Create mock evaluation results
        metrics = AggregatedMetrics(
            resolved_percentage=0.85,
            recall=0.80,
            mrr=0.75,
            avg_turns=3.2,
            avg_steps=8.5,
            redundancy_rate=0.15,
            edit_churn=2.3,
            files_touched=4,
            recovery_rate=0.90,
            stability_score=0.88,
            wall_time_per_solved=45.2,
            tokens_per_solved=1250,
            cost_per_solved=0.025,
            safety_incidents=0,
            policy_violations=0
        )
        
        result = EvaluationResult(
            evaluation_id='test_eval_1',
            task_id='swe_bench_lite',
            model_id='gpt-4',
            success=True,
            total_turns=3,
            turn_results=[],
            aggregated_metrics=metrics,
            metadata={}
        )
        
        legacy_results = self.bridge._convert_results_to_legacy_format([result])
        
        assert 'results' in legacy_results
        assert 'swe_bench_lite' in legacy_results['results']
        
        task_results = legacy_results['results']['swe_bench_lite']
        assert task_results['acc'] == 0.85
        assert task_results['turns'] == 3.2
        assert task_results['steps'] == 8.5
        assert task_results['cost'] == 0.025
        assert task_results['wall_time'] == 45.2
        
        assert 'configs' in legacy_results
        assert 'swe_bench_lite' in legacy_results['configs']
        
        config = legacy_results['configs']['swe_bench_lite']
        assert config['task'] == 'swe_bench_lite'
        assert config['group'] == 'multi_turn'
        assert 'acc' in config['metric_list']
    
    @patch('EvaluationEngineV1_0.core.compatibility.evaluator')
    def test_evaluate_single_turn_with_lm_eval(self, mock_evaluator):
        """Test single-turn evaluation using lm-eval."""
        # Mock lm-eval evaluator
        mock_evaluator.simple_evaluate = Mock(return_value={
            'results': {'hellaswag': {'acc': 0.75}},
            'configs': {'hellaswag': {'task': 'hellaswag'}}
        })
        
        config = {
            'model': 'hf',
            'tasks': 'hellaswag',
            'model_args': {'pretrained': 'gpt2'}
        }
        
        result = self.bridge._evaluate_single_turn(config)
        
        assert result is not None
        assert 'results' in result
        assert 'hellaswag' in result['results']
        assert result['_compatibility']['evaluation_method'] == 'lm_eval'
        assert result['_compatibility']['multi_turn'] is False
        
        mock_evaluator.simple_evaluate.assert_called_once()
    
    def test_evaluate_single_turn_no_backend(self):
        """Test single-turn evaluation with no available backend."""
        with patch('EvaluationEngineV1_0.core.compatibility.evaluator', None):
            with patch.object(self.bridge, '_legacy_framework', None):
                config = {'model': 'hf', 'tasks': 'hellaswag'}
                
                with pytest.raises(RuntimeError, match="No evaluation backend available"):
                    self.bridge._evaluate_single_turn(config)
    
    def test_evaluate_with_deprecated_features(self):
        """Test evaluation with deprecated features."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            result = self.bridge.evaluate(
                model='hf',
                tasks='hellaswag',
                write_out=True,
                check_integrity=True,
                predict_only=True
            )
            
            assert len(result.deprecated_features) == 3
            assert any("write_out" in feature for feature in result.deprecated_features)
            assert any("check_integrity" in feature for feature in result.deprecated_features)
            assert any("predict_only" in feature for feature in result.deprecated_features)
            
            assert len(result.warnings) >= 3


class TestDeprecationManager:
    """Test deprecation warning and migration guidance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = DeprecationManager()
    
    def test_warn_deprecated_known_feature(self):
        """Test deprecation warning for known feature."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            self.manager.warn_deprecated('write_out')
            
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert 'write_out' in str(w[0].message)
            assert 'deprecated' in str(w[0].message)
    
    def test_warn_deprecated_unknown_feature(self):
        """Test deprecation warning for unknown feature."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            self.manager.warn_deprecated('unknown_feature')
            
            assert len(w) == 0  # No warning for unknown features
    
    def test_get_migration_guide_known_feature(self):
        """Test migration guide for known feature."""
        guide = self.manager.get_migration_guide('write_out')
        
        assert guide is not None
        assert 'write_out' in guide
        assert 'log_samples' in guide
        assert 'Replace' in guide
    
    def test_get_migration_guide_unknown_feature(self):
        """Test migration guide for unknown feature."""
        guide = self.manager.get_migration_guide('unknown_feature')
        
        assert guide is None


class TestCompatibilityFunctions:
    """Test top-level compatibility functions."""
    
    @patch('EvaluationEngineV1_0.core.compatibility.LegacyEvaluationBridge')
    def test_simple_evaluate_success(self, mock_bridge_class):
        """Test simple_evaluate function success case."""
        # Mock bridge instance
        mock_bridge = Mock()
        mock_bridge_class.return_value = mock_bridge
        
        # Mock successful evaluation
        mock_result = CompatibilityResult(
            success=True,
            result={'results': {'hellaswag': {'acc': 0.75}}},
            warnings=[],
            migration_notes=['Used legacy evaluation'],
            deprecated_features=[]
        )
        mock_bridge.evaluate.return_value = mock_result
        
        result = simple_evaluate(
            model='hf',
            tasks='hellaswag',
            model_args={'pretrained': 'gpt2'}
        )
        
        assert result is not None
        assert 'results' in result
        assert 'hellaswag' in result['results']
        
        mock_bridge.evaluate.assert_called_once_with(
            'hf', 'hellaswag', {'pretrained': 'gpt2'}
        )
    
    @patch('EvaluationEngineV1_0.core.compatibility.LegacyEvaluationBridge')
    def test_simple_evaluate_failure(self, mock_bridge_class):
        """Test simple_evaluate function failure case."""
        # Mock bridge instance
        mock_bridge = Mock()
        mock_bridge_class.return_value = mock_bridge
        
        # Mock failed evaluation
        mock_result = CompatibilityResult(
            success=False,
            result=None,
            warnings=['Evaluation failed: Test error'],
            migration_notes=[],
            deprecated_features=[]
        )
        mock_bridge.evaluate.return_value = mock_result
        
        with pytest.raises(RuntimeError, match="Evaluation failed"):
            simple_evaluate(model='hf', tasks='hellaswag')
    
    @patch('EvaluationEngineV1_0.core.compatibility.LegacyEvaluationBridge')
    def test_simple_evaluate_with_warnings(self, mock_bridge_class):
        """Test simple_evaluate function with warnings."""
        # Mock bridge instance
        mock_bridge = Mock()
        mock_bridge_class.return_value = mock_bridge
        
        # Mock evaluation with warnings
        mock_result = CompatibilityResult(
            success=True,
            result={'results': {'hellaswag': {'acc': 0.75}}},
            warnings=['Feature deprecated'],
            migration_notes=[],
            deprecated_features=[]
        )
        mock_bridge.evaluate.return_value = mock_result
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            result = simple_evaluate(model='hf', tasks='hellaswag')
            
            assert len(w) == 1
            assert 'Feature deprecated' in str(w[0].message)
    
    def test_load_config_yaml(self):
        """Test loading YAML configuration file."""
        config_data = {
            'model': 'hf',
            'tasks': 'hellaswag',
            'model_args': {'pretrained': 'gpt2'},
            'num_fewshot': 5
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            result = load_config(config_path)
            
            # Should be adapted to new format
            assert 'models' in result
            assert 'tasks' in result
            assert isinstance(result['tasks'], list)
            
        finally:
            Path(config_path).unlink()
    
    def test_load_config_json(self):
        """Test loading JSON configuration file."""
        config_data = {
            'model': 'hf',
            'tasks': 'hellaswag',
            'model_args': {'pretrained': 'gpt2'},
            'num_fewshot': 5
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            result = load_config(config_path)
            
            # Should be adapted to new format
            assert 'models' in result
            assert 'tasks' in result
            
        finally:
            Path(config_path).unlink()
    
    def test_load_config_new_format(self):
        """Test loading configuration in new format."""
        config_data = {
            'models': {
                'default': {
                    'model_id': 'gpt-4',
                    'model_type': 'openai',
                    'parameters': {}
                }
            },
            'tasks': [
                {
                    'task_id': 'swe_bench_lite',
                    'task_type': 'multi_turn',
                    'model_ref': 'default'
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            result = load_config(config_path)
            
            # Should remain in new format
            assert result == config_data
            
        finally:
            Path(config_path).unlink()
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            load_config('/nonexistent/config.yaml')
    
    def test_load_config_unsupported_format(self):
        """Test loading configuration with unsupported format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('model: hf\ntasks: hellaswag')
            config_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported configuration format"):
                load_config(config_path)
                
        finally:
            Path(config_path).unlink()


class TestCompatibilityIntegration:
    """Integration tests for backward compatibility."""
    
    def test_end_to_end_legacy_workflow(self):
        """Test complete legacy evaluation workflow."""
        # This would test a complete workflow from legacy config to results
        # For now, we'll test the key components work together
        
        adapter = ConfigurationAdapter()
        bridge = LegacyEvaluationBridge()
        
        legacy_config = {
            'model': 'hf',
            'tasks': 'hellaswag',
            'model_args': {'pretrained': 'gpt2'},
            'num_fewshot': 5
        }
        
        # Test configuration adaptation
        new_config = adapter.adapt_legacy_config(legacy_config)
        assert isinstance(new_config, EvaluationConfig)
        
        # Test back-conversion
        back_converted = adapter.adapt_new_to_legacy(new_config)
        assert back_converted['model'] == 'auto'  # Adapted model type
        assert back_converted['tasks'] == 'hellaswag'
        assert back_converted['num_fewshot'] == 5
    
    def test_multi_turn_detection_and_routing(self):
        """Test that multi-turn tasks are properly detected and routed."""
        bridge = LegacyEvaluationBridge()
        
        # Test single-turn detection
        assert not bridge._detect_multi_turn_tasks('hellaswag')
        assert not bridge._detect_multi_turn_tasks(['hellaswag', 'arc_easy'])
        
        # Test multi-turn detection
        assert bridge._detect_multi_turn_tasks('swe_bench_lite')
        assert bridge._detect_multi_turn_tasks(['hellaswag', 'swe_bench_lite'])
        assert bridge._detect_multi_turn_tasks('multi_turn_coding')
    
    def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms."""
        bridge = LegacyEvaluationBridge()
        
        # Test with invalid configuration
        result = bridge.evaluate(
            model='',  # Invalid model
            tasks=''   # Invalid tasks
        )
        
        assert not result.success
        assert len(result.warnings) > 0
        assert result.result is None


if __name__ == '__main__':
    pytest.main([__file__])