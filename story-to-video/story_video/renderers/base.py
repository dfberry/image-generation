"""Abstract base renderer for scene rendering."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..models import RenderResult, Scene


class BaseRenderer(ABC):
    """Abstract base class for scene renderers."""

    def __init__(self, output_dir: Path, quality: str = "medium"):
        self.output_dir = output_dir
        self.quality = quality
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def is_available(self) -> tuple[bool, Optional[str]]:
        """Check if this renderer is available (tools installed, etc.)."""
        pass

    @abstractmethod
    def render(self, scene: Scene) -> RenderResult:
        """Render a scene and return the result."""
        pass

    def _get_output_path(self, scene: Scene, extension: str = ".mp4") -> Path:
        """Generate output path for a scene."""
        return self.output_dir / f"scene_{scene.scene_number:03d}{extension}"
