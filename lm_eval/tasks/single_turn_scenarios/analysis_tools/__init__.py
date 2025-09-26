"""
Analysis tools for single_turn_scenarios evaluation results.

This module provides comprehensive analysis and visualization capabilities
for comparing model performance across different dimensions.
"""

# Import analysis tools with error handling
__all__ = []

try:
    from .compare_models import ModelComparator
    __all__.append('ModelComparator')
except ImportError as e:
    print(f"Warning: Could not import ModelComparator: {e}")

try:
    from .context_impact import ContextAnalyzer
    __all__.append('ContextAnalyzer')
except ImportError as e:
    print(f"Warning: Could not import ContextAnalyzer: {e}")

try:
    from .scenario_analysis import ScenarioAnalyzer
    __all__.append('ScenarioAnalyzer')
except ImportError as e:
    print(f"Warning: Could not import ScenarioAnalyzer: {e}")

try:
    from .generate_report import ReportGenerator
    __all__.append('ReportGenerator')
except ImportError as e:
    print(f"Warning: Could not import ReportGenerator: {e}")

# Provide information about available tools
def get_available_tools():
    """Return a list of successfully imported analysis tools."""
    available = []
    for tool_name in ['ModelComparator', 'ContextAnalyzer', 'ScenarioAnalyzer', 'ReportGenerator']:
        if tool_name in globals():
            available.append(tool_name)
    return available

def print_available_tools():
    """Print information about available analysis tools."""
    available = get_available_tools()
    print(f"Available analysis tools: {', '.join(available)}")
    if len(available) < 4:
        missing = set(['ModelComparator', 'ContextAnalyzer', 'ScenarioAnalyzer', 'ReportGenerator']) - set(available)
        print(f"Missing tools: {', '.join(missing)}")
        print("Some tools may require additional dependencies or have import issues.")