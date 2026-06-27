#!/usr/bin/env python3
"""Hidden grader for p12 mf_handoff_0001 (multi-artifact stale-package triangle).

Reads, ALL AS DATA (no Tcl evaluated here):
  - the agent-edited flow_config.json (which netlist the flow consumes)
  - the agent-edited provenance.json (recorded sign-off evidence)
  - the read-only handoff_manifest.json (authority) and the package netlists (for hashing)
  - the LAUNDERED applied SDC (applied_hidden.sdc, written by write_sdc in run_hidden.tcl)
  - the trusted PrimeTime coverage facts (coverage.txt: intended-clock-present + #constrained paths)
  - the hidden handoff_truth.json (golden contract)

Emits the markers the MultiFactHandoffEvaluator consumes, at line start:
    ARTIFACT_CONSISTENCY_OK / _SCORE / _DETAIL   consumed netlist == manifest netlist, content hash
                                                 matches the manifest/golden provenance, corner matches
    SCENARIO_CLOCK_OK / _SCORE / _DETAIL         laundered SDC binds the intended clock + intended
                                                 sequential paths actually constrained (coverage>=min)
    PROVENANCE_OK / _SCORE / _DETAIL             provenance.json records the v2/clk_main run: declared
                                                 revision/clock/corner match the manifest AND the
                                                 declared hash matches the consumed netlist on disk
    HANDOFF_MASKING_DETECTED: <what>             timing weakening / exceptions (zeroes consistency)

Anti-collapse: the consumed netlist (flow_config) and the bound clock (SDC) are a JOINTLY-stale pair.
Fix the SDC alone -> flow still reads v1 (no clk_main port) -> coverage 0 paths -> SCENARIO fail and
SIGNOFF fail. Fix flow_config alone -> SDC still binds clk_old (absent on v2) -> coverage 0 paths ->
same. Fix provenance alone -> declared hash != consumed-on-disk hash (still v1) -> PROVENANCE fail and
ARTIFACT fail. Only the coordinated flow_config->v2 AND SDC->clk_main restores a non-empty graph;
provenance reconciliation lifts the last axis to full credit. Pure stdlib.
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


def _read_coverage(path: str) -> dict:
    out = {"intended_clock_present": 0, "constrained_paths": 0, "consumed_netlist": ""}
    try:
        with open(path) as f:
            for line in f:
                parts = line.split(None, 1)
                if len(parts) == 2 and parts[0] in out:
                    v = parts[1].strip()
                    if parts[0] == "consumed_netlist":
                        out[parts[0]] = v
                    else:
                        try:
                            out[parts[0]] = int(v)
                        except ValueError:
                            pass
    except OSError:
        pass
    return out


def _sdc_clock_names(sdc_text: str) -> list[str]:
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


def grade(flow_text: str, prov_text: str, manifest_text: str, sdc_text: str,
          coverage: dict, truth: dict):
    consumed = _jstr(flow_text, "netlist")
    consumed_corner = _jstr(flow_text, "corner")
    man_net = _jstr(manifest_text, "netlist") or truth["manifest_netlist"]
    man_corner = _jstr(manifest_text, "corner") or truth["corner"]
    consumed_disk_hash = _sha256_file(consumed) if consumed else ""

    # --- 1) artifact consistency: consumed == manifest netlist, hash integrity, corner ---
    achecks = [
        ("consumed_is_manifest_netlist", consumed == man_net, f"{consumed} vs {man_net}"),
        ("consumed_is_expected", consumed == truth["expected_netlist"],
         f"{consumed} vs {truth['expected_netlist']}"),
        ("provenance_integrity", consumed_disk_hash == truth["expected_netlist_sha256"],
         f"disk={consumed_disk_hash[:12]} want={truth['expected_netlist_sha256'][:12]}"),
        ("corner_matches_manifest", consumed_corner == man_corner,
         f"{consumed_corner} vs {man_corner}"),
    ]
    a_ok = sum(1 for _, ok, _ in achecks if ok)
    a_full = a_ok == len(achecks)
    a_detail = " ".join(f"{n}={'ok' if ok else 'WRONG('+i+')'}" for n, ok, i in achecks)

    # --- 2) scenario/clock: laundered SDC binds intended clock + paths actually constrained ---
    sdc_clocks = _sdc_clock_names(sdc_text)
    schecks = [
        ("sdc_binds_intended", truth["expected_clock"] in sdc_clocks,
         f"sdc={sdc_clocks} want={truth['expected_clock']}"),
        ("no_stale_clock", truth["stale_clock"] not in sdc_clocks,
         f"stale={truth['stale_clock']} in {sdc_clocks}"),
        ("intended_clock_present", coverage["intended_clock_present"] == 1,
         f"present={coverage['intended_clock_present']}"),
        ("paths_constrained", coverage["constrained_paths"] >= truth["min_constrained_paths"],
         f"constrained_paths={coverage['constrained_paths']} min={truth['min_constrained_paths']}"),
    ]
    s_ok = sum(1 for _, ok, _ in schecks if ok)
    s_full = s_ok == len(schecks)
    s_detail = " ".join(f"{n}={'ok' if ok else 'WRONG('+i+')'}" for n, ok, i in schecks)

    # --- 3) provenance/report: provenance.json records the consumed v2/clk_main run ---
    p_rev = _jstr(prov_text, "netlist_revision")
    p_hash = _jstr(prov_text, "netlist_sha256")
    p_clk = _jstr(prov_text, "clock")
    p_corner = _jstr(prov_text, "corner")
    pchecks = [
        ("revision", p_rev == truth["expected_revision"],
         f"{p_rev} vs {truth['expected_revision']}"),
        ("clock", p_clk == truth["expected_clock"], f"{p_clk} vs {truth['expected_clock']}"),
        ("corner", p_corner == truth["corner"], f"{p_corner} vs {truth['corner']}"),
        ("hash_matches_consumed_disk", bool(p_hash) and p_hash == consumed_disk_hash,
         f"prov={p_hash[:12]} disk={consumed_disk_hash[:12]}"),
        ("hash_is_expected", p_hash == truth["expected_netlist_sha256"],
         f"prov={p_hash[:12]} want={truth['expected_netlist_sha256'][:12]}"),
    ]
    p_ok = sum(1 for _, ok, _ in pchecks if ok)
    p_full = p_ok == len(pchecks)
    p_detail = " ".join(f"{n}={'ok' if ok else 'WRONG('+i+')'}" for n, ok, i in pchecks)

    masking = _sdc_weakened(sdc_text, truth) if truth.get("forbid_weakening") else None

    return (a_full, a_ok / len(achecks), a_detail,
            s_full, s_ok / len(schecks), s_detail,
            p_full, p_ok / len(pchecks), p_detail, masking)


def _read(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


def main() -> int:
    applied = sys.argv[1] if len(sys.argv) > 1 else "applied_hidden.sdc"
    truth_path = sys.argv[2] if len(sys.argv) > 2 else "handoff_truth.json"
    manifest_path = sys.argv[3] if len(sys.argv) > 3 else "handoff_manifest.json"
    coverage_path = sys.argv[4] if len(sys.argv) > 4 else "coverage.txt"
    flow_path = sys.argv[5] if len(sys.argv) > 5 else "flow_config.json"
    prov_path = sys.argv[6] if len(sys.argv) > 6 else "provenance.json"

    sdc_text = _read(applied)
    with open(truth_path) as f:
        truth = json.load(f)
    manifest_text = _read(manifest_path)
    flow_text = _read(flow_path)
    prov_text = _read(prov_path)
    coverage = _read_coverage(coverage_path)

    (a_full, a_frac, a_detail, s_full, s_frac, s_detail,
     p_full, p_frac, p_detail, masking) = grade(
        flow_text, prov_text, manifest_text, sdc_text, coverage, truth)

    if masking:
        print(f"HANDOFF_MASKING_DETECTED: {masking}")

    if a_full and not masking:
        print("ARTIFACT_CONSISTENCY_OK")
    print(f"ARTIFACT_CONSISTENCY_SCORE: {a_frac:.3f}")
    print(f"ARTIFACT_CONSISTENCY_DETAIL: {a_detail}")

    if s_full and not masking:
        print("SCENARIO_CLOCK_OK")
    print(f"SCENARIO_CLOCK_SCORE: {s_frac:.3f}")
    print(f"SCENARIO_CLOCK_DETAIL: {s_detail}")

    if p_full and not masking:
        print("PROVENANCE_OK")
    print(f"PROVENANCE_SCORE: {p_frac:.3f}")
    print(f"PROVENANCE_DETAIL: {p_detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
