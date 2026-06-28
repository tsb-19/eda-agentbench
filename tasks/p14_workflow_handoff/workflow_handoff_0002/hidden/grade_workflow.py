#!/usr/bin/env python3
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
