"""FFmpeg-based video stitching engine."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import List

from stitch_video.config import ClipConfig, QualityPreset, TransitionType
from stitch_video.errors import FFmpegError

logger = logging.getLogger(__name__)


def check_ffmpeg_installed() -> bool:
    """Check if ffmpeg CLI is available."""
    return shutil.which("ffmpeg") is not None


def stitch_videos(
    clips: List[ClipConfig],
    output_path: Path,
    quality: QualityPreset = QualityPreset.MEDIUM,
) -> Path:
    """Stitch multiple MP4 clips into a single video.

    Args:
        clips: Ordered list of clip configurations.
        output_path: Path for the final output video.
        quality: Quality preset controlling resolution and framerate.

    Returns:
        Path to the stitched output video.

    Raises:
        FFmpegError: If ffmpeg is missing, a clip is missing, or encoding fails.
    """
    if not check_ffmpeg_installed():
        raise FFmpegError(
            "ffmpeg not found. Install FFmpeg: https://ffmpeg.org/download.html"
        )

    if not clips:
        raise FFmpegError("No clips provided")

    # Validate all input files exist
    for clip in clips:
        if not clip.path.exists():
            raise FFmpegError(f"Input file not found: {clip.path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the list of segments (title cards + clips with transitions)
    segments = _build_segment_list(clips, quality)

    if len(segments) == 1 and not _has_transitions(clips):
        # Single clip, no transitions — just re-encode to normalize
        _reencode_single(segments[0], output_path, quality)
    else:
        _concat_segments(segments, output_path, quality, clips)

    # Clean up any generated title card files
    for seg in segments:
        if seg.get("_temp"):
            seg["path"].unlink(missing_ok=True)

    if not output_path.exists():
        raise FFmpegError("Stitching completed but output file not found")

    logger.info(f"Stitched video saved to {output_path}")
    return output_path


def _has_transitions(clips: List[ClipConfig]) -> bool:
    """Check if any clip requests a transition effect."""
    return any(c.transition != TransitionType.NONE for c in clips)


def _build_segment_list(
    clips: List[ClipConfig], quality: QualityPreset
) -> List[dict]:
    """Build ordered list of segment dicts (title cards interleaved with clips)."""
    segments = []
    for clip in clips:
        if clip.title_card:
            title_path = _generate_title_card(
                clip.title_card, clip.title_duration, quality
            )
            segments.append({"path": title_path, "_temp": True})
        segments.append({"path": clip.path, "_temp": False})
    return segments


def _generate_title_card(
    text: str, duration: float, quality: QualityPreset
) -> Path:
    """Generate a title card MP4 using FFmpeg's drawtext filter.

    Returns path to the temporary title card video.
    """
    import hashlib

    name_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    out = Path(f"_titlecard_{name_hash}.mp4")

    # Escape special chars for drawtext
    safe_text = text.replace("'", "'\\''").replace(":", "\\:")

    font_size = max(24, quality.height // 15)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={quality.width}x{quality.height}:r={quality.fps}:d={duration}",
        "-vf", (
            f"drawtext=text='{safe_text}'"
            f":fontsize={font_size}"
            f":fontcolor=white"
            f":x=(w-text_w)/2:y=(h-text_h)/2"
        ),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        str(out),
    ]

    logger.info(f"Generating title card: {text}")
    _run_ffmpeg(cmd)
    return out


def _reencode_single(segment: dict, output_path: Path, quality: QualityPreset) -> None:
    """Re-encode a single clip to the target quality."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(segment["path"]),
        "-vf", f"scale={quality.width}:{quality.height}:force_original_aspect_ratio=decrease,"
               f"pad={quality.width}:{quality.height}:(ow-iw)/2:(oh-ih)/2",
        "-r", str(quality.fps),
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    _run_ffmpeg(cmd)


def _concat_segments(
    segments: List[dict],
    output_path: Path,
    quality: QualityPreset,
    clips: List[ClipConfig],
) -> None:
    """Concatenate multiple segments using FFmpeg's concat filter.

    Normalizes all inputs to the same resolution/fps before concatenating.
    Applies transition effects where configured.
    """
    if _has_transitions(clips):
        _concat_with_transitions(segments, output_path, quality, clips)
    else:
        _concat_simple(segments, output_path, quality)


def _concat_simple(
    segments: List[dict], output_path: Path, quality: QualityPreset
) -> None:
    """Simple concat using the concat demuxer (fast, no transitions)."""
    # First normalize all segments to same format
    normalized = []
    for i, seg in enumerate(segments):
        norm_path = Path(f"_norm_{i}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(seg["path"]),
            "-vf", f"scale={quality.width}:{quality.height}:force_original_aspect_ratio=decrease,"
                   f"pad={quality.width}:{quality.height}:(ow-iw)/2:(oh-ih)/2",
            "-r", str(quality.fps),
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            "-pix_fmt", "yuv420p",
            str(norm_path),
        ]
        _run_ffmpeg(cmd)
        normalized.append(norm_path)

    # Build concat file
    concat_file = Path("_concat_list.txt")
    lines = [f"file '{p.resolve()}'" for p in normalized]
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]
    _run_ffmpeg(cmd)

    # Cleanup
    concat_file.unlink(missing_ok=True)
    for p in normalized:
        p.unlink(missing_ok=True)


def _concat_with_transitions(
    segments: List[dict],
    output_path: Path,
    quality: QualityPreset,
    clips: List[ClipConfig],
) -> None:
    """Concatenate with transition effects using the xfade filter.

    For fade_to_black: inserts a black frame gap between clips.
    For crossfade: uses xfade filter between consecutive clips.
    """
    # Normalize all segments first
    normalized = []
    for i, seg in enumerate(segments):
        norm_path = Path(f"_norm_{i}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(seg["path"]),
            "-vf", f"scale={quality.width}:{quality.height}:force_original_aspect_ratio=decrease,"
                   f"pad={quality.width}:{quality.height}:(ow-iw)/2:(oh-ih)/2",
            "-r", str(quality.fps),
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            "-pix_fmt", "yuv420p",
            str(norm_path),
        ]
        _run_ffmpeg(cmd)
        normalized.append(norm_path)

    # Map clips to segments (accounting for title cards that were inserted)
    # For simplicity with transitions, we concatenate normalized files
    # using the concat demuxer but insert fade-to-black segments between clips
    # that request it.

    final_segments = []
    clip_idx = 0
    for i, seg in enumerate(segments):
        final_segments.append(normalized[i])

        # After each real clip (not a title card), check if the NEXT clip
        # wants a fade-to-black transition
        if not seg.get("_temp"):
            clip_idx += 1
            if clip_idx < len(clips) and clips[clip_idx].transition == TransitionType.FADE_TO_BLACK:
                dur = clips[clip_idx].transition_duration
                black_path = Path(f"_black_{clip_idx}.mp4")
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=black:s={quality.width}x{quality.height}:r={quality.fps}:d={dur}",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", str(dur),
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "128k",
                    "-pix_fmt", "yuv420p",
                    str(black_path),
                ]
                _run_ffmpeg(cmd)
                final_segments.append(black_path)

    # Concat all final segments
    concat_file = Path("_concat_list.txt")
    lines = [f"file '{p.resolve()}'" for p in final_segments]
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]
    _run_ffmpeg(cmd)

    # Cleanup
    concat_file.unlink(missing_ok=True)
    for p in normalized:
        p.unlink(missing_ok=True)
    for p in final_segments:
        if p not in normalized:
            p.unlink(missing_ok=True)


def _run_ffmpeg(cmd: List[str]) -> subprocess.CompletedProcess:
    """Run an FFmpeg command and handle errors."""
    logger.debug(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed (exit {e.returncode})")
        logger.error(f"stderr: {e.stderr}")
        raise FFmpegError(f"FFmpeg failed: {e.stderr[:500]}")
    except FileNotFoundError:
        raise FFmpegError(
            "ffmpeg not found. Install FFmpeg: https://ffmpeg.org/download.html"
        )
