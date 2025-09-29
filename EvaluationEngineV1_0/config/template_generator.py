"""
Template Generator for Multi-Turn Evaluation Configuration

Generates configuration templates for different evaluation scenarios
and use cases.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TemplateGenerator:
    """
    Configuration template generator for multi-turn evaluation.
    
    Implements requirement 9.3: Configuration templates and examples.
    """
    
    def __init__(self):
        self.templates = self._create_templates()
    
    def get_template(self, template_name: str) -> Dict[str, Any]:
        """
        Get configuration template by name.
        
        Args:
            template_name: Template name
            
        Returns:
            Template configuration dictionary
            
        Raises:
            ValueError: If template doesn't exist
        """
        if template_name not in self.templates:
            available = ', '.join(self.templates.keys())
            raise ValueError(f"Template '{template_name}' not found. Available templates: {available}")
        
        template = self.templates[template_name].copy()
        
        # Add generation metadata
        template['metadata'] = template.get('metadata', {})
        template['metadata']['generated_at'] = datetime.utcnow().isoformat()
        template['metadata']['template_name'] = template_name
        template['metadata']['generator_version'] = '1.0.0'
        
        return template
    
    def list_templates(self) -> List[Dict[str, str]]:
        """
        List available templates with descriptions.
        
        Returns:
            List of template information dictionaries
        """
        template_info = []
        
        for name, template in self.templates.items():
            info = {
                'name': name,
                'description': template.get('_description', 'No description available'),
                'use_case': template.get('_use_case', 'General'),
                'complexity': template.get('_complexity', 'Medium'),
                'estimated_duration': template.get('_estimated_duration', 'Unknown')
            }
            template_info.append(info)
        
        return template_info
    
    def create_custom_template(self, 
                             model_id: str,
                             task_ids: List[str],
                             scenario: str = 'general',
                             complexity: str = 'medium',
                             **kwargs) -> Dict[str, Any]:
        """
        Create custom configuration template.
        
        Args:
            model_id: Model identifier
            task_ids: List of task IDs
            scenario: Evaluation scenario
            complexity: Complexity level
            **kwargs: Additional configuration options
            
        Returns:
            Custom configuration template
        """
        # Base configuration
        template = {
            'model_id': model_id,
            'task_ids': task_ids,
            'metadata': {
                'scenario': scenario,
                'complexity': complexity,
                'created_at': datetime.utcnow().isoformat(),
                'custom_template': True
            }
        }
        
        # Apply scenario-specific settings
        if scenario == 'coding':
            template.update(self._get_coding_scenario_settings())
        elif scenario == 'debugging':
            template.update(self._get_debugging_scenario_settings())
        elif scenario == 'research':
            template.update(self._get_research_scenario_settings())
        elif scenario == 'security':
            template.update(self._get_security_scenario_settings())
        else:
            template.update(self._get_general_scenario_settings())
        
        # Apply complexity-specific settings
        if complexity == 'simple':
            template.update(self._get_simple_complexity_settings())
        elif complexity == 'complex':
            template.update(self._get_complex_complexity_settings())
        else:
            template.update(self._get_medium_complexity_settings())
        
        # Apply custom overrides
        template.update(kwargs)
        
        return template
    
    def generate_benchmark_template(self, benchmark_name: str) -> Dict[str, Any]:
        """
        Generate template for specific benchmark.
        
        Args:
            benchmark_name: Benchmark name
            
        Returns:
            Benchmark-specific configuration template
        """
        benchmark_templates = {
            'swe_bench': self._create_swe_bench_template(),
            'intercode': self._create_intercode_template(),
            'convcode': self._create_convcode_template(),
            'bugs_in_py': self._create_bugs_in_py_template(),
            'defects4j': self._create_defects4j_template(),
            'humaneval': self._create_humaneval_template(),
            'mbpp': self._create_mbpp_template()
        }
        
        if benchmark_name not in benchmark_templates:
            available = ', '.join(benchmark_templates.keys())
            raise ValueError(f"Benchmark '{benchmark_name}' not supported. Available: {available}")
        
        return benchmark_templates[benchmark_name]
    
    def _create_templates(self) -> Dict[str, Dict[str, Any]]:
        """Create all configuration templates."""
        templates = {}
        
        # Basic template
        templates['basic'] = {
            '_description': 'Basic multi-turn evaluation configuration',
            '_use_case': 'General purpose evaluation',
            '_complexity': 'Low',
            '_estimated_duration': '30-60 minutes',
            'model_id': 'gpt-4',
            'task_ids': ['example_multi_turn_task'],
            'max_turns': 10,
            'timeout_seconds': 3600,
            'feedback_strategy': 'adaptive',
            'safety_level': 'moderate',
            'enable_context_retention': True,
            'metadata': {
                'description': 'Basic multi-turn evaluation',
                'use_case': 'general'
            }
        }
        
        # Advanced template
        templates['advanced'] = {
            '_description': 'Advanced multi-turn evaluation with comprehensive settings',
            '_use_case': 'Complex evaluation scenarios',
            '_complexity': 'High',
            '_estimated_duration': '2-4 hours',
            'model_id': 'gpt-4',
            'task_ids': [
                'advanced_multi_turn_task_1',
                'advanced_multi_turn_task_2',
                'advanced_multi_turn_task_3'
            ],
            'max_turns': 20,
            'timeout_seconds': 14400,  # 4 hours
            'feedback_strategy': 'full',
            'safety_level': 'moderate',
            'enable_context_retention': True,
            'context_strategy': 'adaptive',
            'max_feedback_length': 20000,
            'max_context_length': 100000,
            'enable_stack_summarization': True,
            'enable_file_context': True,
            'top_k_assertions': 10,
            'allowed_tools': ['python', 'bash', 'git', 'curl', 'wget'],
            'enable_sandboxing': True,
            'max_execution_time': 600,
            'termination_conditions': ['success', 'max_turns', 'timeout', 'safety_violation'],
            'resource_limits': {
                'max_memory_mb': 4096,
                'max_cpu_percent': 80,
                'max_disk_mb': 2048,
                'max_network_requests': 100
            },
            'dangerous_patterns': [
                'rm -rf',
                'sudo.*rm',
                'chmod 777',
                'dd if=/dev/zero'
            ],
            'metadata': {
                'description': 'Advanced multi-turn evaluation with comprehensive monitoring',
                'use_case': 'complex_scenarios',
                'monitoring_level': 'detailed'
            }
        }
        
        # Coding template
        templates['coding'] = {
            '_description': 'Multi-turn coding evaluation template',
            '_use_case': 'Code generation and debugging tasks',
            '_complexity': 'Medium',
            '_estimated_duration': '1-2 hours',
            'model_id': 'gpt-4',
            'task_ids': [
                'coding_task_python',
                'coding_task_javascript',
                'coding_task_debugging'
            ],
            'max_turns': 15,
            'timeout_seconds': 7200,
            'feedback_strategy': 'adaptive',
            'safety_level': 'moderate',
            'enable_context_retention': True,
            'context_strategy': 'full',
            'max_feedback_length': 15000,
            'max_context_length': 75000,
            'enable_stack_summarization': True,
            'enable_file_context': True,
            'top_k_assertions': 8,
            'allowed_tools': ['python', 'node', 'npm', 'pip', 'git'],
            'enable_sandboxing': True,
            'max_execution_time': 300,
            'resource_limits': {
                'max_memory_mb': 2048,
                'max_cpu_percent': 70,
                'max_disk_mb': 1024
            },
            'metadata': {
                'description': 'Multi-turn coding evaluation',
                'use_case': 'coding',
                'languages': ['python', 'javascript']
            }
        }
        
        # Research template
        templates['research'] = {
            '_description': 'Research and analysis evaluation template',
            '_use_case': 'Research tasks and data analysis',
            '_complexity': 'High',
            '_estimated_duration': '3-6 hours',
            'model_id': 'gpt-4',
            'task_ids': [
                'research_task_literature_review',
                'research_task_data_analysis',
                'research_task_hypothesis_testing'
            ],
            'max_turns': 25,
            'timeout_seconds': 21600,  # 6 hours
            'feedback_strategy': 'full',
            'safety_level': 'permissive',
            'enable_context_retention': True,
            'context_strategy': 'full',
            'max_feedback_length': 25000,
            'max_context_length': 150000,
            'enable_stack_summarization': False,
            'enable_file_context': True,
            'top_k_assertions': 15,
            'allowed_tools': ['python', 'R', 'curl', 'wget', 'pandoc'],
            'enable_sandboxing': True,
            'max_execution_time': 900,
            'resource_limits': {
                'max_memory_mb': 8192,
                'max_cpu_percent': 90,
                'max_disk_mb': 4096,
                'max_network_requests': 500
            },
            'metadata': {
                'description': 'Research and analysis evaluation',
                'use_case': 'research',
                'domain': 'academic'
            }
        }
        
        # Security template
        templates['security'] = {
            '_description': 'Security-focused evaluation template',
            '_use_case': 'Security analysis and penetration testing',
            '_complexity': 'High',
            '_estimated_duration': '2-4 hours',
            'model_id': 'gpt-4',
            'task_ids': [
                'security_task_vulnerability_analysis',
                'security_task_code_review',
                'security_task_threat_modeling'
            ],
            'max_turns': 18,
            'timeout_seconds': 14400,
            'feedback_strategy': 'adaptive',
            'safety_level': 'strict',
            'enable_context_retention': True,
            'context_strategy': 'adaptive',
            'max_feedback_length': 12000,
            'max_context_length': 60000,
            'enable_stack_summarization': True,
            'enable_file_context': True,
            'top_k_assertions': 6,
            'allowed_tools': ['python', 'bash'],
            'enable_sandboxing': True,
            'max_execution_time': 180,
            'resource_limits': {
                'max_memory_mb': 1024,
                'max_cpu_percent': 50,
                'max_disk_mb': 512
            },
            'dangerous_patterns': [
                'rm.*-rf',
                'sudo',
                'chmod.*777',
                'wget.*http',
                'curl.*-X.*POST',
                'nc.*-l',
                'netcat',
                'nmap',
                'sqlmap'
            ],
            'metadata': {
                'description': 'Security-focused evaluation with strict controls',
                'use_case': 'security',
                'security_level': 'high'
            }
        }
        
        # Performance template
        templates['performance'] = {
            '_description': 'Performance testing evaluation template',
            '_use_case': 'Performance optimization and benchmarking',
            '_complexity': 'Medium',
            '_estimated_duration': '1-3 hours',
            'model_id': 'gpt-4',
            'task_ids': [
                'performance_task_optimization',
                'performance_task_benchmarking',
                'performance_task_profiling'
            ],
            'max_turns': 12,
            'timeout_seconds': 10800,
            'feedback_strategy': 'adaptive',
            'safety_level': 'moderate',
            'enable_context_retention': True,
            'context_strategy': 'adaptive',
            'max_feedback_length': 10000,
            'max_context_length': 50000,
            'enable_stack_summarization': True,
            'enable_file_context': True,
            'top_k_assertions': 5,
            'allowed_tools': ['python', 'bash', 'time', 'perf'],
            'enable_sandboxing': True,
            'max_execution_time': 600,
            'resource_limits': {
                'max_memory_mb': 4096,
                'max_cpu_percent': 95,
                'max_disk_mb': 2048
            },
            'metadata': {
                'description': 'Performance testing and optimization evaluation',
                'use_case': 'performance',
                'focus': 'optimization'
            }
        }
        
        return templates
    
    def _create_swe_bench_template(self) -> Dict[str, Any]:
        """Create SWE-bench specific template."""
        return {
            '_description': 'SWE-bench software engineering evaluation',
            '_use_case': 'Real-world software bug fixing',
            '_complexity': 'High',
            '_estimated_duration': '4-8 hours',
            'model_id': 'gpt-4',
            'task_ids': [
                'swe_bench_lite_001',
                'swe_bench_lite_002',
                'swe_bench_lite_003'
            ],
            'max_turns': 25,
            'timeout_seconds': 28800,  # 8 hours
            'feedback_strategy': 'full',
            'safety_level': 'moderate',
            'enable_context_retention': True,
            'context_strategy': 'full',
            'max_feedback_length': 25000,
            'max_context_length': 150000,
            'enable_stack_summarization': True,
            'enable_file_context': True,
            'top_k_assertions': 12,
            'allowed_tools': ['python', 'bash', 'git', 'pytest', 'pip', 'conda'],
            'enable_sandboxing': True,
            'max_execution_time': 1200,
            'resource_limits': {
                'max_memory_mb': 8192,
                'max_cpu_percent': 85,
                'max_disk_mb': 4096
            },
            'dangerous_patterns': [
                'rm.*-rf.*/',
                'sudo.*rm',
                'chmod.*777'
            ],
            'metadata': {
                'description': 'SWE-bench evaluation for real-world bug fixing',
                'benchmark': 'swe_bench',
                'subset': 'lite',
                'domain': 'software_engineering'
            }
        }
    
    def _create_intercode_template(self) -> Dict[str, Any]:
        """Create InterCode specific template."""
        return {
            '_description': 'InterCode interactive coding evaluation',
            '_use_case': 'Interactive coding in multiple environments',
            '_complexity': 'Medium',
            '_estimated_duration': '2-4 hours',
            'model_id': 'gpt-4',
            'task_ids': [
                'intercode_python_001',
                'intercode_bash_001',
                'intercode_sql_001'
            ],
            'max_turns': 15,
            'timeout_seconds': 14400,
            'feedback_strategy': 'adaptive',
            'safety_level': 'moderate',
            'enable_context_retention': True,
            'context_strategy': 'adaptive',
            'max_feedback_length': 15000,
            'max_context_length': 75000,
            'enable_stack_summarization': True,
            'enable_file_context': False,
            'top_k_assertions': 8,
            'allowed_tools': ['python', 'bash', 'sqlite3', 'mysql'],
            'enable_sandboxing': True,
            'max_execution_time': 300,
            'resource_limits': {
                'max_memory_mb': 2048,
                'max_cpu_percent': 70,
                'max_disk_mb': 1024
            },
            'metadata': {
                'description': 'InterCode interactive coding evaluation',
                'benchmark': 'intercode',
                'environments': ['python', 'bash', 'sql']
            }
        }
    
    def _get_coding_scenario_settings(self) -> Dict[str, Any]:
        """Get settings for coding scenario."""
        return {
            'max_turns': 15,
            'feedback_strategy': 'adaptive',
            'enable_stack_summarization': True,
            'allowed_tools': ['python', 'node', 'git', 'pip', 'npm']
        }
    
    def _get_debugging_scenario_settings(self) -> Dict[str, Any]:
        """Get settings for debugging scenario."""
        return {
            'max_turns': 20,
            'feedback_strategy': 'full',
            'enable_stack_summarization': True,
            'enable_file_context': True,
            'allowed_tools': ['python', 'gdb', 'strace', 'git']
        }
    
    def _get_research_scenario_settings(self) -> Dict[str, Any]:
        """Get settings for research scenario."""
        return {
            'max_turns': 25,
            'feedback_strategy': 'full',
            'max_context_length': 150000,
            'allowed_tools': ['python', 'R', 'curl', 'wget']
        }
    
    def _get_security_scenario_settings(self) -> Dict[str, Any]:
        """Get settings for security scenario."""
        return {
            'safety_level': 'strict',
            'max_execution_time': 180,
            'dangerous_patterns': ['rm.*-rf', 'sudo', 'chmod.*777']
        }
    
    def _get_general_scenario_settings(self) -> Dict[str, Any]:
        """Get settings for general scenario."""
        return {
            'max_turns': 10,
            'feedback_strategy': 'adaptive',
            'safety_level': 'moderate'
        }
    
    def _get_simple_complexity_settings(self) -> Dict[str, Any]:
        """Get settings for simple complexity."""
        return {
            'max_turns': 8,
            'timeout_seconds': 1800,
            'max_feedback_length': 5000
        }
    
    def _get_medium_complexity_settings(self) -> Dict[str, Any]:
        """Get settings for medium complexity."""
        return {
            'max_turns': 12,
            'timeout_seconds': 3600,
            'max_feedback_length': 10000
        }
    
    def _get_complex_complexity_settings(self) -> Dict[str, Any]:
        """Get settings for complex complexity."""
        return {
            'max_turns': 20,
            'timeout_seconds': 7200,
            'max_feedback_length': 20000
        }