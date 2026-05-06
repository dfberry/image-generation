"""
Unit tests for SDXLProvider img2img functionality (Issue #110).

Tests the img2img path in SDXLProvider.generate() using mocks — no GPU required.

Coverage:
    - img2img pipeline creation shares components with txt2img pipeline
    - Input image is resized when dimensions don't match target
    - Strength parameter is passed to img2img pipeline
    - Text-to-image path still works when input_image is None
    - Dimension mismatch triggers a warning log
    - img2img pipeline is lazily created on first use
    - Cleanup disposes both pipelines
"""

from unittest.mock import MagicMock, patch, PropertyMock
import logging

import pytest
from PIL import Image

from providers.base import GenerationConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_torch():
    """Mock torch module."""
    mock = MagicMock()
    mock.float16 = "float16"
    mock.float32 = "float32"
    mock.cuda.is_available.return_value = False
    mock.backends.mps.is_available.return_value = False
    mock.Generator.return_value.manual_seed.return_value = MagicMock()
    return mock


@pytest.fixture
def mock_diffusers():
    """Mock diffusers module."""
    return MagicMock()


@pytest.fixture
def mock_img2img_cls():
    """Mock StableDiffusionXLImg2ImgPipeline class."""
    return MagicMock()


@pytest.fixture
def provider(mock_torch, mock_diffusers, mock_img2img_cls):
    """Create an SDXLProvider with mocked dependencies and pre-loaded state."""
    with patch.dict("providers.sdxl.__builtins__", {}):
        import providers.sdxl as sdxl_module

        sdxl_module.torch = mock_torch
        sdxl_module.diffusers = mock_diffusers
        sdxl_module.DiffusionPipeline = MagicMock()
        sdxl_module.StableDiffusionXLImg2ImgPipeline = mock_img2img_cls

        from providers.sdxl import SDXLProvider
        p = SDXLProvider()

        # Simulate a loaded pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.vae = MagicMock()
        mock_pipeline.text_encoder = MagicMock()
        mock_pipeline.text_encoder_2 = MagicMock()
        mock_pipeline.tokenizer = MagicMock()
        mock_pipeline.tokenizer_2 = MagicMock()
        mock_pipeline.unet = MagicMock()
        mock_pipeline.scheduler = MagicMock()
        mock_pipeline.return_value.images = [Image.new("RGB", (1024, 1024))]

        p._pipeline = mock_pipeline
        p._device = "cpu"

        yield p


@pytest.fixture
def sample_input_image():
    """A sample 512x512 RGB input image."""
    return Image.new("RGB", (512, 512), color=(128, 200, 50))


# ---------------------------------------------------------------------------
# Tests: text-to-image path unchanged
# ---------------------------------------------------------------------------


class TestTextToImageUnchanged:
    """The existing txt2img path must continue working."""

    def test_txt2img_when_no_input_image(self, provider):
        """Without input_image, uses main pipeline (not img2img)."""
        config = GenerationConfig(
            prompt="a tropical sunset",
            width=1024,
            height=1024,
            steps=20,
        )
        provider._pipeline.return_value.images = [Image.new("RGB", (1024, 1024))]

        result = provider.generate(config)

        provider._pipeline.assert_called_once()
        call_kwargs = provider._pipeline.call_args
        assert call_kwargs[1]["prompt"] == "a tropical sunset"
        assert isinstance(result, Image.Image)

    def test_txt2img_does_not_create_img2img_pipeline(self, provider):
        """txt2img path should not instantiate img2img pipeline."""
        config = GenerationConfig(prompt="test", width=1024, height=1024)
        provider._pipeline.return_value.images = [Image.new("RGB", (1024, 1024))]

        provider.generate(config)

        assert provider._img2img_pipeline is None


# ---------------------------------------------------------------------------
# Tests: img2img path
# ---------------------------------------------------------------------------


class TestImg2ImgGeneration:
    """Tests for the img2img generation path."""

    def test_img2img_triggered_when_input_image_set(self, provider, sample_input_image, mock_img2img_cls):
        """When config.input_image is not None, img2img pipeline is used."""
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="repaint as watercolor",
            input_image=sample_input_image,
            strength=0.7,
            width=1024,
            height=1024,
            steps=30,
        )

        result = provider.generate(config)

        # img2img pipeline should have been called
        mock_img2img_cls.return_value.assert_called_once()
        assert isinstance(result, Image.Image)
        # Main pipeline should NOT be called
        provider._pipeline.assert_not_called()

    def test_strength_passed_to_pipeline(self, provider, sample_input_image, mock_img2img_cls):
        """Strength kwarg is forwarded to the img2img pipeline call."""
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="oil painting",
            input_image=sample_input_image,
            strength=0.4,
            width=1024,
            height=1024,
        )

        provider.generate(config)

        call_kwargs = mock_img2img_cls.return_value.call_args[1]
        assert call_kwargs["strength"] == 0.4

    def test_negative_prompt_forwarded(self, provider, sample_input_image, mock_img2img_cls):
        """Negative prompt is passed to img2img pipeline."""
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="sunset",
            negative_prompt="blurry, low quality",
            input_image=sample_input_image,
            strength=0.6,
            width=1024,
            height=1024,
        )

        provider.generate(config)

        call_kwargs = mock_img2img_cls.return_value.call_args[1]
        assert call_kwargs["negative_prompt"] == "blurry, low quality"

    def test_seed_creates_generator(self, provider, sample_input_image, mock_img2img_cls, mock_torch):
        """Seed should produce a torch.Generator passed to img2img pipeline."""
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="test",
            input_image=sample_input_image,
            strength=0.5,
            seed=42,
            width=1024,
            height=1024,
        )

        provider.generate(config)

        call_kwargs = mock_img2img_cls.return_value.call_args[1]
        assert call_kwargs["generator"] is not None


# ---------------------------------------------------------------------------
# Tests: dimension mismatch handling
# ---------------------------------------------------------------------------


class TestDimensionMismatch:
    """Input images not matching target dimensions are resized with warning."""

    def test_resize_when_input_smaller(self, provider, mock_img2img_cls, caplog):
        """Input 256x256 resized to target 1024x1024."""
        small_image = Image.new("RGB", (256, 256), color=(100, 100, 100))
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="upscale",
            input_image=small_image,
            strength=0.8,
            width=1024,
            height=1024,
        )

        with caplog.at_level(logging.WARNING, logger="providers.sdxl"):
            provider.generate(config)

        assert "resizing" in caplog.text.lower() or "differs" in caplog.text.lower()

        # Verify the image passed to pipeline is the target size
        call_kwargs = mock_img2img_cls.return_value.call_args[1]
        passed_image = call_kwargs["image"]
        assert passed_image.size == (1024, 1024)

    def test_no_resize_when_dimensions_match(self, provider, mock_img2img_cls, caplog):
        """No resize or warning when input matches target exactly."""
        matching_image = Image.new("RGB", (1024, 1024), color=(50, 50, 50))
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="restyle",
            input_image=matching_image,
            strength=0.5,
            width=1024,
            height=1024,
        )

        with caplog.at_level(logging.WARNING, logger="providers.sdxl"):
            provider.generate(config)

        assert "resizing" not in caplog.text.lower()
        assert "differs" not in caplog.text.lower()

    def test_resize_non_square(self, provider, mock_img2img_cls):
        """Non-square input resized to non-square target."""
        wide_image = Image.new("RGB", (800, 400))
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 768))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="landscape",
            input_image=wide_image,
            strength=0.6,
            width=1024,
            height=768,
        )

        provider.generate(config)

        call_kwargs = mock_img2img_cls.return_value.call_args[1]
        assert call_kwargs["image"].size == (1024, 768)


# ---------------------------------------------------------------------------
# Tests: pipeline sharing (VAE/encoders reused)
# ---------------------------------------------------------------------------


class TestPipelineSharing:
    """img2img pipeline shares components with txt2img pipeline."""

    def test_img2img_pipeline_shares_vae(self, provider, sample_input_image, mock_img2img_cls):
        """img2img pipeline is constructed with same VAE as txt2img."""
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="test",
            input_image=sample_input_image,
            strength=0.5,
            width=1024,
            height=1024,
        )

        provider.generate(config)

        # StableDiffusionXLImg2ImgPipeline was constructed with shared components
        constructor_kwargs = mock_img2img_cls.call_args[1]
        assert constructor_kwargs["vae"] is provider._pipeline.vae
        assert constructor_kwargs["text_encoder"] is provider._pipeline.text_encoder
        assert constructor_kwargs["text_encoder_2"] is provider._pipeline.text_encoder_2
        assert constructor_kwargs["unet"] is provider._pipeline.unet
        assert constructor_kwargs["tokenizer"] is provider._pipeline.tokenizer
        assert constructor_kwargs["tokenizer_2"] is provider._pipeline.tokenizer_2

    def test_img2img_pipeline_created_once(self, provider, sample_input_image, mock_img2img_cls):
        """Repeated img2img calls reuse the same pipeline instance."""
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="test",
            input_image=sample_input_image,
            strength=0.5,
            width=1024,
            height=1024,
        )

        provider.generate(config)
        provider.generate(config)

        # Constructor called only once (lazy init)
        assert mock_img2img_cls.call_count == 1


# ---------------------------------------------------------------------------
# Tests: cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    """Cleanup disposes both pipelines."""

    def test_cleanup_removes_img2img_pipeline(self, provider, sample_input_image, mock_img2img_cls):
        """After cleanup, img2img pipeline reference is None."""
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="test",
            input_image=sample_input_image,
            strength=0.5,
            width=1024,
            height=1024,
        )
        provider.generate(config)
        assert provider._img2img_pipeline is not None

        provider.cleanup()

        assert provider._img2img_pipeline is None
        assert provider._pipeline is None

    def test_cleanup_without_img2img_usage(self, provider):
        """Cleanup works even if img2img was never used."""
        provider.cleanup()
        assert provider._img2img_pipeline is None
        assert provider._pipeline is None


# ---------------------------------------------------------------------------
# Tests: RGBA input conversion
# ---------------------------------------------------------------------------


class TestInputConversion:
    """Input images with alpha channel are converted to RGB."""

    def test_rgba_input_converted_to_rgb(self, provider, mock_img2img_cls):
        """RGBA input is converted to RGB before passing to pipeline."""
        rgba_image = Image.new("RGBA", (1024, 1024), color=(128, 200, 50, 128))
        mock_img2img_cls.return_value.return_value.images = [Image.new("RGB", (1024, 1024))]
        mock_img2img_cls.return_value.enable_attention_slicing = MagicMock()

        config = GenerationConfig(
            prompt="test",
            input_image=rgba_image,
            strength=0.5,
            width=1024,
            height=1024,
        )

        provider.generate(config)

        call_kwargs = mock_img2img_cls.return_value.call_args[1]
        assert call_kwargs["image"].mode == "RGB"
