"""
Tests for export engine functionality.

This module contains comprehensive tests for the export engine including
multiple format support, template application, and baseline configurations.
"""

import pytest
import os
import json
import csv
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from enum import Enum
import uuid

from EvaluationEngineV1_0.core.export_engine import (
    ExportEngine, ExportFormat, ExportConfiguration, ExportTemplate,
    BaselineConfiguration, CSVExportHandler, JSONExportHandler,
    ExcelExportHandler, PDFExportHandler, export_results, export_with_baseline,
    get_export_engine
)
from EvaluationEngineV1_0.core.data_models import (
    EvaluationResult, AggregatedMetrics, StandardizedOutput, TurnResult,
    TerminationReason
)
from EvaluationEngineV1_0.core.exceptions import ConfigurationError, ValidationError


class TestExportTemplate:
    """Test ExportTemplate functionality."""
    
    def test_template_creation(self):
        """Test basic template creation."""
        template = ExportTemplate(
            name="test_template",
            description="Test template",
            fields=["field1", "field2", "field3"]
        )
        
        assert template.name == "test_template"
        assert template.description == "Test template"
        assert template.fields == ["field1", "field2", "field3"]
        assert isinstance(template.field_mappings, dict)
        assert isinstance(template.filters, dict)
        assert isinstance(template.sorting, list)
        assert isinstance(template.grouping, list)
        assert isinstance(template.aggregations, dict)
        assert isinstance(template.formatting, dict)
    
    def test_template_with_all_options(self):
        """Test template creation with all options."""
        template = ExportTemplate(
            name="full_template",
            description="Full template with all options",
            fields=["task_id", "success", "duration"],
            field_mappings={"duration": "wall_time_s"},
            filters={"success": True},
            sorting=[{"field": "duration", "order": "asc"}],
            grouping=["success"],
            aggregations={"duration": "mean"},
            formatting={"duration": {"decimals": 2}}
        )
        
        assert template.field_mappings == {"duration": "wall_time_s"}
        assert template.filters == {"success": True}
        assert template.sorting == [{"field": "duration", "order": "asc"}]
        assert template.grouping == ["success"]
        assert template.aggregations == {"duration": "mean"}
        assert template.formatting == {"duration": {"decimals": 2}}


class TestExportConfiguration:
    """Test ExportConfiguration functionality."""
    
    def test_basic_configuration(self):
        """Test basic configuration creation."""
        config = ExportConfiguration(format=ExportFormat.CSV)
        
        assert config.format == ExportFormat.CSV
        assert config.template is None
        assert config.output_path is None
        assert config.include_metadata is True
        assert config.include_raw_data is False
        assert config.compression is False
        assert config.encoding == "utf-8"
    
    def test_full_configuration(self):
        """Test configuration with all options."""
        template = ExportTemplate(
            name="test_template",
            description="Test template",
            fields=["field1", "field2"]
        )
        
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            template=template,
            output_path="/tmp/test.json",
            include_metadata=False,
            include_raw_data=True,
            compression=True,
            encoding="utf-16"
        )
        
        assert config.format == ExportFormat.JSON
        assert config.template == template
        assert config.output_path == "/tmp/test.json"
        assert config.include_metadata is False
        assert config.include_raw_data is True
        assert config.compression is True
        assert config.encoding == "utf-16"


class TestCSVExportHandler:
    """Test CSV export handler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = CSVExportHandler()
        self.test_data = [
            {"task_id": "task1", "success": True, "duration": 10.5},
            {"task_id": "task2", "success": False, "duration": 15.2},
            {"task_id": "task3", "success": True, "duration": 8.7}
        ]
    
    def test_can_handle_csv(self):
        """Test CSV format detection."""
        assert self.handler.can_handle(ExportFormat.CSV) is True
        assert self.handler.can_handle(ExportFormat.JSON) is False
        assert self.handler.can_handle(ExportFormat.PDF) is False
    
    def test_basic_csv_export(self):
        """Test basic CSV export without template."""
        config = ExportConfiguration(format=ExportFormat.CSV)
        output_path = self.handler.export(self.test_data, config)
        
        assert os.path.exists(output_path)
        assert output_path.endswith('.csv')
        
        # Verify CSV content
        with open(output_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            assert len(rows) == 3
            assert rows[0]['task_id'] == 'task1'
            assert rows[0]['success'] == 'True'
            assert rows[0]['duration'] == '10.5'
        
        # Cleanup
        os.unlink(output_path)
    
    def test_csv_export_with_template(self):
        """Test CSV export with template filtering."""
        template = ExportTemplate(
            name="test_template",
            description="Test template",
            fields=["task_id", "success"],
            filters={"success": True}
        )
        
        config = ExportConfiguration(
            format=ExportFormat.CSV,
            template=template
        )
        
        output_path = self.handler.export(self.test_data, config)
        
        assert os.path.exists(output_path)
        
        # Verify filtered content
        with open(output_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            assert len(rows) == 2  # Only successful tasks
            assert all(row['success'] == 'True' for row in rows)
            assert 'duration' not in rows[0]  # Field not in template
        
        # Cleanup
        os.unlink(output_path)
    
    def test_csv_export_with_field_mapping(self):
        """Test CSV export with field mapping."""
        template = ExportTemplate(
            name="test_template",
            description="Test template",
            fields=["task_id", "success", "duration"],
            field_mappings={"duration": "wall_time_s"}
        )
        
        config = ExportConfiguration(
            format=ExportFormat.CSV,
            template=template
        )
        
        output_path = self.handler.export(self.test_data, config)
        
        assert os.path.exists(output_path)
        
        # Verify field mapping
        with open(output_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            assert 'wall_time_s' in rows[0]
            assert 'duration' not in rows[0]
            assert rows[0]['wall_time_s'] == '10.5'
        
        # Cleanup
        os.unlink(output_path)
    
    def test_csv_export_with_sorting(self):
        """Test CSV export with sorting."""
        template = ExportTemplate(
            name="test_template",
            description="Test template",
            fields=["task_id", "success", "duration"],
            sorting=[{"field": "duration", "order": "asc"}]
        )
        
        config = ExportConfiguration(
            format=ExportFormat.CSV,
            template=template
        )
        
        output_path = self.handler.export(self.test_data, config)
        
        assert os.path.exists(output_path)
        
        # Verify sorting
        with open(output_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            durations = [float(row['duration']) for row in rows]
            assert durations == sorted(durations)  # Should be sorted ascending
        
        # Cleanup
        os.unlink(output_path)
    
    def test_csv_export_empty_data(self):
        """Test CSV export with empty data."""
        config = ExportConfiguration(format=ExportFormat.CSV)
        
        with pytest.raises(ValidationError, match="No data to export"):
            self.handler.export([], config)


class TestJSONExportHandler:
    """Test JSON export handler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = JSONExportHandler()
        self.test_data = [
            {"task_id": "task1", "success": True, "duration": 10.5},
            {"task_id": "task2", "success": False, "duration": 15.2}
        ]
    
    def test_can_handle_json(self):
        """Test JSON format detection."""
        assert self.handler.can_handle(ExportFormat.JSON) is True
        assert self.handler.can_handle(ExportFormat.CSV) is False
    
    def test_basic_json_export(self):
        """Test basic JSON export."""
        config = ExportConfiguration(format=ExportFormat.JSON)
        output_path = self.handler.export(self.test_data, config)
        
        assert os.path.exists(output_path)
        assert output_path.endswith('.json')
        
        # Verify JSON content
        with open(output_path, 'r') as jsonfile:
            data = json.load(jsonfile)
            
            assert 'metadata' in data
            assert 'results' in data
            assert data['metadata']['record_count'] == 2
            assert len(data['results']) == 2
            assert data['results'][0]['task_id'] == 'task1'
        
        # Cleanup
        os.unlink(output_path)
    
    def test_json_export_with_template(self):
        """Test JSON export with template."""
        template = ExportTemplate(
            name="test_template",
            description="Test template",
            fields=["task_id", "success"]
        )
        
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            template=template,
            include_metadata=True
        )
        
        output_path = self.handler.export(self.test_data, config)
        
        assert os.path.exists(output_path)
        
        # Verify template application
        with open(output_path, 'r') as jsonfile:
            data = json.load(jsonfile)
            
            assert data['metadata']['template']['name'] == 'test_template'
            assert 'duration' not in data['results'][0]  # Filtered out
            assert 'task_id' in data['results'][0]
            assert 'success' in data['results'][0]
        
        # Cleanup
        os.unlink(output_path)


class TestExportEngine:
    """Test ExportEngine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ExportEngine()
        self.test_results = [
            StandardizedOutput(
                run_id="run1",
                task_id="task1",
                sample_id="sample1",
                success=True,
                turns=3,
                steps=5,
                wall_time_s=10.5,
                token_in=50,
                token_out=75,
                cost_usd=0.05,
                files_touched=2,
                edit_added=10,
                edit_deleted=5,
                redundancy_rate=0.1,
                recovered=False,
                safety_incidents=0
            ),
            StandardizedOutput(
                run_id="run1",
                task_id="task2",
                sample_id="sample2",
                success=False,
                turns=5,
                steps=8,
                wall_time_s=20.3,
                token_in=100,
                token_out=150,
                cost_usd=0.12,
                files_touched=3,
                edit_added=15,
                edit_deleted=8,
                redundancy_rate=0.2,
                recovered=True,
                safety_incidents=1
            )
        ]
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        assert len(self.engine._handlers) == 4  # CSV, JSON, Excel, PDF
        assert len(self.engine._templates) == 4  # standard, summary, performance, safety
        assert len(self.engine._baseline_configs) == 3  # regression, mid_fidelity, milestone
    
    def test_register_template(self):
        """Test template registration."""
        template = ExportTemplate(
            name="custom_template",
            description="Custom test template",
            fields=["task_id", "success"]
        )
        
        initial_count = len(self.engine._templates)
        self.engine.register_template(template)
        
        assert len(self.engine._templates) == initial_count + 1
        assert self.engine.get_template("custom_template") == template
    
    def test_list_templates(self):
        """Test template listing."""
        templates = self.engine.list_templates()
        
        assert isinstance(templates, list)
        assert "standard" in templates
        assert "summary" in templates
        assert "performance" in templates
        assert "safety" in templates
    
    def test_list_supported_formats(self):
        """Test supported format listing."""
        formats = self.engine.list_supported_formats()
        
        assert ExportFormat.CSV in formats
        assert ExportFormat.JSON in formats
        # Excel and PDF may not be available depending on dependencies
    
    def test_export_results_csv(self):
        """Test exporting results to CSV."""
        config = ExportConfiguration(format=ExportFormat.CSV)
        output_path = self.engine.export_results(self.test_results, config)
        
        assert os.path.exists(output_path)
        assert output_path.endswith('.csv')
        
        # Verify content
        with open(output_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            assert len(rows) == 2
            assert rows[0]['task_id'] == 'task1'
            assert rows[0]['success'] == 'True'
            assert rows[1]['task_id'] == 'task2'
            assert rows[1]['success'] == 'False'
        
        # Cleanup
        os.unlink(output_path)
    
    def test_export_results_json(self):
        """Test exporting results to JSON."""
        config = ExportConfiguration(format=ExportFormat.JSON)
        output_path = self.engine.export_results(self.test_results, config)
        
        assert os.path.exists(output_path)
        assert output_path.endswith('.json')
        
        # Verify content
        with open(output_path, 'r') as jsonfile:
            data = json.load(jsonfile)
            
            assert data['metadata']['record_count'] == 2
            assert len(data['results']) == 2
            assert data['results'][0]['task_id'] == 'task1'
        
        # Cleanup
        os.unlink(output_path)
    
    def test_export_with_template(self):
        """Test exporting with template."""
        template = self.engine.get_template("summary")
        config = ExportConfiguration(
            format=ExportFormat.CSV,
            template=template
        )
        
        output_path = self.engine.export_results(self.test_results, config)
        
        assert os.path.exists(output_path)
        
        # Verify template application
        with open(output_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            # Summary template should have limited fields
            expected_fields = {"task_id", "success", "turns", "duration_seconds", "cost_dollars", "safety_incidents"}
            actual_fields = set(rows[0].keys())
            
            # Check that template fields are present (allowing for field mappings)
            assert "task_id" in actual_fields
            assert "success" in actual_fields
            assert "turns" in actual_fields
        
        # Cleanup
        os.unlink(output_path)
    
    def test_export_with_baseline_regression(self):
        """Test exporting with regression baseline."""
        output_path = self.engine.export_with_baseline(
            self.test_results,
            BaselineConfiguration.REGRESSION,
            ExportFormat.CSV
        )
        
        assert os.path.exists(output_path)
        
        # Verify baseline fields
        with open(output_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            # Regression baseline should have minimal fields
            expected_fields = {"task_id", "success", "turns", "wall_time_s"}
            actual_fields = set(rows[0].keys())
            
            assert expected_fields.issubset(actual_fields)
        
        # Cleanup
        os.unlink(output_path)
    
    def test_export_with_baseline_milestone(self):
        """Test exporting with milestone baseline."""
        output_path = self.engine.export_with_baseline(
            self.test_results,
            BaselineConfiguration.MILESTONE,
            ExportFormat.JSON
        )
        
        assert os.path.exists(output_path)
        
        # Verify comprehensive fields
        with open(output_path, 'r') as jsonfile:
            data = json.load(jsonfile)
            
            result = data['results'][0]
            # Milestone baseline should have all fields
            assert 'run_id' in result
            assert 'task_id' in result
            assert 'sample_id' in result
            assert 'success' in result
            assert 'turns' in result
            assert 'steps' in result
            assert 'wall_time_s' in result
            assert 'cost_usd' in result
            assert 'safety_incidents' in result
        
        # Cleanup
        os.unlink(output_path)
    
    def test_export_mixed_result_types(self):
        """Test exporting mixed result types."""
        # Create mixed results
        evaluation_result = EvaluationResult(
            evaluation_id="eval1",
            task_id="task3",
            model_id="model1",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=30),
            success=True,
            total_turns=2,
            turn_results=[
                TurnResult(
                    turn=1,
                    action="action1",
                    observation="obs1",
                    reward=0.5,
                    done=False,
                    info={},
                    execution_time=15.0
                ),
                TurnResult(
                    turn=2,
                    action="action2",
                    observation="obs2",
                    reward=1.0,
                    done=True,
                    info={},
                    execution_time=15.0
                )
            ],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS
        )
        
        dict_result = {
            "task_id": "task4",
            "success": False,
            "turns": 1,
            "wall_time_s": 25.0  # Use standardized field name
        }
        
        mixed_results = [
            self.test_results[0],  # StandardizedOutput
            evaluation_result,     # EvaluationResult
            dict_result           # Dictionary
        ]
        
        config = ExportConfiguration(format=ExportFormat.CSV)
        output_path = self.engine.export_results(mixed_results, config)
        
        assert os.path.exists(output_path)
        
        # Verify all results were processed
        with open(output_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            
            assert len(rows) == 3
            task_ids = [row['task_id'] for row in rows]
            assert 'task1' in task_ids
            assert 'task3' in task_ids
            assert 'task4' in task_ids
        
        # Cleanup
        os.unlink(output_path)
    
    def test_export_empty_results(self):
        """Test exporting empty results."""
        config = ExportConfiguration(format=ExportFormat.CSV)
        
        with pytest.raises(ValidationError, match="No results to export"):
            self.engine.export_results([], config)
    
    def test_export_unsupported_format(self):
        """Test exporting with unsupported format."""
        # Create a mock unsupported format
        class UnsupportedFormat(Enum):
            UNSUPPORTED = "unsupported"
        
        # This should raise an error since we can't create ExportFormat with unsupported value
        # Instead, test with a format that has no handler
        engine = ExportEngine()
        engine._handlers = []  # Remove all handlers
        
        config = ExportConfiguration(format=ExportFormat.CSV)
        
        with pytest.raises(ConfigurationError, match="No handler available"):
            engine.export_results(self.test_results, config)
    
    def test_get_export_statistics(self):
        """Test export statistics."""
        stats = self.engine.get_export_statistics()
        
        assert "registered_handlers" in stats
        assert "handler_types" in stats
        assert "registered_templates" in stats
        assert "template_names" in stats
        assert "supported_formats" in stats
        assert "baseline_configurations" in stats
        
        assert stats["registered_handlers"] == 4
        assert len(stats["handler_types"]) == 4
        assert stats["registered_templates"] == 4
        assert len(stats["template_names"]) == 4


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_results = [
            {"task_id": "task1", "success": True, "turns": 2},
            {"task_id": "task2", "success": False, "turns": 3}
        ]
    
    def test_get_export_engine(self):
        """Test global export engine access."""
        engine = get_export_engine()
        assert isinstance(engine, ExportEngine)
        
        # Should return the same instance
        engine2 = get_export_engine()
        assert engine is engine2
    
    def test_export_results_convenience(self):
        """Test convenience function for exporting results."""
        output_path = export_results(
            self.test_results,
            ExportFormat.CSV,
            template_name="summary"
        )
        
        assert os.path.exists(output_path)
        assert output_path.endswith('.csv')
        
        # Cleanup
        os.unlink(output_path)
    
    def test_export_with_baseline_convenience(self):
        """Test convenience function for baseline export."""
        output_path = export_with_baseline(
            self.test_results,
            BaselineConfiguration.REGRESSION,
            ExportFormat.JSON
        )
        
        assert os.path.exists(output_path)
        assert output_path.endswith('.json')
        
        # Cleanup
        os.unlink(output_path)
    
    def test_export_results_invalid_template(self):
        """Test convenience function with invalid template."""
        with pytest.raises(ConfigurationError, match="Template not found"):
            export_results(
                self.test_results,
                ExportFormat.CSV,
                template_name="nonexistent_template"
            )


class TestBaselineConfigurations:
    """Test predefined baseline configurations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ExportEngine()
    
    def test_regression_baseline(self):
        """Test regression baseline configuration."""
        template = self.engine.get_baseline_template(BaselineConfiguration.REGRESSION)
        
        assert template.name == "regression_baseline"
        assert "task_id" in template.fields
        assert "success" in template.fields
        assert "turns" in template.fields
        assert "wall_time_s" in template.fields
        assert len(template.fields) == 4  # Minimal fields
    
    def test_mid_fidelity_baseline(self):
        """Test mid-fidelity baseline configuration."""
        template = self.engine.get_baseline_template(BaselineConfiguration.MID_FIDELITY)
        
        assert template.name == "mid_fidelity_baseline"
        assert "task_id" in template.fields
        assert "success" in template.fields
        assert "cost_usd" in template.fields
        assert "safety_incidents" in template.fields
        assert len(template.fields) == 8  # Balanced fields
    
    def test_milestone_baseline(self):
        """Test milestone baseline configuration."""
        template = self.engine.get_baseline_template(BaselineConfiguration.MILESTONE)
        
        assert template.name == "milestone_baseline"
        assert "run_id" in template.fields
        assert "task_id" in template.fields
        assert "sample_id" in template.fields
        assert "success" in template.fields
        assert "timestamp" in template.fields
        assert len(template.fields) == 18  # Comprehensive fields


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_missing_dependencies_excel(self):
        """Test Excel export with missing dependencies."""
        handler = ExcelExportHandler()
        
        # Mock missing pandas
        original_validate = handler.validate_dependencies
        handler.validate_dependencies = lambda: False
        
        config = ExportConfiguration(format=ExportFormat.EXCEL)
        test_data = [{"task_id": "task1", "success": True}]
        
        with pytest.raises(ConfigurationError, match="pandas is required"):
            handler.export(test_data, config)
        
        # Restore original method
        handler.validate_dependencies = original_validate
    
    def test_missing_dependencies_pdf(self):
        """Test PDF export with missing dependencies."""
        handler = PDFExportHandler()
        
        # Mock missing reportlab
        original_validate = handler.validate_dependencies
        handler.validate_dependencies = lambda: False
        
        config = ExportConfiguration(format=ExportFormat.PDF)
        test_data = [{"task_id": "task1", "success": True}]
        
        with pytest.raises(ConfigurationError, match="reportlab is required"):
            handler.export(test_data, config)
        
        # Restore original method
        handler.validate_dependencies = original_validate


if __name__ == "__main__":
    pytest.main([__file__])