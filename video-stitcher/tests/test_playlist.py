"""Tests for stitch_video.playlist module."""

import json

import pytest

from stitch_video.config import TransitionType
from stitch_video.errors import PlaylistError
from stitch_video.playlist import load_playlist


class TestLoadPlaylist:
    def test_load_yaml(self, sample_playlist_yaml, tmp_path):
        clips = load_playlist(sample_playlist_yaml)
        assert len(clips) == 2
        assert clips[0].title_card == "Chapter 1"
        assert clips[0].transition == TransitionType.FADE_TO_BLACK
        assert clips[0].transition_duration == 1.5
        assert clips[1].transition == TransitionType.NONE

    def test_load_json(self, sample_playlist_json, tmp_path):
        clips = load_playlist(sample_playlist_json)
        assert len(clips) == 2
        assert clips[1].transition == TransitionType.FADE_TO_BLACK

    def test_simple_string_entries(self, tmp_path):
        import yaml

        data = {"clips": ["a.mp4", "b.mp4"]}
        p = tmp_path / "simple.yaml"
        p.write_text(yaml.dump(data), encoding="utf-8")
        clips = load_playlist(p)
        assert len(clips) == 2

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(PlaylistError, match="not found"):
            load_playlist(tmp_path / "nonexistent.yaml")

    def test_bad_format_raises(self, tmp_path):
        p = tmp_path / "bad.txt"
        p.write_text("hello", encoding="utf-8")
        with pytest.raises(PlaylistError, match="Unsupported playlist format"):
            load_playlist(p)

    def test_missing_clips_key_raises(self, tmp_path):
        p = tmp_path / "no_clips.yaml"
        p.write_text("foo: bar\n", encoding="utf-8")
        with pytest.raises(PlaylistError, match="clips"):
            load_playlist(p)

    def test_empty_clips_raises(self, tmp_path):
        p = tmp_path / "empty.yaml"
        p.write_text("clips: []\n", encoding="utf-8")
        with pytest.raises(PlaylistError, match="non-empty"):
            load_playlist(p)

    def test_clip_missing_path_raises(self, tmp_path):
        p = tmp_path / "no_path.json"
        p.write_text(json.dumps({"clips": [{"transition": "none"}]}), encoding="utf-8")
        with pytest.raises(PlaylistError, match="path"):
            load_playlist(p)


class TestPathResolution:
    def test_relative_paths_resolved_to_playlist_dir(self, tmp_path):
        data = {"clips": ["subdir/clip.mp4"]}
        p = tmp_path / "playlist.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        clips = load_playlist(p)
        assert clips[0].path == (tmp_path / "subdir" / "clip.mp4").resolve()

    def test_custom_base_dir(self, tmp_path):
        data = {"clips": ["clip.mp4"]}
        p = tmp_path / "playlist.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        base = tmp_path / "custom"
        clips = load_playlist(p, base_dir=base)
        assert clips[0].path == (base / "clip.mp4").resolve()
