# Decisions Log

## Current Decisions

### Morpheus Review: PR #5 — MEDIUM Memory Fixes

**Date:** 2026-03-25
**Reviewer:** Morpheus (Lead)
**Branch:** `squad/pr5-medium-memory-fixes`
**Verdict:** ✅ APPROVED — merge when ready

---

## PR #9: TDD Green Phase — OOMError + batch_generate() Implementation

**Date:** 2026-03-25
**Author:** Trinity (Backend Dev) with Morpheus code review
**Branch:** `squad/tdd-batch-oom-tests`
**Verdict:** ✅ **APPROVE — Merge to main**

### OOMError Implementation

```python
class OOMError(RuntimeError):
    """Raised when GPU/MPS runs out of memory during generation."""
    pass
```

Placed before `parse_args()`, importable from generate module.

**Detection logic in generate():**
- CUDA OOM: Catches `torch.cuda.OutOfMemoryError` (torch >= 2.1, guarded by hasattr)
- MPS OOM: Catches `RuntimeError` with "out of memory" in message (case-insensitive)
- Message: "Out of GPU memory. Reduce steps with --steps or switch to CPU with --cpu." (mentions both options)
- Re-raises as OOMError, but finally block still executes unconditionally (Python semantics)

**Review checklist (6/6 OOMError criteria):**
| # | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 1 | Subclasses RuntimeError | ✅ PASS | Proper exception hierarchy |
| 2 | Detects CUDA OOM | ✅ PASS | torch.cuda.OutOfMemoryError with hasattr guard |
| 3 | Detects MPS OOM | ✅ PASS | RuntimeError + "out of memory" string match |
| 4 | finally executes after OOM | ✅ PASS | Lines 208-222 guaranteed by Python |
| 5 | Error message actionable | ✅ PASS | Mentions both --steps AND --cpu |
| 6 | Non-OOM exceptions propagate | ✅ PASS | bare `raise` re-raises non-OOM exceptions |

### batch_generate() Implementation

```python
def batch_generate(prompts: list[dict], device: str = "mps") -> list[dict]:
```

**Behavioral contract (7/7 criteria):**
| # | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 1 | Calls generate() per item | ✅ PASS | Loop lines 235-248 |
| 2 | Memory flush between items | ✅ PASS | gc + cache clears if i < len-1 |
| 3 | Per-item errors handled | ✅ PASS | try/except per item, appends error dict |
| 4 | Empty list returns [] | ✅ PASS | No iterations, no generate() or gc calls |
| 5 | Result order preserved | ✅ PASS | Iterates and appends in order |
| 6 | Never raises | ✅ PASS | All exceptions → error dicts |
| 7 | Signature clean | ✅ PASS | Matches spec exactly |

**Implementation details:**
- Per-item flush: `gc.collect()`, `torch.cuda.empty_cache()`, conditional `torch.mps.empty_cache()`
- Flush guard: `if i < len(prompts) - 1` (between items, not after last — avoids redundant cleanup after generate's final flush)
- Error handling: Exception caught, converted to error dict with original prompt, output flag, error message
- Seed handling: `item.get("seed")` for optional seed
- Device parameter: Converted to cpu flag for generate() call
- Consistent with existing patterns: Uses SimpleNamespace (matching args), cache clearing follows guard pattern

### Integration Verification (3/3 criteria)

| # | Criterion | Status | Notes |
|----|-----------|--------|-------|
| 8 | Existing try/finally cleanup functional | ✅ PASS | All code intact, fully functional |
| 9 | OOM except doesn't interfere | ✅ PASS | Re-raised as RuntimeError subclass, finally executes |
| 10 | Code readable and maintainable | ✅ PASS | Inline comments, clear logic, good variable names |

### Test Results

**All 53 tests passing (2.67s runtime):**
- 22 regression tests (test_memory_cleanup.py) — validates PR #1–#6 fixes
- 17 batch_generate() tests (test_batch_generation.py) — validates batch semantics
- 14 OOMError tests (test_oom_handling.py) — validates exception handling

**Batch generation coverage (17 tests):**
- Per-item generate() invocation (3 tests)
- Inter-item GPU flushing (3 tests) with call-order verification
- Partial failure handling (3 tests)
- Empty batch edge case (2 tests)
- Result ordering and structure (4 tests)
- All-item failure (2 tests)

**OOM handling coverage (14 tests):**
- CUDA OOM detection and re-raise (3 tests)
- MPS OOM detection and re-raise (3 tests)
- finally block cleanup runs after OOM (6 tests)
- OOM message content (3 tests)
- State clean after OOM (2 tests)

### Code Quality Assessment

**Strengths:**
1. Exception safety guaranteed — finally block unconditional on success, OOM, interrupt, or any exception
2. OOMError properly designed — dual detection, version-safe guards, actionable message
3. batch_generate() contract clean — per-item isolation, inter-item flushing, graceful failure, order preserved
4. Error messages user-friendly — both --steps and --cpu mentioned
5. No functional bugs found
6. Code maintainable and tested
7. Consistent with established patterns

**Minor observations (non-blocking):**
1. MPS cache clear could be device-guarded for optimization, but safe no-op on non-MPS (negligible impact)
2. torch.cuda.empty_cache() called unconditionally on all devices (safe no-op, consistent with existing pattern)

### Decisions Made

1. **OOM detection is message-based for MPS** — MPS raises plain RuntimeError. String matching on "out of memory" (case-insensitive) is the only reliable cross-torch-version approach.

2. **Memory flush only between items, not after last** — Matches test contract exactly. Avoids redundant cleanup since generate() already flushes in its own finally block.

3. **batch_generate stays in generate.py** — Test imports from `generate`. No separate batch.py needed.

4. **except + finally coexist** — Python allows both in one try block. except re-raises OOMError, finally still cleans up. Correct pattern for "transform exception but guarantee cleanup."

### Production Readiness

✅ Both OOMError and batch_generate() are production-ready:
- Fully tested (31 new tests + 22 regression tests, all passing)
- Exception-safe (finally block unconditional)
- Error messages actionable
- Edge cases covered (empty batch, partial failure, all-fail, state clean after OOM)
- No VRAM leaks
- Ready for production batch workflows

---

## Fix-by-Fix Findings

### Fix 1: Latents CPU Transfer (MEDIUM)

**Status: CORRECT**

- `latents = latents.cpu()` is placed **before** `del base` and the cache flush. Order is correct — the GPU pin is released before `empty_cache()` runs.
- Device transfer back uses `latents.to(device)` inline at the refiner call site, not hardcoded `"cuda"`. MPS is respected.
- The `if device in ("cuda", "mps")` guard is clean — CPU path is untouched.
- One note: `latents.to(device)` is called inline and its result passed directly to the refiner. The `latents` variable continues to hold the CPU copy until `finally` cleans it up. This is benign — CPU tensors carry negligible VRAM impact.

### Fix 2: Dynamo Cache Reset (MEDIUM)

**Status: CORRECT**

- `torch._dynamo.reset()` is inside the `finally` block. ✅
- Guarded by `device == "cuda" and hasattr(torch, "_dynamo")`. Both guards are present and necessary.
  - `device == "cuda"` is correct: `torch.compile` is only applied on CUDA in `load_base()` (confirmed at line 72–75).
  - `hasattr(torch, "_dynamo")` protects against torch versions without the attribute.
- The comment correctly flags that if `torch.compile` is ever extended to MPS, the guard must be broadened.

### Fix 3: Entry-Point VRAM Flush (MEDIUM)

**Status: CORRECT**

- All three calls present: `gc.collect()`, `torch.cuda.empty_cache()` (CUDA-guarded), `torch.mps.empty_cache()` (MPS-guarded).
- Located at the very start of `generate()`, before `load_base()` is called. Order confirmed in diff and test call-log tracking.
- Two-flush pattern (entry + finally) is intentional and correct. Entry reclaims fragmented VRAM from prior runs; finally unconditionally cleans up after this run.

### Fix 4: Global State Audit (MEDIUM — no code change)

**Status: CLEAN — agree with audit**

Scanned `generate.py` manually. All pipeline variables (`base`, `refiner`, `latents`, `text_encoder_2`, `vae`) are locals initialized inside `generate()`, not module-level. Zero process-persistent pipeline references. Clean architecture for a CLI tool called in batch.

---

## Test Review (9 new MEDIUM tests)

**All 22 tests pass (verified by running `PYTHONPATH=. pytest tests/test_memory_cleanup.py`).**

### Ordering / call-log tracking

- `TestEntryPointVRAMFlush`: All 3 tests use `call_log` + `side_effect` to verify the flush fires **before** `load_base`. Genuine regression guards. ✅
- `TestLatentsTensorHandling.test_latents_not_holding_gpu_ref_during_cache_flush`: Uses `call_log` to verify `latents.cpu()` precedes `mps.empty_cache()`. ✅
- `TestLatentsTensorHandling.test_latents_transferred_back_for_refiner`: Checks that `cpu()` and `to("mps")` are both called, but does NOT verify order. If someone swapped them, this test would still pass. Minor gap — not a blocker.
- `TestDynamoCacheReset`: CUDA test mocks the full `torch` module, correctly exercises the `hasattr` guard. CPU test correctly confirms `_dynamo.reset()` is NOT called on non-CUDA paths. ✅
- `TestGlobalState.test_repeated_calls_dont_compound_memory`: Tracks cumulative gc count across two `generate()` calls — verifies entry flush fires on the second call too. ✅

### Code smell: orphaned assert messages

Several tests use this pattern:
```python
mock.assert_called(), "this message is never shown"
```
The string after the comma is a valid Python expression but is silently orphaned — it's NOT a pytest `assert` statement. When the mock assertion fails, the custom message does NOT appear in the output. The underlying `assert_called()` still raises, so the tests catch regressions, but debugging is harder. Three affected tests: `test_latents_transferred_back_for_refiner`, `test_dynamo_reset_called_after_cleanup`, and `test_base_freed_before_refiner_loads`. **Not a blocker for merge, but Neo should fix this as a follow-up.**

---

## Verdict

**APPROVED.** All four MEDIUM-severity issues are correctly addressed. Code logic is sound. The 9 new tests use call-order tracking and would catch regressions on Fixes 1, 2, and 3. Fix 4 is verified clean by inspection.

**Follow-up (not blocking):** Neo to fix the orphaned message pattern in 3 tests and add call-ordering assertion to `test_latents_transferred_back_for_refiner`.
