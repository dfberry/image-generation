"""Basic audio CLI integration test."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from remotion_gen.cli import generate_video
from remotion_gen.errors import TTSError


def test_narration_text_processed(tmp_path):
    """Narration text triggers TTS generation."""
    project_root = tmp_path / "remotion-project"
    project_root.mkdir()
    (project_root / "src").mkdir()
    (project_root / "public").mkdir()

    output = tmp_path / "output.mp4"

    with patch("remotion_gen.cli.generate_narration") as mock_tts:
        # Mock TTS to return a fake narration file
        fake_narration = project_root / "public" / "narration.mp3"
        fake_narration.write_bytes(b"fake MP3")
        mock_tts.return_value = fake_narration

        with patch("remotion_gen.cli.generate_component") as mock_llm:
            mock_llm.return_value = """
import {AbsoluteFill, Audio, staticFile} from 'remotion';
export default function GeneratedScene() {
  return <AbsoluteFill><Audio src={staticFile('narration.mp3')} /></AbsoluteFill>;
}
            """

            with patch("remotion_gen.cli.render_video") as mock_render:
                mock_render.return_value = output

                generate_video(
                    prompt="Test",
                    output=str(output),
                    narration_text="Hello world",
                    tts_provider="edge-tts",
                    voice="en-US-GuyNeural",
                )

                # Verify TTS was called
                mock_tts.assert_called_once()
                args = mock_tts.call_args[0]
                assert args[0] == "Hello world"

                # Verify LLM received audio context
                mock_llm.assert_called_once()
                call_kwargs = mock_llm.call_args[1]
                assert "audio_context" in call_kwargs
                assert call_kwargs["audio_context"] is not None
                assert "narration" in call_kwargs["audio_context"]


def test_empty_narration_text_raises(tmp_path):
    """Empty narration text raises TTSError."""
    project_root = tmp_path / "remotion-project"
    project_root.mkdir()
    (project_root / "src").mkdir()
    output = tmp_path / "output.mp4"

    with pytest.raises(TTSError, match="cannot be empty"):
        generate_video(
            prompt="Test",
            output=str(output),
            narration_text="   ",  # Whitespace only
        )


def test_background_music_copied(tmp_path):
    """Background music file is copied and audio context generated."""
    project_root = tmp_path / "remotion-project"
    project_root.mkdir()
    (project_root / "src").mkdir()
    (project_root / "public").mkdir()

    music_file = tmp_path / "music.mp3"
    music_file.write_bytes(b"fake MP3")

    output = tmp_path / "output.mp4"

    with patch("remotion_gen.cli.generate_component") as mock_llm:
        mock_llm.return_value = """
import {AbsoluteFill} from 'remotion';
export default function GeneratedScene() {
  return <AbsoluteFill />;
}
        """

        with patch("remotion_gen.cli.render_video") as mock_render:
            mock_render.return_value = output

            generate_video(
                prompt="Test",
                output=str(output),
                background_music=str(music_file),
            )

            # Verify LLM received audio context with music
            mock_llm.assert_called_once()
            call_kwargs = mock_llm.call_args[1]
            assert "audio_context" in call_kwargs
            assert call_kwargs["audio_context"] is not None
            assert "music" in call_kwargs["audio_context"]
            assert "Background Music" in call_kwargs["audio_context"]
            assert "loop" in call_kwargs["audio_context"]
