"""metadata.json schema and validation."""

from __future__ import annotations

METADATA_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "task_id", "track", "tool", "difficulty", "data_type",
        "resource_preset", "timeout_sec", "max_tool_calls",
        "max_patch_attempts", "max_output_tokens",
        "files", "run_command", "scoring",
    ],
    "properties": {
        "task_id": {"type": "string", "pattern": "^(task_[0-9]{6}|spice_deck_debug_[0-9]{4}|p3_timing_[0-9]{6}|p6_dc_syn_[0-9]{6}|dc_constraint_[0-9]{4}|sg_lint_[0-9]{4}|pt_sta_debug_[0-9]{4})$"},
        "track": {
            "type": "string",
            "enum": ["p1_rtl_debug", "p2_rtl_gen", "p2_tb_sva_gen", "p3_timing_report_qa",
                      "p4_spice_sim", "p5_spice_deck_debug", "p6_dc_synthesis_qa", "p6_dc_constraint_debug",
                      "p6_lint", "p7_spyglass_lint_debug", "p7_primetime_sta_debug", "p7_physical"],
        },
        "tool": {
            "type": "array",
            "items": {"type": "string", "enum": [
                "vcs", "xcelium", "hspice", "spectre",
                "dc", "pt", "spyglass", "icc2", "innovus",
                "starrc", "sentaurus", "verdi",
            ]},
            "minItems": 1,
        },
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard", "expert"]},
        "data_type": {"type": "string", "enum": ["template_synthetic", "mutation_synthetic", "flow_synthetic"]},
        "resource_preset": {"type": "string", "enum": ["fast", "standard", "expert"]},
        "timeout_sec": {"type": "integer", "minimum": 1, "maximum": 3600},
        "max_tool_calls": {"type": "integer", "minimum": 1, "maximum": 200},
        "max_patch_attempts": {"type": "integer", "minimum": 1, "maximum": 50},
        "max_output_tokens": {"type": "integer", "minimum": 1000, "maximum": 200000},
        "files": {
            "type": "object",
            "required": ["visible", "editable", "hidden", "forbidden"],
            "properties": {
                "visible": {"type": "array", "items": {"type": "string"}},
                "editable": {"type": "array", "items": {"type": "string"}},
                "hidden": {"type": "array", "items": {"type": "string"}},
                "forbidden": {"type": "array", "items": {"type": "string"}},
            },
        },
        "run_command": {"type": "string"},
        "scoring": {
            "type": "object",
            "required": ["weights"],
            "properties": {
                "weights": {
                    "type": "object",
                    "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "evaluator": {"type": "string"},
                "explanation_weight": {"type": "number", "minimum": 0, "maximum": 0.2},
                "metrics": {
                    "type": "object",
                    "description": "Numeric metric configs for SPICE/timing tasks",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "measure": {"type": "string"},
                            "target": {"type": "number"},
                            "tolerance": {"type": "number"},
                            "min": {"type": "number"},
                            "max": {"type": "number"},
                        },
                    },
                },
            },
        },
        "sanitizer": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
            },
        },
        "generator": {
            "type": "object",
            "properties": {
                "script": {"type": "string"},
                "seed": {"type": "integer"},
                "params": {"type": "object"},
            },
        },
        "version": {"type": "string"},
    },
}


def validate_metadata(meta: dict) -> list[str]:
    """Validate metadata dict against schema rules. Returns list of error strings."""
    errors: list[str] = []

    # Required fields
    for field in METADATA_SCHEMA["required"]:
        if field not in meta:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors

    # task_id format
    import re
    if not re.match(r"^(task_[0-9]{6}|spice_deck_debug_[0-9]{4}|p3_timing_[0-9]{6}|p6_dc_syn_[0-9]{6}|dc_constraint_[0-9]{4}|sg_lint_[0-9]{4}|pt_sta_debug_[0-9]{4})$", meta["task_id"]):
        errors.append(f"Invalid task_id format: {meta['task_id']!r}")

    # weights sum to 1.0
    weights = meta["scoring"]["weights"]
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        errors.append(f"Scoring weights sum to {total}, expected 1.0")

    # editable must be subset of visible
    visible = set(meta["files"]["visible"])
    editable = set(meta["files"]["editable"])
    if not editable.issubset(visible):
        errors.append(f"editable files not in visible: {editable - visible}")

    # hidden must not overlap with visible
    hidden = set(meta["files"]["hidden"])
    if hidden & visible:
        errors.append(f"hidden files overlap with visible: {hidden & visible}")

    # forbidden must exist in task
    forbidden = set(meta["files"]["forbidden"])
    all_files = visible | hidden
    # forbidden files can be in visible or hidden, that's fine
    # but they should be listed somewhere
    missing_forbidden = forbidden - all_files
    if missing_forbidden:
        errors.append(f"forbidden files not in visible or hidden: {missing_forbidden}")

    return errors
