# Trinity — PR #5: MEDIUM Memory Fixes

**Date:** 2026-03-25  
**Branch:** `squad/pr5-medium-memory-fixes`  
**PR:** https://github.com/dfberry/image-generation/pull/5  
**Implementer:** Trinity

---

## What Was Changed

All changes are in `generate.py` only.

### Fix 1 — Latents tensor live during cache flush (lines 153–156, 172–173)

**Problem:** After base inference, `latents` is a GPU tensor still live when `torch.cuda.empty_cache()` / `torch.mps.empty_cache()` runs after `del base`. The cache flush can't reclaim that VRAM because the tensor is still referenced.

**Fix:** Added `latents = latents.cpu()` immediately after extracting `text_encoder_2` / `vae` and before `del base`. This moves the tensor off GPU before the cache flush window opens, so `empty_cache()` can reclaim all base model VRAM. When passing latents to the refiner, `latents.to(device)` moves it back for inference. Guard is `device in ("cuda", "mps")` — CPU path is unaffected.

### Fix 2 — torch.compile dynamo cache survives del base (lines 195–200)

**Problem:** `load_base()` calls `torch.compile(pipe.unet)` on CUDA. This populates `torch._dynamo`'s process-global graph cache. `del base` drops the Python reference but the dynamo cache remains, accumulating across repeated `generate()` calls.

**Verification:** Confirmed `torch.compile` IS used — line 75 in `load_base()`, CUDA only. Fix is correctly scoped to CUDA.

**Fix:** Added `torch._dynamo.reset()` at the end of the `finally` block, guarded by `device == "cuda" and hasattr(torch, "_dynamo")`. The `hasattr` guard future-proofs against torch versions where `_dynamo` isn't present. Comment notes that if `torch.compile` is extended to other devices, the guard should be broadened.

### Fix 3 — No entry-point VRAM flush before pipeline load (lines 104–110)

**Problem:** No cache flush at the top of `generate()` before pipeline loads. Back-to-back calls (e.g. from `generate_blog_images.sh`) start loading new pipelines while residual GPU memory from the previous call hasn't been reclaimed.

**Fix:** Added `gc.collect()` + `torch.cuda.empty_cache()` + guarded `torch.mps.empty_cache()` at the very start of `generate()`, immediately after device detection. Consistent with existing pattern for MPS guard.

### Fix 4 — Global state compounding across calls (no code change)

**Finding:** Audited `generate.py` for module-level or global state. All pipeline objects (`base`, `refiner`, `latents`, `text_encoder_2`, `vae`) are local variables inside `generate()`. No module-level pipeline objects, no global counters, no cached references outside the function. The codebase is clean. No fix required.

---

## Why These Fixes Matter

These are all relevant in the `generate_blog_images.sh` batch context where `generate()` is called 5+ times in a loop. Fix 3 ensures each call starts with a clean VRAM slate. Fix 1 maximizes the memory reclaimed between pipeline stages within each call. Fix 2 prevents dynamo cache growth that would compound over the lifetime of the process.
