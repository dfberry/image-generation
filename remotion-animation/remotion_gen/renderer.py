"""Remotion CLI wrapper for video rendering."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from remotion_gen.config import QualityPreset
from remotion_gen.errors import RenderError


def check_prerequisites() -> tuple[bool, Optional[str]]:
    """Check if Node.js and npm are available.

    Returns:
        (success, error_message)
    """
    if not shutil.which("node"):
        return False, "Node.js not found. Install from https://nodejs.org/"

    if not shutil.which("npm"):
        return False, "npm not found. Install Node.js from https://nodejs.org/"

    return True, None


def render_video(
    project_root: Path,
    output_path: Path,
    quality: QualityPreset,
    duration_frames: int,
) -> Path:
    """Render video using Remotion CLI.

    Args:
        project_root: Path to remotion-project directory
        output_path: Where to save the MP4
        quality: Quality preset (width, height, fps)
        duration_frames: Video duration in frames

    Returns:
        Path to rendered video

    Raises:
        RenderError: If rendering fails
    """
    ok, error = check_prerequisites()
    if not ok:
        raise RenderError(error)

    # Check if node_modules exists
    node_modules = project_root / "node_modules"
    if not node_modules.exists():
        raise RenderError(
            f"Dependencies not installed. Run: npm install (in {project_root})"
        )

    # Resolve npx path (on Windows, npx is installed as npx.cmd)
    npx_path = shutil.which("npx")
    if not npx_path:
        raise RenderError(
            "npx command not found. Ensure Node.js and npm are installed."
        )

    # Build Remotion render command
    cmd = [
        npx_path,
        "remotion",
        "render",
        "src/index.ts",
        "GeneratedScene",
        str(output_path.absolute()),
        "--codec=h264",
        f"--width={quality.width}",
        f"--height={quality.height}",
        f"--fps={quality.fps}",
        "--props={" + '"durationInFrames":' + str(duration_frames) + '}',
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RenderError(f"Remotion render failed: {error_msg}")

        if not output_path.exists():
            raise RenderError(f"Render completed but output not found: {output_path}")

        return output_path

    except Exception as e:
        raise RenderError(f"Render process failed: {e}")
