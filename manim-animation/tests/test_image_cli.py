"""CLI image argument tests for manim-animation.

Tests: --image, --image-descriptions, --image-policy CLI arg parsing.
Integration: generate_video wires images through to LLM client and renderer.
Exit codes: ImageValidationError → exit 5.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from manim_gen.cli import generate_video, main, parse_args
from manim_gen.config import QualityPreset
from manim_gen.errors import ImageValidationError

_FAKE_IMAGE = b"\x89PNG\r\n\x1a\nfake-cli-test-image"


# ===================================================================
# --image / --image-descriptions / --image-policy arg parsing
# ===================================================================


class TestImageCLIArgs:
    """CLI argument parsing for image-related flags."""

    def test_image_accepts_single_path(self):
        with patch.object(
            sys, "argv",
            ["manim-gen", "--prompt", "test", "--image", "photo.png"],
        ):
            args = parse_args()
            assert args.image == [Path("photo.png")]

    def test_image_accepts_multiple_paths(self):
        with patch.object(
            sys, "argv",
            ["manim-gen", "--prompt", "test", "--image", "a.png", "b.jpg"],
        ):
            args = parse_args()
            assert args.image == [Path("a.png"), Path("b.jpg")]

    def test_no_image_flag_defaults_to_none(self):
        with patch.object(sys, "argv", ["manim-gen", "--prompt", "test"]):
            args = parse_args()
            assert args.image is None

    def test_image_policy_defaults_to_strict(self):
        with patch.object(sys, "argv", ["manim-gen", "--prompt", "test"]):
            args = parse_args()
            assert args.image_policy == "strict"

    def test_image_policy_accepts_warn(self):
        with patch.object(
            sys, "argv",
            ["manim-gen", "--prompt", "test", "--image-policy", "warn"],
        ):
            args = parse_args()
            assert args.image_policy == "warn"

    def test_image_policy_accepts_ignore(self):
        with patch.object(
            sys, "argv",
            ["manim-gen", "--prompt", "test", "--image-policy", "ignore"],
        ):
            args = parse_args()
            assert args.image_policy == "ignore"

    def test_image_policy_rejects_invalid_value(self):
        with patch.object(
            sys, "argv",
            ["manim-gen", "--prompt", "test", "--image-policy", "yolo"],
        ):
            with pytest.raises(SystemExit):
                parse_args()

    def test_image_descriptions_parsed(self):
        with patch.object(
            sys, "argv",
            [
                "manim-gen", "--prompt", "test",
                "--image-descriptions", "Photo of a sunset",
            ],
        ):
            args = parse_args()
            assert args.image_descriptions == "Photo of a sunset"

    def test_image_descriptions_defaults_to_none(self):
        with patch.object(sys, "argv", ["manim-gen", "--prompt", "test"]):
            args = parse_args()
            assert args.image_descriptions is None


# ===================================================================
# generate_video integration — images wired to LLM + renderer
# ===================================================================


class TestGenerateVideoWithImages:
    """Integration: generate_video passes images through the full pipeline."""

    @patch("manim_gen.cli.render_scene")
    @patch("manim_gen.cli.LLMClient")
    def test_images_wired_to_llm_and_renderer(
        self, mock_llm_client, mock_render, tmp_path
    ):
        # Real image file for copy_images_to_workspace
        img = tmp_path / "photo.png"
        img.write_bytes(_FAKE_IMAGE)
        output = tmp_path / "output.mp4"

        # LLM returns code using the deterministic workspace filename
        mock_client = MagicMock()
        mock_client.generate_scene_code.return_value = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        img = ImageMobject('image_0_photo.png')\n"
            "        self.play(FadeIn(img))\n```"
        )
        mock_llm_client.return_value = mock_client
        mock_render.return_value = output

        result = generate_video(
            prompt="show the photo",
            output=output,
            quality=QualityPreset.MEDIUM,
            duration=10,
            provider="ollama",
            images=[img],
            image_descriptions="A photo of nature",
            image_policy="strict",
        )

        assert result == output

        # LLM received image context with the workspace filename + descriptions
        call_kwargs = mock_client.generate_scene_code.call_args.kwargs
        assert call_kwargs.get("image_context") is not None
        assert "image_0_photo.png" in call_kwargs["image_context"]
        assert "A photo of nature" in call_kwargs["image_context"]

        # Renderer received assets_dir (workspace with images)
        render_kwargs = mock_render.call_args.kwargs
        assert render_kwargs.get("assets_dir") is not None

    @patch("manim_gen.cli.render_scene")
    @patch("manim_gen.cli.LLMClient")
    def test_no_images_skips_image_pipeline(
        self, mock_llm_client, mock_render, tmp_path
    ):
        output = tmp_path / "output.mp4"

        mock_client = MagicMock()
        mock_client.generate_scene_code.return_value = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        self.play(Create(Circle()))\n```"
        )
        mock_llm_client.return_value = mock_client
        mock_render.return_value = output

        result = generate_video(
            prompt="draw a circle",
            output=output,
            quality=QualityPreset.MEDIUM,
            duration=10,
            provider="ollama",
        )

        assert result == output

        # LLM was NOT given image context
        call_kwargs = mock_client.generate_scene_code.call_args.kwargs
        assert call_kwargs.get("image_context") is None

        # Renderer was NOT given assets_dir
        render_kwargs = mock_render.call_args.kwargs
        assert render_kwargs.get("assets_dir") is None

    @patch("manim_gen.cli.render_scene")
    @patch("manim_gen.cli.LLMClient")
    def test_multiple_images_all_copied(
        self, mock_llm_client, mock_render, tmp_path
    ):
        img_a = tmp_path / "alpha.png"
        img_b = tmp_path / "beta.jpg"
        img_a.write_bytes(_FAKE_IMAGE)
        img_b.write_bytes(_FAKE_IMAGE)
        output = tmp_path / "output.mp4"

        mock_client = MagicMock()
        mock_client.generate_scene_code.return_value = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        a = ImageMobject('image_0_alpha.png')\n"
            "        b = ImageMobject('image_1_beta.jpg')\n"
            "        self.play(FadeIn(a), FadeIn(b))\n```"
        )
        mock_llm_client.return_value = mock_client
        mock_render.return_value = output

        result = generate_video(
            prompt="show both photos",
            output=output,
            quality=QualityPreset.MEDIUM,
            duration=10,
            provider="ollama",
            images=[img_a, img_b],
            image_policy="strict",
        )

        assert result == output

        # LLM context mentions both filenames
        ctx = mock_client.generate_scene_code.call_args.kwargs["image_context"]
        assert "image_0_alpha.png" in ctx
        assert "image_1_beta.jpg" in ctx


# ===================================================================
# main() exit codes — image errors
# ===================================================================


class TestMainWithImageErrors:
    """Test main() returns exit code 5 on ImageValidationError."""

    @patch("manim_gen.cli.generate_video")
    @patch("manim_gen.cli.parse_args")
    def test_main_returns_5_on_image_validation_error(self, mock_args, mock_gen):
        mock_args.return_value = MagicMock(
            prompt="test", output=None, quality="medium",
            duration=10, provider="ollama", model=None, debug=False,
            image=None, image_descriptions=None, image_policy="strict",
        )
        mock_gen.side_effect = ImageValidationError("bad image format")
        assert main() == 5
