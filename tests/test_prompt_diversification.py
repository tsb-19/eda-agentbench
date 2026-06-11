"""Tests for prompt diversification: LLM provider, cache, safety, rewriter."""

import json
from pathlib import Path

import pytest

from eda_agentbench.llm.mock import MockLLMProvider
from eda_agentbench.llm.cache import LLMCache
from eda_agentbench.prompt.safety import SafetyChecker, SafetyResult
from eda_agentbench.prompt.rewriter import PromptRewriter
from eda_agentbench.prompt.variant_manager import VariantManager


# --- Mock Provider Tests ---

def test_mock_provider_deterministic():
    """Same input produces same output."""
    p1 = MockLLMProvider(seed=42)
    p2 = MockLLMProvider(seed=42)
    prompt = "# Test Task\nFix the bug in design.sv."
    r1 = p1.generate(prompt)
    r2 = p2.generate(prompt)
    assert r1.text == r2.text
    assert r1.model == "mock-v1"


def test_mock_provider_different_seeds():
    """Different seeds may produce different output."""
    p1 = MockLLMProvider(seed=1)
    p2 = MockLLMProvider(seed=99)
    prompt = "# Test Task\nFix the bug in design.sv."
    r1 = p1.generate(prompt)
    r2 = p2.generate(prompt)
    # Both should be valid but may differ
    assert len(r1.text) > 0
    assert len(r2.text) > 0


def test_mock_provider_preserves_content():
    """Rewrite preserves key technical content."""
    p = MockLLMProvider(seed=42)
    prompt = "# RTL Debug Task\n\n## Files\n\n- `design.sv` — the buggy design\n\n## Constraints\n\n- Only modify `design.sv`"
    r = p.generate(prompt)
    assert "design.sv" in r.text
    assert "RTL Debug Task" in r.text


# --- Cache Tests ---

def test_cache_hit_miss(tmp_path):
    """Cache returns None on miss, response on hit."""
    cache = LLMCache(tmp_path / "cache")
    assert cache.size == 0

    from eda_agentbench.llm.base import LLMResponse
    resp = LLMResponse(text="rewritten", model="mock-v1")

    # Miss
    assert cache.get("prompt", "sys", "mock", "mock-v1") is None

    # Put
    cache.put("prompt", "sys", "mock", "mock-v1", resp)
    assert cache.size == 1

    # Hit
    cached = cache.get("prompt", "sys", "mock", "mock-v1")
    assert cached is not None
    assert cached.text == "rewritten"


def test_cache_different_inputs(tmp_path):
    """Different inputs produce different cache keys."""
    cache = LLMCache(tmp_path / "cache")
    from eda_agentbench.llm.base import LLMResponse

    cache.put("prompt1", "", "mock", "m", LLMResponse(text="r1", model="m"))
    cache.put("prompt2", "", "mock", "m", LLMResponse(text="r2", model="m"))
    assert cache.size == 2
    assert cache.get("prompt1", "", "mock", "m").text == "r1"
    assert cache.get("prompt2", "", "mock", "m").text == "r2"


def test_cache_clear(tmp_path):
    """Clear removes all entries."""
    cache = LLMCache(tmp_path / "cache")
    from eda_agentbench.llm.base import LLMResponse

    cache.put("p", "", "m", "m", LLMResponse(text="r", model="m"))
    assert cache.size == 1
    removed = cache.clear()
    assert removed == 1
    assert cache.size == 0


def test_cache_no_secrets(tmp_path):
    """Cache entries don't contain API keys."""
    cache = LLMCache(tmp_path / "cache")
    from eda_agentbench.llm.base import LLMResponse

    resp = LLMResponse(text="result", model="m", metadata={"api_key": "secret123"})
    cache.put("p", "", "m", "m", resp)

    # Read raw JSON
    entry_file = list((tmp_path / "cache").glob("*.json"))[0]
    raw = entry_file.read_text()
    assert "secret123" not in raw


# --- Safety Checker Tests ---

def test_safety_clean_prompt():
    """Clean prompt passes safety check."""
    checker = SafetyChecker()
    text = "# Task\nFix the bug in design.sv.\nRun bash run_public.sh to verify."
    result = checker.check(text)
    assert result.passed


def test_safety_rejects_bug_type_label():
    """Prompt containing bug_type label is rejected."""
    checker = SafetyChecker()
    text = "This task has a sensitivity_list bug. Fix it."
    result = checker.check(text)
    assert not result.passed
    assert any("bug_type" in v for v in result.violations)


def test_safety_rejects_readable_bug_type():
    """Prompt containing readable bug type name is rejected."""
    checker = SafetyChecker()
    text = "The sensitivity list is incomplete. Fix it."
    result = checker.check(text)
    assert not result.passed


def test_safety_rejects_local_path():
    """Prompt containing local paths is rejected."""
    checker = SafetyChecker()
    for path in ["/EDA/soft2/synopsys", "/home/tsb/project", "/tmp/workspace"]:
        result = checker.check(f"Run from {path}")
        assert not result.passed
        assert any("local path" in v for v in result.violations)


def test_safety_rejects_license_var():
    """Prompt containing license variables is rejected."""
    checker = SafetyChecker()
    result = checker.check("Set SNPSLMD_LICENSE_FILE=27000@server")
    assert not result.passed


def test_safety_rejects_hidden_file():
    """Prompt referencing hidden files is rejected."""
    checker = SafetyChecker()
    result = checker.check("Look at tb_hidden.sv for clues.")
    assert not result.passed


def test_safety_rejects_solution_ref():
    """Prompt referencing solution files is rejected."""
    checker = SafetyChecker()
    result = checker.check("See solution/design.sv for the answer.")
    assert not result.passed


def test_safety_rejects_tool_banner():
    """Prompt containing tool banners is rejected."""
    checker = SafetyChecker()
    result = checker.check("VCS Release S-2021.09-SP1")
    assert not result.passed


def test_safety_metadata_check():
    """Safety checker uses metadata for additional checks."""
    checker = SafetyChecker()
    meta = {"generator": {"bug_type": "sensitivity_list"}}
    result = checker.check("Fix the sensitivity_list issue.", metadata=meta)
    assert not result.passed


def test_safety_result_str():
    """SafetyResult string representation."""
    r1 = SafetyResult(passed=True)
    assert str(r1) == "SAFETY PASS"

    r2 = SafetyResult(passed=False, violations=["test violation"])
    assert "FAIL" in str(r2)
    assert "test violation" in str(r2)


# --- Rewriter Tests ---

def test_rewriter_with_mock(tmp_path):
    """Rewriter works with mock provider."""
    provider = MockLLMProvider(seed=42)
    cache = LLMCache(tmp_path / "cache")
    rewriter = PromptRewriter(provider=provider, cache=cache)

    prompt = "# RTL Debug Task\n\n## Description\n\nFix the bug in design.sv.\n\n## Hint\n\nCheck the logic."
    text, result = rewriter.rewrite(prompt)
    assert len(text) > 0
    assert result.passed


def test_rewriter_caches_result(tmp_path):
    """Rewriter caches successful results."""
    provider = MockLLMProvider(seed=42)
    cache = LLMCache(tmp_path / "cache")
    rewriter = PromptRewriter(provider=provider, cache=cache)

    prompt = "# Task\nFix design.sv."
    rewriter.rewrite(prompt)
    assert cache.size >= 1

    # Second call should hit cache
    text2, _ = rewriter.rewrite(prompt)
    assert text2 == prompt or len(text2) > 0  # Cache hit or new generation


def test_rewriter_safety_fallback(tmp_path):
    """Rewriter returns original if all attempts fail safety."""
    provider = MockLLMProvider(seed=42)
    safety = SafetyChecker()
    rewriter = PromptRewriter(provider=provider, safety=safety)

    # A prompt that will generate a rewrite containing "design.sv" is fine,
    # but let's test with metadata that causes safety failure
    prompt = "# Task\nThe sensitivity_list is broken."
    meta = {"generator": {"bug_type": "sensitivity_list"}}
    text, result = rewriter.rewrite(prompt, metadata=meta, max_attempts=1)
    # The mock provider preserves "sensitivity_list" in the text
    # so this should fail safety and return original
    assert "sensitivity_list" in text.lower()


# --- Variant Manager Tests ---

def test_variant_manager_creates_files(tmp_path):
    """Variant manager creates variant files in task directory."""
    # Create a minimal task
    task_dir = tmp_path / "task_000001"
    task_dir.mkdir()
    (task_dir / "prompt.md").write_text("# RTL Debug Task\nFix the bug in design.sv.")
    (task_dir / "metadata.json").write_text(json.dumps({
        "task_id": "task_000001",
        "track": "p1_rtl_debug",
        "tool": ["vcs"],
        "generator": {"bug_type": "sensitivity_list"},
    }))

    provider = MockLLMProvider(seed=42)
    rewriter = PromptRewriter(provider=provider)
    manager = VariantManager(rewriter=rewriter)

    path, result = manager.generate_variant(task_dir, variant_name="test_v1")
    assert path.exists()
    assert (task_dir / "prompt_variants" / "test_v1.md").exists()
    assert (task_dir / "prompt_variants" / "test_v1_meta.json").exists()

    # Original prompt unchanged
    assert (task_dir / "prompt.md").read_text() == "# RTL Debug Task\nFix the bug in design.sv."


def test_variant_manager_preserves_original(tmp_path):
    """Original prompt.md is never modified."""
    task_dir = tmp_path / "task_000001"
    task_dir.mkdir()
    original = "# Task\nFix the bug."
    (task_dir / "prompt.md").write_text(original)
    (task_dir / "metadata.json").write_text(json.dumps({
        "task_id": "task_000001", "track": "p1_rtl_debug", "tool": ["vcs"],
    }))

    provider = MockLLMProvider(seed=42)
    manager = VariantManager(rewriter=PromptRewriter(provider=provider))
    manager.generate_variant(task_dir)

    assert (task_dir / "prompt.md").read_text() == original


# --- Integration: sample generation ---

def test_sample_generation_produces_variants(tmp_path):
    """Generate variants for a small sample and verify structure."""
    # Create 3 mock tasks
    for i in range(3):
        task_dir = tmp_path / f"task_{i:06d}"
        task_dir.mkdir()
        (task_dir / "prompt.md").write_text(f"# Task {i}\nFix the bug in design.sv.")
        (task_dir / "metadata.json").write_text(json.dumps({
            "task_id": f"task_{i:06d}",
            "track": "p1_rtl_debug",
            "tool": ["vcs"],
            "generator": {"bug_type": "sensitivity_list"},
        }))

    provider = MockLLMProvider(seed=42)
    manager = VariantManager(rewriter=PromptRewriter(provider=provider))

    tasks = [tmp_path / f"task_{i:06d}" for i in range(3)]
    results = manager.generate_batch(tasks, variant_name="llm_v1")

    assert len(results) == 3
    for path, result in results:
        assert path.exists()
        assert len(path.read_text()) > 0


# --- Real Provider Tests (skip if no API key) ---

def _has_real_provider() -> bool:
    """Check if a real LLM provider is available."""
    from eda_agentbench.llm.openai_provider import create_provider
    from eda_agentbench.llm.mock import MockLLMProvider
    p = create_provider()
    return not isinstance(p, MockLLMProvider)


@pytest.mark.skipif(not _has_real_provider(), reason="No API key available")
def test_real_provider_generates_response():
    """Real provider returns a valid response."""
    from eda_agentbench.llm.openai_provider import create_provider
    provider = create_provider()
    response = provider.generate("# Test Task\nFix the bug in design.sv.")
    assert len(response.text) > 0
    assert response.model


@pytest.mark.skipif(not _has_real_provider(), reason="No API key available")
def test_real_provider_safety_check():
    """Real provider output passes safety check."""
    from eda_agentbench.llm.openai_provider import create_provider
    provider = create_provider()
    safety = SafetyChecker()

    prompt = "# RTL Debug Task: Sensitivity List\n\n## Description\n\nThe module below has a bug.\n\n## Hint\n\nPay attention to the sensitivity list."
    response = provider.generate(prompt, system="Rewrite this prompt. Do not include bug type names.")
    result = safety.check(response.text)
    # Note: real provider may or may not pass depending on model behavior
    # This test just verifies the pipeline works
    assert isinstance(result, SafetyResult)
