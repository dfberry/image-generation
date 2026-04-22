# Decision: Animation Projects Code Review — Priority Fixes

**By:** Morpheus (Lead)  
**Date:** 2026-07-27  
**Status:** Action required

## Context

Deep code review of both `manim-animation/` and `remotion-animation/` following layout fixes. Reviewed all source, tests, configs, and TypeScript. Found 38 issues.

## Priority 0 — Must Fix Before Next Feature Work

1. **Remove unused pydantic dependency** from `remotion-animation/pyproject.toml` and `requirements.txt` — dead weight, never imported
2. **Un-skip 48 remotion tests** — tests say "Waiting for Trinity's implementation" but the modules are fully implemented. These tests need to be activated and wired up.
3. **Fix eager OpenAI import** in `remotion-animation/remotion_gen/llm_client.py` — should be lazy like manim's, or the module crashes on import without openai installed
4. **Fix component_builder.py import injection** (lines 243-258) — the three-fallback replace chain can silently produce code with missing imports. Needs validation that replacement actually succeeded.

## Priority 1 — Should Fix This Sprint

5. **Align QualityPreset patterns** — manim uses Enum, remotion uses dataclass. Both work but the inconsistency is confusing for contributors working across both packages.
6. **Add `engines` field** to `remotion-project/package.json` — README says Node 18+ but nothing enforces it
7. **Generic exception masking** in both `llm_client.py` files — catch specific OpenAI exceptions, not bare `Exception`
8. **Missing React import** in `Root.tsx` — uses `React.FC` type without importing React

## Decision

Trinity should own P0 items 1-4. Neo should own un-skipping tests (item 2). Follow TDD workflow per team decisions.
