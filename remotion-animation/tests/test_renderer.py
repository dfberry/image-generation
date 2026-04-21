"""Renderer tests for remotion-animation.

Tests cover:
- Mock subprocess.run → returns success → output path returned
- Mock subprocess.run → returns failure → RenderError with stderr
- Remotion CLI not found → clear error with install instructions
- Temp file cleanup after render
- Output file doesn't exist after render → error
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from remotion_gen.config import QUALITY_PRESETS
from remotion_gen.renderer import render_video


class TestRendererSuccess:
    """Test successful Remotion rendering scenarios."""

    @patch("subprocess.run")
    def test_successful_render_returns_output_path(
        self, mock_run, mock_subprocess_success, tmp_output_dir
    ):
        """Successful Remotion render should return output path."""
        mock_run.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's renderer.py implementation")

    @patch("subprocess.run")
    def test_creates_output_file(
        self, mock_run, mock_subprocess_success, tmp_output_dir
    ):
        """Successful render should create MP4 file at output path."""
        mock_run.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's renderer.py implementation")

    @patch("subprocess.run")
    def test_calls_remotion_with_correct_args(
        self, mock_run, mock_subprocess_success, tmp_output_dir
    ):
        """Should call npx remotion render with correct arguments."""
        mock_run.side_effect = mock_subprocess_success
        # Expected: npx remotion render src/index.ts
        # GeneratedScene output.mp4
        pytest.skip("Waiting for Trinity's renderer.py implementation")


class TestRendererFailure:
    """Test Remotion rendering failure scenarios."""

    @patch("subprocess.run")
    def test_render_failure_raises_error_with_stderr(
        self, mock_run, mock_subprocess_failure
    ):
        """Failed render should raise RenderError with stderr message."""
        mock_run.side_effect = mock_subprocess_failure
        pytest.skip("Waiting for Trinity's renderer.py implementation")

    @patch("subprocess.run")
    def test_remotion_not_found_raises_clear_error(
        self, mock_run, mock_subprocess_remotion_not_found
    ):
        """Remotion CLI not found should raise error with install instructions."""
        mock_run.side_effect = mock_subprocess_remotion_not_found
        pytest.skip("Waiting for Trinity's renderer.py implementation")

    @patch("subprocess.run")
    def test_output_file_missing_after_success_raises_error(self, mock_run):
        """Subprocess succeeds but output file missing should raise error."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        # But don't create the output file
        pytest.skip("Waiting for Trinity's renderer.py implementation")


class TestRendererFileWriting:
    """Test writing component code to remotion-project/src/."""

    @patch("subprocess.run")
    def test_writes_component_to_generated_scene_tsx(
        self, mock_run, mock_subprocess_success, tmp_project_dir
    ):
        """Should write component code to src/GeneratedScene.tsx."""
        mock_run.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's renderer.py implementation")

    @patch("subprocess.run")
    def test_overwrites_existing_generated_scene_tsx(
        self, mock_run, mock_subprocess_success, tmp_project_dir
    ):
        """Should overwrite existing src/GeneratedScene.tsx on each render."""
        mock_run.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's renderer.py implementation")

    @patch("subprocess.run")
    def test_debug_mode_preserves_component_file(
        self, mock_run, mock_subprocess_success, tmp_project_dir
    ):
        """Debug mode should preserve component file for inspection."""
        mock_run.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's renderer.py implementation")


class TestRendererQuality:
    """Test quality preset handling."""

    @patch("subprocess.run")
    def test_low_quality_uses_480p(self, mock_run, mock_subprocess_success):
        """Quality 'low' should render at 480p."""
        mock_run.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's renderer.py implementation")

    @patch("subprocess.run")
    def test_medium_quality_uses_720p(self, mock_run, mock_subprocess_success):
        """Quality 'medium' should render at 720p."""
        mock_run.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's renderer.py implementation")

    @patch("subprocess.run")
    def test_high_quality_uses_1080p(self, mock_run, mock_subprocess_success):
        """Quality 'high' should render at 1080p."""
        mock_run.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's renderer.py implementation")


class TestRendererInputProps:
    """Issue #93: renderer passes all composition props via --props JSON."""

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_props_json_includes_all_composition_values(self, mock_run, mock_which, tmp_path):
        """--props JSON must include durationInFrames, fps, width, height."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"
        output.write_bytes(b"fake-mp4")

        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr=""
        )

        quality = QUALITY_PRESETS["medium"]  # 1280x720, 30fps
        render_video(project_root, output, quality, duration_frames=200)

        cmd = mock_run.call_args[0][0]
        props_arg = [arg for arg in cmd if arg.startswith("--props")][0]
        props_json = props_arg.split("=", 1)[1]
        props = json.loads(props_json)

        assert props["durationInFrames"] == 200
        assert props["fps"] == 30
        assert props["width"] == 1280
        assert props["height"] == 720

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_props_json_varies_with_quality(self, mock_run, mock_which, tmp_path):
        """Different quality presets produce different props values."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"
        output.write_bytes(b"fake-mp4")

        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr=""
        )

        quality = QUALITY_PRESETS["high"]  # 1920x1080, 60fps
        render_video(project_root, output, quality, duration_frames=90)

        cmd = mock_run.call_args[0][0]
        props_arg = [arg for arg in cmd if arg.startswith("--props")][0]
        props = json.loads(props_arg.split("=", 1)[1])

        assert props["durationInFrames"] == 90
        assert props["fps"] == 60
        assert props["width"] == 1920
        assert props["height"] == 1080
