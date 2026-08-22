#!/usr/bin/env python3
"""Measure the RAW byte size of public-tool output, so the broker's transport caps are derived from
evidence rather than from the observation cap.

What this establishes: empirical transport headroom over the complete calibration set. What it does
NOT establish: that a cap can never bind. 1 MiB > 8 x the largest output on the measured directories
is a fact about those directories. The property that does not depend on this audit being exhaustive
is the runtime one -- a cap hit is fail-closed, typed transport_output_limit, measurement-invalid,
and never delivered to the agent as truncated tool output.

Zero model calls. This runs `run_public.sh` -- the same script the evaluator runs -- in a scratch
copy of each instance's `files/`, and records how many bytes the tool actually produced before any
truncation. The committed records cannot answer this: the frozen driver stores out[:1500] after a
4000-byte truncation (llm_agent_driver.py:742), so the untruncated size was never persisted.

NOTHING is written into tasks/. Each instance is copied to a scratch directory first; the canonical
fingerprint is asserted before and after, because a test harness writing into the canonical tree
once cost a day and was misattributed to a remote tool outage (docs/incident_golden_corruption.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "opencode_probe/evidence/raw_output_audit.json"

# Caps proposed for the broker. The audit's job is to measure the headroom each one has, and to
# refuse a verdict when that headroom is under 8x.
CAPS = {"request_bytes": 2 * 1024 * 1024,
        "stdout_bytes": 1024 * 1024,
        "stderr_bytes": 1024 * 1024,
        "artifact_bytes": 8 * 1024 * 1024}

HEADROOM_FACTOR = 8

ARTIFACTS = {"p15_sta_handoff": [], "p16_spice_handoff": ["hspice_run.lis"]}
FAMILY_OP = {"p15_sta_handoff": "sta_public", "p16_spice_handoff": "spice_public"}

CLAIM = ("empirical transport headroom over the complete calibration set: every measured directory "
         f"left at least {HEADROOM_FACTOR}x headroom under each proposed cap")
NOT_CLAIMED = ("that a cap can never bind. Headroom over a finite calibration set says nothing "
               "about a future invocation. The runtime guarantee is separate and does not depend on "
               "this audit: an over-cap output is typed transport_output_limit, the episode is "
               "measurement-invalid, and no truncated output is delivered as an agent observation.")

# docs/opencode_probe_analysis_plan.md stage 1: all 12 of p15_eval_0004..0015, Base and BundleS.
FORMAL_PANEL = tuple(f"p15_eval_{i:04d}_{c}"
                     for i in range(4, 16) for c in ("base", "bundles"))


def canonical_fingerprint() -> str:
    h = hashlib.sha256()
    for p in sorted((REPO / "tasks").rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(REPO)).encode())
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def _find_tool(root: Path, name: str):
    """Locate a forwarder symlink under the shim mirror without hardcoding a tool version.

    The mirror is EDA_TOOL_ROOT/soft2/synopsys/<tool>/<VERSION>/.../bin/<name>, and the version is
    not this repository's business -- CLAUDE.md's rule is that nothing here hardcodes an EDA path.
    """
    hits = sorted(p for p in Path(root).rglob(f"bin/{name}")
                  if p.is_file() or p.is_symlink())
    return str(hits[0]) if hits else None


def tool_env() -> dict:
    """The frozen tool environment, read from the operator's private shim env.sh.

    `run_public.sh` resolves the tool as `${EDA_PT_CMD:-pt_shell}` and skips when `command -v` fails.
    The shim mirror is NOT on PATH -- env.sh sets only EDA_TOOL_ROOT and B04_HOST -- so the absolute
    shim path has to be supplied here or every instance records SKIP. It is discovered by glob, never
    hardcoded; if env.sh or the mirror is absent the audit records tool_ran=False rather than
    inventing a path.
    """
    env = dict(os.environ)
    shim = os.environ.get("EDA_SHIM_ENV", str(Path.home() / "eda-remote-shim/env.sh"))
    p = Path(shim)
    if not p.is_file():
        p = Path("/data1/tongsb/eda-remote-shim/env.sh")
    if p.is_file():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                k, _, v = line[len("export "):].partition("=")
                env.setdefault(k.strip(), v.strip().strip("'\""))
    root = env.get("EDA_TOOL_ROOT")
    if root and Path(root).is_dir():
        for var, name in (("EDA_PT_CMD", "pt_shell"), ("EDA_HSPICE_CMD", "hspice")):
            if var not in env:
                found = _find_tool(Path(root), name)
                if found:
                    env[var] = found
    return env


def measure(instance: Path, env: dict, timeout: int) -> dict:
    family = instance.parent.name
    # An upper bound on any request this instance can produce: the request carries a base64 copy of
    # a SUBSET of files/ (editable + canonical, never the generated file), so the whole directory
    # inflated by 4/3 bounds it from above. Bounding from above is what a cap needs.
    files_total = sum(p.stat().st_size for p in (instance / "files").rglob("*") if p.is_file())
    request_bound = -(-files_total * 4 // 3) + 4096       # base64 + JSON/framing slack
    with tempfile.TemporaryDirectory(prefix="rawaudit_") as td:
        work = Path(td) / "files"
        shutil.copytree(instance / "files", work)
        t0 = time.time()
        try:
            r = subprocess.run(["bash", "run_public.sh"], cwd=work, env=env,
                               capture_output=True, timeout=timeout)
            rc, out, err = r.returncode, r.stdout, r.stderr
            timed_out = False
        except subprocess.TimeoutExpired as e:
            rc, out, err = -1, e.stdout or b"", e.stderr or b""
            timed_out = True
        elapsed = time.time() - t0
        arts = {}
        for name in ARTIFACTS.get(family, []):
            f = work / name
            arts[name] = f.stat().st_size if f.is_file() else 0
    # "SKIP: <tool> not found" is what run_public.sh prints when the tool is unreachable. That is a
    # measurement of nothing, and is recorded as such rather than folded into a maximum.
    tool_ran = not out.startswith(b"SKIP:") and not timed_out
    return {"instance": instance.name, "family": family, "op": FAMILY_OP[family], "rc": rc,
            "stdout_bytes": len(out), "stderr_bytes": len(err),
            "artifact_bytes": arts, "elapsed_s": round(elapsed, 2),
            "files_total_bytes": files_total, "request_upper_bound_bytes": request_bound,
            "timed_out": timed_out, "tool_ran": tool_ran,
            "in_formal_panel": instance.name in FORMAL_PANEL,
            "stdout_head": out[:200].decode("utf-8", "replace")}


def _pct(values, q: float) -> int:
    if not values:
        return 0
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Measure raw public-tool output size across the complete calibration set. "
                    "Zero model calls.")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--limit", type=int, default=0,
                    help="0 = every instance. A non-zero value marks the record incomplete and "
                         "forfeits the verdict.")
    a = ap.parse_args()

    before = canonical_fingerprint()
    env = tool_env()
    instances = sorted(
        [p for p in (REPO / "tasks/p15_sta_handoff").iterdir() if (p / "files/run_public.sh").is_file()]
        + [p for p in (REPO / "tasks/p16_spice_handoff").iterdir() if (p / "files/run_public.sh").is_file()],
        key=lambda p: (p.parent.name, p.name))
    if a.limit:
        instances = instances[: a.limit]

    rows = []
    for i, p in enumerate(instances, 1):
        print(f"[{i}/{len(instances)}] {p.parent.name}/{p.name}", flush=True)
        rows.append(measure(p, env, a.timeout))
    after = canonical_fingerprint()
    if before != after:
        raise SystemExit("FATAL: the canonical task tree changed during the audit. "
                         "Restore with `git checkout -- tasks/` and find the writer.")

    ran = [r for r in rows if r["tool_ran"]]

    def mx(key):
        return max([r[key] for r in ran], default=0)

    art_max = max([v for r in ran for v in r["artifact_bytes"].values()], default=0)
    # The request bound does not depend on the tool having run, so it is taken over every measured
    # directory rather than only the ones that reached PrimeTime.
    req_max = max([r["request_upper_bound_bytes"] for r in rows], default=0)

    measured = {r["instance"] for r in rows}
    ran_names = {r["instance"] for r in ran}
    missing = [n for n in FORMAL_PANEL if n not in measured or n not in ran_names]
    panel_complete = not missing
    complete = (a.limit == 0) and panel_complete

    record = {
        "generated_by": "scripts/opencode_probe_raw_output_audit.py",
        "model_calls": 0,
        "claim": CLAIM,
        "not_claimed": NOT_CLAIMED,
        "headroom_factor": HEADROOM_FACTOR,
        "canonical_fingerprint": before,
        "n_instances": len(rows), "n_tool_ran": len(ran),
        "limit": a.limit, "complete": complete,
        "formal_panel": {"expected": list(FORMAL_PANEL),
                         "measured": sorted(n for n in FORMAL_PANEL if n in measured),
                         "missing": missing, "complete": panel_complete},
        "instances": rows,
        "max_stdout_bytes": mx("stdout_bytes"),
        "max_stderr_bytes": mx("stderr_bytes"),
        "max_artifact_bytes": art_max,
        "max_request_upper_bound_bytes": req_max,
        "p95_stdout_bytes": _pct([r["stdout_bytes"] for r in ran], 0.95),
        "p99_stdout_bytes": _pct([r["stdout_bytes"] for r in ran], 0.99),
        "p95_stderr_bytes": _pct([r["stderr_bytes"] for r in ran], 0.95),
        "p99_stderr_bytes": _pct([r["stderr_bytes"] for r in ran], 0.99),
        "caps": CAPS,
        "headroom": {
            "stdout_x": round(CAPS["stdout_bytes"] / mx("stdout_bytes"), 1) if mx("stdout_bytes") else None,
            "stderr_x": round(CAPS["stderr_bytes"] / mx("stderr_bytes"), 1) if mx("stderr_bytes") else None,
            "artifact_x": round(CAPS["artifact_bytes"] / art_max, 1) if art_max else None,
            "request_x": round(CAPS["request_bytes"] / req_max, 1) if req_max else None,
        },
    }
    enough = (len(ran) >= 1
              and mx("stdout_bytes") * HEADROOM_FACTOR <= CAPS["stdout_bytes"]
              and mx("stderr_bytes") * HEADROOM_FACTOR <= CAPS["stderr_bytes"]
              and art_max * HEADROOM_FACTOR <= CAPS["artifact_bytes"]
              and req_max * HEADROOM_FACTOR <= CAPS["request_bytes"])
    record["verdict"] = ("HEADROOM_ESTABLISHED" if (enough and complete)
                         else "INSUFFICIENT_HEADROOM" if not enough
                         else "INCOMPLETE")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in
                      ("n_instances", "n_tool_ran", "complete", "max_stdout_bytes",
                       "max_stderr_bytes", "max_artifact_bytes", "max_request_upper_bound_bytes",
                       "p95_stdout_bytes", "p99_stdout_bytes", "headroom", "verdict")}, indent=2))
    if missing:
        print(f"formal-panel directories missing or tool-absent: {missing}")
    return 0 if record["verdict"] == "HEADROOM_ESTABLISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
