# acc_stage — Timing Sign-off Contract (authoritative spec)

`acc_stage` is a registered datapath stage on a single clock `clk`. This document is the
**authority** for its timing constraints. The constraint file `constraints.sdc` must encode
exactly this contract; if the two disagree, the spec wins.

## Clock

- Target clock period **T = 4.0 ns**.
- Clock uncertainty to apply at sign-off (jitter + skew margin): **0.05 ns**.

## Interface budget (derive the SDC I/O delays from these facts)

The SDC input/output delays are **not** stated directly — compute them from the neighbouring
blocks' budgets. This is ordinary budget arithmetic, not a number to copy.

**Upstream source block** (drives `din` and `en`):
- launch flip-flop clock-to-Q (t_co): **1.3 ns**
- board / interconnect flight into `acc_stage`: **0.4 ns**
- ⇒ the external delay seen at our inputs `din`, `en` = t_co + flight.

**Downstream sink block** (captures `dout`):
- capture flip-flop setup requirement (t_su): **0.5 ns**
- board / interconnect flight out of `acc_stage`: **0.3 ns**
- ⇒ the external delay the sink needs before its capture edge = t_su + flight.

## Sign-off requirement

With the constraints encoding the budget above, PrimeTime setup sign-off must report **no
negative-slack paths**.

Over-constraining is **not** a valid fix. Tightening the period, inflating the uncertainty,
zeroing a delay, or padding a delay beyond its budget can make a violation disappear without
making the constraints correct. The constraints must **match the interface budget**, not
merely silence the symptom.
