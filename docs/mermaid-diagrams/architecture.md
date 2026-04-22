← [Back to Documentation Index](../README.md)

# Architecture — mermaid-diagrams

System architecture for the `mermaidgen` Python package.

## Overview

`mermaidgen` converts Mermaid diagram syntax into rendered image files (PNG, SVG, PDF). It accepts input as raw syntax strings, `.mmd` files, or named templates, validates the syntax, and delegates rendering to the `mmdc` subprocess (mermaid-cli).

## Pipeline Flow

```
Input Source                     Core Engine                     Output
─────────────                    ───────────                     ──────
Raw syntax (--syntax)  ──┐
                         ├──▶  MermaidValidator.validate()
.mmd file (--file)     ──┤         │
                         │         ▼
Template (--template)  ──┤   MermaidGenerator.from_syntax()
  └─▶ registry.get()    │         │
  └─▶ template.render() ┘         ▼
                            Write temp .mmd file
                                   │
                                   ▼
                            _run_mmdc() ──▶ subprocess.run(["mmdc", ...])
                                   │
                                   ▼                          ┌─ PNG
                            Read output file ────────────────▶├─ SVG
                                   │                          └─ PDF
                                   ▼
                            Clean up temp .mmd
                                   │
                                   ▼
                            Return output file path
```

## Module Breakdown

### `generator.py` — `MermaidGenerator`

The core class. Orchestrates the full pipeline:

- **`__init__(output_dir, mmdc_binary)`** — Sets output directory (default: `./outputs`) and mmdc binary path. Creates the output directory if it doesn't exist.
- **`from_syntax(syntax, output_filename, fmt)`** — Validates syntax via `MermaidValidator`, writes a temp `.mmd` file, calls `_run_mmdc()`, cleans up the temp file (even on error), returns the output path.
- **`from_template(template_name, params, output_filename, fmt)`** — Looks up a template from `default_registry`, calls `template.render(**params)` to produce syntax, then delegates to `from_syntax()`.
- **`_run_mmdc(input_path, output_path, fmt)`** — Builds the command `[mmdc, -i, input, -o, output, -e, fmt]` and runs it via `subprocess.run()`. Handles three error cases:
  - `FileNotFoundError` from `subprocess.run` → raises `MmcdNotFoundError`
  - `subprocess.TimeoutExpired` → raises `RenderError`
  - Non-zero exit code → raises `RenderError` with stderr content

> **Note:** `MmcdNotFoundError` is raised only when `_run_mmdc` catches `FileNotFoundError` from `subprocess.run` — it is NOT checked at `__init__` time.

### `templates.py` — Template System

Implements the base class, concrete templates, and the registry pattern.

- **`MermaidTemplate` (ABC)** — Abstract base class with:
  - `name: str` — template identifier
  - `description: str` — human-readable description
  - `render(**kwargs) -> str` — abstract method, returns Mermaid syntax
  - `suggest_filename() -> str` — returns `self.name` by default

- **`TemplateRegistry`** — Stores templates in a `dict[str, MermaidTemplate]`:
  - `register(template)` — adds a template by its `.name`
  - `get(name)` — returns template or `None`
  - `list_available()` — returns sorted list of `{name, description}` dicts

- **4 Concrete Templates:**

  | Class | `name` | Required params |
  |-------|--------|-----------------|
  | `FlowchartSimpleTemplate` | `flowchart_simple` | `steps: list[str]` (≥2 items) |
  | `SequenceAPITemplate` | `sequence_api` | `participants: list[str]`, `messages: list[tuple[str,str,str]]` |
  | `ClassInheritanceTemplate` | `class_inheritance` | `parent: str`, `children: list[str]` |
  | `ERDatabaseTemplate` | `er_database` | `entities: list[dict]` with `name` and `attributes` keys |

- **`default_registry`** — module-level `TemplateRegistry` instance with all 4 templates pre-registered.

### `validators.py` — `MermaidValidator`

Static validation layer (no instantiation needed):

- **`MermaidValidator.validate(syntax)`** — Returns `True` or raises `MermaidSyntaxError`.
  - Rejects empty / whitespace-only input
  - Skips blank lines and `%%` comment lines
  - Checks that the first meaningful line starts with a recognized diagram type keyword
  - Recognized types: `flowchart`, `graph`, `sequenceDiagram`, `classDiagram`, `erDiagram`, `stateDiagram`, `gantt`, `pie`, `gitgraph`, `journey`, `mindmap`, `timeline`, `quadrantChart`, `sankey`, `xychart`, `block`, `packet`, `architecture`, `kanban`

### `cli.py` — CLI Entry Point

- **`main(argv)`** — Entry point registered as `mermaid-diagram` console script.
- **`_build_parser()`** — Builds `argparse.ArgumentParser` with mutually exclusive input group (`--syntax`, `--file`, `--template`, `--list-templates`).
- **`_parse_params(raw_params)`** — Parses `KEY=VALUE` strings; comma-separated values become lists.
- No args → prints help, exits with code 1.
- Catches `MermaidError`, `ValueError`, `KeyError` → prints to stderr, exits 1.

### `config.py` — Defaults

| Constant | Value | Purpose |
|----------|-------|---------|
| `DEFAULT_OUTPUT_DIR` | `os.path.join(os.getcwd(), "outputs")` | Where output files go |
| `DEFAULT_MMDC_BINARY` | `"mmdc"` | Binary name on PATH |
| `DEFAULT_FORMAT` | `"png"` | Default output format |
| `SUBPROCESS_TIMEOUT` | `30` | Seconds before timeout |
| `SUPPORTED_FORMATS` | `("png", "svg", "pdf")` | Valid format choices |

### `errors.py` — Exception Hierarchy

```
MermaidError (base)
├── MermaidSyntaxError   — invalid Mermaid syntax
├── RenderError          — mmdc rendering failure (timeout, non-zero exit)
└── MmcdNotFoundError    — mmdc binary not found (FileNotFoundError from subprocess.run)
```

### `__init__.py` — Public API

Exports: `MermaidError`, `MermaidSyntaxError`, `RenderError`, `MmcdNotFoundError`, `MermaidValidator`, `MermaidGenerator`, `TemplateRegistry`, `default_registry`.

## Subprocess Isolation

The `mmdc` binary (from `@mermaid-js/mermaid-cli`) runs as an external subprocess. `mermaidgen` never imports or embeds mermaid-cli JavaScript — it communicates only via:

1. Writing a temp `.mmd` file
2. Calling `subprocess.run(["mmdc", "-i", input, "-o", output, "-e", fmt])`
3. Reading the output file produced by mmdc
4. Cleaning up the temp file in a `finally` block

This keeps the Python package dependency-free at runtime (no npm/Node.js packages in the Python environment) and makes the mmdc version independently upgradeable.

## Data Flow Summary

```
User Input
    │
    ▼
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   cli.py     │────▶│  generator.py    │────▶│  mmdc (Node)  │
│  (argparse)  │     │ MermaidGenerator │     │  subprocess   │
└──────────────┘     └──────────────────┘     └──────────────┘
                            │    ▲                    │
                            │    │                    │
                            ▼    │                    ▼
                     ┌──────────────┐          ┌──────────┐
                     │ validators.py│          │ PNG/SVG/ │
                     │ templates.py │          │ PDF file │
                     │ errors.py    │          └──────────┘
                     │ config.py    │
                     └──────────────┘
```
