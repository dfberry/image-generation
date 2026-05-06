"""Provider abstraction layer for image generation models.

Supports multiple diffusion models via a unified interface with friendly names:
- 'creative'  -> FLUX.1 (best prompt adherence, artistic)
- 'precise'   -> SDXL Base 1.0 (high detail, current default)
- 'balanced'  -> Stable Diffusion 3 Medium (good balance of speed and quality)
"""

from providers.base import BaseProvider, GenerationConfig
from providers.registry import get_provider, list_providers, FRIENDLY_NAMES

__all__ = [
    "BaseProvider",
    "GenerationConfig",
    "get_provider",
    "list_providers",
    "FRIENDLY_NAMES",
]
