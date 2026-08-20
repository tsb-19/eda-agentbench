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


@pytest.mark.parametrize("bad", [5, 3, 1, 0, 7])
def test_reps_must_be_a_preregistered_k(sched_mod, bad):
    """k must come from the prereg's ladder {6,4,2}, not merely be divisible by 3.

    The predecessor of this test asserted `reps % 3 == 0` and justified it as "position balance is
    defined over thirds". That reason was false: a block is `reps` concatenated permutations, so every
    consecutive TRIPLE is a permutation for any reps, and k=5 is balanced in that sense. The guard's
    real effect was to refuse k=4 and k=2 -- two of the three preregistered values -- while waving
    through k=3 and k=9, which were never preregistered. Tying the guard to the ladder refuses more,
    not less, and makes an adaptive k impossible to express rather than only forbidden in prose.
    """
    with pytest.raises(SystemExit):
        sched_mod.build("Qwen3.7-Max-TR", bad, 1)


@pytest.mark.parametrize("k", [6, 4, 2])
def test_every_preregistered_k_generates_a_balanced_schedule(sched_mod, k):
    """All three rungs of the ladder must be executable BEFORE the cost gate picks one.

    Arm 1 ran at k=6, so k=4 and k=2 were never generated and their refusal stayed invisible until
    the arm-2 gate returned k=2. A preregistered contingency that the code cannot build is not a
    contingency. This test exercises every rung so the next one is never discovered at execution time.
    """
    m = sched_mod.build("DeepSeek-V4-Pro-TR", k, 2)
    assert m["position_balance_all_blocks"] is True
    assert m["blocks"] == 12 and m["episodes"] == 12 * 3 * k
    assert m["episodes_per_block"] == 3 * k
    # Position balance, re-derived here rather than trusted from the flag the generator set.
    for bid in {s["block_id"] for s in m["flat"]}:
        conds = [s["condition"] for s in m["flat"] if s["block_id"] == bid]
        assert len(conds) == 3 * k
        for g in range(k):                       # every consecutive triple is a full permutation
            assert sorted(conds[g * 3:(g + 1) * 3]) == sorted(sched_mod.CONDITIONS)
        for c in sched_mod.CONDITIONS:           # hence equal totals
            assert conds.count(c) == k


def test_the_per_third_claim_is_only_made_when_it_is_true(sched_mod):
    """The `method` string is part of the frozen record, so it may not assert a false property.

    'exactly reps/3 times in each third' is meaningless at k=2 and k=4. It must appear at k=6 (where
    arm 1's committed schedule already carries it, and --check would fail if it moved) and vanish
    below."""
    assert "each third" in sched_mod.build("Qwen3.7-Max-TR", 6, 1)["method"]
    for k in (4, 2):
        m = sched_mod.build("DeepSeek-V4-Pro-TR", k, 2)
        assert "each third" not in m["method"]
        assert "once per consecutive triple" in m["method"]


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
    assert run_mod._spent_so_far({"frozen_execution_order": slots}, tmp_path, "qwen3.7-max") == 1.88


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
    paths = [sched_mod.OUT]
    for arm in (1, 2):                      # every arm's outputs, not just the one that ran first
        paths.extend(report_mod._out(arm))
        paths.append(report_mod._ev(arm))
    for p in paths:
        assert "phase8a" in str(p)
        assert f"{REPO}/reports" not in str(p)


# ------------------------------------------------------- a failed episode is never data
def test_run_driver_flags_episodes_with_no_model_call(run_mod, monkeypatch, tmp_path):
    """The smoke-test finding: when the driver refuses to start, the untouched workspace still
    grades and the arbiter's no-telemetry fallback reports measurement_valid=true. Such an episode
    must abort the run, not join the panel."""
    slots = [{"task_id": "p15_eval_0004_base", "rep": 1},
             {"task_id": "p15_eval_0004_bundles", "rep": 1}]
    ok = tmp_path / "p15_eval_0004_base_r1"; ok.mkdir()
    (ok / "episode.json").write_text(json.dumps(
        {"trial": ok.name, "total_cost": 0.61, "custody": {"agentlog.sanitized.json": "h"}}))
    assert run_mod._telemetry_faults(slots[:1], tmp_path) == []

    dead = tmp_path / "p15_eval_0004_bundles_r1"; dead.mkdir()
    (dead / "episode.json").write_text(json.dumps(
        {"trial": dead.name, "total_cost": 0.0, "custody": {"result.json": "h"}}))
    faults = run_mod._telemetry_faults(slots, tmp_path)
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
        (ab / "episode.json").write_text(json.dumps({"trial": ab.name, "total_cost": 0.5597,
                                                     "model_name": "qwen3.7-max"}))
        monkeypatch.setattr(mod, "ABORTED", root / "aborted")
        assert mod._aborted_spend("qwen3.7-max") == 0.5597

    (tmp_path / "cust" / "p15_eval_0006_base_r1").mkdir(parents=True)
    (tmp_path / "cust" / "p15_eval_0006_base_r1" / "episode.json").write_text(
        json.dumps({"trial": "p15_eval_0006_base_r1", "total_cost": 1.0}))
    monkeypatch.setattr(run_mod, "ABORTED", tmp_path / "run" / "aborted")
    slots = [{"task_id": "p15_eval_0006_base", "rep": 1}]
    assert run_mod._spent_so_far({"frozen_execution_order": slots},
                                 tmp_path / "cust", "qwen3.7-max") == 1.5597


def test_aborted_archive_is_never_graded(report_mod):
    """The archive must sit outside evidence/episodes/, so _collect() cannot reach it.

    evidence/episodes/*/episode.json is the grading and spend glob. An archive nested one level
    deeper inside it would be silently re-graded as a live episode -- the same trial would then
    appear twice, once from the aborted pass and once from the re-run.
    """
    assert report_mod.ABORTED.name == "aborted"
    for arm in (1, 2):                      # true for every arm's tree, not only arm 1's
        ev = report_mod._ev(arm)
        assert report_mod.ABORTED.parent == ev.parent
        assert report_mod.ABORTED != ev
        assert report_mod.ABORTED not in ev.parents


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
    assert "Amendment 4" in txt or "修正案 4" in txt
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
    # Every arm's grading tree, and the real one: the predecessor of this line built
    # `EV / "episodes"` -- i.e. evidence/episodes/episodes, a path that has never existed -- so the
    # containment assertion below could not fail no matter where the probe wrote.
    for arm in (1, 2):
        graded = report_mod._ev(arm).resolve()
        assert graded.name in ("episodes", f"episodes_arm{arm}")
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


# ------------------------------------------------------------- arms are separate measurements
def test_arms_write_to_separate_custody_trees(run_mod, report_mod):
    """The runner and the grader must agree, per arm, on where episodes live.

    If they ever disagree, the driver's budget gate reads one tree while the report grades another --
    a study that spends against one ledger and reports from a different one.
    """
    for arm in (1, 2):
        assert run_mod._custody(arm) == report_mod._ev(arm)
    assert run_mod._custody(1) != run_mod._custody(2)
    assert run_mod._custody(1).name == "episodes", "arm 1's tree must not move; it is already written"


def test_arm2_trial_names_would_have_overwritten_arm1(run_mod):
    """The hazard that made separate trees necessary, asserted rather than described.

    A trial directory is `<task_id>_r<rep>` and `rep` restarts at 1 in every arm. Arm 1 ran k=6 and
    wrote reps 1..6; arm 2 runs k=2 and writes reps 1..2 -- the SAME 72 names. In one shared tree,
    arm 2 would have silently overwritten 72 of arm 1's 216 episodes with a different model's, and
    phase8a_report.py's single `episodes/*/episode.json` glob would have graded the mixture as one
    arm. The prereg's "different backend is a different measurement, never pooled" rule would have
    been broken by filename rather than by argument.

    This test is deliberately phrased as "the names DO collide", so it keeps passing (and keeps
    documenting the reason) as long as the two trees stay apart.
    """
    a1 = json.loads((REPO / "phase8a/evidence/schedule_arm1.json").read_text())
    a2p = REPO / "phase8a/evidence/schedule_arm2.json"
    if not a2p.is_file():
        pytest.skip("arm-2 schedule not generated yet")
    a2 = json.loads(a2p.read_text())
    n1 = {f"{s['task_id']}_r{s['rep']}" for s in a1["flat"]}
    n2 = {f"{s['task_id']}_r{s['rep']}" for s in a2["flat"]}
    assert n2 <= n1, "every arm-2 trial name is also an arm-1 trial name"
    assert len(n2) == 72
    # ... which is harmless ONLY because the trees are different.
    assert run_mod._custody(1) != run_mod._custody(2)


def test_aborted_spend_is_attributed_to_the_arm_that_paid_it(run_mod, report_mod, tmp_path,
                                                             monkeypatch):
    """An arm may not inherit another arm's discarded spend.

    Attribution is by the episode's own `model_name`, not by where the archive directory sits: a
    path is a weaker key than the record of which model was actually billed.
    """
    arch = tmp_path / "aborted"
    for name, model, cost in (("p0/t1", "qwen3.7-max", 1.5), ("p0/t2", "deepseek-v4-pro", 2.25),
                              ("p1/t3", "qwen3.7-max", 0.25)):
        d = arch / name
        d.mkdir(parents=True)
        (d / "episode.json").write_text(json.dumps({"model_name": model, "total_cost": cost}))
    monkeypatch.setattr(run_mod, "ABORTED", arch)
    monkeypatch.setattr(report_mod, "ABORTED", arch)
    for mod in (run_mod, report_mod):
        assert mod._aborted_spend("qwen3.7-max") == 1.75
        assert mod._aborted_spend("deepseek-v4-pro") == 2.25
    assert run_mod._aborted_spend(None) == 4.0, "no model filter still totals the whole archive"


def test_budget_default_is_the_arm_share_not_the_whole_cap(run_mod):
    """¥200 is the PROGRAM's cap, and _spent_so_far counts only the arm's own episodes.

    Defaulting --budget to 200 for arm 2 would therefore have authorised a second ¥200 on top of
    everything arm 1 and the cost probe already spent. The cap belongs to the program.
    """
    assert run_mod.PROGRAM_CAP == 200.0
    spend = run_mod._program_spend()
    assert spend > 0, "phase8a has spent real money; a zero here means the glob stopped matching"
    r = subprocess.run([sys.executable, str(RUN_SCRIPT), "--arm", "2", "--dry-run"],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["program_cap_cny"] == 200.0
    assert d["budget_cny"] < 100.0, "arm 2 may not be handed the whole cap again"
    assert round(d["budget_cny"] + d["spent_by_the_rest_of_phase8a_cny"], 4) == 200.0


def test_program_spend_counts_the_cost_probe(run_mod):
    """The probe's custody sits OUTSIDE the grading glob so it can never become a panel point.

    It must nonetheless sit INSIDE the spend glob: money paid is money paid (prereg 5B.3 rule 3), and
    a probe excluded from the ledger would quietly enlarge the cap by whatever it cost.
    """
    probe = REPO / "phase8a/evidence/cost_probe_arm2"
    if not probe.is_dir():
        pytest.skip("cost probe has not run")
    probe_total = round(sum(json.loads(f.read_text()).get("total_cost") or 0.0
                            for f in probe.glob("*/episode.json")), 4)
    assert probe_total > 0
    r = subprocess.run([sys.executable, str(RUN_SCRIPT), "--arm", "1", "--dry-run"],
                       capture_output=True, text=True, cwd=str(REPO))
    rest = json.loads(r.stdout)["spent_by_the_rest_of_phase8a_cny"]

    # From arm 1's point of view "the rest of Phase-8A" is the probe PLUS everything arm 2 has paid:
    # its live episodes, its archived aborted passes, and its replaced attempts. This asserted
    # equality with the probe alone while arm 2 had spent nothing, which made it accidentally true;
    # the composition is the actual property, so state it and let each part be non-zero or not.
    ev = REPO / "phase8a/evidence"
    arm2_live = sum(json.loads(f.read_text()).get("total_cost") or 0.0
                    for f in (ev / "episodes_arm2").glob("*/episode.json"))
    arm2_aborted = run_mod._aborted_spend("deepseek-v4-pro")
    arm2_replaced = run_mod._ledger_spend("deepseek-v4-pro")
    assert rest == round(probe_total + arm2_live + arm2_aborted + arm2_replaced, 4)
    assert rest >= probe_total, "the probe must never drop out of the spend glob"


def test_report_states_and_outputs_are_arm_scoped(report_mod):
    """Arm 2's report may not charge itself arm 1's invalid attempts, nor overwrite arm 1's file."""
    assert report_mod._out(1)[0].name == "phase8a_sta_report.json"
    assert report_mod._out(2)[0].name == "phase8a_sta_report_arm2.json"
    assert report_mod._out(1)[0] != report_mod._out(2)[0]
    s1 = {p.name for p in report_mod._states(1)}
    s2 = {p.name for p in report_mod._states(2)}
    assert s1 and all(n.startswith("run_state_arm1") for n in s1)
    assert not (s1 & s2)


def test_preflight_reads_k_from_the_cost_gate_and_fails_closed(preflight_mod, tmp_path,
                                                               monkeypatch):
    """Arm 1's k is in the prereg text; arm 2's is only knowable from the measured probe.

    Reading it from the gate's own output is what makes "no adaptive k" checkable: a schedule built
    at any other k cannot pass preflight. With no gate output there is no authority, so arm 2 must be
    refused rather than defaulted.
    """
    k, src = preflight_mod._authorized_k(1)
    assert k == 6 and "prereg" in src

    gate = preflight_mod._cost_gate_path()
    if gate.is_file():
        k2, src2 = preflight_mod._authorized_k(2)
        assert k2 == json.loads(gate.read_text())["k2"]
        assert k2 in (6, 4, 2), "k2 must come from the preregistered ladder"
        assert "cost gate" in src2

    monkeypatch.setattr(preflight_mod, "REPO", tmp_path)   # no gate output at all
    k3, src3 = preflight_mod._authorized_k(2)
    assert k3 is None and "MISSING" in src3


def test_preflight_is_arm_aware_in_every_path_that_names_an_arm(preflight_mod):
    """One forgotten literal is enough to preflight arm 1 while running arm 2."""
    src = (REPO / "scripts/phase8a_preflight.py").read_text()
    assert "ARM_MODELS_FMT" in src and "models_arm1.json" not in src.split("phase8a/README.md")[-1]
    assert preflight_mod.ARM_MODEL_TAG == {1: "Qwen3.7-Max-TR", 2: "DeepSeek-V4-Pro-TR"}
    assert preflight_mod.ARM_MODEL_NAME == {1: "qwen3.7-max", 2: "deepseek-v4-pro"}


def test_amendment4_records_the_gate_outcome_and_the_ceiling_overrun(probe_mod):
    """The amendment must agree with the gate's machine-readable output, in both languages.

    Prose in this repository is hard-wrapped, so claims are matched against whitespace-normalised
    text: a statement must not pass or fail on where a line break happens to land.
    """
    gate = probe_mod.REPO / "phase8a" / "reports" / "phase8a_arm2_cost_gate.json"
    if not gate.is_file():
        pytest.skip("cost gate has not run")
    g = json.loads(gate.read_text())
    en = " ".join(PREREG.read_text().split())
    zh = " ".join(PREREG_ZH.read_text().split())

    assert g["k2"] == 2
    assert str(g["probe"]["measured_rate_cny_per_episode"]) in en
    assert str(g["probe"]["spend_cny"]) in en and str(g["probe"]["spend_cny"]) in zh
    # The overrun is recorded as a deviation, not rounded away to the stated "<¥3".
    assert g["probe"]["within_ceiling"] is False
    assert "within_ceiling" in en and "0.0054" in en and "0.0054" in zh
    # k=4's near-miss is named, and the holdback was not spent to reach it.
    assert "4.95" in en and "4.95" in zh
    for k in g["arithmetic"]["candidates"]:
        if k["k"] == 4:
            assert k["fits_hard_200_cap"] is True and k["fits_prereg_formula"] is False


def test_amendment4_states_that_k2_costs_the_arm_its_resolution():
    """k=2 is the granularity Phase-8A existed to escape. The record must say so before the run,
    not discover it in the discussion afterwards."""
    en = " ".join(PREREG.read_text().split())
    zh = " ".join(PREREG_ZH.read_text().split())
    assert "not a powered test" in en
    assert "0, 0.5 or 1" in en and "0、0.5 或 1" in zh
    assert "last unfilled cell" in en and "尚未填写" in zh


def test_the_custody_gate_checks_separation_not_name_uniqueness(preflight_mod):
    """A first attempt at this gate asserted that arm 2's planned trial names appear under no other
    arm's tree. That can never hold: `rep` restarts at 1 per arm, so arm 2's k=2 names are a SUBSET
    of arm 1's k=6 names -- all 72 of them. The overlap is the hazard, and disjoint trees are what
    make it inert. A gate that demands unique names would either block arm 2 forever or invite
    someone to rename trials that arm 1 has already written and reported.
    """
    src = (REPO / "scripts/phase8a_preflight.py").read_text()
    assert "arm_custody_tree_is_disjoint_from_other_arms" in src
    assert "planned_trials_collide_with_no_other_arm" not in src

    pf = REPO / "phase8a/evidence/preflight.json"
    if not pf.is_file():
        pytest.skip("preflight has not run")
    d = json.loads(pf.read_text())
    if d.get("detail", {}).get("arm") != 2:
        pytest.skip("last preflight was not arm 2")
    c = d["detail"]["custody"]
    assert c["planned_trial_names_also_used_by_another_arm"] == 72, \
        "the overlap is expected; if it ever reaches 0 the trees or the naming changed"
    assert d["gates"]["arm_custody_tree_is_disjoint_from_other_arms"] is True
    assert d["gates"]["arm_custody_holds_only_this_arms_episodes"] is True


# ------------------------------------------------- replaced-attempt spend (Amendment 5, section 5E.3)
def test_replaced_attempt_cost_is_harvested_from_the_chain_log(run_mod, monkeypatch, tmp_path):
    """A replacement overwrites the previous attempt's episode.json, so its cost vanishes from the
    custody tree. Measured in arm 2 block 00: attempt 1 cost ¥0.5468, then two ¥0 attempts overwrote
    it and the tree reported ¥0 for a billed slot. The chain log is the only per-attempt cost record.
    """
    monkeypatch.setattr(run_mod, "ATTEMPT_LEDGER", tmp_path / "ledger.json")
    log = tmp_path / "chain_a2_b00.log"
    log.write_text(
        '[executor] run: ...\n'
        '{"trial": "t_bundles_r1", "total_score": 1.0, "cost": 0.8669, "error": null}\n'
        '[arbiter] ... -> ACCEPT\n'
        '{"trial": "t_base_r1", "total_score": 0.5, "cost": 0.5468, "error": null}\n'
        '[arbiter] ... -> REPLACE\n'
        '{"trial": "t_base_r1", "total_score": 0.5, "cost": 0.0, "error": null}\n'
        '[arbiter] ... -> REPLACE\n'
        '{"trial": "t_base_r1", "total_score": 0.5, "cost": 0.0, "error": null}\n'
        '[arbiter] ... -> STOP\n')
    new = run_mod._harvest_replaced_attempts(2, 0, "blk", "deepseek-v4-pro", log)

    # only the SUPERSEDED attempts: the last attempt's episode.json survives in custody
    assert [e["attempt"] for e in new] == [1, 2]
    assert run_mod._ledger_spend("deepseek-v4-pro") == 0.5468
    # the accepted single-attempt trial is not a replacement and must not be double counted
    assert all(e["trial"] == "t_base_r1" for e in new)
    # attributed by model, so one arm never inherits another's replaced spend
    assert run_mod._ledger_spend("qwen3.7-max") == 0.0


def test_replaced_attempt_spend_binds_both_the_program_cap_and_the_arm_budget(run_mod, monkeypatch,
                                                                             tmp_path):
    """Money paid is money paid. Replacements are caused by provider faults and faults cluster, so
    without this the cap slackens exactly during the hours that spend money for no data.
    """
    monkeypatch.setattr(run_mod, "P8A", tmp_path)
    monkeypatch.setattr(run_mod, "ABORTED", tmp_path / "aborted")
    monkeypatch.setattr(run_mod, "ATTEMPT_LEDGER", tmp_path / "ledger.json")
    (tmp_path / "ledger.json").write_text(json.dumps({"entries": [
        {"cost_cny": 0.5468, "model_name": "deepseek-v4-pro"},
        {"cost_cny": 0.0, "model_name": "deepseek-v4-pro"}]}))
    live = tmp_path / "episodes_arm2" / "p15_eval_0004_bundles_r1"
    live.mkdir(parents=True)
    (live / "episode.json").write_text(json.dumps({"total_cost": 0.8669}))

    assert run_mod._program_spend() == round(0.8669 + 0.5468, 4)
    slots = [{"task_id": "p15_eval_0004_bundles", "rep": 1}]
    assert run_mod._spent_so_far({"frozen_execution_order": slots},
                                 tmp_path / "episodes_arm2", "deepseek-v4-pro") == 1.4137


def test_the_harvest_happens_before_every_early_exit(run_mod):
    """A failing pass is the pass that replaced the most attempts, so harvesting after the failure
    checks would lose exactly the spend that matters most. Asserted on source order because the
    ordering, not the function, is the property.
    """
    src = (REPO / "scripts/phase8a_run.py").read_text()
    harvest = src.index("harvested = _harvest_replaced_attempts(")
    for marker in ('"stopped": "FAILED_INTEGRITY"', '"stopped": "telemetry_faults"',
                   '"stopped": "executor_exit"'):
        assert harvest < src.index(marker), f"harvest must precede {marker}"


def test_the_chain_log_path_is_arm_scoped(run_mod):
    """Unscoped, arm 2 block 00 overwrote arm 1's chain_b00.log -- destroying the only per-attempt
    cost record for that pass, i.e. the very evidence the ledger harvests. Fourth instance of an
    arm-scoped quantity written as a global, after --models, the custody tree and the budget default.
    """
    src = (REPO / "scripts/phase8a_run.py").read_text()
    assert 'f"chain_a{a.arm}_b{i:02d}.log"' in src
    assert 'f"chain_b{i:02d}.log"' not in src


def test_arm1_replaced_attempt_gap_is_reported_as_a_bound_not_as_zero():
    """Arm 1's ledger figure is 0.0 because the ledger did not exist then, not because nothing was
    paid. Reporting the gap as a bound is the honest form; inventing a number to close the identity
    would be worse than admitting it.
    """
    en = " ".join(PREREG.read_text().split())
    zh = " ".join(PREREG_ZH.read_text().split())
    assert "a gap, not a measurement" in en and "缺口，不是一次测量" in zh
    assert "at most about ¥1.1" in en and "最多约 ¥1.1" in zh


def test_report_surfaces_replaced_attempt_spend(report_mod):
    src = (REPO / "scripts/phase8a_report.py").read_text()
    assert "spent_on_replaced_attempts_cny" in src
    # Path from the module, never as a literal: a "phase8a/reports/..." string in this file reads to
    # scripts/slim_link_check.py as a repo-root `reports/...` reference and is reported as dangling.
    r = report_mod._out(1)[0]
    if r.is_file():
        assert "spent_on_replaced_attempts_cny" in json.loads(r.read_text())


# ------------------------------------------------------ the outage record (Amendment 5, section 5E)
def test_amendment5_attributes_the_outage_against_an_unbilled_endpoint():
    """The dangerous look-alike is balance exhaustion, which on this backend left GET /v1/models
    returning 200 because listing models is unbilled. Here it returns 503 too. That is the evidence;
    the provider's own error string is only its account of itself.
    """
    en = " ".join(PREREG.read_text().split())
    zh = " ".join(PREREG_ZH.read_text().split())
    assert "An outage that blocks an unbilled endpoint cannot be a balance condition" in en
    assert "不可能是余额问题" in zh
    assert "SERVICE_BUSY" in en and "SERVICE_BUSY" in zh


def test_amendment5_fixes_the_partial_arm_rule_before_the_outcome_is_known():
    """Blocks are instances, so a subset of blocks is a subset of INSTANCES, not a smaller k. With
    bidirectional instance-level heterogeneity observed in arm 1, analysing whichever instances ran
    before an outage would let provider downtime choose the sample.
    """
    en = " ".join(PREREG.read_text().split())
    zh = " ".join(PREREG_ZH.read_text().split())
    assert "reported as incomplete" in en and "never as a smaller arm" in en
    assert "报告为不完整" in zh and "绝不报告为一个更小的臂" in zh
    assert "draws no condition contrast" in en


def test_arm2_block00_pass_is_archived_out_of_the_grading_tree():
    """The pass stopped by the 503 outage must not be gradeable, and its phantom 0.5 must not count.

    Originally this asserted that the three trial names were ABSENT from episodes_arm2/. That
    encoded a transient state, not the invariant: §5B.3 requires the block to be re-run WHOLE, and a
    re-run legitimately repopulates those exact names -- so the assertion started failing the moment
    the rule was obeyed. The durable property is that an archived pass lives OUTSIDE the custody
    glob, so no trial is ever counted twice: once from the abandoned pass and once from the re-run.
    """
    arch = REPO / "phase8a/evidence/aborted/arm2_block00_attempt1"
    if not arch.is_dir():
        pytest.skip("arm 2 block 00 has not been archived")
    trials = sorted(p.name for p in arch.glob("p15_eval_*"))
    assert trials == ["p15_eval_0004_base_r1", "p15_eval_0004_bundles_r1",
                      "p15_eval_0004_typedcontract_r1"]
    custody = REPO / "phase8a/evidence/episodes_arm2"
    assert custody not in arch.parents, "an archive nested in the custody tree would double-count"
    graded = [p.parent.name for p in custody.glob("*/episode.json")]
    assert len(graded) == len(set(graded)), f"a trial appears twice in the grading glob: {graded}"
    for t in trials:
        assert not list(custody.glob(f"*/{t}/episode.json")), f"{t} archive is inside the glob"
    # the phantom: no model call, yet a score, which is why the pass was stopped rather than trusted
    ep = json.loads((arch / "p15_eval_0004_base_r1" / "episode.json").read_text())
    assert (ep.get("total_cost") or 0) == 0 and ep.get("total_score") == 0.5
    # both languages, and the per-attempt cost record preserved out of gitignored runs/
    assert (arch / "ABORTED.md").is_file() and (arch / "ABORTED.zh.md").is_file()
    assert (arch / "chain_log_arm2_block00.log").is_file()
    # the run state stays at the evidence path so the three 503 attempts remain countable
    assert (REPO / "phase8a/evidence/run_state_arm2_block00_attempt1.json").is_file()


# ------------------------------------------- archiving an aborted pass (prereg 5B.3, automated)
def test_archive_refuses_a_pass_whose_fault_is_not_a_transport_fault(tmp_path):
    """The discriminator that keeps automation honest.

    A telemetry stop can mean the provider died, or that something in the harness stopped calling the
    model. Only the first is an infrastructure fault that 5B.3 lets us archive and re-run; archiving
    the second would hide a code defect behind a ledger entry and re-run straight into it.
    """
    ev = REPO / "phase8a/evidence"
    state = ev / "run_state_arm2_block07.json"
    assert not state.exists(), "test would clobber a real run state"
    try:
        state.write_text(json.dumps({"state": "FAILED", "completed_primary_slots": 1,
                                     "expected_primary_slots": 6, "executor_exit_code": 2,
                                     "excluded_invalid_attempts": [
                                         {"classification": {"error": "ValueError: grader crashed"}}]}))
        r = subprocess.run([sys.executable, str(REPO / "scripts/phase8a_archive_pass.py"),
                            "--arm", "2", "--block", "7", "--require-transport-fault", "--dry-run"],
                           capture_output=True, text=True, cwd=str(REPO))
        assert r.returncode == 2, r.stdout
        assert "not demonstrably a transport fault" in r.stdout

        state.write_text(json.dumps({"state": "FAILED", "completed_primary_slots": 1,
                                     "expected_primary_slots": 6, "executor_exit_code": 2,
                                     "excluded_invalid_attempts": [
                                         {"classification": {"error": "chat attempt failed: "
                                          "category=retryable_http exc=ProviderHTTPError "
                                          "status=503"}}]}))
        r = subprocess.run([sys.executable, str(REPO / "scripts/phase8a_archive_pass.py"),
                            "--arm", "2", "--block", "7", "--require-transport-fault", "--dry-run"],
                           capture_output=True, text=True, cwd=str(REPO))
        assert r.returncode == 0, r.stdout
        assert json.loads(r.stdout)["fault_is_transport"] is True
    finally:
        state.unlink(missing_ok=True)


def test_archive_refuses_a_complete_pass():
    """A COMPLETE pass is data, not a discard candidate. Archiving one would remove valid episodes
    from the panel -- the mirror image of retrying away a valid score."""
    ev = REPO / "phase8a/evidence"
    state = ev / "run_state_arm2_block08.json"
    assert not state.exists(), "test would clobber a real run state"
    try:
        state.write_text(json.dumps({"state": "COMPLETE", "completed_primary_slots": 6,
                                     "expected_primary_slots": 6, "executor_exit_code": 0}))
        r = subprocess.run([sys.executable, str(REPO / "scripts/phase8a_archive_pass.py"),
                            "--arm", "2", "--block", "8", "--dry-run"],
                           capture_output=True, text=True, cwd=str(REPO))
        assert r.returncode == 1 and "COMPLETE" in r.stdout
    finally:
        state.unlink(missing_ok=True)


def test_archive_script_makes_no_model_call():
    """It is custody plumbing. A script that could spend money while tidying up after an outage would
    be the worst possible place for a paid call.

    Checked on capability, not on vocabulary: an earlier version of this test grepped for
    "chain_executor" and failed on the sentence explaining why a block restarts at position 0. A test
    that a comment can break tests the comment.
    """
    src = (REPO / "scripts/phase8a_archive_pass.py").read_text()
    assert "import subprocess" not in src, "the archive path cannot launch anything"
    for forbidden in ("TR_API_KEY", "API_KEY", "api_base", "chat/completions",
                      "EDA_BENCH_MAX_CHAT_RETRIES"):
        assert forbidden not in src, f"{forbidden} has no business in the archive path"


# ------------------------------------------------------- the agent-log race (arm 2 block 00)
# run_single_agentic snapshots and grades the agent workspace the moment the agent command returns,
# and llm_agent_driver writes --log as its LAST statement. In arm 2 block 00 the command returned
# while the driver was still working: one episode was graded mid-edit and recorded at cost 0.0 with
# no telemetry, and a second was charged another pass's cost and classified on another pass's 503s.


@pytest.fixture(scope="module")
def runner_mod():
    return _load(REPO / "scripts/phase8a_episode_runner.py", "p8a_runner")


def test_a_stale_agent_log_cannot_be_attributed_to_a_later_attempt():
    """Run directories are keyed by (block, condition, position, attempt) and are REUSED when a block
    is re-run whole, so a previous pass's log sits exactly where this attempt's log will go. Arm 2
    block 00 read it and recorded the archived pass's cost (¥0.5468 against a true ¥2.2849) AND its
    503 telemetry -- and that borrowed telemetry is what drove the arbiter to REPLACE an attempt
    that had scored 1.0. Asserted on source order: clearing must precede the run.
    """
    src = (REPO / "scripts/phase8a_episode_runner.py").read_text()
    assert src.index("logp.unlink(missing_ok=True)") < src.index("run_single_agentic("), \
        "the log path must be cleared BEFORE the driver runs, or a predecessor's log is readable"


def test_grading_waits_for_this_attempts_agent_log(runner_mod):
    """The wait is the whole fix: it holds the shell open until the driver has written its log, so
    the workspace is never snapshotted while the agent is still editing it. The driver's exit code
    must survive the wait, or a driver failure hides behind the loop's own success.
    """
    src = (REPO / "scripts/phase8a_episode_runner.py").read_text()
    assert "rc=$?" in src and "exit $rc" in src, "the driver's exit code must be preserved"
    assert 'for _ in $(seq 1 {LOG_SETTLE_SEC}); do [ -s "{logp}" ] && break; sleep 1; done' in src
    assert runner_mod.LOG_SETTLE_SEC >= 300, \
        "must cover the driver's own hard per-request deadline; observed lateness was 77 s and 94 s"


def test_a_missing_agent_log_is_measurement_invalid_not_a_free_episode():
    """The arbiter is PINNED and fails OPEN here: with no transport_summary it scans the error string
    for a terminal marker, and the shipped stub ("driver produced no log") carries none, so it
    concluded terminal_valid=True and ACCEPTED a phantom at cost 0.0 with score 0.5. The unpinned
    layer must report the fault in the vocabulary the authority reads.
    """
    sys.path.insert(0, str(REPO / "scripts"))
    import episode_arbiter as arb

    src = (REPO / "scripts/phase8a_episode_runner.py").read_text()
    assert "malformed_worker_result: driver produced no readable log" in src
    assert "malformed_worker_result" in arb.TERMINAL_MARKERS, \
        "the marker must be one the pinned arbiter actually recognises"

    graded = {"total_score": 0.5, "agent": {"timed_out": False}}
    shipped = arb.classify_episode(graded, {"error": "driver produced no log"})
    assert shipped["measurement_valid"] is True, "documents the fail-open that let the phantom in"
    assert arb.replacement_decision(shipped, 1) == "ACCEPT"

    fixed = arb.classify_episode(graded, {"error": "malformed_worker_result: driver produced no "
                                                   "readable log within 300s"})
    assert fixed["measurement_valid"] is False
    assert arb.replacement_decision(fixed, 1) == "REPLACE"


def test_the_missing_log_branch_never_consults_the_score():
    """An episode is invalidated for the ABSENCE OF A READABLE LOG, which is observed independently
    of the outcome. If the branch could see the score, it would be a way to retry away a valid one.
    """
    src = (REPO / "scripts/phase8a_episode_runner.py").read_text()
    start = src.index("if agentlog is None:")
    end = src.index("# The two files chain_executor.classify() reads")
    branch = src[start:end]
    assert "score" not in branch, "the invalidation condition must not depend on the outcome"


def test_arm1_custody_carries_no_phantom_episode():
    """Arm 1 predates the fix and is complete, so this is a check on the evidence, not the code: if
    the race had touched it, the arm-1 report's 216 graded episodes and ¥122.8175 would be wrong.
    Every episode must carry a real agent log and a cost that was actually derived from one.
    """
    tree = REPO / "phase8a/evidence/episodes"
    eps = sorted(tree.glob("*/episode.json"))
    if not eps:
        pytest.skip("arm-1 custody tree not present")
    bad = []
    for f in eps:
        d = json.loads(f.read_text())
        log = f.parent / "agentlog.sanitized.json"
        if float(d.get("total_cost") or 0.0) <= 0.0:
            bad.append((f.parent.name, "zero cost"))
        elif log.is_file() and log.stat().st_size < 200:
            bad.append((f.parent.name, f"stub log ({log.stat().st_size} B)"))
    assert not bad, f"phantom episodes in arm-1 custody: {bad[:5]}"


# --------------------------------------------- banking a pass exactly once, and at its true cost
def test_the_ledger_does_not_double_count_one_passs_replaced_attempt(run_mod, tmp_path,
                                                                     monkeypatch):
    """A block is re-run WHOLE, so (arm, block, trial, attempt) repeats across passes and cannot say
    whether two identical rows are two payments or one banked twice. The driver harvests after every
    pass AND phase8a_archive_pass harvests when the pass is archived, so without a pass identity the
    second call silently doubles the charge -- and a cap inflated by phantom spend ends the study
    early just as surely as one deflated by missing spend lets it overrun.
    """
    log = tmp_path / "chain.log"
    log.write_text('{"trial": "t_r1", "total_score": 1.0, "cost": 0.5}\n'
                   '{"trial": "t_r1", "total_score": 0.5, "cost": 2.0}\n')
    monkeypatch.setattr(run_mod, "ATTEMPT_LEDGER", tmp_path / "ledger.json")

    first = run_mod._harvest_replaced_attempts(2, 0, "blk", "m", log, "PASS-A")
    assert [e["cost_cny"] for e in first] == [0.5], "only the superseded attempt is banked"
    again = run_mod._harvest_replaced_attempts(2, 0, "blk", "m", log, "PASS-A")
    assert again == [], "the same pass must not be banked twice"
    assert run_mod._ledger_spend("m") == 0.5

    # a genuine re-run of the same block really did pay again, and must be counted
    other = run_mod._harvest_replaced_attempts(2, 0, "blk", "m", log, "PASS-B")
    assert [e["cost_cny"] for e in other] == [0.5]
    assert run_mod._ledger_spend("m") == 1.0


def test_cost_reconcile_recomputes_from_the_driver_log_not_from_an_estimate():
    """The correction is not an estimate: every attempt's own agentlog.json survives with its usage
    block, so the true cost is recomputed with the SAME _cost() the runner would have used had it
    read the log at the right moment. --check must reproduce it from the artifacts on disk.
    """
    r = subprocess.run([sys.executable, str(REPO / "scripts/phase8a_cost_reconcile.py"),
                        "--arm", "2", "--block", "0", "--check"],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, r.stdout + r.stderr
    assert '"check": "PASS"' in r.stdout


def test_cost_reconcile_excludes_another_passs_leftover_attempt_dirs():
    """Run dirs are keyed by (block, condition, position, attempt) and REUSED, so globbing a block's
    dirs also returns attempts an earlier pass left behind. Counting them would charge this pass for
    money the archived pass already accounts for -- the same stale-artifact-at-a-reused-path fault
    the script exists to correct. Exclusions are listed, never silently dropped.
    """
    r = subprocess.run([sys.executable, str(REPO / "scripts/phase8a_cost_reconcile.py"),
                        "--arm", "2", "--block", "0"],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(r.stdout)
    assert d["attempts_booked"] == d["attempts_with_a_driver_log"], \
        "every booked attempt, and only those, must be recomputed"
    assert d["excluded_as_another_passs_leftovers"], "the known leftover must be reported, not hidden"


def test_a_phantom_disarms_the_transport_fault_flag():
    """A pass can both survive a real 503 AND be ruined by a harness race -- this one did. Reading
    validity off the 503 alone would file a code defect under 'the provider was flaky' and re-run
    straight into it. `malformed_worker_result`, which the runner emits for a missing log, is
    deliberately not a transport category: a driver that fails to deliver a result is ours to fix.

    Asserted against the ARCHIVED pass, not by invoking the script on whatever is live. An earlier
    version of this test ran the CLI and accepted its exit code, and it broke the moment block 00 was
    legitimately re-run clean -- it had encoded a transient state rather than the invariant. The
    contaminated pass is a permanent artifact; the refusal it must produce can be checked forever.
    """
    mod = _load(REPO / "scripts/phase8a_archive_pass.py", "p8a_archive")
    assert not any(m in "malformed_worker_result" for m in mod.TRANSPORT_MARKERS), \
        "a missing driver log must never read as an infrastructure fault"

    arch = REPO / "phase8a/evidence/aborted/arm2_block00_attempt2"
    trials = sorted(p.parent.name for p in arch.glob("*/episode.json"))
    assert trials, "the contaminated pass must remain on disk as evidence"

    errs, is_transport = mod._transport_evidence(json.loads((arch / "run_state.json").read_text()))
    assert is_transport, "the 503 it survived really was a transport fault"

    phantoms = mod._phantom_episodes(arch, trials)
    assert phantoms, "the harness race left an episode with no evidence of a model call"
    unexplained = [p for p in phantoms if not any(m in p[1] for m in mod.TRANSPORT_MARKERS)]
    assert unexplained, "and that phantom is NOT explained by the transport fault"
    # This is the refusal condition in the script, evaluated on the real artifact: transport
    # evidence present, and still refused. That ordering is the whole point.
    assert (not is_transport or unexplained), "--require-transport-fault must still refuse"


def test_arm2_block00_second_pass_is_archived_at_its_true_cost():
    """The pass booked ¥6.069 and really cost ¥11.0465. The shortfall must be in the ledger, and the
    original episode.json records must still say what they said -- a discrepancy you can still see
    is worth more than a total that quietly agrees with itself.
    """
    arch = REPO / "phase8a/evidence/aborted/arm2_block00_attempt2"
    if not arch.is_dir():
        pytest.skip("arm 2 block 00 second pass has not been archived")
    ep = json.loads((arch / "p15_eval_0004_base_r2" / "episode.json").read_text())
    assert (ep.get("total_cost") or 0) == 0, "the original record is preserved, wrong figure included"
    led = json.loads((REPO / "phase8a/evidence/replaced_attempt_ledger.json").read_text())
    corr = [e for e in led["entries"] if e.get("kind") == "understated_cost_correction"
            and e.get("arm") == 2 and e.get("block") == 0]
    assert len(corr) == 1, "exactly one correction, or the cap is charged twice"
    assert corr[0]["cost_cny"] == 4.9775 and corr[0]["true_cny"] == 11.0465
    assert (arch / "ABORTED.md").is_file() and (arch / "ABORTED.zh.md").is_file()


def test_amendment6_records_the_race_as_a_harness_fault_in_both_languages():
    """The outage amendments blamed the provider on evidence (an unbilled endpoint was also down).
    This one must blame us, on evidence, with the same specificity -- otherwise the record reads as
    three provider faults in three days when the third was ours.
    """
    en = " ".join(PREREG.read_text().split())
    zh = " ".join(PREREG_ZH.read_text().split())
    assert "5F. Amendment 6" in en and "5F. 修正案 6" in zh
    # the cause named, not merely "a bug"
    assert "writes its `--log` as its **last** statement" in en
    assert "absence of evidence recorded as evidence of absence" in en
    # the stale-log face, which drove a replacement of an attempt that had scored 1.0
    assert "scores move under re-run" in en and "分数会在重跑下移动" in zh
    # arm 1 cleared explicitly, since its report is already published
    assert "216 of 216" in en and "216 个 episode 全部带有真实日志与非零成本" in zh


def test_amendment6_fixes_the_affordability_procedure_before_the_rerun():
    """The probe said arm 2 fits (¥36) and the one real block said it does not (¥105). The rule for
    deciding between them has to be written down BEFORE the re-run produces the number that decides
    it -- and it must be a rule that cannot shrink the design, only run it or not.
    """
    en = " ".join(PREREG.read_text().split())
    zh = " ".join(PREREG_ZH.read_text().split())
    assert "frozen §2.2 formula is re-applied unchanged" in en
    assert "**arm 2 does not run**" in en
    assert "It can never return a smaller one." in en
    assert "它永远不可能返回一个更小的臂" in zh
    # cost correlates with condition here, so cost may never select instances
    assert "no instance may ever be selected for execution on the basis of what it costs" in en


def test_amendment6_extends_the_discard_rule_to_a_complete_but_contaminated_pass():
    """§5B.3 covered a pass STOPPED part-way. A pass that finishes 6/6 and contains a phantom is the
    same problem, and the extension must be stated rather than improvised at the keyboard.
    """
    en = " ".join(PREREG.read_text().split())
    zh = " ".join(PREREG_ZH.read_text().split())
    assert "or when it completes but contains an episode with no evidence of a model call" in en
    assert "在完成但含有" in zh and "整体废弃" in zh
    src = (REPO / "scripts/phase8a_archive_pass.py").read_text()
    assert "def _phantom_episodes" in src
    assert "Deliberately NOT score-based" in src, "the discard criterion may never read a score"


# ---------------------------------------------------------------------------------------------
# The §2.2 cost gate, re-applied after block 00 was re-run (prereg §5F.5 step 3).
# This is the last decision in the programme and the one with money on it, so it is tested like
# one: the gate may not read a score, may not run on a private copy of the formula, and may not be
# fed a spend figure that flatters it.
# ---------------------------------------------------------------------------------------------

GATE_SCRIPT = REPO / "scripts/phase8a_arm2_gate.py"
GATE_DECISION = REPO / "phase8a/evidence/arm2_gate_decision.json"


def test_the_arm2_gate_never_reads_a_score():
    """§2.2: 'The gate reads cost only. It never reads a score, a rate, a contrast or any outcome.'

    A budget gate that could see outcomes would be a way to stop an arm whose early numbers looked
    wrong, which is the precise practice the preregistration exists to make impossible.
    """
    src = GATE_SCRIPT.read_text()
    assert '"reads_scores": False' in src
    for forbidden in ("total_score", "score", "semantic_binding"):
        assert f'get("{forbidden}"' not in src, f"the gate must not read {forbidden}"
    assert 'get("total_cost")' in src


def test_the_arm2_gate_does_not_reimplement_the_frozen_formula():
    """The ladder arithmetic lives in phase8a_cost_probe.k2_from and is imported, never copied.

    A second copy is a second thing to drift, and the copy that decides whether ~¥50 is spent is
    exactly the one nobody would notice drifting.
    """
    src = GATE_SCRIPT.read_text()
    assert "import phase8a_cost_probe as P" in src
    assert "P.k2_from(" in src
    assert "for k in (6, 4, 2)" not in src, "the ladder must not be re-derived here"


def test_the_arm2_gate_is_fed_total_program_spend_not_the_stale_arm1_figure():
    """k2_from's first parameter is *named* spent_arm1, but by now arm 2 has paid for two archived
    passes and one valid block. Feeding it the arm-1 figure is literal and false: it hides real
    outlay from the cap whose job is to see it, and it flips the answer.

    Both readings must be recorded -- the difference is the whole substance of the decision.
    """
    d = json.loads(GATE_DECISION.read_text())
    assert d["budget"]["program_spend_cny"] > d["budget"]["of_which_arm1_cny"]
    assert d["stale_argument_reading"]["k2"] == 2, "the flattering reading did say run"
    assert d["gate"]["k2"] is None, "the honest reading says do not run"
    assert d["decision"] == "ARM2_NOT_RUN"


def test_the_arm2_gate_decision_still_reproduces():
    r = subprocess.run([sys.executable, str(GATE_SCRIPT), "--check"],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, r.stdout + r.stderr
    assert '"check": "PASS"' in r.stdout


def test_the_holdback_is_what_refuses_arm2_and_is_not_negotiable():
    """The remainder misses only by ¥1.39 -- 2.6% of its own projection -- against a pooled
    per-episode spread of nearly 7x. That is not a margin, it is noise, and abandoning the ¥10
    holdback to fit under it would be lowering the standard after seeing the number.
    """
    d = json.loads(GATE_DECISION.read_text())
    x = d["remainder_cross_check"]
    assert x["fits_after_holdback"] is False
    assert x["fits_only_if_holdback_is_abandoned"] is True
    assert d["rate"]["spread_factor"] > 5, "the estimate is not precise enough to spend a thin margin"


def test_one_completed_block_yields_no_condition_contrast():
    """§5E.5: blocks are instances, so a subset of blocks is a subset of *instances*, not a smaller
    k. Arm 1 observed bidirectional instance-level heterogeneity, so reporting a contrast from
    whichever single instance happened to run would let the budget choose the sample.
    """
    en = " ".join(PREREG.read_text().split())
    assert "a subset of blocks is a subset of *instances*, not a reduced k" in en
    assert "draws no condition contrast from them" in en


def test_the_reconcile_check_covers_every_pass_not_just_the_live_one():
    """Once block 00 was re-run clean, a --check scoped to the live pass reported "nothing
    understated" and silently stopped verifying the ¥4.9775 already recovered from the archived
    pass -- money still bound into the ¥200 cap. A verifier that goes green because it stopped
    looking is worse than no verifier.
    """
    r = subprocess.run([sys.executable, str(REPO / "scripts/phase8a_cost_reconcile.py"),
                        "--arm", "2", "--block", "0", "--check"],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(r.stdout)
    assert d["check"] == "PASS"
    assert d["passes_verified"] >= 3, "the live pass and both archived attempts must be checked"
    ids = {x["pass"] for x in d["results"]}
    assert {"live", "attempt1", "attempt2"} <= ids


def test_an_overwritten_source_is_reported_as_such_and_never_as_a_pass():
    """runs/phase8a/ is gitignored and keyed by (block, condition, position, attempt), so the
    whole-block re-run overwrote the driver logs the archived corrections were computed from.

    That is neither "reproduces" nor "the ledger is wrong" -- it is "the evidence is gone", and
    collapsing it into either would be a lie in a different direction. The weaker fallback check
    (does the recorded breakdown still add up?) must be labelled as weaker.
    """
    r = subprocess.run([sys.executable, str(REPO / "scripts/phase8a_cost_reconcile.py"),
                        "--arm", "2", "--block", "0", "--check"],
                       capture_output=True, text=True, cwd=str(REPO))
    d = json.loads(r.stdout)
    assert d["passes_no_longer_recomputable"] >= 1
    gone = [x for x in d["results"] if x["verdict"].startswith("SOURCE_GONE")]
    assert gone, "the overwritten passes must say so"
    for x in gone:
        assert "cannot be re-read" in x["why"]
        # the sanitized chain log is what still survives in git, and must be named
        assert x["still_committed"] and x["still_committed"].startswith("phase8a/evidence/aborted/")
    corrected = [x for x in gone if x["ledger_cny"] > 0]
    assert corrected, "the ¥4.9775 correction is one of them"
    assert abs(corrected[0]["ledger_cny"] - 4.9775) < 1e-6


def test_the_findings_write_up_uses_the_mandated_phrasing_in_both_languages():
    """The result may be stated as "not established with bidirectional heterogeneity observed" and
    must never be stated as proof of no effect. Non-significance is not evidence of a zero effect,
    and this study is specifically about not overstating what a measurement licenses.
    """
    def _plain(p):
        # strip blockquote markers and bold so the assertion tests the SENTENCE, not its decoration
        t = p.read_text().replace("*", "")
        return " ".join(t.replace("\n>", "\n").split())
    en = _plain(REPO / "docs/phase8a_findings.md")
    zh = _plain(REPO / "docs/phase8a_findings.zh.md")
    assert ("No consistent BundleS advantage was established on this preregistered 12-instance, "
            "k=6 panel, and bidirectional instance-level heterogeneity was observed." in en)
    assert "在这个预注册的 12 实例、k=6 面板上没有建立一致的 BundleS 优势，并且观察到双向的实例级异质性" in zh
    assert "This is not evidence that BundleS is ineffective" in en
    assert "Non-significance is not proof of zero effect" in en
    assert "单纯不显著并不等于证明零效应" in zh
    for doc in (en, zh):
        assert "proves BundleS" not in doc and "证明 BundleS 无效" not in doc.replace(
            "不是\"BundleS 无效\"的证据", "")


def test_the_findings_write_up_reports_the_unrun_arm_as_unaffordable_not_as_null():
    en = " ".join((REPO / "docs/phase8a_findings.md").read_text().split())
    zh = " ".join((REPO / "docs/phase8a_findings.zh.md").read_text().split())
    assert "the one preregistered cell that could not be filled within budget" in en
    assert "预注册计划中唯一一个预算内无法填上的格子" in zh
    # and it must not be dressed up as a finding about the model
    assert "Not anything about `deepseek-v4-pro` on this family" in en


def test_the_programme_is_recorded_as_closed_in_both_languages():
    """"Arm 2 is the last cell, and the programme ends when it does" (§5F.6) -- whether it ran or
    not. The closure has to be a durable record at the study's entry point, not a claim that lives
    only in a chat log, or the next person to open this tree has no way to know it is finished.
    """
    en = " ".join((REPO / "phase8a/README.md").read_text().split())
    zh = " ".join((REPO / "phase8a/README.zh.md").read_text().split())
    assert "Status: CLOSED" in en and "状态：已关闭" in zh
    assert "No further paid model call is authorised" in en
    assert "不再授权任何付费模型调用" in zh
    # the unfilled cell must be named as unfilled, never as tried-and-null
    assert "not run** — refused by the preregistered §2.2 cost gate" in en
    assert "未执行** —— 被预注册的 §2.2 成本门控拒绝" in zh
    # the surplus must be explicitly withheld, not merely unmentioned
    assert "not** spent on additional cells" in en
    assert "不**用于任何额外的格子" in zh


def test_the_artifact_map_states_arm2_was_refused_not_that_it_ran():
    """The single most misreadable fact in this study. "Arm 2 produced no effect" and "arm 2 was
    never executed" license completely different conclusions, and only the second is true. The
    artifact map is where a reviewer or artifact evaluator lands, so it must say so in both
    languages and must not present the one completed block as a contrast.
    """
    en = " ".join((REPO / "docs/artifact_map.md").read_text().split())
    zh = " ".join((REPO / "docs/artifact_map.zh.md").read_text().split())
    assert "S3 was not executed because it failed a preregistered cost gate" in en
    assert "S3 未被执行，因为它没有通过预注册的成本门控" in zh
    assert "ARM2_NOT_RUN" in en and "ARM2_NOT_RUN" in zh
    assert "no condition contrast" in en and "不给出任何条件对比" in zh
    assert "this is not a null result and not a negative one" in en
    assert "这不是零结果，也不是负结果" in zh
    # Phase-8A is now cited by v15, so the map must say which version -- and must still record that
    # v14 does not cite it, or a reader comparing the two would think a number went missing.
    assert "primary S2-F evidence in v15" in en and "v15 中的 S2-F 主要证据" in zh
    assert "**v14 does not cite it**" in en and "**v14 并未引用它**" in zh


def test_the_cross_backend_concordance_is_labelled_post_hoc_and_not_pooling():
    """The 10-of-12 anatomy agreement is the strongest thing Phase-8A found, which is exactly why it
    needs its two limits attached wherever it is stated: it was not preregistered, and it is not a
    pooled statistic. Phase-7A's own panel_anatomy already carries post_hoc: true.
    """
    en = " ".join((REPO / "docs/artifact_map.md").read_text().split())
    zh = " ".join((REPO / "docs/artifact_map.zh.md").read_text().split())
    assert "post hoc and not preregistered" in en
    assert "事后的、非预注册的" in zh
    assert "It is also not pooling: no number is summed across the two studies." in en
    assert "没有任何数字跨这两项研究相加" in zh
    # it may not be turned into a cross-backend inference
    assert "does **not** license any claim about either backend from the other" in en


def test_no_repository_date_is_presented_as_authoritative():
    """The ICLR pages were observed disagreeing with each other. submission/ is frozen and states one
    pair, so the caveat has to live where it CAN live, and it has to say the frozen file is not being
    chased -- otherwise the next reader assumes the repo is authoritative and misses a deadline.
    """
    en = " ".join((REPO / "README.md").read_text().split())
    zh = " ".join((REPO / "README.zh.md").read_text().split())
    assert "is not authoritative" in en and "不具权威性" in zh
    assert "Treat no date in this repository as ground truth" in en
    assert "请勿把本仓库中任何日期当作确定真值" in zh
    # the unverified status must be admitted, not smoothed over
    assert "has not been independently confirmed" in en
    assert "未能**从本环境独立确认" in zh.replace("未能从本环境独立确认", "未能**从本环境独立确认")


# --------------------------------------------------------------------------- manuscript v15
#
# Phase-8A entered the manuscript in v15 as the primary S2-F evidence. Three boundaries are easy to
# cross by accident once that happens, and each of them would change what the paper claims rather
# than how it reads, so each gets a test that reads the shipped source.

MAIN_TEX = REPO / "submission" / "main.tex"


def _tex() -> str:
    return " ".join(MAIN_TEX.read_text().split())


def test_the_manuscript_never_pools_the_two_sta_batches():
    """The k=2 and k=6 batches are two executions of the same twelve instances.

    Combining them is the single most tempting error available here -- 12 instances at k=2 plus 12 at
    k=6 *looks* like a k=8 panel or a 288-episode study, and either would be a fabricated measurement.
    The rule is asserted in the manuscript rather than left to the reader, and asserted here so that a
    later edit cannot quietly introduce a combined figure.
    """
    t = _tex()
    assert "are never pooled" in t, "the non-pooling rule must be stated, not implied"
    assert "no quantity is summed, averaged or differenced across them" in t
    # and the arithmetic that would express a pooled panel must not appear as a claim
    for forbidden in ("$k$=8", "k=8 panel", "288 episodes", "$n$=24", "24 instances"):
        if forbidden in t:
            # the one legitimate occurrence is the sentence forbidding it
            assert "do not form a $k$=8 panel" in t, f"{forbidden!r} appears outside its prohibition"


def test_the_manuscript_reports_s3_as_not_executed_and_never_as_a_negative_result():
    """An arm that did not run has no effect direction.

    "Failed the cost gate" and "showed no effect" are different claims about the world, and only the
    first is true. The distinction is the whole reason the gate was written as a formula in advance.
    """
    t = _tex()
    assert "not executed because it failed a preregistered cost gate" in t
    assert "this is not a null result, not a failure to improve" in t
    # the empty cell must stay empty in the result matrix
    assert r"\emph{joint model$\times$family} (S3) & --- & --- & --- & 0 & \emph{not executed}" in t
    # and the one block that did run may not be turned into a contrast
    assert "reported with \\emph{no} condition contrast" in t


def test_the_manuscript_does_not_treat_the_serving_endpoint_as_an_experimental_factor():
    """The endpoint changed; the model identity and our own API parameters did not.

    Two failures are possible and opposite: silently hiding the change, or promoting it to a confound
    that would make the k=6 batch look like a different model. The manuscript must do neither, must
    name no host (it is a double-blind PDF), and must not claim more than we can verify about the
    serving implementation.
    """
    t = _tex()
    assert "different serving endpoint" in t, "the change must be disclosed"
    assert "cannot certify the serving implementation identical" in t, "do not overclaim"
    assert "not because their endpoints differed" in t, "the endpoint is not the non-pooling reason"
    for host in ("paratera", "tokenrhythm", "llmapi", ".studio", ".com/"):
        assert host not in t.lower(), f"{host!r} would be a serving-host leak in a blind submission"


def test_every_k6_number_in_the_manuscript_is_a_generated_macro():
    """No k=6 figure may be typed into prose by hand.

    The k=2 study earned this rule the hard way; the k=6 batch arrives with three generated files, so
    the rule is enforceable by checking that the literals never appear as bare prose.
    """
    src = MAIN_TEX.read_text()
    assert r"\input{tables/phase8a_stats}" in src
    body = " ".join(l for l in src.splitlines() if not l.strip().startswith("%"))
    # These are the k=6 values; each has a macro, so a literal occurrence means someone transcribed.
    for literal in ("216 episodes", "0.278", "0.250", "0.361", "-2.8 percentage", "7 of 36",
                    "10 of 12", "-31.9", "+26.4"):
        assert literal not in body, f"{literal!r} is transcribed; use the generated macro"


def test_the_two_panels_are_classified_by_one_asserted_rule():
    """The cross-batch concordance is only meaningful if both batches use the same classifier.

    `phase8a_claim_statistics.compute()` runs its own classifier over Phase-7A's instances and asserts
    the result equals Phase-7A's frozen panel_anatomy block. Calling compute() here re-executes that
    assertion, so this test fails if the rules ever diverge -- which is the failure mode that would
    turn "the anatomy reproduces" into an artifact of two different definitions.
    """
    sys.path.insert(0, str(REPO / "scripts"))
    import phase8a_claim_statistics as M

    st = M.compute()
    c = st["cross_batch_structural_concordance"]
    assert c["post_hoc"] is True and c["preregistered"] is False
    assert c["is_pooling"] is False
    assert c["instances_classified_identically"] == 10 and c["instances_total"] == 12
    assert c["sign_agreement_among_informative_in_both"] == [4, 4]
    # the classifier is one function, used for both batches
    assert M.classify(0.0, 0.0) == "floor" and M.classify(1.0, 1.0) == "ceiling"
    assert M.classify(0.5, 0.0) == "informative"


def test_the_concordance_is_never_called_a_replication():
    """Both batches re-run the *same* frozen instances.

    Under the paper's own qualification standard that is repeated measurement of stability, not
    replication -- replication requires newly frozen configurations enlarging the projection claimed.
    Calling it a replication would let the paper claim a scope it did not widen, using its own
    vocabulary against itself.
    """
    t = _tex()
    assert "repeated measurement of stability, never replication" in t
    assert "post hoc, not preregistered" in t


def test_the_process_defects_stay_out_of_the_main_text():
    """Engineering defects are reproducibility governance, not results.

    They belong in the methods appendix as requirements. The check is positional: the three
    accounting requirements must appear after \\appendix, never before it.
    """
    src = MAIN_TEX.read_text()
    appendix_at = src.index("\\appendix")
    marker = "Three accounting requirements the higher-replication batch added"
    assert marker in src, "the requirements must be stated somewhere"
    assert src.index(marker) > appendix_at, "process defects must not sit in the main text"
    # the reference-standard principle, by contrast, is a Layer-4 requirement and stays in the main text
    assert src.index("A monitor is only as trustworthy as the custody of its reference standard") < appendix_at


def test_the_endpoint_is_not_given_as_the_reason_for_not_pooling():
    """The rule and its justification are separate things, and only the rule was ever right.

    An earlier draft justified not pooling by "different serving stack, therefore a different
    measurement". That overstates what an endpoint string implies -- what could move behaviour is
    weights, sampling configuration, context and chat template, none of which the endpoint names. The
    defensible reason is that the two batches are independent executions, the second a preregistered
    higher-replication follow-up. Both languages must carry the corrected reason, because a
    justification this repository states in one language and not the other is how the wrong one
    survives.
    """
    en = " ".join((REPO / "docs/phase8a_findings.md").read_text().split())
    zh = " ".join((REPO / "docs/phase8a_findings.zh.md").read_text().split())
    assert "two independent executions" in en
    assert "两次独立的执行" in zh
    assert "not treated as an experimental factor" in en and "不作为实验因子" in zh
    assert "do not** claim the underlying serving implementation was identical" in en
    assert "不**声称底层 serving 实现完全相同" in zh
    # the discredited justification must be gone from both
    assert "different serving stack, therefore" not in en
    assert "不同服务栈，因此是" not in zh


def test_the_k6_statistics_reproduce_from_the_frozen_records():
    """`--check` must recompute and diff, so a drifted input fails the gate instead of moving a
    printed number silently. Run as a subprocess so the test exercises the same entry point the
    documented command does, including the file comparison the in-process helpers skip.
    """
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "phase8a_claim_statistics.py"), "--check"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert r.returncode == 0, f"phase8a_claim_statistics --check failed: {r.stdout}{r.stderr}"
    out = json.loads(r.stdout)
    assert out["ok"] is True
    assert out["k6_delta_pp"] == -2.8
    assert out["anatomy"] == [6, 1, 5]
    assert out["unstable_cells"] == "7/36"
    assert out["same_class"] == "10/12"
    assert out["arm2"] == "ARM2_NOT_RUN"


# ---------------------------------------------------- the link checker must still be able to fail
def _link_check():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "slim_link_check", REPO / "scripts" / "slim_link_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_link_checker_still_flags_a_genuinely_broken_reference():
    """v15 widened this checker: `phase8a` joined its known top-level directories, and a match
    preceded by a directory segment is no longer treated as a second reference. Both changes reduce
    what it reports, so the standing risk is a verifier tuned until it prints nothing. This is the
    negative control -- a reference nobody could satisfy must still be caught.
    """
    m = _link_check()
    # Assembled at run time: written as literals they would themselves be scanned as broken
    # references by the very check this test drives.
    for broken in ("docs/" + "no_such_document_zzz.md",
                   "scripts/" + "no_such_script_zzz.py",
                   "phase8a/reports/" + "no_such_report_zzz.json"):
        assert m.REF.findall(f"see {broken} for details") == [broken], broken
        assert not m.resolves(broken), broken


def test_the_link_checker_still_reads_the_reference_forms_the_docs_use():
    """The tail guard must not silence the ordinary ways a reference is written."""
    m = _link_check()
    for line, want in (
            ("see reports/README.md", "reports/README.md"),
            ("see ./reports/README.md", "reports/README.md"),
            ("`reports/README.md`", "reports/README.md"),
            ("(reports/README.md)", "reports/README.md"),
            ("[x](docs/artifact_map.md)", "docs/artifact_map.md")):
        got = m.REF.findall(line)
        assert want in got, (line, got)
        assert m.resolves(want.rstrip(")")), want


def test_the_link_checker_does_not_invent_references_from_path_tails():
    """`runs/` is never committed, and frozen episode evidence records absolute runtime paths into
    it verbatim. Reading the tail of such a path as a repo-root reference reports the repository as
    broken for files it never claimed to have -- and the evidence may not be edited to suit a
    checker.
    """
    m = _link_check()
    for tail_only in ("runs/phase8a/a1_8A_sta:p15_eval_0005",
                      "/data1/x/eda-agentbench/runs/phase8a/chain_a2_b00.log",
                      "somewhere/reports/phase8a_sta_report.json"):
        assert m.REF.findall(tail_only) == [], tail_only


def test_the_repository_has_no_dangling_references():
    """The positive half: with the checker demonstrably able to fail, its silence means something."""
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "slim_link_check.py")],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no dangling repository references" in r.stdout
