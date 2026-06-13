**[English](prompt_diversification.md) | 中文**

# 提示多样化

## 概述

提示多样化生成任务提示的多种变体，以减少智能体评估中与特定提示相关的偏差。原始的 `prompt.md` 永远不会被修改——变体单独存储。

## 架构

```
eda_agentbench/
  llm/
    base.py              # 抽象 LLM 提供者
    mock.py              # 确定性模拟提供者（无需 API）
    openai_provider.py   # 可选的 OpenAI 兼容提供者
    cache.py             # 基于文件的请求/响应缓存
  prompt/
    safety.py            # 拒绝泄露任务内部信息的提示
    rewriter.py          # 通过 LLM 重写提示并缓存
    variant_manager.py   # 管理 prompt_variants/ 目录
```

## LLM 提供者

### 模拟提供者（默认）

模拟提供者从种子生成确定性的重写结果。无需 API 访问。用于测试和开发。

```python
from eda_agentbench.llm.mock import MockLLMProvider
provider = MockLLMProvider(seed=42)
response = provider.generate("# Task\nFix the bug.")
```

### OpenAI 兼容提供者（可选）

仅在环境中设置了 `LLM_API_KEY` 时激活。

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `LLM_API_KEY` | （必需） | API 密钥 |
| `LLM_API_BASE` | `https://api.openai.com/v1` | API 基础 URL |
| `LLM_MODEL` | `gpt-4o-mini` | 模型名称 |

```bash
export LLM_API_KEY="sk-..."
python scripts/generate_prompt_variants.py
```

## 缓存

响应缓存在 `.cache/llm/`（已加入 gitignore）。缓存键是以下内容的 SHA-256 哈希值：

- 提示文本
- 系统提示
- 提供者名称
- 模型名称
- 重写策略

缓存条目中不存储任何密钥（API 密钥、token）。

## 安全检查器

安全检查器拒绝暴露以下内容的重写提示：

- 缺陷类型标签（`sensitivity_list`、`blocking_nonblocking` 等）
- 隐藏测试文件名（`tb_hidden`、`run_hidden`）
- 解答/预言文件路径
- 本地路径（`/EDA/`、`/home/`、`/tmp/`）
- 许可变量（`SNPSLMD_LICENSE_FILE`、`CDS_LIC_FILE`）
- 商业工具横幅（`VCS Release`、`Synopsys Inc`）

如果所有重写尝试都未通过安全检查，则返回原始提示不做更改。

## 使用方法

### 为样本生成变体

```bash
# 默认：每种缺陷类型 5 个 P1 任务（50）+ 每种工具 5 个 P4 任务（10）= 60 个任务
python scripts/generate_prompt_variants.py

# 试运行（显示任务但不生成）
python scripts/generate_prompt_variants.py --dry-run

# 自定义数量
python scripts/generate_prompt_variants.py --p1-count 10 --p4-count 10
```

### 生成后的目录结构

```
task_000001/
  prompt.md                    # 原始（未更改）
  prompt_variants/
    llm_v1.md                  # 重写的变体
    llm_v1_meta.json           # 变体元数据
  files/
  hidden/
  solution/
```

### 变体元数据

```json
{
  "variant_name": "llm_v1",
  "provider": "mock",
  "model": "mock-v1",
  "policy": "default",
  "safety_passed": true,
  "safety_violations": [],
  "original_length": 450,
  "variant_length": 512
}
```

## 与评估集成

使用变体而非原始提示进行评估：

```bash
# 未来：--prompt-variant 标志
eda-bench evaluate-task tasks/p1_rtl_debug/task_000001 \
    --submission solution/ \
    --prompt-variant llm_v1
```

## 设计决策

1. **原始不变**：`prompt.md` 是规范提示。变体是附加的。
2. **安全优先**：所有重写在存储为有效变体前必须通过安全检查。
3. **确定性模拟**：测试不需要 API 访问。
4. **缓存中无密钥**：缓存仅存储提示/响应文本和元数据。
5. **小样本先行**：先生成 60 个变体以验证基础设施，然后再扩展规模。
