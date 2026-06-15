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
