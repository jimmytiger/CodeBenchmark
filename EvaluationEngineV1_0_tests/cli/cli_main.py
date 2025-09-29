#!/usr/bin/env python3
"""
Main CLI entry point for EvaluationEngineV1_0 testing framework.
"""

import click
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .cli_test_runner import CLITestRunner
from .cli_config_manager import CLIConfigManager
from .cli_result_formatter import CLIResultFormatter
from ..core.error_handler import setup_error_logging, TestFrameworkError
from ..models.test_models import AdapterType


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--log-file', type=click.Path(), help='Log file path')
@click.pass_context
def cli(ctx, verbose, log_file):
    """EvaluationEngineV1_0 Testing Framework CLI."""
    ctx.ensure_object(dict)
    
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_error_logging(log_level, log_file)
    
    ctx.obj['verbose'] = verbose
    ctx.obj['log_file'] = log_file


@cli.command()
@click.option('--tasks', '-t', multiple=True, required=True, 
              help='Task names to test (can specify multiple)')
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Configuration file path')
@click.option('--timeout', default=300, help='Execution timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'output_format', 
              type=click.Choice(['json', 'yaml', 'csv', 'table']), 
              default='json', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def builtin(ctx, tasks, config, timeout, output, output_format, verbose):
    """Test builtin tasks using CLI interface."""
    try:
        click.echo(f"Testing builtin tasks: {', '.join(tasks)}")
        
        # Create CLI test runner
        runner = CLITestRunner()
        
        # Load configuration if provided
        config_dict = {}
        if config:
            config_manager = CLIConfigManager()
            cli_config = config_manager.load_cli_config_file(Path(config))
            config_dict = {
                "timeout": cli_config.execution_timeout,
                "verbose": cli_config.verbose,
                "output_format": cli_config.output_format
            }
        else:
            config_dict = {
                "timeout": timeout,
                "verbose": verbose or ctx.obj.get('verbose', False),
                "output_format": output_format
            }
        
        # Run tests
        result = runner.run_builtin_tasks(list(tasks), config_dict)
        
        # Format and display results
        formatter = CLIResultFormatter()
        
        if output:
            # Save to file
            formatter.save_results(result, Path(output), output_format)
            click.echo(f"Results saved to: {output}")
        else:
            # Display to console
            if output_format == 'table':
                click.echo("\nTest Results:")
                click.echo("-" * 50)
            
            formatted_result = formatter.format_test_result(
                _create_test_result_from_dict(result), output_format
            )
            click.echo(formatted_result)
        
        # Exit with appropriate code
        if result.get("success", False):
            click.echo("\n✓ All tests passed!")
            sys.exit(0)
        else:
            click.echo(f"\n✗ Tests failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except TestFrameworkError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--task-dir', type=click.Path(exists=True), required=True,
              help='Directory containing custom tasks')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file path')
@click.option('--timeout', default=600, help='Execution timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'output_format',
              type=click.Choice(['json', 'yaml', 'csv', 'table']),
              default='json', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def custom(ctx, task_dir, config, timeout, output, output_format, verbose):
    """Test custom tasks from specified directory."""
    try:
        task_dir_path = Path(task_dir)
        click.echo(f"Testing custom tasks from: {task_dir_path}")
        
        # Create CLI test runner
        runner = CLITestRunner()
        
        # Load configuration if provided
        config_dict = {}
        if config:
            config_manager = CLIConfigManager()
            cli_config = config_manager.load_cli_config_file(Path(config))
            config_dict = {
                "timeout": cli_config.execution_timeout,
                "verbose": cli_config.verbose,
                "output_format": cli_config.output_format
            }
        else:
            config_dict = {
                "timeout": timeout,
                "verbose": verbose or ctx.obj.get('verbose', False),
                "output_format": output_format
            }
        
        # Run tests
        result = runner.run_custom_tasks(task_dir_path, config_dict)
        
        # Format and display results
        formatter = CLIResultFormatter()
        
        if output:
            formatter.save_results(result, Path(output), output_format)
            click.echo(f"Results saved to: {output}")
        else:
            formatted_result = formatter.format_test_result(
                _create_test_result_from_dict(result), output_format
            )
            click.echo(formatted_result)
        
        # Exit with appropriate code
        if result.get("success", False):
            click.echo("\n✓ Custom task tests passed!")
            sys.exit(0)
        else:
            click.echo(f"\n✗ Custom task tests failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except TestFrameworkError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--adapter', type=click.Choice(['lm_eval', 'swe_bench', 'intercode', 'convcode']),
              required=True, help='Adapter to test')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file path')
@click.option('--timeout', default=600, help='Execution timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'output_format',
              type=click.Choice(['json', 'yaml', 'csv', 'table']),
              default='json', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def adapters(ctx, adapter, config, timeout, output, output_format, verbose):
    """Test specific adapter functionality."""
    try:
        click.echo(f"Testing adapter: {adapter}")
        
        # Create CLI test runner
        runner = CLITestRunner()
        
        # Load configuration if provided
        config_dict = {}
        if config:
            config_manager = CLIConfigManager()
            cli_config = config_manager.load_cli_config_file(Path(config))
            config_dict = {
                "timeout": cli_config.execution_timeout,
                "verbose": cli_config.verbose,
                "output_format": cli_config.output_format
            }
        else:
            config_dict = {
                "timeout": timeout,
                "verbose": verbose or ctx.obj.get('verbose', False),
                "output_format": output_format
            }
        
        # Run adapter tests
        result = runner.run_adapter_tests(adapter, config_dict)
        
        # Format and display results
        formatter = CLIResultFormatter()
        
        if output:
            formatter.save_results(result, Path(output), output_format)
            click.echo(f"Results saved to: {output}")
        else:
            formatted_result = formatter.format_test_result(
                _create_test_result_from_dict(result), output_format
            )
            click.echo(formatted_result)
        
        # Exit with appropriate code
        if result.get("success", False):
            click.echo(f"\n✓ Adapter {adapter} tests passed!")
            sys.exit(0)
        else:
            click.echo(f"\n✗ Adapter {adapter} tests failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except TestFrameworkError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file path')
@click.option('--timeout', default=1200, help='Execution timeout in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'output_format',
              type=click.Choice(['json', 'yaml', 'csv', 'table']),
              default='json', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def pipeline(ctx, config, timeout, output, output_format, verbose):
    """Test complete evaluation pipeline."""
    try:
        click.echo("Testing complete evaluation pipeline...")
        
        # Create CLI test runner
        runner = CLITestRunner()
        
        # Load configuration if provided
        config_dict = {}
        if config:
            config_manager = CLIConfigManager()
            cli_config = config_manager.load_cli_config_file(Path(config))
            config_dict = {
                "timeout": cli_config.execution_timeout,
                "verbose": cli_config.verbose,
                "output_format": cli_config.output_format
            }
        else:
            config_dict = {
                "timeout": timeout,
                "verbose": verbose or ctx.obj.get('verbose', False),
                "output_format": output_format
            }
        
        # Run pipeline tests
        result = runner.run_full_pipeline(config_dict)
        
        # Format and display results
        formatter = CLIResultFormatter()
        
        if output:
            formatter.save_results(result, Path(output), output_format)
            click.echo(f"Results saved to: {output}")
        else:
            formatted_result = formatter.format_test_result(
                _create_test_result_from_dict(result), output_format
            )
            click.echo(formatted_result)
        
        # Exit with appropriate code
        if result.get("success", False):
            click.echo("\n✓ Pipeline tests passed!")
            sys.exit(0)
        else:
            click.echo(f"\n✗ Pipeline tests failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except TestFrameworkError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--template', type=click.Choice(['basic', 'comprehensive', 'adapter', 'custom']),
              default='basic', help='Configuration template to generate')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output configuration file path')
@click.option('--format', 'config_format',
              type=click.Choice(['json', 'yaml']),
              default='yaml', help='Configuration file format')
def init_config(template, output, config_format):
    """Initialize configuration file from template."""
    try:
        click.echo(f"Generating {template} configuration template...")
        
        config_manager = CLIConfigManager()
        
        # Create configuration based on template
        if template == 'basic':
            cli_config = config_manager.create_default_cli_config()
        elif template == 'comprehensive':
            cli_config = config_manager.create_builtin_tasks_config([
                "hellaswag", "arc_easy", "arc_challenge", "winogrande"
            ])
            cli_config.parallel_execution = True
            cli_config.max_workers = 4
        elif template == 'adapter':
            cli_config = config_manager.create_adapter_test_config("lm_eval")
        elif template == 'custom':
            # Create a template for custom tasks
            cli_config = config_manager.create_default_cli_config()
            cli_config.custom_task_dir = Path("lm_eval/tasks")
        
        # Save configuration
        output_path = Path(output)
        config_manager.save_cli_config_file(cli_config, output_path)
        
        click.echo(f"Configuration template saved to: {output_path}")
        click.echo(f"Edit the configuration and run tests with: --config {output_path}")
        
    except TestFrameworkError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
def validate_config(config_file):
    """Validate configuration file."""
    try:
        click.echo(f"Validating configuration: {config_file}")
        
        config_manager = CLIConfigManager()
        cli_config = config_manager.load_cli_config_file(Path(config_file))
        
        # Validate configuration
        errors = config_manager.validate_cli_config(cli_config)
        
        if errors:
            click.echo("✗ Configuration validation failed:")
            for error in errors:
                click.echo(f"  - {error}")
            sys.exit(1)
        else:
            click.echo("✓ Configuration is valid")
            
            # Display configuration summary
            click.echo("\nConfiguration Summary:")
            click.echo(f"  Tasks: {', '.join(cli_config.tasks)}")
            click.echo(f"  Adapters: {', '.join(a.value for a in cli_config.adapters)}")
            click.echo(f"  Timeout: {cli_config.execution_timeout}s")
            click.echo(f"  Output Format: {cli_config.output_format}")
            click.echo(f"  Verbose: {cli_config.verbose}")
            
            if cli_config.custom_task_dir:
                click.echo(f"  Custom Task Dir: {cli_config.custom_task_dir}")
        
    except TestFrameworkError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


def _create_test_result_from_dict(result_dict: dict):
    """Create TestResult from dictionary for formatting."""
    from ..models.test_models import TestResult, TestStatus, TestType
    
    return TestResult(
        test_id=result_dict.get("test_id", "cli_test"),
        test_type=TestType.CLI,
        name=result_dict.get("name", "CLI Test"),
        status=TestStatus.PASSED if result_dict.get("success", False) else TestStatus.FAILED,
        execution_time=result_dict.get("execution_time", 0.0),
        real_execution_validated=result_dict.get("real_execution_validated", False),
        metrics=result_dict.get("metrics", {}),
        error_details=result_dict.get("error"),
        artifacts=result_dict.get("artifacts", []),
        logs=result_dict.get("logs", [])
    )


if __name__ == '__main__':
    cli()