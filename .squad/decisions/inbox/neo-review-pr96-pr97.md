# Decision: Code Review — PR #96 and PR #97

**By:** Neo (Tester)
**Date:** 2025-07-25
**Status:** Review complete

---

## PR #96 — Fix #92: Harden LLM prompt and add TSX validation

**Branch:** `squad/92-remotion-llm-prompt`
**Verdict:** ❌ CHANGES REQUESTED

### Critical Issues

#### 1. `validate_image_paths` function destroyed (BLOCKER)

The diff replaced the `def validate_image_paths(...)` line at the insertion point for the new code, but left the function body (docstring + implementation, lines 336-373) orphaned **inside** the first `write_component` function, after `return component_path`. This is dead code that will never execute.

**Consequence:** `validate_image_paths()` no longer exists as a callable function. Any call to it (e.g., line 455 in the second `write_component`) will raise `NameError` at runtime when `image_filename` is provided. This breaks image-based generation entirely.

#### 2. Duplicate `write_component` definitions (BLOCKER)

The file now contains TWO `def write_component(...)` — one at line 284 (new, with `ensure_remotion_imports` + `validate_tsx_syntax`) and one at line 433 (old, without them). Python uses the **last** definition, so the old `write_component` wins. All new validation features are dead code.

- Line 284: New `write_component` → calls `ensure_remotion_imports()`, `validate_tsx_syntax()` ← never used
- Line 433: Old `write_component` → calls `validate_image_paths()` (which doesn't exist) ← this is what Python uses

#### 3. SYSTEM_PROMPT not actually changed (MAJOR)

Switch's history and the decision doc claim a comprehensive prompt rewrite with "9 NEVER/ALWAYS rules," strict API signatures, and a raw (unfenced) working example. But the actual `SYSTEM_PROMPT` in `llm_client.py` is **identical to main**. It still contains the old soft-guidance prompt with markdown-fenced example (`\`\`\`tsx`).

The only user-prompt change was one line: `"Remember: Return ONLY the TSX code..."` → `"Return ONLY raw TSX code. No markdown fences..."` — a minor wording tweak, not the fundamental rewrite described.

### Minor Issues

#### 4. `max_retries` parameter is declared but never used

`generate_component(max_retries=...)` is accepted as a parameter and documented, but no retry loop exists. The parameter is silently ignored. Either implement the loop or remove the parameter — a no-op parameter is a footgun for callers who think retries are happening.

#### 5. No tests for new functions

Neither PR includes tests for:
- `validate_tsx_syntax()` with actual mismatched brackets
- `ensure_remotion_imports()` with missing hooks
- `build_validation_error_context()` output format
- The modified `write_component` calling the validation pipeline

### What's Correct

- Temperature reduction (0.7 → 0.4 for Ollama) — landed properly
- `validation_errors` param and user-prompt error injection — clean implementation
- `validate_tsx_syntax()` function logic — bracket matching, string/comment stripping, JSX tag counting are all well-written (just unreachable)
- `ensure_remotion_imports()` — good 3-tier fallback (append to existing single-quote import → double-quote import → prepend new import line)
- `build_validation_error_context()` — clean retry prompt builder
- `_REMOTION_HOOKS` list with 19 symbols — comprehensive

### Required Actions

1. **Fix the merge damage:** Remove the second (old) `write_component`. Restore `validate_image_paths` as a standalone function before the new `write_component`.
2. **Actually rewrite SYSTEM_PROMPT** or update the decision doc to match what was shipped.
3. **Remove `max_retries`** or wire it to a real retry loop.
4. **Add tests** for `validate_tsx_syntax`, `ensure_remotion_imports`, and `build_validation_error_context`.

---

## PR #97 — Anticipatory tests for #90-#93

**Branch:** `squad/90-93-tests`
**Verdict:** ✅ APPROVE (with notes)

### Strengths

**Test design is solid.** 23 automated tests + 1 manual spec across 4 files. Tests are written at the contract boundary (mock subprocess.run, shutil.move, shutil.which) — correct approach for anticipatory tests.

#### Manim #90 — Media directory detection (7 tests)
- ✅ Parametrized across all 3 quality presets (480p15/720p30/1080p60)
- ✅ Tests output copy to caller-specified path
- ✅ Fallback rglob when primary path missing
- ✅ Error case: media directory never created
- ✅ Error case: media exists but no video file
- Would catch regression if fix were reverted.

#### Remotion renderer #91 — UTF-8 and warnings (9 tests)
- ✅ UTF-8 stdout/stderr with emojis and accented characters
- ✅ Version mismatch warnings on stderr don't fail (returncode=0)
- ✅ Actual errors still raise RenderError (returncode=1)
- ✅ Output file missing after success → RenderError
- ✅ check_prerequisites() — node missing, npm missing, all found
- Would catch regression if fix were reverted.

#### Remotion component #92 — Import injection (8 tests)
- ✅ inject_image_imports adds Img/staticFile/imageSrc
- ✅ No duplicate imports when already present
- ✅ validate_component on valid balanced JSX
- ✅ Missing remotion import still caught
- ✅ Missing return statement still caught
- ✅ Nested JSX passes validation
- Tests validate_component (existing) — correct for anticipatory tests

#### Root.tsx #93 — Manual spec (5 cases)
- ✅ Correctly identified as TypeScript-only (not testable via pytest)
- ✅ 5 well-defined manual test cases with clear expected results
- ✅ Includes ffprobe verification step for dimension checks

### Notes (non-blocking)

1. **Merge conflict risk:** PR #97 and PR #96 modify identical test files with identical content. Whichever merges second will get a clean conflict. Coordinate merge order (PR #97 first, then PR #96 adds implementation on top).

2. **Test count discrepancy:** History says "23 tests" but I count: 7 (manim) + 3 (prerequisites) + 3 (UTF-8) + 3 (version mismatch) + 2 (command construction) + 4 (import injection) + 4 (bracket validation) = 26 automated tests. The 23 count may exclude the 3 prerequisite tests. Minor.

3. **Gap: No direct test for `validate_tsx_syntax()` with broken brackets.** The TestBracketParenValidation class tests `validate_component()` (existing function), not the new `validate_tsx_syntax()` from PR #96. This is correct for anticipatory tests but should be supplemented once PR #96 is fixed.

4. **Mock spec:** Mocks use `MagicMock(returncode=0, stdout="", stderr="")` without `spec=subprocess.CompletedProcess`. Adding `spec=` would catch attribute typos but isn't blocking since the mock attributes match the real interface.
