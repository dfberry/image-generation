"""Component builder - validates and writes Remotion components."""

import re
from pathlib import Path

from remotion_gen.errors import ValidationError


def validate_component(code: str) -> None:
    """Validate generated Remotion component code.
    
    Args:
        code: TSX component code
        
    Raises:
        ValidationError: If component is invalid
    """
    # Check for required imports
    if "from 'remotion'" not in code and 'from "remotion"' not in code:
        raise ValidationError("Component must import from 'remotion' package")
    
    # Check for default export
    if "export default" not in code:
        raise ValidationError("Component must have a default export")
    
    # Check for GeneratedScene function
    if "GeneratedScene" not in code:
        raise ValidationError("Component must be named GeneratedScene")
    
    # Check for basic React patterns
    if "return" not in code:
        raise ValidationError("Component must have a return statement")


def write_component(code: str, project_root: Path, debug: bool = False) -> Path:
    """Write generated component to Remotion project.
    
    Args:
        code: TSX component code
        project_root: Path to remotion-project directory
        debug: If True, also save to outputs/ for inspection
        
    Returns:
        Path to written GeneratedScene.tsx
        
    Raises:
        ValidationError: If component validation fails
    """
    validate_component(code)
    
    component_path = project_root / "src" / "GeneratedScene.tsx"
    component_path.write_text(code, encoding="utf-8")
    
    if debug:
        debug_path = project_root.parent / "outputs" / "GeneratedScene.debug.tsx"
        debug_path.write_text(code, encoding="utf-8")
    
    return component_path
