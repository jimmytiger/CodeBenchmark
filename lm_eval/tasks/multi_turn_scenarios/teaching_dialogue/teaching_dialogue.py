"""Teaching Dialogue multi-turn task implementation."""

import logging
from typing import Dict, List, Any, Optional
import re
import random

from evaluation_engine.core.extended_tasks import MultiTurnTask, ScenarioConfig, ScenarioType, TurnConfig
from lm_eval.api.registry import register_task
from .. import utils, metrics

eval_logger = logging.getLogger(__name__)


@register_task("multi_turn_scenarios_teaching_dialogue")
class TeachingDialogueTask(MultiTurnTask):
    """
    Multi-turn teaching dialogue evaluation task.
    
    This task evaluates a model's ability to conduct effective teaching sessions
    including explanation, Q&A, clarification, and knowledge assessment.
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    DATASET_NAME = "multi_turn_scenarios_teaching_dialogue"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize teaching dialogue task."""
        scenario_config = ScenarioConfig(
            scenario_id="teaching_dialogue",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=4,
            conversation_timeout=600,
            enable_context_retention=True,
            turns=[
                TurnConfig(
                    turn_id="initial_explanation",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""You are teaching a {level} level student about: {topic}

Learning objectives:
{objectives}

Please provide a clear, engaging explanation of the fundamental concepts. Use examples and make it appropriate for a {level} level student.

Structure your explanation with:
1. Introduction to the concept
2. Key principles or components
3. Practical examples
4. Why it's important/useful""",
                    expected_format="structured_explanation",
                    evaluation_metrics=["pedagogical_clarity", "example_quality", "engagement_level", "concept_coverage"],
                    temperature=0.4,
                    max_tokens=2000
                ),
                TurnConfig(
                    turn_id="student_question_response",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""The student asks: "{student_question}"

Please respond to this question in a way that:
1. Directly addresses their concern
2. Provides additional clarification if needed
3. Uses examples or analogies to help understanding
4. Checks if they need further explanation

Keep your response appropriate for a {level} level student.""",
                    expected_format="responsive_explanation",
                    depends_on=["initial_explanation"],
                    evaluation_metrics=["question_addressing", "clarification_quality", "responsiveness"],
                    temperature=0.3,
                    max_tokens=1500
                ),
                TurnConfig(
                    turn_id="concept_reinforcement",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Now let's reinforce the learning with a different approach or additional examples.

Topic: {topic}
Previous explanation: {explanation_summary}
Student question addressed: {student_question}

Please provide:
1. A different way to think about the concept
2. Additional examples or use cases
3. Common misconceptions to avoid
4. Tips for remembering or applying the concept""",
                    expected_format="reinforcement_content",
                    depends_on=["student_question_response"],
                    evaluation_metrics=["concept_reinforcement", "alternative_explanations", "misconception_awareness"],
                    temperature=0.4,
                    max_tokens=1800
                ),
                TurnConfig(
                    turn_id="knowledge_assessment",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""Now let's assess the student's understanding. Create a practical exercise or question that tests their grasp of {topic}.

The assessment should:
1. Test understanding of key concepts covered
2. Be appropriate for {level} level
3. Allow for practical application
4. Include guidance on how to approach it

Provide the assessment question/exercise and explain what you're looking for in a good response.""",
                    expected_format="assessment_with_guidance",
                    depends_on=["concept_reinforcement"],
                    evaluation_metrics=["assessment_quality", "difficulty_appropriateness", "guidance_clarity"],
                    temperature=0.2,
                    max_tokens=1500
                )
            ],
            scenario_metrics=[
                "teaching_effectiveness",
                "student_engagement",
                "learning_progression",
                "overall_pedagogical_quality"
            ],
            success_criteria={
                "teaching_effectiveness": 0.7,
                "student_engagement": 0.6,
                "learning_progression": 0.8
            }
        )
        
        super().__init__(
            data_dir=data_dir,
            cache_dir=cache_dir,
            download_mode=download_mode,
            config=config,
            scenario_config=scenario_config
        )
        
        self.learning_objectives = []
        self.student_questions = []
        self.assessment_results = []
        
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
            dataset_dict = utils.load_dataset(metadata={"scenario": "teaching_dialogue"})
            dataset = dataset_dict["test"]
            processed_dataset = utils.process_docs(dataset)
            
            eval_logger.info(f"Loaded {len(processed_dataset)} teaching scenarios")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load teaching dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """Process model results for multi-turn teaching dialogue."""
        if not results:
            return self._empty_results()
            
        turn_id = self._determine_current_turn(doc)
        prediction = results[0] if results else ""
        
        if turn_id == "initial_explanation":
            return self._process_initial_explanation(doc, prediction)
        elif turn_id == "student_question_response":
            return self._process_student_question_response(doc, prediction)
        elif turn_id == "concept_reinforcement":
            return self._process_concept_reinforcement(doc, prediction)
        elif turn_id == "knowledge_assessment":
            return self._process_knowledge_assessment(doc, prediction)
        else:
            return self._empty_results()
    
    def _determine_current_turn(self, doc: Dict[str, Any]) -> str:
        """Determine current turn based on conversation state."""
        turn_count = len(self._conversation_history)
        turns = ["initial_explanation", "student_question_response", "concept_reinforcement", "knowledge_assessment"]
        return turns[min(turn_count, len(turns) - 1)]
    
    def _process_initial_explanation(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process initial explanation response."""
        objectives = doc.get("objectives", [])
        self.learning_objectives = objectives
        
        metrics_result = {
            "response": prediction,
            "pedagogical_clarity": self._evaluate_pedagogical_clarity(prediction),
            "example_quality": self._evaluate_example_quality(prediction),
            "engagement_level": self._evaluate_engagement_level(prediction),
            "concept_coverage": self._evaluate_concept_coverage(prediction, objectives),
            "structure_quality": self._evaluate_structure_quality(prediction),
            "level_appropriateness": self._evaluate_level_appropriateness(prediction, doc.get("level", ""))
        }
        
        return metrics_result
    
    def _process_student_question_response(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process student question response."""
        student_question = self._generate_student_question(doc)
        self.student_questions.append(student_question)
        
        metrics_result = {
            "response": prediction,
            "question_addressing": self._evaluate_question_addressing(prediction, student_question),
            "clarification_quality": self._evaluate_clarification_quality(prediction),
            "responsiveness": self._evaluate_responsiveness(prediction),
            "patience_demonstration": self._evaluate_patience_demonstration(prediction),
            "follow_up_encouragement": self._evaluate_follow_up_encouragement(prediction)
        }
        
        return metrics_result
    
    def _process_concept_reinforcement(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process concept reinforcement response."""
        metrics_result = {
            "response": prediction,
            "concept_reinforcement": self._evaluate_concept_reinforcement(prediction),
            "alternative_explanations": self._evaluate_alternative_explanations(prediction),
            "misconception_awareness": self._evaluate_misconception_awareness(prediction),
            "memory_aids": self._evaluate_memory_aids(prediction),
            "practical_application": self._evaluate_practical_application(prediction)
        }
        
        return metrics_result
    
    def _process_knowledge_assessment(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process knowledge assessment response."""
        assessment_score = self._evaluate_assessment_response(prediction, doc)
        self.assessment_results.append(assessment_score)
        
        metrics_result = {
            "response": prediction,
            "assessment_quality": assessment_score,
            "difficulty_appropriateness": self._evaluate_difficulty_appropriateness(prediction, doc.get("level", "")),
            "guidance_clarity": self._evaluate_guidance_clarity(prediction),
            "practical_relevance": self._evaluate_practical_relevance(prediction),
            "feedback_framework": self._evaluate_feedback_framework(prediction)
        }
        
        return metrics_result
    
    def _generate_student_question(self, doc: Dict[str, Any]) -> str:
        """Generate a realistic student question based on the topic."""
        topic = doc.get("topic", "")
        level = doc.get("level", "beginner")
        
        question_templates = {
            "beginner": [
                "Can you give me another example of {topic}?",
                "I'm confused about one part - could you clarify?",
                "What's the difference between this and...?",
                "Why is {topic} important?",
                "How do I know when to use {topic}?"
            ],
            "intermediate": [
                "What are the most common mistakes people make with {topic}?",
                "How does {topic} relate to real-world applications?",
                "What if we have a different scenario where...?",
                "Can you explain the underlying principles?",
                "What are the limitations of {topic}?"
            ],
            "advanced": [
                "How does {topic} compare to alternative approaches?",
                "What are the theoretical foundations behind {topic}?",
                "In what edge cases might {topic} not work well?",
                "How would you optimize {topic} for performance?",
                "What recent developments have there been in {topic}?"
            ]
        }
        
        templates = question_templates.get(level, question_templates["beginner"])
        template = random.choice(templates)
        return template.format(topic=topic)
    
    def _evaluate_pedagogical_clarity(self, response: str) -> float:
        """Evaluate pedagogical clarity of explanation."""
        clarity_indicators = [
            "for example" in response.lower() or "example" in response.lower(),
            "first" in response.lower() or "step" in response.lower(),
            "simply" in response.lower() or "basically" in response.lower(),
            len(response.split(".")) > 3,  # Multiple sentences
            "because" in response.lower() or "reason" in response.lower(),
            "let's" in response.lower() or "we can" in response.lower(),
            "imagine" in response.lower() or "think of" in response.lower()
        ]
        
        return sum(clarity_indicators) / len(clarity_indicators)
    
    def _evaluate_example_quality(self, response: str) -> float:
        """Evaluate quality of examples provided."""
        example_indicators = [
            "example" in response.lower(),
            "for instance" in response.lower(),
            "imagine" in response.lower() or "suppose" in response.lower(),
            "like" in response.lower() and ":" in response,  # Analogies
            len(re.findall(r"\d+", response)) > 0,  # Numerical examples
            "such as" in response.lower(),
            re.search(r"consider.*case", response, re.IGNORECASE) is not None
        ]
        
        return sum(example_indicators) / len(example_indicators)
    
    def _evaluate_engagement_level(self, response: str) -> float:
        """Evaluate engagement level of teaching response."""
        engagement_indicators = [
            "you" in response.lower(),  # Direct address
            "?" in response,  # Questions to student
            "!" in response,  # Enthusiasm
            "interesting" in response.lower() or "cool" in response.lower(),
            "exciting" in response.lower() or "amazing" in response.lower(),
            len(response) > 150,  # Comprehensive response
            "let's" in response.lower() or "we" in response.lower(),
            "discover" in response.lower() or "explore" in response.lower()
        ]
        
        return sum(engagement_indicators) / len(engagement_indicators)
    
    def _evaluate_concept_coverage(self, response: str, objectives: List[str]) -> float:
        """Evaluate coverage of learning objectives."""
        if not objectives:
            return 0.5  # No objectives to evaluate against
        
        response_lower = response.lower()
        covered_objectives = 0
        
        for objective in objectives:
            objective_words = objective.lower().split()
            if any(word in response_lower for word in objective_words[:3]):  # Check first 3 words
                covered_objectives += 1
        
        return covered_objectives / len(objectives) if objectives else 0.0
    
    def _evaluate_structure_quality(self, response: str) -> float:
        """Evaluate structural quality of explanation."""
        structure_indicators = [
            len(re.findall(r"\d+\.", response)) >= 2,  # Numbered points
            "introduction" in response.lower() or "first" in response.lower(),
            "conclusion" in response.lower() or "summary" in response.lower(),
            len(response.split('\n')) > 3,  # Multiple paragraphs
            "key" in response.lower() or "important" in response.lower(),
            "principle" in response.lower() or "concept" in response.lower()
        ]
        
        return sum(structure_indicators) / len(structure_indicators)
    
    def _evaluate_level_appropriateness(self, response: str, level: str) -> float:
        """Evaluate appropriateness for student level."""
        level_indicators = {
            "beginner": [
                "simple" in response.lower() or "basic" in response.lower(),
                "start" in response.lower() or "begin" in response.lower(),
                "easy" in response.lower() or "straightforward" in response.lower(),
                len(response.split()) < 300,  # Not too verbose
                not any(word in response.lower() for word in ["complex", "advanced", "sophisticated"])
            ],
            "intermediate": [
                "build" in response.lower() or "expand" in response.lower(),
                "now that" in response.lower() or "building on" in response.lower(),
                "more" in response.lower() or "further" in response.lower(),
                len(response.split()) > 150,  # Adequate detail
                "practice" in response.lower() or "apply" in response.lower()
            ],
            "advanced": [
                "complex" in response.lower() or "sophisticated" in response.lower(),
                "theory" in response.lower() or "theoretical" in response.lower(),
                "research" in response.lower() or "studies" in response.lower(),
                len(response.split()) > 200,  # Detailed explanation
                "implications" in response.lower() or "considerations" in response.lower()
            ]
        }
        
        indicators = level_indicators.get(level, level_indicators["beginner"])
        return sum(indicators) / len(indicators)
    
    def _evaluate_question_addressing(self, response: str, student_question: str) -> float:
        """Evaluate how well the response addresses student questions."""
        response_lower = response.lower()
        question_lower = student_question.lower()
        
        # Check if response references the question
        addressing_indicators = [
            "question" in response_lower or "ask" in response_lower,
            "you mentioned" in response_lower or "you're asking" in response_lower,
            len(response) > 50,  # Comprehensive response
            any(word in response_lower for word in question_lower.split()[:3]),  # References question content
            "clarify" in response_lower or "explain" in response_lower
        ]
        
        return sum(addressing_indicators) / len(addressing_indicators)
    
    def _evaluate_clarification_quality(self, response: str) -> float:
        """Evaluate quality of clarification."""
        clarification_indicators = [
            "clarify" in response.lower() or "explain" in response.lower(),
            "other words" in response.lower() or "differently" in response.lower(),
            "simpler" in response.lower() or "easier" in response.lower(),
            "think of it" in response.lower() or "another way" in response.lower(),
            len(response.split()) > 40,  # Detailed clarification
            "analogy" in response.lower() or "like" in response.lower()
        ]
        
        return sum(clarification_indicators) / len(clarification_indicators)
    
    def _evaluate_responsiveness(self, response: str) -> float:
        """Evaluate responsiveness to student needs."""
        responsiveness_indicators = [
            "understand" in response.lower() or "make sense" in response.lower(),
            "help" in response.lower() or "assist" in response.lower(),
            "need" in response.lower() or "want" in response.lower(),
            "more" in response.lower() or "further" in response.lower(),
            "feel free" in response.lower() or "don't hesitate" in response.lower()
        ]
        
        return sum(responsiveness_indicators) / len(responsiveness_indicators)
    
    def _evaluate_patience_demonstration(self, response: str) -> float:
        """Evaluate demonstration of patience."""
        patience_indicators = [
            "no problem" in response.lower() or "no worries" in response.lower(),
            "take your time" in response.lower() or "don't worry" in response.lower(),
            "perfectly normal" in response.lower() or "common question" in response.lower(),
            "happy to" in response.lower() or "glad to" in response.lower(),
            not any(word in response.lower() for word in ["obviously", "clearly", "simple"])
        ]
        
        return sum(patience_indicators) / len(patience_indicators)
    
    def _evaluate_follow_up_encouragement(self, response: str) -> float:
        """Evaluate encouragement for follow-up questions."""
        encouragement_indicators = [
            "questions" in response.lower() or "ask" in response.lower(),
            "feel free" in response.lower() or "don't hesitate" in response.lower(),
            "anything else" in response.lower() or "more" in response.lower(),
            "help" in response.lower() or "clarify" in response.lower(),
            "?" in response  # Asking if they understand
        ]
        
        return sum(encouragement_indicators) / len(encouragement_indicators)
    
    def _evaluate_concept_reinforcement(self, response: str) -> float:
        """Evaluate concept reinforcement quality."""
        reinforcement_indicators = [
            "another way" in response.lower() or "different approach" in response.lower(),
            "reinforce" in response.lower() or "strengthen" in response.lower(),
            "remember" in response.lower() or "recall" in response.lower(),
            "practice" in response.lower() or "apply" in response.lower(),
            "key point" in response.lower() or "important" in response.lower()
        ]
        
        return sum(reinforcement_indicators) / len(reinforcement_indicators)
    
    def _evaluate_alternative_explanations(self, response: str) -> float:
        """Evaluate provision of alternative explanations."""
        alternative_indicators = [
            "another way" in response.lower() or "alternatively" in response.lower(),
            "different" in response.lower() or "other" in response.lower(),
            "also" in response.lower() or "additionally" in response.lower(),
            "perspective" in response.lower() or "viewpoint" in response.lower(),
            "approach" in response.lower() or "method" in response.lower()
        ]
        
        return sum(alternative_indicators) / len(alternative_indicators)
    
    def _evaluate_misconception_awareness(self, response: str) -> float:
        """Evaluate awareness and addressing of misconceptions."""
        misconception_indicators = [
            "misconception" in response.lower() or "mistake" in response.lower(),
            "common error" in response.lower() or "often think" in response.lower(),
            "avoid" in response.lower() or "careful" in response.lower(),
            "not" in response.lower() and "but" in response.lower(),
            "however" in response.lower() or "actually" in response.lower()
        ]
        
        return sum(misconception_indicators) / len(misconception_indicators)
    
    def _evaluate_memory_aids(self, response: str) -> float:
        """Evaluate provision of memory aids."""
        memory_indicators = [
            "remember" in response.lower() or "recall" in response.lower(),
            "tip" in response.lower() or "trick" in response.lower(),
            "mnemonic" in response.lower() or "acronym" in response.lower(),
            "pattern" in response.lower() or "rule" in response.lower(),
            "associate" in response.lower() or "connect" in response.lower()
        ]
        
        return sum(memory_indicators) / len(memory_indicators)
    
    def _evaluate_practical_application(self, response: str) -> float:
        """Evaluate practical application guidance."""
        application_indicators = [
            "apply" in response.lower() or "use" in response.lower(),
            "practice" in response.lower() or "try" in response.lower(),
            "real world" in response.lower() or "practical" in response.lower(),
            "example" in response.lower() or "case" in response.lower(),
            "situation" in response.lower() or "scenario" in response.lower()
        ]
        
        return sum(application_indicators) / len(application_indicators)
    
    def _evaluate_assessment_response(self, response: str, doc: Dict[str, Any]) -> float:
        """Evaluate assessment response quality."""
        assessment_indicators = [
            "question" in response.lower() or "exercise" in response.lower(),
            "test" in response.lower() or "assess" in response.lower(),
            "understanding" in response.lower() or "knowledge" in response.lower(),
            "solve" in response.lower() or "answer" in response.lower(),
            len(response.split()) > 80,  # Detailed assessment
            "looking for" in response.lower() or "expect" in response.lower()
        ]
        
        return sum(assessment_indicators) / len(assessment_indicators)
    
    def _evaluate_difficulty_appropriateness(self, response: str, level: str) -> float:
        """Evaluate appropriateness of assessment difficulty."""
        # This is a simplified evaluation - in practice would need more sophisticated analysis
        difficulty_indicators = {
            "beginner": [
                "basic" in response.lower() or "simple" in response.lower(),
                "start" in response.lower() or "begin" in response.lower(),
                not any(word in response.lower() for word in ["complex", "advanced"]),
                len(response.split()) < 200
            ],
            "intermediate": [
                "apply" in response.lower() or "use" in response.lower(),
                "combine" in response.lower() or "integrate" in response.lower(),
                len(response.split()) > 100,
                "scenario" in response.lower() or "situation" in response.lower()
            ],
            "advanced": [
                "analyze" in response.lower() or "evaluate" in response.lower(),
                "complex" in response.lower() or "sophisticated" in response.lower(),
                "critique" in response.lower() or "compare" in response.lower(),
                len(response.split()) > 150
            ]
        }
        
        indicators = difficulty_indicators.get(level, difficulty_indicators["beginner"])
        return sum(indicators) / len(indicators)
    
    def _evaluate_guidance_clarity(self, response: str) -> float:
        """Evaluate clarity of assessment guidance."""
        guidance_indicators = [
            "guidance" in response.lower() or "guide" in response.lower(),
            "looking for" in response.lower() or "expect" in response.lower(),
            "should" in response.lower() or "need to" in response.lower(),
            "approach" in response.lower() or "method" in response.lower(),
            "step" in response.lower() or "process" in response.lower()
        ]
        
        return sum(guidance_indicators) / len(guidance_indicators)
    
    def _evaluate_practical_relevance(self, response: str) -> float:
        """Evaluate practical relevance of assessment."""
        relevance_indicators = [
            "practical" in response.lower() or "real" in response.lower(),
            "application" in response.lower() or "apply" in response.lower(),
            "use" in response.lower() or "useful" in response.lower(),
            "scenario" in response.lower() or "situation" in response.lower(),
            "example" in response.lower() or "case" in response.lower()
        ]
        
        return sum(relevance_indicators) / len(relevance_indicators)
    
    def _evaluate_feedback_framework(self, response: str) -> float:
        """Evaluate provision of feedback framework."""
        feedback_indicators = [
            "feedback" in response.lower() or "evaluate" in response.lower(),
            "correct" in response.lower() or "good" in response.lower(),
            "improve" in response.lower() or "better" in response.lower(),
            "criteria" in response.lower() or "rubric" in response.lower(),
            "assess" in response.lower() or "judge" in response.lower()
        ]
        
        return sum(feedback_indicators) / len(feedback_indicators)
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "pedagogical_clarity": 0.0,
            "example_quality": 0.0,
            "engagement_level": 0.0,
            "concept_coverage": 0.0,
            "structure_quality": 0.0,
            "level_appropriateness": 0.0,
            "question_addressing": 0.0,
            "clarification_quality": 0.0,
            "responsiveness": 0.0,
            "patience_demonstration": 0.0,
            "follow_up_encouragement": 0.0,
            "concept_reinforcement": 0.0,
            "alternative_explanations": 0.0,
            "misconception_awareness": 0.0,
            "memory_aids": 0.0,
            "practical_application": 0.0,
            "assessment_quality": 0.0,
            "difficulty_appropriateness": 0.0,
            "guidance_clarity": 0.0,
            "practical_relevance": 0.0,
            "feedback_framework": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {metric: "mean" for metric in self._empty_results().keys()}
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {metric: True for metric in self._empty_results().keys()}