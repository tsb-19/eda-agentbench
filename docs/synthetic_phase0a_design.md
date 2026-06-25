# Synthetic Phase-0A — Hand-Authored Mini Golden Project + Constraint-Drift Mutant

Status: **DESIGN DRAFT (planning only).** Worktree `../eda-agentbench-synthetic-phase0a`, branch
`synthetic-phase0a` (base `631448a` + cherry-picked planning commit). Companion to
`synthetic_eda_project_generator_plan.md`, `synthetic_failure_taxonomy.md` (mechanism **A**),
`synthetic_phase0_mvp.md` (Phase 0A). **No code, no b04 runs, no generator** in this round — this designs
ONE hand-authored project and ONE constraint-drift mutant well enough to build next, and fixes the
project→oracle→evaluator→reliability **contract** the rest of the family inherits.

## Goal of Phase-0A (read this first — it scopes everything below)

Phase-0A proves the **contract**, not the **difficulty**:

> golden project → constraint-drift mutant → VCS/DC/PT oracle → task artifact → evaluator result →
> reliability/calibration layer — end to end, on the smallest real footprint, with the fairness and
> anti-cheat invariants from the whole hardening cycle holding.

It does **not** try to be hard yet. Constraint-drift on a tiny project is, per the taxonomy, the *most
shortcut-prone* mechanism (a strong model may just diff "SDC vs the obvious reading of the spec"). Whether
it is genuinely hard is the **Phase-0D** question, falsified by a cheap multi-model probe *after* the loop
is proven — exactly the discipline that retired the six earlier directions
(`single-localization-saturation`). The durable deliverable of Phase-0A is the reusable
project/oracle/evaluator machinery; if constraint-drift later NO-GOs on difficulty, that machinery still
carries mechanism B (flow-handoff drift) and the harder multi-mechanism projects.

---

## 1. Mini project concept

**Circuit family.** A single **registered sign-off block**: `acc_stage`, an 8-bit registered accumulator
pipeline stage (registered inputs → combinational adder → registered output). This is the smallest design
that has *all three* timing arc kinds a constraint contract governs: an **input→register** path (governed
by `set_input_delay`), a **register→register** internal path (governed by the clock period), and a
**register→output** path (governed by `set_output_delay`). A pure shift/counter (as in the current PT
track) lacks a meaningful combinational reg→output path, so a wrong IO *value* would not move any slack.

**Why small but realistic.** `acc_stage` is a textbook sign-off unit: it is what every real block looks
like at its boundary — data arrives from an upstream block with a clock-to-output budget, is registered,
combined, re-registered, and handed to a downstream block with a setup budget. The interesting engineering
is **not** the logic; it is reconciling the **IO timing budget** across three documents (spec ↔ SDC ↔ PT
report). That reconciliation is the everyday work the benchmark wants to measure, and it survives at this
tiny size because the budget arithmetic — not the gate count — is the hard part.

**Why real PT timing is possible at this size (the critical enabler).** The existing P7 PrimeTime track
can only detect *structural* SDC faults (missing clock, bad port) because its DFF netlist has no real cell
delays — PT cannot compute a slack, which is exactly why its generator *dropped* `wrong_period` and
`missing_input_delay` as "PT accepts silently". Constraint-**drift** is precisely a wrong *value*, so it
**requires real timing arcs**. We get them by reusing the **P9 scalar-delay Liberty asset**
(`generators/assets/p9_pt_exception_debug/{tiny.lib,tiny.db}`), already validated on b04: cells have a
fixed clk→Q + setup of `0.10 ns` and a per-buffer-depth delay of `0.10 ns`, so every path slack is
**known in closed form** (`slack = cycles·period − 0.10 − depth·0.10`, P9's model). That analytic backbone
is what lets a drifted IO value produce a *real, predictable* PT violation and lets the oracle set
tolerances that float-jitter cannot flip (P9's `_MARGIN = 0.05` discipline).

**Files the project contains** (layout in §5; described here):

| File | Role |
|---|---|
| `spec.md` | the **authority**: timing contract with derived IO-budget arithmetic (visible, read-only) |
| `design.v` | RTL of `acc_stage` (visible, read-only) — for understanding the design |
| `design_netlist.v` | gate-level netlist DC produced, timed by PT against `tiny.db` (visible, read-only) |
| `tiny.db` / `tiny.lib` | scalar Liberty so PT computes real slack (visible, read-only; reused P9 asset) |
| `constraints.sdc` | the **editable** artifact — the drifted SDC the agent fixes |
| `run_public.sh` / `.tcl` | agent-runnable sign-off that surfaces the **symptom** (visible, read-only) |
| `run_hidden.sh` / `.tcl` | evaluator-only **oracle** (hidden) |
| `oracle/spec_truth.json` | machine-readable spec-derived intended constraint set (hidden) |
| `hidden/golden/` | golden PT report fixture (hidden) |
| `solution/constraints.sdc` | the correct fixed SDC (for the golden-pass gate) |

---

## 2. Golden project

**RTL — `design.v`** (`acc_stage`, registered accumulator; one real combinational path each side):

```verilog
module acc_stage (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        en,
    input  wire [7:0]  din,
    output reg  [7:0]  dout
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)      dout <= 8'd0;
        else if (en)     dout <= dout + din;   // adder = reg->reg + reg->out combinational depth
    end
endmodule
```

**Smoke flow — VCS.** A minimal `tb_smoke.v` elaborates+runs a few cycles (reset, accumulate, check
`dout` advances) so the project genuinely carries a VCS stage and the RTL is proven synthesizable/sane.
VCS here is an *authoring/CI smoke*, not the per-episode oracle. Emits `^SMOKE_OK`.

**Golden SDC — `solution/constraints.sdc`** (encodes *exactly* the spec contract of §1):

```tcl
create_clock -name clk -period 4.0 [get_ports clk]
set_clock_uncertainty 0.10 [get_clocks clk]
set_input_delay  1.8 -clock clk [get_ports {din[*] en}]
set_output_delay 1.2 -clock clk [get_ports {dout[*]}]
```

**DC script — `synth.tcl`** (authoring-time; produces the timed netlist):

```tcl
read_db tiny.db
set link_library "* tiny.db"
read_verilog design.v
elaborate acc_stage ; link
read_sdc solution/constraints.sdc          # golden author build uses the golden SDC
compile_ultra -no_autoungroup              # tiny design; scalar lib
write -format verilog -hierarchy -output design_netlist.v
```

This runs once at **authoring** to emit the golden `design_netlist.v` that ships visible+read-only. Per
the constraint-drift mechanism the *netlist is constant* across the golden and every mutant (only the SDC
drifts), so DC does not re-run per episode — keeping per-episode cost at the P7-PT level.

**PrimeTime script — sign-off** (the per-episode oracle core, mirrors the P9 PT flow):

```tcl
read_db tiny.db
set link_path "* tiny.db"
read_verilog design_netlist.v ; link_design acc_stage
read_sdc constraints.sdc                    # agent's SDC, laundered (see §4/§6)
write_sdc -nosplit applied_<section>.sdc
report_timing -delay_type max -nworst 10 -slack_lesser_than 0.0
```

**Expected golden result.** With the golden SDC: reg→reg, input→reg, and reg→output paths all have slack
`≥ _MARGIN` (closed-form from `tiny.db`; exact values confirmed at authoring on b04). PT reports **no**
negative-slack path → `^SIGNOFF_OK`; the applied SDC matches `spec_truth.json` on all 5 properties →
`^CONSTRAINT_SPEC_SCORE: 1.0`. Overall golden score **≈ 1.0** through the **same path the agent uses** (the
standing fairness gate). VCS smoke `^SMOKE_OK`.

---

## 3. Constraint-drift mutant

**Exact mutation.** One line of the golden SDC changes value, staying syntactically valid and
tool-accepted:

```
- set_output_delay 1.2 -clock clk [get_ports {dout[*]}]
+ set_output_delay 3.2 -clock clk [get_ports {dout[*]}]
```

Nothing else changes — RTL, netlist, spec, clock, and input delay are golden. The SDC now silently
encodes a **downstream setup budget of 3.2 ns** where the spec's downstream block needs only 1.2 ns.

**Why realistic.** This is a textbook **constraint/spec divergence**: a stale or mis-transcribed downstream
budget (an old revision of the sink block needed more setup; a units/margin double-count; a copy-paste from
a different interface). The SDC is *valid and accepted*; it simply no longer means what the spec says. No
syntax error, no missing object — the failure lives in the **relationship** between `spec.md` and
`constraints.sdc`, surfacing in a **third** artifact (the PT report).

**Expected PT symptom.** The reg→output available time shrinks by exactly 2.0 ns
(`available = period − uncertainty − output_delay`), driving the reg→`dout` path to a **negative slack**
(closed-form ≈ golden_slack − 2.0, comfortably below `−_MARGIN`). Running `run_public.sh`, the agent sees a
concrete `report_timing` **setup violation** on the `dout` path with the offending `output_delay` in the
constraint annotation → `^SIGNOFF_FAIL`. A hard, unambiguous, tool-visible symptom — ideal for a clean
Phase-0A loop-proof.

**Why the symptom does not reveal the fix.** The PT report shows *where* it fails (reg→`dout`, slack
−1.5) and that `output_delay` is in the path, but **not the correct value**. The correct value `1.2` is
**not a literal anywhere** in the SDC, the netlist, or the report. It is **derived** from the spec's
external facts:

> `set_output_delay = downstream_setup (t_su = 0.9) + board_flight (0.3) = 1.2`

(and symmetrically `set_input_delay = upstream_clk_to_q (1.5) + board_flight (0.3) = 1.8`). The agent must
**reconstruct the budget arithmetic** from `spec.md`, not copy a number. Critically, several *wrong* fixes
also clear the visible symptom — loosen the period, zero the output delay, set output_delay to whatever
first makes slack ≥ 0 — so "make PT green" is **not** the same as "restore the spec budget". The
discriminator that separates them lives in the hidden oracle (§4), invisible to the agent. This is the
mechanism's whole point: symptom (PT report) ≠ root cause (SDC↔spec drift) ≠ authority (spec).

> **Shortcut-risk note (honest).** If a model reads `spec.md`, recomputes `0.9+0.3` and `1.5+0.3`, and
> writes them back, it solves this in one reconciliation step. That is acceptable for *proving the loop*;
> it is the **Phase-0D** probe's job to decide whether this is too easy. Mitigations to harden later
> (deferred, not in 0A): multi-term budgets (derate × (t_su + flight + jitter)), multiple drifted ports,
> and a spec that states facts in different units than the SDC expects.

---

## 4. Oracle design

The oracle is **execution-based and marker-anchored**, identical in spirit to
`primetime_sta_debug.py` / `dc_constraint_debug.py`: the hidden run script is the authority and emits
`^MARKER` lines; the evaluator only parses anchored markers from the combined log. **No exact-diff
grading** — equivalent non-identical SDCs (e.g. `1.20` vs `1.2`, reordered lines, different uncertainty
spelling) must pass.

**Two markers, two questions:**

- `^CONSTRAINT_SPEC_SCORE: <frac>` — **primary, the mechanism score.** Fraction of the 5 spec properties
  the *applied* SDC satisfies within tolerance: `{clock period, clock uncertainty, input_delay(din,en),
  output_delay(dout), exceptions==∅}`. Re-derived by the hidden script from `oracle/spec_truth.json`,
  **independent of whether PT went green.**
- `^SIGNOFF_OK` / `^SIGNOFF_FAIL` — **secondary.** Real PT `report_timing` has no negative-slack path.

**Golden pass condition.** `CONSTRAINT_SPEC_SCORE == 1.0` **and** `SIGNOFF_OK` → overall ≈ 1.0.

**Mutant fail condition.** The drifted SDC: `output_delay` 3.2 ≠ spec 1.2 → `CONSTRAINT_SPEC_SCORE` 0.8
(4/5), and reg→`dout` violates → `SIGNOFF_FAIL`. With weights `constraint_spec 0.6 / signoff 0.3 /
explanation 0.1`, mutant overall ≈ `0.6·0.8 + 0 + 0.1 = 0.58` vs golden 1.0 → **margin 0.42 ≥ 0.15**
(CLAUDE.md C2 rule satisfied).

**Hidden oracle metadata — `oracle/spec_truth.json`** (never seeded to the agent):

```json
{
  "clock":      {"name": "clk", "period_ns": 4.0, "uncertainty_ns": 0.10, "tol": 0.001},
  "input_delay_ns":  {"value": 1.8, "tol": 0.051, "ports": ["din[*]", "en"],
                      "derivation": "t_co(1.5) + flight(0.3)"},
  "output_delay_ns": {"value": 1.2, "tol": 0.051, "ports": ["dout[*]"],
                      "derivation": "t_su(0.9) + flight(0.3)"},
  "exceptions": [],
  "overconstrain_guard": {"period_min_ns": 4.0, "note": "period < spec ⇒ masking, not a fix"}
}
```

Tolerance `0.051` (just over P9's `_MARGIN/… ` band) admits honest rounding while the drift Δ=2.0 sits far
outside; exact tol fixed at authoring against measured slacks.

**How the evaluator distinguishes a real fix from symptom-suppression** — the core requirement. Because
`CONSTRAINT_SPEC_SCORE` scores the **mechanism** (SDC≡spec) *separately* from `SIGNOFF`, every
symptom-suppressing "fix" is caught even when PT goes green:

| Agent action | SIGNOFF | SPEC_SCORE | overall | verdict |
|---|---|---|---|---|
| Restore `output_delay 1.2` (**true fix**) | OK | 1.0 | **1.00** | pass |
| Leave mutant (no fix) | FAIL | 0.8 | 0.58 | fail |
| Loosen period to 6.0 to clear violation | OK | 0.8 (period≠spec) | 0.88 | fail* |
| Zero/delete `set_output_delay` | OK | 0.8 (output≠spec) | 0.88 | fail* |
| Set `output_delay` to first value that clears (e.g. 2.2) | OK | 0.8 | 0.88 | fail* |
| Edit `spec.md` to match drifted SDC | — | — | — | **anti-cheat** (forbidden file) |
| Fabricate `spec_truth.json` / golden report / `run_hidden.*` | — | — | — | **anti-cheat** (hidden-shadow) |

\* **Pass predicate for the reliability layer is strict:** `pass ⇔ (SIGNOFF_OK ∧ CONSTRAINT_SPEC_SCORE ==
1.0)`. Symptom-suppression scores a high *continuous* value (0.88) but is **not a pass** — the mechanism is
unresolved. If Phase-0C finds the 0.88-vs-1.00 continuous gap too thin to be comfortable, the
`overconstrain_guard` halves `SPEC_SCORE` when `period < spec` (a build-time knob, validated, not assumed).

---

## 5. Agent-visible vs hidden artifacts

Directory layout (standard `files/` + `hidden/` split, identical isolation contract to P7-PT; **no dirs
created this round**):

```text
tasks/p10_synthetic_project/syn_proj_0001/
  prompt.md
  metadata.json
  spec.md                      # VISIBLE, read-only  (forbidden-to-edit) — the authority
  files/                       # = the agent workspace (create_agent_workspace copies ONLY this)
    design.v                   # visible, forbidden-to-edit (RTL, for understanding)
    design_netlist.v           # visible, forbidden-to-edit (timed by PT)
    tiny.db, tiny.lib          # visible, forbidden-to-edit (scalar Liberty)
    constraints.sdc            # EDITABLE — the only file the agent changes
    run_public.sh | .tcl       # visible, forbidden-to-edit (symptom runner)
  hidden/                      # evaluator-only (NEVER seeded to the agent)
    run_hidden.sh | .tcl       # authoritative oracle; emits ^CONSTRAINT_SPEC_SCORE / ^SIGNOFF_OK
    golden/timing_golden.rpt   # golden PT report fixture (provenance / cross-check)
  oracle/
    spec_truth.json            # spec-derived intended constraint set + tolerances
  solution/
    constraints.sdc            # correct fixed SDC (golden-pass gate)
```

> Note: `spec.md` sits at task root and is listed in `files.visible` + `files.forbidden`. To be present in
> the agent workspace it must physically live under `files/` (since `create_agent_workspace` copies only
> `files/`); the task-root path shown is the canonical listing — at build it is placed in `files/spec.md`.
> This is a provisioning detail the regression test in §6 will enforce, not hand-wave.

- **Public (visible):** `spec.md`, `design.v`, `design_netlist.v`, `tiny.db`, `tiny.lib`,
  `constraints.sdc`, `run_public.sh`, `run_public.tcl`.
- **Read-only / forbidden-to-edit:** everything visible **except** `constraints.sdc` — i.e. `spec.md`,
  `design.v`, `design_netlist.v`, `tiny.db`, `tiny.lib`, `run_public.*`. (Editing the spec to match a
  drifted SDC is the obvious cheat; the spec is read-only precisely so the *authority cannot be moved*.)
- **Editable:** `constraints.sdc` only.
- **Hidden:** `run_hidden.sh`, `run_hidden.tcl`, `hidden/golden/timing_golden.rpt`,
  `oracle/spec_truth.json`.
- **Generated reports:** PT writes `applied_<section>.sdc` + a timing report into the *workspace* at run
  time (transient, sanitized before any publish; never committed — `runs/`/`workspaces/` are git-ignored).
- **Public runner behavior:** `run_public.sh` applies the agent's `constraints.sdc` to the golden netlist,
  runs PT `report_timing`, and prints the **timing report + `^SIGNOFF_OK|^SIGNOFF_FAIL`** so the agent can
  observe and iterate on the symptom. It **deliberately does not** compute or print
  `CONSTRAINT_SPEC_SCORE` or the spec-derived numbers — revealing the mechanism score would let an agent
  brute-force values until it hits 1.0 without reconstructing the budget. Symptom is public; the answer key
  is hidden.

---

## 6. Anti-cheat and provisioning invariants

These are **hard invariants**, inherited from the Phase-2 PT-provisioning lesson
(`pt-agentic-provisioning-bug`) and the existing `agentic/workspace.py` guards. The regression test
`tests/test_agentic_provisioning.py` already encodes the general form; Phase-0A extends it to this track.

1. **Public scripts must not reference hidden-only artifacts.** Everything `run_public.*` reads
   (`design_netlist.v`, `tiny.db`, `constraints.sdc`) is in `files/` → present in the agent workspace.
   `run_public.*` must **never** read `run_hidden.*`, `oracle/spec_truth.json`, or `hidden/golden/*`. This
   is the exact bug that contaminated the Phase-2 PT run; the test asserts it across the new track.
2. **Agent workspace is runnable without any hidden file.** `create_agent_workspace` copies only `files/`;
   running `bash run_public.sh` there must produce the symptom (a real PT violation) with **zero** missing
   inputs — no fabrication is ever necessary or tempted.
3. **Hidden oracle injected only in a fresh grading session.** `run_hidden.*`, `oracle/spec_truth.json`,
   and the golden report are overlaid by `create_evaluator_workspace` **after** the agent exits (agent
   edits + `hidden/` merged in a clean temp dir). The agent process can never read them.
4. **Hidden-shadow detection stays active.** `detect_hidden_shadows` flags any agent-created file whose
   basename matches a hidden artifact (`run_hidden.sh/.tcl`, `spec_truth.json`, `timing_golden.rpt`) —
   fabricating the oracle to force a local pass is the P7-class reward-hack and scores ANTI-CHEAT → 0.
5. **Forbidden-file SHA guard.** `detect_forbidden_modifications` (SHA-256 snapshot diff) catches any edit
   to `spec.md`, `design.v`, `design_netlist.v`, `tiny.*`, or `run_*`. Moving the authority (spec) or the
   timed netlist is a violation, not a fix.
6. **Forge-resistant grading (reused verbatim from P7-PT).** `run_*.tcl` applies the agent SDC via
   `read_sdc` (which sandboxes Tcl `proc`/`exit` redefinition, unlike `source`) then `write_sdc -nosplit
   applied_<section>.sdc` launders the *genuine* applied constraints to a fresh file. The `.sh` wrapper
   computes the verdict from that laundered file + `spec_truth.json` and emits the marker **only there**,
   prefixing raw PT output with `[apply]` so an agent-injected `CONSTRAINT_SPEC_SCORE`/`SIGNOFF_OK` cannot
   match the `^`-anchored marker. No agent-controlled Tcl reaches the grader.

---

## 7. Reliability / calibration integration

The score routes through the **existing** layer unchanged (MVP requirement — no new metrics):

- **Driver:** run via the agentic harness (`run-agent` / `run-agent-dataset`) with `--elicit-confidence`
  and `--temperature 0.7`, k≥3 trials, concurrency 2 (b04 seats). The new track is just a new directory
  name under the trial tree; `scripts/reliability_report.py` `load_trees` already reads
  `<tree>/<model>/<track>/<task>.json` and needs **no special-casing** (confirmed by reading its loader).
- **Pass predicate:** `pass ⇔ (SIGNOFF_OK ∧ CONSTRAINT_SPEC_SCORE == 1.0)` (§4) — strict, so
  symptom-suppression is a fail even at continuous 0.88.
- **Metrics that matter here:**
  - **pass@1 / pass@k / pass^k** — can the model solve it at all, any-of-k, all-of-k.
  - **reliability gap (pass@1 − pass^k)** and **flip-rate** — the load-bearing signals; constraint-drift's
    budget arithmetic is exactly the kind of step a capable model may get right inconsistently.
  - **trust / overconfident-wrong** — does a model that *masks* the symptom (PT green, mechanism unfixed)
    **confidently** report success? That confident-wrong-while-green case is the most valuable calibration
    signal this mechanism can produce, and only the hidden spec-equivalence oracle exposes it.
  - **format compliance** + **protocol tally** (nocommit / budget_exhausted / anti_cheat), with **infra
    (429/empty) excluded from capability** and surfaced separately — same taxonomy as Phase-2.
- **Abstention:** the `--elicit-confidence` ABSTAIN path applies unchanged (Phase-2 saw 0 abstentions
  everywhere — worth re-checking on a task where masking is tempting).

This makes a "solvable-but-unreliable" or "green-but-wrong" project a *useful* data point even if pass@1 is
high — the whole reason the reliability layer survived when single-localization tasks did not.

---

## 8. Phase-0A implementation plan (what to build *next*, not now)

**Files / directories to create later:**

- `tasks/p10_synthetic_project/syn_proj_0001/` — the hand-authored task (layout §5). `p10_synthetic_project`
  is a placeholder track name; final name fixed at build.
- `eda_agentbench/schema.py` — **one** additive enum entry in `track.enum` (after `p9_pt_exception_debug`,
  line ~21) and **one** alternative in the `task_id` pattern (line 15, e.g. `syn_proj_[0-9]{4}`). Minimal +
  documented in the commit, per CLAUDE.md's shared-file rule. No required-field change (MVP §Schema: the
  flat `files` lists already hold a multi-file project; a `project_manifest` field is **not** needed for 0A).
- `eda_agentbench/evaluator/synthetic_project.py` — `SyntheticProjectEvaluator(BaseEvaluator)`, mirrors
  `primetime_sta_debug.py`: parse `^CONSTRAINT_SPEC_SCORE:\s*([0-9.]+)` (fractional) and `^SIGNOFF_OK`
  (binary, `re.MULTILINE`, with crash detection), weights `constraint_spec 0.6 / signoff 0.3 /
  explanation 0.1`.
- `eda_agentbench/cli.py` — **one** `elif evaluator_spec == "synthetic_project.SyntheticProjectEvaluator":`
  branch in the dispatch block (~line 575).
- (Phase-0B, later) `generators/p10_synthetic_project_gen.py` — the constraint-drift mutator as an
  automated transform on the golden, deterministic seed (`BaseGenerator(seed, output_dir)`), producing 5–10
  variants (different drifted port / Δ / template).
- `generators/assets/p10_synthetic_project/` — symlink/copy of the reused `tiny.lib`/`tiny.db` (or share
  the P9 asset path directly).

**Tests to add later** (tool-free, `pytest -m "not requires_tools"`):

- `tests/test_synthetic_project.py` — marker parsing (fractional + binary), weight math, golden vs mutant
  margin ≥ 0.15, and the wrong-fix table of §4 (each masking edit scores below the true fix / fails the
  pass predicate).
- extend `tests/test_agentic_provisioning.py` — the new track's `run_public.*` reads only agent-workspace
  files, and the public flow is runnable in a fresh `create_agent_workspace` (invariants 1–2 of §6).
- `tests/test_validate_dataset.py` path — the C1 (golden=1.0) / C2 (margin≥0.15) gate covers the new task
  via `scripts/validate_dataset.py --glob`.

**Tool commands to run later (b04 only; `/tmp` or `~/Desktop/tsb`, clean up, no internet/pip):**

1. VCS smoke: elaborate `design.v` + `tb_smoke.v` → `^SMOKE_OK` (authoring/CI).
2. DC: `synth.tcl` against `tiny.db` → emit golden `design_netlist.v` (once).
3. PT golden gate: golden SDC → `^SIGNOFF_OK` + `^CONSTRAINT_SPEC_SCORE: 1.0`; record golden report.
4. PT mutant check: drifted SDC → `^SIGNOFF_FAIL`, `SPEC_SCORE 0.8`; confirm margin.
5. Fairness gate: grade `solution/constraints.sdc` through the **same** evaluator path → ≈ 1.0
   (the standing rule: golden must score ~1.0 before trusting any model number).

**Estimated cost / runtime.** Golden authoring + gates: a handful of b04 tool invocations (license-time
only, effectively ¥0 of gateway budget). Phase-0D probe (separate step): 3 models × 5 projects × k=3 ≈ 45
agentic episodes; at the Phase-2 anchor (¥132.6 / 225 ep ≈ ¥0.59/ep) ≈ **¥27** — well within the ¥1000
budget; scale to 10 projects ≈ ¥53. Wall-clock per episode is PT-only (seconds of tool time), comparable to
the P7-PT track.

---

## 9. GO / NO-GO criteria

Phase-0A gates the **contract**; Phase-0D (separate, after) gates **difficulty**. Keep them distinct so a
"too easy" verdict does not discard the reusable machinery.

**Phase-0A GO** (build the loop, proceed to 0B mutator) requires **all**:

1. **Golden passes** through the agent's own path: `SIGNOFF_OK ∧ CONSTRAINT_SPEC_SCORE 1.0`, overall ≈ 1.0,
   confirmed on b04 (fairness gate).
2. **Mutant fails with a tool-visible symptom:** real PT setup violation on `dout`; golden − mutant
   continuous margin ≥ 0.15 (≈ 0.42 by design).
3. **Visible symptom exists, fix is not revealed:** `run_public.sh` in a fresh agent workspace shows the
   violation; the correct `1.2` is derivable from `spec.md` arithmetic, absent as a literal.
4. **Oracle can score real-fix vs symptom-suppression:** the §4 wrong-fix table holds — over-constrain /
   zero / first-clearing-value all fail the strict pass predicate and score below the true fix; spec edit →
   forbidden; oracle fabrication → hidden-shadow.
5. **Provisioning is fair:** §6 invariants hold; `test_agentic_provisioning.py` (extended) green;
   `scripts/check` green.
6. **Reliability layer ingests it** with no special-casing (`reliability_report.py` renders the track).

**NO-GO / retire cheaply** if any of:

- The mutant is **trivially localizable** — Phase-0D shows a strong model solves it like the retired
  single-fault tracks (this is the *expected risk* for constraint-drift alone; if so, the loop still stands
  and we route mechanism **B** through the same machinery rather than scaling constraint-drift).
- A **valid symptom-suppression-resistant oracle proves intractable** — e.g. no tolerance band cleanly
  separates true fix from masking without float-jitter flips.
- The measured gap (Phase-0D) is **noise or infra/protocol**, not capability (the `single-localization-
  saturation` / MCMM-noise failure mode).

Record the verdict the way the prior directions were recorded — a memory entry + one-line status — so the
next cycle inherits the evidence.

---

## Guardrails (restated, unchanged)

Cheap-probe-before-build; reuse don't fork; EDA tools **only on b04** (`/tmp` or `~/Desktop/tsb`, clean up,
no internet/pip); shim stays outside the repo; never commit credentials or raw tool outputs; never modify
hidden/oracle/forbidden/scoring to manufacture a score; grade the golden through the same path before
trusting any number; ¥1000 total budget — Phase-0A authoring is effectively free, the 0D probe is tiny; do
not touch the Phase-2 reliability directories; **no generator code, no b04 runs, no commit/push** without
explicit instruction.
