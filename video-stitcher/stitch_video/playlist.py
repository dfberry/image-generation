"""Playlist loader — reads JSON or YAML playlist files into ClipConfig lists."""

import json
import logging
from pathlib import Path
from typing import List

import yaml

from stitch_video.config import ClipConfig, TransitionType
from stitch_video.errors import PlaylistError

logger = logging.getLogger(__name__)


def load_playlist(playlist_path: Path, base_dir: Path = None) -> List[ClipConfig]:
    """Load a playlist file (JSON or YAML) and return a list of ClipConfigs.

    Args:
        playlist_path: Path to the playlist file.
        base_dir: Base directory for resolving relative clip paths.
                  Defaults to the playlist file's parent directory.

    Returns:
        List of ClipConfig objects in order.

    Raises:
        PlaylistError: If the file can't be parsed or is invalid.
    """
    if base_dir is None:
        base_dir = playlist_path.parent

    if not playlist_path.exists():
        raise PlaylistError(f"Playlist file not found: {playlist_path}")

    text = playlist_path.read_text(encoding="utf-8")
    suffix = playlist_path.suffix.lower()

    try:
        if suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text)
        elif suffix == ".json":
            data = json.loads(text)
        else:
            raise PlaylistError(
                f"Unsupported playlist format: {suffix} (use .json, .yaml, or .yml)"
            )
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise PlaylistError(f"Failed to parse playlist: {e}")

    if not isinstance(data, dict) or "clips" not in data:
        raise PlaylistError("Playlist must be a mapping with a 'clips' key")

    clips_data = data["clips"]
    if not isinstance(clips_data, list) or len(clips_data) == 0:
        raise PlaylistError("Playlist 'clips' must be a non-empty list")

    clips: List[ClipConfig] = []
    for i, entry in enumerate(clips_data):
        if isinstance(entry, str):
            clip_path = _resolve_path(entry, base_dir)
            clips.append(ClipConfig(path=clip_path))
        elif isinstance(entry, dict):
            if "path" not in entry:
                raise PlaylistError(f"Clip {i} missing required 'path' field")
            clip_path = _resolve_path(entry["path"], base_dir)
            transition = TransitionType(entry.get("transition", "none"))
            clips.append(
                ClipConfig(
                    path=clip_path,
                    transition=transition,
                    transition_duration=float(
                        entry.get("transition_duration", 1.0)
                    ),
                    title_card=entry.get("title_card"),
                    title_duration=float(entry.get("title_duration", 3.0)),
                )
            )
        else:
            raise PlaylistError(f"Clip {i} must be a string path or a mapping")

    logger.info(f"Loaded playlist with {len(clips)} clips from {playlist_path}")
    return clips


def _resolve_path(raw: str, base_dir: Path) -> Path:
    """Resolve a clip path relative to base_dir if not absolute."""
    p = Path(raw)
    if not p.is_absolute():
        p = base_dir / p
    return p.resolve()
