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
