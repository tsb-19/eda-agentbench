#!/usr/bin/env python3
"""Hidden handoff grader for FlowHandoff Variant C (clock-name mismatch / unconstrained false-clean).

Reads the LAUNDERED applied SDC (written by write_sdc in run_hidden.tcl), the trusted PrimeTime
coverage facts (coverage.txt: intended-clock-present + constrained-path count), the read-only
handoff_manifest.json, and the hidden handoff_truth.json -- all AS DATA (no Tcl evaluated here).
Emits the SAME markers the shared FlowHandoffEvaluator consumes, so Variant C reuses that
evaluator unchanged:

    MANIFEST_OK / MANIFEST_SCORE / MANIFEST_DETAIL
        -> the constraints bind the clock NAME the manifest+spec intend (not the stale name)
    HANDOFF_CONSISTENCY_OK / HANDOFF_CONSISTENCY_SCORE / HANDOFF_CONSISTENCY_DETAIL
        -> intended clock object present AND the intended sequential paths are actually
           constrained (non-empty timing graph) -- the coverage/completeness check
    HANDOFF_MASKING_DETECTED  -> timing-weakening / exception edits that suppress the symptom

Anti-collapse: a stale clock name yields zero constrained paths. PT prints "clean", but the
coverage check fails (constrained_paths=0) and the laundered SDC binds the wrong clock name, so
neither HANDOFF_CONSISTENCY_OK nor MANIFEST_OK is emitted, and run_signoff.tcl marks SIGNOFF_FAIL
(no_paths). "PT green" alone cannot pass. Pure stdlib.
"""
from __future__ import annotations

import json
import re
import sys


def _jstr(text: str, key: str) -> str:
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', text)
    return m.group(1) if m else ""


def _read_coverage(path: str) -> dict:
    out = {"intended_clock_present": 0, "constrained_paths": 0}
    try:
        with open(path) as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2 and parts[0] in out:
                    try:
                        out[parts[0]] = int(parts[1])
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


def _sdc_clock_names(sdc_text: str) -> list[str]:
    """Clock names created in the laundered SDC (create_clock -name <n> ...)."""
    names = []
    for raw in sdc_text.splitlines():
        line = raw.strip()
        if line.startswith("create_clock"):
            m = re.search(r"-name\s+(\S+)", line)
            if m:
                names.append(m.group(1).strip('{}"'))
    return names


def _sdc_weakened(sdc_text: str, truth: dict) -> str | None:
    exception_cmds = ("set_false_path", "set_multicycle_path", "set_clock_groups",
                      "set_disable_timing")
    for raw in sdc_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for cmd in exception_cmds:
            if line.startswith(cmd):
                return f"sdc_exception:{cmd}"
        if line.startswith("create_clock"):
            mm = re.search(r"-period\s+([0-9.]+)", line)
            if mm and float(mm.group(1)) > truth["clock_period_ns"] + 1e-6:
                return f"period_loosened:{mm.group(1)}"
    return None


def grade(sdc_text: str, manifest_text: str, coverage: dict, truth: dict):
    expected_clk = truth["expected_clock"]
    min_paths = truth.get("min_constrained_paths", 1)
    sdc_clocks = _sdc_clock_names(sdc_text)
    manifest_clk = _jstr(manifest_text, "clock")

    # --- manifest/SDC clock-name agreement (the contract: bind the intended clock) ---
    mchecks = [
        ("sdc_clock_name", expected_clk in sdc_clocks, f"sdc={sdc_clocks} want={expected_clk}"),
        ("no_stale_clock", truth["stale_clock"] not in sdc_clocks,
         f"stale={truth['stale_clock']} in {sdc_clocks}"),
        ("manifest_clock", manifest_clk == expected_clk, f"{manifest_clk} vs {expected_clk}"),
    ]
    m_ok = sum(1 for _, ok, _ in mchecks if ok)
    m_full = m_ok == len(mchecks)
    m_detail = " ".join(f"{n}={'ok' if ok else 'WRONG('+i+')'}" for n, ok, i in mchecks)

    # --- coverage / completeness: intended clock bound AND intended paths constrained ---
    cchecks = [
        ("intended_clock_present", coverage["intended_clock_present"] == 1,
         f"present={coverage['intended_clock_present']}"),
        ("paths_constrained", coverage["constrained_paths"] >= min_paths,
         f"constrained_paths={coverage['constrained_paths']} min={min_paths}"),
        ("sdc_binds_intended", expected_clk in sdc_clocks and truth["stale_clock"] not in sdc_clocks,
         f"sdc={sdc_clocks}"),
    ]
    c_ok = sum(1 for _, ok, _ in cchecks if ok)
    c_full = c_ok == len(cchecks)
    c_detail = " ".join(f"{n}={'ok' if ok else 'WRONG('+i+')'}" for n, ok, i in cchecks)

    masking = _sdc_weakened(sdc_text, truth) if truth.get("forbid_weakening") else None
    return (m_full, m_ok / len(mchecks), m_detail,
            c_full, c_ok / len(cchecks), c_detail, masking)


def main() -> int:
    applied = sys.argv[1] if len(sys.argv) > 1 else "applied_hidden.sdc"
    truth_path = sys.argv[2] if len(sys.argv) > 2 else "handoff_truth.json"
    manifest_path = sys.argv[3] if len(sys.argv) > 3 else "handoff_manifest.json"
    coverage_path = sys.argv[4] if len(sys.argv) > 4 else "coverage.txt"
    try:
        with open(applied) as f:
            sdc_text = f.read()
    except OSError:
        print("MANIFEST_SCORE: 0.000")
        print("MANIFEST_DETAIL: no_applied_sdc")
        print("HANDOFF_CONSISTENCY_SCORE: 0.000")
        print("HANDOFF_CONSISTENCY_DETAIL: no_applied_sdc")
        return 0
    with open(truth_path) as f:
        truth = json.load(f)
    try:
        with open(manifest_path) as f:
            manifest_text = f.read()
    except OSError:
        manifest_text = ""
    coverage = _read_coverage(coverage_path)

    m_full, m_frac, m_detail, c_full, c_frac, c_detail, masking = grade(
        sdc_text, manifest_text, coverage, truth)

    if m_full:
        print("MANIFEST_OK")
    print(f"MANIFEST_SCORE: {m_frac:.3f}")
    print(f"MANIFEST_DETAIL: {m_detail}")

    if masking:
        print(f"HANDOFF_MASKING_DETECTED: {masking}")
    if c_full and not masking:
        print("HANDOFF_CONSISTENCY_OK")
    print(f"HANDOFF_CONSISTENCY_SCORE: {c_frac:.3f}")
    print(f"HANDOFF_CONSISTENCY_DETAIL: {c_detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
