"""Image validation, copying, and LLM context generation for manim_gen"""

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from manim_gen.errors import ImageValidationError

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp",
    ".tiff", ".tif", ".webp",
}
# NOTE: .svg intentionally excluded — Manim uses SVGMobject for SVGs,
# not ImageMobject. Including it here would cause silent render failures.

MAX_IMAGE_SIZE = 100 * 1024 * 1024  # 100 MB


def validate_image_path(image_path: Path, policy: str = "strict") -> bool:
    """Validate a single image path for safety and correctness.

    Args:
        image_path: Path to the image file
        policy: "strict" (raise on error), "warn" (log warning), "ignore" (skip silently)

    Returns:
        True if the image is valid, False otherwise

    Raises:
        ImageValidationError: In strict mode when validation fails
    """

    def _handle(msg: str) -> bool:
        if policy == "strict":
            raise ImageValidationError(msg)
        if policy == "warn":
            logger.warning(msg)
        return False

    # Reject symlinks BEFORE resolving — checking after resolve() always
    # sees a real path and the symlink check becomes dead code.
    if image_path.is_symlink():
        return _handle(f"Symlinks not allowed: {image_path}")

    resolved = image_path.resolve()

    if not resolved.exists():
        return _handle(f"Image not found: {resolved}")

    if not resolved.is_file():
        return _handle(f"Not a file: {resolved}")

    if resolved.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        return _handle(
            f"Unsupported image format '{resolved.suffix}'. "
            f"Allowed: {sorted(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Cache stat result to avoid double syscall (fixes double-stat issue)
    file_stat = resolved.stat()
    if file_stat.st_size > MAX_IMAGE_SIZE:
        size_mb = file_stat.st_size / (1024 * 1024)
        return _handle(f"Image too large ({size_mb:.1f} MB). Max: 100 MB")

    return True


def copy_images_to_workspace(
    image_paths: List[Path],
    workspace_dir: Path,
    policy: str = "strict",
) -> Dict[Path, Path]:
    """Copy validated images to an isolated workspace directory.

    Each image gets a deterministic name: image_0_filename.ext, image_1_filename.ext, etc.

    Args:
        image_paths: List of source image paths
        workspace_dir: Target directory to copy into
        policy: Validation policy ("strict", "warn", "ignore")

    Returns:
        Dict mapping original paths to workspace copies
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    copies: Dict[Path, Path] = {}

    for idx, img_path in enumerate(image_paths):
        # Validate the ORIGINAL path (not resolved) so symlink check works
        if not validate_image_path(img_path, policy=policy):
            continue

        resolved = img_path.resolve()
        dest_name = f"image_{idx}_{resolved.name}"
        dest = workspace_dir / dest_name
        try:
            shutil.copy2(str(resolved), str(dest))
        except OSError as exc:
            raise ImageValidationError(
                f"Failed to copy image '{img_path}': {exc}"
            ) from exc
        copies[resolved] = dest
        logger.info(f"Copied image to workspace: {dest_name}")

    return copies


def generate_image_context(
    image_paths: List[Path],
    custom_descriptions: Optional[str] = None,
) -> str:
    """Generate LLM context block describing available images.

    Args:
        image_paths: Workspace-relative image paths (after copying)
        custom_descriptions: Optional user-provided descriptions

    Returns:
        Formatted context string for the LLM prompt
    """
    if not image_paths:
        return ""

    lines = [
        "## Available Images",
        "The following image files are available in the working directory.",
        "Use `ImageMobject('filename')` to load them in your scene.",
        "",
    ]

    for path in image_paths:
        lines.append(f"- `{path.name}`")

    if custom_descriptions:
        lines.append("")
        lines.append(f"Image descriptions: {custom_descriptions}")

    lines.append("")
    lines.append(
        "Example usage:\n"
        "```python\n"
        "img = ImageMobject('image_0_photo.png')\n"
        "img.scale(0.5)\n"
        "self.play(FadeIn(img))\n"
        "```"
    )

    return "\n".join(lines)
