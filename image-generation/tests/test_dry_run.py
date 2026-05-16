"""
Tests for --dry-run mode.

Tests TDR-01 through TDR-10 per PRD §9.2.
All tests use subprocess invocation — no GPU required.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _run_dry_run(*extra_args, cwd=None):
    """Helper to invoke generate.py --dry-run and return CompletedProcess."""
    cmd = [sys.executable, "generate.py", "--prompt", "Test dry run prompt", "--dry-run"] + list(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or ".")


def _get_generate_cwd():
    """Return the image-generation directory for subprocess calls."""
    here = Path(__file__).parent.parent  # image-generation/
    return str(here)


@pytest.mark.integration
class TestDryRun:
    """--dry-run exits 0, produces valid JSON, does not create output files."""

    def test_dry_run_exits_with_code_zero(self):
        """TDR-01: generate.py --prompt '...' --dry-run exits 0."""
        result = _run_dry_run(cwd=_get_generate_cwd())
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}. stderr: {result.stderr}"

    def test_dry_run_produces_valid_json_on_stdout(self):
        """TDR-02: stdout is parseable by json.loads()."""
        result = _run_dry_run(cwd=_get_generate_cwd())
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, dict)

    def test_dry_run_json_has_resolved_key(self):
        """TDR-03: Output has top-level 'resolved' key."""
        result = _run_dry_run(cwd=_get_generate_cwd())
        parsed = json.loads(result.stdout)
        assert "resolved" in parsed

    def test_dry_run_resolved_contains_all_expected_fields(self):
        """TDR-04: resolved contains all required fields."""
        result = _run_dry_run(cwd=_get_generate_cwd())
        resolved = json.loads(result.stdout)["resolved"]
        required = ["prompt", "negative_prompt", "steps", "guidance", "width", "height",
                    "scheduler", "loras", "refine", "model", "output", "device", "dry_run"]
        for field in required:
            assert field in resolved, f"Missing field in resolved: {field}"

    def test_dry_run_does_not_create_output_file(self, tmp_path):
        """TDR-05: No PNG file is created when --dry-run is set."""
        out_path = tmp_path / "should_not_exist.png"
        result = _run_dry_run("--output", str(out_path), cwd=_get_generate_cwd())
        assert result.returncode == 0
        assert not out_path.exists()

    def test_dry_run_resolved_dry_run_field_is_true(self):
        """TDR-06: resolved['dry_run'] is explicitly True, not just present."""
        result = _run_dry_run(cwd=_get_generate_cwd())
        resolved = json.loads(result.stdout)["resolved"]
        assert resolved["dry_run"] is True

    def test_dry_run_with_seed_shows_seed_in_resolved(self):
        """TDR-07: --seed 42 --dry-run -> resolved['effective_seed'] is 42."""
        result = _run_dry_run("--seed", "42", cwd=_get_generate_cwd())
        resolved = json.loads(result.stdout)["resolved"]
        assert resolved["effective_seed"] == 42

    def test_dry_run_with_lora_shows_lora_in_resolved(self):
        """TDR-08: --lora hf/model --dry-run -> resolved['loras'] is [['hf/model', 0.8]]."""
        result = _run_dry_run("--lora", "hf/model", cwd=_get_generate_cwd())
        resolved = json.loads(result.stdout)["resolved"]
        assert resolved["loras"] == [["hf/model", 0.8]]

    def test_dry_run_with_model_shows_model_in_resolved(self):
        """TDR-09: --model precise --dry-run -> resolved['model'] is 'precise'."""
        result = _run_dry_run("--model", "precise", cwd=_get_generate_cwd())
        resolved = json.loads(result.stdout)["resolved"]
        assert resolved["model"] == "precise"

    def test_dry_run_completes_in_under_30_seconds(self):
        """TDR-10: Wall-clock time for --dry-run invocation < 30.0 seconds (includes cold torch import)."""
        start = time.monotonic()
        result = _run_dry_run(cwd=_get_generate_cwd())
        elapsed = time.monotonic() - start
        assert result.returncode == 0
        assert elapsed < 30.0, f"dry-run took {elapsed:.2f}s, expected < 30.0s"
