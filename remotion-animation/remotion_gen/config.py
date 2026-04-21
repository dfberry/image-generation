"""Configuration and quality presets for Remotion rendering."""

from dataclasses import dataclass


@dataclass
class QualityPreset:
    """Video quality preset configuration."""
    width: int
    height: int
    fps: int
    
    @property
    def resolution_name(self) -> str:
        """Human-readable resolution name."""
        if self.height >= 1080:
            return "1080p"
        elif self.height >= 720:
            return "720p"
        else:
            return "480p"


QUALITY_PRESETS = {
    "low": QualityPreset(width=854, height=480, fps=15),
    "medium": QualityPreset(width=1280, height=720, fps=30),
    "high": QualityPreset(width=1920, height=1080, fps=60),
}

DEFAULT_DURATION_SECONDS = 5
MIN_DURATION_SECONDS = 5
MAX_DURATION_SECONDS = 30

DEFAULT_PROVIDER = "ollama"
