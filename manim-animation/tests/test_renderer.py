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

class TestRenderSceneQuality:

    def test_quality_presets_have_flags(self):
        assert QualityPreset.LOW.flag == "l"
        assert QualityPreset.MEDIUM.flag == "m"
        assert QualityPreset.HIGH.flag == "h"
