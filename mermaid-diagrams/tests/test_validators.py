"""Tests for MermaidValidator.

Tests validate against Trinity's actual implementation in validators.py:
- MermaidValidator.validate(syntax: str) -> bool
- Raises MermaidSyntaxError for empty/whitespace/missing-type input
- Returns True for valid input
- Skips %% comment lines when looking for diagram type
"""

import pytest

from mermaidgen.errors import MermaidSyntaxError
from mermaidgen.validators import MermaidValidator


class TestMermaidValidatorValid:
    """Happy-path tests: valid syntax should return True."""

    def test_valid_flowchart(self, valid_flowchart_syntax):
        assert MermaidValidator.validate(valid_flowchart_syntax) is True

    def test_valid_sequence(self, valid_sequence_syntax):
        assert MermaidValidator.validate(valid_sequence_syntax) is True

    def test_valid_class(self, valid_class_syntax):
        assert MermaidValidator.validate(valid_class_syntax) is True

    def test_valid_er(self, valid_er_syntax):
        assert MermaidValidator.validate(valid_er_syntax) is True

    def test_valid_graph_lr(self):
        """graph is an alias for flowchart."""
        assert MermaidValidator.validate("graph LR\n    A --> B") is True

    def test_valid_gantt(self):
        syntax = "gantt\n    title Project\n    section A\n    Task1 :a1, 2024-01-01, 30d"
        assert MermaidValidator.validate(syntax) is True

    def test_valid_state_diagram(self):
        assert MermaidValidator.validate("stateDiagram-v2\n    [*] --> Active") is True

    def test_valid_pie_chart(self):
        assert MermaidValidator.validate('pie\n    "Cats" : 50\n    "Dogs" : 50') is True

    def test_comment_lines_skipped(self):
        """Leading %% comment lines should be ignored; diagram type on later line."""
        syntax = "%% this is a comment\n%% another comment\nflowchart TD\n    A --> B"
        assert MermaidValidator.validate(syntax) is True

    def test_leading_blank_lines_skipped(self):
        syntax = "\n\n\nflowchart TD\n    A --> B"
        assert MermaidValidator.validate(syntax) is True


class TestMermaidValidatorInvalid:
    """Error-path tests: invalid syntax should raise MermaidSyntaxError."""

    def test_empty_syntax_raises(self, empty_syntax):
        with pytest.raises(MermaidSyntaxError, match="empty"):
            MermaidValidator.validate(empty_syntax)

    def test_missing_type_raises(self, invalid_syntax):
        with pytest.raises(MermaidSyntaxError, match="Missing diagram type"):
            MermaidValidator.validate(invalid_syntax)

    def test_whitespace_only_raises(self):
        with pytest.raises(MermaidSyntaxError, match="empty"):
            MermaidValidator.validate("   \n  \n  ")

    def test_none_like_empty(self):
        """Empty string (falsy) raises."""
        with pytest.raises(MermaidSyntaxError, match="empty"):
            MermaidValidator.validate("")

    def test_only_comments_raises(self):
        """File with only %% comment lines and no diagram type."""
        with pytest.raises(MermaidSyntaxError, match="empty"):
            MermaidValidator.validate("%% just a comment\n%% another comment")

    def test_random_text_raises(self):
        """Plain English text is not a valid diagram."""
        with pytest.raises(MermaidSyntaxError, match="Missing diagram type"):
            MermaidValidator.validate("Hello world, this is random text")
