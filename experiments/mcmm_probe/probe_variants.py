"""MCMM budget+hidden-corner probe — MULTI-VARIANT confirmation.

n=1 showed Qwen/DeepSeek (flawless all session) fail the budget+hidden-corner trap by
under-exploring, while GLM/MiniMax passed. This runs several independent variants to test whether
that spread is STABLE (real discrimination) or noise. Each variant: symmetric A/B (so the naive
balance point is x=0.5) + a coupling term 4x(1-x) that is WORST at x=0.5 + a hidden coupling corner
-> committing the obvious balance x=0.5 fails the holdout; broad probing / off-center commit passes.

The script AUTO-VALIDATES each variant by grid search before trusting it:
  robust_x  = argmax_x min_slack over ALL corners      (must clear >= +0.04)
  lazy_x    = argmax_x min_slack over VISIBLE only      (the overfit optimum)
  a variant is a valid discriminator iff lazy_x FAILS the hidden holdout.
Then runs each model through the query loop and grades the committed x on ALL corners.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, "/data1/tongsb/eda-agentbench")
from scripts.generate_model_submissions import load_model_specs

BUDGET = 6

VARIANTS = [
    {"P": 1.8, "VIS": {0:(1.5,0.6,0.0),1:(0.6,1.5,0.0),2:(1.3,0.8,0.0),3:(0.8,1.3,0.0),
                       4:(1.1,1.0,0.0),5:(1.0,1.1,0.0),6:(1.2,0.9,0.0),
                       7:(0.9,0.9,0.9),8:(1.0,0.8,0.8),9:(0.7,0.7,0.5)},
     "HID": {100:(0.9,0.9,1.0),101:(1.5,0.7,0.0),102:(0.7,1.5,0.0)}},
    {"P": 1.7, "VIS": {0:(1.4,0.6,0.0),1:(0.6,1.4,0.0),2:(1.2,0.7,0.0),3:(0.7,1.2,0.0),
                       4:(1.0,1.0,0.15),5:(0.9,0.9,0.55),6:(1.1,0.8,0.0),
                       7:(0.85,0.85,0.8),8:(0.95,0.8,0.65),9:(0.8,0.95,0.45)},
     "HID": {100:(0.9,0.9,0.95),101:(1.4,0.6,0.0),102:(0.6,1.4,0.0)}},
    {"P": 2.0, "VIS": {0:(1.6,0.7,0.0),1:(0.7,1.6,0.0),2:(1.3,0.9,0.0),3:(0.9,1.3,0.0),
                       4:(1.1,1.1,0.2),5:(1.0,1.0,0.75),6:(1.2,1.0,0.0),
                       7:(1.0,1.0,1.0),8:(1.05,0.95,0.85),9:(0.95,1.05,0.6)},
     "HID": {100:(1.0,1.0,1.2),101:(1.6,0.7,0.0),102:(0.7,1.6,0.0)}},
]


def cost(x, abc):
    A, B, C = abc
    return A * (1 - x) + B * x + C * 4 * x * (1 - x)


def min_slack(x, P, corners):
    return min(P - cost(x, abc) for abc in corners.values())


def best_x(P, corners):  # grid search argmax min-slack
    bx, bs = 0.0, -9.9
    for i in range(1001):
        x = i / 1000.0
        s = min_slack(x, P, corners)
        if s > bs:
            bs, bx = s, x
    return bx, round(bs, 3)


def grade(x, V):
    allc = {**V["VIS"], **V["HID"]}
    sl = {c: V["P"] - cost(x, allc[c]) for c in allc}
    worst = min(sl, key=sl.get)
    return {"min_slack": round(sl[worst], 3), "worst": worst, "pass": sl[worst] >= 0}


def validate(V):
    rx, rs = best_x(V["P"], {**V["VIS"], **V["HID"]})
    naive = grade(0.5, V)   # the textbook "balance the two stress axes" answer = the trap
    return {"robust_x": rx, "robust_slack": rs,
            "naive_hidden_pass": naive["pass"], "naive_slack": naive["min_slack"],
            "valid": (rs >= 0.04 and not naive["pass"])}


INTRO = """\
You are closing timing by choosing ONE knob x in [0.0, 1.0]. Slack at a corner depends on x and on
hidden per-corner factors. 10 corners have ids 0..9; additional HIDDEN corners are used only for
final signoff. A corner FAILS if slack < 0; your x must make EVERY corner (including hidden) pass.
You have a BUDGET of {B} slack queries. Query with lines exactly like:
  QUERY corner=<id> x=<value>
When ready: COMMIT x=<value>. Graded on ALL corners incl. hidden. Spend queries wisely. Begin."""
QPAT = re.compile(r"QUERY\s+corner\s*=\s*(\d+)\s+x\s*=\s*([0-9]*\.?[0-9]+)", re.I)
CPAT = re.compile(r"COMMIT\s+x\s*=\s*([0-9]*\.?[0-9]+)", re.I)


def run_episode(provider, gk, V):
    msgs = [{"role": "system", "content": "You are a senior STA/signoff engineer. Be terse."},
            {"role": "user", "content": INTRO.format(B=BUDGET)}]
    used = 0
    for _ in range(8):
        resp = provider.chat(msgs, **gk).text or ""
        msgs.append({"role": "assistant", "content": resp})
        cm = CPAT.search(resp)
        if cm:
            return float(cm.group(1)), used
        out = []
        for cid, xv in QPAT.findall(resp):
            if used >= BUDGET:
                out.append(f"corner {cid} x={xv}: BUDGET EXCEEDED"); continue
            used += 1
            cidn = int(cid)
            out.append(f"corner {cid} x={xv}: slack={V['P']-cost(float(xv), V['VIS'][cidn]):.3f}"
                       if cidn in V["VIS"] else f"corner {cid}: not characterizable (0..9)")
        if not out:
            out.append("No valid QUERY/COMMIT. Use QUERY corner=<id> x=<v> or COMMIT x=<v>.")
        if used >= BUDGET:
            out.append("Budget exhausted. COMMIT x=<value> now.")
        msgs.append({"role": "user", "content": "\n".join(out)})
    return None, used


if __name__ == "__main__":
    valid_variants = []
    print("=== variant baseline validation ===")
    for i, V in enumerate(VARIANTS):
        info = validate(V)
        print(f"  v{i}: robust_x={info['robust_x']:.2f} (slack {info['robust_slack']:+.3f})  "
              f"naive x=0.5 -> hidden {'PASS' if info['naive_hidden_pass'] else 'FAIL'} "
              f"({info['naive_slack']:+.3f})  valid={info['valid']}")
        if info["valid"]:
            valid_variants.append(i)

    specs = load_model_specs(Path("/data1/tongsb/eda-agentbench/configs/baseline_models.json"),
                             allow_mock=False)
    print(f"\n=== model x variant (committed x / pass) over {len(valid_variants)} valid variants ===")
    tally = {}
    for name, prov, gk in specs:
        gk = {**gk, "max_tokens": 1500}
        cells = []
        for i in valid_variants:
            try:
                x, used = run_episode(prov, gk, VARIANTS[i])
                if x is None:
                    cells.append("nocommit"); continue
                g = grade(x, VARIANTS[i])
                cells.append(f"{x:.2f}{'P' if g['pass'] else 'F'}")
                tally.setdefault(name, [0, 0])
                tally[name][0 if g["pass"] else 1] += 1
            except Exception as e:
                cells.append("429" if "429" in str(e) else "ERR")
        print(f"  {name:16} " + "  ".join(c.rjust(8) for c in cells))
    print("\n=== pass/fail tally (infra-filtered) ===")
    for name, (p, f) in tally.items():
        print(f"  {name:16} pass={p} fail={f}")
