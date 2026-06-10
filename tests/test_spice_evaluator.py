"""Tests for SPICE evaluator: metric parser and metadata validation."""

from pathlib import Path

from eda_agentbench.evaluator.spice_sim import parse_hspice_measurements, _parse_hspice_value
from eda_agentbench.schema import validate_metadata


def test_parse_hspice_value_engineering():
    """Parse engineering suffixes."""
    assert abs(_parse_hspice_value("8.3984n") - 8.3984e-9) < 1e-15
    assert abs(_parse_hspice_value("1.2k") - 1200) < 1e-6
    assert abs(_parse_hspice_value("10p") - 10e-12) < 1e-15
    assert abs(_parse_hspice_value("100u") - 100e-6) < 1e-10
    assert abs(_parse_hspice_value("1.8") - 1.8) < 1e-10
    assert abs(_parse_hspice_value("7.1234E-09") - 7.1234e-9) < 1e-15


def test_parse_hspice_measurements_engineering_suffix(tmp_path):
    """Parse 'name= value' format with engineering suffix."""
    lis = tmp_path / "test.lis"
    lis.write_text("""\
 tdrise=   8.3984n  targ=   8.4484n   trig=  50.0000p
          ***** job concluded
""")
    results = parse_hspice_measurements(lis)
    assert abs(results["tdrise"] - 8.3984e-9) < 1e-15
    assert abs(results["targ"] - 8.4484e-9) < 1e-15


def test_parse_hspice_measurements_lis_format(tmp_path):
    """Parse 'name = value' format from .lis file."""
    lis = tmp_path / "test.lis"
    lis.write_text("""\
***** HSPICE simulation
tdrise = 1.1053E-08
tdfall = 9.8765E-09
**** end
""")
    results = parse_hspice_measurements(lis)
    assert abs(results["tdrise"] - 1.1053e-8) < 1e-12
    assert abs(results["tdfall"] - 9.8765e-9) < 1e-12


def test_parse_hspice_measurements_mt0_format(tmp_path):
    """Parse measurement name + value on next line."""
    lis = tmp_path / "test.lis"
    lis.write_text("""\
$&%# measurement section
tdrise
1.1053E-08
$&%# end
""")
    results = parse_hspice_measurements(lis)
    assert abs(results["tdrise"] - 1.1053e-8) < 1e-12


def test_parse_hspice_measurements_empty(tmp_path):
    """Empty file returns empty dict."""
    lis = tmp_path / "test.lis"
    lis.write_text("")
    results = parse_hspice_measurements(lis)
    assert results == {}


def test_parse_hspice_measurements_no_file(tmp_path):
    """Missing file returns empty dict."""
    results = parse_hspice_measurements(tmp_path / "nonexistent.lis")
    assert results == {}


def test_p4_metadata_valid(tmp_path):
    """P4 spice_sim metadata passes validation."""
    meta = {
        "task_id": "task_000001",
        "track": "p4_spice_sim",
        "tool": ["hspice"],
        "difficulty": "easy",
        "data_type": "template_synthetic",
        "resource_preset": "fast",
        "timeout_sec": 120,
        "max_tool_calls": 10,
        "max_patch_attempts": 3,
        "max_output_tokens": 16000,
        "files": {
            "visible": ["circuit.sp", "run_public.sh"],
            "editable": ["circuit.sp"],
            "hidden": ["run_hidden.sh"],
            "forbidden": ["run_public.sh", "run_hidden.sh"],
        },
        "run_command": "bash run_public.sh",
        "scoring": {
            "weights": {
                "tool_run": 0.3,
                "output_generated": 0.2,
                "public_metric": 0.2,
                "hidden_metric": 0.2,
                "explanation": 0.1,
            },
            "evaluator": "spice_sim.SPICESimEvaluator",
            "metrics": {
                "public": {"measure": "tdrise", "min": 8e-9, "max": 15e-9},
                "hidden": {"measure": "tdrise", "min": 8e-9, "max": 15e-9},
            },
        },
        "version": "1.0.0",
    }
    errors = validate_metadata(meta)
    assert errors == [], f"Metadata validation errors: {errors}"


def test_p1_metadata_still_valid():
    """P1 RTL Debug metadata still passes validation."""
    meta = {
        "task_id": "task_000001",
        "track": "p1_rtl_debug",
        "tool": ["vcs"],
        "difficulty": "easy",
        "data_type": "mutation_synthetic",
        "resource_preset": "fast",
        "timeout_sec": 120,
        "max_tool_calls": 10,
        "max_patch_attempts": 3,
        "max_output_tokens": 16000,
        "files": {
            "visible": ["design.sv", "tb_public.sv", "run_public.sh"],
            "editable": ["design.sv"],
            "hidden": ["tb_hidden.sv", "run_hidden.sh"],
            "forbidden": ["tb_public.sv", "tb_hidden.sv", "run_public.sh", "run_hidden.sh"],
        },
        "run_command": "bash run_public.sh",
        "scoring": {
            "weights": {"compile": 0.1, "public_test": 0.3, "hidden_test": 0.5, "explanation": 0.1},
        },
        "version": "1.0.0",
    }
    errors = validate_metadata(meta)
    assert errors == [], f"P1 metadata validation errors: {errors}"
