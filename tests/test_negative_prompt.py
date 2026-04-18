"""
TDD Red Phase — Negative Prompt Support (Issue #3).

Tests written BEFORE implementation. ALL tests MUST FAIL against current
generate.py, proving the feature doesn't exist yet.

Feature: --negative-prompt CLI flag that passes negative_prompt to the
SDXL pipeline calls (base and refiner). A sensible default negative prompt
should be used when the flag is not specified.

Mocking strategy: patch load_base / load_refiner / get_device to return
callable mocks. No GPU required.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from generate import batch_generate, generate, parse_args

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _args(negative_prompt=None, refine=False, **overrides):
    """Build a minimal SimpleNamespace for testing."""
    defaults = dict(
        prompt="a tropical scene",
        output="outputs/test.png",
        seed=None,
        steps=2,
        guidance=7.5,
        width=64,
        height=64,
        refine=refine,
        cpu=True,
        scheduler="DPMSolverMultistepScheduler",
        refiner_guidance=5.0,
    )
    if negative_prompt is not None:
        defaults["negative_prompt"] = negative_prompt
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_mock_pipeline(return_latents=False):
    """
    Create a MagicMock pipeline that tracks __call__ kwargs.

    Mimics conftest.MockPipeline but uses MagicMock so we can inspect
    call_args after generate() runs.
    """
    pipe = MagicMock()
    pipe.text_encoder_2 = MagicMock()
    pipe.vae = MagicMock()
    pipe.unet = MagicMock()

    if return_latents:
        latent = MagicMock()
        latent.cpu.return_value = latent
        latent.to.return_value = latent
        result = MagicMock()
        result.images = latent
    else:
        mock_image = MagicMock()
        result = MagicMock()
        result.images = [mock_image]

    pipe.return_value = result
    pipe.to.return_value = pipe
    pipe.enable_model_cpu_offload.return_value = None
    return pipe


# ===========================================================================
# CLI Tests — argparse integration
# ===========================================================================

class TestNegativePromptCLI:
    """Verify --negative-prompt is accepted and parsed by argparse."""

    def test_negative_prompt_flag_accepted(self):
        """--negative-prompt flag must exist and be accepted by argparse."""
        with patch("sys.argv", ["generate.py", "--prompt", "a cat",
                                "--negative-prompt", "blurry, ugly"]):
            try:
                args = parse_args()
            except SystemExit as exc:
                pytest.fail(
                    f"parse_args() rejected --negative-prompt (SystemExit {exc.code}). "
                    "The flag has not been added to argparse yet."
                )
        assert hasattr(args, "negative_prompt"), (
            "parse_args() should return an object with 'negative_prompt' attribute"
        )
        assert args.negative_prompt == "blurry, ugly"

    def test_negative_prompt_value_is_stored(self):
        """--negative-prompt value must be stored in the parsed args object."""
        with patch("sys.argv", ["generate.py", "--prompt", "a cat",
                                "--negative-prompt", "low quality, watermark"]):
            try:
                args = parse_args()
            except SystemExit as exc:
                pytest.fail(
                    f"parse_args() rejected --negative-prompt (SystemExit {exc.code})."
                )
        assert args.negative_prompt == "low quality, watermark", (
            "The --negative-prompt value must be stored verbatim in args.negative_prompt"
        )

    def test_default_negative_prompt_when_not_specified(self):
        """When --negative-prompt is omitted, a sensible default must be used (not empty/None)."""
        with patch("sys.argv", ["generate.py", "--prompt", "a cat"]):
            args = parse_args()
        assert hasattr(args, "negative_prompt"), (
            "args should have negative_prompt attribute even when flag is not specified"
        )
        assert args.negative_prompt is not None, (
            "Default negative_prompt should not be None"
        )
        assert isinstance(args.negative_prompt, str) and len(args.negative_prompt.strip()) > 0, (
            "Default negative_prompt should be a non-empty string with sensible content"
        )


# ===========================================================================
# Pipeline Tests — Base model (no refiner)
# ===========================================================================

class TestNegativePromptBasePipeline:
    """generate() must pass negative_prompt to the base pipeline __call__."""

    @patch("generate.load_base")
    @patch("generate.get_device", return_value="cpu")
    def test_base_pipeline_receives_negative_prompt(self, _mock_device, mock_load):
        """Base pipeline should be called with a negative_prompt keyword argument."""
        pipe = _make_mock_pipeline()
        mock_load.return_value = pipe

        args = _args(negative_prompt="blurry, ugly, distorted")
        generate(args)

        pipe.assert_called_once()
        call_kwargs = pipe.call_args.kwargs
        assert "negative_prompt" in call_kwargs, (
            "Base pipeline was not called with negative_prompt keyword argument. "
            "generate() must forward args.negative_prompt to the pipeline."
        )
        assert call_kwargs["negative_prompt"] == "blurry, ugly, distorted"


# ===========================================================================
# Pipeline Tests — Refiner mode (base + refiner)
# ===========================================================================

class TestNegativePromptRefinerPipeline:
    """generate() must pass negative_prompt to both base and refiner when --refine is used."""

    @patch("generate.load_refiner")
    @patch("generate.load_base")
    @patch("generate.get_device", return_value="cpu")
    def test_refiner_pipeline_receives_negative_prompt(
        self, _mock_device, mock_load_base, mock_load_refiner
    ):
        """Refiner pipeline should be called with negative_prompt kwarg."""
        base_pipe = _make_mock_pipeline(return_latents=True)
        refiner_pipe = _make_mock_pipeline()
        mock_load_base.return_value = base_pipe
        mock_load_refiner.return_value = refiner_pipe

        args = _args(negative_prompt="blurry, ugly", refine=True)
        generate(args)

        refiner_pipe.assert_called_once()
        refiner_kwargs = refiner_pipe.call_args.kwargs
        assert "negative_prompt" in refiner_kwargs, (
            "Refiner pipeline was not called with negative_prompt keyword argument. "
            "generate() must forward args.negative_prompt to the refiner."
        )
        assert refiner_kwargs["negative_prompt"] == "blurry, ugly"

    @patch("generate.load_refiner")
    @patch("generate.load_base")
    @patch("generate.get_device", return_value="cpu")
    def test_base_pipeline_also_receives_negative_prompt_in_refine_mode(
        self, _mock_device, mock_load_base, mock_load_refiner
    ):
        """In refine mode, the base pipeline stage must ALSO receive negative_prompt."""
        base_pipe = _make_mock_pipeline(return_latents=True)
        refiner_pipe = _make_mock_pipeline()
        mock_load_base.return_value = base_pipe
        mock_load_refiner.return_value = refiner_pipe

        args = _args(negative_prompt="blurry, ugly", refine=True)
        generate(args)

        base_pipe.assert_called_once()
        base_kwargs = base_pipe.call_args.kwargs
        assert "negative_prompt" in base_kwargs, (
            "Base pipeline (in refine mode) was not called with negative_prompt. "
            "Both stages need the negative prompt for consistent guidance."
        )
        assert base_kwargs["negative_prompt"] == "blurry, ugly"


# ===========================================================================
# batch_generate Tests
# ===========================================================================

class TestNegativePromptBatchGenerate:
    """batch_generate() must forward negative_prompt for each batch item."""

    @patch("generate.generate_with_retry")
    def test_batch_forwards_negative_prompt(self, mock_retry):
        """Each item in the batch should get the negative_prompt from args."""
        mock_retry.return_value = "outputs/test.png"

        prompts = [
            {"prompt": "cats on a beach", "output": "out1.png"},
            {"prompt": "dogs in a garden", "output": "out2.png"},
        ]
        args = _args(negative_prompt="blurry, ugly, watermark")

        batch_generate(prompts, device="cpu", args=args)

        assert mock_retry.call_count == 2, (
            f"Expected 2 generate_with_retry calls, got {mock_retry.call_count}"
        )
        for i, c in enumerate(mock_retry.call_args_list):
            batch_item_args = c[0][0]  # first positional arg to generate_with_retry
            assert hasattr(batch_item_args, "negative_prompt"), (
                f"Batch item {i}: generate_with_retry was called without "
                "negative_prompt on the per-item args namespace"
            )
            assert batch_item_args.negative_prompt == "blurry, ugly, watermark", (
                f"Batch item {i}: negative_prompt was not forwarded from the CLI args"
            )
