"""Base enhancer interface for image upscaling/super-resolution models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from PIL import Image


@dataclass
class EnhanceConfig:
    """Configuration for an image enhancement request."""

    input_image: Image.Image
    scale: int = 4
    output_path: Optional[str] = None


class BaseEnhancer(ABC):
    """Abstract base class for image enhancement (upscaling) providers.

    Each enhancer wraps a super-resolution model and exposes a simple
    load -> enhance -> cleanup lifecycle.
    """

    @property
    @abstractmethod
    def friendly_name(self) -> str:
        """User-facing name for this enhancer."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Model identifier (HuggingFace repo or local path)."""
        ...

    @property
    @abstractmethod
    def supported_scales(self) -> list[int]:
        """List of supported upscaling factors (e.g. [2, 4])."""
        ...

    @abstractmethod
    def load(self, device: str, scale: int = 4) -> None:
        """Load model weights onto the given device.

        Args:
            device: Target device ('cuda', 'mps', or 'cpu').
            scale: Upscaling factor to configure the model for.
        """
        ...

    @abstractmethod
    def enhance(self, config: EnhanceConfig) -> Image.Image:
        """Upscale the input image.

        Raises RuntimeError if the model is not loaded.
        """
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """Free GPU/CPU memory held by this enhancer."""
        ...

    @property
    def is_loaded(self) -> bool:
        """Whether the model is currently loaded and ready."""
        return False
