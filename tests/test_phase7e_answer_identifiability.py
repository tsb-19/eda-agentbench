"""Regression tests for the Phase-7E answer-identifiability probe
(scripts/phase7e_answer_identifiability.py).

The probe asks whether a condition's own disclosure already pins the golden assignment, without
reading task evidence. Its entire credibility rests on two things being true rather than merely
claimed:

  1. The read gate is REAL. If the probe could reach report_A/B/C, evidence_D or the golden while
     deriving constraints, it would be answering a different question and the negative result
     would be worthless.
  2. The probe can DETECT answer disclosure when it is present. A probe too weak to fire on a
     component known to be answer-bearing would report "no unique identification" for every
     condition, including ones that publish the answer outright.

Locks in:
  (a) The committed JSON reproduces exactly (--check is meaningful).
  (b) |Omega| = 294, matching the manuscript's declared candidate count, and the candidate space
      is byte-identical across all conditions (so survivor counts are comparable).
  (c) POSITIVE CONTROL: the two conditions that carry clarity component C6 (0010 full bundle,
      0014 = Base + C6) have their (scenario, corner) projection collapsed to exactly one, and
      C6 is detected in exactly those two instances and no others.
  (d) NEGATIVE RESULT: neither BundleS arm (0015 S0, 0017 S1 held-out) uniquely identifies the
      golden under either reading -- and the survivor count is >1 by a margin, not by one.
  (e) Disclosure never excludes the truth: the golden is inside every survivor set. A constraint
      that ruled out the golden would mean the disclosure detection is wrong.
  (f) The read gate fires. Each negative control below asks the gate for something forbidden and
      requires ForbiddenRead, and the structural accessor is proven unable to return the golden.
  (g) The probe is not vacuous: it distinguishes conditions. Base and BundleS must NOT produce
      identical counts under the generous reading, or the probe would be measuring nothing.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase7e_answer_identifiability.py"
OUT = REPO / "reports/synthetic_phase7e_answer_identifiability.json"


def _load():
    spec = importlib.util.spec_from_file_location("phase7e", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


@pytest.fixture(scope="module")
def payload(mod):
    return mod.build()


def _by(payload, label):
    return next(r for r in payload["conditions"] if r["condition"] == label)


# ---------------------------------------------------------------- (a) reproducibility
def test_committed_json_reproduces_exactly(payload):
    assert OUT.exists(), "run the probe once without --check to commit its JSON"
    assert json.loads(OUT.read_text(encoding="utf-8")) == payload


# ---------------------------------------------------------------- (b) candidate universe
def test_universe_is_294_and_matches_the_manuscript(payload):
    assert payload["headline"]["omega"] == 294


def test_universe_is_identical_across_every_condition(mod, payload):
    axes = {c[0]: mod._structural_axes(mod.TASKS / c[0]) for c in mod.CONDITIONS}
    blobs = {json.dumps(a, sort_keys=True) for a in axes.values()}
    assert len(blobs) == 1, "conditions must share one candidate space to be comparable"
    assert all(r["strict"]["omega"] == 294 for r in payload["conditions"])


# ---------------------------------------------------------------- (c) positive control
@pytest.mark.parametrize("label", ["Full bundle(0010)", "V9"])
def test_c6_conditions_collapse_the_signoff_pair_projection(payload, label):
    """C6 publishes the sign-off ROLE PAIR, so the projection --- not necessarily the full
    assignment --- must be unique under both readings. This is the exact positive-control
    invariant; see test_c6_full_assignment_uniqueness_is_reading_dependent for why it is not
    stated over the full assignment."""
    row = _by(payload, label)
    assert row["c6_present"] is True
    for reading in ("strict", "generous"):
        assert row[reading]["scenario_corner_uniquely_identified"] is True, (
            f"{label} publishes the sign-off pair; the probe must detect it under {reading}")


def test_c6_full_assignment_uniqueness_is_reading_dependent(payload):
    """Guards against overstating the control. V9 (= Base + C6) leaves 3 full assignments under
    the strict reading because the clock is not value-stated there, so the claim 'C6 collapses
    all 294 to one' is false and must not be written."""
    v9 = _by(payload, "V9")
    assert v9["strict"]["survivors"] == 3
    assert v9["strict"]["golden_uniquely_identified"] is False
    assert v9["generous"]["golden_uniquely_identified"] is True
    full = _by(payload, "Full bundle(0010)")
    assert full["strict"]["golden_uniquely_identified"] is True
    assert full["generous"]["golden_uniquely_identified"] is True


def test_c6_detected_in_exactly_the_two_designed_instances(payload):
    got = {r["instance"] for r in payload["conditions"] if r["c6_present"]}
    assert got == {"workflow_handoff_0010", "workflow_handoff_0014"}
    assert all(r["c6_matches_design"] for r in payload["conditions"])


def test_c6_asserted_pair_is_read_off_the_prose_correctly(payload):
    row = _by(payload, "V9")
    assert row["strict"]["disclosure"]["k5_asserted_pair"] == ["slow", "func"]


def test_positive_control_flag_is_set(payload):
    assert payload["headline"]["positive_control_detects_C6"] is True


# ---------------------------------------------------------------- (d) the negative result
@pytest.mark.parametrize("label", ["BundleS", "Held(0017)"])
def test_bundleS_does_not_uniquely_identify_the_golden(payload, label):
    row = _by(payload, label)
    assert row["c6_present"] is False, "BundleS withholds C6 by design"
    for reading in ("strict", "generous"):
        r = row[reading]
        assert r["golden_uniquely_identified"] is False
        assert r["survivors"] > 1
        # >1 by a margin, not by one: a count of 2 would warrant a different reading.
        assert r["survivors"] >= 9, f"{label}/{reading} left only {r['survivors']} candidates"


def test_reportable_interval_is_a_bracket_not_a_point(payload):
    """The result must be quotable as an interval. Quoting only the leakage-favorable bound
    overstates how much the treatment narrows; only the strict bound understates it."""
    for key in ("bundleS_S0_bracket", "bundleS_S1_bracket"):
        b = payload["headline"][key]
        assert b["low_leakage_favorable"] == 9
        assert b["high_strict"] == 147
        assert b["low_leakage_favorable"] > 1


def test_strict_reading_shows_no_candidate_narrowing_by_bundleS(payload):
    """Under the strict reading BundleS does not shrink the candidate set at all relative to
    Base. Any prose that restates the survivor ratio as the treatment's mechanism contradicts
    this, which is why the payload carries a bounds_not_mechanism caveat."""
    assert (_by(payload, "BundleS")["strict"]["survivors"]
            == _by(payload, "Base(0009)")["strict"]["survivors"] == 147)
    assert "bounds_not_mechanism" in payload["what_this_can_and_cannot_show"]


def test_payload_does_not_claim_leakage_is_closed(payload):
    """The analysis closes direct answer disclosure only. Softer leakage stays open, and the
    record must say so rather than letting a reader infer the stronger claim."""
    w = payload["what_this_can_and_cannot_show"]
    assert "direct answer disclosure" in w["closed_if_survivors_gt_1"]
    for still_open in ("softer information leakage", "prior narrowing",
                       "model-specific exploitation"):
        assert still_open in w["not_closed"]


def test_positive_control_basis_is_recorded(payload):
    """The control's basis must travel with the number, so it cannot be restated as
    'C6 collapses all 294 candidates to one'."""
    basis = payload["headline"]["positive_control_basis"]
    assert "projection" in basis
    assert "reading-dependent" in basis


def test_headline_negative_result_flag(payload):
    assert payload["headline"][
        "golden_uniquely_identified_under_any_BundleS_reading"] is False


# ---------------------------------------------------------------- (e) truth is never excluded
def test_golden_is_inside_every_survivor_set(payload):
    for row in payload["conditions"]:
        for reading in ("strict", "generous"):
            assert row[reading]["golden_in_survivors"] is True, (
                f"{row['condition']}/{reading} excluded the golden --- disclosure detection "
                f"is wrong, not the task")


# ---------------------------------------------------------------- (f) the read gate is real
@pytest.mark.parametrize("rel", [
    "files/report_A_role_swap.rpt",
    "files/report_B_role_stale.rpt",
    "files/report_C_role_pvt.rpt",
    "files/evidence_D_role_mismatch.json",
    "files/prev_signoff.log",
    "files/flow_config.json",
    "files/handoff_manifest.json",
    "hidden/handoff_truth.json",
    "hidden/grade_workflow.py",
])
def test_read_gate_refuses_task_evidence(mod, rel):
    inst = mod.TASKS / "workflow_handoff_0009"
    with pytest.raises(mod.ForbiddenRead):
        mod._read_disclosure(inst, rel)


def test_disclosure_reads_only_allowlisted_files(payload):
    allowed = set()
    for row in payload["conditions"]:
        allowed |= set(row["strict"]["files_read"])
    assert allowed <= set((
        "prompt.md", "files/spec.md", "files/glossary.md",
        "files/public_check_summary.json"))


def test_no_condition_ever_read_an_evidence_file(payload):
    forbidden = set(payload["information_classes"]["C_forbidden"])
    for row in payload["conditions"]:
        for reading in ("strict", "generous"):
            for f in row[reading]["files_read"]:
                assert Path(f).name not in forbidden


def test_structural_accessor_cannot_return_the_golden(mod):
    """CLASS A must expose axis domains and nothing else --- especially not the answer."""
    axes = mod._structural_axes(mod.TASKS / "workflow_handoff_0009")
    assert set(axes) <= set(mod.STRUCTURAL_KEY_WHITELIST)
    blob = json.dumps(axes)
    assert "expected_unique_assignment" not in blob
    assert "global_authority_tuple" not in blob
    # The domains necessarily *contain* the golden values; what must be absent is any field
    # identifying WHICH of them is correct.
    for answer_key in ("expected_netlist", "expected_clock", "expected_scenario",
                       "expected_corner", "semantic_role_mapping", "uniqueness"):
        assert answer_key not in blob


def test_golden_loader_is_separate_from_narrowing(mod):
    """The golden must come from a distinct accessor, so ordering is auditable by inspection."""
    g = mod._golden_verification_only(mod.TASKS / "workflow_handoff_0009")
    assert g == {"netlist": "netlist_v2.v", "clock": "clk_main",
                 "scenario": "slow", "corner": "func"}
    assert "golden" not in mod.constraints_for.__code__.co_varnames


# ---------------------------------------------------------------- (g) the probe discriminates
def test_probe_is_not_vacuous_base_and_bundleS_differ(payload):
    base = _by(payload, "Base(0009)")["generous"]["survivors"]
    bundle = _by(payload, "BundleS")["generous"]["survivors"]
    assert base > bundle, (
        "under the generous reading BundleS must narrow more than Base, or the probe is not "
        "measuring the treatment at all")


def test_bundleS_narrows_the_typed_grid_not_the_answer(payload):
    """The treatment's whole mechanism: 7x7 role-ambiguous grid -> 3x3 typed grid, still >1."""
    assert _by(payload, "Base(0009)")["generous"][
        "survivors_scenario_corner_projection"] == 49
    assert _by(payload, "BundleS")["generous"][
        "survivors_scenario_corner_projection"] == 9


def test_held_out_arm_matches_the_S0_arm(payload):
    """S1 replicates S0's disclosure structure; if it did not, the arms are not comparable."""
    for reading in ("strict", "generous"):
        assert (_by(payload, "Held(0017)")[reading]["survivors"]
                == _by(payload, "BundleS")[reading]["survivors"])
        assert (_by(payload, "Base(0011)")[reading]["survivors"]
                == _by(payload, "Base(0009)")[reading]["survivors"])


# ---------------------------------------------------------------- fail-closed behaviour
def test_check_mode_detects_drift(mod, tmp_path, monkeypatch):
    """--check must fail on a mutated committed JSON, or it certifies nothing."""
    tampered = json.loads(OUT.read_text(encoding="utf-8"))
    tampered["headline"]["bundleS_S0"]["generous"] = 1
    target = tmp_path / "drift.json"
    target.write_text(json.dumps(tampered, indent=2) + "\n")
    monkeypatch.setattr(mod, "OUT_JSON", target)
    monkeypatch.setattr("sys.argv", ["phase7e", "--check"])
    assert mod.main() == 1


def test_main_fails_closed_if_positive_control_breaks(mod, monkeypatch):
    """If the probe ever stops detecting C6, it must refuse to report the negative result."""
    good = mod.build()
    good["headline"]["positive_control_detects_C6"] = False
    monkeypatch.setattr(mod, "build", lambda: good)
    monkeypatch.setattr("sys.argv", ["phase7e"])
    monkeypatch.setattr(mod.Path, "write_text", lambda *a, **k: None)
    assert mod.main() == 1
