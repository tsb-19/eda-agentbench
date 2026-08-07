#!/usr/bin/env python3
"""Phase-7A Study A — FROZEN 12-instance STA expansion spec (source of truth).

Prospective confirmatory expansion of Family A (STA/PrimeTime). Uses the ALREADY
FROZEN Family-A semantic design (generator p15_sta_handoff_gen.py) unchanged: no
modification to Base/BundleS/TypedContract, semantic-binding definitions, grader
semantics, model config, or budgets. Partitions remain the frozen
["cdc","reset","scan","core"]; diversity is selected within the frozen typed
space, NOT lexical relabeling.

The 12 (golden, wrong, decoy_recipe) tuples below are FROZEN BEFORE any new model
result and BEFORE generation. Strata are predefined from the generator's real
dimensions. The prior 3 STA eval instances (p15_eval_0001..0003) are treated as
historical/external-validity PILOT evidence; this batch (0004..0015) is the
prospective confirmatory dataset, analyzed independently before any combined
summary.

NO model calls. This module only asserts stratum coverage + distinct signatures.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "generators"))
import p15_sta_handoff_gen as GA

INTENTS = GA.INTENTS                  # 4: functional_close, cdc_isolate, reset_exempt, scan_override
PARTITIONS = ["cdc", "reset", "scan", "core"]   # frozen partition set
CHECK_MODES = GA.CHECK_MODES          # 3: setup, hold, both
LEGAL_VIEWS = GA.LEGAL_VIEWS          # golden view must be the intent's legal view

# ---- the frozen 12-instance spec table ----
# (task_id, golden=(intent,partition,view), wrong=(intent,partition,view), decoy_recipe, conflict_axis)
# golden view is always the legal view for the golden intent; wrong view is legal for the WRONG intent
# (keeps the wrong binding plausible, not an obviously-illegal view).
STA12_SPECS = [
    # golden partition varies WITHIN each intent group (balanced: every partition x3 overall,
    # every intent x3) so authority chains + wrong-green signoffs are structurally distinct
    # (no lexical relabel). golden view is the intent's legal view; wrong view is legal for the
    # wrong intent (keeps the wrong binding plausible).
    ("p15_eval_0004", ("functional_close", "core",  "setup"), ("functional_close", "cdc",   "setup"), "scope_drift",  "partition"),
    ("p15_eval_0005", ("functional_close", "cdc",   "setup"), ("reset_exempt",     "cdc",   "both"),  "wrong_domain", "intent+view"),
    ("p15_eval_0006", ("functional_close", "reset", "setup"), ("scan_override",    "reset", "both"),  "wrong_domain", "intent+view"),
    ("p15_eval_0007", ("cdc_isolate",      "core",  "setup"), ("cdc_isolate",      "cdc",   "setup"), "mis_scope",    "partition"),
    ("p15_eval_0008", ("cdc_isolate",      "cdc",   "setup"), ("scan_override",    "cdc",   "both"),  "intent_swap",  "intent+view"),
    ("p15_eval_0009", ("cdc_isolate",      "scan",  "setup"), ("reset_exempt",     "scan",  "both"),  "wrong_domain", "intent+view"),
    ("p15_eval_0010", ("reset_exempt",     "cdc",   "both"),  ("reset_exempt",     "reset", "both"),  "stale_intent", "partition"),
    ("p15_eval_0011", ("reset_exempt",     "reset", "both"),  ("functional_close", "reset", "setup"), "intent_swap",  "intent+view"),
    ("p15_eval_0012", ("reset_exempt",     "scan",  "both"),  ("cdc_isolate",      "scan",  "setup"), "intent_swap",  "intent+view"),
    ("p15_eval_0013", ("scan_override",    "core",  "both"),  ("scan_override",    "scan",  "both"),  "mis_scope",    "partition"),
    ("p15_eval_0014", ("scan_override",    "reset", "both"),  ("cdc_isolate",      "reset", "setup"), "intent_swap",  "intent+view"),
    ("p15_eval_0015", ("scan_override",    "scan",  "both"),  ("functional_close", "scan",  "setup"), "wrong_domain", "intent+view"),
]

PILOT_INSTANCES = ["p15_eval_0001", "p15_eval_0002", "p15_eval_0003"]   # historical; not in this batch


def _sig(golden, wrong, decoy):
    """Structural signature used for distinctness (not lexical relabel)."""
    g_intent, g_part, g_view = golden
    w_intent, w_part, w_view = wrong
    conf = tuple(int(a != b) for a, b in zip(golden, wrong))   # which axes differ
    return (g_intent, g_part, g_view, w_intent, decoy, conf)


def validate():
    problems = []
    ids = [s[0] for s in STA12_SPECS]
    if len(set(ids)) != 12:
        problems.append("task_ids not unique")
    if any(i in PILOT_INSTANCES for i in ids):
        problems.append("batch overlaps pilot instances")
    # legal golden view
    for tid, g, w, decoy, axis in STA12_SPECS:
        if LEGAL_VIEWS[g[0]] != g[2]:
            problems.append(f"{tid}: golden view {g[2]} not legal for {g[0]} (legal={LEGAL_VIEWS[g[0]]})")
        if g == w:
            problems.append(f"{tid}: wrong == golden")
        if w[2] != LEGAL_VIEWS[w[0]]:
            problems.append(f"{tid}: wrong view {w[2]} not legal for wrong intent {w[0]} (plausibility)")
        if any(v not in PARTITIONS for v in (g[1], w[1])):
            problems.append(f"{tid}: partition not in frozen set")
    # distinct structural signatures (no lexical relabel)
    sigs = [_sig(g, w, d) for _, g, w, d, _ in STA12_SPECS]
    if len(set(sigs)) != 12:
        problems.append("structural signatures not all distinct (lexical relabel risk)")
    # distinct golden tuples (authority_signature is a function of the golden derivation)
    goldens = [tuple(g) for _, g, _, _, _ in STA12_SPECS]
    if len(set(goldens)) != 12:
        problems.append("golden bindings not all distinct (authority-signature collision)")
    # distinct wrong tuples (wrong_green_signature is a function of the wrong binding)
    wrongs = [tuple(w) for _, _, w, _, _ in STA12_SPECS]
    if len(set(wrongs)) != 12:
        problems.append(f"wrong bindings not all distinct (wrong-green signature collision): dupes via n={len(wrongs)-len(set(wrongs))}")
    # within each intent group, golden partitions must be distinct (else authority chains collide)
    by_intent = {}
    for _, g, _, _, _ in STA12_SPECS:
        by_intent.setdefault(g[0], []).append(g[1])
    for intent, parts in by_intent.items():
        if len(set(parts)) != len(parts):
            problems.append(f"intent {intent}: golden partitions not distinct within group {parts} (authority collision)")
    # stratum coverage
    cov = {
        "golden_intent":  sorted(set(g[0] for _, g, _, _, _ in STA12_SPECS)),
        "golden_partition": sorted(set(g[1] for _, g, _, _, _ in STA12_SPECS)),
        "golden_view":    sorted(set(g[2] for _, g, _, _, _ in STA12_SPECS)),
        "conflict_axis":  sorted(set(a for _, _, _, _, a in STA12_SPECS)),
        "decoy_recipe":   sorted(set(d for _, _, _, d, _ in STA12_SPECS)),
        "n_per_intent":   {i: sum(1 for _, g, _, _, _ in STA12_SPECS if g[0] == i) for i in INTENTS},
        "n_per_partition": {p: sum(1 for _, g, _, _, _ in STA12_SPECS if g[1] == p) for p in PARTITIONS},
    }
    return problems, cov


def main():
    problems, cov = validate()
    print(json.dumps({"n_specs": len(STA12_SPECS),
                      "coverage": cov,
                      "validation_problems": problems,
                      "PASS": not problems}, indent=2))
    out = REPO / "reports" / "evidence" / "phase7a_sta12_specs.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": "phase7a_sta12_specs/v1",
        "frozen_before": "any Phase-7 model result",
        "pilot_instances_excluded": PILOT_INSTANCES,
        "specs": [{"task_id": t, "golden": list(g), "wrong": list(w), "decoy_recipe": d,
                   "conflict_axis": a, "legal_golden_view": LEGAL_VIEWS[g[0]]}
                  for t, g, w, d, a in STA12_SPECS],
        "coverage": cov,
        "validation_problems": problems,
        "PASS": not problems,
    }, indent=2) + "\n")
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
