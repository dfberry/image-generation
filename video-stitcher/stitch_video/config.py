"""Configuration and presets for stitch_video"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class QualityPreset(Enum):
    """Quality presets matching the sibling animation projects."""

    LOW = (480, 15)    # 480p, 15fps
    MEDIUM = (720, 30)  # 720p, 30fps
    HIGH = (1080, 60)  # 1080p, 60fps

    @property
    def height(self) -> int:
        return self.value[0]

    @property
    def fps(self) -> int:
        return self.value[1]

    @property
    def width(self) -> int:
        """16:9 width for the given height."""
        return int(self.height * 16 / 9)


class TransitionType(Enum):
    """Supported transition effects between clips."""

    NONE = "none"
    FADE_TO_BLACK = "fade_to_black"
    CROSSFADE = "crossfade"


@dataclass
class ClipConfig:
    """Configuration for a single clip in the stitch sequence."""

    path: Path
    transition: TransitionType = TransitionType.NONE
    transition_duration: float = 1.0
    title_card: Optional[str] = None
    title_duration: float = 3.0

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.transition, str):
            self.transition = TransitionType(self.transition)


@dataclass
class Config:
    """Runtime configuration for video stitching.

    Attributes:
        quality: Video quality preset (LOW, MEDIUM, HIGH).
        output_dir: Default directory for output files.
        transition: Default transition between clips.
        transition_duration: Default transition duration in seconds.
    """

    quality: QualityPreset = QualityPreset.MEDIUM
    output_dir: Path = field(default_factory=lambda: Path("outputs"))
    transition: TransitionType = TransitionType.NONE
    transition_duration: float = 1.0

    def __post_init__(self):
        if isinstance(self.quality, str):
            self.quality = QualityPreset[self.quality.upper()]
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if isinstance(self.transition, str):
            self.transition = TransitionType(self.transition)
