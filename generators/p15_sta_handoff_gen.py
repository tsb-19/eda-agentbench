#!/usr/bin/env python3
"""Family A generator — STA constraint/exception handoff (PrimeTime; track p15_sta_handoff).

Structurally independent SEMANTIC family over SHARED PT infrastructure (tiny.db/tiny.lib,
the 6-line read_db/link_design/read_sdc setup, the read_sdc/write_sdc launder, the
[apply]-prefix anti-injection pattern, EDA_PT_CMD resolution — all reused from P9/p14 and
disclosed as generic infrastructure, not as a claim of an independent technical stack).

Agent edits exception_config.json to bind (intent_class, target_partition, check_mode) by
reconciling an authority chain (intent.md / cdc_report.rpt / reset_report.rpt / scan_section /
signoff.log decoy). run_hidden translates the binding to an SDC exception, launders it, and
signs off; the design is marginally timed so ANY binding stays signoff-green — correctness is
provenance-attested (grade_sta_handoff.py), not slack-attested.

Two-phase: build_task_skeleton (pure, deterministic from seed) + bake_golden (real PT on b04).
Phase-5B: NO model calls. Real EDA-tool runs (PT) for golden/wrong-binding feasibility only.
"""
from __future__ import annotations
import json, os, random, shutil, subprocess, sys, hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBSTRATE = Path(__file__).resolve().parent / "p15_sta_handoff" / "substrate"
TRACK = "p15_sta_handoff"

# ---- frozen role space (typed-axis domains; the agent sees these via BundleS/TypedContract) ----
INTENTS = ["functional_close", "cdc_isolate", "reset_exempt", "scan_override"]
CHECK_MODES = ["setup", "hold", "both"]
# generic intent -> exception type (public; structural, not golden)
INTENT_EXCEPTION = {
    "cdc_isolate":   {"type": "false_path"},
    "reset_exempt":  {"type": "false_path"},
    "scan_override": {"type": "multicycle", "cycles": 2},
    "functional_close": {"type": "none"},
}
# legal check view per intent
LEGAL_VIEWS = {
    "cdc_isolate": "setup", "reset_exempt": "both", "scan_override": "both", "functional_close": "setup",
}


def _w(path, text):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


# ---------------- netlist + SDC ----------------
def gen_netlist(partitions, top="p15_sta_top"):
    """One register->buffer->register path per partition; all DFFX1/BUFX1 from tiny.db."""
    L = [f"// Family A STA handoff netlist (generated; timed vs tiny.db). Top: {top}.",
         f"// One register-to-register path per partition; marginally timed so any exception binding",
         f"// leaves report_timing green (tool success != semantic correctness).",
         f"module {top} (clk, {', '.join(p+'_in' for p in partitions)}, {', '.join(p+'_out' for p in partitions)});",
         "  input clk;"]
    L += [f"  input {p}_in;" for p in partitions]
    L += [f"  output {p}_out;" for p in partitions]
    for p in partitions:
        L += [f"  wire {p}_a, {p}_b;",
              f"  DFFX1 {p}_src (.D({p}_in), .CK(clk), .Q({p}_a));",
              f"  BUFX1 {p}_b0 (.A({p}_a), .Y({p}_b));",
              f"  DFFX1 {p}_dst (.D({p}_b), .CK(clk), .Q({p}_out));"]
    L.append("endmodule")
    return "\n".join(L) + "\n"


def gen_base_sdc(period=0.8, partitions=None):
    partitions = partitions or []
    L = [f"create_clock -name clk -period {period} [get_ports clk]",
         f"set_input_delay  0.05 -clock clk [get_ports {{ {' '.join(p+'_in' for p in partitions)} }}]",
         f"set_output_delay 0.05 -clock clk [get_ports {{ {' '.join(p+'_out' for p in partitions)} }}]"]
    return "\n".join(L) + "\n"


def partition_pins(partitions):
    return {p: {"from": f"{p}_src/Q", "to": f"{p}_dst/D"} for p in partitions}


# ---------------- truth (provenance DAG + coverage matrix) ----------------
def gen_truth(task_id, partitions, golden, wrong, decoy_recipe):
    """golden/wrong are (intent, partition, view). Build DAG + coverage matrix + exception maps."""
    g_intent, g_part, g_view = golden
    cov = {}
    cov.setdefault(g_part, {}).setdefault(g_view, {})[g_intent] = "requires_exception"
    truth = {
        "schema": "p15_signoff_intent_truth/v1",
        "task_id": task_id,
        "typed_axes": {
            "intent_class": INTENTS,
            "target_partition": partitions,
            "check_mode": CHECK_MODES,
        },
        "authority_nodes": [
            {"id": "INT", "artifact": "intent.md", "clause": "timing-intent", "trust": "primary"},
            {"id": "CDC", "artifact": "cdc_report.rpt", "clause": "crossing", "trust": "primary"},
            {"id": "RST", "artifact": "reset_report.rpt", "clause": "reset-domain", "trust": "primary"},
            {"id": "SCN", "artifact": "scan_section.md", "clause": "scan-mode", "trust": "primary"},
            {"id": "COV", "artifact": "coverage_matrix", "clause": "requires_exception", "trust": "derived"},
            {"id": "PRIOR", "artifact": "signoff.log", "clause": "prior-attest", "trust": "none"},
        ],
        "derivation_edges": [
            {"from": ["INT"], "to": {"intent_class": g_intent}, "rule": "primary intent"},
            {"from": ["CDC" if g_intent == "cdc_isolate" else ("RST" if g_intent == "reset_exempt" else "SCN")],
             "to": {"target_partition": g_part}, "rule": "crossing/reset/scan pin"},
            {"from": ["COV"], "to": {"check_mode": g_view}, "rule": "requires_exception cell"},
        ],
        "coverage_matrix": cov,
        "golden_binding": {"intent_class": g_intent, "target_partition": g_part, "check_mode": g_view},
        "wrong_binding_green": {"intent_class": wrong[0], "target_partition": wrong[1], "check_mode": wrong[2]},
        "legal_views_for_intent": LEGAL_VIEWS,
        "intent_exception": INTENT_EXCEPTION,
        "partition_pins": partition_pins(partitions),
        "decoy_sources": ["PRIOR"],
        "decoy_recipe": decoy_recipe,
        "masking_keywords": ["set_false_path", "set_multicycle_path"],
    }
    return truth


# ---------------- authority artifacts (condition-dependent labels) ----------------
def gen_authority_artifacts(truth, condition, partitions):
    """Base: overloaded 'timing_tag'; BundleS/TypedContract: canonical labels."""
    g = truth["golden_binding"]
    g_intent, g_part = g["intent_class"], g["target_partition"]
    canonical = condition in ("BundleS", "TypedContract")
    label = "intent_class/target_partition/check_mode" if canonical else "timing_tag"
    artifacts = {}
    # intent.md always attests the golden intent (primary)
    artifacts["intent.md"] = (f"# Timing intent (authority: INT, primary)\n"
                              f"The block's timing intent is **{g_intent}**.\n"
                              f" ({'canonical typed roles: ' + label if canonical else 'field label: ' + label})\n")
    # CDC report attests cdc partition (if cdc path exists)
    if "cdc" in partitions:
        cdc_part = g_part if g_intent == "cdc_isolate" else "cdc"
        artifacts["cdc_report.rpt"] = (f"# CDC crossing report (authority: CDC, primary)\n"
                                       f"Clock-domain crossing identified at partition: **{cdc_part}**.\n")
    if "reset" in partitions:
        rst_part = g_part if g_intent == "reset_exempt" else "reset"
        artifacts["reset_report.rpt"] = (f"# Reset-domain report (authority: RST, primary)\n"
                                         f"Reset exemption applies to partition: **{rst_part}**.\n")
    if "scan" in partitions:
        scan_part = g_part if g_intent == "scan_override" else "scan"
        artifacts["scan_section.md"] = (f"# Scan mode section (authority: SCN, primary)\n"
                                        f"Scan override applies to partition: **{scan_part}**.\n")
    # decoy prior signoff attests the WRONG binding (non-authoritative)
    w = truth["wrong_binding_green"]
    artifacts["signoff.log"] = (f"# Prior signoff log (NON-AUTHORITATIVE, stale)\n"
                                f"Prior run attested: intent={w['intent_class']} "
                                f"partition={w['target_partition']} view={w['check_mode']}.\n"
                                f"(This is a decoy; lower precedence than the primary authorities above.)\n")
    return artifacts


# ---------------- disclosure (condition-dependent, from frozen treatment mapping) ----------------
def gen_disclosure(truth, condition, partitions):
    g = truth["golden_binding"]
    if condition == "Base":
        return {}  # no BundleS/TypedContract files; artifacts carry overloaded 'timing_tag'
    domains = {
        "intent_class": INTENTS,
        "target_partition": partitions,
        "check_mode": CHECK_MODES,
    }
    common_facts = {
        "roles": ["intent_class", "target_partition", "check_mode"],
        "domains": domains,
        "disjoint_axes": True,
        "authority_sources": {"intent_class": "intent.md", "target_partition": "cdc_report|reset_report|scan_section",
                              "check_mode": "coverage matrix"},
        "provenance_precedence": ["INT(primary)", "CDC/RST/SCN(primary)", "COV(derived)", "PRIOR(none/decoy)"],
        "procedure": "Bind each role from its attesting primary/derived authority; tool signs green regardless, so correctness is provenance-attested.",
    }
    if condition == "BundleS":
        # natural-language/structured-prose disclosure (C1+C2+C4+C7)
        text = ("# Disclosure bundle (BundleS: C1+C2+C4+C7, non-answer-bearing)\n\n"
                "## C1 canonical labels + disjoint-axis declaration\n"
                f"Typed roles: {', '.join(common_facts['roles'])}. They are DISJOINT typed axes "
                "(a value on one axis does not satisfy another).\n\n"
                "## C2 value-domain definitions\n"
                + "\n".join(f"- {k} in {v}" for k, v in domains.items()) +
                "\n\n## C4 glossary + references\n"
                f"- intent_class: see {common_facts['authority_sources']['intent_class']}\n"
                f"- target_partition: see {common_facts['authority_sources']['target_partition']}\n"
                f"- check_mode: the coverage matrix requires_exception cell\n"
                f"Authority precedence: {', '.join(common_facts['provenance_precedence'])}\n\n"
                "## C7 procedural contract\n"
                f"{common_facts['procedure']}\n")
        return {"disclosure_bundles.md": text}
    if condition == "TypedContract":
        schema = {
            "schema": "p15_typed_contract/v1",
            "typed_axes": {r: {"type": "enum", "domain": domains[r]} for r in common_facts["roles"]},
            "disjoint_axes": True,
            "authority_sources": common_facts["authority_sources"],
            "provenance_precedence": common_facts["provenance_precedence"],
            "procedure": common_facts["procedure"],
        }
        return {"typed_contract.json": json.dumps(schema, indent=2) + "\n"}
    raise ValueError(condition)


# ---------------- run scripts (tcl + sh), templated from the proven PT recipe ----------------
RUN_PUBLIC_TCL = """\
# Public feedback: agent_applied.sdc is built by run_public.sh (build_applied_sdc.py);
# show real PrimeTime timing + active exceptions. FEEDBACK, not a verdict.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design.v
link_design {top}
read_sdc agent_applied.sdc
puts "=== SETUP VIOLATIONS (worst 10) ==="
report_timing -delay_type max -nworst 10 -slack_lesser_than 0.0
puts "=== TIMING EXCEPTIONS IN EFFECT ==="
report_exceptions
puts "PUBLIC_DONE"
exit
"""

RUN_LAUNDER_TCL = """\
# Hidden launder: read the agent-applied SDC, serialize the resolved constraint state.
set afh [open applied_hidden.sdc w]; close $afh
read_db tiny.db
set link_path "* tiny.db"
read_verilog design.v
link_design {top}
catch {{ read_sdc agent_applied.sdc }}
write_sdc -nosplit applied_hidden.sdc
exit
"""

RUN_SIGNOFF_TCL = """\
# Hidden signoff on the laundered (trusted) SDC. Zero constrained paths => FAIL.
read_db tiny.db
set link_path "* tiny.db"
read_verilog design.v
link_design {top}
read_sdc applied_hidden.sdc
set wp [get_timing_paths -delay_type max -nworst 1]
if {{[sizeof_collection $wp] == 0}} {{
    puts "SIGNOFF_FAIL worst_slack=NONE no_paths"
}} else {{
    set s [get_attribute [index_collection $wp 0] slack]
    if {{$s >= -0.001}} {{ puts "SIGNOFF_OK worst_slack=$s" }} else {{ puts "SIGNOFF_FAIL worst_slack=$s" }}
}}
exit
"""

BUILD_APPLIED_SDC_PY = """\
# Public: translate exception_config.json (+ partition_pins.json + intent_exception.json)
# into agent_applied.sdc. Deterministic; same logic run_public and run_hidden use.
import json
cfg = json.load(open("exception_config.json"))
pins = json.load(open("partition_pins.json"))["partition_pins"]
iexc = json.load(open("intent_exception.json"))["intent_exception"]
base = open("constraints.sdc").read().splitlines()
lines = [l for l in base]
intent = cfg.get("intent_class"); part = cfg.get("target_partition")
exc = iexc.get(intent, {"type": "none"})
if exc.get("type") == "false_path" and part in pins:
    lines.append("set_false_path -from [get_pins %s] -to [get_pins %s]" % (pins[part]["from"], pins[part]["to"]))
elif exc.get("type") == "multicycle" and part in pins:
    lines.append("set_multicycle_path %d -setup -from [get_pins %s] -to [get_pins %s]"
                 % (exc.get("cycles", 2), pins[part]["from"], pins[part]["to"]))
open("agent_applied.sdc", "w").write("\\n".join(lines) + "\\n")
"""

RUN_PUBLIC_SH = """\
#!/bin/bash
# Public feedback runner (iterate as much as you like). Translates your exception_config
# binding to an SDC exception, then reports real PrimeTime timing + active exceptions.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"; exit 0; fi
PY_CMD="${EDA_PY_CMD:-python3}"
"$PY_CMD" build_applied_sdc.py
"$PT_CMD" -f run_public.tcl 2>&1
exit 0
"""

RUN_HIDDEN_SH = """\
#!/bin/bash
# Hidden grader (forge-resistant, two-phase). Runs in the FLATTENED evaluator workspace
# (files/ + hidden/ co-located). Writes signoff_result.json, then emits grade markers.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo '{"signoff_green": false, "fatal": "pt_shell not found"}' > signoff_result.json; exit 0; fi
"$PY_CMD" build_applied_sdc.py
# Phase 1: launder (output [apply]-prefixed so an injected marker cannot match ^marker)
APPLY_OUT="$("$PT_CMD" -f run_launder.tcl 2>&1)"; echo "$APPLY_OUT" | sed 's/^/[apply] /'
# Phase 2: signoff on laundered SDC
SIGN_OUT="$("$PT_CMD" -f run_signoff.tcl 2>&1)"
SIGN_LINE=$(echo "$SIGN_OUT" | grep -E '^SIGNOFF_OK|^SIGNOFF_FAIL' || echo 'SIGNOFF_FAIL worst_slack=NONE no_marker')
SLACK=$(echo "$SIGN_LINE" | sed -E 's/.*worst_slack=([-0-9.]+|NONE).*/\\1/')
GREEN=$(echo "$SIGN_LINE" | grep -q '^SIGNOFF_OK' && echo true || echo false)
AEX=$(grep -cE 'set_false_path|set_multicycle_path' applied_hidden.sdc 2>/dev/null || echo 0)
cat > signoff_result.json <<JSON
{"signoff_green": $GREEN, "worst_slack": "$SLACK", "applied_exception_lines": $AEX, "expected_exception_lines": 1, "signoff_line": "$SIGN_LINE"}
JSON
# Phase 3: provenance/authority grade (python; reads truth + signoff_result + applied_hidden.sdc from cwd)
"$PY_CMD" grade_sta_handoff.py
exit 0
"""


# ---------------- skeleton ----------------
def build_task_skeleton(out, task_id, seed, golden, wrong, condition, decoy_recipe="default"):
    rng = random.Random(seed)
    partitions = ["cdc", "reset", "scan", "core"]
    top = "p15_sta_top"
    truth = gen_truth(task_id, partitions, golden, wrong, decoy_recipe)
    files = out / "files"; hidden = out / "hidden"; sol = out / "solution"
    files.mkdir(parents=True, exist_ok=True); hidden.mkdir(parents=True, exist_ok=True); sol.mkdir(parents=True, exist_ok=True)
    # shared PT library (generic infrastructure)
    shutil.copy(SUBSTRATE / "tiny.db", files / "tiny.db"); shutil.copy(SUBSTRATE / "tiny.lib", files / "tiny.lib")
    _w(files / "design.v", gen_netlist(partitions, top))
    _w(files / "constraints.sdc", gen_base_sdc(0.8, partitions))
    # editable: ships the WRONG (plausible, green) binding; agent repairs to golden
    _w(files / "exception_config.json", json.dumps({
        "_comment": "STA exception binding (editable). Ships a plausible-but-wrong binding; repair to the provenance-attested binding.",
        "intent_class": wrong[0], "target_partition": wrong[1], "check_mode": wrong[2]}, indent=2) + "\n")
    _w(files / "partition_pins.json", json.dumps({"partition_pins": partition_pins(partitions)}, indent=2) + "\n")
    _w(files / "intent_exception.json", json.dumps({"intent_exception": INTENT_EXCEPTION}, indent=2) + "\n")
    _w(files / "build_applied_sdc.py", BUILD_APPLIED_SDC_PY)
    _w(files / "run_public.tcl", RUN_PUBLIC_TCL.format(top=top))
    _w(files / "run_public.sh", RUN_PUBLIC_SH); os.chmod(files / "run_public.sh", 0o755)
    for name, text in gen_authority_artifacts(truth, condition, partitions).items():
        _w(files / name, text)
    for name, text in gen_disclosure(truth, condition, partitions).items():
        _w(files / name, text)
    # prompt
    _w(out / "prompt.md", gen_prompt(task_id, condition))
    _w(out / "metadata.json", json.dumps(gen_metadata(task_id, condition, golden), indent=2) + "\n")
    # hidden
    _w(hidden / "signoff_intent_truth.json", json.dumps(truth, indent=2) + "\n")
    shutil.copy(SUBSTRATE.parent / "grade_sta_handoff.py", hidden / "grade_sta_handoff.py")
    _w(hidden / "run_launder.tcl", RUN_LAUNDER_TCL.format(top=top))
    _w(hidden / "run_signoff.tcl", RUN_SIGNOFF_TCL.format(top=top))
    _w(hidden / "run_hidden.sh", RUN_HIDDEN_SH); os.chmod(hidden / "run_hidden.sh", 0o755)
    # solution
    _w(sol / "exception_config.json", json.dumps({
        "intent_class": golden[0], "target_partition": golden[1], "check_mode": golden[2]}, indent=2) + "\n")
    return truth


def gen_prompt(task_id, condition):
    amb = condition == "Base"
    role_line = ("The reports use an overloaded field `timing_tag`; resolve the typed roles "
                 "(intent / partition / view) from the authority intersection."
                 if amb else "Canonical typed roles `intent_class` / `target_partition` / `check_mode` are stated; "
                 "see disclosure_bundles.md." if condition == "BundleS" else
                 "A machine-readable typed contract `typed_contract.json` declares the roles, domains, and authority precedence.")
    return (f"# Task {task_id}: STA timing-exception signoff handoff\n\n"
            f"You own static-timing signoff. Reconcile the timing-exception intent from the authority chain and "
            f"bind it in `exception_config.json` as (intent_class, target_partition, check_mode). {role_line}\n\n"
            f"The design is marginally timed and healthy: `report_timing` is GREEN regardless of which exception you "
            f"bind — so a clean signoff is necessary but NOT sufficient. Correctness is provenance-attested: the "
            f"binding must match the primary authorities (intent.md / cdc_report / reset_report / scan_section), not "
            f"the stale prior signoff.log.\n\n"
            f"Edit `exception_config.json`, run `bash run_public.sh` for feedback, iterate, then finalize.\n")


def gen_metadata(task_id, condition, golden):
    return {
        "task_id": task_id, "track": TRACK, "tool": ["pt"], "difficulty": "hard",
        "data_type": "flow_synthetic", "resource_preset": "standard", "timeout_sec": 300,
        "max_tool_calls": 30, "max_patch_attempts": 8, "max_output_tokens": 32000,
        "condition": condition,
        "files": {"visible": ["design.v", "constraints.sdc", "exception_config.json", "partition_pins.json",
                              "intent_exception.json", "build_applied_sdc.py", "run_public.sh", "run_public.tcl",
                              "intent.md", "cdc_report.rpt", "reset_report.rpt", "scan_section.md", "signoff.log",
                              "tiny.db", "tiny.lib"],
                  "editable": ["exception_config.json"],
                  "hidden": ["signoff_intent_truth.json", "grade_sta_handoff.py", "run_hidden.sh",
                             "run_launder.tcl", "run_signoff.tcl"],
                  "forbidden": ["design.v", "constraints.sdc", "run_public.sh", "run_public.tcl", "tiny.db", "tiny.lib",
                                "signoff_intent_truth.json", "grade_sta_handoff.py", "run_hidden.sh"]},
        "run_command": "bash run_public.sh",
        "scoring": {"weights": {"provenance_attested": 0.30, "coverage_cell_consistent": 0.20, "check_view_legal": 0.10,
                                "pt_signoff_green": 0.10, "not_masking": 0.15, "explanation": 0.15},
                    "evaluator": "sta_handoff.STAHandoffEvaluator"},
        "generator": {"script": "p15_sta_handoff_gen.py", "condition": condition},
        "version": "1.0.0",
    }


# ---------------- bake (real PT) + hard-feasibility gate ----------------
def _run_pt(cmd, cwd, env, timeout=240):
    return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)


def bake_golden(task_dir, env):
    """Stage a FLAT evaluator workspace (files/+hidden/ co-located), run real PT for golden and
    wrong bindings, collect signoff + grade markers. Mirrors the harness grade-time layout."""
    files = task_dir / "files"; hidden = task_dir / "hidden"
    truth = json.loads((hidden / "signoff_intent_truth.json").read_text())
    pt = env["EDA_PT_CMD"]
    import tempfile
    stage = Path(tempfile.mkdtemp(prefix="p15_bake_"))
    # flatten files/ + hidden/ into the stage (the evaluator-workspace contract)
    shutil.copytree(files, stage, dirs_exist_ok=True)
    shutil.copytree(hidden, stage, dirs_exist_ok=True)
    results = {}
    for label, binding in (("golden", truth["golden_binding"]), ("wrong", truth["wrong_binding_green"])):
        (stage / "exception_config.json").write_text(json.dumps(binding, indent=2) + "\n")
        _run_pt(["python3", "build_applied_sdc.py"], cwd=stage, env=env)
        _run_pt([pt, "-f", "run_launder.tcl"], cwd=stage, env=env)
        sig = _run_pt([pt, "-f", "run_signoff.tcl"], cwd=stage, env=env)
        so = sig.stdout + "\n" + sig.stderr
        sign_line = next((l for l in so.splitlines() if l.startswith(("SIGNOFF_OK", "SIGNOFF_FAIL"))),
                         "SIGNOFF_FAIL worst_slack=NONE no_marker")
        green = sign_line.startswith("SIGNOFF_OK")
        aex = sum(1 for l in (stage / "applied_hidden.sdc").read_text().splitlines()
                  if l.strip().startswith(("set_false_path", "set_multicycle_path")))
        (stage / "signoff_result.json").write_text(json.dumps({
            "signoff_green": green, "applied_exception_lines": aex, "expected_exception_lines": 1,
            "signoff_line": sign_line}) + "\n")
        g = _run_pt(["python3", "grade_sta_handoff.py"], cwd=stage, env=env)
        try:
            markers = json.loads(g.stdout)
        except Exception:
            markers = {"fatal": "grade_failed", "stdout": g.stdout[-400:], "stderr": g.stderr[-400:]}
        results[label] = {"binding": binding, "signoff_line": sign_line, "signoff_green": green, "markers": markers}
    # persist wrong-binding feasibility evidence into the instance hidden/ dir
    (hidden / "wrong_binding_signoff.rpt").write_text(
        "# wrong_binding_green signoff evidence (real PT on b04)\n" + results["wrong"]["signoff_line"] + "\n"
        + "# markers: " + json.dumps(results["wrong"]["markers"].get("checks", {})) + "\n")
    shutil.rmtree(stage, ignore_errors=True)
    return results


def hard_feasibility(results):
    """5-criterion gate on the wrong binding (amendment 4)."""
    w = results["wrong"]; m = w["markers"].get("checks", {}); sl = w["signoff_line"]
    gate = {
        "wrong_tool_syntax_accepted": "no_marker" not in sl,                       # (a) tool syntax accepted
        "wrong_executes_finds_nonzero_paths": "no_paths" not in sl,                # (b) executes, nonzero paths
        "wrong_plausible_signoff_green": bool(w["signoff_green"]),                 # (c) plausible signoff
        "wrong_remains_semantically_wrong": not m.get("semantic_binding", False),  # (d) semantically wrong
        "wrong_rejected_by_provenance_not_PT": (not m.get("provenance_attested", True)) and bool(w["signoff_green"]),  # (e)
    }
    gate["PASS"] = all(gate.values())
    return gate


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id", default="p15_dev_0000")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--golden", default="cdc_isolate,cdc,setup")
    ap.add_argument("--wrong", default="cdc_isolate,core,setup")
    ap.add_argument("--condition", default="BundleS", choices=["Base", "BundleS", "TypedContract"])
    ap.add_argument("--out-root", default=str(REPO / "tasks" / TRACK))
    ap.add_argument("--bake", action="store_true")
    args = ap.parse_args()
    g = tuple(args.golden.split(",")); w = tuple(args.wrong.split(","))
    out = Path(args.out_root) / args.task_id
    if out.exists():
        shutil.rmtree(out)
    truth = build_task_skeleton(out, args.task_id, args.seed, g, w, args.condition)
    print(json.dumps({"built": str(out), "golden": truth["golden_binding"], "wrong": truth["wrong_binding_green"]}, indent=2))
    if args.bake:
        env = dict(os.environ)
        env["EDA_TOOL_ROOT"] = "/data1/tongsb/eda-remote-shim/EDA"
        env["B04_HOST"] = "tsb@b04"
        env["EDA_PT_CMD"] = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/prime/V-2023.12/bin/pt_shell"
        res = bake_golden(out, env)
        gate = hard_feasibility(res)
        (out / "hidden" / "bake_results.json").write_text(json.dumps({"results": res, "hard_feasibility": gate}, indent=2) + "\n")
        print(json.dumps({"hard_feasibility": gate, "golden_signoff_green": res['golden']['signoff_green'],
                          "wrong_signoff_green": res['wrong']['signoff_green'],
                          "wrong_green_but_unattested": res['wrong']['markers'].get('green_but_unattested')}, indent=2))


if __name__ == "__main__":
    main()
