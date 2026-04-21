"""Image security tests for manim-animation.

Tests: validate_image_operations (AST-based security check for generated image code).
Integration: build_scene with image_filenames parameter.

Verifies that only literal-string ImageMobject calls with allowed filenames pass,
and that all file-write attribute calls are blocked.
"""

import pytest

from manim_gen.errors import ValidationError
from manim_gen.scene_builder import build_scene, validate_image_operations

# ===================================================================
# validate_image_operations — unit tests
# ===================================================================


class TestValidateImageOperations:
    """Unit tests for validate_image_operations() in scene_builder."""

    # -- Allowed patterns -------------------------------------------------

    def test_allows_literal_filename(self):
        code = (
            "from manim import *\n"
            "img = ImageMobject('photo.png')\n"
        )
        validate_image_operations(code, {"photo.png"})

    def test_allows_multiple_image_mobjects(self):
        code = (
            "from manim import *\n"
            "a = ImageMobject('image_0_a.png')\n"
            "b = ImageMobject('image_1_b.jpg')\n"
        )
        validate_image_operations(code, {"image_0_a.png", "image_1_b.jpg"})

    def test_allows_code_without_image_mobject(self):
        """No ImageMobject calls → nothing to reject."""
        code = (
            "from manim import *\n"
            "circle = Circle()\n"
        )
        validate_image_operations(code, {"photo.png"})

    def test_allows_attribute_style_image_mobject(self):
        """manim.ImageMobject('x') is also valid."""
        code = (
            "import manim\n"
            "img = manim.ImageMobject('photo.png')\n"
        )
        validate_image_operations(code, {"photo.png"})

    # -- Blocked: dynamic / missing filenames -----------------------------

    def test_blocks_variable_filename(self):
        code = (
            "from manim import *\n"
            "name = 'photo.png'\n"
            "img = ImageMobject(name)\n"
        )
        with pytest.raises(ValidationError, match="string literal"):
            validate_image_operations(code, {"photo.png"})

    def test_blocks_fstring_filename(self):
        code = (
            "from manim import *\n"
            "img = ImageMobject(f'{prefix}.png')\n"
        )
        with pytest.raises(ValidationError, match="string literal"):
            validate_image_operations(code, {"photo.png"})

    def test_blocks_no_args(self):
        code = (
            "from manim import *\n"
            "img = ImageMobject()\n"
        )
        with pytest.raises(ValidationError, match="filename argument"):
            validate_image_operations(code, {"photo.png"})

    def test_blocks_unknown_filename(self):
        code = (
            "from manim import *\n"
            "img = ImageMobject('evil.png')\n"
        )
        with pytest.raises(ValidationError, match="unknown file"):
            validate_image_operations(code, {"photo.png"})

    def test_blocks_integer_arg(self):
        code = (
            "from manim import *\n"
            "img = ImageMobject(42)\n"
        )
        with pytest.raises(ValidationError, match="string literal"):
            validate_image_operations(code, {"photo.png"})

    def test_blocks_concatenation_arg(self):
        code = (
            "from manim import *\n"
            "img = ImageMobject('photo' + '.png')\n"
        )
        with pytest.raises(ValidationError, match="string literal"):
            validate_image_operations(code, {"photo.png"})

    # -- Blocked: file-write operations -----------------------------------

    def test_blocks_write_text(self):
        code = "img.write_text('hack')\n"
        with pytest.raises(ValidationError, match="write_text"):
            validate_image_operations(code, set())

    def test_blocks_write_bytes(self):
        code = "p.write_bytes(b'data')\n"
        with pytest.raises(ValidationError, match="write_bytes"):
            validate_image_operations(code, set())

    def test_blocks_unlink(self):
        code = "p.unlink()\n"
        with pytest.raises(ValidationError, match="unlink"):
            validate_image_operations(code, set())

    def test_blocks_rmdir(self):
        code = "p.rmdir()\n"
        with pytest.raises(ValidationError, match="rmdir"):
            validate_image_operations(code, set())

    def test_blocks_remove(self):
        code = "os.remove('file')\n"
        with pytest.raises(ValidationError, match="remove"):
            validate_image_operations(code, set())

    def test_blocks_rmtree(self):
        code = "shutil.rmtree('/tmp/x')\n"
        with pytest.raises(ValidationError, match="rmtree"):
            validate_image_operations(code, set())

    def test_blocks_rename(self):
        code = "p.rename('new_name')\n"
        with pytest.raises(ValidationError, match="rename"):
            validate_image_operations(code, set())

    # -- Edge cases -------------------------------------------------------

    def test_syntax_error_code_does_not_crash(self):
        """Syntax errors are handled by a separate validator; this one returns."""
        code = "def broken(\n"
        validate_image_operations(code, set())  # should not raise

    def test_empty_allowed_set_still_blocks_image_mobject(self):
        code = "img = ImageMobject('photo.png')\n"
        with pytest.raises(ValidationError, match="unknown file"):
            validate_image_operations(code, set())


# ===================================================================
# build_scene + image validation — integration
# ===================================================================


@pytest.mark.integration
class TestBuildSceneWithImages:
    """Integration: build_scene with image_filenames triggers image checks."""

    def test_valid_image_code_passes(self, tmp_path):
        llm_output = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        img = ImageMobject('image_0_photo.png')\n"
            "        self.play(FadeIn(img))\n```"
        )
        scene_file = tmp_path / "scene.py"
        code, path = build_scene(
            llm_output, scene_file, image_filenames={"image_0_photo.png"}
        )
        assert "ImageMobject" in code
        assert path.exists()

    def test_rejects_dynamic_filename(self, tmp_path):
        llm_output = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        name = 'photo.png'\n"
            "        img = ImageMobject(name)\n```"
        )
        scene_file = tmp_path / "scene.py"
        with pytest.raises(ValidationError, match="string literal"):
            build_scene(llm_output, scene_file, image_filenames={"photo.png"})

    def test_rejects_file_write_ops(self, tmp_path):
        llm_output = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        img = ImageMobject('image_0_photo.png')\n"
            "        self.play(FadeIn(img))\n"
            "        img.write_text('hack')\n```"
        )
        scene_file = tmp_path / "scene.py"
        with pytest.raises(ValidationError, match="write_text"):
            build_scene(
                llm_output, scene_file, image_filenames={"image_0_photo.png"}
            )

    def test_rejects_unknown_image_filename(self, tmp_path):
        llm_output = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        img = ImageMobject('sneaky.png')\n"
            "        self.play(FadeIn(img))\n```"
        )
        scene_file = tmp_path / "scene.py"
        with pytest.raises(ValidationError, match="unknown file"):
            build_scene(
                llm_output, scene_file, image_filenames={"image_0_photo.png"}
            )

    def test_no_image_filenames_skips_image_check(self, tmp_path):
        """image_filenames=None → image operations are NOT validated."""
        llm_output = (
            "```python\nfrom manim import *\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        img = ImageMobject('anything.png')\n"
            "        self.play(FadeIn(img))\n```"
        )
        scene_file = tmp_path / "scene.py"
        code, path = build_scene(llm_output, scene_file, image_filenames=None)
        assert "ImageMobject" in code
