# Squad Decisions

## Active Decisions

### Documentation: Comprehensive Package Documentation (2026-04-22)
**By:** Trinity (Backend Dev)  
**Status:** Implemented

Created 5-file documentation suites for all 4 packages:
- **image-generation:** architecture, development, testing, installation, user-guide
- **manim-animation:** architecture, development, testing, installation, user-guide
- **mermaid-diagrams:** architecture, development, testing, installation, user-guide
- **remotion-animation:** architecture, development, testing, installation, user-guide

All docs sourced from actual codebase, cross-referenced against existing README/design docs to avoid contradictions. Follows established convention: docs live in central `docs/{package-name}/` with consistent 5-file structure.

**Impact:** All team members can onboard to packages without reading source. New contributors have clear extension guides and mock patterns.

---

### Test Coverage: All Skipped CLI/Integration Tests Activated (2026-04-22)
**By:** Neo (Tester)  
**Status:** Implemented

Rewrote and activated 17 previously-skipped tests in `remotion-animation/tests/test_cli.py` (11 tests) and `tests/test_integration.py` (6 tests). Replaced stale `openai.ChatCompletion.create` mock pattern with module-boundary mocking. Removed all `pytest.skip()` calls from both files. Renamed `test_missing_output_uses_default` → `test_missing_output_causes_argparse_error` to match actual CLI behavior.

**Convention:** All remotion-animation tests mock at the import site (`remotion_gen.cli.<fn>`), never at the OpenAI SDK level. Insulates tests from SDK version changes.

**Result:** 208 passed, 1 skipped (Windows symlink privilege — unrelated). Zero skips remain in test_cli.py and test_integration.py.

---

## Archived Decisions

### Code Review: Animation Projects — Priority Fixes (2026-07-27)
**By:** Morpheus (Lead)  
**Status:** Action required

Deep code review of both manim-animation/ and emotion-animation/. Found 38 issues (5 red, 20 yellow, 13 green).

**Priority 0 — Must Fix Before Next Feature Work**
1. Remove unused pydantic dependency from emotion-animation/pyproject.toml and equirements.txt
2. Un-skip 48 remotion tests — fully implemented, just need activation
3. Fix eager OpenAI import in emotion-animation/remotion_gen/llm_client.py — should be lazy
4. Fix component_builder.py import injection (lines 243-258) — validate replacement succeeded

**Priority 1 — Should Fix This Sprint**
5. Align QualityPreset patterns (manim Enum vs remotion dataclass)
6. Add `engines` field to emotion-project/package.json — enforce Node 18+
7. Catch specific OpenAI exceptions, not bare Exception
8. Add missing React import in Root.tsx

**Decision:** Trinity owns P0 items 1-4. Neo owns test un-skipping (item 2).

---

### Test Coverage: Activate Remaining Skipped Remotion Tests (2026-07-24)
**By:** Neo (Tester)  
**Status:** Recommendation

Activated 31 skipped tests. 18 remain with stale mock patterns.

**Recommendation:** Rewrite remaining 18 tests to mock at module boundaries instead of OpenAI SDK. This ensures tests are resilient to SDK version changes and focus on testing our code.

---

### Implementation: Manim Code Quality Fixes (2026-07-22)
**By:** Trinity (Backend Dev)  
**Status:** Implemented

Fixed 5 code quality issues: consolidated forbidden-call lists (S2), removed dead np alias (S3), added version ceilings (S7), strengthened test assertions (S8), fixed mock fixtures (S9).

**Verification:** Ruff clean, 149/149 tests pass.

---

### Convention: LLM Exception Tagging (2026-07-22)
**By:** Trinity (Backend Dev)  
**Status:** Implemented

Both manim_gen/llm_client.py and remotion_gen/llm_client.py now tag LLMError messages with bracket-prefixed error classes: [auth] for non-retryable auth errors, [rate_limit] for retryable rate limit errors, [connection] for API connection errors. Callers can check error message prefixes to decide retry behavior.

---
