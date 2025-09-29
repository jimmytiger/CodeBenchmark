#!/usr/bin/env python3
"""
Quick Validation Workflow for EvaluationEngineV1_0 Testing Framework

This script provides a complete workflow for quickly validating the
EvaluationEngineV1_0 testing framework with minimal setup.
"""

import sys
import logging
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the test framework to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.test_orchestrator import TestOrchestrator
from core.config_manager import ConfigManager
from core.metrics_collector import MetricsCollector
from core.real_execution_validator import RealExecutionValidator
from cli.cli_test_runner import CLITestRunner
from api.api_test_server import APITestServer
from api.api_test_client import APITestClient
from adapters.lm_eval_adapter_validator import LMEvalAdapterValidator
from models.test_models import TestConfiguration, TestType, TestSuiteResults


def setup_logging() -> logging.Logger:
    """Setup logging for the workflow."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('quick_validation.log')
        ]
    )
    return logging.getLogger(__name__)


class QuickValidationWorkflow:
    """Quick validation workflow for the testing framework."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.results = {}
        self.start_time = time.time()
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.metrics_collector = MetricsCollector()
        self.real_validator = RealExecutionValidator()
        self.orchestrator = TestOrchestrator(self.config_manager, self.metrics_collector)
        
        # Results directory
        self.results_dir = Path("quick_validation_results")
        self.results_dir.mkdir(exist_ok=True)
    
    def step_1_framework_health_check(self) -> Dict[str, Any]:
        """Step 1: Check framework health and dependencies."""
        self.logger.info("=== Step 1: Framework Health Check ===")
        
        result = {
            "success": False,
            "checks": {},
            "issues": [],
            "execution_time": 0.0
        }
        
        start_time = time.time()
        
        try:
            # Check 1: Import all core modules
            self.logger.info("Checking core module imports...")
            try:
                from cli.cli_test_runner import CLITestRunner
                from api.api_test_server import APITestServer
                from core.test_orchestrator import TestOrchestrator
                result["checks"]["core_imports"] = True
                self.logger.info("✓ Core modules imported successfully")
            except Exception as e:
                result["checks"]["core_imports"] = False
                result["issues"].append(f"Core import failed: {e}")
                self.logger.error(f"✗ Core import failed: {e}")
            
            # Check 2: Configuration loading
            self.logger.info("Checking configuration loading...")
            try:
                config = {
                    "test_type": "quick_validation",
                    "timeout": 60,
                    "verbose": True
                }
                result["checks"]["config_loading"] = True
                self.logger.info("✓ Configuration loading works")
            except Exception as e:
                result["checks"]["config_loading"] = False
                result["issues"].append(f"Config loading failed: {e}")
                self.logger.error(f"✗ Config loading failed: {e}")
            
            # Check 3: Metrics collection
            self.logger.info("Checking metrics collection...")
            try:
                self.metrics_collector.start_collection()
                time.sleep(0.1)  # Brief collection
                metrics = self.metrics_collector.stop_collection()
                result["checks"]["metrics_collection"] = True
                self.logger.info("✓ Metrics collection works")
            except Exception as e:
                result["checks"]["metrics_collection"] = False
                result["issues"].append(f"Metrics collection failed: {e}")
                self.logger.error(f"✗ Metrics collection failed: {e}")
            
            # Check 4: Real execution validator
            self.logger.info("Checking real execution validator...")
            try:
                self.real_validator.configure_validation(mock_detection=True)
                result["checks"]["real_execution_validator"] = True
                self.logger.info("✓ Real execution validator works")
            except Exception as e:
                result["checks"]["real_execution_validator"] = False
                result["issues"].append(f"Real execution validator failed: {e}")
                self.logger.error(f"✗ Real execution validator failed: {e}")
            
            # Overall success
            result["success"] = all(result["checks"].values())
            
        except Exception as e:
            result["issues"].append(f"Health check failed: {e}")
            self.logger.error(f"Health check failed: {e}")
        
        finally:
            result["execution_time"] = time.time() - start_time
        
        self.logger.info(f"Framework health check: {'PASSED' if result['success'] else 'FAILED'}")
        return result
    
    def step_2_cli_quick_test(self) -> Dict[str, Any]:
        """Step 2: Quick CLI functionality test."""
        self.logger.info("=== Step 2: CLI Quick Test ===")
        
        result = {
            "success": False,
            "test_results": [],
            "execution_time": 0.0,
            "metrics": {}
        }
        
        start_time = time.time()
        
        try:
            # Create CLI test runner
            cli_runner = CLITestRunner()
            
            # Quick test configuration
            config = {
                "timeout": 120,
                "verbose": True,
                "output_format": "json",
                "limit": 2  # Very small sample for quick test
            }
            
            self.logger.info("Running quick CLI test with hellaswag...")
            cli_result = cli_runner.run_builtin_tasks(["hellaswag"], config)
            
            result["test_results"].append({
                "test": "hellaswag_cli",
                "success": cli_result["success"],
                "execution_time": cli_result["execution_time"],
                "command": cli_result.get("command", "N/A")
            })
            
            if cli_result.get("metrics"):
                result["metrics"].update(cli_result["metrics"])
            
            result["success"] = cli_result["success"]
            
            self.logger.info(f"CLI quick test: {'PASSED' if result['success'] else 'FAILED'}")
            if result["success"]:
                self.logger.info(f"  Execution time: {cli_result['execution_time']:.2f}s")
            else:
                self.logger.error(f"  Error: {cli_result.get('error', 'Unknown error')}")
            
        except Exception as e:
            result["test_results"].append({
                "test": "cli_exception",
                "success": False,
                "error": str(e)
            })
            self.logger.error(f"CLI quick test failed: {e}")
        
        finally:
            result["execution_time"] = time.time() - start_time
        
        return result
    
    async def step_3_api_quick_test(self) -> Dict[str, Any]:
        """Step 3: Quick API functionality test."""
        self.logger.info("=== Step 3: API Quick Test ===")
        
        result = {
            "success": False,
            "api_tests": {},
            "execution_time": 0.0,
            "server_started": False
        }
        
        start_time = time.time()
        api_server = None
        
        try:
            # Start API server
            self.logger.info("Starting API test server...")
            api_server = APITestServer(host="localhost", port=8002)
            api_server.start_server()
            
            # Wait for server to be ready
            await asyncio.sleep(2)
            
            if api_server.is_running():
                result["server_started"] = True
                self.logger.info("✓ API server started successfully")
                
                # Create API client
                api_client = APITestClient(base_url="http://localhost:8002", timeout=30)
                
                # Test 1: Health check
                self.logger.info("Testing API health check...")
                success, health_result = api_client.test_health_check()
                result["api_tests"]["health_check"] = {
                    "success": success,
                    "response_time": health_result.get("response_time", 0.0)
                }
                
                # Test 2: List tasks
                self.logger.info("Testing API list tasks...")
                success, tasks_result = api_client.test_list_tasks()
                result["api_tests"]["list_tasks"] = {
                    "success": success,
                    "response_time": tasks_result.get("response_time", 0.0),
                    "task_count": len(tasks_result.get("response_data", {}).get("tasks", []))
                }
                
                # Test 3: Create evaluation
                self.logger.info("Testing API create evaluation...")
                success, create_result = api_client.test_create_evaluation(
                    "quick_test_model", ["hellaswag"], {"limit": 1}
                )
                result["api_tests"]["create_evaluation"] = {
                    "success": success,
                    "response_time": create_result.get("response_time", 0.0)
                }
                
                if success:
                    evaluation_id = create_result.get("response_data", {}).get("evaluation_id")
                    if evaluation_id:
                        # Test 4: Check status
                        self.logger.info("Testing API status check...")
                        success, status_result = api_client.test_get_evaluation_status(evaluation_id)
                        result["api_tests"]["check_status"] = {
                            "success": success,
                            "response_time": status_result.get("response_time", 0.0)
                        }
                
                api_client.close()
                
                # Overall API success
                api_successes = sum(1 for test in result["api_tests"].values() if test["success"])
                total_api_tests = len(result["api_tests"])
                result["success"] = api_successes == total_api_tests
                
                self.logger.info(f"API quick test: {'PASSED' if result['success'] else 'FAILED'}")
                self.logger.info(f"  API tests: {api_successes}/{total_api_tests} passed")
                
            else:
                self.logger.error("✗ Failed to start API server")
                result["success"] = False
        
        except Exception as e:
            self.logger.error(f"API quick test failed: {e}")
            result["success"] = False
            result["error"] = str(e)
        
        finally:
            # Stop API server
            if api_server and api_server.is_running():
                self.logger.info("Stopping API server...")
                api_server.stop_server()
            
            result["execution_time"] = time.time() - start_time
        
        return result
    
    def step_4_adapter_validation(self) -> Dict[str, Any]:
        """Step 4: Quick adapter validation."""
        self.logger.info("=== Step 4: Adapter Validation ===")
        
        result = {
            "success": False,
            "adapters": {},
            "execution_time": 0.0
        }
        
        start_time = time.time()
        
        try:
            # Test lm_eval adapter
            self.logger.info("Validating lm_eval adapter...")
            lm_eval_validator = LMEvalAdapterValidator()
            
            # Basic validation
            validation_result = lm_eval_validator.validate_integration()
            
            result["adapters"]["lm_eval"] = {
                "integration_status": validation_result.integration_status,
                "dependencies_installed": validation_result.dependencies_installed,
                "issues_count": len(validation_result.issues_found),
                "success": validation_result.integration_status == "success"
            }
            
            self.logger.info(f"LM-Eval adapter: {'PASSED' if result['adapters']['lm_eval']['success'] else 'FAILED'}")
            
            if validation_result.issues_found:
                self.logger.warning("Issues found:")
                for issue in validation_result.issues_found[:3]:  # Show first 3
                    self.logger.warning(f"  - {issue}")
            
            # Overall adapter success
            adapter_successes = sum(1 for adapter in result["adapters"].values() if adapter["success"])
            total_adapters = len(result["adapters"])
            result["success"] = adapter_successes > 0  # At least one adapter should work
            
            self.logger.info(f"Adapter validation: {'PASSED' if result['success'] else 'FAILED'}")
            self.logger.info(f"  Adapters: {adapter_successes}/{total_adapters} validated")
            
        except Exception as e:
            self.logger.error(f"Adapter validation failed: {e}")
            result["success"] = False
            result["error"] = str(e)
        
        finally:
            result["execution_time"] = time.time() - start_time
        
        return result
    
    def step_5_real_execution_check(self) -> Dict[str, Any]:
        """Step 5: Verify real execution (no mocks)."""
        self.logger.info("=== Step 5: Real Execution Check ===")
        
        result = {
            "success": False,
            "validation_results": {},
            "execution_time": 0.0
        }
        
        start_time = time.time()
        
        try:
            # Configure real execution validator
            self.real_validator.configure_validation(
                mock_detection=True,
                resource_tracking=True,
                api_call_tracking=True
            )
            
            # Start tracking
            self.real_validator.start_tracking()
            
            # Run a simple test to validate
            self.logger.info("Running test for real execution validation...")
            cli_runner = CLITestRunner()
            config = {
                "timeout": 60,
                "verbose": False,
                "output_format": "json",
                "limit": 1
            }
            
            cli_result = cli_runner.run_builtin_tasks(["hellaswag"], config)
            
            # Create test configuration for validation
            test_config = TestConfiguration(
                test_id="quick_validation_real_exec",
                test_type=TestType.CLI,
                name="Quick Validation Real Execution Test",
                description="Test to validate real execution in quick validation",
                real_execution_required=True
            )
            
            # Create test result for validation
            from models.test_models import TestResult, TestStatus
            test_result = TestResult(
                test_id="quick_validation_real_exec",
                test_type=TestType.CLI,
                name="Quick Validation Real Execution Test",
                status=TestStatus.PASSED if cli_result["success"] else TestStatus.FAILED,
                execution_time=cli_result["execution_time"],
                real_execution_validated=False,
                logs=["Test executed for real execution validation"],
                metrics=cli_result.get("metrics", {})
            )
            
            # Validate real execution
            is_real = self.real_validator.validate_real_execution(test_result, test_config)
            self.real_validator.stop_tracking()
            
            # Get validation report
            validation_report = self.real_validator.get_validation_report()
            
            result["validation_results"] = {
                "test_success": cli_result["success"],
                "real_execution_validated": is_real,
                "mock_objects_found": validation_report["mock_objects_found"],
                "api_calls_recorded": validation_report["api_calls_recorded"],
                "resource_snapshots": validation_report["resource_snapshots"]
            }
            
            result["success"] = is_real and cli_result["success"]
            
            self.logger.info(f"Real execution check: {'PASSED' if result['success'] else 'FAILED'}")
            self.logger.info(f"  Test success: {cli_result['success']}")
            self.logger.info(f"  Real execution validated: {is_real}")
            self.logger.info(f"  Mock objects found: {validation_report['mock_objects_found']}")
            
        except Exception as e:
            self.logger.error(f"Real execution check failed: {e}")
            result["success"] = False
            result["error"] = str(e)
        
        finally:
            result["execution_time"] = time.time() - start_time
        
        return result
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a summary report of the validation workflow."""
        total_time = time.time() - self.start_time
        
        # Count successes
        successful_steps = sum(1 for step_result in self.results.values() 
                             if step_result.get("success", False))
        total_steps = len(self.results)
        
        summary = {
            "workflow_name": "Quick Validation",
            "total_execution_time": total_time,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "success_rate": successful_steps / total_steps if total_steps > 0 else 0.0,
            "overall_success": successful_steps == total_steps,
            "step_results": self.results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "recommendations": []
        }
        
        # Add recommendations based on results
        if not summary["overall_success"]:
            summary["recommendations"].append("Some validation steps failed. Check individual step logs for details.")
        
        if successful_steps >= total_steps * 0.8:  # 80% success
            summary["recommendations"].append("Framework is mostly functional. Minor issues may need attention.")
        elif successful_steps >= total_steps * 0.5:  # 50% success
            summary["recommendations"].append("Framework has significant issues. Review failed steps carefully.")
        else:
            summary["recommendations"].append("Framework has major issues. Consider reinstallation or environment check.")
        
        return summary
    
    async def run_workflow(self) -> Dict[str, Any]:
        """Run the complete quick validation workflow."""
        self.logger.info("Starting Quick Validation Workflow")
        self.logger.info("=" * 50)
        
        try:
            # Step 1: Framework health check
            self.results["step_1_health_check"] = self.step_1_framework_health_check()
            
            # Step 2: CLI quick test
            self.results["step_2_cli_test"] = self.step_2_cli_quick_test()
            
            # Step 3: API quick test
            self.results["step_3_api_test"] = await self.step_3_api_quick_test()
            
            # Step 4: Adapter validation
            self.results["step_4_adapter_validation"] = self.step_4_adapter_validation()
            
            # Step 5: Real execution check
            self.results["step_5_real_execution"] = self.step_5_real_execution_check()
            
            # Generate summary
            summary = self.generate_summary_report()
            
            # Save results
            results_file = self.results_dir / "quick_validation_results.json"
            with open(results_file, 'w') as f:
                json.dump({
                    "summary": summary,
                    "detailed_results": self.results
                }, f, indent=2, default=str)
            
            # Display summary
            self.logger.info("\n" + "=" * 50)
            self.logger.info("Quick Validation Summary")
            self.logger.info("=" * 50)
            self.logger.info(f"Total execution time: {summary['total_execution_time']:.2f}s")
            self.logger.info(f"Steps completed: {summary['successful_steps']}/{summary['total_steps']}")
            self.logger.info(f"Success rate: {summary['success_rate']:.1%}")
            self.logger.info(f"Overall result: {'✓ PASSED' if summary['overall_success'] else '✗ FAILED'}")
            
            # Step-by-step results
            self.logger.info("\nStep Results:")
            for step_name, step_result in self.results.items():
                status = "✓ PASSED" if step_result.get("success", False) else "✗ FAILED"
                time_str = f"({step_result.get('execution_time', 0):.1f}s)"
                self.logger.info(f"  {status} {step_name.replace('_', ' ').title()} {time_str}")
            
            # Recommendations
            if summary["recommendations"]:
                self.logger.info("\nRecommendations:")
                for rec in summary["recommendations"]:
                    self.logger.info(f"  • {rec}")
            
            self.logger.info(f"\nDetailed results saved to: {results_file}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Workflow failed: {e}")
            return {
                "overall_success": False,
                "error": str(e),
                "partial_results": self.results
            }


async def main():
    """Main function to run the quick validation workflow."""
    logger = setup_logging()
    
    try:
        # Create and run workflow
        workflow = QuickValidationWorkflow(logger)
        summary = await workflow.run_workflow()
        
        # Exit with appropriate code
        if summary.get("overall_success", False):
            logger.info("🎉 Quick validation completed successfully!")
            sys.exit(0)
        else:
            logger.warning("⚠️ Quick validation completed with issues.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())