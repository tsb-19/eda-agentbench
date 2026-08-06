#!/usr/bin/env python3
"""Phase-5C SPICE no-call forensic audit (zero model calls). For each of the 12 SPICE episodes:
regenerate circuit_built.sp from the preserved submitted meas_config via the REAL build_deck.py,
diff against the original shipped deck, and classify what changed. Also scan the agentlog for any
MANUAL write/run command targeting the deck (there should be none if the change is purely the
intended build_deck regeneration). Verdict per episode: protocol_compromised iff a behaviorally
relevant edit occurred (anything beyond the intended .param av/cload regeneration from meas_config)
that could have changed the evidence trajectory or enabled semantic success outside protocol.
"""
from __future__ import annotations
import json, re, shutil, subprocess, sys, tempfile, difflib
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "generators"))
import p16_spice_handoff_gen as GB  # noqa: E402
EV = REPO / "reports/evidence/phase5c_episodes"

# categories of deck lines
def classify_line(line):
    s = line.strip().lower()
    if s.startswith("*") or s == "" or s.startswith("//"):
        return "comment_or_whitespace"
    if s.startswith(".param"):
        return "corner_model_or_load_param"   # av (corner/model) + cload (load)
    if s.startswith(".measure"):
        return "measurement_statement"
    if s.startswith(".ac") or s.startswith(".tran") or s.startswith(".dc") or s.startswith(".op"):
        return "analysis_statement"
    if s.startswith("vin") or s.startswith("vpulse"):
        return "stimulus"
    if s.startswith("ein") or s.startswith("e(") or "vccvs" in s:
        return "controlled_source"
    if re.match(r"^[rcl]\w*\s", s) or s.startswith("r") and "out" in s:
        return "circuit_param_or_topology"
    if s.startswith(".") :
        return "other_directive"
    return "topology_or_other"


def regenerate_deck(submitted_cfg):
    """Run the REAL build_deck.py on the submitted meas_config -> the regenerated deck text."""
    stage = Path(tempfile.mkdtemp(prefix="forensic_"))
    try:
        # copy a task's build_deck + models, set meas_config, run build_deck
        src = REPO / "tasks/p16_spice_handoff/p16_eval_0001_base/files"
        shutil.copy(src / "build_deck.py", stage / "build_deck.py")
        shutil.copy(src / "corner_models.json", stage / "corner_models.json")
        shutil.copy(src / "load_models.json", stage / "load_models.json")
        (stage / "meas_config.json").write_text(json.dumps(submitted_cfg))
        r = subprocess.run([sys.executable, "build_deck.py"], cwd=str(stage), capture_output=True, text=True, timeout=30)
        deck = (stage / "circuit_built.sp").read_text() if (stage / "circuit_built.sp").is_file() else ""
        return deck
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def manual_deck_edits(agentlog):
    """Return any write/run actions that target circuit_built.sp (a manual edit beyond build_deck)."""
    out = []
    for a in agentlog.get("actions", []):
        if a.get("type") not in ("write", "run"):
            continue
        blob = json.dumps(a).lower()
        if "circuit_built.sp" in blob and "build_deck" not in blob and "run_public" not in blob and "run_hidden" not in blob:
            out.append(a)
    return out


def main():
    results = []
    for ep in sorted(EV.iterdir()):
        if not ep.is_dir() or not ep.name.startswith("p16"):
            continue
        trial = ep.name
        sub = json.loads((ep / "meas_config.submitted.json").read_text())
        ag = json.loads((ep / "agentlog.sanitized.json").read_text())
        # original shipped deck (wrong tuple's params) from the corresponding task
        cond = "_base" if trial.endswith("_base_r1") or trial.endswith("_base_r2") else "_bundles"
        inst = re.sub(r"_r[12]$", "", trial).rsplit("_", 1)[0]
        shipped = (REPO / "tasks/p16_spice_handoff" / f"{inst}{cond}" / "files/circuit_built.sp").read_text()
        regen = regenerate_deck(sub)
        # line diff classification
        changed_categories = set()
        sm = difflib.SequenceMatcher(None, shipped.splitlines(), regen.splitlines())
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            for line in regen.splitlines()[j1:j2] + shipped.splitlines()[i1:i2]:
                changed_categories.add(classify_line(line))
        manual = manual_deck_edits(ag)
        behaviorally_relevant = bool((changed_categories - {"comment_or_whitespace", "corner_model_or_load_param"}))
        compromised = behaviorally_relevant or bool(manual)
        results.append({"trial": trial, "instance": inst, "condition": "Base" if "_base_" in trial else "BundleS",
                        "submitted_corner_load": [sub.get("corner"), sub.get("load_condition")],
                        "changed_categories": sorted(changed_categories),
                        "manual_deck_edits": len(manual),
                        "behaviorally_relevant": behaviorally_relevant,
                        "protocol_compromised": compromised})
    n_comp = sum(r["protocol_compromised"] for r in results)
    report = {"schema": "phase5c_spice_forensic_audit/v1", "episodes_audited": len(results),
              "protocol_compromised_count": n_comp,
              "hypothesis": "the anti-cheat 'circuit_built.sp modified' flag is a FALSE POSITIVE: run_public.sh calls build_deck.py, which regenerates the deck's .param av/cload from the agent's meas_config; the shipped deck carries the WRONG tuple's params, so a corrected meas_config regenerates a different deck -> hash mismatch. The change is the intended corner/model + load regeneration, not a manual edit.",
              "verdict": (f"0 behaviorally-relevant deck edits; the modification is the intended build_deck .param "
                          f"regeneration from the agent's meas_config in all {len(results)} episodes -> NOT protocol_compromised. "
                          "semantic_binding is graded from meas_config (preserved), independent of the deck.") if n_comp == 0
                          else f"{n_comp} episode(s) with behaviorally-relevant deck edits -> protocol_compromised",
              "per_episode": results}
    out = REPO / "reports/synthetic_phase5c_spice_forensic_audit.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"episodes": len(results), "protocol_compromised": n_comp,
                      "changed_categories_seen": sorted({c for r in results for c in r["changed_categories"]}),
                      "manual_deck_edits_total": sum(r["manual_deck_edits"] for r in results)}, indent=2))
    for r in results[:4]:
        print(f"  {r['trial']}: changed={r['changed_categories']} manual={r['manual_deck_edits']} compromised={r['protocol_compromised']}")


if __name__ == "__main__":
    main()
