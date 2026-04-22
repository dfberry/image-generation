# Decision: Activate Remaining Skipped Remotion Tests

**By:** Neo (Tester)  
**Date:** 2026-07-24  
**Status:** Recommendation

## Context

During the test coverage audit, I found 49 skipped tests in remotion-animation — many tagged "Waiting for Trinity's implementation" even though Trinity's code has been implemented for weeks. I activated 31 of them. 18 remain skipped.

## Recommendation

The remaining 18 skipped tests (`test_cli.py` 11 tests, `test_integration.py` 6 tests, `test_image_handler.py` 1 symlink test) should be activated in a follow-up. The CLI and integration tests use stale `openai.ChatCompletion.create` mock patterns that don't match the actual implementation (which uses `OpenAI().chat.completions.create`). 

**Action needed:** Rewrite these 18 tests to mock at the `remotion_gen.llm_client._call_llm` and `remotion_gen.llm_client._create_client` boundaries instead of patching the OpenAI SDK directly. This mirrors how I rewrote `test_llm_client.py` successfully.

## Pattern for Future Tests

Mock at the **module boundary**, not the third-party SDK:
- ✅ `@patch("remotion_gen.llm_client._call_llm")`
- ❌ `@patch("openai.ChatCompletion.create")`

This makes tests resilient to SDK version changes and focuses on testing our code, not OpenAI's.
