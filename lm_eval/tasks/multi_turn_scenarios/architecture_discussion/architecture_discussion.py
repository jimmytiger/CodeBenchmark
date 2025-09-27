"""Architecture Discussion multi-turn task implementation."""

import logging
from typing import Dict, List, Any, Optional
import re
import json

from evaluation_engine.core.extended_tasks import MultiTurnTask, ScenarioConfig, ScenarioType, TurnConfig
from lm_eval.api.registry import register_task
from .. import utils, metrics

eval_logger = logging.getLogger(__name__)


@register_task("multi_turn_scenarios_architecture_discussion")
class ArchitectureDiscussionTask(MultiTurnTask):
    """
    Multi-turn architecture discussion evaluation task.
    
    This task evaluates a model's ability to conduct system architecture discussions
    including initial design, stakeholder input, trade-off analysis, and decision documentation.
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    DATASET_NAME = "multi_turn_scenarios_architecture_discussion"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize architecture discussion task."""
        scenario_config = ScenarioConfig(
            scenario_id="architecture_discussion",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=4,
            conversation_timeout=600,
            enable_context_retention=True,
            turns=[
                TurnConfig(
                    turn_id="initial_architecture",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""You are leading an architecture discussion for the following system:

**System Requirements**: {system_requirements}
**Scale Requirements**: {scale_requirements}
**Technical Constraints**: {technical_constraints_text}
**Stakeholders**: {stakeholders_text}

Please present an initial system architecture proposal that includes:
1. High-level system architecture overview
2. Key components and their responsibilities
3. Data flow and communication patterns
4. Technology stack recommendations
5. Scalability and performance considerations
6. Security and reliability measures

Present your architecture in a clear, structured format suitable for technical stakeholders.""",
                    expected_format="architecture_proposal",
                    evaluation_metrics=["architecture_completeness", "technical_depth", "scalability_consideration", "clarity"],
                    temperature=0.2,
                    max_tokens=2500
                ),
                TurnConfig(
                    turn_id="stakeholder_input",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""The stakeholders have provided input on your architecture proposal:

**Your Architecture Proposal**: {architecture_summary}

**Stakeholder Input**:
{stakeholder_input}

Please respond by:
1. Acknowledging the stakeholder concerns and suggestions
2. Explaining your architectural decisions and rationale
3. Identifying areas where modifications might be beneficial
4. Discussing potential alternatives or variations
5. Asking for clarification on any ambiguous points

Maintain a collaborative tone and demonstrate deep technical understanding.""",
                    expected_format="stakeholder_response",
                    depends_on=["initial_architecture"],
                    evaluation_metrics=["stakeholder_engagement", "technical_justification", "flexibility_demonstration"],
                    temperature=0.2,
                    max_tokens=2000
                ),
                TurnConfig(
                    turn_id="trade_off_analysis",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Based on the discussion, please provide a comprehensive trade-off analysis:

**Original Architecture**: {original_architecture}
**Stakeholder Input**: {stakeholder_input}
**Your Response**: {stakeholder_response}

Analyze the trade-offs for key architectural decisions:
1. Performance vs. Complexity trade-offs
2. Cost vs. Scalability considerations
3. Security vs. Usability balance
4. Maintainability vs. Feature richness
5. Time-to-market vs. Technical debt

For each trade-off, explain the implications and recommend the best approach given the constraints.""",
                    expected_format="trade_off_analysis",
                    depends_on=["stakeholder_input"],
                    evaluation_metrics=["trade_off_depth", "decision_rationale", "constraint_consideration"],
                    temperature=0.1,
                    max_tokens=2200
                ),
                TurnConfig(
                    turn_id="final_decision",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Provide the final architectural decision and documentation:

**Trade-off Analysis**: {trade_off_analysis}
**All Previous Discussion**: {discussion_summary}

Please document:
1. Final recommended architecture with key decisions
2. Rationale for major architectural choices
3. Risk assessment and mitigation strategies
4. Implementation roadmap and phases
5. Success metrics and monitoring approach
6. Future evolution and extensibility considerations

This should serve as the definitive architectural documentation for the development team.""",
                    expected_format="final_architecture_doc",
                    depends_on=["trade_off_analysis"],
                    evaluation_metrics=["decision_clarity", "documentation_quality", "implementation_guidance"],
                    temperature=0.1,
                    max_tokens=2500
                )
            ],
            scenario_metrics=[
                "architecture_discussion_effectiveness",
                "technical_leadership",
                "decision_making_quality",
                "overall_architecture_process_score"
            ],
            success_criteria={
                "architecture_discussion_effectiveness": 0.7,
                "technical_leadership": 0.8,
                "decision_making_quality": 0.7
            }
        )
        
        super().__init__(
            data_dir=data_dir,
            cache_dir=cache_dir,
            download_mode=download_mode,
            config=config,
            scenario_config=scenario_config
        )
        
        self.architecture_proposals = []
        self.stakeholder_inputs = []
        self.trade_off_analyses = []
        
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
            dataset_dict = utils.load_dataset(metadata={"scenario": "architecture_discussion"})
            if not dataset_dict.get("test"):
                # Create sample scenarios if none exist
                sample_scenarios = utils.create_sample_scenarios("architecture_discussion", 5)
                dataset_dict = {"test": sample_scenarios}
            
            dataset = dataset_dict["test"]
            processed_dataset = utils.process_docs(dataset)
            
            eval_logger.info(f"Loaded {len(processed_dataset)} architecture discussion scenarios")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load architecture discussion dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """Process model results for multi-turn architecture discussion."""
        if not results:
            return self._empty_results()
            
        turn_id = self._determine_current_turn(doc)
        prediction = results[0] if results else ""
        
        if turn_id == "initial_architecture":
            return self._process_initial_architecture(doc, prediction)
        elif turn_id == "stakeholder_input":
            return self._process_stakeholder_input(doc, prediction)
        elif turn_id == "trade_off_analysis":
            return self._process_trade_off_analysis(doc, prediction)
        elif turn_id == "final_decision":
            return self._process_final_decision(doc, prediction)
        else:
            return self._empty_results()
    
    def _determine_current_turn(self, doc: Dict[str, Any]) -> str:
        """Determine current turn based on conversation state."""
        turn_count = len(getattr(self, '_conversation_history', []))
        turns = ["initial_architecture", "stakeholder_input", "trade_off_analysis", "final_decision"]
        return turns[min(turn_count, len(turns) - 1)]
    
    def _process_initial_architecture(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process initial architecture proposal response."""
        self.architecture_proposals.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "architecture_completeness": self._evaluate_architecture_completeness(prediction),
            "technical_depth": self._evaluate_technical_depth(prediction),
            "scalability_consideration": self._evaluate_scalability_consideration(prediction),
            "clarity": self._evaluate_clarity(prediction),
            "component_definition": self._evaluate_component_definition(prediction),
            "technology_justification": self._evaluate_technology_justification(prediction)
        }
        
        return metrics_result
    
    def _process_stakeholder_input(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process stakeholder input response."""
        stakeholder_input = self._generate_stakeholder_input(doc, self.architecture_proposals[-1] if self.architecture_proposals else "")
        self.stakeholder_inputs.append(stakeholder_input)
        
        metrics_result = {
            "response": prediction,
            "stakeholder_engagement": self._evaluate_stakeholder_engagement(prediction),
            "technical_justification": self._evaluate_technical_justification(prediction),
            "flexibility_demonstration": self._evaluate_flexibility_demonstration(prediction),
            "communication_effectiveness": self._evaluate_communication_effectiveness(prediction),
            "problem_solving_approach": self._evaluate_problem_solving_approach(prediction)
        }
        
        return metrics_result
    
    def _process_trade_off_analysis(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process trade-off analysis response."""
        self.trade_off_analyses.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "trade_off_depth": self._evaluate_trade_off_depth(prediction),
            "decision_rationale": self._evaluate_decision_rationale(prediction),
            "constraint_consideration": self._evaluate_constraint_consideration(prediction),
            "analytical_thinking": self._evaluate_analytical_thinking(prediction),
            "comprehensive_coverage": self._evaluate_comprehensive_coverage(prediction)
        }
        
        return metrics_result
    
    def _process_final_decision(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process final decision response."""
        metrics_result = {
            "response": prediction,
            "decision_clarity": self._evaluate_decision_clarity(prediction),
            "documentation_quality": self._evaluate_documentation_quality(prediction),
            "implementation_guidance": self._evaluate_implementation_guidance(prediction),
            "risk_management": self._evaluate_risk_management(prediction),
            "future_considerations": self._evaluate_future_considerations(prediction)
        }
        
        return metrics_result
    
    def _generate_stakeholder_input(self, doc: Dict[str, Any], architecture: str) -> str:
        """Generate realistic stakeholder input based on the architecture."""
        input_templates = [
            "The architecture looks solid overall. However, we're concerned about the complexity of the {component} component. Could we simplify this?",
            "Great work on the scalability aspects! One question: how will this handle {concern} in production?",
            "The technology choices seem appropriate. What about the operational overhead of managing {technology}?",
            "I like the modular approach. Could we consider using {alternative} instead of {current_tech} for better {benefit}?",
            "The security considerations are well thought out. How does this architecture handle {security_aspect}?"
        ]
        
        import random
        template = random.choice(input_templates)
        
        # Fill in template variables
        component = random.choice(["authentication", "data processing", "API gateway", "caching layer"])
        concern = random.choice(["high load", "data consistency", "failover scenarios"])
        technology = random.choice(["microservices", "containers", "message queues"])
        alternative = random.choice(["GraphQL", "event sourcing", "CQRS", "serverless"])
        current_tech = random.choice(["REST APIs", "SQL database", "monolithic design"])
        benefit = random.choice(["performance", "maintainability", "cost efficiency"])
        security_aspect = random.choice(["data encryption", "access control", "audit logging"])
        
        return template.format(
            component=component, concern=concern, technology=technology,
            alternative=alternative, current_tech=current_tech, benefit=benefit,
            security_aspect=security_aspect
        )
    
    def _evaluate_architecture_completeness(self, proposal: str) -> float:
        """Evaluate completeness of architecture proposal."""
        completeness_indicators = [
            "architecture" in proposal.lower() or "system" in proposal.lower(),
            "component" in proposal.lower() or "service" in proposal.lower(),
            "data" in proposal.lower() or "flow" in proposal.lower(),
            "technology" in proposal.lower() or "stack" in proposal.lower(),
            "scalability" in proposal.lower() or "performance" in proposal.lower(),
            "security" in proposal.lower() or "reliability" in proposal.lower(),
            len(re.findall(r"\d+\.", proposal)) >= 4,  # Structured points
            len(proposal.split()) > 300  # Comprehensive response
        ]
        
        return sum(completeness_indicators) / len(completeness_indicators)
    
    def _evaluate_technical_depth(self, proposal: str) -> float:
        """Evaluate technical depth of the proposal."""
        technical_indicators = [
            "database" in proposal.lower() or "storage" in proposal.lower(),
            "api" in proposal.lower() or "interface" in proposal.lower(),
            "microservice" in proposal.lower() or "service" in proposal.lower(),
            "load balancer" in proposal.lower() or "proxy" in proposal.lower(),
            "cache" in proposal.lower() or "redis" in proposal.lower(),
            "queue" in proposal.lower() or "messaging" in proposal.lower(),
            "container" in proposal.lower() or "kubernetes" in proposal.lower(),
            "monitoring" in proposal.lower() or "logging" in proposal.lower()
        ]
        
        return sum(technical_indicators) / len(technical_indicators)
    
    def _evaluate_scalability_consideration(self, proposal: str) -> float:
        """Evaluate scalability considerations."""
        scalability_indicators = [
            "scalability" in proposal.lower() or "scale" in proposal.lower(),
            "horizontal" in proposal.lower() or "vertical" in proposal.lower(),
            "load" in proposal.lower() or "traffic" in proposal.lower(),
            "performance" in proposal.lower() or "throughput" in proposal.lower(),
            "bottleneck" in proposal.lower() or "capacity" in proposal.lower(),
            "auto-scaling" in proposal.lower() or "elastic" in proposal.lower()
        ]
        
        return sum(scalability_indicators) / len(scalability_indicators)
    
    def _evaluate_clarity(self, proposal: str) -> float:
        """Evaluate clarity of the proposal."""
        clarity_indicators = [
            len(re.findall(r"\d+\.", proposal)) >= 3,  # Structured
            len(proposal.split('\n')) > 5,  # Well-formatted
            "overview" in proposal.lower() or "summary" in proposal.lower(),
            not any(word in proposal.lower() for word in ["maybe", "perhaps", "might"]),  # Decisive
            len(proposal.split()) > 200  # Adequate detail
        ]
        
        return sum(clarity_indicators) / len(clarity_indicators)
    
    def _evaluate_component_definition(self, proposal: str) -> float:
        """Evaluate component definition quality."""
        component_indicators = [
            "component" in proposal.lower() or "module" in proposal.lower(),
            "responsibility" in proposal.lower() or "role" in proposal.lower(),
            "interface" in proposal.lower() or "boundary" in proposal.lower(),
            "interaction" in proposal.lower() or "communication" in proposal.lower(),
            "separation" in proposal.lower() or "decoupling" in proposal.lower()
        ]
        
        return sum(component_indicators) / len(component_indicators)
    
    def _evaluate_technology_justification(self, proposal: str) -> float:
        """Evaluate technology choice justification."""
        justification_indicators = [
            "because" in proposal.lower() or "since" in proposal.lower(),
            "reason" in proposal.lower() or "rationale" in proposal.lower(),
            "benefit" in proposal.lower() or "advantage" in proposal.lower(),
            "suitable" in proposal.lower() or "appropriate" in proposal.lower(),
            "proven" in proposal.lower() or "reliable" in proposal.lower()
        ]
        
        return sum(justification_indicators) / len(justification_indicators)
    
    def _evaluate_stakeholder_engagement(self, response: str) -> float:
        """Evaluate stakeholder engagement quality."""
        engagement_indicators = [
            "thank" in response.lower() or "appreciate" in response.lower(),
            "understand" in response.lower() or "acknowledge" in response.lower(),
            "concern" in response.lower() or "point" in response.lower(),
            "question" in response.lower() or "clarification" in response.lower(),
            "we" in response.lower() or "our" in response.lower(),
            not any(word in response.lower() for word in ["wrong", "incorrect"])
        ]
        
        return sum(engagement_indicators) / len(engagement_indicators)
    
    def _evaluate_technical_justification(self, response: str) -> float:
        """Evaluate technical justification quality."""
        justification_indicators = [
            "because" in response.lower() or "reason" in response.lower(),
            "technical" in response.lower() or "architecture" in response.lower(),
            "performance" in response.lower() or "scalability" in response.lower(),
            "design" in response.lower() or "pattern" in response.lower(),
            "experience" in response.lower() or "proven" in response.lower()
        ]
        
        return sum(justification_indicators) / len(justification_indicators)
    
    def _evaluate_flexibility_demonstration(self, response: str) -> float:
        """Evaluate demonstration of flexibility."""
        flexibility_indicators = [
            "alternative" in response.lower() or "option" in response.lower(),
            "consider" in response.lower() or "explore" in response.lower(),
            "modify" in response.lower() or "adjust" in response.lower(),
            "flexible" in response.lower() or "adaptable" in response.lower(),
            "different" in response.lower() or "various" in response.lower()
        ]
        
        return sum(flexibility_indicators) / len(flexibility_indicators)
    
    def _evaluate_communication_effectiveness(self, response: str) -> float:
        """Evaluate communication effectiveness."""
        communication_indicators = [
            len(response.split()) > 100,  # Adequate length
            "explain" in response.lower() or "clarify" in response.lower(),
            "understand" in response.lower() or "clear" in response.lower(),
            not any(word in response.lower() for word in ["obviously", "clearly"]),  # Not condescending
            "let me" in response.lower() or "allow me" in response.lower()
        ]
        
        return sum(communication_indicators) / len(communication_indicators)
    
    def _evaluate_problem_solving_approach(self, response: str) -> float:
        """Evaluate problem-solving approach."""
        problem_solving_indicators = [
            "solve" in response.lower() or "address" in response.lower(),
            "approach" in response.lower() or "strategy" in response.lower(),
            "analyze" in response.lower() or "evaluate" in response.lower(),
            "solution" in response.lower() or "resolve" in response.lower(),
            "systematic" in response.lower() or "methodical" in response.lower()
        ]
        
        return sum(problem_solving_indicators) / len(problem_solving_indicators)
    
    def _evaluate_trade_off_depth(self, analysis: str) -> float:
        """Evaluate depth of trade-off analysis."""
        depth_indicators = [
            "trade-off" in analysis.lower() or "tradeoff" in analysis.lower(),
            "vs" in analysis.lower() or "versus" in analysis.lower(),
            "balance" in analysis.lower() or "compromise" in analysis.lower(),
            "pros and cons" in analysis.lower() or "advantages" in analysis.lower(),
            "cost" in analysis.lower() or "benefit" in analysis.lower(),
            len(analysis.split()) > 200  # Comprehensive analysis
        ]
        
        return sum(depth_indicators) / len(depth_indicators)
    
    def _evaluate_decision_rationale(self, analysis: str) -> float:
        """Evaluate decision rationale quality."""
        rationale_indicators = [
            "recommend" in analysis.lower() or "suggest" in analysis.lower(),
            "because" in analysis.lower() or "since" in analysis.lower(),
            "rationale" in analysis.lower() or "reasoning" in analysis.lower(),
            "best" in analysis.lower() or "optimal" in analysis.lower(),
            "given" in analysis.lower() or "considering" in analysis.lower()
        ]
        
        return sum(rationale_indicators) / len(rationale_indicators)
    
    def _evaluate_constraint_consideration(self, analysis: str) -> float:
        """Evaluate constraint consideration."""
        constraint_indicators = [
            "constraint" in analysis.lower() or "limitation" in analysis.lower(),
            "requirement" in analysis.lower() or "requirement" in analysis.lower(),
            "budget" in analysis.lower() or "cost" in analysis.lower(),
            "timeline" in analysis.lower() or "time" in analysis.lower(),
            "resource" in analysis.lower() or "capacity" in analysis.lower()
        ]
        
        return sum(constraint_indicators) / len(constraint_indicators)
    
    def _evaluate_analytical_thinking(self, analysis: str) -> float:
        """Evaluate analytical thinking quality."""
        analytical_indicators = [
            "analyze" in analysis.lower() or "analysis" in analysis.lower(),
            "evaluate" in analysis.lower() or "assess" in analysis.lower(),
            "compare" in analysis.lower() or "contrast" in analysis.lower(),
            "implication" in analysis.lower() or "consequence" in analysis.lower(),
            "factor" in analysis.lower() or "aspect" in analysis.lower()
        ]
        
        return sum(analytical_indicators) / len(analytical_indicators)
    
    def _evaluate_comprehensive_coverage(self, analysis: str) -> float:
        """Evaluate comprehensive coverage of trade-offs."""
        coverage_indicators = [
            "performance" in analysis.lower(),
            "cost" in analysis.lower() or "budget" in analysis.lower(),
            "security" in analysis.lower(),
            "maintainability" in analysis.lower() or "maintenance" in analysis.lower(),
            "scalability" in analysis.lower(),
            len(re.findall(r"\d+\.", analysis)) >= 4  # Multiple structured points
        ]
        
        return sum(coverage_indicators) / len(coverage_indicators)
    
    def _evaluate_decision_clarity(self, decision: str) -> float:
        """Evaluate decision clarity."""
        clarity_indicators = [
            "final" in decision.lower() or "recommend" in decision.lower(),
            "decision" in decision.lower() or "choose" in decision.lower(),
            "architecture" in decision.lower() or "design" in decision.lower(),
            len(re.findall(r"\d+\.", decision)) >= 4,  # Structured
            "clear" in decision.lower() or "definitive" in decision.lower()
        ]
        
        return sum(clarity_indicators) / len(clarity_indicators)
    
    def _evaluate_documentation_quality(self, decision: str) -> float:
        """Evaluate documentation quality."""
        documentation_indicators = [
            "document" in decision.lower() or "documentation" in decision.lower(),
            "rationale" in decision.lower() or "reasoning" in decision.lower(),
            "decision" in decision.lower() or "choice" in decision.lower(),
            len(decision.split()) > 250,  # Comprehensive
            "team" in decision.lower() or "developer" in decision.lower()
        ]
        
        return sum(documentation_indicators) / len(documentation_indicators)
    
    def _evaluate_implementation_guidance(self, decision: str) -> float:
        """Evaluate implementation guidance quality."""
        guidance_indicators = [
            "implementation" in decision.lower() or "implement" in decision.lower(),
            "roadmap" in decision.lower() or "plan" in decision.lower(),
            "phase" in decision.lower() or "step" in decision.lower(),
            "timeline" in decision.lower() or "schedule" in decision.lower(),
            "next" in decision.lower() or "first" in decision.lower()
        ]
        
        return sum(guidance_indicators) / len(guidance_indicators)
    
    def _evaluate_risk_management(self, decision: str) -> float:
        """Evaluate risk management considerations."""
        risk_indicators = [
            "risk" in decision.lower() or "threat" in decision.lower(),
            "mitigation" in decision.lower() or "contingency" in decision.lower(),
            "monitor" in decision.lower() or "track" in decision.lower(),
            "failure" in decision.lower() or "issue" in decision.lower(),
            "backup" in decision.lower() or "fallback" in decision.lower()
        ]
        
        return sum(risk_indicators) / len(risk_indicators)
    
    def _evaluate_future_considerations(self, decision: str) -> float:
        """Evaluate future considerations."""
        future_indicators = [
            "future" in decision.lower() or "evolution" in decision.lower(),
            "extensibility" in decision.lower() or "extend" in decision.lower(),
            "growth" in decision.lower() or "expand" in decision.lower(),
            "upgrade" in decision.lower() or "migrate" in decision.lower(),
            "long-term" in decision.lower() or "roadmap" in decision.lower()
        ]
        
        return sum(future_indicators) / len(future_indicators)
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "architecture_completeness": 0.0,
            "technical_depth": 0.0,
            "scalability_consideration": 0.0,
            "clarity": 0.0,
            "component_definition": 0.0,
            "technology_justification": 0.0,
            "stakeholder_engagement": 0.0,
            "technical_justification": 0.0,
            "flexibility_demonstration": 0.0,
            "communication_effectiveness": 0.0,
            "problem_solving_approach": 0.0,
            "trade_off_depth": 0.0,
            "decision_rationale": 0.0,
            "constraint_consideration": 0.0,
            "analytical_thinking": 0.0,
            "comprehensive_coverage": 0.0,
            "decision_clarity": 0.0,
            "documentation_quality": 0.0,
            "implementation_guidance": 0.0,
            "risk_management": 0.0,
            "future_considerations": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {metric: "mean" for metric in self._empty_results().keys()}
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {metric: True for metric in self._empty_results().keys()}