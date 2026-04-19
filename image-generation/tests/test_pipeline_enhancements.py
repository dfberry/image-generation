"""
Tests for SDXL pipeline enhancements:
- Dimension divisible-by-8 validation (CLI + runtime)
- LoRA loading with weight configuration
- Per-image negative prompt in batch mode
- Guidance scale default change
"""

import argparse
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from generate import (
    _dimension,
    batch_generate,
    generate,
    parse_args,
    validate_dimensions,
)

# ============================================================
# Phase 1: Dimension validation
# ============================================================


class TestDimensionArgparseType:
    """_dimension() argparse type rejects non-divisible-by-8 values."""

    def test_rejects_630(self):
        with pytest.raises(argparse.ArgumentTypeError, match="divisible by 8"):
            _dimension("630")

    def test_accepts_632(self):
        assert _dimension("632") == 632

    def test_accepts_1024(self):
        assert _dimension("1024") == 1024

    def test_accepts_1200(self):
        assert _dimension("1200") == 1200

    def test_rejects_65(self):
        with pytest.raises(argparse.ArgumentTypeError, match="divisible by 8"):
            _dimension("65")

    def test_accepts_64(self):
        assert _dimension("64") == 64

    def test_rejects_below_64(self):
        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 64"):
            _dimension("32")

    def test_error_suggests_nearest(self):
        """Error message for 630 should suggest 632."""
        with pytest.raises(argparse.ArgumentTypeError, match="632"):
            _dimension("630")


class TestValidateDimensionsRuntime:
    """validate_dimensions() guards generate() from bad sizes."""

    def test_valid_dimensions_pass(self):
        validate_dimensions(1024, 1024)
        validate_dimensions(1200, 632)

    def test_invalid_width_raises(self):
        with pytest.raises(ValueError, match="divisible by 8"):
            validate_dimensions(1201, 1024)

    def test_invalid_height_raises(self):
        with pytest.raises(ValueError, match="divisible by 8"):
            validate_dimensions(1024, 630)


# ============================================================
# Phase 2: LoRA support
# ============================================================


class TestLoRACLI:
    """--lora and --lora-weight CLI flags parse correctly."""

    def test_lora_flag_accepted(self):
        with patch("sys.argv", ["prog", "--prompt", "test", "--lora", "some/lora-model"]):
            args = parse_args()
            assert args.lora == "some/lora-model"

    def test_lora_weight_default(self):
        with patch("sys.argv", ["prog", "--prompt", "test", "--lora", "some/lora-model"]):
            args = parse_args()
            assert args.lora_weight == 0.8

    def test_lora_weight_custom(self):
        with patch("sys.argv", ["prog", "--prompt", "test", "--lora", "m", "--lora-weight", "0.6"]):
            args = parse_args()
            assert args.lora_weight == 0.6

    def test_no_lora_defaults_none(self):
        with patch("sys.argv", ["prog", "--prompt", "test"]):
            args = parse_args()
            assert args.lora is None


class TestLoRALoading:
    """LoRA weights are loaded when --lora is specified."""

    @patch("generate.load_base")
    @patch("generate.get_device", return_value="cpu")
    def test_lora_loaded_when_specified(self, mock_device, mock_load):
        from conftest import MockPipeline
        pipe = MockPipeline()
        pipe.load_lora_weights = MagicMock()
        pipe.set_adapters = MagicMock()
        mock_load.return_value = pipe

        args = SimpleNamespace(
            prompt="test", output="out.png", seed=None, steps=2,
            guidance=6.5, width=1024, height=1024, refine=False,
            negative_prompt="", cpu=True, scheduler="DPMSolverMultistepScheduler",
            refiner_guidance=5.0, lora="some/model", lora_weight=0.7,
        )
        generate(args)
        pipe.load_lora_weights.assert_called_once_with("some/model")
        pipe.set_adapters.assert_called_once()

    @patch("generate.load_base")
    @patch("generate.get_device", return_value="cpu")
    def test_lora_skipped_when_none(self, mock_device, mock_load):
        from conftest import MockPipeline
        pipe = MockPipeline()
        pipe.load_lora_weights = MagicMock()
        mock_load.return_value = pipe

        args = SimpleNamespace(
            prompt="test", output="out.png", seed=None, steps=2,
            guidance=6.5, width=1024, height=1024, refine=False,
            negative_prompt="", cpu=True, scheduler="DPMSolverMultistepScheduler",
            refiner_guidance=5.0, lora=None, lora_weight=0.8,
        )
        generate(args)
        pipe.load_lora_weights.assert_not_called()


# ============================================================
# Phase 3: Per-image negative prompt in batch
# ============================================================


class TestBatchNegativePrompt:
    """Batch items can override the default negative prompt."""

    @patch("generate.generate_with_retry")
    def test_per_item_negative_prompt(self, mock_gen):
        mock_gen.return_value = "out.png"
        prompts = [
            {"prompt": "test1", "output": "o1.png", "negative_prompt": "custom negative"},
        ]
        args = SimpleNamespace(
            steps=2, guidance=6.5, width=1024, height=1024,
            refine=False, negative_prompt="default negative",
            scheduler="DPMSolverMultistepScheduler", refiner_guidance=5.0,
            lora=None, lora_weight=0.8, refiner_steps=10,
        )
        batch_generate(prompts, device="cpu", args=args)

        call_args = mock_gen.call_args[0][0]
        assert call_args.negative_prompt == "custom negative"

    @patch("generate.generate_with_retry")
    def test_fallback_to_default_negative(self, mock_gen):
        mock_gen.return_value = "out.png"
        prompts = [
            {"prompt": "test1", "output": "o1.png"},
        ]
        args = SimpleNamespace(
            steps=2, guidance=6.5, width=1024, height=1024,
            refine=False, negative_prompt="default negative",
            scheduler="DPMSolverMultistepScheduler", refiner_guidance=5.0,
            lora=None, lora_weight=0.8, refiner_steps=10,
        )
        batch_generate(prompts, device="cpu", args=args)

        call_args = mock_gen.call_args[0][0]
        assert call_args.negative_prompt == "default negative"


# ============================================================
# Guidance default
# ============================================================


class TestGuidanceDefault:
    """Guidance scale default changed to 6.5 per tuning recommendations."""

    def test_default_guidance_is_6_5(self):
        with patch("sys.argv", ["prog", "--prompt", "test"]):
            args = parse_args()
            assert args.guidance == 6.5
