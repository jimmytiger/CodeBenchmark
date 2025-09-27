"""Requirements Refinement multi-turn task implementation."""

import logging
from typing import Dict, List, Any, Optional
import re
import json

from evaluation_engine.core.extended_tasks import MultiTurnTask, ScenarioConfig, ScenarioType, TurnConfig
from lm_eval.api.registry import register_task
from .. import utils, metrics

eval_logger = logging.getLogger(__name__)


@register_task("multi_turn_scenarios_requirements_refinement")
class RequirementsRefinementTask(MultiTurnTask):
    """
    Multi-turn requirements refinement evaluation task.
    
    This task evaluates a model's ability to conduct requirements analysis and refinement
    including initial analysis, clarification, specification, validation, and finalization.
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    DATASET_NAME = "multi_turn_scenarios_requirements_refinement"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize requirements refinement task."""
        scenario_config = ScenarioConfig(
            scenario_id="requirements_refinement",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=5,
            conversation_timeout=900,
            enable_context_retention=True,
            turns=[
                TurnConfig(
                    turn_id="initial_analysis",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""You are a Business Analyst working on requirements refinement for:

**Initial Requirement**: {initial_requirement}
**Stakeholders**: {stakeholders_text}
**Domain**: {domain}

Please conduct an initial analysis by:
1. Breaking down the high-level requirement into key components
2. Identifying potential ambiguities or gaps in the requirement
3. Listing assumptions that need to be validated
4. Identifying stakeholder concerns and perspectives
5. Proposing initial functional and non-functional requirements
6. Highlighting areas that need further clarification

Present your analysis in a structured format suitable for stakeholder review.""",
                    expected_format="requirements_analysis",
                    evaluation_metrics=["analysis_depth", "gap_identification", "stakeholder_awareness", "structure_quality"],
                    temperature=0.2,
                    max_tokens=2500
                ),
                TurnConfig(
                    turn_id="clarification_session",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Based on your initial analysis, stakeholders have provided input:

**Your Analysis**: {analysis_summary}
**Stakeholder Input**: {stakeholder_input}

Please conduct a clarification session by:
1. Addressing the stakeholder input and questions
2. Asking targeted follow-up questions to resolve ambiguities
3. Validating or refining your initial assumptions
4. Exploring edge cases and exceptional scenarios
5. Clarifying success criteria and acceptance conditions
6. Identifying any conflicting requirements or priorities

Focus on gathering precise information to create clear requirements.""",
                    expected_format="clarification_response",
                    depends_on=["initial_analysis"],
                    evaluation_metrics=["clarification_effectiveness", "question_quality", "assumption_validation", "conflict_identification"],
                    temperature=0.3,
                    max_tokens=2200
                ),
                TurnConfig(
                    turn_id="specification_development",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Now develop detailed specifications based on the clarification:

**Original Requirement**: {initial_requirement}
**Analysis**: {analysis_summary}
**Clarification Results**: {clarification_results}

Please create detailed specifications including:
1. Functional requirements with clear acceptance criteria
2. Non-functional requirements (performance, security, usability)
3. User stories or use cases with scenarios
4. Data requirements and constraints
5. Integration and interface requirements
6. Business rules and validation logic

Ensure each requirement is specific, measurable, and testable.""",
                    expected_format="detailed_specifications",
                    depends_on=["clarification_session"],
                    evaluation_metrics=["specification_completeness", "requirement_clarity", "testability", "traceability"],
                    temperature=0.2,
                    max_tokens=2800
                ),
                TurnConfig(
                    turn_id="validation_review",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Conduct a validation review of the specifications:

**Detailed Specifications**: {specifications_summary}
**Stakeholder Feedback**: {validation_feedback}

Please perform validation by:
1. Reviewing specifications against original business needs
2. Checking for completeness, consistency, and clarity
3. Validating feasibility and technical constraints
4. Ensuring requirements are prioritized appropriately
5. Identifying potential risks or implementation challenges
6. Confirming stakeholder alignment and satisfaction

Provide recommendations for any necessary adjustments.""",
                    expected_format="validation_report",
                    depends_on=["specification_development"],
                    evaluation_metrics=["validation_thoroughness", "consistency_checking", "feasibility_assessment", "risk_identification"],
                    temperature=0.2,
                    max_tokens=2200
                ),
                TurnConfig(
                    turn_id="finalization",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Finalize the requirements based on validation results:

**Validation Results**: {validation_results}
**Final Adjustments Needed**: {final_adjustments}

Please provide the final requirements package:
1. Finalized functional and non-functional requirements
2. Requirements traceability matrix
3. Acceptance criteria and testing guidelines
4. Implementation priorities and dependencies
5. Change management process for future modifications
6. Sign-off recommendations and next steps

This should be the definitive requirements document for development.""",
                    expected_format="final_requirements",
                    depends_on=["validation_review"],
                    evaluation_metrics=["finalization_quality", "documentation_completeness", "implementation_readiness", "change_management"],
                    temperature=0.1,
                    max_tokens=2500
                )
            ],
            scenario_metrics=[
                "requirements_refinement_effectiveness",
                "stakeholder_collaboration_quality",
                "specification_quality",
                "overall_requirements_process_score"
            ],
            success_criteria={
                "requirements_refinement_effectiveness": 0.7,
                "stakeholder_collaboration_quality": 0.8,
                "specification_quality": 0.7
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
        self.clarifications = []
        self.specifications = []
        
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
            dataset_dict = utils.load_dataset(metadata={"scenario": "requirements_refinement"})
            if not dataset_dict.get("test"):
                # Create sample scenarios if none exist
                sample_scenarios = utils.create_sample_scenarios("requirements_refinement", 5)
                dataset_dict = {"test": sample_scenarios}
            
            dataset = dataset_dict["test"]
            processed_dataset = utils.process_docs(dataset)
            
            eval_logger.info(f"Loaded {len(processed_dataset)} requirements refinement scenarios")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load requirements refinement dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """Process model results for multi-turn requirements refinement."""
        if not results:
            return self._empty_results()
            
        turn_id = self._determine_current_turn(doc)
        prediction = results[0] if results else ""
        
        if turn_id == "initial_analysis":
            return self._process_initial_analysis(doc, prediction)
        elif turn_id == "clarification_session":
            return self._process_clarification_session(doc, prediction)
        elif turn_id == "specification_development":
            return self._process_specification_development(doc, prediction)
        elif turn_id == "validation_review":
            return self._process_validation_review(doc, prediction)
        elif turn_id == "finalization":
            return self._process_finalization(doc, prediction)
        else:
            return self._empty_results()
    
    def _determine_current_turn(self, doc: Dict[str, Any]) -> str:
        """Determine current turn based on conversation state."""
        turn_count = len(getattr(self, '_conversation_history', []))
        turns = ["initial_analysis", "clarification_session", "specification_development", 
                "validation_review", "finalization"]
        return turns[min(turn_count, len(turns) - 1)]
    
    def _process_initial_analysis(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process initial analysis response."""
        self.analyses.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "analysis_depth": self._evaluate_analysis_depth(prediction),
            "gap_identification": self._evaluate_gap_identification(prediction),
            "stakeholder_awareness": self._evaluate_stakeholder_awareness(prediction, doc),
            "structure_quality": self._evaluate_structure_quality(prediction),
            "assumption_identification": self._evaluate_assumption_identification(prediction),
            "requirement_decomposition": self._evaluate_requirement_decomposition(prediction)
        }
        
        return metrics_result
    
    def _process_clarification_session(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process clarification session response."""
        stakeholder_input = self._generate_stakeholder_input(doc, self.analyses[-1] if self.analyses else "")
        self.clarifications.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "clarification_effectiveness": self._evaluate_clarification_effectiveness(prediction),
            "question_quality": self._evaluate_question_quality(prediction),
            "assumption_validation": self._evaluate_assumption_validation(prediction),
            "conflict_identification": self._evaluate_conflict_identification(prediction),
            "edge_case_exploration": self._evaluate_edge_case_exploration(prediction)
        }
        
        return metrics_result
    
    def _process_specification_development(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process specification development response."""
        self.specifications.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "specification_completeness": self._evaluate_specification_completeness(prediction),
            "requirement_clarity": self._evaluate_requirement_clarity(prediction),
            "testability": self._evaluate_testability(prediction),
            "traceability": self._evaluate_traceability(prediction),
            "acceptance_criteria_quality": self._evaluate_acceptance_criteria_quality(prediction)
        }
        
        return metrics_result
    
    def _process_validation_review(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process validation review response."""
        metrics_result = {
            "response": prediction,
            "validation_thoroughness": self._evaluate_validation_thoroughness(prediction),
            "consistency_checking": self._evaluate_consistency_checking(prediction),
            "feasibility_assessment": self._evaluate_feasibility_assessment(prediction),
            "risk_identification": self._evaluate_risk_identification(prediction),
            "stakeholder_alignment": self._evaluate_stakeholder_alignment(prediction)
        }
        
        return metrics_result
    
    def _process_finalization(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process finalization response."""
        metrics_result = {
            "response": prediction,
            "finalization_quality": self._evaluate_finalization_quality(prediction),
            "documentation_completeness": self._evaluate_documentation_completeness(prediction),
            "implementation_readiness": self._evaluate_implementation_readiness(prediction),
            "change_management": self._evaluate_change_management(prediction),
            "traceability_matrix": self._evaluate_traceability_matrix(prediction)
        }
        
        return metrics_result
    
    def _generate_stakeholder_input(self, doc: Dict[str, Any], analysis: str) -> str:
        """Generate realistic stakeholder input based on the analysis."""
        input_templates = [
            "Your analysis is comprehensive. However, we need to clarify the {aspect} requirements. What about {specific_concern}?",
            "Good breakdown of the requirements. One concern: how will this handle {scenario}? We've had issues with this before.",
            "The functional requirements look solid. What about performance requirements? We need to support {scale} users.",
            "I see you've identified {component} as a key area. Could you elaborate on the integration with our existing {system}?",
            "The assumptions you've listed are mostly correct, but we need to reconsider {assumption}. The business context has changed."
        ]
        
        import random
        template = random.choice(input_templates)
        
        # Fill in template variables
        aspect = random.choice(["security", "performance", "usability", "integration"])
        specific_concern = random.choice(["data privacy", "user authentication", "system reliability"])
        scenario = random.choice(["high load", "system failures", "concurrent users"])
        scale = random.choice(["10,000", "50,000", "100,000"])
        component = random.choice(["user management", "data processing", "reporting"])
        system = random.choice(["CRM", "ERP", "database"])
        assumption = random.choice(["user behavior", "data volume", "system capacity"])
        
        return template.format(
            aspect=aspect, specific_concern=specific_concern, scenario=scenario,
            scale=scale, component=component, system=system, assumption=assumption
        )
    
    def _evaluate_analysis_depth(self, analysis: str) -> float:
        """Evaluate depth of requirements analysis."""
        depth_indicators = [
            "component" in analysis.lower() or "element" in analysis.lower(),
            "ambiguity" in analysis.lower() or "unclear" in analysis.lower(),
            "assumption" in analysis.lower() or "assume" in analysis.lower(),
            "stakeholder" in analysis.lower() or "user" in analysis.lower(),
            "functional" in analysis.lower() or "non-functional" in analysis.lower(),
            "clarification" in analysis.lower() or "clarify" in analysis.lower(),
            len(analysis.split()) > 200,  # Comprehensive analysis
            len(re.findall(r"\d+\.", analysis)) >= 5  # Structured points
        ]
        
        return sum(depth_indicators) / len(depth_indicators)
    
    def _evaluate_gap_identification(self, analysis: str) -> float:
        """Evaluate gap identification quality."""
        gap_indicators = [
            "gap" in analysis.lower() or "missing" in analysis.lower(),
            "unclear" in analysis.lower() or "ambiguous" in analysis.lower(),
            "undefined" in analysis.lower() or "unspecified" in analysis.lower(),
            "need" in analysis.lower() or "require" in analysis.lower(),
            "incomplete" in analysis.lower() or "partial" in analysis.lower(),
            "question" in analysis.lower() or "clarify" in analysis.lower()
        ]
        
        return sum(gap_indicators) / len(gap_indicators)
    
    def _evaluate_stakeholder_awareness(self, analysis: str, doc: Dict[str, Any]) -> float:
        """Evaluate stakeholder awareness in analysis."""
        stakeholders = doc.get("stakeholders", [])
        analysis_lower = analysis.lower()
        
        awareness_indicators = [
            "stakeholder" in analysis_lower or "user" in analysis_lower,
            "perspective" in analysis_lower or "viewpoint" in analysis_lower,
            "concern" in analysis_lower or "interest" in analysis_lower,
            "business" in analysis_lower or "organization" in analysis_lower,
            "end user" in analysis_lower or "customer" in analysis_lower
        ]
        
        # Check if specific stakeholders are mentioned
        if stakeholders:
            stakeholder_mentions = sum(1 for stakeholder in stakeholders 
                                     if any(word in analysis_lower for word in stakeholder.lower().split()))
            awareness_indicators.append(stakeholder_mentions > 0)
        
        return sum(awareness_indicators) / len(awareness_indicators)
    
    def _evaluate_structure_quality(self, analysis: str) -> float:
        """Evaluate structural quality of analysis."""
        structure_indicators = [
            len(re.findall(r"\d+\.", analysis)) >= 4,  # Numbered points
            len(analysis.split('\n')) > 8,  # Well-formatted
            "analysis" in analysis.lower() or "breakdown" in analysis.lower(),
            "summary" in analysis.lower() or "overview" in analysis.lower(),
            len(analysis.split()) > 150  # Adequate detail
        ]
        
        return sum(structure_indicators) / len(structure_indicators)
    
    def _evaluate_assumption_identification(self, analysis: str) -> float:
        """Evaluate assumption identification quality."""
        assumption_indicators = [
            "assumption" in analysis.lower() or "assume" in analysis.lower(),
            "validate" in analysis.lower() or "verify" in analysis.lower(),
            "confirm" in analysis.lower() or "check" in analysis.lower(),
            "uncertain" in analysis.lower() or "unclear" in analysis.lower(),
            "need to" in analysis.lower() or "should" in analysis.lower()
        ]
        
        return sum(assumption_indicators) / len(assumption_indicators)
    
    def _evaluate_requirement_decomposition(self, analysis: str) -> float:
        """Evaluate requirement decomposition quality."""
        decomposition_indicators = [
            "break down" in analysis.lower() or "decompose" in analysis.lower(),
            "component" in analysis.lower() or "part" in analysis.lower(),
            "functional" in analysis.lower() or "feature" in analysis.lower(),
            "non-functional" in analysis.lower() or "quality" in analysis.lower(),
            "requirement" in analysis.lower() or "need" in analysis.lower()
        ]
        
        return sum(decomposition_indicators) / len(decomposition_indicators)
    
    def _evaluate_clarification_effectiveness(self, response: str) -> float:
        """Evaluate clarification effectiveness."""
        clarification_indicators = [
            "clarify" in response.lower() or "clarification" in response.lower(),
            "question" in response.lower() or "ask" in response.lower(),
            "understand" in response.lower() or "confirm" in response.lower(),
            "specific" in response.lower() or "precise" in response.lower(),
            "example" in response.lower() or "scenario" in response.lower(),
            len(response.split()) > 100  # Comprehensive response
        ]
        
        return sum(clarification_indicators) / len(clarification_indicators)
    
    def _evaluate_question_quality(self, response: str) -> float:
        """Evaluate quality of clarification questions."""
        question_indicators = [
            response.count("?") >= 3,  # Multiple questions
            "what" in response.lower() or "how" in response.lower(),
            "when" in response.lower() or "where" in response.lower(),
            "why" in response.lower() or "which" in response.lower(),
            "specific" in response.lower() or "exactly" in response.lower(),
            "scenario" in response.lower() or "case" in response.lower()
        ]
        
        return sum(question_indicators) / len(question_indicators)
    
    def _evaluate_assumption_validation(self, response: str) -> float:
        """Evaluate assumption validation approach."""
        validation_indicators = [
            "assumption" in response.lower() or "assume" in response.lower(),
            "validate" in response.lower() or "verify" in response.lower(),
            "confirm" in response.lower() or "check" in response.lower(),
            "correct" in response.lower() or "accurate" in response.lower(),
            "refine" in response.lower() or "adjust" in response.lower()
        ]
        
        return sum(validation_indicators) / len(validation_indicators)
    
    def _evaluate_conflict_identification(self, response: str) -> float:
        """Evaluate conflict identification capability."""
        conflict_indicators = [
            "conflict" in response.lower() or "contradiction" in response.lower(),
            "priority" in response.lower() or "prioritize" in response.lower(),
            "trade-off" in response.lower() or "balance" in response.lower(),
            "competing" in response.lower() or "conflicting" in response.lower(),
            "resolve" in response.lower() or "address" in response.lower()
        ]
        
        return sum(conflict_indicators) / len(conflict_indicators)
    
    def _evaluate_edge_case_exploration(self, response: str) -> float:
        """Evaluate edge case exploration."""
        edge_case_indicators = [
            "edge case" in response.lower() or "exception" in response.lower(),
            "unusual" in response.lower() or "rare" in response.lower(),
            "what if" in response.lower() or "scenario" in response.lower(),
            "failure" in response.lower() or "error" in response.lower(),
            "boundary" in response.lower() or "limit" in response.lower()
        ]
        
        return sum(edge_case_indicators) / len(edge_case_indicators)
    
    def _evaluate_specification_completeness(self, specification: str) -> float:
        """Evaluate completeness of specifications."""
        completeness_indicators = [
            "functional" in specification.lower() or "feature" in specification.lower(),
            "non-functional" in specification.lower() or "performance" in specification.lower(),
            "user story" in specification.lower() or "use case" in specification.lower(),
            "data" in specification.lower() or "information" in specification.lower(),
            "integration" in specification.lower() or "interface" in specification.lower(),
            "business rule" in specification.lower() or "validation" in specification.lower(),
            len(specification.split()) > 300,  # Comprehensive
            len(re.findall(r"\d+\.", specification)) >= 6  # Multiple sections
        ]
        
        return sum(completeness_indicators) / len(completeness_indicators)
    
    def _evaluate_requirement_clarity(self, specification: str) -> float:
        """Evaluate clarity of requirements."""
        clarity_indicators = [
            "shall" in specification.lower() or "must" in specification.lower(),
            "specific" in specification.lower() or "exactly" in specification.lower(),
            "measurable" in specification.lower() or "quantifiable" in specification.lower(),
            not any(word in specification.lower() for word in ["maybe", "perhaps", "might"]),
            "clear" in specification.lower() or "unambiguous" in specification.lower()
        ]
        
        return sum(clarity_indicators) / len(clarity_indicators)
    
    def _evaluate_testability(self, specification: str) -> float:
        """Evaluate testability of requirements."""
        testability_indicators = [
            "testable" in specification.lower() or "verifiable" in specification.lower(),
            "acceptance criteria" in specification.lower() or "acceptance" in specification.lower(),
            "test" in specification.lower() or "verify" in specification.lower(),
            "measure" in specification.lower() or "metric" in specification.lower(),
            "criteria" in specification.lower() or "condition" in specification.lower()
        ]
        
        return sum(testability_indicators) / len(testability_indicators)
    
    def _evaluate_traceability(self, specification: str) -> float:
        """Evaluate traceability of requirements."""
        traceability_indicators = [
            "trace" in specification.lower() or "traceability" in specification.lower(),
            "link" in specification.lower() or "connect" in specification.lower(),
            "reference" in specification.lower() or "relate" in specification.lower(),
            "id" in specification.lower() or "identifier" in specification.lower(),
            "source" in specification.lower() or "origin" in specification.lower()
        ]
        
        return sum(traceability_indicators) / len(traceability_indicators)
    
    def _evaluate_acceptance_criteria_quality(self, specification: str) -> float:
        """Evaluate acceptance criteria quality."""
        criteria_indicators = [
            "acceptance criteria" in specification.lower() or "acceptance" in specification.lower(),
            "given" in specification.lower() or "when" in specification.lower(),
            "then" in specification.lower() or "should" in specification.lower(),
            "scenario" in specification.lower() or "condition" in specification.lower(),
            "pass" in specification.lower() or "fail" in specification.lower()
        ]
        
        return sum(criteria_indicators) / len(criteria_indicators)
    
    def _evaluate_validation_thoroughness(self, validation: str) -> float:
        """Evaluate validation thoroughness."""
        thoroughness_indicators = [
            "validation" in validation.lower() or "validate" in validation.lower(),
            "review" in validation.lower() or "check" in validation.lower(),
            "completeness" in validation.lower() or "complete" in validation.lower(),
            "consistency" in validation.lower() or "consistent" in validation.lower(),
            "feasibility" in validation.lower() or "feasible" in validation.lower(),
            len(validation.split()) > 150  # Comprehensive validation
        ]
        
        return sum(thoroughness_indicators) / len(thoroughness_indicators)
    
    def _evaluate_consistency_checking(self, validation: str) -> float:
        """Evaluate consistency checking quality."""
        consistency_indicators = [
            "consistency" in validation.lower() or "consistent" in validation.lower(),
            "conflict" in validation.lower() or "contradiction" in validation.lower(),
            "align" in validation.lower() or "alignment" in validation.lower(),
            "coherent" in validation.lower() or "coherence" in validation.lower(),
            "compatible" in validation.lower() or "compatibility" in validation.lower()
        ]
        
        return sum(consistency_indicators) / len(consistency_indicators)
    
    def _evaluate_feasibility_assessment(self, validation: str) -> float:
        """Evaluate feasibility assessment quality."""
        feasibility_indicators = [
            "feasible" in validation.lower() or "feasibility" in validation.lower(),
            "realistic" in validation.lower() or "achievable" in validation.lower(),
            "constraint" in validation.lower() or "limitation" in validation.lower(),
            "resource" in validation.lower() or "budget" in validation.lower(),
            "timeline" in validation.lower() or "schedule" in validation.lower()
        ]
        
        return sum(feasibility_indicators) / len(feasibility_indicators)
    
    def _evaluate_risk_identification(self, validation: str) -> float:
        """Evaluate risk identification quality."""
        risk_indicators = [
            "risk" in validation.lower() or "threat" in validation.lower(),
            "challenge" in validation.lower() or "obstacle" in validation.lower(),
            "issue" in validation.lower() or "problem" in validation.lower(),
            "mitigation" in validation.lower() or "contingency" in validation.lower(),
            "impact" in validation.lower() or "consequence" in validation.lower()
        ]
        
        return sum(risk_indicators) / len(risk_indicators)
    
    def _evaluate_stakeholder_alignment(self, validation: str) -> float:
        """Evaluate stakeholder alignment assessment."""
        alignment_indicators = [
            "stakeholder" in validation.lower() or "user" in validation.lower(),
            "alignment" in validation.lower() or "agree" in validation.lower(),
            "satisfaction" in validation.lower() or "satisfied" in validation.lower(),
            "consensus" in validation.lower() or "agreement" in validation.lower(),
            "approval" in validation.lower() or "accept" in validation.lower()
        ]
        
        return sum(alignment_indicators) / len(alignment_indicators)
    
    def _evaluate_finalization_quality(self, finalization: str) -> float:
        """Evaluate finalization quality."""
        finalization_indicators = [
            "final" in finalization.lower() or "finalize" in finalization.lower(),
            "complete" in finalization.lower() or "comprehensive" in finalization.lower(),
            "definitive" in finalization.lower() or "authoritative" in finalization.lower(),
            "ready" in finalization.lower() or "prepared" in finalization.lower(),
            len(finalization.split()) > 200  # Comprehensive finalization
        ]
        
        return sum(finalization_indicators) / len(finalization_indicators)
    
    def _evaluate_documentation_completeness(self, finalization: str) -> float:
        """Evaluate documentation completeness."""
        documentation_indicators = [
            "document" in finalization.lower() or "documentation" in finalization.lower(),
            "traceability" in finalization.lower() or "matrix" in finalization.lower(),
            "acceptance" in finalization.lower() or "criteria" in finalization.lower(),
            "priority" in finalization.lower() or "dependency" in finalization.lower(),
            "change management" in finalization.lower() or "process" in finalization.lower()
        ]
        
        return sum(documentation_indicators) / len(documentation_indicators)
    
    def _evaluate_implementation_readiness(self, finalization: str) -> float:
        """Evaluate implementation readiness."""
        readiness_indicators = [
            "implementation" in finalization.lower() or "develop" in finalization.lower(),
            "ready" in finalization.lower() or "prepared" in finalization.lower(),
            "priority" in finalization.lower() or "sequence" in finalization.lower(),
            "dependency" in finalization.lower() or "prerequisite" in finalization.lower(),
            "next step" in finalization.lower() or "action" in finalization.lower()
        ]
        
        return sum(readiness_indicators) / len(readiness_indicators)
    
    def _evaluate_change_management(self, finalization: str) -> float:
        """Evaluate change management considerations."""
        change_indicators = [
            "change" in finalization.lower() or "modification" in finalization.lower(),
            "process" in finalization.lower() or "procedure" in finalization.lower(),
            "control" in finalization.lower() or "manage" in finalization.lower(),
            "version" in finalization.lower() or "revision" in finalization.lower(),
            "approval" in finalization.lower() or "authorization" in finalization.lower()
        ]
        
        return sum(change_indicators) / len(change_indicators)
    
    def _evaluate_traceability_matrix(self, finalization: str) -> float:
        """Evaluate traceability matrix quality."""
        matrix_indicators = [
            "traceability" in finalization.lower() or "matrix" in finalization.lower(),
            "trace" in finalization.lower() or "link" in finalization.lower(),
            "requirement" in finalization.lower() or "source" in finalization.lower(),
            "mapping" in finalization.lower() or "relationship" in finalization.lower(),
            "reference" in finalization.lower() or "connection" in finalization.lower()
        ]
        
        return sum(matrix_indicators) / len(matrix_indicators)
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "analysis_depth": 0.0,
            "gap_identification": 0.0,
            "stakeholder_awareness": 0.0,
            "structure_quality": 0.0,
            "assumption_identification": 0.0,
            "requirement_decomposition": 0.0,
            "clarification_effectiveness": 0.0,
            "question_quality": 0.0,
            "assumption_validation": 0.0,
            "conflict_identification": 0.0,
            "edge_case_exploration": 0.0,
            "specification_completeness": 0.0,
            "requirement_clarity": 0.0,
            "testability": 0.0,
            "traceability": 0.0,
            "acceptance_criteria_quality": 0.0,
            "validation_thoroughness": 0.0,
            "consistency_checking": 0.0,
            "feasibility_assessment": 0.0,
            "risk_identification": 0.0,
            "stakeholder_alignment": 0.0,
            "finalization_quality": 0.0,
            "documentation_completeness": 0.0,
            "implementation_readiness": 0.0,
            "change_management": 0.0,
            "traceability_matrix": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {metric: "mean" for metric in self._empty_results().keys()}
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {metric: True for metric in self._empty_results().keys()}