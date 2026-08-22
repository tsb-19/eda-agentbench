"""Guards on the OpenCode external-scaffold probe.

The probe is the paper's first arm that is NOT part of the frozen a89e084 programme, so the rules
that keep it honest cannot live only in prose. Three of them are load-bearing:

  1. The scaffold main effect may not be estimated. OpenCode necessarily replaces the action surface
     and the prompt frame, and the paper's own definition of task information counts both, so
     `OpenCode - controlled runner` is not a scaffold effect. Every plausible way that difference
     could re-enter -- a deleted prohibition, a new report key, a drifted sentence -- fails here.
  2. The plan must precede the outcomes. A preregistration that can be written after the numbers is
     not one. Enforced against git, not against a claim in a header.
  3. Nothing pools with the frozen programme, and nothing is written under reports/. Phase-8A
     already learned the second one: an early draft that wrote there drove the frozen pin count
     1065 -> 1979 and silently resolved one of the two expected mismatches.

The escalation rule is also asserted to be outcome-independent, because "we saw +20 pp so we ran
more to confirm it" is the exact failure the paper is about.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PLAN = REPO / "docs/opencode_probe_analysis_plan.md"
PLAN_ZH = REPO / "docs/opencode_probe_analysis_plan.zh.md"
SCOPE = REPO / "docs/opencode_scaffold_probe_scope.md"
SCOPE_ZH = REPO / "docs/opencode_scaffold_probe_scope.zh.md"
CLAUDE_MD = REPO / "CLAUDE.md"
PROBE_ROOT = REPO / "opencode_probe"

# Any key or identifier that would compute the excluded quantity.
FORBIDDEN_KEYS = (
    "scaffold_effect",
    "scaffold_main_effect",
    "opencode_minus_runner",
    "runner_minus_opencode",
    "cross_scaffold_delta",
    "scaffold_delta",
)


def _git(*args: str) -> str:
    return subprocess.run(("git", "-C", str(REPO)) + args,
                          capture_output=True, text=True, check=False).stdout.strip()


def _flat(text: str) -> str:
    """Collapse whitespace, so a prose assertion survives a line wrap."""
    return " ".join(text.split())


def _added_at(path: Path) -> str | None:
    """Commit that first added `path`, or None if it is not committed yet."""
    rel = path.relative_to(REPO).as_posix()
    out = _git("log", "--diff-filter=A", "--format=%H", "--follow", "-1", "--", rel)
    return out or None


def _outcome_files() -> list[Path]:
    if not PROBE_ROOT.is_dir():
        return []
    return sorted(p for p in PROBE_ROOT.rglob("*.json")
                  if p.name in ("episode.json", "report.json", "claim_statistics.json"))


def test_the_plan_and_its_translation_both_exist_with_the_bilingual_header():
    """A reader-facing doc that governs an experiment is incomplete in one language."""
    assert PLAN.is_file() and PLAN_ZH.is_file()
    assert PLAN.read_text().startswith(
        "**English | [中文](opencode_probe_analysis_plan.zh.md)**")
    assert _flat(PLAN_ZH.read_text()).startswith(
        "**[English](opencode_probe_analysis_plan.md) | 中文**")


def test_no_scaffold_main_effect_claim():
    """The excluded question stays excluded, in the plan, in CLAUDE.md, and in code.

    This is the guard CLAUDE.md's carve-out names. It fails three ways: if the prohibition is
    deleted from either governing document, if a probe script grows a key that computes the
    difference, or if a probe artifact reports one.
    """
    plan = _flat(PLAN.read_text())
    # (a) the plan still excludes it, and still says why
    assert "Not estimated. Not reported." in plan
    assert "is not a scaffold effect" in plan
    assert "action surface" in plan and "prompt frame" in plan, (
        "the exclusion must keep its reason: the scaffold is not separable from what it brings")
    plan_zh = _flat(PLAN_ZH.read_text())
    assert "不估计。不报告。" in plan_zh
    assert "不是 scaffold effect" in plan_zh

    # (b) CLAUDE.md's carve-out still carries it
    cmd = _flat(CLAUDE_MD.read_text())
    assert "The scaffold main effect may not be estimated." in cmd
    assert "is not a scaffold effect and may not be reported as one" in cmd
    assert "test_no_scaffold_main_effect_claim" in cmd, (
        "the carve-out must keep naming its own enforcement, or the guard can be orphaned")

    # (c) no probe script or artifact computes it
    for script in sorted(REPO.glob("scripts/opencode*.py")):
        body = script.read_text()
        for key in FORBIDDEN_KEYS:
            assert key not in body, f"{script.name} computes the excluded quantity via {key!r}"
    for art in _outcome_files():
        blob = json.dumps(json.loads(art.read_text()))
        for key in FORBIDDEN_KEYS:
            assert key not in blob, f"{art} reports the excluded quantity via {key!r}"


# Assertive single-factor phrasings. Matched against emphasis-stripped, whitespace-collapsed
# sentences, because the phrasing this guard exists to catch was "makes the scaffold the *only*
# varied factor" -- markdown emphasis mid-phrase and all.
SINGLE_FACTOR = (
    r"mak\w*\s+(?:the\s+)?scaffold\s+the\s+only\s+\w*\s*factor",
    r"scaffold\s+(?:is|as|becomes)\s+the\s+only\s+\w*\s*factor",
    r"only\s+varied\s+factor\s+is\s+(?:the\s+)?scaffold",
    r"varies\s+only\s+the\s+scaffold",
    r"only\s+the\s+scaffold\s+(?:is\s+)?var\w+",
)
# A sentence is exonerated if it is forbidding the phrasing rather than using it.
NEGATED = ("not", "n't", "never", "may not", "cannot", "false")


def _sentences(md: str) -> list[str]:
    plain = re.sub(r"\*\*|\*|`|_", "", _flat(md))
    return re.split(r"(?<=[.!?:])\s+", plain)


def test_the_probe_is_not_described_as_varying_only_the_scaffold():
    """The wording the user corrected. 'Only the scaffold' is false by the paper's own taxonomy.

    OpenCode necessarily replaces the action surface and the prompt frame, both of which the paper
    counts as task information, so no probe document may claim single-factor variation.
    """
    for doc in (PLAN, PLAN_ZH, SCOPE, SCOPE_ZH):
        for sentence in _sentences(doc.read_text()):
            for pat in SINGLE_FACTOR:
                if re.search(pat, sentence, re.I):
                    low = sentence.lower()
                    assert any(n in low for n in NEGATED), (
                        f"{doc.name} asserts single-factor variation: {sentence.strip()[:160]!r}")
    # and the accurate framing is present, in both languages
    plan = _flat(PLAN.read_text())
    assert "while substituting the execution scaffold" in plan
    assert "It does **not** make the scaffold the only varied factor" in plan
    assert "同时替换执行 scaffold" in _flat(PLAN_ZH.read_text())


def test_the_plan_precedes_every_outcome():
    """A preregistration that can be written after the numbers is not one."""
    plan_commit = _added_at(PLAN)
    outcomes = _outcome_files()
    if plan_commit is None:
        assert not outcomes, (
            "probe outcomes exist while the analysis plan is still uncommitted -- the plan's "
            "precedence claim is already false")
        pytest.skip("plan not yet committed; no outcomes exist, invariant holds vacuously")
    if not outcomes:
        return
    plan_time = int(_git("show", "-s", "--format=%ct", plan_commit))
    for art in outcomes:
        at = _added_at(art)
        assert at, f"{art} is uncommitted; its precedence cannot be verified"
        assert int(_git("show", "-s", "--format=%ct", at)) >= plan_time, (
            f"{art} was committed before the analysis plan")


def test_the_probe_writes_nothing_under_reports():
    """Phase-8A's pin-count lesson, applied before it can be relearned.

    Path components are joined rather than written as literals: slim_link_check.py scans source for
    repo-relative paths and cannot tell a reference from an assertion of absence, so spelling the
    probe subdirectory out under the reports tree would register here as a dangling reference.
    """
    reports = REPO / "reports"
    assert not (reports / "opencode_probe").exists()
    assert not (reports / "evidence" / "opencode_probe").exists()
    assert "never under `reports/`" in PLAN.read_text()
    assert "绝不放在 `reports/` 下面" in _flat(PLAN_ZH.read_text())
    frozen_custody = "reports" + "/evidence"
    for script in sorted(REPO.glob("scripts/opencode*.py")):
        body = script.read_text()
        assert frozen_custody not in body, f"{script.name} writes into frozen custody"


def test_the_probe_never_pools_with_the_frozen_programme():
    """A fourth separately reported execution. The no-pooling rule extends unamended."""
    plan = _flat(PLAN.read_text())
    assert "No pooling" in plan
    assert "No combined episode count, no combined *k*, no combined *n*." in plan
    for phrase in ("Phase-7A", "arm 1", "arm 2"):
        assert phrase in plan, f"the no-pooling clause must name {phrase}"
    assert "不合并" in _flat(PLAN_ZH.read_text())


def test_the_escalation_rule_is_fixed_and_outcome_independent():
    """Stage 1 is k=2. Escalation must not depend on which direction stage 1 pointed."""
    plan = _flat(PLAN.read_text())
    assert "regardless of which condition scored higher" in plan
    assert "The direction of the stage-1 result is not an input to this decision." in plan
    assert "at least 5 instances" in plan, "the expressible-range threshold must be a number"
    # all three conditions, stated as conditions
    for cond in ("Trajectory completeness", "Expressible range", "Cost"):
        assert cond in plan, f"escalation condition {cond!r} is missing"
    assert "无论哪个条件得分更高都照样进行" in _flat(PLAN_ZH.read_text())
    assert "至少 5 个实例" in _flat(PLAN_ZH.read_text())


def test_layer_one_is_descriptive_and_reports_the_null_too():
    """Existence and frequency. No significance claim at any count, including zero."""
    plan = _flat(PLAN.read_text())
    assert "no significance test, and none will be computed for it" in plan
    assert "no significance claim at any count" in plan
    assert "not a null to be buried" in plan, (
        "a probe that finds nothing must be reportable with equal prominence")
    assert "n_tool_green_wrong" in plan
    zh = _flat(PLAN_ZH.read_text())
    assert "任何计数下都不作显著性主张" in zh
    assert "不是要被埋掉的零结果" in zh


def test_layer_two_keeps_the_papers_own_three_part_standard():
    """A looser bar for this probe than the paper applies to itself is the paper's own subject."""
    plan = _flat(PLAN.read_text())
    assert '**"Supports" requires all three**' in plan
    for part in ("*p* < 0.05", "band excludes 0", "improvements outnumber declines"):
        assert part in plan, f"the standard is missing its {part!r} clause"
    assert "not established" in plan
    assert 'neither "no effect" nor "does not transfer"' in plan
    assert "三条同时成立" in _flat(PLAN_ZH.read_text())


def test_the_authorized_scope_stops_short_of_the_formal_arm():
    """Authorization is integration plus one discarded dry run -- not 48 episodes."""
    plan = _flat(PLAN.read_text())
    assert "It does not authorize the 48-episode formal arm." in plan
    assert "unscored, discarded paid dry run" in plan
    assert "p15_dev_0000" in plan
    cmd = _flat(CLAUDE_MD.read_text())
    assert "Authorized so far: integration plus one unscored, discarded paid dry run" in cmd
    assert "The 48-episode formal arm is *not* authorized" in cmd


def test_the_frozen_programme_is_still_declared_closed():
    """The carve-out adds an exception. It must not have removed the rule."""
    cmd = _flat(CLAUDE_MD.read_text())
    assert "The `a89e084` experimental programme is permanently closed." in cmd
    assert "Every number the paper reports is re-derived from committed ledgers at or before it" in cmd
    assert "may not alter, pool with, replace, or retroactively reinterpret any `a89e084`-derived episode or statistic" in cmd
    assert "a separate study rather than a reopening" in cmd


def test_the_probe_does_not_touch_the_studied_panels_for_the_dry_run():
    """The dry run uses the family's only dev instance, never a studied instance."""
    plan = _flat(PLAN.read_text())
    assert "p15_dev_0000" in plan
    assert (REPO / "tasks/p15_sta_handoff/p15_dev_0000").is_dir(), (
        "the dry-run instance must exist")
    # and the studied panel is named as the panel, not as a selection
    assert "with no selection on prior informativeness" in plan
    assert "p15_eval_0004" in plan and "p15_eval_0015" in plan


def test_check6_is_parity_not_absolute():
    """Check 6's criterion was corrected BEFORE the formal arm, and the correction is recorded as
    a dated amendment rather than by editing the original to look as though it always said this.

    The original demanded the agent "cannot recover the overflow by any path" -- a property the
    frozen control never had either (llm_agent_driver.py:67 does not block redirect-then-read), so
    it would have failed the probe for being EQUAL to the control. The quantity check 6 protects is
    comparability of the observation budget, and parity is that quantity.
    """
    for doc in (SCOPE, SCOPE_ZH):
        raw = doc.read_text()
        text = _flat(raw)
        assert "Amendment, 2026-08-21" in raw or "修订，2026-08-21" in raw, \
            f"{doc.name}: the correction must be a dated amendment with its own heading"
        # tightened half: mandatory and explicit
        assert "tool-output" in text and "/tmp/opencode" in text, \
            f"{doc.name}: the backing-store requirement must be explicit, not folded into a general ban"
        # loosened half: parity, not absolute. The original wording stays, marked superseded.
        assert ("by any path" not in text and "任何路径" not in raw) or \
               ("Superseded" in raw or "被取代" in raw), \
            f"{doc.name}: the absolute wording must be superseded, not left standing unmarked"


def test_the_broker_does_not_claim_to_authorize_the_formal_arm():
    design = REPO / "docs/opencode_probe_remote_broker_design.md"
    if not design.is_file():
        pytest.skip("design doc not yet committed")
    for doc in (design, REPO / "docs/opencode_probe_remote_broker_design.zh.md"):
        text = doc.read_text()
        assert "**English | [中文]" in text or "**[English]" in text, f"{doc.name}: missing bilingual header"
    text = _flat(design.read_text())
    assert "does not authorize the formal" in text or "NOT authorize" in design.read_text()


def test_the_broker_caps_are_justified_by_measurement():
    """`64 KiB is 16x the 4000-byte observation cap` is not evidence for a transport bound. The
    design must cite the measured raw-output audit instead."""
    design = REPO / "docs/opencode_probe_remote_broker_design.md"
    if not design.is_file():
        pytest.skip("design doc not yet committed")
    text = _flat(design.read_text())
    assert "raw_output_audit.json" in text, "the caps must cite the measured audit record"
    assert "16x the frozen 4000-byte" not in text and "16× the frozen 4000-byte" not in text, \
        "the superseded justification must be gone"


def test_the_design_states_the_limit_of_the_headroom_claim_and_the_fail_closed_rule():
    """Requirement F, in the document a later reader will quote. Headroom over a finite calibration
    set is not a proof, and the design must say which property covers the gap."""
    for name in ("opencode_probe_remote_broker_design.md",
                 "opencode_probe_remote_broker_design.zh.md"):
        doc = REPO / "docs" / name
        if not doc.is_file():
            pytest.skip("design doc not yet committed")
        raw = doc.read_text()
        text = _flat(raw)
        assert "transport_output_limit" in text, f"{name}: the sixth status must be documented"
        assert "measurement-invalid" in text or "测量无效" in raw, \
            f"{name}: a cap hit must be documented as measurement-invalid"
        assert "calibration set" in text or "校准集" in raw, \
            f"{name}: the headroom claim must name the set it holds over"


def test_the_design_does_not_claim_byte_for_byte_action_parity():
    """The broker hash-pins tool-authoritative inputs to the canonical task version; the frozen
    runner shipped whatever was in $PWD and caught tampering at scoring time. That is a real
    difference in the action surface, and the paper's own section 2 counts the action surface as task
    information -- so it gets recorded, not inferred away."""
    for name in ("opencode_probe_remote_broker_design.md",
                 "opencode_probe_remote_broker_design.zh.md"):
        doc = REPO / "docs" / name
        if not doc.is_file():
            pytest.skip("design doc not yet committed")
        raw = doc.read_text()
        text = _flat(raw)
        for overclaim in ("byte-for-byte action parity", "byte-for-byte parity of the action",
                          "identical action surface", "完全一致的动作面"):
            assert overclaim not in text and overclaim not in raw, \
                f"{name}: unestablished parity claim: {overclaim!r}"
        assert ("pins tool-authoritative inputs" in text
                or "canonical task version" in text
                or "规范任务版本" in raw), \
            f"{name}: the pinning difference must be stated positively, not merely not-denied"


def test_the_batch_key_lifecycle_is_documented_in_both_languages():
    """Requirement E is a safety property about the operator's real login keys, so it belongs in the
    reader-facing document and not only in the code."""
    for name in ("opencode_probe_remote_broker_design.md",
                 "opencode_probe_remote_broker_design.zh.md"):
        doc = REPO / "docs" / name
        if not doc.is_file():
            pytest.skip("design doc not yet committed")
        raw = doc.read_text()
        text = _flat(raw)
        assert "48" in text, f"{name}: the batch size must be stated"
        assert "batch.json" in text, f"{name}: the lock-out record must be named"
        assert "nfs(5)" in text, f"{name}: the reason batching exists must cite the NFS guarantee"
        assert ("quarantine" in text or "隔离" in raw), \
            f"{name}: the mutex must not be described as breaking locks on age alone"
