"""Regression tests for the Phase-8A STA power expansion.

Phase-8A re-runs the frozen Phase-7A design at k=6 on a replacement backend, because the frozen
gateway no longer serves the models. Two things must be true for it to mean anything:

  1. The design really is Phase-7A's, changed ONLY in k and backend. If an instance, a condition or
     the blocking principle drifted, the comparison is not the comparison that was claimed.
  2. The frozen artifact must be untouched. Phase-8A writes nothing under reports/, because
     frozen_membership_verify.py scans all of reports/ for `path -> sha256` pairs -- an early draft
     that wrote there drove the pin count 1065 -> 1979 and silently resolved one of the two expected
     mismatches. See phase8a/README.md.

Also locks the budget rule (cost-only, never outcome-dependent) and the no-pooling declaration.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCHED_SCRIPT = REPO / "scripts/phase8a_schedule.py"
RUN_SCRIPT = REPO / "scripts/phase8a_run.py"
REPORT_SCRIPT = REPO / "scripts/phase8a_report.py"
ARM1 = REPO / "phase8a/evidence/schedule_arm1.json"
PREREG = REPO / "docs/phase8a_prereg.md"
PREREG_ZH = REPO / "docs/phase8a_prereg.zh.md"
COND = ["Base", "BundleS", "TypedContract"]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def sched_mod():
    return _load(SCHED_SCRIPT, "p8a_sched")


@pytest.fixture(scope="module")
def run_mod():
    return _load(RUN_SCRIPT, "p8a_run")


@pytest.fixture(scope="module")
def report_mod():
    return _load(REPORT_SCRIPT, "p8a_report")


@pytest.fixture(scope="module")
def arm1():
    assert ARM1.is_file(), "generate the arm-1 schedule before running these tests"
    return json.loads(ARM1.read_text())


# ------------------------------------------------------------------ the design is Phase-7A's
def test_instances_are_exactly_the_frozen_twelve(arm1):
    """No instance added, dropped, regenerated or reworded. Same panel, more reps."""
    sys.path.insert(0, str(REPO / "scripts"))
    import phase7a_sta12_specs as SPECS
    frozen = [s[0] for s in SPECS.STA12_SPECS]
    got = sorted({s["task_id"].rsplit("_", 1)[0] for s in arm1["flat"]})
    assert got == sorted(frozen)
    assert len(got) == 12
    assert arm1["n_instances"] == 12


def test_conditions_are_the_frozen_three_and_resolve_to_real_task_dirs(arm1):
    assert arm1["conditions"] == COND
    for slot in arm1["flat"]:
        d = REPO / "tasks/p15_sta_handoff" / slot["task_id"]
        assert d.is_dir(), f"{slot['task_id']} has no task directory"


def test_k_is_six_and_totals_are_216(arm1):
    assert arm1["reps_per_condition"] == 6
    assert arm1["episodes"] == 216
    assert arm1["blocks"] == 12
    assert arm1["episodes_per_block"] == 18
    assert arm1["counts"] == {c: 72 for c in COND}


def test_every_block_is_position_balanced(arm1):
    """Each condition exactly 6x per block, exactly 2x in each third, and each (cond, rep) once."""
    assert arm1["position_balance_all_blocks"] is True
    by = {}
    for s in arm1["flat"]:
        by.setdefault(s["block_id"], []).append(s)
    assert len(by) == 12
    for block, slots in by.items():
        slots = sorted(slots, key=lambda s: s["position_in_block"])
        assert len(slots) == 18, block
        assert Counter(s["condition"] for s in slots) == {c: 6 for c in COND}
        for t in range(3):
            seg = Counter(s["condition"] for s in slots[t * 6:(t + 1) * 6])
            assert seg == {c: 2 for c in COND}, f"{block} third {t} unbalanced: {seg}"
        assert all(v == 1 for v in Counter((s["condition"], s["rep"]) for s in slots).values())
        assert [s["position_in_block"] for s in slots] == list(range(18))


def test_reps_must_be_divisible_by_three(sched_mod):
    """Position balance is defined over thirds; k=5 cannot be balanced and must be refused."""
    with pytest.raises(SystemExit):
        sched_mod.build("Qwen3.7-Max-TR", 5, 1)


def test_schedule_is_deterministic_and_reproduces(sched_mod, arm1):
    """The DESIGN must reproduce byte-for-byte. code_commit_at_freeze_base is excluded because the
    freeze commit necessarily lands after the schedule is generated -- comparing it would make
    --check fail on every subsequent commit, which is a broken gate, not a detected mutation."""
    rebuilt = sched_mod.build(arm1["model"], 6, 1)
    drop = "code_commit_at_freeze_base"
    assert {k: v for k, v in rebuilt.items() if k != drop} == \
           {k: v for k, v in arm1.items() if k != drop}
    rc = subprocess.run([sys.executable, str(SCHED_SCRIPT), "--model", arm1["model"],
                         "--reps", "6", "--arm", "1", "--check"],
                        capture_output=True, text=True, cwd=str(REPO)).returncode
    assert rc == 0


def test_freeze_base_stamp_is_a_real_commit(arm1):
    stamp = arm1["code_commit_at_freeze_base"]
    assert len(stamp) == 40 and all(c in "0123456789abcdef" for c in stamp)
    r = subprocess.run(["git", "cat-file", "-t", stamp], capture_output=True, text=True,
                       cwd=str(REPO))
    assert r.stdout.strip() == "commit", f"{stamp} is not a commit in this repository"


def test_check_detects_a_mutated_schedule(sched_mod, arm1, tmp_path, monkeypatch):
    """--check must fail on a tampered design, or it certifies nothing."""
    tampered = dict(arm1)
    tampered["flat"] = arm1["flat"][:-1]          # drop one slot
    monkeypatch.setattr(sched_mod, "OUT", tmp_path)
    (tmp_path / "schedule_arm1.json").write_text(json.dumps(tampered, indent=2) + "\n")
    monkeypatch.setattr("sys.argv", ["s", "--model", arm1["model"], "--reps", "6",
                                     "--arm", "1", "--check"])
    assert sched_mod.main() == 1


def test_schedule_declares_it_is_not_poolable(arm1):
    assert "not_poolable_with" in arm1
    assert "phase7a" in arm1["not_poolable_with"]
    assert "different backend" in arm1["not_poolable_with"]


# ------------------------------------------------------------------ block-chunked execution
def test_block_split_preserves_the_frozen_order_exactly(run_mod, arm1):
    """Chunking must be a pure partition: concatenating the blocks rebuilds the frozen order."""
    blocks = run_mod._blocks_of(arm1)
    assert len(blocks) == 12
    assert [len(b) for _, b in blocks] == [18] * 12
    rebuilt = [s for _, slots in blocks for s in slots]
    assert rebuilt == arm1["frozen_execution_order"]


def test_block_split_never_straddles_a_block_id(run_mod, arm1):
    for block_id, slots in run_mod._blocks_of(arm1):
        assert {s["block_id"] for s in slots} == {block_id}


def test_incomplete_block_state_is_not_treated_as_done(run_mod, tmp_path):
    """A crashed block must be re-run, not silently skipped."""
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"status": "RUNNING", "episodes": [{}] * 18}))
    assert run_mod._done(p, 18) is False
    p.write_text(json.dumps({"status": "complete", "episodes": [{}] * 17}))
    assert run_mod._done(p, 18) is False
    p.write_text(json.dumps({"status": "complete", "episodes": [{}] * 18}))
    assert run_mod._done(p, 18) is True
    assert run_mod._done(tmp_path / "absent.json", 18) is False


def test_spend_accumulates_across_block_states(run_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(run_mod, "P8A", tmp_path)
    for i, amt in enumerate([1.5, 2.25, 3.0]):
        (tmp_path / f"run_state_arm1_block{i:02d}.json").write_text(json.dumps({"spent": amt}))
    assert run_mod._spent_so_far(1) == 6.75


# ------------------------------------------------------------------ the budget rule
@pytest.mark.parametrize("spent,rate,expected_k", [
    (130.0, 0.113, 6),     # cheap DeepSeek tier (¥3/¥6): 216 x 0.113 = ¥24 -> full k
    (130.0, 0.400, 4),     # 144 x 0.40 = ¥58 fits in ¥60; 216 x 0.40 = ¥86 does not
    (130.0, 0.454, 2),     # dear tier (¥12/¥24): only 72 x 0.454 = ¥33 fits -- k collapses to 2
    (130.0, 1.50, None),   # nothing affordable
    (195.0, 0.454, None),  # arm 1 overran -> arm 2 not run at all
])
def test_arm2_k_gate_is_cost_only(spent, rate, expected_k):
    """The prereg's rule: k2 = max k in {6,4,2} with 12*3*k*r <= 200 - spent - 10.

    It reads cost only; no score, rate or contrast may enter it. Note what the arithmetic says:
    if DeepSeek bills at the dear tier, arm 2 can only afford k=2 -- the exact coarseness Phase-8A
    exists to escape. That is a real constraint on what the S3 arm can conclude, not a bug."""
    remaining = 200.0 - spent - 10.0
    k2 = next((k for k in (6, 4, 2) if 12 * 3 * k * rate <= remaining), None)
    assert k2 == expected_k


def test_prereg_states_the_gate_is_cost_only():
    txt = PREREG.read_text()
    assert "reads **cost only**" in txt or "reads cost only" in txt.lower()
    assert "never reads a score" in txt


# ------------------------------------------------------------------ frozen artifact untouched
def test_no_phase8a_artifact_anywhere_under_reports():
    """The rule that a Phase-8A file must never enter the frozen pin scan region."""
    strays = sorted(str(p.relative_to(REPO)) for p in (REPO / "reports").rglob("*phase8a*"))
    assert strays == [], f"these would pollute the frozen pin count: {strays}"


def test_clean_tree_gate_exempts_only_its_own_outputs():
    """The preflight writes two custody files, so without an exemption the gate could never pass
    twice. The exemption must cover EXACTLY those two paths -- widening it would let real
    uncommitted code through on the way to spending money."""
    src = (REPO / "scripts/phase8a_preflight.py").read_text()
    assert 'OWN_OUTPUTS = {"phase8a/evidence/preflight.json", ' \
           '"phase8a/evidence/prerun_manifest.json"}' in src
    # and it must be a subtraction from git status, not a replacement of it
    assert 'git", "-C", str(REPO), "status", "--porcelain"' in src


def test_frozen_membership_baseline_is_unchanged():
    r = subprocess.run([sys.executable, "scripts/frozen_membership_verify.py",
                        "--expect", "docs/frozen_membership_baseline.json"],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, f"frozen membership drifted:\n{r.stdout[-800:]}"


def test_phase8a_outputs_are_declared_outside_reports(report_mod, sched_mod):
    for p in (report_mod.OUT_JSON, report_mod.OUT_MD, report_mod.EV, sched_mod.OUT):
        assert "phase8a" in str(p)
        assert f"{REPO}/reports" not in str(p)


# ------------------------------------------------------------------ analysis correctness
def test_sign_test_matches_hand_computed_values(report_mod):
    # 5 positive, 1 negative, 6 ties -> n=6 non-zero, k=5
    diffs = [0.5, 0.2, 0.1, 0.4, 0.3, -0.2, 0, 0, 0, 0, 0, 0]
    n, k, p = report_mod._sign_p(diffs)
    assert (n, k) == (6, 5)
    assert round(p, 5) == 0.21875          # 2 * (C(6,0)+C(6,1)) / 2^6
    assert report_mod._sign_p([0] * 12) == (0, 0, 1.0)
    n, k, p = report_mod._sign_p([1, 1, 1, 1])
    assert (n, k, round(p, 5)) == (4, 4, 0.125)


def test_report_declares_no_pooling_and_names_the_backend_change(report_mod):
    src = REPORT_SCRIPT.read_text()
    assert "NOT POOLABLE WITH PHASE-7A" in src
    assert "paratera" in src
    assert report_mod.PILOTS == ["p15_eval_0001", "p15_eval_0002", "p15_eval_0003"]


def test_report_uses_the_pinned_grader(report_mod):
    """Re-grading must go through the sha256-pinned grader, not a local reimplementation."""
    sys.path.insert(0, str(REPO / "scripts"))
    from frozen_membership_verify import SCAN_ROOT, collect_pins
    pins = collect_pins(SCAN_ROOT)
    assert "generators/p15_sta_handoff/grade_sta_handoff.py" in pins
    assert "from grade_sta_handoff import grade" in REPORT_SCRIPT.read_text()


# ------------------------------------------------------------------ preregistration is bilingual
def test_prereg_exists_in_both_languages_with_cross_links():
    assert PREREG.is_file() and PREREG_ZH.is_file()
    assert PREREG.read_text().startswith("**English | [中文](phase8a_prereg.zh.md)**")
    assert PREREG_ZH.read_text().startswith("**[English](phase8a_prereg.md) | 中文**")


def test_prereg_records_the_dead_frozen_endpoint_and_the_replacement():
    txt = PREREG.read_text()
    assert "llmapi.paratera.com" in txt
    assert "403" in txt
    assert "tokenrhythm.studio" in txt
    assert "S-2021.06-SP5" in txt          # the EDA apparatus did NOT drift
    assert "never pooled" in txt or "never summed" in txt


def test_prereg_answers_the_s3_objection():
    """The paper declines to fill S3; the prereg must meet that head-on, not hope it passes."""
    txt = PREREG.read_text()
    assert "main.tex:325" in txt
    assert "outcome-adaptive" in txt
    assert "withheld" in txt
