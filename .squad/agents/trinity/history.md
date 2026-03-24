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

### 2026-03-25 — PR #3: try/finally cleanup guard + accelerate version floor

- **try/finally pattern for pipeline cleanup:** Initialize `base = refiner = latents = text_encoder_2 = vae = image = None` before the try block. The inline `del base; base = None` in the refiner path must stay inside try (not moved to finally) because it frees VRAM before `load_refiner()` — ordering is load-order-dependent. The finally block catches everything else: any variable still non-None gets deleted, then gc.collect() and both CUDA/MPS cache clears run unconditionally.
- **`del` on None is safe:** Python's `del` on a None-valued local just removes the binding. No NameError. This makes the "initialize to None, delete in finally" pattern clean and reliable.
- **`torch.cuda.empty_cache()` is safe to call even without CUDA:** Unlike `torch.mps.empty_cache()`, the CUDA variant doesn't raise if no CUDA device is present — it's a no-op. The MPS call still needs an `is_available()` guard because it will raise on non-Apple hardware.
- **Version floors are prerequisites, not optional hygiene:** `accelerate<0.24.0` silently breaks the CPU offload deregistration path. This isn't a "might cause issues" risk — it means PR#1's entire cleanup strategy is inert on older accelerate. Always audit version floors as part of any memory management PR.

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-25 — PR #5: MEDIUM memory fixes (latents CPU transfer, dynamo reset, entry-point flush, global state audit)

- **latents.cpu() before cache flush is the correct fix for the GPU-pin problem:** Moving the latents tensor to CPU before `del base` / `empty_cache()` lets the cache flush reclaim all base model VRAM. Moving back with `latents.to(device)` at refiner call site is clean and explicit. Guard on `device in ("cuda", "mps")` — no-op on CPU path.
- **torch._dynamo.reset() belongs in the finally block, CUDA-guarded:** `torch.compile` is only applied on CUDA (in `load_base()`), so the dynamo reset is correctly scoped to `device == "cuda"`. The `hasattr(torch, "_dynamo")` guard protects against torch versions without the attribute. If `torch.compile` is ever extended to MPS or other devices, the guard must be broadened.
- **Entry-point flush pattern mirrors the finally pattern:** `gc.collect()` first, then CUDA unconditional, then MPS guarded. Consistent with the existing `finally` cleanup so it's easy to audit both at once.
- **Global state audit finding:** `generate.py` has zero module-level pipeline objects or accumulating global state. All pipeline vars are locals inside `generate()`. This is the right architecture for a CLI tool called in batch — no risk of cross-call contamination from Python-level references.
### 2026-03-25 — PR #5: MEDIUM Memory Fixes Delivered & Approved

Delivered all 4 MEDIUM-severity fixes in `squad/pr5-medium-memory-fixes`. Approved by Morpheus (Lead).

**Fixes implemented:**
1. **Latents CPU Transfer:** `latents.cpu()` before `del base` and cache flush. Device transfer back via `latents.to(device)` (MPS-aware). Guard: `if device in ("cuda", "mps")`.
2. **Dynamo Cache Reset:** `torch._dynamo.reset()` in finally block, guarded by `device == "cuda" and hasattr(torch, "_dynamo")`.
3. **Entry-Point VRAM Flush:** Added `gc.collect()`, `torch.cuda.empty_cache()` (CUDA-guarded), `torch.mps.empty_cache()` (MPS-guarded) at start of `generate()`.
4. **Global State Audit:** Verified all pipeline variables are locals. Zero process-persistent references. Clean.

**Tests:** Neo added 9 new MEDIUM tests. All 22 tests pass (~5.9s, no GPU). Call-order tracking validates fixes 1, 2, 3 at the code level.

**Review verdict:** APPROVED. All fixes correct. Code logic sound. Follow-up (not blocking): Neo to fix orphaned assert message patterns in 3 tests.

### 2026-03-23 — Memory Audit of generate.py (post PR#1, PR#2)

- **No exception-safe cleanup (HIGH):** `generate()` has no `try/finally` blocks. Any mid-inference exception leaves `base`, `refiner`, `latents`, `text_encoder_2`, and `vae` allocated in VRAM. Must wrap each pipeline load+call pair in try/finally.
- **torch.compile cache survives del (MEDIUM):** On CUDA, `torch.compile(pipe.unet)` populates `torch._dynamo`'s graph cache. `del base` drops the Python reference but the compiled graph stays cached. Call `torch._dynamo.reset()` after deletion on CUDA when compile was used.
- **Latents tensor holds GPU ref through cache-clear window (MEDIUM):** In the refiner path, `latents` is a CUDA tensor still live when `torch.cuda.empty_cache()` runs after `del base`. `empty_cache()` can't free it. Pin latents to CPU before loading refiner, move back to device when passing to refiner.
- **PIL image not freed after save (LOW):** `image` (~4MB) is never `del`'d after `image.save()`. Fine for single runs; accumulates in batch/loop contexts.
- **requirements.txt floors too low (MEDIUM):** `accelerate>=0.20.0` allows versions where CPU offload hooks are NOT deregistered on model delete — this directly undermines PR#1's cleanup. Safe floors: `accelerate>=0.24.0`, `diffusers>=0.21.0`, `torch>=2.1.0`.
- **No outer torch.no_grad() (LOW):** Diffusers handles it internally, but an explicit outer context is defensive hygiene against future hooks or wrappers.

---

### 2026-03-24 — Cross-Agent Audit Sync

Trinity's code-level audit converged with Morpheus's architectural review and Neo's test-gap analysis:

**All three agents independently identified the same 4 core issues:**
1. No exception safety (HIGH) — Trinity's detail matches Morpheus and Neo's critical test gap
2. torch.compile cache (MEDIUM) — Trinity and Morpheus both found it
3. Latents tensor GPU ref (MEDIUM) — Trinity emphasized "can cause OOM at large resolutions"
4. Entry-point cache flush (MEDIUM) — Trinity and Morpheus both found it

**Trinity's unique findings:**
- Defensive `torch.no_grad()` wrapping (LOW) — subtle but defensible hygiene
- **requirements.txt version floors (MEDIUM)** — Critical prerequisite: `accelerate>=0.24.0` (PR#1's offload hooks), `diffusers>=0.21.0` (attention cache), `torch>=2.1.0` (MPS backend). Without these, code fixes can't be relied upon.

**Neo identified critical testing gap:**
- 22 regression tests catch reversion of PR#1 and PR#2 fixes
- Exception safety test fails until try/finally is added

**Team consensus:** Trinity's version-floor fix must run in Phase 1 (prerequisite). Then Neo's test infra (Phase 2), then Morpheus's code fixes (Phase 3). All merged into `.squad/decisions.md`.

## Learnings

### 2026-03-25 — PR #6: PIL Image Leak Fix (LOW)

- **image.save() inside try is the right pattern:** Keeping the save inside the `try` block lets the `finally` clause null out `image` unconditionally. This closes the window where PIL's uncompressed pixel buffer (~4MB) lingers in scope after cleanup.
- **`if image is not None` guard is essential:** On exception paths (OOM, interrupt, inference failure), `image` stays `None`. The guard prevents an AttributeError on None and makes intent explicit — the save is a conditional success-path action, not an unconditional epilogue.
- **`image = None` vs `del image`:** Used `image = None` (not `del image`) in `finally` to match the initialize-to-None pattern established in PR#4. `del` would remove the binding; `= None` keeps the variable in scope but releases the PIL reference — consistent with how the block already handles `base = None` after inline deletion.
- **Return after finally is clean:** `return output_path` sits after the `try/finally` and is unaffected by the restructuring. The function still returns the path whether or not the save succeeded (caller decides what to do with that).

### 2026-03-25 — CI Workflow: Manual-Dispatch Test Runner

- **`workflow_dispatch` only is the correct CI trigger when minutes are scarce:** No `push` or `pull_request` triggers. The workflow only runs when manually invoked from the Actions tab. This is a deliberate cost-control decision, not a limitation.
- **CPU-only torch install for CI:** `--index-url https://download.pytorch.org/whl/cpu` pulls the CPU wheel (~180MB vs ~2GB GPU). Since all tests mock the pipeline, no GPU is needed and this dramatically reduces install time.
- **Matrix strategy on Python 3.10 and 3.11:** Both versions this project targets get validated on every manual run. No caching, no artifacts — keeps the workflow simple and the YAML minimal.
- **Tests run in ~2 seconds with mocks:** The full suite (22 tests in `tests/test_memory_cleanup.py` + `tests/conftest.py`) uses `unittest.mock` throughout. No model downloads, no GPU, no external calls.
- **Branch naming collision:** Created `squad/ci-manual-dispatch` but the working tree was on `squad/readme-update` due to a pre-existing local branch. Fixed by force-pushing the commit ref directly: `git push origin squad/readme-update:squad/ci-manual-dispatch --force`.
- **PR #7:** https://github.com/dfberry/image-generation/pull/7

### 2026-03-25 — PR #8: README Testing Section Fix

Fixed Neo's rejection of PR #8 by updating the pytest command and Testing section description in README.md:

**Problem:** PR #9 added TDD red-phase tests (batch_generation, OOM handling) that intentionally fail. Running `pytest tests/` now shows 53 tests, not 22. Users see 22 failures and think the project is broken.

**Solution:**
- Scoped the main command to `pytest tests/test_memory_cleanup.py -v` (the 22 regression tests that pass)
- Added secondary command `pytest tests/ -v` with context that TDD suites are expected to have failing tests
- Updated descriptive text to clarify: "Regression tests (stable)" vs "TDD suites (in development)"
- Verified all 22 tests pass in 1.88s, no GPU required

**Commit:** `83ea71b` to `squad/readme-update`  
**Status:** Approved. Tests verified. Ready for Neo's re-review.

### 2026-03-25 — CI, README, TDD Sprint: Orchestration Complete

**Sprint Completion:**

| PR | Agent | Task | Status |
|----|-------|------|--------|
| #7 | Trinity | Create workflow_dispatch CI | ✅ MERGED |
| #8 | Morpheus | Update README (MPS, testing, memory model, batch gen) | ✅ MERGED |
| #9 | Neo | Write TDD test suite (batch_generate, OOMError) | 🔴 RED (22 tests fail, 31 green) |

**Execution:**
- Trinity created `.github/workflows/tests.yml` (CPU torch, Python 3.10/3.11, ~2s runtime)
- Morpheus updated README with MPS support, testing section, memory model, batch generation docs
- Initial PR #8 pytest command failed (would show 22 TDD red-phase failures)
- Trinity scoped pytest to `test_memory_cleanup.py` (22 green tests only) on `squad/readme-update` branch
- Neo re-reviewed PR #8 after scope fix: APPROVED
- PR #8 merged to main (squash)
- Neo wrote 34 new tests: 17 batch_generate(), 17 OOMError (9 pass, 22 red)
- PR #9 opened on `squad/tdd-batch-oom-tests`, awaits Trinity implementation

**Test Status:**
| File | Red | Green |
|------|-----|-------|
| test_batch_generation.py | 17 | 0 |
| test_oom_handling.py | 5 | 9 |
| test_memory_cleanup.py | 0 | 22 |
| **Total** | **22** | **31** |

**Next:** Trinity implements batch_generate() and OOMError to pass PR #9.
