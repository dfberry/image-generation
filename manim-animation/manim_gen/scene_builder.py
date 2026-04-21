"""Scene code builder and validator"""

import ast
import logging
import re
from pathlib import Path
from typing import Optional, Set, Tuple

from manim_gen.config import ALLOWED_IMPORTS
from manim_gen.errors import ValidationError

logger = logging.getLogger(__name__)

def extract_code_block(llm_output: str) -> str:
    """Extract Python code from LLM response (handle markdown blocks)

    Args:
        llm_output: Raw LLM response text

    Returns:
        Extracted Python code

    Raises:
        ValidationError: If no valid code block found
    """
    # Try to extract from markdown code block first
    match = re.search(r"```python\s*(.*?)\s*```", llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try plain code block without language tag
    match = re.search(r"```\s*(.*?)\s*```", llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no code block markers, assume entire output is code
    if "class GeneratedScene" in llm_output:
        return llm_output.strip()

    raise ValidationError("No valid Python code block found in LLM output")

def validate_syntax(code: str) -> None:
    """Validate Python syntax by compiling code

    Args:
        code: Python source code

    Raises:
        ValidationError: If code has syntax errors
    """
    try:
        compile(code, "<generated>", "exec")
    except SyntaxError as e:
        raise ValidationError(f"Generated code has syntax error: {e}")

# Dangerous built-in function names that must never appear in generated code
FORBIDDEN_CALLS = frozenset({
    "open", "exec", "eval", "__import__",
    "compile", "getattr", "setattr", "delattr",
    "globals", "locals", "vars", "dir",
    "breakpoint", "input",
})

# Names that should never be referenced (even without being called)
FORBIDDEN_NAMES = frozenset({
    "__import__", "__builtins__", "__loader__", "__spec__",
})

def validate_safety(code: str) -> None:
    """Check for unsafe operations in generated code.

    Validates AST nodes to block:
    - Forbidden imports (only ALLOWED_IMPORTS permitted)
    - Dangerous built-in calls (exec, eval, compile, getattr, etc.)
    - Attribute-based bypass vectors (e.g. builtins.open)
    - References to dangerous names (__import__, __builtins__)

    Args:
        code: Python source code

    Raises:
        ValidationError: If code contains forbidden operations
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Syntax validation is done separately
        return

    for node in ast.walk(tree):
        # --- Import statements ---
        if isinstance(node, ast.Import):
            for alias in node.names:
                base_module = alias.name.split(".")[0]
                if base_module not in ALLOWED_IMPORTS:
                    raise ValidationError(
                        f"Forbidden import: {alias.name}. "
                        f"Only {ALLOWED_IMPORTS} are allowed."
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_module = node.module.split(".")[0]
                if base_module not in ALLOWED_IMPORTS:
                    raise ValidationError(
                        f"Forbidden import from: {node.module}. "
                        f"Only {ALLOWED_IMPORTS} are allowed."
                    )

        # --- Dangerous function calls ---
        elif isinstance(node, ast.Call):
            # Direct calls: open(), exec(), compile(), getattr(), etc.
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    raise ValidationError(
                        f"Forbidden function call: {node.func.id}"
                    )

            # Attribute calls: obj.exec(), builtins.open(), etc.
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in FORBIDDEN_CALLS:
                    raise ValidationError(
                        f"Forbidden attribute call: {node.func.attr}"
                    )

        # --- Dangerous name references ---
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                raise ValidationError(
                    f"Forbidden name reference: {node.id}"
                )

def validate_scene_class(code: str) -> None:
    """Ensure code contains GeneratedScene class

    Args:
        code: Python source code

    Raises:
        ValidationError: If GeneratedScene class not found
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return  # Syntax validation happens separately

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "GeneratedScene":
            return

    raise ValidationError("Generated code must contain a class named 'GeneratedScene'")

def build_scene(
    llm_output: str, output_path: Path, image_filenames: Optional[Set[str]] = None
) -> Tuple[str, Path]:
    """Build and validate Manim scene code, write to file

    Args:
        llm_output: Raw LLM response
        output_path: Path to write scene file
        image_filenames: If provided, also run image-operation validation

    Returns:
        Tuple of (validated code, output path)

    Raises:
        ValidationError: If code validation fails
    """
    logger.info("Extracting code from LLM output")
    code = extract_code_block(llm_output)

    logger.info("Validating syntax")
    validate_syntax(code)

    logger.info("Validating safety")
    validate_safety(code)

    logger.info("Validating scene class")
    validate_scene_class(code)

    if image_filenames:
        logger.info("Validating image operations")
        validate_image_operations(code, image_filenames)

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(code, encoding="utf-8")
    logger.info(f"Scene code written to {output_path}")

    return code, output_path


# --- Image operation validation ---

# File-write method names that must be blocked in generated code
_FILE_WRITE_CALLS = frozenset({
    "write_text", "write_bytes", "unlink", "rmdir",
    "remove", "rmtree", "rename",
})


def validate_image_operations(code: str, allowed_filenames: Set[str]) -> None:
    """Validate that generated code only uses images safely.

    Rules:
    - ImageMobject must be called with a string literal filename
    - That filename must be in the allowed set
    - File-write operations are blocked

    Args:
        code: Python source code
        allowed_filenames: Set of permitted image filenames

    Raises:
        ValidationError: If code violates image-safety rules
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return  # Syntax validation handles this

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        # Check for ImageMobject calls
        is_image_mobject = (
            (isinstance(func, ast.Name) and func.id == "ImageMobject")
            or (isinstance(func, ast.Attribute) and func.attr == "ImageMobject")
        )

        if is_image_mobject:
            if not node.args:
                raise ValidationError(
                    "ImageMobject must be called with a filename argument"
                )
            arg = node.args[0]
            if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                raise ValidationError(
                    "ImageMobject filename must be a string literal, "
                    "not a variable or expression"
                )
            if arg.value not in allowed_filenames:
                raise ValidationError(
                    f"ImageMobject references unknown file '{arg.value}'. "
                    f"Allowed: {sorted(allowed_filenames)}"
                )

        # Block file-write operations
        if isinstance(func, ast.Attribute) and func.attr in _FILE_WRITE_CALLS:
            raise ValidationError(
                f"File write operation not allowed: {func.attr}"
            )
