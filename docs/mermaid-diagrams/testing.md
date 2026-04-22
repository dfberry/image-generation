← [Back to Documentation Index](../README.md)

# Testing Guide — mermaid-diagrams

How the test suite works, how tests avoid needing the real `mmdc` binary, and how to add new tests.

## Running Tests

From the `mermaid-diagrams/` directory:

```bash
# Install the package first (required for imports to work)
pip install -e .
pip install -r requirements-dev.txt

# Run the full test suite
python -m pytest tests/ -v

# Or use the Makefile
make test
```

The package must be installed in editable mode (`pip install -e .`) before running tests. Without this, Python won't resolve `mermaidgen` imports.

## Test Architecture

Tests are organized by module, with shared fixtures in `conftest.py`:

```
tests/
├── conftest.py            # Shared fixtures: syntax samples, mock_mmdc, generator
├── fixtures/              # Reserved for test data files
├── test_validators.py     # MermaidValidator.validate() — happy + error paths
├── test_templates.py      # Template rendering, registry, suggest_filename()
├── test_generator.py      # MermaidGenerator — from_syntax, from_template, errors
└── test_cli.py            # CLI argument parsing, modes, error handling
```

### Test file → Module mapping

| Test file | Module under test | What it covers |
|-----------|-------------------|----------------|
| `test_validators.py` | `validators.py` | Valid syntax returns True; empty/invalid raises MermaidSyntaxError; comment/blank line skipping |
| `test_templates.py` | `templates.py` | All 4 template render methods; registry get/list/register; param validation; suggest_filename |
| `test_generator.py` | `generator.py` | from_syntax file creation; from_template delegation; output formats; temp file cleanup; mmdc error handling |
| `test_cli.py` | `cli.py` | _parse_params; parser construction; --list-templates; all CLI modes; error exits |

## Mock Patterns — How Tests Avoid Real mmdc

The real `mmdc` binary (a Node.js tool) is **not required** for testing. All subprocess calls are intercepted by the `mock_mmdc` fixture in `conftest.py`.

### The `mock_mmdc` fixture

```python
@pytest.fixture
def mock_mmdc():
    """Mock that simulates mmdc subprocess."""
    original_run = subprocess.run

    def _fake_run(cmd, **kwargs):
        if isinstance(cmd, list) and len(cmd) >= 5:
            binary = os.path.basename(cmd[0])
            if binary == "mmdc" or cmd[0] == "mmdc":
                # Parse -o flag for output path
                out_idx = cmd.index("-o") + 1
                output_path = Path(cmd[out_idx])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                # Write fake PNG or SVG based on -e flag
                fmt_content = _FAKE_PNG
                try:
                    fmt_idx = cmd.index("-e") + 1
                    if cmd[fmt_idx] == "svg":
                        fmt_content = _FAKE_SVG
                except (ValueError, IndexError):
                    pass
                output_path.write_bytes(fmt_content)
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return original_run(cmd, **kwargs)

    with patch("mermaidgen.generator.subprocess.run", side_effect=_fake_run) as mock_obj:
        yield mock_obj
```

**How it works:**

1. Patches `mermaidgen.generator.subprocess.run` (the specific import path)
2. When the command starts with `mmdc`, intercepts it:
   - Reads the `-o` flag to find the output path
   - Reads the `-e` flag to determine format (PNG or SVG)
   - Writes fake but structurally valid PNG header bytes or SVG content to the output path
   - Returns `CompletedProcess` with exit code 0
3. For non-mmdc commands, falls through to the real `subprocess.run`

**Fake output data:**

- `_FAKE_PNG` — minimal valid PNG header (IHDR + IEND chunks)
- `_FAKE_SVG` — minimal valid SVG element

### The `generator` fixture

Combines `mock_mmdc` with a temp output directory:

```python
@pytest.fixture
def generator(mock_mmdc, tmp_output_dir):
    """MermaidGenerator with mocked mmdc and temp output directory."""
    return MermaidGenerator(output_dir=str(tmp_output_dir), mmdc_binary="mmdc")
```

This gives each test a clean `MermaidGenerator` instance that writes to an isolated temp directory and never calls the real mmdc.

### Syntax sample fixtures

`conftest.py` provides pre-built valid and invalid syntax as fixtures:

| Fixture | Content |
|---------|---------|
| `valid_flowchart_syntax` | Flowchart with decisions |
| `valid_sequence_syntax` | Client-Server sequence |
| `valid_class_syntax` | Animal/Dog/Cat class diagram |
| `valid_er_syntax` | User/Post ER diagram |
| `invalid_syntax` | Plain text (missing diagram type) |
| `empty_syntax` | Empty string |

### Error simulation

For testing mmdc failures, individual tests patch `subprocess.run` directly:

- **`MmcdNotFoundError`** — patch with `side_effect=FileNotFoundError`
- **Timeout** — patch with `side_effect=subprocess.TimeoutExpired`
- **Non-zero exit** — patch returning `CompletedProcess` with `returncode=1`

Example from `test_generator.py`:

```python
def test_mmdc_not_found_raises(self, tmp_path, valid_flowchart_syntax):
    with patch(
        "mermaidgen.generator.subprocess.run",
        side_effect=FileNotFoundError("mmdc not found"),
    ):
        gen = MermaidGenerator(output_dir=str(tmp_path), mmdc_binary="mmdc_does_not_exist")
        with pytest.raises(MmcdNotFoundError):
            gen.from_syntax(valid_flowchart_syntax, output_filename=str(tmp_path / "out.png"))
```

## How to Add New Tests

### Adding a test for a new template

1. Add a new test class in `test_templates.py`:

```python
class TestMyNewTemplate:
    def test_render_with_valid_params(self):
        t = MyNewTemplate()
        result = t.render(my_param="value")
        assert "expectedKeyword" in result

    def test_render_validates_as_mermaid(self):
        t = MyNewTemplate()
        result = t.render(my_param="value")
        assert MermaidValidator.validate(result) is True

    def test_render_missing_param_raises(self):
        t = MyNewTemplate()
        with pytest.raises(ValueError):
            t.render()

    def test_suggest_filename(self):
        t = MyNewTemplate()
        assert t.suggest_filename() == "my_new_template"
```

### Adding a test for new generator behavior

1. Use the `generator` fixture (includes mock_mmdc + temp dir):

```python
def test_new_feature(self, generator, valid_flowchart_syntax, tmp_output_dir):
    result = generator.from_syntax(valid_flowchart_syntax)
    assert os.path.exists(result)
    # ... additional assertions
```

### Adding a new syntax fixture

Add the constant and fixture to `conftest.py`:

```python
VALID_GANTT = """\
gantt
    title Project
    section Dev
    Task1 :a1, 2024-01-01, 30d
"""

@pytest.fixture
def valid_gantt_syntax():
    return VALID_GANTT
```

### Conventions

- Group tests in classes by feature (e.g., `TestFromSyntax`, `TestMmcdErrors`)
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- Always test both happy path and error path
- Template render tests should verify output passes `MermaidValidator.validate()`
- Use `tmp_path` (pytest built-in) for isolated file system operations
