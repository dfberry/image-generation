"""test_reproducibility_lora.py — LoRA determinism and seed stability tests.

Covers test cases RL-1 through RL-3 from PRD §15.
These tests validate that the wrapper parameter layer is deterministic;
image-level pixel determinism requires generate.py engine changes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

_IMAGE_GEN_DIR = Path(__file__).parent.parent
_SIMPLE_CONFIG = str(_IMAGE_GEN_DIR / "simple_config.py")


@pytest.mark.reproducibility
class TestParamDeterminismWithLora:
    def test_same_inputs_produce_identical_resolved_params(self):
        """RL-1: Same preset + LoRA name + seed → identical resolved parameter dict
        across 10 consecutive calls (no state mutation between calls).
        """
        import argparse  # noqa: PLC0415

        from simple_config import apply_prompt_and_style, resolve_base_params  # noqa: PLC0415

        # Build a minimal args namespace
        args = argparse.Namespace(
            preset="standard",
            modifiers=None,
            model=None,
            size=None,
            width=None,
            height=None,
            seed=42,
            output=None,
            cpu=False,
            negative_prompt=None,
        )

        results = []
        for _ in range(10):
            base = resolve_base_params(args)
            params = apply_prompt_and_style(
                base,
                "a test scene, no text",
                None,  # no style
                True,  # no_default_style
                "aether-watercolor",
                None,
            )
            results.append((params["lora"], params["lora_weight"], params["steps"]))

        first = results[0]
        for i, r in enumerate(results[1:], 1):
            assert r == first, (
                f"Run {i} produced different params: {r} vs {first}"
            )


@pytest.mark.reproducibility
class TestWeightAliasDeterminism:
    def test_strong_alias_always_returns_0_9(self):
        """RL-2: resolve_lora_weight('strong') returns identical float across 10 calls."""
        from presets import resolve_lora_weight  # noqa: PLC0415

        results = [resolve_lora_weight("strong") for _ in range(10)]
        assert all(r == results[0] for r in results), (
            f"resolve_lora_weight('strong') returned inconsistent values: {results}"
        )
        assert results[0] == 0.9

    def test_light_alias_always_returns_0_4(self):
        """RL-2: resolve_lora_weight('light') returns 0.4 every time."""
        from presets import resolve_lora_weight  # noqa: PLC0415

        for _ in range(10):
            assert resolve_lora_weight("light") == 0.4

    def test_medium_alias_always_returns_0_7(self):
        """RL-2: resolve_lora_weight('medium') returns 0.7 every time."""
        from presets import resolve_lora_weight  # noqa: PLC0415

        for _ in range(10):
            assert resolve_lora_weight("medium") == 0.7


@pytest.mark.reproducibility
class TestDryRunStabilityWithLora:
    def test_lora_dry_run_produces_identical_command_10_times(self):
        """RL-3: --lora aether-watercolor --dry-run produces identical command string
        across 10 consecutive subprocess invocations.
        """
        cmd = [
            sys.executable,
            _SIMPLE_CONFIG,
            "--prompt", "a tropical office, no text",
            "--preset", "standard",
            "--no-default-style",
            "--lora", "aether-watercolor",
            "--dry-run",
        ]

        outputs = []
        for _ in range(10):
            result = subprocess.run(
                cmd,
                cwd=str(_IMAGE_GEN_DIR),
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, f"dry-run failed: {result.stderr}"
            # Extract only the resolved command line (the stable part)
            lines = [
                line.strip()
                for line in result.stdout.splitlines()
                if "generate.py" in line and "--steps" in line
            ]
            assert lines, f"No resolved command found in output:\n{result.stdout}"
            outputs.append(lines[0])

        first = outputs[0]
        for i, out in enumerate(outputs[1:], 1):
            assert out == first, (
                f"Run {i} produced a different command:\n  got:      {out}\n  expected: {first}"
            )
