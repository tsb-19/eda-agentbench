"""Log normalization utilities for removing proprietary information from EDA tool logs."""

import hashlib
import re
from typing import Optional


# --- SPICE error taxonomy ---
SPICE_ERROR_CATEGORIES = {
    "missing_model": [
        r"(?i)model.*not found",
        r"(?i)definition of model.*not found",
    ],
    "missing_subckt": [
        r"(?i)subckt.*not found",
        r"(?i)definition of subckt.*not found",
    ],
    "floating_node": [
        r"(?i)floating node",
        r"(?i)node.*has no DC path",
        r"(?i)no DC path to ground",
    ],
    "wrong_pin_count": [
        r"(?i)number of pins",
        r"(?i)too few.*nodes",
        r"(?i)too many.*nodes",
        r"(?i)wrong number of.*connections",
    ],
    "invalid_directive": [
        r"(?i)unrecognized.*statement",
        r"(?i)unknown.*directive",
        r"(?i)invalid.*command",
        r"(?i)syntax error",
        r"(?i)should have a file name",
        r"(?i)\.inc/\.include should have",
        r"(?i)\.lib should have a filename",
        r"(?i)\.include should have a filename",
        r"(?i)\.inc should have a filename",
    ],
    "invalid_measure": [
        r"(?i)\.measure.*error",
        r"(?i)measure.*failed",
        r"(?i)invalid.*measure",
    ],
    "duplicate_element": [
        r"(?i)duplicate.*element",
        r"(?i)already defined",
        r"(?i)redefined",
        r"(?i)attempts to redefine",
    ],
    "missing_include": [
        r"(?i)include.*not found",
        r"(?i)cannot open.*file",
        r"(?i)unable to open.*file",
        r"(?i)file.*not found",
        r"(?i)no such file",
    ],
    "unsupported_dialect": [
        r"(?i)unsupported.*syntax",
        r"(?i)not supported",
        r"(?i)invalid.*parameter.*name",
        r"(?i)invalid.*model.*level",
        r"(?i)specify a valid model level",
        r"(?i)effective channel length.*too small",
        r"(?i)model level.*not supported",
        r"(?i)model not available",
        r"(?i)level.*mos model not available",
    ],
    "convergence_failure": [
        r"(?i)convergence.*fail",
        r"(?i)did not converge",
        r"(?i)iteration limit",
        r"(?i)truncation error",
    ],
}


def classify_spice_error(line: str) -> str:
    """Classify a SPICE error line into a specific category.

    Uses element prefix to distinguish missing_model vs missing_subckt:
    - X prefix (subcircuit instance) → missing_subckt
    - M prefix (MOSFET) → missing_model

    Args:
        line: A normalized error line from a SPICE simulator log.

    Returns:
        Category string from the SPICE error taxonomy.
    """
    # Check for missing include/file first (before model/subckt)
    if re.search(r"(?i)include.*not found|cannot open.*file|file.*not found|no such file", line):
        return "missing_include"

    # Check for "model/subckt not found" with element-aware logic
    if re.search(r"(?i)definition of model/subckt.*not found", line):
        if re.search(r'for the element\s+"x', line, re.IGNORECASE):
            return "missing_subckt"
        return "missing_model"

    # Pin/node count mismatches
    if re.search(r"(?i)number of nodes mismatch|nodes? mismatch|wrong number of|too few.*nodes|too many.*nodes|number of pins", line):
        return "wrong_pin_count"

    # Generic subckt/model not found
    if re.search(r"(?i)subckt.*not found", line):
        return "missing_subckt"
    if re.search(r"(?i)model.*not found", line):
        return "missing_model"

    # Remaining categories
    for category, patterns in SPICE_ERROR_CATEGORIES.items():
        if category in ("missing_model", "missing_subckt", "wrong_pin_count"):
            continue  # Already handled above
        for pattern in patterns:
            if re.search(pattern, line):
                return category
    return "unknown"


# --- Proprietary info patterns to strip ---

_LICENSE_BANNER_PATTERNS = [
    r"(?i)license.*(?:expire|checkout|check.?in|feature|daemon|server)",
    r"(?i)(?:flexlm|lmx|flexnet).*license",
    r"(?i)using\s+\w+\s+license",
    r"(?i)license\s+(?:file|path|server)\s*[:=]",
    r"(?i)\d+\s+license[s]?\s+(?:checked|returned|available|in use)",
]

_HOSTNAME_PATTERNS = [
    r"(?i)(?:host(?:name)?|machine)\s*[:=]\s*\S+",
    r"(?i)running\s+on\s+\S+",
    r"\b(?:[a-z0-9]+-){2,}[a-z0-9]+\b",
]

_USERNAME_PATTERNS = [
    r"(?i)(?:user|login)\s*[:=]\s*\S+",
    r"(?:^|\s)/home/\S+",
    r"(?:^|\s)/users/\S+",
]

_ABSOLUTE_PATH_PATTERNS = [
    r"(?:^|\s)/[a-zA-Z]\S*(?:bin|lib|share|tools|eda|cadence|synopsys|mentor)\S*",
    r"(?:^|\s)/(?:tools|eda|cadence|synopsys|mentor|usr/local)/\S+",
]

_TOOL_VERSION_BANNER_PATTERNS = [
    r"(?i)(?:version|build)\s*[:=]\s*\d+\.\d+[\.\d]*\S*",
    r"(?i)\w+\s+(?:version|v)\s*\d+\.\d+[\.\d]*\S*",
    r"(?i)Copyright\s.*\d{4}",
]

_TIMESTAMP_PATTERNS = [
    r"\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}",
    r"(?i)(?:created|generated|run)\s+(?:on|at)\s+\S+",
]


def normalize_log(
    raw_log: str,
    extra_patterns: Optional[list[str]] = None,
) -> str:
    """Normalize a raw EDA tool log by removing proprietary information."""
    lines = raw_log.split("\n")
    normalized_lines = []

    all_patterns = (
        _LICENSE_BANNER_PATTERNS
        + _HOSTNAME_PATTERNS
        + _USERNAME_PATTERNS
        + _ABSOLUTE_PATH_PATTERNS
        + _TOOL_VERSION_BANNER_PATTERNS
        + _TIMESTAMP_PATTERNS
    )
    if extra_patterns:
        all_patterns.extend(extra_patterns)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Preserve error/warning lines with path redaction
        is_diagnostic = bool(re.search(
            r"\*\*(?:error|warning|info)\*\*|\berror\b.*(?:found|not|missing|abort)",
            stripped, re.IGNORECASE
        ))

        if is_diagnostic:
            cleaned = re.sub(r"\(/[^)]+\)", "([PATH])", stripped)
            cleaned = re.sub(r"/[a-zA-Z]\S*(?:bin|lib|tools|eda|home|tmp)\S*", "[PATH]", cleaned)
            normalized_lines.append(cleaned)
        else:
            skip = False
            for pattern in all_patterns:
                if re.search(pattern, stripped):
                    skip = True
                    break
            if not skip:
                cleaned = re.sub(r"/[a-zA-Z]\S*(?:bin|lib|tools|eda)\S*", "[PATH]", stripped)
                normalized_lines.append(cleaned)

    return "\n".join(normalized_lines)


def compute_raw_log_hash(raw_log: str) -> str:
    """Compute SHA-256 hash of raw log for reproducibility tracking."""
    return hashlib.sha256(raw_log.encode("utf-8")).hexdigest()


def extract_errors(normalized_log: str) -> list[dict]:
    """Extract error and warning summaries from a normalized log.

    Uses the refined SPICE error taxonomy for categorization.
    """
    errors = []
    error_patterns = [
        (r"\*\*error\*\*", "error"),
        (r"\*\*warning\*\*", "warning"),
        (r"\bfatal\b", "error"),
        (r"(?i)\berror\b", "error"),
        (r"(?i)\bwarning\b", "warning"),
        (r"(?i)not available", "error"),
        (r"(?i)job aborted", "error"),
    ]

    for line in normalized_log.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        for pattern, severity in error_patterns:
            if re.search(pattern, stripped, re.IGNORECASE):
                category = classify_spice_error(stripped)
                errors.append({
                    "severity": severity,
                    "category": category,
                    "message": stripped[:200],
                })
                break

    return errors
