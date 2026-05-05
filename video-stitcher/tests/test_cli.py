"""Tests for stitch_video.cli module."""

from pathlib import Path
from unittest.mock import patch

from stitch_video.cli import _load_from_drop_folder, build_clips_from_args, main
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
        assert clips[0].transition == TransitionType.NONE
        assert clips[1].transition == TransitionType.FADE_TO_BLACK
        assert clips[1].transition_duration == 2.0
        assert clips[2].transition == TransitionType.FADE_TO_BLACK


class TestLoadFromDropFolder:
    def test_empty_folder_returns_empty(self, tmp_path):
        clips_dir = tmp_path / "clips"
        clips_dir.mkdir()
        result = _load_from_drop_folder(clips_dir, TransitionType.NONE, 1.0)
        assert result == []

    def test_nonexistent_folder_returns_empty(self, tmp_path):
        result = _load_from_drop_folder(
            tmp_path / "nope", TransitionType.NONE, 1.0
        )
        assert result == []

    def test_finds_mp4s_sorted(self, tmp_path):
        clips_dir = tmp_path / "clips"
        clips_dir.mkdir()
        (clips_dir / "02-second.mp4").write_bytes(b"\x00")
        (clips_dir / "01-first.mp4").write_bytes(b"\x00")
        (clips_dir / "readme.txt").write_text("ignore me")
        result = _load_from_drop_folder(clips_dir, TransitionType.FADE_TO_BLACK, 1.5)
        assert len(result) == 2
        assert result[0].path.name == "01-first.mp4"
        assert result[1].path.name == "02-second.mp4"
        assert result[0].transition == TransitionType.NONE
        assert result[1].transition == TransitionType.FADE_TO_BLACK


class TestMainErrors:
    def test_no_inputs_empty_clips_dir_returns_1(self, tmp_path):
        clips_dir = tmp_path / "clips"
        clips_dir.mkdir()
        with patch("sys.argv", ["stitch-video", "--clips-dir", str(clips_dir)]):
            assert main() == 1

    def test_playlist_and_inputs_returns_1(self, tmp_path):
        playlist = tmp_path / "p.yaml"
        playlist.write_text("clips:\n  - path: x.mp4\n", encoding="utf-8")
        with patch(
            "sys.argv",
            ["stitch-video", "--playlist", str(playlist), "extra.mp4"],
        ):
            assert main() == 1
