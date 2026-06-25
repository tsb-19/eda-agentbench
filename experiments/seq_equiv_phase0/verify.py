"""Cross-check that the Verilog artifacts (what the LLM sees) reproduce the Python oracle exactly.
For each task: feed the SAME stimulus to the Python model and to iverilog-compiled ref+dut, and
assert the first-divergence cycle matches. If they match, the graded ground truth == the shown
artifact. Uses a fixed PRNG seed (no Date/random nondeterminism)."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from oracle import golden_fsm, impl_fsm, golden_pipe_stream, impl_pipe_stream

HERE = Path(__file__).parent


class LCG:  # deterministic, dependency-free
    def __init__(self, seed): self.s = seed
    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s


def py_firstdiv_fsm(bits):
    gstep, gs = golden_fsm()
    istep, isn = impl_fsm()
    for i, x in enumerate(bits):
        gns, go = gstep(gs, x)
        ins, io = istep(isn, x)
        if go != io:
            return i
        gs, isn = gns, ins
    return -1


def run_iverilog(srcs, tb, mem_name, mem_lines, n, divtag="DIVERGE i="):
    wd = HERE / srcs[0]
    (wd / mem_name).write_text("\n".join(mem_lines) + "\n")
    vvp = wd / "sim.vvp"
    subprocess.run(["iverilog", "-o", str(vvp), *[str(wd / s) for s in srcs[1:]]],
                   check=True, capture_output=True, text=True)
    out = subprocess.run(["vvp", str(vvp), f"+N={n}"], cwd=wd, check=True,
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("DIVERGE i="):
            return int(line.split("i=")[1].split()[0]), out.strip()
    return -1, out.strip()


def main():
    ok = True

    # ---- TASK 1 ----
    print("=== TASK 1 (FSM re-encoding) cross-check ===")
    directed = [1, 0, 1, 0, 1, 1]                      # oracle shortest distinguishing seq
    rng = LCG(20260624)
    rand = [rng.next() & 1 for _ in range(120)]
    for tag, bits in [("directed-101011", directed), ("random-120", rand)]:
        py = py_firstdiv_fsm(bits)
        hw, raw = run_iverilog(["task1_fsm", "ref_detector.v", "dut_detector.v", "tb.v"],
                               "tb.v", "stim1.mem", [str(b) for b in bits], len(bits))
        match = (py == hw)
        ok &= match
        print(f"  {tag:16} python_firstdiv={py:3d}  iverilog_firstdiv={hw:3d}  "
              f"{'MATCH' if match else 'MISMATCH'}  [{raw}]")

    # ---- TASK 2 ----
    print("=== TASK 2 (backward retiming) cross-check ===")
    rng = LCG(777)
    xs = [(rng.next() % 256) for _ in range(40)]
    ys = [0] + [(rng.next() % 256) for _ in range(39)]   # y[0]=0 to isolate first real divergence
    g = golden_pipe_stream(xs, ys)
    im = impl_pipe_stream(xs, ys)
    py = next((n for n in range(len(g)) if g[n] != im[n]), -1)
    mem = [f"{x:02x}{y:02x}" for x, y in zip(xs, ys)]
    hw, raw = run_iverilog(["task2_retime", "ref_pipe.v", "dut_pipe.v", "tb.v"],
                           "tb.v", "stim2.mem", mem, len(xs))
    match = (py == hw)
    ok &= match
    print(f"  random-40        python_firstdiv={py:3d}  iverilog_firstdiv={hw:3d}  "
          f"{'MATCH' if match else 'MISMATCH'}  [{raw}]")

    print("\n", "ALL CROSS-CHECKS PASS" if ok else "*** CROSS-CHECK FAILED ***")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
