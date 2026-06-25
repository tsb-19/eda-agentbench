"""Sequential-equivalence Phase-0 frontier probe.

Two hand-authored tasks (FSM re-encoding; backward retiming). For each, the model sees ref.v + dut.v
+ the failing SYMPTOM (the compare point that differs) and must return, in a structured format:
  - the ROOT CAUSE (which transition / which mis-registered signal), and
  - a DISTINGUISHING INPUT sequence.
Grading is objective and split to separate temporal reasoning from endpoint echoing:
  core (0.6): did it identify the correct wrong transition / mis-registered signal?
  seq  (0.4): does its claimed distinguishing input ACTUALLY diverge when simulated through the
              authoritative oracle?  (echoing "the output differs" earns neither.)
Two scripted baselines run through the SAME grader:
  - symptom_lister: repeats the failing compare point, nothing else.
  - combinational: names the failing output's combinational fan-in cone as the cause (the strategy
    that aced combinational LEC) -- which is the ENDPOINT, not the temporal root cause.
GO if frontier models do NOT all reach ~1.0 AND the baselines score clearly lower.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, "/data1/tongsb/eda-agentbench")
sys.path.insert(0, str(Path(__file__).parent))
from scripts.generate_model_submissions import load_model_specs
from oracle import golden_fsm, impl_fsm, golden_pipe_stream, impl_pipe_stream

HERE = Path(__file__).parent
REPS = 2
SYS = "You are a senior RTL verification engineer. Reason carefully, then answer in the exact format requested."


def fsm_diverges(bits):
    gstep, gs = golden_fsm(); istep, isn = impl_fsm()
    for x in bits:
        gns, go = gstep(gs, x); ins, io = istep(isn, x)
        if go != io:
            return True
        gs, isn = gns, ins
    return False


def pipe_diverges(xs, ys):
    g = golden_pipe_stream(xs, ys); im = impl_pipe_stream(xs, ys)
    return any(a != b for a, b in zip(g, im))


# ---------------- Task 1 ----------------
def prompt_t1():
    ref = (HERE / "task1_fsm/ref_detector.v").read_text()
    dut = (HERE / "task1_fsm/dut_detector.v").read_text()
    return f"""`dut_detector` is claimed to be a one-hot RE-ENCODING of the reference FSM `ref_detector`
(same intended behavior, different state encoding). A sequential equivalence checker reports they are
NOT equivalent. The only observable failing point it reports is: output `det` differs on some input
sequence. The two encodings have no 1:1 state-register correspondence, so you must reason about the
state trajectory, not diff the text.

REFERENCE (binary, case table):
```verilog
{ref}
```
DESIGN UNDER TEST (one-hot, product-term next-state):
```verilog
{dut}
```
The DUT has exactly ONE wrong state transition. States mean matched-prefix of "1011":
S0="", S1="1", S2="10", S3="101". Identify it and prove inequivalence.

Answer in EXACTLY this format (no extra text after):
ROOT_CAUSE_STATE = <S0|S1|S2|S3>
ROOT_CAUSE_INPUT = <0|1>
DUT_GOES_TO = <S0|S1|S2|S3>
SHOULD_GO_TO = <S0|S1|S2|S3>
DISTINGUISHING_INPUT = <bit string, first bit = first cycle after reset>"""


def grade_t1(text):
    def field(name):
        m = re.search(rf"{name}\s*=\s*\**\s*([A-Za-z0-9]+)", text, re.I)
        return m.group(1).upper() if m else ""
    st, inp, should = field("ROOT_CAUSE_STATE"), field("ROOT_CAUSE_INPUT"), field("SHOULD_GO_TO")
    core = 1.0 if (st in ("S3", "3", "101") and inp in ("0",) and should in ("S2", "2", "10")) else 0.0
    m = re.search(r"DISTINGUISHING_INPUT\s*=\s*\**\s*([01\s,]+)", text, re.I)
    seq = 0.0
    bits_s = ""
    if m:
        bits = [int(c) for c in m.group(1) if c in "01"]
        bits_s = "".join(map(str, bits))
        seq = 1.0 if (bits and fsm_diverges(bits)) else 0.0
    return 0.6 * core + 0.4 * seq, f"core={core} seq={seq} st={st} in={inp} should={should} dseq={bits_s[:16]}"


# ---------------- Task 2 ----------------
def prompt_t2():
    ref = (HERE / "task2_retime/ref_pipe.v").read_text()
    dut = (HERE / "task2_retime/dut_pipe.v").read_text()
    return f"""`dut_pipe` is claimed to be a RETIMED version of `ref_pipe`: the reference's single output
register was pushed BACKWARD across the adder onto its inputs (reg(x+y) == reg(x)+reg(y)). A
sequential equivalence checker reports they are NOT equivalent; the only failing point is that output
`outp` differs on some input trace. The retiming was done incorrectly for exactly ONE input.

REFERENCE:
```verilog
{ref}
```
DESIGN UNDER TEST:
```verilog
{dut}
```
Identify which input signal was retimed incorrectly (its alignment register is missing, so it is one
cycle early), and give a concrete input trace that proves inequivalence.

Answer in EXACTLY this format (no extra text after):
ROOT_CAUSE_SIGNAL = <x|y>
WHY = <one short sentence>
DISTINGUISHING_X = <comma-separated bytes, cycle 0 first>
DISTINGUISHING_Y = <comma-separated bytes, cycle 0 first>"""


def grade_t2(text):
    m = re.search(r"ROOT_CAUSE_SIGNAL\s*=\s*\**\s*([xy])", text, re.I)
    sig = m.group(1).lower() if m else ""
    core = 1.0 if sig == "y" else 0.0

    def nums(name):
        mm = re.search(rf"{name}\s*=\s*\**\s*([0-9,\sxXbB]+)", text)
        if not mm:
            return []
        out = []
        for tok in mm.group(1).split(","):
            tok = tok.strip()
            if re.fullmatch(r"\d+", tok):
                out.append(int(tok) & 0xFF)
        return out
    xs, ys = nums("DISTINGUISHING_X"), nums("DISTINGUISHING_Y")
    seq = 0.0
    if xs and ys:
        n = min(len(xs), len(ys))
        seq = 1.0 if pipe_diverges(xs[:n], ys[:n]) else 0.0
    return 0.6 * core + 0.4 * seq, f"core={core} seq={seq} sig={sig} nx={len(xs)} ny={len(ys)}"


TASKS = [("T1_fsm_reencode", prompt_t1, grade_t1), ("T2_backward_retime", prompt_t2, grade_t2)]


def baseline_answers(task_id):
    if task_id == "T1_fsm_reencode":
        symptom = "Compare point `det` FAILED: the DUT output `det` differs from the reference on some input. The designs are not equivalent."
        comb = ("ROOT_CAUSE_STATE = S3\nROOT_CAUSE_INPUT = 1\nDUT_GOES_TO = S1\nSHOULD_GO_TO = S1\n"
                "DISTINGUISHING_INPUT = (the bug is in the `det = q[3] & din` output cone, which differs at the failing point)")
    else:
        symptom = "Compare point `outp` FAILED: the DUT output `outp` differs from the reference. The designs are not equivalent."
        comb = ("ROOT_CAUSE_SIGNAL = x\nWHY = the combinational fan-in cone of outp (rx + y) is where the mismatch is observed\n"
                "DISTINGUISHING_X = \nDISTINGUISHING_Y = ")
    return {"symptom_lister": symptom, "combinational": comb}


if __name__ == "__main__":
    print("=== scripted baselines (through the same grader) ===")
    for tid, _, grade in TASKS:
        for bname, ans in baseline_answers(tid).items():
            s, d = grade(ans)
            print(f"  {tid:18} {bname:14} score={s:.2f}  [{d}]")

    specs = load_model_specs(Path("/data1/tongsb/eda-agentbench/configs/baseline_models.json"),
                             allow_mock=False)
    print(f"\n=== frontier models (REPS={REPS}) ===")
    agg = {}
    for name, prov, gk in specs:
        gk = {**gk, "max_tokens": 2200}
        row = []
        for tid, pf, grade in TASKS:
            for r in range(REPS):
                try:
                    txt = prov.generate(pf(), system=SYS, **gk).text or ""
                except Exception as e:
                    row.append(f"{tid[:2]}r{r}:{'429' if '429' in str(e) else 'ERR'}")
                    continue
                s, d = grade(txt)
                row.append(f"{tid[:2]}r{r}={s:.2f}")
                agg.setdefault(name, []).append((tid, s))
                (HERE / f"tr_{name}_{tid}_r{r}.txt").write_text(txt)
        print(f"  {name:16} " + "  ".join(row))

    print("\n=== per-model mean by task (infra-filtered to real answers) ===")
    for name, rows in agg.items():
        t1 = [s for t, s in rows if t == "T1_fsm_reencode"]
        t2 = [s for t, s in rows if t == "T2_backward_retime"]
        m = lambda xs: f"{sum(xs)/len(xs):.2f}" if xs else "  - "
        print(f"  {name:16} T1={m(t1)} (n={len(t1)})  T2={m(t2)} (n={len(t2)})")
