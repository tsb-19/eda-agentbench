"""MCMM mechanism probe: act under a tool-QUERY BUDGET against a HIDDEN corner.

The one mechanism with a principled reason to resist frontier collapse (user pick, 2026-06-23):
the agent cannot DERIVE the answer from visible inputs (it must actively probe) and cannot
EXHAUSTIVELY probe (budget K < #corners), so it must prioritize under uncertainty. A hidden
holdout corner punishes lazy/incomplete exploration.

Toy: one knob x in [0,1]. Timing "cost" at corner c = A_c*(1-x) + B_c*x + C_c*4x(1-x), must be
<= P. The coupling term 4x(1-x) PEAKS at x=0.5 — so a "coupling corner" (high C) is worst exactly
where a lazy prober lands when balancing the obvious A/B-stress corners. Visible corners 0..9 are
mostly A/B-stress (low C) with two coupling corners (7,8) that a SMART prober can discover; the
hidden holdout adds the killer coupling corner H0 (C=1.0). Budget K=6 queries < 10 corners, so the
agent can't just sweep everything — it must probe strategically.

  lazy  (commit x=0.5): passes all visible, FAILS hidden H0  -> the trap
  smart (commit x~0.3): discovers coupling tightness, passes holdout

Run one episode per baseline model via the query loop; grade committed x on the FULL corner set.
This measures: does the budget+hidden-corner mechanism make the frontier fail (lazy commit), or
do they probe strategically and pass (mechanism also collapses)?
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, "/data1/tongsb/eda-agentbench")
from scripts.generate_model_submissions import load_model_specs

P = 1.8
BUDGET = 6
# corner id -> (A, B, C); visible/queryable are 0..9
VISIBLE = {
    0: (1.5, 0.6, 0.0), 1: (0.6, 1.5, 0.0), 2: (1.3, 0.8, 0.0), 3: (0.8, 1.3, 0.0),
    4: (1.1, 1.0, 0.0), 5: (1.0, 1.1, 0.0), 6: (1.2, 0.9, 0.0),
    7: (0.9, 0.9, 0.9), 8: (1.0, 0.8, 0.8), 9: (0.7, 0.7, 0.5),
}
HIDDEN = {100: (0.9, 0.9, 1.0), 101: (1.5, 0.7, 0.0), 102: (0.7, 1.5, 0.0)}
ALL = {**VISIBLE, **HIDDEN}


def cost(x, c):
    A, B, C = ALL[c]
    return A * (1 - x) + B * x + C * 4 * x * (1 - x)


def slack(x, c):
    return P - cost(x, c)


def grade(x):
    sl = {c: slack(x, c) for c in ALL}
    worst = min(sl, key=sl.get)
    return {"x": x, "min_slack": round(sl[worst], 3), "worst_corner": worst,
            "pass": sl[worst] >= 0,
            "fails": [c for c in ALL if sl[c] < 0]}


INTRO = f"""\
You are closing timing on a chip by choosing ONE knob x in [0.0, 1.0]. The timing slack at a
process corner depends on x and on hidden per-corner factors you cannot see directly. There are 10
characterizable corners with ids 0..9, PLUS additional hidden corners used only for final signoff.
A corner FAILS if its slack < 0; your x must make EVERY corner (including hidden ones) pass.

You have a BUDGET of {BUDGET} slack queries. To query, write lines exactly like:
  QUERY corner=<id> x=<value>
(each returns the slack at that corner for that x; each line costs 1 query). You may spread queries
over several messages. When ready, output exactly:
  COMMIT x=<value>
Your committed x is graded on ALL corners including hidden ones. Spend queries wisely — you cannot
query every corner at every x. Begin."""

QPAT = re.compile(r"QUERY\s+corner\s*=\s*(\d+)\s+x\s*=\s*([0-9]*\.?[0-9]+)", re.I)
CPAT = re.compile(r"COMMIT\s+x\s*=\s*([0-9]*\.?[0-9]+)", re.I)


def run_episode(provider, gk):
    msgs = [{"role": "system", "content": "You are a senior STA/signoff engineer. Be terse."},
            {"role": "user", "content": INTRO}]
    used = 0
    transcript = []
    for _ in range(8):
        resp = provider.chat(msgs, **gk).text or ""
        transcript.append(resp)
        msgs.append({"role": "assistant", "content": resp})
        cm = CPAT.search(resp)
        if cm:
            return float(cm.group(1)), used, transcript
        out = []
        for cid, xv in QPAT.findall(resp):
            if used >= BUDGET:
                out.append(f"corner {cid} x={xv}: BUDGET EXCEEDED")
                continue
            used += 1
            cidn = int(cid)
            if cidn in VISIBLE:
                out.append(f"corner {cid} x={xv}: slack={slack(float(xv), cidn):.3f}")
            else:
                out.append(f"corner {cid}: not characterizable (id must be 0..9)")
        if not out:
            out.append("No valid QUERY or COMMIT found. Use 'QUERY corner=<id> x=<v>' or "
                       "'COMMIT x=<v>'.")
        if used >= BUDGET:
            out.append("Budget exhausted. Output COMMIT x=<value> now.")
        msgs.append({"role": "user", "content": "\n".join(out)})
    return None, used, transcript


if __name__ == "__main__":
    print("baselines:")
    for label, x in [("lazy x=0.5", 0.5), ("smart x=0.30", 0.30), ("smart x=0.70", 0.70),
                     ("over x=0.08", 0.08)]:
        g = grade(x)
        print(f"  {label:14} min_slack={g['min_slack']:+.3f} worst=corner{g['worst_corner']} "
              f"{'PASS' if g['pass'] else 'FAIL fails=' + str(g['fails'])}")

    specs = load_model_specs(Path("/data1/tongsb/eda-agentbench/configs/baseline_models.json"),
                             allow_mock=False)
    print("\nmodels:")
    for name, prov, gk in specs:
        gk = {**gk, "max_tokens": 1500}
        try:
            x, used, tr = run_episode(prov, gk)
            if x is None:
                print(f"  {name:16} NO-COMMIT (queries={used})")
                continue
            g = grade(x)
            print(f"  {name:16} commit x={x:.3f} queries={used} min_slack={g['min_slack']:+.3f} "
                  f"worst=corner{g['worst_corner']} {'PASS' if g['pass'] else 'FAIL ' + str(g['fails'])}")
            Path(f"/data1/tongsb/eda-agentbench/experiments/mcmm_probe/tr_{name}.txt").write_text(
                "\n\n----\n\n".join(tr))
        except Exception as e:
            print(f"  {name:16} ERROR {type(e).__name__}: {str(e)[:70]}")
