"""
Tests for ConvCodeBench and language-specific adapters.

This module contains comprehensive tests for the ConvCodeBench adapter
(conversation replay), BugsInPy adapter (Python bug fixing), and 
Defects4J adapter (Java bug fixing).
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from EvaluationEngineV1_0.core.convcode_adapters import (
    ConversationTurn,
    ConversationLog,
    ConversationReplayEnvironment,
    ConvCodeBenchAdapter,
    ConvCodeBenchTask,
    BugFixEnvironment,
    BugsInPyAdapter,
    Defects4JAdapter,
    BugFixTask
)
from EvaluationEngineV1_0.core.adapters import AdapterStatus
from EvaluationEngineV1_0.core.exceptions import AdapterError, ConfigurationError, TaskExecutionError
from EvaluationEngineV1_0.core.task_types import TaskType


class TestConversationTurn(unittest.TestCase):
    """Test ConversationTurn data model."""
    
    def test_conversation_turn_creation(self):
        """Test creating a conversation turn."""
        turn = ConversationTurn(
            turn_id=1,
            role="user",
            content="Hello, can you help me fix this bug?",
            metadata={"language": "python"}
        )
        
        self.assertEqual(turn.turn_id, 1)
        self.assertEqual(turn.role, "user")
        self.assertEqual(turn.content, "Hello, can you help me fix this bug?")
        self.assertEqual(turn.metadata["language"], "python")
        self.assertIsInstance(turn.timestamp, datetime)
    
    def test_conversation_turn_with_timestamp(self):
        """Test creating a conversation turn with explicit timestamp."""
        timestamp = datetime.now()
        turn = ConversationTurn(
            turn_id=2,
            role="assistant",
            content="I'd be happy to help!",
            timestamp=timestamp
        )
        
        self.assertEqual(turn.timestamp, timestamp)


class TestConversationLog(unittest.TestCase):
    """Test ConversationLog data model."""
    
    def test_conversation_log_creation(self):
        """Test creating a conversation log."""
        turns = [
            ConversationTurn(1, "user", "Fix this bug"),
            ConversationTurn(2, "assistant", "I'll help you")
        ]
        
        log = ConversationLog(
            conversation_id="conv_001",
            task_description="Fix Python import error",
            turns=turns,
            expected_outcome={"bug_fixed": True}
        )
        
        self.assertEqual(log.conversation_id, "conv_001")
        self.assertEqual(log.task_description, "Fix Python import error")
        self.assertEqual(len(log.turns), 2)
        self.assertEqual(log.expected_outcome["bug_fixed"], True)


class TestConversationReplayEnvironment(unittest.TestCase):
    """Test ConversationReplayEnvironment."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_conversation = {
            'conversation_id': 'test_conv_001',
            'task_description': 'Fix a Python import bug',
            'turns': [
                {
                    'turn_id': 1,
                    'role': 'user',
                    'content': 'I have an import error in my Python code',
                    'timestamp': datetime.now().isoformat(),
                    'metadata': {}
                },
                {
                    'turn_id': 2,
                    'role': 'assistant',
                    'content': 'I can help you fix that. Can you show me the error?',
                    'timestamp': datetime.now().isoformat(),
                    'metadata': {}
                },
                {
                    'turn_id': 3,
                    'role': 'user',
                    'content': 'ImportError: No module named requests',
                    'timestamp': datetime.now().isoformat(),
                    'metadata': {}
                },
                {
                    'turn_id': 4,
                    'role': 'assistant',
                    'content': 'You need to install the requests module: pip install requests',
                    'timestamp': datetime.now().isoformat(),
                    'metadata': {}
                }
            ],
            'expected_outcome': {'bug_fixed': True},
            'metadata': {'language': 'python'}
        }
    
    def test_environment_initialization(self):
        """Test environment initialization with conversation log."""
        config = {
            'conversation_log': self.sample_conversation,
            'agent_role': 'assistant',
            'user_role': 'user'
        }
        
        env = ConversationReplayEnvironment(config)
        
        self.assertIsNotNone(env.conversation_log)
        self.assertEqual(env.conversation_log.conversation_id, 'test_conv_001')
        self.assertEqual(len(env.original_agent_outputs), 2)  # 2 assistant turns
    
    def test_environment_reset(self):
        """Test environment reset functionality."""
        config = {
            'conversation_log': self.sample_conversation,
            'agent_role': 'assistant'
        }
        
        env = ConversationReplayEnvironment(config)
        observation = env.reset()
        
        self.assertEqual(env.current_turn, 0)
        self.assertEqual(len(env.conversation_history), 0)
        self.assertEqual(len(env.replaced_outputs), 0)
        self.assertFalse(env.task_completed)
        
        self.assertIn('task_description', observation)
        self.assertIn('conversation_id', observation)
        self.assertEqual(observation['task_description'], 'Fix a Python import bug')
    
    def test_environment_step(self):
        """Test environment step execution."""
        config = {
            'conversation_log': self.sample_conversation,
            'agent_role': 'assistant'
        }
        
        env = ConversationReplayEnvironment(config)
        env.reset()
        
        # First agent response
        action = "I can help you with that import error."
        observation, reward, done, info = env.step(action)
        
        self.assertGreater(reward, 0)  # Should get some reward for similarity
        self.assertFalse(done)  # Should not be done yet
        self.assertEqual(len(env.replaced_outputs), 1)
        self.assertIn('original_output', info)
        self.assertIn('replaced_output', info)
    
    def test_environment_success(self):
        """Test environment success detection."""
        config = {
            'conversation_log': self.sample_conversation,
            'agent_role': 'assistant'
        }
        
        env = ConversationReplayEnvironment(config)
        env.reset()
        
        # Complete all agent turns
        env.step("I can help you with that.")
        env.step("You need to install requests.")
        
        self.assertTrue(env.task_completed)
        self.assertTrue(env.success())
    
    def test_environment_metrics(self):
        """Test environment metrics calculation."""
        config = {
            'conversation_log': self.sample_conversation,
            'agent_role': 'assistant'
        }
        
        env = ConversationReplayEnvironment(config)
        env.reset()
        
        metrics = env.get_metrics()
        
        self.assertIn('conversation_completion', metrics)
        self.assertIn('agent_turns_completed', metrics)
        self.assertIn('average_turn_similarity', metrics)
        self.assertIn('conversation_coherence', metrics)
    
    def test_similarity_calculation(self):
        """Test turn reward calculation based on similarity."""
        config = {
            'conversation_log': self.sample_conversation,
            'agent_role': 'assistant'
        }
        
        env = ConversationReplayEnvironment(config)
        
        # Test exact match
        exact_reward = env._calculate_turn_reward("test message", "test message")
        self.assertEqual(exact_reward, 1.0)
        
        # Test partial match
        partial_reward = env._calculate_turn_reward("test message", "test different message")
        self.assertGreater(partial_reward, 0.0)
        self.assertLess(partial_reward, 1.0)
        
        # Test no match
        no_match_reward = env._calculate_turn_reward("completely different", "test message")
        self.assertGreaterEqual(no_match_reward, 0.0)


class TestConvCodeBenchAdapter(unittest.TestCase):
    """Test ConvCodeBench adapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.dataset_path = os.path.join(self.temp_dir, "conversations.json")
        
        # Create sample conversation data
        sample_data = [
            {
                'conversation_id': 'conv_001',
                'task_description': 'Fix Python import error',
                'turns': [
                    {
                        'turn_id': 1,
                        'role': 'user',
                        'content': 'I have an import error',
                        'timestamp': datetime.now().isoformat(),
                        'metadata': {}
                    },
                    {
                        'turn_id': 2,
                        'role': 'assistant',
                        'content': 'I can help you fix that',
                        'timestamp': datetime.now().isoformat(),
                        'metadata': {}
                    }
                ],
                'expected_outcome': {'bug_fixed': True},
                'metadata': {'language': 'python', 'difficulty': 'easy'}
            }
        ]
        
        with open(self.dataset_path, 'w') as f:
            json.dump(sample_data, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_adapter_info(self):
        """Test adapter information."""
        config = {'dataset_path': self.dataset_path}
        adapter = ConvCodeBenchAdapter(config)
        
        info = adapter.get_adapter_info()
        
        self.assertEqual(info.name, "convcodebench")
        self.assertIn(TaskType.MULTI_TURN, info.supported_task_types)
        self.assertIn("conversation_replay", info.capabilities)
        self.assertIn("agent_output_replacement", info.capabilities)
    
    def test_adapter_initialization(self):
        """Test adapter initialization."""
        config = {'dataset_path': self.dataset_path}
        adapter = ConvCodeBenchAdapter(config)
        
        self.assertTrue(adapter.initialize())
        self.assertEqual(adapter.get_status(), AdapterStatus.READY)
        self.assertEqual(len(adapter.conversation_logs), 1)
    
    def test_adapter_initialization_failure(self):
        """Test adapter initialization with invalid path."""
        config = {'dataset_path': '/nonexistent/path'}
        adapter = ConvCodeBenchAdapter(config)
        
        self.assertFalse(adapter.initialize())
        self.assertEqual(adapter.get_status(), AdapterStatus.ERROR)
    
    def test_create_environment(self):
        """Test environment creation."""
        config = {'dataset_path': self.dataset_path}
        adapter = ConvCodeBenchAdapter(config)
        adapter.initialize()
        
        task_config = {'conversation_id': 'conv_001'}
        env = adapter.create_environment(task_config)
        
        self.assertIsInstance(env, ConversationReplayEnvironment)
        self.assertEqual(env.conversation_log.conversation_id, 'conv_001')
    
    def test_load_tasks(self):
        """Test loading tasks from adapter."""
        config = {'dataset_path': self.dataset_path}
        adapter = ConvCodeBenchAdapter(config)
        adapter.initialize()
        
        tasks = adapter.load_tasks()
        
        self.assertEqual(len(tasks), 1)
        self.assertIsInstance(tasks[0], ConvCodeBenchTask)
        self.assertEqual(tasks[0].get_task_type(), TaskType.MULTI_TURN)
    
    def test_load_tasks_with_filter(self):
        """Test loading tasks with filters."""
        config = {'dataset_path': self.dataset_path}
        adapter = ConvCodeBenchAdapter(config)
        adapter.initialize()
        
        # Filter by language
        tasks = adapter.load_tasks({'language': ['python']})
        self.assertEqual(len(tasks), 1)
        
        # Filter by non-matching language
        tasks = adapter.load_tasks({'language': ['java']})
        self.assertEqual(len(tasks), 0)
    
    def test_convert_results(self):
        """Test result conversion."""
        config = {'dataset_path': self.dataset_path}
        adapter = ConvCodeBenchAdapter(config)
        
        results = {
            'task_id': 'conv_001',
            'success': True,
            'score': 0.85,
            'execution_time': 120.5,
            'turns': 5,
            'tokens_used': 1000,
            'cost': 0.02,
            'conversation_id': 'conv_001',
            'similarity_score': 0.85,
            'coherence_score': 0.90
        }
        
        standardized = adapter.convert_results(results)
        
        self.assertEqual(standardized.task_id, 'conv_001')
        self.assertEqual(standardized.adapter_name, 'convcodebench')
        self.assertTrue(standardized.success)
        self.assertEqual(standardized.score, 0.85)
        self.assertEqual(standardized.metadata['similarity_score'], 0.85)


class TestBugFixEnvironment(unittest.TestCase):
    """Test BugFixEnvironment base class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = os.path.join(self.temp_dir, "test_project")
        os.makedirs(self.project_path)
        
        # Create a simple Python file with a bug
        with open(os.path.join(self.project_path, "main.py"), 'w') as f:
            f.write("import nonexistent_module\nprint('Hello World')\n")
        
        # Create a simple test file
        with open(os.path.join(self.project_path, "test_main.py"), 'w') as f:
            f.write("import unittest\nfrom main import *\n\nclass TestMain(unittest.TestCase):\n    def test_import(self):\n        self.assertTrue(True)\n")
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_environment_initialization(self):
        """Test bug fix environment initialization."""
        config = {
            'bug_id': 'bug_001',
            'project_path': self.project_path,
            'test_command': 'python -m pytest test_main.py',
            'language': 'python',
            'bug_description': 'Import error in main.py'
        }
        
        env = BugFixEnvironment(config)
        
        self.assertEqual(env.bug_id, 'bug_001')
        self.assertEqual(env.language, 'python')
        self.assertIsNotNone(env.working_directory)
        self.assertTrue(os.path.exists(env.working_directory))
    
    def test_environment_reset(self):
        """Test environment reset."""
        config = {
            'bug_id': 'bug_001',
            'project_path': self.project_path,
            'test_command': 'echo "test"',
            'language': 'python'
        }
        
        env = BugFixEnvironment(config)
        observation = env.reset()
        
        self.assertEqual(env.current_step, 0)
        self.assertEqual(len(env.files_modified), 0)
        self.assertFalse(env.bug_fixed)
        
        self.assertIn('bug_id', observation)
        self.assertIn('project_path', observation)
        self.assertEqual(observation['bug_id'], 'bug_001')
    
    @patch('subprocess.run')
    def test_file_modification_action(self, mock_run):
        """Test file modification action."""
        config = {
            'bug_id': 'bug_001',
            'project_path': self.project_path,
            'test_command': 'echo "test"',
            'language': 'python'
        }
        
        env = BugFixEnvironment(config)
        env.reset()
        
        # Test file modification
        action = "modify_file:main.py:1:1:# Fixed import"
        observation, reward, done, info = env.step(action)
        
        self.assertGreater(reward, 0)  # Should get reward for taking action
        self.assertFalse(done)
        self.assertIn('main.py', env.files_modified)
        self.assertEqual(info['action_type'], 'file_modification')
    
    @patch('subprocess.run')
    def test_test_execution_action(self, mock_run):
        """Test test execution action."""
        # Mock successful test run
        mock_run.return_value = Mock(
            returncode=0,
            stdout="PASSED",
            stderr=""
        )
        
        config = {
            'bug_id': 'bug_001',
            'project_path': self.project_path,
            'test_command': 'python -m pytest',
            'language': 'python'
        }
        
        env = BugFixEnvironment(config)
        env.reset()
        
        action = "run_tests"
        observation, reward, done, info = env.step(action)
        
        self.assertGreater(reward, 0)  # Should get reward for passing tests
        self.assertTrue(env.bug_fixed)  # Bug should be marked as fixed
        self.assertEqual(info['action_type'], 'test_execution')
    
    def test_environment_metrics(self):
        """Test environment metrics."""
        config = {
            'bug_id': 'bug_001',
            'project_path': self.project_path,
            'test_command': 'echo "test"',
            'language': 'python'
        }
        
        env = BugFixEnvironment(config)
        env.reset()
        
        metrics = env.get_metrics()
        
        self.assertIn('steps_taken', metrics)
        self.assertIn('step_efficiency', metrics)
        self.assertIn('files_modified', metrics)
        self.assertIn('bug_fixed', metrics)
        self.assertIn('test_pass_rate', metrics)


class TestBugsInPyAdapter(unittest.TestCase):
    """Test BugsInPy adapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.dataset_path = os.path.join(self.temp_dir, "bugs.json")
        
        # Create sample bug data
        sample_bugs = [
            {
                'bug_id': 'bug_001',
                'project': 'test_project',
                'project_path': '/path/to/project',
                'description': 'Import error in main module',
                'test_command': 'python -m pytest',
                'build_command': '',
                'language': 'python',
                'failing_tests': ['test_main.py::test_import'],
                'expected_fix': {'files': ['main.py']},
                'difficulty': 'easy'
            }
        ]
        
        with open(self.dataset_path, 'w') as f:
            json.dump(sample_bugs, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_adapter_info(self):
        """Test adapter information."""
        config = {'dataset_path': self.dataset_path}
        adapter = BugsInPyAdapter(config)
        
        info = adapter.get_adapter_info()
        
        self.assertEqual(info.name, "bugsinpy")
        self.assertIn(TaskType.MULTI_TURN, info.supported_task_types)
        self.assertIn("python_bug_fixing", info.capabilities)
        self.assertEqual(info.metadata['language'], 'python')
    
    def test_adapter_initialization(self):
        """Test adapter initialization."""
        config = {'dataset_path': self.dataset_path}
        adapter = BugsInPyAdapter(config)
        
        self.assertTrue(adapter.initialize())
        self.assertEqual(adapter.get_status(), AdapterStatus.READY)
        self.assertEqual(len(adapter.bugs_data), 1)
    
    def test_load_tasks(self):
        """Test loading bug fixing tasks."""
        config = {'dataset_path': self.dataset_path}
        adapter = BugsInPyAdapter(config)
        adapter.initialize()
        
        tasks = adapter.load_tasks()
        
        self.assertEqual(len(tasks), 1)
        self.assertIsInstance(tasks[0], BugFixTask)
        self.assertEqual(tasks[0].get_task_type(), TaskType.MULTI_TURN)
    
    def test_convert_results(self):
        """Test result conversion."""
        config = {'dataset_path': self.dataset_path}
        adapter = BugsInPyAdapter(config)
        
        results = {
            'task_id': 'bug_001',
            'bug_fixed': True,
            'execution_time': 300.0,
            'steps_taken': 15,
            'files_modified': 2,
            'test_pass_rate': 1.0,
            'build_successful': True
        }
        
        standardized = adapter.convert_results(results)
        
        self.assertEqual(standardized.adapter_name, 'bugsinpy')
        self.assertTrue(standardized.success)
        self.assertEqual(standardized.score, 1.0)
        self.assertEqual(standardized.metadata['language'], 'python')


class TestDefects4JAdapter(unittest.TestCase):
    """Test Defects4J adapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.dataset_path = os.path.join(self.temp_dir, "defects.json")
        
        # Create sample defect data
        sample_defects = [
            {
                'bug_id': 'Chart-1',
                'project': 'Chart',
                'project_path': '/path/to/chart',
                'description': 'Null pointer exception in chart rendering',
                'test_command': 'mvn test',
                'build_command': 'mvn compile',
                'language': 'java',
                'failing_tests': ['org.jfree.chart.ChartTest::testNullPointer'],
                'expected_fix': {'files': ['Chart.java']},
                'difficulty': 'medium'
            }
        ]
        
        with open(self.dataset_path, 'w') as f:
            json.dump(sample_defects, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_adapter_info(self):
        """Test adapter information."""
        config = {'dataset_path': self.dataset_path}
        adapter = Defects4JAdapter(config)
        
        info = adapter.get_adapter_info()
        
        self.assertEqual(info.name, "defects4j")
        self.assertIn(TaskType.MULTI_TURN, info.supported_task_types)
        self.assertIn("java_bug_fixing", info.capabilities)
        self.assertEqual(info.metadata['language'], 'java')
    
    def test_adapter_initialization(self):
        """Test adapter initialization."""
        config = {'dataset_path': self.dataset_path}
        adapter = Defects4JAdapter(config)
        
        self.assertTrue(adapter.initialize())
        self.assertEqual(adapter.get_status(), AdapterStatus.READY)
        self.assertEqual(len(adapter.bugs_data), 1)
    
    def test_load_tasks(self):
        """Test loading Java bug fixing tasks."""
        config = {'dataset_path': self.dataset_path}
        adapter = Defects4JAdapter(config)
        adapter.initialize()
        
        tasks = adapter.load_tasks()
        
        self.assertEqual(len(tasks), 1)
        self.assertIsInstance(tasks[0], BugFixTask)
        self.assertEqual(tasks[0].get_task_type(), TaskType.MULTI_TURN)


class TestBugFixTask(unittest.TestCase):
    """Test BugFixTask implementation."""
    
    def test_task_creation(self):
        """Test bug fix task creation."""
        bug_data = {
            'bug_id': 'test_bug',
            'description': 'Test bug description',
            'language': 'python',
            'project': 'test_project',
            'difficulty': 'easy'
        }
        
        adapter = Mock()
        task = BugFixTask("test_task", bug_data, adapter)
        
        self.assertEqual(task.get_id(), "test_task")
        self.assertEqual(task.get_task_type(), TaskType.MULTI_TURN)
        self.assertEqual(task.get_description(), "Test bug description")
        
        metadata = task.get_metadata()
        self.assertEqual(metadata['bug_id'], 'test_bug')
        self.assertEqual(metadata['language'], 'python')
    
    def test_required_capabilities(self):
        """Test required capabilities for bug fix task."""
        bug_data = {'language': 'python'}
        adapter = Mock()
        task = BugFixTask("test_task", bug_data, adapter)
        
        capabilities = task.get_required_capabilities()
        
        self.assertIn("python_programming", capabilities)
        self.assertIn("bug_fixing", capabilities)
        self.assertIn("multi_turn_interaction", capabilities)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests with actual benchmark datasets."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up integration test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_convcodebench_integration(self):
        """Test ConvCodeBench integration with sample data."""
        # Create sample conversation dataset
        conversations = [
            {
                'conversation_id': 'python_debug_001',
                'task_description': 'Debug Python script with import error',
                'turns': [
                    {
                        'turn_id': 1,
                        'role': 'user',
                        'content': 'My Python script has an import error. Can you help?',
                        'timestamp': datetime.now().isoformat(),
                        'metadata': {}
                    },
                    {
                        'turn_id': 2,
                        'role': 'assistant',
                        'content': 'I\'d be happy to help! Can you show me the error message?',
                        'timestamp': datetime.now().isoformat(),
                        'metadata': {}
                    },
                    {
                        'turn_id': 3,
                        'role': 'user',
                        'content': 'ImportError: No module named \'requests\'',
                        'timestamp': datetime.now().isoformat(),
                        'metadata': {}
                    },
                    {
                        'turn_id': 4,
                        'role': 'assistant',
                        'content': 'You need to install the requests module. Run: pip install requests',
                        'timestamp': datetime.now().isoformat(),
                        'metadata': {}
                    }
                ],
                'expected_outcome': {'bug_fixed': True, 'solution': 'pip install requests'},
                'metadata': {'language': 'python', 'difficulty': 'easy', 'category': 'import_error'}
            }
        ]
        
        dataset_file = os.path.join(self.temp_dir, 'conversations.json')
        with open(dataset_file, 'w') as f:
            json.dump(conversations, f)
        
        # Test adapter initialization and task loading
        config = {'dataset_path': dataset_file}
        adapter = ConvCodeBenchAdapter(config)
        
        self.assertTrue(adapter.initialize())
        
        tasks = adapter.load_tasks()
        self.assertEqual(len(tasks), 1)
        
        # Test environment creation and execution
        task_config = {'conversation_id': 'python_debug_001'}
        env = adapter.create_environment(task_config)
        
        observation = env.reset()
        self.assertIn('task_description', observation)
        
        # Simulate agent responses
        response1 = "I can help you with that import error!"
        obs1, reward1, done1, info1 = env.step(response1)
        
        self.assertGreater(reward1, 0)
        self.assertFalse(done1)
        
        response2 = "Install requests with pip install requests"
        obs2, reward2, done2, info2 = env.step(response2)
        
        self.assertGreater(reward2, 0)
        self.assertTrue(done2)
        self.assertTrue(env.success())
    
    def test_bugsinpy_integration(self):
        """Test BugsInPy integration with sample bug data."""
        # Create sample bug dataset
        bugs = [
            {
                'bug_id': 'sample_bug_001',
                'project': 'sample_project',
                'project_path': os.path.join(self.temp_dir, 'sample_project'),
                'description': 'Division by zero error in calculator',
                'test_command': 'python -m pytest test_calculator.py',
                'build_command': '',
                'language': 'python',
                'failing_tests': ['test_calculator.py::test_divide'],
                'expected_fix': {'files': ['calculator.py'], 'lines_changed': 5},
                'difficulty': 'easy',
                'category': 'arithmetic_error'
            }
        ]
        
        # Create project directory and files
        project_dir = bugs[0]['project_path']
        os.makedirs(project_dir)
        
        # Create buggy calculator.py
        with open(os.path.join(project_dir, 'calculator.py'), 'w') as f:
            f.write("""
def divide(a, b):
    return a / b  # Bug: no check for division by zero

def add(a, b):
    return a + b
""")
        
        # Create test file
        with open(os.path.join(project_dir, 'test_calculator.py'), 'w') as f:
            f.write("""
import unittest
from calculator import divide, add

class TestCalculator(unittest.TestCase):
    def test_divide(self):
        self.assertEqual(divide(10, 2), 5)
        # This should not raise an exception
        result = divide(10, 0)
        self.assertIsNone(result)
    
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

if __name__ == '__main__':
    unittest.main()
""")
        
        dataset_file = os.path.join(self.temp_dir, 'bugs.json')
        with open(dataset_file, 'w') as f:
            json.dump(bugs, f)
        
        # Test adapter
        config = {'dataset_path': dataset_file}
        adapter = BugsInPyAdapter(config)
        
        self.assertTrue(adapter.initialize())
        
        tasks = adapter.load_tasks()
        self.assertEqual(len(tasks), 1)
        
        # Test task metadata
        task = tasks[0]
        metadata = task.get_metadata()
        self.assertEqual(metadata['language'], 'python')
        self.assertEqual(metadata['bug_id'], 'sample_bug_001')
    
    def test_cross_language_compatibility(self):
        """Test compatibility across different programming languages."""
        # Test that adapters can handle multiple languages
        
        # Python bugs
        python_bugs = [{'bug_id': 'py_001', 'language': 'python', 'project_path': '/tmp/py'}]
        python_file = os.path.join(self.temp_dir, 'python_bugs.json')
        with open(python_file, 'w') as f:
            json.dump(python_bugs, f)
        
        # Java bugs  
        java_bugs = [{'bug_id': 'java_001', 'language': 'java', 'project_path': '/tmp/java'}]
        java_file = os.path.join(self.temp_dir, 'java_bugs.json')
        with open(java_file, 'w') as f:
            json.dump(java_bugs, f)
        
        # Test both adapters
        py_adapter = BugsInPyAdapter({'dataset_path': python_file})
        java_adapter = Defects4JAdapter({'dataset_path': java_file})
        
        self.assertTrue(py_adapter.initialize())
        self.assertTrue(java_adapter.initialize())
        
        py_tasks = py_adapter.load_tasks()
        java_tasks = java_adapter.load_tasks()
        
        self.assertEqual(len(py_tasks), 1)
        self.assertEqual(len(java_tasks), 1)
        
        # Verify language-specific capabilities
        py_capabilities = py_tasks[0].get_required_capabilities()
        java_capabilities = java_tasks[0].get_required_capabilities()
        
        self.assertIn('python_programming', py_capabilities)
        self.assertIn('java_programming', java_capabilities)


if __name__ == '__main__':
    unittest.main()