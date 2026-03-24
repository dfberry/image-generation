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

### 2026-03-25 — PR #3: try/finally cleanup guard + accelerate version floor

- **try/finally pattern for pipeline cleanup:** Initialize `base = refiner = latents = text_encoder_2 = vae = image = None` before the try block. The inline `del base; base = None` in the refiner path must stay inside try (not moved to finally) because it frees VRAM before `load_refiner()` — ordering is load-order-dependent. The finally block catches everything else: any variable still non-None gets deleted, then gc.collect() and both CUDA/MPS cache clears run unconditionally.
- **`del` on None is safe:** Python's `del` on a None-valued local just removes the binding. No NameError. This makes the "initialize to None, delete in finally" pattern clean and reliable.
- **`torch.cuda.empty_cache()` is safe to call even without CUDA:** Unlike `torch.mps.empty_cache()`, the CUDA variant doesn't raise if no CUDA device is present — it's a no-op. The MPS call still needs an `is_available()` guard because it will raise on non-Apple hardware.
- **Version floors are prerequisites, not optional hygiene:** `accelerate<0.24.0` silently breaks the CPU offload deregistration path. This isn't a "might cause issues" risk — it means PR#1's entire cleanup strategy is inert on older accelerate. Always audit version floors as part of any memory management PR.

<!-- Append new learnings below. Each entry is something lasting about the project. -->

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
