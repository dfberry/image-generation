"""Component builder tests for remotion-animation.

Tests cover:
- Component validation
- Dangerous import rejection
- Safe imports allowed
- require() and bare import patterns
- write_component file writing
- TSX bracket/syntax validation (validate_tsx_syntax)
- Missing Remotion import fixup (ensure_remotion_imports)
"""

import pytest

from remotion_gen.component_builder import (
    ensure_remotion_imports,
    validate_component,
    validate_imports,
    validate_tsx_syntax,
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
# validate_tsx_syntax tests
# ---------------------------------------------------------------------------


class TestValidateTsxSyntax:
    """Test bracket/paren/brace mismatch detection."""

    def test_valid_code_returns_empty(self):
        code = VALID_COMPONENT
        assert validate_tsx_syntax(code) == []

    def test_unclosed_paren_detected(self):
        code = "const x = interpolate(frame, [0, 30], [0, 1];"
        errors = validate_tsx_syntax(code)
        assert len(errors) >= 1
        assert any("Unclosed" in e or "Mismatched" in e for e in errors)

    def test_extra_closing_brace_detected(self):
        code = "const x = 1; }"
        errors = validate_tsx_syntax(code)
        assert len(errors) >= 1
        assert any("Unexpected closing" in e for e in errors)

    def test_mismatched_bracket_types_detected(self):
        code = "const arr = [1, 2, 3);"
        errors = validate_tsx_syntax(code)
        assert len(errors) >= 1
        assert any("Mismatched" in e for e in errors)

    def test_balanced_complex_code_passes(self):
        code = """\
import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <h1 style={{opacity}}>Test</h1>
    </AbsoluteFill>
  );
}
"""
        assert validate_tsx_syntax(code) == []

    def test_unclosed_jsx_tag_detected(self):
        code = """\
import {AbsoluteFill, useCurrentFrame} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <div>
        <h1>Missing closing div</h1>
    </AbsoluteFill>
  );
}
"""
        errors = validate_tsx_syntax(code)
        assert any("Unclosed <div>" in e for e in errors)

    def test_strings_ignored_in_bracket_check(self):
        """Brackets inside string literals should not cause false positives."""
        code = """\
import {AbsoluteFill} from 'remotion';
export default function GeneratedScene() {
  const msg = "array notation: [1, 2)";
  return (<AbsoluteFill><p>{msg}</p></AbsoluteFill>);
}
"""
        errors = validate_tsx_syntax(code)
        # The mismatch is inside a string, so should be cleaned away
        assert errors == []

    def test_self_closing_tags_not_flagged(self):
        code = """\
import {AbsoluteFill, Img, staticFile} from 'remotion';
export default function GeneratedScene() {
  return (
    <AbsoluteFill>
      <Img src={staticFile('test.png')} style={{width: 100}} />
    </AbsoluteFill>
  );
}
"""
        assert validate_tsx_syntax(code) == []


# ---------------------------------------------------------------------------
# ensure_remotion_imports tests
# ---------------------------------------------------------------------------


class TestEnsureRemotionImports:
    """Test automatic import fixup for missing Remotion symbols."""

    def test_no_change_when_all_imported(self):
        code = """\
import {useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const x = interpolate(frame, [0, 30], [0, 1]);
  return null;
}
"""
        result = ensure_remotion_imports(code)
        assert result == code

    def test_adds_missing_useCurrentFrame(self):
        code = """\
import {AbsoluteFill} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  return <AbsoluteFill>{frame}</AbsoluteFill>;
}
"""
        result = ensure_remotion_imports(code)
        assert "useCurrentFrame" in result.split("from 'remotion'")[0]

    def test_adds_multiple_missing_imports(self):
        code = """\
import {AbsoluteFill} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const x = interpolate(frame, [0, 30], [0, 1]);
  return <AbsoluteFill />;
}
"""
        result = ensure_remotion_imports(code)
        import_section = result.split("from 'remotion'")[0]
        assert "useCurrentFrame" in import_section
        assert "useVideoConfig" in import_section
        assert "interpolate" in import_section

    def test_double_quote_import_style(self):
        code = """\
import {AbsoluteFill} from "remotion";

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  return <AbsoluteFill>{frame}</AbsoluteFill>;
}
"""
        result = ensure_remotion_imports(code)
        assert "useCurrentFrame" in result

    def test_no_existing_import_adds_new_line(self):
        code = """\
export default function GeneratedScene() {
  const frame = useCurrentFrame();
  return <div>{frame}</div>;
}
"""
        result = ensure_remotion_imports(code)
        assert "import {useCurrentFrame} from 'remotion'" in result

    def test_spring_added_when_used(self):
        code = """\
import {AbsoluteFill, useCurrentFrame} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  const scale = spring({frame, fps: 30});
  return <AbsoluteFill />;
}
"""
        result = ensure_remotion_imports(code)
        import_section = result.split("from 'remotion'")[0]
        assert "spring" in import_section

