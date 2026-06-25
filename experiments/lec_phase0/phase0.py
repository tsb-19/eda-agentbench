"""LEC-Attribution Phase-0 falsification experiment (hand-authored, NOT a track commitment).

User-set success criteria (all must hold, else RETIRE LEC before any generator):
  1. golden identifies the mutation site/cone
  2. symptom-listing baseline scores significantly lower
  3. frontier models cannot ace by repeating Formality output   (separate frontier probe)
  4. margin >= 0.15 across multiple variants

This file builds the assets + grader and runs the SCRIPTED gate (criteria 1,2,4). The netlist
pairs' multi-symptom-from-one-cause structure is verified separately on real fm_shell (b04).

Design: each impl is the reference RE-STRUCTURED (every line rewritten, equivalent) EXCEPT ONE
internal net mutated. That net feeds >=2 outputs -> >=2 failing compare points. The failing
compare points are OUTPUTS (what Formality prints); the root cause is the INTERNAL net. So a model
that echoes Formality's failing points names the wrong things; only genuine cone-tracing finds it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# --- two hand-authored variants: (golden, impl_mut, oracle) ----------------
TASKS = {
    "task1": {
        "golden": """\
module top(input a, b, c, d, output z1, z2, z3);
  wire p, q, r;
  assign p = a ^ b;
  assign q = c & d;
  assign r = p | q;
  assign z1 = r & a;
  assign z2 = r | d;
  assign z3 = p & c;
endmodule
""",
        # restructured (every line rewritten, equivalent) EXCEPT n_r mutated (| -> &)
        "impl": """\
module top(input a, b, c, d, output z1, z2, z3);
  wire n_p, n_q, n_r, t2;
  assign n_p = (a & ~b) | (~a & b);
  assign n_q = ~(~c | ~d);
  assign n_r = n_p & n_q;
  assign z1 = n_r & a;
  assign z2 = n_r | d;
  assign t2 = n_p & c;
  assign z3 = t2;
endmodule
""",
        "oracle": {"cause": "n_r", "cause_inputs": ["n_p", "n_q"],
                   "symptoms": ["z1", "z2", "z3"], "failing": ["z1", "z2"]},
    },
    "task2": {
        "golden": """\
module top(input a, b, c, d, e, output o1, o2, o3);
  wire s, t, u;
  assign s = a | b;
  assign t = c & d;
  assign u = s & t;
  assign o1 = u ^ e;
  assign o2 = u | a;
  assign o3 = s & e;
endmodule
""",
        # restructured EXCEPT m_u mutated (& -> |)
        "impl": """\
module top(input a, b, c, d, e, output o1, o2, o3);
  wire m_s, m_t, m_u, w;
  assign m_s = ~(~a & ~b);
  assign m_t = ~(~c | ~d);
  assign m_u = m_s | m_t;
  assign o1 = m_u ^ e;
  assign o2 = m_u | a;
  assign w = m_s & e;
  assign o3 = w;
endmodule
""",
        "oracle": {"cause": "m_u", "cause_inputs": ["m_s", "m_t"],
                   "symptoms": ["o1", "o2", "o3"], "failing": ["o1", "o2"]},
    },
    # --- DEEP variants: divergence buried 3-4 levels up, generic net names (no name
    #     correspondence to the reference), propagation points that must be REJECTED. ---
    "task3": {  # mutation at the mid node n5 (| -> ^), depth 3 from the failing outputs
        "golden": """\
module top(input a, b, c, d, e, f, g, h, output y1, y2);
  wire l1, l2, l3, l4, m1, m2, hi;
  assign l1 = a & b;
  assign l2 = c ^ d;
  assign l3 = e | f;
  assign l4 = g & h;
  assign m1 = l1 | l2;
  assign m2 = l3 ^ l4;
  assign hi = m1 & m2;
  assign y1 = hi ^ a;
  assign y2 = hi | h;
endmodule
""",
        "impl": """\
module top(input a, b, c, d, e, f, g, h, output y1, y2);
  wire n1, n2, n3, n4, n5, n6, n7;
  assign n1 = ~(~a | ~b);
  assign n2 = (c & ~d) | (~c & d);
  assign n3 = ~(~e & ~f);
  assign n4 = ~(~g | ~h);
  assign n5 = n1 ^ n2;
  assign n6 = (n3 & ~n4) | (~n3 & n4);
  assign n7 = n5 & n6;
  assign y1 = n7 ^ a;
  assign y2 = n7 | h;
endmodule
""",
        "oracle": {"cause": "n5", "cause_inputs": ["n1", "n2"],
                   "symptoms": ["y1", "y2"], "failing": ["y1", "y2"],
                   "propagation_points": ["n7"]},
    },
    "task4": {  # mutation at a LEAF node n2 (c^d -> c&d), depth 4; n5/n7 are propagation points
        "golden": """\
module top(input a, b, c, d, e, f, g, h, output y1, y2);
  wire l1, l2, l3, l4, m1, m2, hi;
  assign l1 = a & b;
  assign l2 = c ^ d;
  assign l3 = e | f;
  assign l4 = g & h;
  assign m1 = l1 | l2;
  assign m2 = l3 ^ l4;
  assign hi = m1 & m2;
  assign y1 = hi ^ a;
  assign y2 = hi | h;
endmodule
""",
        "impl": """\
module top(input a, b, c, d, e, f, g, h, output y1, y2);
  wire n1, n2, n3, n4, n5, n6, n7;
  assign n1 = ~(~a | ~b);
  assign n2 = c & d;
  assign n3 = ~(~e & ~f);
  assign n4 = ~(~g | ~h);
  assign n5 = n1 | n2;
  assign n6 = (n3 & ~n4) | (~n3 & n4);
  assign n7 = n5 & n6;
  assign y1 = n7 ^ a;
  assign y2 = n7 | h;
endmodule
""",
        "oracle": {"cause": "n2", "cause_inputs": ["c", "d"],
                   "symptoms": ["y1", "y2"], "failing": ["y1", "y2"],
                   "propagation_points": ["n5", "n7"]},
    },
}

PROMPT_TMPL = """\
# LEC Failure Attribution: `top`

`impl.v` was produced from the reference `golden.v` by an automated transform, but Formality
reports the two designs are NOT logically equivalent. Find the ROOT CAUSE.

## What you have
- `golden.v` — the reference (correct) design.
- `impl.v` — the implementation under test. It has been STRUCTURALLY REWRITTEN — it is NOT a
  line-by-line copy of the reference, so you cannot simply diff the two files.
- Formality `verify` result below.

## Formality result
Verification FAILED.
{fail_lines}
(every other compare point passed.)

## Your task
The failing compare points are **outputs** — symptoms at the end of the affected logic. Exactly
ONE internal signal in `impl.v` is computed incorrectly and feeds all the failing outputs.
Identify that single root-cause signal. Answer with the wire NAME as declared in `impl.v`, and
state what it computes vs. what it should compute.

## Rules
- Naming the failing compare points (the outputs) is NOT an answer — those are symptoms.
- Name the one internal signal in `impl.v` that is the actual divergence.
"""


def write_assets():
    for name, t in TASKS.items():
        d = ROOT / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "golden.v").write_text(t["golden"])
        (d / "impl.v").write_text(t["impl"])
        (d / "oracle.json").write_text(json.dumps(t["oracle"], indent=2) + "\n")
        fail_lines = "\n".join(f"  Compare point {f} failed (is not equivalent)"
                               for f in t["oracle"]["failing"])
        (d / "prompt.md").write_text(PROMPT_TMPL.format(fail_lines=fail_lines))


# --- attribution grader ----------------------------------------------------

def grade(answer_text: str, oracle: dict) -> dict:
    """ATTR score: identifying the INTERNAL root-cause net = 1.0; echoing only the failing
    outputs (symptoms) = 0.0. Token-based against the named net (prompt asks for the wire name)."""
    toks = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", answer_text))
    named_cause = oracle["cause"] in toks
    named_symptoms = sorted(set(oracle["symptoms"]) & toks)
    score = 1.0 if named_cause else 0.0
    verdict = ("ATTRIBUTED" if named_cause
               else ("SYMPTOM_LISTING" if named_symptoms else "MISS"))
    return {"score": score, "named_cause": named_cause,
            "named_symptoms": named_symptoms, "verdict": verdict}


# scripted baseline "agents"
def golden_answer(oracle):   # a perfect attributor
    return (f"The root cause is the internal signal `{oracle['cause']}` in impl.v. It is computed "
            f"as {oracle['cause_inputs'][0]} AND {oracle['cause_inputs'][1]} but should be OR; this "
            f"feeds the failing outputs.")


def symptom_answer(oracle):  # echoes Formality's failing compare points
    return (f"Formality reports the failing compare points are {', '.join(oracle['failing'])}. "
            f"These outputs are not equivalent between golden.v and impl.v.")


if __name__ == "__main__":
    write_assets()
    print(f"{'variant':8}{'agent':10}{'score':>7}  verdict")
    margins = []
    for name, t in TASKS.items():
        o = t["oracle"]
        g = grade(golden_answer(o), o)
        s = grade(symptom_answer(o), o)
        print(f"{name:8}{'golden':10}{g['score']:7.2f}  {g['verdict']}")
        print(f"{name:8}{'symptom':10}{s['score']:7.2f}  {s['verdict']} {s['named_symptoms']}")
        margins.append(g["score"] - s["score"])
    mn = min(margins)
    print(f"\nmin margin (golden - symptom) across {len(margins)} variants: {mn:.2f}  "
          f"[{'PASS' if mn >= 0.15 else 'FAIL'} >=0.15]")
    print("Criteria 1,2,4 (scripted): "
          + ("PASS" if mn >= 0.15 else "FAIL")
          + "  -- criterion 3 (frontier no-echo) = separate probe")
