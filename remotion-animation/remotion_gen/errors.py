"""Custom exceptions for Remotion animation generation."""


class RemotionGenError(Exception):
    """Base exception for remotion-gen package."""
    pass


class LLMError(RemotionGenError):
    """LLM API call failed or returned invalid output."""
    pass


class RenderError(RemotionGenError):
    """Remotion rendering process failed."""
    pass


class ValidationError(RemotionGenError):
    """Generated component failed validation."""
    pass
