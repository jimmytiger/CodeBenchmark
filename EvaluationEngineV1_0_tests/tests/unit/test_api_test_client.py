"""
Unit tests for APITestClient component.

Tests API client functionality for testing evaluation engine.
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
import requests

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from api.api_test_client import APITestClient
from models.test_models import TestResult
from core.error_handler import ExecutionError


class TestAPITestClient:
    """Unit tests for APITestClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_client = APITestClient(base_url='http://localhost:8000')
        self.sample_config = {
            'tasks': ['hellaswag', 'arc_easy'],
            'model': 'gpt-3.5-turbo',
            'timeout': 300
        }
    
    def test_client_initialization(self):
        """Test API client initialization."""
        assert self.api_client.base_url == 'http://localhost:8000'
        assert hasattr(self.api_client, 'session')
        assert isinstance(self.api_client.session, requests.Session)
    
    @patch('requests.Session.post')
    def test_run_evaluation_success(self, mock_post):
        """Test successful evaluation request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'evaluation_id': 'eval_123',
            'status': 'started',
            'message': 'Evaluation started successfully'
        }
        mock_post.return_value = mock_response
        
        result = self.api_client.run_evaluation(self.sample_config)
        
        assert result['evaluation_id'] == 'eval_123'
        assert result['status'] == 'started'
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_run_evaluation_failure(self, mock_post):
        """Test evaluation request failure."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': 'Invalid configuration',
            'details': 'Missing required field: tasks'
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(ExecutionError):
            self.api_client.run_evaluation({})
    
    @patch('requests.Session.get')
    def test_get_evaluation_status(self, mock_get):
        """Test getting evaluation status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'evaluation_id': 'eval_123',
            'status': 'running',
            'progress': 0.5,
            'estimated_completion': '2024-01-01T12:30:00Z'
        }
        mock_get.return_value = mock_response
        
        status = self.api_client.get_evaluation_status('eval_123')
        
        assert status['status'] == 'running'
        assert status['progress'] == 0.5
        mock_get.assert_called_once_with('/api/v1/evaluations/eval_123/status')
    
    @patch('requests.Session.get')
    def test_get_evaluation_results(self, mock_get):
        """Test getting evaluation results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'evaluation_id': 'eval_123',
            'status': 'completed',
            'results': {
                'hellaswag': {'acc': 0.85, 'acc_stderr': 0.02},
                'arc_easy': {'acc': 0.78, 'acc_stderr': 0.03}
            },
            'metadata': {
                'execution_time': 120.5,
                'total_tokens': 1500
            }
        }
        mock_get.return_value = mock_response
        
        results = self.api_client.get_evaluation_results('eval_123')
        
        assert results['status'] == 'completed'
        assert 'hellaswag' in results['results']
        assert results['results']['hellaswag']['acc'] == 0.85
        mock_get.assert_called_once_with('/api/v1/evaluations/eval_123/results')
    
    @patch('requests.Session.get')
    def test_list_available_tasks(self, mock_get):
        """Test listing available tasks."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tasks': [
                {'name': 'hellaswag', 'type': 'multiple_choice', 'description': 'Common sense reasoning'},
                {'name': 'arc_easy', 'type': 'multiple_choice', 'description': 'Science questions'},
                {'name': 'winogrande', 'type': 'multiple_choice', 'description': 'Pronoun resolution'}
            ]
        }
        mock_get.return_value = mock_response
        
        tasks = self.api_client.list_available_tasks()
        
        assert len(tasks['tasks']) == 3
        assert tasks['tasks'][0]['name'] == 'hellaswag'
        mock_get.assert_called_once_with('/api/v1/tasks')
    
    @patch('requests.Session.get')
    def test_list_available_adapters(self, mock_get):
        """Test listing available adapters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'adapters': [
                {'name': 'lm_eval', 'status': 'active', 'version': '0.4.0'},
                {'name': 'swe_bench', 'status': 'active', 'version': '1.0.0'},
                {'name': 'custom_adapter', 'status': 'inactive', 'version': '0.1.0'}
            ]
        }
        mock_get.return_value = mock_response
        
        adapters = self.api_client.list_available_adapters()
        
        assert len(adapters['adapters']) == 3
        assert adapters['adapters'][0]['name'] == 'lm_eval'
        mock_get.assert_called_once_with('/api/v1/adapters')
    
    def test_wait_for_completion_success(self):
        """Test waiting for evaluation completion."""
        with patch.object(self.api_client, 'get_evaluation_status') as mock_status:
            # Simulate progression from running to completed
            mock_status.side_effect = [
                {'status': 'running', 'progress': 0.3},
                {'status': 'running', 'progress': 0.7},
                {'status': 'completed', 'progress': 1.0}
            ]
            
            with patch('time.sleep'):  # Speed up the test
                final_status = self.api_client.wait_for_completion('eval_123', poll_interval=0.1)
            
            assert final_status['status'] == 'completed'
            assert mock_status.call_count == 3
    
    def test_wait_for_completion_timeout(self):
        """Test timeout while waiting for completion."""
        with patch.object(self.api_client, 'get_evaluation_status') as mock_status:
            mock_status.return_value = {'status': 'running', 'progress': 0.5}
            
            with patch('time.sleep'), patch('time.time') as mock_time:
                # Simulate timeout
                mock_time.side_effect = [0, 0, 0, 301]  # Exceed 300 second timeout
                
                with pytest.raises(TimeoutError):
                    self.api_client.wait_for_completion('eval_123', timeout=300, poll_interval=0.1)
    
    @patch('requests.Session.post')
    def test_run_evaluation_async(self, mock_post):
        """Test asynchronous evaluation execution."""
        mock_response = MagicMock()
        mock_response.status_code = 202  # Accepted
        mock_response.json.return_value = {
            'evaluation_id': 'eval_123',
            'status': 'queued',
            'message': 'Evaluation queued for processing'
        }
        mock_post.return_value = mock_response
        
        result = self.api_client.run_evaluation_async(self.sample_config)
        
        assert result['evaluation_id'] == 'eval_123'
        assert result['status'] == 'queued'
        mock_post.assert_called_once()
    
    def test_batch_evaluation_requests(self):
        """Test batch processing of multiple evaluation requests."""
        configs = [
            {'tasks': ['hellaswag'], 'model': 'gpt-3.5-turbo'},
            {'tasks': ['arc_easy'], 'model': 'gpt-3.5-turbo'},
            {'tasks': ['winogrande'], 'model': 'gpt-3.5-turbo'}
        ]
        
        with patch.object(self.api_client, 'run_evaluation_async') as mock_async:
            mock_async.side_effect = [
                {'evaluation_id': 'eval_001', 'status': 'queued'},
                {'evaluation_id': 'eval_002', 'status': 'queued'},
                {'evaluation_id': 'eval_003', 'status': 'queued'}
            ]
            
            results = self.api_client.run_batch_evaluations(configs)
            
            assert len(results) == 3
            assert all('evaluation_id' in result for result in results)
            assert mock_async.call_count == 3
    
    def test_error_handling_network_error(self):
        """Test handling of network errors."""
        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = requests.ConnectionError("Connection failed")
            
            with pytest.raises(ExecutionError):
                self.api_client.run_evaluation(self.sample_config)
    
    def test_error_handling_timeout(self):
        """Test handling of request timeouts."""
        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = requests.Timeout("Request timed out")
            
            with pytest.raises(ExecutionError):
                self.api_client.run_evaluation(self.sample_config)
    
    def test_retry_mechanism(self):
        """Test retry mechanism for failed requests."""
        with patch('requests.Session.post') as mock_post:
            # First two calls fail, third succeeds
            mock_post.side_effect = [
                requests.ConnectionError("Connection failed"),
                requests.ConnectionError("Connection failed"),
                MagicMock(status_code=200, json=lambda: {'evaluation_id': 'eval_123'})
            ]
            
            result = self.api_client.run_evaluation_with_retry(
                self.sample_config, 
                max_retries=3, 
                retry_delay=0.1
            )
            
            assert result['evaluation_id'] == 'eval_123'
            assert mock_post.call_count == 3
    
    def test_authentication_handling(self):
        """Test API authentication handling."""
        api_client = APITestClient(
            base_url='http://localhost:8000',
            api_key='test_api_key'
        )
        
        with patch('requests.Session.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'evaluation_id': 'eval_123'}
            mock_post.return_value = mock_response
            
            api_client.run_evaluation(self.sample_config)
            
            # Verify authentication header was set
            call_args = mock_post.call_args
            headers = call_args[1].get('headers', {})
            assert 'Authorization' in headers or 'X-API-Key' in headers
    
    def test_request_validation(self):
        """Test validation of API requests."""
        # Valid request
        valid_config = {
            'tasks': ['hellaswag'],
            'model': 'gpt-3.5-turbo',
            'timeout': 300
        }
        
        is_valid, errors = self.api_client.validate_request(valid_config)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid request - missing required fields
        invalid_config = {
            'model': 'gpt-3.5-turbo'
            # Missing tasks
        }
        
        is_valid, errors = self.api_client.validate_request(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_response_parsing(self):
        """Test parsing of API responses."""
        # Valid JSON response
        valid_response = MagicMock()
        valid_response.status_code = 200
        valid_response.json.return_value = {
            'evaluation_id': 'eval_123',
            'status': 'completed'
        }
        
        parsed = self.api_client._parse_response(valid_response)
        assert parsed['evaluation_id'] == 'eval_123'
        
        # Invalid JSON response
        invalid_response = MagicMock()
        invalid_response.status_code = 200
        invalid_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        invalid_response.text = "Invalid JSON response"
        
        with pytest.raises(ExecutionError):
            self.api_client._parse_response(invalid_response)
    
    def test_concurrent_requests(self):
        """Test handling of concurrent API requests."""
        from concurrent.futures import ThreadPoolExecutor
        
        configs = [
            {'tasks': [f'task_{i}'], 'model': 'gpt-3.5-turbo'}
            for i in range(10)
        ]
        
        with patch.object(self.api_client, 'run_evaluation') as mock_eval:
            mock_eval.return_value = {'evaluation_id': 'eval_123', 'status': 'started'}
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(self.api_client.run_evaluation, config)
                    for config in configs
                ]
                results = [future.result() for future in futures]
            
            assert len(results) == 10
            assert all(r['evaluation_id'] == 'eval_123' for r in results)
            assert mock_eval.call_count == 10
    
    def test_rate_limiting_handling(self):
        """Test handling of rate limiting responses."""
        with patch('requests.Session.post') as mock_post:
            # First call gets rate limited, second succeeds
            rate_limit_response = MagicMock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {'Retry-After': '1'}
            
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {'evaluation_id': 'eval_123'}
            
            mock_post.side_effect = [rate_limit_response, success_response]
            
            with patch('time.sleep') as mock_sleep:
                result = self.api_client.run_evaluation_with_rate_limiting(self.sample_config)
            
            assert result['evaluation_id'] == 'eval_123'
            mock_sleep.assert_called_once_with(1)
            assert mock_post.call_count == 2
    
    def test_streaming_results(self):
        """Test streaming of evaluation results."""
        with patch('requests.Session.get') as mock_get:
            # Mock streaming response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"progress": 0.3, "current_task": "hellaswag"}',
                b'data: {"progress": 0.7, "current_task": "arc_easy"}',
                b'data: {"progress": 1.0, "status": "completed"}'
            ]
            mock_get.return_value = mock_response
            
            updates = list(self.api_client.stream_evaluation_progress('eval_123'))
            
            assert len(updates) == 3
            assert updates[0]['progress'] == 0.3
            assert updates[-1]['status'] == 'completed'