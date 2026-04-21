# Decision: Demo flags and SYSTEM_PROMPT cleanup rules

**Date:** 2025-07-17
**Author:** Trinity
**Status:** Implemented

## Context

Manim-generated videos had a stacking bug — sequences of numbers/text were piled on top of each other because the SYSTEM_PROMPT never told the LLM to clean up previous objects. Additionally, we needed personalized demo modes for both animation packages.

## Decisions

### 1. SYSTEM_PROMPT now includes explicit object-cleanup rules
- Rules 8–11 in the manim SYSTEM_PROMPT mandate FadeOut/ReplacementTransform when cycling through items.
- A new few-shot example (Example 4: countdown) demonstrates the correct pattern.

### 2. Both CLIs get a `--demo` flag
- **manim-animation:** `--demo` injects a personalized "Dina Berry" prompt with current datetime into the normal LLM pipeline. `--prompt` becomes optional when `--demo` is set.
- **remotion-animation:** `--demo` bypasses the LLM entirely and writes a pre-built TSX component from `demo_template.py`. This avoids llama3 TSX generation failures.

### 3. Remotion demo uses a static template, not LLM
- More reliable than asking llama3 to generate valid TSX.
- Template lives in `remotion_gen/demo_template.py` and accepts a datetime string parameter.
- `--output` auto-generates a timestamped filename when `--demo` is used without it.

## Files changed
- `manim-animation/manim_gen/config.py` — SYSTEM_PROMPT + FEW_SHOT_EXAMPLES
- `manim-animation/manim_gen/cli.py` — `--demo` flag
- `remotion-animation/remotion_gen/cli.py` — `--demo` flag
- `remotion-animation/remotion_gen/demo_template.py` — new pre-built TSX template
