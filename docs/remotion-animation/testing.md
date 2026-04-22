← [Back to Documentation Index](../README.md)

# remotion-animation — Test Guide

## Test Architecture

The test suite contains **209+ tests** across 11 test files, covering every module in the Python package. Tests are pure-Python and do not require Node.js, Ollama, or any external service.

### Test Files

| File | Module Under Test | Tests | Focus |
|------|-------------------|-------|-------|
| `test_cli.py` | `cli.py` | CLI arg parsing, validation, exit codes, integration |
| `test_llm_client.py` | `llm_client.py` | Code extraction, client creation, generation, retry |
| `test_component_builder.py` | `component_builder.py` | Validation, security, import injection, writing |
| `test_renderer.py` | `renderer.py` | Subprocess, prerequisites, UTF-8, version warnings |
| `test_image_handler.py` | `image_handler.py` | Path validation, copy, context generation |
| `test_image_security.py` | `component_builder.py` | Image path security, injection, integration |
| `test_image_cli.py` | `cli.py` | Image CLI args, generate_video image pipeline |
| `test_audio_handler.py` | `audio_handler.py` | Audio validation, copy, context generation |
| `test_audio_cli.py` | `cli.py` | Audio CLI args, TTS, narration, music, sound effects |
| `test_config.py` | `config.py` | Quality presets, resolution names, constants |
| `test_demo_template.py` | `demo_template.py` | Template output, timestamp embedding, edge cases |
| `test_integration.py` | Full pipeline | End-to-end with mocked LLM + renderer |
| `conftest.py` | — | Shared fixtures |

## Running Tests

```bash
cd remotion-animation
python -m pytest tests/ -q
```

All 209 tests should pass. **1 expected skip** on Windows: `test_symlink_rejected_strict` in `test_image_handler.py` — symlink creation requires elevated privileges on Windows and is skipped with:

```python
@pytest.mark.skipif(os.name == "nt", reason="symlinks require privileges on Windows")
```

### Run specific test categories

```bash
# Only integration tests
python -m pytest tests/ -q -m integration

# Only image security tests
python -m pytest tests/test_image_security.py -q

# Only component builder tests
python -m pytest tests/test_component_builder.py -q

# Verbose with individual test names
python -m pytest tests/ -v
```

### Configuration

Test settings live in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "integration: marks tests as integration tests",
]
```

## Mock Patterns

### Module-Boundary Mocks for OpenAI SDK

The LLM client tests mock at the boundary — they never call a real LLM. Two levels of mocking:

**1. Low-level: Mock `_create_client` and `_call_llm`**

Used in `test_llm_client.py::TestGenerateComponent`:

```python
@patch("remotion_gen.llm_client._call_llm")
@patch("remotion_gen.llm_client._create_client")
def test_happy_path(self, mock_create, mock_call):
    mock_create.return_value = (MagicMock(), "llama3")
    mock_call.return_value = VALID_TSX
    result = generate_component("A blue circle", duration_seconds=5, fps=30)
```

**2. High-level: Mock `generate_component`, `write_component`, `render_video`**

Used in `test_cli.py` and `test_integration.py` to test the pipeline without any real LLM or renderer:

```python
with patch("remotion_gen.cli.generate_component", return_value="fake tsx"), \
     patch("remotion_gen.cli.write_component"), \
     patch("remotion_gen.cli.render_video", return_value=Path("out.mp4")):
    result = generate_video(prompt="test", output="out.mp4")
```

### Mock Subprocess for Renderer

Renderer tests mock `subprocess.run` and `shutil.which` to avoid requiring Node.js:

```python
@patch("remotion_gen.renderer.shutil.which", return_value="/usr/bin/npx")
@patch("remotion_gen.renderer.subprocess.run")
def test_successful_render(self, mock_run, mock_which, tmp_path):
    mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
    # ... test render_video()
```

### Image Pipeline Mocks

Image CLI integration tests use `monkeypatch` to redirect `__file__` resolution so `generate_video()` finds the test's temp directory structure:

```python
monkeypatch.setattr(cli_mod, "__file__", str(fake_gen / "cli.py"))
```

## Test Categories

### CLI Tests (`test_cli.py`)

- Argument parsing: valid prompts, missing `--prompt`/`--output`, invalid `--quality`
- Flag forwarding: `--debug`, `--duration`, `--provider`, `--model`
- Duration validation: rejects negative, zero, and out-of-range values
- Exit codes: 0 on success, 1 on `RemotionGenError`, 2 on argparse errors
- Integration: end-to-end with mocked pipeline components

### LLM Client Tests (`test_llm_client.py`)

- `_extract_code_block()`: TSX fences, generic fences, no fences, partial fences, multiline
- `_create_client()`: ollama (no key needed), openai (requires `OPENAI_API_KEY`), azure (requires 3 env vars), unknown provider, case insensitivity
- `generate_component()`: happy path, API failure, image context inclusion, retry on syntax errors, no-retry mode, model override

### Component Builder Tests (`test_component_builder.py`)

- **Structural validation**: remotion import, default export, GeneratedScene name, return statement
- **Security**: dangerous imports (fs, child_process, http, net, os, crypto, etc.), node: prefixed, require(), bare imports, subpath imports
- **Safe imports**: remotion, react, @remotion/* all pass
- **Import injection**: Img/staticFile injection, no duplication, imageSrc constant
- **Bracket validation**: balanced JSX, nested JSX, missing return
- **write_component**: file writing, debug copy, dangerous code rejection

### Renderer Tests (`test_renderer.py`)

- Success path: output returned, correct subprocess command
- Failure: stderr in RenderError, missing output file
- Edge cases: missing node_modules, missing npx, missing Node.js
- Prerequisites: `check_prerequisites()` returns informative errors
- UTF-8 handling: emoji in stdout/stderr, accented characters
- Version warnings: warnings on stderr with returncode=0 don't fail
- Command construction: `--props` includes durationInFrames, quality dimensions

### Image Handler Tests (`test_image_handler.py`)

- Extension validation: 6 valid extensions pass, 5 invalid rejected
- Edge cases: missing file, oversized file, directory path, symlinks
- Policy modes: strict raises, warn prints, ignore skips
- `copy_image_to_public()`: UUID naming, public/ creation, source untouched, unique per call
- `generate_image_context()`: filename, Img/staticFile guidance, description, directives

### Image Security Tests (`test_image_security.py`)

Comprehensive evasion pattern testing:

- **file:// blocking**: standard, uppercase, mixed case, URL-encoded (`file%3A%2F%2F`)
- **Path traversal**: `../`, `..\`, URL-encoded (`%2E%2E%2F`)
- **data: URI blocking**
- **staticFile() validation**: matching refs pass, non-matching rejected, path prefixes rejected
- **Dynamic staticFile() blocking**: template literals, variables, function calls
- **Integration**: `write_component` with `image_filename` validates end-to-end

### Config Tests (`test_config.py`)

- Preset values: low/medium/high exact dimensions and fps
- `resolution_name` property: 480p, 720p, 1080p, 4K
- Custom overrides: arbitrary width/height/fps
- Constants: DEFAULT_DURATION, MIN, MAX, DEFAULT_PROVIDER
- Completeness: exactly 3 presets exist

### Demo Template Tests (`test_demo_template.py`)

- Structure: non-empty, export default, GeneratedScene, remotion import
- Content: useCurrentFrame, useVideoConfig, AbsoluteFill, return statement
- Timestamp: embedded correctly, "Dina Berry" name present
- Edge cases: empty string, special characters, long strings, different timestamps produce different output

### Integration Tests (`test_integration.py`)

- Full pipeline: prompt → LLM → component → render → MP4
- Error handling: LLM failure, render failure, validation failure blocks render
- Output: correct directory, correct path resolution
- Component: written to remotion-project/src/

## conftest.py Fixtures

```python
@pytest.fixture
def tmp_output_dir(tmp_path)    # Temp dir for test outputs
def tmp_project_dir(tmp_path)   # Simulates remotion-project/ with src/

@pytest.fixture
def mock_openai_response()       # MagicMock with valid TSX in code block
def mock_openai_empty_response() # MagicMock with empty content
def mock_openai_non_code_response()  # MagicMock with non-code text
```

Also defines `_FAKE_MP4` bytes for renderer tests.

## How to Add New Tests

1. **Pick the right file** — match the module under test. If testing a new module, create `tests/test_<module>.py`.

2. **Use test classes** — group related tests in `class Test*:` following existing patterns.

3. **Mock at module boundaries** — don't call real LLMs or renderers. Mock `_create_client`, `_call_llm`, `subprocess.run`, or `generate_component` depending on the level you're testing.

4. **Use fixtures from conftest.py** — `tmp_output_dir`, `tmp_project_dir`, `mock_openai_response`.

5. **Include docstrings** — every test function should have a one-line docstring explaining what it verifies.

6. **Mark integration tests**:
   ```python
   @pytest.mark.integration
   def test_end_to_end(...):
   ```

7. **Run the full suite** to verify no regressions:
   ```bash
   python -m pytest tests/ -q
   ```
