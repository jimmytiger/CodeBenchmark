"""
Configuration file format detection utilities.

This module provides functionality to detect and validate configuration
file formats (YAML, JSON) based on file extensions and content analysis.
"""

import os
import json
from pathlib import Path
from typing import Optional, Tuple

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .models import ConfigFormat, ValidationError, ValidationSeverity


class ConfigFormatDetector:
    """Detects and validates configuration file formats."""
    
    @staticmethod
    def detect_format(file_path: str) -> ConfigFormat:
        """
        Detect configuration file format based on extension and content.
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            ConfigFormat enum indicating the detected format
        """
        if not os.path.exists(file_path):
            return ConfigFormat.UNKNOWN
            
        # First try to detect by file extension
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension in ['.yaml', '.yml']:
            return ConfigFormat.YAML
        elif extension in ['.json']:
            return ConfigFormat.JSON
        
        # If extension is ambiguous, try content-based detection
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Try JSON first (stricter format)
            if content.startswith('{') and content.endswith('}'):
                try:
                    json.loads(content)
                    return ConfigFormat.JSON
                except json.JSONDecodeError:
                    pass
            
            # Try YAML if available - but be more strict about what we consider YAML
            if YAML_AVAILABLE:
                try:
                    parsed = yaml.safe_load(content)
                    # Only consider it YAML if it parses to a dict (configuration-like)
                    # or if it contains YAML-specific syntax
                    if isinstance(parsed, dict) or ':' in content:
                        return ConfigFormat.YAML
                except yaml.YAMLError:
                    pass
                    
        except (IOError, UnicodeDecodeError):
            pass
            
        return ConfigFormat.UNKNOWN
    
    @staticmethod
    def validate_format_support(format_type: ConfigFormat) -> ValidationError:
        """
        Validate that the detected format is supported.
        
        Args:
            format_type: The detected configuration format
            
        Returns:
            ValidationError if format is not supported, None otherwise
        """
        if format_type == ConfigFormat.UNKNOWN:
            return ValidationError(
                type="syntax",
                message="Unable to detect configuration file format",
                severity=ValidationSeverity.ERROR,
                suggestion="Ensure file has .yaml, .yml, or .json extension and valid syntax"
            )
        
        if format_type == ConfigFormat.YAML and not YAML_AVAILABLE:
            return ValidationError(
                type="syntax", 
                message="YAML format detected but PyYAML is not installed",
                severity=ValidationSeverity.ERROR,
                suggestion="Install PyYAML: pip install PyYAML"
            )
        
        return None
    
    @staticmethod
    def check_file_accessibility(file_path: str) -> Optional[ValidationError]:
        """
        Check if configuration file exists and is readable.
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            ValidationError if file is not accessible, None otherwise
        """
        if not os.path.exists(file_path):
            return ValidationError(
                type="syntax",
                message=f"Configuration file not found: {file_path}",
                severity=ValidationSeverity.ERROR,
                suggestion="Check the file path and ensure the file exists"
            )
        
        if not os.path.isfile(file_path):
            return ValidationError(
                type="syntax",
                message=f"Path is not a file: {file_path}",
                severity=ValidationSeverity.ERROR,
                suggestion="Provide a path to a configuration file, not a directory"
            )
        
        if not os.access(file_path, os.R_OK):
            return ValidationError(
                type="syntax",
                message=f"Configuration file is not readable: {file_path}",
                severity=ValidationSeverity.ERROR,
                suggestion="Check file permissions and ensure read access"
            )
        
        return None
    
    @classmethod
    def validate_file(cls, file_path: str) -> Tuple[ConfigFormat, Optional[ValidationError]]:
        """
        Comprehensive validation of configuration file.
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            Tuple of (detected_format, validation_error)
            validation_error is None if file is valid
        """
        # Check file accessibility first
        access_error = cls.check_file_accessibility(file_path)
        if access_error:
            return ConfigFormat.UNKNOWN, access_error
        
        # Detect format
        detected_format = cls.detect_format(file_path)
        
        # Validate format support
        format_error = cls.validate_format_support(detected_format)
        if format_error:
            return detected_format, format_error
        
        return detected_format, None