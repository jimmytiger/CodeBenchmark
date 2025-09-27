# 模型Token限制分析

## 🔍 各模型Token限制对比

| 模型后端 | 模型名称 | 最大输出Tokens | 当前配置 | 是否有问题 | 解决方案 |
|---------|---------|---------------|---------|-----------|----------|
| **Claude Code SDK** | claude-3-haiku-20240307 | 4,096 | 800 | ✅ 已修复 | 降低到800 tokens |
| **Claude Code SDK** | claude-3-sonnet-20240229 | 8,192 | 800 | ✅ 安全 | 可以提高到2000 |
| **Claude Code SDK** | claude-3-opus-20240229 | 8,192 | 800 | ✅ 安全 | 可以提高到2000 |
| **DeepSeek** | deepseek-v3.1 | 32,768+ | 4000 | ✅ 安全 | 足够大 |
| **OpenAI** | gpt-4-turbo | 4,096 | 2500 | ⚠️ 接近上限 | 建议2000 |
| **OpenAI** | gpt-4 | 8,192 | 2500 | ✅ 安全 | 足够 |
| **Anthropic Claude API** | claude-3-haiku-20240307 | 4,096 | 2500 | ⚠️ 接近上限 | 建议2000 |
| **Anthropic Claude API** | claude-3-sonnet-20240229 | 8,192 | 2500 | ✅ 安全 | 足够 |
| **DashScope (Qwen)** | qwen-turbo | 8,192 | 2500 | ✅ 安全 | 足够 |

## 🚨 问题分析

### 1. Claude Code SDK特殊问题
- **问题**: Claude Code SDK会对token参数进行内部转换/放大
- **表现**: `max_gen_toks: 3000` → 实际请求 `8192+`
- **解决**: 必须设置更小的值 (800-1000)

### 2. 其他模型的潜在问题
- **Haiku模型**: 所有Haiku变体都只支持4096输出tokens
- **GPT-4 Turbo**: 某些版本限制为4096 tokens
- **成本考虑**: 更长的输出会增加API成本

## 💡 推荐配置策略

### 方案1: 保守统一配置
```yaml
generation_kwargs:
  max_gen_toks: 2000  # 对所有模型都安全
```

### 方案2: 模型特定优化配置
- **Claude Code (Haiku)**: 800 tokens
- **Claude Code (Sonnet/Opus)**: 2000 tokens  
- **DeepSeek**: 4000 tokens
- **OpenAI GPT-4**: 2000 tokens
- **Anthropic API**: 2000 tokens
- **DashScope**: 2500 tokens

## 🧪 测试建议

1. **测试不同token设置**:
   ```bash
   # 测试较小设置
   lm_eval --model deepseek --model_args model=deepseek-v3.1,max_tokens=2000 --tasks multi_turn_coding_eval_deepseek --limit 1
   
   # 测试较大设置
   lm_eval --model deepseek --model_args model=deepseek-v3.1,max_tokens=4000 --tasks multi_turn_coding_eval_deepseek --limit 1
   ```

2. **观察输出质量**: token太少可能导致响应截断，影响评估质量

## ⚙️ 当前配置状态

- ✅ `multi_turn_coding.yaml` (Claude Code): 800 tokens - 安全
- ⚠️ `multi_turn_coding_universal.yaml`: 2500 tokens - 对Haiku可能过高
- ✅ `multi_turn_coding_deepseek.yaml`: 4000 tokens - DeepSeek支持良好

## 🔧 建议修复

1. **Universal配置优化**:
   ```yaml
   generation_kwargs:
     max_gen_toks: 2000  # 降低到安全值
   ```

2. **创建Haiku专用配置**:
   ```yaml
   generation_kwargs:
     max_gen_toks: 2000  # Haiku安全值
   ```