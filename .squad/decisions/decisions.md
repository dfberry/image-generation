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

---

## TDD Sprint: Batch CLI + OOM Retry (PRs #10, #11)

### PR #10: OOM Auto-Retry with Step Reduction

**Date:** 2026-03-24
**Author:** Trinity (Backend Developer)
**Branch:** `squad/oom-retry`
**Verdict:** ✅ **APPROVED — Merged to main**

**Feature Implemented:** `generate_with_retry(args, max_retries: int = 2) -> str`

- **Behavior:** Wraps `generate(args)` with OOM retry logic
- **On OOMError:** Halves `args.steps` (floor at 1), prints warning, retries
- **Retries:** Up to `max_retries` times (so `max_retries + 1` total calls)
- **Exhaustion:** Re-raises `OOMError` with final steps count in message
- **Non-OOM exceptions:** Propagate immediately, no retry

**Test Results:** 12/12 tests pass
- All critical paths covered (step halving, max_retries exhaustion)
- Edge cases: steps=1 floor, all retry types

**Integration with main():** Single-prompt path now calls `generate_with_retry()` instead of `generate()`. Batch mode preserves existing `batch_generate()` path.

**Reviewer Note (Morpheus):** Future work should update `batch_generate()` to utilize `generate_with_retry()` logic for robust batch OOM handling. Currently batch fails immediately on OOM for a single item. Acceptable for this scope but inconsistent architecturally. Deferred as architectural improvement.

### PR #11: --batch-file CLI Flag

**Date:** 2026-03-24
**Author:** Trinity (Backend Developer)
**Branch:** `squad/batch-cli`
**Verdict:** ✅ **APPROVED — Merged to main**

**Features Implemented:**
1. `--batch-file <path>` argument (mutually exclusive with `--prompt`)
2. Extracted `main()` function from `if __name__ == "__main__":` block
3. main() handles both paths: --batch-file → read JSON → call batch_generate(), or --prompt → call generate()

**Test Results:** 10/10 tests pass
- All contract tests from neo-batch-cli-tdd-red.md satisfied
- Full regression suite: 63/63 pass (zero regressions)

**Error Handling:**
- Missing file → `sys.exit(1)` with stderr message
- Malformed JSON → `sys.exit(1)` with stderr message
- Partial batch failure → continues (per-item try/except in batch_generate())

**CI Constraint:** `.github/workflows/tests.yml` uses `workflow_dispatch` only (no auto-triggers on push/PR)

**generate_blog_images.sh Refactor (included in PR #11):**
- Replaced 5 sequential `python generate.py` calls with single `--batch-file` invocation
- PID-namespaced temp JSON file (no /tmp usage, local directory)
- `set -euo pipefail` for safety
- Per-item seeds preserved (42–46)

### TDD Cycle Summary

**Neo's Red Phase Tests (2026-03-24):**
- tests/test_batch_cli.py: 10 tests documenting --batch-file contract
- tests/test_oom_retry.py: 12 tests documenting generate_with_retry() contract
- Both files syntactically valid, collected by pytest, all failing (by design)

**Trinity's Green Phase Implementation:**
- PR #10: generate_with_retry() implementation
- PR #11: --batch-file CLI + main() refactor + shell update
- All tests transitioned from red to green via implementation

**Code Reviews:**
- **Morpheus review PR #10:** APPROVED. Correctness verified. Safety validated. Testing comprehensive.
- **Neo review PR #11:** APPROVED. All 10 contract tests pass. Zero regressions. CI constraint verified.

### Architectural Notes

- **TDD Discipline:** Red phase tests documented requirements precisely. Trinity implementation satisfied all tests in green phase. Code reviews verified behavior matches spec.
- **Exception Safety:** 
  - Single-prompt path: `generate_with_retry()` catches OOMError, retries, delegates cleanup to `generate()`'s finally block
  - Batch path: Per-item exceptions caught, converted to error dicts, batch never raises
  - Both paths respect device handling and --cpu flag
- **Memory Management:** batch_generate() flushes GPU memory between items (gc.collect + device cache clears), following generate()'s established patterns

### Merged to main

Both PRs merged to main with all tests passing:
- PR #10: squad/oom-retry → generate_with_retry() implementation
- PR #11: squad/batch-cli → --batch-file CLI + shell update

Tests written and merged:
- tests/test_batch_cli.py (10 tests, all passing on main)
- tests/test_oom_retry.py (12 tests, all passing on main)

**Final test status on main:**
- test_batch_cli.py: 10/10 ✅
- test_oom_retry.py: 12/12 ✅
- test_batch_generation.py: 17/17 ✅
- test_oom_handling.py: 14/14 ✅
- test_memory_cleanup.py: 22/22 ✅
- **Total: 75/75 ✅ ALL PASSING**

### Future Work Note

Morpheus flagged that `batch_generate()` should eventually use `generate_with_retry()` for consistent OOM handling across both single-prompt and batch modes. Currently batch fails immediately on OOM for one item while single-prompt mode retries. This is acceptable for initial release but represents an architectural inconsistency. Deferred as future enhancement, not blocking current merge.

---

## Full Team Code Review (2026-03-26T02:00:00Z — 2026-03-26T02:02:00Z)

**Date:** 2026-03-26 (UTC)  
**Event:** Comprehensive team code review: architecture, backend implementation, pipeline quality, prompt library, and test coverage  
**Agents:** Morpheus (Lead), Trinity (Backend), Niobe (Pipeline), Switch (Prompts), Neo (Testing)  
**Outcome:** 10 issues identified (3 HIGH, 4 MEDIUM, 3 LOW), cross-team recommendations for Phase 1/2/3 work

### Issues Summary

#### HIGH Severity (Correctness & Portability Blockers)

1. **args.steps Mutation in generate_with_retry() — Trinity Finding**
   - **Issue:** Retry loop modifies passed-in args object: `args.steps = args.steps // 2`
   - **Impact:** Caller's args permanently modified (unexpected side effect)
   - **Fix:** Use local copy: `retry_args = SimpleNamespace(**vars(args))`
   - **Severity:** HIGH (correctness bug)
   - **Priority:** Phase 2 immediate fix

2. **Hardcoded Absolute Path in generate_blog_images.sh — Morpheus Finding**
   - **Issue:** Line 13 uses absolute path (breaks on different machines)
   - **Impact:** Script fails on different directories/systems
   - **Fix:** Use `$(dirname "$0")` or PWD-relative path
   - **Severity:** HIGH (portability blocker)
   - **Priority:** Phase 1 quick win

3. **Monolithic generate.py (7+ Responsibilities) — Morpheus Finding**
   - **Issue:** 320-line single file: CLI parsing, generation, memory, batch logic mixed
   - **Impact:** Harder to test, module reuse limited
   - **Recommendation:** Consider batch logic extraction (Phase 3 architectural)
   - **Severity:** HIGH (design concern, not immediate blocker)

#### MEDIUM Severity (Functional Gaps & Architecture)

1. **batch_generate() Ignores CLI Overrides — Trinity Finding**
   - **Issue:** Batch items generated with defaults, not CLI args (--steps, --guidance, --width, --height, --refine)
   - **Impact:** CLI flags only work in single-prompt path; batch inconsistent with CLI
   - **Fix:** Implement parameter forwarding (TDD-first approach)
   - **Severity:** MEDIUM (design inconsistency)
   - **Priority:** Phase 2

2. **Cache Flush Guard Inconsistency — Trinity Finding**
   - **Issue:** CUDA cache clear unconditional; MPS guards incomplete
   - **Impact:** Code maintainability, inconsistent guard strategy
   - **Fix:** Extract `flush_device_cache(device)` helper
   - **Severity:** MEDIUM (code quality, DRY)
   - **Priority:** Phase 2 refactor

3. **No --negative-prompt CLI Support — Switch/Niobe Finding**
   - **Issue:** Pipeline supports negative prompts, but no CLI flag or batch wiring
   - **Impact:** SDXL quality degraded (negative prompts critical for artifact rejection)
   - **Estimated Quality Gain:** 20–30% improvement with negative prompts
   - **Architecture Needed:** CLI flag (Trinity) + batch JSON (Trinity) + style guide (Switch) + pipeline tuning (Niobe)
   - **Severity:** MEDIUM (architectural gap, image quality blocker)
   - **Priority:** Phase 3 (depends on negative prompt support)
   - **Blocking Dependencies:** Trinity CLI wiring required before style guide finalization

4. **CLI Argument Validation Missing — Neo Finding**
   - **Issue:** argparse accepts invalid ranges (steps=0, width=7, guidance=-1)
   - **Impact:** Parser accepts edge cases; generation may fail or produce unexpected output
   - **Fix:** Add validators using argparse type= parameter
   - **Severity:** MEDIUM (correctness edge case)
   - **Priority:** Phase 2 (TDD-first)

#### LOW Severity (Quick Wins & Documentation)

1. **README Test Count Stale — Morpheus Finding**
   - **Issue:** Documentation says "22 tests", actual: 53+
   - **Fix:** Update README: "22 tests" → "53+ tests"
   - **Priority:** Phase 1 quick win

2. **Style Anchor Inconsistency in Prompts — Switch Finding**
   - **Issue:** 3 different anchors across 10 prompts; "magical realism" missing from vacation set
   - **Impact:** Visual style inconsistency
   - **Fix:** Standardize anchor, add to vacation set
   - **Priority:** Phase 2

3. **Missing tests/__init__.py — Morpheus Finding**
   - **Issue:** No __init__.py in tests/ (minor, pytest doesn't require it)
   - **Fix:** Add empty file for consistency
   - **Priority:** Phase 1 quick win

4. **Vacation Prompts Missing "No Text" Constraint — Switch Finding**
   - **Issue:** All original vacation prompts include "no text" constraint; current examples.md missing
   - **Impact:** Generated vacation images may have text artifacts
   - **Fix:** Add "no text" constraint documentation + negative prompt
   - **Priority:** Phase 2

5. **No Prompt Template System — Switch Finding**
   - **Issue:** Prompts duplicated, no single source of truth (no programmatic access)
   - **Impact:** Hard to maintain consistency, no template reuse
   - **Recommendation:** JSON/YAML template system (Phase 3)
   - **Priority:** Phase 3 architectural enhancement

### Recommendations by Phase

#### Phase 1 (Immediate, Quick Wins)
1. Fix hardcoded path in generate_blog_images.sh
2. Update README: test count 22 → 53+
3. Add tests/__init__.py (empty)

#### Phase 2 (Next Sprint, Core Fixes, TDD-First)

**HIGH Priority:**
1. Fix args.steps mutation in generate_with_retry() (use SimpleNamespace copy)

**MEDIUM Priority:**
2. batch_generate() parameter forwarding (Neo writes tests → Trinity implements)
3. Extract flush_device_cache() helper (DRY refactor)
4. Add CLI argument validators (TDD-first)
5. Vacation set fixes: add "magical realism" + "no text" constraint
6. Document local test setup (CPU torch workaround)

**Architectural Changes:**
7. All TDD-first: write failing tests first, implement to green, regression check

#### Phase 3 (Architectural Enhancements)

1. **Negative Prompt Feature (Highest Priority)**
   - Trinity: CLI wiring (--negative-prompt flag) + batch JSON support
   - Switch: Style guide + negative prompt anchors + vacation set completion
   - Niobe: Pipeline integration + guidance tuning

2. **Prompt Template System (After Negative Prompts)**
   - Switch: Create prompts/templates.json (JSON/YAML structured definitions)
   - Trinity: Implement prompt builder function in generate.py
   - Benefits: Single source of truth, programmatic access, easy maintenance

3. **Quality Tuning (After Negative Prompts Wired)**
   - Niobe: A/B test guidance scales (current 7.5 vs proposed 5.0 for refiner)
   - Niobe: A/B test scheduler (Euler 40 steps vs DPMSolverMultistep 28 steps, ~35% speedup)
   - Establish baseline and validate quality equivalence

4. **Optional: Logging Infrastructure**
   - Trinity: Consider structured logging (logging module)
   - Benefits: Better debugging, performance metrics
   - Priority: Low, non-blocking

### Cross-Team Dependencies

- **Trinity/Neo:** Batch parameter forwarding requires TDD test-first
- **Trinity/Switch:** Negative prompt CLI requires close collaboration on style guide
- **Trinity/Niobe:** Scheduler/guidance tuning depends on --negative-prompt feature
- **Morpheus:** Approves all architectural decisions and prioritization

### Test Coverage Status

**Current:** 53+ tests all passing (22 memory + 17 batch + 14 OOM + 10 CLI + 12 retry + 3 device)

**Gaps Identified by Neo:**
- CLI argument validation: No edge case tests (steps=0, width=7, etc.)
- Batch parameter forwarding: Not tested (feature not yet implemented)
- Device fallback: Incomplete (local CPU workaround, CUDA/MPS untested in CI)
- Integration: No end-to-end tests (CLI → file output)

**Phase 2 Additions:**
- CLI validation tests (TDD-first)
- Batch parameter forwarding tests (TDD-first)

**Phase 3 Additions:**
- Device-specific fixtures + conditional skip decorators
- Integration tests (file output verification)

### Memory Management Status

**Audit Result: ✅ SOLID — No Blockers**

All MEDIUM-priority memory fixes (PR #4–#6) verified correct:
- Latents CPU transfer: ✅ Correct timing and device handling
- Dynamo cache reset: ✅ Guards present and necessary
- Entry-point VRAM flush: ✅ Fires before load_base()
- Global state: ✅ Clean (no process-persistent references)

**Production Status:** Memory management ready for production batch workflows

### Pipeline Quality Status

**Finding: Wait for Negative Prompts Before Tuning**

- **Scheduler Swap:** Defer DPMSolverMultistep swap (35% speedup) until negative prompts establish baseline
- **Guidance Tuning:** Defer refiner guidance 5.0 testing (vs current 7.5) until negative prompt baseline
- **Rationale:** Negative prompts significantly impact quality perception; baseline unreliable without them

**Blocked on:** Trinity CLI implementation (negative prompt feature)

### Prompt Library Status

**Findings:**
- Style consistency issues (3 different anchors)
- Vacation set missing constraints ("no text", style anchor)
- No template system (prompts duplicated, no programmatic access)

**Phase 2:** Fix vacation set consistency  
**Phase 3:** Template system + negative prompt integration (blocked on Trinity)

### Decisions Made

1. **HIGH Priority:** Fix args.steps mutation immediately (Phase 2)
2. **TDD-First Approach:** All Phase 2 changes require tests first
3. **Negative Prompt Feature:** Critical for quality improvement, Phase 3 priority
4. **Template System:** Deferred to Phase 3 (after negative prompts)
5. **Guidance/Scheduler Tuning:** Deferred to Phase 3 (after negative prompts establish baseline)

### Next Steps

1. Team consensus on Phase 2 prioritization
2. Begin Phase 1 quick wins immediately
3. Neo writes failing tests for Phase 2 (CLI validation, batch parameters)
4. Trinity implements Phase 2 fixes per TDD-first approach
5. Scribe merges inbox decisions into decisions.md (completed)
6. Team syncs on Phase 3 scope after Phase 2 complete


---

# The Joel Test: Assessment for image-generation

**Assessed by:** Morpheus (Lead)
**Date:** 2026-03-27
**Repo:** dfberry/image-generation
**Score:** 6/12 (3 YES, 6 PARTIAL, 3 NO)

---

## Scoring Summary

| # | Question | Score | Details |
|---|----------|-------|---------|
| 1 | Source control? | ✅ YES | Git + GitHub, active branching |
| 2 | One-step build? | ⚠️ PARTIAL | `pip install -r requirements.txt` works, but no Makefile or single entry point |
| 3 | Daily builds? | ⚠️ PARTIAL | CI exists but is manual-dispatch only |
| 4 | Bug database? | ⚠️ PARTIAL | GitHub Issues used, but lightly |
| 5 | Fix bugs before new code? | ✅ YES | TDD directive enforced, evidence in PR history |
| 6 | Up-to-date schedule? | ❌ NO | No roadmap, milestones, or project board |
| 7 | Have a spec? | ⚠️ PARTIAL | Prompt library and style guide exist, but no functional spec for the tool itself |
| 8 | Quiet working conditions? | ⚠️ PARTIAL | Good DX basics (venv, .gitignore), but no Makefile, no pre-commit hooks, no linting |
| 9 | Best tools? | ⚠️ PARTIAL | Good ML stack, but missing linter, formatter, type checker |
| 10 | Have testers? | ✅ YES | Neo (AI tester), 53+ mock-based regression tests, ~2s runtime |
| 11 | Code during interview? | ❌ NO | No CONTRIBUTING.md, no issue templates, no onboarding path |
| 12 | Hallway usability testing? | ❌ NO | README is decent but no quickstart validation, no user feedback loop |

---

## Detailed Assessment

### 1. Do you use source control? ✅ YES

**What exists:**
- Git repository hosted on GitHub (dfberry/image-generation)
- Active branch strategy: `squad/{issue}-{slug}` naming convention
- 14+ PRs merged with review process
- Clean `.gitignore` covering Python, model weights, generated outputs, IDE files
- `.gitattributes` present

**What's good:** Branching discipline is strong. PRs have reviewers, decisions are documented before merge. The Squad system enforces a review gate.

**Gaps:** None significant. This is solid.

---

### 2. Can you make a build in one step? ⚠️ PARTIAL

**What exists:**
- `pip install -r requirements.txt` installs all dependencies
- `python generate.py --prompt "..."` runs the tool
- `bash generate_blog_images.sh` runs batch generation
- README documents setup and usage clearly

**What's missing:**
- **No Makefile or task runner.** There's no single command that sets up the environment, installs deps, and verifies the installation works. A new developer must manually: create venv → activate → pip install → verify.
- **No `setup.py` or `pyproject.toml`.** The project isn't installable as a package.
- **No dev dependencies separation.** `pytest` isn't in requirements.txt — you have to know to install it separately.

**Recommended improvements:**
1. Create a `Makefile` with targets: `setup`, `install`, `test`, `lint`, `clean`
2. Add `requirements-dev.txt` (pytest, any future linting tools)
3. Or migrate to `pyproject.toml` with `[project.optional-dependencies]` for dev deps

---

### 3. Do you make daily builds? ⚠️ PARTIAL

**What exists:**
- `.github/workflows/tests.yml` — GitHub Actions CI pipeline
- Tests Python 3.10 and 3.11 matrix
- CPU-only torch install (fast, no GPU required)
- 53+ tests run in ~2 seconds

**What's missing:**
- **CI is `workflow_dispatch` only** — must be manually triggered. No automatic runs on push or PR.
- **No PR gate.** PRs can merge without CI passing (no branch protection rules enforcing status checks).
- **No linting in CI.** Only tests run; no style/type checks.
- Rationale for manual-only: dfberry ran out of GitHub Actions minutes. This is understandable but leaves a gap.

**Recommended improvements:**
1. Add `on: pull_request` trigger (even if limited to `paths: ['**.py']` to conserve minutes)
2. Add branch protection requiring CI to pass before merge
3. Add a lint job (ruff is fast — adds <5 seconds)
4. Consider: on push to main + on PR, with concurrency groups to cancel stale runs

---

### 4. Do you have a bug database? ⚠️ PARTIAL

**What exists:**
- GitHub Issues is used (Issue #3 was a detailed test coverage request)
- Squad workflows auto-triage issues labeled `squad`
- `.squad/decisions.md` tracks bugs found during audits (6 memory issues cataloged with severity)
- PR descriptions document bugs being fixed

**What's missing:**
- **Only 1 issue ever created** (and it's closed). Most bugs are tracked informally in `.squad/decisions.md` and PR descriptions rather than as discrete GitHub Issues.
- **No issue templates** (bug report, feature request). Contributors don't have a structured way to report problems.
- **No labels beyond `squad`** for categorization (severity, type, area).
- **Known bugs exist without issues:** args.steps mutation, batch parameter drop, negative prompt gap — all documented in squad decisions but not tracked as issues.

**Recommended improvements:**
1. Create `.github/ISSUE_TEMPLATE/bug_report.md` and `feature_request.md`
2. File GitHub Issues for all known bugs (args mutation, batch param drop, etc.)
3. Add labels: `bug`, `enhancement`, `good-first-issue`, severity levels
4. Use GitHub Projects or milestones for tracking

---

### 5. Do you fix bugs before writing new code? ✅ YES

**What exists:**
- **TDD directive is the #1 team decision.** Documented, enforced, evidenced in PR history.
- PR sequence shows discipline: memory audit → test infrastructure → fixes → new features
- PRs #1–#6 were all bug fixes before feature work (PR #9 batch, PR #14 enhancements)
- Code review process catches regressions (Morpheus rejected PR #8 initially for scoping)

**What's good:** This is one of the strongest areas. The team has a documented "fix bugs first" culture reinforced by the TDD directive and review gates.

**Gaps:** Some known bugs (args mutation, batch param forwarding) are documented but not yet fixed. They're queued in priority order though, which is the right approach.

---

### 6. Do you have an up-to-date schedule? ❌ NO

**What exists:**
- `.squad/decisions.md` has a rough priority order ("Next Sprint Priority" sections)
- Squad decisions document recommended implementation order for fixes
- `image-generation-improvements.md` and `performance-optimization.md` contain ideas

**What's missing:**
- **No milestones** in GitHub
- **No project board** (GitHub Projects)
- **No roadmap document** with dates or target versions
- **No versioning** (no CHANGELOG, no tags, no releases)
- Sprint priorities exist but are informal notes in decision documents

**Recommended improvements:**
1. Create GitHub Milestones for next 2 planned work batches
2. Add a `CHANGELOG.md` — even informal, it provides release history
3. Tag releases (even v0.1.0 as baseline)
4. Use GitHub Projects board with columns: Backlog → In Progress → Review → Done

---

### 7. Do you have a spec? ⚠️ PARTIAL

**What exists:**
- `README.md` documents CLI flags, usage, and setup
- `prompts/examples.md` — detailed style guide and prompt library
- `docs/blog-image-generation-skill.md` — skill documentation
- `image-generation-improvements.md` — improvement ideas
- `performance-optimization.md` — optimization guidance
- `.squad/decisions.md` (~26KB) — detailed architectural decisions

**What's missing:**
- **No functional specification** for the tool itself (what it should do, edge cases, expected behavior)
- **No API/interface contract** (what `generate()` accepts, returns, guarantees)
- **Decision documents serve as de facto specs** but are scattered and chronological rather than organized by feature
- **No architecture diagram** or system overview

**Recommended improvements:**
1. Add a `docs/architecture.md` describing the pipeline: CLI → args → device detection → base model → (optional refiner) → output
2. Document the `generate()` function contract (inputs, outputs, side effects, error handling)
3. Create a `docs/spec.md` with expected behaviors for each CLI flag

---

### 8. Do programmers have quiet working conditions? ⚠️ PARTIAL

*Adapted for repo context: Does the development environment minimize friction?*

**What exists:**
- Clean `.gitignore` (Python, IDE, models, outputs)
- Virtual environment documented in README
- Tests run in 2 seconds (no GPU required)
- Mock-based testing eliminates 7GB model download for dev
- Squad system provides structured decision-making

**What's missing:**
- **No Makefile or task runner** — developers must remember exact commands
- **No pre-commit hooks** — formatting/linting issues caught only in review
- **No linting configuration** (no ruff, flake8, black, mypy, pylint)
- **No editor configuration** (no `.editorconfig`, no `.vscode/settings.json`)
- **No type hints enforced** (Python code uses no type annotations)

**Recommended improvements:**
1. Add `ruff` for linting + formatting (single tool, fast, modern)
2. Add `pre-commit` hooks configuration (`.pre-commit-config.yaml`)
3. Add `.editorconfig` for consistent formatting across editors
4. Consider `mypy` or type annotations in `generate.py` critical paths

---

### 9. Do you use the best tools money can buy? ⚠️ PARTIAL

*Adapted: Are you using the best available tools for this project?*

**What exists:**
- **ML stack is excellent:** diffusers, transformers, torch, accelerate — industry standard
- **Testing:** pytest with comprehensive mock infrastructure
- **CI:** GitHub Actions (even if underused)
- **AI team system:** Squad framework for structured development
- **GitHub Copilot integration** with agent definitions

**What's missing:**
- **No linter** (ruff/flake8/pylint) — code quality is review-dependent
- **No formatter** (black/ruff format) — style is inconsistent
- **No type checker** (mypy/pyright)
- **No security scanner** (bandit, safety)
- **No dependency update automation** (dependabot, renovate)
- **No code coverage tool** (coverage.py, pytest-cov)

**Recommended improvements:**
1. Add `ruff` (linting + formatting, replaces flake8+black+isort)
2. Add `pytest-cov` for coverage reporting
3. Enable Dependabot for dependency updates
4. Add `bandit` for security scanning (relevant given ML model loading)

---

### 10. Do you have testers? ✅ YES

**What exists:**
- **Neo (AI Tester)** — dedicated testing agent with charter, history, and test design authority
- **53+ regression tests** across 12 test files
- **conftest.py** with shared mock infrastructure (MockPipeline, MockImage, 4 fixture variants)
- **TDD workflow:** tests written before code, enforced by team directive
- Tests cover: memory cleanup, batch generation, OOM handling, CLI validation, schedulers, negative prompts, bug fixes, pipeline enhancements, unit functions
- **~2 second runtime**, no GPU required, CI-ready

**What's good:** This is strong. Test-first culture is real and evidenced in commit history. Mock strategy is well-designed.

**Gaps:**
- No code coverage measurement (don't know actual line/branch coverage %)
- Some test files are TDD "red phase" (expected failures for in-progress features)
- No integration tests (real model loading) — acceptable given GPU requirements

---

### 11. Do new candidates write code during their interview? ❌ NO

*Adapted: Is there a clear path for new contributors?*

**What exists:**
- README has setup and usage instructions
- MIT license declared
- `.squad/` system documents team roles and conventions

**What's missing:**
- **No CONTRIBUTING.md** — no guidance on how to contribute
- **No CODEOWNERS file** — no automatic review assignment
- **No issue templates** — no structured way to report bugs or request features
- **No "good first issue" labels** — no onboarding path for new contributors
- **No development setup guide** beyond basic pip install

**Recommended improvements:**
1. Create `CONTRIBUTING.md` with: dev setup, test commands, PR process, coding standards
2. Add `CODEOWNERS` file mapping paths to reviewers
3. Create issue templates (bug, feature, question)
4. Label some backlog items as `good-first-issue`

---

### 12. Do you do hallway usability testing? ❌ NO

*Adapted: Do you validate the user experience?*

**What exists:**
- README documents all CLI flags with a table
- Example commands provided
- `prompts/examples.md` shows real-world prompt examples
- Generated outputs demonstrate the tool works

**What's missing:**
- **No quickstart validation** — nobody has tested "can a new person get from clone to first image?"
- **No user feedback mechanism** (discussions, feedback form)
- **No error message review** — OOM errors are good, but general error UX is untested
- **No `--help` output review** (argparse help may not match README)
- **No Windows setup tested** (README shows Unix `source venv/bin/activate` with Windows comment)

**Recommended improvements:**
1. Have someone unfamiliar with the project try the README setup → first image flow
2. Add `python generate.py --help` output validation test
3. Enable GitHub Discussions for user feedback
4. Test and document Windows setup explicitly

---

## Prioritized Top Improvements

These are the highest-impact changes, ordered by effort-to-value ratio:

### Tier 1 — Quick Wins (< 1 hour each, high impact)

| # | Action | Joel Test Items | Impact |
|---|--------|----------------|--------|
| 1 | **Add `on: pull_request` to CI workflow** | #3 Daily Builds | Catches regressions automatically |
| 2 | **Add `ruff` linting** (config + CI job) | #8 DX, #9 Tools | Instant code quality baseline |
| 3 | **Create `Makefile`** with setup/test/lint targets | #2 One-Step Build, #8 DX | Single entry point for all tasks |
| 4 | **Create issue templates** (bug + feature) | #4 Bug Database, #11 Contributors | Structured bug reporting |

### Tier 2 — Medium Effort (2-4 hours each, high impact)

| # | Action | Joel Test Items | Impact |
|---|--------|----------------|--------|
| 5 | **Create `CONTRIBUTING.md`** | #11 Contributors | Onboarding path for new devs |
| 6 | **Add `requirements-dev.txt`** or migrate to `pyproject.toml` | #2 Build | Clean dependency management |
| 7 | **File GitHub Issues for all known bugs** | #4 Bug Database | Centralized tracking |
| 8 | **Add `pytest-cov` coverage reporting** | #10 Testers | Know actual coverage % |

### Tier 3 — Larger Efforts (half-day+, strategic value)

| # | Action | Joel Test Items | Impact |
|---|--------|----------------|--------|
| 9 | **Create GitHub Project board** | #6 Schedule | Visual progress tracking |
| 10 | **Write `docs/architecture.md`** | #7 Spec | System understanding for contributors |
| 11 | **Add pre-commit hooks** | #8 DX, #9 Tools | Shift quality left |
| 12 | **Tag first release (v0.1.0)** + CHANGELOG | #6 Schedule | Version history baseline |

---

## Summary

The repo is strongest in **testing culture** (#5, #10) and **source control discipline** (#1) — the TDD directive and Neo's test infrastructure are genuine strengths. The biggest gaps are in **developer experience tooling** (#2, #8, #9) and **project management infrastructure** (#4, #6, #11, #12). The CI workflow exists but is underused due to Actions minute constraints.

The four Tier 1 improvements (PR-triggered CI, ruff, Makefile, issue templates) would move the score from **6/12 to 9/12** with minimal effort. These should be the immediate priority.

---

## Joel Test Tier 1 Implementation (2026-04-18)

### Decision: Joel Test Tier 1 — CI, Makefile, Linting, Dev Deps

**By:** Trinity (Backend Dev)  
**Date:** 2026-04-18  
**Status:** Implemented  
**Test Status:** 172 tests passing

#### What Changed

1. **CI workflow** (`.github/workflows/tests.yml`): Added `push` (main) and `pull_request` triggers with path filters. Added `lint` job (ruff) that gates test matrix. Added concurrency groups to cancel stale runs.
2. **Makefile**: Standard targets — `setup`, `install`, `install-dev`, `test`, `lint`, `format`, `clean`, `all`. Uses venv-relative Python paths.
3. **requirements-dev.txt**: Chains base requirements + pytest, ruff, pytest-cov.
4. **ruff.toml**: Python 3.10 target, 120 char lines, E/F/W/I rules, E501 ignored (formatter owns line length), excludes venv/outputs/__pycache__.

#### Rationale

Joel Test improvements: automated builds on every PR, one-command dev setup, consistent linting across local + CI.

#### Impact

- All PRs now get lint + test automatically
- New contributors: `make setup && make all` gets a working environment
- ruff config is the single source of truth for style rules

---

### Decision: Contributor Experience Templates (Joel Test #4, #11)

**By:** Neo (Tester)  
**Date:** 2026-04-18  
**Status:** Implemented  
**Test Status:** All contributor flows validated

#### What

Created GitHub issue templates (bug report, feature request), CONTRIBUTING.md, and CODEOWNERS to address Joel Test items #4 (bug database) and #11 (new candidate process / contributor onboarding).

#### Key Choices

1. **CONTRIBUTING.md references direct commands** — Makefile targets added by Trinity in parallel; CONTRIBUTING.md documents Python commands directly. Should reference Makefile if workflow changes.
2. **TDD-first workflow documented** — consistent with team's existing TDD directive.
3. **Branch naming** — `squad/{issue}-{slug}` convention documented for all contributors.
4. **CODEOWNERS scope** — all paths map to @dfberry as sole maintainer.

#### Files

- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `CONTRIBUTING.md`
- `CODEOWNERS`

#### Impact

- Streamlined issue filing and feature requests
- Clear contributor onboarding path
- Consistent branch and workflow documentation

