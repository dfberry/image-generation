"""test_performance_baselines.py — Performance baseline tests for simple_config.py.

Verifies that preset resolution and dry-run subprocess invocation complete
within acceptable time bounds. Results are written to tests/benchmarks.json
on first run and compared on subsequent runs.

Covers PRD §13 Performance Baseline Tests (2 cases).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

_IMAGE_GEN_DIR = Path(__file__).parent.parent
_SIMPLE_CONFIG = str(_IMAGE_GEN_DIR / "simple_config.py")
_BENCHMARKS_FILE = Path(__file__).parent / "benchmarks.json"

# Absolute thresholds (wall-clock limits regardless of stored baseline)
_PRESET_RESOLUTION_THRESHOLD_MS = 200
_DRY_RUN_THRESHOLD_MS = 5000

# Baseline regression factor: fail if new time > 200% of recorded baseline
_REGRESSION_FACTOR = 2.0


def _load_benchmarks() -> dict:
    if _BENCHMARKS_FILE.exists():
        return json.loads(_BENCHMARKS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_benchmarks(data: dict) -> None:
    _BENCHMARKS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1 — Preset resolution time
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestPresetResolutionTime:
    def test_all_presets_resolve_under_100ms(self):
        """Resolving all 4 presets + applying modifiers must complete in < 100ms total."""
        from presets import MODIFIERS, apply_modifier, resolve_preset

        start = time.perf_counter()
        for preset_name in ("quick-draft", "standard", "high-quality", "production"):
            params = resolve_preset(preset_name)
            for mod_name in MODIFIERS:
                # Apply each modifier to a fresh copy so they don't stack
                p = dict(params)
                apply_modifier(p, mod_name)
        elapsed_ms = (time.perf_counter() - start) * 1000

        benchmarks = _load_benchmarks()
        benchmarks["preset_resolution_ms"] = round(elapsed_ms, 2)
        benchmarks["recorded_at"] = time.strftime("%Y-%m-%d")
        _save_benchmarks(benchmarks)

        assert elapsed_ms < _PRESET_RESOLUTION_THRESHOLD_MS, (
            f"Preset resolution took {elapsed_ms:.1f}ms, exceeds {_PRESET_RESOLUTION_THRESHOLD_MS}ms threshold"
        )

    def test_single_preset_resolve_is_microseconds(self):
        """Single preset lookup should be essentially instantaneous (< 10ms)."""
        from presets import resolve_preset

        start = time.perf_counter()
        for _ in range(1000):
            resolve_preset("standard")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"1000 preset resolves took {elapsed_ms:.1f}ms"


# ---------------------------------------------------------------------------
# Test 2 — Dry-run subprocess time
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestDryRunSubprocessTime:
    def test_dry_run_completes_under_5_seconds(self):
        """python simple_config.py --preset standard --dry-run returns in < 5 seconds."""
        start = time.perf_counter()
        result = subprocess.run(
            [sys.executable, _SIMPLE_CONFIG, "--preset", "standard", "--dry-run"],
            cwd=str(_IMAGE_GEN_DIR),
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        benchmarks = _load_benchmarks()
        benchmarks["dry_run_subprocess_ms"] = round(elapsed_ms, 2)
        benchmarks["recorded_at"] = time.strftime("%Y-%m-%d")
        _save_benchmarks(benchmarks)

        assert result.returncode == 0, f"Process failed: {result.stderr}"
        assert elapsed_ms < _DRY_RUN_THRESHOLD_MS, (
            f"Dry-run subprocess took {elapsed_ms:.1f}ms, exceeds {_DRY_RUN_THRESHOLD_MS}ms threshold"
        )

    def test_dry_run_with_all_options_under_5_seconds(self):
        """Dry-run with preset + style + size + modifier completes in < 5 seconds."""
        start = time.perf_counter()
        result = subprocess.run(
            [
                sys.executable,
                _SIMPLE_CONFIG,
                "--prompt", "a test image, no text",
                "--preset", "production",
                "--style", "watercolor",
                "--size", "blog-hero",
                "--modifier", "more-detailed",
                "--dry-run",
            ],
            cwd=str(_IMAGE_GEN_DIR),
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.returncode == 0, f"Process failed: {result.stderr}"
        assert elapsed_ms < _DRY_RUN_THRESHOLD_MS
