"""
Generic adapter validator that coordinates real execution testing.
"""

import logging
from typing import Dict, Any, List
from ..models.test_models import TestConfiguration, ValidationResult, AdapterType
from .lm_eval_adapter_validator import LMEvalAdapterValidator
from .swe_bench_adapter_validator import SWEBenchAdapterValidator


class AdapterValidator:
    """Coordinates validation of all adapters with REAL execution."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.AdapterValidator")
        self.validators = {
            AdapterType.LM_EVAL: LMEvalAdapterValidator(),
            AdapterType.SWE_BENCH: SWEBenchAdapterValidator()
        }
    
    def validate_adapter(self, test_config: TestConfiguration) -> Dict[str, Any]:
        """Validate specific adapter with REAL execution."""
        adapter_name = test_config.task_selection.get("adapter", "lm_eval")
        
        self.logger.info(f"🚀 Starting REAL validation for adapter: {adapter_name}")
        
        result = {
            "success": False,
            "metrics": {},
            "artifacts": [],
            "logs": [],
            "error": None,
            "validation_result": None
        }
        
        try:
            # Map adapter name to type
            adapter_type_map = {
                "lm_eval": AdapterType.LM_EVAL,
                "swe_bench": AdapterType.SWE_BENCH,
                "intercode": AdapterType.INTERCODE,
                "convcode": AdapterType.CONVCODE
            }
            
            adapter_type = adapter_type_map.get(adapter_name, AdapterType.LM_EVAL)
            
            if adapter_type not in self.validators:
                raise ValueError(f"No validator available for adapter type: {adapter_type}")
            
            # Get validator and run REAL validation
            validator = self.validators[adapter_type]
            validation_result = validator.validate_integration()
            
            result["validation_result"] = validation_result
            result["metrics"].update(validation_result.performance_metrics)
            
            # Determine success
            result["success"] = validation_result.integration_status.value == "passed"
            
            # Add logs
            result["logs"].append(f"Adapter: {validation_result.adapter_name}")
            result["logs"].append(f"Status: {validation_result.integration_status.value}")
            result["logs"].append(f"Dependencies installed: {validation_result.dependencies_installed}")
            result["logs"].append(f"Tests run: {len(validation_result.test_results)}")
            result["logs"].append(f"Validation time: {validation_result.validation_time:.2f}s")
            
            if validation_result.issues_found:
                result["logs"].append(f"Issues found: {len(validation_result.issues_found)}")
                for issue in validation_result.issues_found:
                    result["logs"].append(f"  - {issue}")
            
            if result["success"]:
                result["logs"].append("✅ REAL adapter validation PASSED!")
            else:
                result["logs"].append("❌ REAL adapter validation FAILED!")
                result["error"] = f"Validation failed: {validation_result.issues_found}"
            
        except Exception as e:
            result["error"] = str(e)
            result["logs"].append(f"❌ Adapter validation error: {e}")
            self.logger.error(f"Adapter validation failed: {e}")
        
        return result
    
    def validate_all_adapters(self) -> Dict[str, ValidationResult]:
        """Validate all available adapters with REAL execution."""
        self.logger.info("🚀 Starting REAL validation for ALL adapters...")
        
        results = {}
        
        for adapter_type, validator in self.validators.items():
            try:
                self.logger.info(f"Validating {adapter_type.value} adapter...")
                validation_result = validator.validate_integration()
                results[adapter_type.value] = validation_result
                
                if validation_result.integration_status.value == "passed":
                    self.logger.info(f"✅ {adapter_type.value} validation PASSED")
                else:
                    self.logger.warning(f"⚠️ {adapter_type.value} validation FAILED")
                    
            except Exception as e:
                self.logger.error(f"❌ {adapter_type.value} validation ERROR: {e}")
                # Create error result
                from ..models.test_models import TestStatus
                error_result = ValidationResult(
                    adapter_name=adapter_type.value,
                    adapter_type=adapter_type,
                    integration_status=TestStatus.ERROR,
                    dependencies_installed=False
                )
                error_result.issues_found.append(str(e))
                results[adapter_type.value] = error_result
        
        return results


def create_adapter_validator() -> AdapterValidator:
    """Factory function to create adapter validator."""
    return AdapterValidator()