← [Back to Documentation Index](../README.md)

# Development Guide — Manim Animation Generator

## Repository Structure

```
manim-animation/
├── manim_gen/                  # Python package
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point and orchestration
│   ├── config.py               # Quality presets, prompts, allowed imports
│   ├── errors.py               # Custom exception hierarchy
│   ├── image_handler.py        # Image validation, copying, LLM context
│   ├── llm_client.py           # Ollama/OpenAI/Azure LLM wrapper
│   ├── renderer.py             # Manim subprocess wrapper
│   └── scene_builder.py        # Code extraction, AST validation, security
├── tests/                      # Test suite (162+ tests)
│   ├── conftest.py             # Shared fixtures (mocks, temp dirs)
│   ├── test_cli.py             # CLI arg parsing, exit codes
│   ├── test_config.py          # Quality presets, Config dataclass
│   ├── test_image_cli.py       # Image CLI args, generate_video integration
│   ├── test_image_handler.py   # Image validation, copying, context generation
│   ├── test_image_security.py  # AST-based image operation validation
│   ├── test_integration.py     # End-to-end build_scene pipeline
│   ├── test_llm_client.py      # LLM client init, API calls, error handling
│   ├── test_renderer.py        # Manim subprocess, media dir detection
│   └── test_scene_builder.py   # Code extraction, syntax/safety/class checks
├── outputs/                    # Generated videos (gitignored)
├── media/                      # Manim working directory (gitignored)
├── pyproject.toml              # Package config, dependencies, tool settings
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Dev dependencies (pytest, ruff)
└── README.md                   # Project documentation
```

## Package Configuration

The project uses `pyproject.toml` with setuptools as the build backend:

- **Entry point**: `manim-gen = "manim_gen.cli:main"` — installs the `manim-gen` CLI command
- **Python**: Requires `>=3.10`
- **Runtime deps**: `manim>=0.18.0,<0.20.0`, `openai>=1.0.0,<2.0.0`
- **Dev deps** (optional): `pytest>=7.0.0`, `ruff>=0.1.0`
- **Version ceilings**: Upper bounds prevent breaking changes from major version bumps

### Audio Module (`audio_handler.py`)

The audio module validates and manages sound effect files for Manim animations:

- **`validate_audio_path()`** — Symlink rejection, existence check, format validation (`.wav`, `.mp3`, `.ogg`), size limit (50 MB). Returns bool; raises `AudioValidationError` in strict mode.
- **`copy_audio_to_workspace()`** — Copies validated audio to isolated temp directory with deterministic filenames (`sfx_N_name.ext`).
- **`generate_audio_context()`** — Generates LLM prompt context explaining `self.add_sound()` API and available files.
- **`validate_audio_operations()`** — AST-walks generated code ensuring all `self.add_sound()` calls use string literals and reference only provided files.

Add new audio formats by updating `ALLOWED_AUDIO_EXTENSIONS` in `audio_handler.py`.

## Coding Conventions

### Linting with Ruff

Configured in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]
```

Rule categories:
- **E** — pycodestyle errors
- **F** — pyflakes (unused imports, undefined names)
- **I** — isort (import ordering)
- **N** — pep8-naming conventions
- **W** — pycodestyle warnings
- **E501** ignored — line length handled by formatter, not linter

Commands:
```bash
ruff check manim_gen/       # Lint
ruff format manim_gen/      # Format
```

### Code Style

- Type hints on all public function signatures
- Docstrings on all public functions (Google style with Args/Returns/Raises)
- Explicit over implicit — no magic globals, no monkey-patching
- Lazy imports for heavy dependencies (OpenAI SDK loaded in `_get_client()`)
- Custom exceptions over generic `Exception` — see `errors.py`

## How to Add a New LLM Provider

1. **Update `llm_client.py`**:
   - Add the provider name to the `__init__` method's `if/elif` chain
   - Read any required env vars and validate them
   - Add a lazy client initialization block in `_get_client()`
   - Add default model to `DEFAULT_MODELS` dict

2. **Update `cli.py`**:
   - Add the provider to the `--provider` choices list: `choices=["ollama", "openai", "azure", "your_provider"]`

3. **Update documentation**:
   - Add env vars to the CLI epilog in `parse_args()`
   - Update `README.md` with setup instructions

4. **Add tests** in `tests/test_llm_client.py`:
   - Test initialization with valid credentials
   - Test missing credentials raises `LLMError`
   - Test `generate_scene_code()` returns code (mock the API)

Example skeleton:
```python
# In LLMClient.__init__():
elif self.provider == "anthropic":
    self.api_key = os.getenv("ANTHROPIC_API_KEY")
    if not self.api_key:
        raise LLMError("Anthropic requires ANTHROPIC_API_KEY")

# In LLMClient._get_client():
elif self.provider == "anthropic":
    from anthropic import Anthropic
    self._client = Anthropic(api_key=self.api_key)
```

> **Note**: The current architecture assumes all providers use OpenAI-compatible chat completions. If the new provider uses a different API shape, you'll need to add a provider-specific `generate_scene_code()` path.

## How to Extend Scene Validation Rules

### Adding a New Forbidden Call

Add the function name to `FORBIDDEN_CALLS` in `scene_builder.py`:

```python
FORBIDDEN_CALLS = frozenset({
    "open", "exec", "eval", "__import__",
    "compile", "getattr", "setattr", "delattr",
    "globals", "locals", "vars", "dir",
    "breakpoint", "input",
    "your_new_function",  # ← add here
})
```

### Adding a New Allowed Import

Add the module name to `ALLOWED_IMPORTS` in `config.py`:

```python
ALLOWED_IMPORTS = {
    "manim",
    "math",
    "numpy",
    "your_new_module",  # ← add here
}
```

> **Important**: Only add modules that are safe for untrusted code to use. The allowed import set is a security boundary.

### Adding a New Validation Pass

Add a new `validate_*()` function in `scene_builder.py` and call it from `build_scene()`:

```python
def validate_custom_rule(code: str) -> None:
    """Your custom validation."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        # Your checks here
        pass

def build_scene(llm_output, output_path, image_filenames=None):
    # ... existing validation ...
    validate_custom_rule(code)  # ← add call here
    # ... write file ...
```

## How to Add New Quality Presets

1. Add a new enum member in `config.py`:

```python
class QualityPreset(Enum):
    LOW = ("l", 480, 15)
    MEDIUM = ("m", 720, 30)
    HIGH = ("h", 1080, 60)
    ULTRA = ("k", 2160, 60)  # ← 4K preset
```

2. Add the quality directory mapping in `renderer.py`:

```python
manim_output = (
    base_dir / "media" / "videos" / scene_stem / {
        QualityPreset.LOW: "480p15",
        QualityPreset.MEDIUM: "720p30",
        QualityPreset.HIGH: "1080p60",
        QualityPreset.ULTRA: "2160p60",  # ← add here
    }[quality] / "GeneratedScene.mp4"
)
```

3. Add the choice to CLI args in `cli.py`:

```python
choices=["low", "medium", "high", "ultra"]
```

4. Add tests in `test_config.py` and `test_renderer.py`.

## Few-Shot Prompt System

The LLM receives two prompt components from `config.py`:

- **`SYSTEM_PROMPT`**: Core instructions — create `GeneratedScene` class, use only allowed imports, use Manim CE syntax, handle cleanup of previous objects. Also contains image usage guidelines.
- **`FEW_SHOT_EXAMPLES`**: Four example prompt→code pairs demonstrating:
  1. Shape animation (Create, Rotate, Transform)
  2. Image usage (ImageMobject, animate.shift, FadeIn)
  3. Text with equations (MathTex, Write, FadeOut)
  4. Counting sequence (proper FadeOut/FadeIn cleanup pattern)

These are concatenated into the user message in `generate_scene_code()`:

```
[FEW_SHOT_EXAMPLES]
[IMAGE_CONTEXT (optional)]
User request (target duration: {N} seconds): {prompt}
Generate the Python code:
```

To add new examples, append to `FEW_SHOT_EXAMPLES` in `config.py`. Keep examples focused on patterns that LLMs commonly get wrong (like stacking text without cleanup).

## Branch Naming

For issue-linked work:

```
squad/{issue-number}-{kebab-case-slug}
```

Examples:
- `squad/42-add-audio-support`
- `squad/90-fix-media-dir-detection`

## PR Workflow

1. Create a feature branch from `main`
2. Make changes, run linter and tests
3. Push and open a PR
4. Ensure all tests pass in CI

## Dependency Management

| File | Purpose |
|------|---------|
| `requirements.txt` | Runtime deps: `manim>=0.18.0`, `openai>=1.0.0` |
| `requirements-dev.txt` | Dev deps: `pytest>=7.0.0`, `ruff>=0.1.0` |
| `pyproject.toml` | Canonical deps with version ceilings (`<0.20.0`, `<2.0.0`) |

Install for development:
```bash
pip install -e .                    # Editable install (uses pyproject.toml)
pip install -r requirements-dev.txt # Dev tools
```
