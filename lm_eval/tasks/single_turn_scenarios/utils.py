"""Utility functions for single_turn_scenarios evaluation tasks."""

import json
import os
import re
import logging
from typing import Dict, List, Any, Optional
import datasets
from pathlib import Path

eval_logger = logging.getLogger(__name__)

def load_dataset(metadata: Optional[Dict] = None, **kwargs) -> datasets.Dataset:
    """Load the problems.jsonl dataset with validation.
    
    Args:
        metadata: Optional metadata for filtering
        
    Returns:
        datasets.Dataset: Loaded and validated dataset
        
    Raises:
        FileNotFoundError: If problems.jsonl file is not found
        ValueError: If no valid problems are found in the dataset
    """
    current_dir = Path(__file__).parent
    problems_file = current_dir / "problems.jsonl"
    
    if not problems_file.exists():
        raise FileNotFoundError(f"Problems file not found: {problems_file}")
    
    # Load JSONL data with comprehensive validation
    data = []
    validation_errors = []
    
    with open(problems_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                problem = json.loads(line)
                
                # Validate problem schema
                if validate_problem_schema(problem):
                    data.append(problem)
                else:
                    validation_errors.append(f"Line {line_num}: Schema validation failed for problem {problem.get('id', 'unknown')}")
                    
            except json.JSONDecodeError as e:
                validation_errors.append(f"Line {line_num}: Invalid JSON - {e}")
                continue
            except Exception as e:
                validation_errors.append(f"Line {line_num}: Unexpected error - {e}")
                continue
    
    # Log validation errors
    if validation_errors:
        eval_logger.warning(f"Found {len(validation_errors)} validation errors:")
        for error in validation_errors[:10]:  # Log first 10 errors
            eval_logger.warning(f"  {error}")
        if len(validation_errors) > 10:
            eval_logger.warning(f"  ... and {len(validation_errors) - 10} more errors")
    
    if not data:
        raise ValueError("No valid problems found in dataset")
    
    # Convert to HuggingFace dataset
    dataset = datasets.Dataset.from_list(data)
    
    # Apply metadata filtering if provided
    # Check for metadata in kwargs first, then use direct metadata parameter
    filter_metadata = kwargs.get('metadata', metadata)
    if filter_metadata:
        dataset = filter_by_metadata(dataset, filter_metadata)
    
    eval_logger.info(f"Loaded {len(dataset)} problems from {problems_file} ({len(validation_errors)} validation errors)")
    
    # Return dataset in the format expected by lm-eval framework
    return {"test": dataset}

def filter_by_metadata(dataset: datasets.Dataset, filters: Dict[str, Any]) -> datasets.Dataset:
    """Filter dataset by metadata criteria with comprehensive filtering support.
    
    Args:
        dataset: Input dataset to filter
        filters: Dictionary of filter criteria with the following supported keys:
                - scenario: str or list of scenario names
                - difficulty: str or list of difficulty levels
                - language: str or list of programming languages
                - context_mode: str or list of context modes
                - id: str or list of specific problem IDs
                - Any other field present in the dataset
        
    Returns:
        datasets.Dataset: Filtered dataset
        
    Example:
        filters = {
            'scenario': ['algorithm_implementation', 'bug_fix'],
            'difficulty': 'intermediate',
            'language': 'python'
        }
    """
    if not filters:
        eval_logger.info("No filters provided, returning original dataset")
        return dataset
    
    def filter_fn(example):
        for key, value in filters.items():
            if key not in example:
                eval_logger.debug(f"Filter key '{key}' not found in example {example.get('id', 'unknown')}")
                return False
            
            example_value = example[key]
            
            # Handle list of acceptable values
            if isinstance(value, list):
                if example_value not in value:
                    return False
            # Handle single value
            else:
                if example_value != value:
                    return False
        return True
    
    try:
        filtered = dataset.filter(filter_fn)
        eval_logger.info(f"Filtered dataset from {len(dataset)} to {len(filtered)} problems using filters: {filters}")
        return filtered
    except Exception as e:
        eval_logger.error(f"Failed to filter dataset: {e}")
        return dataset

def process_docs(dataset: datasets.Dataset) -> datasets.Dataset:
    """Process documents for evaluation with comprehensive preprocessing.
    
    Args:
        dataset: Raw dataset from load_dataset
        
    Returns:
        datasets.Dataset: Processed dataset with applied context and validation
    """
    def _process_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document."""
        try:
            # Create a copy to avoid modifying original
            processed_doc = doc.copy()
            
            # Validate essential fields
            required_fields = ['id', 'prompt', 'context_mode']
            for field in required_fields:
                if field not in processed_doc:
                    eval_logger.error(f"Missing required field '{field}' in document {processed_doc.get('id', 'unknown')}")
                    # Use default values for missing fields
                    if field == 'context_mode':
                        processed_doc[field] = 'no_context'
                    elif field == 'prompt':
                        processed_doc[field] = ''
            
            # Apply context template based on context_mode
            processed_doc = apply_context_template(processed_doc, processed_doc.get('context_mode', 'no_context'))
            
            # Ensure formatted_prompt exists
            if 'formatted_prompt' not in processed_doc:
                processed_doc['formatted_prompt'] = processed_doc.get('prompt', '')
                
            # Add processing metadata
            processed_doc['_processed'] = True
            
            return processed_doc
            
        except Exception as e:
            eval_logger.error(f"Failed to process document {doc.get('id', 'unknown')}: {e}")
            # Return minimal viable document
            return {
                'id': doc.get('id', 'unknown'),
                'prompt': doc.get('prompt', ''),
                'formatted_prompt': doc.get('prompt', ''),
                'context_mode': doc.get('context_mode', 'no_context'),
                '_processed': False,
                '_error': str(e)
            }
    
    # Process all documents in the dataset
    try:
        processed_dataset = dataset.map(_process_doc)
        eval_logger.info(f"Processed {len(processed_dataset)} documents")
        return processed_dataset
    except Exception as e:
        eval_logger.error(f"Failed to process dataset: {e}")
        return dataset

def apply_context_template(doc: Dict[str, Any], context_mode: str) -> Dict[str, Any]:
    """Apply context template to document with comprehensive context injection.
    
    Args:
        doc: Document to process
        context_mode: Context mode to apply ('no_context', 'minimal_context', 'full_context', 'domain_context')
        
    Returns:
        Dict: Document with applied context template
        
    Raises:
        ValueError: If context application fails critically
    """
    # Load context configurations
    current_dir = Path(__file__).parent
    context_config_file = current_dir / "context_configs.json"
    
    if not context_config_file.exists():
        eval_logger.warning(f"Context config file not found: {context_config_file}")
        doc['formatted_prompt'] = doc.get('prompt', '')
        return doc
    
    try:
        with open(context_config_file, 'r', encoding='utf-8') as f:
            context_configs = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        eval_logger.warning(f"Failed to load context configs: {e}")
        doc['formatted_prompt'] = doc.get('prompt', '')
        return doc
    
    # Validate context mode
    if context_mode not in context_configs:
        eval_logger.warning(f"Unknown context mode '{context_mode}' for problem {doc.get('id', 'unknown')}. Falling back to 'no_context'")
        context_mode = 'no_context'
    
    config = context_configs[context_mode]
    template = config.get('template', '{{prompt}}')
    
    # Apply template with context-specific substitutions
    try:
        formatted_prompt = template.replace('{{prompt}}', doc.get('prompt', ''))
        
        # Context-specific template substitutions
        if context_mode == 'minimal_context':
            requirements = _generate_minimal_requirements(doc)
            formatted_prompt = formatted_prompt.replace('{{requirements}}', requirements)
            
        elif context_mode == 'full_context':
            company_standards = _generate_company_standards(doc)
            best_practices = _generate_best_practices(doc)
            formatted_prompt = formatted_prompt.replace('{{company_standards}}', company_standards)
            formatted_prompt = formatted_prompt.replace('{{best_practices}}', best_practices)
            
        elif context_mode == 'domain_context':
            domain = doc.get('scenario', 'general')
            domain_requirements = _generate_domain_requirements(doc)
            formatted_prompt = formatted_prompt.replace('{{domain}}', domain)
            formatted_prompt = formatted_prompt.replace('{{domain_requirements}}', domain_requirements)
        
        doc['formatted_prompt'] = formatted_prompt
        doc['_context_applied'] = context_mode
        
    except Exception as e:
        eval_logger.error(f"Failed to apply context template for problem {doc.get('id', 'unknown')}: {e}")
        doc['formatted_prompt'] = doc.get('prompt', '')
        doc['_context_applied'] = 'error'
    
    return doc

def _generate_minimal_requirements(doc: Dict[str, Any]) -> str:
    """Generate minimal context requirements based on document properties."""
    language = doc.get('language', 'code')
    scenario = doc.get('scenario', 'general')
    
    requirements = [f"Requirements for {language}:"]
    
    # Language-specific requirements
    if language == 'python':
        requirements.extend([
            "- Follow PEP 8 style guidelines",
            "- Use type hints where appropriate",
            "- Include proper error handling"
        ])
    elif language in ['javascript', 'typescript']:
        requirements.extend([
            "- Use modern ES6+ syntax",
            "- Follow consistent naming conventions",
            "- Handle edge cases appropriately"
        ])
    elif language == 'java':
        requirements.extend([
            "- Follow Java naming conventions",
            "- Use appropriate access modifiers",
            "- Include proper exception handling"
        ])
    elif language in ['cpp', 'c++']:
        requirements.extend([
            "- Use modern C++ features (C++11 or later)",
            "- Manage memory properly",
            "- Follow RAII principles"
        ])
    elif language == 'go':
        requirements.extend([
            "- Follow Go formatting conventions",
            "- Use proper error handling patterns",
            "- Write idiomatic Go code"
        ])
    elif language == 'rust':
        requirements.extend([
            "- Follow Rust naming conventions",
            "- Use proper ownership and borrowing",
            "- Handle Result and Option types appropriately"
        ])
    else:
        requirements.extend([
            "- Follow language best practices",
            "- Include appropriate error handling",
            "- Write clean, readable code"
        ])
    
    # Scenario-specific requirements
    if scenario in ['algorithm_implementation', 'performance_optimization']:
        requirements.append("- Optimize for time and space complexity")
    elif scenario in ['security', 'api_design']:
        requirements.append("- Consider security implications")
    elif scenario == 'testing_strategy':
        requirements.append("- Include comprehensive test coverage")
    
    return '\n'.join(requirements)

def _generate_company_standards(doc: Dict[str, Any]) -> str:
    """Generate company standards context."""
    return """Company coding standards:
- Clean code principles: readable, maintainable, and well-documented
- Comprehensive testing with unit tests and integration tests
- Security-first approach with input validation and secure coding practices
- Code review requirements: all code must be reviewed before deployment
- Documentation: all public APIs and complex logic must be documented
- Performance considerations: code should be efficient and scalable"""

def _generate_best_practices(doc: Dict[str, Any]) -> str:
    """Generate best practices context based on document properties."""
    language = doc.get('language', 'code')
    scenario = doc.get('scenario', 'general')
    
    practices = [f"Best practices for {language}:"]
    
    # Language-specific best practices
    if language == 'python':
        practices.extend([
            "- Use list comprehensions and generator expressions appropriately",
            "- Leverage built-in functions and standard library",
            "- Use context managers for resource management"
        ])
    elif language in ['javascript', 'typescript']:
        practices.extend([
            "- Use async/await for asynchronous operations",
            "- Leverage functional programming concepts",
            "- Use proper module imports and exports"
        ])
    elif language == 'java':
        practices.extend([
            "- Use appropriate design patterns",
            "- Leverage Java 8+ features (streams, lambdas)",
            "- Use dependency injection where appropriate"
        ])
    
    # Scenario-specific best practices
    if scenario == 'api_design':
        practices.extend([
            "- Follow RESTful design principles",
            "- Use appropriate HTTP status codes",
            "- Implement proper authentication and authorization"
        ])
    elif scenario == 'database_design':
        practices.extend([
            "- Normalize database schema appropriately",
            "- Use proper indexing strategies",
            "- Implement data validation and constraints"
        ])
    
    return '\n'.join(practices)

def _generate_domain_requirements(doc: Dict[str, Any]) -> str:
    """Generate domain-specific requirements based on scenario."""
    scenario = doc.get('scenario', 'general')
    
    domain_requirements = {
        'system_design': [
            "- Consider scalability and performance requirements",
            "- Design for fault tolerance and reliability",
            "- Plan for monitoring and observability",
            "- Consider data consistency and availability trade-offs"
        ],
        'security': [
            "- Implement defense in depth strategies",
            "- Follow OWASP security guidelines",
            "- Use secure coding practices",
            "- Implement proper authentication and authorization"
        ],
        'api_design': [
            "- Follow RESTful API design principles",
            "- Implement proper versioning strategy",
            "- Use appropriate HTTP methods and status codes",
            "- Design for backward compatibility"
        ],
        'database_design': [
            "- Apply appropriate normalization techniques",
            "- Design efficient indexing strategies",
            "- Consider ACID properties and transaction management",
            "- Plan for data migration and schema evolution"
        ],
        'performance_optimization': [
            "- Profile code to identify bottlenecks",
            "- Optimize algorithms and data structures",
            "- Consider caching strategies",
            "- Minimize resource usage and latency"
        ],
        'testing_strategy': [
            "- Implement comprehensive test coverage",
            "- Use appropriate testing patterns (unit, integration, e2e)",
            "- Design tests for maintainability",
            "- Consider test automation and CI/CD integration"
        ]
    }
    
    requirements = domain_requirements.get(scenario, [
        "- Follow industry best practices",
        "- Consider maintainability and extensibility",
        "- Implement appropriate error handling",
        "- Document assumptions and design decisions"
    ])
    
    return f"Domain-specific requirements for {scenario}:\n" + '\n'.join(requirements)

def doc_to_text(doc: Dict[str, Any]) -> str:
    """Convert document to text for model input with context injection.
    
    Args:
        doc: Processed document with applied context
        
    Returns:
        str: Formatted text for model input
        
    Note:
        This function expects the document to have been processed by process_docs()
        which applies the appropriate context template.
    """
    # Use formatted_prompt if available (from context application)
    if 'formatted_prompt' in doc and doc['formatted_prompt']:
        return doc['formatted_prompt']
    
    # Fallback to original prompt
    prompt = doc.get('prompt', '')
    if not prompt:
        eval_logger.warning(f"No prompt found in document {doc.get('id', 'unknown')}")
        return ""
    
    return prompt

def doc_to_target(doc: Dict[str, Any]) -> str:
    """Extract target/reference from document for evaluation.
    
    Args:
        doc: Document containing reference implementation
        
    Returns:
        str: Target reference implementation or empty string if not available
        
    Note:
        Returns the first reference if multiple references are provided.
        This is used for metrics that compare against reference implementations.
    """
    reference = doc.get('reference', [])
    
    # Handle list of references
    if isinstance(reference, list):
        if reference:
            # Return first non-empty reference
            for ref in reference:
                if isinstance(ref, str) and ref.strip():
                    return ref.strip()
        return ""
    
    # Handle single string reference
    elif isinstance(reference, str):
        return reference.strip()
    
    # No reference available
    else:
        eval_logger.debug(f"No reference found in document {doc.get('id', 'unknown')}")
        return ""

def validate_problem_schema(problem: Dict[str, Any]) -> bool:
    """Validate problem against expected schema with comprehensive checks.
    
    Args:
        problem: Problem dictionary to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(problem, dict):
        eval_logger.error("Problem must be a dictionary")
        return False
    
    # Required fields validation
    required_fields = [
        'id', 'title', 'language', 'scenario', 'difficulty', 
        'context_mode', 'prompt'
    ]
    
    for field in required_fields:
        if field not in problem:
            eval_logger.error(f"Missing required field: {field} in problem {problem.get('id', 'unknown')}")
            return False
        if not isinstance(problem[field], str) or not problem[field].strip():
            eval_logger.error(f"Field '{field}' must be a non-empty string in problem {problem.get('id', 'unknown')}")
            return False
    
    # Validate field values against allowed options
    valid_languages = ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust', 'sql']
    valid_scenarios = [
        'code_completion', 'bug_fix', 'code_translation', 'documentation', 'function_generation',
        'system_design', 'algorithm_implementation', 'api_design', 'database_design', 
        'performance_optimization', 'full_stack', 'testing_strategy', 'security'
    ]
    valid_difficulties = ['simple', 'intermediate', 'complex']
    valid_context_modes = ['no_context', 'minimal_context', 'full_context', 'domain_context']
    
    if problem['language'] not in valid_languages:
        eval_logger.error(f"Invalid language '{problem['language']}' in problem {problem['id']}. Must be one of: {valid_languages}")
        return False
    
    if problem['scenario'] not in valid_scenarios:
        eval_logger.error(f"Invalid scenario '{problem['scenario']}' in problem {problem['id']}. Must be one of: {valid_scenarios}")
        return False
    
    if problem['difficulty'] not in valid_difficulties:
        eval_logger.error(f"Invalid difficulty '{problem['difficulty']}' in problem {problem['id']}. Must be one of: {valid_difficulties}")
        return False
    
    if problem['context_mode'] not in valid_context_modes:
        eval_logger.error(f"Invalid context_mode '{problem['context_mode']}' in problem {problem['id']}. Must be one of: {valid_context_modes}")
        return False
    
    # Validate optional fields if present
    if 'reference' in problem:
        if not isinstance(problem['reference'], (list, str)):
            eval_logger.error(f"Field 'reference' must be a string or list in problem {problem['id']}")
            return False
    
    if 'tests' in problem:
        if not isinstance(problem['tests'], list):
            eval_logger.error(f"Field 'tests' must be a list in problem {problem['id']}")
            return False
        for i, test in enumerate(problem['tests']):
            if not isinstance(test, dict):
                eval_logger.error(f"Test {i} must be a dictionary in problem {problem['id']}")
                return False
            if 'type' not in test or 'cmd' not in test:
                eval_logger.error(f"Test {i} missing required fields 'type' or 'cmd' in problem {problem['id']}")
                return False
    
    if 'metadata' in problem:
        if not isinstance(problem['metadata'], dict):
            eval_logger.error(f"Field 'metadata' must be a dictionary in problem {problem['id']}")
            return False
        
        # Validate metadata fields
        metadata = problem['metadata']
        if 'time_limit_s' in metadata and not isinstance(metadata['time_limit_s'], (int, float)):
            eval_logger.error(f"metadata.time_limit_s must be a number in problem {problem['id']}")
            return False
        if 'memory_limit_mb' in metadata and not isinstance(metadata['memory_limit_mb'], (int, float)):
            eval_logger.error(f"metadata.memory_limit_mb must be a number in problem {problem['id']}")
            return False
        if 'seed' in metadata and not isinstance(metadata['seed'], int):
            eval_logger.error(f"metadata.seed must be an integer in problem {problem['id']}")
            return False
    
    return True

def validate_metadata(metadata: Dict[str, Any]) -> bool:
    """Validate metadata dictionary against expected schema.
    
    Args:
        metadata: Metadata dictionary to validate
        
    Returns:
        bool: True if metadata is valid, False otherwise
    """
    if not isinstance(metadata, dict):
        eval_logger.error("Metadata must be a dictionary")
        return False
    
    # Optional fields with type validation
    optional_fields = {
        'time_limit_s': (int, float),
        'memory_limit_mb': (int, float),
        'seed': int,
        'author': str,
        'license': str
    }
    
    for field, expected_type in optional_fields.items():
        if field in metadata:
            if not isinstance(metadata[field], expected_type):
                eval_logger.error(f"Metadata field '{field}' must be of type {expected_type}")
                return False
            
            # Additional validation for specific fields
            if field == 'time_limit_s' and metadata[field] <= 0:
                eval_logger.error("time_limit_s must be positive")
                return False
            if field == 'memory_limit_mb' and metadata[field] <= 0:
                eval_logger.error("memory_limit_mb must be positive")
                return False
    
    return True

def get_dataset_statistics(dataset: datasets.Dataset) -> Dict[str, Any]:
    """Generate comprehensive statistics about the dataset.
    
    Args:
        dataset: Dataset to analyze
        
    Returns:
        Dict: Statistics including counts by scenario, difficulty, language, etc.
    """
    if len(dataset) == 0:
        return {"total_problems": 0}
    
    stats = {
        "total_problems": len(dataset),
        "by_scenario": {},
        "by_difficulty": {},
        "by_language": {},
        "by_context_mode": {},
        "problems_with_tests": 0,
        "problems_with_reference": 0,
        "problems_with_metadata": 0
    }
    
    for example in dataset:
        # Count by scenario
        scenario = example.get('scenario', 'unknown')
        stats['by_scenario'][scenario] = stats['by_scenario'].get(scenario, 0) + 1
        
        # Count by difficulty
        difficulty = example.get('difficulty', 'unknown')
        stats['by_difficulty'][difficulty] = stats['by_difficulty'].get(difficulty, 0) + 1
        
        # Count by language
        language = example.get('language', 'unknown')
        stats['by_language'][language] = stats['by_language'].get(language, 0) + 1
        
        # Count by context mode
        context_mode = example.get('context_mode', 'unknown')
        stats['by_context_mode'][context_mode] = stats['by_context_mode'].get(context_mode, 0) + 1
        
        # Count problems with additional data
        if 'tests' in example and example['tests']:
            stats['problems_with_tests'] += 1
        if 'reference' in example and example['reference']:
            stats['problems_with_reference'] += 1
        if 'metadata' in example and example['metadata']:
            stats['problems_with_metadata'] += 1
    
    return stats

def filter_by_scenario(dataset: datasets.Dataset, scenarios: List[str]) -> datasets.Dataset:
    """Filter dataset by specific scenarios.
    
    Args:
        dataset: Input dataset
        scenarios: List of scenario names to include
        
    Returns:
        datasets.Dataset: Filtered dataset containing only specified scenarios
    """
    return filter_by_metadata(dataset, {'scenario': scenarios})

def filter_by_difficulty(dataset: datasets.Dataset, difficulties: List[str]) -> datasets.Dataset:
    """Filter dataset by difficulty levels.
    
    Args:
        dataset: Input dataset
        difficulties: List of difficulty levels to include ('simple', 'intermediate', 'complex')
        
    Returns:
        datasets.Dataset: Filtered dataset containing only specified difficulties
    """
    return filter_by_metadata(dataset, {'difficulty': difficulties})

def filter_by_language(dataset: datasets.Dataset, languages: List[str]) -> datasets.Dataset:
    """Filter dataset by programming languages.
    
    Args:
        dataset: Input dataset
        languages: List of programming languages to include
        
    Returns:
        datasets.Dataset: Filtered dataset containing only specified languages
    """
    return filter_by_metadata(dataset, {'language': languages})

def get_problems_by_id(dataset: datasets.Dataset, problem_ids: List[str]) -> datasets.Dataset:
    """Get specific problems by their IDs.
    
    Args:
        dataset: Input dataset
        problem_ids: List of problem IDs to retrieve
        
    Returns:
        datasets.Dataset: Dataset containing only the specified problems
    """
    return filter_by_metadata(dataset, {'id': problem_ids})

def shuffle_dataset(dataset: datasets.Dataset, seed: Optional[int] = None) -> datasets.Dataset:
    """Shuffle dataset with optional seed for reproducibility.
    
    Args:
        dataset: Input dataset to shuffle
        seed: Optional seed for reproducible shuffling
        
    Returns:
        datasets.Dataset: Shuffled dataset
    """
    try:
        if seed is not None:
            shuffled = dataset.shuffle(seed=seed)
        else:
            shuffled = dataset.shuffle()
        eval_logger.info(f"Shuffled dataset with {len(shuffled)} problems")
        return shuffled
    except Exception as e:
        eval_logger.error(f"Failed to shuffle dataset: {e}")
        return dataset

def split_dataset(dataset: datasets.Dataset, 
                 train_ratio: float = 0.7, 
                 val_ratio: float = 0.15, 
                 test_ratio: float = 0.15,
                 seed: Optional[int] = None) -> Dict[str, datasets.Dataset]:
    """Split dataset into train/validation/test sets.
    
    Args:
        dataset: Input dataset to split
        train_ratio: Proportion for training set (default: 0.7)
        val_ratio: Proportion for validation set (default: 0.15)
        test_ratio: Proportion for test set (default: 0.15)
        seed: Optional seed for reproducible splitting
        
    Returns:
        Dict: Dictionary with 'train', 'val', and 'test' datasets
        
    Raises:
        ValueError: If ratios don't sum to 1.0 or dataset is too small
    """
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
        raise ValueError("Train, validation, and test ratios must sum to 1.0")
    
    if len(dataset) < 3:
        raise ValueError("Dataset must have at least 3 problems for splitting")
    
    # Shuffle first for random splitting
    shuffled = shuffle_dataset(dataset, seed=seed)
    
    total_size = len(shuffled)
    train_size = int(total_size * train_ratio)
    val_size = int(total_size * val_ratio)
    
    # Create splits
    train_dataset = shuffled.select(range(train_size))
    val_dataset = shuffled.select(range(train_size, train_size + val_size))
    test_dataset = shuffled.select(range(train_size + val_size, total_size))
    
    eval_logger.info(f"Split dataset: train={len(train_dataset)}, val={len(val_dataset)}, test={len(test_dataset)}")
    
    return {
        'train': train_dataset,
        'val': val_dataset,
        'test': test_dataset
    }

def extract_code_response(responses, docs):
    """Extract code from model responses (filter function for lm-eval).
    
    Args:
        responses: List of model responses
        docs: List of corresponding documents (not used)
        
    Returns:
        List[str]: List of extracted code responses
    """
    def _extract_single_response(response: str) -> str:
        """Extract code from a single model response."""
        # Look for code blocks
        code_block_pattern = r'```(?:python|javascript|java|cpp|go|rust)?\s*\n(.*?)\n```'
        matches = re.findall(code_block_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks, try to extract code-like content
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Simple heuristics for code detection
            if any(keyword in line.lower() for keyword in ['def ', 'function ', 'class ', 'import ', 'from ']):
                in_code = True
            
            if in_code:
                code_lines.append(line)
                
            # Stop if we hit explanatory text after code
            if in_code and line.strip() and not line.startswith((' ', '\t')) and not any(c in line for c in '(){}[];'):
                if len(line.split()) > 10:  # Likely explanatory text
                    break
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        # Fallback: return the response as-is
        return response.strip()
    
    # Process all responses
    # Handle case where responses might be nested lists
    processed_responses = []
    for resp in responses:
        if isinstance(resp, list):
            # If resp is a list, take the first element
            actual_resp = resp[0] if resp else ""
        else:
            actual_resp = resp
        processed_responses.append(_extract_single_response(str(actual_resp)))
    
    return processed_responses

# Configuration Management Integration
try:
    from .config_manager import get_config_manager, load_model_config, get_scenario_config
except ImportError:
    try:
        # Fallback for direct execution
        from config_manager import get_config_manager, load_model_config, get_scenario_config
    except ImportError:
        # If config_manager functions don't exist, create dummy functions
        def get_config_manager():
            return None
        
        def load_model_config(model_name: str):
            return {}
        
        def get_scenario_config(scenario: str):
            return {}

def get_model_configuration(model_name: str, scenario: Optional[str] = None) -> Dict[str, Any]:
    """Get model configuration with optional scenario-specific parameters.
    
    Args:
        model_name: Name of the model configuration to load
        scenario: Optional scenario name for scenario-specific parameters
        
    Returns:
        Dictionary containing model configuration parameters
        
    Raises:
        FileNotFoundError: If model configuration is not found
        ValueError: If configuration is invalid
    """
    try:
        config = load_model_config(model_name)
        
        if scenario:
            # Get scenario-specific parameters
            scenario_params = get_scenario_config(model_name, scenario)
            return {
                'model_config': config,
                'generation_params': scenario_params,
                'endpoint_config': config.endpoint_config,
                'batch_config': config.batch_config,
                'tokenizer_config': config.tokenizer_config,
                'optimization': config.optimization,
                'features': config.features,
                'metadata': config.metadata
            }
        else:
            # Return full configuration
            return {
                'model_config': config,
                'generation_params': config.generation_params,
                'endpoint_config': config.endpoint_config,
                'batch_config': config.batch_config,
                'tokenizer_config': config.tokenizer_config,
                'optimization': config.optimization,
                'features': config.features,
                'metadata': config.metadata
            }
            
    except Exception as e:
        eval_logger.error(f"Failed to load model configuration '{model_name}': {e}")
        raise

def get_available_model_configs() -> List[str]:
    """Get list of available model configurations.
    
    Returns:
        List of available model configuration names
    """
    config_manager = get_config_manager()
    return config_manager.get_available_configs()

def validate_model_config(config_name: str) -> bool:
    """Validate a specific model configuration.
    
    Args:
        config_name: Name of the configuration to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        load_model_config(config_name)
        return True
    except Exception as e:
        eval_logger.error(f"Configuration '{config_name}' validation failed: {e}")
        return False

def merge_model_config(base_config: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Merge a base model configuration with override parameters.
    
    Args:
        base_config: Name of the base configuration
        overrides: Dictionary of parameters to override
        
    Returns:
        Dictionary containing merged configuration
        
    Raises:
        FileNotFoundError: If base configuration is not found
        ValueError: If merged configuration is invalid
    """
    try:
        config_manager = get_config_manager()
        merged_config = config_manager.merge_configs(base_config, overrides)
        
        return {
            'model_config': merged_config,
            'generation_params': merged_config.generation_params,
            'endpoint_config': merged_config.endpoint_config,
            'batch_config': merged_config.batch_config,
            'tokenizer_config': merged_config.tokenizer_config,
            'optimization': merged_config.optimization,
            'features': merged_config.features,
            'metadata': merged_config.metadata
        }
        
    except Exception as e:
        eval_logger.error(f"Failed to merge configuration '{base_config}': {e}")
        raise