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
def _flow_config(netlist: str, comment: str) -> str:
    return json.dumps({
        "_comment": comment,
        "netlist": netlist,
        "top_module": TOP,
        "constraints": "constraints.sdc",
        "library": "tiny.db",
        "scenario": SCENARIO,
        "corner": CORNER,
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
    fchecks = [
        ("consumed_is_authority", consumed == man_net, "%s vs %s" % (consumed, man_net)),
        ("consumed_is_expected", consumed == truth["expected_netlist"],
         "%s vs %s" % (consumed, truth["expected_netlist"])),
        ("provenance_integrity", consumed_disk == truth["expected_netlist_sha256"],
         "disk=%s" % consumed_disk[:12]),
        ("corner_matches", consumed_corner == man_corner, "%s vs %s" % (consumed_corner, man_corner)),
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
def _handoff_manifest(expected_netlist_sha: str) -> str:
    return json.dumps({
        "_comment": "Handoff package manifest -- the AUTHORITY/contract for what the evidence flow "
                    "must consume and what the fresh evidence chain must describe. Read-only and "
                    "FROZEN: current handoff is netlist v2 on clk_main, scenario func, corner typ. The "
                    "defect is in the lagging consumers + stale generated evidence, not here.",
        "design": TOP, "top_module": TOP,
        "clock": _CLOCK_PAIRS[0][0], "scenario": SCENARIO, "corner": CORNER, "library": "tiny.db",
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


def _spec_md(evidence_steps: int) -> str:
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


def _prompt_md(evidence_steps: int) -> str:
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


def _handoff_truth(evidence_steps: int, expected_sha: str, stale_sha: str) -> str:
    a_clk, s_clk = _CLOCK_PAIRS[0]
    return json.dumps({
        "_comment": "Hidden oracle metadata for p14 workflow handoff. Used ONLY inside "
                    "grade_workflow.py; never seen by the agent.",
        "evidence_steps": evidence_steps,
        "top_module": TOP,
        "expected_netlist": "netlist_v2.v", "expected_revision": "v2",
        "expected_netlist_sha256": expected_sha,
        "stale_netlist": "netlist_v1.v", "stale_netlist_sha256": stale_sha,
        "expected_clock": a_clk, "stale_clock": s_clk,
        "scenario": SCENARIO, "corner": CORNER, "library": "tiny.db",
        "required_ports": [a_clk, "din", "en", "dout"],
        "min_constrained_paths": 1, "clock_period_ns": PERIOD,
        "forbid_weakening": True,
        "manifest_netlist": "netlist_v2.v", "manifest_clock": a_clk,
    }, indent=2) + "\n"


def _metadata(task_id: str, seed: int, evidence_steps: int) -> dict:
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
    forbidden += hidden
    return {
        "task_id": task_id, "track": "p14_workflow_handoff", "tool": ["pt"],
        "difficulty": "hard", "data_type": "mutation_synthetic", "resource_preset": "standard",
        "timeout_sec": 600, "max_tool_calls": 60, "max_patch_attempts": 10, "max_output_tokens": 32000,
        "files": {"visible": visible, "editable": editable, "hidden": hidden, "forbidden": forbidden},
        "run_command": run_command,
        "scoring": {"weights": weights, "evaluator": "workflow_handoff.WorkflowHandoffEvaluator",
                    "explanation_weight": 0.10},
        "sanitizer": {"enabled": True},
        "generator": {"script": "p14_workflow_handoff_gen.py", "seed": seed,
                      "params": {"mechanism": "workflow_multistage_evidence_chain_handoff",
                                 "evidence_steps": evidence_steps,
                                 "expected_netlist": "netlist_v2.v", "expected_clock": _CLOCK_PAIRS[0][0],
                                 "stale_netlist": "netlist_v1.v", "stale_clock": _CLOCK_PAIRS[0][1],
                                 "scenario_corner": "%s/%s" % (SCENARIO, CORNER),
                                 "pass_gate": "SIGNOFF_OK AND EVIDENCE_OK AND FINAL_STATE_OK AND "
                                              "STAGE_CHAIN_OK AND PROVENANCE_OK AND no forbidden edits"}},
        "expected_error_category": "workflow_handoff_stale_evidence_chain_requires_ordered_rerun",
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


def build_task_skeleton(out_dir: Path, task_id: str, seed: int = 0, evidence_steps: int = 1) -> Path:
    """PURE (no tool). Write the full task directory in the MUTANT starting state.

    Deterministic: same (task_id, seed, evidence_steps) -> byte-identical tree. The initial evidence
    files are the STALE (v1/clk_old) run -- but since we cannot run the tool here, we seed them by
    copying the committed p13 stale evidence (for evidence_steps>=1) and, for stage 2, a STALE stage-2
    placeholder that the public runner reports as STALE. bake_golden() later produces the real golden
    evidence for solution/ via the tool.
    """
    if evidence_steps not in (1, 2):
        raise ValueError("evidence_steps must be 1 or 2")
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
    _write(files / "evidence_manifest.json", json.dumps(stale_mani, indent=2, sort_keys=True) + "\n")
    _write(files / "timing_report.rpt", (P13_SRC / "files/timing_report.rpt").read_text())

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
    _write(files / "handoff_manifest.json", _handoff_manifest(expected_sha))
    _write(files / "spec.md", _spec_md(evidence_steps))
    _write(task / "prompt.md", _prompt_md(evidence_steps))

    # hidden oracle
    _write(hidden / "grade_workflow.py", _GRADE_WORKFLOW)
    _write(hidden / "handoff_truth.json", _handoff_truth(evidence_steps, expected_sha, stale_sha))
    _write(hidden / "run_hidden.sh", _run_hidden_sh(evidence_steps), executable=True)
    _write(hidden / "regen_reference.sh", _regen_reference_sh(evidence_steps), executable=True)

    # GOLDEN inputs into solution/ (evidence baked later by bake_golden)
    _write(sol / "flow_config.json",
           _flow_config("netlist_v2.v", "Restored to current v2 netlist."))
    _write(sol / "constraints.sdc",
           _constraints(_CLOCK_PAIRS[0][0], "Restored to current clock clk_main; en is part of v2."))

    # metadata
    _write(task / "metadata.json", json.dumps(_metadata(task_id, seed, evidence_steps), indent=2) + "\n")
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
    shutil.rmtree(scratch)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="p14 workflow handoff generator (skeleton + bake)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--evidence-steps", type=int, default=1, choices=[1, 2])
    ap.add_argument("--bake", action="store_true", help="also run the chain to bake golden evidence")
    ap.add_argument("--pt-cmd", default=os.environ.get("EDA_PT_CMD", "pt_shell"))
    a = ap.parse_args()
    td = build_task_skeleton(Path(a.out), a.task_id, a.seed, a.evidence_steps)
    print("skeleton:", td)
    if a.bake:
        bake_golden(td, a.pt_cmd, a.evidence_steps)
        print("baked golden evidence")
