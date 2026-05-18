"""Factory for selecting image generation backends by name."""

from typing import Optional

from .base import ImageGeneratorBase

# Registry of known image generator names → constructor functions
_REGISTRY: dict[str, type[ImageGeneratorBase]] = {}

# Default provider for backward compatibility
DEFAULT_IMAGE_PROVIDER = "local"


def _ensure_registry() -> None:
    """Lazily populate the registry to avoid circular imports."""
    if _REGISTRY:
        return

    from .azure_dalle import AzureDalleGenerator
    from .local_sdxl import LocalSdxlGenerator

    _REGISTRY["local"] = LocalSdxlGenerator
    _REGISTRY["azure-dalle"] = AzureDalleGenerator


def get_image_generator(name: Optional[str] = None) -> ImageGeneratorBase:
    """Get an image generator by name.

    Args:
        name: Generator name ('local', 'azure-dalle'). Defaults to 'local'.

    Returns:
        An initialized ImageGeneratorBase instance.

    Raises:
        ValueError: If the name is not recognized.
    """
    _ensure_registry()
    name = name or DEFAULT_IMAGE_PROVIDER

    cls = _REGISTRY.get(name)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(
            f"Unknown image provider '{name}'. Available: {available}"
        )

    return cls()


def list_image_providers() -> list[str]:
    """Return sorted list of registered image provider names."""
    _ensure_registry()
    return sorted(_REGISTRY.keys())
