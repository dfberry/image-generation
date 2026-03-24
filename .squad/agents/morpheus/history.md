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

### 2026-03-25 — PR #6 Code Review: PIL Leak Fix + Test Assert Fixes

Reviewed and APPROVED `squad/pr6-pil-leak-fix` (Trinity code fix, Neo test fixes). Both changes correct.

**Change 1 (Trinity — PIL leak fix):**
- `image.save()` moved inside `try` with `if image is not None:` guard. Guard is defensively correct (not strictly required since exception path already skips save, but harmless). Happy path unchanged. `image = None` in `finally` properly releases the PIL buffer after save. `return output_path` post-`finally` still correct — `output_path` defined before `try`.
- Closes the LOW-severity PIL leak identified in the original memory audit.

**Change 2 (Neo — test assert fixes + file restoration):**
- Root bug: `mock.assert_called(), "msg"` is a tuple expression (not an assertion). The comma silently detaches the message; `assert_called()` is called as a bare expression; the message is dropped. Tests appeared to pass even if the mock was never called.
- Fix: `assert mock.called, "msg"` — proper Python assertion with message. Semantically correct.
- Neo's commit also restored `tests/test_memory_cleanup.py`, `tests/conftest.py`, and the 3 MEDIUM code fixes (entry-point flush, latents CPU transfer, dynamo reset) from PR5 — which were documented as merged but absent from main. This wider scope is justified; tests and code are tightly coupled.
- All 22 tests pass.

**Architecture note:** PR5 code changes were documented as merged but never landed in main's `generate.py`. This was a scribe/merge gap — squad decisions documented the approval but the code wasn't actually in main. PR6 closes that gap. Recommend the scribe confirm main's final state post-merge.

**Decision:** Both changes APPROVED.

### 2026-03-25 — PR #5 Code Review & Approval: Four MEDIUM Memory Fixes

Reviewed and APPROVED `squad/pr5-medium-memory-fixes` (Trinity code, Neo tests). All four MEDIUM-severity issues correctly addressed.

**Fix reviews:**
1. **Latents CPU Transfer:** Order verified. `latents.cpu()` before `del base`. Device transfer uses `latents.to(device)` (MPS-aware). Guard correct.
2. **Dynamo Cache Reset:** In finally block. Both guards present: `device == "cuda"` and `hasattr(torch, "_dynamo")`. Comment flags MPS extension risk.
3. **Entry-Point VRAM Flush:** All 3 calls present, correct order, start of generate(). Two-flush pattern (entry + finally) intentional.
4. **Global State Audit:** Manual scan confirms. All pipeline vars are locals. Zero process-persistent refs. Clean architecture.

**Test review:** All 22 tests pass. 9 new MEDIUM tests use call-order tracking. Would catch regressions on active fixes 1, 2, 3. Fix 4 verified clean by inspection.

**Non-blocking finding:** 3 tests have orphaned assert message patterns. Neo follow-up for clarity, not a correctness issue.

**Decision:** APPROVED. All fixes correct. Code logic sound. Ready to merge.

### 2026-03-25 — PR #5 Code Review: Four MEDIUM Memory Fixes

Reviewed `squad/pr5-medium-memory-fixes` (Trinity's code, Neo's tests). All four MEDIUM-severity issues correctly handled.

**Fix 1 (latents CPU transfer):** `latents.cpu()` is placed before `del base` and before the mid-refine cache flush. Order confirmed in diff. Device transfer back uses `latents.to(device)` inline — not hardcoded `"cuda"`, MPS-safe. CPU path is correctly excluded via `if device in ("cuda", "mps")` guard. The `latents` variable holds the CPU copy until finally cleans it — benign.

**Fix 2 (dynamo reset):** `torch._dynamo.reset()` is inside `finally`. Dual guard: `device == "cuda"` (matches where `torch.compile` is actually used in `load_base()`, lines 72–75) AND `hasattr(torch, "_dynamo")` (protects against old torch versions). Both guards necessary and present.

**Fix 3 (entry-point flush):** All three calls present in correct order. Placed at the very start of `generate()` before `load_base()`. Two-flush pattern (entry + finally) is deliberate and correct.

**Fix 4 (global state audit):** Verified clean. All pipeline vars are locals in `generate()`. No module-level mutable pipeline state. Clean CLI architecture.

**Tests:** All 22 pass. 9 new MEDIUM tests use call-order tracking via `side_effect + call_log`. Would catch regressions on all three active fixes.

**One code smell found:** Three tests use `mock.assert_called(), "message"` — the comma makes the message an orphaned expression (not a pytest `assert`). Tests still catch regressions but custom messages don't surface on failure. Flagged for Neo follow-up, not blocking.

**Decision:** APPROVED.

### 2026-03-25 — PR #4 Code Review: try/finally + accelerate version floor

Reviewed `squad/pr3-high-memory-fixes` (Trinity's work). Both HIGH-severity issues are correctly fixed.

**try/finally analysis:**
- All five pipeline variables (`base`, `refiner`, `latents`, `text_encoder_2`, `vae`) initialized to `None` before `try`. `finally` deletes all five unconditionally — safe even when `base=None` mid-refine.
- The inline `del base; base = None` inside the refiner path is intentional load-order management (frees VRAM before `load_refiner()`), NOT duplicate cleanup. Setting `base = None` makes the `finally` deletion a safe no-op. Pattern is correct.
- `image` is intentionally excluded from `finally` cleanup — needed for the post-finally `image.save()` call. PIL image leak (LOW) is a known open issue, out of scope here.
- `torch.cuda.empty_cache()` called unconditionally in `finally` — correct, it's a no-op without CUDA. `torch.mps.empty_cache()` guarded by `is_available()` — also correct.
- Exception propagates correctly: if an exception fires inside `try`, `finally` cleans up, then exception propagates up. `image.save()` is unreachable in the exception path.
- Happy path unchanged: try completes, finally cleans pipelines, image is still live for save.

**requirements.txt analysis:**
- `accelerate>=0.24.0` — the critical fix. Versions below 0.24.0 silently skip CPU offload hook deregistration on `del pipe`, making PR#1's entire cleanup strategy inert.
- `diffusers>=0.21.0`, `torch>=2.1.0` — appropriate tightening.
- `transformers>=4.30.0` — not changed, within scope. No known equivalent hook regression.

**Remaining open (out of scope for this PR):** torch.compile dynamo cache reset (MEDIUM), entry-point VRAM flush (MEDIUM), latents tensor CPU transfer before refiner load (MEDIUM), PIL image cleanup (LOW).

**Decision:** APPROVED.

### 2026-03-23 — Memory Audit of generate.py (post PR #1 + PR #2)

Performed architectural memory review. Five issues found that survived both merged PRs:

1. **No exception safety (HIGH):** All `del`/cache-flush/gc calls are happy-path only. A single OOM or KeyboardInterrupt during inference leaves the full pipeline in VRAM with no cleanup. The fix is `try/finally` around the pipeline section — nothing else matters until this is in place.

2. **torch.compile dynamo cache (MEDIUM):** `torch.compile` on the UNet registers a graph in torch's process-global `_dynamo`/`_inductor` caches. `del base` + `gc.collect()` + `torch.cuda.empty_cache()` do NOT clear it. The compiled graph holds closure refs to model weights, potentially blocking VRAM reclaim. Fix: `torch._dynamo.reset()` after pipeline deletion on CUDA.

3. **No VRAM flush at function entry (MEDIUM):** `generate()` loads models immediately with no prior cache flush. Fragmented VRAM from prior operations (or prior calls in library mode) can cause spurious OOM. Mirror the exit cleanup at entry.

4. **Latent tensor bridges pipeline lifetimes (LOW–MEDIUM):** In refiner mode, the `latents` tensor from base inference is alive while the refiner loads. For SDXL at 1024×1024 fp16 this is ~0.5 MB — small now, but the pattern scales with resolution/additional pipelines.

5. **PIL image not deleted after save (LOW):** 3 MB in-process; harmless in CLI mode but accumulates in batch/library mode. Consistent with the explicit-cleanup discipline already established.

**Architecture note:** `generate()` is a flat function that owns model lifecycle. It has no error boundary. The team should consider whether model load/unload should move to a context manager to make cleanup unconditional and testable.

---

### 2026-03-24 — Cross-Agent Audit Sync

Morpheus's architectural audit converged with Trinity's code-level review and Neo's test-gap analysis:

**All three agents independently identified the same 4 core issues:**
1. No exception safety (HIGH) — Morpheus detail matches Trinity and Neo's critical test gap
2. torch.compile cache (MEDIUM) — Morpheus and Trinity both found it
3. Entry-point cache flush (MEDIUM) — Morpheus and Trinity both found it  
4. Latents tensor overlap (MEDIUM) — Morpheus and Trinity both found it

**Trinity added 2 more findings:**
- Defensive `torch.no_grad()` wrapping (LOW)
- Version floor vulnerability in requirements.txt (MEDIUM, cross-cutting)

**Neo identified critical testing gap:**
- 22 mock-based regression tests needed to protect PR#1 and PR#2 fixes
- Critical gating test: exception safety cleanup (fails until try/finally is added)

**Team consensus:** Full-audit summary merged into `.squad/decisions.md`. Morpheus is architecting Phase 3 (code fixes) to follow Neo's test infrastructure (Phase 2) and Trinity's version-floor tightening (Phase 1).

### 2026-03-25 — PR #4 Code Review: try/finally + accelerate version floor

Reviewed `squad/pr3-high-memory-fixes` (Trinity's work). Both HIGH-severity issues are correctly fixed.

**try/finally analysis:**
- All five pipeline variables (`base`, `refiner`, `latents`, `text_encoder_2`, `vae`) initialized to `None` before `try`. `finally` deletes all five unconditionally — safe even when `base=None` mid-refine.
- The inline `del base; base = None` inside the refiner path is intentional load-order management (frees VRAM before `load_refiner()`), NOT duplicate cleanup. Setting `base = None` makes the `finally` deletion a safe no-op. Pattern is correct.
- `image` is intentionally excluded from `finally` cleanup — needed for the post-finally `image.save()` call. PIL image leak (LOW) is a known open issue, out of scope here.
- `torch.cuda.empty_cache()` called unconditionally in `finally` — correct, it's a no-op without CUDA. `torch.mps.empty_cache()` guarded by `is_available()` — also correct.
- Exception propagates correctly: if an exception fires inside `try`, `finally` cleans up, then exception propagates up. `image.save()` is unreachable in the exception path.
- Happy path unchanged: try completes, finally cleans pipelines, image is still live for save.

**requirements.txt analysis:**
- `accelerate>=0.24.0` — the critical fix. Versions below 0.24.0 silently skip CPU offload hook deregistration on `del pipe`, making PR#1's entire cleanup strategy inert.
- `diffusers>=0.21.0`, `torch>=2.1.0` — appropriate tightening.
- `transformers>=4.30.0` — not changed, within scope. No known equivalent hook regression.

**Remaining open (out of scope for this PR):** torch.compile dynamo cache reset (MEDIUM), entry-point VRAM flush (MEDIUM), latents tensor CPU transfer before refiner load (MEDIUM), PIL image cleanup (LOW).

**Decision:** APPROVED.

### 2026-03-25 — PR #8: README Update (MPS Support, Testing, Memory Model, Batch Gen) — MERGED

**Sprint:** CI, README, TDD Sprint

**Changes made:**
- Added MPS support section with device detection guidance
- Updated Testing section with pytest instructions and test counts (22 regression tests)
- Documented memory management model (try/finally cleanup, inter-item cache flush, exception safety)
- Added Batch Generation feature overview
- Scoped pytest command to `pytest tests/test_memory_cleanup.py -v` (22 green tests only, avoiding TDD red-phase failures)

**Review flow:**
1. Trinity reviewed PR #8: APPROVED (all technical claims verified accurate)
2. Neo reviewed PR #8: REJECTED (initial pytest command showed 22 failures from TDD red-phase tests)
3. Trinity fixed scoping on `squad/readme-update` branch (commit scoped to test_memory_cleanup.py)
4. Neo re-reviewed PR #8 after fix: APPROVED
5. PR #8 merged to main (squash)

**Status:** ✅ MERGED

**Architectural note:** README now correctly explains the memory model and batch generation as design decisions, not just features. Readers understand why `generate()` flushes GPU state and how batch workflows should manage inter-iteration cleanup.
