"""Mermaid syntax validation."""

from .errors import MermaidSyntaxError

VALID_DIAGRAM_TYPES: tuple[str, ...] = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "erDiagram",
    "stateDiagram",
    "gantt",
    "pie",
    "gitgraph",
    "journey",
    "mindmap",
    "timeline",
    "quadrantChart",
    "sankey",
    "xychart",
    "block",
    "packet",
    "architecture",
    "kanban",
)


class MermaidValidator:
    """Validates Mermaid diagram syntax."""

    @staticmethod
    def validate(syntax: str) -> bool:
        """Validate Mermaid syntax structure.

        Checks that the input is non-empty and that the first meaningful
        (non-empty, non-comment) line starts with a known diagram type keyword.

        Args:
            syntax: Raw Mermaid diagram syntax string.

        Returns:
            True if syntax passes validation.

        Raises:
            MermaidSyntaxError: If syntax is empty/whitespace-only or missing
                a recognised diagram type on the first meaningful line.
        """
        if not syntax or not syntax.strip():
            raise MermaidSyntaxError("Mermaid syntax cannot be empty")

        # Find the first non-empty, non-comment line
        first_line: str | None = None
        for line in syntax.strip().splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("%%"):
                continue
            first_line = stripped
            break

        if first_line is None:
            raise MermaidSyntaxError("Mermaid syntax cannot be empty")

        has_type = any(first_line.startswith(dt) for dt in VALID_DIAGRAM_TYPES)
        if not has_type:
            raise MermaidSyntaxError(
                f"Missing diagram type declaration. First line must start with one of: "
                f"{', '.join(VALID_DIAGRAM_TYPES)}. Got: '{first_line}'"
            )

        return True
