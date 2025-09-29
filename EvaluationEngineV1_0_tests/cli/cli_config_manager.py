"""
Configuration manager for CLI testing.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..models.test_models import CLITestConfig, TestConfiguration, TestType
from ..core.config_manager import ConfigManager
from ..core.error_handler import ConfigurationError


class CLIConfigManager:
    """Manages CLI-specific configuration for testing."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(f"{__name__}.CLIConfigManager")
    
    def create_cli_config(self, config_dict: Dict[str, Any]) -> CLITestConfig:
        """Create CLITestConfig from dictionary."""
        try:
            return CLITestConfig(
                tasks=config_dict.get("tasks", []),
                adapters=config_dict.get("adapters", []),
                execution_timeout=config_dict.get("execution_timeout", 300),
                output_format=config_dict.get("output_format", "json"),
                verbose=config_dict.get("verbose", False),
                config_file=Path(config_dict["config_file"]) if config_dict.get("config_file") else None,
                custom_task_dir=Path(config_dict["custom_task_dir"]) if config_dict.get("custom_task_dir") else None,
                parallel_execution=config_dict.get("parallel_execution", False),
                max_workers=config_dict.get("max_workers", 4)
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to create CLI config: {e}")
    
    def create_test_configuration(self, cli_config: CLITestConfig, 
                                 test_name: str = "CLI Test") -> TestConfiguration:
        """Create TestConfiguration from CLITestConfig."""
        return TestConfiguration(
            test_id=f"cli_test_{int(time.time())}",
            test_type=TestType.CLI,
            name=test_name,
            description=f"CLI test with {len(cli_config.tasks)} tasks",
            task_selection={
                "tasks": cli_config.tasks,
                "adapters": [a.value for a in cli_config.adapters],
                "custom_task_dir": str(cli_config.custom_task_dir) if cli_config.custom_task_dir else None
            },
            execution_params={
                "timeout": cli_config.execution_timeout,
                "output_format": cli_config.output_format,
                "verbose": cli_config.verbose,
                "parallel": cli_config.parallel_execution,
                "max_workers": cli_config.max_workers
            },
            timeout=cli_config.execution_timeout
        )
    
    def load_cli_config_file(self, config_path: Path) -> CLITestConfig:
        """Load CLI configuration from file."""
        config_dict = self.config_manager.load_config(config_path)
        
        # Extract CLI-specific section
        cli_section = config_dict.get("cli_config", config_dict)
        
        return self.create_cli_config(cli_section)
    
    def save_cli_config_file(self, cli_config: CLITestConfig, config_path: Path) -> None:
        """Save CLI configuration to file."""
        config_dict = {
            "cli_config": {
                "tasks": cli_config.tasks,
                "adapters": [a.value for a in cli_config.adapters],
                "execution_timeout": cli_config.execution_timeout,
                "output_format": cli_config.output_format,
                "verbose": cli_config.verbose,
                "parallel_execution": cli_config.parallel_execution,
                "max_workers": cli_config.max_workers
            }
        }
        
        if cli_config.custom_task_dir:
            config_dict["cli_config"]["custom_task_dir"] = str(cli_config.custom_task_dir)
        
        self.config_manager.save_config(config_dict, config_path)
    
    def validate_cli_config(self, cli_config: CLITestConfig) -> List[str]:
        """Validate CLI configuration."""
        errors = []
        
        # Validate tasks
        if not cli_config.tasks:
            errors.append("No tasks specified for CLI test")
        
        # Validate adapters
        if not cli_config.adapters:
            errors.append("No adapters specified for CLI test")
        
        # Validate timeout
        if cli_config.execution_timeout <= 0:
            errors.append("Execution timeout must be positive")
        
        # Validate output format
        valid_formats = ["json", "yaml", "csv", "table"]
        if cli_config.output_format not in valid_formats:
            errors.append(f"Invalid output format. Must be one of: {valid_formats}")
        
        # Validate custom task directory
        if cli_config.custom_task_dir and not cli_config.custom_task_dir.exists():
            errors.append(f"Custom task directory does not exist: {cli_config.custom_task_dir}")
        
        # Validate parallel execution settings
        if cli_config.parallel_execution and cli_config.max_workers <= 0:
            errors.append("Max workers must be positive when parallel execution is enabled")
        
        return errors
    
    def create_default_cli_config(self) -> CLITestConfig:
        """Create default CLI configuration."""
        from ..models.test_models import AdapterType
        
        return CLITestConfig(
            tasks=["hellaswag", "arc_easy"],
            adapters=[AdapterType.LM_EVAL],
            execution_timeout=300,
            output_format="json",
            verbose=True,
            parallel_execution=False,
            max_workers=2
        )
    
    def create_builtin_tasks_config(self, task_names: List[str]) -> CLITestConfig:
        """Create CLI config for builtin tasks."""
        from ..models.test_models import AdapterType
        
        return CLITestConfig(
            tasks=task_names,
            adapters=[AdapterType.LM_EVAL],
            execution_timeout=300,
            output_format="json",
            verbose=True,
            parallel_execution=False,
            max_workers=1
        )
    
    def create_custom_tasks_config(self, task_dir: Path, 
                                  task_names: Optional[List[str]] = None) -> CLITestConfig:
        """Create CLI config for custom tasks."""
        from ..models.test_models import AdapterType
        
        if not task_dir.exists():
            raise ConfigurationError(f"Custom task directory does not exist: {task_dir}")
        
        # If no task names provided, try to discover them
        if not task_names:
            task_names = self._discover_tasks_in_directory(task_dir)
        
        return CLITestConfig(
            tasks=task_names,
            adapters=[AdapterType.LM_EVAL],
            execution_timeout=600,  # Longer timeout for custom tasks
            output_format="json",
            verbose=True,
            custom_task_dir=task_dir,
            parallel_execution=False,
            max_workers=1
        )
    
    def create_adapter_test_config(self, adapter_name: str) -> CLITestConfig:
        """Create CLI config for adapter testing."""
        from ..models.test_models import AdapterType
        
        # Map adapter name to AdapterType
        adapter_map = {
            "lm_eval": AdapterType.LM_EVAL,
            "swe_bench": AdapterType.SWE_BENCH,
            "intercode": AdapterType.INTERCODE,
            "convcode": AdapterType.CONVCODE
        }
        
        adapter_type = adapter_map.get(adapter_name, AdapterType.LM_EVAL)
        
        # Choose appropriate tasks based on adapter
        if adapter_name == "swe_bench":
            tasks = ["swe_bench_lite"]  # SWE-bench specific task
        else:
            tasks = ["hellaswag"]  # Default task
        
        return CLITestConfig(
            tasks=tasks,
            adapters=[adapter_type],
            execution_timeout=600,  # Longer timeout for adapter tests
            output_format="json",
            verbose=True,
            parallel_execution=False,
            max_workers=1
        )
    
    def merge_cli_configs(self, base_config: CLITestConfig, 
                         override_config: CLITestConfig) -> CLITestConfig:
        """Merge two CLI configurations."""
        return CLITestConfig(
            tasks=override_config.tasks or base_config.tasks,
            adapters=override_config.adapters or base_config.adapters,
            execution_timeout=override_config.execution_timeout or base_config.execution_timeout,
            output_format=override_config.output_format or base_config.output_format,
            verbose=override_config.verbose if override_config.verbose is not None else base_config.verbose,
            config_file=override_config.config_file or base_config.config_file,
            custom_task_dir=override_config.custom_task_dir or base_config.custom_task_dir,
            parallel_execution=override_config.parallel_execution if override_config.parallel_execution is not None else base_config.parallel_execution,
            max_workers=override_config.max_workers or base_config.max_workers
        )
    
    def _discover_tasks_in_directory(self, task_dir: Path) -> List[str]:
        """Discover task names in a directory."""
        task_names = []
        
        try:
            # Look for Python files
            for py_file in task_dir.glob("**/*.py"):
                if py_file.name != "__init__.py":
                    task_names.append(py_file.stem)
            
            # Look for YAML files
            for yaml_file in task_dir.glob("**/*.yaml"):
                task_names.append(yaml_file.stem)
            
            # Look for JSON files
            for json_file in task_dir.glob("**/*.json"):
                task_names.append(json_file.stem)
            
        except Exception as e:
            self.logger.warning(f"Error discovering tasks in {task_dir}: {e}")
        
        return task_names[:10]  # Limit to first 10 tasks
    
    def get_cli_command_template(self, cli_config: CLITestConfig) -> str:
        """Get CLI command template for configuration."""
        cmd_parts = ["python -m EvaluationEngineV1_0.cli.multi_turn_cli"]
        
        # Add tasks
        if cli_config.tasks:
            cmd_parts.extend(["--tasks"] + cli_config.tasks)
        
        # Add timeout
        cmd_parts.extend(["--timeout", str(cli_config.execution_timeout)])
        
        # Add output format
        cmd_parts.extend(["--output-format", cli_config.output_format])
        
        # Add verbose flag
        if cli_config.verbose:
            cmd_parts.append("--verbose")
        
        # Add custom task directory
        if cli_config.custom_task_dir:
            cmd_parts.extend(["--task-path", str(cli_config.custom_task_dir)])
        
        return " ".join(cmd_parts)


def create_cli_config_manager() -> CLIConfigManager:
    """Factory function to create a CLI config manager."""
    return CLIConfigManager()