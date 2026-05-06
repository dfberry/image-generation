"""FLUX.1-schnell provider - creative, prompt-adherent generation.

Friendly name: 'creative'
Model: black-forest-labs/FLUX.1-schnell
License: Apache 2.0
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
FluxPipeline = None


def _ensure_imports() -> None:
    global torch, FluxPipeline
    if torch is None:
        import torch as _torch
        torch = _torch
    if FluxPipeline is None:
        from diffusers import FluxPipeline as _FP
        FluxPipeline = _FP


class FluxProvider(BaseProvider):
    """FLUX.1-schnell - excellent prompt adherence with artistic flair."""

    _MODEL_ID = "black-forest-labs/FLUX.1-schnell"

    def __init__(self) -> None:
        self._pipeline: Optional[object] = None
        self._device: Optional[str] = None

    @property
    def friendly_name(self) -> str:
        return "creative"

    @property
    def model_id(self) -> str:
        return self._MODEL_ID

    @property
    def description(self) -> str:
        return "Best prompt adherence & artistic quality - great for creative compositions"

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def load(self, device: str) -> None:
        _ensure_imports()
        logger.info("Loading FLUX.1-schnell (first run downloads ~12 GB)...")
        dtype = torch.bfloat16 if device in ("cuda", "mps") else torch.float32
        pipe = FluxPipeline.from_pretrained(
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
            raise RuntimeError("FLUX provider not loaded. Call load() first.")
        _ensure_imports()

        generator = None
        if config.seed is not None:
            gen_device = "cpu" if self._device in ("cpu", "mps") else self._device
            generator = torch.Generator(device=gen_device).manual_seed(config.seed)

        # FLUX.1-schnell uses fewer steps (4) and no CFG
        steps = min(config.steps, 4) if config.steps > 4 else config.steps
        result = self._pipeline(
            prompt=config.prompt,
            num_inference_steps=steps,
            guidance_scale=0.0,
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
