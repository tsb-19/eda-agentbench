"""P3 Timing Report QA task generator — 10 question types, deterministic seed."""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator


# ---------------------------------------------------------------------------
# Name pools for realistic design elements
# ---------------------------------------------------------------------------

CLOCK_NAMES = ["clk", "clk_100m", "clk_core", "clk_io", "sys_clk", "cpu_clk",
               "mem_clk", "pci_clk", "usb_clk", "eth_clk"]

MODULE_NAMES = ["alu", "fifo", "uart", "spi", "i2c", "dma", "cache", "decoder",
                "encoder", "arbiter", "mux", "demux", "buffer", "pipeline",
                "controller", "datapath", "regfile", "adder", "multiplier", "shifter"]

PATH_GROUPS = ["clk", "clk_100m", "clk_core", "clk_io", "reg2reg", "in2reg", "reg2out"]

DATA_TYPES = ["setup", "hold"]


def _gen_signal_name(rng, prefix: str) -> str:
    """Generate a realistic signal name."""
    module = rng.choice(MODULE_NAMES)
    suffix = rng.choice(["_q", "_d", "_en", "_out", "_in", "_reg", ""])
    return f"{prefix}/{module}{suffix}"


def _gen_timing_paths(rng, count: int, clock: str, path_group: str,
                      wns_target: float, data_type: str = "setup") -> list[dict]:
    """Generate a list of timing paths with realistic values."""
    paths = []
    # First path is always the worst
    worst_slack = wns_target

    for i in range(count):
        if i == 0:
            slack = worst_slack
        else:
            # Subsequent paths have progressively better slack
            slack = worst_slack + rng.uniform(0.01, 0.5) * (i + 1)
            if slack > 0 and i < count - 1:
                # Some paths may be non-violating
                slack = rng.uniform(-0.1, 0.3)

        required_time = rng.uniform(1.5, 5.0)
        arrival_time = required_time - slack

        startpoint = _gen_signal_name(rng, rng.choice(["u_core", "u_top", "u_io", "u_mem"]))
        endpoint = _gen_signal_name(rng, rng.choice(["u_core", "u_top", "u_io", "u_mem"]))

        paths.append({
            "index": i + 1,
            "startpoint": startpoint,
            "endpoint": endpoint,
            "path_group": path_group,
            "clock": clock,
            "slack": round(slack, 4),
            "arrival_time": round(arrival_time, 4),
            "required_time": round(required_time, 4),
            "data_type": data_type,
        })

    return paths


def _format_timing_report(paths: list[dict], wns: float, tns: float,
                          violating_count: int) -> str:
    """Format timing paths into a normalized PrimeTime-style report."""
    lines = [
        "**** Report : timing",
        "    -path_type full",
        "    -delay_type max",
        f"    -max_paths {len(paths)}",
        "",
        f"wns: {wns:.4f}",
        f"tns: {tns:.4f}",
        f"violating_path_count: {violating_count}",
        "",
    ]

    for path in paths:
        lines.extend([
            f"Startpoint: {path['startpoint']}",
            f"Endpoint: {path['endpoint']}",
            f"Path Group: {path['path_group']}",
            f"Clock: {path['clock']}",
            "-" * 40,
            f"Slack:                    {path['slack']:.4f}",
            f"Arrival Time:              {path['arrival_time']:.4f}",
            f"Required Time:             {path['required_time']:.4f}",
            f"Data Type: {path['data_type']}",
            "",
        ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Question templates
# ---------------------------------------------------------------------------

QUESTION_TEMPLATES = [
    {
        "type": "wns",
        "question": "What is the WNS (Worst Negative Slack) in the timing report?",
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda paths, wns, tns, vc: f"{wns:.4f}",
    },
    {
        "type": "tns",
        "question": "What is the TNS (Total Negative Slack) in the timing report?",
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda paths, wns, tns, vc: f"{tns:.4f}",
    },
    {
        "type": "worst_endpoint",
        "question": "What is the endpoint of the worst (most negative slack) timing path?",
        "answer_type": "string",
        "tolerance": 0.0,
        "extract": lambda paths, wns, tns, vc: paths[0]["endpoint"] if paths else "",
    },
    {
        "type": "worst_startpoint",
        "question": "What is the startpoint of the worst (most negative slack) timing path?",
        "answer_type": "string",
        "tolerance": 0.0,
        "extract": lambda paths, wns, tns, vc: paths[0]["startpoint"] if paths else "",
    },
    {
        "type": "violating_paths",
        "question": "How many violating paths (negative slack) are in the timing report?",
        "answer_type": "numeric",
        "tolerance": 0.0,
        "extract": lambda paths, wns, tns, vc: str(vc),
    },
    {
        "type": "path_group",
        "question": "What is the path group of the worst timing path?",
        "answer_type": "string",
        "tolerance": 0.0,
        "extract": lambda paths, wns, tns, vc: paths[0]["path_group"] if paths else "",
    },
    {
        "type": "clock_name",
        "question": "What is the clock name of the worst timing path?",
        "answer_type": "string",
        "tolerance": 0.0,
        "extract": lambda paths, wns, tns, vc: paths[0]["clock"] if paths else "",
    },
    {
        "type": "required_time",
        "question": "What is the required time of the worst timing path?",
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda paths, wns, tns, vc: f"{paths[0]['required_time']:.4f}" if paths else "0",
    },
    {
        "type": "arrival_time",
        "question": "What is the arrival time of the worst timing path?",
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda paths, wns, tns, vc: f"{paths[0]['arrival_time']:.4f}" if paths else "0",
    },
    {
        "type": "slack_of_named_path",
        "question": None,  # Dynamic: asks about a specific path's slack
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda paths, wns, tns, vc: None,  # Handled dynamically
    },
]

EXPECTED_QUESTION_TYPES = [t["type"] for t in QUESTION_TEMPLATES]


class P3TimingReportQAGenerator(BaseGenerator):
    """Generates P3 Timing Report QA tasks with deterministic seeds."""

    def generate_one(self, task_index: int) -> Path:
        # Round-robin across question types
        qtype_idx = task_index % len(QUESTION_TEMPLATES)
        template = QUESTION_TEMPLATES[qtype_idx]

        task_id = f"p3_timing_{task_index:06d}"
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Generate timing report parameters
        clock = self.rng.choice(CLOCK_NAMES)
        path_group = self.rng.choice(PATH_GROUPS)
        num_paths = self.rng.randint(5, 20)
        wns_target = round(-self.rng.uniform(0.05, 2.0), 4)
        data_type = self.rng.choice(DATA_TYPES)

        # Generate paths
        paths = _gen_timing_paths(self.rng, num_paths, clock, path_group,
                                  wns_target, data_type)

        # Calculate TNS and violating count
        tns = round(sum(p["slack"] for p in paths if p["slack"] < 0), 4)
        violating_count = sum(1 for p in paths if p["slack"] < 0)
        wns = min(p["slack"] for p in paths)

        # Generate report text
        report_text = _format_timing_report(paths, wns, tns, violating_count)

        # Determine question and answer
        if template["type"] == "slack_of_named_path":
            # Pick a specific path (not the worst) to ask about
            target_idx = self.rng.randint(1, min(len(paths) - 1, 4))
            target_path = paths[target_idx]
            question = (
                f"What is the slack of the timing path ending at "
                f"'{target_path['endpoint']}'?"
            )
            expected_answer = f"{target_path['slack']:.4f}"
        else:
            question = template["question"]
            expected_answer = template["extract"](
                paths, wns, tns, violating_count
            )

        answer_type = template["answer_type"]
        tolerance = template["tolerance"]

        # Write files
        (task_dir / "files" / "timing_report.rpt").write_text(report_text)
        # Create empty answer.txt placeholder (model will overwrite)
        (task_dir / "files" / "answer.txt").write_text("")

        # Write prompt
        prompt = f"""\
# Timing Report QA Task

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

        # Write solution answer
        (task_dir / "solution" / "answer.txt").write_text(expected_answer + "\n")

        # Write metadata
        meta = {
            "task_id": task_id,
            "track": "p3_timing_report_qa",
            "tool": ["pt"],
            "difficulty": self._get_difficulty(template["type"]),
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
            "run_command": "echo 'P3 QA task - no tool execution needed'",
            "scoring": {
                "weights": {
                    "answer_match": 1.0,
                },
                "evaluator": "timing_report_qa.TimingReportQAEvaluator",
            },
            "answer": {
                "type": answer_type,
                "expected": expected_answer,
                "tolerance": tolerance,
                "question_type": template["type"],
            },
            "generator": {
                "script": "p3_timing_report_qa_gen.py",
                "seed": self.seed,
                "question_type": template["type"],
                "task_index": task_index,
                "num_paths": num_paths,
                "clock": clock,
                "path_group": path_group,
            },
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir

    def _get_difficulty(self, question_type: str) -> str:
        """Map question type to difficulty level."""
        easy = {"wns", "tns", "violating_paths"}
        medium = {"worst_endpoint", "worst_startpoint", "path_group", "clock_name"}
        hard = {"required_time", "arrival_time", "slack_of_named_path"}
        if question_type in easy:
            return "easy"
        if question_type in medium:
            return "medium"
        return "hard"
