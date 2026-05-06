"""Tests for the provider abstraction layer.

Verifies:
- Provider registry resolves friendly names correctly
- BaseProvider contract is enforced
- Each provider's lifecycle (load -> generate -> cleanup) works
- The --model CLI flag integrates correctly
- Backward compatibility (no --model uses legacy path)
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistry:
    """Test provider registry lookups."""

    def test_get_provider_creative(self):
        from providers.registry import get_provider
        from providers.flux import FluxProvider
        p = get_provider("creative")
        assert isinstance(p, FluxProvider)

    def test_get_provider_precise(self):
        from providers.registry import get_provider
        from providers.sdxl import SDXLProvider
        p = get_provider("precise")
        assert isinstance(p, SDXLProvider)

    def test_get_provider_fast(self):
        from providers.registry import get_provider
        from providers.sd3 import SD3Provider
        p = get_provider("fast")
        assert isinstance(p, SD3Provider)

    def test_get_provider_case_insensitive(self):
        from providers.registry import get_provider
        from providers.flux import FluxProvider
        p = get_provider("Creative")
        assert isinstance(p, FluxProvider)

    def test_get_provider_invalid_raises(self):
        from providers.registry import get_provider
        with pytest.raises(ValueError, match="Unknown model"):
            get_provider("nonexistent")

    def test_list_providers_returns_all(self):
        from providers.registry import list_providers
        providers = list_providers()
        assert "creative" in providers
        assert "precise" in providers
        assert "fast" in providers
        assert len(providers) == 3

    def test_default_model_is_precise(self):
        from providers.registry import DEFAULT_MODEL
        assert DEFAULT_MODEL == "precise"


# ---------------------------------------------------------------------------
# BaseProvider contract tests
# ---------------------------------------------------------------------------


class TestBaseProvider:
    """Verify the abstract base class cannot be instantiated directly."""

    def test_cannot_instantiate_base(self):
        from providers.base import BaseProvider
        with pytest.raises(TypeError):
            BaseProvider()

    def test_generation_config_defaults(self):
        from providers.base import GenerationConfig
        config = GenerationConfig(prompt="test")
        assert config.width == 1024
        assert config.height == 1024
        assert config.steps == 30
        assert config.guidance_scale == 7.5
        assert config.seed is None
        assert config.negative_prompt is None

    def test_generation_config_custom(self):
        from providers.base import GenerationConfig
        config = GenerationConfig(
            prompt="a cat",
            negative_prompt="blurry",
            width=512,
            height=512,
            steps=20,
            guidance_scale=5.0,
            seed=42,
            scheduler="EulerDiscreteScheduler",
        )
        assert config.prompt == "a cat"
        assert config.seed == 42


# ---------------------------------------------------------------------------
# SDXL Provider tests
# ---------------------------------------------------------------------------


class TestSDXLProvider:
    """Test SDXLProvider lifecycle with mocked torch/diffusers."""

    def test_friendly_name(self):
        from providers.sdxl import SDXLProvider
        p = SDXLProvider()
        assert p.friendly_name == "precise"

    def test_model_id(self):
        from providers.sdxl import SDXLProvider
        p = SDXLProvider()
        assert "stable-diffusion-xl" in p.model_id

    def test_not_loaded_initially(self):
        from providers.sdxl import SDXLProvider
        p = SDXLProvider()
        assert not p.is_loaded

    def test_generate_without_load_raises(self):
        from providers.sdxl import SDXLProvider
        from providers.base import GenerationConfig
        p = SDXLProvider()
        with pytest.raises(RuntimeError, match="not loaded"):
            p.generate(GenerationConfig(prompt="test"))

    @patch("providers.sdxl.DiffusionPipeline")
    @patch("providers.sdxl.torch")
    def test_load_and_generate(self, mock_torch, mock_dp):
        from providers.sdxl import SDXLProvider
        from providers.base import GenerationConfig

        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False

        mock_pipe = MagicMock()
        mock_image = MagicMock()
        mock_pipe.return_value.images = [mock_image]
        mock_dp.from_pretrained.return_value = mock_pipe

        p = SDXLProvider()
        p.load("cpu")
        assert p.is_loaded

        config = GenerationConfig(prompt="test", steps=2)
        result = p.generate(config)
        assert result == mock_image
        mock_pipe.assert_called_once()

    @patch("providers.sdxl.torch")
    def test_cleanup(self, mock_torch):
        from providers.sdxl import SDXLProvider

        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch._dynamo = None

        p = SDXLProvider()
        p._pipeline = MagicMock()
        p._device = "cpu"
        p.cleanup()
        assert not p.is_loaded
        assert p._device is None


# ---------------------------------------------------------------------------
# FLUX Provider tests
# ---------------------------------------------------------------------------


class TestFluxProvider:
    """Test FluxProvider lifecycle with mocked imports."""

    def test_friendly_name(self):
        from providers.flux import FluxProvider
        p = FluxProvider()
        assert p.friendly_name == "creative"

    def test_model_id(self):
        from providers.flux import FluxProvider
        p = FluxProvider()
        assert "FLUX" in p.model_id

    def test_generate_without_load_raises(self):
        from providers.flux import FluxProvider
        from providers.base import GenerationConfig
        p = FluxProvider()
        with pytest.raises(RuntimeError, match="not loaded"):
            p.generate(GenerationConfig(prompt="test"))

    @patch("providers.flux.FluxPipeline")
    @patch("providers.flux.torch")
    def test_load_and_generate(self, mock_torch, mock_fp):
        from providers.flux import FluxProvider
        from providers.base import GenerationConfig

        mock_torch.float32 = "float32"
        mock_torch.bfloat16 = "bfloat16"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False

        mock_pipe = MagicMock()
        mock_image = MagicMock()
        mock_pipe.return_value.images = [mock_image]
        mock_fp.from_pretrained.return_value = mock_pipe

        p = FluxProvider()
        p.load("cpu")
        assert p.is_loaded

        config = GenerationConfig(prompt="test", steps=4)
        result = p.generate(config)
        assert result == mock_image

    @patch("providers.flux.torch")
    def test_cleanup(self, mock_torch):
        from providers.flux import FluxProvider

        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False

        p = FluxProvider()
        p._pipeline = MagicMock()
        p._device = "cpu"
        p.cleanup()
        assert not p.is_loaded


# ---------------------------------------------------------------------------
# SD3 Provider tests
# ---------------------------------------------------------------------------


class TestSD3Provider:
    """Test SD3Provider lifecycle with mocked imports."""

    def test_friendly_name(self):
        from providers.sd3 import SD3Provider
        p = SD3Provider()
        assert p.friendly_name == "fast"

    def test_model_id(self):
        from providers.sd3 import SD3Provider
        p = SD3Provider()
        assert "stable-diffusion-3" in p.model_id

    def test_generate_without_load_raises(self):
        from providers.sd3 import SD3Provider
        from providers.base import GenerationConfig
        p = SD3Provider()
        with pytest.raises(RuntimeError, match="not loaded"):
            p.generate(GenerationConfig(prompt="test"))

    @patch("providers.sd3.StableDiffusion3Pipeline")
    @patch("providers.sd3.torch")
    def test_load_and_generate(self, mock_torch, mock_sd3):
        from providers.sd3 import SD3Provider
        from providers.base import GenerationConfig

        mock_torch.float32 = "float32"
        mock_torch.float16 = "float16"
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False

        mock_pipe = MagicMock()
        mock_image = MagicMock()
        mock_pipe.return_value.images = [mock_image]
        mock_sd3.from_pretrained.return_value = mock_pipe

        p = SD3Provider()
        p.load("cpu")
        assert p.is_loaded

        config = GenerationConfig(prompt="test", steps=10)
        result = p.generate(config)
        assert result == mock_image

    @patch("providers.sd3.torch")
    def test_cleanup(self, mock_torch):
        from providers.sd3 import SD3Provider

        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False

        p = SD3Provider()
        p._pipeline = MagicMock()
        p._device = "cpu"
        p.cleanup()
        assert not p.is_loaded


# ---------------------------------------------------------------------------
# CLI Integration tests (--model flag)
# ---------------------------------------------------------------------------


class TestModelFlag:
    """Test that the --model flag routes to the provider system."""

    @patch("generate.generate_with_provider")
    def test_model_flag_calls_provider_path(self, mock_gen_provider):
        """When --model is specified, main() calls generate_with_provider."""
        import generate
        with patch("generate.parse_args") as mock_parse:
            args = MagicMock()
            args.batch_file = None
            args.model = "creative"
            mock_parse.return_value = args
            generate.main()
            mock_gen_provider.assert_called_once_with(args)

    @patch("generate.generate_with_retry")
    def test_no_model_flag_uses_legacy_path(self, mock_gen_retry):
        """When --model is not specified, main() uses the legacy path."""
        import generate
        with patch("generate.parse_args") as mock_parse:
            args = MagicMock()
            args.batch_file = None
            args.model = None
            mock_parse.return_value = args
            generate.main()
            mock_gen_retry.assert_called_once_with(args)

    @patch("generate.get_device", return_value="cpu")
    @patch("generate._ensure_heavy_imports")
    def test_generate_with_provider_saves_image(self, mock_ensure, mock_dev, tmp_path):
        """generate_with_provider loads, generates, saves, and cleans up."""
        import generate

        mock_image = MagicMock()
        mock_provider = MagicMock()
        mock_provider.friendly_name = "creative"
        mock_provider.description = "Test"
        mock_provider.generate.return_value = mock_image

        args = MagicMock()
        args.model = "creative"
        args.prompt = "test"
        args.output = str(tmp_path / "out.png")
        args.cpu = True
        args.width = 512
        args.height = 512
        args.steps = 4
        args.guidance = 7.5
        args.negative_prompt = ""
        args.seed = None
        args.scheduler = None

        with patch("providers.registry.get_provider", return_value=mock_provider), \
             patch("providers.get_provider", return_value=mock_provider):
            result = generate.generate_with_provider(args)
            assert result == str(tmp_path / "out.png")
            mock_provider.load.assert_called_once_with("cpu")
            mock_provider.generate.assert_called_once()
            mock_image.save.assert_called_once()
            mock_provider.cleanup.assert_called_once()
