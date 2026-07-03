# p14 v4 post-k5 synthesis — workflow_handoff_0005

**Design-only synthesis.** Corrects the prior narrative after the preserved DeepSeek k=5 probe:
`workflow_handoff_0005` is **not a hard capability wall** and the earlier "confident-wrong" was **not a
stable failure mode**. It is a **validated efficiency / protocol-stress task with strong provenance
instrumentation**. This document is analysis + forward design only — no code, no tasks, no probes.

---

## 1. Current checkpoint

- **HEAD:** `a8f7824` (`docs: report p14 v4 deepseek k5 preserved probe`)
- **Branch:** `synthetic-phase0a` — **local-only, not pushed** (no upstream), working tree clean.
- **Latest relevant commits (newest first):**
  - `a8f7824` — k5 preserved report (this synthesis's basis)
  - `326961b` — affirmative-marker fix (Phase-4J)
  - `16c314a` — preserved DeepSeek follow-up report
  - `f4ef140` — opt-in artifact preservation (Phase-4I)
  - `310fbcf` — `workflow_handoff_0005` implementation (multi-conflict decoy variant)
  - `5678d11` — 0005 smoke/stress probe report
  - (context: `991f60c` calibrated k=2 follow-up report; `bce6480` p14 saturation summary)

---

## 2. Pre-k5 hypothesis

- `0005` was introduced **after** the p10→p14 v3 ladder had **saturated** (single-fault localization and
  earlier handoff hazards all frontier-easy).
- Its design used a **multi-conflict, partially-truthful decoy** structure: a single global authority
  tuple `[netlist_v2.v, clk_main, slow, func]`, surrounded by decoys each correct on some axes and wrong
  on others (report_A right-netlist/wrong-corner, report_B right-corner/stale-netlist, evidence_C
  fresh-but-wrong-package, prev_signoff non-authoritative).
- **Initial k=1** smoke: Qwen solved; DeepSeek timed out — read as a possible frontier-edge signal.
- **Calibrated k=2** (1800s): one DeepSeek solve (1.0) + one non-solve (0.20) initially **inferred** as
  "report_A-like, wrong-corner, overconfident_wrong."
- **Preservation (Phase-4I) later corrected that inference:** the preserved final package decoded to the
  **correct** authority tuple (correct corner `func`); the real fault was a **broken evidence-provenance
  chain** (stage-1 and stage-2 generated from different byte-versions of a semantically-correct
  flow_config). Not decoy-following, not wrong-package.

---

## 3. What k=5 changed

Under 5 preserved trials (1800s, max 60 actions, temp 0.7, `--elicit-confidence`, preservation on):

- DeepSeek **solved 5/5** valid trials.
- **capability pass^5 = 1.00** (every trial `total_score = 1.0`, all gated components 1.0).
- **No decoy-following** failure occurred.
- **No broken-provenance** failure **recurred**.
- **No confident-wrong** occurred (0 overconfident_wrong).
- **Therefore `0005` is not a stable DeepSeek capability-difficulty task.** The k=2 broken-chain
  non-solve is best read as **run-to-run variance / a protocol slip**, not a stable mode.

---

## 4. What remains positive

Even with correctness saturated, `0005` still produces a real operational signal:

- Materially **increases exploration + execution cost** vs 0001–0004.
- **Long wall times** — 2/5 trials hit the full 1800s; mean ~1550s.
- **Many PT runs** — ~30–37 PT-like tool invocations per trial.
- **High tool-call count** — 47–57 actions per trial (near the 60 cap).
- **High protocol-incomplete / no-FINISH rate** — 4/5 solved but did not emit a clean FINISH+confidence.
- **Useful as an efficiency / protocol-stress task**: it is **stronger than 0001–0004 in operational
  cost** even though final correctness saturates for a strong agent.

---

## 5. Capability vs protocol conclusion

**Capability axis:**
- **Saturated for DeepSeek** under k=5 (pass^5 = 1.00).
- Qwen had **already solved** `0005` at k=1.

**Protocol / efficiency axis:**
- Only **1/5** DeepSeek k=5 runs were **protocol-clean** (FINISH + usable confidence).
- **4/5** solved but did **not** finish cleanly (budget_exhausted, no confidence).
- **2/5** hit the **1800s wall** while still scoring 1.0.
- This is a **meaningful agentic workflow-stress pattern** — the model reaches the correct final state but
  spends its whole action/time budget getting there and does not close the protocol.

**Key separation:** protocol-incompleteness is a **budget/harness interaction**, *not* a capability
failure. It must **not** be folded into capability-pass accounting.

---

## 6. Role of preservation (Phase-4I / 4J)

- Preservation was **not cosmetic.** It **corrected** the earlier "report_A-like wrong-corner" inference
  into the true broken-provenance-chain diagnosis.
- It makes **final submitted-package classification auditable** (byte hashes of the exact editable files
  the agent committed).
- **Methodology rule going forward:** future wrong-package / confident-wrong claims must be backed by
  **preserved artifacts**, or explicitly **marked inference-only**.
- **`component_scores` are authoritative** over `affirmative_grader_markers`. Phase-4J made the markers
  affirmative-only (no presence-only false positives); k=5 confirmed markers and gated scores now agree.

---

## 7. Why `0005` still is not enough (for a capability benchmark)

- The decoy graph is **still solvable** by strong agents (Qwen k=1, DeepSeek pass^5=1.0).
- The **global authority tuple is too recoverable** — the manifest/spec effectively let a strong agent
  reconstruct it directly.
- Decoys are **locally plausible** but do not compose into a **stable semantic trap** — no decoy survives
  once the agent cross-checks axes.
- The dominant effect is **longer exploration**, not **incorrect convergence**.
- A true capability benchmark needs **failure modes that persist after more time** — not merely slow but
  ultimately-correct convergence. Extra budget here would only raise the protocol_clean rate, not expose a
  wall.

---

## 8. What NOT to do

- **Do not** run more DeepSeek `0005` trials expecting a capability failure — pass^5=1.0 already answers it.
- **Do not** claim `0005` is a capability wall.
- **Do not** cite the earlier k=2 "confident-wrong" as stable — k=5 contradicted it (and preservation
  reclassified it as a protocol-slip broken chain, not confident-wrong).
- **Do not** generate more **minor variants** of `0005` (same recoverable structure → same saturation).
- **Do not** mix **protocol_clean** failure into **capability_pass** failure.

---

## 9. Next research direction

If continuing toward a **positive capability** signal, design a stronger **p14 v5 / workflow_handoff_0006**
around **joint constraint consistency** rather than single-tuple recovery:

- A **constraint-graph workflow** where multiple artifact choices must satisfy **coupled** constraints.
- **No single manifest line** directly reveals the full target tuple.
- Authority must be **inferred from several independent consistency checks**, not read off.
- Decoys remain **valid under each individual check** but **fail under joint consistency**.
- A **later stage invalidates** an earlier locally-plausible recovery.
- **Multi-step dependency repair** where the correct **rerun subset is non-obvious**.
- Reports are **not merely wrong by label** but **numerically / provenance-inconsistent across two
  independent tool outputs**.
- If cost allows, **cross-tool confirmation** (e.g. DC+PT or PT+Formality) so consistency must hold across
  tools — only if the b04/PT cost stays manageable.

---

## 10. Candidate `workflow_handoff_0006` concept — constraint-graph multi-source recovery

**Artifacts:**
- `manifest` carries **partial** authority, not the full tuple.
- `spec` gives design **intent** but not the exact recovery tuple in one place.
- `report_A` satisfies **netlist + timing** but **violates scenario**.
- `report_B` satisfies **scenario + clock** but **violates netlist**.
- `report_C` satisfies **provenance hashes** but **violates tool-derived numeric consistency**.
- `evidence_D` has a **valid upstream digest** but **depends on an invalidated intermediate stage**.
- **Public check** only reports **pairwise** consistency failures.
- **Hidden oracle** requires **global** consistency across all axes.

**Valid recovery:**
- Infer the **only** tuple satisfying **all** constraints jointly.
- Repair the lower configs.
- **Invalidate** the wrong stages.
- **Rerun the minimal correct stage subset.**
- Produce a **globally consistent** evidence chain.

**Acceptance filters (must hold):**
- All **pairwise-plausible** decoy recoveries **fail**.
- All **single-axis** fixes **fail**.
- **final-state-only** **fails**.
- **Full global recovery** **passes** (golden = 1.0).

This is the same additive, forgery-resistant echeck philosophy as 0005, but the **discriminator moves from
"recover one recoverable tuple" to "satisfy a joint constraint graph no single source reveals."**

---

## 11. Recommendation

- **Commit this synthesis after review.**
- Then choose:
  - **A.** Pause p14 task generation and prepare a **research appendix** around the substrate +
    efficiency/protocol-stress findings; or
  - **B.** Design **`workflow_handoff_0006`** as a true **constraint-graph hazard** (§10).
- **Preferred if pursuing positive capability:** design **0006 first**, not more 0005 probes.
- **Do not run more probes until a 0006 acceptance matrix exists.**

---

*Compliance: design-only. No code, no tasks, no models, no other-worktree changes. Not committed, not
pushed — awaiting review.*
