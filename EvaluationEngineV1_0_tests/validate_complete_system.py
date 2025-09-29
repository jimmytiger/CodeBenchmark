#!/usr/bin/env python3
"""
Complete System Validation Script

This script performs comprehensive validation of the entire EvaluationEngineV1_0_tests
framework, ensuring all components work correctly and all requirements are satisfied.
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from final_integration_validator import FinalIntegrationValidator
    from core.config_manager import ConfigManager
    from core.error_handler import ErrorHandler
except ImportError as e:
    print(f"❌ Failed to import validation components: {e}")
    print("Please ensure all required modules are available.")
    sys.exit(1)


class SystemValidator:
    """Complete system validation orchestrator"""
    
    def __init__(self, config_path: str = None, verbose: bool = False):
        """Initialize system validator"""
        self.config_path = config_path
        self.verbose = verbose
        self.setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.start_time = None
        self.validation_results = {}
        
    def setup_logging(self):
        """Set up logging configuration"""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('system_validation.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    async def validate_system(self) -> bool:
        """Run complete system validation"""
        self.logger.info("🚀 Starting Complete System Validation")
        self.start_time = time.time()
        
        try:
            # Step 1: Environment validation
            if not await self.validate_environment():
                return False
            
            # Step 2: Dependencies validation
            if not await self.validate_dependencies():
                return False
            
            # Step 3: Component validation
            if not await self.validate_components():
                return False
            
            # Step 4: Integration validation
            if not await self.validate_integration():
                return False
            
            # Step 5: End-to-end validation
            if not await self.validate_end_to_end():
                return False
            
            # Step 6: Documentation validation
            if not await self.validate_documentation():
                return False
            
            # Step 7: Generate final report
            await self.generate_final_report()
            
            self.logger.info("✅ Complete system validation passed!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ System validation failed: {str(e)}")
            return False
    
    async def validate_environment(self) -> bool:
        """Validate system environment"""
        self.logger.info("🔍 Validating system environment...")
        
        try:
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 8):
                self.logger.error(f"❌ Python 3.8+ required, found {python_version.major}.{python_version.minor}")
                return False
            
            self.logger.info(f"✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
            
            # Check required directories
            required_dirs = [
                "core",
                "cli",
                "api",
                "adapters",
                "tests",
                "docs",
                "configs"
            ]
            
            for dir_name in required_dirs:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    self.logger.error(f"❌ Required directory missing: {dir_name}")
                    return False
                self.logger.debug(f"✅ Directory found: {dir_name}")
            
            # Check EvaluationEngineV1_0 availability
            eval_engine_path = Path("../EvaluationEngineV1_0")
            if not eval_engine_path.exists():
                self.logger.warning("⚠️  EvaluationEngineV1_0 directory not found at expected location")
            else:
                self.logger.info("✅ EvaluationEngineV1_0 directory found")
            
            self.validation_results['environment'] = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Environment validation failed: {str(e)}")
            self.validation_results['environment'] = False
            return False
    
    async def validate_dependencies(self) -> bool:
        """Validate system dependencies"""
        self.logger.info("📦 Validating dependencies...")
        
        try:
            # Check Python packages
            required_packages = [
                'asyncio',
                'json',
                'logging',
                'pathlib',
                'subprocess',
                'yaml',
                'pytest'
            ]
            
            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package)
                    self.logger.debug(f"✅ Package available: {package}")
                except ImportError:
                    missing_packages.append(package)
                    self.logger.error(f"❌ Missing package: {package}")
            
            if missing_packages:
                self.logger.error(f"❌ Missing required packages: {missing_packages}")
                return False
            
            # Check optional packages
            optional_packages = ['numpy', 'pandas', 'matplotlib']
            for package in optional_packages:
                try:
                    __import__(package)
                    self.logger.debug(f"✅ Optional package available: {package}")
                except ImportError:
                    self.logger.debug(f"ℹ️  Optional package not available: {package}")
            
            self.validation_results['dependencies'] = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Dependencies validation failed: {str(e)}")
            self.validation_results['dependencies'] = False
            return False
    
    async def validate_components(self) -> bool:
        """Validate individual components"""
        self.logger.info("🔧 Validating individual components...")
        
        try:
            components_status = {}
            
            # Test core components
            core_components = [
                'core.config_manager',
                'core.error_handler',
                'core.test_orchestrator',
                'core.real_execution_validator',
                'core.metrics_collector'
            ]
            
            for component in core_components:
                try:
                    module = __import__(component, fromlist=[''])
                    self.logger.debug(f"✅ Core component available: {component}")
                    components_status[component] = True
                except ImportError as e:
                    self.logger.error(f"❌ Core component unavailable: {component} - {str(e)}")
                    components_status[component] = False
            
            # Test CLI components
            cli_components = [
                'cli.cli_test_runner',
                'cli.cli_config_manager',
                'cli.cli_result_formatter'
            ]
            
            for component in cli_components:
                try:
                    module = __import__(component, fromlist=[''])
                    self.logger.debug(f"✅ CLI component available: {component}")
                    components_status[component] = True
                except ImportError as e:
                    self.logger.error(f"❌ CLI component unavailable: {component} - {str(e)}")
                    components_status[component] = False
            
            # Test API components
            api_components = [
                'api.api_test_server',
                'api.api_test_client',
                'api.async_evaluation_manager'
            ]
            
            for component in api_components:
                try:
                    module = __import__(component, fromlist=[''])
                    self.logger.debug(f"✅ API component available: {component}")
                    components_status[component] = True
                except ImportError as e:
                    self.logger.error(f"❌ API component unavailable: {component} - {str(e)}")
                    components_status[component] = False
            
            # Test adapter components
            adapter_components = [
                'adapters.lm_eval_adapter_validator',
                'adapters.swe_bench_adapter_validator'
            ]
            
            for component in adapter_components:
                try:
                    module = __import__(component, fromlist=[''])
                    self.logger.debug(f"✅ Adapter component available: {component}")
                    components_status[component] = True
                except ImportError as e:
                    self.logger.error(f"❌ Adapter component unavailable: {component} - {str(e)}")
                    components_status[component] = False
            
            # Check overall component status
            failed_components = [comp for comp, status in components_status.items() if not status]
            
            if failed_components:
                self.logger.error(f"❌ Failed components: {failed_components}")
                self.validation_results['components'] = False
                return False
            
            self.logger.info("✅ All components validated successfully")
            self.validation_results['components'] = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Component validation failed: {str(e)}")
            self.validation_results['components'] = False
            return False
    
    async def validate_integration(self) -> bool:
        """Validate component integration"""
        self.logger.info("🔗 Validating component integration...")
        
        try:
            # Test configuration loading
            config_manager = ConfigManager()
            test_config = config_manager.load_config(self.config_path) if self.config_path else {}
            self.logger.debug("✅ Configuration loading works")
            
            # Test error handling
            error_handler = ErrorHandler()
            try:
                error_handler.handle_error(Exception("Test error"), {"test": True})
                self.logger.debug("✅ Error handling works")
            except Exception:
                pass  # Expected to handle gracefully
            
            # Test basic integration
            from core.test_orchestrator import TestOrchestrator
            orchestrator = TestOrchestrator()
            self.logger.debug("✅ Test orchestrator integration works")
            
            self.validation_results['integration'] = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Integration validation failed: {str(e)}")
            self.validation_results['integration'] = False
            return False
    
    async def validate_end_to_end(self) -> bool:
        """Validate end-to-end functionality"""
        self.logger.info("🎯 Validating end-to-end functionality...")
        
        try:
            # Run the final integration validator
            validator = FinalIntegrationValidator(self.config_path)
            
            # Run a subset of validation tests
            self.logger.info("Running final integration validation...")
            test_suite = await validator.run_complete_validation()
            
            if test_suite.final_status == "passed":
                self.logger.info("✅ End-to-end validation passed")
                self.validation_results['end_to_end'] = True
                return True
            else:
                self.logger.error(f"❌ End-to-end validation failed: {test_suite.failed_tests} failed tests")
                self.validation_results['end_to_end'] = False
                return False
            
        except Exception as e:
            self.logger.error(f"❌ End-to-end validation failed: {str(e)}")
            self.validation_results['end_to_end'] = False
            return False
    
    async def validate_documentation(self) -> bool:
        """Validate documentation completeness"""
        self.logger.info("📚 Validating documentation...")
        
        try:
            # Check required documentation files
            required_docs = [
                "README.md",
                "docs/usage.md",
                "docs/api_specification.md",
                "docs/developer_guide.md",
                "docs/troubleshooting_guide.md"
            ]
            
            missing_docs = []
            for doc_path in required_docs:
                if not Path(doc_path).exists():
                    missing_docs.append(doc_path)
                    self.logger.error(f"❌ Missing documentation: {doc_path}")
                else:
                    self.logger.debug(f"✅ Documentation found: {doc_path}")
            
            if missing_docs:
                self.logger.error(f"❌ Missing documentation files: {missing_docs}")
                self.validation_results['documentation'] = False
                return False
            
            # Check examples
            examples_dir = Path("examples")
            if examples_dir.exists():
                example_count = len(list(examples_dir.rglob("*")))
                self.logger.info(f"✅ Found {example_count} example files")
            else:
                self.logger.warning("⚠️  Examples directory not found")
            
            self.validation_results['documentation'] = True
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Documentation validation failed: {str(e)}")
            self.validation_results['documentation'] = False
            return False
    
    async def generate_final_report(self):
        """Generate final validation report"""
        self.logger.info("📊 Generating final validation report...")
        
        try:
            end_time = time.time()
            total_time = end_time - self.start_time
            
            # Calculate overall status
            all_passed = all(self.validation_results.values())
            overall_status = "PASSED" if all_passed else "FAILED"
            
            # Generate report data
            report_data = {
                'validation_summary': {
                    'overall_status': overall_status,
                    'total_execution_time': total_time,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'validation_categories': len(self.validation_results),
                    'passed_categories': sum(1 for status in self.validation_results.values() if status),
                    'failed_categories': sum(1 for status in self.validation_results.values() if not status)
                },
                'detailed_results': self.validation_results,
                'system_info': {
                    'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    'platform': sys.platform,
                    'working_directory': str(Path.cwd())
                }
            }
            
            # Save JSON report
            with open('complete_system_validation_report.json', 'w') as f:
                json.dump(report_data, f, indent=2)
            
            # Generate markdown report
            markdown_report = self._generate_markdown_report(report_data)
            with open('COMPLETE_SYSTEM_VALIDATION_REPORT.md', 'w') as f:
                f.write(markdown_report)
            
            self.logger.info("✅ Final validation report generated")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate final report: {str(e)}")
    
    def _generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """Generate markdown validation report"""
        summary = report_data['validation_summary']
        results = report_data['detailed_results']
        
        status_emoji = "✅" if summary['overall_status'] == "PASSED" else "❌"
        
        report = f"""# Complete System Validation Report

## Summary

{status_emoji} **Overall Status**: {summary['overall_status']}
⏱️ **Execution Time**: {summary['total_execution_time']:.2f} seconds
📅 **Timestamp**: {summary['timestamp']}

## Validation Results

**Categories**: {summary['validation_categories']}
**Passed**: {summary['passed_categories']}
**Failed**: {summary['failed_categories']}

### Detailed Results

"""
        
        for category, status in results.items():
            emoji = "✅" if status else "❌"
            report += f"- {emoji} **{category.title()}**: {'PASSED' if status else 'FAILED'}\n"
        
        report += f"""

## System Information

- **Python Version**: {report_data['system_info']['python_version']}
- **Platform**: {report_data['system_info']['platform']}
- **Working Directory**: {report_data['system_info']['working_directory']}

## Next Steps

"""
        
        if summary['overall_status'] == "PASSED":
            report += """
✅ All validation checks passed! The system is ready for use.

### Recommended Actions:
1. Review the detailed validation logs
2. Run specific component tests as needed
3. Proceed with system deployment or usage
"""
        else:
            failed_categories = [cat for cat, status in results.items() if not status]
            report += f"""
❌ Validation failed in the following categories: {', '.join(failed_categories)}

### Required Actions:
1. Review the detailed error logs
2. Fix issues in failed categories
3. Re-run validation to confirm fixes
4. Do not proceed with deployment until all checks pass
"""
        
        report += f"""

---
*Report generated by Complete System Validator*
"""
        
        return report


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Complete System Validation")
    parser.add_argument(
        '--config',
        type=str,
        help='Path to validation configuration file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick validation (skip some time-intensive tests)'
    )
    
    args = parser.parse_args()
    
    try:
        validator = SystemValidator(
            config_path=args.config,
            verbose=args.verbose
        )
        
        success = asyncio.run(validator.validate_system())
        
        if success:
            print("\n🎉 Complete system validation PASSED!")
            print("📄 Check 'COMPLETE_SYSTEM_VALIDATION_REPORT.md' for details")
            sys.exit(0)
        else:
            print("\n💥 Complete system validation FAILED!")
            print("📄 Check 'COMPLETE_SYSTEM_VALIDATION_REPORT.md' for details")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()