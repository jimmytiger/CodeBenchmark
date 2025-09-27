"""
Unit tests for TaskRegistry.
"""

import pytest
from unittest.mock import Mock, patch
import json
from pathlib import Path

from evaluation_engine.core.task_registration import TaskRegistry, TaskDefinition


class TestTaskRegistry:
    """Test cases for TaskRegistry."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = TaskRegistry()
        
        assert registry.tasks == {}
        assert registry.task_groups == {}
        assert hasattr(registry, 'logger')

    def test_register_task_basic(self, task_registry, sample_task_config):
        """Test basic task registration."""
        task_id = task_registry.register_task(sample_task_config)
        
        assert task_id == sample_task_config["task_id"]
        assert task_id in task_registry.tasks
        assert task_registry.tasks[task_id]["task_id"] == task_id

    def test_register_task_with_validation(self, task_registry):
        """Test task registration with validation."""
        valid_config = {
            "task_id": "valid_task",
            "task_type": "single_turn",
            "description": "Valid test task",
            "dataset_path": "test_data.jsonl",
            "metrics": ["accuracy"]
        }
        
        task_id = task_registry.register_task(valid_config)
        assert task_id == "valid_task"

    def test_register_task_invalid_config(self, task_registry):
        """Test task registration with invalid config."""
        invalid_configs = [
            {},  # Empty config
            {"task_id": "test"},  # Missing required fields
            {"task_type": "invalid_type"},  # Invalid task type
            {"task_id": "", "task_type": "single_turn"}  # Empty task_id
        ]
        
        for config in invalid_configs:
            with pytest.raises(ValueError):
                task_registry.register_task(config)

    def test_register_duplicate_task(self, task_registry, sample_task_config):
        """Test registering duplicate task."""
        # Register task first time
        task_registry.register_task(sample_task_config)
        
        # Try to register same task again
        with pytest.raises(ValueError, match="Task .* already registered"):
            task_registry.register_task(sample_task_config)

    def test_unregister_task(self, task_registry, sample_task_config):
        """Test task unregistration."""
        task_id = task_registry.register_task(sample_task_config)
        
        # Verify task is registered
        assert task_id in task_registry.tasks
        
        # Unregister task
        result = task_registry.unregister_task(task_id)
        
        assert result is True
        assert task_id not in task_registry.tasks

    def test_unregister_nonexistent_task(self, task_registry):
        """Test unregistering non-existent task."""
        result = task_registry.unregister_task("nonexistent_task")
        assert result is False

    def test_get_task(self, task_registry, sample_task_config):
        """Test getting task configuration."""
        task_id = task_registry.register_task(sample_task_config)
        
        retrieved_task = task_registry.get_task(task_id)
        
        assert retrieved_task is not None
        assert retrieved_task["task_id"] == task_id
        assert retrieved_task["task_type"] == sample_task_config["task_type"]

    def test_get_nonexistent_task(self, task_registry):
        """Test getting non-existent task."""
        task = task_registry.get_task("nonexistent_task")
        assert task is None

    def test_list_tasks(self, task_registry, sample_task_config):
        """Test listing all tasks."""
        # Register multiple tasks
        task_configs = [
            {**sample_task_config, "task_id": f"test_task_{i}"}
            for i in range(3)
        ]
        
        for config in task_configs:
            task_registry.register_task(config)
        
        tasks = task_registry.list_tasks()
        
        assert len(tasks) >= 3
        task_ids = [task["task_id"] for task in tasks]
        assert all(f"test_task_{i}" in task_ids for i in range(3))

    def test_filter_tasks_by_type(self, task_registry):
        """Test filtering tasks by type."""
        # Register tasks of different types
        single_turn_config = {
            "task_id": "single_turn_task",
            "task_type": "single_turn",
            "description": "Single turn task",
            "dataset_path": "data.jsonl",
            "metrics": ["accuracy"]
        }
        
        multi_turn_config = {
            "task_id": "multi_turn_task", 
            "task_type": "multi_turn",
            "description": "Multi turn task",
            "dataset_path": "data.jsonl",
            "metrics": ["coherence"]
        }
        
        task_registry.register_task(single_turn_config)
        task_registry.register_task(multi_turn_config)
        
        # Filter by single_turn
        single_turn_tasks = task_registry.filter_tasks({"task_type": "single_turn"})
        assert len(single_turn_tasks) >= 1
        assert all(task["task_type"] == "single_turn" for task in single_turn_tasks)
        
        # Filter by multi_turn
        multi_turn_tasks = task_registry.filter_tasks({"task_type": "multi_turn"})
        assert len(multi_turn_tasks) >= 1
        assert all(task["task_type"] == "multi_turn" for task in multi_turn_tasks)

    def test_filter_tasks_by_metrics(self, task_registry):
        """Test filtering tasks by metrics."""
        configs = [
            {
                "task_id": "accuracy_task",
                "task_type": "single_turn",
                "description": "Task with accuracy metric",
                "dataset_path": "data.jsonl",
                "metrics": ["accuracy"]
            },
            {
                "task_id": "bleu_task",
                "task_type": "single_turn", 
                "description": "Task with BLEU metric",
                "dataset_path": "data.jsonl",
                "metrics": ["bleu"]
            },
            {
                "task_id": "multi_metric_task",
                "task_type": "single_turn",
                "description": "Task with multiple metrics",
                "dataset_path": "data.jsonl",
                "metrics": ["accuracy", "bleu"]
            }
        ]
        
        for config in configs:
            task_registry.register_task(config)
        
        # Filter by accuracy metric
        accuracy_tasks = task_registry.filter_tasks({"metrics": "accuracy"})
        assert len(accuracy_tasks) >= 2  # accuracy_task and multi_metric_task

    def test_task_groups(self, task_registry):
        """Test task group functionality."""
        # Register tasks with groups
        configs = [
            {
                "task_id": "coding_task_1",
                "task_type": "single_turn",
                "description": "Coding task 1",
                "dataset_path": "data.jsonl",
                "metrics": ["accuracy"],
                "group": "coding"
            },
            {
                "task_id": "coding_task_2",
                "task_type": "single_turn",
                "description": "Coding task 2", 
                "dataset_path": "data.jsonl",
                "metrics": ["accuracy"],
                "group": "coding"
            },
            {
                "task_id": "math_task_1",
                "task_type": "single_turn",
                "description": "Math task 1",
                "dataset_path": "data.jsonl", 
                "metrics": ["accuracy"],
                "group": "math"
            }
        ]
        
        for config in configs:
            task_registry.register_task(config)
        
        # Get tasks by group
        coding_tasks = task_registry.get_tasks_by_group("coding")
        assert len(coding_tasks) == 2
        assert all("coding_task" in task["task_id"] for task in coding_tasks)
        
        math_tasks = task_registry.get_tasks_by_group("math")
        assert len(math_tasks) == 1
        assert math_tasks[0]["task_id"] == "math_task_1"

    def test_task_dependencies(self, task_registry):
        """Test task dependency handling."""
        # Register tasks with dependencies
        base_task_config = {
            "task_id": "base_task",
            "task_type": "single_turn",
            "description": "Base task",
            "dataset_path": "data.jsonl",
            "metrics": ["accuracy"]
        }
        
        dependent_task_config = {
            "task_id": "dependent_task",
            "task_type": "single_turn",
            "description": "Dependent task",
            "dataset_path": "data.jsonl",
            "metrics": ["accuracy"],
            "dependencies": ["base_task"]
        }
        
        # Register base task first
        task_registry.register_task(base_task_config)
        
        # Register dependent task
        task_registry.register_task(dependent_task_config)
        
        # Verify dependency is recorded
        dependent_task = task_registry.get_task("dependent_task")
        assert "dependencies" in dependent_task
        assert "base_task" in dependent_task["dependencies"]

    def test_task_dependency_validation(self, task_registry):
        """Test task dependency validation."""
        dependent_task_config = {
            "task_id": "dependent_task",
            "task_type": "single_turn",
            "description": "Dependent task",
            "dataset_path": "data.jsonl",
            "metrics": ["accuracy"],
            "dependencies": ["nonexistent_task"]
        }
        
        # Should raise error for missing dependency
        with pytest.raises(ValueError, match="Dependency .* not found"):
            task_registry.register_task(dependent_task_config)

    def test_circular_dependency_detection(self, task_registry):
        """Test circular dependency detection."""
        task_a_config = {
            "task_id": "task_a",
            "task_type": "single_turn",
            "description": "Task A",
            "dataset_path": "data.jsonl",
            "metrics": ["accuracy"],
            "dependencies": ["task_b"]
        }
        
        task_b_config = {
            "task_id": "task_b",
            "task_type": "single_turn",
            "description": "Task B",
            "dataset_path": "data.jsonl",
            "metrics": ["accuracy"],
            "dependencies": ["task_a"]
        }
        
        # Register first task
        task_registry.register_task({**task_a_config, "dependencies": []})
        
        # Try to create circular dependency
        with pytest.raises(ValueError, match="Circular dependency detected"):
            task_registry.register_task(task_b_config)
            task_registry.update_task("task_a", {"dependencies": ["task_b"]})

    def test_task_validation_schema(self, task_registry):
        """Test task validation against schema."""
        # Valid task should pass
        valid_task = {
            "task_id": "valid_task",
            "task_type": "single_turn",
            "description": "Valid task",
            "dataset_path": "data.jsonl",
            "metrics": ["accuracy"],
            "timeout": 300,
            "max_retries": 3
        }
        
        is_valid, errors = task_registry.validate_task_config(valid_task)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid task should fail
        invalid_task = {
            "task_id": "",  # Empty task_id
            "task_type": "invalid_type",  # Invalid type
            "metrics": "not_a_list",  # Should be list
            "timeout": -1  # Invalid timeout
        }
        
        is_valid, errors = task_registry.validate_task_config(invalid_task)
        assert is_valid is False
        assert len(errors) > 0

    def test_task_metadata(self, task_registry):
        """Test task metadata handling."""
        task_config = {
            "task_id": "metadata_task",
            "task_type": "single_turn",
            "description": "Task with metadata",
            "dataset_path": "data.jsonl",
            "metrics": ["accuracy"],
            "metadata": {
                "author": "test_author",
                "version": "1.0.0",
                "tags": ["coding", "python"],
                "difficulty": "medium"
            }
        }
        
        task_id = task_registry.register_task(task_config)
        retrieved_task = task_registry.get_task(task_id)
        
        assert "metadata" in retrieved_task
        assert retrieved_task["metadata"]["author"] == "test_author"
        assert retrieved_task["metadata"]["version"] == "1.0.0"
        assert "coding" in retrieved_task["metadata"]["tags"]

    def test_task_update(self, task_registry, sample_task_config):
        """Test task configuration update."""
        task_id = task_registry.register_task(sample_task_config)
        
        # Update task
        updates = {
            "description": "Updated description",
            "timeout": 600,
            "metrics": ["accuracy", "bleu"]
        }
        
        result = task_registry.update_task(task_id, updates)
        assert result is True
        
        # Verify updates
        updated_task = task_registry.get_task(task_id)
        assert updated_task["description"] == "Updated description"
        assert updated_task["timeout"] == 600
        assert "bleu" in updated_task["metrics"]

    def test_task_export_import(self, task_registry, sample_task_config, temp_dir):
        """Test task export and import functionality."""
        # Register some tasks
        task_configs = [
            {**sample_task_config, "task_id": f"export_task_{i}"}
            for i in range(3)
        ]
        
        for config in task_configs:
            task_registry.register_task(config)
        
        # Export tasks
        export_file = temp_dir / "exported_tasks.json"
        task_registry.export_tasks(str(export_file))
        
        assert export_file.exists()
        
        # Create new registry and import
        new_registry = TaskRegistry()
        new_registry.import_tasks(str(export_file))
        
        # Verify imported tasks
        imported_tasks = new_registry.list_tasks()
        assert len(imported_tasks) >= 3
        
        original_task_ids = {task["task_id"] for task in task_registry.list_tasks()}
        imported_task_ids = {task["task_id"] for task in imported_tasks}
        
        assert original_task_ids.issubset(imported_task_ids)

    def test_task_search(self, task_registry):
        """Test task search functionality."""
        # Register tasks with searchable content
        search_configs = [
            {
                "task_id": "python_coding_task",
                "task_type": "single_turn",
                "description": "Python coding challenge",
                "dataset_path": "data.jsonl",
                "metrics": ["accuracy"],
                "metadata": {"language": "python", "tags": ["coding"]}
            },
            {
                "task_id": "javascript_task",
                "task_type": "single_turn",
                "description": "JavaScript programming task",
                "dataset_path": "data.jsonl",
                "metrics": ["accuracy"],
                "metadata": {"language": "javascript", "tags": ["coding"]}
            },
            {
                "task_id": "math_problem",
                "task_type": "single_turn",
                "description": "Mathematical problem solving",
                "dataset_path": "data.jsonl",
                "metrics": ["accuracy"],
                "metadata": {"subject": "mathematics", "tags": ["math"]}
            }
        ]
        
        for config in search_configs:
            task_registry.register_task(config)
        
        # Search by description
        python_tasks = task_registry.search_tasks("python")
        assert len(python_tasks) >= 1
        assert any("python" in task["description"].lower() for task in python_tasks)
        
        # Search by metadata
        coding_tasks = task_registry.search_tasks("coding")
        assert len(coding_tasks) >= 2
        
        # Search by task_id
        js_tasks = task_registry.search_tasks("javascript")
        assert len(js_tasks) >= 1

    def test_task_statistics(self, task_registry):
        """Test task statistics functionality."""
        # Register various tasks
        task_types = ["single_turn", "multi_turn", "single_turn", "multi_turn", "single_turn"]
        
        for i, task_type in enumerate(task_types):
            config = {
                "task_id": f"stats_task_{i}",
                "task_type": task_type,
                "description": f"Task {i}",
                "dataset_path": "data.jsonl",
                "metrics": ["accuracy"]
            }
            task_registry.register_task(config)
        
        stats = task_registry.get_statistics()
        
        assert "total_tasks" in stats
        assert "task_types" in stats
        assert stats["total_tasks"] >= 5
        assert stats["task_types"]["single_turn"] >= 3
        assert stats["task_types"]["multi_turn"] >= 2