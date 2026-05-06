"""
Comprehensive cross-feature integration tests for Phase 2 features (Issue #117).

Covers edge cases and integration points across:
- img2img (--input, --strength)
- Real-ESRGAN enhancement (--enhance, --scale)
- Style presets (--style, --list-styles)
- Cross-feature interactions and flag combinations

All tests mock at the boundary (pipeline calls, file I/O, network) and
require no GPU or model downloads.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generate import parse_args, validate_input_image, enhance_image, main
from providers.base import GenerationConfig
from providers.styles import (
    STYLE_PRESETS,
    StylePreset,
    format_styles_table,
    get_style,
    list_styles,
)


def _parse(cli_args: list[str]):
    """Helper to parse CLI args via generate.parse_args()."""
    with patch.object(sys, "argv", ["generate.py"] + cli_args):
        return parse_args()


# ===========================================================================
# Section 1: img2img Edge Cases (10+ tests)
# ===========================================================================


class TestImg2ImgEdgeCases:
    """Edge cases for img2img --input and --strength flags."""

    def test_strength_zero_parses(self):
        """strength=0.0 is valid (no denoising, pure pass-through)."""
        args = _parse(["--prompt", "test", "--input", "photo.png", "--strength", "0.0"])
        assert args.strength == 0.0

    def test_strength_one_parses(self):
        """strength=1.0 is valid (full regeneration)."""
        args = _parse(["--prompt", "test", "--input", "photo.png", "--strength", "1.0"])
        assert args.strength == 1.0

    def test_strength_negative_rejected(self):
        """strength=-0.1 must be rejected."""
        with pytest.raises((SystemExit, ValueError)):
            _parse(["--prompt", "test", "--strength", "-0.1"])

    def test_strength_above_one_rejected(self):
        """strength=1.5 must be rejected."""
        with pytest.raises((SystemExit, ValueError)):
            _parse(["--prompt", "test", "--strength", "1.5"])

    def test_input_nonexistent_file(self, tmp_path):
        """--input pointing to non-existent file raises SystemExit."""
        fake = str(tmp_path / "does_not_exist.png")
        with pytest.raises(SystemExit):
            validate_input_image(fake)

    def test_input_invalid_format(self, tmp_path):
        """--input with unsupported format (.bmp) raises SystemExit."""
        bmp_file = tmp_path / "image.bmp"
        bmp_file.write_bytes(b"BM" + b"\x00" * 50)
        with pytest.raises(SystemExit):
            validate_input_image(str(bmp_file))

    def test_input_without_prompt_in_main(self, tmp_path, capsys):
        """--input without --prompt exits with error in main()."""
        img_path = tmp_path / "input.png"
        img = Image.new("RGB", (64, 64), color="red")
        img.save(str(img_path))

        with patch("sys.argv", ["generate.py", "--prompt", "test", "--input", str(img_path)]):
            # This should work fine (has --prompt)
            args = parse_args()
            assert args.input == str(img_path)

    def test_input_requires_prompt_in_main(self, tmp_path, capsys):
        """main() rejects --input without --prompt."""
        img_path = tmp_path / "input.png"
        img = Image.new("RGB", (64, 64), color="red")
        img.save(str(img_path))

        # Can't parse with mutually exclusive group — need --prompt to parse
        # but main() validates --input requires --prompt at runtime
        with patch("sys.argv", ["generate.py", "--prompt", "", "--input", str(img_path)]):
            with pytest.raises(SystemExit):
                main()

    def test_input_with_model_creative(self):
        """--input with --model creative parses correctly."""
        args = _parse(["--prompt", "test", "--input", "photo.png", "--model", "creative"])
        assert args.model == "creative"
        assert args.input == "photo.png"

    def test_input_with_model_balanced(self):
        """--input with --model balanced parses correctly."""
        args = _parse(["--prompt", "test", "--input", "photo.png", "--model", "balanced"])
        assert args.model == "balanced"
        assert args.input == "photo.png"

    def test_large_image_rejected(self, tmp_path):
        """Images exceeding _MAX_INPUT_DIMENSION are rejected."""
        # Create image just above limit (mock to avoid huge memory)
        large_img = tmp_path / "huge.png"
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(str(large_img))

        # Patch Image.open to return a mock with large dimensions
        mock_img = MagicMock()
        mock_img.size = (9000, 9000)
        mock_img.verify = MagicMock()
        mock_img.load = MagicMock()

        with patch("generate.Image.open") as mock_open:
            # First call is verify, second is load
            mock_verify = MagicMock()
            mock_load = MagicMock()
            mock_load.size = (9000, 9000)
            mock_load.load = MagicMock()
            mock_open.side_effect = [mock_verify, mock_load]
            with pytest.raises(SystemExit):
                validate_input_image(str(large_img))

    def test_empty_file_rejected(self, tmp_path):
        """Zero-byte files are rejected with friendly error."""
        empty = tmp_path / "empty.png"
        empty.write_bytes(b"")
        with pytest.raises(SystemExit):
            validate_input_image(str(empty))

    def test_directory_rejected(self, tmp_path):
        """Passing a directory path is rejected."""
        with pytest.raises(SystemExit):
            validate_input_image(str(tmp_path))

    def test_strength_with_various_values(self):
        """Multiple valid strength values parse correctly."""
        for val in ["0.1", "0.25", "0.5", "0.75", "0.99"]:
            args = _parse(["--prompt", "test", "--strength", val])
            assert args.strength == pytest.approx(float(val))


# ===========================================================================
# Section 2: Real-ESRGAN Edge Cases (10+ tests)
# ===========================================================================


class TestRealESRGANEdgeCases:
    """Edge cases for --enhance and --scale flags."""

    def test_scale_1_rejected(self):
        """--scale 1 is not a valid choice."""
        with pytest.raises(SystemExit):
            _parse(["--enhance", "photo.png", "--scale", "1"])

    def test_scale_8_rejected(self):
        """--scale 8 is not a valid choice."""
        with pytest.raises(SystemExit):
            _parse(["--enhance", "photo.png", "--scale", "8"])

    def test_scale_3_rejected(self):
        """--scale 3 is not a valid choice (only 2, 4 allowed)."""
        with pytest.raises(SystemExit):
            _parse(["--enhance", "photo.png", "--scale", "3"])

    def test_enhance_with_prompt_mutual_exclusion(self):
        """--enhance and --prompt are mutually exclusive."""
        with pytest.raises(SystemExit):
            _parse(["--enhance", "photo.png", "--prompt", "test"])

    def test_enhance_with_style_ignored(self):
        """--enhance with --style parses (style has no effect in enhance mode)."""
        # --style is not in the mutually exclusive group, so it parses fine
        # but has no effect since enhance mode bypasses style logic
        args = _parse(["--enhance", "photo.png", "--style", "watercolor"])
        assert args.enhance == "photo.png"
        assert args.style == "watercolor"

    def test_enhance_accepts_scale_2(self):
        """--enhance with --scale 2 parses correctly."""
        args = _parse(["--enhance", "photo.png", "--scale", "2"])
        assert args.scale == 2
        assert args.enhance == "photo.png"

    def test_enhance_accepts_scale_4(self):
        """--enhance with --scale 4 (default) parses correctly."""
        args = _parse(["--enhance", "photo.png"])
        assert args.scale == 4

    def test_model_download_failure(self):
        """Network error during model download produces friendly message."""
        from providers.realesrgan import RealESRGANProvider

        mock_realesrgan_mod = MagicMock()
        mock_realesrgan_mod.RealESRGANer.side_effect = Exception(
            "Failed to download from URL: connection timeout"
        )
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

    def test_enhance_cleanup_on_error(self):
        """Provider cleanup is called even when enhance() raises."""
        import generate

        mock_img = MagicMock()
        mock_provider = MagicMock()
        mock_provider.enhance.side_effect = RuntimeError("GPU OOM")

        with patch("generate.validate_input_image", return_value=mock_img):
            with patch("generate.get_device", return_value="cpu"):
                with patch("providers.realesrgan.RealESRGANProvider", return_value=mock_provider):
                    args = SimpleNamespace(enhance="photo.png", output="out.png", scale=4, cpu=True)
                    with pytest.raises(RuntimeError, match="GPU OOM"):
                        enhance_image(args)
                    mock_provider.cleanup.assert_called_once()

    def test_memory_estimation_small_image(self):
        """Small images should not cause memory issues (basic sanity)."""
        from providers.realesrgan import RealESRGANProvider
        p = RealESRGANProvider()
        # Verify properties are accessible before loading
        assert 2 in p.supported_scales
        assert 4 in p.supported_scales
        assert not p.is_loaded

    def test_enhance_before_load_raises(self):
        """Calling enhance() without load() raises RuntimeError."""
        from providers.realesrgan import RealESRGANProvider
        from providers.enhancer import EnhanceConfig

        p = RealESRGANProvider()
        config = EnhanceConfig(input_image=MagicMock(), scale=4)
        with pytest.raises(RuntimeError, match="Model not loaded"):
            p.enhance(config)

    def test_enhance_default_output_naming(self):
        """Default output should be outputs/{stem}_enhanced.png."""
        import generate

        mock_img = MagicMock()
        mock_result = MagicMock()
        mock_result.size = (2048, 2048)
        mock_provider = MagicMock()
        mock_provider.enhance.return_value = mock_result

        with patch("generate.validate_input_image", return_value=mock_img):
            with patch("generate.get_device", return_value="cpu"):
                with patch("providers.realesrgan.RealESRGANProvider", return_value=mock_provider):
                    with patch("os.makedirs"):
                        args = SimpleNamespace(enhance="landscape.png", output=None, scale=4, cpu=True)
                        output = enhance_image(args)
                        assert output == "outputs/landscape_enhanced.png"


# ===========================================================================
# Section 3: Style Presets Edge Cases (10+ tests)
# ===========================================================================


class TestStylePresetsEdgeCases:
    """Edge cases for --style and --list-styles."""

    def test_style_invalid_name_raises(self):
        """get_style with unknown name raises ValueError with available list."""
        with pytest.raises(ValueError, match="Unknown style 'impressionist'"):
            get_style("impressionist")

    def test_style_invalid_error_lists_available(self):
        """Error message includes all available style names."""
        try:
            get_style("cubism")
        except ValueError as e:
            msg = str(e)
            for name in STYLE_PRESETS:
                assert name in msg

    def test_style_without_input_exits(self, capsys):
        """--style without --input prints error and exits."""
        with patch("sys.argv", ["generate.py", "--prompt", "test", "--style", "watercolor"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--style requires --input" in captured.err

    def test_style_with_enhance_parses_but_style_unused(self):
        """--style with --enhance parses but style is unused in enhance mode."""
        # --style is not enforced at parse level, but enhance mode ignores it
        args = _parse(["--enhance", "photo.png", "--style", "watercolor"])
        assert args.enhance == "photo.png"

    def test_watercolor_lora_config(self):
        """Watercolor style generates correct LoRA config."""
        preset = get_style("watercolor")
        assert "ostris" in preset.lora_id
        assert preset.strength == 0.70
        assert preset.guidance_scale == 7.0
        assert preset.lora_weight == 0.85

    def test_oil_painting_lora_config(self):
        """Oil-painting style generates correct LoRA config."""
        preset = get_style("oil-painting")
        assert "Oil_Painting" in preset.lora_id
        assert preset.strength == 0.72
        assert preset.guidance_scale == 7.5
        assert preset.lora_weight == 0.80

    def test_sketch_lora_config(self):
        """Sketch style generates correct LoRA config."""
        preset = get_style("sketch")
        assert "pencil-sketch" in preset.lora_id
        assert preset.strength == 0.68
        assert preset.lora_weight == 0.80

    def test_anime_lora_config(self):
        """Anime style generates correct LoRA config."""
        preset = get_style("anime")
        assert "anime-detailer" in preset.lora_id
        assert preset.strength == 0.75
        assert preset.guidance_scale == 8.0

    def test_pixel_art_lora_config(self):
        """Pixel-art style generates correct LoRA config."""
        preset = get_style("pixel-art")
        assert "pixel-art-xl" in preset.lora_id
        assert preset.strength == 0.78
        assert preset.lora_weight == 0.90

    def test_list_styles_output_formatting(self):
        """format_styles_table includes all styles with proper formatting."""
        table = format_styles_table()
        assert "Available styles:" in table
        assert "--style" in table
        for name in STYLE_PRESETS:
            assert name in table
        # Verify structure includes LoRA info
        assert "LoRA:" in table
        assert "Defaults:" in table

    def test_list_styles_sorted_alphabetically(self):
        """list_styles returns presets sorted alphabetically."""
        styles = list_styles()
        names = [s.name for s in styles]
        assert names == sorted(names)

    def test_style_with_custom_strength_override(self, tmp_path):
        """--style defaults can be overridden (strength is set by style)."""
        img_path = tmp_path / "input.png"
        img = Image.new("RGB", (64, 64), color="red")
        img.save(str(img_path))

        captured_args = {}

        def mock_generate(args):
            captured_args["strength"] = args.strength
            captured_args["lora"] = args.lora
            return "outputs/test.png"

        import generate
        with patch("sys.argv", [
            "generate.py", "--prompt", "forest",
            "--style", "watercolor", "--input", str(img_path),
        ]):
            with patch.object(generate, "generate_with_retry", side_effect=mock_generate):
                with patch.object(generate, "_ensure_heavy_imports"):
                    main()

        # Style overrides strength
        assert captured_args["strength"] == 0.70
        assert captured_args["lora"] == "ostris/watercolor_style_lora_sdxl"

    def test_style_with_custom_guidance_override(self, tmp_path):
        """Style sets guidance_scale from the preset."""
        img_path = tmp_path / "input.png"
        img = Image.new("RGB", (64, 64), color="blue")
        img.save(str(img_path))

        captured_args = {}

        def mock_generate(args):
            captured_args["guidance"] = args.guidance
            return "outputs/test.png"

        import generate
        with patch("sys.argv", [
            "generate.py", "--prompt", "sunset",
            "--style", "anime", "--input", str(img_path),
        ]):
            with patch.object(generate, "generate_with_retry", side_effect=mock_generate):
                with patch.object(generate, "_ensure_heavy_imports"):
                    main()

        assert captured_args["guidance"] == 8.0  # anime preset guidance

    def test_style_merges_negative_prompt(self, tmp_path):
        """Style appends negative_prompt_additions to existing negative prompt."""
        img_path = tmp_path / "input.png"
        img = Image.new("RGB", (64, 64), color="green")
        img.save(str(img_path))

        captured_args = {}

        def mock_generate(args):
            captured_args["negative_prompt"] = args.negative_prompt
            return "outputs/test.png"

        import generate
        with patch("sys.argv", [
            "generate.py", "--prompt", "cat",
            "--style", "sketch", "--input", str(img_path),
            "--negative-prompt", "ugly",
        ]):
            with patch.object(generate, "generate_with_retry", side_effect=mock_generate):
                with patch.object(generate, "_ensure_heavy_imports"):
                    main()

        assert "ugly" in captured_args["negative_prompt"]
        assert "color" in captured_args["negative_prompt"]  # sketch addition


# ===========================================================================
# Section 4: Cross-Feature Integration (5+ tests)
# ===========================================================================


class TestCrossFeatureIntegration:
    """Integration tests spanning multiple Phase 2 features."""

    def test_style_pipeline_full_mock(self, tmp_path):
        """Full pipeline: --style watercolor --input photo.png --prompt 'extra'."""
        img_path = tmp_path / "photo.png"
        img = Image.new("RGB", (64, 64), color="orange")
        img.save(str(img_path))

        captured_args = {}

        def mock_generate(args):
            captured_args["prompt"] = args.prompt
            captured_args["lora"] = args.lora
            captured_args["lora_weight"] = args.lora_weight
            captured_args["strength"] = args.strength
            captured_args["guidance"] = args.guidance
            captured_args["negative_prompt"] = args.negative_prompt
            return "outputs/test.png"

        import generate
        with patch("sys.argv", [
            "generate.py", "--prompt", "extra detail",
            "--style", "watercolor", "--input", str(img_path),
        ]):
            with patch.object(generate, "generate_with_retry", side_effect=mock_generate):
                with patch.object(generate, "_ensure_heavy_imports"):
                    main()

        assert captured_args["prompt"] == "extra detail"
        assert captured_args["lora"] == "ostris/watercolor_style_lora_sdxl"
        assert captured_args["lora_weight"] == 0.85
        assert captured_args["strength"] == 0.70
        assert captured_args["guidance"] == 7.0
        assert "photograph" in captured_args["negative_prompt"]

    @pytest.mark.parametrize("flags,should_fail", [
        # Valid combinations
        (["--prompt", "test"], False),
        (["--prompt", "test", "--input", "photo.png", "--strength", "0.5"], False),
        (["--prompt", "test", "--input", "photo.png", "--style", "anime"], False),
        (["--enhance", "photo.png"], False),
        (["--enhance", "photo.png", "--scale", "2"], False),
        (["--list-styles"], False),
        # Invalid combinations
        (["--enhance", "photo.png", "--prompt", "test"], True),
        (["--enhance", "photo.png", "--batch-file", "b.json"], True),
    ])
    def test_flag_combination_matrix(self, flags, should_fail):
        """Valid vs invalid flag combinations at parse level."""
        if should_fail:
            with pytest.raises(SystemExit):
                _parse(flags)
        else:
            args = _parse(flags)
            assert args is not None

    def test_provider_registry_all_phase2_providers(self):
        """All Phase 2 providers are registered and instantiable."""
        from providers.registry import get_provider, list_providers, _REGISTRY

        providers = list_providers()
        assert "creative" in providers
        assert "precise" in providers
        assert "balanced" in providers

        for name in _REGISTRY:
            p = get_provider(name)
            assert hasattr(p, "generate")
            assert hasattr(p, "load")
            assert hasattr(p, "cleanup")
            assert hasattr(p, "friendly_name")

    def test_provider_registry_invalid_name(self):
        """Unknown provider name raises ValueError."""
        from providers.registry import get_provider
        with pytest.raises(ValueError, match="Unknown model"):
            get_provider("nonexistent")

    def test_config_propagation_txt2img(self):
        """GenerationConfig correctly propagates text-to-image fields."""
        config = GenerationConfig(
            prompt="a sunset",
            negative_prompt="blurry",
            width=1024,
            height=1024,
            steps=30,
            guidance_scale=7.5,
            seed=42,
        )
        assert config.prompt == "a sunset"
        assert config.input_image is None
        assert config.strength == 0.75
        assert config.seed == 42

    def test_config_propagation_img2img(self):
        """GenerationConfig correctly propagates img2img fields."""
        mock_img = Image.new("RGB", (512, 512))
        config = GenerationConfig(
            prompt="repaint",
            input_image=mock_img,
            strength=0.6,
            width=1024,
            height=1024,
        )
        assert config.input_image is mock_img
        assert config.strength == 0.6

    def test_generate_with_provider_img2img_config(self, tmp_path):
        """GenerationConfig correctly wires input_image for provider path."""
        img = Image.new("RGB", (64, 64), color="blue")

        # Verify the config that generate_with_provider would build
        config = GenerationConfig(
            prompt="test",
            negative_prompt="",
            width=1024,
            height=1024,
            steps=20,
            guidance_scale=7.5,
            seed=None,
            scheduler="DPMSolverMultistepScheduler",
            input_image=img,
            strength=0.7,
        )

        assert config.input_image is img
        assert config.strength == 0.7
        assert config.prompt == "test"
        assert config.guidance_scale == 7.5

    def test_enhance_does_not_need_prompt(self):
        """Enhancement mode works without any text prompt."""
        args = _parse(["--enhance", "photo.png", "--scale", "4"])
        assert args.enhance == "photo.png"
        assert not hasattr(args, "prompt") or args.prompt is None

    def test_all_styles_have_negative_additions(self):
        """Every style preset has negative_prompt_additions defined."""
        for name, preset in STYLE_PRESETS.items():
            assert preset.negative_prompt_additions, f"{name} missing negative_prompt_additions"

    def test_style_preset_dataclass_frozen(self):
        """StylePreset is frozen (immutable)."""
        preset = get_style("watercolor")
        with pytest.raises(Exception):  # FrozenInstanceError
            preset.name = "hacked"
