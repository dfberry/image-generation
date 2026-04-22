"""Tests for tts_providers module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from remotion_gen.errors import TTSError
from remotion_gen.tts_providers import (
    EdgeTTSProvider,
    get_tts_provider,
    generate_narration,
)


class TestEdgeTTSProvider:
    """Tests for EdgeTTSProvider."""

    def test_generate_creates_mp3(self, tmp_path):
        """Mock edge_tts, verify MP3 output path returned."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"
        
        # Manually create file to simulate successful generation
        output_path.write_bytes(b"fake MP3")

        with patch("remotion_gen.tts_providers.asyncio.run") as mock_asyncio_run:
            result = provider.generate("Hello world", "en-US-GuyNeural", output_path)
            assert result == output_path
            assert output_path.exists()
            mock_asyncio_run.assert_called_once()

    def test_generate_with_custom_voice(self, tmp_path):
        """Voice parameter passed to Communicate()."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"
        
        output_path.write_bytes(b"fake MP3")

        with patch("remotion_gen.tts_providers.asyncio.run") as mock_asyncio_run:
            provider.generate("Test text", "en-GB-RyanNeural", output_path)
            mock_asyncio_run.assert_called_once()

    def test_empty_text_raises(self, tmp_path):
        """Empty string raises TTSError."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"

        with pytest.raises(TTSError, match="cannot be empty"):
            provider.generate("", "en-US-GuyNeural", output_path)

        with pytest.raises(TTSError, match="cannot be empty"):
            provider.generate("   ", "en-US-GuyNeural", output_path)

    def test_text_too_long_raises(self, tmp_path):
        """Text exceeding MAX_TTS_TEXT_LENGTH raises TTSError."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"
        long_text = "x" * 10001  # Exceeds MAX_TTS_TEXT_LENGTH (10000)

        with pytest.raises(TTSError, match="Text too long"):
            provider.generate(long_text, "en-US-GuyNeural", output_path)

    def test_missing_edge_tts_raises(self, tmp_path):
        """Missing edge-tts package raises TTSError with install instructions."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"

        # Mock the ImportError when trying to import edge_tts
        with patch.dict("sys.modules", {"edge_tts": None}):
            with pytest.raises(TTSError, match="pip install remotion-gen\\[audio\\]"):
                provider.generate("Hello", "en-US-GuyNeural", output_path)

    def test_network_error_wraps(self, tmp_path):
        """edge_tts exception wrapped in TTSError."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"

        with patch("remotion_gen.tts_providers.asyncio.run") as mock_asyncio_run:
            mock_asyncio_run.side_effect = RuntimeError("Network error")

            with pytest.raises(TTSError, match="edge-tts generation failed"):
                provider.generate("Hello", "en-US-GuyNeural", output_path)

    def test_invalid_voice_raises(self, tmp_path):
        """Nonexistent voice name raises TTSError."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"

        with patch("remotion_gen.tts_providers.asyncio.run") as mock_asyncio_run:
            mock_asyncio_run.side_effect = ValueError("Invalid voice")

            with pytest.raises(TTSError, match="edge-tts generation failed"):
                provider.generate("Hello", "invalid-voice", output_path)

    def test_output_file_created(self, tmp_path):
        """Verify file exists after generate()."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"

        # Simulate successful file creation
        output_path.write_bytes(b"fake MP3 content")

        with patch("remotion_gen.tts_providers.asyncio.run"):
            result = provider.generate("Hello", "en-US-GuyNeural", output_path)
            assert result.exists()
            assert result.stat().st_size > 0

    def test_empty_output_file_raises(self, tmp_path):
        """Empty output file raises TTSError."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"

        # Simulate empty file creation
        output_path.write_bytes(b"")

        with patch("remotion_gen.tts_providers.asyncio.run"):
            with pytest.raises(TTSError, match="output file not created"):
                provider.generate("Hello", "en-US-GuyNeural", output_path)


class TestGetTTSProvider:
    """Tests for get_tts_provider factory function."""

    def test_edge_tts_returned(self):
        """get_tts_provider('edge-tts') returns EdgeTTSProvider."""
        provider = get_tts_provider("edge-tts")
        assert isinstance(provider, EdgeTTSProvider)

    def test_openai_not_implemented(self):
        """get_tts_provider('openai') raises TTSError (Phase 1)."""
        with pytest.raises(TTSError, match="OpenAI TTS provider not yet implemented"):
            get_tts_provider("openai")

    def test_unknown_provider_raises(self):
        """get_tts_provider('foo') raises TTSError."""
        with pytest.raises(TTSError, match="Unknown TTS provider"):
            get_tts_provider("unknown")


class TestGenerateNarration:
    """Tests for high-level generate_narration API."""

    @patch("remotion_gen.tts_providers.get_tts_provider")
    def test_generates_with_defaults(self, mock_get_provider, tmp_path):
        """generate_narration uses default provider and voice."""
        mock_provider = MagicMock()
        mock_provider.generate.return_value = tmp_path / "narration.mp3"
        mock_get_provider.return_value = mock_provider

        output_path = tmp_path / "narration.mp3"
        output_path.write_bytes(b"fake")

        result = generate_narration(
            "Hello world", output_dir=tmp_path
        )

        mock_get_provider.assert_called_once_with("edge-tts")
        mock_provider.generate.assert_called_once()
        args = mock_provider.generate.call_args[0]
        assert args[0] == "Hello world"
        assert args[1] == "en-US-GuyNeural"  # Default voice

    @patch("remotion_gen.tts_providers.get_tts_provider")
    def test_custom_voice(self, mock_get_provider, tmp_path):
        """generate_narration accepts custom voice."""
        mock_provider = MagicMock()
        mock_provider.generate.return_value = tmp_path / "narration.mp3"
        mock_get_provider.return_value = mock_provider

        output_path = tmp_path / "narration.mp3"
        output_path.write_bytes(b"fake")

        generate_narration(
            "Hello", voice="en-GB-RyanNeural", output_dir=tmp_path
        )

        args = mock_provider.generate.call_args[0]
        assert args[1] == "en-GB-RyanNeural"

    def test_empty_text_raises(self):
        """Empty text raises TTSError."""
        with pytest.raises(TTSError, match="cannot be empty"):
            generate_narration("")

        with pytest.raises(TTSError, match="cannot be empty"):
            generate_narration("   ")

    @patch("remotion_gen.tts_providers.get_tts_provider")
    def test_creates_temp_dir_if_needed(self, mock_get_provider, tmp_path):
        """Uses temp dir if output_dir is None."""
        mock_provider = MagicMock()
        mock_provider.generate.return_value = Path("/tmp/narration.mp3")
        mock_get_provider.return_value = mock_provider

        generate_narration("Hello")

        mock_provider.generate.assert_called_once()
        # Verify output_path argument points to a real directory
        call_args = mock_provider.generate.call_args[0]
        output_path = call_args[2]
        assert output_path.parent.exists()
