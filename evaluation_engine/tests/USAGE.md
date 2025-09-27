# AI Evaluation Engine 完整使用指南

## 🚀 API服务器使用

### 启动API服务器

#### 方法1：真实评估服务器（推荐）
```bash
# 启动真实的API服务器，支持实际的lm-eval任务执行
python real_api_server.py
```

#### 方法2：简化测试服务器
```bash
# 启动简化版服务器，仅用于API接口测试
python simple_api_server.py
```

### API使用流程

#### 1. 健康检查
```bash
curl -X GET http://localhost:8000/health
```

#### 2. 用户登录获取访问令牌
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

#### 3. 获取可用任务和模型
```bash
# 获取任务列表
curl -X GET "http://localhost:8000/tasks?limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 获取模型列表
curl -X GET http://localhost:8000/models \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 4. 创建并执行lm-eval任务
```bash
curl -X POST http://localhost:8000/evaluations \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "dummy",
    "task_ids": ["single_turn_scenarios_function_generation"],
    "configuration": {
      "limit": 3,
      "temperature": 0.7
    },
    "metadata": {
      "experiment_name": "api_demo"
    }
  }'
```

#### 5. 监控评估进度
```bash
curl -X GET http://localhost:8000/evaluations/EVALUATION_ID \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 6. 获取评估结果
```bash
curl -X GET "http://localhost:8000/results/EVALUATION_ID?include_details=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 自动化测试脚本

#### Python API客户端测试
```bash
# 运行完整的API功能测试
python test_real_lm_eval.py
```

#### Bash脚本测试
```bash
# 运行curl命令测试
chmod +x curl_test_examples.sh
./curl_test_examples.sh
```

### 可用的真实任务

API服务器支持以下真实的lm-eval任务：
- `single_turn_scenarios_function_generation` - 函数生成
- `single_turn_scenarios_code_completion` - 代码补全
- `single_turn_scenarios_bug_fix` - 错误修复
- `single_turn_scenarios_algorithm_implementation` - 算法实现
- `single_turn_scenarios_api_design` - API设计
- 更多任务请通过API查询

### 支持的模型

- `dummy` - 测试模型（无需API密钥）
- `claude-local` - Claude 3 Haiku（需要ANTHROPIC_API_KEY）
- `openai-completions` - GPT-3.5 Turbo（需要OPENAI_API_KEY）
- `deepseek` - DeepSeek Coder（需要DEEPSEEK_API_KEY）

## 🎯 测试套件运行

### 运行全部测试
```bash
python -m pytest evaluation_engine/tests/ -v
```

### 按目录运行

| 测试类别 | 命令 | 说明 |
|---------|------|------|
| 核心引擎 | `pytest evaluation_engine/tests/core_engines/ -v` | 分析、指标、提示、可视化引擎 |
| API集成 | `pytest evaluation_engine/tests/api_integration/ -v` | API网关和系统集成测试 |
| 安全测试 | `pytest evaluation_engine/tests/security/ -v` | 安全框架和合规测试 |
| 分析工具 | `pytest evaluation_engine/tests/analysis_tools/ -v` | 数据分析工具测试 |
| 专项功能 | `pytest evaluation_engine/tests/specialized/ -v` | 模型配置和特殊功能测试 |

## 🔍 单个测试文件

| 文件 | 快速运行 | 功能 |
|------|----------|------|
| core_engines/test_analysis_engine.py | `python evaluation_engine/tests/core_engines/test_analysis_engine.py` | 趋势分析、异常检测 |
| core_engines/test_metrics_engine.py | `python evaluation_engine/tests/core_engines/test_metrics_engine.py` | NLP指标计算 |
| api_integration/test_api_minimal.py | `python evaluation_engine/tests/api_integration/test_api_minimal.py` | API基础验证 |
| api_integration/test_integration.py | `python evaluation_engine/tests/api_integration/test_integration.py` | lm-eval集成 |
| security/test_security_framework.py | `pytest evaluation_engine/tests/security/test_security_framework.py -v` | 完整安全测试 |

## ⚡ 快速诊断

### 检查环境
```bash
python -c "import evaluation_engine; print('✅ 导入成功')"
```

### 验证依赖
```bash
pip install -r requirements_api.txt
```

### 生成报告
```bash
pytest evaluation_engine/tests/ --html=report.html
```

## 🚨 常见错误解决

| 错误 | 解决方案 |
|------|----------|
| `ModuleNotFoundError` | `export PYTHONPATH="${PYTHONPATH}:."` |
| `ImportError` | `pip install -r requirements_api.txt` |
| 端口占用 | 检查并释放相关端口 |
| 权限错误 | 确保文件读写权限 |

## 📊 测试覆盖

```bash
# 安装覆盖率工具
pip install pytest-cov

# 生成覆盖率报告
pytest evaluation_engine/tests/ --cov=evaluation_engine --cov-report=term-missing
```

## 🔧 API配置和故障排除

### 环境变量配置
```bash
# 可选：配置AI模型API密钥
export ANTHROPIC_API_KEY="your_anthropic_key"
export OPENAI_API_KEY="your_openai_key"
export DEEPSEEK_API_KEY="your_deepseek_key"
export DASHSCOPE_API_KEY="your_dashscope_key"
```

### 依赖安装
```bash
# API服务器依赖
pip install fastapi uvicorn pydantic PyJWT python-multipart

# lm-eval框架
pip install lm-eval
```

### 常见API问题

| 问题 | 解决方案 |
|------|----------|
| 端口8000被占用 | `pkill -f "python.*api_server.py"` 然后重启 |
| 401认证失败 | 检查访问令牌是否过期，重新登录 |
| 404任务不存在 | 通过`/tasks`端点查看可用任务列表 |
| 500服务器错误 | 检查服务器日志，确认lm-eval环境正常 |

### API文档访问
- 启动服务器后访问：http://localhost:8000/docs
- 交互式API测试界面，支持在线测试所有端点

### 性能优化建议
- 使用`limit`参数控制评估样本数量
- 对于大规模评估，建议使用异步方式监控进度
- 生产环境建议配置适当的速率限制和超时设置

## 📚 完整文档

详细的API使用指南请参考：
- `API_USAGE_COMPLETE_GUIDE.md` - 完整的API使用指南
- `evaluation_engine/docs/api_usage_guide.md` - API技术文档
- 在线API文档：http://localhost:8000/docs（服务器启动后）