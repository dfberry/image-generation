← [Back to Documentation Index](../README.md)

# Testing Guide — image-generation

How to run, understand, and extend the test suite.

## Overview

- **170+ tests** across **15 test files** (14 test files + conftest.py)
- All tests use **mocks** — no GPU or model downloads required
- Framework: **pytest** with **pytest-cov** for coverage
- All tests target the single `generate.py` module

## Running Tests

```bash
# Full suite
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=generate --cov-report=term-missing

# Single file
python -m pytest tests/test_cli_validation.py -v

# Single test
python -m pytest tests/test_cli_validation.py::test_name -v

# Short output
python -m pytest tests/
```

Or via Makefile:

```bash
make test
```

## Test Architecture

### Test Files

| File | Focus |
|------|-------|
| `conftest.py` | Shared fixtures, MockPipeline, MockImage |
| `test_batch_cli.py` | `--batch-file` CLI integration, JSON parsing |
| `test_batch_generation.py` | `batch_generate()` logic, per-item errors, validation |
| `test_bug_fixes.py` | Regression tests for specific bug fixes |
| `test_cli_validation.py` | Argparse validation, custom types, required flags |
| `test_coverage_gaps.py` | Edge cases, `__getattr__`, lazy imports, performance opts |
| `test_input_validation.py` | Dimension validation, output path validation |
| `test_memory_cleanup.py` | GPU memory cleanup, gc.collect, cache flush |
| `test_negative_prompt.py` | Negative prompt forwarding through pipeline |
| `test_oom_handling.py` | OOMError detection for CUDA and MPS |
| `test_oom_retry.py` | `generate_with_retry()` step-halving logic |
| `test_pipeline_enhancements.py` | Refiner path, LoRA loading, refiner guidance |
| `test_scheduler.py` | Scheduler swapping, validation, Karras sigmas |
| `test_security.py` | Path traversal, absolute path blocking |
| `test_unit_functions.py` | Pure function unit tests |

### conftest.py — Shared Fixtures

#### MockImage

Minimal PIL Image stand-in with a `save(path)` method (no-op).

#### MockPipeline

Full stand-in for `DiffusionPipeline`:
- Has all expected attributes: `text_encoder_2`, `vae`, `unet`, `scheduler`, `safety_checker`
- `__call__(**kwargs)` returns a result with `.images` (list of `MockImage` or mock latent)
- `return_latents=True` constructor arg switches to latent output mode
- Implements `to()`, `enable_model_cpu_offload()`, `enable_attention_slicing()`, `enable_xformers_memory_efficient_attention()`, `load_lora_weights()`, `set_adapters()`

#### Args Fixtures

| Fixture | Device | Refiner |
|---------|--------|---------|
| `mock_args_base` | CPU | No |
| `mock_args_refine` | CPU | Yes |
| `mock_args_cuda` | CUDA | No |
| `mock_args_cuda_refine` | CUDA | Yes |

All use `MagicMock()` with every field set explicitly. Width/height default to 64 (minimum valid dimension).

## Mock Patterns

### Pipeline Mocking — The `spec` Pattern

**Critical**: When creating pipeline mocks with `MagicMock(spec=...)`, pass an **instance**, not the class:

```python
# ✅ Correct — pass instance
pipe = MagicMock(spec=MockPipeline())

# ❌ Wrong — passes class, spec won't match instance attributes
pipe = MagicMock(spec=MockPipeline)
```

This matters because `MagicMock(spec=SomeClass)` creates a mock matching the **class** interface, while `MagicMock(spec=SomeClass())` matches the **instance** interface (which includes `__call__`, instance attributes, etc.).

### Standard Patching Pattern

Most tests patch `generate.load_base` and/or `generate.load_refiner` to return `MockPipeline()`:

```python
@patch("generate.load_base")
@patch("generate.load_refiner")
def test_something(mock_refiner, mock_base, mock_args_refine):
    mock_base.return_value = MockPipeline(return_latents=True)
    mock_refiner.return_value = MockPipeline()
    result = generate.generate(mock_args_refine)
    assert result == mock_args_refine.output
```

### Torch Mocking

Tests patch `generate.torch` and related modules. The lazy import system means the patched value is found in `globals()` before `_ensure_heavy_imports()` would import the real thing:

```python
@patch("generate.torch")
def test_device_detection(mock_torch):
    mock_torch.cuda.is_available.return_value = True
    assert generate.get_device(False) == "cuda"
```

## Lazy Import Testing

The lazy import system (`_ensure_heavy_imports` + `__getattr__`) requires special patterns.

### The `_patch_heavy` Context Manager

Used in `test_coverage_gaps.py` for testing lazy import edge cases:

```python
@contextmanager
def _patch_heavy():
    """Inject mock torch/diffusers into generate's globals, then restore."""
    mock_torch = MagicMock()
    mock_torch.cuda.empty_cache = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = False

    # Save current state
    had_torch = "torch" in gen_module.__dict__
    old_torch = gen_module.__dict__.get("torch")

    # Inject mocks directly into module __dict__
    gen_module.__dict__["torch"] = mock_torch
    gen_module.__dict__["diffusers"] = MagicMock()

    # Disable the real import guard
    original_ensure = gen_module._ensure_heavy_imports
    gen_module._ensure_heavy_imports = lambda: None

    try:
        yield mock_torch
    finally:
        # Restore original state
        gen_module._ensure_heavy_imports = original_ensure
        if had_torch:
            gen_module.__dict__["torch"] = old_torch
        else:
            gen_module.__dict__.pop("torch", None)
```

**Key points:**
- Injects mocks via `gen_module.__dict__` (not `@patch`) to bypass PEP 562 `__getattr__`
- Replaces `_ensure_heavy_imports` with a no-op lambda
- Saves and restores original state in `finally`

### Why `__dict__` Instead of `@patch`

When testing the lazy import machinery itself, `@patch("generate.torch")` triggers `__getattr__` which calls `_ensure_heavy_imports()` — defeating the purpose. Direct `__dict__` injection bypasses this.

## Batch Test Patching

**Critical**: When testing `batch_generate()`, patch `generate_with_retry`, not `generate`:

```python
# ✅ Correct — batch_generate calls generate_with_retry
@patch("generate.generate_with_retry")
def test_batch(mock_retry):
    mock_retry.return_value = "outputs/test.png"
    results = generate.batch_generate([...])

# ❌ Wrong — batch_generate does NOT call generate directly
@patch("generate.generate")
def test_batch(mock_gen):
    ...
```

This is because `batch_generate()` calls `generate_with_retry()` (which internally calls `generate()`). Patching `generate` won't intercept the batch path.

## Adding New Tests

### 1. Choose the Right Test File

Match the feature area to an existing file, or create a new one if it's a new area.

### 2. Use conftest.py Fixtures

```python
def test_my_feature(mock_args_base):
    mock_args_base.my_new_flag = "value"
    # ... test logic ...
```

### 3. Follow the Patching Pattern

```python
from unittest.mock import patch, MagicMock
from conftest import MockPipeline

@patch("generate.load_base")
@patch("generate.torch")
def test_my_feature(mock_torch, mock_base, mock_args_base):
    mock_torch.cuda.is_available.return_value = False
    mock_torch.backends.mps.is_available.return_value = False
    mock_base.return_value = MockPipeline()

    result = generate.generate(mock_args_base)
    assert result == mock_args_base.output
```

### 4. Add New Fixture Fields

If you added a new CLI flag, add it to all four conftest.py fixtures:
- `mock_args_base`
- `mock_args_refine`
- `mock_args_cuda`
- `mock_args_cuda_refine`

## CI Workflow

Defined in `.github/workflows/tests.yml`:

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install 'ruff>=0.4.0'
      - working-directory: image-generation
        run: ruff check .

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - working-directory: image-generation
        run: |
          pip install torch --index-url https://download.pytorch.org/whl/cpu
          pip install -r requirements-dev.txt
      - working-directory: image-generation
        run: python -m pytest tests/ -v --cov=generate --cov-report=term-missing
```

**Key details:**
- `working-directory: image-generation` — CI runs from the package root, not repo root
- CPU-only PyTorch installed via `--index-url https://download.pytorch.org/whl/cpu`
- Tests run on both Python 3.10 and 3.11
- Lint runs first; tests only run if lint passes (`needs: lint`)
- Actor allowlist restricts to `["diberry","dfberry"]`
- Triggered by `workflow_dispatch` or `pull_request` with `run-ci` label

## Coverage

Run with coverage report:

```bash
python -m pytest tests/ -v --cov=generate --cov-report=term-missing
```

The `--cov=generate` flag measures coverage of the `generate` module specifically. `--cov-report=term-missing` shows which lines are not covered.
