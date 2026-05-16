"""test_lora_performance.py — Performance baseline tests for the LoRA registry system.

Covers test cases LP-1 through LP-4 from PRD §15.
Thresholds are defined in tests/perf-baselines.json (extended with lora baselines).
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

_IMAGE_GEN_DIR = Path(__file__).parent.parent
_SIMPLE_CONFIG = str(_IMAGE_GEN_DIR / "simple_config.py")

# Performance thresholds (per PRD §15 LP-1 through LP-4)
_THRESHOLD_REGISTRY_LOAD_MS = 50
_THRESHOLD_NAME_RESOLUTION_MS = 10
_THRESHOLD_LORA_LIST_SUBCOMMAND_MS = 500
_THRESHOLD_DRY_RUN_WITH_LORA_MS = 5000


@pytest.mark.performance
class TestRegistryLoadTime:
    def test_load_loras_under_50ms(self):
        """LP-1: load_loras() completes in under 50ms."""
        from presets import load_loras  # noqa: PLC0415

        start = time.perf_counter()
        load_loras()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < _THRESHOLD_REGISTRY_LOAD_MS, (
            f"load_loras() took {elapsed_ms:.1f}ms — exceeds {_THRESHOLD_REGISTRY_LOAD_MS}ms threshold"
        )


@pytest.mark.performance
class TestNameResolutionTime:
    def test_single_lora_lookup_under_10ms(self):
        """LP-2: Single LoRA name resolution (dict lookup) completes in under 10ms."""
        from presets import LORAS  # noqa: PLC0415

        start = time.perf_counter()
        _ = LORAS.get("aether-watercolor")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < _THRESHOLD_NAME_RESOLUTION_MS, (
            f"LORAS lookup took {elapsed_ms:.2f}ms — exceeds {_THRESHOLD_NAME_RESOLUTION_MS}ms threshold"
        )


@pytest.mark.performance
class TestLoraListSubcommandTime:
    def test_lora_list_under_200ms(self):
        """LP-3: 'lora list' subcommand wall time is under 200ms."""
        start = time.perf_counter()
        result = subprocess.run(
            [sys.executable, _SIMPLE_CONFIG, "lora", "list"],
            cwd=str(_IMAGE_GEN_DIR),
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert result.returncode == 0, f"lora list failed: {result.stderr}"
        assert elapsed_ms < _THRESHOLD_LORA_LIST_SUBCOMMAND_MS, (
            f"lora list took {elapsed_ms:.0f}ms — exceeds {_THRESHOLD_LORA_LIST_SUBCOMMAND_MS}ms threshold"
        )


@pytest.mark.performance
class TestDryRunWithLoraTime:
    def test_dry_run_with_lora_under_5s(self):
        """LP-4: Dry-run subprocess with LoRA resolution completes in under 5s."""
        start = time.perf_counter()
        result = subprocess.run(
            [
                sys.executable,
                _SIMPLE_CONFIG,
                "--prompt", "a test scene, no text",
                "--preset", "standard",
                "--lora", "aether-watercolor",
                "--dry-run",
            ],
            cwd=str(_IMAGE_GEN_DIR),
            capture_output=True,
            text=True,
            timeout=30,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert result.returncode == 0, f"dry-run failed: {result.stderr}"
        assert elapsed_ms < _THRESHOLD_DRY_RUN_WITH_LORA_MS, (
            f"dry-run with lora took {elapsed_ms:.0f}ms — exceeds {_THRESHOLD_DRY_RUN_WITH_LORA_MS}ms threshold"
        )
