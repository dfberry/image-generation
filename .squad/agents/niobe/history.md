# Niobe — History

## Project Context

- **Project:** image-generation — Python CLI tool using Stable Diffusion XL (SDXL) to generate blog post illustrations with a tropical magical-realism aesthetic.
- **Stack:** Python 3.10+, diffusers, transformers, torch, Pillow
- **Owner:** dfberry
- **Key files:** generate.py (main pipeline), outputs/ (generated images), requirements.txt
- **Joined:** 2026-03-26

## Learnings

### Pipeline Review — 2026-03-26

**Reviewed:** `generate.py` full diffusers pipeline, `requirements.txt`, `prompts/examples.md`, `generate_blog_images.sh`, test suite.

**Architecture:** SDXL base 1.0 + optional refiner 1.0, using `DiffusionPipeline.from_pretrained`. Shares `text_encoder_2` and `vae` between base and refiner (correct VRAM optimization). 80/20 denoising split via `denoising_end`/`denoising_start`. Memory management is solid — try/finally cleanup, gc.collect, device cache flushes, latents CPU transfer during refiner load, dynamo reset.

**What's good:**
- Resolution 1024×1024 is SDXL native — correct
- fp16 variant on GPU, float32 on CPU — correct
- Component sharing between base/refiner saves ~1.5GB VRAM
- torch.compile on CUDA UNet for 20-30% speedup
- Comprehensive OOM detection (CUDA + MPS) with retry logic
- Batch generation with inter-item GPU memory flushes

**Findings by severity:**

| # | Severity | Finding |
|---|----------|---------|
| 1 | **HIGH** | No negative prompt support — single biggest quality win available for SDXL |
| 2 | **HIGH** | No explicit scheduler — relies on model default (EulerDiscrete). DPMSolverMultistepScheduler at 25-30 steps matches quality of current 40-step Euler, ~35% faster |
| 3 | **MEDIUM** | Refiner uses same guidance_scale as base (7.5). Refiner benefits from lower CFG (~5.0) to avoid over-sharpened fine details |
| 4 | **MEDIUM** | CUDA uses `pipe.to("cuda")` not `enable_model_cpu_offload()` — loads full model to VRAM. Fine for >=16GB cards, risky on 8-12GB |
| 5 | **MEDIUM** | `torch.compile(fullgraph=True)` is aggressive — can cause compilation failures on some torch versions. Safer without `fullgraph=True` |
| 6 | **MEDIUM** | `batch_generate()` hardcodes steps=40, guidance=7.5, refine=False — no per-item override |
| 7 | **MEDIUM** | `batch_generate()` defaults `device="mps"` — platform-specific, should auto-detect |
| 8 | **LOW** | `prompts/examples.md` recommends guidance=8.0 for "best quality" — SDXL sweet spot is 5.0-7.5, >8.0 causes oversaturation |
| 9 | **LOW** | No `enable_vae_slicing()` — would reduce peak VRAM during decode, especially for batch |
| 10 | **LOW** | No `torch.inference_mode()` wrapper — already noted by team as LOW priority |

**Key paths:** `generate.py` (pipeline), `generate_blog_images.sh` (batch script), `prompts/examples.md` (parameter recommendations), `tests/conftest.py` (mock infrastructure).

**Team has already fixed:** try/finally cleanup (PR#4), entry-point VRAM flush (PR#5), latents CPU transfer (PR#5), dynamo reset (PR#5), PIL leak (PR#6), version floors (PR#4). Memory management is now solid.

### D2 Pipeline & GPU Safety Review — 2026-03-27

**Scope:** Full D2 (Pipeline & GPU) audit of `generate.py` — 16-point checklist.

**Verdict:** SOUND — 0 CRITICAL, 1 HIGH, 3 MEDIUM, 3 LOW, 5 INFO.

**Key findings:**
- HIGH: `batch_generate()` still defaults `device="mps"` — platform-specific API defect (L360)
- MEDIUM: `safety_checker = None` undocumented on both pipelines (L148, L173)
- MEDIUM: `torch.compile(fullgraph=True)` is fragile to diffusers updates (L126)
- LOW: Inconsistent cache flush guarding (finally unconditional vs pre-flight guarded)
- LOW: Inconsistent `hasattr(torch.backends, "mps")` usage across call sites
- All HIGH findings from initial review (2026-03-26) confirmed FIXED through PRs #4–#8.

**What passed cleanly:** Device detection order, dtype selection, fp16 variant logic, MPS-only cpu_offload, xFormers fallback chain, scheduler config preservation, Karras sigmas scoping, LoRA loading, latents CPU transfer, generator device binding, OOM detection, 80/20 refiner split, cpu_offload/generator safety.

**Report:** `.squad/decisions/inbox/niobe-pipeline-review.md`
