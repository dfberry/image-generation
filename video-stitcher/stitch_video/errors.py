"""Custom exceptions for stitch_video"""


class StitchError(Exception):
    """Base exception for all stitch_video errors."""

    pass


class FFmpegError(StitchError):
    """Raised when an FFmpeg subprocess call fails.

    Covers ffmpeg not found, non-zero exit codes, and missing output files.
    """

    pass


class PlaylistError(StitchError):
    """Raised when a playlist file is invalid.

    Covers parse errors, missing required fields, and invalid file references.
    """

    pass
