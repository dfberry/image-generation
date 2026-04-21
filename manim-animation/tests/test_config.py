"""Config tests for manim-animation."""

from pathlib import Path

import pytest

from manim_gen.config import Config, QualityPreset


class TestQualityPresets:

    def test_low_quality_preset(self):
        assert QualityPreset.LOW.height == 480
        assert QualityPreset.LOW.fps == 15
        assert QualityPreset.LOW.flag == "l"

    def test_medium_quality_preset(self):
        assert QualityPreset.MEDIUM.height == 720
        assert QualityPreset.MEDIUM.fps == 30
        assert QualityPreset.MEDIUM.flag == "m"

    def test_high_quality_preset(self):
        assert QualityPreset.HIGH.height == 1080
        assert QualityPreset.HIGH.fps == 60
        assert QualityPreset.HIGH.flag == "h"

    def test_invalid_quality_string_raises_error(self):
        with pytest.raises(KeyError):
            QualityPreset["ULTRA"]

class TestCustomOverrides:

    def test_quality_string_coerced_to_enum(self):
        config = Config(quality="high", duration=10)
        assert config.quality == QualityPreset.HIGH

    def test_output_dir_string_coerced_to_path(self):
        config = Config(output_dir="my_outputs")
        assert config.output_dir == Path("my_outputs")

    def test_custom_duration_works(self):
        config = Config(duration=20)
        assert config.duration == 20

class TestDefaultConfig:

    def test_default_quality_is_medium(self):
        config = Config()
        assert config.quality == QualityPreset.MEDIUM

    def test_default_output_dir_is_outputs(self):
        config = Config()
        assert config.output_dir == Path("outputs")

    def test_default_duration_is_10_seconds(self):
        config = Config()
        assert config.duration == 10

    def test_duration_below_minimum_raises(self):
        with pytest.raises(ValueError, match="Duration must be between"):
            Config(duration=2)

    def test_duration_above_maximum_raises(self):
        with pytest.raises(ValueError, match="Duration must be between"):
            Config(duration=60)
