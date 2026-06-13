"""Parser for Design Compiler synthesis reports.

Extracts structured data from text-format DC reports for P6 QA tasks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DCReport:
    """Parsed Design Compiler synthesis report data."""
    top_module: str = ""
    total_area: float | None = None
    combinational_area: float | None = None
    sequential_area: float | None = None
    cell_count: int | None = None
    register_count: int | None = None
    worst_slack: float | None = None
    clock_period: float | None = None
    compile_status: str = ""
    warning_count: int | None = None
    error_count: int | None = None

    def get_top_module(self) -> str:
        return self.top_module

    def get_total_area(self) -> float | None:
        return self.total_area

    def get_combinational_area(self) -> float | None:
        return self.combinational_area

    def get_sequential_area(self) -> float | None:
        return self.sequential_area

    def get_cell_count(self) -> int | None:
        return self.cell_count

    def get_register_count(self) -> int | None:
        return self.register_count

    def get_worst_slack(self) -> float | None:
        return self.worst_slack

    def get_clock_period(self) -> float | None:
        return self.clock_period

    def get_compile_status(self) -> str:
        return self.compile_status

    def get_warning_count(self) -> int | None:
        return self.warning_count

    def get_error_count(self) -> int | None:
        return self.error_count


def parse_dc_report(text: str) -> DCReport:
    """Parse a normalized DC synthesis report text.

    Supports report sections:
        *****  Report : area
        *****  Report : timing
        *****  Report : compile
        Top module: <name>
        Combinational area: ...
        Noncombinational area: ...
        Total cell area: ...
        Number of cells: ...
        Number of registers: ...
        Worst slack: ...
        Clock period: ...
        Compile status: ...
        Warning count: ...
        Error count: ...
    """
    report = DCReport()
    lines = text.splitlines()

    for line in lines:
        stripped = line.strip()

        # Top module
        m = re.match(r"Top\s+[Mm]odule\s*:\s*(\S+)", stripped, re.IGNORECASE)
        if m:
            report.top_module = m.group(1)
            continue

        # Total cell area
        m = re.match(r"(?:Total\s+cell\s+area|Total\s+area)\s*[:=]\s*([-\d.eE+]+)", stripped, re.IGNORECASE)
        if m:
            report.total_area = _parse_float(m.group(1))
            continue

        # Combinational area
        m = re.match(r"Combinational\s+area\s*[:=]\s*([-\d.eE+]+)", stripped, re.IGNORECASE)
        if m:
            report.combinational_area = _parse_float(m.group(1))
            continue

        # Sequential / Noncombinational area
        m = re.match(r"(?:Noncombinational|Sequential)\s+area\s*[:=]\s*([-\d.eE+]+)", stripped, re.IGNORECASE)
        if m:
            report.sequential_area = _parse_float(m.group(1))
            continue

        # Number of cells
        m = re.match(r"Number\s+of\s+cells\s*[:=]\s*(\d+)", stripped, re.IGNORECASE)
        if m:
            report.cell_count = int(m.group(1))
            continue

        # Number of registers / sequential elements
        m = re.match(r"Number\s+of\s+(?:registers|sequential\s+elements)\s*[:=]\s*(\d+)", stripped, re.IGNORECASE)
        if m:
            report.register_count = int(m.group(1))
            continue

        # Worst slack
        m = re.match(r"Worst\s+slack\s*[:=]\s*([-\d.eE+]+)", stripped, re.IGNORECASE)
        if m:
            report.worst_slack = _parse_float(m.group(1))
            continue

        # Clock period
        m = re.match(r"Clock\s+period\s*[:=]\s*([-\d.eE+]+)", stripped, re.IGNORECASE)
        if m:
            report.clock_period = _parse_float(m.group(1))
            continue

        # Compile status
        m = re.match(r"Compile\s+status\s*[:=]\s*(.+)", stripped, re.IGNORECASE)
        if m:
            report.compile_status = m.group(1).strip()
            continue

        # Warning count
        m = re.match(r"Warning\s+(?:count|total)\s*[:=]\s*(\d+)", stripped, re.IGNORECASE)
        if m:
            report.warning_count = int(m.group(1))
            continue

        # Error count
        m = re.match(r"Error\s+(?:count|total)\s*[:=]\s*(\d+)", stripped, re.IGNORECASE)
        if m:
            report.error_count = int(m.group(1))
            continue

    return report


def _parse_float(s: str) -> float:
    """Parse a string to float, handling edge cases."""
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        s = re.sub(r"\s*(ns|ps|us|ms)\s*$", "", s, flags=re.IGNORECASE)
        try:
            return float(s)
        except ValueError:
            return 0.0
