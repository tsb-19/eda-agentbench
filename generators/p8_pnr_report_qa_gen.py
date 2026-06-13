"""Generator for P8 PnR Report QA tasks.

Generates synthetic ICC2-style and Innovus-style PnR reports with
deterministic seeds and diverse question types.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

# Design name pool
DESIGN_NAMES = [
    "aes_core", "spi_controller", "uart_top", "i2c_master", "usb_device",
    "pcie_endpoint", "ddr_controller", "sram_wrapper", "fifo_async",
    "arbiter_rr", "dma_engine", "gpio_block", "timer_unit", "watchdog",
    "interrupt_ctrl", "bus_bridge", "codec_frontend", "pll_controller",
    "clock_divider", "reset_sync", "pad_ring", "voltage_regulator",
    "adc_interface", "dac_interface", "filter_dsp", "fft_engine",
    "viterbi_decoder", "reed_solomon", "crc_generator", "scrambler",
    "deserializer", "serializer", "elast_fifo", "rate_match",
    "protocol_conv", "error_detect", "crc_check", "lane_align",
    "byte_sync", "frame_sync", "pattern_gen", "pattern_check",
    "prbs_gen", "prbs_check", "ber_meter", "eye_monitor",
    "cdr_loop", "eq_adapt", "ffe_dfe", "decision_feedback",
]

# Stage options
STAGES = ["floorplan", "place", "cts", "route", "postroute"]

# Layer names for congestion
CONGESTION_LAYERS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]

# Question types and their fields
QUESTION_TYPES = {
    "setup_timing": ["setup_wns", "setup_tns", "setup_violations"],
    "hold_timing": ["hold_wns", "hold_tns", "hold_violations"],
    "timing_path": ["worst_endpoint", "worst_startpoint", "timing_met"],
    "utilization": ["core_utilization", "placement_density", "instance_count", "sequential_count"],
    "area": ["cell_area", "macro_area", "total_cell_area", "buffer_count"],
    "congestion": ["max_horizontal_overflow", "max_vertical_overflow", "total_overflow",
                   "congested_bins", "worst_congestion_layer", "congestion_pass"],
    "routing": ["total_wirelength", "drc_total", "shorts", "opens", "antenna_violations",
                "route_completed"],
    "power": ["internal_power", "switching_power", "leakage_power", "total_power"],
    "flow_status": ["stage", "tool_family", "design_name"],
}

# Endpoint/startpoint name pools
ENDPOINTS = [
    "u_cpu/reg_pc_reg", "u_mem/data_out_reg", "u_uart/tx_shift_reg",
    "u_spi/miso_reg", "u_i2c/sda_out_reg", "u_usb/dp_out_reg",
    "u_pcie/tlp_hdr_reg", "u_ddr/dfi_wrdata_reg", "u_sram/q_reg",
    "u_fifo/wptr_reg", "u_arb/grant_reg", "u_dma/addr_reg",
    "u_gpio/out_val_reg", "u_timer/cnt_reg", "u_wdog/bark_reg",
    "u_intc/pending_reg", "u_bridge/addr_reg", "u_codec/pcm_out_reg",
    "u_pll/lock_det_reg", "u_clkdiv/div_ratio_reg", "u_rst/sync_reg",
    "u_adc/sample_reg", "u_dac/out_reg", "u_filter/acc_reg",
    "u_fft/bfly_reg", "u_vit/path_reg", "u_rs/codeword_reg",
    "u_crc/remainder_reg", "u_scram/state_reg", "u_deser/word_reg",
]

STARTPOINTS = [
    "u_cpu/if_stage_reg", "u_mem/addr_in_reg", "u_uart/rx_fifo_reg",
    "u_spi/mosi_reg", "u_i2c/scl_in_reg", "u_usb/dp_in_reg",
    "u_pcie/rxp_reg", "u_ddr/dfi_rddata_reg", "u_sram/d_reg",
    "u_fifo/rptr_reg", "u_arb/req_reg", "u_dma/ctrl_reg",
    "u_gpio/in_val_reg", "u_timer/load_reg", "u_wdog/refresh_reg",
    "u_intc/mask_reg", "u_bridge/data_reg", "u_codec/adc_reg",
    "u_pll/ref_clk_reg", "u_clkdiv/clk_in_reg", "u_rst/rst_n_reg",
    "u_adc/vin_reg", "u_dac/vref_reg", "u_filter/coeff_reg",
    "u_fft/twiddle_reg", "u_vit/bm_reg", "u_rs/syndrome_reg",
    "u_crc/poly_reg", "u_scram/init_reg", "u_ser/shift_reg",
]


def _make_rng(seed: int) -> random.Random:
    return random.Random(seed)


def generate_report(rng: random.Random, tool_family: str, design_name: str,
                    stage: str) -> tuple[str, dict[str, Any]]:
    """Generate a synthetic PnR report and its oracle answers.

    Returns (report_text, oracle_answers).
    """
    # Generate timing values
    setup_wns = round(rng.uniform(-2.5, -0.01), 3)
    setup_tns = round(setup_wns * rng.randint(1, 20), 3)
    setup_violations = rng.randint(0, 15)
    hold_wns = round(rng.uniform(-1.5, -0.01), 3)
    hold_tns = round(hold_wns * rng.randint(1, 10), 3)
    hold_violations = rng.randint(0, 8)

    worst_endpoint = rng.choice(ENDPOINTS)
    worst_startpoint = rng.choice(STARTPOINTS)
    timing_met = setup_violations == 0 and hold_violations == 0

    # Generate utilization values
    core_utilization = round(rng.uniform(40.0, 95.0), 1)
    placement_density = round(rng.uniform(0.5, 0.95), 3)
    instance_count = rng.randint(5000, 500000)
    sequential_count = rng.randint(500, 50000)

    # Generate area values
    cell_area = round(rng.uniform(10000, 500000), 1)
    macro_area = round(rng.uniform(0, cell_area * 0.3), 1)
    total_cell_area = round(cell_area + macro_area, 1)
    buffer_count = rng.randint(500, 20000)

    # Generate congestion values
    max_h_overflow = round(rng.uniform(0.0, 15.0), 1)
    max_v_overflow = round(rng.uniform(0.0, 15.0), 1)
    total_overflow = round(max_h_overflow + max_v_overflow + rng.uniform(0, 5), 1)
    congested_bins = rng.randint(0, 200)
    worst_congestion_layer = rng.choice(CONGESTION_LAYERS)
    congestion_pass = max_h_overflow < 10.0 and max_v_overflow < 10.0

    # Generate routing values
    total_wirelength = round(rng.uniform(100000, 5000000), 0)
    drc_total = rng.randint(0, 50)
    shorts = rng.randint(0, drc_total)
    opens = rng.randint(0, drc_total - shorts)
    antenna_violations = rng.randint(0, 10)
    route_completed = drc_total == 0

    # Generate power values
    internal_power = round(rng.uniform(0.5, 50.0), 2)
    switching_power = round(rng.uniform(0.5, 100.0), 2)
    leakage_power = round(rng.uniform(0.01, 5.0), 3)
    total_power = round(internal_power + switching_power + leakage_power, 2)

    # Build report text based on tool family
    if tool_family == "icc2":
        report = _build_icc2_report(
            design_name, stage, setup_wns, setup_tns, setup_violations,
            hold_wns, hold_tns, hold_violations, worst_endpoint, worst_startpoint,
            timing_met, core_utilization, placement_density, instance_count,
            sequential_count, cell_area, macro_area, total_cell_area, buffer_count,
            max_h_overflow, max_v_overflow, total_overflow, congested_bins,
            worst_congestion_layer, congestion_pass, total_wirelength, drc_total,
            shorts, opens, antenna_violations, route_completed, internal_power,
            switching_power, leakage_power, total_power,
        )
    else:
        report = _build_innovus_report(
            design_name, stage, setup_wns, setup_tns, setup_violations,
            hold_wns, hold_tns, hold_violations, worst_endpoint, worst_startpoint,
            timing_met, core_utilization, placement_density, instance_count,
            sequential_count, cell_area, macro_area, total_cell_area, buffer_count,
            max_h_overflow, max_v_overflow, total_overflow, congested_bins,
            worst_congestion_layer, congestion_pass, total_wirelength, drc_total,
            shorts, opens, antenna_violations, route_completed, internal_power,
            switching_power, leakage_power, total_power,
        )

    # Build oracle answers
    oracle = {
        "tool_family": tool_family,
        "design_name": design_name,
        "stage": stage,
        "setup_wns": setup_wns,
        "setup_tns": setup_tns,
        "setup_violations": setup_violations,
        "hold_wns": hold_wns,
        "hold_tns": hold_tns,
        "hold_violations": hold_violations,
        "worst_endpoint": worst_endpoint,
        "worst_startpoint": worst_startpoint,
        "timing_met": timing_met,
        "core_utilization": core_utilization,
        "placement_density": placement_density,
        "instance_count": instance_count,
        "sequential_count": sequential_count,
        "cell_area": cell_area,
        "macro_area": macro_area,
        "total_cell_area": total_cell_area,
        "buffer_count": buffer_count,
        "max_horizontal_overflow": max_h_overflow,
        "max_vertical_overflow": max_v_overflow,
        "total_overflow": total_overflow,
        "congested_bins": congested_bins,
        "worst_congestion_layer": worst_congestion_layer,
        "congestion_pass": congestion_pass,
        "total_wirelength": total_wirelength,
        "drc_total": drc_total,
        "shorts": shorts,
        "opens": opens,
        "antenna_violations": antenna_violations,
        "route_completed": route_completed,
        "internal_power": internal_power,
        "switching_power": switching_power,
        "leakage_power": leakage_power,
        "total_power": total_power,
    }

    return report, oracle


def _build_icc2_report(
    design_name: str, stage: str, setup_wns: float, setup_tns: float,
    setup_violations: int, hold_wns: float, hold_tns: float, hold_violations: int,
    worst_endpoint: str, worst_startpoint: str, timing_met: bool,
    core_utilization: float, placement_density: float, instance_count: int,
    sequential_count: int, cell_area: float, macro_area: float, total_cell_area: float,
    buffer_count: int, max_h_overflow: float, max_v_overflow: float,
    total_overflow: float, congested_bins: int, worst_congestion_layer: str,
    congestion_pass: bool, total_wirelength: float, drc_total: int, shorts: int,
    opens: int, antenna_violations: int, route_completed: bool,
    internal_power: float, switching_power: float, leakage_power: float,
    total_power: float,
) -> str:
    """Build ICC2-style report text."""
    timing_status = "MET" if timing_met else "VIOLATED"
    congestion_status = "PASS" if congestion_pass else "FAIL"
    route_status = "clean" if route_completed else "dirty"

    return f"""================================================================================
ICC2 Physical Implementation Report
================================================================================

Design          : {design_name}
Stage           : {stage}
Tool Family     : ICC2
Date            : 2026-01-15 10:30:00

--------------------------------------------------------------------------------
Timing Summary
--------------------------------------------------------------------------------
Setup WNS               : {setup_wns}
Setup TNS               : {setup_tns}
Setup Violating Paths   : {setup_violations}
Hold WNS                : {hold_wns}
Hold TNS                : {hold_tns}
Hold Violating Paths    : {hold_violations}
Worst Endpoint          : {worst_endpoint}
Worst Startpoint        : {worst_startpoint}
Timing Status           : {timing_status}

--------------------------------------------------------------------------------
Utilization & Area
--------------------------------------------------------------------------------
Core Utilization        : {core_utilization}%
Placement Density       : {placement_density}
Standard Cell Area      : {cell_area}
Macro Area              : {macro_area}
Total Cell Area         : {total_cell_area}
Instances               : {instance_count}
Sequential Cells        : {sequential_count}
Buffers/Inverters       : {buffer_count}

--------------------------------------------------------------------------------
Congestion Analysis
--------------------------------------------------------------------------------
Max Horizontal Overflow : {max_h_overflow}%
Max Vertical Overflow   : {max_v_overflow}%
Total Overflow          : {total_overflow}
Congested Bins          : {congested_bins}
Worst Congestion Layer  : {worst_congestion_layer}
Congestion Status       : {congestion_status}

--------------------------------------------------------------------------------
Routing & DRC
--------------------------------------------------------------------------------
Total Wirelength        : {total_wirelength}
DRC Violations          : {drc_total}
Shorts                  : {shorts}
Opens                   : {opens}
Antenna Violations      : {antenna_violations}
Route Status            : {route_status}

--------------------------------------------------------------------------------
Power Summary
--------------------------------------------------------------------------------
Internal Power          : {internal_power} mW
Switching Power         : {switching_power} mW
Leakage Power           : {leakage_power} mW
Total Power             : {total_power} mW

================================================================================
End of Report
================================================================================
"""


def _build_innovus_report(
    design_name: str, stage: str, setup_wns: float, setup_tns: float,
    setup_violations: int, hold_wns: float, hold_tns: float, hold_violations: int,
    worst_endpoint: str, worst_startpoint: str, timing_met: bool,
    core_utilization: float, placement_density: float, instance_count: int,
    sequential_count: int, cell_area: float, macro_area: float, total_cell_area: float,
    buffer_count: int, max_h_overflow: float, max_v_overflow: float,
    total_overflow: float, congested_bins: int, worst_congestion_layer: str,
    congestion_pass: bool, total_wirelength: float, drc_total: int, shorts: int,
    opens: int, antenna_violations: int, route_completed: bool,
    internal_power: float, switching_power: float, leakage_power: float,
    total_power: float,
) -> str:
    """Build Innovus-style report text."""
    timing_status = "MET" if timing_met else "VIOLATED"
    congestion_status = "PASS" if congestion_pass else "FAIL"
    route_status = "clean" if route_completed else "dirty"

    return f"""--------------------------------------------------------------
 Innovus Implementation Report
--------------------------------------------------------------

Design          = {design_name}
Stage           = {stage}
Tool Family     = Innovus
Date            = 2026-01-15 10:30:00

--- Timing ---

Setup WNS               = {setup_wns}
Setup TNS               = {setup_tns}
Setup Violating Paths   = {setup_violations}
Hold WNS                = {hold_wns}
Hold TNS                = {hold_tns}
Hold Violating Paths    = {hold_violations}
Worst Endpoint          = {worst_endpoint}
Worst Startpoint        = {worst_startpoint}
Timing Status           = {timing_status}

--- Utilization ---

Core Utilization        = {core_utilization}%
Placement Density       = {placement_density}
Standard Cell Area      = {cell_area}
Macro Area              = {macro_area}
Total Cell Area         = {total_cell_area}
Instances               = {instance_count}
Sequential Cells        = {sequential_count}
Buffers/Inverters       = {buffer_count}

--- Congestion ---

Max Horizontal Overflow = {max_h_overflow}%
Max Vertical Overflow   = {max_v_overflow}%
Total Overflow          = {total_overflow}
Congested Bins          = {congested_bins}
Worst Congestion Layer  = {worst_congestion_layer}
Congestion Status       = {congestion_status}

--- Routing ---

Total Wirelength        = {total_wirelength}
DRC Violations          = {drc_total}
Shorts                  = {shorts}
Opens                   = {opens}
Antenna Violations      = {antenna_violations}
Route Status            = {route_status}

--- Power ---

Internal Power          = {internal_power} mW
Switching Power         = {switching_power} mW
Leakage Power           = {leakage_power} mW
Total Power             = {total_power} mW

--------------------------------------------------------------
End of Report
--------------------------------------------------------------
"""


def generate_task_metadata(task_id: str, tool_family: str, difficulty: str,
                           question_types: list[str]) -> dict[str, Any]:
    """Generate task metadata dict."""
    return {
        "task_id": task_id,
        "track": "p8_pnr_report_qa",
        "tool": ["icc2" if tool_family == "icc2" else "innovus"],
        "difficulty": difficulty,
        "data_type": "template_synthetic",
        "resource_preset": "fast",
        "timeout_sec": 60,
        "max_tool_calls": 10,
        "max_patch_attempts": 3,
        "max_output_tokens": 16000,
        "files": {
            "visible": ["report.txt", "prompt.md"],
            "editable": ["answers.json"],
            "hidden": ["answers.json"],
            "forbidden": ["report.txt"],
        },
        "run_command": "true",
        "scoring": {
            "weights": {
                "answer_match": 0.9,
                "explanation": 0.1,
            },
            "evaluator": "pnr_report_qa.PnRReportQAEvaluator",
            "explanation_weight": 0.1,
        },
        "sanitizer": {
            "enabled": True,
        },
        "generator": {
            "script": "p8_pnr_report_qa_gen.py",
            "tool_family": tool_family,
            "question_types": question_types,
        },
    }


def generate_prompt(question_types: list[str], tool_family: str) -> str:
    """Generate the prompt.md content."""
    questions = []
    for qt in question_types:
        if qt == "setup_timing":
            questions.append("- What is the setup WNS (in ns)?")
            questions.append("- What is the setup TNS (in ns)?")
            questions.append("- How many setup violating paths are there?")
        elif qt == "hold_timing":
            questions.append("- What is the hold WNS (in ns)?")
            questions.append("- What is the hold TNS (in ns)?")
            questions.append("- How many hold violating paths are there?")
        elif qt == "timing_path":
            questions.append("- What is the worst endpoint?")
            questions.append("- What is the worst startpoint?")
            questions.append("- Is timing met? (true/false)")
        elif qt == "utilization":
            questions.append("- What is the core utilization (in %)?")
            questions.append("- What is the placement density?")
            questions.append("- How many instances are there?")
            questions.append("- How many sequential cells are there?")
        elif qt == "area":
            questions.append("- What is the standard cell area?")
            questions.append("- What is the macro area?")
            questions.append("- What is the total cell area?")
            questions.append("- How many buffers/inverters are there?")
        elif qt == "congestion":
            questions.append("- What is the max horizontal overflow (in %)?")
            questions.append("- What is the max vertical overflow (in %)?")
            questions.append("- What is the total overflow?")
            questions.append("- How many congested bins are there?")
            questions.append("- What is the worst congestion layer?")
            questions.append("- Does congestion pass? (true/false)")
        elif qt == "routing":
            questions.append("- What is the total wirelength?")
            questions.append("- How many DRC violations are there?")
            questions.append("- How many shorts are there?")
            questions.append("- How many opens are there?")
            questions.append("- How many antenna violations are there?")
            questions.append("- Is route status clean? (true/false)")
        elif qt == "power":
            questions.append("- What is the internal power (in mW)?")
            questions.append("- What is the switching power (in mW)?")
            questions.append("- What is the leakage power (in mW)?")
            questions.append("- What is the total power (in mW)?")
        elif qt == "flow_status":
            questions.append("- What is the tool family? (icc2/innovus)")
            questions.append("- What is the design name?")
            questions.append("- What is the current stage?")

    tool_name = "ICC2" if tool_family == "icc2" else "Innovus"
    return f"""# PnR Report QA Task

You are given a {tool_name} physical implementation report in `report.txt`.

Read the report and answer the following questions. Write your answers to `answers.json` as a JSON object with the field name as key and your answer as value.

**Important:**
- For numeric answers, use the exact value from the report
- For string answers, use the exact text from the report
- For boolean answers, use `true` or `false`

## Questions

{chr(10).join(questions)}

## Output Format

Write your answers to `answers.json`:
```json
{{
  "field_name": "your_answer"
}}
```

Replace `field_name` with the actual field name (e.g., `setup_wns`, `tool_family`, etc.).
"""


def select_question_types(rng: random.Random, count: int = 3) -> list[str]:
    """Select a random subset of question types."""
    all_types = list(QUESTION_TYPES.keys())
    return rng.sample(all_types, min(count, len(all_types)))
