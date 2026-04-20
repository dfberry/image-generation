"""Tests for MermaidGenerator (with mocked mmdc).

Tests matched against Trinity's actual implementation in generator.py:
- MermaidGenerator(output_dir=str|None, mmdc_binary=str|None)
- from_syntax(syntax, output_filename=None, fmt=None) -> str
- from_template(template_name, params: dict, output_filename=None, fmt=None) -> str
- _run_mmdc(input_path, output_path, fmt) -> None
  Raises MmcdNotFoundError on FileNotFoundError
  Raises RenderError on TimeoutExpired or non-zero exit
"""

import os
import subprocess
from unittest.mock import patch

import pytest

from mermaidgen.errors import MermaidSyntaxError, MmcdNotFoundError, RenderError
from mermaidgen.generator import MermaidGenerator


# =========================================================================
# from_syntax tests
# =========================================================================


class TestFromSyntax:
    """Tests for MermaidGenerator.from_syntax()."""

    def test_from_syntax_creates_file(self, generator, valid_flowchart_syntax, tmp_output_dir):
        out = str(tmp_output_dir / "test.png")
        result = generator.from_syntax(valid_flowchart_syntax, output_filename=out)
        assert result == out
        assert os.path.exists(result)

    def test_from_syntax_auto_generates_name(self, generator, valid_flowchart_syntax):
        """When output_filename is None, an auto-generated path is used."""
        result = generator.from_syntax(valid_flowchart_syntax)
        assert result.endswith(".png")
        assert os.path.exists(result)

    def test_from_syntax_invalid_raises(self, generator, invalid_syntax):
        with pytest.raises(MermaidSyntaxError):
            generator.from_syntax(invalid_syntax)

    def test_from_syntax_empty_raises(self, generator, empty_syntax):
        with pytest.raises(MermaidSyntaxError):
            generator.from_syntax(empty_syntax)

    def test_from_syntax_returns_string(self, generator, valid_flowchart_syntax):
        """from_syntax returns str, not Path."""
        result = generator.from_syntax(valid_flowchart_syntax)
        assert isinstance(result, str)


# =========================================================================
# from_template tests
# =========================================================================


class TestFromTemplate:
    """Tests for MermaidGenerator.from_template()."""

    def test_from_template_creates_file(self, generator):
        result = generator.from_template(
            "flowchart_simple",
            params={"steps": ["A", "B", "C"]},
        )
        assert os.path.exists(result)

    def test_from_template_unknown_raises(self, generator):
        with pytest.raises(ValueError, match="not found"):
            generator.from_template("totally_fake_template", params={})

    def test_from_template_custom_output(self, generator, tmp_output_dir):
        out = str(tmp_output_dir / "custom.png")
        result = generator.from_template(
            "flowchart_simple",
            params={"steps": ["X", "Y"]},
            output_filename=out,
        )
        assert result == out
        assert os.path.exists(result)

    def test_from_template_svg_format(self, generator):
        result = generator.from_template(
            "sequence_api",
            params={
                "participants": ["Client", "Server"],
                "messages": [("Client", "Server", "GET /data")],
            },
            fmt="svg",
        )
        assert result.endswith(".svg")
        assert os.path.exists(result)


# =========================================================================
# Output format tests
# =========================================================================


class TestOutputFormats:
    """Test that png and svg formats both produce output."""

    def test_png_format(self, generator, valid_flowchart_syntax, tmp_output_dir):
        out = str(tmp_output_dir / "diagram.png")
        result = generator.from_syntax(valid_flowchart_syntax, output_filename=out, fmt="png")
        assert os.path.exists(result)

    def test_svg_format(self, generator, valid_flowchart_syntax, tmp_output_dir):
        out = str(tmp_output_dir / "diagram.svg")
        result = generator.from_syntax(valid_flowchart_syntax, output_filename=out, fmt="svg")
        assert os.path.exists(result)


# =========================================================================
# Temp file cleanup
# =========================================================================


class TestTempFileCleanup:
    """Verify temp .mmd files are cleaned up even on error."""

    def test_temp_file_cleanup_on_success(self, generator, valid_flowchart_syntax, tmp_output_dir):
        out = str(tmp_output_dir / "test.png")
        generator.from_syntax(valid_flowchart_syntax, output_filename=out)
        # If we get here without error, the finally block cleaned up the temp file.
        assert os.path.exists(out)

    def test_temp_file_cleanup_on_render_error(self, tmp_output_dir, valid_flowchart_syntax):
        """Even when _run_mmdc fails, temp .mmd should be cleaned up."""
        with patch(
            "mermaidgen.generator.subprocess.run",
            return_value=subprocess.CompletedProcess(["mmdc"], 1, stdout="", stderr="fail"),
        ):
            gen = MermaidGenerator(output_dir=str(tmp_output_dir), mmdc_binary="mmdc")
            with pytest.raises(RenderError):
                gen.from_syntax(valid_flowchart_syntax, output_filename=str(tmp_output_dir / "x.png"))

        # If we got here, the RenderError was raised and temp file was cleaned up.


# =========================================================================
# mmdc error handling
# =========================================================================


class TestMmcdErrors:
    """Tests for mmdc subprocess error handling."""

    def test_mmdc_not_found_raises(self, tmp_path, valid_flowchart_syntax):
        """FileNotFoundError from subprocess.run -> MmcdNotFoundError."""
        with patch(
            "mermaidgen.generator.subprocess.run",
            side_effect=FileNotFoundError("mmdc not found"),
        ):
            gen = MermaidGenerator(output_dir=str(tmp_path), mmdc_binary="mmdc_does_not_exist")
            with pytest.raises(MmcdNotFoundError):
                gen.from_syntax(valid_flowchart_syntax, output_filename=str(tmp_path / "out.png"))

    def test_mmdc_timeout_raises(self, tmp_path, valid_flowchart_syntax):
        """subprocess.TimeoutExpired -> RenderError."""
        with patch(
            "mermaidgen.generator.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["mmdc"], 30),
        ):
            gen = MermaidGenerator(output_dir=str(tmp_path), mmdc_binary="mmdc")
            with pytest.raises(RenderError, match="timed out"):
                gen.from_syntax(valid_flowchart_syntax, output_filename=str(tmp_path / "out.png"))

    def test_mmdc_failure_nonzero_exit(self, tmp_path, valid_flowchart_syntax):
        """Non-zero exit code from mmdc -> RenderError."""
        with patch(
            "mermaidgen.generator.subprocess.run",
            return_value=subprocess.CompletedProcess(
                ["mmdc"], 1, stdout="", stderr="Parse error at line 2"
            ),
        ):
            gen = MermaidGenerator(output_dir=str(tmp_path), mmdc_binary="mmdc")
            with pytest.raises(RenderError, match="mmdc failed"):
                gen.from_syntax(valid_flowchart_syntax, output_filename=str(tmp_path / "out.png"))
