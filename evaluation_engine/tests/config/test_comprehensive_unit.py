"""
Comprehensive unit tests for configuration-driven evaluation system.

This module provides comprehensive unit test coverage for all components,
including edge cases, boundary conditions, and error scenarios.
"""

import pytest
import tempfile
import json
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from evaluation_engine.config.parser import ConfigParser
from evaluation_engine.config.validator import ConfigValidator
from evaluation_engine.config.builder import TaskBuilder
from evaluation_engine.config.evaluator import ConfigDrivenEvaluator
from evaluation_engine.config.templates import ModelTemplateManager
from evaluation_engine.config.models import (
    EvaluationConfig, TaskConfig, ModelConfig, ConfigMetadata,
    DefaultConfig, OutputConfig, ValidationResult, ValidationError,
    ValidationSeverity
)


class TestConfigParserEdgeCases:
    """Test edge cases and boundary conditions for ConfigParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ConfigParser()
    
    def test_parse_extremely_large_config(self):
        """Test parsing very large configuration files."""
        # Create a config with many tasks and models
        large_config = {
            "metadata": {"name": "Large Config", "version": "1.0"},
            "models": {},
            "tasks": []
        }
        
        # Add 100 models
        for i in range(100):
            large_config["models"][f"model_{i}"] = {
                "name": f"model_{i}",
                "type": "openai",
                "model_name": f"gpt-3.5-turbo-{i}",
                "parameters": {"temperature": 0.7 + (i * 0.001)}
            }
        
        # Add 500 tasks
        for i in range(500):
            large_config["tasks"].append({
                "name": f"task_{i}",
                "model_ref": f"model_{i % 100}",
                "task_name": "hellaswag",
                "num_fewshot": i % 10,
                "batch_size": (i % 32) + 1
            })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(large_config, f)
            temp_path = f.name
        
        try:
            start_time = time.time()
            config = self.parser.parse_config(temp_path)
            parse_time = time.time() - start_time
            
            # Should parse within reasonable time (< 5 seconds)
            assert parse_time < 5.0
            assert len(config.models) == 100
            assert len(config.tasks) == 500
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_config_with_unicode_content(self):
        """Test parsing configuration with Unicode characters."""
        unicode_config = {
            "metadata": {
                "name": "测试配置",
                "version": "1.0",
                "author": "José María",
                "description": "Configuration with émojis 🚀 and special chars: αβγ"
            },
            "models": {
                "模型_1": {
                    "name": "模型_1",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "parameters": {"temperature": 0.7}
                }
            },
            "tasks": [{
                "name": "任务_1",
                "model_ref": "模型_1",
                "task_name": "hellaswag",
                "description": "Task with special chars: ñáéíóú"
            }]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(unicode_config, f, ensure_ascii=False)
            temp_path = f.name
        
        try:
            config = self.parser.parse_config(temp_path)
            
            assert config.metadata.name == "测试配置"
            assert config.metadata.author == "José María"
            assert "🚀" in config.metadata.description
            assert "模型_1" in config.models
            assert config.tasks[0].name == "任务_1"
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_config_with_deeply_nested_variables(self):
        """Test parsing configuration with deeply nested variable references."""
        nested_config = {
            "variables": {
                "level1": "base",
                "level2": "${level1}_extended",
                "level3": "${level2}_more",
                "level4": "${level3}_final",
                "complex": "${level4}_${level1}_${level2}"
            },
            "metadata": {"name": "Nested Variables Test"},
            "tasks": [{
                "name": "test_task",
                "model_ref": "test_model",
                "task_name": "hellaswag",
                "description": "${complex}"
            }]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(nested_config, f)
            temp_path = f.name
        
        try:
            config = self.parser.parse_config(temp_path)
            
            # Should resolve to: "base_extended_more_final_base_base_extended"
            expected = "base_extended_more_final_base_base_extended"
            assert config.tasks[0].description == expected
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_config_with_malformed_json(self):
        """Test parsing malformed JSON files."""
        malformed_configs = [
            '{"metadata": {"name": "test"}, "tasks": [}',  # Missing closing bracket
            '{"metadata": {"name": "test"} "tasks": []}',   # Missing comma
            '{"metadata": {"name": "test"}, "tasks": [,]}', # Extra comma
            '{"metadata": {"name": "test"}, "tasks": [{"name": "test",}]}', # Trailing comma
        ]
        
        for malformed_json in malformed_configs:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(malformed_json)
                temp_path = f.name
            
            try:
                result = self.parser.validate_syntax(temp_path)
                assert not result.is_valid
                assert len(result.errors) > 0
                assert any("syntax error" in error.message.lower() for error in result.errors)
                
            finally:
                os.unlink(temp_path)
    
    def test_parse_config_with_circular_includes(self):
        """Test detection of circular includes in configuration files."""
        # Create config A that includes config B
        config_a = {
            "metadata": {"name": "Config A"},
            "models": {"include": "config_b.json"},
            "tasks": [{"name": "task_a", "model_ref": "model_b", "task_name": "hellaswag"}]
        }
        
        # Create config B that includes config A (circular)
        config_b = {
            "model_b": {
                "name": "model_b",
                "type": "openai",
                "model_name": "gpt-3.5-turbo"
            },
            "extra_models": {"include": "config_a.json"}
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_a_path = os.path.join(temp_dir, "config_a.json")
            config_b_path = os.path.join(temp_dir, "config_b.json")
            
            with open(config_a_path, 'w') as f:
                json.dump(config_a, f)
            
            with open(config_b_path, 'w') as f:
                json.dump(config_b, f)
            
            # Should detect circular include
            with pytest.raises(ValueError, match="Circular include detected"):
                self.parser.parse_config(config_a_path)
    
    def test_parse_config_with_missing_include_files(self):
        """Test handling of missing include files."""
        config_with_missing_include = {
            "metadata": {"name": "Test Config"},
            "models": {"include": "nonexistent_models.json"},
            "tasks": [{"name": "task1", "model_ref": "model1", "task_name": "hellaswag"}]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_with_missing_include, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Include file not found"):
                self.parser.parse_config(temp_path)
                
        finally:
            os.unlink(temp_path)
    
    def test_parse_config_with_environment_variable_fallbacks(self):
        """Test environment variable resolution with fallbacks."""
        # Set some environment variables
        os.environ['TEST_MODEL_NAME'] = 'gpt-4'
        os.environ['TEST_TEMPERATURE'] = '0.8'
        
        try:
            config_with_env_vars = {
                "variables": {
                    "model_name": "${env:TEST_MODEL_NAME}",
                    "temperature": "${env:TEST_TEMPERATURE}",
                    "undefined_var": "${env:UNDEFINED_VAR:default_value}",  # With fallback
                    "batch_size": "${env:UNDEFINED_BATCH_SIZE:32}"  # Numeric fallback
                },
                "metadata": {"name": "Env Var Test"},
                "models": {
                    "test_model": {
                        "name": "test_model",
                        "type": "openai",
                        "model_name": "${model_name}",
                        "parameters": {"temperature": "${temperature}"}
                    }
                },
                "tasks": [{
                    "name": "test_task",
                    "model_ref": "test_model",
                    "task_name": "hellaswag",
                    "batch_size": "${batch_size}"
                }],
                "output": {
                    "directory": "${undefined_var}"
                }
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config_with_env_vars, f)
                temp_path = f.name
            
            try:
                config = self.parser.parse_config(temp_path)
                
                assert config.models["test_model"].model_name == "gpt-4"
                assert config.models["test_model"].parameters["temperature"] == "0.8"
                assert config.output.directory == "default_value"
                assert config.tasks[0].batch_size == "32"
                
            finally:
                os.unlink(temp_path)
                
        finally:
            # Clean up environment variables
            del os.environ['TEST_MODEL_NAME']
            del os.environ['TEST_TEMPERATURE']
    
    def test_parse_config_with_complex_template_inheritance(self):
        """Test complex template inheritance scenarios."""
        # Create base template
        base_template = {
            "metadata": {"name": "Base Template", "version": "1.0"},
            "defaults": {"num_fewshot": 5, "batch_size": 32},
            "models": {
                "base_model": {
                    "name": "base_model",
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "parameters": {"temperature": 0.7}
                }
            }
        }
        
        # Create intermediate template that extends base
        intermediate_template = {
            "extends": "base.json",
            "metadata": {"name": "Intermediate Template"},
            "defaults": {"num_fewshot": 10},  # Override
            "models": {
                "base_model": {
                    "parameters": {"temperature": 0.5, "max_tokens": 1000}  # Merge/override
                },
                "intermediate_model": {
                    "name": "intermediate_model",
                    "type": "anthropic",
                    "model_name": "claude-3-sonnet"
                }
            }
        }
        
        # Create final template that extends intermediate
        final_template = {
            "extends": "intermediate.json",
            "metadata": {"name": "Final Template", "author": "Test Author"},
            "tasks": [{
                "name": "final_task",
                "model_ref": "base_model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = os.path.join(temp_dir, "base.json")
            intermediate_path = os.path.join(temp_dir, "intermediate.json")
            final_path = os.path.join(temp_dir, "final.json")
            
            with open(base_path, 'w') as f:
                json.dump(base_template, f)
            
            with open(intermediate_path, 'w') as f:
                json.dump(intermediate_template, f)
            
            with open(final_path, 'w') as f:
                json.dump(final_template, f)
            
            config = self.parser.parse_config(final_path)
            
            # Check inheritance chain
            assert config.metadata.name == "Final Template"
            assert config.metadata.version == "1.0"  # From base
            assert config.metadata.author == "Test Author"  # From final
            
            # Check defaults merging
            assert config.defaults.num_fewshot == 10  # From intermediate
            assert config.defaults.batch_size == 32   # From base
            
            # Check model merging
            assert "base_model" in config.models
            assert "intermediate_model" in config.models
            assert config.models["base_model"].parameters["temperature"] == 0.5  # From intermediate
            assert config.models["base_model"].parameters["max_tokens"] == 1000  # From intermediate
            
            # Check tasks (only in final)
            assert len(config.tasks) == 1
            assert config.tasks[0].name == "final_task"


class TestConfigValidatorEdgeCases:
    """Test edge cases and boundary conditions for ConfigValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigValidator()
    
    def test_validate_config_with_extreme_parameter_values(self):
        """Test validation with extreme parameter values."""
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Extreme Values Test"),
            models={
                "extreme_model": ModelConfig(
                    name="extreme_model",
                    type="openai",
                    model_name="gpt-3.5-turbo",
                    parameters={
                        "temperature": 2.0,      # Maximum allowed
                        "max_tokens": 4096,      # Very high
                        "top_p": 1.0,           # Maximum
                        "frequency_penalty": 2.0, # Maximum
                        "presence_penalty": 2.0   # Maximum
                    }
                )
            },
            tasks=[
                TaskConfig(
                    name="extreme_task",
                    model_ref="extreme_model",
                    task_name="hellaswag",
                    num_fewshot=100,  # Very high
                    batch_size=1024,  # Very high
                    task_config={
                        "limit": 1000000,  # Very high
                        "temperature": 2.0
                    }
                )
            ]
        )
        
        result = self.validator.validate_config(config)
        
        # Should be valid but may have warnings
        assert result.is_valid
        # May have warnings about extreme values
        warning_messages = [w.message for w in result.warnings]
        assert any("high" in msg.lower() or "extreme" in msg.lower() for msg in warning_messages)
    
    def test_validate_config_with_invalid_parameter_types(self):
        """Test validation with invalid parameter types."""
        # Create config with wrong parameter types directly to bypass model validation
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Invalid Types Test"),
            models={
                "invalid_model": ModelConfig(
                    name="invalid_model",
                    type="openai",
                    model_name="gpt-3.5-turbo",
                    parameters={
                        "temperature": "not_a_number",  # Should be float
                        "max_tokens": "also_not_a_number",  # Should be int
                        "top_p": [1, 2, 3]  # Should be float
                    }
                )
            },
            tasks=[
                TaskConfig(
                    name="invalid_task",
                    model_ref="invalid_model",
                    task_name="hellaswag",
                    num_fewshot="not_an_int",  # Should be int
                    batch_size="also_not_an_int"  # Should be int
                )
            ]
        )
        
        result = self.validator.validate_config(config)
        
        assert not result.is_valid
        error_messages = [e.message for e in result.errors]
        assert any("type" in msg.lower() for msg in error_messages)
    
    def test_validate_config_with_complex_dependencies(self):
        """Test validation of complex task dependency graphs."""
        # Create a complex dependency graph
        tasks = []
        
        # Create 20 tasks with complex dependencies
        for i in range(20):
            depends_on = []
            if i > 0:
                depends_on.append(f"task_{i-1}")  # Linear dependency
            if i > 5:
                depends_on.append(f"task_{i-5}")  # Skip dependency
            if i % 3 == 0 and i > 0:
                depends_on.append("task_0")  # Common dependency
            
            tasks.append(TaskConfig(
                name=f"task_{i}",
                model_ref="test_model",
                task_name="hellaswag",
                depends_on=depends_on
            ))
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Complex Dependencies Test"),
            models={
                "test_model": ModelConfig(
                    name="test_model",
                    type="openai",
                    model_name="gpt-3.5-turbo"
                )
            },
            tasks=tasks
        )
        
        result = self.validator.validate_config(config)
        
        # Should be valid (no circular dependencies)
        assert result.is_valid
    
    def test_validate_config_with_many_model_types(self):
        """Test validation with many different model types."""
        models = {}
        tasks = []
        
        model_types = ["openai", "anthropic", "huggingface", "custom"]
        
        for i, model_type in enumerate(model_types):
            model_name = f"{model_type}_model_{i}"
            models[model_name] = ModelConfig(
                name=model_name,
                type=model_type,
                model_name=f"test-{model_type}-model",
                parameters={"temperature": 0.7}
            )
            
            tasks.append(TaskConfig(
                name=f"task_{i}",
                model_ref=model_name,
                task_name="hellaswag"
            ))
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Many Model Types Test"),
            models=models,
            tasks=tasks
        )
        
        result = self.validator.validate_config(config)
        
        # Should have errors for unsupported model types
        assert not result.is_valid
        error_messages = [e.message for e in result.errors]
        assert any("Unsupported model type: custom" in msg for msg in error_messages)
    
    def test_validate_config_performance_with_large_config(self):
        """Test validation performance with large configurations."""
        # Create a large configuration
        models = {}
        tasks = []
        
        # 50 models
        for i in range(50):
            models[f"model_{i}"] = ModelConfig(
                name=f"model_{i}",
                type="openai",
                model_name=f"gpt-3.5-turbo-{i}",
                parameters={"temperature": 0.7}
            )
        
        # 200 tasks with dependencies
        for i in range(200):
            depends_on = []
            if i > 0:
                depends_on.append(f"task_{i-1}")
            
            tasks.append(TaskConfig(
                name=f"task_{i}",
                model_ref=f"model_{i % 50}",
                task_name="hellaswag",
                depends_on=depends_on
            ))
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Large Config Performance Test"),
            models=models,
            tasks=tasks
        )
        
        start_time = time.time()
        result = self.validator.validate_config(config)
        validation_time = time.time() - start_time
        
        # Should validate within reasonable time (< 2 seconds)
        assert validation_time < 2.0
        assert result.is_valid


class TestTaskBuilderEdgeCases:
    """Test edge cases and boundary conditions for TaskBuilder."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.builder = TaskBuilder()
    
    def test_build_tasks_with_complex_parameter_merging(self):
        """Test task building with complex parameter merging scenarios."""
        model_config = ModelConfig(
            name="test_model",
            type="openai",
            model_name="gpt-3.5-turbo",
            parameters={
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 0.9
            }
        )
        
        task_config = TaskConfig(
            name="test_task",
            model_ref="test_model",
            task_name="hellaswag",
            task_config={
                "temperature": 0.5,  # Override model parameter
                "max_tokens": 2000,  # Override model parameter
                "limit": 100,        # Task-specific parameter
                "custom_param": "value"  # Custom parameter
            }
        )
        
        eval_config = EvaluationConfig(
            metadata=ConfigMetadata(name="Parameter Merging Test"),
            models={"test_model": model_config},
            tasks=[task_config]
        )
        
        framework_params = self.builder.convert_to_framework_format(
            task_config, model_config, eval_config
        )
        
        # Check parameter merging
        assert framework_params["gen_kwargs"]["temperature"] == 0.5  # Task override
        assert framework_params["gen_kwargs"]["max_tokens"] == 2000  # Task override
        assert framework_params["gen_kwargs"]["top_p"] == 0.9       # From model
        assert framework_params["limit"] == 100                     # Task-specific
        assert framework_params["custom_param"] == "value"          # Custom
    
    def test_resolve_dependencies_with_parallel_branches(self):
        """Test dependency resolution with parallel execution branches."""
        # Create a dependency graph with parallel branches
        #     task1
        #    /     \
        # task2   task3
        #    \     /
        #     task4
        
        task1 = TaskConfig(name="task1", model_ref="model1", task_name="task1", depends_on=[])
        task2 = TaskConfig(name="task2", model_ref="model1", task_name="task2", depends_on=["task1"])
        task3 = TaskConfig(name="task3", model_ref="model1", task_name="task3", depends_on=["task1"])
        task4 = TaskConfig(name="task4", model_ref="model1", task_name="task4", depends_on=["task2", "task3"])
        
        tasks = [task4, task2, task3, task1]  # Intentionally out of order
        resolved = self.builder.resolve_dependencies(tasks)
        
        # Check ordering
        assert resolved[0].name == "task1"
        # task2 and task3 can be in any order
        middle_tasks = {resolved[1].name, resolved[2].name}
        assert middle_tasks == {"task2", "task3"}
        assert resolved[3].name == "task4"
    
    def test_build_tasks_with_missing_model_references(self):
        """Test task building with missing model references."""
        task_config = TaskConfig(
            name="orphan_task",
            model_ref="nonexistent_model",
            task_name="hellaswag"
        )
        
        eval_config = EvaluationConfig(
            metadata=ConfigMetadata(name="Missing Model Test"),
            models={},  # No models defined
            tasks=[task_config]
        )
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            self.builder.build_tasks(eval_config)


class TestConfigDrivenEvaluatorEdgeCases:
    """Test edge cases and boundary conditions for ConfigDrivenEvaluator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = ConfigDrivenEvaluator()
    
    def test_run_from_config_with_execution_timeout(self):
        """Test evaluation with simulated execution timeout."""
        # Mock a framework that takes a long time
        mock_framework = Mock()
        
        def slow_evaluate(request):
            time.sleep(0.1)  # Simulate slow execution
            result = Mock()
            result.status = "completed"
            result.start_time = datetime.now()
            result.end_time = datetime.now()
            result.results = {"test": {"accuracy": 0.8}}
            result.metrics_summary = {"test_accuracy": 0.8}
            result.analysis = {"summary": "Success"}
            result.error = None
            return result
        
        mock_framework.evaluate.side_effect = slow_evaluate
        
        evaluator = ConfigDrivenEvaluator(framework=mock_framework)
        
        config = EvaluationConfig(
            metadata=ConfigMetadata(name="Timeout Test"),
            models={
                "test_model": ModelConfig(
                    name="test_model",
                    type="openai",
                    model_name="gpt-3.5-turbo"
                )
            },
            tasks=[
                TaskConfig(
                    name="test_task",
                    model_ref="test_model",
                    task_name="hellaswag"
                )
            ]
        )
        
        with patch.object(evaluator.parser, 'parse_config', return_value=config):
            with patch.object(evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run with timeout (should complete normally)
                    result = evaluator.run_from_config(config_path, execution_timeout=1.0)
                    
                    assert result.batch_result.completed_tasks == 1
                    assert result.batch_result.failed_tasks == 0
                    
                finally:
                    os.unlink(config_path)
    
    def test_run_from_config_with_memory_constraints(self):
        """Test evaluation under memory constraints."""
        # Create a config that might use significant memory
        large_config = EvaluationConfig(
            metadata=ConfigMetadata(name="Memory Test"),
            models={
                f"model_{i}": ModelConfig(
                    name=f"model_{i}",
                    type="openai",
                    model_name="gpt-3.5-turbo",
                    parameters={"temperature": 0.7}
                ) for i in range(10)
            },
            tasks=[
                TaskConfig(
                    name=f"task_{i}",
                    model_ref=f"model_{i % 10}",
                    task_name="hellaswag",
                    batch_size=1024  # Large batch size
                ) for i in range(50)
            ]
        )
        
        with patch.object(self.evaluator.parser, 'parse_config', return_value=large_config):
            with patch.object(self.evaluator.validator, 'validate_config', 
                            return_value=ValidationResult(is_valid=True)):
                
                # Create temporary config file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    f.write("test: config")
                    config_path = f.name
                
                try:
                    # Run in dry run mode to avoid actual execution
                    result = self.evaluator.run_from_config(config_path, dry_run=True)
                    
                    assert result.batch_result.total_tasks == 50
                    assert result.batch_result.skipped_tasks == 50
                    
                finally:
                    os.unlink(config_path)


class TestModelTemplateManagerEdgeCases:
    """Test edge cases and boundary conditions for ModelTemplateManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ModelTemplateManager()
    
    def test_apply_template_with_complex_formatting(self):
        """Test template application with complex formatting scenarios."""
        complex_template = """
System: {system_prompt}

Previous conversation:
{conversation_history}

Current question: {question}

Context information:
- Topic: {topic}
- Difficulty: {difficulty}
- Format: {format}

Please provide a {response_type} response.
"""
        
        context = {
            "system_prompt": "You are a helpful assistant",
            "conversation_history": "User: Hello\nAssistant: Hi there!",
            "question": "What is machine learning?",
            "topic": "AI/ML",
            "difficulty": "beginner",
            "format": "detailed",
            "response_type": "comprehensive"
        }
        
        result = self.manager.apply_prompt_template(complex_template, context)
        
        assert "You are a helpful assistant" in result
        assert "What is machine learning?" in result
        assert "comprehensive" in result
        assert "User: Hello" in result
    
    def test_validate_template_with_edge_case_syntax(self):
        """Test template validation with edge case syntax."""
        edge_case_templates = [
            "Normal text without variables",  # No variables
            "{single_var}",                   # Only variable
            "{{escaped_braces}}",            # Escaped braces
            "{var1} and {var2} and {var1}",  # Repeated variables
            "Text with { space } in braces", # Spaces in braces
            "Text with {_underscore_var}",   # Underscore in variable
            "Text with {var123}",            # Numbers in variable
            "Text with {VAR_UPPER}",         # Uppercase variable
        ]
        
        for template in edge_case_templates:
            result = self.manager.validate_template_syntax(template)
            # Most should be valid except the one with spaces
            if "{ space }" in template:
                assert not result.is_valid
            else:
                assert result.is_valid


class TestPerformanceAndScalability:
    """Test performance and scalability of the configuration system."""
    
    def test_large_configuration_parsing_performance(self):
        """Test parsing performance with very large configurations."""
        # Create a configuration with 1000 tasks and 100 models
        large_config = {
            "metadata": {"name": "Performance Test", "version": "1.0"},
            "models": {},
            "tasks": [],
            "variables": {}
        }
        
        # Add variables
        for i in range(100):
            large_config["variables"][f"var_{i}"] = f"value_{i}"
        
        # Add models
        for i in range(100):
            large_config["models"][f"model_{i}"] = {
                "name": f"model_{i}",
                "type": "openai",
                "model_name": f"gpt-3.5-turbo-{i}",
                "parameters": {
                    "temperature": "${var_" + str(i % 100) + "}",
                    "max_tokens": 1000 + i
                }
            }
        
        # Add tasks with dependencies
        for i in range(1000):
            depends_on = []
            if i > 0:
                depends_on.append(f"task_{i-1}")
            if i > 10:
                depends_on.append(f"task_{i-10}")
            
            large_config["tasks"].append({
                "name": f"task_{i}",
                "model_ref": f"model_{i % 100}",
                "task_name": "hellaswag",
                "num_fewshot": i % 20,
                "batch_size": (i % 64) + 1,
                "depends_on": depends_on
            })
        
        parser = ConfigParser()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(large_config, f)
            temp_path = f.name
        
        try:
            start_time = time.time()
            config = parser.parse_config(temp_path)
            parse_time = time.time() - start_time
            
            # Should parse within reasonable time (< 10 seconds)
            assert parse_time < 10.0
            assert len(config.models) == 100
            assert len(config.tasks) == 1000
            
            # Test validation performance
            validator = ConfigValidator()
            start_time = time.time()
            result = validator.validate_config(config)
            validation_time = time.time() - start_time
            
            # Should validate within reasonable time (< 5 seconds)
            assert validation_time < 5.0
            
        finally:
            os.unlink(temp_path)
    
    def test_concurrent_configuration_processing(self):
        """Test concurrent processing of multiple configurations."""
        import threading
        import queue
        
        def process_config(config_data, result_queue):
            """Process a configuration in a separate thread."""
            try:
                parser = ConfigParser()
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(config_data, f)
                    temp_path = f.name
                
                try:
                    config = parser.parse_config(temp_path)
                    result_queue.put(("success", config))
                except Exception as e:
                    result_queue.put(("error", str(e)))
                finally:
                    os.unlink(temp_path)
                    
            except Exception as e:
                result_queue.put(("error", str(e)))
        
        # Create multiple configurations
        configs = []
        for i in range(10):
            config = {
                "metadata": {"name": f"Concurrent Config {i}"},
                "models": {
                    f"model_{i}": {
                        "name": f"model_{i}",
                        "type": "openai",
                        "model_name": "gpt-3.5-turbo"
                    }
                },
                "tasks": [{
                    "name": f"task_{i}",
                    "model_ref": f"model_{i}",
                    "task_name": "hellaswag"
                }]
            }
            configs.append(config)
        
        # Process configurations concurrently
        result_queue = queue.Queue()
        threads = []
        
        start_time = time.time()
        
        for config in configs:
            thread = threading.Thread(target=process_config, args=(config, result_queue))
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        processing_time = time.time() - start_time
        
        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())
        
        # All should succeed
        assert len(results) == 10
        success_count = sum(1 for status, _ in results if status == "success")
        assert success_count == 10
        
        # Should complete within reasonable time (< 5 seconds)
        assert processing_time < 5.0


if __name__ == "__main__":
    pytest.main([__file__])