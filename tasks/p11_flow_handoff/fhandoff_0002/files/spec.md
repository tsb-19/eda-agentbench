# acc_stage — Handoff Sign-off Package (authoritative spec)

This is a downstream **timing sign-off handoff** for the `acc_stage` block. Your job is to make the
constraints bind the **intended clock** so the sign-off flow actually constrains the design's
sequential paths, then confirm sign-off passes. This document is the **authority**; if an artifact
disagrees with it, the spec wins.

## Current design intent

After a recent clock-domain restructuring, `acc_stage`'s clock port is named **`clk_main`**. The
gate-level netlist (`design_netlist.v`) clocks every flip-flop (`cap_reg`, `acc_reg`, `en_reg`)
from this port. The behavioural `design.v` is the reference.

The constraints **must create the clock on the real port `clk_main`** and constrain the
sequential paths from/to it. An SDC that names a **stale** clock (one that no longer exists on the
netlist) creates no clock object: the flip-flops are left unclocked, every timing path goes
**unconstrained**, and PrimeTime then reports **no violations — because it checked nothing**. A
clean report obtained that way is meaningless.

## Handoff scenario

- Scenario: **func** (functional sign-off).
- Corner / library: **typ** (`tiny.db`).
- Clock: **clk_main**, period **3.0 ns**, uncertainty **0.15 ns**.
- The downstream flow consumes `design_netlist.v` and `constraints.sdc` per `handoff_manifest.json`.

## The sign-off requirement

The handoff is correct only when:

1. the constraints bind the clock to the design's real clock port (`clk_main`),
2. the intended sequential endpoints (`cap_reg`, `acc_reg`, `en_reg`, and the `dout` output path)
   are **actually constrained** (a non-empty, meaningful timing graph), and
3. PrimeTime setup sign-off reports **no negative-slack paths**.

A green PrimeTime report alone is **not** sufficient: if the clock name is stale, PT prints a clean
report while constraining **zero** intended paths. Do **not** "fix" this by weakening timing,
deleting checks, renaming the netlist/design to match the stale SDC, editing forbidden netlist/lib
artifacts, or faking a report. The only correct repair is to **bind the clock to the intended port
name** so the intended paths are constrained.
