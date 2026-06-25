"""P10 Synthetic Project generator — Phase-0B constraint-drift mutator (tiny, deterministic).

Turns the hand-authored ``syn_proj_0001`` contract into a deterministic generator that
emits ``acc_stage``-style timing-constraint tasks of ONE family and ONE mechanism:

    golden project -> constraint-drift mutant -> PrimeTime oracle -> evaluator score

This proves the GENERATOR contract (fair, oracle-checkable, byte-deterministic variants
without answer/hidden leaks), not difficulty — see docs/synthetic_phase0b_generator_design.md.

Closed-form timing backbone (reused P9 scalar Liberty tiny.db: BUFX1 0.10, DFF clk->Q 0.08,
setup 0.02), confirmed on b04 for syn_proj_0001 to 0.01 ns:

    input -> reg   (din,en) :  slack = (T - U - 0.02) - I        - 0.10*D
    reg   -> reg   (internal): slack = (T - U - 0.02) - 0.08     - 0.10*D   (= (T-U-0.10) - 0.10*D)
    reg   -> out   (dout)   :  slack = (T - U - O)    - 0.08     - 0.10*D

Because every slack is exact, the generator SOLVES for buffer depths and a drift magnitude
that guarantee golden-pass / mutant-fail with a fixed margin — no trial PT runs to build a
task, only to validate it. One budget value drifts (output_delay / input_delay / uncertainty,
all "wrong value" = constraint drift), so exactly one SDC line differs golden->mutant.

The drifted property is always DERIVED in the spec (stated as budget terms, never as the
value) so the correct answer is not a copyable literal; non-drifted properties may be stated
directly. The hidden oracle (grade_spec.py / spec_truth.json), the runner scripts, design.v
and the scalar library are reused VERBATIM from syn_proj_0001 — ports stay {din,en,dout}, so
no hidden-grader change is needed.
"""

from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path

from generators.base import BaseGenerator

_REPO = Path(__file__).resolve().parent.parent
# The hand-authored Phase-0A task: source of the reused static machinery + assets.
_TEMPLATE = _REPO / "tasks" / "p10_synthetic_project" / "syn_proj_0001"

# Cell timing — MUST match tiny.lib and the b04-confirmed hand task.
_BUF = 0.10
_CLK_Q = 0.08
_SETUP = 0.02
_MARGIN = 0.05          # keep slacks clear of 0 so float jitter cannot flip a verdict
_PUSH = 0.30            # mutant binding-arc slack target = -_PUSH (a clear, unambiguous violation)

# Sampling pools (chosen so every combination is feasible for T >= 3.0 with comfortable headroom).
_PERIODS = [3.0, 4.0, 5.0, 6.0]
_UNC = [0.05, 0.10, 0.15]
_TCO = [0.9, 1.1, 1.3, 1.5]
_FLIGHT = [0.2, 0.3, 0.4]
_TSU = [0.5, 0.7, 0.9]
_JITTER = [0.04, 0.05, 0.06, 0.07]
_SKEW = [0.04, 0.05, 0.06, 0.07]
_DRIFTS = ["output_delay", "input_delay", "uncertainty"]
_S_DRIFT = [0.08, 0.13, 0.18]   # binding (to-be-drifted) arc golden slack target
_S_BIG = [0.45, 0.60, 0.75]     # non-binding arcs golden slack target

_STATIC_FILES = ["design.v", "tiny.lib", "tiny.db", "run_public.sh", "run_public.tcl"]
_STATIC_HIDDEN = ["run_hidden.sh", "run_hidden.tcl", "run_signoff.tcl", "grade_spec.py"]

_MAX_RESAMPLE = 200


def _fmt(x: float) -> str:
    """Stable minimal decimal rendering (4.0 -> '4.0', 0.10 -> '0.1', 1.20 -> '1.2')."""
    x = round(x, 3)
    if x == int(x):
        return f"{int(x)}.0"
    return f"{x:.3f}".rstrip("0").rstrip(".")


def _depth(avail: float, target_slack: float) -> int:
    """Largest integer buffer depth D >= 1 with (avail - 0.10*D) >= target_slack."""
    d = math.floor((avail - target_slack) / _BUF + 1e-9)
    return max(d, 1)


def _has_token(text: str, value: float) -> bool:
    """True iff _fmt(value) appears as a standalone numeric token in text."""
    tok = _fmt(value)
    return re.search(rf"(?<![\d.]){re.escape(tok)}(?![\d.])", text) is not None


class SyntheticProjectGenerator(BaseGenerator):
    """Deterministic constraint-drift task generator for the p10_synthetic_project track."""

    def __init__(self, seed: int, output_dir: Path, id_start: int = 2):
        super().__init__(seed, output_dir)
        self.id_start = id_start
        # Concatenated text of the reused static visible files (design.v, runners, library):
        # the leak scan must cover these too, so a drifted value can't coincide with a token
        # already present (e.g. a tiny.lib cell delay).
        self._static_visible = "".join(
            (_TEMPLATE / "files" / f).read_text()
            for f in ("design.v", "run_public.sh", "run_public.tcl", "tiny.lib")
        )

    # --- parameter solve ---------------------------------------------------

    def _solve(self) -> dict:
        """Draw + solve one feasible, leak-free parameter vector (deterministic resample)."""
        for _ in range(_MAX_RESAMPLE):
            p = self._draw()
            if p is not None:
                return p
        raise RuntimeError("could not solve a feasible synthetic project (check sampling pools)")

    def _draw(self) -> dict | None:
        rng = self.rng
        T = rng.choice(_PERIODS)
        drift = rng.choice(_DRIFTS)
        t_co = rng.choice(_TCO)
        flight_in = rng.choice(_FLIGHT)
        t_su = rng.choice(_TSU)
        flight_out = rng.choice(_FLIGHT)
        I = round(t_co + flight_in, 3)
        O = round(t_su + flight_out, 3)
        if drift == "uncertainty":
            jitter = rng.choice(_JITTER)
            skew = rng.choice(_SKEW)
            U = round(jitter + skew, 3)
        else:
            jitter = skew = None
            U = rng.choice(_UNC)
        s_drift = rng.choice(_S_DRIFT)
        s_big = rng.choice(_S_BIG)

        # available time per arc
        avail_in = round((T - U - _SETUP) - I, 6)
        avail_reg = round((T - U - _SETUP) - _CLK_Q, 6)
        avail_out = round((T - U - O) - _CLK_Q, 6)
        if min(avail_in, avail_reg, avail_out) <= _S_DRIFT[0] + _BUF:
            return None  # too tight for depth >= 1 at the smallest target — resample

        # binding arc (the one a drift will push negative): din for input drift, else reg->out
        binding = "din" if drift == "input_delay" else "out"
        tgt_din = s_drift if binding == "din" else s_big
        tgt_out = s_drift if binding == "out" else s_big

        D_din = _depth(avail_in, tgt_din)
        D_en = _depth(avail_in, s_big)      # en never binding -> larger slack -> shallower
        D_reg = _depth(avail_reg, s_big)
        D_out = _depth(avail_out, tgt_out)
        if min(D_din, D_en, D_reg, D_out) < 1:
            return None

        s_din = round(avail_in - _BUF * D_din, 6)
        s_en = round(avail_in - _BUF * D_en, 6)
        s_reg = round(avail_reg - _BUF * D_reg, 6)
        s_out = round(avail_out - _BUF * D_out, 6)
        golden = [s_din, s_en, s_reg, s_out]
        g_worst = min(golden)
        if g_worst < _MARGIN - 1e-9:
            return None  # golden would not sign off cleanly — resample

        s_bind = s_din if binding == "din" else s_out
        delta = round(s_bind + _PUSH, 2)

        # mutant value + mutant worst slack
        if drift == "output_delay":
            mut_val = round(O + delta, 3)
            m_worst = min(s_din, s_en, s_reg, round(s_out - delta, 6))
        elif drift == "input_delay":
            mut_val = round(I + delta, 3)
            m_worst = min(round(s_din - delta, 6), round(s_en - delta, 6), s_reg, s_out)
        else:  # uncertainty: all arcs shift by -delta
            mut_val = round(U + delta, 3)
            m_worst = round(g_worst - delta, 6)
        if m_worst > -_MARGIN + 1e-9:
            return None  # mutant would not clearly violate — resample

        p = {
            "T": T, "U": U, "I": I, "O": O,
            "t_co": t_co, "flight_in": flight_in, "t_su": t_su, "flight_out": flight_out,
            "jitter": jitter, "skew": skew,
            "drift": drift, "delta": delta, "mut_val": mut_val,
            "D_din": D_din, "D_en": D_en, "D_reg": D_reg, "D_out": D_out,
            "s_din": s_din, "s_en": s_en, "s_reg": s_reg, "s_out": s_out,
            "golden_worst_slack": round(g_worst, 4), "mutant_worst_slack": round(m_worst, 4),
        }

        # F6 — no literal answer leak: the DRIFTED property's golden value must not appear as a
        # standalone token anywhere in agent-visible content (spec, the visible mutant SDC, the
        # netlist, or the reused static files such as tiny.lib).
        leak_val = {"output_delay": O, "input_delay": I, "uncertainty": U}[drift]
        visible = "\n".join((self._spec_md(p), self._sdc(p, mutant=True),
                             self._netlist(p), self._static_visible))
        if _has_token(visible, leak_val):
            return None
        return p

    # --- templated artifacts ----------------------------------------------

    def _sdc(self, p: dict, *, mutant: bool) -> str:
        T, U, I, O = p["T"], p["U"], p["I"], p["O"]
        if mutant:
            if p["drift"] == "output_delay":
                O = p["mut_val"]
            elif p["drift"] == "input_delay":
                I = p["mut_val"]
            else:
                U = p["mut_val"]
        return (
            "# Timing constraints for acc_stage\n"
            "# Must encode the interface budget from spec.md (I/O delays are budget sums, not literals).\n"
            f"create_clock -name clk -period {_fmt(T)} [get_ports clk]\n"
            f"set_clock_uncertainty {_fmt(U)} [get_clocks clk]\n"
            f"set_input_delay  {_fmt(I)} -clock clk [get_ports {{din en}}]\n"
            f"set_output_delay {_fmt(O)} -clock clk [get_ports dout]\n"
        )

    def _spec_md(self, p: dict) -> str:
        T = p["T"]
        if p["drift"] == "uncertainty":
            unc_block = (
                "- Clock uncertainty to apply at sign-off — derive it from the sign-off margins:\n"
                f"    - clock jitter: **{_fmt(p['jitter'])} ns**\n"
                f"    - clock skew margin: **{_fmt(p['skew'])} ns**\n"
                "    - ⇒ the uncertainty to apply = jitter + skew.\n"
            )
        else:
            unc_block = (
                f"- Clock uncertainty to apply at sign-off (jitter + skew margin): **{_fmt(p['U'])} ns**.\n"
            )
        return (
            "# acc_stage — Timing Sign-off Contract (authoritative spec)\n\n"
            "`acc_stage` is a registered datapath stage on a single clock `clk`. This document is the\n"
            "**authority** for its timing constraints. The constraint file `constraints.sdc` must encode\n"
            "exactly this contract; if the two disagree, the spec wins.\n\n"
            "## Clock\n\n"
            f"- Target clock period **T = {_fmt(T)} ns**.\n"
            f"{unc_block}\n"
            "## Interface budget (derive the SDC I/O delays from these facts)\n\n"
            "The SDC input/output delays are **not** stated directly — compute them from the neighbouring\n"
            "blocks' budgets. This is ordinary budget arithmetic, not a number to copy.\n\n"
            "**Upstream source block** (drives `din` and `en`):\n"
            f"- launch flip-flop clock-to-Q (t_co): **{_fmt(p['t_co'])} ns**\n"
            f"- board / interconnect flight into `acc_stage`: **{_fmt(p['flight_in'])} ns**\n"
            "- ⇒ the external delay seen at our inputs `din`, `en` = t_co + flight.\n\n"
            "**Downstream sink block** (captures `dout`):\n"
            f"- capture flip-flop setup requirement (t_su): **{_fmt(p['t_su'])} ns**\n"
            f"- board / interconnect flight out of `acc_stage`: **{_fmt(p['flight_out'])} ns**\n"
            "- ⇒ the external delay the sink needs before its capture edge = t_su + flight.\n\n"
            "## Sign-off requirement\n\n"
            "With the constraints encoding the budget above, PrimeTime setup sign-off must report **no\n"
            "negative-slack paths**.\n\n"
            "Over-constraining is **not** a valid fix. Tightening the period, inflating the uncertainty,\n"
            "zeroing a delay, or padding a delay beyond its budget can make a violation disappear without\n"
            "making the constraints correct. The constraints must **match the interface budget**, not\n"
            "merely silence the symptom.\n"
        )

    def _netlist(self, p: dict) -> str:
        body: list[str] = []
        wires: set[str] = {"cap_d", "cap_q", "acc_d", "acc_q", "en_d", "en_q"}

        def chain(prefix: str, src: str, depth: int, dst: str) -> None:
            prev = src
            for k in range(depth):
                node = dst if k == depth - 1 else f"{prefix}{k}"
                if node != "dout":
                    wires.add(node)
                body.append(f"  BUFX1 {prefix}_b{k} (.A({prev}), .Y({node}));")
                prev = node

        chain("i", "din", p["D_din"], "cap_d")
        body.append("  DFFX1 cap_reg (.D(cap_d), .CK(clk), .Q(cap_q));")
        chain("r", "cap_q", p["D_reg"], "acc_d")
        body.append("  DFFX1 acc_reg (.D(acc_d), .CK(clk), .Q(acc_q));")
        chain("o", "acc_q", p["D_out"], "dout")
        chain("e", "en", p["D_en"], "en_d")
        body.append("  DFFX1 en_reg (.D(en_d), .CK(clk), .Q(en_q));")

        wire_decl = "  wire " + ", ".join(sorted(wires)) + ";"
        header = (
            "// Gate-level timing model for acc_stage — timed by PrimeTime against tiny.db.\n"
            "// Scalar-delay abstraction (BUFX1 0.10, DFFX1 clk->Q 0.08, setup 0.02). Async reset\n"
            "// omitted; only the three governed timing paths are represented. Buffer-chain depths:\n"
            f"//   din -> cap_reg : depth {p['D_din']}\n"
            f"//   cap_reg->acc_reg: depth {p['D_reg']}\n"
            f"//   acc_reg-> dout : depth {p['D_out']}\n"
            f"//   en  -> en_reg  : depth {p['D_en']}\n"
            "module acc_stage (clk, din, en, dout);\n"
            "  input  clk;\n  input  din;\n  input  en;\n  output dout;\n\n"
        )
        return header + wire_decl + "\n" + "\n".join(body) + "\nendmodule\n"

    def _truth(self, p: dict) -> dict:
        return {
            "_comment": ("Hidden oracle metadata, generated by p10_synthetic_project_gen.py. Used ONLY "
                         "inside grade_spec.py; never seen by the agent. Values are the spec-derived "
                         f"intended constraints: input_delay = t_co {_fmt(p['t_co'])} + flight "
                         f"{_fmt(p['flight_in'])} = {_fmt(p['I'])}; output_delay = t_su {_fmt(p['t_su'])} "
                         f"+ flight {_fmt(p['flight_out'])} = {_fmt(p['O'])}."),
            "clock": {
                "name": "clk", "period_ns": p["T"], "uncertainty_ns": p["U"],
                "period_tol": 0.01, "uncertainty_tol": 0.011,
            },
            "input_delay": {
                "value_ns": p["I"], "tol": 0.051, "ports": ["din", "en"],
                "derivation": f"t_co {_fmt(p['t_co'])} + flight {_fmt(p['flight_in'])}",
            },
            "output_delay": {
                "value_ns": p["O"], "tol": 0.051, "ports": ["dout"],
                "derivation": f"t_su {_fmt(p['t_su'])} + flight {_fmt(p['flight_out'])}",
            },
            "forbid_exceptions": True,
            "overconstrain": {
                "period_min_ns": p["T"], "uncertainty_max_ns": p["U"],
                "note": ("tightening period, inflating uncertainty, or zeroing/padding a delay is "
                         "masking, not a fix; rejected by the within-tolerance property checks"),
            },
        }

    def _prompt(self, p: dict) -> str:
        return (
            "# Timing Constraint Sign-off Debug: `acc_stage`\n\n"
            "You own static-timing sign-off for the `acc_stage` datapath stage. The constraint file\n"
            "`constraints.sdc` is failing sign-off review.\n\n"
            "## What to do\n\n"
            "Edit **`constraints.sdc`** so that:\n"
            "1. PrimeTime setup sign-off reports no negative-slack paths, **and**\n"
            "2. the constraints encode the **interface budget defined in `spec.md`** (the authority).\n\n"
            "`spec.md` gives the clock target and the neighbouring blocks' budgets. The clock, input, and\n"
            "output constraints must all match the spec; the I/O delays are **not** stated literally —\n"
            "derive them from the budget arithmetic in the spec.\n\n"
            "## Symptom\n\n"
            "`report_timing` reports a setup **violation**. The violation is real, but its cause is that a\n"
            "constraint no longer matches the spec budget. Making the violation disappear is **necessary\n"
            "but not sufficient**: over-constraining (tightening the period, inflating uncertainty, zeroing\n"
            "or padding a delay) is rejected at sign-off review — the constraints must match the spec, not\n"
            "merely silence the symptom.\n\n"
            "## Files\n\n"
            "- `spec.md` — the authoritative timing contract (read-only)\n"
            "- `design.v` — RTL of `acc_stage` (read-only)\n"
            "- `design_netlist.v` — gate-level netlist timed by PrimeTime (read-only)\n"
            "- `tiny.lib`, `tiny.db` — scalar timing library (read-only)\n"
            "- `constraints.sdc` — the constraint file (**you may edit only this file**)\n"
            "- `run_public.sh`, `run_public.tcl` — live sign-off feedback (read-only)\n\n"
            "## Feedback\n\n"
            "Run `bash run_public.sh` for live `report_timing` and a sign-off pass/fail indication. There\n"
            "is no answer key in the feedback — reason about the spec budget the way an engineer does\n"
            "before sign-off.\n\n"
            "## Rules\n\n"
            "- Only `constraints.sdc` is editable; every other file is read-only.\n"
            "- The design has a single clock `clk`. Design ports: `clk`, `din`, `en`, `dout`.\n"
        )

    def _meta(self, p: dict, task_id: str, task_index: int) -> dict:
        mutation = {
            "output_delay": f"set_output_delay dout {_fmt(p['O'])} -> {_fmt(p['mut_val'])}",
            "input_delay": f"set_input_delay din,en {_fmt(p['I'])} -> {_fmt(p['mut_val'])}",
            "uncertainty": f"set_clock_uncertainty {_fmt(p['U'])} -> {_fmt(p['mut_val'])}",
        }[p["drift"]]
        return {
            "task_id": task_id,
            "track": "p10_synthetic_project",
            "tool": ["pt"],
            "difficulty": "medium",
            "data_type": "mutation_synthetic",
            "resource_preset": "standard",
            "timeout_sec": 300,
            "max_tool_calls": 30,
            "max_patch_attempts": 8,
            "max_output_tokens": 32000,
            "files": {
                "visible": ["spec.md", "design.v", "design_netlist.v", "tiny.lib", "tiny.db",
                            "constraints.sdc", "run_public.sh", "run_public.tcl"],
                "editable": ["constraints.sdc"],
                "hidden": ["run_hidden.sh", "run_hidden.tcl", "run_signoff.tcl", "grade_spec.py",
                           "spec_truth.json"],
                "forbidden": ["spec.md", "design.v", "design_netlist.v", "tiny.lib", "tiny.db",
                              "run_public.sh", "run_public.tcl",
                              "run_hidden.sh", "run_hidden.tcl", "run_signoff.tcl", "grade_spec.py"],
            },
            "run_command": "bash run_public.sh && bash run_hidden.sh",
            "scoring": {
                "weights": {"constraint_spec": 0.6, "signoff": 0.3, "explanation": 0.1},
                "evaluator": "synthetic_project.SyntheticProjectEvaluator",
                "explanation_weight": 0.1,
            },
            "sanitizer": {"enabled": True},
            "generator": {
                "script": "p10_synthetic_project_gen.py",
                "seed": self.seed,
                "task_index": task_index,
                "params": {
                    "mechanism": "constraint_drift",
                    "drift_type": p["drift"],
                    "mutation": mutation,
                    "delta_ns": p["delta"],
                    "period_ns": p["T"],
                    "uncertainty_ns": p["U"],
                    "expected_input_delay_ns": p["I"],
                    "expected_output_delay_ns": p["O"],
                    "budget_terms": {
                        "t_co": p["t_co"], "flight_in": p["flight_in"],
                        "t_su": p["t_su"], "flight_out": p["flight_out"],
                        "jitter": p["jitter"], "skew": p["skew"],
                    },
                    "depths": {"din": p["D_din"], "reg": p["D_reg"],
                               "out": p["D_out"], "en": p["D_en"]},
                    "golden_arc_slacks_ns": {"din": p["s_din"], "en": p["s_en"],
                                             "reg": p["s_reg"], "out": p["s_out"]},
                    "golden_worst_slack_ns": p["golden_worst_slack"],
                    "mutant_worst_slack_ns": p["mutant_worst_slack"],
                    "golden_signoff": "OK",
                    "mutant_signoff": "FAIL",
                },
            },
            "expected_error_category": f"constraint_drift_{p['drift']}",
            "version": "0.1.0",
        }

    # --- emit --------------------------------------------------------------

    def generate_one(self, task_index: int) -> Path:
        p = self._solve()
        task_id = f"syn_proj_{self.id_start + task_index:04d}"
        d = self.output_dir / task_id
        (d / "files").mkdir(parents=True, exist_ok=True)
        (d / "hidden").mkdir(exist_ok=True)
        (d / "solution").mkdir(exist_ok=True)

        for f in _STATIC_FILES:
            shutil.copyfile(_TEMPLATE / "files" / f, d / "files" / f)
        for f in _STATIC_HIDDEN:
            shutil.copyfile(_TEMPLATE / "hidden" / f, d / "hidden" / f)

        (d / "files" / "spec.md").write_text(self._spec_md(p))
        (d / "files" / "design_netlist.v").write_text(self._netlist(p))
        (d / "files" / "constraints.sdc").write_text(self._sdc(p, mutant=True))
        (d / "solution" / "constraints.sdc").write_text(self._sdc(p, mutant=False))
        (d / "hidden" / "spec_truth.json").write_text(json.dumps(self._truth(p), indent=2) + "\n")
        (d / "prompt.md").write_text(self._prompt(p))
        (d / "metadata.json").write_text(json.dumps(self._meta(p, task_id, task_index), indent=2) + "\n")
        return d
