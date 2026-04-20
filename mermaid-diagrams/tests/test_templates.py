"""Tests for TemplateRegistry and all four concrete templates.

Tests matched against Trinity's actual implementation in templates.py:
- TemplateRegistry: register(), get(name) -> template | None, list_available()
- FlowchartSimpleTemplate: render(steps=list[str], title=str)
- SequenceAPITemplate: render(participants=list[str], messages=list[tuple])
- ClassInheritanceTemplate: render(parent=str, children=list[str])
- ERDatabaseTemplate: render(entities=list[dict])
- All templates: suggest_filename() -> str (no params)
- Module-level default_registry has all 4 registered
"""

import pytest

from mermaidgen.templates import (
    TemplateRegistry,
    FlowchartSimpleTemplate,
    SequenceAPITemplate,
    ClassInheritanceTemplate,
    ERDatabaseTemplate,
    default_registry,
)
from mermaidgen.validators import MermaidValidator


# =========================================================================
# TemplateRegistry tests
# =========================================================================


class TestTemplateRegistry:
    """Tests for the TemplateRegistry."""

    def test_registry_list_returns_four_or_more(self):
        """default_registry.list_available() returns at least 4 templates."""
        templates = default_registry.list_available()
        assert len(templates) >= 4

    def test_registry_list_contains_expected_names(self):
        names = [t["name"] for t in default_registry.list_available()]
        assert "flowchart_simple" in names
        assert "sequence_api" in names
        assert "class_inheritance" in names
        assert "er_database" in names

    def test_registry_get_known(self):
        """get('flowchart_simple') returns the template instance."""
        tmpl = default_registry.get("flowchart_simple")
        assert tmpl is not None
        assert tmpl.name == "flowchart_simple"

    def test_registry_get_unknown_returns_none(self):
        """get('nonexistent') returns None — does NOT raise."""
        result = default_registry.get("nonexistent")
        assert result is None

    def test_empty_registry_has_no_templates(self):
        """A freshly created registry is empty."""
        reg = TemplateRegistry()
        assert reg.list_available() == []

    def test_register_and_retrieve(self):
        """register() then get() round-trips correctly."""
        reg = TemplateRegistry()
        tmpl = FlowchartSimpleTemplate()
        reg.register(tmpl)
        assert reg.get("flowchart_simple") is tmpl


# =========================================================================
# FlowchartSimpleTemplate tests
# =========================================================================


class TestFlowchartSimpleTemplate:
    """Tests for FlowchartSimpleTemplate."""

    def test_render_with_steps(self):
        t = FlowchartSimpleTemplate()
        result = t.render(steps=["Start", "Process", "End"])
        assert "flowchart TD" in result
        assert "Start" in result
        assert "Process" in result
        assert "End" in result
        assert "-->" in result

    def test_render_validates_as_mermaid(self):
        t = FlowchartSimpleTemplate()
        result = t.render(steps=["A", "B", "C"])
        assert MermaidValidator.validate(result) is True

    def test_render_with_title_kwarg(self):
        t = FlowchartSimpleTemplate()
        # title is accepted but doesn't appear in the flowchart TD line;
        # just ensure it doesn't raise.
        result = t.render(steps=["X", "Y"], title="My Flow")
        assert "flowchart TD" in result

    def test_render_missing_steps_raises(self):
        t = FlowchartSimpleTemplate()
        with pytest.raises(ValueError):
            t.render()

    def test_render_single_step_raises(self):
        t = FlowchartSimpleTemplate()
        with pytest.raises(ValueError, match="at least 2"):
            t.render(steps=["Only"])

    def test_suggest_filename(self):
        t = FlowchartSimpleTemplate()
        name = t.suggest_filename()
        assert isinstance(name, str)
        assert len(name) > 0
        assert name == "flowchart_simple"


# =========================================================================
# SequenceAPITemplate tests
# =========================================================================


class TestSequenceAPITemplate:
    """Tests for SequenceAPITemplate."""

    def test_render_with_participants_and_messages(self):
        t = SequenceAPITemplate()
        result = t.render(
            participants=["Client", "Server"],
            messages=[("Client", "Server", "GET /api")]
        )
        assert "sequenceDiagram" in result
        assert "participant Client" in result
        assert "participant Server" in result
        assert "GET /api" in result

    def test_render_validates_as_mermaid(self):
        t = SequenceAPITemplate()
        result = t.render(
            participants=["Alice", "Bob"],
            messages=[("Alice", "Bob", "Hello")]
        )
        assert MermaidValidator.validate(result) is True

    def test_render_missing_participants_raises(self):
        t = SequenceAPITemplate()
        with pytest.raises(ValueError, match="participants"):
            t.render(messages=[("A", "B", "msg")])

    def test_render_missing_messages_raises(self):
        t = SequenceAPITemplate()
        with pytest.raises(ValueError, match="messages"):
            t.render(participants=["A", "B"])

    def test_suggest_filename(self):
        t = SequenceAPITemplate()
        name = t.suggest_filename()
        assert isinstance(name, str)
        assert name == "sequence_api"


# =========================================================================
# ClassInheritanceTemplate tests
# =========================================================================


class TestClassInheritanceTemplate:
    """Tests for ClassInheritanceTemplate."""

    def test_render_with_parent_and_children(self):
        t = ClassInheritanceTemplate()
        result = t.render(parent="Animal", children=["Dog", "Cat"])
        assert "classDiagram" in result
        assert "Animal" in result
        assert "Dog" in result
        assert "Cat" in result
        assert "<|--" in result

    def test_render_validates_as_mermaid(self):
        t = ClassInheritanceTemplate()
        result = t.render(parent="Shape", children=["Circle", "Square"])
        assert MermaidValidator.validate(result) is True

    def test_render_missing_parent_raises(self):
        t = ClassInheritanceTemplate()
        with pytest.raises(ValueError, match="parent"):
            t.render(children=["A", "B"])

    def test_render_missing_children_raises(self):
        t = ClassInheritanceTemplate()
        with pytest.raises(ValueError, match="children"):
            t.render(parent="Base")

    def test_suggest_filename(self):
        t = ClassInheritanceTemplate()
        assert t.suggest_filename() == "class_inheritance"


# =========================================================================
# ERDatabaseTemplate tests
# =========================================================================


class TestERDatabaseTemplate:
    """Tests for ERDatabaseTemplate."""

    def test_render_with_entities(self):
        t = ERDatabaseTemplate()
        result = t.render(
            entities=[
                {"name": "User", "attributes": ["id", "name"]},
                {"name": "Post", "attributes": ["id", "title"]},
            ]
        )
        assert "erDiagram" in result
        assert "User" in result
        assert "Post" in result

    def test_render_validates_as_mermaid(self):
        t = ERDatabaseTemplate()
        result = t.render(
            entities=[
                {"name": "Customer", "attributes": ["id"]},
                {"name": "Order", "attributes": ["id", "total"]},
            ]
        )
        assert MermaidValidator.validate(result) is True

    def test_render_single_entity_works(self):
        """A single entity should work without relationships."""
        t = ERDatabaseTemplate()
        result = t.render(entities=[{"name": "Config", "attributes": ["key", "value"]}])
        assert "erDiagram" in result
        assert "Config" in result

    def test_render_missing_entities_raises(self):
        t = ERDatabaseTemplate()
        with pytest.raises(ValueError, match="entities"):
            t.render()

    def test_render_entity_missing_name_raises(self):
        t = ERDatabaseTemplate()
        with pytest.raises(ValueError, match="name"):
            t.render(entities=[{"attributes": ["a"]}])

    def test_suggest_filename(self):
        t = ERDatabaseTemplate()
        assert t.suggest_filename() == "er_database"
