# Phase-7A — the discarded episode of the single validity-only replacement

This directory preserves the artifact of the **one replaced episode** in the Phase-7A
prospective STA run (`reports/evidence/phase7a_state.json`: `replaced: 1`, `invalid: 0`,
`aborted: 0`). The manuscript discloses that replacement; until now the discarded artifact
itself existed **only** under the gitignored `runs/` tree and had no backup in version
control. `runs/` has since been deleted to reclaim disk, so this is the surviving record.

Nothing frozen was modified to add this. This directory is purely additive.

## What was replaced

| | |
|---|---|
| Trial | `p15_eval_0004_base_r2` (task instance `p15_eval_0004`, condition **Base**, rep 2) |
| Block | `A_sta:p15_eval_0004:Qwen3.7-Max`, position 4 of 6 |
| Original run path | `runs/phase7a/p15_eval_0004/20260808_225705/` (deleted) |
| Artifact | `exception_config.discarded.json` — sha256 `9dadc5f253cab8f24a29fee3ddfc1eb8883e331a878f935f23afeebed4654666` |

**Attempt 1 (discarded, this artifact):** `total_score` 0.5, `measurement_valid: false`,
`terminal_transport_valid: false`, `recovered_hard_deadlines: 1`,
`error: RuntimeError: chat attempt failed: category=hard_request_deadline`.

**Attempt 2 (retained, in `phase7a_episodes/p15_eval_0004_base_r2/`):** `total_score` 1.0,
`measurement_valid: true`, custody `exception_config.json` → `0948d82f9bc301f2`.

The replacement is therefore **infrastructure-only**, exactly as the pre-registered fairness
rule requires: a transport failure (here a hard request deadline) is measurement-invalid and
is retried, and is never recorded as a capability failure. A *valid* episode with a wrong
score is a hard failure and is never retried.

## Why the artifact is the unmodified shipped file

The submitted content is the task's shipped starting binding, comment intact:

```json
{
  "_comment": "STA exception binding (editable). Ships a plausible-but-wrong binding; repair to the provenance-attested binding.",
  "intent_class": "functional_close",
  "target_partition": "cdc",
  "check_mode": "setup"
}
```

The agent never edited the file — consistent with an episode cut short by a hard request
deadline. This is *not* a semantic-binding datum and must not be graded or pooled: it is the
record of a discarded measurement, kept so the disclosed replacement is auditable.

## How this artifact was identified

`p15_eval_0004` had **seven** run directories but only **six** recorded trials. Hashing the
preserved artifact in each directory against the custody hashes in `phase7a_state.json`
matched six of seven exactly (typedcontract r1/r2, bundles r1/r2, base r1, base r2-retained);
`20260808_225705` was the only unmatched one, and it falls chronologically between
`typedcontract_r2` (22:51:13) and the retained `base_r2` attempt (23:14:05) — the slot where
`base_r2`'s failed first attempt belongs. Its score (0.5) matches the recorded attempt 1.

A repository-wide audit of all 73 `preserved/` artifacts under `runs/` found 72 byte-identical
to files already tracked under `reports/`; this was the sole orphan.
