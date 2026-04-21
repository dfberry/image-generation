# Switch Review — PR #99: Manim Stacking Fix + Demo Prompts

**Date:** 2025-07-17
**PR:** #99 (`squad/94-demo-prompt-stacking-fix`)
**Reviewer:** Switch (Prompt/LLM Engineer)
**Verdict:** ✅ APPROVE — with minor suggestions (non-blocking)

---

## Review Summary

### 1. SYSTEM_PROMPT Rules 8–9 (Anti-Stacking) — ✅ Strong

Rules 8 and 9 are well-crafted for llama3 instruction-following:

- **Rule 8** is general (covers all sequence types) and uses ALWAYS/NEVER emphasis — LLMs respond well to caps-lock imperatives in system prompts.
- **Rule 9** is specific (countdowns/numbers) and prescribes the exact pattern: new object → FadeOut old → FadeIn new. This general-then-specific layering is the right approach for smaller models like llama3.
- Mentioning both `FadeOut()` and `ReplacementTransform()` in Rule 8 is smart — gives the LLM two valid tools, preventing it from ignoring the rule because it "wanted" to use a different API.

**Minor nit (non-blocking):** Rule 9 says "FadeOut the old one, **then** FadeIn the new one" — which implies sequential. The few-shot example correctly does `self.play(FadeOut(prev), FadeIn(num))` (simultaneous). Consider rewording to "FadeOut the old one **and** FadeIn the new one in the same self.play() call" to match the example exactly. Llama3 may follow the example over the text, but consistency between prose and code reduces ambiguity.

### 2. Few-Shot Example 4 (Countdown) — ✅ Correct

The countdown example is syntactically valid Manim CE and teaches exactly the right pattern:

- `prev = None` tracker → first-item special case → FadeOut+FadeIn pair → final cleanup FadeOut
- This is the canonical anti-stacking loop. LLMs learn loop patterns well from few-shot.
- The `self.wait(0.5)` at the end is good — prevents abrupt scene termination.
- Using `Text(str(i), font_size=96)` keeps it simple. Good choice over MathTex for a counting example.

### 3. Manim --demo Prompt — ✅ Well-Structured

The auto-generated demo prompt is effective:

- Uses explicit Manim terminology (FadeIn, FadeOut) which aligns with system prompt vocabulary
- Has a clear temporal sequence: dark bg → name → datetime → wait → FadeOut → outro
- Reinforces anti-stacking at the end ("never stack text on top of existing text")
- The datetime injection (`{now}`) produces natural-language timestamps that LLMs handle well

**Note:** Unlike the remotion demo, this still passes through llama3. The prompt quality is high enough that it should work, but it's inherently less deterministic than a template. This is an acceptable tradeoff — manim code generation is the core feature being tested.

### 4. Remotion Demo TSX Template — ✅ Polished

The hardcoded TSX template is a smart design choice — bypassing the LLM entirely for demos ensures reliability.

The animation is well-composed:
- Spring entrance for the name (professional feel)
- Staggered timestamp fade+slide (visual hierarchy)
- 3s hold → crossfade to outro (clean timing)
- Gradient background (#0f0c29 → #302b63 → #24243e) is tasteful dark purple

**Two minor issues (non-blocking):**

1. **Unused import:** `Sequence` is imported but never used in the template. Won't break anything but is dead code.
2. **Python indentation:** The docstring's first line uses 3-space indent while the body uses 4-space. Cosmetic only — Python parses it fine.

---

## Overall Assessment

This PR effectively addresses the object-stacking problem through three complementary layers: system prompt rules, few-shot demonstration, and demo mode for reliable testing. The prompt engineering is sound and follows established patterns for instructing smaller LLMs. Approve as-is; suggestions are polish items.
