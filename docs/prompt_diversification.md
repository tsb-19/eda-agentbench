# Prompt Diversification

## Overview

Prompt diversification generates varied versions of task prompts to reduce prompt-specific bias in agent evaluation. The original `prompt.md` is never modified — variants are stored separately.

## Architecture

```
eda_agentbench/
  llm/
    base.py              # Abstract LLM provider
    mock.py              # Deterministic mock provider (no API needed)
    openai_provider.py   # Optional OpenAI-compatible provider
    cache.py             # File-based request/response cache
  prompt/
    safety.py            # Rejects prompts leaking task internals
    rewriter.py          # Rewrites prompts via LLM with caching
    variant_manager.py   # Manages prompt_variants/ directory
```

## LLM Providers

### Mock Provider (default)

The mock provider produces deterministic rewrites from a seed. No API access required. Used for testing and development.

```python
from eda_agentbench.llm.mock import MockLLMProvider
provider = MockLLMProvider(seed=42)
response = provider.generate("# Task\nFix the bug.")
```

### OpenAI-Compatible Provider (optional)

Activated only when `LLM_API_KEY` is set in the environment.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | (required) | API key |
| `LLM_API_BASE` | `https://api.openai.com/v1` | API base URL |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |

```bash
export LLM_API_KEY="sk-..."
python scripts/generate_prompt_variants.py
```

## Cache

Responses are cached in `.cache/llm/` (gitignored). Cache key is a SHA-256 hash of:

- Prompt text
- System prompt
- Provider name
- Model name
- Rewrite policy

No secrets (API keys, tokens) are stored in cache entries.

## Safety Checker

The safety checker rejects rewritten prompts that expose:

- Bug type labels (`sensitivity_list`, `blocking_nonblocking`, etc.)
- Hidden test file names (`tb_hidden`, `run_hidden`)
- Solution/oracle file paths
- Local paths (`/EDA/`, `/home/`, `/tmp/`)
- License variables (`SNPSLMD_LICENSE_FILE`, `CDS_LIC_FILE`)
- Commercial tool banners (`VCS Release`, `Synopsys Inc`)

If all rewrite attempts fail safety, the original prompt is returned unchanged.

## Usage

### Generate Variants for Sample

```bash
# Default: 5 P1 tasks per bug type (50) + 5 P4 per tool (10) = 60 tasks
python scripts/generate_prompt_variants.py

# Dry run (show tasks without generating)
python scripts/generate_prompt_variants.py --dry-run

# Custom counts
python scripts/generate_prompt_variants.py --p1-count 10 --p4-count 10
```

### Directory Structure After Generation

```
task_000001/
  prompt.md                    # Original (unchanged)
  prompt_variants/
    llm_v1.md                  # Rewritten variant
    llm_v1_meta.json           # Variant metadata
  files/
  hidden/
  solution/
```

### Variant Metadata

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

## Integration with Evaluation

To evaluate using a variant instead of the original prompt:

```bash
# Future: --prompt-variant flag
eda-bench evaluate-task tasks/p1_rtl_debug/task_000001 \
    --submission solution/ \
    --prompt-variant llm_v1
```

## Design Decisions

1. **Original unchanged**: `prompt.md` is the canonical prompt. Variants are additive.
2. **Safety-first**: All rewrites pass safety before being stored as valid variants.
3. **Deterministic mock**: Testing doesn't require API access.
4. **No secrets in cache**: Cache stores only prompt/response text and metadata.
5. **Small sample first**: Generate 60 variants to validate infrastructure before scaling.
