"""Integration tests for remotion-animation.

End-to-end pipeline tests: mock LLM at module boundary →
component build → mock render → verify pipeline.

Mark with @pytest.mark.integration for easy skipping.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from remotion_gen.cli import generate_video
from remotion_gen.errors import LLMError, RenderError, ValidationError


@pytest.mark.integration
class TestEndToEndPipeline:
    """Integration tests for full animation generation pipeline."""

    def test_full_pipeline_valid_prompt(self, tmp_output_dir):
        """End-to-end: prompt → LLM → component code → render → MP4 output."""
        output_file = str(tmp_output_dir / "output.mp4")
        with patch("remotion_gen.cli.generate_component", return_value="fake tsx") as mock_gen, \
             patch("remotion_gen.cli.write_component") as mock_write, \
             patch("remotion_gen.cli.render_video", return_value=Path(output_file)) as mock_render:
            result = generate_video(
                prompt="A blue circle spinning", output=output_file
            )
        assert result == Path(output_file)
        mock_gen.assert_called_once()
        assert mock_gen.call_args[0][0] == "A blue circle spinning"
        mock_write.assert_called_once()
        mock_render.assert_called_once()

    def test_pipeline_handles_llm_error_gracefully(self, tmp_output_dir):
        """Pipeline should handle LLM error gracefully with clear message."""
        output_file = str(tmp_output_dir / "output.mp4")
        with patch(
            "remotion_gen.cli.generate_component",
            side_effect=LLMError("API error"),
        ):
            with pytest.raises(LLMError, match="API error"):
                generate_video(prompt="test", output=output_file)

    def test_pipeline_handles_render_error_gracefully(self, tmp_output_dir):
        """Pipeline should handle render error gracefully with stderr."""
        output_file = str(tmp_output_dir / "output.mp4")
        with patch("remotion_gen.cli.generate_component", return_value="fake tsx"), \
             patch("remotion_gen.cli.write_component"), \
             patch("remotion_gen.cli.render_video", side_effect=RenderError("Component not found")):
            with pytest.raises(RenderError, match="Component not found"):
                generate_video(prompt="test", output=output_file)

    def test_pipeline_validates_component_code_before_render(
        self, tmp_output_dir
    ):
        """Pipeline should validate component code before attempting render."""
        output_file = str(tmp_output_dir / "output.mp4")
        with patch("remotion_gen.cli.generate_component", return_value="import fs from 'fs';"), \
             patch("remotion_gen.cli.write_component", side_effect=ValidationError("Dangerous import detected")), \
             patch("remotion_gen.cli.render_video") as mock_render:
            with pytest.raises(ValidationError, match="Dangerous import"):
                generate_video(prompt="test", output=output_file)
            # render_video should NOT have been called since validation failed
            mock_render.assert_not_called()

    def test_pipeline_creates_output_in_correct_directory(
        self, tmp_output_dir
    ):
        """Pipeline should create output file in specified directory."""
        output_file = str(tmp_output_dir / "my_video.mp4")
        expected_path = Path(output_file).resolve()
        with patch("remotion_gen.cli.generate_component", return_value="fake tsx"), \
             patch("remotion_gen.cli.write_component"), \
             patch("remotion_gen.cli.render_video", return_value=expected_path) as mock_render:
            result = generate_video(prompt="test", output=output_file)
        assert result == expected_path
        # Verify render_video received the resolved output path
        render_args = mock_render.call_args[0]
        assert render_args[1] == expected_path

    def test_pipeline_writes_component_to_remotion_project(
        self, tmp_output_dir
    ):
        """Write component to remotion-project/src/."""
        output_file = str(tmp_output_dir / "out.mp4")
        fake_code = "fake tsx component"
        with patch("remotion_gen.cli.generate_component", return_value=fake_code), \
             patch("remotion_gen.cli.write_component") as mock_write, \
             patch("remotion_gen.cli.render_video", return_value=Path(output_file)):
            generate_video(prompt="test", output=output_file)
        mock_write.assert_called_once()
        write_args = mock_write.call_args[0]
        assert write_args[0] == fake_code
        assert write_args[1].name == "remotion-project"
