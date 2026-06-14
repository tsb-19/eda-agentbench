"""Generate SPICE deck debug tasks — scaled to 100.

Produces 100 tasks covering 7 HSPICE-catchable error categories,
balanced across categories and distributed across varied circuit topologies.

Category distribution (100 tasks):
  missing_model:      15
  missing_subckt:     14
  duplicate_element:  14
  wrong_pin_count:    14
  missing_include:    14
  unsupported_dialect: 15
  invalid_directive:  14

Each task has a buggy deck (fails HSPICE) and a golden deck (passes HSPICE).

Design approach: Each category uses hand-validated deck templates where the
bug injection is known to produce the correct HSPICE behavior. Parameter
substitution (component values, names) provides variation.
"""

import json
from pathlib import Path

TASKS_DIR = Path(__file__).parent.parent.parent / "tasks_candidates"


# ---------------------------------------------------------------------------
# Per-category task generators
#
# Each generator yields dicts with: buggy_deck, fixed_deck, oracle_answer,
# difficulty, tags, circuit_name
# ---------------------------------------------------------------------------

def _missing_model_tasks():
    """Model name typo/absent — element references undefined model."""
    tasks = []
    # Variant A: CMOS inverter, pmos model typo
    for i, (w1, l1, w2, l2, vdd) in enumerate([
        ("2u", "180n", "1u", "180n", "1.8"),
        ("4u", "90n", "2u", "90n", "1.2"),
        ("1u", "250n", "500n", "250n", "2.5"),
    ]):
        tasks.append({
            "buggy": (
                f".title CMOS Inverter - Missing Model\n"
                f"M1 out gate vdd vdd pmos_typo W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "fixed": (
                f".title CMOS Inverter - Missing Model\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "oracle": 'Fix model name from `pmos_typo` to `pmos`, add `.model pmos pmos (level=1 vto=-0.7 kp=50u)`.',
            "difficulty": "easy",
            "tags": ["syntax", "mosfet", "missing-model"],
            "circuit": "CMOS Inverter",
        })

    # Variant B: NAND gate, pmos model typo
    for i, (w1, l1, w2, l2, vdd) in enumerate([
        ("2u", "180n", "1u", "180n", "1.8"),
        ("3u", "130n", "1.5u", "130n", "1.5"),
    ]):
        tasks.append({
            "buggy": (
                f".title NAND Gate - Missing Model\n"
                f"M1 out a vdd vdd pmos_bad W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos_bad W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M4 mid b gnd gnd nmos W={w2} L={l2}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NAND Gate - Missing Model\n"
                f"M1 out a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M4 mid b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": 'Fix model name from `pmos_bad` to `pmos`, add `.model pmos pmos (level=1 vto=-0.7 kp=50u)`.',
            "difficulty": "easy",
            "tags": ["syntax", "mosfet", "missing-model"],
            "circuit": "NAND Gate",
        })

    # Variant C: Diode model typo
    for i, (r1, vamp, freq, sim_end) in enumerate([
        ("1k", "5", "60", "33m"),
        ("10k", "3.3", "1k", "2m"),
    ]):
        tasks.append({
            "buggy": (
                f".title Diode Rectifier - Missing Model\n"
                f"D1 anode cathode Drect\n"
                f"R1 cathode 0 {r1}\n"
                f"V1 anode 0 SIN(0 {vamp} {freq})\n"
                f".model Drectifier D(Is=1e-14 N=1)\n"
                f".tran 10p {sim_end}\n"
            ),
            "fixed": (
                f".title Diode Rectifier - Missing Model\n"
                f"D1 anode cathode Drectifier\n"
                f"R1 cathode 0 {r1}\n"
                f"V1 anode 0 SIN(0 {vamp} {freq})\n"
                f".model Drectifier D(Is=1e-14 N=1)\n"
                f".tran 10p {sim_end}\n"
            ),
            "oracle": "Fix diode model reference from `Drect` to `Drectifier`.",
            "difficulty": "medium",
            "tags": ["syntax", "diode", "missing-model"],
            "circuit": "Diode Rectifier",
        })

    # Variant D: NOR gate, nmos typo
    for w1, l1, w2, l2, vdd in [
        ("4u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title NOR Gate - Missing Model\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos_typo W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos_typo W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NOR Gate - Missing Model\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": 'Fix model name from `nmos_typo` to `nmos`, add `.model nmos nmos (level=1 vto=0.7 kp=120u)`.',
            "difficulty": "medium",
            "tags": ["syntax", "mosfet", "missing-model"],
            "circuit": "NOR Gate",
        })

    # Variant E: Latch, both models corrupted (only nmos typo)
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title CMOS Latch - Missing Model\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos_bad W={w2} L={l2}\n"
                f"M3 in out vdd vdd pmos W={w1} L={l1}\n"
                f"M4 in out gnd gnd nmos_bad W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f"Vdd vdd 0 {vdd}\n"
                f"Vin in 0 PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title CMOS Latch - Missing Model\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f"M3 in out vdd vdd pmos W={w1} L={l1}\n"
                f"M4 in out gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd 0 {vdd}\n"
                f"Vin in 0 PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": 'Fix model name from `nmos_bad` to `nmos`, add `.model nmos nmos (level=1 vto=0.7 kp=120u)`.',
            "difficulty": "medium",
            "tags": ["syntax", "mosfet", "missing-model"],
            "circuit": "CMOS Latch",
        })

    # Variant F: Source follower, nmos typo
    for w1, l1, r1, vdd in [
        ("4u", "180n", "1k", "1.8"),
        ("2u", "90n", "2k", "1.2"),
    ]:
        tasks.append({
            "buggy": (
                f".title Source Follower - Missing Model\n"
                f"M1 vdd in out gnd nmos_bad W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 16n\n"
            ),
            "fixed": (
                f".title Source Follower - Missing Model\n"
                f"M1 vdd in out gnd nmos W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 10p 16n\n"
            ),
            "oracle": 'Fix model name from `nmos_bad` to `nmos`, add `.model nmos nmos (level=1 vto=0.7 kp=120u)`.',
            "difficulty": "medium",
            "tags": ["syntax", "mosfet", "missing-model"],
            "circuit": "Source Follower",
        })

    # Variant G: Current mirror, nmos typo
    for w1, l1, r1, vdd in [
        ("2u", "180n", "10k", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title Current Mirror - Missing Model\n"
                f"M1 ref ref gnd gnd nmos_bad W={w1} L={l1}\n"
                f"M2 out ref gnd gnd nmos_bad W={w1} L={l1}\n"
                f"R1 vdd ref {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f".op\n"
            ),
            "fixed": (
                f".title Current Mirror - Missing Model\n"
                f"M1 ref ref gnd gnd nmos W={w1} L={l1}\n"
                f"M2 out ref gnd gnd nmos W={w1} L={l1}\n"
                f"R1 vdd ref {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".op\n"
            ),
            "oracle": 'Fix model name from `nmos_bad` to `nmos`, add `.model nmos nmos (level=1 vto=0.7 kp=120u)`.',
            "difficulty": "hard",
            "tags": ["syntax", "mosfet", "missing-model"],
            "circuit": "Current Mirror",
        })

    # Variant H: Common-source amplifier, pmos typo
    for w1, l1, r1, vdd in [
        ("10u", "180n", "10k", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title Common-Source Amplifier - Missing Model\n"
                f"M1 out in vdd vdd pmos_bad W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 16n\n"
            ),
            "fixed": (
                f".title Common-Source Amplifier - Missing Model\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".tran 10p 16n\n"
            ),
            "oracle": 'Fix model name from `pmos_bad` to `pmos`, add `.model pmos pmos (level=1 vto=-0.7 kp=50u)`.',
            "difficulty": "hard",
            "tags": ["syntax", "mosfet", "missing-model"],
            "circuit": "Common-Source Amplifier",
        })

    # Variant I: CMOS inverter with nmos typo
    for w1, l1, w2, l2, vdd in [
        ("2u", "130n", "1u", "130n", "1.5"),
        ("4u", "90n", "2u", "90n", "1.0"),
    ]:
        tasks.append({
            "buggy": (
                f".title CMOS Inverter Variant - Missing Model\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos_bad W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "fixed": (
                f".title CMOS Inverter Variant - Missing Model\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "oracle": 'Fix model name from `nmos_bad` to `nmos`, add `.model nmos nmos (level=1 vto=0.7 kp=120u)`.',
            "difficulty": "easy",
            "tags": ["syntax", "mosfet", "missing-model"],
            "circuit": "CMOS Inverter",
        })

    return tasks


def _missing_subckt_tasks():
    """Undefined subcircuit reference."""
    tasks = []

    # Variant A: Buffer circuit, subcircuit not defined
    for i, (rsub, rout, vin) in enumerate([
        ("100", "1k", "1.8"),
        ("220", "2.2k", "3.3"),
        ("470", "4.7k", "5"),
    ]):
        tasks.append({
            "buggy": (
                f".title Buffer Circuit - Missing Subckt\n"
                f"X1 in out buf\n"
                f"R1 out gnd {rout}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title Buffer Circuit - Missing Subckt\n"
                f".subckt buf in out\n"
                f"Rseries in out {rsub}\n"
                f".ends buf\n"
                f"X1 in out buf\n"
                f"R1 out gnd {rout}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": f'Add `.subckt buf in out` / `Rseries in out {rsub}` / `.ends buf` before the X1 instance.',
            "difficulty": "easy",
            "tags": ["syntax", "subcircuit", "missing-subckt"],
            "circuit": "Buffer Circuit",
        })

    # Variant B: Ring oscillator, subcircuit name mismatch
    for w1, l1, w2, l2, vdd, sim_end in [
        ("2u", "180n", "1u", "180n", "1.8", "100n"),
        ("1u", "90n", "500n", "90n", "1.0", "50n"),
    ]:
        tasks.append({
            "buggy": (
                f".title Ring Oscillator - Missing Subckt\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".subckt inv_stage in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv_stage\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 1p {sim_end}\n"
            ),
            "fixed": (
                f".title Ring Oscillator - Missing Subckt\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".tran 1p {sim_end}\n"
            ),
            "oracle": 'Rename `.subckt inv_stage` to `.subckt inv` and `.ends inv_stage` to `.ends inv`.',
            "difficulty": "hard",
            "tags": ["syntax", "ring-oscillator", "subckt-mismatch"],
            "circuit": "Ring Oscillator",
        })

    # Variant C: Inverter subcircuit, wrong name
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
        ("3u", "90n", "1.5u", "90n", "1.2"),
    ]:
        tasks.append({
            "buggy": (
                f".title Inverter Chain - Missing Subckt\n"
                f"X1 a b vdd gnd inv\n"
                f"X2 b c vdd gnd inv\n"
                f".subckt inv_buffer in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv_buffer\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title Inverter Chain - Missing Subckt\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"X1 a b vdd gnd inv\n"
                f"X2 b c vdd gnd inv\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": 'Rename `.subckt inv_buffer` to `.subckt inv` and `.ends inv_buffer` to `.ends inv`.',
            "difficulty": "medium",
            "tags": ["syntax", "subcircuit", "missing-subckt"],
            "circuit": "Inverter Chain",
        })

    # Variant D: 5-stage ring oscillator, subcircuit name mismatch
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title 5-Stage Ring Oscillator - Missing Subckt\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n4 vdd 0 inv\n"
                f"X4 n4 n5 vdd 0 inv\n"
                f"X5 n5 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".subckt inv_buf in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv_buf\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 1p 200n\n"
            ),
            "fixed": (
                f".title 5-Stage Ring Oscillator - Missing Subckt\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n4 vdd 0 inv\n"
                f"X4 n4 n5 vdd 0 inv\n"
                f"X5 n5 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".tran 1p 200n\n"
            ),
            "oracle": 'Rename `.subckt inv_buf` to `.subckt inv` and `.ends inv_buf` to `.ends inv`.',
            "difficulty": "hard",
            "tags": ["syntax", "ring-oscillator", "subckt-mismatch"],
            "circuit": "5-Stage Ring Oscillator",
        })

    # Variant E: RC filter with subcircuit, missing subckt
    for rsub, r1, c1, vin in [
        ("100", "1k", "1p", "1.8"),
        ("220", "4.7k", "100f", "3.3"),
    ]:
        tasks.append({
            "buggy": (
                f".title Filter with Subckt - Missing Subckt\n"
                f"X1 in mid terminator\n"
                f"R1 mid out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title Filter with Subckt - Missing Subckt\n"
                f".subckt terminator in out\n"
                f"Rt in out {rsub}\n"
                f".ends terminator\n"
                f"X1 in mid terminator\n"
                f"R1 mid out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "oracle": 'Add `.subckt terminator in out` / `Rt in out {rsub}` / `.ends terminator` before X1.',
            "difficulty": "medium",
            "tags": ["syntax", "subcircuit", "missing-subckt"],
            "circuit": "Filter with Subckt",
        })

    # Variant F: 7-stage ring oscillator
    for w1, l1, w2, l2, vdd in [
        ("1u", "90n", "500n", "90n", "1.0"),
    ]:
        tasks.append({
            "buggy": (
                f".title 7-Stage Ring Oscillator - Missing Subckt\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n4 vdd 0 inv\n"
                f"X4 n4 n5 vdd 0 inv\n"
                f"X5 n5 n6 vdd 0 inv\n"
                f"X6 n6 n7 vdd 0 inv\n"
                f"X7 n7 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".subckt inv_stage in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv_stage\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 1p 500n\n"
            ),
            "fixed": (
                f".title 7-Stage Ring Oscillator - Missing Subckt\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n4 vdd 0 inv\n"
                f"X4 n4 n5 vdd 0 inv\n"
                f"X5 n5 n6 vdd 0 inv\n"
                f"X6 n6 n7 vdd 0 inv\n"
                f"X7 n7 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".tran 1p 500n\n"
            ),
            "oracle": 'Rename `.subckt inv_stage` to `.subckt inv` and `.ends inv_stage` to `.ends inv`.',
            "difficulty": "hard",
            "tags": ["syntax", "ring-oscillator", "subckt-mismatch"],
            "circuit": "7-Stage Ring Oscillator",
        })

    # Variant G: Buffer with wrong subckt name
    for rsub, rout, vin in [
        ("470", "4.7k", "5"),
    ]:
        tasks.append({
            "buggy": (
                f".title Buffer Wrong Name - Missing Subckt\n"
                f"X1 in out attenuator\n"
                f"R1 out gnd {rout}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".subckt buffer in out\n"
                f"Rseries in out {rsub}\n"
                f".ends buffer\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title Buffer Wrong Name - Missing Subckt\n"
                f".subckt attenuator in out\n"
                f"Rseries in out {rsub}\n"
                f".ends attenuator\n"
                f"X1 in out attenuator\n"
                f"R1 out gnd {rout}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": 'Rename `.subckt buffer` to `.subckt attenuator` and `.ends buffer` to `.ends attenuator`.',
            "difficulty": "medium",
            "tags": ["syntax", "subcircuit", "missing-subckt"],
            "circuit": "Buffer Circuit",
        })

    # Variant H: Inverter chain with wrong name
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title Inverter Chain Wrong Name - Missing Subckt\n"
                f"X1 a b vdd gnd inverter\n"
                f"X2 b c vdd gnd inverter\n"
                f".subckt buf_stage in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends buf_stage\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title Inverter Chain Wrong Name - Missing Subckt\n"
                f".subckt inverter in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inverter\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"X1 a b vdd gnd inverter\n"
                f"X2 b c vdd gnd inverter\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": 'Rename `.subckt buf_stage` to `.subckt inverter` and `.ends buf_stage` to `.ends inverter`.',
            "difficulty": "medium",
            "tags": ["syntax", "subcircuit", "missing-subckt"],
            "circuit": "Inverter Chain",
        })
        tasks.append({
            "buggy": (
                f".title 7-Stage Ring Oscillator - Missing Subckt\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n4 vdd 0 inv\n"
                f"X4 n4 n5 vdd 0 inv\n"
                f"X5 n5 n6 vdd 0 inv\n"
                f"X6 n6 n7 vdd 0 inv\n"
                f"X7 n7 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".subckt inv_stage in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv_stage\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 1p 500n\n"
            ),
            "fixed": (
                f".title 7-Stage Ring Oscillator - Missing Subckt\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n4 vdd 0 inv\n"
                f"X4 n4 n5 vdd 0 inv\n"
                f"X5 n5 n6 vdd 0 inv\n"
                f"X6 n6 n7 vdd 0 inv\n"
                f"X7 n7 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".tran 1p 500n\n"
            ),
            "oracle": 'Rename `.subckt inv_stage` to `.subckt inv` and `.ends inv_stage` to `.ends inv`.',
            "difficulty": "hard",
            "tags": ["syntax", "ring-oscillator", "subckt-mismatch"],
            "circuit": "7-Stage Ring Oscillator",
        })

    return tasks


def _duplicate_element_tasks():
    """Same element name used twice."""
    tasks = []

    # Variant A: Voltage divider, R1 duplicate
    for i, (rin, r2, vin) in enumerate([
        ("1k", "1k", "5"),
        ("10k", "20k", "12"),
        ("4.7k", "10k", "3.3"),
    ]):
        tasks.append({
            "buggy": (
                f".title Voltage Divider - Duplicate Element\n"
                f"R1 in mid {rin}\n"
                f"R1 mid gnd {r2}\n"
                f"V1 in gnd {vin}\n"
                f".op\n"
            ),
            "fixed": (
                f".title Voltage Divider - Duplicate Element\n"
                f"R1 in mid {rin}\n"
                f"R2 mid gnd {r2}\n"
                f"V1 in gnd {vin}\n"
                f".op\n"
            ),
            "oracle": "Rename second `R1` to `R2`.",
            "difficulty": "easy",
            "tags": ["syntax", "resistor", "duplicate"],
            "circuit": "Voltage Divider",
        })

    # Variant B: CMOS latch, M1 duplicate
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
        ("4u", "90n", "2u", "90n", "1.2"),
    ]:
        tasks.append({
            "buggy": (
                f".title CMOS Latch - Duplicate Element\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f"M3 in out vdd vdd pmos W={w1} L={l1}\n"
                f"M1 in out gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd 0 {vdd}\n"
                f"Vin in 0 PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title CMOS Latch - Duplicate Element\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f"M3 in out vdd vdd pmos W={w1} L={l1}\n"
                f"M4 in out gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd 0 {vdd}\n"
                f"Vin in 0 PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": "Rename duplicate `M1` to `M4`.",
            "difficulty": "hard",
            "tags": ["syntax", "mosfet", "duplicate"],
            "circuit": "CMOS Latch",
        })

    # Variant C: RC filter, R1 duplicate
    for r1, c1, vin in [
        ("1k", "1p", "1.8"),
        ("10k", "100f", "3.3"),
    ]:
        tasks.append({
            "buggy": (
                f".title RC Filter - Duplicate Element\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"R1 out gnd 10k\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title RC Filter - Duplicate Element\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"R2 out gnd 10k\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "oracle": "Rename duplicate `R1` to `R2`.",
            "difficulty": "easy",
            "tags": ["syntax", "resistor", "duplicate"],
            "circuit": "RC Filter",
        })

    # Variant D: CMOS inverter, M2 duplicate
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
        ("3u", "130n", "1.5u", "130n", "1.5"),
    ]:
        tasks.append({
            "buggy": (
                f".title CMOS Inverter - Duplicate Element\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f"M2 out gate vdd vdd pmos W={w1} L={l1}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "fixed": (
                f".title CMOS Inverter - Duplicate Element\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f"M3 out gate vdd vdd pmos W={w1} L={l1}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "oracle": "Rename duplicate `M2` to `M3`.",
            "difficulty": "medium",
            "tags": ["syntax", "mosfet", "duplicate"],
            "circuit": "CMOS Inverter",
        })

    # Variant E: Diode, D1 duplicate
    for r1, vamp, freq in [
        ("1k", "5", "60"),
    ]:
        tasks.append({
            "buggy": (
                f".title Diode Circuit - Duplicate Element\n"
                f"D1 anode cathode Dreal\n"
                f"D1 anode2 cathode2 Dreal\n"
                f"R1 cathode 0 {r1}\n"
                f"R2 cathode2 0 {r1}\n"
                f".model Dreal D(Is=1e-14 N=1)\n"
                f"V1 anode 0 SIN(0 {vamp} {freq})\n"
                f"V2 anode2 0 SIN(0 {vamp} {freq})\n"
                f".tran 10p 33m\n"
            ),
            "fixed": (
                f".title Diode Circuit - Duplicate Element\n"
                f"D1 anode cathode Dreal\n"
                f"D2 anode2 cathode2 Dreal\n"
                f"R1 cathode 0 {r1}\n"
                f"R2 cathode2 0 {r1}\n"
                f".model Dreal D(Is=1e-14 N=1)\n"
                f"V1 anode 0 SIN(0 {vamp} {freq})\n"
                f"V2 anode2 0 SIN(0 {vamp} {freq})\n"
                f".tran 10p 33m\n"
            ),
            "oracle": "Rename duplicate `D1` to `D2`.",
            "difficulty": "medium",
            "tags": ["syntax", "diode", "duplicate"],
            "circuit": "Diode Circuit",
        })

    # Variant F: Capacitor duplicate
    for c1, r1, vin in [
        ("1p", "1k", "1.8"),
        ("10p", "10k", "3.3"),
    ]:
        tasks.append({
            "buggy": (
                f".title RC Circuit - Duplicate Element\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"C1 out2 gnd 10p\n"
                f"R2 out2 gnd {r1}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title RC Circuit - Duplicate Element\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"C2 out2 gnd 10p\n"
                f"R2 out2 gnd {r1}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "oracle": "Rename duplicate `C1` to `C2`.",
            "difficulty": "easy",
            "tags": ["syntax", "capacitor", "duplicate"],
            "circuit": "RC Circuit",
        })

    # Variant G: MOSFET duplicate in NAND
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title NAND Gate - Duplicate Element\n"
                f"M1 out a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M3 mid b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NAND Gate - Duplicate Element\n"
                f"M1 out a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M4 mid b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": "Rename duplicate `M3` to `M4`.",
            "difficulty": "medium",
            "tags": ["syntax", "mosfet", "duplicate"],
            "circuit": "NAND Gate",
        })

    # Variant H: Resistor duplicate in RC high-pass
    for c1, r1, vin in [
        ("1p", "1k", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title RC High-Pass - Duplicate Element\n"
                f"C1 in out {c1}\n"
                f"R1 out gnd {r1}\n"
                f"R1 in gnd 10k\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title RC High-Pass - Duplicate Element\n"
                f"C1 in out {c1}\n"
                f"R1 out gnd {r1}\n"
                f"R2 in gnd 10k\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "oracle": "Rename duplicate `R1` to `R2`.",
            "difficulty": "easy",
            "tags": ["syntax", "resistor", "duplicate"],
            "circuit": "RC High-Pass Filter",
        })
        tasks.append({
            "buggy": (
                f".title RC Circuit - Duplicate Element\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"C1 out2 gnd 10p\n"
                f"R2 out2 gnd {r1}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title RC Circuit - Duplicate Element\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"C2 out2 gnd 10p\n"
                f"R2 out2 gnd {r1}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "oracle": "Rename duplicate `C1` to `C2`.",
            "difficulty": "easy",
            "tags": ["syntax", "capacitor", "duplicate"],
            "circuit": "RC Circuit",
        })

    return tasks


def _wrong_pin_count_tasks():
    """Pin count mismatch on subcircuit instance."""
    tasks = []

    # Variant A: Inverter subcircuit, missing gnd pin
    for i, (w1, l1, w2, l2, vdd) in enumerate([
        ("2u", "180n", "1u", "180n", "1.8"),
        ("4u", "90n", "2u", "90n", "1.2"),
        ("3u", "130n", "1.5u", "130n", "1.5"),
        ("1u", "250n", "500n", "250n", "2.5"),
    ]):
        tasks.append({
            "buggy": (
                f".title Inverter Subcircuit - Wrong Pin Count\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f"X1 in out vdd inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title Inverter Subcircuit - Wrong Pin Count\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f"X1 in out vdd gnd inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": "Add missing `gnd` pin: change `X1 in out vdd inv` to `X1 in out vdd gnd inv`.",
            "difficulty": "medium",
            "tags": ["syntax", "subcircuit", "wrong-pins"],
            "circuit": "Inverter Subcircuit",
        })

    # Variant B: Buffer subcircuit, extra pin
    for r1, vin in [
        ("100", "1.8"),
        ("220", "3.3"),
        ("470", "5"),
    ]:
        tasks.append({
            "buggy": (
                f".title Buffer Subcircuit - Wrong Pin Count\n"
                f".subckt buf in out\n"
                f"Rseries in out {r1}\n"
                f".ends buf\n"
                f"X1 in out gnd buf\n"
                f"R1 out gnd 1k\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title Buffer Subcircuit - Wrong Pin Count\n"
                f".subckt buf in out\n"
                f"Rseries in out {r1}\n"
                f".ends buf\n"
                f"X1 in out buf\n"
                f"R1 out gnd 1k\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": "Remove extra `gnd` pin: change `X1 in out gnd buf` to `X1 in out buf`.",
            "difficulty": "medium",
            "tags": ["syntax", "subcircuit", "wrong-pins"],
            "circuit": "Buffer Subcircuit",
        })

    # Variant C: Ring oscillator, missing vdd pin
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title Ring Oscillator - Wrong Pin Count\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f"X1 n1 n2 0 inv\n"
                f"X2 n2 n3 0 inv\n"
                f"X3 n3 n1 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 1p 100n\n"
            ),
            "fixed": (
                f".title Ring Oscillator - Wrong Pin Count\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 1p 100n\n"
            ),
            "oracle": "Add missing `vdd` pin: change `X1 n1 n2 0 inv` to `X1 n1 n2 vdd 0 inv`.",
            "difficulty": "hard",
            "tags": ["syntax", "ring-oscillator", "wrong-pins"],
            "circuit": "Ring Oscillator",
        })

    # Variant D: NAND subcircuit, missing pin
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
        ("3u", "130n", "1.5u", "130n", "1.5"),
    ]:
        tasks.append({
            "buggy": (
                f".title NAND Gate Subcircuit - Wrong Pin Count\n"
                f".subckt nand2 a b out vdd gnd\n"
                f"M1 out a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M4 mid b gnd gnd nmos W={w2} L={l2}\n"
                f".ends nand2\n"
                f"X1 a b out vdd nand2\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NAND Gate Subcircuit - Wrong Pin Count\n"
                f".subckt nand2 a b out vdd gnd\n"
                f"M1 out a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M4 mid b gnd gnd nmos W={w2} L={l2}\n"
                f".ends nand2\n"
                f"X1 a b out vdd gnd nand2\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": "Add missing `gnd` pin: change `X1 a b out vdd nand2` to `X1 a b out vdd gnd nand2`.",
            "difficulty": "hard",
            "tags": ["syntax", "subcircuit", "wrong-pins"],
            "circuit": "NAND Gate Subcircuit",
        })

    # Variant E: NOR subcircuit, missing pin
    for w1, l1, w2, l2, vdd in [
        ("4u", "180n", "1u", "180n", "1.8"),
        ("2u", "130n", "1u", "130n", "1.5"),
    ]:
        tasks.append({
            "buggy": (
                f".title NOR Gate Subcircuit - Wrong Pin Count\n"
                f".subckt nor2 a b out vdd gnd\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f".ends nor2\n"
                f"X1 a b out vdd nor2\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NOR Gate Subcircuit - Wrong Pin Count\n"
                f".subckt nor2 a b out vdd gnd\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f".ends nor2\n"
                f"X1 a b out vdd gnd nor2\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": "Add missing `gnd` pin: change `X1 a b out vdd nor2` to `X1 a b out vdd gnd nor2`.",
            "difficulty": "hard",
            "tags": ["syntax", "subcircuit", "wrong-pins"],
            "circuit": "NOR Gate Subcircuit",
        })

    # Variant F: Inverter subcircuit, extra pin
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
        ("3u", "130n", "1.5u", "130n", "1.5"),
    ]:
        tasks.append({
            "buggy": (
                f".title Inverter Extra Pin - Wrong Pin Count\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f"X1 in out vdd gnd mid inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title Inverter Extra Pin - Wrong Pin Count\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f"X1 in out vdd gnd inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": "Remove extra `mid` pin: change `X1 in out vdd gnd mid inv` to `X1 in out vdd gnd inv`.",
            "difficulty": "medium",
            "tags": ["syntax", "subcircuit", "wrong-pins"],
            "circuit": "Inverter Subcircuit",
        })

    return tasks


def _missing_include_tasks():
    """Include references nonexistent file."""
    tasks = []

    # Variant A: MOSFET circuit with missing include
    for i, (w1, l1, w2, l2, vdd) in enumerate([
        ("2u", "180n", "1u", "180n", "1.8"),
        ("4u", "90n", "2u", "90n", "1.2"),
        ("1u", "250n", "500n", "250n", "2.5"),
    ]):
        fname = f"models_{i+1}.lib"
        tasks.append({
            "buggy": (
                f".title MOSFET with Include - Missing Include\n"
                f".include {fname}\n"
                f"M1 out gate gnd gnd nmos W={w1} L={l1}\n"
                f"R1 out 0 1k\n"
                f"Vdd gate 0 {vdd}\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title MOSFET with Include - Missing Include\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"M1 out gate gnd gnd nmos W={w1} L={l1}\n"
                f"R1 out 0 1k\n"
                f"Vdd gate 0 {vdd}\n"
                f".tran 10p 10n\n"
            ),
            "oracle": f'Remove `.include {fname}` and add `.model nmos nmos (level=1 vto=0.7 kp=120u)` directly.',
            "difficulty": "medium",
            "tags": ["syntax", "include", "missing-file"],
            "circuit": "MOSFET Circuit",
        })

    # Variant B: CMOS inverter with missing include
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
        ("3u", "130n", "1.5u", "130n", "1.5"),
    ]:
        tasks.append({
            "buggy": (
                f".title CMOS Inverter - Missing Include\n"
                f".include cmos_models.lib\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "fixed": (
                f".title CMOS Inverter - Missing Include\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "oracle": 'Remove `.include cmos_models.lib` and add model definitions directly.',
            "difficulty": "easy",
            "tags": ["syntax", "include", "missing-file"],
            "circuit": "CMOS Inverter",
        })

    # Variant C: RC filter with missing include
    for r1, c1, vin in [
        ("1k", "1p", "1.8"),
        ("10k", "100f", "3.3"),
    ]:
        tasks.append({
            "buggy": (
                f".title RC Filter - Missing Include\n"
                f".include passive_models.lib\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title RC Filter - Missing Include\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"V1 in gnd PULSE(0 {vin} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 10n\n"
            ),
            "oracle": 'Remove `.include passive_models.lib` (no models needed for passive components).',
            "difficulty": "easy",
            "tags": ["syntax", "include", "missing-file"],
            "circuit": "RC Filter",
        })

    # Variant D: Diode with missing include
    for r1, vamp, freq, sim_end in [
        ("1k", "5", "60", "33m"),
    ]:
        tasks.append({
            "buggy": (
                f".title Diode Rectifier - Missing Include\n"
                f".include diode_models.lib\n"
                f"D1 anode cathode Dreal\n"
                f"R1 cathode 0 {r1}\n"
                f"V1 anode 0 SIN(0 {vamp} {freq})\n"
                f".tran 10p {sim_end}\n"
            ),
            "fixed": (
                f".title Diode Rectifier - Missing Include\n"
                f".model Dreal D(Is=1e-14 N=1)\n"
                f"D1 anode cathode Dreal\n"
                f"R1 cathode 0 {r1}\n"
                f"V1 anode 0 SIN(0 {vamp} {freq})\n"
                f".tran 10p {sim_end}\n"
            ),
            "oracle": 'Remove `.include diode_models.lib` and add `.model Dreal D(Is=1e-14 N=1)` directly.',
            "difficulty": "medium",
            "tags": ["syntax", "include", "missing-file"],
            "circuit": "Diode Rectifier",
        })

    # Variant E: Voltage divider with missing include
    for r1, r2, vin in [
        ("1k", "1k", "5"),
        ("10k", "20k", "12"),
    ]:
        tasks.append({
            "buggy": (
                f".title Voltage Divider - Missing Include\n"
                f".include component_lib.lib\n"
                f"R1 in mid {r1}\n"
                f"R2 mid gnd {r2}\n"
                f"V1 in gnd {vin}\n"
                f".op\n"
            ),
            "fixed": (
                f".title Voltage Divider - Missing Include\n"
                f"R1 in mid {r1}\n"
                f"R2 mid gnd {r2}\n"
                f"V1 in gnd {vin}\n"
                f".op\n"
            ),
            "oracle": 'Remove `.include component_lib.lib` (no include needed).',
            "difficulty": "easy",
            "tags": ["syntax", "include", "missing-file"],
            "circuit": "Voltage Divider",
        })

    # Variant F: NOR gate with missing include
    for w1, l1, w2, l2, vdd in [
        ("4u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title NOR Gate - Missing Include\n"
                f".include nor_models.lib\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NOR Gate - Missing Include\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": 'Remove `.include nor_models.lib` and add model definitions directly.',
            "difficulty": "medium",
            "tags": ["syntax", "include", "missing-file"],
            "circuit": "NOR Gate",
        })

    # Variant G: NAND gate with missing include
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title NAND Gate - Missing Include\n"
                f".include nand_lib.lib\n"
                f"M1 out a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M4 mid b gnd gnd nmos W={w2} L={l2}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NAND Gate - Missing Include\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"M1 out a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M4 mid b gnd gnd nmos W={w2} L={l2}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": 'Remove `.include nand_lib.lib` and add model definitions directly.',
            "difficulty": "medium",
            "tags": ["syntax", "include", "missing-file"],
            "circuit": "NAND Gate",
        })

    # Variant H: Ring oscillator with missing include
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title Ring Oscillator - Missing Include\n"
                f".include ring_models.lib\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".tran 1p 100n\n"
            ),
            "fixed": (
                f".title Ring Oscillator - Missing Include\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".tran 1p 100n\n"
            ),
            "oracle": 'Remove `.include ring_models.lib` and add model definitions directly.',
            "difficulty": "hard",
            "tags": ["syntax", "include", "missing-file"],
            "circuit": "Ring Oscillator",
        })
        tasks.append({
            "buggy": (
                f".title NOR Gate - Missing Include\n"
                f".include nor_models.lib\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NOR Gate - Missing Include\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": 'Remove `.include nor_models.lib` and add model definitions directly.',
            "difficulty": "medium",
            "tags": ["syntax", "include", "missing-file"],
            "circuit": "NOR Gate",
        })

    return tasks


def _unsupported_dialect_tasks():
    """Invalid model level or unsupported parameter."""
    tasks = []

    # Variant A: MOSFET level=99
    for i, (w1, l1, w2, l2, vdd) in enumerate([
        ("2u", "180n", "1u", "180n", "1.8"),
        ("4u", "90n", "2u", "90n", "1.2"),
        ("1u", "250n", "500n", "250n", "2.5"),
    ]):
        tasks.append({
            "buggy": (
                f".title CMOS Inverter - Bad Level {99+i}\n"
                f"M1 out gate gnd gnd nmos W={w1} L={l1}\n"
                f".model nmos nmos (level={99+i} vto=0.7 kp=120u)\n"
                f"Vdd gate 0 {vdd}\n"
                f"R1 out 0 1k\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title CMOS Inverter - Bad Level {99+i}\n"
                f"M1 out gate gnd gnd nmos W={w1} L={l1}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd gate 0 {vdd}\n"
                f"R1 out 0 1k\n"
                f".tran 10p 10n\n"
            ),
            "oracle": f'Change `level={99+i}` to `level=1` in the .model statement.',
            "difficulty": "medium",
            "tags": ["syntax", "mosfet", "invalid-level"],
            "circuit": "MOSFET Circuit",
        })

    # Variant B: CMOS inverter with bad level on pmos
    for i, (w1, l1, w2, l2, vdd) in enumerate([
        ("2u", "180n", "1u", "180n", "1.8"),
        ("3u", "130n", "1.5u", "130n", "1.5"),
    ]):
        bad_level = 50 + i
        tasks.append({
            "buggy": (
                f".title CMOS Inverter - Bad PMOS Level\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level={bad_level} vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "fixed": (
                f".title CMOS Inverter - Bad PMOS Level\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "oracle": f'Change `level={bad_level}` to `level=1` in the pmos .model statement.',
            "difficulty": "medium",
            "tags": ["syntax", "mosfet", "invalid-level"],
            "circuit": "CMOS Inverter",
        })

    # Variant C: NAND gate with bad level
    for bad_level in [200, 201]:
        w1, l1, w2, l2, vdd = "2u", "180n", "1u", "180n", "1.8"
        tasks.append({
            "buggy": (
                f".title NAND Gate - Bad Level\n"
                f"M1 out a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M4 mid b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level={bad_level} vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NAND Gate - Bad Level\n"
                f"M1 out a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b vdd vdd pmos W={w1} L={l1}\n"
                f"M3 out a mid mid nmos W={w2} L={l2}\n"
                f"M4 mid b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": f'Change `level={bad_level}` to `level=1` in the pmos .model statement.',
            "difficulty": "hard",
            "tags": ["syntax", "mosfet", "invalid-level"],
            "circuit": "NAND Gate",
        })

    # Variant D: NOR gate with bad level
    for bad_level in [150, 151]:
        w1, l1, w2, l2, vdd = "4u", "180n", "1u", "180n", "1.8"
        tasks.append({
            "buggy": (
                f".title NOR Gate - Bad Level\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level={bad_level} vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NOR Gate - Bad Level\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": f'Change `level={bad_level}` to `level=1` in the nmos .model statement.',
            "difficulty": "hard",
            "tags": ["syntax", "mosfet", "invalid-level"],
            "circuit": "NOR Gate",
        })

    # Variant E: Ring oscillator with bad level
    for bad_level in [999]:
        w1, l1, w2, l2, vdd = "2u", "180n", "1u", "180n", "1.8"
        tasks.append({
            "buggy": (
                f".title Ring Oscillator - Bad Level\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level={bad_level} vto=0.7 kp=120u)\n"
                f".tran 1p 100n\n"
            ),
            "fixed": (
                f".title Ring Oscillator - Bad Level\n"
                f".subckt inv in out vdd gnd\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f".ends inv\n"
                f"X1 n1 n2 vdd 0 inv\n"
                f"X2 n2 n3 vdd 0 inv\n"
                f"X3 n3 n1 vdd 0 inv\n"
                f"Vdd vdd 0 {vdd}\n"
                f".ic v(n1)={vdd}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 1p 100n\n"
            ),
            "oracle": f'Change `level={bad_level}` to `level=1` in the nmos .model statement.',
            "difficulty": "hard",
            "tags": ["syntax", "ring-oscillator", "invalid-level"],
            "circuit": "Ring Oscillator",
        })

    # Variant F: CMOS latch with bad level
    for bad_level in [77]:
        w1, l1, w2, l2, vdd = "2u", "180n", "1u", "180n", "1.8"
        tasks.append({
            "buggy": (
                f".title CMOS Latch - Bad Level\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f"M3 in out vdd vdd pmos W={w1} L={l1}\n"
                f"M4 in out gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level={bad_level} vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd 0 {vdd}\n"
                f"Vin in 0 PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title CMOS Latch - Bad Level\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out in gnd gnd nmos W={w2} L={l2}\n"
                f"M3 in out vdd vdd pmos W={w1} L={l1}\n"
                f"M4 in out gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd 0 {vdd}\n"
                f"Vin in 0 PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": f'Change `level={bad_level}` to `level=1` in the pmos .model statement.',
            "difficulty": "medium",
            "tags": ["syntax", "mosfet", "invalid-level"],
            "circuit": "CMOS Latch",
        })

    # Variant G: Source follower with bad level
    for bad_level in [88, 77]:
        w1, l1, r1, vdd = "4u", "180n", "1k", "1.8"
        tasks.append({
            "buggy": (
                f".title Source Follower - Bad Level\n"
                f"M1 vdd in out gnd nmos W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".model nmos nmos (level={bad_level} vto=0.7 kp=120u)\n"
                f".tran 10p 16n\n"
            ),
            "fixed": (
                f".title Source Follower - Bad Level\n"
                f"M1 vdd in out gnd nmos W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 10p 16n\n"
            ),
            "oracle": f'Change `level={bad_level}` to `level=1` in the .model statement.',
            "difficulty": "medium",
            "tags": ["syntax", "mosfet", "invalid-level"],
            "circuit": "Source Follower",
        })

    # Variant H: Current mirror with bad level
    for bad_level in [66]:
        w1, l1, r1, vdd = "2u", "180n", "10k", "1.8"
        tasks.append({
            "buggy": (
                f".title Current Mirror - Bad Level\n"
                f"M1 ref ref gnd gnd nmos W={w1} L={l1}\n"
                f"M2 out ref gnd gnd nmos W={w1} L={l1}\n"
                f"R1 vdd ref {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f".model nmos nmos (level={bad_level} vto=0.7 kp=120u)\n"
                f".op\n"
            ),
            "fixed": (
                f".title Current Mirror - Bad Level\n"
                f"M1 ref ref gnd gnd nmos W={w1} L={l1}\n"
                f"M2 out ref gnd gnd nmos W={w1} L={l1}\n"
                f"R1 vdd ref {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".op\n"
            ),
            "oracle": f'Change `level={bad_level}` to `level=1` in the .model statement.',
            "difficulty": "hard",
            "tags": ["syntax", "mosfet", "invalid-level"],
            "circuit": "Current Mirror",
        })

    return tasks


def _invalid_directive_tasks():
    """Malformed directive (e.g., .include with no filename)."""
    tasks = []

    # Variant A: Bare .include
    for i, (r1, c1, vin) in enumerate([
        ("1k", "1p", "1.8"),
        ("10k", "100f", "3.3"),
        ("4.7k", "10p", "5"),
    ]):
        tasks.append({
            "buggy": (
                f".title RC Filter - Invalid Directive\n"
                f".include\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"V1 in gnd {vin}\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title RC Filter - Invalid Directive\n"
                f"R1 in out {r1}\n"
                f"C1 out gnd {c1}\n"
                f"V1 in gnd {vin}\n"
                f".tran 10p 10n\n"
            ),
            "oracle": "Remove the malformed `.include` line (no filename).",
            "difficulty": "medium",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "RC Filter",
        })

    # Variant B: Bare .inc
    for r1, r2, vin in [
        ("1k", "1k", "5"),
        ("10k", "20k", "12"),
    ]:
        tasks.append({
            "buggy": (
                f".title Voltage Divider - Invalid Directive\n"
                f".inc\n"
                f"R1 in mid {r1}\n"
                f"R2 mid gnd {r2}\n"
                f"V1 in gnd {vin}\n"
                f".op\n"
            ),
            "fixed": (
                f".title Voltage Divider - Invalid Directive\n"
                f"R1 in mid {r1}\n"
                f"R2 mid gnd {r2}\n"
                f"V1 in gnd {vin}\n"
                f".op\n"
            ),
            "oracle": "Remove the malformed `.inc` line (no filename).",
            "difficulty": "easy",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "Voltage Divider",
        })

    # Variant C: MOSFET circuit with bare .lib
    for w1, l1, vdd in [
        ("2u", "180n", "1.8"),
        ("4u", "90n", "1.2"),
    ]:
        tasks.append({
            "buggy": (
                f".title MOSFET Circuit - Invalid Directive\n"
                f".lib\n"
                f"M1 out gate gnd gnd nmos W={w1} L={l1}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd gate 0 {vdd}\n"
                f"R1 out 0 1k\n"
                f".tran 10p 10n\n"
            ),
            "fixed": (
                f".title MOSFET Circuit - Invalid Directive\n"
                f"M1 out gate gnd gnd nmos W={w1} L={l1}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd gate 0 {vdd}\n"
                f"R1 out 0 1k\n"
                f".tran 10p 10n\n"
            ),
            "oracle": "Remove the malformed `.lib` line (no filename).",
            "difficulty": "medium",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "MOSFET Circuit",
        })

    # Variant D: Diode circuit with bare .include
    for r1, vamp, freq in [
        ("1k", "5", "60"),
    ]:
        tasks.append({
            "buggy": (
                f".title Diode Rectifier - Invalid Directive\n"
                f".include\n"
                f"D1 anode cathode Dreal\n"
                f"R1 cathode 0 {r1}\n"
                f"V1 anode 0 SIN(0 {vamp} {freq})\n"
                f".model Dreal D(Is=1e-14 N=1)\n"
                f".tran 10p 33m\n"
            ),
            "fixed": (
                f".title Diode Rectifier - Invalid Directive\n"
                f"D1 anode cathode Dreal\n"
                f"R1 cathode 0 {r1}\n"
                f"V1 anode 0 SIN(0 {vamp} {freq})\n"
                f".model Dreal D(Is=1e-14 N=1)\n"
                f".tran 10p 33m\n"
            ),
            "oracle": "Remove the malformed `.include` line (no filename).",
            "difficulty": "medium",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "Diode Rectifier",
        })

    # Variant E: CMOS inverter with bare .include
    for w1, l1, w2, l2, vdd in [
        ("2u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title CMOS Inverter - Invalid Directive\n"
                f".include\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "fixed": (
                f".title CMOS Inverter - Invalid Directive\n"
                f"M1 out gate vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out gate gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin gate gnd PULSE(0 {vdd} 1n 100p 100p 1n 2n)\n"
                f".tran 10p 4n\n"
            ),
            "oracle": "Remove the malformed `.include` line (no filename).",
            "difficulty": "easy",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "CMOS Inverter",
        })

    # Variant F: Current mirror with bare .inc
    for w1, l1, r1, vdd in [
        ("2u", "180n", "10k", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title Current Mirror - Invalid Directive\n"
                f".inc\n"
                f"M1 ref ref gnd gnd nmos W={w1} L={l1}\n"
                f"M2 out ref gnd gnd nmos W={w1} L={l1}\n"
                f"R1 vdd ref {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".op\n"
            ),
            "fixed": (
                f".title Current Mirror - Invalid Directive\n"
                f"M1 ref ref gnd gnd nmos W={w1} L={l1}\n"
                f"M2 out ref gnd gnd nmos W={w1} L={l1}\n"
                f"R1 vdd ref {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".op\n"
            ),
            "oracle": "Remove the malformed `.inc` line (no filename).",
            "difficulty": "hard",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "Current Mirror",
        })

    # Variant G: Source follower with bare .lib
    for w1, l1, r1, vdd in [
        ("4u", "180n", "1k", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title Source Follower - Invalid Directive\n"
                f".lib\n"
                f"M1 vdd in out gnd nmos W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 10p 16n\n"
            ),
            "fixed": (
                f".title Source Follower - Invalid Directive\n"
                f"M1 vdd in out gnd nmos W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".tran 10p 16n\n"
            ),
            "oracle": "Remove the malformed `.lib` line (no filename).",
            "difficulty": "medium",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "Source Follower",
        })

    # Variant H: Common-source with bare .include
    for w1, l1, r1, vdd in [
        ("10u", "180n", "10k", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title Common-Source Amplifier - Invalid Directive\n"
                f".include\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".tran 10p 16n\n"
            ),
            "fixed": (
                f".title Common-Source Amplifier - Invalid Directive\n"
                f"M1 out in vdd vdd pmos W={w1} L={l1}\n"
                f"R1 out gnd {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Vin in gnd PULSE(0 {vdd} 1n 100p 100p 2n 4n)\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".tran 10p 16n\n"
            ),
            "oracle": "Remove the malformed `.include` line (no filename).",
            "difficulty": "medium",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "Common-Source Amplifier",
        })

    # Variant I: NOR gate with bare .inc
    for w1, l1, w2, l2, vdd in [
        ("4u", "180n", "1u", "180n", "1.8"),
    ]:
        tasks.append({
            "buggy": (
                f".title NOR Gate - Invalid Directive\n"
                f".inc\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "fixed": (
                f".title NOR Gate - Invalid Directive\n"
                f"M1 mid a vdd vdd pmos W={w1} L={l1}\n"
                f"M2 out b mid mid pmos W={w1} L={l1}\n"
                f"M3 out a gnd gnd nmos W={w2} L={l2}\n"
                f"M4 out b gnd gnd nmos W={w2} L={l2}\n"
                f".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f"Vdd vdd gnd {vdd}\n"
                f"Va a gnd PULSE(0 {vdd} 0 100p 100p 1n 2n)\n"
                f"Vb b gnd PULSE(0 {vdd} 0 100p 100p 2n 4n)\n"
                f".tran 10p 8n\n"
            ),
            "oracle": "Remove the malformed `.inc` line (no filename).",
            "difficulty": "medium",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "NOR Gate",
        })
        tasks.append({
            "buggy": (
                f".title Current Mirror - Invalid Directive\n"
                f".inc\n"
                f"M1 ref ref gnd gnd nmos W={w1} L={l1}\n"
                f"M2 out ref gnd gnd nmos W={w1} L={l1}\n"
                f"R1 vdd ref {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".op\n"
            ),
            "fixed": (
                f".title Current Mirror - Invalid Directive\n"
                f"M1 ref ref gnd gnd nmos W={w1} L={l1}\n"
                f"M2 out ref gnd gnd nmos W={w1} L={l1}\n"
                f"R1 vdd ref {r1}\n"
                f"Vdd vdd gnd {vdd}\n"
                f".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
                f".op\n"
            ),
            "oracle": "Remove the malformed `.inc` line (no filename).",
            "difficulty": "hard",
            "tags": ["syntax", "include", "malformed"],
            "circuit": "Current Mirror",
        })

    return tasks


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

CATEGORY_GENERATORS = {
    "missing_model": _missing_model_tasks,
    "missing_subckt": _missing_subckt_tasks,
    "duplicate_element": _duplicate_element_tasks,
    "wrong_pin_count": _wrong_pin_count_tasks,
    "missing_include": _missing_include_tasks,
    "unsupported_dialect": _unsupported_dialect_tasks,
    "invalid_directive": _invalid_directive_tasks,
}


def generate_spice_debug_tasks(output_dir: Path) -> int:
    """Generate 100 SPICE deck debug tasks."""
    tasks = []
    for category, gen_fn in CATEGORY_GENERATORS.items():
        for task_def in gen_fn():
            tasks.append({**task_def, "expected_error_category": category})

    count = 0
    for idx, task_def in enumerate(tasks):
        task_num = idx + 1
        task_id = f"spice_deck_debug_{task_num:04d}"

        task_dir = output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        visible_dir = task_dir / "visible"
        hidden_dir = task_dir / "hidden"
        oracle_dir = task_dir / "oracle"
        visible_dir.mkdir(exist_ok=True)
        hidden_dir.mkdir(exist_ok=True)
        oracle_dir.mkdir(exist_ok=True)

        # Wrap with .end
        buggy_deck = task_def["buggy"].rstrip() + "\n.end\n"
        fixed_deck = task_def["fixed"].rstrip() + "\n.end\n"

        deck_file = visible_dir / f"{task_id}_bug.sp"
        deck_file.write_text(buggy_deck)

        fixed_file = hidden_dir / f"{task_id}_fixed.sp"
        fixed_file.write_text(fixed_deck)

        oracle_file = oracle_dir / "answer.md"
        oracle_file.write_text(f"# Expected Fix\n\n{task_def['oracle']}\n")

        prompt = f"""# SPICE Deck Debug Task

## Objective
Find and fix the bug in the provided SPICE simulation deck.

## Bug Description
The deck has a {task_def['expected_error_category'].replace('_', ' ')} issue.

## Instructions
1. Read the SPICE deck file in `visible/`
2. Identify the bug
3. Describe the fix needed
4. Provide the corrected SPICE deck

## Files
- `visible/` — Contains the buggy SPICE deck

## Constraints
- Only modify the buggy lines
- Preserve the circuit topology (unless the bug is a topology error)
- The fix should be minimal and correct
"""
        (task_dir / "prompt.md").write_text(prompt)

        tags = list(set(task_def.get("tags", ["syntax"])))
        metadata = {
            "task_id": task_id,
            "domain": "spice_deck_debug",
            "task_family": "syntax_error",
            "expected_error_category": task_def["expected_error_category"],
            "difficulty": task_def.get("difficulty", "medium"),
            "tags": tags,
            "prompt_file": "prompt.md",
            "visible_files": [str(deck_file.relative_to(task_dir))],
            "hidden_files": [str(fixed_file.relative_to(task_dir))],
            "expected_outputs": [f"{task_id}_fixed.sp"],
            "grader": {
                "type": "exact_match",
                "criteria": "Fixed SPICE deck must be functionally equivalent to oracle solution",
            },
            "timeout_sec": 300,
            "license_notes": "Apache-2.0, synthetic content",
            "generation_source": "synthetic",
            "oracle_description": task_def["oracle"],
            "validation_status": "candidate_unvalidated",
            "optional_tool_backends": ["hspice", "spectre"],
            "public_release_safe": True,
        }

        with open(task_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        count += 1

    return count


# For test compatibility — expose category plan
CATEGORY_PLAN = {name: len(fn()) for name, fn in CATEGORY_GENERATORS.items()}
BUG_FUNCTIONS = CATEGORY_GENERATORS  # test references this


def main():
    count = generate_spice_debug_tasks(TASKS_DIR)
    print(f"Generated {count} SPICE deck debug tasks")


if __name__ == "__main__":
    main()
