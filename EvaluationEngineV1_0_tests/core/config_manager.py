"""
Configuration management for the testing framework.
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import asdict

from models.test_models import (
    TestConfiguration, CLITestConfig, APITestConfig, 
    AdapterTestConfig, ReportConfig, TestType, AdapterType
)
from .error_handler import ConfigurationError


class ConfigManager:
    """Manages configuration loading, validation, and defaults."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent.parent / "configs"
        self.logger = logging.getLogger(f"{__name__}.ConfigManager")
        self._ensure_config_dir()
    
    def _ensure_config_dir(self) -> None:
        """Ensure configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {config_path}",
                config_path=str(config_path)
            )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    config = json.load(f)
                else:
                    raise ConfigurationError(
                        f"Unsupported configuration file format: {config_path.suffix}",
                        config_path=str(config_path)
                    )
            
            self.logger.info(f"Loaded configuration from {config_path}")
            return config
        
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ConfigurationError(
                f"Failed to parse configuration file: {e}",
                config_path=str(config_path)
            )
        except Exception as e:
            raise ConfigurationError(
                f"Error loading configuration: {e}",
                config_path=str(config_path)
            )
    
    def save_config(self, config: Dict[str, Any], config_path: Union[str, Path]) -> None:
        """Save configuration to file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config, f, default_flow_style=False, indent=2)
                elif config_path.suffix.lower() == '.json':
                    json.dump(config, f, indent=2)
                else:
                    raise ConfigurationError(
                        f"Unsupported configuration file format: {config_path.suffix}",
                        config_path=str(config_path)
                    )
            
            self.logger.info(f"Saved configuration to {config_path}")
        
        except Exception as e:
            raise ConfigurationError(
                f"Error saving configuration: {e}",
                config_path=str(config_path)
            )
    
    def validate_config(self, config: Dict[str, Any], 
                       config_type: str = "general") -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if config_type == "cli":
            errors.extend(self._validate_cli_config(config))
        elif config_type == "api":
            errors.extend(self._validate_api_config(config))
        elif config_type == "adapter":
            errors.extend(self._validate_adapter_config(config))
        elif config_type == "test":
            errors.extend(self._validate_test_config(config))
        else:
            errors.extend(self._validate_general_config(config))
        
        return errors
    
    def _validate_general_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate general configuration."""
        errors = []
        
        # Check required fields
        required_fields = ["test_type", "name"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate test_type
        if "test_type" in config:
            try:
                TestType(config["test_type"])
            except ValueError:
                valid_types = [t.value for t in TestType]
                errors.append(f"Invalid test_type. Must be one of: {valid_types}")
        
        # Validate timeout
        if "timeout" in config:
            if not isinstance(config["timeout"], int) or config["timeout"] <= 0:
                errors.append("timeout must be a positive integer")
        
        return errors
    
    def _validate_cli_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate CLI configuration."""
        errors = []
        
        # Validate adapters
        if "adapters" in config:
            for adapter in config["adapters"]:
                try:
                    AdapterType(adapter)
                except ValueError:
                    valid_adapters = [a.value for a in AdapterType]
                    errors.append(f"Invalid adapter '{adapter}'. Must be one of: {valid_adapters}")
        
        # Validate output format
        if "output_format" in config:
            valid_formats = ["json", "yaml", "csv", "table"]
            if config["output_format"] not in valid_formats:
                errors.append(f"Invalid output_format. Must be one of: {valid_formats}")
        
        # Validate custom_task_dir
        if "custom_task_dir" in config:
            task_dir = Path(config["custom_task_dir"])
            if not task_dir.exists():
                errors.append(f"custom_task_dir does not exist: {task_dir}")
        
        return errors
    
    def _validate_api_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate API configuration."""
        errors = []
        
        # Validate port
        if "server_port" in config:
            port = config["server_port"]
            if not isinstance(port, int) or not (1 <= port <= 65535):
                errors.append("server_port must be an integer between 1 and 65535")
        
        # Validate concurrent_requests
        if "concurrent_requests" in config:
            concurrent = config["concurrent_requests"]
            if not isinstance(concurrent, int) or concurrent <= 0:
                errors.append("concurrent_requests must be a positive integer")
        
        return errors
    
    def _validate_adapter_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate adapter configuration."""
        errors = []
        
        # Validate adapter_type
        if "adapter_type" in config:
            try:
                AdapterType(config["adapter_type"])
            except ValueError:
                valid_types = [a.value for a in AdapterType]
                errors.append(f"Invalid adapter_type. Must be one of: {valid_types}")
        
        # Validate test_task_count
        if "test_task_count" in config:
            count = config["test_task_count"]
            if not isinstance(count, int) or count <= 0:
                errors.append("test_task_count must be a positive integer")
        
        return errors
    
    def _validate_test_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate test configuration."""
        errors = []
        
        # Validate test_id
        if "test_id" not in config or not config["test_id"]:
            errors.append("test_id is required and cannot be empty")
        
        # Validate name
        if "name" not in config or not config["name"]:
            errors.append("name is required and cannot be empty")
        
        return errors
    
    def create_default_config(self, config_type: str) -> Dict[str, Any]:
        """Create default configuration for specified type."""
        if config_type == "cli":
            return self._create_default_cli_config()
        elif config_type == "api":
            return self._create_default_api_config()
        elif config_type == "adapter":
            return self._create_default_adapter_config()
        elif config_type == "test":
            return self._create_default_test_config()
        else:
            return self._create_default_general_config()
    
    def _create_default_general_config(self) -> Dict[str, Any]:
        """Create default general configuration."""
        return {
            "test_type": "pipeline",
            "name": "Default Test Configuration",
            "description": "Default configuration for testing framework",
            "timeout": 300,
            "retry_count": 0,
            "real_execution_required": True,
            "execution_params": {
                "verbose": False,
                "parallel": False
            },
            "output_config": {
                "format": "json",
                "include_logs": True,
                "include_artifacts": True
            }
        }
    
    def _create_default_cli_config(self) -> Dict[str, Any]:
        """Create default CLI configuration."""
        return {
            "tasks": [],
            "adapters": ["lm_eval"],
            "execution_timeout": 300,
            "output_format": "json",
            "verbose": False,
            "parallel_execution": False,
            "max_workers": 4
        }
    
    def _create_default_api_config(self) -> Dict[str, Any]:
        """Create default API configuration."""
        return {
            "server_host": "localhost",
            "server_port": 8000,
            "test_endpoints": [
                "/api/v1/evaluations",
                "/api/v1/tasks",
                "/api/v1/adapters"
            ],
            "concurrent_requests": 5,
            "timeout": 30,
            "ssl_verify": True
        }
    
    def _create_default_adapter_config(self) -> Dict[str, Any]:
        """Create default adapter configuration."""
        return {
            "adapter_name": "lm_eval",
            "adapter_type": "lm_eval",
            "test_task_count": 1,
            "dependency_check": True,
            "performance_benchmark": True,
            "installation_timeout": 600,
            "test_timeout": 300,
            "real_execution_only": True
        }
    
    def _create_default_test_config(self) -> Dict[str, Any]:
        """Create default test configuration."""
        return {
            "test_id": "default_test",
            "test_type": "integration",
            "name": "Default Integration Test",
            "description": "Default integration test configuration",
            "target_adapters": ["lm_eval"],
            "task_selection": {
                "count": 1,
                "type": "builtin"
            },
            "execution_params": {
                "timeout": 300,
                "verbose": False
            },
            "output_config": {
                "format": "json",
                "save_artifacts": True
            }
        }
    
    def create_config_from_dataclass(self, config_obj: Union[
        TestConfiguration, CLITestConfig, APITestConfig, 
        AdapterTestConfig, ReportConfig
    ]) -> Dict[str, Any]:
        """Convert dataclass configuration to dictionary."""
        return asdict(config_obj)
    
    def create_dataclass_from_config(self, config: Dict[str, Any], 
                                   config_class: type) -> Any:
        """Create dataclass from configuration dictionary."""
        try:
            return config_class(**config)
        except TypeError as e:
            raise ConfigurationError(
                f"Failed to create {config_class.__name__} from config: {e}",
                validation_errors=[str(e)]
            )
    
    def get_config_template(self, template_name: str) -> Dict[str, Any]:
        """Get configuration template by name."""
        templates = {
            "basic_cli": {
                "test_type": "cli",
                "name": "Basic CLI Test",
                "description": "Basic CLI testing configuration",
                "adapters": ["lm_eval"],
                "tasks": ["hellaswag"],
                "execution_timeout": 300,
                "output_format": "json"
            },
            "comprehensive_api": {
                "test_type": "api",
                "name": "Comprehensive API Test",
                "description": "Comprehensive API testing configuration",
                "server_port": 8000,
                "test_endpoints": [
                    "/api/v1/evaluations",
                    "/api/v1/tasks",
                    "/api/v1/adapters",
                    "/api/v1/status"
                ],
                "concurrent_requests": 10,
                "timeout": 60
            },
            "adapter_validation": {
                "test_type": "adapter",
                "name": "Adapter Validation Test",
                "description": "Validate all core adapters",
                "adapters": ["lm_eval", "swe_bench"],
                "test_task_count": 2,
                "dependency_check": True,
                "performance_benchmark": True
            },
            "full_pipeline": {
                "test_type": "pipeline",
                "name": "Full Pipeline Test",
                "description": "Complete end-to-end pipeline test",
                "target_adapters": ["lm_eval", "swe_bench"],
                "task_selection": {
                    "builtin_count": 2,
                    "custom_count": 1
                },
                "execution_params": {
                    "timeout": 600,
                    "parallel": True,
                    "max_workers": 4
                }
            }
        }
        
        if template_name not in templates:
            available = list(templates.keys())
            raise ConfigurationError(
                f"Unknown template '{template_name}'. Available templates: {available}"
            )
        
        return templates[template_name]
    
    def merge_configs(self, base_config: Dict[str, Any], 
                     override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configurations, with override taking precedence."""
        merged = base_config.copy()
        
        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self.merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged