"""
Tests for configuration parser.
"""

import os
import tempfile
import json
import pytest
from evaluation_engine.config.parser import ConfigParser
from evaluation_engine.config.models import (
    EvaluationConfig,
    TaskConfig,
    ModelConfig,
    ConfigMetadata,
    ValidationSeverity
)

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class TestConfigParser:
    """Test ConfigParser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ConfigParser()
        
        # Sample configuration data
        self.sample_config = {
            "metadata": {
                "name": "test-evaluation",
                "version": "1.0",
                "author": "Test Author"
            },
            "models": {
                "gpt35": {
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "parameters": {"temperature": 0.7}
                }
            },
            "tasks": [
                {
                    "name": "test-task",
                    "model_ref": "gpt35",
                    "task_name": "hellaswag",
                    "num_fewshot": 5
                }
            ],
            "variables": {
                "output_dir": "./results"
            }
        }
    
    def test_parse_json_config(self):
        """Test parsing JSON configuration file."""
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(self.sample_config, f)
            f.flush()
            
            config = self.parser.parse_config(f.name)
            
            assert isinstance(config, EvaluationConfig)
            assert config.metadata.name == "test-evaluation"
            assert config.metadata.author == "Test Author"
            assert len(config.tasks) == 1
            assert config.tasks[0].name == "test-task"
            assert config.tasks[0].model_ref == "gpt35"
            assert "gpt35" in config.models
            assert config.models["gpt35"].type == "openai"
            assert config.variables["output_dir"] == "./results"
            
            os.unlink(f.name)
    
    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not available")
    def test_parse_yaml_config(self):
        """Test parsing YAML configuration file."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f:
            yaml.dump(self.sample_config, f)
            f.flush()
            
            config = self.parser.parse_config(f.name)
            
            assert isinstance(config, EvaluationConfig)
            assert config.metadata.name == "test-evaluation"
            assert len(config.tasks) == 1
            assert config.tasks[0].name == "test-task"
            
            os.unlink(f.name)
    
    def test_parse_config_with_defaults(self):
        """Test parsing configuration with default values."""
        config_data = {
            "metadata": {"name": "test-config"},
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            config = self.parser.parse_config(f.name)
            
            # Check that defaults are applied
            assert config.defaults is not None
            assert config.defaults.num_fewshot == 5
            assert config.defaults.batch_size == 32
            assert config.output is not None
            assert config.output.directory == "./results"
            
            os.unlink(f.name)
    
    def test_parse_config_missing_metadata(self):
        """Test parsing configuration with missing metadata."""
        config_data = {
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model", 
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="'metadata.name' is required"):
                self.parser.parse_config(f.name)
            
            os.unlink(f.name)
    
    def test_parse_config_missing_tasks(self):
        """Test parsing configuration with missing tasks."""
        config_data = {
            "metadata": {"name": "test-config"}
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="At least one task must be defined"):
                self.parser.parse_config(f.name)
            
            os.unlink(f.name)
    
    def test_parse_config_invalid_task(self):
        """Test parsing configuration with invalid task."""
        config_data = {
            "metadata": {"name": "test-config"},
            "tasks": [{
                "name": "test-task",
                # missing model_ref and task_name
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="Invalid task configuration"):
                self.parser.parse_config(f.name)
            
            os.unlink(f.name)
    
    def test_parse_config_invalid_model(self):
        """Test parsing configuration with invalid model."""
        config_data = {
            "metadata": {"name": "test-config"},
            "models": {
                "invalid-model": {
                    # missing required fields
                }
            },
            "tasks": [{
                "name": "test-task",
                "model_ref": "invalid-model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="Invalid model configuration"):
                self.parser.parse_config(f.name)
            
            os.unlink(f.name)
    
    def test_validate_syntax_valid_file(self):
        """Test syntax validation for valid configuration file."""
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(self.sample_config, f)
            f.flush()
            
            result = self.parser.validate_syntax(f.name)
            
            assert result.is_valid is True
            assert len(result.errors) == 0
            
            os.unlink(f.name)
    
    def test_validate_syntax_invalid_json(self):
        """Test syntax validation for invalid JSON file."""
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            f.write('{ invalid json }')
            f.flush()
            
            result = self.parser.validate_syntax(f.name)
            
            assert result.is_valid is False
            assert len(result.errors) == 1
            assert result.errors[0].severity == ValidationSeverity.ERROR
            assert "syntax error" in result.errors[0].message.lower()
            
            os.unlink(f.name)
    
    def test_validate_syntax_nonexistent_file(self):
        """Test syntax validation for non-existent file."""
        result = self.parser.validate_syntax('/nonexistent/file.json')
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].message
    
    def test_parse_config_nonexistent_file(self):
        """Test parsing non-existent configuration file."""
        with pytest.raises(ValueError, match="Configuration file validation failed"):
            self.parser.parse_config('/nonexistent/file.json')
    
    def test_parse_config_with_custom_defaults(self):
        """Test parsing configuration with custom defaults."""
        config_data = {
            "metadata": {"name": "test-config"},
            "defaults": {
                "num_fewshot": 10,
                "batch_size": 64,
                "output": {"format": ["csv"], "save_predictions": False}
            },
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            config = self.parser.parse_config(f.name)
            
            assert config.defaults.num_fewshot == 10
            assert config.defaults.batch_size == 64
            assert config.defaults.output["format"] == ["csv"]
            
            os.unlink(f.name)
    
    def test_parse_config_with_custom_output(self):
        """Test parsing configuration with custom output settings."""
        config_data = {
            "metadata": {"name": "test-config"},
            "output": {
                "directory": "/tmp/results",
                "formats": ["json", "csv"],
                "include_raw_responses": True
            },
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            config = self.parser.parse_config(f.name)
            
            assert config.output.directory == "/tmp/results"
            assert config.output.formats == ["json", "csv"]
            assert config.output.include_raw_responses is True
            
            os.unlink(f.name)
    
    def test_resolve_variables_basic(self):
        """Test basic variable resolution."""
        config_data = {
            "variables": {
                "model_name": "gpt-3.5-turbo",
                "output_dir": "./results"
            },
            "metadata": {"name": "test-config"},
            "models": {
                "gpt35": {
                    "type": "openai",
                    "model_name": "${model_name}",
                    "parameters": {"temperature": 0.7}
                }
            },
            "tasks": [{
                "name": "test-task",
                "model_ref": "gpt35",
                "task_name": "hellaswag"
            }],
            "output": {
                "directory": "${output_dir}"
            }
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            config = self.parser.parse_config(f.name)
            
            assert config.models["gpt35"].model_name == "gpt-3.5-turbo"
            assert config.output.directory == "./results"
            
            os.unlink(f.name)
    
    def test_resolve_variables_environment(self):
        """Test environment variable resolution."""
        # Set a test environment variable
        os.environ['TEST_MODEL_NAME'] = 'test-model-from-env'
        os.environ['TEST_OUTPUT_DIR'] = '/tmp/test-results'
        
        try:
            config_data = {
                "variables": {
                    "local_var": "local-value"
                },
                "metadata": {"name": "test-config"},
                "models": {
                    "test_model": {
                        "type": "openai",
                        "model_name": "${env:TEST_MODEL_NAME}",
                        "parameters": {"temperature": 0.7}
                    }
                },
                "tasks": [{
                    "name": "test-task",
                    "model_ref": "test_model",
                    "task_name": "hellaswag"
                }],
                "output": {
                    "directory": "${env:TEST_OUTPUT_DIR}"
                }
            }
            
            with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
                json.dump(config_data, f)
                f.flush()
                
                config = self.parser.parse_config(f.name)
                
                assert config.models["test_model"].model_name == "test-model-from-env"
                assert config.output.directory == "/tmp/test-results"
                
                os.unlink(f.name)
        finally:
            # Clean up environment variables
            del os.environ['TEST_MODEL_NAME']
            del os.environ['TEST_OUTPUT_DIR']
    
    def test_resolve_variables_nested(self):
        """Test nested variable resolution."""
        config_data = {
            "variables": {
                "base_dir": "/tmp",
                "project_name": "test-project",
                "output_dir": "${base_dir}/${project_name}/results"
            },
            "metadata": {"name": "test-config"},
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model",
                "task_name": "hellaswag"
            }],
            "output": {
                "directory": "${output_dir}"
            }
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            config = self.parser.parse_config(f.name)
            
            assert config.output.directory == "/tmp/test-project/results"
            
            os.unlink(f.name)
    
    def test_resolve_variables_circular_reference(self):
        """Test detection of circular variable references."""
        config_data = {
            "variables": {
                "var_a": "${var_b}",
                "var_b": "${var_a}"
            },
            "metadata": {"name": "test-config"},
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="Circular reference detected"):
                self.parser.parse_config(f.name)
            
            os.unlink(f.name)
    
    def test_resolve_variables_undefined_variable(self):
        """Test handling of undefined variables."""
        config_data = {
            "variables": {
                "defined_var": "value"
            },
            "metadata": {"name": "test-config"},
            "models": {
                "test_model": {
                    "type": "openai",
                    "model_name": "${undefined_var}",
                    "parameters": {"temperature": 0.7}
                }
            },
            "tasks": [{
                "name": "test-task",
                "model_ref": "test_model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="Variable not found: undefined_var"):
                self.parser.parse_config(f.name)
            
            os.unlink(f.name)
    
    def test_resolve_variables_undefined_env_variable(self):
        """Test handling of undefined environment variables."""
        config_data = {
            "metadata": {"name": "test-config"},
            "models": {
                "test_model": {
                    "type": "openai",
                    "model_name": "${env:UNDEFINED_ENV_VAR}",
                    "parameters": {"temperature": 0.7}
                }
            },
            "tasks": [{
                "name": "test-task",
                "model_ref": "test_model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="Environment variable not found: UNDEFINED_ENV_VAR"):
                self.parser.parse_config(f.name)
            
            os.unlink(f.name)
    
    def test_resolve_variables_in_lists(self):
        """Test variable resolution in lists."""
        config_data = {
            "variables": {
                "format1": "json",
                "format2": "csv"
            },
            "metadata": {"name": "test-config"},
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model",
                "task_name": "hellaswag"
            }],
            "output": {
                "formats": ["${format1}", "${format2}", "html"]
            }
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            config = self.parser.parse_config(f.name)
            
            assert config.output.formats == ["json", "csv", "html"]
            
            os.unlink(f.name)
    
    def test_resolve_variables_mixed_types(self):
        """Test variable resolution with mixed data types."""
        config_data = {
            "variables": {
                "batch_size": 64,
                "temperature": 0.8,
                "enable_feature": True,
                "model_name": "gpt-4"
            },
            "metadata": {"name": "test-config"},
            "models": {
                "test_model": {
                    "type": "openai",
                    "model_name": "${model_name}",
                    "parameters": {
                        "temperature": "${temperature}",
                        "max_tokens": 1000
                    }
                }
            },
            "tasks": [{
                "name": "test-task",
                "model_ref": "test_model",
                "task_name": "hellaswag",
                "batch_size": "${batch_size}"
            }],
            "defaults": {
                "batch_size": "${batch_size}"
            }
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            config = self.parser.parse_config(f.name)
            
            assert config.models["test_model"].model_name == "gpt-4"
            # Note: variables are resolved as strings, so numeric values become strings
            assert config.models["test_model"].parameters["temperature"] == "0.8"
            
            os.unlink(f.name)
    
    def test_resolve_variables_no_variables_section(self):
        """Test configuration without variables section."""
        config_data = {
            "metadata": {"name": "test-config"},
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            # Should not raise any errors
            config = self.parser.parse_config(f.name)
            assert config.metadata.name == "test-config"
            
            os.unlink(f.name)
    
    def test_template_inheritance_basic(self):
        """Test basic template inheritance with extends."""
        # Create parent template
        parent_config = {
            "metadata": {
                "name": "parent-config",
                "version": "1.0"
            },
            "models": {
                "base_model": {
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo",
                    "parameters": {"temperature": 0.5}
                }
            },
            "defaults": {
                "num_fewshot": 10,
                "batch_size": 32
            }
        }
        
        # Create child template that extends parent
        child_config = {
            "extends": "parent.json",
            "metadata": {
                "name": "child-config",  # Override parent name
                "author": "Test Author"  # Add new field
            },
            "models": {
                "base_model": {
                    "parameters": {"temperature": 0.7}  # Override temperature
                },
                "new_model": {  # Add new model
                    "type": "anthropic",
                    "model_name": "claude-3-sonnet",
                    "parameters": {"temperature": 0.6}
                }
            },
            "tasks": [{
                "name": "test-task",
                "model_ref": "base_model",
                "task_name": "hellaswag"
            }]
        }
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as parent_file:
            json.dump(parent_config, parent_file)
            parent_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False, dir=os.path.dirname(parent_file.name)) as child_file:
                # Update child config to reference the correct parent file
                child_config_copy = child_config.copy()
                child_config_copy["extends"] = os.path.basename(parent_file.name)
                json.dump(child_config_copy, child_file)
                child_file.flush()
                
                config = self.parser.parse_config(child_file.name)
                
                # Check that child overrides work
                assert config.metadata.name == "child-config"
                assert config.metadata.author == "Test Author"
                assert config.metadata.version == "1.0"  # Inherited from parent
                
                # Check model merging
                assert "base_model" in config.models
                assert "new_model" in config.models
                assert config.models["base_model"].parameters["temperature"] == 0.7  # Overridden
                assert config.models["new_model"].type == "anthropic"  # New model
                
                # Check defaults inheritance
                assert config.defaults.num_fewshot == 10
                assert config.defaults.batch_size == 32
                
                # Check tasks (only in child)
                assert len(config.tasks) == 1
                assert config.tasks[0].name == "test-task"
                
                os.unlink(child_file.name)
            os.unlink(parent_file.name)
    
    def test_include_functionality(self):
        """Test include functionality."""
        # Create a models configuration file
        models_config = {
            "gpt35": {
                "type": "openai",
                "model_name": "gpt-3.5-turbo",
                "parameters": {"temperature": 0.7}
            },
            "claude": {
                "type": "anthropic",
                "model_name": "claude-3-sonnet",
                "parameters": {"temperature": 0.6}
            }
        }
        
        # Create main configuration with include
        main_config = {
            "metadata": {"name": "test-config"},
            "models": {"include": "models.json"},
            "tasks": [{
                "name": "test-task",
                "model_ref": "gpt35",
                "task_name": "hellaswag"
            }]
        }
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as models_file:
            json.dump(models_config, models_file)
            models_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False, dir=os.path.dirname(models_file.name)) as main_file:
                # Update main config to reference the correct models file
                main_config_copy = main_config.copy()
                main_config_copy["models"] = {"include": os.path.basename(models_file.name)}
                json.dump(main_config_copy, main_file)
                main_file.flush()
                
                config = self.parser.parse_config(main_file.name)
                
                # Check that models were included
                assert "gpt35" in config.models
                assert "claude" in config.models
                assert config.models["gpt35"].type == "openai"
                assert config.models["claude"].type == "anthropic"
                
                os.unlink(main_file.name)
            os.unlink(models_file.name)
    
    def test_include_in_list(self):
        """Test include functionality within lists."""
        # Create task configurations
        task1_config = {
            "name": "task1",
            "model_ref": "gpt35",
            "task_name": "hellaswag",
            "num_fewshot": 5
        }
        
        task2_config = {
            "name": "task2", 
            "model_ref": "claude",
            "task_name": "arc_easy",
            "num_fewshot": 10
        }
        
        # Create main configuration with includes in task list
        main_config = {
            "metadata": {"name": "test-config"},
            "models": {
                "gpt35": {
                    "type": "openai",
                    "model_name": "gpt-3.5-turbo"
                },
                "claude": {
                    "type": "anthropic", 
                    "model_name": "claude-3-sonnet"
                }
            },
            "tasks": [
                {"include": "task1.json"},
                {"include": "task2.json"},
                {
                    "name": "inline-task",
                    "model_ref": "gpt35",
                    "task_name": "gsm8k"
                }
            ]
        }
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as task1_file:
            json.dump(task1_config, task1_file)
            task1_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False, dir=os.path.dirname(task1_file.name)) as task2_file:
                json.dump(task2_config, task2_file)
                task2_file.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False, dir=os.path.dirname(task1_file.name)) as main_file:
                    # Update main config to reference the correct task files
                    main_config_copy = main_config.copy()
                    main_config_copy["tasks"] = [
                        {"include": os.path.basename(task1_file.name)},
                        {"include": os.path.basename(task2_file.name)},
                        {
                            "name": "inline-task",
                            "model_ref": "gpt35",
                            "task_name": "gsm8k"
                        }
                    ]
                    json.dump(main_config_copy, main_file)
                    main_file.flush()
                    
                    config = self.parser.parse_config(main_file.name)
                    
                    # Check that all tasks are present
                    assert len(config.tasks) == 3
                    task_names = [task.name for task in config.tasks]
                    assert "task1" in task_names
                    assert "task2" in task_names
                    assert "inline-task" in task_names
                    
                    # Check task details
                    task1 = next(task for task in config.tasks if task.name == "task1")
                    assert task1.model_ref == "gpt35"
                    assert task1.task_name == "hellaswag"
                    assert task1.num_fewshot == 5
                    
                    os.unlink(main_file.name)
                os.unlink(task2_file.name)
            os.unlink(task1_file.name)
    
    def test_circular_include_detection(self):
        """Test detection of circular includes."""
        # Create file A that includes file B
        config_a = {
            "metadata": {"name": "config-a"},
            "tasks": [{"include": "config_b.json"}]
        }
        
        # Create file B that includes file A (circular)
        config_b = {
            "name": "task-b",
            "model_ref": "test-model",
            "task_name": "hellaswag",
            "subtasks": [{"include": "config_a.json"}]
        }
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as file_a:
            json.dump(config_a, file_a)
            file_a.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False, dir=os.path.dirname(file_a.name)) as file_b:
                # Update configs to reference correct files
                config_a_copy = config_a.copy()
                config_a_copy["tasks"] = [{"include": os.path.basename(file_b.name)}]
                
                config_b_copy = config_b.copy()
                config_b_copy["subtasks"] = [{"include": os.path.basename(file_a.name)}]
                
                # Write file A
                file_a.seek(0)
                file_a.truncate()
                json.dump(config_a_copy, file_a)
                file_a.flush()
                
                # Write file B
                json.dump(config_b_copy, file_b)
                file_b.flush()
                
                with pytest.raises(ValueError, match="Circular include detected"):
                    self.parser.parse_config(file_a.name)
                
                os.unlink(file_b.name)
            os.unlink(file_a.name)
    
    def test_nonexistent_template_file(self):
        """Test handling of non-existent template files."""
        config_data = {
            "extends": "nonexistent.json",
            "metadata": {"name": "test-config"},
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="Failed to load parent template"):
                self.parser.parse_config(f.name)
            
            os.unlink(f.name)
    
    def test_nonexistent_include_file(self):
        """Test handling of non-existent include files."""
        config_data = {
            "metadata": {"name": "test-config"},
            "models": {"include": "nonexistent.json"},
            "tasks": [{
                "name": "test-task",
                "model_ref": "test-model",
                "task_name": "hellaswag"
            }]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="Failed to include file"):
                self.parser.parse_config(f.name)
            
            os.unlink(f.name)
    
    def test_combined_extends_and_includes(self):
        """Test combination of extends and includes."""
        # Create base models file
        models_config = {
            "base_model": {
                "type": "openai",
                "model_name": "gpt-3.5-turbo",
                "parameters": {"temperature": 0.5}
            }
        }
        
        # Create parent template
        parent_config = {
            "metadata": {
                "name": "parent-config",
                "version": "1.0"
            },
            "models": {"include": "models.json"},
            "defaults": {
                "num_fewshot": 5,
                "batch_size": 16
            }
        }
        
        # Create child config that extends parent
        child_config = {
            "extends": "parent.json",
            "metadata": {
                "name": "child-config"
            },
            "models": {
                "additional_model": {
                    "type": "anthropic",
                    "model_name": "claude-3-sonnet"
                }
            },
            "tasks": [{
                "name": "test-task",
                "model_ref": "base_model",
                "task_name": "hellaswag"
            }]
        }
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as models_file:
            json.dump(models_config, models_file)
            models_file.flush()
            
            with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False, dir=os.path.dirname(models_file.name)) as parent_file:
                # Update parent config to reference correct models file
                parent_config_copy = parent_config.copy()
                parent_config_copy["models"] = {"include": os.path.basename(models_file.name)}
                json.dump(parent_config_copy, parent_file)
                parent_file.flush()
                
                with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False, dir=os.path.dirname(models_file.name)) as child_file:
                    # Update child config to reference correct parent file
                    child_config_copy = child_config.copy()
                    child_config_copy["extends"] = os.path.basename(parent_file.name)
                    json.dump(child_config_copy, child_file)
                    child_file.flush()
                    
                    config = self.parser.parse_config(child_file.name)
                    
                    # Check metadata inheritance and override
                    assert config.metadata.name == "child-config"
                    assert config.metadata.version == "1.0"
                    
                    # Check models from include and child addition
                    assert "base_model" in config.models
                    assert "additional_model" in config.models
                    assert config.models["base_model"].type == "openai"
                    assert config.models["additional_model"].type == "anthropic"
                    
                    # Check defaults inheritance
                    assert config.defaults.num_fewshot == 5
                    assert config.defaults.batch_size == 16
                    
                    # Check tasks
                    assert len(config.tasks) == 1
                    assert config.tasks[0].name == "test-task"
                    
                    os.unlink(child_file.name)
                os.unlink(parent_file.name)
            os.unlink(models_file.name)