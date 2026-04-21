"""Manim CLI wrapper for rendering scenes"""

import logging
import shutil
import subprocess
from pathlib import Path

from manim_gen.config import QualityPreset
from manim_gen.errors import RenderError

logger = logging.getLogger(__name__)

def check_manim_installed() -> bool:
    """Check if manim CLI is available"""
    return shutil.which("manim") is not None

def render_scene(
    scene_file: Path,
    output_path: Path,
    quality: QualityPreset = QualityPreset.MEDIUM,
    assets_dir: Path = None,
) -> Path:
    """Render Manim scene to video file

    Args:
        scene_file: Path to Python file containing GeneratedScene
        output_path: Desired output video path
        quality: Quality preset (LOW, MEDIUM, HIGH)
        assets_dir: Optional directory containing image assets (sets cwd for Manim)

    Returns:
        Path to rendered video file

    Raises:
        RenderError: If manim is not installed or render fails
    """
    if not check_manim_installed():
        raise RenderError(
            "manim CLI not found. Install with: pip install manim\n"
            "Requires FFmpeg: https://docs.manim.community/en/stable/installation.html"
        )

    # Build manim command
    # manim render <file> <scene_class> --format=mp4 -q<quality>
    cmd = [
        "manim",
        "render",
        str(scene_file),
        "GeneratedScene",
        "--format=mp4",
        f"-q{quality.flag}",
        "--disable_caching",  # Avoid caching issues between runs
    ]

    logger.info(f"Running: {' '.join(cmd)}")

    try:
        run_kwargs = dict(capture_output=True, text=True, check=True)
        if assets_dir:
            run_kwargs["cwd"] = str(assets_dir)
        result = subprocess.run(cmd, **run_kwargs)

        logger.info("Manim render completed successfully")
        logger.debug(f"stdout: {result.stdout}")

        # Manim outputs to media/videos/<scene_file_stem>/[quality]/GeneratedScene.mp4
        scene_stem = scene_file.stem
        manim_output = (
            scene_file.parent
            / "media"
            / "videos"
            / scene_stem
            / {
                QualityPreset.LOW: "480p15",
                QualityPreset.MEDIUM: "720p30",
                QualityPreset.HIGH: "1080p60",
            }[quality]
            / "GeneratedScene.mp4"
        )

        if not manim_output.exists():
            # Fallback: search for any GeneratedScene.mp4
            media_dir = scene_file.parent / "media"
            if media_dir.exists():
                matches = list(media_dir.rglob("GeneratedScene.mp4"))
                if matches:
                    manim_output = matches[0]
                    logger.info(f"Found output at: {manim_output}")
                else:
                    raise RenderError("Manim completed but output video not found")
            else:
                raise RenderError("Manim media directory not created")

        # Move to desired output location
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(manim_output), str(output_path))
        logger.info(f"Video moved to {output_path}")

        return output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"Manim render failed with exit code {e.returncode}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        raise RenderError(f"Manim render failed: {e.stderr}")

    except Exception as e:
        raise RenderError(f"Unexpected error during render: {e}")
