"""Custom exceptions for manim_gen"""


class ManimGenError(Exception):
    """Base exception for all manim_gen errors.

    All manim_gen exceptions inherit from this for catch-all handling.
    """

    pass


class LLMError(ManimGenError):
    """Raised when an LLM API call fails or returns an invalid response.

    Covers auth failures, rate limits, timeouts, and malformed responses.
    """

    pass


class RenderError(ManimGenError):
    """Raised when the Manim render subprocess fails.

    Covers manim CLI not found, non-zero exit codes, and missing output files.
    """

    pass


class ValidationError(ManimGenError):
    """Raised when generated code fails validation checks.

    Covers AST parse errors, forbidden imports, missing GeneratedScene class,
    and structural issues detected before rendering.
    """

    pass


class ImageValidationError(ManimGenError):
    """Raised when image validation fails.

    Covers bad file paths, unsupported formats, oversized files, symlink
    rejection, and copy failures.
    """

    pass
