"""Shared test fixtures for stitch_video tests."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_playlist_yaml(tmp_path: Path) -> Path:
    """Create a sample YAML playlist file."""
    content = """clips:
  - path: clip1.mp4
    title_card: "Chapter 1"
    transition: fade_to_black
    transition_duration: 1.5
  - path: clip2.mp4
    transition: none
"""
    p = tmp_path / "playlist.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def sample_playlist_json(tmp_path: Path) -> Path:
    """Create a sample JSON playlist file."""
    import json

    data = {
        "clips": [
            {"path": "clip1.mp4"},
            {"path": "clip2.mp4", "transition": "fade_to_black"},
        ]
    }
    p = tmp_path / "playlist.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


@pytest.fixture
def empty_mp4(tmp_path: Path) -> Path:
    """Create a dummy MP4 file (not valid video, just exists on disk)."""
    p = tmp_path / "dummy.mp4"
    p.write_bytes(b"\x00" * 100)
    return p
