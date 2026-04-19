"""Mermaid diagram templates and template registry."""

from abc import ABC, abstractmethod


class MermaidTemplate(ABC):
    """Abstract base class for Mermaid diagram templates."""

    name: str
    description: str

    @abstractmethod
    def render(self, **kwargs: object) -> str:
        """Render the template with the given parameters.

        Returns:
            Valid Mermaid diagram syntax string.
        """

    def suggest_filename(self) -> str:
        """Suggest a filename (without extension) for the rendered diagram."""
        return self.name


class TemplateRegistry:
    """Registry of available Mermaid diagram templates."""

    def __init__(self) -> None:
        self._templates: dict[str, MermaidTemplate] = {}

    def register(self, template: MermaidTemplate) -> None:
        """Register a template instance."""
        self._templates[template.name] = template

    def get(self, name: str) -> MermaidTemplate | None:
        """Get a template by name, or None if not found."""
        return self._templates.get(name)

    def list_available(self) -> list[dict]:
        """Return list of available templates with metadata."""
        return [
            {
                "name": t.name,
                "description": t.description,
            }
            for t in sorted(self._templates.values(), key=lambda t: t.name)
        ]


# ---------------------------------------------------------------------------
# Concrete templates
# ---------------------------------------------------------------------------


class FlowchartSimpleTemplate(MermaidTemplate):
    """Linear top-down flowchart from a list of steps."""

    name = "flowchart_simple"
    description = "A linear top-down flowchart generated from a list of steps."

    def render(self, **kwargs: object) -> str:
        steps: list[str] = kwargs.get("steps", [])  # type: ignore[assignment]

        if not steps or len(steps) < 2:
            raise ValueError("'steps' must be a list with at least 2 items")

        lines = ["flowchart TD"]
        for i, step in enumerate(steps):
            node_id = chr(65 + i)  # A, B, C, ...
            lines.append(f"    {node_id}[\"{step}\"]")

        for i in range(len(steps) - 1):
            src = chr(65 + i)
            dst = chr(65 + i + 1)
            lines.append(f"    {src} --> {dst}")

        return "\n".join(lines)

    def suggest_filename(self) -> str:
        return "flowchart_simple"


class SequenceAPITemplate(MermaidTemplate):
    """Sequence diagram from participants and messages."""

    name = "sequence_api"
    description = "Sequence diagram with explicit participants and messages."

    def render(self, **kwargs: object) -> str:
        participants: list[str] = kwargs.get("participants", [])  # type: ignore[assignment]
        messages: list[tuple[str, str, str]] = kwargs.get("messages", [])  # type: ignore[assignment]

        if not participants:
            raise ValueError("'participants' must be a non-empty list of strings")
        if not messages:
            raise ValueError("'messages' must be a non-empty list of (from, to, label) tuples")

        lines = ["sequenceDiagram"]
        for p in participants:
            lines.append(f"    participant {p}")
        for frm, to, label in messages:
            lines.append(f"    {frm}->>{to}: {label}")

        return "\n".join(lines)

    def suggest_filename(self) -> str:
        return "sequence_api"


class ClassInheritanceTemplate(MermaidTemplate):
    """Class diagram with a parent and child classes."""

    name = "class_inheritance"
    description = "Class diagram showing a parent class and its children."

    def render(self, **kwargs: object) -> str:
        parent: str = kwargs.get("parent", "")  # type: ignore[assignment]
        children: list[str] = kwargs.get("children", [])  # type: ignore[assignment]

        if not parent:
            raise ValueError("'parent' is required")
        if not children:
            raise ValueError("'children' must be a non-empty list of class names")

        lines = ["classDiagram"]
        lines.append(f"    class {parent}")
        for child in children:
            lines.append(f"    class {child}")
            lines.append(f"    {parent} <|-- {child}")

        return "\n".join(lines)

    def suggest_filename(self) -> str:
        return "class_inheritance"


class ERDatabaseTemplate(MermaidTemplate):
    """ER diagram from a list of entity dicts."""

    name = "er_database"
    description = "Entity-relationship diagram from entity definitions with attributes."

    def render(self, **kwargs: object) -> str:
        entities: list[dict] = kwargs.get("entities", [])  # type: ignore[assignment]

        if not entities or len(entities) < 1:
            raise ValueError("'entities' must be a non-empty list of dicts with 'name' and 'attributes'")

        lines = ["erDiagram"]
        for entity in entities:
            name = entity.get("name", "")
            attributes = entity.get("attributes", [])
            if not name:
                raise ValueError("Each entity dict must have a 'name' key")
            lines.append(f"    {name} {{")
            for attr in attributes:
                lines.append(f"        string {attr}")
            lines.append("    }")

        # Connect first entity to all others (one-to-many)
        if len(entities) > 1:
            primary = entities[0]["name"]
            for entity in entities[1:]:
                lines.append(f"    {primary} ||--o{{ {entity['name']} : has")

        return "\n".join(lines)

    def suggest_filename(self) -> str:
        return "er_database"


# ---------------------------------------------------------------------------
# Module-level default registry with all templates pre-registered
# ---------------------------------------------------------------------------

default_registry = TemplateRegistry()
default_registry.register(FlowchartSimpleTemplate())
default_registry.register(SequenceAPITemplate())
default_registry.register(ClassInheritanceTemplate())
default_registry.register(ERDatabaseTemplate())
