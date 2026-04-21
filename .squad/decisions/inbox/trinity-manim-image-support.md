# Decision: Manim Image/Screenshot Input Support

**Date:** 2025-07-24
**Author:** Trinity (Backend Dev)
**Status:** Implemented
**Issue:** #88

## Context

Users need to include screenshots and images in Manim animations — e.g., annotating a UI screenshot or animating a diagram. This requires safe image handling, LLM prompt augmentation, and render-time asset availability.

## Decision

### Architecture
- **New module `image_handler.py`** owns all image I/O: validation, workspace copying, and LLM context generation. Single responsibility, easy to test.
- **Workspace isolation**: images are always copied to a temp directory with deterministic names (`image_0_filename.png`). Original paths are never passed to generated code or Manim.
- **Policy parameter** (`strict`/`warn`/`ignore`) controls validation behavior, letting callers choose fail-fast vs. best-effort.

### Security
- Symlinks rejected in strict mode to prevent path traversal.
- `validate_image_operations()` in `scene_builder.py` uses AST analysis to enforce:
  - ImageMobject must use string-literal filenames only (no dynamic construction)
  - Only filenames in the copied workspace set are allowed
  - File-write operations (`write_text`, `unlink`, `rmtree`, etc.) are blocked
- The renderer runs with `cwd` set to the workspace so Manim resolves image filenames locally.

### Integration Points
- `cli.py`: three new args (`--image`, `--image-descriptions`, `--image-policy`)
- `llm_client.py`: `generate_scene_code()` accepts optional `image_context` string
- `config.py`: SYSTEM_PROMPT updated with ImageMobject guidance; new few-shot example
- `renderer.py`: `render_scene()` accepts optional `assets_dir` for cwd override

## Alternatives Considered
- **Symlink images into workspace** — rejected; copying is safer and avoids platform edge cases.
- **Base64-encode images into prompt** — rejected; unnecessary for code generation, and would bloat token usage.
- **Allow dynamic filenames in generated code** — rejected; too risky. Literal-only policy is enforceable via AST.
