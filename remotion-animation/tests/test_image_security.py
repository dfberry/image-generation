"""Image security tests for component_builder image features.

Tests cover:
- validate_image_paths: file:// blocking, path traversal, staticFile ref matching
- inject_image_imports: Img/staticFile injection, imageSrc constant, idempotency
- Integration: write_component with image_filename validates and injects
"""

import pytest

from remotion_gen.component_builder import (
    inject_image_imports,
    validate_image_paths,
    write_component,
)
from remotion_gen.errors import ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A minimal valid component that already has correct structure
VALID_COMPONENT = """\
import {AbsoluteFill, useCurrentFrame} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <h1>{frame}</h1>
    </AbsoluteFill>
  );
}
"""

# Component that LLM might generate using the image
COMPONENT_WITH_IMAGE = """\
import {AbsoluteFill, useCurrentFrame, Img, staticFile} from 'remotion';

const imageSrc = staticFile('image_abc12345.png');

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Img src={imageSrc} style={{width: 1280}} />
    </AbsoluteFill>
  );
}
"""


# ---------------------------------------------------------------------------
# validate_image_paths
# ---------------------------------------------------------------------------


class TestValidateImagePaths:
    """Test security validation of image references in generated code."""

    def test_blocks_file_url(self):
        """file:// URLs must be rejected."""
        code = VALID_COMPONENT.replace(
            "<h1>{frame}</h1>",
            '<img src="file:///etc/passwd" />',
        )
        with pytest.raises(ValidationError, match="file://"):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_path_traversal(self):
        """../ path traversal must be rejected."""
        code = VALID_COMPONENT.replace(
            "<h1>{frame}</h1>",
            "<img src={staticFile('../../../etc/passwd')} />",
        )
        with pytest.raises(ValidationError, match="Path traversal"):
            validate_image_paths(code, "image_abc12345.png")

    def test_allows_matching_static_file_ref(self):
        """staticFile() referencing the allowed filename should pass."""
        code = """const img = staticFile('image_abc12345.png');"""
        validate_image_paths(code, "image_abc12345.png")  # Should not raise

    def test_blocks_non_matching_static_file_ref(self):
        """staticFile() referencing a different filename should be rejected."""
        code = """const img = staticFile('malicious.png');"""
        with pytest.raises(
            ValidationError,
            match="malicious.png.*only.*image_abc12345.png",
        ):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_static_file_with_path_prefix(self):
        """staticFile('subdir/image.png') should be rejected when not matching."""
        code = """const img = staticFile('subdir/image_abc12345.png');"""
        with pytest.raises(ValidationError, match="staticFile"):
            validate_image_paths(code, "image_abc12345.png")

    def test_clean_code_without_static_file_passes(self):
        """Code with no staticFile() calls and no file:// should pass."""
        validate_image_paths(VALID_COMPONENT, "image_abc12345.png")

    def test_multiple_valid_static_file_refs(self):
        """Multiple staticFile() calls to the same allowed file should pass."""
        code = (
            "const a = staticFile('image_abc12345.png');\n"
            "const b = staticFile('image_abc12345.png');\n"
        )
        validate_image_paths(code, "image_abc12345.png")

    def test_one_bad_among_good_static_file_refs(self):
        """If one staticFile() ref is wrong, validation should fail."""
        code = (
            "const a = staticFile('image_abc12345.png');\n"
            "const b = staticFile('sneaky.jpg');\n"
        )
        with pytest.raises(ValidationError, match="sneaky.jpg"):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_file_url_case_variations(self):
        """file:// check is case-insensitive — FILE:// and File:// are caught."""
        code = 'const src = "file:///secret/data";'
        with pytest.raises(ValidationError, match="file://"):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_file_url_uppercase(self):
        """FILE:// in uppercase must also be rejected."""
        code = 'const src = "FILE:///etc/passwd";'
        with pytest.raises(ValidationError, match="file://"):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_file_url_mixed_case(self):
        """File:// in mixed case must also be rejected."""
        code = 'const src = "File:///etc/shadow";'
        with pytest.raises(ValidationError, match="file://"):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_double_dot_in_string(self):
        """Even ../ embedded in a string literal should be caught."""
        code = "const path = '../../../passwords.txt';"
        with pytest.raises(ValidationError, match="Path traversal"):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_backslash_path_traversal(self):
        r"""..\ (backslash) path traversal must be rejected."""
        code = r"const path = '..\..\secret.txt';"
        with pytest.raises(ValidationError, match="Path traversal"):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_dynamic_static_file_template_literal(self):
        """staticFile() with template literals must be rejected."""
        code = "const img = staticFile(`${someVar}`);"
        with pytest.raises(ValidationError, match="string literals"):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_dynamic_static_file_variable(self):
        """staticFile() with a variable reference must be rejected."""
        code = "const img = staticFile(someVariable);"
        with pytest.raises(ValidationError, match="string literals"):
            validate_image_paths(code, "image_abc12345.png")

    def test_blocks_dynamic_static_file_function_call(self):
        """staticFile() with a function call must be rejected."""
        code = "const img = staticFile(getPath());"
        with pytest.raises(ValidationError, match="string literals"):
            validate_image_paths(code, "image_abc12345.png")


# ---------------------------------------------------------------------------
# inject_image_imports
# ---------------------------------------------------------------------------


class TestInjectImageImports:
    """Test inject_image_imports adds Img, staticFile, and imageSrc."""

    def test_injection_produces_valid_tsx_syntax(self):
        """Injection into code without Img/staticFile should produce valid TSX."""
        result = inject_image_imports(VALID_COMPONENT, "image_abc12345.png")
        # The result should retain a valid import closing: } from 'remotion'
        assert "} from 'remotion'" in result or '} from "remotion"' in result
        # Img and staticFile should appear inside the import braces
        assert "Img" in result
        assert "staticFile" in result

    def test_adds_img_import(self):
        """Img should be present in result if absent in input."""
        result = inject_image_imports(VALID_COMPONENT, "image_abc12345.png")
        assert "Img" in result

    def test_adds_static_file_import(self):
        """staticFile should be present in result if absent in input."""
        result = inject_image_imports(VALID_COMPONENT, "image_abc12345.png")
        assert "staticFile" in result

    def test_adds_image_src_constant(self):
        """imageSrc constant should be injected."""
        result = inject_image_imports(VALID_COMPONENT, "image_abc12345.png")
        assert "const imageSrc = staticFile('image_abc12345.png');" in result

    def test_does_not_duplicate_existing_img(self):
        """If Img is already imported, don't add it again."""
        code_with_img = VALID_COMPONENT.replace(
            "from 'remotion'",
            "Img, staticFile} from 'remotion'",
            1,
        ).replace(
            "{AbsoluteFill, useCurrentFrame,",
            "import {AbsoluteFill, useCurrentFrame,",
            0,
        )
        # The actual component already has correct import syntax
        code_with_img = (
            "import {AbsoluteFill, useCurrentFrame,"
            " Img, staticFile} from 'remotion';\n\n"
            "export default function GeneratedScene() {\n"
            "  const frame = useCurrentFrame();\n"
            "  return <AbsoluteFill><h1>{frame}</h1></AbsoluteFill>;\n"
            "}\n"
        )
        result = inject_image_imports(code_with_img, "image_abc12345.png")
        # Count Img occurrences in import lines
        # (import line + imageSrc is fine, but not duplicates)
        import_lines = [
            line for line in result.split("\n")
            if line.strip().startswith("import") and "Img" in line
        ]
        assert len(import_lines) == 1

    def test_does_not_duplicate_existing_static_file(self):
        """If staticFile already imported, shouldn't double-import."""
        code_with_sf = (
            "import {AbsoluteFill, staticFile} from 'remotion';\n\n"
            "export default function GeneratedScene() {\n"
            "  return <AbsoluteFill />;\n"
            "}\n"
        )
        result = inject_image_imports(code_with_sf, "image_abc12345.png")
        count = result.count("staticFile,")
        # staticFile should appear in import but not be duplicated
        assert count <= 1

    def test_does_not_duplicate_existing_image_src(self):
        """If imageSrc already defined, don't add again."""
        result = inject_image_imports(COMPONENT_WITH_IMAGE, "image_abc12345.png")
        count = result.count("const imageSrc")
        assert count == 1

    def test_preserves_component_structure(self):
        """Injection should not break the component's export/return."""
        result = inject_image_imports(VALID_COMPONENT, "image_abc12345.png")
        assert "export default function GeneratedScene" in result
        assert "return" in result

    def test_works_with_double_quote_imports(self):
        """Should handle double-quoted imports."""
        code = (
            'import {AbsoluteFill, useCurrentFrame} from "remotion";\n\n'
            "export default function GeneratedScene() {\n"
            "  return <AbsoluteFill />;\n"
            "}\n"
        )
        result = inject_image_imports(code, "image_abc12345.png")
        assert "Img" in result or "staticFile" in result


# ---------------------------------------------------------------------------
# Integration: write_component with image_filename
# ---------------------------------------------------------------------------


class TestWriteComponentImageIntegration:
    """Test write_component's image_filename parameter end-to-end."""

    def test_write_with_image_injects_and_validates(self, tmp_path):
        """write_component with image_filename should inject imports and validate."""
        project = tmp_path / "remotion-project"
        (project / "src").mkdir(parents=True)

        code = COMPONENT_WITH_IMAGE
        path = write_component(code, project, image_filename="image_abc12345.png")

        written = path.read_text(encoding="utf-8")
        assert "Img" in written
        assert "staticFile" in written
        assert "GeneratedScene" in written

    def test_write_with_image_rejects_file_url(self, tmp_path):
        """write_component should reject code with file://.

        Even when image_filename is set, file:// is blocked.
        """
        project = tmp_path / "remotion-project"
        (project / "src").mkdir(parents=True)

        code = (
            "import {AbsoluteFill, Img, staticFile} from 'remotion';\n"
            "export default function GeneratedScene() {\n"
            '  return <AbsoluteFill><img src="file:///etc/passwd" /></AbsoluteFill>;\n'
            "}\n"
        )
        with pytest.raises(ValidationError, match="file://"):
            write_component(code, project, image_filename="image_abc12345.png")

    def test_write_with_image_rejects_wrong_static_file(self, tmp_path):
        """write_component should reject staticFile() referencing wrong filename."""
        project = tmp_path / "remotion-project"
        (project / "src").mkdir(parents=True)

        code = (
            "import {AbsoluteFill, Img, staticFile} from 'remotion';\n"
            "const imageSrc = staticFile('evil.png');\n"
            "export default function GeneratedScene() {\n"
            "  return <AbsoluteFill><Img src={imageSrc} /></AbsoluteFill>;\n"
            "}\n"
        )
        with pytest.raises(ValidationError, match="evil.png"):
            write_component(code, project, image_filename="image_abc12345.png")

    def test_write_without_image_skips_image_checks(self, tmp_path):
        """write_component without image_filename should not do image validation."""
        project = tmp_path / "remotion-project"
        (project / "src").mkdir(parents=True)

        # Regular component without image — should pass even without Img import
        path = write_component(VALID_COMPONENT, project)
        assert path.exists()

    def test_write_with_image_rejects_path_traversal(self, tmp_path):
        """write_component should reject ../ path traversal in code."""
        project = tmp_path / "remotion-project"
        (project / "src").mkdir(parents=True)

        code = (
            "import {AbsoluteFill, Img, staticFile} from 'remotion';\n"
            "const imageSrc = staticFile('../../../etc/shadow');\n"
            "export default function GeneratedScene() {\n"
            "  return <AbsoluteFill><Img src={imageSrc} /></AbsoluteFill>;\n"
            "}\n"
        )
        with pytest.raises(ValidationError):
            write_component(code, project, image_filename="image_abc12345.png")
