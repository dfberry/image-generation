"""Real-ESRGAN upscaling provider.

Uses the RRDBNet architecture from basicsr with Real-ESRGAN weights
for 2x and 4x super-resolution. Weights are downloaded from HuggingFace
on first use.
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from providers.enhancer import BaseEnhancer, EnhanceConfig

logger = logging.getLogger(__name__)

# HuggingFace weight URLs for Real-ESRGAN models
_WEIGHT_URLS = {
    4: "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    2: "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
}


class RealESRGANProvider(BaseEnhancer):
    """Real-ESRGAN super-resolution provider.

    Wraps the realesrgan Python package for high-quality image upscaling.
    Supports 2x and 4x scale factors.
    """

    def __init__(self):
        self._upsampler = None
        self._scale: Optional[int] = None
        self._device: Optional[str] = None

    @property
    def friendly_name(self) -> str:
        return "Real-ESRGAN"

    @property
    def model_id(self) -> str:
        return "xinntao/Real-ESRGAN"

    @property
    def supported_scales(self) -> list[int]:
        return [2, 4]

    @property
    def is_loaded(self) -> bool:
        return self._upsampler is not None

    def load(self, device: str, scale: int = 4) -> None:
        """Load Real-ESRGAN model weights.

        Downloads weights on first use (~67MB for 4x, ~67MB for 2x).
        """
        if scale not in self.supported_scales:
            raise ValueError(
                f"Unsupported scale factor: {scale}. "
                f"Supported: {self.supported_scales}"
            )

        try:
            import torch
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
        except ImportError as exc:
            raise RuntimeError(
                "Real-ESRGAN dependencies not installed. "
                "Run: pip install realesrgan basicsr"
            ) from exc

        self._scale = scale
        self._device = device

        # Configure RRDBNet architecture based on scale
        if scale == 4:
            model = RRDBNet(
                num_in_ch=3, num_out_ch=3, num_feat=64,
                num_block=23, num_grow_ch=32, scale=4,
            )
        else:
            model = RRDBNet(
                num_in_ch=3, num_out_ch=3, num_feat=64,
                num_block=23, num_grow_ch=32, scale=2,
            )

        model_path = _WEIGHT_URLS[scale]

        # Determine half precision based on device
        use_half = device in ("cuda",)

        try:
            logger.info(
                "Loading Real-ESRGAN %dx model (first run downloads ~67MB)...",
                scale,
            )
            self._upsampler = RealESRGANer(
                scale=scale,
                model_path=model_path,
                model=model,
                tile=0,
                tile_pad=10,
                pre_pad=0,
                half=use_half,
                device=device,
            )
        except Exception as exc:
            error_msg = str(exc).lower()
            if "url" in error_msg or "download" in error_msg or "connection" in error_msg:
                raise RuntimeError(
                    "Could not download upscaling model. Check your internet connection."
                ) from exc
            raise RuntimeError(
                f"Failed to load Real-ESRGAN model: {exc}"
            ) from exc

    def enhance(self, config: EnhanceConfig) -> Image.Image:
        """Upscale an image using Real-ESRGAN.

        Args:
            config: Enhancement configuration with input image and scale.

        Returns:
            Upscaled PIL Image.
        """
        if self._upsampler is None:
            raise RuntimeError(
                "Model not loaded. Call load() before enhance()."
            )

        # Convert PIL Image to numpy array (BGR for OpenCV compatibility)
        img = config.input_image.convert("RGB")
        img_array = np.array(img)
        # Convert RGB to BGR (Real-ESRGAN uses OpenCV BGR format)
        img_bgr = img_array[:, :, ::-1]

        try:
            output_bgr, _ = self._upsampler.enhance(img_bgr, outscale=config.scale)
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                raise RuntimeError(
                    "Out of GPU memory during upscaling. "
                    "Try a smaller image or use --cpu."
                ) from exc
            raise RuntimeError(
                f"Upscaling failed: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Upscaling failed: {exc}"
            ) from exc

        # Convert BGR back to RGB and return as PIL Image
        output_rgb = output_bgr[:, :, ::-1]
        return Image.fromarray(output_rgb)

    def cleanup(self) -> None:
        """Free GPU/CPU memory held by the model."""
        if self._upsampler is not None:
            del self._upsampler
            self._upsampler = None

        self._scale = None
        self._device = None
        gc.collect()

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            mps_backend = getattr(torch.backends, "mps", None)
            if mps_backend is not None and mps_backend.is_available():
                torch.mps.empty_cache()
        except ImportError:
            pass
