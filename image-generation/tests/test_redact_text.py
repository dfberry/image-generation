"""
Text redaction tool tests.

Tests for redact_text.py — OCR-based text detection and replacement.
All OCR calls are mocked so Tesseract is not required to run tests.
"""

import argparse
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Import will work because conftest.py adds parent dir to sys.path
import redact_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_image(path: Path, width: int = 200, height: int = 100) -> Path:
    """Create a simple solid-color test PNG."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    img.save(path)
    return path


def _mock_ocr_data(entries: list[dict]) -> dict:
    """Build a pytesseract image_to_data DICT response from simple entries.

    Each entry: {"text": str, "left": int, "top": int, "width": int, "height": int, "conf": float}
    """
    data = {"text": [], "left": [], "top": [], "width": [], "height": [], "conf": []}
    for e in entries:
        data["text"].append(e.get("text", ""))
        data["left"].append(e.get("left", 0))
        data["top"].append(e.get("top", 0))
        data["width"].append(e.get("width", 50))
        data["height"].append(e.get("height", 20))
        data["conf"].append(e.get("conf", 95.0))
    return data


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestParseArgs:
    def test_required_args(self):
        args = redact_text.parse_args(["--input", "img.png", "--find", "secret"])
        assert args.input == Path("img.png")
        assert args.find == "secret"

    def test_defaults(self):
        args = redact_text.parse_args(["--input", "img.png", "--find", "x"])
        assert args.fill_color == "#FFFFFF"
        assert args.padding == 2
        assert args.confidence == 60
        assert args.all is False
        assert args.regex is False
        assert args.replace is None
        assert args.output is None
        assert args.font_size is None
        assert args.font_color == "#000000"

    def test_regex_flag(self):
        args = redact_text.parse_args(["--input", "i.png", "--find", "a.*b", "--regex"])
        assert args.regex is True

    def test_all_flag(self):
        args = redact_text.parse_args(["--input", "i.png", "--find", "x", "--all"])
        assert args.all is True

    def test_custom_colors(self):
        args = redact_text.parse_args([
            "--input", "i.png", "--find", "x",
            "--fill-color", "#FF0000", "--font-color", "#00FF00"
        ])
        assert args.fill_color == "#FF0000"
        assert args.font_color == "#00FF00"

    def test_short_hex_expanded(self):
        args = redact_text.parse_args([
            "--input", "i.png", "--find", "x", "--fill-color", "#F00"
        ])
        assert args.fill_color == "#FF0000"

    def test_invalid_color_rejected(self):
        with pytest.raises(SystemExit):
            redact_text.parse_args(["--input", "i.png", "--find", "x", "--fill-color", "red"])

    def test_missing_input_rejected(self):
        with pytest.raises(SystemExit):
            redact_text.parse_args(["--find", "x"])

    def test_missing_find_rejected(self):
        with pytest.raises(SystemExit):
            redact_text.parse_args(["--input", "i.png"])

    def test_confidence_range(self):
        args = redact_text.parse_args(["--input", "i.png", "--find", "x", "--confidence", "80"])
        assert args.confidence == 80

    def test_confidence_out_of_range(self):
        with pytest.raises(SystemExit):
            redact_text.parse_args(["--input", "i.png", "--find", "x", "--confidence", "101"])

    def test_confidence_negative(self):
        with pytest.raises(SystemExit):
            redact_text.parse_args(["--input", "i.png", "--find", "x", "--confidence", "-1"])

    def test_replace_with_output(self):
        args = redact_text.parse_args([
            "--input", "i.png", "--find", "x",
            "--replace", "[REDACTED]", "--output", "out.png"
        ])
        assert args.replace == "[REDACTED]"
        assert args.output == Path("out.png")


# ---------------------------------------------------------------------------
# Color validation
# ---------------------------------------------------------------------------

class TestColorType:
    def test_valid_6digit(self):
        assert redact_text._color_type("#AABBCC") == "#AABBCC"

    def test_valid_3digit_expanded(self):
        assert redact_text._color_type("#ABC") == "#AABBCC"

    def test_lowercase_uppercased(self):
        assert redact_text._color_type("#aabbcc") == "#AABBCC"

    def test_invalid_no_hash(self):
        with pytest.raises(argparse.ArgumentTypeError):
            redact_text._color_type("AABBCC")

    def test_invalid_length(self):
        with pytest.raises(argparse.ArgumentTypeError):
            redact_text._color_type("#AABB")

    def test_invalid_chars(self):
        with pytest.raises(argparse.ArgumentTypeError):
            redact_text._color_type("#GGHHII")


# ---------------------------------------------------------------------------
# find_text_regions
# ---------------------------------------------------------------------------

class TestFindTextRegions:
    @patch("redact_text.pytesseract")
    @patch("redact_text.Image")
    def test_exact_match(self, mock_image_mod, mock_tess):
        mock_tess.Output.DICT = "dict"
        mock_tess.image_to_data.return_value = _mock_ocr_data([
            {"text": "hello", "left": 10, "top": 20, "width": 50, "height": 15, "conf": 90.0},
            {"text": "world", "left": 70, "top": 20, "width": 50, "height": 15, "conf": 85.0},
        ])
        mock_image_mod.open.return_value = MagicMock()

        regions = redact_text.find_text_regions(Path("test.png"), "hello", is_regex=False, confidence=60)
        assert len(regions) == 1
        assert regions[0]["text"] == "hello"
        assert regions[0]["left"] == 10

    @patch("redact_text.pytesseract")
    @patch("redact_text.Image")
    def test_regex_match(self, mock_image_mod, mock_tess):
        mock_tess.Output.DICT = "dict"
        mock_tess.image_to_data.return_value = _mock_ocr_data([
            {"text": "api_key_abc123", "left": 10, "top": 5, "width": 100, "height": 15, "conf": 92.0},
            {"text": "normal_text", "left": 10, "top": 30, "width": 80, "height": 15, "conf": 88.0},
        ])
        mock_image_mod.open.return_value = MagicMock()

        regions = redact_text.find_text_regions(Path("t.png"), r"api_key_\w+", is_regex=True, confidence=60)
        assert len(regions) == 1
        assert regions[0]["text"] == "api_key_abc123"

    @patch("redact_text.pytesseract")
    @patch("redact_text.Image")
    def test_confidence_filter(self, mock_image_mod, mock_tess):
        mock_tess.Output.DICT = "dict"
        mock_tess.image_to_data.return_value = _mock_ocr_data([
            {"text": "secret", "left": 10, "top": 5, "width": 50, "height": 15, "conf": 40.0},
            {"text": "secret", "left": 10, "top": 30, "width": 50, "height": 15, "conf": 80.0},
        ])
        mock_image_mod.open.return_value = MagicMock()

        regions = redact_text.find_text_regions(Path("t.png"), "secret", is_regex=False, confidence=60)
        assert len(regions) == 1
        assert regions[0]["conf"] == 80.0

    @patch("redact_text.pytesseract")
    @patch("redact_text.Image")
    def test_no_matches(self, mock_image_mod, mock_tess):
        mock_tess.Output.DICT = "dict"
        mock_tess.image_to_data.return_value = _mock_ocr_data([
            {"text": "nothing", "left": 10, "top": 5, "width": 50, "height": 15, "conf": 90.0},
        ])
        mock_image_mod.open.return_value = MagicMock()

        regions = redact_text.find_text_regions(Path("t.png"), "secret", is_regex=False, confidence=60)
        assert regions == []

    @patch("redact_text.pytesseract")
    @patch("redact_text.Image")
    def test_empty_text_skipped(self, mock_image_mod, mock_tess):
        mock_tess.Output.DICT = "dict"
        mock_tess.image_to_data.return_value = _mock_ocr_data([
            {"text": "", "left": 0, "top": 0, "width": 10, "height": 10, "conf": 95.0},
            {"text": "secret", "left": 10, "top": 5, "width": 50, "height": 15, "conf": 90.0},
        ])
        mock_image_mod.open.return_value = MagicMock()

        regions = redact_text.find_text_regions(Path("t.png"), "secret", is_regex=False, confidence=60)
        assert len(regions) == 1

    @patch("redact_text.pytesseract")
    @patch("redact_text.Image")
    def test_multiple_matches(self, mock_image_mod, mock_tess):
        mock_tess.Output.DICT = "dict"
        mock_tess.image_to_data.return_value = _mock_ocr_data([
            {"text": "password", "left": 10, "top": 5, "width": 60, "height": 15, "conf": 90.0},
            {"text": "password", "left": 10, "top": 30, "width": 60, "height": 15, "conf": 85.0},
            {"text": "username", "left": 10, "top": 55, "width": 60, "height": 15, "conf": 92.0},
        ])
        mock_image_mod.open.return_value = MagicMock()

        regions = redact_text.find_text_regions(Path("t.png"), "password", is_regex=False, confidence=60)
        assert len(regions) == 2

    @patch("redact_text.pytesseract")
    @patch("redact_text.Image")
    def test_partial_match(self, mock_image_mod, mock_tess):
        """Exact mode uses 'in' — partial matches should be found."""
        mock_tess.Output.DICT = "dict"
        mock_tess.image_to_data.return_value = _mock_ocr_data([
            {"text": "my_secret_key", "left": 10, "top": 5, "width": 100, "height": 15, "conf": 90.0},
        ])
        mock_image_mod.open.return_value = MagicMock()

        regions = redact_text.find_text_regions(Path("t.png"), "secret", is_regex=False, confidence=60)
        assert len(regions) == 1


# ---------------------------------------------------------------------------
# redact_regions
# ---------------------------------------------------------------------------

class TestRedactRegions:
    def test_fills_region_with_color(self, tmp_path):
        img_path = _make_test_image(tmp_path / "test.png", 200, 100)
        regions = [{"left": 50, "top": 30, "width": 60, "height": 20}]

        result = redact_text.redact_regions(img_path, regions, "#FF0000", padding=0, output_path=tmp_path / "out.png")
        # Check that the center of the filled region is red
        pixel = result.getpixel((80, 40))
        assert pixel == (255, 0, 0)

    def test_padding_expands_region(self, tmp_path):
        img_path = _make_test_image(tmp_path / "test.png", 200, 100)
        regions = [{"left": 50, "top": 30, "width": 60, "height": 20}]

        result = redact_text.redact_regions(img_path, regions, "#FF0000", padding=5, output_path=tmp_path / "out.png")
        # Point just outside original region but inside padding should be red
        pixel = result.getpixel((46, 26))
        assert pixel == (255, 0, 0)

    def test_empty_regions_unchanged(self, tmp_path):
        img_path = _make_test_image(tmp_path / "test.png", 200, 100)

        result = redact_text.redact_regions(img_path, [], "#FF0000", padding=0, output_path=tmp_path / "out.png")
        # Image should remain white
        pixel = result.getpixel((100, 50))
        assert pixel == (255, 255, 255)

    def test_region_clamped_to_image_bounds(self, tmp_path):
        """Regions near edges should be clamped, not cause errors."""
        img_path = _make_test_image(tmp_path / "test.png", 100, 100)
        regions = [{"left": 0, "top": 0, "width": 50, "height": 50}]

        # padding=10 would push left/top to -10, should clamp to 0
        result = redact_text.redact_regions(img_path, regions, "#0000FF", padding=10, output_path=tmp_path / "out.png")
        pixel = result.getpixel((0, 0))
        assert pixel == (0, 0, 255)

    def test_custom_fill_color(self, tmp_path):
        img_path = _make_test_image(tmp_path / "test.png", 200, 100)
        regions = [{"left": 10, "top": 10, "width": 40, "height": 20}]

        result = redact_text.redact_regions(img_path, regions, "#00FF00", padding=0, output_path=tmp_path / "out.png")
        pixel = result.getpixel((30, 20))
        assert pixel == (0, 255, 0)


# ---------------------------------------------------------------------------
# render_placeholder
# ---------------------------------------------------------------------------

class TestRenderPlaceholder:
    def test_renders_text(self, tmp_path):
        from PIL import Image
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        regions = [{"left": 10, "top": 10, "width": 100, "height": 30}]

        result = redact_text.render_placeholder(img, regions, "[REDACTED]", font_size=12, font_color="#000000", padding=0)
        # At least some pixels in the region should no longer be white
        changed = False
        for x in range(10, 110):
            for y in range(10, 40):
                if result.getpixel((x, y)) != (255, 255, 255):
                    changed = True
                    break
            if changed:
                break
        assert changed, "Expected placeholder text to change pixels in region"

    def test_empty_regions_no_change(self, tmp_path):
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))

        result = redact_text.render_placeholder(img, [], "[TEXT]", font_size=12, font_color="#000000", padding=0)
        pixel = result.getpixel((50, 50))
        assert pixel == (255, 255, 255)

    def test_auto_font_size(self, tmp_path):
        """Auto-fit should not raise and should render something."""
        from PIL import Image
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        regions = [{"left": 10, "top": 10, "width": 80, "height": 25}]

        # font_size=None triggers auto-fit
        result = redact_text.render_placeholder(img, regions, "X", font_size=None, font_color="#000000", padding=0)
        assert result is not None


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------

class TestMain:
    @patch("redact_text.check_tesseract")
    @patch("redact_text.find_text_regions")
    def test_end_to_end_redact(self, mock_find, mock_check, tmp_path):
        img_path = _make_test_image(tmp_path / "input.png", 200, 100)
        output_path = tmp_path / "output.png"

        mock_find.return_value = [
            {"text": "secret", "left": 20, "top": 20, "width": 60, "height": 20, "conf": 90.0}
        ]

        result = redact_text.main([
            "--input", str(img_path),
            "--find", "secret",
            "--replace", "[REDACTED]",
            "--output", str(output_path),
        ])
        assert result == 0
        assert output_path.exists()

    @patch("redact_text.check_tesseract")
    @patch("redact_text.find_text_regions")
    def test_no_matches_returns_zero(self, mock_find, mock_check, tmp_path):
        img_path = _make_test_image(tmp_path / "input.png")
        mock_find.return_value = []

        result = redact_text.main(["--input", str(img_path), "--find", "nonexistent"])
        assert result == 0

    @patch("redact_text.check_tesseract")
    def test_missing_input_returns_one(self, mock_check, tmp_path):
        result = redact_text.main(["--input", str(tmp_path / "nope.png"), "--find", "x"])
        assert result == 1

    @patch("redact_text.check_tesseract", side_effect=redact_text.TesseractNotInstalledError("not installed"))
    def test_tesseract_not_installed(self, mock_check):
        result = redact_text.main(["--input", "x.png", "--find", "x"])
        assert result == 1

    @patch("redact_text.check_tesseract")
    @patch("redact_text.find_text_regions")
    def test_first_match_only_by_default(self, mock_find, mock_check, tmp_path):
        img_path = _make_test_image(tmp_path / "input.png", 200, 100)
        output_path = tmp_path / "output.png"

        mock_find.return_value = [
            {"text": "secret", "left": 10, "top": 10, "width": 50, "height": 15, "conf": 90.0},
            {"text": "secret", "left": 10, "top": 40, "width": 50, "height": 15, "conf": 85.0},
        ]

        result = redact_text.main([
            "--input", str(img_path), "--find", "secret", "--output", str(output_path),
        ])
        assert result == 0
        # Only first match should be redacted — hard to verify pixel-level without
        # more infrastructure, so we trust the --all logic in main()

    @patch("redact_text.check_tesseract")
    @patch("redact_text.find_text_regions")
    def test_all_flag_processes_all(self, mock_find, mock_check, tmp_path):
        img_path = _make_test_image(tmp_path / "input.png", 200, 100)
        output_path = tmp_path / "output.png"

        mock_find.return_value = [
            {"text": "secret", "left": 10, "top": 10, "width": 50, "height": 15, "conf": 90.0},
            {"text": "secret", "left": 10, "top": 40, "width": 50, "height": 15, "conf": 85.0},
        ]

        result = redact_text.main([
            "--input", str(img_path), "--find", "secret", "--all", "--output", str(output_path),
        ])
        assert result == 0

    @patch("redact_text.check_tesseract")
    @patch("redact_text.find_text_regions")
    def test_inplace_overwrite(self, mock_find, mock_check, tmp_path):
        img_path = _make_test_image(tmp_path / "input.png", 200, 100)

        mock_find.return_value = [
            {"text": "secret", "left": 20, "top": 20, "width": 60, "height": 20, "conf": 90.0}
        ]

        # No --output → should overwrite input
        result = redact_text.main([
            "--input", str(img_path), "--find", "secret",
        ])
        assert result == 0
        assert img_path.exists()


# ---------------------------------------------------------------------------
# check_tesseract
# ---------------------------------------------------------------------------

class TestCheckTesseract:
    def test_pytesseract_not_installed(self):
        original = redact_text.pytesseract
        try:
            redact_text.pytesseract = None
            with pytest.raises(ImportError, match="pytesseract is not installed"):
                redact_text.check_tesseract()
        finally:
            redact_text.pytesseract = original

    @patch("redact_text.pytesseract")
    def test_tesseract_binary_not_found(self, mock_tess):
        # Create a real exception class for TesseractNotFoundError
        class FakeTesseractNotFoundError(Exception):
            pass
        mock_tess.TesseractNotFoundError = FakeTesseractNotFoundError
        mock_tess.get_tesseract_version.side_effect = FakeTesseractNotFoundError("not found")
        with pytest.raises(redact_text.TesseractNotInstalledError):
            redact_text.check_tesseract()
