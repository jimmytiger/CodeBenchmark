"""
Unit tests for ErrorHandler component.

Tests error handling, classification, and recovery functionality.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from io import StringIO

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from core.error_handler import (
    ErrorHandler, 
    TestFrameworkError, 
    ConfigurationError, 
    DependencyError, 
    ExecutionError, 
    ValidationError
)


class TestErrorHandler:
    """Unit tests for ErrorHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
        self.log_stream = StringIO()
        self.test_logger = logging.getLogger('test_logger')
        self.test_logger.addHandler(logging.StreamHandler(self.log_stream))
        self.test_logger.setLevel(logging.DEBUG)
    
    def test_handle_configuration_error(self):
        """Test handling configuration errors."""
        error = ConfigurationError("Invalid configuration format")
        
        result = self.error_handler.handle_error(error)
        
        assert result['error_type'] == 'ConfigurationError'
        assert result['message'] == 'Invalid configuration format'
        assert result['recoverable'] is True
        assert 'suggestions' in result
    
    def test_handle_dependency_error(self):
        """Test handling dependency errors."""
        error = DependencyError("Missing required package: pytest")
        
        result = self.error_handler.handle_error(error)
        
        assert result['error_type'] == 'DependencyError'
        assert result['message'] == 'Missing required package: pytest'
        assert result['recoverable'] is True
        assert any('install' in suggestion.lower() for suggestion in result['suggestions'])
    
    def test_handle_execution_error(self):
        """Test handling execution errors."""
        error = ExecutionError("Test execution failed with exit code 1")
        
        result = self.error_handler.handle_error(error)
        
        assert result['error_type'] == 'ExecutionError'
        assert result['recoverable'] is False
        assert 'suggestions' in result
    
    def test_handle_validation_error(self):
        """Test handling validation errors."""
        error = ValidationError("Real execution validation failed")
        
        result = self.error_handler.handle_error(error)
        
        assert result['error_type'] == 'ValidationError'
        assert result['recoverable'] is False
        assert 'mock' in result['message'].lower() or 'real' in result['message'].lower()
    
    def test_handle_generic_exception(self):
        """Test handling generic exceptions."""
        error = ValueError("Generic error message")
        
        result = self.error_handler.handle_error(error)
        
        assert result['error_type'] == 'ValueError'
        assert result['message'] == 'Generic error message'
        assert result['recoverable'] is False
    
    def test_classify_error_severity(self):
        """Test error severity classification."""
        critical_error = ExecutionError("System crash")
        warning_error = ConfigurationError("Missing optional field")
        
        critical_severity = self.error_handler.classify_severity(critical_error)
        warning_severity = self.error_handler.classify_severity(warning_error)
        
        assert critical_severity == 'CRITICAL'
        assert warning_severity == 'WARNING'
    
    def test_suggest_recovery_actions(self):
        """Test recovery action suggestions."""
        config_error = ConfigurationError("Invalid test_type value")
        suggestions = self.error_handler.suggest_recovery_actions(config_error)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any('configuration' in suggestion.lower() for suggestion in suggestions)
    
    def test_log_error_with_context(self):
        """Test error logging with context information."""
        error = ExecutionError("Test failed")
        context = {
            'test_id': 'test_001',
            'adapter': 'lm_eval',
            'task': 'hellaswag'
        }
        
        with patch.object(self.error_handler, 'logger') as mock_logger:
            self.error_handler.log_error(error, context)
            
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0][0]
            assert 'test_001' in call_args
            assert 'lm_eval' in call_args
    
    def test_error_aggregation(self):
        """Test error aggregation and statistics."""
        errors = [
            ConfigurationError("Error 1"),
            ConfigurationError("Error 2"),
            ExecutionError("Error 3"),
            ValidationError("Error 4")
        ]
        
        for error in errors:
            self.error_handler.handle_error(error)
        
        stats = self.error_handler.get_error_statistics()
        
        assert stats['total_errors'] == 4
        assert stats['by_type']['ConfigurationError'] == 2
        assert stats['by_type']['ExecutionError'] == 1
        assert stats['by_type']['ValidationError'] == 1
    
    def test_retry_logic(self):
        """Test retry logic for recoverable errors."""
        def failing_operation():
            if not hasattr(failing_operation, 'call_count'):
                failing_operation.call_count = 0
            failing_operation.call_count += 1
            
            if failing_operation.call_count < 3:
                raise ExecutionError("Temporary failure")
            return "Success"
        
        result = self.error_handler.retry_operation(
            failing_operation, 
            max_retries=3, 
            delay=0.1
        )
        
        assert result == "Success"
        assert failing_operation.call_count == 3
    
    def test_retry_logic_max_retries_exceeded(self):
        """Test retry logic when max retries exceeded."""
        def always_failing_operation():
            raise ExecutionError("Permanent failure")
        
        with pytest.raises(ExecutionError):
            self.error_handler.retry_operation(
                always_failing_operation,
                max_retries=2,
                delay=0.1
            )
    
    def test_error_context_preservation(self):
        """Test that error context is preserved through handling."""
        original_error = ConfigurationError("Original message")
        original_error.context = {'file': 'config.yaml', 'line': 42}
        
        result = self.error_handler.handle_error(original_error)
        
        assert 'context' in result
        assert result['context']['file'] == 'config.yaml'
        assert result['context']['line'] == 42
    
    def test_graceful_degradation(self):
        """Test graceful degradation when error handling fails."""
        # Mock logger to raise exception
        with patch.object(self.error_handler, 'logger') as mock_logger:
            mock_logger.error.side_effect = Exception("Logging failed")
            
            error = ConfigurationError("Test error")
            result = self.error_handler.handle_error(error)
            
            # Should still return error info even if logging fails
            assert result['error_type'] == 'ConfigurationError'
            assert result['message'] == 'Test error'
    
    def test_error_chain_handling(self):
        """Test handling of chained exceptions."""
        try:
            try:
                raise ValueError("Root cause")
            except ValueError as e:
                raise ExecutionError("Execution failed") from e
        except ExecutionError as chained_error:
            result = self.error_handler.handle_error(chained_error)
            
            assert result['error_type'] == 'ExecutionError'
            assert 'chain' in result
            assert result['chain'][0]['error_type'] == 'ValueError'
    
    def test_custom_error_handlers(self):
        """Test registration and use of custom error handlers."""
        def custom_handler(error):
            return {
                'error_type': 'CustomHandled',
                'message': f"Custom: {str(error)}",
                'recoverable': True,
                'suggestions': ['Custom suggestion']
            }
        
        self.error_handler.register_custom_handler(ConfigurationError, custom_handler)
        
        error = ConfigurationError("Test error")
        result = self.error_handler.handle_error(error)
        
        assert result['error_type'] == 'CustomHandled'
        assert result['message'] == 'Custom: Test error'
        assert 'Custom suggestion' in result['suggestions']