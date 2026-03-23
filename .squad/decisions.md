# Team Decisions

## Architecture

- **SDXL pipeline:** Uses base model + refiner. Base runs 32 steps, refiner 8 steps.
- **MPS support:** fp16 variant used for Apple Silicon (MPS) to halve VRAM usage.
- **Memory management:** gc.collect() + torch.mps.empty_cache() called after base teardown and after refiner. enable_model_cpu_offload() applied for both CPU and MPS.
- **Base teardown before refiner:** text_encoder_2 and vae extracted from base, base deleted, then refiner loaded with shared refs — prevents both models living in memory simultaneously.

## Prompt Engineering

- **No text/letters:** Never include text, letters, words, or signs in image prompts. SDXL renders them as visual noise.
- **Figure representation:** Use "dark silhouette figure backlit" for people — most reliable featureless result on SDXL.
- **No arm/hand action verbs:** Avoid holding, reaching, extending, pointing — causes anatomically wrong renders. Use props on surfaces instead.
- **Token limit:** SDXL CLIP truncates at 77 tokens. Keep prompts concise; put critical terms first.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
