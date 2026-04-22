"""Security tests for audio path validation in components."""

import pytest

from remotion_gen.component_builder import (
    validate_audio_paths,
    inject_audio_imports,
)
from remotion_gen.errors import ValidationError


class TestValidateAudioPaths:
    """Security tests for validate_audio_paths function."""

    def test_blocks_file_url(self):
        """file:// in code raises ValidationError."""
        code = """
        <Audio src="file:///etc/passwd" />
        """
        with pytest.raises(ValidationError, match="file:// URLs are not allowed"):
            validate_audio_paths(code, ["narration.mp3"])

    def test_blocks_path_traversal(self):
        """../ blocked."""
        code = """
        <Audio src={staticFile('../../../etc/passwd')} />
        """
        with pytest.raises(ValidationError, match="Path traversal"):
            validate_audio_paths(code, ["narration.mp3"])

    def test_blocks_data_uri(self):
        """data:audio/ blocked."""
        code = """
        <Audio src="data:audio/mp3;base64,SGVsbG8=" />
        """
        with pytest.raises(ValidationError, match="data: URIs are not allowed"):
            validate_audio_paths(code, ["narration.mp3"])

    def test_blocks_unknown_filename(self):
        """staticFile('evil.mp3') blocked when not in allowed list."""
        code = """
        <Audio src={staticFile('evil.mp3')} />
        """
        with pytest.raises(ValidationError, match="only .* are allowed"):
            validate_audio_paths(code, ["narration.mp3"])

    def test_allows_known_files(self):
        """Approved filenames pass validation."""
        code = """
        <Audio src={staticFile('narration_a1b2c3d4.mp3')} />
        <Audio src={staticFile('music_e5f6g7h8.mp3')} loop />
        """
        # Should not raise
        validate_audio_paths(code, ["narration_a1b2c3d4.mp3", "music_e5f6g7h8.mp3"])

    def test_blocks_non_literal(self):
        """Template literal in staticFile() blocked."""
        code = """
        const audioSrc = `sfx_${i}.mp3`;
        <Audio src={staticFile(audioSrc)} />
        """
        with pytest.raises(ValidationError, match="string literals"):
            validate_audio_paths(code, ["sfx_0.mp3"])

    def test_blocks_template_literal_backticks(self):
        """`` `sfx_${i}.mp3` `` blocked (Neo condition #4)."""
        code = """
        <Audio src={staticFile(`sfx_${i}.mp3`)} />
        """
        with pytest.raises(ValidationError, match="Template literals are not allowed"):
            validate_audio_paths(code, ["sfx_0.mp3"])

    def test_blocks_encoded_traversal(self):
        """%2E%2E%2F blocked."""
        code = """
        <Audio src={staticFile('%2E%2E%2Fetc%2Fpasswd')} />
        """
        with pytest.raises(ValidationError, match="Encoded path traversal"):
            validate_audio_paths(code, ["audio.mp3"])


class TestInjectAudioImports:
    """Tests for inject_audio_imports function."""

    def test_adds_audio(self):
        """Audio import injected correctly."""
        code = """
        import {AbsoluteFill, useCurrentFrame} from 'remotion';
        """
        result = inject_audio_imports(code, ["audio.mp3"])
        assert "Audio" in result
        assert "staticFile" in result
        assert "from 'remotion'" in result or 'from "remotion"' in result

    def test_adds_staticfile_if_missing(self):
        """staticFile added when Audio already present."""
        code = """
        import {AbsoluteFill, Audio} from 'remotion';
        """
        result = inject_audio_imports(code, ["audio.mp3"])
        assert "staticFile" in result

    def test_handles_double_quotes(self):
        """Works with double-quote import style."""
        code = """
        import {AbsoluteFill} from "remotion";
        """
        result = inject_audio_imports(code, ["audio.mp3"])
        assert "Audio" in result
        assert "staticFile" in result

    def test_raises_if_injection_fails(self):
        """ValidationError if imports can't be injected."""
        code = """
        const x = 5;
        """
        with pytest.raises(ValidationError, match="Failed to inject"):
            inject_audio_imports(code, ["audio.mp3"])


class TestNeoConditions:
    """Test cases specifically requested by Neo."""

    def test_narration_text_whitespace_only(self):
        """Neo condition #1: '   ' should error (handled in TTS, not here)."""
        # This is tested in test_tts_providers.py
        pass

    def test_narration_text_with_unicode(self):
        """Neo condition #2: 'Hello 世界 🌍' should pass TTS (tested in TTS)."""
        # This is tested in test_tts_providers.py
        pass

    def test_staticfile_with_template_literal_backticks(self):
        """Neo condition #4: `` `sfx_${i}.mp3` `` blocked."""
        code = """
        <Audio src={staticFile(`sfx_${i}.mp3`)} />
        """
        with pytest.raises(ValidationError, match="Template literals are not allowed"):
            validate_audio_paths(code, ["sfx_0.mp3"])
