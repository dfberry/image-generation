# Cooper — History

## Project Context (seeded 2026-03-23)

- **Repo:** image-generation — SDXL image generation tool
- **Owner:** dfberry
- **Stack:** Python, diffusers, torch, SDXL base + refiner, MPS/CUDA/CPU
- **Main file:** generate.py
- **Key docs:** docs/blog-image-generation-skill.md

## Core Decisions Known

- MPS memory leak fixed (2026-03-23): 5 root causes resolved — shared vae/text_encoder_2, base teardown, gc.collect(), torch.mps.empty_cache(), fp16 for MPS, cpu_offload for MPS
- Performance after fix: ~70s/step on MPS vs 3.5 min/step before
- No text/letters in prompts (SDXL renders as noise)
- Backlit silhouette preferred for human figures
