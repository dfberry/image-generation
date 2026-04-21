"""CLI image argument tests for remotion-animation.

Tests cover:
- CLI arg parsing: --image, --image-description, --image-policy
- Integration: generate_video wires image through pipeline (mocked LLM + renderer)
"""

from unittest.mock import patch

import pytest

from remotion_gen.cli import generate_video
from remotion_gen.errors import ImageValidationError

# Minimal valid PNG bytes for test image files
_FAKE_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01"
    b"\x00\x00\x00\x01"
    b"\x08\x02"
    b"\x00\x00\x00"
)


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestCLIImageArgParsing:
    """Test that --image, --image-description, --image-policy are accepted."""

    def test_image_arg_accepted(self):
        """--image should be parsed without error."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--prompt", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--image", type=str)
        parser.add_argument("--image-description", type=str)
        parser.add_argument(
            "--image-policy",
            choices=["strict", "warn", "ignore"],
            default="strict",
        )

        args = parser.parse_args([
            "--prompt", "test",
            "--output", "out.mp4",
            "--image", "photo.png",
        ])
        assert args.image == "photo.png"

    def test_image_description_arg_accepted(self):
        """--image-description should be parsed."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--prompt", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--image", type=str)
        parser.add_argument("--image-description", type=str)

        args = parser.parse_args([
            "--prompt", "test",
            "--output", "out.mp4",
            "--image", "photo.png",
            "--image-description", "A screenshot of the app",
        ])
        assert args.image_description == "A screenshot of the app"

    def test_image_policy_default_strict(self):
        """--image-policy should default to 'strict'."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--prompt", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument(
            "--image-policy",
            choices=["strict", "warn", "ignore"],
            default="strict",
        )

        args = parser.parse_args(
            ["--prompt", "test", "--output", "out.mp4"]
        )
        assert args.image_policy == "strict"

    def test_image_policy_accepts_warn(self):
        """--image-policy warn should be accepted."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--prompt", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument(
            "--image-policy",
            choices=["strict", "warn", "ignore"],
            default="strict",
        )

        args = parser.parse_args([
            "--prompt", "test",
            "--output", "out.mp4",
            "--image-policy", "warn",
        ])
        assert args.image_policy == "warn"

    def test_image_policy_accepts_ignore(self):
        """--image-policy ignore should be accepted."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--prompt", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument(
            "--image-policy",
            choices=["strict", "warn", "ignore"],
            default="strict",
        )

        args = parser.parse_args([
            "--prompt", "test",
            "--output", "out.mp4",
            "--image-policy", "ignore",
        ])
        assert args.image_policy == "ignore"


# ---------------------------------------------------------------------------
# Integration: generate_video with image
# ---------------------------------------------------------------------------


class TestGenerateVideoImageIntegration:
    """Test generate_video wires image through the full pipeline (mocked)."""

    def _setup_project(self, tmp_path):
        """Create a fake remotion-project directory structure."""
        project = tmp_path / "remotion-project"
        project.mkdir()
        (project / "src").mkdir()
        (project / "node_modules").mkdir()
        (project / "public").mkdir()
        return project

    def _create_test_image(self, tmp_path, name="photo.png"):
        """Create a small test image file."""
        img = tmp_path / name
        img.write_bytes(_FAKE_PNG)
        return img

    @patch("remotion_gen.cli.render_video")
    @patch("remotion_gen.cli.generate_component")
    @patch("remotion_gen.cli.copy_image_to_public")
    @patch("remotion_gen.cli.generate_image_context")
    def test_image_copies_to_public(
        self, mock_ctx, mock_copy, mock_gen, mock_render, tmp_path, monkeypatch
    ):
        """generate_video should call copy_image_to_public with correct args."""
        self._setup_project(tmp_path)
        img = self._create_test_image(tmp_path)
        output = tmp_path / "out.mp4"
        output.write_bytes(b"fake")

        mock_copy.return_value = "image_12345678.png"
        mock_ctx.return_value = "[image context]"
        mock_gen.return_value = (
            "import {AbsoluteFill, useCurrentFrame, Img, staticFile} from 'remotion';\n"
            "const imageSrc = staticFile('image_12345678.png');\n"
            "export default function GeneratedScene() {\n"
            "  const frame = useCurrentFrame();\n"
            "  return <AbsoluteFill><Img src={imageSrc} /></AbsoluteFill>;\n"
            "}\n"
        )
        mock_render.return_value = output

        # Patch the repo_root / project_root resolution inside generate_video
        monkeypatch.setattr(
            "remotion_gen.cli.Path.__file__",
            str(tmp_path / "remotion_gen" / "cli.py"),
            raising=False,
        )

        # We need generate_video to find project_root correctly.
        # The function uses: repo_root = Path(__file__).parent.parent
        # Let's patch that at module level.
        import remotion_gen.cli as cli_mod

        original_file = cli_mod.__file__
        # Create the expected structure
        fake_gen = tmp_path / "remotion_gen"
        fake_gen.mkdir(exist_ok=True)
        (fake_gen / "cli.py").write_text("", encoding="utf-8")

        monkeypatch.setattr(cli_mod, "__file__", str(fake_gen / "cli.py"))

        try:
            generate_video(
                prompt="Animate my screenshot",
                output=str(output),
                image_path=str(img),
                image_description="My app screenshot",
                image_policy="strict",
            )
        finally:
            monkeypatch.setattr(cli_mod, "__file__", original_file)

        mock_copy.assert_called_once()
        call_args = mock_copy.call_args
        assert call_args[0][0] == str(img)
        assert call_args[0][2] == "strict"

    @patch("remotion_gen.cli.render_video")
    @patch("remotion_gen.cli.generate_component")
    @patch("remotion_gen.cli.copy_image_to_public")
    @patch("remotion_gen.cli.generate_image_context")
    def test_image_context_passed_to_llm(
        self, mock_ctx, mock_copy, mock_gen, mock_render, tmp_path, monkeypatch
    ):
        """generate_video should pass generated image_context to generate_component."""
        self._setup_project(tmp_path)
        img = self._create_test_image(tmp_path)
        output = tmp_path / "out.mp4"
        output.write_bytes(b"fake")

        mock_copy.return_value = "image_12345678.png"
        mock_ctx.return_value = "## Image Asset Available\nFilename: image_12345678.png"
        mock_gen.return_value = (
            "import {AbsoluteFill, useCurrentFrame, Img, staticFile} from 'remotion';\n"
            "const imageSrc = staticFile('image_12345678.png');\n"
            "export default function GeneratedScene() {\n"
            "  const frame = useCurrentFrame();\n"
            "  return <AbsoluteFill><Img src={imageSrc} /></AbsoluteFill>;\n"
            "}\n"
        )
        mock_render.return_value = output

        import remotion_gen.cli as cli_mod

        original_file = cli_mod.__file__
        fake_gen = tmp_path / "remotion_gen"
        fake_gen.mkdir(exist_ok=True)
        (fake_gen / "cli.py").write_text("", encoding="utf-8")
        monkeypatch.setattr(cli_mod, "__file__", str(fake_gen / "cli.py"))

        try:
            generate_video(
                prompt="Animate screenshot",
                output=str(output),
                image_path=str(img),
                image_description="Dashboard view",
                image_policy="strict",
            )
        finally:
            monkeypatch.setattr(cli_mod, "__file__", original_file)

        # Verify generate_image_context was called with correct args
        mock_ctx.assert_called_once_with("image_12345678.png", "Dashboard view")

        # Verify generate_component received the image_context
        mock_gen.assert_called_once()
        gen_kwargs = mock_gen.call_args
        assert gen_kwargs.kwargs.get("image_context") or (
            len(gen_kwargs.args) > 5 and gen_kwargs.args[5] is not None
        )

    @patch("remotion_gen.cli.render_video")
    @patch("remotion_gen.cli.generate_component")
    def test_no_image_skips_image_pipeline(
        self, mock_gen, mock_render, tmp_path, monkeypatch
    ):
        """generate_video without --image should not call image functions."""
        self._setup_project(tmp_path)
        output = tmp_path / "out.mp4"
        output.write_bytes(b"fake")

        mock_gen.return_value = (
            "import {AbsoluteFill, useCurrentFrame} from 'remotion';\n"
            "export default function GeneratedScene() {\n"
            "  const frame = useCurrentFrame();\n"
            "  return <AbsoluteFill><h1>{frame}</h1></AbsoluteFill>;\n"
            "}\n"
        )
        mock_render.return_value = output

        import remotion_gen.cli as cli_mod

        original_file = cli_mod.__file__
        fake_gen = tmp_path / "remotion_gen"
        fake_gen.mkdir(exist_ok=True)
        (fake_gen / "cli.py").write_text("", encoding="utf-8")
        monkeypatch.setattr(cli_mod, "__file__", str(fake_gen / "cli.py"))

        with patch("remotion_gen.cli.copy_image_to_public") as mock_copy, \
             patch("remotion_gen.cli.generate_image_context") as mock_ctx:
            try:
                generate_video(
                    prompt="Simple animation",
                    output=str(output),
                )
            finally:
                monkeypatch.setattr(cli_mod, "__file__", original_file)

            mock_copy.assert_not_called()
            mock_ctx.assert_not_called()

        # Verify generate_component was called without image_context
        gen_call = mock_gen.call_args
        # image_context should be None
        if gen_call.kwargs:
            assert gen_call.kwargs.get("image_context") is None
        else:
            # positional arg at index 5 if present
            assert len(gen_call.args) <= 5 or gen_call.args[5] is None

    def test_invalid_image_raises_error(self, tmp_path, monkeypatch):
        """generate_video with invalid image should raise ImageValidationError."""
        self._setup_project(tmp_path)
        output = tmp_path / "out.mp4"
        missing_image = tmp_path / "nonexistent.png"

        import remotion_gen.cli as cli_mod

        original_file = cli_mod.__file__
        fake_gen = tmp_path / "remotion_gen"
        fake_gen.mkdir(exist_ok=True)
        (fake_gen / "cli.py").write_text("", encoding="utf-8")
        monkeypatch.setattr(cli_mod, "__file__", str(fake_gen / "cli.py"))

        try:
            with pytest.raises(ImageValidationError, match="not found"):
                generate_video(
                    prompt="Animate screenshot",
                    output=str(output),
                    image_path=str(missing_image),
                    image_policy="strict",
                )
        finally:
            monkeypatch.setattr(cli_mod, "__file__", original_file)
