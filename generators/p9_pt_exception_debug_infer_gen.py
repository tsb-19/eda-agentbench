"""P9 ExceptionDebug — INFERRED-INTENT falsification variant.

Why this file exists
--------------------
The first P9 probe (stated-intent) COLLAPSED: DeepSeek-V4-Pro / GLM-5.1 / Qwen3.7-Max each
scored a flawless 1.00 on all 8 tasks, both categories (2026-06-23). Diagnosis: the prompt
STATED the timing intent ("this transfer is two-cycle"), so the task reduced to mechanical
exception synthesis — the hidden variable was written in prose. The grading mechanism
(necessary-but-not-sufficient + hidden holdout + anti-cheat) was sound; the TASK was too easy.

This variant is the make-or-break falsification test (user-directed): remove the stated intent
and force the model to RECOVER it from a visible behavioral RTL spec (`design_rtl.v`), whose
capture-enable cadence is the only evidence of which transfers are multi-cycle / quasi-static.
Everything else — netlist, scalar library, two-session laundering, anti-cheat — is reused
verbatim from `p9_pt_exception_debug_gen` (imported, not copied), so the banked track and its
tests are untouched.

VERDICT RULE: if the frontier-3 still hit ~1.00 here, ExceptionDebug is retired entirely; the
hardness must come from somewhere search/inference cannot shortcut (the LEC-Attribution pivot).

What is added over the stated variant
-------------------------------------
* `design_rtl.v` (VISIBLE, forbidden-to-edit): behavioral spec. A small `phase` counter gates a
  capture-enable that fires once every `_MC_CYCLES` clocks for the multi-cycle transfer; sibling
  registers update every clock. The model must trace enable -> cadence -> which path is multicycle.
* A `timed1` grader check (closes the blanket-multicycle hole): asserts a single-cycle path's
  slack stays at its 1-cycle value (unrelaxed). Without it, a model could silence the violation by
  blanket `set_multicycle_path` and score 1.0 — which would make a "collapse" result meaningless.
  Score ladder: correct-narrow 1.0 / blanket 0.5 / did-nothing 0.5 / mis-attributed 0.0.

The grading protocol (EXC_SCORE / EXC_EXEC_OK), evaluator, schema track and id pattern are all
shared with the stated variant — no core, schema, or evaluator change is required.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from generators.base import BaseGenerator
from generators.p9_pt_exception_debug_gen import (
    ASSET_DIR,
    _MC_CYCLES,
    _base_sdc,
    _mc_depth,
    _mc_lines,
    _netlist,
    _run_hidden_sh,
    _run_hidden_tcl,
    _run_public_sh,
    _run_public_tcl,
    _single_depth,
    _slack,
    THEMES_A,
    THEMES_B,
)

# tolerance for the timed1 "is this path unrelaxed?" check. Single- vs multi-cycle slack differ
# by exactly `period` (>= 0.5 ns), so any non-trivial tolerance separates them; 0.05 = _MARGIN.
_T1_TOL = 0.05


# --- behavioral RTL evidence (the recoverable hidden variable) --------------

def _rtl_b(theme: dict, cycles: int) -> str:
    """Behavioral spec whose capture-enable cadence implies the multicycle intent."""
    mc, singles = theme["mc"], theme["single"]
    ins = [mc["in"]] + [s["in"] for s in singles]
    outs = [mc["out"]] + [s["out"] for s in singles]
    L = [
        f"// Behavioral spec for {theme['top']}. PrimeTime times the synthesized datapath in",
        "// design_netlist.v; THIS file defines each register transfer's capture cadence.",
        "// The timing intent (which transfers may take more than one cycle) is NOT stated",
        "// anywhere -- infer it from the capture-enable logic below.",
        f"module {theme['top']}_spec (clk, rst, {', '.join(ins + outs)});",
        "  input clk;",
        "  input rst;",
    ]
    L += [f"  input {p};" for p in ins]
    L += [f"  output {p};" for p in outs]
    L += [
        "",
        f"  // cadence counter: {mc['dst']}_en is asserted once every {cycles} clocks",
        "  reg [1:0] phase;",
        "  always @(posedge clk or posedge rst)",
        "    if (rst) phase <= 2'd0;",
        f"    else     phase <= (phase == 2'd{cycles - 1}) ? 2'd0 : phase + 2'd1;",
        f"  wire {mc['dst']}_en = (phase == 2'd0);",
        "",
        f"  // multi-cycle transfer: {mc['dst']} samples {mc['src']} only when enabled,",
        f"  //   i.e. once per {cycles} clocks -> this path may take {cycles} cycles to settle",
        f"  reg {mc['src']}, {mc['dst']};",
        f"  always @(posedge clk)                    {mc['src']} <= {mc['in']};",
        f"  always @(posedge clk) if ({mc['dst']}_en) {mc['dst']} <= {mc['src']};",
        f"  assign {mc['out']} = {mc['dst']};",
        "",
        "  // single-cycle transfers: updated on EVERY clock -> must meet timing at 1 cycle",
    ]
    for s in singles:
        L += [
            f"  reg {s['src']}, {s['dst']};",
            f"  always @(posedge clk) {s['src']} <= {s['in']};",
            f"  always @(posedge clk) {s['dst']} <= {s['src']};",
            f"  assign {s['out']} = {s['dst']};",
        ]
    L += ["endmodule", ""]
    return "\n".join(L)


def _rtl_a(theme: dict) -> str:
    """Behavioral spec showing which sink is quasi-static (written only at boot) vs functional."""
    cfg, qs, dp = theme["cfg"], theme["qs"], theme["dp"]
    cfg_in, qs_out, dp_out = theme["cfg_in"], theme["qs_out"], theme["dp_out"]
    L = [
        f"// Behavioral spec for {theme['top']}. PrimeTime times the synthesized datapath in",
        "// design_netlist.v; THIS file shows how each register is updated. Which transfers are",
        "// quasi-static (safe to exclude) vs functional (must meet timing) is NOT stated --",
        "// infer it from the write-enable conditions below.",
        f"module {theme['top']}_spec (clk, rst, {cfg_in}, {qs_out}, {dp_out});",
        "  input clk;",
        "  input rst;",
        f"  input {cfg_in};",
        f"  output {qs_out};",
        f"  output {dp_out};",
        "",
        "  // boot controller: cfg_we is high only in the first cycle after reset",
        "  reg boot_done;",
        "  always @(posedge clk or posedge rst)",
        "    if (rst) boot_done <= 1'b0; else boot_done <= 1'b1;",
        "  wire cfg_we = ~boot_done;",
        "",
        f"  // {cfg} / {qs}: written ONLY at boot (cfg_we) -> quasi-static once configured,",
        f"  //   so the {cfg} -> {qs} path never toggles in operation",
        f"  reg {cfg}, {qs};",
        f"  always @(posedge clk) if (cfg_we) {cfg} <= {cfg_in};",
        f"  always @(posedge clk) if (cfg_we) {qs}  <= {cfg};",
        f"  assign {qs_out} = {qs};",
        "",
        f"  // {dp}: recomputed from {cfg} on EVERY clock during operation,",
        f"  //   so the {cfg} -> {dp} path is a real functional path that must meet timing",
        f"  reg {dp};",
        f"  always @(posedge clk) {dp} <= {cfg} ^ {cfg_in};",
        f"  assign {dp_out} = {dp};",
        "endmodule",
        "",
    ]
    return "\n".join(L)


# --- grade phase with the added timed1 (anti-blanket) check -----------------

def _run_grade_tcl_ext(top: str, checks: list[tuple]) -> str:
    """Like the banked grader but adds a `timed1` check type:
      meet            : path ANALYZED (sizeof>0) AND slack >= 0
      exclude         : path stays EXCLUDED (sizeof == 0)
      timed1 <exp>    : path ANALYZED AND |slack - exp| <= tol  (timed at 1 cycle, NOT relaxed)
    The timed1 case catches a blanket set_multicycle_path that would otherwise silence the
    violation for free. EXC_SCORE = passed / total."""
    pairs = " ".join("{%s}" % " ".join(str(x) for x in c) for c in checks)
    return f"""\
# Hidden grade phase — fresh session, reads only the laundered (trusted) SDC.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design {top}
read_sdc applied_hidden.sdc

set checks {{ {pairs} }}
set total 0
set pass 0
set detail ""
foreach c $checks {{
  incr total
  set typ [lindex $c 0]
  set frm [lindex $c 1]
  set to  [lindex $c 2]
  set ps [get_timing_paths -from [get_pins $frm] -to [get_pins $to] -delay_type max]
  set n [sizeof_collection $ps]
  if {{$typ eq "exclude"}} {{
    if {{$n == 0}} {{
      incr pass
      append detail " EXOK:$frm->$to"
    }} else {{
      set slk [get_attribute [index_collection $ps 0] slack]
      append detail " NOTEXCLUDED:$to=$slk"
    }}
  }} elseif {{$typ eq "timed1"}} {{
    set exp [lindex $c 3]
    if {{$n == 0}} {{
      append detail " NOTTIMED:$frm->$to"
    }} else {{
      set slk [get_attribute [index_collection $ps 0] slack]
      if {{[expr {{abs($slk - $exp)}}] <= {_T1_TOL}}} {{
        incr pass
        append detail " T1OK:$to=$slk"
      }} else {{
        append detail " RELAXED:$to=$slk/exp$exp"
      }}
    }}
  }} else {{
    if {{$n == 0}} {{
      append detail " EXCLUDED:$frm->$to"
    }} else {{
      set slk [get_attribute [index_collection $ps 0] slack]
      if {{$slk >= 0}} {{
        incr pass
        append detail " OK:$to=$slk"
      }} else {{
        append detail " VIOL:$to=$slk"
      }}
    }}
  }}
}}
set score [expr {{double($pass)/$total}}]
puts "EXC_SCORE: [format %.3f $score]"
puts "EXC_DETAIL:$detail"
exit
"""


# --- per-category builders (inferred intent) -------------------------------

def _build_b_infer(theme: dict, period: float, rng) -> dict:
    mc, singles = theme["mc"], theme["single"]
    mc_depth = _mc_depth(period, rng)

    inputs = [mc["in"]] + [s["in"] for s in singles]
    outputs = [mc["out"]] + [s["out"] for s in singles]
    regs = [(mc["src"], mc["in"], mc["src"] + "_q"), (mc["dst"], mc["dst"] + "_d", mc["out"])]
    chains = [(mc["src"] + "_mc", mc["src"] + "_q", mc["dst"] + "_d", mc_depth)]
    single_depths = []
    for s in singles:
        sd = _single_depth(period, rng)
        single_depths.append(sd)
        regs += [(s["src"], s["in"], s["src"] + "_q"), (s["dst"], s["dst"] + "_d", s["out"])]
        chains += [(s["src"] + "_s", s["src"] + "_q", s["dst"] + "_d", sd)]

    base = _base_sdc(period, inputs, outputs)
    checks = [("meet", f"{mc['src']}/CK", f"{mc['dst']}/D")]
    for s, sd in zip(singles, single_depths):
        checks.append(("timed1", f"{s['src']}/CK", f"{s['dst']}/D", _slack(1, period, sd)))

    symptom = ("`report_timing` reports a setup violation on one transfer. Bring the constraints "
               "into agreement with the per-transfer cadences defined in `design_rtl.v`.")
    return {
        "top": theme["top"], "inputs": inputs, "outputs": outputs,
        "netlist": _netlist(theme["top"], inputs, outputs, regs, chains),
        "rtl": _rtl_b(theme, _MC_CYCLES),
        "golden_sdc": base + _mc_lines(mc["src"], mc["dst"], _MC_CYCLES),
        "buggy_sdc": base, "checks": checks, "symptom": symptom,
        "bug_type": "missing_multicycle_inferred", "difficulty": "hard",
        "gen_meta": {"category": "B", "mode": "inferred", "period_ns": period,
                     "mc_cycles": _MC_CYCLES, "mc_depth": mc_depth,
                     "single_depths": single_depths,
                     "expected_slack_1cyc": _slack(1, period, mc_depth),
                     "expected_slack_ncyc": _slack(_MC_CYCLES, period, mc_depth)},
    }


def _build_a_infer(theme: dict, period: float, rng) -> dict:
    cfg, qs, dp = theme["cfg"], theme["qs"], theme["dp"]
    qs_depth = _mc_depth(period, rng)       # deep: would VIOLATE if it were timed
    dp_depth = _single_depth(period, rng)   # shallow: MEETS at single cycle

    inputs = [theme["cfg_in"]]
    outputs = [theme["qs_out"], theme["dp_out"]]
    regs = [(cfg, theme["cfg_in"], cfg + "_q"),
            (qs, qs + "_d", theme["qs_out"]),
            (dp, dp + "_d", theme["dp_out"])]
    chains = [(cfg + "_qs", cfg + "_q", qs + "_d", qs_depth),
              (cfg + "_dp", cfg + "_q", dp + "_d", dp_depth)]

    base = _base_sdc(period, inputs, outputs)
    golden = base + f"set_false_path -from [get_pins {cfg}/CK] -to [get_pins {qs}/D]\n"
    buggy = base + f"set_false_path -from [get_pins {cfg}/CK]\n"   # over-broad: no -to
    checks = [("meet", f"{cfg}/CK", f"{dp}/D"), ("exclude", f"{cfg}/CK", f"{qs}/D")]
    symptom = ("`report_timing` reports no setup violations. The constraints are nonetheless under "
               "suspicion: from `design_rtl.v`, determine which transfers are genuinely quasi-static "
               "(safe to exclude) and which are functional paths that must remain analyzed and meet "
               "timing.")
    return {
        "top": theme["top"], "inputs": inputs, "outputs": outputs,
        "netlist": _netlist(theme["top"], inputs, outputs, regs, chains),
        "rtl": _rtl_a(theme),
        "golden_sdc": golden, "buggy_sdc": buggy, "checks": checks, "symptom": symptom,
        "bug_type": "overbroad_false_path_inferred", "difficulty": "hard",
        "gen_meta": {"category": "A", "mode": "inferred", "period_ns": period,
                     "qs_depth": qs_depth, "dp_depth": dp_depth,
                     "expected_qs_slack_if_timed": _slack(1, period, qs_depth),
                     "expected_dp_slack": _slack(1, period, dp_depth)},
    }


def _prompt_infer(top: str, period: float, port_list: str, symptom: str) -> str:
    return f"""\
# Timing Signoff Debug: `{top}`

You own static-timing signoff for the `{top}` block. The constraint file `constraints.sdc` is
failing signoff review.

## What you are given
- `design_netlist.v` — the synthesized gate-level datapath PrimeTime times (one clock `clk`,
  period **{period} ns**).
- `design_rtl.v` — the behavioral RTL spec. Its capture-enable logic defines the cadence of each
  register transfer: some registers update on every clock, others only once every few clocks (or
  only at boot). **The timing intent is not stated in words — you must infer it from this RTL.**
- `constraints.sdc` — the constraints under review (the only editable file).

## Symptom
{symptom}

## Your task
From `design_rtl.v`, determine which register transfers are genuinely multi-cycle or quasi-static
and which must meet timing every cycle, then correct `constraints.sdc` so every transfer is
constrained according to its real cadence — no broader, no narrower.

## Rules
- Only `constraints.sdc` is editable; all other files are read-only.
- A clean `report_timing` is **necessary but not sufficient**. Signoff rejects *over-constraining*
  (relaxing, cutting, or masking a path that must meet timing every cycle) and *under-constraining*
  (failing to relax a genuine multi-cycle path or exclude a genuine quasi-static one). Applying an
  exception too broadly is as wrong as omitting it.
- Run `bash run_public.sh` for live `report_timing` / `report_exceptions` feedback. There is no
  answer key; reason about correctness the way an engineer does before signoff.

## Design ports
{port_list}
"""


class P9InferGenerator(BaseGenerator):
    """Inferred-intent P9 falsification tasks. Even task_index -> Category B (missing multicycle,
    cadence inferred from RTL); odd -> Category A (over-broad false_path, quasi-static inferred).
    id_start defaults to 2001 to stay clear of the stated-variant id space (0000-0999)."""

    def __init__(self, seed: int, output_dir: Path, id_start: int = 2001):
        super().__init__(seed, output_dir)
        self.id_start = id_start

    def generate_one(self, task_index: int) -> Path:
        display_index = task_index + self.id_start
        period = self.rng.choice([0.5, 0.6, 0.8, 1.0])
        if task_index % 2 == 0:
            b = _build_b_infer(THEMES_B[(task_index // 2) % len(THEMES_B)], period, self.rng)
        else:
            b = _build_a_infer(THEMES_A[(task_index // 2) % len(THEMES_A)], period, self.rng)

        top = b["top"]
        task_id = f"pt_exc_debug_{display_index:04d}"
        task_dir = self.output_dir / task_id
        (task_dir / "files").mkdir(parents=True, exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # files/ (visible) — netlist + RTL evidence + library + buggy constraints + public runner
        (task_dir / "files" / "design_netlist.v").write_text(b["netlist"])
        (task_dir / "files" / "design_rtl.v").write_text(b["rtl"])
        shutil.copy2(ASSET_DIR / "tiny.lib", task_dir / "files" / "tiny.lib")
        shutil.copy2(ASSET_DIR / "tiny.db", task_dir / "files" / "tiny.db")
        (task_dir / "files" / "constraints.sdc").write_text(b["buggy_sdc"])
        (task_dir / "files" / "run_public.tcl").write_text(_run_public_tcl(top))
        (task_dir / "files" / "run_public.sh").write_text(_run_public_sh())
        (task_dir / "files" / "run_public.sh").chmod(0o755)

        # hidden/ — two-session grader (extended with the timed1 check)
        (task_dir / "hidden" / "run_hidden.tcl").write_text(_run_hidden_tcl(top))
        (task_dir / "hidden" / "run_grade.tcl").write_text(_run_grade_tcl_ext(top, b["checks"]))
        (task_dir / "hidden" / "run_hidden.sh").write_text(_run_hidden_sh())
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)

        # solution/ — golden constraints (precise, spec-consistent exception)
        (task_dir / "solution" / "constraints.sdc").write_text(b["golden_sdc"])

        port_list = ", ".join(["clk"] + b["inputs"] + b["outputs"])
        (task_dir / "prompt.md").write_text(
            _prompt_infer(top, b["gen_meta"]["period_ns"], port_list, b["symptom"]))

        meta = {
            "task_id": task_id,
            "track": "p9_pt_exception_debug",
            "tool": ["pt"],
            "difficulty": b["difficulty"],
            "data_type": "template_synthetic",
            "resource_preset": "standard",
            "timeout_sec": 300,
            "max_tool_calls": 30,
            "max_patch_attempts": 8,
            "max_output_tokens": 32000,
            "files": {
                "visible": ["design_netlist.v", "design_rtl.v", "tiny.lib", "tiny.db",
                            "constraints.sdc", "run_public.sh", "run_public.tcl"],
                "editable": ["constraints.sdc"],
                "hidden": ["run_hidden.sh", "run_hidden.tcl", "run_grade.tcl"],
                "forbidden": ["design_netlist.v", "design_rtl.v", "tiny.lib", "tiny.db",
                              "run_public.sh", "run_public.tcl",
                              "run_hidden.sh", "run_hidden.tcl", "run_grade.tcl"],
            },
            "run_command": "bash run_hidden.sh",
            "scoring": {
                "weights": {"exception_check": 0.6, "execution_pass": 0.3, "explanation": 0.1},
                "evaluator": "pt_exception_debug.PTExceptionDebugEvaluator",
                "explanation_weight": 0.1,
            },
            "sanitizer": {"enabled": True},
            "generator": dict({"script": "p9_pt_exception_debug_infer_gen.py", "seed": self.seed,
                               "bug_type": b["bug_type"], "theme": top, "task_index": task_index,
                               "intent_mode": "inferred"},
                              **b["gen_meta"]),
            "expected_error_category": b["bug_type"],
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
        return task_dir
