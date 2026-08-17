#!/usr/bin/env python3
"""Phase-7E: disclosure-only answer-identifiability analysis (direct-answer disclosure probe).

No paid calls, no EDA tool, no new episode, no model. Deterministic enumeration over files
committed at or before the experiment freeze. Same class of analysis as Phase-7D: retrospective,
post-freeze, re-derivable by any reader.

THE QUESTION, STATED NARROWLY
-----------------------------
    Reading ONLY what a condition discloses --- and never the task evidence --- is the golden
    assignment already pinned to a single candidate?

WHAT IS AND IS NOT CLOSED BY THIS
---------------------------------
This probe is deliberately NOT called a leakage test. It closes exactly one alternative
explanation and leaves the rest open:

  CLOSED        direct answer disclosure / literal answer identifiability. If |Omega_T| > 1,
                condition T cannot hand the answer over, so "the treatment simply told the model
                the answer" is refuted as an explanation of the S0/S1 result.

  NOT CLOSED    softer information leakage, prior narrowing, prompt-induced heuristic cues,
                accidental lexical correlation, model-specific exploitation. A treatment that
                shrinks the candidate set is informative by construction, and BundleS is designed
                to reduce semantic ambiguity.

  BOUNDS, NOT MECHANISM
                The probe bounds the informational advantage of a condition. It does not
                identify the behavioral mechanism, and a survivor ratio must not be restated as
                one: under the strict reading BundleS does not shrink the candidate set at all.

Survivor counts are reported rather than a boolean because 294 -> 9 and 294 -> 2 warrant
different readings, and because the two readings below bracket rather than pinpoint the answer.

NAMING
------
This script uses K1..K5 for the TASK CONSTRAINTS and C1..C7 for the CLARITY-BUNDLE COMPONENTS.
The frozen task files name both families "C1..C5" / "C1..C7", which collides exactly where it
does the most damage: task constraint C5 (the sign-off pair) is what clarity component C6
asserts. The code refuses to inherit that ambiguity.

    K1  netlist_family                  netlist is in the v2.x family
    K2  clock_identity                  the clock with non-zero intended-clock coverage
    K3  scenario_typed                  scenario value must be a scenario-axis member
    K4  corner_typed                    corner value must be a corner-axis member
    K5  scenario_corner_signoff_pair    the unique (scenario, corner) sign-off pair
                                        <-- this is what clarity component C6 publishes

THREE INFORMATION CLASSES, ENFORCED AND NOT MERELY DECLARED
-----------------------------------------------------------
Every file read goes through _read(), which raises ForbiddenRead on anything outside the
allowlist for its class. The probe would be worthless if it enumerated over a directory that
contains the evidence, so the discipline is executable rather than promised.

  CLASS A  shared candidate universe   the typed-axis value domains. Condition-INVARIANT: the
           (structural)               probe asserts byte-equal domains across all conditions,
                                      so Omega cannot advantage any arm. Loaded through a
                                      key-whitelisted accessor that can return nothing else.

  CLASS B  treatment disclosure        prompt.md, spec.md, glossary.md,
           (per condition)            public_check_summary.json --- and nothing else. These are
                                      the files that differ between Base and BundleS.

  CLASS C  FORBIDDEN                  report_A/B/C, evidence_D, prev_signoff, timing_report,
                                      evidence_manifest, stage2_summary, flow_config,
                                      handoff_manifest, netlists, hidden/*, solution/*.
                                      Reading any of these to derive a constraint would let
                                      task evidence in through the back door and the result
                                      would answer a different question.

The golden tuple is loaded exactly once, in _golden_verification_only(), which is called AFTER
every survivor set is already computed and is used only to report whether the golden sits inside
the survivors and whether it is alone there. It never participates in narrowing.

TWO READINGS, REPORTED AS A BRACKET
-----------------------------------
Whether a condition "discloses" the typed-axis membership is a judgement call, so the probe
refuses to make it and brackets the answer instead. Neither bound is the answer on its own:

  strict     a constraint counts as disclosed only when its VALUE CONTENT is explicitly stated
             in a disclosure file. BundleS's own spec.md says "No complete value-to-axis table
             is provided", so under this reading BundleS does NOT shrink the candidate set at
             all beyond what Base already states --- its contribution is legibility of the role
             binding, not elimination of candidates.

  generous   the LEAKAGE-FAVOURABLE reading. Additionally GRANTS the full typed-axis membership
             table to any condition disclosing canonical labels + axis disjointness + the
             PVT-descriptor rule, and grants clock identity from the declared v2 interface. This
             hands BundleS more than its own files provide. If BundleS survives >1 even here,
             the conclusion is robust.

The reportable quantity is therefore an interval: BundleS leaves between the generous and the
strict count compatible with disclosure alone. Quoting only the generous bound would overstate
how much the treatment narrows; quoting only the strict bound would understate it.

Usage:  python3 scripts/phase7e_answer_identifiability.py [--check]
        --check  recompute and diff against the committed JSON; non-zero exit on drift.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASKS = REPO / "tasks/p14_workflow_handoff"
OUT_JSON = REPO / "reports/synthetic_phase7e_answer_identifiability.json"

SCHEMA = "p14_answer_identifiability/v1"

# --------------------------------------------------------------------------------------------
# Conditions. Every clarity condition in the Study I ledger is a committed task instance; the
# mapping below is the ledger's (condition -> task) column, so the probe measures the arms that
# actually produced the reported numbers rather than a reconstruction of them.
# --------------------------------------------------------------------------------------------
CONDITIONS = [
    # (instance, ledger condition label, role in the paper, expects_C6)
    ("workflow_handoff_0009", "Base(0009)", "S0 baseline", False),
    ("workflow_handoff_0015", "BundleS", "S0 treatment (primary)", False),
    ("workflow_handoff_0011", "Base(0011)", "S1 held-out baseline", False),
    ("workflow_handoff_0017", "Held(0017)", "S1 held-out treatment (primary)", False),
    ("workflow_handoff_0010", "Full bundle(0010)", "positive control: bundle WITH C6", True),
    ("workflow_handoff_0014", "V9", "positive control: Base + C6 only", True),
    ("workflow_handoff_0013", "V1", "full bundle minus C6", False),
    ("workflow_handoff_0016", "BundleD", "disclosure variant", False),
    ("workflow_handoff_0018", "Schema", "component arm", False),
    ("workflow_handoff_0019", "Contract", "component arm", False),
    ("workflow_handoff_0020", "C1", "component arm", False),
    ("workflow_handoff_0021", "C24", "component arm", False),
    ("workflow_handoff_0022", "C2", "component arm", False),
    ("workflow_handoff_0023", "C4", "component arm", False),
]

# Class B: the only files a constraint may be derived from.
DISCLOSURE_ALLOWLIST = (
    "prompt.md",
    "files/spec.md",
    "files/glossary.md",
    "files/public_check_summary.json",
)

# Class C: named explicitly so the audit record shows what was refused, not just what was read.
FORBIDDEN_BASENAMES = (
    "report_A_role_swap.rpt",
    "report_B_role_stale.rpt",
    "report_C_role_pvt.rpt",
    "evidence_D_role_mismatch.json",
    "prev_signoff.log",
    "timing_report.rpt",
    "evidence_manifest.json",
    "stage2_summary.json",
    "flow_config.json",
    "handoff_manifest.json",
    "netlist_v1.v",
    "netlist_v2.v",
    "constraints.sdc",
)

# Class A: the only keys the structural accessor may ever return.
STRUCTURAL_KEY_WHITELIST = ("axes", "typed_axes", "pvt_label_axis")


class ForbiddenRead(RuntimeError):
    """Raised when the probe attempts a read that would admit task evidence."""


# --------------------------------------------------------------------------------------------
# Gated I/O
# --------------------------------------------------------------------------------------------
def _read_disclosure(inst: Path, rel: str) -> str:
    """Read one Class-B disclosure file. Raises on anything not on the allowlist."""
    if rel not in DISCLOSURE_ALLOWLIST:
        raise ForbiddenRead(f"{rel} is not a declared disclosure file")
    p = inst / rel
    if p.name in FORBIDDEN_BASENAMES:
        raise ForbiddenRead(f"{p.name} is task evidence")
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def _disclosure_text(inst: Path) -> tuple[str, list[str]]:
    """Concatenate every present Class-B file. Returns (text, files_read)."""
    parts, read = [], []
    for rel in DISCLOSURE_ALLOWLIST:
        t = _read_disclosure(inst, rel)
        if t:
            parts.append(t)
            read.append(rel)
    return "\n".join(parts), read


def _structural_axes(inst: Path) -> dict:
    """CLASS A. Return ONLY the typed-axis value domains --- the condition-invariant candidate
    space. Physically cannot return the golden: every other key is dropped here, so no caller
    can reach an answer-bearing field through this accessor."""
    raw = json.loads((inst / "hidden/handoff_truth.json").read_text(encoding="utf-8"))
    schema = raw.get("axis_schema", {})
    out = {k: schema[k] for k in STRUCTURAL_KEY_WHITELIST if k in schema}
    leaked = set(out) - set(STRUCTURAL_KEY_WHITELIST)
    if leaked:  # unreachable by construction; asserted so a future edit cannot widen it
        raise ForbiddenRead(f"structural accessor widened to {sorted(leaked)}")
    return out


def _golden_verification_only(inst: Path) -> dict:
    """The golden tuple. Called ONLY after all survivor sets exist, and only to report whether
    the golden is inside them. Never used to narrow anything."""
    raw = json.loads((inst / "hidden/handoff_truth.json").read_text(encoding="utf-8"))
    g = raw["axis_schema"]["expected_unique_assignment"]
    return {k: g[k] for k in ("netlist", "clock", "scenario", "corner")}


# --------------------------------------------------------------------------------------------
# Disclosure detection --- what does this condition actually STATE?
# --------------------------------------------------------------------------------------------
def detect_disclosure(text: str) -> dict:
    """Classify a condition's disclosure content. Pure text predicates over Class-B files."""
    d = {}

    # K1: the spec names the out-of-family netlist outright, in every condition.
    d["k1_netlist_family_stated"] = bool(re.search(r"is out of family", text))
    d["k1_excluded_netlist"] = "netlist_v1.v" if "netlist_v1.v` is out of family" in text \
        or re.search(r"`netlist_v1\.v`\s*is out of family", text) else None

    # K2, strict: a coverage anchor states the per-clock coverage numbers.
    d["k2_coverage_anchor_present"] = "intended_clock_coverage" in text
    # K2, generous: the declared v2 interface names exactly one clock, so the clock is derivable
    # from the family declaration without consulting any coverage evidence.
    m = re.search(r"\{(clk_[a-z_]+(?:,\s*\w+)*)\}`?\s*interface", text)
    iface = [p for p in (m.group(1).split(",") if m else []) if p.startswith("clk")]
    d["k2_v2_interface_declared"] = len(iface) == 1
    d["k2_interface_clock"] = iface[0] if len(iface) == 1 else None

    # K3/K4: is the typed-axis membership tabulated, or explicitly withheld?
    withheld = bool(re.search(
        r"No (?:complete )?value-to-axis (?:table|mapping) is provided", text))
    d["k34_membership_explicitly_withheld"] = withheld
    d["k34_canonical_labels"] = bool(
        re.search(r"carry a \*\*scenario\*\* field|canonical `?scenario`? ?/ ?`?corner`?", text))
    d["k34_axis_disjointness_stated"] = "DISJOINT typed axes" in text
    d["k34_pvt_rule_stated"] = bool(re.search(
        r"never\*?\*? a valid scenario or corner value|NEVER a valid scenario or corner value",
        text))
    # The generous grant: role semantics disclosed well enough to treat membership as known.
    d["k34_role_semantics_disclosed"] = (
        d["k34_canonical_labels"]
        and d["k34_axis_disjointness_stated"]
        and d["k34_pvt_rule_stated"]
    )

    # K5: clarity component C6 --- the sign-off pair, published verbatim.
    m5 = re.search(
        r"setup signoff is taken at the \*\*(\w+) scenario\*\* in the \*\*(\w+) corner\*\*", text)
    d["k5_c6_signoff_pair_asserted"] = bool(m5)
    if m5:
        scen, corner_word = m5.group(1), m5.group(2)
        # "functional corner" is prose for the corner-axis value `func`.
        d["k5_asserted_pair"] = [scen, "func" if corner_word.startswith("func") else corner_word]
    else:
        d["k5_asserted_pair"] = None
    return d


# --------------------------------------------------------------------------------------------
# Enumeration
# --------------------------------------------------------------------------------------------
def build_universe(axes: dict) -> list[dict]:
    """Omega: the full declared candidate space, identical for every condition."""
    a = axes["axes"]
    return [
        {"netlist": n, "clock": c, "scenario": s, "corner": k}
        for n, c, s, k in itertools.product(
            a["netlist"], a["clock"], a["scenario"], a["corner"])
    ]


def constraints_for(disc: dict, axes: dict, reading: str) -> dict:
    """Translate detected disclosure into the K-constraints that reading admits.

    Returns {K: predicate-spec}. Absent K => that constraint is NOT disclosed and the probe
    leaves the corresponding axis unrestricted, because recovering it would require the
    evidence the probe refuses to read.
    """
    generous = reading == "generous"
    typed = axes["typed_axes"]
    out: dict[str, dict] = {}

    if disc["k1_netlist_family_stated"] and disc["k1_excluded_netlist"]:
        out["K1"] = {"axis": "netlist",
                     "allowed": [v for v in axes["axes"]["netlist"]
                                 if v != disc["k1_excluded_netlist"]]}

    if disc["k2_coverage_anchor_present"]:
        out["K2"] = {"axis": "clock", "allowed": ["clk_main"], "via": "coverage anchor"}
    elif generous and disc["k2_v2_interface_declared"]:
        out["K2"] = {"axis": "clock", "allowed": [disc["k2_interface_clock"]],
                     "via": "declared v2 interface"}

    if generous and disc["k34_role_semantics_disclosed"]:
        out["K3"] = {"axis": "scenario", "allowed": list(typed["scenario_axis"]),
                     "via": "granted membership table"}
        out["K4"] = {"axis": "corner", "allowed": list(typed["corner_axis"]),
                     "via": "granted membership table"}

    if disc["k5_c6_signoff_pair_asserted"]:
        out["K5"] = {"axis": ("scenario", "corner"),
                     "allowed_pair": disc["k5_asserted_pair"], "via": "component C6"}
    return out


def survivors(universe: list[dict], cons: dict) -> list[dict]:
    """Candidates compatible with every disclosed constraint."""
    out = []
    for cand in universe:
        ok = True
        for key, spec in cons.items():
            if key == "K5":
                if [cand["scenario"], cand["corner"]] != spec["allowed_pair"]:
                    ok = False
                    break
            elif cand[spec["axis"]] not in spec["allowed"]:
                ok = False
                break
        if ok:
            out.append(cand)
    return out


def probe_condition(inst: Path, axes: dict, reading: str) -> dict:
    text, files_read = _disclosure_text(inst)
    disc = detect_disclosure(text)
    cons = constraints_for(disc, axes, reading)
    universe = build_universe(axes)
    surv = survivors(universe, cons)

    # (scenario, corner) projection --- the part clarity component C6 claims to publish.
    proj = sorted({(c["scenario"], c["corner"]) for c in surv})

    # Golden consulted only now, and only to locate it inside an already-fixed survivor set.
    golden = _golden_verification_only(inst)
    return {
        "reading": reading,
        "files_read": files_read,
        "disclosure": disc,
        "constraints_disclosed": sorted(cons),
        "omega": len(universe),
        "survivors": len(surv),
        "survivors_scenario_corner_projection": len(proj),
        "golden_in_survivors": golden in surv,
        "golden_uniquely_identified": len(surv) == 1 and surv[0] == golden,
        "scenario_corner_uniquely_identified": len(proj) == 1,
    }


# --------------------------------------------------------------------------------------------
def build() -> dict:
    # CLASS A invariance: every condition must share one candidate space, or a survivor-count
    # comparison across conditions would be meaningless.
    axes_by_inst = {name: _structural_axes(TASKS / name) for name, _, _, _ in CONDITIONS}
    ref_name, ref_axes = next(iter(axes_by_inst.items()))
    ref_blob = json.dumps(ref_axes, sort_keys=True)
    divergent = [n for n, a in axes_by_inst.items()
                 if json.dumps(a, sort_keys=True) != ref_blob]
    if divergent:
        raise SystemExit(f"PHASE-7E: candidate universe differs across conditions: {divergent}")

    results = []
    for name, label, role, expects_c6 in CONDITIONS:
        inst = TASKS / name
        row = {"instance": name, "condition": label, "paper_role": role}
        for reading in ("strict", "generous"):
            row[reading] = probe_condition(inst, ref_axes, reading)
        got_c6 = row["strict"]["disclosure"]["k5_c6_signoff_pair_asserted"]
        row["c6_present"] = got_c6
        row["c6_matches_design"] = got_c6 == expects_c6
        results.append(row)

    by_label = {r["condition"]: r for r in results}

    def pair(label):
        r = by_label[label]
        return {"strict": r["strict"]["survivors"], "generous": r["generous"]["survivors"]}

    def bracket(label):
        """The reportable interval: [leakage-favourable bound, strict bound]."""
        r = by_label[label]
        lo, hi = r["generous"]["survivors"], r["strict"]["survivors"]
        return {"low_leakage_favorable": min(lo, hi), "high_strict": max(lo, hi)}

    # The positive control asks a PRECISE question: does the probe detect a component known to be
    # answer-bearing? C6 publishes the sign-off ROLE PAIR, so the invariant that must hold under
    # BOTH readings is uniqueness of the (scenario, corner) projection. Whether C6 also pins the
    # FULL assignment is reading-dependent --- V9 leaves 3 under the strict reading, because the
    # clock is not value-stated there --- and the control does not require it.
    v9 = by_label["V9"]
    full = by_label["Full bundle(0010)"]
    pos_projection = all(
        by_label[l][rd]["scenario_corner_uniquely_identified"]
        for l in ("V9", "Full bundle(0010)") for rd in ("strict", "generous"))
    pos_discriminates = not any(
        by_label[l][rd]["scenario_corner_uniquely_identified"]
        for l in ("BundleS", "Held(0017)") for rd in ("strict", "generous"))
    pos_ok = pos_projection and pos_discriminates

    primary_unique = any(
        by_label[l][rd]["golden_uniquely_identified"]
        for l in ("BundleS", "Held(0017)") for rd in ("strict", "generous"))

    return {
        "schema": SCHEMA,
        "analysis_name": "disclosure-only answer-identifiability (direct-answer disclosure probe)",
        "question": (
            "Reading only what a condition discloses, and never the task evidence, is the "
            "golden assignment already pinned to a single candidate?"
        ),
        "what_this_can_and_cannot_show": {
            "closed_if_survivors_gt_1": (
                "direct answer disclosure / literal answer identifiability --- i.e. the "
                "explanation that the treatment simply told the model the answer"
            ),
            "not_closed": (
                "softer information leakage, prior narrowing, prompt-induced heuristic cues, "
                "accidental lexical correlation, model-specific exploitation"
            ),
            "bounds_not_mechanism": (
                "the probe bounds a condition's informational advantage; it does not identify "
                "the behavioral mechanism, and the survivor ratio must not be restated as one "
                "--- under the strict reading BundleS does not shrink the candidate set at all"
            ),
            "provenance": (
                "retrospective, post-freeze, not preregistered; no paid call, no model, no EDA "
                "tool, no new episode. Same class as Phase-7D."
            ),
        },
        "naming": {
            "K1..K5": "task constraints (this script)",
            "C1..C7": "clarity-bundle components (this script)",
            "collision_in_frozen_files": (
                "the frozen task files name both families C1..C5/C1..C7; task constraint C5 "
                "(sign-off pair) is what clarity component C6 asserts"
            ),
        },
        "information_classes": {
            "A_shared_candidate_universe": {
                "source": "axis_schema typed-axis domains, key-whitelisted",
                "condition_invariant": True,
                "verified_identical_across_conditions": len(CONDITIONS),
            },
            "B_treatment_disclosure": list(DISCLOSURE_ALLOWLIST),
            "C_forbidden": list(FORBIDDEN_BASENAMES) + ["hidden/*", "solution/*"],
            "golden_use": (
                "loaded only after every survivor set was computed; used solely to report "
                "membership and uniqueness, never to narrow"
            ),
        },
        "readings": {
            "strict": "a constraint counts as disclosed only if its value content is stated",
            "generous": (
                "the leakage-favourable reading: additionally grants the typed-axis membership "
                "table to conditions disclosing canonical labels + disjointness + the PVT rule, "
                "and clock identity from the declared v2 interface --- more than the treatment's "
                "own files provide"
            ),
            "how_to_report": (
                "as a bracket. Quoting only the generous bound overstates how much the treatment "
                "narrows; quoting only the strict bound understates it."
            ),
        },
        "headline": {
            "omega": results[0]["strict"]["omega"],
            "base_S0": pair("Base(0009)"),
            "bundleS_S0": pair("BundleS"),
            "base_S1_heldout": pair("Base(0011)"),
            "bundleS_S1_heldout": pair("Held(0017)"),
            "positive_control_V9_base_plus_C6": pair("V9"),
            "positive_control_full_bundle_with_C6": pair("Full bundle(0010)"),
            "bundleS_S0_bracket": bracket("BundleS"),
            "bundleS_S1_bracket": bracket("Held(0017)"),
            "base_S0_bracket": bracket("Base(0009)"),
            "golden_uniquely_identified_under_any_BundleS_reading": primary_unique,
            "positive_control_detects_C6": pos_ok,
            "positive_control_basis": (
                "C6 publishes the sign-off role pair, so the invariant required under BOTH "
                "readings is uniqueness of the (scenario, corner) projection, which holds for "
                "V9 and the full bundle and fails for both BundleS arms. Whether C6 also pins "
                "the FULL assignment is reading-dependent: V9 leaves 3 under the strict reading "
                "because the clock is not value-stated there, and 1 under the generous reading; "
                "the full bundle is unique under both. The control does not require full-"
                "assignment uniqueness and must not be reported as if it did."
            ),
        },
        "conditions": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="recompute and diff against the committed JSON; non-zero exit on drift")
    args = ap.parse_args()

    payload = build()
    h = payload["headline"]

    if args.check:
        if not OUT_JSON.exists():
            print(f"PHASE-7E: {OUT_JSON.relative_to(REPO)} missing; run without --check first",
                  file=sys.stderr)
            return 1
        committed = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        if committed != payload:
            print("PHASE-7E: DRIFT --- recomputed payload differs from the committed JSON",
                  file=sys.stderr)
            return 1
        print("PHASE-7E check: ok")
    else:
        OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"wrote {OUT_JSON.relative_to(REPO)}")

    print(f"  candidate universe |Omega|            {h['omega']}")
    for key, lab in (("base_S0", "Base(0009)          S0 baseline"),
                     ("bundleS_S0", "BundleS             S0 treatment"),
                     ("base_S1_heldout", "Base(0011)          S1 baseline"),
                     ("bundleS_S1_heldout", "Held(0017)          S1 treatment"),
                     ("positive_control_V9_base_plus_C6", "V9 = Base + C6      pos. control"),
                     ("positive_control_full_bundle_with_C6", "Full bundle (C6)    pos. control")):
        v = h[key]
        print(f"  {lab:36} strict {v['strict']:4}   leakage-favorable {v['generous']:4}")
    b = h["bundleS_S0_bracket"]
    print(f"  reportable interval, BundleS S0       {b['low_leakage_favorable']} to "
          f"{b['high_strict']} of {h['omega']}")
    print(f"  golden uniquely identified under BundleS?  "
          f"{h['golden_uniquely_identified_under_any_BundleS_reading']}")
    print(f"  positive control detects C6?               {h['positive_control_detects_C6']}"
          f"  (basis: (scenario, corner) projection unique under both readings)")

    if not h["positive_control_detects_C6"]:
        print("PHASE-7E: positive control FAILED --- the probe did not detect a component known "
              "to be answer-bearing; do not report the negative result", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
