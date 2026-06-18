"""Local, tool-free validation of the P4 damping-design measurement + scoring.

Runs the EXACT measure_specs.py source (embedded in the generator) against
analytic second-order RLC step responses, so the load-bearing waveform math
(overshoot / settling / propagation delay + the graded scoring) is proven
without any SPICE tool. Overshoot has a closed form for an underdamped step:
    OS_fraction = exp(-pi*zeta / sqrt(1 - zeta^2))
which is the ground truth we check the measurement against.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _step_response(zeta: float, w0: float, v_final: float, t_edge: float,
                   t_end: float, dt: float):
    """Analytic series-RLC step response (output across C). Returns t, vin, vout."""
    t = np.arange(0.0, t_end, dt)
    vin = np.where(t >= t_edge, v_final, 0.0)
    tp = t - t_edge
    vout = np.zeros_like(t)
    post = tp >= 0
    x = tp[post]
    if zeta < 1.0:
        wd = w0 * math.sqrt(1.0 - zeta ** 2)
        env = np.exp(-zeta * w0 * x)
        vout[post] = v_final * (1.0 - env * (np.cos(wd * x)
                                + (zeta / math.sqrt(1.0 - zeta ** 2)) * np.sin(wd * x)))
    elif abs(zeta - 1.0) < 1e-9:
        vout[post] = v_final * (1.0 - np.exp(-w0 * x) * (1.0 + w0 * x))
    else:
        s = math.sqrt(zeta ** 2 - 1.0)
        s1 = -w0 * (zeta - s)
        s2 = -w0 * (zeta + s)
        # v_c(t) = V[1 + (s2 e^{s1 t} - s1 e^{s2 t})/(s1 - s2)]; v_c(0)=0, v_c'(0)=0.
        vout[post] = v_final * (1.0 + (s2 * np.exp(s1 * x) - s1 * np.exp(s2 * x)) / (s1 - s2))
    return t, vin, vout


def _write_wave(tmp: Path, t, vin, vout) -> Path:
    p = tmp / "wave.csv"
    with open(p, "w") as f:
        f.write("# t v_in v_out\n")
        for i in range(len(t)):
            f.write(f"{t[i]:.6e} {vin[i]:.6e} {vout[i]:.6e}\n")
    return p


def _measure_script(tmp: Path) -> Path:
    from generators.p4_damping_gen import MEASURE_PY
    p = tmp / "measure_specs.py"
    p.write_text(MEASURE_PY)
    return p


def _run(script: Path, wave: Path, spec: Path, mode: str = "hidden") -> dict:
    out = subprocess.run(
        [sys.executable, str(script), str(wave), str(spec), "--mode", mode],
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


# Fixed L,C => w0; R sets zeta. L=1e-6, C=1e-9 => w0 = 1/sqrt(LC).
W0 = 1.0 / math.sqrt(1e-6 * 1e-9)
V_FINAL = 1.8
T_EDGE = 1e-9


@pytest.mark.parametrize("zeta", [0.2, 0.3, 0.5, 0.707])
def test_overshoot_matches_analytic(tmp_path, zeta):
    """Measured overshoot must match the closed-form underdamped overshoot."""
    expected_os = math.exp(-math.pi * zeta / math.sqrt(1 - zeta ** 2)) * 100.0
    # Sim long enough to capture the full ring-down.
    t_end = T_EDGE + 12.0 / (zeta * W0)
    dt = (2 * math.pi / W0) / 400.0   # ~400 samples per ringing period
    t, vin, vout = _step_response(zeta, W0, V_FINAL, T_EDGE, t_end, dt)
    script = _measure_script(tmp_path)
    wave = _write_wave(tmp_path, t, vin, vout)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "v_final": V_FINAL, "t_edge": T_EDGE,
        "specs": {"t_pd": {"max": 1e-6, "ramp": 1.0},
                  "overshoot": {"max": 5.0, "ramp": 1.0},
                  "t_settle": {"max": 1e-3, "ramp": 1.0}},
    }))
    r = _run(script, wave, spec)
    assert r["overshoot"] == pytest.approx(expected_os, abs=1.0), \
        f"zeta={zeta}: measured {r['overshoot']} vs analytic {expected_os}"


def test_overdamped_has_no_overshoot(tmp_path):
    t_end = T_EDGE + 30.0 / W0
    dt = (2 * math.pi / W0) / 400.0
    t, vin, vout = _step_response(1.8, W0, V_FINAL, T_EDGE, t_end, dt)
    script = _measure_script(tmp_path)
    wave = _write_wave(tmp_path, t, vin, vout)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "v_final": V_FINAL, "t_edge": T_EDGE,
        "specs": {"t_pd": {"max": 1e-6, "ramp": 1.0},
                  "overshoot": {"max": 5.0, "ramp": 1.0},
                  "t_settle": {"max": 1e-3, "ramp": 1.0}},
    }))
    r = _run(script, wave, spec)
    assert r["overshoot"] == pytest.approx(0.0, abs=0.5)


def test_scoring_separates_designs(tmp_path):
    """A well-damped design (zeta~0.7) meets all 3 specs; an underdamped one
    (zeta=0.3) blows the overshoot+settling budget; an overdamped one (zeta=2.5)
    blows the delay budget. Scores must be ordered well-damped > others."""
    script = _measure_script(tmp_path)

    def score_for(zeta, spec_cfg):
        t_end = T_EDGE + 14.0 / (zeta * W0)
        dt = (2 * math.pi / W0) / 400.0
        t, vin, vout = _step_response(zeta, W0, V_FINAL, T_EDGE, t_end, dt)
        wave = _write_wave(tmp_path, t, vin, vout)
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps(spec_cfg))
        return _run(script, wave, spec)

    # Calibrate caps around the zeta~0.7 "golden": measure it first, then add margin.
    base_cfg = {"v_final": V_FINAL, "t_edge": T_EDGE,
                "specs": {"t_pd": {"max": 1e9, "ramp": 1.0},
                          "overshoot": {"max": 1e9, "ramp": 1.0},
                          "t_settle": {"max": 1e9, "ramp": 1.0}}}
    g = score_for(0.707, base_cfg)
    caps = {"v_final": V_FINAL, "t_edge": T_EDGE,
            "specs": {"t_pd": {"max": g["t_pd"] * 1.30, "ramp": 1.0},
                      "overshoot": {"max": max(g["overshoot"] * 1.5, 6.0), "ramp": 1.0},
                      "t_settle": {"max": g["t_settle"] * 1.30, "ramp": 1.0}}}
    well = score_for(0.707, caps)
    under = score_for(0.3, caps)
    over = score_for(2.5, caps)

    assert well["score"] > 0.95, f"well-damped should pass all: {well}"
    assert under["score"] < well["score"], f"underdamped should lose credit: {under}"
    assert over["score"] < well["score"], f"overdamped should lose credit: {over}"
    # Underdamped specifically blows overshoot.
    assert "overshoot=0.0" in under["detail"] or float(
        under["detail"].split("overshoot=")[1].split()[0]) < 0.5, under["detail"]


def test_broken_waveform_scores_zero(tmp_path):
    """A flat/dead output (never reaches 50%) scores 0, not a crash."""
    t = np.arange(0.0, 1e-6, 1e-9)
    vin = np.where(t >= T_EDGE, V_FINAL, 0.0)
    vout = np.zeros_like(t)
    script = _measure_script(tmp_path)
    wave = _write_wave(tmp_path, t, vin, vout)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "v_final": V_FINAL, "t_edge": T_EDGE,
        "specs": {"t_pd": {"max": 1e-7, "ramp": 1.0},
                  "overshoot": {"max": 5.0, "ramp": 1.0},
                  "t_settle": {"max": 1e-6, "ramp": 1.0}},
    }))
    r = _run(script, wave, spec)
    assert r["score"] == pytest.approx(0.0, abs=1e-9)
