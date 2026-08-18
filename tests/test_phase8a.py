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
def preflight_mod():
    return _load(REPO / "scripts/phase8a_preflight.py", "p8a_preflight")


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
    """A crashed block must be re-run, not silently skipped. chain_executor writes state='COMPLETE'
    and completed_primary_slots only when every slot was filled."""
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"state": "RUNNING", "completed_primary_slots": 18}))
    assert run_mod._done(p, 18) is False
    p.write_text(json.dumps({"state": "COMPLETE", "completed_primary_slots": 17}))
    assert run_mod._done(p, 18) is False
    p.write_text(json.dumps({"state": "FAILED_INTEGRITY", "completed_primary_slots": 18}))
    assert run_mod._done(p, 18) is False
    p.write_text(json.dumps({"state": "COMPLETE", "completed_primary_slots": 18}))
    assert run_mod._done(p, 18) is True
    assert run_mod._done(tmp_path / "absent.json", 18) is False


def test_spend_accumulates_from_per_episode_custody(run_mod, monkeypatch, tmp_path):
    """Spend is summed from the per-episode records, not from a runner's self-report."""
    monkeypatch.setattr(run_mod, "CUSTODY", tmp_path)
    # Isolate the scheduled-slot sum from the archived-pass sum, which this asserts nothing about;
    # test_aborted_attempt_spend_still_counts_against_the_cap covers the two together. Without this
    # the assertion silently tracks whatever aborted passes happen to exist in the real evidence tree.
    monkeypatch.setattr(run_mod, "ABORTED", tmp_path / "no_aborted_passes")
    slots = []
    for i, amt in enumerate([0.61, 0.55, 0.72]):
        slots.append({"task_id": f"p15_eval_000{i}_base", "rep": 1})
        d = tmp_path / f"p15_eval_000{i}_base_r1"
        d.mkdir()
        (d / "episode.json").write_text(json.dumps(
            {"trial": d.name, "total_cost": amt,
             "custody": {"agentlog.sanitized.json": "h"}}))
    assert run_mod._spent_so_far({"frozen_execution_order": slots}) == 1.88


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


def test_clean_tree_gate_parses_porcelain_rather_than_a_stripped_blob(preflight_mod):
    """The exemption has to survive porcelain's leading space, and it did not.

    `git status --porcelain` emits `XY<space>PATH`, and for an unstaged modification X is itself a
    SPACE. Stripping the whole stdout before splitting decapitates the FIRST line's status field, so
    ln[3:] eats a path character ('hase8a/evidence/preflight.json') and the first path listed can
    never match OWN_OUTPUTS. The gate then blocks forever on its own output while printing a mangled
    path, and the documented exemption is a fiction -- it only ever 'passed' when the tree happened
    to be clean already. Grepping the source could not catch that; this exercises it.
    """
    dp = preflight_mod._dirty_paths
    both = (" M phase8a/evidence/preflight.json\n"
            " M phase8a/evidence/prerun_manifest.json\n")
    assert dp(both) == [], "both own outputs must be exempt regardless of line order"
    assert dp(" M phase8a/evidence/prerun_manifest.json\n"
              " M phase8a/evidence/preflight.json\n") == []
    # staged, and untracked, forms of the same two paths
    assert dp("M  phase8a/evidence/preflight.json\n") == []
    assert dp("?? phase8a/evidence/preflight.json\n") == []
    # anything else still fails the gate, and is reported with its status intact
    real = dp(" M scripts/llm_agent_driver.py\n M phase8a/evidence/preflight.json\n")
    assert real == [" M scripts/llm_agent_driver.py"]
    assert dp(" M docs/phase8a_prereg.md\n") == [" M docs/phase8a_prereg.md"]
    # a rename is dirty at its destination
    assert dp('R  a.py -> phase8a/evidence/preflight.json\n') == []
    assert dp('R  phase8a/evidence/preflight.json -> b.py\n') == \
        ['R  phase8a/evidence/preflight.json -> b.py']
    assert dp("") == [] and dp("\n") == []


def test_frozen_membership_baseline_is_unchanged():
    r = subprocess.run([sys.executable, "scripts/frozen_membership_verify.py",
                        "--expect", "docs/frozen_membership_baseline.json"],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, f"frozen membership drifted:\n{r.stdout[-800:]}"


def test_phase8a_outputs_are_declared_outside_reports(report_mod, sched_mod):
    for p in (report_mod.OUT_JSON, report_mod.OUT_MD, report_mod.EV, sched_mod.OUT):
        assert "phase8a" in str(p)
        assert f"{REPO}/reports" not in str(p)


# ------------------------------------------------------- a failed episode is never data
def test_run_driver_flags_episodes_with_no_model_call(run_mod, monkeypatch, tmp_path):
    """The smoke-test finding: when the driver refuses to start, the untouched workspace still
    grades and the arbiter's no-telemetry fallback reports measurement_valid=true. Such an episode
    must abort the run, not join the panel."""
    monkeypatch.setattr(run_mod, "CUSTODY", tmp_path)
    slots = [{"task_id": "p15_eval_0004_base", "rep": 1},
             {"task_id": "p15_eval_0004_bundles", "rep": 1}]
    ok = tmp_path / "p15_eval_0004_base_r1"; ok.mkdir()
    (ok / "episode.json").write_text(json.dumps(
        {"trial": ok.name, "total_cost": 0.61, "custody": {"agentlog.sanitized.json": "h"}}))
    assert run_mod._telemetry_faults(slots[:1]) == []

    dead = tmp_path / "p15_eval_0004_bundles_r1"; dead.mkdir()
    (dead / "episode.json").write_text(json.dumps(
        {"trial": dead.name, "total_cost": 0.0, "custody": {"result.json": "h"}}))
    faults = run_mod._telemetry_faults(slots)
    assert len(faults) == 1
    assert faults[0].startswith("p15_eval_0004_bundles_r1")
    assert "total_cost=0.0" in faults[0] and "no agentlog custody" in faults[0]


def test_aborted_attempt_spend_still_counts_against_the_cap(run_mod, report_mod, monkeypatch,
                                                            tmp_path):
    """An aborted block's episodes are discarded from the ANALYSIS but not from the LEDGER.

    Block 01 was aborted mid-way by a provider 502 window and re-executed whole. Its first pass is
    archived under evidence/aborted/ rather than deleted. That money was still paid, and the cap is
    about money, not validity -- so if the archive dropped out of the spend total, both the budget
    gate and the reported total would understate real spend, and prereg section 4's "summed episode
    cost must equal the reported total" would be false while looking true.
    """
    for mod, root in ((run_mod, tmp_path / "run"), (report_mod, tmp_path / "rep")):
        ab = root / "aborted" / "block01_attempt1" / "p15_eval_0005_typedcontract_r1"
        ab.mkdir(parents=True)
        (ab / "episode.json").write_text(json.dumps({"trial": ab.name, "total_cost": 0.5597}))
        monkeypatch.setattr(mod, "ABORTED", root / "aborted")
        assert mod._aborted_spend() == 0.5597

    monkeypatch.setattr(run_mod, "CUSTODY", tmp_path / "cust")
    (tmp_path / "cust" / "p15_eval_0006_base_r1").mkdir(parents=True)
    (tmp_path / "cust" / "p15_eval_0006_base_r1" / "episode.json").write_text(
        json.dumps({"trial": "p15_eval_0006_base_r1", "total_cost": 1.0}))
    monkeypatch.setattr(run_mod, "ABORTED", tmp_path / "run" / "aborted")
    slots = [{"task_id": "p15_eval_0006_base", "rep": 1}]
    assert run_mod._spent_so_far({"frozen_execution_order": slots}) == 1.5597


def test_aborted_archive_is_never_graded(report_mod):
    """The archive must sit outside evidence/episodes/, so _collect() cannot reach it.

    evidence/episodes/*/episode.json is the grading and spend glob. An archive nested one level
    deeper inside it would be silently re-graded as a live episode -- the same trial would then
    appear twice, once from the aborted pass and once from the re-run.
    """
    assert report_mod.ABORTED.name == "aborted"
    assert report_mod.ABORTED.parent == report_mod.EV.parent
    assert report_mod.ABORTED != report_mod.EV
    assert report_mod.ABORTED not in report_mod.EV.parents


def test_report_excludes_untelemetered_episodes_from_grading(report_mod):
    """Inclusion is asserted in code, not merely stated: an earlier aggregation in this project
    collapsed 70 episodes to 54 despite a written rule."""
    src = REPORT_SCRIPT.read_text()
    for marker in ("no_telemetry_custody", "no_cost", "no_submitted_artifact", "episode_error"):
        assert marker in src, marker
    assert "never graded" in src


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


@pytest.mark.parametrize("doc", [PREREG, PREREG_ZH])
def test_amendments_are_appended_never_folded_into_the_design(doc):
    """Each amendment is its own numbered section in BOTH languages.

    A preregistration edited to match what was done is not a preregistration. Amendment 1 raised the
    retry budget; Amendment 2 corrects the per-episode cost estimate and fixes the aborted-block
    rule. Section 2 must still read as it did before either.
    """
    txt = doc.read_text()
    assert "Amendment 1" in txt or "修正案 1" in txt
    assert "Amendment 2" in txt or "修正案 2" in txt
    assert "k = 6" in txt or "k = 6" in txt.replace("k=6", "k = 6")


def test_amendment2_pre_commits_the_smaller_panel_before_seeing_more_results(run_mod):
    """The cost correction must be recorded as a constraint accepted in ADVANCE.

    Measured spend is ~2x the Amendment-1 estimate, so the unchanged Y200 cap can no longer buy all
    12 instances. Deciding that after seeing which instances came out favourably would be the
    outcome-adaptive practice this program exists to prevent; deciding it before is just arithmetic.
    So the amendment must name the measured rate, keep the cap, and say the panel may stop short.
    """
    txt = PREREG.read_text()
    assert "0.962" in txt, "the measured per-episode cost must be named"
    assert "0.447" in txt, "the superseded Amendment-1 estimate must stay visible"
    assert "cap is unchanged" in txt or "cap stays" in txt
    assert "stop short" in txt or "fewer than 12" in txt
    # the runner's gate must be able to enforce it: a per-slot projection knob, and a stop-on-budget
    src = RUN_SCRIPT.read_text()
    assert "--per-slot" in src and '"stopped": "budget"' in src
