"""
Configuration Parser for Multi-Turn Evaluation

Handles parsing, validation, and template generation for
multi-turn evaluation configuration files.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from pydantic import ValidationError
import logging

from ..core.data_models import MultiTurnConfig, FeedbackConfig, SafetyConfig

logger = logging.getLogger(__name__)


class ConfigParser:
    """
    Configuration parser for multi-turn evaluation.
    
    Implements requirement 9.3: YAML-based configuration parsing.
    """
    
    def __init__(self):
        self.templates = self._create_templates()
    
    def parse_config_file(self, config_path: str) -> Dict[str, Any]:
        """
        Parse configuration file (JSON or YAML).
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Parsed configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file format is invalid
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif config_file.suffix.lower() == '.json':
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
            
            logger.info(f"Successfully parsed configuration from: {config_path}")
            return config_data
            
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"Invalid configuration file format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error reading configuration file: {str(e)}")
    
    def validate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration data.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            Validation result with 'valid' boolean and 'errors' list
        """
        errors = []
        
        # Required fields
        required_fields = ['model_id', 'task_ids']
        for field in required_fields:
            if field not in config_data:
                errors.append(f"Missing required field: {field}")
            elif not config_data[field]:
                errors.append(f"Field cannot be empty: {field}")
        
        # Validate model_id
        if 'model_id' in config_data:
            if not isinstance(config_data['model_id'], str):
                errors.append("model_id must be a string")
        
        # Validate task_ids
        if 'task_ids' in config_data:
            if not isinstance(config_data['task_ids'], list):
                errors.append("task_ids must be a list")
            elif len(config_data['task_ids']) == 0:
                errors.append("task_ids cannot be empty")
            else:
                for i, task_id in enumerate(config_data['task_ids']):
                    if not isinstance(task_id, str):
                        errors.append(f"task_ids[{i}] must be a string")
        
        # Validate optional numeric fields
        numeric_fields = {
            'max_turns': (1, 100),
            'timeout_seconds': (60, 86400),
            'max_feedback_length': (100, 100000),
            'max_context_length': (1000, 200000),
            'top_k_assertions': (1, 20),
            'max_execution_time': (10, 3600)
        }
        
        for field, (min_val, max_val) in numeric_fields.items():
            if field in config_data:
                value = config_data[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"{field} must be a number")
                elif value < min_val or value > max_val:
                    errors.append(f"{field} must be between {min_val} and {max_val}")
        
        # Validate boolean fields
        boolean_fields = [
            'enable_context_retention', 'enable_stack_summarization',
            'enable_file_context', 'enable_sandboxing'
        ]
        
        for field in boolean_fields:
            if field in config_data:
                if not isinstance(config_data[field], bool):
                    errors.append(f"{field} must be a boolean")
        
        # Validate choice fields
        choice_fields = {
            'feedback_strategy': ['full', 'adaptive', 'minimal', 'top_k'],
            'safety_level': ['strict', 'moderate', 'permissive'],
            'context_strategy': ['full', 'adaptive', 'minimal']
        }
        
        for field, choices in choice_fields.items():
            if field in config_data:
                value = config_data[field]
                if not isinstance(value, str):
                    errors.append(f"{field} must be a string")
                elif value not in choices:
                    errors.append(f"{field} must be one of: {', '.join(choices)}")
        
        # Validate list fields
        if 'allowed_tools' in config_data:
            if not isinstance(config_data['allowed_tools'], list):
                errors.append("allowed_tools must be a list")
            else:
                for i, tool in enumerate(config_data['allowed_tools']):
                    if not isinstance(tool, str):
                        errors.append(f"allowed_tools[{i}] must be a string")
        
        if 'dangerous_patterns' in config_data:
            if not isinstance(config_data['dangerous_patterns'], list):
                errors.append("dangerous_patterns must be a list")
            else:
                for i, pattern in enumerate(config_data['dangerous_patterns']):
                    if not isinstance(pattern, str):
                        errors.append(f"dangerous_patterns[{i}] must be a string")
        
        # Validate termination_conditions
        if 'termination_conditions' in config_data:
            valid_conditions = ['success', 'max_turns', 'timeout', 'safety_violation']
            if not isinstance(config_data['termination_conditions'], list):
                errors.append("termination_conditions must be a list")
            else:
                for i, condition in enumerate(config_data['termination_conditions']):
                    if not isinstance(condition, str):
                        errors.append(f"termination_conditions[{i}] must be a string")
                    elif condition not in valid_conditions:
                        errors.append(f"termination_conditions[{i}] must be one of: {', '.join(valid_conditions)}")
        
        # Validate resource_limits
        if 'resource_limits' in config_data:
            if not isinstance(config_data['resource_limits'], dict):
                errors.append("resource_limits must be a dictionary")
        
        # Validate metadata
        if 'metadata' in config_data:
            if not isinstance(config_data['metadata'], dict):
                errors.append("metadata must be a dictionary")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def create_multi_turn_config(self, config_data: Dict[str, Any]) -> MultiTurnConfig:
        """
        Create MultiTurnConfig from configuration data.
        
        Args:
            config_data: Validated configuration dictionary
            
        Returns:
            MultiTurnConfig instance
            
        Raises:
            ValidationError: If configuration is invalid
        """
        try:
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
            
        except Exception as e:
            raise ValidationError(f"Error creating configuration: {str(e)}")
    
    def get_template(self, template_name: str) -> Dict[str, Any]:
        """
        Get configuration template by name.
        
        Args:
            template_name: Template name
            
        Returns:
            Template configuration dictionary
            
        Raises:
            ValueError: If template doesn't exist
        """
        if template_name not in self.templates:
            available = ', '.join(self.templates.keys())
            raise ValueError(f"Template '{template_name}' not found. Available templates: {available}")
        
        return self.templates[template_name].copy()
    
    def _create_templates(self) -> Dict[str, Dict[str, Any]]:
        """Create configuration templates."""
        templates = {}
        
        # Basic template
        templates['basic'] = {
            "model_id": "gpt-4",
            "task_ids": [
                "example_multi_turn_task"
            ],
            "max_turns": 10,
            "timeout_seconds": 3600,
            "feedback_strategy": "adaptive",
            "safety_level": "moderate",
            "enable_context_retention": True,
            "metadata": {
                "description": "Basic multi-turn evaluation",
                "created_by": "user"
            }
        }
        
        # Advanced template
        templates['advanced'] = {
            "model_id": "gpt-4",
            "task_ids": [
                "advanced_multi_turn_task_1",
                "advanced_multi_turn_task_2"
            ],
            "max_turns": 15,
            "timeout_seconds": 7200,
            "feedback_strategy": "adaptive",
            "safety_level": "moderate",
            "enable_context_retention": True,
            "context_strategy": "adaptive",
            "max_feedback_length": 15000,
            "max_context_length": 75000,
            "enable_stack_summarization": True,
            "enable_file_context": True,
            "top_k_assertions": 8,
            "allowed_tools": ["python", "bash", "git", "curl"],
            "enable_sandboxing": True,
            "max_execution_time": 600,
            "termination_conditions": ["success", "max_turns", "timeout", "safety_violation"],
            "resource_limits": {
                "max_memory_mb": 2048,
                "max_cpu_percent": 80,
                "max_disk_mb": 1024
            },
            "metadata": {
                "description": "Advanced multi-turn evaluation with custom settings",
                "created_by": "user",
                "experiment_id": "exp_001"
            }
        }
        
        # SWE-bench template
        templates['swe_bench'] = {
            "model_id": "gpt-4",
            "task_ids": [
                "swe_bench_lite_001",
                "swe_bench_lite_002",
                "swe_bench_lite_003"
            ],
            "max_turns": 20,
            "timeout_seconds": 10800,
            "feedback_strategy": "full",
            "safety_level": "moderate",
            "enable_context_retention": True,
            "context_strategy": "full",
            "max_feedback_length": 20000,
            "max_context_length": 100000,
            "enable_stack_summarization": True,
            "enable_file_context": True,
            "top_k_assertions": 10,
            "allowed_tools": ["python", "bash", "git", "pytest", "pip"],
            "enable_sandboxing": True,
            "max_execution_time": 900,
            "dangerous_patterns": [
                "rm -rf",
                "sudo",
                "chmod 777"
            ],
            "metadata": {
                "description": "SWE-bench evaluation configuration",
                "benchmark": "swe_bench",
                "subset": "lite"
            }
        }
        
        # InterCode template
        templates['intercode'] = {
            "model_id": "gpt-4",
            "task_ids": [
                "intercode_python_001",
                "intercode_bash_001",
                "intercode_sql_001"
            ],
            "max_turns": 12,
            "timeout_seconds": 5400,
            "feedback_strategy": "adaptive",
            "safety_level": "strict",
            "enable_context_retention": True,
            "context_strategy": "adaptive",
            "max_feedback_length": 12000,
            "max_context_length": 60000,
            "enable_stack_summarization": True,
            "enable_file_context": False,
            "top_k_assertions": 5,
            "allowed_tools": ["python", "bash", "sqlite3"],
            "enable_sandboxing": True,
            "max_execution_time": 300,
            "resource_limits": {
                "max_memory_mb": 1024,
                "max_cpu_percent": 60,
                "max_execution_time": 300
            },
            "metadata": {
                "description": "InterCode evaluation configuration",
                "benchmark": "intercode",
                "environments": ["python", "bash", "sql"]
            }
        }
        
        return templates
    
    def export_config(self, config: MultiTurnConfig, output_path: str, format: str = 'yaml'):
        """
        Export MultiTurnConfig to file.
        
        Args:
            config: MultiTurnConfig instance
            output_path: Output file path
            format: Output format ('yaml' or 'json')
        """
        # Convert config to dictionary
        config_dict = {
            "max_turns": config.max_turns,
            "timeout_seconds": config.conversation_timeout,
            "enable_context_retention": config.enable_context_retention,
            "termination_conditions": config.termination_conditions,
            "context_strategy": config.feedback_config.context_strategy,
            "max_feedback_length": config.feedback_config.max_feedback_length,
            "max_context_length": config.feedback_config.max_context_length,
            "enable_stack_summarization": config.feedback_config.enable_stack_summarization,
            "enable_file_context": config.feedback_config.enable_file_context,
            "top_k_assertions": config.feedback_config.top_k_assertions,
            "allowed_tools": config.safety_config.allowed_tools,
            "resource_limits": config.safety_config.resource_limits,
            "dangerous_patterns": config.safety_config.dangerous_patterns,
            "enable_sandboxing": config.safety_config.enable_sandboxing,
            "max_execution_time": config.safety_config.max_execution_time
        }
        
        # Write to file
        output_file = Path(output_path)
        with open(output_file, 'w') as f:
            if format.lower() == 'yaml':
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration exported to: {output_path}")
    
    def merge_configs(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries.
        
        Args:
            base_config: Base configuration
            override_config: Override configuration
            
        Returns:
            Merged configuration dictionary
        """
        merged = base_config.copy()
        
        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                merged[key] = self.merge_configs(merged[key], value)
            else:
                # Override value
                merged[key] = value
        
        return merged