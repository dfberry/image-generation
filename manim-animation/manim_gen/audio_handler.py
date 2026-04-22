"""Audio validation, copying, and LLM context generation for manim_gen"""

import ast
import logging
import shutil
from pathlib import Path
from typing import Dict, List

from manim_gen.errors import AudioValidationError

logger = logging.getLogger(__name__)

ALLOWED_AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".ogg",
}

MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50 MB per file


def validate_audio_path(audio_path: Path, policy: str = "strict") -> bool:
    """Validate a single audio path for safety and correctness.

    Args:
        audio_path: Path to the audio file
        policy: "strict" (raise on error), "warn" (log warning), "ignore" (skip silently)

    Returns:
        True if the audio is valid, False otherwise

    Raises:
        AudioValidationError: In strict mode when validation fails
    """

    def _handle(msg: str) -> bool:
        if policy == "strict":
            raise AudioValidationError(msg)
        if policy == "warn":
            logger.warning(msg)
        return False

    # Reject symlinks BEFORE resolving — checking after resolve() always
    # sees a real path and the symlink check becomes dead code.
    if audio_path.is_symlink():
        return _handle(f"Symlinks not allowed: {audio_path}")

    resolved = audio_path.resolve()

    if not resolved.exists():
        return _handle(f"Audio file not found: {resolved}")

    if not resolved.is_file():
        return _handle(f"Not a file: {resolved}")

    if resolved.suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
        return _handle(
            f"Unsupported audio format '{resolved.suffix}'. "
            f"Allowed: {sorted(ALLOWED_AUDIO_EXTENSIONS)}"
        )

    # Cache stat result to avoid double syscall
    file_stat = resolved.stat()
    if file_stat.st_size > MAX_AUDIO_SIZE:
        size_mb = file_stat.st_size / (1024 * 1024)
        return _handle(f"Audio file too large ({size_mb:.1f} MB). Max: 50 MB")

    return True


def copy_audio_to_workspace(
    audio_paths: List[Path],
    workspace_dir: Path,
    policy: str = "strict",
) -> Dict[Path, Path]:
    """Copy validated audio files to an isolated workspace directory.

    Each audio file gets a deterministic name: sfx_0_filename.ext, sfx_1_filename.ext, etc.

    Args:
        audio_paths: List of source audio paths
        workspace_dir: Target directory to copy into
        policy: Validation policy ("strict", "warn", "ignore")

    Returns:
        Dict mapping original paths to workspace copies
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    copies: Dict[Path, Path] = {}

    for idx, audio_path in enumerate(audio_paths):
        # Validate the ORIGINAL path (not resolved) so symlink check works
        if not validate_audio_path(audio_path, policy=policy):
            continue

        resolved = audio_path.resolve()
        dest_name = f"sfx_{idx}_{resolved.name}"
        dest = workspace_dir / dest_name
        try:
            shutil.copy2(str(resolved), str(dest))
        except OSError as exc:
            raise AudioValidationError(
                f"Failed to copy audio file '{audio_path}': {exc}"
            ) from exc
        copies[resolved] = dest
        logger.info(f"Copied audio to workspace: {dest_name}")

    return copies


def generate_audio_context(audio_paths: List[Path]) -> str:
    """Generate LLM context block describing available audio files.

    Args:
        audio_paths: Workspace-relative audio paths (after copying)

    Returns:
        Formatted context string for the LLM prompt
    """
    if not audio_paths:
        return ""

    lines = [
        "## Available Sound Effects",
        "The following audio files are available in the working directory.",
        "Use `self.add_sound('filename')` to play them during the scene.",
        "",
        "| File | Format |",
        "|------|--------|",
    ]

    for path in audio_paths:
        ext = path.suffix.upper().lstrip(".")
        lines.append(f"| {path.name} | {ext} |")

    lines.append("")
    lines.append(
        "API: self.add_sound(sound_file, time_offset=0, gain=None)\n"
        "- time_offset: seconds after current scene time to start playback\n"
        "- gain: volume adjustment in dB (negative = quieter, None = original volume)"
    )

    return "\n".join(lines)


def validate_audio_operations(code: str, allowed_filenames: set) -> None:
    """Ensure add_sound() calls only reference provided audio files.

    Args:
        code: Python source code to validate
        allowed_filenames: Set of allowed audio filenames

    Raises:
        AudioValidationError: If validation fails
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise AudioValidationError(f"Cannot parse code for audio validation: {e}")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Match self.add_sound(...)
        if (isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_sound"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"):

            if not node.args:
                raise AudioValidationError(
                    "add_sound() must have a filename argument. "
                    "Expected: self.add_sound('filename.wav')"
                )

            arg = node.args[0]
            if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                raise AudioValidationError(
                    "add_sound() filename must be a string literal, not a variable or expression. "
                    "Expected: self.add_sound('filename.wav')"
                )

            if arg.value not in allowed_filenames:
                raise AudioValidationError(
                    f"add_sound() references unknown file '{arg.value}'. "
                    f"Allowed: {sorted(allowed_filenames)}"
                )
