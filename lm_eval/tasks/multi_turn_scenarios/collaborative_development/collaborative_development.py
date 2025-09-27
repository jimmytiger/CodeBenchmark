"""Collaborative Development multi-turn task implementation."""

import logging
from typing import Dict, List, Any, Optional
import re
import json

from evaluation_engine.core.extended_tasks import MultiTurnTask, ScenarioConfig, ScenarioType, TurnConfig
from lm_eval.api.registry import register_task
from .. import utils, metrics

eval_logger = logging.getLogger(__name__)


@register_task("multi_turn_scenarios_collaborative_development")
class CollaborativeDevelopmentTask(MultiTurnTask):
    """
    Multi-turn collaborative development evaluation task.
    
    This task evaluates a model's ability to participate in collaborative development
    including task assignment, development coordination, integration, and delivery.
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    DATASET_NAME = "multi_turn_scenarios_collaborative_development"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize collaborative development task."""
        scenario_config = ScenarioConfig(
            scenario_id="collaborative_development",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=5,
            conversation_timeout=900,
            enable_context_retention=True,
            turns=[
                TurnConfig(
                    turn_id="task_assignment",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""You are leading a collaborative development project with the following details:

**Project**: {project}
**Team Size**: {team_size} developers
**Timeline**: {timeline}
**Technologies**: {technologies_text}

As the technical lead, please:
1. Break down the project into manageable tasks
2. Assign tasks to team members based on skills and dependencies
3. Define clear deliverables and acceptance criteria
4. Establish communication protocols and checkpoints
5. Identify potential risks and mitigation strategies

Present a comprehensive project plan that enables effective collaboration.""",
                    expected_format="project_plan",
                    evaluation_metrics=["task_breakdown_quality", "assignment_logic", "collaboration_planning", "risk_awareness"],
                    temperature=0.2,
                    max_tokens=2500
                ),
                TurnConfig(
                    turn_id="development_coordination",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""The development phase has begun. Here's the current status:

**Your Project Plan**: {project_plan_summary}
**Current Status**: {development_status}
**Team Updates**: {team_updates}

As the coordinator, please:
1. Review the current progress against the plan
2. Address any blockers or dependencies mentioned
3. Coordinate between team members who need to collaborate
4. Adjust timelines or assignments if necessary
5. Provide guidance on technical decisions or conflicts

Maintain team morale while ensuring project success.""",
                    expected_format="coordination_response",
                    depends_on=["task_assignment"],
                    evaluation_metrics=["coordination_effectiveness", "problem_solving", "team_communication", "adaptability"],
                    temperature=0.3,
                    max_tokens=2000
                ),
                TurnConfig(
                    turn_id="integration_management",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""The team is ready to integrate their work. Current situation:

**Completed Components**: {completed_components}
**Integration Challenges**: {integration_challenges}
**Timeline Status**: {timeline_status}

Please manage the integration process by:
1. Defining the integration strategy and sequence
2. Addressing technical integration challenges
3. Coordinating testing and quality assurance
4. Managing conflicts or compatibility issues
5. Ensuring code quality and standards compliance

Focus on smooth integration while maintaining quality.""",
                    expected_format="integration_plan",
                    depends_on=["development_coordination"],
                    evaluation_metrics=["integration_strategy", "quality_assurance", "conflict_resolution", "technical_leadership"],
                    temperature=0.2,
                    max_tokens=2200
                ),
                TurnConfig(
                    turn_id="review_and_feedback",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""The integration is complete. Time for review and feedback:

**Integrated System**: {integrated_system_status}
**Test Results**: {test_results}
**Team Feedback**: {team_feedback}

Please conduct a comprehensive review:
1. Evaluate the overall quality of the integrated solution
2. Provide constructive feedback on the development process
3. Identify lessons learned and best practices
4. Suggest improvements for future collaborations
5. Recognize team contributions and achievements

Balance constructive criticism with positive reinforcement.""",
                    expected_format="review_feedback",
                    depends_on=["integration_management"],
                    evaluation_metrics=["review_thoroughness", "feedback_quality", "team_recognition", "process_improvement"],
                    temperature=0.2,
                    max_tokens=2000
                ),
                TurnConfig(
                    turn_id="delivery_and_retrospective",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Final delivery and project retrospective:

**Final Deliverable**: {final_deliverable}
**Project Outcomes**: {project_outcomes}
**Team Performance**: {team_performance}

Please provide:
1. Final delivery assessment and sign-off
2. Project retrospective with key insights
3. Team performance evaluation and growth areas
4. Recommendations for future collaborative projects
5. Documentation of best practices and lessons learned

Conclude the project on a positive note while capturing valuable insights.""",
                    expected_format="delivery_retrospective",
                    depends_on=["review_and_feedback"],
                    evaluation_metrics=["delivery_assessment", "retrospective_quality", "team_development", "knowledge_capture"],
                    temperature=0.2,
                    max_tokens=2200
                )
            ],
            scenario_metrics=[
                "collaborative_leadership_effectiveness",
                "team_coordination_quality",
                "project_delivery_success",
                "overall_collaboration_score"
            ],
            success_criteria={
                "collaborative_leadership_effectiveness": 0.7,
                "team_coordination_quality": 0.8,
                "project_delivery_success": 0.7
            }
        )
        
        super().__init__(
            data_dir=data_dir,
            cache_dir=cache_dir,
            download_mode=download_mode,
            config=config,
            scenario_config=scenario_config
        )
        
        self.project_plans = []
        self.coordination_history = []
        self.integration_strategies = []
        
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
            dataset_dict = utils.load_dataset(metadata={"scenario": "collaborative_development"})
            if not dataset_dict.get("test"):
                # Create sample scenarios if none exist
                sample_scenarios = utils.create_sample_scenarios("collaborative_development", 5)
                dataset_dict = {"test": sample_scenarios}
            
            dataset = dataset_dict["test"]
            processed_dataset = utils.process_docs(dataset)
            
            eval_logger.info(f"Loaded {len(processed_dataset)} collaborative development scenarios")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load collaborative development dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """Process model results for multi-turn collaborative development."""
        if not results:
            return self._empty_results()
            
        turn_id = self._determine_current_turn(doc)
        prediction = results[0] if results else ""
        
        if turn_id == "task_assignment":
            return self._process_task_assignment(doc, prediction)
        elif turn_id == "development_coordination":
            return self._process_development_coordination(doc, prediction)
        elif turn_id == "integration_management":
            return self._process_integration_management(doc, prediction)
        elif turn_id == "review_and_feedback":
            return self._process_review_and_feedback(doc, prediction)
        elif turn_id == "delivery_and_retrospective":
            return self._process_delivery_and_retrospective(doc, prediction)
        else:
            return self._empty_results()
    
    def _determine_current_turn(self, doc: Dict[str, Any]) -> str:
        """Determine current turn based on conversation state."""
        turn_count = len(getattr(self, '_conversation_history', []))
        turns = ["task_assignment", "development_coordination", "integration_management", 
                "review_and_feedback", "delivery_and_retrospective"]
        return turns[min(turn_count, len(turns) - 1)]
    
    def _process_task_assignment(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process task assignment response."""
        self.project_plans.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "task_breakdown_quality": self._evaluate_task_breakdown_quality(prediction),
            "assignment_logic": self._evaluate_assignment_logic(prediction, doc),
            "collaboration_planning": self._evaluate_collaboration_planning(prediction),
            "risk_awareness": self._evaluate_risk_awareness(prediction),
            "communication_protocols": self._evaluate_communication_protocols(prediction),
            "deliverable_clarity": self._evaluate_deliverable_clarity(prediction)
        }
        
        return metrics_result
    
    def _process_development_coordination(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process development coordination response."""
        status_update = self._generate_development_status(doc)
        self.coordination_history.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "coordination_effectiveness": self._evaluate_coordination_effectiveness(prediction),
            "problem_solving": self._evaluate_problem_solving(prediction),
            "team_communication": self._evaluate_team_communication(prediction),
            "adaptability": self._evaluate_adaptability(prediction),
            "leadership_presence": self._evaluate_leadership_presence(prediction)
        }
        
        return metrics_result
    
    def _process_integration_management(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process integration management response."""
        self.integration_strategies.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "integration_strategy": self._evaluate_integration_strategy(prediction),
            "quality_assurance": self._evaluate_quality_assurance(prediction),
            "conflict_resolution": self._evaluate_conflict_resolution(prediction),
            "technical_leadership": self._evaluate_technical_leadership(prediction),
            "process_management": self._evaluate_process_management(prediction)
        }
        
        return metrics_result
    
    def _process_review_and_feedback(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process review and feedback response."""
        metrics_result = {
            "response": prediction,
            "review_thoroughness": self._evaluate_review_thoroughness(prediction),
            "feedback_quality": self._evaluate_feedback_quality(prediction),
            "team_recognition": self._evaluate_team_recognition(prediction),
            "process_improvement": self._evaluate_process_improvement(prediction),
            "constructive_balance": self._evaluate_constructive_balance(prediction)
        }
        
        return metrics_result
    
    def _process_delivery_and_retrospective(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process delivery and retrospective response."""
        metrics_result = {
            "response": prediction,
            "delivery_assessment": self._evaluate_delivery_assessment(prediction),
            "retrospective_quality": self._evaluate_retrospective_quality(prediction),
            "team_development": self._evaluate_team_development(prediction),
            "knowledge_capture": self._evaluate_knowledge_capture(prediction),
            "future_recommendations": self._evaluate_future_recommendations(prediction)
        }
        
        return metrics_result
    
    def _generate_development_status(self, doc: Dict[str, Any]) -> str:
        """Generate realistic development status update."""
        status_templates = [
            "Frontend team completed the UI components but needs backend API integration. Backend team is 80% done with authentication service.",
            "Database schema is finalized. API development is on track but we're facing some performance issues with complex queries.",
            "Testing framework is set up. Two team members are blocked waiting for the shared utility library to be completed.",
            "Mobile app development is ahead of schedule. Web frontend needs another day for responsive design implementation.",
            "Integration testing revealed some compatibility issues between the payment module and user management system."
        ]
        
        import random
        return random.choice(status_templates)
    
    def _evaluate_task_breakdown_quality(self, plan: str) -> float:
        """Evaluate quality of task breakdown."""
        breakdown_indicators = [
            "task" in plan.lower() or "component" in plan.lower(),
            "break" in plan.lower() or "divide" in plan.lower(),
            "manageable" in plan.lower() or "small" in plan.lower(),
            len(re.findall(r"\d+\.", plan)) >= 4,  # Multiple tasks
            "dependency" in plan.lower() or "depend" in plan.lower(),
            "deliverable" in plan.lower() or "outcome" in plan.lower()
        ]
        
        return sum(breakdown_indicators) / len(breakdown_indicators)
    
    def _evaluate_assignment_logic(self, plan: str, doc: Dict[str, Any]) -> float:
        """Evaluate logic of task assignments."""
        team_size = doc.get("team_size", 3)
        assignment_indicators = [
            "assign" in plan.lower() or "allocate" in plan.lower(),
            "team member" in plan.lower() or "developer" in plan.lower(),
            "skill" in plan.lower() or "expertise" in plan.lower(),
            "experience" in plan.lower() or "strength" in plan.lower(),
            "balance" in plan.lower() or "distribute" in plan.lower(),
            len(re.findall(r"developer|member|person", plan, re.IGNORECASE)) >= team_size // 2
        ]
        
        return sum(assignment_indicators) / len(assignment_indicators)
    
    def _evaluate_collaboration_planning(self, plan: str) -> float:
        """Evaluate collaboration planning quality."""
        collaboration_indicators = [
            "collaborate" in plan.lower() or "cooperation" in plan.lower(),
            "communication" in plan.lower() or "coordinate" in plan.lower(),
            "meeting" in plan.lower() or "standup" in plan.lower(),
            "checkpoint" in plan.lower() or "review" in plan.lower(),
            "protocol" in plan.lower() or "process" in plan.lower(),
            "integration" in plan.lower() or "merge" in plan.lower()
        ]
        
        return sum(collaboration_indicators) / len(collaboration_indicators)
    
    def _evaluate_risk_awareness(self, plan: str) -> float:
        """Evaluate risk awareness in planning."""
        risk_indicators = [
            "risk" in plan.lower() or "threat" in plan.lower(),
            "challenge" in plan.lower() or "obstacle" in plan.lower(),
            "mitigation" in plan.lower() or "contingency" in plan.lower(),
            "blocker" in plan.lower() or "dependency" in plan.lower(),
            "timeline" in plan.lower() or "delay" in plan.lower()
        ]
        
        return sum(risk_indicators) / len(risk_indicators)
    
    def _evaluate_communication_protocols(self, plan: str) -> float:
        """Evaluate communication protocol definition."""
        protocol_indicators = [
            "communication" in plan.lower() or "communicate" in plan.lower(),
            "protocol" in plan.lower() or "process" in plan.lower(),
            "meeting" in plan.lower() or "standup" in plan.lower(),
            "update" in plan.lower() or "status" in plan.lower(),
            "channel" in plan.lower() or "tool" in plan.lower()
        ]
        
        return sum(protocol_indicators) / len(protocol_indicators)
    
    def _evaluate_deliverable_clarity(self, plan: str) -> float:
        """Evaluate clarity of deliverables."""
        clarity_indicators = [
            "deliverable" in plan.lower() or "outcome" in plan.lower(),
            "criteria" in plan.lower() or "requirement" in plan.lower(),
            "acceptance" in plan.lower() or "definition" in plan.lower(),
            "complete" in plan.lower() or "done" in plan.lower(),
            "quality" in plan.lower() or "standard" in plan.lower()
        ]
        
        return sum(clarity_indicators) / len(clarity_indicators)
    
    def _evaluate_coordination_effectiveness(self, response: str) -> float:
        """Evaluate coordination effectiveness."""
        coordination_indicators = [
            "coordinate" in response.lower() or "sync" in response.lower(),
            "progress" in response.lower() or "status" in response.lower(),
            "blocker" in response.lower() or "issue" in response.lower(),
            "adjust" in response.lower() or "modify" in response.lower(),
            "team" in response.lower() or "member" in response.lower(),
            len(response.split()) > 100  # Comprehensive response
        ]
        
        return sum(coordination_indicators) / len(coordination_indicators)
    
    def _evaluate_problem_solving(self, response: str) -> float:
        """Evaluate problem-solving approach."""
        problem_solving_indicators = [
            "solve" in response.lower() or "resolve" in response.lower(),
            "address" in response.lower() or "handle" in response.lower(),
            "solution" in response.lower() or "approach" in response.lower(),
            "alternative" in response.lower() or "option" in response.lower(),
            "strategy" in response.lower() or "plan" in response.lower()
        ]
        
        return sum(problem_solving_indicators) / len(problem_solving_indicators)
    
    def _evaluate_team_communication(self, response: str) -> float:
        """Evaluate team communication quality."""
        communication_indicators = [
            "communicate" in response.lower() or "discuss" in response.lower(),
            "team" in response.lower() or "everyone" in response.lower(),
            "update" in response.lower() or "inform" in response.lower(),
            "meeting" in response.lower() or "call" in response.lower(),
            "clear" in response.lower() or "transparent" in response.lower()
        ]
        
        return sum(communication_indicators) / len(communication_indicators)
    
    def _evaluate_adaptability(self, response: str) -> float:
        """Evaluate adaptability in coordination."""
        adaptability_indicators = [
            "adapt" in response.lower() or "adjust" in response.lower(),
            "flexible" in response.lower() or "change" in response.lower(),
            "modify" in response.lower() or "update" in response.lower(),
            "respond" in response.lower() or "react" in response.lower(),
            "pivot" in response.lower() or "shift" in response.lower()
        ]
        
        return sum(adaptability_indicators) / len(adaptability_indicators)
    
    def _evaluate_leadership_presence(self, response: str) -> float:
        """Evaluate leadership presence."""
        leadership_indicators = [
            "lead" in response.lower() or "guide" in response.lower(),
            "decision" in response.lower() or "decide" in response.lower(),
            "direction" in response.lower() or "vision" in response.lower(),
            "support" in response.lower() or "help" in response.lower(),
            "confidence" in response.lower() or "assure" in response.lower()
        ]
        
        return sum(leadership_indicators) / len(leadership_indicators)
    
    def _evaluate_integration_strategy(self, response: str) -> float:
        """Evaluate integration strategy quality."""
        integration_indicators = [
            "integration" in response.lower() or "integrate" in response.lower(),
            "strategy" in response.lower() or "approach" in response.lower(),
            "sequence" in response.lower() or "order" in response.lower(),
            "component" in response.lower() or "module" in response.lower(),
            "testing" in response.lower() or "validation" in response.lower()
        ]
        
        return sum(integration_indicators) / len(integration_indicators)
    
    def _evaluate_quality_assurance(self, response: str) -> float:
        """Evaluate quality assurance considerations."""
        qa_indicators = [
            "quality" in response.lower() or "standard" in response.lower(),
            "test" in response.lower() or "testing" in response.lower(),
            "validation" in response.lower() or "verify" in response.lower(),
            "review" in response.lower() or "check" in response.lower(),
            "compliance" in response.lower() or "requirement" in response.lower()
        ]
        
        return sum(qa_indicators) / len(qa_indicators)
    
    def _evaluate_conflict_resolution(self, response: str) -> float:
        """Evaluate conflict resolution approach."""
        conflict_indicators = [
            "conflict" in response.lower() or "issue" in response.lower(),
            "resolve" in response.lower() or "address" in response.lower(),
            "compatibility" in response.lower() or "integrate" in response.lower(),
            "compromise" in response.lower() or "balance" in response.lower(),
            "solution" in response.lower() or "fix" in response.lower()
        ]
        
        return sum(conflict_indicators) / len(conflict_indicators)
    
    def _evaluate_technical_leadership(self, response: str) -> float:
        """Evaluate technical leadership quality."""
        technical_leadership_indicators = [
            "technical" in response.lower() or "architecture" in response.lower(),
            "decision" in response.lower() or "choose" in response.lower(),
            "standard" in response.lower() or "practice" in response.lower(),
            "guidance" in response.lower() or "direction" in response.lower(),
            "expertise" in response.lower() or "experience" in response.lower()
        ]
        
        return sum(technical_leadership_indicators) / len(technical_leadership_indicators)
    
    def _evaluate_process_management(self, response: str) -> float:
        """Evaluate process management quality."""
        process_indicators = [
            "process" in response.lower() or "procedure" in response.lower(),
            "workflow" in response.lower() or "pipeline" in response.lower(),
            "manage" in response.lower() or "coordinate" in response.lower(),
            "step" in response.lower() or "phase" in response.lower(),
            "systematic" in response.lower() or "organized" in response.lower()
        ]
        
        return sum(process_indicators) / len(process_indicators)
    
    def _evaluate_review_thoroughness(self, response: str) -> float:
        """Evaluate review thoroughness."""
        thoroughness_indicators = [
            "review" in response.lower() or "evaluate" in response.lower(),
            "quality" in response.lower() or "standard" in response.lower(),
            "comprehensive" in response.lower() or "thorough" in response.lower(),
            "assess" in response.lower() or "analyze" in response.lower(),
            len(response.split()) > 150  # Detailed review
        ]
        
        return sum(thoroughness_indicators) / len(thoroughness_indicators)
    
    def _evaluate_feedback_quality(self, response: str) -> float:
        """Evaluate feedback quality."""
        feedback_indicators = [
            "feedback" in response.lower() or "comment" in response.lower(),
            "constructive" in response.lower() or "helpful" in response.lower(),
            "improve" in response.lower() or "better" in response.lower(),
            "specific" in response.lower() or "concrete" in response.lower(),
            "actionable" in response.lower() or "practical" in response.lower()
        ]
        
        return sum(feedback_indicators) / len(feedback_indicators)
    
    def _evaluate_team_recognition(self, response: str) -> float:
        """Evaluate team recognition quality."""
        recognition_indicators = [
            "recognize" in response.lower() or "acknowledge" in response.lower(),
            "appreciate" in response.lower() or "thank" in response.lower(),
            "contribution" in response.lower() or "effort" in response.lower(),
            "achievement" in response.lower() or "success" in response.lower(),
            "team" in response.lower() or "member" in response.lower()
        ]
        
        return sum(recognition_indicators) / len(recognition_indicators)
    
    def _evaluate_process_improvement(self, response: str) -> float:
        """Evaluate process improvement suggestions."""
        improvement_indicators = [
            "improve" in response.lower() or "better" in response.lower(),
            "lesson" in response.lower() or "learn" in response.lower(),
            "future" in response.lower() or "next time" in response.lower(),
            "process" in response.lower() or "workflow" in response.lower(),
            "suggestion" in response.lower() or "recommend" in response.lower()
        ]
        
        return sum(improvement_indicators) / len(improvement_indicators)
    
    def _evaluate_constructive_balance(self, response: str) -> float:
        """Evaluate balance between constructive criticism and positivity."""
        balance_indicators = [
            "positive" in response.lower() or "good" in response.lower(),
            "improve" in response.lower() or "enhance" in response.lower(),
            "strength" in response.lower() or "success" in response.lower(),
            "opportunity" in response.lower() or "potential" in response.lower(),
            not any(word in response.lower() for word in ["terrible", "awful", "bad"])
        ]
        
        return sum(balance_indicators) / len(balance_indicators)
    
    def _evaluate_delivery_assessment(self, response: str) -> float:
        """Evaluate delivery assessment quality."""
        assessment_indicators = [
            "delivery" in response.lower() or "deliverable" in response.lower(),
            "assess" in response.lower() or "evaluate" in response.lower(),
            "complete" in response.lower() or "finished" in response.lower(),
            "quality" in response.lower() or "standard" in response.lower(),
            "sign-off" in response.lower() or "approve" in response.lower()
        ]
        
        return sum(assessment_indicators) / len(assessment_indicators)
    
    def _evaluate_retrospective_quality(self, response: str) -> float:
        """Evaluate retrospective quality."""
        retrospective_indicators = [
            "retrospective" in response.lower() or "review" in response.lower(),
            "insight" in response.lower() or "learning" in response.lower(),
            "what worked" in response.lower() or "success" in response.lower(),
            "challenge" in response.lower() or "difficulty" in response.lower(),
            "future" in response.lower() or "next" in response.lower()
        ]
        
        return sum(retrospective_indicators) / len(retrospective_indicators)
    
    def _evaluate_team_development(self, response: str) -> float:
        """Evaluate team development considerations."""
        development_indicators = [
            "team" in response.lower() or "member" in response.lower(),
            "growth" in response.lower() or "develop" in response.lower(),
            "skill" in response.lower() or "learning" in response.lower(),
            "performance" in response.lower() or "improvement" in response.lower(),
            "potential" in response.lower() or "strength" in response.lower()
        ]
        
        return sum(development_indicators) / len(development_indicators)
    
    def _evaluate_knowledge_capture(self, response: str) -> float:
        """Evaluate knowledge capture quality."""
        knowledge_indicators = [
            "knowledge" in response.lower() or "learning" in response.lower(),
            "document" in response.lower() or "capture" in response.lower(),
            "best practice" in response.lower() or "lesson" in response.lower(),
            "experience" in response.lower() or "insight" in response.lower(),
            "future" in response.lower() or "reference" in response.lower()
        ]
        
        return sum(knowledge_indicators) / len(knowledge_indicators)
    
    def _evaluate_future_recommendations(self, response: str) -> float:
        """Evaluate future recommendations quality."""
        recommendation_indicators = [
            "recommend" in response.lower() or "suggest" in response.lower(),
            "future" in response.lower() or "next" in response.lower(),
            "improve" in response.lower() or "better" in response.lower(),
            "consider" in response.lower() or "explore" in response.lower(),
            "project" in response.lower() or "collaboration" in response.lower()
        ]
        
        return sum(recommendation_indicators) / len(recommendation_indicators)
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "task_breakdown_quality": 0.0,
            "assignment_logic": 0.0,
            "collaboration_planning": 0.0,
            "risk_awareness": 0.0,
            "communication_protocols": 0.0,
            "deliverable_clarity": 0.0,
            "coordination_effectiveness": 0.0,
            "problem_solving": 0.0,
            "team_communication": 0.0,
            "adaptability": 0.0,
            "leadership_presence": 0.0,
            "integration_strategy": 0.0,
            "quality_assurance": 0.0,
            "conflict_resolution": 0.0,
            "technical_leadership": 0.0,
            "process_management": 0.0,
            "review_thoroughness": 0.0,
            "feedback_quality": 0.0,
            "team_recognition": 0.0,
            "process_improvement": 0.0,
            "constructive_balance": 0.0,
            "delivery_assessment": 0.0,
            "retrospective_quality": 0.0,
            "team_development": 0.0,
            "knowledge_capture": 0.0,
            "future_recommendations": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {metric: "mean" for metric in self._empty_results().keys()}
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {metric: True for metric in self._empty_results().keys()}