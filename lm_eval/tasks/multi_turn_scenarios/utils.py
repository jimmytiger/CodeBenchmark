"""
Utility functions for multi-turn scenarios.

This module provides common utility functions used across different
multi-turn scenario implementations.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

eval_logger = logging.getLogger(__name__)


def load_dataset(metadata: Optional[Dict[str, Any]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load dataset for multi-turn scenarios.
    
    Args:
        metadata: Optional metadata containing scenario information
        
    Returns:
        Dictionary with 'test' key containing list of scenario documents
    """
    # For now, return sample data - in production this would load from actual files
    scenario_name = metadata.get("scenario", "generic") if metadata else "generic"
    
    sample_scenarios = {
        "code_review_process": [
            {
                "id": "code_review_001",
                "scenario": "code_review_process",
                "language": "python",
                "code": """def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)""",
                "context": "This function calculates the average of a list of numbers.",
                "expected_issues": ["No input validation", "Division by zero risk"],
                "difficulty": "intermediate"
            }
        ],
        "debugging_session": [
            {
                "id": "debug_001",
                "scenario": "debugging_session",
                "problem_description": "Function returns incorrect results for edge cases",
                "buggy_code": """def find_max(arr):
    max_val = 0
    for val in arr:
        if val > max_val:
            max_val = val
    return max_val""",
                "language": "python",
                "error_symptoms": "Returns 0 for arrays with all negative numbers",
                "expected_behavior": "Should return the maximum value even if all numbers are negative",
                "root_cause": "Initialization with 0 instead of first element",
                "expected_fix": "Initialize max_val with arr[0] after checking if array is not empty"
            }
        ],
        "teaching_dialogue": [
            {
                "id": "teaching_001",
                "scenario": "teaching_dialogue",
                "topic": "Binary Search Algorithm",
                "level": "intermediate",
                "objectives": [
                    "Understand the concept of binary search",
                    "Learn time complexity analysis",
                    "Practice implementation"
                ],
                "student_question": "How does binary search work with sorted arrays?"
            }
        ]
    }
    
    scenarios = sample_scenarios.get(scenario_name, [
        {
            "id": "generic_001",
            "scenario": scenario_name,
            "content": "Generic multi-turn scenario for testing"
        }
    ])
    
    return {"test": scenarios}


def process_docs(dataset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process documents for multi-turn evaluation.
    
    Args:
        dataset: List of raw documents
        
    Returns:
        List of processed documents
    """
    processed = []
    
    for doc in dataset:
        # Add any necessary preprocessing
        processed_doc = doc.copy()
        
        # Ensure required fields exist
        if "id" not in processed_doc:
            processed_doc["id"] = f"doc_{len(processed)}"
            
        if "scenario" not in processed_doc:
            processed_doc["scenario"] = "generic"
            
        processed.append(processed_doc)
    
    return processed


def doc_to_text(doc: Dict[str, Any]) -> str:
    """
    Convert document to text prompt for model input.
    
    Args:
        doc: Document dictionary
        
    Returns:
        Formatted text prompt
    """
    # Extract key information from document
    scenario = doc.get("scenario", "")
    content = doc.get("content", "")
    
    if scenario == "code_review_process":
        return f"""Please review the following code:

```{doc.get('language', 'python')}
{doc.get('code', '')}
```

Context: {doc.get('context', '')}

Provide a thorough code review with specific feedback."""

    elif scenario == "debugging_session":
        return f"""Debug the following issue:

Problem: {doc.get('problem_description', '')}

Code:
```{doc.get('language', 'python')}
{doc.get('buggy_code', '')}
```

Error: {doc.get('error_symptoms', '')}
Expected: {doc.get('expected_behavior', '')}

Please analyze and debug this issue."""

    elif scenario == "teaching_dialogue":
        return f"""Teach a {doc.get('level', 'beginner')} student about: {doc.get('topic', '')}

Learning objectives:
{chr(10).join(f'- {obj}' for obj in doc.get('objectives', []))}

Please provide a clear explanation."""

    else:
        # Generic format
        return content or f"Please respond to this {scenario} scenario."


def doc_to_target(doc: Dict[str, Any]) -> str:
    """
    Extract target reference from document.
    
    Args:
        doc: Document dictionary
        
    Returns:
        Target reference string
    """
    # Return expected output or reference if available
    return doc.get("expected_output", doc.get("reference", ""))


def format_conversation_history(history: List[Dict[str, Any]]) -> str:
    """
    Format conversation history for display.
    
    Args:
        history: List of conversation turns
        
    Returns:
        Formatted conversation string
    """
    formatted_turns = []
    
    for turn in history:
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        turn_id = turn.get("turn_id", "")
        
        if turn_id:
            formatted_turns.append(f"{role.title()} ({turn_id}): {content}")
        else:
            formatted_turns.append(f"{role.title()}: {content}")
    
    return "\n\n".join(formatted_turns)


def extract_code_blocks(text: str) -> List[str]:
    """
    Extract code blocks from text.
    
    Args:
        text: Text containing code blocks
        
    Returns:
        List of extracted code blocks
    """
    import re
    
    # Match code blocks with optional language specification
    pattern = r"```(?:\w+)?\n?(.*?)\n?```"
    matches = re.findall(pattern, text, re.DOTALL)
    
    return [match.strip() for match in matches]


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple text similarity between two strings.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    if not text1.strip() or not text2.strip():
        return 0.0
    
    # Simple word-based similarity
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


def validate_response_format(response: str, expected_format: str) -> bool:
    """
    Validate response format.
    
    Args:
        response: Response text to validate
        expected_format: Expected format specification
        
    Returns:
        True if response matches expected format
    """
    if not response.strip():
        return False
    
    if expected_format == "structured_feedback":
        # Check for structured elements
        return any(indicator in response.lower() for indicator in [
            "1.", "2.", "3.", "first", "second", "issues", "recommendations"
        ])
    
    elif expected_format == "code_with_explanation":
        # Check for code blocks and explanation
        return "```" in response and len(response.split()) > 20
    
    elif expected_format == "evaluation_summary":
        # Check for evaluation elements
        return any(indicator in response.lower() for indicator in [
            "evaluation", "assessment", "rating", "score", "improvement"
        ])
    
    elif expected_format == "structured_analysis":
        # Check for analysis structure
        return any(indicator in response.lower() for indicator in [
            "analysis", "understanding", "causes", "strategy"
        ])
    
    elif expected_format == "ranked_hypotheses":
        # Check for hypothesis ranking
        return any(indicator in response.lower() for indicator in [
            "hypothesis", "likely", "rank", "1.", "2."
        ])
    
    else:
        # Default validation - just check for non-empty response
        return len(response.strip()) > 10


def extract_metrics_from_response(response: str, metric_keywords: List[str]) -> Dict[str, float]:
    """
    Extract metric values from response text.
    
    Args:
        response: Response text
        metric_keywords: Keywords to look for
        
    Returns:
        Dictionary of extracted metrics
    """
    import re
    
    metrics = {}
    response_lower = response.lower()
    
    for keyword in metric_keywords:
        # Look for patterns like "keyword: 0.8" or "keyword score: 85%"
        patterns = [
            rf"{keyword}[:\s]+([0-9]*\.?[0-9]+)",
            rf"{keyword}\s+score[:\s]+([0-9]*\.?[0-9]+)",
            rf"{keyword}\s+rating[:\s]+([0-9]*\.?[0-9]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_lower)
            if match:
                try:
                    value = float(match.group(1))
                    # Normalize percentage values
                    if value > 1.0 and value <= 100.0:
                        value = value / 100.0
                    metrics[keyword] = min(max(value, 0.0), 1.0)  # Clamp to 0-1
                    break
                except ValueError:
                    continue
    
    return metrics


def create_sample_scenarios(scenario_type: str, count: int = 5) -> List[Dict[str, Any]]:
    """
    Create sample scenarios for testing.
    
    Args:
        scenario_type: Type of scenario to create
        count: Number of scenarios to create
        
    Returns:
        List of sample scenario documents
    """
    scenarios = []
    
    for i in range(count):
        base_scenario = {
            "id": f"{scenario_type}_{i+1:03d}",
            "scenario": scenario_type,
            "difficulty": ["simple", "intermediate", "complex"][i % 3]
        }
        
        if scenario_type == "design_iteration":
            base_scenario.update({
                "design_brief": f"Design a mobile app for {['fitness tracking', 'meal planning', 'task management'][i % 3]}",
                "constraints": ["Budget: $50k", "Timeline: 3 months", "Team: 4 developers"],
                "stakeholders": ["Product Manager", "UX Designer", "Engineering Lead"],
                "success_criteria": ["User engagement > 70%", "Performance < 2s load time"]
            })
        
        elif scenario_type == "architecture_discussion":
            base_scenario.update({
                "system_requirements": f"Design architecture for {['e-commerce platform', 'social media app', 'data analytics system'][i % 3]}",
                "scale_requirements": f"{[100, 1000, 10000][i % 3]}k users",
                "technical_constraints": ["Cloud-native", "Microservices", "High availability"],
                "stakeholders": ["CTO", "Senior Architect", "DevOps Lead"]
            })
        
        elif scenario_type == "collaborative_development":
            base_scenario.update({
                "project": f"Implement {['user authentication', 'payment processing', 'data visualization'][i % 3]} feature",
                "team_size": [3, 5, 7][i % 3],
                "timeline": f"{[2, 4, 6][i % 3]} weeks",
                "technologies": ["React", "Node.js", "PostgreSQL"]
            })
        
        elif scenario_type == "requirements_refinement":
            base_scenario.update({
                "initial_requirement": f"Build a {['reporting dashboard', 'user management system', 'notification service'][i % 3]}",
                "stakeholders": ["Business Analyst", "Product Owner", "End Users"],
                "domain": ["Healthcare", "Finance", "E-commerce"][i % 3]
            })
        
        elif scenario_type == "performance_tuning":
            base_scenario.update({
                "performance_issue": f"{['Slow database queries', 'High memory usage', 'Long API response times'][i % 3]}",
                "current_metrics": {
                    "response_time": f"{[500, 1000, 2000][i % 3]}ms",
                    "throughput": f"{[100, 50, 25][i % 3]} req/s",
                    "error_rate": f"{[1, 3, 5][i % 3]}%"
                },
                "target_metrics": {
                    "response_time": "< 200ms",
                    "throughput": "> 500 req/s",
                    "error_rate": "< 0.1%"
                }
            })
        
        scenarios.append(base_scenario)
    
    return scenarios