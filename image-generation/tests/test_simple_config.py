"""test_simple_config.py — Integration tests for simple_config.py.

All tests run simple_config.py as a subprocess (dry-run) to validate
argument resolution, output format, and exit codes without invoking
generate.py or loading any ML models.

Covers the 4 integration test cases from PRD §13.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

import pytest

_IMAGE_GEN_DIR = Path(__file__).parent.parent
_SIMPLE_CONFIG = str(_IMAGE_GEN_DIR / "simple_config.py")


def _run(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run simple_config.py with given args in the image-generation/ directory."""
    cmd = [sys.executable, _SIMPLE_CONFIG, *args]
    return subprocess.run(
        cmd,
        cwd=str(_IMAGE_GEN_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _parse_resolved_cmd(stdout: str) -> list[str]:
    """Extract and shlex-split the resolved generate.py command from stdout."""
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith(sys.executable) or ("generate.py" in line and line.startswith("/")):
            return shlex.split(line)
        # Also handle Windows paths and quoted python
        if "generate.py" in line and not line.startswith("["):
            return shlex.split(line)
    # Fall back: look for python in any line that contains generate.py
    for line in stdout.splitlines():
        if "generate.py" in line and "--steps" in line:
            return shlex.split(line.strip())
    return []


# ---------------------------------------------------------------------------
# Test 1 — Dry-run mode
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDryRunMode:
    def test_dry_run_exits_zero(self):
        """--preset standard --dry-run exits with code 0."""
        result = _run("--preset", "standard", "--dry-run")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_dry_run_prints_resolved_command(self):
        """--dry-run prints a line containing 'generate.py'."""
        result = _run("--preset", "standard", "--dry-run")
        assert "generate.py" in result.stdout, f"Expected generate.py in output:\n{result.stdout}"

    def test_dry_run_prints_dry_run_marker(self):
        """--dry-run prints the [dry-run] summary line."""
        result = _run("--preset", "standard", "--dry-run")
        assert "[dry-run]" in result.stdout, f"Expected [dry-run] marker:\n{result.stdout}"

    def test_dry_run_does_not_generate(self):
        """--dry-run should complete in under 10 seconds (no model loading)."""
        result = _run("--preset", "standard", "--dry-run", timeout=10)
        assert result.returncode == 0

    def test_dry_run_with_prompt_exits_zero(self):
        """--dry-run with --prompt exits 0 and includes prompt in resolved command."""
        result = _run("--prompt", "a sunny beach, no text", "--preset", "standard", "--dry-run")
        assert result.returncode == 0
        assert "generate.py" in result.stdout


# ---------------------------------------------------------------------------
# Test 2 — Arg passthrough
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestArgPassthrough:
    """Verify that --preset production --style watercolor --size blog-hero
    produces the correct resolved generate.py arguments."""

    def _get_resolved_args(self) -> list[str]:
        result = _run(
            "--prompt", "test prompt, no text",
            "--preset", "production",
            "--style", "watercolor",
            "--size", "blog-hero",
            "--dry-run",
        )
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        return _parse_resolved_cmd(result.stdout)

    def test_steps_35(self):
        args = self._get_resolved_args()
        assert "--steps" in args
        idx = args.index("--steps")
        assert args[idx + 1] == "35"

    def test_refine_flag_present(self):
        args = self._get_resolved_args()
        assert "--refine" in args

    def test_refiner_steps_15(self):
        args = self._get_resolved_args()
        assert "--refiner-steps" in args
        idx = args.index("--refiner-steps")
        assert args[idx + 1] == "15"

    def test_guidance_6_5(self):
        args = self._get_resolved_args()
        assert "--guidance" in args
        idx = args.index("--guidance")
        assert args[idx + 1] == "6.5"

    def test_lora_watercolor(self):
        args = self._get_resolved_args()
        assert "--lora" in args
        idx = args.index("--lora")
        assert args[idx + 1] == "joachim_s/aether-watercolor-and-ink-sdxl"

    def test_lora_weight_0_8(self):
        args = self._get_resolved_args()
        assert "--lora-weight" in args
        idx = args.index("--lora-weight")
        assert args[idx + 1] == "0.8"

    def test_width_1200(self):
        args = self._get_resolved_args()
        assert "--width" in args
        idx = args.index("--width")
        assert args[idx + 1] == "1200"

    def test_height_632(self):
        args = self._get_resolved_args()
        assert "--height" in args
        idx = args.index("--height")
        assert args[idx + 1] == "632"

    def test_watercolor_tokens_in_prompt(self):
        """Prompt in resolved command must start with watercolor style tokens."""
        result = _run(
            "--prompt", "test prompt, no text",
            "--preset", "production",
            "--style", "watercolor",
            "--size", "blog-hero",
            "--dry-run",
        )
        assert "Watercolor illustration" in result.stdout

    def test_standard_no_refine(self):
        """--preset standard should NOT include --refine in output."""
        result = _run(
            "--prompt", "test, no text",
            "--preset", "standard",
            "--dry-run",
        )
        resolved = _parse_resolved_cmd(result.stdout)
        assert "--refine" not in resolved

    def test_square_size_no_width_height(self):
        """--size square should NOT add --width/--height (they are generate.py defaults)."""
        result = _run(
            "--prompt", "test, no text",
            "--preset", "standard",
            "--size", "square",
            "--dry-run",
        )
        resolved = _parse_resolved_cmd(result.stdout)
        assert "--width" not in resolved
        assert "--height" not in resolved

    def test_folk_art_default_tokens(self):
        """When no --style is given, folk-art tokens are prepended by default."""
        result = _run(
            "--prompt", "a scenic mountain, no text",
            "--preset", "standard",
            "--dry-run",
        )
        assert "Latin American folk art style" in result.stdout

    def test_no_default_style_suppresses_tokens(self):
        """--no-default-style prevents folk-art token injection."""
        result = _run(
            "--prompt", "a scenic mountain, no text",
            "--preset", "standard",
            "--no-default-style",
            "--dry-run",
        )
        assert "Latin American folk art style" not in result.stdout

    def test_style_none_suppresses_tokens(self):
        """--style none is equivalent to --no-default-style."""
        result = _run(
            "--prompt", "a scenic mountain, no text",
            "--preset", "standard",
            "--style", "none",
            "--dry-run",
        )
        assert "Latin American folk art style" not in result.stdout

    def test_modifier_dreamier_changes_guidance(self):
        """--modifier dreamier should set guidance to 4.0 in resolved command."""
        result = _run(
            "--prompt", "test, no text",
            "--preset", "standard",
            "--modifier", "dreamier",
            "--no-default-style",
            "--dry-run",
        )
        resolved = _parse_resolved_cmd(result.stdout)
        assert "--guidance" in resolved
        idx = resolved.index("--guidance")
        assert resolved[idx + 1] == "4.0"

    def test_seed_passthrough(self):
        """--seed should appear in resolved command."""
        result = _run(
            "--prompt", "test, no text",
            "--preset", "standard",
            "--seed", "42",
            "--dry-run",
        )
        resolved = _parse_resolved_cmd(result.stdout)
        assert "--seed" in resolved
        idx = resolved.index("--seed")
        assert resolved[idx + 1] == "42"

    def test_cpu_flag_passthrough(self):
        """--cpu should appear in resolved command."""
        result = _run(
            "--prompt", "test, no text",
            "--preset", "standard",
            "--cpu",
            "--dry-run",
        )
        resolved = _parse_resolved_cmd(result.stdout)
        assert "--cpu" in resolved


# ---------------------------------------------------------------------------
# Test 3 — generate.py reachability (--help)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestHelpReachability:
    def test_help_exits_zero_within_10_seconds(self):
        """python simple_config.py --help exits 0 within 10 seconds."""
        result = _run("--help", timeout=10)
        assert result.returncode == 0

    def test_help_output_mentions_preset(self):
        """--help output should describe the --preset option."""
        result = _run("--help", timeout=10)
        assert "preset" in result.stdout.lower()

    def test_help_with_args_still_exits_zero(self):
        """argparse --help takes priority regardless of other args."""
        result = _run("--preset", "standard", "--help", timeout=10)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Test 4 — Batch-file dry-run
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestBatchFileDryRun:
    """python simple_config.py --preset standard --batch-file tests/fixtures/batch-two-jobs.json --dry-run"""

    _BATCH_FILE = "tests/fixtures/batch-two-jobs.json"

    def _run_batch(self, *extra: str) -> subprocess.CompletedProcess:
        return _run(
            "--preset", "standard",
            "--batch-file", self._BATCH_FILE,
            "--dry-run",
            *extra,
        )

    def test_batch_dry_run_exits_zero(self):
        result = self._run_batch()
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"

    def test_batch_prints_job_1_marker(self):
        result = self._run_batch()
        assert "[job 1/2]" in result.stdout

    def test_batch_prints_job_2_marker(self):
        result = self._run_batch()
        assert "[job 2/2]" in result.stdout

    def test_batch_prints_dry_run_summary(self):
        result = self._run_batch()
        assert "[dry-run]" in result.stdout
        assert "2 jobs resolved" in result.stdout

    def test_batch_dry_run_zero_calls(self):
        """Dry-run must state 0 generate.py calls made."""
        result = self._run_batch()
        assert "0 generate.py calls made" in result.stdout

    def test_batch_jobs_get_folk_art_tokens(self):
        """With no --style, default folk-art tokens are prepended to each job's prompt."""
        result = self._run_batch()
        assert "Latin American folk art style" in result.stdout

    def test_batch_jobs_distinct_seeds(self):
        """Each job should carry its own seed from the fixture."""
        result = self._run_batch("--no-default-style")
        assert "--seed 42" in result.stdout or "seed' '42'" in result.stdout or "'--seed', '42'" in result.stdout
        # More reliable: just check both seeds appear somewhere in output
        assert "42" in result.stdout
        assert "43" in result.stdout

    def test_batch_file_not_found_exits_nonzero(self):
        result = _run(
            "--preset", "standard",
            "--batch-file", "nonexistent-file.json",
            "--dry-run",
        )
        assert result.returncode != 0

    def test_batch_with_watercolor_style(self):
        """Batch with --style watercolor injects watercolor tokens into each job."""
        result = _run(
            "--preset", "production",
            "--style", "watercolor",
            "--batch-file", self._BATCH_FILE,
            "--dry-run",
        )
        assert result.returncode == 0
        assert "Watercolor illustration" in result.stdout
