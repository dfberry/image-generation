"""Scene builder tests for manim-animation."""

import pytest

from manim_gen.errors import ValidationError
from manim_gen.scene_builder import (
    extract_code_block,
    validate_safety,
    validate_scene_class,
    validate_syntax,
)


class TestSceneCodeExtraction:
    """Test extracting Manim scene code from LLM response."""

    def test_extracts_code_from_markdown_fence(self):
        llm_response = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n    def construct(self):\n"
            "        pass\n```"
        )
        result = extract_code_block(llm_response)
        assert "class GeneratedScene" in result
        assert "```" not in result

    def test_strips_leading_trailing_whitespace(self):
        llm_response = (
            "```python\n  \nfrom manim import *\n"
            "class GeneratedScene(Scene):\n    pass\n  \n```"
        )
        result = extract_code_block(llm_response)
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_handles_multiple_code_blocks(self):
        llm_response = (
            "```python\nfirst_block = True\n```"
            "\n\n```python\nsecond_block = True\n```"
        )
        result = extract_code_block(llm_response)
        assert "first_block" in result

    def test_empty_code_raises_error(self):
        with pytest.raises(ValidationError):
            extract_code_block("I cannot generate that animation.")

    def test_no_code_fence_returns_as_is(self):
        raw_code = "from manim import *\n\nclass GeneratedScene(Scene):\n    pass"
        result = extract_code_block(raw_code)
        assert "class GeneratedScene" in result

class TestSceneCodeValidation:
    """Test Python syntax and class validation."""

    def test_valid_python_syntax_passes(self):
        validate_syntax("x = 1\ny = 2\n")

    def test_invalid_python_syntax_raises_error(self):
        with pytest.raises(ValidationError, match="syntax error"):
            validate_syntax("def broken(\n")

    def test_missing_scene_class_raises_error(self):
        with pytest.raises(ValidationError, match="GeneratedScene"):
            validate_scene_class("def some_function():\n    pass\n")

    def test_scene_class_present_passes(self):
        validate_scene_class("class GeneratedScene:\n    pass\n")

class TestSceneCodeSafety:
    """Test security validation of generated code."""

    def test_dangerous_import_os_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden import"):
            validate_safety("import os\n")

    def test_dangerous_import_subprocess_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden import"):
            validate_safety("import subprocess\n")

    def test_dangerous_import_requests_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden import"):
            validate_safety("import requests\n")

    def test_dangerous_import_socket_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden import"):
            validate_safety("import socket\n")

    def test_safe_manim_imports_allowed(self):
        validate_safety("from manim import *\n")

    def test_safe_standard_lib_imports_allowed(self):
        validate_safety("import math\nfrom manim import *\n")

    def test_open_call_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden"):
            validate_safety("x = open(\'/etc/passwd\')\n")

    def test_exec_call_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden"):
            validate_safety("exec(\'import os\')\n")

    def test_eval_call_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden"):
            validate_safety("eval(\'1+1\')\n")

    def test_dunder_import_call_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden"):
            validate_safety("__import__(\'os\')\n")

    def test_compile_call_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden"):
            validate_safety("compile(\'import os\', \'<s>\', \'exec\')\n")

    def test_getattr_on_builtins_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden"):
            validate_safety("getattr(__builtins__, \'open\')\n")

    def test_importlib_import_rejected(self):
        with pytest.raises(ValidationError, match="Forbidden import"):
            validate_safety("import importlib\n")

    def test_dynamic_import_via_variable_rejected(self):
        code = "imp = __import__\nos = imp(\'os\')\n"
        with pytest.raises(ValidationError, match="Forbidden"):
            validate_safety(code)
