← [Back to Documentation Index](../README.md)

# Installation Guide — mermaid-diagrams

How to install the `mermaidgen` package and its external dependency (`mmdc`).

## System Requirements

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.10+ | Package runtime (uses `str \| None` union syntax) |
| Node.js | LTS recommended | Required to run `mmdc` (mermaid-cli) |
| npm | Comes with Node.js | Install mermaid-cli globally |

## Step 1: Install mermaid-cli (mmdc)

The `mmdc` binary renders Mermaid syntax into PNG/SVG/PDF. It's a Node.js tool installed via npm:

```bash
npm install -g @mermaid-js/mermaid-cli
```

Verify the installation:

```bash
mmdc --version
```

You should see a version number like `10.x.x`. If `mmdc` is not on your PATH, the package will raise `MmcdNotFoundError` when you try to render a diagram.

## Step 2: Install the Python package

From the `mermaid-diagrams/` directory:

```bash
cd mermaid-diagrams
pip install -e .
```

This installs the package in **editable mode** — changes to the source code take effect immediately without reinstalling.

### For development (includes test and lint tools)

```bash
pip install -e .
pip install -r requirements-dev.txt
```

Dev dependencies: `pytest>=7.4`, `pytest-cov>=4.1`, `ruff>=0.1.0`.

### Using the Makefile shortcut

```bash
make install
```

This runs both `pip install -e .` and `pip install -r requirements-dev.txt`, then prints a reminder about installing mermaid-cli.

## Step 3: Verify Installation

### CLI tool

```bash
mermaid-diagram --help
```

Expected output:

```
usage: mermaid-diagram [-h] [--syntax SYNTAX | --file FILE | --template TEMPLATE | --list-templates]
                       [--param KEY=VALUE] [--output OUTPUT] [--format {png,svg,pdf}]

Generate Mermaid diagrams and render to PNG/SVG/PDF
...
```

### List available templates

```bash
mermaid-diagram --list-templates
```

Should show 4 built-in templates: `class_inheritance`, `er_database`, `flowchart_simple`, `sequence_api`.

### Python API

```python
python -c "from mermaidgen import MermaidGenerator; print('OK')"
```

### mmdc binary

```bash
mmdc --version
```

## Troubleshooting

### `MmcdNotFoundError` when rendering

**Cause:** The `mmdc` binary is not on your system PATH.

**Fix:** Install mermaid-cli globally:

```bash
npm install -g @mermaid-js/mermaid-cli
```

Or specify a custom path when creating the generator:

```python
gen = MermaidGenerator(mmdc_binary="/path/to/mmdc")
```

### `ModuleNotFoundError: No module named 'mermaidgen'`

**Cause:** The package is not installed.

**Fix:** Run `pip install -e .` from the `mermaid-diagrams/` directory.

### Tests fail with import errors

**Cause:** Package not installed before running tests.

**Fix:** Install in editable mode first:

```bash
pip install -e .
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```
