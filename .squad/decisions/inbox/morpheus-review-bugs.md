# Decision: Code Review — PRs #94, #95, #98 (Bug Fix Batch)

**By:** Morpheus (Lead)
**Date:** 2025-07-26
**Status:** Review complete

---

## PR #94 — Fix #90: Manim media directory detection
**Branch:** `squad/90-manim-media-dir`
**Verdict:** ✅ APPROVE

**What it does:** When `assets_dir` is provided (which becomes Manim's CWD), the renderer now looks for `media/` output relative to `assets_dir` instead of `scene_file.parent`. Falls back to `scene_file.parent` when no `assets_dir` is given.

**Review findings:**
- Logic is correct: `base_dir = Path(assets_dir) if assets_dir else scene_file.parent` handles both cases cleanly.
- Both the primary path lookup (quality-specific directory) and the fallback `rglob` search use `base_dir` consistently.
- All three quality presets (LOW/MEDIUM/HIGH) work because the quality→directory mapping (`480p15`/`720p30`/`1080p60`) is unchanged — only the base path changed.
- Three new tests: assets_dir provided, no assets_dir (regression), fallback rglob with assets_dir. Good coverage of the fix and the edge case.
- Clean, minimal diff — changes only what's needed.

**No issues found.**

---

## PR #95 — Fix #91: Remotion version pins + issue #92 LLM hardening
**Branch:** `squad/91-remotion-version-pins`
**Verdict:** ❌ CHANGES REQUESTED

### Issue 1 — CRITICAL: `validate_image_paths` function definition destroyed

The `def validate_image_paths(...)` line was deleted during the insertion of new code. Its body (docstring + regex checks + security validation) is now orphaned as unreachable dead code inside the first `write_component` function, after its `return` statement.

The second `write_component` (which Python uses, since it's defined last) calls `validate_image_paths(code, image_filename)` — but that function no longer exists at module scope. This will cause a `NameError` at runtime whenever a user passes an image.

**Impact:** Image path security validation is broken. Any image filename passes through unchecked.

### Issue 2 — CRITICAL: `write_component` defined twice, new logic is dead

`write_component` appears twice in the file. Python uses the last definition, which is the OLD version. The NEW version (with `ensure_remotion_imports()` + `validate_tsx_syntax()` calls) is overwritten and never executes.

All the new validation pipeline code — TSX syntax checking, import fixup, retry-ready error context — is effectively dead code that will never run through the `write_component` entry point.

### Issue 3 — No tests for new functions

`validate_tsx_syntax()`, `ensure_remotion_imports()`, `build_validation_error_context()` have zero test coverage. The test directory diff is empty.

### Issue 4 — Scope creep: Two issues in one PR

This PR merges issue #91 (version pins) and issue #92 (LLM prompt hardening) into a single branch. These should be separate PRs:
- The package.json version pins are correct and ready to merge independently.
- The component_builder + llm_client changes need the structural bugs fixed first.

### What's correct

- **package.json version pins are good.** All three direct `@remotion/*` deps pinned to `4.0.450`. Overrides block covers 8 transitive packages. All consistent.
- **llm_client.py changes are sound.** Temperature reduction for Ollama (0.7→0.4), retry params, validation error re-prompting — all well-structured.
- **New functions are well-designed in isolation.** `validate_tsx_syntax`, `ensure_remotion_imports`, and `build_validation_error_context` are good code — they just need to actually be wired in correctly.

### Required fixes

1. Restore `def validate_image_paths(code: str, allowed_image_filename: str) -> None:` as a standalone function at module scope.
2. Remove the duplicate `write_component`. Keep ONE definition that includes both the new validation pipeline AND the existing image path validation.
3. Add tests for `validate_tsx_syntax`, `ensure_remotion_imports`, and `build_validation_error_context`.
4. Consider splitting the version pins commit into its own PR so it can merge independently.

---

## PR #98 — Fix #93: Root.tsx uses getInputProps()
**Branch:** `squad/93-root-tsx-props`
**Verdict:** ✅ APPROVE

**What it does:** Replaces hardcoded composition values in Root.tsx with dynamic values from `getInputProps()`, and fixes renderer.py to pass all composition properties as structured JSON.

**Review findings — Root.tsx:**
- Correctly imports `getInputProps` from `'remotion'`.
- Calls `getInputProps()` at module scope (correct for Remotion — this runs once at bundle time).
- Uses nullish coalescing (`??`) with sensible defaults that match the previous hardcoded values: 150 frames, 30fps, 1280×720.
- Optional chaining (`inputProps?.`) guards against undefined props during development/preview.

**Review findings — renderer.py:**
- Replaces the fragile string concatenation (`'--props={' + '"durationInFrames":' + str(...)`) with `json.dumps()`. Much safer — handles escaping, no risk of malformed JSON.
- Props JSON now includes all four composition values: `durationInFrames`, `fps`, `width`, `height`.
- CLI still passes `--width`, `--height`, `--fps` as separate flags. This is correct — Remotion CLI flags control the rendering pipeline, while `--props` controls what `getInputProps()` returns to components. Both should agree.

**Review findings — tests:**
- Two solid tests: verifies props JSON structure for medium quality (1280×720/30fps) and high quality (1920×1080/60fps).
- Tests parse the actual `--props` argument from the subprocess command and validate each field.
- Good coverage of the round-trip: Python dict → json.dumps → CLI arg → parsed JSON.

**No issues found.**
