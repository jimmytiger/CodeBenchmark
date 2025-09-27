"""Performance Tuning multi-turn task implementation."""

import logging
from typing import Dict, List, Any, Optional
import re
import json

from evaluation_engine.core.extended_tasks import MultiTurnTask, ScenarioConfig, ScenarioType, TurnConfig
from lm_eval.api.registry import register_task
from .. import utils, metrics

eval_logger = logging.getLogger(__name__)


@register_task("multi_turn_scenarios_performance_tuning")
class PerformanceTuningTask(MultiTurnTask):
    """
    Multi-turn performance tuning evaluation task.
    
    This task evaluates a model's ability to conduct systematic performance optimization
    including analysis, bottleneck identification, optimization implementation, and validation.
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    DATASET_NAME = "multi_turn_scenarios_performance_tuning"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize performance tuning task."""
        scenario_config = ScenarioConfig(
            scenario_id="performance_tuning",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=5,
            conversation_timeout=900,
            enable_context_retention=True,
            turns=[
                TurnConfig(
                    turn_id="performance_analysis",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""You are a Performance Engineer analyzing the following performance issue:

**Performance Issue**: {performance_issue}
**Current Metrics**: {current_metrics_text}
**Target Metrics**: {target_metrics_text}
**System Context**: {system_context}

Please conduct a comprehensive performance analysis:
1. Analyze the current performance metrics and identify key problems
2. Hypothesize potential root causes and bottlenecks
3. Prioritize areas for investigation based on impact and likelihood
4. Outline a systematic approach for performance diagnosis
5. Identify tools and techniques needed for deeper analysis
6. Estimate the potential performance improvement opportunities

Present your analysis in a structured format for the engineering team.""",
                    expected_format="performance_analysis",
                    evaluation_metrics=["analysis_depth", "bottleneck_identification", "systematic_approach", "tool_selection"],
                    temperature=0.2,
                    max_tokens=2500
                ),
                TurnConfig(
                    turn_id="bottleneck_identification",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Based on your analysis, detailed profiling has been conducted:

**Your Analysis**: {analysis_summary}
**Profiling Results**: {profiling_results}
**System Monitoring Data**: {monitoring_data}

Please identify and prioritize bottlenecks:
1. Analyze the profiling and monitoring data
2. Identify specific bottlenecks and their impact on performance
3. Quantify the performance cost of each bottleneck
4. Prioritize bottlenecks by potential improvement and implementation effort
5. Explain the root causes behind each bottleneck
6. Recommend specific areas for optimization focus

Focus on actionable insights that will drive the biggest performance gains.""",
                    expected_format="bottleneck_report",
                    depends_on=["performance_analysis"],
                    evaluation_metrics=["bottleneck_accuracy", "impact_assessment", "prioritization_logic", "root_cause_analysis"],
                    temperature=0.2,
                    max_tokens=2200
                ),
                TurnConfig(
                    turn_id="optimization_implementation",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Now implement optimizations for the identified bottlenecks:

**Identified Bottlenecks**: {bottlenecks_summary}
**Priority Areas**: {priority_areas}

Please provide optimization implementations:
1. Design specific optimization strategies for each priority bottleneck
2. Provide code changes, configuration updates, or architectural modifications
3. Explain the rationale behind each optimization approach
4. Estimate the expected performance improvement for each change
5. Identify any trade-offs or risks associated with the optimizations
6. Provide implementation guidelines and best practices

Ensure optimizations are practical and maintainable.""",
                    expected_format="optimization_plan",
                    depends_on=["bottleneck_identification"],
                    evaluation_metrics=["optimization_quality", "implementation_feasibility", "trade_off_awareness", "expected_impact"],
                    temperature=0.2,
                    max_tokens=2800
                ),
                TurnConfig(
                    turn_id="measurement_validation",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""The optimizations have been implemented. Review the results:

**Implemented Optimizations**: {optimizations_summary}
**New Performance Metrics**: {new_metrics}
**Comparison with Targets**: {target_comparison}

Please validate the optimization results:
1. Analyze the performance improvements achieved
2. Compare results against the original targets and expectations
3. Identify any unexpected side effects or regressions
4. Validate that the optimizations are working as intended
5. Recommend additional optimizations if targets are not met
6. Assess the overall success of the performance tuning effort

Provide objective assessment of the optimization outcomes.""",
                    expected_format="validation_report",
                    depends_on=["optimization_implementation"],
                    evaluation_metrics=["measurement_accuracy", "target_assessment", "regression_detection", "success_evaluation"],
                    temperature=0.1,
                    max_tokens=2200
                ),
                TurnConfig(
                    turn_id="monitoring_recommendations",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Provide final recommendations for ongoing performance monitoring:

**Optimization Results**: {validation_results}
**Current Performance State**: {current_state}

Please provide monitoring and maintenance recommendations:
1. Design ongoing monitoring strategy to maintain performance gains
2. Identify key performance indicators to track continuously
3. Set up alerting thresholds for performance degradation
4. Recommend regular performance review processes
5. Document lessons learned and best practices for future optimization
6. Provide guidance for scaling and maintaining optimized performance

Ensure sustainable performance management going forward.""",
                    expected_format="monitoring_strategy",
                    depends_on=["measurement_validation"],
                    evaluation_metrics=["monitoring_strategy_quality", "sustainability_planning", "knowledge_transfer", "proactive_management"],
                    temperature=0.2,
                    max_tokens=2200
                )
            ],
            scenario_metrics=[
                "performance_tuning_effectiveness",
                "systematic_optimization_approach",
                "measurable_improvement_achievement",
                "overall_performance_engineering_score"
            ],
            success_criteria={
                "performance_tuning_effectiveness": 0.7,
                "systematic_optimization_approach": 0.8,
                "measurable_improvement_achievement": 0.6
            }
        )
        
        super().__init__(
            data_dir=data_dir,
            cache_dir=cache_dir,
            download_mode=download_mode,
            config=config,
            scenario_config=scenario_config
        )
        
        self.analyses = []
        self.bottlenecks = []
        self.optimizations = []
        
    def has_training_docs(self) -> bool:
        return False
        
    def has_validation_docs(self) -> bool:
        return False
        
    def has_test_docs(self) -> bool:
        return True
        
    def training_docs(self):
        return []
        
    def validation_docs(self):
        return []
        
    def test_docs(self):
        """Load test documents from scenarios.jsonl."""
        return self._load_docs()
        
    def _load_docs(self):
        """Load documents from scenarios.jsonl file."""
        try:
            dataset_dict = utils.load_dataset(metadata={"scenario": "performance_tuning"})
            if not dataset_dict.get("test"):
                # Create sample scenarios if none exist
                sample_scenarios = utils.create_sample_scenarios("performance_tuning", 5)
                dataset_dict = {"test": sample_scenarios}
            
            dataset = dataset_dict["test"]
            processed_dataset = utils.process_docs(dataset)
            
            eval_logger.info(f"Loaded {len(processed_dataset)} performance tuning scenarios")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load performance tuning dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """Process model results for multi-turn performance tuning."""
        if not results:
            return self._empty_results()
            
        turn_id = self._determine_current_turn(doc)
        prediction = results[0] if results else ""
        
        if turn_id == "performance_analysis":
            return self._process_performance_analysis(doc, prediction)
        elif turn_id == "bottleneck_identification":
            return self._process_bottleneck_identification(doc, prediction)
        elif turn_id == "optimization_implementation":
            return self._process_optimization_implementation(doc, prediction)
        elif turn_id == "measurement_validation":
            return self._process_measurement_validation(doc, prediction)
        elif turn_id == "monitoring_recommendations":
            return self._process_monitoring_recommendations(doc, prediction)
        else:
            return self._empty_results()
    
    def _determine_current_turn(self, doc: Dict[str, Any]) -> str:
        """Determine current turn based on conversation state."""
        turn_count = len(getattr(self, '_conversation_history', []))
        turns = ["performance_analysis", "bottleneck_identification", "optimization_implementation", 
                "measurement_validation", "monitoring_recommendations"]
        return turns[min(turn_count, len(turns) - 1)]
    
    def _process_performance_analysis(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process performance analysis response."""
        self.analyses.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "analysis_depth": self._evaluate_analysis_depth(prediction),
            "bottleneck_identification": self._evaluate_bottleneck_identification(prediction),
            "systematic_approach": self._evaluate_systematic_approach(prediction),
            "tool_selection": self._evaluate_tool_selection(prediction),
            "metrics_interpretation": self._evaluate_metrics_interpretation(prediction),
            "hypothesis_quality": self._evaluate_hypothesis_quality(prediction)
        }
        
        return metrics_result
    
    def _process_bottleneck_identification(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process bottleneck identification response."""
        profiling_data = self._generate_profiling_data(doc)
        self.bottlenecks.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "bottleneck_accuracy": self._evaluate_bottleneck_accuracy(prediction, doc),
            "impact_assessment": self._evaluate_impact_assessment(prediction),
            "prioritization_logic": self._evaluate_prioritization_logic(prediction),
            "root_cause_analysis": self._evaluate_root_cause_analysis(prediction),
            "quantitative_analysis": self._evaluate_quantitative_analysis(prediction)
        }
        
        return metrics_result
    
    def _process_optimization_implementation(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process optimization implementation response."""
        self.optimizations.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "optimization_quality": self._evaluate_optimization_quality(prediction),
            "implementation_feasibility": self._evaluate_implementation_feasibility(prediction),
            "trade_off_awareness": self._evaluate_trade_off_awareness(prediction),
            "expected_impact": self._evaluate_expected_impact(prediction),
            "code_quality": self._evaluate_code_quality(prediction)
        }
        
        return metrics_result
    
    def _process_measurement_validation(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process measurement validation response."""
        new_metrics = self._generate_improved_metrics(doc)
        
        metrics_result = {
            "response": prediction,
            "measurement_accuracy": self._evaluate_measurement_accuracy(prediction),
            "target_assessment": self._evaluate_target_assessment(prediction, doc),
            "regression_detection": self._evaluate_regression_detection(prediction),
            "success_evaluation": self._evaluate_success_evaluation(prediction),
            "objective_assessment": self._evaluate_objective_assessment(prediction)
        }
        
        return metrics_result
    
    def _process_monitoring_recommendations(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process monitoring recommendations response."""
        metrics_result = {
            "response": prediction,
            "monitoring_strategy_quality": self._evaluate_monitoring_strategy_quality(prediction),
            "sustainability_planning": self._evaluate_sustainability_planning(prediction),
            "knowledge_transfer": self._evaluate_knowledge_transfer(prediction),
            "proactive_management": self._evaluate_proactive_management(prediction),
            "long_term_vision": self._evaluate_long_term_vision(prediction)
        }
        
        return metrics_result
    
    def _generate_profiling_data(self, doc: Dict[str, Any]) -> str:
        """Generate realistic profiling data based on the performance issue."""
        issue = doc.get("performance_issue", "")
        
        if "database" in issue.lower() or "query" in issue.lower():
            return "Query execution time: 2.3s average, Index usage: 45%, Lock contention: High on user_data table"
        elif "memory" in issue.lower():
            return "Memory usage: 85% of heap, GC frequency: 12/min, Memory leaks detected in session management"
        elif "api" in issue.lower() or "response" in issue.lower():
            return "API response time: 1.2s p95, Thread pool utilization: 90%, Connection pool exhaustion detected"
        else:
            return "CPU usage: 78% average, I/O wait: 25%, Network latency: 150ms average"
    
    def _generate_improved_metrics(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Generate improved metrics after optimization."""
        current_metrics = doc.get("current_metrics", {})
        target_metrics = doc.get("target_metrics", {})
        
        # Simulate improvement (not reaching full target but showing progress)
        improved_metrics = {}
        for key, current_value in current_metrics.items():
            if key in target_metrics:
                target_value = target_metrics[key]
                # Simulate 60-80% improvement toward target
                improvement_factor = 0.7
                if "ms" in str(current_value) or "time" in key.lower():
                    # For time metrics, lower is better
                    improved_value = current_value - (current_value - target_value) * improvement_factor
                else:
                    # For throughput metrics, higher is better
                    improved_value = current_value + (target_value - current_value) * improvement_factor
                improved_metrics[key] = improved_value
        
        return improved_metrics
    
    def _evaluate_analysis_depth(self, analysis: str) -> float:
        """Evaluate depth of performance analysis."""
        depth_indicators = [
            "performance" in analysis.lower() or "metric" in analysis.lower(),
            "bottleneck" in analysis.lower() or "constraint" in analysis.lower(),
            "root cause" in analysis.lower() or "cause" in analysis.lower(),
            "systematic" in analysis.lower() or "methodical" in analysis.lower(),
            "tool" in analysis.lower() or "profiling" in analysis.lower(),
            "improvement" in analysis.lower() or "optimization" in analysis.lower(),
            len(analysis.split()) > 200,  # Comprehensive analysis
            len(re.findall(r"\d+\.", analysis)) >= 5  # Structured points
        ]
        
        return sum(depth_indicators) / len(depth_indicators)
    
    def _evaluate_bottleneck_identification(self, analysis: str) -> float:
        """Evaluate bottleneck identification quality."""
        bottleneck_indicators = [
            "bottleneck" in analysis.lower() or "constraint" in analysis.lower(),
            "cpu" in analysis.lower() or "memory" in analysis.lower(),
            "database" in analysis.lower() or "query" in analysis.lower(),
            "network" in analysis.lower() or "i/o" in analysis.lower(),
            "thread" in analysis.lower() or "connection" in analysis.lower(),
            "cache" in analysis.lower() or "storage" in analysis.lower()
        ]
        
        return sum(bottleneck_indicators) / len(bottleneck_indicators)
    
    def _evaluate_systematic_approach(self, analysis: str) -> float:
        """Evaluate systematic approach quality."""
        systematic_indicators = [
            "systematic" in analysis.lower() or "methodical" in analysis.lower(),
            "approach" in analysis.lower() or "methodology" in analysis.lower(),
            "step" in analysis.lower() or "phase" in analysis.lower(),
            "prioritize" in analysis.lower() or "priority" in analysis.lower(),
            "diagnose" in analysis.lower() or "investigate" in analysis.lower(),
            len(re.findall(r"\d+\.", analysis)) >= 4  # Structured approach
        ]
        
        return sum(systematic_indicators) / len(systematic_indicators)
    
    def _evaluate_tool_selection(self, analysis: str) -> float:
        """Evaluate tool selection quality."""
        tool_indicators = [
            "tool" in analysis.lower() or "profiler" in analysis.lower(),
            "monitor" in analysis.lower() or "monitoring" in analysis.lower(),
            "benchmark" in analysis.lower() or "test" in analysis.lower(),
            "apm" in analysis.lower() or "observability" in analysis.lower(),
            "metric" in analysis.lower() or "measurement" in analysis.lower()
        ]
        
        return sum(tool_indicators) / len(tool_indicators)
    
    def _evaluate_metrics_interpretation(self, analysis: str) -> float:
        """Evaluate metrics interpretation quality."""
        interpretation_indicators = [
            "interpret" in analysis.lower() or "analyze" in analysis.lower(),
            "indicate" in analysis.lower() or "suggest" in analysis.lower(),
            "pattern" in analysis.lower() or "trend" in analysis.lower(),
            "correlation" in analysis.lower() or "relationship" in analysis.lower(),
            "threshold" in analysis.lower() or "baseline" in analysis.lower()
        ]
        
        return sum(interpretation_indicators) / len(interpretation_indicators)
    
    def _evaluate_hypothesis_quality(self, analysis: str) -> float:
        """Evaluate hypothesis quality."""
        hypothesis_indicators = [
            "hypothesis" in analysis.lower() or "theory" in analysis.lower(),
            "likely" in analysis.lower() or "probable" in analysis.lower(),
            "suspect" in analysis.lower() or "believe" in analysis.lower(),
            "evidence" in analysis.lower() or "indication" in analysis.lower(),
            "test" in analysis.lower() or "validate" in analysis.lower()
        ]
        
        return sum(hypothesis_indicators) / len(hypothesis_indicators)
    
    def _evaluate_bottleneck_accuracy(self, response: str, doc: Dict[str, Any]) -> float:
        """Evaluate accuracy of bottleneck identification."""
        issue = doc.get("performance_issue", "").lower()
        response_lower = response.lower()
        
        # Check if response identifies relevant bottleneck types
        accuracy_indicators = []
        
        if "database" in issue or "query" in issue:
            accuracy_indicators.append("database" in response_lower or "query" in response_lower)
        if "memory" in issue:
            accuracy_indicators.append("memory" in response_lower or "heap" in response_lower)
        if "api" in issue or "response" in issue:
            accuracy_indicators.append("api" in response_lower or "response" in response_lower)
        if "cpu" in issue:
            accuracy_indicators.append("cpu" in response_lower or "processor" in response_lower)
        
        # General accuracy indicators
        accuracy_indicators.extend([
            "bottleneck" in response_lower,
            "identify" in response_lower or "found" in response_lower,
            "specific" in response_lower or "particular" in response_lower
        ])
        
        return sum(accuracy_indicators) / len(accuracy_indicators) if accuracy_indicators else 0.5
    
    def _evaluate_impact_assessment(self, response: str) -> float:
        """Evaluate impact assessment quality."""
        impact_indicators = [
            "impact" in response.lower() or "effect" in response.lower(),
            "cost" in response.lower() or "overhead" in response.lower(),
            "performance" in response.lower() or "degradation" in response.lower(),
            "quantify" in response.lower() or "measure" in response.lower(),
            "significant" in response.lower() or "major" in response.lower(),
            re.search(r"\d+%|\d+\s*percent", response) is not None  # Quantitative impact
        ]
        
        return sum(impact_indicators) / len(impact_indicators)
    
    def _evaluate_prioritization_logic(self, response: str) -> float:
        """Evaluate prioritization logic quality."""
        prioritization_indicators = [
            "priority" in response.lower() or "prioritize" in response.lower(),
            "first" in response.lower() or "most important" in response.lower(),
            "effort" in response.lower() or "difficulty" in response.lower(),
            "benefit" in response.lower() or "gain" in response.lower(),
            "order" in response.lower() or "sequence" in response.lower(),
            "rank" in response.lower() or "ranking" in response.lower()
        ]
        
        return sum(prioritization_indicators) / len(prioritization_indicators)
    
    def _evaluate_root_cause_analysis(self, response: str) -> float:
        """Evaluate root cause analysis quality."""
        root_cause_indicators = [
            "root cause" in response.lower() or "cause" in response.lower(),
            "because" in response.lower() or "due to" in response.lower(),
            "reason" in response.lower() or "explanation" in response.lower(),
            "underlying" in response.lower() or "fundamental" in response.lower(),
            "why" in response.lower() or "source" in response.lower()
        ]
        
        return sum(root_cause_indicators) / len(root_cause_indicators)
    
    def _evaluate_quantitative_analysis(self, response: str) -> float:
        """Evaluate quantitative analysis quality."""
        quantitative_indicators = [
            re.search(r"\d+%|\d+\s*percent", response) is not None,
            re.search(r"\d+ms|\d+\s*millisecond", response) is not None,
            re.search(r"\d+\s*req/s|\d+\s*requests", response) is not None,
            "metric" in response.lower() or "measurement" in response.lower(),
            "data" in response.lower() or "number" in response.lower(),
            "baseline" in response.lower() or "benchmark" in response.lower()
        ]
        
        return sum(quantitative_indicators) / len(quantitative_indicators)
    
    def _evaluate_optimization_quality(self, response: str) -> float:
        """Evaluate optimization quality."""
        optimization_indicators = [
            "optimization" in response.lower() or "optimize" in response.lower(),
            "improve" in response.lower() or "enhancement" in response.lower(),
            "strategy" in response.lower() or "approach" in response.lower(),
            "code" in response.lower() or "implementation" in response.lower(),
            "configuration" in response.lower() or "setting" in response.lower(),
            "algorithm" in response.lower() or "logic" in response.lower(),
            len(response.split()) > 200  # Comprehensive optimization plan
        ]
        
        return sum(optimization_indicators) / len(optimization_indicators)
    
    def _evaluate_implementation_feasibility(self, response: str) -> float:
        """Evaluate implementation feasibility assessment."""
        feasibility_indicators = [
            "feasible" in response.lower() or "practical" in response.lower(),
            "implementation" in response.lower() or "implement" in response.lower(),
            "effort" in response.lower() or "work" in response.lower(),
            "resource" in response.lower() or "time" in response.lower(),
            "realistic" in response.lower() or "achievable" in response.lower(),
            "guideline" in response.lower() or "instruction" in response.lower()
        ]
        
        return sum(feasibility_indicators) / len(feasibility_indicators)
    
    def _evaluate_trade_off_awareness(self, response: str) -> float:
        """Evaluate trade-off awareness."""
        tradeoff_indicators = [
            "trade-off" in response.lower() or "tradeoff" in response.lower(),
            "risk" in response.lower() or "downside" in response.lower(),
            "compromise" in response.lower() or "balance" in response.lower(),
            "cost" in response.lower() or "overhead" in response.lower(),
            "complexity" in response.lower() or "maintenance" in response.lower(),
            "however" in response.lower() or "but" in response.lower()
        ]
        
        return sum(tradeoff_indicators) / len(tradeoff_indicators)
    
    def _evaluate_expected_impact(self, response: str) -> float:
        """Evaluate expected impact assessment."""
        impact_indicators = [
            "expect" in response.lower() or "estimate" in response.lower(),
            "improvement" in response.lower() or "gain" in response.lower(),
            "performance" in response.lower() or "speed" in response.lower(),
            re.search(r"\d+%|\d+\s*percent", response) is not None,
            "faster" in response.lower() or "better" in response.lower(),
            "reduction" in response.lower() or "increase" in response.lower()
        ]
        
        return sum(impact_indicators) / len(impact_indicators)
    
    def _evaluate_code_quality(self, response: str) -> float:
        """Evaluate code quality in optimization suggestions."""
        code_indicators = [
            "```" in response,  # Contains code blocks
            "function" in response.lower() or "method" in response.lower(),
            "class" in response.lower() or "object" in response.lower(),
            "variable" in response.lower() or "parameter" in response.lower(),
            "comment" in response.lower() or "documentation" in response.lower(),
            len(utils.extract_code_blocks(response)) > 0  # Has actual code
        ]
        
        return sum(code_indicators) / len(code_indicators)
    
    def _evaluate_measurement_accuracy(self, response: str) -> float:
        """Evaluate measurement accuracy."""
        measurement_indicators = [
            "measure" in response.lower() or "measurement" in response.lower(),
            "metric" in response.lower() or "data" in response.lower(),
            "result" in response.lower() or "outcome" in response.lower(),
            "compare" in response.lower() or "comparison" in response.lower(),
            "before" in response.lower() and "after" in response.lower(),
            re.search(r"\d+%|\d+\s*percent", response) is not None
        ]
        
        return sum(measurement_indicators) / len(measurement_indicators)
    
    def _evaluate_target_assessment(self, response: str, doc: Dict[str, Any]) -> float:
        """Evaluate target assessment quality."""
        target_metrics = doc.get("target_metrics", {})
        response_lower = response.lower()
        
        assessment_indicators = [
            "target" in response_lower or "goal" in response_lower,
            "achieve" in response_lower or "reach" in response_lower,
            "meet" in response_lower or "satisfy" in response_lower,
            "compare" in response_lower or "against" in response_lower,
            "success" in response_lower or "failure" in response_lower
        ]
        
        # Check if specific target metrics are mentioned
        if target_metrics:
            for key in target_metrics.keys():
                if key.lower() in response_lower:
                    assessment_indicators.append(True)
                    break
        
        return sum(assessment_indicators) / len(assessment_indicators)
    
    def _evaluate_regression_detection(self, response: str) -> float:
        """Evaluate regression detection capability."""
        regression_indicators = [
            "regression" in response.lower() or "side effect" in response.lower(),
            "unexpected" in response.lower() or "unintended" in response.lower(),
            "degradation" in response.lower() or "worse" in response.lower(),
            "impact" in response.lower() or "affect" in response.lower(),
            "monitor" in response.lower() or "watch" in response.lower()
        ]
        
        return sum(regression_indicators) / len(regression_indicators)
    
    def _evaluate_success_evaluation(self, response: str) -> float:
        """Evaluate success evaluation quality."""
        success_indicators = [
            "success" in response.lower() or "successful" in response.lower(),
            "evaluate" in response.lower() or "assessment" in response.lower(),
            "overall" in response.lower() or "total" in response.lower(),
            "objective" in response.lower() or "measurable" in response.lower(),
            "conclusion" in response.lower() or "summary" in response.lower()
        ]
        
        return sum(success_indicators) / len(success_indicators)
    
    def _evaluate_objective_assessment(self, response: str) -> float:
        """Evaluate objectivity of assessment."""
        objectivity_indicators = [
            "objective" in response.lower() or "factual" in response.lower(),
            "data" in response.lower() or "evidence" in response.lower(),
            "metric" in response.lower() or "measurement" in response.lower(),
            not any(word in response.lower() for word in ["amazing", "terrible", "perfect"]),
            "quantify" in response.lower() or "measure" in response.lower()
        ]
        
        return sum(objectivity_indicators) / len(objectivity_indicators)
    
    def _evaluate_monitoring_strategy_quality(self, response: str) -> float:
        """Evaluate monitoring strategy quality."""
        monitoring_indicators = [
            "monitoring" in response.lower() or "monitor" in response.lower(),
            "strategy" in response.lower() or "approach" in response.lower(),
            "continuous" in response.lower() or "ongoing" in response.lower(),
            "alert" in response.lower() or "notification" in response.lower(),
            "threshold" in response.lower() or "limit" in response.lower(),
            "dashboard" in response.lower() or "visualization" in response.lower()
        ]
        
        return sum(monitoring_indicators) / len(monitoring_indicators)
    
    def _evaluate_sustainability_planning(self, response: str) -> float:
        """Evaluate sustainability planning quality."""
        sustainability_indicators = [
            "sustain" in response.lower() or "maintain" in response.lower(),
            "long-term" in response.lower() or "future" in response.lower(),
            "process" in response.lower() or "procedure" in response.lower(),
            "regular" in response.lower() or "periodic" in response.lower(),
            "review" in response.lower() or "assessment" in response.lower()
        ]
        
        return sum(sustainability_indicators) / len(sustainability_indicators)
    
    def _evaluate_knowledge_transfer(self, response: str) -> float:
        """Evaluate knowledge transfer quality."""
        knowledge_indicators = [
            "knowledge" in response.lower() or "learning" in response.lower(),
            "document" in response.lower() or "documentation" in response.lower(),
            "lesson" in response.lower() or "experience" in response.lower(),
            "best practice" in response.lower() or "guideline" in response.lower(),
            "share" in response.lower() or "transfer" in response.lower()
        ]
        
        return sum(knowledge_indicators) / len(knowledge_indicators)
    
    def _evaluate_proactive_management(self, response: str) -> float:
        """Evaluate proactive management approach."""
        proactive_indicators = [
            "proactive" in response.lower() or "preventive" in response.lower(),
            "anticipate" in response.lower() or "predict" in response.lower(),
            "early" in response.lower() or "before" in response.lower(),
            "prevent" in response.lower() or "avoid" in response.lower(),
            "trend" in response.lower() or "pattern" in response.lower()
        ]
        
        return sum(proactive_indicators) / len(proactive_indicators)
    
    def _evaluate_long_term_vision(self, response: str) -> float:
        """Evaluate long-term vision quality."""
        vision_indicators = [
            "long-term" in response.lower() or "future" in response.lower(),
            "vision" in response.lower() or "roadmap" in response.lower(),
            "scale" in response.lower() or "growth" in response.lower(),
            "evolution" in response.lower() or "development" in response.lower(),
            "strategic" in response.lower() or "planning" in response.lower()
        ]
        
        return sum(vision_indicators) / len(vision_indicators)
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "analysis_depth": 0.0,
            "bottleneck_identification": 0.0,
            "systematic_approach": 0.0,
            "tool_selection": 0.0,
            "metrics_interpretation": 0.0,
            "hypothesis_quality": 0.0,
            "bottleneck_accuracy": 0.0,
            "impact_assessment": 0.0,
            "prioritization_logic": 0.0,
            "root_cause_analysis": 0.0,
            "quantitative_analysis": 0.0,
            "optimization_quality": 0.0,
            "implementation_feasibility": 0.0,
            "trade_off_awareness": 0.0,
            "expected_impact": 0.0,
            "code_quality": 0.0,
            "measurement_accuracy": 0.0,
            "target_assessment": 0.0,
            "regression_detection": 0.0,
            "success_evaluation": 0.0,
            "objective_assessment": 0.0,
            "monitoring_strategy_quality": 0.0,
            "sustainability_planning": 0.0,
            "knowledge_transfer": 0.0,
            "proactive_management": 0.0,
            "long_term_vision": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {metric: "mean" for metric in self._empty_results().keys()}
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {metric: True for metric in self._empty_results().keys()}