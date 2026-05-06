"""Provider registry - maps friendly names to provider implementations."""

from __future__ import annotations

from typing import Dict, Type

from providers.base import BaseProvider
from providers.flux import FluxProvider
from providers.sd3 import SD3Provider
from providers.sdxl import SDXLProvider

# Friendly name -> provider class
_REGISTRY: Dict[str, Type[BaseProvider]] = {
    "creative": FluxProvider,
    "precise": SDXLProvider,
    "balanced": SD3Provider,
}

# Human-readable descriptions for --help output
FRIENDLY_NAMES: Dict[str, str] = {
    "creative": "FLUX.1 - best prompt adherence, artistic",
    "precise": "SDXL Base 1.0 - high detail (default)",
    "balanced": "SD3 Medium - good balance of speed and quality",
}

# Default model when --model is not specified
DEFAULT_MODEL = "precise"


def get_provider(name: str) -> BaseProvider:
    """Instantiate a provider by its friendly name.

    Args:
        name: One of 'creative', 'precise', 'balanced'.

    Returns:
        An unloaded provider instance.

    Raises:
        ValueError: If name is not recognized.
    """
    name_lower = name.lower().strip()
    if name_lower not in _REGISTRY:
        valid = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(
            f"Unknown model '{name}'. Available models: {valid}"
        )
    return _REGISTRY[name_lower]()


def list_providers() -> Dict[str, str]:
    """Return dict of friendly_name -> description for all registered providers."""
    return dict(FRIENDLY_NAMES)
