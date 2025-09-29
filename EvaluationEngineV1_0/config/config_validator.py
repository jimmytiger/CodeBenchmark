"""
Configuration Validator for Multi-Turn Evaluation

Provides comprehensive validation for configuration files
with detailed error reporting and schema validation.
"""

import re
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Configuration validator for multi-turn evaluation.
    
    Implements requirement 9.3: Configuration validation and error reporting.
    """
    
    def __init__(self):
        self.validation_rules = self._create_validation_rules()
    
    def validate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration data.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            Validation result with 'valid' boolean, 'errors' list, and 'warnings' list
        """
        errors = []
        warnings = []
        
        # Validate required fields
        errors.extend(self._validate_required_fields(config_data))
        
        # Validate field types
        errors.extend(self._validate_field_types(config_data))
        
        # Validate field values
        errors.extend(self._validate_field_values(config_data))
        
        # Validate field relationships
        errors.extend(self._validate_field_relationships(config_data))
        
        # Generate warnings
        warnings.extend(self._generate_warnings(config_data))
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_task_ids(self, task_ids: List[str]) -> List[str]:
        """
        Validate task IDs format and naming conventions.
        
        Args:
            task_ids: List of task IDs
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not task_ids:
            errors.append("task_ids cannot be empty")
            return errors
        
        # Validate each task ID
        for i, task_id in enumerate(task_ids):
            if not isinstance(task_id, str):
                errors.append(f"task_ids[{i}] must be a string")
                continue
            
            if not task_id.strip():
                errors.append(f"task_ids[{i}] cannot be empty or whitespace")
                continue
            
            # Validate task ID format (alphanumeric, underscores, hyphens)
            if not re.match(r'^[a-zA-Z0-9_-]+$', task_id):
                errors.append(f"task_ids[{i}] '{task_id}' contains invalid characters. Use only letters, numbers, underscores, and hyphens")
            
            # Check length
            if len(task_id) > 100:
                errors.append(f"task_ids[{i}] '{task_id}' is too long (max 100 characters)")
            
            if len(task_id) < 3:
                errors.append(f"task_ids[{i}] '{task_id}' is too short (min 3 characters)")
        
        # Check for duplicates
        if len(task_ids) != len(set(task_ids)):
            duplicates = [task_id for task_id in task_ids if task_ids.count(task_id) > 1]
            errors.append(f"Duplicate task IDs found: {list(set(duplicates))}")
        
        return errors
    
    def validate_model_id(self, model_id: str) -> List[str]:
        """
        Validate model ID format.
        
        Args:
            model_id: Model identifier
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not isinstance(model_id, str):
            errors.append("model_id must be a string")
            return errors
        
        if not model_id.strip():
            errors.append("model_id cannot be empty or whitespace")
            return errors
        
        # Validate model ID format
        if not re.match(r'^[a-zA-Z0-9._-]+$', model_id):
            errors.append("model_id contains invalid characters. Use only letters, numbers, dots, underscores, and hyphens")
        
        # Check length
        if len(model_id) > 100:
            errors.append("model_id is too long (max 100 characters)")
        
        if len(model_id) < 2:
            errors.append("model_id is too short (min 2 characters)")
        
        return errors
    
    def validate_resource_limits(self, resource_limits: Dict[str, Any]) -> List[str]:
        """
        Validate resource limits configuration.
        
        Args:
            resource_limits: Resource limits dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not isinstance(resource_limits, dict):
            errors.append("resource_limits must be a dictionary")
            return errors
        
        # Define valid resource limit keys and their validation rules
        valid_limits = {
            'max_memory_mb': (int, 1, 32768),  # 1MB to 32GB
            'max_cpu_percent': (int, 1, 100),
            'max_disk_mb': (int, 1, 102400),  # 1MB to 100GB
            'max_network_requests': (int, 0, 10000),
            'max_file_descriptors': (int, 1, 10000),
            'max_processes': (int, 1, 1000)
        }
        
        for key, value in resource_limits.items():
            if key not in valid_limits:
                errors.append(f"Unknown resource limit: {key}")
                continue
            
            expected_type, min_val, max_val = valid_limits[key]
            
            if not isinstance(value, expected_type):
                errors.append(f"resource_limits.{key} must be a {expected_type.__name__}")
                continue
            
            if value < min_val or value > max_val:
                errors.append(f"resource_limits.{key} must be between {min_val} and {max_val}")
        
        return errors
    
    def validate_dangerous_patterns(self, patterns: List[str]) -> List[str]:
        """
        Validate dangerous command patterns.
        
        Args:
            patterns: List of dangerous patterns
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not isinstance(patterns, list):
            errors.append("dangerous_patterns must be a list")
            return errors
        
        for i, pattern in enumerate(patterns):
            if not isinstance(pattern, str):
                errors.append(f"dangerous_patterns[{i}] must be a string")
                continue
            
            if not pattern.strip():
                errors.append(f"dangerous_patterns[{i}] cannot be empty or whitespace")
                continue
            
            # Try to compile as regex to check validity
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"dangerous_patterns[{i}] is not a valid regex pattern: {str(e)}")
        
        return errors
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """
        Validate metadata dictionary.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not isinstance(metadata, dict):
            errors.append("metadata must be a dictionary")
            return errors
        
        # Check for reserved keys
        reserved_keys = ['_internal', '_system', '_config']
        for key in metadata:
            if key.startswith('_') and key in reserved_keys:
                errors.append(f"metadata key '{key}' is reserved")
        
        # Validate key format
        for key in metadata:
            if not isinstance(key, str):
                errors.append(f"metadata key must be a string, got {type(key)}")
                continue
            
            if not re.match(r'^[a-zA-Z0-9_-]+$', key):
                errors.append(f"metadata key '{key}' contains invalid characters")
        
        # Check nesting depth (max 3 levels)
        def check_depth(obj, current_depth=0):
            if current_depth > 3:
                return ["metadata nesting too deep (max 3 levels)"]
            
            if isinstance(obj, dict):
                for value in obj.values():
                    result = check_depth(value, current_depth + 1)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = check_depth(item, current_depth + 1)
                    if result:
                        return result
            
            return []
        
        errors.extend(check_depth(metadata))
        
        return errors
    
    def _create_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Create validation rules for configuration fields."""
        return {
            'model_id': {
                'type': str,
                'required': True,
                'validator': self.validate_model_id
            },
            'task_ids': {
                'type': list,
                'required': True,
                'validator': self.validate_task_ids
            },
            'max_turns': {
                'type': int,
                'required': False,
                'min': 1,
                'max': 100,
                'default': 10
            },
            'timeout_seconds': {
                'type': int,
                'required': False,
                'min': 60,
                'max': 86400,
                'default': 3600
            },
            'feedback_strategy': {
                'type': str,
                'required': False,
                'choices': ['full', 'adaptive', 'minimal', 'top_k'],
                'default': 'adaptive'
            },
            'safety_level': {
                'type': str,
                'required': False,
                'choices': ['strict', 'moderate', 'permissive'],
                'default': 'moderate'
            },
            'enable_context_retention': {
                'type': bool,
                'required': False,
                'default': True
            },
            'context_strategy': {
                'type': str,
                'required': False,
                'choices': ['full', 'adaptive', 'minimal'],
                'default': 'adaptive'
            },
            'max_feedback_length': {
                'type': int,
                'required': False,
                'min': 100,
                'max': 100000,
                'default': 10000
            },
            'max_context_length': {
                'type': int,
                'required': False,
                'min': 1000,
                'max': 200000,
                'default': 50000
            },
            'enable_stack_summarization': {
                'type': bool,
                'required': False,
                'default': True
            },
            'enable_file_context': {
                'type': bool,
                'required': False,
                'default': True
            },
            'top_k_assertions': {
                'type': int,
                'required': False,
                'min': 1,
                'max': 20,
                'default': 5
            },
            'allowed_tools': {
                'type': list,
                'required': False,
                'default': ['python', 'bash', 'git']
            },
            'resource_limits': {
                'type': dict,
                'required': False,
                'validator': self.validate_resource_limits
            },
            'dangerous_patterns': {
                'type': list,
                'required': False,
                'validator': self.validate_dangerous_patterns
            },
            'enable_sandboxing': {
                'type': bool,
                'required': False,
                'default': True
            },
            'max_execution_time': {
                'type': int,
                'required': False,
                'min': 10,
                'max': 3600,
                'default': 300
            },
            'termination_conditions': {
                'type': list,
                'required': False,
                'choices': ['success', 'max_turns', 'timeout', 'safety_violation'],
                'default': ['success', 'max_turns', 'timeout', 'safety_violation']
            },
            'metadata': {
                'type': dict,
                'required': False,
                'validator': self.validate_metadata
            }
        }
    
    def _validate_required_fields(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate required fields."""
        errors = []
        
        for field, rules in self.validation_rules.items():
            if rules.get('required', False) and field not in config_data:
                errors.append(f"Missing required field: {field}")
            elif field in config_data and not config_data[field]:
                if rules.get('required', False):
                    errors.append(f"Required field cannot be empty: {field}")
        
        return errors
    
    def _validate_field_types(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate field types."""
        errors = []
        
        for field, value in config_data.items():
            if field in self.validation_rules:
                expected_type = self.validation_rules[field]['type']
                if not isinstance(value, expected_type):
                    errors.append(f"{field} must be a {expected_type.__name__}, got {type(value).__name__}")
        
        return errors
    
    def _validate_field_values(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate field values."""
        errors = []
        
        for field, value in config_data.items():
            if field not in self.validation_rules:
                continue
            
            rules = self.validation_rules[field]
            
            # Check choices
            if 'choices' in rules:
                if isinstance(value, list):
                    for item in value:
                        if item not in rules['choices']:
                            errors.append(f"{field} item '{item}' must be one of: {', '.join(rules['choices'])}")
                elif value not in rules['choices']:
                    errors.append(f"{field} must be one of: {', '.join(rules['choices'])}")
            
            # Check numeric ranges
            if isinstance(value, (int, float)):
                if 'min' in rules and value < rules['min']:
                    errors.append(f"{field} must be >= {rules['min']}")
                if 'max' in rules and value > rules['max']:
                    errors.append(f"{field} must be <= {rules['max']}")
            
            # Check list constraints
            if isinstance(value, list):
                if 'min_items' in rules and len(value) < rules['min_items']:
                    errors.append(f"{field} must have at least {rules['min_items']} items")
                if 'max_items' in rules and len(value) > rules['max_items']:
                    errors.append(f"{field} must have at most {rules['max_items']} items")
            
            # Run custom validator
            if 'validator' in rules:
                validator_errors = rules['validator'](value)
                errors.extend(validator_errors)
        
        return errors
    
    def _validate_field_relationships(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate relationships between fields."""
        errors = []
        
        # Validate feedback strategy and related fields
        feedback_strategy = config_data.get('feedback_strategy', 'adaptive')
        if feedback_strategy == 'top_k':
            if 'top_k_assertions' not in config_data:
                errors.append("top_k_assertions is required when feedback_strategy is 'top_k'")
        
        # Validate safety level and allowed tools
        safety_level = config_data.get('safety_level', 'moderate')
        allowed_tools = config_data.get('allowed_tools', [])
        
        if safety_level == 'strict':
            dangerous_tools = ['rm', 'sudo', 'chmod', 'chown']
            for tool in allowed_tools:
                if any(dangerous in tool for dangerous in dangerous_tools):
                    errors.append(f"Tool '{tool}' not allowed with strict safety level")
        
        # Validate timeout and max_turns relationship
        timeout_seconds = config_data.get('timeout_seconds', 3600)
        max_turns = config_data.get('max_turns', 10)
        max_execution_time = config_data.get('max_execution_time', 300)
        
        if max_turns * max_execution_time > timeout_seconds:
            errors.append(f"Total possible execution time ({max_turns * max_execution_time}s) exceeds timeout ({timeout_seconds}s)")
        
        # Validate context lengths
        max_feedback_length = config_data.get('max_feedback_length', 10000)
        max_context_length = config_data.get('max_context_length', 50000)
        
        if max_feedback_length > max_context_length:
            errors.append("max_feedback_length cannot be greater than max_context_length")
        
        return errors
    
    def _generate_warnings(self, config_data: Dict[str, Any]) -> List[str]:
        """Generate warnings for potentially problematic configurations."""
        warnings = []
        
        # Check for high resource usage
        max_turns = config_data.get('max_turns', 10)
        if max_turns > 50:
            warnings.append(f"High max_turns ({max_turns}) may result in long evaluation times")
        
        timeout_seconds = config_data.get('timeout_seconds', 3600)
        if timeout_seconds > 7200:  # 2 hours
            warnings.append(f"Long timeout ({timeout_seconds}s) may tie up resources")
        
        # Check for permissive safety settings
        safety_level = config_data.get('safety_level', 'moderate')
        if safety_level == 'permissive':
            warnings.append("Permissive safety level may allow dangerous operations")
        
        enable_sandboxing = config_data.get('enable_sandboxing', True)
        if not enable_sandboxing:
            warnings.append("Disabled sandboxing increases security risks")
        
        # Check for large context sizes
        max_context_length = config_data.get('max_context_length', 50000)
        if max_context_length > 100000:
            warnings.append(f"Large max_context_length ({max_context_length}) may impact performance")
        
        # Check for empty allowed tools
        allowed_tools = config_data.get('allowed_tools', [])
        if not allowed_tools:
            warnings.append("Empty allowed_tools list may prevent task execution")
        
        return warnings