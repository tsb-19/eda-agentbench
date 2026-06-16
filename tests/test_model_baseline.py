"""Network-free tests for the model-baseline harness.

Covers: the submission parser, sampler parity with the CLI's sampling algorithm,
and an end-to-end (fake-provider) dry run that produces a graded PASS on a QA task.
No network and no commercial tools are used.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from eda_agentbench.llm.base import BaseLLMProvider, LLMResponse
from eda_agentbench.task.loader import TaskLoader, TaskValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_model_submissions as gms  # noqa: E402
import run_model_baseline as rmb  # noqa: E402

TASKS_ROOT = REPO_ROOT / "tasks"


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def test_parse_multi_file_blocks():
    text = (
        "<<<FILE: a.sv>>>\nmodule a; endmodule\n<<<END>>>\n"
        "junk between\n"
        "<<<FILE: b.sv>>>\nmodule b; endmodule\n<<<END>>>\n"
    )
    files, ok = gms.parse_submission(text, ["a.sv", "b.sv"], is_p5=False)
    assert ok is True
    assert files["a.sv"].strip() == "module a; endmodule"
    assert files["b.sv"].strip() == "module b; endmodule"


def test_parse_single_file_fallback_strips_fence():
    text = "```verilog\nmodule x; endmodule\n```"
    files, ok = gms.parse_submission(text, ["design.sv"], is_p5=False)
    assert ok is False  # fallback path
    assert files["design.sv"].strip() == "module x; endmodule"


def test_parse_block_matches_by_basename():
    # Model may echo a bare filename; we match on basename.
    text = "<<<FILE: answer.txt>>>\n-3.14\n<<<END>>>"
    files, ok = gms.parse_submission(text, ["answer.txt"], is_p5=False)
    assert ok is True
    assert files["answer.txt"].strip() == "-3.14"


def test_parse_p5_maps_to_basename():
    text = "<<<FILE: deck.sp>>>\n* fixed\n<<<END>>>"
    files, ok = gms.parse_submission(text, ["visible/deck.sp"], is_p5=True)
    assert ok is True
    assert "deck.sp" in files  # basename target, not nested path


def test_parse_strips_fence_inside_marker_block():
    # Model obeyed the contract but fenced the code inside the block.
    text = "<<<FILE: design.sv>>>\n```verilog\nmodule x; endmodule\n```\n<<<END>>>"
    files, ok = gms.parse_submission(text, ["design.sv"], is_p5=False)
    assert ok is True
    assert files["design.sv"].strip() == "module x; endmodule"


def test_parse_prose_wrapped_code_extracts_block():
    # No contract markers; model wrapped the file in prose + a fence. The file must be
    # recovered cleanly (else it would be a broken submission -> unfair fail / wasted run).
    text = ("Here is the corrected module:\n\n```verilog\n"
            "module top(input a, output b);\n  assign b = a;\nendmodule\n```\n\n"
            "This fixes the missing assignment.")
    files, ok = gms.parse_submission(text, ["design.sv"], is_p5=False)
    assert ok is False  # fell back
    assert files["design.sv"].strip().startswith("module top")
    assert "This fixes" not in files["design.sv"]
    assert "Here is the corrected" not in files["design.sv"]


def test_parse_prose_multiple_blocks_takes_largest():
    text = ("Change this line `assign b = a;` then use:\n```\nshort\n```\n"
            "Full file:\n```verilog\nmodule top; wire a, b, c, d, e; endmodule\n```")
    files, ok = gms.parse_submission(text, ["design.sv"], is_p5=False)
    assert "module top" in files["design.sv"]
    assert files["design.sv"].strip() != "short"


# --------------------------------------------------------------------------- #
# Retry/backoff on transient gateway errors (429/5xx/timeout)
# --------------------------------------------------------------------------- #
class _FlakyProvider(BaseLLMProvider):
    """Raises a 429 the first `fail_n` times, then succeeds."""

    def __init__(self, fail_n: int):
        self._fail_n = fail_n
        self.calls = 0

    @property
    def name(self): return "flaky"

    @property
    def model(self): return "flaky-v1"

    def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        self.calls += 1
        if self.calls <= self._fail_n:
            raise RuntimeError("HTTP 429 from gateway: RateLimitError local_rate_limited")
        return LLMResponse(text="ok", model=self.model, usage={}, metadata={})


def test_retry_recovers_from_rate_limit(monkeypatch):
    monkeypatch.setattr(gms.time, "sleep", lambda *_: None)  # no real waiting
    prov = _FlakyProvider(fail_n=2)
    resp = gms._generate_with_retry(prov, "p", {}, max_retries=5)
    assert resp.text == "ok"
    assert prov.calls == 3


def test_retry_gives_up_and_raises(monkeypatch):
    monkeypatch.setattr(gms.time, "sleep", lambda *_: None)
    prov = _FlakyProvider(fail_n=99)
    try:
        gms._generate_with_retry(prov, "p", {}, max_retries=2)
        assert False, "should have raised"
    except RuntimeError as e:
        assert "429" in str(e)
    assert prov.calls == 3  # initial + 2 retries


def test_retry_does_not_retry_nonretryable(monkeypatch):
    monkeypatch.setattr(gms.time, "sleep", lambda *_: None)

    class _Bad(BaseLLMProvider):
        def __init__(self): self.calls = 0
        @property
        def name(self): return "bad"
        @property
        def model(self): return "bad"
        def generate(self, prompt, system="", **kw):
            self.calls += 1
            raise RuntimeError("HTTP 400 bad request")

    prov = _Bad()
    try:
        gms._generate_with_retry(prov, "p", {}, max_retries=5)
        assert False
    except RuntimeError:
        pass
    assert prov.calls == 1  # 400 is not retried




# --------------------------------------------------------------------------- #
# Sampler parity with the CLI algorithm (cli.py cmd_evaluate_dataset 271-288)
# --------------------------------------------------------------------------- #
def _cli_replica(loader: TaskLoader, sample_per_track: int, seed: int):
    task_paths = loader.discover(track=None, recursive=True)
    by_track: dict[str, list[Path]] = {}
    for tp in task_paths:
        try:
            tr = loader.load(tp).get("track", "unknown")
        except TaskValidationError:
            tr = "unknown"
        by_track.setdefault(tr, []).append(tp)
    rng = random.Random(seed)
    out: list[Path] = []
    for tr in sorted(by_track):
        cands = by_track[tr]
        out.extend(rng.sample(cands, min(sample_per_track, len(cands))))
    return out


def test_sampler_matches_cli_algorithm():
    loader = TaskLoader(TASKS_ROOT)
    got = gms.sample_tasks(loader, track=None, sample_per_track=3, seed=42)
    expected = _cli_replica(loader, sample_per_track=3, seed=42)
    assert got == expected


def test_sampler_is_deterministic():
    loader = TaskLoader(TASKS_ROOT)
    a = gms.sample_tasks(loader, track=None, sample_per_track=2, seed=7)
    b = gms.sample_tasks(loader, track=None, sample_per_track=2, seed=7)
    assert a == b


# --------------------------------------------------------------------------- #
# End-to-end dry run with a fake provider returning the correct answer
# --------------------------------------------------------------------------- #
class _OracleProvider(BaseLLMProvider):
    """Returns the task's known-correct answer wrapped in the output contract."""

    def __init__(self, answer: str):
        self._answer = answer

    @property
    def name(self) -> str:
        return "oracle"

    @property
    def model(self) -> str:
        return "oracle-v1"

    def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        return LLMResponse(
            text=f"<<<FILE: answer.txt>>>\n{self._answer}\n<<<END>>>",
            model=self.model, usage={}, metadata={},
        )


def test_end_to_end_oracle_passes_on_qa_task(tmp_path):
    loader = TaskLoader(TASKS_ROOT)
    qa = loader.discover(track="p3_timing_report_qa", recursive=True)
    assert qa, "no P3 tasks discovered"
    task_path = qa[0]
    meta = loader.load(task_path)
    correct = (task_path / "solution" / "answer.txt").read_text().strip()

    provider = _OracleProvider(correct)
    prompt = gms.build_prompt(task_path, meta, max_visible_bytes=20000)
    resp = provider.generate(prompt)
    files, ok = gms.parse_submission(resp.text, meta["files"]["editable"], is_p5=False)
    assert ok is True

    sub_dir = tmp_path / "sub"
    gms.write_submission(sub_dir, files)

    res = rmb._grade_one(task_path, sub_dir, runs_root=tmp_path / "runs")
    assert res["ok"] is True
    assert res["passed"] is True
    assert res["total_score"] == 1.0


# --------------------------------------------------------------------------- #
# OpenAIProvider: extra_body merge + reasoning capture (no network — stub urlopen)
# --------------------------------------------------------------------------- #
def test_provider_merges_extra_body_and_captures_reasoning(monkeypatch):
    import json as _json
    import contextlib
    from eda_agentbench.llm import openai_provider as op

    captured = {}

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return _json.dumps(self._payload).encode()

    @contextlib.contextmanager
    def fake_urlopen(req, timeout=0):
        captured["body"] = _json.loads(req.data.decode())
        yield _Resp({
            "model": "m1",
            "choices": [{"finish_reason": "stop",
                         "message": {"content": "answer", "reasoning_content": "because..."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 40,
                      "completion_tokens_details": {"reasoning_tokens": 30}},
        })

    monkeypatch.setattr(op, "urlopen", fake_urlopen)
    prov = op.OpenAIProvider(api_key="k", api_base="https://x/v1", model="m1")
    resp = prov.generate("hi", system="sys", extra_body={"enable_thinking": True}, max_tokens=99)

    assert captured["body"]["enable_thinking"] is True       # extra_body merged
    assert captured["body"]["max_tokens"] == 99
    assert resp.text == "answer"
    assert resp.usage["reasoning_tokens"] == 30              # reasoning usage captured
    assert resp.metadata["reasoning_content"] == "because..."



# --------------------------------------------------------------------------- #
# Concurrency: rate limiter (pure, clock-injected) + manifest assembly order
# --------------------------------------------------------------------------- #
def test_rate_limiter_sliding_window():
    """At most `rpm` starts per window; the (rpm+1)th waits, then admits once the
    oldest start ages out. `_reserve` is pure (clock injected) so no real sleeping."""
    rl = gms.RateLimiter(rpm=2, window=60.0)
    assert rl._reserve(0.0) == 0.0      # 1st admitted
    assert rl._reserve(0.0) == 0.0      # 2nd admitted
    assert rl._reserve(0.0) == 60.0     # 3rd blocked: wait the full window
    assert rl._reserve(30.0) == 30.0    # still blocked: 30s until oldest ages out
    assert rl._reserve(61.0) == 0.0     # both aged out -> admitted again


def test_rate_limiter_disabled_is_noop():
    rl = gms.RateLimiter(rpm=0)
    for t in (0.0, 0.0, 0.0, 0.0, 0.0):
        assert rl._reserve(t) == 0.0
    rl.acquire()  # returns immediately (no sleep)


class _FixedProvider(BaseLLMProvider):
    """Deterministic provider: same output regardless of prompt/thread."""

    def __init__(self, tag: str):
        self._tag = tag

    @property
    def name(self) -> str:
        return self._tag

    @property
    def model(self) -> str:
        return f"{self._tag}-v1"

    def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        return LLMResponse(text="<<<FILE: answer.txt>>>\nX\n<<<END>>>",
                           model=self.model, usage={"prompt_tokens": 1, "completion_tokens": 1},
                           metadata={})


def test_manifest_assembly_deterministic_under_concurrency(tmp_path, monkeypatch):
    """The flat (task,model) job pool is assembled back into manifest.json in sampled
    order with models in config order — so concurrency must not change the manifest."""
    fake = [("fakeA", _FixedProvider("fakeA"), {}),
            ("fakeB", _FixedProvider("fakeB"), {})]
    monkeypatch.setattr(gms, "load_model_specs", lambda *a, **k: fake)

    def run(out: Path, conc: int):
        gms.main([str(TASKS_ROOT), "--models", "ignored", "--track", "p3_timing_report_qa",
                  "--sample-per-track", "4", "--seed", "42", "--out", str(out),
                  "--concurrency", str(conc)])

    run(tmp_path / "c1", 1)
    run(tmp_path / "c4", 4)
    m1 = (tmp_path / "c1" / "manifest.json").read_text()
    m4 = (tmp_path / "c4" / "manifest.json").read_text()
    assert m1 == m4, "manifest changed with concurrency"
    # And every (model,track,task) submission dir was written.
    import json as _json
    man = _json.loads(m1)
    assert len(man["tasks"]) == 4
    for t in man["tasks"]:
        assert set(t["submissions"]) == {"fakeA", "fakeB"}
        for rec in t["submissions"].values():
            assert (tmp_path / "c4" / rec["submission_dir"] / "answer.txt").is_file()
