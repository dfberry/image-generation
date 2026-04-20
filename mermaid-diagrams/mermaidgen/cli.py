"""Command-line interface for mermaid-diagram."""

import argparse
import sys

from .config import DEFAULT_FORMAT, SUPPORTED_FORMATS
from .errors import MermaidError
from .generator import MermaidGenerator
from .templates import default_registry


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mermaid-diagram",
        description="Generate Mermaid diagrams and render to PNG/SVG/PDF",
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--syntax",
        type=str,
        help="Raw Mermaid syntax string",
    )
    input_group.add_argument(
        "--file",
        type=str,
        help="Path to a .mmd file containing Mermaid syntax",
    )
    input_group.add_argument(
        "--template",
        type=str,
        help="Name of a built-in template to use",
    )
    input_group.add_argument(
        "--list-templates",
        action="store_true",
        help="Show available templates and exit",
    )

    # Template parameters
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Template parameter as KEY=VALUE (repeatable; comma-separated values become lists)",
    )

    # Output options
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (auto-generated if omitted)",
    )
    parser.add_argument(
        "--format",
        choices=list(SUPPORTED_FORMATS),
        default=DEFAULT_FORMAT,
        help=f"Output format (default: {DEFAULT_FORMAT})",
    )

    return parser


def _parse_params(raw_params: list[str]) -> dict:
    """Parse --param KEY=VALUE arguments into a dict.

    Values containing commas are split into lists.
    """
    params: dict = {}
    for item in raw_params:
        if "=" not in item:
            print(f"Error: --param must be KEY=VALUE, got: '{item}'", file=sys.stderr)
            sys.exit(1)
        key, _, value = item.partition("=")
        key = key.strip()
        value = value.strip()
        # Parse comma-separated values as lists
        if "," in value:
            params[key] = [v.strip() for v in value.split(",") if v.strip()]
        else:
            params[key] = value
    return params


def _list_templates() -> None:
    """Print available templates and exit."""
    templates = default_registry.list_available()
    if not templates:
        print("No templates available.")
        return

    print("Available templates:\n")
    for t in templates:
        print(f"  {t['name']}")
        print(f"    {t['description']}")
        print()


def main(argv: list[str] | None = None) -> None:
    """Entry point for the mermaid-diagram CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Handle --list-templates
    if args.list_templates:
        _list_templates()
        return

    # Must have an input source
    if not args.syntax and not args.file and not args.template:
        parser.print_help()
        sys.exit(1)

    try:
        gen = MermaidGenerator()

        if args.syntax:
            result = gen.from_syntax(args.syntax, args.output, args.format)

        elif args.file:
            import os
            if not os.path.isfile(args.file):
                print(f"Error: File not found: {args.file}", file=sys.stderr)
                sys.exit(1)
            with open(args.file, encoding="utf-8") as f:
                syntax = f.read()
            result = gen.from_syntax(syntax, args.output, args.format)

        elif args.template:
            params = _parse_params(args.param)
            result = gen.from_template(
                args.template,
                params=params,
                output_filename=args.output,
                fmt=args.format,
            )
        else:
            parser.print_help()
            sys.exit(1)

        print(f"Diagram saved to: {result}")

    except MermaidError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
