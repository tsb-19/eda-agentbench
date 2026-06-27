#!/usr/bin/env python3
"""Hidden handoff-consistency grader for FlowHandoff Variant A (manifest->stale-netlist).

Reads the agent-repaired handoff_manifest.json and the package artifacts (netlists, sdc) AS DATA
(no Tcl evaluated here) plus the hidden handoff_truth.json, and decides whether the HANDOFF
CONTRACT is restored — independent of whether PrimeTime sign-off went green. Emits, at line start:

    MANIFEST_OK                          (only when every graded manifest field matches the contract)
    MANIFEST_SCORE: <frac>
    MANIFEST_DETAIL: <per-field>
    HANDOFF_CONSISTENCY_OK               (only when the consumed netlist matches the contract:
                                          provenance hash + spec-required interface)
    HANDOFF_CONSISTENCY_SCORE: <frac>
    HANDOFF_CONSISTENCY_DETAIL: <per-check>
    HANDOFF_MASKING_DETECTED: <what>     (symptom-suppression: zeroes consistency credit in the evaluator)

The headline anti-collapse property: selecting the STALE netlist (PT still green) fails both
MANIFEST_OK (wrong netlist/revision/hash) and HANDOFF_CONSISTENCY_OK (missing the `en` interface,
provenance mismatch). Restoring the manifest to the current revision with a matching hash is the
only path to full credit. Pure stdlib.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys


def _jstr(text: str, key: str) -> str:
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', text)
    return m.group(1) if m else ""


def _sha256_file(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ""


def _netlist_ports(path: str) -> set[str]:
    """Parse the module port list from the gate-level netlist header (module top (p, p, ...);)."""
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        return set()
    m = re.search(r"\bmodule\s+\w+\s*\(([^)]*)\)\s*;", text, re.DOTALL)
    if not m:
        return set()
    return {p.strip() for p in m.group(1).split(",") if p.strip()}


def _sdc_weakened(sdc_path: str, truth: dict) -> str | None:
    """Detect masking edits to a frozen SDC: over-constraint relief or timing exceptions that
    suppress the symptom instead of fixing the handoff. Returns a reason string or None."""
    try:
        with open(sdc_path) as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    exception_cmds = ("set_false_path", "set_multicycle_path", "set_clock_groups",
                      "set_disable_timing")
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for cmd in exception_cmds:
            if line.startswith(cmd):
                return f"sdc_exception:{cmd}"
        # period loosened beyond the frozen 3.0, or uncertainty zeroed/inflated
        if line.startswith("create_clock"):
            mm = re.search(r"-period\s+([0-9.]+)", line)
            if mm and float(mm.group(1)) > 3.0 + 1e-6:
                return f"period_loosened:{mm.group(1)}"
    return None


def grade(manifest_text: str, truth: dict) -> tuple[bool, float, str, bool, float, str, str | None]:
    sel = _jstr(manifest_text, "netlist")
    decl_hash = _jstr(manifest_text, "netlist_provenance_sha256")
    rev = _jstr(manifest_text, "netlist_revision")
    top = _jstr(manifest_text, "top_module")
    clock = _jstr(manifest_text, "clock")
    scenario = _jstr(manifest_text, "scenario")
    corner = _jstr(manifest_text, "corner")

    # --- manifest field checks ---
    mchecks = [
        ("netlist", sel == truth["expected_netlist"], f"{sel} vs {truth['expected_netlist']}"),
        ("revision", rev == truth["expected_revision"], f"{rev} vs {truth['expected_revision']}"),
        ("provenance_hash", decl_hash == truth["expected_netlist_sha256"],
         f"{decl_hash[:12]} vs {truth['expected_netlist_sha256'][:12]}"),
        ("top_module", top == truth["top_module"], f"{top} vs {truth['top_module']}"),
        ("clock", clock == truth["clock"], f"{clock} vs {truth['clock']}"),
        ("scenario", scenario == truth["scenario"], f"{scenario} vs {truth['scenario']}"),
        ("corner", corner == truth["corner"], f"{corner} vs {truth['corner']}"),
    ]
    m_ok = sum(1 for _, ok, _ in mchecks if ok)
    m_frac = m_ok / len(mchecks)
    m_full = m_ok == len(mchecks)
    m_detail = " ".join(f"{n}={'ok' if ok else 'WRONG('+info+')'}" for n, ok, info in mchecks)

    # --- handoff-consistency checks against the ACTUAL consumed artifact ---
    actual_hash = _sha256_file(sel) if sel else ""
    ports = _netlist_ports(sel) if sel else set()
    cchecks = [
        # the selected file's content really is the expected revision (provenance integrity)
        ("provenance_integrity", actual_hash == truth["expected_netlist_sha256"],
         f"actual={actual_hash[:12]}"),
        # declared hash matches the file actually on disk (no stale/forged pointer)
        ("declared_matches_disk", bool(decl_hash) and decl_hash == actual_hash,
         f"decl={decl_hash[:12]} disk={actual_hash[:12]}"),
        # the consumed netlist exposes the spec-required interface (the `en` qualifier)
        ("interface_port", truth["required_interface_port"] in ports,
         f"ports={sorted(ports)}"),
        # full required port set present
        ("required_ports", set(truth["required_ports"]).issubset(ports),
         f"missing={sorted(set(truth['required_ports']) - ports)}"),
    ]
    c_ok = sum(1 for _, ok, _ in cchecks if ok)
    c_frac = c_ok / len(cchecks)
    c_full = c_ok == len(cchecks)
    c_detail = " ".join(f"{n}={'ok' if ok else 'WRONG('+info+')'}" for n, ok, info in cchecks)

    # --- masking: weakened frozen SDC ---
    masking = None
    if truth.get("forbid_sdc_weakening"):
        masking = _sdc_weakened(truth.get("constraints", "constraints.sdc"), truth)

    return m_full, m_frac, m_detail, c_full, c_frac, c_detail, masking


def main() -> int:
    manifest_path = sys.argv[1] if len(sys.argv) > 1 else "handoff_manifest.json"
    truth_path = sys.argv[2] if len(sys.argv) > 2 else "handoff_truth.json"
    try:
        with open(manifest_path) as f:
            manifest_text = f.read()
    except OSError:
        print("MANIFEST_SCORE: 0.000")
        print("MANIFEST_DETAIL: no_manifest")
        print("HANDOFF_CONSISTENCY_SCORE: 0.000")
        print("HANDOFF_CONSISTENCY_DETAIL: no_manifest")
        return 0
    with open(truth_path) as f:
        truth = json.load(f)

    m_full, m_frac, m_detail, c_full, c_frac, c_detail, masking = grade(manifest_text, truth)

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
