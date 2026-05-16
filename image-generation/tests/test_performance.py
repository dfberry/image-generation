"""
Performance baseline tests.

Tests TPF-01 through TPF-03 per PRD §9.2.
Does NOT require GPU — pure logic/mock pipeline timing.
"""

import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from generate import _build_lora_list, _save_with_metadata


def _get_generate_cwd():
    return str(Path(__file__).parent.parent)


@pytest.mark.perf
class TestPerformanceBaselines:
    """Performance thresholds from tests/perf-baselines.json."""

    @pytest.mark.integration
    def test_dry_run_resolves_in_under_30_seconds(self):
        """TPF-01: Wall clock for --dry-run subprocess call < 30.0s (includes cold torch import)."""
        start = time.monotonic()
        result = subprocess.run(
            [sys.executable, "generate.py", "--prompt", "Test", "--dry-run"],
            capture_output=True, text=True, cwd=_get_generate_cwd()
        )
        elapsed = time.monotonic() - start
        assert result.returncode == 0
        assert elapsed < 30.0, f"dry-run took {elapsed:.2f}s, threshold 30.0s"

    def test_multi_lora_build_list_under_500ms_for_3_adapters(self):
        """TPF-02: _build_lora_list() with 3 LoRAs completes in < 500ms."""
        args = SimpleNamespace(
            lora=["hf/a", "hf/b", "hf/c"],
            lora_weight=[0.8, 0.7, 0.6],
        )
        start = time.monotonic()
        for _ in range(1000):
            _build_lora_list(args)
        # Total for 1000 calls should be < 500ms => each call < 0.5ms
        assert (time.monotonic() - start) * 1000 < 500, "1000 calls took > 500ms"

    def test_png_metadata_write_overhead_under_100ms(self, tmp_path):
        """TPF-03: _save_with_metadata() vs plain save overhead < 100ms."""
        img = Image.new("RGB", (1024, 1024), color=(128, 128, 128))
        params = {
            "prompt": "Test",
            "negative_prompt": "bad",
            "seed": 42,
            "steps": 22,
            "guidance": 6.5,
            "width": 1024,
            "height": 1024,
            "model": "precise",
            "scheduler": "DPMSolverMultistepScheduler",
            "loras": [],
            "refine": False,
            "refiner_steps": 10,
            "generated_at": "2026-05-16T06:48:00",
        }

        plain_out = str(tmp_path / "plain.png")
        meta_out = str(tmp_path / "meta.png")

        # Time plain save
        start_plain = time.monotonic()
        img.save(plain_out)
        plain_ms = (time.monotonic() - start_plain) * 1000

        # Time metadata save
        start_meta = time.monotonic()
        _save_with_metadata(img, meta_out, params)
        meta_ms = (time.monotonic() - start_meta) * 1000

        overhead_ms = meta_ms - plain_ms
        # Allow for variation — what matters is overhead is < 100ms
        # (actual overhead is typically < 5ms)
        assert meta_ms < plain_ms + 100, f"metadata overhead was {overhead_ms:.1f}ms, threshold 100ms"
