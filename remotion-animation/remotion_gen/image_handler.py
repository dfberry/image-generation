"""Image validation, copying, and LLM context generation for image input support."""

import shutil
import uuid
from pathlib import Path

from remotion_gen.errors import ImageValidationError

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
MAX_IMAGE_SIZE = 100 * 1024 * 1024  # 100 MB


def validate_image_path(image_path: str, policy: str = "strict") -> Path:
    """Validate that an image path is safe and points to a supported file.

    Args:
        image_path: Path to the image file.
        policy: "strict" raises on all issues, "warn" prints warnings,
                "ignore" skips validation entirely.

    Returns:
        Resolved Path object.

    Raises:
        ImageValidationError: If validation fails under strict policy.
    """
    if policy == "ignore":
        return Path(image_path).resolve()

    path = Path(image_path)

    # Check symlinks FIRST (before exists/is_file) for defensive security.
    # A symlink to a valid file passes exists() and is_file(), so checking
    # symlink last would give a less informative error message.
    if path.is_symlink():
        raise ImageValidationError(
            f"Symlinks are not allowed for security: {image_path}"
        )

    if not path.exists():
        raise ImageValidationError(f"Image file not found: {image_path}")

    if not path.is_file():
        raise ImageValidationError(
            f"Image path is not a file: {image_path}"
        )

    ext = path.suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        msg = (
            f"Unsupported image extension '{ext}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}"
        )
        if policy == "strict":
            raise ImageValidationError(msg)
        print(f"⚠ {msg}")

    file_size = path.stat().st_size
    if file_size > MAX_IMAGE_SIZE:
        msg = f"Image too large ({file_size} bytes). Max: {MAX_IMAGE_SIZE} bytes"
        if policy == "strict":
            raise ImageValidationError(msg)
        print(f"⚠ {msg}")

    return path.resolve()


def copy_image_to_public(
    image_path: str, project_root: Path, policy: str = "strict"
) -> str:
    """Copy image to Remotion's public/ folder with a sanitized name.

    Args:
        image_path: Path to the source image.
        project_root: Path to the remotion-project directory.
        policy: Validation policy.

    Returns:
        The sanitized filename (e.g. "image_a1b2c3d4.png").

    Raises:
        ImageValidationError: If copy fails.
    """
    resolved = validate_image_path(image_path, policy)
    ext = resolved.suffix.lower()
    short_id = uuid.uuid4().hex[:8]
    safe_filename = f"image_{short_id}{ext}"

    public_dir = project_root / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    dest = public_dir / safe_filename
    try:
        shutil.copy2(str(resolved), str(dest))
    except OSError as e:
        raise ImageValidationError(f"Failed to copy image to public/: {e}")

    return safe_filename


def generate_image_context(
    image_filename: str, custom_description: str | None = None
) -> str:
    """Generate LLM prompt context describing how to use the image in Remotion.

    Args:
        image_filename: Sanitized filename in public/ (e.g. "image_a1b2c3d4.png").
        custom_description: Optional user-provided description of the image.

    Returns:
        Formatted context string for injection into the LLM prompt.
    """
    description_line = ""
    if custom_description:
        description_line = f"\nImage description: {custom_description}\n"

    return f"""
## Image Asset Available

An image file has been placed in the Remotion project's public/ folder.
Filename: `{image_filename}`
{description_line}
### How to use the image in your component:

1. Import Img and staticFile:
   ```tsx
   import {{ Img }} from 'remotion';
   import {{ staticFile }} from 'remotion';
   ```

2. Reference the image:
   ```tsx
   <Img src={{staticFile('{image_filename}')}} style={{{{width: 1280, height: 720}}}} />
   ```

3. You can animate the image using interpolate() on opacity, scale, or position:
   ```tsx
   const scale = interpolate(
     frame, [0, 30], [0.8, 1], {{extrapolateRight: 'clamp'}}
   );
   <Img
     src={{staticFile('{image_filename}')}}
     style={{{{transform: `scale(${{scale}})`}}}}
   />
   ```

IMPORTANT: You MUST use the image in the animation.
Use `staticFile('{image_filename}')` — do NOT use any
other path or URL.
"""
