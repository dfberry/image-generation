# Decision: LLM Exception Tagging Convention

**By:** Trinity (Backend Dev)
**Date:** 2026-07-22
**Status:** Implemented

## Convention

Both `manim_gen/llm_client.py` and `remotion_gen/llm_client.py` now tag LLMError
messages with bracket-prefixed error classes:

- `[auth]` — `AuthenticationError` (non-retryable)
- `[rate_limit]` — `RateLimitError` (retryable)
- `[connection]` — `APIConnectionError` (retryable)
- No prefix — generic/unknown failures

Callers can do `if "[rate_limit]" in str(e):` to decide retry behavior.

## Why

The generic `except Exception` was masking whether failures were credential issues
(should abort) vs transient network/rate issues (should retry). Preserving exception
type info in the error message is the minimal change that enables smart retry logic
without breaking the existing LLMError contract.
