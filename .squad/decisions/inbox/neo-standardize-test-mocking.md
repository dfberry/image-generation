# Decision: Standardized Test Mocking Pattern for generate.py

**Owner:** Neo (Tester)
**Status:** Implemented
**Impact:** All 15 test files now use a consistent mocking approach; 263/264 tests pass on CPU-only machines

## Context

The test suite had two incompatible mocking strategies for `_ensure_heavy_imports()`. Five files used a manual `_patch_heavy()` context manager; eight files had no patching at all. Two files imported `torch` at module level. This caused 57 test failures and 2 collection errors on any machine without GPU/torch.

## Decision

Added a single **autouse fixture** (`_patch_heavy_imports`) in `conftest.py` that:

1. Injects mock `torch`, `diffusers`, and `DiffusionPipeline` into `generate.__dict__` (bypasses PEP 562 `__getattr__`)
2. Replaces `_ensure_heavy_imports()` with a no-op
3. Makes `torch.cuda.OutOfMemoryError` a real exception subclass (for `isinstance()` compatibility)
4. Restores all originals in teardown

Individual tests can still layer `@patch("generate.torch")` or `patch("generate.torch.cuda.empty_cache")` on top.

## Rule for Future Tests

- **Never** `import torch` at module level in any test file
- **Never** call `generate()`, `batch_generate()`, `load_base()`, etc. without the conftest autouse fixture active (it's automatic)
- If you need a specific torch constant (e.g. `float16`), use a sentinel value or `gen.torch.float16` from the mock
- If patching `diffusers.SomeScheduler`, use `patch.object(gen.diffusers, "SomeScheduler", ...)` not `patch("diffusers.SomeScheduler")`
