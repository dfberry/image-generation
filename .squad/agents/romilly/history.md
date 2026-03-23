# Romilly — History

## Project Context (seeded 2026-03-23)

- **Repo:** image-generation — SDXL image generation tool
- **Owner:** dfberry
- **Main file:** generate.py
- **Stack:** Python, diffusers, torch, SDXL

## Memory Leak Fix (2026-03-23)

Five root causes fixed in generate.py:
1. Both base (~7GB) and refiner (~5GB) loaded into MPS simultaneously → fixed by extracting text_encoder_2/vae from base, deleting base, then loading refiner with shared refs
2. No torch.mps.empty_cache() calls → Metal GPU memory fragmented
3. No gc.collect() calls → Python allocator held freed tensors
4. fp32 used on MPS instead of fp16 → 2x VRAM waste; fixed by adding MPS to variant="fp16" condition
5. enable_model_cpu_offload() only called for CPU, not MPS → extended to include MPS

Performance after fix: step 1 ~19s (warmup), steps 2+ ~70s each on MPS.
PR #1 created and merged.

## Key file locations
- `generate.py` — main generation script (lines 11, 64, 66-68, 80, 136-142, 154-157, 169-172 contain the fixes)
- `docs/blog-image-generation-skill.md` — prompt engineering skill doc
- `outputs/` — generated images land here
