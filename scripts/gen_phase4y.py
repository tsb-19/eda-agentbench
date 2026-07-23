#!/usr/bin/env python3
"""Phase-4Y Stage-1 variant generator: Schema (0018) vs Contract (0019), both from frozen 0009.

CLAUSE-LEVEL C7 BOUNDARY (review-directed, 2026-07-23):
  C7 = ONLY pure procedural-contract clauses: frozen wording that instructs the agent to resolve/infer
  semantic roles or assignments from the available evidence/constraints (the handoff/reasoning
  contract). C7 EXCLUDES all schema-bearing material (canonical labels, disjoint-axis declarations,
  PVT definitions, glossary content/references, value-to-axis definitions, schema-bearing
  parentheticals). Mixed sentences that cannot be clause-separated without inventing wording are LEFT
  AT THE 0009 BASELINE in both variants (experimental isolation > textual smoothness).

  0018 / Schema    = 0009 + exactly C1 + C2 + C4  (no C7 procedural-contract delta)
  0019 / Contract = 0009 + exactly pure C7         (no C1/C2/C4; no answer/decoy-filter additions)

All OLD/NEW strings are byte-copied from frozen 0009/0015 (no invented text). A HARD SEMANTIC-DIFF
GATE classifies every delta clause and asserts: 0018 deltas are schema-bearing only (no new C7 vs
0009); 0019 deltas are contract-bearing only (no new schema/answer/decoy). Fail-closed on any leak.

C1 canonical labels for reports are applied by copying 0015's frozen report/evidence_D files verbatim
(verified == 0009's files under op_point->scenario / mode->corner).
"""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4y"
EXPECTED_COMMIT = "67199e3"  # infra-fixes HEAD (membership code + executor frozen here)

# ---- frozen source hashes (0009 baseline + 0015 for C1 report files) ----
SRC_HASHES = {
    "0009/flow_config": "65d3682943022f6306a5ef1391d322a03695cb7c285c364b1aa50f983d75b203",
    "0015/flow_config": "6fe91510716dfa8eaff9e8fd476b11939e6608c54187c4883707cf0af7a4b6e6",
}

# ---- C1 (canonical labels + disjoint-axes declaration) -- spec/prompt frozen strings ----
C1_SPEC_OLD = "- The shipped reports use two field labels: `op_point=` / `mode=`. Their meaning is NOT defined here -- infer it from how the values are used across the (conflicting) report sources."
C1_SPEC_NEW = "- The reports carry a **scenario** field (`scenario=`) and a **corner** field (`corner=`). These are DISJOINT typed axes: a value valid on one is invalid on the other."
C1_PROMPT_OLD = "The reports use field labels `op_point` / `mode` whose logical-axis role is NOT defined upfront -- resolve it from the report intersection (no glossary or summary is provided)."
C1_PROMPT_NEW = "The reports use canonical `scenario` / `corner` labels; glossary.md states the disjoint typed axes."

# ---- C2 (PVT-descriptor definition) -- frozen string, inserted before the clock line ----
C2_PVT_LINE = "- A **PVT descriptor** (e.g. `slow_1.0V_125C`) is a string `<process>_<voltage>_<temperature>` that **characterizes** a (scenario, corner) pair but is **never** a valid scenario or corner value."
C2_CLOCK_OLD = "- The consumed clock is the one that yields non-zero intended-clock path coverage on the design."

# ---- C4 (glossary) -- frozen references ----
C4_SPEC_TERM_OLD = "## Terminology"
C4_SPEC_TERM_NEW = "## Terminology (partial; see glossary.md for examples -- NOT a complete schema)"
C4_SPEC_BULLET = "- `glossary.md` — INCOMPLETE terminology examples (NOT a schema)."
C4_SPEC_BULLET_ANCHOR = "- `evidence_D_role_mismatch.json` — valid-looking chain; the role fields are swapped inside."
C4_SPEC_FORBID_OLD = "- Editing the netlists, library, manifest generators, or runners; weakening `constraints.sdc`."
C4_SPEC_FORBID_NEW = "- Editing the netlists, library, manifest, glossary, generators, or runners; weakening `constraints.sdc`."
C4_PROMPT_FORBID_OLD = "the manifest the decoy reports"
C4_PROMPT_FORBID_NEW = "the manifest, `glossary.md`, the decoy reports"

# ---- C7 (pure procedural-contract) -- clause-level frozen swaps ----
# spec: keep 0009's schema-absence clause; swap ONLY the procedural clause to 0015's frozen wording.
C7_SPEC_OLD = "**No value-to-axis mapping is provided.** Resolve the role of each label from the evidence."
C7_SPEC_NEW = "**No value-to-axis mapping is provided.** Infer the unique assignment from the constraints."
# prompt step 1: 0015's frozen pure-contract version (drops the 0009 "Resolve the semantic role..." clause).
C7_PROMPT_OLD = "1. Resolve the semantic role of each report field label from the report intersection. Then Infer the unique assignment by intersecting C1–C5; do NOT trust any single shipped source (each decoy is pairwise plausible but role-mismatched)."
C7_PROMPT_NEW = "1. Infer the unique assignment by intersecting C1–C5; do NOT trust any single shipped source (each decoy is pairwise plausible but role-mismatched)."

C1_REPORT_FILES = ["report_A_role_swap.rpt", "report_B_role_stale.rpt", "report_C_role_pvt.rpt",
                   "evidence_D_role_mismatch.json"]
SCHEMA_MARKERS = ("scenario=", "corner=", "scenario slot", "corner slot", "PVT descriptor",
                  "glossary", "DISJOINT typed axes", "disjoint typed axes", "value-to-axis table")
CONTRACT_MARKERS = ("Infer the unique assignment",)  # shared stem of both frozen C7 clauses
# (spec: "...from the constraints"; prompt: "...by intersecting C1-5")


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


def build_schema(out):
    """0018 = 0009 + C1 + C2 + C4. Reports via frozen 0015 files; spec/prompt via frozen strings."""
    s = out / "workflow_handoff_0018"
    if s.exists():
        shutil.rmtree(s)
    shutil.copytree(TRACK / "workflow_handoff_0009", s)
    # C1 reports: copy 0015's frozen canonical-label report files verbatim
    for f in C1_REPORT_FILES:
        shutil.copy2(TRACK / "workflow_handoff_0015" / "files" / f, s / "files" / f)
    shutil.copy2(TRACK / "workflow_handoff_0015" / "files" / "glossary.md", s / "files" / "glossary.md")  # C4
    # spec.md: C1 (S3), C2 (insert PVT), C4 (term header, glossary bullet, forbid list)
    spec = (s / "files/spec.md").read_text()
    spec = _replace_once(spec, C1_SPEC_OLD, C1_SPEC_NEW, "C1 spec")
    spec = _replace_once(spec, C2_CLOCK_OLD, C2_PVT_LINE + "\n" + C2_CLOCK_OLD, "C2 PVT insert")
    spec = _replace_once(spec, C4_SPEC_TERM_OLD, C4_SPEC_TERM_NEW, "C4 spec term header")
    spec = _replace_once(spec, C4_SPEC_BULLET_ANCHOR, C4_SPEC_BULLET_ANCHOR + "\n" + C4_SPEC_BULLET, "C4 spec bullet")
    spec = _replace_once(spec, C4_SPEC_FORBID_OLD, C4_SPEC_FORBID_NEW, "C4 spec forbid")
    (s / "files/spec.md").write_text(spec)
    # prompt.md: C1+C4 (P1), C4 (forbid). KEEP 0009's C7 (do NOT apply C7_PROMPT).
    prompt = (s / "prompt.md").read_text()
    prompt = _replace_once(prompt, C1_PROMPT_OLD, C1_PROMPT_NEW, "C1+C4 prompt")
    prompt = _replace_once(prompt, C4_PROMPT_FORBID_OLD, C4_PROMPT_FORBID_NEW, "C4 prompt forbid")
    (s / "prompt.md").write_text(prompt)
    _patch_meta(s, "workflow_handoff_0018", "Schema = 0009 + C1 + C2 + C4 (no C7)")


def build_contract(out):
    """0019 = 0009 + pure C7 (spec S6 procedural clause + prompt step1). No C1/C2/C4."""
    c = out / "workflow_handoff_0019"
    if c.exists():
        shutil.rmtree(c)
    shutil.copytree(TRACK / "workflow_handoff_0009", c)
    spec = (c / "files/spec.md").read_text()
    spec = _replace_once(spec, C7_SPEC_OLD, C7_SPEC_NEW, "C7 spec")
    (c / "files/spec.md").write_text(spec)
    prompt = (c / "prompt.md").read_text()
    prompt = _replace_once(prompt, C7_PROMPT_OLD, C7_PROMPT_NEW, "C7 prompt")
    (c / "prompt.md").write_text(prompt)
    _patch_meta(c, "workflow_handoff_0019", "Contract = 0009 + pure C7 (no C1/C2/C4)")


def _patch_meta(task, tid, note):
    mf = task / "metadata.json"
    md = json.loads(mf.read_text())
    md["task_id"] = tid
    md["phase4y"] = note
    mf.write_text(json.dumps(md, indent=2, ensure_ascii=False) + "\n")


def semantic_diff_gate(out):
    """HARD gate. 0018: all deltas schema-bearing, NO new C7 vs 0009. 0019: all deltas pure C7,
    NO new schema/answer/decoy. Enumerate deltas by line vs 0009 and classify each."""
    base_spec = (TRACK / "workflow_handoff_0009/files/spec.md").read_text().splitlines()
    base_prompt = (TRACK / "workflow_handoff_0009/prompt.md").read_text().splitlines()
    import difflib
    verdict = {"0018": [], "0019": []}
    for tid, label in [("workflow_handoff_0018", "0018"), ("workflow_handoff_0019", "0019")]:
        for fname, base in [("files/spec.md", base_spec), ("prompt.md", base_prompt)]:
            new = (TRACK / tid / fname).read_text().splitlines()
            for ln in difflib.unified_diff(base, new, lineterm="", n=0):
                if ln.startswith(("---", "+++", "@@")):
                    continue
                verdict[label].append({"file": fname, "line": ln[1:], "kind": "added" if ln.startswith("+") else "removed"})
    # ---- 0018 (Schema): added lines must be schema-bearing; the authoritative C7 guard is the
    # swap-ABSENCE check below (Schema must not contain the C7 spec/prompt swaps). The line-level
    # C7-leak proxy is intentionally NOT used: prompt line 3 carries the baseline-0009 phrase
    # "Infer the unique assignment by intersecting the constraints in spec.md" (shared by 0009 and
    # 0015), which is not a C7 delta and must not trip the gate. ----
    s18_added = [d for d in verdict["0018"] if d["kind"] == "added"]
    for d in s18_added:
        if not any(m in d["line"] for m in SCHEMA_MARKERS):
            raise FailClosed(f"0018 added line is NOT schema-bearing: {d}")
    # 0018 must NOT have applied the C7 prompt swap (0009's 'Resolve the semantic role...' step retained)
    p18 = (TRACK / "workflow_handoff_0018/prompt.md").read_text()
    if C7_PROMPT_NEW in p18 or "Resolve the semantic role of each report field label" not in p18:
        raise FailClosed("0018 must retain 0009's C7 prompt step (no C7 delta)")
    sp18 = (TRACK / "workflow_handoff_0018/files/spec.md").read_text()
    if C7_SPEC_NEW in sp18:
        raise FailClosed("0018 must retain 0009's C7 spec sentence (no C7 delta)")
    # ---- 0019 (Contract): added lines must be pure C7; NO schema/answer/decoy leak ----
    s19_added = [d for d in verdict["0019"] if d["kind"] == "added"]
    for d in s19_added:
        if not any(m in d["line"] for m in CONTRACT_MARKERS):
            raise FailClosed(f"0019 added line is NOT contract-bearing: {d}")
        if any(m in d["line"] for m in SCHEMA_MARKERS):
            raise FailClosed(f"0019 added line leaks schema: {d}")
    # 0019 must introduce NO schema. Precise check: every non-edited file byte-identical to 0009, and
    # spec.md/prompt.md equal 0009 with EXACTLY the C7 substitutions applied (nothing else). Baseline
    # 0009 already mentions "PVT descriptor"/"glossary" (negation), so bare-term scans are unreliable.
    edited = {"files/spec.md", "prompt.md", "metadata.json"}  # metadata = task_id + provenance note
    for f in sorted((TRACK / "workflow_handoff_0019").rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(TRACK / "workflow_handoff_0019"))
        src = TRACK / "workflow_handoff_0009" / rel
        if rel not in edited:
            if not src.is_file() or src.read_bytes() != f.read_bytes():
                raise FailClosed(f"0019 {rel} differs from 0009 baseline (Contract must not touch non-C7 files)")
    want_spec = (TRACK / "workflow_handoff_0009/files/spec.md").read_text().replace(C7_SPEC_OLD, C7_SPEC_NEW, 1)
    want_prompt = (TRACK / "workflow_handoff_0009/prompt.md").read_text().replace(C7_PROMPT_OLD, C7_PROMPT_NEW, 1)
    if (TRACK / "workflow_handoff_0019/files/spec.md").read_text() != want_spec:
        raise FailClosed("0019 spec.md != 0009 + exactly the C7 spec substitution")
    if (TRACK / "workflow_handoff_0019/prompt.md").read_text() != want_prompt:
        raise FailClosed("0019 prompt.md != 0009 + exactly the C7 prompt substitution")
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
        h = sha_file(TRACK / f"workflow_handoff_{tag.split('/')[0]}/files/flow_config.json")
        if h != p:
            raise FailClosed(f"source hash mismatch {tag}")
    build_schema(out)
    build_contract(out)
    verdict = semantic_diff_gate(out)
    # record the exact frozen C7 strings + locations (immutable operational definition)
    c7_record = {
        "c7_operational_definition": "pure procedural-contract clauses only (clause-level); excludes all schema",
        "c7_strings": [
            {"location": "files/spec.md", "old_0009": C7_SPEC_OLD, "new_0019": C7_SPEC_NEW,
             "clause_swapped": "Resolve the role of each label from the evidence. -> Infer the unique assignment from the constraints."},
            {"location": "prompt.md", "old_0009": C7_PROMPT_OLD, "new_0019": C7_PROMPT_NEW,
             "clause_dropped": "Resolve the semantic role of each report field label from the report intersection. Then"},
        ],
        "mixed_sentences_left_at_0009_baseline": [
            "spec 'What correct looks like' step (0015 fuses the procedural drop with a C1+C4 schema parenthetical; not clause-separable without invention -> kept at 0009 in BOTH variants)",
            "prompt line-3 framing is schema-only (C1+C4); applied to Schema, kept at 0009 in Contract",
        ],
        "c1_report_rename": "op_point=->scenario=, mode=->corner= (applied via frozen 0015 report files in Schema)",
        "semantic_diff_gate": "PASS (0018 schema-only no-C7; 0019 contract-only no-schema)",
        "diffs": verdict,
    }
    (OUT / "component_classification.json").write_text(json.dumps(c7_record, indent=2) + "\n")
    print(json.dumps({"ok": True, "variants": ["workflow_handoff_0018 (Schema)", "workflow_handoff_0019 (Contract)"],
                       "semantic_diff_gate": "PASS", "source_commit": head}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except FailClosed as e:
        print("FAIL-CLOSED:", e, file=sys.stderr)
        sys.exit(1)
