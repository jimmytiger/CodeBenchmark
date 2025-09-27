# AI Evaluation Engine - 评估结果存储位置指南

## 📁 结果存储结构

评估结果存储在多个位置，包括内存中的临时存储和磁盘上的持久化文件。

---

## 1. 内存存储 (临时)

### 位置
- **API服务器内存**: `RealEvaluationExecutor.active_evaluations`
- **数据结构**: Python字典，以evaluation_id为键

### 存储内容
```python
{
  "eval_5a7155ca25d4": {
    "status": "completed",
    "model_id": "claude-local", 
    "task_ids": ["single_turn_scenarios_code_completion", ...],
    "configuration": {...},
    "metadata": {...},
    "user_id": "admin_001",
    "created_at": datetime.utcnow(),
    "start_time": datetime.utcnow(),
    "completed_at": datetime.utcnow(),
    "progress": 1.0,
    "results": {...},  # 解析后的结果
    "error": None
  }
}
```

### 特点
- ✅ 快速访问
- ❌ 服务器重启后丢失
- ❌ 不支持持久化

---

## 2. 磁盘存储 (持久化)

### 主要存储目录
```
results/
├── eval_YYYYMMDD_HHMMSS/           # 按时间戳命名的评估目录
│   └── {model_name}/               # 按模型名称分组
│       ├── results_timestamp.json  # 汇总结果文件
│       └── samples_*.jsonl         # 详细样本文件
└── 其他历史结果文件...
```

### 具体示例
```
results/
├── eval_20250927_062647/           # 2025年9月27日 06:26:47的评估
│   └── claude-3-haiku-20240307/    # Claude Haiku模型
│       ├── results_2025-09-26T23-27-22.602322.json
│       ├── samples_single_turn_scenarios_bug_fix_2025-09-26T23-27-22.602322.jsonl
│       ├── samples_single_turn_scenarios_code_completion_2025-09-26T23-27-22.602322.jsonl
│       └── samples_single_turn_scenarios_function_generation_2025-09-26T23-27-22.602322.jsonl
```

---

## 3. 文件类型详解

### 3.1 汇总结果文件 (`results_*.json`)

**文件名格式**: `results_YYYY-MM-DDTHH-MM-SS.ssssss.json`

**内容结构**:
```json
{
  "results": {
    "single_turn_scenarios_bug_fix": {
      "alias": "single_turn_scenarios_bug_fix",
      "exact_match,extract_code": 0.0,
      "exact_match_stderr,extract_code": 0.0,
      "syntax_validity,extract_code": 0.75,
      "syntax_validity_stderr,extract_code": 0.25,
      "runtime_correctness,extract_code": 0.0,
      "runtime_correctness_stderr,extract_code": 0.0
    }
  },
  "group_subtasks": {...},
  "configs": {...},
  "versions": {...}
}
```

**包含信息**:
- 各任务的评估指标分数
- 标准误差
- 任务配置信息
- 版本信息

### 3.2 样本详情文件 (`samples_*.jsonl`)

**文件名格式**: `samples_{task_name}_{timestamp}.jsonl`

**内容结构** (每行一个JSON对象):
```json
{
  "doc_id": 0,
  "doc": {
    "id": "st_0002",
    "title": "FizzBuzz implementation",
    "language": "python",
    "scenario": "function_generation",
    "prompt": "Write a function `fizzbuzz(n)`...",
    "reference": ["def fizzbuzz(n):..."],
    "tests": [...]
  },
  "target": "def fizzbuzz(n):...",
  "resps": [["Here's a Python function..."]],
  "filtered_resps": ["def fizzbuzz(n):..."],
  "metrics": ["exact_match", "syntax_validity"],
  "exact_match": 0.0,
  "syntax_validity": 1.0
}
```

**包含信息**:
- 原始问题和提示
- 模型生成的完整响应
- 提取的代码片段
- 各项指标的具体分数
- 参考答案和测试用例

---

## 4. 存储路径生成逻辑

### API服务器中的路径生成
```python
# 在 real_api_server.py 的 _build_lm_eval_command 方法中
output_path = f"results/eval_{evaluation['created_at'].strftime('%Y%m%d_%H%M%S')}"
cmd.extend(["--output_path", output_path])
```

### 实际生成的路径示例
- 评估创建时间: `2025-09-27T06:26:47.568426`
- 生成的目录: `results/eval_20250927_062647/`
- 模型子目录: `claude-3-haiku-20240307/`

---

## 5. 如何访问评估结果

### 5.1 通过API访问 (推荐)
```bash
# 获取评估状态
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/evaluations/eval_5a7155ca25d4

# 获取评估结果
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/results/eval_5a7155ca25d4?include_details=true
```

### 5.2 直接访问文件系统
```bash
# 查看最新的评估目录
ls -la results/ | grep eval_ | tail -5

# 查看特定评估的结果
ls -la results/eval_20250927_062647/claude-3-haiku-20240307/

# 查看汇总结果
cat results/eval_20250927_062647/claude-3-haiku-20240307/results_*.json | jq '.results'

# 查看具体样本
head -1 results/eval_20250927_062647/claude-3-haiku-20240307/samples_*.jsonl | jq '.'
```

### 5.3 编程方式访问
```python
import json
import glob
from pathlib import Path

# 查找最新的评估结果
results_dir = Path("results")
latest_eval = max(results_dir.glob("eval_*"), key=lambda x: x.name)

# 读取汇总结果
results_file = list(latest_eval.glob("*/results_*.json"))[0]
with open(results_file) as f:
    results = json.load(f)

# 读取样本详情
samples_files = list(latest_eval.glob("*/samples_*.jsonl"))
for samples_file in samples_files:
    with open(samples_file) as f:
        for line in f:
            sample = json.loads(line)
            print(f"Task: {sample['doc']['scenario']}")
            print(f"Score: {sample.get('exact_match', 'N/A')}")
```

---

## 6. 结果文件管理

### 清理旧结果
```bash
# 删除30天前的评估结果
find results/ -name "eval_*" -type d -mtime +30 -exec rm -rf {} \;

# 只保留最近10次评估
ls -t results/eval_* | tail -n +11 | xargs rm -rf
```

### 备份重要结果
```bash
# 压缩特定评估结果
tar -czf eval_20250927_062647_backup.tar.gz results/eval_20250927_062647/

# 备份到远程存储
rsync -av results/eval_20250927_062647/ user@backup-server:/backups/evaluations/
```

---

## 7. 结果数据分析

### 快速统计
```bash
# 统计各任务的平均分数
find results/ -name "results_*.json" -exec jq -r '.results | to_entries[] | "\(.key): \(.value | to_entries[] | select(.key | endswith("extract_code") and (. | endswith("_stderr") | not)) | .value)"' {} \;

# 查看语法有效性趋势
find results/ -name "results_*.json" -exec jq -r '.results | to_entries[] | select(.key | contains("syntax_validity")) | "\(.key): \(.value)"' {} \;
```

### 详细分析脚本
可以编写Python脚本来分析历史评估数据，比较不同模型的性能，追踪性能趋势等。

---

## 总结

评估结果存储在两个层面：
1. **内存中**: 用于API快速响应，临时存储
2. **磁盘上**: 用于持久化存储，详细记录

通过API访问是推荐的方式，但直接访问文件系统可以获得更详细的信息和进行批量分析。