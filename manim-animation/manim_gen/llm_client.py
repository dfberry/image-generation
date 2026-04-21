"""LLM client for generating Manim scene code"""

import logging
import os
from typing import Optional

from manim_gen.config import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT
from manim_gen.errors import LLMError

logger = logging.getLogger(__name__)

# Default models per provider
DEFAULT_MODELS = {
    "ollama": "llama3",
    "openai": "gpt-4",
}

class LLMClient:
    """Wrapper for Ollama/OpenAI/Azure OpenAI API calls"""

    def __init__(self, provider: str = "ollama"):
        """Initialize LLM client

        Args:
            provider: "ollama" (default, local), "openai", or "azure"

        Raises:
            LLMError: If API credentials are missing (openai/azure only)
        """
        self.provider = provider.lower()

        if self.provider == "ollama":
            self.ollama_host = os.getenv(
                "OLLAMA_HOST", "http://localhost:11434"
            )
        elif self.provider == "azure":
            self.api_key = os.getenv("AZURE_OPENAI_KEY")
            self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

            if not all([self.api_key, self.endpoint, self.deployment]):
                raise LLMError(
                    "Azure OpenAI requires AZURE_OPENAI_KEY, "
                    "AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT"
                )
        elif self.provider == "openai":
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise LLMError("OpenAI requires OPENAI_API_KEY environment variable")
        else:
            raise LLMError(
                f"Unknown provider '{self.provider}'. "
                "Use 'ollama', 'openai', or 'azure'."
            )

        # Lazy import to avoid dependency issues in tests
        self._client = None

    def _get_client(self):
        """Lazy-load OpenAI-compatible client"""
        if self._client is None:
            try:
                if self.provider == "ollama":
                    from openai import OpenAI
                    self._client = OpenAI(
                        base_url=f"{self.ollama_host}/v1",
                        api_key="ollama",
                    )
                elif self.provider == "azure":
                    from openai import AzureOpenAI
                    self._client = AzureOpenAI(
                        api_key=self.api_key,
                        api_version="2024-02-15-preview",
                        azure_endpoint=self.endpoint,
                    )
                else:
                    from openai import OpenAI
                    self._client = OpenAI(api_key=self.api_key)
            except ImportError as e:
                raise LLMError(f"Failed to import openai library: {e}")
        return self._client

    def generate_scene_code(
        self, prompt: str, duration: int, model: Optional[str] = None
    ) -> str:
        """Generate Manim scene code from user prompt

        Args:
            prompt: User's description of desired animation
            duration: Target duration in seconds
            model: Optional model override

        Returns:
            Python code string for Manim scene

        Raises:
            LLMError: If API call fails or returns invalid response
        """
        client = self._get_client()

        # Build user message with duration context
        user_message = (
            f"{FEW_SHOT_EXAMPLES}\n\n"
            f"User request (target duration: {duration} seconds): {prompt}\n\n"
            f"Generate the Python code:"
        )

        # Determine model name
        if self.provider == "azure":
            model_name = self.deployment  # Azure uses deployment name
        else:
            model_name = model or DEFAULT_MODELS.get(self.provider, "gpt-4")

        try:
            logger.info(f"Calling {self.provider} API with model {model_name}")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            code = response.choices[0].message.content.strip()
            logger.info(f"Received {len(code)} characters from LLM")
            return code

        except Exception as e:
            raise LLMError(f"LLM API call failed: {e}")
