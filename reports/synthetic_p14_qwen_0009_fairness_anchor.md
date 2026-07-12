# p14 Qwen × workflow_handoff_0009 fairness-anchor probe (Phase-4V) — UNRESOLVED (measurement-invalid)

**Status: COMPLETE — fairness anchor NOT obtained. Not committed (awaiting review).** HEAD `d821d34`.
Cost **¥2.97 / ¥20**. Model: Qwen3.7-Max only. Task: workflow_handoff_0009 only.

**Goal:** obtain one valid, preserved, gradeable Qwen × 0009 episode to confirm 0009 is directly
solvable by the fairness-anchor model.

## Headline — NO valid Qwen × 0009 episode; fairness anchor UNRESOLVED (measurement-invalid)

Both Phase-4V attempts are **measurement-invalid due to non-streaming long-reasoning transport
censoring**. Qwen3.7-Max has thinking enabled by default; the attempts accumulated ~20K–29K reasoning
tokens; the current provider uses a **non-streaming Chat Completions request** that returns only after
the complete reasoning+answer is generated; the **120-second urllib blocking-operation timeout fired
during that long thinking** before any repair action was returned. The observed `socket_timeout`s MAY
therefore be **legitimate long-thinking latency censored by the client transport policy** — NOT a
gateway defect (exact external cause **unproven**). Both attempts performed read-only exploration and
issued NO WRITE; both ended on the unchanged mutant. **This is a measurement failure, NOT a Qwen
capability failure.** The Phase-4U preliminary controlled-mechanism signal stands unchanged.

## 1. Valid / measurement-invalid attempts
- **Valid Qwen × 0009 episodes: 0.**
- **Phase-4V measurement-invalid attempts: 2** (trial1, trial1_retry1).
- **Total Qwen × 0009 invalid attempts across Phase-4U + Phase-4V: 4.**
- trial1: 8 read-only `cat` actions, `edited=[]`, `socket_timeout`, ¥1.18.
- trial1_retry1: 12 read-only `cat` actions, `edited=[]`, `socket_timeout`, ¥1.79.
- Stop per protocol ("two infrastructure-invalid attempts").

## 2. Cost / cap
¥2.97 / ¥20 (under cap).

## 3. HTTP timeout / deadline diagnostics + transport analysis
- **0 `hard_request_deadline` events** (wall 300 s never fired).
- **2 classified `socket_timeout` events** (op 120 s, one per attempt). 0 unclassified stalls.
- **Transport:** the dependency-free provider uses a **non-streaming** Chat Completions request (one
  POST, one response read). The client receives **no tokens until the model finishes generating** the
  complete reasoning chain + answer. During a long-reasoning generation there is **no network activity**
  on the client socket.
- **Qwen reasoning:** ~20K (trial1) and ~29K (trial1_retry1) `reasoning_tokens` — Qwen reasons
  extensively on 0009's ambiguous content.
- **Censoring mechanism:** the **120-second operation timeout may fire during the long-thinking
  interval** (no bytes received while the model reasons), censoring a response that may have been
  legitimately in progress. The exact gateway-side behavior (active generation vs. slow-drip vs.
  stall) is **not proven**.

## 4. Exact submitted tuple
Neither attempt edited `flow_config`. **Both submitted the unchanged mutant** `netlist_v1 / func / typ`.
**This is NOT a Qwen-authored semantic-role hypothesis** — it is the task's starting mutant scored
after a measurement abort.

## 5. Score / why it is not a capability result
0.10 (both) = explanation-only on the unchanged mutant; signoff=0 (the mutant netlist_v1 does not
PrimeTime-sign-off). **This is not a gradeable Qwen solution and yields no capability conclusion.**
**No repair WRITE was issued** in either attempt.

## 6. Preservation result
Both episodes: manifest + 5 editable files + `secrets_excluded=true` + hidden/forbidden excluded.
Preserved files hold the **unchanged mutant** (no WRITE was issued). **No preservation failure; no
oracle shortcut passed; no secret/hidden truth preserved.**

## 7. Byte-confirmed classification
**Both attempts: measurement-invalid (non-streaming long-reasoning transport censoring).** Qwen
produced ONLY read-only `cat` actions, never issued a WRITE, and submitted the unchanged starting
mutant. **Not a capability failure; not a semantic-role binding outcome; the unchanged mutant is NOT a
Qwen hypothesis.**

## 8. Comparison (Phase-4U results UNCHANGED)
| cell | valid | result |
|---|---|---|
| DeepSeek × 0009 | 3 | **0/3 pass, 3/3 semantic-role failures** |
| DeepSeek × 0010 | 3 | **3/3 pass, correct slow/func** |
| Qwen × 0010 | 1 | **PASS, correct slow/func** |
| **Qwen × 0009** | **0** | **4 measurement-invalid attempts total** (2 Phase-4U + 2 here) |

## 9. Is direct 0009 solvability established?
**No.** 0009 solvability is **not** directly confirmed by Qwen. Supported only indirectly: Qwen × 0010
PASS + the workflow_handoff_0006 reference (Qwen 8/8 on the analogous task). A clean Qwen × 0009
success has not been observed across 4 attempts.

## 10. Recommendation — do NOT proceed to the 2×2 factor-isolation experiment yet
The fairness anchor is a prerequisite and remains unresolved. **The next step is an independently
reviewed streaming-transport implementation — NOT another paid retry.**

**Rationale:** a paid retry under the current non-streaming transport is likely to reproduce the same
measurement censoring (Qwen reasons extensively on 0009; the 120 s op-timeout fires during the
thinking interval). The transport must be fixed first so a long-reasoning response is **observable
incrementally** (streaming delivers tokens as they are generated, keeping the socket active and
defeating the inactivity timeout).

**After the streaming transport is reviewed + committed:** re-attempt Qwen × 0009 to obtain the
fairness anchor → only then design the 2×2 factor-isolation study.

## Effect on the Phase-4U result
**None.** The supported wording stands unchanged: *"The clarity bundle produces a preliminary
controlled difference in semantic-role binding on DeepSeek at k=3."* No claim is added or removed.
**Do not** claim Qwen failed 0009, that 0009 is unsolvable by Qwen, that the gateway is definitively
defective, that a slow-drip/request-shape issue is proven, or that the unchanged mutant is a Qwen
semantic-role submission.

---
*Compliance: Qwen3.7-Max only (no DeepSeek/MiniMax/Kimi/GLM). `.env` removed after the run. No secrets
printed; no shell tracing; no code modified. Real PrimeTime grading path. Stage-0 gate: golden=1.0
(0009, live PT), 294→1 uniqueness, no leak. **Not committed, not pushed.** Other worktrees untouched.*
