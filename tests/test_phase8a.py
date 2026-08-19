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
def probe_mod():
    return _load(REPO / "scripts/phase8a_cost_probe.py", "p8a_probe")


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
    assert "Amendment 3" in txt or "修正案 3" in txt
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


def test_amendment3_records_that_the_cap_was_never_the_binding_constraint():
    """Arm 1 was stopped by the backend's balance, not by the preregistered Y200 cap.

    This is the amendment's whole point, and it is the kind of fact a preregistration is easiest to
    quietly lose: the cap READ as the operative stop rule for two amendments, and it never was one.
    Assert the cause is named in provider terms (402 / INSUFFICIENT_BALANCE), that the amendment says
    so plainly, and -- the discipline that matters -- that the two superseded projections stay
    visible rather than being edited into agreement with the outcome.

    Whitespace is normalised before matching: these are assertions about prose, and prose in this
    repository is hard-wrapped, so a claim must not pass or fail on where a line break happens to
    land.
    """
    txt = " ".join(PREREG.read_text().split())
    assert "402" in txt and "INSUFFICIENT_BALANCE" in txt, "name the provider's own verdict"
    assert "never the operative stop rule" in txt
    assert "164.07" in txt, "the unspent headroom is the evidence the cap did not bind"
    # superseded estimates must remain readable: 0.447 (Amdt 1) and the n=11 projection (Amdt 2)
    assert "0.447" in txt and "n = 11" in txt
    # the ledger figure must be labelled as frozen-rate-denominated, not as a provider bill
    assert "billing statement" in txt


def test_amendment3_applies_the_existing_abort_rule_rather_than_writing_a_new_one():
    """Block 02 aborted the same way block 01 did, so 5B.3 must be APPLIED, not re-legislated.

    A rule that gets rewritten each time it fires is not a rule. The second occurrence is the test of
    the first: same archive location, same whole-block re-execution, same money kept in the ledger,
    same run state left glob-visible so the invalid attempts stay countable.
    """
    for doc in (PREREG, PREREG_ZH):
        txt = doc.read_text()
        assert "block02_attempt1" in txt, f"{doc.name}: name the archive destination"
        assert "run_state_arm1_block02_attempt1.json" in txt, f"{doc.name}: keep the state visible"
        assert "5B.3" in txt, f"{doc.name}: cite the rule being applied"
    # and the ledger must survive the move: 17.3244 + 10.7598 live + 0.5597 + 7.2848 archived
    txt = PREREG.read_text()
    assert "35.9287" in txt
    assert abs((17.3244 + 10.7598 + 0.5597 + 7.2848) - 35.9287) < 1e-9


def test_aborted_spend_generalises_past_the_first_archived_pass(run_mod, tmp_path, monkeypatch):
    """_aborted_spend must sum EVERY archived pass, not just the one it was written for.

    There are now two. A glob that happened to match one pass would have looked correct for a week
    and then silently dropped block 02's Y7.2848 out of the cap arithmetic.
    """
    root = tmp_path / "aborted"
    for pas, trial, cost in (("block01_attempt1", "p15_eval_0005_typedcontract_r1", 0.5597),
                             ("block02_attempt1", "p15_eval_0006_base_r1", 0.7145),
                             ("block02_attempt1", "p15_eval_0006_bundles_r1", 0.5000)):
        d = root / pas / trial
        d.mkdir(parents=True)
        (d / "episode.json").write_text(json.dumps({"trial": trial, "total_cost": cost}))
    monkeypatch.setattr(run_mod, "ABORTED", root)
    assert run_mod._aborted_spend() == 1.7742


# ------------------------------------------------------------------ arm 2's cost-only gate
@pytest.mark.parametrize("spent,rate,expected_k", [
    (122.8175, 0.100, 6),      # 216 x 0.10 = ¥21.6 inside ¥67.18 -> full k
    (122.8175, 0.311, 6),      # exactly at the k=6 threshold (67.1825 / 216)
    (122.8175, 0.312, 4),      # a fen over it and k=6 is gone
    (122.8175, 0.500, 2),      # 144 x 0.50 = ¥72 does not fit; 72 x 0.50 = ¥36 does
    (122.8175, 1.000, None),   # nothing affordable -> arm 2 is not run
])
def test_cost_probe_k2_matches_the_frozen_formula(probe_mod, spent, rate, expected_k):
    """The implementation must agree with the preregistered arithmetic, at the boundary too.

    The boundary cases are the point. A gate that rounds in its own favour at r = 0.311 buys a k it
    cannot pay for, and the failure surfaces only when the account empties mid-arm -- which is
    exactly how arm 1 ended (prereg 5C.1).
    """
    k2, remaining, _ = probe_mod.k2_from(rate, spent)
    assert k2 == expected_k
    assert remaining == round(200.0 - spent - 10.0, 4)


def test_cost_probe_gate_also_respects_the_hard_cap_including_its_own_spend(probe_mod):
    """Section 2.2's formula predates the probe, so it does not subtract the probe's own money.
    Section 2.3's ¥200 cap does cover it, so the implementation checks both and the stricter binds.

    The arithmetic turns out to make that cross-check unreachable, and saying so is the point of the
    test. The formula holds back ¥10 and section 2.2 caps the probe at ¥3, so
    spent + probe + need <= spent + 10 + (190 - spent) = 200 always. A conflict needs probe > 10.
    So the cross-check can never veto a legitimately-run probe -- it is belt and braces, not a second
    opinion, and nobody should later "discover" it as dead code and delete it.

    Both halves are asserted: it stays silent while the probe honours its ceiling, and it does fire
    if the ceiling is ever breached.
    """
    spent, rate = 128.0, 0.4
    # within the ¥3 ceiling: the formula alone decides, the hard cap never disagrees
    for probe in (0.0, 1.5, 3.0, probe_mod.HOLDBACK):
        bare, _, _ = probe_mod.k2_from(rate, spent)
        withp, _, detail = probe_mod.k2_from(rate, spent, probe)
        assert withp == bare == 4
        assert all(d["fits_prereg_formula"] == d["fits_hard_200_cap"]
                   for d in detail if d["fits_prereg_formula"])
    # breach the ceiling and the cross-check earns its keep
    k, _, detail = probe_mod.k2_from(rate, spent, 15.0)
    assert k == 2, "a probe past the holdback must cost arm 2 a step of k"
    row4 = next(d for d in detail if d["k"] == 4)
    assert row4["fits_prereg_formula"] is True and row4["fits_hard_200_cap"] is False


def test_cost_probe_writes_outside_the_grading_glob(probe_mod, report_mod):
    """Probe custody must not be reachable by the analysis glob.

    evidence/episodes/*/episode.json is what _collect() grades and what spend sums. Six DeepSeek
    probe episodes landing there would enter arm 1's panel as if they were Qwen panel data -- a
    different model, a different arm and instances the design excludes, all silently pooled.
    """
    probe = probe_mod.PROBE_CUSTODY.resolve()
    graded = report_mod.EV.resolve() / "episodes"
    assert graded not in probe.parents and probe != graded
    assert "cost_probe" in probe.name


def test_cost_probe_runs_only_pilot_instances(probe_mod):
    """Belt and braces: even if a probe episode reached the grader it could not become a panel point.

    Section 2 excludes p15_eval_0001..0003 from the primary analysis, and the arm-1 report lists them
    in pilot_instances_excluded_from_primary. The probe draws from that set only.
    """
    pilots = {"p15_eval_0001", "p15_eval_0002", "p15_eval_0003"}
    assert set(probe_mod.PROBE_INSTANCES) <= pilots
    assert set(probe_mod.PROBE_INSTANCES) & set(f"p15_eval_{i:04d}" for i in range(4, 16)) == set()


def test_cost_probe_cannot_read_a_score(probe_mod):
    """A cost gate that can see an outcome is not a cost gate.

    Asserted on the source rather than by mocking, because the guarantee is 'this code has no path to
    a score at all', which a behavioural test on one call path would not establish.
    """
    src = (REPO / "scripts/phase8a_cost_probe.py").read_text()
    for forbidden in ("total_score", "semantic_binding", "_regrade", "grade_sta_handoff"):
        assert forbidden not in src.split('"""')[2], f"the probe must not reference {forbidden}"


def test_cost_probe_enforces_its_own_spending_ceiling(probe_mod):
    """Section 2.2 says the probe spends <¥3. A stated limit the code does not enforce is not one."""
    src = (REPO / "scripts/phase8a_cost_probe.py").read_text()
    assert "--max-probe-cny" in src and "probe_ceiling" in src
    assert "max_probe_cny" in src


def test_arm_selects_its_own_models_config(run_mod):
    """--models must follow --arm, not default to arm 1's file.

    Running arm 2 under models_arm1.json would resolve the runner's entry BY NAME to qwen3.7-max, so
    the S3 arm would have measured the S2-F model while billing at Qwen's output rate. The arm is not
    a flag anyone should have to remember to change.
    """
    src = RUN_SCRIPT.read_text()
    assert 'f"phase8a/models_arm{a.arm}.json"' in src
    assert '"--model-name", model_name' in src
    assert '"PHASE8A_MODEL_NAME": model_name' in src
    # and the single-entry rule must be enforced wherever the name is resolved
    assert "must hold exactly one model entry" in src


def test_arm2_models_config_is_single_entry_and_uses_frozen_deepseek_rates():
    """Denominate arm 2's ledger exactly as arm 1's and the frozen 72: comparability needs one unit.

    reports/evidence/*/frozen_config.json records DeepSeek-V4-Pro at input 12 / output 24 CNY per 1M.
    Section 2.2 notes the provider may bill a cheaper tier; pinning the frozen rate means this ledger
    can overstate real spend, which is the safe direction for a cap.
    """
    cfg = json.loads((REPO / "phase8a/models_arm2.json").read_text())
    entries = [m for m in cfg["models"] if not str(m.get("name", "")).startswith("_")]
    assert len(entries) == 1
    e = entries[0]
    assert e["model_id"] == "deepseek-v4-pro"
    assert e["api_base"] == "https://tokenrhythm.studio/v1"
    assert (e["price_in_per_m"], e["price_out_per_m"]) == (12.0, 24.0)
    assert e["api_key_env"] in ("API_KEY", "MIMO_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY")
    assert "sk-" not in json.dumps(cfg), "no credential value may be stored in a config"
