"""Renderer tests for remotion-animation.

Tests cover:
- Mock subprocess.run → returns success → output path returned
- Mock subprocess.run → returns failure → RenderError with stderr
- Remotion CLI not found → clear error with install instructions
- Temp file cleanup after render
- Output file doesn't exist after render → error
- Issue #91: UTF-8 encoding and version mismatch handling
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from remotion_gen.config import QualityPreset, QUALITY_PRESETS
from remotion_gen.errors import RenderError
from remotion_gen.renderer import check_prerequisites, render_video


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


# ---------------------------------------------------------------------------
# Issue #91: UTF-8 encoding and version mismatch handling
# ---------------------------------------------------------------------------


class TestRendererPrerequisites:
    """Test check_prerequisites()."""

    @patch("remotion_gen.renderer.shutil.which")
    def test_node_not_found(self, mock_which):
        mock_which.return_value = None
        ok, msg = check_prerequisites()
        assert ok is False
        assert "Node.js" in msg

    @patch("remotion_gen.renderer.shutil.which")
    def test_npm_not_found(self, mock_which):
        def _side(name):
            return "/usr/bin/node" if name == "node" else None
        mock_which.side_effect = _side
        ok, msg = check_prerequisites()
        assert ok is False
        assert "npm" in msg

    @patch("remotion_gen.renderer.shutil.which")
    def test_all_found(self, mock_which):
        mock_which.return_value = "/usr/bin/found"
        ok, msg = check_prerequisites()
        assert ok is True
        assert msg is None


class TestRendererUTF8Encoding:
    """Verify renderer handles UTF-8 output with special characters.

    Bug #91-related: Remotion subprocess may emit UTF-8 output containing
    special characters (emojis, accented text, Unicode symbols). The renderer
    must not crash when parsing this output.
    """

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_utf8_stdout_does_not_crash(self, mock_run, mock_which, tmp_path):
        """Renderer should tolerate UTF-8 characters in subprocess output."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"
        output.write_bytes(b"fake-mp4")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="✅ Render complete — «scene» rendered in 2.3s 🎬",
            stderr="",
        )

        quality = QUALITY_PRESETS["medium"]
        result = render_video(project_root, output, quality, duration_frames=150)
        assert result == output

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_utf8_stderr_does_not_crash(self, mock_run, mock_which, tmp_path):
        """Non-zero exit with UTF-8 stderr should produce readable RenderError."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="❌ Error: Composición no encontrada — «GeneratedScene» não existe",
        )

        quality = QUALITY_PRESETS["medium"]
        with pytest.raises(RenderError, match="Composición"):
            render_video(project_root, output, quality, duration_frames=150)

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_emoji_in_output_preserved(self, mock_run, mock_which, tmp_path):
        """Emoji characters in stdout should not cause encoding errors."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"
        output.write_bytes(b"fake-mp4")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="🎥 Rendering frame 1/300 ━━━━━━━━━━ 100%",
            stderr="⚠️ Warning: version mismatch detected",
        )

        quality = QUALITY_PRESETS["low"]
        result = render_video(project_root, output, quality, duration_frames=300)
        assert result == output


class TestRendererVersionMismatchWarnings:
    """Verify that version mismatch warnings don't cause failures.

    Bug #91-related: npm/Remotion may emit version warnings on stderr even
    when rendering succeeds (returncode=0). These must not be treated as errors.
    """

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_warning_on_stderr_with_success_does_not_fail(
        self, mock_run, mock_which, tmp_path
    ):
        """returncode=0 + warnings on stderr → success, not failure."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"
        output.write_bytes(b"fake-mp4")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Render complete",
            stderr=(
                "npm WARN deprecated @remotion/renderer@3.3.89: "
                "Upgrade to @remotion/renderer@4.x for best results\n"
                "WARN: Node.js version 18.x detected, recommended 20.x"
            ),
        )

        quality = QUALITY_PRESETS["high"]
        result = render_video(project_root, output, quality, duration_frames=60)
        assert result == output

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_actual_error_with_nonzero_exit_still_fails(
        self, mock_run, mock_which, tmp_path
    ):
        """returncode=1 should still raise RenderError regardless of warnings."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Could not find composition 'GeneratedScene'",
        )

        quality = QUALITY_PRESETS["medium"]
        with pytest.raises(RenderError, match="GeneratedScene"):
            render_video(project_root, output, quality, duration_frames=150)

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_output_missing_after_success_raises_error(
        self, mock_run, mock_which, tmp_path
    ):
        """Subprocess succeeds but output file missing → RenderError."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"
        # Deliberately don't create the output file

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Render complete",
            stderr="",
        )

        quality = QUALITY_PRESETS["medium"]
        with pytest.raises(RenderError, match="output not found"):
            render_video(project_root, output, quality, duration_frames=150)


class TestRendererCommandConstruction:
    """Verify the subprocess command includes correct --props for issue #93."""

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_props_include_duration_frames(self, mock_run, mock_which, tmp_path):
        """Command must pass --props with durationInFrames."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"
        output.write_bytes(b"fake-mp4")

        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr=""
        )

        quality = QUALITY_PRESETS["medium"]
        render_video(project_root, output, quality, duration_frames=300)

        cmd = mock_run.call_args[0][0]
        props_args = [arg for arg in cmd if arg.startswith("--props")]
        assert len(props_args) == 1
        assert "300" in props_args[0]

    @patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
    @patch("remotion_gen.renderer.subprocess.run")
    def test_quality_dimensions_in_command(self, mock_run, mock_which, tmp_path):
        """Command should include --width, --height, --fps from quality preset."""
        project_root = tmp_path / "remotion-project"
        project_root.mkdir()
        (project_root / "node_modules").mkdir()
        output = tmp_path / "output.mp4"
        output.write_bytes(b"fake-mp4")

        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr=""
        )

        quality = QUALITY_PRESETS["high"]
        render_video(project_root, output, quality, duration_frames=60)

        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "--width=1920" in cmd_str
        assert "--height=1080" in cmd_str
        assert "--fps=60" in cmd_str
