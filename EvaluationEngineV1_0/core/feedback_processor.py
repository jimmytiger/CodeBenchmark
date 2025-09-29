"""
Feedback processing pipeline for multi-turn evaluation.

This module implements comprehensive feedback processing including context management,
filtering, stack trace summarization, and adaptive length truncation to ensure
efficient and effective feedback delivery to models.
"""

import json
import re
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

from .data_models import FeedbackConfig, ProcessedFeedback, ContextStrategy


@dataclass
class ContextWindow:
    """Represents a context window for feedback processing.
    
    Attributes:
        content: The actual content in this window
        priority: Priority level (higher = more important)
        timestamp: When this content was created
        content_type: Type of content (error, output, file, etc.)
        size: Size of content in characters
    """
    content: str
    priority: int
    timestamp: datetime
    content_type: str
    size: int = field(init=False)
    
    def __post_init__(self):
        self.size = len(self.content)


class ContextManager:
    """Manages context windows and implements context retention strategies.
    
    This class handles different strategies for managing context across
    multiple turns in a conversation, ensuring the most relevant information
    is preserved within token limits.
    """
    
    def __init__(self, max_context_length: int):
        """Initialize context manager.
        
        Args:
            max_context_length: Maximum total context length in characters
        """
        self.max_context_length = max_context_length
        self.context_windows: List[ContextWindow] = []
        self.total_size = 0
    
    def add_context(self, 
                   content: str, 
                   content_type: str, 
                   priority: int = 1) -> bool:
        """Add content to context management.
        
        Args:
            content: Content to add
            content_type: Type of content (error, output, file, etc.)
            priority: Priority level (higher = more important)
            
        Returns:
            True if content was added, False if rejected due to size
        """
        if not content.strip():
            return False
        
        window = ContextWindow(
            content=content,
            priority=priority,
            timestamp=datetime.now(),
            content_type=content_type
        )
        
        # Check if adding this would exceed limits
        if self.total_size + window.size > self.max_context_length:
            # Try to make room by removing lower priority content
            if not self._make_room(window.size, priority):
                return False
        
        self.context_windows.append(window)
        self.total_size += window.size
        return True
    
    def _make_room(self, needed_size: int, min_priority: int) -> bool:
        """Make room for new content by removing lower priority items.
        
        Args:
            needed_size: Size needed for new content
            min_priority: Minimum priority of new content
            
        Returns:
            True if enough room was made, False otherwise
        """
        # Calculate how much space we actually need to free
        current_available = self.max_context_length - self.total_size
        space_needed = needed_size - current_available
        
        if space_needed <= 0:
            return True  # No need to make room
        
        # Sort by priority (ascending) and timestamp (oldest first)
        candidates = sorted(
            self.context_windows,
            key=lambda w: (w.priority, w.timestamp)
        )
        
        freed_size = 0
        to_remove = []
        
        for window in candidates:
            # Only remove content with strictly lower priority
            if window.priority < min_priority:
                to_remove.append(window)
                freed_size += window.size
                
                if freed_size >= space_needed:
                    break
        
        # Remove the selected windows
        for window in to_remove:
            self.context_windows.remove(window)
            self.total_size -= window.size
        
        return freed_size >= space_needed
    
    def get_context(self, strategy: ContextStrategy) -> str:
        """Get context according to the specified strategy.
        
        Args:
            strategy: Context management strategy
            
        Returns:
            Formatted context string
        """
        if strategy == ContextStrategy.FULL:
            return self._get_full_context()
        elif strategy == ContextStrategy.ADAPTIVE:
            return self._get_adaptive_context()
        elif strategy == ContextStrategy.MINIMAL:
            return self._get_minimal_context()
        elif strategy == ContextStrategy.SLIDING_WINDOW:
            return self._get_sliding_window_context()
        else:
            return self._get_adaptive_context()  # Default
    
    def _get_full_context(self) -> str:
        """Get all context content."""
        return "\n".join(window.content for window in self.context_windows)
    
    def _get_adaptive_context(self) -> str:
        """Get context using adaptive strategy (priority-based)."""
        # Sort by priority (descending) and recency
        sorted_windows = sorted(
            self.context_windows,
            key=lambda w: (-w.priority, -w.timestamp.timestamp())
        )
        
        context_parts = []
        current_size = 0
        
        for window in sorted_windows:
            if current_size + window.size <= self.max_context_length:
                context_parts.append(f"[{window.content_type}] {window.content}")
                current_size += window.size
            else:
                # Try to fit a truncated version
                remaining = self.max_context_length - current_size
                if remaining > 100:  # Only if we have reasonable space
                    truncated = window.content[:remaining-20] + "...[truncated]"
                    context_parts.append(f"[{window.content_type}] {truncated}")
                break
        
        return "\n".join(context_parts)
    
    def _get_minimal_context(self) -> str:
        """Get only the highest priority, most recent context."""
        if not self.context_windows:
            return ""
        
        # Get the highest priority, most recent window
        best_window = max(
            self.context_windows,
            key=lambda w: (w.priority, w.timestamp.timestamp())
        )
        
        return f"[{best_window.content_type}] {best_window.content}"
    
    def _get_sliding_window_context(self) -> str:
        """Get the most recent context within size limits."""
        # Sort by timestamp (most recent first)
        recent_windows = sorted(
            self.context_windows,
            key=lambda w: -w.timestamp.timestamp()
        )
        
        context_parts = []
        current_size = 0
        
        for window in recent_windows:
            if current_size + window.size <= self.max_context_length:
                context_parts.append(f"[{window.content_type}] {window.content}")
                current_size += window.size
            else:
                break
        
        # Reverse to maintain chronological order
        return "\n".join(reversed(context_parts))
    
    def clear(self):
        """Clear all context."""
        self.context_windows.clear()
        self.total_size = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context management statistics."""
        type_counts = {}
        priority_counts = {}
        
        for window in self.context_windows:
            type_counts[window.content_type] = type_counts.get(window.content_type, 0) + 1
            priority_counts[window.priority] = priority_counts.get(window.priority, 0) + 1
        
        return {
            "total_windows": len(self.context_windows),
            "total_size": self.total_size,
            "max_size": self.max_context_length,
            "utilization": self.total_size / self.max_context_length if self.max_context_length > 0 else 0,
            "type_counts": type_counts,
            "priority_counts": priority_counts
        }


class StackTraceProcessor:
    """Processes and summarizes stack traces for better readability."""
    
    def __init__(self):
        """Initialize stack trace processor."""
        self.common_patterns = [
            # Python patterns
            r'File "([^"]+)", line (\d+), in (.+)',
            r'(\w+Error): (.+)',
            r'Traceback \(most recent call last\):',
            
            # JavaScript patterns
            r'at (.+) \(([^:]+):(\d+):(\d+)\)',
            r'(\w+Error): (.+)',
            
            # Java patterns
            r'at (.+)\.(.+)\(([^:]+):(\d+)\)',
            r'(\w+Exception): (.+)',
        ]
        
        self.compiled_patterns = [re.compile(pattern) for pattern in self.common_patterns]
    
    def summarize_stack_trace(self, stack_trace: str, max_lines: int = 10) -> str:
        """Summarize a stack trace to essential information.
        
        Args:
            stack_trace: Full stack trace string
            max_lines: Maximum number of lines to include
            
        Returns:
            Summarized stack trace
        """
        if not stack_trace.strip():
            return stack_trace
        
        lines = stack_trace.strip().split('\n')
        
        # Extract key information
        error_info = self._extract_error_info(lines)
        call_stack = self._extract_call_stack(lines, max_lines // 2)
        
        # Build summary
        summary_parts = []
        
        if error_info:
            summary_parts.append(f"Error: {error_info}")
        
        if call_stack:
            summary_parts.append("Call stack:")
            summary_parts.extend(f"  {line}" for line in call_stack)
        
        # If we couldn't parse it, just truncate
        if not summary_parts:
            summary_parts = lines[:max_lines]
            if len(lines) > max_lines:
                summary_parts.append(f"... ({len(lines) - max_lines} more lines)")
        
        return '\n'.join(summary_parts)
    
    def _extract_error_info(self, lines: List[str]) -> Optional[str]:
        """Extract the main error information."""
        # Look for error patterns in reverse order (errors usually at the end)
        for line in reversed(lines):
            for pattern in self.compiled_patterns:
                match = pattern.search(line)
                if match and ('Error' in line or 'Exception' in line):
                    return line.strip()
        return None
    
    def _extract_call_stack(self, lines: List[str], max_entries: int) -> List[str]:
        """Extract the most relevant call stack entries."""
        stack_entries = []
        
        for line in lines:
            # Look for file/line patterns
            for pattern in self.compiled_patterns:
                match = pattern.search(line)
                if match and ('File' in line or 'at ' in line):
                    stack_entries.append(line.strip())
                    break
        
        # Return the most recent entries
        return stack_entries[-max_entries:] if stack_entries else []


class AssertionFilter:
    """Filters and prioritizes assertion failures and test results."""
    
    def __init__(self, top_k: int = 5):
        """Initialize assertion filter.
        
        Args:
            top_k: Number of top assertions to keep
        """
        self.top_k = top_k
        self.assertion_patterns = [
            r'assert (.+)',
            r'AssertionError: (.+)',
            r'FAIL: (.+)',
            r'FAILED (.+)',
            r'ERROR: (.+)',
            r'Test (.+) failed',
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.assertion_patterns]
    
    def filter_assertions(self, content: str) -> List[str]:
        """Filter and rank assertion failures.
        
        Args:
            content: Content containing potential assertions
            
        Returns:
            List of top-K assertion failures
        """
        lines = content.split('\n')
        assertions = []
        
        for line in lines:
            for pattern in self.compiled_patterns:
                match = pattern.search(line)
                if match:
                    # Calculate priority based on keywords
                    priority = self._calculate_assertion_priority(line)
                    assertions.append((priority, line.strip()))
                    break
        
        # Sort by priority (descending) and take top-K
        assertions.sort(key=lambda x: -x[0])
        return [assertion[1] for assertion in assertions[:self.top_k]]
    
    def _calculate_assertion_priority(self, line: str) -> int:
        """Calculate priority score for an assertion."""
        priority = 1
        
        # Higher priority for certain keywords
        high_priority_keywords = ['error', 'failed', 'exception', 'critical']
        medium_priority_keywords = ['warning', 'assert', 'fail']
        
        line_lower = line.lower()
        
        for keyword in high_priority_keywords:
            if keyword in line_lower:
                priority += 3
        
        for keyword in medium_priority_keywords:
            if keyword in line_lower:
                priority += 1
        
        return priority


class FeedbackProcessor:
    """Main feedback processing pipeline.
    
    This class orchestrates the complete feedback processing pipeline including
    context management, filtering, summarization, and length truncation.
    """
    
    def __init__(self, config: FeedbackConfig):
        """Initialize feedback processor.
        
        Args:
            config: Feedback processing configuration
        """
        self.config = config
        self.context_manager = ContextManager(config.max_context_length)
        self.stack_processor = StackTraceProcessor()
        self.assertion_filter = AssertionFilter(config.top_k_assertions)
        
        # Processing statistics
        self.stats = {
            "total_processed": 0,
            "total_truncated": 0,
            "total_processing_time": 0.0,
            "avg_input_size": 0.0,
            "avg_output_size": 0.0
        }
    
    def process(self, 
                observation: Any, 
                info: Dict[str, Any],
                turn_context: Optional[Dict[str, Any]] = None) -> ProcessedFeedback:
        """Process feedback from environment execution.
        
        Args:
            observation: Raw observation from environment
            info: Additional information dictionary
            turn_context: Optional context from previous turns
            
        Returns:
            Processed feedback ready for model consumption
        """
        start_time = datetime.now()
        
        # Extract raw feedback data
        raw_feedback = self._extract_raw_feedback(observation, info)
        
        # Apply safety filtering (basic content filtering)
        filtered_feedback = self._apply_safety_filtering(raw_feedback)
        
        # Add context and manage context windows
        contextualized_feedback = self._add_context(filtered_feedback, turn_context)
        
        # Apply intelligent truncation
        final_feedback = self._apply_truncation(contextualized_feedback)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Update statistics
        self._update_stats(raw_feedback, final_feedback, processing_time)
        
        return ProcessedFeedback(
            original=raw_feedback,
            filtered=filtered_feedback,
            contextualized=contextualized_feedback,
            final=final_feedback,
            processing_time=processing_time,
            truncated=len(str(final_feedback)) < len(str(contextualized_feedback)),
            timestamp=datetime.now()
        )
    
    def _extract_raw_feedback(self, observation: Any, info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured feedback from observation and info."""
        feedback = {
            'observation': str(observation) if observation else "",
            'stdout': info.get('stdout', ''),
            'stderr': info.get('stderr', ''),
            'files_changed': info.get('files_changed', []),
            'test_results': info.get('test_results', {}),
            'execution_time': info.get('execution_time', 0),
            'exit_code': info.get('exit_code', 0),
            'error_message': info.get('error_message', ''),
            'warnings': info.get('warnings', []),
            'metadata': info.get('metadata', {})
        }
        
        return feedback
    
    def _apply_safety_filtering(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Apply basic safety filtering to feedback content."""
        filtered = feedback.copy()
        
        # Filter potentially sensitive information
        sensitive_patterns = [
            r'password[=:]\s*\S+',
            r'token[=:]\s*\S+',
            r'key[=:]\s*\S+',
            r'secret[=:]\s*\S+',
        ]
        
        for key, value in filtered.items():
            if isinstance(value, str):
                for pattern in sensitive_patterns:
                    value = re.sub(pattern, f'{key}=[REDACTED]', value, flags=re.IGNORECASE)
                filtered[key] = value
        
        return filtered
    
    def _add_context(self, 
                    feedback: Dict[str, Any], 
                    turn_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Add context information to feedback."""
        contextualized = feedback.copy()
        
        # Process different types of content with appropriate priorities
        if feedback.get('stderr'):
            # High priority for errors
            self.context_manager.add_context(
                feedback['stderr'], 
                'error', 
                priority=5
            )
        
        if feedback.get('stdout'):
            # Medium priority for output
            self.context_manager.add_context(
                feedback['stdout'], 
                'output', 
                priority=3
            )
        
        if feedback.get('test_results'):
            # High priority for test results
            test_summary = self._summarize_test_results(feedback['test_results'])
            self.context_manager.add_context(
                test_summary, 
                'test_results', 
                priority=4
            )
        
        # Add file context if enabled
        if self.config.enable_file_context and feedback.get('files_changed'):
            file_context = self._create_file_context(feedback['files_changed'])
            self.context_manager.add_context(
                file_context, 
                'file_changes', 
                priority=2
            )
        
        # Get context according to strategy
        context_content = self.context_manager.get_context(self.config.context_strategy)
        contextualized['context'] = context_content
        
        return contextualized
    
    def _apply_truncation(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Apply intelligent truncation to stay within limits."""
        final = feedback.copy()
        
        # Calculate current size
        current_size = sum(len(str(v)) for v in final.values())
        
        if current_size <= self.config.max_feedback_length:
            return final
        
        # Apply truncation strategy
        if self.config.truncation_strategy == "intelligent":
            final = self._intelligent_truncation(final)
        elif self.config.truncation_strategy == "tail":
            final = self._tail_truncation(final)
        elif self.config.truncation_strategy == "head":
            final = self._head_truncation(final)
        
        return final
    
    def _intelligent_truncation(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Apply intelligent truncation preserving important information."""
        truncated = feedback.copy()
        target_size = self.config.max_feedback_length
        
        # Priority order for preservation (high to low priority)
        priority_order = [
            'error_message',
            'stderr', 
            'test_results',
            'stdout',
            'observation',
            'context',
            'metadata'
        ]
        
        # Calculate current size
        current_size = len(str(truncated))
        
        if current_size <= target_size:
            return truncated
        
        # Always preserve error information if configured
        preserved_keys = set()
        if self.config.preserve_error_info:
            preserved_keys.update(['error_message', 'stderr'])
        
        # Truncate fields in reverse priority order (lowest priority first)
        for key in reversed(priority_order):
            if current_size <= target_size:
                break
            
            if key in truncated and key not in preserved_keys:
                value = str(truncated[key])
                if len(value) > 50:  # Only truncate if reasonably large
                    # Calculate how much to truncate
                    excess = current_size - target_size
                    new_length = max(20, len(value) - excess - 20)  # Leave room for truncation marker
                    truncated[key] = value[:new_length] + "...[truncated]"
                    current_size = len(str(truncated))
        
        return truncated
    
    def _tail_truncation(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Truncate from the end of content."""
        truncated = feedback.copy()
        content_str = json.dumps(truncated)
        
        if len(content_str) > self.config.max_feedback_length:
            truncated_str = content_str[:self.config.max_feedback_length - 20] + "...[truncated]"
            try:
                truncated = json.loads(truncated_str)
            except json.JSONDecodeError:
                # Fallback to simple truncation
                truncated['_truncated'] = True
        
        return truncated
    
    def _head_truncation(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Truncate from the beginning of content."""
        truncated = feedback.copy()
        content_str = json.dumps(truncated)
        
        if len(content_str) > self.config.max_feedback_length:
            truncated_str = "...[truncated]" + content_str[-(self.config.max_feedback_length - 20):]
            try:
                truncated = json.loads(truncated_str)
            except json.JSONDecodeError:
                # Fallback to simple truncation
                truncated['_truncated'] = True
        
        return truncated
    
    def _summarize_test_results(self, test_results: Dict[str, Any]) -> str:
        """Summarize test results for context."""
        if not test_results:
            return ""
        
        summary_parts = []
        
        # Basic statistics
        total = test_results.get('total', 0)
        passed = test_results.get('passed', 0)
        failed = test_results.get('failed', 0)
        
        summary_parts.append(f"Tests: {passed}/{total} passed, {failed} failed")
        
        # Failed test details
        if 'failures' in test_results:
            failures = test_results['failures'][:self.config.top_k_assertions]
            if failures:
                summary_parts.append("Failed tests:")
                for failure in failures:
                    summary_parts.append(f"  - {failure}")
        
        # Stack traces if enabled
        if self.config.enable_stack_summarization and 'stack_traces' in test_results:
            for trace in test_results['stack_traces'][:3]:  # Limit to 3 traces
                summarized = self.stack_processor.summarize_stack_trace(trace)
                summary_parts.append(f"Stack trace:\n{summarized}")
        
        return '\n'.join(summary_parts)
    
    def _create_file_context(self, files_changed: List[str]) -> str:
        """Create context information about changed files."""
        if not files_changed:
            return ""
        
        context_parts = [f"Files modified: {len(files_changed)}"]
        
        # List files (limit to reasonable number)
        for file_path in files_changed[:10]:
            context_parts.append(f"  - {file_path}")
        
        if len(files_changed) > 10:
            context_parts.append(f"  ... and {len(files_changed) - 10} more files")
        
        return '\n'.join(context_parts)
    
    def _update_stats(self, 
                     raw_feedback: Dict[str, Any], 
                     final_feedback: Dict[str, Any], 
                     processing_time: float):
        """Update processing statistics."""
        self.stats["total_processed"] += 1
        self.stats["total_processing_time"] += processing_time
        
        input_size = sum(len(str(v)) for v in raw_feedback.values())
        output_size = sum(len(str(v)) for v in final_feedback.values())
        
        # Update running averages
        n = self.stats["total_processed"]
        self.stats["avg_input_size"] = ((n - 1) * self.stats["avg_input_size"] + input_size) / n
        self.stats["avg_output_size"] = ((n - 1) * self.stats["avg_output_size"] + output_size) / n
        
        if output_size < input_size:
            self.stats["total_truncated"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = self.stats.copy()
        stats["context_stats"] = self.context_manager.get_stats()
        
        if stats["total_processed"] > 0:
            stats["avg_processing_time"] = stats["total_processing_time"] / stats["total_processed"]
            stats["truncation_rate"] = stats["total_truncated"] / stats["total_processed"]
        else:
            stats["avg_processing_time"] = 0.0
            stats["truncation_rate"] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            "total_processed": 0,
            "total_truncated": 0,
            "total_processing_time": 0.0,
            "avg_input_size": 0.0,
            "avg_output_size": 0.0
        }
        self.context_manager.clear()
    
    def update_config(self, config: FeedbackConfig):
        """Update processor configuration."""
        self.config = config
        self.context_manager.max_context_length = config.max_context_length
        self.assertion_filter.top_k = config.top_k_assertions


# Utility functions for feedback processing
def create_test_feedback_config() -> FeedbackConfig:
    """Create a feedback configuration suitable for testing."""
    return FeedbackConfig(
        max_feedback_length=5000,
        context_strategy=ContextStrategy.ADAPTIVE,
        max_context_length=10000,
        enable_stack_summarization=True,
        enable_file_context=True,
        top_k_assertions=3,
        truncation_strategy="intelligent",
        preserve_error_info=True
    )


def extract_key_information(content: str) -> Dict[str, List[str]]:
    """Extract key information from content for analysis.
    
    Args:
        content: Content to analyze
        
    Returns:
        Dictionary with categorized key information
    """
    info = {
        'errors': [],
        'warnings': [],
        'files': [],
        'functions': [],
        'tests': []
    }
    
    lines = content.split('\n')
    
    for line in lines:
        line_lower = line.lower()
        
        # Extract errors
        if any(keyword in line_lower for keyword in ['error', 'exception', 'failed']):
            info['errors'].append(line.strip())
        
        # Extract warnings
        elif 'warning' in line_lower:
            info['warnings'].append(line.strip())
        
        # Extract file references
        file_match = re.search(r'File "([^"]+)"', line)
        if file_match:
            info['files'].append(file_match.group(1))
        
        # Extract function references
        func_match = re.search(r'def (\w+)\(', line)
        if func_match:
            info['functions'].append(func_match.group(1))
        
        # Extract test references
        if 'test' in line_lower and any(keyword in line_lower for keyword in ['pass', 'fail', 'assert']):
            info['tests'].append(line.strip())
    
    return info