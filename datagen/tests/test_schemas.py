"""Tests for JSON schema validity and task metadata validation."""

import json
import re
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
TASKS_DIR = REPO_ROOT / "tasks_candidates"


class TestSchemaFiles:
    """Test that schema files are valid JSON Schema."""

    def test_task_schema_is_valid_json(self):
        with open(SCHEMAS_DIR / "task_schema.json") as f:
            schema = json.load(f)
        assert schema["$schema"]
        assert "properties" in schema

    def test_validation_record_schema_is_valid_json(self):
        with open(SCHEMAS_DIR / "validation_record_schema.json") as f:
            schema = json.load(f)
        assert schema["$schema"]
        assert "properties" in schema

    def test_grader_contract_schema_is_valid_json(self):
        with open(SCHEMAS_DIR / "grader_contract_schema.json") as f:
            schema = json.load(f)
        assert schema["$schema"]
        assert "properties" in schema
        required = schema.get("required", [])
        assert "task_id" in required
        assert "success_criteria" in required
        assert "command_template" in required

    def test_task_schema_has_required_fields(self):
        with open(SCHEMAS_DIR / "task_schema.json") as f:
            schema = json.load(f)
        required = schema.get("required", [])
        assert "task_id" in required
        assert "domain" in required
        assert "task_family" in required
        assert "difficulty" in required
        assert "public_release_safe" in required

    def test_validation_record_schema_has_required_fields(self):
        with open(SCHEMAS_DIR / "validation_record_schema.json") as f:
            schema = json.load(f)
        required = schema.get("required", [])
        assert "task_id" in required
        assert "backend" in required
        assert "validation_status" in required
        # run_record sub-schema has the log fields
        run_record = schema.get("$defs", {}).get("run_record", {})
        run_required = run_record.get("required", [])
        assert "raw_log_sha256" in run_required
        assert "raw_log_retained" in run_required


class TestTaskMetadata:
    """Test that all generated tasks have valid metadata."""

    @pytest.fixture(autouse=True)
    def load_schemas(self):
        with open(SCHEMAS_DIR / "task_schema.json") as f:
            self.task_schema = json.load(f)

    def _get_task_dirs(self):
        if not TASKS_DIR.exists():
            pytest.skip("tasks_candidates not generated yet")
        return sorted(TASKS_DIR.iterdir())

    def test_all_tasks_validate_against_schema(self):
        errors = []
        for task_dir in self._get_task_dirs():
            meta_file = task_dir / "metadata.json"
            if not meta_file.exists():
                errors.append(f"{task_dir.name}: missing metadata.json")
                continue
            with open(meta_file) as f:
                meta = json.load(f)
            try:
                jsonschema.validate(meta, self.task_schema)
            except jsonschema.ValidationError as e:
                errors.append(f"{task_dir.name}: {e.message}")
        assert not errors, "Metadata validation errors:\n" + "\n".join(errors)

    def test_task_ids_match_directory_names(self):
        for task_dir in self._get_task_dirs():
            meta_file = task_dir / "metadata.json"
            if not meta_file.exists():
                continue
            with open(meta_file) as f:
                meta = json.load(f)
            assert meta["task_id"] == task_dir.name

    def test_prompt_files_exist(self):
        for task_dir in self._get_task_dirs():
            meta_file = task_dir / "metadata.json"
            if not meta_file.exists():
                continue
            with open(meta_file) as f:
                meta = json.load(f)
            prompt_path = task_dir / meta["prompt_file"]
            assert prompt_path.exists(), f"{task_dir.name}: prompt file {meta['prompt_file']} missing"

    def test_visible_files_exist(self):
        for task_dir in self._get_task_dirs():
            meta_file = task_dir / "metadata.json"
            if not meta_file.exists():
                continue
            with open(meta_file) as f:
                meta = json.load(f)
            for vf in meta["visible_files"]:
                assert (task_dir / vf).exists(), f"{task_dir.name}: visible file {vf} missing"

    def test_public_release_safe(self):
        for task_dir in self._get_task_dirs():
            meta_file = task_dir / "metadata.json"
            if not meta_file.exists():
                continue
            with open(meta_file) as f:
                meta = json.load(f)
            assert meta["public_release_safe"] is True, f"{task_dir.name}: not marked public_release_safe"

    def test_normalized_task_id_format(self):
        """All task IDs must use 4-digit zero-padded numbering."""
        for task_dir in self._get_task_dirs():
            meta_file = task_dir / "metadata.json"
            if not meta_file.exists():
                continue
            with open(meta_file) as f:
                meta = json.load(f)
            task_id = meta["task_id"]
            assert re.match(r"^[a-z_]+_\d{4}$", task_id), \
                f"{task_dir.name}: task_id '{task_id}' does not match <domain>_NNNN format"

    def test_domain_matches_task_id(self):
        """The domain field must match the task_id prefix."""
        for task_dir in self._get_task_dirs():
            meta_file = task_dir / "metadata.json"
            if not meta_file.exists():
                continue
            with open(meta_file) as f:
                meta = json.load(f)
            task_id = meta["task_id"]
            domain = meta["domain"]
            assert task_id.startswith(domain + "_"), \
                f"{task_dir.name}: task_id '{task_id}' does not start with domain '{domain}'"
