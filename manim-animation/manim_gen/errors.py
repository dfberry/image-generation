"""Custom exceptions for manim_gen"""

class ManimGenError(Exception):
    """Base exception for all manim_gen errors"""

    pass

class LLMError(ManimGenError):
    """Raised when LLM API call fails or returns invalid response"""

    pass

class RenderError(ManimGenError):
    """Raised when Manim render subprocess fails"""

    pass

class ValidationError(ManimGenError):
    """Raised when generated code fails validation checks"""

    pass

class ImageValidationError(ManimGenError):
    """Raised when image validation fails (bad path, format, size, or symlink)"""

    pass
