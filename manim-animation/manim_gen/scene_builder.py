"""Scene code builder and validator"""

import ast
import logging
import re
from pathlib import Path
from typing import Tuple

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


def validate_safety(code: str) -> None:
    """Check for unsafe operations in generated code
    
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
    
    # Check imports
    for node in ast.walk(tree):
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
        
        # Check for file I/O operations
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ("open", "exec", "eval", "__import__"):
                    raise ValidationError(f"Forbidden function call: {node.func.id}")


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


def build_scene(llm_output: str, output_path: Path) -> Tuple[str, Path]:
    """Build and validate Manim scene code, write to file
    
    Args:
        llm_output: Raw LLM response
        output_path: Path to write scene file
        
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
    
    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(code, encoding="utf-8")
    logger.info(f"Scene code written to {output_path}")
    
    return code, output_path
