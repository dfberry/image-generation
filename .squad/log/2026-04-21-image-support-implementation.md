# Image/Screenshot Input Support Implementation — 2026-04-21

**Branches:** `squad/88-manim-image-support`, `squad/89-remotion-image-support`
**PRs:** #88 (manim), #89 (remotion)
**User:** Dina Berry

## Summary

Implemented secure image/screenshot input support for both animation packages (Manim and Remotion). Both implementations follow consistent security patterns: image validation, workspace isolation, LLM context injection, and AST-based generated-code verification. 67 tests pass on manim, 64 on remotion (63 pass, 1 skip due to Windows symlink behavior).

## Timeline

| Step | Agent | Action |
|------|-------|--------|
| 1 | Trinity (manim worktree) | Implemented `image_handler.py`, modified `cli.py`, `llm_client.py`, `config.py`, `scene_builder.py`, `renderer.py`, `errors.py`. |
| 2 | Neo (manim worktree) | Wrote 67 tests: `test_image_handler.py`, `test_image_security.py`, `test_image_cli.py`. All passing. |
| 3 | Trinity (remotion worktree) | Implemented `image_handler.py`, modified `cli.py`, `llm_client.py`, `component_builder.py`, `errors.py`. Created `public/.gitkeep`. |
| 4 | Neo (remotion worktree) | Wrote 64 tests: `test_image_handler.py`, `test_image_security.py`, `test_image_cli.py`. 63 pass, 1 skip (Windows symlink). |

## Key Decisions

### Manim Implementation (PR #88)

**Architecture:**
- New `image_handler.py` module owns all image I/O (validation, workspace copying, LLM context generation)
- Images copied to temp workspace with deterministic names: `image_0_filename.png`
- Policy parameter (`strict`/`warn`/`ignore`) for validation strictness

**Security:**
- Symlinks rejected in strict mode (path traversal prevention)
- `validate_image_operations()` in `scene_builder.py`:
  - ImageMobject must use string-literal filenames only
  - Only approved filenames allowed
  - File-write operations blocked
- Renderer runs with workspace `cwd` for local image resolution

**Integration:**
- CLI: `--image`, `--image-descriptions`, `--image-policy` flags
- `llm_client.py`: accepts optional `image_context` string
- `config.py`: SYSTEM_PROMPT updated with ImageMobject guidance
- `renderer.py`: accepts optional `assets_dir` for cwd override

### Remotion Implementation (PR #89)

**Architecture:**
- New `image_handler.py` module with validation, copy, LLM context generation
- Images copied to `remotion-project/public/` with UUID-sanitized filenames: `image_{uuid8}.ext`
- Policy flag (`strict`/`warn`/`ignore`) controls validation

**Security:**
- `component_builder.py` blocks `file://` URLs, path traversal (`../`), unapproved `staticFile()` calls
- Existing dangerous-import blocking unchanged
- LLM context injection into user prompt (not system prompt)

**Integration:**
- CLI: `--image`, `--image-description`, `--image-policy` flags
- `llm_client.py`: accepts `image_context`, updated system prompt
- `component_builder.py`: `validate_image_paths()`, `inject_image_imports()`
- No renderer changes needed (Remotion CLI auto-serves `public/`)

## Test Coverage

### Manim (67 tests)
- `test_image_handler.py`: Validation, copying, context generation
- `test_image_security.py`: AST analysis, symlink rejection, literal-only enforcement
- `test_image_cli.py`: CLI args parsing, integration

**Result:** ✅ All 67 passing

### Remotion (64 tests)
- `test_image_handler.py`: Validation, UUID copying, context generation
- `test_image_security.py`: `staticFile()` validation, path traversal blocks, dangerous imports
- `test_image_cli.py`: CLI args parsing, integration

**Result:** ✅ 63 passing, 1 skip (Windows symlink limitation, not a blocker)

## Design Rationale

**Why consistent patterns across packages?**
- Both need image I/O, validation, workspace isolation, and generated-code safety
- Separate `image_handler.py` modules in each package enable independent evolution
- Consistent API (`--image`, policy flags, context injection) improves user experience

**Why workspace isolation?**
- Prevents accidental/intentional file access outside the animation assets
- Deterministic naming removes path-traversal attack surface
- Temporary directories cleaned up after render

**Why LLM context injection?**
- LLM needs guidance on API usage (`ImageMobject` for manim, `staticFile()` for remotion)
- Context string provided to `generate_scene_code()` / `generate_component_code()`
- System prompts updated with general guidance; user context is task-specific

**Why AST analysis for manim? Why `staticFile()` validation for remotion?**
- Manim: dynamic filename construction is hard to reason about; literal-only policy is enforceable via AST
- Remotion: `staticFile()` calls are the attack surface; validation checks filename matches approved set

## Files Changed

### Manim (`squad/88-manim-image-support`)
**New:**
- `manim-animation/image_handler.py` — image I/O, validation, context generation
**Modified:**
- `manim-animation/cli.py` — new args
- `manim-animation/llm_client.py` — `image_context` parameter
- `manim-animation/config.py` — SYSTEM_PROMPT guidance
- `manim-animation/scene_builder.py` — `validate_image_operations()` AST check
- `manim-animation/renderer.py` — `assets_dir` support
- `manim-animation/errors.py` — image-specific error types

### Remotion (`squad/89-remotion-image-support`)
**New:**
- `remotion-animation/image_handler.py` — image I/O, validation, context generation
- `remotion-animation/public/.gitkeep` — ensure public/ directory tracked
**Modified:**
- `remotion-animation/cli.py` — new args
- `remotion-animation/llm_client.py` — `image_context` parameter
- `remotion-animation/component_builder.py` — `validate_image_paths()`, `inject_image_imports()`
- `remotion-animation/errors.py` — `ImageValidationError`

## Next Steps (Post-Merge)

- Team PR review and approval of #88 and #89
- Update documentation (CLI help, README) with image input examples
- Consider integration tests with real animation renders
- Monitor user feedback on image handling workflow

---

*— Scribe | Logged: 2026-04-21*
