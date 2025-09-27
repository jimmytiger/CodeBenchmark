"""Code Review Process multi-turn task implementation."""

import logging
from typing import Dict, List, Any, Optional
import re
import json

from evaluation_engine.core.extended_tasks import MultiTurnTask, ScenarioConfig, ScenarioType, TurnConfig
from lm_eval.api.registry import register_task
from .. import utils, metrics

eval_logger = logging.getLogger(__name__)


@register_task("multi_turn_scenarios_code_review")
class CodeReviewProcessTask(MultiTurnTask):
    """
    Multi-turn code review process evaluation task.
    
    This task evaluates a model's ability to conduct a complete code review process
    including initial review, code revision, and final evaluation.
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    DATASET_NAME = "multi_turn_scenarios_code_review"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize code review process task."""
        # Create scenario configuration
        scenario_config = ScenarioConfig(
            scenario_id="code_review_process",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=3,
            conversation_timeout=600,
            enable_context_retention=True,
            turns=[
                TurnConfig(
                    turn_id="initial_review",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Please perform a thorough code review of the following code:

```{language}
{code}
```

Context: {context}

Please provide specific, actionable feedback covering:
1. Code quality and style
2. Functionality and correctness
3. Performance implications
4. Security considerations
5. Maintainability

Format your response with clear sections and specific line references where applicable.""",
                    expected_format="structured_feedback",
                    evaluation_metrics=["review_thoroughness", "specificity_score", "actionability_score"],
                    temperature=0.1,
                    max_tokens=2000
                ),
                TurnConfig(
                    turn_id="code_revision",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Based on the code review feedback provided, please revise the code to address the identified issues:

Original code:
```{language}
{code}
```

Review feedback:
{previous_response}

Please provide:
1. The revised code
2. A summary of changes made
3. Explanation of how each change addresses the feedback""",
                    expected_format="code_with_explanation",
                    depends_on=["initial_review"],
                    evaluation_metrics=["revision_quality", "feedback_addressing", "code_improvement"],
                    temperature=0.2,
                    max_tokens=2500
                ),
                TurnConfig(
                    turn_id="final_evaluation",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Please provide a final evaluation comparing the original and revised code:

Original code:
```{language}
{original_code}
```

Revised code:
```{language}
{revised_code}
```

Assess:
1. How well the revision addresses the original feedback
2. Overall improvement in code quality
3. Any remaining issues or suggestions
4. Overall rating (1-10) for the revision process""",
                    expected_format="evaluation_summary",
                    depends_on=["initial_review", "code_revision"],
                    evaluation_metrics=["evaluation_completeness", "improvement_assessment"],
                    temperature=0.1,
                    max_tokens=1500
                )
            ],
            scenario_metrics=[
                "review_thoroughness",
                "code_improvement_score",
                "process_completeness",
                "overall_quality"
            ],
            success_criteria={
                "review_thoroughness": 0.7,
                "code_improvement_score": 0.6,
                "process_completeness": 0.8
            }
        )
        
        super().__init__(
            data_dir=data_dir,
            cache_dir=cache_dir,
            download_mode=download_mode,
            config=config,
            scenario_config=scenario_config
        )
        
        self.code_versions = []
        self.review_comments = []
        
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
            dataset_dict = utils.load_dataset(metadata={"scenario": "code_review_process"})
            dataset = dataset_dict["test"]
            processed_dataset = utils.process_docs(dataset)
            
            eval_logger.info(f"Loaded {len(processed_dataset)} code review scenarios")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load code review dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """Process model results for multi-turn code review."""
        if not results:
            return self._empty_results()
            
        # Determine which turn this is based on conversation history
        turn_id = self._determine_current_turn(doc)
        prediction = results[0] if results else ""
        
        if turn_id == "initial_review":
            return self._process_initial_review(doc, prediction)
        elif turn_id == "code_revision":
            return self._process_code_revision(doc, prediction)
        elif turn_id == "final_evaluation":
            return self._process_final_evaluation(doc, prediction)
        else:
            return self._empty_results()
    
    def _determine_current_turn(self, doc: Dict[str, Any]) -> str:
        """Determine current turn based on conversation state."""
        # This is a simplified implementation
        # In practice, this would be managed by the multi-turn evaluation engine
        if len(self._conversation_history) == 0:
            return "initial_review"
        elif len(self._conversation_history) == 1:
            return "code_revision"
        else:
            return "final_evaluation"
    
    def _process_initial_review(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process initial code review response."""
        self.review_comments.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "review_thoroughness": self._evaluate_review_thoroughness(prediction),
            "specificity_score": self._evaluate_specificity(prediction),
            "actionability_score": self._evaluate_actionability(prediction),
            "security_awareness": self._evaluate_security_awareness(prediction),
            "performance_awareness": self._evaluate_performance_awareness(prediction)
        }
        
        return metrics_result
    
    def _process_code_revision(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process code revision response."""
        revised_code = self._extract_code_from_response(prediction)
        if revised_code:
            self.code_versions.append(revised_code)
        
        metrics_result = {
            "response": prediction,
            "revision_quality": self._evaluate_revision_quality(prediction, doc),
            "feedback_addressing": self._evaluate_feedback_addressing(prediction),
            "code_improvement": self._evaluate_code_improvement(doc, revised_code),
            "explanation_quality": self._evaluate_explanation_quality(prediction)
        }
        
        return metrics_result
    
    def _process_final_evaluation(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process final evaluation response."""
        metrics_result = {
            "response": prediction,
            "evaluation_completeness": self._evaluate_evaluation_completeness(prediction),
            "improvement_assessment": self._evaluate_improvement_assessment(prediction),
            "rating_provided": self._check_rating_provided(prediction),
            "objectivity": self._evaluate_objectivity(prediction)
        }
        
        return metrics_result
    
    def _evaluate_review_thoroughness(self, review: str) -> float:
        """Evaluate thoroughness of code review."""
        review_aspects = [
            ("functionality", ["function", "logic", "correct", "bug", "error", "algorithm"]),
            ("style", ["style", "formatting", "convention", "pep", "naming", "readable"]),
            ("performance", ["performance", "efficiency", "optimize", "slow", "complexity"]),
            ("security", ["security", "vulnerability", "safe", "validate", "sanitize"]),
            ("maintainability", ["maintain", "readable", "clean", "document", "comment"])
        ]
        
        review_lower = review.lower()
        covered_aspects = 0
        
        for aspect, keywords in review_aspects:
            if any(keyword in review_lower for keyword in keywords):
                covered_aspects += 1
        
        thoroughness = covered_aspects / len(review_aspects)
        
        # Bonus for specific line references or detailed analysis
        if re.search(r"line \d+|:\d+", review, re.IGNORECASE):
            thoroughness += 0.1
        if len(review.split()) > 100:  # Detailed review
            thoroughness += 0.1
            
        return min(thoroughness, 1.0)
    
    def _evaluate_specificity(self, review: str) -> float:
        """Evaluate specificity of review comments."""
        specificity_indicators = [
            len(re.findall(r"line \d+|:\d+", review, re.IGNORECASE)) * 0.2,  # Line references
            len(re.findall(r"```|`[^`]+`", review)) * 0.15,  # Code snippets
            len(re.findall(r"should|could|suggest|recommend|try|consider", review, re.IGNORECASE)) * 0.1,
            len(re.findall(r"instead|replace|change|modify|add|remove", review, re.IGNORECASE)) * 0.1
        ]
        
        return min(sum(specificity_indicators), 1.0)
    
    def _evaluate_actionability(self, review: str) -> float:
        """Evaluate how actionable the review feedback is."""
        actionable_words = [
            "change", "replace", "add", "remove", "modify", "fix", "implement",
            "refactor", "extract", "rename", "move", "delete", "update"
        ]
        
        review_lower = review.lower()
        actionable_count = sum(1 for word in actionable_words if word in review_lower)
        
        # Normalize based on review length
        review_sentences = len(review.split('.'))
        if review_sentences > 0:
            actionability = min(actionable_count / review_sentences, 1.0)
        else:
            actionability = 0.0
            
        return actionability
    
    def _evaluate_security_awareness(self, review: str) -> float:
        """Evaluate security awareness in review."""
        security_keywords = [
            "security", "vulnerability", "exploit", "injection", "xss", "csrf",
            "authentication", "authorization", "validate", "sanitize", "escape"
        ]
        
        review_lower = review.lower()
        security_mentions = sum(1 for keyword in security_keywords if keyword in review_lower)
        
        return min(security_mentions / 3.0, 1.0)  # Normalize to 0-1
    
    def _evaluate_performance_awareness(self, review: str) -> float:
        """Evaluate performance awareness in review."""
        performance_keywords = [
            "performance", "efficiency", "optimize", "slow", "fast", "complexity",
            "algorithm", "time", "space", "memory", "cache", "bottleneck"
        ]
        
        review_lower = review.lower()
        performance_mentions = sum(1 for keyword in performance_keywords if keyword in review_lower)
        
        return min(performance_mentions / 3.0, 1.0)  # Normalize to 0-1
    
    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract code blocks from response."""
        code_blocks = re.findall(r"```(?:\w+)?\n?(.*?)\n?```", response, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        # Try to find code without markdown formatting
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if line.strip().startswith(('def ', 'class ', 'import ', 'from ')):
                in_code = True
            if in_code:
                code_lines.append(line)
            if in_code and line.strip() == '':
                break
                
        return '\n'.join(code_lines) if code_lines else None
    
    def _evaluate_revision_quality(self, response: str, doc: Dict[str, Any]) -> float:
        """Evaluate quality of code revision."""
        quality_indicators = [
            "```" in response,  # Contains code
            len(response.split()) > 50,  # Substantial response
            "change" in response.lower() or "modify" in response.lower(),  # Mentions changes
            "because" in response.lower() or "reason" in response.lower(),  # Provides reasoning
            "improve" in response.lower() or "better" in response.lower()  # Improvement focus
        ]
        
        return sum(quality_indicators) / len(quality_indicators)
    
    def _evaluate_feedback_addressing(self, response: str) -> float:
        """Evaluate how well the revision addresses feedback."""
        if not self.review_comments:
            return 0.0
            
        latest_review = self.review_comments[-1].lower()
        response_lower = response.lower()
        
        # Extract key terms from review
        review_words = set(latest_review.split())
        response_words = set(response_lower.split())
        
        # Calculate overlap
        overlap = len(review_words & response_words)
        total_review_words = len(review_words)
        
        if total_review_words > 0:
            addressing_score = min(overlap / (total_review_words * 0.3), 1.0)
        else:
            addressing_score = 0.0
            
        # Bonus for explicit references to feedback
        if any(phrase in response_lower for phrase in ["feedback", "review", "comment", "suggestion"]):
            addressing_score += 0.2
            
        return min(addressing_score, 1.0)
    
    def _evaluate_code_improvement(self, doc: Dict[str, Any], revised_code: Optional[str]) -> float:
        """Evaluate improvement between original and revised code."""
        if not revised_code:
            return 0.0
            
        original_code = doc.get("code", "")
        if not original_code:
            return 0.0
        
        improvement_indicators = [
            len(revised_code) > len(original_code) * 0.8,  # Not just deletion
            revised_code.count('\n') >= original_code.count('\n'),  # Maintained structure
            revised_code.count('#') > original_code.count('#'),  # More comments
            'def ' in revised_code or 'class ' in revised_code,  # Has functions/classes
            revised_code != original_code  # Actually changed
        ]
        
        return sum(improvement_indicators) / len(improvement_indicators)
    
    def _evaluate_explanation_quality(self, response: str) -> float:
        """Evaluate quality of explanation provided with revision."""
        explanation_indicators = [
            "summary" in response.lower() or "changes" in response.lower(),
            "because" in response.lower() or "reason" in response.lower(),
            len(response.split()) > 100,  # Detailed explanation
            "1." in response or "2." in response,  # Structured explanation
            "address" in response.lower() or "fix" in response.lower()
        ]
        
        return sum(explanation_indicators) / len(explanation_indicators)
    
    def _evaluate_evaluation_completeness(self, evaluation: str) -> float:
        """Evaluate completeness of final evaluation."""
        evaluation_aspects = [
            "original" in evaluation.lower() and "revised" in evaluation.lower(),
            "improvement" in evaluation.lower() or "better" in evaluation.lower(),
            "quality" in evaluation.lower(),
            "remaining" in evaluation.lower() or "issue" in evaluation.lower(),
            "rating" in evaluation.lower() or re.search(r"\d+/10|\d+\s*out\s*of\s*10", evaluation)
        ]
        
        return sum(evaluation_aspects) / len(evaluation_aspects)
    
    def _evaluate_improvement_assessment(self, evaluation: str) -> float:
        """Evaluate quality of improvement assessment."""
        assessment_indicators = [
            "compare" in evaluation.lower() or "comparison" in evaluation.lower(),
            "before" in evaluation.lower() and "after" in evaluation.lower(),
            "significant" in evaluation.lower() or "substantial" in evaluation.lower(),
            len(evaluation.split()) > 80,  # Detailed assessment
            "specific" in evaluation.lower() or "particular" in evaluation.lower()
        ]
        
        return sum(assessment_indicators) / len(assessment_indicators)
    
    def _check_rating_provided(self, evaluation: str) -> float:
        """Check if a numerical rating was provided."""
        rating_patterns = [
            r"\d+/10",
            r"\d+\s*out\s*of\s*10",
            r"rating.*\d+",
            r"score.*\d+",
            r"\d+\s*points?"
        ]
        
        for pattern in rating_patterns:
            if re.search(pattern, evaluation, re.IGNORECASE):
                return 1.0
                
        return 0.0
    
    def _evaluate_objectivity(self, evaluation: str) -> float:
        """Evaluate objectivity of the evaluation."""
        objective_indicators = [
            "objectively" in evaluation.lower() or "objective" in evaluation.lower(),
            "measurable" in evaluation.lower() or "quantifiable" in evaluation.lower(),
            "evidence" in evaluation.lower() or "demonstrate" in evaluation.lower(),
            not any(word in evaluation.lower() for word in ["amazing", "terrible", "awful", "perfect"]),
            "specific" in evaluation.lower() or "concrete" in evaluation.lower()
        ]
        
        return sum(objective_indicators) / len(objective_indicators)
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "review_thoroughness": 0.0,
            "specificity_score": 0.0,
            "actionability_score": 0.0,
            "security_awareness": 0.0,
            "performance_awareness": 0.0,
            "revision_quality": 0.0,
            "feedback_addressing": 0.0,
            "code_improvement": 0.0,
            "explanation_quality": 0.0,
            "evaluation_completeness": 0.0,
            "improvement_assessment": 0.0,
            "rating_provided": 0.0,
            "objectivity": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {
            "review_thoroughness": "mean",
            "specificity_score": "mean",
            "actionability_score": "mean",
            "security_awareness": "mean",
            "performance_awareness": "mean",
            "revision_quality": "mean",
            "feedback_addressing": "mean",
            "code_improvement": "mean",
            "explanation_quality": "mean",
            "evaluation_completeness": "mean",
            "improvement_assessment": "mean",
            "rating_provided": "mean",
            "objectivity": "mean"
        }
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {
            "review_thoroughness": True,
            "specificity_score": True,
            "actionability_score": True,
            "security_awareness": True,
            "performance_awareness": True,
            "revision_quality": True,
            "feedback_addressing": True,
            "code_improvement": True,
            "explanation_quality": True,
            "evaluation_completeness": True,
            "improvement_assessment": True,
            "rating_provided": True,
            "objectivity": True
        }