"""
Main entry point for evaluation_engine CLI

This allows the package to be run as: python -m evaluation_engine
"""

import sys
from evaluation_engine.cli.config_cli import main

if __name__ == "__main__":
    sys.exit(main())