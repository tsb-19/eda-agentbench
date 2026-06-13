"""Core agentic evaluation runner.

Security model:
- Agent runs in a workspace with ONLY visible+editable files.
- After agent exits, an evaluator-private workspace is created by merging
  the agent's edits with hidden/oracle files from the task root.
- EDA tool execution and scoring happen in the evaluator workspace.
- Hidden/oracle files are NEVER readable by the agent process.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from eda_agentbench.config import RUNS_ROOT
from eda_agentbench.types import (
    AgentSubprocessResult,
    AgenticRunResult,
    ScoreResult,
    ScoreComponent,
)
from eda_agentbench.agentic.workspace import (
    create_agent_workspace,
    create_evaluator_workspace,
    snapshot_workspace,
    compute_file_changes,
    detect_forbidden_modifications,
)


def run_single_agentic(
    task_path: Path,
    agent_cmd: str,
    meta: dict,
    timeout: int,
    runs_root: Path | None = None,
) -> tuple[Path, ScoreResult, AgenticRunResult]:
    """Run an agent against a single task, then evaluate.

    Two-phase workspace model:
    1. Agent workspace: visible+editable only. Agent runs here.
    2. Evaluator workspace: agent output + hidden files. EDA tools + scoring here.

    Returns: (runs_dir, ScoreResult, AgenticRunResult)
    """
    from eda_agentbench.tools.detector import ToolEnvironmentDetector
    from eda_agentbench.tools.env_shim import EnvShim
    from eda_agentbench.sanitizer.log_sanitizer import LogSanitizer

    task_id = meta["task_id"]
    files_spec = meta["files"]
    runs_base = runs_root or RUNS_ROOT
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    runs_dir = runs_base / task_id / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    agent_workspace = None
    eval_workspace = None
    try:
        # === PHASE 1: Agent workspace (visible+editable only) ===
        agent_workspace = create_agent_workspace(task_path, meta)

        # Snapshot agent workspace before agent runs
        before_snapshot = snapshot_workspace(agent_workspace)

        # Run agent in agent-only workspace
        agent_result = _run_agent_subprocess(
            agent_cmd, agent_workspace, timeout, task_path, meta,
        )

        # Snapshot agent workspace after agent runs
        after_snapshot = snapshot_workspace(agent_workspace)

        # Compute changes and anti-cheat on agent workspace
        changes = compute_file_changes(before_snapshot, after_snapshot)
        clean, violations = detect_forbidden_modifications(
            changes, files_spec.get("forbidden", []),
        )

        # === PHASE 2: Evaluator workspace (agent output + hidden files) ===
        eval_workspace = create_evaluator_workspace(
            task_path, meta, agent_workspace,
        )

        is_report_qa = meta.get("track") in ("p3_timing_report_qa", "p6_dc_synthesis_qa")

        # Detect tools (skip for report QA)
        detector = ToolEnvironmentDetector()
        detected = []
        if not is_report_qa:
            for tool_name in meta["tool"]:
                t = detector.detect_one(tool_name)
                if t and t.available:
                    detected.append(t)
        env_shim = EnvShim(detected)
        env = env_shim.get_env()

        sanitizer = LogSanitizer()
        start_time = time.time()
        raw_pub_log, raw_hid_log = _run_eda_tools(meta, eval_workspace, env, timeout)
        wall_time = time.time() - start_time

        san_pub_log = sanitizer.sanitize(raw_pub_log)
        san_hid_log = sanitizer.sanitize(raw_hid_log)

        # === PHASE 3: Score using evaluator ===
        if not clean:
            # Anti-cheat violation: force score to 0
            score_result = ScoreResult(
                task_id=task_id,
                track=meta["track"],
                mode="agentic",
                total_score=0.0,
                max_possible=1.0,
                components=[],
                passed=False,
                passing_threshold=0.5,
                evaluation_time_sec=wall_time,
                anti_cheat={
                    "forbidden_files_modified": True,
                    "checked_files": files_spec.get("forbidden", []),
                    "hash_mismatches": violations,
                },
                resource_usage={"wall_time_sec": round(wall_time, 2)},
                metadata={
                    "difficulty": meta["difficulty"],
                    "data_type": meta["data_type"],
                    "tool": meta["tool"],
                    "version": meta.get("version", "1.0.0"),
                    "agent_cmd": agent_cmd,
                    "agent_exit_code": agent_result.return_code,
                    "agent_timed_out": agent_result.timed_out,
                },
                objective_score=0.0,
                explanation_score=0.0,
            )
        else:
            evaluator = _select_evaluator(meta, task_path)
            combined_log = raw_pub_log + "\n" + raw_hid_log
            log_map = {
                "compile": combined_log,
                "public_test": raw_pub_log,
                "hidden_test": raw_hid_log,
                "explanation": combined_log,
                "tool_run": combined_log,
                "output_generated": combined_log,
                "public_metric": raw_pub_log,
                "hidden_metric": raw_hid_log,
            }
            # P2 TB/SVA: extract per-section logs
            if meta.get("track") in ("p2_rtl_gen", "p2_tb_sva_gen"):
                sections = _extract_p2_log_sections(raw_hid_log)
                log_map["golden_pass"] = raw_pub_log
                log_map["mutant_1"] = sections.get("mutant_1", raw_hid_log)
                log_map["mutant_2"] = sections.get("mutant_2", raw_hid_log)

            components: list[ScoreComponent] = []
            for comp_name in meta["scoring"]["weights"]:
                comp = evaluator.evaluate_component(
                    comp_name, eval_workspace, log_map.get(comp_name, combined_log),
                    mode="submission",
                )
                components.append(comp)

            total_score = sum(c.weighted_score for c in components)
            explanation_comps = [c for c in components if c.name == "explanation"]
            objective_comps = [c for c in components if c.name != "explanation"]
            explanation_score = sum(c.weighted_score for c in explanation_comps)
            objective_score = sum(c.weighted_score for c in objective_comps)

            score_result = ScoreResult(
                task_id=task_id,
                track=meta["track"],
                mode="agentic",
                total_score=total_score,
                max_possible=1.0,
                components=components,
                passed=total_score >= 0.5,
                passing_threshold=0.5,
                evaluation_time_sec=wall_time,
                anti_cheat={
                    "forbidden_files_modified": False,
                    "checked_files": files_spec.get("forbidden", []),
                    "hash_mismatches": [],
                },
                resource_usage={"wall_time_sec": round(wall_time, 2)},
                metadata={
                    "difficulty": meta["difficulty"],
                    "data_type": meta["data_type"],
                    "tool": meta["tool"],
                    "version": meta.get("version", "1.0.0"),
                    "agent_cmd": agent_cmd,
                    "agent_exit_code": agent_result.return_code,
                    "agent_timed_out": agent_result.timed_out,
                },
                objective_score=round(objective_score, 4),
                explanation_score=round(explanation_score, 4),
            )

        # === PHASE 4: Write artifacts ===
        agentic_result = AgenticRunResult(
            task_id=task_id,
            agent_cmd=agent_cmd,
            agent_exit_code=agent_result.return_code,
            agent_wall_time_sec=agent_result.wall_time_sec,
            agent_timed_out=agent_result.timed_out,
            file_changes=changes,
            forbidden_violations=violations,
            anti_cheat_clean=clean,
            total_score=score_result.total_score,
            passed=score_result.passed,
            transcript_path=runs_dir / "transcript.jsonl",
            score_path=runs_dir / "score.json",
        )

        _write_agentic_artifacts(
            runs_dir, agent_result, changes, before_snapshot, after_snapshot,
            score_result, meta, agent_cmd,
        )

        return runs_dir, score_result, agentic_result

    finally:
        if agent_workspace is not None:
            shutil.rmtree(agent_workspace, ignore_errors=True)
        if eval_workspace is not None:
            shutil.rmtree(eval_workspace, ignore_errors=True)


def _run_agent_subprocess(
    agent_cmd: str,
    workspace: Path,
    timeout: int,
    task_path: Path,
    meta: dict,
) -> AgentSubprocessResult:
    """Run the agent command as a subprocess with EDA_* env vars."""
    env = os.environ.copy()
    env["EDA_WORKSPACE"] = str(workspace)
    env["EDA_TASK_PATH"] = str(task_path)
    env["EDA_TASK_ID"] = meta["task_id"]
    env["EDA_TIMEOUT"] = str(timeout)

    start = time.time()
    try:
        result = subprocess.run(
            agent_cmd,
            shell=True,
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        wall_time = time.time() - start
        return AgentSubprocessResult(
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            wall_time_sec=round(wall_time, 3),
            timed_out=False,
        )
    except subprocess.TimeoutExpired as e:
        wall_time = time.time() - start
        return AgentSubprocessResult(
            return_code=-1,
            stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
            stderr=e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or ""),
            wall_time_sec=round(wall_time, 3),
            timed_out=True,
        )


def _select_evaluator(meta: dict, task_path: Path):
    """Select the appropriate evaluator based on metadata."""
    evaluator_spec = meta["scoring"].get("evaluator", "rtl_debug.VCSRTLEvaluator")
    if evaluator_spec == "spice_sim.SPICESimEvaluator":
        from eda_agentbench.evaluator.spice_sim import SPICESimEvaluator
        return SPICESimEvaluator(task_path, meta)
    elif evaluator_spec == "spice_deck_debug.SPICEDeckDebugEvaluator":
        from eda_agentbench.evaluator.spice_deck_debug import SPICEDeckDebugEvaluator
        return SPICEDeckDebugEvaluator(task_path, meta)
    elif evaluator_spec == "timing_report_qa.TimingReportQAEvaluator":
        from eda_agentbench.evaluator.timing_report_qa import TimingReportQAEvaluator
        return TimingReportQAEvaluator(task_path, meta)
    elif evaluator_spec == "dc_synthesis_qa.DCSynthesisQAEvaluator":
        from eda_agentbench.evaluator.dc_synthesis_qa import DCSynthesisQAEvaluator
        return DCSynthesisQAEvaluator(task_path, meta)
    elif evaluator_spec in ("tb_sva_gen.TBSVAGenEvaluator", "rtl_gen.RTLGenEvaluator"):
        from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
        return TBSVAGenEvaluator(task_path, meta)
    elif evaluator_spec == "dc_constraint_debug.DCConstraintDebugEvaluator":
        from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
        return DCConstraintDebugEvaluator(task_path, meta)
    else:
        from eda_agentbench.evaluator.rtl_debug import VCSRTLEvaluator
        return VCSRTLEvaluator(task_path, meta)


def _run_eda_tools(
    meta: dict,
    workspace: Path,
    env: dict[str, str],
    timeout: int,
) -> tuple[str, str]:
    """Run EDA tool scripts in evaluator workspace. Returns (pub_log, hid_log)."""
    track = meta.get("track", "")
    is_p5 = track == "p5_spice_deck_debug"
    is_report_qa = track in ("p3_timing_report_qa", "p6_dc_synthesis_qa")

    if is_report_qa:
        return f"{track} QA task - no tool execution", ""

    if is_p5:
        deck_file = _find_deck_file(workspace, set(meta["files"]["editable"]))
        return _run_hspice(workspace, env, deck_file, timeout), ""

    # Standard: run public + hidden test scripts
    _, pub_log = _run_test_script(workspace, env, "run_public.sh", timeout)
    _, hid_log = _run_test_script(workspace, env, "run_hidden.sh", timeout)
    return pub_log, hid_log


def _run_test_script(work_dir: Path, env: dict[str, str], script_name: str,
                     timeout: int) -> tuple[bool, str]:
    """Run a test shell script in work_dir. Returns (success, output)."""
    script = work_dir / script_name
    if not script.is_file():
        return False, f"Script {script_name} not found"
    try:
        result = subprocess.run(
            ["bash", str(script)],
            cwd=work_dir, env=env,
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode == 0, result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Script {script_name} timed out"


def _run_hspice(work_dir: Path, env: dict[str, str], deck_file: str,
                timeout: int) -> str:
    """Run HSPICE on a deck file. Returns combined stdout+stderr."""
    if not deck_file:
        return "ERROR: No deck file found in workspace"
    hspice_cmd = env.get("EDA_HSPICE_CMD", "hspice")
    try:
        result = subprocess.run(
            [hspice_cmd, deck_file],
            cwd=work_dir, env=env,
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        return f"HSPICE timed out after {timeout}s"
    except FileNotFoundError:
        return f"ERROR: HSPICE not found at '{hspice_cmd}'"


def _find_deck_file(work_dir: Path, editable: set[str]) -> str:
    """Find the SPICE deck file name in workspace."""
    for f in editable:
        name = Path(f).name
        if (work_dir / name).is_file():
            return name
    for f in work_dir.iterdir():
        if f.suffix == ".sp":
            return f.name
    return ""


def _extract_p2_log_sections(combined_log: str) -> dict[str, str]:
    """Extract per-mutant sections from P2 hidden run log."""
    import re
    sections: dict[str, str] = {}
    parts = re.split(r"=== Mutant (\d+) ===", combined_log)
    for i in range(1, len(parts) - 1, 2):
        mutant_num = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        sections[f"mutant_{mutant_num}"] = content
    return sections


def _build_transcript(
    agent_result: AgentSubprocessResult,
    changes: dict[str, str],
    anti_cheat_clean: bool,
    violations: list[str],
    score_result: ScoreResult,
) -> list[dict]:
    """Build JSONL transcript entries from agent run results."""
    ts = datetime.now().isoformat()
    entries = [
        {"ts": ts, "type": "start", "agent_exit_code": agent_result.return_code,
         "timed_out": agent_result.timed_out, "wall_time_sec": agent_result.wall_time_sec},
        {"ts": ts, "type": "agent_stdout", "content": agent_result.stdout},
        {"ts": ts, "type": "agent_stderr", "content": agent_result.stderr},
        {"ts": ts, "type": "file_changes", "changes": changes,
         "anti_cheat_clean": anti_cheat_clean, "violations": violations},
        {"ts": ts, "type": "score", "total_score": score_result.total_score,
         "passed": score_result.passed, "mode": score_result.mode},
        {"ts": ts, "type": "end", "total_score": score_result.total_score},
    ]
    return entries


def _write_agentic_artifacts(
    runs_dir: Path,
    agent_result: AgentSubprocessResult,
    changes: dict[str, str],
    before_snapshot: dict[str, str],
    after_snapshot: dict[str, str],
    score_result: ScoreResult,
    meta: dict,
    agent_cmd: str,
) -> None:
    """Write all output artifacts to runs_dir."""
    # transcript.jsonl
    transcript = _build_transcript(
        agent_result, changes,
        score_result.anti_cheat.get("forbidden_files_modified", True) is False,
        score_result.anti_cheat.get("hash_mismatches", []),
        score_result,
    )
    with open(runs_dir / "transcript.jsonl", "w") as f:
        for entry in transcript:
            f.write(json.dumps(entry) + "\n")

    # stdout.log / stderr.log
    (runs_dir / "stdout.log").write_text(agent_result.stdout)
    (runs_dir / "stderr.log").write_text(agent_result.stderr)

    # score.json
    (runs_dir / "score.json").write_text(json.dumps(score_result.to_dict(), indent=2))

    # workspace_manifest.json — agent-visible files only
    manifest = {"before": before_snapshot, "after": after_snapshot}
    (runs_dir / "workspace_manifest.json").write_text(json.dumps(manifest, indent=2))

    # modified_files.json
    modified = {
        "changes": changes,
        "forbidden_violations": score_result.anti_cheat.get("hash_mismatches", []),
    }
    (runs_dir / "modified_files.json").write_text(json.dumps(modified, indent=2))

    # metadata.json
    run_meta = {
        "task_id": meta["task_id"],
        "track": meta["track"],
        "agent_cmd": agent_cmd,
        "timeout": meta.get("timeout_sec", 300),
        "mode": "agentic",
        "timestamp": datetime.now().isoformat(),
    }
    (runs_dir / "metadata.json").write_text(json.dumps(run_meta, indent=2))
