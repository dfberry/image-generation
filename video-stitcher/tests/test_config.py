"""Tests for stitch_video.config module."""

from pathlib import Path

from stitch_video.config import ClipConfig, Config, QualityPreset, TransitionType


class TestQualityPreset:
    def test_low_preset(self):
        assert QualityPreset.LOW.height == 480
        assert QualityPreset.LOW.fps == 15
        assert QualityPreset.LOW.width == 853  # int(480 * 16/9)

    def test_medium_preset(self):
        assert QualityPreset.MEDIUM.height == 720
        assert QualityPreset.MEDIUM.fps == 30

    def test_high_preset(self):
        assert QualityPreset.HIGH.height == 1080
        assert QualityPreset.HIGH.fps == 60


class TestTransitionType:
    def test_values(self):
        assert TransitionType.NONE.value == "none"
        assert TransitionType.FADE_TO_BLACK.value == "fade_to_black"
        assert TransitionType.CROSSFADE.value == "crossfade"


class TestClipConfig:
    def test_string_path_conversion(self):
        clip = ClipConfig(path="test.mp4")
        assert isinstance(clip.path, Path)

    def test_string_transition_conversion(self):
        clip = ClipConfig(path="test.mp4", transition="fade_to_black")
        assert clip.transition == TransitionType.FADE_TO_BLACK

    def test_defaults(self):
        clip = ClipConfig(path="test.mp4")
        assert clip.transition == TransitionType.NONE
        assert clip.transition_duration == 1.0
        assert clip.title_card is None
        assert clip.title_duration == 3.0


class TestConfig:
    def test_defaults(self):
        config = Config()
        assert config.quality == QualityPreset.MEDIUM
        assert config.output_dir == Path("outputs")
        assert config.transition == TransitionType.NONE

    def test_string_quality(self):
        config = Config(quality="high")
        assert config.quality == QualityPreset.HIGH

    def test_string_transition(self):
        config = Config(transition="fade_to_black")
        assert config.transition == TransitionType.FADE_TO_BLACK
