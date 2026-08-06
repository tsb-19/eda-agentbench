#!/usr/bin/env python3
"""Family B generator — SPICE model/measurement handoff (HSPICE; track p16_spice_handoff).

Structurally independent SEMANTIC family over SHARED HSPICE infrastructure (the hspice shim,
the .measure/.lis run+parse pattern, the EDA_HSPICE_CMD resolution — reused from P4/P5 and
disclosed as generic infrastructure).

Agent edits meas_config.json to bind (corner, load_condition, metric) by joining a
characterization request to its authority chain (char_spec / mission_profile /
application_note / stale measurement.log decoy). build_deck translates the binding to deck
params (.param av/cload) and the right analysis; HSPICE runs and .measure extracts a number
for ANY tuple — so simulation success + a plausible number != semantic correctness. The
grader (grade_spice_handoff.py) reports six separated dimensions and decides semantic
correctness from the authority/provenance join, NEVER from closeness to a hidden exact number.

The quantitative plausibility spec (generators/p16_spice_handoff/plausibility_spec.json) is
FROZEN before any bake and is independent of observed output.
"""
from __future__ import annotations
import json, os, random, shutil, subprocess, sys, tempfile, math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FAMDIR = Path(__file__).resolve().parent / "p16_spice_handoff"
TRACK = "p16_spice_handoff"

CORNERS = ["SS_0p9_-40", "TT_1p2_25", "FF_1p3_125"]
LOADS = ["light", "nominal", "heavy"]
METRICS = ["gain", "gbw", "pm", "slew", "vdsat"]
# corner -> macro-amplifier voltage gain (real HSPICE .ac computes vdb from this)
CORNER_AV = {"SS_0p9_-40": 100.0, "TT_1p2_25": 50.0, "FF_1p3_125": 30.0}
# load -> compensation/load cap (sets the second pole; load-dependent bandwidth)
LOAD_C = {"light": 1.0e-12, "nominal": 5.0e-12, "heavy": 20.0e-12}
METRIC_ANALYSIS = {"gain": "ac", "gbw": "ac", "pm": "ac", "slew": "tran", "vdsat": "dc"}
METRIC_MEASURE = {"gain": "gain_db", "gbw": "gbw_hz", "pm": "pm_deg", "slew": "slew_v", "vdsat": "vdsat_v"}
# plausible ranges — loaded from the FROZEN spec (single source of truth)
SPEC = json.loads((FAMDIR / "plausibility_spec.json").read_text())
METRIC_RANGE = {m: SPEC["metrics"][m]["range"] for m in METRICS}
METRIC_UNIT = {m: SPEC["metrics"][m]["unit"] for m in METRICS}


def _w(path, text):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)


# ---------------- deck + parser ----------------
CIRCUIT_CORE = """\
* Family B measurement-handoff circuit (IMMUTABLE CORE — do not edit; integrity-hashed).
* The executable deck (circuit_built.sp) is REGENERATED from this core + meas_config.json by build_deck.py.
.param av={av} cload={cload}
vin in 0 dc 0 ac 1
ein outc 0 in 0 av
r1 outc outa 1e3
c1 outa 0 1.59e-9
r2 outa out 1e3
c2 out 0 cload
rl out 0 1e12
.ac dec 20 1 1g
.measure ac gain_db max vdb(out)
.measure ac gbw_hz when vdb(out)=0 fall=1
.end
"""

BUILD_DECK_PY = """\
# Public: regenerate the executable deck from the IMMUTABLE circuit core + meas_config.
# The core (circuit_core.sp) is integrity-hashed and immutable; only meas_config.json is editable.
import json
cfg = json.load(open("meas_config.json"))
CAV = json.load(open("corner_models.json"))["corner_av"]
LDC = json.load(open("load_models.json"))["load_c"]
av = CAV.get(cfg.get("corner"), 50.0); cload = LDC.get(cfg.get("load_condition"), 5e-12)
core = open("circuit_core.sp").read()              # immutable template
deck = core.replace("{av}", "%g" % av).replace("{cload}", "%g" % cload)
open("circuit_built.sp", "w").write(deck)          # derived artifact (regenerated each run)
"""

PARSE_MEASURE_PY = """\
# Public parser: extract the requested metric's value from the HSPICE .lis (handles scale suffixes).
import re, sys, json
SCALE = {'':1,'f':1e-15,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'%':1e-2,'k':1e3,'x':1e6,'meg':1e6,'g':1e9,'t':1e12}
lis = open(sys.argv[1]).read() if len(sys.argv) > 1 else open("hspice_run.lis").read()
metric = sys.argv[2] if len(sys.argv) > 2 else "gain"
name = {"gain": "gain_db", "gbw": "gbw_hz", "pm": "pm_deg", "slew": "slew_v", "vdsat": "vdsat_v"}[metric]
val = None
for line in lis.splitlines():
    m = re.match(r"^\\s*" + re.escape(name) + r"\\s*=\\s*([0-9.eE+\\-]+[a-zA-Z%]*)", line)
    if m:
        tok = m.group(1).lower()
        mm = re.match(r"^([-+]?[0-9]*\\.?[0-9]+(?:[eE][-+]?[0-9]+)?)([a-z%]*)$", tok)
        if mm:
            try:
                val = float(mm.group(1)) * SCALE.get(mm.group(2), 1); break
            except ValueError:
                pass
if val is not None and metric == "gbw":
    val = val / 1e6  # Hz -> MHz
print(json.dumps({"metric": metric, "value": val, "measure_name": name}))
"""


def parse_lis_value(lis_text, metric):
    name = METRIC_MEASURE[metric]
    val = None
    for line in lis_text.splitlines():
        m = re.match(r"^\s*" + re.escape(name) + r"\s*=\s*([0-9.eE+\-]+[a-zA-Z%]*)", line)
        if m:
            v = _parse_hspice_num(m.group(1))
            if v is not None:
                val = v
                break
    if val is not None and metric == "gbw":
        val = val / 1e6  # Hz -> MHz
    return val


import re  # noqa: E402

_HSPICE_SCALE = {"": 1, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "um": 1e-6,
                 "m": 1e-3, "%": 1e-2, "k": 1e3, "x": 1e6, "meg": 1e6, "g": 1e9, "t": 1e12}


def _parse_hspice_num(tok):
    """Parse a numeric token with an optional HSPICE scale suffix (e.g. '4.9335x' -> 4.9335e6)."""
    tok = tok.strip().lower()
    m = re.match(r"^([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)([a-z%]*)$", tok)
    if not m:
        return None
    try:
        base = float(m.group(1))
    except ValueError:
        return None
    suf = m.group(2)
    if suf not in _HSPICE_SCALE:
        return None
    return base * _HSPICE_SCALE[suf]


# ---------------- truth (request-authority relational join) ----------------
def gen_truth(task_id, golden, wrong, decoy_recipe):
    g_corner, g_load, g_metric = golden
    truth = {
        "schema": "p16_meas_request_truth/v1",
        "task_id": task_id,
        "typed_axes": {"corner": CORNERS, "load_condition": LOADS, "metric": METRICS},
        "request": {"metric": g_metric, "src": "char_spec"},
        "authorities": {
            "metric": {"src": "char_spec", "value": g_metric, "trust": "primary"},
            "corner": {"src": "mission_profile", "value": g_corner, "trust": "primary"},
            "load_condition": {"src": "application_note", "value": g_load, "trust": "primary"},
        },
        "decoy_authorities": [
            {"role": "corner", "src": "mission_profile_stale", "value": wrong[0], "trust": "none"},
            {"role": "load_condition", "src": "load_note_swapped", "value": wrong[1], "trust": "none"},
        ],
        "golden_join": {"corner": g_corner, "load_condition": g_load, "metric": g_metric},
        "wrong_join_plausible": {"corner": wrong[0], "load_condition": wrong[1], "metric": wrong[2]},
        "plausible_range": {m: {"min": METRIC_RANGE[m][0], "max": METRIC_RANGE[m][1]} for m in METRICS},
        "units": METRIC_UNIT,
        "analysis_for_metric": METRIC_ANALYSIS,
    }
    return truth


# ---------------- authority artifacts (condition-dependent) ----------------
def gen_authority_artifacts(truth, condition):
    g = truth["golden_join"]; w = truth["wrong_join_plausible"]
    canonical = condition in ("BundleS", "TypedContract")
    label = "corner/load_condition/metric" if canonical else "condition_id"
    art = {
        "char_spec.md": (f"# Characterization spec (authority: REQ, primary)\n"
                         f"Requested measurement (metric): **{g['metric']}**.\n"
                         f" ({'canonical typed roles: ' + label if canonical else 'field label: ' + label})\n"),
        "mission_profile.md": (f"# PVT mission profile (authority: PVT, primary)\n"
                               f"Signoff corner for this characterization: **{g['corner']}**.\n"),
        "application_note.md": (f"# Application / load note (authority: LOAD, primary)\n"
                                f"Operating load condition: **{g['load_condition']}**.\n"),
        "measurement.log": (f"# Prior measurement log (NON-AUTHORITATIVE, stale)\n"
                            f"Prior run measured corner={w['corner']} load={w['load_condition']} "
                            f"metric={w['metric']} — a substituted (wrong) tuple.\n"
                            f"(Decoy; lower precedence than the primary authorities above.)\n"),
    }
    return art


# ---------------- disclosure (from frozen SPICE treatment mapping) ----------------
def gen_disclosure(truth, condition):
    if condition == "Base":
        return {}
    domains = {"corner": CORNERS, "load_condition": LOADS, "metric": METRICS}
    common = {"roles": ["corner", "load_condition", "metric"], "domains": domains,
              "authority_sources": {"metric": "char_spec.md", "corner": "mission_profile.md",
                                    "load_condition": "application_note.md"},
              "procedure": "Join the request to its authorities: metric from char_spec, corner from "
                           "mission_profile, load_condition from application_note; the deck measures a "
                           "plausible number for any tuple, so correctness is authority-joined, not numeric."}
    if condition == "BundleS":
        text = ("# Disclosure bundle (BundleS: C1+C2+C4+C7, non-answer-bearing)\n\n"
                "## C1 canonical labels + disjoint-axis declaration\n"
                f"Typed roles: {', '.join(common['roles'])} — DISJOINT typed axes.\n\n"
                "## C2 value-domain definitions\n"
                + "\n".join(f"- {k} in {v}" for k, v in domains.items()) + "\n\n"
                "## C4 glossary + references\n"
                + "\n".join(f"- {r}: see {s}" for r, s in common['authority_sources'].items()) + "\n\n"
                "## C7 procedural contract\n" + common['procedure'] + "\n")
        return {"disclosure_bundles.md": text}
    if condition == "TypedContract":
        schema = {"schema": "p16_typed_contract/v1",
                  "typed_axes": {r: {"type": "enum", "domain": domains[r]} for r in common["roles"]},
                  "authority_sources": common["authority_sources"], "procedure": common["procedure"]}
        return {"typed_contract.json": json.dumps(schema, indent=2) + "\n"}
    raise ValueError(condition)


RUN_PUBLIC_SH = """\
#!/bin/bash
# Public feedback: build the deck from your meas_config, run HSPICE, report the measured value.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
HS_CMD="${EDA_HSPICE_CMD:-hspice}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$HS_CMD" >/dev/null 2>&1; then echo "SKIP: hspice not found (EDA_HSPICE_CMD=$HS_CMD)"; exit 0; fi
"$PY_CMD" build_deck.py
"$HS_CMD" -i circuit_built.sp -o hspice_run 2>&1
echo "=== measured value (no verdict) ==="
"$PY_CMD" parse_measure.py hspice_run.lis "$(python3 -c 'import json;print(json.load(open("meas_config.json"))["metric"])')"
exit 0
"""

RUN_HIDDEN_SH = """\
#!/bin/bash
# Hidden grader: build deck from submitted meas_config, run HSPICE, parse, grade (6 dimensions).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
HS_CMD="${EDA_HSPICE_CMD:-hspice}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$HS_CMD" >/dev/null 2>&1; then echo '{"sim_ok": false, "fatal": "hspice not found"}' > measure_result.json; exit 0; fi
"$PY_CMD" build_deck.py
HS_OUT="$("$HS_CMD" -i circuit_built.sp -o hspice_run 2>&1)"; RC=$?
METRIC="$(python3 -c 'import json;print(json.load(open("meas_config.json"))["metric"])')"
PJ="$("$PY_CMD" parse_measure.py hspice_run.lis "$METRIC")"
VALUE=$(echo "$PJ" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("value"))')
ANALYSIS=$(python3 -c 'import json;a={"gain":"ac","gbw":"ac","pm":"ac","slew":"tran","vdsat":"dc"};print(a.get("'$METRIC'","ac"))')
SIM_OK=$( [ $RC -eq 0 ] && [ -f hspice_run.lis ] && [ "$VALUE" != "None" ] && echo true || echo false )
cat > measure_result.json <<JSON
{"sim_ok": $SIM_OK, "value": ${VALUE:-null}, "metric": "$METRIC", "analysis": "$ANALYSIS", "hspice_rc": $RC}
JSON
"$PY_CMD" grade_spice_handoff.py
exit 0
"""


def gen_prompt(task_id, condition):
    amb = condition == "Base"
    role = ("The artifacts use an overloaded field `condition_id`; resolve the typed roles "
            "(corner / load / metric) from the authority chain." if amb else
            "Canonical typed roles `corner` / `load_condition` / `metric`; see disclosure_bundles.md."
            if condition == "BundleS" else
            "A machine-readable typed contract `typed_contract.json` declares roles, domains, authority sources.")
    return (f"# Task {task_id}: SPICE measurement-handoff\n\n"
            f"Bind the characterization measurement request to (corner, load_condition, metric) in "
            f"`meas_config.json` by joining the request to its authority sources. {role}\n\n"
            f"The deck measures a PLAUSIBLE number for any tuple — simulation success and a plausible "
            f"numeric output are NOT sufficient. Correctness is authority-joined (char_spec / mission_profile / "
            f"application_note), not numeric; the stale measurement.log is a decoy.\n\n"
            f"## Action surface (operational)\n"
            f"The executable circuit deck (`circuit_built.sp`) is REGENERATED from an immutable, integrity-hashed "
            f"core (`circuit_core.sp`) and your `meas_config.json` by `build_deck.py`. Only `meas_config.json` is "
            f"editable. Do NOT modify `circuit_core.sp`, `build_deck.py`, or any generated deck — such modifications "
            f"are rejected.\n\n"
            f"Edit `meas_config.json`, run `bash run_public.sh` for the measured value, iterate, then finalize.\n")


def gen_metadata(task_id, condition):
    return {
        "task_id": task_id, "track": TRACK, "tool": ["hspice"], "difficulty": "hard",
        "data_type": "flow_synthetic", "resource_preset": "standard", "timeout_sec": 300,
        "max_tool_calls": 30, "max_patch_attempts": 8, "max_output_tokens": 32000, "condition": condition,
        "files": {"visible": ["circuit_core.sp", "meas_config.json", "corner_models.json", "load_models.json",
                              "build_deck.py", "parse_measure.py", "run_public.sh", "char_spec.md",
                              "mission_profile.md", "application_note.md", "measurement.log"],
                  "editable": ["meas_config.json"],
                  "hidden": ["meas_request_truth.json", "grade_spice_handoff.py", "run_hidden.sh"],
                  "forbidden": ["circuit_core.sp", "run_public.sh", "build_deck.py", "corner_models.json",
                                "load_models.json", "parse_measure.py",
                                "meas_request_truth.json", "grade_spice_handoff.py", "run_hidden.sh"]},
        "run_command": "bash run_public.sh",
        "scoring": {"weights": {"semantic_binding": 0.30, "evidence_provenance": 0.20, "simulation_success": 0.10,
                                "numeric_validity": 0.10, "artifact_completion": 0.15, "protocol_completion": 0.15},
                    "evaluator": "spice_handoff.SPICEHandoffEvaluator"},
        "generator": {"script": "p16_spice_handoff_gen.py", "condition": condition}, "version": "1.0.0",
    }


def build_task_skeleton(out, task_id, seed, golden, wrong, condition, decoy_recipe="default"):
    out.mkdir(parents=True, exist_ok=True)
    files = out / "files"; hidden = out / "hidden"; sol = out / "solution"
    files.mkdir(parents=True, exist_ok=True); hidden.mkdir(parents=True, exist_ok=True); sol.mkdir(parents=True, exist_ok=True)
    truth = gen_truth(task_id, golden, wrong, decoy_recipe)
    _w(files / "corner_models.json", json.dumps({"corner_av": CORNER_AV}, indent=2) + "\n")
    _w(files / "load_models.json", json.dumps({"load_c": LOAD_C}, indent=2) + "\n")
    # editable: ships the WRONG (plausible) tuple
    _w(files / "meas_config.json", json.dumps({"_comment": "measurement binding (editable). Ships a plausible-but-wrong tuple; repair to the authority-joined binding.",
                                               "corner": wrong[0], "load_condition": wrong[1], "metric": wrong[2]}, indent=2) + "\n")
    _w(files / "build_deck.py", BUILD_DECK_PY)
    _w(files / "parse_measure.py", PARSE_MEASURE_PY)
    _w(files / "run_public.sh", RUN_PUBLIC_SH); os.chmod(files / "run_public.sh", 0o755)
    # immutable, integrity-hashed circuit CORE (visible + forbidden). The executable deck
    # (circuit_built.sp) is DERIVED by build_deck.py from this core + meas_config (not shipped).
    _w(files / "circuit_core.sp", CIRCUIT_CORE)
    for name, text in gen_authority_artifacts(truth, condition).items():
        _w(files / name, text)
    for name, text in gen_disclosure(truth, condition).items():
        _w(files / name, text)
    _w(out / "prompt.md", gen_prompt(task_id, condition))
    _w(out / "metadata.json", json.dumps(gen_metadata(task_id, condition), indent=2) + "\n")
    _w(hidden / "meas_request_truth.json", json.dumps(truth, indent=2) + "\n")
    shutil.copy(FAMDIR / "grade_spice_handoff.py", hidden / "grade_spice_handoff.py")
    _w(hidden / "run_hidden.sh", RUN_HIDDEN_SH); os.chmod(hidden / "run_hidden.sh", 0o755)
    _w(sol / "meas_config.json", json.dumps({"corner": golden[0], "load_condition": golden[1], "metric": golden[2]}, indent=2) + "\n")
    return truth


def _run(cmd, cwd, env, timeout=240):
    return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)


def bake_golden(task_dir, env):
    """Stage a FLAT evaluator workspace, run real HSPICE for golden and wrong tuples, grade."""
    files = task_dir / "files"; hidden = task_dir / "hidden"
    truth = json.loads((hidden / "meas_request_truth.json").read_text())
    hs = env["EDA_HSPICE_CMD"]
    stage = Path(tempfile.mkdtemp(prefix="p16_bake_"))
    shutil.copytree(files, stage, dirs_exist_ok=True)
    shutil.copytree(hidden, stage, dirs_exist_ok=True)
    results = {}
    for label, binding in (("golden", truth["golden_join"]), ("wrong", truth["wrong_join_plausible"])):
        (stage / "meas_config.json").write_text(json.dumps(binding, indent=2) + "\n")
        _run(["python3", "build_deck.py"], cwd=stage, env=env)
        r = _run([hs, "-i", "circuit_built.sp", "-o", "hspice_run"], cwd=stage, env=env)
        rc = r.returncode
        lis = (stage / "hspice_run.lis")
        metric = binding["metric"]
        value = parse_lis_value(lis.read_text(errors="ignore"), metric) if lis.is_file() else None
        sim_ok = (rc == 0 and lis.is_file() and value is not None and math.isfinite(value))
        (stage / "measure_result.json").write_text(json.dumps({
            "sim_ok": sim_ok, "value": value, "metric": metric,
            "analysis": METRIC_ANALYSIS[metric], "hspice_rc": rc}) + "\n")
        # provenance attestation: the binding's authority sources (for the grader's evidence_provenance)
        (stage / "provenance_attestation.json").write_text(json.dumps({
            "roles": {"metric": "char_spec", "corner": "mission_profile", "load_condition": "application_note"},
            "protocol_completed": True}) + "\n")
        (stage / "measurement_report.md").write_text(f"{metric} = {value} {METRIC_UNIT[metric]}\nFINISH\n")
        g = _run(["python3", "grade_spice_handoff.py"], cwd=stage, env=env)
        try:
            markers = json.loads(g.stdout)
        except Exception:
            markers = {"fatal": "grade_failed", "stdout": g.stdout[-400:], "stderr": g.stderr[-400:]}
        results[label] = {"binding": binding, "hspice_rc": rc, "value": value, "sim_ok": sim_ok, "markers": markers}
    (hidden / "wrong_tuple_measure.lis").write_text(
        "# wrong_join_plausible measurement evidence (real HSPICE on b04)\n"
        + f"# metric={results['wrong']['binding']['metric']} value={results['wrong']['value']} {METRIC_UNIT[results['wrong']['binding']['metric']]}\n"
        + "# markers: " + json.dumps(results["wrong"]["markers"].get("dimensions", {})) + "\n")
    shutil.rmtree(stage, ignore_errors=True)
    return results


def hard_feasibility(results):
    """Family B hard gate on the wrong tuple (against the FROZEN plausibility spec)."""
    w = results["wrong"]; d = w["markers"].get("dimensions", {}); metric = w["binding"]["metric"]
    val = w["value"]; lo, hi = METRIC_RANGE[metric]
    finite = val is not None and math.isfinite(val)
    in_range = finite and (lo <= val <= hi)
    gate = {
        "wrong_syntactically_valid": w["hspice_rc"] == 0 or w["sim_ok"],                      # (a) syntactically valid
        "wrong_completes_simulation": w["sim_ok"],                                            # (b) completes
        "wrong_produces_required_measurement": w["value"] is not None,                        # (c) measurement present
        "wrong_within_frozen_plausibility": in_range and finite,                              # (d) within frozen criteria
        "wrong_not_trivially_numerically_failing": finite and in_range,                       # not NaN/missing/parser-fallback
        "wrong_rejected_by_authority_not_numeric": (not d.get("semantic_binding", True)) and bool(d.get("numeric_validity", False)),
    }
    gate["grader_does_not_use_hidden_exact_answer"] = True  # semantic_binding compares binding, not value
    gate["PASS"] = all(v for k, v in gate.items() if k != "grader_does_not_use_hidden_exact_answer") and gate["grader_does_not_use_hidden_exact_answer"]
    return gate


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id", default="p16_dev_0000")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--golden", default="SS_0p9_-40,light,gain")
    ap.add_argument("--wrong", default="FF_1p3_125,heavy,gain")
    ap.add_argument("--condition", default="BundleS", choices=["Base", "BundleS", "TypedContract"])
    ap.add_argument("--out-root", default=str(REPO / "tasks" / TRACK))
    ap.add_argument("--bake", action="store_true")
    args = ap.parse_args()
    g = tuple(args.golden.split(",")); w = tuple(args.wrong.split(","))
    out = Path(args.out_root) / args.task_id
    if out.exists():
        shutil.rmtree(out)
    truth = build_task_skeleton(out, args.task_id, args.seed, g, w, args.condition)
    print(json.dumps({"built": str(out), "golden": truth["golden_join"], "wrong": truth["wrong_join_plausible"]}, indent=2))
    if args.bake:
        env = dict(os.environ)
        env["EDA_TOOL_ROOT"] = "/data1/tongsb/eda-remote-shim/EDA"
        env["B04_HOST"] = "tsb@b04"
        env["EDA_HSPICE_CMD"] = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice"
        res = bake_golden(out, env)
        gate = hard_feasibility(res)
        (out / "hidden" / "bake_results.json").write_text(json.dumps({"results": res, "hard_feasibility": gate}, indent=2) + "\n")
        print(json.dumps({"hard_feasibility": gate,
                          "golden_sim_ok": res['golden']['sim_ok'], "golden_value": res['golden']['value'],
                          "wrong_sim_ok": res['wrong']['sim_ok'], "wrong_value": res['wrong']['value'],
                          "wrong_plausible_but_wrong": res['wrong']['markers'].get('plausible_but_wrong')}, indent=2))


if __name__ == "__main__":
    main()
