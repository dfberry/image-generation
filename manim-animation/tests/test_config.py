"""Config tests for manim-animation.

Tests cover:
- Quality presets resolve to correct resolution/fps
- Custom overrides work
- Invalid quality string → error
"""

import pytest


class TestQualityPresets:
    """Test quality preset resolution."""

    def test_low_quality_preset(self):
        """Quality 'low' should resolve to 480p30."""
        pytest.skip("Waiting for Trinity's config.py implementation")
        # Expected: {"width": 854, "height": 480, "fps": 30}

    def test_medium_quality_preset(self):
        """Quality 'medium' should resolve to 720p30."""
        pytest.skip("Waiting for Trinity's config.py implementation")
        # Expected: {"width": 1280, "height": 720, "fps": 30}

    def test_high_quality_preset(self):
        """Quality 'high' should resolve to 1080p60."""
        pytest.skip("Waiting for Trinity's config.py implementation")
        # Expected: {"width": 1920, "height": 1080, "fps": 60}

    def test_invalid_quality_string_raises_error(self):
        """Invalid quality string should raise error."""
        pytest.skip("Waiting for Trinity's config.py implementation")
        # Invalid: "best", "ultra", "4k", etc.


class TestCustomOverrides:
    """Test custom config overrides."""

    def test_custom_resolution_overrides_preset(self):
        """Custom width/height should override quality preset."""
        pytest.skip("Waiting for Trinity's config.py implementation")

    def test_custom_fps_overrides_preset(self):
        """Custom fps should override quality preset."""
        pytest.skip("Waiting for Trinity's config.py implementation")

    def test_custom_duration_works(self):
        """Custom duration should be applied."""
        pytest.skip("Waiting for Trinity's config.py implementation")


class TestDefaultConfig:
    """Test default configuration values."""

    def test_default_quality_is_medium(self):
        """Default quality should be 'medium' if not specified."""
        pytest.skip("Waiting for Trinity's config.py implementation")

    def test_default_output_dir_is_outputs(self):
        """Default output directory should be 'outputs/'."""
        pytest.skip("Waiting for Trinity's config.py implementation")

    def test_default_duration_is_15_seconds(self):
        """Default video duration should be 15 seconds."""
        pytest.skip("Waiting for Trinity's config.py implementation")
