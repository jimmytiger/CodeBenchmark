# Quantitative Trading Scenarios Documentation

## Overview

The AI Evaluation Engine includes specialized multi-turn scenarios for evaluating language models in quantitative finance and algorithmic trading contexts. These scenarios assess models' capabilities in financial analysis, strategy development, risk management, and quantitative research.

## Financial Domain Expertise

### Core Competencies Evaluated

1. **Quantitative Analysis**: Mathematical modeling and statistical analysis
2. **Risk Management**: Portfolio risk assessment and mitigation strategies
3. **Strategy Development**: Systematic trading strategy construction
4. **Market Research**: Data-driven market analysis and insights
5. **Financial Engineering**: Complex financial instrument modeling
6. **Regulatory Compliance**: Understanding of financial regulations
7. **Performance Attribution**: Analysis of strategy performance drivers
8. **Execution Optimization**: Trade execution and market microstructure

## Available Quantitative Trading Scenarios

### 1. Strategy Development (`multi_turn_scenarios_quantitative_strategy_development`)

**Purpose**: Comprehensive development of quantitative trading strategies from conception to implementation.

**Financial Domain Focus**:
- **Factor Research**: Identification and validation of predictive factors
- **Alpha Generation**: Development of return-generating signals
- **Risk Modeling**: Construction of risk models and controls
- **Portfolio Construction**: Optimization and allocation methodologies
- **Backtesting**: Historical performance validation
- **Implementation**: Practical trading considerations

**Conversation Flow**:
```
Turn 1: Strategy Conceptualization
- Investment universe definition
- Return objectives and risk constraints
- Benchmark selection and tracking error targets
- Regulatory and capacity constraints

Turn 2: Factor Research and Selection
- Fundamental factors (value, quality, profitability)
- Technical factors (momentum, mean reversion)
- Alternative data factors (sentiment, satellite data)
- Factor correlation and orthogonalization
- Factor decay and stability analysis

Turn 3: Signal Construction and Combination
- Individual factor scoring methodologies
- Signal combination techniques (equal weight, optimization, ML)
- Signal timing and frequency considerations
- Regime-dependent signal adjustments

Turn 4: Risk Model Development
- Systematic risk factor identification
- Specific risk estimation
- Risk model validation and stress testing
- Dynamic risk adjustment mechanisms

Turn 5: Portfolio Construction
- Optimization objective functions (mean-variance, risk parity, etc.)
- Constraint specification (sector, country, liquidity)
- Transaction cost modeling
- Portfolio rebalancing frequency optimization

Turn 6: Backtesting and Validation
- Historical simulation methodology
- Performance attribution analysis
- Drawdown analysis and risk-adjusted returns
- Out-of-sample validation procedures

Turn 7: Implementation Strategy
- Trading infrastructure requirements
- Market impact and execution algorithms
- Operational risk considerations
- Monitoring and maintenance procedures

Turn 8: Performance Monitoring and Enhancement
- Real-time performance tracking
- Strategy decay detection
- Continuous improvement processes
- Capacity management and scaling
```

**Example Conversation**:
```
Turn 1 (Human): I want to develop a long-short equity strategy for US large-cap stocks. Target 15% annual return with max 20% volatility. Benchmark is S&P 500.

Turn 1 (Model): Excellent strategy parameters! Let's build a robust long-short equity framework. Here's my systematic approach:

**Strategy Specification:**
- **Universe**: US large-cap equities (S&P 500 + Russell 1000)
- **Style**: Long-short market neutral with modest beta exposure
- **Target Metrics**: 15% return, 20% vol, Sharpe > 0.75
- **Benchmark**: S&P 500 (for beta exposure component)

**Initial Framework Design:**

**1. Investment Universe Refinement:**
```python
def define_universe():
    criteria = {
        'market_cap': '>$2B',
        'avg_daily_volume': '>$10M',
        'listing_age': '>2 years',
        'sector_exclusions': ['REITs', 'Utilities'],  # Low alpha potential
        'liquidity_score': '>75th percentile'
    }
    return apply_universe_filters(criteria)
```

**2. Return Target Decomposition:**
- **Market Beta Component**: 3-5% (0.3-0.5 beta to S&P 500)
- **Alpha Generation**: 10-12% from long-short selection
- **Risk Budget Allocation**:
  - Systematic factors: 60% of risk budget
  - Specific stock selection: 40% of risk budget

**3. Preliminary Factor Categories:**
- **Value**: P/E, P/B, EV/EBITDA, FCF Yield
- **Quality**: ROE, Debt/Equity, Earnings Stability
- **Growth**: EPS growth, Revenue growth, Analyst revisions
- **Momentum**: Price momentum, Earnings momentum
- **Low Risk**: Low volatility, Low beta

**Key Questions for Next Phase:**
1. Do you have a preference for factor weighting methodology?
2. What's your tolerance for sector concentration?
3. Any specific ESG or sustainability requirements?
4. Preferred rebalancing frequency (monthly/quarterly)?

**Risk Considerations Already Identified:**
- Style drift risk (value vs growth cycles)
- Concentration risk in mega-cap names
- Liquidity risk during market stress
- Model overfitting to historical data

Ready to dive into factor research and backtesting framework?

Turn 2 (Human): Let's focus on momentum and quality factors. Monthly rebalancing. I want to avoid concentration - max 3% per stock, 25% per sector.

Turn 2 (Model): Perfect focus! Momentum + Quality is a proven combination with strong academic backing. Let's build this systematically:

**Enhanced Strategy Design: Momentum-Quality Framework**

**Factor Construction:**

**1. Momentum Factors (40% weight):**
```python
def momentum_factors():
    return {
        'price_momentum_12_1': (price[-1] / price[-252:-21].mean()) - 1,
        'price_momentum_6_1': (price[-1] / price[-126:-21].mean()) - 1,
        'earnings_momentum': rolling_eps_surprises(4).mean(),
        'analyst_revisions': analyst_eps_revisions(60).mean(),
        'technical_momentum': rsi_divergence() + macd_signal()
    }
```

**2. Quality Factors (40% weight):**
```python
def quality_factors():
    return {
        'roe_stability': roe.rolling(12).std() / roe.rolling(12).mean(),
        'earnings_quality': (operating_cf - net_income) / total_assets,
        'balance_sheet_quality': (debt_to_equity + current_ratio) / 2,
        'profitability_trend': roe.rolling(8).apply(lambda x: linregress(range(8), x).slope),
        'piotroski_score': calculate_piotroski_score()
    }
```

**3. Combined Signal (20% risk control):**
```python
def combined_signal():
    momentum_score = weighted_average(momentum_factors(), momentum_weights)
    quality_score = weighted_average(quality_factors(), quality_weights)
    
    # Risk adjustment
    volatility_adj = 1 / realized_volatility(60)
    beta_adj = 1 / abs(market_beta(252))
    
    return (momentum_score + quality_score) * volatility_adj * beta_adj
```

**Portfolio Construction with Constraints:**
```python
def optimize_portfolio(signals, constraints):
    """
    Optimize portfolio with concentration limits
    """
    from cvxpy import *
    
    n_stocks = len(signals)
    weights = Variable(n_stocks)
    
    # Objective: maximize expected return
    objective = Maximize(signals.T @ weights)
    
    constraints = [
        # Long-short constraint
        sum(weights) == 0,  # Market neutral
        
        # Position size limits
        weights <= 0.03,    # Max 3% long position
        weights >= -0.03,   # Max 3% short position
        
        # Sector concentration (implement sector_weights matrix)
        sector_weights @ abs(weights) <= 0.25,  # Max 25% per sector
        
        # Gross exposure
        sum(abs(weights)) <= 1.0,  # 100% gross exposure
        
        # Turnover constraint (if previous weights available)
        sum(abs(weights - prev_weights)) <= 0.4  # Max 40% monthly turnover
    ]
    
    problem = Problem(objective, constraints)
    problem.solve()
    
    return weights.value
```

**Risk Management Framework:**
- **Factor Exposure Limits**: Max 0.3 beta to any style factor
- **Sector Neutrality**: Target +/- 5% vs benchmark weights
- **Liquidity Management**: Min 20 days to liquidate any position
- **Correlation Monitoring**: Max 0.7 correlation between long/short books

**Backtesting Methodology:**
1. **Sample Period**: 2010-2023 (includes various market regimes)
2. **Rebalancing**: Monthly (last trading day)
3. **Transaction Costs**: 15 bps per trade + market impact
4. **Capacity Analysis**: Test up to $1B AUM

**Expected Performance Characteristics:**
- **Annual Return**: 12-18% (target 15%)
- **Volatility**: 16-22% (target 20%)
- **Sharpe Ratio**: 0.7-0.9
- **Max Drawdown**: <15%
- **Win Rate**: 55-60% of months positive

**Next Steps:**
1. Historical factor performance analysis
2. Correlation matrix and factor orthogonalization
3. Regime analysis (bull/bear/sideways markets)
4. Stress testing against major market events

Shall we proceed with the backtesting framework and historical analysis?
```

**Evaluation Metrics**:
- **Strategy Sophistication**: Depth of quantitative methodology
- **Risk Management Quality**: Comprehensive risk framework
- **Implementation Feasibility**: Practical trading considerations
- **Performance Realism**: Realistic return expectations
- **Factor Understanding**: Knowledge of factor investing principles
- **Market Microstructure**: Understanding of execution challenges

### 2. Multi-factor Model Construction (`multi_turn_scenarios_multifactor_model`)

**Purpose**: Build sophisticated multi-factor models for return prediction and risk management.

**Financial Domain Focus**:
- **Factor Mining**: Systematic discovery of return predictors
- **Statistical Testing**: Rigorous factor validation methodologies
- **Model Architecture**: Linear and non-linear model construction
- **Regime Detection**: Time-varying factor exposures
- **Cross-Asset Models**: Multi-asset class factor models
- **Alternative Data**: Integration of non-traditional data sources

**Conversation Flow**:
```
Turn 1: Model Specification and Objectives
- Return prediction vs risk modeling objectives
- Asset universe and frequency considerations
- Factor categories and data sources
- Model complexity and interpretability trade-offs

Turn 2: Factor Research and Mining
- Fundamental factor construction
- Technical and price-based factors
- Macro-economic factors
- Alternative data integration
- Factor transformation and normalization

Turn 3: Statistical Validation Framework
- Factor significance testing
- Multicollinearity analysis
- Stability testing across time periods
- Cross-sectional vs time-series analysis

Turn 4: Model Architecture Design
- Linear factor models (Fama-French extensions)
- Machine learning approaches (regularization, ensemble methods)
- Regime-switching models
- Dynamic factor models

Turn 5: Risk Model Integration
- Systematic vs specific risk decomposition
- Factor covariance matrix estimation
- Risk forecasting and updating
- Stress testing and scenario analysis

Turn 6: Model Validation and Testing
- In-sample vs out-of-sample performance
- Cross-validation methodologies
- Model stability and decay analysis
- Benchmark comparison and attribution

Turn 7: Implementation and Production
- Model updating frequency and procedures
- Data quality and missing value handling
- Computational efficiency optimization
- Model monitoring and maintenance

Turn 8: Enhancement and Research Pipeline
- Continuous factor research process
- Model ensemble and combination techniques
- Regime adaptation mechanisms
- Performance feedback integration
```

**Evaluation Metrics**:
- **Model Sophistication**: Statistical rigor and complexity
- **Predictive Accuracy**: Out-of-sample forecasting performance
- **Factor Significance**: Statistical validity of factors
- **Model Stability**: Consistency across time periods
- **Implementation Quality**: Production-ready considerations

### 3. Market Research Analysis (`multi_turn_scenarios_market_research`)

**Purpose**: Conduct comprehensive quantitative market research with statistical rigor.

**Financial Domain Focus**:
- **Hypothesis Formation**: Structured research question development
- **Data Collection**: Multi-source data aggregation and cleaning
- **Statistical Methodology**: Appropriate statistical test selection
- **Causal Inference**: Distinguishing correlation from causation
- **Economic Significance**: Practical vs statistical significance
- **Research Documentation**: Reproducible research practices

**Example Research Topics**:
- **Market Anomalies**: Calendar effects, earnings announcement drift
- **Cross-Asset Relationships**: Equity-bond correlations, currency carry
- **Behavioral Finance**: Sentiment indicators, herding behavior
- **Market Microstructure**: Bid-ask spreads, market impact models
- **Macro-Finance**: Interest rate sensitivity, inflation hedging

**Evaluation Metrics**:
- **Research Rigor**: Quality of research methodology
- **Statistical Validity**: Proper use of statistical methods
- **Insight Quality**: Depth and actionability of findings
- **Risk Awareness**: Recognition of limitations and biases

### 4. Portfolio Risk Assessment (`multi_turn_scenarios_portfolio_risk`)

**Purpose**: Comprehensive portfolio risk analysis and optimization.

**Financial Domain Focus**:
- **Risk Decomposition**: Factor vs specific risk attribution
- **VaR and CVaR**: Value-at-Risk methodologies
- **Stress Testing**: Scenario analysis and tail risk assessment
- **Correlation Analysis**: Dynamic correlation modeling
- **Liquidity Risk**: Market liquidity and funding risk
- **Operational Risk**: Settlement, counterparty, and model risk

**Risk Metrics Covered**:
- **Market Risk**: Delta, gamma, vega exposures
- **Credit Risk**: Default probability and loss given default
- **Liquidity Risk**: Bid-ask spreads and market depth
- **Concentration Risk**: Single name and sector exposures
- **Model Risk**: Parameter uncertainty and model error

**Evaluation Metrics**:
- **Risk Measurement Accuracy**: Correctness of risk calculations
- **Attribution Quality**: Accurate risk source identification
- **Optimization Effectiveness**: Quality of risk reduction strategies
- **Monitoring Framework**: Comprehensive ongoing risk tracking

### 5. Execution Algorithm Optimization (`multi_turn_scenarios_execution_algorithm`)

**Purpose**: Optimize trade execution algorithms for minimal market impact and cost.

**Financial Domain Focus**:
- **Market Microstructure**: Order book dynamics and price formation
- **Execution Strategies**: TWAP, VWAP, implementation shortfall
- **Market Impact Models**: Temporary vs permanent impact
- **Algorithmic Trading**: Smart order routing and dark pools
- **Transaction Cost Analysis**: Explicit vs implicit costs
- **Regulatory Considerations**: Best execution requirements

**Algorithm Types Evaluated**:
- **Volume-Weighted Average Price (VWAP)**
- **Time-Weighted Average Price (TWAP)**
- **Implementation Shortfall (IS)**
- **Participation Rate Algorithms**
- **Liquidity-Seeking Algorithms**
- **Arrival Price Algorithms**

**Evaluation Metrics**:
- **Algorithm Effectiveness**: Cost reduction and impact minimization
- **Implementation Quality**: Practical execution considerations
- **Market Impact Understanding**: Microstructure knowledge
- **Performance Measurement**: Appropriate benchmarking

### 6. High Frequency Trading (`multi_turn_scenarios_high_frequency_trading`)

**Purpose**: Develop high-frequency trading strategies with microsecond precision.

**Financial Domain Focus**:
- **Latency Optimization**: Hardware and software optimization
- **Market Making**: Bid-ask spread capture and inventory management
- **Statistical Arbitrage**: Mean reversion at high frequencies
- **News Analytics**: Real-time news processing and reaction
- **Co-location**: Exchange proximity and infrastructure
- **Regulatory Compliance**: Market manipulation and fairness

**Technical Considerations**:
- **Latency Measurement**: One-way vs round-trip latency
- **Order Management**: Smart order routing and execution
- **Risk Management**: Real-time position and exposure monitoring
- **Data Processing**: Tick-by-tick data handling and storage
- **Infrastructure**: Hardware acceleration and networking

**Evaluation Metrics**:
- **Signal Quality**: Predictive power at high frequencies
- **Latency Optimization**: Speed and efficiency improvements
- **Risk Control**: Real-time risk management effectiveness
- **Profitability**: Risk-adjusted returns after costs

### 7. Fundamental Analysis (`multi_turn_scenarios_fundamental_analysis`)

**Purpose**: Conduct comprehensive fundamental analysis for equity valuation.

**Financial Domain Focus**:
- **Financial Statement Analysis**: Income, balance sheet, cash flow analysis
- **Valuation Models**: DCF, comparable company, precedent transactions
- **Industry Analysis**: Competitive positioning and market dynamics
- **Management Assessment**: Corporate governance and strategy evaluation
- **Economic Moats**: Sustainable competitive advantages
- **ESG Integration**: Environmental, social, governance factors

**Valuation Methodologies**:
- **Discounted Cash Flow (DCF)**
- **Relative Valuation (P/E, EV/EBITDA)**
- **Asset-Based Valuation**
- **Option-Based Valuation**
- **Sum-of-the-Parts Analysis**
- **Scenario-Based Valuation**

**Evaluation Metrics**:
- **Analysis Depth**: Thoroughness of fundamental research
- **Valuation Accuracy**: Reasonable valuation estimates
- **Risk Assessment**: Identification of key risks
- **Investment Thesis**: Clear and compelling investment rationale

### 8. Technical Analysis (`multi_turn_scenarios_technical_analysis`)

**Purpose**: Apply technical analysis for market timing and trend identification.

**Financial Domain Focus**:
- **Chart Patterns**: Support, resistance, trend lines
- **Technical Indicators**: Moving averages, oscillators, momentum
- **Volume Analysis**: Volume-price relationships
- **Market Sentiment**: Fear/greed indicators, positioning data
- **Intermarket Analysis**: Cross-asset technical relationships
- **Quantitative Technical Analysis**: Statistical pattern recognition

**Technical Tools Evaluated**:
- **Trend Following**: Moving averages, trend channels
- **Momentum Indicators**: RSI, MACD, Stochastic
- **Volatility Indicators**: Bollinger Bands, ATR
- **Volume Indicators**: OBV, Accumulation/Distribution
- **Sentiment Indicators**: VIX, Put/Call ratios
- **Pattern Recognition**: Head and shoulders, triangles, flags

**Evaluation Metrics**:
- **Signal Accuracy**: Predictive power of technical signals
- **Pattern Recognition**: Correct identification of chart patterns
- **Risk Management**: Stop-loss and position sizing
- **Strategy Completeness**: Comprehensive trading framework

## Domain-Specific Evaluation Criteria

### Financial Knowledge Assessment

**Level 1: Basic Financial Literacy**
- Understanding of basic financial concepts (risk, return, diversification)
- Knowledge of major asset classes and instruments
- Awareness of market participants and structure

**Level 2: Intermediate Quantitative Finance**
- Portfolio theory and optimization
- Factor models and risk attribution
- Basic derivatives and hedging strategies
- Statistical analysis and hypothesis testing

**Level 3: Advanced Quantitative Methods**
- Advanced derivatives pricing models
- Machine learning applications in finance
- High-frequency trading and market microstructure
- Alternative risk premia and exotic strategies

**Level 4: Expert-Level Specialization**
- Cutting-edge research and methodology development
- Regulatory and compliance expertise
- Cross-asset and global macro strategies
- Institutional implementation and operational considerations

### Risk Management Sophistication

**Risk Identification**:
- Market risk (delta, gamma, vega, theta)
- Credit risk (default, migration, concentration)
- Liquidity risk (funding, market liquidity)
- Operational risk (model, settlement, counterparty)
- Regulatory risk (compliance, capital requirements)

**Risk Measurement**:
- Value-at-Risk (VaR) methodologies
- Expected Shortfall (CVaR)
- Stress testing and scenario analysis
- Monte Carlo simulation
- Factor decomposition and attribution

**Risk Management**:
- Hedging strategies and instruments
- Portfolio optimization and allocation
- Dynamic risk budgeting
- Real-time monitoring and alerts
- Crisis management procedures

### Implementation Realism

**Trading Infrastructure**:
- Order management systems (OMS)
- Execution management systems (EMS)
- Risk management systems (RMS)
- Data management and storage
- Connectivity and market access

**Operational Considerations**:
- Settlement and clearing processes
- Regulatory reporting requirements
- Audit trails and compliance monitoring
- Disaster recovery and business continuity
- Cost analysis and fee structures

**Scalability and Capacity**:
- Strategy capacity constraints
- Infrastructure scaling requirements
- Performance degradation analysis
- Operational complexity management
- Resource allocation and budgeting

## Evaluation Methodology

### Quantitative Metrics

**Strategy Performance**:
- Risk-adjusted returns (Sharpe, Sortino, Calmar ratios)
- Maximum drawdown and recovery time
- Win/loss ratios and profit factors
- Tail risk measures (VaR, CVaR)
- Benchmark-relative performance

**Model Quality**:
- Statistical significance of factors
- Out-of-sample R-squared
- Information coefficient (IC)
- Model stability across time periods
- Prediction accuracy metrics

**Risk Management**:
- Risk budget utilization
- Risk-adjusted performance attribution
- Stress test results
- Correlation forecasting accuracy
- Tail risk prediction

### Qualitative Assessment

**Financial Expertise**:
- Depth of domain knowledge
- Understanding of market dynamics
- Awareness of regulatory environment
- Recognition of practical constraints
- Integration of multiple perspectives

**Analytical Rigor**:
- Statistical methodology appropriateness
- Data quality and preprocessing
- Model validation procedures
- Robustness testing
- Documentation and reproducibility

**Communication Quality**:
- Clear explanation of complex concepts
- Appropriate use of financial terminology
- Visual presentation of results
- Risk disclosure and limitations
- Actionable recommendations

## Best Practices for Quantitative Finance Evaluation

### Data Quality and Preprocessing

1. **Survivorship Bias**: Include delisted securities in historical analysis
2. **Look-Ahead Bias**: Ensure point-in-time data availability
3. **Data Snooping**: Use proper cross-validation and out-of-sample testing
4. **Corporate Actions**: Adjust for splits, dividends, and spin-offs
5. **Currency Effects**: Handle multi-currency exposures appropriately

### Model Development and Validation

1. **Feature Engineering**: Create meaningful financial variables
2. **Regime Awareness**: Account for changing market conditions
3. **Transaction Costs**: Include realistic trading costs and market impact
4. **Capacity Constraints**: Consider strategy scalability limitations
5. **Model Decay**: Monitor and address performance degradation

### Risk Management Integration

1. **Real-Time Monitoring**: Implement continuous risk oversight
2. **Stress Testing**: Regular scenario analysis and tail risk assessment
3. **Correlation Breakdown**: Prepare for correlation regime changes
4. **Liquidity Management**: Maintain adequate liquidity buffers
5. **Regulatory Compliance**: Ensure adherence to applicable regulations

### Performance Attribution and Analysis

1. **Factor Attribution**: Decompose returns into systematic sources
2. **Transaction Cost Analysis**: Measure implementation efficiency
3. **Benchmark Selection**: Choose appropriate performance benchmarks
4. **Statistical Significance**: Test for meaningful outperformance
5. **Risk-Adjusted Metrics**: Focus on risk-adjusted performance measures

This comprehensive documentation provides the financial domain expertise necessary for evaluating language models in quantitative trading and finance contexts, ensuring assessments reflect real-world industry standards and practices.