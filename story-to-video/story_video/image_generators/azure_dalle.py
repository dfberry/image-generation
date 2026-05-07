"""Azure OpenAI DALL-E 3 image generator."""

import logging
import os
from pathlib import Path
from typing import Optional

import requests
from openai import AzureOpenAI

from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)

ENV_ENDPOINT = "STORY_VIDEO_AZURE_OPENAI_ENDPOINT"
ENV_API_KEY = "STORY_VIDEO_AZURE_OPENAI_API_KEY"
ENV_DEPLOYMENT = "STORY_VIDEO_AZURE_OPENAI_DEPLOYMENT"


class AzureDalleGenerator(ImageGeneratorBase):
    """Generates images using Azure OpenAI DALL-E 3 API."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: str = "2024-02-01",
    ):
        self._endpoint = endpoint or os.environ.get(ENV_ENDPOINT, "")
        self._api_key = api_key or os.environ.get(ENV_API_KEY, "")
        self._deployment = deployment or os.environ.get(ENV_DEPLOYMENT, "")
        self._api_version = api_version

    @property
    def name(self) -> str:
        return "azure-dalle"

    def is_available(self) -> tuple[bool, Optional[str]]:
        if not self._endpoint:
            return False, f"{ENV_ENDPOINT} not set"
        if not self._api_key:
            return False, f"{ENV_API_KEY} not set"
        if not self._deployment:
            return False, f"{ENV_DEPLOYMENT} not set"
        return True, None

    def generate(self, prompt: str, output_path: Path, **kwargs) -> Path:
        available, reason = self.is_available()
        if not available:
            raise RuntimeError(f"Azure DALL-E not available: {reason}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        size = kwargs.get("size", "1024x1024")
        quality = kwargs.get("quality", "standard")

        client = AzureOpenAI(
            azure_endpoint=self._endpoint,
            api_key=self._api_key,
            api_version=self._api_version,
        )

        logger.info(f"Requesting DALL-E 3 image: {prompt[:80]}...")
        try:
            response = client.images.generate(
                model=self._deployment,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
        except Exception as e:
            raise RuntimeError(f"Azure DALL-E 3 API call failed: {e}") from e

        if not response.data:
            raise RuntimeError("Azure DALL-E 3 returned no image data")

        image_url = response.data[0].url
        if not image_url:
            raise RuntimeError("Azure DALL-E 3 returned empty image URL")

        # Download the generated image
        logger.debug(f"Downloading generated image to {output_path}")
        try:
            img_response = requests.get(image_url, timeout=60)
            img_response.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Failed to download DALL-E image: {e}") from e

        output_path.write_bytes(img_response.content)

        if output_path.stat().st_size == 0:
            raise RuntimeError(f"Downloaded DALL-E image is 0 bytes: {output_path}")

        logger.info(f"Azure DALL-E 3 image saved: {output_path}")
        return output_path
