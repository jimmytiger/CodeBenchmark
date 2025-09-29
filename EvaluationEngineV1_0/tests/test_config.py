"""
Tests for Configuration Management Components

Tests configuration manager, validator, and template generator
functionality.
"""

import pytest
import json
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from ..config.config_manager import ConfigManager
from ..config.config_validator import ConfigValidator
from ..config.template_generator import TemplateGenerator
from ..core.data_models import MultiTurnConfig


@pytest.fixture
def config_manager():
    """Create config manager instance."""
    return ConfigManager()


@pytest.fixture
def config_validator():
    """Create config validator instance."""
    return ConfigValidator()


@pytest.fixture
def template_generator():
    """Create template generator instance."""
    return TemplateGenerator()


@pytest.fixture
def sample_config():
    """Sample configuration dictionary."""
    return {
        "model_id": "gpt-4",
        "task_ids": ["task1", "task2"],
        "max_turns": 10,
        "timeout_seconds": 3600,
        "feedback_strategy": "adaptive",
        "safety_level": "moderate",
        "enable_context_retention": True,
        "metadata": {"test": "data"}
    }


@pytest.fixture
def temp_config_file(sample_config):
    """Create temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


class TestConfigManager:
    """Test configuration manager functionality."""
    
    def test_load_config_yaml(self, config_manager, temp_config_file):
        """Test loading YAML configuration file."""
        config_data = config_manager.load_config(temp_config_file)
        
        assert config_data["model_id"] == "gpt-4"
        assert config_data["task_ids"] == ["task1", "task2"]
        assert config_data["max_turns"] == 10
    
    def test_load_config_json(self, config_manager, sample_config):
        """Test loading JSON configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config, f)
            temp_path = f.name
        
        try:
            config_data = config_manager.load_config(temp_path)
            
            assert config_data["model_id"] == "gpt-4"
            assert config_data["task_ids"] == ["task1", "task2"]
            
        finally:
            os.unlink(temp_path)
    
    def test_load_config_nonexistent(self, config_manager):
        """Test loading non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            config_manager.load_config("nonexistent.yaml")
    
    def test_load_config_invalid_yaml(self, config_manager):
        """Test loading invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Invalid configuration file format"):
                config_manager.load_config(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_load_config_with_cache(self, config_manager, temp_config_file):
        """Test configuration caching."""
        # Load config first time
        config1 = config_manager.load_config(temp_config_file, use_cache=True)
        
        # Load config second time (should use cache)
        config2 = config_manager.load_config(temp_config_file, use_cache=True)
        
        assert config1 == config2
        assert len(config_manager.config_cache) == 1
    
    def test_load_config_without_validation(self, config_manager):
        """Test loading configuration without validation."""
        invalid_config = {"model_id": "gpt-4"}  # Missing required fields
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            # Should not raise error when validation is disabled
            config_data = config_manager.load_config(temp_path, validate=False)
            assert config_data["model_id"] == "gpt-4"
            
        finally:
            os.unlink(temp_path)
    
    def test_save_config_yaml(self, config_manager, sample_config):
        """Test saving configuration to YAML file."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            config_manager.save_config(sample_config, temp_path, 'yaml')
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            # Verify content
            with open(temp_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
            
            assert loaded_config["model_id"] == "gpt-4"
            assert loaded_config["task_ids"] == ["task1", "task2"]
            
        finally:
            os.unlink(temp_path)
    
    def test_save_config_json(self, config_manager, sample_config):
        """Test saving configuration to JSON file."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config_manager.save_config(sample_config, temp_path, 'json')
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            # Verify content
            with open(temp_path, 'r') as f:
                loaded_config = json.load(f)
            
            assert loaded_config["model_id"] == "gpt-4"
            assert loaded_config["task_ids"] == ["task1", "task2"]
            
        finally:
            os.unlink(temp_path)
    
    def test_save_config_invalid_format(self, config_manager, sample_config):
        """Test saving configuration with invalid format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            config_manager.save_config(sample_config, "test.txt", "invalid")
    
    def test_merge_configs(self, config_manager):
        """Test merging configuration dictionaries."""
        config1 = {
            "model_id": "gpt-3.5",
            "max_turns": 5,
            "metadata": {"version": "1.0"}
        }
        
        config2 = {
            "model_id": "gpt-4",
            "timeout_seconds": 7200,
            "metadata": {"experiment": "test"}
        }
        
        merged = config_manager.merge_configs(config1, config2)
        
        assert merged["model_id"] == "gpt-4"  # Overridden
        assert merged["max_turns"] == 5  # From config1
        assert merged["timeout_seconds"] == 7200  # From config2
        assert merged["metadata"]["version"] == "1.0"  # Merged
        assert merged["metadata"]["experiment"] == "test"  # Merged
    
    def test_create_multi_turn_config(self, config_manager, sample_config):
        """Test creating MultiTurnConfig from configuration data."""
        config = config_manager.create_multi_turn_config(sample_config)
        
        assert isinstance(config, MultiTurnConfig)
        assert config.max_turns == 10
        assert config.conversation_timeout == 3600
        assert config.enable_context_retention is True
    
    def test_config_to_dict(self, config_manager, sample_config):
        """Test converting MultiTurnConfig to dictionary."""
        config = config_manager.create_multi_turn_config(sample_config)
        config_dict = config_manager.config_to_dict(config)
        
        assert config_dict["max_turns"] == 10
        assert config_dict["timeout_seconds"] == 3600
        assert config_dict["enable_context_retention"] is True
    
    def test_get_config_schema(self, config_manager):
        """Test getting configuration schema."""
        schema = config_manager.get_config_schema()
        
        assert schema["type"] == "object"
        assert "model_id" in schema["required"]
        assert "task_ids" in schema["required"]
        assert "model_id" in schema["properties"]
        assert "task_ids" in schema["properties"]
    
    def test_clear_cache(self, config_manager, temp_config_file):
        """Test clearing configuration cache."""
        # Load config to populate cache
        config_manager.load_config(temp_config_file, use_cache=True)
        assert len(config_manager.config_cache) == 1
        
        # Clear cache
        config_manager.clear_cache()
        assert len(config_manager.config_cache) == 0
    
    @patch.dict(os.environ, {'MULTI_TURN_MODEL_ID': 'gpt-3.5', 'MULTI_TURN_MAX_TURNS': '15'})
    def test_environment_overrides(self, config_manager, sample_config):
        """Test environment variable overrides."""
        # Create config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            temp_path = f.name
        
        try:
            config_data = config_manager.load_config(temp_path)
            
            # Environment variables should override config file values
            assert config_data["model_id"] == "gpt-3.5"  # Overridden by env var
            assert config_data["max_turns"] == 15  # Overridden by env var
            assert config_data["task_ids"] == ["task1", "task2"]  # From config file
            
        finally:
            os.unlink(temp_path)


class TestConfigValidator:
    """Test configuration validator functionality."""
    
    def test_validate_config_success(self, config_validator, sample_config):
        """Test successful configuration validation."""
        result = config_validator.validate_config(sample_config)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "warnings" in result
    
    def test_validate_config_missing_required(self, config_validator):
        """Test validation with missing required fields."""
        config = {"model_id": "gpt-4"}  # Missing task_ids
        
        result = config_validator.validate_config(config)
        
        assert result["valid"] is False
        assert any("Missing required field: task_ids" in error for error in result["errors"])
    
    def test_validate_config_invalid_types(self, config_validator):
        """Test validation with invalid field types."""
        config = {
            "model_id": 123,  # Should be string
            "task_ids": "not_a_list",  # Should be list
            "max_turns": "not_a_number"  # Should be number
        }
        
        result = config_validator.validate_config(config)
        
        assert result["valid"] is False
        assert any("model_id must be a str" in error for error in result["errors"])
        assert any("task_ids must be a list" in error for error in result["errors"])
        assert any("max_turns must be a int" in error for error in result["errors"])
    
    def test_validate_task_ids_success(self, config_validator):
        """Test successful task ID validation."""
        task_ids = ["valid_task_1", "another-task", "task123"]
        
        errors = config_validator.validate_task_ids(task_ids)
        
        assert len(errors) == 0
    
    def test_validate_task_ids_invalid_format(self, config_validator):
        """Test task ID validation with invalid format."""
        task_ids = ["invalid task!", "task@123", ""]
        
        errors = config_validator.validate_task_ids(task_ids)
        
        assert len(errors) > 0
        assert any("contains invalid characters" in error for error in errors)
        assert any("cannot be empty" in error for error in errors)
    
    def test_validate_task_ids_duplicates(self, config_validator):
        """Test task ID validation with duplicates."""
        task_ids = ["task1", "task2", "task1"]
        
        errors = config_validator.validate_task_ids(task_ids)
        
        assert len(errors) > 0
        assert any("Duplicate task IDs" in error for error in errors)
    
    def test_validate_model_id_success(self, config_validator):
        """Test successful model ID validation."""
        errors = config_validator.validate_model_id("gpt-4")
        
        assert len(errors) == 0
    
    def test_validate_model_id_invalid(self, config_validator):
        """Test model ID validation with invalid format."""
        errors = config_validator.validate_model_id("invalid model!")
        
        assert len(errors) > 0
        assert any("contains invalid characters" in error for error in errors)
    
    def test_validate_resource_limits_success(self, config_validator):
        """Test successful resource limits validation."""
        resource_limits = {
            "max_memory_mb": 2048,
            "max_cpu_percent": 80,
            "max_disk_mb": 1024
        }
        
        errors = config_validator.validate_resource_limits(resource_limits)
        
        assert len(errors) == 0
    
    def test_validate_resource_limits_invalid(self, config_validator):
        """Test resource limits validation with invalid values."""
        resource_limits = {
            "max_memory_mb": "not_a_number",
            "max_cpu_percent": 150,  # Too high
            "unknown_limit": 100
        }
        
        errors = config_validator.validate_resource_limits(resource_limits)
        
        assert len(errors) > 0
        assert any("must be a int" in error for error in errors)
        assert any("must be between" in error for error in errors)
        assert any("Unknown resource limit" in error for error in errors)
    
    def test_validate_dangerous_patterns_success(self, config_validator):
        """Test successful dangerous patterns validation."""
        patterns = ["rm.*-rf", "sudo.*", "chmod.*777"]
        
        errors = config_validator.validate_dangerous_patterns(patterns)
        
        assert len(errors) == 0
    
    def test_validate_dangerous_patterns_invalid_regex(self, config_validator):
        """Test dangerous patterns validation with invalid regex."""
        patterns = ["rm.*-rf", "[invalid_regex"]
        
        errors = config_validator.validate_dangerous_patterns(patterns)
        
        assert len(errors) > 0
        assert any("not a valid regex pattern" in error for error in errors)
    
    def test_validate_metadata_success(self, config_validator):
        """Test successful metadata validation."""
        metadata = {
            "description": "Test evaluation",
            "created_by": "user",
            "tags": ["test", "example"]
        }
        
        errors = config_validator.validate_metadata(metadata)
        
        assert len(errors) == 0
    
    def test_validate_metadata_reserved_keys(self, config_validator):
        """Test metadata validation with reserved keys."""
        metadata = {
            "_internal": "should_not_be_allowed",
            "valid_key": "valid_value"
        }
        
        errors = config_validator.validate_metadata(metadata)
        
        assert len(errors) > 0
        assert any("is reserved" in error for error in errors)
    
    def test_validate_metadata_deep_nesting(self, config_validator):
        """Test metadata validation with deep nesting."""
        metadata = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "too_deep"
                    }
                }
            }
        }
        
        errors = config_validator.validate_metadata(metadata)
        
        assert len(errors) > 0
        assert any("nesting too deep" in error for error in errors)


class TestTemplateGenerator:
    """Test template generator functionality."""
    
    def test_get_template_basic(self, template_generator):
        """Test getting basic template."""
        template = template_generator.get_template("basic")
        
        assert "model_id" in template
        assert "task_ids" in template
        assert "max_turns" in template
        assert "metadata" in template
        assert template["metadata"]["template_name"] == "basic"
    
    def test_get_template_advanced(self, template_generator):
        """Test getting advanced template."""
        template = template_generator.get_template("advanced")
        
        assert "model_id" in template
        assert "resource_limits" in template
        assert "dangerous_patterns" in template
        assert template["max_turns"] == 20
    
    def test_get_template_invalid(self, template_generator):
        """Test getting invalid template."""
        with pytest.raises(ValueError, match="Template 'invalid' not found"):
            template_generator.get_template("invalid")
    
    def test_list_templates(self, template_generator):
        """Test listing available templates."""
        templates = template_generator.list_templates()
        
        assert len(templates) > 0
        assert all("name" in template for template in templates)
        assert all("description" in template for template in templates)
        assert any(template["name"] == "basic" for template in templates)
        assert any(template["name"] == "advanced" for template in templates)
    
    def test_create_custom_template(self, template_generator):
        """Test creating custom template."""
        template = template_generator.create_custom_template(
            model_id="gpt-4",
            task_ids=["custom_task_1", "custom_task_2"],
            scenario="coding",
            complexity="medium",
            custom_field="custom_value"
        )
        
        assert template["model_id"] == "gpt-4"
        assert template["task_ids"] == ["custom_task_1", "custom_task_2"]
        assert template["metadata"]["scenario"] == "coding"
        assert template["metadata"]["complexity"] == "medium"
        assert template["custom_field"] == "custom_value"
    
    def test_generate_benchmark_template_swe_bench(self, template_generator):
        """Test generating SWE-bench template."""
        template = template_generator.generate_benchmark_template("swe_bench")
        
        assert "swe_bench" in template["task_ids"][0]
        assert template["max_turns"] == 25
        assert "pytest" in template["allowed_tools"]
        assert template["metadata"]["benchmark"] == "swe_bench"
    
    def test_generate_benchmark_template_intercode(self, template_generator):
        """Test generating InterCode template."""
        template = template_generator.generate_benchmark_template("intercode")
        
        assert "intercode" in template["task_ids"][0]
        assert "sqlite3" in template["allowed_tools"]
        assert template["metadata"]["benchmark"] == "intercode"
    
    def test_generate_benchmark_template_invalid(self, template_generator):
        """Test generating template for invalid benchmark."""
        with pytest.raises(ValueError, match="Benchmark 'invalid' not supported"):
            template_generator.generate_benchmark_template("invalid")


if __name__ == "__main__":
    pytest.main([__file__])