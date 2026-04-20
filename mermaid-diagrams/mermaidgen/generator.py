"""Core Mermaid diagram generator."""

import os
import subprocess
import tempfile

from .config import DEFAULT_FORMAT, DEFAULT_MMDC_BINARY, DEFAULT_OUTPUT_DIR, SUBPROCESS_TIMEOUT
from .errors import MmcdNotFoundError, RenderError
from .templates import default_registry
from .validators import MermaidValidator


class MermaidGenerator:
    """Generate Mermaid diagrams by calling the mmdc CLI."""

    def __init__(
        self,
        output_dir: str | None = None,
        mmdc_binary: str | None = None,
    ) -> None:
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.mmdc_binary = mmdc_binary or DEFAULT_MMDC_BINARY
        os.makedirs(self.output_dir, exist_ok=True)

    def from_syntax(
        self,
        syntax: str,
        output_filename: str | None = None,
        fmt: str | None = None,
    ) -> str:
        """Render a Mermaid diagram from raw syntax.

        Args:
            syntax: Valid Mermaid diagram syntax.
            output_filename: Output file name or path. Auto-generated if None.
            fmt: Output format — png, svg, or pdf.

        Returns:
            Path to the rendered output file as a string.

        Raises:
            MermaidSyntaxError: If syntax validation fails.
            RenderError: If mmdc rendering fails.
        """
        if fmt is None:
            fmt = DEFAULT_FORMAT

        MermaidValidator.validate(syntax)

        if output_filename is None:
            output_path = os.path.join(self.output_dir, f"diagram.{fmt}")
        else:
            output_path = output_filename

        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        tmp_path: str | None = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".mmd", text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(syntax)

            self._run_mmdc(tmp_path, output_path, fmt)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        return output_path

    def from_template(
        self,
        template_name: str,
        params: dict,
        output_filename: str | None = None,
        fmt: str | None = None,
    ) -> str:
        """Render a diagram using a named template.

        Args:
            template_name: Name of the registered template.
            params: Parameters passed to the template's render method.
            output_filename: Output file path. Auto-generated if None.
            fmt: Output format — png, svg, or pdf.

        Returns:
            Path to the rendered output file as a string.

        Raises:
            ValueError: If template_name is not found in the registry.
        """
        template = default_registry.get(template_name)
        if template is None:
            raise ValueError(f"Template '{template_name}' not found")

        syntax = template.render(**params)

        if output_filename is None:
            if fmt is None:
                ext = DEFAULT_FORMAT
            else:
                ext = fmt
            output_filename = os.path.join(
                self.output_dir, f"{template.suggest_filename()}.{ext}"
            )

        return self.from_syntax(syntax, output_filename, fmt)

    def _run_mmdc(self, input_path: str, output_path: str, fmt: str) -> None:
        """Execute mmdc subprocess to render a diagram.

        Args:
            input_path: Path to the .mmd input file.
            output_path: Path for the rendered output.
            fmt: Output format.

        Raises:
            MmcdNotFoundError: If the mmdc binary cannot be found.
            RenderError: If mmdc times out or exits with non-zero status.
        """
        cmd = [
            self.mmdc_binary,
            "-i", input_path,
            "-o", output_path,
            "-e", fmt,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=SUBPROCESS_TIMEOUT,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise MmcdNotFoundError(
                f"'{self.mmdc_binary}' not found. "
                "Install mermaid-cli: npm install -g @mermaid-js/mermaid-cli"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RenderError(
                f"mmdc timed out after {SUBPROCESS_TIMEOUT}s"
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "unknown error"
            raise RenderError(f"mmdc failed (exit {result.returncode}): {stderr}")
