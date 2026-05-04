"""Tests for stitch_video.cli module."""

from pathlib import Path
from unittest.mock import patch

from stitch_video.cli import build_clips_from_args, main
from stitch_video.config import TransitionType


class TestBuildClipsFromArgs:
    def test_single_clip(self):
        clips = build_clips_from_args(
            [Path("a.mp4")], TransitionType.NONE, 1.0
        )
        assert len(clips) == 1
        assert clips[0].transition == TransitionType.NONE

    def test_multiple_clips_with_transition(self):
        clips = build_clips_from_args(
            [Path("a.mp4"), Path("b.mp4"), Path("c.mp4")],
            TransitionType.FADE_TO_BLACK,
            2.0,
        )
        assert len(clips) == 3
        # First clip has no transition
        assert clips[0].transition == TransitionType.NONE
        # Subsequent clips use the specified transition
        assert clips[1].transition == TransitionType.FADE_TO_BLACK
        assert clips[1].transition_duration == 2.0
        assert clips[2].transition == TransitionType.FADE_TO_BLACK


class TestMainErrors:
    def test_no_inputs_returns_1(self):
        with patch("sys.argv", ["stitch-video"]):
            assert main() == 1

    def test_playlist_and_inputs_returns_1(self, tmp_path):
        playlist = tmp_path / "p.yaml"
        playlist.write_text("clips:\n  - path: x.mp4\n", encoding="utf-8")
        with patch(
            "sys.argv",
            ["stitch-video", "--playlist", str(playlist), "extra.mp4"],
        ):
            assert main() == 1
