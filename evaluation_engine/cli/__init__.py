"""
Command Line Interface for Evaluation Engine Configuration System

This module provides CLI commands for configuration-driven evaluation.
"""

from .config_cli import main, setup_parser

__all__ = ["main", "setup_parser"]