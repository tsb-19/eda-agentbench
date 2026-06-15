"""Unit tests for anti-cheat guard."""

from pathlib import Path

from eda_agentbench.anti_cheat.guard import ForbiddenModificationGuard


def test_snapshot_and_verify_clean(tmp_path):
    f = tmp_path / "test.sv"
    f.write_text("module test; endmodule")
    guard = ForbiddenModificationGuard()
    guard.snapshot(tmp_path, ["test.sv"])
    clean, mismatches = guard.verify(tmp_path)
    assert clean is True
    assert mismatches == []


def test_snapshot_and_verify_modified(tmp_path):
    f = tmp_path / "test.sv"
    f.write_text("module test; endmodule")
    guard = ForbiddenModificationGuard()
    guard.snapshot(tmp_path, ["test.sv"])
    # Modify the file
    f.write_text("module test; // modified endmodule")
    clean, mismatches = guard.verify(tmp_path)
    assert clean is False
    assert "test.sv" in mismatches


def test_snapshot_and_verify_deleted(tmp_path):
    f = tmp_path / "test.sv"
    f.write_text("module test; endmodule")
    guard = ForbiddenModificationGuard()
    guard.snapshot(tmp_path, ["test.sv"])
    f.unlink()
    clean, mismatches = guard.verify(tmp_path)
    assert clean is False
    assert any("deleted" in m for m in mismatches)


def test_submission_forbidden_check(tmp_path):
    from eda_agentbench.task.validator import check_submission_forbidden
    # Create submission with forbidden file
    sub = tmp_path / "submission"
    sub.mkdir()
    (sub / "design.sv").write_text("module mux; endmodule")
    (sub / "tb_public.sv").write_text("module tb; endmodule")  # forbidden!
    violations = check_submission_forbidden(sub, ["tb_public.sv", "tb_hidden.sv"])
    assert "tb_public.sv" in violations
    assert "tb_hidden.sv" not in violations


def test_submission_clean(tmp_path):
    from eda_agentbench.task.validator import check_submission_forbidden
    sub = tmp_path / "submission"
    sub.mkdir()
    (sub / "design.sv").write_text("module mux; endmodule")
    violations = check_submission_forbidden(sub, ["tb_public.sv", "tb_hidden.sv"])
    assert violations == []


# --- TCL injection guard for editable constraint files ---

_CLEAN_SDC = (
    "# constraints\n"
    "create_clock -name clk -period 5 [get_ports clk]\n"
    "set_input_delay 1.0 -clock clk [get_ports en]\n"
    "set_output_delay 1.0 -clock clk [get_ports count]\n"
    "set_clock_uncertainty 0.1 [get_clocks clk]\n"
    "set period 5\n"                       # plain `set` is legitimate, never flagged
    "set_max_area 0\n"
)


def test_tcl_injection_clean_sdc(tmp_path):
    from eda_agentbench.task.validator import check_tcl_injection
    (tmp_path / "constraints.sdc").write_text(_CLEAN_SDC)
    assert check_tcl_injection(tmp_path, ["constraints.sdc"]) == []


def test_tcl_injection_proc_override(tmp_path):
    """The headline exploit: redefining a grader builtin must be flagged."""
    from eda_agentbench.task.validator import check_tcl_injection
    (tmp_path / "constraints.sdc").write_text(_CLEAN_SDC + "proc incr {args} {}\n")
    violations = check_tcl_injection(tmp_path, ["constraints.sdc"])
    assert violations == ["constraints.sdc: proc"]


def test_tcl_injection_various_commands(tmp_path):
    """Every grader-subversion / IO command is rejected."""
    from eda_agentbench.task.validator import check_tcl_injection
    for cmd, line in [
        ("rename", "rename incr {}"),
        ("eval", "eval {set x 1}"),
        ("exec", "exec /bin/sh -c whoami"),
        ("open", "set f [open /dev/stdout w]"),     # command after [
        ("interp", "interp alias {} incr {} ::list"),
        ("namespace", "namespace eval :: {}"),
        ("source", "source ../hidden/run_hidden.tcl"),
        ("puts", "puts stdout CONSTRAINTS_OK"),
        ("upvar", "upvar 0 error_count ec"),
    ]:
        (tmp_path / "constraints.sdc").write_text(_CLEAN_SDC + line + "\n")
        violations = check_tcl_injection(tmp_path, ["constraints.sdc"])
        assert f"constraints.sdc: {cmd}" in violations, f"{cmd!r} not flagged in {line!r}"


def test_tcl_injection_after_semicolon(tmp_path):
    """A second command stacked after ; on a constraint line is still scanned."""
    from eda_agentbench.task.validator import check_tcl_injection
    (tmp_path / "constraints.sdc").write_text(
        "create_clock -name clk -period 5 [get_ports clk] ; proc incr {a} {}\n"
    )
    assert check_tcl_injection(tmp_path, ["constraints.sdc"]) == ["constraints.sdc: proc"]


def test_tcl_injection_ignores_comments(tmp_path):
    """Denylisted words inside a # comment are not at command position -> ignored."""
    from eda_agentbench.task.validator import check_tcl_injection
    (tmp_path / "constraints.sdc").write_text(
        _CLEAN_SDC + "# do not use proc rename eval exec here\n"
    )
    assert check_tcl_injection(tmp_path, ["constraints.sdc"]) == []


def test_tcl_injection_skips_non_tcl_files(tmp_path):
    """Editable Verilog (.v/.sv) is not Tcl-sourced, so it is not scanned."""
    from eda_agentbench.task.validator import check_tcl_injection
    (tmp_path / "design.v").write_text("// proc is just a word here\nmodule m; endmodule\n")
    assert check_tcl_injection(tmp_path, ["design.v"]) == []


def test_tcl_injection_missing_file_ok(tmp_path):
    """A listed-but-absent editable file is not a violation."""
    from eda_agentbench.task.validator import check_tcl_injection
    assert check_tcl_injection(tmp_path, ["constraints.sdc"]) == []
