"""Tests for style transfer presets (--style, --list-styles).

Covers:
- Style registry lookup (valid/invalid names)
- format_styles_table output
- CLI --list-styles flag
- CLI --style requires --input validation
- --style applies LoRA and defaults correctly
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch

import pytest

from providers.styles import (
    STYLE_PRESETS,
    StylePreset,
    format_styles_table,
    get_style,
    list_styles,
)


class TestStyleRegistry:
    """Tests for the style preset registry."""

    def test_all_presets_exist(self):
        """All five required presets are registered."""
        expected = {"watercolor", "oil-painting", "sketch", "anime", "pixel-art"}
        assert expected == set(STYLE_PRESETS.keys())

    def test_get_style_valid(self):
        """get_style returns the correct preset for known names."""
        preset = get_style("watercolor")
        assert isinstance(preset, StylePreset)
        assert preset.name == "watercolor"
        assert "ostris" in preset.lora_id

    def test_get_style_invalid(self):
        """get_style raises ValueError for unknown style names."""
        with pytest.raises(ValueError, match="Unknown style 'nonexistent'"):
            get_style("nonexistent")

    def test_list_styles_sorted(self):
        """list_styles returns presets sorted alphabetically by name."""
        styles = list_styles()
        names = [s.name for s in styles]
        assert names == sorted(names)
        assert len(styles) == 5

    def test_preset_has_required_fields(self):
        """Every preset has all required fields populated."""
        for name, preset in STYLE_PRESETS.items():
            assert preset.name == name
            assert preset.lora_id, f"{name} missing lora_id"
            assert preset.description, f"{name} missing description"
            assert 0.0 < preset.strength <= 1.0
            assert preset.guidance_scale > 0
            assert 0.0 < preset.lora_weight <= 1.0

    def test_format_styles_table(self):
        """format_styles_table produces readable output with all styles."""
        table = format_styles_table()
        assert "Available styles:" in table
        for name in STYLE_PRESETS:
            assert name in table
        assert "--style" in table


class TestStyleCLI:
    """Tests for --style and --list-styles CLI integration."""

    def test_list_styles_flag(self, capsys):
        """--list-styles prints table and exits without generation."""
        with patch("sys.argv", ["generate.py", "--list-styles"]):
            import generate
            generate.main()
        captured = capsys.readouterr()
        assert "Available styles:" in captured.out
        assert "watercolor" in captured.out

    def test_style_requires_input(self, capsys):
        """--style without --input prints error and exits."""
        with patch("sys.argv", ["generate.py", "--prompt", "test", "--style", "watercolor"]):
            import generate
            with pytest.raises(SystemExit) as exc_info:
                generate.main()
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--style requires --input" in captured.err

    def test_style_applies_lora_defaults(self, tmp_path):
        """--style sets lora, lora_weight, strength, guidance from preset."""
        # Create a fake input image
        from PIL import Image
        img_path = tmp_path / "input.png"
        img = Image.new("RGB", (64, 64), color="red")
        img.save(str(img_path))

        with patch("sys.argv", [
            "generate.py", "--prompt", "a forest",
            "--style", "anime", "--input", str(img_path),
        ]):
            import generate

            # Patch generate_with_retry to capture args
            captured_args = {}

            def mock_generate(args):
                captured_args["lora"] = args.lora
                captured_args["lora_weight"] = args.lora_weight
                captured_args["strength"] = args.strength
                captured_args["guidance"] = args.guidance
                return "outputs/test.png"

            with patch.object(generate, "generate_with_retry", side_effect=mock_generate):
                with patch.object(generate, "_ensure_heavy_imports"):
                    generate.main()

        preset = get_style("anime")
        assert captured_args["lora"] == preset.lora_id
        assert captured_args["lora_weight"] == preset.lora_weight
        assert captured_args["strength"] == preset.strength
        assert captured_args["guidance"] == preset.guidance_scale

    def test_style_with_prompt_combination(self, tmp_path):
        """--style can be combined with --prompt for additional direction."""
        from PIL import Image
        img_path = tmp_path / "input.png"
        img = Image.new("RGB", (64, 64), color="blue")
        img.save(str(img_path))

        with patch("sys.argv", [
            "generate.py", "--prompt", "autumn forest sunset",
            "--style", "oil-painting", "--input", str(img_path),
        ]):
            import generate

            captured_args = {}

            def mock_generate(args):
                captured_args["prompt"] = args.prompt
                captured_args["lora"] = args.lora
                return "outputs/test.png"

            with patch.object(generate, "generate_with_retry", side_effect=mock_generate):
                with patch.object(generate, "_ensure_heavy_imports"):
                    generate.main()

        assert captured_args["prompt"] == "autumn forest sunset"
        assert captured_args["lora"] == "TheLastBen/Oil_Painting_SDXL_LoRA"

    def test_style_merges_negative_prompt(self, tmp_path):
        """--style appends its negative prompt additions to existing negative."""
        from PIL import Image
        img_path = tmp_path / "input.png"
        img = Image.new("RGB", (64, 64), color="green")
        img.save(str(img_path))

        with patch("sys.argv", [
            "generate.py", "--prompt", "a cat",
            "--style", "pixel-art", "--input", str(img_path),
            "--negative-prompt", "ugly",
        ]):
            import generate

            captured_args = {}

            def mock_generate(args):
                captured_args["negative_prompt"] = args.negative_prompt
                return "outputs/test.png"

            with patch.object(generate, "generate_with_retry", side_effect=mock_generate):
                with patch.object(generate, "_ensure_heavy_imports"):
                    generate.main()

        assert "ugly" in captured_args["negative_prompt"]
        assert "smooth" in captured_args["negative_prompt"]  # pixel-art addition
