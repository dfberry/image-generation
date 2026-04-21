"""Component builder tests for remotion-animation.

Tests cover:
- Component validation
- Dangerous import rejection
- Safe imports allowed
- require() and bare import patterns
- write_component file writing
"""

import pytest

from remotion_gen.component_builder import (
    validate_component,
    validate_imports,
    write_component,
)
from remotion_gen.errors import ValidationError

VALID_COMPONENT = """\
import { AbsoluteFill, useCurrentFrame } from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  return <AbsoluteFill>{frame}</AbsoluteFill>;
}
"""


def _dangerous_component(import_line: str) -> str:
    """Build a component with a dangerous import."""
    return (
        import_line
        + "\n"
        + "import { AbsoluteFill } from 'remotion';\n"
        + "\n"
        + "export default function GeneratedScene() {\n"
        + "  return <AbsoluteFill />;\n"
        + "}\n"
    )


class TestComponentCodeValidation:
    """Test structural validation."""

    def test_valid_component_passes(self):
        validate_component(VALID_COMPONENT)

    def test_missing_remotion_import_raises_error(self):
        code = (
            "export default function GeneratedScene()"
            " { return <div/>; }"
        )
        with pytest.raises(ValidationError, match="remotion"):
            validate_component(code)

    def test_missing_default_export_raises_error(self):
        code = (
            "import { AbsoluteFill } from 'remotion';\n"
            "export function GeneratedScene()"
            " { return <AbsoluteFill />; }"
        )
        with pytest.raises(
            ValidationError, match="default export"
        ):
            validate_component(code)

    def test_missing_generated_scene_raises_error(self):
        code = (
            "import { AbsoluteFill } from 'remotion';\n"
            "export default function MyScene()"
            " { return <AbsoluteFill />; }"
        )
        with pytest.raises(
            ValidationError, match="GeneratedScene"
        ):
            validate_component(code)

    def test_missing_return_raises_error(self):
        code = (
            "import { AbsoluteFill } from 'remotion';\n"
            "export default function GeneratedScene()"
            " { const x = 1; }"
        )
        with pytest.raises(ValidationError, match="return"):
            validate_component(code)


class TestComponentCodeSafety:
    """Test security validation."""

    def test_dangerous_import_fs_rejected(self):
        code = _dangerous_component("import fs from 'fs';")
        with pytest.raises(
            ValidationError, match="Dangerous import.*fs"
        ):
            validate_component(code)

    def test_dangerous_import_child_process_rejected(self):
        code = _dangerous_component(
            "import { exec } from 'child_process';"
        )
        with pytest.raises(
            ValidationError,
            match="Dangerous import.*child_process",
        ):
            validate_component(code)

    def test_dangerous_import_http_rejected(self):
        code = _dangerous_component(
            "import http from 'http';"
        )
        with pytest.raises(
            ValidationError, match="Dangerous import.*http"
        ):
            validate_component(code)

    def test_dangerous_import_net_rejected(self):
        code = _dangerous_component(
            "import net from 'net';"
        )
        with pytest.raises(
            ValidationError, match="Dangerous import.*net"
        ):
            validate_component(code)

    def test_dangerous_import_os_rejected(self):
        code = _dangerous_component(
            "import os from 'os';"
        )
        with pytest.raises(
            ValidationError, match="Dangerous import.*os"
        ):
            validate_component(code)

    def test_dangerous_node_prefixed_import_rejected(self):
        code = _dangerous_component(
            "import fs from 'node:fs';"
        )
        with pytest.raises(
            ValidationError,
            match="Dangerous import.*node:fs",
        ):
            validate_component(code)

    def test_dangerous_require_rejected(self):
        code = _dangerous_component(
            "const fs = require('fs');"
        )
        with pytest.raises(
            ValidationError, match="Dangerous import.*fs"
        ):
            validate_component(code)

    def test_dangerous_subpath_import_rejected(self):
        code = _dangerous_component(
            "import { readFile } from 'fs/promises';"
        )
        with pytest.raises(
            ValidationError,
            match="Dangerous import.*fs/promises",
        ):
            validate_component(code)

    def test_dangerous_import_https_rejected(self):
        code = _dangerous_component(
            "import https from 'https';"
        )
        with pytest.raises(
            ValidationError, match="Dangerous import.*https"
        ):
            validate_component(code)

    @pytest.mark.parametrize(
        "module",
        [
            "crypto",
            "process",
            "cluster",
            "dgram",
            "dns",
            "tls",
            "vm",
            "worker_threads",
            "path",
        ],
    )
    def test_all_dangerous_modules_rejected(self, module):
        code = _dangerous_component(
            f"import mod from '{module}';"
        )
        with pytest.raises(
            ValidationError, match="Dangerous import"
        ):
            validate_component(code)

    def test_safe_remotion_imports_allowed(self):
        validate_component(VALID_COMPONENT)

    def test_safe_react_imports_allowed(self):
        code = (
            "import { useState } from 'react';\n"
            "import { AbsoluteFill } from 'remotion';\n"
            "export default function GeneratedScene()"
            " { return <AbsoluteFill />; }"
        )
        validate_component(code)

    def test_multiple_safe_imports_allowed(self):
        code = (
            "import { AbsoluteFill } from 'remotion';\n"
            "import { spring } from '@remotion/spring';\n"
            "export default function GeneratedScene()"
            " { return <AbsoluteFill />; }"
        )
        validate_component(code)


class TestValidateImportsDirectly:
    """Test validate_imports() in isolation."""

    def test_empty_code_passes(self):
        validate_imports("")

    def test_bare_import_rejected(self):
        with pytest.raises(ValidationError, match="fs"):
            validate_imports("import 'fs';")

    def test_double_quote_import_rejected(self):
        with pytest.raises(
            ValidationError, match="child_process"
        ):
            validate_imports(
                'import { exec } from "child_process";'
            )

    def test_require_with_double_quotes_rejected(self):
        with pytest.raises(ValidationError, match="os"):
            validate_imports('const os = require("os");')

    def test_safe_module_passes(self):
        validate_imports("import React from 'react';")


class TestWriteComponent:
    """Test write_component file writing."""

    def test_writes_to_generated_scene_tsx(
        self, tmp_project_dir
    ):
        path = write_component(
            VALID_COMPONENT, tmp_project_dir
        )
        expected = (
            tmp_project_dir / "src" / "GeneratedScene.tsx"
        )
        assert path == expected
        assert (
            path.read_text(encoding="utf-8")
            == VALID_COMPONENT
        )

    def test_debug_mode_writes_debug_copy(
        self, tmp_project_dir
    ):
        outputs_dir = tmp_project_dir.parent / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        write_component(
            VALID_COMPONENT, tmp_project_dir, debug=True
        )
        debug_path = (
            outputs_dir / "GeneratedScene.debug.tsx"
        )
        assert debug_path.exists()
        assert (
            debug_path.read_text(encoding="utf-8")
            == VALID_COMPONENT
        )

    def test_rejects_dangerous_code_before_writing(
        self, tmp_project_dir
    ):
        code = _dangerous_component(
            "import fs from 'fs';"
        )
        with pytest.raises(
            ValidationError, match="Dangerous import"
        ):
            write_component(code, tmp_project_dir)
        scene = (
            tmp_project_dir / "src" / "GeneratedScene.tsx"
        )
        assert not scene.exists()


# ---------------------------------------------------------------------------
# Issue #92: Component validation — import injection & bracket matching
# ---------------------------------------------------------------------------


class TestEnsureRemotionImports:
    """Test that missing Remotion imports are injected automatically.

    Bug #92: LLM-generated TSX sometimes omits required Remotion imports.
    After the fix, ensure_remotion_imports() (or equivalent) should inject
    missing imports before validation.
    """

    def test_valid_tsx_passes_without_modification(self):
        """Already-valid component should pass validation unchanged."""
        validate_component(VALID_COMPONENT)

    def test_tsx_missing_imports_gets_them_injected_via_write(
        self, tmp_project_dir
    ):
        """write_component with image_filename triggers inject_image_imports,
        which adds Img and staticFile if missing."""
        from remotion_gen.component_builder import inject_image_imports

        code = (
            "import { AbsoluteFill } from 'remotion';\n"
            "\n"
            "export default function GeneratedScene() {\n"
            "  return <AbsoluteFill />;\n"
            "}\n"
        )
        result = inject_image_imports(code, "photo.png")
        assert "Img" in result
        assert "staticFile" in result
        assert "photo.png" in result

    def test_inject_does_not_duplicate_existing_imports(self):
        """If Img and staticFile are already present, don't add them again."""
        from remotion_gen.component_builder import inject_image_imports

        code = (
            "import { AbsoluteFill, Img, staticFile } from 'remotion';\n"
            "\n"
            "export default function GeneratedScene() {\n"
            "  return <AbsoluteFill />;\n"
            "}\n"
        )
        result = inject_image_imports(code, "photo.png")
        # Count occurrences — should not duplicate
        assert result.count("Img") <= 3  # in import + possibly usage
        assert result.count("staticFile") <= 3

    def test_inject_adds_image_const(self):
        """inject_image_imports should add imageSrc constant."""
        from remotion_gen.component_builder import inject_image_imports

        code = (
            "import { AbsoluteFill } from 'remotion';\n"
            "\n"
            "export default function GeneratedScene() {\n"
            "  return <AbsoluteFill />;\n"
            "}\n"
        )
        result = inject_image_imports(code, "hero.png")
        assert "const imageSrc = staticFile('hero.png');" in result


class TestBracketParenValidation:
    """Test that structural validation catches mismatched brackets/parens.

    Bug #92: LLM output sometimes has mismatched JSX brackets or parens.
    validate_component should catch these.
    """

    def test_valid_jsx_brackets_pass(self):
        """Properly balanced JSX should pass."""
        code = (
            "import { AbsoluteFill } from 'remotion';\n"
            "export default function GeneratedScene() {\n"
            "  return (\n"
            "    <AbsoluteFill>\n"
            "      <div>hello</div>\n"
            "    </AbsoluteFill>\n"
            "  );\n"
            "}\n"
        )
        validate_component(code)

    def test_missing_remotion_import_still_caught(self):
        """Validation should still catch missing remotion import."""
        code = (
            "export default function GeneratedScene() {\n"
            "  return <div />;\n"
            "}\n"
        )
        with pytest.raises(ValidationError, match="remotion"):
            validate_component(code)

    def test_missing_return_still_caught(self):
        """Component with no return statement should fail."""
        code = (
            "import { AbsoluteFill } from 'remotion';\n"
            "export default function GeneratedScene() {\n"
            "  const x = 1;\n"
            "}\n"
        )
        with pytest.raises(ValidationError, match="return"):
            validate_component(code)

    def test_component_with_nested_jsx_passes(self):
        """Deeply nested JSX should still pass validation."""
        code = (
            "import { AbsoluteFill, useCurrentFrame } from 'remotion';\n"
            "export default function GeneratedScene() {\n"
            "  const frame = useCurrentFrame();\n"
            "  return (\n"
            "    <AbsoluteFill>\n"
            "      <div style={{opacity: frame / 30}}>\n"
            "        <span>nested</span>\n"
            "      </div>\n"
            "    </AbsoluteFill>\n"
            "  );\n"
            "}\n"
        )
        validate_component(code)
