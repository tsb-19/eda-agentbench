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

    # evaluate-dataset
    p_ds = sub.add_parser("evaluate-dataset", help="Evaluate all tasks in a dataset")
    p_ds.add_argument("tasks_root", help="Root directory containing task tracks")
    p_ds.add_argument("--submission-mode", choices=["solution", "buggy"], default="solution",
                       help="Submission strategy: solution/ or files/ (buggy)")
    p_ds.add_argument("--track", default=None, help="Filter by track (e.g., p1_rtl_debug)")
    p_ds.add_argument("--timeout", type=int, default=None, help="Override timeout per task")
    p_ds.add_argument("--run-id", default=None, help="Custom run ID (default: dataset_<timestamp>)")
    p_ds.add_argument("--limit", type=int, default=None,
                       help="Evaluate at most N tasks total")
    p_ds.add_argument("--sample-per-track", type=int, default=None,
                       help="Evaluate at most N tasks per track")
    p_ds.add_argument("--seed", type=int, default=42,
                       help="Deterministic sampling seed (default: 42)")

    # report
    p_rep = sub.add_parser("report", help="Generate report from evaluation results")
    p_rep.add_argument("runs_dir", help="Runs directory to report on")
    p_rep.add_argument("--format", choices=["terminal", "json", "markdown", "all"], default="all")
    p_rep.add_argument("--output", default=None, help="Output directory for report files")

    # run-agent
    p_ra = sub.add_parser("run-agent", help="Run an external agent against a task")
    p_ra.add_argument("task", help="Task directory path")
    p_ra.add_argument("--agent-cmd", required=True,
                       help="Agent command to execute (receives EDA_WORKSPACE env var)")
    p_ra.add_argument("--timeout", type=int, default=None,
                       help="Override timeout in seconds")
    p_ra.add_argument("--run-id", default=None,
                       help="Custom run ID (default: agentic_<timestamp>)")
    p_ra.add_argument("--output-dir", default=None,
                       help="Override output runs root directory")

    # run-agent-dataset
    p_rad = sub.add_parser("run-agent-dataset",
                            help="Run agent against a sampled dataset")
    p_rad.add_argument("tasks_root", help="Root directory containing task tracks")
    p_rad.add_argument("--agent-cmd", required=True, help="Agent command to execute")
    p_rad.add_argument("--track", default=None, help="Filter by track")
    p_rad.add_argument("--timeout", type=int, default=None, help="Override timeout per task")
    p_rad.add_argument("--run-id", default=None, help="Custom run ID")
    p_rad.add_argument("--sample-per-track", type=int, default=None,
                        help="Sample N tasks per track")
    p_rad.add_argument("--limit", type=int, default=None,
                        help="Evaluate at most N tasks total")
    p_rad.add_argument("--seed", type=int, default=42, help="Sampling seed (default: 42)")

    args = parser.parse_args(argv)

    if args.command == "detect-tools":
        cmd_detect_tools(args)
    elif args.command == "validate-task":
        cmd_validate_task(args)
    elif args.command == "evaluate-task":
        cmd_evaluate_task(args)
    elif args.command == "evaluate-dataset":
        cmd_evaluate_dataset(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "run-agent":
        cmd_run_agent(args)
    elif args.command == "run-agent-dataset":
        cmd_run_agent_dataset(args)


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
        if meta.get("expected_error_category"):
            print(f"  Expected error: {meta['expected_error_category']}")
    except TaskValidationError as e:
        print(f"INVALID: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_evaluate_task(args) -> None:
    from eda_agentbench.task.loader import TaskLoader, TaskValidationError

    task_path = Path(args.task).resolve()
    submission_path = Path(args.submission).resolve()

    if not task_path.is_dir():
        print(f"ERROR: Task directory not found: {task_path}", file=sys.stderr)
        sys.exit(1)
    if not submission_path.is_dir():
        print(f"ERROR: Submission directory not found: {submission_path}", file=sys.stderr)
        sys.exit(1)

    loader = TaskLoader(Path("."))
    try:
        meta = loader.load(task_path)
    except TaskValidationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    timeout = args.timeout or meta.get("timeout_sec", 300)

    try:
        runs_dir, score_result = _evaluate_single(task_path, submission_path, meta, timeout)
    except RuntimeError as e:
        print(f"ANTI-CHEAT FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nScore: {score_result.total_score:.2f} / 1.00 {'(PASS)' if score_result.passed else '(FAIL)'}")
    print(f"  objective_score:   {score_result.objective_score:.4f}")
    print(f"  explanation_score: {score_result.explanation_score:.4f}")
    for c in score_result.components:
        print(f"  {c.name}: {c.raw_score:.2f} * {c.weight:.2f} = {c.weighted_score:.4f} — {c.details}")
    print(f"\nScore written to: {runs_dir / 'score.json'}")
    print(f"Logs written to:  {runs_dir}/")


def cmd_run_agent(args) -> None:
    """Run an external agent against a single task."""
    from eda_agentbench.task.loader import TaskLoader, TaskValidationError
    from eda_agentbench.agentic.runner import run_single_agentic

    task_path = Path(args.task).resolve()
    if not task_path.is_dir():
        print(f"ERROR: Task directory not found: {task_path}", file=sys.stderr)
        sys.exit(1)

    loader = TaskLoader(Path("."))
    try:
        meta = loader.load(task_path)
    except TaskValidationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    timeout = args.timeout or meta.get("timeout_sec", 300)
    runs_root = Path(args.output_dir).resolve() if args.output_dir else None

    try:
        runs_dir, score_result, agentic_result = run_single_agentic(
            task_path, args.agent_cmd, meta, timeout, runs_root=runs_root,
        )
    except RuntimeError as e:
        print(f"AGENT RUN FAILED: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nAgent: {args.agent_cmd}")
    print(f"Agent exit code: {agentic_result.agent_exit_code}")
    print(f"Agent wall time: {agentic_result.agent_wall_time_sec:.1f}s")
    print(f"Files changed: {len(agentic_result.file_changes)}")
    for path, change_type in sorted(agentic_result.file_changes.items()):
        print(f"  {change_type}: {path}")
    if not agentic_result.anti_cheat_clean:
        print(f"  ANTI-CHEAT VIOLATIONS: {agentic_result.forbidden_violations}")
    print(f"\nScore: {score_result.total_score:.2f} / 1.00 "
          f"{'(PASS)' if score_result.passed else '(FAIL)'}")
    for c in score_result.components:
        print(f"  {c.name}: {c.raw_score:.2f} * {c.weight:.2f} = "
              f"{c.weighted_score:.4f} — {c.details}")
    print(f"\nArtifacts written to: {runs_dir}/")


def cmd_run_agent_dataset(args) -> None:
    """Run agent against a sampled dataset."""
    import random
    from eda_agentbench.task.loader import TaskLoader, TaskValidationError
    from eda_agentbench.agentic.runner import run_single_agentic

    tasks_root = Path(args.tasks_root).resolve()
    if not tasks_root.is_dir():
        print(f"ERROR: Tasks root not found: {tasks_root}", file=sys.stderr)
        sys.exit(1)

    track_filter = args.track
    timeout_override = args.timeout
    limit = args.limit
    sample_per_track = args.sample_per_track
    seed = args.seed
    run_id = args.run_id or f"agentic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    dataset_runs_root = RUNS_ROOT / run_id

    # Discover tasks
    loader = TaskLoader(tasks_root)
    task_paths = loader.discover(track=track_filter, recursive=True)
    if not task_paths:
        print(f"ERROR: No tasks found under {tasks_root}", file=sys.stderr)
        sys.exit(1)

    total_candidates = len(task_paths)

    # Apply sampling (same logic as cmd_evaluate_dataset)
    sampled = sample_per_track is not None or limit is not None
    selected_task_ids: list[str] = []

    if sample_per_track is not None:
        by_track: dict[str, list[Path]] = {}
        for tp in task_paths:
            try:
                meta = loader.load(tp)
                track = meta.get("track", "unknown")
            except TaskValidationError:
                track = "unknown"
            by_track.setdefault(track, []).append(tp)

        rng = random.Random(seed)
        sampled_paths: list[Path] = []
        for track in sorted(by_track):
            candidates = by_track[track]
            n = min(sample_per_track, len(candidates))
            selected = rng.sample(candidates, n)
            sampled_paths.extend(selected)
        task_paths = sampled_paths
    elif limit is not None:
        rng = random.Random(seed)
        shuffled = list(task_paths)
        rng.shuffle(shuffled)
        task_paths = shuffled[:limit]

    for tp in task_paths:
        try:
            meta = loader.load(tp)
            selected_task_ids.append(meta.get("task_id", tp.name))
        except TaskValidationError:
            selected_task_ids.append(tp.name)

    print(f"=== Agentic Dataset Evaluation ===")
    print(f"  Tasks root:      {tasks_root}")
    print(f"  Agent cmd:       {args.agent_cmd}")
    print(f"  Track filter:    {track_filter or 'all'}")
    print(f"  Run ID:          {run_id}")
    print(f"  Total candidates: {total_candidates}")
    print(f"  Tasks selected:  {len(task_paths)}")
    print()

    results: list[dict] = []
    for i, task_path in enumerate(task_paths):
        try:
            meta = loader.load(task_path)
        except TaskValidationError as e:
            print(f"[{i+1}/{len(task_paths)}] SKIP {task_path.name}: {e}")
            results.append({
                "task_path": str(task_path), "task_id": task_path.name,
                "status": "error", "reason": str(e),
            })
            continue

        task_id = meta["task_id"]
        timeout = timeout_override or meta.get("timeout_sec", 300)

        print(f"[{i+1}/{len(task_paths)}] {task_id} (agentic)...", end=" ", flush=True)

        try:
            runs_dir, score_result, agentic_result = run_single_agentic(
                task_path, args.agent_cmd, meta, timeout, runs_root=dataset_runs_root,
            )
            status = "pass" if score_result.passed else "fail"
            print(f"{score_result.total_score:.2f} {'PASS' if score_result.passed else 'FAIL'}")
            results.append({
                "task_path": str(task_path),
                "task_id": task_id,
                "track": meta["track"],
                "tool": meta["tool"],
                "difficulty": meta["difficulty"],
                "status": status,
                "total_score": score_result.total_score,
                "objective_score": score_result.objective_score,
                "explanation_score": score_result.explanation_score,
                "components": [c.to_dict() for c in score_result.components],
                "score_path": str(runs_dir / "score.json"),
            })
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "task_path": str(task_path),
                "task_id": task_id,
                "track": meta.get("track", "unknown"),
                "tool": meta.get("tool", []),
                "difficulty": meta.get("difficulty", "unknown"),
                "status": "error",
                "reason": str(e),
            })

    # Write summary
    summary = _build_dataset_summary(
        results, run_id, "agentic", track_filter,
        sampled=sampled, sample_per_track=sample_per_track,
        limit=limit, seed=seed,
        total_candidates=total_candidates,
        selected_task_ids=selected_task_ids,
    )
    summary_path = dataset_runs_root / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))

    print(f"\n=== Agentic Dataset Summary ===")
    print(f"  Total:       {summary['total']}")
    print(f"  Evaluated:   {summary['evaluated']}")
    print(f"  Passed:      {summary['passed']}")
    print(f"  Failed:      {summary['failed']}")
    print(f"  Errors:      {summary['errors']}")
    print(f"  Avg score:   {summary['avg_score']:.4f}")
    print(f"\nSummary written to: {summary_path}")


def _safe_rmtree(path: Path) -> None:
    """Remove a temp directory robustly.

    EDA tools (e.g. VCS ``simv.daidir/``) can leave read-only files or dirs that
    defeat ``shutil.rmtree``; the old ``rmtree(ignore_errors=True)`` would then
    silently leak the directory under ``/tmp``. Retry after making each offending
    entry writable, and if the directory still survives, warn rather than leak
    silently.
    """
    import os
    import stat

    def _onerror(func, p, _exc):
        try:
            os.chmod(p, stat.S_IRWXU)
            func(p)
        except OSError:
            pass

    shutil.rmtree(path, onerror=_onerror)
    if Path(path).exists():
        print(f"warning: could not fully remove temp dir {path}", file=sys.stderr)


def _evaluate_single(task_path: Path, submission_path: Path, meta: dict,
                      timeout: int, runs_root: Path | None = None) -> tuple[Path, ScoreResult]:
    """Core evaluation logic. Returns (runs_dir, ScoreResult).

    Args:
        task_path: Path to the task directory.
        submission_path: Path to the submission directory.
        meta: Loaded task metadata dict.
        timeout: Timeout in seconds.
        runs_root: Override for runs output root (default: RUNS_ROOT).
    """
    from eda_agentbench.task.validator import check_submission_forbidden, check_tcl_injection
    from eda_agentbench.tools.detector import ToolEnvironmentDetector
    from eda_agentbench.tools.env_shim import EnvShim
    from eda_agentbench.anti_cheat.guard import ForbiddenModificationGuard
    from eda_agentbench.sanitizer.log_sanitizer import LogSanitizer

    task_id = meta["task_id"]
    files_spec = meta["files"]
    runs_base = runs_root or RUNS_ROOT

    # Anti-cheat: check submission doesn't contain forbidden files
    violations = check_submission_forbidden(submission_path, files_spec["forbidden"])
    if violations:
        _write_anticheat_fail(task_path, meta, violations, runs_base)
        raise RuntimeError(f"Anti-cheat fail: submission contains forbidden files: {violations}")

    # Anti-cheat: an editable .sdc/.tcl must not carry Tcl that subverts a grader
    # which sources it (e.g. `proc incr {} {}` to forge CONSTRAINTS_OK).
    tcl_violations = check_tcl_injection(submission_path, files_spec.get("editable", []))
    if tcl_violations:
        _write_anticheat_fail(task_path, meta, tcl_violations, runs_base)
        raise RuntimeError(f"Anti-cheat fail: editable file contains forbidden TCL: {tcl_violations}")

    is_p3 = meta.get("track") == "p3_timing_report_qa"
    is_p6 = meta.get("track") == "p6_dc_synthesis_qa"
    is_p8 = meta.get("track") == "p8_pnr_report_qa"
    is_report_qa = is_p3 or is_p6 or is_p8

    # Detect tools (skip for report QA tasks which don't need EDA tools)
    detector = ToolEnvironmentDetector()
    required_tools = meta["tool"]
    detected = []
    for tool_name in required_tools:
        t = detector.detect_one(tool_name)
        if t and t.available:
            detected.append(t)
        elif not is_report_qa:
            raise RuntimeError(f"Required tool '{tool_name}' not available")

    env_shim = EnvShim(detected)
    env = env_shim.get_env()

    # Create temp workspace
    work_dir = Path(tempfile.mkdtemp(prefix="eda_bench_"))
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    runs_dir = runs_base / task_id / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    try:
        is_p5 = meta.get("track") == "p5_spice_deck_debug"

        # Copy visible files to workspace
        if is_p5:
            # P5 tasks use visible/ layout (not files/)
            src_visible = task_path / "visible"
            if src_visible.is_dir():
                shutil.copytree(src_visible, work_dir, dirs_exist_ok=True)
        else:
            src_files = task_path / "files"
            if src_files.is_dir():
                shutil.copytree(src_files, work_dir, dirs_exist_ok=True)

        # Copy submission editable files into workspace (overwrite)
        editable = set(files_spec["editable"])
        if is_p5:
            # P5: submission replaces the editable deck file in workspace.
            # Find the .sp file in submission and copy it to replace the editable file.
            edit_name = Path(next(iter(editable))).name  # e.g., spice_deck_debug_0001_bug.sp
            sub_files = list(submission_path.glob("*.sp"))
            if sub_files:
                shutil.copy2(sub_files[0], work_dir / edit_name)
        else:
            for f in editable:
                src = submission_path / f
                if src.is_file():
                    shutil.copy2(src, work_dir / f)

        # Copy hidden files into workspace (for evaluator, not visible to agent)
        src_hidden = task_path / "hidden"
        if src_hidden.is_dir():
            shutil.copytree(src_hidden, work_dir, dirs_exist_ok=True)

        # Snapshot forbidden files for anti-cheat
        guard = ForbiddenModificationGuard()
        if is_p5:
            guard.snapshot(work_dir, files_spec["forbidden"])
        else:
            guard.snapshot(task_path / "files", [f for f in files_spec["forbidden"] if "/" not in f])
            guard.snapshot(task_path / "hidden", [f for f in files_spec["forbidden"] if "/" not in f])
            guard.snapshot(work_dir, files_spec["forbidden"])

        sanitizer = LogSanitizer()
        start_time = time.time()

        if is_p5:
            # P5: run HSPICE directly on the deck file
            deck_file = _find_deck_file(work_dir, editable)
            run_log = _run_hspice(work_dir, env, deck_file, timeout)
            raw_pub_log = run_log
            raw_hid_log = ""
            san_pub_log = sanitizer.sanitize(run_log)
            san_hid_log = ""
        elif is_p3 or is_p6 or is_p8:
            # P3/P6/P8: no tool execution needed, just evaluate answer file
            raw_pub_log = f"{meta['track']} QA task - no tool execution"
            raw_hid_log = ""
            san_pub_log = raw_pub_log
            san_hid_log = ""
        else:
            # Standard: run public/hidden test scripts
            pub_ok, pub_log = _run_test_script(work_dir, env, "run_public.sh", timeout)
            raw_pub_log = pub_log
            san_pub_log = sanitizer.sanitize(pub_log)
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
        elif evaluator_spec == "spice_deck_debug.SPICEDeckDebugEvaluator":
            from eda_agentbench.evaluator.spice_deck_debug import SPICEDeckDebugEvaluator
            evaluator = SPICEDeckDebugEvaluator(task_path, meta)
        elif evaluator_spec == "timing_report_qa.TimingReportQAEvaluator":
            from eda_agentbench.evaluator.timing_report_qa import TimingReportQAEvaluator
            evaluator = TimingReportQAEvaluator(task_path, meta)
        elif evaluator_spec == "dc_synthesis_qa.DCSynthesisQAEvaluator":
            from eda_agentbench.evaluator.dc_synthesis_qa import DCSynthesisQAEvaluator
            evaluator = DCSynthesisQAEvaluator(task_path, meta)
        elif evaluator_spec in ("tb_sva_gen.TBSVAGenEvaluator", "rtl_gen.RTLGenEvaluator"):
            from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator
            evaluator = TBSVAGenEvaluator(task_path, meta)
        elif evaluator_spec == "dc_constraint_debug.DCConstraintDebugEvaluator":
            from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
            evaluator = DCConstraintDebugEvaluator(task_path, meta)
        elif evaluator_spec == "spyglass_lint_debug.SpyGlassLintDebugEvaluator":
            from eda_agentbench.evaluator.spyglass_lint_debug import SpyGlassLintDebugEvaluator
            evaluator = SpyGlassLintDebugEvaluator(task_path, meta)
        elif evaluator_spec == "primetime_sta_debug.PrimeTimeSTADebugEvaluator":
            from eda_agentbench.evaluator.primetime_sta_debug import PrimeTimeSTADebugEvaluator
            evaluator = PrimeTimeSTADebugEvaluator(task_path, meta)
        elif evaluator_spec == "pnr_report_qa.PnRReportQAEvaluator":
            from eda_agentbench.evaluator.pnr_report_qa import PnRReportQAEvaluator
            evaluator = PnRReportQAEvaluator(task_path, meta)
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
        # P2 TB/SVA: extract per-section logs from hidden log
        if meta.get("track") in ("p2_rtl_gen", "p2_tb_sva_gen"):
            sections = _extract_p2_log_sections(raw_hid_log)
            log_map["golden_pass"] = raw_pub_log
            log_map["mutant_1"] = sections.get("mutant_1", raw_hid_log)
            log_map["mutant_2"] = sections.get("mutant_2", raw_hid_log)

        components: list[ScoreComponent] = []
        for comp_name in meta["scoring"]["weights"]:
            comp = evaluator.evaluate_component(comp_name, work_dir, log_map.get(comp_name, combined_log), mode="submission")
            components.append(comp)

        total_score = sum(c.weighted_score for c in components)

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

        score_path = runs_dir / "score.json"
        score_path.write_text(json.dumps(score_result.to_dict(), indent=2))
        return runs_dir, score_result

    finally:
        _safe_rmtree(work_dir)


def cmd_evaluate_dataset(args) -> None:
    import random
    from eda_agentbench.task.loader import TaskLoader, TaskValidationError

    tasks_root = Path(args.tasks_root).resolve()
    if not tasks_root.is_dir():
        print(f"ERROR: Tasks root not found: {tasks_root}", file=sys.stderr)
        sys.exit(1)

    submission_mode = args.submission_mode
    track_filter = args.track
    timeout_override = args.timeout
    limit = args.limit
    sample_per_track = args.sample_per_track
    seed = args.seed
    run_id = args.run_id or f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    dataset_runs_root = RUNS_ROOT / run_id

    # Discover tasks
    loader = TaskLoader(tasks_root)
    task_paths = loader.discover(track=track_filter, recursive=True)
    if not task_paths:
        print(f"ERROR: No tasks found under {tasks_root}", file=sys.stderr)
        sys.exit(1)

    total_candidates = len(task_paths)

    # Apply sampling if requested
    sampled = sample_per_track is not None or limit is not None
    selected_task_ids: list[str] = []

    if sample_per_track is not None:
        # Group by track, sample N per track
        by_track: dict[str, list[Path]] = {}
        for tp in task_paths:
            try:
                meta = loader.load(tp)
                track = meta.get("track", "unknown")
            except TaskValidationError:
                track = "unknown"
            by_track.setdefault(track, []).append(tp)

        rng = random.Random(seed)
        sampled_paths: list[Path] = []
        for track in sorted(by_track):
            candidates = by_track[track]
            n = min(sample_per_track, len(candidates))
            selected = rng.sample(candidates, n)
            sampled_paths.extend(selected)
        task_paths = sampled_paths
    elif limit is not None:
        # Global limit with deterministic shuffle
        rng = random.Random(seed)
        shuffled = list(task_paths)
        rng.shuffle(shuffled)
        task_paths = shuffled[:limit]

    # Collect selected task IDs for report
    for tp in task_paths:
        try:
            meta = loader.load(tp)
            selected_task_ids.append(meta.get("task_id", tp.name))
        except TaskValidationError:
            selected_task_ids.append(tp.name)

    print(f"=== Dataset Evaluation ===")
    print(f"  Tasks root:      {tasks_root}")
    print(f"  Submission mode: {submission_mode}")
    print(f"  Track filter:    {track_filter or 'all'}")
    print(f"  Run ID:          {run_id}")
    print(f"  Total candidates: {total_candidates}")
    if sampled:
        print(f"  Sampled:         YES (seed={seed})")
        if sample_per_track is not None:
            print(f"  Sample per track: {sample_per_track}")
        if limit is not None:
            print(f"  Limit:           {limit}")
    else:
        print(f"  Sampled:         NO (full evaluation)")
    print(f"  Tasks selected:  {len(task_paths)}")
    print()

    results: list[dict] = []
    for i, task_path in enumerate(task_paths):
        # Load task metadata first (need editable list for buggy mode)
        try:
            meta = loader.load(task_path)
        except TaskValidationError as e:
            print(f"[{i+1}/{len(task_paths)}] SKIP {task_path.name}: {e}")
            results.append({
                "task_path": str(task_path),
                "task_id": task_path.name,
                "status": "error",
                "reason": str(e),
            })
            continue

        task_id = meta["task_id"]
        timeout = timeout_override or meta.get("timeout_sec", 300)

        # Determine submission path
        is_p5 = meta.get("track") == "p5_spice_deck_debug"
        is_p3 = meta.get("track") == "p3_timing_report_qa"
        is_p6 = meta.get("track") == "p6_dc_synthesis_qa"
        if submission_mode == "solution":
            if is_p5:
                # P5: solution is hidden/ (the fixed deck)
                submission_path = task_path / "hidden"
            else:
                submission_path = task_path / "solution"
            if not submission_path.is_dir():
                label = "hidden/" if is_p5 else "solution/"
                print(f"[{i+1}/{len(task_paths)}] SKIP {task_path.name}: {label} not found")
                results.append({
                    "task_path": str(task_path), "task_id": task_id,
                    "track": meta["track"], "tool": meta["tool"],
                    "difficulty": meta["difficulty"],
                    "status": "skipped", "reason": f"{label} not found",
                })
                continue
        else:
            # Buggy mode: create temp dir with wrong answer
            buggy_dir = Path(tempfile.mkdtemp(prefix="eda_buggy_"))
            if is_p3 or is_p6:
                # P3/P6: write a deliberately wrong answer
                (buggy_dir / "answer.txt").write_text("WRONG_ANSWER\n")
            else:
                editable_files = meta["files"]["editable"]
                if is_p5:
                    # P5: editable files are under visible/
                    for ef in editable_files:
                        src = task_path / ef
                        if src.is_file():
                            shutil.copy2(src, buggy_dir / Path(ef).name)
                else:
                    files_dir = task_path / "files"
                    for ef in editable_files:
                        src = files_dir / ef
                        if src.is_file():
                            shutil.copy2(src, buggy_dir / ef)
            submission_path = buggy_dir

        print(f"[{i+1}/{len(task_paths)}] {task_id} ({meta['track']}, {submission_mode})...", end=" ", flush=True)

        try:
            runs_dir, score_result = _evaluate_single(
                task_path, submission_path, meta, timeout, runs_root=dataset_runs_root,
            )
            status = "pass" if score_result.passed else "fail"
            print(f"{score_result.total_score:.2f} {'PASS' if score_result.passed else 'FAIL'}")
            results.append({
                "task_path": str(task_path),
                "task_id": task_id,
                "track": meta["track"],
                "tool": meta["tool"],
                "difficulty": meta["difficulty"],
                "status": status,
                "total_score": score_result.total_score,
                "objective_score": score_result.objective_score,
                "explanation_score": score_result.explanation_score,
                "components": [c.to_dict() for c in score_result.components],
                "score_path": str(runs_dir / "score.json"),
            })
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "task_path": str(task_path),
                "task_id": task_id,
                "track": meta.get("track", "unknown"),
                "tool": meta.get("tool", []),
                "difficulty": meta.get("difficulty", "unknown"),
                "status": "error",
                "reason": str(e),
            })
        finally:
            # Clean up buggy temp dir
            if submission_mode != "solution" and submission_path != (task_path / "files"):
                _safe_rmtree(submission_path)

    # Write summary
    summary = _build_dataset_summary(
        results, run_id, submission_mode, track_filter,
        sampled=sampled, sample_per_track=sample_per_track,
        limit=limit, seed=seed,
        total_candidates=total_candidates,
        selected_task_ids=selected_task_ids,
    )
    summary_path = dataset_runs_root / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))

    # Print summary
    print(f"\n=== Dataset Summary ===")
    print(f"  Total:       {summary['total']}")
    print(f"  Evaluated:   {summary['evaluated']}")
    print(f"  Passed:      {summary['passed']}")
    print(f"  Failed:      {summary['failed']}")
    print(f"  Errors:      {summary['errors']}")
    print(f"  Avg score:   {summary['avg_score']:.4f}")
    print(f"  Avg obj:     {summary['avg_objective']:.4f}")
    if summary.get("sampled"):
        print(f"  Sampled:     YES (seed={summary.get('seed')})")
    print(f"\nSummary written to: {summary_path}")


def _build_dataset_summary(results: list[dict], run_id: str, submission_mode: str,
                            track_filter: str | None, *,
                            sampled: bool = False, sample_per_track: int | None = None,
                            limit: int | None = None, seed: int = 42,
                            total_candidates: int = 0,
                            selected_task_ids: list[str] | None = None) -> dict:
    """Build a dataset summary dict from per-task results."""
    evaluated = [r for r in results if r["status"] in ("pass", "fail")]
    passed = [r for r in results if r["status"] == "pass"]
    failed = [r for r in results if r["status"] == "fail"]
    errors = [r for r in results if r["status"] in ("error", "skipped")]

    avg_score = sum(r["total_score"] for r in evaluated) / len(evaluated) if evaluated else 0.0
    avg_obj = sum(r["objective_score"] for r in evaluated) / len(evaluated) if evaluated else 0.0
    avg_exp = sum(r["explanation_score"] for r in evaluated) / len(evaluated) if evaluated else 0.0

    # Per-track stats
    tracks: dict[str, dict] = {}
    for r in evaluated:
        t = r.get("track", "unknown")
        if t not in tracks:
            tracks[t] = {"total": 0, "passed": 0, "avg_score": 0.0, "scores": []}
        tracks[t]["total"] += 1
        tracks[t]["scores"].append(r["total_score"])
        if r["status"] == "pass":
            tracks[t]["passed"] += 1
    for t in tracks:
        scores = tracks[t]["scores"]
        tracks[t]["avg_score"] = sum(scores) / len(scores) if scores else 0.0
        del tracks[t]["scores"]

    # Per-tool stats
    tools: dict[str, dict] = {}
    for r in evaluated:
        for tool_name in r.get("tool", ["unknown"]):
            if tool_name not in tools:
                tools[tool_name] = {"total": 0, "passed": 0, "scores": []}
            tools[tool_name]["total"] += 1
            tools[tool_name]["scores"].append(r["total_score"])
            if r["status"] == "pass":
                tools[tool_name]["passed"] += 1
    for t in tools:
        scores = tools[t]["scores"]
        tools[t]["avg_score"] = sum(scores) / len(scores) if scores else 0.0
        del tools[t]["scores"]

    # Per-difficulty stats
    difficulties: dict[str, dict] = {}
    for r in evaluated:
        d = r.get("difficulty", "unknown")
        if d not in difficulties:
            difficulties[d] = {"total": 0, "passed": 0, "scores": []}
        difficulties[d]["total"] += 1
        difficulties[d]["scores"].append(r["total_score"])
        if r["status"] == "pass":
            difficulties[d]["passed"] += 1
    for d in difficulties:
        scores = difficulties[d]["scores"]
        difficulties[d]["avg_score"] = sum(scores) / len(scores) if scores else 0.0
        del difficulties[d]["scores"]

    # Score distribution
    buckets = {"1.0": 0, "[0.8,1.0)": 0, "[0.5,0.8)": 0, "<0.5": 0}
    for r in evaluated:
        s = r["total_score"]
        if abs(s - 1.0) < 0.001:
            buckets["1.0"] += 1
        elif s >= 0.8:
            buckets["[0.8,1.0)"] += 1
        elif s >= 0.5:
            buckets["[0.5,0.8)"] += 1
        else:
            buckets["<0.5"] += 1

    # Buggy-specific: count tasks where score < 1.0 (lower than solution)
    buggy_lower = sum(1 for r in evaluated if abs(r["total_score"] - 1.0) >= 0.001)

    return {
        "run_id": run_id,
        "submission_mode": submission_mode,
        "track_filter": track_filter,
        "total": len(results),
        "evaluated": len(evaluated),
        "passed": len(passed),
        "failed": len(failed),
        "errors": len(errors),
        "avg_score": round(avg_score, 4),
        "avg_objective": round(avg_obj, 4),
        "avg_explanation": round(avg_exp, 4),
        "buggy_lower_than_solution_count": buggy_lower,
        "per_track": tracks,
        "per_tool": tools,
        "per_difficulty": difficulties,
        "score_distribution": buckets,
        "failure_list": [
            {"task_id": r["task_id"], "track": r.get("track"), "score": r.get("total_score"),
             "reason": r.get("reason", "")}
            for r in failed + errors
        ],
        "sampled": sampled,
        "sample_per_track": sample_per_track,
        "limit": limit,
        "seed": seed if sampled else None,
        "total_candidates": total_candidates,
        "selected_task_count": len(results),
        "selected_task_ids": selected_task_ids if sampled else None,
        "results": results,
    }


def cmd_report(args) -> None:
    runs_dir = Path(args.runs_dir).resolve()
    if not runs_dir.is_dir():
        print(f"ERROR: Runs directory not found: {runs_dir}", file=sys.stderr)
        sys.exit(1)

    fmt = args.format
    output_dir = Path(args.output).resolve() if args.output else runs_dir

    # Check if this is a dataset run (has summary.json) or single task run
    summary_path = runs_dir / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text())
    else:
        # Try to aggregate from score.json files
        summary = _aggregate_score_jsons(runs_dir)

    if fmt in ("terminal", "all"):
        _print_terminal_report(summary)
    if fmt in ("json", "all"):
        out_path = output_dir / "summary.json"
        out_path.write_text(json.dumps(summary, indent=2))
        print(f"\nJSON summary: {out_path}")
    if fmt in ("markdown", "all"):
        md = _generate_markdown_report(summary)
        out_path = output_dir / "report.md"
        out_path.write_text(md)
        print(f"Markdown report: {out_path}")


def _aggregate_score_jsons(runs_dir: Path) -> dict:
    """Aggregate score.json files from a runs directory into a summary."""
    score_files = list(runs_dir.rglob("score.json"))
    results = []
    for sf in sorted(score_files):
        try:
            score = json.loads(sf.read_text())
            results.append({
                "task_id": score.get("task_id", sf.parent.parent.name),
                "track": score.get("track", "unknown"),
                "tool": score.get("metadata", {}).get("tool", []),
                "difficulty": score.get("metadata", {}).get("difficulty", "unknown"),
                "status": "pass" if score.get("passed") else "fail",
                "total_score": score.get("total_score", 0.0),
                "objective_score": score.get("objective_score", 0.0),
                "explanation_score": score.get("explanation_score", 0.0),
                "components": score.get("components", []),
                "score_path": str(sf),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return _build_dataset_summary(results, runs_dir.name, "unknown", None)


def _print_terminal_report(summary: dict) -> None:
    """Print a formatted terminal report."""
    print(f"\n{'='*60}")
    print(f"  EDA-AgentBench Dataset Report")
    print(f"{'='*60}")
    print(f"  Run ID:          {summary.get('run_id', 'N/A')}")
    print(f"  Submission mode: {summary.get('submission_mode', 'N/A')}")
    print(f"  Track filter:    {summary.get('track_filter', 'all')}")
    print(f"{'='*60}")

    print(f"\n  Total tasks:     {summary['total']}")
    print(f"  Evaluated:       {summary['evaluated']}")
    print(f"  Passed:          {summary['passed']}")
    print(f"  Failed:          {summary['failed']}")
    print(f"  Errors:          {summary['errors']}")
    print(f"  Avg score:       {summary['avg_score']:.4f}")
    print(f"  Avg objective:   {summary['avg_objective']:.4f}")
    print(f"  Avg explanation: {summary['avg_explanation']:.4f}")

    # Score distribution
    dist = summary.get("score_distribution", {})
    print(f"\n  Score Distribution:")
    for bucket, count in dist.items():
        bar = "#" * count
        print(f"    {bucket:>12}: {count:>3}  {bar}")

    # Per-track
    per_track = summary.get("per_track", {})
    if per_track:
        print(f"\n  Per-Track:")
        print(f"    {'Track':<20} {'Total':>5} {'Pass':>5} {'Avg':>8}")
        print(f"    {'-'*40}")
        for track, stats in sorted(per_track.items()):
            print(f"    {track:<20} {stats['total']:>5} {stats['passed']:>5} {stats['avg_score']:>8.4f}")

    # Per-tool
    per_tool = summary.get("per_tool", {})
    if per_tool:
        print(f"\n  Per-Tool:")
        print(f"    {'Tool':<15} {'Total':>5} {'Pass':>5} {'Avg':>8}")
        print(f"    {'-'*35}")
        for tool, stats in sorted(per_tool.items()):
            print(f"    {tool:<15} {stats['total']:>5} {stats['passed']:>5} {stats['avg_score']:>8.4f}")

    # Per-difficulty
    per_diff = summary.get("per_difficulty", {})
    if per_diff:
        print(f"\n  Per-Difficulty:")
        print(f"    {'Difficulty':<15} {'Total':>5} {'Pass':>5} {'Avg':>8}")
        print(f"    {'-'*35}")
        for diff, stats in sorted(per_diff.items()):
            print(f"    {diff:<15} {stats['total']:>5} {stats['passed']:>5} {stats['avg_score']:>8.4f}")

    # Failure list
    failures = summary.get("failure_list", [])
    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for f in failures[:20]:
            reason = f.get("reason", "")
            score = f.get("score", "N/A")
            print(f"    {f['task_id']:<20} score={score}  {reason}")
        if len(failures) > 20:
            print(f"    ... and {len(failures) - 20} more")

    print(f"\n{'='*60}")


def _generate_markdown_report(summary: dict) -> str:
    """Generate a markdown report."""
    lines = [
        "# EDA-AgentBench Dataset Report",
        "",
        f"- **Run ID:** {summary.get('run_id', 'N/A')}",
        f"- **Submission mode:** {summary.get('submission_mode', 'N/A')}",
        f"- **Track filter:** {summary.get('track_filter', 'all')}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total tasks | {summary['total']} |",
        f"| Evaluated | {summary['evaluated']} |",
        f"| Passed | {summary['passed']} |",
        f"| Failed | {summary['failed']} |",
        f"| Errors | {summary['errors']} |",
        f"| Avg score | {summary['avg_score']:.4f} |",
        f"| Avg objective | {summary['avg_objective']:.4f} |",
        f"| Avg explanation | {summary['avg_explanation']:.4f} |",
        "",
        "## Score Distribution",
        "",
        "| Bucket | Count |",
        "|--------|-------|",
    ]
    for bucket, count in summary.get("score_distribution", {}).items():
        lines.append(f"| {bucket} | {count} |")

    per_track = summary.get("per_track", {})
    if per_track:
        lines += ["", "## Per-Track", "", "| Track | Total | Passed | Avg Score |", "|-------|-------|--------|-----------|"]
        for track, stats in sorted(per_track.items()):
            lines.append(f"| {track} | {stats['total']} | {stats['passed']} | {stats['avg_score']:.4f} |")

    per_tool = summary.get("per_tool", {})
    if per_tool:
        lines += ["", "## Per-Tool", "", "| Tool | Total | Passed | Avg Score |", "|------|-------|--------|-----------|"]
        for tool, stats in sorted(per_tool.items()):
            lines.append(f"| {tool} | {stats['total']} | {stats['passed']} | {stats['avg_score']:.4f} |")

    per_diff = summary.get("per_difficulty", {})
    if per_diff:
        lines += ["", "## Per-Difficulty", "", "| Difficulty | Total | Passed | Avg Score |", "|------------|-------|--------|-----------|"]
        for diff, stats in sorted(per_diff.items()):
            lines.append(f"| {diff} | {stats['total']} | {stats['passed']} | {stats['avg_score']:.4f} |")

    failures = summary.get("failure_list", [])
    if failures:
        lines += ["", "## Failures", "", "| Task ID | Track | Score | Reason |", "|---------|-------|-------|--------|"]
        for f in failures:
            lines.append(f"| {f['task_id']} | {f.get('track', '')} | {f.get('score', 'N/A')} | {f.get('reason', '')} |")

    return "\n".join(lines) + "\n"


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


def _find_deck_file(work_dir: Path, editable: set[str]) -> str:
    """Find the SPICE deck file name in workspace (strips visible/ prefix)."""
    for f in editable:
        name = Path(f).name
        if (work_dir / name).is_file():
            return name
    # Fallback: find first .sp file
    for f in work_dir.iterdir():
        if f.suffix == ".sp":
            return f.name
    return ""


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


def _extract_p2_log_sections(combined_log: str) -> dict[str, str]:
    """Extract per-mutant sections from P2 hidden run log.

    The hidden run.sh script outputs sections separated by
    '=== Mutant N ===' headers. This function splits the log
    into per-mutant sections so the evaluator can check each independently.
    """
    import re
    sections: dict[str, str] = {}
    # Split on "=== Mutant N ===" headers
    parts = re.split(r"=== Mutant (\d+) ===", combined_log)
    # parts[0] is before first header (may be empty or contain previous output)
    # parts[1] = "1", parts[2] = content after Mutant 1
    # parts[3] = "2", parts[4] = content after Mutant 2
    for i in range(1, len(parts) - 1, 2):
        mutant_num = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        sections[f"mutant_{mutant_num}"] = content
    return sections


def _write_anticheat_fail(task_path: Path, meta: dict, violations: list[str],
                           runs_base: Path | None = None) -> None:
    """Write a score.json indicating anti-cheat failure."""
    from eda_agentbench.types import ScoreResult
    runs_root = runs_base or RUNS_ROOT
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    runs_dir = runs_root / meta["task_id"] / run_id
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
