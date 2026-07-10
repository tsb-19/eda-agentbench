#!/usr/bin/env python3
"""p14 workflow / multi-stage evidence-chain handoff generator (Phase-4B, smallest contract).

Builds a mini EDA workflow-handoff task whose pass requires repairing a broken handoff AND running an
ORDERED evidence-generation workflow. Two depths:

  evidence_steps=1  -- reproduces the p13 trajectory pattern as a *generated* task (sanity baseline):
                       repair flow_config->v2 + constraints.sdc->clk_main, then run stage-1 evidence.
  evidence_steps=2  -- adds a cross-stage dependency: stage-2 summary evidence binds the FRESH stage-1
                       report digest via `upstream_evidence_digest`. Stale/missing/wrong-package stage-1
                       breaks the stage-2 binding, so the chain (and EVIDENCE_OK/STAGE_CHAIN_OK) fails.

Design: REUSE the committed, b04-validated p13 substrate for everything proven (netlists, tiny.lib/db,
the stage-1 evidence_signoff TCL + gen logic, launder/coverage/signoff phases, the SDC-laundering
forge-resistant grading). Only the p14 deltas are templated here: renamed score markers
(FINAL_STATE / STAGE_CHAIN), the stage-2 evidence layer, and a chain-aware stdlib oracle
(grade_workflow.py). The stage-1 evidence digest still binds pt_shell's ACTUAL report_timing body, so
hand-forged evidence cannot match the hidden re-run.

The generator has two entry points:
  build_task_skeleton(out_dir, task_id, seed, evidence_steps)  -- PURE (no tool); writes the whole task
      dir in the MUTANT starting state, with golden inputs + placeholder golden evidence in solution/.
      Deterministic: same (task_id, seed, evidence_steps) -> byte-identical tree.
  bake_golden(task_dir, pt_cmd)                                -- TOOL-backed; runs the evidence chain on
      the golden inputs and writes the real golden evidence into solution/. Used by validation/b04.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
P13_SRC = REPO / "tasks" / "p13_trajectory_handoff" / "traj_handoff_0001"

# Seed -> (authority clock, stale clock) label pair. Different seeds produce a genuinely different
# task (clock names differ end to end) while staying authority-unique. The default pair (index 0)
# matches the frozen netlists (clk_main / clk_old), which is required for evidence_steps=1 to reuse
# the p13 netlists verbatim; non-zero seeds are reserved for future netlist-parameterized variants.
_CLOCK_PAIRS = [("clk_main", "clk_old")]

TOP = "acc_stage"
SCENARIO = "func"
CORNER = "typ"
PERIOD = 3.0

# p14 v3 (scenario/corner cross-source conflict) authority + stale labels. Only consulted for the
# hazard_type="scenario_corner_cross_source_conflict" preset; the ordered-chain and v2 tasks keep the
# SCENARIO/CORNER module constants byte-for-byte. scenario/corner are PURE PROVENANCE metadata here (a
# single tiny.db, no set_operating_conditions), so the report BODY is corner-independent: the v3 oracle
# pins authority to the hidden re-run's ACTUAL scenario/corner (from the submitted flow_config), which a
# lying manifest cannot forge.
SC_AUTH_SCENARIO = "slow"
SC_AUTH_CORNER = "func"
SC_STALE_SCENARIO = "test"
SC_STALE_CORNER = "typ"

# p14 v6 (axis-binding / value-invention stress) typed-axis vocabulary + value-swap stale labels. The
# challenge is BINDING, not vocabulary hiding: the typed vocabularies below are PUBLISHED in the visible
# axis_schema.json, but the correct assignment is still the constraint-graph intersection
# (netlist_v2/clk_main/slow/func). The mutant ships a value-SWAP -- a CORNER value in the scenario slot and
# a SCENARIO value in the corner slot -- which is the exact DeepSeek k=3 failure mode on 0006. Because the
# report body is corner-independent on the single tiny.db, a package with the correct netlist+clock
# PrimeTime-signs-off GREEN even when scenario/corner are swapped or a PVT label is substituted, so the
# type-membership echecks (gated on axis_schema, folded into EVIDENCE_OK) are what floor a signoff-green-
# but-mis-typed package below pass.
AB_STALE_SCENARIO = "func"   # a CORNER value placed in the scenario slot (the value-swap type error)
AB_STALE_CORNER = "typ"      # a SCENARIO value placed in the corner slot (the value-swap type error)
AB_TYPED_AXES = {
    "netlist_axis": ["netlist_v1.v", "netlist_v2.v"],
    "clock_axis": ["clk_old", "clk_main"],
    "scenario_axis": ["slow", "typ", "fast"],
    "corner_axis": ["func", "test", "lowpower"],
    "pvt_label_axis": ["slow_1.0V_125C", "typ_1.0V_25C", "fast_0.8V_0C"],
}
# a PVT label is DESCRIPTIVE METADATA mapping to a (scenario, corner) pair; it is never a valid scenario
# or corner value and may occupy only a dedicated pvt_label metadata field.
AB_PVT_MAPPING = {
    "slow_1.0V_125C": ["slow", "func"],
    "typ_1.0V_25C": ["typ", "test"],
    "fast_0.8V_0C": ["fast", "lowpower"],
}

# p14 v8 (semantic-role-binding REPRODUCTION -- the 0006-mechanism controlled pair). Two VARIANTS of ONE
# hazard_type share the IDENTICAL hidden truth + the byte-identical typed-binding grader (reused verbatim
# from v6/v7); they differ ONLY in the VISIBLE clarity bundle (the experimental variable):
#   variant "ambiguous"     (workflow_handoff_0009a): reports use OVERLOADED non-canonical labels
#                           (op_point / mode) whose logical-axis role must be INFERRED, AND ship NO
#                           inference anchors (no glossary, no public_check_summary, no coverage fact, no
#                           spec binding hint). This reproduces the 0006 difficulty (no anchor + body-
#                           embedded swapped values).
#   variant "clear_control" (workflow_handoff_0009b): reports use CANONICAL labels (scenario / corner)
#                           AND ship the inference anchors (sparse glossary + public_check_summary with the
#                           coverage fact + a spec binding hint). This is the negative control (~v7, which
#                           saturated). If the mechanism hypothesis holds, 0009a reproduces the axis-binding
#                           failure family while 0009b saturates.
# The variant is derived from the task_id suffix ('a' -> ambiguous, 'b' -> clear_control) so the TASKS table
# uses a single hazard_type for both. Both share the SAME unique typed assignment (netlist_v2/clk_main/slow/
# func), the SAME 294->1 uniqueness, the SAME decoy structure, and the SAME value-swap mutant
# (scenario=func/corner=typ -- the exact DeepSeek 0006 failure mode).
SRB_HAZARD = "semantic_role_binding_reproduction"
SRB_AMBIGUOUS = "ambiguous"        # 0009a: overloaded labels + no anchors (reproduce 0006 difficulty)
SRB_CLEAR_CONTROL = "clear_control"  # 0009b: canonical labels + anchors (negative control, ~v7)
# the overloaded report labels for the ambiguous variant and the semantic-role mapping they imply
SRB_AMBIGUOUS_LABELS = {"scenario": "op_point", "corner": "mode"}  # report label -> ... see mapping below
SRB_ROLE_MAPPING = {"op_point": "scenario", "mode": "corner"}      # report label -> logical typed axis
SRB_CLEAR_LABELS = {"scenario": "scenario", "corner": "corner"}    # canonical labels = their own axis



# ---------------------------------------------------------------------------
# small deterministic helpers
# ---------------------------------------------------------------------------
def _sha_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _clock_pair(seed: int) -> tuple[str, str]:
    return _CLOCK_PAIRS[seed % len(_CLOCK_PAIRS)]


# ---------------------------------------------------------------------------
# templated p14-specific file bodies
# ---------------------------------------------------------------------------
def _flow_config(netlist: str, comment: str, scenario: str = SCENARIO, corner: str = CORNER) -> str:
    return json.dumps({
        "_comment": comment,
        "netlist": netlist,
        "top_module": TOP,
        "constraints": "constraints.sdc",
        "library": "tiny.db",
        "scenario": scenario,
        "corner": corner,
    }, indent=2) + "\n"


def _constraints(clock: str, comment: str) -> str:
    en = " en" if clock_is_v2(clock) else ""
    ports = "din en" if clock_is_v2(clock) else "din"
    return (
        f"# {comment}\n"
        f"create_clock -name {clock} -period {PERIOD} [get_ports {clock}]\n"
        f"set_clock_uncertainty 0.15 [get_clocks {clock}]\n"
        f"set_input_delay  1.4 -clock {clock} [get_ports {{{ports}}}]\n"
        f"set_output_delay 1.1 -clock {clock} [get_ports dout]\n"
    )


def clock_is_v2(clock: str) -> bool:
    # the authority clock binds the v2 (enable-qualified) netlist
    return clock == _CLOCK_PAIRS[0][0]


# stage-1 evidence generator (writes timing_report.rpt + evidence_manifest.json with stage metadata).
# This is the p13 gen_evidence.py logic with two added manifest fields: "stage" and
# "upstream_evidence_digest" (null at stage 1). Kept self-contained for the generated task.
_GEN_STAGE1 = r'''#!/usr/bin/env python3
"""Stage-1 deterministic evidence generator (p14 workflow handoff).

Identical mechanism to p13 gen_evidence.py: parse flow_config.json, sign off the consumed netlist,
capture the REAL report_timing body via redirect, canonicalize it, and write
timing_report.rpt + evidence_manifest.json. Adds manifest fields stage="stage1" and
upstream_evidence_digest=null (the chain root). No wall-clock; run_nonce is a pure function of inputs
+ tool result. Shared IDENTICALLY by the public stage-1 runner and the hidden re-run.
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess


def sha_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ""


def jget(path, key, default=""):
    try:
        t = open(path).read()
    except OSError:
        return default
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', t)
    return m.group(1) if m else default


def sdc_clock(sdc_path):
    try:
        for line in open(sdc_path):
            line = line.strip()
            if line.startswith("create_clock"):
                m = re.search(r"-name\s+(\S+)", line)
                if m:
                    return m.group(1).strip('{}"')
    except OSError:
        pass
    return ""


_VOLATILE = re.compile(
    r"(?i)\b(date|version|copyright|license|synopsys|solvnet|report_timing|"
    r"design\s*:\s|tool created|loading|information:|warning:)\b")


def canon_report(body):
    out = []
    for line in body.splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        if not s or _VOLATILE.search(s):
            continue
        out.append(s)
    return "\n".join(out) + "\n"


def main():
    pt = os.environ.get("EDA_PT_CMD", "pt_shell")
    flow = "flow_config.json"
    consumed = jget(flow, "netlist")
    top = jget(flow, "top_module", "acc_stage")
    sdc = jget(flow, "constraints", "constraints.sdc")
    scenario = jget(flow, "scenario", "func")
    corner = jget(flow, "corner", "typ")
    with open("selected.tcl", "w") as f:
        f.write('set sel "%s"\nset top "%s"\nset sdc "%s"\n' % (consumed, top, sdc))
    raw = subprocess.run([pt, "-f", "evidence_signoff.tcl"],
                         capture_output=True, text=True, timeout=600).stdout
    signoff, paths, slack = "FAIL", 0, "NONE"
    for line in raw.splitlines():
        if line.startswith("EVFACT_SIGNOFF"):
            signoff = line.split(None, 1)[1].strip()
        elif line.startswith("EVFACT_PATHS"):
            try:
                paths = int(line.split(None, 1)[1].strip())
            except (ValueError, IndexError):
                paths = 0
        elif line.startswith("EVFACT_SLACK"):
            slack = line.split(None, 1)[1].strip()
    try:
        report_body = canon_report(open("report_body.txt").read())
    except OSError:
        report_body = "\n"
    clk = sdc_clock(sdc)
    with open("timing_report.rpt", "w") as f:
        f.write("# acc_stage stage-1 evidence (generated by run_evidence_stage1.sh -- do not hand-edit)\n")
        f.write("# consumed_netlist=%s clock=%s scenario=%s corner=%s signoff=%s paths=%d slack=%s\n"
                % (consumed, clk, scenario, corner, signoff, paths, slack))
        f.write("=== REPORT_TIMING BEGIN ===\n")
        f.write(report_body)
        f.write("=== REPORT_TIMING END ===\n")
    report_digest = hashlib.sha256(report_body.encode()).hexdigest()
    ih = {
        "flow_config.json": sha_file("flow_config.json"),
        "constraints.sdc": sha_file(sdc),
        "consumed_netlist": sha_file(consumed) if consumed else "",
    }
    nonce_src = (ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
                 + clk + scenario + corner + report_digest)
    run_nonce = hashlib.sha256(nonce_src.encode()).hexdigest()[:16]
    manifest = {
        "_comment": "Generated by run_evidence_stage1.sh. Do not hand-edit; the grader re-runs the "
                    "generator and compares. run_nonce is deterministic (no wall-clock).",
        "stage": "stage1",
        "upstream_evidence_digest": None,
        "input_hashes": ih,
        "selected_netlist": consumed,
        "selected_sdc": sdc,
        "selected_clock": clk,
        "scenario": scenario,
        "corner": corner,
        "tool": "pt_shell",
        "tool_exit": 0,
        "signoff": signoff,
        "constrained_paths": paths,
        "report_digest": report_digest,
        "run_nonce": run_nonce,
    }
    with open("evidence_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# stage-2 summary generator: consumes stage-1's evidence_manifest.json (upstream_evidence_digest),
# runs a SECOND, distinct PT analysis (register-to-register path via -from cap_reg), and writes
# stage2_summary.json whose run_nonce folds in the FRESH stage-1 report_digest. If stage 1 is missing
# / signoff!=OK, it writes a FAIL summary so the chain breaks.
_GEN_STAGE2 = r'''#!/usr/bin/env python3
"""Stage-2 deterministic summary-evidence generator (p14 workflow handoff, evidence_steps=2).

Depends on stage 1: reads evidence_manifest.json (the stage-1 product) and binds its report_digest as
upstream_evidence_digest. Runs a SECOND PrimeTime analysis (the cap_reg->acc_reg register path) via
evidence_signoff_stage2.tcl, captures the real report body, canonicalizes it (same rule as stage 1),
and writes stage2_summary.json. run_nonce_stage2 folds in BOTH the stage-2 report digest AND the
stage-1 upstream digest, so a stale/missing/wrong-package stage 1 changes the stage-2 nonce -> the
hidden re-run rejects it. No wall-clock.
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess


def sha_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ""


def jget(path, key, default=""):
    try:
        t = open(path).read()
    except OSError:
        return default
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', t)
    return m.group(1) if m else default


def jload(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return {}


_VOLATILE = re.compile(
    r"(?i)\b(date|version|copyright|license|synopsys|solvnet|report_timing|"
    r"design\s*:\s|tool created|loading|information:|warning:)\b")


def canon_report(body):
    out = []
    for line in body.splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        if not s or _VOLATILE.search(s):
            continue
        out.append(s)
    return "\n".join(out) + "\n"


def main():
    pt = os.environ.get("EDA_PT_CMD", "pt_shell")
    flow = "flow_config.json"
    consumed = jget(flow, "netlist")
    top = jget(flow, "top_module", "acc_stage")
    sdc = jget(flow, "constraints", "constraints.sdc")
    scenario = jget(flow, "scenario", "func")
    corner = jget(flow, "corner", "typ")
    stage1 = jload("evidence_manifest.json")
    upstream = stage1.get("report_digest") if stage1 else None
    stage1_ok = bool(stage1) and stage1.get("signoff") == "OK" and bool(upstream)

    with open("selected.tcl", "w") as f:
        f.write('set sel "%s"\nset top "%s"\nset sdc "%s"\n' % (consumed, top, sdc))
    raw = subprocess.run([pt, "-f", "evidence_signoff_stage2.tcl"],
                         capture_output=True, text=True, timeout=600).stdout
    s2_signoff, s2_paths, s2_slack = "FAIL", 0, "NONE"
    for line in raw.splitlines():
        if line.startswith("EVFACT2_SIGNOFF"):
            s2_signoff = line.split(None, 1)[1].strip()
        elif line.startswith("EVFACT2_PATHS"):
            try:
                s2_paths = int(line.split(None, 1)[1].strip())
            except (ValueError, IndexError):
                s2_paths = 0
        elif line.startswith("EVFACT2_SLACK"):
            s2_slack = line.split(None, 1)[1].strip()
    try:
        s2_body = canon_report(open("report_body2.txt").read())
    except OSError:
        s2_body = "\n"
    stage2_report_digest = hashlib.sha256(s2_body.encode()).hexdigest()

    ih = {
        "flow_config.json": sha_file("flow_config.json"),
        "constraints.sdc": sha_file(sdc),
        "consumed_netlist": sha_file(consumed) if consumed else "",
    }
    clk = stage1.get("selected_clock", "") if stage1 else ""
    nonce_src = (ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
                 + clk + scenario + corner + stage2_report_digest + (upstream or ""))
    run_nonce2 = hashlib.sha256(nonce_src.encode()).hexdigest()[:16]
    summary = {
        "_comment": "Generated by run_evidence_stage2.sh from the stage-1 evidence. Do not hand-edit. "
                    "upstream_evidence_digest binds the FRESH stage-1 report; run_nonce is deterministic.",
        "stage": "stage2",
        "upstream_evidence_digest": upstream,
        "upstream_stage_ok": stage1_ok,
        "input_hashes": ih,
        "selected_netlist": consumed,
        "selected_clock": clk,
        "scenario": scenario,
        "corner": corner,
        "tool": "pt_shell",
        "tool_exit": 0,
        "signoff": s2_signoff,
        "stage2_constrained_paths": s2_paths,
        "stage2_slack": s2_slack,
        "stage2_report_digest": stage2_report_digest,
        "run_nonce": run_nonce2,
    }
    with open("stage2_summary.json", "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# stage-2 sign-off TCL: reports the cap_reg->acc_reg register path (a DISTINCT analysis from stage 1's
# din->cap_reg worst path). Uses -from on the cap_reg launch to select the reg2reg arc; falls back to
# the global worst path if the constrained query returns nothing (robust across PT versions).
_SIGNOFF_STAGE2_TCL = r'''# Stage-2 evidence sign-off (p14). Reports the cap_reg->acc_reg register path (distinct from stage 1's
# din->cap_reg worst path) and writes the real report body to report_body2.txt via redirect, so the
# stage-2 digest binds pt_shell's actual path table. EVFACT2_* facts on ^-anchored stdout lines.
if {[file exists selected.tcl]} { source selected.tcl } else {
    set sel ""; set top "acc_stage"; set sdc "constraints.sdc"
}
set bfh [open report_body2.txt w]; close $bfh
if {![info exists sel] || $sel eq "" || ![file exists $sel]} {
    puts "EVFACT2_SIGNOFF FAIL"; puts "EVFACT2_PATHS 0"; puts "EVFACT2_SLACK NONE"; exit
}
if {[catch {
    read_db tiny.db
    set link_path "* tiny.db"
    read_verilog $sel
    link_design $top
    read_sdc $sdc
    update_timing
} emsg]} {
    puts "EVFACT2_SIGNOFF FAIL"; puts "EVFACT2_PATHS 0"; puts "EVFACT2_SLACK NONE"; exit
}
# the register-to-register arc launched by cap_reg (reliable -from on the reg cell)
set wp [get_timing_paths -delay_type max -nworst 1 -from cap_reg]
if {[sizeof_collection $wp] == 0} {
    set wp [get_timing_paths -delay_type max -nworst 1]
}
set np [sizeof_collection $wp]
if {$np == 0} {
    puts "EVFACT2_SIGNOFF FAIL"; puts "EVFACT2_PATHS 0"; puts "EVFACT2_SLACK NONE"; exit
}
redirect report_body2.txt { report_timing -delay_type max -nworst 1 -from cap_reg }
set s [get_attribute [index_collection $wp 0] slack]
puts "EVFACT2_PATHS 1"
puts "EVFACT2_SLACK $s"
if {$s >= -0.001} { puts "EVFACT2_SIGNOFF OK" } else { puts "EVFACT2_SIGNOFF FAIL" }
exit
'''


def _run_evidence_stage1_sh() -> str:
    return (
        "#!/bin/bash\n"
        "# Public stage-1 evidence generator (p14). Reruns sign-off on the CURRENT flow_config.json +\n"
        "# constraints.sdc and (re)writes fresh timing_report.rpt + evidence_manifest.json. Read-only\n"
        "# (you run it; you do not edit it).\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"\n'
        'PT_CMD="${EDA_PT_CMD:-pt_shell}"\n'
        'PY_CMD="${EDA_PY_CMD:-python3}"\n'
        'if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found"; exit 0; fi\n'
        'EDA_PT_CMD="$PT_CMD" "$PY_CMD" gen_evidence_stage1.py\n'
        'echo "EVIDENCE_STAGE1_GENERATED timing_report.rpt evidence_manifest.json"\n'
        "exit 0\n"
    )


def _run_evidence_stage2_sh() -> str:
    return (
        "#!/bin/bash\n"
        "# Public stage-2 summary-evidence generator (p14, evidence_steps=2). Consumes the stage-1\n"
        "# evidence_manifest.json and writes stage2_summary.json binding the fresh stage-1 digest. Run\n"
        "# AFTER stage 1. Read-only.\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"\n'
        'PT_CMD="${EDA_PT_CMD:-pt_shell}"\n'
        'PY_CMD="${EDA_PY_CMD:-python3}"\n'
        'if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found"; exit 0; fi\n'
        'EDA_PT_CMD="$PT_CMD" "$PY_CMD" gen_evidence_stage2.py\n'
        'echo "EVIDENCE_STAGE2_GENERATED stage2_summary.json"\n'
        "exit 0\n"
    )


# ---------------------------------------------------------------------------
# public runner (verdict-first, no leak). TCL mirrors p13 run_public.tcl and adds a stage-2 freshness
# line when evidence_steps==2. Emits no expected hashes/nonces/digests.
# ---------------------------------------------------------------------------
def _run_public_tcl(evidence_steps: int) -> str:
    s2 = ""
    if evidence_steps == 2:
        s2 = r'''
# stage-2 freshness: present and bound to the CURRENT stage-1 digest?
set s2_state "MISSING"
if {[file exists stage2_summary.json] && [file exists evidence_manifest.json]} {
    set fh [open stage2_summary.json r]; set s2t [read $fh]; close $fh
    set fh [open evidence_manifest.json r]; set s1t [read $fh]; close $fh
    set up ""; set s1dig ""
    regexp {"upstream_evidence_digest"\s*:\s*"([^"]*)"} $s2t -> up
    regexp {"report_digest"\s*:\s*"([^"]*)"} $s1t -> s1dig
    if {$up ne "" && $up eq $s1dig} { set s2_state "FRESH" } else { set s2_state "STALE" }
}'''
    s2_verdict = ' stage2=$s2_state' if evidence_steps == 2 else ''
    s2_hint = ''
    if evidence_steps == 2:
        s2_hint = r'''
    if {$s2_state ne "FRESH"} {
        puts "PUBLIC_HINT: stage-2 summary is $s2_state -- after stage 1 is FRESH, run 'bash run_evidence_stage2.sh' so stage2_summary.json binds the current stage-1 digest"
    }'''
    s2_init = '\nset s2_state "NA"' if evidence_steps == 2 else ''
    pass_cond = '$ev_state eq "FRESH"'
    if evidence_steps == 2:
        pass_cond = '$ev_state eq "FRESH" && $s2_state eq "FRESH"'
    return f'''# Public feedback (p14 workflow handoff). Verdict-first; FEEDBACK not the grade. Reports whether
# flow_config consumes the authority netlist + the SDC constrains the design, stage-1 evidence
# FRESH/STALE/MISSING, and (steps=2) stage-2 summary freshness. Never reveals expected hashes/nonce/
# digest. Reads only agent-visible files.

proc jstr {{text key}} {{
    if {{[regexp "\\"$key\\"\\s*:\\s*\\"(\\[^\\"\\]*)\\"" $text -> v]}} {{ return $v }}
    return ""
}}
proc sha256_file {{path}} {{
    if {{![file exists $path]}} {{ return "" }}
    if {{[catch {{exec sha256sum $path}} out]}} {{ return "" }}
    return [lindex [split $out] 0]
}}

set consumed ""; set top "acc_stage"; set sdc "constraints.sdc"
if {{[file exists flow_config.json]}} {{
    set fh [open flow_config.json r]; set ft [read $fh]; close $fh
    set consumed [jstr $ft netlist]
    set t [jstr $ft top_module]; if {{$t ne ""}} {{ set top $t }}
    set s [jstr $ft constraints]; if {{$s ne ""}} {{ set sdc $s }}
}}
set want_net ""; set want_clk ""
if {{[file exists handoff_manifest.json]}} {{
    set fh [open handoff_manifest.json r]; set mt [read $fh]; close $fh
    set want_net [jstr $mt netlist]; set want_clk [jstr $mt clock]
}}

set ev_state "MISSING"
if {{[file exists evidence_manifest.json] && [file exists timing_report.rpt]}} {{
    set fh [open evidence_manifest.json r]; set et [read $fh]; close $fh
    set rec_fc ""; set rec_sdc ""; set rec_net ""
    regexp {{"flow_config.json"\\s*:\\s*"([^"]*)"}} $et -> rec_fc
    regexp {{"constraints.sdc"\\s*:\\s*"([^"]*)"}} $et -> rec_sdc
    regexp {{"consumed_netlist"\\s*:\\s*"([^"]*)"}} $et -> rec_net
    set cur_fc [sha256_file flow_config.json]
    set cur_sdc [sha256_file $sdc]
    set cur_net [sha256_file $consumed]
    if {{$rec_fc eq $cur_fc && $rec_sdc eq $cur_sdc && $rec_net eq $cur_net && $cur_fc ne ""}} {{
        set ev_state "FRESH"
    }} else {{ set ev_state "STALE" }}
}}{s2_init}{s2}

set net_match [expr {{$consumed ne "" && $consumed eq $want_net}}]
set npaths 0; set pt_status "NO_RUN"; set consumed_clk ""
if {{$consumed ne "" && [file exists $consumed]}} {{
    if {{[catch {{
        read_db tiny.db; set link_path "* tiny.db"
        read_verilog $consumed; link_design $top; read_sdc $sdc; update_timing
    }} emsg]}} {{
        set pt_status "LINK_OR_SDC_ERROR"
    }} else {{
        set clks [get_clocks -quiet *]
        if {{[sizeof_collection $clks] > 0}} {{ set consumed_clk [get_attribute [index_collection $clks 0] full_name] }}
        set npaths [sizeof_collection [get_timing_paths -delay_type max -nworst 1]]
        if {{$npaths == 0}} {{ set pt_status "NO_PATHS" }} else {{
            set ws [get_attribute [index_collection [get_timing_paths -delay_type max -nworst 1] 0] slack]
            if {{$ws >= -0.001}} {{ set pt_status "OK" }} else {{ set pt_status "VIOLATION" }}
        }}
    }}
}} else {{ set pt_status "NO_NETLIST" }}

if {{$net_match && $npaths > 0 && $pt_status eq "OK" && {pass_cond}}} {{
    puts "WORKFLOW_PUBLIC: OK consumed=$consumed/$consumed_clk manifest=$want_net/$want_clk constrained_paths=$npaths signoff=$pt_status evidence=$ev_state{s2_verdict}"
}} else {{
    puts "WORKFLOW_PUBLIC: MISMATCH consumed=$consumed/$consumed_clk manifest=$want_net/$want_clk constrained_paths=$npaths signoff=$pt_status evidence=$ev_state{s2_verdict}"
    if {{!$net_match}} {{
        puts "PUBLIC_HINT: flow_config.json consumes a netlist the authority does not name (consumed=$consumed vs manifest=$want_net) -- check handoff_manifest.json / spec.md"
    }}
    if {{$npaths == 0}} {{
        puts "PUBLIC_HINT: zero constrained paths -- check constraints.sdc binds the consumed netlist's real clock PORT (authority clock=$want_clk)"
    }}
    if {{$ev_state ne "FRESH"}} {{
        puts "PUBLIC_HINT: stage-1 evidence is $ev_state -- after repairing inputs run 'bash run_evidence_stage1.sh' to regenerate timing_report.rpt + evidence_manifest.json"
    }}{s2_hint}
}}
puts "=== CONSUMED FLOW ==="
puts "consumed=$consumed consumed_clock=$consumed_clk manifest=$want_net/$want_clk evidence=$ev_state"
if {{$npaths > 0}} {{ report_timing -delay_type max -nworst 1 }}
puts "PUBLIC_DONE"
exit
'''


def _run_public_sh() -> str:
    return (
        "#!/bin/bash\n"
        "# Public feedback runner (p14 workflow handoff). Verdict hoisted to the TOP of stdout.\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"\n'
        'PT_CMD="${EDA_PT_CMD:-pt_shell}"\n'
        'if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found"; exit 0; fi\n'
        'RAW="$("$PT_CMD" -f run_public.tcl 2>&1)"\n'
        "echo \"$RAW\" | grep -E '^WORKFLOW_PUBLIC:' || echo \"WORKFLOW_PUBLIC: UNKNOWN no_verdict\"\n"
        "echo \"$RAW\" | grep -E '^PUBLIC_HINT:' || true\n"
        'echo "----- full PrimeTime log -----"\n'
        "printf '%s\\n' \"$RAW\"\n"
        "exit 0\n"
    )


# ---------------------------------------------------------------------------
# hidden chain-aware oracle (stdlib; reads everything as data). Emits the markers
# WorkflowHandoffEvaluator consumes. Reuses p13's report-digest canonicalization + authority clauses,
# and adds the STAGE_CHAIN axis (steps>=2): stage-2 present & fresh & upstream_evidence_digest == fresh
# stage-1 digest. For steps==1, STAGE_CHAIN is trivially OK.
# ---------------------------------------------------------------------------
_GRADE_WORKFLOW = r'''#!/usr/bin/env python3
"""Hidden chain-aware grader for p14 workflow handoff. Reads ALL inputs as data (no Tcl evaluated).

Compares the submitted evidence chain against the hidden re-run's reference:
  - stage1: submitted timing_report.rpt + evidence_manifest.json vs ref_evidence_manifest.json /
            ref_timing_report.rpt (report_digest, input_hashes, run_nonce, signoff, paths, authority pkg)
  - stage2 (evidence_steps>=2): submitted stage2_summary.json vs ref_stage2_summary.json
            (stage2_report_digest, run_nonce, AND upstream_evidence_digest == the FRESH stage-1 digest)

EVIDENCE_OK is the master gate: it requires every REQUIRED stage to match the hidden re-run AND
describe the authority-correct package. STAGE_CHAIN_OK additionally requires the ordered binding
(stage2.upstream == fresh stage1.report_digest). Emitted markers (line start):
    EVIDENCE_OK / _SCORE / _DETAIL
    FINAL_STATE_OK / _SCORE / _DETAIL
    STAGE_CHAIN_OK / _SCORE / _DETAIL
    PROVENANCE_OK / _SCORE / _DETAIL
    HANDOFF_MASKING_DETECTED: <what>
Pure stdlib.
"""
from __future__ import annotations
import hashlib, json, re, sys


def _jstr(text, key):
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', text)
    return m.group(1) if m else ""


def _sha_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ""


def _read(path):
    try:
        return open(path).read()
    except OSError:
        return ""


def _load(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return {}


def _report_digest(path, begin="=== REPORT_TIMING BEGIN ===", end="=== REPORT_TIMING END ==="):
    raw = _read(path)
    m = re.search(re.escape(begin) + r"\n(.*?)\n" + re.escape(end), raw, re.DOTALL)
    body = m.group(1) if m else ""
    volatile = re.compile(
        r"(?i)\b(date|version|copyright|license|synopsys|solvnet|report_timing|"
        r"design\s*:\s|tool created|loading|information:|warning:)\b")
    out = []
    for line in body.splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        if not s or volatile.search(s):
            continue
        out.append(s)
    return hashlib.sha256(("\n".join(out) + "\n").encode()).hexdigest()


def _read_coverage(path):
    out = {"intended_clock_present": 0, "constrained_paths": 0}
    for line in _read(path).splitlines():
        p = line.split()
        if len(p) == 2 and p[0] in out:
            try:
                out[p[0]] = int(p[1])
            except ValueError:
                pass
    return out


def _sdc_clocks(sdc_text):
    names = []
    for raw in sdc_text.splitlines():
        line = raw.strip()
        if line.startswith("create_clock"):
            m = re.search(r"-name\s+(\S+)", line)
            if m:
                names.append(m.group(1).strip('{}"'))
    return names


def _masking(sdc_text, truth):
    exc = ("set_false_path", "set_multicycle_path", "set_clock_groups", "set_disable_timing")
    for raw in sdc_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for c in exc:
            if line.startswith(c):
                return "sdc_exception:" + c
        if line.startswith("create_clock"):
            mm = re.search(r"-period\s+([0-9.]+)", line)
            if mm and float(mm.group(1)) > truth["clock_period_ns"] + 1e-6:
                return "period_loosened:" + mm.group(1)
    return None


def grade(truth):
    steps = int(truth.get("evidence_steps", 1))
    flow_text = _read("flow_config.json")
    consumed = _jstr(flow_text, "netlist")
    consumed_corner = _jstr(flow_text, "corner")
    man_text = _read("handoff_manifest.json")
    man_net = _jstr(man_text, "netlist") or truth["manifest_netlist"]
    man_corner = _jstr(man_text, "corner") or truth["corner"]
    applied = _read("applied_hidden.sdc")
    coverage = _read_coverage("coverage.txt")

    sub = _load("evidence_manifest.json")
    ref = _load("ref_evidence_manifest.json")
    sub_present = bool(sub) and bool(_read("timing_report.rpt"))
    ref_present = bool(ref) and bool(_read("ref_timing_report.rpt"))
    sub_report_digest = _report_digest("timing_report.rpt")

    # stage-1 evidence checks (identical spirit to p13)
    echecks = []
    if not ref_present:
        echecks.append(("reference_rerun", False, "hidden re-run produced no stage1 reference"))
    echecks += [
        ("evidence_present", sub_present, "manifest=%s report=%s" % (bool(sub), bool(_read("timing_report.rpt")))),
        ("manifest_digest_matches_ref", bool(sub) and bool(ref)
         and sub.get("report_digest") == ref.get("report_digest"),
         "sub=%s ref=%s" % (str(sub.get("report_digest"))[:12], str(ref.get("report_digest"))[:12])),
        ("submitted_report_matches_its_manifest",
         bool(sub) and sub.get("report_digest") == sub_report_digest,
         "manifest=%s body=%s" % (str(sub.get("report_digest"))[:12], sub_report_digest[:12])),
        ("input_hashes_match_ref", bool(sub) and bool(ref)
         and sub.get("input_hashes") == ref.get("input_hashes"), "input_hashes vs ref"),
        ("run_nonce_matches_ref", bool(sub) and bool(ref)
         and sub.get("run_nonce") == ref.get("run_nonce"),
         "sub=%s ref=%s" % (sub.get("run_nonce"), ref.get("run_nonce"))),
        ("signoff_ok", bool(sub) and sub.get("signoff") == "OK", "signoff=%s" % sub.get("signoff")),
        ("paths_min", bool(sub) and int(sub.get("constrained_paths", 0)) >= truth["min_constrained_paths"],
         "paths=%s" % sub.get("constrained_paths")),
        ("evidence_is_authority_pkg", bool(sub)
         and sub.get("selected_netlist") == truth["expected_netlist"]
         and sub.get("selected_clock") == truth["expected_clock"]
         and sub.get("scenario") == truth["scenario"]
         and sub.get("corner") == truth["corner"],
         "net=%s clk=%s" % (sub.get("selected_netlist"), sub.get("selected_clock"))),
    ]

    # scenario/corner provenance authority (v3 hazard only). PINNED to the hidden re-run: ref.scenario/
    # ref.corner are the ACTUAL scenario/corner of the re-run on the SUBMITTED flow_config, so a
    # hand-edited manifest claim cannot satisfy these. Folded into EVIDENCE (master gate) so a
    # wrong-scenario/corner package stays far below pass. Gated on expected_scenario/corner being present
    # in truth (only set for the scenario_corner hazard), so 0001/0002/0003 output is byte-identical.
    if truth.get("expected_scenario") is not None:
        exp_sc = truth.get("expected_scenario")
        exp_co = truth.get("expected_corner")
        ref_sc = ref.get("scenario") if ref else None
        ref_co = ref.get("corner") if ref else None
        echecks += [
            ("evidence_scenario_is_authority",
             bool(sub) and bool(ref) and ref_sc == exp_sc and sub.get("scenario") == ref_sc,
             "sub=%s ref=%s want=%s" % (sub.get("scenario"), ref_sc, exp_sc)),
            ("evidence_corner_is_authority",
             bool(sub) and bool(ref) and ref_co == exp_co and sub.get("corner") == ref_co,
             "sub=%s ref=%s want=%s" % (sub.get("corner"), ref_co, exp_co)),
        ]

    # multi-conflict global-authority echecks (v4 hazard only). FORGERY-RESISTANT: pinned to the
    # consumed netlist (flow_config.json) and the consumed clock (the trusted-laundered applied_hidden.sdc),
    # NOT to the agent-authored evidence_manifest -- so an agent that runs the chain on the stale netlist
    # and then hand-edits the manifest to CLAIM netlist_v2 cannot satisfy these. Folded into EVIDENCE_OK
    # (master gate) so any partially-truthful decoy recovery (Report-A right-netlist/wrong-corner,
    # Report-B right-corner/stale-netlist, Evidence-C fresh-but-wrong-package) stays far below pass.
    # Gated on global_authority_tuple being present (only set for the multi_conflict hazard), so
    # 0001/0002/0003/0004 grader output is byte-identical.
    if truth.get("global_authority_tuple") is not None:
        consumed_clocks = _sdc_clocks(applied)
        consumed_clk = consumed_clocks[0] if consumed_clocks else None
        echecks += [
            ("evidence_consumed_netlist_is_authority",
             consumed == truth["expected_netlist"],
             "flow_config.netlist=%s want=%s" % (consumed, truth["expected_netlist"])),
            ("evidence_consumed_clock_is_authority",
             consumed_clk == truth["expected_clock"],
             "applied.clock=%s want=%s" % (consumed_clk, truth["expected_clock"])),
        ]

    # axis-binding typed-membership echecks (v6 hazard only). The report body is corner-independent on the
    # single tiny.db, so a package with the CORRECT netlist+clock still PrimeTime-signs-off GREEN even when
    # scenario/corner are SWAPPED or a PVT label is substituted for a corner. These echecks reject exactly
    # that: every consumed axis value must be an in-domain member of its OWN typed axis (a scenario value
    # cannot occupy the corner slot and vice versa; a PVT label is never an axis value; the clock must be
    # the exact identity, not a generic alias). FORGERY-RESISTANT: pinned to the consumed flow_config
    # (scenario/corner) and the trusted laundered applied_hidden.sdc (clock), not to agent-authored
    # evidence. Folded into EVIDENCE_OK (master gate) so a signoff-green-but-mis-typed package stays far
    # below pass. Gated on axis_schema (only the v6 hazard sets it) -> 0001-0005 grader output byte-identical.
    if truth.get("axis_schema") is not None:
        _schema = truth["axis_schema"]
        _scen_dom = set(_schema["typed_axes"]["scenario_axis"])
        _corn_dom = set(_schema["typed_axes"]["corner_axis"])
        _clk_dom = set(_schema["typed_axes"]["clock_axis"])
        _pvt_dom = set(_schema["typed_axes"].get("pvt_label_axis", []))
        _cc = _sdc_clocks(applied)
        _fc_clk = _cc[0] if _cc else None
        _fc_scen = _jstr(flow_text, "scenario")
        echecks += [
            ("typed_scenario_in_scenario_axis", _fc_scen in _scen_dom,
             "scenario=%s in %s" % (_fc_scen, sorted(_scen_dom))),
            ("typed_corner_in_corner_axis", consumed_corner in _corn_dom,
             "corner=%s in %s" % (consumed_corner, sorted(_corn_dom))),
            ("typed_scenario_not_pvt_label", _fc_scen not in _pvt_dom,
             "scenario=%s not a pvt label" % _fc_scen),
            ("typed_corner_not_pvt_label", consumed_corner not in _pvt_dom,
             "corner=%s not a pvt label" % consumed_corner),
            ("typed_clock_identity_in_clock_axis", _fc_clk in _clk_dom,
             "clock=%s in %s" % (_fc_clk, sorted(_clk_dom))),
        ]

    # stage-2 chain checks (only when required). These also feed EVIDENCE_OK (master gate) so a
    # missing/stale stage-2 cannot pass on stage-1 alone.
    s2sub = _load("stage2_summary.json") if steps >= 2 else {}
    s2ref = _load("ref_stage2_summary.json") if steps >= 2 else {}
    cchecks = []
    if steps >= 2:
        fresh_up = ref.get("report_digest") if ref else None
        cchecks += [
            ("stage2_present", bool(s2sub), "present=%s" % bool(s2sub)),
            ("stage2_reference_rerun", bool(s2ref), "ref=%s" % bool(s2ref)),
            ("stage2_digest_matches_ref", bool(s2sub) and bool(s2ref)
             and s2sub.get("stage2_report_digest") == s2ref.get("stage2_report_digest"),
             "sub=%s ref=%s" % (str(s2sub.get("stage2_report_digest"))[:12], str(s2ref.get("stage2_report_digest"))[:12])),
            ("stage2_run_nonce_matches_ref", bool(s2sub) and bool(s2ref)
             and s2sub.get("run_nonce") == s2ref.get("run_nonce"),
             "sub=%s ref=%s" % (s2sub.get("run_nonce"), s2ref.get("run_nonce"))),
            # the ORDERED binding: stage2 must reference the FRESH stage-1 digest (from the hidden re-run)
            ("stage2_binds_fresh_stage1", bool(s2sub) and fresh_up is not None
             and s2sub.get("upstream_evidence_digest") == fresh_up,
             "up=%s fresh=%s" % (str(s2sub.get("upstream_evidence_digest"))[:12], str(fresh_up)[:12])),
            ("stage2_signoff_ok", bool(s2sub) and s2sub.get("signoff") == "OK",
             "s2_signoff=%s" % s2sub.get("signoff")),
        ]

    e_checks_all = echecks + cchecks   # master gate folds in the chain
    e_ok = sum(1 for _, ok, _ in e_checks_all if ok)
    e_full = e_ok == len(e_checks_all)
    e_detail = " ".join("%s=%s" % (n, "ok" if ok else "WRONG(" + i + ")") for n, ok, i in e_checks_all)

    # STAGE_CHAIN axis: the ordered-chain subset (steps>=2); trivially full when steps==1
    if steps >= 2:
        sc_ok = sum(1 for _, ok, _ in cchecks if ok)
        sc_full = sc_ok == len(cchecks)
        sc_frac = sc_ok / len(cchecks)
        sc_detail = " ".join("%s=%s" % (n, "ok" if ok else "WRONG(" + i + ")") for n, ok, i in cchecks)
    else:
        sc_full, sc_frac, sc_detail = True, 1.0, "single_stage_no_chain"

    # FINAL state consistency
    consumed_disk = _sha_file(consumed) if consumed else ""
    consumed_scenario = _jstr(flow_text, "scenario")
    fchecks = [
        ("consumed_is_authority", consumed == man_net, "%s vs %s" % (consumed, man_net)),
        ("consumed_is_expected", consumed == truth["expected_netlist"],
         "%s vs %s" % (consumed, truth["expected_netlist"])),
        ("provenance_integrity", consumed_disk == truth["expected_netlist_sha256"],
         "disk=%s" % consumed_disk[:12]),
        ("corner_matches", consumed_corner == man_corner, "%s vs %s" % (consumed_corner, man_corner)),
    ]
    # v3 hazard: bind the consumed scenario/corner to the truth authority too (defense in depth, so the
    # final-state axis also rejects wrong-corner flow_config). Gated on expected_scenario presence.
    if truth.get("expected_scenario") is not None:
        fchecks += [
            ("consumed_scenario_is_authority", consumed_scenario == truth.get("expected_scenario"),
             "%s vs %s" % (consumed_scenario, truth.get("expected_scenario"))),
            ("consumed_corner_is_authority", consumed_corner == truth.get("expected_corner"),
             "%s vs %s" % (consumed_corner, truth.get("expected_corner"))),
        ]
    f_ok = sum(1 for _, ok, _ in fchecks if ok)
    f_full = f_ok == len(fchecks)
    f_detail = " ".join("%s=%s" % (n, "ok" if ok else "WRONG(" + i + ")") for n, ok, i in fchecks)

    # PROVENANCE: evidence selected_* match authority
    pchecks = [
        ("sel_netlist", bool(sub) and sub.get("selected_netlist") == truth["expected_netlist"],
         "%s" % sub.get("selected_netlist")),
        ("sel_clock", bool(sub) and sub.get("selected_clock") == truth["expected_clock"],
         "%s" % sub.get("selected_clock")),
        ("sel_scenario", bool(sub) and sub.get("scenario") == truth["scenario"], "%s" % sub.get("scenario")),
        ("sel_corner", bool(sub) and sub.get("corner") == truth["corner"], "%s" % sub.get("corner")),
    ]
    p_ok = sum(1 for _, ok, _ in pchecks if ok)
    p_full = p_ok == len(pchecks)
    p_detail = " ".join("%s=%s" % (n, "ok" if ok else "WRONG(" + i + ")") for n, ok, i in pchecks)

    masking = _masking(applied, truth) if truth.get("forbid_weakening") else None
    return (e_full, e_ok / len(e_checks_all), e_detail,
            f_full, f_ok / len(fchecks), f_detail,
            sc_full, sc_frac, sc_detail,
            p_full, p_ok / len(pchecks), p_detail, masking)


def main():
    truth = _load(sys.argv[1] if len(sys.argv) > 1 else "handoff_truth.json")
    (e_full, e_frac, e_detail, f_full, f_frac, f_detail,
     sc_full, sc_frac, sc_detail, p_full, p_frac, p_detail, masking) = grade(truth)
    # re-load the data the diagnostic markers below read (grade() keeps these local; load fresh here so
    # the reported diagnostics reflect the on-disk submission, independent of grade()'s locals).
    sub = _load("evidence_manifest.json")
    ref = _load("ref_evidence_manifest.json")
    applied = _read("applied_hidden.sdc")
    if masking:
        print("HANDOFF_MASKING_DETECTED: " + masking)
    if e_full and not masking:
        print("EVIDENCE_OK")
    print("EVIDENCE_SCORE: %.3f" % e_frac)
    print("EVIDENCE_DETAIL: " + e_detail)
    if f_full and not masking:
        print("FINAL_STATE_OK")
    print("FINAL_STATE_SCORE: %.3f" % f_frac)
    print("FINAL_STATE_DETAIL: " + f_detail)
    if sc_full and not masking:
        print("STAGE_CHAIN_OK")
    print("STAGE_CHAIN_SCORE: %.3f" % sc_frac)
    print("STAGE_CHAIN_DETAIL: " + sc_detail)
    if p_full and not masking:
        print("PROVENANCE_OK")
    print("PROVENANCE_SCORE: %.3f" % p_frac)
    print("PROVENANCE_DETAIL: " + p_detail)
    # Hazard-recovery markers (emitted only for hazard presets so the ordered-chain tasks'
    # output is byte-identical). Both fold into the EVIDENCE master gate: AUTHORITY_CONSISTENCY_OK
    # requires the final consumed package to equal the manifest authority AND the fresh evidence to
    # describe it (so editing the manifest down, or trusting the v1 decoy, cannot satisfy it);
    # HAZARD_RECOVERY_OK requires the full fresh ordered chain (so stale/partial/wrong-order fail).
    if truth.get("hazard_type", "none") != "none":
        authority_consistent = bool(e_full and f_full) and not masking
        hazard_recovered = bool(e_full and f_full and sc_full) and not masking
        if authority_consistent:
            print("AUTHORITY_CONSISTENCY_OK")
        print("AUTHORITY_CONSISTENCY_SCORE: %.3f" % (1.0 if authority_consistent else 0.0))
        if hazard_recovered:
            print("HAZARD_RECOVERY_OK")
        print("HAZARD_RECOVERY_SCORE: %.3f" % (1.0 if hazard_recovered else 0.0))
        # scenario/corner authority diagnostics (v3 hazard). These fold into EVIDENCE (master gate) via
        # the evidence_scenario_is_authority / evidence_corner_is_authority echecks, so the markers are
        # reported (not separately scored) -- a wrong scenario/corner already collapses EVIDENCE_OK.
        if truth.get("expected_scenario") is not None:
            ref_sc = ref.get("scenario") if ref else None
            ref_co = ref.get("corner") if ref else None
            scen_ok = bool(sub) and bool(ref) and ref_sc == truth.get("expected_scenario") \
                and sub.get("scenario") == ref_sc and not masking
            corn_ok = bool(sub) and bool(ref) and ref_co == truth.get("expected_corner") \
                and sub.get("corner") == ref_co and not masking
            if scen_ok:
                print("SCENARIO_AUTHORITY_OK")
            print("SCENARIO_AUTHORITY_SCORE: %.3f" % (1.0 if scen_ok else 0.0))
            if corn_ok:
                print("CORNER_AUTHORITY_OK")
            print("CORNER_AUTHORITY_SCORE: %.3f" % (1.0 if corn_ok else 0.0))
            if scen_ok and corn_ok:
                print("SCENARIO_CORNER_AUTHORITY_OK")
            print("SCENARIO_CORNER_AUTHORITY_SCORE: %.3f" % (1.0 if (scen_ok and corn_ok) else 0.0))
            if not (scen_ok and corn_ok) and bool(sub) and not masking:
                print("WRONG_CORNER_PROVENANCE_DETECTED: evidence scenario/corner not authority-consistent "
                      "(sub=%s/%s ref=%s/%s want=%s/%s)" % (
                          sub.get("scenario"), sub.get("corner"), ref_sc, ref_co,
                          truth.get("expected_scenario"), truth.get("expected_corner")))
        # multi-conflict global-authority diagnostics (v4 hazard). These fold into EVIDENCE (master gate)
        # via the evidence_consumed_netlist/clock_is_authority + scenario/corner echecks, so the markers are
        # reported (not separately scored): a partial-truth decoy recovery already collapses EVIDENCE_OK.
        # Gated on global_authority_tuple (only the multi_conflict hazard sets it) -> 0001-0004 unaffected.
        if truth.get("global_authority_tuple") is not None:
            ga_ok = bool(e_full and f_full) and not masking
            mc_ok = bool(e_full and f_full and sc_full) and not masking
            if ga_ok:
                print("GLOBAL_AUTHORITY_OK")
            print("GLOBAL_AUTHORITY_SCORE: %.3f" % (1.0 if ga_ok else 0.0))
            if mc_ok:
                print("MULTI_CONFLICT_OK")
            print("MULTI_CONFLICT_SCORE: %.3f" % (1.0 if mc_ok else 0.0))
            if bool(sub) and not ga_ok and not masking:
                print("PARTIAL_DECOY_REJECTED: submitted evidence is locally plausible but not the "
                      "global-authority package (netlist_v2/clk_main/%s/%s)"
                      % (truth.get("expected_scenario"), truth.get("expected_corner")))
        # constraint-graph global-consistency diagnostics (v5 hazard). The runtime enforcement is the SAME
        # proven tuple machinery as v4 (global_authority_tuple + scenario/corner echecks folded into
        # EVIDENCE_OK); these markers only RE-REPORT that gated verdict under constraint-graph names, so a
        # recovery that satisfies a subset of axes (a single decoy / single-axis fix) stays far below pass.
        # Gated on constraint_graph (only the v5 hazard sets it) -> 0001-0005 grader output byte-identical.
        if truth.get("constraint_graph") is not None:
            gc_ok = bool(e_full and f_full) and not masking             # all axes jointly consistent
            uniq_ok = gc_ok                                             # the unique global assignment reached
            chain_ok = bool(e_full and f_full and sc_full) and not masking  # fresh ordered chain, semantically valid
            if gc_ok:
                print("GLOBAL_CONSTRAINT_OK")
            print("GLOBAL_CONSTRAINT_SCORE: %.3f" % (1.0 if gc_ok else 0.0))
            if uniq_ok:
                print("UNIQUE_ASSIGNMENT_OK")
            print("UNIQUE_ASSIGNMENT_SCORE: %.3f" % (1.0 if uniq_ok else 0.0))
            if chain_ok:
                print("EVIDENCE_CHAIN_SEMANTIC_OK")
            print("EVIDENCE_CHAIN_SEMANTIC_SCORE: %.3f" % (1.0 if chain_ok else 0.0))
            if bool(sub) and not gc_ok and not masking:
                print("PAIRWISE_DECOY_REJECTED: submitted package satisfies only a subset of the "
                      "constraint graph (a locally/pairwise-plausible decoy), not the unique global "
                      "assignment (netlist_v2/clk_main/%s/%s)"
                      % (truth.get("expected_scenario"), truth.get("expected_corner")))
        # axis-binding typed-binding diagnostics (v6 hazard). Runtime enforcement is the typed-membership
        # echecks above (folded into EVIDENCE_OK); these markers RE-REPORT that gated verdict under
        # typed-binding names so a signoff-green-but-mis-typed package is named as such. AXIS_SCHEMA_OK =
        # every consumed axis value is an in-domain member of its own axis (incl. exact clock identity);
        # TYPED_BINDING_OK = additionally no PVT label occupies an axis slot; PVT_LABEL_OK = a present PVT
        # label would be metadata-only (a PVT label in any axis slot already fails AXIS_SCHEMA_OK).
        # GLOBAL_CONSTRAINT_OK / UNIQUE_ASSIGNMENT_OK / EVIDENCE_CHAIN_TYPED_OK mirror the v5 verdicts under
        # the typed-axis framing. Gated on axis_schema (only the v6 hazard sets it) -> 0001-0005 byte-identical.
        if truth.get("axis_schema") is not None:
            _schema = truth["axis_schema"]
            _scen_dom = set(_schema["typed_axes"]["scenario_axis"])
            _corn_dom = set(_schema["typed_axes"]["corner_axis"])
            _clk_dom = set(_schema["typed_axes"]["clock_axis"])
            _pvt_dom = set(_schema["typed_axes"].get("pvt_label_axis", []))
            _cc = _sdc_clocks(applied)
            _fc_clk = _cc[0] if _cc else None
            _fc_scen = _jstr(_read("flow_config.json"), "scenario")
            _fc_corn = _jstr(_read("flow_config.json"), "corner")
            axis_schema_ok = bool(_fc_scen in _scen_dom and _fc_corn in _corn_dom
                                  and _fc_clk in _clk_dom) and not masking
            typed_binding_ok = bool(axis_schema_ok and _fc_scen not in _pvt_dom and _fc_corn not in _pvt_dom)
            pvt_ok = bool(axis_schema_ok)   # a pvt label in an axis slot already fails axis_schema_ok
            gc_ok = bool(e_full and f_full) and not masking
            uniq_ok = gc_ok
            chain_ok = bool(e_full and f_full and sc_full) and not masking
            if axis_schema_ok:
                print("AXIS_SCHEMA_OK")
            print("AXIS_SCHEMA_SCORE: %.3f" % (1.0 if axis_schema_ok else 0.0))
            if typed_binding_ok:
                print("TYPED_BINDING_OK")
            print("TYPED_BINDING_SCORE: %.3f" % (1.0 if typed_binding_ok else 0.0))
            if pvt_ok:
                print("PVT_LABEL_OK")
            print("PVT_LABEL_SCORE: %.3f" % (1.0 if pvt_ok else 0.0))
            if gc_ok:
                print("GLOBAL_CONSTRAINT_OK")
            print("GLOBAL_CONSTRAINT_SCORE: %.3f" % (1.0 if gc_ok else 0.0))
            if uniq_ok:
                print("UNIQUE_ASSIGNMENT_OK")
            print("UNIQUE_ASSIGNMENT_SCORE: %.3f" % (1.0 if uniq_ok else 0.0))
            if chain_ok:
                print("EVIDENCE_CHAIN_TYPED_OK")
            print("EVIDENCE_CHAIN_TYPED_SCORE: %.3f" % (1.0 if chain_ok else 0.0))
            if bool(sub) and not axis_schema_ok and not masking:
                print("MISTYPED_BINDING_REJECTED: consumed scenario/corner/clock are not type-correct axis "
                      "bindings (scenario=%s corner=%s clock=%s) -- a signoff-green but mis-typed package is "
                      "rejected. The unique typed assignment is netlist_v2/clk_main/%s/%s."
                      % (_fc_scen, _fc_corn, _fc_clk,
                         truth.get("expected_scenario"), truth.get("expected_corner")))
        if not authority_consistent and bool(sub) and not masking:
            # diagnostic classification (reported, not scored)
            if sub.get("selected_netlist") == truth.get("stale_netlist") or \
               (applied and truth.get("stale_clock") and truth["stale_clock"] in str(applied)):
                print("WRONG_AUTHORITY_DETECTED: consumed/evidence tracks the stale v1 source")
            print("CROSS_SOURCE_CONFLICT_DETECTED: submitted evidence not authority-consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


# ---------------------------------------------------------------------------
# hidden orchestrator + reference re-run (re-runs the FULL trusted chain on the submitted inputs)
# ---------------------------------------------------------------------------
def _run_hidden_sh(evidence_steps: int) -> str:
    stage2_grade_note = ""
    return (
        "#!/bin/bash\n"
        "# Hidden grader for p14 workflow handoff. Trusted phases; no agent code runs in the decision:\n"
        "#   Phase 0 select  : parse submitted flow_config.json + authority clock -> selected*.tcl\n"
        "#   Phase 1 launder : run_launder.tcl read_sdc/write_sdc -> applied_hidden.sdc (injection-safe)\n"
        "#   Phase 2 coverage: TRUSTED PT facts (intended clock present?, #constrained paths)\n"
        "#   Phase 3 signoff : FRESH session signs off consumed netlist from applied_hidden.sdc\n"
        "#   Phase 4 ref     : regen_reference.sh re-runs the TRUSTED evidence chain on submitted inputs\n"
        "#   Phase 5 grade   : grade_workflow.py compares submitted chain vs reference + authority\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"\n'
        'PT_CMD="${EDA_PT_CMD:-pt_shell}"\n'
        'PY_CMD="${EDA_PY_CMD:-python3}"\n'
        'if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found"; exit 0; fi\n'
        "rm -f applied_hidden.sdc coverage.txt selected_launder.tcl selected_signoff.tcl \\\n"
        "      ref_timing_report.rpt ref_evidence_manifest.json ref_stage2_summary.json\n"
        "\n"
        '"$PY_CMD" - <<\'PYX\'\n'
        "import json, re\n"
        "def jget(path, key, default=''):\n"
        "    try:\n"
        "        t = open(path).read()\n"
        "    except OSError:\n"
        "        return default\n"
        "    m = re.search(r'\"' + re.escape(key) + r'\"\\s*:\\s*\"([^\"]*)\"', t)\n"
        "    return m.group(1) if m else default\n"
        "sel = jget('flow_config.json', 'netlist')\n"
        "top = jget('flow_config.json', 'top_module', 'acc_stage')\n"
        "sdc = jget('flow_config.json', 'constraints', 'constraints.sdc')\n"
        "want_clk = jget('handoff_manifest.json', 'clock', 'clk_main')\n"
        "open('selected_launder.tcl','w').write('set sel \"%s\"\\nset top \"%s\"\\nset sdc \"%s\"\\n'%(sel,top,sdc))\n"
        "open('selected_signoff.tcl','w').write('set sel \"%s\"\\nset top \"%s\"\\nset want_clk \"%s\"\\n'%(sel,top,want_clk))\n"
        "PYX\n"
        "\n"
        'APPLY_OUT="$("$PT_CMD" -f run_launder.tcl 2>&1)"; echo "$APPLY_OUT" | sed \'s/^/[apply] /\'\n'
        'COV_OUT="$("$PT_CMD" -f run_coverage.tcl 2>&1)"; echo "$COV_OUT" | sed \'s/^/[apply] /\'\n'
        'SIGN_OUT="$("$PT_CMD" -f run_signoff.tcl 2>&1)"\n'
        'echo "$SIGN_OUT" | grep -E "^SIGNOFF_OK|^SIGNOFF_FAIL" || echo "SIGNOFF_FAIL worst_slack=NONE no_marker"\n'
        "bash regen_reference.sh >/dev/null 2>&1\n"
        '"$PY_CMD" grade_workflow.py handoff_truth.json 2>&1 || {\n'
        '    echo "EVIDENCE_SCORE: 0.000"; echo "EVIDENCE_DETAIL: grade_error"\n'
        '    echo "FINAL_STATE_SCORE: 0.000"; echo "FINAL_STATE_DETAIL: grade_error"\n'
        '    echo "STAGE_CHAIN_SCORE: 0.000"; echo "STAGE_CHAIN_DETAIL: grade_error"\n'
        '    echo "PROVENANCE_SCORE: 0.000"; echo "PROVENANCE_DETAIL: grade_error"\n'
        "}\n"
        "exit 0\n"
    )


def _regen_reference_sh(evidence_steps: int) -> str:
    stage2 = ""
    if evidence_steps == 2:
        stage2 = (
            'cp gen_evidence_stage2_trusted.py "$SCRATCH/gen_evidence_stage2.py"\n'
            'cp evidence_signoff_stage2_trusted.tcl "$SCRATCH/evidence_signoff_stage2.tcl"\n'
            '( cd "$SCRATCH" && EDA_PT_CMD="$PT_CMD" EDA_PY_CMD="$PY_CMD" "$PY_CMD" gen_evidence_stage2.py >/dev/null 2>&1 )\n'
            'cp "$SCRATCH/stage2_summary.json" ref_stage2_summary.json 2>/dev/null\n'
        )
    return (
        "#!/bin/bash\n"
        "# Hidden reference re-run (p14). Recomputes the CORRECT evidence chain from the SUBMITTED\n"
        "# repaired inputs using TRUSTED hidden copies of the generators, in a private scratch dir, so\n"
        "# the oracle has its own reference for each stage's digest/hashes/nonce. The agent-side copies\n"
        "# are never used. Writes ref_timing_report.rpt + ref_evidence_manifest.json (+ ref_stage2 for\n"
        "# evidence_steps=2) into the eval workspace.\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"\n'
        'PT_CMD="${EDA_PT_CMD:-pt_shell}"\n'
        'PY_CMD="${EDA_PY_CMD:-python3}"\n'
        'SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/p14ref.XXXXXX")"\n'
        'cp netlist_v1.v netlist_v2.v tiny.lib tiny.db "$SCRATCH/" 2>/dev/null\n'
        'cp gen_evidence_stage1_trusted.py "$SCRATCH/gen_evidence_stage1.py"\n'
        'cp evidence_signoff_trusted.tcl "$SCRATCH/evidence_signoff.tcl"\n'
        'cp flow_config.json constraints.sdc "$SCRATCH/" 2>/dev/null\n'
        '( cd "$SCRATCH" && EDA_PT_CMD="$PT_CMD" EDA_PY_CMD="$PY_CMD" "$PY_CMD" gen_evidence_stage1.py >/dev/null 2>&1 )\n'
        'cp "$SCRATCH/timing_report.rpt" ref_timing_report.rpt 2>/dev/null\n'
        'cp "$SCRATCH/evidence_manifest.json" "$SCRATCH/evidence_manifest.json" 2>/dev/null\n'
        'cp "$SCRATCH/evidence_manifest.json" ref_evidence_manifest.json 2>/dev/null\n'
        + stage2 +
        'rm -rf "$SCRATCH"\n'
    )


# ---------------------------------------------------------------------------
# spec / manifest / prompt / truth / metadata builders
# ---------------------------------------------------------------------------
def _handoff_manifest(expected_netlist_sha: str, scenario: str = SCENARIO, corner: str = CORNER,
                      cg: bool = False, ab: bool = False, imp: bool = False, srb: str | None = None) -> str:
    if srb is not None:
        # v8 semantic-role-binding manifest: PARTIAL AUTHORITY only. Declares the netlist FAMILY + interface
        # (C1); it deliberately OMITS the concrete clock/scenario/corner values AND any typed-axis mapping.
        # The clear-control variant (0009b) points at the INCOMPLETE glossary; the ambiguous variant (0009a)
        # ships no glossary and no mapping at all. manifest_netlist stays the v2 FAMILY representative.
        _amb = srb == SRB_AMBIGUOUS
        _terminology = ("NONE shipped -- resolve the role of each report field label from the report "
                        "intersection (no glossary, no summary)"
                        if _amb else "glossary.md (INCOMPLETE examples only; NOT a schema)")
        _recovery = ("resolve the semantic role of each report field label from the report intersection; "
                     "infer the clock from non-zero intended-clock coverage; do NOT trust any single shipped "
                     "source (each decoy is pairwise plausible but role-mismatched). A signoff-green-but-"
                     "mis-typed package is still rejected."
                     if _amb else
                     "the reports use canonical scenario/corner labels; glossary.md + public_check_summary.json "
                     "state the disjoint typed axes and the coverage fact -- infer clock/scenario/corner by "
                     "intersecting the constraints; do NOT trust any single shipped source (each decoy is "
                     "pairwise plausible but role-mismatched). A signoff-green-but-mis-typed package is still "
                     "rejected.")
        out = {
            "_comment": ("Handoff package manifest -- PARTIAL AUTHORITY for the semantic-role-binding handoff "
                         "(variant=%s). Declares the netlist FAMILY + interface (C1) and the design intent; "
                         "it deliberately OMITS the concrete clock/scenario/corner values and any typed-axis "
                         "mapping. The unique assignment is the INTERSECTION of the spec.md constraints -- "
                         "NOT a line in this file. Read-only and FROZEN." % srb),
            "design": TOP, "top_module": TOP,
            "interface": {"ports": ["clk_main", "din", "en", "dout"], "note": "v2.x family interface"},
            "netlist_family": "v2.x", "netlist_revision": "v2",
            "library": "tiny.db",
            "terminology": _terminology,
            "constraints": "constraints.sdc", "flow_config": "flow_config.json",
            "stage1_generator": "run_evidence_stage1.sh", "report": "timing_report.rpt",
            "evidence_manifest": "evidence_manifest.json",
            "recovery_note": _recovery,
            "netlist": "netlist_v2.v",  # family representative (C1-allowed); NOT a full tuple statement
            "netlist_provenance_sha256": expected_netlist_sha,
            "history": {
                "v1": "legacy pre-ECO revision on clk_old (provenance only -- out of family, must NOT be consumed)",
                "v2": "current post-ECO family on clk_main, enable-qualified (the handoff design family)",
            },
        }
        return json.dumps(out, indent=2) + "\n"
    if imp:
        # v7 implicit-axis manifest: PARTIAL AUTHORITY only. Declares the netlist FAMILY + interface (C1)
        # and points at the INCOMPLETE glossary; it deliberately OMITS the concrete clock/op_point/mode
        # values AND omits any typed-axis membership. The typed-binding oracle stays in the hidden grader;
        # axis membership must be INFERRED from evidence. manifest_netlist stays the v2 FAMILY representative.
        return json.dumps({
            "_comment": "Handoff package manifest -- PARTIAL AUTHORITY for the implicit-axis-binding handoff. "
                        "Declares the netlist FAMILY + interface (C1) and points at glossary.md (INCOMPLETE "
                        "examples only). It deliberately OMITS the concrete clock/op_point/mode values and "
                        "OMITS any typed-axis membership -- the typed axes are NOT published; they must be "
                        "INFERRED from report context, spec terminology, PVT notation, and coverage facts. "
                        "Read-only and FROZEN.",
            "design": TOP, "top_module": TOP,
            "interface": {"ports": ["clk_main", "din", "en", "dout"], "note": "v2.x family interface"},
            "netlist_family": "v2.x", "netlist_revision": "v2",
            "library": "tiny.db",
            "terminology": "glossary.md (INCOMPLETE examples only; NOT a schema)",
            "constraints": "constraints.sdc", "flow_config": "flow_config.json",
            "stage1_generator": "run_evidence_stage1.sh", "report": "timing_report.rpt",
            "evidence_manifest": "evidence_manifest.json",
            "recovery_note": "axis membership is NOT published: infer op_point->scenario, mode->corner from "
                             "the report context + PVT notation + coverage facts; do NOT trust any single "
                             "shipped source (each decoy is pairwise plausible but mis-typed). A "
                             "signoff-green-but-mis-typed package is still rejected.",
            "netlist": "netlist_v2.v",  # family representative (C1-allowed); NOT a full tuple statement
            "netlist_provenance_sha256": expected_netlist_sha,
            "history": {
                "v1": "legacy pre-ECO revision on clk_old (provenance only -- out of family, must NOT be consumed)",
                "v2": "current post-ECO family on clk_main, enable-qualified (the handoff design family)",
            },
        }, indent=2) + "\n"
    if ab:
        # v6 axis-binding manifest: PARTIAL AUTHORITY only. Declares the netlist FAMILY + interface (C1) and
        # points at the PUBLISHED typed-axis vocabulary (axis_schema.json); it deliberately OMITS the
        # concrete clock/scenario/corner recovery values. The unique typed assignment is the INTERSECTION of
        # the spec.md typed constraints (C1 family x C2 clock identity x C3 scenario-typed x C4 corner-typed
        # x C5 scenario/corner pair) -- NOT a line in this file. manifest_netlist stays the v2 FAMILY
        # representative so the grader's final-state consumed==manifest check stays meaningful.
        return json.dumps({
            "_comment": "Handoff package manifest -- PARTIAL AUTHORITY for the axis-binding handoff. "
                        "Declares the netlist FAMILY + interface (C1) and points at axis_schema.json (the "
                        "PUBLISHED typed-axis vocabulary). It deliberately OMITS the concrete "
                        "clock/scenario/corner recovery values. The unique typed assignment is the "
                        "INTERSECTION of the spec.md constraints (C1 family x C2 clock identity x C3 "
                        "scenario-typed x C4 corner-typed x C5 scenario/corner pair) -- each value bound to "
                        "its OWN axis -- NOT a line in this file. Read-only and FROZEN.",
            "design": TOP, "top_module": TOP,
            "interface": {"ports": ["clk_main", "din", "en", "dout"], "note": "v2.x family interface"},
            "netlist_family": "v2.x", "netlist_revision": "v2",
            "library": "tiny.db",
            "typed_axis_vocabulary": "axis_schema.json",
            "constraints": "constraints.sdc", "flow_config": "flow_config.json",
            "stage1_generator": "run_evidence_stage1.sh", "report": "timing_report.rpt",
            "evidence_manifest": "evidence_manifest.json",
            "recovery_note": "the challenge is BINDING, not vocabulary hiding: infer clock/scenario/corner "
                             "by intersecting spec.md C1-C5 and bind each value to its OWN typed axis; do "
                             "NOT trust any single shipped evidence source (each decoy is locally plausible "
                             "but mis-typed). A signoff-green-but-mis-typed package is still rejected.",
            "netlist": "netlist_v2.v",  # family representative (C1-allowed); NOT a full tuple statement
            "netlist_provenance_sha256": expected_netlist_sha,
            "history": {
                "v1": "legacy pre-ECO revision on clk_old (provenance only -- out of family, must NOT be consumed)",
                "v2": "current post-ECO family on clk_main, enable-qualified (the handoff design family)",
            },
        }, indent=2) + "\n"
    if cg:
        # v5 constraint-graph manifest: PARTIAL AUTHORITY only. Declares the netlist FAMILY + interface +
        # design intent, but deliberately OMITS the concrete clock/scenario/corner recovery values -- the
        # agent must infer those by intersecting the constraints in spec.md (C1 netlist-family x C2 clock
        # coverage x C3 scenario/corner signoff pair). This is the central v5 design choice (no single
        # artifact reveals the full tuple). manifest_netlist stays the v2 FAMILY representative so the
        # grader's final-state consumed==manifest check stays meaningful (v2 family, not a specific tuple).
        return json.dumps({
            "_comment": "Handoff package manifest -- PARTIAL AUTHORITY for the constraint-graph handoff. "
                        "Declares the netlist FAMILY + interface (C1) and the design intent; it deliberately "
                        "OMITS the concrete clock/scenario/corner recovery values. The unique globally-"
                        "consistent package is the INTERSECTION of the spec.md constraints (C1 family x C2 "
                        "clock coverage x C3 scenario/corner signoff pair) -- NOT a line in this file. "
                        "Read-only and FROZEN.",
            "design": TOP, "top_module": TOP,
            "interface": {"ports": ["clk_main", "din", "en", "dout"], "note": "v2.x family interface"},
            "netlist_family": "v2.x", "netlist_revision": "v2",
            "library": "tiny.db",
            "constraints": "constraints.sdc", "flow_config": "flow_config.json",
            "stage1_generator": "run_evidence_stage1.sh", "report": "timing_report.rpt",
            "evidence_manifest": "evidence_manifest.json",
            "recovery_note": "infer clock/scenario/corner from spec.md C1/C2/C3; do NOT trust any single "
                             "shipped evidence source (each decoy satisfies only a subset of the graph).",
            "netlist": "netlist_v2.v",  # family representative (C1-allowed); NOT a full tuple statement
            "netlist_provenance_sha256": expected_netlist_sha,
            "history": {
                "v1": "legacy pre-ECO revision on clk_old (provenance only -- out of family, must NOT be consumed)",
                "v2": "current post-ECO family on clk_main, enable-qualified (the handoff design family)",
            },
        }, indent=2) + "\n"
    return json.dumps({
        "_comment": "Handoff package manifest -- the AUTHORITY/contract for what the evidence flow "
                    "must consume and what the fresh evidence chain must describe. Read-only and "
                    "FROZEN: current handoff is netlist v2 on clk_main, scenario %s, corner %s. The "
                    "defect is in the lagging consumers + stale generated evidence, not here." % (scenario, corner),
        "design": TOP, "top_module": TOP,
        "clock": _CLOCK_PAIRS[0][0], "scenario": scenario, "corner": corner, "library": "tiny.db",
        "constraints": "constraints.sdc", "flow_config": "flow_config.json",
        "stage1_generator": "run_evidence_stage1.sh", "report": "timing_report.rpt",
        "evidence_manifest": "evidence_manifest.json",
        "netlist": "netlist_v2.v", "netlist_revision": "v2",
        "netlist_provenance_sha256": expected_netlist_sha,
        "history": {
            "v1": "legacy pre-ECO revision on clk_old (provenance only -- must NOT be consumed)",
            "v2": "current post-ECO revision on clk_main, enable-qualified (the handoff design)",
        },
    }, indent=2) + "\n"


def _spec_md_sc(evidence_steps: int) -> str:
    """Authoritative spec for the p14 v3 scenario/corner cross-source conflict preset."""
    chain = ""
    if evidence_steps == 2:
        chain = (
            "\n## Two-stage evidence chain (evidence_steps=2)\n\n"
            "Sign-off evidence is a **two-stage ordered chain**:\n\n"
            "1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + "
            "`evidence_manifest.json` from the repaired inputs.\n"
            "2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and "
            "regenerates `stage2_summary.json` (its `upstream_evidence_digest` must equal the fresh "
            "stage-1 report digest).\n\n"
            "Run stage 1 **then** stage 2, after the inputs are repaired.\n"
        )
    return (
        "# acc_stage — Scenario/Corner Provenance Sign-off Handoff (authoritative spec)\n\n"
        "This is a downstream **timing sign-off handoff** for `acc_stage`. The consumed **netlist and "
        "clock are already correct** (`netlist_v2.v` on `clk_main`). The defect is in the **scenario / "
        "corner provenance**: the shipped evidence was generated under the **wrong scenario/corner**, and "
        "the evidence manifest **claims** the authority scenario/corner while actually binding the wrong "
        "one. `handoff_manifest.json` + this document is the **authority**.\n\n"
        "## Current design intent (authority)\n\n"
        "Current contract: netlist **v2** (ports `{clk_main, din, en, dout}`), clock **`clk_main`**, "
        "scenario **`%s`**, corner **`%s`** (`tiny.db`). The evidence chain must be **generated under "
        "`%s`/`%s`**.\n\n"
        "## The defect\n\n"
        "The authority says scenario **`%s`** / corner **`%s`**, but `flow_config.json` selects the "
        "**wrong** scenario/corner (`%s`/`%s`), so the shipped evidence was generated under the wrong "
        "provenance. `evidence_manifest.json` *claims* `%s`/`%s` but its run actually used `%s`/`%s` "
        "(its `run_nonce` and input provenance bind the wrong scenario/corner). The decoy "
        "`prev_corner_signoff.log` reinforces the wrong `%s`/`%s` story but is **non-authoritative**.\n"
        % (SC_AUTH_SCENARIO, SC_AUTH_CORNER, SC_AUTH_SCENARIO, SC_AUTH_CORNER,
           SC_AUTH_SCENARIO, SC_AUTH_CORNER, SC_STALE_SCENARIO, SC_STALE_CORNER,
           SC_AUTH_SCENARIO, SC_AUTH_CORNER, SC_STALE_SCENARIO, SC_STALE_CORNER,
           SC_STALE_SCENARIO, SC_STALE_CORNER)
        + chain +
        "\n## What correct looks like\n\n"
        "1. **Do not** change the netlist or clock — they are already correct (`netlist_v2.v` / "
        "`clk_main`);\n"
        "2. repair `flow_config.json` so its **scenario** is **`%s`** and its **corner** is **`%s`** "
        "(up to the authority);\n"
        "3. **rerun the evidence flow** (stage 1%s) so the evidence is freshly generated under "
        "`%s`/`%s`;\n"
        "4. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**.\n\n"
        % (SC_AUTH_SCENARIO, SC_AUTH_CORNER,
           " then stage 2" if evidence_steps == 2 else "", SC_AUTH_SCENARIO, SC_AUTH_CORNER)
        + "## What will NOT be accepted\n\n"
        "- Leaving the evidence under the wrong scenario/corner.\n"
        "- **Editing the authority manifest or spec DOWN** to the wrong scenario/corner.\n"
        "- **Hand-editing the evidence** to *claim* `%s`/`%s`. The grader re-runs the generator chain on "
        "your submitted `flow_config.json` and pins the authority to the **actual** scenario/corner of "
        "that re-run (digest / input-hashes / `run_nonce`"
        % (SC_AUTH_SCENARIO, SC_AUTH_CORNER)
        + (" / `upstream_evidence_digest`" if evidence_steps == 2 else "") + ").\n"
        "- A green PrimeTime report produced under the wrong scenario/corner.\n"
        "- Trusting the `prev_corner_signoff.log` decoy as authority.\n"
        "- Editing a netlist, the library, the authority manifest, the generators, or the runners; "
        "weakening `constraints.sdc`.\n\n"
        "When done, briefly state the root cause (wrong scenario/corner provenance) and the repair, and "
        "confirm you reran the evidence flow"
        + (" (both stages, in order)" if evidence_steps == 2 else "") + ".\n"
    )


def _prompt_md_sc(evidence_steps: int) -> str:
    steps = (
        "1. Leave the netlist (`netlist_v2.v`) and clock (`clk_main`) as-is — they are already correct.\n"
        "2. Repair `flow_config.json` so `scenario` is `%s` and `corner` is `%s` (the authority).\n"
        "3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + "
        "`evidence_manifest.json` under the authority scenario/corner.\n"
        % (SC_AUTH_SCENARIO, SC_AUTH_CORNER)
    )
    if evidence_steps == 2:
        steps += ("4. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the "
                  "fresh stage-1 digest).\n"
                  "5. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, and "
                  "the scenario/corner match the authority.\n")
    else:
        steps += ("4. Confirm `bash run_public.sh` shows `evidence=FRESH`, `signoff=OK`, and the "
                  "scenario/corner match the authority.\n")
    return (
        "# Task: restore the acc_stage scenario/corner provenance AND regenerate fresh sign-off evidence\n\n"
        "You are handed a downstream **timing sign-off handoff** whose **netlist and clock are already "
        "correct** but whose evidence was generated under the **wrong scenario/corner**. The evidence "
        "manifest **claims** the authority scenario/corner while actually binding the wrong one, and a "
        "`prev_corner_signoff.log` decoy reinforces the wrong story. Diagnose the scenario/corner "
        "authority from `handoff_manifest.json` / `spec.md`, repair `flow_config.json` up to it, then "
        "**rerun the evidence flow"
        + (" (two ordered stages)" if evidence_steps == 2 else "") + "**. Hand-edited or wrong-corner "
        "evidence will **not** pass.\n\n"
        "## The correct trajectory\n\n" + steps +
        "\n## What you can edit / run\n\n"
        "- Edit `flow_config.json` (scenario/corner). Do **not** change the netlist or clock.\n"
        "- Run `bash run_public.sh` for verdict-first feedback (FRESH/STALE/MISSING).\n"
        "- Run the evidence generators to regenerate evidence — do not hand-write evidence files.\n"
        "- Do not edit netlists, the library, the authority manifest, the generators, or the runners.\n\n"
        "When done, briefly state the root cause (wrong scenario/corner provenance) and the repair, and "
        "confirm you reran the evidence flow"
        + (" (both stages, in order)" if evidence_steps == 2 else "") + ".\n"
    )


def _spec_md_mc(evidence_steps: int) -> str:
    """Authoritative spec for the p14 v4 multi-conflict partially-truthful-decoy preset."""
    chain = (
        "\n## Two-stage evidence chain (evidence_steps=2)\n\n"
        "Sign-off evidence is a **two-stage ordered chain**:\n\n"
        "1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + "
        "`evidence_manifest.json` from the repaired inputs.\n"
        "2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and "
        "regenerates `stage2_summary.json` (its `upstream_evidence_digest` must equal the fresh stage-1 "
        "report digest).\n\n"
        "Run stage 1 **then** stage 2, after the inputs are repaired.\n"
    )
    return (
        "# acc_stage — Multi-Conflict Sign-off Handoff (authoritative spec)\n\n"
        "This is a downstream **timing sign-off handoff** for `acc_stage` with **several coupled faults** "
        "and **several partially-truthful decoy evidence sources**. `handoff_manifest.json` + this "
        "document is the **single global authority**. No one shipped evidence source is fully correct; you "
        "must infer the only globally consistent target and regenerate fresh evidence for it.\n\n"
        "## Global authority (the only valid target)\n\n"
        "Current contract: netlist **v2** (`{clk_main, din, en, dout}`), clock **`clk_main`**, scenario "
        "**`%s`**, corner **`%s`** (`tiny.db`). The valid evidence chain is the one freshly generated from "
        "**exactly this package**: `netlist_v2.v` + `clk_main` + `%s`/`%s`.\n\n"
        "## The shipped state (multiple coupled faults)\n\n"
        "`flow_config.json` is wrong on **more than one axis** (stale netlist AND wrong scenario/corner), "
        "and the workspace ships **several decoy evidence sources, each locally plausible and partially "
        "true but globally invalid**:\n\n"
        "- `report_A_typ_test.rpt` — fresh-looking, internally consistent; **right** on netlist/clock "
        "(`netlist_v2`/`clk_main`) but **wrong** on scenario/corner (`%s`/`%s`).\n"
        "- `report_B_stale_netlist.rpt` — fresh-looking, internally consistent; **right** on "
        "scenario/corner (`%s`/`%s`) but **stale** netlist (`netlist_v1.v`).\n"
        "- `evidence_C_manifest.json` — a fresh digest/upstream chain that is **syntactically valid** but "
        "semantically tied to a wrong package.\n"
        "- `prev_signoff.log` — recent and plausible, but **non-authoritative**; reinforces one decoy.\n\n"
        "Each decoy satisfies **part** of the global tuple; **none** satisfies all of it.\n"
        % (SC_AUTH_SCENARIO, SC_AUTH_CORNER, SC_AUTH_SCENARIO, SC_AUTH_CORNER,
           SC_STALE_SCENARIO, SC_STALE_CORNER, SC_AUTH_SCENARIO, SC_AUTH_CORNER)
        + chain +
        "\n## What correct looks like\n\n"
        "1. Repair `flow_config.json` to the **global authority**: netlist **`netlist_v2.v`**, scenario "
        "**`%s`**, corner **`%s`** (clock `clk_main` is already correct);\n"
        "2. **reject every decoy** — do not follow report A (wrong corner), report B (stale netlist), "
        "evidence C (wrong package), or `prev_signoff.log`;\n"
        "3. **rerun the evidence flow** (stage 1 then stage 2) so the chain is freshly generated from the "
        "global-authority package `%s`/`%s`/`netlist_v2`;\n"
        "4. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**.\n\n"
        % (SC_AUTH_SCENARIO, SC_AUTH_CORNER, SC_AUTH_SCENARIO, SC_AUTH_CORNER)
        + "## What will NOT be accepted\n\n"
        "- Following report A because netlist/clock are right (corner is wrong).\n"
        "- Following report B because scenario/corner are right (netlist is stale).\n"
        "- Following evidence C because its digest/upstream chain is syntactically valid (package is "
        "semantically wrong).\n"
        "- Making all files agree with **one** locally-plausible-but-globally-wrong source.\n"
        "- **Editing the authority manifest/spec DOWN** to any decoy.\n"
        "- **Hand-editing evidence** to claim the global package. The grader re-runs the generator chain "
        "on your submitted `flow_config.json` and pins the authority to the **actual** consumed netlist / "
        "clock / scenario / corner of that re-run (digest / input-hashes / `run_nonce` / "
        "`upstream_evidence_digest`).\n"
        "- A green PrimeTime report under any wrong package; rerunning only the last stage; final-state-"
        "only repair; stage1-only; stage2 from a semantically wrong stage1.\n"
        "- Editing a netlist, the library, the authority manifest, the generators, or the runners; "
        "weakening `constraints.sdc`.\n\n"
        "When done, briefly state that the root cause is a multi-axis conflict with partially-truthful "
        "decoys, identify which decoys are partially true vs false, and confirm you repaired to the global "
        "authority and reran both stages in order.\n"
    )


def _prompt_md_mc(evidence_steps: int) -> str:
    return (
        "# Task: resolve the multi-conflict handoff AND regenerate the fresh global-authority evidence chain\n\n"
        "You are handed a downstream **timing sign-off handoff** with **several coupled faults** and "
        "**several partially-truthful decoy evidence sources**. `handoff_manifest.json` / `spec.md` define "
        "the **single global authority**: `netlist_v2.v` + `clk_main` + `%s`/`%s`. No shipped evidence "
        "source is fully correct — each decoy is right on some axes and wrong on others. Diagnose the "
        "global authority, **reject every decoy**, repair `flow_config.json` to the global package, then "
        "**rerun the evidence flow (two ordered stages)**. Following any single decoy, hand-edited "
        "evidence, or a green report under a wrong package will **not** pass.\n\n"
        "## The correct trajectory\n\n"
        "1. Repair `flow_config.json` to the global authority: `netlist_v2.v`, scenario `%s`, corner "
        "`%s` (clock `clk_main` is already correct — do not change it).\n"
        "2. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json` "
        "from the global-authority package.\n"
        "3. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh "
        "stage-1 digest).\n"
        "4. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, and the "
        "consumed package == the global authority.\n\n"
        "## What you can edit / run\n\n"
        "- Edit `flow_config.json` (netlist/scenario/corner). Do **not** change the clock or the netlists.\n"
        "- Run `bash run_public.sh` for verdict-first feedback (FRESH/STALE/MISSING).\n"
        "- Run the evidence generators to regenerate evidence — do not hand-write evidence files.\n"
        "- Do not edit netlists, the library, the authority manifest, the decoy reports, the generators, "
        "or the runners.\n\n"
        "When done, briefly state that the root cause is a multi-axis conflict with partially-truthful "
        "decoys, identify which decoys are partially true vs false, and confirm you repaired to the global "
        "authority and reran both stages in order.\n"
        % (SC_AUTH_SCENARIO, SC_AUTH_CORNER, SC_AUTH_SCENARIO, SC_AUTH_CORNER)
    )


def _spec_md_cg(evidence_steps: int) -> str:
    """v5 constraint-graph spec. CRITICAL: states the constraint STRUCTURE, never the full target tuple.
    The agent must intersect (netlist-family C1) AND (clock-coverage C2) AND (scenario/corner signoff
    pair C3); no single line reveals the answer."""
    lines = [
        "# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (constraint-graph spec)",
        "",
        "This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of date** "
        "AND whose **correct recovery target is NOT stated in any single file**. You must infer the only "
        "globally-consistent package by **intersecting independent constraints**, then regenerate fresh "
        "sign-off evidence by rerunning the flow in order.",
        "",
        "## Design intent (post-ECO v2 family)",
        "",
        "The shipped design family is **netlist v2.x** with interface ports `{clk_main, din, en, dout}`. "
        "Legacy **v1** (`{clk_old, din, dout}`) is provenance-only. The exact recovery package is the "
        "**unique assignment** satisfying all of the constraints below — it is **not** written out as a "
        "single tuple anywhere in this handoff.",
        "",
        "## Constraint graph (intersect these; none alone is the answer)",
        "",
        "- **C1 — netlist family (interface):** the consumed netlist must be in the **v2.x family** with the "
        "`{clk_main, din, en, dout}` interface. The `handoff_manifest.json` declares the allowed family + "
        "interface; it does **not** state the full recovery tuple. `netlist_v1.v` (interface "
        "`{clk_old, din, dout}`) is **out of family** and cannot be the consumed netlist.",
        "- **C2 — clock coverage:** the consumed clock must be the **intended clock** that yields non-zero "
        "path coverage on the v2 netlist. A clock binding that produces **zero constrained paths** (e.g. "
        "`clk_old` against the v2 design) is rejected. (Coverage is a tool-derived fact, reported by the "
        "public runner.)",
        "- **C3 — scenario/corner signoff pair:** the signoff-mode joint-validity table for `acc_stage` "
        "admits **exactly one** (scenario, corner) pair for a setup signoff; the other (scenario, corner) "
        "combinations are characterization-only or non-signoff and are rejected by the hidden oracle.",
        "- **C4 — report provenance / C5 upstream digest / C6 stage dependency:** the evidence chain must be "
        "freshly regenerated from the inferred package (stages ordered); a valid-looking digest bound to "
        "an **invalidated prerequisite stage** (e.g. a stale netlist) is rejected. (Runtime check.)",
        "",
        "## Shipped evidence sources (each is LOCALLY / PAIRWISE plausible, NONE globally consistent)",
        "",
        "- `report_A_scenario_corner.rpt` — satisfies C1+C2; violates C3 (wrong scenario/corner).",
        "- `report_B_stale_netlist.rpt` — satisfies C3; violates C1 (stale netlist, out of family).",
        "- `report_C_wrong_clock.rpt` — satisfies C1+C3; violates C2 (wrong clock, zero coverage).",
        "- `evidence_D_manifest.json` — valid-looking digest/upstream chain; violates C1+C6 (depends on an "
        "invalidated prerequisite stage).",
        "- `prev_signoff.log` — recent, plausible, NON-authoritative.",
        "",
        "**No two decoys agree on the same wrong axis** — you cannot majority-vote; you must intersect the "
        "constraints.",
        "",
    ]
    if evidence_steps == 2:
        lines += [
            "## Two-stage evidence chain (evidence_steps=2)",
            "",
            "Sign-off evidence is a **two-stage chain** and the stages are **ordered**:",
            "",
            "1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + "
            "`evidence_manifest.json` from the repaired inputs.",
            "2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and "
            "regenerates `stage2_summary.json`; its `upstream_evidence_digest` must equal the fresh "
            "stage-1 report digest.",
            "",
            "Run stage 1 **then** stage 2, after the inputs are repaired and consistent.",
            "",
        ]
    lines += [
        "## What correct looks like",
        "",
        "1. Infer the **unique** globally-consistent package by intersecting C1 ∧ C2 ∧ C3.",
        "2. Repair `flow_config.json` to consume that netlist at that (scenario, corner) pair (the clock is "
        "already the intended clock — do **not** change it).",
        "3. Run `bash run_evidence_stage1.sh`"
        + (" then `bash run_evidence_stage2.sh`" if evidence_steps == 2 else "")
        + " to regenerate fresh evidence from the repaired inputs.",
        "4. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**, with "
        "**non-zero intended-clock coverage**.",
        "",
        "## What will NOT be accepted",
        "",
        "- Following any single shipped source (report_A / report_B / report_C / evidence_D / prev_signoff). "
        "Each satisfies only a subset of the constraint graph.",
        "- A **single-axis** repair (fixing only the netlist, or only the clock, or only the scenario/corner).",
        "- A **pairwise-plausible / majority-vote** package (no decoy majority is the global answer).",
        "- A green PrimeTime report alone, or hand-edited evidence, or a stage-2 summary built from a "
        "stale/wrong stage 1.",
        "- Editing the netlists, the library, the authority manifest, the generators, or the runners; or "
        "weakening `constraints.sdc`.",
        "",
    ]
    return "\n".join(lines)


def _prompt_md_cg(evidence_steps: int) -> str:
    return (
        "# Task: infer the unique globally-consistent package AND regenerate the fresh sign-off chain\n\n"
        "You are handed a downstream **timing sign-off handoff** whose evidence is out of date AND whose "
        "**correct recovery target is NOT stated in any single file**. Infer it by intersecting the "
        "constraints in `spec.md` (netlist family C1 + clock coverage C2 + scenario/corner signoff pair "
        "C3), then **rerun the evidence flow" + (" (two ordered stages)" if evidence_steps == 2 else "") +
        "** so the evidence is freshly generated from the inferred package.\n\n"
        "Steps:\n"
        "1. Infer the unique globally-consistent package (intersect C1 ∧ C2 ∧ C3) — do NOT trust any single "
        "shipped source; each decoy (report_A / report_B / report_C / evidence_D) satisfies only a subset.\n"
        "2. Repair `flow_config.json` to that netlist + (scenario, corner) pair (the clock is already the "
        "intended clock — do not change it).\n"
        "3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json` "
        "from the repaired inputs.\n"
        + ("4. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh "
           "stage-1 digest).\n"
           "5. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, non-zero "
           "intended-clock coverage, and the consumed package == the inferred unique assignment.\n"
           if evidence_steps == 2 else
           "4. Confirm `bash run_public.sh` shows `evidence=FRESH`, `signoff=OK`, non-zero intended-clock "
           "coverage, and the consumed package == the inferred unique assignment.\n") +
        "\nYou may edit `flow_config.json`. Do **not** edit netlists, the library, the manifest, the decoy "
        "reports, the generators, or the runners; do not hand-write evidence.\n\n"
        "When done, briefly state the constraint-graph root cause, which decoys are pairwise-plausible, "
        "and confirm you inferred the unique assignment and reran " +
        ("both stages in order" if evidence_steps == 2 else "the stage") + ".\n"
    )


def _spec_md_ab(evidence_steps: int) -> str:
    """v6 axis-binding spec. CRITICAL: PUBLISHES the typed-axis vocabulary (it is in axis_schema.json) and
    states the constraint STRUCTURE, but never the final tuple. The challenge is BINDING: a value valid on
    one axis is invalid on another, a PVT label is never an axis value, and a signoff-green-but-mis-typed
    package is rejected. The agent must intersect C1-C5 AND bind each value to its OWN typed axis."""
    lines = [
        "# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (axis-binding spec)",
        "",
        "This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of date** "
        "AND whose shipped `flow_config.json` carries a **value-swap** on scenario/corner. The typed-axis "
        "vocabulary is **published** in `axis_schema.json` -- the challenge is correct **binding**, not "
        "vocabulary hiding. You must infer the only globally-consistent **typed** package, bind each value "
        "to its own axis, then regenerate fresh sign-off evidence by rerunning the flow in order.",
        "",
        "## Design intent (post-ECO v2 family)",
        "",
        "The shipped design family is **netlist v2.x** with interface ports `{clk_main, din, en, dout}`. "
        "Legacy **v1** (`{clk_old, din, dout}`) is provenance-only. The exact recovery package is the "
        "**unique typed assignment** satisfying all constraints below -- it is **not** written out anywhere.",
        "",
        "## Typed axes (vocabulary published in `axis_schema.json`)",
        "",
        "- **scenario_axis:** `{slow, typ, fast}` -- may occupy ONLY the scenario field.",
        "- **corner_axis:** `{func, test, lowpower}` -- may occupy ONLY the corner field.",
        "- **clock_axis:** `{clk_old, clk_main}` -- exact identity required (`clk_main`).",
        "- **pvt_label_axis:** `{slow_1.0V_125C, typ_1.0V_25C, fast_0.8V_0C}` -- DESCRIPTIVE METADATA mapping "
        "to a `(scenario, corner)` pair; **never** a valid scenario or corner value.",
        "",
        "**A value valid on one axis is invalid on another.** A corner value in the scenario slot, a "
        "scenario value in the corner slot, or a PVT label in either slot is a **type error**.",
        "",
        "## Constraint graph (intersect these; none alone is the answer)",
        "",
        "- **C1 — netlist family (interface):** the consumed netlist must be in the **v2.x family** with the "
        "`{clk_main, din, en, dout}` interface (`netlist_v1.v` is out of family).",
        "- **C2 — clock identity:** the consumed clock must be the exact intended clock (`clk_main`); a "
        "generic/aliased name (e.g. `clk`) is rejected.",
        "- **C3 — scenario typed:** the scenario field must be a `scenario_axis` member.",
        "- **C4 — corner typed:** the corner field must be a `corner_axis` member.",
        "- **C5 — scenario/corner signoff pair:** the signoff-mode joint-validity table admits **exactly "
        "one** `(scenario, corner)` pair for a setup signoff.",
        "- **C6/C7 — report provenance / upstream digest / stage dependency:** the evidence chain must be "
        "freshly regenerated from the inferred typed package (stages ordered); a valid-looking digest bound "
        "to a typed-mismatched or invalidated prerequisite is rejected. (Runtime check.)",
        "",
        "## Shipped evidence sources (each is LOCALLY plausible, NONE type-correct)",
        "",
        "- `report_A_value_swap.rpt` — right netlist/clock; scenario/corner SWAPPED (violates C3+C4).",
        "- `report_B_pvt_corner.rpt` — a PVT label used as the corner (violates C4).",
        "- `report_C_wrong_clock.rpt` — a generic clock alias `clk` (violates C2).",
        "- `evidence_D_typed_mismatch.json` — valid-looking chain with swapped scenario/corner fields "
        "(violates C3+C4).",
        "- `prev_signoff.log` — recent, plausible, NON-authoritative.",
        "",
        "**A package with the correct netlist+clock still PrimeTime-signs-off GREEN when scenario/corner are "
        "swapped or a PVT label is substituted** -- because the report body is corner-independent. Type "
        "binding (C3/C4), not signoff, is what rejects a signoff-green-but-mis-typed package.",
        "",
    ]
    if evidence_steps == 2:
        lines += [
            "## Two-stage evidence chain (evidence_steps=2)",
            "",
            "Sign-off evidence is a **two-stage chain** and the stages are **ordered**:",
            "",
            "1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + "
            "`evidence_manifest.json` from the repaired inputs.",
            "2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and "
            "regenerates `stage2_summary.json`; its `upstream_evidence_digest` must equal the fresh "
            "stage-1 report digest.",
            "",
            "Run stage 1 **then** stage 2, after the inputs are repaired and typed-consistent.",
            "",
        ]
    lines += [
        "## What correct looks like",
        "",
        "1. Infer the **unique typed** package by intersecting C1 ∧ C2 ∧ C3 ∧ C4 ∧ C5.",
        "2. **Bind** each value to its own typed axis (scenario-axis value in the scenario field; corner-axis "
        "value in the corner field; `clk_main` as the clock).",
        "3. Repair `flow_config.json` to consume that netlist at that typed `(scenario, corner)` pair.",
        "4. Run `bash run_evidence_stage1.sh`"
        + (" then `bash run_evidence_stage2.sh`" if evidence_steps == 2 else "")
        + " to regenerate fresh evidence from the repaired inputs.",
        "5. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**, with "
        "**non-zero intended-clock coverage**.",
        "",
        "## What will NOT be accepted",
        "",
        "- A **value-swap** (a corner value in the scenario slot / a scenario value in the corner slot) -- "
        "signoff-green but mis-typed.",
        "- A **PVT label** substituted for a scenario or corner value.",
        "- A **generic clock alias** (`clk`) instead of `clk_main`.",
        "- Following any single shipped source (report_A / report_B / report_C / evidence_D / prev_signoff).",
        "- A **single-axis** repair (fixing only the netlist, or only the clock, or only scenario/corner).",
        "- A green PrimeTime report alone, or hand-edited evidence, or a stage-2 summary built from a "
        "stale/wrong/typed-mismatched stage 1.",
        "- Editing the netlists, the library, the manifest, `axis_schema.json`, the generators, or the "
        "runners; or weakening `constraints.sdc`.",
        "",
    ]
    return "\n".join(lines)


def _prompt_md_ab(evidence_steps: int) -> str:
    return (
        "# Task: infer the unique type-correct package, bind each value to its own axis, AND regenerate the "
        "fresh sign-off chain\n\n"
        "You are handed a downstream **timing sign-off handoff** whose evidence is out of date AND whose "
        "`flow_config.json` carries a **value-swap** on scenario/corner. The typed-axis vocabulary is "
        "**published** in `axis_schema.json` -- the challenge is correct **binding**, not vocabulary hiding. "
        "Infer the unique typed assignment by intersecting the constraints in `spec.md` (C1 netlist family + "
        "C2 clock identity + C3 scenario-typed + C4 corner-typed + C5 scenario/corner pair), bind each value "
        "to its OWN axis, then **rerun the evidence flow" + (" (two ordered stages)" if evidence_steps == 2 else "") +
        "** so the evidence is freshly generated from the inferred package.\n\n"
        "Steps:\n"
        "1. Infer the unique typed assignment (intersect C1-C5); bind each value to its own axis. Do NOT "
        "trust any single shipped source; each decoy is locally plausible but mis-typed.\n"
        "2. Repair `flow_config.json` to that netlist + typed `(scenario, corner)` pair + clock identity "
        "(the clock is already `clk_main` -- do not change it).\n"
        "3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json` "
        "from the repaired inputs.\n"
        + ("4. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh "
           "stage-1 digest).\n"
           "5. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, non-zero "
           "intended-clock coverage, and the consumed package == the inferred typed assignment.\n"
           if evidence_steps == 2 else
           "4. Confirm `bash run_public.sh` shows `evidence=FRESH`, `signoff=OK`, non-zero intended-clock "
           "coverage, and the consumed package == the inferred typed assignment.\n") +
        "\nA package with the correct netlist+clock still PrimeTime-signs-off GREEN when scenario/corner are "
        "swapped -- type binding, not signoff, is what rejects it. You may edit `flow_config.json`. Do "
        "**not** edit netlists, the library, the manifest, `axis_schema.json`, the decoy reports, the "
        "generators, or the runners; do not hand-write evidence.\n\n"
        "When done, briefly state the axis-binding root cause, which decoys are mis-typed, and confirm you "
        "inferred the unique typed assignment and reran " +
        ("both stages in order" if evidence_steps == 2 else "the stage") + ".\n"
    )


def _spec_md_implicit(evidence_steps: int) -> str:
    """v7 implicit-axis spec. CRITICAL: NO complete typed vocabulary is published. The spec gives PARTIAL
    terminology (operating point / signoff mode), a PVT-descriptor example, and the disjoint-axes rule --
    enough for a domain-aware reader to INFER membership from report context + coverage, not enough to look
    it up from a schema. The answer tuple is never stated."""
    lines = [
        "# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (implicit typed-axis spec)",
        "",
        "This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of date** "
        "AND whose shipped `flow_config.json` carries a **value-swap** on the typed axes. The typed axes are "
        "**NOT** published as a schema -- you must **infer** axis membership from the report context, the "
        "terminology here, PVT notation, and the coverage facts, then recover the only globally-consistent "
        "**typed** package and regenerate fresh sign-off evidence.",
        "",
        "## Design intent (post-ECO v2 family)",
        "",
        "The shipped design family is **netlist v2.x** with interface ports `{clk_main, din, en, dout}`. "
        "Legacy **v1** (`{clk_old, din, dout}`) is provenance-only. The setup signoff is taken at the "
        "**slow operating point** in the **functional signoff mode**. The exact recovery package is the "
        "**unique typed assignment** satisfying all constraints below -- it is **not** written out anywhere.",
        "",
        "## Terminology (partial; see glossary.md for examples -- NOT a complete schema)",
        "",
        "- The reports carry an **operating-point** field (`op_point=`) and a **signoff-mode** field "
        "(`mode=`). These are DISJOINT typed axes: a value valid on one is invalid on the other.",
        "- A **PVT descriptor** (e.g. `slow_1.0V_125C`) is a string `<process>_<voltage>_<temperature>` that "
        "**characterizes** an (operating point, signoff mode) pair but is **never** a valid `op_point` or "
        "`mode` value.",
        "- The consumed clock is the one yielding **non-zero intended-clock path coverage** on the design.",
        "",
        "**No complete value-to-axis table is provided.** Infer membership from how values are used.",
        "",
        "## Constraints (intersect these; none alone is the answer)",
        "",
        "- **C1 netlist family:** the consumed netlist is in the v2.x family with the `{clk_main,din,en,dout}` "
        "interface (`netlist_v1.v` is out of family).",
        "- **C2 clock coverage:** the consumed clock is the only one with non-zero intended-clock coverage "
        "on the v2 netlist (a coverage fact).",
        "- **C3 op_point typed:** the `op_point` value is an operating-point member (infer which values are "
        "operating points from PVT notation + context).",
        "- **C4 mode typed:** the `mode` value is a signoff-mode member (the OTHER typed axis).",
        "- **C5 signoff pair:** the setup signoff uses the slow operating point in the functional mode.",
        "- **C6/C7 provenance / digest:** the evidence chain must be freshly regenerated from the inferred "
        "typed package; a valid-looking digest bound to a typed-mismatched or invalidated stage is rejected.",
        "",
        "## Shipped evidence sources (each is LOCALLY plausible, NONE globally correct as-shipped)",
        "",
        "- `report_A_context_swap.rpt` — right netlist/clock; `op_point`/`mode` swapped.",
        "- `report_B_context_stale.rpt` — right `op_point`/`mode`; stale netlist.",
        "- `report_C_context_pvt.rpt` — a PVT descriptor used in `mode`.",
        "- `evidence_D_context_mismatch.json` — valid-looking chain; `op_point`/`mode` swapped inside.",
        "- `public_check_summary.json` — pairwise typed/provenance inconsistency symptoms + the coverage "
        "fact (verdict-first; never the answer/schema).",
        "- `glossary.md` — INCOMPLETE terminology examples (NOT a schema).",
        "- `prev_signoff.log` — recent, plausible, NON-authoritative.",
        "",
        "**A package with the correct netlist+clock still PrimeTime-signs-off GREEN when the typed axes are "
        "swapped or a PVT label is substituted** (the report body is corner-independent). Typed binding, not "
        "signoff, is what rejects a signoff-green-but-mis-typed package.",
        "",
    ]
    if evidence_steps == 2:
        lines += [
            "## Two-stage evidence chain (evidence_steps=2)",
            "",
            "1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + "
            "`evidence_manifest.json` from the repaired inputs.",
            "2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and "
            "regenerates `stage2_summary.json`; its `upstream_evidence_digest` must equal the fresh stage-1 "
            "report digest.",
            "",
            "Run stage 1 **then** stage 2, after the inputs are repaired and typed-consistent.",
            "",
        ]
    lines += [
        "## What correct looks like",
        "",
        "1. **Infer** axis membership from the evidence (op_point→scenario, mode→corner via PVT notation + "
        "context + coverage).",
        "2. **Infer** the unique typed package by intersecting C1–C5.",
        "3. **Repair** `flow_config.json` to that netlist + typed (scenario, corner) pair + clock.",
        "4. Run `bash run_evidence_stage1.sh`"
        + (" then `bash run_evidence_stage2.sh`" if evidence_steps == 2 else "")
        + " to regenerate fresh evidence.",
        "",
        "## What will NOT be accepted",
        "",
        "- A **value-swap** on the typed axes (signoff-green but mis-typed).",
        "- A **PVT descriptor** substituted for an `op_point`/`mode` value.",
        "- A **wrong clock** (zero coverage).",
        "- Following any single shipped source; a single-axis repair; a green report alone; hand-edited "
        "evidence; a stage-2 from a stale/typed-wrong stage 1.",
        "- Editing the netlists, library, manifest, glossary, generators, or runners; weakening "
        "`constraints.sdc`.",
        "",
    ]
    return "\n".join(lines)


def _prompt_md_implicit(evidence_steps: int) -> str:
    return (
        "# Task: infer the typed-axis membership AND the unique typed package, then regenerate the fresh "
        "sign-off chain\n\n"
        "You are handed a downstream **timing sign-off handoff** whose evidence is out of date AND whose "
        "`flow_config.json` carries a value-swap on the typed axes. The typed axes are **NOT** published as a "
        "schema -- infer membership from the report context (`op_point=` / `mode=`), the spec terminology, "
        "PVT notation, and the coverage facts. Then infer the unique typed assignment (intersect C1–C5), "
        "repair `flow_config.json`, and **rerun the evidence flow"
        + (" (two ordered stages)" if evidence_steps == 2 else "")
        + "** so the evidence is freshly generated from the inferred package.\n\n"
        "Steps:\n"
        "1. Infer axis membership from the evidence (PVT notation reveals the operating-point values; the "
        "coverage fact reveals the clock; the manifest+interface reveal the netlist; the remaining axis is "
        "the signoff mode).\n"
        "2. Infer the unique typed assignment by intersecting C1–C5; reject every pairwise-plausible decoy.\n"
        "3. Repair `flow_config.json` to the inferred netlist + (scenario, corner) pair + clock identity.\n"
        "4. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json`.\n"
        + ("5. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh "
           "stage-1 digest).\n"
           "6. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, non-zero "
           "intended-clock coverage, and the consumed package == the inferred typed assignment.\n"
           if evidence_steps == 2 else
           "5. Confirm `bash run_public.sh` shows `evidence=FRESH`, `signoff=OK`, non-zero intended-clock "
           "coverage, and the consumed package == the inferred typed assignment.\n") +
        "\nA package with the correct netlist+clock still PrimeTime-signs-off GREEN when the typed axes are "
        "swapped -- typed binding, not signoff, is what rejects it. You may edit `flow_config.json`. Do "
        "**not** edit netlists, the library, the manifest, `glossary.md`, the decoy reports, the generators, "
        "or the runners; do not hand-write evidence.\n\n"
        "When done, briefly state the axis-binding root cause (which values are operating-point vs "
        "signoff-mode and how you inferred it), which decoys are mis-typed, and confirm you inferred the "
        "unique typed assignment and reran " +
        ("both stages in order" if evidence_steps == 2 else "the stage") + ".\n"
    )


def _spec_md_srb(evidence_steps: int, variant: str) -> str:
    """v8 semantic-role-binding REPRODUCTION spec. The hidden typed-binding oracle is reused byte-identically
    from v6/v7; the variant controls ONLY the visible clarity bundle. The answer tuple is never stated.
      ambiguous (0009a): overloaded op_point/mode labels + NO anchors (no glossary/summary/coverage/spec
        hint) -- the agent must resolve the semantic role of each label from the report intersection.
      clear_control (0009b): canonical scenario/corner labels + the disjoint-axis statement + the signoff-
        pair binding hint + glossary + public_check_summary (the negative control, ~v7)."""
    amb = variant == SRB_AMBIGUOUS
    role_fields = "`op_point=` / `mode=`" if amb else "`scenario=` / `corner=`"
    title = "ambiguous-role spec" if amb else "clear-control spec"
    lines = [
        "# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (semantic-role-binding, %s)" % title,
        "",
        "This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of date** "
        "AND whose shipped `flow_config.json` carries a **value-swap** on the signoff axes. You must recover "
        "the only globally-consistent package by **resolving the semantic role of each shipped value** (which "
        "value belongs on which axis) and intersecting the partially-truthful sources, then regenerate fresh "
        "sign-off evidence by rerunning the flow in order.",
        "",
        "## Design intent (post-ECO v2 family)",
        "",
        "The shipped design family is **netlist v2.x** with interface ports `{clk_main, din, en, dout}`. "
        "Legacy **v1** (`{clk_old, din, dout}`) is provenance-only. The exact recovery package is the "
        "**unique assignment** satisfying all constraints below -- it is **not** written out as a single tuple "
        "anywhere in this handoff.",
        "",
    ]
    if amb:
        # 0009a: MINIMAL terminology. No disjoint-axis statement, no PVT rule, no signoff-pair hint, no
        # coverage fact, no glossary reference. The role of op_point/mode must be inferred from the reports.
        lines += [
            "## Terminology",
            "",
            "- The shipped reports use two field labels: %s. Their meaning is NOT defined here -- infer it "
            "from how the values are used across the (conflicting) report sources." % role_fields,
            "- The consumed clock is the one that yields non-zero intended-clock path coverage on the design.",
            "",
            "**No value-to-axis mapping is provided.** Resolve the role of each label from the evidence.",
            "",
        ]
    else:
        # 0009b: canonical labels + the disjoint-axis statement + the signoff-pair binding hint + glossary
        # reference (the negative-control clarity bundle). Still does NOT print the full tuple.
        lines += [
            "## Terminology (partial; see glossary.md for examples -- NOT a complete schema)",
            "",
            "- The reports carry a **scenario** field (`scenario=`) and a **corner** field (`corner=`). These "
            "are DISJOINT typed axes: a value valid on one is invalid on the other.",
            "- A **PVT descriptor** (e.g. `slow_1.0V_125C`) is a string `<process>_<voltage>_<temperature>` "
            "that **characterizes** a (scenario, corner) pair but is **never** a valid scenario or corner value.",
            "- The setup signoff is taken at the **slow scenario** in the **functional corner**.",
            "- The consumed clock is the one yielding **non-zero intended-clock path coverage** on the design.",
            "",
            "**No complete value-to-axis table is provided.** Infer the unique assignment from the constraints.",
            "",
        ]
    lines += [
        "## Constraints (intersect these; none alone is the answer)",
        "",
        "- **C1 netlist family:** the consumed netlist is in the v2.x family with the `{clk_main,din,en,dout}` "
        "interface (`netlist_v1.v` is out of family).",
        "- **C2 clock coverage:** the consumed clock is the only one with non-zero intended-clock coverage on "
        "the v2 netlist.",
        "- **C3 scenario typed:** the scenario value must be a scenario member (a corner value or PVT label in "
        "the scenario role is a type error).",
        "- **C4 corner typed:** the corner value must be a corner member (a scenario value or PVT label in the "
        "corner role is a type error).",
        "- **C5 scenario/corner signoff pair:** exactly one `(scenario, corner)` pair is the setup signoff pair.",
        "- **C6/C7 provenance / digest:** the evidence chain must be freshly regenerated from the inferred "
        "package (stages ordered); a valid-looking digest bound to a role-mismatched or invalidated stage is "
        "rejected.",
        "",
        "## Shipped evidence sources (each is LOCALLY plausible, NONE globally correct as-shipped)",
        "",
        "- `report_A_role_swap.rpt` — right netlist/clock; the role fields are SWAPPED vs the authority.",
        "- `report_B_role_stale.rpt` — correct role fields; stale netlist (netlist_v1).",
        "- `report_C_role_pvt.rpt` — a PVT descriptor in the corner role (and a generic clock alias).",
        "- `evidence_D_role_mismatch.json` — valid-looking chain; the role fields are swapped inside.",
    ]
    if not amb:
        lines += [
            "- `public_check_summary.json` — pairwise inconsistency symptoms + the coverage fact (verdict-"
            "first; never the answer/schema).",
            "- `glossary.md` — INCOMPLETE terminology examples (NOT a schema).",
        ]
    lines += [
        "- `prev_signoff.log` — recent, plausible, NON-authoritative.",
        "",
        "**A package with the correct netlist+clock still PrimeTime-signs-off GREEN when the role fields are "
        "swapped or a PVT label is substituted** (the report body is corner-independent). Semantic-role "
        "binding, not signoff, is what rejects a signoff-green-but-mis-typed package.",
        "",
    ]
    if evidence_steps == 2:
        lines += [
            "## Two-stage evidence chain (evidence_steps=2)",
            "",
            "1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + "
            "`evidence_manifest.json` from the repaired inputs.",
            "2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and "
            "regenerates `stage2_summary.json`; its `upstream_evidence_digest` must equal the fresh stage-1 "
            "report digest.",
            "",
            "Run stage 1 **then** stage 2, after the inputs are repaired and role-consistent.",
            "",
        ]
    lines += [
        "## What correct looks like",
        "",
    ]
    if amb:
        lines += [
            "1. **Resolve** the semantic role of each report field label from the report intersection.",
            "2. **Infer** the unique assignment by intersecting C1–C5 (reject each pairwise-plausible decoy).",
        ]
    else:
        lines += [
            "1. **Infer** the unique assignment by intersecting C1–C5 (the reports use canonical scenario/"
            "corner labels; glossary.md + public_check_summary.json give the disjoint-axis rule and the "
            "coverage fact).",
        ]
    lines += [
        "3. **Repair** `flow_config.json` to that netlist + `(scenario, corner)` pair + clock.",
        "4. Run `bash run_evidence_stage1.sh`"
        + (" then `bash run_evidence_stage2.sh`" if evidence_steps == 2 else "")
        + " to regenerate fresh evidence.",
        "",
        "## What will NOT be accepted",
        "",
        "- A **value-swap / role mismatch** on the signoff axes (signoff-green but mis-typed).",
        "- A **PVT descriptor** substituted for a scenario or corner value.",
        "- A **wrong clock** (zero coverage / a generic alias).",
        "- Following any single shipped source; a single-axis repair; a green report alone; hand-edited "
        "evidence; a stage-2 from a stale/role-wrong stage 1.",
        "- Editing the netlists, library, manifest"
        + (", glossary," if not amb else "")
        + " generators, or runners; weakening `constraints.sdc`.",
        "",
    ]
    return "\n".join(lines)


def _prompt_md_srb(evidence_steps: int, variant: str) -> str:
    amb = variant == SRB_AMBIGUOUS
    role_hint = ("The reports use field labels `op_point` / `mode` whose logical-axis role is NOT defined "
                 "upfront -- resolve it from the report intersection (no glossary or summary is provided)."
                 if amb else
                 "The reports use canonical `scenario` / `corner` labels; glossary.md + "
                 "public_check_summary.json state the disjoint typed axes and the coverage fact.")
    return (
        "# Task: resolve the semantic-role binding, infer the unique package, AND regenerate the fresh "
        "sign-off chain\n\n"
        "You are handed a downstream **timing sign-off handoff** whose evidence is out of date AND whose "
        "`flow_config.json` carries a value-swap on the signoff axes. %s Infer the unique assignment by "
        "intersecting the constraints in `spec.md` (C1 netlist family + C2 clock coverage + C3 scenario-typed "
        "+ C4 corner-typed + C5 signoff pair), reject every pairwise-plausible decoy, repair `flow_config.json`, "
        "and **rerun the evidence flow"
        % role_hint
        + (" (two ordered stages)" if evidence_steps == 2 else "")
        + "** so the evidence is freshly generated from the inferred package.\n\n"
        "Steps:\n"
        "1. "
        + ("Resolve the semantic role of each report field label from the report intersection. Then "
           if amb else "")
        + "Infer the unique assignment by intersecting C1–C5; do NOT trust any single shipped source (each "
        "decoy is pairwise plausible but role-mismatched).\n"
        "2. Repair `flow_config.json` to the inferred netlist + `(scenario, corner)` pair + clock identity "
        "(the clock is the only one with non-zero intended-clock coverage).\n"
        "3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json`.\n"
        + ("4. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh "
           "stage-1 digest).\n"
           "5. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, non-zero "
           "intended-clock coverage, and the consumed package == the inferred assignment.\n"
           if evidence_steps == 2 else
           "4. Confirm `bash run_public.sh` shows `evidence=FRESH`, `signoff=OK`, non-zero intended-clock "
           "coverage, and the consumed package == the inferred assignment.\n")
        + "\nA package with the correct netlist+clock still PrimeTime-signs-off GREEN when the role fields "
        "are swapped -- semantic-role binding, not signoff, is what rejects it. You may edit "
        "`flow_config.json`. Do **not** edit netlists, the library, the manifest"
        + (", `glossary.md`," if not amb else "")
        + " the decoy reports, the generators, or the runners; do not hand-write evidence.\n\n"
        "When done, briefly state the semantic-role binding (which value is the scenario vs the corner and "
        "how you resolved it), which decoys are role-mismatched, and confirm you inferred the unique "
        "assignment and reran " + ("both stages in order" if evidence_steps == 2 else "the stage") + ".\n"
    )


def _spec_md(evidence_steps: int, sc_hazard: bool = False, mc_hazard: bool = False,
             cg_hazard: bool = False, ab_hazard: bool = False, imp_hazard: bool = False,
             srb_hazard: bool = False, srb_variant: str | None = None) -> str:
    if srb_hazard:
        return _spec_md_srb(evidence_steps, srb_variant or SRB_AMBIGUOUS)
    if imp_hazard:
        return _spec_md_implicit(evidence_steps)
    if ab_hazard:
        return _spec_md_ab(evidence_steps)
    if cg_hazard:
        return _spec_md_cg(evidence_steps)
    if mc_hazard:
        return _spec_md_mc(evidence_steps)
    if sc_hazard:
        return _spec_md_sc(evidence_steps)
    chain = ""
    if evidence_steps == 2:
        chain = (
            "\n## Two-stage evidence chain (evidence_steps=2)\n\n"
            "Sign-off evidence here is a **two-stage chain** and the stages are **ordered**:\n\n"
            "1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + "
            "`evidence_manifest.json` from the repaired inputs (the input-path timing evidence).\n"
            "2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and "
            "regenerates `stage2_summary.json` (the register-path summary). Its "
            "`upstream_evidence_digest` must equal the fresh stage-1 report digest.\n\n"
            "You must run stage 1 **then** stage 2, after the inputs are repaired. A stage-2 summary "
            "built from a stale or missing stage 1 (or generated before the repair) will not match the "
            "hidden re-run and will fail.\n"
        )
    return (
        "# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (authoritative spec)\n\n"
        "This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of "
        "date**. Make the handoff consistent with the authority **and regenerate fresh sign-off "
        "evidence by rerunning the flow in order** — editing evidence by hand or leaving stale evidence "
        "in place is not acceptable. `handoff_manifest.json` + this document is the **authority**.\n\n"
        "## Current design intent (post-ECO v2)\n\n"
        "Current contract: netlist **v2** (ports `{clk_main, din, en, dout}`), clock **`clk_main`**, "
        "scenario **func**, corner/library **typ** (`tiny.db`). Legacy **v1** (`{clk_old, din, dout}`) "
        "is provenance-only and must **not** be consumed.\n\n"
        "## The defect\n\n"
        "The authority says **v2 / clk_main**, but the consumers lag: `flow_config.json` selects stale "
        "`netlist_v1.v`, `constraints.sdc` binds stale `clk_old`, and the shipped evidence is the old "
        "v1/clk_old run. The stale evidence *correctly* describes the stale inputs — locally "
        "self-consistent but wrong against the authority.\n"
        + chain +
        "\n## What correct looks like\n\n"
        "1. `flow_config.json` consumes the **v2** netlist;\n"
        "2. `constraints.sdc` binds **`clk_main`**;\n"
        "3. you have **rerun the evidence flow** (stage 1"
        + (" then stage 2" if evidence_steps == 2 else "") +
        ") so the evidence is freshly generated from the repaired inputs;\n"
        "4. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**.\n\n"
        "## What will NOT be accepted\n\n"
        "- A green PrimeTime report alone (the stale island self-signs-off green on the wrong design).\n"
        "- **Editing the evidence files by hand.** The grader re-runs the generator chain on your "
        "submitted inputs and rejects any evidence that does not match (digest / input-hashes / "
        "`run_nonce`"
        + (" / `upstream_evidence_digest`" if evidence_steps == 2 else "") + ").\n"
        "- **Leaving stale evidence** after repairing, or **running a generator before repairing**.\n"
        + ("- **A stage-2 summary built from a stale/missing stage 1**, or running stage 2 before "
           "stage 1.\n" if evidence_steps == 2 else "") +
        "- Editing a netlist, the library, the authority manifest, the generators, or the runners; "
        "weakening `constraints.sdc` (timing exceptions / loosened period).\n\n"
        "When done, briefly state the root cause and the repair, and confirm you reran the evidence "
        "flow" + (" (both stages, in order)" if evidence_steps == 2 else "") + ".\n"
    )


def _prompt_md(evidence_steps: int, sc_hazard: bool = False, mc_hazard: bool = False,
               cg_hazard: bool = False, ab_hazard: bool = False, imp_hazard: bool = False,
               srb_hazard: bool = False, srb_variant: str | None = None) -> str:
    if srb_hazard:
        return _prompt_md_srb(evidence_steps, srb_variant or SRB_AMBIGUOUS)
    if imp_hazard:
        return _prompt_md_implicit(evidence_steps)
    if ab_hazard:
        return _prompt_md_ab(evidence_steps)
    if cg_hazard:
        return _prompt_md_cg(evidence_steps)
    if mc_hazard:
        return _prompt_md_mc(evidence_steps)
    if sc_hazard:
        return _prompt_md_sc(evidence_steps)
    steps = (
        "1. Repair `flow_config.json` to consume `netlist_v2.v`.\n"
        "2. Repair `constraints.sdc` to bind `clk_main`.\n"
        "3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + "
        "`evidence_manifest.json`.\n"
    )
    if evidence_steps == 2:
        steps += ("4. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the "
                  "fresh stage-1 digest).\n"
                  "5. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, "
                  "and the consumed package matches the authority.\n")
    else:
        steps += ("4. Confirm `bash run_public.sh` shows `evidence=FRESH`, `signoff=OK`, and the "
                  "consumed package matches the authority.\n")
    return (
        "# Task: restore the acc_stage handoff AND regenerate the fresh sign-off evidence chain\n\n"
        "You are handed a downstream **timing sign-off handoff** whose evidence is **out of date**. "
        "Repair the package to the authority contract, then **rerun the evidence flow"
        + (" (two ordered stages)" if evidence_steps == 2 else "") + "** so the evidence is freshly "
        "generated from the repaired inputs. A green report alone, hand-edited evidence, stale evidence "
        "left in place, "
        + ("or a stage-2 summary built from a stale/missing stage 1, " if evidence_steps == 2 else "") +
        "will **not** pass.\n\n"
        "## The correct trajectory\n\n" + steps +
        "\n## What you can edit / run\n\n"
        "- Edit `flow_config.json` and `constraints.sdc`.\n"
        "- Run `bash run_public.sh` for verdict-first feedback (FRESH/STALE/MISSING).\n"
        "- Run the evidence generators to regenerate evidence — do not hand-write evidence files.\n"
        "- Do not edit netlists, the library, the authority manifest, the generators, or the runners.\n\n"
        "When done, briefly state the root cause and the repair, and confirm you reran the evidence "
        "flow" + (" (both stages, in order)" if evidence_steps == 2 else "") + ".\n"
    )


def enumerate_constraint_graph(cg: dict) -> dict:
    """PURE, offline. Enumerate the full axis product of a constraint graph and apply each constraint's
    allowed-set; return the uniqueness result. This is the make-or-break proof for the v5 task: exactly
    one assignment must satisfy all constraints AND equal the expected unique assignment, and every named
    decoy assignment must violate at least one constraint. Uses only the HIDDEN constraint_graph metadata
    (never a visible file), so it proves a property of the design, not of any agent's behavior.
    """
    axes = cg["axes"]
    axis_names = list(axes.keys())
    domains = [axes[n] for n in axis_names]
    constraints = cg["constraints"]

    def satisfies(assign: dict) -> bool:
        for c in constraints:
            over = c["over"]
            allowed = {tuple(a) for a in c["allowed"]}
            if tuple(assign[o] for o in over) not in allowed:
                return False
        return True

    satisfying = []
    total = 0
    for combo in itertools.product(*domains):
        total += 1
        assign = dict(zip(axis_names, combo))
        if satisfies(assign):
            satisfying.append(assign)
    exp = cg["expected_unique_assignment"]
    exactly_one = len(satisfying) == 1
    return {
        "total_assignments": total,
        "satisfying_count": len(satisfying),
        "satisfying_assignments": satisfying,
        "exactly_one": exactly_one,
        "unique_matches_expected": bool(exactly_one and satisfying[0] == exp),
    }


def _handoff_truth(evidence_steps: int, expected_sha: str, stale_sha: str,
                   hazard_type: str | None = None, variant: str | None = None) -> str:
    a_clk, s_clk = _CLOCK_PAIRS[0]
    _is_sc = hazard_type == "scenario_corner_cross_source_conflict"
    _is_mc = hazard_type == "multi_conflict_partially_truthful_decoy"
    _is_cg = hazard_type == "constraint_graph_multi_source_recovery"
    _is_ab = hazard_type == "axis_binding_value_invention"
    _is_imp = hazard_type == "implicit_axis_binding"
    _is_srb = hazard_type == SRB_HAZARD
    _typed = _is_sc or _is_mc or _is_cg or _is_ab or _is_imp or _is_srb
    scenario = SC_AUTH_SCENARIO if _typed else SCENARIO
    corner = SC_AUTH_CORNER if _typed else CORNER
    truth = {
        "_comment": "Hidden oracle metadata for p14 workflow handoff. Used ONLY inside "
                    "grade_workflow.py; never seen by the agent.",
        "evidence_steps": evidence_steps,
        "top_module": TOP,
        "expected_netlist": "netlist_v2.v", "expected_revision": "v2",
        "expected_netlist_sha256": expected_sha,
        "stale_netlist": "netlist_v1.v", "stale_netlist_sha256": stale_sha,
        "expected_clock": a_clk, "stale_clock": s_clk,
        "scenario": scenario, "corner": corner, "library": "tiny.db",
        "required_ports": [a_clk, "din", "en", "dout"],
        "min_constrained_paths": 1, "clock_period_ns": PERIOD,
        "forbid_weakening": True,
        "manifest_netlist": "netlist_v2.v", "manifest_clock": a_clk,
    }
    if hazard_type == "cross_source_conflict":
        # Authority hierarchy (strict total order): the highest-authority source is the manifest; lower
        # sources must be repaired UP to it. Only emitted for hazard presets so the ordered-chain tasks'
        # truth file stays byte-identical to the committed p14 v1 tasks.
        truth["authority_source"] = "handoff_manifest.json"
        truth["authority_hierarchy"] = ["spec.md", "handoff_manifest.json", "flow_config.json",
                                        "evidence_manifest.json", "timing_report.rpt", "prev_signoff.log"]
        truth["hazard_type"] = hazard_type
        truth["stale_source_id"] = ["flow_config.json", "constraints.sdc", "timing_report.rpt",
                                    "evidence_manifest.json(claim)", "prev_signoff.log"]
        truth["non_authoritative_sources"] = ["prev_signoff.log", "timing_report.rpt(stale)",
                                              "evidence_manifest.json(claim)"]
        truth["invalidated_by"] = "input_hashes_mismatch_and_lower_than_manifest"
        truth["recovery_step_expected"] = ["fix_flow_config_to_v2", "fix_sdc_to_clk_main",
                                           "rerun_stage1", "rerun_stage2"]
    if _is_sc:
        # p14 v3: scenario/corner cross-source conflict. netlist/clock are ALREADY correct in the mutant;
        # the conflict is purely in scenario/corner provenance. Authority = manifest's slow/func; the
        # shipped flow_config selects the WRONG scenario/corner and the evidence/manifest claim slow/func
        # while actually being a test/typ run. Recovery = repair flow_config scenario->slow corner->func,
        # then rerun the chain. The oracle pins authority to the hidden re-run's ACTUAL scenario/corner
        # (ref.*), which a hand-edited manifest claim cannot forge.
        truth["authority_source"] = "handoff_manifest.json"
        truth["authority_hierarchy"] = ["spec.md", "handoff_manifest.json", "flow_config.json",
                                        "evidence_manifest.json", "timing_report.rpt",
                                        "prev_corner_signoff.log"]
        truth["hazard_type"] = hazard_type
        truth["expected_scenario"] = SC_AUTH_SCENARIO
        truth["expected_corner"] = SC_AUTH_CORNER
        truth["stale_scenario"] = SC_STALE_SCENARIO
        truth["stale_corner"] = SC_STALE_CORNER
        truth["netlist_clock_already_correct"] = True
        truth["stale_source_id"] = ["flow_config.json(scenario/corner)", "timing_report.rpt(corner)",
                                    "evidence_manifest.json(corner claim)", "prev_corner_signoff.log"]
        truth["non_authoritative_sources"] = ["prev_corner_signoff.log",
                                              "evidence_manifest.json(scenario/corner claim)"]
        truth["invalidated_by"] = "scenario_corner_mismatch_vs_manifest_authority"
        truth["recovery_step_expected"] = ["fix_flow_config_scenario_to_slow",
                                           "fix_flow_config_corner_to_func",
                                           "rerun_stage1", "rerun_stage2"]
    if _is_mc:
        # p14 v4: multi-conflict partially-truthful decoy. The global authority is the 4-tuple
        # (netlist_v2, clk_main, slow, func). Multiple public evidence sources are each LOCALLY plausible
        # and partially true but globally invalid; only the full global package + a fresh ordered chain
        # generated from it passes. The oracle enforces the full tuple via (a) the v3 scenario/corner
        # authority echecks (expected_scenario/corner, pinned to the hidden re-run) and (b) the new
        # forgery-resistant consumed-netlist/clock echecks (global_authority_tuple, pinned to flow_config
        # + applied_hidden.sdc), both folded into EVIDENCE_OK.
        truth["authority_source"] = "handoff_manifest.json"
        truth["authority_hierarchy"] = ["spec.md", "handoff_manifest.json", "flow_config.json",
                                        "evidence_manifest.json", "report_A_typ_test.rpt",
                                        "report_B_stale_netlist.rpt", "evidence_C_manifest.json",
                                        "prev_signoff.log"]
        truth["hazard_type"] = hazard_type
        truth["expected_scenario"] = SC_AUTH_SCENARIO
        truth["expected_corner"] = SC_AUTH_CORNER
        truth["stale_scenario"] = SC_STALE_SCENARIO
        truth["stale_corner"] = SC_STALE_CORNER
        truth["global_authority_tuple"] = ["netlist_v2.v", a_clk, SC_AUTH_SCENARIO, SC_AUTH_CORNER]
        truth["decoy_sources"] = [
            "report_A_typ_test.rpt(netlist_v2/clk_main right; scenario/corner wrong)",
            "report_B_stale_netlist.rpt(scenario/corner right; netlist_v1 stale)",
            "evidence_C_manifest.json(fresh digest/upstream chain; semantically wrong package)",
            "prev_signoff.log(recent, plausible, non-authoritative)"]
        truth["partial_truth_sources"] = [
            "report_A_typ_test.rpt(partial: design right, corner wrong)",
            "report_B_stale_netlist.rpt(partial: corner right, design stale)",
            "evidence_C_manifest.json(partial: chain syntactically valid, package semantically wrong)"]
        truth["non_authoritative_sources"] = ["prev_signoff.log", "report_A_typ_test.rpt",
                                              "report_B_stale_netlist.rpt", "evidence_C_manifest.json"]
        truth["invalidated_by"] = "no_single_local_source_is_globally_authority_consistent"
        truth["recovery_step_expected"] = ["fix_flow_config_netlist_to_v2",
                                           "fix_flow_config_scenario_to_slow",
                                           "fix_flow_config_corner_to_func",
                                           "rerun_stage1", "rerun_stage2"]
    if _is_cg:
        # p14 v5: constraint-graph multi-source recovery. Runtime ENFORCEMENT reuses the proven v4 tuple
        # machinery -- the unique global assignment is the SAME (netlist_v2, clk_main, slow, func), pinned
        # by global_authority_tuple + expected_scenario/corner echecks folded into EVIDENCE_OK, so every
        # partial/single-axis/decoy recovery already fails. What is NEW is the DISCOVERABILITY: no single
        # visible file states the tuple. It is recoverable only by intersecting independent constraints:
        #   C1 netlist family   -- handoff_manifest allows only the v2.x family + acc_stage interface
        #   C2 clock coverage   -- only clk_main yields intended-clock coverage on netlist_v2 (clk_old = 0)
        #   C3 scenario/corner  -- spec's joint-validity table + signoff-mode rule pin exactly (slow, func)
        #   C4 report provenance/ C5 upstream digest / C6 stage dependency -- fresh ordered chain (runtime)
        # The constraint_graph block below is machine-checkable data used by the offline uniqueness
        # enumeration and by the constraint-graph diagnostic markers; it does NOT change enforcement.
        truth["authority_source"] = "handoff_manifest.json + spec.md joint-validity table (constraint graph)"
        truth["authority_hierarchy"] = ["spec.md", "handoff_manifest.json", "flow_config.json",
                                        "evidence_manifest.json", "report_A_scenario_corner.rpt",
                                        "report_B_stale_netlist.rpt", "report_C_wrong_clock.rpt",
                                        "evidence_D_manifest.json", "prev_signoff.log"]
        truth["hazard_type"] = hazard_type
        truth["expected_scenario"] = SC_AUTH_SCENARIO
        truth["expected_corner"] = SC_AUTH_CORNER
        truth["stale_scenario"] = SC_STALE_SCENARIO
        truth["stale_corner"] = SC_STALE_CORNER
        # reuse the v4 forgery-resistant consumed-netlist/clock enforcement (proven to reject every decoy)
        truth["global_authority_tuple"] = ["netlist_v2.v", a_clk, SC_AUTH_SCENARIO, SC_AUTH_CORNER]
        # machine-checkable constraint graph (HIDDEN; never in a visible file). Axis domains + per-constraint
        # allowed-sets; the offline uniqueness enumeration re-derives the unique assignment from THESE.
        truth["constraint_graph"] = {
            "axes": {
                "netlist": ["netlist_v1.v", "netlist_v2.v"],
                "clock": [a_clk, s_clk],
                "scenario": ["slow", "typ", "fast"],
                "corner": ["func", "test", "lowpower"],
            },
            "constraints": [
                {"id": "C1", "name": "netlist_family", "over": ["netlist"],
                 "allowed": [["netlist_v2.v"]],
                 "source": "handoff_manifest.json allows only the v2.x family + acc_stage interface"},
                {"id": "C2", "name": "clock_coverage", "over": ["clock"],
                 "allowed": [[a_clk]],
                 "source": "only clk_main yields intended-clock coverage on netlist_v2 (clk_old=0 paths)"},
                {"id": "C3", "name": "scenario_corner_signoff_pair", "over": ["scenario", "corner"],
                 "allowed": [["slow", "func"]],
                 "source": "spec.md joint-validity table + signoff-mode rule pin exactly (slow, func)"},
            ],
            "expected_unique_assignment": {
                "netlist": "netlist_v2.v", "clock": a_clk,
                "scenario": SC_AUTH_SCENARIO, "corner": SC_AUTH_CORNER},
            "decoy_violates": {
                "report_A_scenario_corner.rpt": "C3 (v2/clk_main right; scenario/corner = typ/test)",
                "report_B_stale_netlist.rpt": "C1 (slow/func right; netlist stale v1)",
                "report_C_wrong_clock.rpt": "C2 (v2/slow right; clock = clk_old, no coverage)",
                "evidence_D_manifest.json": "C1/C6 (valid-looking digest; depends on invalidated v1 stage)",
            },
            # filled in by the offline uniqueness enumeration at generation time (validate_uniqueness)
            "uniqueness": None,
        }
        truth["constraint_graph"]["uniqueness"] = enumerate_constraint_graph(truth["constraint_graph"])
        truth["decoy_sources"] = [
            "report_A_scenario_corner.rpt(netlist_v2/clk_main right; scenario/corner wrong -> C3)",
            "report_B_stale_netlist.rpt(scenario/corner right; netlist_v1 stale -> C1)",
            "report_C_wrong_clock.rpt(netlist_v2/scenario right; clock clk_old wrong -> C2)",
            "evidence_D_manifest.json(fresh-looking digest; invalidated prerequisite stage -> C1/C6)",
            "prev_signoff.log(recent, plausible, non-authoritative)"]
        truth["pairwise_valid_but_global_invalid_sources"] = [
            "report_A_scenario_corner.rpt", "report_B_stale_netlist.rpt",
            "report_C_wrong_clock.rpt", "evidence_D_manifest.json"]
        truth["non_authoritative_sources"] = ["prev_signoff.log", "report_A_scenario_corner.rpt",
                                              "report_B_stale_netlist.rpt", "report_C_wrong_clock.rpt",
                                              "evidence_D_manifest.json"]
        truth["invalidated_by"] = "no_single_source_satisfies_all_constraints_only_their_intersection"
        truth["recovery_step_expected"] = ["infer_unique_assignment_from_C1_C2_C3",
                                           "fix_flow_config_netlist_to_v2",
                                           "fix_flow_config_scenario_to_slow",
                                           "fix_flow_config_corner_to_func",
                                           "rerun_stage1", "rerun_stage2"]
    if _is_ab:
        # p14 v6: axis-binding / value-invention stress. Same unique global assignment as v5
        # (netlist_v2/clk_main/slow/func), reused deliberately -- the difficulty is BINDING, not a different
        # answer. NEW vs v5: typed axes with closed PUBLISHED vocabularies (axis_schema.json), and the
        # mutant ships a value-SWAP (corner value 'func' in the scenario slot, scenario value 'typ' in the
        # corner slot -- the exact DeepSeek k=3 failure mode on 0006). Because the report body is corner-
        # independent on the single tiny.db, a correct netlist+clock package PrimeTime-signs-off GREEN even
        # when scenario/corner are swapped or a PVT label is substituted, so the type-membership echecks
        # (gated on axis_schema, folded into EVIDENCE_OK) are what floor a signoff-green-but-mis-typed
        # package below pass. The constraint enumeration below includes TRAP values in its axis domains (a
        # corner value + a PVT label on the scenario axis; a scenario value + a PVT label on the corner axis;
        # a generic 'clk' alias on the clock axis) so the offline enumeration PROVES that swapped-axis /
        # PVT-substitution / wrong-clock-alias assignments violate the typed constraints, and exactly one
        # typed assignment satisfies all of them.
        truth["authority_source"] = "handoff_manifest.json (family) + spec.md typed-axis joint-validity + axis_schema.json (vocabulary)"
        truth["authority_hierarchy"] = ["spec.md", "handoff_manifest.json", "axis_schema.json", "flow_config.json",
                                        "evidence_manifest.json", "report_A_value_swap.rpt",
                                        "report_B_pvt_corner.rpt", "report_C_wrong_clock.rpt",
                                        "evidence_D_typed_mismatch.json", "prev_signoff.log"]
        truth["hazard_type"] = hazard_type
        truth["expected_scenario"] = SC_AUTH_SCENARIO
        truth["expected_corner"] = SC_AUTH_CORNER
        truth["stale_scenario"] = AB_STALE_SCENARIO
        truth["stale_corner"] = AB_STALE_CORNER
        # reuse the proven v4/v5 forgery-resistant consumed-netlist/clock enforcement
        truth["global_authority_tuple"] = ["netlist_v2.v", a_clk, SC_AUTH_SCENARIO, SC_AUTH_CORNER]
        # machine-checkable typed constraint graph (HIDDEN; never in a visible file). The axis domains include
        # trap values so the offline uniqueness enumeration re-derives the unique TYPED assignment AND proves
        # the typed-binding failures; typed_axes (clean, no traps) is what the visible axis_schema.json publishes.
        truth["axis_schema"] = {
            "typed_axes": AB_TYPED_AXES,
            "pvt_label_mapping": AB_PVT_MAPPING,
            "type_rules": [
                "scenario_axis values may occupy ONLY the scenario field",
                "corner_axis values may occupy ONLY the corner field",
                "a pvt_label_axis token is descriptive metadata mapping to a (scenario, corner) pair; "
                "it is never a valid scenario or corner value and may occupy only a pvt_label field",
                "clock_axis requires exact identity (clk_main); a generic/aliased name is rejected",
            ],
            "axes": {
                "netlist": ["netlist_v1.v", "netlist_v2.v"],
                "clock": [a_clk, s_clk, "clk"],
                "scenario": ["slow", "typ", "fast", "func", "test", "lowpower", "slow_1.0V_125C"],
                "corner": ["func", "test", "lowpower", "slow", "typ", "fast", "slow_1.0V_125C"],
            },
            "constraints": [
                {"id": "C1", "name": "netlist_family", "over": ["netlist"],
                 "allowed": [["netlist_v2.v"]],
                 "source": "handoff_manifest.json allows only the v2.x family + acc_stage interface"},
                {"id": "C2", "name": "clock_identity", "over": ["clock"],
                 "allowed": [[a_clk]],
                 "source": "clock must be the exact intended clock clk_main; clk_old / generic 'clk' alias rejected"},
                {"id": "C3", "name": "scenario_typed", "over": ["scenario"],
                 "allowed": [["slow"], ["typ"], ["fast"]],
                 "source": "scenario field must be a scenario_axis member (slow/typ/fast); a corner value or "
                           "PVT label in the scenario slot is a type error"},
                {"id": "C4", "name": "corner_typed", "over": ["corner"],
                 "allowed": [["func"], ["test"], ["lowpower"]],
                 "source": "corner field must be a corner_axis member (func/test/lowpower); a scenario value or "
                           "PVT label in the corner slot is a type error"},
                {"id": "C5", "name": "scenario_corner_signoff_pair", "over": ["scenario", "corner"],
                 "allowed": [["slow", "func"]],
                 "source": "spec.md signoff-mode joint-validity table pins exactly (slow, func)"},
            ],
            "expected_unique_assignment": {
                "netlist": "netlist_v2.v", "clock": a_clk,
                "scenario": SC_AUTH_SCENARIO, "corner": SC_AUTH_CORNER},
            "decoy_violates": {
                "report_A_value_swap.rpt": "C3+C4 (v2/clk_main right; scenario=func/corner=typ is a value-swap -- "
                                           "corner value in scenario slot, scenario value in corner slot)",
                "report_B_pvt_corner.rpt": "C4 (v2/clk_main/slow right; corner=slow_1.0V_125C is a PVT label, "
                                           "not a corner_axis value)",
                "report_C_wrong_clock.rpt": "C2 (v2/slow/func right; clock=clk is a generic alias, not clk_main)",
                "evidence_D_typed_mismatch.json": "C3+C4 (syntactically valid chain; scenario/corner fields swapped inside)",
            },
            "uniqueness": None,
        }
        truth["axis_schema"]["uniqueness"] = enumerate_constraint_graph(truth["axis_schema"])
        truth["decoy_sources"] = [
            "report_A_value_swap.rpt(netlist_v2/clk_main right; scenario/corner swapped func/typ -> C3+C4)",
            "report_B_pvt_corner.rpt(netlist_v2/clk_main/slow right; corner=slow_1.0V_125C PVT label -> C4)",
            "report_C_wrong_clock.rpt(netlist_v2/slow/func right; clock=clk generic alias -> C2)",
            "evidence_D_typed_mismatch.json(valid-looking chain; scenario/corner fields swapped -> C3+C4)",
            "prev_signoff.log(recent, plausible, non-authoritative)"]
        truth["pairwise_valid_but_global_invalid_sources"] = [
            "report_A_value_swap.rpt", "report_B_pvt_corner.rpt",
            "report_C_wrong_clock.rpt", "evidence_D_typed_mismatch.json"]
        truth["non_authoritative_sources"] = ["prev_signoff.log", "report_A_value_swap.rpt",
                                              "report_B_pvt_corner.rpt", "report_C_wrong_clock.rpt",
                                              "evidence_D_typed_mismatch.json"]
        truth["invalidated_by"] = "no_single_source_satisfies_all_typed_constraints_only_their_intersection"
        truth["recovery_step_expected"] = ["infer_unique_typed_assignment_from_C1_C2_C3_C4_C5",
                                           "bind_scenario_to_scenario_axis_value",
                                           "bind_corner_to_corner_axis_value",
                                           "fix_flow_config_netlist_to_v2",
                                           "fix_flow_config_scenario_to_slow",
                                           "fix_flow_config_corner_to_func",
                                           "rerun_stage1", "rerun_stage2"]
    if _is_imp:
        # p14 v7: implicit typed-axis binding. Same unique typed assignment as v6 (netlist_v2/clk_main/slow/
        # func), reusing the v6 typed-binding oracle (the axis_schema hidden block + the grader's axis_schema
        # gated echecks). The DIFFERENCE from v6 is the DISCOVERABILITY: NO axis_schema.json is shipped. The
        # visible reports/spec use NON-CANONICAL labels (op_point / mode / "operating point" / "signoff
        # mode"), so the agent must INFER axis membership from PVT notation + spec terminology + cross-source
        # consistency + coverage facts -- a typed-INFERENCE task, not a vocabulary-LOOKUP task (the v6
        # collapse). flow_config keeps canonical scenario/corner fields (so the existing grader echecks work
        # unchanged); the load-bearing inference is mapping the non-canonical report terms to those fields.
        truth["authority_source"] = ("inferred from evidence/provenance: handoff_manifest.json (family) + "
                                     "spec.md partial terminology + coverage facts + PVT-notation parsing")
        truth["authority_hierarchy"] = ["spec.md", "handoff_manifest.json", "glossary.md", "flow_config.json",
                                        "evidence_manifest.json", "report_A_context_swap.rpt",
                                        "report_B_context_stale.rpt", "report_C_context_pvt.rpt",
                                        "evidence_D_context_mismatch.json", "public_check_summary.json",
                                        "prev_signoff.log"]
        truth["hazard_type"] = hazard_type
        truth["expected_scenario"] = SC_AUTH_SCENARIO
        truth["expected_corner"] = SC_AUTH_CORNER
        truth["stale_scenario"] = AB_STALE_SCENARIO   # the value-swap mutant (corner value in scenario slot)
        truth["stale_corner"] = AB_STALE_CORNER
        truth["global_authority_tuple"] = ["netlist_v2.v", a_clk, SC_AUTH_SCENARIO, SC_AUTH_CORNER]
        # Reuse the v6 typed constraint graph (HIDDEN; never shipped). Same axes/constraints/uniqueness; the
        # v7 difference is purely that typed_axes is NOT published (no axis_schema.json) -- membership must be
        # INFERRED. The grader's axis_schema gated block enforces typed binding identically to v6.
        truth["axis_schema"] = {
            "typed_axes": AB_TYPED_AXES,
            "pvt_label_mapping": AB_PVT_MAPPING,
            "type_rules": [
                "scenario_axis values may occupy ONLY the scenario field",
                "corner_axis values may occupy ONLY the corner field",
                "a pvt_label_axis token is descriptive metadata mapping to a (scenario, corner) pair; "
                "it is never a valid scenario or corner value",
                "clock_axis requires exact identity (clk_main); a generic/aliased name is rejected",
            ],
            "membership_visibility": "IMPLICIT -- not published in any visible file; inferred from PVT "
                                     "notation, spec terminology, coverage facts, and cross-source consistency",
            "axes": {
                "netlist": ["netlist_v1.v", "netlist_v2.v"],
                "clock": [a_clk, s_clk, "clk"],
                "scenario": ["slow", "typ", "fast", "func", "test", "lowpower", "slow_1.0V_125C"],
                "corner": ["func", "test", "lowpower", "slow", "typ", "fast", "slow_1.0V_125C"],
            },
            "constraints": [
                {"id": "C1", "name": "netlist_family", "over": ["netlist"],
                 "allowed": [["netlist_v2.v"]],
                 "source": "handoff_manifest.json family + acc_stage interface"},
                {"id": "C2", "name": "clock_identity", "over": ["clock"],
                 "allowed": [[a_clk]],
                 "source": "the only clock with non-zero intended-clock coverage on netlist_v2"},
                {"id": "C3", "name": "scenario_typed", "over": ["scenario"],
                 "allowed": [["slow"], ["typ"], ["fast"]],
                 "source": "scenario field must be a scenario_axis member (inferred from op_point context + "
                           "PVT process token); a corner value or PVT label is a type error"},
                {"id": "C4", "name": "corner_typed", "over": ["corner"],
                 "allowed": [["func"], ["test"], ["lowpower"]],
                 "source": "corner field must be a corner_axis member (inferred from mode context); a "
                           "scenario value or PVT label is a type error"},
                {"id": "C5", "name": "scenario_corner_signoff_pair", "over": ["scenario", "corner"],
                 "allowed": [["slow", "func"]],
                 "source": "spec.md 'slow operating point in functional signoff mode'"},
            ],
            "expected_unique_assignment": {
                "netlist": "netlist_v2.v", "clock": a_clk,
                "scenario": SC_AUTH_SCENARIO, "corner": SC_AUTH_CORNER},
            "decoy_violates": {
                "report_A_context_swap.rpt": "C3+C4 (right netlist/clock; op_point/mode swapped)",
                "report_B_context_stale.rpt": "C1 (op_point/mode correct; netlist stale v1)",
                "report_C_context_pvt.rpt": "C4 (PVT label slow_1.0V_125C in mode field)",
                "evidence_D_context_mismatch.json": "C3+C4 (valid digest; op_point/mode swapped inside)",
            },
            "uniqueness": None,
        }
        truth["axis_schema"]["uniqueness"] = enumerate_constraint_graph(truth["axis_schema"])
        truth["decoy_sources"] = [
            "report_A_context_swap.rpt(netlist_v2/clk_main right; op_point/mode swapped -> C3+C4)",
            "report_B_context_stale.rpt(op_point/mode correct; netlist_v1 stale -> C1)",
            "report_C_context_pvt.rpt(op_point correct; mode=slow_1.0V_125C PVT label -> C4)",
            "evidence_D_context_mismatch.json(valid-looking chain; op_point/mode swapped -> C3+C4)",
            "prev_signoff.log(recent, plausible, non-authoritative)"]
        truth["pairwise_valid_but_global_invalid_sources"] = [
            "report_A_context_swap.rpt", "report_B_context_stale.rpt",
            "report_C_context_pvt.rpt", "evidence_D_context_mismatch.json"]
        truth["non_authoritative_sources"] = ["prev_signoff.log", "report_A_context_swap.rpt",
                                              "report_B_context_stale.rpt", "report_C_context_pvt.rpt",
                                              "evidence_D_context_mismatch.json"]
        truth["invalidated_by"] = "no_single_source_satisfies_all_typed_constraints_only_their_intersection"
        truth["recovery_step_expected"] = ["infer_axis_membership_from_evidence",
                                           "infer_unique_typed_assignment_from_C1_C2_C3_C4_C5",
                                           "fix_flow_config_netlist_to_v2",
                                           "fix_flow_config_scenario_to_slow",
                                           "fix_flow_config_corner_to_func",
                                           "rerun_stage1", "rerun_stage2"]
    if _is_srb:
        # p14 v8: semantic-role-binding REPRODUCTION (the controlled pair). The hidden truth + typed-binding
        # grader are REUSED byte-identically from v6/v7 (same unique typed assignment
        # netlist_v2/clk_main/slow/func, same 294->1 uniqueness, same value-swap mutant scenario=func/corner=
        # typ -- the exact DeepSeek 0006 failure mode). The TWO VARIANTS differ ONLY in the visible clarity
        # bundle (report-label semantics + inference anchors), which the grader never reads for these
        # echecks. So grading is identical across a/b; only presentation difficulty differs.
        #   variant "ambiguous" (0009a): overloaded op_point/mode labels + NO anchors -> reproduce 0006.
        #   variant "clear_control" (0009b): canonical scenario/corner labels + anchors -> negative control.
        truth["authority_source"] = ("inferred from evidence/provenance (variant=%s): handoff_manifest "
                                     "(family) + report intersection + (ambiguous: no anchors; clear: "
                                     "glossary + public_check_summary)" % variant)
        truth["authority_hierarchy"] = ["spec.md", "handoff_manifest.json", "flow_config.json",
                                        "evidence_manifest.json", "report_A_role_swap.rpt",
                                        "report_B_role_stale.rpt", "report_C_role_pvt.rpt",
                                        "evidence_D_role_mismatch.json", "prev_signoff.log"]
        truth["hazard_type"] = hazard_type
        truth["variant"] = variant
        truth["expected_scenario"] = SC_AUTH_SCENARIO
        truth["expected_corner"] = SC_AUTH_CORNER
        truth["stale_scenario"] = AB_STALE_SCENARIO   # the value-swap mutant (corner value in scenario slot)
        truth["stale_corner"] = AB_STALE_CORNER
        truth["global_authority_tuple"] = ["netlist_v2.v", a_clk, SC_AUTH_SCENARIO, SC_AUTH_CORNER]
        # the semantic-role mapping the AMBIGUOUS variant forces the agent to infer (the clear variant uses
        # canonical labels so the mapping is identity). Recorded here as hidden documentation + for tests.
        truth["semantic_role_mapping"] = (dict(SRB_ROLE_MAPPING) if variant == SRB_AMBIGUOUS
                                          else dict(SRB_CLEAR_LABELS))
        # report-role labels shipped per variant (what physical field name each report uses for each axis)
        truth["report_role_labels"] = (dict(SRB_AMBIGUOUS_LABELS) if variant == SRB_AMBIGUOUS
                                       else dict(SRB_CLEAR_LABELS))
        # the locally-plausible WRONG values embedded inside the genuine-looking report bodies (the 0006
        # body-embedding mechanism): the swapped pair func/typ appears inside report_A/report_C bodies.
        truth["decoy_embedded_values"] = {
            "report_A_role_swap.rpt": {"scenario_slot": AB_STALE_SCENARIO, "corner_slot": AB_STALE_CORNER},
            "report_C_role_pvt.rpt": {"scenario_slot": SC_AUTH_SCENARIO, "corner_slot": "slow_1.0V_125C"},
        }
        # Reuse the v6/v7 typed constraint graph (HIDDEN; never shipped). Same axes/constraints/uniqueness;
        # the variant difference is purely VISIBLE (overloaded vs canonical labels; anchors absent vs
        # present). The grader's axis_schema gated block enforces typed binding identically to v6/v7.
        truth["axis_schema"] = {
            "typed_axes": AB_TYPED_AXES,
            "pvt_label_mapping": AB_PVT_MAPPING,
            "type_rules": [
                "scenario_axis values may occupy ONLY the scenario field",
                "corner_axis values may occupy ONLY the corner field",
                "a pvt_label_axis token is descriptive metadata mapping to a (scenario, corner) pair; "
                "it is never a valid scenario or corner value",
                "clock_axis requires exact identity (clk_main); a generic/aliased name is rejected",
            ],
            "membership_visibility": ("IMPLICIT, variant=%s -- ambiguous: inferred from report intersection "
                                      "with NO glossary/summary anchor; clear: canonical labels + anchors" % variant),
            "axes": {
                "netlist": ["netlist_v1.v", "netlist_v2.v"],
                "clock": [a_clk, s_clk, "clk"],
                "scenario": ["slow", "typ", "fast", "func", "test", "lowpower", "slow_1.0V_125C"],
                "corner": ["func", "test", "lowpower", "slow", "typ", "fast", "slow_1.0V_125C"],
            },
            "constraints": [
                {"id": "C1", "name": "netlist_family", "over": ["netlist"],
                 "allowed": [["netlist_v2.v"]],
                 "source": "handoff_manifest.json family + acc_stage interface"},
                {"id": "C2", "name": "clock_identity", "over": ["clock"],
                 "allowed": [[a_clk]],
                 "source": "the only clock with non-zero intended-clock coverage on netlist_v2"},
                {"id": "C3", "name": "scenario_typed", "over": ["scenario"],
                 "allowed": [["slow"], ["typ"], ["fast"]],
                 "source": "scenario field must be a scenario_axis member; a corner value or PVT label "
                           "in the scenario slot is a type error"},
                {"id": "C4", "name": "corner_typed", "over": ["corner"],
                 "allowed": [["func"], ["test"], ["lowpower"]],
                 "source": "corner field must be a corner_axis member; a scenario value or PVT label "
                           "in the corner slot is a type error"},
                {"id": "C5", "name": "scenario_corner_signoff_pair", "over": ["scenario", "corner"],
                 "allowed": [["slow", "func"]],
                 "source": "the unique signoff pair recovered by intersecting the (partially-truthful) "
                           "report sources"},
            ],
            "expected_unique_assignment": {
                "netlist": "netlist_v2.v", "clock": a_clk,
                "scenario": SC_AUTH_SCENARIO, "corner": SC_AUTH_CORNER},
            "decoy_violates": {
                "report_A_role_swap.rpt": "C3+C4 (right netlist/clock; the role fields are SWAPPED -- a "
                                          "corner value in the scenario role, a scenario value in the corner role)",
                "report_B_role_stale.rpt": "C1 (correct role fields; netlist stale v1)",
                "report_C_role_pvt.rpt": "C2+C4 (right netlist/scenario; corner is a PVT label; clock alias 'clk')",
                "evidence_D_role_mismatch.json": "C3+C4 (valid digest; role fields swapped inside)",
            },
            "uniqueness": None,
        }
        truth["axis_schema"]["uniqueness"] = enumerate_constraint_graph(truth["axis_schema"])
        truth["decoy_sources"] = [
            "report_A_role_swap.rpt(netlist_v2/clk_main right; role fields swapped func/typ -> C3+C4)",
            "report_B_role_stale.rpt(correct role fields slow/func; netlist_v1 stale -> C1)",
            "report_C_role_pvt.rpt(netlist_v2/slow right; corner=PVT label slow_1.0V_125C + clock alias clk -> C2+C4)",
            "evidence_D_role_mismatch.json(valid-looking chain; role fields swapped -> C3+C4)",
            "prev_signoff.log(recent, plausible, non-authoritative)"]
        truth["pairwise_valid_but_global_invalid_sources"] = [
            "report_A_role_swap.rpt", "report_B_role_stale.rpt",
            "report_C_role_pvt.rpt", "evidence_D_role_mismatch.json"]
        truth["non_authoritative_sources"] = ["prev_signoff.log", "report_A_role_swap.rpt",
                                              "report_B_role_stale.rpt", "report_C_role_pvt.rpt",
                                              "evidence_D_role_mismatch.json"]
        truth["invalidated_by"] = "no_single_source_satisfies_all_typed_constraints_only_their_intersection"
        truth["recovery_step_expected"] = ["resolve_semantic_role_binding_from_report_intersection",
                                           "infer_unique_typed_assignment_from_C1_C2_C3_C4_C5",
                                           "fix_flow_config_netlist_to_v2",
                                           "fix_flow_config_scenario_to_slow",
                                           "fix_flow_config_corner_to_func",
                                           "rerun_stage1", "rerun_stage2"]
    return json.dumps(truth, indent=2) + "\n"


def _metadata(task_id: str, seed: int, evidence_steps: int,
              hazard_type: str | None = None, hint_level: int = 1, variant: str | None = None) -> dict:
    visible = ["spec.md", "handoff_manifest.json", "flow_config.json", "constraints.sdc",
               "netlist_v1.v", "netlist_v2.v", "pt_signoff.tcl",
               "run_evidence_stage1.sh", "gen_evidence_stage1.py", "evidence_signoff.tcl",
               "timing_report.rpt", "evidence_manifest.json",
               "tiny.lib", "tiny.db", "run_public.sh", "run_public.tcl"]
    editable = ["flow_config.json", "constraints.sdc", "timing_report.rpt", "evidence_manifest.json"]
    forbidden = ["spec.md", "handoff_manifest.json", "netlist_v1.v", "netlist_v2.v", "pt_signoff.tcl",
                 "run_evidence_stage1.sh", "gen_evidence_stage1.py", "evidence_signoff.tcl",
                 "tiny.lib", "tiny.db", "run_public.sh", "run_public.tcl"]
    hidden = ["run_hidden.sh", "run_launder.tcl", "run_coverage.tcl", "run_signoff.tcl",
              "regen_reference.sh", "gen_evidence_stage1_trusted.py", "evidence_signoff_trusted.tcl",
              "grade_workflow.py", "handoff_truth.json"]
    weights = {"signoff": 0.15, "final_state": 0.20, "evidence_generation": 0.25,
               "stage_chain": 0.15, "provenance": 0.15, "explanation": 0.10}
    run_command = "bash run_public.sh && bash run_hidden.sh"
    if evidence_steps == 2:
        for f in ("run_evidence_stage2.sh", "gen_evidence_stage2.py", "evidence_signoff_stage2.tcl",
                  "stage2_summary.json"):
            visible.append(f)
        editable.append("stage2_summary.json")
        for f in ("run_evidence_stage2.sh", "gen_evidence_stage2.py", "evidence_signoff_stage2.tcl"):
            forbidden.append(f)
        for f in ("gen_evidence_stage2_trusted.py", "evidence_signoff_stage2_trusted.tcl"):
            hidden.append(f)
    if hazard_type == "cross_source_conflict":
        # the non-authoritative decoy log is a visible, read-only, forbidden-to-edit distractor
        visible.append("prev_signoff.log")
        forbidden.append("prev_signoff.log")
        # add the two hazard axes; re-balance so weights still sum to 1.0. The two new gates fold into
        # the EVIDENCE master gate in the oracle, so wrong-authority / partial-recovery stay <0.5.
        weights = {"signoff": 0.10, "final_state": 0.15, "evidence_generation": 0.25,
                   "stage_chain": 0.10, "provenance": 0.10, "authority_consistency": 0.10,
                   "hazard_recovery": 0.10, "explanation": 0.10}
    if hazard_type == "scenario_corner_cross_source_conflict":
        # v3: scenario/corner provenance decoy. Same weight layout + hazard axes as the v2 preset; the
        # scenario/corner authority folds into EVIDENCE so wrong-corner states stay <0.5.
        visible.append("prev_corner_signoff.log")
        forbidden.append("prev_corner_signoff.log")
        weights = {"signoff": 0.10, "final_state": 0.15, "evidence_generation": 0.25,
                   "stage_chain": 0.10, "provenance": 0.10, "authority_consistency": 0.10,
                   "hazard_recovery": 0.10, "explanation": 0.10}
    if hazard_type == "multi_conflict_partially_truthful_decoy":
        # v4: multi-conflict partially-truthful decoys. Four visible, read-only, forbidden distractors,
        # each locally plausible but globally invalid. Same weight layout + hazard axes as v2/v3; the full
        # global-authority tuple (netlist_v2/clk_main/slow/func) + multi-conflict recovery fold into
        # EVIDENCE / HAZARD_RECOVERY so every partial-truth recovery stays <0.5.
        for f in ("report_A_typ_test.rpt", "report_B_stale_netlist.rpt", "evidence_C_manifest.json",
                  "prev_signoff.log"):
            visible.append(f)
            forbidden.append(f)
        weights = {"signoff": 0.10, "final_state": 0.15, "evidence_generation": 0.25,
                   "stage_chain": 0.10, "provenance": 0.10, "authority_consistency": 0.10,
                   "hazard_recovery": 0.10, "explanation": 0.10}
    if hazard_type == "constraint_graph_multi_source_recovery":
        # v5: constraint-graph multi-source recovery. Five visible, read-only, forbidden distractors,
        # each locally/pairwise plausible but jointly invalid; no single source reveals the full target
        # tuple (manifest gives netlist FAMILY only; spec gives a joint-validity table; clock is pinned
        # by coverage). Same weight layout + hazard axes as v2/v3/v4; the constraint-graph markers fold
        # into EVIDENCE / HAZARD_RECOVERY (reusing the proven global_authority_tuple enforcement) so every
        # partial / single-axis / pairwise decoy stays <0.5.
        for f in ("report_A_scenario_corner.rpt", "report_B_stale_netlist.rpt", "report_C_wrong_clock.rpt",
                  "evidence_D_manifest.json", "prev_signoff.log"):
            visible.append(f)
            forbidden.append(f)
        weights = {"signoff": 0.10, "final_state": 0.15, "evidence_generation": 0.25,
                   "stage_chain": 0.10, "provenance": 0.10, "authority_consistency": 0.10,
                   "hazard_recovery": 0.10, "explanation": 0.10}
    if hazard_type == "axis_binding_value_invention":
        # v6: axis-binding / value-invention stress. The typed-axis vocabulary is PUBLISHED in
        # axis_schema.json (visible + forbidden to edit) because the challenge is BINDING, not vocabulary
        # hiding. Five visible, read-only, forbidden distractors, each locally plausible but globally
        # invalid on a TYPED axis (value-swap / PVT substitution / wrong clock alias / typed-field mismatch).
        # Same weight layout + hazard axes as v2-v5; the typed-membership echecks fold into EVIDENCE /
        # HAZARD_RECOVERY (reusing the proven global_authority_tuple enforcement) so every signoff-green-but-
        # mis-typed / partial / single-axis / pairwise decoy stays <0.5.
        for f in ("axis_schema.json", "report_A_value_swap.rpt", "report_B_pvt_corner.rpt",
                  "report_C_wrong_clock.rpt", "evidence_D_typed_mismatch.json", "prev_signoff.log"):
            visible.append(f)
            forbidden.append(f)
        weights = {"signoff": 0.10, "final_state": 0.15, "evidence_generation": 0.25,
                   "stage_chain": 0.10, "provenance": 0.10, "authority_consistency": 0.10,
                   "hazard_recovery": 0.10, "explanation": 0.10}
    if hazard_type == "implicit_axis_binding":
        # v7: implicit typed-axis binding. NO axis_schema.json is shipped -- the typed-binding oracle is
        # reused (the hidden axis_schema truth + the grader's axis_schema gated block) but axis membership is
        # INFERRED from non-canonical report labels (op_point/mode), spec terminology, PVT notation, and
        # coverage facts. Visible read-only forbidden distractors use non-canonical context labels; a glossary
        # (examples only) + a public pairwise consistency summary are added. Same weight layout as v2-v6; the
        # typed-membership echecks fold into EVIDENCE / HAZARD_RECOVERY so every mis-typed / partial / pairwise
        # decoy stays <0.5 even when PT signoff is green.
        for f in ("report_A_context_swap.rpt", "report_B_context_stale.rpt",
                  "report_C_context_pvt.rpt", "evidence_D_context_mismatch.json",
                  "public_check_summary.json", "glossary.md", "prev_signoff.log"):
            visible.append(f)
            forbidden.append(f)
        weights = {"signoff": 0.10, "final_state": 0.15, "evidence_generation": 0.25,
                   "stage_chain": 0.10, "provenance": 0.10, "authority_consistency": 0.10,
                   "hazard_recovery": 0.10, "explanation": 0.10}
    if hazard_type == SRB_HAZARD:
        # v8 semantic-role-binding REPRODUCTION. Same weight layout + hazard axes as v2-v7; the typed-binding
        # echecks fold into EVIDENCE / HAZARD_RECOVERY (reused byte-identically from v6/v7) so every
        # signoff-green-but-mis-typed / role-mismatched / partial / pairwise decoy stays <0.5. The variant
        # controls the visible clarity bundle: the ambiguous variant ships NO glossary/summary anchors; the
        # clear-control variant ships both (the negative control).
        _amb = variant == SRB_AMBIGUOUS
        _files = ["report_A_role_swap.rpt", "report_B_role_stale.rpt",
                  "report_C_role_pvt.rpt", "evidence_D_role_mismatch.json", "prev_signoff.log"]
        if not _amb:
            _files += ["public_check_summary.json", "glossary.md"]
        for f in _files:
            visible.append(f)
            forbidden.append(f)
        weights = {"signoff": 0.10, "final_state": 0.15, "evidence_generation": 0.25,
                   "stage_chain": 0.10, "provenance": 0.10, "authority_consistency": 0.10,
                   "hazard_recovery": 0.10, "explanation": 0.10}
    forbidden += hidden
    gen_params = {"mechanism": "workflow_multistage_evidence_chain_handoff",
                  "evidence_steps": evidence_steps,
                  "expected_netlist": "netlist_v2.v", "expected_clock": _CLOCK_PAIRS[0][0],
                  "stale_netlist": "netlist_v1.v", "stale_clock": _CLOCK_PAIRS[0][1],
                  "scenario_corner": "%s/%s" % (SCENARIO, CORNER),
                  "pass_gate": "SIGNOFF_OK AND EVIDENCE_OK AND FINAL_STATE_OK AND "
                               "STAGE_CHAIN_OK AND PROVENANCE_OK AND no forbidden edits"}
    err_cat = "workflow_handoff_stale_evidence_chain_requires_ordered_rerun"
    if hazard_type == "cross_source_conflict":
        gen_params.update({
            "hazard_type": "cross_source_conflict", "num_hazards": 1, "hint_level": hint_level,
            "authority_source": "handoff_manifest.json",
            "conflict": "evidence_manifest.json CLAIMS v2 but report body + input_hashes are v1; "
                        "flow_config.json selects v1; prev_signoff.log decoy reinforces v1",
            "valid_recovery": "repair flow_config->v2 AND constraints.sdc->clk_main UP to the manifest "
                              "authority, then rerun stage1 then stage2 (fresh honest chain)",
            "rejects": ["edit manifest/spec DOWN to match stale evidence (forbidden/anti-cheat)",
                        "trust evidence_manifest claim or prev_signoff.log decoy",
                        "stage2 from stale stage1", "stage1-only", "stale report reuse",
                        "hand-edited evidence", "PT green on v1 island"],
            "pass_gate": "SIGNOFF_OK AND EVIDENCE_OK AND FINAL_STATE_OK AND STAGE_CHAIN_OK AND "
                         "PROVENANCE_OK AND AUTHORITY_CONSISTENCY_OK AND HAZARD_RECOVERY_OK AND "
                         "no forbidden edits"})
        err_cat = "workflow_handoff_cross_source_conflict_requires_authority_recovery"
    if hazard_type == "scenario_corner_cross_source_conflict":
        gen_params.update({
            "hazard_type": "scenario_corner_cross_source_conflict", "num_hazards": 1,
            "hint_level": hint_level, "authority_source": "handoff_manifest.json",
            "expected_scenario": SC_AUTH_SCENARIO, "expected_corner": SC_AUTH_CORNER,
            "stale_scenario": SC_STALE_SCENARIO, "stale_corner": SC_STALE_CORNER,
            "netlist_clock_already_correct": True,
            "conflict": "netlist_v2/clk_main are already correct; flow_config.json selects the WRONG "
                        "scenario/corner (%s/%s); evidence_manifest.json CLAIMS %s/%s but its run used "
                        "%s/%s; prev_corner_signoff.log decoy reinforces %s/%s"
                        % (SC_STALE_SCENARIO, SC_STALE_CORNER, SC_AUTH_SCENARIO, SC_AUTH_CORNER,
                           SC_STALE_SCENARIO, SC_STALE_CORNER, SC_STALE_SCENARIO, SC_STALE_CORNER),
            "valid_recovery": "repair flow_config scenario->%s corner->%s UP to the manifest authority "
                              "(do NOT touch netlist/clock), then rerun stage1 then stage2"
                              % (SC_AUTH_SCENARIO, SC_AUTH_CORNER),
            "rejects": ["edit manifest/spec DOWN to the wrong scenario/corner (forbidden/anti-cheat)",
                        "trust evidence_manifest scenario/corner claim or prev_corner_signoff.log decoy",
                        "accept wrong-corner evidence as current", "rerun stage1 under wrong corner",
                        "stage2 from wrong-corner stage1", "stage1-only", "hand-edited evidence",
                        "PT green under wrong corner"],
            "pass_gate": "SIGNOFF_OK AND EVIDENCE_OK AND FINAL_STATE_OK AND STAGE_CHAIN_OK AND "
                         "PROVENANCE_OK AND AUTHORITY_CONSISTENCY_OK AND SCENARIO_CORNER_AUTHORITY_OK "
                         "AND HAZARD_RECOVERY_OK AND no forbidden edits"})
        err_cat = "workflow_handoff_scenario_corner_conflict_requires_provenance_recovery"
    if hazard_type == "multi_conflict_partially_truthful_decoy":
        gen_params.update({
            "hazard_type": "multi_conflict_partially_truthful_decoy", "num_hazards": 2,
            "hint_level": hint_level, "authority_source": "handoff_manifest.json",
            "expected_scenario": SC_AUTH_SCENARIO, "expected_corner": SC_AUTH_CORNER,
            "stale_scenario": SC_STALE_SCENARIO, "stale_corner": SC_STALE_CORNER,
            "global_authority_tuple": ["netlist_v2.v", _CLOCK_PAIRS[0][0], SC_AUTH_SCENARIO, SC_AUTH_CORNER],
            "conflict": "global authority is netlist_v2/clk_main/slow/func; report_A is right on "
                        "netlist/clock but wrong on scenario/corner; report_B is right on scenario/corner "
                        "but stale on netlist; evidence_C is a fresh chain on a semantically wrong package; "
                        "prev_signoff.log is a recent non-authoritative decoy",
            "valid_recovery": "repair flow_config to the GLOBAL authority (netlist_v2 + slow + func; clock "
                              "already clk_main), reject every partial-truth decoy, then rerun stage1 then "
                              "stage2 (fresh ordered chain bound to the global package)",
            "rejects": ["follow report_A (netlist/clock right, scenario/corner wrong)",
                        "follow report_B (scenario/corner right, netlist stale)",
                        "follow evidence_C (syntactically valid chain, semantically wrong package)",
                        "edit manifest/spec DOWN to any decoy (forbidden/anti-cheat)",
                        "make all files agree with one locally-plausible-but-globally-wrong source",
                        "rerun only the last stage", "final-state-only without evidence", "stage1-only",
                        "stage2 from semantically wrong stage1", "hand-edited evidence",
                        "PT green under any wrong package"],
            "pass_gate": "SIGNOFF_OK AND EVIDENCE_OK AND FINAL_STATE_OK AND STAGE_CHAIN_OK AND "
                         "PROVENANCE_OK AND AUTHORITY_CONSISTENCY_OK AND GLOBAL_AUTHORITY_OK AND "
                         "MULTI_CONFLICT_OK AND HAZARD_RECOVERY_OK AND no forbidden edits"})
        err_cat = "workflow_handoff_multi_conflict_requires_global_authority_recovery"
    if hazard_type == "constraint_graph_multi_source_recovery":
        gen_params.update({
            "hazard_type": "constraint_graph_multi_source_recovery", "num_hazards": 3,
            "hint_level": hint_level,
            "authority_source": "handoff_manifest.json (family) + spec.md joint-validity table (no full tuple)",
            "expected_scenario": SC_AUTH_SCENARIO, "expected_corner": SC_AUTH_CORNER,
            "stale_scenario": SC_STALE_SCENARIO, "stale_corner": SC_STALE_CORNER,
            "global_authority_tuple": ["netlist_v2.v", _CLOCK_PAIRS[0][0], SC_AUTH_SCENARIO, SC_AUTH_CORNER],
            "constraints": ["C1 netlist_family", "C2 clock_coverage", "C3 scenario_corner_signoff_pair"],
            "conflict": "no single artifact reveals the full target; report_A is right on netlist/clock "
                        "but wrong on scenario/corner (C3); report_B is right on scenario/corner but stale "
                        "on netlist (C1); report_C is right on netlist/scenario but wrong on clock (C2); "
                        "evidence_D has a valid-looking digest but depends on an invalidated prerequisite "
                        "(C1/C6). Only the INTERSECTION of C1+C2+C3 identifies the unique assignment "
                        "(netlist_v2/clk_main/slow/func).",
            "valid_recovery": "infer the unique assignment by intersecting the constraints, repair flow_config "
                              "to netlist_v2 + slow + func (clock already clk_main), invalidate wrong stages, "
                              "rerun the minimal correct stage subset, produce a fresh globally-consistent chain",
            "rejects": ["follow report_A (netlist/clock right, scenario/corner wrong -> C3)",
                        "follow report_B (scenario/corner right, netlist stale -> C1)",
                        "follow report_C (netlist/scenario right, clock wrong -> C2)",
                        "follow evidence_D (valid digest, invalidated prerequisite -> C1/C6)",
                        "single-axis repair (satisfies only one constraint)",
                        "pairwise-plausible / majority-vote repair (no single decoy majority is global)",
                        "edit manifest/spec DOWN to a decoy (forbidden/anti-cheat)",
                        "rerun only stage2", "final-state-only without evidence", "stage1-only",
                        "stage2 from semantically wrong stage1", "hand-edited evidence",
                        "PT green under any wrong package"],
            "pass_gate": "SIGNOFF_OK AND EVIDENCE_OK AND FINAL_STATE_OK AND STAGE_CHAIN_OK AND "
                         "PROVENANCE_OK AND AUTHORITY_CONSISTENCY_OK AND GLOBAL_AUTHORITY_OK AND "
                         "GLOBAL_CONSTRAINT_OK AND UNIQUE_ASSIGNMENT_OK AND EVIDENCE_CHAIN_SEMANTIC_OK "
                         "AND HAZARD_RECOVERY_OK AND no forbidden edits"})
        err_cat = "workflow_handoff_constraint_graph_requires_joint_consistency_recovery"
    if hazard_type == "axis_binding_value_invention":
        gen_params.update({
            "hazard_type": "axis_binding_value_invention", "num_hazards": 3,
            "hint_level": hint_level,
            "authority_source": "handoff_manifest.json (family) + spec.md typed-axis joint-validity + "
                                "axis_schema.json (vocabulary)",
            "expected_scenario": SC_AUTH_SCENARIO, "expected_corner": SC_AUTH_CORNER,
            "stale_scenario": AB_STALE_SCENARIO, "stale_corner": AB_STALE_CORNER,
            "global_authority_tuple": ["netlist_v2.v", _CLOCK_PAIRS[0][0], SC_AUTH_SCENARIO, SC_AUTH_CORNER],
            "typed_axes": AB_TYPED_AXES, "pvt_label_mapping": AB_PVT_MAPPING,
            "constraints": ["C1 netlist_family", "C2 clock_identity", "C3 scenario_typed",
                            "C4 corner_typed", "C5 scenario_corner_signoff_pair"],
            "conflict": "the typed-axis vocabulary is PUBLISHED (axis_schema.json) but the shipped "
                        "flow_config is a value-SWAP: a corner value 'func' in the scenario slot and a "
                        "scenario value 'typ' in the corner slot (the exact DeepSeek k=3 failure on 0006). "
                        "report_A is the same swap on the right netlist/clock; report_B substitutes a PVT "
                        "label (slow_1.0V_125C) for the corner; report_C binds a generic clock alias 'clk'; "
                        "evidence_D is a syntactically valid chain with swapped scenario/corner fields. "
                        "Because the report body is corner-independent, a correct netlist+clock package "
                        "PrimeTime-signs-off GREEN even when mis-typed -- only the type-membership checks "
                        "(C3/C4) reject it. The unique TYPED assignment is the intersection "
                        "(netlist_v2/clk_main/slow/func).",
            "valid_recovery": "infer the unique typed assignment by intersecting C1-C5 (type-correct axis "
                              "binding, not just global satisfaction), bind each value to its own typed "
                              "axis, repair flow_config to netlist_v2 + slow + func (clock already clk_main), "
                              "rerun stage1 then stage2 (fresh typed-consistent chain)",
            "rejects": ["value-swap (scenario=func/corner=typ) -- signoff-green but mis-typed -> C3+C4",
                        "PVT-label-as-corner (corner=slow_1.0V_125C) -> C4",
                        "wrong clock alias (clock=clk) -> C2",
                        "follow report_A/report_B/report_C/evidence_D (each violates a typed constraint)",
                        "single-axis repair (satisfies only one constraint)",
                        "edit axis_schema/manifest/spec DOWN (forbidden/anti-cheat)",
                        "rerun only stage2", "final-state-only without evidence", "stage1-only",
                        "stage2 from typed-wrong stage1", "hand-edited evidence",
                        "PT green under any mis-typed package"],
            "pass_gate": "SIGNOFF_OK AND EVIDENCE_OK AND FINAL_STATE_OK AND STAGE_CHAIN_OK AND "
                         "PROVENANCE_OK AND AUTHORITY_CONSISTENCY_OK AND GLOBAL_AUTHORITY_OK AND "
                         "GLOBAL_CONSTRAINT_OK AND UNIQUE_ASSIGNMENT_OK AND EVIDENCE_CHAIN_TYPED_OK "
                         "AND AXIS_SCHEMA_OK AND TYPED_BINDING_OK AND PVT_LABEL_OK AND HAZARD_RECOVERY_OK "
                         "AND no forbidden edits"})
        err_cat = "workflow_handoff_axis_binding_requires_typed_global_recovery"
    if hazard_type == "implicit_axis_binding":
        gen_params.update({
            "hazard_type": "implicit_axis_binding", "num_hazards": 3,
            "hint_level": hint_level,
            "authority_source": "inferred from evidence/provenance (NO published schema): manifest family "
                                "+ spec partial terminology + coverage facts + PVT notation",
            "expected_scenario": SC_AUTH_SCENARIO, "expected_corner": SC_AUTH_CORNER,
            "stale_scenario": AB_STALE_SCENARIO, "stale_corner": AB_STALE_CORNER,
            "global_authority_tuple": ["netlist_v2.v", _CLOCK_PAIRS[0][0], SC_AUTH_SCENARIO, SC_AUTH_CORNER],
            "constraints": ["C1 netlist_family", "C2 clock_identity", "C3 scenario_typed(inferred)",
                            "C4 corner_typed(inferred)", "C5 scenario_corner_signoff_pair"],
            "conflict": "the typed-axis vocabulary is NOT published (no axis_schema.json); axis membership "
                        "must be INFERRED from non-canonical report labels (op_point/mode), spec terminology, "
                        "PVT notation, and coverage facts. The shipped flow_config is a value-SWAP on the "
                        "canonical scenario/corner fields (scenario=func/corner=typ). report_A is the same "
                        "swap with op_point/mode labels on the right netlist/clock; report_B has the correct "
                        "op_point/mode but a stale netlist; report_C puts a PVT label (slow_1.0V_125C) in the "
                        "mode field; evidence_D is a valid chain with swapped op_point/mode fields. A correct "
                        "netlist+clock package PrimeTime-signs-off GREEN even when mis-typed; the typed-binding "
                        "oracle (reused from v6, hidden) rejects it. The unique TYPED assignment is the "
                        "intersection (netlist_v2/clk_main/slow/func).",
            "valid_recovery": "infer axis membership from evidence (op_point->scenario, mode->corner via PVT "
                              "notation + spec + coverage), infer the unique typed assignment by intersecting "
                              "C1-C5, repair flow_config to netlist_v2 + slow + func (clock already clk_main), "
                              "rerun stage1 then stage2 (fresh typed-consistent chain)",
            "rejects": ["value-swap (scenario=func/corner=typ) -- signoff-green but mis-typed -> C3+C4",
                        "PVT-label-as-corner (corner=slow_1.0V_125C) -> C4",
                        "wrong clock alias (clock=clk) -> C2",
                        "follow report_A/report_B/report_C/evidence_D (each violates a typed constraint)",
                        "single-axis repair (satisfies only one constraint)",
                        "edit manifest/spec/glossary DOWN (forbidden/anti-cheat)",
                        "rerun only stage2", "final-state-only without evidence", "stage1-only",
                        "stage2 from typed-wrong stage1", "hand-edited evidence",
                        "PT green under any mis-typed package"],
            "pass_gate": "SIGNOFF_OK AND EVIDENCE_OK AND FINAL_STATE_OK AND STAGE_CHAIN_OK AND "
                         "PROVENANCE_OK AND AUTHORITY_CONSISTENCY_OK AND GLOBAL_AUTHORITY_OK AND "
                         "GLOBAL_CONSTRAINT_OK AND UNIQUE_ASSIGNMENT_OK AND EVIDENCE_CHAIN_TYPED_OK "
                         "AND TYPED_BINDING_OK AND HAZARD_RECOVERY_OK AND no forbidden edits"})
        err_cat = "workflow_handoff_implicit_axis_binding_requires_typed_inference_recovery"
    if hazard_type == SRB_HAZARD:
        _amb = variant == SRB_AMBIGUOUS
        gen_params.update({
            "hazard_type": SRB_HAZARD, "num_hazards": 3, "variant": variant,
            "hint_level": hint_level,
            "authority_source": ("inferred from evidence/provenance (variant=%s): manifest family + report "
                                 "intersection%s" % (variant, " + glossary + coverage fact" if not _amb else "")),
            "expected_scenario": SC_AUTH_SCENARIO, "expected_corner": SC_AUTH_CORNER,
            "stale_scenario": AB_STALE_SCENARIO, "stale_corner": AB_STALE_CORNER,
            "global_authority_tuple": ["netlist_v2.v", _CLOCK_PAIRS[0][0], SC_AUTH_SCENARIO, SC_AUTH_CORNER],
            "semantic_role_mapping": dict(SRB_ROLE_MAPPING) if _amb else dict(SRB_CLEAR_LABELS),
            "constraints": ["C1 netlist_family", "C2 clock_identity", "C3 scenario_typed",
                            "C4 corner_typed", "C5 scenario_corner_signoff_pair"],
            "conflict": ("MECHANISM REPRODUCTION (variant=%s): the hidden typed-binding oracle is reused "
                         "byte-identically from v6/v7 (same unique assignment netlist_v2/clk_main/slow/func, "
                         "same 294->1 uniqueness). The shipped flow_config is a value-SWAP on the canonical "
                         "scenario/corner fields (scenario=func/corner=typ -- the exact DeepSeek 0006 failure "
                         "mode). %s report_A is the same swap on the right netlist/clock; report_B carries the "
                         "correct role fields on a stale netlist; report_C puts a PVT label in the corner role "
                         "+ a generic clock alias; evidence_D is a valid chain with the role fields swapped "
                         "inside. A correct netlist+clock package PrimeTime-signs-off GREEN even when mis-typed; "
                         "the typed-binding oracle rejects it. The unique assignment is the intersection "
                         "(netlist_v2/clk_main/slow/func)."
                         % (variant, "AMBIGUOUS: reports use overloaded op_point/mode labels + ship NO anchors"
                            " (no glossary/summary/coverage/spec hint) -- the role must be inferred. CLEAR:"
                            " reports use canonical scenario/corner labels + glossary + public_check_summary.")),
            "valid_recovery": ("resolve the semantic role of each report field label (if ambiguous), infer "
                               "the unique assignment by intersecting C1-C5, repair flow_config to netlist_v2 "
                               "+ slow + func (clock already clk_main), rerun stage1 then stage2"),
            "rejects": ["value-swap / role-mismatch (scenario=func/corner=typ) -- signoff-green but mis-typed -> C3+C4",
                        "PVT-label-as-corner (corner=slow_1.0V_125C) -> C4",
                        "wrong clock alias (clock=clk) -> C2",
                        "follow report_A/report_B/report_C/evidence_D (each violates a typed constraint)",
                        "single-axis repair (satisfies only one constraint)",
                        "edit manifest/spec/glossary DOWN (forbidden/anti-cheat)",
                        "rerun only stage2", "final-state-only without evidence", "stage1-only",
                        "stage2 from role-wrong stage1", "hand-edited evidence",
                        "PT green under any mis-typed package"],
            "pass_gate": "SIGNOFF_OK AND EVIDENCE_OK AND FINAL_STATE_OK AND STAGE_CHAIN_OK AND "
                         "PROVENANCE_OK AND AUTHORITY_CONSISTENCY_OK AND GLOBAL_AUTHORITY_OK AND "
                         "GLOBAL_CONSTRAINT_OK AND UNIQUE_ASSIGNMENT_OK AND EVIDENCE_CHAIN_TYPED_OK "
                         "AND TYPED_BINDING_OK AND SEMANTIC_ROLE_BINDING_OK AND HAZARD_RECOVERY_OK "
                         "AND no forbidden edits"})
        err_cat = ("workflow_handoff_semantic_role_binding_%s_requires_role_resolution_recovery"
                   % ("ambiguous" if _amb else "clear_control"))
    return {
        "task_id": task_id, "track": "p14_workflow_handoff", "tool": ["pt"],
        "difficulty": "hard", "data_type": "mutation_synthetic", "resource_preset": "standard",
        "timeout_sec": 600, "max_tool_calls": 60, "max_patch_attempts": 10, "max_output_tokens": 32000,
        "files": {"visible": visible, "editable": editable, "hidden": hidden, "forbidden": forbidden},
        "run_command": run_command,
        "scoring": {"weights": weights, "evaluator": "workflow_handoff.WorkflowHandoffEvaluator",
                    "explanation_weight": 0.10},
        "sanitizer": {"enabled": True},
        "generator": {"script": "p14_workflow_handoff_gen.py", "seed": seed, "params": gen_params},
        "expected_error_category": err_cat,
        "version": "0.1.0",
    }


# ---------------------------------------------------------------------------
# entry points
# ---------------------------------------------------------------------------
# Frozen, b04-validated assets reused verbatim from the committed p13 task. Reusing them (rather than
# re-synthesizing) is deliberate: they are already proven on real PrimeTime.
_REUSED_FROM_P13 = {
    "netlist_v1.v": "files/netlist_v1.v",
    "netlist_v2.v": "files/netlist_v2.v",
    "tiny.lib": "files/tiny.lib",
    "tiny.db": "files/tiny.db",
    "pt_signoff.tcl": "files/pt_signoff.tcl",
    "evidence_signoff.tcl": "files/evidence_signoff.tcl",       # stage-1 signoff TCL (unchanged)
    "run_launder.tcl": "hidden/run_launder.tcl",
    "run_coverage.tcl": "hidden/run_coverage.tcl",
    "run_signoff.tcl": "hidden/run_signoff.tcl",
}


def _write(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if executable:
        path.chmod(0o755)


def build_task_skeleton(out_dir: Path, task_id: str, seed: int = 0, evidence_steps: int = 1,
                        hazard_type: str | None = None, hint_level: int = 1,
                        variant: str | None = None) -> Path:
    """PURE (no tool). Write the full task directory in the MUTANT starting state.

    Deterministic: same (task_id, seed, evidence_steps, hazard_type) -> byte-identical tree. The initial
    evidence files are the STALE (v1/clk_old) run -- seeded by copying the committed p13 stale evidence
    (for evidence_steps>=1) and, for stage 2, a STALE stage-2 placeholder. bake_golden() later produces
    the real golden evidence for solution/ via the tool.

    hazard_type:
      None (default)            -- the ordered-evidence-chain mutant (workflow_handoff_0001/0002).
                                   Byte-for-byte identical to the committed v1 tasks.
      "cross_source_conflict"   -- p14 v2 preset: the shipped evidence_manifest.json LIES (claims the
                                   v2/clk_main authority package while its report_digest/body are the
                                   stale v1/clk_old run), and a non-authoritative prev_signoff.log
                                   reinforces the v1 story. The agent must apply the authority hierarchy
                                   (manifest > configs > evidence > report > logs), repair the lower
                                   sources UP to the manifest, and regenerate the chain -- not edit the
                                   manifest DOWN or trust the decoy.
    """
    if evidence_steps not in (1, 2):
        raise ValueError("evidence_steps must be 1 or 2")
    if hazard_type not in (None, "cross_source_conflict", "scenario_corner_cross_source_conflict",
                           "multi_conflict_partially_truthful_decoy",
                           "constraint_graph_multi_source_recovery",
                           "axis_binding_value_invention",
                           "implicit_axis_binding",
                           SRB_HAZARD):
        raise ValueError("unsupported hazard_type: %r" % hazard_type)
    _is_sc = hazard_type == "scenario_corner_cross_source_conflict"
    _is_mc = hazard_type == "multi_conflict_partially_truthful_decoy"
    _is_cg = hazard_type == "constraint_graph_multi_source_recovery"
    _is_ab = hazard_type == "axis_binding_value_invention"
    _is_imp = hazard_type == "implicit_axis_binding"
    _is_srb = hazard_type == SRB_HAZARD
    # v8: the semantic-role-binding hazard has two VARIANTS, passed EXPLICITLY (not derived from the task_id,
    # which the schema requires to be numeric workflow_handoff_[0-9]{4}). workflow_handoff_0009 = ambiguous
    # (reproduce 0006); workflow_handoff_0010 = clear_control (negative control). Both share one hazard_type.
    if _is_srb:
        if variant == SRB_AMBIGUOUS or variant == SRB_CLEAR_CONTROL:
            _srb_variant = variant
        else:
            raise ValueError("semantic_role_binding_reproduction requires variant=%r or %r (got %r)"
                             % (SRB_AMBIGUOUS, SRB_CLEAR_CONTROL, variant))
    else:
        _srb_variant = None
    task = out_dir / task_id
    files = task / "files"
    hidden = task / "hidden"
    sol = task / "solution"
    for d in (files, hidden, sol):
        d.mkdir(parents=True, exist_ok=True)

    # reuse frozen p13 assets
    for name, rel in _REUSED_FROM_P13.items():
        dst_dir = hidden if name in ("run_launder.tcl", "run_coverage.tcl", "run_signoff.tcl") else files
        shutil.copy2(P13_SRC / rel, dst_dir / name)
    expected_sha = _sha_file(files / "netlist_v2.v")
    stale_sha = _sha_file(files / "netlist_v1.v")

    # MUTANT inputs (stale island): flow_config -> v1, constraints -> clk_old
    if _is_sc:
        # v3: netlist/clock are ALREADY correct (v2 / clk_main); the mutant ships the WRONG
        # scenario/corner in flow_config so the evidence is generated under the wrong provenance.
        _write(files / "flow_config.json",
               _flow_config("netlist_v2.v",
                            "Downstream evidence flow selection. Editable. Netlist/clock correct, but "
                            "scenario/corner are STALE (%s/%s; restore to %s/%s)."
                            % (SC_STALE_SCENARIO, SC_STALE_CORNER, SC_AUTH_SCENARIO, SC_AUTH_CORNER),
                            scenario=SC_STALE_SCENARIO, corner=SC_STALE_CORNER))
        _write(files / "constraints.sdc",
               _constraints(_CLOCK_PAIRS[0][0],
                            "Timing constraints (clk_main correct -- do not change)."))
    elif _is_mc or _is_cg or _is_ab or _is_imp or _is_srb:
        # v4 multi-conflict / v5 constraint-graph / v6 axis-binding / v7 implicit-axis-binding / v8 srb:
        # flow_config is wrong on MULTIPLE axes (stale netlist_v1 AND a wrong scenario/corner). clock clk_main
        # is already correct. The agent must repair ALL axes up to the global authority (netlist_v2 + slow + func).
        if _is_srb:
            # v8: same value-SWAP mutant as v6/v7 (canonical scenario/corner fields, swapped values). The
            # variant controls the visible clarity bundle: ambiguous ships NO anchors; clear_control ships a
            # glossary + summary. The semantic role of the report labels must be resolved.
            if _srb_variant == SRB_AMBIGUOUS:
                _hint = ("Downstream evidence flow selection. Editable. SEMANTIC-ROLE-BINDING CONFLICT "
                         "(ambiguous): stale netlist (v1) AND a value-SWAP on the signoff axes. The reports "
                         "use field labels like op_point / mode whose logical-axis role is NOT defined upfront "
                         "-- resolve it from the report intersection. No glossary or summary is shipped; no "
                         "single source reveals the full correct target.")
            else:
                _hint = ("Downstream evidence flow selection. Editable. SEMANTIC-ROLE-BINDING CONFLICT "
                         "(clear control): stale netlist (v1) AND a value-SWAP on scenario/corner (a corner "
                         "value is in the scenario slot and a scenario value is in the corner slot). The "
                         "reports use canonical scenario/corner labels; glossary.md + public_check_summary.json "
                         "state the disjoint typed axes and the coverage fact. Infer the unique assignment by "
                         "intersecting the constraints.")
            _stale_sc, _stale_co = AB_STALE_SCENARIO, AB_STALE_CORNER
        elif _is_imp:
            # v7: same value-SWAP mutant as v6 (canonical scenario/corner fields, swapped values) but NO
            # axis_schema.json is shipped -- axis membership must be INFERRED from the report/glossary context.
            _hint = ("Downstream evidence flow selection. Editable. IMPLICIT-AXIS CONFLICT: stale netlist "
                     "(v1) AND a value-SWAP on the typed axes. The report context uses field labels like "
                     "op_point / mode (NOT a published schema) -- infer which value belongs to which axis "
                     "from the report context, the spec terminology, the PVT notation, and the coverage facts. "
                     "No single shipped source reveals the full correct target.")
            _stale_sc, _stale_co = AB_STALE_SCENARIO, AB_STALE_CORNER
        elif _is_ab:
            # v6: the shipped scenario/corner is a value-SWAP (corner value 'func' in the scenario slot,
            # scenario value 'typ' in the corner slot) -- the exact DeepSeek k=3 failure on 0006.
            _hint = ("Downstream evidence flow selection. Editable. AXIS-BINDING CONFLICT: stale netlist "
                     "(v1) AND a value-SWAP on scenario/corner (a corner value is in the scenario slot and a "
                     "scenario value is in the corner slot). The typed-axis vocabulary is in axis_schema.json; "
                     "bind each value to its OWN axis. No single shipped source reveals the full correct target "
                     "-- infer it by intersecting the constraints in spec.md + handoff_manifest.json + "
                     "axis_schema.json.")
            _stale_sc, _stale_co = AB_STALE_SCENARIO, AB_STALE_CORNER
        elif _is_cg:
            _hint = ("Downstream evidence flow selection. Editable. CONSTRAINT-GRAPH CONFLICT: the shipped "
                     "selection is wrong on multiple axes, but NO single shipped source reveals the full "
                     "correct target. Infer it by intersecting the constraints in spec.md + "
                     "handoff_manifest.json (netlist FAMILY + clock coverage + scenario/corner signoff pair).")
            _stale_sc, _stale_co = SC_STALE_SCENARIO, SC_STALE_CORNER
        else:
            _hint = ("Downstream evidence flow selection. Editable. MULTI-CONFLICT: stale netlist (v1) AND "
                     "wrong scenario/corner (%s/%s). Restore netlist->netlist_v2.v AND scenario/corner->"
                     "%s/%s (the global authority). Clock clk_main is correct."
                     % (SC_STALE_SCENARIO, SC_STALE_CORNER, SC_AUTH_SCENARIO, SC_AUTH_CORNER))
            _stale_sc, _stale_co = SC_STALE_SCENARIO, SC_STALE_CORNER
        _write(files / "flow_config.json",
               _flow_config("netlist_v1.v", _hint, scenario=_stale_sc, corner=_stale_co))
        _write(files / "constraints.sdc",
               _constraints(_CLOCK_PAIRS[0][0],
                            "Timing constraints (clk_main correct -- do not change)."))
    else:
        _write(files / "flow_config.json",
               _flow_config("netlist_v1.v", "Downstream evidence flow selection. Editable. STALE (pre-ECO v1)."))
        _write(files / "constraints.sdc",
               _constraints(_CLOCK_PAIRS[0][1], "Timing constraints (STALE clk_old; restore to clk_main)."))

    # stage-1 generator (public + trusted copy) and signoff TCL already copied
    _write(files / "gen_evidence_stage1.py", _GEN_STAGE1)
    _write(hidden / "gen_evidence_stage1_trusted.py", _GEN_STAGE1)
    _write(hidden / "evidence_signoff_trusted.tcl", (P13_SRC / "files/evidence_signoff.tcl").read_text())
    _write(files / "run_evidence_stage1.sh", _run_evidence_stage1_sh(), executable=True)

    # stale stage-1 evidence seeded from the committed p13 stale evidence (v1/clk_old run), but with the
    # stage metadata fields injected so the public runner + grader read consistent shapes.
    stale_mani = json.loads((P13_SRC / "files/evidence_manifest.json").read_text())
    stale_mani = {"stage": "stage1", "upstream_evidence_digest": None, **stale_mani}
    if hazard_type == "cross_source_conflict":
        # CROSS-SOURCE CONFLICT: the shipped manifest LIES about the package -- it claims the v2/clk_main
        # authority selection while its report_digest/input_hashes (and the report body below) are the
        # stale v1/clk_old run. This makes manifest-claim disagree with (a) flow_config.json (v1), (b) the
        # report body (v1), and (c) the authority manifest only by the *claim* matching -- so an agent
        # that trusts the evidence_manifest's claim is misled. The grader's
        # submitted_report_matches_its_manifest + input_hashes_match_ref + authority-pkg checks reject it
        # until the agent repairs the lower sources and regenerates honest fresh evidence.
        stale_mani["selected_netlist"] = "netlist_v2.v"
        stale_mani["selected_clock"] = _CLOCK_PAIRS[0][0]
        stale_mani["_comment"] = ("CONFLICTING evidence manifest: it CLAIMS the v2/clk_main package but "
                                  "its report_digest + input_hashes are the stale v1/clk_old run (see "
                                  "timing_report.rpt body and flow_config.json). Do NOT trust this claim; "
                                  "the authority is handoff_manifest.json. Regenerate fresh evidence.")
    if _is_sc:
        # SCENARIO/CORNER CONFLICT: netlist/clock are already correct (v2/clk_main). The shipped manifest
        # CLAIMS the authority scenario/corner (slow/func) while its run was actually under the wrong
        # scenario/corner (test/typ) -- a lie that an agent who trusts the manifest's scenario/corner
        # claim will accept. The grader pins authority to the hidden re-run's ACTUAL scenario/corner, so
        # the lie is rejected until flow_config is repaired up and the chain is regenerated.
        stale_mani["selected_netlist"] = "netlist_v2.v"
        stale_mani["selected_clock"] = _CLOCK_PAIRS[0][0]
        stale_mani["scenario"] = SC_AUTH_SCENARIO   # CLAIM (lie): authority scenario
        stale_mani["corner"] = SC_AUTH_CORNER       # CLAIM (lie): authority corner
        stale_mani["_comment"] = ("CONFLICTING evidence manifest: it CLAIMS scenario=%s corner=%s "
                                  "(the authority) but its run actually used %s/%s (see flow_config.json "
                                  "and the stale provenance). Do NOT trust this claim; regenerate fresh "
                                  "evidence after repairing flow_config scenario/corner up to the "
                                  "authority." % (SC_AUTH_SCENARIO, SC_AUTH_CORNER,
                                                  SC_STALE_SCENARIO, SC_STALE_CORNER))
    if _is_mc or _is_cg or _is_ab or _is_imp or _is_srb:
        # MULTI-CONFLICT / CONSTRAINT-GRAPH / AXIS-BINDING / IMPLICIT-AXIS / SEMANTIC-ROLE-BINDING shipped
        # manifest: CLAIMS the full global authority (netlist_v2/clk_main/slow/func) while its report body +
        # input_hashes are the stale netlist_v1 run. A multi-axis lie: no shipped source is globally correct.
        # The grader's forgery-resistant consumed-netlist/clock + scenario/corner authority + typed-membership
        # echecks (pinned to flow_config / applied.sdc / hidden re-run) reject it until flow_config is
        # repaired on ALL axes and the chain is regenerated.
        stale_mani["selected_netlist"] = "netlist_v2.v"
        stale_mani["selected_clock"] = _CLOCK_PAIRS[0][0]
        stale_mani["scenario"] = SC_AUTH_SCENARIO   # CLAIM (lie): authority scenario
        stale_mani["corner"] = SC_AUTH_CORNER       # CLAIM (lie): authority corner
        if _is_srb:
            stale_mani["_comment"] = ("CONFLICTING evidence manifest: it CLAIMS the typed-authority "
                                      "assignment (netlist_v2/clk_main/%s/%s) but its report body + "
                                      "input_hashes are the stale netlist_v1 run AND flow_config.json ships a "
                                      "value-SWAP on the signoff axes. Resolve the semantic role of each "
                                      "report field label%s; do NOT trust any single source's claim. "
                                      "Regenerate fresh evidence after inferring and repairing flow_config to "
                                      "the unique assignment."
                                      % (SC_AUTH_SCENARIO, SC_AUTH_CORNER,
                                         " from the report intersection (no glossary/summary is shipped)"
                                         if _srb_variant == SRB_AMBIGUOUS else
                                         " (canonical scenario/corner labels; see glossary.md + "
                                         "public_check_summary.json)"))
        elif _is_imp:
            stale_mani["_comment"] = ("CONFLICTING evidence manifest: it CLAIMS the typed-authority "
                                      "assignment (netlist_v2/clk_main/%s/%s) but its report body + "
                                      "input_hashes are the stale netlist_v1 run AND flow_config.json ships a "
                                      "value-SWAP on the typed axes. The typed-axis membership is NOT "
                                      "published; infer it from the report context (op_point/mode labels), "
                                      "the spec terminology, PVT notation, and coverage facts. Regenerate "
                                      "fresh evidence after inferring and repairing flow_config to the unique "
                                      "typed assignment." % (SC_AUTH_SCENARIO, SC_AUTH_CORNER))
        elif _is_ab:
            stale_mani["_comment"] = ("CONFLICTING evidence manifest: it CLAIMS the typed-authority "
                                      "assignment (netlist_v2/clk_main/%s/%s) but its report body + "
                                      "input_hashes are the stale netlist_v1 run AND flow_config.json ships a "
                                      "value-SWAP (a corner value in the scenario slot, a scenario value in "
                                      "the corner slot). Do NOT trust any single source's claim; the target "
                                      "is the INTERSECTION of the spec.md + handoff_manifest + axis_schema "
                                      "constraints, with each value bound to its OWN typed axis. Regenerate "
                                      "fresh evidence after inferring and repairing flow_config to the unique "
                                      "typed assignment." % (SC_AUTH_SCENARIO, SC_AUTH_CORNER))
        elif _is_cg:
            stale_mani["_comment"] = ("CONFLICTING evidence manifest: it CLAIMS the global-consistent "
                                      "assignment (netlist_v2/clk_main/%s/%s) but its report body + "
                                      "input_hashes are the stale netlist_v1 run (see timing_report.rpt + "
                                      "flow_config.json). Do NOT trust any single source's claim; the target "
                                      "is the INTERSECTION of the spec.md + handoff_manifest constraints, "
                                      "not a manifest line. Regenerate fresh evidence after inferring and "
                                      "repairing flow_config to the unique assignment."
                                      % (SC_AUTH_SCENARIO, SC_AUTH_CORNER))
        else:
            stale_mani["_comment"] = ("CONFLICTING evidence manifest: it CLAIMS the global authority "
                                      "(netlist_v2/clk_main/%s/%s) but its report body + input_hashes are the "
                                      "stale netlist_v1 run (see timing_report.rpt + flow_config.json). Do NOT "
                                      "trust this claim; this is a multi-axis conflict. Regenerate fresh "
                                      "evidence after repairing flow_config to the global authority."
                                      % (SC_AUTH_SCENARIO, SC_AUTH_CORNER))
    _write(files / "evidence_manifest.json", json.dumps(stale_mani, indent=2, sort_keys=True) + "\n")
    _write(files / "timing_report.rpt", (P13_SRC / "files/timing_report.rpt").read_text())

    if hazard_type == "cross_source_conflict":
        # Non-authoritative decoy: a previous sign-off log that reinforces the stale v1/clk_old story.
        # Visible + read-only + forbidden to cite as evidence (a distractor, not an authority source).
        _write(files / "prev_signoff.log",
               "# prev_signoff.log -- ARCHIVED previous sign-off (NON-AUTHORITATIVE diagnostic).\n"
               "# This log is from the pre-ECO v1 flow. It is kept for history only; it is NOT the\n"
               "# authority and must NOT be used to justify consuming netlist_v1.v / clk_old.\n"
               "consumed_netlist=netlist_v1.v\n"
               "clock=clk_old\n"
               "scenario=func\n"
               "corner=typ\n"
               "signoff=OK\n"
               "worst_slack=0.65\n"
               "note=v1 island self-signs-off clean; superseded by the v2 ECO (see handoff_manifest.json)\n")

    if _is_sc:
        # Non-authoritative decoy: a previous corner sign-off log that reinforces the WRONG test/typ
        # scenario/corner. Visible + read-only + forbidden to cite as authority (a distractor).
        _write(files / "prev_corner_signoff.log",
               "# prev_corner_signoff.log -- ARCHIVED previous sign-off (NON-AUTHORITATIVE diagnostic).\n"
               "# This log is from a %s/%s characterization run. It is kept for history only; it is NOT\n"
               "# the authority and must NOT be used to justify keeping scenario=%s / corner=%s.\n"
               "consumed_netlist=netlist_v2.v\n"
               "clock=clk_main\n"
               "scenario=%s\n"
               "corner=%s\n"
               "signoff=OK\n"
               "worst_slack=0.40\n"
               "note=%s/%s run self-signs-off clean; superseded by the %s/%s authority "
               "(see handoff_manifest.json)\n"
               % (SC_STALE_SCENARIO, SC_STALE_CORNER, SC_STALE_SCENARIO, SC_STALE_CORNER,
                  SC_STALE_SCENARIO, SC_STALE_CORNER, SC_STALE_SCENARIO, SC_STALE_CORNER,
                  SC_AUTH_SCENARIO, SC_AUTH_CORNER))

    if _is_mc:
        # v4 multi-conflict decoys: four PARTIALLY-TRUTHFUL evidence sources. Each is locally plausible
        # and right on some axes, wrong on others; none is the global authority. report_A's body is a
        # stand-in here (bake_golden overwrites it with the real netlist_v2 body); report_B reuses the
        # real stale netlist_v1 body (p13), so it is internally consistent on a stale design.
        _rpt_body = (P13_SRC / "files/timing_report.rpt").read_text()
        _write(files / "report_A_typ_test.rpt",
               "# report_A_typ_test.rpt -- shipped evidence candidate (PARTIALLY TRUE).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk_main  scenario=%s  corner=%s\n"
               "# Right design (netlist_v2) + clock (clk_main); WRONG scenario/corner vs global authority.\n"
               % (SC_STALE_SCENARIO, SC_STALE_CORNER) + _rpt_body)
        _write(files / "report_B_stale_netlist.rpt",
               "# report_B_stale_netlist.rpt -- shipped evidence candidate (PARTIALLY TRUE).\n"
               "# consumed_netlist=netlist_v1.v  clock=clk_main  scenario=%s  corner=%s\n"
               "# Right scenario/corner; STALE netlist (netlist_v1) vs global authority.\n"
               % (SC_AUTH_SCENARIO, SC_AUTH_CORNER) + _rpt_body)
        _cmani = dict(stale_mani)
        _cmani["stage"] = "stage1"
        _cmani["selected_netlist"] = "netlist_v1.v"
        _cmani["selected_clock"] = _CLOCK_PAIRS[0][0]
        _cmani["scenario"] = SC_AUTH_SCENARIO
        _cmani["corner"] = SC_AUTH_CORNER
        _cmani["_comment"] = ("evidence_C_manifest.json -- shipped evidence candidate (PARTIALLY TRUE). "
                              "Fresh digest/upstream chain, but semantically tied to stale netlist_v1 "
                              "(wrong package). Syntactically valid; globally invalid.")
        _write(files / "evidence_C_manifest.json", json.dumps(_cmani, indent=2, sort_keys=True) + "\n")
        _write(files / "prev_signoff.log",
               "# prev_signoff.log -- ARCHIVED previous sign-off (NON-AUTHORITATIVE diagnostic).\n"
               "# Recent and plausible, but NOT the authority. Reinforces a partially-true decoy path;\n"
               "# it must NOT be used to justify any non-global-authority package.\n"
               "consumed_netlist=netlist_v2.v\nclock=clk_main\nscenario=%s\ncorner=%s\n"
               "signoff=OK\nworst_slack=0.45\nnote=characterization run; superseded by the global "
               "authority in handoff_manifest.json\n" % (SC_STALE_SCENARIO, SC_STALE_CORNER))

    if _is_cg:
        # v5 constraint-graph decoys: each PARTIALLY-TRUTHFUL source satisfies exactly one constraint and
        # violates another, so no source is globally consistent and no two agree on the same wrong axis
        # (the agent cannot majority-vote; it must intersect). report_A's body is a stand-in here
        # (bake_golden overwrites it with the real netlist_v2 body); report_B reuses the real stale v1 body;
        # report_C reuses a v2 body but is pinned to the wrong clock (clk_old, zero coverage).
        _rpt_body = (P13_SRC / "files/timing_report.rpt").read_text()
        # report_A: right netlist/clock (C1+C2 ok), WRONG scenario/corner -> violates C3
        _write(files / "report_A_scenario_corner.rpt",
               "# report_A_scenario_corner.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk_main  scenario=%s  corner=%s\n"
               "# Right design (netlist_v2) + clock (clk_main) -> satisfies C1+C2; WRONG scenario/corner "
               "vs the spec.md signoff pair -> violates C3.\n"
               % (SC_STALE_SCENARIO, SC_STALE_CORNER) + _rpt_body)
        # report_B: right scenario/corner (C3 ok), STALE netlist -> violates C1
        _write(files / "report_B_stale_netlist.rpt",
               "# report_B_stale_netlist.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE).\n"
               "# consumed_netlist=netlist_v1.v  clock=clk_main  scenario=%s  corner=%s\n"
               "# Right scenario/corner -> satisfies C3; STALE netlist (netlist_v1) outside the manifest "
               "family -> violates C1.\n"
               % (SC_AUTH_SCENARIO, SC_AUTH_CORNER) + _rpt_body)
        # report_C: right netlist/scenario (C1+C3 ok), WRONG clock (clk_old, no coverage) -> violates C2
        _write(files / "report_C_wrong_clock.rpt",
               "# report_C_wrong_clock.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk_old  scenario=%s  corner=%s\n"
               "# Right design + scenario/corner -> satisfies C1+C3; clock clk_old yields NO intended-clock "
               "coverage on netlist_v2 -> violates C2.\n"
               % (SC_AUTH_SCENARIO, SC_AUTH_CORNER) + _rpt_body)
        # evidence_D: syntactically valid digest/upstream chain, but semantically tied to an INVALIDATED
        # prerequisite stage (stale v1) -> violates C1 (and the stage-dependency constraint at runtime)
        _dmani = dict(stale_mani)
        _dmani["stage"] = "stage1"
        _dmani["selected_netlist"] = "netlist_v1.v"
        _dmani["selected_clock"] = _CLOCK_PAIRS[0][0]
        _dmani["scenario"] = SC_AUTH_SCENARIO
        _dmani["corner"] = SC_AUTH_CORNER
        _dmani["_comment"] = ("evidence_D_manifest.json -- shipped evidence candidate (PAIRWISE PLAUSIBLE). "
                              "Fresh-looking digest / upstream chain, but semantically depends on an "
                              "INVALIDATED prerequisite stage (stale netlist_v1). Syntactically valid; "
                              "globally invalid (violates C1 + the stage-dependency constraint).")
        _write(files / "evidence_D_manifest.json", json.dumps(_dmani, indent=2, sort_keys=True) + "\n")
        _write(files / "prev_signoff.log",
               "# prev_signoff.log -- ARCHIVED previous sign-off (NON-AUTHORITATIVE diagnostic).\n"
               "# Recent and plausible, but NOT the authority. Reinforces one pairwise-plausible decoy;\n"
               "# it must NOT be used to justify any non-global-consistent package.\n"
               "consumed_netlist=netlist_v2.v\nclock=clk_main\nscenario=%s\ncorner=%s\n"
               "signoff=OK\nworst_slack=0.45\nnote=characterization run; superseded by the unique global "
               "assignment (the constraint-graph intersection)\n" % (SC_STALE_SCENARIO, SC_STALE_CORNER))

    if _is_ab:
        # v6 axis-binding decoys: each PARTIALLY-TRUTHFUL source is a TYPED-axis failure -- a value valid on
        # one axis placed on another, or an out-of-domain label. The typed-axis vocabulary is PUBLISHED in
        # axis_schema.json (the challenge is binding, not vocabulary hiding). report bodies are stand-ins
        # here (bake_golden overwrites report_A with the real netlist_v2 body); report_B/report_C reuse the
        # real stale v1 body (internally consistent on a real design). evidence_D reuses stale_mani with the
        # scenario/corner fields swapped, so it is a syntactically valid chain on a typed-mismatched package.
        _rpt_body = (P13_SRC / "files/timing_report.rpt").read_text()
        # axis_schema.json: PUBLISHED typed vocabulary (no traps, no expected answer) -- visible + forbidden.
        _write(files / "axis_schema.json", json.dumps({
            "_comment": "Typed-axis vocabulary for the acc_stage axis-binding handoff. PUBLISHED (visible) "
                        "because the challenge is correct BINDING, not vocabulary hiding. This file states "
                        "the allowed typed values and the PVT-label mapping; it does NOT state which member "
                        "is correct. Read-only and FROZEN.",
            **AB_TYPED_AXES,
            "pvt_label_mapping": AB_PVT_MAPPING,
            "type_rules": [
                "scenario_axis values may occupy ONLY the scenario field",
                "corner_axis values may occupy ONLY the corner field",
                "a pvt_label_axis token is descriptive metadata mapping to a (scenario, corner) pair; it is "
                "never a valid scenario or corner value",
                "clock_axis requires exact identity (clk_main); a generic/aliased name is rejected",
            ],
            "binding_rule": "the correct package requires type-correct axis binding AND global constraint "
                            "satisfaction -- a value valid on one axis is invalid on another, and a PVT label "
                            "is never an axis value.",
        }, indent=2) + "\n")
        # report_A: right netlist/clock (C1+C2 ok), scenario/corner SWAPPED (corner value 'func' in the
        # scenario slot, scenario value 'typ' in the corner slot) -> violates C3+C4. This is the
        # signoff-green-but-mis-typed decoy: PT signs off (right netlist+clock) but typed-binding fails.
        _write(files / "report_A_value_swap.rpt",
               "# report_A_value_swap.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE / MIS-TYPED).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk_main  scenario=%s  corner=%s\n"
               "# Right design (netlist_v2) + clock (clk_main) -> satisfies C1+C2; but scenario/corner are "
               "SWAPPED (a corner value is in the scenario slot; a scenario value is in the corner slot) -> "
               "violates C3+C4 (typed binding). PrimeTime still signs off green here -- type-binding, not "
               "signoff, is what rejects it.\n"
               % (AB_STALE_SCENARIO, AB_STALE_CORNER) + _rpt_body)
        # report_B: right netlist/clock/scenario (C1+C2+C3 ok), corner = a PVT LABEL (slow_1.0V_125C) -> C4.
        _write(files / "report_B_pvt_corner.rpt",
               "# report_B_pvt_corner.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE / MIS-TYPED).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk_main  scenario=%s  corner=%s\n"
               "# Right design + clock + scenario -> satisfies C1+C2+C3; but the corner is a PVT LABEL "
               "(%s), not a corner_axis value -> violates C4 (a PVT label is metadata, never an axis value).\n"
               % (SC_AUTH_SCENARIO, "slow_1.0V_125C", "slow_1.0V_125C") + _rpt_body)
        # report_C: right netlist/scenario/corner (C1+C3+C4+C5 ok), clock = generic alias 'clk' -> C2.
        _write(files / "report_C_wrong_clock.rpt",
               "# report_C_wrong_clock.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE / MIS-TYPED).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk  scenario=%s  corner=%s\n"
               "# Right design + scenario/corner -> satisfies C1+C3+C4+C5; but the clock is a GENERIC ALIAS "
               "('clk'), not the exact identity clk_main -> violates C2.\n"
               % (SC_AUTH_SCENARIO, SC_AUTH_CORNER) + _rpt_body)
        # evidence_D: syntactically valid digest/upstream chain, but scenario/corner fields SWAPPED inside
        # -> violates C3+C4 (typed-field mismatch in a well-formed chain).
        _dmani = dict(stale_mani)
        _dmani["stage"] = "stage1"
        _dmani["selected_netlist"] = "netlist_v2.v"
        _dmani["selected_clock"] = _CLOCK_PAIRS[0][0]
        _dmani["scenario"] = AB_STALE_SCENARIO   # swapped: corner value in scenario field
        _dmani["corner"] = AB_STALE_CORNER       # swapped: scenario value in corner field
        _dmani["_comment"] = ("evidence_D_typed_mismatch.json -- shipped evidence candidate (PAIRWISE "
                              "PLAUSIBLE / MIS-TYPED). Fresh-looking digest / upstream chain, but the "
                              "scenario/corner FIELDS are swapped inside (a corner value in the scenario "
                              "field, a scenario value in the corner field). Syntactically valid; fails "
                              "typed binding (violates C3+C4).")
        _write(files / "evidence_D_typed_mismatch.json", json.dumps(_dmani, indent=2, sort_keys=True) + "\n")
        _write(files / "prev_signoff.log",
               "# prev_signoff.log -- ARCHIVED previous sign-off (NON-AUTHORITATIVE diagnostic).\n"
               "# Recent and plausible, but NOT the authority. Reinforces the value-swap decoy; it must\n"
               "# NOT be used to justify any mis-typed package (a signoff-green-but-mis-typed package is\n"
               "# still rejected by typed binding).\n"
               "consumed_netlist=netlist_v2.v\nclock=clk_main\nscenario=%s\ncorner=%s\n"
               "signoff=OK\nworst_slack=0.45\nnote=characterization run; superseded by the unique typed "
               "assignment (the axis-binding intersection)\n" % (AB_STALE_SCENARIO, AB_STALE_CORNER))

    if _is_imp:
        # v7 implicit-axis decoys: each candidate is plausible but mis-typed. CRITICAL: reports use
        # NON-CANONICAL context labels (op_point / mode), NOT scenario/corner -- axis membership must be
        # INFERRED. NO axis_schema.json is shipped. report bodies are stand-ins (bake_golden overwrites the
        # right-netlist report_A with the real netlist_v2 body if a full task is later baked).
        _rpt_body = (P13_SRC / "files/timing_report.rpt").read_text()
        # glossary.md: INCOMPLETE examples only (NOT a complete vocabulary / value-to-axis table)
        _write(files / "glossary.md",
               "# acc_stage handoff glossary (examples only -- NOT a complete schema)\n\n"
               "This glossary gives EXAMPLES of the terminology used in the reports. It is deliberately "
               "INCOMPLETE: it does not list every valid value, and it does not give a value-to-axis table.\n\n"
               "- **op_point**: an operating-point field. The design's operating points are named in the "
               "spec; a report's `op_point=` value is one of them.\n"
               "- **mode**: a signoff-mode field.\n"
               "- **PVT descriptor**: a string of the form `<process>_<voltage>_<temperature>`, e.g. "
               "`slow_1.0V_125C`. A PVT descriptor CHARACTERIZES an (operating point, signoff mode) pair but "
               "is NEVER a valid op_point or mode value itself.\n"
               "- The consumed clock is the one that yields full intended-clock path coverage on the design.\n"
               "- op_point and mode are DISJOINT typed axes: a value valid on one is invalid on the other.\n")
        # report_A: right netlist/clock, op_point/mode SWAPPED (a corner value in op_point, a scenario value
        # in mode) -> violates the typed binding. Matches the mutant (scenario=func corner=typ). PrimeTime
        # signs off green here; typed binding rejects it.
        _write(files / "report_A_context_swap.rpt",
               "# report_A_context_swap.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE / MIS-TYPED).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk_main  op_point=%s  mode=%s\n"
               "# Right design (netlist_v2) + clock (clk_main); op_point/mode are SWAPPED vs the authority "
               "(a corner value is in op_point; a scenario value is in mode). PrimeTime still signs off green "
               "here -- typed binding, not signoff, is what rejects it.\n"
               % (AB_STALE_SCENARIO, AB_STALE_CORNER) + _rpt_body)
        # report_B: correct op_point/mode, STALE netlist (netlist_v1)
        _write(files / "report_B_context_stale.rpt",
               "# report_B_context_stale.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE).\n"
               "# consumed_netlist=netlist_v1.v  clock=clk_main  op_point=%s  mode=%s\n"
               "# Right op_point/mode; STALE netlist (netlist_v1) outside the manifest family.\n"
               % (SC_AUTH_SCENARIO, SC_AUTH_CORNER) + _rpt_body)
        # report_C: op_point correct, mode = a PVT label (looks plausible, semantically wrong)
        _write(files / "report_C_context_pvt.rpt",
               "# report_C_context_pvt.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE / MIS-TYPED).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk_main  op_point=%s  mode=%s\n"
               "# Right design + clock + op_point; mode is a PVT DESCRIPTOR, not a signoff-mode value.\n"
               % (SC_AUTH_SCENARIO, "slow_1.0V_125C") + _rpt_body)
        # evidence_D: syntactically valid digest/upstream chain, but op_point/mode swapped inside
        _dmani = dict(stale_mani)
        _dmani["stage"] = "stage1"
        _dmani["selected_netlist"] = "netlist_v2.v"
        _dmani["selected_clock"] = _CLOCK_PAIRS[0][0]
        _dmani["op_point"] = AB_STALE_SCENARIO    # swapped: corner value in op_point field
        _dmani["mode"] = AB_STALE_CORNER          # swapped: scenario value in mode field
        _dmani.pop("scenario", None); _dmani.pop("corner", None)
        _dmani["_comment"] = ("evidence_D_context_mismatch.json -- shipped evidence candidate (PAIRWISE "
                              "PLAUSIBLE / MIS-TYPED). Fresh-looking digest / upstream chain, but the "
                              "op_point/mode fields are swapped inside. Syntactically valid; fails typed "
                              "binding.")
        _write(files / "evidence_D_context_mismatch.json", json.dumps(_dmani, indent=2, sort_keys=True) + "\n")
        # public_check_summary.json: VERDICT-FIRST pairwise typed/provenance inconsistencies + the
        # tool-derived coverage fact (so the clock is inferable without running PT). Never the answer/schema.
        _write(files / "public_check_summary.json", json.dumps({
            "_comment": "Public pairwise consistency summary. Reports SYMPTOMS only; never the recovery "
                        "target, the typed-axis membership, or the verdict.",
            "intended_clock_coverage": {"clk_main": 1, "clk_old": 0, "clk": 0},
            "pairwise_conflicts": [
                "report_A_context_swap.rpt op_point/mode disagree with report_B_context_stale.rpt",
                "report_C_context_pvt.rpt mode value looks like a PVT descriptor, not a signoff-mode value",
                "flow_config.json scenario/corner disagree with report_B_context_stale.rpt op_point/mode",
                "evidence_D_context_mismatch.json op_point/mode disagree internally",
            ],
            "note": "These are symptom-level pairwise conflicts; the globally-consistent typed assignment "
                    "is NOT stated here.",
        }, indent=2) + "\n")
        _write(files / "prev_signoff.log",
               "# prev_signoff.log -- ARCHIVED previous sign-off (NON-AUTHORITATIVE diagnostic).\n"
               "# Recent and plausible, but NOT the authority. Reinforces one pairwise-plausible decoy; it\n"
               "# must NOT be used to justify any mis-typed package.\n"
               "consumed_netlist=netlist_v2.v\nclock=clk_main\nop_point=%s\nmode=%s\n"
               "signoff=OK\nworst_slack=0.45\nnote=characterization run; superseded by the unique typed "
               "assignment (inferred from the evidence intersection)\n" % (AB_STALE_SCENARIO, AB_STALE_CORNER))

    if _is_srb:
        # v8 semantic-role-binding REPRODUCTION decoys. Each candidate is pairwise-plausible but role-
        # mismatched. The VARIANT controls the report field labels + the inference anchors:
        #   ambiguous (0009a): reports use OVERLOADED op_point/mode labels; NO glossary/summary shipped.
        #   clear_control (0009b): reports use CANONICAL scenario/corner labels; glossary + summary shipped.
        # In BOTH variants the swapped values (func/typ) are embedded inside the genuine-looking report
        # comment lines (the 0006 body-embedding mechanism), and report_B carries the correct role fields on a
        # stale netlist (the multi-source intersection). bake_golden overwrites report_A_role_swap.rpt's body
        # with the real netlist_v2 timing body (keeping the header); report_B/report_C reuse the stale p13 body.
        _amb = _srb_variant == SRB_AMBIGUOUS
        # the two role-field labels and the (correct) authority values under them
        _lbl_scn, _lbl_cor = ("op_point", "mode") if _amb else ("scenario", "corner")
        _rpt_body = (P13_SRC / "files/timing_report.rpt").read_text()
        # report_A: right netlist/clock (C1+C2 ok); the role fields are SWAPPED (corner value 'func' in the
        # scenario-role slot, scenario value 'typ' in the corner-role slot) -> violates C3+C4. PT signs off
        # green here (right netlist+clock) -- semantic-role binding, not signoff, is what rejects it.
        _write(files / "report_A_role_swap.rpt",
               "# report_A_role_swap.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE / MIS-TYPED).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk_main  %s=%s  %s=%s\n"
               "# Right design (netlist_v2) + clock (clk_main); the role fields are SWAPPED vs the authority "
               "(a corner value in the %s slot; a scenario value in the %s slot). PrimeTime still signs off "
               "green here -- semantic-role binding, not signoff, is what rejects it.\n"
               % (_lbl_scn, AB_STALE_SCENARIO, _lbl_cor, AB_STALE_CORNER, _lbl_scn, _lbl_cor) + _rpt_body)
        # report_B: correct role fields (slow/func) on a STALE netlist (netlist_v1) -> violates C1.
        _write(files / "report_B_role_stale.rpt",
               "# report_B_role_stale.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE).\n"
               "# consumed_netlist=netlist_v1.v  clock=clk_main  %s=%s  %s=%s\n"
               "# Correct role fields -> satisfies C3+C4+C5; STALE netlist (netlist_v1) outside the manifest "
               "family -> violates C1.\n"
               % (_lbl_scn, SC_AUTH_SCENARIO, _lbl_cor, SC_AUTH_CORNER) + _rpt_body)
        # report_C: right netlist/scenario; corner = a PVT LABEL (slow_1.0V_125C) + a generic clock alias
        # 'clk' -> violates C2+C4.
        _write(files / "report_C_role_pvt.rpt",
               "# report_C_role_pvt.rpt -- shipped evidence candidate (PAIRWISE PLAUSIBLE / MIS-TYPED).\n"
               "# consumed_netlist=netlist_v2.v  clock=clk  %s=%s  %s=%s\n"
               "# Right design + scenario -> satisfies C1+C3; but the corner role is a PVT DESCRIPTOR "
               "(slow_1.0V_125C), not a corner value -> violates C4; and the clock is a GENERIC ALIAS ('clk'), "
               "not clk_main -> violates C2.\n"
               % (_lbl_scn, SC_AUTH_SCENARIO, _lbl_cor, "slow_1.0V_125C") + _rpt_body)
        # evidence_D: syntactically valid digest/upstream chain, but the role fields are SWAPPED inside.
        _dmani = dict(stale_mani)
        _dmani["stage"] = "stage1"
        _dmani["selected_netlist"] = "netlist_v2.v"
        _dmani["selected_clock"] = _CLOCK_PAIRS[0][0]
        if _amb:
            _dmani["op_point"] = AB_STALE_SCENARIO    # swapped: corner value in the op_point role
            _dmani["mode"] = AB_STALE_CORNER          # swapped: scenario value in the mode role
            _dmani.pop("scenario", None); _dmani.pop("corner", None)
            _fields = "op_point/mode"
        else:
            _dmani["scenario"] = AB_STALE_SCENARIO    # swapped: corner value in the scenario field
            _dmani["corner"] = AB_STALE_CORNER        # swapped: scenario value in the corner field
            _fields = "scenario/corner"
        _dmani["_comment"] = ("evidence_D_role_mismatch.json -- shipped evidence candidate (PAIRWISE "
                              "PLAUSIBLE / MIS-TYPED). Fresh-looking digest / upstream chain, but the %s "
                              "fields are swapped inside (a corner value in the scenario role, a scenario "
                              "value in the corner role). Syntactically valid; fails semantic-role binding "
                              "(violates C3+C4)." % _fields)
        _write(files / "evidence_D_role_mismatch.json", json.dumps(_dmani, indent=2, sort_keys=True) + "\n")
        # clear-control variant only: ship the inference anchors (sparse glossary + public pairwise summary
        # with the coverage fact). The ambiguous variant ships NEITHER -- the absence is the experiment.
        if not _amb:
            _write(files / "glossary.md",
                   "# acc_stage handoff glossary (examples only -- NOT a complete schema)\n\n"
                   "This glossary gives EXAMPLES of the terminology used in the reports. It is deliberately "
                   "INCOMPLETE: it does not list every valid value, and it does not give a value-to-axis "
                   "table.\n\n"
                   "- **scenario**: a setup scenario field. The design's scenarios are named in the spec; a "
                   "report's `scenario=` value is one of them.\n"
                   "- **corner**: a signoff corner field.\n"
                   "- **PVT descriptor**: a string of the form `<process>_<voltage>_<temperature>`, e.g. "
                   "`slow_1.0V_125C`. A PVT descriptor CHARACTERIZES a (scenario, corner) pair but is NEVER a "
                   "valid scenario or corner value itself.\n"
                   "- The consumed clock is the one that yields full intended-clock path coverage on the "
                   "design.\n"
                   "- scenario and corner are DISJOINT typed axes: a value valid on one is invalid on the "
                   "other.\n")
            _write(files / "public_check_summary.json", json.dumps({
                "_comment": "Public pairwise consistency summary. Reports SYMPTOMS only; never the recovery "
                            "target, the typed-axis membership, or the verdict.",
                "intended_clock_coverage": {"clk_main": 1, "clk_old": 0, "clk": 0},
                "pairwise_conflicts": [
                    "report_A_role_swap.rpt scenario/corner disagree with report_B_role_stale.rpt",
                    "report_C_role_pvt.rpt corner value looks like a PVT descriptor, not a corner value",
                    "flow_config.json scenario/corner disagree with report_B_role_stale.rpt",
                    "evidence_D_role_mismatch.json scenario/corner disagree internally",
                ],
                "note": "These are symptom-level pairwise conflicts; the globally-consistent assignment is "
                        "NOT stated here.",
            }, indent=2) + "\n")
        _write(files / "prev_signoff.log",
               "# prev_signoff.log -- ARCHIVED previous sign-off (NON-AUTHORITATIVE diagnostic).\n"
               "# Recent and plausible, but NOT the authority. Reinforces one pairwise-plausible decoy; it\n"
               "# must NOT be used to justify any role-mismatched package.\n"
               "consumed_netlist=netlist_v2.v\nclock=clk_main\n%s=%s\n%s=%s\n"
               "signoff=OK\nworst_slack=0.45\nnote=characterization run; superseded by the unique assignment "
               "(the role-binding intersection)\n" % (_lbl_scn, AB_STALE_SCENARIO, _lbl_cor, AB_STALE_CORNER))

    if evidence_steps == 2:
        _write(files / "gen_evidence_stage2.py", _GEN_STAGE2)
        _write(hidden / "gen_evidence_stage2_trusted.py", _GEN_STAGE2)
        _write(files / "evidence_signoff_stage2.tcl", _SIGNOFF_STAGE2_TCL)
        _write(hidden / "evidence_signoff_stage2_trusted.tcl", _SIGNOFF_STAGE2_TCL)
        _write(files / "run_evidence_stage2.sh", _run_evidence_stage2_sh(), executable=True)
        # stale stage-2 placeholder: bound to the STALE stage-1 digest, so public reports STALE/MISMATCH
        stale_s2 = {
            "_comment": "STALE stage-2 summary (pre-repair). Regenerate with run_evidence_stage2.sh "
                        "after stage 1 is fresh.",
            "stage": "stage2",
            "upstream_evidence_digest": stale_mani.get("report_digest"),
            "upstream_stage_ok": True,
            "input_hashes": stale_mani.get("input_hashes", {}),
            "selected_netlist": stale_mani.get("selected_netlist"),
            "selected_clock": stale_mani.get("selected_clock"),
            "scenario": SCENARIO, "corner": CORNER, "tool": "pt_shell", "tool_exit": 0,
            "signoff": "OK", "stage2_constrained_paths": 1, "stage2_slack": "0.0",
            "stage2_report_digest": "0" * 64, "run_nonce": "staleplaceholder",
        }
        _write(files / "stage2_summary.json", json.dumps(stale_s2, indent=2, sort_keys=True) + "\n")

    # public runner
    _write(files / "run_public.tcl", _run_public_tcl(evidence_steps))
    _write(files / "run_public.sh", _run_public_sh(), executable=True)

    # authority + docs
    _auth_scn = SC_AUTH_SCENARIO if (_is_sc or _is_mc or _is_cg or _is_ab or _is_imp or _is_srb) else SCENARIO
    _auth_cor = SC_AUTH_CORNER if (_is_sc or _is_mc or _is_cg or _is_ab or _is_imp or _is_srb) else CORNER
    _write(files / "handoff_manifest.json",
           _handoff_manifest(expected_sha, _auth_scn, _auth_cor, cg=_is_cg, ab=_is_ab, imp=_is_imp,
                             srb=_srb_variant))
    _write(files / "spec.md", _spec_md(evidence_steps, sc_hazard=_is_sc, mc_hazard=_is_mc,
                                       cg_hazard=_is_cg, ab_hazard=_is_ab, imp_hazard=_is_imp,
                                       srb_hazard=_is_srb, srb_variant=_srb_variant))
    _write(task / "prompt.md", _prompt_md(evidence_steps, sc_hazard=_is_sc, mc_hazard=_is_mc,
                                          cg_hazard=_is_cg, ab_hazard=_is_ab, imp_hazard=_is_imp,
                                          srb_hazard=_is_srb, srb_variant=_srb_variant))

    # hidden oracle
    _write(hidden / "grade_workflow.py", _GRADE_WORKFLOW)
    _write(hidden / "handoff_truth.json",
           _handoff_truth(evidence_steps, expected_sha, stale_sha, hazard_type, variant=_srb_variant))
    _write(hidden / "run_hidden.sh", _run_hidden_sh(evidence_steps), executable=True)
    _write(hidden / "regen_reference.sh", _regen_reference_sh(evidence_steps), executable=True)

    # GOLDEN inputs into solution/ (evidence baked later by bake_golden)
    if _is_sc or _is_mc or _is_cg or _is_ab or _is_imp or _is_srb:
        _write(sol / "flow_config.json",
               _flow_config("netlist_v2.v",
                            ("Restored to the global authority: netlist_v2 + clk_main + %s/%s."
                             % (SC_AUTH_SCENARIO, SC_AUTH_CORNER)),
                            scenario=SC_AUTH_SCENARIO, corner=SC_AUTH_CORNER))
        _write(sol / "constraints.sdc",
               _constraints(_CLOCK_PAIRS[0][0], "clk_main (already correct; unchanged)."))
    else:
        _write(sol / "flow_config.json",
               _flow_config("netlist_v2.v", "Restored to current v2 netlist."))
        _write(sol / "constraints.sdc",
               _constraints(_CLOCK_PAIRS[0][0], "Restored to current clock clk_main; en is part of v2."))

    # metadata
    _write(task / "metadata.json",
           json.dumps(_metadata(task_id, seed, evidence_steps, hazard_type, hint_level,
                                variant=_srb_variant), indent=2) + "\n")
    return task


def _run_chain(work: Path, evidence_steps: int, pt_cmd: str) -> None:
    env = dict(os.environ, EDA_PT_CMD=pt_cmd)
    subprocess.run(["bash", "run_evidence_stage1.sh"], cwd=work, env=env,
                   capture_output=True, text=True, timeout=600)
    if evidence_steps == 2:
        subprocess.run(["bash", "run_evidence_stage2.sh"], cwd=work, env=env,
                       capture_output=True, text=True, timeout=600)


def bake_golden(task_dir: Path, pt_cmd: str, evidence_steps: int) -> None:
    """TOOL-backed. Run the evidence chain on the GOLDEN inputs in a scratch copy of files/, then copy
    the produced evidence into solution/ (and refresh files/ stale evidence is NOT touched -- the
    mutant ships stale on purpose). Idempotent + deterministic given a working pt_shell.
    """
    task = Path(task_dir)
    scratch = task / ".bake_scratch"
    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(task / "files", scratch)
    # overlay golden inputs
    shutil.copy2(task / "solution" / "flow_config.json", scratch / "flow_config.json")
    shutil.copy2(task / "solution" / "constraints.sdc", scratch / "constraints.sdc")
    _run_chain(scratch, evidence_steps, pt_cmd)
    for name in ("timing_report.rpt", "evidence_manifest.json"):
        if (scratch / name).exists():
            shutil.copy2(scratch / name, task / "solution" / name)
    if evidence_steps == 2 and (scratch / "stage2_summary.json").exists():
        shutil.copy2(scratch / "stage2_summary.json", task / "solution" / "stage2_summary.json")
    # v4 multi-conflict: bake decoy report_A with the REAL netlist_v2 body (corner-independent on the
    # single tiny.db, so its body == the golden body) stamped with the WRONG scenario/corner. This makes
    # report_A internally consistent (genuine netlist_v2 timing) but wrong on corner -- a faithful
    # partially-truthful decoy. Detected from the task's truth (global_authority_tuple), not an argument.
    try:
        _truth = json.loads((task / "hidden" / "handoff_truth.json").read_text())
    except (OSError, ValueError):
        _truth = {}
    if _truth.get("global_authority_tuple") is not None and (scratch / "timing_report.rpt").exists():
        _body = (scratch / "timing_report.rpt").read_text()
        _stale_sc = _truth.get("stale_scenario", "test")
        _stale_co = _truth.get("stale_corner", "typ")
        _is_cg = _truth.get("constraint_graph") is not None
        _is_ab = _truth.get("hazard_type") == "axis_binding_value_invention"
        _is_imp = _truth.get("hazard_type") == "implicit_axis_binding"
        _is_srb = _truth.get("hazard_type") == SRB_HAZARD
        # v4 report_A_typ_test.rpt; v5 report_A_scenario_corner.rpt; v6 report_A_value_swap.rpt;
        # v7 implicit report_A_context_swap.rpt; v8 srb report_A_role_swap.rpt (right netlist/clock body,
        # swapped role fields).
        if _is_srb:
            _ra = "report_A_role_swap.rpt"
        elif _is_imp:
            _ra = "report_A_context_swap.rpt"
        elif _is_ab:
            _ra = "report_A_value_swap.rpt"
        elif _is_cg:
            _ra = "report_A_scenario_corner.rpt"
        else:
            _ra = "report_A_typ_test.rpt"
        if _is_srb:
            # v8: header label set depends on the variant (ambiguous -> op_point/mode; clear -> scenario/corner)
            _amb = _truth.get("variant") == SRB_AMBIGUOUS
            _lscn, _lcor = ("op_point", "mode") if _amb else ("scenario", "corner")
            _hdr = (
                "# %s -- shipped evidence candidate (PAIRWISE PLAUSIBLE / MIS-TYPED).\n"
                "# consumed_netlist=netlist_v2.v  clock=clk_main  %s=%s  %s=%s\n"
                "# Right design (netlist_v2) + clock (clk_main); the role fields are SWAPPED (a corner value "
                "in the %s slot; a scenario value in the %s slot). PrimeTime signs off green here; semantic-"
                "role binding (C3+C4) is what rejects it.\n"
                % (_ra, _lscn, _stale_sc, _lcor, _stale_co, _lscn, _lcor))
        elif _is_ab:
            _hdr = (
                "# %s -- shipped evidence candidate (PAIRWISE PLAUSIBLE / MIS-TYPED).\n"
                "# consumed_netlist=netlist_v2.v  clock=clk_main  scenario=%s  corner=%s\n"
                "# Right design (netlist_v2) + clock (clk_main); scenario/corner are SWAPPED (a corner value "
                "in the scenario slot, a scenario value in the corner slot). PrimeTime signs off green here; "
                "typed binding (C3+C4) is what rejects it.\n" % (_ra, _stale_sc, _stale_co))
        else:
            _hdr = (
                "# %s -- shipped evidence candidate (PAIRWISE PLAUSIBLE / PARTIALLY TRUE).\n"
                "# consumed_netlist=netlist_v2.v  clock=clk_main  scenario=%s  corner=%s\n"
                "# Right design (netlist_v2) + clock (clk_main); WRONG scenario/corner vs the global "
                "authority / unique assignment.\n" % (_ra, _stale_sc, _stale_co))
        (task / "files" / _ra).write_text(_hdr + _body)
    shutil.rmtree(scratch)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="p14 workflow handoff generator (skeleton + bake)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--evidence-steps", type=int, default=1, choices=[1, 2])
    ap.add_argument("--hazard-type", default=None,
                    choices=[None, "cross_source_conflict", "scenario_corner_cross_source_conflict",
                             "multi_conflict_partially_truthful_decoy",
                             "constraint_graph_multi_source_recovery",
                             "axis_binding_value_invention",
                             "implicit_axis_binding",
                             SRB_HAZARD])
    ap.add_argument("--hint-level", type=int, default=1)
    ap.add_argument("--variant", default=None, choices=[None, SRB_AMBIGUOUS, SRB_CLEAR_CONTROL],
                    help="semantic_role_binding_reproduction variant (0009=ambiguous, 0010=clear_control)")
    ap.add_argument("--bake", action="store_true", help="also run the chain to bake golden evidence")
    ap.add_argument("--pt-cmd", default=os.environ.get("EDA_PT_CMD", "pt_shell"))
    a = ap.parse_args()
    td = build_task_skeleton(Path(a.out), a.task_id, a.seed, a.evidence_steps,
                             a.hazard_type, a.hint_level, variant=a.variant)
    print("skeleton:", td)
    if a.bake:
        bake_golden(td, a.pt_cmd, a.evidence_steps)
        print("baked golden evidence")
