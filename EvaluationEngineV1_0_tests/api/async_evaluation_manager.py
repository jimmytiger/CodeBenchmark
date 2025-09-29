"""
Asynchronous evaluation manager for handling concurrent API requests.
"""

import asyncio
import aiohttp
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import json

from ..models.test_models import TestConfiguration
from ..core.error_handler import APIError, ExecutionError


class AsyncEvaluationManager:
    """Manages asynchronous evaluation requests and monitoring."""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 max_concurrent: int = 10, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.AsyncEvaluationManager")
        
        # Semaphore for controlling concurrency
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Callbacks
        self.evaluation_started_callbacks: List[Callable[[str, Dict], None]] = []
        self.evaluation_completed_callbacks: List[Callable[[str, Dict], None]] = []
        self.evaluation_failed_callbacks: List[Callable[[str, str], None]] = []
    
    async def create_evaluation(self, session: aiohttp.ClientSession,
                              model_id: str, tasks: List[str],
                              config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a single evaluation asynchronously."""
        async with self.semaphore:
            try:
                data = {
                    "model_id": model_id,
                    "tasks": tasks,
                    "config": config or {}
                }
                
                async with session.post(
                    f"{self.base_url}/api/v1/evaluations",
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    result = {
                        "status_code": response.status,
                        "response_time": time.time(),  # Will be calculated properly
                        "response_data": await response.json() if response.content_length else None
                    }
                    
                    if response.status == 201:
                        evaluation_id = result["response_data"].get("evaluation_id")
                        if evaluation_id:
                            # Notify callbacks
                            for callback in self.evaluation_started_callbacks:
                                try:
                                    callback(evaluation_id, result)
                                except Exception as e:
                                    self.logger.warning(f"Evaluation started callback failed: {e}")
                    
                    return result
                    
            except asyncio.TimeoutError:
                raise APIError("Request timed out")
            except Exception as e:
                raise APIError(f"Request failed: {e}")
    
    async def get_evaluation_status(self, session: aiohttp.ClientSession,
                                  evaluation_id: str) -> Dict[str, Any]:
        """Get evaluation status asynchronously."""
        try:
            async with session.get(
                f"{self.base_url}/api/v1/evaluations/{evaluation_id}/status",
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                result = {
                    "status_code": response.status,
                    "response_time": time.time(),
                    "response_data": await response.json() if response.content_length else None
                }
                
                return result
                
        except asyncio.TimeoutError:
            raise APIError("Status request timed out")
        except Exception as e:
            raise APIError(f"Status request failed: {e}")
    
    async def get_evaluation_results(self, session: aiohttp.ClientSession,
                                   evaluation_id: str) -> Dict[str, Any]:
        """Get evaluation results asynchronously."""
        try:
            async with session.get(
                f"{self.base_url}/api/v1/evaluations/{evaluation_id}/results",
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                result = {
                    "status_code": response.status,
                    "response_time": time.time(),
                    "response_data": await response.json() if response.content_length else None
                }
                
                return result
                
        except asyncio.TimeoutError:
            raise APIError("Results request timed out")
        except Exception as e:
            raise APIError(f"Results request failed: {e}")
    
    async def wait_for_evaluation_completion(self, session: aiohttp.ClientSession,
                                           evaluation_id: str,
                                           max_wait_time: int = 300,
                                           poll_interval: int = 5) -> Dict[str, Any]:
        """Wait for evaluation to complete asynchronously."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                status_result = await self.get_evaluation_status(session, evaluation_id)
                
                if status_result["status_code"] != 200:
                    return {"success": False, "error": "Failed to get status", "result": status_result}
                
                status_data = status_result.get("response_data", {})
                status = status_data.get("status")
                
                if status == "completed":
                    # Notify completion callbacks
                    for callback in self.evaluation_completed_callbacks:
                        try:
                            callback(evaluation_id, status_data)
                        except Exception as e:
                            self.logger.warning(f"Evaluation completed callback failed: {e}")
                    
                    return {"success": True, "status": status, "result": status_result}
                
                elif status in ["failed", "cancelled"]:
                    # Notify failure callbacks
                    error_msg = status_data.get("error", f"Evaluation {status}")
                    for callback in self.evaluation_failed_callbacks:
                        try:
                            callback(evaluation_id, error_msg)
                        except Exception as e:
                            self.logger.warning(f"Evaluation failed callback failed: {e}")
                    
                    return {"success": False, "status": status, "result": status_result}
                
                # Still running, wait and check again
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Evaluation did not complete within timeout"}
    
    async def run_concurrent_evaluations(self, evaluation_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run multiple evaluations concurrently."""
        self.logger.info(f"Starting {len(evaluation_configs)} concurrent evaluations")
        
        results = {
            "total_evaluations": len(evaluation_configs),
            "successful_creations": 0,
            "successful_completions": 0,
            "failed_evaluations": 0,
            "evaluation_results": [],
            "total_time": 0.0,
            "average_response_time": 0.0,
            "errors": []
        }
        
        start_time = time.time()
        
        try:
            # Create aiohttp session
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            ) as session:
                
                # Create all evaluations concurrently
                creation_tasks = []
                for i, config in enumerate(evaluation_configs):
                    task = self.create_evaluation(
                        session,
                        config.get("model_id", f"test_model_{i}"),
                        config.get("tasks", ["hellaswag"]),
                        config.get("config", {})
                    )
                    creation_tasks.append(task)
                
                # Wait for all creations to complete
                creation_results = await asyncio.gather(*creation_tasks, return_exceptions=True)
                
                # Process creation results
                evaluation_ids = []
                total_response_time = 0.0
                
                for i, result in enumerate(creation_results):
                    if isinstance(result, Exception):
                        results["errors"].append(f"Creation {i} failed: {str(result)}")
                        results["failed_evaluations"] += 1
                    else:
                        if result["status_code"] == 201:
                            results["successful_creations"] += 1
                            evaluation_id = result["response_data"].get("evaluation_id")
                            if evaluation_id:
                                evaluation_ids.append(evaluation_id)
                        else:
                            results["errors"].append(f"Creation {i} failed with status {result['status_code']}")
                            results["failed_evaluations"] += 1
                        
                        total_response_time += result.get("response_time", 0.0)
                
                # Wait for all evaluations to complete
                if evaluation_ids:
                    completion_tasks = []
                    for eval_id in evaluation_ids:
                        task = self.wait_for_evaluation_completion(session, eval_id)
                        completion_tasks.append(task)
                    
                    completion_results = await asyncio.gather(*completion_tasks, return_exceptions=True)
                    
                    # Process completion results
                    for i, result in enumerate(completion_results):
                        eval_id = evaluation_ids[i] if i < len(evaluation_ids) else f"unknown_{i}"
                        
                        if isinstance(result, Exception):
                            results["errors"].append(f"Completion {eval_id} failed: {str(result)}")
                            results["failed_evaluations"] += 1
                        else:
                            if result.get("success", False):
                                results["successful_completions"] += 1
                                
                                # Get final results
                                try:
                                    final_result = await self.get_evaluation_results(session, eval_id)
                                    results["evaluation_results"].append({
                                        "evaluation_id": eval_id,
                                        "result": final_result
                                    })
                                except Exception as e:
                                    results["errors"].append(f"Failed to get results for {eval_id}: {str(e)}")
                            else:
                                results["errors"].append(f"Completion {eval_id} failed: {result.get('error', 'Unknown error')}")
                                results["failed_evaluations"] += 1
                
                # Calculate metrics
                results["average_response_time"] = (
                    total_response_time / len(creation_results) 
                    if creation_results else 0.0
                )
        
        except Exception as e:
            results["errors"].append(f"Concurrent evaluation failed: {str(e)}")
            self.logger.error(f"Concurrent evaluation error: {e}")
        
        finally:
            results["total_time"] = time.time() - start_time
        
        self.logger.info(f"Concurrent evaluations completed: {results['successful_completions']}/{results['total_evaluations']} successful")
        
        return results
    
    async def run_load_test(self, model_id: str, tasks: List[str],
                          num_requests: int = 10, ramp_up_time: int = 10) -> Dict[str, Any]:
        """Run load test with gradual ramp-up."""
        self.logger.info(f"Starting load test: {num_requests} requests over {ramp_up_time}s")
        
        results = {
            "num_requests": num_requests,
            "ramp_up_time": ramp_up_time,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": [],
            "total_time": 0.0,
            "requests_per_second": 0.0
        }
        
        start_time = time.time()
        
        try:
            # Calculate delay between requests
            delay_between_requests = ramp_up_time / num_requests if num_requests > 0 else 0
            
            # Create evaluation configs
            evaluation_configs = []
            for i in range(num_requests):
                config = {
                    "model_id": f"{model_id}_load_{i}",
                    "tasks": tasks,
                    "config": {"load_test": True, "request_id": i}
                }
                evaluation_configs.append(config)
            
            # Create aiohttp session
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            ) as session:
                
                # Send requests with ramp-up
                tasks = []
                for i, config in enumerate(evaluation_configs):
                    # Wait for ramp-up delay
                    if i > 0:
                        await asyncio.sleep(delay_between_requests)
                    
                    # Create task
                    task = self._load_test_request(session, config, i)
                    tasks.append(task)
                
                # Wait for all requests to complete
                request_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(request_results):
                    if isinstance(result, Exception):
                        results["failed_requests"] += 1
                        results["errors"].append(f"Request {i}: {str(result)}")
                    else:
                        if result.get("success", False):
                            results["successful_requests"] += 1
                            results["response_times"].append(result.get("response_time", 0.0))
                        else:
                            results["failed_requests"] += 1
                            results["errors"].append(f"Request {i}: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            results["errors"].append(f"Load test failed: {str(e)}")
            self.logger.error(f"Load test error: {e}")
        
        finally:
            results["total_time"] = time.time() - start_time
            results["requests_per_second"] = num_requests / results["total_time"] if results["total_time"] > 0 else 0.0
        
        self.logger.info(f"Load test completed: {results['successful_requests']}/{num_requests} successful")
        
        return results
    
    async def _load_test_request(self, session: aiohttp.ClientSession,
                               config: Dict[str, Any], request_id: int) -> Dict[str, Any]:
        """Execute a single load test request."""
        request_start = time.time()
        
        try:
            result = await self.create_evaluation(
                session,
                config["model_id"],
                config["tasks"],
                config["config"]
            )
            
            response_time = time.time() - request_start
            
            return {
                "success": result["status_code"] == 201,
                "response_time": response_time,
                "status_code": result["status_code"],
                "request_id": request_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - request_start,
                "request_id": request_id
            }
    
    def add_evaluation_started_callback(self, callback: Callable[[str, Dict], None]) -> None:
        """Add callback for evaluation started events."""
        self.evaluation_started_callbacks.append(callback)
    
    def add_evaluation_completed_callback(self, callback: Callable[[str, Dict], None]) -> None:
        """Add callback for evaluation completed events."""
        self.evaluation_completed_callbacks.append(callback)
    
    def add_evaluation_failed_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add callback for evaluation failed events."""
        self.evaluation_failed_callbacks.append(callback)


def create_async_evaluation_manager(base_url: str = "http://localhost:8000",
                                   max_concurrent: int = 10,
                                   timeout: int = 30) -> AsyncEvaluationManager:
    """Factory function to create an async evaluation manager."""
    return AsyncEvaluationManager(
        base_url=base_url,
        max_concurrent=max_concurrent,
        timeout=timeout
    )