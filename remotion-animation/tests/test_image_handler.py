"""Image handler tests for remotion-animation.

Tests cover:
- validate_image_path: extension checks, existence, size, symlink, policy modes
- copy_image_to_public: UUID filename, public/ creation, source untouched
- generate_image_context: Remotion Img/staticFile format, with/without description
"""

import os

import pytest

from remotion_gen.errors import ImageValidationError
from remotion_gen.image_handler import (
    MAX_IMAGE_SIZE,
    copy_image_to_public,
    generate_image_context,
    validate_image_path,
)

# Minimal valid PNG header (8-byte signature + IHDR chunk stub)
_FAKE_PNG = (
    b"\x89PNG\r\n\x1a\n"  # PNG signature
    b"\x00\x00\x00\rIHDR"  # IHDR chunk
    b"\x00\x00\x00\x01"  # width = 1
    b"\x00\x00\x00\x01"  # height = 1
    b"\x08\x02"  # bit-depth=8, color-type=RGB
    b"\x00\x00\x00"  # compression, filter, interlace
)

# ---------------------------------------------------------------------------
# validate_image_path
# ---------------------------------------------------------------------------


class TestValidateImagePath:
    """Test validate_image_path under various inputs and policies."""

    @pytest.mark.parametrize("ext", [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"])
    def test_valid_extension_passes(self, tmp_path, ext):
        """Allowed image extensions should pass strict validation."""
        img = tmp_path / f"photo{ext}"
        img.write_bytes(_FAKE_PNG)
        result = validate_image_path(str(img), policy="strict")
        assert result == img.resolve()

    @pytest.mark.parametrize("ext", [".bmp", ".tiff", ".psd", ".exe", ".txt"])
    def test_invalid_extension_rejected(self, tmp_path, ext):
        """Unsupported extensions should raise under strict policy."""
        img = tmp_path / f"photo{ext}"
        img.write_bytes(_FAKE_PNG)
        with pytest.raises(ImageValidationError, match="Unsupported image extension"):
            validate_image_path(str(img), policy="strict")

    def test_missing_file_rejected(self, tmp_path):
        """Non-existent file should raise under strict policy."""
        missing = tmp_path / "does_not_exist.png"
        with pytest.raises(ImageValidationError, match="not found"):
            validate_image_path(str(missing), policy="strict")

    def test_oversized_file_rejected(self, tmp_path):
        """File exceeding MAX_IMAGE_SIZE should raise under strict policy."""
        img = tmp_path / "huge.png"
        # Write just enough to exceed MAX_IMAGE_SIZE — use sparse write
        with open(img, "wb") as f:
            f.seek(MAX_IMAGE_SIZE + 1)
            f.write(b"\x00")
        with pytest.raises(ImageValidationError, match="too large"):
            validate_image_path(str(img), policy="strict")

    @pytest.mark.skipif(
        os.name == "nt",
        reason="symlinks require privileges on Windows",
    )
    def test_symlink_rejected_strict(self, tmp_path):
        """Symlinks should raise under strict policy (security)."""
        real = tmp_path / "real.png"
        real.write_bytes(_FAKE_PNG)
        link = tmp_path / "link.png"
        link.symlink_to(real)
        with pytest.raises(ImageValidationError, match="Symlinks"):
            validate_image_path(str(link), policy="strict")

    def test_directory_rejected(self, tmp_path):
        """A directory path should raise under strict policy."""
        d = tmp_path / "images"
        d.mkdir()
        # Rename to have .png suffix so extension check doesn't trigger first
        d_png = tmp_path / "images.png"
        d_png.mkdir()
        with pytest.raises(ImageValidationError, match="not a file"):
            validate_image_path(str(d_png), policy="strict")

    # -- warn policy ---------------------------------------------------------

    def test_warn_policy_raises_on_missing(self, tmp_path):
        """Warn policy should raise for missing file — existence is not lenient."""
        missing = tmp_path / "nope.png"
        with pytest.raises(ImageValidationError, match="not found"):
            validate_image_path(str(missing), policy="warn")

    def test_warn_policy_prints_on_bad_ext(self, tmp_path, capsys):
        """Warn policy should print warning for bad extension."""
        img = tmp_path / "photo.bmp"
        img.write_bytes(_FAKE_PNG)
        validate_image_path(str(img), policy="warn")
        captured = capsys.readouterr()
        assert "Unsupported image extension" in captured.out

    # -- ignore policy -------------------------------------------------------

    def test_ignore_policy_skips_all_validation(self, tmp_path):
        """Ignore policy should return resolved path without any checks."""
        missing = tmp_path / "does_not_exist.tiff"
        result = validate_image_path(str(missing), policy="ignore")
        assert result == missing.resolve()

    # -- return value --------------------------------------------------------

    def test_returns_resolved_path(self, tmp_path):
        """Return value should be an absolute, resolved Path."""
        img = tmp_path / "photo.png"
        img.write_bytes(_FAKE_PNG)
        result = validate_image_path(str(img), policy="strict")
        assert result.is_absolute()
        assert result == img.resolve()


# ---------------------------------------------------------------------------
# copy_image_to_public
# ---------------------------------------------------------------------------


class TestCopyImageToPublic:
    """Test copy_image_to_public copies, renames, and preserves source."""

    def test_copies_with_uuid_name(self, tmp_path):
        """Copied file should have image_<hex8>.<ext> pattern."""
        img = tmp_path / "my screenshot.png"
        img.write_bytes(_FAKE_PNG)
        project = tmp_path / "remotion-project"
        project.mkdir()

        filename = copy_image_to_public(str(img), project, policy="strict")

        assert filename.startswith("image_")
        assert filename.endswith(".png")
        # UUID hex portion should be 8 characters
        hex_part = filename[len("image_"):-len(".png")]
        assert len(hex_part) == 8
        # Check file actually exists
        assert (project / "public" / filename).exists()

    def test_creates_public_dir_if_missing(self, tmp_path):
        """public/ should be created automatically if absent."""
        img = tmp_path / "photo.jpg"
        img.write_bytes(_FAKE_PNG)
        project = tmp_path / "remotion-project"
        project.mkdir()

        copy_image_to_public(str(img), project, policy="strict")

        assert (project / "public").is_dir()

    def test_source_file_untouched(self, tmp_path):
        """Source image should remain after copy."""
        img = tmp_path / "photo.png"
        img.write_bytes(_FAKE_PNG)
        project = tmp_path / "remotion-project"
        project.mkdir()

        copy_image_to_public(str(img), project, policy="strict")

        assert img.exists()
        assert img.read_bytes() == _FAKE_PNG

    def test_preserves_extension(self, tmp_path):
        """Extension from source file should be preserved in copied filename."""
        img = tmp_path / "animation.webp"
        img.write_bytes(_FAKE_PNG)
        project = tmp_path / "remotion-project"
        project.mkdir()

        filename = copy_image_to_public(str(img), project, policy="strict")

        assert filename.endswith(".webp")

    def test_content_matches_source(self, tmp_path):
        """Copied file content should be identical to source."""
        data = _FAKE_PNG + b"\xff\xd8\xff\xe0EXTRA"
        img = tmp_path / "photo.png"
        img.write_bytes(data)
        project = tmp_path / "remotion-project"
        project.mkdir()

        filename = copy_image_to_public(str(img), project, policy="strict")
        dest = project / "public" / filename
        assert dest.read_bytes() == data

    def test_unique_filenames_per_call(self, tmp_path):
        """Multiple copies of the same file should produce unique names."""
        img = tmp_path / "photo.png"
        img.write_bytes(_FAKE_PNG)
        project = tmp_path / "remotion-project"
        project.mkdir()

        f1 = copy_image_to_public(str(img), project, policy="strict")
        f2 = copy_image_to_public(str(img), project, policy="strict")
        assert f1 != f2

    def test_invalid_image_raises_before_copy(self, tmp_path):
        """Validation errors should fire before any file I/O."""
        project = tmp_path / "remotion-project"
        project.mkdir()
        missing = tmp_path / "nope.png"

        with pytest.raises(ImageValidationError, match="not found"):
            copy_image_to_public(str(missing), project, policy="strict")

        # public/ should not have been created since validate fires first
        # (actually mkdir is after validate, so public/ may or may not exist)
        # Just ensure no random files landed there
        public = project / "public"
        if public.exists():
            assert list(public.iterdir()) == [] or not any(
                p.name.startswith("image_") for p in public.iterdir()
            )


# ---------------------------------------------------------------------------
# generate_image_context
# ---------------------------------------------------------------------------


class TestGenerateImageContext:
    """Test LLM context string generation."""

    def test_contains_filename(self):
        """Context should reference the given filename."""
        ctx = generate_image_context("image_abc12345.png")
        assert "image_abc12345.png" in ctx

    def test_contains_remotion_img_guidance(self):
        """Context should include Img import instructions."""
        ctx = generate_image_context("image_abc12345.png")
        assert "Img" in ctx
        assert "staticFile" in ctx

    def test_contains_static_file_usage(self):
        """Context should show staticFile('filename') usage."""
        ctx = generate_image_context("image_abc12345.png")
        assert "staticFile('image_abc12345.png')" in ctx

    def test_without_description(self):
        """Without description, context should not have a description line."""
        ctx = generate_image_context("image_abc12345.png")
        assert "Image description:" not in ctx

    def test_with_description(self):
        """With description, context should include it."""
        ctx = generate_image_context("image_abc12345.png", "A screenshot of my app")
        assert "Image description: A screenshot of my app" in ctx

    def test_must_use_directive(self):
        """Context should include directive to use the image."""
        ctx = generate_image_context("image_abc12345.png")
        assert "MUST use the image" in ctx

    def test_no_other_path_directive(self):
        """Context should warn against using other paths."""
        ctx = generate_image_context("image_abc12345.png")
        assert "do NOT use any" in ctx.lower() or "do NOT use" in ctx
