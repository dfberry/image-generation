"""Custom exceptions for Remotion animation generation."""


class RemotionGenError(Exception):
    """Base exception for remotion-gen package.

    All remotion-gen exceptions inherit from this for catch-all handling.
    """
    pass


class LLMError(RemotionGenError):
    """Raised when an LLM API call fails or returns invalid output.

    Covers auth failures, rate limits, timeouts, and malformed responses.
    """
    pass


class RenderError(RemotionGenError):
    """Raised when the Remotion rendering subprocess fails.

    Covers npx/node not found, non-zero exit codes, and missing output files.
    """
    pass


class ValidationError(RemotionGenError):
    """Raised when a generated TSX component fails validation.

    Covers bracket mismatch, missing exports, forbidden imports, and
    structural issues detected before rendering.
    """
    pass


class ImageValidationError(RemotionGenError):
    """Raised when image input validation fails.

    Covers bad file paths, unsupported formats, oversized files, and
    symlink rejection.
    """
    pass


class AudioValidationError(RemotionGenError):
    """Raised when audio input validation fails.

    Covers bad file paths, unsupported formats, oversized files,
    excessive duration, and symlink rejection.
    """
    pass


class TTSError(RemotionGenError):
    """Raised when text-to-speech generation fails.

    Covers TTS provider errors, network failures, invalid voices,
    missing API keys, and output file creation failures.
    """
    pass
