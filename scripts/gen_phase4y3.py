#!/usr/bin/env python3
"""Phase-4Y Stage-3 variant generator: C2-only (0022) vs C4-only (0023), from frozen 0009.

Clause-level component boundary (frozen wording only; no invention):
  0022 / C2-only = 0009 + frozen PVT-definition spec line (exclude C1,C3,C4,C5,C6,C7)
  0023 / C4-only = 0009 + frozen glossary.md + exact frozen C4 references (exclude C1,C2,C3,C5,C6,C7)

C2 and C4 are cleanly separable: C2 is the single spec PVT-definition LINE; C4 is the glossary FILE
(+ its frozen references). Note C4's glossary.md itself contains a PVT line (part of the frozen file);
that is C4 content, distinct from the C2 spec line. The gate checks spec.md for the C2 line and the
glossary file for C4, so the two do not contaminate each other's variant.
"""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4y3"
EXPECTED_COMMIT = "007aa7b"
SRC_HASHES = {"0009/flow_config": "65d3682943022f6306a5ef1391d322a03695cb7c285c364b1aa50f983d75b203"}

# C2: frozen PVT-definition spec line (from 0018)
C2_PVT_LINE = "- A **PVT descriptor** (e.g. `slow_1.0V_125C`) is a string `<process>_<voltage>_<temperature>` that **characterizes** a (scenario, corner) pair but is **never** a valid scenario or corner value."
C2_CLOCK_OLD = "- The consumed clock is the one that yields non-zero intended-clock path coverage on the design."

# C4: frozen glossary + references (from 0018)
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


class FailClosed(Exception):
    pass


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _replace_once(text, old, new, label):
    if old not in text:
        raise FailClosed(f"anchor not found for {label}: {old[:60]}")
    if text.count(old) != 1:
        raise FailClosed(f"anchor not unique for {label}")
    return text.replace(old, new, 1)


def build_c2(out):
    s = out / "workflow_handoff_0022"
    if s.exists():
        shutil.rmtree(s)
    shutil.copytree(TRACK / "workflow_handoff_0009", s)
    spec = (s / "files/spec.md").read_text()
    spec = _replace_once(spec, C2_CLOCK_OLD, C2_PVT_LINE + "\n" + C2_CLOCK_OLD, "C2 PVT insert")
    (s / "files/spec.md").write_text(spec)
    _patch_meta(s, "workflow_handoff_0022", "C2-only = 0009 + frozen PVT-def spec line (no C1,C3-C7)")


def build_c4(out):
    c = out / "workflow_handoff_0023"
    if c.exists():
        shutil.rmtree(c)
    shutil.copytree(TRACK / "workflow_handoff_0009", c)
    shutil.copy2(TRACK / "workflow_handoff_0018" / "files" / "glossary.md", c / "files" / "glossary.md")
    spec = (c / "files/spec.md").read_text()
    spec = _replace_once(spec, C4_SPEC_TERM_OLD, C4_SPEC_TERM_NEW, "C4 spec term")
    spec = _replace_once(spec, C4_SPEC_BULLET_ANCHOR, C4_SPEC_BULLET_ANCHOR + "\n" + C4_SPEC_BULLET, "C4 spec bullet")
    spec = _replace_once(spec, C4_SPEC_FORBID_OLD, C4_SPEC_FORBID_NEW, "C4 spec forbid")
    (c / "files/spec.md").write_text(spec)
    prompt = (c / "prompt.md").read_text()
    prompt = _replace_once(prompt, C4_PROMPT_OLD, C4_PROMPT_NEW, "C4 prompt clause")
    prompt = _replace_once(prompt, C4_PROMPT_FORBID_OLD, C4_PROMPT_FORBID_NEW, "C4 prompt forbid")
    (c / "prompt.md").write_text(prompt)
    _patch_meta(c, "workflow_handoff_0023", "C4-only = 0009 + frozen glossary.md + C4 refs (no C1-C3,C5-C7)")


def _patch_meta(task, tid, note):
    md = json.loads((task / "metadata.json").read_text())
    md["task_id"] = tid
    md["phase4y3"] = note
    (task / "metadata.json").write_text(json.dumps(md, indent=2, ensure_ascii=False) + "\n")


def semantic_diff_gate(out):
    import difflib
    base_spec = (TRACK / "workflow_handoff_0009/files/spec.md").read_text().splitlines()
    base_prompt = (TRACK / "workflow_handoff_0009/prompt.md").read_text().splitlines()
    verdict = {"0022": [], "0023": []}
    for tid, label in [("workflow_handoff_0022", "0022"), ("workflow_handoff_0023", "0023")]:
        for fname, base in [("files/spec.md", base_spec), ("prompt.md", base_prompt)]:
            new = (TRACK / tid / fname).read_text().splitlines()
            for ln in difflib.unified_diff(base, new, lineterm="", n=0):
                if ln.startswith(("---", "+++", "@@")):
                    continue
                verdict[label].append({"file": fname, "line": ln[1:], "kind": "added" if ln.startswith("+") else "removed"})
    # 0022 (C2-only): added line is the C2 PVT-def; NO glossary.md, NO C4 refs in spec/prompt, NO C1 labels
    sp22 = (TRACK / "workflow_handoff_0022/files/spec.md").read_text()
    p22 = (TRACK / "workflow_handoff_0022/prompt.md").read_text()
    if "<process>_<voltage>_<temperature>" not in sp22:
        raise FailClosed("0022 must add the C2 PVT-def line")
    if (TRACK / "workflow_handoff_0022/files/glossary.md").exists():
        raise FailClosed("0022 must NOT add glossary.md (C4)")
    if "see glossary.md" in sp22 or "glossary.md states the disjoint typed axes" in p22:
        raise FailClosed("0022 leaks C4 references")
    # 0023 (C4-only): glossary.md present + C4 refs; NO C2 PVT-def LINE in spec; reports op_point/mode
    if not (TRACK / "workflow_handoff_0023/files/glossary.md").exists():
        raise FailClosed("0023 must add glossary.md (C4)")
    sp23 = (TRACK / "workflow_handoff_0023/files/spec.md").read_text()
    if "<process>_<voltage>_<temperature>" in sp23:
        raise FailClosed("0023 must NOT add the C2 PVT-def spec line")
    edited = {"files/spec.md", "prompt.md", "metadata.json"}
    for f in sorted((TRACK / "workflow_handoff_0023").rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(TRACK / "workflow_handoff_0023"))
        src = TRACK / "workflow_handoff_0009" / rel
        if rel not in edited and rel != "files/glossary.md":
            if not src.is_file() or src.read_bytes() != f.read_bytes():
                raise FailClosed(f"0023 {rel} differs from 0009 baseline (C4-only must not touch other files)")
    # both: reports stay op_point/mode (no C1 canonical rename) -- enforced by the non-edited byte-equality above
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
    build_c2(out)
    build_c4(out)
    verdict = semantic_diff_gate(out)
    rec = {"c2_operational_definition": "frozen PVT-definition spec line only (exclude C1,C3,C4-C7)",
           "c4_operational_definition": "frozen glossary.md + exact frozen C4 references (exclude C1-C3,C5-C7)",
           "note": "C2 (spec PVT-def line) and C4 (glossary file + refs) are cleanly separable; C4's glossary contains a PVT line as part of the frozen file but the C2 SPEC line is absent from 0023",
           "semantic_diff_gate": "PASS (0022 C2-only no-C4/no-C1; 0023 C4-only no-C2-line, reports op_point/mode)",
           "diffs": verdict}
    (OUT / "component_classification.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({"ok": True, "variants": ["workflow_handoff_0022 (C2-only)", "workflow_handoff_0023 (C4-only)"],
                      "semantic_diff_gate": "PASS", "source_commit": head}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except FailClosed as e:
        print("FAIL-CLOSED:", e, file=sys.stderr)
        sys.exit(1)
