"""Regression tests for the Phase-7D semantic/tool discrimination analysis
(scripts/phase7d_semantic_proxy_gap.py).

The analysis re-derives, from records frozen at or before the experiment freeze, how often a
family's own tool-success signal accepts a submission the typed oracle rejects. Its credibility
rests entirely on its fail-closed source assertions, so this module's job is to prove those
assertions are NOT vacuous: a verifier tuned until it prints nothing would hide the next real
mutation.

Locks in:
  (a) The committed JSON reproduces exactly from the frozen sources (--check is meaningful).
  (b) Structural invariants of the emitted record set: the universe reconciles with the source
      manifests, and no included episode carries a null verdict or an unverified pairing.
  (c) Every fail-closed assertion actually fires. Each negative control below mutates one
      invariant of a KNOWN-GOOD payload in memory and requires assertions() to catch it:
        - un-excluding a structurally unidentifiable episode (controlled pair, SPICE-5C)
        - imputing a missing verdict instead of excluding the episode
        - including a workflow episode whose stage-2 tool verdict describes a superseded config
        - arithmetic tampering (false-accept numerator > denominator; correct+wrong != n;
          confusion matrix not summing to n)
        - dropping an episode from the universe, or shrinking the included count
  (d) The two families' pairing rules stay distinct: STA/SPICE pair by construction (the tool
      signal is generated at grading time from the submission), workflow pairs only when
      stage2_summary's consumed-config hash equals the submitted config's hash.

Read-only: every test operates on the committed sources or on deep copies in memory. Nothing
writes into the canonical tree or into reports/evidence/.
"""
import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import phase7d_semantic_proxy_gap as p7d  # noqa: E402


@pytest.fixture(scope="module")
def payload():
    """The recomputed analysis. Known-good: (a) asserts this is assertion-clean."""
    return p7d.collect()


# --------------------------------------------------------------------- (a) reproducibility

def test_committed_json_reproduces_exactly(payload):
    assert p7d.OUT_JSON.is_file(), "committed analysis JSON is missing"
    assert json.loads(p7d.OUT_JSON.read_text()) == payload, (
        "recomputed analysis differs from the committed JSON; --check would report drift")


def test_baseline_is_assertion_clean(payload):
    assert p7d.assertions(payload) == []


# --------------------------------------------------------------------- (b) structural invariants

def test_universe_reconciles_and_nothing_is_imputed(payload):
    u = payload["universe"]
    recs = payload["per_episode"]
    assert u["considered"] == len(recs)
    assert u["included"] + u["excluded"] == u["considered"]

    included = [r for r in recs if r["exclusion_reason"] is None]
    assert len(included) == u["included"]
    for r in included:
        assert r["semantic_correct"] is not None, f"{r['episode_id']}: null semantic verdict"
        assert r["tool_proxy_accept"] is not None, f"{r['episode_id']}: null tool verdict"
        assert r["pairing_verified"] is True, f"{r['episode_id']}: unverified pairing"
        assert r["semantic_source"] and r["tool_proxy_source"] and r["pairing_rule"]

    # excluded episodes must carry a reason and must never be silently defaulted to a verdict
    for r in recs:
        if r["exclusion_reason"] is not None:
            assert not (r["semantic_correct"] is not None
                        and r["tool_proxy_accept"] is not None
                        and r["pairing_verified"] is True), (
                f"{r['episode_id']}: excluded yet fully identifiable")


def test_strata_partition_the_included_set(payload):
    assert sum(s["n"] for s in payload["strata"].values()) == payload["universe"]["included"]
    for name, s in payload["strata"].items():
        if not s["n"]:
            continue
        assert s["semantic_correct"] + s["semantic_wrong"] == s["n"], name
        assert sum(s["confusion_matrix"].values()) == s["n"], name
        assert (s["observed_tool_false_accept_numerator"]
                <= s["observed_tool_false_accept_denominator"]), name
        assert s["observed_tool_false_accept_denominator"] == s["semantic_wrong"], name


def test_episode_ids_are_unique(payload):
    ids = [r["episode_id"] for r in payload["per_episode"]]
    assert len(ids) == len(set(ids)), "episode identity collides (must be evidence-dir + name)"


def test_scope_limitation_is_recorded(payload):
    """The construction caveat must travel with the number, not live only in prose."""
    for key in ("scope_limitation", "delta_is_not_independent", "no_new_measurement"):
        assert payload[key].strip(), f"{key} must be stated in the emitted JSON"


# --------------------------------------------------------------------- (c) negative controls

def _first(recs, pred):
    for r in recs:
        if pred(r):
            return r
    raise AssertionError("no record matched the negative-control precondition")


NEGATIVE_CONTROLS = {
    "unexclude_controlled_pair":
        lambda b: _first(b["per_episode"], lambda r: r["stage"] == "4V-pair")
                  .__setitem__("exclusion_reason", None),
    "unexclude_spice_5c":
        lambda b: _first(b["per_episode"],
                         lambda r: r["family"] == "spice" and r["stage"] == "5C")
                  .__setitem__("exclusion_reason", None),
    "include_stale_stage2_episode":
        lambda b: _first(b["per_episode"],
                         lambda r: r["exclusion_reason"] ==
                         "stale_stage2_evidence:tool_verdict_on_superseded_config")
                  .__setitem__("exclusion_reason", None),
    "inflate_false_accept_numerator":
        lambda b: b["strata"]["sta_prospective_7A"]
                  .__setitem__("observed_tool_false_accept_numerator", 999),
    "break_correct_plus_wrong":
        lambda b: b["strata"]["workflow_program_primary"].__setitem__("semantic_correct", 34),
    "break_confusion_matrix_sum":
        lambda b: b["strata"]["sta_phase5D"]["confusion_matrix"]
                  .__setitem__("tool_reject_semantic_wrong", 5),
    "drop_episode_from_universe":
        lambda b: b["per_episode"].pop(),
    "shrink_included_count":
        lambda b: b["universe"].__setitem__("included", b["universe"]["included"] - 1),
}


@pytest.mark.parametrize("name", sorted(NEGATIVE_CONTROLS))
def test_assertion_fires_for(name, payload):
    bad = copy.deepcopy(payload)
    NEGATIVE_CONTROLS[name](bad)
    assert p7d.assertions(bad), f"assertions() did not catch the '{name}' mutation"


def test_imputing_a_missing_verdict_is_caught(payload):
    """Filling a missing frozen field with False (instead of excluding) must fail the gate."""
    bad = copy.deepcopy(payload)
    r = _first(bad["per_episode"],
               lambda x: x["exclusion_reason"] is not None and x["semantic_correct"] is None)
    r.update(semantic_correct=False, tool_proxy_accept=False,
             pairing_verified=True, exclusion_reason=None)
    assert p7d.assertions(bad), "imputed verdict was not caught"


# --------------------------------------------------------------------- (d) pairing rules

def test_pairing_rules_differ_by_family(payload):
    included = [r for r in payload["per_episode"] if r["exclusion_reason"] is None]
    wf = {r["pairing_rule"] for r in included if r["family"] == "workflow"}
    graded = {r["pairing_rule"] for r in included if r["family"] in ("sta", "spice")}
    assert wf == {"stage2_input_hash==sha256(submitted)"}
    assert graded == {p7d.BY_CONSTRUCTION}, (
        "STA/SPICE tool signals are produced at grading time from the submission; they must not "
        "borrow the workflow family's stale-evidence pairing rule")


def test_workflow_stale_evidence_episodes_are_excluded(payload):
    """The hash rule must be doing work: tuple equality alone under-detects the hazard."""
    recs = [r for r in payload["per_episode"] if r["family"] == "workflow"]
    stale = [r for r in recs
             if r["exclusion_reason"] == "stale_stage2_evidence:tool_verdict_on_superseded_config"]
    assert stale, "no stale-evidence episode detected; the pairing gate is not being exercised"
    # most stale episodes agree on the submitted tuple while consuming a different config file,
    # which is exactly why pairing is verified by hash rather than by tuple
    tuple_agrees = [r for r in stale if r.get("binding_paired")]
    assert tuple_agrees, (
        "expected stale episodes whose (scenario, corner, netlist) still matches; if none remain, "
        "re-derive whether the hash rule is still stricter than tuple comparison")


def test_conclusion_is_robust_to_the_pairing_rule(payload):
    """The finding must not depend on which pairing rule is chosen."""
    strata = list(payload["strata"].values()) + list(
        payload["workflow_pairing_sensitivity"].values())
    for s in strata:
        if not s["n"]:
            continue
        assert s["tool_proxy_is_constant"] is True, (
            "a stratum where the tool signal is no longer constant invalidates the headline "
            "framing; re-derive before reporting")
        if s["semantic_wrong"]:
            assert s["observed_tool_false_accept_rate"] == 1.0
