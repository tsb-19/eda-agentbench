"""Parser for synthetic ICC2-style and Innovus-style PnR reports.

Parses report text into a normalized record dict. Only extracts fields
that are present in the report; missing fields default to None.
"""

from __future__ import annotations

import re
from typing import Any, Optional


def parse_pnr_report(text: str) -> dict[str, Any]:
    """Parse a PnR report string into a normalized record.

    Returns a dict with keys matching the normalized schema. Fields not
    found in the report are set to None.
    """
    rec: dict[str, Any] = {
        "tool_family": None,
        "design_name": None,
        "stage": None,
        "setup_wns": None,
        "setup_tns": None,
        "setup_violations": None,
        "hold_wns": None,
        "hold_tns": None,
        "hold_violations": None,
        "worst_endpoint": None,
        "worst_startpoint": None,
        "timing_met": None,
        "core_utilization": None,
        "placement_density": None,
        "cell_area": None,
        "macro_area": None,
        "total_cell_area": None,
        "instance_count": None,
        "sequential_count": None,
        "buffer_count": None,
        "total_wirelength": None,
        "max_horizontal_overflow": None,
        "max_vertical_overflow": None,
        "total_overflow": None,
        "congested_bins": None,
        "worst_congestion_layer": None,
        "congestion_pass": None,
        "drc_total": None,
        "shorts": None,
        "opens": None,
        "antenna_violations": None,
        "route_completed": None,
        "internal_power": None,
        "switching_power": None,
        "leakage_power": None,
        "total_power": None,
    }

    # Tool family detection
    if re.search(r"ICC2|icc2", text, re.IGNORECASE):
        rec["tool_family"] = "icc2"
    elif re.search(r"Innovus|innovus|INNOVUS", text):
        rec["tool_family"] = "innovus"

    # Design name (support both : and = separators)
    m = re.search(r"Design\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    if m:
        rec["design_name"] = m.group(1)

    # Stage
    m = re.search(r"Stage\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    if m:
        rec["stage"] = m.group(1).lower()

    # --- Timing ---
    m = re.search(r"Setup\s+WNS\s*[:=]\s*([-\d.]+)", text, re.IGNORECASE)
    if m:
        rec["setup_wns"] = float(m.group(1))

    m = re.search(r"Setup\s+TNS\s*[:=]\s*([-\d.]+)", text, re.IGNORECASE)
    if m:
        rec["setup_tns"] = float(m.group(1))

    m = re.search(r"Setup\s+Violating\s+Paths?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["setup_violations"] = int(m.group(1))

    m = re.search(r"Hold\s+WNS\s*[:=]\s*([-\d.]+)", text, re.IGNORECASE)
    if m:
        rec["hold_wns"] = float(m.group(1))

    m = re.search(r"Hold\s+TNS\s*[:=]\s*([-\d.]+)", text, re.IGNORECASE)
    if m:
        rec["hold_tns"] = float(m.group(1))

    m = re.search(r"Hold\s+Violating\s+Paths?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["hold_violations"] = int(m.group(1))

    m = re.search(r"Worst\s+Endpoint\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    if m:
        rec["worst_endpoint"] = m.group(1)

    m = re.search(r"Worst\s+Startpoint\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    if m:
        rec["worst_startpoint"] = m.group(1)

    # Timing met status
    m = re.search(r"Timing\s+Status\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    if m:
        status = m.group(1).lower()
        rec["timing_met"] = status == "met"

    # --- Utilization / Area ---
    m = re.search(r"Core\s+Utilization\s*[:=]\s*([\d.]+)\s*%?", text, re.IGNORECASE)
    if m:
        rec["core_utilization"] = float(m.group(1))

    m = re.search(r"Placement\s+Density\s*[:=]\s*([\d.]+)\s*%?", text, re.IGNORECASE)
    if m:
        rec["placement_density"] = float(m.group(1))

    m = re.search(r"Standard\s+Cell\s+Area\s*[:=]\s*([\d.]+)", text, re.IGNORECASE)
    if m:
        rec["cell_area"] = float(m.group(1))

    m = re.search(r"Macro\s+Area\s*[:=]\s*([\d.]+)", text, re.IGNORECASE)
    if m:
        rec["macro_area"] = float(m.group(1))

    m = re.search(r"Total\s+Cell\s+Area\s*[:=]\s*([\d.]+)", text, re.IGNORECASE)
    if m:
        rec["total_cell_area"] = float(m.group(1))

    m = re.search(r"(?:Number\s+of\s+)?Instances?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["instance_count"] = int(m.group(1))

    m = re.search(r"(?:Number\s+of\s+)?Sequential\s+(?:Cells?|Elements?)?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["sequential_count"] = int(m.group(1))

    m = re.search(r"(?:Number\s+of\s+)?(?:Buffers?|Inverters?)\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["buffer_count"] = int(m.group(1))

    # --- Congestion ---
    m = re.search(r"Max\s+Horizontal\s+Overflow\s*[:=]\s*([\d.]+)\s*%?", text, re.IGNORECASE)
    if m:
        rec["max_horizontal_overflow"] = float(m.group(1))

    m = re.search(r"Max\s+Vertical\s+Overflow\s*[:=]\s*([\d.]+)\s*%?", text, re.IGNORECASE)
    if m:
        rec["max_vertical_overflow"] = float(m.group(1))

    m = re.search(r"Total\s+Overflow\s*[:=]\s*([\d.]+)", text, re.IGNORECASE)
    if m:
        rec["total_overflow"] = float(m.group(1))

    m = re.search(r"(?:Number\s+of\s+)?Congested\s+Bins?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["congested_bins"] = int(m.group(1))

    m = re.search(r"Worst\s+Congestion\s+Layer\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    if m:
        rec["worst_congestion_layer"] = m.group(1)

    m = re.search(r"Congestion\s+Status\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    if m:
        status = m.group(1).lower()
        rec["congestion_pass"] = status == "pass"

    # --- Routing / DRC ---
    m = re.search(r"Total\s+Wirelength\s*[:=]\s*([\d.]+)", text, re.IGNORECASE)
    if m:
        rec["total_wirelength"] = float(m.group(1))

    m = re.search(r"(?:Total\s+)?DRC\s+Violations?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["drc_total"] = int(m.group(1))

    m = re.search(r"Shorts?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["shorts"] = int(m.group(1))

    m = re.search(r"Opens?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["opens"] = int(m.group(1))

    m = re.search(r"Antenna\s+Violations?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        rec["antenna_violations"] = int(m.group(1))

    m = re.search(r"Route\s+Status\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    if m:
        status = m.group(1).lower()
        rec["route_completed"] = status == "clean"

    # --- Power ---
    m = re.search(r"Internal\s+Power\s*[:=]\s*([\d.]+)\s*(?:mW|W|uW)?", text, re.IGNORECASE)
    if m:
        rec["internal_power"] = float(m.group(1))

    m = re.search(r"Switching\s+Power\s*[:=]\s*([\d.]+)\s*(?:mW|W|uW)?", text, re.IGNORECASE)
    if m:
        rec["switching_power"] = float(m.group(1))

    m = re.search(r"Leakage\s+Power\s*[:=]\s*([\d.]+)\s*(?:mW|W|uW)?", text, re.IGNORECASE)
    if m:
        rec["leakage_power"] = float(m.group(1))

    m = re.search(r"Total\s+Power\s*[:=]\s*([\d.]+)\s*(?:mW|W|uW)?", text, re.IGNORECASE)
    if m:
        rec["total_power"] = float(m.group(1))

    return rec


def get_field(record: dict[str, Any], field: str) -> Any:
    """Get a field from a parsed record, returning None if missing."""
    return record.get(field)
