"""Tests for validator modules — static only, no EDA executable required."""

import json
import subprocess
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).parent.parent


class TestLogNormalizer:
    """Test log normalization strips proprietary information."""

    def test_removes_license_banners(self):
        from validators.common.log_normalizer import normalize_log

        log = "Starting simulation\nLicense checkout successful for VCS\nSimulation complete"
        result = normalize_log(log)
        assert "License checkout" not in result
        assert "Starting simulation" in result

    def test_removes_hostnames(self):
        from validators.common.log_normalizer import normalize_log

        log = "Running on server-01.example.com\nCompiling module top"
        result = normalize_log(log)
        assert "server-01" not in result

    def test_removes_absolute_paths(self):
        from validators.common.log_normalizer import normalize_log

        log = "Using /tools/synopsys/vcs/bin/vcs to compile"
        result = normalize_log(log)
        assert "/tools/synopsys" not in result

    def test_preserves_errors(self):
        from validators.common.log_normalizer import normalize_log

        log = "Error: missing semicolon at line 42"
        result = normalize_log(log)
        assert "missing semicolon" in result

    def test_compute_hash(self):
        from validators.common.log_normalizer import compute_raw_log_hash

        h = compute_raw_log_hash("test log content")
        assert len(h) == 64
        assert h == compute_raw_log_hash("test log content")

    def test_extract_errors(self):
        from validators.common.log_normalizer import extract_errors

        log = "Error: syntax error at line 5\nWarning: unused signal\nSimulation complete"
        errors = extract_errors(log)
        assert len(errors) == 2
        assert errors[0]["severity"] == "error"
        assert errors[1]["severity"] == "warning"


class TestRunRecord:
    """Test run record creation."""

    def test_create_run_record_pass(self):
        from validators.common.validation_record import create_run_record

        record = create_run_record(
            backend="hspice",
            expected_status="fail",
            raw_log="Simulation complete\n0 errors",
            returncode=0,
        )
        assert record["command_backend"] == "hspice"
        assert record["expected_status"] == "fail"
        assert record["actual_status"] == "pass"
        assert record["exit_code"] == 0
        assert record["raw_log_retained"] is False
        assert len(record["raw_log_sha256"]) == 64

    def test_create_run_record_fail(self):
        from validators.common.validation_record import create_run_record

        record = create_run_record(
            backend="hspice",
            expected_status="fail",
            raw_log="Error: convergence failed\nSimulation aborted",
            returncode=1,
        )
        assert record["actual_status"] == "fail"
        assert len(record["normalized_errors"]) > 0

    def test_create_run_record_error(self):
        from validators.common.validation_record import create_run_record

        record = create_run_record(
            backend="hspice",
            expected_status="fail",
            raw_log="[TIMEOUT]",
            returncode=-1,
        )
        assert record["actual_status"] == "error"


class TestDebugContrast:
    """Test debug contrast analysis."""

    def test_contrast_verified_when_buggy_fails_golden_passes(self):
        from validators.common.validation_record import (
            create_run_record, determine_debug_contrast, determine_validation_status,
        )

        buggy = create_run_record("hspice", "fail",
            '**error** Definition of model/subckt "pmos_typo" is not found for the element "m1"', 1)
        golden = create_run_record("hspice", "pass", "Simulation complete", 0)

        contrast = determine_debug_contrast(buggy, golden, "missing_model")
        assert contrast["buggy_failed_as_expected"] is True
        assert contrast["golden_passed_as_expected"] is True
        assert contrast["error_category_match"] is True

        status = determine_validation_status("spice_deck_debug", buggy, golden, contrast)
        assert status == "debug_contrast_verified"

    def test_contrast_fails_when_both_pass(self):
        from validators.common.validation_record import (
            create_run_record, determine_debug_contrast, determine_validation_status,
        )

        buggy = create_run_record("hspice", "fail", "Simulation complete", 0)
        golden = create_run_record("hspice", "pass", "Simulation complete", 0)

        contrast = determine_debug_contrast(buggy, golden, "syntax")
        assert contrast["buggy_failed_as_expected"] is False

        status = determine_validation_status("spice_deck_debug", buggy, golden, contrast)
        assert status == "validation_failed"

    def test_contrast_fails_when_both_fail(self):
        from validators.common.validation_record import (
            create_run_record, determine_debug_contrast, determine_validation_status,
        )

        buggy = create_run_record("hspice", "fail", "Error: syntax", 1)
        golden = create_run_record("hspice", "pass", "Error: model not found", 1)

        contrast = determine_debug_contrast(buggy, golden, "syntax")
        assert contrast["buggy_failed_as_expected"] is True
        assert contrast["golden_passed_as_expected"] is False

        status = determine_validation_status("spice_deck_debug", buggy, golden, contrast)
        assert status == "validation_failed"

    def test_contrast_fails_when_category_mismatch(self):
        from validators.common.validation_record import (
            create_run_record, determine_debug_contrast, determine_validation_status,
        )

        buggy = create_run_record("hspice", "fail", "Error: convergence failed", 1)
        golden = create_run_record("hspice", "pass", "Simulation complete", 0)

        contrast = determine_debug_contrast(buggy, golden, "syntax")
        assert contrast["buggy_failed_as_expected"] is True
        assert contrast["golden_passed_as_expected"] is True
        assert contrast["error_category_match"] is False  # convergence != syntax

        status = determine_validation_status("spice_deck_debug", buggy, golden, contrast)
        assert status == "validation_failed"

    def test_timing_qa_uses_smoke_passed(self):
        from validators.common.validation_record import (
            create_run_record, determine_validation_status,
        )

        golden = create_run_record("pt", "pass", "Timing analysis complete", 0)
        status = determine_validation_status("timing_report_qa", golden_run=golden)
        assert status == "commercial_smoke_passed"


class TestValidationRecord:
    """Test full validation record creation."""

    def test_create_record_with_debug_contrast(self):
        from validators.common.validation_record import (
            create_run_record, determine_debug_contrast, create_validation_record,
        )

        buggy = create_run_record("hspice", "fail",
            '**error** Definition of model/subckt "nmos" is not found for the element "m1"', 1)
        golden = create_run_record("hspice", "pass", "Simulation complete", 0)
        contrast = determine_debug_contrast(buggy, golden, "missing_model")

        record = create_validation_record(
            task_id="spice_deck_debug_0001",
            domain="spice_deck_debug",
            backend="hspice",
            tool_name="Synopsys HSPICE",
            tool_version="2021.09-SP1",
            buggy_run=buggy,
            golden_run=golden,
            debug_contrast=contrast,
            notes="test",
        )
        assert record["validation_status"] == "debug_contrast_verified"
        assert "buggy_run" in record
        assert "golden_run" in record
        assert "debug_contrast" in record
        assert record["tool_version_normalized"] == "2021.09"

    def test_create_record_timing_qa(self):
        from validators.common.validation_record import (
            create_run_record, create_validation_record,
        )

        golden = create_run_record("pt", "pass", "Timing complete", 0)
        record = create_validation_record(
            task_id="timing_report_qa_0001",
            domain="timing_report_qa",
            backend="pt",
            tool_name="Synopsys PrimeTime",
            tool_version="2021.06",
            golden_run=golden,
        )
        assert record["validation_status"] == "commercial_smoke_passed"


class TestCommercialAdapters:
    """Test that commercial adapters handle missing env vars correctly."""

    def test_vcs_env_var_none_without_env(self, monkeypatch):
        monkeypatch.delenv("EDA_VCS_CMD", raising=False)
        monkeypatch.setattr("shutil.which", lambda x: None)
        from validators.vcs.validate_rtl import get_vcs_cmd
        assert get_vcs_cmd() is None

    def test_hspice_env_var_none_without_env(self, monkeypatch):
        monkeypatch.delenv("EDA_HSPICE_CMD", raising=False)
        monkeypatch.setattr("shutil.which", lambda x: None)
        from validators.hspice.validate_spice import get_hspice_cmd
        assert get_hspice_cmd() is None

    def test_spectre_env_var_none_without_env(self, monkeypatch):
        monkeypatch.delenv("EDA_SPECTRE_CMD", raising=False)
        monkeypatch.setattr("shutil.which", lambda x: None)
        from validators.spectre.validate_spectre import get_spectre_cmd
        assert get_spectre_cmd() is None

    def test_pt_env_var_none_without_env(self, monkeypatch):
        monkeypatch.delenv("EDA_PT_CMD", raising=False)
        monkeypatch.setattr("shutil.which", lambda x: None)
        from validators.pt.parse_report import get_pt_cmd
        assert get_pt_cmd() is None


class TestSpiceErrorTaxonomy:
    """Test refined SPICE error categorization."""

    def test_missing_model_category(self):
        from validators.common.log_normalizer import classify_spice_error
        assert classify_spice_error('**error** Definition of model/subckt "pmos_typo" is not found') == "missing_model"

    def test_missing_subckt_category(self):
        from validators.common.log_normalizer import classify_spice_error
        assert classify_spice_error('**error** subckt "buf" is not found') == "missing_subckt"

    def test_wrong_pin_count_category(self):
        from validators.common.log_normalizer import classify_spice_error
        assert classify_spice_error('**error** wrong number of pins for element') == "wrong_pin_count"
        assert classify_spice_error('**error** too few nodes for m1') == "wrong_pin_count"

    def test_missing_include_category(self):
        from validators.common.log_normalizer import classify_spice_error
        assert classify_spice_error('**error** include file "models.lib" not found') == "missing_include"
        assert classify_spice_error('**error** cannot open file models.lib') == "missing_include"

    def test_invalid_measure_category(self):
        from validators.common.log_normalizer import classify_spice_error
        assert classify_spice_error('**error** .measure tran failed') == "invalid_measure"

    def test_convergence_failure_category(self):
        from validators.common.log_normalizer import classify_spice_error
        assert classify_spice_error('**error** simulation did not converge') == "convergence_failure"

    def test_unknown_category(self):
        from validators.common.log_normalizer import classify_spice_error
        assert classify_spice_error('**error** some random error message') == "unknown"

    def test_extract_errors_uses_taxonomy(self):
        from validators.common.log_normalizer import extract_errors
        log = '**error** Definition of model/subckt "nmos" is not found\n**warning** no tran outputs'
        errors = extract_errors(log)
        assert len(errors) == 2
        assert errors[0]["category"] == "missing_model"
        assert errors[1]["category"] == "unknown"  # warning about tran outputs


class TestSpiceCategoryDiversity:
    """Test that SPICE tasks cover diverse error categories."""

    VALID_CATEGORIES = {
        "missing_model", "missing_subckt", "floating_node", "wrong_pin_count",
        "invalid_directive", "invalid_measure", "duplicate_element",
        "missing_include", "unsupported_dialect", "convergence_failure", "unknown",
    }

    def _get_spice_metadata(self):
        candidates_dir = REPO_ROOT / "tasks_candidates"
        if not candidates_dir.exists():
            pytest.skip("tasks_candidates not generated")
        spice_dirs = sorted([
            d for d in candidates_dir.iterdir()
            if d.is_dir() and d.name.startswith("spice_deck_debug_")
        ])
        metas = []
        for d in spice_dirs:
            meta_path = d / "metadata.json"
            if meta_path.exists():
                metas.append(json.loads(meta_path.read_text()))
        return metas

    def test_at_least_7_distinct_categories(self):
        """At least 7 distinct expected_error_category values among 100 SPICE tasks.

        HSPICE reliably catches 7 categories (missing_model, missing_subckt,
        wrong_pin_count, duplicate_element, missing_include, unsupported_dialect,
        invalid_directive). The remaining 3 (floating_node, convergence_failure,
        invalid_measure) only produce HSPICE warnings — see docs/taxonomy.md.
        """
        metas = self._get_spice_metadata()
        categories = {m.get("expected_error_category") for m in metas}
        assert len(categories) >= 7, \
            f"Only {len(categories)} distinct categories: {categories}"

    def test_no_category_dominates(self):
        """No single category may account for more than 20/100 tasks (20%)."""
        metas = self._get_spice_metadata()
        from collections import Counter
        counts = Counter(m.get("expected_error_category") for m in metas)
        for cat, count in counts.items():
            assert count <= 20, \
                f"Category '{cat}' appears {count} times (max 20 allowed)"

    def test_all_categories_in_taxonomy(self):
        """Every expected_error_category must be in the SPICE error taxonomy."""
        metas = self._get_spice_metadata()
        for m in metas:
            cat = m.get("expected_error_category")
            assert cat in self.VALID_CATEGORIES, \
                f"{m['task_id']}: unknown category '{cat}'"

    def test_exactly_100_spice_tasks(self):
        """Must have exactly 100 SPICE deck debug tasks."""
        metas = self._get_spice_metadata()
        assert len(metas) == 100, f"Expected 100 SPICE tasks, got {len(metas)}"


class TestRunCommand:
    """Test the command runner."""

    def test_run_simple_command(self):
        from validators.common.run_command import run_command
        result = run_command(["echo", "hello"])
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]
        assert result["timed_out"] is False

    def test_run_command_timeout(self):
        from validators.common.run_command import run_command
        result = run_command(["sleep", "10"], timeout_sec=1)
        assert result["timed_out"] is True

    def test_run_command_not_found(self):
        from validators.common.run_command import run_command
        result = run_command(["nonexistent_command_xyz"])
        assert result["returncode"] == -2


class TestPublicPackaging:
    """Test that public task packages are safe for release."""

    def _get_public_dirs(self):
        public_dir = REPO_ROOT / "tasks_public"
        if not public_dir.exists():
            return []
        return [d for d in public_dir.iterdir() if d.is_dir()]

    def _get_candidate_dirs(self):
        candidates_dir = REPO_ROOT / "tasks_candidates"
        if not candidates_dir.exists():
            return []
        return [d for d in candidates_dir.iterdir() if d.is_dir()]

    def _get_validated_dirs(self):
        validated_dir = REPO_ROOT / "tasks_validated"
        if not validated_dir.exists():
            return []
        return [d for d in validated_dir.iterdir() if d.is_dir()]

    def test_no_log_files_in_public_tasks(self):
        for task_dir in self._get_public_dirs():
            log_files = list(task_dir.rglob("*.log"))
            assert not log_files, f"{task_dir.name}: contains .log files: {log_files}"

    def test_no_lis_files_in_public_tasks(self):
        for task_dir in self._get_public_dirs():
            lis_files = list(task_dir.rglob("*.lis"))
            assert not lis_files, f"{task_dir.name}: contains .lis files: {lis_files}"

    def test_no_raw_sim_output_in_public_tasks(self):
        raw_exts = {".log", ".lis", ".trn", ".dsn", ".raw", ".st0", ".sw0", ".ac0", ".ic0"}
        for task_dir in self._get_public_dirs():
            for ext in raw_exts:
                files = list(task_dir.rglob(f"*{ext}"))
                assert not files, f"{task_dir.name}: contains {ext} files: {files}"

    def test_no_absolute_paths_in_public_tasks(self):
        bad_patterns = ["/home/", "/data1/", "/tmp/", "/EDA/", "/tools/", "/usr/local/"]
        for task_dir in self._get_public_dirs():
            for f in task_dir.rglob("*"):
                if f.is_file():
                    content = f.read_text(errors="replace")
                    for pattern in bad_patterns:
                        assert pattern not in content, f"{f}: contains '{pattern}'"

    def test_no_license_vars_in_public_tasks(self):
        lic_patterns = ["LM_LICENSE_FILE", "SNPSLMD_LICENSE_FILE", "CDS_LIC_FILE",
                        "license_file", "license_path", "license_server", "flexlm"]
        for task_dir in self._get_public_dirs():
            for f in task_dir.rglob("*"):
                if f.is_file():
                    content = f.read_text(errors="replace").upper()
                    for pattern in lic_patterns:
                        assert pattern.upper() not in content, f"{f}: contains '{pattern}'"

    def test_no_log_files_in_candidates(self):
        for task_dir in self._get_candidate_dirs():
            log_files = list(task_dir.rglob("*.log"))
            assert not log_files, f"{task_dir.name}: contains .log files: {log_files}"

    def test_no_absolute_paths_in_candidates(self):
        for task_dir in self._get_candidate_dirs():
            for f in task_dir.rglob("*"):
                if f.is_file():
                    content = f.read_text(errors="replace")
                    assert "/home/" not in content, f"{f}: contains /home/ path"
                    assert "/tools/" not in content, f"{f}: contains /tools/ path"

    def test_validate_one_candidate_script_exists(self):
        script = REPO_ROOT / "scripts" / "validate_one_candidate.sh"
        assert script.exists(), "scripts/validate_one_candidate.sh missing"

    def test_package_public_task_script_exists(self):
        script = REPO_ROOT / "scripts" / "package_public_task.sh"
        assert script.exists(), "scripts/package_public_task.sh missing"

    def test_validate_one_candidate_usage(self):
        script = REPO_ROOT / "scripts" / "validate_one_candidate.sh"
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 1
        assert "Usage:" in result.stdout

    def test_package_public_task_usage(self):
        script = REPO_ROOT / "scripts" / "package_public_task.sh"
        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 1
        assert "Usage:" in result.stdout


class TestPipelineFlow:
    """Test the candidate -> validated -> public pipeline."""

    def _run_script(self, args, timeout=30):
        return subprocess.run(
            args,
            capture_output=True, text=True, timeout=timeout,
            cwd=str(REPO_ROOT),
        )

    def test_package_refuses_candidates_by_default(self):
        candidate_dir = REPO_ROOT / "tasks_candidates" / "spice_deck_debug_0001"
        if not candidate_dir.exists():
            pytest.skip("tasks_candidates not generated")

        script = str(REPO_ROOT / "scripts" / "package_public_task.sh")
        result = self._run_script(["bash", script, str(candidate_dir)])

        assert result.returncode == 1
        combined = result.stdout + result.stderr
        assert "tasks_validated" in combined

    def test_package_accepts_candidates_with_flag(self):
        candidate_dir = REPO_ROOT / "tasks_candidates" / "spice_deck_debug_0001"
        if not candidate_dir.exists():
            pytest.skip("tasks_candidates not generated")

        script = str(REPO_ROOT / "scripts" / "package_public_task.sh")
        result = self._run_script(["bash", script, str(candidate_dir), "--allow-unvalidated"])

        combined = result.stdout + result.stderr
        assert "must be under tasks_validated" not in combined
        # Don't clean up — let batch packaging handle the state

    def test_package_accepts_validated_tasks(self):
        validated_dir = REPO_ROOT / "tasks_validated" / "spice_deck_debug_0001"
        if not validated_dir.exists():
            pytest.skip("No validated tasks yet")

        script = str(REPO_ROOT / "scripts" / "package_public_task.sh")
        result = self._run_script(["bash", script, str(validated_dir)])

        combined = result.stdout + result.stderr
        assert "must be under tasks_validated" not in combined
        # Don't clean up — let batch packaging handle the state

    def test_public_package_preserves_task_id(self):
        public_dirs = [d for d in (REPO_ROOT / "tasks_public").iterdir() if d.is_dir()] if (REPO_ROOT / "tasks_public").exists() else []
        for task_dir in public_dirs:
            meta = json.loads((task_dir / "metadata.json").read_text())
            assert meta["task_id"] == task_dir.name

    def test_public_package_has_public_release_safe(self):
        public_dirs = [d for d in (REPO_ROOT / "tasks_public").iterdir() if d.is_dir()] if (REPO_ROOT / "tasks_public").exists() else []
        for task_dir in public_dirs:
            meta = json.loads((task_dir / "metadata.json").read_text())
            assert meta["public_release_safe"] is True

    def test_validated_tasks_have_validation_dir(self):
        validated_dir = REPO_ROOT / "tasks_validated"
        if not validated_dir.exists():
            pytest.skip("tasks_validated/ does not exist")
        for task_dir in validated_dir.iterdir():
            if not task_dir.is_dir():
                continue
            val_dir = task_dir / "validation"
            assert val_dir.exists(), f"{task_dir.name}: missing validation/ directory"
            assert (val_dir / "validation_record.json").exists(), \
                f"{task_dir.name}: missing validation/validation_record.json"
            assert (val_dir / "raw_log.sha256").exists(), \
                f"{task_dir.name}: missing validation/raw_log.sha256"

    def test_validated_tasks_no_raw_logs(self):
        validated_dir = REPO_ROOT / "tasks_validated"
        if not validated_dir.exists():
            pytest.skip("tasks_validated/ does not exist")
        for task_dir in validated_dir.iterdir():
            if not task_dir.is_dir():
                continue
            log_files = list(task_dir.rglob("*.log"))
            assert not log_files, f"{task_dir.name}: contains .log files: {log_files}"

    def test_validation_record_has_structured_runs(self):
        """Debug tasks must have buggy_run and golden_run in validation_record.json."""
        validated_dir = REPO_ROOT / "tasks_validated"
        if not validated_dir.exists():
            pytest.skip("tasks_validated/ does not exist")
        for task_dir in validated_dir.iterdir():
            if not task_dir.is_dir():
                continue
            domain = task_dir.name.rsplit("_", 1)[0]
            if domain not in ("rtl_debug", "spice_deck_debug"):
                continue
            record_path = task_dir / "validation" / "validation_record.json"
            if not record_path.exists():
                continue
            record = json.loads(record_path.read_text())
            assert "buggy_run" in record, f"{task_dir.name}: missing buggy_run"
            assert "golden_run" in record, f"{task_dir.name}: missing golden_run"
            assert "debug_contrast" in record, f"{task_dir.name}: missing debug_contrast"

    def test_debug_contrast_verified_required_for_debug_tasks(self):
        """Debug tasks in tasks_public/ must have debug_contrast_verified status."""
        public_dir = REPO_ROOT / "tasks_public"
        if not public_dir.exists():
            pytest.skip("tasks_public/ does not exist")
        for task_dir in public_dir.iterdir():
            if not task_dir.is_dir():
                continue
            meta = json.loads((task_dir / "metadata.json").read_text())
            domain = meta.get("domain", "")
            if domain in ("rtl_debug", "spice_deck_debug"):
                assert meta["validation_status"] == "debug_contrast_verified", \
                    f"{task_dir.name}: debug task must have debug_contrast_verified, got {meta['validation_status']}"


class TestPublicSpicePackaging:
    """Test the public SPICE task package."""

    def _get_public_spice_dirs(self):
        public_dir = REPO_ROOT / "tasks_public"
        if not public_dir.exists():
            return []
        return sorted([
            d for d in public_dir.iterdir()
            if d.is_dir() and d.name.startswith("spice_deck_debug_")
        ])

    def test_public_spice_tasks_present(self):
        """Public SPICE tasks must exist in tasks_public/."""
        dirs = self._get_public_spice_dirs()
        assert len(dirs) >= 10, f"Expected at least 10 public SPICE tasks, got {len(dirs)}"

    def test_manifest_exists_with_matching_rows(self):
        """manifest.jsonl must exist with rows matching public task count."""
        manifest = REPO_ROOT / "tasks_public" / "manifest.jsonl"
        assert manifest.exists(), "tasks_public/manifest.jsonl missing"
        lines = [l for l in manifest.read_text().strip().split("\n") if l]
        dirs = self._get_public_spice_dirs()
        assert len(lines) == len(dirs), \
            f"Manifest has {len(lines)} rows but {len(dirs)} public task dirs"

    def test_manifest_tasks_exist_on_disk(self):
        """Every task in manifest.jsonl must exist as a directory."""
        manifest = REPO_ROOT / "tasks_public" / "manifest.jsonl"
        if not manifest.exists():
            pytest.skip("manifest.jsonl missing")
        for line in manifest.read_text().strip().split("\n"):
            if not line:
                continue
            row = json.loads(line)
            task_dir = REPO_ROOT / "tasks_public" / row["task_id"]
            assert task_dir.is_dir(), f"Manifest task {row['task_id']} not on disk"

    def test_every_public_task_has_release_safe(self):
        """Every public task must have public_release_safe=true."""
        for task_dir in self._get_public_spice_dirs():
            meta = json.loads((task_dir / "metadata.json").read_text())
            assert meta["public_release_safe"] is True, \
                f"{task_dir.name}: public_release_safe is not true"

    def test_every_public_task_has_contrast_verified(self):
        """Every public SPICE task must have validation_status=debug_contrast_verified."""
        for task_dir in self._get_public_spice_dirs():
            meta = json.loads((task_dir / "metadata.json").read_text())
            assert meta["validation_status"] == "debug_contrast_verified", \
                f"{task_dir.name}: expected debug_contrast_verified, got {meta['validation_status']}"

    def test_no_raw_commercial_output_leaks(self):
        """No raw commercial output files in tasks_public/."""
        raw_exts = {".log", ".lis", ".trn", ".dsn", ".raw", ".st0", ".sw0", ".ac0", ".ic0"}
        public_dir = REPO_ROOT / "tasks_public"
        if not public_dir.exists():
            pytest.skip("tasks_public/ does not exist")
        for ext in raw_exts:
            files = list(public_dir.rglob(f"*{ext}"))
            assert not files, f"Raw {ext} files found: {files}"

    def test_no_absolute_paths_in_public_spice(self):
        """No absolute paths in public SPICE tasks."""
        bad_patterns = ["/home/", "/data1/", "/tmp/", "/EDA/", "/tools/", "/usr/local/"]
        for task_dir in self._get_public_spice_dirs():
            for f in task_dir.rglob("*"):
                if f.is_file():
                    content = f.read_text(errors="replace")
                    for pattern in bad_patterns:
                        assert pattern not in content, f"{f}: contains '{pattern}'"

    def test_no_hidden_golden_solution_exposed(self):
        """Hidden golden files should not be in public packages unless explicitly allowed."""
        for task_dir in self._get_public_spice_dirs():
            meta = json.loads((task_dir / "metadata.json").read_text())
            allow_oracle = meta.get("allow_public_oracle", False)
            hidden_dir = task_dir / "hidden"
            oracle_dir = task_dir / "oracle"
            if not allow_oracle:
                assert not hidden_dir.exists() or not any(hidden_dir.iterdir()), \
                    f"{task_dir.name}: hidden/ present but allow_public_oracle not set"
                assert not oracle_dir.exists() or not any(oracle_dir.iterdir()), \
                    f"{task_dir.name}: oracle/ present but allow_public_oracle not set"

    def test_public_task_has_validation_record(self):
        """Public tasks must have validation/validation_record.json with normalized data."""
        for task_dir in self._get_public_spice_dirs():
            record_path = task_dir / "validation" / "validation_record.json"
            assert record_path.exists(), f"{task_dir.name}: missing validation_record.json"
            record = json.loads(record_path.read_text())
            assert "buggy_run" in record
            assert "golden_run" in record
            assert "debug_contrast" in record
            # Must not contain raw log content, only hashes
            assert "raw_log_sha256" in record["buggy_run"]
            assert "raw_log_retained" in record["buggy_run"]

    def test_public_task_has_normalized_errors(self):
        """Public tasks must have validation/normalized_errors.json."""
        for task_dir in self._get_public_spice_dirs():
            errors_path = task_dir / "validation" / "normalized_errors.json"
            assert errors_path.exists(), f"{task_dir.name}: missing normalized_errors.json"

    def test_public_task_has_raw_log_hash(self):
        """Public tasks must have validation/raw_log.sha256."""
        for task_dir in self._get_public_spice_dirs():
            hash_path = task_dir / "validation" / "raw_log.sha256"
            assert hash_path.exists(), f"{task_dir.name}: missing raw_log.sha256"
            content = hash_path.read_text()
            assert "buggy:" in content
            assert "golden:" in content


class TestPrivateEvalBundle:
    """Test the private evaluator bundle."""

    def _get_private_dirs(self):
        private_dir = REPO_ROOT / "tasks_eval_private"
        if not private_dir.exists():
            return []
        return sorted([
            d for d in private_dir.iterdir()
            if d.is_dir() and d.name.startswith("spice_deck_debug_")
        ])

    def _get_public_spice_ids(self):
        public_dir = REPO_ROOT / "tasks_public"
        if not public_dir.exists():
            return set()
        return {
            d.name for d in public_dir.iterdir()
            if d.is_dir() and d.name.startswith("spice_deck_debug_")
        }

    def test_every_public_task_has_matching_private(self):
        """Every public SPICE task must have a matching private eval task."""
        public_ids = self._get_public_spice_ids()
        private_dirs = self._get_private_dirs()
        private_ids = {d.name for d in private_dirs}
        missing = public_ids - private_ids
        assert not missing, f"Public tasks without private eval bundle: {missing}"

    def test_private_tasks_have_grader_contract(self):
        """Private eval tasks must contain grader_contract.json."""
        for task_dir in self._get_private_dirs():
            contract_path = task_dir / "grader_contract.json"
            assert contract_path.exists(), f"{task_dir.name}: missing grader_contract.json"

    def test_private_tasks_have_hidden_files(self):
        """Private eval tasks must contain hidden/ files."""
        for task_dir in self._get_private_dirs():
            hidden_dir = task_dir / "hidden"
            assert hidden_dir.exists(), f"{task_dir.name}: missing hidden/"
            files = list(hidden_dir.iterdir())
            assert len(files) > 0, f"{task_dir.name}: hidden/ is empty"

    def test_private_tasks_have_oracle_files(self):
        """Private eval tasks must contain oracle/ files."""
        for task_dir in self._get_private_dirs():
            oracle_dir = task_dir / "oracle"
            assert oracle_dir.exists(), f"{task_dir.name}: missing oracle/"
            files = list(oracle_dir.iterdir())
            assert len(files) > 0, f"{task_dir.name}: oracle/ is empty"

    def test_private_tasks_no_raw_logs(self):
        """Private eval tasks must not contain raw .log/.lis/.raw files."""
        raw_exts = {".log", ".lis", ".raw"}
        for task_dir in self._get_private_dirs():
            for ext in raw_exts:
                files = list(task_dir.rglob(f"*{ext}"))
                assert not files, f"{task_dir.name}: raw {ext} files found: {files}"

    def test_grader_contract_conforms_to_schema(self):
        """Grader contract must conform to the schema."""
        schema_path = REPO_ROOT / "schemas" / "grader_contract_schema.json"
        if not schema_path.exists():
            pytest.skip("grader_contract_schema.json missing")
        schema = json.loads(schema_path.read_text())
        for task_dir in self._get_private_dirs():
            contract_path = task_dir / "grader_contract.json"
            if not contract_path.exists():
                continue
            contract = json.loads(contract_path.read_text())
            jsonschema.validate(contract, schema)

    def test_editable_files_under_visible(self):
        """editable_files must point to files under visible/."""
        for task_dir in self._get_private_dirs():
            contract_path = task_dir / "grader_contract.json"
            if not contract_path.exists():
                continue
            contract = json.loads(contract_path.read_text())
            for f in contract["editable_files"]:
                assert f.startswith("visible/"), \
                    f"{task_dir.name}: editable_file '{f}' not under visible/"

    def test_backend_env_var_is_hspice(self):
        """backend_env_var must be EDA_HSPICE_CMD for SPICE tasks."""
        for task_dir in self._get_private_dirs():
            contract_path = task_dir / "grader_contract.json"
            if not contract_path.exists():
                continue
            contract = json.loads(contract_path.read_text())
            assert contract["backend_env_var"] == "EDA_HSPICE_CMD", \
                f"{task_dir.name}: expected EDA_HSPICE_CMD, got {contract['backend_env_var']}"

    def test_success_criteria_no_exact_diff(self):
        """success_criteria must not require exact diff match."""
        for task_dir in self._get_private_dirs():
            contract_path = task_dir / "grader_contract.json"
            if not contract_path.exists():
                continue
            contract = json.loads(contract_path.read_text())
            criteria = contract["success_criteria"]
            assert criteria["execution_based"] is True, \
                f"{task_dir.name}: success_criteria.execution_based must be True"
            assert criteria["exit_code"] == 0
            assert criteria["no_fatal_errors"] is True


class TestReleaseSafety:
    """Test the release safety scanner."""

    def _run_safety_check(self, target_dir, timeout=30):
        script = REPO_ROOT / "scripts" / "check_release_safety.sh"
        return subprocess.run(
            ["bash", str(script), str(target_dir)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(REPO_ROOT),
        )

    def test_tasks_public_passes_safety_check(self):
        """tasks_public/ must pass the release safety scanner."""
        public_dir = REPO_ROOT / "tasks_public"
        if not public_dir.exists() or not any(public_dir.iterdir()):
            pytest.skip("tasks_public/ is empty")
        result = self._run_safety_check(public_dir)
        assert result.returncode == 0, f"Safety check failed:\n{result.stdout}\n{result.stderr}"

    def test_tasks_eval_private_fails_safety_check(self):
        """tasks_eval_private/ must fail the safety scanner (contains hidden/oracle)."""
        private_dir = REPO_ROOT / "tasks_eval_private"
        if not private_dir.exists() or not any(private_dir.iterdir()):
            pytest.skip("tasks_eval_private/ is empty")
        result = self._run_safety_check(private_dir)
        assert result.returncode != 0, "Safety check should have failed for private bundle"

    def test_raw_log_fixture_fails(self, tmp_path):
        """A directory containing a .log file must fail the safety scanner."""
        # Create a fixture with a raw log file
        fixture_dir = tmp_path / "bad_package"
        fixture_dir.mkdir()
        (fixture_dir / "test.log").write_text("HSPICE raw log content")
        (fixture_dir / "metadata.json").write_text('{"task_id": "test"}')

        result = self._run_safety_check(fixture_dir)
        assert result.returncode != 0, "Safety check should have failed for .log file"

    def test_license_variable_fixture_fails(self, tmp_path):
        """A directory containing license variable references must fail."""
        fixture_dir = tmp_path / "bad_package"
        fixture_dir.mkdir()
        (fixture_dir / "config.json").write_text('{"license": "LM_LICENSE_FILE=27000@server"}')

        result = self._run_safety_check(fixture_dir)
        assert result.returncode != 0, "Safety check should have failed for license variable"

    def test_absolute_path_fixture_fails(self, tmp_path):
        """A directory containing absolute paths must fail."""
        fixture_dir = tmp_path / "bad_package"
        fixture_dir.mkdir()
        (fixture_dir / "data.json").write_text('{"path": "/EDA/tools/hspice/bin/hspice"}')

        result = self._run_safety_check(fixture_dir)
        assert result.returncode != 0, "Safety check should have failed for absolute path"

    def test_hidden_directory_fixture_fails(self, tmp_path):
        """A directory containing hidden/ must fail."""
        fixture_dir = tmp_path / "bad_package"
        fixture_dir.mkdir()
        hidden = fixture_dir / "hidden"
        hidden.mkdir()
        (hidden / "solution.sp").write_text("fixed circuit")

        result = self._run_safety_check(fixture_dir)
        assert result.returncode != 0, "Safety check should have failed for hidden/ directory"

    def test_safe_fixture_passes(self, tmp_path):
        """A clean directory with no violations must pass."""
        fixture_dir = tmp_path / "good_package"
        fixture_dir.mkdir()
        (fixture_dir / "metadata.json").write_text('{"task_id": "test", "public_release_safe": true}')
        (fixture_dir / "prompt.md").write_text("# Test task")
        visible = fixture_dir / "visible"
        visible.mkdir()
        (visible / "test.sp").write_text("R1 in out 1k\n.end")

        result = self._run_safety_check(fixture_dir)
        assert result.returncode == 0, f"Safety check should have passed:\n{result.stdout}"
