### Test Coverage: All Skipped CLI/Integration Tests Activated (2026-07-27)
**By:** Neo (Tester)
**Status:** Implemented

Rewrote and activated 17 previously-skipped tests in `remotion-animation/tests/test_cli.py` (11 tests) and `tests/test_integration.py` (6 tests).

**What changed:**
- Replaced stale `openai.ChatCompletion.create` mock pattern with module-boundary mocking (`remotion_gen.cli.generate_component`, `write_component`, `render_video`).
- Removed all `pytest.skip()` calls from both files.
- Renamed `test_missing_output_uses_default` → `test_missing_output_causes_argparse_error` (matches actual CLI behavior: `--output` is required).

**Convention established:** All remotion-animation tests mock at the import site (`remotion_gen.cli.<fn>`), never at the OpenAI SDK level. This insulates tests from SDK version changes.

**Result:** 208 passed, 1 skipped (Windows symlink privilege — unrelated). Zero skips remain in test_cli.py and test_integration.py.
