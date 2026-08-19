#!/usr/bin/env python3
"""Archive an aborted Phase-8A block pass out of the analysis tree (NO model calls).

The rule is fixed in docs/phase8a_prereg.md §5B.3: a block stopped part-way is re-executed WHOLE and
its first pass is ARCHIVED rather than deleted. It leaves the analysis; it does not leave the ledger.

Doing this by hand worked once. It will not keep working: this backend has produced three distinct
terminal faults in three days (502 window, 402 INSUFFICIENT_BALANCE, 503 auth-service outage), each
stranding an arm mid-block, and every hand-run archive is a chance to forget one of the five steps --
at which point either a phantom episode stays gradeable or paid money leaves the ledger.

What it does, in order:
  1. refuses if there is nothing to archive -- a COMPLETE pass in which every episode carries
     evidence of a model call -- or, under --require-transport-fault, if the fault was not an
     infrastructure fault. That flag is the discriminator that keeps this from papering over a code
     bug, and it earned its keep: it refused arm 2 block 00's second pass, which turned out to be a
     harness race rather than an outage;
  2. moves every collected trial of the block out of the arm's custody tree;
  3. copies the run state, and renames the live one to <name>_attempt<K>.json so the report still
     counts the invalid attempts and the re-run writes a fresh state;
  4. sanitizes and copies the chain log in, because runs/ is gitignored and that log is the ONLY
     per-attempt cost record;
  5. harvests replaced-attempt cost into the ledger, then writes a bilingual ABORTED record.

Usage:
  python3 scripts/phase8a_archive_pass.py --arm 2 --block 0 [--reason "..."] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import phase8a_run as R  # noqa: E402  (reuse the driver's custody, ledger and harvest logic verbatim)

TRANSPORT_MARKERS = ("ProviderHTTPError", "retryable_http", "non_retryable_http", "status=",
                     "Timeout", "timeout", "MissingApiKey", "SERVICE_BUSY", "INSUFFICIENT_BALANCE")


def _sanitize(text: str) -> str:
    return text.replace(str(REPO), "<PROJECT_ROOT>").replace("/data/tongsb", "/<USER>")


def _transport_evidence(state: dict):
    """Every recorded classification error for this pass, and whether they are transport faults.

    The point of the check: a telemetry stop can mean the provider died OR that something in the
    harness stopped calling the model. Only the first is an infrastructure fault that §5B.3 lets us
    archive and re-run. Archiving the second would hide a code defect behind a ledger entry.
    """
    errs = []
    for e in state.get("excluded_invalid_attempts") or []:
        err = (e.get("classification") or {}).get("error") or ""
        if err:
            errs.append(err)
    is_transport = bool(errs) and all(any(m in e for m in TRANSPORT_MARKERS) for e in errs)
    return errs, is_transport


def _phantom_episodes(custody, trials):
    """Collected episodes carrying no evidence of a model call, or a recorded error.

    Deliberately NOT score-based. A pass is contaminated because an episode has no evidence behind
    it -- zero cost, or an error the runner recorded -- and that is observable without looking at
    what anything scored. Were the criterion a score, archiving would become a way to re-roll an
    outcome someone did not like.
    """
    out = []
    for t in trials:
        p = custody / t / "episode.json"
        if not p.is_file():
            continue
        d = json.loads(p.read_text())
        if float(d.get("total_cost") or 0.0) <= 0.0:
            out.append((t, "no evidence of a model call (total_cost 0)"))
        elif d.get("error"):
            out.append((t, str(d["error"])[:120]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Archive an aborted Phase-8A block pass.")
    ap.add_argument("--arm", type=int, required=True, choices=(1, 2))
    ap.add_argument("--block", type=int, required=True)
    ap.add_argument("--reason", default="")
    ap.add_argument("--require-transport-fault", action="store_true",
                    help="refuse unless every recorded fault is a transport fault")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    ev = REPO / "phase8a" / "evidence"
    live_state = ev / f"run_state_arm{a.arm}_block{a.block:02d}.json"
    if not live_state.is_file():
        print(json.dumps({"nothing_to_archive": str(live_state.relative_to(REPO))}))
        return 0
    state = json.loads(live_state.read_text())

    # which attempt number this archive is
    k = 1
    while (ev / "aborted" / f"arm{a.arm}_block{a.block:02d}_attempt{k}").exists():
        k += 1
    dest = ev / "aborted" / f"arm{a.arm}_block{a.block:02d}_attempt{k}"
    custody = R._custody(a.arm)
    sched = json.loads((ev / f"schedule_arm{a.arm}.json").read_text())
    blocks = R._blocks_of(sched)
    if a.block >= len(blocks):
        print(json.dumps({"refused": f"block {a.block} is not in the schedule"}))
        return 1
    block_id, slots = blocks[a.block]
    trials = [f"{s['task_id']}_r{s['rep']}" for s in slots]
    present = [t for t in trials if (custody / t / "episode.json").is_file()]

    # A COMPLETE pass may still be unusable. Arm 2 block 00's second pass finished 6/6 and contained
    # a phantom: run_single_agentic graded the workspace while the driver was still editing it, so
    # the episode was recorded at cost 0.0 with no telemetry and the (pinned, fail-open) arbiter
    # ACCEPTED it. §5B.3 was written for a pass STOPPED part-way and does not name this case;
    # Amendment 6 extends it, because the reasoning is identical and here it is not hypothetical.
    # In this very block a replacement moved a recorded score from 1.0 to 0.5, so scores demonstrably
    # move under re-run -- which is exactly why the keep/discard boundary may not be drawn between
    # episodes whose scores are already known. All-or-nothing, or nothing.
    phantoms = _phantom_episodes(custody, trials)
    if state.get("state") == "COMPLETE" and not phantoms:
        print(json.dumps({"refused": "pass is COMPLETE and every episode carries evidence of a "
                                     "model call — there is nothing to archive",
                          "block": a.block}))
        return 1

    errs, is_transport = _transport_evidence(state)
    # A phantom is NOT evidence of a transport fault, and a pass can carry both: this one survived a
    # real 503 (correctly replaced) and was then ruined by a harness race. Reading validity off the
    # 503 alone would file a code defect under "the provider was flaky" and re-run straight back into
    # it -- so a phantom disarms the flag unless its OWN recorded error names a transport category.
    # `malformed_worker_result`, which the runner now emits for a missing log, deliberately is not
    # one of those categories: the driver failing to deliver a result is ours to fix, not theirs.
    unexplained = [p for p in phantoms if not any(m in p[1] for m in TRANSPORT_MARKERS)]
    if a.require_transport_fault and (not is_transport or unexplained):
        print(json.dumps({"refused": "fault is not demonstrably a transport fault",
                          "errors": errs[:4],
                          "phantom_episodes": phantoms,
                          "phantoms_not_explained_by_transport": unexplained,
                          "note": "an infrastructure fault may be archived and re-run; a harness "
                                  "fault must be fixed. Investigate before spending again."},
                         indent=2))
        return 2

    costs = {t: float(json.loads((custody / t / "episode.json").read_text()).get("total_cost") or 0.0)
             for t in present}
    chain_log = REPO / "runs" / "phase8a" / f"chain_a{a.arm}_b{a.block:02d}.log"

    plan = {"arm": a.arm, "block": a.block, "block_id": block_id, "attempt": k,
            "archive": str(dest.relative_to(REPO)), "episodes": len(present),
            "episode_spend_cny": round(sum(costs.values()), 4),
            "pass_state": state.get("state"), "phantom_episodes": phantoms,
            "fault_is_transport": is_transport, "errors": errs[:3],
            "chain_log_present": chain_log.is_file()}
    print(json.dumps(plan, indent=2), flush=True)
    if a.dry_run:
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    for t in present:
        shutil.move(str(custody / t), str(dest / t))
    shutil.copy2(live_state, dest / "run_state.json")
    live_state.rename(ev / f"run_state_arm{a.arm}_block{a.block:02d}_attempt{k}.json")
    archived_log = None
    if chain_log.is_file():
        archived_log = dest / f"chain_log_arm{a.arm}_block{a.block:02d}.log"
        archived_log.write_text(
            f"# sanitized copy of {chain_log.relative_to(REPO)} (gitignored). <PROJECT_ROOT> <USER>\n"
            "# The only surviving per-attempt cost record for this pass. See ABORTED.md.\n"
            + _sanitize(chain_log.read_text(errors="replace")))

    # The model name comes from the arm's own config, never a literal here: the ledger attributes
    # spend by model, and a wrong name would charge one arm for another arm's replaced attempts.
    # Filtered like phase8a_run does -- these configs carry a leading "_comment" pseudo-entry.
    cfg = json.loads((REPO / f"phase8a/models_arm{a.arm}.json").read_text())
    named = [m for m in cfg.get("models", []) if not str(m.get("name", "")).startswith("_")]
    if len(named) != 1:
        raise SystemExit(f"phase8a_archive_pass: models_arm{a.arm}.json must hold exactly one entry")
    model_name = named[0]["name"]
    # Idempotent by pass: the driver harvests immediately after every pass, so by the time a pass is
    # archived its replaced attempts are normally already banked and this call adds nothing. It stays
    # as the backstop for a pass whose driver was killed before it could harvest -- and `pass_id`
    # (the pass's own started_at) is what keeps the backstop from becoming a double charge.
    harvested = R._harvest_replaced_attempts(a.arm, a.block, block_id, model_name,
                                             archived_log or chain_log,
                                             str(state.get("started_at") or ""))
    replaced_cny = round(sum(e["cost_cny"] for e in harvested), 4)

    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = "\n".join(f"{t}/{' ' * max(1, 34 - len(t))}¥{round(costs[t], 4)}" for t in present)
    # When a COMPLETE pass is archived, the cause of the archive is the phantom, not whatever
    # transport fault the pass also happened to survive. Naming the 503 here would file a harness
    # defect under "the provider was flaky", which is the misattribution this whole record exists to
    # prevent (docs/incident_golden_corruption.md: a monitor inherits the custody of its standard).
    reason = a.reason or (
        f"pass COMPLETE but contaminated: {phantoms[0][0]} — {phantoms[0][1]}" if phantoms
        else (errs[0] if errs else "see run_state.json"))
    (dest / "ABORTED.md").write_text(f"""**English | [中文](ABORTED.zh.md)**

# Aborted pass — arm {a.arm}, block {a.block:02d} (`{block_id}`), attempt {k}

Archived by `scripts/phase8a_archive_pass.py` at {stamp} under the rule fixed in
[`docs/phase8a_prereg.md` §5B.3](../../../../docs/phase8a_prereg.md).
**Nothing here enters the analysis. Its cost does enter the ledger.**

| | |
|---|---|
| started | {state.get('started_at')} |
| ended | {state.get('executor_finished_at')}, `executor_exit_code: {state.get('executor_exit_code')}` |
| slots completed | {state.get('completed_primary_slots')} of {state.get('expected_primary_slots')} |
| episodes collected | {len(present)} |
| cause | `{_sanitize(reason)[:400]}` |
| classification | `measurement_valid: false` — an infrastructure fault, never a capability failure |
| cost paid | **¥{round(sum(costs.values()) + replaced_cny, 4)}** = ¥{round(sum(costs.values()), 4)} in \
collected episodes + ¥{replaced_cny} for replaced attempts |

The whole pass is discarded rather than resumed. Some episodes here may have completed **validly**;
keeping those and resuming mid-block would put the keep/discard boundary between episodes whose
scores were already known, which is the shape of retrying away a valid score. All-or-nothing cannot
depend on any episode's score. `chain_executor.py` restarts a block at position 0 and
`phase8a_episode_runner.py` overwrites a trial's custody directory, so an in-place re-run would
overwrite them anyway.

The reasoning is set out at greater length, for the first such pass, in
[`../arm2_block00_attempt1/ABORTED.md`](../arm2_block00_attempt1/ABORTED.md).

## Contents

```
{rows}
run_state.json                     copy of the aborted chain_executor run state
{(archived_log.name + '   sanitized chain log — the only per-attempt cost record') if archived_log else ''}
```

The live run state was renamed to `run_state_arm{a.arm}_block{a.block:02d}_attempt{k}.json` so that
`phase8a_report._states()` still counts this pass's measurement-invalid attempts, and so the re-run
writes a fresh state rather than resuming this one.

This directory sits **outside** `{custody.relative_to(REPO)}/` deliberately: that tree's
`*/episode.json` glob is the grading and spend glob, and an archive nested inside it would make the
same trial appear twice, once from this pass and once from the re-run.
""", encoding="utf-8")

    (dest / "ABORTED.zh.md").write_text(f"""**[English](ABORTED.md) | 中文**

# 已废弃的执行轮次 —— arm {a.arm}，block {a.block:02d}（`{block_id}`），第 {k} 次

由 `scripts/phase8a_archive_pass.py` 于 {stamp} 依
[`docs/phase8a_prereg.md` §5B.3](../../../../docs/phase8a_prereg.md) 中确定的规则归档。
**此处任何内容都不进入分析。其花费进入账本。**

| | |
|---|---|
| 开始 | {state.get('started_at')} |
| 结束 | {state.get('executor_finished_at')}，`executor_exit_code: {state.get('executor_exit_code')}` |
| 完成的 slot | {state.get('expected_primary_slots')} 个中的 {state.get('completed_primary_slots')} 个 |
| 采集到的 episode | {len(present)} |
| 原因 | `{_sanitize(reason)[:400]}` |
| 分类 | `measurement_valid: false` —— 基础设施故障，绝非能力失败 |
| 已付费用 | **¥{round(sum(costs.values()) + replaced_cny, 4)}** = 已采集 episode 的 \
¥{round(sum(costs.values()), 4)} + 被替换尝试的 ¥{replaced_cny} |

整轮废弃而不是断点续跑。此处某些 episode 可能是**有效完成**的；保留它们并从中途续跑，
会把"保留/丢弃"的分界线画在**分数已知**的 episode 之间，而这正是"把有效分数重试掉"的形状。
全有或全无才不可能依赖任何 episode 的分数。此外 `chain_executor.py` 会把一个 block 从位置 0
重新开始，而 `phase8a_episode_runner.py` 会覆盖某个 trial 的 custody 目录，所以原地重跑
本来也会覆盖它们。

更详尽的论证见第一个这样的轮次：
[`../arm2_block00_attempt1/ABORTED.zh.md`](../arm2_block00_attempt1/ABORTED.zh.md)。

## 目录内容

```
{rows}
run_state.json                     被废弃的 chain_executor 运行状态副本
{(archived_log.name + '   脱敏的 chain 日志 —— 唯一的逐次花费记录') if archived_log else ''}
```

活动运行状态已重命名为 `run_state_arm{a.arm}_block{a.block:02d}_attempt{k}.json`，
以便 `phase8a_report._states()` 仍能计入本轮的 measurement-invalid 尝试，
并使重跑写入一份新的状态而不是续用这一份。

本目录**位于** `{custody.relative_to(REPO)}/` **之外**，这是刻意的：该树的 `*/episode.json`
glob 就是评分与花费的 glob，嵌套在其内的归档会让同一个 trial 出现两次 ——
一次来自被废弃的这一轮，一次来自重跑。
""", encoding="utf-8")

    print(json.dumps({"archived": str(dest.relative_to(REPO)), "episodes": len(present),
                      "episode_spend_cny": round(sum(costs.values()), 4),
                      "replaced_attempt_spend_cny": replaced_cny,
                      "program_spend_cny": R._program_spend()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
