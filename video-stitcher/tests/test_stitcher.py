"""Tests for stitch_video.stitcher module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from stitch_video.config import ClipConfig
from stitch_video.errors import FFmpegError
from stitch_video.stitcher import check_ffmpeg_installed, stitch_videos


class TestCheckFFmpeg:
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    def test_ffmpeg_found(self, mock_which):
        assert check_ffmpeg_installed() is True

    @patch("shutil.which", return_value=None)
    def test_ffmpeg_not_found(self, mock_which):
        assert check_ffmpeg_installed() is False


class TestStitchVideosValidation:
    @patch("stitch_video.stitcher.check_ffmpeg_installed", return_value=False)
    def test_no_ffmpeg_raises(self, _mock):
        with pytest.raises(FFmpegError, match="ffmpeg not found"):
            stitch_videos([], Path("out.mp4"))

    @patch("stitch_video.stitcher.check_ffmpeg_installed", return_value=True)
    def test_no_clips_raises(self, _mock):
        with pytest.raises(FFmpegError, match="No clips"):
            stitch_videos([], Path("out.mp4"))

    @patch("stitch_video.stitcher.check_ffmpeg_installed", return_value=True)
    def test_missing_input_raises(self, _mock):
        clips = [ClipConfig(path=Path("/nonexistent/clip.mp4"))]
        with pytest.raises(FFmpegError, match="not found"):
            stitch_videos(clips, Path("out.mp4"))
