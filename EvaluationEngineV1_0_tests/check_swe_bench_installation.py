#!/usr/bin/env python3
"""
Check SWE-bench installation and availability.

This script checks if SWE-bench is properly installed and accessible.
"""

import sys
import subprocess
import importlib
from pathlib import Path


def check_python_package(package_name):
    """Check if a Python package is installed."""
    try:
        importlib.import_module(package_name)
        return True, "Installed"
    except ImportError:
        return False, "Not installed"


def check_pip_package(package_name):
    """Check if a package is installed via pip."""
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "show", package_name
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            # Extract version from pip show output
            lines = result.stdout.split('\n')
            version_line = next((line for line in lines if line.startswith('Version:')), None)
            version = version_line.split(': ')[1] if version_line else "Unknown"
            return True, f"Installed (version: {version})"
        else:
            return False, "Not installed"
    except Exception as e:
        return False, f"Error checking: {e}"


def check_swe_bench_variants():
    """Check different SWE-bench package variants."""
    variants = [
        "swe_bench",
        "swe-bench", 
        "sweBench",
        "swebench"
    ]
    
    results = {}
    for variant in variants:
        installed, status = check_python_package(variant)
        pip_installed, pip_status = check_pip_package(variant)
        
        results[variant] = {
            "python_import": (installed, status),
            "pip_package": (pip_installed, pip_status)
        }
    
    return results


def check_swe_bench_datasets():
    """Check for SWE-bench datasets."""
    try:
        import datasets
        
        # Common SWE-bench dataset names
        dataset_names = [
            "princeton-nlp/SWE-bench",
            "princeton-nlp/SWE-bench_Lite",
            "swe-bench/SWE-bench",
            "swe-bench/SWE-bench_Lite"
        ]
        
        available_datasets = []
        for dataset_name in dataset_names:
            try:
                # Try to load dataset info (without downloading)
                dataset_info = datasets.get_dataset_infos(dataset_name)
                if dataset_info:
                    available_datasets.append(dataset_name)
            except Exception:
                continue
        
        return available_datasets
    except ImportError:
        return ["datasets package not available"]


def check_evaluation_engine_swe_bench():
    """Check if EvaluationEngineV1_0 has SWE-bench adapter."""
    try:
        # Add current directory to path
        current_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(current_dir))
        
        from EvaluationEngineV1_0.core.swe_bench_adapter import SWEBenchAdapter
        return True, "EvaluationEngineV1_0 SWE-bench adapter available"
    except ImportError as e:
        return False, f"EvaluationEngineV1_0 SWE-bench adapter not available: {e}"


def main():
    """Main function to check SWE-bench installation."""
    print("=" * 60)
    print("SWE-bench Installation Check")
    print("=" * 60)
    
    # Check Python packages
    print("\n1. Python Package Check:")
    variants = check_swe_bench_variants()
    
    for variant, results in variants.items():
        python_installed, python_status = results["python_import"]
        pip_installed, pip_status = results["pip_package"]
        
        print(f"   {variant}:")
        print(f"     Python import: {'✓' if python_installed else '✗'} {python_status}")
        print(f"     Pip package:   {'✓' if pip_installed else '✗'} {pip_status}")
    
    # Check datasets
    print("\n2. SWE-bench Datasets Check:")
    try:
        datasets = check_swe_bench_datasets()
        if datasets and datasets[0] != "datasets package not available":
            print("   Available datasets:")
            for dataset in datasets:
                print(f"     ✓ {dataset}")
        else:
            print("   ✗ No SWE-bench datasets found or datasets package not available")
    except Exception as e:
        print(f"   ✗ Error checking datasets: {e}")
    
    # Check EvaluationEngineV1_0 adapter
    print("\n3. EvaluationEngineV1_0 SWE-bench Adapter Check:")
    adapter_available, adapter_status = check_evaluation_engine_swe_bench()
    print(f"   {'✓' if adapter_available else '✗'} {adapter_status}")
    
    # Check dependencies
    print("\n4. Dependencies Check:")
    dependencies = [
        ("git", "git --version"),
        ("python", f"{sys.executable} --version"),
        ("pip", f"{sys.executable} -m pip --version"),
        ("datasets", None),  # Python package
        ("requests", None),   # Python package
        ("tqdm", None),      # Python package
    ]
    
    for dep_name, command in dependencies:
        if command:
            # Command-line tool
            try:
                result = subprocess.run(
                    command.split(), 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split('\n')[0]
                    print(f"   ✓ {dep_name}: {version}")
                else:
                    print(f"   ✗ {dep_name}: Not available")
            except Exception as e:
                print(f"   ✗ {dep_name}: Error - {e}")
        else:
            # Python package
            installed, status = check_python_package(dep_name)
            print(f"   {'✓' if installed else '✗'} {dep_name}: {status}")
    
    # Installation recommendations
    print("\n5. Installation Recommendations:")
    
    # Check if any SWE-bench variant is installed
    any_installed = any(
        results["python_import"][0] or results["pip_package"][0] 
        for results in variants.values()
    )
    
    if not any_installed:
        print("   📦 To install SWE-bench, try one of these commands:")
        print("      pip install swe-bench")
        print("      pip install git+https://github.com/princeton-nlp/SWE-bench.git")
        print("      pip install datasets  # For dataset access")
    
    if not adapter_available:
        print("   🔧 EvaluationEngineV1_0 SWE-bench adapter is available in the codebase")
        print("      but may need the SWE-bench package to be fully functional")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    
    if any_installed:
        print("   ✅ SWE-bench appears to be installed")
    else:
        print("   ❌ SWE-bench does not appear to be installed")
    
    if adapter_available:
        print("   ✅ EvaluationEngineV1_0 SWE-bench adapter is available")
    else:
        print("   ⚠️  EvaluationEngineV1_0 SWE-bench adapter has import issues")
    
    print("=" * 60)


if __name__ == "__main__":
    main()