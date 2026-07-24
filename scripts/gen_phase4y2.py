#!/usr/bin/env python3
"""Phase-4Y Stage-2 variant generator: C1/Axis-schema (0020) vs C24/Value-schema (0021), from 0009.

Clause-level component boundary (review methodology, same as Stage 1): extract only already-frozen
pure-component clauses verbatim from BundleS/Schema (0015/0018); mixed sentences are clause-separated
(their other-component portion stays at the 0009 baseline); no invented/smoothed prose; a HARD
semantic-diff gate classifies every delta clause.

  0020 / C1  = 0009 + canonical scenario/corner labels + disjoint-axis declaration (exclude C2-C7)
  0021 / C24 = 0009 + C2 PVT definition + C4 glossary + frozen C4 references (exclude C1,C3,C5-C7)

C1 takes the frozen canonical-labels prompt clause; C24 takes the frozen 'glossary.md states the
disjoint typed axes' prompt clause; each leaves the other's portion at the 0009 baseline. C1 renames
the report labels (canonical); C24 keeps op_point/mode reports (C1 excluded) and supplies the value
schema via glossary.md + PVT-def.
"""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4y2"
EXPECTED_COMMIT = "751e38f"
SRC_HASHES = {"0009/flow_config": "65d3682943022f6306a5ef1391d322a03695cb7c285c364b1aa50f983d75b203"}

# ---- C1: canonical labels + disjoint-axis declaration (frozen from 0018) ----
C1_REPORT_FILES = ["report_A_role_swap.rpt", "report_B_role_stale.rpt", "report_C_role_pvt.rpt",
                   "evidence_D_role_mismatch.json"]
C1_SPEC_OLD = "- The shipped reports use two field labels: `op_point=` / `mode=`. Their meaning is NOT defined here -- infer it from how the values are used across the (conflicting) report sources."
C1_SPEC_NEW = "- The reports carry a **scenario** field (`scenario=`) and a **corner** field (`corner=`). These are DISJOINT typed axes: a value valid on one is invalid on the other."
C1_PROMPT_OLD = "The reports use field labels `op_point` / `mode` whose logical-axis role is NOT defined upfront"
C1_PROMPT_NEW = "The reports use canonical `scenario` / `corner` labels"

# ---- C2: PVT-descriptor definition (frozen from 0018) ----
C2_PVT_LINE = "- A **PVT descriptor** (e.g. `slow_1.0V_125C`) is a string `<process>_<voltage>_<temperature>` that **characterizes** a (scenario, corner) pair but is **never** a valid scenario or corner value."
C2_CLOCK_OLD = "- The consumed clock is the one that yields non-zero intended-clock path coverage on the design."

# ---- C4: glossary + frozen references (from 0018) ----
C4_SPEC_TERM_OLD = "## Terminology"
C4_SPEC_TERM_NEW = "## Terminology (partial; see glossary.md for examples -- NOT a complete schema)"
C4_SPEC_BULLET = "- `glossary.md` — INCOMPLETE terminology examples (NOT a schema)."
C4_SPEC_BULLET_ANCHOR = "- `evidence_D_role_mismatch.json` — valid-looking chain; the role fields are swapped inside."
C4_SPEC_FORBID_OLD = "- Editing the netlists, library, manifest generators, or runners; weakening `constraints.sdc`."
C4_SPEC_FORBID_NEW = "- Editing the netlists, library, manifest, glossary, generators, or runners; weakening `constraints.sdc`."
C4_PROMPT_OLD = "(no glossary or summary is provided)"
C4_PROMPT_NEW = "(glossary.md states the disjoint typed axes)"
C4_PROMPT_FORBID_OLD = "the manifest the decoy reports"
C4_PROMPT_FORBID_NEW = "the manifest, `glossary.md`, the decoy reports"

C1_MARKERS = ("scenario=", "corner=", "DISJOINT typed axes", "canonical `scenario`")
C24_MARKERS = ("PVT descriptor", "glossary")


class FailClosed(Exception):
    pass


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _replace_once(text, old, new, label):
    if old not in text:
        raise FailClosed(f"anchor not found for {label}: {old[:60]}")
    if text.count(old) != 1:
        raise FailClosed(f"anchor not unique for {label} (count={text.count(old)})")
    return text.replace(old, new, 1)


def build_c1(out):
    s = out / "workflow_handoff_0020"
    if s.exists():
        shutil.rmtree(s)
    shutil.copytree(TRACK / "workflow_handoff_0009", s)
    for f in C1_REPORT_FILES:  # C1 canonical-label reports (frozen from 0018)
        shutil.copy2(TRACK / "workflow_handoff_0018" / "files" / f, s / "files" / f)
    spec = (s / "files/spec.md").read_text()
    spec = _replace_once(spec, C1_SPEC_OLD, C1_SPEC_NEW, "C1 spec")
    (s / "files/spec.md").write_text(spec)
    prompt = (s / "prompt.md").read_text()
    prompt = _replace_once(prompt, C1_PROMPT_OLD, C1_PROMPT_NEW, "C1 prompt clause")
    (s / "prompt.md").write_text(prompt)
    _patch_meta(s, "workflow_handoff_0020", "C1 = 0009 + canonical labels + disjoint-axis decl (no C2-C7)")


def build_c24(out):
    c = out / "workflow_handoff_0021"
    if c.exists():
        shutil.rmtree(c)
    shutil.copytree(TRACK / "workflow_handoff_0009", c)
    shutil.copy2(TRACK / "workflow_handoff_0018" / "files" / "glossary.md", c / "files" / "glossary.md")
    spec = (c / "files/spec.md").read_text()
    spec = _replace_once(spec, C2_CLOCK_OLD, C2_PVT_LINE + "\n" + C2_CLOCK_OLD, "C2 PVT insert")
    spec = _replace_once(spec, C4_SPEC_TERM_OLD, C4_SPEC_TERM_NEW, "C4 spec term")
    spec = _replace_once(spec, C4_SPEC_BULLET_ANCHOR, C4_SPEC_BULLET_ANCHOR + "\n" + C4_SPEC_BULLET, "C4 spec bullet")
    spec = _replace_once(spec, C4_SPEC_FORBID_OLD, C4_SPEC_FORBID_NEW, "C4 spec forbid")
    (c / "files/spec.md").write_text(spec)
    prompt = (c / "prompt.md").read_text()
    prompt = _replace_once(prompt, C4_PROMPT_OLD, C4_PROMPT_NEW, "C4 prompt clause")
    prompt = _replace_once(prompt, C4_PROMPT_FORBID_OLD, C4_PROMPT_FORBID_NEW, "C4 prompt forbid")
    (c / "prompt.md").write_text(prompt)
    _patch_meta(c, "workflow_handoff_0021", "C24 = 0009 + C2 PVT-def + C4 glossary (no C1,C3,C5-C7)")


def _patch_meta(task, tid, note):
    mf = task / "metadata.json"
    md = json.loads(mf.read_text())
    md["task_id"] = tid
    md["phase4y2"] = note
    mf.write_text(json.dumps(md, indent=2, ensure_ascii=False) + "\n")


def semantic_diff_gate(out):
    import difflib
    base_spec = (TRACK / "workflow_handoff_0009/files/spec.md").read_text().splitlines()
    base_prompt = (TRACK / "workflow_handoff_0009/prompt.md").read_text().splitlines()
    verdict = {"0020": [], "0021": []}
    for tid, label in [("workflow_handoff_0020", "0020"), ("workflow_handoff_0021", "0021")]:
        for fname, base in [("files/spec.md", base_spec), ("prompt.md", base_prompt)]:
            new = (TRACK / tid / fname).read_text().splitlines()
            for ln in difflib.unified_diff(base, new, lineterm="", n=0):
                if ln.startswith(("---", "+++", "@@")):
                    continue
                verdict[label].append({"file": fname, "line": ln[1:], "kind": "added" if ln.startswith("+") else "removed"})
    # 0020 (C1): added lines C1-bearing. The authoritative C2/C4-exclusion check is precise (not a
    # crude marker scan): 0020 must have NO glossary.md, NO PVT-def in spec, and NOT the C4 prompt
    # clause. The bare word "glossary" in 0009's retained negation "(no glossary or summary is
    # provided)" is 0009 baseline, not a C4 addition, and must not trip the gate.
    for d in [d for d in verdict["0020"] if d["kind"] == "added"]:
        if not any(m in d["line"] for m in C1_MARKERS):
            raise FailClosed(f"0020 added line not C1-bearing: {d}")
    if (TRACK / "workflow_handoff_0020/files/glossary.md").exists():
        raise FailClosed("0020 must NOT add glossary.md (C4)")
    sp20 = (TRACK / "workflow_handoff_0020/files/spec.md").read_text()
    if "<process>_<voltage>_<temperature>" in sp20 or "see glossary.md" in sp20:
        raise FailClosed("0020 leaks C2 (PVT def) / C4 (glossary ref) into spec")
    p20 = (TRACK / "workflow_handoff_0020/prompt.md").read_text()
    if "glossary.md states the disjoint typed axes" in p20:
        raise FailClosed("0020 leaks the C4 prompt clause")
    # 0021 (C24): added lines C2/C4-bearing; reports byte-identical to 0009 (no C1 canonical rename)
    for d in [d for d in verdict["0021"] if d["kind"] == "added"]:
        if not any(m in d["line"] for m in C24_MARKERS):
            raise FailClosed(f"0021 added line not C2/C4-bearing: {d}")
    edited = {"files/spec.md", "prompt.md", "metadata.json"}
    for f in sorted((TRACK / "workflow_handoff_0021").rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(TRACK / "workflow_handoff_0021"))
        src = TRACK / "workflow_handoff_0009" / rel
        if rel not in edited and rel != "files/glossary.md":
            if not src.is_file() or src.read_bytes() != f.read_bytes():
                raise FailClosed(f"0021 {rel} differs from 0009 baseline (C24 must not touch non-C2/C4 files)")
    # 0021 reports byte-identical to 0009 (authoritative C1-exclusion guard; the non-edited loop above
    # already enforces this). NOTE: 0009 baseline reports contain 'scenario='/'corner=' in their inner
    # stage-1 stamp, so a bare scenario= scan is not a valid C1-leak marker -- byte-equality is.
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(TRACK))
    a = ap.parse_args()
    out = Path(a.out)
    OUT.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if not head.startswith(EXPECTED_COMMIT):
        raise FailClosed(f"HEAD {head} != {EXPECTED_COMMIT}*")
    for tag, p in SRC_HASHES.items():
        if sha_file(TRACK / f"workflow_handoff_{tag.split('/')[0]}/files/flow_config.json") != p:
            raise FailClosed(f"source hash mismatch {tag}")
    build_c1(out)
    build_c24(out)
    verdict = semantic_diff_gate(out)
    rec = {"c1_operational_definition": "canonical scenario/corner labels + disjoint-axis declaration (clause-level; excludes C2-C7)",
           "c24_operational_definition": "C2 PVT definition + C4 glossary + frozen C4 references (clause-level; excludes C1,C3,C5-C7)",
           "clause_extraction_note": "mixed prompt-line-3 clause-separated: C1 takes 'canonical scenario/corner labels', C24 takes 'glossary.md states the disjoint typed axes'; each leaves the other portion at the 0009 baseline. No invented/smoothed prose.",
           "semantic_diff_gate": "PASS (0020 C1-only no-C2/C4; 0021 C24-only no-C1, reports op_point/mode)",
           "diffs": verdict}
    (OUT / "component_classification.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({"ok": True, "variants": ["workflow_handoff_0020 (C1)", "workflow_handoff_0021 (C24)"],
                      "semantic_diff_gate": "PASS", "source_commit": head}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except FailClosed as e:
        print("FAIL-CLOSED:", e, file=sys.stderr)
        sys.exit(1)
