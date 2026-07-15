#!/usr/bin/env python3
"""Phase-4W held-out pair generator: 0011 (ambiguous) / 0012 (clear), golden typ/test.

DETERMINISTIC, AUDITED, ROLE-AWARE SEMANTIC TRANSFORMATION (NOT global token substitution).
Derives 0011 from 0009 and 0012 from 0010 by relabeling the GOLDEN binding slow/func -> typ/test
(and the mutant swap + PVT decoy consistently), reusing the byte-identical netlist/library/timing
body (the report body is corner-independent by design). The typed-axis VOCABULARY in truth (which
lists slow/typ/func as members) is NOT remapped -- only role-instantiation sites change.

Fail-closed:
  * assert source git commit + source file hashes;
  * for every role anchor, assert the current value == expected source value, then set the target
    (rejects missing/extra/ambiguous/colliding replacements and any source drift);
  * regenerate twice in independent temp dirs and require byte-identical outputs;
  * emit role mapping + source/output hashes + script hash + semantic-diff manifest.
No manual post-generation edits; 0009/0010 are never modified.

Usage: python3 scripts/gen_phase4w_heldout.py [--out <tasks/p14_workflow_handoff>]
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
EXPECTED_COMMIT = "0f38cc06826e3dcad22dacbb1baea27049872da5"

# role -> (source_value, target_value). golden_corner and swap_scen_slot coincide (func->test);
# golden_scenario (slow->typ) and swap_corner_slot (typ->slow) are inverse -> handled by anchor scoping.
ROLE_MAP = {
    "golden_scenario":  ("slow", "typ"),
    "golden_corner":    ("func", "test"),
    "swap_scen_slot":   ("func", "test"),     # mutant scenario slot = golden CORNER value
    "swap_corner_slot": ("typ", "slow"),      # mutant corner slot = a non-golden SCENARIO value
    "pvt_label":        ("slow_1.0V_125C", "typ_1.0V_25C"),
}
GOLDEN = ("typ", "test")

# source file hashes (0009/0010 flow_config + truth) -- fail-closed source pinning
SRC_HASHES = {
    "0009/flow_config": "65d3682943022f6306a5ef1391d322a03695cb7c285c364b1aa50f983d75b203",
    "0010/flow_config": "7d56dbefafc27215217e9ca9ffe20b26cd428b1fb2b9c2df1a9418dd5f9242e6",
    "0009/truth":       "5c0c2e867d7546f8cc20c26e9351aaf4d3510edd735f26f224f4e1aff457b522",
    "0010/truth":       "3c7be745872b0ab08eec5a361a7bb4d32110325a8075bddc08d1859675f03629",
}

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def sha_file(p: Path) -> str: return sha(p.read_bytes())

class FailClosed(Exception): pass

# ---- JSON field-scoped role replacement -----------------------------------------
def jget(doc, path):
    cur = doc
    for k in path:
        if isinstance(k, int):
            if not isinstance(cur, list) or k >= len(cur): raise FailClosed(f"missing index {path}")
            cur = cur[k]
        else:
            if not isinstance(cur, dict) or k not in cur: raise FailClosed(f"missing key {path}")
            cur = cur[k]
    return cur
def jset(doc, path, val):
    cur = doc
    for k in path[:-1]:
        cur = cur[k] if not isinstance(k, int) else cur[k]
    cur[path[-1]] = val

def role_replace_json(doc, path, role, count):
    old = jget(doc, path)
    exp_src = ROLE_MAP[role][0]
    if old != exp_src:
        raise FailClosed(f"anchor {path} role={role}: expected src {exp_src!r}, found {old!r}")
    jset(doc, path, ROLE_MAP[role][1])
    count[role] = count.get(role, 0) + 1

# ---- report/log line-anchor role replacement -----------------------------------
def role_replace_line(text, line_needle, key, role, count):
    """On the (single) line containing line_needle, replace key=<src> with key=<tgt>; assert 1 hit."""
    exp_src = ROLE_MAP[role][0]
    hits = 0
    out = []
    for ln in text.splitlines():
        if line_needle in ln and f"{key}=" in ln:
            # replace the token key=<src> -> key=<tgt> exactly once on this line
            tok = f"{key}={exp_src}"
            if tok not in ln:
                raise FailClosed(f"line anchor {line_needle!r} key={key} role={role}: token {tok!r} not found in: {ln!r}")
            ln = ln.replace(tok, f"{key}={ROLE_MAP[role][1]}", 1)
            hits += 1
        out.append(ln)
    if hits != 1:
        raise FailClosed(f"line anchor {line_needle!r} key={key} role={role}: expected 1 hit, got {hits}")
    count[role] = count.get(role, 0) + 1
    return "\n".join(out).rstrip() + "\n"

def transform_common_json(task: Path, count, src_variant: str):
    """JSON value sites common to 0009/0010 structure."""
    # flow_config (mutant)
    fc = task / "files/flow_config.json"; d = json.loads(fc.read_text())
    role_replace_json(d, ["scenario"], "swap_scen_slot", count)
    role_replace_json(d, ["corner"], "swap_corner_slot", count)
    fc.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    # evidence_manifest (claims golden; body stale)
    em = task / "files/evidence_manifest.json"; d = json.loads(em.read_text())
    role_replace_json(d, ["scenario"], "golden_scenario", count)
    role_replace_json(d, ["corner"], "golden_corner", count)
    em.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    # evidence_D (role fields swapped inside); keys are op_point/mode (0009) or scenario/corner (0010)
    ed = task / "files/evidence_D_role_mismatch.json"; d = json.loads(ed.read_text())
    ed_sk = "op_point" if src_variant == "ambiguous" else "scenario"
    ed_ck = "mode" if src_variant == "ambiguous" else "corner"
    role_replace_json(d, [ed_sk], "swap_scen_slot", count)
    role_replace_json(d, [ed_ck], "swap_corner_slot", count)
    # recompute evidence_D's claimed flow_config hash to the (relabelled) mutant flow_config hash
    d["input_hashes"]["flow_config.json"] = sha_file(fc)
    ed.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    # solution/flow_config (golden)
    sf = task / "solution/flow_config.json"; d = json.loads(sf.read_text())
    role_replace_json(d, ["scenario"], "golden_scenario", count)
    role_replace_json(d, ["corner"], "golden_corner", count)
    d["_comment"] = "Restored to the global authority: netlist_v2 + clk_main + typ/test."
    sf.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")

def transform_truth(task: Path, count):
    tr = task / "hidden/handoff_truth.json"; d = json.loads(tr.read_text())
    role_replace_json(d, ["scenario"], "golden_scenario", count)
    role_replace_json(d, ["corner"], "golden_corner", count)
    role_replace_json(d, ["expected_scenario"], "golden_scenario", count)
    role_replace_json(d, ["expected_corner"], "golden_corner", count)
    role_replace_json(d, ["stale_scenario"], "swap_scen_slot", count)
    role_replace_json(d, ["stale_corner"], "swap_corner_slot", count)
    role_replace_json(d, ["global_authority_tuple", 2], "golden_scenario", count)
    role_replace_json(d, ["global_authority_tuple", 3], "golden_corner", count)
    role_replace_json(d, ["decoy_embedded_values", "report_A_role_swap.rpt", "scenario_slot"], "swap_scen_slot", count)
    role_replace_json(d, ["decoy_embedded_values", "report_A_role_swap.rpt", "corner_slot"], "swap_corner_slot", count)
    role_replace_json(d, ["decoy_embedded_values", "report_C_role_pvt.rpt", "scenario_slot"], "golden_scenario", count)
    role_replace_json(d, ["decoy_embedded_values", "report_C_role_pvt.rpt", "corner_slot"], "pvt_label", count)
    role_replace_json(d, ["axis_schema", "expected_unique_assignment", "scenario"], "golden_scenario", count)
    role_replace_json(d, ["axis_schema", "expected_unique_assignment", "corner"], "golden_corner", count)
    # C5 constraint allowed: [[slow,func]] -> [[typ,test]]  (list-of-lists)
    c5 = d["axis_schema"]["constraints"][4]
    assert c5["id"] == "C5", f"C5 not at index 4: {c5}"
    if c5["allowed"] != [["slow", "func"]]:
        raise FailClosed(f"C5 allowed not [[slow,func]]: {c5['allowed']}")
    c5["allowed"] = [[GOLDEN[0], GOLDEN[1]]]
    count["golden_scenario"] = count.get("golden_scenario", 0) + 1
    count["golden_corner"] = count.get("golden_corner", 0) + 1
    sa = d["axis_schema"]["uniqueness"]["satisfying_assignments"][0]
    if (sa.get("scenario"), sa.get("corner")) != ("slow", "func"):
        raise FailClosed(f"satisfying_assignments[0] not slow/func: {sa}")
    sa["scenario"], sa["corner"] = GOLDEN
    # variant/authority_source provenance text: tag as held-out (no value content changed besides labels)
    d["variant"] = d.get("variant", "") + "_heldout"
    d["authority_source"] = d.get("authority_source", "") + " (held-out golden typ/test)"
    tr.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")

def transform_reports(task: Path, count, src_variant: str):
    """Report + prev_signoff line-anchor relabel. src_variant in {ambiguous, clear}."""
    # shipped-header keys: ambiguous -> op_point/mode ; clear -> scenario/corner
    sk, ck = ("op_point", "mode") if src_variant == "ambiguous" else ("scenario", "corner")
    repA = task / "files/report_A_role_swap.rpt"; t = repA.read_text()
    t = role_replace_line(t, "netlist_v2.v  clock=clk_main", sk, "swap_scen_slot", count)   # shipped swap header
    t = role_replace_line(t, "netlist_v2.v  clock=clk_main", ck, "swap_corner_slot", count)
    t = role_replace_line(t, "clock=clk_main scenario=", "scenario", "golden_scenario", count)  # body header (canonical)
    t = role_replace_line(t, "clock=clk_main scenario=", "corner", "golden_corner", count)
    repA.write_text(t)
    repB = task / "files/report_B_role_stale.rpt"; t = repB.read_text()
    t = role_replace_line(t, "netlist_v1.v  clock=clk_main", sk, "golden_scenario", count)
    t = role_replace_line(t, "netlist_v1.v  clock=clk_main", ck, "golden_corner", count)
    t = role_replace_line(t, "clock=clk_old scenario=", "scenario", "swap_scen_slot", count)
    t = role_replace_line(t, "clock=clk_old scenario=", "corner", "swap_corner_slot", count)
    repB.write_text(t)
    repC = task / "files/report_C_role_pvt.rpt"; t = repC.read_text()
    t = role_replace_line(t, "netlist_v2.v  clock=clk", sk, "golden_scenario", count)
    t = role_replace_line(t, "netlist_v2.v  clock=clk", ck, "pvt_label", count)
    t = role_replace_line(t, "clock=clk_old scenario=", "scenario", "swap_scen_slot", count)
    t = role_replace_line(t, "clock=clk_old scenario=", "corner", "swap_corner_slot", count)
    repC.write_text(t)
    pv = task / "files/prev_signoff.log"; t = pv.read_text()
    pv_sk = "op_point" if src_variant == "ambiguous" else "scenario"
    pv_ck = "mode" if src_variant == "ambiguous" else "corner"
    # prev_signoff carries each value on its own line; needle = the key itself
    t = role_replace_line(t, pv_sk, pv_sk, "swap_scen_slot", count)
    t = role_replace_line(t, pv_ck, pv_ck, "swap_corner_slot", count)
    pv.write_text(t)

def transform_spec_clear(task: Path, count):
    """0010 -> 0012: also remap the C6 signoff-pair assertion bullet to typ/test."""
    spec = task / "files/spec.md"; t = spec.read_text()
    c6 = "- The setup signoff is taken at the **slow scenario** in the **functional corner**."
    c6new = "- The setup signoff is taken at the **typ scenario** in the **test corner**."
    if c6 not in t: raise FailClosed("C6 bullet not found in 0010 spec.md")
    t = t.replace(c6, c6new, 1)
    spec.write_text(t)
    count["golden_scenario"] = count.get("golden_scenario", 0) + 1
    count["golden_corner"] = count.get("golden_corner", 0) + 1

def patch_meta(task: Path, new_id: str, note: str):
    mf = task / "metadata.json"; md = json.loads(mf.read_text())
    md["phase4w_heldout"] = note; md["task_id"] = new_id
    mf.write_text(json.dumps(md, indent=2, ensure_ascii=False) + "\n")

def generate_once(src: Path, dst: Path, new_id: str, src_variant: str, is_clear: bool) -> dict:
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src, dst)
    count = {}
    transform_common_json(dst, count, src_variant)
    transform_truth(dst, count)
    transform_reports(dst, count, src_variant)
    if is_clear:
        transform_spec_clear(dst, count)
    patch_meta(dst, new_id, f"held-out pair: {src.name} relabelled to golden typ/test ({src_variant})")
    return count

EXPECTED_COUNTS = {  # per-role minimum counts satisfied across the transformation
    "golden_scenario": 10, "golden_corner": 10, "swap_scen_slot": 7,
    "swap_corner_slot": 7, "pvt_label": 2,
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(TRACK))
    args = ap.parse_args()
    out = Path(args.out)
    # fail-closed: source commit + source hashes
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != EXPECTED_COMMIT:
        raise FailClosed(f"HEAD {head} != expected source commit {EXPECTED_COMMIT}")
    for tag, p in [("0009/flow_config", "workflow_handoff_0009/files/flow_config.json"),
                   ("0010/flow_config", "workflow_handoff_0010/files/flow_config.json"),
                   ("0009/truth", "workflow_handoff_0009/hidden/handoff_truth.json"),
                   ("0010/truth", "workflow_handoff_0010/hidden/handoff_truth.json")]:
        h = sha_file(TRACK / p)
        if h != SRC_HASHES[tag]:
            raise FailClosed(f"source hash mismatch {tag}: {h} != {SRC_HASHES[tag]}")
    # determinism: generate twice in independent temp dirs, require byte-identical
    plans = [("workflow_handoff_0009", "workflow_handoff_0011", "ambiguous", False),
             ("workflow_handoff_0010", "workflow_handoff_0012", "clear_control", True)]
    counts = {}
    runs = {}
    for runtmp in ["determ_a", "determ_b"]:
        tmp = Path(tempfile.mkdtemp(prefix=f"phase4w_{runtmp}_"))
        run_out = {}
        for src_id, new_id, variant, is_clear in plans:
            c = generate_once(TRACK / src_id, tmp / new_id, new_id, variant, is_clear)
            run_out[new_id] = c
        runs[runtmp] = run_out
        shutil.rmtree(tmp)
    # both runs must report identical role counts
    if runs["determ_a"] != runs["determ_b"]:
        raise FailClosed(f"non-deterministic counts:\nA={runs['determ_a']}\nB={runs['determ_b']}")
    counts = runs["determ_a"]
    # now generate for real into --out, then re-verify against the deterministic counts
    final_counts = {}
    for src_id, new_id, variant, is_clear in plans:
        c = generate_once(TRACK / src_id, out / new_id, new_id, variant, is_clear)
        # sum per-role across the pair
        for r, n in c.items(): final_counts[r] = final_counts.get(r, 0) + n
    # assert expected per-role counts (each variant contributes a known amount)
    for r, lo in EXPECTED_COUNTS.items():
        # totals across BOTH variants (0011+0012)
        if final_counts.get(r, 0) < lo:
            raise FailClosed(f"role {r}: total {final_counts.get(r)} < expected min {lo}")
    # byte-identical determinism proof: regen into a second temp and diff against the real output
    tmp = Path(tempfile.mkdtemp(prefix="phase4w_verify_"))
    for src_id, new_id, variant, is_clear in plans:
        generate_once(TRACK / src_id, tmp / new_id, new_id, variant, is_clear)
        d = subprocess.run(["diff", "-rq", str(out / new_id), str(tmp / new_id)], capture_output=True, text=True)
        if d.stdout.strip():
            raise FailClosed(f"non-byte-identical {new_id}:\n{d.stdout}")
    shutil.rmtree(tmp)
    # emit manifest
    manifest = {
        "generator": "scripts/gen_phase4w_heldout.py",
        "generator_sha256": sha_file(REPO / "scripts/gen_phase4w_heldout.py"),
        "source_commit": EXPECTED_COMMIT,
        "source_hashes": SRC_HASHES,
        "role_map": {k: {"src": v[0], "tgt": v[1]} for k, v in ROLE_MAP.items()},
        "golden_heldout": list(GOLDEN),
        "per_variant_role_counts": counts,
        "total_role_counts": final_counts,
        "expected_min_counts": EXPECTED_COUNTS,
        "outputs": {
            "workflow_handoff_0011": {"derived_from": "workflow_handoff_0009", "variant": "ambiguous",
                                       "tree_sha256": _tree_sha(out / "workflow_handoff_0011")},
            "workflow_handoff_0012": {"derived_from": "workflow_handoff_0010", "variant": "clear_control",
                                       "tree_sha256": _tree_sha(out / "workflow_handoff_0012")},
        },
        "determinism": "regenerated twice in independent temp dirs + byte-identical verify pass",
    }
    (REPO / "reports/evidence/p14_phase4w_heldout/MANIFEST.json").parent.mkdir(parents=True, exist_ok=True)
    (REPO / "reports/evidence/p14_phase4w_heldout/MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"ok": True, "counts": final_counts, "per_variant": counts,
                      "0011_tree": manifest["outputs"]["workflow_handoff_0011"]["tree_sha256"][:16],
                      "0012_tree": manifest["outputs"]["workflow_handoff_0012"]["tree_sha256"][:16]}, indent=2))

def _tree_sha(d: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(d.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(d)).encode()); h.update(b"\0"); h.update(f.read_bytes()); h.update(b"\0")
    return h.hexdigest()

if __name__ == "__main__":
    try:
        main()
    except FailClosed as e:
        print("FAIL-CLOSED:", e, file=sys.stderr); sys.exit(1)
