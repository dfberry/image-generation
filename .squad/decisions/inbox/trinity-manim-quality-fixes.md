# Decision: Manim Code Quality Fixes (S2, S3, S7, S8, S9)

**By:** Trinity (Backend Dev)
**Date:** 2026-07-22
**Status:** Implemented

## Summary

Fixed 5 code quality issues from Morpheus's review in the manim-animation package.

## Changes

1. **S2 — Consolidated forbidden-call lists:** Removed `_BLOCKED_BUILTINS` from `scene_builder.py`. `validate_image_operations()` now references the module-level `FORBIDDEN_CALLS` set directly. This is actually stronger protection (14 blocked names instead of 4) for standalone callers.

2. **S3 — Removed dead "np" config entry:** AST import validation checks `ast.Import.names[].name` (the module name, e.g. `numpy`), not aliases (e.g. `np`). The `"np"` entry in `ALLOWED_IMPORTS` was unreachable dead code.

3. **S7 — Upper-bound version constraints:** `manim>=0.18.0,<0.20.0` and `openai>=1.0.0,<2.0.0`. Prevents silent breakage from major version bumps while allowing patch/minor updates.

4. **S8 — Strengthened test assertions:** Error-path tests in `test_cli.py` now use `capsys` to verify stderr contains the expected error class label and message text, not just exit codes.

5. **S9 — Fixed mock subprocess fixtures:** `conftest.py` subprocess fixtures now accept `monkeypatch` and apply `monkeypatch.setattr(subprocess, "run", ...)` inside the fixture body. Previously they returned bare functions that were never applied.

## Verification

- ruff: clean (0 new issues)
- pytest: 149/149 passed (1.95s)
- Commit: `c5289bf`
