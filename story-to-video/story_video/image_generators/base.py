"""Abstract base class for image generation backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class ImageGeneratorBase(ABC):
    """Interface for pluggable image generation backends.

    Each implementation generates a still image from a text prompt
    and saves it to the specified output path.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this generator (e.g., 'local-sdxl', 'azure-dalle')."""

    @abstractmethod
    def is_available(self) -> tuple[bool, Optional[str]]:
        """Check if this generator is ready to use.

        Returns:
            (True, None) if available, or (False, reason) if not.
        """

    @abstractmethod
    def generate(self, prompt: str, output_path: Path, **kwargs) -> Path:
        """Generate an image from a text prompt.

        Args:
            prompt: The image generation prompt.
            output_path: Where to save the generated image.
            **kwargs: Backend-specific options.

        Returns:
            Path to the generated image file.

        Raises:
            RuntimeError: If generation fails.
        """
