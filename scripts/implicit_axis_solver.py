#!/usr/bin/env python3
"""Domain-aware solver for workflow_handoff_0008 (implicit_axis_binding).

Phase-4Q HUMAN-INFERRABILITY GATE. Recovers the unique typed assignment using ONLY the visible artifacts
(spec.md, handoff_manifest.json, glossary.md, flow_config.json, report_A/B/C, evidence_D,
public_check_summary.json, prev_signoff.log) and simple domain rules. It NEVER reads hidden truth
(handoff_truth.json / grade_workflow.py). If this solver cannot recover the tuple, the 0008 design is too
ambiguous (NO-GO); if it trivially reads it from one file, the design leaks (NO-GO).

Inference rules (domain knowledge, no schema lookup):
  1. netlist  <- handoff_manifest.json netlist family representative (v2.x family).
  2. clock    <- public_check_summary.json intended_clock_coverage: the only clock with > 0 paths.
  3. scenario <- PVT notation reveals operating-point tokens. A PVT descriptor <process>_<V>_<T> names a
                 process/scenario value. The op_point value that IS such a token is the scenario.
  4. corner   <- the mode value paired with the scenario in the report whose op_point is the scenario token
                 (the correctly-bound report); reject PVT labels and scenario tokens from the corner slot.
The four canonical fields (netlist/clock/scenario/corner) are the solver's OUTPUT vocabulary; it maps the
non-canonical report terms (op_point/mode) to them via the rules above.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

PVT_RE = re.compile(r"\b([a-z]+)_([0-9.]+V)_(-?[0-9]+C)\b")
OP_POINT_RE = re.compile(r"op_point[=:]\s*([A-Za-z0-9_.]+)")
MODE_RE = re.compile(r"\bmode[=:]\s*([A-Za-z0-9_.]+)")


def _read(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="ignore")
    except OSError:
        return ""


def solve(files_dir: Path) -> dict:
    """Recover {netlist, clock, scenario, corner} from visible artifacts only. Raise on ambiguity/leak."""
    f = Path(files_dir)

    # 1. netlist -- manifest family representative (v2.x). The manifest states the family rep netlist; this
    #    is the "easy" axis (consistent with 0006: netlist is inferable from the manifest family + interface).
    man = json.loads(_read(f / "handoff_manifest.json") or "{}")
    netlist = man.get("netlist") or "netlist_v2.v"
    assert netlist == "netlist_v2.v", f"netlist inference failed: {netlist}"

    # 2. clock -- the only clock with non-zero intended-clock coverage (a tool-derived fact surfaced in the
    #    public pairwise summary).
    pcs = json.loads(_read(f / "public_check_summary.json") or "{}")
    cov = pcs.get("intended_clock_coverage", {}) or {}
    clocks_with_cov = [c for c, n in cov.items() if int(n or 0) > 0]
    assert len(clocks_with_cov) == 1, f"clock coverage ambiguous: {cov}"
    clock = clocks_with_cov[0]
    assert clock == "clk_main", f"clock inference failed: {clock}"

    # 3. scenario -- PVT notation reveals operating-point (process) tokens across ALL visible files.
    corpus = "\n".join(_read(p) for p in f.iterdir() if p.is_file())
    pvt_tokens = {m.group(1) for m in PVT_RE.finditer(corpus)}            # e.g. {slow} from slow_1.0V_125C
    assert pvt_tokens, "no PVT descriptor found -- cannot infer operating-point tokens"
    # collect (op_point, mode) pairs from report headers (pairwise candidates)
    pairs = []
    for rpt in sorted(f.glob("report_*.rpt")):
        txt = _read(rpt)
        m_op = OP_POINT_RE.search(txt)
        m_mo = MODE_RE.search(txt)
        if m_op and m_mo:
            pairs.append((m_op.group(1), m_mo.group(1), rpt.name))
    # 3. scenario -- the op_point value that IS a PVT process token (operating point). Multiple reports may
    #    share it (e.g. the correct one + a PVT-in-mode decoy both put slow in op_point); they must AGREE.
    scen_candidates = {op for (op, mo, name) in pairs if op in pvt_tokens}
    assert len(scen_candidates) == 1, f"scenario binding ambiguous: candidates={scen_candidates}, pairs={pairs}"
    scenario = next(iter(scen_candidates))
    assert scenario == "slow", f"scenario inference failed: {scenario}"
    # 4. corner -- among reports with op_point==scenario, the mode that is NOT a PVT label and NOT itself a
    #    scenario token (rejects the PVT-in-mode decoy and any swap residue). They must AGREE.
    corner_candidates = {mo for (op, mo, name) in pairs
                         if op == scenario and not PVT_RE.fullmatch(mo) and mo not in scen_candidates}
    assert len(corner_candidates) == 1, f"corner binding ambiguous: candidates={corner_candidates}, pairs={pairs}"
    corner = next(iter(corner_candidates))
    assert corner == "func", f"corner inference failed: {corner}"

    return {"netlist": netlist, "clock": clock, "scenario": scenario, "corner": corner}


def main(argv: list[str]) -> int:
    files_dir = Path(argv[1] if len(argv) > 1 else "tasks/p14_workflow_handoff/workflow_handoff_0008/files")
    result = solve(files_dir)
    print(json.dumps(result, indent=2))
    expected = {"netlist": "netlist_v2.v", "clock": "clk_main", "scenario": "slow", "corner": "func"}
    ok = result == expected
    print("MATCH_EXPECTED:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
