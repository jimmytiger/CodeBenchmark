# Multi-Turn Evaluation Scenarios and Tools Integration

## Evaluation Scenarios Pool

### 1. Repository-Level Bug Fixing (最像真实研发)

**场景描述**: 读取 issue → 多文件修改 → 运行项目测试

**适用数据集**: SWE-bench (Lite/Verified/Bash-only/Multimodal)

**最小适配要求**:
- Git checkout 到指定 commit
- 自动安装项目依赖 (pip install -e ., npm install 等)
- 运行测试套件并捕获失败信息
- 将失败断言/栈摘要裁剪为下一轮反馈
- 支持多文件并发修改和版本控制

**建议样本量**: 25-50 个任务/轮

**典型执行流程**:
```python
# Turn 1: 环境初始化和问题理解
action = Action(type="FILE_READ", content="README.md")
action = Action(type="FILE_READ", content="issue_description.md")

# Turn 2-3: 代码探索和问题定位
action = Action(type="BASH_COMMAND", content="find . -name '*.py' | grep -E '(test_|_test)' | head -10")
action = Action(type="FILE_READ", content="src/main_module.py")

# Turn 4-6: 初步修复尝试
action = Action(type="CODE_EDIT", content="修复核心逻辑", parameters={"file": "src/main_module.py"})
action = Action(type="TEST_RUN", content="python -m pytest tests/test_main.py -v")

# Turn 7-10: 基于测试反馈的迭代修复
# 观察: 测试失败，获得详细错误信息和栈跟踪
action = Action(type="CODE_EDIT", content="根据测试反馈调整实现")

# Turn 11-15: 最终验证和边缘情况处理
action = Action(type="TEST_RUN", content="python -m pytest --tb=short")
```

**关键指标**:
- Resolved%: 15-30% (取决于 agent 能力)
- Avg Turns: 8-12
- Files Touched: 2-5
- Edit Churn: 50-200 lines
- Wall Time per Solved: 600-1200s

### 2. Interactive Debugging (强调执行反馈)

**场景描述**: 先失败 → 读取报错/日志 → 迭代修复

**适用数据集**: InterCode (IC-Python/IC-Bash/IC-SQL/IC-SWE)

**最小适配要求**:
- env.step(action) 适配器实现
- 收集 stdout/stderr/reward 并构造成结构化反馈
- 支持代码执行环境的状态保持
- 变量状态跟踪和调试信息提取

**建议样本量**: 50-100 个任务/轮

**典型执行流程**:
```python
# Turn 1: 初始代码执行和错误发现
action = Action(type="CODE_RUN", content="initial_buggy_code.py")
# 观察: RuntimeError, TypeError, 或逻辑错误

# Turn 2-5: 错误分析和调试
action = Action(type="CODE_EDIT", content="添加调试打印语句")
action = Action(type="CODE_RUN", content="debug_version.py")
# 观察: 变量状态，执行路径信息

# Turn 6-10: 逐步修复和验证
action = Action(type="CODE_EDIT", content="修复识别出的问题")
action = Action(type="CODE_RUN", content="test_fix.py")

# Turn 11-15: 边缘情况测试和最终优化
action = Action(type="CODE_RUN", content="comprehensive_test.py")
```

**关键指标**:
- Solved%: 40-60%
- Avg Steps: 15-25
- Recovery Rate: 70-85% (从错误中恢复的能力)
- Redundancy Rate: 20-35%

### 3. Requirement Clarification + Implementation

**场景描述**: 需求模糊 → 澄清问答 → 补齐实现与测试

**适用数据集**: ConvCodeBench (离线日志复放)

**最小适配要求**:
- 复放每轮对话反馈
- 替换"该轮 agent 输出"进行评估
- 支持多轮需求澄清对话
- 自动验证实现是否满足澄清后的需求

**建议样本量**: 100-200 个任务/轮

**典型执行流程**:
```python
# Turn 1-5: 需求澄清阶段
action = Action(type="QUERY_CLARIFICATION", content="What specific data format should the function accept?")
# 观察: 用户回答和需求细化

action = Action(type="QUERY_CLARIFICATION", content="Should error handling be strict or permissive?")
# 观察: 进一步的需求澄清

# Turn 6-15: 实现阶段
action = Action(type="CODE_EDIT", content="基于澄清需求的初始实现")
action = Action(type="CODE_EDIT", content="添加测试用例")

# Turn 16-20: 验证和完善
action = Action(type="TEST_RUN", content="验证实现是否满足所有澄清的需求")
```

**关键指标**:
- Recall: 与 ConvCodeBench 原始指标对齐
- MRR: 越少回合完成越好
- Clarification Efficiency: 澄清轮数/总轮数比例

### 4. Data Science Script Development

**场景描述**: 读数据 → 编写/修复 Pandas/Numpy/可视化代码 → 比对期望输出

**自定义场景设计**:

**最小适配要求**:
- 数据文件加载和预处理
- 支持 Pandas/Numpy/Matplotlib/Seaborn 等库
- 输出结果与期望输出的自动比对
- 可视化结果的相似度评估

**建议样本量**: 30-50 个任务/轮

**典型执行流程**:
```python
# Turn 1-3: 数据探索
action = Action(type="CODE_RUN", content="""
import pandas as pd
df = pd.read_csv('data.csv')
print(df.head())
print(df.describe())
""")

# Turn 4-8: 数据分析和处理
action = Action(type="CODE_RUN", content="""
# 数据清洗和特征工程
df_clean = df.dropna()
df_clean['new_feature'] = df_clean['col1'] * df_clean['col2']
""")

# Turn 9-12: 可视化创建
action = Action(type="CODE_RUN", content="""
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))
plt.plot(df_clean['x'], df_clean['y'])
plt.savefig('output.png')
""")

# Turn 13-15: 结果验证和调优
action = Action(type="CODE_RUN", content="compare_with_expected_output()")
```

**关键指标**:
- Output Similarity: 与期望输出的相似度
- Code Quality: 代码规范性和效率
- Library Usage: 正确使用数据科学库的程度

### 5. Command Line Environment Manipulation

**场景描述**: Bash/SQL 步骤式任务 → 逐步执行与回退

**适用数据集**: InterCode-Bash, InterCode-SQL

**最小适配要求**:
- 命令执行环境的沙箱化
- 支持命令历史和状态回退
- 环境变量和文件系统状态管理
- 危险命令的安全过滤

**建议样本量**: 40-60 个任务/轮

**典型执行流程**:
```bash
# Turn 1-3: 环境设置和探索
action = Action(type="BASH_COMMAND", content="ls -la")
action = Action(type="BASH_COMMAND", content="pwd && whoami")

# Turn 4-8: 逐步任务执行
action = Action(type="BASH_COMMAND", content="mkdir project && cd project")
action = Action(type="BASH_COMMAND", content="git clone https://github.com/example/repo.git")

# Turn 9-15: 问题解决和回退处理
action = Action(type="BASH_COMMAND", content="make install")
# 如果失败，支持回退到之前的检查点
action = Action(type="ENVIRONMENT_SETUP", content="rollback_to_checkpoint")
```

**关键指标**:
- Task Completion Rate: 完整任务流程完成率
- Command Efficiency: 有效命令/总命令比例
- Rollback Success: 成功回退和恢复的比例

### 6. Cross-Language Bug Fixing

**场景描述**: 同类缺陷在 Python/Java/TS 的迁移与对齐

**适用数据集**: BugsInPy (Python), Defects4J (Java), QuixBugs (Python/Java)

**最小适配要求**:
- 多语言环境的统一接口
- 跨语言测试执行和结果标准化
- 语言特定的错误模式识别
- 修复策略的跨语言适应性评估

**建议样本量**: 20-50 个任务/轮 (每种语言)

**典型执行流程**:
```python
# Turn 1-3: 问题理解和语言选择
action = Action(type="FILE_READ", content="bug_description.md")
action = Action(type="QUERY_CLARIFICATION", content="Which language should I start with?")

# Turn 4-8: 第一种语言的修复
action = Action(type="CODE_EDIT", content="Python implementation fix")
action = Action(type="TEST_RUN", content="python -m pytest test_python.py")

# Turn 9-15: 其他语言的对应修复
action = Action(type="CODE_EDIT", content="Java implementation fix")
action = Action(type="TEST_RUN", content="mvn test -Dtest=TestJava")

# Turn 16-20: 跨语言一致性验证
action = Action(type="TEST_RUN", content="cross_language_consistency_test")
```

**关键指标**:
- Cross-Language Consistency: 跨语言修复的一致性
- Language-Specific Success Rate: 每种语言的成功率
- Transfer Learning Efficiency: 从一种语言到另一种语言的迁移效率

## 工具集成适配指南

### SWE-bench 集成

**安装和配置**:
```bash
pip install swe-bench
export SWE_BENCH_DATA_PATH="./swe_bench_data"
```

**适配器实现要点**:
```python
class SWEBenchAdapter(BenchmarkAdapter):
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        return SWEBenchEnvironment(
            repo_url=task_config["repo"],
            commit_hash=task_config["base_commit"],
            issue_description=task_config["problem_statement"],
            test_command=task_config["test_cmd"],
            timeout=1800
        )
    
    def process_feedback(self, test_output: str) -> ProcessedFeedback:
        # 裁剪长测试输出，保留关键错误信息
        # 提取失败断言和栈跟踪摘要
        # 限制反馈长度在 8000 字符以内
        pass
```

**关键适配点**:
- Git 仓库的自动 checkout 和依赖安装
- 测试失败信息的智能裁剪和摘要
- 多文件修改的版本控制和回滚
- 长时间运行任务的超时处理

### InterCode 集成

**安装和配置**:
```bash
pip install intercode-bench
intercode-setup --env python bash sql swe
```

**适配器实现要点**:
```python
class InterCodeAdapter(BenchmarkAdapter):
    def __init__(self, subtask: str):
        self.subtask = subtask
        self.ic_env = InterCodeEnv(subtask)
    
    def step(self, action: Action) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        # 将 Action 转换为 InterCode 格式
        ic_action = self.convert_action(action)
        
        # 执行 InterCode step
        obs, reward, done, info = self.ic_env.step(ic_action)
        
        # 转换回统一格式
        return self.convert_observation(obs), reward, done, info
```

**关键适配点**:
- env.step() 接口的统一封装
- stdout/stderr 的结构化收集
- 执行环境状态的保持和恢复
- 不同子任务 (Python/Bash/SQL) 的统一处理

### ConvCodeBench 集成

**数据准备**:
```bash
wget https://github.com/ConvCodeBench/dataset/releases/latest/download/conv_code_bench.tar.gz
tar -xzf conv_code_bench.tar.gz
```

**适配器实现要点**:
```python
class ConvCodeBenchAdapter(BenchmarkAdapter):
    def __init__(self, dataset_path: str):
        self.conversations = self.load_conversations(dataset_path)
    
    def replay_conversation(self, conv_id: str, agent_responses: List[str]) -> float:
        # 复放对话，替换 agent 输出
        # 计算与原始对话的相似度
        # 评估最终实现的正确性
        pass
```

**关键适配点**:
- 离线对话日志的解析和复放
- Agent 输出替换的精确定位
- 对话质量和实现正确性的双重评估
- 大规模对话数据的高效处理

### BugsInPy / Defects4J 集成

**BugsInPy 配置**:
```bash
git clone https://github.com/soarsmu/BugsInPy.git
cd BugsInPy
python -m pip install -r requirements.txt
```

**Defects4J 配置**:
```bash
git clone https://github.com/rjust/defects4j.git
cd defects4j
./init.sh
export PATH=$PATH:$(pwd)/framework/bin
```

**适配器实现要点**:
```python
class BugsInPyAdapter(BenchmarkAdapter):
    def create_environment(self, task_config: Dict[str, Any]) -> UnifiedEnv:
        return BugFixEnvironment(
            project=task_config["project"],
            bug_id=task_config["bug_id"],
            language="python"
        )
    
    def run_tests(self, project_path: str) -> TestResult:
        # 运行失败测试
        # 捕获异常和 diff 信息
        # 构造结构化反馈
        pass
```

**关键适配点**:
- 项目特定的构建和测试命令
- 失败测试的异常信息提取
- 修复前后的 diff 分析
- 语言特定的错误模式识别

## 预定义基线配置

### 1. 回归基线 (每日/每 PR)

**配置目标**: 快速回归测试，30 分钟内完成

```yaml
name: daily_regression
benchmarks:
  - adapter: conv_code_bench
    samples: 100
    feedback_configs:
      - compile_only
      - exec_only
    max_turns: 5
    timeout: 300

metrics:
  - recall
  - mrr
  - avg_turns
  - cost_usd

alert_thresholds:
  recall_drop: 5.0  # 召回率下降超过 5% 时告警
  cost_increase: 20.0  # 成本增加超过 20% 时告警
  avg_turns_increase: 2.0  # 平均轮数增加超过 2 时告警

output:
  format: [json, csv]
  dashboard_update: true
  slack_notification: true
```

### 2. 中保真基线 (每周)

**配置目标**: 全面评估，4 小时内完成

```yaml
name: weekly_comprehensive
benchmarks:
  - adapter: intercode_python
    samples: 50
    max_turns: 15
    scenarios: [interactive_debugging, data_science_script]
  
  - adapter: intercode_bash
    samples: 50
    max_turns: 20
    scenarios: [command_line]

metrics:
  - solved_percent
  - avg_steps
  - recovery_rate
  - wall_time
  - redundancy_rate

analysis:
  trend_analysis: true
  compare_with_previous: true
  generate_detailed_report: true
  include_failure_analysis: true

output:
  format: [json, html_report]
  include_visualizations: true
  benchmark_comparison: true
```

### 3. 里程碑基线 (月度)

**配置目标**: 完整评估，24 小时内完成

```yaml
name: monthly_milestone
benchmarks:
  - adapter: swe_bench_lite
    samples: 25
    max_turns: 15
    scenarios: [repository_bug_fix]
  
  - adapter: swe_bench_verified
    samples: 25
    max_turns: 15
    scenarios: [repository_bug_fix]
  
  - adapter: bugs_in_py
    samples: 20
    max_turns: 12
    scenarios: [interactive_debugging]
  
  - adapter: defects4j
    samples: 20
    max_turns: 12
    scenarios: [cross_language_fix]

metrics:
  - resolved_percent
  - avg_turns
  - edit_churn
  - cost_per_solved
  - stability_score
  - files_touched
  - recovery_rate

analysis:
  multiple_runs: 3  # 用于稳定性计算
  statistical_significance: true
  detailed_failure_analysis: true
  cross_benchmark_comparison: true
  performance_regression_detection: true

output:
  format: [json, pdf_report, html_dashboard]
  include_executive_summary: true
  benchmark_leaderboard_update: true
  research_paper_metrics: true
```

## 统一输出格式规范

### CSV/JSON Schema

```python
@dataclass
class StandardizedOutput:
    # 基础标识
    run_id: str          # 评估运行唯一标识
    task_id: str         # 任务唯一标识
    sample_id: str       # 样本唯一标识
    benchmark: str       # 基准测试名称
    scenario: str        # 评估场景类型
    
    # 核心结果
    success: bool        # 任务是否成功完成
    turns: int          # 总轮数
    steps: int          # 总步数
    wall_time_s: float  # 墙钟时间(秒)
    
    # Token 和成本
    token_in: int       # 输入 token 数
    token_out: int      # 输出 token 数
    cost_usd: float     # 成本(美元)
    
    # 代码质量指标
    files_touched: int   # 修改文件数
    edit_added: int     # 新增行数
    edit_deleted: int   # 删除行数
    redundancy_rate: float  # 冗余操作率
    
    # 鲁棒性指标
    recovered: bool     # 是否从错误中恢复
    safety_incidents: int  # 安全事件数量
    
    # 扩展信息
    notes: str          # 备注信息
    metadata: Dict[str, Any]  # 元数据
    
    # 详细轮次信息 (可选)
    turn_details: List[TurnResult] = None
```

### 横向对比字段

为便于不同基准测试和场景的横向对比，所有输出都包含以下标准化字段：

```python
COMPARISON_FIELDS = {
    # 成功率指标 (0-100)
    "success_rate": "resolved_percent | solved_percent | recall",
    
    # 效率指标
    "efficiency_score": "1.0 / avg_turns",  # 越少轮数越高效
    "step_efficiency": "success_rate / avg_steps",
    
    # 成本效益
    "cost_effectiveness": "success_rate / cost_per_solved",
    "time_effectiveness": "success_rate / wall_time_per_solved",
    
    # 质量指标
    "code_quality": "success_rate / edit_churn",  # 成功率与修改量的比值
    "precision": "success_rate / (success_rate + false_positive_rate)",
    
    # 鲁棒性
    "robustness": "recovery_rate * (1 - safety_incidents_per_100/100)",
    
    # 综合评分 (0-100)
    "overall_score": "weighted_average(success_rate, efficiency_score, cost_effectiveness, robustness)"
}
```

这个规范确保了所有评估结果都可以进行有意义的横向对比和趋势分析。