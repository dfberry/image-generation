"""CLI argument parsing and validation tests for manim-animation."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from manim_gen.cli import main, parse_args
from manim_gen.errors import LLMError, RenderError, ValidationError


class TestCLIValidation:

    def test_valid_prompt_parses(self):
        with patch.object(sys, "argv", ["manim-gen", "--prompt", "A blue circle"]):
            args = parse_args()
            assert args.prompt == "A blue circle"

    def test_missing_prompt_defaults_to_none(self):
        """Missing --prompt defaults to None (--demo or error handled in main())."""
        with patch.object(sys, "argv", ["manim-gen"]):
            args = parse_args()
            assert args.prompt is None

    def test_missing_output_uses_default(self):
        with patch.object(sys, "argv", ["manim-gen", "--prompt", "test"]):
            args = parse_args()
            assert args.output is None

    def test_invalid_quality_value_raises_error(self):
        with patch.object(
            sys, "argv", ["manim-gen", "--prompt", "test", "--quality", "ultra"]
        ):
            with pytest.raises(SystemExit):
                parse_args()

    def test_debug_flag_parsed(self):
        with patch.object(sys, "argv", ["manim-gen", "--prompt", "test", "--debug"]):
            args = parse_args()
            assert args.debug is True

    def test_duration_accepts_positive_integers(self):
        with patch.object(
            sys, "argv", ["manim-gen", "--prompt", "test", "--duration", "15"]
        ):
            args = parse_args()
            assert args.duration == 15

    def test_provider_defaults_to_ollama(self):
        with patch.object(sys, "argv", ["manim-gen", "--prompt", "test"]):
            args = parse_args()
            assert args.provider == "ollama"

    def test_quality_defaults_to_medium(self):
        with patch.object(sys, "argv", ["manim-gen", "--prompt", "test"]):
            args = parse_args()
            assert args.quality == "medium"

class TestMainFunction:

    @patch("manim_gen.cli.generate_video")
    @patch("manim_gen.cli.parse_args")
    def test_main_returns_1_on_llm_error(self, mock_args, mock_gen, capsys):
        mock_args.return_value = MagicMock(
            prompt="test", output=None, quality="medium",
            duration=10, provider="ollama", model=None, debug=False,
            demo=False,
        )
        mock_gen.side_effect = LLMError("API failed")
        assert main() == 1
        captured = capsys.readouterr()
        assert "LLM Error" in captured.err
        assert "API failed" in captured.err

    @patch("manim_gen.cli.generate_video")
    @patch("manim_gen.cli.parse_args")
    def test_main_returns_2_on_validation_error(self, mock_args, mock_gen, capsys):
        mock_args.return_value = MagicMock(
            prompt="test", output=None, quality="medium",
            duration=10, provider="ollama", model=None, debug=False,
            demo=False,
        )
        mock_gen.side_effect = ValidationError("bad code")
        assert main() == 2
        captured = capsys.readouterr()
        assert "Validation Error" in captured.err
        assert "bad code" in captured.err

    @patch("manim_gen.cli.generate_video")
    @patch("manim_gen.cli.parse_args")
    def test_main_returns_3_on_render_error(self, mock_args, mock_gen, capsys):
        mock_args.return_value = MagicMock(
            prompt="test", output=None, quality="medium",
            duration=10, provider="ollama", model=None, debug=False,
            demo=False,
        )
        mock_gen.side_effect = RenderError("render failed")
        assert main() == 3
        captured = capsys.readouterr()
        assert "Render Error" in captured.err
        assert "render failed" in captured.err
