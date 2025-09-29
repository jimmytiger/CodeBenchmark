"""
Tests for configuration format detection.
"""

import os
import tempfile
import pytest
from evaluation_engine.config.detector import ConfigFormatDetector
from evaluation_engine.config.models import ConfigFormat, ValidationSeverity


class TestConfigFormatDetector:
    """Test ConfigFormatDetector functionality."""
    
    def test_detect_yaml_by_extension(self):
        """Test YAML format detection by file extension."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f:
            f.write('test: value')
            f.flush()
            
            format_type = ConfigFormatDetector.detect_format(f.name)
            assert format_type == ConfigFormat.YAML
            
            os.unlink(f.name)
    
    def test_detect_yml_by_extension(self):
        """Test YAML format detection by .yml extension."""
        with tempfile.NamedTemporaryFile(suffix='.yml', mode='w', delete=False) as f:
            f.write('test: value')
            f.flush()
            
            format_type = ConfigFormatDetector.detect_format(f.name)
            assert format_type == ConfigFormat.YAML
            
            os.unlink(f.name)
    
    def test_detect_json_by_extension(self):
        """Test JSON format detection by file extension."""
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False) as f:
            f.write('{"test": "value"}')
            f.flush()
            
            format_type = ConfigFormatDetector.detect_format(f.name)
            assert format_type == ConfigFormat.JSON
            
            os.unlink(f.name)
    
    def test_detect_json_by_content(self):
        """Test JSON format detection by content analysis."""
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as f:
            f.write('{"test": "value"}')
            f.flush()
            
            format_type = ConfigFormatDetector.detect_format(f.name)
            assert format_type == ConfigFormat.JSON
            
            os.unlink(f.name)
    
    def test_detect_unknown_format(self):
        """Test unknown format detection."""
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as f:
            # Write content that's neither valid JSON nor YAML
            # This will fail YAML parsing due to invalid indentation
            f.write('invalid:\n  - item1\n - item2')  # inconsistent indentation
            f.flush()
            
            format_type = ConfigFormatDetector.detect_format(f.name)
            assert format_type == ConfigFormat.UNKNOWN
            
            os.unlink(f.name)
    
    def test_detect_nonexistent_file(self):
        """Test detection of non-existent file."""
        format_type = ConfigFormatDetector.detect_format('/nonexistent/file.yaml')
        assert format_type == ConfigFormat.UNKNOWN
    
    def test_validate_unknown_format(self):
        """Test validation of unknown format."""
        error = ConfigFormatDetector.validate_format_support(ConfigFormat.UNKNOWN)
        assert error is not None
        assert error.severity == ValidationSeverity.ERROR
        assert "Unable to detect" in error.message
    
    def test_validate_supported_formats(self):
        """Test validation of supported formats."""
        # JSON should always be supported
        error = ConfigFormatDetector.validate_format_support(ConfigFormat.JSON)
        assert error is None
        
        # YAML support depends on PyYAML availability
        error = ConfigFormatDetector.validate_format_support(ConfigFormat.YAML)
        # Error should only occur if PyYAML is not available
        # In our test environment, we assume PyYAML is available
    
    def test_check_file_accessibility_nonexistent(self):
        """Test accessibility check for non-existent file."""
        error = ConfigFormatDetector.check_file_accessibility('/nonexistent/file.yaml')
        assert error is not None
        assert error.severity == ValidationSeverity.ERROR
        assert "not found" in error.message
    
    def test_check_file_accessibility_directory(self):
        """Test accessibility check for directory instead of file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            error = ConfigFormatDetector.check_file_accessibility(temp_dir)
            assert error is not None
            assert error.severity == ValidationSeverity.ERROR
            assert "not a file" in error.message
    
    def test_check_file_accessibility_valid(self):
        """Test accessibility check for valid file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('test content')
            f.flush()
            
            error = ConfigFormatDetector.check_file_accessibility(f.name)
            assert error is None
            
            os.unlink(f.name)
    
    def test_validate_file_complete(self):
        """Test complete file validation."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as f:
            f.write('test: value')
            f.flush()
            
            format_type, error = ConfigFormatDetector.validate_file(f.name)
            assert format_type == ConfigFormat.YAML
            assert error is None
            
            os.unlink(f.name)
    
    def test_validate_file_nonexistent(self):
        """Test validation of non-existent file."""
        format_type, error = ConfigFormatDetector.validate_file('/nonexistent/file.yaml')
        assert format_type == ConfigFormat.UNKNOWN
        assert error is not None
        assert "not found" in error.message