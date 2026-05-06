"""SDXL Base 1.0 provider - high-detail image generation.

Friendly name: 'precise'
Model: stabilityai/stable-diffusion-xl-base-1.0
License: CreativeML Open RAIL++-M

Supports both text-to-image and img2img (when config.input_image is set).
"""

from __future__ import annotations

import gc
import logging
from typing import Optional

from PIL import Image

from providers.base import BaseProvider, GenerationConfig

logger = logging.getLogger(__name__)

# Lazy imports populated on first load
torch = None
diffusers = None
DiffusionPipeline = None
StableDiffusionXLImg2ImgPipeline = None


def _ensure_imports() -> None:
    global torch, diffusers, DiffusionPipeline, StableDiffusionXLImg2ImgPipeline
    if torch is None:
        import torch as _torch
        torch = _torch
    if diffusers is None:
        import diffusers as _diffusers
        diffusers = _diffusers
    if DiffusionPipeline is None:
        from diffusers import DiffusionPipeline as _DP
        DiffusionPipeline = _DP
    if StableDiffusionXLImg2ImgPipeline is None:
        from diffusers import StableDiffusionXLImg2ImgPipeline as _Img2Img
        StableDiffusionXLImg2ImgPipeline = _Img2Img


class SDXLProvider(BaseProvider):
    """Stable Diffusion XL Base 1.0 - high-detail, versatile generation."""

    _MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

    def __init__(self) -> None:
        self._pipeline: Optional[object] = None
        self._img2img_pipeline: Optional[object] = None
        self._device: Optional[str] = None

    @property
    def friendly_name(self) -> str:
        return "precise"

    @property
    def model_id(self) -> str:
        return self._MODEL_ID

    @property
    def description(self) -> str:
        return "High detail & versatility - best for photorealistic and detailed scenes"

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def load(self, device: str) -> None:
        _ensure_imports()
        logger.info("Loading SDXL base model (first run downloads ~7 GB)...")
        dtype = torch.float16 if device in ("cuda", "mps") else torch.float32
        try:
            pipe = DiffusionPipeline.from_pretrained(
                self._MODEL_ID,
                torch_dtype=dtype,
                use_safetensors=True,
                variant="fp16" if device in ("cuda", "mps") else None,
            )
        except (OSError, ConnectionError) as exc:
            raise RuntimeError(
                f"Could not download {self._MODEL_ID}. Check your internet connection and try again."
            ) from exc
        except Exception as exc:
            if "requests" in type(exc).__module__:
                raise RuntimeError(
                    f"Could not download {self._MODEL_ID}. Check your internet connection and try again."
                ) from exc
            raise
        pipe.safety_checker = None

        if device == "mps":
            pipe.enable_model_cpu_offload()
        elif device == "cpu":
            pipe.to("cpu")
        else:
            pipe.to(device)

        # Performance optimizations
        if device == "cuda" and hasattr(torch, "compile"):
            pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead")
        xformers_fn = getattr(pipe, "enable_xformers_memory_efficient_attention", None)
        if xformers_fn is not None:
            try:
                xformers_fn()
            except Exception:
                pipe.enable_attention_slicing()
        else:
            pipe.enable_attention_slicing()

        self._pipeline = pipe
        self._device = device

    def generate(self, config: GenerationConfig) -> Image.Image:
        if not self.is_loaded:
            raise RuntimeError("SDXL provider not loaded. Call load() first.")
        _ensure_imports()

        if config.scheduler:
            self._apply_scheduler(config.scheduler)

        generator = None
        if config.seed is not None:
            gen_device = "cpu" if self._device in ("cpu", "mps") else self._device
            generator = torch.Generator(device=gen_device).manual_seed(config.seed)

        # img2img path
        if config.input_image is not None:
            return self._generate_img2img(config, generator)

        # text-to-image path (unchanged)
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

    def _generate_img2img(self, config: GenerationConfig, generator) -> Image.Image:
        """Generate using img2img pipeline with input image + strength."""
        img2img_pipe = self._get_img2img_pipeline()

        # Resize input image to target dimensions if they don't match
        input_image = config.input_image.convert("RGB")
        if input_image.size != (config.width, config.height):
            logger.warning(
                "Input image size %s differs from target %dx%d — resizing.",
                input_image.size, config.width, config.height,
            )
            input_image = input_image.resize(
                (config.width, config.height), Image.LANCZOS
            )

        result = img2img_pipe(
            prompt=config.prompt,
            negative_prompt=config.negative_prompt,
            image=input_image,
            strength=config.strength,
            num_inference_steps=config.steps,
            guidance_scale=config.guidance_scale,
            generator=generator,
        )
        return result.images[0]

    def _get_img2img_pipeline(self):
        """Lazily create img2img pipeline sharing components with txt2img."""
        if self._img2img_pipeline is not None:
            return self._img2img_pipeline

        # Share VAE, text encoders, tokenizers, and UNet from existing pipeline
        pipe = self._pipeline
        img2img_pipe = StableDiffusionXLImg2ImgPipeline(
            vae=pipe.vae,
            text_encoder=pipe.text_encoder,
            text_encoder_2=pipe.text_encoder_2,
            tokenizer=pipe.tokenizer,
            tokenizer_2=pipe.tokenizer_2,
            unet=pipe.unet,
            scheduler=pipe.scheduler,
        )
        img2img_pipe.safety_checker = None

        # Apply same attention optimization
        xformers_fn = getattr(img2img_pipe, "enable_xformers_memory_efficient_attention", None)
        if xformers_fn is not None:
            try:
                xformers_fn()
            except Exception:
                img2img_pipe.enable_attention_slicing()
        else:
            img2img_pipe.enable_attention_slicing()

        self._img2img_pipeline = img2img_pipe
        return img2img_pipe

    def cleanup(self) -> None:
        _ensure_imports()
        if self._img2img_pipeline is not None:
            del self._img2img_pipeline
            self._img2img_pipeline = None
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        mps_backend = getattr(torch.backends, "mps", None)
        if mps_backend is not None and mps_backend.is_available():
            torch.mps.empty_cache()
        dynamo = getattr(torch, "_dynamo", None)
        if self._device == "cuda" and dynamo is not None:
            dynamo.reset()
        self._device = None

    def _apply_scheduler(self, scheduler_name: str) -> None:
        """Override the pipeline's scheduler by name."""
        _ensure_imports()
        scheduler_cls = getattr(diffusers, scheduler_name, None)
        if scheduler_cls is None:
            raise ValueError(f"Unknown scheduler: {scheduler_name}")
        cfg = getattr(self._pipeline.scheduler, "config", {})
        if not isinstance(cfg, dict):
            cfg = {}
        if scheduler_name == "DPMSolverMultistepScheduler":
            cfg["use_karras_sigmas"] = True
        self._pipeline.scheduler = scheduler_cls.from_config(cfg)
