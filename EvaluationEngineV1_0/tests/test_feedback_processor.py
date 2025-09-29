"""
Comprehensive tests for the feedback processing pipeline.

This module tests all components of the feedback processing system including
context management, stack trace processing, assertion filtering, and the
main feedback processor.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from EvaluationEngineV1_0.core.feedback_processor import (
    FeedbackProcessor,
    ContextManager,
    ContextWindow,
    StackTraceProcessor,
    AssertionFilter,
    create_test_feedback_config,
    extract_key_information
)
from EvaluationEngineV1_0.core.data_models import FeedbackConfig, ContextStrategy


class TestContextWindow:
    """Test ContextWindow data class."""
    
    def test_context_window_creation(self):
        """Test creating a context window."""
        content = "This is test content"
        window = ContextWindow(
            content=content,
            priority=3,
            timestamp=datetime.now(),
            content_type="test"
        )
        
        assert window.content == content
        assert window.priority == 3
        assert window.content_type == "test"
        assert window.size == len(content)
    
    def test_context_window_size_calculation(self):
        """Test automatic size calculation."""
        content = "Hello, World!"
        window = ContextWindow(
            content=content,
            priority=1,
            timestamp=datetime.now(),
            content_type="test"
        )
        
        assert window.size == 13  # Length of "Hello, World!"


class TestContextManager:
    """Test ContextManager class."""
    
    def test_context_manager_initialization(self):
        """Test context manager initialization."""
        manager = ContextManager(max_context_length=1000)
        
        assert manager.max_context_length == 1000
        assert len(manager.context_windows) == 0
        assert manager.total_size == 0
    
    def test_add_context_basic(self):
        """Test adding context content."""
        manager = ContextManager(max_context_length=1000)
        
        success = manager.add_context("Test content", "test", priority=1)
        
        assert success is True
        assert len(manager.context_windows) == 1
        assert manager.total_size == len("Test content")
    
    def test_add_context_empty_content(self):
        """Test adding empty content."""
        manager = ContextManager(max_context_length=1000)
        
        success = manager.add_context("", "test", priority=1)
        
        assert success is False
        assert len(manager.context_windows) == 0
    
    def test_add_context_exceeds_limit(self):
        """Test adding content that exceeds limits."""
        manager = ContextManager(max_context_length=10)
        
        # Add content that fits
        success1 = manager.add_context("Short", "test", priority=1)
        assert success1 is True
        
        # Add content that would exceed limit
        success2 = manager.add_context("This is a very long content that exceeds the limit", "test", priority=1)
        assert success2 is False
    
    def test_make_room_for_higher_priority(self):
        """Test making room for higher priority content."""
        manager = ContextManager(max_context_length=30)  # Set limit that requires room-making
        
        # Add low priority content that takes up most of the space
        success1 = manager.add_context("Low priority content", "test", priority=1)  # 20 chars
        assert success1 is True
        assert len(manager.context_windows) == 1
        
        # Add high priority content that requires making room (total would be >30)
        success2 = manager.add_context("High priority content", "test", priority=5)  # 21 chars
        
        assert success2 is True
        assert len(manager.context_windows) == 1  # Low priority content was removed
        assert "High priority content" in manager.context_windows[0].content
    
    def test_get_full_context(self):
        """Test getting full context."""
        manager = ContextManager(max_context_length=1000)
        
        manager.add_context("First content", "test1", priority=1)
        manager.add_context("Second content", "test2", priority=2)
        
        context = manager.get_context(ContextStrategy.FULL)
        
        assert "First content" in context
        assert "Second content" in context
    
    def test_get_adaptive_context(self):
        """Test getting adaptive context."""
        manager = ContextManager(max_context_length=1000)
        
        manager.add_context("Low priority", "test1", priority=1)
        manager.add_context("High priority", "test2", priority=5)
        
        context = manager.get_context(ContextStrategy.ADAPTIVE)
        
        # High priority content should appear first
        assert context.index("High priority") < context.index("Low priority")
    
    def test_get_minimal_context(self):
        """Test getting minimal context."""
        manager = ContextManager(max_context_length=1000)
        
        # Add content with different priorities and timestamps
        manager.add_context("Old low priority", "test1", priority=1)
        
        # Add a small delay to ensure different timestamps
        import time
        time.sleep(0.01)
        
        manager.add_context("New high priority", "test2", priority=5)
        
        context = manager.get_context(ContextStrategy.MINIMAL)
        
        # Should only contain the highest priority, most recent content
        assert "New high priority" in context
        assert "Old low priority" not in context
    
    def test_get_sliding_window_context(self):
        """Test getting sliding window context."""
        manager = ContextManager(max_context_length=50)
        
        manager.add_context("First", "test1", priority=1)
        
        import time
        time.sleep(0.01)
        
        manager.add_context("Second", "test2", priority=1)
        
        time.sleep(0.01)
        
        manager.add_context("Third", "test3", priority=1)
        
        context = manager.get_context(ContextStrategy.SLIDING_WINDOW)
        
        # Should contain recent content in chronological order
        assert "First" in context
        assert "Second" in context
        assert "Third" in context
    
    def test_clear_context(self):
        """Test clearing context."""
        manager = ContextManager(max_context_length=1000)
        
        manager.add_context("Test content", "test", priority=1)
        assert len(manager.context_windows) == 1
        
        manager.clear()
        
        assert len(manager.context_windows) == 0
        assert manager.total_size == 0
    
    def test_get_stats(self):
        """Test getting context statistics."""
        manager = ContextManager(max_context_length=1000)
        
        manager.add_context("Test content", "test", priority=1)
        manager.add_context("Error content", "error", priority=5)
        
        stats = manager.get_stats()
        
        assert stats["total_windows"] == 2
        assert stats["total_size"] > 0
        assert stats["max_size"] == 1000
        assert stats["utilization"] > 0
        assert "test" in stats["type_counts"]
        assert "error" in stats["type_counts"]
        assert 1 in stats["priority_counts"]
        assert 5 in stats["priority_counts"]


class TestStackTraceProcessor:
    """Test StackTraceProcessor class."""
    
    def test_stack_trace_processor_initialization(self):
        """Test stack trace processor initialization."""
        processor = StackTraceProcessor()
        
        assert len(processor.common_patterns) > 0
        assert len(processor.compiled_patterns) > 0
    
    def test_summarize_python_stack_trace(self):
        """Test summarizing Python stack trace."""
        processor = StackTraceProcessor()
        
        stack_trace = """Traceback (most recent call last):
  File "test.py", line 10, in main
    result = divide(10, 0)
  File "test.py", line 5, in divide
    return a / b
ZeroDivisionError: division by zero"""
        
        summary = processor.summarize_stack_trace(stack_trace, max_lines=5)
        
        assert "ZeroDivisionError: division by zero" in summary
        assert "test.py" in summary
        assert "divide" in summary
    
    def test_summarize_empty_stack_trace(self):
        """Test summarizing empty stack trace."""
        processor = StackTraceProcessor()
        
        summary = processor.summarize_stack_trace("", max_lines=5)
        
        assert summary == ""
    
    def test_summarize_unparseable_stack_trace(self):
        """Test summarizing unparseable stack trace."""
        processor = StackTraceProcessor()
        
        stack_trace = "Some random error output that doesn't match patterns"
        
        summary = processor.summarize_stack_trace(stack_trace, max_lines=3)
        
        # Should fall back to simple truncation
        assert len(summary.split('\n')) <= 3
    
    def test_extract_error_info(self):
        """Test extracting error information."""
        processor = StackTraceProcessor()
        
        lines = [
            "Traceback (most recent call last):",
            "  File \"test.py\", line 5, in test",
            "ValueError: invalid literal for int()"
        ]
        
        error_info = processor._extract_error_info(lines)
        
        assert error_info == "ValueError: invalid literal for int()"
    
    def test_extract_call_stack(self):
        """Test extracting call stack."""
        processor = StackTraceProcessor()
        
        lines = [
            "Traceback (most recent call last):",
            "  File \"main.py\", line 10, in main",
            "  File \"utils.py\", line 5, in helper",
            "ValueError: something went wrong"
        ]
        
        call_stack = processor._extract_call_stack(lines, max_entries=2)
        
        assert len(call_stack) == 2
        assert any("main.py" in entry for entry in call_stack)
        assert any("utils.py" in entry for entry in call_stack)


class TestAssertionFilter:
    """Test AssertionFilter class."""
    
    def test_assertion_filter_initialization(self):
        """Test assertion filter initialization."""
        filter_obj = AssertionFilter(top_k=3)
        
        assert filter_obj.top_k == 3
        assert len(filter_obj.assertion_patterns) > 0
    
    def test_filter_assertions_basic(self):
        """Test basic assertion filtering."""
        filter_obj = AssertionFilter(top_k=3)
        
        content = """Test output
assert x == 5
AssertionError: Expected 5, got 3
FAIL: test_something failed
Some other output
ERROR: Critical error occurred"""
        
        assertions = filter_obj.filter_assertions(content)
        
        assert len(assertions) <= 3
        assert any("AssertionError" in assertion for assertion in assertions)
        assert any("ERROR" in assertion for assertion in assertions)
    
    def test_filter_assertions_priority_ordering(self):
        """Test that assertions are ordered by priority."""
        filter_obj = AssertionFilter(top_k=5)
        
        content = """Warning: minor issue
ERROR: critical error
assert something
FAILED: test failed
Some normal output"""
        
        assertions = filter_obj.filter_assertions(content)
        
        # ERROR should come before Warning due to higher priority
        error_index = next((i for i, a in enumerate(assertions) if "ERROR" in a), -1)
        warning_index = next((i for i, a in enumerate(assertions) if "Warning" in a), -1)
        
        if error_index >= 0 and warning_index >= 0:
            assert error_index < warning_index
    
    def test_calculate_assertion_priority(self):
        """Test assertion priority calculation."""
        filter_obj = AssertionFilter()
        
        high_priority = filter_obj._calculate_assertion_priority("ERROR: critical failure")
        medium_priority = filter_obj._calculate_assertion_priority("assert x == y")
        low_priority = filter_obj._calculate_assertion_priority("some normal output")
        
        assert high_priority > medium_priority > low_priority
    
    def test_filter_assertions_empty_content(self):
        """Test filtering assertions from empty content."""
        filter_obj = AssertionFilter(top_k=3)
        
        assertions = filter_obj.filter_assertions("")
        
        assert len(assertions) == 0


class TestFeedbackProcessor:
    """Test FeedbackProcessor class."""
    
    def test_feedback_processor_initialization(self):
        """Test feedback processor initialization."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        assert processor.config == config
        assert processor.context_manager is not None
        assert processor.stack_processor is not None
        assert processor.assertion_filter is not None
    
    def test_extract_raw_feedback(self):
        """Test extracting raw feedback from observation and info."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        observation = "Test observation"
        info = {
            'stdout': 'Test output',
            'stderr': 'Test error',
            'execution_time': 1.5,
            'exit_code': 0
        }
        
        raw_feedback = processor._extract_raw_feedback(observation, info)
        
        assert raw_feedback['observation'] == "Test observation"
        assert raw_feedback['stdout'] == 'Test output'
        assert raw_feedback['stderr'] == 'Test error'
        assert raw_feedback['execution_time'] == 1.5
        assert raw_feedback['exit_code'] == 0
    
    def test_apply_safety_filtering(self):
        """Test applying safety filtering to feedback."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        feedback = {
            'stdout': 'Normal output',
            'stderr': 'password=secret123 and token=abc123',
            'metadata': 'key=sensitive_data'
        }
        
        filtered = processor._apply_safety_filtering(feedback)
        
        assert filtered['stdout'] == 'Normal output'  # Unchanged
        assert 'secret123' not in filtered['stderr']  # Sensitive data removed
        assert '[REDACTED]' in filtered['stderr']
        assert 'sensitive_data' not in filtered['metadata']
    
    def test_process_complete_workflow(self):
        """Test complete feedback processing workflow."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        observation = "Test completed"
        info = {
            'stdout': 'Test passed successfully',
            'stderr': 'Warning: deprecated function used',
            'test_results': {
                'total': 5,
                'passed': 4,
                'failed': 1,
                'failures': ['test_division_by_zero failed']
            },
            'execution_time': 2.3
        }
        
        result = processor.process(observation, info)
        
        assert result.original is not None
        assert result.filtered is not None
        assert result.contextualized is not None
        assert result.final is not None
        assert result.processing_time > 0
        assert isinstance(result.truncated, bool)
    
    def test_summarize_test_results(self):
        """Test test results summarization."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        test_results = {
            'total': 10,
            'passed': 8,
            'failed': 2,
            'failures': [
                'test_invalid_input failed: AssertionError',
                'test_edge_case failed: ValueError'
            ]
        }
        
        summary = processor._summarize_test_results(test_results)
        
        assert "8/10 passed" in summary
        assert "2 failed" in summary
        assert "test_invalid_input" in summary
        assert "test_edge_case" in summary
    
    def test_create_file_context(self):
        """Test creating file context."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        files_changed = [
            'src/main.py',
            'tests/test_main.py',
            'README.md'
        ]
        
        context = processor._create_file_context(files_changed)
        
        assert "Files modified: 3" in context
        assert "src/main.py" in context
        assert "tests/test_main.py" in context
        assert "README.md" in context
    
    def test_create_file_context_many_files(self):
        """Test creating file context with many files."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        files_changed = [f'file_{i}.py' for i in range(15)]
        
        context = processor._create_file_context(files_changed)
        
        assert "Files modified: 15" in context
        assert "and 5 more files" in context
    
    def test_intelligent_truncation(self):
        """Test intelligent truncation strategy."""
        config = FeedbackConfig(
            max_feedback_length=100,
            truncation_strategy="intelligent",
            preserve_error_info=True
        )
        processor = FeedbackProcessor(config)
        
        feedback = {
            'error_message': 'Critical error occurred',
            'stdout': 'This is a very long output that should be truncated because it exceeds the limit',
            'metadata': 'Some metadata that is less important'
        }
        
        truncated = processor._intelligent_truncation(feedback)
        
        # Error message should be preserved
        assert truncated['error_message'] == 'Critical error occurred'
        # Other content should be truncated
        assert len(str(truncated)) <= config.max_feedback_length + 100  # More generous tolerance
    
    def test_update_stats(self):
        """Test statistics updating."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        raw_feedback = {'content': 'This is some content'}
        final_feedback = {'content': 'Shorter'}
        processing_time = 0.5
        
        processor._update_stats(raw_feedback, final_feedback, processing_time)
        
        stats = processor.get_stats()
        
        assert stats['total_processed'] == 1
        assert stats['total_processing_time'] == 0.5
        assert stats['avg_processing_time'] == 0.5
        assert stats['avg_input_size'] > 0
        assert stats['avg_output_size'] > 0
    
    def test_get_stats(self):
        """Test getting processing statistics."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        # Process some feedback to generate stats
        processor.process("test", {'stdout': 'test output'})
        
        stats = processor.get_stats()
        
        assert 'total_processed' in stats
        assert 'total_truncated' in stats
        assert 'avg_processing_time' in stats
        assert 'truncation_rate' in stats
        assert 'context_stats' in stats
    
    def test_reset_stats(self):
        """Test resetting statistics."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        # Process some feedback
        processor.process("test", {'stdout': 'test output'})
        
        # Reset stats
        processor.reset_stats()
        
        stats = processor.get_stats()
        
        assert stats['total_processed'] == 0
        assert stats['total_truncated'] == 0
        assert stats['avg_processing_time'] == 0.0
    
    def test_update_config(self):
        """Test updating processor configuration."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        new_config = FeedbackConfig(
            max_feedback_length=2000,
            max_context_length=5000,
            top_k_assertions=10
        )
        
        processor.update_config(new_config)
        
        assert processor.config.max_feedback_length == 2000
        assert processor.context_manager.max_context_length == 5000
        assert processor.assertion_filter.top_k == 10


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_test_feedback_config(self):
        """Test creating test feedback configuration."""
        config = create_test_feedback_config()
        
        assert isinstance(config, FeedbackConfig)
        assert config.max_feedback_length > 0
        assert config.max_context_length > 0
        assert config.top_k_assertions > 0
        assert config.enable_stack_summarization is True
        assert config.enable_file_context is True
    
    def test_extract_key_information(self):
        """Test extracting key information from content."""
        content = """File "test.py", line 10, in main
def test_function():
    pass
ERROR: Something went wrong
Warning: deprecated function
Test passed successfully
AssertionError: Expected 5, got 3"""
        
        info = extract_key_information(content)
        
        assert len(info['errors']) > 0
        assert len(info['warnings']) > 0
        assert len(info['files']) > 0
        assert len(info['functions']) > 0
        
        assert any('ERROR' in error for error in info['errors'])
        assert any('Warning' in warning for warning in info['warnings'])
        assert 'test.py' in info['files']
        assert 'test_function' in info['functions']
    
    def test_extract_key_information_empty_content(self):
        """Test extracting key information from empty content."""
        info = extract_key_information("")
        
        assert len(info['errors']) == 0
        assert len(info['warnings']) == 0
        assert len(info['files']) == 0
        assert len(info['functions']) == 0
        assert len(info['tests']) == 0


class TestIntegrationScenarios:
    """Integration tests for the complete feedback processing system."""
    
    def test_complete_feedback_processing_workflow(self):
        """Test complete feedback processing workflow with realistic data."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        # Simulate a complex evaluation scenario
        observation = "Evaluation completed with mixed results"
        stderr_content = '''Traceback (most recent call last):
  File "test_edge_cases.py", line 15, in test_division_by_zero
    result = divide(10, 0)
  File "calculator.py", line 8, in divide
    return a / b
ZeroDivisionError: division by zero'''
        
        info = {
            'stdout': '''Running tests...
test_basic_functionality ... PASSED
test_edge_cases ... FAILED
test_performance ... PASSED
3 tests run, 2 passed, 1 failed''',
            'stderr': stderr_content,
            'test_results': {
                'total': 3,
                'passed': 2,
                'failed': 1,
                'failures': ['test_edge_cases.test_division_by_zero'],
                'stack_traces': [stderr_content]
            },
            'files_changed': ['calculator.py', 'test_edge_cases.py'],
            'execution_time': 1.2,
            'exit_code': 1
        }
        
        result = processor.process(observation, info)
        
        # Verify all processing stages completed
        assert result.original is not None
        assert result.filtered is not None
        assert result.contextualized is not None
        assert result.final is not None
        
        # Verify key information is preserved
        final_content = str(result.final)
        assert "ZeroDivisionError" in final_content or "division by zero" in final_content
        assert "2 passed, 1 failed" in final_content or "test" in final_content
        
        # Verify processing metadata
        assert result.processing_time > 0
        assert isinstance(result.truncated, bool)
    
    def test_feedback_processing_with_large_content(self):
        """Test feedback processing with content that exceeds limits."""
        config = FeedbackConfig(
            max_feedback_length=500,  # Small limit to force truncation
            max_context_length=200,
            truncation_strategy="intelligent",
            preserve_error_info=True
        )
        processor = FeedbackProcessor(config)
        
        # Create large content
        large_output = "This is a line of output.\n" * 100  # Very large output
        
        observation = "Large test completed"
        info = {
            'stdout': large_output,
            'stderr': 'CRITICAL ERROR: System failure',
            'execution_time': 5.0
        }
        
        result = processor.process(observation, info)
        
        # Should be truncated
        assert result.truncated is True
        
        # Critical error should be preserved
        final_content = str(result.final)
        assert "CRITICAL ERROR" in final_content
        
        # Final content should be within limits (with some tolerance)
        assert len(final_content) <= config.max_feedback_length + 200  # More generous tolerance for complex content
    
    def test_feedback_processing_performance(self):
        """Test feedback processing performance with multiple iterations."""
        config = create_test_feedback_config()
        processor = FeedbackProcessor(config)
        
        # Process multiple feedback instances
        for i in range(10):
            observation = f"Test iteration {i}"
            info = {
                'stdout': f'Output from iteration {i}',
                'stderr': f'Warning from iteration {i}' if i % 3 == 0 else '',
                'execution_time': 0.1 * i
            }
            
            result = processor.process(observation, info)
            assert result is not None
        
        # Check statistics
        stats = processor.get_stats()
        assert stats['total_processed'] == 10
        assert stats['avg_processing_time'] > 0
        
        # Performance should be reasonable (less than 100ms per processing on average)
        assert stats['avg_processing_time'] < 0.1
    
    def test_context_management_across_turns(self):
        """Test context management across multiple turns."""
        config = FeedbackConfig(
            max_context_length=1000,
            context_strategy=ContextStrategy.ADAPTIVE
        )
        processor = FeedbackProcessor(config)
        
        # Simulate multiple turns with different types of content
        turns = [
            ("Turn 1", {'stdout': 'Initial setup completed', 'stderr': ''}),
            ("Turn 2", {'stdout': 'Processing data...', 'stderr': 'Warning: deprecated API'}),
            ("Turn 3", {'stdout': 'Analysis complete', 'stderr': 'ERROR: Critical failure'}),
        ]
        
        results = []
        for observation, info in turns:
            result = processor.process(observation, info)
            results.append(result)
        
        # Later turns should have more context
        assert len(str(results[0].contextualized)) < len(str(results[2].contextualized))
        
        # Critical error from turn 3 should be prioritized in context
        final_context = str(results[2].final)
        assert "ERROR: Critical failure" in final_context


if __name__ == "__main__":
    pytest.main([__file__])