"""Video Stitcher - Combine multiple MP4 animations into a single video"""

from stitch_video.cli import main
from stitch_video.config import Config, QualityPreset
from stitch_video.errors import FFmpegError, PlaylistError, StitchError
from stitch_video.stitcher import stitch_videos

__all__ = [
    "main",
    "Config",
    "QualityPreset",
    "StitchError",
    "FFmpegError",
    "PlaylistError",
    "stitch_videos",
]
