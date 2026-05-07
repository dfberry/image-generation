"""Shared tool discovery for sibling tools."""
import os
import shutil
from pathlib import Path
from typing import Optional

# Default repo root (sibling directory of story-to-video)
_REPO_ROOT = Path(__file__).parent.parent.parent


def find_tool(name: str, env_var: Optional[str] = None, sibling_path: Optional[str] = None) -> Optional[str]:
    """Find a tool by checking: env var → PATH → sibling directory.

    Args:
        name: CLI command name (e.g., "remotion-gen", "stitch-video")
        env_var: Optional env var override (e.g., "REMOTION_GEN_PATH")
        sibling_path: Optional relative path from repo root (e.g., "remotion-animation")
    """
    # 1. Environment variable override
    if env_var:
        path = os.environ.get(env_var)
        if path and (Path(path).exists() or shutil.which(path)):
            return path

    # 2. Check PATH
    if shutil.which(name):
        return name

    # 3. Check sibling directory
    if sibling_path:
        full_path = _REPO_ROOT / sibling_path
        if full_path.exists():
            return str(full_path)

    return None


def find_tool_file(relative_path: str, env_var: Optional[str] = None) -> Optional[Path]:
    """Find a specific file in sibling tools (e.g., generate.py).

    Args:
        relative_path: Path relative to repo root (e.g., "image-generation/generate.py")
        env_var: Optional env var override
    """
    if env_var:
        path = os.environ.get(env_var)
        if path and Path(path).exists():
            return Path(path)

    full_path = _REPO_ROOT / relative_path
    if full_path.exists():
        return full_path

    return None
