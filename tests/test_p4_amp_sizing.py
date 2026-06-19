"""Local, tool-free validation of the P4 op-amp-sizing AC measurement + scoring.

Runs the EXACT measure_ac.py source (embedded in the generator) against an
ANALYTIC two-stage Miller-OTA frequency response — two poles + a Miller RHP zero:

    H(f) = A0 * (1 - j f/fz) / ((1 + j f/fp1)(1 + j f/fp2))

so the load-bearing AC math (DC gain / gain-bandwidth / phase margin + the graded
min-spec scoring) is proven without any SPICE tool. Ground truth is the closed-form
magnitude (dB) and phase (deg) below; the measurement runs on a coarse decade sweep
(like a real `.ac`) and must recover the metrics within a small tolerance.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _gain_db(f, A0, fp1, fp2, fz):
    mag = (A0 * math.sqrt(1 + (f / fz) ** 2)
           / (math.sqrt(1 + (f / fp1) ** 2) * math.sqrt(1 + (f / fp2) ** 2)))
    return 20.0 * math.log10(mag)


def _phase_deg(f, fp1, fp2, fz):
    # RHP zero (1 - j f/fz): angle = -atan(f/fz); each pole: -atan(f/fp). Continuous (no wrap).
    return math.degrees(-math.atan(f / fz) - math.atan(f / fp1) - math.atan(f / fp2))


def _ota_bode(tmp: Path, A0, fp1, fp2, fz, fstart=1e0, fstop=1e11, ppd=30) -> Path:
    """Write an analytic Bode sweep to ac.csv (ppd points per decade)."""
    p = tmp / "ac.csv"
    n_dec = math.log10(fstop / fstart)
    npts = int(n_dec * ppd) + 1
    with open(p, "w") as fh:
        fh.write("# freq_hz gain_db phase_deg\n")
        for k in range(npts):
            f = fstart * 10.0 ** (k / ppd)
            fh.write(f"{f:.6e} {_gain_db(f, A0, fp1, fp2, fz):.6e} "
                     f"{_phase_deg(f, fp1, fp2, fz):.6e}\n")
    return p


def _exact_gbw_pm(A0, fp1, fp2, fz):
    """Exact unity-gain frequency (0 dB) and phase margin by fine bisection."""
    lo, hi = fp1, fp2 * 100.0
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if _gain_db(mid, A0, fp1, fp2, fz) > 0.0:
            lo = mid
        else:
            hi = mid
    gbw = math.sqrt(lo * hi)
    return gbw, 180.0 + _phase_deg(gbw, fp1, fp2, fz)


def _measure_script(tmp: Path) -> Path:
    from generators.p4_amp_sizing_gen import MEASURE_AC_PY
    p = tmp / "measure_ac.py"
    p.write_text(MEASURE_AC_PY)
    return p


def _run(script: Path, ac: Path, spec: Path, mode: str = "hidden") -> dict:
    out = subprocess.run(
        [sys.executable, str(script), str(ac), str(spec), "--mode", mode],
        capture_output=True, text=True, check=True,
    ).stdout
    res = {"raw": out}
    for line in out.splitlines():
        if line.startswith("SPEC_MEASURED:"):
            for tok in line.split(":", 1)[1].split():
                k, _, v = tok.partition("=")
                res[k] = None if v == "None" else float(v)
        elif line.startswith("SPEC_SCORE:"):
            res["score"] = float(line.split(":", 1)[1])
        elif line.startswith("SPEC_DETAIL:"):
            res["detail"] = line.split(":", 1)[1].strip()
    return res


# A nominal "golden" two-stage OTA: 60 dB DC gain, dominant pole 10 kHz,
# non-dominant pole 20 MHz, Miller RHP zero 50 MHz -> GBW ~10 MHz, PM ~50 deg.
A0, FP1, FP2, FZ = 1000.0, 1e4, 2e7, 5e7


def test_measures_gain_gbw_pm_matches_analytic(tmp_path):
    script = _measure_script(tmp_path)
    ac = _ota_bode(tmp_path, A0, FP1, FP2, FZ)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"specs": {
        "gain_db": {"min": 40.0, "ramp": 1.0},
        "gbw_hz": {"min": 1e6, "ramp": 1.0},
        "pm_deg": {"min": 45.0, "ramp": 1.0}}}))
    r = _run(script, ac, spec)
    gbw_exact, pm_exact = _exact_gbw_pm(A0, FP1, FP2, FZ)
    assert r["gain_db"] == pytest.approx(20 * math.log10(A0), abs=0.5)   # ~60 dB
    assert r["gbw_hz"] == pytest.approx(gbw_exact, rel=0.05)             # ~10 MHz
    assert r["pm_deg"] == pytest.approx(pm_exact, abs=2.0)               # ~50 deg


def test_scoring_separates_designs(tmp_path):
    """Golden meets gain/GBW/PM; a low-gain part loses gain credit; a too-fast part
    (GBW pushed into the 2nd pole) loses phase-margin credit. Golden must rank top."""
    script = _measure_script(tmp_path)

    def score(A0_, fp1_, fp2_, fz_, spec_cfg):
        ac = _ota_bode(tmp_path, A0_, fp1_, fp2_, fz_)
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps(spec_cfg))
        return _run(script, ac, spec)

    cfg = {"specs": {"gain_db": {"min": 55.0, "ramp": 1.0},
                     "gbw_hz": {"min": 8e6, "ramp": 1.0},
                     "pm_deg": {"min": 45.0, "ramp": 1.0}}}
    golden = score(A0, FP1, FP2, FZ, cfg)
    low_gain = score(30.0, FP1, FP2, FZ, cfg)            # 30 dB << 55 dB min
    # Too aggressive: dominant pole pushed up 10x -> GBW ~100 MHz collides with fp2 -> PM collapses.
    low_pm = score(A0, 1e5, FP2, FZ, cfg)

    assert golden["score"] > 0.95, golden
    assert low_gain["score"] < golden["score"], (low_gain, golden)
    assert low_pm["score"] < golden["score"], (low_pm, golden)
    # low_gain specifically loses gain credit; low_pm specifically loses pm credit
    # (both clearly below the golden's 1.0 on their axis).
    assert float(low_gain["detail"].split("gain_db=")[1].split()[0]) < 0.9, low_gain["detail"]
    assert float(low_pm["detail"].split("pm_deg=")[1].split()[0]) < 0.9, low_pm["detail"]


def test_dead_response_scores_zero(tmp_path):
    """A part with DC gain < 1 (never reaches 0 dB) is not a working amp -> score 0."""
    script = _measure_script(tmp_path)
    ac = _ota_bode(tmp_path, 0.5, FP1, FP2, FZ)          # A0=0.5 -> -6 dB, never crosses 0
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"specs": {
        "gain_db": {"min": 40.0, "ramp": 1.0},
        "gbw_hz": {"min": 1e6, "ramp": 1.0},
        "pm_deg": {"min": 45.0, "ramp": 1.0}}}))
    r = _run(script, ac, spec)
    assert r["score"] == pytest.approx(0.0, abs=1e-9)


def test_uncalibrated_spec_scores_zero(tmp_path):
    """Null targets (not yet calibrated) -> graded 0 + UNCALIBRATED flag."""
    script = _measure_script(tmp_path)
    ac = _ota_bode(tmp_path, A0, FP1, FP2, FZ)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"specs": {
        "gain_db": {"min": None, "ramp": 1.0},
        "gbw_hz": {"min": None, "ramp": 1.0},
        "pm_deg": {"min": None, "ramp": 1.0}}}))
    r = _run(script, ac, spec)
    assert r["score"] == pytest.approx(0.0, abs=1e-9)
    assert "UNCALIBRATED" in r["detail"]


def test_generator_emits_wellformed_task(tmp_path):
    """Offline structural check of P4AmpSizingGenerator.generate_one: required
    files, NULL floors (grounded later by calibration, never analytic), locked
    devices, and the under-compensation invariant (golden cc > buggy cc)."""
    from generators.p4_amp_sizing_gen import P4AmpSizingGenerator
    g = P4AmpSizingGenerator(seed=42, output_dir=tmp_path)
    td = g.generate_one(0)

    for rel in ("prompt.md", "metadata.json", "files/circuit.scs",
                "files/run_public.sh", "files/measure_ac.py", "files/spec_public.json",
                "hidden/run_hidden.sh", "hidden/spec.json", "solution/circuit.scs"):
        assert (td / rel).is_file(), f"missing {rel}"

    meta = json.loads((td / "metadata.json").read_text())
    assert meta["track"] == "p4_spice_sim"
    assert meta["calibrated"] is False
    assert meta["scoring"]["weights"]["spec_score"] == 0.6

    spec = json.loads((td / "hidden" / "spec.json").read_text())
    # NULL until a real Spectre golden sim grounds them (the settling-bug lesson).
    assert all(spec["specs"][k]["min"] is None for k in ("gain_db", "gbw_hz", "pm_deg"))
    assert set(spec["lock"]) >= {"cl_c", "m1_w", "m6_w"}

    def _cc(rel):
        for ln in (td / rel).read_text().splitlines():
            if ln.strip().startswith("parameters"):
                tok = [t for t in ln.split() if t.startswith("cc=")][0]
                return float(tok.split("=")[1])
        raise AssertionError("no parameters line")
    # buggy is under-compensated -> smaller Miller cap than the golden.
    assert _cc("solution/circuit.scs") > _cc("files/circuit.scs")

