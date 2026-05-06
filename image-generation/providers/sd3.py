"""Stable Diffusion 3 Medium provider - fast, good quality generation.

Friendly name: 'fast'
Model: stabilityai/stable-diffusion-3-medium-diffusers
License: Stability AI Community License
"""

from __future__ import annotations

import gc
import logging
from typing import Optional

from PIL import Image

from providers.base import BaseProvider, GenerationConfig

logger = logging.getLogger(__name__)

# Lazy imports
torch = None
StableDiffusion3Pipeline = None


def _ensure_imports() -> None:
    global torch, StableDiffusion3Pipeline
    if torch is None:
        import torch as _torch
        torch = _torch
    if StableDiffusion3Pipeline is None:
        from diffusers import StableDiffusion3Pipeline as _SD3
        StableDiffusion3Pipeline = _SD3


class SD3Provider(BaseProvider):
    """Stable Diffusion 3 Medium - fast generation with good quality."""

    _MODEL_ID = "stabilityai/stable-diffusion-3-medium-diffusers"

    def __init__(self) -> None:
        self._pipeline: Optional[object] = None
        self._device: Optional[str] = None

    @property
    def friendly_name(self) -> str:
        return "fast"

    @property
    def model_id(self) -> str:
        return self._MODEL_ID

    @property
    def description(self) -> str:
        return "Quick generation with good quality - balanced speed and detail"

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def load(self, device: str) -> None:
        _ensure_imports()
        logger.info("Loading SD3 Medium (first run downloads ~5 GB)...")
        dtype = torch.float16 if device in ("cuda", "mps") else torch.float32
        pipe = StableDiffusion3Pipeline.from_pretrained(
            self._MODEL_ID,
            torch_dtype=dtype,
        )

        if device == "mps":
            pipe.enable_model_cpu_offload()
        elif device == "cpu":
            pipe.to("cpu")
        else:
            pipe.to(device)

        pipe.enable_attention_slicing()

        self._pipeline = pipe
        self._device = device

    def generate(self, config: GenerationConfig) -> Image.Image:
        if not self.is_loaded:
            raise RuntimeError("SD3 provider not loaded. Call load() first.")
        _ensure_imports()

        generator = None
        if config.seed is not None:
            gen_device = "cpu" if self._device in ("cpu", "mps") else self._device
            generator = torch.Generator(device=gen_device).manual_seed(config.seed)

        result = self._pipeline(
            prompt=config.prompt,
            negative_prompt=config.negative_prompt,
            num_inference_steps=config.steps,
            guidance_scale=config.guidance_scale,
            width=config.width,
            height=config.height,
            generator=generator,
        )
        return result.images[0]

    def cleanup(self) -> None:
        _ensure_imports()
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        mps_backend = getattr(torch.backends, "mps", None)
        if mps_backend is not None and mps_backend.is_available():
            torch.mps.empty_cache()
        self._device = None
