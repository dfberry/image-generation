# Decision: Remotion LLM Prompt Hardening (issue #92)

**By:** Switch (Prompt/LLM Engineer)
**Date:** 2025-07-18
**Status:** Implemented on `squad/92-remotion-llm-prompt`

## Context

The remotion-gen LLM pipeline produces invalid TSX with llama3 8B (the default Ollama model). Three recurring failure modes: bracket mismatches in `interpolate()` calls, missing Remotion imports, and wrong `spring()` signatures.

## Decisions

1. **Strict system prompt over soft guidance.** NEVER/ALWAYS rules at the top of the prompt, exact API signatures, and a raw (unfenced) working example. Small models respond better to rigid structure than conversational instruction.

2. **Lower temperature for local models (0.4 vs 0.7).** Structural correctness > creativity for code generation on <10B models.

3. **Post-generation validation is mandatory.** `validate_tsx_syntax()` checks bracket matching before writing. `ensure_remotion_imports()` fixes missing imports. Defence in depth — don't trust the LLM output.

4. **Retry architecture is stubbed, not wired.** `build_validation_error_context()` and `generate_component(validation_errors=)` exist but the retry loop is the caller's responsibility. This avoids coupling the validation layer to the LLM client.

5. **Minimum model guidance.** GPT-4 class recommended. llama3 8B is marginal even with the improved prompt. Models <7B are not recommended.

## Impact

- `llm_client.py` — new system prompt, temperature change, retry params
- `component_builder.py` — new `validate_tsx_syntax()`, `build_validation_error_context()`, `write_component()`, expanded `_REMOTION_HOOKS` (19 symbols), `ensure_remotion_imports()`
- No breaking changes to existing callers
