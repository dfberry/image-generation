← [Back to Documentation Index](../README.md)

# Development Guide — image-generation

How to work on the image-generation package.

## Repository Structure

```
image-generation/            # Package root (working-directory for CI)
├── generate.py              # Main CLI — single-file pipeline module
├── generate_blog_images.sh  # Batch shell script (5 blog images)
├── batch_blog_images.json   # Example batch JSON file
├── Makefile                 # Build automation (setup, test, lint, format)
├── ruff.toml                # Linter/formatter config
├── requirements.txt         # Runtime dependencies (minimum versions)
├── requirements.lock        # Pinned dependencies (exact versions for CI)
├── requirements-dev.txt     # Dev dependencies (includes requirements.txt + pytest, ruff, pytest-cov)
├── CONTRIBUTING.md          # Contributor guide
├── README.md                # Usage docs
├── prompts/
│   └── examples.md          # Master prompt library and style guide
├── outputs/                 # Generated PNG images (1024×1024)
├── tests/                   # pytest test suite (14 test files + conftest.py)
│   ├── conftest.py          # Shared fixtures and mock utilities
│   ├── test_batch_cli.py
│   ├── test_batch_generation.py
│   ├── test_bug_fixes.py
│   ├── test_cli_validation.py
│   ├── test_coverage_gaps.py
│   ├── test_input_validation.py
│   ├── test_memory_cleanup.py
│   ├── test_negative_prompt.py
│   ├── test_oom_handling.py
│   ├── test_oom_retry.py
│   ├── test_pipeline_enhancements.py
│   ├── test_scheduler.py
│   ├── test_security.py
│   └── test_unit_functions.py
└── docs/                    # Package-level docs
    ├── design.md
    ├── feature-specification.md
    └── security.md
```

## Coding Conventions

### Linter: ruff

Configuration in `ruff.toml`:

```toml
target-version = "py310"
line-length = 120
exclude = ["venv", "__pycache__", "outputs"]

[lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]

[lint.isort]
known-first-party = ["generate"]
```

**Active rule sets:**
| Rule prefix | Category |
|-------------|----------|
| `E` | pycodestyle errors |
| `F` | Pyflakes (undefined names, unused imports, etc.) |
| `W` | pycodestyle warnings |
| `I` | isort (import ordering) |

`E501` (line too long) is ignored — the 120-character line-length applies to the formatter only.

### Commands

```bash
ruff check .          # Lint
ruff check --fix .    # Auto-fix
ruff format .         # Format
```

Or via Makefile:

```bash
make lint
make format
```

### Style Patterns

- **Single module**: All pipeline code lives in `generate.py`. No package structure.
- **Underscore prefix**: Internal helpers are prefixed with `_` (e.g., `_load_pipeline`, `_run_inference`).
- **Lazy imports**: Heavy dependencies (`torch`, `diffusers`) are imported on first use, not at module level.
- **`SimpleNamespace`**: Used for constructing args objects in batch processing and retry logic (avoids MagicMock in production).
- **Explicit cleanup**: Every resource is explicitly `del`'d and garbage collected.
- **Logging**: Uses `logging.getLogger(__name__)`. No print statements.

## Adding a New CLI Flag

1. **Add to `parse_args()`** in `generate.py`:
   ```python
   parser.add_argument("--my-flag", type=str, default="value",
                       help="Description of the flag")
   ```

2. **Use in `generate()` or helpers** via `args.my_flag` (argparse converts hyphens to underscores).

3. **Forward in batch path** — if the flag should work with `--batch-file`, add it to the `SimpleNamespace` in `batch_generate()`:
   ```python
   batch_args = SimpleNamespace(
       # ... existing fields ...
       my_flag=args.my_flag if args else "default",
   )
   ```

4. **Add to conftest.py fixtures** — add the field to `mock_args_base`, `mock_args_refine`, `mock_args_cuda`, and `mock_args_cuda_refine`.

5. **Write tests** in the appropriate test file.

6. **Update README.md** options table.

### Custom Argparse Types

The module defines custom argparse type validators:
- `_positive_int(value)` — integers > 0
- `_non_negative_float(value)` — floats >= 0
- `_dimension(value)` — integers >= 64, divisible by 8

## Scheduler System

Schedulers control the noise reduction strategy during image generation.

### Supported Schedulers

All 10 schedulers are listed in the `SUPPORTED_SCHEDULERS` list in `generate.py`:

```
DPMSolverMultistepScheduler    (default, gets Karras sigmas)
EulerDiscreteScheduler
EulerAncestralDiscreteScheduler
DDIMScheduler
LMSDiscreteScheduler
PNDMScheduler
UniPCMultistepScheduler
HeunDiscreteScheduler
KDPM2DiscreteScheduler
DEISMultistepScheduler
```

### How It Works

`apply_scheduler(pipeline, scheduler_name)`:
1. Validates name against `SUPPORTED_SCHEDULERS`
2. Gets class from `diffusers` module via `getattr`
3. Extracts existing scheduler config from the pipeline
4. For `DPMSolverMultistepScheduler`, enables Karras sigmas
5. Creates new scheduler with `scheduler_cls.from_config(config)`

### Adding a New Scheduler

1. Add the class name to `SUPPORTED_SCHEDULERS` list
2. Add any special config (like Karras sigmas) in the `apply_scheduler()` function
3. Write a test in `tests/test_scheduler.py`

## LoRA Loading

LoRA (Low-Rank Adaptation) allows fine-tuned style weights without replacing the full model.

```python
def apply_lora(pipeline, lora, lora_weight=0.8):
    pipeline.load_lora_weights(lora)
    pipeline.set_adapters(["default"], adapter_weights=[lora_weight])
```

- Triggered by `--lora <model_id_or_path>` and `--lora-weight <float>`
- Applied after scheduler setup in `_load_pipeline()`
- Weight range: 0.0 (no effect) to 1.0 (full effect), default 0.8

## Modifying the Pipeline

### Changing the base model
Edit `load_base()` — change the HuggingFace model ID in `DiffusionPipeline.from_pretrained()`.

### Changing the refiner
Edit `load_refiner()` — change the model ID. The refiner must share the same text encoder and VAE architecture.

### Changing the base/refiner split ratio
Edit `_HIGH_NOISE_FRAC` (currently 0.8 = 80% base, 20% refiner). This value is used as `denoising_end` (base) and `denoising_start` (refiner).

### Adding pipeline stages
Add a new helper function following the `_run_*` pattern. Call it from `generate()` in the appropriate pipeline path (base-only or base+refiner).

## Branch Naming

```
squad/{issue-number}-{kebab-case-slug}
```

Examples:
- `squad/12-add-batch-retry`
- `squad/29-batch-validation`

## PR Workflow

1. Branch from `main` using naming convention above
2. Write tests first (TDD)
3. Run full test suite: `python -m pytest tests/ -v`
4. Run lint: `ruff check .`
5. Open PR against `main` with:
   - What changed and why
   - Issue number (e.g., "Closes #12")
   - Test results summary

## Dependency Management

### `requirements.txt` — Runtime Dependencies (Minimum Versions)

```
diffusers>=0.21.0
transformers>=4.30.0
accelerate>=0.24.0
safetensors>=0.3.0
invisible-watermark>=0.2.0
torch>=2.1.0
Pillow>=10.0.0
```

Use `>=` version specifiers. These are minimum-compatible versions.

### `requirements.lock` — Pinned Dependencies (Exact Versions)

```
diffusers==0.21.0
transformers==4.30.0
accelerate==0.24.0
safetensors==0.3.0
invisible-watermark==0.2.0
torch==2.1.0
Pillow==10.0.0
```

Use `==` version specifiers. For reproducible builds in CI/CD.

### `requirements-dev.txt` — Dev Dependencies

```
-r requirements.txt
pytest>=7.0
ruff>=0.4.0
pytest-cov>=4.0
```

Includes all runtime deps plus test tools.

### Makefile Targets

| Target | Command | Description |
|--------|---------|-------------|
| `make all` | `setup lint test` | Full build |
| `make setup` | Create venv + install-dev | Dev environment setup |
| `make install` | `pip install -r requirements.txt` | Runtime deps only |
| `make install-dev` | `pip install -r requirements-dev.txt` | All deps |
| `make test` | `pytest tests/ -v` | Run tests |
| `make lint` | `ruff check .` | Lint |
| `make format` | `ruff format .` | Format |
| `make clean` | Remove caches | Cleanup |

## CI Workflow

The CI workflow (`.github/workflows/tests.yml`) runs on:
- `workflow_dispatch` (manual)
- `pull_request` with `run-ci` label

Two jobs:
1. **lint** — ruff check on Python 3.11
2. **test** — pytest on Python 3.10 and 3.11

All jobs use `working-directory: image-generation`.

CI installs CPU-only PyTorch (`--index-url https://download.pytorch.org/whl/cpu`) to avoid GPU dependencies.

Actor allowlist restricts CI triggers to `["diberry","dfberry"]`.
