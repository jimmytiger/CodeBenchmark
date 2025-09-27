# 安全和合规测试使用指南

## 🔒 测试文件概览

| 测试文件 | 功能描述 | 主要测试内容 |
|---------|----------|-------------|
| test_security_basic.py | 基础安全测试 | 基本安全功能验证 |
| test_security_framework.py | 完整安全框架测试 | 漏洞扫描、加密管理、审计日志、事件检测、合规管理、访问控制 |

## 🚀 快速运行

### 运行所有安全测试
```bash
python -m pytest evaluation_engine/tests/security/ -v
```

### 运行单个测试文件
```bash
# 基础安全测试
python evaluation_engine/tests/security/test_security_basic.py

# 完整安全框架测试
python -m pytest evaluation_engine/tests/security/test_security_framework.py -v
```

## 📊 详细测试说明

### test_security_basic.py
**基础安全功能测试**:
- 基本认证机制验证
- 简单权限控制测试
- 基础数据保护验证

**运行示例**:
```bash
python evaluation_engine/tests/security/test_security_basic.py
```

### test_security_framework.py
**完整安全框架测试**:

#### 🔍 漏洞扫描系统
- 代码漏洞检测
- 依赖安全扫描
- 配置安全检查
- 实时威胁监控

#### 🔐 加密管理系统
- 数据加密/解密功能
- 密钥生成和管理
- 加密算法验证
- 安全存储测试

#### 📝 审计日志系统
- 安全事件记录
- 日志完整性验证
- 访问轨迹追踪
- 合规性报告生成

#### 🚨 事件检测系统
- 异常行为检测
- 安全威胁识别
- 实时告警机制
- 事件响应流程

#### 📋 合规管理系统
- GDPR合规性检查
- 数据主体权利管理
- 隐私政策验证
- 合规报告生成

#### 🛡️ 访问控制系统
- 用户权限管理
- 角色基础访问控制
- 多因素认证
- 会话管理

**运行示例**:
```bash
python -m pytest evaluation_engine/tests/security/test_security_framework.py -v
```

## 🔧 测试配置

### 环境要求
```bash
pip install -r requirements_api.txt
pip install cryptography
pip install pytest-asyncio
export PYTHONPATH="${PYTHONPATH}:."
```

### 安全测试环境变量
```bash
export TEST_ENCRYPTION_KEY="test_key_for_security_tests"
export TEST_AUDIT_LOG_PATH="/tmp/test_audit_logs"
export TEST_SECURITY_MODE="strict"
```

### 调试模式
```bash
python -m pytest evaluation_engine/tests/security/ -v -s --tb=long
```

### 生成安全报告
```bash
python -m pytest evaluation_engine/tests/security/ --html=security_report.html --self-contained-html
```

## 🔐 安全测试最佳实践

### 测试数据安全
- 使用模拟数据，避免真实敏感信息
- 测试完成后清理临时文件
- 确保测试环境与生产环境隔离

### 权限测试
- 验证最小权限原则
- 测试权限升级和降级
- 检查未授权访问防护

### 加密测试
- 验证加密算法强度
- 测试密钥轮换机制
- 检查数据传输加密

## 🐛 常见问题

| 问题 | 解决方案 |
|------|----------|
| 加密库导入失败 | `pip install cryptography` |
| 权限不足错误 | 确保测试目录写权限 |
| 异步测试失败 | `pip install pytest-asyncio` |
| 临时文件清理失败 | 手动清理 `/tmp/test_*` 文件 |

## ⚠️ 安全注意事项

1. **测试环境隔离**: 确保安全测试在隔离环境中运行
2. **敏感数据保护**: 不在测试中使用真实的密钥或敏感数据
3. **日志安全**: 测试日志不应包含敏感信息
4. **清理机制**: 测试完成后及时清理临时文件和测试数据