"""P9 PrimeTime Exception Debug generator — timing-exception diagnosis that resists
the P5/P6/P7 frontier collapse.

Why this track exists
---------------------
P5/P6/P7 debug tracks saturate because each bug is a single named symptom that one tool
run fully localizes. Here the root cause is a HIDDEN VARIABLE — the design's timing intent
(which register transfers may legitimately take >1 cycle, which are quasi-static and may be
cut) — that the netlist cannot reveal and the prompt does not name. The defining contract:

    real `report_timing` is NECESSARY BUT NOT SUFFICIENT.

Grading asserts each path the spec requires to be timed stays ANALYZED (not exception'd
away) AND meets; and each path the spec excludes STAYS excluded. So neither over-constraining
(cutting a real path to silence a violation) nor under-constraining (deleting a required
exception) can reach the golden score. Proven on b04 (PrimeTime S-2021.06-SP5, 2026-06-22).

Two bug categories
------------------
* Category B (missing_multicycle): a transfer that is functionally multi-cycle (captured on
  alternate clocks) shows a single-cycle setup VIOLATION. Correct fix = set_multicycle_path
  on exactly that transfer. The tempting wrong fix (set_false_path to silence it) is caught:
  the transfer must stay analyzed and meet at its multi-cycle requirement.
* Category A (overbroad_false_path): a config register feeds BOTH a quasi-static sink (rightly
  excluded) AND a real datapath register (must meet). The bug is an over-broad false_path
  (`-from cfg/CK` with no `-to`) that also masks the datapath path. `report_timing` is
  DECEPTIVELY CLEAN — a naive agent declares victory. Correct fix = scope the exception to the
  config sink only. Caught two ways: the datapath path must be analyzed+meet (over-broad bug
  fails it), and the quasi-static path must stay excluded (deleting the exception fails it).

Mechanism (generator-controlled, deterministic)
-----------------------------------------------
A tiny scalar-delay Liberty (generators/assets/p9_pt_exception_debug/tiny.lib, compiled to
tiny.db via dc_shell `enable_write_lib_mode; read_lib; write_lib -format db`) ships in each
task's files/ (VISIBLE — the agent workspace is files/-flat). Delays are exact: BUF 0.10ns,
DFF clk->Q 0.08, setup 0.02; a depth-D chain between two DFFs has arrival 0.08+D*0.10, so
slack = cycles*period - 0.10 - D*0.10 is known in closed form. PrimeTime reads design_netlist.v
+ tiny.db, applies the agent's constraints.sdc, and a path-level grader asserts typed checks
via get_timing_paths/get_attribute slack (sizeof_collection==0 == path exception'd away).

Forge-resistance (P7's verified primitives): the hidden runner launders the agent SDC in one
pt_shell session (read_sdc sandboxes Tcl proc/exit; write_sdc serializes the genuine constraint
state to applied_hidden.sdc, overwriting anything the agent's SDC wrote) and grades in a FRESH
session reading only the laundered SDC. The .sh prefixes the apply-session output so an injected
`EXC_SCORE:` cannot match the real `^EXC_SCORE:`.
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

from generators.base import BaseGenerator

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "p9_pt_exception_debug"

# Cell timing from tiny.lib (must stay in sync with the asset).
_CLK_Q = 0.08
_SETUP = 0.02
_BUF = 0.10
_FIXED = _CLK_Q + _SETUP   # 0.10: the non-chain part of every reg->reg path slack
_MARGIN = 0.05             # keep slacks clear of 0 so float jitter can't flip a verdict

_PERIODS = [0.5, 0.6, 0.8, 1.0]
_MC_CYCLES = 2  # Phase 1/2: fixed 2-cycle transfer (the b04-proven case)


# --- timing math -----------------------------------------------------------

def _mc_depth(period: float, rng) -> int:
    """Buffer depth so a transfer VIOLATES at 1 cycle and MEETS at _MC_CYCLES, each by
    >= _MARGIN. slack(c) = c*period - _FIXED - depth*_BUF."""
    lo = int(math.ceil((period - _FIXED + _MARGIN) / _BUF - 1e-9))
    hi = int(math.floor((_MC_CYCLES * period - _FIXED - _MARGIN) / _BUF + 1e-9))
    lo = max(lo, 1)
    return rng.randint(lo, max(lo, hi))


def _single_depth(period: float, rng) -> int:
    """Buffer depth so a single-cycle transfer MEETS by at least _MARGIN."""
    hi = int(math.floor((period - _FIXED - _MARGIN) / _BUF + 1e-9))
    return rng.randint(1, max(1, hi))


def _slack(cycles: int, period: float, depth: int) -> float:
    return round(cycles * period - _FIXED - depth * _BUF, 6)


# --- netlist (register + chain model; supports fanout) ---------------------

def _chain_between(prefix: str, src: str, dst: str, depth: int) -> tuple[list[str], list[str]]:
    """BUFX1 chain driving `dst` from `src` over `depth` cells. Returns (lines, intermediate_nets)."""
    lines, nets, prev = [], [], src
    for i in range(depth):
        out = dst if i == depth - 1 else f"{prefix}_n{i}"
        lines.append(f"  BUFX1 {prefix}_b{i} (.A({prev}), .Y({out}));")
        if i != depth - 1:
            nets.append(out)
        prev = out
    return lines, nets


def _netlist(top: str, inputs: list[str], outputs: list[str],
             regs: list[tuple[str, str, str]], chains: list[tuple[str, str, str, int]]) -> str:
    """regs: (name, d_net, q_net). chains: (prefix, src_net, dst_net, depth). A q_net may
    drive several chains (fanout); shared/internal nets are declared once."""
    head = [f"// Gate-level netlist for {top} — timed by PrimeTime against tiny.db",
            f"module {top} (clk, {', '.join(inputs + outputs)});",
            "  input clk;"]
    for p in inputs:
        head.append(f"  input {p};")
    for p in outputs:
        head.append(f"  output {p};")

    chain_lines: list[str] = []
    chain_nets: list[str] = []
    for prefix, src, dst, depth in chains:
        cl, nets = _chain_between(prefix, src, dst, depth)
        chain_lines += cl
        chain_nets += nets

    seen = set(inputs) | set(outputs)
    decl: list[str] = []
    for name, d_net, q_net in regs:
        for n in (d_net, q_net):
            if n not in seen and n not in decl:
                decl.append(n)
    for n in chain_nets:
        if n not in seen and n not in decl:
            decl.append(n)

    body = [f"  wire {n};" for n in decl]
    for name, d_net, q_net in regs:
        body.append(f"  DFFX1 {name} (.D({d_net}), .CK(clk), .Q({q_net}));")
    body += chain_lines
    return "\n".join(head + body + ["endmodule", ""])


def _base_sdc(period: float, inputs: list[str], outputs: list[str]) -> str:
    return (f"create_clock -name clk -period {period} [get_ports clk]\n"
            f"set_input_delay  0.05 -clock clk [get_ports {{{' '.join(inputs)}}}]\n"
            f"set_output_delay 0.05 -clock clk [get_ports {{{' '.join(outputs)}}}]\n")


def _mc_lines(src: str, dst: str, cycles: int) -> str:
    frm, to = f"[get_pins {src}/CK]", f"[get_pins {dst}/D]"
    return (f"set_multicycle_path {cycles} -setup -from {frm} -to {to}\n"
            f"set_multicycle_path {cycles - 1} -hold  -from {frm} -to {to}\n")


# --- design themes ---------------------------------------------------------

THEMES_B = [
    {"top": "mac_unit",
     "mc": {"src": "prod_reg", "dst": "acc_reg", "in": "a_in", "out": "acc_out",
            "intent": "The accumulator `acc_reg` latches the product register `prod_reg` on "
                      "every **second** clock (enabled on alternate cycles), so the architects "
                      "allow this accumulate transfer two clock periods to settle."},
     "single": [{"src": "cmd_reg", "dst": "stat_reg", "in": "cmd_in", "out": "stat_out"}]},
    {"top": "fir_tap",
     "mc": {"src": "coef_reg", "dst": "mult_reg", "in": "coef_in", "out": "y_out",
            "intent": "The coefficient register `coef_reg` drives the tap multiplier `mult_reg`, "
                      "which is clock-enabled to capture once every **two** cycles; this multiply "
                      "is specified as a two-cycle transfer."},
     "single": [{"src": "din_reg", "dst": "sum_reg", "in": "x_in", "out": "y_sum"}]},
    {"top": "spi_core",
     "mc": {"src": "shift_reg", "dst": "cap_reg", "in": "mosi_in", "out": "rx_out",
            "intent": "The capture register `cap_reg` samples the shift register `shift_reg` at "
                      "half the core clock rate (every **second** edge), a documented two-cycle path."},
     "single": [{"src": "cnt_reg", "dst": "flag_reg", "in": "tick_in", "out": "flag_out"}]},
    {"top": "alu_pipe",
     "mc": {"src": "op_reg", "dst": "res_reg", "in": "op_in", "out": "res_out",
            "intent": "The result register `res_reg` accepts the wide ALU result from `op_reg` once "
                      "every **two** clocks (the ALU is multi-cycle for this operation)."},
     "single": [{"src": "flag_reg", "dst": "cc_reg", "in": "flag_in", "out": "cc_out"}]},
]

THEMES_A = [
    {"top": "cfg_bus", "cfg": "cfg_reg", "qs": "mode_reg", "dp": "data_reg",
     "cfg_in": "cfg_in", "qs_out": "mode_out", "dp_out": "data_out"},
    {"top": "vid_ctrl", "cfg": "ctrl_reg", "qs": "opt_reg", "dp": "pix_reg",
     "cfg_in": "ctrl_in", "qs_out": "opt_out", "dp_out": "pix_out"},
    {"top": "dma_eng", "cfg": "desc_reg", "qs": "mode2_reg", "dp": "addr_reg",
     "cfg_in": "desc_in", "qs_out": "mode2_out", "dp_out": "addr_out"},
    {"top": "rf_front", "cfg": "gain_reg", "qs": "band_reg", "dp": "samp_reg",
     "cfg_in": "gain_in", "qs_out": "band_out", "dp_out": "samp_out"},
]


# --- per-category builders (return a uniform bundle) -----------------------

def _build_b(theme: dict, period: float, rng) -> dict:
    mc = theme["mc"]
    singles = theme["single"]
    mc_depth = _mc_depth(period, rng)

    inputs = [mc["in"]] + [s["in"] for s in singles]
    outputs = [mc["out"]] + [s["out"] for s in singles]
    regs = [(mc["src"], mc["in"], mc["src"] + "_q"), (mc["dst"], mc["dst"] + "_d", mc["out"])]
    chains = [(mc["src"] + "_mc", mc["src"] + "_q", mc["dst"] + "_d", mc_depth)]
    for s in singles:
        sd = _single_depth(period, rng)
        regs += [(s["src"], s["in"], s["src"] + "_q"), (s["dst"], s["dst"] + "_d", s["out"])]
        chains += [(s["src"] + "_s", s["src"] + "_q", s["dst"] + "_d", sd)]

    base = _base_sdc(period, inputs, outputs)
    checks = [("meet", f"{mc['src']}/CK", f"{mc['dst']}/D")]
    checks += [("meet", f"{s['src']}/CK", f"{s['dst']}/D") for s in singles]
    intent = (f"- {mc['intent']}\n"
              f"- Every other register transfer is ordinary single-cycle logic and **must meet "
              f"timing** at `clk`.")
    symptom = ("`report_timing` reports a setup violation. Resolve it so the constraints reflect "
               "the design intent above.")
    return {
        "top": theme["top"], "inputs": inputs, "outputs": outputs,
        "netlist": _netlist(theme["top"], inputs, outputs, regs, chains),
        "golden_sdc": base + _mc_lines(mc["src"], mc["dst"], _MC_CYCLES),
        "buggy_sdc": base, "checks": checks, "intent": intent, "symptom": symptom,
        "bug_type": "missing_multicycle", "difficulty": "medium",
        "gen_meta": {"category": "B", "period_ns": period, "mc_cycles": _MC_CYCLES,
                     "mc_depth": mc_depth,
                     "expected_slack_1cyc": _slack(1, period, mc_depth),
                     "expected_slack_ncyc": _slack(_MC_CYCLES, period, mc_depth)},
    }


def _build_a(theme: dict, period: float, rng) -> dict:
    cfg, qs, dp = theme["cfg"], theme["qs"], theme["dp"]
    qs_depth = _mc_depth(period, rng)       # deep: would VIOLATE if it were timed
    dp_depth = _single_depth(period, rng)   # shallow: MEETS at single cycle

    inputs = [theme["cfg_in"]]
    outputs = [theme["qs_out"], theme["dp_out"]]
    regs = [(cfg, theme["cfg_in"], cfg + "_q"),
            (qs, qs + "_d", theme["qs_out"]),
            (dp, dp + "_d", theme["dp_out"])]
    chains = [(cfg + "_qs", cfg + "_q", qs + "_d", qs_depth),   # fanout 1: config sink
              (cfg + "_dp", cfg + "_q", dp + "_d", dp_depth)]   # fanout 2: datapath (must meet)

    base = _base_sdc(period, inputs, outputs)
    golden = base + f"set_false_path -from [get_pins {cfg}/CK] -to [get_pins {qs}/D]\n"
    buggy = base + f"set_false_path -from [get_pins {cfg}/CK]\n"   # over-broad: no -to
    checks = [("meet", f"{cfg}/CK", f"{dp}/D"), ("exclude", f"{cfg}/CK", f"{qs}/D")]
    intent = (f"- The configuration register `{cfg}` holds quasi-static settings written once at "
              f"boot; the path `{cfg}` -> `{qs}` (the config sink) is intentionally **excluded** "
              f"from timing (it never toggles in operation).\n"
              f"- `{cfg}` **also** drives the datapath register `{dp}`; that transfer is a normal "
              f"functional path that **must meet timing**.")
    symptom = ("`report_timing` reports no setup violations. Even so the constraints are believed "
               "incorrect: confirm that every transfer the spec requires to be timed is actually "
               "being analyzed (not masked by an over-broad exception), and that the quasi-static "
               "path remains excluded.")
    return {
        "top": theme["top"], "inputs": inputs, "outputs": outputs,
        "netlist": _netlist(theme["top"], inputs, outputs, regs, chains),
        "golden_sdc": golden, "buggy_sdc": buggy, "checks": checks,
        "intent": intent, "symptom": symptom,
        "bug_type": "overbroad_false_path", "difficulty": "hard",
        "gen_meta": {"category": "A", "period_ns": period, "qs_depth": qs_depth,
                     "dp_depth": dp_depth,
                     "expected_qs_slack_if_timed": _slack(1, period, qs_depth),
                     "expected_dp_slack": _slack(1, period, dp_depth)},
    }


# --- run scripts -----------------------------------------------------------

def _run_public_tcl(top: str) -> str:
    return f"""\
# Public feedback: apply your constraints and show real PrimeTime timing.
# FEEDBACK, not a verdict — there is no answer key. A clean report is necessary
# but NOT sufficient (signoff also rejects over-constraining / over-exclusion).
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design {top}
read_sdc constraints.sdc
puts "=== SETUP VIOLATIONS (worst 10) ==="
report_timing -delay_type max -nworst 10 -slack_lesser_than 0.0
puts "=== TIMING EXCEPTIONS IN EFFECT ==="
report_exceptions
puts "PUBLIC_DONE"
exit
"""


def _run_public_sh() -> str:
    return """\
#!/bin/bash
# Public feedback runner (run me as many times as you like).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"; exit 0; fi
"$PT_CMD" -f run_public.tcl 2>&1
exit 0
"""


def _run_hidden_tcl(top: str) -> str:
    return f"""\
# Hidden launder phase — apply agent constraints, then serialize the GENUINE
# constraint state. read_sdc sandboxes Tcl proc/exit; write_sdc overwrites any file the
# agent's SDC may have written. The verdict is computed in a fresh session (run_grade.tcl)
# reading only this laundered SDC, so no agent Tcl reaches grading.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v
link_design {top}
read_sdc constraints.sdc
write_sdc -nosplit applied_hidden.sdc
exit
"""


def _run_grade_tcl(top: str, checks: list[tuple[str, str, str]]) -> str:
    """Grade phase: read ONLY the laundered SDC, evaluate typed holdout checks.
      meet    : path must be ANALYZED (sizeof>0) AND slack >= 0
      exclude : path must stay EXCLUDED (sizeof == 0)
    EXC_SCORE = passed / total."""
    pairs = " ".join("{%s %s %s}" % (t, f, to) for (t, f, to) in checks)
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


def _run_hidden_sh() -> str:
    return """\
#!/bin/bash
# Hidden grader (two-session, forge-resistant). Emits EXC_EXEC_OK / EXC_SCORE.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
APPLIED="applied_hidden.sdc"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"; exit 0; fi

rm -f "$APPLIED"
# Phase 1: launder. Prefix output so an injected "EXC_SCORE:" cannot match ^EXC_SCORE:.
APPLY_OUT="$("$PT_CMD" -f run_hidden.tcl 2>&1)"
echo "$APPLY_OUT" | sed 's/^/[apply] /'
if [ ! -s "$APPLIED" ]; then
    echo "EXC_EXEC_FAIL: no_applied_sdc"
    echo "EXC_SCORE: 0.000"
    exit 0
fi
echo "EXC_EXEC_OK"
# Phase 2: grade in a fresh session from the laundered (trusted) SDC.
GRADE_OUT="$("$PT_CMD" -f run_grade.tcl 2>&1)"
if echo "$GRADE_OUT" | grep -qE "^EXC_SCORE:"; then
    echo "$GRADE_OUT" | grep -E "^EXC_SCORE:|^EXC_DETAIL:"
else
    echo "EXC_SCORE: 0.000"
    echo "EXC_DETAIL: grade_session_produced_no_score"
fi
exit 0
"""


def _prompt(top: str, period: float, intent: str, port_list: str, symptom: str) -> str:
    return f"""\
# Timing Signoff Debug: `{top}`

You own static-timing signoff for the `{top}` block. The constraint file `constraints.sdc`
is failing signoff review.

## Design intent (from the micro-architecture spec)
- `{top}` runs on a single clock `clk` with period **{period} ns**.
{intent}

## Symptom
{symptom}

## Rules
- Only `constraints.sdc` is editable; all other files are read-only.
- A clean `report_timing` is **necessary but not sufficient**: signoff also rejects
  *over-constraining*. Any path required to meet timing must stay analyzed — masking, cutting,
  or relaxing a real functional path will be rejected, and so will removing an exception that is
  genuinely required.
- Run `bash run_public.sh` for live `report_timing` / `report_exceptions` feedback. There is no
  answer key; reason about correctness the way an engineer does before signoff.

## Design ports
{port_list}
"""


class P9PrimeTimeExceptionDebugGenerator(BaseGenerator):
    """Generates P9 PrimeTime Exception Debug tasks, alternating Category B (even task_index,
    missing multicycle) and Category A (odd, over-broad false_path). id_start=0 generates the
    smoke task (pt_exc_debug_0000, Category B); default 1 starts the generated set at 0001.
    """

    def __init__(self, seed: int, output_dir: Path, id_start: int = 1):
        super().__init__(seed, output_dir)
        self.id_start = id_start

    def generate_one(self, task_index: int) -> Path:
        display_index = task_index + self.id_start
        period = self.rng.choice(_PERIODS)
        if task_index % 2 == 0:
            b = _build_b(THEMES_B[(task_index // 2) % len(THEMES_B)], period, self.rng)
        else:
            b = _build_a(THEMES_A[(task_index // 2) % len(THEMES_A)], period, self.rng)

        top = b["top"]
        task_id = f"pt_exc_debug_{display_index:04d}"
        task_dir = self.output_dir / task_id
        (task_dir / "files").mkdir(parents=True, exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # files/ (visible) — netlist + library + buggy constraints + public runner
        (task_dir / "files" / "design_netlist.v").write_text(b["netlist"])
        shutil.copy2(ASSET_DIR / "tiny.lib", task_dir / "files" / "tiny.lib")
        shutil.copy2(ASSET_DIR / "tiny.db", task_dir / "files" / "tiny.db")
        (task_dir / "files" / "constraints.sdc").write_text(b["buggy_sdc"])
        (task_dir / "files" / "run_public.tcl").write_text(_run_public_tcl(top))
        (task_dir / "files" / "run_public.sh").write_text(_run_public_sh())
        (task_dir / "files" / "run_public.sh").chmod(0o755)

        # hidden/ — two-session grader
        (task_dir / "hidden" / "run_hidden.tcl").write_text(_run_hidden_tcl(top))
        (task_dir / "hidden" / "run_grade.tcl").write_text(_run_grade_tcl(top, b["checks"]))
        (task_dir / "hidden" / "run_hidden.sh").write_text(_run_hidden_sh())
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)

        # solution/ — golden constraints (the precise, spec-consistent exception)
        (task_dir / "solution" / "constraints.sdc").write_text(b["golden_sdc"])

        port_list = ", ".join(["clk"] + b["inputs"] + b["outputs"])
        (task_dir / "prompt.md").write_text(
            _prompt(top, b["gen_meta"]["period_ns"], b["intent"], port_list, b["symptom"]))

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
                "visible": ["design_netlist.v", "tiny.lib", "tiny.db", "constraints.sdc",
                            "run_public.sh", "run_public.tcl"],
                "editable": ["constraints.sdc"],
                "hidden": ["run_hidden.sh", "run_hidden.tcl", "run_grade.tcl"],
                "forbidden": ["design_netlist.v", "tiny.lib", "tiny.db",
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
            "generator": dict({"script": "p9_pt_exception_debug_gen.py", "seed": self.seed,
                               "bug_type": b["bug_type"], "theme": top, "task_index": task_index},
                              **b["gen_meta"]),
            "expected_error_category": b["bug_type"],
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
        return task_dir
