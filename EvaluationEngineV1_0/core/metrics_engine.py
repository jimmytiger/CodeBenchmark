"""
Core Metrics Engine for Multi-Turn Evaluation.

This module implements comprehensive metrics calculation for multi-turn evaluation
scenarios, covering task success, efficiency, repair quality, robustness, cost,
and safety dimensions as specified in requirements 4.1-4.6.
"""

import math
import statistics
from collections import defaultdict, Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import logging

from .data_models import (
    EvaluationResult, TurnResult, AggregatedMetrics, 
    TerminationReason, StandardizedOutput
)

logger = logging.getLogger(__name__)


@dataclass
class MetricCalculationResult:
    """Result of a metric calculation with metadata."""
    value: float
    metadata: Dict[str, Any]
    calculation_time: float
    error: Optional[str] = None


class MetricsEngine:
    """
    Core metrics engine for multi-turn evaluation.
    
    Implements comprehensive metrics across all dimensions:
    - Task Success: Resolved%, Recall, MRR (Requirements 4.1, 4.2)
    - Efficiency: Avg Turns, Steps, Redundancy Rate (Requirements 4.2)
    - Repair Quality: Edit Churn, Files Touched (Requirements 4.3)
    - Robustness: Recovery Rate, Stability (Requirements 4.4)
    - Cost: Wall Time, Token/Cost per Solved (Requirements 4.5)
    - Safety: Incidents, Policy Violations (Requirements 4.6)
    """
    
    def __init__(self):
        """Initialize the metrics engine."""
        self.calculation_history: List[Dict[str, Any]] = []
        self.metric_cache: Dict[str, MetricCalculationResult] = {}
        self.advanced_metrics_enabled = True
        
    def calculate_all_metrics(self, 
                            evaluation_results: List[EvaluationResult]) -> AggregatedMetrics:
        """
        Calculate all metrics for a set of evaluation results.
        
        Args:
            evaluation_results: List of evaluation results to analyze
            
        Returns:
            AggregatedMetrics with all calculated metrics
            
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
        """
        start_time = datetime.now()
        
        if not evaluation_results:
            logger.warning("No evaluation results provided for metrics calculation")
            return AggregatedMetrics()
        
        try:
            # Calculate Task Success Metrics (Requirements 4.1, 4.2)
            task_success_metrics = self._calculate_task_success_metrics(evaluation_results)
            
            # Calculate Efficiency Metrics (Requirements 4.2)
            efficiency_metrics = self._calculate_efficiency_metrics(evaluation_results)
            
            # Calculate Repair Quality Metrics (Requirements 4.3)
            repair_quality_metrics = self._calculate_repair_quality_metrics(evaluation_results)
            
            # Calculate Robustness Metrics (Requirements 4.4)
            robustness_metrics = self._calculate_robustness_metrics(evaluation_results)
            
            # Calculate Cost Metrics (Requirements 4.5)
            cost_metrics = self._calculate_cost_metrics(evaluation_results)
            
            # Calculate Safety Metrics (Requirements 4.6)
            safety_metrics = self._calculate_safety_metrics(evaluation_results)
            
            # Combine all metrics
            aggregated_metrics = AggregatedMetrics(
                # Task Success
                resolved_percentage=task_success_metrics['resolved_percentage'],
                recall=task_success_metrics['recall'],
                mrr=task_success_metrics['mrr'],
                
                # Efficiency
                avg_turns=efficiency_metrics['avg_turns'],
                avg_steps=efficiency_metrics['avg_steps'],
                redundancy_rate=efficiency_metrics['redundancy_rate'],
                
                # Repair Quality
                edit_churn=repair_quality_metrics['edit_churn'],
                files_touched=repair_quality_metrics['files_touched'],
                
                # Robustness
                recovery_rate=robustness_metrics['recovery_rate'],
                stability_score=robustness_metrics['stability_score'],
                
                # Cost
                wall_time_per_solved=cost_metrics['wall_time_per_solved'],
                tokens_per_solved=cost_metrics['tokens_per_solved'],
                cost_per_solved=cost_metrics['cost_per_solved'],
                
                # Safety
                safety_incidents=safety_metrics['safety_incidents'],
                policy_violations=safety_metrics['policy_violations']
            )
            
            # Record calculation
            calculation_time = (datetime.now() - start_time).total_seconds()
            self.calculation_history.append({
                'timestamp': start_time,
                'calculation_time': calculation_time,
                'num_evaluations': len(evaluation_results),
                'metrics': aggregated_metrics.to_dict()
            })
            
            logger.info(f"Calculated metrics for {len(evaluation_results)} evaluations in {calculation_time:.2f}s")
            return aggregated_metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            raise
    
    def _calculate_task_success_metrics(self, 
                                      evaluation_results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate task success metrics: Resolved%, Recall, MRR.
        
        Requirements: 4.1, 4.2
        """
        total_tasks = len(evaluation_results)
        successful_tasks = sum(1 for result in evaluation_results if result.success)
        
        # Resolved Percentage (Requirements 4.1)
        resolved_percentage = (successful_tasks / total_tasks * 100.0) if total_tasks > 0 else 0.0
        
        # Recall (Requirements 4.2)
        # For multi-turn evaluation, recall is the same as resolved percentage
        recall = resolved_percentage / 100.0
        
        # Mean Reciprocal Rank (MRR) (Requirements 4.2)
        # Calculate based on the turn at which success was achieved
        reciprocal_ranks = []
        for result in evaluation_results:
            if result.success:
                # Find the turn where success was first achieved
                success_turn = self._find_success_turn(result.turn_results)
                if success_turn > 0:
                    reciprocal_ranks.append(1.0 / success_turn)
                else:
                    reciprocal_ranks.append(1.0)  # Success on first turn
            else:
                reciprocal_ranks.append(0.0)  # No success
        
        mrr = statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
        
        return {
            'resolved_percentage': resolved_percentage,
            'recall': recall,
            'mrr': mrr
        }
    
    def _calculate_efficiency_metrics(self, 
                                    evaluation_results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate efficiency metrics: Avg Turns, Steps, Redundancy Rate.
        
        Requirements: 4.2
        """
        if not evaluation_results:
            return {'avg_turns': 0.0, 'avg_steps': 0.0, 'redundancy_rate': 0.0}
        
        # Average Turns
        turns = [result.total_turns for result in evaluation_results]
        avg_turns = statistics.mean(turns)
        
        # Average Steps (sum of all actions across all turns)
        total_steps = []
        for result in evaluation_results:
            steps = sum(1 for turn in result.turn_results if turn.action is not None)
            total_steps.append(steps)
        
        avg_steps = statistics.mean(total_steps) if total_steps else 0.0
        
        # Redundancy Rate (percentage of repeated or unnecessary actions)
        redundancy_rates = []
        for result in evaluation_results:
            redundancy_rate = self._calculate_redundancy_rate(result.turn_results)
            redundancy_rates.append(redundancy_rate)
        
        avg_redundancy_rate = statistics.mean(redundancy_rates) if redundancy_rates else 0.0
        
        return {
            'avg_turns': avg_turns,
            'avg_steps': avg_steps,
            'redundancy_rate': avg_redundancy_rate
        }
    
    def _calculate_repair_quality_metrics(self, 
                                        evaluation_results: List[EvaluationResult]) -> Dict[str, Union[float, int]]:
        """
        Calculate repair quality metrics: Edit Churn, Files Touched.
        
        Requirements: 4.3
        """
        if not evaluation_results:
            return {'edit_churn': 0.0, 'files_touched': 0}
        
        edit_churns = []
        files_touched_counts = []
        
        for result in evaluation_results:
            # Calculate edit churn (ratio of total edits to final edits)
            edit_churn = self._calculate_edit_churn(result.turn_results)
            edit_churns.append(edit_churn)
            
            # Count unique files touched
            files_touched = self._count_files_touched(result.turn_results)
            files_touched_counts.append(files_touched)
        
        avg_edit_churn = statistics.mean(edit_churns) if edit_churns else 0.0
        avg_files_touched = int(statistics.mean(files_touched_counts)) if files_touched_counts else 0
        
        return {
            'edit_churn': avg_edit_churn,
            'files_touched': avg_files_touched
        }
    
    def _calculate_robustness_metrics(self, 
                                    evaluation_results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate robustness metrics: Recovery Rate, Stability.
        
        Requirements: 4.4
        """
        if not evaluation_results:
            return {'recovery_rate': 0.0, 'stability_score': 0.0}
        
        recovery_rates = []
        stability_scores = []
        
        for result in evaluation_results:
            # Recovery Rate: percentage of errors that were recovered from
            recovery_rate = self._calculate_recovery_rate(result.turn_results)
            recovery_rates.append(recovery_rate)
            
            # Stability Score: consistency of performance across turns
            stability_score = self._calculate_stability_score(result.turn_results)
            stability_scores.append(stability_score)
        
        avg_recovery_rate = statistics.mean(recovery_rates) if recovery_rates else 0.0
        avg_stability_score = statistics.mean(stability_scores) if stability_scores else 0.0
        
        return {
            'recovery_rate': avg_recovery_rate,
            'stability_score': avg_stability_score
        }
    
    def _calculate_cost_metrics(self, 
                              evaluation_results: List[EvaluationResult]) -> Dict[str, Union[float, int]]:
        """
        Calculate cost metrics: Wall Time per Solved, Token/Cost per Solved.
        
        Requirements: 4.5
        """
        if not evaluation_results:
            return {'wall_time_per_solved': 0.0, 'tokens_per_solved': 0, 'cost_per_solved': 0.0}
        
        successful_results = [r for r in evaluation_results if r.success]
        
        if not successful_results:
            return {'wall_time_per_solved': 0.0, 'tokens_per_solved': 0, 'cost_per_solved': 0.0}
        
        # Wall Time per Solved
        wall_times = [r.duration for r in successful_results]
        avg_wall_time_per_solved = statistics.mean(wall_times)
        
        # Tokens per Solved
        tokens_per_solved_list = []
        costs_per_solved_list = []
        
        for result in successful_results:
            total_tokens = sum(turn.tokens_used for turn in result.turn_results)
            total_cost = sum(turn.cost for turn in result.turn_results)
            
            tokens_per_solved_list.append(total_tokens)
            costs_per_solved_list.append(total_cost)
        
        avg_tokens_per_solved = int(statistics.mean(tokens_per_solved_list)) if tokens_per_solved_list else 0
        avg_cost_per_solved = statistics.mean(costs_per_solved_list) if costs_per_solved_list else 0.0
        
        return {
            'wall_time_per_solved': avg_wall_time_per_solved,
            'tokens_per_solved': avg_tokens_per_solved,
            'cost_per_solved': avg_cost_per_solved
        }
    
    def _calculate_safety_metrics(self, 
                                evaluation_results: List[EvaluationResult]) -> Dict[str, int]:
        """
        Calculate safety metrics: Safety Incidents, Policy Violations.
        
        Requirements: 4.6
        """
        total_safety_incidents = 0
        total_policy_violations = 0
        
        for result in evaluation_results:
            # Count safety incidents from turn results
            for turn in result.turn_results:
                total_safety_incidents += len(turn.safety_violations)
            
            # Count policy violations from termination reasons
            if result.termination_reason == TerminationReason.SAFETY_VIOLATION:
                total_policy_violations += 1
        
        return {
            'safety_incidents': total_safety_incidents,
            'policy_violations': total_policy_violations
        }
    
    def _find_success_turn(self, turn_results: List[TurnResult]) -> int:
        """Find the turn number where success was first achieved."""
        for i, turn in enumerate(turn_results):
            if turn.done and turn.reward > 0:
                return i + 1
        return len(turn_results)  # Success on last turn if at all
    
    def _calculate_redundancy_rate(self, turn_results: List[TurnResult]) -> float:
        """Calculate the redundancy rate for a sequence of turns."""
        if len(turn_results) <= 1:
            return 0.0
        
        # Count repeated actions
        actions = [str(turn.action) for turn in turn_results if turn.action is not None]
        if not actions:
            return 0.0
        
        action_counts = Counter(actions)
        repeated_actions = sum(count - 1 for count in action_counts.values() if count > 1)
        
        return repeated_actions / len(actions) if actions else 0.0
    
    def _calculate_edit_churn(self, turn_results: List[TurnResult]) -> float:
        """Calculate edit churn (ratio of total edits to final edits)."""
        total_edits = 0
        final_state_edits = 0
        
        # Track file modifications across turns
        file_modifications = defaultdict(int)
        
        for turn in turn_results:
            if turn.info and 'files_changed' in turn.info:
                files_changed = turn.info['files_changed']
                if isinstance(files_changed, list):
                    total_edits += len(files_changed)
                    for file_path in files_changed:
                        file_modifications[file_path] += 1
        
        # Final edits are unique files that were modified
        final_state_edits = len(file_modifications)
        
        if final_state_edits == 0:
            return 0.0
        
        return total_edits / final_state_edits if final_state_edits > 0 else 0.0
    
    def _count_files_touched(self, turn_results: List[TurnResult]) -> int:
        """Count unique files touched across all turns."""
        files_touched = set()
        
        for turn in turn_results:
            if turn.info and 'files_changed' in turn.info:
                files_changed = turn.info['files_changed']
                if isinstance(files_changed, list):
                    files_touched.update(files_changed)
        
        return len(files_touched)
    
    def _calculate_recovery_rate(self, turn_results: List[TurnResult]) -> float:
        """Calculate recovery rate from errors."""
        error_turns = []
        recovery_turns = []
        
        for i, turn in enumerate(turn_results):
            # Identify error turns (negative reward or error in info)
            if turn.reward < 0 or (turn.info and turn.info.get('error')):
                error_turns.append(i)
            
            # Identify recovery turns (positive reward after error)
            if (turn.reward > 0 and i > 0 and 
                turn_results[i-1].reward < 0):
                recovery_turns.append(i)
        
        if not error_turns:
            return 1.0  # No errors, perfect recovery rate
        
        return len(recovery_turns) / len(error_turns)
    
    def _calculate_stability_score(self, turn_results: List[TurnResult]) -> float:
        """Calculate stability score based on reward consistency."""
        if len(turn_results) <= 1:
            return 1.0
        
        rewards = [turn.reward for turn in turn_results]
        
        # Calculate coefficient of variation (std dev / mean)
        if not rewards or statistics.mean(rewards) == 0:
            return 0.0
        
        try:
            cv = statistics.stdev(rewards) / abs(statistics.mean(rewards))
            # Convert to stability score (lower CV = higher stability)
            stability_score = 1.0 / (1.0 + cv)
            return stability_score
        except (statistics.StatisticsError, ZeroDivisionError):
            return 0.0
    
    def calculate_single_evaluation_metrics(self, 
                                          evaluation_result: EvaluationResult) -> AggregatedMetrics:
        """
        Calculate metrics for a single evaluation result.
        
        Args:
            evaluation_result: Single evaluation result to analyze
            
        Returns:
            AggregatedMetrics for the single evaluation
        """
        return self.calculate_all_metrics([evaluation_result])
    
    def get_metric_summary(self, 
                          evaluation_results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Get a comprehensive summary of metrics.
        
        Args:
            evaluation_results: List of evaluation results
            
        Returns:
            Dictionary with metric summary and analysis
        """
        if not evaluation_results:
            return {'error': 'No evaluation results provided'}
        
        metrics = self.calculate_all_metrics(evaluation_results)
        
        return {
            'total_evaluations': len(evaluation_results),
            'successful_evaluations': sum(1 for r in evaluation_results if r.success),
            'success_rate': sum(1 for r in evaluation_results if r.success) / len(evaluation_results),
            'metrics': metrics.to_dict(),
            'performance_summary': {
                'task_success': {
                    'resolved_percentage': metrics.resolved_percentage,
                    'recall': metrics.recall,
                    'mrr': metrics.mrr
                },
                'efficiency': {
                    'avg_turns': metrics.avg_turns,
                    'avg_steps': metrics.avg_steps,
                    'redundancy_rate': metrics.redundancy_rate
                },
                'quality': {
                    'edit_churn': metrics.edit_churn,
                    'files_touched': metrics.files_touched
                },
                'robustness': {
                    'recovery_rate': metrics.recovery_rate,
                    'stability_score': metrics.stability_score
                },
                'cost': {
                    'wall_time_per_solved': metrics.wall_time_per_solved,
                    'tokens_per_solved': metrics.tokens_per_solved,
                    'cost_per_solved': metrics.cost_per_solved
                },
                'safety': {
                    'safety_incidents': metrics.safety_incidents,
                    'policy_violations': metrics.policy_violations
                }
            }
        }
    
    def clear_cache(self):
        """Clear the metrics calculation cache."""
        self.metric_cache.clear()
        logger.info("Metrics cache cleared")
    
    def get_calculation_history(self) -> List[Dict[str, Any]]:
        """Get the history of metrics calculations."""
        return self.calculation_history.copy()
    
    # Advanced Metrics Calculation Methods (Requirements 4.3, 4.4, 4.5, 4.6)
    
    def calculate_advanced_repair_quality_metrics(self, 
                                                 evaluation_results: List[EvaluationResult]) -> Dict[str, Union[float, int]]:
        """
        Calculate advanced repair quality metrics with detailed analysis.
        
        Requirements: 4.3
        """
        if not evaluation_results:
            return {
                'edit_churn': 0.0,
                'files_touched': 0,
                'edit_efficiency': 0.0,
                'modification_patterns': {},
                'file_complexity_impact': 0.0,
                'rollback_frequency': 0.0
            }
        
        edit_churns = []
        files_touched_counts = []
        edit_efficiencies = []
        modification_patterns = defaultdict(int)
        rollback_frequencies = []
        
        for result in evaluation_results:
            # Enhanced edit churn calculation
            edit_churn_data = self._calculate_advanced_edit_churn(result.turn_results)
            edit_churns.append(edit_churn_data['churn'])
            edit_efficiencies.append(edit_churn_data['efficiency'])
            
            # File analysis
            file_analysis = self._analyze_file_modifications(result.turn_results)
            files_touched_counts.append(file_analysis['unique_files'])
            
            # Modification patterns
            for pattern, count in file_analysis['patterns'].items():
                modification_patterns[pattern] += count
            
            # Rollback frequency
            rollback_freq = self._calculate_rollback_frequency(result.turn_results)
            rollback_frequencies.append(rollback_freq)
        
        return {
            'edit_churn': statistics.mean(edit_churns) if edit_churns else 0.0,
            'files_touched': int(statistics.mean(files_touched_counts)) if files_touched_counts else 0,
            'edit_efficiency': statistics.mean(edit_efficiencies) if edit_efficiencies else 0.0,
            'modification_patterns': dict(modification_patterns),
            'file_complexity_impact': self._calculate_file_complexity_impact(evaluation_results),
            'rollback_frequency': statistics.mean(rollback_frequencies) if rollback_frequencies else 0.0
        }
    
    def calculate_advanced_robustness_metrics(self, 
                                            evaluation_results: List[EvaluationResult]) -> Dict[str, float]:
        """
        Calculate advanced robustness metrics with detailed analysis.
        
        Requirements: 4.4
        """
        if not evaluation_results:
            return {
                'recovery_rate': 0.0,
                'stability_score': 0.0,
                'error_resilience': 0.0,
                'adaptation_speed': 0.0,
                'consistency_score': 0.0,
                'failure_pattern_diversity': 0.0
            }
        
        recovery_rates = []
        stability_scores = []
        error_resiliences = []
        adaptation_speeds = []
        consistency_scores = []
        failure_patterns = []
        
        for result in evaluation_results:
            # Enhanced recovery rate
            recovery_data = self._calculate_advanced_recovery_rate(result.turn_results)
            recovery_rates.append(recovery_data['rate'])
            error_resiliences.append(recovery_data['resilience'])
            adaptation_speeds.append(recovery_data['adaptation_speed'])
            
            # Enhanced stability
            stability_data = self._calculate_advanced_stability_score(result.turn_results)
            stability_scores.append(stability_data['score'])
            consistency_scores.append(stability_data['consistency'])
            
            # Failure patterns
            patterns = self._extract_failure_patterns(result.turn_results)
            failure_patterns.extend(patterns)
        
        # Calculate failure pattern diversity
        pattern_diversity = self._calculate_pattern_diversity(failure_patterns)
        
        return {
            'recovery_rate': statistics.mean(recovery_rates) if recovery_rates else 0.0,
            'stability_score': statistics.mean(stability_scores) if stability_scores else 0.0,
            'error_resilience': statistics.mean(error_resiliences) if error_resiliences else 0.0,
            'adaptation_speed': statistics.mean(adaptation_speeds) if adaptation_speeds else 0.0,
            'consistency_score': statistics.mean(consistency_scores) if consistency_scores else 0.0,
            'failure_pattern_diversity': pattern_diversity
        }
    
    def calculate_advanced_cost_metrics(self, 
                                      evaluation_results: List[EvaluationResult]) -> Dict[str, Union[float, int]]:
        """
        Calculate advanced cost metrics with detailed analysis.
        
        Requirements: 4.5
        """
        if not evaluation_results:
            return {
                'wall_time_per_solved': 0.0,
                'tokens_per_solved': 0,
                'cost_per_solved': 0.0,
                'cost_efficiency': 0.0,
                'resource_utilization': 0.0,
                'cost_variance': 0.0,
                'time_to_first_success': 0.0
            }
        
        successful_results = [r for r in evaluation_results if r.success]
        all_results = evaluation_results
        
        if not successful_results:
            return {
                'wall_time_per_solved': 0.0,
                'tokens_per_solved': 0,
                'cost_per_solved': 0.0,
                'cost_efficiency': 0.0,
                'resource_utilization': 0.0,
                'cost_variance': 0.0,
                'time_to_first_success': 0.0
            }
        
        # Basic cost metrics
        wall_times = [r.duration for r in successful_results]
        tokens_per_solved = [sum(turn.tokens_used for turn in r.turn_results) for r in successful_results]
        costs_per_solved = [sum(turn.cost for turn in r.turn_results) for r in successful_results]
        
        # Advanced cost metrics
        cost_efficiencies = []
        resource_utilizations = []
        time_to_first_success_values = []
        
        for result in successful_results:
            # Cost efficiency (success per unit cost)
            total_cost = sum(turn.cost for turn in result.turn_results)
            cost_efficiency = 1.0 / total_cost if total_cost > 0 else 0.0
            cost_efficiencies.append(cost_efficiency)
            
            # Resource utilization
            resource_util = self._calculate_resource_utilization(result.turn_results)
            resource_utilizations.append(resource_util)
            
            # Time to first success indicator
            time_to_success = self._calculate_time_to_first_success(result.turn_results)
            time_to_first_success_values.append(time_to_success)
        
        # Cost variance across all attempts (including failed ones)
        all_costs = [sum(turn.cost for turn in r.turn_results) for r in all_results]
        cost_variance = statistics.variance(all_costs) if len(all_costs) > 1 else 0.0
        
        return {
            'wall_time_per_solved': statistics.mean(wall_times),
            'tokens_per_solved': int(statistics.mean(tokens_per_solved)),
            'cost_per_solved': statistics.mean(costs_per_solved),
            'cost_efficiency': statistics.mean(cost_efficiencies) if cost_efficiencies else 0.0,
            'resource_utilization': statistics.mean(resource_utilizations) if resource_utilizations else 0.0,
            'cost_variance': cost_variance,
            'time_to_first_success': statistics.mean(time_to_first_success_values) if time_to_first_success_values else 0.0
        }
    
    def calculate_advanced_safety_metrics(self, 
                                        evaluation_results: List[EvaluationResult]) -> Dict[str, Union[int, float]]:
        """
        Calculate advanced safety metrics with detailed analysis.
        
        Requirements: 4.6
        """
        total_safety_incidents = 0
        total_policy_violations = 0
        safety_incident_types = defaultdict(int)
        violation_severity_scores = []
        safety_recovery_rates = []
        incident_frequencies = []
        
        for result in evaluation_results:
            result_incidents = 0
            result_violations = []
            
            # Analyze turn-level safety violations
            for turn in result.turn_results:
                turn_incidents = len(turn.safety_violations)
                result_incidents += turn_incidents
                total_safety_incidents += turn_incidents
                
                # Categorize incident types
                for violation in turn.safety_violations:
                    safety_incident_types[violation] += 1
                    result_violations.append(violation)
            
            # Policy violations from termination
            if result.termination_reason == TerminationReason.SAFETY_VIOLATION:
                total_policy_violations += 1
            
            # Calculate safety metrics per evaluation
            incident_frequency = result_incidents / result.total_turns if result.total_turns > 0 else 0.0
            incident_frequencies.append(incident_frequency)
            
            # Safety recovery rate (ability to continue after safety incident)
            safety_recovery = self._calculate_safety_recovery_rate(result.turn_results)
            safety_recovery_rates.append(safety_recovery)
            
            # Violation severity
            severity = self._calculate_violation_severity(result_violations)
            violation_severity_scores.append(severity)
        
        # Calculate advanced safety metrics
        avg_incident_frequency = statistics.mean(incident_frequencies) if incident_frequencies else 0.0
        avg_safety_recovery_rate = statistics.mean(safety_recovery_rates) if safety_recovery_rates else 0.0
        avg_violation_severity = statistics.mean(violation_severity_scores) if violation_severity_scores else 0.0
        
        # Safety trend analysis
        safety_trend = self._calculate_safety_trend(evaluation_results)
        
        return {
            'safety_incidents': total_safety_incidents,
            'policy_violations': total_policy_violations,
            'incident_types': dict(safety_incident_types),
            'incident_frequency': avg_incident_frequency,
            'safety_recovery_rate': avg_safety_recovery_rate,
            'violation_severity': avg_violation_severity,
            'safety_trend': safety_trend,
            'safety_compliance_rate': self._calculate_safety_compliance_rate(evaluation_results)
        }
    
    # Helper methods for advanced metrics
    
    def _calculate_advanced_edit_churn(self, turn_results: List[TurnResult]) -> Dict[str, float]:
        """Calculate advanced edit churn with efficiency metrics."""
        total_edits = 0
        final_state_edits = 0
        effective_edits = 0
        
        file_modifications = defaultdict(list)
        
        for i, turn in enumerate(turn_results):
            if turn.info and 'files_changed' in turn.info:
                files_changed = turn.info['files_changed']
                if isinstance(files_changed, list):
                    total_edits += len(files_changed)
                    for file_path in files_changed:
                        file_modifications[file_path].append(i)
        
        # Calculate final state edits and effective edits
        for file_path, edit_turns in file_modifications.items():
            final_state_edits += 1
            # Effective edits are those that contribute to final state
            if len(edit_turns) > 0:
                effective_edits += 1
        
        churn = total_edits / final_state_edits if final_state_edits > 0 else 0.0
        efficiency = effective_edits / total_edits if total_edits > 0 else 0.0
        
        return {
            'churn': churn,
            'efficiency': efficiency
        }
    
    def _analyze_file_modifications(self, turn_results: List[TurnResult]) -> Dict[str, Any]:
        """Analyze file modification patterns."""
        file_modifications = defaultdict(int)
        modification_patterns = defaultdict(int)
        
        for turn in turn_results:
            if turn.info and 'files_changed' in turn.info:
                files_changed = turn.info['files_changed']
                if isinstance(files_changed, list):
                    for file_path in files_changed:
                        file_modifications[file_path] += 1
                        
                        # Analyze modification patterns
                        if file_path.endswith('.py'):
                            modification_patterns['python_file'] += 1
                        elif file_path.endswith('.js'):
                            modification_patterns['javascript_file'] += 1
                        elif file_path.endswith('.java'):
                            modification_patterns['java_file'] += 1
                        else:
                            modification_patterns['other_file'] += 1
        
        return {
            'unique_files': len(file_modifications),
            'total_modifications': sum(file_modifications.values()),
            'patterns': dict(modification_patterns),
            'file_modification_counts': dict(file_modifications)
        }
    
    def _calculate_rollback_frequency(self, turn_results: List[TurnResult]) -> float:
        """Calculate frequency of rollbacks or undoing changes."""
        rollback_indicators = 0
        total_turns = len(turn_results)
        
        for i in range(1, len(turn_results)):
            current_turn = turn_results[i]
            previous_turn = turn_results[i-1]
            
            # Check for rollback indicators
            if (current_turn.info and previous_turn.info and
                'files_changed' in current_turn.info and 'files_changed' in previous_turn.info):
                
                current_files = set(current_turn.info['files_changed'])
                previous_files = set(previous_turn.info['files_changed'])
                
                # If we're modifying the same files again, it might be a rollback
                if current_files.intersection(previous_files) and current_turn.reward < previous_turn.reward:
                    rollback_indicators += 1
        
        return rollback_indicators / total_turns if total_turns > 0 else 0.0
    
    def _calculate_file_complexity_impact(self, evaluation_results: List[EvaluationResult]) -> float:
        """Calculate impact of file complexity on performance."""
        complexity_scores = []
        
        for result in evaluation_results:
            file_count = self._count_files_touched(result.turn_results)
            turn_count = result.total_turns
            
            # Simple complexity score based on files touched vs turns taken
            if file_count > 0:
                complexity_impact = turn_count / file_count
                complexity_scores.append(complexity_impact)
        
        return statistics.mean(complexity_scores) if complexity_scores else 0.0
    
    def _calculate_advanced_recovery_rate(self, turn_results: List[TurnResult]) -> Dict[str, float]:
        """Calculate advanced recovery metrics."""
        error_turns = []
        recovery_turns = []
        adaptation_times = []
        
        for i, turn in enumerate(turn_results):
            # Identify error turns
            if turn.reward < 0 or (turn.info and turn.info.get('error')):
                error_turns.append(i)
            
            # Identify recovery turns and measure adaptation time
            if (turn.reward > 0 and i > 0 and 
                turn_results[i-1].reward < 0):
                recovery_turns.append(i)
                
                # Find the start of the error sequence
                error_start = i - 1
                while error_start > 0 and turn_results[error_start-1].reward < 0:
                    error_start -= 1
                
                adaptation_time = i - error_start
                adaptation_times.append(adaptation_time)
        
        recovery_rate = len(recovery_turns) / len(error_turns) if error_turns else 1.0
        
        # Error resilience: ability to maintain performance despite errors
        if len(turn_results) > 0:
            positive_rewards = sum(1 for turn in turn_results if turn.reward > 0)
            error_resilience = positive_rewards / len(turn_results)
        else:
            error_resilience = 0.0
        
        # Adaptation speed: how quickly recovery happens
        avg_adaptation_speed = 1.0 / statistics.mean(adaptation_times) if adaptation_times else 0.0
        
        return {
            'rate': recovery_rate,
            'resilience': error_resilience,
            'adaptation_speed': avg_adaptation_speed
        }
    
    def _calculate_advanced_stability_score(self, turn_results: List[TurnResult]) -> Dict[str, float]:
        """Calculate advanced stability metrics."""
        if len(turn_results) <= 1:
            return {'score': 1.0, 'consistency': 1.0}
        
        rewards = [turn.reward for turn in turn_results]
        execution_times = [turn.execution_time for turn in turn_results]
        
        # Reward stability
        reward_cv = 0.0
        if rewards and statistics.mean(rewards) != 0:
            try:
                reward_cv = statistics.stdev(rewards) / abs(statistics.mean(rewards))
            except (statistics.StatisticsError, ZeroDivisionError):
                reward_cv = 0.0
        
        reward_stability = 1.0 / (1.0 + reward_cv)
        
        # Execution time consistency
        time_cv = 0.0
        if execution_times and statistics.mean(execution_times) != 0:
            try:
                time_cv = statistics.stdev(execution_times) / statistics.mean(execution_times)
            except (statistics.StatisticsError, ZeroDivisionError):
                time_cv = 0.0
        
        time_consistency = 1.0 / (1.0 + time_cv)
        
        # Overall consistency score
        consistency = (reward_stability + time_consistency) / 2.0
        
        return {
            'score': reward_stability,
            'consistency': consistency
        }
    
    def _extract_failure_patterns(self, turn_results: List[TurnResult]) -> List[str]:
        """Extract failure patterns from turn results."""
        patterns = []
        
        for turn in turn_results:
            if turn.reward < 0 or (turn.info and turn.info.get('error')):
                if turn.info and 'error' in turn.info:
                    error_type = turn.info['error']
                    patterns.append(error_type)
                elif turn.safety_violations:
                    patterns.extend(turn.safety_violations)
                else:
                    patterns.append('unknown_failure')
        
        return patterns
    
    def _calculate_pattern_diversity(self, patterns: List[str]) -> float:
        """Calculate diversity of failure patterns."""
        if not patterns:
            return 0.0
        
        pattern_counts = Counter(patterns)
        total_patterns = len(patterns)
        unique_patterns = len(pattern_counts)
        
        # Shannon diversity index
        diversity = 0.0
        for count in pattern_counts.values():
            p = count / total_patterns
            if p > 0:
                diversity -= p * math.log2(p)
        
        # Normalize by maximum possible diversity
        max_diversity = math.log2(unique_patterns) if unique_patterns > 1 else 1.0
        normalized_diversity = diversity / max_diversity if max_diversity > 0 else 0.0
        
        return normalized_diversity
    
    def _calculate_resource_utilization(self, turn_results: List[TurnResult]) -> float:
        """Calculate resource utilization efficiency."""
        if not turn_results:
            return 0.0
        
        total_time = sum(turn.execution_time for turn in turn_results)
        total_tokens = sum(turn.tokens_used for turn in turn_results)
        
        # Simple utilization score based on time and token efficiency
        if total_time > 0 and total_tokens > 0:
            time_efficiency = len(turn_results) / total_time  # turns per second
            token_efficiency = len(turn_results) / total_tokens  # turns per token
            
            # Normalize and combine
            utilization = (time_efficiency * 100 + token_efficiency * 1000) / 2
            return min(utilization, 1.0)  # Cap at 1.0
        
        return 0.0
    
    def _calculate_time_to_first_success(self, turn_results: List[TurnResult]) -> float:
        """Calculate time to first successful action."""
        for i, turn in enumerate(turn_results):
            if turn.reward > 0:
                return sum(t.execution_time for t in turn_results[:i+1])
        
        # If no success, return total time
        return sum(turn.execution_time for turn in turn_results)
    
    def _calculate_safety_recovery_rate(self, turn_results: List[TurnResult]) -> float:
        """Calculate rate of recovery after safety incidents."""
        safety_incidents = []
        recoveries = []
        
        for i, turn in enumerate(turn_results):
            if turn.safety_violations:
                safety_incidents.append(i)
            
            # Check for recovery after safety incident
            if (i > 0 and turn_results[i-1].safety_violations and 
                not turn.safety_violations and turn.reward >= 0):
                recoveries.append(i)
        
        return len(recoveries) / len(safety_incidents) if safety_incidents else 1.0
    
    def _calculate_violation_severity(self, violations: List[str]) -> float:
        """Calculate severity score for safety violations."""
        if not violations:
            return 0.0
        
        # Define severity weights for different violation types
        severity_weights = {
            'dangerous_command': 1.0,
            'file_system_violation': 0.8,
            'network_violation': 0.6,
            'resource_violation': 0.4,
            'unsafe_command': 0.7,
            'policy_violation': 0.5
        }
        
        total_severity = 0.0
        for violation in violations:
            severity = severity_weights.get(violation, 0.3)  # Default severity
            total_severity += severity
        
        # Normalize by number of violations
        return total_severity / len(violations)
    
    def _calculate_safety_trend(self, evaluation_results: List[EvaluationResult]) -> float:
        """Calculate safety trend over time."""
        if len(evaluation_results) < 2:
            return 0.0
        
        # Sort by start time
        sorted_results = sorted(evaluation_results, key=lambda x: x.start_time)
        
        safety_scores = []
        for result in sorted_results:
            # Calculate safety score for each evaluation
            total_violations = sum(len(turn.safety_violations) for turn in result.turn_results)
            safety_score = 1.0 / (1.0 + total_violations)  # Higher score = safer
            safety_scores.append(safety_score)
        
        # Calculate trend (positive = improving, negative = degrading)
        if len(safety_scores) >= 2:
            first_half = safety_scores[:len(safety_scores)//2]
            second_half = safety_scores[len(safety_scores)//2:]
            
            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            
            trend = second_avg - first_avg
            return trend
        
        return 0.0
    
    def _calculate_safety_compliance_rate(self, evaluation_results: List[EvaluationResult]) -> float:
        """Calculate overall safety compliance rate."""
        total_evaluations = len(evaluation_results)
        if total_evaluations == 0:
            return 1.0
        
        safe_evaluations = sum(1 for result in evaluation_results 
                             if result.termination_reason != TerminationReason.SAFETY_VIOLATION)
        
        return safe_evaluations / total_evaluations
    
    # Metrics Aggregation and Reporting (Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6)
    
    def aggregate_metrics_across_runs(self, 
                                    multiple_run_results: List[List[EvaluationResult]],
                                    run_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Aggregate metrics across multiple evaluation runs.
        
        Args:
            multiple_run_results: List of evaluation result lists (one per run)
            run_labels: Optional labels for each run
            
        Returns:
            Dictionary with aggregated metrics and statistical analysis
            
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
        """
        if not multiple_run_results:
            return {'error': 'No evaluation runs provided'}
        
        if run_labels is None:
            run_labels = [f"Run_{i+1}" for i in range(len(multiple_run_results))]
        
        # Calculate metrics for each run
        run_metrics = []
        for i, run_results in enumerate(multiple_run_results):
            if run_results:
                metrics = self.calculate_all_metrics(run_results)
                run_metrics.append({
                    'run_label': run_labels[i],
                    'metrics': metrics,
                    'num_evaluations': len(run_results),
                    'success_rate': sum(1 for r in run_results if r.success) / len(run_results)
                })
        
        if not run_metrics:
            return {'error': 'No valid runs with results'}
        
        # Aggregate across runs
        aggregated_data = self._aggregate_run_metrics(run_metrics)
        
        # Statistical analysis
        statistical_analysis = self._perform_statistical_analysis(run_metrics)
        
        # Trend detection
        trend_analysis = self._detect_trends(run_metrics)
        
        # Performance comparison
        performance_comparison = self._compare_run_performance(run_metrics)
        
        return {
            'summary': {
                'total_runs': len(run_metrics),
                'total_evaluations': sum(rm['num_evaluations'] for rm in run_metrics),
                'overall_success_rate': statistics.mean([rm['success_rate'] for rm in run_metrics])
            },
            'aggregated_metrics': aggregated_data,
            'statistical_analysis': statistical_analysis,
            'trend_analysis': trend_analysis,
            'performance_comparison': performance_comparison,
            'run_details': run_metrics
        }
    
    def generate_comprehensive_report(self, 
                                    evaluation_results: List[EvaluationResult],
                                    report_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive metrics report with analysis and insights.
        
        Args:
            evaluation_results: List of evaluation results to analyze
            report_config: Optional configuration for report generation
            
        Returns:
            Comprehensive report dictionary
        """
        if report_config is None:
            report_config = self._get_default_report_config()
        
        # Basic metrics
        basic_metrics = self.calculate_all_metrics(evaluation_results)
        
        # Advanced metrics if enabled
        advanced_metrics = {}
        if report_config.get('include_advanced_metrics', True):
            advanced_metrics = {
                'repair_quality': self.calculate_advanced_repair_quality_metrics(evaluation_results),
                'robustness': self.calculate_advanced_robustness_metrics(evaluation_results),
                'cost': self.calculate_advanced_cost_metrics(evaluation_results),
                'safety': self.calculate_advanced_safety_metrics(evaluation_results)
            }
        
        # Performance insights
        insights = self._generate_performance_insights(evaluation_results, basic_metrics, advanced_metrics)
        
        # Threshold analysis
        threshold_analysis = self._analyze_metric_thresholds(basic_metrics, report_config.get('thresholds', {}))
        
        # Recommendations
        recommendations = self._generate_recommendations(basic_metrics, advanced_metrics, threshold_analysis)
        
        # Executive summary
        executive_summary = self._generate_executive_summary(
            evaluation_results, basic_metrics, advanced_metrics, insights
        )
        
        return {
            'executive_summary': executive_summary,
            'basic_metrics': basic_metrics.to_dict(),
            'advanced_metrics': advanced_metrics,
            'performance_insights': insights,
            'threshold_analysis': threshold_analysis,
            'recommendations': recommendations,
            'metadata': {
                'report_generated_at': datetime.now().isoformat(),
                'total_evaluations': len(evaluation_results),
                'report_config': report_config
            }
        }
    
    def detect_performance_anomalies(self, 
                                   evaluation_results: List[EvaluationResult],
                                   baseline_metrics: Optional[AggregatedMetrics] = None,
                                   sensitivity: float = 2.0) -> Dict[str, Any]:
        """
        Detect performance anomalies in evaluation results.
        
        Args:
            evaluation_results: List of evaluation results to analyze
            baseline_metrics: Optional baseline metrics for comparison
            sensitivity: Sensitivity threshold for anomaly detection (standard deviations)
            
        Returns:
            Dictionary with detected anomalies and analysis
        """
        current_metrics = self.calculate_all_metrics(evaluation_results)
        
        anomalies = {
            'detected_anomalies': [],
            'severity_levels': {},
            'affected_metrics': [],
            'analysis': {}
        }
        
        if baseline_metrics is None:
            # Use historical data if available
            if len(self.calculation_history) > 1:
                baseline_metrics = self._calculate_baseline_from_history()
            else:
                # No baseline available, perform internal anomaly detection
                return self._detect_internal_anomalies(evaluation_results, sensitivity)
        
        # Compare current metrics with baseline
        metric_comparisons = self._compare_metrics_with_baseline(current_metrics, baseline_metrics, sensitivity)
        
        for metric_name, comparison in metric_comparisons.items():
            if comparison['is_anomaly']:
                anomaly = {
                    'metric': metric_name,
                    'current_value': comparison['current_value'],
                    'baseline_value': comparison['baseline_value'],
                    'deviation': comparison['deviation'],
                    'severity': comparison['severity'],
                    'direction': comparison['direction']  # 'higher' or 'lower'
                }
                anomalies['detected_anomalies'].append(anomaly)
                anomalies['affected_metrics'].append(metric_name)
                anomalies['severity_levels'][metric_name] = comparison['severity']
        
        # Generate analysis
        anomalies['analysis'] = self._analyze_anomalies(anomalies['detected_anomalies'])
        
        return anomalies
    
    def configure_metric_thresholds(self, 
                                  thresholds: Dict[str, Dict[str, float]]) -> None:
        """
        Configure metric thresholds for alerting and analysis.
        
        Args:
            thresholds: Dictionary of metric thresholds
                       Format: {metric_name: {'warning': value, 'critical': value}}
        """
        self.metric_thresholds = thresholds
        logger.info(f"Configured thresholds for {len(thresholds)} metrics")
    
    def check_metric_thresholds(self, 
                              metrics: AggregatedMetrics) -> Dict[str, Any]:
        """
        Check metrics against configured thresholds.
        
        Args:
            metrics: Aggregated metrics to check
            
        Returns:
            Dictionary with threshold violations and alerts
        """
        if not hasattr(self, 'metric_thresholds'):
            return {'alerts': [], 'violations': {}}
        
        alerts = []
        violations = {}
        
        metrics_dict = metrics.to_dict()
        
        for metric_name, thresholds in self.metric_thresholds.items():
            if metric_name in metrics_dict:
                current_value = metrics_dict[metric_name]
                
                # Check critical threshold first
                if 'critical' in thresholds:
                    if self._exceeds_threshold(current_value, thresholds['critical'], metric_name):
                        alert = {
                            'level': 'critical',
                            'metric': metric_name,
                            'current_value': current_value,
                            'threshold': thresholds['critical'],
                            'message': f"Critical threshold exceeded for {metric_name}"
                        }
                        alerts.append(alert)
                        violations[metric_name] = 'critical'
                        continue  # Skip warning check if critical is exceeded
                
                # Check warning threshold only if critical wasn't exceeded
                if 'warning' in thresholds:
                    if self._exceeds_threshold(current_value, thresholds['warning'], metric_name):
                        alert = {
                            'level': 'warning',
                            'metric': metric_name,
                            'current_value': current_value,
                            'threshold': thresholds['warning'],
                            'message': f"Warning threshold exceeded for {metric_name}"
                        }
                        alerts.append(alert)
                        violations[metric_name] = 'warning'
        
        return {
            'alerts': alerts,
            'violations': violations,
            'total_alerts': len(alerts),
            'critical_alerts': len([a for a in alerts if a['level'] == 'critical']),
            'warning_alerts': len([a for a in alerts if a['level'] == 'warning'])
        }
    
    # Helper methods for aggregation and reporting
    
    def _aggregate_run_metrics(self, run_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate metrics across multiple runs."""
        if not run_metrics:
            return {}
        
        # Extract all metric values
        all_metrics = {}
        for run_data in run_metrics:
            metrics_dict = run_data['metrics'].to_dict()
            for metric_name, value in metrics_dict.items():
                if metric_name not in all_metrics:
                    all_metrics[metric_name] = []
                all_metrics[metric_name].append(value)
        
        # Calculate aggregated statistics
        aggregated = {}
        for metric_name, values in all_metrics.items():
            if values:
                aggregated[metric_name] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
                    'min': min(values),
                    'max': max(values),
                    'range': max(values) - min(values),
                    'coefficient_of_variation': (statistics.stdev(values) / statistics.mean(values)) if len(values) > 1 and statistics.mean(values) != 0 else 0.0
                }
        
        return aggregated
    
    def _perform_statistical_analysis(self, run_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform statistical analysis on run metrics."""
        if len(run_metrics) < 2:
            return {'note': 'Insufficient data for statistical analysis (need at least 2 runs)'}
        
        # Extract success rates for analysis
        success_rates = [rm['success_rate'] for rm in run_metrics]
        
        # Basic statistical tests
        analysis = {
            'success_rate_analysis': {
                'mean': statistics.mean(success_rates),
                'std_dev': statistics.stdev(success_rates),
                'confidence_interval_95': self._calculate_confidence_interval(success_rates, 0.95),
                'is_consistent': statistics.stdev(success_rates) < 0.1  # Less than 10% variation
            },
            'run_consistency': self._analyze_run_consistency(run_metrics),
            'performance_stability': self._analyze_performance_stability(run_metrics)
        }
        
        return analysis
    
    def _detect_trends(self, run_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect trends in metrics across runs."""
        if len(run_metrics) < 3:
            return {'note': 'Insufficient data for trend detection (need at least 3 runs)'}
        
        trends = {}
        
        # Analyze success rate trend
        success_rates = [rm['success_rate'] for rm in run_metrics]
        success_trend = self._calculate_trend(success_rates)
        trends['success_rate_trend'] = success_trend
        
        # Analyze key metrics trends
        key_metrics = ['resolved_percentage', 'avg_turns', 'cost_per_solved', 'safety_incidents']
        
        for metric_name in key_metrics:
            values = []
            for rm in run_metrics:
                metrics_dict = rm['metrics'].to_dict()
                if metric_name in metrics_dict:
                    values.append(metrics_dict[metric_name])
            
            if len(values) >= 3:
                trend = self._calculate_trend(values)
                trends[f'{metric_name}_trend'] = trend
        
        return trends
    
    def _compare_run_performance(self, run_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare performance across runs."""
        if len(run_metrics) < 2:
            return {'note': 'Need at least 2 runs for comparison'}
        
        # Find best and worst performing runs
        success_rates = [(i, rm['success_rate']) for i, rm in enumerate(run_metrics)]
        success_rates.sort(key=lambda x: x[1], reverse=True)
        
        best_run_idx = success_rates[0][0]
        worst_run_idx = success_rates[-1][0]
        
        best_run = run_metrics[best_run_idx]
        worst_run = run_metrics[worst_run_idx]
        
        comparison = {
            'best_run': {
                'label': best_run['run_label'],
                'success_rate': best_run['success_rate'],
                'metrics': best_run['metrics'].to_dict()
            },
            'worst_run': {
                'label': worst_run['run_label'],
                'success_rate': worst_run['success_rate'],
                'metrics': worst_run['metrics'].to_dict()
            },
            'performance_gap': best_run['success_rate'] - worst_run['success_rate'],
            'improvement_potential': self._calculate_improvement_potential(best_run, worst_run)
        }
        
        return comparison
    
    def _get_default_report_config(self) -> Dict[str, Any]:
        """Get default configuration for report generation."""
        return {
            'include_advanced_metrics': True,
            'include_insights': True,
            'include_recommendations': True,
            'thresholds': {
                'resolved_percentage': {'warning': 70.0, 'critical': 50.0},
                'safety_incidents': {'warning': 5, 'critical': 10},
                'avg_turns': {'warning': 15, 'critical': 25},
                'cost_per_solved': {'warning': 1.0, 'critical': 2.0}
            }
        }
    
    def _generate_performance_insights(self, 
                                     evaluation_results: List[EvaluationResult],
                                     basic_metrics: AggregatedMetrics,
                                     advanced_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance insights from metrics."""
        insights = []
        
        # Success rate insights
        if basic_metrics.resolved_percentage < 50.0:
            insights.append({
                'type': 'performance',
                'severity': 'high',
                'title': 'Low Success Rate',
                'description': f'Success rate of {basic_metrics.resolved_percentage:.1f}% is below acceptable threshold',
                'recommendation': 'Review task complexity and model capabilities'
            })
        
        # Efficiency insights
        if basic_metrics.avg_turns > 10:
            insights.append({
                'type': 'efficiency',
                'severity': 'medium',
                'title': 'High Turn Count',
                'description': f'Average turns of {basic_metrics.avg_turns:.1f} indicates potential inefficiency',
                'recommendation': 'Optimize task decomposition and feedback processing'
            })
        
        # Safety insights
        if basic_metrics.safety_incidents > 0:
            insights.append({
                'type': 'safety',
                'severity': 'high',
                'title': 'Safety Incidents Detected',
                'description': f'{basic_metrics.safety_incidents} safety incidents occurred',
                'recommendation': 'Review and strengthen safety controls'
            })
        
        # Cost insights
        if basic_metrics.cost_per_solved > 1.0:
            insights.append({
                'type': 'cost',
                'severity': 'medium',
                'title': 'High Cost per Solution',
                'description': f'Cost of ${basic_metrics.cost_per_solved:.3f} per solved task is above target',
                'recommendation': 'Optimize token usage and reduce redundant operations'
            })
        
        return insights
    
    def _analyze_metric_thresholds(self, 
                                 metrics: AggregatedMetrics,
                                 thresholds: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Analyze metrics against thresholds."""
        if not thresholds:
            return {'note': 'No thresholds configured'}
        
        # Set thresholds first
        self.configure_metric_thresholds(thresholds)
        threshold_results = self.check_metric_thresholds(metrics)
        
        # Add analysis
        analysis = {
            'threshold_violations': threshold_results,
            'compliance_rate': 1.0 - (len(threshold_results['violations']) / len(thresholds)) if thresholds else 1.0,
            'risk_level': 'high' if threshold_results.get('critical_alerts', 0) > 0 else 'medium' if threshold_results.get('warning_alerts', 0) > 0 else 'low'
        }
        
        return analysis
    
    def _generate_recommendations(self, 
                                basic_metrics: AggregatedMetrics,
                                advanced_metrics: Dict[str, Any],
                                threshold_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []
        
        # Performance recommendations
        if basic_metrics.resolved_percentage < 70.0:
            recommendations.append({
                'category': 'performance',
                'priority': 'high',
                'title': 'Improve Success Rate',
                'description': 'Success rate is below target',
                'actions': [
                    'Review task difficulty and model capabilities',
                    'Improve prompt engineering and context management',
                    'Consider model fine-tuning for specific task types'
                ]
            })
        
        # Efficiency recommendations
        if basic_metrics.redundancy_rate > 0.2:
            recommendations.append({
                'category': 'efficiency',
                'priority': 'medium',
                'title': 'Reduce Redundancy',
                'description': f'Redundancy rate of {basic_metrics.redundancy_rate:.1%} indicates repeated actions',
                'actions': [
                    'Implement better action tracking and prevention',
                    'Improve feedback processing to avoid repeated mistakes',
                    'Add context retention mechanisms'
                ]
            })
        
        # Safety recommendations
        if basic_metrics.safety_incidents > 0:
            recommendations.append({
                'category': 'safety',
                'priority': 'critical',
                'title': 'Address Safety Issues',
                'description': f'{basic_metrics.safety_incidents} safety incidents detected',
                'actions': [
                    'Review and update safety policies',
                    'Implement stricter command filtering',
                    'Add additional safety training for models'
                ]
            })
        
        return recommendations
    
    def _generate_executive_summary(self, 
                                  evaluation_results: List[EvaluationResult],
                                  basic_metrics: AggregatedMetrics,
                                  advanced_metrics: Dict[str, Any],
                                  insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate executive summary of evaluation results."""
        total_evaluations = len(evaluation_results)
        successful_evaluations = sum(1 for r in evaluation_results if r.success)
        
        # Overall assessment
        if basic_metrics.resolved_percentage >= 80.0:
            overall_assessment = 'Excellent'
        elif basic_metrics.resolved_percentage >= 60.0:
            overall_assessment = 'Good'
        elif basic_metrics.resolved_percentage >= 40.0:
            overall_assessment = 'Fair'
        else:
            overall_assessment = 'Poor'
        
        # Key findings
        key_findings = []
        if basic_metrics.resolved_percentage > 0:
            key_findings.append(f"Successfully resolved {basic_metrics.resolved_percentage:.1f}% of tasks")
        if basic_metrics.avg_turns > 0:
            key_findings.append(f"Average of {basic_metrics.avg_turns:.1f} turns per task")
        if basic_metrics.safety_incidents > 0:
            key_findings.append(f"{basic_metrics.safety_incidents} safety incidents occurred")
        
        # Critical issues
        critical_issues = [insight for insight in insights if insight.get('severity') == 'high']
        
        return {
            'overall_assessment': overall_assessment,
            'success_rate': basic_metrics.resolved_percentage,
            'total_evaluations': total_evaluations,
            'successful_evaluations': successful_evaluations,
            'key_findings': key_findings,
            'critical_issues': len(critical_issues),
            'primary_concerns': [issue['title'] for issue in critical_issues[:3]],  # Top 3
            'recommendation_summary': f"Focus on {'safety improvements' if basic_metrics.safety_incidents > 0 else 'performance optimization'}"
        }
    
    def _calculate_confidence_interval(self, values: List[float], confidence: float) -> Tuple[float, float]:
        """Calculate confidence interval for a list of values."""
        if len(values) < 2:
            mean_val = values[0] if values else 0.0
            return (mean_val, mean_val)
        
        mean_val = statistics.mean(values)
        std_dev = statistics.stdev(values)
        n = len(values)
        
        # Use t-distribution for small samples
        if n < 30:
            # Simplified t-value approximation
            t_value = 2.0 if confidence >= 0.95 else 1.5
        else:
            # Normal distribution
            t_value = 1.96 if confidence >= 0.95 else 1.645
        
        margin_of_error = t_value * (std_dev / math.sqrt(n))
        
        return (mean_val - margin_of_error, mean_val + margin_of_error)
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and strength."""
        if len(values) < 3:
            return {'direction': 'insufficient_data', 'strength': 0.0}
        
        # Simple linear trend calculation
        n = len(values)
        x = list(range(n))
        
        # Calculate slope
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator
        
        # Determine direction and strength
        if abs(slope) < 0.01:
            direction = 'stable'
            strength = 0.0
        elif slope > 0:
            direction = 'improving'
            strength = min(abs(slope) * 10, 1.0)  # Normalize to 0-1
        else:
            direction = 'declining'
            strength = min(abs(slope) * 10, 1.0)
        
        return {
            'direction': direction,
            'strength': strength,
            'slope': slope
        }
    
    def _exceeds_threshold(self, value: float, threshold: float, metric_name: str) -> bool:
        """Check if a metric value exceeds its threshold."""
        # For metrics where lower is better
        lower_is_better = ['avg_turns', 'cost_per_solved', 'safety_incidents', 'redundancy_rate']
        
        if metric_name in lower_is_better:
            return value > threshold
        else:
            # For metrics where higher is better
            return value < threshold
    
    def _analyze_run_consistency(self, run_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze consistency across runs."""
        success_rates = [rm['success_rate'] for rm in run_metrics]
        
        cv = statistics.stdev(success_rates) / statistics.mean(success_rates) if statistics.mean(success_rates) > 0 else 0.0
        
        if cv < 0.1:
            consistency_level = 'high'
        elif cv < 0.3:
            consistency_level = 'medium'
        else:
            consistency_level = 'low'
        
        return {
            'consistency_level': consistency_level,
            'coefficient_of_variation': cv,
            'success_rate_range': max(success_rates) - min(success_rates)
        }
    
    def _analyze_performance_stability(self, run_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance stability across runs."""
        # Extract key metrics for stability analysis
        key_metrics = ['resolved_percentage', 'avg_turns', 'safety_incidents']
        stability_scores = []
        
        for metric_name in key_metrics:
            values = []
            for rm in run_metrics:
                metrics_dict = rm['metrics'].to_dict()
                if metric_name in metrics_dict:
                    values.append(metrics_dict[metric_name])
            
            if len(values) > 1 and statistics.mean(values) > 0:
                cv = statistics.stdev(values) / statistics.mean(values)
                stability_score = 1.0 / (1.0 + cv)  # Higher score = more stable
                stability_scores.append(stability_score)
        
        overall_stability = statistics.mean(stability_scores) if stability_scores else 0.0
        
        return {
            'overall_stability_score': overall_stability,
            'stability_level': 'high' if overall_stability > 0.8 else 'medium' if overall_stability > 0.6 else 'low'
        }
    
    def _calculate_improvement_potential(self, best_run: Dict[str, Any], worst_run: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate improvement potential based on best vs worst run."""
        best_metrics = best_run['metrics'].to_dict()
        worst_metrics = worst_run['metrics'].to_dict()
        
        improvements = {}
        for metric_name in best_metrics:
            if metric_name in worst_metrics:
                best_val = best_metrics[metric_name]
                worst_val = worst_metrics[metric_name]
                
                if worst_val != 0:
                    improvement_pct = ((best_val - worst_val) / worst_val) * 100
                    improvements[metric_name] = improvement_pct
        
        return improvements
    
    def _calculate_baseline_from_history(self) -> AggregatedMetrics:
        """Calculate baseline metrics from calculation history."""
        if not self.calculation_history:
            return AggregatedMetrics()
        
        # Use the most recent historical metrics as baseline
        recent_history = self.calculation_history[-5:]  # Last 5 calculations
        
        # Average the metrics
        all_metrics = defaultdict(list)
        for entry in recent_history:
            metrics = entry.get('metrics', {})
            for metric_name, value in metrics.items():
                all_metrics[metric_name].append(value)
        
        # Calculate averages
        baseline_data = {}
        for metric_name, values in all_metrics.items():
            if values:
                baseline_data[metric_name] = statistics.mean(values)
        
        return AggregatedMetrics.from_dict(baseline_data)
    
    def _detect_internal_anomalies(self, 
                                 evaluation_results: List[EvaluationResult],
                                 sensitivity: float) -> Dict[str, Any]:
        """Detect anomalies within the current evaluation set."""
        if len(evaluation_results) < 5:
            return {'note': 'Insufficient data for internal anomaly detection'}
        
        # Calculate metrics for each evaluation
        individual_metrics = []
        for result in evaluation_results:
            metrics = self.calculate_single_evaluation_metrics(result)
            individual_metrics.append(metrics.to_dict())
        
        # Detect outliers using IQR method
        anomalies = {'detected_anomalies': [], 'analysis': {}}
        
        key_metrics = ['resolved_percentage', 'avg_turns', 'cost_per_solved']
        
        for metric_name in key_metrics:
            values = [m.get(metric_name, 0) for m in individual_metrics]
            outliers = self._detect_outliers_iqr(values, sensitivity)
            
            for outlier_idx in outliers:
                anomaly = {
                    'evaluation_id': evaluation_results[outlier_idx].evaluation_id,
                    'metric': metric_name,
                    'value': values[outlier_idx],
                    'type': 'internal_outlier'
                }
                anomalies['detected_anomalies'].append(anomaly)
        
        return anomalies
    
    def _compare_metrics_with_baseline(self, 
                                     current_metrics: AggregatedMetrics,
                                     baseline_metrics: AggregatedMetrics,
                                     sensitivity: float) -> Dict[str, Dict[str, Any]]:
        """Compare current metrics with baseline."""
        current_dict = current_metrics.to_dict()
        baseline_dict = baseline_metrics.to_dict()
        
        comparisons = {}
        
        for metric_name in current_dict:
            if metric_name in baseline_dict:
                current_val = current_dict[metric_name]
                baseline_val = baseline_dict[metric_name]
                
                if baseline_val != 0:
                    deviation = abs(current_val - baseline_val) / baseline_val
                    is_anomaly = deviation > (sensitivity * 0.1)  # 10% threshold per sensitivity unit
                    
                    severity = 'critical' if deviation > 0.5 else 'high' if deviation > 0.3 else 'medium'
                    direction = 'higher' if current_val > baseline_val else 'lower'
                    
                    comparisons[metric_name] = {
                        'current_value': current_val,
                        'baseline_value': baseline_val,
                        'deviation': deviation,
                        'is_anomaly': is_anomaly,
                        'severity': severity,
                        'direction': direction
                    }
        
        return comparisons
    
    def _analyze_anomalies(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze detected anomalies for patterns and insights."""
        if not anomalies:
            return {'summary': 'No anomalies detected'}
        
        # Group by metric
        by_metric = defaultdict(list)
        for anomaly in anomalies:
            by_metric[anomaly['metric']].append(anomaly)
        
        # Analyze patterns
        analysis = {
            'total_anomalies': len(anomalies),
            'affected_metrics': list(by_metric.keys()),
            'severity_distribution': Counter([a.get('severity', 'unknown') for a in anomalies]),
            'most_affected_metric': max(by_metric.keys(), key=lambda k: len(by_metric[k])) if by_metric else None,
            'patterns': []
        }
        
        # Look for patterns
        if len(anomalies) > 3:
            analysis['patterns'].append('Multiple anomalies detected - investigate systematic issues')
        
        if 'safety_incidents' in by_metric:
            analysis['patterns'].append('Safety-related anomalies detected - review safety controls')
        
        return analysis
    
    def _detect_outliers_iqr(self, values: List[float], sensitivity: float) -> List[int]:
        """Detect outliers using IQR method."""
        if len(values) < 4:
            return []
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - sensitivity * iqr
        upper_bound = q3 + sensitivity * iqr
        
        outliers = []
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                outliers.append(i)
        
        return outliers