"""CLI entry point for eda-bench."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from eda_agentbench.config import RUNS_ROOT
from eda_agentbench.types import ScoreResult, ScoreComponent


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="eda-bench", description="EDA-AgentBench benchmark CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # detect-tools
    p_det = sub.add_parser("detect-tools", help="Detect installed EDA tools")
    p_det.add_argument("--format", choices=["table", "json"], default="table")
    p_det.add_argument("--require", default=None, help="Comma-separated tool names to require")

    # validate-task
    p_val = sub.add_parser("validate-task", help="Validate a task directory")
    p_val.add_argument("task", help="Task directory path")

    # evaluate-task
    p_eval = sub.add_parser("evaluate-task", help="Evaluate a submission against a task")
    p_eval.add_argument("task", help="Task directory path")
    p_eval.add_argument("--submission", required=True, help="Submission directory (contains editable files)")
    p_eval.add_argument("--timeout", type=int, default=None, help="Override timeout in seconds")
    p_eval.add_argument("--verbose", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "detect-tools":
        cmd_detect_tools(args)
    elif args.command == "validate-task":
        cmd_validate_task(args)
    elif args.command == "evaluate-task":
        cmd_evaluate_task(args)


def cmd_detect_tools(args) -> None:
    from eda_agentbench.tools.detector import ToolEnvironmentDetector
    detector = ToolEnvironmentDetector()
    tools = detector.detect_all()

    if args.require:
        required = set(args.require.split(","))
    else:
        required = set()

    if args.format == "json":
        out = []
        for t in tools:
            out.append({"name": t.name, "vendor": t.vendor, "version": t.version,
                        "binary": str(t.binary_path), "available": t.available})
        print(json.dumps(out, indent=2))
    else:
        print(f"{'Tool':<12} {'Vendor':<8} {'Version':<20} {'Available':<10} {'Binary'}")
        print("-" * 80)
        for t in tools:
            status = "YES" if t.available else "NO"
            print(f"{t.name:<12} {t.vendor:<8} {t.version:<20} {status:<10} {t.binary_path}")

    missing = required - {t.name for t in tools if t.available}
    if missing:
        print(f"\nERROR: Required tools not found: {', '.join(sorted(missing))}", file=sys.stderr)
        sys.exit(1)


def cmd_validate_task(args) -> None:
    from eda_agentbench.task.loader import TaskLoader, TaskValidationError
    task_path = Path(args.task)
    if not task_path.is_dir():
        print(f"ERROR: Task directory not found: {task_path}", file=sys.stderr)
        sys.exit(1)

    loader = TaskLoader(Path("."))
    try:
        meta = loader.load(task_path)
        print(f"Task {meta['task_id']} ({meta['track']}): VALID")
        print(f"  Tool: {meta['tool']}")
        print(f"  Difficulty: {meta['difficulty']}")
        print(f"  Data type: {meta['data_type']}")
        print(f"  Visible files: {meta['files']['visible']}")
        print(f"  Editable files: {meta['files']['editable']}")
        print(f"  Forbidden files: {meta['files']['forbidden']}")
        print(f"  Scoring weights: {meta['scoring']['weights']}")
    except TaskValidationError as e:
        print(f"INVALID: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_evaluate_task(args) -> None:
    from eda_agentbench.task.loader import TaskLoader, TaskValidationError
    from eda_agentbench.task.validator import check_submission_forbidden
    from eda_agentbench.tools.detector import ToolEnvironmentDetector
    from eda_agentbench.tools.env_shim import EnvShim
    from eda_agentbench.anti_cheat.guard import ForbiddenModificationGuard
    from eda_agentbench.sanitizer.log_sanitizer import LogSanitizer
    from eda_agentbench.evaluator.rtl_debug import VCSRTLEvaluator, run_vcs_compile, run_vcs_sim

    task_path = Path(args.task).resolve()
    submission_path = Path(args.submission).resolve()

    if not task_path.is_dir():
        print(f"ERROR: Task directory not found: {task_path}", file=sys.stderr)
        sys.exit(1)
    if not submission_path.is_dir():
        print(f"ERROR: Submission directory not found: {submission_path}", file=sys.stderr)
        sys.exit(1)

    # Load task
    loader = TaskLoader(Path("."))
    try:
        meta = loader.load(task_path)
    except TaskValidationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    task_id = meta["task_id"]
    files_spec = meta["files"]
    timeout = args.timeout or meta.get("timeout_sec", 300)

    # Anti-cheat: check submission doesn't contain forbidden files
    violations = check_submission_forbidden(submission_path, files_spec["forbidden"])
    if violations:
        print(f"ANTI-CHEAT FAIL: Submission contains forbidden files: {violations}", file=sys.stderr)
        # Write a failing score and exit
        _write_anticheat_fail(task_path, meta, violations)
        sys.exit(1)

    # Detect tools
    detector = ToolEnvironmentDetector()
    required_tools = meta["tool"]
    detected = []
    for tool_name in required_tools:
        t = detector.detect_one(tool_name)
        if t and t.available:
            detected.append(t)
        else:
            print(f"ERROR: Required tool '{tool_name}' not available", file=sys.stderr)
            sys.exit(1)

    env_shim = EnvShim(detected)
    env = env_shim.get_env()

    # Create temp workspace
    work_dir = Path(tempfile.mkdtemp(prefix="eda_bench_"))
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    runs_dir = RUNS_ROOT / task_id / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Copy visible files to workspace
        src_files = task_path / "files"
        if src_files.is_dir():
            shutil.copytree(src_files, work_dir, dirs_exist_ok=True)

        # Copy submission editable files into workspace (overwrite)
        editable = set(files_spec["editable"])
        for f in editable:
            src = submission_path / f
            if src.is_file():
                shutil.copy2(src, work_dir / f)
            elif src.is_file() is False and not (work_dir / f).is_file():
                print(f"WARNING: Editable file '{f}' not in submission and not in task files/", file=sys.stderr)

        # Copy hidden files into workspace (for evaluator, not visible to agent)
        src_hidden = task_path / "hidden"
        if src_hidden.is_dir():
            shutil.copytree(src_hidden, work_dir, dirs_exist_ok=True)

        # Snapshot forbidden files for anti-cheat
        guard = ForbiddenModificationGuard()
        guard.snapshot(task_path / "files", [f for f in files_spec["forbidden"] if "/" not in f])
        guard.snapshot(task_path / "hidden", [f for f in files_spec["forbidden"] if "/" not in f])
        # Also snapshot forbidden files in work_dir
        guard.snapshot(work_dir, files_spec["forbidden"])

        sanitizer = LogSanitizer()
        start_time = time.time()

        # Run public test
        print("Running public test...")
        pub_ok, pub_log = _run_test_script(work_dir, env, "run_public.sh", timeout)
        raw_pub_log = pub_log
        san_pub_log = sanitizer.sanitize(pub_log)

        # Run hidden test
        print("Running hidden test...")
        hid_ok, hid_log = _run_test_script(work_dir, env, "run_hidden.sh", timeout)
        raw_hid_log = hid_log
        san_hid_log = sanitizer.sanitize(hid_log)

        wall_time = time.time() - start_time

        # Anti-cheat verification
        clean, mismatches = guard.verify(work_dir)

        # Save logs
        (runs_dir / "raw_public.log").write_text(raw_pub_log)
        (runs_dir / "raw_hidden.log").write_text(raw_hid_log)
        (runs_dir / "sanitized_public.log").write_text(san_pub_log)
        (runs_dir / "sanitized_hidden.log").write_text(san_hid_log)

        # Select evaluator based on metadata
        evaluator_spec = meta["scoring"].get("evaluator", "rtl_debug.VCSRTLEvaluator")
        if evaluator_spec == "spice_sim.SPICESimEvaluator":
            from eda_agentbench.evaluator.spice_sim import SPICESimEvaluator
            evaluator = SPICESimEvaluator(task_path, meta)
        else:
            from eda_agentbench.evaluator.rtl_debug import VCSRTLEvaluator
            evaluator = VCSRTLEvaluator(task_path, meta)
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

        components: list[ScoreComponent] = []
        for comp_name in meta["scoring"]["weights"]:
            comp = evaluator.evaluate_component(comp_name, work_dir, log_map.get(comp_name, combined_log), mode="submission")
            components.append(comp)

        total_score = sum(c.weighted_score for c in components)

        # Separate objective and explanation scores
        explanation_weight = meta["scoring"].get("explanation_weight", 0.0)
        explanation_comps = [c for c in components if c.name == "explanation"]
        objective_comps = [c for c in components if c.name != "explanation"]
        explanation_score = sum(c.weighted_score for c in explanation_comps)
        objective_score = sum(c.weighted_score for c in objective_comps)

        score_result = ScoreResult(
            task_id=task_id,
            track=meta["track"],
            mode="submission",
            total_score=total_score,
            max_possible=1.0,
            components=components,
            passed=total_score >= 0.5,
            passing_threshold=0.5,
            evaluation_time_sec=wall_time,
            anti_cheat={
                "forbidden_files_modified": not clean,
                "checked_files": files_spec["forbidden"],
                "hash_mismatches": mismatches,
            },
            resource_usage={"wall_time_sec": round(wall_time, 2)},
            metadata={
                "difficulty": meta["difficulty"],
                "data_type": meta["data_type"],
                "tool": meta["tool"],
                "version": meta.get("version", "1.0.0"),
            },
            objective_score=round(objective_score, 4),
            explanation_score=round(explanation_score, 4),
        )

        # Write score JSON
        score_path = runs_dir / "score.json"
        score_path.write_text(json.dumps(score_result.to_dict(), indent=2))
        print(f"\nScore: {total_score:.2f} / 1.00 {'(PASS)' if score_result.passed else '(FAIL)'}")
        print(f"  objective_score:   {objective_score:.4f}")
        print(f"  explanation_score: {explanation_score:.4f}")
        for c in components:
            print(f"  {c.name}: {c.raw_score:.2f} * {c.weight:.2f} = {c.weighted_score:.4f} — {c.details}")
        print(f"\nScore written to: {score_path}")
        print(f"Logs written to:  {runs_dir}/")

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


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


def _write_anticheat_fail(task_path: Path, meta: dict, violations: list[str]) -> None:
    """Write a score.json indicating anti-cheat failure."""
    from eda_agentbench.types import ScoreResult
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    runs_dir = RUNS_ROOT / meta["task_id"] / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    score = ScoreResult(
        task_id=meta["task_id"], track=meta["track"], mode="submission",
        total_score=0.0, max_possible=1.0, components=[], passed=False,
        passing_threshold=0.5, evaluation_time_sec=0.0,
        anti_cheat={"forbidden_files_modified": True, "checked_files": violations, "hash_mismatches": violations},
        resource_usage={}, metadata={},
        objective_score=0.0, explanation_score=0.0,
    )
    (runs_dir / "score.json").write_text(json.dumps(score.to_dict(), indent=2))
