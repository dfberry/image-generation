# Phase 2 Decomposition: Image-to-Image & Enhancement

**Author:** Morpheus (Lead)  
**Date:** 2026-05-06  
**Status:** PROPOSED  
**Ref:** Issue #106 — Feature Roadmap, Phase 2  
**Prerequisite:** Phase 1 (provider abstraction, FLUX.1, SD3 Medium, --model flag) ✅ DONE

---

## Architecture Context

Phase 1 established the `providers/` package with `BaseProvider` → `generate()` → `GenerationConfig` pattern. Phase 2 must extend this pattern to support **input images** (not just text prompts). The key architectural choice:

> **Extend `GenerationConfig` with an optional `input_image` field** and add a new `enhance()` method to the base provider (or create a separate `BaseEnhancer` ABC for tools like Real-ESRGAN that don't do diffusion).

---

## Work Items (ordered by dependency)

| # | Title | Owner | Depends On | Est. Size |
|---|-------|-------|-----------|-----------|
| 1 | Extend BaseProvider for img2img support | Trinity | — | M |
| 2 | SDXL img2img provider implementation | Trinity | #1 | L |
| 3 | Real-ESRGAN upscaling provider | Trinity | #1 | M |
| 4 | Style Transfer presets (LoRA-based) | Niobe | #2 | M |
| 5 | Test suite for Phase 2 features | Neo | #2, #3 | L |

---

## Issue 1: Extend BaseProvider for img2img support

**Owner:** Trinity  
**Dependencies:** None (builds on existing provider abstraction)

**Scope:**
- Add `input_image: Optional[Image.Image]` and `strength: float = 0.75` fields to `GenerationConfig`
- Add `--input` CLI argument to `generate.py` (loads a PNG/JPEG and passes it into config)
- Add `--strength` CLI argument (controls how much the input image is modified, 0.0–1.0)
- Add input image validation (file exists, valid image format, reasonable dimensions)
- Update `parse_args()` with clear help text: "Path to an image to transform (enables img2img mode)"

**CLI Interface:**
```bash
# img2img mode (implicit — detected by presence of --input)
python generate.py --prompt "add tropical flowers" --input my-photo.png
python generate.py --prompt "make it dreamy" --input photo.png --strength 0.6
```

**Acceptance Criteria:**
- [ ] `GenerationConfig` has `input_image` and `strength` fields
- [ ] `--input` and `--strength` flags parse correctly
- [ ] Invalid image paths produce friendly error messages (not tracebacks)
- [ ] Passing `--input` without `--prompt` fails with helpful message
- [ ] Existing text-to-image still works identically (no regression)
- [ ] Unit tests for new CLI args and validation logic (mock-based, no GPU)

---

## Issue 2: SDXL img2img provider implementation

**Owner:** Trinity  
**Dependencies:** Issue #1

**Scope:**
- Implement img2img path in `SDXLProvider.generate()` (detect `config.input_image is not None`)
- Use `StableDiffusionXLImg2ImgPipeline` from diffusers when input image is present
- Handle strength parameter (maps to diffusers `strength` kwarg)
- Reuse existing OOM retry with step-halving logic
- Share VAE/text encoders with existing text-to-image pipeline where possible
- Handle dimension mismatch (resize input to target w×h if needed, warn user)

**CLI Interface:**
```bash
python generate.py --model precise --prompt "tropical sunset version" --input photo.png --strength 0.7
python generate.py --model precise --prompt "oil painting style" --input sketch.png --steps 30
```

**Acceptance Criteria:**
- [ ] `SDXLProvider` loads img2img pipeline when `input_image` is set
- [ ] `strength` parameter controls transformation intensity (0.1 = subtle, 0.9 = dramatic)
- [ ] OOM retry works for img2img (same pattern as text2img)
- [ ] Input images of arbitrary sizes are handled (resized + warned)
- [ ] GPU memory is cleaned up properly (same lifecycle as text2img)
- [ ] Works on CUDA, MPS, and CPU (with CPU being slow but functional)

---

## Issue 3: Real-ESRGAN upscaling provider

**Owner:** Trinity  
**Dependencies:** Issue #1 (uses the `--input` flag)

**Scope:**
- Create `providers/enhancer.py` with `BaseEnhancer` ABC (separate from diffusion providers)
- Create `providers/realesrgan.py` implementing `BaseEnhancer`
- Use `realesrgan` PyPI package (wraps official Real-ESRGAN, torch-based, free)
- Add `--enhance` flag to CLI: standalone mode (no prompt needed)
- Support 2× and 4× upscaling via `--scale` flag (default 4×)
- Output naming: `{input_stem}_enhanced.png`

**CLI Interface:**
```bash
# Upscale a low-res image (no prompt needed)
python generate.py --enhance my-image.png
python generate.py --enhance my-image.png --scale 2
python generate.py --enhance my-image.png --output hi-res-version.png
```

**Acceptance Criteria:**
- [ ] `--enhance` flag works standalone (no --prompt required)
- [ ] Default 4× upscaling produces visually sharp output
- [ ] `--scale 2` option works for lighter processing
- [ ] Output file naming is intuitive (auto-suffixed or user-specified)
- [ ] Handles various input formats (PNG, JPEG, WebP)
- [ ] Memory management: model loaded → process → cleanup (no VRAM leak)
- [ ] Error messages are plain English (no "tensor shape mismatch" gibberish to users)
- [ ] `requirements.txt` updated with `realesrgan` dependency

---

## Issue 4: Style Transfer presets (LoRA-based)

**Owner:** Niobe (quality/tuning)  
**Dependencies:** Issue #2 (needs img2img working)

**Scope:**
- Create `providers/styles.py` with a preset registry mapping friendly names → LoRA model IDs
- Initial presets: `watercolor`, `oil-painting`, `sketch`, `anime`, `pixel-art`
- Add `--style` CLI flag that auto-applies the correct LoRA + appropriate strength/guidance defaults
- `--style` implies img2img mode: requires `--input` (error if missing)
- Each preset bundles: LoRA ID, default strength, recommended guidance scale, suggested negative prompt additions
- Curate 5 open-source LoRA models from Hugging Face (Civitai-hosted models are NOT allowed — HF-hosted only)

**CLI Interface:**
```bash
# Apply a style preset (user-friendly, no LoRA knowledge needed)
python generate.py --style watercolor --input photo.png
python generate.py --style oil-painting --input photo.png --prompt "autumn forest"
python generate.py --style anime --input selfie.png --strength 0.8

# List available styles
python generate.py --list-styles
```

**Acceptance Criteria:**
- [ ] `--style watercolor` works end-to-end with default settings
- [ ] All 5 presets produce visually distinct outputs
- [ ] `--list-styles` shows a pretty table of available styles with descriptions
- [ ] Style presets are stored in a single registry file (easy to add more later)
- [ ] Users can combine `--style` with `--prompt` for additional creative direction
- [ ] Strength/guidance defaults per-style produce good results without user tuning
- [ ] LoRA weights are downloaded from HF on first use (auto-cached, free)

---

## Issue 5: Test suite for Phase 2 features

**Owner:** Neo  
**Dependencies:** Issues #2 and #3 (needs implementations to test)

**Scope:**
- Unit tests for img2img config parsing and validation
- Unit tests for Real-ESRGAN enhancer lifecycle (mock-based)
- Unit tests for style preset registry and flag parsing
- Integration test stubs for end-to-end img2img pipeline (GPU-optional, mocked)
- Edge cases: invalid image paths, corrupt images, unsupported formats, 0-byte files
- OOM retry tests adapted for img2img path

**Acceptance Criteria:**
- [ ] All tests pass on CPU-only machines (no torch/GPU import at module level)
- [ ] Coverage for new CLI flags (--input, --strength, --enhance, --scale, --style)
- [ ] Coverage for error paths (bad file, wrong format, missing input with --style)
- [ ] Follows existing test patterns: mock-based, uses `_ensure_heavy_imports` guard
- [ ] Minimum 30 new test cases across the 3 features
- [ ] `make test` passes with no regressions to existing 170 tests

---

## Dependency Graph

```
Issue #1 (BaseProvider extension)
    ├── Issue #2 (SDXL img2img)
    │       └── Issue #4 (Style presets)
    ├── Issue #3 (Real-ESRGAN)
    └── Issue #5 (Test suite) ← waits for #2 + #3
```

## Implementation Order

1. **Issue #1** — Foundation (unblocks everything)
2. **Issue #2** + **Issue #3** — Can be built in parallel
3. **Issue #4** — After img2img works
4. **Issue #5** — After implementations land (but Neo can start writing test skeletons from Issue #1 acceptance criteria)

## Requirements Impact

```
# New dependencies for Phase 2
realesrgan>=0.3.0          # Real-ESRGAN upscaling
basicsr>=1.4.2             # Required by realesrgan
```

No new paid APIs. All models are free Hugging Face downloads.
