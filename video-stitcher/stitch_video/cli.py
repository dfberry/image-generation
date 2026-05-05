#!/usr/bin/env python3
"""Video Stitcher CLI — combine multiple MP4 animations into one video."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from stitch_video.config import ClipConfig, Config, QualityPreset, TransitionType
from stitch_video.errors import FFmpegError, PlaylistError, StitchError
from stitch_video.playlist import load_playlist
from stitch_video.stitcher import stitch_videos

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Stitch multiple MP4 animations into a single video",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  stitch-video                             (reads all MP4s from clips/ folder)
  stitch-video clip1.mp4 clip2.mp4 clip3.mp4
  stitch-video --playlist playlist.yaml --quality high
  stitch-video clip1.mp4 clip2.mp4 --transition fade_to_black --output final.mp4
  stitch-video --clips-dir ./my-clips --quality high

Drop folder workflow:
  1. Render animations with manim-gen or remotion-gen
  2. Copy/move MP4 outputs into the clips/ folder
  3. Run: stitch-video

Playlist format (YAML):
  clips:
    - path: intro.mp4
      title_card: "Chapter 1: Introduction"
      transition: fade_to_black
    - path: demo.mp4
      transition: none
        """,
    )

    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="Input MP4 files to stitch together (in order)",
    )

    parser.add_argument(
        "--playlist",
        type=Path,
        help="Path to a JSON or YAML playlist file (alternative to positional inputs)",
    )

    parser.add_argument(
        "--clips-dir",
        type=Path,
        default=None,
        help="Drop folder containing MP4 clips (default: clips/)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output video path (default: outputs/stitched_YYYYMMDD_HHMMSS.mp4)",
    )

    parser.add_argument(
        "--quality",
        type=str,
        choices=["low", "medium", "high"],
        default="medium",
        help="Video quality preset (default: medium)",
    )

    parser.add_argument(
        "--transition",
        type=str,
        choices=["none", "fade_to_black", "crossfade"],
        default="none",
        help="Transition effect between clips (default: none)",
    )

    parser.add_argument(
        "--transition-duration",
        type=float,
        default=1.0,
        help="Transition duration in seconds (default: 1.0)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args()


def build_clips_from_args(
    inputs: List[Path],
    transition: TransitionType,
    transition_duration: float,
) -> List[ClipConfig]:
    """Build ClipConfig list from CLI positional arguments."""
    clips = []
    for i, path in enumerate(inputs):
        # First clip gets no transition; subsequent clips use the specified one
        t = TransitionType.NONE if i == 0 else transition
        clips.append(
            ClipConfig(
                path=path.resolve(),
                transition=t,
                transition_duration=transition_duration,
            )
        )
    return clips


def _load_from_drop_folder(
    clips_dir: Path,
    transition: TransitionType,
    transition_duration: float,
) -> List[ClipConfig]:
    """Load all MP4 files from the drop folder, sorted alphabetically."""
    if not clips_dir.exists():
        return []
    mp4s = sorted(clips_dir.glob("*.mp4"))
    if not mp4s:
        return []
    logger.info(f"Found {len(mp4s)} MP4 file(s) in drop folder: {clips_dir}")
    return build_clips_from_args(mp4s, transition, transition_duration)


def main() -> int:
    """CLI entry point.

    Exit codes:
        0 — Success
        1 — Input error (no clips, missing files)
        2 — Playlist error (invalid format)
        3 — FFmpeg error (encoding failure)
        4 — Unexpected error
    """
    args = parse_args()
    setup_logging(args.debug)

    try:
        # Determine clip list from playlist, positional args, or drop folder
        if args.playlist:
            if args.inputs:
                print(
                    "✗ Error: Cannot use both positional inputs and --playlist",
                    file=sys.stderr,
                )
                return 1
            clips = load_playlist(args.playlist)
        elif args.inputs:
            transition = TransitionType(args.transition)
            clips = build_clips_from_args(
                args.inputs, transition, args.transition_duration
            )
        else:
            # Default: read all MP4s from the drop folder
            clips_dir = args.clips_dir or Config().clips_dir
            clips = _load_from_drop_folder(
                clips_dir,
                TransitionType(args.transition),
                args.transition_duration,
            )
            if not clips:
                print(
                    f"✗ Error: No MP4 files found in drop folder: {clips_dir}",
                    file=sys.stderr,
                )
                print(
                    "  Copy rendered animations into the clips/ folder, or provide explicit paths.",
                    file=sys.stderr,
                )
                return 1

        if len(clips) < 1:
            print("✗ Error: At least one clip is required", file=sys.stderr)
            return 1

        # Build config
        config = Config(
            quality=QualityPreset[args.quality.upper()],
            transition=TransitionType(args.transition),
            transition_duration=args.transition_duration,
        )

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.output_dir / f"stitched_{timestamp}.mp4"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Run stitcher
        result = stitch_videos(
            clips=clips,
            output_path=output_path,
            quality=config.quality,
        )

        print(f"\n✓ Video stitched successfully: {result}")
        print(f"  Clips: {len(clips)}")
        print(
            f"  Quality: {config.quality.name} "
            f"({config.quality.height}p @ {config.quality.fps}fps)"
        )
        return 0

    except PlaylistError as e:
        logger.error(f"Playlist error: {e}")
        print(f"\n✗ Playlist Error: {e}", file=sys.stderr)
        return 2

    except FFmpegError as e:
        logger.error(f"FFmpeg error: {e}")
        print(f"\n✗ FFmpeg Error: {e}", file=sys.stderr)
        print("  Check that FFmpeg is installed correctly", file=sys.stderr)
        return 3

    except StitchError as e:
        logger.error(f"Stitch error: {e}")
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        logger.exception("Unexpected error")
        print(f"\n✗ Unexpected Error: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
