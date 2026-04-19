# mermaid-diagrams

Generate Mermaid diagrams from text prompts and render to PNG/SVG/PDF.

## Prerequisites

- Python 3.10+
- [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) (`mmdc` binary)

```bash
npm install -g @mermaid-js/mermaid-cli
```

## Install

```bash
cd mermaid-diagrams
pip install -e .
pip install -r requirements-dev.txt
```

Or use the Makefile:

```bash
make install
```

## Usage

### CLI

```bash
# From raw syntax
mermaid-gen --syntax "flowchart TD\n    A[Start] --> B[End]"

# From a .mmd file
mermaid-gen --file diagram.mmd --format svg

# Using a template
mermaid-gen --template flowchart-simple --param steps="Start,Process,End"

# List available templates
mermaid-gen --list-templates
```

### Python API

```python
from mermaidgen import MermaidGenerator, TemplateRegistry, MermaidValidator

# Validate syntax
MermaidValidator.validate("flowchart TD\n    A --> B")

# Generate from syntax
gen = MermaidGenerator(output_dir="outputs")
path = gen.from_syntax("flowchart TD\n    A[Start] --> B[End]", fmt="png")

# Generate from template
path = gen.from_template("flowchart-simple", steps="Start,Process,End")

# List templates
registry = TemplateRegistry()
for t in registry.list_available():
    print(f"{t['name']}: {t['description']}")
```

## Built-in Templates

| Name | Description |
|------|-------------|
| `flowchart-simple` | Linear flowchart from a list of steps |
| `sequence-api` | Sequence diagram for API calls (client → server → database) |
| `class-inheritance` | Class diagram with inheritance relationships |
| `er-database` | Entity-relationship diagram from entity names |

## Development

```bash
make test    # Run tests
make lint    # Run ruff linter
make clean   # Remove generated files
```

## Project Structure

```
mermaid-diagrams/
├── mermaidgen/
│   ├── __init__.py       # Public API exports
│   ├── cli.py            # argparse CLI entry point
│   ├── config.py         # Default configuration values
│   ├── errors.py         # Custom exception classes
│   ├── generator.py      # Core MermaidGenerator class
│   ├── templates.py      # Template base + 4 concrete templates + registry
│   └── validators.py     # Mermaid syntax validation
├── outputs/              # Default output directory
├── tests/                # Test suite
├── pyproject.toml        # Package metadata and tool config
├── requirements.txt      # Runtime dependencies (none)
├── requirements-dev.txt  # Dev dependencies
├── Makefile              # Common dev commands
└── README.md             # This file
```
