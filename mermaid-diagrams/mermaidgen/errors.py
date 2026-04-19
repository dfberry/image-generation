"""Custom exceptions for mermaidgen."""


class MermaidError(Exception):
    """Base exception for mermaidgen."""
    pass


class MermaidSyntaxError(MermaidError):
    """Raised when Mermaid syntax is invalid."""
    pass


class RenderError(MermaidError):
    """Raised when mmdc rendering fails."""
    pass


class MmcdNotFoundError(MermaidError):
    """Raised when the mmdc binary is not found."""
    pass
