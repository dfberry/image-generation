"""Unit tests for audio_handler.py"""

import tempfile
from pathlib import Path

import pytest

from manim_gen.audio_handler import (
    ALLOWED_AUDIO_EXTENSIONS,
    MAX_AUDIO_SIZE,
    copy_audio_to_workspace,
    generate_audio_context,
    validate_audio_path,
)
from manim_gen.errors import AudioValidationError


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_wav(temp_dir):
    """Create a minimal valid WAV file"""
    wav_path = temp_dir / "thud.wav"
    # Minimal WAV header (44 bytes) + 1 sample
    wav_data = (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        b"\x01\x00\x01\x00\x80\xbb\x00\x00\x00w\x01\x00\x02\x00\x10\x00"
        b"data\x00\x00\x00\x00"
    )
    wav_path.write_bytes(wav_data)
    return wav_path


@pytest.fixture
def sample_mp3(temp_dir):
    """Create a minimal valid MP3 file"""
    mp3_path = temp_dir / "whoosh.mp3"
    # Minimal MP3 frame header
    mp3_data = b"\xff\xfb\x90\x00" + b"\x00" * 100
    mp3_path.write_bytes(mp3_data)
    return mp3_path


@pytest.fixture
def sample_ogg(temp_dir):
    """Create a minimal valid OGG file"""
    ogg_path = temp_dir / "beep.ogg"
    # Minimal OGG header
    ogg_data = b"OggS\x00" + b"\x00" * 100
    ogg_path.write_bytes(ogg_data)
    return ogg_path


# Test 1: Validate .wav file
def test_validate_wav_file(sample_wav):
    assert validate_audio_path(sample_wav) is True


# Test 2: Validate .mp3 file
def test_validate_mp3_file(sample_mp3):
    assert validate_audio_path(sample_mp3) is True


# Test 3: Validate .ogg file
def test_validate_ogg_file(sample_ogg):
    assert validate_audio_path(sample_ogg) is True


# Test 4: Reject unsupported format
@pytest.mark.parametrize("ext", [".flac", ".aac", ".m4a", ".wma", ".txt"])
def test_reject_unsupported_format(temp_dir, ext):
    audio_path = temp_dir / f"audio{ext}"
    audio_path.write_bytes(b"dummy data")
    with pytest.raises(AudioValidationError, match="Unsupported audio format"):
        validate_audio_path(audio_path)


# Test 5: Reject nonexistent file
def test_reject_nonexistent_file(temp_dir):
    nonexistent = temp_dir / "missing.wav"
    with pytest.raises(AudioValidationError, match="Audio file not found"):
        validate_audio_path(nonexistent)


# Test 6: Reject directory as audio
def test_reject_directory_as_audio(temp_dir):
    subdir = temp_dir / "audio_dir"
    subdir.mkdir()
    with pytest.raises(AudioValidationError, match="Not a file"):
        validate_audio_path(subdir)


# Test 7: Reject symlink
def test_reject_symlink(temp_dir, sample_wav):
    symlink = temp_dir / "link.wav"
    try:
        symlink.symlink_to(sample_wav)
    except OSError:
        pytest.skip("Symlink creation not supported on this platform")
    
    with pytest.raises(AudioValidationError, match="Symlinks not allowed"):
        validate_audio_path(symlink)


# Test 8: Reject oversized file
def test_reject_oversized_file(temp_dir):
    huge_file = temp_dir / "huge.wav"
    # Create a file larger than MAX_AUDIO_SIZE
    huge_file.write_bytes(b"\x00" * (MAX_AUDIO_SIZE + 1))
    with pytest.raises(AudioValidationError, match="Audio file too large"):
        validate_audio_path(huge_file)


# Test 9: Warn policy logs warning
def test_warn_policy_logs_warning(temp_dir, caplog):
    nonexistent = temp_dir / "missing.wav"
    result = validate_audio_path(nonexistent, policy="warn")
    assert result is False
    assert "Audio file not found" in caplog.text


# Test 10: Ignore policy silent
def test_ignore_policy_silent(temp_dir, caplog):
    nonexistent = temp_dir / "missing.wav"
    result = validate_audio_path(nonexistent, policy="ignore")
    assert result is False
    assert len(caplog.records) == 0


# Test 11: Copy audio to workspace
def test_copy_audio_to_workspace(temp_dir, sample_wav, sample_mp3):
    workspace = temp_dir / "workspace"
    copies = copy_audio_to_workspace([sample_wav, sample_mp3], workspace)
    
    assert len(copies) == 2
    assert (workspace / "sfx_0_thud.wav").exists()
    assert (workspace / "sfx_1_whoosh.mp3").exists()


# Test 12: Copy preserves extension
def test_copy_preserves_extension(temp_dir, sample_wav):
    workspace = temp_dir / "workspace"
    copies = copy_audio_to_workspace([sample_wav], workspace)
    
    copied = list(copies.values())[0]
    assert copied.suffix == ".wav"
    assert "sfx_0" in copied.name


# Test 13: Copy multiple files with sequential prefixes
def test_copy_multiple_files(temp_dir):
    # Create 3 audio files
    audio_files = []
    for i in range(3):
        audio = temp_dir / f"audio_{i}.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 40)
        audio_files.append(audio)
    
    workspace = temp_dir / "workspace"
    copies = copy_audio_to_workspace(audio_files, workspace)
    
    assert len(copies) == 3
    assert (workspace / "sfx_0_audio_0.wav").exists()
    assert (workspace / "sfx_1_audio_1.wav").exists()
    assert (workspace / "sfx_2_audio_2.wav").exists()


# Test 14: Generate audio context single file
def test_generate_audio_context_single(temp_dir):
    audio_path = temp_dir / "sfx_0_thud.wav"
    audio_path.touch()
    
    context = generate_audio_context([audio_path])
    
    assert "## Available Sound Effects" in context
    assert "sfx_0_thud.wav" in context
    assert "WAV" in context
    assert "self.add_sound" in context
    assert "time_offset" in context
    assert "gain" in context


# Test 15: Generate audio context multiple files
def test_generate_audio_context_multiple(temp_dir):
    audio_paths = [
        temp_dir / "sfx_0_thud.wav",
        temp_dir / "sfx_1_whoosh.mp3",
        temp_dir / "sfx_2_beep.ogg",
    ]
    for path in audio_paths:
        path.touch()
    
    context = generate_audio_context(audio_paths)
    
    assert "sfx_0_thud.wav" in context
    assert "sfx_1_whoosh.mp3" in context
    assert "sfx_2_beep.ogg" in context
    assert "WAV" in context
    assert "MP3" in context
    assert "OGG" in context


# Test 16: Generate audio context empty list
def test_generate_audio_context_empty():
    context = generate_audio_context([])
    assert context == ""


# Test 17: Add negative time_offset (Neo condition #1)
def test_add_sound_with_negative_time_offset():
    """Test behavior with time_offset=-1.0 - should be allowed by AST validation"""
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('sfx_0_thud.wav', time_offset=-1.0)
"""
    from manim_gen.audio_handler import validate_audio_operations
    # Should not raise - negative time_offset is a valid parameter
    validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 18: Add invalid gain (Neo condition #2)
def test_add_sound_with_invalid_gain():
    """Test with gain=9999 - should be allowed by AST validation (Manim handles runtime validation)"""
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('sfx_0_thud.wav', gain=9999)
"""
    from manim_gen.audio_handler import validate_audio_operations
    # Should not raise - AST validation only checks filename, Manim validates gain at runtime
    validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 19: Audio validation error message format (Neo condition #3)
def test_audio_validation_error_message_format():
    """Verify error messages are user-friendly"""
    from manim_gen.audio_handler import validate_audio_operations
    
    code = """
class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('unknown.wav')
"""
    
    with pytest.raises(AudioValidationError) as exc_info:
        validate_audio_operations(code, {"sfx_0_thud.wav"})
    
    error_msg = str(exc_info.value)
    # Check error is user-friendly
    assert "unknown.wav" in error_msg
    assert "Allowed:" in error_msg
    assert "sfx_0_thud.wav" in error_msg


# Test 20: Copy fails gracefully with OSError
def test_copy_audio_fails_with_oserror(temp_dir, sample_wav, monkeypatch):
    """Test that copy failures raise AudioValidationError with context"""
    workspace = temp_dir / "workspace"
    
    def mock_copy2(*args, **kwargs):
        raise OSError("Permission denied")
    
    import shutil
    monkeypatch.setattr(shutil, "copy2", mock_copy2)
    
    with pytest.raises(AudioValidationError, match="Failed to copy audio file"):
        copy_audio_to_workspace([sample_wav], workspace)
