"""
Tests for effective seed capture (Change 5).

Tests TSS-01 through TSS-05 per PRD §9.2.
Mocks torch.Generator and torch.randint — no GPU required.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import generate as gen_mod


def _make_minimal_args(seed=None, output=None, tmp_path=None):
    """Build a minimal args namespace for generate()."""
    if output is None and tmp_path is not None:
        output = str(tmp_path / "out.png")
    return SimpleNamespace(
        prompt="Test prompt",
        negative_prompt="bad quality",
        seed=seed,
        steps=1,
        guidance=6.5,
        refiner_guidance=5.0,
        width=64,
        height=64,
        refine=False,
        cpu=True,
        lora=None,
        lora_weight=None,
        scheduler="DPMSolverMultistepScheduler",
        refiner_steps=10,
        output=output,
        model=None,
        dry_run=False,
    )


@pytest.fixture
def mock_pipeline(tmp_path):
    """Fixture providing mocked torch and DiffusionPipeline."""
    mock_torch = MagicMock()
    mock_torch.float32 = "float32"
    mock_torch.float16 = "float16"
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = False

    # Mock randint to return a fixed value
    mock_torch.randint.return_value = MagicMock()
    mock_torch.randint.return_value.item.return_value = 99999

    mock_generator = MagicMock()
    mock_torch.Generator.return_value.manual_seed.return_value = mock_generator

    mock_image = Image.new("RGB", (64, 64), color=(0, 0, 0))
    mock_pipe_instance = MagicMock()
    mock_pipe_instance.return_value.images = [mock_image]
    mock_pipe_instance.return_value.images.__getitem__ = lambda self, idx: mock_image

    mock_diffusion = MagicMock()
    mock_diffusion.from_pretrained.return_value = mock_pipe_instance
    # Make the pipeline callable (for inference)
    mock_pipe_instance.side_effect = None
    result_mock = MagicMock()
    result_mock.images = [mock_image]
    mock_pipe_instance.return_value = result_mock
    mock_pipe_instance.__call__ = MagicMock(return_value=result_mock)

    return mock_torch, mock_pipe_instance, tmp_path


class TestSeedSurfacing:
    """Effective seed is always captured and stored in args.seed."""

    def test_specified_seed_is_used_as_effective_seed(self, tmp_path):
        """TSS-01: When args.seed=42, generator is seeded with 42; args.seed remains 42."""
        args = _make_minimal_args(seed=42, tmp_path=tmp_path)

        mock_torch = MagicMock()
        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False
        mock_generator = MagicMock()
        mock_torch.Generator.return_value.manual_seed.return_value = mock_generator

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

        assert args.seed == 42
        mock_torch.Generator.return_value.manual_seed.assert_called_with(42)

    def test_auto_seed_is_captured_in_args(self, tmp_path):
        """TSS-02: When args.seed=None, torch.randint is called; args.seed is set to the result."""
        args = _make_minimal_args(seed=None, tmp_path=tmp_path)

        mock_torch = MagicMock()
        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False
        auto_seed_val = MagicMock()
        auto_seed_val.item.return_value = 77777
        mock_torch.randint.return_value = auto_seed_val

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

        mock_torch.randint.assert_called_once()
        assert args.seed == 77777

    def test_auto_seed_is_logged(self, tmp_path):
        """TSS-03: logger.info is called with the effective seed when args.seed=None."""
        args = _make_minimal_args(seed=None, tmp_path=tmp_path)

        mock_torch = MagicMock()
        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False
        auto_seed = MagicMock()
        auto_seed.item.return_value = 12345
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
             patch("generate.DiffusionPipeline", mock_diffusion), \
             patch("generate.logger") as mock_logger:
            gen_mod.generate(args)

        # logger.info should have been called with seed info
        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("12345" in c or "Seed" in c for c in info_calls)

    def test_auto_seed_appears_in_png_metadata(self, tmp_path):
        """TSS-04: When args.seed=None, the PNG tEXt chunk 'seed' field is a non-None integer."""
        args = _make_minimal_args(seed=None, tmp_path=tmp_path)

        mock_torch = MagicMock()
        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False
        auto_seed = MagicMock()
        auto_seed.item.return_value = 55555
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

        from PIL import Image as PILImage
        saved = PILImage.open(str(tmp_path / "out.png"))
        assert "generate_params" in saved.info
        parsed = json.loads(saved.info["generate_params"])
        assert parsed["seed"] is not None
        assert isinstance(parsed["seed"], int)
