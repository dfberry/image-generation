# Squad Decisions

## Active Decisions

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
