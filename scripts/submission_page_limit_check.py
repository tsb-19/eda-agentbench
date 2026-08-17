#!/usr/bin/env python3
"""Assert that the submission's main text ends within the ICLR page limit.

ICLR 2027 caps the *main text* at 9 pages at submission; the bibliography does not
count and the appendix follows it. The naive test --- "the REFERENCES heading is on
page 10, therefore the main text is 9 pages" --- is wrong, and was wrong here once:
the heading began *mid-page* on page 10 with 580 words of main text above it, and a
build measured that way reported 9 pages when the true figure was 10.

This script measures the thing the rule is about: whether any main-text word is
typeset above the REFERENCES heading on the heading's own page. It is deliberately
fail-closed --- a missing PDF, a missing extractor, an unlocatable heading, or an
unexpected glyph in the excluded margins is a failure, not a pass. A checker that
prints nothing when it cannot see is worse than no checker.

    python3 scripts/submission_page_limit_check.py [--pdf submission/main.pdf]
                                                   [--limit 9]

Exit status is 0 only if the main text provably ends on or before --limit.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = REPO_ROOT / "submission" / "main.pdf"

# The running head "Under review as a conference paper at ICLR 2027" sits in the top
# margin; the iclr style's line-number ruler sits in the left margin. Both are page
# furniture, not main text. Everything else above the heading is a violation.
HEADER_BAND_Y = 40.0
MARGIN_RULER_X = 100.0
RUNNING_HEAD = "Under review as a conference paper at ICLR"

PAGE_RE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
WORD_RE = re.compile(
    r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>'
)


class PageLimitFailure(Exception):
    """Raised for any condition that leaves the page limit unproven."""


def extract_pages(pdf: Path):
    """Return [(page_number, height, [(xMin, yMin, xMax, yMax, text), ...]), ...]."""
    if shutil.which("pdftotext") is None:
        raise PageLimitFailure(
            "pdftotext not on PATH --- the page limit cannot be measured, so it is "
            "not proven. Install poppler-utils rather than skipping this check."
        )
    if not pdf.is_file():
        raise PageLimitFailure(f"{pdf} does not exist --- build it with 'cd submission && make'.")

    proc = subprocess.run(
        ["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise PageLimitFailure(f"pdftotext failed on {pdf}: {proc.stderr.strip()}")

    pages = []
    for number, match in enumerate(PAGE_RE.finditer(proc.stdout), start=1):
        height = float(match.group(2))
        words = [
            (float(a), float(b), float(c), float(d), text)
            for a, b, c, d, text in WORD_RE.findall(match.group(3))
        ]
        pages.append((number, height, words))
    if not pages:
        raise PageLimitFailure(
            f"extracted zero pages from {pdf} --- the measurement is vacuous, not passing."
        )
    return pages


def find_references_page(pages):
    """Locate the REFERENCES heading. Small caps split it into two words."""
    hits = []
    for number, _height, words in pages:
        for index, (_x0, y0, _x1, _y1, text) in enumerate(words):
            if text.startswith("EFERENCES") and index > 0 and words[index - 1][4] == "R":
                hits.append((number, y0))
    if not hits:
        raise PageLimitFailure(
            "could not locate the REFERENCES heading --- without it there is no boundary "
            "between main text and bibliography, so nothing is proven."
        )
    if len(hits) > 1:
        raise PageLimitFailure(f"found {len(hits)} REFERENCES headings at {hits}; expected one.")
    return hits[0]


def classify_above(words, heading_y):
    """Split words ending above the heading into page furniture and main text."""
    furniture, main_text = [], []
    for word in words:
        x0, y0, _x1, y1, text = word
        if y1 > heading_y:
            continue
        if y0 < HEADER_BAND_Y:
            furniture.append(word)  # running head
        elif x0 < MARGIN_RULER_X and re.fullmatch(r"\d+", text):
            furniture.append(word)  # line-number ruler
        else:
            main_text.append(word)
    return furniture, main_text


def audit(pdf: Path, limit: int):
    pages = extract_pages(pdf)
    ref_page, heading_y = find_references_page(pages)
    words_by_page = {number: words for number, _h, words in pages}
    furniture, main_text = classify_above(words_by_page[ref_page], heading_y)

    # Non-vacuity: the exclusions must be exactly the furniture we expect. An
    # unrecognised glyph in a margin must fail rather than be silently dropped.
    head_words = [w[4] for w in furniture if w[1] < HEADER_BAND_Y]
    if not head_words:
        raise PageLimitFailure(
            f"no running head found on page {ref_page} --- the exclusion rule is untested "
            "on this build, so its result cannot be trusted."
        )
    if not " ".join(head_words).startswith(RUNNING_HEAD):
        raise PageLimitFailure(
            f"page {ref_page} top margin reads {' '.join(head_words)!r}, not the expected "
            f"running head {RUNNING_HEAD!r}; refusing to guess what is furniture."
        )

    main_pages = ref_page if main_text else ref_page - 1
    report = {
        "pdf": str(pdf.relative_to(REPO_ROOT)) if pdf.is_relative_to(REPO_ROOT) else str(pdf),
        "total_pages": len(pages),
        "references_page": ref_page,
        "heading_y": round(heading_y, 2),
        "main_text_words_above_heading": len(main_text),
        "main_text_pages": main_pages,
        "limit": limit,
    }
    violations = []
    if main_text:
        preview = " ".join(w[4] for w in main_text[:18])
        violations.append(
            f"{len(main_text)} main-text word(s) are typeset above the REFERENCES heading "
            f"on page {ref_page}: {preview!r}... The main text therefore occupies "
            f"{ref_page} pages, not {ref_page - 1}."
        )
    if main_pages > limit:
        violations.append(f"main text occupies {main_pages} pages; the limit is {limit}.")
    return report, violations


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--limit", type=int, default=9, help="main-text page limit (ICLR 2027: 9)")
    args = parser.parse_args(argv)

    try:
        report, violations = audit(args.pdf, args.limit)
    except PageLimitFailure as exc:
        print(f"FAIL (unproven): {exc}", file=sys.stderr)
        return 2

    width = max(len(k) for k in report)
    for key, value in report.items():
        print(f"  {key:<{width}} : {value}")
    if violations:
        print()
        for violation in violations:
            print(f"FAIL: {violation}", file=sys.stderr)
        return 1
    print(
        f"\nPASS: main text ends on page {report['main_text_pages']} "
        f"(limit {args.limit}); page {report['references_page']} begins with the "
        f"bibliography, which does not count."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
