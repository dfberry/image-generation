"""Tests for the Real-ESRGAN upscaling feature (--enhance flag).

Tests cover:
- CLI argument parsing for --enhance and --scale
- Input image validation in enhance mode
- Output path generation ({stem}_enhanced.png default)
- Provider load/enhance/cleanup lifecycle (mocked)
- Error handling (missing file, bad format, download failures)
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Ensure imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestEnhanceCLIParsing:
    """Test --enhance and --scale argument parsing."""

    def test_enhance_flag_accepted(self):
        """--enhance should be accepted as a standalone mode."""
        import generate
        with patch("sys.argv", ["generate.py", "--enhance", "photo.png"]):
            args = generate.parse_args()
            assert args.enhance == "photo.png"

    def test_enhance_mutually_exclusive_with_prompt(self):
        """--enhance and --prompt cannot be used together."""
        import generate
        with patch("sys.argv", ["generate.py", "--enhance", "img.png", "--prompt", "test"]):
            with pytest.raises(SystemExit):
                generate.parse_args()

    def test_enhance_mutually_exclusive_with_batch(self):
        """--enhance and --batch-file cannot be used together."""
        import generate
        with patch("sys.argv", ["generate.py", "--enhance", "img.png", "--batch-file", "b.json"]):
            with pytest.raises(SystemExit):
                generate.parse_args()

    def test_scale_default_is_4(self):
        """--scale defaults to 4x."""
        import generate
        with patch("sys.argv", ["generate.py", "--enhance", "img.png"]):
            args = generate.parse_args()
            assert args.scale == 4

    def test_scale_2x(self):
        """--scale 2 sets 2x upscaling."""
        import generate
        with patch("sys.argv", ["generate.py", "--enhance", "img.png", "--scale", "2"]):
            args = generate.parse_args()
            assert args.scale == 2

    def test_scale_invalid_value_rejected(self):
        """--scale 3 should be rejected (only 2 and 4 allowed)."""
        import generate
        with patch("sys.argv", ["generate.py", "--enhance", "img.png", "--scale", "3"]):
            with pytest.raises(SystemExit):
                generate.parse_args()

    def test_enhance_with_output(self):
        """--enhance with --output specifies custom output path."""
        import generate
        with patch("sys.argv", ["generate.py", "--enhance", "img.png", "--output", "hi-res.png"]):
            args = generate.parse_args()
            assert args.enhance == "img.png"
            assert args.output == "hi-res.png"


class TestEnhanceImageFunction:
    """Test the enhance_image() function with mocked provider."""

    @patch("providers.realesrgan.RealESRGANProvider", autospec=False)
    @patch("generate.validate_input_image")
    @patch("generate.get_device", return_value="cpu")
    def test_enhance_default_output_naming(self, mock_device, mock_validate, mock_provider_cls, tmp_path):
        """Default output should be {stem}_enhanced.png."""
        import generate

        mock_img = MagicMock()
        mock_validate.return_value = mock_img

        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.size = (2048, 2048)
        mock_provider.enhance.return_value = mock_result
        mock_provider_cls.return_value = mock_provider

        args = SimpleNamespace(
            enhance="my-photo.png",
            output=None,
            scale=4,
            cpu=True,
        )

        with patch("os.makedirs"):
            output = generate.enhance_image(args)

        assert output == "outputs/my-photo_enhanced.png"
        mock_provider.load.assert_called_once_with("cpu", scale=4)
        mock_provider.enhance.assert_called_once()
        mock_provider.cleanup.assert_called_once()

    @patch("providers.realesrgan.RealESRGANProvider", autospec=False)
    @patch("generate.validate_input_image")
    @patch("generate.get_device", return_value="cpu")
    def test_enhance_custom_output(self, mock_device, mock_validate, mock_provider_cls, tmp_path):
        """User-specified --output path is respected."""
        import generate

        mock_img = MagicMock()
        mock_validate.return_value = mock_img

        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.size = (4096, 4096)
        mock_provider.enhance.return_value = mock_result
        mock_provider_cls.return_value = mock_provider

        custom_output = str(tmp_path / "hi-res.png")
        args = SimpleNamespace(
            enhance="input.png",
            output=custom_output,
            scale=4,
            cpu=True,
        )

        output = generate.enhance_image(args)
        assert output == custom_output
        mock_result.save.assert_called_once_with(custom_output)

    @patch("providers.realesrgan.RealESRGANProvider", autospec=False)
    @patch("generate.validate_input_image")
    @patch("generate.get_device", return_value="cpu")
    def test_enhance_cleanup_on_error(self, mock_device, mock_validate, mock_provider_cls):
        """Provider cleanup is called even when enhance() raises."""
        import generate

        mock_img = MagicMock()
        mock_validate.return_value = mock_img

        mock_provider = MagicMock()
        mock_provider.enhance.side_effect = RuntimeError("GPU exploded")
        mock_provider_cls.return_value = mock_provider

        args = SimpleNamespace(
            enhance="photo.png",
            output="out.png",
            scale=4,
            cpu=True,
        )

        with pytest.raises(RuntimeError, match="GPU exploded"):
            generate.enhance_image(args)

        mock_provider.cleanup.assert_called_once()

    @patch("providers.realesrgan.RealESRGANProvider", autospec=False)
    @patch("generate.validate_input_image")
    @patch("generate.get_device", return_value="cuda")
    def test_enhance_scale_2x(self, mock_device, mock_validate, mock_provider_cls):
        """Scale=2 is passed correctly to provider."""
        import generate

        mock_img = MagicMock()
        mock_validate.return_value = mock_img

        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.size = (1024, 1024)
        mock_provider.enhance.return_value = mock_result
        mock_provider_cls.return_value = mock_provider

        args = SimpleNamespace(
            enhance="photo.png",
            output="out.png",
            scale=2,
            cpu=False,
        )

        generate.enhance_image(args)
        mock_provider.load.assert_called_once_with("cuda", scale=2)


class TestEnhanceMainIntegration:
    """Test that main() routes --enhance correctly."""

    @patch("generate.enhance_image")
    def test_main_routes_to_enhance(self, mock_enhance):
        """main() should call enhance_image when --enhance is set."""
        import generate

        with patch("sys.argv", ["generate.py", "--enhance", "photo.png"]):
            generate.main()

        mock_enhance.assert_called_once()
        call_args = mock_enhance.call_args[0][0]
        assert call_args.enhance == "photo.png"

    @patch("generate.enhance_image")
    def test_main_enhance_does_not_require_prompt(self, mock_enhance):
        """Enhancement mode should work without any prompt."""
        import generate

        with patch("sys.argv", ["generate.py", "--enhance", "img.png", "--scale", "2"]):
            generate.main()

        mock_enhance.assert_called_once()


class TestBaseEnhancerABC:
    """Test the BaseEnhancer abstract interface."""

    def test_cannot_instantiate_base_enhancer(self):
        """BaseEnhancer is abstract and cannot be directly instantiated."""
        from providers.enhancer import BaseEnhancer
        with pytest.raises(TypeError):
            BaseEnhancer()

    def test_enhance_config_defaults(self):
        """EnhanceConfig defaults: scale=4, output_path=None."""
        from providers.enhancer import EnhanceConfig
        mock_img = MagicMock()
        config = EnhanceConfig(input_image=mock_img)
        assert config.scale == 4
        assert config.output_path is None


class TestRealESRGANProvider:
    """Test RealESRGANProvider with mocked dependencies."""

    def test_provider_properties(self):
        """Provider has correct friendly name and supported scales."""
        from providers.realesrgan import RealESRGANProvider
        p = RealESRGANProvider()
        assert p.friendly_name == "Real-ESRGAN"
        assert 2 in p.supported_scales
        assert 4 in p.supported_scales
        assert not p.is_loaded

    def test_unsupported_scale_raises(self):
        """Loading with unsupported scale raises ValueError."""
        from providers.realesrgan import RealESRGANProvider
        p = RealESRGANProvider()
        with pytest.raises(ValueError, match="Unsupported scale factor: 3"):
            p.load("cpu", scale=3)

    def test_enhance_before_load_raises(self):
        """Calling enhance() without load() raises RuntimeError."""
        from providers.realesrgan import RealESRGANProvider
        from providers.enhancer import EnhanceConfig
        p = RealESRGANProvider()
        config = EnhanceConfig(input_image=MagicMock(), scale=4)
        with pytest.raises(RuntimeError, match="Model not loaded"):
            p.enhance(config)

    def test_load_and_enhance_lifecycle(self):
        """Full lifecycle: load → enhance → cleanup."""
        import numpy as np
        from providers.realesrgan import RealESRGANProvider
        from providers.enhancer import EnhanceConfig

        mock_rrdb = MagicMock()
        mock_upsampler = MagicMock()
        # Simulate upscaler output (BGR numpy array)
        fake_output = np.zeros((200, 200, 3), dtype=np.uint8)
        mock_upsampler.enhance.return_value = (fake_output, None)

        mock_realesrgan_mod = MagicMock()
        mock_realesrgan_mod.RealESRGANer.return_value = mock_upsampler

        mock_basicsr_arch = MagicMock()
        mock_basicsr_arch.RRDBNet.return_value = mock_rrdb

        with patch.dict("sys.modules", {
            "torch": MagicMock(),
            "basicsr": MagicMock(),
            "basicsr.archs": MagicMock(),
            "basicsr.archs.rrdbnet_arch": mock_basicsr_arch,
            "realesrgan": mock_realesrgan_mod,
        }):
            p = RealESRGANProvider()
            p.load("cpu", scale=4)

        assert p.is_loaded

        # Create a real PIL image for enhance
        from PIL import Image
        input_img = Image.new("RGB", (50, 50), color=(128, 64, 32))
        config = EnhanceConfig(input_image=input_img, scale=4)
        result = p.enhance(config)

        assert isinstance(result, Image.Image)
        mock_upsampler.enhance.assert_called_once()

        p.cleanup()
        assert not p.is_loaded

    def test_download_error_gives_friendly_message(self):
        """Network errors produce a user-friendly message."""
        from providers.realesrgan import RealESRGANProvider

        mock_realesrgan_mod = MagicMock()
        mock_realesrgan_mod.RealESRGANer.side_effect = Exception("Failed to download from URL")

        mock_basicsr_arch = MagicMock()

        with patch.dict("sys.modules", {
            "torch": MagicMock(),
            "basicsr": MagicMock(),
            "basicsr.archs": MagicMock(),
            "basicsr.archs.rrdbnet_arch": mock_basicsr_arch,
            "realesrgan": mock_realesrgan_mod,
        }):
            p = RealESRGANProvider()
            with pytest.raises(RuntimeError, match="Could not download upscaling model"):
                p.load("cpu", scale=4)
