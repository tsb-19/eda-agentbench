"""Tool-free unit tests for scripts/validate_dataset.py.

No EDA tools, no network: the verdict/hash/cache logic is pure, and the main()
orchestration is exercised with validate_one monkeypatched (so no real grading).
Mirrors the mock style of tests/test_model_baseline.py.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import scripts.validate_dataset as vd  # noqa: E402


# --------------------------------------------------------------------------- #
# C1-C4 verdict logic
# --------------------------------------------------------------------------- #
def test_verdict_healthy():
    r = vd.evaluate_verdict(1.0, 0.9, 0.5, margin_tau=0.15)
    assert r["ok"] is True and r["failures"] == []
    assert abs(r["margin"] - 0.4) < 1e-9


def test_verdict_c1_golden_below_one():
    r = vd.evaluate_verdict(0.6, 0.5, 0.5, margin_tau=0.15)
    assert r["ok"] is False
    assert any(f.startswith("C1") for f in r["failures"])


def test_verdict_c2_no_margin():
    # buggy objective == golden objective -> a no-op scores like a fix
    r = vd.evaluate_verdict(1.0, 0.9, 0.9, margin_tau=0.15)
    assert r["ok"] is False
    assert any(f.startswith("C2") for f in r["failures"])
    assert abs(r["margin"]) < 1e-9


def test_verdict_c2_margin_just_below_tau():
    r = vd.evaluate_verdict(1.0, 0.90, 0.80, margin_tau=0.15)  # margin 0.10 < 0.15
    assert r["ok"] is False and any(f.startswith("C2") for f in r["failures"])


def test_verdict_c3_determinism():
    r = vd.evaluate_verdict(1.0, 0.9, 0.5, det_total=0.8,
                            check_determinism=True, margin_tau=0.15)
    assert r["ok"] is False and any(f.startswith("C3") for f in r["failures"])
    # identical re-grade passes C3
    r2 = vd.evaluate_verdict(1.0, 0.9, 0.5, det_total=1.0,
                             check_determinism=True, margin_tau=0.15)
    assert r2["ok"] is True


def test_verdict_c4_empty_must_fail():
    r = vd.evaluate_verdict(1.0, 0.9, 0.5, empty_passed=True,
                            check_empty=True, margin_tau=0.15)
    assert r["ok"] is False and any(f.startswith("C4") for f in r["failures"])
    r2 = vd.evaluate_verdict(1.0, 0.9, 0.5, empty_passed=False,
                             check_empty=True, margin_tau=0.15)
    assert r2["ok"] is True


def test_verdict_grading_errors_flagged():
    r = vd.evaluate_verdict(None, None, None, margin_tau=0.15)
    assert r["ok"] is False
    assert any(f.startswith("C1") for f in r["failures"])
    assert any(f.startswith("C2") for f in r["failures"])


# --------------------------------------------------------------------------- #
# task_hash
# --------------------------------------------------------------------------- #
def test_task_hash_stable_and_change_sensitive(tmp_path):
    d = tmp_path / "task"
    (d / "sub").mkdir(parents=True)
    (d / "metadata.json").write_text("{}")
    (d / "sub" / "f.txt").write_text("hello")
    h1 = vd.task_hash(d)
    assert h1 == vd.task_hash(d)            # stable
    (d / "sub" / "f.txt").write_text("world")
    assert vd.task_hash(d) != h1            # content change
    (d / "sub" / "g.txt").write_text("x")
    assert vd.task_hash(d) != h1            # added file


# --------------------------------------------------------------------------- #
# cache load/save
# --------------------------------------------------------------------------- #
def test_cache_roundtrip(tmp_path):
    p = tmp_path / "nested" / "cache.json"
    assert vd.load_cache(p) == {}           # missing -> {}
    vd.save_cache(p, {"k": {"hash": "abc", "verdict": {"ok": True}}})
    assert vd.load_cache(p)["k"]["hash"] == "abc"
    p.write_text("{ not json")
    assert vd.load_cache(p) == {}           # corrupt -> {}


# --------------------------------------------------------------------------- #
# main() orchestration (validate_one monkeypatched -> no real grading)
# --------------------------------------------------------------------------- #
def _make_tasks(root: Path, names):
    for n in names:
        d = root / n
        d.mkdir(parents=True)
        (d / "metadata.json").write_text(json.dumps({"task_id": n, "track": "t"}))
        (d / "body.txt").write_text(n)
    return root


def _fake_validate_one(calls):
    def inner(task_dir, loader, **kw):
        calls.append(task_dir.name)
        if "bad" in task_dir.name:
            return {"task_id": task_dir.name, "track": "t", "golden": 0.6,
                    "buggy": 0.6, "margin": 0.0, "ok": False,
                    "failures": ["C1:golden=0.600<1.0"]}
        return {"task_id": task_dir.name, "track": "t", "golden": 1.0,
                "buggy": 0.5, "margin": 0.5, "ok": True, "failures": []}
    return inner


def test_main_exit_code_and_offenders(tmp_path, monkeypatch):
    root = _make_tasks(tmp_path / "ds", ["task_good", "task_bad"])
    calls = []
    monkeypatch.setattr(vd, "validate_one", _fake_validate_one(calls))
    cache = tmp_path / "cache.json"
    rc = vd.main(["--tasks-root", str(root), "--glob", "*", "--cache", str(cache)])
    assert rc == 1                          # one offender -> nonzero
    assert sorted(calls) == ["task_bad", "task_good"]

    # all-good dataset -> exit 0
    root2 = _make_tasks(tmp_path / "ds2", ["task_good1", "task_good2"])
    rc2 = vd.main(["--tasks-root", str(root2), "--glob", "*", "--no-cache"])
    assert rc2 == 0


def test_changed_reuses_cache_until_file_edited(tmp_path, monkeypatch):
    root = _make_tasks(tmp_path / "ds", ["task_good", "task_good2"])
    calls = []
    monkeypatch.setattr(vd, "validate_one", _fake_validate_one(calls))
    cache = tmp_path / "cache.json"

    # run 1: populate cache (grades both)
    vd.main(["--tasks-root", str(root), "--glob", "*", "--cache", str(cache)])
    assert len(calls) == 2

    # run 2 with --changed: nothing changed -> 0 re-graded
    calls.clear()
    rc = vd.main(["--tasks-root", str(root), "--glob", "*", "--cache", str(cache), "--changed"])
    assert calls == [] and rc == 0          # reused from cache, still valid

    # edit one task -> only it re-grades
    calls.clear()
    (root / "task_good" / "body.txt").write_text("CHANGED")
    vd.main(["--tasks-root", str(root), "--glob", "*", "--cache", str(cache), "--changed"])
    assert calls == ["task_good"]


def test_changed_reuse_preserves_failure_in_report(tmp_path, monkeypatch):
    # A cached FAILURE on an unchanged task must still make --changed exit nonzero.
    root = _make_tasks(tmp_path / "ds", ["task_bad"])
    monkeypatch.setattr(vd, "validate_one", _fake_validate_one([]))
    cache = tmp_path / "cache.json"
    assert vd.main(["--tasks-root", str(root), "--glob", "*", "--cache", str(cache)]) == 1
    # unchanged + --changed: reused cached failure -> still nonzero, no re-grade
    calls = []
    monkeypatch.setattr(vd, "validate_one", _fake_validate_one(calls))
    rc = vd.main(["--tasks-root", str(root), "--glob", "*", "--cache", str(cache), "--changed"])
    assert rc == 1 and calls == []
