"""Configuration and presets for story-to-video."""

from typing import Literal

# Default values
DEFAULT_QUALITY: Literal["low", "medium", "high"] = "medium"
DEFAULT_SCENE_DURATION = 30
DEFAULT_TRANSITION: Literal["none", "fade_to_black", "crossfade"] = "fade_to_black"
DEFAULT_PROVIDER: Literal["ollama", "openai", "azure"] = "ollama"
DEFAULT_MODEL = "llama3.2"

# Timeouts for rendering (seconds)
# CPU-only inference with 32B models needs ~150s for TSX generation + render
RENDER_TIMEOUT_IMAGE = 300
RENDER_TIMEOUT_REMOTION = 600
RENDER_TIMEOUT_MANIM = 300
RENDER_TIMEOUT_STITCH = 600

# LLM configuration
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"  # Dummy key for Ollama
