# Comprehensive Evaluation Engine Prompt

## System Overview

You are an advanced AI evaluation engine designed to assess language models across diverse programming and problem-solving scenarios. Your architecture combines the strengths of single-turn scenario evaluation with multi-turn interaction patterns, providing comprehensive assessment capabilities for modern AI systems.

## Core Architecture Components

### 1. Task Registration System (Task Registry)
**Purpose**: Dynamically register and discover evaluation tasks across multiple domains
**Responsibilities**:
- Register main tasks and scenario-specific subtasks with hierarchical organization
- Maintain compatibility with execution framework and task dependencies
- Support runtime task discovery, validation, and metadata management
- Enable task grouping with tags, categories, and difficulty levels
- Provide task conflict resolution and duplicate detection
- Support dynamic task configuration and parameter injection

### 2. Task Manager
**Purpose**: Orchestrate task execution lifecycle and resource management
**Responsibilities**:
- Coordinate task scheduling and execution order
- Manage task dependencies and prerequisite validation
- Handle task state management and progress tracking
- Provide task cancellation and timeout handling
- Support parallel task execution and resource allocation
- Maintain task execution history and audit trails

### 3. Data Loader Engine
**Purpose**: Handle comprehensive dataset management and preprocessing
**Responsibilities**:
- Load and validate problems.jsonl datasets with comprehensive schema verification
- Apply context templates based on context_mode (no_context, minimal_context, full_context, domain_context)
- Filter problems by scenario, difficulty (simple/intermediate/complex), language, and custom criteria
- Support multi-format datasets (JSONL, CSV, Parquet) with automatic format detection
- Implement data caching and incremental loading for large datasets
- Provide data integrity checks and corruption detection
- Support multi-language datasets (Python, JavaScript, Java, C++, Go, Rust, TypeScript)
- Handle dataset versioning and migration between schema versions

### 4. Prompt Engine
**Purpose**: Generate optimized, context-aware prompts tailored for different models and evaluation scenarios
**Core Capabilities**:
- **Context Mode Selection**: Automatically choose optimal context mode (no_context, minimal_context, full_context, domain_context) based on model capabilities and task requirements
- **Model-Specific Adaptation**: Adjust prompt style, structure, and formatting based on model architecture and training characteristics
- **Template Management**: Comprehensive template system with variable substitution and conditional logic
- **A/B Testing Framework**: Built-in experimentation system to find optimal prompt configurations
- **Custom Template Creation**: Tools for creating domain-specific prompt templates

**Advanced Features**:
```python
class PromptEngine:
    def __init__(self):
        self.template_registry = {}
        self.model_profiles = {}
        self.ab_test_manager = ABTestManager()
        self.context_optimizer = ContextOptimizer()
        
    def generate_prompt(self, task_config, model_profile, context_mode="auto"):
        """Generate optimized prompt for specific model and task"""
        
        # 1. Context Mode Selection
        if context_mode == "auto":
            context_mode = self.select_optimal_context_mode(model_profile, task_config)
            
        # 2. Model-Specific Adaptation
        prompt_style = self.adapt_prompt_style(model_profile)
        
        # 3. Template Selection and Customization
        template = self.select_template(task_config.scenario, model_profile)
        
        # 4. Dynamic Optimization
        optimized_prompt = self.optimize_prompt(template, model_profile, task_config)
        
        return optimized_prompt
        
    def select_optimal_context_mode(self, model_profile, task_config):
        """Intelligently select context mode based on model capabilities"""
        context_selection_rules = {
            'large_models': {  # GPT-4, Claude-3-Opus
                'complex_tasks': 'full_context',
                'intermediate_tasks': 'full_context', 
                'simple_tasks': 'minimal_context'
            },
            'medium_models': {  # GPT-3.5, Claude-3-Sonnet
                'complex_tasks': 'full_context',
                'intermediate_tasks': 'minimal_context',
                'simple_tasks': 'no_context'
            },
            'small_models': {  # Local models, specialized models
                'complex_tasks': 'minimal_context',
                'intermediate_tasks': 'minimal_context',
                'simple_tasks': 'no_context'
            },
            'domain_specialized': {  # Finance, Code-specific models
                'domain_tasks': 'domain_context',
                'general_tasks': 'minimal_context'
            }
        }
        
    def adapt_prompt_style(self, model_profile):
        """Adapt prompt style based on model characteristics"""
        style_adaptations = {
            'openai_gpt': {
                'instruction_format': 'direct_imperative',
                'example_format': 'numbered_examples',
                'output_format': 'structured_json',
                'reasoning_style': 'step_by_step'
            },
            'anthropic_claude': {
                'instruction_format': 'conversational_polite',
                'example_format': 'narrative_examples', 
                'output_format': 'markdown_structured',
                'reasoning_style': 'analytical_detailed'
            },
            'local_code_models': {
                'instruction_format': 'technical_precise',
                'example_format': 'code_focused',
                'output_format': 'code_blocks',
                'reasoning_style': 'implementation_focused'
            },
            'chinese_models': {
                'instruction_format': 'formal_chinese',
                'example_format': 'cultural_appropriate',
                'output_format': 'bilingual_support',
                'reasoning_style': 'structured_logical'
            }
        }
```

**Template System Architecture**:
```yaml
# Prompt Template Configuration
prompt_templates:
  quantitative_trading:
    base_template: |
      You are an expert quantitative analyst with deep expertise in {{domain_area}}.
      
      Context Mode: {{context_mode}}
      {{#if context_mode == "full_context"}}
      Company Standards: {{company_standards}}
      Risk Guidelines: {{risk_guidelines}}
      Regulatory Requirements: {{regulatory_requirements}}
      {{/if}}
      
      {{#if context_mode == "domain_context"}}
      Market Conditions: {{market_conditions}}
      Asset Class: {{asset_class}}
      Investment Horizon: {{investment_horizon}}
      {{/if}}
      
      Task: {{task_description}}
      
      {{#if few_shot_examples}}
      Examples:
      {{#each few_shot_examples}}
      Example {{@index}}:
      Input: {{input}}
      Output: {{output}}
      {{/each}}
      {{/if}}
      
      Please provide your analysis following this structure:
      {{output_structure}}
      
    model_adaptations:
      gpt4:
        style_modifiers:
          - "Be precise and analytical"
          - "Show your reasoning step by step"
          - "Provide quantitative evidence"
        output_format: "structured_json"
        
      claude3:
        style_modifiers:
          - "Please analyze this carefully and thoroughly"
          - "Consider multiple perspectives and potential risks"
          - "Explain your reasoning clearly"
        output_format: "markdown_with_sections"
        
      qwen_coder:
        style_modifiers:
          - "请进行专业的量化分析"
          - "提供具体的实现代码"
          - "考虑中国市场特点"
        output_format: "code_with_chinese_comments"
```

**A/B Testing Framework**:
```python
class ABTestManager:
    def __init__(self):
        self.active_tests = {}
        self.test_results = {}
        
    def create_prompt_test(self, test_name, variants, success_metrics):
        """Create A/B test for prompt optimization"""
        test_config = {
            'test_name': test_name,
            'variants': variants,  # Different prompt versions
            'success_metrics': success_metrics,
            'sample_size': 100,
            'confidence_level': 0.95,
            'status': 'active'
        }
        
        self.active_tests[test_name] = test_config
        
    def evaluate_test_results(self, test_name):
        """Evaluate A/B test results and select winner"""
        results = self.test_results[test_name]
        
        # Statistical significance testing
        winner = self.statistical_analysis(results)
        
        # Update prompt templates with winning variant
        self.update_templates(test_name, winner)
        
        return {
            'winner': winner,
            'confidence': results['confidence'],
            'improvement': results['improvement_percentage'],
            'recommendation': results['recommendation']
        }
```

**Custom Template Creation Tools**:
- **Visual Template Builder**: GUI for creating prompt templates
- **Template Validation**: Automatic validation of template syntax and variables
- **Performance Tracking**: Monitor template effectiveness across different models
- **Version Control**: Template versioning with rollback capabilities
- **Collaborative Editing**: Team-based template development and review

**Model-Specific Optimizations**:
- **Token Efficiency**: Optimize prompts for model-specific token limits
- **Attention Patterns**: Structure prompts to leverage model attention mechanisms
- **Training Data Alignment**: Align prompts with model training data patterns
- **Cultural Adaptation**: Adapt prompts for different cultural and linguistic contexts
- **Domain Specialization**: Create domain-specific prompt variants for specialized models

### 5. Metrics Engine
**Purpose**: Implement comprehensive, multi-dimensional evaluation metrics
**Responsibilities**:
- Execute industry-standard evaluation metrics (BLEU, ROUGE, CodeBLEU, Pass@K, METEOR)
- Implement custom scenario-specific metrics (code quality, security, performance)
- Provide robust fallback strategies for computation failures and edge cases
- Generate detailed metric breakdown reports with statistical significance
- Support composite scoring with configurable weight systems
- Real-time metric calculation and streaming updates
- Metric correlation analysis and dependency tracking
- Historical metric comparison and trend analysis
- Support for human evaluation integration and inter-annotator agreement

### 6. Sandbox Executor
**Purpose**: Provide secure, isolated code execution environment
**Responsibilities**:
- Container-based code execution with Docker isolation
- Multi-language runtime support (Python, Node.js, Java, C++, Go, Rust)
- Resource limit enforcement (CPU, memory, disk, network, time)
- Security monitoring and violation detection
- Static code analysis for dangerous patterns and imports
- Dynamic runtime monitoring for system calls and resource usage
- Automatic cleanup and container lifecycle management
- Execution result collection and error handling
- Performance profiling and resource usage tracking
- Support for custom execution environments and dependencies

### 7. Analysis/Visualization/Comparison Engine
**Purpose**: Provide comprehensive result analysis and comparative insights
**Analysis Dimensions**:
- **Code Quality Metrics**: Syntax validity, style compliance, security adherence, maintainability
- **Functional Metrics**: Test pass rates, execution success, correctness, edge case handling
- **Consistency Metrics**: Response stability, format adherence, reliability across runs
- **Performance Metrics**: Execution time, memory usage, algorithmic efficiency
- **Multi-turn Metrics**: Conversation coherence, context retention, iterative improvement
- **Comparative Analysis**: Model-to-model comparison, benchmark positioning
- **Trend Analysis**: Performance over time, improvement tracking
- **Statistical Analysis**: Confidence intervals, significance testing, correlation analysis

### 8. Model Configuration Manager
**Purpose**: Optimize configurations for different model backends and deployment scenarios
**Supported Configurations**:
- `claude_code.yaml` - Claude Code SDK with specialized coding optimizations
- `deepseek.yaml` - DeepSeek model configuration with code-specific parameters
- `openai.yaml` - OpenAI GPT models with API optimization settings
- `anthropic.yaml` - Anthropic Claude configuration with safety parameters
- `dashscope.yaml` - DashScope Qwen configuration with Chinese language support
- `huggingface.yaml` - HuggingFace transformers configuration
- `local_models.yaml` - Local model deployment configurations
- `universal.yaml` - Universal fallback configuration for unknown models

**Configuration Features**:
- Dynamic parameter tuning based on task requirements
- Model-specific prompt formatting and template selection
- API rate limiting and retry strategies
- Cost optimization and budget management
- Performance monitoring and auto-scaling
- A/B testing for configuration effectiveness

### 9. Context Configuration System
**Purpose**: Manage contextual information and environmental settings
**Responsibilities**:
- Context mode management (no_context, minimal_context, full_context, domain_context)
- Environmental variable injection and configuration
- Company standards and best practices integration
- Domain-specific knowledge base integration
- Context versioning and rollback capabilities
- Context effectiveness measurement and optimization

## Evaluation Scenarios

### Single-Turn Scenarios
1. **Code Completion** - Complete partial function implementations
2. **Bug Fix** - Identify and repair code defects
3. **Function Generation** - Create complete functions from specifications
4. **Code Translation** - Convert code between programming languages
5. **Algorithm Implementation** - Implement complex algorithms with optimization
6. **API Design** - Design and implement RESTful API endpoints
7. **System Design** - Architect system components and interactions
8. **Database Design** - Create database schemas and queries
9. **Security Implementation** - Apply security best practices and measures
10. **Performance Optimization** - Optimize code for better performance
11. **Documentation Generation** - Create comprehensive code documentation
12. **Testing Strategy** - Design and implement testing approaches
13. **Full Stack Development** - Complete end-to-end application features

### Multi-Turn Scenarios

#### Configurable Multi-Turn Framework
Each multi-turn scenario supports fully configurable turns with custom metrics:

```yaml
# Multi-Turn Scenario Configuration Template
scenario_config:
  scenario_id: "custom_multi_turn_scenario"
  scenario_type: "configurable"
  name: "Custom Multi-Turn Evaluation"
  description: "Flexible multi-turn scenario with configurable turns and metrics"
  
  # Global scenario settings
  max_turns: 5
  min_turns: 2
  conversation_timeout: 300  # seconds
  enable_context_retention: true
  
  # Turn-specific configurations
  turns:
    - turn_id: "turn_1"
      turn_type: "user_query"
      role: "user"
      prompt_template: "{{initial_prompt}}"
      expected_format: "structured_response"
      validation_rules:
        - "response_length_min: 50"
        - "response_format: json"
      evaluation_metrics:
        - "response_completeness"
        - "technical_accuracy"
        - "clarity_score"
      depends_on: []
      context_window: -1  # Use all previous context
      temperature: 0.1
      max_tokens: 1000
      stop_sequences: ["END_TURN"]
      
    - turn_id: "turn_2"
      turn_type: "assistant_response"
      role: "assistant"
      prompt_template: "Based on the previous response: {{previous_response}}, please {{follow_up_instruction}}"
      expected_format: "code_with_explanation"
      validation_rules:
        - "contains_code_block: true"
        - "explanation_present: true"
      evaluation_metrics:
        - "code_quality"
        - "explanation_clarity"
        - "improvement_over_previous"
      depends_on: ["turn_1"]
      context_window: 2  # Use last 2 turns
      temperature: 0.0
      max_tokens: 2000
      
  # Scenario-level metrics
  scenario_metrics:
    - "conversation_coherence"
    - "goal_achievement"
    - "iterative_improvement"
    - "context_retention_quality"
    - "overall_satisfaction"
    
  # Success criteria
  success_criteria:
    - "all_turns_completed: true"
    - "minimum_quality_threshold: 0.7"
    - "goal_achievement_score: 0.8"
```

#### Core Multi-Turn Scenarios

1. **Code Review Process** - Iterative code review and improvement (3-5 turns)
   ```yaml
   turns:
     - turn_1: "Initial code submission and review request"
     - turn_2: "Detailed code review with suggestions"
     - turn_3: "Code revision based on feedback"
     - turn_4: "Final review and approval/rejection"
     - turn_5: "Documentation and deployment preparation"
   metrics: ["review_thoroughness", "improvement_quality", "code_standards_compliance"]
   ```

2. **Debugging Session** - Interactive problem diagnosis and resolution
   ```yaml
   turns:
     - turn_1: "Problem description and initial analysis"
     - turn_2: "Hypothesis generation and testing strategy"
     - turn_3: "Evidence gathering and analysis"
     - turn_4: "Root cause identification"
     - turn_5: "Solution implementation and validation"
   metrics: ["diagnostic_accuracy", "solution_effectiveness", "debugging_efficiency"]
   ```

3. **Design Iteration** - Collaborative design refinement with feedback
   ```yaml
   turns:
     - turn_1: "Initial design proposal"
     - turn_2: "Stakeholder feedback and requirements clarification"
     - turn_3: "Design refinement and alternative exploration"
     - turn_4: "Final design validation and approval"
   metrics: ["design_quality", "stakeholder_satisfaction", "requirement_coverage"]
   ```

4. **Teaching Dialogue** - Instructional conversations with progressive learning
   ```yaml
   turns:
     - turn_1: "Concept introduction and explanation"
     - turn_2: "Student questions and clarification requests"
     - turn_3: "Practical examples and exercises"
     - turn_4: "Assessment and feedback"
     - turn_5: "Advanced topics and next steps"
   metrics: ["teaching_effectiveness", "student_engagement", "learning_progression"]
   ```

5. **Quantitative Trading Multi-Turn Scenarios** - Comprehensive quantitative trading evaluation scenarios

#### 5.1 量化策略开发场景

**策略构建对话流程配置**:
```python
def create_strategy_development_config() -> ScenarioConfig:
    """量化策略开发场景配置"""
    turns = [
        TurnConfig(
            turn_id="strategy_requirement_analysis",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""作为量化策略专家，请分析以下投资需求：
            投资目标: {{investment_objective}}
            风险偏好: {{risk_preference}}
            资金规模: {{capital_size}}
            投资期限: {{investment_horizon}}
            
            请提供：
            1. 策略类型建议（趋势跟踪、均值回归、套利等）
            2. 适合的资产类别和市场
            3. 预期收益风险特征
            4. 关键成功因素分析""",
            evaluation_metrics=["requirement_understanding", "strategy_recommendation_quality", "risk_assessment_accuracy"],
            temperature=0.1,
            max_tokens=2000
        ),
        TurnConfig(
            turn_id="factor_selection_validation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""基于策略需求分析 {{previous_analysis}}，请进行因子选择与验证：
            
            可用数据源: {{data_sources}}
            历史数据期间: {{historical_period}}
            
            请完成：
            1. 识别和选择相关因子（技术、基本面、宏观、另类数据）
            2. 进行单因子有效性测试
            3. 因子相关性分析
            4. 历史回测验证
            5. 因子稳定性评估""",
            depends_on=["strategy_requirement_analysis"],
            evaluation_metrics=["factor_selection_logic", "backtesting_methodology", "statistical_rigor"],
            temperature=0.0,
            max_tokens=3000
        ),
        TurnConfig(
            turn_id="model_construction_optimization",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""基于因子验证结果 {{factor_results}}，构建预测模型：
            
            请实现：
            1. 模型架构设计（线性回归、机器学习、深度学习）
            2. 特征工程和数据预处理
            3. 模型训练和验证
            4. 参数优化和正则化
            5. 模型性能评估和诊断
            
            提供完整的Python实现代码。""",
            depends_on=["factor_selection_validation"],
            evaluation_metrics=["model_sophistication", "code_quality", "performance_optimization"],
            temperature=0.0,
            max_tokens=4000
        ),
        TurnConfig(
            turn_id="risk_control_design",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""基于模型构建结果 {{model_results}}，设计风险控制机制：
            
            请设计：
            1. 仓位管理规则（Kelly公式、风险平价、等权重）
            2. 止损止盈机制
            3. 最大回撤控制
            4. 集中度风险管理
            5. 流动性风险控制
            6. 极端市场情况应对预案""",
            depends_on=["model_construction_optimization"],
            evaluation_metrics=["risk_control_comprehensiveness", "implementation_feasibility", "risk_awareness"],
            temperature=0.1,
            max_tokens=2500
        ),
        TurnConfig(
            turn_id="strategy_validation_evaluation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""进行策略的样本外验证和综合评估：
            
            验证数据: {{out_of_sample_data}}
            基准指数: {{benchmark_indices}}
            
            请完成：
            1. 样本外测试执行
            2. 与基准的比较分析
            3. 风险调整后收益评估
            4. 策略容量分析
            5. 实施可行性评估
            6. 最终策略报告和建议""",
            depends_on=["risk_control_design"],
            evaluation_metrics=["validation_rigor", "performance_analysis_depth", "practical_considerations"],
            temperature=0.1,
            max_tokens=3000
        )
    ]
    
    return ScenarioConfig(
        scenario_id="quantitative_strategy_development",
        scenario_type=ScenarioType.ITERATIVE,
        name="量化策略开发流程",
        description="完整的量化交易策略开发和验证流程",
        turns=turns,
        chat_template_required=True,
        system_message="你是一个资深的量化交易专家，具有丰富的策略开发和风险管理经验。"
    )
```

**多因子模型构建配置**:
```python
def create_multifactor_model_config() -> ScenarioConfig:
    """多因子模型构建场景配置"""
    turns = [
        TurnConfig(
            turn_id="factor_mining",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""基于市场数据进行因子挖掘：
            
            数据源: {{market_data}}
            资产池: {{asset_universe}}
            
            请完成：
            1. 技术因子构建（价格、成交量、波动率）
            2. 基本面因子提取（财务指标、估值指标）
            3. 宏观因子识别（利率、汇率、商品价格）
            4. 另类数据因子（情绪、新闻、社交媒体）
            5. 因子正交化处理""",
            evaluation_metrics=["factor_diversity", "data_processing_quality", "innovation_level"],
            temperature=0.1,
            max_tokens=2500
        ),
        TurnConfig(
            turn_id="factor_testing",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""对挖掘的因子进行单因子测试：
            
            因子列表: {{factor_list}}
            测试期间: {{test_period}}
            
            请进行：
            1. 因子收益率计算
            2. IC（信息系数）分析
            3. 因子衰减测试
            4. 分层回测验证
            5. 统计显著性检验
            6. 因子稳定性评估""",
            depends_on=["factor_mining"],
            evaluation_metrics=["testing_methodology", "statistical_rigor", "result_interpretation"],
            temperature=0.0,
            max_tokens=3000
        ),
        TurnConfig(
            turn_id="factor_synthesis",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""将有效因子合成为综合评分：
            
            有效因子: {{valid_factors}}
            合成方法选择: {{synthesis_method}}
            
            请实现：
            1. 因子权重确定（等权重、IC加权、优化权重）
            2. 因子标准化处理
            3. 综合评分计算
            4. 评分分布分析
            5. 合成效果验证
            
            提供完整实现代码。""",
            depends_on=["factor_testing"],
            evaluation_metrics=["synthesis_logic", "code_implementation", "effectiveness_validation"],
            temperature=0.0,
            max_tokens=3500
        ),
        TurnConfig(
            turn_id="model_validation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""验证多因子模型的预测能力：
            
            模型输出: {{model_scores}}
            验证数据: {{validation_data}}
            
            请完成：
            1. 预测准确性验证
            2. 分位数组合构建
            3. 多空组合表现分析
            4. 风险调整收益计算
            5. 模型稳定性测试
            6. 归因分析""",
            depends_on=["factor_synthesis"],
            evaluation_metrics=["prediction_accuracy", "portfolio_construction", "risk_analysis"],
            temperature=0.1,
            max_tokens=2800
        ),
        TurnConfig(
            turn_id="parameter_optimization",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""优化模型参数以提升策略表现：
            
            当前模型表现: {{current_performance}}
            优化目标: {{optimization_targets}}
            
            请进行：
            1. 参数敏感性分析
            2. 网格搜索优化
            3. 交叉验证防止过拟合
            4. 正则化参数调整
            5. 最优参数组合确定
            6. 优化后性能评估""",
            depends_on=["model_validation"],
            evaluation_metrics=["optimization_methodology", "overfitting_prevention", "performance_improvement"],
            temperature=0.0,
            max_tokens=2500
        )
    ]
    
    return ScenarioConfig(
        scenario_id="multifactor_model_construction",
        scenario_type=ScenarioType.ITERATIVE,
        name="多因子模型构建",
        description="系统化的多因子模型开发和优化流程",
        turns=turns,
        chat_template_required=True,
        system_message="你是一个量化研究专家，专精于多因子模型的构建和优化。"
    )
```

#### 5.2 量化研究分析场景

**市场研究对话配置**:
```python
def create_market_research_config() -> ScenarioConfig:
    """市场研究分析场景配置"""
    turns = [
        TurnConfig(
            turn_id="research_objective_setting",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""设定市场研究目标和假设：
            
            研究主题: {{research_topic}}
            市场环境: {{market_environment}}
            
            请明确：
            1. 具体研究问题和假设
            2. 研究范围和边界
            3. 预期研究成果
            4. 成功评估标准
            5. 潜在风险和限制""",
            evaluation_metrics=["objective_clarity", "hypothesis_quality", "research_design"],
            temperature=0.1,
            max_tokens=1800
        ),
        TurnConfig(
            turn_id="data_collection_analysis",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""收集和分析相关数据：
            
            研究目标: {{research_objectives}}
            可用数据源: {{data_sources}}
            
            请完成：
            1. 数据需求分析和收集计划
            2. 数据质量检查和清洗
            3. 探索性数据分析
            4. 初步统计描述
            5. 数据可视化展示""",
            depends_on=["research_objective_setting"],
            evaluation_metrics=["data_quality_assessment", "analysis_depth", "visualization_effectiveness"],
            temperature=0.0,
            max_tokens=3000
        ),
        TurnConfig(
            turn_id="statistical_testing",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""进行统计显著性检验：
            
            分析数据: {{analysis_data}}
            研究假设: {{research_hypothesis}}
            
            请执行：
            1. 选择合适的统计检验方法
            2. 检验假设条件和前提
            3. 计算检验统计量和p值
            4. 多重比较校正
            5. 效应大小评估
            6. 结果稳健性检验""",
            depends_on=["data_collection_analysis"],
            evaluation_metrics=["statistical_method_selection", "test_execution_quality", "result_interpretation"],
            temperature=0.0,
            max_tokens=2500
        ),
        TurnConfig(
            turn_id="result_interpretation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""解释分析结果并提出投资建议：
            
            统计结果: {{statistical_results}}
            市场背景: {{market_context}}
            
            请提供：
            1. 结果的经济学解释
            2. 投资含义和机会识别
            3. 策略实施建议
            4. 预期收益和风险评估
            5. 监控指标和调整触发条件""",
            depends_on=["statistical_testing"],
            evaluation_metrics=["interpretation_quality", "investment_insight", "practical_applicability"],
            temperature=0.2,
            max_tokens=2200
        ),
        TurnConfig(
            turn_id="risk_assessment",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""评估研究结论的可靠性和风险：
            
            研究结论: {{research_conclusions}}
            投资建议: {{investment_recommendations}}
            
            请分析：
            1. 结论的置信度和局限性
            2. 模型风险和参数不确定性
            3. 市场环境变化的影响
            4. 实施风险和操作难度
            5. 风险缓释措施建议""",
            depends_on=["result_interpretation"],
            evaluation_metrics=["risk_awareness", "limitation_recognition", "mitigation_quality"],
            temperature=0.1,
            max_tokens=2000
        )
    ]
    
    return ScenarioConfig(
        scenario_id="quantitative_market_research",
        scenario_type=ScenarioType.WORKFLOW,
        name="量化市场研究分析",
        description="系统化的量化市场研究和分析流程",
        turns=turns,
        chat_template_required=True,
        system_message="你是一个资深的量化研究分析师，具有深厚的统计学和金融市场知识。"
    )
```

#### 5.3 风险管理场景

**投资组合风险评估配置**:
```python
def create_portfolio_risk_assessment_config() -> ScenarioConfig:
    """投资组合风险评估场景配置"""
    turns = [
        TurnConfig(
            turn_id="portfolio_composition_analysis",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""分析当前投资组合构成和风险暴露：
            
            组合持仓: {{portfolio_holdings}}
            市场数据: {{market_data}}
            
            请分析：
            1. 资产配置结构和权重分布
            2. 行业和地区暴露度
            3. 市值和风格暴露
            4. 流动性风险评估
            5. 集中度风险识别""",
            evaluation_metrics=["composition_analysis_depth", "risk_exposure_identification", "concentration_assessment"],
            temperature=0.1,
            max_tokens=2000
        ),
        TurnConfig(
            turn_id="risk_metrics_calculation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""计算各类风险指标和进行压力测试：
            
            组合分析: {{portfolio_analysis}}
            历史数据: {{historical_data}}
            
            请计算：
            1. VaR和CVaR（参数法、历史模拟法、蒙特卡洛法）
            2. 最大回撤和回撤持续期
            3. 波动率和跟踪误差
            4. Beta和相关性分析
            5. 压力测试场景分析
            
            提供计算代码和结果。""",
            depends_on=["portfolio_composition_analysis"],
            evaluation_metrics=["risk_metric_accuracy", "methodology_appropriateness", "stress_test_comprehensiveness"],
            temperature=0.0,
            max_tokens=3500
        ),
        TurnConfig(
            turn_id="risk_attribution_analysis",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""进行风险归因和贡献度分析：
            
            风险指标: {{risk_metrics}}
            因子模型: {{factor_model}}
            
            请分析：
            1. 总风险的因子分解
            2. 个股风险贡献度
            3. 行业和风格因子贡献
            4. 特质风险vs系统风险
            5. 风险集中度分析
            6. 边际风险贡献""",
            depends_on=["risk_metrics_calculation"],
            evaluation_metrics=["attribution_accuracy", "factor_analysis_depth", "risk_decomposition_quality"],
            temperature=0.1,
            max_tokens=2800
        ),
        TurnConfig(
            turn_id="optimization_recommendations",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""提出组合优化和风险控制建议：
            
            风险归因结果: {{risk_attribution}}
            投资约束: {{investment_constraints}}
            
            请提供：
            1. 风险降低的具体措施
            2. 组合再平衡建议
            3. 对冲策略设计
            4. 仓位调整方案
            5. 风险预算重新分配
            6. 实施时间表和优先级""",
            depends_on=["risk_attribution_analysis"],
            evaluation_metrics=["recommendation_feasibility", "risk_reduction_effectiveness", "implementation_clarity"],
            temperature=0.2,
            max_tokens=2500
        )
    ]
    
    return ScenarioConfig(
        scenario_id="portfolio_risk_assessment",
        scenario_type=ScenarioType.WORKFLOW,
        name="投资组合风险评估",
        description="全面的投资组合风险测量、归因和优化流程",
        turns=turns,
        chat_template_required=True,
        system_message="你是一个专业的风险管理专家，精通各种风险测量和控制方法。"
    )
```

#### 5.4 算法交易场景

**执行算法优化配置**:
```python
def create_execution_algorithm_config() -> ScenarioConfig:
    """执行算法优化场景配置"""
    turns = [
        TurnConfig(
            turn_id="trading_requirement_analysis",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""分析交易执行需求：
            
            交易指令: {{trading_order}}
            市场条件: {{market_conditions}}
            
            请分析：
            1. 交易规模和市场容量比较
            2. 时间约束和紧急程度
            3. 市场冲击成本预估
            4. 流动性需求评估
            5. 执行风险识别""",
            evaluation_metrics=["requirement_analysis_completeness", "market_impact_assessment", "risk_identification"],
            temperature=0.1,
            max_tokens=2000
        ),
        TurnConfig(
            turn_id="algorithm_selection",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""选择和配置执行算法：
            
            交易需求: {{trading_requirements}}
            可用算法: {{available_algorithms}}
            
            请选择并配置：
            1. 算法类型选择（TWAP、VWAP、Implementation Shortfall、POV）
            2. 参数设置和调优
            3. 执行时间安排
            4. 风险控制参数
            5. 监控指标设定""",
            depends_on=["trading_requirement_analysis"],
            evaluation_metrics=["algorithm_selection_logic", "parameter_optimization", "risk_control_design"],
            temperature=0.0,
            max_tokens=2500
        ),
        TurnConfig(
            turn_id="execution_monitoring",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""实时监控交易执行情况：
            
            执行算法: {{execution_algorithm}}
            实时数据: {{real_time_data}}
            
            请监控：
            1. 执行进度和完成率
            2. 实际vs预期成本分析
            3. 市场冲击实时评估
            4. 异常情况识别和处理
            5. 动态参数调整建议""",
            depends_on=["algorithm_selection"],
            evaluation_metrics=["monitoring_effectiveness", "anomaly_detection", "adaptive_adjustment"],
            temperature=0.1,
            max_tokens=2200
        ),
        TurnConfig(
            turn_id="execution_evaluation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""评估交易执行效果：
            
            执行结果: {{execution_results}}
            基准比较: {{benchmark_comparison}}
            
            请评估：
            1. 执行成本分解（市场冲击、时机成本、手续费）
            2. 与基准算法的比较
            3. 执行质量评分
            4. 改进建议和优化方向
            5. 算法参数调优建议""",
            depends_on=["execution_monitoring"],
            evaluation_metrics=["evaluation_comprehensiveness", "cost_analysis_accuracy", "improvement_suggestions"],
            temperature=0.1,
            max_tokens=2300
        )
    ]
    
    return ScenarioConfig(
        scenario_id="execution_algorithm_optimization",
        scenario_type=ScenarioType.WORKFLOW,
        name="执行算法优化",
        description="交易执行算法的选择、配置、监控和优化流程",
        turns=turns,
        chat_template_required=True,
        system_message="你是一个专业的算法交易专家，精通各种执行算法和交易成本分析。"
    )
```

**高频交易策略配置**:
```python
def create_high_frequency_trading_config() -> ScenarioConfig:
    """高频交易策略场景配置"""
    turns = [
        TurnConfig(
            turn_id="signal_generation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""基于高频数据生成交易信号：
            
            高频数据: {{high_frequency_data}}
            市场微观结构: {{market_microstructure}}
            
            请实现：
            1. 订单簿数据分析
            2. 价格和成交量模式识别
            3. 市场失衡信号检测
            4. 短期预测模型构建
            5. 信号强度量化
            
            提供信号生成代码。""",
            evaluation_metrics=["signal_quality", "prediction_accuracy", "code_efficiency"],
            temperature=0.0,
            max_tokens=3000
        ),
        TurnConfig(
            turn_id="signal_filtering",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""过滤噪音信号，提高信号质量：
            
            原始信号: {{raw_signals}}
            历史表现: {{historical_performance}}
            
            请实现：
            1. 噪音识别和过滤算法
            2. 信号置信度评估
            3. 多信号融合机制
            4. 动态阈值调整
            5. 信号衰减检测
            
            优化后的信号生成系统。""",
            depends_on=["signal_generation"],
            evaluation_metrics=["noise_reduction_effectiveness", "signal_quality_improvement", "fusion_methodology"],
            temperature=0.0,
            max_tokens=2800
        ),
        TurnConfig(
            turn_id="order_management",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""设计智能订单管理系统：
            
            交易信号: {{filtered_signals}}
            市场流动性: {{market_liquidity}}
            
            请设计：
            1. 智能订单路由算法
            2. 订单类型选择逻辑
            3. 仓位管理和风险控制
            4. 延迟优化策略
            5. 订单执行监控
            
            完整的订单管理系统。""",
            depends_on=["signal_filtering"],
            evaluation_metrics=["order_routing_intelligence", "latency_optimization", "risk_management_integration"],
            temperature=0.0,
            max_tokens=3200
        ),
        TurnConfig(
            turn_id="latency_optimization",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""优化系统延迟，提升执行速度：
            
            当前系统架构: {{system_architecture}}
            延迟分析: {{latency_analysis}}
            
            请优化：
            1. 数据处理管道优化
            2. 算法计算效率提升
            3. 网络传输优化
            4. 硬件加速方案
            5. 系统架构改进
            
            延迟优化实施方案。""",
            depends_on=["order_management"],
            evaluation_metrics=["latency_reduction_achievement", "optimization_feasibility", "cost_benefit_analysis"],
            temperature=0.1,
            max_tokens=2500
        ),
        TurnConfig(
            turn_id="performance_monitoring",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""监控策略性能并实时调整：
            
            策略表现: {{strategy_performance}}
            市场变化: {{market_changes}}
            
            请实现：
            1. 实时性能监控指标
            2. 策略衰减检测
            3. 参数动态调整机制
            4. 风险预警系统
            5. 自动停止和重启逻辑
            
            完整的监控和调整系统。""",
            depends_on=["latency_optimization"],
            evaluation_metrics=["monitoring_comprehensiveness", "adaptive_capability", "risk_control_effectiveness"],
            temperature=0.1,
            max_tokens=2600
        )
    ]
    
    return ScenarioConfig(
        scenario_id="high_frequency_trading_strategy",
        scenario_type=ScenarioType.ITERATIVE,
        name="高频交易策略",
        description="高频交易策略的开发、优化和监控流程",
        turns=turns,
        chat_template_required=True,
        system_message="你是一个高频交易专家，精通市场微观结构和低延迟系统设计。"
    )
```

#### 5.5 量化投研场景

**基本面量化分析配置**:
```python
def create_fundamental_quant_analysis_config() -> ScenarioConfig:
    """基本面量化分析场景配置"""
    turns = [
        TurnConfig(
            turn_id="financial_data_collection",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""收集和清洗财务报表数据：
            
            目标公司: {{target_companies}}
            数据源: {{data_sources}}
            
            请完成：
            1. 财务报表数据获取和验证
            2. 数据质量检查和异常处理
            3. 会计准则统一化处理
            4. 历史数据一致性调整
            5. 缺失数据插值和估算""",
            evaluation_metrics=["data_quality_assessment", "processing_accuracy", "consistency_handling"],
            temperature=0.0,
            max_tokens=2200
        ),
        TurnConfig(
            turn_id="financial_metrics_calculation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""计算各类财务和估值指标：
            
            财务数据: {{financial_data}}
            市场数据: {{market_data}}
            
            请计算：
            1. 盈利能力指标（ROE、ROA、毛利率等）
            2. 偿债能力指标（资产负债率、流动比率等）
            3. 运营效率指标（周转率、现金循环等）
            4. 估值指标（PE、PB、EV/EBITDA等）
            5. 成长性指标（收入增长率、利润增长率等）
            
            提供计算代码和结果。""",
            depends_on=["financial_data_collection"],
            evaluation_metrics=["metric_calculation_accuracy", "indicator_comprehensiveness", "code_quality"],
            temperature=0.0,
            max_tokens=3000
        ),
        TurnConfig(
            turn_id="industry_comparison",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""进行同行业公司对比分析：
            
            目标公司指标: {{company_metrics}}
            行业数据: {{industry_data}}
            
            请分析：
            1. 行业排名和分位数位置
            2. 与行业均值的偏离程度
            3. 竞争优势和劣势识别
            4. 行业周期性影响分析
            5. 相对估值水平评估""",
            depends_on=["financial_metrics_calculation"],
            evaluation_metrics=["comparison_methodology", "competitive_analysis_depth", "relative_valuation_accuracy"],
            temperature=0.1,
            max_tokens=2500
        ),
        TurnConfig(
            turn_id="trend_analysis",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""分析财务指标的历史趋势：
            
            历史指标数据: {{historical_metrics}}
            宏观经济背景: {{macro_environment}}
            
            请分析：
            1. 关键指标的长期趋势
            2. 周期性和季节性模式
            3. 拐点识别和原因分析
            4. 趋势可持续性评估
            5. 未来趋势预测""",
            depends_on=["industry_comparison"],
            evaluation_metrics=["trend_identification_accuracy", "pattern_recognition", "predictive_insight"],
            temperature=0.1,
            max_tokens=2400
        ),
        TurnConfig(
            turn_id="investment_recommendation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""基于分析结果给出投资建议：
            
            综合分析结果: {{analysis_results}}
            投资目标: {{investment_objectives}}
            
            请提供：
            1. 投资评级和目标价格
            2. 投资逻辑和核心驱动因素
            3. 风险因素识别和评估
            4. 投资时间框架建议
            5. 组合配置建议和权重
            6. 监控指标和调整触发条件""",
            depends_on=["trend_analysis"],
            evaluation_metrics=["recommendation_logic", "risk_assessment_quality", "actionable_insights"],
            temperature=0.2,
            max_tokens=2600
        )
    ]
    
    return ScenarioConfig(
        scenario_id="fundamental_quantitative_analysis",
        scenario_type=ScenarioType.WORKFLOW,
        name="基本面量化分析",
        description="系统化的基本面量化分析和投资决策流程",
        turns=turns,
        chat_template_required=True,
        system_message="你是一个资深的基本面分析师，具有深厚的财务分析和估值建模经验。"
    )
```

**技术面量化分析配置**:
```python
def create_technical_quant_analysis_config() -> ScenarioConfig:
    """技术面量化分析场景配置"""
    turns = [
        TurnConfig(
            turn_id="technical_indicator_calculation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""计算各类技术分析指标：
            
            价格数据: {{price_data}}
            成交量数据: {{volume_data}}
            
            请计算：
            1. 趋势指标（MA、EMA、MACD、ADX）
            2. 动量指标（RSI、Stochastic、Williams %R）
            3. 波动率指标（Bollinger Bands、ATR）
            4. 成交量指标（OBV、Volume Profile、VWAP）
            5. 支撑阻力位识别
            
            提供完整的技术指标计算代码。""",
            evaluation_metrics=["indicator_accuracy", "calculation_efficiency", "indicator_diversity"],
            temperature=0.0,
            max_tokens=3200
        ),
        TurnConfig(
            turn_id="pattern_recognition",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""识别价格图表中的技术形态：
            
            技术指标: {{technical_indicators}}
            价格图表: {{price_charts}}
            
            请识别：
            1. 经典图表形态（头肩顶底、双顶底、三角形等）
            2. K线形态（锤子线、十字星、吞没形态等）
            3. 趋势线和通道
            4. 关键支撑阻力位
            5. 突破和反转信号
            
            形态识别算法和结果。""",
            depends_on=["technical_indicator_calculation"],
            evaluation_metrics=["pattern_recognition_accuracy", "signal_identification", "algorithm_sophistication"],
            temperature=0.0,
            max_tokens=2800
        ),
        TurnConfig(
            turn_id="signal_generation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""基于技术指标生成买卖信号：
            
            技术指标: {{technical_indicators}}
            识别形态: {{identified_patterns}}
            
            请生成：
            1. 多指标综合信号系统
            2. 信号强度量化评分
            3. 买卖点精确定位
            4. 止损止盈位设定
            5. 信号过滤和确认机制
            
            完整的信号生成系统。""",
            depends_on=["pattern_recognition"],
            evaluation_metrics=["signal_quality", "timing_accuracy", "risk_management_integration"],
            temperature=0.0,
            max_tokens=2600
        ),
        TurnConfig(
            turn_id="signal_validation",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""验证技术信号的历史有效性：
            
            交易信号: {{trading_signals}}
            历史数据: {{historical_data}}
            
            请验证：
            1. 信号胜率和盈亏比统计
            2. 不同市场环境下的表现
            3. 信号衰减和失效分析
            4. 最优参数组合测试
            5. 风险调整后收益评估
            
            信号有效性验证报告。""",
            depends_on=["signal_generation"],
            evaluation_metrics=["validation_rigor", "performance_analysis", "parameter_optimization"],
            temperature=0.1,
            max_tokens=2400
        ),
        TurnConfig(
            turn_id="strategy_construction",
            turn_type=TurnType.ASSISTANT_RESPONSE,
            role="assistant",
            prompt_template="""构建基于技术分析的交易策略：
            
            验证信号: {{validated_signals}}
            风险参数: {{risk_parameters}}
            
            请构建：
            1. 完整的交易策略框架
            2. 仓位管理和资金分配
            3. 风险控制和止损机制
            4. 策略组合和分散化
            5. 实盘交易实施方案
            
            可执行的交易策略系统。""",
            depends_on=["signal_validation"],
            evaluation_metrics=["strategy_completeness", "risk_management_quality", "implementation_feasibility"],
            temperature=0.1,
            max_tokens=2800
        )
    ]
    
    return ScenarioConfig(
        scenario_id="technical_quantitative_analysis",
        scenario_type=ScenarioType.ITERATIVE,
        name="技术面量化分析",
        description="基于技术分析的量化交易策略开发流程",
        turns=turns,
        chat_template_required=True,
        system_message="你是一个技术分析专家，精通各种技术指标和图表形态分析。"
    )
```

6. **Collaborative Development** - Multi-agent development workflows
7. **Requirements Refinement** - Iterative requirement clarification and specification
8. **Architecture Discussion** - System design conversations with stakeholders
9. **Performance Tuning** - Interactive optimization with measurement feedback
9. 
## Context Modes

### 1. No Context (`no_context`)
- Pure problem statement with minimal information
- Tests model's baseline capabilities without assistance
- Suitable for fundamental skill assessment

### 2. Minimal Context (`minimal_context`)
- Basic constraints and requirements provided
- Essential information for problem understanding
- Balanced evaluation of guided problem-solving

### 3. Full Context (`full_context`)
- Complete company standards and best practices
- Comprehensive documentation and examples
- Evaluates ability to work within established frameworks

### 4. Domain Context (`domain_context`)
- Domain-specific professional requirements
- Industry standards and specialized knowledge
- Tests expertise in specific technical domains

## Difficulty Levels

### Simple
- Single-skill, direct output tasks
- Clear requirements with straightforward solutions
- Basic programming concepts and patterns

### Intermediate  
- Multi-step thinking with structured output
- Integration of multiple concepts and techniques
- Moderate complexity with some ambiguity

### Complex
- Complete analysis → design → implementation workflows
- Advanced algorithms and system design
- High-level architectural thinking required

## Security and Execution Framework

### Sandbox Executor Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    Sandbox Executor Core                        │
├─────────────────────────────────────────────────────────────────┤
│  Container Management  │  Security Monitor  │  Resource Manager │
│  ┌─────────────────┐  │  ┌──────────────┐  │  ┌──────────────┐ │
│  │ Docker Engine   │  │  │ Static       │  │  │ CPU Limits   │ │
│  │ Container Pool  │  │  │ Analysis     │  │  │ Memory Caps  │ │
│  │ Lifecycle Mgmt  │  │  │ Runtime Mon  │  │  │ Time Limits  │ │
│  └─────────────────┘  │  └──────────────┘  │  └──────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Language Runtimes     │  Network Isolation │  File System     │
│  ┌─────────────────┐  │  ┌──────────────┐  │  ┌──────────────┐ │
│  │ Python 3.9+     │  │  │ No External  │  │  │ Temp FS Only │ │
│  │ Node.js 18+     │  │  │ Network      │  │  │ Read-Only    │ │
│  │ Java 11+        │  │  │ DNS Blocked  │  │  │ Auto Cleanup │ │
│  │ C++/GCC         │  │  │ Port Binding │  │  │ Size Limits  │ │
│  │ Go 1.19+        │  │  │ Disabled     │  │  │ Permission   │ │
│  │ Rust Stable     │  │  │              │  │  │ Control      │ │
│  └─────────────────┘  │  └──────────────┘  │  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Multi-Layer Security Strategy

#### Layer 1: Static Analysis (Pre-Execution)
```python
SECURITY_PATTERNS = {
    'dangerous_imports': [
        r'import\s+os', r'import\s+subprocess', r'import\s+socket',
        r'import\s+sys', r'from\s+os\s+import', r'__import__'
    ],
    'dangerous_functions': [
        r'eval\s*\(', r'exec\s*\(', r'compile\s*\(',
        r'open\s*\(', r'file\s*\(', r'input\s*\('
    ],
    'system_access': [
        r'getattr\s*\(', r'setattr\s*\(', r'delattr\s*\(',
        r'globals\s*\(', r'locals\s*\(', r'vars\s*\('
    ],
    'network_access': [
        r'urllib', r'requests', r'http', r'socket',
        r'ftplib', r'smtplib', r'telnetlib'
    ]
}
```

#### Layer 2: Container Isolation
- **Language-Specific Containers**: Optimized runtime environments
- **Resource Constraints**: CPU (0.5 cores), Memory (200MB), Disk (100MB)
- **Network Isolation**: Complete external network blocking
- **User Isolation**: Non-root user execution with minimal privileges
- **File System**: Read-only root with temporary writable directories

#### Layer 3: Runtime Monitoring
- **System Call Monitoring**: seccomp-based syscall filtering
- **Resource Usage Tracking**: Real-time CPU, memory, disk monitoring
- **Process Monitoring**: Fork bomb detection and process limits
- **Network Attempt Detection**: Socket creation and connection monitoring
- **File Access Control**: Path-based access restrictions

#### Layer 4: Violation Response
```python
VIOLATION_RESPONSES = {
    'IMMEDIATE_TERMINATION': [
        'network_access_attempt', 'file_system_escape',
        'privilege_escalation', 'fork_bomb_detection',
        'resource_limit_exceeded', 'malicious_code_execution'
    ],
    'LOGGED_WARNINGS': [
        'suspicious_import', 'resource_limit_approach',
        'unusual_system_call', 'deprecated_function_usage'
    ],
    'GRACEFUL_HANDLING': [
        'timeout_exceeded', 'memory_limit_soft',
        'compilation_error', 'runtime_exception'
    ]
}
```

### Execution Environment Specifications

#### Container Configurations
```yaml
python_container:
  image: "evaluation-engine/python:3.9-secure"
  user: "sandbox:sandbox"
  memory_limit: "200m"
  cpu_quota: 50000  # 0.5 CPU
  network_mode: "none"
  read_only: true
  security_opt: ["no-new-privileges"]
  cap_drop: ["ALL"]
  tmpfs:
    /tmp: "size=50m,noexec,nosuid,nodev"
    /var/tmp: "size=50m,noexec,nosuid,nodev"

javascript_container:
  image: "evaluation-engine/node:18-secure"
  user: "sandbox:sandbox"
  memory_limit: "200m"
  cpu_quota: 50000
  network_mode: "none"
  read_only: true
  security_opt: ["no-new-privileges"]
  cap_drop: ["ALL"]
```

#### Resource Monitoring and Limits
- **CPU Monitoring**: Real-time CPU usage tracking with hard limits
- **Memory Monitoring**: RSS, VSZ, and swap usage monitoring
- **Disk I/O Monitoring**: Read/write operation tracking and limits
- **Time Limits**: Wall clock time (30s) and CPU time (20s) limits
- **Process Limits**: Maximum process count and thread limits

### Security Audit and Compliance

#### Continuous Security Monitoring
- **Vulnerability Scanning**: Regular container image security scans
- **Dependency Auditing**: Third-party library vulnerability assessment
- **Configuration Validation**: Security configuration compliance checks
- **Incident Response**: Automated security incident detection and response

#### Compliance Framework
- **Data Privacy**: No persistent data storage, automatic cleanup
- **Access Control**: Role-based access to evaluation results
- **Audit Logging**: Comprehensive security event logging
- **Regulatory Compliance**: GDPR, SOC2, and industry standard compliance

## Evaluation Workflow

### Phase 1: System Initialization
```
Task Registry Initialization:
1. Discover and register all available tasks from task directories
2. Validate task configurations and resolve dependencies
3. Build task hierarchy and category mappings
4. Initialize task metadata and parameter schemas

Task Manager Setup:
1. Load task execution plans and scheduling configurations
2. Initialize resource pools and execution queues
3. Set up task monitoring and progress tracking systems
4. Configure parallel execution and load balancing

Data Loader Preparation:
1. Load and validate dataset schemas and integrity
2. Apply data filtering based on evaluation criteria
3. Initialize data caching and preprocessing pipelines
4. Set up incremental loading for large datasets

Model Configuration:
1. Load model-specific configuration files
2. Initialize API clients and authentication
3. Set up rate limiting and retry mechanisms
4. Configure model-specific parameters and optimizations

Context Configuration:
1. Load context templates and formatting rules
2. Initialize domain-specific knowledge bases
3. Set up context injection and variable substitution
4. Configure context mode switching capabilities
```

### Phase 2: Prompt Generation and Model Interaction
```
For each evaluation problem:

Prompt Engine Processing:
1. Select appropriate prompt template based on task type and model
2. Inject context information according to context_mode
3. Apply few-shot examples and formatting rules
4. Optimize prompt length and structure for target model
5. Generate model-specific conversation formatting

Model Query Execution:
1. Apply model-specific preprocessing and tokenization
2. Execute API calls with retry logic and error handling
3. Monitor response quality and format compliance
4. Handle streaming responses and partial completions
5. Apply post-processing and response validation

Response Processing:
1. Extract structured information from model responses
2. Validate response format and completeness
3. Clean and normalize response content
4. Store raw responses and processed outputs
```

### Phase 3: Code Execution and Validation
```
Sandbox Executor Operations:
1. Initialize language-specific execution containers
2. Perform static security analysis on generated code
3. Set up resource limits and monitoring systems
4. Execute code in isolated sandbox environment
5. Collect execution results, outputs, and performance metrics
6. Handle execution failures and security violations
7. Clean up containers and temporary resources

Execution Result Processing:
1. Parse execution outputs and error messages
2. Run test cases and validate correctness
3. Measure performance metrics (time, memory, efficiency)
4. Detect security violations and policy breaches
5. Generate execution summary and diagnostic information
```

### Phase 4: Multi-Turn Scenario Processing
```
For multi-turn scenarios:

Conversation Initialization:
1. Set up conversation context and state management
2. Initialize turn-specific configurations and parameters
3. Prepare conversation history and context tracking

Turn-by-Turn Processing:
For each conversation turn:
  1. Generate turn-specific prompts using Prompt Engine
  2. Maintain conversation context and history
  3. Process model responses and update conversation state
  4. Evaluate turn-specific metrics and quality indicators
  5. Determine conversation flow and next turn requirements
  6. Handle conversation branching and error recovery

Scenario Completion:
1. Calculate cumulative scenario metrics and scores
2. Assess conversation coherence and goal achievement
3. Evaluate iterative improvement and learning progression
4. Generate scenario-specific analysis and insights
```

### Phase 5: Metrics Calculation and Analysis
```
Metrics Engine Processing:
1. Calculate individual metric scores for each problem
2. Apply metric-specific algorithms and statistical methods
3. Handle metric calculation failures with fallback strategies
4. Aggregate metrics across problems, scenarios, and categories
5. Generate confidence intervals and statistical significance tests
6. Perform correlation analysis between different metrics

Composite Scoring:
1. Apply weighted scoring algorithms for composite metrics
2. Calculate difficulty-adjusted and context-normalized scores
3. Generate percentile rankings and comparative benchmarks
4. Create scenario-specific and language-specific scorecards
```

### Phase 6: Analysis, Visualization, and Reporting
```
Analysis Engine Operations:
1. Perform statistical analysis and trend identification
2. Generate comparative analysis across models and configurations
3. Identify performance patterns and anomalies
4. Create detailed diagnostic reports and recommendations
5. Calculate improvement suggestions and optimization opportunities

Visualization Generation:
1. Create interactive charts and performance dashboards
2. Generate comparative visualizations and benchmark plots
3. Build detailed breakdown charts for metric analysis
4. Create timeline visualizations for multi-turn scenarios
5. Generate exportable reports in multiple formats (PDF, HTML, JSON)

Result Export and Storage:
1. Structure results in standardized output formats
2. Generate machine-readable and human-readable reports
3. Store detailed logs and audit trails
4. Create shareable benchmark results and leaderboards
5. Export data for external analysis and integration
```

### Phase 7: Quality Assurance and Validation
```
Result Validation:
1. Verify metric calculation accuracy and consistency
2. Validate statistical significance and confidence levels
3. Check for data integrity and completeness
4. Perform sanity checks on extreme values and outliers
5. Validate cross-scenario and cross-model consistency

Quality Control:
1. Monitor evaluation pipeline performance and reliability
2. Detect and handle evaluation failures and errors
3. Validate sandbox security and isolation effectiveness
4. Check prompt generation quality and consistency
5. Ensure reproducibility and deterministic results
```

## Metrics Framework

### Code Quality Metrics
- **Syntax Validity**: AST parsing success rate
- **Style Compliance**: PEP8, ESLint, language-specific standards
- **Security Score**: Vulnerability detection and best practices
- **Maintainability**: Code complexity, readability, documentation

### Functional Metrics
- **Pass@K**: Test case success rates at different K values
- **Execution Success**: Code compilation and runtime success
- **Correctness**: Output matching expected results
- **Edge Case Handling**: Robustness to boundary conditions

### Multi-Turn Specific Metrics

#### Core Multi-Turn Metrics
- **Context Retention**: Ability to maintain conversation context across turns
- **Iterative Improvement**: Quality progression and learning across turns
- **Coherence**: Logical consistency and flow in multi-turn responses
- **Convergence**: Ability to reach satisfactory solutions within turn limits
- **Goal Achievement**: Success in accomplishing scenario objectives
- **Turn Efficiency**: Optimal use of available conversation turns

#### Configurable Turn-Level Metrics
```python
TURN_LEVEL_METRICS = {
    'response_quality': {
        'completeness': 'Response addresses all aspects of the prompt',
        'accuracy': 'Technical accuracy of information provided',
        'clarity': 'Clarity and understandability of response',
        'relevance': 'Relevance to the current conversation context'
    },
    'conversation_flow': {
        'context_awareness': 'Understanding of previous conversation context',
        'logical_progression': 'Logical flow from previous turns',
        'question_answering': 'Appropriate response to questions asked',
        'information_building': 'Building upon previous information'
    },
    'task_progression': {
        'goal_advancement': 'Progress toward scenario objectives',
        'problem_solving': 'Effective problem-solving approach',
        'decision_quality': 'Quality of decisions made in the turn',
        'action_appropriateness': 'Appropriateness of actions taken'
    }
}
```

#### Quantitative Trading Specific Metrics
```python
QUANTITATIVE_TRADING_METRICS = {
    'market_analysis': {
        'technical_analysis_quality': 'Accuracy and depth of technical analysis',
        'fundamental_analysis_depth': 'Quality of fundamental market analysis',
        'risk_factor_identification': 'Identification of relevant risk factors',
        'market_timing_accuracy': 'Accuracy of market timing predictions',
        'correlation_analysis': 'Understanding of asset correlations',
        'volatility_assessment': 'Accuracy of volatility predictions'
    },
    'strategy_development': {
        'strategy_completeness': 'Completeness of trading strategy specification',
        'entry_exit_clarity': 'Clarity of entry and exit criteria',
        'position_sizing_logic': 'Soundness of position sizing methodology',
        'risk_management_robustness': 'Robustness of risk management rules',
        'performance_expectations': 'Realism of performance expectations',
        'market_regime_adaptation': 'Ability to adapt to different market conditions'
    },
    'implementation_quality': {
        'code_correctness': 'Correctness of trading algorithm implementation',
        'backtesting_accuracy': 'Accuracy of backtesting methodology',
        'performance_calculation': 'Correctness of performance metric calculations',
        'risk_metric_computation': 'Accuracy of risk metric calculations',
        'execution_efficiency': 'Efficiency of order execution logic',
        'error_handling': 'Quality of error handling and edge cases'
    },
    'risk_management': {
        'var_calculation_accuracy': 'Accuracy of Value at Risk calculations',
        'stress_testing_comprehensiveness': 'Comprehensiveness of stress testing',
        'drawdown_analysis_depth': 'Depth of drawdown analysis',
        'correlation_risk_assessment': 'Assessment of correlation risks',
        'liquidity_risk_evaluation': 'Evaluation of liquidity risks',
        'model_risk_awareness': 'Awareness of model and parameter risks'
    },
    'execution_planning': {
        'market_impact_consideration': 'Consideration of market impact costs',
        'execution_timing_strategy': 'Quality of execution timing strategy',
        'slippage_estimation': 'Accuracy of slippage cost estimation',
        'monitoring_protocol_completeness': 'Completeness of monitoring protocols',
        'emergency_procedure_quality': 'Quality of emergency stop procedures',
        'regulatory_compliance_awareness': 'Awareness of regulatory requirements'
    },
    'financial_performance': {
        'sharpe_ratio_optimization': 'Optimization for risk-adjusted returns',
        'maximum_drawdown_control': 'Control of maximum drawdown levels',
        'return_consistency': 'Consistency of returns over time',
        'benchmark_outperformance': 'Ability to outperform relevant benchmarks',
        'transaction_cost_efficiency': 'Efficiency in managing transaction costs',
        'capital_utilization': 'Efficient utilization of available capital'
    }
}
```

#### Scenario-Specific Composite Metrics
```python
COMPOSITE_METRICS = {
    'quantitative_trading_overall': {
        'weights': {
            'market_analysis': 0.20,
            'strategy_development': 0.25,
            'implementation_quality': 0.20,
            'risk_management': 0.25,
            'execution_planning': 0.10
        },
        'minimum_thresholds': {
            'market_analysis': 0.6,
            'risk_management': 0.7,
            'implementation_quality': 0.65
        }
    },
    'code_review_overall': {
        'weights': {
            'review_thoroughness': 0.30,
            'improvement_suggestions': 0.25,
            'code_quality_assessment': 0.25,
            'communication_clarity': 0.20
        }
    },
    'teaching_dialogue_overall': {
        'weights': {
            'concept_explanation': 0.25,
            'student_engagement': 0.20,
            'learning_assessment': 0.25,
            'adaptive_teaching': 0.30
        }
    }
}
```

### Composite Metrics
- **Overall Quality Score**: Weighted combination of all metrics
- **Scenario-Specific Score**: Tailored scoring for each scenario type
- **Difficulty-Adjusted Score**: Performance relative to problem complexity
- **Language-Specific Score**: Performance within programming language domains

## Output Format

### Structured Results
```json
{
  "evaluation_id": "unique_evaluation_identifier",
  "timestamp": "2024-01-01T00:00:00Z",
  "model_info": {
    "name": "model_name",
    "version": "model_version",
    "configuration": {...}
  },
  "task_summary": {
    "total_problems": 100,
    "completed_problems": 98,
    "success_rate": 0.92,
    "average_execution_time": 2.3
  },
  "metrics": {
    "code_quality": {
      "syntax_validity": 0.95,
      "style_compliance": 0.87,
      "security_score": 0.91,
      "maintainability": 0.83
    },
    "functional": {
      "pass_at_1": 0.78,
      "pass_at_5": 0.89,
      "execution_success": 0.94,
      "correctness": 0.82
    },
    "composite": {
      "overall_score": 0.85,
      "difficulty_adjusted": 0.88,
      "language_weighted": 0.86
    }
  },
  "analysis": {
    "strengths": ["Strong syntax understanding", "Good error handling"],
    "weaknesses": ["Complex algorithm implementation", "Edge case handling"],
    "recommendations": ["Focus on algorithmic thinking", "Improve test coverage"]
  },
  "detailed_results": [...]
}
```

## Usage Instructions

### Basic Evaluation Commands

#### Single-Turn Scenario Evaluation
```bash
# Code completion with comprehensive metrics
lm_eval --model openai-chat \
    --model_args model=gpt-4,temperature=0.0 \
    --tasks single_turn_scenarios_code_completion \
    --limit 50 \
    --output_path results/code_completion_evaluation.json \
    --log_samples \
    --batch_size 5

# Bug fixing with security analysis
lm_eval --model anthropic \
    --model_args model=claude-3-sonnet-20240229 \
    --tasks single_turn_scenarios_bug_fix \
    --limit 30 \
    --metadata '{"enable_security_analysis":true,"sandbox_timeout":45}' \
    --output_path results/bug_fix_evaluation.json

# Algorithm implementation with performance profiling
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus \
    --tasks single_turn_scenarios_algorithm_implementation \
    --limit 25 \
    --metadata '{"enable_profiling":true,"difficulty":"complex"}' \
    --output_path results/algorithm_evaluation.json
```

#### Multi-Turn Scenario Evaluation
```bash
# Code review process with configurable turns and custom metrics
lm_eval --model claude-code-local \
    --model_args model=claude-3-haiku-20240307 \
    --tasks multi_turn_scenarios.code_review_configurable \
    --apply_chat_template \
    --limit 15 \
    --metadata '{
        "review_depth":"comprehensive",
        "enable_suggestions":true,
        "turn_config": {
            "max_turns": 5,
            "custom_metrics": ["code_improvement_rate", "review_thoroughness", "suggestion_quality"],
            "turn_specific_config": {
                "turn_1": {"temperature": 0.0, "max_tokens": 1500},
                "turn_2": {"temperature": 0.1, "max_tokens": 2000},
                "turn_3": {"temperature": 0.0, "max_tokens": 1800}
            }
        }
    }' \
    --output_path results/code_review_evaluation.json

# Quantitative trading agent multi-turn evaluation
lm_eval --model openai-chat \
    --model_args model=gpt-4,temperature=0.1 \
    --tasks multi_turn_scenarios.quantitative_trading_agent \
    --apply_chat_template \
    --limit 8 \
    --metadata '{
        "market_data_source": "historical_sp500_2020_2023",
        "strategy_type": "momentum_mean_reversion",
        "risk_tolerance": "moderate",
        "evaluation_period": "2020-2023",
        "turn_config": {
            "max_turns": 5,
            "enable_backtesting": true,
            "custom_metrics": [
                "strategy_profitability",
                "risk_management_effectiveness", 
                "market_understanding",
                "implementation_feasibility"
            ],
            "turn_specific_config": {
                "market_analysis": {"temperature": 0.1, "max_tokens": 2000},
                "strategy_development": {"temperature": 0.0, "max_tokens": 3000},
                "backtesting_execution": {"temperature": 0.0, "max_tokens": 4000},
                "risk_assessment": {"temperature": 0.1, "max_tokens": 2500},
                "execution_planning": {"temperature": 0.0, "max_tokens": 2000}
            }
        }
    }' \
    --output_path results/quantitative_trading_evaluation.json

# Debugging session with interactive problem solving
lm_eval --model openai-chat \
    --model_args model=gpt-4,temperature=0.1 \
    --tasks multi_turn_scenarios.debug_session \
    --apply_chat_template \
    --limit 10 \
    --metadata '{"max_turns":5,"enable_step_by_step":true}' \
    --output_path results/debug_session_evaluation.json

# Teaching dialogue with configurable learning progression
lm_eval --model anthropic \
    --model_args model=claude-3-opus-20240229 \
    --tasks multi_turn_scenarios.teaching_dialogue_configurable \
    --apply_chat_template \
    --limit 12 \
    --metadata '{
        "learning_objectives":["algorithms","data_structures","complexity_analysis"],
        "assessment_mode":"continuous",
        "turn_config": {
            "max_turns": 6,
            "adaptive_difficulty": true,
            "custom_metrics": [
                "teaching_effectiveness",
                "student_engagement_simulation",
                "learning_progression",
                "concept_mastery_assessment"
            ],
            "turn_specific_config": {
                "concept_introduction": {"temperature": 0.2, "max_tokens": 1500},
                "student_interaction": {"temperature": 0.3, "max_tokens": 1000},
                "practical_examples": {"temperature": 0.1, "max_tokens": 2000},
                "assessment": {"temperature": 0.0, "max_tokens": 1200},
                "feedback_and_adjustment": {"temperature": 0.2, "max_tokens": 1500}
            }
        }
    }' \
    --output_path results/teaching_evaluation.json

# Financial risk management dialogue with configurable risk scenarios
lm_eval --model dashscope \
    --model_args model=qwen-max \
    --tasks multi_turn_scenarios.financial_risk_management \
    --apply_chat_template \
    --limit 10 \
    --metadata '{
        "risk_scenarios": ["market_crash", "interest_rate_shock", "liquidity_crisis"],
        "portfolio_type": "diversified_equity",
        "risk_tolerance": "conservative",
        "turn_config": {
            "max_turns": 4,
            "scenario_adaptation": true,
            "custom_metrics": [
                "risk_identification_accuracy",
                "mitigation_strategy_effectiveness",
                "regulatory_compliance_awareness",
                "stress_testing_quality"
            ],
            "turn_specific_config": {
                "risk_assessment": {"temperature": 0.0, "max_tokens": 2500},
                "scenario_analysis": {"temperature": 0.1, "max_tokens": 3000},
                "mitigation_planning": {"temperature": 0.0, "max_tokens": 2000},
                "implementation_strategy": {"temperature": 0.0, "max_tokens": 1800}
            }
        }
    }' \
    --output_path results/risk_management_evaluation.json
```

### Advanced Configuration Examples

#### Context-Specific Evaluation
```bash
# Full context evaluation with company standards
lm_eval --model dashscope \
    --model_args model=qwen-max,temperature=0.0 \
    --tasks single_turn_scenarios_system_design \
    --metadata '{
        "context_mode":"full_context",
        "difficulty":"complex",
        "company_standards":"enterprise",
        "include_best_practices":true,
        "enable_architecture_validation":true
    }' \
    --limit 20 \
    --output_path results/system_design_full_context.json

# Domain-specific evaluation with specialized knowledge
lm_eval --model claude-code-local \
    --model_args model=claude-3-sonnet-20240229 \
    --tasks single_turn_scenarios_security \
    --metadata '{
        "context_mode":"domain_context",
        "security_domain":"web_application",
        "compliance_standards":["OWASP","SOC2"],
        "threat_modeling":true
    }' \
    --limit 15 \
    --output_path results/security_domain_evaluation.json

# Minimal context baseline evaluation
lm_eval --model openai-chat \
    --model_args model=gpt-3.5-turbo \
    --tasks single_turn_scenarios_function_generation \
    --metadata '{
        "context_mode":"minimal_context",
        "difficulty":"intermediate",
        "language":"python",
        "enable_type_hints":true
    }' \
    --limit 40 \
    --output_path results/minimal_context_baseline.json
```

#### Multi-Language and Cross-Platform Evaluation
```bash
# Cross-language code translation evaluation
lm_eval --model dashscope \
    --model_args model=qwen-coder-plus \
    --tasks single_turn_scenarios_code_translation \
    --metadata '{
        "source_language":"python",
        "target_language":"java",
        "preserve_functionality":true,
        "optimize_for_target":true,
        "include_documentation":true
    }' \
    --limit 25 \
    --output_path results/python_to_java_translation.json

# Multi-language performance comparison
for lang in python javascript java cpp go rust; do
    lm_eval --model claude-code-local \
        --model_args model=claude-3-haiku-20240307 \
        --tasks single_turn_scenarios_algorithm_implementation \
        --metadata "{
            \"language\":\"$lang\",
            \"difficulty\":\"intermediate\",
            \"enable_optimization\":true,
            \"benchmark_performance\":true
        }" \
        --limit 15 \
        --output_path "results/algorithm_${lang}_evaluation.json"
done

# Full-stack development evaluation
lm_eval --model openai-chat \
    --model_args model=gpt-4 \
    --tasks single_turn_scenarios_full_stack \
    --metadata '{
        "frontend_framework":"react",
        "backend_framework":"express",
        "database":"postgresql",
        "deployment_target":"docker",
        "include_testing":true,
        "security_requirements":true
    }' \
    --limit 10 \
    --output_path results/full_stack_evaluation.json
```

#### Comprehensive Suite Evaluation
```bash
# Complete evaluation suite with all scenarios
lm_eval --model anthropic \
    --model_args model=claude-3-opus-20240229 \
    --tasks single_turn_scenarios_suite,multi_turn_scenarios_suite \
    --limit 100 \
    --metadata '{
        "enable_all_metrics":true,
        "include_performance_profiling":true,
        "security_analysis":true,
        "cross_scenario_comparison":true,
        "generate_detailed_report":true
    }' \
    --batch_size 3 \
    --output_path results/comprehensive_evaluation.json \
    --log_samples

# Model comparison evaluation
models=("openai-chat" "anthropic" "dashscope" "claude-code-local")
model_configs=("model=gpt-4" "model=claude-3-sonnet-20240229" "model=qwen-coder-plus" "model=claude-3-haiku-20240307")

for i in "${!models[@]}"; do
    model="${models[$i]}"
    config="${model_configs[$i]}"
    
    lm_eval --model "$model" \
        --model_args "$config,temperature=0.0" \
        --tasks single_turn_scenarios_code_completion,single_turn_scenarios_bug_fix \
        --limit 30 \
        --metadata '{
            "evaluation_id":"model_comparison_'$(date +%Y%m%d)'",
            "enable_statistical_analysis":true,
            "confidence_level":0.95
        }' \
        --output_path "results/comparison_${model}_evaluation.json"
done
```

#### Custom Multi-Turn Scenario Configuration
```bash
# Custom quantitative trading scenario with full configuration
lm_eval --model openai-chat \
    --model_args model=gpt-4,temperature=0.0 \
    --tasks multi_turn_scenarios.custom_quantitative_trading \
    --apply_chat_template \
    --limit 5 \
    --metadata '{
        "scenario_config": {
            "scenario_id": "advanced_quant_trading",
            "max_turns": 6,
            "conversation_timeout": 600,
            "enable_context_retention": true,
            "market_data": {
                "symbols": ["SPY", "QQQ", "IWM", "GLD", "TLT"],
                "timeframe": "2020-2024",
                "frequency": "daily"
            },
            "custom_turns": [
                {
                    "turn_id": "market_regime_analysis",
                    "prompt_template": "Analyze market regime for {{symbols}} from {{start_date}} to {{end_date}}. Identify: 1) Market phases 2) Volatility regimes 3) Correlation patterns 4) Risk factors",
                    "expected_format": "structured_analysis",
                    "custom_metrics": ["regime_identification_accuracy", "volatility_analysis_depth", "correlation_insights"],
                    "temperature": 0.1,
                    "max_tokens": 2500
                },
                {
                    "turn_id": "multi_asset_strategy",
                    "prompt_template": "Based on regime analysis {{previous_analysis}}, design multi-asset momentum strategy with: 1) Asset selection criteria 2) Signal generation 3) Portfolio construction 4) Rebalancing rules",
                    "expected_format": "strategy_specification",
                    "custom_metrics": ["strategy_sophistication", "multi_asset_integration", "signal_quality"],
                    "depends_on": ["market_regime_analysis"],
                    "temperature": 0.0,
                    "max_tokens": 3500
                },
                {
                    "turn_id": "risk_parity_implementation",
                    "prompt_template": "Implement risk parity overlay for strategy {{strategy_spec}}. Include: 1) Risk budgeting 2) Volatility targeting 3) Correlation adjustments 4) Dynamic hedging",
                    "expected_format": "code_with_risk_framework",
                    "custom_metrics": ["risk_parity_implementation", "volatility_targeting_accuracy", "hedging_effectiveness"],
                    "depends_on": ["multi_asset_strategy"],
                    "temperature": 0.0,
                    "max_tokens": 4000
                },
                {
                    "turn_id": "alternative_data_integration",
                    "prompt_template": "Enhance strategy with alternative data sources: {{alt_data_sources}}. Show: 1) Data preprocessing 2) Signal extraction 3) Integration methodology 4) Performance impact",
                    "expected_format": "enhanced_strategy_code",
                    "custom_metrics": ["alt_data_utilization", "signal_enhancement", "integration_quality"],
                    "depends_on": ["risk_parity_implementation"],
                    "temperature": 0.1,
                    "max_tokens": 3500
                },
                {
                    "turn_id": "regime_adaptive_execution",
                    "prompt_template": "Design regime-adaptive execution system for {{final_strategy}}. Include: 1) Regime detection 2) Execution adaptation 3) Transaction cost optimization 4) Market impact minimization",
                    "expected_format": "execution_system_design",
                    "custom_metrics": ["regime_adaptation_quality", "execution_optimization", "cost_minimization"],
                    "depends_on": ["alternative_data_integration"],
                    "temperature": 0.0,
                    "max_tokens": 3000
                }
            ],
            "scenario_metrics": [
                "overall_strategy_sophistication",
                "risk_management_comprehensiveness", 
                "implementation_feasibility",
                "performance_potential",
                "market_adaptability",
                "technology_integration"
            ],
            "success_criteria": {
                "minimum_sharpe_expectation": 1.2,
                "maximum_drawdown_limit": 0.15,
                "implementation_complexity": "advanced",
                "regulatory_compliance": true
            }
        }
    }' \
    --output_path results/advanced_quant_trading_evaluation.json \
    --log_samples \
    --verbosity DEBUG

# Custom pipeline configuration with turn-specific optimization
lm_eval --model dashscope \
    --model_args model=qwen-max,temperature=0.1,max_tokens=4000 \
    --tasks single_turn_scenarios_performance_optimization \
    --metadata '{
        "optimization_targets":["time_complexity","space_complexity","readability"],
        "profiling_enabled":true,
        "benchmark_against_baseline":true,
        "include_algorithmic_analysis":true,
        "generate_optimization_report":true,
        "custom_metrics":["big_o_analysis","code_elegance","maintainability"]
    }' \
    --limit 20 \
    --batch_size 2 \
    --output_path results/performance_optimization_evaluation.json \
    --log_samples \
    --verbosity DEBUG
```

#### Multi-Turn Scenario Template Configuration
```yaml
# Template for creating custom multi-turn scenarios
custom_scenario_template:
  scenario_id: "{{scenario_name}}"
  scenario_type: "configurable"
  name: "{{display_name}}"
  description: "{{scenario_description}}"
  
  # Global settings
  max_turns: "{{max_turns}}"
  min_turns: "{{min_turns}}"
  conversation_timeout: "{{timeout_seconds}}"
  enable_context_retention: true
  enable_turn_branching: false
  
  # Turn definitions
  turns:
    - turn_id: "{{turn_1_id}}"
      turn_type: "{{turn_type}}"  # user_query, assistant_response, system_instruction, evaluation_point
      role: "{{role}}"  # user, assistant, system, evaluator
      prompt_template: "{{prompt_with_variables}}"
      expected_format: "{{response_format}}"  # json, code, text, structured_analysis
      validation_rules:
        - "{{validation_rule_1}}"
        - "{{validation_rule_2}}"
      evaluation_metrics:
        - "{{metric_1}}"
        - "{{metric_2}}"
      depends_on: []  # List of turn_ids this turn depends on
      context_window: -1  # -1 for all context, N for last N turns
      temperature: 0.0
      max_tokens: 2000
      stop_sequences: ["{{stop_sequence}}"]
      
  # Scenario-level metrics
  scenario_metrics:
    - "{{scenario_metric_1}}"
    - "{{scenario_metric_2}}"
    
  # Success criteria
  success_criteria:
    - "{{success_criterion_1}}: {{threshold}}"
    - "{{success_criterion_2}}: {{threshold}}"
    
  # Custom configuration
  custom_config:
    domain_specific_settings: "{{domain_settings}}"
    evaluation_weights: "{{metric_weights}}"
    performance_thresholds: "{{thresholds}}"
```

## Integration Architecture

### Component Interaction Flow
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Evaluation Engine Core                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │    Task     │    │    Task     │    │   Data      │    │   Context   │  │
│  │  Registry   │◄──►│   Manager   │◄──►│   Loader    │◄──►│   Config    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                   │                   │                   │       │
│         ▼                   ▼                   ▼                   ▼       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Prompt    │    │   Model     │    │   Sandbox   │    │   Metrics   │  │
│  │   Engine    │◄──►│   Config    │◄──►│  Executor   │◄──►│   Engine    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                   │                   │                   │       │
│         ▼                   ▼                   ▼                   ▼       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │              Analysis/Visualization/Comparison Engine              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                     │                                       │
├─────────────────────────────────────┼─────────────────────────────────────┤
│                Storage Layer        │        Results & Analytics           │
├─────────────────────────────────────┼─────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  │  ┌─────────────┐  ┌─────────────┐  │
│  │   Model     │  │   Dataset   │  │  │   Results   │  │  Analytics  │  │
│  │  Configs    │  │   Storage   │  │  │   Storage   │  │  Dashboard  │  │
│  └─────────────┘  └─────────────┘  │  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────┼─────────────────────────────────────┘
                                      ▼
                            ┌─────────────────┐
                            │   API Gateway   │
                            │  (REST/GraphQL) │
                            └─────────────────┘
```

### Data Flow Architecture
```
Input Data → Data Loader → Context Injection → Prompt Engine → Model Query
     ↓              ↓              ↓              ↓              ↓
Task Config → Problem Filter → Context Template → Prompt Format → API Call
     ↓              ↓              ↓              ↓              ↓
Model Response → Response Parser → Code Extraction → Sandbox Executor → Results
     ↓              ↓              ↓              ↓              ↓
Raw Output → Structured Data → Code Validation → Safe Execution → Metrics
     ↓              ↓              ↓              ↓              ↓
Metrics Engine → Score Calculation → Analysis Engine → Visualization → Report
```

### API Interface Specifications

#### REST API Endpoints
```yaml
# Evaluation Management
POST /api/v1/evaluations
GET /api/v1/evaluations/{evaluation_id}
DELETE /api/v1/evaluations/{evaluation_id}
GET /api/v1/evaluations/{evaluation_id}/status
POST /api/v1/evaluations/{evaluation_id}/cancel

# Task Management  
GET /api/v1/tasks
GET /api/v1/tasks/{task_id}
POST /api/v1/tasks/{task_id}/validate
GET /api/v1/tasks/categories
GET /api/v1/tasks/scenarios

# Model Configuration
GET /api/v1/models
POST /api/v1/models/{model_id}/configure
GET /api/v1/models/{model_id}/status
POST /api/v1/models/{model_id}/test

# Results and Analytics
GET /api/v1/results/{evaluation_id}
GET /api/v1/results/{evaluation_id}/metrics
GET /api/v1/results/{evaluation_id}/analysis
POST /api/v1/results/{evaluation_id}/compare
GET /api/v1/analytics/dashboard
```

#### WebSocket Interface for Real-time Updates
```javascript
// Real-time evaluation progress
ws://api/evaluations/{evaluation_id}/progress

// Live metrics streaming
ws://api/evaluations/{evaluation_id}/metrics

// System health monitoring
ws://api/system/health
```

## Future Extensions: Agentic Evaluation for Multi-Agent Systems (AE4MAS)

### Multi-Agent Coordination Framework
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AE4MAS Architecture                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │        │
│  │ Coordinator │  │ Evaluator   │  │ Validator   │  │ Analyzer    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                 │                 │                 │             │
│         └─────────────────┼─────────────────┼─────────────────┘             │
│                           │                 │                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 Multi-Agent Communication Bus                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                 │                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Task        │  │ Resource    │  │ Knowledge   │  │ Consensus   │        │
│  │ Distributor │  │ Manager     │  │ Base        │  │ Engine      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Communication Protocols
- **Message Passing**: Structured inter-agent communication with protocol validation
- **Task Negotiation**: Dynamic task assignment and workload balancing
- **Conflict Resolution**: Automated conflict detection and resolution mechanisms
- **Consensus Building**: Multi-agent agreement protocols for evaluation decisions
- **Knowledge Sharing**: Distributed knowledge base with consistency management

### Agentic Capabilities Assessment
```python
AGENTIC_EVALUATION_DIMENSIONS = {
    'planning_reasoning': {
        'long_term_planning': 'Ability to create and execute multi-step plans',
        'strategic_thinking': 'High-level strategic decision making',
        'goal_decomposition': 'Breaking complex goals into manageable tasks',
        'contingency_planning': 'Handling unexpected situations and failures'
    },
    'tool_integration': {
        'api_usage': 'Effective integration with external APIs and services',
        'tool_selection': 'Choosing appropriate tools for specific tasks',
        'tool_chaining': 'Combining multiple tools for complex workflows',
        'error_handling': 'Graceful handling of tool failures and limitations'
    },
    'memory_management': {
        'persistent_memory': 'Long-term information retention and retrieval',
        'context_awareness': 'Maintaining relevant context across interactions',
        'knowledge_updating': 'Learning and updating knowledge from experience',
        'memory_optimization': 'Efficient memory usage and garbage collection'
    },
    'adaptive_behavior': {
        'learning_from_feedback': 'Improving performance based on feedback',
        'strategy_adaptation': 'Modifying approaches based on results',
        'environment_adaptation': 'Adjusting to changing conditions',
        'meta_learning': 'Learning how to learn more effectively'
    }
}
```

### Multi-Agent Evaluation Scenarios
1. **Collaborative Code Development**: Multiple agents working on different components
2. **Distributed Problem Solving**: Agents specializing in different problem domains
3. **Peer Review Systems**: Agents reviewing and improving each other's work
4. **Knowledge Discovery**: Agents collaborating to discover new insights
5. **System Maintenance**: Agents coordinating to maintain complex systems
6. **Crisis Response**: Agents working together to handle emergency situations

### System-Level Evaluation Metrics
```python
SYSTEM_LEVEL_METRICS = {
    'emergent_behaviors': {
        'collective_intelligence': 'System performance exceeding individual capabilities',
        'self_organization': 'Spontaneous organization without central control',
        'adaptive_specialization': 'Agents developing specialized roles dynamically',
        'swarm_intelligence': 'Collective problem-solving capabilities'
    },
    'scalability_metrics': {
        'agent_scaling': 'Performance with increasing number of agents',
        'task_complexity_scaling': 'Handling increasingly complex tasks',
        'resource_efficiency': 'Optimal resource utilization across agents',
        'communication_overhead': 'Communication costs vs. performance benefits'
    },
    'robustness_evaluation': {
        'fault_tolerance': 'System resilience to individual agent failures',
        'graceful_degradation': 'Performance degradation under stress',
        'recovery_capabilities': 'System recovery from failures',
        'adversarial_robustness': 'Resistance to malicious inputs or agents'
    },
    'efficiency_optimization': {
        'resource_utilization': 'Optimal use of computational resources',
        'task_completion_time': 'Speed of collaborative task completion',
        'communication_efficiency': 'Minimizing unnecessary communication',
        'energy_efficiency': 'Power consumption optimization'
    }
}
```

### Implementation Roadmap
```
Phase 1: Foundation (Q1-Q2 2024)
- Implement basic multi-agent communication framework
- Develop agent coordination protocols
- Create simple collaborative evaluation scenarios
- Establish baseline metrics for multi-agent performance

Phase 2: Advanced Capabilities (Q3-Q4 2024)
- Implement complex multi-agent scenarios
- Develop emergent behavior detection systems
- Create adaptive learning mechanisms
- Establish comprehensive evaluation metrics

Phase 3: Production Deployment (Q1-Q2 2025)
- Scale to large multi-agent systems
- Implement real-world application scenarios
- Develop automated optimization systems
- Create comprehensive benchmarking suite

Phase 4: Research Integration (Q3-Q4 2025)
- Integrate cutting-edge research findings
- Develop novel evaluation methodologies
- Create open-source research platform
- Establish industry standards and best practices
```

This comprehensive evaluation engine provides a unified, extensible framework for assessing AI systems across single-turn tasks, multi-turn interactions, and future multi-agent scenarios. The architecture ensures thorough evaluation of modern language models while providing a foundation for next-generation agentic AI systems.