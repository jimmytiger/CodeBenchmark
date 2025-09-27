"""
Evaluation Engine Test Suite

This package contains comprehensive tests for all components of the AI Evaluation Engine.
All test files have been consolidated from the root directory for better organization.

Test Categories:
- Core Engines: analysis, metrics, prompt, visualization
- API & Integration: gateway, endpoints, lm-eval integration  
- Security & Compliance: vulnerability scanning, encryption, audit
- Analysis Tools: data analysis and visualization tools
- Specialized Tests: model adapters, composite metrics, etc.

Usage:
    Run all tests: python -m pytest evaluation_engine/tests/ -v
    Run specific category: python -m pytest evaluation_engine/tests/test_*_engine.py -v
    
For detailed usage instructions, see README.md and USAGE.md in this directory.
"""

__version__ = "1.0.0"
__author__ = "AI Evaluation Engine Team"

# Test file registry for programmatic access
TEST_DIRECTORIES = {
    "core_engines": {
        "path": "core_engines/",
        "files": [
            "test_analysis_engine.py",
            "test_metrics_engine.py", 
            "test_prompt_engine.py",
            "test_visualization_engine.py"
        ]
    },
    "api_integration": {
        "path": "api_integration/",
        "files": [
            "test_api_minimal.py",
            "test_api_basic.py", 
            "test_api_gateway.py",
            "test_integration.py",
            "test_lm_eval_integration.py"
        ]
    },
    "security": {
        "path": "security/",
        "files": [
            "test_security_basic.py",
            "test_security_framework.py"
        ]
    },
    "analysis_tools": {
        "path": "analysis_tools/",
        "files": [
            "test_analysis_tools.py",
            "test_analysis_tools_documentation.py",
            "test_analysis_visualization_integration.py",
            "test_fixed_analysis_tools.py"
        ]
    },
    "specialized": {
        "path": "specialized/",
        "files": [
            "test_advanced_model_config.py",
            "test_concrete_model_adapters.py",
            "test_composite_metrics.py",
            "test_single_turn_simple.py",
            "test_task_2_implementation.py"
        ]
    }
}

def get_test_files(category=None):
    """
    Get list of test files by category.
    
    Args:
        category (str, optional): Test category. If None, returns all files with paths.
        
    Returns:
        list: List of test file paths
    """
    if category is None:
        all_files = []
        for cat_info in TEST_DIRECTORIES.values():
            for file in cat_info["files"]:
                all_files.append(cat_info["path"] + file)
        return all_files
    
    cat_info = TEST_DIRECTORIES.get(category, {})
    if cat_info:
        return [cat_info["path"] + f for f in cat_info["files"]]
    return []

def get_test_categories():
    """Get list of available test categories."""
    return list(TEST_DIRECTORIES.keys())

def get_test_directory_path(category):
    """
    Get the directory path for a test category.
    
    Args:
        category (str): Test category name
        
    Returns:
        str: Directory path or None if category not found
    """
    cat_info = TEST_DIRECTORIES.get(category, {})
    return cat_info.get("path")