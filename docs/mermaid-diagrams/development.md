← [Back to Documentation Index](../README.md)

# Development Guide — mermaid-diagrams

How to develop, extend, and maintain the `mermaidgen` package.

## Repo Structure

```
mermaid-diagrams/
├── mermaidgen/                # Python package
│   ├── __init__.py            # Public API exports
│   ├── cli.py                 # argparse CLI (mermaid-diagram command)
│   ├── config.py              # Default constants (format, timeout, paths)
│   ├── errors.py              # Exception hierarchy (MermaidError base)
│   ├── generator.py           # MermaidGenerator class (core pipeline)
│   ├── templates.py           # MermaidTemplate ABC + 4 concrete + registry
│   └── validators.py          # MermaidValidator (static syntax checks)
├── tests/
│   ├── conftest.py            # Shared fixtures (mock_mmdc, syntax samples)
│   ├── fixtures/              # (reserved for test data files)
│   ├── test_cli.py            # CLI argument parsing and mode tests
│   ├── test_generator.py      # MermaidGenerator integration tests
│   ├── test_templates.py      # Template rendering and registry tests
│   └── test_validators.py     # Validator happy/error path tests
├── outputs/                   # Default output directory (gitignored)
├── pyproject.toml             # Package metadata, tool config (ruff, pytest)
├── requirements.txt           # Runtime deps (none — mmdc is external)
├── requirements-dev.txt       # Dev deps: pytest, pytest-cov, ruff
├── Makefile                   # install, test, lint, clean targets
└── README.md
```

## Package Configuration

Defined in `pyproject.toml`:

- **Name:** `mermaid-diagrams`
- **Version:** `0.1.0`
- **Python:** `>=3.10`
- **Build:** setuptools + wheel
- **Console script:** `mermaid-diagram` → `mermaidgen.cli:main`
- **Ruff:** line-length 100, target Python 3.10
- **Pytest:** test paths = `["tests"]`

## Coding Conventions

- **Type hints:** Use `str | None` union syntax (Python 3.10+), not `Optional[str]`.
- **Imports:** Standard library first, then package-relative imports.
- **Docstrings:** Google style — Args, Returns, Raises sections.
- **Linter:** Ruff with 100-char line length. Run `make lint` before committing.
- **Naming:** Template names use underscores, not hyphens: `flowchart_simple`, `sequence_api`, `class_inheritance`, `er_database`.
- **Error handling:** All custom exceptions inherit from `MermaidError`. Use specific subclasses (`MermaidSyntaxError`, `RenderError`, `MmcdNotFoundError`).

## How to Add a New Template

1. **Create a class** in `templates.py` extending `MermaidTemplate`:

```python
class MyNewTemplate(MermaidTemplate):
    name = "my_new_template"  # use underscores
    description = "Description of what this template generates."

    def render(self, **kwargs: object) -> str:
        # Extract and validate params from kwargs
        param = kwargs.get("param", "")
        if not param:
            raise ValueError("'param' is required")

        lines = ["flowchart TD"]
        # ... build Mermaid syntax ...
        return "\n".join(lines)

    def suggest_filename(self) -> str:
        return "my_new_template"
```

2. **Register it** in the module-level `default_registry` at the bottom of `templates.py`:

```python
default_registry.register(MyNewTemplate())
```

3. **Add tests** in `tests/test_templates.py`:
   - Test `render()` with valid params produces valid Mermaid syntax
   - Test `MermaidValidator.validate(result)` returns `True`
   - Test missing/invalid params raise `ValueError`
   - Test `suggest_filename()` returns expected string

4. **Update documentation** — add the template to the built-in templates table in `README.md` and `docs/mermaid-diagrams/user-guide.md`.

## How to Add New Output Formats

Output formats are controlled by the `-e` flag passed to `mmdc`. To add a new format:

1. Add the format string to `SUPPORTED_FORMATS` in `config.py`:

```python
SUPPORTED_FORMATS = ("png", "svg", "pdf", "newformat")
```

2. That's it — `cli.py` reads `SUPPORTED_FORMATS` for `--format` choices, and `generator.py` passes the format string directly to `mmdc -e`.

3. If the new format needs special handling in tests, update the `mock_mmdc` fixture in `conftest.py` to write appropriate fake output for the format.

## How the Validator Works

`MermaidValidator.validate(syntax)` performs structural pre-validation before passing syntax to `mmdc`:

1. Rejects empty or whitespace-only input → `MermaidSyntaxError("empty")`
2. Iterates lines, skipping blank lines and `%%` comment lines
3. Checks the first meaningful line starts with a known diagram type keyword (from `VALID_DIAGRAM_TYPES` tuple)
4. If no match → `MermaidSyntaxError("Missing diagram type declaration...")`
5. Returns `True` on success

### Extending Validation Rules

To add new diagram type support, add the keyword to `VALID_DIAGRAM_TYPES` in `validators.py`:

```python
VALID_DIAGRAM_TYPES: tuple[str, ...] = (
    "flowchart",
    "graph",
    # ... existing types ...
    "newDiagramType",  # add here
)
```

For deeper validation (e.g., checking node syntax), extend `MermaidValidator` with additional static methods and call them from `validate()` or as separate opt-in checks.

## Makefile Targets

| Target | Command | Purpose |
|--------|---------|---------|
| `make install` | `pip install -e .` + `pip install -r requirements-dev.txt` | Install package in editable mode + dev deps |
| `make test` | `python -m pytest tests/ -v --tb=short` | Run test suite |
| `make lint` | `ruff check .` | Run linter |
| `make clean` | Remove `__pycache__` dirs + output files | Clean artifacts |

## Branch Naming

For issue-linked work, use the Squad convention:

```
squad/{issue-number}-{kebab-case-slug}
```

Example: `squad/42-add-gantt-template`

## Dependency Management

- **Runtime:** Zero Python dependencies. The only external requirement is the `mmdc` binary (Node.js).
- **Dev:** Listed in `requirements-dev.txt` — `pytest>=7.4`, `pytest-cov>=4.1`, `ruff>=0.1.0`.
- **Build:** `setuptools>=68.0` and `wheel` (declared in `pyproject.toml` build-system).
- Add new runtime deps to `pyproject.toml` `[project.dependencies]` and `requirements.txt`.
- Add new dev deps to `requirements-dev.txt`.
