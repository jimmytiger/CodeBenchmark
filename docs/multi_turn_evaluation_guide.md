# Multi-Turn Evaluation Scenarios User Guide

## Overview

Multi-turn evaluation scenarios assess language models through interactive conversations that simulate real-world collaborative workflows. These scenarios evaluate context retention, iterative improvement, and complex reasoning across multiple exchanges.

## Available Multi-Turn Scenarios

### 1. Code Review Process (`multi_turn_scenarios_code_review`)

**Purpose**: Simulate a complete code review workflow with iterative feedback and improvements.

**Conversation Flow**:
1. **Initial Submission**: Developer submits code for review
2. **Review Analysis**: Model provides comprehensive code review
3. **Code Revision**: Developer addresses feedback
4. **Follow-up Review**: Model reviews changes
5. **Final Approval**: Model approves or requests further changes

**Example Conversation**:
```
Turn 1 (Human): Please review this Python function:
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

Turn 1 (Model): I've reviewed your code. Here are my observations:

**Strengths:**
- Clear function name and simple logic
- Handles the basic requirement correctly

**Issues to Address:**
1. **Missing Documentation**: No docstring explaining parameters and return value
2. **Type Hints**: Missing type annotations for better code clarity
3. **Input Validation**: No validation for None or non-iterable inputs
4. **Edge Cases**: Doesn't handle empty lists explicitly

**Recommendations:**
```python
def process_data(data: List[Union[int, float]]) -> List[Union[int, float]]:
    """
    Process numerical data by doubling positive values.
    
    Args:
        data: List of numerical values to process
        
    Returns:
        List containing doubled positive values from input
        
    Raises:
        TypeError: If data is not iterable
        ValueError: If data contains non-numerical values
    """
    if data is None:
        raise ValueError("Data cannot be None")
    
    if not hasattr(data, '__iter__'):
        raise TypeError("Data must be iterable")
    
    result = []
    for item in data:
        if not isinstance(item, (int, float)):
            raise ValueError(f"All items must be numerical, got {type(item)}")
        if item > 0:
            result.append(item * 2)
    
    return result
```

Turn 2 (Human): Thanks for the feedback. Here's my revised version:
[Updated code with improvements]

Turn 2 (Model): Excellent improvements! Your revised code addresses all the major concerns:

✅ **Documentation**: Clear docstring with parameters and return value
✅ **Type Hints**: Proper type annotations added
✅ **Input Validation**: Comprehensive error handling
✅ **Code Quality**: Much more robust and maintainable

**Minor Suggestions:**
- Consider using `typing.Union` import for cleaner type hints
- The function looks production-ready!

**Status**: APPROVED ✅
```

**Metrics**:
- `review_thoroughness`: Completeness of code analysis
- `improvement_quality`: Quality of suggested improvements
- `code_standards_compliance`: Adherence to coding standards
- `iterative_progress`: Improvement across conversation turns
- `final_code_quality`: Quality of final approved code

### 2. Debugging Session (`multi_turn_scenarios_debug_session`)

**Purpose**: Collaborative debugging process to identify and resolve software issues.

**Conversation Flow**:
1. **Problem Description**: User describes the bug or issue
2. **Hypothesis Formation**: Model proposes potential causes
3. **Evidence Gathering**: Collect logs, reproduce steps, analyze code
4. **Root Cause Analysis**: Identify the underlying issue
5. **Solution Implementation**: Develop and test the fix

**Example Conversation**:
```
Turn 1 (Human): My web application is randomly crashing with a 500 error. It happens about once every hour during peak traffic. The logs show "Database connection timeout" but our database server seems fine.

Turn 1 (Model): Let's systematically debug this issue. Based on your description, I have several hypotheses:

**Primary Hypotheses:**
1. **Connection Pool Exhaustion**: Too many concurrent connections
2. **Long-Running Queries**: Queries holding connections too long
3. **Connection Leak**: Connections not being properly released
4. **Network Issues**: Intermittent connectivity problems

**Next Steps - Let's gather evidence:**
1. Can you share your database connection configuration?
2. What's your current connection pool size?
3. Do you have monitoring on active database connections?
4. Are there any patterns in the timing of these errors?

**Immediate Check:**
```sql
-- Check current active connections
SHOW PROCESSLIST;
-- Look for long-running queries or sleeping connections
```

Turn 2 (Human): Here's my connection config:
```python
DATABASE_CONFIG = {
    'host': 'db.example.com',
    'pool_size': 5,
    'max_overflow': 10,
    'pool_timeout': 30,
    'pool_recycle': 3600
}
```

The monitoring shows we hit 15 connections during peak times. Some queries run for 2-3 minutes.

Turn 2 (Model): **Root Cause Identified!** 🎯

Your connection pool is too small for your traffic pattern:
- Pool size: 5 + 10 overflow = 15 max connections
- You're hitting the limit during peak traffic
- Long-running queries (2-3 minutes) are holding connections
- New requests timeout waiting for available connections

**Solution Strategy:**
1. **Immediate Fix**: Increase pool size
2. **Long-term Fix**: Optimize slow queries
3. **Monitoring**: Add connection pool metrics

**Implementation:**
```python
DATABASE_CONFIG = {
    'host': 'db.example.com',
    'pool_size': 20,        # Increased from 5
    'max_overflow': 30,     # Increased from 10
    'pool_timeout': 60,     # Increased timeout
    'pool_recycle': 3600,
    'pool_pre_ping': True   # Validate connections
}
```

**Query Optimization:**
- Identify the 2-3 minute queries
- Add appropriate indexes
- Consider query result caching
- Implement connection pooling monitoring

Would you like me to help optimize specific slow queries?
```

**Metrics**:
- `diagnostic_accuracy`: Correctness of problem identification
- `solution_effectiveness`: Quality of proposed solutions
- `debugging_efficiency`: Speed of reaching root cause
- `systematic_approach`: Use of structured debugging methodology

### 3. Design Iteration (`multi_turn_scenarios_design_iteration`)

**Purpose**: Iterative design process with stakeholder feedback and refinement.

**Conversation Flow**:
1. **Initial Proposal**: Present initial design concept
2. **Stakeholder Feedback**: Gather requirements and concerns
3. **Design Refinement**: Modify design based on feedback
4. **Validation**: Verify design meets requirements
5. **Final Approval**: Stakeholder approval of final design

**Metrics**:
- `design_quality`: Overall design effectiveness
- `stakeholder_satisfaction`: Meeting stakeholder needs
- `requirement_coverage`: Addressing all requirements
- `design_evolution`: Improvement through iterations

### 4. Teaching Dialogue (`multi_turn_scenarios_teaching_dialogue`)

**Purpose**: Educational conversation that adapts to student understanding and progress.

**Conversation Flow**:
1. **Concept Introduction**: Introduce new topic or concept
2. **Understanding Check**: Assess student comprehension
3. **Examples and Practice**: Provide examples and exercises
4. **Assessment**: Test understanding with questions
5. **Advanced Topics**: Progress to more complex concepts

**Example Conversation**:
```
Turn 1 (Model): Today we'll learn about Big O notation - a way to describe how algorithms perform as input size grows. 

Think of it like describing how long it takes to find a book:
- In a small pile (10 books): Quick to search through
- In a library (10,000 books): Much longer without a system

Big O describes this relationship mathematically. The most common complexities are:
- O(1): Constant time - same speed regardless of size
- O(n): Linear time - time grows proportionally with size
- O(n²): Quadratic time - time grows with square of size

Can you think of a real-world example where time increases linearly with the amount of work?

Turn 1 (Human): Like reading a book? The more pages, the longer it takes?

Turn 1 (Model): Perfect example! 📚 Reading a book is indeed O(n) - if a book has twice as many pages, it takes roughly twice as long to read.

Let's apply this to programming. Here are three ways to find if a number exists in a list:

**Method 1: Linear Search**
```python
def find_number(numbers, target):
    for num in numbers:  # Check each number one by one
        if num == target:
            return True
    return False
```
This is O(n) - we might need to check every number.

**Method 2: Binary Search (sorted list)**
```python
def binary_search(sorted_numbers, target):
    left, right = 0, len(sorted_numbers) - 1
    while left <= right:
        mid = (left + right) // 2
        if sorted_numbers[mid] == target:
            return True
        elif sorted_numbers[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return False
```
This is O(log n) - we eliminate half the possibilities each step.

Which method do you think would be faster for a list of 1 million numbers?
```

**Metrics**:
- `teaching_effectiveness`: Student learning progress
- `concept_clarity`: Clear explanation of concepts
- `engagement_level`: Student participation and interest
- `adaptive_instruction`: Adjusting to student needs

## Quantitative Trading Scenarios

### 5. Strategy Development (`multi_turn_scenarios_quantitative_strategy_development`)

**Purpose**: Develop comprehensive quantitative trading strategies through collaborative analysis.

**Conversation Flow**:
1. **Requirement Analysis**: Define strategy objectives and constraints
2. **Factor Selection**: Identify and evaluate potential factors
3. **Model Construction**: Build predictive models
4. **Risk Control**: Implement risk management measures
5. **Validation**: Backtest and validate strategy performance

**Example Conversation**:
```
Turn 1 (Human): I want to develop a momentum strategy for US equities. Target Sharpe ratio > 1.5, max drawdown < 15%. Focus on mid-cap stocks.

Turn 1 (Model): Excellent strategy parameters! Let's build a robust momentum strategy. Here's my systematic approach:

**Strategy Framework:**
- **Universe**: Mid-cap US equities (market cap $2B-$10B)
- **Target Metrics**: Sharpe > 1.5, Max DD < 15%
- **Style**: Momentum-based with risk controls

**Phase 1: Factor Selection & Analysis**

**Primary Momentum Factors:**
1. **Price Momentum**: 12-1 month returns (skip last month)
2. **Earnings Momentum**: Quarterly EPS surprise and revisions
3. **Technical Momentum**: RSI, MACD convergence
4. **Volume Momentum**: Price-volume relationship

**Factor Construction:**
```python
# Price momentum (12-1 month)
def price_momentum(prices):
    return (prices.iloc[-1] / prices.iloc[-252:-21].mean()) - 1

# Earnings momentum
def earnings_momentum(eps_surprises, revisions):
    surprise_score = eps_surprises.rolling(4).mean()
    revision_score = revisions.rolling(60).mean()
    return (surprise_score + revision_score) / 2
```

**Risk Factors to Control:**
- Market beta, size, value, profitability
- Sector concentration
- Volatility clustering

**Next Steps:**
1. Historical factor performance analysis
2. Factor correlation matrix
3. Decay analysis for optimal rebalancing frequency

What's your preference for rebalancing frequency? Monthly or quarterly?

Turn 2 (Human): Let's go with monthly rebalancing. Also, I'm concerned about sector concentration - tech stocks dominate momentum lately.

Turn 2 (Model): Smart observation! Tech concentration is a real risk in momentum strategies. Let's address this:

**Sector Neutralization Approach:**
```python
def sector_neutral_momentum(returns, sectors, target_positions=50):
    """
    Create sector-neutral momentum portfolio
    """
    momentum_scores = calculate_momentum_scores(returns)
    
    # Sector constraints: max 25% in any sector
    sector_weights = {}
    for sector in sectors.unique():
        sector_mask = sectors == sector
        sector_stocks = momentum_scores[sector_mask].nlargest(
            min(10, int(target_positions * 0.25))  # Max 25% per sector
        )
        sector_weights[sector] = sector_stocks
    
    return create_equal_weight_portfolio(sector_weights)
```

**Enhanced Strategy Design:**
1. **Sector Constraints**: Max 25% allocation per sector
2. **Stock Constraints**: Max 3% per individual stock
3. **Momentum Decay**: Weight recent performance more heavily
4. **Volatility Adjustment**: Risk-adjust momentum scores

**Risk Management Framework:**
```python
def risk_adjusted_momentum(returns, volatility, market_beta):
    """
    Adjust momentum scores for risk
    """
    raw_momentum = calculate_momentum(returns)
    vol_adjustment = 1 / volatility.rolling(60).mean()
    beta_adjustment = 1 / abs(market_beta)
    
    return raw_momentum * vol_adjustment * beta_adjustment
```

**Backtesting Framework:**
- Start date: 2010-01-01 (post-crisis)
- Transaction costs: 10 bps per trade
- Market impact: 5 bps for mid-cap stocks
- Rebalancing: Monthly (last trading day)

Ready to proceed with backtesting? I'll need historical price and fundamental data.
```

**Metrics**:
- `strategy_sophistication`: Complexity and depth of strategy
- `risk_management_quality`: Effectiveness of risk controls
- `implementation_feasibility`: Practical implementability
- `performance_expectations`: Realistic performance projections

### 6. Multi-factor Model Construction (`multi_turn_scenarios_multifactor_model`)

**Purpose**: Build sophisticated multi-factor models for return prediction.

**Conversation Flow**:
1. **Factor Mining**: Identify potential predictive factors
2. **Factor Testing**: Statistical validation of factors
3. **Model Synthesis**: Combine factors into unified model
4. **Validation**: Out-of-sample testing
5. **Optimization**: Parameter tuning and refinement

**Metrics**:
- `model_sophistication`: Statistical rigor and complexity
- `predictive_accuracy`: Out-of-sample performance
- `factor_significance`: Statistical significance of factors
- `model_stability`: Consistency across time periods

### 7. Market Research Analysis (`multi_turn_scenarios_market_research`)

**Purpose**: Conduct comprehensive market research with statistical analysis.

**Conversation Flow**:
1. **Objective Setting**: Define research questions and hypotheses
2. **Data Collection**: Gather relevant market data
3. **Statistical Testing**: Apply appropriate statistical methods
4. **Interpretation**: Analyze results and draw conclusions
5. **Risk Assessment**: Evaluate limitations and risks

**Metrics**:
- `research_rigor`: Quality of research methodology
- `statistical_validity`: Proper use of statistical methods
- `insight_quality`: Depth and actionability of insights
- `risk_awareness`: Recognition of limitations and risks

### 8. Portfolio Risk Assessment (`multi_turn_scenarios_portfolio_risk`)

**Purpose**: Comprehensive portfolio risk analysis and optimization.

**Conversation Flow**:
1. **Composition Analysis**: Analyze current portfolio holdings
2. **Risk Calculation**: Calculate various risk metrics
3. **Attribution Analysis**: Identify sources of risk
4. **Optimization**: Recommend risk reduction strategies
5. **Monitoring**: Set up ongoing risk monitoring

**Metrics**:
- `risk_measurement_accuracy`: Correctness of risk calculations
- `attribution_quality`: Accuracy of risk source identification
- `optimization_effectiveness`: Quality of risk reduction recommendations
- `monitoring_comprehensiveness`: Completeness of monitoring framework

## Running Multi-Turn Evaluations

### Basic Multi-Turn Evaluation

```python
from evaluation_engine import EvaluationClient

client = EvaluationClient(api_key="your-api-key")

# Code review evaluation
evaluation = client.create_evaluation(
    models=[{
        "model_id": "anthropic/claude-3-opus",
        "model_type": "anthropic",
        "config": {"temperature": 0.5}
    }],
    tasks=[{
        "task_id": "multi_turn_scenarios_code_review",
        "max_turns": 5,
        "context_mode": "full_context",
        "num_scenarios": 20
    }]
)

# Monitor conversation progress
for update in client.stream_progress(evaluation.id):
    print(f"Scenario {update.current_scenario}: Turn {update.current_turn}")
    print(f"Progress: {update.progress:.1%}")
```

### Advanced Multi-Turn Configuration

```python
# Quantitative trading strategy evaluation
evaluation = client.create_evaluation(
    models=[
        {"model_id": "openai/gpt-4", "model_type": "openai"},
        {"model_id": "anthropic/claude-3-opus", "model_type": "anthropic"}
    ],
    tasks=[{
        "task_id": "multi_turn_scenarios_quantitative_strategy_development",
        "max_turns": 8,
        "conversation_timeout": 1800,  # 30 minutes per conversation
        "context_retention": True,
        "domain_expertise": "quantitative_finance",
        "scenario_configs": {
            "strategy_types": ["momentum", "mean_reversion", "arbitrage"],
            "asset_classes": ["equities", "fixed_income", "commodities"],
            "complexity_levels": ["intermediate", "advanced"]
        }
    }]
)
```

### Custom Turn Configuration

```python
# Teaching dialogue with adaptive difficulty
evaluation = client.create_evaluation(
    models=[{"model_id": "openai/gpt-4", "model_type": "openai"}],
    tasks=[{
        "task_id": "multi_turn_scenarios_teaching_dialogue",
        "turn_configs": [
            {
                "turn_id": "concept_introduction",
                "role": "teacher",
                "temperature": 0.7,
                "max_tokens": 1000,
                "evaluation_criteria": ["clarity", "engagement"]
            },
            {
                "turn_id": "understanding_check",
                "role": "teacher",
                "temperature": 0.3,
                "max_tokens": 500,
                "evaluation_criteria": ["assessment_accuracy", "feedback_quality"]
            }
        ]
    }]
)
```

## Context Management

### Context Retention Strategies

1. **Full Context**: Maintain complete conversation history
2. **Sliding Window**: Keep last N turns in context
3. **Summarization**: Compress older context into summaries
4. **Key Information**: Extract and retain critical information

### Context Configuration

```python
context_config = {
    "retention_strategy": "sliding_window",
    "window_size": 10,
    "summarization_threshold": 5,
    "key_information_extraction": True,
    "context_compression": {
        "enabled": True,
        "compression_ratio": 0.3,
        "preserve_code": True
    }
}
```

## Conversation Flow Control

### Turn Dependencies

```yaml
# Example turn configuration for code review
turns:
  - turn_id: "initial_submission"
    role: "human"
    required: true
    
  - turn_id: "initial_review"
    role: "assistant"
    depends_on: ["initial_submission"]
    evaluation_criteria: ["thoroughness", "accuracy"]
    
  - turn_id: "code_revision"
    role: "human"
    depends_on: ["initial_review"]
    optional: true
    
  - turn_id: "follow_up_review"
    role: "assistant"
    depends_on: ["code_revision"]
    conditional: "if code_revision provided"
```

### Branching Conversations

```python
# Conditional conversation paths
branching_config = {
    "branch_conditions": [
        {
            "condition": "student_understanding_low",
            "action": "provide_additional_examples",
            "next_turn": "remedial_explanation"
        },
        {
            "condition": "student_understanding_high",
            "action": "advance_to_next_topic",
            "next_turn": "advanced_concepts"
        }
    ]
}
```

## Metrics and Evaluation

### Conversation-Level Metrics

- **Context Retention**: How well context is maintained across turns
- **Coherence**: Logical flow and consistency of conversation
- **Goal Achievement**: Success in reaching conversation objectives
- **Engagement Quality**: Level of meaningful interaction

### Turn-Level Metrics

- **Response Relevance**: Appropriateness of each response
- **Information Quality**: Accuracy and usefulness of information
- **Communication Effectiveness**: Clarity and understanding
- **Progress Contribution**: How each turn advances the conversation

### Domain-Specific Metrics

**Code Review**:
- Review thoroughness and accuracy
- Code improvement quality
- Standards compliance

**Teaching**:
- Concept explanation clarity
- Student engagement level
- Learning progression

**Quantitative Trading**:
- Strategy sophistication
- Risk management quality
- Implementation feasibility

## Best Practices

### Conversation Design

1. **Clear Objectives**: Define specific goals for each conversation
2. **Natural Flow**: Design realistic conversation patterns
3. **Error Recovery**: Handle misunderstandings gracefully
4. **Progress Tracking**: Monitor advancement toward goals

### Model Configuration

1. **Temperature Settings**: Adjust for conversation style
2. **Context Length**: Optimize for conversation depth
3. **Response Length**: Balance detail with engagement
4. **Consistency**: Maintain consistent persona/expertise level

### Evaluation Strategy

1. **Multiple Scenarios**: Test diverse conversation types
2. **Statistical Significance**: Use adequate sample sizes
3. **Human Validation**: Validate automated metrics with human judgment
4. **Longitudinal Analysis**: Track performance across conversation length

## Troubleshooting

### Common Issues

**Context Loss**:
- Increase context window size
- Improve summarization strategy
- Use key information extraction

**Inconsistent Responses**:
- Lower temperature for consistency
- Improve persona definition
- Add conversation state tracking

**Poor Conversation Flow**:
- Review turn dependencies
- Improve transition prompts
- Add conversation flow validation

**Low Engagement**:
- Adjust response style
- Improve question quality
- Add interactive elements

This comprehensive guide enables effective evaluation of language models in complex, multi-turn scenarios that mirror real-world collaborative workflows.