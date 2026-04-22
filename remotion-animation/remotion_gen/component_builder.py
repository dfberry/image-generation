"""Component builder - validates and writes Remotion components.

Includes import fixup, bracket validation, and retry-ready validation
to compensate for smaller LLMs (e.g. llama3 8B) that frequently produce
structurally invalid TSX.
"""

import logging
import re
from pathlib import Path
from typing import Optional

from remotion_gen.errors import ValidationError

logger = logging.getLogger(__name__)

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


def validate_tsx_syntax(code: str) -> list[str]:
    """Check for bracket/paren/brace mismatches in TSX code.

    Returns a list of error descriptions. Empty list means valid.
    This catches the most common llama3 failure mode: unclosed or
    extra brackets in interpolate()/spring() calls.
    """
    errors: list[str] = []

    # Track bracket pairs
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = set(pairs.values())
    stack: list[tuple[str, int]] = []

    # Strip string literals and template literals to avoid false positives
    cleaned = re.sub(r"`[^`]*`", '""', code)
    cleaned = re.sub(r"'[^']*'", '""', cleaned)
    cleaned = re.sub(r'"[^"]*"', '""', cleaned)
    # Strip single-line comments
    cleaned = re.sub(r"//.*$", "", cleaned, flags=re.MULTILINE)
    # Strip multi-line comments
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

    for i, ch in enumerate(cleaned):
        if ch in pairs:
            stack.append((ch, i))
        elif ch in closers:
            if not stack:
                errors.append(
                    f"Unexpected closing '{ch}' at position {i} with no matching opener"
                )
            else:
                opener, open_pos = stack.pop()
                expected = pairs[opener]
                if ch != expected:
                    errors.append(
                        f"Mismatched bracket: '{opener}' at pos {open_pos} "
                        f"closed by '{ch}' at pos {i} (expected '{expected}')"
                    )

    for opener, pos in stack:
        errors.append(f"Unclosed '{opener}' at position {pos}")

    # Check for JSX-specific issues: unclosed tags
    # Simple heuristic: count <Tag vs </Tag for known Remotion components
    for tag in ["AbsoluteFill", "Sequence", "div", "Img", "Audio"]:
        opens = len(re.findall(rf"<{tag}[\s>]", code))
        self_closes = len(re.findall(rf"<{tag}\s[^>]*/\s*>", code))
        closes = len(re.findall(rf"</{tag}>", code))
        if opens - self_closes > closes:
            errors.append(f"Unclosed <{tag}> tag ({opens} opens, {self_closes} self-closes, {closes} closes)")

    return errors


# All Remotion symbols that LLMs commonly use but forget to import.
_REMOTION_HOOKS = [
    "useCurrentFrame",
    "useVideoConfig",
    "spring",
    "interpolate",
    "Sequence",
    "AbsoluteFill",
    "Img",
    "staticFile",
    "Audio",
    "Video",
    "OffthreadVideo",
    "Series",
    "Easing",
    "random",
    "delayRender",
    "continueRender",
    "Loop",
    "Still",
    "Composition",
]


def ensure_remotion_imports(code: str) -> str:
    """Ensure all used Remotion symbols are imported.

    LLMs often use hooks like useCurrentFrame without importing them.
    This scans the code for known Remotion symbols and adds any
    missing ones to the existing import statement.

    Args:
        code: TSX component source.

    Returns:
        Code with missing Remotion imports added.
    """
    missing = []
    for hook in _REMOTION_HOOKS:
        # Use word-boundary check to avoid substring false positives
        # (e.g. "Video" matching inside "useVideoConfig")
        if re.search(rf"\b{hook}\b", code):
            import_pattern = re.compile(
                rf"""import\s+\{{[^}}]*\b{hook}\b[^}}]*\}}\s+from\s+['"]remotion['"]"""
            )
            if not import_pattern.search(code):
                missing.append(hook)

    if not missing:
        return code

    additions = ", ".join(missing)
    replaced = code.replace(
        "} from 'remotion'",
        f", {additions}}} from 'remotion'",
        1,
    )
    if replaced == code:
        replaced = code.replace(
            '} from "remotion"',
            f', {additions}}} from "remotion"',
            1,
        )
    if replaced == code:
        import_line = f"import {{{additions}}} from 'remotion';\n"
        replaced = import_line + code

    # Validate that all missing imports were actually injected
    for hook in missing:
        import_check = re.compile(
            rf"""import\s+\{{[^}}]*\b{hook}\b[^}}]*\}}\s+from\s+['"]remotion['"]"""
        )
        if not import_check.search(replaced):
            raise ValidationError(
                f"Failed to inject required Remotion import '{hook}'. "
                "The generated code structure may be too unusual to auto-fix."
            )

    return replaced


def build_validation_error_context(code: str, errors: list[str]) -> str:
    """Format validation errors into a prompt snippet for LLM retry.

    When validate_tsx_syntax() finds issues, this builds a message that
    can be appended to a follow-up LLM prompt so the model can fix its
    own mistakes. This is the retry logic stub — callers can feed this
    into a second LLM call.

    Args:
        code: The invalid TSX code.
        errors: List of error strings from validate_tsx_syntax().

    Returns:
        A formatted error context string suitable for LLM re-prompting.
    """
    error_list = "\n".join(f"  - {e}" for e in errors)
    return (
        "The TSX code you generated has structural errors:\n"
        f"{error_list}\n\n"
        "Please fix these issues and return ONLY the corrected TSX code. "
        "Pay special attention to matching every opening bracket, parenthesis, "
        "and brace with its closing counterpart."
    )


def write_component(
    code: str,
    project_root: Path,
    debug: bool = False,
    image_filename: Optional[str] = None,
    audio_filenames: Optional[list[str]] = None,
) -> Path:
    """Write generated component to Remotion project.

    Runs full validation pipeline: import fixup, syntax check, component
    structure validation, and optional image/audio path validation.

    Args:
        code: TSX component source code.
        project_root: Path to remotion-project directory.
        debug: Save a debug copy of the component.
        image_filename: If set, inject image imports and validate paths.
        audio_filenames: If set, inject audio imports and validate paths.

    Returns:
        Path to written GeneratedScene.tsx

    Raises:
        ValidationError: If component validation fails
    """
    if image_filename:
        code = inject_image_imports(code, image_filename)
        validate_image_paths(code, image_filename)

    if audio_filenames:
        code = inject_audio_imports(code, audio_filenames)
        validate_audio_paths(code, audio_filenames)

    code = ensure_remotion_imports(code)

    # Bracket/syntax check before structural validation
    syntax_errors = validate_tsx_syntax(code)
    if syntax_errors:
        logger.warning("TSX syntax issues found: %s", syntax_errors)
        raise ValidationError(
            "Generated TSX has structural syntax errors: "
            + "; ".join(syntax_errors)
        )

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


def validate_image_paths(code: str, allowed_image_filename: str) -> None:
    """Validate that generated code only references the approved image.

    Blocks file:// URLs, path traversal, and staticFile() calls
    that don't match the allowed filename.

    Raises:
        ValidationError: If unsafe image references are found.
    """
    _validate_static_file_refs(code, [allowed_image_filename], "image")


def inject_image_imports(code: str, image_filename: str) -> str:
    """Ensure Img and staticFile imports exist and add image constant.

    Args:
        code: TSX component source.
        image_filename: Sanitized filename in public/.

    Returns:
        Modified code with image imports and constant.

    Raises:
        ValidationError: If required imports could not be injected.
    """
    # Ensure Img is imported
    if "Img" not in code:
        additions = (
            "Img, staticFile" if "staticFile" not in code else "Img"
        )
        code = code.replace(
            "} from 'remotion'",
            f", {additions}}} from 'remotion'",
            1,
        )
        # Fallback: if the above didn't work (double-quote style)
        if "Img" not in code:
            code = code.replace(
                '} from "remotion"',
                f', {additions}}} from "remotion"',
                1,
            )

    # Ensure staticFile is imported
    if "staticFile" not in code:
        code = code.replace(
            "} from 'remotion'",
            ", staticFile} from 'remotion'",
            1,
        )
        if "staticFile" not in code:
            code = code.replace(
                '} from "remotion"',
                ', staticFile} from "remotion"',
                1,
            )

    # Validate that Img and staticFile are now present
    if "Img" not in code:
        raise ValidationError(
            "Failed to inject 'Img' import into generated component. "
            "The code may be missing a remotion import statement."
        )
    if "staticFile" not in code:
        raise ValidationError(
            "Failed to inject 'staticFile' import into generated component. "
            "The code may be missing a remotion import statement."
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


def _validate_static_file_refs(
    code: str, allowed_filenames: list[str], asset_type: str = "file"
) -> None:
    """Shared staticFile() validation for images and audio.

    Blocks file:// URLs, path traversal, data: URIs, and non-literal calls.
    Validates that all staticFile() references match allowed filenames.

    Args:
        code: TSX component source code.
        allowed_filenames: List of approved filenames (e.g. ["image.png", "audio.mp3"]).
        asset_type: Type of asset for error messages ("image" or "audio").

    Raises:
        ValidationError: If unsafe references are found.
    """
    if re.search(r"file://", code, re.IGNORECASE):
        raise ValidationError(
            "file:// URLs are not allowed in generated components. "
            "Use staticFile() to reference assets."
        )

    # Block URL-encoded file:// (file%3A%2F%2F and variants)
    if re.search(r"file%3A%2F%2F", code, re.IGNORECASE):
        raise ValidationError(
            "Encoded file:// URLs are not allowed in generated components. "
            "Use staticFile() to reference assets."
        )

    # Block data: URIs (data:image/..., data:audio/..., etc.)
    if re.search(r"data:", code, re.IGNORECASE):
        raise ValidationError(
            "data: URIs are not allowed in generated components. "
            "Use staticFile() to reference assets."
        )

    if "../" in code or "..\\" in code:
        raise ValidationError(
            "Path traversal ('../' or '..\\') is not allowed "
            "in generated components."
        )

    # Block URL-encoded path traversal (%2E%2E%2F, %2e%2e%2f, etc.)
    if re.search(r"%2E%2E%2F", code, re.IGNORECASE):
        raise ValidationError(
            "Encoded path traversal is not allowed "
            "in generated components."
        )

    # Block template literal backticks in staticFile() calls
    if re.search(r"staticFile\s*\(\s*`", code):
        raise ValidationError(
            "Template literals are not allowed in staticFile() calls. "
            "Use string literals only."
        )

    # Check staticFile() calls reference only the allowed filenames
    static_file_re = re.compile(r"""staticFile\s*\(\s*['"]([^'"]+)['"]\s*\)""")
    for match in static_file_re.finditer(code):
        referenced = match.group(1)
        if referenced not in allowed_filenames:
            raise ValidationError(
                f"staticFile() references '{referenced}' but only "
                f"{allowed_filenames} are allowed."
            )

    # Reject non-literal staticFile() calls (template literals, variables, etc.)
    all_calls = re.findall(r"staticFile\s*\(", code)
    literal_calls = static_file_re.findall(code)
    if len(all_calls) > len(literal_calls):
        raise ValidationError(
            "staticFile() must only be called with string literals, "
            "not variables or template expressions."
        )


def validate_audio_paths(code: str, allowed_audio_filenames: list[str]) -> None:
    """Validate that generated code only references the approved audio files.

    Blocks file:// URLs, path traversal, and staticFile() calls
    that don't match the allowed filenames.

    Args:
        code: TSX component source code.
        allowed_audio_filenames: List of approved audio filenames.

    Raises:
        ValidationError: If unsafe audio references are found.
    """
    _validate_static_file_refs(code, allowed_audio_filenames, "audio")


def inject_audio_imports(code: str, audio_filenames: list[str]) -> str:
    """Ensure Audio and staticFile imports exist.

    Args:
        code: TSX component source.
        audio_filenames: List of audio filenames in public/.

    Returns:
        Modified code with audio imports.

    Raises:
        ValidationError: If required imports could not be injected.
    """
    # Ensure Audio is imported
    if "Audio" not in code:
        additions = (
            "Audio, staticFile" if "staticFile" not in code else "Audio"
        )
        code = code.replace(
            "} from 'remotion'",
            f", {additions}}} from 'remotion'",
            1,
        )
        # Fallback: if the above didn't work (double-quote style)
        if "Audio" not in code:
            code = code.replace(
                '} from "remotion"',
                f', {additions}}} from "remotion"',
                1,
            )

    # Ensure staticFile is imported
    if "staticFile" not in code:
        code = code.replace(
            "} from 'remotion'",
            ", staticFile} from 'remotion'",
            1,
        )
        if "staticFile" not in code:
            code = code.replace(
                '} from "remotion"',
                ', staticFile} from "remotion"',
                1,
            )

    # Validate that Audio and staticFile are now present
    if "Audio" not in code:
        raise ValidationError(
            "Failed to inject 'Audio' import into generated component. "
            "The code may be missing a remotion import statement."
        )
    if "staticFile" not in code:
        raise ValidationError(
            "Failed to inject 'staticFile' import into generated component. "
            "The code may be missing a remotion import statement."
        )

    return code

