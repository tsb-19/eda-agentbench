#!/usr/bin/env python3
"""Exploratory continuation of arm 2, QUARANTINED from the closed Phase-8A study.

## What this is, and what it is not

The preregistered §2.2 cost gate refused arm 2 (`phase8a/evidence/arm2_gate_decision.json`,
`ARM2_NOT_RUN`) and the programme is recorded as closed. That decision stands and is not revisited
here. This script exists because the operator asked, explicitly and after being shown the arithmetic,
to let the remaining blocks run in the background until they either finish or the provider account
runs dry -- on the stated condition that it must not affect any current process or conclusion.

So this is **not** arm 2. It is an unregistered exploratory run whose only preregistered-safe use is
an infrastructure question: *can this backend complete 11 consecutive blocks at all?* Nothing it
produces may enter a condition contrast without a numbered amendment written first.

## How the isolation works

`phase8a_run` derives its custody tree, run-state paths, block files and replaced-attempt ledger from
one module global, `P8A`. Redirecting that global -- plus `BLOCKS` and `ATTEMPT_LEDGER`, which are
bound at import -- moves the entire write surface into a quarantine root under `runs/`, which is
gitignored. Concretely, the committed artefacts this protects:

  * `phase8a_report.py --arm 2 --check` re-grades `phase8a/evidence/episodes_arm2/`. New episodes
    landing there would change the report and fail the check.
  * `phase8a_arm2_gate.py --check` recomputes r' from that same tree pooled with the probe. New
    episodes would move r' and could flip a recorded decision -- the one thing that must not happen.
  * `phase8a_report._states()` globs `run_state_arm2*.json`; new state files would change arm 2's
    recorded invalid/replaced attempt counts.
  * the replaced-attempt ledger feeds `_program_spend()`, hence the cap arithmetic.

Block 00 already ran validly and is seeded into the quarantine so the executor skips it rather than
paying for it twice. Its chain log and run directories are therefore never rewritten -- which matters,
because overwriting exactly those directories is how the archived passes' cost evidence was lost
(findings 5 in docs/phase8a_findings.md).

## The budget

The ¥200 programme cap is deliberately NOT the stop condition here; the operator's instruction was to
run until completion or account exhaustion. `--budget` therefore only carries a runaway backstop, set
well above any plausible completion cost (11 blocks x 6 episodes at the pooled ¥0.8051 project ~¥53).
Quarantine spend is counted separately from the study's ledger and never merges into it.

  python3 scripts/phase8a_exploratory_arm2.py --dry-run
  python3 scripts/phase8a_exploratory_arm2.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import phase8a_run as R  # noqa: E402

# Under runs/, which .gitignore already excludes: the quarantine must be incapable of entering a
# commit by accident, including via `git add -A`.
QUARANTINE = REPO / "runs" / "phase8a_exploratory_arm2"
REAL = REPO / "phase8a" / "evidence"
BACKSTOP_CNY = 150.0


def seed() -> dict:
    """Copy the inputs the runner reads, and the one block that already ran validly."""
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in ("schedule_arm2.json", "prerun_manifest.json"):
        src = REAL / name
        if not src.is_file():
            raise SystemExit(f"phase8a_exploratory_arm2: missing {src}")
        shutil.copy2(src, QUARANTINE / name)
        copied.append(name)

    # Block 00's valid pass, so the executor skips it instead of re-paying for it. Copied, never
    # moved: the study's own custody tree must be left exactly as committed.
    st = REAL / "run_state_arm2_block00.json"
    if st.is_file():
        shutil.copy2(st, QUARANTINE / "run_state_arm2_block00.json")
        copied.append(st.name)
    src_ep = REAL / "episodes_arm2"
    dst_ep = QUARANTINE / "episodes_arm2"
    if src_ep.is_dir() and not dst_ep.exists():
        shutil.copytree(src_ep, dst_ep)
        copied.append("episodes_arm2/")

    # A ledger of its own. Sharing the study's would let an exploratory replacement move the
    # programme's spend total, and with it the cap arithmetic behind a committed decision.
    led = QUARANTINE / "replaced_attempt_ledger.json"
    if not led.is_file():
        led.write_text(json.dumps({"entries": []}, indent=2) + "\n")
    return {"seeded": copied, "quarantine": str(QUARANTINE.relative_to(REPO))}


def redirect() -> None:
    """Point every write path in phase8a_run at the quarantine.

    P8A is read at call time by _custody/_state_path/_program_spend and by main() itself; BLOCKS,
    ATTEMPT_LEDGER and ABORTED are bound at import and must be reassigned explicitly. Missing any of
    them would send part of the run back into the study's tree, which is the whole failure this
    guards against.

    ABORTED is only ever read, so leaving it would not have contaminated anything -- but it would
    have charged this run ¥6.92 of the study's discarded spend, and it would have left
    assert_isolated() below asserting less than it appears to. A partial redirect that looks total is
    worse than an obvious one.
    """
    R.P8A = QUARANTINE
    R.BLOCKS = QUARANTINE / "blocks"
    R.ATTEMPT_LEDGER = QUARANTINE / "replaced_attempt_ledger.json"
    R.ABORTED = QUARANTINE / "aborted"


def assert_isolated() -> None:
    """Fail closed if any redirected path still points inside the study's evidence tree."""
    for label, p in (("P8A", R.P8A), ("BLOCKS", R.BLOCKS), ("ATTEMPT_LEDGER", R.ATTEMPT_LEDGER),
                     ("ABORTED", R.ABORTED),
                     ("custody", R._custody(2)), ("state", R._state_path(2, 1))):
        rp = Path(p).resolve()
        if rp == REAL.resolve() or REAL.resolve() in rp.parents:
            raise SystemExit(f"phase8a_exploratory_arm2: {label} still points into {REAL} -- refusing")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=BACKSTOP_CNY,
                    help="runaway backstop only; the intended stop is completion or account "
                         "exhaustion, per explicit operator instruction")
    a = ap.parse_args()

    info = seed()
    redirect()
    assert_isolated()
    print(json.dumps({**info, "budget_backstop_cny": a.budget,
                      "study_tree_untouched": str(REAL.relative_to(REPO)),
                      "enters_analysis": False}, indent=2), flush=True)

    sys.argv = ["phase8a_run", "--arm", "2", "--budget", str(a.budget)]
    if a.dry_run:
        sys.argv.append("--dry-run")
    return R.main()


if __name__ == "__main__":
    raise SystemExit(main())
