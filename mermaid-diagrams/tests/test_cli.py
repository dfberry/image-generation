"""Tests for the mermaid-diagram CLI.

Tests matched against Trinity's actual implementation in cli.py:
- main(argv: list[str] | None = None) -> None
- _build_parser() -> argparse.ArgumentParser
- _parse_params(raw_params: list[str]) -> dict
- --syntax, --file, --template, --list-templates are mutually exclusive
- --param KEY=VALUE (comma-separated values become lists)
- --output, --format
- No args -> print help and sys.exit(1)
"""

import os
from unittest.mock import patch

import pytest

from mermaidgen.cli import main, _build_parser, _parse_params


# =========================================================================
# _parse_params tests
# =========================================================================


class TestParseParams:
    """Tests for --param KEY=VALUE parsing."""

    def test_simple_param_no_comma(self):
        """Single value without commas stays as a string."""
        result = _parse_params(["title=My Flow"])
        assert result == {"title": "My Flow"}

    def test_comma_separated_becomes_list(self):
        """Values with commas are split into a list."""
        result = _parse_params(["steps=A,B,C"])
        assert result == {"steps": ["A", "B", "C"]}

    def test_multiple_params(self):
        result = _parse_params(["key1=val1", "key2=val2"])
        assert result["key1"] == "val1"
        assert result["key2"] == "val2"

    def test_value_with_equals_sign(self):
        """Partition on first = only; the rest is the value."""
        result = _parse_params(["query=x=1&y=2"])
        assert result == {"query": "x=1&y=2"}


# =========================================================================
# _build_parser tests
# =========================================================================


class TestBuildParser:
    """Tests for argument parser construction."""

    def test_parser_accepts_list_templates(self):
        parser = _build_parser()
        args = parser.parse_args(["--list-templates"])
        assert args.list_templates is True

    def test_syntax_and_file_are_exclusive(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--syntax", "flowchart TD", "--file", "test.mmd"])

    def test_format_default_is_png(self):
        parser = _build_parser()
        args = parser.parse_args(["--syntax", "flowchart TD"])
        assert args.format == "png"


# =========================================================================
# --list-templates
# =========================================================================


class TestListTemplates:
    """Tests for --list-templates output."""

    def test_list_templates_prints_names(self, capsys):
        main(["--list-templates"])
        captured = capsys.readouterr()
        assert "flowchart_simple" in captured.out
        assert "sequence_api" in captured.out
        assert "class_inheritance" in captured.out
        assert "er_database" in captured.out


# =========================================================================
# CLI modes
# =========================================================================


class TestCLIModes:
    """Tests for CLI input modes (syntax, file, template)."""

    def test_no_args_shows_help(self):
        """No args prints help and exits with code 1."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 1

    def test_syntax_mode(self, mock_mmdc, tmp_path):
        out = str(tmp_path / "out.png")
        main(["--syntax", "flowchart TD\n    A --> B\n    B --> C", "--output", out])
        assert os.path.exists(out)

    def test_file_mode(self, mock_mmdc, tmp_path):
        mmd = tmp_path / "input.mmd"
        mmd.write_text("flowchart TD\n    A --> B\n    B --> C", encoding="utf-8")
        out = str(tmp_path / "out.svg")
        main(["--file", str(mmd), "--output", out, "--format", "svg"])
        assert os.path.exists(out)

    def test_template_mode(self, mock_mmdc, tmp_path):
        out = str(tmp_path / "out.png")
        main([
            "--template", "flowchart_simple",
            "--param", "steps=A,B,C",
            "--output", out,
        ])
        assert os.path.exists(out)

    def test_file_not_found_exits(self, mock_mmdc, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            main(["--file", str(tmp_path / "nope.mmd"), "--output", str(tmp_path / "x.png")])
        assert exc_info.value.code == 1

    def test_missing_output_uses_auto_name(self, mock_mmdc, tmp_path):
        """--syntax without --output auto-generates a filename."""
        # Temporarily change the default output dir to tmp_path
        with patch("mermaidgen.generator.DEFAULT_OUTPUT_DIR", str(tmp_path)):
            main(["--syntax", "flowchart TD\n    A --> B\n    B --> C"])
        # Should have created a file in the output dir
        files = list(tmp_path.glob("*.png"))
        assert len(files) >= 1

    def test_invalid_format_exits(self):
        """--format xyz should be rejected by argparse."""
        with pytest.raises(SystemExit):
            main(["--syntax", "flowchart TD\n    A-->B", "--format", "xyz"])

    def test_invalid_template_exits(self, mock_mmdc, tmp_path):
        """Unknown template name causes exit(1)."""
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--template", "nonexistent",
                "--output", str(tmp_path / "out.png"),
            ])
        assert exc_info.value.code == 1
