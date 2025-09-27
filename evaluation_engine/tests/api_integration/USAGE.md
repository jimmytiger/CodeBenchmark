# API和集成测试使用指南

## 🌐 测试文件概览

| 测试文件 | 功能描述 | 主要测试内容 |
|---------|----------|-------------|
| test_api_minimal.py | API最小化测试 | 文件结构验证、基础功能、无依赖测试 |
| test_api_basic.py | API基础测试 | 基本API功能验证 |
| test_api_gateway.py | API网关测试 | 完整网关功能、路由、中间件 |
| test_integration.py | 系统集成测试 | lm-eval集成、组件导入、基础功能 |
| test_lm_eval_integration.py | lm-eval专项测试 | 任务管理、任务加载、功能验证 |

## 🚀 快速运行

### 运行所有API集成测试
```bash
python -m pytest evaluation_engine/tests/api_integration/ -v
```

### 运行单个测试文件
```bash
# API最小化测试
python evaluation_engine/tests/api_integration/test_api_minimal.py

# API基础测试
python evaluation_engine/tests/api_integration/test_api_basic.py

# API网关测试
python -m pytest evaluation_engine/tests/api_integration/test_api_gateway.py -v

# 系统集成测试
python evaluation_engine/tests/api_integration/test_integration.py

# lm-eval集成测试
python evaluation_engine/tests/api_integration/test_lm_eval_integration.py
```

## 📊 详细测试说明

### test_api_minimal.py
**最小化验证测试**:
- API文件结构完整性检查
- 基础功能可用性验证
- 无外部依赖环境测试

**运行示例**:
```bash
python evaluation_engine/tests/api_integration/test_api_minimal.py
```

### test_api_basic.py
**基础API功能测试**:
- RESTful API端点测试
- 请求响应格式验证
- 基本错误处理测试

**运行示例**:
```bash
python evaluation_engine/tests/api_integration/test_api_basic.py
```

### test_api_gateway.py
**完整网关功能测试**:
- API路由和中间件
- 认证和授权机制
- WebSocket连接测试
- 通知系统验证

**运行示例**:
```bash
python -m pytest evaluation_engine/tests/api_integration/test_api_gateway.py -v
```

### test_integration.py
**系统集成验证**:
- lm-eval库集成测试
- 核心组件导入验证
- 统一评估框架测试
- 任务注册系统验证

**运行示例**:
```bash
python evaluation_engine/tests/api_integration/test_integration.py
```

### test_lm_eval_integration.py
**lm-eval专项集成**:
- 基础lm-eval功能验证
- 任务管理器功能测试
- 任务加载和执行验证
- 评估结果处理测试

**运行示例**:
```bash
python evaluation_engine/tests/api_integration/test_lm_eval_integration.py
```

## 🔧 测试配置

### 环境要求
```bash
pip install -r requirements_api.txt
pip install lm-eval
export PYTHONPATH="${PYTHONPATH}:."
```

### 端口配置
某些API测试可能需要特定端口，确保以下端口可用：
- 8000 (API服务器)
- 8001 (WebSocket服务)

### 调试模式
```bash
python -m pytest evaluation_engine/tests/api_integration/ -v -s --tb=long
```

### 生成报告
```bash
python -m pytest evaluation_engine/tests/api_integration/ --html=api_integration_report.html
```

## 🐛 常见问题

| 问题 | 解决方案 |
|------|----------|
| 端口占用 | `lsof -ti:8000 \| xargs kill -9` |
| lm-eval导入失败 | `pip install lm-eval` |
| API服务启动失败 | 检查防火墙和端口权限 |