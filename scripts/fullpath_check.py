#!/usr/bin/env python3
"""Level-2 full-path PT check standard (score-independent measurement-process control).

A fixed, versioned KNOWN REFERENCE design (workflow_handoff_0009 golden: netlist_v2 / clk_main /
slow / func on tiny.db) is driven through the SAME launcher/shim + PT signoff + report-generation +
parsing + evidence-freshness path the fairness grader uses. The check verifies predeclared structural
/ signoff / freshness invariants against frozen reference values. It is INDEPENDENT of the identity or
expected score of any candidate currently being graded: it always runs the fixed reference and never
receives or inspects a candidate result.

If b04 corrupts the path (false signoff-RED on a MET design, truncated report, broken digest chain),
the reference invariants fail -> the check is unhealthy -> the enclosing measurement block is
inadmissible (score-INDEPENDENTLY: a 1.0 inside an unhealthy block is invalid just as a 0.1 is).

Invariants (on the fixed reference):
  - PT exit: stage1 rc=0, stage2 rc=0 (tool_exit=0)
  - design fingerprint: netlist_v2.v / clk_main / slow / func / acc_stage / tiny.db
  - report completeness: timing_report.rpt exists with a REPORT_TIMING body
  - signoff: timing_report header signoff=OK; manifest signoff=OK; stage2 signoff=OK
  - slack: timing_report slack MET in [0.10, 0.20] (reference 0.13)
  - freshness: manifest.report_digest non-empty; stage2.upstream_evidence_digest == manifest.report_digest
Frozen reference hash: the golden flow_config sha256 (config fingerprint, versioned).
"""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import phase4w_fairness_gate as G  # noqa: E402  (regen_evidence + EDITABLE path)

REFERENCE_TASK = "workflow_handoff_0009"
# frozen reference config fingerprint (the 0009 golden flow_config sha256)
REFERENCE_FC_HASH = "c80812cce61d10c1a84f35793deff9ddfdb40acbf18e12d19c5a75af30240fce"
SLACK_LO, SLACK_HI = 0.10, 0.20  # MET slack window around the 0.13 reference


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slack_from_header(hdr: str):
    import re
    m = re.search(r"slack=([-\d.]+)", hdr)
    return float(m.group(1)) if m else None


def check(env: dict, regen_timeout: float = 600.0) -> dict:
    """Run the fixed reference through the full PT path and verify invariants. Score-independent:
    takes NO candidate argument and never inspects any candidate result. Returns a control record."""
    rec = {"ts": _now_iso(), "reference": REFERENCE_TASK, "healthy": False,
           "config_fingerprint_ok": None, "pt_exit_ok": None, "report_complete": None,
           "signoff_ok": None, "slack_ok": None, "slack": None, "freshness_ok": None,
           "digest_chain": None, "elapsed_s": None, "error": None}
    task = G.TRACK / REFERENCE_TASK
    fc = json.loads((task / "solution/flow_config.json").read_text())
    fc_hash = hashlib.sha256((task / "solution/flow_config.json").read_bytes()).hexdigest()
    rec["config_fingerprint_ok"] = (fc_hash == REFERENCE_FC_HASH)
    work = Path(tempfile.mkdtemp(prefix="fullpath_check_"))
    try:
        shutil.copytree(task / "files", work, dirs_exist_ok=True)
        shutil.copytree(task / "hidden", work, dirs_exist_ok=True)
        (work / "flow_config.json").write_text(json.dumps(fc, indent=2) + "\n")
        t0 = time.monotonic()
        G.regen_evidence(work, env, regen_timeout)  # stage1 + stage2 via the SAME path as the grader
        rec["elapsed_s"] = round(time.monotonic() - t0, 2)
        tr = work / "timing_report.rpt"; em = work / "evidence_manifest.json"; s2 = work / "stage2_summary.json"
        body = tr.read_text(errors="replace") if tr.is_file() else ""
        rec["pt_exit_ok"] = em.is_file() and json.loads(em.read_text()).get("tool_exit", 1) == 0
        rec["report_complete"] = ("=== REPORT_TIMING BEGIN ===" in body and "=== REPORT_TIMING END ===" in body)
        hdr = body.splitlines()[1] if len(body.splitlines()) > 1 else ""
        rec["signoff_ok"] = ("signoff=OK" in hdr and "netlist_v2.v" in hdr and "clk_main" in hdr
                             and "slow" in hdr and "func" in hdr)
        slack = _slack_from_header(hdr)
        rec["slack"] = slack
        rec["slack_ok"] = (slack is not None and SLACK_LO <= slack <= SLACK_HI)
        if em.is_file() and s2.is_file():
            emd = json.loads(em.read_text()); s2d = json.loads(s2.read_text())
            rd = emd.get("report_digest") or ""
            chain = (bool(rd) and s2d.get("upstream_evidence_digest") == rd)
            rec["digest_chain"] = {"manifest_report_digest_prefix": rd[:12],
                                   "stage2_upstream_prefix": (s2d.get("upstream_evidence_digest") or "")[:12],
                                   "match": bool(chain)}
            rec["freshness_ok"] = bool(chain) and emd.get("signoff") == "OK" and s2d.get("signoff") == "OK"
        rec["healthy"] = all(rec.get(k) for k in ("config_fingerprint_ok", "pt_exit_ok", "report_complete",
                                                    "signoff_ok", "slack_ok", "freshness_ok"))
        return rec
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
        return rec
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--regen-timeout", type=float, default=600.0)
    a = ap.parse_args()
    rec = check(os.environ.copy(), a.regen_timeout)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec, indent=2))
    sys.exit(0 if rec["healthy"] else 2)


if __name__ == "__main__":
    main()
