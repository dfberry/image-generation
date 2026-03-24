# Squad Decisions

## Active Decisions

### Directive: User Test-Driven Development Workflow (2026-03-23)

**By:** dfberry (via Copilot)

**Decision:** All future changes must follow this workflow:
1. Create a PR branch first
2. Write tests before making any fixes (test-first / TDD)
3. Make the fixes
4. Ensure all tests pass
5. Team signs off before merge

**Rationale:** Establishes TDD workflow and PR-gate process. Ensures all code changes are validated by tests before merge.

---

### Plan: Test Coverage for Memory Fixes (2026-03-23)

**By:** Neo (Tester)

**Status:** Ready for implementation

**Scope:** 20 regression tests covering:
- PR #1: Model loading variants, CPU offload, shared components
- PR #2: Cache clearing, dangling reference cleanup, generator device binding

**Test File:** `tests/test_generate.py`

**Strategy:** Mock-based testing (no real GPU required). All tests use patching at the `generate` module level to avoid 7GB model downloads.

**Key Fixes Covered:**
- fp16 variant handling on MPS/CUDA/CPU
- CPU offload on MPS and CPU devices
- Shared text_encoder_2 and VAE in dual-pipeline setup
- Cache clearing: `torch.mps.empty_cache()` and `torch.cuda.empty_cache()`
- Garbage collection forcing between generation stages
- Explicit deletion of dangling references (`del text_encoder_2, vae`)
- Generator device binding to CPU for offloaded layers

**Execution:** Run tests via `pytest tests/`

---

### Audit: Memory Management Issues in generate.py (2026-03-24)

**By:** Morpheus (Architecture), Trinity (Backend), Neo (Testing)

**Status:** Audit complete, recommendations ready for implementation

**Finding:** Three independent audits converged on 6 critical issues (4 shared, 2 Trinity-specific) in `generate.py` memory management, NOT addressed by PR #1 or PR #2.

#### Issues Identified

| # | Severity | Location | Issue | Fix |
|---|----------|----------|-------|-----|
| 1 | **HIGH** | `generate()` L123–180 | No try/finally — exception skips pipeline cleanup | Wrap both branches in try/finally; extract cache-flush helper |
| 2 | **MEDIUM** | `load_base()` L73–75 | `torch.compile` dynamo cache never reset | Add `torch._dynamo.reset()` after `del base` (CUDA only) |
| 3 | **MEDIUM** | `generate()` L102 | No VRAM cache flush at function entry | Add device-appropriate cache flush before `load_base()` |
| 4 | **MEDIUM** | `generate()` L137–148 | Latents tensor overlaps refiner load window (GPU side) | Move latents to CPU before refiner load on CUDA |
| 5 | **LOW** | `generate()` L128–174 | No outer `torch.no_grad()` on inference calls | Wrap inference with `@torch.no_grad()` for defensive hygiene |
| 6 | **MEDIUM** | `requirements.txt` | Version floors allow broken releases | Tighten: accelerate>=0.24.0, diffusers>=0.21.0, torch>=2.1.0 |

#### Neo's Test Gap Analysis

- Current coverage: **ZERO** (no `tests/` directory)
- Untested behaviors: 12 memory management patterns
- Proposed suite: **22 mock-based regression tests** (5 files, <5 seconds runtime)
- Critical gating test: `test_generate_refine_path_cleans_up_on_refiner_exception` will FAIL until Issue #1 is fixed

#### Recommended Implementation Order

1. **Phase 1:** Tighten `requirements.txt` version floors (Trinity #6, prerequisite)
2. **Phase 2:** Create test infrastructure and 22 regression tests (Neo)
3. **Phase 3:** Fix code in severity order: #1 (HIGH) → #2–4 (MEDIUM) → #5 (LOW)
4. **Phase 4:** Verify all tests pass, team review and merge

**Governance:** Per TDD directive, all fixes require test-first approach on PR branch with team sign-off.

---

### PR #4: High-Memory Fixes (try/finally + accelerate floor) — MERGED

**Date:** 2026-03-25
**Implementer:** Trinity
**Reviewer:** Morpheus
**Verdict:** ✅ MERGED

**Fixes (2 HIGH-severity):**
1. **try/finally exception safety** — Wraps inference body in exception-safe cleanup. Initializes all pipeline vars to None before try. Inline `del base; base = None` in refiner path preserved for load-order management. Finally block deletes all variables, calls `gc.collect()`, and cache clears (`torch.cuda.empty_cache()` unconditional, `torch.mps.empty_cache()` guarded by `is_available()`). `image` intentionally excluded from finally for post-finally `image.save()` call.

2. **Version floor tightening** — `accelerate>=0.24.0` (critical, fixes silent CPU offload hook deregistration regression), `diffusers>=0.21.0`, `torch>=2.1.0`. No conflicts. Prevents breaking of PR#1 cleanup on old versions.

**Test coverage:** 13 regression tests passing (neo-pr3-tests), all exception paths covered.

**Open issues (MEDIUM — Phase 3):** torch.compile dynamo cache reset, entry-point VRAM flush, latents CPU transfer, PIL cleanup (LOW).

---

### PR #5: MEDIUM Memory Fixes — MERGED

**Date:** 2026-03-25
**Implementer:** Trinity
**Reviewer:** Morpheus
**Verdict:** ✅ MERGED

**Fixes (3 MEDIUM-severity, 1 architecture note):**
1. **Latents tensor on GPU during cache flush** — `latents = latents.cpu()` before `del base`, guarded by `device in ("cuda", "mps")`. Moves tensor off GPU before cache flush window opens, maximizing VRAM reclamation.

2. **torch.compile dynamo cache growth** — `torch._dynamo.reset()` added to `finally` block, guarded by `device == "cuda" and hasattr(torch, "_dynamo")`. Prevents graph cache accumulation across repeated `generate()` calls.

3. **Entry-point VRAM flush missing** — `gc.collect()` + `torch.cuda.empty_cache()` + guarded `torch.mps.empty_cache()` added at the top of `generate()` before pipeline loads. Ensures each call starts with clean VRAM.

4. **Global state audit** — All pipeline objects (`base`, `refiner`, `latents`, `text_encoder_2`, `vae`) confirmed local to `generate()`. No module-level globals, no cache leaks. Code is clean.

**Test coverage:** 22 regression tests (test_memory_cleanup.py) all passing.

---

### PR #6: PIL Leak Fix + Test Assert Fixes — MERGED

**Date:** 2026-03-25
**Implementers:** Trinity (PIL fix), Neo (test assertions + file restoration)
**Reviewer:** Morpheus
**Verdict:** ✅ MERGED

**Fixes:**
1. **PIL Image leak (LOW)** — Moved `image.save(output_path)` and print inside try block, guarded by `if image is not None:`. Added `image = None` to finally cleanup. Releases PIL buffer promptly in batch contexts.

2. **Test assertion fixes** — Fixed 3 tests in `test_memory_cleanup.py` changing from `mock.assert_called(), "msg"` (silent tuple, broken assertion message) to `assert mock.called, "msg"` (proper Python assertion). Tests: gc_collect_called_at_entry_cuda, cuda_cache_flush_at_entry, mps_cache_flush_at_entry.

3. **PR #5 code restoration** — Neo's commit restored missing entry-point flush, latents CPU transfer, and dynamo reset code that was previously reviewed/approved (PR #5) but absent from main. Also restored test infrastructure (test_memory_cleanup.py, conftest.py).

**Result:** All 22 tests pass. Codebase now reflects approved fixes.

---

### Decision: CI Workflow — Manual Dispatch Only (2026-03-25)

**By:** Trinity (Backend Developer)
**PR:** #7

**Decision:** Add `.github/workflows/tests.yml` with `on: workflow_dispatch` only.

**Rationale:** dfberry is out of GitHub Actions minutes; no auto-triggers to avoid accidental burns. CPU-only torch install (`--index-url https://download.pytorch.org/whl/cpu`) keeps install fast and avoids GPU runner requirements. All 22 tests mock the pipeline — no real model loading, ~2 second runtime. Matrix: Python 3.10 and 3.11 (both supported versions).

**Files Created:** `.github/workflows/tests.yml`

---

### Decision: README Update — MPS Support + Testing + Memory Model (2026-03-25)

**By:** Morpheus (Architecture)
**PR:** #8
**Status:** MERGED (after Trinity scoped pytest command to test_memory_cleanup.py)

**Content Added:**
- MPS support section with device detection and model architecture
- Testing instructions (scoped pytest command showing 22 green tests only)
- Memory management model explanation
- Batch generation feature overview

**Note:** Initial pytest command failed due to TDD red-phase tests (PR #9). Trinity fixed scoping on squad/readme-update branch. Neo re-reviewed and approved. Merged to main (squash).

---

### Decision: TDD Test Suite — Batch Generation + OOM Handling (2026-03-25)

**By:** Neo (Tester)
**PR:** #9
**Status:** Red phase complete, awaiting Trinity implementation

**Test Suite:**
- **test_batch_generation.py** (17 tests): batch_generate() function contract tests (per-item error handling, inter-item GPU flushing, order preservation)
- **test_oom_handling.py** (17 tests): OOMError class and recovery hints (9 pass, 5 red)
- **test_memory_cleanup.py** (22 tests): Existing regression suite (all green)

**Total:** 22 red, 31 green

**Features Under Test:**
1. **batch_generate(prompts: list[dict], device: str = "mps") → list[dict]** — Input: [{"prompt", "output", "seed"}], Output: [{"prompt", "output", "status", "error"}]. Contract: per-item exception handling, inter-item `gc.collect()` + device cache clear, order preservation.

2. **OOMError(RuntimeError)** — Catches `torch.cuda.OutOfMemoryError` and MPS OOM `RuntimeError("out of memory")`, re-raises as custom OOMError with recovery message. Finally block executes (cleanup guaranteed even on OOM).

**Implementation Location:** Trinity may place `batch_generate` in `generate.py` or new `batch.py`. Tests handle both with try/except import.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
