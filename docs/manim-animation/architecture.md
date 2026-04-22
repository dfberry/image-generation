← [Back to Documentation Index](../README.md)

# Architecture — Manim Animation Generator

## Overview

The Manim Animation Generator (`manim-gen`) converts natural language prompts into rendered MP4 animations using Manim Community Edition. The tool bridges an LLM (for code generation) with Manim (for rendering), with a security-focused validation layer in between.

## Pipeline Flow

```
User Prompt (+ optional images)
        │
        ▼
┌──────────────────┐
│    cli.py         │  Parse args, build Config, orchestrate pipeline
│    (entry point)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────────┐
│  image_handler.py │────▶│ Validate, copy images    │
│  (optional)       │     │ to isolated workspace    │
└────────┬─────────┘     └─────────────────────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────────┐
│  llm_client.py   │────▶│ Ollama / OpenAI / Azure  │
│                  │     │ Chat Completions API     │
└────────┬─────────┘     └─────────────────────────┘
         │
         │  Raw LLM output (may include markdown fences)
         ▼
┌──────────────────┐
│ scene_builder.py │
│                  │
│  1. Extract code │  Strip ```python fences
│  2. Syntax check │  compile() verification
│  3. Safety check │  AST-based forbidden import/call scan
│  4. Class check  │  Ensure GeneratedScene exists
│  5. Image check  │  (if images provided) Validate ImageMobject calls
│  6. Write file   │  Write validated code to scene.py
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────────┐
│  renderer.py     │────▶│ subprocess: manim render │
│                  │     │ scene.py GeneratedScene  │
└────────┬─────────┘     │ --format=mp4 -q{l,m,h}  │
         │               └─────────────────────────┘
         ▼
    MP4 Video (outputs/)
```

## Module Breakdown

### `cli.py` — Entry Point & Orchestrator

- Parses CLI arguments via `argparse`
- Builds a `Config` dataclass from args
- Orchestrates the full pipeline: LLM → build → render
- Handles `--demo` mode (auto-generated title card prompt)
- Maps exceptions to exit codes:
  - `0` — Success
  - `1` — LLM error
  - `2` — Validation error
  - `3` — Render error
  - `4` — Unexpected error
  - `5` — Image validation error

### `llm_client.py` — LLM Provider Abstraction

Wraps three providers behind a single `LLMClient` interface:

| Provider | Backend | Auth | Default Model |
|----------|---------|------|---------------|
| `ollama` | Local Ollama via OpenAI-compatible API | None (key = `"ollama"`) | `llama3` |
| `openai` | OpenAI API | `OPENAI_API_KEY` env var | `gpt-4` |
| `azure`  | Azure OpenAI | `AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` | Deployment name |

Key design decisions:
- **Lazy client initialization** (`_get_client()`) — avoids importing `openai` at module load time, making tests fast and dependency-free.
- **OpenAI SDK for all providers** — Ollama exposes an OpenAI-compatible `/v1` endpoint, so all three providers use the same `openai` Python SDK.
- **Structured error mapping** — catches `AuthenticationError`, `RateLimitError`, `APIConnectionError` and wraps them in `LLMError` with category tags (`[auth]`, `[rate_limit]`, `[connection]`).
- **Few-shot prompting** — `SYSTEM_PROMPT` and `FEW_SHOT_EXAMPLES` from `config.py` are injected into every request.

### `scene_builder.py` — Code Extraction & Validation

Four-stage validation pipeline:

1. **`extract_code_block()`** — Extracts Python from markdown fences (`\`\`\`python ... \`\`\``). Falls back to plain fences, then raw text if `class GeneratedScene` is detected.

2. **`validate_syntax()`** — Compiles code with `compile()` to catch syntax errors before AST parsing.

3. **`validate_safety()`** — AST-walks the parsed tree checking:
   - **Imports**: Only `manim`, `math`, `numpy` allowed (checked against `ALLOWED_IMPORTS`)
   - **Forbidden calls**: `open`, `exec`, `eval`, `__import__`, `compile`, `getattr`, `setattr`, `delattr`, `globals`, `locals`, `vars`, `dir`, `breakpoint`, `input`
   - **Forbidden names**: `__import__`, `__builtins__`, `__loader__`, `__spec__`
   - **Attribute-based bypass**: Catches `obj.exec()`, `builtins.open()`, etc.

4. **`validate_scene_class()`** — Ensures the AST contains a `ClassDef` node named `GeneratedScene`.

5. **`validate_image_operations()`** (conditional) — When images are provided:
   - `ImageMobject` must use string literal filenames only (no variables, f-strings, concatenation)
   - Filenames must be in the allowed set (workspace copies)
   - File-write operations blocked: `write_text`, `write_bytes`, `unlink`, `rmdir`, `remove`, `rmtree`, `rename`

### `renderer.py` — Subprocess Isolation

- Checks `manim` CLI availability via `shutil.which()`
- Builds and runs the render command:
  ```
  manim render <scene_file> GeneratedScene --format=mp4 -q{l,m,h} --disable_caching
  ```
- When images are provided, sets `cwd` to the workspace directory so Manim can find image assets
- Locates output at `media/videos/<scene_stem>/<quality_dir>/GeneratedScene.mp4`
- Falls back to `rglob("GeneratedScene.mp4")` if the primary path doesn't match
- Moves the rendered file to the user's requested output path

### `config.py` — Configuration & Prompts

- **`QualityPreset` enum**: Maps quality names to Manim flags and resolution
  - `LOW` = `-ql`, 480p, 15fps
  - `MEDIUM` = `-qm`, 720p, 30fps
  - `HIGH` = `-qh`, 1080p, 60fps
- **`Config` dataclass**: Runtime configuration with validation (duration 5–30s)
- **`ALLOWED_IMPORTS`**: Security whitelist — `{"manim", "math", "numpy"}`
- **`SYSTEM_PROMPT`**: Instructions for the LLM on how to generate valid Manim code
- **`FEW_SHOT_EXAMPLES`**: Four example prompt→code pairs covering shapes, images, equations, and counting sequences

### `errors.py` — Exception Hierarchy

```
ManimGenError (base)
├── LLMError          — API failures, auth issues, rate limits
├── RenderError       — Manim/FFmpeg subprocess failures
├── ValidationError   — AST/syntax/safety check failures
└── ImageValidationError — Bad paths, formats, sizes, symlinks
```

### `image_handler.py` — Image Pipeline

- **`validate_image_path()`** — Checks existence, file type, extension (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp`), size (≤100MB), rejects symlinks. Policy modes: `strict` (raise), `warn` (log), `ignore` (skip).
- **`copy_images_to_workspace()`** — Copies validated images to an isolated temp directory with deterministic names (`image_0_filename.ext`, `image_1_filename.ext`).
- **`generate_image_context()`** — Builds an LLM context block listing available images with usage examples.

## Security Model

### Defense in Depth

Generated code passes through multiple security layers before execution:

1. **Import whitelist** — Only `manim`, `math`, `numpy` can be imported. All other imports (including `os`, `subprocess`, `socket`, `requests`, `importlib`) are blocked at the AST level.

2. **Forbidden calls** — Dangerous builtins (`open`, `exec`, `eval`, `compile`, `getattr`, `setattr`, `delattr`, `globals`, `locals`, `vars`, `dir`, `breakpoint`, `input`, `__import__`) are blocked whether called directly or via attribute access.

3. **Forbidden name references** — `__import__`, `__builtins__`, `__loader__`, `__spec__` cannot even be referenced.

4. **Image operation validation** — When images are provided, `ImageMobject` must use string literal filenames from the allowed set. File-write operations are blocked.

5. **Subprocess isolation** — Generated code never runs in the main process. Manim's CLI executes it in a separate subprocess.

6. **Workspace isolation** — Images are copied to a temporary directory; the generated code accesses copies, not originals.

### What Can Generated Code Do?

- Import from `manim`, `math`, `numpy`
- Create Manim scenes with animations
- Use `ImageMobject` with pre-validated filenames (when images are provided)
- Standard math operations

### What Is Blocked?

- File I/O (`open()`, `write_text()`, `unlink()`, etc.)
- Code execution (`exec()`, `eval()`, `compile()`)
- Dynamic imports (`__import__()`, `importlib`)
- Introspection (`getattr()`, `globals()`, `locals()`)
- Network access (no `socket`, `requests`, `urllib`)
- System access (no `os`, `subprocess`, `sys`)

## Quality Presets

| Preset   | Flag | Resolution | FPS | Use Case |
|----------|------|-----------|-----|----------|
| `low`    | `-ql` | 480p  | 15  | Quick previews, testing |
| `medium` | `-qm` | 720p  | 30  | Default, good balance |
| `high`   | `-qh` | 1080p | 60  | Final output, presentations |
