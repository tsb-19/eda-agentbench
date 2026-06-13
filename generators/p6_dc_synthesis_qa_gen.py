"""P6 DC Synthesis QA task generator — 10 question types, deterministic seed."""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator


# ---------------------------------------------------------------------------
# Name pools for realistic DC synthesis reports
# ---------------------------------------------------------------------------

MODULE_NAMES = [
    "alu_top", "fifo_ctrl", "uart_core", "spi_master", "i2c_slave", "dma_engine",
    "cache_ctrl", "decoder_8b10b", "encoder_nrz", "arbiter_rr", "mux_4to1",
    "pipeline_stage", "controller_fsm", "datapath_64b", "regfile_32x32",
    "adder_tree", "multiplier_16x16", "barrel_shifter", "comparator_32b",
    "sync_fifo", "async_bridge", "crc_gen", "ecc_encoder", "timer_32b",
    "watchdog", "interrupt_ctrl", "phy_rgmii", "mac_gbe", "pcs_10g",
    "serdes_12g", "pll_ctrl", "adc_interface", "dac_interface",
    "noc_router", "ddr_ctrl", "pcie_ep", "usb_device", "eth_mac",
    "gpu_shader", "dsp_core", "riscv_core", "arm_cortex", "mips_cpu",
    "jpeg_encoder", "fft_engine", "fir_filter", "iir_filter",
    "viterbi_dec", "reed_solomon", "aes_cipher", "sha256_core",
]

CLOCK_NAMES = [
    "clk", "clk_100m", "clk_200m", "clk_50m", "clk_33m", "clk_25m",
    "clk_core", "clk_io", "clk_mem", "clk_bus", "clk_dsp", "clk_gpu",
    "sys_clk", "cpu_clk", "mem_clk", "pci_clk", "usb_clk", "eth_clk",
    "spi_clk", "i2c_clk", "uart_clk", "jtag_clk", "ref_clk", "pll_clk",
    "axi_clk", "ahb_clk", "apb_clk", "noc_clk", "ddr_clk", "pcie_clk",
]

COMPILE_STATUSES = [
    "0 errors, 0 warnings",
    "0 errors, 1 warning",
    "0 errors, 3 warnings",
    "0 errors, 5 warnings",
    "0 errors, 12 warnings",
    "0 errors, 27 warnings",
]


def _format_dc_report(top_module: str, total_area: float, comb_area: float,
                      seq_area: float, cell_count: int, register_count: int,
                      worst_slack: float, clock_period: float,
                      compile_status: str, warning_count: int,
                      error_count: int, clock_name: str) -> str:
    """Format DC synthesis report in a normalized format."""
    lines = [
        "============================================================",
        "  Design Compiler Synthesis Report",
        "============================================================",
        "",
        f"  Top Module:         {top_module}",
        f"  Clock:              {clock_name}",
        "",
        "------------------------------------------------------------",
        "  Area Report",
        "------------------------------------------------------------",
        f"  Combinational area:  {comb_area:.2f}",
        f"  Noncombinational area: {seq_area:.2f}",
        f"  Total cell area:     {total_area:.2f}",
        "",
        "------------------------------------------------------------",
        "  Cell Report",
        "------------------------------------------------------------",
        f"  Number of cells:     {cell_count}",
        f"  Number of registers: {register_count}",
        "",
        "------------------------------------------------------------",
        "  Timing Report",
        "------------------------------------------------------------",
        f"  Clock period:        {clock_period:.4f}",
        f"  Worst slack:         {worst_slack:.4f}",
        "",
        "------------------------------------------------------------",
        "  Compile Status",
        "------------------------------------------------------------",
        f"  Compile status:      {compile_status}",
        f"  Warning count:       {warning_count}",
        f"  Error count:         {error_count}",
        "",
        "============================================================",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Question templates
# ---------------------------------------------------------------------------

QUESTION_TEMPLATES = [
    {
        "type": "total_area",
        "question": "What is the total cell area in the synthesis report?",
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda r: f"{r['total_area']:.2f}",
    },
    {
        "type": "combinational_area",
        "question": "What is the combinational area in the synthesis report?",
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda r: f"{r['comb_area']:.2f}",
    },
    {
        "type": "sequential_area",
        "question": "What is the sequential (noncombinational) area in the synthesis report?",
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda r: f"{r['seq_area']:.2f}",
    },
    {
        "type": "cell_count",
        "question": "How many cells are in the synthesized design?",
        "answer_type": "numeric",
        "tolerance": 0.0,
        "extract": lambda r: str(r["cell_count"]),
    },
    {
        "type": "register_count",
        "question": "How many registers are in the synthesized design?",
        "answer_type": "numeric",
        "tolerance": 0.0,
        "extract": lambda r: str(r["register_count"]),
    },
    {
        "type": "top_module",
        "question": "What is the top module name in the synthesis report?",
        "answer_type": "string",
        "tolerance": 0.0,
        "extract": lambda r: r["top_module"],
    },
    {
        "type": "worst_slack",
        "question": "What is the worst slack in the synthesis report?",
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda r: f"{r['worst_slack']:.4f}",
    },
    {
        "type": "compile_status",
        "question": "What is the compile status reported in the synthesis report?",
        "answer_type": "string",
        "tolerance": 0.0,
        "extract": lambda r: r["compile_status"],
    },
    {
        "type": "clock_period",
        "question": "What is the clock period in the synthesis report?",
        "answer_type": "numeric",
        "tolerance": 0.01,
        "extract": lambda r: f"{r['clock_period']:.4f}",
    },
    {
        "type": "warning_count",
        "question": "How many warnings are reported in the synthesis report?",
        "answer_type": "numeric",
        "tolerance": 0.0,
        "extract": lambda r: str(r["warning_count"]),
    },
]

EXPECTED_QUESTION_TYPES = [t["type"] for t in QUESTION_TEMPLATES]


class DCSynthesisQAGenerator(BaseGenerator):
    """Generates P6 DC Synthesis QA tasks with deterministic seeds."""

    def generate_one(self, task_index: int) -> Path:
        # Round-robin across question types
        qtype_idx = task_index % len(QUESTION_TEMPLATES)
        template = QUESTION_TEMPLATES[qtype_idx]

        # ID offset by 1 to avoid collision with smoke task (p6_dc_syn_000000)
        internal_index = task_index + 1
        task_id = f"p6_dc_syn_{internal_index:06d}"
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Generate synthesis report parameters
        top_module = self.rng.choice(MODULE_NAMES)
        clock_name = self.rng.choice(CLOCK_NAMES)
        clock_period = round(self.rng.uniform(1.0, 10.0), 4)

        # Area parameters (realistic ranges)
        total_area = round(self.rng.uniform(1000.0, 500000.0), 2)
        comb_fraction = self.rng.uniform(0.4, 0.8)
        comb_area = round(total_area * comb_fraction, 2)
        seq_area = round(total_area - comb_area, 2)

        # Cell/register counts
        cell_count = self.rng.randint(500, 50000)
        register_count = self.rng.randint(100, 10000)

        # Timing
        worst_slack = round(-self.rng.uniform(0.01, 2.0), 4)

        # Compile status
        warning_count = self.rng.choice([0, 1, 2, 3, 5, 8, 12, 15, 20, 27, 42])
        error_count = 0
        compile_status = f"{error_count} errors, {warning_count} warnings"

        # Build params dict for answer extraction
        params = {
            "top_module": top_module,
            "total_area": total_area,
            "comb_area": comb_area,
            "seq_area": seq_area,
            "cell_count": cell_count,
            "register_count": register_count,
            "worst_slack": worst_slack,
            "clock_period": clock_period,
            "compile_status": compile_status,
            "warning_count": warning_count,
            "error_count": error_count,
        }

        # Generate report text
        report_text = _format_dc_report(
            top_module, total_area, comb_area, seq_area,
            cell_count, register_count, worst_slack, clock_period,
            compile_status, warning_count, error_count, clock_name,
        )

        # Determine question and answer
        question = template["question"]
        expected_answer = template["extract"](params)
        answer_type = template["answer_type"]
        tolerance = template["tolerance"]

        # Write files
        (task_dir / "files" / "synthesis_report.rpt").write_text(report_text)
        (task_dir / "files" / "answer.txt").write_text("")

        # Write prompt
        prompt = f"""\
# DC Synthesis Report QA Task

## Question

{question}

## Instructions

Read the synthesis report file `synthesis_report.rpt` and answer the question.

Write your answer to `answer.txt` in this directory. The answer should be:
- For numeric answers: a decimal number (e.g., 12345.67 or 1000)
- For string answers: the exact text from the report (e.g., a module name or status)

## Files

- `synthesis_report.rpt` — the DC synthesis report (read-only)
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
            "track": "p6_dc_synthesis_qa",
            "tool": ["dc"],
            "difficulty": self._get_difficulty(template["type"]),
            "data_type": "template_synthetic",
            "resource_preset": "fast",
            "timeout_sec": 60,
            "max_tool_calls": 5,
            "max_patch_attempts": 1,
            "max_output_tokens": 4000,
            "files": {
                "visible": ["synthesis_report.rpt", "answer.txt"],
                "editable": ["answer.txt"],
                "hidden": [],
                "forbidden": ["synthesis_report.rpt"],
            },
            "run_command": "echo 'P6 QA task - no tool execution needed'",
            "scoring": {
                "weights": {
                    "answer_match": 1.0,
                },
                "evaluator": "dc_synthesis_qa.DCSynthesisQAEvaluator",
            },
            "answer": {
                "type": answer_type,
                "expected": expected_answer,
                "tolerance": tolerance,
                "question_type": template["type"],
            },
            "generator": {
                "script": "p6_dc_synthesis_qa_gen.py",
                "seed": self.seed,
                "question_type": template["type"],
                "task_index": task_index,
                "internal_index": internal_index,
                "top_module": top_module,
                "clock_name": clock_name,
            },
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir

    def _get_difficulty(self, question_type: str) -> str:
        """Map question type to difficulty level."""
        easy = {"total_area", "cell_count", "register_count", "top_module", "compile_status"}
        medium = {"combinational_area", "sequential_area", "clock_period", "warning_count"}
        hard = {"worst_slack"}
        if question_type in easy:
            return "easy"
        if question_type in medium:
            return "medium"
        return "hard"
