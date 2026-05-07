"""Local SDXL image generator — wraps the existing image-generation/generate.py script."""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..config import RENDER_TIMEOUT_IMAGE
from ..tool_locator import find_tool_file
from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)


class LocalSdxlGenerator(ImageGeneratorBase):
    """Generates images using local Stable Diffusion XL via subprocess."""

    def __init__(self, image_gen_path: Optional[Path] = None):
        self._image_gen_path = image_gen_path or self._find_image_gen()

    @property
    def name(self) -> str:
        return "local-sdxl"

    def _find_image_gen(self) -> Optional[Path]:
        return find_tool_file("image-generation/generate.py", env_var="IMAGE_GEN_PATH")

    def is_available(self) -> tuple[bool, Optional[str]]:
        if not self._image_gen_path or not self._image_gen_path.exists():
            return False, "image-generation/generate.py not found"
        return True, None

    def generate(self, prompt: str, output_path: Path, **kwargs) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(self._image_gen_path),
            "--prompt", prompt,
            "--output", str(output_path),
        ]

        logger.debug(f"Running local SDXL: {' '.join(cmd[:4])}... → {output_path}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RENDER_TIMEOUT_IMAGE,
        )
        logger.debug(f"Local SDXL exited with code {result.returncode}")

        if result.returncode != 0:
            raise RuntimeError(f"Local SDXL generation failed: {result.stderr}")

        if not output_path.exists():
            raise RuntimeError(f"Expected output {output_path} not found after generation")
        if output_path.stat().st_size == 0:
            raise RuntimeError(f"Local SDXL produced 0-byte file: {output_path}")

        return output_path
