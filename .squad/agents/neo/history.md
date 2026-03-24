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

### 2026-03-23 — Memory Audit of generate.py

**Finding: Zero test coverage exists.** There is no `tests/` directory and no project-owned test files. The "Plan: Test Coverage for Memory Fixes" in decisions.md is documented but not implemented.

**Critical gap — no try/finally in generate().** If an exception is thrown after `del base` but before `del refiner` in the refine path, `text_encoder_2`, `vae`, `latents`, and `refiner` are never freed. This is the highest-risk untested scenario.

**Shared object lifetime is subtle.** `del text_encoder_2, vae` in generate() only removes local aliases. If the refiner pipeline holds internal strong references, the objects survive until the refiner itself is deleted. The ordering (`del latents, refiner` before `del text_encoder_2, vae`) is important but untested.

**All 12 memory behaviors are untested:** fp16 variant gating, cpu offload routing, `pipe.to(device)`, `del base`, MPS cache clear, CUDA cache clear, `gc.collect()`, `del latents/refiner`, `del text_encoder_2/vae`, generator CPU binding, `torch.compile` gating, shared component transfer.

**Cannot test without GPU:** real VRAM measurement, actual OOM triggering, MPS memory counters, `torch.compile` benefit, CPU offload effectiveness on constrained VRAM.

**Proposed suite:** ~22 mock-based tests across 5 files (`test_device.py`, `test_load_base.py`, `test_load_refiner.py`, `test_generate.py`, `test_edge_cases.py`). Full test function names and assertions written in `.squad/decisions/inbox/neo-memory-audit.md`.

---

### 2026-03-24 — Cross-Agent Audit Sync + Implementation Roadmap

Neo's test-gap analysis converged with Morpheus's architectural audit and Trinity's code-level review:

**All three agents independently identified the same 4 core issues:**
1. No exception safety (HIGH) — Neo's critical test gap matches Morpheus and Trinity's findings
2. torch.compile cache (MEDIUM) — All three identified it
3. Latents tensor overlap (MEDIUM) — All three identified it
4. Entry-point cache flush (MEDIUM) — All three identified it

**Neo's unique findings:**
- **Zero test coverage** — Complete absence of regression tests for PR#1 and PR#2 fixes
- **12 untested memory behaviors** — All device/offload/cache/gc patterns untested
- **22-test regression suite** — Specific test functions and fixtures ready to implement
- **Critical gating test** — `test_generate_refine_path_cleans_up_on_refiner_exception` FAILS until try/finally is added; serves as pass/fail gate for Issue #1 fix

**Recommended phases:**
1. **Phase 1 (Trinity):** Tighten requirements.txt version floors (prerequisite)
2. **Phase 2 (Neo):** Create test infrastructure, 22 regression tests (most fail initially)
3. **Phase 3 (Morpheus):** Fix code in severity order (failures in Phase 2 guide fixes)
4. **Phase 4:** Verify all tests pass, team review and merge

**Team consensus:** All findings merged into `.squad/decisions.md`. Neo will provide detailed test implementation plan before Phase 2 kicks off.
