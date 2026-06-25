"""MCMM budget+hidden-corner — STABILITY + mechanism-attribution probe.

Multi-variant run did NOT reproduce the n=1 discrimination (GLM inverted, models flip pass/fail on
near-identical variants). That smells like sampling noise. This probe isolates the two questions the
multi-variant run conflated:

  Q1 STABILITY: repeat the SAME variant (v0) N times per model. If a model flips pass/fail across
     identical repeats, the per-model score is noise, not capability -> NOT a discriminator.
  Q2 MECHANISM: the thesis is "lazy probers never query the coupling corners (7,8,9), so they
     balance the A/B-stress axes at x=0.5 and die on the hidden coupling corner." So capture, per
     episode, whether the model PROBED any coupling corner and whether it PASSED. If pass strongly
     correlates with probing-coupling, the failure is mechanism-driven (real). If not, it's a
     coin-flip on the x=0.5 heuristic (a gotcha, not a capability axis).

v0 facts: visible optimum ~x=0.14 PASSES hidden (so a model that truly optimizes visible corners,
incl. coupling 7/8/9, passes); naive "balance A and B" -> x=0.5 -> FAILS hidden (-0.100). Budget=6.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/data1/tongsb/eda-agentbench")
from scripts.generate_model_submissions import load_model_specs

P = 1.8
BUDGET = 6
REPS = 5
VISIBLE = {0: (1.5, 0.6, 0.0), 1: (0.6, 1.5, 0.0), 2: (1.3, 0.8, 0.0), 3: (0.8, 1.3, 0.0),
           4: (1.1, 1.0, 0.0), 5: (1.0, 1.1, 0.0), 6: (1.2, 0.9, 0.0),
           7: (0.9, 0.9, 0.9), 8: (1.0, 0.8, 0.8), 9: (0.7, 0.7, 0.5)}
HIDDEN = {100: (0.9, 0.9, 1.0), 101: (1.5, 0.7, 0.0), 102: (0.7, 1.5, 0.0)}
ALL = {**VISIBLE, **HIDDEN}
COUPLING = {7, 8, 9}  # the visible corners that REVEAL coupling matters


def cost(x, abc):
    A, B, C = abc
    return A * (1 - x) + B * x + C * 4 * x * (1 - x)


def grade(x):
    sl = {c: P - cost(x, ALL[c]) for c in ALL}
    worst = min(sl, key=sl.get)
    return sl[worst] >= 0, round(sl[worst], 3), worst


INTRO = f"""\
You are closing timing by choosing ONE knob x in [0.0, 1.0]. Slack at a corner depends on x and on
hidden per-corner factors. 10 corners have ids 0..9; additional HIDDEN corners are used only for
final signoff. A corner FAILS if slack < 0; your x must make EVERY corner (including hidden) pass.
You have a BUDGET of {BUDGET} slack queries. Query with lines exactly like:
  QUERY corner=<id> x=<value>
When ready, output exactly: COMMIT x=<value>
Graded on ALL corners incl. hidden. Spend queries wisely. Begin."""
QPAT = re.compile(r"QUERY\s+corner\s*=\s*(\d+)\s+x\s*=\s*([0-9]*\.?[0-9]+)", re.I)
CPAT = re.compile(r"COMMIT\s+x\s*=\s*([0-9]*\.?[0-9]+)", re.I)


def run_episode(provider, gk):
    msgs = [{"role": "system", "content": "You are a senior STA/signoff engineer. Be terse."},
            {"role": "user", "content": INTRO}]
    used = 0
    probed = set()
    last = ""
    for _ in range(8):
        resp = provider.chat(msgs, **gk).text or ""
        last = resp
        msgs.append({"role": "assistant", "content": resp})
        cm = CPAT.search(resp)
        if cm:
            return float(cm.group(1)), used, probed, None
        out = []
        for cid, xv in QPAT.findall(resp):
            if used >= BUDGET:
                out.append(f"corner {cid} x={xv}: BUDGET EXCEEDED"); continue
            used += 1
            cidn = int(cid)
            probed.add(cidn)
            out.append(f"corner {cid} x={xv}: slack={P-cost(float(xv), VISIBLE[cidn]):.3f}"
                       if cidn in VISIBLE else f"corner {cid}: not characterizable (0..9)")
        if not out:
            out.append("No valid QUERY/COMMIT. Use QUERY corner=<id> x=<v> or COMMIT x=<v>.")
        if used >= BUDGET:
            out.append("Budget exhausted. COMMIT x=<value> now.")
        msgs.append({"role": "user", "content": "\n".join(out)})
    return None, used, probed, last[-160:]


if __name__ == "__main__":
    b_pass, b_sl, b_worst = grade(0.5)
    o_pass, o_sl, _ = grade(0.14)
    print(f"v0 baselines: naive x=0.5 -> {'PASS' if b_pass else 'FAIL'} ({b_sl:+.3f}, worst c{b_worst})"
          f" | optimum x=0.14 -> {'PASS' if o_pass else 'FAIL'} ({o_sl:+.3f})")
    print(f"REPS={REPS} per model on v0\n")

    specs = load_model_specs(Path("/data1/tongsb/eda-agentbench/configs/baseline_models.json"),
                             allow_mock=False)
    # rows for the mechanism correlation
    cells = defaultdict(list)  # name -> list of (x, used, n_probed, probed_coupling, pass)
    for name, prov, gk in specs:
        gk = {**gk, "max_tokens": 1500}
        for r in range(REPS):
            try:
                x, used, probed, nc = run_episode(prov, gk)
            except Exception as e:
                tag = "429" if "429" in str(e) else "ERR"
                print(f"  {name:16} rep{r}: {tag}")
                continue
            if x is None:
                print(f"  {name:16} rep{r}: NOCOMMIT used={used} probed={sorted(probed)} last={nc!r}")
                continue
            ok, sl, worst = grade(x)
            coup = bool(probed & COUPLING)
            cells[name].append((x, used, len(probed), coup, ok))
            print(f"  {name:16} rep{r}: x={x:.2f} {'PASS' if ok else 'FAIL'} "
                  f"slack={sl:+.3f} q={used} probed={sorted(probed)} coupling={'Y' if coup else 'n'}")

    print("\n=== Q1 stability (per-model on identical v0) ===")
    for name, rows in cells.items():
        if not rows:
            continue
        xs = [r[0] for r in rows]
        npass = sum(r[4] for r in rows)
        print(f"  {name:16} n={len(rows)} pass={npass}/{len(rows)} "
              f"x in [{min(xs):.2f},{max(xs):.2f}] mean={sum(xs)/len(xs):.2f}")

    print("\n=== Q2 mechanism: does PASS track probing a coupling corner? ===")
    cp = [r for rows in cells.values() for r in rows if r[3]]      # probed coupling
    ncp = [r for rows in cells.values() for r in rows if not r[3]]  # did not
    def rate(g):
        return f"{sum(r[4] for r in g)}/{len(g)}" if g else "0/0"
    print(f"  probed a coupling corner (7/8/9): pass {rate(cp)}")
    print(f"  did NOT probe coupling:           pass {rate(ncp)}")
