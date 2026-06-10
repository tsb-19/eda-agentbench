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
