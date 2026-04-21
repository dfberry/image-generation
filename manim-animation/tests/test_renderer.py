"""Renderer tests for manim-animation."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from manim_gen.config import QualityPreset
from manim_gen.errors import RenderError
from manim_gen.renderer import check_manim_installed, render_scene


class TestCheckManimInstalled:

    @patch("manim_gen.renderer.shutil.which", return_value="/usr/bin/manim")
    def test_manim_found(self, mock_which):
        assert check_manim_installed() is True

    @patch("manim_gen.renderer.shutil.which", return_value=None)
    def test_manim_not_found(self, mock_which):
        assert check_manim_installed() is False

class TestRenderScene:

    @patch("manim_gen.renderer.check_manim_installed", return_value=False)
    def test_manim_not_installed_raises_error(self, mock_check, tmp_path):
        scene_file = tmp_path / "scene.py"
        scene_file.write_text("pass")
        output = tmp_path / "output.mp4"
        with pytest.raises(RenderError, match="manim CLI not found"):
            render_scene(scene_file, output)

    @patch("manim_gen.renderer.shutil.move")
    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_successful_render(self, mock_check, mock_run, mock_move, tmp_path):
        scene_file = tmp_path / "scene.py"
        scene_file.write_text("pass")
        output = tmp_path / "output.mp4"

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        expected_dir = scene_file.parent / "media" / "videos" / "scene" / "720p30"
        expected_dir.mkdir(parents=True)
        expected_file = expected_dir / "GeneratedScene.mp4"
        expected_file.write_bytes(b"fake-mp4")

        result = render_scene(scene_file, output, QualityPreset.MEDIUM)
        assert result == output

    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_render_failure_raises_error(self, mock_check, mock_run, tmp_path):
        scene_file = tmp_path / "scene.py"
        scene_file.write_text("pass")
        output = tmp_path / "output.mp4"

        mock_run.side_effect = subprocess.CalledProcessError(
            1, "manim", stderr="Error: bad code"
        )
        with pytest.raises(RenderError, match="Manim render failed"):
            render_scene(scene_file, output)

class TestRenderSceneMediaDir:
    """Issue #90: media directory detection uses correct base when assets_dir is provided."""

    @patch("manim_gen.renderer.shutil.move")
    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_assets_dir_media_path(self, mock_check, mock_run, mock_move, tmp_path):
        """When assets_dir is provided, media output is relative to assets_dir, not scene_file.parent."""
        scene_dir = tmp_path / "scenes"
        scene_dir.mkdir()
        scene_file = scene_dir / "scene.py"
        scene_file.write_text("pass")

        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()

        output = tmp_path / "output.mp4"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Manim outputs media relative to cwd (assets_dir), NOT scene_file.parent
        media_dir = assets_dir / "media" / "videos" / "scene" / "720p30"
        media_dir.mkdir(parents=True)
        (media_dir / "GeneratedScene.mp4").write_bytes(b"fake-mp4")

        result = render_scene(scene_file, output, QualityPreset.MEDIUM, assets_dir=assets_dir)
        assert result == output
        mock_move.assert_called_once()

    @patch("manim_gen.renderer.shutil.move")
    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_no_assets_dir_uses_scene_parent(self, mock_check, mock_run, mock_move, tmp_path):
        """Without assets_dir, media output is relative to scene_file.parent (default cwd behavior)."""
        scene_file = tmp_path / "scene.py"
        scene_file.write_text("pass")
        output = tmp_path / "output.mp4"

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        media_dir = tmp_path / "media" / "videos" / "scene" / "720p30"
        media_dir.mkdir(parents=True)
        (media_dir / "GeneratedScene.mp4").write_bytes(b"fake-mp4")

        result = render_scene(scene_file, output, QualityPreset.MEDIUM)
        assert result == output

    @patch("manim_gen.renderer.shutil.move")
    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_fallback_rglob_with_assets_dir(self, mock_check, mock_run, mock_move, tmp_path):
        """Fallback rglob search also uses assets_dir as base."""
        scene_file = tmp_path / "scene.py"
        scene_file.write_text("pass")

        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()

        output = tmp_path / "output.mp4"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Put video in unexpected quality dir (triggers fallback)
        unexpected_dir = assets_dir / "media" / "videos" / "scene" / "1080p60"
        unexpected_dir.mkdir(parents=True)
        (unexpected_dir / "GeneratedScene.mp4").write_bytes(b"fake-mp4")

        result = render_scene(scene_file, output, QualityPreset.MEDIUM, assets_dir=assets_dir)
        assert result == output


class TestRenderSceneQuality:

    def test_quality_presets_have_flags(self):
        assert QualityPreset.LOW.flag == "l"
        assert QualityPreset.MEDIUM.flag == "m"
        assert QualityPreset.HIGH.flag == "h"


# ---------------------------------------------------------------------------
# Issue #90: Media directory detection
# ---------------------------------------------------------------------------


class TestMediaDirectoryDetection:
    """Verify render_scene locates output at the correct quality-specific path.

    Bug #90: renderer failed to find media output because it looked in the
    wrong subdirectory.  After the fix, the expected path is:
        media/videos/<scene_stem>/<quality_dir>/GeneratedScene.mp4
    """

    @pytest.mark.parametrize(
        "quality,quality_dir",
        [
            (QualityPreset.LOW, "480p15"),
            (QualityPreset.MEDIUM, "720p30"),
            (QualityPreset.HIGH, "1080p60"),
        ],
        ids=["low-480p15", "medium-720p30", "high-1080p60"],
    )
    @patch("manim_gen.renderer.shutil.move")
    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_finds_output_at_quality_specific_path(
        self, mock_check, mock_run, mock_move, tmp_path, quality, quality_dir
    ):
        """Renderer must look in media/videos/<stem>/<quality_dir>/."""
        scene_file = tmp_path / "my_scene.py"
        scene_file.write_text("pass")
        output = tmp_path / "final_output.mp4"

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        expected_dir = (
            scene_file.parent / "media" / "videos" / "my_scene" / quality_dir
        )
        expected_dir.mkdir(parents=True)
        expected_file = expected_dir / "GeneratedScene.mp4"
        expected_file.write_bytes(b"fake-mp4")

        result = render_scene(scene_file, output, quality)
        assert result == output
        mock_move.assert_called_once_with(str(expected_file), str(output))

    @patch("manim_gen.renderer.shutil.move")
    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_output_copied_to_outputs_directory(
        self, mock_check, mock_run, mock_move, tmp_path
    ):
        """Rendered video must be moved to the caller-specified output path."""
        scene_file = tmp_path / "scene.py"
        scene_file.write_text("pass")
        outputs_dir = tmp_path / "outputs"
        outputs_dir.mkdir()
        output = outputs_dir / "rendered.mp4"

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        media_file = (
            scene_file.parent
            / "media" / "videos" / "scene" / "720p30" / "GeneratedScene.mp4"
        )
        media_file.parent.mkdir(parents=True)
        media_file.write_bytes(b"fake-mp4")

        render_scene(scene_file, output, QualityPreset.MEDIUM)
        mock_move.assert_called_once_with(str(media_file), str(output))

    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_error_when_media_directory_missing(self, mock_check, mock_run, tmp_path):
        """Must raise RenderError when media directory is never created."""
        scene_file = tmp_path / "scene.py"
        scene_file.write_text("pass")
        output = tmp_path / "output.mp4"

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with pytest.raises(RenderError, match="media directory not created"):
            render_scene(scene_file, output)

    @patch("manim_gen.renderer.shutil.move")
    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_fallback_search_when_primary_path_missing(
        self, mock_check, mock_run, mock_move, tmp_path
    ):
        """Fallback rglob should find GeneratedScene.mp4 in an unexpected subdir."""
        scene_file = tmp_path / "scene.py"
        scene_file.write_text("pass")
        output = tmp_path / "output.mp4"

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        unexpected_dir = (
            scene_file.parent / "media" / "videos" / "scene" / "1080p60"
        )
        unexpected_dir.mkdir(parents=True)
        fallback_file = unexpected_dir / "GeneratedScene.mp4"
        fallback_file.write_bytes(b"fake-mp4")

        result = render_scene(scene_file, output, QualityPreset.MEDIUM)
        assert result == output

    @patch("manim_gen.renderer.subprocess.run")
    @patch("manim_gen.renderer.check_manim_installed", return_value=True)
    def test_error_when_media_exists_but_video_missing(
        self, mock_check, mock_run, tmp_path
    ):
        """media/ exists but contains no GeneratedScene.mp4 → RenderError."""
        scene_file = tmp_path / "scene.py"
        scene_file.write_text("pass")
        output = tmp_path / "output.mp4"

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        media_dir = scene_file.parent / "media" / "videos" / "scene" / "720p30"
        media_dir.mkdir(parents=True)

        with pytest.raises(RenderError, match="output video not found"):
            render_scene(scene_file, output)
