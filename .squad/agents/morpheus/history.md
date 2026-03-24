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
