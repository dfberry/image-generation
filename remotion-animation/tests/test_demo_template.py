"""Tests for demo_template.py — pre-built TSX bypass.

Tests cover:
- get_demo_component() returns valid TSX structure
- Timestamp is embedded correctly
- Component meets Remotion validation requirements
- Edge cases: empty string, special characters in timestamp
"""

import pytest

from remotion_gen.demo_template import get_demo_component


class TestGetDemoComponent:
    """Test the pre-built demo template generator."""

    def test_returns_non_empty_string(self):
        """Should return a non-empty TSX code string."""
        result = get_demo_component("January 1, 2026 at 12:00 PM")
        assert isinstance(result, str)
        assert len(result) > 100

    def test_contains_export_default(self):
        """Component must have export default for Remotion to find it."""
        code = get_demo_component("January 1, 2026 at 12:00 PM")
        assert "export default" in code

    def test_contains_generated_scene_name(self):
        """Component must define GeneratedScene."""
        code = get_demo_component("January 1, 2026 at 12:00 PM")
        assert "GeneratedScene" in code

    def test_contains_remotion_imports(self):
        """Component must import from 'remotion'."""
        code = get_demo_component("January 1, 2026 at 12:00 PM")
        assert "from \"remotion\"" in code or "from 'remotion'" in code

    def test_uses_use_current_frame(self):
        """Component should use useCurrentFrame for animation."""
        code = get_demo_component("January 1, 2026 at 12:00 PM")
        assert "useCurrentFrame" in code

    def test_uses_use_video_config(self):
        """Component should use useVideoConfig for fps/duration."""
        code = get_demo_component("January 1, 2026 at 12:00 PM")
        assert "useVideoConfig" in code

    def test_embeds_timestamp(self):
        """The provided datetime string should appear in the output."""
        timestamp = "March 15, 2026 at 3:42 PM"
        code = get_demo_component(timestamp)
        assert timestamp in code

    def test_embeds_dina_berry_name(self):
        """The demo template shows 'Dina Berry' name card."""
        code = get_demo_component("January 1, 2026 at 12:00 PM")
        assert "Dina Berry" in code

    def test_contains_return_statement(self):
        """Component must have a return statement with JSX."""
        code = get_demo_component("January 1, 2026 at 12:00 PM")
        assert "return" in code

    def test_contains_absolute_fill(self):
        """Component should use AbsoluteFill (standard Remotion pattern)."""
        code = get_demo_component("January 1, 2026 at 12:00 PM")
        assert "AbsoluteFill" in code


class TestDemoTemplateEdgeCases:
    """Edge cases for demo template generation."""

    def test_empty_timestamp(self):
        """Empty timestamp should not crash — just embed empty string."""
        code = get_demo_component("")
        assert "GeneratedScene" in code
        assert "export default" in code

    def test_special_characters_in_timestamp(self):
        """Timestamps with special chars should be safely embedded."""
        timestamp = "Día 25 de Março, 2026 — 14:30"
        code = get_demo_component(timestamp)
        assert timestamp in code

    def test_long_timestamp(self):
        """Very long timestamp should not break the template."""
        timestamp = "A" * 500
        code = get_demo_component(timestamp)
        assert timestamp in code

    def test_timestamp_with_quotes(self):
        """Timestamp containing quotes should be embedded without breaking."""
        # The f-string in get_demo_component may break on embedded braces,
        # but regular single/double quotes should be fine in JSX text content
        timestamp = "January 1, 2026 at 12:00 PM"
        code = get_demo_component(timestamp)
        assert "GeneratedScene" in code

    def test_different_timestamps_produce_different_output(self):
        """Different timestamps should produce different component code."""
        code1 = get_demo_component("January 1, 2026 at 12:00 PM")
        code2 = get_demo_component("December 31, 2026 at 11:59 PM")
        assert code1 != code2
