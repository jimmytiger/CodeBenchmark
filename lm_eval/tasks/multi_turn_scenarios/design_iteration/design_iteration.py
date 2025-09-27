"""Design Iteration multi-turn task implementation."""

import logging
from typing import Dict, List, Any, Optional
import re
import json

from evaluation_engine.core.extended_tasks import MultiTurnTask, ScenarioConfig, ScenarioType, TurnConfig
from lm_eval.api.registry import register_task
from .. import utils, metrics

eval_logger = logging.getLogger(__name__)


@register_task("multi_turn_scenarios_design_iteration")
class DesignIterationTask(MultiTurnTask):
    """
    Multi-turn design iteration evaluation task.
    
    This task evaluates a model's ability to conduct iterative design processes
    including initial proposal, feedback incorporation, refinement, and validation.
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    DATASET_NAME = "multi_turn_scenarios_design_iteration"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize design iteration task."""
        scenario_config = ScenarioConfig(
            scenario_id="design_iteration",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=4,
            conversation_timeout=600,
            enable_context_retention=True,
            turns=[
                TurnConfig(
                    turn_id="initial_proposal",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""You are tasked with creating an initial design proposal for the following project:

**Design Brief**: {design_brief}

**Constraints**:
{constraints_text}

**Stakeholders**: {stakeholders_text}

**Success Criteria**:
{success_criteria_text}

Please provide an initial design proposal that includes:
1. Overall design concept and approach
2. Key features and functionality
3. Technical architecture overview
4. User experience considerations
5. How the design addresses the constraints and success criteria

Present your proposal in a structured format.""",
                    expected_format="structured_proposal",
                    evaluation_metrics=["design_completeness", "constraint_addressing", "innovation_level", "feasibility_assessment"],
                    temperature=0.3,
                    max_tokens=2500
                ),
                TurnConfig(
                    turn_id="stakeholder_feedback",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Based on your initial design proposal, stakeholders have provided the following feedback:

**Your Proposal Summary**: {proposal_summary}

**Stakeholder Feedback**:
{stakeholder_feedback}

Please respond to this feedback by:
1. Acknowledging the key points raised
2. Explaining how you would address each concern
3. Identifying any trade-offs or compromises needed
4. Proposing specific modifications to your design
5. Asking clarifying questions if needed

Maintain a collaborative and professional tone.""",
                    expected_format="feedback_response",
                    depends_on=["initial_proposal"],
                    evaluation_metrics=["feedback_responsiveness", "collaboration_quality", "trade_off_analysis"],
                    temperature=0.2,
                    max_tokens=2000
                ),
                TurnConfig(
                    turn_id="design_refinement",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Now refine your design based on the stakeholder feedback and your response:

**Original Proposal**: {original_proposal}
**Stakeholder Feedback**: {stakeholder_feedback}
**Your Response**: {feedback_response}

Please provide a refined design that:
1. Incorporates the stakeholder feedback
2. Addresses the concerns raised
3. Maintains the core design vision
4. Shows clear improvements from the original
5. Includes updated technical specifications

Highlight what has changed and why these changes improve the design.""",
                    expected_format="refined_design",
                    depends_on=["stakeholder_feedback"],
                    evaluation_metrics=["design_improvement", "feedback_integration", "design_coherence"],
                    temperature=0.2,
                    max_tokens=2500
                ),
                TurnConfig(
                    turn_id="validation_assessment",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Provide a final validation assessment of your refined design:

**Refined Design**: {refined_design}
**Original Requirements**: {original_requirements}

Please assess:
1. How well the refined design meets the original requirements
2. Validation against success criteria
3. Risk assessment and mitigation strategies
4. Implementation roadmap and next steps
5. Metrics for measuring design success

Provide a confidence rating (1-10) for the design's likelihood of success.""",
                    expected_format="validation_assessment",
                    depends_on=["design_refinement"],
                    evaluation_metrics=["validation_thoroughness", "risk_assessment", "success_prediction"],
                    temperature=0.1,
                    max_tokens=2000
                )
            ],
            scenario_metrics=[
                "design_iteration_effectiveness",
                "stakeholder_collaboration",
                "design_quality_improvement",
                "overall_design_process_score"
            ],
            success_criteria={
                "design_iteration_effectiveness": 0.7,
                "stakeholder_collaboration": 0.8,
                "design_quality_improvement": 0.6
            }
        )
        
        super().__init__(
            data_dir=data_dir,
            cache_dir=cache_dir,
            download_mode=download_mode,
            config=config,
            scenario_config=scenario_config
        )
        
        self.design_proposals = []
        self.stakeholder_feedback_history = []
        self.design_iterations = []
        
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
            dataset_dict = utils.load_dataset(metadata={"scenario": "design_iteration"})
            if not dataset_dict.get("test"):
                # Create sample scenarios if none exist
                sample_scenarios = utils.create_sample_scenarios("design_iteration", 5)
                dataset_dict = {"test": sample_scenarios}
            
            dataset = dataset_dict["test"]
            processed_dataset = utils.process_docs(dataset)
            
            eval_logger.info(f"Loaded {len(processed_dataset)} design iteration scenarios")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load design iteration dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """Process model results for multi-turn design iteration."""
        if not results:
            return self._empty_results()
            
        turn_id = self._determine_current_turn(doc)
        prediction = results[0] if results else ""
        
        if turn_id == "initial_proposal":
            return self._process_initial_proposal(doc, prediction)
        elif turn_id == "stakeholder_feedback":
            return self._process_stakeholder_feedback(doc, prediction)
        elif turn_id == "design_refinement":
            return self._process_design_refinement(doc, prediction)
        elif turn_id == "validation_assessment":
            return self._process_validation_assessment(doc, prediction)
        else:
            return self._empty_results()
    
    def _determine_current_turn(self, doc: Dict[str, Any]) -> str:
        """Determine current turn based on conversation state."""
        turn_count = len(getattr(self, '_conversation_history', []))
        turns = ["initial_proposal", "stakeholder_feedback", "design_refinement", "validation_assessment"]
        return turns[min(turn_count, len(turns) - 1)]
    
    def _process_initial_proposal(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process initial design proposal response."""
        self.design_proposals.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "design_completeness": self._evaluate_design_completeness(prediction),
            "constraint_addressing": self._evaluate_constraint_addressing(prediction, doc),
            "innovation_level": self._evaluate_innovation_level(prediction),
            "feasibility_assessment": self._evaluate_feasibility_assessment(prediction),
            "structure_quality": self._evaluate_structure_quality(prediction),
            "technical_depth": self._evaluate_technical_depth(prediction)
        }
        
        return metrics_result
    
    def _process_stakeholder_feedback(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process stakeholder feedback response."""
        feedback = self._generate_stakeholder_feedback(doc, self.design_proposals[-1] if self.design_proposals else "")
        self.stakeholder_feedback_history.append(feedback)
        
        metrics_result = {
            "response": prediction,
            "feedback_responsiveness": self._evaluate_feedback_responsiveness(prediction, feedback),
            "collaboration_quality": self._evaluate_collaboration_quality(prediction),
            "trade_off_analysis": self._evaluate_trade_off_analysis(prediction),
            "professionalism": self._evaluate_professionalism(prediction),
            "clarification_seeking": self._evaluate_clarification_seeking(prediction)
        }
        
        return metrics_result
    
    def _process_design_refinement(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process design refinement response."""
        self.design_iterations.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "design_improvement": self._evaluate_design_improvement(prediction, doc),
            "feedback_integration": self._evaluate_feedback_integration(prediction),
            "design_coherence": self._evaluate_design_coherence(prediction),
            "change_justification": self._evaluate_change_justification(prediction),
            "technical_advancement": self._evaluate_technical_advancement(prediction)
        }
        
        return metrics_result
    
    def _process_validation_assessment(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process validation assessment response."""
        metrics_result = {
            "response": prediction,
            "validation_thoroughness": self._evaluate_validation_thoroughness(prediction),
            "risk_assessment": self._evaluate_risk_assessment(prediction),
            "success_prediction": self._evaluate_success_prediction(prediction),
            "implementation_planning": self._evaluate_implementation_planning(prediction),
            "metrics_definition": self._evaluate_metrics_definition(prediction)
        }
        
        return metrics_result
    
    def _generate_stakeholder_feedback(self, doc: Dict[str, Any], proposal: str) -> str:
        """Generate realistic stakeholder feedback based on the proposal."""
        feedback_templates = [
            "The design looks promising, but we're concerned about the scalability aspects. How will this handle {scale_concern}?",
            "Great innovation in the user experience! However, we need to consider the budget constraints more carefully.",
            "The technical architecture seems solid, but we're worried about the timeline. Can we simplify some features?",
            "Love the overall concept! Could we explore alternative approaches for the {technical_aspect} component?",
            "This addresses most of our requirements well. What about accessibility and compliance considerations?"
        ]
        
        import random
        template = random.choice(feedback_templates)
        
        # Fill in template variables based on doc content
        scale_concern = random.choice(["high user load", "data volume", "concurrent users"])
        technical_aspect = random.choice(["authentication", "data storage", "user interface"])
        
        return template.format(scale_concern=scale_concern, technical_aspect=technical_aspect)
    
    def _evaluate_design_completeness(self, proposal: str) -> float:
        """Evaluate completeness of design proposal."""
        completeness_indicators = [
            "concept" in proposal.lower() or "approach" in proposal.lower(),
            "features" in proposal.lower() or "functionality" in proposal.lower(),
            "architecture" in proposal.lower() or "technical" in proposal.lower(),
            "user" in proposal.lower() or "experience" in proposal.lower(),
            "constraint" in proposal.lower() or "requirement" in proposal.lower(),
            len(re.findall(r"\d+\.", proposal)) >= 3,  # Structured points
            len(proposal.split()) > 200  # Comprehensive response
        ]
        
        return sum(completeness_indicators) / len(completeness_indicators)
    
    def _evaluate_constraint_addressing(self, proposal: str, doc: Dict[str, Any]) -> float:
        """Evaluate how well the proposal addresses constraints."""
        constraints = doc.get("constraints", [])
        if not constraints:
            return 0.5
        
        proposal_lower = proposal.lower()
        addressed_constraints = 0
        
        for constraint in constraints:
            constraint_words = constraint.lower().split()[:3]  # First 3 words
            if any(word in proposal_lower for word in constraint_words):
                addressed_constraints += 1
        
        base_score = addressed_constraints / len(constraints) if constraints else 0.5
        
        # Bonus for explicit constraint discussion
        if "constraint" in proposal_lower or "limitation" in proposal_lower:
            base_score += 0.2
        
        return min(base_score, 1.0)
    
    def _evaluate_innovation_level(self, proposal: str) -> float:
        """Evaluate innovation level of the proposal."""
        innovation_indicators = [
            "innovative" in proposal.lower() or "novel" in proposal.lower(),
            "creative" in proposal.lower() or "unique" in proposal.lower(),
            "cutting-edge" in proposal.lower() or "advanced" in proposal.lower(),
            "breakthrough" in proposal.lower() or "revolutionary" in proposal.lower(),
            len(re.findall(r"new|fresh|original", proposal, re.IGNORECASE)) > 0,
            "approach" in proposal.lower() and "different" in proposal.lower()
        ]
        
        return sum(innovation_indicators) / len(innovation_indicators)
    
    def _evaluate_feasibility_assessment(self, proposal: str) -> float:
        """Evaluate feasibility assessment in the proposal."""
        feasibility_indicators = [
            "feasible" in proposal.lower() or "achievable" in proposal.lower(),
            "realistic" in proposal.lower() or "practical" in proposal.lower(),
            "timeline" in proposal.lower() or "schedule" in proposal.lower(),
            "resource" in proposal.lower() or "budget" in proposal.lower(),
            "risk" in proposal.lower() or "challenge" in proposal.lower(),
            "implementation" in proposal.lower() or "execution" in proposal.lower()
        ]
        
        return sum(feasibility_indicators) / len(feasibility_indicators)
    
    def _evaluate_structure_quality(self, response: str) -> float:
        """Evaluate structural quality of response."""
        structure_indicators = [
            len(re.findall(r"\d+\.", response)) >= 3,  # Numbered points
            len(response.split('\n')) > 5,  # Multiple paragraphs
            "overview" in response.lower() or "summary" in response.lower(),
            "conclusion" in response.lower() or "summary" in response.lower(),
            len(response.split()) > 150  # Adequate length
        ]
        
        return sum(structure_indicators) / len(structure_indicators)
    
    def _evaluate_technical_depth(self, proposal: str) -> float:
        """Evaluate technical depth of the proposal."""
        technical_indicators = [
            "architecture" in proposal.lower() or "system" in proposal.lower(),
            "database" in proposal.lower() or "storage" in proposal.lower(),
            "api" in proposal.lower() or "interface" in proposal.lower(),
            "security" in proposal.lower() or "authentication" in proposal.lower(),
            "performance" in proposal.lower() or "scalability" in proposal.lower(),
            "technology" in proposal.lower() or "framework" in proposal.lower()
        ]
        
        return sum(technical_indicators) / len(technical_indicators)
    
    def _evaluate_feedback_responsiveness(self, response: str, feedback: str) -> float:
        """Evaluate responsiveness to stakeholder feedback."""
        response_lower = response.lower()
        feedback_lower = feedback.lower()
        
        responsiveness_indicators = [
            "acknowledge" in response_lower or "understand" in response_lower,
            "address" in response_lower or "respond" in response_lower,
            "concern" in response_lower or "feedback" in response_lower,
            len(response.split()) > 100,  # Comprehensive response
            any(word in response_lower for word in feedback_lower.split()[:5])  # References feedback content
        ]
        
        return sum(responsiveness_indicators) / len(responsiveness_indicators)
    
    def _evaluate_collaboration_quality(self, response: str) -> float:
        """Evaluate collaboration quality in response."""
        collaboration_indicators = [
            "we" in response.lower() or "our" in response.lower(),
            "together" in response.lower() or "collaborate" in response.lower(),
            "team" in response.lower() or "stakeholder" in response.lower(),
            "appreciate" in response.lower() or "thank" in response.lower(),
            "understand" in response.lower() or "agree" in response.lower(),
            not any(word in response.lower() for word in ["wrong", "incorrect", "disagree"])
        ]
        
        return sum(collaboration_indicators) / len(collaboration_indicators)
    
    def _evaluate_trade_off_analysis(self, response: str) -> float:
        """Evaluate trade-off analysis quality."""
        tradeoff_indicators = [
            "trade-off" in response.lower() or "tradeoff" in response.lower(),
            "compromise" in response.lower() or "balance" in response.lower(),
            "pros and cons" in response.lower() or "advantages" in response.lower(),
            "however" in response.lower() or "but" in response.lower(),
            "alternative" in response.lower() or "option" in response.lower()
        ]
        
        return sum(tradeoff_indicators) / len(tradeoff_indicators)
    
    def _evaluate_professionalism(self, response: str) -> float:
        """Evaluate professionalism in response."""
        professionalism_indicators = [
            not any(word in response.lower() for word in ["stupid", "dumb", "ridiculous"]),
            "professional" in response.lower() or "respectful" in response.lower(),
            len(response.split()) > 50,  # Adequate length
            response.count("!") <= 2,  # Not overly enthusiastic
            "thank" in response.lower() or "appreciate" in response.lower()
        ]
        
        return sum(professionalism_indicators) / len(professionalism_indicators)
    
    def _evaluate_clarification_seeking(self, response: str) -> float:
        """Evaluate quality of clarification seeking."""
        clarification_indicators = [
            "?" in response,  # Contains questions
            "clarify" in response.lower() or "clarification" in response.lower(),
            "understand" in response.lower() or "confirm" in response.lower(),
            "could you" in response.lower() or "would you" in response.lower(),
            "more information" in response.lower() or "details" in response.lower()
        ]
        
        return sum(clarification_indicators) / len(clarification_indicators)
    
    def _evaluate_design_improvement(self, refinement: str, doc: Dict[str, Any]) -> float:
        """Evaluate design improvement in refinement."""
        improvement_indicators = [
            "improve" in refinement.lower() or "better" in refinement.lower(),
            "enhance" in refinement.lower() or "upgrade" in refinement.lower(),
            "refine" in refinement.lower() or "optimize" in refinement.lower(),
            "change" in refinement.lower() or "modify" in refinement.lower(),
            "update" in refinement.lower() or "revise" in refinement.lower(),
            len(refinement.split()) > 200  # Comprehensive refinement
        ]
        
        return sum(improvement_indicators) / len(improvement_indicators)
    
    def _evaluate_feedback_integration(self, refinement: str) -> float:
        """Evaluate integration of feedback into refinement."""
        if not self.stakeholder_feedback_history:
            return 0.5
        
        latest_feedback = self.stakeholder_feedback_history[-1].lower()
        refinement_lower = refinement.lower()
        
        integration_indicators = [
            "based on feedback" in refinement_lower or "incorporating" in refinement_lower,
            "as suggested" in refinement_lower or "as requested" in refinement_lower,
            "feedback" in refinement_lower or "input" in refinement_lower,
            any(word in refinement_lower for word in latest_feedback.split()[:5]),
            "address" in refinement_lower or "resolve" in refinement_lower
        ]
        
        return sum(integration_indicators) / len(integration_indicators)
    
    def _evaluate_design_coherence(self, refinement: str) -> float:
        """Evaluate coherence of refined design."""
        coherence_indicators = [
            "consistent" in refinement.lower() or "coherent" in refinement.lower(),
            "align" in refinement.lower() or "integrate" in refinement.lower(),
            "overall" in refinement.lower() or "holistic" in refinement.lower(),
            len(re.findall(r"\d+\.", refinement)) >= 3,  # Structured
            "maintain" in refinement.lower() or "preserve" in refinement.lower()
        ]
        
        return sum(coherence_indicators) / len(coherence_indicators)
    
    def _evaluate_change_justification(self, refinement: str) -> float:
        """Evaluate justification of changes made."""
        justification_indicators = [
            "because" in refinement.lower() or "since" in refinement.lower(),
            "reason" in refinement.lower() or "rationale" in refinement.lower(),
            "why" in refinement.lower() or "justification" in refinement.lower(),
            "therefore" in refinement.lower() or "thus" in refinement.lower(),
            "improve" in refinement.lower() and "by" in refinement.lower()
        ]
        
        return sum(justification_indicators) / len(justification_indicators)
    
    def _evaluate_technical_advancement(self, refinement: str) -> float:
        """Evaluate technical advancement in refinement."""
        advancement_indicators = [
            "technical" in refinement.lower() or "technology" in refinement.lower(),
            "architecture" in refinement.lower() or "system" in refinement.lower(),
            "performance" in refinement.lower() or "efficiency" in refinement.lower(),
            "scalability" in refinement.lower() or "reliability" in refinement.lower(),
            "security" in refinement.lower() or "robust" in refinement.lower()
        ]
        
        return sum(advancement_indicators) / len(advancement_indicators)
    
    def _evaluate_validation_thoroughness(self, assessment: str) -> float:
        """Evaluate thoroughness of validation assessment."""
        thoroughness_indicators = [
            "validation" in assessment.lower() or "validate" in assessment.lower(),
            "assess" in assessment.lower() or "evaluation" in assessment.lower(),
            "criteria" in assessment.lower() or "requirement" in assessment.lower(),
            "success" in assessment.lower() or "failure" in assessment.lower(),
            "metric" in assessment.lower() or "measure" in assessment.lower(),
            len(assessment.split()) > 150  # Comprehensive assessment
        ]
        
        return sum(thoroughness_indicators) / len(thoroughness_indicators)
    
    def _evaluate_risk_assessment(self, assessment: str) -> float:
        """Evaluate risk assessment quality."""
        risk_indicators = [
            "risk" in assessment.lower() or "threat" in assessment.lower(),
            "challenge" in assessment.lower() or "obstacle" in assessment.lower(),
            "mitigation" in assessment.lower() or "contingency" in assessment.lower(),
            "probability" in assessment.lower() or "likelihood" in assessment.lower(),
            "impact" in assessment.lower() or "consequence" in assessment.lower()
        ]
        
        return sum(risk_indicators) / len(risk_indicators)
    
    def _evaluate_success_prediction(self, assessment: str) -> float:
        """Evaluate success prediction quality."""
        prediction_indicators = [
            "confidence" in assessment.lower() or "likely" in assessment.lower(),
            "success" in assessment.lower() or "achieve" in assessment.lower(),
            "rating" in assessment.lower() or "score" in assessment.lower(),
            re.search(r"\d+/10|\d+\s*out\s*of\s*10", assessment) is not None,
            "predict" in assessment.lower() or "forecast" in assessment.lower()
        ]
        
        return sum(prediction_indicators) / len(prediction_indicators)
    
    def _evaluate_implementation_planning(self, assessment: str) -> float:
        """Evaluate implementation planning quality."""
        planning_indicators = [
            "implementation" in assessment.lower() or "execute" in assessment.lower(),
            "roadmap" in assessment.lower() or "plan" in assessment.lower(),
            "step" in assessment.lower() or "phase" in assessment.lower(),
            "timeline" in assessment.lower() or "schedule" in assessment.lower(),
            "next" in assessment.lower() or "future" in assessment.lower()
        ]
        
        return sum(planning_indicators) / len(planning_indicators)
    
    def _evaluate_metrics_definition(self, assessment: str) -> float:
        """Evaluate metrics definition quality."""
        metrics_indicators = [
            "metric" in assessment.lower() or "measure" in assessment.lower(),
            "kpi" in assessment.lower() or "indicator" in assessment.lower(),
            "track" in assessment.lower() or "monitor" in assessment.lower(),
            "success" in assessment.lower() and "measure" in assessment.lower(),
            re.search(r"\d+%|\d+\s*percent", assessment) is not None
        ]
        
        return sum(metrics_indicators) / len(metrics_indicators)
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "design_completeness": 0.0,
            "constraint_addressing": 0.0,
            "innovation_level": 0.0,
            "feasibility_assessment": 0.0,
            "structure_quality": 0.0,
            "technical_depth": 0.0,
            "feedback_responsiveness": 0.0,
            "collaboration_quality": 0.0,
            "trade_off_analysis": 0.0,
            "professionalism": 0.0,
            "clarification_seeking": 0.0,
            "design_improvement": 0.0,
            "feedback_integration": 0.0,
            "design_coherence": 0.0,
            "change_justification": 0.0,
            "technical_advancement": 0.0,
            "validation_thoroughness": 0.0,
            "risk_assessment": 0.0,
            "success_prediction": 0.0,
            "implementation_planning": 0.0,
            "metrics_definition": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {metric: "mean" for metric in self._empty_results().keys()}
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {metric: True for metric in self._empty_results().keys()}