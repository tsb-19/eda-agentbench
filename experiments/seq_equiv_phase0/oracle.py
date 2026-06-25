"""Authoritative ground-truth oracle for the sequential-equivalence Phase-0 probe.

Two hand-authored tasks. For each: a Python cycle-accurate model of golden and of the buggy impl
(faithful to the .v artifacts the model will see), plus a BFS that finds the SHORTEST input sequence
that makes them diverge. The shortest distinguishing sequence + the root-cause transition/path are
the oracle. The Verilog tb (run via iverilog) cross-checks that golden.v/impl.v reproduce these
exact Python models, so the artifact the LLM sees == the artifact we graded against.

TASK 1 -- FSM re-encoding. Golden: binary-encoded Mealy "1011" overlapping detector (case stmt).
Impl: one-hot, next-state written as boolean product-term equations (NO case table to diff), with
ONE bug: the S3,in=0 transition goes to S0 instead of S2 -> the "10" overlap context is lost, so a
detection is missed several cycles later. Endpoint (output `det` differs) does NOT reveal which
transition is wrong; you must trace the trajectory.

TASK 2 -- backward retiming across an adder. Golden: out = reg(x + y)  (register AFTER the adder).
Impl: register pushed back across the adder onto the inputs -- reg(x)+reg(y) -- BUT one input (y)
was left un-registered: out = reg(x) + y. y is now one cycle early. Endpoint (out differs) does not
say which input lost its retiming register.
"""
from collections import deque


# ---------------- TASK 1: FSM ----------------
# states S0..S3 = matched-prefix of "1011": "", "1", "10", "101"
def golden_fsm():
    # returns (step, init_state); step(state, in_bit) -> (next_state, out_bit)
    def step(s, x):
        if s == 0:   return (1, 0) if x else (0, 0)
        if s == 1:   return (1, 0) if x else (2, 0)
        if s == 2:   return (3, 0) if x else (0, 0)
        if s == 3:   return (1, 1) if x else (2, 0)   # S3,in0 -> S2  (keep "10")
    return step, 0


def impl_fsm():
    # one-hot bug: S3,in0 -> S0 (should be S2)
    def step(s, x):
        if s == 0:   return (1, 0) if x else (0, 0)
        if s == 1:   return (1, 0) if x else (2, 0)
        if s == 2:   return (3, 0) if x else (0, 0)
        if s == 3:   return (1, 1) if x else (0, 0)   # BUG: -> S0 (loses "10" context)
    return step, 0


# ---------------- TASK 2: retiming ----------------
# golden: out[n] = x[n-1] + y[n-1]   (one register after adder)
# impl:   out[n] = x[n-1] + y[n]     (y not registered -> one cycle early)
def golden_pipe_stream(xs, ys):
    out, rx, ry = [], 0, 0
    for x, y in zip(xs, ys):
        out.append((rx + ry) & 0xFF)   # value registered from previous cycle's x+y
        rx, ry = x, y
    return out


def impl_pipe_stream(xs, ys):
    out, rx = [], 0
    for x, y in zip(xs, ys):
        out.append((rx + y) & 0xFF)    # BUG: current y, only x registered
        rx = x
    return out


def bfs_distinguish(g, i, max_len=20):
    gstep, gs0 = g
    istep, is0 = i
    # state = (golden_state, impl_state); BFS over input bits; record first output divergence
    start = (gs0, is0)
    q = deque([(start, [])])
    seen = {start}
    while q:
        (gsS, isS), seq = q.popleft()
        if len(seq) > max_len:
            return None
        for x in (0, 1):
            gns, go = gstep(gsS, x)
            ins, io = istep(isS, x)
            nseq = seq + [x]
            if go != io:
                return nseq, go, io        # diverging output at this step
            st = (gns, ins)
            if st not in seen:
                seen.add(st)
                q.append((st, nseq))
    return None


if __name__ == "__main__":
    print("=== TASK 1 (FSM re-encoding) ===")
    res = bfs_distinguish(golden_fsm(), impl_fsm())
    if res:
        seq, go, io = res
        print(f"  shortest distinguishing input = {''.join(map(str, seq))} (len {len(seq)})")
        print(f"  at final bit: golden det={go}, impl det={io}")
        # trace golden state trajectory to show where S3,in0 is exercised
        s, traj = 0, []
        for x in seq:
            traj.append(s); s, _ = golden_fsm()[0](s, x)
        print(f"  golden state trajectory (pre-step): {traj}")
    print("  ORACLE root cause: impl transition S3 (matched '101'), input=0 -> goes to S0;")
    print("                     golden goes to S2 (keep '10'). impl loses overlap context.")

    print("\n=== TASK 2 (backward retiming across adder) ===")
    xs = [3, 3, 3, 3, 3]
    ys = [0, 5, 5, 5, 5]   # y changes at cycle1 -> exposes misalignment
    g = golden_pipe_stream(xs, ys)
    im = impl_pipe_stream(xs, ys)
    print(f"  xs={xs}\n  ys={ys}")
    print(f"  golden out={g}")
    print(f"  impl   out={im}")
    div = next((n for n in range(len(g)) if g[n] != im[n]), None)
    print(f"  first diverging cycle = {div} (golden {g[div]} vs impl {im[div]})" if div is not None
          else "  NO divergence (bad task!)")
    print("  ORACLE root cause: y input not registered after backward retiming (out = reg(x)+y);")
    print("                     y is one cycle early. Fix: register y too -> out = reg(x)+reg(y).")
