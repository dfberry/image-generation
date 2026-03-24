# Trinity PR #3 — High-Severity Memory Audit Fixes

**Date:** 2026-03-25
**Branch:** `squad/pr3-high-memory-fixes`
**PR:** https://github.com/dfberry/image-generation/pull/4

---

## What Was Changed

### Fix 1 — `try/finally` in `generate()` (generate.py)

**Problem:** The entire inference body had no exception handling. Any OOM error, `KeyboardInterrupt`, or runtime failure left `base`, `refiner`, `latents`, `text_encoder_2`, and `vae` stranded in VRAM. All cleanup code from PR #1 and PR #2 was happy-path only.

**Fix:** Initialized all pipeline variables to `None` before the try block (`base = refiner = latents = text_encoder_2 = vae = image = None`). Wrapped the inference body in `try/finally`. The `finally` block unconditionally deletes all five variables, calls `gc.collect()`, calls `torch.cuda.empty_cache()`, and calls `torch.mps.empty_cache()` guarded by `torch.backends.mps.is_available()`.

The inline `del base; base = None` in the refiner path was preserved inside the try block — this frees VRAM *before* `load_refiner()` is called, which is a load-ordering requirement, not just cleanup. Setting `base = None` after the inline del ensures the finally-block del is a safe no-op on the happy path. The inline mid-path cache clears (between del base and load_refiner) were also preserved for the same reason.

### Fix 2 — Version floors in `requirements.txt`

**Problem:** `accelerate>=0.20.0` allowed versions where CPU offload hooks are never deregistered on `del pipe`, silently defeating PR #1's entire cleanup strategy. `diffusers>=0.19.0` and `torch>=2.0.0` had similar stability gaps.

**Fix:**
- `accelerate>=0.20.0` → `accelerate>=0.24.0` (CPU offload hook deregistration fixed in 0.24.0)
- `diffusers>=0.19.0` → `diffusers>=0.21.0` (attention cache fix)
- `torch>=2.0.0` → `torch>=2.1.0` (MPS backend stability floor)

---

## Why These Two Fixes Now

The team audit in `.squad/decisions.md` classified these as HIGH severity. They are prerequisites — without the version floor fix, the existing cleanup code from PR #1 may silently do nothing; without try/finally, any exception during the ~30–60s inference window strands several GB in VRAM with no recovery path until process exit.
