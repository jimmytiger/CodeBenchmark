"""
Configuration file parser for evaluation_engine.

This module provides the core parsing functionality for configuration files,
supporting YAML and JSON formats with variable replacement and basic validation.
"""

import json
import os
import re
from typing import Dict, Any, Optional, Set

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .models import (
    EvaluationConfig, 
    TaskConfig, 
    ModelConfig, 
    ConfigMetadata,
    DefaultConfig,
    OutputConfig,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    ConfigFormat
)
from .detector import ConfigFormatDetector


class ConfigParser:
    """Parser for evaluation configuration files."""
    
    def __init__(self):
        """Initialize the configuration parser."""
        self.detector = ConfigFormatDetector()
    
    def parse_config(self, config_path: str) -> EvaluationConfig:
        """
        Parse configuration file and return EvaluationConfig object.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            EvaluationConfig object
            
        Raises:
            ValueError: If configuration is invalid
            FileNotFoundError: If configuration file doesn't exist
            RuntimeError: If parsing fails
        """
        # Validate file first
        detected_format, validation_error = self.detector.validate_file(config_path)
        if validation_error:
            raise ValueError(f"Configuration file validation failed: {validation_error}")
        
        # Load raw configuration data
        try:
            raw_config = self._load_raw_config(config_path, detected_format)
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration file: {e}")
        
        # Process template inheritance and includes
        try:
            processed_config = self.merge_templates(raw_config, config_path)
        except Exception as e:
            raise ValueError(f"Failed to process templates: {e}")
        
        # Resolve variables in the configuration
        try:
            resolved_config = self.resolve_variables(processed_config)
        except Exception as e:
            raise ValueError(f"Failed to resolve variables: {e}")
        
        # Parse into structured configuration
        try:
            return self._parse_raw_config(resolved_config)
        except Exception as e:
            raise ValueError(f"Failed to parse configuration: {e}")
    
    def validate_syntax(self, config_path: str) -> ValidationResult:
        """
        Validate configuration file syntax without full parsing.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            ValidationResult with syntax validation results
        """
        result = ValidationResult(is_valid=True)
        
        # Check file accessibility and format
        detected_format, validation_error = self.detector.validate_file(config_path)
        if validation_error:
            result.add_error(validation_error)
            return result
        
        # Try to load the file to check syntax
        try:
            self._load_raw_config(config_path, detected_format)
        except Exception as e:
            error = ValidationError(
                type="syntax",
                message=f"Syntax error in configuration file: {str(e)}",
                severity=ValidationSeverity.ERROR,
                location=config_path,
                suggestion="Check file syntax and format"
            )
            result.add_error(error)
        
        return result
    
    def resolve_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve variables in configuration using ${variable_name} and ${env:ENV_VAR_NAME} syntax.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Configuration dictionary with resolved variables
            
        Raises:
            ValueError: If circular references are detected or variables cannot be resolved
        """
        # Extract variables section
        variables = config.get('variables', {})
        
        # Create a copy to avoid modifying the original
        resolved_config = self._deep_copy_dict(config)
        
        # Resolve variables in the variables section first
        resolved_variables = self._resolve_variables_dict(variables, variables)
        resolved_config['variables'] = resolved_variables
        
        # Resolve variables in the entire configuration
        resolved_config = self._resolve_variables_recursive(resolved_config, resolved_variables)
        
        return resolved_config
    
    def merge_templates(self, config: Dict[str, Any], config_path: str) -> Dict[str, Any]:
        """
        Process template inheritance and includes in configuration.
        
        Args:
            config: Raw configuration dictionary
            config_path: Path to the current configuration file (for resolving relative paths)
            
        Returns:
            Configuration dictionary with templates merged
            
        Raises:
            ValueError: If template processing fails
        """
        # Create a copy to avoid modifying the original
        merged_config = self._deep_copy_dict(config)
        
        # Process extends (template inheritance)
        if 'extends' in merged_config:
            merged_config = self._process_extends(merged_config, config_path)
        
        # Process includes
        merged_config = self._process_includes(merged_config, config_path)
        
        return merged_config
    
    def _process_extends(self, config: Dict[str, Any], config_path: str) -> Dict[str, Any]:
        """
        Process template inheritance using 'extends' keyword.
        
        Args:
            config: Configuration dictionary with extends directive
            config_path: Path to the current configuration file
            
        Returns:
            Configuration with parent template merged
            
        Raises:
            ValueError: If template inheritance fails
        """
        extends_path = config.pop('extends')  # Remove extends from final config
        
        if not isinstance(extends_path, str):
            raise ValueError("'extends' must be a string path to a template file")
        
        # Resolve relative path
        base_dir = os.path.dirname(config_path)
        template_path = os.path.join(base_dir, extends_path) if not os.path.isabs(extends_path) else extends_path
        
        # Load parent template
        try:
            parent_format, validation_error = self.detector.validate_file(template_path)
            if validation_error:
                raise ValueError(f"Parent template validation failed: {validation_error}")
            
            parent_config = self._load_raw_config(template_path, parent_format)
            
            # Recursively process parent template (in case it also extends something)
            parent_config = self.merge_templates(parent_config, template_path)
            
        except Exception as e:
            raise ValueError(f"Failed to load parent template '{extends_path}': {e}")
        
        # Merge parent and child configurations
        # Child configuration takes precedence over parent
        merged = self._merge_configurations(parent_config, config)
        
        return merged
    
    def _process_includes(self, config: Dict[str, Any], config_path: str) -> Dict[str, Any]:
        """
        Process include directives in configuration.
        
        Args:
            config: Configuration dictionary that may contain include directives
            config_path: Path to the current configuration file
            
        Returns:
            Configuration with includes processed
            
        Raises:
            ValueError: If include processing fails
        """
        # Process includes recursively in the configuration
        return self._process_includes_recursive(config, config_path, set())
    
    def _process_includes_recursive(self, obj: Any, config_path: str, processed_files: Set[str]) -> Any:
        """
        Recursively process include directives in any object.
        
        Args:
            obj: Object to process (dict, list, or other)
            config_path: Path to the current configuration file
            processed_files: Set of already processed files (to prevent circular includes)
            
        Returns:
            Object with includes processed
        """
        if isinstance(obj, dict):
            if 'include' in obj and len(obj) == 1:
                # This is an include directive
                include_path = obj['include']
                return self._process_single_include(include_path, config_path, processed_files)
            else:
                # Process includes in dictionary values
                return {key: self._process_includes_recursive(value, config_path, processed_files) 
                       for key, value in obj.items()}
        elif isinstance(obj, list):
            # Process includes in list items
            result = []
            for item in obj:
                processed_item = self._process_includes_recursive(item, config_path, processed_files)
                if isinstance(processed_item, list):
                    # If include returned a list, extend the result
                    result.extend(processed_item)
                else:
                    result.append(processed_item)
            return result
        else:
            return obj
    
    def _process_single_include(self, include_path: str, config_path: str, processed_files: Set[str]) -> Any:
        """
        Process a single include directive.
        
        Args:
            include_path: Path to the file to include
            config_path: Path to the current configuration file
            processed_files: Set of already processed files
            
        Returns:
            Content of the included file
            
        Raises:
            ValueError: If include processing fails
        """
        if not isinstance(include_path, str):
            raise ValueError("Include path must be a string")
        
        # Resolve relative path
        base_dir = os.path.dirname(config_path)
        full_include_path = os.path.join(base_dir, include_path) if not os.path.isabs(include_path) else include_path
        
        # Normalize path to detect circular includes
        normalized_path = os.path.normpath(full_include_path)
        
        if normalized_path in processed_files:
            raise ValueError(f"Circular include detected: {include_path}")
        
        # Load included file
        try:
            include_format, validation_error = self.detector.validate_file(full_include_path)
            if validation_error:
                raise ValueError(f"Include file validation failed: {validation_error}")
            
            included_config = self._load_raw_config(full_include_path, include_format)
            
            # Add to processed files and recursively process includes in the included file
            new_processed_files = processed_files | {normalized_path}
            included_config = self._process_includes_recursive(included_config, full_include_path, new_processed_files)
            
            return included_config
            
        except Exception as e:
            raise ValueError(f"Failed to include file '{include_path}': {e}")
    
    def _merge_configurations(self, parent: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge parent and child configurations with child taking precedence.
        
        Args:
            parent: Parent configuration dictionary
            child: Child configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        merged = self._deep_copy_dict(parent)
        
        for key, value in child.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                merged[key] = self._merge_configurations(merged[key], value)
            elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
                # For lists, child completely replaces parent (no merging)
                # This is the most predictable behavior for configuration
                merged[key] = value
            else:
                # Child value completely replaces parent value
                merged[key] = value
        
        return merged
    
    def _resolve_variables_dict(self, variables: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve variables within the variables dictionary, handling circular references.
        
        Args:
            variables: Variables dictionary to resolve
            context: Context for variable resolution
            
        Returns:
            Resolved variables dictionary
            
        Raises:
            ValueError: If circular references are detected
        """
        resolved = {}
        resolving = set()  # Track variables currently being resolved
        
        def resolve_variable(var_name: str) -> Any:
            if var_name in resolving:
                raise ValueError(f"Circular reference detected for variable: {var_name}")
            
            if var_name in resolved:
                return resolved[var_name]
            
            if var_name not in variables:
                raise ValueError(f"Variable not found: {var_name}")
            
            var_value = variables[var_name]
            resolving.add(var_name)
            
            try:
                if isinstance(var_value, str):
                    resolved_value = self._resolve_string_variables_with_context(var_value, variables, resolved, resolving, resolve_variable)
                elif isinstance(var_value, dict):
                    resolved_value = self._resolve_variables_recursive_with_context(var_value, variables, resolved, resolving, resolve_variable)
                elif isinstance(var_value, list):
                    resolved_value = [self._resolve_variables_recursive_with_context(item, variables, resolved, resolving, resolve_variable) if isinstance(item, (dict, list)) 
                                    else self._resolve_string_variables_with_context(str(item), variables, resolved, resolving, resolve_variable) if isinstance(item, str)
                                    else item for item in var_value]
                else:
                    resolved_value = var_value
                
                resolved[var_name] = resolved_value
                return resolved_value
            finally:
                resolving.discard(var_name)
        
        # Resolve all variables
        for var_name in variables.keys():
            if var_name not in resolved:
                resolve_variable(var_name)
        
        return resolved
    
    def _resolve_string_variables_with_context(self, text: str, all_variables: Dict[str, Any], resolved_variables: Dict[str, Any], resolving: Set[str], resolve_func) -> str:
        """
        Resolve variables in a string with circular reference detection.
        
        Args:
            text: String containing variable references
            all_variables: All available variables
            resolved_variables: Already resolved variables
            resolving: Set of variables currently being resolved
            resolve_func: Function to resolve a variable by name
            
        Returns:
            String with resolved variables
        """
        # Pattern to match ${variable_name} and ${env:ENV_VAR_NAME}
        pattern = r'\$\{([^}]+)\}'
        
        def replace_variable(match):
            var_ref = match.group(1)
            
            # Handle environment variables
            if var_ref.startswith('env:'):
                env_var_name = var_ref[4:]  # Remove 'env:' prefix
                env_value = os.environ.get(env_var_name)
                if env_value is None:
                    raise ValueError(f"Environment variable not found: {env_var_name}")
                return env_value
            
            # Handle regular variables
            if var_ref in resolved_variables:
                value = resolved_variables[var_ref]
                return str(value) if not isinstance(value, str) else value
            elif var_ref in all_variables:
                # Need to resolve this variable
                value = resolve_func(var_ref)
                return str(value) if not isinstance(value, str) else value
            else:
                raise ValueError(f"Variable not found: {var_ref}")
        
        return re.sub(pattern, replace_variable, text)
    
    def _resolve_variables_recursive_with_context(self, obj: Any, all_variables: Dict[str, Any], resolved_variables: Dict[str, Any], resolving: Set[str], resolve_func) -> Any:
        """
        Recursively resolve variables in any object with circular reference detection.
        
        Args:
            obj: Object to resolve variables in
            all_variables: All available variables
            resolved_variables: Already resolved variables
            resolving: Set of variables currently being resolved
            resolve_func: Function to resolve a variable by name
            
        Returns:
            Object with resolved variables
        """
        if isinstance(obj, str):
            return self._resolve_string_variables_with_context(obj, all_variables, resolved_variables, resolving, resolve_func)
        elif isinstance(obj, dict):
            return {key: self._resolve_variables_recursive_with_context(value, all_variables, resolved_variables, resolving, resolve_func) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_variables_recursive_with_context(item, all_variables, resolved_variables, resolving, resolve_func) for item in obj]
        else:
            return obj
    
    def _resolve_variables_recursive(self, obj: Any, variables: Dict[str, Any]) -> Any:
        """
        Recursively resolve variables in any object (dict, list, string).
        
        Args:
            obj: Object to resolve variables in
            variables: Available variables for resolution
            
        Returns:
            Object with resolved variables
        """
        if isinstance(obj, str):
            return self._resolve_string_variables(obj, variables, variables)
        elif isinstance(obj, dict):
            return {key: self._resolve_variables_recursive(value, variables) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_variables_recursive(item, variables) for item in obj]
        else:
            return obj
    
    def _resolve_string_variables(self, text: str, all_variables: Dict[str, Any], resolved_variables: Dict[str, Any]) -> str:
        """
        Resolve variables in a string using ${variable_name} and ${env:ENV_VAR_NAME} syntax.
        
        Args:
            text: String containing variable references
            all_variables: All available variables (for dependency resolution)
            resolved_variables: Already resolved variables
            
        Returns:
            String with resolved variables
            
        Raises:
            ValueError: If variable cannot be resolved
        """
        # Pattern to match ${variable_name} and ${env:ENV_VAR_NAME}
        pattern = r'\$\{([^}]+)\}'
        
        def replace_variable(match):
            var_ref = match.group(1)
            
            # Handle environment variables
            if var_ref.startswith('env:'):
                env_var_name = var_ref[4:]  # Remove 'env:' prefix
                env_value = os.environ.get(env_var_name)
                if env_value is None:
                    raise ValueError(f"Environment variable not found: {env_var_name}")
                return env_value
            
            # Handle regular variables
            if var_ref in resolved_variables:
                value = resolved_variables[var_ref]
                # Convert non-string values to strings
                return str(value) if not isinstance(value, str) else value
            elif var_ref in all_variables:
                # Variable exists but not yet resolved - this should not happen in proper resolution order
                raise ValueError(f"Variable '{var_ref}' is not yet resolved (possible circular reference)")
            else:
                raise ValueError(f"Variable not found: {var_ref}")
        
        try:
            return re.sub(pattern, replace_variable, text)
        except Exception as e:
            raise ValueError(f"Failed to resolve variables in '{text}': {e}")
    
    def _deep_copy_dict(self, obj: Any) -> Any:
        """
        Create a deep copy of a dictionary or other object.
        
        Args:
            obj: Object to copy
            
        Returns:
            Deep copy of the object
        """
        if isinstance(obj, dict):
            return {key: self._deep_copy_dict(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy_dict(item) for item in obj]
        else:
            return obj
    
    def _load_raw_config(self, config_path: str, format_type: ConfigFormat) -> Dict[str, Any]:
        """
        Load raw configuration data from file.
        
        Args:
            config_path: Path to configuration file
            format_type: Detected configuration format
            
        Returns:
            Raw configuration dictionary
            
        Raises:
            ValueError: If format is not supported
            RuntimeError: If file loading fails
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except IOError as e:
            raise RuntimeError(f"Failed to read configuration file: {e}")
        
        if format_type == ConfigFormat.JSON:
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Invalid JSON syntax: {e}")
        
        elif format_type == ConfigFormat.YAML:
            if not YAML_AVAILABLE:
                raise ValueError("YAML format requires PyYAML to be installed")
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise RuntimeError(f"Invalid YAML syntax: {e}")
        
        else:
            raise ValueError(f"Unsupported configuration format: {format_type}")
    
    def _parse_raw_config(self, raw_config: Dict[str, Any]) -> EvaluationConfig:
        """
        Parse raw configuration dictionary into EvaluationConfig object.
        
        Args:
            raw_config: Raw configuration dictionary
            
        Returns:
            EvaluationConfig object
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Parse metadata (required)
        metadata_data = raw_config.get('metadata', {})
        if not isinstance(metadata_data, dict):
            raise ValueError("'metadata' must be a dictionary")
        
        if 'name' not in metadata_data:
            raise ValueError("'metadata.name' is required")
        
        metadata = ConfigMetadata(**metadata_data)
        
        # Parse tasks (required)
        tasks_data = raw_config.get('tasks', [])
        if not isinstance(tasks_data, list):
            raise ValueError("'tasks' must be a list")
        
        if not tasks_data:
            raise ValueError("At least one task must be defined")
        
        tasks = []
        for i, task_data in enumerate(tasks_data):
            if not isinstance(task_data, dict):
                raise ValueError(f"Task {i} must be a dictionary")
            try:
                task = TaskConfig(**task_data)
                tasks.append(task)
            except TypeError as e:
                raise ValueError(f"Invalid task configuration at index {i}: {e}")
        
        # Parse models (optional)
        models_data = raw_config.get('models', {})
        if not isinstance(models_data, dict):
            raise ValueError("'models' must be a dictionary")
        
        models = {}
        for model_name, model_data in models_data.items():
            if not isinstance(model_data, dict):
                raise ValueError(f"Model '{model_name}' configuration must be a dictionary")
            try:
                # Ensure the model name matches the key
                model_data_copy = model_data.copy()
                model_data_copy['name'] = model_name
                model = ModelConfig(**model_data_copy)
                models[model_name] = model
            except TypeError as e:
                raise ValueError(f"Invalid model configuration for '{model_name}': {e}")
        
        # Parse variables (optional)
        variables = raw_config.get('variables', {})
        if not isinstance(variables, dict):
            raise ValueError("'variables' must be a dictionary")
        
        # Parse defaults (optional)
        defaults = None
        defaults_data = raw_config.get('defaults')
        if defaults_data is not None:
            if not isinstance(defaults_data, dict):
                raise ValueError("'defaults' must be a dictionary")
            try:
                defaults = DefaultConfig(**defaults_data)
            except TypeError as e:
                raise ValueError(f"Invalid defaults configuration: {e}")
        
        # Parse output (optional)
        output = None
        output_data = raw_config.get('output')
        if output_data is not None:
            if not isinstance(output_data, dict):
                raise ValueError("'output' must be a dictionary")
            try:
                output = OutputConfig(**output_data)
            except TypeError as e:
                raise ValueError(f"Invalid output configuration: {e}")
        
        return EvaluationConfig(
            metadata=metadata,
            tasks=tasks,
            models=models,
            variables=variables,
            defaults=defaults,
            output=output
        )