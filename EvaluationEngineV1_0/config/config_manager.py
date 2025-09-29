"""
Configuration Manager for Multi-Turn Evaluation

Centralized configuration management with support for multiple
file formats, environment variables, and configuration merging.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict
import logging

from .config_validator import ConfigValidator
from ..core.data_models import MultiTurnConfig, FeedbackConfig, SafetyConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Configuration manager for multi-turn evaluation.
    
    Implements requirement 9.3: YAML-based configuration parsing and validation.
    """
    
    def __init__(self):
        self.validator = ConfigValidator()
        self.config_cache: Dict[str, Dict[str, Any]] = {}
        self.environment_prefix = "MULTI_TURN_"
    
    def load_config(self, config_path: Union[str, Path], 
                   validate: bool = True, 
                   use_cache: bool = True) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            validate: Whether to validate configuration
            use_cache: Whether to use cached configuration
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        config_path = Path(config_path)
        cache_key = str(config_path.absolute())
        
        # Check cache
        if use_cache and cache_key in self.config_cache:
            logger.debug(f"Using cached configuration: {config_path}")
            return self.config_cache[cache_key].copy()
        
        # Load configuration
        config_data = self._load_config_file(config_path)
        
        # Apply environment variable overrides
        config_data = self._apply_environment_overrides(config_data)
        
        # Validate configuration
        if validate:
            validation_result = self.validator.validate_config(config_data)
            if not validation_result['valid']:
                error_msg = "Configuration validation failed:\n" + "\n".join(validation_result['errors'])
                raise ValueError(error_msg)
        
        # Cache configuration
        if use_cache:
            self.config_cache[cache_key] = config_data.copy()
        
        logger.info(f"Successfully loaded configuration: {config_path}")
        return config_data
    
    def save_config(self, config_data: Dict[str, Any], 
                   output_path: Union[str, Path], 
                   format: str = 'yaml') -> None:
        """
        Save configuration to file.
        
        Args:
            config_data: Configuration dictionary
            output_path: Output file path
            format: Output format ('yaml' or 'json')
        """
        output_path = Path(output_path)
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write configuration
        with open(output_path, 'w') as f:
            if format.lower() == 'yaml':
                yaml.dump(config_data, f, default_flow_style=False, indent=2, sort_keys=False)
            elif format.lower() == 'json':
                json.dump(config_data, f, indent=2, sort_keys=False)
            else:
                raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Configuration saved to: {output_path}")
    
    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple configuration dictionaries.
        
        Args:
            *configs: Configuration dictionaries to merge
            
        Returns:
            Merged configuration dictionary
        """
        if not configs:
            return {}
        
        merged = configs[0].copy()
        
        for config in configs[1:]:
            merged = self._deep_merge(merged, config)
        
        return merged
    
    def create_multi_turn_config(self, config_data: Dict[str, Any]) -> MultiTurnConfig:
        """
        Create MultiTurnConfig from configuration data.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            MultiTurnConfig instance
        """
        # Create feedback configuration
        feedback_config = FeedbackConfig(
            max_feedback_length=config_data.get('max_feedback_length', 10000),
            context_strategy=config_data.get('context_strategy', 'adaptive'),
            max_context_length=config_data.get('max_context_length', 50000),
            enable_stack_summarization=config_data.get('enable_stack_summarization', True),
            enable_file_context=config_data.get('enable_file_context', True),
            top_k_assertions=config_data.get('top_k_assertions', 5)
        )
        
        # Create safety configuration
        safety_config = SafetyConfig(
            allowed_tools=config_data.get('allowed_tools', ['python', 'bash', 'git']),
            resource_limits=config_data.get('resource_limits', {}),
            dangerous_patterns=config_data.get('dangerous_patterns', []),
            enable_sandboxing=config_data.get('enable_sandboxing', True),
            max_execution_time=config_data.get('max_execution_time', 300)
        )
        
        # Create multi-turn configuration
        multi_turn_config = MultiTurnConfig(
            max_turns=config_data.get('max_turns', 10),
            conversation_timeout=config_data.get('timeout_seconds', 3600),
            enable_context_retention=config_data.get('enable_context_retention', True),
            termination_conditions=config_data.get('termination_conditions', 
                                                  ['success', 'max_turns', 'timeout', 'safety_violation']),
            feedback_config=feedback_config,
            safety_config=safety_config
        )
        
        return multi_turn_config
    
    def config_to_dict(self, config: MultiTurnConfig) -> Dict[str, Any]:
        """
        Convert MultiTurnConfig to dictionary.
        
        Args:
            config: MultiTurnConfig instance
            
        Returns:
            Configuration dictionary
        """
        return {
            'max_turns': config.max_turns,
            'timeout_seconds': config.conversation_timeout,
            'enable_context_retention': config.enable_context_retention,
            'termination_conditions': config.termination_conditions,
            'max_feedback_length': config.feedback_config.max_feedback_length,
            'context_strategy': config.feedback_config.context_strategy,
            'max_context_length': config.feedback_config.max_context_length,
            'enable_stack_summarization': config.feedback_config.enable_stack_summarization,
            'enable_file_context': config.feedback_config.enable_file_context,
            'top_k_assertions': config.feedback_config.top_k_assertions,
            'allowed_tools': config.safety_config.allowed_tools,
            'resource_limits': config.safety_config.resource_limits,
            'dangerous_patterns': config.safety_config.dangerous_patterns,
            'enable_sandboxing': config.safety_config.enable_sandboxing,
            'max_execution_time': config.safety_config.max_execution_time
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema for documentation/validation.
        
        Returns:
            Configuration schema dictionary
        """
        return {
            "type": "object",
            "required": ["model_id", "task_ids"],
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": "Model identifier to evaluate"
                },
                "task_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "description": "List of task IDs to execute"
                },
                "max_turns": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10,
                    "description": "Maximum number of turns per task"
                },
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 60,
                    "maximum": 86400,
                    "default": 3600,
                    "description": "Evaluation timeout in seconds"
                },
                "feedback_strategy": {
                    "type": "string",
                    "enum": ["full", "adaptive", "minimal", "top_k"],
                    "default": "adaptive",
                    "description": "Feedback processing strategy"
                },
                "safety_level": {
                    "type": "string",
                    "enum": ["strict", "moderate", "permissive"],
                    "default": "moderate",
                    "description": "Safety enforcement level"
                },
                "enable_context_retention": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable context retention between turns"
                },
                "context_strategy": {
                    "type": "string",
                    "enum": ["full", "adaptive", "minimal"],
                    "default": "adaptive",
                    "description": "Context management strategy"
                },
                "max_feedback_length": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 100000,
                    "default": 10000,
                    "description": "Maximum feedback length in characters"
                },
                "max_context_length": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 200000,
                    "default": 50000,
                    "description": "Maximum context length in characters"
                },
                "enable_stack_summarization": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable stack trace summarization"
                },
                "enable_file_context": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable file context extraction"
                },
                "top_k_assertions": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                    "description": "Number of top assertions to include"
                },
                "allowed_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["python", "bash", "git"],
                    "description": "List of allowed tools"
                },
                "resource_limits": {
                    "type": "object",
                    "description": "Resource limits configuration"
                },
                "dangerous_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": "List of dangerous command patterns"
                },
                "enable_sandboxing": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable execution sandboxing"
                },
                "max_execution_time": {
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 3600,
                    "default": 300,
                    "description": "Maximum execution time per action in seconds"
                },
                "termination_conditions": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["success", "max_turns", "timeout", "safety_violation"]
                    },
                    "default": ["success", "max_turns", "timeout", "safety_violation"],
                    "description": "List of termination conditions"
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata"
                }
            }
        }
    
    def clear_cache(self) -> None:
        """Clear configuration cache."""
        self.config_cache.clear()
        logger.debug("Configuration cache cleared")
    
    def _load_config_file(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    # Try to detect format by content
                    content = f.read()
                    try:
                        config_data = json.loads(content)
                    except json.JSONDecodeError:
                        try:
                            config_data = yaml.safe_load(content)
                        except yaml.YAMLError:
                            raise ValueError("Unable to parse configuration file as JSON or YAML")
            
            if not isinstance(config_data, dict):
                raise ValueError("Configuration file must contain a dictionary/object")
            
            return config_data
            
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"Invalid configuration file format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error reading configuration file: {str(e)}")
    
    def _apply_environment_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        config_copy = config_data.copy()
        
        # Define environment variable mappings
        env_mappings = {
            f"{self.environment_prefix}MODEL_ID": "model_id",
            f"{self.environment_prefix}MAX_TURNS": ("max_turns", int),
            f"{self.environment_prefix}TIMEOUT_SECONDS": ("timeout_seconds", int),
            f"{self.environment_prefix}FEEDBACK_STRATEGY": "feedback_strategy",
            f"{self.environment_prefix}SAFETY_LEVEL": "safety_level",
            f"{self.environment_prefix}ENABLE_CONTEXT_RETENTION": ("enable_context_retention", lambda x: x.lower() == 'true'),
            f"{self.environment_prefix}MAX_FEEDBACK_LENGTH": ("max_feedback_length", int),
            f"{self.environment_prefix}MAX_CONTEXT_LENGTH": ("max_context_length", int),
            f"{self.environment_prefix}ENABLE_SANDBOXING": ("enable_sandboxing", lambda x: x.lower() == 'true'),
            f"{self.environment_prefix}MAX_EXECUTION_TIME": ("max_execution_time", int)
        }
        
        # Apply overrides
        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if isinstance(config_key, tuple):
                    key, converter = config_key
                    try:
                        config_copy[key] = converter(env_value)
                        logger.debug(f"Applied environment override: {env_var} -> {key} = {config_copy[key]}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to apply environment override {env_var}: {str(e)}")
                else:
                    config_copy[config_key] = env_value
                    logger.debug(f"Applied environment override: {env_var} -> {config_key} = {env_value}")
        
        # Handle list environment variables
        task_ids_env = os.getenv(f"{self.environment_prefix}TASK_IDS")
        if task_ids_env:
            config_copy["task_ids"] = [task.strip() for task in task_ids_env.split(",")]
            logger.debug(f"Applied environment override: task_ids = {config_copy['task_ids']}")
        
        allowed_tools_env = os.getenv(f"{self.environment_prefix}ALLOWED_TOOLS")
        if allowed_tools_env:
            config_copy["allowed_tools"] = [tool.strip() for tool in allowed_tools_env.split(",")]
            logger.debug(f"Applied environment override: allowed_tools = {config_copy['allowed_tools']}")
        
        return config_copy
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        merged = base.copy()
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        
        return merged