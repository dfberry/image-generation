"""Audio validation, copying, and LLM context generation for audio input support."""

import shutil
import uuid
from pathlib import Path
from typing import Optional

from remotion_gen.config import (
    ALLOWED_AUDIO_EXTENSIONS,
    MAX_AUDIO_SIZE,
    MAX_AUDIO_DURATION_SECONDS,
)
from remotion_gen.errors import AudioValidationError


def validate_audio_path(audio_path: str, policy: str = "strict") -> Path:
    """Validate that an audio path is safe and points to a supported file.

    Args:
        audio_path: Path to the audio file.
        policy: "strict" raises on all issues, "warn" prints warnings,
                "ignore" skips validation entirely.

    Returns:
        Resolved Path object.

    Raises:
        AudioValidationError: If validation fails under strict policy.
    """
    if policy == "ignore":
        return Path(audio_path).resolve()

    path = Path(audio_path)

    # Check symlinks FIRST (before exists/is_file) for defensive security.
    if path.is_symlink():
        raise AudioValidationError(
            f"Symlinks are not allowed for security: {audio_path}"
        )

    if not path.exists():
        raise AudioValidationError(f"Audio file not found: {audio_path}")

    if not path.is_file():
        raise AudioValidationError(f"Audio path is not a file: {audio_path}")

    ext = path.suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        msg = (
            f"Unsupported audio extension '{ext}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}"
        )
        if policy == "strict":
            raise AudioValidationError(msg)
        print(f"⚠ {msg}")

    file_size = path.stat().st_size
    if file_size > MAX_AUDIO_SIZE:
        size_mb = file_size / (1024 * 1024)
        msg = f"Audio too large ({size_mb:.1f} MB). Max: {MAX_AUDIO_SIZE / (1024 * 1024):.0f} MB"
        if policy == "strict":
            raise AudioValidationError(msg)
        print(f"⚠ {msg}")

    # Note: Duration validation requires audio library (pydub/ffprobe)
    # Deferred to Phase 1 to keep dependencies minimal
    # For now, rely on file size as proxy (200MB @ 320kbps ≈ 1.5 hours)

    return path.resolve()


def copy_audio_to_public(
    audio_path: str,
    project_root: Path,
    policy: str = "strict",
    prefix: str = "audio",
) -> str:
    """Copy audio to Remotion's public/ folder with a sanitized name.

    Args:
        audio_path: Path to the source audio.
        project_root: Path to the remotion-project directory.
        policy: Validation policy.
        prefix: Filename prefix (e.g. "audio", "music", "sfx_0").

    Returns:
        The sanitized filename (e.g. "audio_a1b2c3d4.mp3").

    Raises:
        AudioValidationError: If copy fails.
    """
    resolved = validate_audio_path(audio_path, policy)
    ext = resolved.suffix.lower()
    short_id = uuid.uuid4().hex[:8]
    safe_filename = f"{prefix}_{short_id}{ext}"

    public_dir = project_root / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    dest = public_dir / safe_filename
    try:
        shutil.copy2(str(resolved), str(dest))
    except OSError as e:
        raise AudioValidationError(f"Failed to copy audio to public/: {e}")

    return safe_filename


def generate_audio_context(
    audio_files: dict[str, str],
    music_volume: float,
    narration_volume: float,
) -> str:
    """Generate LLM prompt context describing how to use audio in Remotion.

    Args:
        audio_files: Dict mapping audio type to filename.
                     Keys: "narration", "music", "sfx_0", "sfx_1", etc.
        music_volume: Background music volume (0.0-1.0).
        narration_volume: Narration volume (0.0-1.0).

    Returns:
        Formatted context string for injection into the LLM prompt.
    """
    if not audio_files:
        return ""

    lines = ["## Audio Assets Available", ""]
    lines.append(
        "The following audio files have been placed in the Remotion project's public/ folder."
    )
    lines.append("")

    if "narration" in audio_files:
        lines.append("### Narration")
        lines.append(f"- Filename: `{audio_files['narration']}`")
        lines.append(
            f"- Use: `<Audio src={{staticFile('{audio_files['narration']}')}} volume={{{narration_volume}}} />`"
        )
        lines.append("")

    if "music" in audio_files:
        lines.append("### Background Music")
        lines.append(f"- Filename: `{audio_files['music']}`")
        lines.append(
            f"- Use: `<Audio src={{staticFile('{audio_files['music']}')}} volume={{{music_volume}}} loop />`"
        )
        lines.append("")

    sfx_files = {
        k: v for k, v in audio_files.items() if k.startswith("sfx_")
    }
    if sfx_files:
        lines.append("### Sound Effects")
        for key in sorted(sfx_files.keys()):
            filename = sfx_files[key]
            lines.append(
                f"- `{filename}` — Use inside <Sequence> for timed playback"
            )
        lines.append("")

    lines.append("IMPORTANT: You MUST include all provided audio files in the component.")
    lines.append("Use staticFile('exact_filename') — do NOT use any other path.")
    lines.append(
        f"Set narration volume to {narration_volume} and music volume to {music_volume}."
    )

    return "\n".join(lines)
