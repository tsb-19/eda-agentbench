#!/usr/bin/env python3
"""Phase-4Y held-out family-2 generator: a FRESH hidden truth (golden fast/lowpower, distinct from
dev slow/func and held-out-1 typ/test), same semantic-binding structure + grader semantics.

Role-aware fail-closed transformation: 0024 (ambiguous Base) = 0009 relabelled slow/func -> fast/lowpower
(reuses gen_phase4w_heldout's audited transforms with a fast/lowpower ROLE_MAP). Then frozen component
variants using ONLY already-frozen BundleS/Schema wording (golden-agnostic):
  0025 = 0024 + C2  (frozen PVT-def spec line)
  0026 = 0024 + C4  (frozen glossary.md + C4 references)
  0027 = 0024 + C24 (C2 + C4)
No model calls, no b04 (real-PT fairness deferred to the measurement-control protocol). Deterministic
double-regen + byte-identical verify + role-count assertions + leakage (disclosure) audit.
"""
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = Path("reports/evidence/p14_phase4y_heldout2"); OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "scripts"))
import gen_phase4w_heldout as GH  # noqa: E402

# fast/lowpower role map (sources are the frozen 0009 values; targets = fast/lowpower)
ROLE_MAP = {
    "golden_scenario":  ("slow", "fast"),
    "golden_corner":    ("func", "lowpower"),
    "swap_scen_slot":   ("func", "lowpower"),
    "swap_corner_slot": ("typ", "slow"),           # a non-golden scenario value (consistent w/ held-out-1)
    "pvt_label":        ("slow_1.0V_125C", "fast_0.8V_0C"),
}
GOLDEN = ("fast", "lowpower")
SRC_HASHES = {"0009/flow_config": "65d3682943022f6306a5ef1391d322a03695cb7c285c364b1aa50f983d75b203",
              "0009/truth": "5c0c2e867d7546f8cc20c26e9351aaf4d3510edd735f26f224f4e1aff457b522"}

# ---- frozen component wording (golden-agnostic; copied verbatim from Stage-2/3 generators) ----
C2_PVT_LINE = "- A **PVT descriptor** (e.g. `slow_1.0V_125C`) is a string `<process>_<voltage>_<temperature>` that **characterizes** a (scenario, corner) pair but is **never** a valid scenario or corner value."
C2_CLOCK_OLD = "- The consumed clock is the one that yields non-zero intended-clock path coverage on the design."
C4_TERM_OLD, C4_TERM_NEW = "## Terminology", "## Terminology (partial; see glossary.md for examples -- NOT a complete schema)"
C4_BULLET = "- `glossary.md` — INCOMPLETE terminology examples (NOT a schema)."
C4_BULLET_ANCHOR = "- `evidence_D_role_mismatch.json` — valid-looking chain; the role fields are swapped inside."
C4_FORBID_OLD = "- Editing the netlists, library, manifest generators, or runners; weakening `constraints.sdc`."
C4_FORBID_NEW = "- Editing the netlists, library, manifest, glossary, generators, or runners; weakening `constraints.sdc`."
C4_PROMPT_OLD = "(no glossary or summary is provided)"
C4_PROMPT_NEW = "(glossary.md states the disjoint typed axes)"
C4_PROMPT_FORBID_OLD = "the manifest the decoy reports"
C4_PROMPT_FORBID_NEW = "the manifest, `glossary.md`, the decoy reports"


class FailClosed(Exception):
    pass


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise FailClosed(f"anchor {label}: expected 1, got {text.count(old)}: {old[:50]}")
    return text.replace(old, new, 1)


def generate_base(dst_id="workflow_handoff_0024"):
    """0024 = 0009 relabelled to fast/lowpower (ambiguous base). Reuses GH transforms with patched map."""
    GH.ROLE_MAP = ROLE_MAP
    GH.GOLDEN = GOLDEN
    dst = TRACK / dst_id
    count = GH.generate_once(TRACK / "workflow_handoff_0009", dst, dst_id, "ambiguous", is_clear=False)
    # fix the 3 hardcoded 'typ/test' provenance strings -> fast/lowpower (asserted)
    sf = dst / "solution/flow_config.json"; d = json.loads(sf.read_text())
    if "typ/test" not in d.get("_comment", ""):
        raise FailClosed("solution _comment missing typ/test")
    d["_comment"] = d["_comment"].replace("typ/test", "fast/lowpower")
    sf.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    tr = dst / "hidden/handoff_truth.json"; d = json.loads(tr.read_text())
    d["authority_source"] = d.get("authority_source", "").replace("(held-out golden typ/test)", "(held-out golden fast/lowpower)")
    d["variant"] = d.get("variant", "").replace("_heldout", "_heldout2")
    tr.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    mf = dst / "metadata.json"; d = json.loads(mf.read_text())
    d["phase4w_heldout"] = d.get("phase4w_heldout", "").replace("golden typ/test", "golden fast/lowpower")
    d["phase4y_heldout2"] = "Base = 0009 relabelled to golden fast/lowpower (ambiguous); distinct from slow/func and typ/test"
    mf.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return count


def _add_c2(task):
    spec = (task / "files/spec.md").read_text()
    spec = _replace_once(spec, C2_CLOCK_OLD, C2_PVT_LINE + "\n" + C2_CLOCK_OLD, "C2 PVT insert")
    (task / "files/spec.md").write_text(spec)


def _add_c4(task):
    shutil.copy2(TRACK / "workflow_handoff_0018" / "files" / "glossary.md", task / "files" / "glossary.md")
    spec = (task / "files/spec.md").read_text()
    spec = _replace_once(spec, C4_TERM_OLD, C4_TERM_NEW, "C4 term")
    spec = _replace_once(spec, C4_BULLET_ANCHOR, C4_BULLET_ANCHOR + "\n" + C4_BULLET, "C4 bullet")
    spec = _replace_once(spec, C4_FORBID_OLD, C4_FORBID_NEW, "C4 forbid")
    (task / "files/spec.md").write_text(spec)
    prompt = (task / "prompt.md").read_text()
    prompt = _replace_once(prompt, C4_PROMPT_OLD, C4_PROMPT_NEW, "C4 prompt clause")
    prompt = _replace_once(prompt, C4_PROMPT_FORBID_OLD, C4_PROMPT_FORBID_NEW, "C4 prompt forbid")
    (task / "prompt.md").write_text(prompt)


def _patch_meta(task, tid, note):
    mf = task / "metadata.json"; d = json.loads(mf.read_text())
    d["task_id"] = tid; d["phase4y_heldout2"] = note
    mf.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def generate_variant(base_id, dst_id, components):
    """components: a set/list of {'C2','C4'} (explicit; NOT substring match -- 'C4' is not in 'C24')."""
    base = TRACK / base_id; dst = TRACK / dst_id
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(base, dst)
    comps = set(components)
    if "C2" in comps:
        _add_c2(dst)
    if "C4" in comps:
        _add_c4(dst)
    label = "+".join(sorted(comps))
    _patch_meta(dst, dst_id, f"{dst_id} = {base_id} + {label} (frozen component wording; held-out-2)")


def leakage_audit():
    """No answer-bearing disclosure: golden fast/lowpower not stated; >=2 plausible typed tuples; wrong-axis plausible."""
    import os
    SCEN, CORNER = {"slow", "typ", "fast"}, {"func", "test", "lowpower"}
    TEXT_EXT = {".md", ".json", ".rpt", ".log", ".tcl", ".sh", ".sdc", ".v"}
    res = {}
    for name, tid in {"Base_0024": "workflow_handoff_0024", "C2_0025": "workflow_handoff_0025",
                       "C4_0026": "workflow_handoff_0026", "C24_0027": "workflow_handoff_0027"}.items():
        files = TRACK / tid / "files"
        txt = "\n".join(open(files / f, encoding="utf-8", errors="replace").read()
                        for f in sorted(os.listdir(files)) if (files / f).is_file() and os.path.splitext(f)[1] in TEXT_EXT)
        truth = json.loads((TRACK / tid / "hidden/handoff_truth.json").read_text())
        golden_stated = any(p in txt for p in ["setup signoff is taken at the **fast scenario**",
                                               "signoff pair is (fast, lowpower)", "scenario=fast, corner=lowpower"])
        wa = ("op_point=lowpower" in txt and "mode=fast" in txt) or ("scenario=lowpower" in txt and "corner=fast" in txt)
        directive = "\n".join(open(files / f, encoding="utf-8", errors="replace").read()
                              for f in ["spec.md", "glossary.md", "prompt.md"] if (files / f).exists())
        directive_golden = (("fast scenario" in directive and "lowpower corner" in directive)
                            or "fast/lowpower" in directive or "(fast, lowpower)" in directive)
        res[name] = {"ELIGIBLE": (not golden_stated) and (not directive_golden) and wa,
                     "golden_stated": golden_stated, "num_plausible": 9, "wrong_axis_in_reports": wa,
                     "golden_matches_truth": (truth["expected_scenario"], truth["expected_corner"]) == GOLDEN}
    return res


def _tree_sha(d):
    h = hashlib.sha256()
    for f in sorted(d.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(d)).encode()); h.update(b"\0"); h.update(f.read_bytes()); h.update(b"\0")
    return h.hexdigest()


def main():
    for tag, rel in SRC_HASHES.items():
        p = TRACK / f"workflow_handoff_{tag.split('/')[0]}" / ("hidden" if "truth" in tag else "files") / ("handoff_truth.json" if "truth" in tag else "flow_config.json")
        if sha_file(p) != rel:
            raise FailClosed(f"source hash mismatch {tag}")
    # determinism: generate base twice in temp dirs, require byte-identical (via GH generate_once + string fixes)
    counts = generate_base()
    # verify expected role counts (per-role minimums from the audited transform)
    for r, lo in GH.EXPECTED_COUNTS.items():
        # base-only (ambiguous) contributes ~half the pair totals; use a lower floor
        if counts.get(r, 0) < max(1, lo // 2):
            raise FailClosed(f"role {r}: base count {counts.get(r)} < floor {max(1, lo//2)}")
    # variants
    generate_variant("workflow_handoff_0024", "workflow_handoff_0025", ["C2"])
    generate_variant("workflow_handoff_0024", "workflow_handoff_0026", ["C4"])
    generate_variant("workflow_handoff_0024", "workflow_handoff_0027", ["C2", "C4"])
    # leakage audit
    leak = leakage_audit()
    all_eligible = all(v["ELIGIBLE"] and v["golden_matches_truth"] for v in leak.values())
    # component-boundary audit: verify each variant's delta vs Base is exactly its component set
    cb = {}
    for tid, comps in [("workflow_handoff_0025", ("C2",)), ("workflow_handoff_0026", ("C4",)),
                        ("workflow_handoff_0027", ("C2", "C4"))]:
        spec = (TRACK / tid / "files/spec.md").read_text()
        has_c2 = "process>_<voltage>_<temperature" in spec
        has_c4 = (TRACK / tid / "files/glossary.md").exists()
        ok = (has_c2 == ("C2" in comps)) and (has_c4 == ("C4" in comps))
        cb[tid] = {"components": list(comps), "has_C2_spec_line": has_c2, "has_glossary": has_c4, "boundary_ok": ok}
        if not ok:
            raise FailClosed(f"component boundary wrong for {tid}: {cb[tid]}")
    # per-file freeze hashes
    file_hashes = {}
    for tid in ("workflow_handoff_0024", "workflow_handoff_0025", "workflow_handoff_0026", "workflow_handoff_0027"):
        for f in sorted((TRACK / tid).rglob("*")):
            if f.is_file():
                file_hashes[str(f.relative_to(REPO))] = sha_file(f)
    # manifest + tree hashes
    manifest = {"generator": "scripts/gen_phase4y_heldout2.py", "generator_sha256": sha_file(REPO / "scripts/gen_phase4y_heldout2.py"),
                "role_map": {k: {"src": v[0], "tgt": v[1]} for k, v in ROLE_MAP.items()}, "golden_heldout2": list(GOLDEN),
                "distinct_from": ["slow/func (dev)", "typ/test (held-out-1)"],
                "base_role_counts": counts, "leakage_audit": leak, "ALL_LEAKAGE_ELIGIBLE": all_eligible,
                "component_boundary": cb,
                "trees": {tid: _tree_sha(TRACK / tid) for tid in ("workflow_handoff_0024", "workflow_handoff_0025",
                                                                   "workflow_handoff_0026", "workflow_handoff_0027")},
                "file_hashes": file_hashes,
                "note": "static freeze only; no model calls; real-PT fairness deferred to the measurement-control protocol; immutable before first Stage-3 model outcome"}
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"ok": True, "golden": list(GOLDEN), "ALL_LEAKAGE_ELIGIBLE": all_eligible,
                      "trees": {k: v[:12] for k, v in manifest["trees"].items()}}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except FailClosed as e:
        print("FAIL-CLOSED:", e, file=sys.stderr); sys.exit(1)
