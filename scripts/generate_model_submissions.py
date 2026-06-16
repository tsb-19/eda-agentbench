#!/usr/bin/env python3
"""Generate single-shot model submissions for the EDA-AgentBench baseline.

Runs LLM inference HERE (needs internet). For each sampled task and each model,
this builds a prompt from prompt.md + the task's visible files, asks the model to
emit the full final content of each editable file, parses the response, and writes
a submission directory:

    <out>/<model_name>/<track>/<task_id>/<editable files>

Plus a per-task transcript.json (raw response + token usage) and a top-level
manifest.json. Grading is a SEPARATE step (scripts/run_model_baseline.py): report-QA
tracks are graded locally; the real-tool tracks are graded on the EDA host (b04).
The model is never invoked during grading, so this inference/grading split keeps the
LLM (internet) and the EDA tools (b04, no internet) in different processes.

Usage:
    python scripts/generate_model_submissions.py tasks \
        --models configs/baseline_models.json --sample-per-track 15 --seed 42 \
        --out runs/baseline/<stamp>/submissions
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eda_agentbench.llm.base import BaseLLMProvider  # noqa: E402
from eda_agentbench.llm.openai_provider import OpenAIProvider, _load_dotenv  # noqa: E402
from eda_agentbench.task.loader import TaskLoader, TaskValidationError  # noqa: E402

# Report-QA tracks need no commercial tool: graded locally. Everything else -> b04.
LOCAL_QA_TRACKS = {
    "p3_timing_report_qa",
    "p6_dc_synthesis_qa",
    "p8_pnr_report_qa",
}

# Output contract markers the model must wrap each edited file in.
_FILE_BLOCK_RE = re.compile(
    r"<<<FILE:\s*(?P<name>[^\n>]+?)\s*>>>\n(?P<body>.*?)\n?<<<END>>>",
    re.DOTALL,
)
# A single enclosing markdown fence (whole chunk).
_FENCE_RE = re.compile(r"^\s*```[^\n]*\n(?P<body>.*?)\n```\s*$", re.DOTALL)
# Any fenced code block (for prose-wrapped answers like "Here's the fix:\n```...```").
_CODE_BLOCK_RE = re.compile(r"```[^\n]*\n(?P<body>.*?)\n?```", re.DOTALL)


def _strip_enclosing_fence(text: str) -> str:
    """If the chunk is wrapped in one ```lang ... ``` fence, return its inner body."""
    m = _FENCE_RE.match(text.strip())
    return m.group("body") if m else text


# --------------------------------------------------------------------------- #
# Model specs
# --------------------------------------------------------------------------- #
def load_model_specs(path: Path, allow_mock: bool) -> list[tuple[str, BaseLLMProvider, dict]]:
    """Return [(name, provider, gen_kwargs), ...] from a baseline_models.json file."""
    _load_dotenv()
    cfg = json.loads(path.read_text())
    specs = cfg.get("models", [])
    if not specs:
        raise SystemExit(f"No models listed in {path}")

    out: list[tuple[str, BaseLLMProvider, dict]] = []
    for spec in specs:
        if str(spec.get("name", "")).startswith("_"):
            continue  # skip comment-like entries
        name = spec["name"]
        env_key = spec.get("api_key_env", "")
        api_key = os.environ.get(env_key, "") if env_key else ""
        # api_base: literal, or read from an env var named by api_base_env (e.g. BASE_URL),
        # optionally with a path suffix appended (e.g. "/v1").
        api_base = spec.get("api_base", "")
        if not api_base and spec.get("api_base_env"):
            api_base = os.environ.get(spec["api_base_env"], "").rstrip("/") + spec.get("api_base_suffix", "")
        gen_kwargs = {
            "temperature": spec.get("temperature", 0.0),
            "max_tokens": spec.get("max_tokens", 4096),
            "timeout": spec.get("timeout", 600),
        }
        if spec.get("extra_body"):
            gen_kwargs["extra_body"] = spec["extra_body"]
        if api_key:
            provider: BaseLLMProvider = OpenAIProvider(
                api_key=api_key,
                api_base=api_base,
                model=spec.get("model_id", ""),
            )
        elif allow_mock:
            from eda_agentbench.llm.mock import MockLLMProvider
            provider = MockLLMProvider()
            name = f"{name}__MOCK"
        else:
            raise SystemExit(
                f"Model '{name}': no API key in ${env_key}. Set it (or use --allow-mock "
                f"for a wiring dry run). Refusing to silently fall back to the mock provider."
            )
        out.append((name, provider, gen_kwargs))
    return out


# --------------------------------------------------------------------------- #
# Sampling — replicates eda_agentbench/cli.py cmd_evaluate_dataset (lines 271-288)
# verbatim so the baseline samples the SAME tasks for a given (seed, N).
# --------------------------------------------------------------------------- #
def sample_tasks(loader: TaskLoader, track: str | None,
                 sample_per_track: int, seed: int) -> list[Path]:
    task_paths = loader.discover(track=track, recursive=True)
    if not task_paths:
        raise SystemExit("No tasks discovered")

    by_track: dict[str, list[Path]] = {}
    for tp in task_paths:
        try:
            meta = loader.load(tp)
            tr = meta.get("track", "unknown")
        except TaskValidationError:
            tr = "unknown"
        by_track.setdefault(tr, []).append(tp)

    rng = random.Random(seed)
    sampled: list[Path] = []
    for tr in sorted(by_track):
        candidates = by_track[tr]
        n = min(sample_per_track, len(candidates))
        sampled.extend(rng.sample(candidates, n))
    return sampled


# --------------------------------------------------------------------------- #
# Prompt building + response parsing
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "You are an expert digital/analog IC design engineer working in a commercial "
    "EDA flow (Synopsys/Cadence). You will be given one task: read the provided "
    "files and produce the corrected/required content for the editable file(s). "
    "Reply with ONLY the file blocks in the exact format requested — no prose, no "
    "explanation outside the blocks."
)


def _read_text(p: Path, max_bytes: int) -> str:
    try:
        data = p.read_bytes()
    except OSError:
        return ""
    truncated = len(data) > max_bytes
    text = data[:max_bytes].decode("utf-8", errors="replace")
    if truncated:
        text += "\n... [truncated]"
    return text


def build_prompt(task_path: Path, meta: dict, max_visible_bytes: int) -> str:
    files_spec = meta["files"]
    editable = list(files_spec.get("editable", []))
    visible = list(files_spec.get("visible", []))
    is_p5 = meta.get("track") == "p5_spice_deck_debug"
    base = task_path  # visible files live under files/ (or visible/ for P5)

    prompt_md = (task_path / "prompt.md")
    parts: list[str] = []
    if prompt_md.is_file():
        parts.append("# TASK\n" + _read_text(prompt_md, max_visible_bytes))

    parts.append("\n# PROVIDED FILES")
    for rel in visible:
        # Resolve the on-disk location of a visible file.
        for cand in ((base / "files" / rel), (base / rel), (base / "visible" / Path(rel).name)):
            if cand.is_file():
                parts.append(f"\n## {rel}\n```\n{_read_text(cand, max_visible_bytes)}\n```")
                break

    contract_files = [Path(e).name if is_p5 else e for e in editable]
    parts.append("\n# YOUR OUTPUT")
    parts.append(
        "Return the FULL final content of each editable file below, each wrapped "
        "EXACTLY as:\n<<<FILE: NAME>>>\n<file content>\n<<<END>>>\n"
        "Editable file(s): " + ", ".join(contract_files) + "\n"
        "Output nothing else."
    )
    return "\n".join(parts)


def parse_submission(text: str, editable: list[str], is_p5: bool) -> tuple[dict[str, str], bool]:
    """Parse model output into {target_relpath: content}. Returns (files, parse_ok)."""
    # Target relpath each editable maps to in the submission dir.
    # P5: write the .sp at the submission root by basename (the evaluator globs *.sp).
    targets = {Path(e).name if is_p5 else e: e for e in editable}
    by_name = {Path(e).name: (Path(e).name if is_p5 else e) for e in editable}

    found: dict[str, str] = {}
    for m in _FILE_BLOCK_RE.finditer(text):
        name = m.group("name").strip()
        body = _strip_enclosing_fence(m.group("body"))  # model may fence inside the block
        key = Path(name).name
        if key in by_name:
            found[by_name[key]] = body
        elif name in targets:
            found[targets[name]] = body

    if found:
        return found, True

    # Fallback (single editable file): the model ignored the contract. Recover the file
    # content robustly so a prose-wrapped-but-correct answer isn't turned into a broken
    # file (which would unfairly fail — and waste an expensive tool/b04 run):
    #   1. one enclosing fence -> its body;
    #   2. fenced code block(s) amid prose -> the largest block (the full file);
    #   3. otherwise the whole reply.
    if len(editable) == 1:
        body = text.strip()
        if _FENCE_RE.match(body):
            body = _strip_enclosing_fence(body)
        else:
            blocks = [b for b in _CODE_BLOCK_RE.findall(body)]
            if blocks:
                body = max(blocks, key=len)
        target = Path(editable[0]).name if is_p5 else editable[0]
        return {target: body}, False

    return {}, False


def write_submission(sub_dir: Path, files: dict[str, str]) -> None:
    sub_dir.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        dest = sub_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not content.endswith("\n"):
            content += "\n"
        dest.write_text(content)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate single-shot model submissions.")
    ap.add_argument("tasks_root", help="Root dir containing task tracks (e.g. tasks)")
    ap.add_argument("--models", required=True, help="Path to baseline_models.json")
    ap.add_argument("--out", required=True, help="Output dir for submissions")
    ap.add_argument("--track", default=None, help="Restrict to a single track")
    ap.add_argument("--sample-per-track", type=int, default=15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-visible-bytes", type=int, default=20000,
                    help="Per-file cap on inlined visible-file context")
    ap.add_argument("--allow-mock", action="store_true",
                    help="Permit MockLLMProvider when a key is missing (wiring dry run only)")
    ap.add_argument("--limit", type=int, default=None, help="Cap total tasks (debug)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tasks_root = Path(args.tasks_root).resolve()
    out_root = Path(args.out).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    models = load_model_specs(Path(args.models).resolve(), args.allow_mock)
    loader = TaskLoader(tasks_root)
    sampled = sample_tasks(loader, args.track, args.sample_per_track, args.seed)
    if args.limit is not None:
        sampled = sampled[: args.limit]

    print(f"Sampled {len(sampled)} tasks; {len(models)} model(s): "
          f"{', '.join(n for n, _, _ in models)}")

    manifest: dict = {
        "tasks_root": str(tasks_root),
        "seed": args.seed,
        "sample_per_track": args.sample_per_track,
        "track_filter": args.track,
        "models": [n for n, _, _ in models],
        "tasks": [],
    }

    for tp in sampled:
        meta = loader.load(tp)
        task_id = meta["task_id"]
        track = meta.get("track", "unknown")
        is_p5 = track == "p5_spice_deck_debug"
        editable = list(meta["files"].get("editable", []))
        prompt = build_prompt(tp, meta, args.max_visible_bytes)
        needs_b04 = track not in LOCAL_QA_TRACKS

        entry = {"task_id": task_id, "track": track, "task_path": str(tp),
                 "needs_b04": needs_b04, "submissions": {}}

        for name, provider, gen_kwargs in models:
            sub_dir = out_root / name / track / task_id
            rec = {"submission_dir": str(sub_dir), "parse_ok": False, "error": None}
            try:
                t0 = time.time()
                resp = provider.generate(prompt, system=_SYSTEM, **gen_kwargs)
                dt = time.time() - t0
                files, parse_ok = parse_submission(resp.text, editable, is_p5)
                write_submission(sub_dir, files)
                rec["parse_ok"] = parse_ok
                (sub_dir / "transcript.json").write_text(json.dumps({
                    "task_id": task_id, "track": track, "model": name,
                    "model_id": provider.model, "parse_ok": parse_ok,
                    "elapsed_sec": round(dt, 2), "usage": resp.usage,
                    "raw_response": resp.text,
                }, indent=2))
            except Exception as e:  # network/HTTP/parse — record, keep going
                rec["error"] = f"{type(e).__name__}: {e}"
                sub_dir.mkdir(parents=True, exist_ok=True)
                (sub_dir / "transcript.json").write_text(json.dumps({
                    "task_id": task_id, "track": track, "model": name,
                    "error": rec["error"],
                }, indent=2))
            status = "ok" if rec["error"] is None and rec["parse_ok"] else \
                     ("fallback" if rec["error"] is None else "ERR")
            print(f"  [{name}] {track}/{task_id}: {status}")
            entry["submissions"][name] = rec

        manifest["tasks"].append(entry)

    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2))
    n_b04 = sum(1 for t in manifest["tasks"] if t["needs_b04"])
    print(f"\nWrote submissions + manifest to {out_root}")
    print(f"  {len(sampled) - n_b04} local-QA tasks, {n_b04} tool tasks (grade on b04)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
