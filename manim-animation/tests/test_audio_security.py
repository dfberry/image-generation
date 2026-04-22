"""Security-focused tests for audio AST validation"""

import pytest

from manim_gen.audio_handler import validate_audio_operations
from manim_gen.errors import AudioValidationError


# Test 1: add_sound with allowed file
def test_add_sound_with_allowed_file():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('sfx_0_thud.wav')
"""
    validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 2: add_sound with unknown file
def test_add_sound_with_unknown_file():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('evil.wav')
"""
    with pytest.raises(AudioValidationError, match="unknown file 'evil.wav'"):
        validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 3: add_sound with path traversal
def test_add_sound_with_path_traversal():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('../../etc/passwd')
"""
    with pytest.raises(AudioValidationError, match="unknown file"):
        validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 4: add_sound with variable filename
def test_add_sound_with_variable_filename():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        filename = 'sfx_0_thud.wav'
        self.add_sound(filename)
"""
    with pytest.raises(AudioValidationError, match="must be a string literal"):
        validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 5: add_sound with f-string
def test_add_sound_with_fstring():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        name = 'thud'
        self.add_sound(f'sfx_0_{name}.wav')
"""
    with pytest.raises(AudioValidationError, match="must be a string literal"):
        validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 6: add_sound with concatenation
def test_add_sound_with_concatenation():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('sfx_0_' + 'thud.wav')
"""
    with pytest.raises(AudioValidationError, match="must be a string literal"):
        validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 7: add_sound with no args
def test_add_sound_no_args():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound()
"""
    with pytest.raises(AudioValidationError, match="must have a filename argument"):
        validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 8: add_sound with time_offset
def test_add_sound_with_time_offset():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('sfx_0_thud.wav', time_offset=1.5)
"""
    validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 9: add_sound with gain
def test_add_sound_with_gain():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('sfx_0_thud.wav', gain=-3)
"""
    validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 10: Multiple add_sound calls
def test_multiple_add_sound_calls():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('sfx_0_thud.wav')
        self.add_sound('sfx_1_whoosh.mp3', time_offset=1.0)
        self.add_sound('sfx_2_beep.ogg', gain=-6)
"""
    validate_audio_operations(code, {"sfx_0_thud.wav", "sfx_1_whoosh.mp3", "sfx_2_beep.ogg"})


# Test 11: Mixed valid and invalid calls
def test_mixed_valid_invalid_calls():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('sfx_0_thud.wav')
        self.add_sound('evil.wav')
"""
    with pytest.raises(AudioValidationError, match="unknown file 'evil.wav'"):
        validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 12: add_sound on non-self object (Neo condition #5 - renamed and clarified)
def test_add_sound_on_non_self_object_ignored():
    """Test that other.add_sound() is ignored (not our concern)"""
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        other = SomeOtherObject()
        other.add_sound('whatever.wav')  # Not validated - not a self. method
        self.add_sound('sfx_0_thud.wav')  # This IS validated
"""
    # Should pass - we only validate self.add_sound(), not other objects
    validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 13: Forbidden calls still blocked
def test_forbidden_calls_still_blocked():
    """Ensure add_sound doesn't bypass other security checks"""
    # Note: This test verifies audio validation doesn't interfere with
    # existing security checks. The actual forbidden call check happens
    # in scene_builder.py's validate_safety(), not in audio_handler.
    # This test just confirms audio validation itself doesn't prevent
    # detecting other security issues.
    code_with_open = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.add_sound('sfx_0_thud.wav')
        with open('/etc/passwd') as f:
            data = f.read()
"""
    # Audio validation passes (only checks add_sound calls)
    validate_audio_operations(code_with_open, {"sfx_0_thud.wav"})
    
    # The forbidden 'open' call would be caught by scene_builder.validate_safety()
    # which is tested separately


# Test 14: Empty code
def test_empty_code():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        pass
"""
    validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 15: Code with no add_sound calls
def test_code_with_no_add_sound_calls():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        circle = Circle()
        self.play(Create(circle))
        self.wait(1)
"""
    validate_audio_operations(code, {"sfx_0_thud.wav"})


# Test 16: Syntax error handling
def test_syntax_error_handling():
    code = """
from manim import *

class GeneratedScene(Scene):
    def construct(self
        self.add_sound('sfx_0_thud.wav')
"""
    with pytest.raises(AudioValidationError, match="Cannot parse code"):
        validate_audio_operations(code, {"sfx_0_thud.wav"})
