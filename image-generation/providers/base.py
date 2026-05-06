"""Base provider interface for image generation models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image


@dataclass
class GenerationConfig:
    """Configuration for a single image generation request."""

    prompt: str
    negative_prompt: Optional[str] = None
    width: int = 1024
    height: int = 1024
    steps: int = 30
    guidance_scale: float = 7.5
    seed: Optional[int] = None
    scheduler: Optional[str] = None
    input_image: Optional[Image.Image] = None
    strength: float = 0.75
    extras: dict = field(default_factory=dict)


class BaseProvider(ABC):
    """Abstract base class for all image generation providers.

    Each provider wraps a specific diffusion model and exposes a simple
    load -> generate -> cleanup lifecycle. Models are downloaded from
    Hugging Face on first use via diffusers' built-in caching.
    """

    @property
    @abstractmethod
    def friendly_name(self) -> str:
        """User-facing name (e.g., 'creative', 'precise', 'fast')."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Hugging Face model identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short human-readable description of this model's strengths."""
        ...

    @abstractmethod
    def load(self, device: str) -> None:
        """Load model weights onto the given device.

        Downloads from Hugging Face on first use (auto-cached).
        """
        ...

    @abstractmethod
    def generate(self, config: GenerationConfig) -> Image.Image:
        """Generate an image from the given configuration.

        Raises RuntimeError if the model is not loaded.
        """
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """Free GPU/CPU memory held by this provider."""
        ...

    @property
    def is_loaded(self) -> bool:
        """Whether the model is currently loaded and ready."""
        return False
