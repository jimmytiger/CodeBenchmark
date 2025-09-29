#!/usr/bin/env python3
"""
Simple script to run API tests for EvaluationEngineV1_0.

This script starts an API test server and runs various API tests.
"""

import sys
import time
import asyncio
import logging
from pathlib import Path

from .api.api_test_server import APITestServer
from .api.api_test_client import APITestClient
from .api.curl_test_generator import CurlTestGenerator
from .api.async_evaluation_manager import AsyncEvaluationManager
from .core.error_handler import setup_error_logging


def test_basic_api_endpoints(client):
    """Test basic API endpoints."""
    print("Testing basic API endpoints...")
    
    results = {}
    
    # Health check
    success, result = client.test_health_check()
    results['health'] = success
    print(f"  Health check: {'PASSED' if success else 'FAILED'}")
    if success:
        response_time = result.get('response_time', 0)
        print(f"    Response time: {response_time:.3f}s")
    
    # List tasks
    success, result = client.test_list_tasks()
    results['list_tasks'] = success
    print(f"  List tasks: {'PASSED' if success else 'FAILED'}")
    if success:
        tasks = result.get('response_data', {}).get('tasks', [])
        print(f"    Found {len(tasks)} tasks")
    
    # List adapters
    success, result = client.test_list_adapters()
    results['list_adapters'] = success
    print(f"  List adapters: {'PASSED' if success else 'FAILED'}")
    if success:
        adapters = result.get('response_data', {}).get('adapters', [])
        print(f"    Found {len(adapters)} adapters")
    
    # List evaluations
    success, result = client.test_list_evaluations()
    results['list_evaluations'] = success
    print(f"  List evaluations: {'PASSED' if success else 'FAILED'}")
    
    return results


def test_evaluation_workflow(client):
    """Test complete evaluation workflow."""
    print("Testing evaluation workflow...")
    
    # Create evaluation
    model_id = "test_model"
    tasks = ["hellaswag"]
    config = {"limit": 3, "test_mode": True}
    
    success, result = client.test_create_evaluation(model_id, tasks, config)
    print(f"  Create evaluation: {'PASSED' if success else 'FAILED'}")
    
    if not success:
        return {"create_evaluation": False}
    
    evaluation_id = result.get('response_data', {}).get('evaluation_id')
    if not evaluation_id:
        print("    No evaluation ID returned")
        return {"create_evaluation": False}
    
    print(f"    Evaluation ID: {evaluation_id}")
    
    # Wait for completion
    print("  Waiting for evaluation completion...")
    success, completion_result = client.wait_for_evaluation_completion(
        evaluation_id, max_wait_time=60, poll_interval=2
    )
    
    print(f"  Wait for completion: {'PASSED' if success else 'FAILED'}")
    
    if success:
        # Get results
        success, results = client.test_get_evaluation_results(evaluation_id)
        print(f"  Get results: {'PASSED' if success else 'FAILED'}")
        
        if success:
            results_data = results.get('response_data', {})
            task_results = results_data.get('task_results', [])
            print(f"    Retrieved results for {len(task_results)} tasks")
        
        return {
            "create_evaluation": True,
            "wait_completion": True,
            "get_results": success
        }
    else:
        return {
            "create_evaluation": True,
            "wait_completion": False,
            "get_results": False
        }


async def test_concurrent_evaluations(base_url):
    """Test concurrent evaluations."""
    print("Testing concurrent evaluations...")
    
    # Create async manager
    async_manager = AsyncEvaluationManager(
        base_url=base_url,
        max_concurrent=3,
        timeout=30
    )
    
    # Create evaluation configs
    evaluation_configs = [
        {
            "model_id": f"concurrent_model_{i}",
            "tasks": ["hellaswag"],
            "config": {"limit": 2, "concurrent_id": i}
        }
        for i in range(3)
    ]
    
    # Run concurrent evaluations
    results = await async_manager.run_concurrent_evaluations(evaluation_configs)
    
    print(f"  Concurrent evaluations: {'PASSED' if results['successful_completions'] > 0 else 'FAILED'}")
    print(f"    Total evaluations: {results['total_evaluations']}")
    print(f"    Successful creations: {results['successful_creations']}")
    print(f"    Successful completions: {results['successful_completions']}")
    print(f"    Total time: {results['total_time']:.2f}s")
    
    if results['errors']:
        print(f"    Errors: {len(results['errors'])}")
    
    return results['successful_completions'] > 0


def generate_curl_commands(base_url):
    """Generate curl commands for manual testing."""
    print("Generating curl commands...")
    
    generator = CurlTestGenerator(base_url=base_url)
    
    # Generate examples file
    config = {
        "model_id": "test_model",
        "tasks": ["hellaswag", "arc_easy"],
        "evaluation_config": {"limit": 5}
    }
    
    examples = generator.generate_curl_examples_file(config)
    
    # Save examples
    examples_path = Path("curl_examples.txt")
    with open(examples_path, 'w') as f:
        f.write(examples)
    
    print(f"  Curl examples saved to: {examples_path}")
    
    # Generate comprehensive test script
    script_content = generator.generate_comprehensive_test_script(config)
    script_path = Path("api_test_script.sh")
    generator.save_test_script(script_content, script_path)
    
    print(f"  Test script saved to: {script_path}")
    print(f"  Run with: chmod +x {script_path} && ./{script_path}")
    
    return True


def main():
    """Main function to run all API tests."""
    # Setup logging
    setup_error_logging("INFO", "api_tests.log")
    
    print("EvaluationEngineV1_0 API Testing")
    print("=" * 40)
    
    # Configuration
    host = "localhost"
    port = 8001
    base_url = f"http://{host}:{port}"
    
    # Start API server
    print(f"Starting API test server on {host}:{port}...")
    server = APITestServer(host=host, port=port)
    
    try:
        server.start_server()
        
        if not server.is_running():
            print("❌ Failed to start API server")
            sys.exit(1)
        
        print("✅ API server started successfully")
        
        # Create API client
        client = APITestClient(base_url=base_url, timeout=30)
        
        results = {}
        
        # Test basic endpoints
        print("\n1. Testing basic endpoints...")
        basic_results = test_basic_api_endpoints(client)
        results.update(basic_results)
        
        # Test evaluation workflow
        print("\n2. Testing evaluation workflow...")
        workflow_results = test_evaluation_workflow(client)
        results.update(workflow_results)
        
        # Test concurrent evaluations
        print("\n3. Testing concurrent evaluations...")
        concurrent_success = asyncio.run(test_concurrent_evaluations(base_url))
        results['concurrent_evaluations'] = concurrent_success
        
        # Generate curl commands
        print("\n4. Generating curl commands...")
        curl_success = generate_curl_commands(base_url)
        results['curl_generation'] = curl_success
        
        # Clean up client
        client.close()
        
        # Summary
        print("\n" + "=" * 40)
        print("API Test Summary:")
        total_tests = len(results)
        passed_tests = sum(1 for success in results.values() if success)
        
        for test_name, success in results.items():
            status = "PASSED" if success else "FAILED"
            print(f"  {test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All API tests passed!")
            return True
        else:
            print("❌ Some API tests failed. Check the logs for details.")
            return False
    
    except KeyboardInterrupt:
        print("\nAPI tests interrupted by user")
        return False
    except Exception as e:
        print(f"\nAPI test execution failed: {e}")
        return False
    
    finally:
        # Stop server
        if server.is_running():
            print("\nStopping API server...")
            server.stop_server()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)