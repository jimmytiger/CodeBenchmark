"""
Unit tests for ConfigManager component.

Tests configuration loading, validation, and management functionality.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from core.config_manager import ConfigManager
from core.error_handler import ConfigurationError


class TestConfigManager:
    """Unit tests for ConfigManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()
        self.sample_config = {
            'test_type': 'cli',
            'target_adapters': ['lm_eval', 'swe_bench'],
            'task_selection': {'builtin_tasks': ['task1', 'task2']},
            'execution_params': {'timeout': 300, 'verbose': True},
            'output_config': {'format': 'json', 'save_results': True}
        }
    
    def test_load_config_from_file(self):
        """Test loading configuration from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(self.sample_config, f)
            config_path = f.name
        
        try:
            loaded_config = self.config_manager.load_config(config_path)
            assert loaded_config == self.sample_config
        finally:
            os.unlink(config_path)
    
    def test_load_config_from_dict(self):
        """Test loading configuration from dictionary."""
        loaded_config = self.config_manager.load_config(self.sample_config)
        assert loaded_config == self.sample_config
    
    def test_load_config_file_not_found(self):
        """Test error handling when config file doesn't exist."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            self.config_manager.load_config("nonexistent_file.yaml")
    
    def test_validate_config_valid(self):
        """Test validation of valid configuration."""
        is_valid, errors = self.config_manager.validate_config(self.sample_config)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_config_missing_required_fields(self):
        """Test validation with missing required fields."""
        invalid_config = {'test_type': 'cli'}  # Missing other required fields
        is_valid, errors = self.config_manager.validate_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
        assert any('target_adapters' in error for error in errors)
    
    def test_validate_config_invalid_test_type(self):
        """Test validation with invalid test type."""
        invalid_config = self.sample_config.copy()
        invalid_config['test_type'] = 'invalid_type'
        is_valid, errors = self.config_manager.validate_config(invalid_config)
        assert is_valid is False
        assert any('test_type' in error for error in errors)
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        default_config = self.config_manager.get_default_config()
        assert isinstance(default_config, dict)
        assert 'test_type' in default_config
        assert 'target_adapters' in default_config
        assert 'execution_params' in default_config
    
    def test_merge_configs(self):
        """Test merging configurations."""
        base_config = {'test_type': 'cli', 'timeout': 300}
        override_config = {'timeout': 600, 'verbose': True}
        
        merged = self.config_manager.merge_configs(base_config, override_config)
        assert merged['test_type'] == 'cli'
        assert merged['timeout'] == 600  # Override value
        assert merged['verbose'] is True  # New value
    
    def test_save_config(self):
        """Test saving configuration to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        try:
            self.config_manager.save_config(self.sample_config, config_path)
            
            # Verify file was created and contains correct data
            with open(config_path, 'r') as f:
                saved_config = yaml.safe_load(f)
            assert saved_config == self.sample_config
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)
    
    @patch('builtins.open', mock_open(read_data='invalid: yaml: content:'))
    def test_load_config_invalid_yaml(self):
        """Test error handling for invalid YAML content."""
        with pytest.raises(ConfigurationError, match="Invalid YAML format"):
            self.config_manager.load_config("test.yaml")
    
    def test_config_schema_validation(self):
        """Test configuration schema validation."""
        # Test with extra unknown fields
        config_with_extra = self.sample_config.copy()
        config_with_extra['unknown_field'] = 'value'
        
        is_valid, errors = self.config_manager.validate_config(config_with_extra)
        # Should still be valid but may warn about unknown fields
        assert is_valid is True
    
    def test_environment_variable_substitution(self):
        """Test environment variable substitution in config."""
        config_with_env = {
            'test_type': 'cli',
            'api_key': '${API_KEY}',
            'timeout': '${TIMEOUT:300}'  # With default value
        }
        
        with patch.dict(os.environ, {'API_KEY': 'test_key'}):
            resolved_config = self.config_manager.resolve_environment_variables(config_with_env)
            assert resolved_config['api_key'] == 'test_key'
            assert resolved_config['timeout'] == '300'  # Default value used