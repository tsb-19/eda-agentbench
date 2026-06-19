#!/usr/bin/env python3
"""Calibrate P4 op-amp-sizing tasks from REAL Spectre golden AC sims.

The generator (generators/p4_amp_sizing_gen.py) emits OTA-sizing tasks with NULL
acceptance floors (no analytic windows -- the P4 settling-bug lesson). This script
grounds them: for each task it runs the GOLDEN deck through real Spectre AC,
measures the real DC gain / gain-bandwidth / phase margin, sets each spec floor =
golden_value * margin (margin < 1, so the golden clears its own floor), writes the
floors into hidden/spec.json, fills the prompt's __GAINMIN__/__GBWMIN__/__PMMIN__
placeholders, and flips metadata "calibrated" to true. It then VERIFIES (gate-in-one)
that the golden meets all three calibrated floors (SPEC_SCORE ~ 1.0) and the buggy
(under-compensated) deck does NOT (clearly lower) -- printing the margin so a
non-discriminating task is caught.

Run with the EDA shim sourced so `spectre` resolves to the forwarder:
    source /data1/tongsb/eda-remote-shim/env.sh
    python3 scripts/calibrate_p4_amp.py tasks/p4_spice_sim/generated_ota/* --apply

Without --apply it is a dry run (measures + reports, writes nothing).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eda_agentbench.tools.detector import ToolEnvironmentDetector  # noqa: E402
from eda_agentbench.tools.env_shim import EnvShim  # noqa: E402

_SPECS = ("gain_db", "gbw_hz", "pm_deg")


def _build_env() -> dict:
    """Reuse the agentic runner's tool-env construction (shim -> PATH)."""
    detector = ToolEnvironmentDetector()
    t = detector.detect_one("spectre")
    detected = [t] if (t and t.available) else []
    if not detected:
        sys.exit("ERROR: spectre not detected. Did you `source .../eda-remote-shim/env.sh`?")
    return EnvShim(detected).get_env()


def _run_deck(deck_text: str, scripts_dir: Path, spec: dict, env: dict,
              timeout: int) -> dict:
    """Simulate one deck in a throwaway workspace and score it against `spec`.

    Returns {measured: {...}, score: float|None, detail: str, raw: str, work: Path}.
    The work dir is left on disk (caller cleans up) so its ac.csv can be re-scored
    without re-simulating.
    """
    work = Path(tempfile.mkdtemp(prefix="calamp_"))
    (work / "circuit.scs").write_text(deck_text)
    for fn in ("run_public.sh", "measure_ac.py"):
        shutil.copy2(scripts_dir / fn, work / fn)
    (work / "spec_public.json").write_text(json.dumps({"specs": {}}))
    (work / "spec.json").write_text(json.dumps(spec))
    (work / "run_public.sh").chmod(0o755)

    subprocess.run(["bash", "run_public.sh"], cwd=work, env=env,
                   capture_output=True, text=True, timeout=timeout)
    return _score_ac(work, env)


def _score_ac(work: Path, env: dict) -> dict:
    """Score the existing work/ac.csv against work/spec.json (no re-sim)."""
    r = subprocess.run(
        [sys.executable, "measure_ac.py", "ac.csv", "spec.json", "--mode", "hidden"],
        cwd=work, env=env, capture_output=True, text=True)
    out = r.stdout
    res = {"measured": {}, "score": None, "detail": "", "raw": out, "work": work}
    metrics_path = work / "metrics.json"
    if metrics_path.is_file():
        try:
            res["measured"] = json.loads(metrics_path.read_text())
        except json.JSONDecodeError:
            pass
    for line in out.splitlines():
        if line.startswith("SPEC_SCORE:"):
            res["score"] = float(line.split(":", 1)[1])
        elif line.startswith("SPEC_DETAIL:"):
            res["detail"] = line.split(":", 1)[1].strip()
    return res


def _fmt(name: str, v: float) -> str:
    if v is None:
        return "?"
    if name == "gain_db":
        return f"{v:.1f} dB"
    if name == "gbw_hz":
        if v >= 1e6:
            return f"{v / 1e6:.3g} MHz"
        if v >= 1e3:
            return f"{v / 1e3:.3g} kHz"
        return f"{v:.3g} Hz"
    return f"{v:.1f} deg"


def calibrate_one(task_dir: Path, env: dict, args) -> dict:
    meta = json.loads((task_dir / "metadata.json").read_text())
    spec = json.loads((task_dir / "hidden" / "spec.json").read_text())
    golden = (task_dir / "solution" / "circuit.scs").read_text()
    buggy = (task_dir / "files" / "circuit.scs").read_text()
    scripts = task_dir / "files"

    # 1) Measure the golden (null floors -> score ignored; we want metrics.json).
    gm = _run_deck(golden, scripts, spec, env, args.timeout)
    m = gm["measured"]
    for k in _SPECS:
        if m.get(k) is None:
            shutil.rmtree(gm["work"], ignore_errors=True)
            return {"task": task_dir.name, "ok": False,
                    "why": f"golden missing {k} ({gm['raw'][:200]})"}

    # 2) Floors from real golden values * margin (margin < 1 so golden clears them).
    floors = {
        "gain_db": round(m["gain_db"] * args.margin_gain, 4),
        "gbw_hz": round(m["gbw_hz"] * args.margin_gbw, 6),
        "pm_deg": round(m["pm_deg"] * args.margin_pm, 4),
    }
    cal_spec = dict(spec)
    cal_spec["specs"] = {n: {"min": floors[n], "ramp": spec["specs"][n].get("ramp", 0.5)}
                         for n in _SPECS}

    # 3) Verify: golden (re-score its ac.csv, no re-sim) and buggy (one sim).
    (gm["work"] / "spec.json").write_text(json.dumps(cal_spec))
    g = _score_ac(gm["work"], env)
    b = _run_deck(buggy, scripts, cal_spec, env, args.timeout)
    shutil.rmtree(gm["work"], ignore_errors=True)
    shutil.rmtree(b["work"], ignore_errors=True)

    margin = (g["score"] or 0.0) - (b["score"] or 0.0)
    ok = (g["score"] is not None and g["score"] >= 1.0 - 1e-6
          and b["score"] is not None and margin >= args.min_margin)

    if args.apply and ok:
        (task_dir / "hidden" / "spec.json").write_text(json.dumps(cal_spec, indent=2) + "\n")
        prompt = (task_dir / "prompt.md").read_text()
        prompt = (prompt.replace("__GAINMIN__", _fmt("gain_db", floors["gain_db"]))
                        .replace("__GBWMIN__", _fmt("gbw_hz", floors["gbw_hz"]))
                        .replace("__PMMIN__", _fmt("pm_deg", floors["pm_deg"])))
        (task_dir / "prompt.md").write_text(prompt)
        meta["calibrated"] = True
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

    return {"task": task_dir.name, "ok": ok,
            "golden": g["score"], "buggy": b["score"], "margin": margin,
            "measured": {k: _fmt(k, m[k]) for k in _SPECS},
            "floors": {k: _fmt(k, floors[k]) for k in _SPECS},
            "buggy_detail": b["detail"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks", nargs="+", help="task directories")
    ap.add_argument("--apply", action="store_true", help="write floors+prompt+meta (else dry run)")
    ap.add_argument("--margin-gain", type=float, default=0.90, help="gain floor = golden*this")
    ap.add_argument("--margin-gbw", type=float, default=0.80, help="GBW floor = golden*this")
    ap.add_argument("--margin-pm", type=float, default=0.85, help="PM floor = golden*this")
    ap.add_argument("--min-margin", type=float, default=0.25, help="required golden-buggy SPEC_SCORE gap")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    env = _build_env()
    rows, n_ok = [], 0
    for t in args.tasks:
        td = Path(t).resolve()
        if not (td / "metadata.json").is_file():
            continue
        r = calibrate_one(td, env, args)
        rows.append(r)
        flag = "OK " if r["ok"] else "BAD"
        n_ok += int(r["ok"])
        if r["ok"]:
            mz = r["measured"]
            print(f"  {flag} {r['task']}  golden={r['golden']:.3f} buggy={r['buggy']:.3f} "
                  f"margin={r['margin']:.3f}  golden[{mz['gain_db']}, {mz['gbw_hz']}, "
                  f"{mz['pm_deg']}]  buggy:[{r['buggy_detail']}]", flush=True)
        else:
            print(f"  {flag} {r['task']}  {r.get('why', '')}  "
                  f"golden={r.get('golden')} buggy={r.get('buggy')} margin={r.get('margin')}", flush=True)
    print(f"\n{n_ok}/{len(rows)} tasks calibrated cleanly "
          f"({'APPLIED' if args.apply else 'dry run'}).")
    sys.exit(0 if n_ok == len(rows) and rows else 1)


if __name__ == "__main__":
    main()
