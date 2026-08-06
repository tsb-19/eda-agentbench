#!/usr/bin/env python3
"""Phase-5D SPICE protocol-repair regressions. Proves:
  (a) modifying the immutable circuit_core.sp is detected by the anti-cheat (a real violation);
  (b) build_deck.py regenerates circuit_built.sp from circuit_core.sp + meas_config (derived);
  (c) circuit_built.sp is NOT a forbidden file (its regeneration does not trip the anti-cheat —
      this is the Phase-5C false-positive fix);
  (d) the SPICE run_public workflow executes end-to-end on real HSPICE (skip if tool absent).
"""
import json, os, sys, shutil, subprocess, tempfile
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from eda_agentbench.agentic.workspace import snapshot_workspace, compute_file_changes, detect_forbidden_modifications  # noqa: E402

INST = REPO / "tasks/p16_spice_handoff/p16_eval_0001_base"


def _meta():
    return json.loads((INST / "metadata.json").read_text())


def test_core_modification_detected():
    """Editing circuit_core.sp (forbidden/immutable) is a real anti-cheat violation."""
    work = Path(tempfile.mkdtemp(prefix="repair_"))
    try:
        shutil.copytree(INST / "files", work, dirs_exist_ok=True)
        meta = _meta(); forbidden = meta["files"]["forbidden"]
        before = snapshot_workspace(work)
        (work / "circuit_core.sp").write_text((work / "circuit_core.sp").read_text() + "\n* TAMPER\n")
        after = snapshot_workspace(work)
        changes = compute_file_changes(before, after)
        clean, violations = detect_forbidden_modifications(changes, forbidden)
        assert not clean and any("circuit_core.sp" in v for v in violations), \
            f"core modification NOT detected: clean={clean} violations={violations}"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_derived_deck_not_forbidden():
    """circuit_built.sp is derived (not in forbidden) -> regenerating it is not a violation."""
    meta = _meta()
    forbidden = meta["files"]["forbidden"]
    assert "circuit_core.sp" in forbidden, "immutable core must be forbidden"
    assert "circuit_built.sp" not in forbidden, "derived deck must NOT be forbidden (Phase-5C false-positive fix)"
    assert "circuit_built.sp" not in meta["files"]["visible"], "derived deck must not be a shipped visible file"


def test_build_deck_regenerates_from_core():
    """build_deck.py reads the immutable core + meas_config -> circuit_built.sp with the right params."""
    work = Path(tempfile.mkdtemp(prefix="repair_bd_"))
    try:
        shutil.copytree(INST / "files", work, dirs_exist_ok=True)
        cfg = {"corner": "SS_0p9_-40", "load_condition": "light", "metric": "gain"}
        (work / "meas_config.json").write_text(json.dumps(cfg))
        r = subprocess.run([sys.executable, "build_deck.py"], cwd=str(work), capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, f"build_deck failed: {r.stderr}"
        deck = (work / "circuit_built.sp").read_text()
        assert ".param av=100" in deck and "cload=1e-12" in deck, f"deck not regenerated with core params: {deck[:120]}"
        # core unchanged by build_deck
        assert "{av}" in (work / "circuit_core.sp").read_text(), "build_deck must not mutate the immutable core"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_run_public_executes_real_hspice():
    hspice = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice"
    if not Path(hspice).exists() or not INST.is_dir():
        return  # skip when tool/instance absent
    work = Path(tempfile.mkdtemp(prefix="repair_rp_"))
    try:
        shutil.copytree(INST / "files", work, dirs_exist_ok=True)
        env = dict(os.environ); env["EDA_HSPICE_CMD"] = hspice
        env["EDA_TOOL_ROOT"] = "/data1/tongsb/eda-remote-shim/EDA"; env["B04_HOST"] = "tsb@b04"
        (work / "meas_config.json").write_text(json.dumps({"corner": "SS_0p9_-40", "load_condition": "light", "metric": "gain"}))
        r = subprocess.run(["bash", "run_public.sh"], cwd=str(work), env=env, capture_output=True, text=True, timeout=240)
        assert r.returncode == 0, f"run_public failed: {r.stdout[-300:]}"
        assert "gain_db" in (r.stdout + (work / "hspice_run.lis").read_text(errors="ignore") if (work / "hspice_run.lis").is_file() else r.stdout)
    finally:
        shutil.rmtree(work, ignore_errors=True)
