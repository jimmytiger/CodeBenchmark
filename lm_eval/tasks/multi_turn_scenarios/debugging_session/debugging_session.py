"""Debugging Session multi-turn task implementation."""

import logging
from typing import Dict, List, Any, Optional
import re
import json

from evaluation_engine.core.extended_tasks import MultiTurnTask, ScenarioConfig, ScenarioType, TurnConfig
from lm_eval.api.registry import register_task
from .. import utils, metrics

eval_logger = logging.getLogger(__name__)


@register_task("multi_turn_scenarios_debugging_session")
class DebuggingSessionTask(MultiTurnTask):
    """
    Multi-turn debugging session evaluation task.
    
    This task evaluates a model's ability to conduct systematic debugging
    including problem analysis, hypothesis formation, evidence gathering, and solution.
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    DATASET_NAME = "multi_turn_scenarios_debugging_session"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize debugging session task."""
        scenario_config = ScenarioConfig(
            scenario_id="debugging_session",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=5,
            conversation_timeout=900,
            enable_context_retention=True,
            turns=[
                TurnConfig(
                    turn_id="problem_analysis",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""You are debugging the following issue:

**Problem Description**: {problem_description}

**Code with Issue**:
```{language}
{buggy_code}
```

**Error/Symptoms**: {error_symptoms}

**Expected Behavior**: {expected_behavior}

Please analyze this debugging scenario and provide:
1. Your initial understanding of the problem
2. Potential root causes you suspect
3. What additional information you would need
4. Your debugging strategy""",
                    expected_format="structured_analysis",
                    evaluation_metrics=["problem_understanding", "hypothesis_quality", "debugging_strategy"],
                    temperature=0.2,
                    max_tokens=2000
                ),
                TurnConfig(
                    turn_id="hypothesis_formation",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Based on your initial analysis, please form specific hypotheses about what might be causing the issue.

Previous analysis: {previous_response}

For each hypothesis, provide:
1. The specific hypothesis
2. Why you think this could be the cause
3. How you would test this hypothesis
4. What evidence would confirm or refute it

Rank your hypotheses by likelihood.""",
                    expected_format="ranked_hypotheses",
                    depends_on=["problem_analysis"],
                    evaluation_metrics=["hypothesis_specificity", "reasoning_quality", "testability"],
                    temperature=0.3,
                    max_tokens=2000
                ),
                TurnConfig(
                    turn_id="evidence_gathering",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Now let's gather evidence to test your hypotheses. 

Your hypotheses: {previous_response}

Additional debugging information available:
{debug_info}

Based on this information:
1. Which hypothesis does this evidence support or refute?
2. What does this tell us about the root cause?
3. What additional tests or information would help narrow down the issue?
4. Update your assessment of the most likely cause""",
                    expected_format="evidence_analysis",
                    depends_on=["hypothesis_formation"],
                    evaluation_metrics=["evidence_interpretation", "logical_reasoning", "hypothesis_updating"],
                    temperature=0.2,
                    max_tokens=1800
                ),
                TurnConfig(
                    turn_id="root_cause_identification",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Based on your analysis and evidence gathering, identify the root cause of the issue.

Problem: {problem_description}
Your analysis: {analysis_summary}
Evidence: {evidence_summary}

Please provide:
1. The identified root cause
2. Explanation of how you arrived at this conclusion
3. Why other hypotheses were ruled out
4. Confidence level in your diagnosis""",
                    expected_format="root_cause_diagnosis",
                    depends_on=["evidence_gathering"],
                    evaluation_metrics=["diagnosis_accuracy", "reasoning_clarity", "confidence_calibration"],
                    temperature=0.1,
                    max_tokens=1500
                ),
                TurnConfig(
                    turn_id="solution_implementation",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Now provide a solution to fix the identified issue.

Root cause: {root_cause}
Original buggy code:
```{language}
{buggy_code}
```

Please provide:
1. The corrected code
2. Explanation of what was changed and why
3. How this fix addresses the root cause
4. Any additional recommendations to prevent similar issues""",
                    expected_format="solution_with_explanation",
                    depends_on=["root_cause_identification"],
                    evaluation_metrics=["solution_correctness", "fix_quality", "prevention_recommendations"],
                    temperature=0.2,
                    max_tokens=2000
                )
            ],
            scenario_metrics=[
                "debugging_effectiveness",
                "systematic_approach",
                "solution_quality",
                "overall_debugging_score"
            ],
            success_criteria={
                "debugging_effectiveness": 0.7,
                "systematic_approach": 0.8,
                "solution_quality": 0.6
            }
        )
        
        super().__init__(
            data_dir=data_dir,
            cache_dir=cache_dir,
            download_mode=download_mode,
            config=config,
            scenario_config=scenario_config
        )
        
        self.hypotheses = []
        self.evidence_collected = []
        self.root_cause = None
        
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
            dataset_dict = utils.load_dataset(metadata={"scenario": "debugging_session"})
            dataset = dataset_dict["test"]
            processed_dataset = utils.process_docs(dataset)
            
            eval_logger.info(f"Loaded {len(processed_dataset)} debugging scenarios")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load debugging dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """Process model results for multi-turn debugging session."""
        if not results:
            return self._empty_results()
            
        turn_id = self._determine_current_turn(doc)
        prediction = results[0] if results else ""
        
        if turn_id == "problem_analysis":
            return self._process_problem_analysis(doc, prediction)
        elif turn_id == "hypothesis_formation":
            return self._process_hypothesis_formation(doc, prediction)
        elif turn_id == "evidence_gathering":
            return self._process_evidence_gathering(doc, prediction)
        elif turn_id == "root_cause_identification":
            return self._process_root_cause_identification(doc, prediction)
        elif turn_id == "solution_implementation":
            return self._process_solution_implementation(doc, prediction)
        else:
            return self._empty_results()
    
    def _determine_current_turn(self, doc: Dict[str, Any]) -> str:
        """Determine current turn based on conversation state."""
        turn_count = len(self._conversation_history)
        turns = ["problem_analysis", "hypothesis_formation", "evidence_gathering", 
                "root_cause_identification", "solution_implementation"]
        return turns[min(turn_count, len(turns) - 1)]
    
    def _process_problem_analysis(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process problem analysis response."""
        metrics_result = {
            "response": prediction,
            "problem_understanding": self._evaluate_problem_understanding(prediction, doc),
            "hypothesis_quality": self._evaluate_initial_hypothesis_quality(prediction),
            "debugging_strategy": self._evaluate_debugging_strategy(prediction),
            "information_needs": self._evaluate_information_needs(prediction),
            "systematic_thinking": self._evaluate_systematic_thinking(prediction)
        }
        
        return metrics_result
    
    def _process_hypothesis_formation(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process hypothesis formation response."""
        hypotheses = self._extract_hypotheses(prediction)
        self.hypotheses.extend(hypotheses)
        
        metrics_result = {
            "response": prediction,
            "hypothesis_specificity": self._evaluate_hypothesis_specificity(prediction),
            "reasoning_quality": self._evaluate_reasoning_quality(prediction),
            "testability": self._evaluate_testability(prediction),
            "hypothesis_count": len(hypotheses),
            "ranking_quality": self._evaluate_ranking_quality(prediction)
        }
        
        return metrics_result
    
    def _process_evidence_gathering(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process evidence gathering response."""
        evidence = self._extract_evidence_analysis(prediction)
        self.evidence_collected.append(evidence)
        
        metrics_result = {
            "response": prediction,
            "evidence_interpretation": self._evaluate_evidence_interpretation(prediction),
            "logical_reasoning": self._evaluate_logical_reasoning(prediction),
            "hypothesis_updating": self._evaluate_hypothesis_updating(prediction),
            "critical_thinking": self._evaluate_critical_thinking(prediction)
        }
        
        return metrics_result
    
    def _process_root_cause_identification(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process root cause identification response."""
        root_cause = self._extract_root_cause(prediction)
        self.root_cause = root_cause
        
        metrics_result = {
            "response": prediction,
            "diagnosis_accuracy": self._evaluate_diagnosis_accuracy(prediction, doc),
            "reasoning_clarity": self._evaluate_reasoning_clarity(prediction),
            "confidence_calibration": self._evaluate_confidence_calibration(prediction),
            "elimination_reasoning": self._evaluate_elimination_reasoning(prediction)
        }
        
        return metrics_result
    
    def _process_solution_implementation(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process solution implementation response."""
        fixed_code = self._extract_code_from_response(prediction)
        
        metrics_result = {
            "response": prediction,
            "solution_correctness": self._evaluate_solution_correctness(prediction, doc, fixed_code),
            "fix_quality": self._evaluate_fix_quality(prediction, doc, fixed_code),
            "prevention_recommendations": self._evaluate_prevention_recommendations(prediction),
            "explanation_quality": self._evaluate_solution_explanation_quality(prediction)
        }
        
        return metrics_result
    
    def _evaluate_problem_understanding(self, response: str, doc: Dict[str, Any]) -> float:
        """Evaluate understanding of the problem."""
        problem_elements = [
            doc.get("problem_description", "").lower(),
            doc.get("error_symptoms", "").lower(),
            doc.get("expected_behavior", "").lower()
        ]
        
        response_lower = response.lower()
        understanding_score = 0.0
        
        for element in problem_elements:
            if element and any(word in response_lower for word in element.split()[:5]):
                understanding_score += 1.0
        
        understanding_score /= len([e for e in problem_elements if e])
        
        # Bonus for demonstrating comprehension
        comprehension_indicators = [
            "understand" in response_lower,
            "problem" in response_lower,
            "issue" in response_lower,
            "symptom" in response_lower,
            "expect" in response_lower
        ]
        
        understanding_score += sum(comprehension_indicators) * 0.1
        return min(understanding_score, 1.0)
    
    def _evaluate_initial_hypothesis_quality(self, response: str) -> float:
        """Evaluate quality of initial hypotheses."""
        hypothesis_indicators = [
            "suspect" in response.lower() or "hypothesis" in response.lower(),
            "might" in response.lower() or "could" in response.lower(),
            "possible" in response.lower() or "potential" in response.lower(),
            len(re.findall(r"\d+\.", response)) > 0,  # Numbered points
            "cause" in response.lower()
        ]
        
        return sum(hypothesis_indicators) / len(hypothesis_indicators)
    
    def _evaluate_debugging_strategy(self, response: str) -> float:
        """Evaluate debugging strategy quality."""
        strategy_indicators = [
            "strategy" in response.lower() or "approach" in response.lower(),
            "step" in response.lower() or "process" in response.lower(),
            "test" in response.lower() or "check" in response.lower(),
            "investigate" in response.lower() or "examine" in response.lower(),
            "systematic" in response.lower() or "methodical" in response.lower()
        ]
        
        return sum(strategy_indicators) / len(strategy_indicators)
    
    def _evaluate_information_needs(self, response: str) -> float:
        """Evaluate identification of information needs."""
        info_indicators = [
            "need" in response.lower() or "require" in response.lower(),
            "additional" in response.lower() or "more" in response.lower(),
            "information" in response.lower() or "data" in response.lower(),
            "log" in response.lower() or "trace" in response.lower(),
            "context" in response.lower() or "environment" in response.lower()
        ]
        
        return sum(info_indicators) / len(info_indicators)
    
    def _evaluate_systematic_thinking(self, response: str) -> float:
        """Evaluate systematic thinking approach."""
        systematic_indicators = [
            len(re.findall(r"\d+\.", response)) >= 3,  # Structured points
            "first" in response.lower() or "then" in response.lower(),
            "next" in response.lower() or "after" in response.lower(),
            len(response.split()) > 100,  # Detailed analysis
            "because" in response.lower() or "since" in response.lower()
        ]
        
        return sum(systematic_indicators) / len(systematic_indicators)
    
    def _extract_hypotheses(self, response: str) -> List[str]:
        """Extract hypotheses from response."""
        # Look for numbered hypotheses
        hypotheses = re.findall(r"\d+\.\s*([^.]+(?:\.[^.]*)*)", response)
        
        # If no numbered hypotheses, look for bullet points
        if not hypotheses:
            hypotheses = re.findall(r"[-*]\s*([^-*\n]+)", response)
        
        return [h.strip() for h in hypotheses if len(h.strip()) > 10]
    
    def _evaluate_hypothesis_specificity(self, response: str) -> float:
        """Evaluate specificity of hypotheses."""
        specificity_indicators = [
            len(re.findall(r"specific|particular|exact|precise", response, re.IGNORECASE)),
            len(re.findall(r"line \d+|function \w+|variable \w+", response, re.IGNORECASE)),
            len(re.findall(r"because|due to|caused by", response, re.IGNORECASE)),
            len(self._extract_hypotheses(response))
        ]
        
        return min(sum(specificity_indicators) / 10.0, 1.0)
    
    def _evaluate_reasoning_quality(self, response: str) -> float:
        """Evaluate quality of reasoning."""
        reasoning_indicators = [
            "because" in response.lower() or "since" in response.lower(),
            "therefore" in response.lower() or "thus" in response.lower(),
            "evidence" in response.lower() or "indicate" in response.lower(),
            "likely" in response.lower() or "probable" in response.lower(),
            len(response.split()) > 150  # Detailed reasoning
        ]
        
        return sum(reasoning_indicators) / len(reasoning_indicators)
    
    def _evaluate_testability(self, response: str) -> float:
        """Evaluate testability of hypotheses."""
        testability_indicators = [
            "test" in response.lower() or "verify" in response.lower(),
            "check" in response.lower() or "examine" in response.lower(),
            "evidence" in response.lower() or "confirm" in response.lower(),
            "would" in response.lower() or "could" in response.lower(),
            "if" in response.lower() and "then" in response.lower()
        ]
        
        return sum(testability_indicators) / len(testability_indicators)
    
    def _evaluate_ranking_quality(self, response: str) -> float:
        """Evaluate quality of hypothesis ranking."""
        ranking_indicators = [
            "most likely" in response.lower() or "least likely" in response.lower(),
            "rank" in response.lower() or "order" in response.lower(),
            "probability" in response.lower() or "chance" in response.lower(),
            re.search(r"1\.|first.*2\.|second", response, re.IGNORECASE) is not None,
            "priority" in response.lower()
        ]
        
        return sum(ranking_indicators) / len(ranking_indicators)
    
    def _extract_evidence_analysis(self, response: str) -> Dict[str, Any]:
        """Extract evidence analysis from response."""
        return {
            "evidence_mentioned": "evidence" in response.lower(),
            "hypothesis_referenced": any(h in response.lower() for h in ["hypothesis", "theory", "suspect"]),
            "conclusion_drawn": any(c in response.lower() for c in ["conclude", "determine", "find"])
        }
    
    def _evaluate_evidence_interpretation(self, response: str) -> float:
        """Evaluate evidence interpretation quality."""
        interpretation_indicators = [
            "evidence" in response.lower() or "information" in response.lower(),
            "support" in response.lower() or "refute" in response.lower(),
            "indicate" in response.lower() or "suggest" in response.lower(),
            "consistent" in response.lower() or "inconsistent" in response.lower(),
            "confirm" in response.lower() or "contradict" in response.lower()
        ]
        
        return sum(interpretation_indicators) / len(interpretation_indicators)
    
    def _evaluate_logical_reasoning(self, response: str) -> float:
        """Evaluate logical reasoning quality."""
        logic_indicators = [
            "therefore" in response.lower() or "thus" in response.lower(),
            "if" in response.lower() and "then" in response.lower(),
            "because" in response.lower() or "since" in response.lower(),
            "however" in response.lower() or "but" in response.lower(),
            "conclusion" in response.lower() or "deduce" in response.lower()
        ]
        
        return sum(logic_indicators) / len(logic_indicators)
    
    def _evaluate_hypothesis_updating(self, response: str) -> float:
        """Evaluate hypothesis updating based on evidence."""
        updating_indicators = [
            "update" in response.lower() or "revise" in response.lower(),
            "change" in response.lower() or "modify" in response.lower(),
            "now" in response.lower() or "based on" in response.lower(),
            "likely" in response.lower() or "unlikely" in response.lower(),
            "rule out" in response.lower() or "eliminate" in response.lower()
        ]
        
        return sum(updating_indicators) / len(updating_indicators)
    
    def _evaluate_critical_thinking(self, response: str) -> float:
        """Evaluate critical thinking quality."""
        critical_indicators = [
            "question" in response.lower() or "doubt" in response.lower(),
            "assume" in response.lower() or "assumption" in response.lower(),
            "alternative" in response.lower() or "other" in response.lower(),
            "limitation" in response.lower() or "caveat" in response.lower(),
            "uncertain" in response.lower() or "unclear" in response.lower()
        ]
        
        return sum(critical_indicators) / len(critical_indicators)
    
    def _extract_root_cause(self, response: str) -> Optional[str]:
        """Extract root cause from response."""
        # Look for explicit root cause statements
        root_cause_patterns = [
            r"root cause.*?is\s+([^.]+)",
            r"cause.*?is\s+([^.]+)",
            r"problem.*?is\s+([^.]+)",
            r"issue.*?is\s+([^.]+)"
        ]
        
        for pattern in root_cause_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _evaluate_diagnosis_accuracy(self, response: str, doc: Dict[str, Any]) -> float:
        """Evaluate accuracy of diagnosis."""
        expected_cause = doc.get("root_cause", "").lower()
        response_lower = response.lower()
        
        if not expected_cause:
            return 0.5  # No ground truth available
        
        # Check for key terms from expected cause
        expected_terms = expected_cause.split()
        matching_terms = sum(1 for term in expected_terms if term in response_lower)
        
        accuracy = matching_terms / len(expected_terms) if expected_terms else 0.0
        
        # Bonus for correct identification
        if "root cause" in response_lower and expected_cause in response_lower:
            accuracy += 0.3
            
        return min(accuracy, 1.0)
    
    def _evaluate_reasoning_clarity(self, response: str) -> float:
        """Evaluate clarity of reasoning."""
        clarity_indicators = [
            "because" in response.lower() or "reason" in response.lower(),
            "explain" in response.lower() or "explanation" in response.lower(),
            "clear" in response.lower() or "obvious" in response.lower(),
            len(response.split()) > 80,  # Detailed explanation
            "step" in response.lower() or "process" in response.lower()
        ]
        
        return sum(clarity_indicators) / len(clarity_indicators)
    
    def _evaluate_confidence_calibration(self, response: str) -> float:
        """Evaluate confidence calibration."""
        confidence_indicators = [
            "confident" in response.lower() or "confidence" in response.lower(),
            "certain" in response.lower() or "sure" in response.lower(),
            "likely" in response.lower() or "probable" in response.lower(),
            re.search(r"\d+%|\d+\s*percent", response, re.IGNORECASE) is not None,
            "believe" in response.lower() or "think" in response.lower()
        ]
        
        return sum(confidence_indicators) / len(confidence_indicators)
    
    def _evaluate_elimination_reasoning(self, response: str) -> float:
        """Evaluate elimination reasoning quality."""
        elimination_indicators = [
            "rule out" in response.lower() or "eliminate" in response.lower(),
            "not" in response.lower() and "because" in response.lower(),
            "other" in response.lower() or "alternative" in response.lower(),
            "however" in response.lower() or "but" in response.lower(),
            "unlikely" in response.lower() or "improbable" in response.lower()
        ]
        
        return sum(elimination_indicators) / len(elimination_indicators)
    
    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract code blocks from response."""
        code_blocks = re.findall(r"```(?:\w+)?\n?(.*?)\n?```", response, re.DOTALL)
        return code_blocks[0].strip() if code_blocks else None
    
    def _evaluate_solution_correctness(self, response: str, doc: Dict[str, Any], fixed_code: Optional[str]) -> float:
        """Evaluate correctness of solution."""
        if not fixed_code:
            return 0.0
        
        correctness_indicators = [
            fixed_code != doc.get("buggy_code", ""),  # Code was actually changed
            len(fixed_code) > 0,  # Non-empty solution
            "fix" in response.lower() or "correct" in response.lower(),
            "solution" in response.lower() or "resolve" in response.lower()
        ]
        
        # Check against expected fix if available
        expected_fix = doc.get("expected_fix", "")
        if expected_fix:
            similarity = len(set(fixed_code.split()) & set(expected_fix.split()))
            similarity_score = similarity / max(len(expected_fix.split()), 1)
            correctness_indicators.append(similarity_score > 0.3)
        
        return sum(correctness_indicators) / len(correctness_indicators)
    
    def _evaluate_fix_quality(self, response: str, doc: Dict[str, Any], fixed_code: Optional[str]) -> float:
        """Evaluate quality of fix."""
        if not fixed_code:
            return 0.0
        
        quality_indicators = [
            "```" in response,  # Properly formatted code
            len(response.split()) > 50,  # Detailed explanation
            "change" in response.lower() or "modify" in response.lower(),
            "why" in response.lower() or "because" in response.lower(),
            fixed_code.count('\n') >= doc.get("buggy_code", "").count('\n') * 0.8  # Maintained structure
        ]
        
        return sum(quality_indicators) / len(quality_indicators)
    
    def _evaluate_prevention_recommendations(self, response: str) -> float:
        """Evaluate prevention recommendations."""
        prevention_indicators = [
            "prevent" in response.lower() or "avoid" in response.lower(),
            "future" in response.lower() or "next time" in response.lower(),
            "recommend" in response.lower() or "suggest" in response.lower(),
            "best practice" in response.lower() or "good practice" in response.lower(),
            "test" in response.lower() or "validation" in response.lower()
        ]
        
        return sum(prevention_indicators) / len(prevention_indicators)
    
    def _evaluate_solution_explanation_quality(self, response: str) -> float:
        """Evaluate quality of solution explanation."""
        explanation_indicators = [
            "explanation" in response.lower() or "explain" in response.lower(),
            "what" in response.lower() and "change" in response.lower(),
            "how" in response.lower() and "fix" in response.lower(),
            "address" in response.lower() or "solve" in response.lower(),
            len(response.split()) > 100  # Detailed explanation
        ]
        
        return sum(explanation_indicators) / len(explanation_indicators)
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "problem_understanding": 0.0,
            "hypothesis_quality": 0.0,
            "debugging_strategy": 0.0,
            "information_needs": 0.0,
            "systematic_thinking": 0.0,
            "hypothesis_specificity": 0.0,
            "reasoning_quality": 0.0,
            "testability": 0.0,
            "hypothesis_count": 0,
            "ranking_quality": 0.0,
            "evidence_interpretation": 0.0,
            "logical_reasoning": 0.0,
            "hypothesis_updating": 0.0,
            "critical_thinking": 0.0,
            "diagnosis_accuracy": 0.0,
            "reasoning_clarity": 0.0,
            "confidence_calibration": 0.0,
            "elimination_reasoning": 0.0,
            "solution_correctness": 0.0,
            "fix_quality": 0.0,
            "prevention_recommendations": 0.0,
            "explanation_quality": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {metric: "mean" for metric in self._empty_results().keys()}
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {metric: True for metric in self._empty_results().keys()}