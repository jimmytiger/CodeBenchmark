"""
Configuration-driven evaluation CLI

This module provides command-line interface for configuration-driven evaluation tasks.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional, List

from evaluation_engine import __version__
from evaluation_engine.config import ConfigDrivenEvaluator, ConfigParser, ConfigValidator


def setup_logging(verbosity: str = "INFO") -> None:
    """Setup logging configuration."""
    level = getattr(logging, verbosity.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def setup_parser() -> argparse.ArgumentParser:
    """Setup the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="eval-engine",
        description="Configuration-driven evaluation engine for language models",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"eval-engine {__version__}"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Create subparsers for different command groups
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        metavar="COMMAND"
    )
    
    # Config command group
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration-driven evaluation commands",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        help="Configuration commands",
        metavar="CONFIG_COMMAND"
    )
    
    # Config run command
    run_parser = config_subparsers.add_parser(
        "run",
        help="Run evaluation from configuration file",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    run_parser.add_argument(
        "config_file",
        type=str,
        help="Path to the configuration file (YAML or JSON)"
    )
    
    run_parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Override output directory from config"
    )
    
    run_parser.add_argument(
        "--override",
        action="append",
        default=[],
        help="Override configuration values (format: key=value). Can be used multiple times."
    )
    
    run_parser.add_argument(
        "--tasks",
        type=str,
        default=None,
        help="Comma-separated list of specific tasks to run (overrides config)"
    )
    
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and show execution plan without running"
    )
    
    run_parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level"
    )
    
    run_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop execution on first task failure"
    )
    
    run_parser.add_argument(
        "--export-results",
        type=str,
        default=None,
        help="Export detailed results to JSON file"
    )
    
    # Config validate command
    validate_parser = config_subparsers.add_parser(
        "validate",
        help="Validate configuration file",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    validate_parser.add_argument(
        "config_file",
        type=str,
        help="Path to the configuration file to validate"
    )
    
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode"
    )
    
    # Config list-tasks command
    list_tasks_parser = config_subparsers.add_parser(
        "list-tasks",
        help="List available lm-eval tasks",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    list_tasks_parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Filter tasks by name pattern"
    )
    
    list_tasks_parser.add_argument(
        "--format",
        type=str,
        choices=["table", "json", "yaml"],
        default="table",
        help="Output format"
    )
    
    # Config list-models command
    list_models_parser = config_subparsers.add_parser(
        "list-models",
        help="List supported model types and templates",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    list_models_parser.add_argument(
        "--format",
        type=str,
        choices=["table", "json", "yaml"],
        default="table",
        help="Output format"
    )
    
    # Config template command
    template_parser = config_subparsers.add_parser(
        "template",
        help="Generate configuration template",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    template_parser.add_argument(
        "template_name",
        type=str,
        choices=["basic", "multi-model", "comprehensive"],
        help="Template type to generate"
    )
    
    template_parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: stdout)"
    )
    
    template_parser.add_argument(
        "--format",
        type=str,
        choices=["yaml", "json"],
        default="yaml",
        help="Output format"
    )
    
    return parser


def handle_config_run(args: argparse.Namespace) -> int:
    """Handle the config run command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Setup logging
        setup_logging(args.log_level)
        
        # Check if config file exists
        config_path = Path(args.config_file)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return 1
        
        logger.info(f"Loading configuration from: {config_path}")
        
        # Parse overrides
        overrides = {}
        for override in args.override:
            if "=" not in override:
                logger.error(f"Invalid override format: {override}. Use key=value format.")
                return 1
            key, value = override.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Try to parse value as JSON for complex types
            try:
                import json
                # Try to parse as JSON first (for numbers, booleans, lists, etc.)
                parsed_value = json.loads(value)
                overrides[key] = parsed_value
            except json.JSONDecodeError:
                # If not valid JSON, treat as string
                overrides[key] = value
        
        # Create evaluator
        evaluator = ConfigDrivenEvaluator()
        
        if args.dry_run:
            logger.info("Dry run mode - validating configuration and showing execution plan")
            
            # Prepare parameter overrides
            parameter_overrides = {}
            if overrides:
                parameter_overrides.update(overrides)
            
            if args.output_dir:
                parameter_overrides.setdefault('output', {})['directory'] = args.output_dir
            
            # Run in dry-run mode
            results = evaluator.run_from_config(
                str(config_path),
                task_filter=args.tasks.split(",") if args.tasks else None,
                parameter_overrides=parameter_overrides,
                fail_fast=args.fail_fast,
                dry_run=True
            )
            
            logger.info("Configuration is valid")
            logger.info(f"Tasks to execute: {results.batch_result.execution_order}")
            logger.info(f"Total tasks: {results.batch_result.total_tasks}")
            logger.info(f"Output directory: {results.config_metadata.name}")
            
            return 0
        
        # Run evaluation
        logger.info("Starting evaluation...")
        
        # Prepare parameter overrides
        parameter_overrides = {}
        if overrides:
            parameter_overrides.update(overrides)
        
        if args.output_dir:
            parameter_overrides.setdefault('output', {})['directory'] = args.output_dir
        
        results = evaluator.run_from_config(
            str(config_path),
            task_filter=args.tasks.split(",") if args.tasks else None,
            parameter_overrides=parameter_overrides,
            fail_fast=args.fail_fast,
            dry_run=False
        )
        
        logger.info("Evaluation completed successfully")
        logger.info(f"Total execution time: {results.total_execution_time:.2f} seconds")
        logger.info(f"Tasks completed: {results.batch_result.completed_tasks}/{results.batch_result.total_tasks}")
        logger.info(f"Success rate: {results.batch_result.success_rate:.1f}%")
        
        if results.batch_result.failed_tasks > 0:
            logger.warning(f"Failed tasks: {results.batch_result.failed_tasks}")
            for task_name, error in results.batch_result.task_errors.items():
                logger.warning(f"  - {task_name}: {error}")
        
        # Export results if requested
        if args.export_results:
            if evaluator.export_results(args.export_results, results):
                logger.info(f"Detailed results exported to: {args.export_results}")
            else:
                logger.error(f"Failed to export results to: {args.export_results}")
        
        return 0 if results.batch_result.is_successful else 1
        
    except Exception as e:
        logger.error(f"Error running evaluation: {e}")
        if args.log_level == "DEBUG":
            import traceback
            traceback.print_exc()
        return 1


def handle_config_validate(args: argparse.Namespace) -> int:
    """Handle the config validate command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Check if config file exists
        config_path = Path(args.config_file)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return 1
        
        logger.info(f"Validating configuration: {config_path}")
        
        # Create evaluator and validate
        evaluator = ConfigDrivenEvaluator()
        validation_result = evaluator.validate_config_file(str(config_path))
        
        if validation_result.is_valid:
            logger.info("✓ Configuration is valid")
            
            # In strict mode, also check for warnings
            if args.strict and validation_result.has_warnings():
                logger.warning("⚠ Configuration has warnings (strict mode):")
                for warning in validation_result.warnings:
                    logger.warning(f"  - {warning.message}")
                    if warning.location:
                        logger.warning(f"    Location: {warning.location}")
                    if warning.suggestion:
                        logger.warning(f"    Suggestion: {warning.suggestion}")
                return 1 if args.strict else 0
            
            # Show summary information
            try:
                parser = ConfigParser()
                config = parser.parse_config(str(config_path))
                logger.info(f"  Tasks: {len(config.tasks)}")
                logger.info(f"  Models: {len(config.models)}")
                
                # Show task details
                if config.tasks:
                    logger.info("  Task details:")
                    for task in config.tasks:
                        logger.info(f"    - {task.name}: {task.task_name} (model: {task.model_ref})")
                
                # Show model details
                if config.models:
                    logger.info("  Model details:")
                    for model_name, model in config.models.items():
                        logger.info(f"    - {model_name}: {model.type} ({model.model_name})")
                        
            except Exception as e:
                logger.debug(f"Could not parse config for summary: {e}")
            
            return 0
        else:
            logger.error("✗ Configuration validation failed:")
            for error in validation_result.errors:
                logger.error(f"  - {error.message}")
                if error.location:
                    logger.error(f"    Location: {error.location}")
                if error.suggestion:
                    logger.error(f"    Suggestion: {error.suggestion}")
            
            # Show warnings even in error case
            if validation_result.has_warnings():
                logger.warning("Configuration warnings:")
                for warning in validation_result.warnings:
                    logger.warning(f"  - {warning.message}")
                    if warning.location:
                        logger.warning(f"    Location: {warning.location}")
            
            return 1
            
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        if logger.getEffectiveLevel() <= logging.DEBUG:
            import traceback
            traceback.print_exc()
        return 1


def handle_config_list_tasks(args: argparse.Namespace) -> int:
    """Handle the config list-tasks command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Import lm_eval to get available tasks
        try:
            from lm_eval.tasks import TaskManager
            task_manager = TaskManager()
            all_tasks = task_manager.list_all_tasks()
        except ImportError as e:
            logger.error(f"Could not import lm_eval: {e}")
            logger.error("Please ensure lm-evaluation-harness is installed")
            return 1
        
        # Filter tasks if requested
        if args.filter:
            filtered_tasks = [task for task in all_tasks if args.filter.lower() in task.lower()]
        else:
            filtered_tasks = all_tasks
        
        # Output in requested format
        if args.format == "json":
            import json
            print(json.dumps(filtered_tasks, indent=2))
        elif args.format == "yaml":
            try:
                import yaml
                print(yaml.dump({"tasks": filtered_tasks}, default_flow_style=False))
            except ImportError:
                logger.error("PyYAML not installed. Please install it to use YAML format.")
                return 1
        else:  # table format
            print(f"Available lm-eval tasks ({len(filtered_tasks)} total):")
            print("-" * 50)
            for task in sorted(filtered_tasks):
                print(f"  {task}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return 1


def handle_config_list_models(args: argparse.Namespace) -> int:
    """Handle the config list-models command."""
    logger = logging.getLogger(__name__)
    
    try:
        from evaluation_engine.config.templates import ModelTemplateManager
        
        template_manager = ModelTemplateManager()
        builtin_templates = template_manager.load_builtin_templates()
        
        model_types = {
            "openai": "OpenAI API models (GPT-3.5, GPT-4, etc.)",
            "anthropic": "Anthropic Claude models",
            "huggingface": "Hugging Face transformers models",
            "custom": "Custom model implementations"
        }
        
        # Output in requested format
        if args.format == "json":
            import json
            data = {
                "model_types": model_types,
                "builtin_templates": list(builtin_templates.keys())
            }
            print(json.dumps(data, indent=2))
        elif args.format == "yaml":
            import yaml
            data = {
                "model_types": model_types,
                "builtin_templates": list(builtin_templates.keys())
            }
            print(yaml.dump(data, default_flow_style=False))
        else:  # table format
            print("Supported Model Types:")
            print("-" * 50)
            for model_type, description in model_types.items():
                print(f"  {model_type:12} - {description}")
            
            print(f"\nBuiltin Templates ({len(builtin_templates)} available):")
            print("-" * 50)
            for template_name in sorted(builtin_templates.keys()):
                print(f"  {template_name}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return 1


def handle_config_template(args: argparse.Namespace) -> int:
    """Handle the config template command."""
    logger = logging.getLogger(__name__)
    
    try:
        # Generate template based on type
        templates = {
            "basic": _generate_basic_template(),
            "multi-model": _generate_multi_model_template(),
            "comprehensive": _generate_comprehensive_template()
        }
        
        template_content = templates[args.template_name]
        
        # Convert to requested format
        if args.format == "json":
            import yaml
            import json
            # Parse YAML and convert to JSON
            data = yaml.safe_load(template_content)
            output_content = json.dumps(data, indent=2)
        else:
            output_content = template_content
        
        # Output to file or stdout
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output_content)
            logger.info(f"Template written to: {output_path}")
        else:
            print(output_content)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error generating template: {e}")
        return 1


def _generate_basic_template() -> str:
    """Generate a basic configuration template."""
    return """# Basic Evaluation Configuration Template
metadata:
  name: "Basic LLM Evaluation"
  version: "1.0"
  author: "Your Name"

variables:
  output_dir: "./results"
  default_batch_size: 16

models:
  gpt35:
    name: "gpt35"
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.7
      max_tokens: 1000
    system_prompt: "You are a helpful assistant."

defaults:
  num_fewshot: 5
  batch_size: "${default_batch_size}"

tasks:
  - name: "hellaswag_basic"
    description: "Basic HellaSwag evaluation"
    model_ref: "gpt35"
    task_name: "hellaswag"
    num_fewshot: 10
    batch_size: 8

output:
  directory: "${output_dir}"
  formats: ["json", "csv"]
  include_raw_responses: false
"""


def _generate_multi_model_template() -> str:
    """Generate a multi-model comparison template."""
    return """# Multi-Model Comparison Configuration Template
metadata:
  name: "Multi-Model LLM Comparison"
  version: "1.0"
  author: "Your Name"

variables:
  output_dir: "./results/comparison"
  default_batch_size: 16

models:
  gpt35:
    name: "gpt35"
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: 0.7
      max_tokens: 1000
    system_prompt: "You are a helpful assistant."

  claude:
    name: "claude"
    type: "anthropic"
    model_name: "claude-3-sonnet-20240229"
    parameters:
      temperature: 0.7
      max_tokens: 1000
    system_prompt: "You are Claude, an AI assistant."

  llama2:
    name: "llama2"
    type: "huggingface"
    model_name: "meta-llama/Llama-2-7b-chat-hf"
    parameters:
      temperature: 0.7
      max_tokens: 1000

defaults:
  num_fewshot: 5
  batch_size: "${default_batch_size}"

tasks:
  - name: "hellaswag_gpt35"
    description: "HellaSwag with GPT-3.5"
    model_ref: "gpt35"
    task_name: "hellaswag"
    num_fewshot: 10

  - name: "hellaswag_claude"
    description: "HellaSwag with Claude"
    model_ref: "claude"
    task_name: "hellaswag"
    num_fewshot: 10

  - name: "hellaswag_llama2"
    description: "HellaSwag with Llama2"
    model_ref: "llama2"
    task_name: "hellaswag"
    num_fewshot: 10

output:
  directory: "${output_dir}"
  formats: ["json", "html", "csv"]
  include_raw_responses: true
  generate_report: true
  compare_models: true
"""


def _generate_comprehensive_template() -> str:
    """Generate a comprehensive configuration template."""
    return """# Comprehensive Evaluation Configuration Template
metadata:
  name: "Comprehensive LLM Evaluation Suite"
  version: "1.0"
  author: "Your Name"
  description: "Full evaluation across multiple tasks and models"

variables:
  output_dir: "./results/comprehensive"
  default_batch_size: 16
  default_temperature: 0.7

models:
  gpt35:
    name: "gpt35"
    type: "openai"
    model_name: "gpt-3.5-turbo"
    parameters:
      temperature: "${default_temperature}"
      max_tokens: 1000
    system_prompt: "You are a helpful assistant."

  claude:
    name: "claude"
    type: "anthropic"
    model_name: "claude-3-sonnet-20240229"
    parameters:
      temperature: "${default_temperature}"
      max_tokens: 1000
    system_prompt: "You are Claude, an AI assistant."

defaults:
  num_fewshot: 5
  batch_size: "${default_batch_size}"

tasks:
  # Commonsense reasoning
  - name: "hellaswag_gpt35"
    description: "HellaSwag commonsense reasoning with GPT-3.5"
    model_ref: "gpt35"
    task_name: "hellaswag"
    num_fewshot: 10
    depends_on: []

  - name: "arc_easy_gpt35"
    description: "ARC Easy reasoning with GPT-3.5"
    model_ref: "gpt35"
    task_name: "arc_easy"
    num_fewshot: 25
    depends_on: []

  # Math reasoning
  - name: "gsm8k_gpt35"
    description: "GSM8K math reasoning with GPT-3.5"
    model_ref: "gpt35"
    task_name: "gsm8k"
    task_config:
      limit: 1000
    num_fewshot: 5
    depends_on: ["hellaswag_gpt35"]

  # Reading comprehension
  - name: "truthfulqa_gpt35"
    description: "TruthfulQA with GPT-3.5"
    model_ref: "gpt35"
    task_name: "truthfulqa_mc"
    task_config:
      limit: 500
    num_fewshot: 0
    depends_on: ["arc_easy_gpt35"]

  # Comparison tasks with Claude
  - name: "hellaswag_claude"
    description: "HellaSwag with Claude for comparison"
    model_ref: "claude"
    task_name: "hellaswag"
    num_fewshot: 10
    depends_on: ["hellaswag_gpt35"]

output:
  directory: "${output_dir}"
  formats: ["json", "html", "csv"]
  include_raw_responses: true
  generate_report: true
  compare_models: true
  save_predictions: true
"""


def main() -> int:
    """Main CLI entry point."""
    parser = setup_parser()
    args = parser.parse_args()
    
    # Setup basic logging
    if hasattr(args, 'verbose') and args.verbose:
        setup_logging("DEBUG")
    else:
        setup_logging("INFO")
    
    # Handle no command
    if not hasattr(args, 'command') or args.command is None:
        parser.print_help()
        return 1
    
    # Handle config commands
    if args.command == "config":
        if not hasattr(args, 'config_command') or args.config_command is None:
            parser.print_help()
            return 1
        
        if args.config_command == "run":
            return handle_config_run(args)
        elif args.config_command == "validate":
            return handle_config_validate(args)
        elif args.config_command == "list-tasks":
            return handle_config_list_tasks(args)
        elif args.config_command == "list-models":
            return handle_config_list_models(args)
        elif args.config_command == "template":
            return handle_config_template(args)
        else:
            print(f"Unknown config command: {args.config_command}")
            return 1
    
    print(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())