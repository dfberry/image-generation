"""Text-to-speech provider abstraction for narration generation.

Phase 0: edge-tts ONLY (OpenAI TTS deferred to Phase 1)
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Protocol

from remotion_gen.config import TTS_VOICE_DEFAULTS, MAX_TTS_TEXT_LENGTH
from remotion_gen.errors import TTSError

logger = logging.getLogger(__name__)


class TTSProvider(Protocol):
    """TTS provider interface."""

    def generate(self, text: str, voice: str, output_path: Path) -> Path:
        """Generate speech audio from text.

        Args:
            text: Text to convert to speech.
            voice: Voice identifier (provider-specific).
            output_path: Path where MP3 should be saved.

        Returns:
            Path to generated audio file.

        Raises:
            TTSError: If generation fails.
        """
        ...


class EdgeTTSProvider:
    """Free TTS using edge-tts (Microsoft Azure voices via Edge browser protocol).

    No API key required. Outputs MP3 natively.
    """

    def generate(self, text: str, voice: str, output_path: Path) -> Path:
        """Generate speech using edge-tts.

        Args:
            text: Text to convert to speech.
            voice: Voice name (e.g. "en-US-GuyNeural").
            output_path: Path where MP3 should be saved.

        Returns:
            Path to generated audio file.

        Raises:
            TTSError: If generation fails.
        """
        if not text or not text.strip():
            raise TTSError("Text for TTS cannot be empty")

        if len(text) > MAX_TTS_TEXT_LENGTH:
            raise TTSError(
                f"Text too long ({len(text)} chars). Max: {MAX_TTS_TEXT_LENGTH}"
            )

        try:
            import edge_tts
        except ImportError as e:
            raise TTSError(
                "edge-tts not installed. Run: pip install remotion-gen[audio]"
            ) from e

        try:
            # edge-tts uses async API, wrap in asyncio.run()
            asyncio.run(self._generate_async(text, voice, output_path))
        except Exception as e:
            raise TTSError(f"edge-tts generation failed: {e}") from e

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise TTSError(f"TTS output file not created: {output_path}")

        logger.info("Generated TTS audio: %s", output_path)
        return output_path

    async def _generate_async(
        self, text: str, voice: str, output_path: Path
    ) -> None:
        """Async helper for edge-tts generation."""
        import edge_tts

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))


def get_tts_provider(provider_name: str) -> TTSProvider:
    """Factory function to get TTS provider by name.

    Args:
        provider_name: Provider identifier ("edge-tts" or "openai").

    Returns:
        TTSProvider instance.

    Raises:
        TTSError: If provider name is unknown.
    """
    if provider_name == "edge-tts":
        return EdgeTTSProvider()
    elif provider_name == "openai":
        raise TTSError(
            "OpenAI TTS provider not yet implemented (Phase 1). "
            "Use --tts-provider edge-tts for now."
        )
    else:
        raise TTSError(
            f"Unknown TTS provider: {provider_name}. "
            f"Supported: edge-tts"
        )


def generate_narration(
    text: str,
    provider_name: str = "edge-tts",
    voice: str | None = None,
    output_dir: Path | None = None,
) -> Path:
    """High-level API: text → MP3 file path.

    Args:
        text: Text to convert to speech.
        provider_name: TTS provider to use.
        voice: Voice identifier (provider-specific). Uses default if None.
        output_dir: Directory for output file. Uses temp dir if None.

    Returns:
        Path to generated MP3 file.

    Raises:
        TTSError: If generation fails.
    """
    if not text or not text.strip():
        raise TTSError("Narration text cannot be empty")

    provider = get_tts_provider(provider_name)

    if voice is None:
        voice = TTS_VOICE_DEFAULTS.get(
            provider_name, TTS_VOICE_DEFAULTS["edge-tts"]
        )

    if output_dir is None:
        import tempfile

        output_dir = Path(tempfile.mkdtemp())

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "narration.mp3"

    return provider.generate(text, voice, output_path)
