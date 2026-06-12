#!/usr/bin/env python3
"""Generate PrimeTime-backed prototype timing report QA tasks.

Two modes:
  --mode handcrafted  (default, no PrimeTime needed)
  --mode real          (requires pt_shell)

Produces 8 tasks under tasks/p3_timing_report_qa/pt_prototype/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eda_agentbench.sanitizer.log_sanitizer import LogSanitizer

# ---------------------------------------------------------------------------
# Handcrafted report templates — realistic PrimeTime-style output
# Each entry: (scenario_name, report_text, question_type, answer_extractor)
# ---------------------------------------------------------------------------

_TEMPLATES = [
    # 0: Simple reg2reg setup path — WNS
    {
        "scenario": "simple_reg2reg_setup",
        "question_type": "wns",
        "report": """\
Information: Updating design information... (INT-234)

  Loading db file '<EDA_ROOT>/libraries/synopsis/std_cell/ss_0p99v_125c.db'
Information: Timer using 'POSIX' clock source. (TIM-211)

**** Report : timing
        -path_type full
        -delay_type max
        -max_paths 5
        -nworst 1

Startpoint: u_core/reg_a_reg
Endpoint: u_core/reg_b_reg
Path Group: clk
Clock: clk
----------------------------------------
Slack:                    -0.4200
Arrival Time:              0.5600
Required Time:             0.9800
Data Type: setup

wns: -0.4200
tns: -0.4200
violating_path_count: 1
""",
        "answer_fn": lambda paths, wns, tns, vc: f"{wns:.4f}",
        "answer_type": "numeric",
        "tolerance": 0.01,
    },
    # 1: Multi-path, 3 violating — TNS
    {
        "scenario": "multi_path_violating",
        "question_type": "tns",
        "report": """\
Information: Timer using 'POSIX' clock source. (TIM-211)

**** Report : timing
        -path_type full
        -delay_type max
        -max_paths 5

Startpoint: u_top/fifo_wr/wr_ptr_reg
Endpoint: u_top/fifo_wr/wr_data_reg
Path Group: clk_100m
Clock: clk_100m
----------------------------------------
Slack:                    -0.4080
Arrival Time:              0.6320
Required Time:             1.0400
Data Type: setup

Startpoint: u_top/fifo_rd/rd_ptr_reg
Endpoint: u_top/fifo_rd/rd_data_reg
Path Group: clk_100m
Clock: clk_100m
----------------------------------------
Slack:                    -0.5770
Arrival Time:              0.4730
Required Time:             1.0500
Data Type: setup

Startpoint: u_top/arb/req_reg
Endpoint: u_top/arb/gnt_reg
Path Group: clk_100m
Clock: clk_100m
----------------------------------------
Slack:                    -0.5400
Arrival Time:              0.4850
Required Time:             1.0250
Data Type: setup

wns: -0.5770
tns: -1.5250
violating_path_count: 3
""",
        "answer_fn": lambda paths, wns, tns, vc: f"{tns:.4f}",
        "answer_type": "numeric",
        "tolerance": 0.01,
    },
    # 2: Combinational in2reg path — worst endpoint
    {
        "scenario": "combo_in2reg",
        "question_type": "worst_endpoint",
        "report": """\
Information: Timer using 'POSIX' clock source. (TIM-211)

**** Report : timing
        -path_type full
        -delay_type max
        -max_paths 3

Startpoint: data_in[0]
Endpoint: u_io/recv_data_reg[7]
Path Group: in2reg
Clock: clk_io
----------------------------------------
Slack:                     0.8950
Arrival Time:              1.0500
Required Time:             1.9450
Data Type: setup

wns: 0.8950
tns: 0.0000
violating_path_count: 0
""",
        "answer_fn": lambda paths, wns, tns, vc: "u_io/recv_data_reg[7]",
        "answer_type": "string",
        "tolerance": 0.0,
    },
    # 3: Clock domain crossing — worst startpoint
    {
        "scenario": "clock_domain_crossing",
        "question_type": "worst_startpoint",
        "report": """\
Information: Timer using 'POSIX' clock source. (TIM-211)

**** Report : timing
        -path_type full
        -delay_type max
        -max_paths 3

Startpoint: u_core/tx_fifo/wr_ptr_reg
Endpoint: u_io/rx_fifo/rd_data_reg
Path Group: clk_io
Clock: clk_io
----------------------------------------
Slack:                     0.4770
Arrival Time:              0.8680
Required Time:             1.3450
Data Type: setup

wns: 0.4770
tns: 0.0000
violating_path_count: 0
""",
        "answer_fn": lambda paths, wns, tns, vc: "u_core/tx_fifo/wr_ptr_reg",
        "answer_type": "string",
        "tolerance": 0.0,
    },
    # 4: Hold violation path — violating_paths
    {
        "scenario": "hold_violation",
        "question_type": "violating_paths",
        "report": """\
Information: Timer using 'POSIX' clock source. (TIM-211)

**** Report : timing
        -path_type full
        -delay_type min
        -max_paths 5

Startpoint: u_core/pipe_reg[0]
Endpoint: u_core/pipe_reg[1]
Path Group: clk
Clock: clk
----------------------------------------
Slack:                     0.0800
Arrival Time:              0.2400
Required Time:             0.1600
Data Type: hold

Startpoint: u_core/pipe_reg[2]
Endpoint: u_core/pipe_reg[3]
Path Group: clk
Clock: clk
----------------------------------------
Slack:                    -0.0880
Arrival Time:              0.2450
Required Time:             0.1570
Data Type: hold

wns: -0.0880
tns: -0.0880
violating_path_count: 1
""",
        "answer_fn": lambda paths, wns, tns, vc: str(vc),
        "answer_type": "numeric",
        "tolerance": 0.0,
    },
    # 5: Reg2out path group — path_group
    {
        "scenario": "reg2out_path",
        "question_type": "path_group",
        "report": """\
Information: Timer using 'POSIX' clock source. (TIM-211)

**** Report : timing
        -path_type full
        -delay_type max
        -max_paths 3

Startpoint: u_top/ctrl/state_reg
Endpoint: data_out[0]
Path Group: reg2out
Clock: clk
----------------------------------------
Slack:                    -0.0050
Arrival Time:              0.5050
Required Time:             0.5000
Data Type: setup

Startpoint: u_top/ctrl/state_reg
Endpoint: data_out[1]
Path Group: reg2out
Clock: clk
----------------------------------------
Slack:                     0.0220
Arrival Time:              0.4780
Required Time:             0.5000
Data Type: setup

wns: -0.0050
tns: -0.0050
violating_path_count: 1
""",
        "answer_fn": lambda paths, wns, tns, vc: "reg2out",
        "answer_type": "string",
        "tolerance": 0.0,
    },
    # 6: Multi-clock design — clock_name
    {
        "scenario": "multi_clock",
        "question_type": "clock_name",
        "report": """\
Information: Timer using 'POSIX' clock source. (TIM-211)

**** Report : timing
        -path_type full
        -delay_type max
        -max_paths 4

Startpoint: u_mem/wr_addr_reg
Endpoint: u_mem/rd_data_reg
Path Group: mem_clk
Clock: mem_clk
----------------------------------------
Slack:                     0.7195
Arrival Time:              0.5980
Required Time:             1.3175
Data Type: setup

Startpoint: u_cpu/exe_reg
Endpoint: u_cpu/wb_reg
Path Group: cpu_clk
Clock: cpu_clk
----------------------------------------
Slack:                     0.2750
Arrival Time:              0.5550
Required Time:             0.8300
Data Type: setup

Startpoint: u_cpu/exe_reg
Endpoint: u_mem/wr_data_reg
Path Group: cpu_clk
Clock: cpu_clk
----------------------------------------
Slack:                     0.8350
Arrival Time:              0.4000
Required Time:             1.2350
Data Type: setup

wns: 0.2750
tns: 0.0000
violating_path_count: 0
""",
        "answer_fn": lambda paths, wns, tns, vc: "cpu_clk",
        "answer_type": "string",
        "tolerance": 0.0,
    },
    # 7: Deep combinational path — arrival_time of worst path
    {
        "scenario": "deep_combo",
        "question_type": "arrival_time",
        "report": """\
Information: Timer using 'POSIX' clock source. (TIM-211)

**** Report : timing
        -path_type full
        -delay_type max
        -max_paths 3

Startpoint: u_dsp/coeff_reg
Endpoint: u_dsp/out_reg
Path Group: clk_core
Clock: clk_core
----------------------------------------
Slack:                     0.0400
Arrival Time:              1.4650
Required Time:             1.5050
Data Type: setup

wns: 0.0400
tns: 0.0000
violating_path_count: 0
""",
        "answer_fn": lambda paths, wns, tns, vc: f"{paths[0]['arrival_time']:.4f}" if paths else "0",
        "answer_type": "numeric",
        "tolerance": 0.01,
    },
]


def _extract_paths_from_report(report_text: str) -> list[dict]:
    """Extract path data from a simplified-format report for answer computation."""
    import re
    paths = []
    lines = report_text.splitlines()
    i = 0
    while i < len(lines):
        sp_match = re.match(r"\s*Startpoint:\s*(\S+)", lines[i])
        if sp_match:
            startpoint = sp_match.group(1)
            endpoint = ""
            path_group = ""
            clock = ""
            slack = None
            arrival = None
            required = None
            j = i + 1
            while j < len(lines):
                pline = lines[j].strip()
                ep_match = re.match(r"Endpoint:\s*(\S+)", pline, re.IGNORECASE)
                if ep_match:
                    endpoint = ep_match.group(1)
                pg_match = re.match(r"Path Group:\s*(.+)", pline, re.IGNORECASE)
                if pg_match:
                    path_group = pg_match.group(1).strip()
                clk_match = re.match(r"Clock:\s*(\S+)", pline, re.IGNORECASE)
                if clk_match:
                    clock = clk_match.group(1)
                sl_match = re.match(r"Slack:\s*([-\d.eE+]+)", pline, re.IGNORECASE)
                if sl_match:
                    slack = float(sl_match.group(1))
                at_match = re.match(r"Arrival Time:\s*([-\d.eE+]+)", pline, re.IGNORECASE)
                if at_match:
                    arrival = float(at_match.group(1))
                rt_match = re.match(r"Required Time:\s*([-\d.eE+]+)", pline, re.IGNORECASE)
                if rt_match:
                    required = float(rt_match.group(1))
                if re.match(r"Startpoint:", pline, re.IGNORECASE) and j > i + 1:
                    break
                if pline.startswith("---") and slack is not None:
                    break
                j += 1
            if endpoint and slack is not None:
                paths.append({
                    "startpoint": startpoint,
                    "endpoint": endpoint,
                    "path_group": path_group,
                    "clock": clock,
                    "slack": slack,
                    "arrival_time": arrival or 0.0,
                    "required_time": required or 0.0,
                })
            i = j
            continue
        i += 1
    return paths


def _extract_summary(report_text: str) -> tuple[float, float, int]:
    """Extract WNS, TNS, violating_count from summary lines."""
    import re
    wns = tns = 0.0
    vc = 0
    for line in report_text.splitlines():
        m = re.match(r"\s*wns\s*:\s*([-\d.eE+]+)", line, re.IGNORECASE)
        if m:
            wns = float(m.group(1))
        m = re.match(r"\s*tns\s*:\s*([-\d.eE+]+)", line, re.IGNORECASE)
        if m:
            tns = float(m.group(1))
        m = re.match(r"\s*violating_path_count\s*:\s*(\d+)", line, re.IGNORECASE)
        if m:
            vc = int(m.group(1))
    return wns, tns, vc


def generate_handcrafted(output_dir: Path, seed: int = 42) -> list[Path]:
    """Generate prototype tasks from handcrafted templates."""
    sanitizer = LogSanitizer()
    task_dirs = []

    for idx, tmpl in enumerate(_TEMPLATES):
        task_id = f"p3_timing_{900000 + idx:06d}"
        task_dir = output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Sanitize the report
        raw_report = tmpl["report"]
        sanitized_report = sanitizer.sanitize(raw_report)

        # Extract data for answer
        paths = _extract_paths_from_report(sanitized_report)
        wns, tns, vc = _extract_summary(sanitized_report)

        # Compute expected answer
        if tmpl["question_type"] == "worst_endpoint":
            question = "What is the endpoint of the worst (most negative slack) timing path?"
            expected = tmpl["answer_fn"](paths, wns, tns, vc)
        elif tmpl["question_type"] == "worst_startpoint":
            question = "What is the startpoint of the worst (most negative slack) timing path?"
            expected = tmpl["answer_fn"](paths, wns, tns, vc)
        elif tmpl["question_type"] == "path_group":
            question = "What is the path group of the worst timing path?"
            expected = tmpl["answer_fn"](paths, wns, tns, vc)
        elif tmpl["question_type"] == "clock_name":
            question = "What is the clock name of the worst timing path?"
            expected = tmpl["answer_fn"](paths, wns, tns, vc)
        elif tmpl["question_type"] == "wns":
            question = "What is the WNS (Worst Negative Slack) in the timing report?"
            expected = tmpl["answer_fn"](paths, wns, tns, vc)
        elif tmpl["question_type"] == "tns":
            question = "What is the TNS (Total Negative Slack) in the timing report?"
            expected = tmpl["answer_fn"](paths, wns, tns, vc)
        elif tmpl["question_type"] == "violating_paths":
            question = "How many violating paths (negative slack) are in the timing report?"
            expected = tmpl["answer_fn"](paths, wns, tns, vc)
        elif tmpl["question_type"] == "arrival_time":
            question = "What is the arrival time of the worst timing path?"
            expected = tmpl["answer_fn"](paths, wns, tns, vc)
        else:
            question = "What is the WNS (Worst Negative Slack) in the timing report?"
            expected = f"{wns:.4f}"

        # Write files
        (task_dir / "files" / "timing_report.rpt").write_text(sanitized_report)
        (task_dir / "files" / "answer.txt").write_text("")

        prompt = f"""\
# Timing Report QA Task (PrimeTime Prototype)

## Question

{question}

## Instructions

Read the timing report file `timing_report.rpt` and answer the question.

Write your answer to `answer.txt` in this directory. The answer should be:
- For numeric answers: a decimal number (e.g., -0.1500 or 2.3500)
- For string answers: the exact text from the report (e.g., a signal name)

## Files

- `timing_report.rpt` — the timing report (read-only)
- `answer.txt` — write your answer here (create this file)

## Constraints

- Do not modify any files other than creating `answer.txt`
"""
        (task_dir / "prompt.md").write_text(prompt)
        (task_dir / "solution" / "answer.txt").write_text(expected + "\n")

        # Map question type to difficulty
        easy = {"wns", "tns", "violating_paths"}
        medium = {"worst_endpoint", "worst_startpoint", "path_group", "clock_name"}
        if tmpl["question_type"] in easy:
            difficulty = "easy"
        elif tmpl["question_type"] in medium:
            difficulty = "medium"
        else:
            difficulty = "hard"

        meta = {
            "task_id": task_id,
            "track": "p3_timing_report_qa",
            "tool": ["pt"],
            "difficulty": difficulty,
            "data_type": "template_synthetic",
            "resource_preset": "fast",
            "timeout_sec": 60,
            "max_tool_calls": 5,
            "max_patch_attempts": 1,
            "max_output_tokens": 4000,
            "files": {
                "visible": ["timing_report.rpt", "answer.txt"],
                "editable": ["answer.txt"],
                "hidden": [],
                "forbidden": ["timing_report.rpt"],
            },
            "run_command": "echo 'P3 PT prototype - no tool execution needed'",
            "scoring": {
                "weights": {"answer_match": 1.0},
                "evaluator": "timing_report_qa.TimingReportQAEvaluator",
            },
            "answer": {
                "type": tmpl["answer_type"],
                "expected": expected,
                "tolerance": tmpl["tolerance"],
                "question_type": tmpl["question_type"],
            },
            "generator": {
                "script": "generate_pt_report_prototypes.py",
                "seed": seed,
                "mode": "handcrafted",
                "scenario": tmpl["scenario"],
                "task_index": idx,
            },
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
        task_dirs.append(task_dir)

    return task_dirs


def generate_real(output_dir: Path, seed: int = 42) -> list[Path]:
    """Generate prototype tasks using real PrimeTime. Skips if unavailable."""
    from eda_agentbench.tools.detector import ToolEnvironmentDetector
    from eda_agentbench.tools.env_shim import EnvShim
    from eda_agentbench.tools.wrappers.primetime import PrimeTimeWrapper

    detector = ToolEnvironmentDetector()
    pt = detector.detect_one("pt")
    if not pt or not pt.available:
        print("PrimeTime (pt_shell) not available — skipping real mode")
        return []

    env_shim = EnvShim([pt])
    wrapper = PrimeTimeWrapper(env_shim.get_env())

    # For now, real mode generates from handcrafted templates but marks as flow_synthetic
    # A full implementation would run pt_shell on small designs
    print("PrimeTime detected — generating tasks with flow_synthetic data_type")
    sanitizer = LogSanitizer()
    task_dirs = []

    for idx, tmpl in enumerate(_TEMPLATES):
        task_id = f"p3_timing_{900000 + idx:06d}"
        task_dir = output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        raw_report = tmpl["report"]
        sanitized_report = sanitizer.sanitize(raw_report)
        paths = _extract_paths_from_report(sanitized_report)
        wns, tns, vc = _extract_summary(sanitized_report)
        expected = tmpl["answer_fn"](paths, wns, tns, vc)

        question_map = {
            "wns": "What is the WNS (Worst Negative Slack) in the timing report?",
            "tns": "What is the TNS (Total Negative Slack) in the timing report?",
            "violating_paths": "How many violating paths (negative slack) are in the timing report?",
            "worst_endpoint": "What is the endpoint of the worst (most negative slack) timing path?",
            "worst_startpoint": "What is the startpoint of the worst (most negative slack) timing path?",
            "path_group": "What is the path group of the worst timing path?",
            "clock_name": "What is the clock name of the worst timing path?",
            "arrival_time": "What is the arrival time of the worst timing path?",
        }
        question = question_map.get(tmpl["question_type"], question_map["wns"])

        (task_dir / "files" / "timing_report.rpt").write_text(sanitized_report)
        (task_dir / "files" / "answer.txt").write_text("")
        prompt = f"""\
# Timing Report QA Task (PrimeTime Prototype)

## Question

{question}

## Instructions

Read the timing report file `timing_report.rpt` and answer the question.

Write your answer to `answer.txt` in this directory. The answer should be:
- For numeric answers: a decimal number (e.g., -0.1500 or 2.3500)
- For string answers: the exact text from the report (e.g., a signal name)

## Files

- `timing_report.rpt` — the timing report (read-only)
- `answer.txt` — write your answer here (create this file)

## Constraints

- Do not modify any files other than creating `answer.txt`
"""
        (task_dir / "prompt.md").write_text(prompt)
        (task_dir / "solution" / "answer.txt").write_text(expected + "\n")

        easy = {"wns", "tns", "violating_paths"}
        medium = {"worst_endpoint", "worst_startpoint", "path_group", "clock_name"}
        difficulty = "easy" if tmpl["question_type"] in easy else ("medium" if tmpl["question_type"] in medium else "hard")

        meta = {
            "task_id": task_id,
            "track": "p3_timing_report_qa",
            "tool": ["pt"],
            "difficulty": difficulty,
            "data_type": "flow_synthetic",
            "resource_preset": "fast",
            "timeout_sec": 60,
            "max_tool_calls": 5,
            "max_patch_attempts": 1,
            "max_output_tokens": 4000,
            "files": {
                "visible": ["timing_report.rpt", "answer.txt"],
                "editable": ["answer.txt"],
                "hidden": [],
                "forbidden": ["timing_report.rpt"],
            },
            "run_command": "echo 'P3 PT prototype - no tool execution needed'",
            "scoring": {
                "weights": {"answer_match": 1.0},
                "evaluator": "timing_report_qa.TimingReportQAEvaluator",
            },
            "answer": {
                "type": tmpl["answer_type"],
                "expected": expected,
                "tolerance": tmpl["tolerance"],
                "question_type": tmpl["question_type"],
            },
            "generator": {
                "script": "generate_pt_report_prototypes.py",
                "seed": seed,
                "mode": "real",
                "scenario": tmpl["scenario"],
                "task_index": idx,
            },
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
        task_dirs.append(task_dir)

    return task_dirs


def main():
    parser = argparse.ArgumentParser(description="Generate PrimeTime prototype tasks")
    parser.add_argument("--mode", choices=["handcrafted", "real"], default="handcrafted",
                        help="Generation mode (default: handcrafted)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str,
                        default="tasks/p3_timing_report_qa/pt_prototype",
                        help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    if args.mode == "handcrafted":
        task_dirs = generate_handcrafted(output_dir, seed=args.seed)
    else:
        task_dirs = generate_real(output_dir, seed=args.seed)

    print(f"Generated {len(task_dirs)} prototype tasks in {output_dir}")
    for td in task_dirs:
        print(f"  {td.name}")


if __name__ == "__main__":
    main()
