"""Component builder - validates and writes Remotion components."""

import re
from pathlib import Path

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


def write_component(
    code: str,
    project_root: Path,
    debug: bool = False,
) -> Path:
    """Write generated component to Remotion project.

    Returns:
        Path to written GeneratedScene.tsx

    Raises:
        ValidationError: If component validation fails
    """
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
