# Decision: Morpheus Code Review — Remaining Fixes Complete

**By:** Trinity (Backend Dev)
**Date:** 2026-07-27
**Status:** Implemented
**Branch:** fix/morpheus-review-issues

## Summary

Fixed 27 remaining issues from Morpheus's code review (R4-R5, S4, S6, S10-S15, S19-S20, N1-N4, N6-N13). Combined with prior fixes (R1-R2, S1-S3, S5, S7-S9, S16-S18), all 38 review items are now addressed.

## Key Decisions

1. **Import injection validation (R4):** Post-injection regex validation raises `ValidationError` rather than returning potentially broken code. This catches unusual code structures that confuse the string-replace approach.

2. **React.FC removal (R5):** Chose plain function signatures over adding React import. This aligns with React 18+ conventions and matches what our template files already use.

3. **Security hardening (S15):** Added three new evasion checks to `validate_image_paths`: URL-encoded `file://` (`file%3A%2F%2F`), `data:` URIs, and URL-encoded path traversal (`%2E%2E%2F`). These are case-insensitive.

4. **Version pinning (S6):** Pinned react@18.2.0 and typescript@5.5.4 exact. Chose 5.5.4 as latest stable TS5 at time of writing, consistent with exact pinning on Remotion packages.

5. **Dead fixture removal (S13):** Removed `mock_subprocess_success/failure/not_found` from remotion conftest — no test references them. The real mocking happens at module boundaries in individual test files.

## Verification

- Ruff clean: both projects
- Manim: 162/162 tests pass
- Remotion: 208/209 tests pass (1 skip: Windows symlink)
