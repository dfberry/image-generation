"""Integration tests for manim-animation."""

import pytest

from manim_gen.errors import ValidationError
from manim_gen.scene_builder import build_scene


@pytest.mark.integration
class TestEndToEndPipeline:
    """Integration tests for the build_scene pipeline."""

    def test_build_scene_valid_code(self, tmp_path):
        llm_output = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        self.play(Create(Circle()))\n```"
        )
        scene_file = tmp_path / "scene.py"
        code, path = build_scene(llm_output, scene_file)
        assert "GeneratedScene" in code
        assert path.exists()
        assert path.read_text(encoding="utf-8") == code

    def test_build_scene_rejects_dangerous_code(self, tmp_path):
        llm_output = (
            "```python\nimport os\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        os.system(\'rm -rf /\')\n```"
        )
        scene_file = tmp_path / "scene.py"
        with pytest.raises(ValidationError, match="Forbidden import"):
            build_scene(llm_output, scene_file)

    def test_build_scene_rejects_missing_class(self, tmp_path):
        llm_output = (
            "```python\nfrom manim import *\n\n"
            "def my_function():\n    pass\n```"
        )
        scene_file = tmp_path / "scene.py"
        with pytest.raises(ValidationError, match="GeneratedScene"):
            build_scene(llm_output, scene_file)

    def test_build_scene_rejects_syntax_error(self, tmp_path):
        llm_output = "```python\ndef broken(\n```"
        scene_file = tmp_path / "scene.py"
        with pytest.raises(ValidationError, match="syntax error"):
            build_scene(llm_output, scene_file)

    def test_build_scene_creates_parent_dirs(self, tmp_path):
        llm_output = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n        pass\n```"
        )
        nested = tmp_path / "deep" / "nested" / "scene.py"
        code, path = build_scene(llm_output, nested)
        assert path.exists()
