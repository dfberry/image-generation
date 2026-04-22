"""Image handler tests for manim-animation.

Tests: validate_image_path, copy_images_to_workspace, generate_image_context.

Covers: happy paths for all allowed formats, rejection of bad extensions / missing
files / oversized files / symlinks in strict mode, warn+ignore policy behavior,
deterministic workspace naming, source-file integrity, and LLM context formatting.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from manim_gen.errors import ImageValidationError
from manim_gen.image_handler import (
    copy_images_to_workspace,
    generate_image_context,
    validate_image_path,
)

# ---------------------------------------------------------------------------
# Helpers — validator checks path / extension / size / symlink, NOT content
# ---------------------------------------------------------------------------

_FAKE_IMAGE = b"\x89PNG\r\n\x1a\nfake-image-bytes-for-testing"


@pytest.fixture
def valid_png(tmp_path):
    """Small file with .png extension."""
    p = tmp_path / "photo.png"
    p.write_bytes(_FAKE_IMAGE)
    return p


@pytest.fixture
def valid_jpg(tmp_path):
    p = tmp_path / "photo.jpg"
    p.write_bytes(_FAKE_IMAGE)
    return p


@pytest.fixture
def symlink_image(tmp_path):
    """Symlink → valid image. Skips if OS can't create symlinks."""
    real = tmp_path / "real.png"
    real.write_bytes(_FAKE_IMAGE)
    link = tmp_path / "link.png"
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("Symlinks not supported on this platform/permissions")
    return link


# ===================================================================
# validate_image_path
# ===================================================================


class TestValidateImagePath:
    """Unit tests for validate_image_path()."""

    # -- happy-path: accepted formats --

    def test_valid_png_passes(self, valid_png):
        assert validate_image_path(valid_png) is True

    def test_valid_jpg_passes(self, valid_jpg):
        assert validate_image_path(valid_jpg) is True

    def test_svg_rejected_strict(self, tmp_path):
        """SVG is not in ALLOWED_IMAGE_EXTENSIONS (use SVGMobject instead)."""
        p = tmp_path / "icon.svg"
        p.write_text("<svg></svg>", encoding="utf-8")
        with pytest.raises(ImageValidationError, match="Unsupported image format"):
            validate_image_path(p, policy="strict")

    def test_valid_jpeg_passes(self, tmp_path):
        p = tmp_path / "shot.jpeg"
        p.write_bytes(_FAKE_IMAGE)
        assert validate_image_path(p) is True

    def test_valid_gif_passes(self, tmp_path):
        p = tmp_path / "anim.gif"
        p.write_bytes(_FAKE_IMAGE)
        assert validate_image_path(p) is True

    def test_valid_webp_passes(self, tmp_path):
        p = tmp_path / "modern.webp"
        p.write_bytes(_FAKE_IMAGE)
        assert validate_image_path(p) is True

    def test_uppercase_extension_passes(self, tmp_path):
        """Extension check is case-insensitive (.PNG → .png)."""
        p = tmp_path / "PHOTO.PNG"
        p.write_bytes(_FAKE_IMAGE)
        assert validate_image_path(p) is True

    # -- strict-mode rejections --

    def test_invalid_extension_rejected_strict(self, tmp_path):
        p = tmp_path / "script.py"
        p.write_text("print('hello')", encoding="utf-8")
        with pytest.raises(ImageValidationError, match="Unsupported image format"):
            validate_image_path(p, policy="strict")

    def test_missing_file_rejected_strict(self, tmp_path):
        missing = tmp_path / "does_not_exist.png"
        with pytest.raises(ImageValidationError, match="Image not found"):
            validate_image_path(missing, policy="strict")

    def test_directory_rejected_strict(self, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        with pytest.raises(ImageValidationError, match="Not a file"):
            validate_image_path(d, policy="strict")

    def test_oversized_file_rejected_strict(self, tmp_path):
        p = tmp_path / "big.png"
        p.write_bytes(b"x" * 100)
        with patch("manim_gen.image_handler.MAX_IMAGE_SIZE", 50):
            with pytest.raises(ImageValidationError, match="Image too large"):
                validate_image_path(p, policy="strict")

    def test_symlink_rejected_strict(self, symlink_image):
        with pytest.raises(ImageValidationError, match="Symlinks not allowed"):
            validate_image_path(symlink_image, policy="strict")

    # -- warn mode --

    def test_symlink_warned_in_warn_mode(self, symlink_image, caplog):
        with caplog.at_level(logging.WARNING):
            result = validate_image_path(symlink_image, policy="warn")
        assert result is False
        assert "Symlinks not allowed" in caplog.text

    def test_warn_returns_false_for_missing_file(self, tmp_path, caplog):
        missing = tmp_path / "gone.png"
        with caplog.at_level(logging.WARNING):
            result = validate_image_path(missing, policy="warn")
        assert result is False
        assert "Image not found" in caplog.text

    def test_warn_returns_false_for_bad_extension(self, tmp_path, caplog):
        p = tmp_path / "data.txt"
        p.write_text("hello", encoding="utf-8")
        with caplog.at_level(logging.WARNING):
            result = validate_image_path(p, policy="warn")
        assert result is False
        assert "Unsupported image format" in caplog.text

    # -- ignore mode --

    def test_ignore_returns_false_for_invalid(self, tmp_path):
        missing = tmp_path / "nope.png"
        result = validate_image_path(missing, policy="ignore")
        assert result is False

    def test_ignore_returns_true_for_valid(self, valid_png):
        assert validate_image_path(valid_png, policy="ignore") is True


# ===================================================================
# copy_images_to_workspace
# ===================================================================


class TestCopyImagesToWorkspace:
    """Unit tests for copy_images_to_workspace()."""

    def test_copies_files_with_deterministic_names(self, tmp_path):
        src = tmp_path / "sources"
        src.mkdir()
        img_a = src / "alpha.png"
        img_b = src / "beta.jpg"
        img_a.write_bytes(_FAKE_IMAGE)
        img_b.write_bytes(_FAKE_IMAGE)

        workspace = tmp_path / "workspace"
        copies = copy_images_to_workspace([img_a, img_b], workspace)

        assert len(copies) == 2
        dest_names = {p.name for p in copies.values()}
        assert "image_0_alpha.png" in dest_names
        assert "image_1_beta.jpg" in dest_names

    def test_source_file_untouched(self, valid_png, tmp_path):
        original_bytes = valid_png.read_bytes()
        workspace = tmp_path / "workspace"
        copy_images_to_workspace([valid_png], workspace)
        assert valid_png.read_bytes() == original_bytes

    def test_copied_content_matches_source(self, valid_png, tmp_path):
        workspace = tmp_path / "workspace"
        copies = copy_images_to_workspace([valid_png], workspace)
        dest = list(copies.values())[0]
        assert dest.read_bytes() == valid_png.read_bytes()

    def test_workspace_dir_created_even_if_nested(self, valid_png, tmp_path):
        workspace = tmp_path / "new" / "deep" / "workspace"
        assert not workspace.exists()
        copy_images_to_workspace([valid_png], workspace)
        assert workspace.is_dir()

    def test_invalid_images_skipped_in_warn_mode(self, tmp_path, valid_png):
        missing = tmp_path / "gone.png"
        workspace = tmp_path / "workspace"
        copies = copy_images_to_workspace(
            [missing, valid_png], workspace, policy="warn"
        )
        # Only the valid image copied; index is 1 because it's the second item
        assert len(copies) == 1
        dest_names = {p.name for p in copies.values()}
        assert "image_1_photo.png" in dest_names

    def test_strict_rejects_invalid_image(self, tmp_path):
        """Strict policy raises ImageValidationError for missing images."""
        missing = tmp_path / "gone.png"
        workspace = tmp_path / "workspace"
        with pytest.raises(ImageValidationError, match="Image not found"):
            copy_images_to_workspace([missing], workspace, policy="strict")

    def test_ignore_skips_invalid_silently(self, tmp_path, valid_png):
        """Ignore policy silently skips invalid images without logging."""
        missing = tmp_path / "gone.png"
        workspace = tmp_path / "workspace"
        copies = copy_images_to_workspace(
            [missing, valid_png], workspace, policy="ignore"
        )
        assert len(copies) == 1
        dest_names = {p.name for p in copies.values()}
        assert "image_1_photo.png" in dest_names

    @pytest.mark.parametrize("policy", ["strict", "warn", "ignore"])
    def test_all_policies_copy_valid_images(self, valid_png, tmp_path, policy):
        """All policies should successfully copy valid images."""
        workspace = tmp_path / "workspace"
        copies = copy_images_to_workspace([valid_png], workspace, policy=policy)
        assert len(copies) == 1

    def test_empty_list_returns_empty_dict(self, tmp_path):
        workspace = tmp_path / "workspace"
        copies = copy_images_to_workspace([], workspace)
        assert copies == {}

    def test_return_keys_are_resolved_source_paths(self, valid_png, tmp_path):
        workspace = tmp_path / "workspace"
        copies = copy_images_to_workspace([valid_png], workspace)
        keys = list(copies.keys())
        assert len(keys) == 1
        assert keys[0] == valid_png.resolve()

    def test_symlink_rejected_through_copy_strict(self, tmp_path):
        """Symlinks must be caught even when passed through copy_images_to_workspace.

        Regression test: previously resolved the path BEFORE validation,
        making the symlink check dead code in the normal pipeline.
        """
        real = tmp_path / "real.png"
        real.write_bytes(_FAKE_IMAGE)
        link = tmp_path / "link.png"
        try:
            link.symlink_to(real)
        except OSError:
            pytest.skip("Symlinks not supported on this platform/permissions")

        workspace = tmp_path / "workspace"
        with pytest.raises(ImageValidationError, match="Symlinks not allowed"):
            copy_images_to_workspace([link], workspace, policy="strict")

    def test_copy_error_raises_image_validation_error(self, valid_png, tmp_path):
        """OSError during shutil.copy2 must surface as ImageValidationError."""
        workspace = tmp_path / "workspace"
        with patch("manim_gen.image_handler.shutil.copy2", side_effect=OSError("disk full")):
            with pytest.raises(ImageValidationError, match="Failed to copy"):
                copy_images_to_workspace([valid_png], workspace)


# ===================================================================
# generate_image_context
# ===================================================================


class TestGenerateImageContext:
    """Unit tests for generate_image_context()."""

    def test_empty_list_returns_empty_string(self):
        assert generate_image_context([]) == ""

    def test_single_image_listed(self):
        result = generate_image_context([Path("image_0_photo.png")])
        assert "## Available Images" in result
        assert "`image_0_photo.png`" in result
        assert "ImageMobject" in result

    def test_multiple_images_listed(self):
        paths = [Path("image_0_a.png"), Path("image_1_b.jpg")]
        result = generate_image_context(paths)
        assert "`image_0_a.png`" in result
        assert "`image_1_b.jpg`" in result

    def test_descriptions_included_when_provided(self):
        result = generate_image_context(
            [Path("image_0_photo.png")],
            custom_descriptions="A landscape photo of mountains",
        )
        assert "Image descriptions:" in result
        assert "A landscape photo of mountains" in result

    def test_descriptions_absent_when_not_provided(self):
        result = generate_image_context([Path("image_0_photo.png")])
        assert "Image descriptions:" not in result

    def test_example_usage_block_included(self):
        result = generate_image_context([Path("image_0_photo.png")])
        assert "Example usage:" in result
        assert "ImageMobject(" in result
        assert "FadeIn" in result


# ===================================================================
# Edge cases: unicode filenames, long names, permission errors
# ===================================================================


class TestImageHandlerEdgeCases:
    """Edge case tests for image validation and copying."""

    def test_unicode_filename_accepted(self, tmp_path):
        """Unicode characters in filenames should be handled correctly."""
        p = tmp_path / "日本語の画像.png"
        p.write_bytes(_FAKE_IMAGE)
        assert validate_image_path(p) is True

    def test_unicode_filename_copies_successfully(self, tmp_path):
        """Unicode filenames should copy to workspace without errors."""
        p = tmp_path / "фото.png"
        p.write_bytes(_FAKE_IMAGE)
        workspace = tmp_path / "workspace"
        copies = copy_images_to_workspace([p], workspace)
        assert len(copies) == 1
        dest = list(copies.values())[0]
        assert dest.exists()
        assert dest.read_bytes() == _FAKE_IMAGE

    def test_long_filename_accepted(self, tmp_path):
        """Very long filenames (within OS limits) should work."""
        # Use a name that's long but within typical filesystem limits
        long_name = "a" * 200 + ".png"
        try:
            p = tmp_path / long_name
            p.write_bytes(_FAKE_IMAGE)
        except OSError:
            pytest.skip("Filesystem does not support this filename length")
        assert validate_image_path(p) is True

    def test_spaces_in_filename_accepted(self, tmp_path):
        """Filenames with spaces should be handled correctly."""
        p = tmp_path / "my photo file.png"
        p.write_bytes(_FAKE_IMAGE)
        assert validate_image_path(p) is True

    def test_permission_error_during_copy(self, valid_png, tmp_path):
        """PermissionError during copy surfaces as ImageValidationError."""
        workspace = tmp_path / "workspace"
        with patch(
            "manim_gen.image_handler.shutil.copy2",
            side_effect=PermissionError("access denied"),
        ):
            with pytest.raises(ImageValidationError, match="Failed to copy"):
                copy_images_to_workspace([valid_png], workspace)
