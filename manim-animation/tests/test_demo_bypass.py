"""Tests for --demo bypass feature (issue #100).

Tests cover:
- --demo flag is recognized by the argument parser
- --demo triggers demo template rendering (bypasses LLM)
- LLM is NOT called when --demo is used
- Demo scene contains "Dina Berry" text
- Demo scene contains a timestamp
- Scene elements don't stack (FadeOut/ReplacementTransform between elements)
"""

import re
import sys
from unittest.mock import MagicMock, patch

import pytest

from manim_gen.cli import main, parse_args


class TestDemoArgParsing:
    """Verify --demo flag is accepted by the argument parser."""

    def test_demo_flag_parsed(self):
        """--demo should be recognized without requiring --prompt."""
        with patch.object(sys, "argv", ["manim-gen", "--demo"]):
            args = parse_args()
            assert args.demo is True

    def test_demo_flag_defaults_to_false(self):
        """Without --demo, the flag should default to False."""
        with patch.object(sys, "argv", ["manim-gen", "--prompt", "test"]):
            args = parse_args()
            assert args.demo is False

    def test_demo_does_not_require_prompt(self):
        """--demo should work without --prompt (no error)."""
        with patch.object(sys, "argv", ["manim-gen", "--demo"]):
            args = parse_args()
            assert args.prompt is None
            assert args.demo is True

    def test_demo_with_prompt_ignores_prompt(self):
        """If both --demo and --prompt are given, --demo takes priority."""
        with patch.object(sys, "argv", ["manim-gen", "--demo", "--prompt", "ignored"]):
            args = parse_args()
            assert args.demo is True


class TestDemoBypassesLLM:
    """Verify that --demo mode never calls the LLM."""

    @patch("manim_gen.cli.generate_video")
    @patch("manim_gen.cli.parse_args")
    def test_demo_does_not_call_generate_video(self, mock_args, mock_gen):
        """--demo should bypass the normal generate_video pipeline."""
        mock_args.return_value = MagicMock(
            prompt=None, output=None, quality="medium",
            duration=10, provider="ollama", model=None,
            debug=False, demo=True,
        )
        main()
        mock_gen.assert_not_called()

    @patch("manim_gen.cli.render_demo_scene")
    @patch("manim_gen.cli.parse_args")
    def test_demo_calls_render_demo_scene(self, mock_args, mock_render):
        """--demo should call the dedicated demo renderer."""
        mock_args.return_value = MagicMock(
            prompt=None, output=None, quality="medium",
            duration=10, provider="ollama", model=None,
            debug=False, demo=True,
        )
        mock_render.return_value = "output.mp4"
        result = main()
        mock_render.assert_called_once()
        assert result == 0


class TestDemoSceneContent:
    """Verify the demo scene template has required content."""

    @pytest.fixture
    def demo_scene_code(self):
        """Get demo scene code from the template module."""
        from manim_gen.demo_template import get_demo_scene
        return get_demo_scene()

    def test_contains_dina_berry(self, demo_scene_code):
        """Demo scene must display 'Dina Berry'."""
        assert "Dina Berry" in demo_scene_code

    def test_contains_timestamp(self, demo_scene_code):
        """Demo scene must include a date/time reference."""
        # Look for common datetime patterns (e.g., 2026, AM/PM, or strftime-like)
        has_date_pattern = bool(
            re.search(r"\d{4}", demo_scene_code)  # year
            or "datetime" in demo_scene_code
            or "strftime" in demo_scene_code
            or "now()" in demo_scene_code
        )
        assert has_date_pattern, "Demo scene should contain a timestamp or datetime reference"

    def test_contains_generated_scene_class(self, demo_scene_code):
        """Demo scene must define a GeneratedScene class for Manim."""
        assert "class GeneratedScene" in demo_scene_code or "class DemoScene" in demo_scene_code

    def test_inherits_from_scene(self, demo_scene_code):
        """Demo scene class must inherit from Scene."""
        assert "(Scene)" in demo_scene_code

    def test_has_construct_method(self, demo_scene_code):
        """Demo scene must have a construct method."""
        assert "def construct(self)" in demo_scene_code


class TestDemoNoTextStacking:
    """Verify demo scene clears elements before showing new ones.

    Elements must not stack — each text/element should be removed
    (FadeOut, ReplacementTransform, or similar) before the next appears.
    """

    @pytest.fixture
    def demo_scene_code(self):
        """Get demo scene code from the template module."""
        from manim_gen.demo_template import get_demo_scene
        return get_demo_scene()

    def test_uses_fade_or_transform_between_elements(self, demo_scene_code):
        """Scene should use FadeOut, FadeIn, or ReplacementTransform."""
        has_transition = bool(
            "FadeOut" in demo_scene_code
            or "ReplacementTransform" in demo_scene_code
            or "Transform" in demo_scene_code
            or "FadeIn" in demo_scene_code
        )
        assert has_transition, (
            "Demo scene must use transitions (FadeOut/Transform) "
            "to avoid text stacking"
        )

    def test_no_consecutive_play_write_without_removal(self, demo_scene_code):
        """Multiple Write() calls without FadeOut/Remove between them = stacking.

        This is a heuristic check: count Write/Create calls vs removal calls.
        There should be at least (writes - 1) removals to prevent stacking.
        """
        write_count = len(re.findall(r"self\.play\((Write|Create)", demo_scene_code))
        removal_count = len(re.findall(
            r"(FadeOut|RemoveTextLetterByLetter|Uncreate|ReplacementTransform|self\.remove)",
            demo_scene_code,
        ))
        if write_count > 1:
            assert removal_count >= write_count - 1, (
                f"Found {write_count} Write/Create calls but only "
                f"{removal_count} removals — elements will stack"
            )


class TestDemoEndToEnd:
    """Integration-style tests for the full --demo flow."""

    @patch("subprocess.run")
    def test_demo_cli_invocation_returns_zero(self, mock_run):
        """Running `python -m manim_gen.cli --demo` should exit 0."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with patch.object(sys, "argv", ["manim-gen", "--demo"]):
            # This tests the full CLI path with subprocess mocked
            # (Manim rendering is the subprocess call)
            result = main()
            assert result == 0

    @patch("subprocess.run")
    def test_demo_does_not_require_api_key(self, mock_run):
        """--demo should work without any LLM API key configured."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(sys, "argv", ["manim-gen", "--demo"]):
                # Should not raise KeyError or similar for missing API keys
                result = main()
                assert result == 0
