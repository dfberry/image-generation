"""Component builder - validates and writes Remotion components."""

import re
from pathlib import Path
from typing import Optional

from remotion_gen.errors import ValidationError

# Node.js built-in modules that are dangerous in rendered components.
DANGEROUS_IMPORTS = frozenset(
    [
        "fs",
        "node:fs",
        "fs/promises",
        "node:fs/promises",
        "child_process",
        "node:child_process",
        "http",
        "node:http",
        "https",
        "node:https",
        "net",
        "node:net",
        "os",
        "node:os",
        "path",
        "node:path",
        "crypto",
        "node:crypto",
        "process",
        "node:process",
        "cluster",
        "node:cluster",
        "dgram",
        "node:dgram",
        "dns",
        "node:dns",
        "tls",
        "node:tls",
        "vm",
        "node:vm",
        "worker_threads",
        "node:worker_threads",
    ]
)

_DANGEROUS_PREFIXES = tuple(
    f"{mod}/"
    for mod in [
        "fs",
        "child_process",
        "http",
        "https",
        "net",
        "os",
        "crypto",
    ]
)

_IMPORT_FROM_RE = re.compile(
    r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_IMPORT_BARE_RE = re.compile(
    r"""import\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_REQUIRE_RE = re.compile(
    r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE,
)


def validate_imports(code: str) -> None:
    """Check TSX code for dangerous Node.js imports.

    Raises:
        ValidationError: If a dangerous import is detected.
    """
    found_modules: list[str] = []
    found_modules.extend(_IMPORT_FROM_RE.findall(code))
    found_modules.extend(_IMPORT_BARE_RE.findall(code))
    found_modules.extend(_REQUIRE_RE.findall(code))

    for mod in found_modules:
        if mod in DANGEROUS_IMPORTS or mod.startswith(
            _DANGEROUS_PREFIXES
        ):
            raise ValidationError(
                f"Dangerous import detected: '{mod}' is not "
                "allowed for security reasons. "
                "Only Remotion and React imports are permitted."
            )


def validate_component(code: str) -> None:
    """Validate generated Remotion component code.

    Raises:
        ValidationError: If component is invalid
    """
    validate_imports(code)

    if (
        "from 'remotion'" not in code
        and 'from "remotion"' not in code
    ):
        raise ValidationError(
            "Component must import from 'remotion' package"
        )

    if "export default" not in code:
        raise ValidationError(
            "Component must have a default export"
        )

    if "GeneratedScene" not in code:
        raise ValidationError(
            "Component must be named GeneratedScene"
        )

    if "return" not in code:
        raise ValidationError(
            "Component must have a return statement"
        )


def validate_image_paths(code: str, allowed_image_filename: str) -> None:
    """Validate that generated code only references the approved image.

    Blocks file:// URLs, path traversal, and staticFile() calls
    that don't match the allowed filename.

    Raises:
        ValidationError: If unsafe image references are found.
    """
    if "file://" in code:
        raise ValidationError(
            "file:// URLs are not allowed in generated components. "
            "Use staticFile() to reference images."
        )

    if "../" in code:
        raise ValidationError(
            "Path traversal ('..\\') is not allowed in generated components."
        )

    # Check staticFile() calls reference only the allowed filename
    static_file_re = re.compile(r"""staticFile\s*\(\s*['"]([^'"]+)['"]\s*\)""")
    for match in static_file_re.finditer(code):
        referenced = match.group(1)
        if referenced != allowed_image_filename:
            raise ValidationError(
                f"staticFile() references '{referenced}' but only "
                f"'{allowed_image_filename}' is allowed."
            )


def inject_image_imports(code: str, image_filename: str) -> str:
    """Ensure Img and staticFile imports exist and add image constant.

    Args:
        code: TSX component source.
        image_filename: Sanitized filename in public/.

    Returns:
        Modified code with image imports and constant.
    """
    # Ensure Img is imported
    if "Img" not in code:
        code = code.replace(
            "from 'remotion'",
            "Img, staticFile, " if "staticFile" not in code else "Img, ",
            1,
        )
        # Fallback: if the above didn't work (double-quote style)
        if "Img" not in code:
            code = code.replace(
                'from "remotion"',
                "Img, staticFile, " if "staticFile" not in code else "Img, ",
                1,
            )

    # Ensure staticFile is imported
    if "staticFile" not in code:
        code = code.replace(
            "from 'remotion'",
            "staticFile, ",
            1,
        )
        if "staticFile" not in code:
            code = code.replace(
                'from "remotion"',
                "staticFile, ",
                1,
            )

    # Add image source constant if not present
    image_const = f"const imageSrc = staticFile('{image_filename}');"
    if image_const not in code and "imageSrc" not in code:
        # Insert after the last import line
        lines = code.split("\n")
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import "):
                last_import_idx = i
        lines.insert(last_import_idx + 1, f"\n{image_const}\n")
        code = "\n".join(lines)

    return code


def write_component(
    code: str,
    project_root: Path,
    debug: bool = False,
    image_filename: Optional[str] = None,
) -> Path:
    """Write generated component to Remotion project.

    Args:
        code: TSX component source code.
        project_root: Path to remotion-project directory.
        debug: Save a debug copy of the component.
        image_filename: If set, inject image imports and validate paths.

    Returns:
        Path to written GeneratedScene.tsx

    Raises:
        ValidationError: If component validation fails
    """
    if image_filename:
        code = inject_image_imports(code, image_filename)
        validate_image_paths(code, image_filename)

    validate_component(code)

    component_path = project_root / "src" / "GeneratedScene.tsx"
    component_path.write_text(code, encoding="utf-8")

    if debug:
        debug_path = (
            project_root.parent
            / "outputs"
            / "GeneratedScene.debug.tsx"
        )
        debug_path.write_text(code, encoding="utf-8")

    return component_path
