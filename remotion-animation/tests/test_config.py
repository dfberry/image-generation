"""Config tests for remotion-animation.

Tests cover:
- Quality presets resolve to correct resolution/fps
- Custom QualityPreset overrides
- Invalid quality key → KeyError
- Default configuration constants
- QualityPreset.resolution_name property
"""

import pytest

from remotion_gen.config import (
    DEFAULT_DURATION_SECONDS,
    DEFAULT_PROVIDER,
    MAX_DURATION_SECONDS,
    MIN_DURATION_SECONDS,
    QUALITY_PRESETS,
    QualityPreset,
)


class TestQualityPresets:
    """Test quality preset resolution."""

    def test_low_quality_preset(self):
        """Quality 'low' should resolve to 854×480 15fps."""
        preset = QUALITY_PRESETS["low"]
        assert preset.width == 854
        assert preset.height == 480
        assert preset.fps == 15

    def test_medium_quality_preset(self):
        """Quality 'medium' should resolve to 1280×720 30fps."""
        preset = QUALITY_PRESETS["medium"]
        assert preset.width == 1280
        assert preset.height == 720
        assert preset.fps == 30

    def test_high_quality_preset(self):
        """Quality 'high' should resolve to 1920×1080 60fps."""
        preset = QUALITY_PRESETS["high"]
        assert preset.width == 1920
        assert preset.height == 1080
        assert preset.fps == 60

    def test_invalid_quality_string_raises_error(self):
        """Invalid quality string should raise KeyError."""
        with pytest.raises(KeyError):
            _ = QUALITY_PRESETS["ultra"]

    def test_all_presets_have_positive_dimensions(self):
        """All presets must have positive width, height, and fps."""
        for name, preset in QUALITY_PRESETS.items():
            assert preset.width > 0, f"{name} width <= 0"
            assert preset.height > 0, f"{name} height <= 0"
            assert preset.fps > 0, f"{name} fps <= 0"


class TestQualityPresetResolutionName:
    """Test QualityPreset.resolution_name property."""

    def test_1080p_name(self):
        """Height >= 1080 should report '1080p'."""
        preset = QualityPreset(width=1920, height=1080, fps=60)
        assert preset.resolution_name == "1080p"

    def test_720p_name(self):
        """Height >= 720 (but < 1080) should report '720p'."""
        preset = QualityPreset(width=1280, height=720, fps=30)
        assert preset.resolution_name == "720p"

    def test_480p_name(self):
        """Height < 720 should report '480p'."""
        preset = QualityPreset(width=854, height=480, fps=15)
        assert preset.resolution_name == "480p"

    def test_4k_still_reports_1080p(self):
        """Height > 1080 should still report '1080p' (highest label)."""
        preset = QualityPreset(width=3840, height=2160, fps=60)
        assert preset.resolution_name == "1080p"


class TestCustomOverrides:
    """Test custom QualityPreset creation."""

    def test_custom_resolution(self):
        """Custom width/height should be stored correctly."""
        preset = QualityPreset(width=640, height=360, fps=24)
        assert preset.width == 640
        assert preset.height == 360

    def test_custom_fps(self):
        """Custom fps should be stored correctly."""
        preset = QualityPreset(width=1280, height=720, fps=24)
        assert preset.fps == 24

    def test_custom_duration_constant(self):
        """Default duration constant should be 5 seconds."""
        assert DEFAULT_DURATION_SECONDS == 5


class TestDefaultConfig:
    """Test default configuration constants."""

    def test_default_duration(self):
        """Default duration should be 5 seconds."""
        assert DEFAULT_DURATION_SECONDS == 5

    def test_min_duration(self):
        """Minimum duration should be 5 seconds."""
        assert MIN_DURATION_SECONDS == 5

    def test_max_duration(self):
        """Maximum duration should be 30 seconds."""
        assert MAX_DURATION_SECONDS == 30

    def test_min_less_than_max(self):
        """MIN_DURATION must be less than MAX_DURATION."""
        assert MIN_DURATION_SECONDS < MAX_DURATION_SECONDS

    def test_default_provider(self):
        """Default provider should be 'ollama'."""
        assert DEFAULT_PROVIDER == "ollama"

    def test_three_quality_presets_exist(self):
        """Exactly three presets (low, medium, high) should exist."""
        assert set(QUALITY_PRESETS.keys()) == {"low", "medium", "high"}
