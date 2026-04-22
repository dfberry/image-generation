← [Back to Documentation Index](../README.md)

# Testing Guide — Manim Animation Generator

## Overview

The test suite contains **162+ tests** across 9 test files, covering CLI parsing, LLM client initialization, scene code validation, rendering, image handling, and security. All tests run without a GPU, network access, or LLM — mocks are used throughout.

## Running Tests

```bash
cd manim-animation

# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_scene_builder.py -v

# Run a specific test class
python -m pytest tests/test_scene_builder.py::TestSceneCodeSafety -v

# Run a specific test
python -m pytest tests/test_scene_builder.py::TestSceneCodeSafety::test_open_call_rejected -v

# Run only integration tests
python -m pytest tests/ -m integration -v

# Run everything except integration tests
python -m pytest tests/ -m "not integration" -v
```

### Pytest Configuration

From `pyproject.toml`:

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

## Test Architecture

### No GPU, No LLM, No Network Required

Every test mocks external dependencies:
- **LLM API calls** → `unittest.mock.MagicMock` with canned responses
- **Manim subprocess** → Mocked `subprocess.run` that creates fake MP4 files
- **File system** → `tmp_path` fixture (pytest built-in) for isolated temp dirs

### Test Categories

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_cli.py` | CLI arg parsing, exit codes | `parse_args()`, `main()` return codes for each error type |
| `test_config.py` | Quality presets, Config dataclass | Enum values, string coercion, duration bounds |
| `test_llm_client.py` | LLM client init, API call mocking | Ollama/OpenAI/Azure init, missing credentials, error wrapping |
| `test_scene_builder.py` | Code extraction, validation | Markdown fences, syntax check, safety (forbidden imports/calls) |
| `test_renderer.py` | Manim subprocess, media detection | `check_manim_installed()`, render success/failure, quality paths, fallback search |
| `test_integration.py` | End-to-end `build_scene()` | Valid code passes, dangerous code rejected, missing class rejected |
| `test_image_handler.py` | Image validation, copying, context | Path validation, format checks, symlink rejection, workspace copying, LLM context |
| `test_image_cli.py` | Image CLI args, pipeline wiring | `--image`, `--image-policy` parsing, `generate_video()` image integration |
| `test_image_security.py` | AST-based image security checks | `validate_image_operations()`, `build_scene()` with image filenames |

## Shared Fixtures (`conftest.py`)

### Temp Directories

```python
@pytest.fixture
def tmp_output_dir(tmp_path):
    """Temp directory for test outputs."""

@pytest.fixture
def tmp_code_dir(tmp_path):
    """Temp directory for intermediate scene code files."""
```

### LLM Response Mocks

```python
@pytest.fixture
def mock_openai_response():
    """Valid Manim scene code in markdown fence."""

@pytest.fixture
def mock_openai_empty_response():
    """Empty content response."""

@pytest.fixture
def mock_openai_non_code_response():
    """Non-code text response."""
```

### Subprocess Mocks (Manim CLI)

```python
@pytest.fixture
def mock_subprocess_success(monkeypatch):
    """Simulates successful Manim render — creates fake MP4 at expected path."""

@pytest.fixture
def mock_subprocess_failure(monkeypatch):
    """Simulates Manim render failure with non-zero exit code."""

@pytest.fixture
def mock_subprocess_manim_not_found(monkeypatch):
    """Simulates manim CLI not installed (FileNotFoundError)."""
```

The success mock detects Manim CLI calls by checking `cmd[0] == "manim"`, constructs the expected output path from the command args, and writes a minimal fake MP4 file.

## Mock Patterns

### Mocking LLM Clients

Tests never call real APIs. The pattern is to mock `_get_client()` or the entire `LLMClient`:

```python
@patch("manim_gen.llm_client.LLMClient._get_client")
def test_ollama_returns_code(self, mock_get_client):
    mock_api = MagicMock()
    mock_api.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="from manim import *"))]
    )
    mock_get_client.return_value = mock_api

    client = LLMClient(provider="ollama")
    result = client.generate_scene_code("test prompt", 10)
    assert "manim" in result
```

### Mocking Subprocess (Manim Render)

For renderer tests, mock at the `subprocess.run` level:

```python
@patch("manim_gen.renderer.subprocess.run")
@patch("manim_gen.renderer.check_manim_installed", return_value=True)
def test_successful_render(self, mock_check, mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    # Create fake output file where renderer expects it
    expected_dir = scene_file.parent / "media" / "videos" / "scene" / "720p30"
    expected_dir.mkdir(parents=True)
    (expected_dir / "GeneratedScene.mp4").write_bytes(b"fake-mp4")

    result = render_scene(scene_file, output, QualityPreset.MEDIUM)
```

### Mocking CLI Args

Use `patch.object(sys, "argv", ...)`:

```python
def test_provider_defaults_to_ollama(self):
    with patch.object(sys, "argv", ["manim-gen", "--prompt", "test"]):
        args = parse_args()
        assert args.provider == "ollama"
```

### Mocking Environment Variables

Use `patch.dict("os.environ", ...)`:

```python
@patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
def test_openai_client_initializes(self):
    client = LLMClient(provider="openai")
    assert client.api_key == "test-key"
```

## How to Add New Tests

### 1. Choose the Right Test File

- CLI arg parsing → `test_cli.py`
- Config/presets → `test_config.py`
- LLM client behavior → `test_llm_client.py`
- Code validation/safety → `test_scene_builder.py`
- Render subprocess → `test_renderer.py`
- Image handling → `test_image_handler.py`
- Image CLI integration → `test_image_cli.py`
- Image security (AST) → `test_image_security.py`
- End-to-end pipeline → `test_integration.py`

### 2. Follow the Pattern

```python
class TestYourFeature:
    """Describe what you're testing."""

    def test_happy_path(self):
        """Normal usage works."""
        # Arrange
        # Act
        # Assert

    def test_error_case(self):
        """Bad input raises expected error."""
        with pytest.raises(SpecificError, match="expected message"):
            function_under_test(bad_input)
```

### 3. Use Existing Fixtures

Check `conftest.py` first — reuse `tmp_output_dir`, `mock_openai_response`, `mock_subprocess_success`, etc.

### 4. Mark Integration Tests

```python
@pytest.mark.integration
class TestMyIntegration:
    """Tests that exercise multiple modules together."""
```

### 5. Test Security Boundaries

When adding new validation rules, test both sides:

```python
def test_safe_input_passes(self):
    validate_safety("from manim import *\n")  # No exception

def test_dangerous_input_rejected(self):
    with pytest.raises(ValidationError, match="Forbidden"):
        validate_safety("import os\n")
```

## Image Test Fixtures

Test files for images use the `_FAKE_IMAGE` constant — a minimal byte string with a PNG header:

```python
_FAKE_IMAGE = b"\x89PNG\r\n\x1a\nfake-image-bytes-for-testing"
```

This is sufficient because `validate_image_path()` checks path, extension, and size — not file content.

Key image test fixtures:

```python
@pytest.fixture
def valid_png(tmp_path):
    """Small file with .png extension."""

@pytest.fixture
def valid_jpg(tmp_path):
    """Small file with .jpg extension."""

@pytest.fixture
def symlink_image(tmp_path):
    """Symlink → valid image. Skips if OS can't create symlinks."""
```
