"""Code completion scenario implementation for single_turn_scenarios."""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from evaluation_engine.core.extended_tasks import AdvancedTask, ScenarioConfig, ScenarioType
from lm_eval.api.registry import register_task
from . import utils, metrics, sandbox

eval_logger = logging.getLogger(__name__)


@register_task("single_turn_scenarios_code_completion")
class CodeCompletionTask(AdvancedTask):
    """
    Code completion evaluation task.
    
    This task evaluates a model's ability to complete partial code implementations
    across multiple programming languages with proper syntax and functionality.
    """
    
    VERSION = 1.0
    DATASET_PATH = "problems.jsonl"
    DATASET_NAME = "single_turn_scenarios_code_completion"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize code completion task."""
        # Create scenario configuration
        scenario_config = ScenarioConfig(
            scenario_id="code_completion",
            scenario_type=ScenarioType.SINGLE_TURN,
            max_turns=1,
            scenario_metrics=[
                "syntax_validity",
                "code_execution_success", 
                "functionality_correctness",
                "code_quality_score"
            ],
            success_criteria={
                "syntax_validity": 0.8,
                "code_execution_success": 0.7,
                "functionality_correctness": 0.6
            }
        )
        
        super().__init__(
            data_dir=data_dir,
            cache_dir=cache_dir, 
            download_mode=download_mode,
            config=config,
            scenario_config=scenario_config
        )
        
        # Initialize sandbox executor for code execution
        self._sandbox_executors = {}
        
    def has_training_docs(self) -> bool:
        """Code completion task uses test split only."""
        return False
        
    def has_validation_docs(self) -> bool:
        """Code completion task uses test split only."""
        return False
        
    def has_test_docs(self) -> bool:
        """Code completion task has test documents."""
        return True
        
    def training_docs(self):
        """No training documents."""
        return []
        
    def validation_docs(self):
        """No validation documents."""
        return []
        
    def test_docs(self):
        """Load and return test documents."""
        return self._load_docs()
        
    def _load_docs(self):
        """Load documents from problems.jsonl file."""
        try:
            # Use the utils.load_dataset function which handles filtering
            dataset_dict = utils.load_dataset(metadata={"scenario": "code_completion"})
            dataset = dataset_dict["test"]
            
            # Process documents through utils
            processed_dataset = utils.process_docs(dataset)
            
            eval_logger.info(f"Loaded {len(processed_dataset)} code completion problems")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load code completion dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """
        Process model results and calculate metrics.
        
        Args:
            doc: Original document
            results: List of model predictions
            
        Returns:
            Dictionary of calculated metrics
        """
        if not results:
            return self._empty_results()
            
        prediction = results[0] if results else ""
        language = doc.get("language", "python")
        
        # Extract code from prediction if needed
        extracted_code = utils.extract_code_response(prediction)
        
        # Calculate basic metrics
        metrics_result = {}
        
        # 1. Syntax validity
        try:
            syntax_score = metrics.syntax_validity([extracted_code], language)
            metrics_result["syntax_validity"] = syntax_score
        except Exception as e:
            eval_logger.warning(f"Syntax validation failed: {e}")
            metrics_result["syntax_validity"] = 0.0
        
        # 2. Code execution and functionality
        execution_result = self._execute_code(extracted_code, doc, language)
        metrics_result.update(execution_result)
        
        # 3. Code quality metrics
        quality_metrics = self._calculate_quality_metrics(extracted_code, language)
        metrics_result.update(quality_metrics)
        
        # 4. Similarity to reference if available
        reference = doc.get("reference", [])
        if reference:
            similarity_metrics = self._calculate_similarity_metrics(
                extracted_code, reference[0] if isinstance(reference, list) else reference
            )
            metrics_result.update(similarity_metrics)
        
        return metrics_result
    
    def _execute_code(self, code: str, doc: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Execute code in sandbox and return execution metrics."""
        try:
            # Get or create sandbox executor for this language
            if language not in self._sandbox_executors:
                self._sandbox_executors[language] = sandbox.SandboxExecutor(
                    language=language,
                    limits={
                        'timeout_s': doc.get('metadata', {}).get('time_limit_s', 10),
                        'memory_mb': doc.get('metadata', {}).get('memory_limit_mb', 200)
                    }
                )
            
            executor = self._sandbox_executors[language]
            
            # Prepare tests from document
            tests = doc.get("tests", [])
            
            # Execute code
            result = executor.execute_code(code, tests)
            
            return {
                "code_execution_success": 1.0 if result.success else 0.0,
                "execution_time": result.wall_time,
                "memory_usage": result.peak_memory,
                "security_violations": len(result.security_violations),
                "functionality_correctness": 1.0 if result.success and result.exit_code == 0 else 0.0
            }
            
        except Exception as e:
            eval_logger.warning(f"Code execution failed: {e}")
            return {
                "code_execution_success": 0.0,
                "execution_time": 0.0,
                "memory_usage": 0,
                "security_violations": 0,
                "functionality_correctness": 0.0
            }
    
    def _calculate_quality_metrics(self, code: str, language: str) -> Dict[str, Any]:
        """Calculate code quality metrics."""
        try:
            quality_metrics = {}
            
            # Cyclomatic complexity
            complexity = metrics.cyclomatic_complexity([code], language)
            quality_metrics["cyclomatic_complexity"] = complexity
            
            # Security score
            security = metrics.security_score([code], language)
            quality_metrics["security_score"] = security
            
            # Overall code quality score (weighted combination)
            quality_score = (
                0.4 * security +  # Security is important
                0.3 * (1.0 / max(1.0, complexity / 5.0)) +  # Lower complexity is better
                0.3 * 1.0  # Base quality score
            )
            quality_metrics["code_quality_score"] = min(1.0, quality_score)
            
            return quality_metrics
            
        except Exception as e:
            eval_logger.warning(f"Quality metrics calculation failed: {e}")
            return {
                "cyclomatic_complexity": 1.0,
                "security_score": 1.0,
                "code_quality_score": 0.5
            }
    
    def _calculate_similarity_metrics(self, prediction: str, reference: str) -> Dict[str, Any]:
        """Calculate similarity metrics against reference."""
        try:
            similarity_metrics = {}
            
            # BLEU score for text similarity
            bleu = metrics.bleu_score([prediction], [reference])
            similarity_metrics["bleu_score"] = bleu
            
            # CodeBLEU for code similarity
            codebleu = metrics.codebleu_score([prediction], [reference])
            similarity_metrics["codebleu_score"] = codebleu
            
            # Edit distance
            edit_dist = metrics.edit_distance_score([prediction], [reference])
            similarity_metrics["edit_distance_score"] = edit_dist
            
            # Exact match
            exact = metrics.exact_match([prediction.strip()], [reference.strip()])
            similarity_metrics["exact_match"] = exact
            
            return similarity_metrics
            
        except Exception as e:
            eval_logger.warning(f"Similarity metrics calculation failed: {e}")
            return {
                "bleu_score": 0.0,
                "codebleu_score": 0.0,
                "edit_distance_score": 0.0,
                "exact_match": 0.0
            }
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "syntax_validity": 0.0,
            "code_execution_success": 0.0,
            "functionality_correctness": 0.0,
            "code_quality_score": 0.0,
            "execution_time": 0.0,
            "memory_usage": 0,
            "security_violations": 0,
            "cyclomatic_complexity": 1.0,
            "security_score": 0.0,
            "bleu_score": 0.0,
            "codebleu_score": 0.0,
            "edit_distance_score": 0.0,
            "exact_match": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {
            "syntax_validity": "mean",
            "code_execution_success": "mean", 
            "functionality_correctness": "mean",
            "code_quality_score": "mean",
            "execution_time": "mean",
            "memory_usage": "mean",
            "security_violations": "sum",
            "cyclomatic_complexity": "mean",
            "security_score": "mean",
            "bleu_score": "mean",
            "codebleu_score": "mean",
            "edit_distance_score": "mean",
            "exact_match": "mean"
        }
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {
            "syntax_validity": True,
            "code_execution_success": True,
            "functionality_correctness": True,
            "code_quality_score": True,
            "execution_time": False,  # Lower is better
            "memory_usage": False,   # Lower is better
            "security_violations": False,  # Lower is better
            "cyclomatic_complexity": False,  # Lower is better
            "security_score": True,
            "bleu_score": True,
            "codebleu_score": True,
            "edit_distance_score": True,
            "exact_match": True
        }