"""Regression tests for the ICLR main-text page-limit gate
(scripts/submission_page_limit_check.py).

ICLR 2027 caps the main text at 9 pages at submission. The bibliography does not count and
the appendix follows it, so the boundary is the REFERENCES heading --- but the heading can
begin *mid-page*. Measuring "the heading is on page 10, therefore the main text is 9 pages"
reported 9 for this manuscript once while 580 words of main text sat above the heading on
page 10. The gate exists because that arithmetic is wrong, and this module exists to prove
the gate still catches it.

Locks in:
  (a) The classifier separates page furniture (running head, line-number ruler) from main text,
      and counts only the latter as a violation.
  (b) A word above the heading in the body column is a violation even when the heading page
      itself is page 10 --- the exact case the naive page-arithmetic misses.
  (c) The gate is fail-closed: a missing PDF, an unlocatable or duplicated heading, an empty
      extraction and an unexpected top-margin string each FAIL rather than pass quietly.
  (d) If the built PDF is present, the committed manuscript passes at the real limit.

Read-only: nothing here builds, moves or edits a submission artifact.
"""
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "submission_page_limit_check.py"
MAIN_PDF = REPO_ROOT / "submission" / "main.pdf"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import submission_page_limit_check as GATE  # noqa: E402


def _head(y=28.6):
    """The running head, as pdftotext reports it, one word tuple per token."""
    words, x = [], 108.0
    for token in "Under review as a conference paper at ICLR 2027".split():
        words.append((x, y, x + 20.0, y + 8.5, token))
        x += 25.0
    return words


def _ruler(ys):
    """Left-margin line numbers from the iclr style's vertical ruler."""
    return [(88.0, y, 96.0, y + 8.5, str(400 + i)) for i, y in enumerate(ys)]


def _heading(y=126.8):
    return [(108.0, y, 116.0, y + 8.5, "R"), (116.9, y, 175.3, y + 8.5, "EFERENCES")]


def _body(y, text="prospective 12-instance expansion reversed the direction"):
    words, x = [], 108.0
    for token in text.split():
        words.append((x, y, x + 30.0, y + 8.5, token))
        x += 35.0
    return words


def test_script_exists_and_is_executable():
    assert SCRIPT.is_file()


# --- (a) furniture is not main text -------------------------------------------------------

def test_running_head_and_ruler_are_not_counted_as_main_text():
    words = _head() + _ruler([100.0, 111.0]) + _heading() + _body(200.0)
    furniture, main_text = GATE.classify_above(words, heading_y=126.8)
    assert [w[4] for w in main_text] == []
    assert len(furniture) == len(_head()) + 2


def test_body_text_below_the_heading_is_not_counted():
    """Only words *above* the heading matter; the bibliography itself is exempt."""
    words = _head() + _heading() + _body(300.0) + _body(320.0)
    _furniture, main_text = GATE.classify_above(words, heading_y=126.8)
    assert main_text == []


# --- (b) the case the naive arithmetic misses ---------------------------------------------

def test_main_text_above_a_midpage_heading_is_a_violation():
    words = _head() + _ruler([100.0]) + _body(100.0) + _heading(y=126.8)
    _furniture, main_text = GATE.classify_above(words, heading_y=126.8)
    assert len(main_text) == 6, "body words above a mid-page heading must be counted"


@pytest.mark.parametrize("x_min,expected", [(88.0, 0), (108.0, 1)])
def test_only_numeric_glyphs_in_the_left_margin_are_treated_as_ruler(x_min, expected):
    """A digit in the body column is main text; a digit in the ruler column is furniture."""
    words = _head() + [(x_min, 100.0, x_min + 8.0, 108.5, "432")] + _heading()
    _furniture, main_text = GATE.classify_above(words, heading_y=126.8)
    assert len(main_text) == expected


def test_a_nonnumeric_glyph_in_the_ruler_column_is_still_main_text():
    """The exclusion is narrow on purpose: it drops line numbers, not stray prose."""
    words = _head() + [(88.0, 100.0, 96.0, 108.5, "weakest.")] + _heading()
    _furniture, main_text = GATE.classify_above(words, heading_y=126.8)
    assert [w[4] for w in main_text] == ["weakest."]


# --- (c) fail-closed: every unproven condition raises rather than passing ------------------

def test_missing_pdf_fails_rather_than_passing(tmp_path):
    with pytest.raises(GATE.PageLimitFailure):
        GATE.extract_pages(tmp_path / "absent.pdf")


def test_missing_heading_fails_rather_than_passing():
    pages = [(1, 792.0, _head() + _body(200.0))]
    with pytest.raises(GATE.PageLimitFailure):
        GATE.find_references_page(pages)


def test_duplicate_heading_fails_rather_than_guessing():
    pages = [
        (10, 792.0, _head() + _heading()),
        (11, 792.0, _head() + _heading()),
    ]
    with pytest.raises(GATE.PageLimitFailure):
        GATE.find_references_page(pages)


def test_heading_requires_the_smallcaps_pair():
    """'EFERENCES' alone, without a preceding 'R', is not the heading."""
    pages = [(10, 792.0, _head() + [(116.9, 126.8, 175.3, 135.3, "EFERENCES")])]
    with pytest.raises(GATE.PageLimitFailure):
        GATE.find_references_page(pages)


def test_empty_extraction_is_a_failure_not_a_pass(tmp_path, monkeypatch):
    """A PDF that yields no words must not report a passing zero-word count."""
    fake = tmp_path / "empty.pdf"
    fake.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(GATE.shutil, "which", lambda _name: "/usr/bin/pdftotext")

    class _Proc:
        returncode = 0
        stdout = "<html><body></body></html>"
        stderr = ""

    monkeypatch.setattr(GATE.subprocess, "run", lambda *a, **k: _Proc())
    with pytest.raises(GATE.PageLimitFailure):
        GATE.extract_pages(fake)


def test_unexpected_top_margin_fails_rather_than_excluding_it(monkeypatch):
    """If the top-margin text is not the known running head, refuse to call it furniture."""
    words = [(108.0, 28.6, 128.0, 37.1, "Camera-ready")] + _heading()
    monkeypatch.setattr(GATE, "extract_pages", lambda _pdf: [(10, 792.0, words)])
    with pytest.raises(GATE.PageLimitFailure):
        GATE.audit(Path("dummy.pdf"), limit=9)


def test_absent_running_head_fails_rather_than_passing(monkeypatch):
    monkeypatch.setattr(GATE, "extract_pages", lambda _pdf: [(10, 792.0, _heading())])
    with pytest.raises(GATE.PageLimitFailure):
        GATE.audit(Path("dummy.pdf"), limit=9)


# --- (d) the committed manuscript, when it has been built ---------------------------------

@pytest.mark.skipif(not MAIN_PDF.is_file(), reason="submission/main.pdf not built")
def test_committed_manuscript_is_within_the_limit():
    report, violations = GATE.audit(MAIN_PDF, limit=9)
    assert violations == [], violations
    assert report["main_text_words_above_heading"] == 0
    assert report["main_text_pages"] <= 9


@pytest.mark.skipif(not MAIN_PDF.is_file(), reason="submission/main.pdf not built")
def test_cli_exit_status_reflects_the_verdict():
    ok = subprocess.run(
        [sys.executable, str(SCRIPT), "--pdf", str(MAIN_PDF)],
        capture_output=True, text=True,
    )
    assert ok.returncode == 0, ok.stderr
    # Negative control on the CLI path: the same PDF fails a limit it genuinely exceeds,
    # proving exit status is derived from the measurement rather than hardcoded.
    tightened = subprocess.run(
        [sys.executable, str(SCRIPT), "--pdf", str(MAIN_PDF), "--limit", "8"],
        capture_output=True, text=True,
    )
    assert tightened.returncode == 1
    assert "the limit is 8" in tightened.stderr
