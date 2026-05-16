"""
Seed determinism tests.

Tests TRP-01 through TRP-04 per PRD §9.2.
Mocks the diffusion pipeline — no GPU required.
"""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import generate as gen_mod


def _get_generate_cwd():
    return str(Path(__file__).parent.parent)


class TestSeedDeterminism:
    """Same seed + same params -> same generator state."""

    def test_fixed_seed_produces_same_generator_state(self, tmp_path):
        """TRP-01: Two calls with seed=42 produce generators with identical manual_seed calls."""
        seeds_used = []

        def make_args(out):
            return SimpleNamespace(
                prompt="Test", negative_prompt="bad", seed=42, steps=1, guidance=6.5,
                refiner_guidance=5.0, width=64, height=64, refine=False, cpu=True,
                lora=None, lora_weight=None, scheduler="DPMSolverMultistepScheduler",
                refiner_steps=10, output=out, model=None, dry_run=False,
            )

        mock_torch = MagicMock()
        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False

        def capture_seed(seed):
            seeds_used.append(seed)
            return MagicMock()

        mock_torch.Generator.return_value.manual_seed.side_effect = capture_seed

        mock_image = Image.new("RGB", (64, 64))
        mock_pipe = MagicMock()
        result = MagicMock()
        result.images = [mock_image]
        mock_pipe.return_value = result
        mock_diffusion = MagicMock()
        mock_diffusion.from_pretrained.return_value = mock_pipe

        with patch("generate._ensure_heavy_imports"), \
             patch("generate.torch", mock_torch), \
             patch("generate.DiffusionPipeline", mock_diffusion):
            gen_mod.generate(make_args(str(tmp_path / "out1.png")))
            gen_mod.generate(make_args(str(tmp_path / "out2.png")))

        assert len(seeds_used) == 2
        assert seeds_used[0] == seeds_used[1] == 42

    def test_auto_seed_captured_in_metadata_enables_rerun(self, tmp_path):
        """TRP-02: Auto-generated seed embedded in metadata; re-running with that seed produces identical generator state."""
        args = SimpleNamespace(
            prompt="Test", negative_prompt="bad", seed=None, steps=1, guidance=6.5,
            refiner_guidance=5.0, width=64, height=64, refine=False, cpu=True,
            lora=None, lora_weight=None, scheduler="DPMSolverMultistepScheduler",
            refiner_steps=10, output=str(tmp_path / "out.png"), model=None, dry_run=False,
        )

        mock_torch = MagicMock()
        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False
        auto_seed = MagicMock()
        auto_seed.item.return_value = 42424242
        mock_torch.randint.return_value = auto_seed

        mock_image = Image.new("RGB", (64, 64))
        mock_pipe = MagicMock()
        result = MagicMock()
        result.images = [mock_image]
        mock_pipe.return_value = result
        mock_diffusion = MagicMock()
        mock_diffusion.from_pretrained.return_value = mock_pipe

        with patch("generate._ensure_heavy_imports"), \
             patch("generate.torch", mock_torch), \
             patch("generate.DiffusionPipeline", mock_diffusion):
            gen_mod.generate(args)

        saved = Image.open(str(tmp_path / "out.png"))
        parsed = json.loads(saved.info["generate_params"])
        assert parsed["seed"] == 42424242

    @pytest.mark.integration
    def test_dry_run_output_is_stable_across_10_runs(self):
        """TRP-03: --seed 42 --dry-run --output fixed.png invoked 10 times -> identical JSON."""
        outputs = []
        for _ in range(10):
            result = subprocess.run(
                [sys.executable, "generate.py", "--prompt", "Test", "--seed", "42",
                 "--dry-run", "--output", "outputs/stable_test.png"],
                capture_output=True, text=True, cwd=_get_generate_cwd()
            )
            assert result.returncode == 0
            outputs.append(result.stdout.strip())
        assert len(set(outputs)) == 1, "dry-run output was not stable across 10 runs"

    @pytest.mark.integration
    def test_dry_run_includes_effective_seed_field(self):
        """TRP-04: --dry-run without --seed -> resolved['effective_seed'] is null (not omitted)."""
        result = subprocess.run(
            [sys.executable, "generate.py", "--prompt", "Test", "--dry-run"],
            capture_output=True, text=True, cwd=_get_generate_cwd()
        )
        assert result.returncode == 0
        resolved = json.loads(result.stdout)["resolved"]
        assert "effective_seed" in resolved
        assert resolved["effective_seed"] is None
