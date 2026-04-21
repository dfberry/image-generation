"""Integration tests for manim-animation.

End-to-end pipeline tests: mock LLM → real scene build → mock render → verify pipeline.

Mark with @pytest.mark.integration for easy skipping.
"""

import pytest
from unittest.mock import patch


@pytest.mark.integration
class TestEndToEndPipeline:
    """Integration tests for full animation generation pipeline."""

    @patch("subprocess.run")
    @patch("openai.ChatCompletion.create")
    def test_full_pipeline_valid_prompt(
        self,
        mock_llm,
        mock_subprocess,
        mock_openai_response,
        mock_subprocess_success,
        tmp_output_dir,
    ):
        """End-to-end: prompt → LLM → scene code → render → MP4 output."""
        mock_llm.return_value = mock_openai_response
        mock_subprocess.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's full pipeline implementation")

    @patch("subprocess.run")
    @patch("openai.ChatCompletion.create")
    def test_pipeline_handles_llm_error_gracefully(
        self, mock_llm, mock_subprocess, tmp_output_dir
    ):
        """Pipeline should handle LLM error gracefully with clear message."""
        mock_llm.side_effect = Exception("API error")
        pytest.skip("Waiting for Trinity's full pipeline implementation")

    @patch("subprocess.run")
    @patch("openai.ChatCompletion.create")
    def test_pipeline_handles_render_error_gracefully(
        self,
        mock_llm,
        mock_subprocess,
        mock_openai_response,
        mock_subprocess_failure,
        tmp_output_dir,
    ):
        """Pipeline should handle render error gracefully with stderr."""
        mock_llm.return_value = mock_openai_response
        mock_subprocess.side_effect = mock_subprocess_failure
        pytest.skip("Waiting for Trinity's full pipeline implementation")

    @patch("subprocess.run")
    @patch("openai.ChatCompletion.create")
    def test_pipeline_validates_scene_code_before_render(
        self, mock_llm, mock_subprocess, tmp_output_dir
    ):
        """Pipeline should validate scene code before attempting render."""
        # LLM returns code with dangerous imports
        dangerous_response = MagicMock()
        dangerous_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""```python
import os
from manim import *

class DangerousScene(Scene):
    def construct(self):
        os.system("echo bad")
```"""
                )
            )
        ]
        mock_llm.return_value = dangerous_response
        pytest.skip("Waiting for Trinity's full pipeline implementation")

    @patch("subprocess.run")
    @patch("openai.ChatCompletion.create")
    def test_pipeline_creates_output_in_correct_directory(
        self,
        mock_llm,
        mock_subprocess,
        mock_openai_response,
        mock_subprocess_success,
        tmp_output_dir,
    ):
        """Pipeline should create output file in specified directory."""
        mock_llm.return_value = mock_openai_response
        mock_subprocess.side_effect = mock_subprocess_success
        pytest.skip("Waiting for Trinity's full pipeline implementation")
