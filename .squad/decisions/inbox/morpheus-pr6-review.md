# PR #6 Review — PIL Leak Fix + Test Assert Fixes

**Date:** 2026-03-25
**Reviewer:** Morpheus
**Branch:** squad/pr6-pil-leak-fix
**Requested by:** dfberry

---

## Change 1 — Trinity's PIL Leak Fix (`generate.py`, commit f3fbf95)

### What Changed
- `image.save(output_path)` + print moved inside the `try` block, guarded by `if image is not None:`
- `image = None` added to `finally` after the `del base, refiner, latents, text_encoder_2, vae` line
- `return output_path` remains post-`finally` (unchanged)

### Review

**1. Happy path correctness:**
`image` is always assigned by either `refiner(...).images[0]` or `base(...).images[0]` before the guard check. `if image is not None:` evaluates True. `image.save(output_path)` runs correctly. ✅

**2. Edge case — image is None:**
`image` is initialized to `None` in the multi-assignment before `try`. If `load_base` or inference raises an exception, `image` stays `None`. The guard correctly prevents calling `save()` on `None`, and the exception propagates after `finally`. The guard is defensively correct — not strictly necessary (the exception path already skips save), but harmless and good hygiene. ✅

**3. `return output_path` post-`finally`:**
`output_path` is assigned before the `try` block. Post-`finally`, if no exception was raised, execution reaches `return output_path` normally. If an exception was raised, it propagates out of `finally` and `return` is unreachable. Behavior is correct and unchanged. ✅

**4. Unintended side effects:**
None. `image = None` in `finally` releases the PIL buffer reference after save is complete, which is exactly the intended fix for the LOW-severity PIL leak identified in the memory audit.

### Verdict: ✅ APPROVED

---

## Change 2 — Neo's Test Assertion Fixes (`tests/test_memory_cleanup.py`, commit 5f68310)

### What Changed
Three tests changed from:
```python
mock_something.assert_called(), "message string"
```
to:
```python
assert mock_something.called, "message string"
```

The three affected tests:
- `test_gc_collect_called_at_entry_cuda` — message: `"gc.collect() should fire before load_base on CUDA"`
- `test_cuda_cache_flush_at_entry` — message: `"torch.cuda.empty_cache() should fire before load_base"`
- `test_mps_cache_flush_at_entry` — message: `"torch.mps.empty_cache() should fire before load_base"`

### Review

**1. Semantic correctness:**
`mock.assert_called(), "msg"` evaluates as a tuple expression `(None, "msg")`. It is always truthy. It is NOT an assertion — the comma detaches the message from any assert context, and `mock.assert_called()` is called as a standalone expression whose return value is discarded. The test appeared to pass regardless of whether the mock was actually called.

`assert mock.called, "msg"` is a proper Python assertion. `mock.called` is a boolean property. If False, `AssertionError` is raised with the message. This is the correct fix. ✅

**2. Message strings:**
All three messages accurately describe the expected behavior being tested (cache flushing and gc before `load_base()`). Clear, actionable, accurate. ✅

**3. Test file completeness:**
Neo's commit also:
- Adds `tests/test_memory_cleanup.py` (460 lines, new file — was absent from main despite being documented as merged in PR5)
- Adds `tests/conftest.py` (112 lines, fixtures for the test suite)
- Restores PR5 MEDIUM code fixes to `generate.py` (entry-point flush, latents CPU transfer, dynamo cache reset) — these were documented as merged but missing from the codebase

**Scope note:** This commit does more than "fix assert messages" — it also restores missing code changes and test infrastructure. However, all restored items were previously reviewed and approved (PR5). The code changes and tests are tightly coupled; without the code fixes, several tests would fail. Neo correctly called this out in the commit message. The inclusion is justified and transparent. ✅

**All 22 tests pass.** ✅

### Verdict: ✅ APPROVED

---

## Summary

| Change | Owner | Verdict |
|--------|-------|---------|
| PIL leak fix in generate.py | Trinity | ✅ APPROVED |
| Test assert fixes + file restoration | Neo | ✅ APPROVED |

**PR #6 is clear to merge.**

**Note for scribe:** The PR5 MEDIUM code fixes (entry-point flush, latents CPU transfer, dynamo reset) were restored in this PR. The main branch should reflect all of these after merge. Confirm the final state of main post-merge matches the expected architecture.
