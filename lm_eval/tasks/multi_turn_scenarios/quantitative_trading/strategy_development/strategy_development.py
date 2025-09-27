"""Quantitative Trading Strategy Development multi-turn task implementation."""

import logging
from typing import Dict, List, Any, Optional
import re
import json

from evaluation_engine.core.extended_tasks import MultiTurnTask, ScenarioConfig, ScenarioType, TurnConfig
from lm_eval.api.registry import register_task
from ... import utils, metrics

eval_logger = logging.getLogger(__name__)


@register_task("multi_turn_scenarios_quantitative_strategy_development")
class QuantitativeStrategyDevelopmentTask(MultiTurnTask):
    """
    Multi-turn quantitative trading strategy development evaluation task.
    
    This task evaluates a model's ability to develop quantitative trading strategies
    including requirement analysis, factor selection, model construction, risk control, and validation.
    """
    
    VERSION = 1.0
    DATASET_PATH = "scenarios.jsonl"
    DATASET_NAME = "multi_turn_scenarios_quantitative_strategy_development"
    
    def __init__(self, data_dir=None, cache_dir=None, download_mode=None, config=None):
        """Initialize quantitative strategy development task."""
        scenario_config = ScenarioConfig(
            scenario_id="quantitative_strategy_development",
            scenario_type=ScenarioType.MULTI_TURN,
            max_turns=5,
            conversation_timeout=1200,
            enable_context_retention=True,
            turns=[
                TurnConfig(
                    turn_id="requirement_analysis",
                    turn_type="assistant_response",
                    role="assistant",
                    prompt_template="""You are a Quantitative Analyst developing a trading strategy:

**Strategy Objective**: {strategy_objective}
**Market Focus**: {market_focus}
**Risk Tolerance**: {risk_tolerance}
**Investment Horizon**: {investment_horizon}
**Capital Allocation**: {capital_allocation}

Please conduct requirement analysis:
1. Define clear strategy objectives and success metrics
2. Analyze market characteristics and opportunities
3. Identify key risk factors and constraints
4. Determine data requirements and sources
5. Outline regulatory and compliance considerations
6. Establish performance benchmarks and evaluation criteria

Present a comprehensive strategy development framework.""",
                    expected_format="strategy_requirements",
                    evaluation_metrics=["requirement_clarity", "market_analysis", "risk_assessment", "data_planning"],
                    temperature=0.2,
                    max_tokens=2500
                )
            ],
            scenario_metrics=[
                "quantitative_strategy_quality",
                "financial_domain_expertise",
                "risk_management_effectiveness",
                "overall_quant_development_score"
            ],
            success_criteria={
                "quantitative_strategy_quality": 0.7,
                "financial_domain_expertise": 0.8,
                "risk_management_effectiveness": 0.7
            }
        )
        
        super().__init__(
            data_dir=data_dir,
            cache_dir=cache_dir,
            download_mode=download_mode,
            config=config,
            scenario_config=scenario_config
        )       
 
        self.requirements = []
        self.factors = []
        self.models = []
        
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
            # Create sample quantitative trading scenarios
            sample_scenarios = [
                {
                    "id": "quant_strategy_001",
                    "scenario": "quantitative_strategy_development",
                    "strategy_objective": "Develop a market-neutral equity strategy targeting 12% annual returns",
                    "market_focus": "US Large Cap Equities",
                    "risk_tolerance": "Medium - Max 15% annual volatility",
                    "investment_horizon": "Medium-term (3-12 months)",
                    "capital_allocation": "$50M initial capital"
                },
                {
                    "id": "quant_strategy_002", 
                    "scenario": "quantitative_strategy_development",
                    "strategy_objective": "Create a momentum-based cryptocurrency trading strategy",
                    "market_focus": "Major Cryptocurrencies (BTC, ETH, etc.)",
                    "risk_tolerance": "High - Max 25% annual volatility",
                    "investment_horizon": "Short-term (1-30 days)",
                    "capital_allocation": "$10M initial capital"
                }
            ]
            
            processed_dataset = utils.process_docs(sample_scenarios)
            eval_logger.info(f"Loaded {len(processed_dataset)} quantitative strategy scenarios")
            return processed_dataset
            
        except Exception as e:
            eval_logger.error(f"Failed to load quantitative strategy dataset: {e}")
            return []
    
    def doc_to_text(self, doc: Dict[str, Any]) -> str:
        """Convert document to text prompt for model input."""
        return utils.doc_to_text(doc)
    
    def doc_to_target(self, doc: Dict[str, Any]) -> str:
        """Extract target reference from document."""
        return utils.doc_to_target(doc)
    
    def process_results(self, doc: Dict[str, Any], results: List[str]) -> Dict[str, Any]:
        """Process model results for quantitative strategy development."""
        if not results:
            return self._empty_results()
            
        turn_id = self._determine_current_turn(doc)
        prediction = results[0] if results else ""
        
        if turn_id == "requirement_analysis":
            return self._process_requirement_analysis(doc, prediction)
        else:
            return self._empty_results()
    
    def _determine_current_turn(self, doc: Dict[str, Any]) -> str:
        """Determine current turn based on conversation state."""
        return "requirement_analysis"  # Simplified for now
    
    def _process_requirement_analysis(self, doc: Dict[str, Any], prediction: str) -> Dict[str, Any]:
        """Process requirement analysis response."""
        self.requirements.append(prediction)
        
        metrics_result = {
            "response": prediction,
            "requirement_clarity": self._evaluate_requirement_clarity(prediction),
            "market_analysis": self._evaluate_market_analysis(prediction, doc),
            "risk_assessment": self._evaluate_risk_assessment(prediction),
            "data_planning": self._evaluate_data_planning(prediction),
            "financial_expertise": self._evaluate_financial_expertise(prediction),
            "quantitative_approach": self._evaluate_quantitative_approach(prediction)
        }
        
        return metrics_result
    
    def _evaluate_requirement_clarity(self, response: str) -> float:
        """Evaluate requirement clarity."""
        clarity_indicators = [
            "objective" in response.lower() or "goal" in response.lower(),
            "metric" in response.lower() or "measure" in response.lower(),
            "success" in response.lower() or "criteria" in response.lower(),
            "specific" in response.lower() or "clear" in response.lower(),
            "benchmark" in response.lower() or "target" in response.lower()
        ]
        return sum(clarity_indicators) / len(clarity_indicators)
    
    def _evaluate_market_analysis(self, response: str, doc: Dict[str, Any]) -> float:
        """Evaluate market analysis quality."""
        market_indicators = [
            "market" in response.lower() or "trading" in response.lower(),
            "liquidity" in response.lower() or "volume" in response.lower(),
            "volatility" in response.lower() or "risk" in response.lower(),
            "opportunity" in response.lower() or "alpha" in response.lower(),
            "correlation" in response.lower() or "factor" in response.lower()
        ]
        return sum(market_indicators) / len(market_indicators)
    
    def _evaluate_risk_assessment(self, response: str) -> float:
        """Evaluate risk assessment quality."""
        risk_indicators = [
            "risk" in response.lower() or "volatility" in response.lower(),
            "drawdown" in response.lower() or "loss" in response.lower(),
            "var" in response.lower() or "value at risk" in response.lower(),
            "sharpe" in response.lower() or "ratio" in response.lower(),
            "constraint" in response.lower() or "limit" in response.lower()
        ]
        return sum(risk_indicators) / len(risk_indicators)
    
    def _evaluate_data_planning(self, response: str) -> float:
        """Evaluate data planning quality."""
        data_indicators = [
            "data" in response.lower() or "dataset" in response.lower(),
            "source" in response.lower() or "provider" in response.lower(),
            "quality" in response.lower() or "clean" in response.lower(),
            "frequency" in response.lower() or "update" in response.lower(),
            "historical" in response.lower() or "backtest" in response.lower()
        ]
        return sum(data_indicators) / len(data_indicators)
    
    def _evaluate_financial_expertise(self, response: str) -> float:
        """Evaluate financial domain expertise."""
        finance_indicators = [
            "alpha" in response.lower() or "beta" in response.lower(),
            "sharpe" in response.lower() or "sortino" in response.lower(),
            "portfolio" in response.lower() or "asset" in response.lower(),
            "return" in response.lower() or "yield" in response.lower(),
            "hedge" in response.lower() or "arbitrage" in response.lower()
        ]
        return sum(finance_indicators) / len(finance_indicators)
    
    def _evaluate_quantitative_approach(self, response: str) -> float:
        """Evaluate quantitative approach quality."""
        quant_indicators = [
            "quantitative" in response.lower() or "statistical" in response.lower(),
            "model" in response.lower() or "algorithm" in response.lower(),
            "factor" in response.lower() or "signal" in response.lower(),
            "backtest" in response.lower() or "simulation" in response.lower(),
            "optimization" in response.lower() or "parameter" in response.lower()
        ]
        return sum(quant_indicators) / len(quant_indicators)
    
    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results when no predictions are available."""
        return {
            "requirement_clarity": 0.0,
            "market_analysis": 0.0,
            "risk_assessment": 0.0,
            "data_planning": 0.0,
            "financial_expertise": 0.0,
            "quantitative_approach": 0.0
        }
    
    def aggregation(self) -> Dict[str, Any]:
        """Define how metrics should be aggregated."""
        return {metric: "mean" for metric in self._empty_results().keys()}
    
    def higher_is_better(self) -> Dict[str, bool]:
        """Define whether higher values are better for each metric."""
        return {metric: True for metric in self._empty_results().keys()}