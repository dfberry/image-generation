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

# LLM sampling temperatures per provider.
# Lower temperature for small/local models reduces structural errors.
PROVIDER_TEMPERATURES = {
    "ollama": 0.4,
    "openai": 0.7,
    "azure": 0.7,
}

# Audio configuration
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}
MAX_AUDIO_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_AUDIO_DURATION_SECONDS = 300  # 5 minutes
MAX_TTS_TEXT_LENGTH = 10000  # characters

DEFAULT_TTS_PROVIDER = "edge-tts"
DEFAULT_MUSIC_VOLUME = 0.3
DEFAULT_NARRATION_VOLUME = 1.0

TTS_VOICE_DEFAULTS = {
    "edge-tts": "en-US-GuyNeural",
    "openai": "alloy",
}

TTS_OUTPUT_FORMAT = "mp3"
