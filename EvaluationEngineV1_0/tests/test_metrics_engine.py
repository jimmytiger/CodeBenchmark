"""
Unit tests for the core metrics engine.

Tests all metric calculations for accuracy and edge cases as specified
in requirements 4.1-4.6.
"""

import pytest
import math
from datetime import datetime, timedelta
from typing import List
from unittest.mock import Mock, patch

from EvaluationEngineV1_0.core.metrics_engine import MetricsEngine, MetricCalculationResult
from EvaluationEngineV1_0.core.data_models import (
    EvaluationResult, TurnResult, AggregatedMetrics, 
    TerminationReason, StandardizedOutput
)


class TestMetricsEngine:
    """Test suite for MetricsEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics_engine = MetricsEngine()
        
        # Create sample evaluation results for testing
        self.sample_evaluation_results = self._create_sample_evaluation_results()
    
    def _create_sample_evaluation_results(self) -> list:
        """Create sample evaluation results for testing."""
        results = []
        
        # Successful evaluation with 3 turns
        successful_result = EvaluationResult(
            evaluation_id="eval_001",
            task_id="task_001",
            model_id="model_001",
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now(),
            success=True,
            total_turns=3,
            turn_results=[
                TurnResult(
                    turn=1,
                    action="action_1",
                    observation="obs_1",
                    reward=0.0,
                    done=False,
                    info={'files_changed': ['file1.py']},
                    execution_time=10.0,
                    tokens_used=100,
                    cost=0.01,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=2,
                    action="action_2",
                    observation="obs_2",
                    reward=0.5,
                    done=False,
                    info={'files_changed': ['file1.py', 'file2.py']},
                    execution_time=15.0,
                    tokens_used=150,
                    cost=0.015,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=3,
                    action="action_3",
                    observation="obs_3",
                    reward=1.0,
                    done=True,
                    info={'files_changed': ['file2.py']},
                    execution_time=12.0,
                    tokens_used=120,
                    cost=0.012,
                    safety_violations=[]
                )
            ],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS,
            metadata={}
        )
        results.append(successful_result)
        
        # Failed evaluation with 5 turns (max turns reached)
        failed_result = EvaluationResult(
            evaluation_id="eval_002",
            task_id="task_002",
            model_id="model_001",
            start_time=datetime.now() - timedelta(minutes=10),
            end_time=datetime.now() - timedelta(minutes=2),
            success=False,
            total_turns=5,
            turn_results=[
                TurnResult(
                    turn=1,
                    action="action_1",
                    observation="obs_1",
                    reward=-0.1,
                    done=False,
                    info={'error': 'syntax_error', 'files_changed': ['file3.py']},
                    execution_time=8.0,
                    tokens_used=80,
                    cost=0.008,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=2,
                    action="action_1",  # Repeated action
                    observation="obs_2",
                    reward=-0.1,
                    done=False,
                    info={'error': 'syntax_error', 'files_changed': ['file3.py']},
                    execution_time=8.0,
                    tokens_used=80,
                    cost=0.008,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=3,
                    action="action_2",
                    observation="obs_3",
                    reward=0.2,
                    done=False,
                    info={'files_changed': ['file3.py', 'file4.py']},
                    execution_time=12.0,
                    tokens_used=110,
                    cost=0.011,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=4,
                    action="action_3",
                    observation="obs_4",
                    reward=-0.2,
                    done=False,
                    info={'error': 'runtime_error', 'files_changed': ['file4.py']},
                    execution_time=10.0,
                    tokens_used=95,
                    cost=0.0095,
                    safety_violations=['unsafe_command']
                ),
                TurnResult(
                    turn=5,
                    action="action_4",
                    observation="obs_5",
                    reward=0.0,
                    done=False,
                    info={'files_changed': ['file4.py']},
                    execution_time=9.0,
                    tokens_used=90,
                    cost=0.009,
                    safety_violations=[]
                )
            ],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.MAX_TURNS,
            metadata={}
        )
        results.append(failed_result)
        
        # Safety violation evaluation
        safety_violation_result = EvaluationResult(
            evaluation_id="eval_003",
            task_id="task_003",
            model_id="model_001",
            start_time=datetime.now() - timedelta(minutes=3),
            end_time=datetime.now() - timedelta(minutes=1),
            success=False,
            total_turns=2,
            turn_results=[
                TurnResult(
                    turn=1,
                    action="action_1",
                    observation="obs_1",
                    reward=0.0,
                    done=False,
                    info={'files_changed': ['file5.py']},
                    execution_time=5.0,
                    tokens_used=50,
                    cost=0.005,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=2,
                    action="rm -rf /",
                    observation="obs_2",
                    reward=-1.0,
                    done=True,
                    info={'error': 'safety_violation'},
                    execution_time=1.0,
                    tokens_used=20,
                    cost=0.002,
                    safety_violations=['dangerous_command', 'file_system_violation']
                )
            ],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SAFETY_VIOLATION,
            metadata={}
        )
        results.append(safety_violation_result)
        
        return results
    
    def test_calculate_all_metrics_basic(self):
        """Test basic metrics calculation with sample data."""
        metrics = self.metrics_engine.calculate_all_metrics(self.sample_evaluation_results)
        
        assert isinstance(metrics, AggregatedMetrics)
        
        # Test Task Success Metrics (Requirements 4.1, 4.2)
        expected_resolved = (1 / 3) * 100.0  # 1 out of 3 successful
        assert abs(metrics.resolved_percentage - expected_resolved) < 0.01
        assert 0.0 <= metrics.recall <= 1.0
        assert 0.0 <= metrics.mrr <= 1.0
        
        # Test Efficiency Metrics (Requirements 4.2)
        assert metrics.avg_turns > 0.0
        assert metrics.avg_steps > 0.0
        assert 0.0 <= metrics.redundancy_rate <= 1.0
        
        # Test Repair Quality Metrics (Requirements 4.3)
        assert metrics.edit_churn >= 0.0
        assert metrics.files_touched >= 0
        
        # Test Robustness Metrics (Requirements 4.4)
        assert 0.0 <= metrics.recovery_rate <= 1.0
        assert 0.0 <= metrics.stability_score <= 1.0
        
        # Test Cost Metrics (Requirements 4.5)
        assert metrics.wall_time_per_solved >= 0.0
        assert metrics.tokens_per_solved >= 0
        assert metrics.cost_per_solved >= 0.0
        
        # Test Safety Metrics (Requirements 4.6)
        assert metrics.safety_incidents >= 0
        assert metrics.policy_violations >= 0
    
    def test_task_success_metrics_calculation(self):
        """Test task success metrics calculation accuracy."""
        # Test with only successful results
        successful_results = [r for r in self.sample_evaluation_results if r.success]
        metrics = self.metrics_engine._calculate_task_success_metrics(successful_results)
        
        assert metrics['resolved_percentage'] == 100.0
        assert metrics['recall'] == 1.0
        assert metrics['mrr'] > 0.0
        
        # Test with only failed results
        failed_results = [r for r in self.sample_evaluation_results if not r.success]
        metrics = self.metrics_engine._calculate_task_success_metrics(failed_results)
        
        assert metrics['resolved_percentage'] == 0.0
        assert metrics['recall'] == 0.0
        assert metrics['mrr'] == 0.0
        
        # Test with mixed results
        metrics = self.metrics_engine._calculate_task_success_metrics(self.sample_evaluation_results)
        
        expected_resolved = (1 / 3) * 100.0  # 1 successful out of 3
        assert abs(metrics['resolved_percentage'] - expected_resolved) < 0.01
        assert abs(metrics['recall'] - (expected_resolved / 100.0)) < 0.01
    
    def test_efficiency_metrics_calculation(self):
        """Test efficiency metrics calculation accuracy."""
        metrics = self.metrics_engine._calculate_efficiency_metrics(self.sample_evaluation_results)
        
        # Check average turns
        expected_avg_turns = (3 + 5 + 2) / 3  # Average of turn counts
        assert abs(metrics['avg_turns'] - expected_avg_turns) < 0.01
        
        # Check average steps (should equal average turns for our test data)
        assert metrics['avg_steps'] > 0.0
        
        # Check redundancy rate (should be > 0 due to repeated action in failed result)
        assert metrics['redundancy_rate'] > 0.0
    
    def test_repair_quality_metrics_calculation(self):
        """Test repair quality metrics calculation accuracy."""
        metrics = self.metrics_engine._calculate_repair_quality_metrics(self.sample_evaluation_results)
        
        # Check edit churn
        assert metrics['edit_churn'] >= 1.0  # Should be >= 1 due to file modifications
        
        # Check files touched
        assert metrics['files_touched'] > 0  # Should have touched some files
    
    def test_robustness_metrics_calculation(self):
        """Test robustness metrics calculation accuracy."""
        metrics = self.metrics_engine._calculate_robustness_metrics(self.sample_evaluation_results)
        
        # Check recovery rate
        assert 0.0 <= metrics['recovery_rate'] <= 1.0
        
        # Check stability score
        assert 0.0 <= metrics['stability_score'] <= 1.0
    
    def test_cost_metrics_calculation(self):
        """Test cost metrics calculation accuracy."""
        metrics = self.metrics_engine._calculate_cost_metrics(self.sample_evaluation_results)
        
        # Should only calculate for successful results
        assert metrics['wall_time_per_solved'] > 0.0
        assert metrics['tokens_per_solved'] > 0
        assert metrics['cost_per_solved'] > 0.0
    
    def test_safety_metrics_calculation(self):
        """Test safety metrics calculation accuracy."""
        metrics = self.metrics_engine._calculate_safety_metrics(self.sample_evaluation_results)
        
        # Should count safety violations from turn results
        assert metrics['safety_incidents'] >= 2  # At least 2 from safety violation result
        
        # Should count policy violations from termination reasons
        assert metrics['policy_violations'] >= 1  # At least 1 from safety violation termination
    
    def test_empty_evaluation_results(self):
        """Test metrics calculation with empty input."""
        metrics = self.metrics_engine.calculate_all_metrics([])
        
        assert isinstance(metrics, AggregatedMetrics)
        assert metrics.resolved_percentage == 0.0
        assert metrics.recall == 0.0
        assert metrics.mrr == 0.0
        assert metrics.avg_turns == 0.0
        assert metrics.avg_steps == 0.0
        assert metrics.redundancy_rate == 0.0
        assert metrics.edit_churn == 0.0
        assert metrics.files_touched == 0
        assert metrics.recovery_rate == 0.0
        assert metrics.stability_score == 0.0
        assert metrics.wall_time_per_solved == 0.0
        assert metrics.tokens_per_solved == 0
        assert metrics.cost_per_solved == 0.0
        assert metrics.safety_incidents == 0
        assert metrics.policy_violations == 0
    
    def test_single_evaluation_metrics(self):
        """Test metrics calculation for a single evaluation."""
        single_result = self.sample_evaluation_results[0]  # Successful result
        metrics = self.metrics_engine.calculate_single_evaluation_metrics(single_result)
        
        assert isinstance(metrics, AggregatedMetrics)
        assert metrics.resolved_percentage == 100.0  # Single successful result
        assert metrics.recall == 1.0
        assert abs(metrics.mrr - (1.0/3.0)) < 0.01  # Success on turn 3, so MRR = 1/3
    
    def test_find_success_turn(self):
        """Test finding the turn where success was achieved."""
        # Test successful turn sequence
        successful_turns = self.sample_evaluation_results[0].turn_results
        success_turn = self.metrics_engine._find_success_turn(successful_turns)
        assert success_turn == 3  # Success on turn 3
        
        # Test failed turn sequence
        failed_turns = self.sample_evaluation_results[1].turn_results
        success_turn = self.metrics_engine._find_success_turn(failed_turns)
        assert success_turn == 5  # No success, returns last turn
    
    def test_calculate_redundancy_rate(self):
        """Test redundancy rate calculation."""
        # Test with repeated actions
        failed_turns = self.sample_evaluation_results[1].turn_results
        redundancy_rate = self.metrics_engine._calculate_redundancy_rate(failed_turns)
        assert redundancy_rate > 0.0  # Should detect repeated "action_1"
        
        # Test with no repeated actions
        successful_turns = self.sample_evaluation_results[0].turn_results
        redundancy_rate = self.metrics_engine._calculate_redundancy_rate(successful_turns)
        assert redundancy_rate == 0.0  # No repeated actions
        
        # Test with empty turns
        redundancy_rate = self.metrics_engine._calculate_redundancy_rate([])
        assert redundancy_rate == 0.0
    
    def test_calculate_edit_churn(self):
        """Test edit churn calculation."""
        # Test with file modifications
        turns = self.sample_evaluation_results[0].turn_results
        edit_churn = self.metrics_engine._calculate_edit_churn(turns)
        assert edit_churn >= 1.0  # Should be >= 1 due to multiple modifications
        
        # Test with no file modifications
        empty_turns = [
            TurnResult(
                turn=1, action="action", observation="obs", reward=0.0,
                done=False, info={}, execution_time=1.0
            )
        ]
        edit_churn = self.metrics_engine._calculate_edit_churn(empty_turns)
        assert edit_churn == 0.0
    
    def test_count_files_touched(self):
        """Test counting unique files touched."""
        turns = self.sample_evaluation_results[0].turn_results
        files_count = self.metrics_engine._count_files_touched(turns)
        assert files_count == 2  # file1.py and file2.py
        
        # Test with no files
        empty_turns = [
            TurnResult(
                turn=1, action="action", observation="obs", reward=0.0,
                done=False, info={}, execution_time=1.0
            )
        ]
        files_count = self.metrics_engine._count_files_touched(empty_turns)
        assert files_count == 0
    
    def test_calculate_recovery_rate(self):
        """Test recovery rate calculation."""
        # Test with recovery (failed result has some recovery)
        failed_turns = self.sample_evaluation_results[1].turn_results
        recovery_rate = self.metrics_engine._calculate_recovery_rate(failed_turns)
        assert 0.0 <= recovery_rate <= 1.0
        
        # Test with no errors (should return 1.0)
        successful_turns = [
            TurnResult(
                turn=1, action="action", observation="obs", reward=1.0,
                done=False, info={}, execution_time=1.0
            )
        ]
        recovery_rate = self.metrics_engine._calculate_recovery_rate(successful_turns)
        assert recovery_rate == 1.0
    
    def test_calculate_stability_score(self):
        """Test stability score calculation."""
        # Test with varying rewards
        turns = self.sample_evaluation_results[1].turn_results
        stability_score = self.metrics_engine._calculate_stability_score(turns)
        assert 0.0 <= stability_score <= 1.0
        
        # Test with consistent rewards
        consistent_turns = [
            TurnResult(
                turn=1, action="action", observation="obs", reward=1.0,
                done=False, info={}, execution_time=1.0
            ),
            TurnResult(
                turn=2, action="action", observation="obs", reward=1.0,
                done=False, info={}, execution_time=1.0
            )
        ]
        stability_score = self.metrics_engine._calculate_stability_score(consistent_turns)
        assert stability_score == 1.0  # Perfect stability
        
        # Test with single turn
        single_turn = [consistent_turns[0]]
        stability_score = self.metrics_engine._calculate_stability_score(single_turn)
        assert stability_score == 1.0
    
    def test_get_metric_summary(self):
        """Test comprehensive metric summary generation."""
        summary = self.metrics_engine.get_metric_summary(self.sample_evaluation_results)
        
        assert 'total_evaluations' in summary
        assert 'successful_evaluations' in summary
        assert 'success_rate' in summary
        assert 'metrics' in summary
        assert 'performance_summary' in summary
        
        assert summary['total_evaluations'] == 3
        assert summary['successful_evaluations'] == 1
        assert abs(summary['success_rate'] - (1/3)) < 0.01
        
        # Check performance summary structure
        perf_summary = summary['performance_summary']
        assert 'task_success' in perf_summary
        assert 'efficiency' in perf_summary
        assert 'quality' in perf_summary
        assert 'robustness' in perf_summary
        assert 'cost' in perf_summary
        assert 'safety' in perf_summary
    
    def test_get_metric_summary_empty_input(self):
        """Test metric summary with empty input."""
        summary = self.metrics_engine.get_metric_summary([])
        assert 'error' in summary
        assert summary['error'] == 'No evaluation results provided'
    
    def test_calculation_history(self):
        """Test calculation history tracking."""
        initial_history_length = len(self.metrics_engine.get_calculation_history())
        
        # Perform a calculation
        self.metrics_engine.calculate_all_metrics(self.sample_evaluation_results)
        
        # Check history was updated
        history = self.metrics_engine.get_calculation_history()
        assert len(history) == initial_history_length + 1
        
        latest_entry = history[-1]
        assert 'timestamp' in latest_entry
        assert 'calculation_time' in latest_entry
        assert 'num_evaluations' in latest_entry
        assert 'metrics' in latest_entry
        assert latest_entry['num_evaluations'] == 3
    
    def test_cache_operations(self):
        """Test cache operations."""
        # Clear cache
        self.metrics_engine.clear_cache()
        assert len(self.metrics_engine.metric_cache) == 0
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test with evaluation result with no turn results
        empty_turn_result = EvaluationResult(
            evaluation_id="eval_empty",
            task_id="task_empty",
            model_id="model_001",
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=False,
            total_turns=0,
            turn_results=[],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.ERROR,
            metadata={}
        )
        
        metrics = self.metrics_engine.calculate_all_metrics([empty_turn_result])
        assert isinstance(metrics, AggregatedMetrics)
        
        # Test with None values in turn results
        turn_with_none = TurnResult(
            turn=1,
            action=None,
            observation=None,
            reward=0.0,
            done=False,
            info=None,
            execution_time=0.0
        )
        
        result_with_none = EvaluationResult(
            evaluation_id="eval_none",
            task_id="task_none",
            model_id="model_001",
            start_time=datetime.now(),
            end_time=datetime.now(),
            success=False,
            total_turns=1,
            turn_results=[turn_with_none],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.ERROR,
            metadata={}
        )
        
        metrics = self.metrics_engine.calculate_all_metrics([result_with_none])
        assert isinstance(metrics, AggregatedMetrics)
    
    def test_mrr_calculation_accuracy(self):
        """Test MRR calculation with specific scenarios."""
        # Create evaluation results with known success turns
        results = []
        
        # Success on turn 1 (MRR contribution: 1/1 = 1.0)
        result1 = self._create_test_result("eval1", success_turn=1, total_turns=1)
        results.append(result1)
        
        # Success on turn 2 (MRR contribution: 1/2 = 0.5)
        result2 = self._create_test_result("eval2", success_turn=2, total_turns=2)
        results.append(result2)
        
        # Success on turn 4 (MRR contribution: 1/4 = 0.25)
        result3 = self._create_test_result("eval3", success_turn=4, total_turns=4)
        results.append(result3)
        
        # No success (MRR contribution: 0.0)
        result4 = self._create_test_result("eval4", success_turn=None, total_turns=3)
        results.append(result4)
        
        metrics = self.metrics_engine._calculate_task_success_metrics(results)
        
        # Expected MRR: (1.0 + 0.5 + 0.25 + 0.0) / 4 = 0.4375
        expected_mrr = (1.0 + 0.5 + 0.25 + 0.0) / 4
        assert abs(metrics['mrr'] - expected_mrr) < 0.01
    
    def _create_test_result(self, eval_id: str, success_turn: int = None, total_turns: int = 3):
        """Helper to create test evaluation results."""
        turn_results = []
        
        for i in range(1, total_turns + 1):
            reward = 1.0 if (success_turn and i == success_turn) else 0.0
            done = success_turn and i == success_turn
            
            turn_results.append(TurnResult(
                turn=i,
                action=f"action_{i}",
                observation=f"obs_{i}",
                reward=reward,
                done=done,
                info={},
                execution_time=1.0,
                tokens_used=10,
                cost=0.001
            ))
        
        return EvaluationResult(
            evaluation_id=eval_id,
            task_id="test_task",
            model_id="test_model",
            start_time=datetime.now() - timedelta(minutes=total_turns),
            end_time=datetime.now(),
            success=success_turn is not None,
            total_turns=total_turns,
            turn_results=turn_results,
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS if success_turn else TerminationReason.MAX_TURNS,
            metadata={}
        )


class TestAdvancedMetrics:
    """Test suite for advanced metrics calculations."""
    
    def setup_method(self):
        """Set up test fixtures for advanced metrics."""
        self.metrics_engine = MetricsEngine()
        self.advanced_evaluation_results = self._create_advanced_test_data()
    
    def _create_advanced_test_data(self) -> list:
        """Create more complex evaluation results for advanced metrics testing."""
        results = []
        
        # Complex successful evaluation with multiple file modifications
        complex_successful = EvaluationResult(
            evaluation_id="adv_eval_001",
            task_id="complex_task_001",
            model_id="model_001",
            start_time=datetime.now() - timedelta(minutes=15),
            end_time=datetime.now() - timedelta(minutes=5),
            success=True,
            total_turns=6,
            turn_results=[
                TurnResult(
                    turn=1,
                    action="analyze_code",
                    observation="Found 3 issues",
                    reward=0.1,
                    done=False,
                    info={'files_changed': ['main.py'], 'error': None},
                    execution_time=20.0,
                    tokens_used=200,
                    cost=0.02,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=2,
                    action="fix_syntax_error",
                    observation="Fixed syntax",
                    reward=-0.1,
                    done=False,
                    info={'files_changed': ['main.py'], 'error': 'syntax_error'},
                    execution_time=15.0,
                    tokens_used=150,
                    cost=0.015,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=3,
                    action="fix_syntax_error_retry",
                    observation="Syntax fixed successfully",
                    reward=0.3,
                    done=False,
                    info={'files_changed': ['main.py'], 'error': None},
                    execution_time=18.0,
                    tokens_used=180,
                    cost=0.018,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=4,
                    action="add_tests",
                    observation="Added unit tests",
                    reward=0.2,
                    done=False,
                    info={'files_changed': ['test_main.py'], 'error': None},
                    execution_time=25.0,
                    tokens_used=250,
                    cost=0.025,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=5,
                    action="refactor_code",
                    observation="Refactored for better performance",
                    reward=0.4,
                    done=False,
                    info={'files_changed': ['main.py', 'utils.py'], 'error': None},
                    execution_time=30.0,
                    tokens_used=300,
                    cost=0.03,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=6,
                    action="final_validation",
                    observation="All tests pass",
                    reward=1.0,
                    done=True,
                    info={'files_changed': [], 'error': None},
                    execution_time=10.0,
                    tokens_used=100,
                    cost=0.01,
                    safety_violations=[]
                )
            ],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS,
            metadata={}
        )
        results.append(complex_successful)
        
        # Evaluation with multiple safety violations and recovery
        safety_heavy_evaluation = EvaluationResult(
            evaluation_id="adv_eval_002",
            task_id="safety_task_002",
            model_id="model_001",
            start_time=datetime.now() - timedelta(minutes=8),
            end_time=datetime.now() - timedelta(minutes=2),
            success=False,
            total_turns=4,
            turn_results=[
                TurnResult(
                    turn=1,
                    action="rm -rf temp/",
                    observation="Attempted dangerous operation",
                    reward=-0.5,
                    done=False,
                    info={'error': 'dangerous_command'},
                    execution_time=5.0,
                    tokens_used=50,
                    cost=0.005,
                    safety_violations=['dangerous_command', 'file_system_violation']
                ),
                TurnResult(
                    turn=2,
                    action="ls temp/",
                    observation="Safe directory listing",
                    reward=0.1,
                    done=False,
                    info={'files_changed': [], 'error': None},
                    execution_time=3.0,
                    tokens_used=30,
                    cost=0.003,
                    safety_violations=[]
                ),
                TurnResult(
                    turn=3,
                    action="sudo chmod 777 /",
                    observation="Another dangerous operation",
                    reward=-1.0,
                    done=False,
                    info={'error': 'unsafe_command'},
                    execution_time=2.0,
                    tokens_used=20,
                    cost=0.002,
                    safety_violations=['unsafe_command', 'policy_violation']
                ),
                TurnResult(
                    turn=4,
                    action="echo 'safe command'",
                    observation="Safe operation completed",
                    reward=0.0,
                    done=True,
                    info={'files_changed': [], 'error': None},
                    execution_time=1.0,
                    tokens_used=10,
                    cost=0.001,
                    safety_violations=[]
                )
            ],
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SAFETY_VIOLATION,
            metadata={}
        )
        results.append(safety_heavy_evaluation)
        
        return results
    
    def test_calculate_advanced_repair_quality_metrics(self):
        """Test advanced repair quality metrics calculation."""
        metrics = self.metrics_engine.calculate_advanced_repair_quality_metrics(
            self.advanced_evaluation_results
        )
        
        assert 'edit_churn' in metrics
        assert 'files_touched' in metrics
        assert 'edit_efficiency' in metrics
        assert 'modification_patterns' in metrics
        assert 'file_complexity_impact' in metrics
        assert 'rollback_frequency' in metrics
        
        # Verify metric ranges
        assert metrics['edit_churn'] >= 0.0
        assert metrics['files_touched'] >= 0
        assert 0.0 <= metrics['edit_efficiency'] <= 1.0
        assert metrics['file_complexity_impact'] >= 0.0
        assert 0.0 <= metrics['rollback_frequency'] <= 1.0
        
        # Check modification patterns
        assert isinstance(metrics['modification_patterns'], dict)
        assert 'python_file' in metrics['modification_patterns']
    
    def test_calculate_advanced_robustness_metrics(self):
        """Test advanced robustness metrics calculation."""
        metrics = self.metrics_engine.calculate_advanced_robustness_metrics(
            self.advanced_evaluation_results
        )
        
        assert 'recovery_rate' in metrics
        assert 'stability_score' in metrics
        assert 'error_resilience' in metrics
        assert 'adaptation_speed' in metrics
        assert 'consistency_score' in metrics
        assert 'failure_pattern_diversity' in metrics
        
        # Verify metric ranges
        assert 0.0 <= metrics['recovery_rate'] <= 1.0
        assert 0.0 <= metrics['stability_score'] <= 1.0
        assert 0.0 <= metrics['error_resilience'] <= 1.0
        assert metrics['adaptation_speed'] >= 0.0
        assert 0.0 <= metrics['consistency_score'] <= 1.0
        assert 0.0 <= metrics['failure_pattern_diversity'] <= 1.0
    
    def test_calculate_advanced_cost_metrics(self):
        """Test advanced cost metrics calculation."""
        metrics = self.metrics_engine.calculate_advanced_cost_metrics(
            self.advanced_evaluation_results
        )
        
        assert 'wall_time_per_solved' in metrics
        assert 'tokens_per_solved' in metrics
        assert 'cost_per_solved' in metrics
        assert 'cost_efficiency' in metrics
        assert 'resource_utilization' in metrics
        assert 'cost_variance' in metrics
        assert 'time_to_first_success' in metrics
        
        # Verify metric ranges and types
        assert metrics['wall_time_per_solved'] >= 0.0
        assert metrics['tokens_per_solved'] >= 0
        assert metrics['cost_per_solved'] >= 0.0
        assert metrics['cost_efficiency'] >= 0.0
        assert 0.0 <= metrics['resource_utilization'] <= 1.0
        assert metrics['cost_variance'] >= 0.0
        assert metrics['time_to_first_success'] >= 0.0
    
    def test_calculate_advanced_safety_metrics(self):
        """Test advanced safety metrics calculation."""
        metrics = self.metrics_engine.calculate_advanced_safety_metrics(
            self.advanced_evaluation_results
        )
        
        assert 'safety_incidents' in metrics
        assert 'policy_violations' in metrics
        assert 'incident_types' in metrics
        assert 'incident_frequency' in metrics
        assert 'safety_recovery_rate' in metrics
        assert 'violation_severity' in metrics
        assert 'safety_trend' in metrics
        assert 'safety_compliance_rate' in metrics
        
        # Verify metric ranges and types
        assert metrics['safety_incidents'] >= 0
        assert metrics['policy_violations'] >= 0
        assert isinstance(metrics['incident_types'], dict)
        assert metrics['incident_frequency'] >= 0.0
        assert 0.0 <= metrics['safety_recovery_rate'] <= 1.0
        assert metrics['violation_severity'] >= 0.0
        assert 0.0 <= metrics['safety_compliance_rate'] <= 1.0
        
        # Check that we detected the safety violations from test data
        assert metrics['safety_incidents'] > 0  # Should detect violations from test data
        assert 'dangerous_command' in metrics['incident_types']
    
    def test_advanced_edit_churn_calculation(self):
        """Test advanced edit churn calculation."""
        turn_results = self.advanced_evaluation_results[0].turn_results
        churn_data = self.metrics_engine._calculate_advanced_edit_churn(turn_results)
        
        assert 'churn' in churn_data
        assert 'efficiency' in churn_data
        assert churn_data['churn'] >= 1.0  # Should be >= 1 due to multiple edits
        assert 0.0 <= churn_data['efficiency'] <= 1.0
    
    def test_file_modification_analysis(self):
        """Test file modification pattern analysis."""
        turn_results = self.advanced_evaluation_results[0].turn_results
        analysis = self.metrics_engine._analyze_file_modifications(turn_results)
        
        assert 'unique_files' in analysis
        assert 'total_modifications' in analysis
        assert 'patterns' in analysis
        assert 'file_modification_counts' in analysis
        
        assert analysis['unique_files'] > 0
        assert analysis['total_modifications'] >= analysis['unique_files']
        assert 'python_file' in analysis['patterns']
    
    def test_rollback_frequency_calculation(self):
        """Test rollback frequency calculation."""
        turn_results = self.advanced_evaluation_results[0].turn_results
        rollback_freq = self.metrics_engine._calculate_rollback_frequency(turn_results)
        
        assert 0.0 <= rollback_freq <= 1.0
    
    def test_advanced_recovery_rate_calculation(self):
        """Test advanced recovery rate calculation."""
        turn_results = self.advanced_evaluation_results[1].turn_results  # Safety-heavy evaluation
        recovery_data = self.metrics_engine._calculate_advanced_recovery_rate(turn_results)
        
        assert 'rate' in recovery_data
        assert 'resilience' in recovery_data
        assert 'adaptation_speed' in recovery_data
        
        assert 0.0 <= recovery_data['rate'] <= 1.0
        assert 0.0 <= recovery_data['resilience'] <= 1.0
        assert recovery_data['adaptation_speed'] >= 0.0
    
    def test_advanced_stability_score_calculation(self):
        """Test advanced stability score calculation."""
        turn_results = self.advanced_evaluation_results[0].turn_results
        stability_data = self.metrics_engine._calculate_advanced_stability_score(turn_results)
        
        assert 'score' in stability_data
        assert 'consistency' in stability_data
        
        assert 0.0 <= stability_data['score'] <= 1.0
        assert 0.0 <= stability_data['consistency'] <= 1.0
    
    def test_failure_pattern_extraction(self):
        """Test failure pattern extraction."""
        turn_results = self.advanced_evaluation_results[1].turn_results
        patterns = self.metrics_engine._extract_failure_patterns(turn_results)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0  # Should extract some failure patterns
        assert 'dangerous_command' in patterns or 'unsafe_command' in patterns
    
    def test_pattern_diversity_calculation(self):
        """Test pattern diversity calculation."""
        patterns = ['error_a', 'error_b', 'error_a', 'error_c', 'error_b', 'error_a']
        diversity = self.metrics_engine._calculate_pattern_diversity(patterns)
        
        assert 0.0 <= diversity <= 1.0
        
        # Test with no patterns
        empty_diversity = self.metrics_engine._calculate_pattern_diversity([])
        assert empty_diversity == 0.0
        
        # Test with single pattern type
        single_diversity = self.metrics_engine._calculate_pattern_diversity(['error'] * 5)
        assert single_diversity == 0.0
    
    def test_resource_utilization_calculation(self):
        """Test resource utilization calculation."""
        turn_results = self.advanced_evaluation_results[0].turn_results
        utilization = self.metrics_engine._calculate_resource_utilization(turn_results)
        
        assert 0.0 <= utilization <= 1.0
    
    def test_time_to_first_success_calculation(self):
        """Test time to first success calculation."""
        turn_results = self.advanced_evaluation_results[0].turn_results
        time_to_success = self.metrics_engine._calculate_time_to_first_success(turn_results)
        
        assert time_to_success > 0.0
        
        # Test with no success
        failed_turns = [
            TurnResult(
                turn=1, action="action", observation="obs", reward=-1.0,
                done=False, info={}, execution_time=10.0
            ),
            TurnResult(
                turn=2, action="action", observation="obs", reward=-1.0,
                done=False, info={}, execution_time=15.0
            )
        ]
        time_no_success = self.metrics_engine._calculate_time_to_first_success(failed_turns)
        assert time_no_success == 25.0  # Total time
    
    def test_safety_recovery_rate_calculation(self):
        """Test safety recovery rate calculation."""
        turn_results = self.advanced_evaluation_results[1].turn_results
        recovery_rate = self.metrics_engine._calculate_safety_recovery_rate(turn_results)
        
        assert 0.0 <= recovery_rate <= 1.0
    
    def test_violation_severity_calculation(self):
        """Test violation severity calculation."""
        violations = ['dangerous_command', 'file_system_violation', 'unsafe_command']
        severity = self.metrics_engine._calculate_violation_severity(violations)
        
        assert severity > 0.0
        
        # Test with no violations
        no_violations_severity = self.metrics_engine._calculate_violation_severity([])
        assert no_violations_severity == 0.0
    
    def test_safety_trend_calculation(self):
        """Test safety trend calculation."""
        trend = self.metrics_engine._calculate_safety_trend(self.advanced_evaluation_results)
        
        # Trend can be positive, negative, or zero
        assert isinstance(trend, float)
        
        # Test with single evaluation
        single_trend = self.metrics_engine._calculate_safety_trend([self.advanced_evaluation_results[0]])
        assert single_trend == 0.0
    
    def test_safety_compliance_rate_calculation(self):
        """Test safety compliance rate calculation."""
        compliance_rate = self.metrics_engine._calculate_safety_compliance_rate(self.advanced_evaluation_results)
        
        assert 0.0 <= compliance_rate <= 1.0
        
        # Should be less than 1.0 since we have safety violations
        assert compliance_rate < 1.0
        
        # Test with empty list
        empty_compliance = self.metrics_engine._calculate_safety_compliance_rate([])
        assert empty_compliance == 1.0


class TestMetricsAggregationAndReporting:
    """Test suite for metrics aggregation and reporting functionality."""
    
    def setup_method(self):
        """Set up test fixtures for aggregation and reporting."""
        self.metrics_engine = MetricsEngine()
        self.multiple_runs = self._create_multiple_run_data()
    
    def _create_multiple_run_data(self) -> List[List[EvaluationResult]]:
        """Create multiple runs of evaluation results for testing."""
        runs = []
        
        # Run 1: Good performance
        run1 = [
            self._create_test_evaluation("run1_eval1", success=True, turns=3, cost=0.05),
            self._create_test_evaluation("run1_eval2", success=True, turns=4, cost=0.06),
            self._create_test_evaluation("run1_eval3", success=False, turns=8, cost=0.12)
        ]
        runs.append(run1)
        
        # Run 2: Poor performance
        run2 = [
            self._create_test_evaluation("run2_eval1", success=False, turns=10, cost=0.15),
            self._create_test_evaluation("run2_eval2", success=True, turns=6, cost=0.08),
            self._create_test_evaluation("run2_eval3", success=False, turns=12, cost=0.18)
        ]
        runs.append(run2)
        
        # Run 3: Mixed performance
        run3 = [
            self._create_test_evaluation("run3_eval1", success=True, turns=5, cost=0.07),
            self._create_test_evaluation("run3_eval2", success=True, turns=3, cost=0.04),
            self._create_test_evaluation("run3_eval3", success=True, turns=4, cost=0.05)
        ]
        runs.append(run3)
        
        return runs
    
    def _create_test_evaluation(self, eval_id: str, success: bool, turns: int, cost: float) -> EvaluationResult:
        """Helper to create test evaluation results."""
        turn_results = []
        for i in range(turns):
            reward = 1.0 if (success and i == turns - 1) else 0.1 if success else -0.1
            turn_results.append(TurnResult(
                turn=i+1,
                action=f"action_{i+1}",
                observation=f"obs_{i+1}",
                reward=reward,
                done=(i == turns - 1),
                info={'files_changed': [f'file_{i}.py'] if i % 2 == 0 else []},
                execution_time=5.0,
                tokens_used=50,
                cost=cost / turns
            ))
        
        return EvaluationResult(
            evaluation_id=eval_id,
            task_id="test_task",
            model_id="test_model",
            start_time=datetime.now() - timedelta(minutes=turns),
            end_time=datetime.now(),
            success=success,
            total_turns=turns,
            turn_results=turn_results,
            final_metrics={},
            aggregated_metrics=AggregatedMetrics(),
            termination_reason=TerminationReason.SUCCESS if success else TerminationReason.MAX_TURNS,
            metadata={}
        )
    
    def test_aggregate_metrics_across_runs(self):
        """Test metrics aggregation across multiple runs."""
        result = self.metrics_engine.aggregate_metrics_across_runs(
            self.multiple_runs,
            run_labels=["Good Run", "Poor Run", "Mixed Run"]
        )
        
        assert 'summary' in result
        assert 'aggregated_metrics' in result
        assert 'statistical_analysis' in result
        assert 'trend_analysis' in result
        assert 'performance_comparison' in result
        assert 'run_details' in result
        
        # Check summary
        summary = result['summary']
        assert summary['total_runs'] == 3
        assert summary['total_evaluations'] == 9  # 3 evaluations per run
        assert 0.0 <= summary['overall_success_rate'] <= 1.0
        
        # Check run details
        assert len(result['run_details']) == 3
        assert result['run_details'][0]['run_label'] == "Good Run"
    
    def test_generate_comprehensive_report(self):
        """Test comprehensive report generation."""
        evaluation_results = self.multiple_runs[0]  # Use first run
        
        report = self.metrics_engine.generate_comprehensive_report(evaluation_results)
        
        assert 'executive_summary' in report
        assert 'basic_metrics' in report
        assert 'advanced_metrics' in report
        assert 'performance_insights' in report
        assert 'threshold_analysis' in report
        assert 'recommendations' in report
        assert 'metadata' in report
        
        # Check executive summary
        exec_summary = report['executive_summary']
        assert 'overall_assessment' in exec_summary
        assert 'success_rate' in exec_summary
        assert 'total_evaluations' in exec_summary
        assert exec_summary['total_evaluations'] == 3
        
        # Check metadata
        metadata = report['metadata']
        assert 'report_generated_at' in metadata
        assert 'total_evaluations' in metadata
        assert 'report_config' in metadata
    
    def test_detect_performance_anomalies(self):
        """Test performance anomaly detection."""
        evaluation_results = []
        
        # Create normal evaluations
        for i in range(8):
            evaluation_results.append(
                self._create_test_evaluation(f"normal_{i}", success=True, turns=4, cost=0.05)
            )
        
        # Add anomalous evaluation
        evaluation_results.append(
            self._create_test_evaluation("anomaly", success=False, turns=20, cost=0.50)
        )
        
        anomalies = self.metrics_engine.detect_performance_anomalies(evaluation_results)
        
        assert 'detected_anomalies' in anomalies
        assert 'analysis' in anomalies
        
        # Should detect the anomalous evaluation
        assert len(anomalies['detected_anomalies']) > 0
    
    def test_configure_and_check_metric_thresholds(self):
        """Test metric threshold configuration and checking."""
        # Configure thresholds
        thresholds = {
            'resolved_percentage': {'warning': 70.0, 'critical': 50.0},
            'safety_incidents': {'warning': 2, 'critical': 5},
            'avg_turns': {'warning': 10, 'critical': 15}
        }
        
        self.metrics_engine.configure_metric_thresholds(thresholds)
        
        # Create metrics that violate thresholds
        test_metrics = AggregatedMetrics(
            resolved_percentage=40.0,  # Below critical threshold
            safety_incidents=3,        # Above warning threshold
            avg_turns=12.0            # Above warning threshold
        )
        
        threshold_results = self.metrics_engine.check_metric_thresholds(test_metrics)
        
        assert 'alerts' in threshold_results
        assert 'violations' in threshold_results
        assert 'total_alerts' in threshold_results
        assert 'critical_alerts' in threshold_results
        assert 'warning_alerts' in threshold_results
        
        # Should have violations
        assert threshold_results['total_alerts'] > 0
        assert threshold_results['critical_alerts'] > 0
        assert threshold_results['warning_alerts'] > 0
    
    def test_statistical_analysis(self):
        """Test statistical analysis functionality."""
        run_metrics = []
        for i, run_results in enumerate(self.multiple_runs):
            metrics = self.metrics_engine.calculate_all_metrics(run_results)
            run_metrics.append({
                'run_label': f'Run_{i+1}',
                'metrics': metrics,
                'num_evaluations': len(run_results),
                'success_rate': sum(1 for r in run_results if r.success) / len(run_results)
            })
        
        analysis = self.metrics_engine._perform_statistical_analysis(run_metrics)
        
        assert 'success_rate_analysis' in analysis
        assert 'run_consistency' in analysis
        assert 'performance_stability' in analysis
        
        # Check success rate analysis
        sr_analysis = analysis['success_rate_analysis']
        assert 'mean' in sr_analysis
        assert 'std_dev' in sr_analysis
        assert 'confidence_interval_95' in sr_analysis
        assert 'is_consistent' in sr_analysis
    
    def test_trend_detection(self):
        """Test trend detection functionality."""
        run_metrics = []
        
        # Create runs with improving trend
        success_rates = [0.3, 0.5, 0.7, 0.8, 0.9]  # Improving trend
        
        for i, sr in enumerate(success_rates):
            # Create mock run metrics
            mock_metrics = AggregatedMetrics(resolved_percentage=sr * 100)
            run_metrics.append({
                'run_label': f'Run_{i+1}',
                'metrics': mock_metrics,
                'success_rate': sr
            })
        
        trends = self.metrics_engine._detect_trends(run_metrics)
        
        assert 'success_rate_trend' in trends
        
        # Should detect improving trend
        sr_trend = trends['success_rate_trend']
        assert sr_trend['direction'] == 'improving'
        assert sr_trend['strength'] > 0
    
    def test_performance_comparison(self):
        """Test performance comparison across runs."""
        run_metrics = []
        for i, run_results in enumerate(self.multiple_runs):
            metrics = self.metrics_engine.calculate_all_metrics(run_results)
            run_metrics.append({
                'run_label': f'Run_{i+1}',
                'metrics': metrics,
                'success_rate': sum(1 for r in run_results if r.success) / len(run_results)
            })
        
        comparison = self.metrics_engine._compare_run_performance(run_metrics)
        
        assert 'best_run' in comparison
        assert 'worst_run' in comparison
        assert 'performance_gap' in comparison
        assert 'improvement_potential' in comparison
        
        # Performance gap should be positive (best > worst)
        assert comparison['performance_gap'] >= 0
    
    def test_confidence_interval_calculation(self):
        """Test confidence interval calculation."""
        values = [0.8, 0.85, 0.9, 0.75, 0.88, 0.82, 0.87, 0.79]
        
        ci_95 = self.metrics_engine._calculate_confidence_interval(values, 0.95)
        ci_90 = self.metrics_engine._calculate_confidence_interval(values, 0.90)
        
        assert isinstance(ci_95, tuple)
        assert len(ci_95) == 2
        assert ci_95[0] <= ci_95[1]  # Lower bound <= upper bound
        
        # 95% CI should be wider than 90% CI
        assert (ci_95[1] - ci_95[0]) >= (ci_90[1] - ci_90[0])
        
        # Test with single value
        single_ci = self.metrics_engine._calculate_confidence_interval([0.5], 0.95)
        assert single_ci == (0.5, 0.5)
    
    def test_trend_calculation(self):
        """Test trend calculation functionality."""
        # Test improving trend
        improving_values = [1.0, 2.0, 3.0, 4.0, 5.0]
        improving_trend = self.metrics_engine._calculate_trend(improving_values)
        
        assert improving_trend['direction'] == 'improving'
        assert improving_trend['strength'] > 0
        assert improving_trend['slope'] > 0
        
        # Test declining trend
        declining_values = [5.0, 4.0, 3.0, 2.0, 1.0]
        declining_trend = self.metrics_engine._calculate_trend(declining_values)
        
        assert declining_trend['direction'] == 'declining'
        assert declining_trend['strength'] > 0
        assert declining_trend['slope'] < 0
        
        # Test stable trend
        stable_values = [3.0, 3.0, 3.0, 3.0, 3.0]
        stable_trend = self.metrics_engine._calculate_trend(stable_values)
        
        assert stable_trend['direction'] == 'stable'
        assert stable_trend['strength'] == 0.0
        
        # Test insufficient data
        insufficient_trend = self.metrics_engine._calculate_trend([1.0, 2.0])
        assert insufficient_trend['direction'] == 'insufficient_data'
    
    def test_outlier_detection_iqr(self):
        """Test IQR-based outlier detection."""
        # Normal distribution with outliers
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100]  # 100 is an outlier
        
        outliers = self.metrics_engine._detect_outliers_iqr(values, 1.5)
        
        assert len(outliers) > 0
        assert 10 in outliers  # Index of the outlier value (100)
        
        # Test with no outliers
        normal_values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        no_outliers = self.metrics_engine._detect_outliers_iqr(normal_values, 1.5)
        
        assert len(no_outliers) == 0
        
        # Test with insufficient data
        insufficient_outliers = self.metrics_engine._detect_outliers_iqr([1, 2, 3], 1.5)
        assert len(insufficient_outliers) == 0
    
    def test_baseline_calculation_from_history(self):
        """Test baseline calculation from history."""
        # Add some history entries
        for i in range(3):
            metrics = AggregatedMetrics(
                resolved_percentage=80.0 + i * 5,
                avg_turns=5.0 + i,
                cost_per_solved=0.1 + i * 0.01
            )
            self.metrics_engine.calculation_history.append({
                'timestamp': datetime.now(),
                'metrics': metrics.to_dict()
            })
        
        baseline = self.metrics_engine._calculate_baseline_from_history()
        
        assert isinstance(baseline, AggregatedMetrics)
        assert baseline.resolved_percentage > 0
        assert baseline.avg_turns > 0
        assert baseline.cost_per_solved > 0
    
    def test_metrics_comparison_with_baseline(self):
        """Test metrics comparison with baseline."""
        baseline = AggregatedMetrics(
            resolved_percentage=80.0,
            avg_turns=5.0,
            cost_per_solved=0.1
        )
        
        # Current metrics with some deviations
        current = AggregatedMetrics(
            resolved_percentage=60.0,  # 25% lower
            avg_turns=8.0,            # 60% higher
            cost_per_solved=0.15      # 50% higher
        )
        
        comparisons = self.metrics_engine._compare_metrics_with_baseline(
            current, baseline, sensitivity=2.0
        )
        
        assert 'resolved_percentage' in comparisons
        assert 'avg_turns' in comparisons
        assert 'cost_per_solved' in comparisons
        
        # Should detect anomalies for significant deviations
        rp_comparison = comparisons['resolved_percentage']
        assert rp_comparison['is_anomaly'] == True
        assert rp_comparison['direction'] == 'lower'
        assert rp_comparison['deviation'] > 0.2  # 20% deviation
    
    def test_anomaly_analysis(self):
        """Test anomaly analysis functionality."""
        anomalies = [
            {'metric': 'resolved_percentage', 'severity': 'high', 'value': 30.0},
            {'metric': 'safety_incidents', 'severity': 'critical', 'value': 10},
            {'metric': 'avg_turns', 'severity': 'medium', 'value': 15.0},
            {'metric': 'safety_incidents', 'severity': 'high', 'value': 8}
        ]
        
        analysis = self.metrics_engine._analyze_anomalies(anomalies)
        
        assert 'total_anomalies' in analysis
        assert 'affected_metrics' in analysis
        assert 'severity_distribution' in analysis
        assert 'most_affected_metric' in analysis
        assert 'patterns' in analysis
        
        assert analysis['total_anomalies'] == 4
        assert 'safety_incidents' in analysis['affected_metrics']
        assert analysis['most_affected_metric'] == 'safety_incidents'  # Appears twice
    
    def test_empty_data_handling(self):
        """Test handling of empty data in aggregation functions."""
        # Test with empty runs
        empty_result = self.metrics_engine.aggregate_metrics_across_runs([])
        assert 'error' in empty_result
        
        # Test with runs containing no results
        empty_runs_result = self.metrics_engine.aggregate_metrics_across_runs([[]])
        assert 'error' in empty_runs_result
        
        # Test anomaly detection with insufficient data
        insufficient_anomalies = self.metrics_engine.detect_performance_anomalies([])
        # Should handle gracefully without errors
        assert isinstance(insufficient_anomalies, dict)
    
    def test_report_configuration(self):
        """Test report configuration functionality."""
        custom_config = {
            'include_advanced_metrics': False,
            'include_insights': True,
            'thresholds': {
                'resolved_percentage': {'warning': 60.0, 'critical': 40.0}
            }
        }
        
        evaluation_results = self.multiple_runs[0]
        report = self.metrics_engine.generate_comprehensive_report(
            evaluation_results, 
            report_config=custom_config
        )
        
        # Should respect configuration
        assert report['metadata']['report_config'] == custom_config
        
        # Advanced metrics should be empty or minimal since disabled
        if 'advanced_metrics' in report:
            # May still have structure but should be limited
            pass
    
    def test_threshold_exceeds_logic(self):
        """Test threshold exceeding logic for different metric types."""
        # Test lower-is-better metrics
        assert self.metrics_engine._exceeds_threshold(10.0, 5.0, 'avg_turns') == True
        assert self.metrics_engine._exceeds_threshold(3.0, 5.0, 'avg_turns') == False
        
        # Test higher-is-better metrics
        assert self.metrics_engine._exceeds_threshold(60.0, 70.0, 'resolved_percentage') == True
        assert self.metrics_engine._exceeds_threshold(80.0, 70.0, 'resolved_percentage') == False
    
    def test_advanced_metrics_integration(self):
        """Test integration of all advanced metrics."""
        # Use the first run data for testing
        evaluation_results = self.multiple_runs[0]
        
        # Test that advanced metrics can be calculated together
        repair_metrics = self.metrics_engine.calculate_advanced_repair_quality_metrics(
            evaluation_results
        )
        robustness_metrics = self.metrics_engine.calculate_advanced_robustness_metrics(
            evaluation_results
        )
        cost_metrics = self.metrics_engine.calculate_advanced_cost_metrics(
            evaluation_results
        )
        safety_metrics = self.metrics_engine.calculate_advanced_safety_metrics(
            evaluation_results
        )
        
        # Verify all metrics are calculated
        assert all(isinstance(m, dict) for m in [repair_metrics, robustness_metrics, cost_metrics, safety_metrics])
        assert all(len(m) > 0 for m in [repair_metrics, robustness_metrics, cost_metrics, safety_metrics])
    
    def test_advanced_metrics_with_empty_data(self):
        """Test advanced metrics with empty evaluation results."""
        empty_results = []
        
        repair_metrics = self.metrics_engine.calculate_advanced_repair_quality_metrics(empty_results)
        robustness_metrics = self.metrics_engine.calculate_advanced_robustness_metrics(empty_results)
        cost_metrics = self.metrics_engine.calculate_advanced_cost_metrics(empty_results)
        safety_metrics = self.metrics_engine.calculate_advanced_safety_metrics(empty_results)
        
        # All should return valid default values
        assert all(isinstance(m, dict) for m in [repair_metrics, robustness_metrics, cost_metrics, safety_metrics])
        
        # Check specific default values
        assert repair_metrics['edit_churn'] == 0.0
        assert robustness_metrics['recovery_rate'] == 0.0
        assert cost_metrics['cost_per_solved'] == 0.0
        assert safety_metrics['safety_incidents'] == 0


if __name__ == "__main__":
    pytest.main([__file__])