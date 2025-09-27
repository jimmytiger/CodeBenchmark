# Evaluation Engine 配置实现方式详解

## 🎯 概述

Evaluation Engine中的task和metrics配置采用了**混合配置方式**，结合了文件配置、代码配置和API动态配置三种方式，以提供最大的灵活性和可扩展性。

## 📁 配置文件存放位置

### 1. Task配置文件位置

#### 主要任务配置目录
```
lm_eval/tasks/
├── single_turn_scenarios/          # 单轮场景任务
│   ├── function_generation.yaml    # 函数生成任务配置
│   ├── code_completion.yaml        # 代码补全任务配置
│   ├── bug_fix.yaml                # Bug修复任务配置
│   ├── context_configs.json        # 上下文配置
│   └── problems.jsonl              # 数据集文件
├── multi_turn_scenarios/           # 多轮场景任务
│   ├── debugging_session/          # 调试会话场景
│   ├── code_review_process/        # 代码审查场景
│   └── collaborative_development/  # 协作开发场景
├── multi_turn_coding/              # 多轮编程任务
│   ├── multi_turn_coding.yaml      # 主配置文件
│   ├── multi_turn_config.json      # 运行时配置
│   └── problems.jsonl              # 数据集文件
└── python_coding/                  # Python编程任务
    ├── function_generation.yaml    # 函数生成配置
    ├── code_completion.yaml        # 代码补全配置
    └── problems.jsonl              # 数据集文件
```

#### Evaluation Engine扩展配置
```
evaluation_engine/
├── core/
│   ├── task_registration.py        # 任务注册系统
│   ├── metrics_engine.py           # 指标引擎
│   ├── extended_tasks.py           # 扩展任务类
│   └── advanced_model_config.py    # 高级模型配置
├── api/
│   └── models.py                   # API数据模型
└── docs/
    └── config_templates.json       # 配置模板（自动生成）
```

#### 动态配置存储
```
tasks/custom/                       # API创建的自定义任务
├── custom_task_1.json
├── custom_task_2.json
└── ...

security/                          # 安全配置
├── alerts/
└── vuln_db.json

results/                           # 结果和配置缓存
├── validation_*.json
└── samples_*.jsonl
```

### 2. Metrics配置位置

#### 内置指标配置
```python
# evaluation_engine/core/metrics_engine.py
class MetricsEngine:
    def _initialize_calculators(self) -> Dict[str, Callable]:
        return {
            # 标准NLP指标
            'bleu': self._calculate_bleu,
            'rouge_1': self._calculate_rouge_1,
            'rouge_2': self._calculate_rouge_2,
            'rouge_l': self._calculate_rouge_l,
            'meteor': self._calculate_meteor,
            'exact_match': self._calculate_exact_match,
            
            # 代码质量指标
            'syntax_valid': self._calculate_syntax_validity,
            'cyclomatic_complexity': self._calculate_cyclomatic_complexity,
            'security_score': self._calculate_security_score,
            
            # 功能指标
            'pass_at_1': self._calculate_pass_at_k,
            'pass_at_5': self._calculate_pass_at_k,
            'execution_success': self._calculate_execution_success,
            
            # 多轮指标
            'context_retention': self._calculate_context_retention,
            'conversation_coherence': self._calculate_conversation_coherence,
        }
```

#### 任务特定指标配置
```yaml
# lm_eval/tasks/single_turn_scenarios/function_generation.yaml
metric_list:
  - metric: exact_match
    aggregation: mean
    higher_is_better: true
  - metric: !function metrics.syntax_validity
    aggregation: mean
    higher_is_better: true
  - metric: !function metrics.code_quality_score
    aggregation: mean
    higher_is_better: true
    weight: 0.3
```

## ⚙️ 配置实现方式详解

### 1. YAML文件配置（主要方式）

#### 基础任务配置结构
```yaml
# 任务基本信息
task: single_turn_scenarios_function_generation
dataset_kwargs:
  metadata:
    scenario: "function_generation"

# 数据加载
custom_dataset: !function utils.load_dataset
test_split: test

# 文档处理
process_docs: !function utils.process_docs
doc_to_text: !function utils.doc_to_text
doc_to_target: !function utils.doc_to_target

# 输出类型
output_type: generate_until

# 指标配置
metric_list:
  - metric: exact_match
    aggregation: mean
    higher_is_better: true
  - metric: !function metrics.syntax_validity
    aggregation: mean
    higher_is_better: true

# 生成参数
generation_kwargs:
  temperature: 0.0
  max_gen_toks: 512
  until: []
  do_sample: false

# 过滤器
filter_list:
  - name: "extract_code"
    filter:
      - function: "custom"
        filter_fn: !function utils.extract_code_response

# 元数据
metadata:
  version: 1.0
  scenario: "function_generation"
  description: "Function implementation tasks"
```

#### 高级配置示例
```yaml
# 多轮任务配置
task: multi_turn_scenarios_debugging_session
scenario_config:
  scenario_type: "multi_turn"
  max_turns: 5
  conversation_timeout: 300
  enable_context_retention: true
  
  turns:
    - turn_id: "initial_problem"
      role: "user"
      template: "I have a bug in my code: {code}\nError: {error_message}"
      expected_format: "analysis"
      
    - turn_id: "diagnosis"
      role: "assistant"
      template: "Let me analyze this issue..."
      validation_rules:
        - "must_identify_root_cause"
        - "must_suggest_solution"

# 上下文配置
context_config:
  context_mode: "domain_context"
  context_sources:
    - type: "documentation"
      path: "docs/debugging_guide.md"
      weight: 0.4
    - type: "best_practices"
      path: "standards/debugging_practices.md"
      weight: 0.6

# 安全配置
security_config:
  enable_code_execution: false
  sandbox_environment: "docker"
  allowed_imports: ["os", "sys", "json"]
  resource_limits:
    max_execution_time: 10
    max_memory_mb: 256
```

### 2. JSON配置文件

#### 上下文配置
```json
// lm_eval/tasks/single_turn_scenarios/context_configs.json
{
  "no_context": {
    "template": "{{prompt}}",
    "description": "Pure problem with no additional context"
  },
  "minimal_context": {
    "template": "{{prompt}}\n\nRequirements:\n{{requirements}}",
    "description": "Basic constraints and requirements"
  },
  "full_context": {
    "template": "Company Standards:\n{{company_standards}}\n\nProblem:\n{{prompt}}\n\nBest Practices:\n{{best_practices}}",
    "description": "Complete company standards and best practices"
  },
  "domain_context": {
    "template": "Domain: {{domain}}\n\nSpecialist Requirements:\n{{domain_requirements}}\n\nProblem:\n{{prompt}}",
    "description": "Domain-specific professional requirements"
  }
}
```

#### 运行时配置
```json
// lm_eval/tasks/multi_turn_coding/multi_turn_config.json
{
  "model": "claude-3-haiku-20240307",
  "debug": false,
  "allowed_tools": ["Bash", "Python", "FileEditor"],
  "cwd": "./output",
  "max_problems": 5,
  "timeout_per_phase": 300,
  "cleanup_between_runs": true,
  "metrics_config": {
    "enable_code_execution": true,
    "security_checks": true,
    "performance_analysis": false
  }
}
```

### 3. Python代码配置

#### 任务注册和配置
```python
# evaluation_engine/core/task_registration.py
@dataclass
class TaskMetadata:
    task_id: str
    name: str
    description: str
    category: str
    difficulty: str
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_time: Optional[int] = None
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"

@dataclass
class ScenarioConfig:
    scenario_id: str
    scenario_type: str
    max_turns: int
    conversation_timeout: int
    enable_context_retention: bool
    turns: List[Dict[str, Any]] = field(default_factory=list)
    scenario_metrics: List[str] = field(default_factory=list)
    success_criteria: Dict[str, float] = field(default_factory=dict)

# 注册任务
extended_registry.register_advanced_task(
    task_class=CustomTask,
    task_name="custom_python_debugging",
    metadata=TaskMetadata(
        task_id="custom_python_debugging",
        name="Python Debugging Task",
        description="Debug Python code and fix errors",
        category="single_turn",
        difficulty="advanced",
        tags=["debugging", "python", "error-fixing"]
    )
)
```

#### 指标配置
```python
# evaluation_engine/core/metrics_engine.py
class MetricsEngine:
    def register_custom_metric(self, 
                             name: str, 
                             calculator: Callable,
                             metric_type: MetricType = MetricType.CUSTOM):
        """注册自定义指标"""
        self.custom_metrics[name] = {
            'calculator': calculator,
            'metric_type': metric_type
        }
        self.metric_calculators[name] = calculator
    
    def create_composite_metric(self,
                              name: str,
                              component_metrics: List[str],
                              weights: Optional[List[float]] = None,
                              aggregation_method: str = 'weighted_average'):
        """创建复合指标"""
        self.composite_metrics[name] = {
            'components': component_metrics,
            'weights': weights or [1.0] * len(component_metrics),
            'aggregation_method': aggregation_method
        }

# 使用示例
metrics_engine = MetricsEngine()

# 注册自定义指标
def calculate_code_elegance(prediction: str, reference: str) -> float:
    # 自定义指标计算逻辑
    return 0.8

metrics_engine.register_custom_metric(
    "code_elegance", 
    calculate_code_elegance,
    MetricType.CODE_QUALITY
)

# 创建复合指标
metrics_engine.create_composite_metric(
    "overall_code_quality",
    ["syntax_valid", "code_elegance", "performance_score"],
    [0.3, 0.4, 0.3],
    "weighted_average"
)
```

### 4. API动态配置

#### 通过API创建任务配置
```python
# 通过API创建自定义任务
task_config = {
    "task_id": "api_created_task",
    "name": "API Created Task",
    "category": "single_turn",
    "difficulty": "intermediate",
    "configuration": {
        "dataset_config": {
            "dataset_path": "custom_data.jsonl",
            "preprocessing": {
                "normalize_whitespace": True,
                "validate_syntax": True
            }
        },
        "evaluation_config": {
            "metrics": ["accuracy", "quality", "performance"],
            "evaluation_criteria": {
                "accuracy": {"weight": 0.4, "threshold": 0.8},
                "quality": {"weight": 0.3, "threshold": 0.7},
                "performance": {"weight": 0.3, "threshold": 0.6}
            }
        },
        "generation_config": {
            "temperature": 0.5,
            "max_tokens": 1024,
            "stop_sequences": ["```"]
        }
    }
}

# 保存到文件
import json
with open(f"tasks/custom/{task_config['task_id']}.json", 'w') as f:
    json.dump(task_config, f, indent=2)
```

## 🔧 配置加载和处理流程

### 1. 配置加载顺序
```python
def load_task_configuration(task_name: str):
    """配置加载优先级"""
    
    # 1. 检查API动态配置
    api_config_path = f"tasks/custom/{task_name}.json"
    if Path(api_config_path).exists():
        return load_json_config(api_config_path)
    
    # 2. 检查YAML配置文件
    yaml_config_path = f"lm_eval/tasks/*/{task_name}.yaml"
    yaml_files = glob.glob(yaml_config_path)
    if yaml_files:
        return load_yaml_config(yaml_files[0])
    
    # 3. 检查代码注册的配置
    if task_name in extended_registry.task_metadata:
        return extended_registry.get_task_metadata(task_name)
    
    # 4. 使用默认配置
    return create_default_config(task_name)
```

### 2. 配置合并策略
```python
def merge_configurations(base_config, override_config):
    """配置合并策略"""
    merged = base_config.copy()
    
    # 深度合并字典
    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_configurations(merged[key], value)
        else:
            merged[key] = value
    
    return merged

# 配置继承示例
base_config = load_yaml_config("base_task.yaml")
specific_config = load_json_config("specific_overrides.json")
final_config = merge_configurations(base_config, specific_config)
```

### 3. 配置验证
```python
def validate_task_configuration(config: Dict[str, Any]) -> List[str]:
    """配置验证"""
    errors = []
    
    # 必需字段验证
    required_fields = ["task", "output_type", "metric_list"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # 指标配置验证
    if "metric_list" in config:
        for metric in config["metric_list"]:
            if "metric" not in metric:
                errors.append("Metric configuration missing 'metric' field")
            if "aggregation" not in metric:
                errors.append("Metric configuration missing 'aggregation' field")
    
    # 生成参数验证
    if "generation_kwargs" in config:
        gen_kwargs = config["generation_kwargs"]
        if "temperature" in gen_kwargs:
            temp = gen_kwargs["temperature"]
            if not 0.0 <= temp <= 2.0:
                errors.append("Temperature must be between 0.0 and 2.0")
    
    return errors
```

## 📊 配置最佳实践

### 1. 文件组织结构
```
evaluation_engine/
├── configs/                    # 推荐的配置目录结构
│   ├── tasks/                  # 任务配置
│   │   ├── base/              # 基础配置模板
│   │   ├── single_turn/       # 单轮任务配置
│   │   ├── multi_turn/        # 多轮任务配置
│   │   └── custom/            # 自定义任务配置
│   ├── metrics/               # 指标配置
│   │   ├── standard.yaml      # 标准指标配置
│   │   ├── code_quality.yaml  # 代码质量指标
│   │   └── custom.yaml        # 自定义指标
│   ├── models/                # 模型配置
│   │   ├── claude.yaml        # Claude模型配置
│   │   ├── openai.yaml        # OpenAI模型配置
│   │   └── custom.yaml        # 自定义模型配置
│   └── environments/          # 环境配置
│       ├── development.yaml   # 开发环境
│       ├── testing.yaml       # 测试环境
│       └── production.yaml    # 生产环境
```

### 2. 配置模板化
```yaml
# configs/tasks/base/single_turn_template.yaml
task: "{{ task_name }}"
dataset_kwargs:
  metadata:
    scenario: "{{ scenario }}"

custom_dataset: !function utils.load_dataset
test_split: test
output_type: generate_until

process_docs: !function utils.process_docs
doc_to_text: !function utils.doc_to_text
doc_to_target: !function utils.doc_to_target

metric_list: "{{ metrics | default(default_metrics) }}"

generation_kwargs:
  temperature: "{{ temperature | default(0.0) }}"
  max_gen_toks: "{{ max_tokens | default(512) }}"
  until: []
  do_sample: false

metadata:
  version: "{{ version | default('1.0') }}"
  scenario: "{{ scenario }}"
  description: "{{ description }}"
```

### 3. 环境特定配置
```python
# 环境配置管理
class ConfigManager:
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.base_config = self.load_base_config()
        self.env_config = self.load_environment_config(environment)
        
    def get_task_config(self, task_name: str) -> Dict[str, Any]:
        """获取任务配置，应用环境特定覆盖"""
        base_task_config = self.load_task_config(task_name)
        env_overrides = self.env_config.get("task_overrides", {}).get(task_name, {})
        
        return merge_configurations(base_task_config, env_overrides)
    
    def get_metrics_config(self) -> Dict[str, Any]:
        """获取指标配置"""
        base_metrics = self.load_metrics_config()
        env_metrics = self.env_config.get("metrics_overrides", {})
        
        return merge_configurations(base_metrics, env_metrics)

# 使用示例
config_manager = ConfigManager("production")
task_config = config_manager.get_task_config("function_generation")
metrics_config = config_manager.get_metrics_config()
```

## 🚀 配置迁移和升级

### 从文件配置迁移到API配置
```python
def migrate_yaml_to_api_config(yaml_file: str) -> Dict[str, Any]:
    """将YAML配置迁移到API格式"""
    
    with open(yaml_file, 'r') as f:
        yaml_config = yaml.safe_load(f)
    
    # 转换为API配置格式
    api_config = {
        "task_id": yaml_config["task"],
        "name": yaml_config.get("metadata", {}).get("description", yaml_config["task"]),
        "category": infer_category(yaml_config["task"]),
        "difficulty": "intermediate",  # 默认值
        "configuration": {
            "generation_config": yaml_config.get("generation_kwargs", {}),
            "evaluation_config": {
                "metrics": [m["metric"] for m in yaml_config.get("metric_list", [])],
                "evaluation_criteria": extract_criteria(yaml_config.get("metric_list", []))
            },
            "dataset_config": yaml_config.get("dataset_kwargs", {})
        }
    }
    
    return api_config

# 批量迁移
def migrate_all_yaml_configs():
    yaml_files = glob.glob("lm_eval/tasks/**/*.yaml", recursive=True)
    
    for yaml_file in yaml_files:
        try:
            api_config = migrate_yaml_to_api_config(yaml_file)
            
            # 保存为JSON配置
            output_file = f"tasks/custom/{api_config['task_id']}.json"
            with open(output_file, 'w') as f:
                json.dump(api_config, f, indent=2)
                
            print(f"✅ Migrated {yaml_file} -> {output_file}")
            
        except Exception as e:
            print(f"❌ Failed to migrate {yaml_file}: {e}")
```

## 📝 总结

Evaluation Engine的配置实现采用了**分层混合配置架构**：

1. **YAML文件配置** - 主要的任务定义方式，适合静态配置
2. **JSON文件配置** - 运行时配置和上下文配置，适合结构化数据
3. **Python代码配置** - 复杂逻辑和动态配置，适合高级功能
4. **API动态配置** - 运行时创建和修改，适合自动化和集成

这种混合方式提供了：
- **灵活性** - 支持多种配置方式
- **可扩展性** - 易于添加新的配置类型
- **向后兼容** - 保持与lm-eval的兼容性
- **动态性** - 支持运行时配置修改
- **可维护性** - 清晰的配置层次和继承关系

配置文件主要存放在：
- `lm_eval/tasks/` - lm-eval原生任务配置
- `evaluation_engine/core/` - 扩展功能配置
- `tasks/custom/` - API创建的动态配置
- `configs/` - 推荐的统一配置目录（可选）