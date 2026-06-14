"""Tests for SPICE evaluator: metric parser and metadata validation."""

from pathlib import Path

from eda_agentbench.evaluator.spice_sim import (
    parse_hspice_measurements, _parse_hspice_value, parse_metrics_json,
)
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


def test_parse_metrics_json(tmp_path):
    """Parse metrics.json with numeric values."""
    metrics = tmp_path / "metrics.json"
    metrics.write_text('{"tdrise": 8.3984e-09, "tdfall": 7.123e-09, "gain": 2.5}')
    results = parse_metrics_json(tmp_path)
    assert abs(results["tdrise"] - 8.3984e-9) < 1e-15
    assert abs(results["tdfall"] - 7.123e-9) < 1e-15
    assert abs(results["gain"] - 2.5) < 1e-10


def test_parse_metrics_json_empty(tmp_path):
    """Empty metrics.json returns empty dict."""
    metrics = tmp_path / "metrics.json"
    metrics.write_text("{}")
    results = parse_metrics_json(tmp_path)
    assert results == {}


def test_parse_metrics_json_no_file(tmp_path):
    """Missing metrics.json returns empty dict."""
    results = parse_metrics_json(tmp_path)
    assert results == {}


def test_parse_metrics_json_invalid(tmp_path):
    """Invalid JSON returns empty dict."""
    metrics = tmp_path / "metrics.json"
    metrics.write_text("not valid json{{{")
    results = parse_metrics_json(tmp_path)
    assert results == {}


def test_parse_metrics_json_string_values(tmp_path):
    """metrics.json with string values is ignored."""
    metrics = tmp_path / "metrics.json"
    metrics.write_text('{"tdrise": "hello", "tdfall": 1e-9}')
    results = parse_metrics_json(tmp_path)
    assert "tdrise" not in results
    assert abs(results["tdfall"] - 1e-9) < 1e-15


def test_spectre_metadata_valid():
    """Spectre spice_sim metadata passes validation."""
    meta = {
        "task_id": "task_000002",
        "track": "p4_spice_sim",
        "tool": ["spectre"],
        "difficulty": "easy",
        "data_type": "template_synthetic",
        "resource_preset": "fast",
        "timeout_sec": 120,
        "max_tool_calls": 10,
        "max_patch_attempts": 3,
        "max_output_tokens": 16000,
        "files": {
            "visible": ["circuit.scs", "run_public.sh"],
            "editable": ["circuit.scs"],
            "hidden": ["run_hidden.sh"],
            "forbidden": ["run_public.sh", "run_hidden.sh"],
        },
        "run_command": "bash run_public.sh",
        "scoring": {
            "weights": {
                "tool_run": 0.3, "output_generated": 0.2,
                "public_metric": 0.2, "hidden_metric": 0.2, "explanation": 0.1,
            },
            "evaluator": "spice_sim.SPICESimEvaluator",
            "metrics": {
                "public": {"measure": "tdrise", "min": 8e-9, "max": 15e-9},
                "hidden": {"measure": "tdfall", "min": 8e-9, "max": 15e-9},
            },
        },
        "version": "1.0.0",
    }
    errors = validate_metadata(meta)
    assert errors == [], f"Spectre metadata validation errors: {errors}"


# --- P4 tool_run execution gating (regression) ---

def _spice_evaluator():
    from eda_agentbench.evaluator.spice_sim import SPICESimEvaluator
    meta = {"scoring": {"weights": {"tool_run": 0.3}}}
    return SPICESimEvaluator(Path("/nonexistent"), meta)


def test_tool_run_pass_hspice_concluded():
    """HSPICE 'job concluded' with no abort scores 1.0."""
    ev = _spice_evaluator()
    comp = ev.evaluate_component("tool_run", Path("/nonexistent"),
                                 "tdrise = 1.1e-08\n***** job concluded\n")
    assert comp.raw_score == 1.0


def test_tool_run_pass_spectre_completes():
    """Real SPECTRE191 success banner 'spectre completes with 0 errors' scores 1.0."""
    ev = _spice_evaluator()
    comp = ev.evaluate_component(
        "tool_run", Path("/nonexistent"),
        "Time used: CPU = 497 ms\nspectre completes with 0 errors, 0 warnings, and 2 notices.\n")
    assert comp.raw_score == 1.0


def test_tool_run_pass_spectre_ended_legacy():
    """Legacy 'spectre ended' wording is still accepted as completion."""
    ev = _spice_evaluator()
    comp = ev.evaluate_component("tool_run", Path("/nonexistent"),
                                 "Aggregate audit (3 of 3) ...\nspectre ended at 12:00:00\n")
    assert comp.raw_score == 1.0


def test_tool_run_fail_on_spectre_errors():
    """Spectre completing *with errors* scores 0.0."""
    ev = _spice_evaluator()
    comp = ev.evaluate_component(
        "tool_run", Path("/nonexistent"),
        "Error found by spectre.\nspectre completes with 3 errors, 1 warning, and 0 notices.\n")
    assert comp.raw_score == 0.0


def test_tool_run_fail_when_tool_did_not_run():
    """Regression: a log without a completion banner (tool missing / timeout /
    empty / unrelated output) must score 0.0, never 1.0."""
    ev = _spice_evaluator()
    for bad_log in [
        "",
        "HSPICE not found in PATH",
        "Simulation timed out",
        "some unrelated output with no completion banner",
    ]:
        comp = ev.evaluate_component("tool_run", Path("/nonexistent"), bad_log)
        assert comp.raw_score == 0.0, f"log {bad_log!r} should score 0.0, got {comp.raw_score}"


def test_tool_run_fail_on_hspice_abort():
    """An aborted HSPICE run (no conclusion banner) scores 0.0."""
    ev = _spice_evaluator()
    comp = ev.evaluate_component("tool_run", Path("/nonexistent"),
                                 ">error ***** hspice job aborted\n")
    assert comp.raw_score == 0.0
