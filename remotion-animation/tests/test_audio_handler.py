"""Tests for audio_handler module."""

import os
import shutil
from pathlib import Path

import pytest

from remotion_gen.audio_handler import (
    validate_audio_path,
    copy_audio_to_public,
    generate_audio_context,
)
from remotion_gen.errors import AudioValidationError


@pytest.fixture
def tmp_audio_dir(tmp_path):
    """Create temporary directory with test audio files."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    # Valid audio files
    (audio_dir / "test.mp3").write_bytes(b"fake MP3 data")
    (audio_dir / "test.wav").write_bytes(b"fake WAV data")
    (audio_dir / "test.ogg").write_bytes(b"fake OGG data")
    (audio_dir / "test.m4a").write_bytes(b"fake M4A data")

    # Invalid files
    (audio_dir / "test.exe").write_bytes(b"fake EXE data")
    (audio_dir / "test.txt").write_text("not audio")

    # Oversized file (simulate)
    large_file = audio_dir / "large.mp3"
    large_file.write_bytes(b"x" * (201 * 1024 * 1024))  # 201 MB

    return audio_dir


class TestValidateAudioPath:
    """Tests for validate_audio_path function."""

    def test_valid_mp3_passes(self, tmp_audio_dir):
        """MP3 file passes strict validation."""
        path = validate_audio_path(str(tmp_audio_dir / "test.mp3"), "strict")
        assert path.exists()
        assert path.name == "test.mp3"

    def test_valid_wav_passes(self, tmp_audio_dir):
        """WAV file passes strict validation."""
        path = validate_audio_path(str(tmp_audio_dir / "test.wav"), "strict")
        assert path.exists()
        assert path.name == "test.wav"

    def test_valid_ogg_passes(self, tmp_audio_dir):
        """OGG file passes strict validation."""
        path = validate_audio_path(str(tmp_audio_dir / "test.ogg"), "strict")
        assert path.exists()
        assert path.name == "test.ogg"

    def test_valid_m4a_passes(self, tmp_audio_dir):
        """M4A file passes strict validation."""
        path = validate_audio_path(str(tmp_audio_dir / "test.m4a"), "strict")
        assert path.exists()
        assert path.name == "test.m4a"

    def test_invalid_extension_rejected(self, tmp_audio_dir):
        """Invalid extensions (.exe, .txt) are rejected in strict mode."""
        with pytest.raises(AudioValidationError, match="Unsupported audio extension"):
            validate_audio_path(str(tmp_audio_dir / "test.exe"), "strict")

        with pytest.raises(AudioValidationError, match="Unsupported audio extension"):
            validate_audio_path(str(tmp_audio_dir / "test.txt"), "strict")

    def test_invalid_extension_warn_mode(self, tmp_audio_dir, capsys):
        """Bad extension prints warning in warn mode, doesn't raise."""
        path = validate_audio_path(str(tmp_audio_dir / "test.txt"), "warn")
        assert path.exists()
        captured = capsys.readouterr()
        assert "⚠" in captured.out
        assert "Unsupported audio extension" in captured.out

    def test_ignore_policy_skips_all(self, tmp_audio_dir):
        """Ignore mode returns path without checks."""
        path = validate_audio_path(str(tmp_audio_dir / "test.exe"), "ignore")
        assert path.name == "test.exe"

    def test_nonexistent_file_rejected(self, tmp_audio_dir):
        """Missing file raises AudioValidationError."""
        with pytest.raises(AudioValidationError, match="Audio file not found"):
            validate_audio_path(str(tmp_audio_dir / "missing.mp3"), "strict")

    def test_directory_rejected(self, tmp_audio_dir):
        """Path to directory raises error."""
        with pytest.raises(AudioValidationError, match="not a file"):
            validate_audio_path(str(tmp_audio_dir), "strict")

    def test_symlink_rejected(self, tmp_audio_dir):
        """Symlink raises AudioValidationError."""
        target = tmp_audio_dir / "test.mp3"
        link = tmp_audio_dir / "link.mp3"
        
        # Skip if OS doesn't support symlinks
        try:
            os.symlink(target, link)
        except OSError:
            pytest.skip("OS does not support symlinks")

        with pytest.raises(AudioValidationError, match="Symlinks are not allowed"):
            validate_audio_path(str(link), "strict")

    def test_oversized_file_rejected(self, tmp_audio_dir):
        """File > MAX_AUDIO_SIZE raises error in strict mode."""
        with pytest.raises(AudioValidationError, match="Audio too large"):
            validate_audio_path(str(tmp_audio_dir / "large.mp3"), "strict")

    def test_oversized_file_warn_mode(self, tmp_audio_dir, capsys):
        """Large file prints warning in warn mode."""
        path = validate_audio_path(str(tmp_audio_dir / "large.mp3"), "warn")
        assert path.exists()
        captured = capsys.readouterr()
        assert "⚠" in captured.out
        assert "Audio too large" in captured.out


class TestCopyAudioToPublic:
    """Tests for copy_audio_to_public function."""

    def test_copies_with_sanitized_name(self, tmp_audio_dir, tmp_path):
        """Output is audio_{uuid}.mp3."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        filename = copy_audio_to_public(
            str(tmp_audio_dir / "test.mp3"), project_root, "strict"
        )

        assert filename.startswith("audio_")
        assert filename.endswith(".mp3")
        assert len(filename) == len("audio_") + 8 + len(".mp3")  # audio_ + 8 hex + .mp3

        public_dir = project_root / "public"
        assert (public_dir / filename).exists()

    def test_creates_public_dir(self, tmp_audio_dir, tmp_path):
        """public/ created if missing."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        assert not (project_root / "public").exists()

        copy_audio_to_public(
            str(tmp_audio_dir / "test.mp3"), project_root, "strict"
        )

        assert (project_root / "public").exists()

    def test_custom_prefix(self, tmp_audio_dir, tmp_path):
        """prefix='music' → music_{uuid}.mp3."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        filename = copy_audio_to_public(
            str(tmp_audio_dir / "test.mp3"),
            project_root,
            "strict",
            prefix="music",
        )

        assert filename.startswith("music_")
        assert filename.endswith(".mp3")

    def test_source_file_untouched(self, tmp_audio_dir, tmp_path):
        """Original file still exists after copy."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        source = tmp_audio_dir / "test.mp3"
        assert source.exists()

        copy_audio_to_public(str(source), project_root, "strict")

        assert source.exists()  # Original unchanged


class TestGenerateAudioContext:
    """Tests for generate_audio_context function."""

    def test_narration_only_context(self):
        """Context mentions narration filename and volume."""
        audio_files = {"narration": "narration_a1b2c3d4.mp3"}
        context = generate_audio_context(audio_files, 0.3, 1.0)

        assert "narration_a1b2c3d4.mp3" in context
        assert "volume={1.0}" in context
        assert "Narration" in context

    def test_full_context(self):
        """Context includes narration + music + SFX with volumes."""
        audio_files = {
            "narration": "narration_a1b2c3d4.mp3",
            "music": "music_e5f6g7h8.mp3",
            "sfx_0": "sfx_0_i9j0k1l2.mp3",
            "sfx_1": "sfx_1_m3n4o5p6.mp3",
        }
        context = generate_audio_context(audio_files, 0.3, 1.0)

        assert "narration_a1b2c3d4.mp3" in context
        assert "music_e5f6g7h8.mp3" in context
        assert "sfx_0_i9j0k1l2.mp3" in context
        assert "sfx_1_m3n4o5p6.mp3" in context
        assert "volume={1.0}" in context
        assert "volume={0.3}" in context
        assert "loop" in context
        assert "Sequence" in context

    def test_empty_audio_files(self):
        """Empty dict returns empty string."""
        context = generate_audio_context({}, 0.3, 1.0)
        assert context == ""
