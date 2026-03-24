# Project Context

- **Owner:** dfberry
- **Project:** Python-based AI image generation tool using Stable Diffusion XL (SDXL). Generates blog illustrations with tropical magical-realism aesthetic. Stack: Python 3.10+, diffusers, transformers, torch, Pillow. Key files: generate.py (main CLI), generate_blog_images.sh and regen_*.sh (batch scripts), prompts/ (style guides and prompt library), outputs/ (generated PNG images).
- **Stack:** Python 3.10+, diffusers>=0.19.0, transformers>=4.30.0, torch>=2.0.0, accelerate, safetensors, Pillow
- **Created:** 2026-03-23

## Key Paths

- `generate.py` — main CLI with --steps, --guidance, --seed, --width, --height, --refiner, --device flags
- `generate_blog_images.sh` — generates 5 blog images (01-05), seeds 42-46
- `regen_fix.sh` — regenerates images 01, 06, 07, 08 with corrected prompts
- `prompts/examples.md` — master prompt library, style guide (Latin American folk art, magical realism, tropical palette)
- `prompts/BLOG_IMAGE_UPDATES.md` — alt text and filename mapping for website integration
- `outputs/` — generated PNGs at 1024×1024, ~1.5-1.7MB each
- `.squad/` — team memory, decisions, agent histories

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-25 — PR #5: MEDIUM Regression Tests Delivered & Approved

Added 9 new MEDIUM regression tests to `tests/test_memory_cleanup.py` for `squad/pr5-medium-memory-fixes`. All 22 tests pass (~5.9s, no GPU).

**Test coverage:**
- **Entry-Point VRAM Flush (3 tests):** Verify gc.collect, cuda.empty_cache, mps.empty_cache fire before load_base. Uses call-order tracking.
- **Latents Tensor Handling (3 tests):** Verify latents.cpu() precedes cache flush, transferred back for refiner, cleaned up in finally.
- **Dynamo Cache Reset (2 tests):** Verify torch._dynamo.reset() called on CUDA after cleanup, NOT called on CPU.
- **Global State (1 test):** Verify entry flush fires on second generate() call too (no compound memory).

**Implementation approach:** Mock-based testing with call_log + side_effect patterns. All regressions caught at code level without GPU.

**Code findings (non-blocking):** Three tests use `mock.assert_called(), "message"` pattern — orphaned messages don't surface on failure. Will fix as follow-up.

**Review verdict:** APPROVED by Morpheus. Tests validate all active code fixes.

### 2026-03-25 — PR #3 Code Review: try/finally + test coverage validation

Neo wrote 13 regression tests covering exception paths and version floors:
- 12 tests for try/finally cleanup validation in generate()
- 1 test for accelerate version floor prerequisites
- All pass without GPU via mocking
- Critical test: `test_generate_refine_path_cleans_up_on_refiner_exception` validates exception safety architecture

**Key learnings for Phase 2 (full 22-test suite):**
- Mock-based testing scales well: no GPU, fast execution (~few seconds)
- Exception path testing is testable via patching at function entry points
- Version floor changes need validation tests to prevent silent regressions

**Trinity's PR #4 approved by Morpheus.** Both HIGH-severity fixes structurally correct. Ready for Phase 2 expansion (22 full regression tests). Phase 3 will tackle MEDIUM issues.

### 2026-03-23 — Memory Audit of generate.py (post PR#1, PR#2)

**Finding: Zero test coverage exists.** There is no `tests/` directory and no project-owned test files. The "Plan: Test Coverage for Memory Fixes" in decisions.md is documented but not implemented.

**Critical gap — no try/finally in generate().** If an exception is thrown after `del base` but before `del refiner` in the refine path, `text_encoder_2`, `vae`, `latents`, and `refiner` are never freed. This is the highest-risk untested scenario.

**Shared object lifetime is subtle.** `del text_encoder_2, vae` in generate() only removes local aliases. If the refiner pipeline holds internal strong references, the objects survive until the refiner itself is deleted. The ordering (`del latents, refiner` before `del text_encoder_2, vae`) is important but untested.

**All 12 memory behaviors are untested:** fp16 variant gating, cpu offload routing, `pipe.to(device)`, `del base`, MPS cache clear, CUDA cache clear, `gc.collect()`, `del latents/refiner`, `del text_encoder_2/vae`, generator CPU binding, `torch.compile` gating, shared component transfer.

**Cannot test without GPU:** real VRAM measurement, actual OOM triggering, MPS memory counters, `torch.compile` benefit, CPU offload effectiveness on constrained VRAM.

**Proposed suite:** ~22 mock-based tests across 5 files (`test_device.py`, `test_load_base.py`, `test_load_refiner.py`, `test_generate.py`, `test_edge_cases.py`). Full test function names and assertions written in `.squad/decisions/inbox/neo-memory-audit.md`.

---

### 2026-03-24 — Cross-Agent Audit Sync + Implementation Roadmap

Neo's test-gap analysis converged with Morpheus's architectural audit and Trinity's code-level review:

**All three agents independently identified the same 4 core issues:**
1. No exception safety (HIGH) — Neo's critical test gap matches Morpheus and Trinity's findings
2. torch.compile cache (MEDIUM) — All three identified it
3. Latents tensor overlap (MEDIUM) — All three identified it
4. Entry-point cache flush (MEDIUM) — All three identified it

**Neo's unique findings:**
- **Zero test coverage** — Complete absence of regression tests for PR#1 and PR#2 fixes
- **12 untested memory behaviors** — All device/offload/cache/gc patterns untested
- **22-test regression suite** — Specific test functions and fixtures ready to implement
- **Critical gating test** — `test_generate_refine_path_cleans_up_on_refiner_exception` FAILS until try/finally is added; serves as pass/fail gate for Issue #1 fix

**Recommended phases:**
1. **Phase 1 (Trinity):** Tighten requirements.txt version floors (prerequisite)
2. **Phase 2 (Neo):** Create test infrastructure, 22 regression tests (most fail initially)
3. **Phase 3 (Morpheus):** Fix code in severity order (failures in Phase 2 guide fixes)
4. **Phase 4:** Verify all tests pass, team review and merge

**Team consensus:** All findings merged into `.squad/decisions.md`. Neo will provide detailed test implementation plan before Phase 2 kicks off.

### 2026-03-25 — PR #6: 3 Orphaned Assert Messages Fixed

Fixed 3 tests in `tests/test_memory_cleanup.py` that used the silently-broken `mock.assert_called(), "message"` pattern (orphaned tuple syntax where the message string is discarded by pytest).

**Pattern fixed (before):**
```python
mock_gc.collect.assert_called(), "gc.collect() should fire before load_base on CUDA"
```
**After:**
```python
assert mock_gc.collect.called, "gc.collect() should fire before load_base on CUDA"
```

**3 tests fixed:**
1. `TestEntryPointFlush::test_gc_collect_called_at_entry_cuda`
2. `TestEntryPointFlush::test_cuda_cache_flush_at_entry`
3. `TestEntryPointFlush::test_mps_cache_flush_at_entry`

**Rule confirmed:** When the message adds diagnostic value (explains WHY or WHERE the call must happen), use `assert mock.called, "message"`. If redundant, remove. All 3 messages here explain ordering semantics, so they're worth keeping.

**Codebase note:** `tests/test_memory_cleanup.py` and `tests/conftest.py` were documented in PR #5 orchestration logs but never committed. Both created fresh on this PR. PR #5 MEDIUM code fixes (entry-point flush, latents CPU transfer, dynamo cache reset) were similarly missing from `generate.py` and restored.

All 22 tests pass (~1.9s, no GPU). Branch: `squad/pr6-pil-leak-fix`.
