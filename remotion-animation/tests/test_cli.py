"""CLI argument parsing and validation tests for remotion-animation.

Tests cover:
- Valid prompt + output path → success
- Missing --prompt → error code 1
- Missing --output → argparse error (required argument)
- Invalid --quality value → argparse error
- --debug flag forwarded to generate_video
- --duration accepts positive integers in range (5-30), rejects negative/zero
- End-to-end CLI integration with mocked pipeline components
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from remotion_gen.cli import generate_video, main
from remotion_gen.errors import LLMError, RenderError


class TestCLIValidation:
    """Test CLI argument validation via main() with mocked generate_video."""

    def test_valid_prompt_and_output(self, tmp_output_dir):
        """Valid prompt and output path should succeed."""
        with patch(
            "remotion_gen.cli.generate_video", return_value=Path("out.mp4")
        ) as mock_gv:
            with patch(
                "sys.argv",
                ["remotion-gen", "--prompt", "A spinning cube", "--output", "out.mp4"],
            ):
                result = main()
        assert result == 0
        mock_gv.assert_called_once()
        assert mock_gv.call_args[1]["prompt"] == "A spinning cube"
        assert mock_gv.call_args[1]["output"] == "out.mp4"

    def test_missing_prompt_raises_error(self):
        """Missing --prompt argument should return error code 1."""
        with patch("sys.argv", ["remotion-gen", "--output", "out.mp4"]):
            result = main()
        assert result == 1

    def test_missing_output_causes_argparse_error(self):
        """Missing --output should cause argparse error (it is required)."""
        with patch("sys.argv", ["remotion-gen", "--prompt", "test"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    def test_invalid_quality_value_raises_error(self):
        """Invalid --quality value should cause argparse error.

        Valid values: low, medium, high.
        Invalid: "best", "ultra", 1080, etc.
        """
        with patch(
            "sys.argv",
            [
                "remotion-gen",
                "--prompt", "test",
                "--output", "out.mp4",
                "--quality", "ultra",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    def test_debug_flag_saves_intermediate_code(self):
        """--debug flag should be forwarded to generate_video."""
        with patch(
            "remotion_gen.cli.generate_video", return_value=Path("out.mp4")
        ) as mock_gv:
            with patch(
                "sys.argv",
                ["remotion-gen", "--prompt", "test", "--output", "out.mp4", "--debug"],
            ):
                result = main()
        assert result == 0
        assert mock_gv.call_args[1]["debug"] is True

    def test_duration_accepts_positive_integers(self):
        """--duration should accept positive integers within valid range (5-30)."""
        with patch(
            "remotion_gen.cli.generate_video", return_value=Path("out.mp4")
        ) as mock_gv:
            with patch(
                "sys.argv",
                [
                    "remotion-gen",
                    "--prompt", "test",
                    "--output", "out.mp4",
                    "--duration", "10",
                ],
            ):
                result = main()
        assert result == 0
        assert mock_gv.call_args[1]["duration"] == 10

    def test_duration_rejects_negative(self):
        """--duration should reject negative values (below minimum of 5)."""
        with patch(
            "sys.argv",
            [
                "remotion-gen",
                "--prompt", "test",
                "--output", "out.mp4",
                "--duration", "-5",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    def test_duration_rejects_zero(self):
        """--duration should reject zero (below minimum of 5)."""
        with patch(
            "sys.argv",
            [
                "remotion-gen",
                "--prompt", "test",
                "--output", "out.mp4",
                "--duration", "0",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2


class TestCLIIntegration:
    """Integration tests for CLI workflow using generate_video() directly."""

    @pytest.mark.integration
    def test_end_to_end_valid_prompt(self, tmp_output_dir):
        """End-to-end: valid prompt → LLM → component code → render → output."""
        output_file = str(tmp_output_dir / "out.mp4")
        with patch("remotion_gen.cli.generate_component", return_value="fake tsx") as mock_gen, \
             patch("remotion_gen.cli.write_component") as mock_write, \
             patch("remotion_gen.cli.render_video", return_value=Path(output_file)) as mock_render:
            result = generate_video(prompt="A spinning cube", output=output_file)
        assert result == Path(output_file)
        mock_gen.assert_called_once()
        mock_write.assert_called_once()
        mock_render.assert_called_once()

    @pytest.mark.integration
    def test_cli_handles_llm_failure_gracefully(self, tmp_output_dir):
        """CLI should handle LLM API failure with clear error message."""
        output_file = str(tmp_output_dir / "out.mp4")
        with patch(
            "remotion_gen.cli.generate_component",
            side_effect=LLMError("API key invalid"),
        ):
            with pytest.raises(LLMError, match="API key invalid"):
                generate_video(prompt="test", output=output_file)

    @pytest.mark.integration
    def test_cli_handles_render_failure_gracefully(self, tmp_output_dir):
        """CLI should handle Remotion render failure with clear error message."""
        output_file = str(tmp_output_dir / "out.mp4")
        with patch("remotion_gen.cli.generate_component", return_value="fake tsx"), \
             patch("remotion_gen.cli.write_component"), \
             patch("remotion_gen.cli.render_video", side_effect=RenderError("Render crashed")):
            with pytest.raises(RenderError, match="Render crashed"):
                generate_video(prompt="test", output=output_file)
