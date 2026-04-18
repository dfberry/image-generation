# Design Document — Image Generation CLI

> **Document type:** Technical design (internal architecture)
> **Status:** Living document
> **Applies to:** `generate.py` (root module)
> **Last verified against:** commit `6c10f02` (2026-04-18)

---

## 1. Architecture Overview

### 1.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLI Entry Point                           │
│                          main() / parse_args()                      │
├────────────┬────────────────────────────────────────────────────────┤
│            │                                                        │
│  --prompt  │  --batch-file                                          │
│     │      │       │                                                │
│     ▼      │       ▼                                                │
│  generate_ │    batch_generate()                                    │
│  with_     │       │                                                │
│  retry()   │       ├─── for each item ──► generate_with_retry()     │
│     │      │       │                         │                      │
│     ▼      │       │                         ▼                      │
│  generate()│◄──────┘                     generate()                 │
│     │      │                                                        │
├─────┴──────┴────────────────────────────────────────────────────────┤
│                        Generation Core                              │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ get_device() │    │ get_dtype()  │    │ validate_dimensions()│  │
│  │ CUDA→MPS→CPU │    │ fp16 / fp32  │    │ >=64, div by 8      │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────────────────┘  │
│         │                   │                                       │
│         ▼                   ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Pipeline Loading                         │   │
│  │  load_base()  ──►  apply_scheduler()  ──►  apply_lora()     │   │
│  │  load_refiner()     (10 schedulers)        (optional)        │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Inference Path                           │   │
│  │                                                              │   │
│  │   Path A: Base-only          Path B: Base + Refiner          │   │
│  │   ───────────────            ────────────────────            │   │
│  │   base(prompt) → image       base(prompt) → latents          │   │
│  │                              latents → CPU                   │   │
│  │                              del base, flush                 │   │
│  │                              load refiner (shared VAE+TE2)   │   │
│  │                              refiner(latents) → image        │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Memory Management                         │   │
│  │  Pre-flight flush │ Mid-refine flush │ Between-batch flush   │   │
│  │  Finally-block cleanup │ Dynamo cache reset                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     OOM Recovery                             │   │
│  │  generate_with_retry(): catch OOMError → halve steps → retry │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Module Structure

The entire tool lives in a single file: **`generate.py`** (461 lines). This is deliberate — the tool is small enough that splitting into multiple modules would add import complexity without meaningful separation of concerns. Key organizational units:

| Section | Lines (approx.) | Contents |
|---------|-----------------|----------|
| Imports + `OOMError` | 1–25 | Standard library, torch, diffusers |
| Argparse types + validation | 28–65 | `_positive_int`, `_non_negative_float`, `_dimension`, `validate_dimensions` |
| `parse_args()` | 67–99 | CLI argument definitions |
| Device + dtype helpers | 102–118 | `get_device()`, `get_dtype()` |
| Performance optimizations | 121–135 | `_apply_performance_opts()` |
| Model loading | 138–183 | `load_base()`, `load_refiner()` |
| Scheduler + LoRA | 186–223 | `SUPPORTED_SCHEDULERS`, `apply_scheduler()`, `apply_lora()` |
| Core generation | 226–357 | `generate()` — the main inference function |
| Batch + retry | 360–436 | `batch_generate()`, `generate_with_retry()` |
| Entry point | 439–461 | `main()` |

---

## 2. Data Flow

### 2.1 Single-Prompt Flow

```
User invokes CLI
        │
        ▼
   parse_args()
        │
        ▼
   main() detects --prompt mode
        │
        ▼
   generate_with_retry(args)          ◄── OOM retry wrapper
        │
        ▼
   generate(args)
        │
        ├── validate_dimensions(width, height)
        ├── get_device(force_cpu) → "cuda" | "mps" | "cpu"
        ├── Pre-flight memory flush (gc + cache clear)
        ├── Set up torch.Generator if --seed provided
        ├── Resolve output path (explicit or timestamped)
        │
        ├── [if --refine]
        │       ├── load_base(device)
        │       ├── apply_scheduler(base, scheduler_name)
        │       ├── apply_lora(base, lora, weight)
        │       ├── base(prompt, ..., output_type="latent") → latents
        │       ├── Extract text_encoder_2 + vae from base
        │       ├── Move latents to CPU
        │       ├── del base; flush GPU
        │       ├── load_refiner(text_encoder_2, vae, device)
        │       └── refiner(prompt, ..., image=latents.to(device)) → image
        │
        ├── [else base-only]
        │       ├── load_base(device)
        │       ├── apply_scheduler(base, scheduler_name)
        │       ├── apply_lora(base, lora, weight)
        │       └── base(prompt, ...) → image
        │
        ├── image.save(output_path)
        │
        └── [finally] Cleanup: del all, gc.collect, cache flush, dynamo reset
```

### 2.2 Batch Flow

```
User invokes CLI with --batch-file
        │
        ▼
   main() reads JSON file
        │
        ├── FileNotFoundError → stderr + exit(1)
        ├── JSONDecodeError → stderr + exit(1)
        │
        ▼
   batch_generate(prompts, device, args)
        │
        ├── for each item in prompts:
        │       │
        │       ├── Build SimpleNamespace from item + CLI args
        │       ├── generate_with_retry(batch_args)
        │       │       ├── [success] → append {"status": "ok", ...}
        │       │       └── [exception] → append {"status": "error", ...}
        │       │
        │       └── [if not last item] gc.collect + cache flush
        │
        └── Print per-item status lines to stdout
```

---

## 3. Pipeline Architecture

### 3.1 Base-Only Pipeline

The simpler path. One model loaded, inference produces a PIL Image directly.

```python
base = load_base(device)          # DiffusionPipeline.from_pretrained(...)
apply_scheduler(base, name)       # Swap scheduler, preserve config
apply_lora(base, lora, weight)    # Optional: load LoRA adapter

image = base(
    prompt=...,
    negative_prompt=...,
    num_inference_steps=steps,     # Default: 22
    guidance_scale=guidance,       # Default: 6.5
    width=..., height=...,
    generator=generator,           # Seeded or None
).images[0]
```

**When to use:** Default mode. Good enough for most blog illustrations. Lower memory, faster.

### 3.2 Base + Refiner Pipeline

Two-stage pipeline where the base generates coarse structure and the refiner adds fine detail. The key challenge is that both models cannot fit in VRAM simultaneously on most consumer GPUs.

```
 Base Model (80% denoising)              Refiner Model (20% denoising)
┌─────────────────────────┐             ┌──────────────────────────┐
│                         │             │                          │
│  prompt ──► base(       │  latents    │  refiner(                │
│    denoising_end=0.8,   │──────────►  │    denoising_start=0.8,  │
│    output_type="latent" │  (via CPU)  │    image=latents         │
│  )                      │             │  ) ──► image             │
│                         │             │                          │
│  Shares: text_encoder_2 │─────────────│  Receives: TE2, VAE     │
│          vae            │             │  (shared, not reloaded)  │
└─────────────────────────┘             └──────────────────────────┘
```

**Key design choices:**

1. **Sequential loading:** Base is loaded, run, and deleted before refiner loads. This means peak VRAM ≈ size of one model, not both.

2. **Component sharing:** The refiner receives `text_encoder_2` and `vae` from the base rather than loading its own copies. This saves ~2 GB of VRAM.

3. **Latent CPU transfer:** Before deleting the base, latents are moved to CPU (`latents.cpu()`). Without this, the latent tensor pins VRAM during `torch.cuda.empty_cache()`, defeating the cache flush.

4. **Denoising split:** `denoising_end=0.8` on base, `denoising_start=0.8` on refiner. The base handles 80% of the denoising steps (coarse structure), the refiner handles 20% (fine detail, textures). This is the ratio recommended by Stability AI.

### 3.3 Model Details

| Model | Hugging Face ID | Size (fp16) | Purpose |
|-------|----------------|-------------|---------|
| SDXL Base 1.0 | `stabilityai/stable-diffusion-xl-base-1.0` | ~6.9 GB | Primary text-to-image generation |
| SDXL Refiner 1.0 | `stabilityai/stable-diffusion-xl-refiner-1.0` | ~6.0 GB | Fine-detail enhancement pass |

Both models are loaded with `use_safetensors=True` and the `fp16` variant on GPU devices (no variant on CPU, which uses float32).

The safety checker is explicitly disabled (`pipe.safety_checker = None`) because:
- All prompts are author-controlled blog illustrations, not user-generated content.
- Removing it saves ~1.5 GB of VRAM and avoids false positives on folk art aesthetics.

---

## 4. Memory Management Strategy

Memory management is the most complex subsystem. Consumer GPUs (8–12 GB) can't comfortably hold SDXL, so the code implements a **4-layer cleanup strategy** to minimize VRAM pressure.

### 4.1 The Four Layers

```
Layer 1: Pre-flight flush
    When:  Start of generate(), before any model loads
    What:  gc.collect() + torch.cuda.empty_cache() + torch.mps.empty_cache()
    Why:   Reclaim memory from prior generate() calls or other GPU work.

Layer 2: Mid-refine flush
    When:  After base produces latents, before refiner loads (refiner path only)
    What:  latents.cpu() → del base → cache flush → gc.collect()
    Why:   Free ~7 GB of base model VRAM to make room for the refiner.
    Key:   Latents MUST move to CPU FIRST — otherwise the tensor pins VRAM.

Layer 3: Between-batch flush
    When:  Between batch items (not after the last one)
    What:  gc.collect() + torch.cuda.empty_cache() + torch.mps.empty_cache()
    Why:   Prevent VRAM accumulation across sequential generations.

Layer 4: Finally-block cleanup
    When:  Always, after generate() completes (success or failure)
    What:  del base, refiner, latents, text_encoder_2, vae, image
           gc.collect() + cache flush + torch._dynamo.reset() (CUDA only)
    Why:   Exception-safe cleanup. Runs on OOM, keyboard interrupt, any exception.
```

### 4.2 Dynamo Cache Reset

`torch.compile()` (applied to UNet on CUDA in `_apply_performance_opts()`) populates a process-global `torch._dynamo` cache. This cache survives `del pipe` because it's attached to the torch runtime, not the pipeline object. Without an explicit `torch._dynamo.reset()`, the cache grows across repeated `generate()` calls — a slow memory leak.

The reset is gated to CUDA only because `torch.compile` is only applied on CUDA:

```python
# generate.py line 354
if device == "cuda" and hasattr(torch, "_dynamo"):
    torch._dynamo.reset()
```

### 4.3 MPS-Specific Handling

Apple Silicon (MPS) has unique memory behavior:
- `pipe.enable_model_cpu_offload()` is used instead of `pipe.to("mps")` because MPS has a unified memory architecture and offloading reduces peak allocation.
- `torch.mps.empty_cache()` is called alongside CUDA cache clears. MPS cache behavior is less predictable than CUDA's.
- The random generator is bound to `"cpu"` for MPS devices because CPU offload routes some layers through CPU, and a device-mismatched generator causes runtime errors.

---

## 5. OOM Recovery

### 5.1 Detection

CUDA and MPS report out-of-memory differently:

```python
# CUDA: typed exception (torch >= 2.0)
isinstance(exc, torch.cuda.OutOfMemoryError)

# MPS: generic RuntimeError with message
isinstance(exc, RuntimeError) and "out of memory" in str(exc).lower()
```

Both are caught in `generate()` and re-raised as `OOMError(RuntimeError)`, providing a unified error type.

### 5.2 Retry Logic (`generate_with_retry`)

```
generate_with_retry(args, max_retries=2)
    │
    ├── attempt 0: generate(args, steps=N)
    │       ├── [success] → return output_path
    │       ├── [OOMError] → current_steps = max(1, N // 2)
    │       └── [other error] → raise immediately (no retry)
    │
    ├── attempt 1: generate(args, steps=N//2)
    │       ├── [success] → return output_path
    │       ├── [OOMError] → current_steps = max(1, N//4)
    │       └── [other error] → raise immediately
    │
    └── attempt 2: generate(args, steps=N//4)
            ├── [success] → return output_path
            └── [OOMError] → raise OOMError("...after 2 retries...{steps}...")
```

**Design constraints:**
- `args.steps` is never mutated. A local `current_steps` variable tracks the halved value, and a fresh `SimpleNamespace` copy is created for each attempt.
- Total attempts = `max_retries + 1` (default: 3).
- Steps floor at 1: `max(1, current_steps // 2)`.
- Only `OOMError` triggers retry. All other exceptions propagate immediately.

### 5.3 Why Step Halving?

Inference memory scales roughly with step count because each step accumulates intermediate activations. Halving steps is a coarse but effective heuristic:

- **It's fast** — no need to detect available VRAM or adjust image size.
- **It preserves the prompt** — the user gets a lower-quality version of what they asked for, not a different image.
- **It's bounded** — at most 2 retries, and steps can't go below 1, so the tool doesn't spin forever.

---

## 6. Device Abstraction

### 6.1 Detection Chain

```python
def get_device(force_cpu: bool) -> str:
    if force_cpu:         return "cpu"     # User override
    if cuda_available:    return "cuda"    # Preferred: NVIDIA GPU
    if mps_available:     return "mps"     # Apple Silicon GPU
    return "cpu"                           # Fallback
```

### 6.2 Device-Specific Behavior Matrix

| Behavior | CUDA | MPS | CPU |
|----------|------|-----|-----|
| **dtype** | float16 | float16 | float32 |
| **Model placement** | `pipe.to("cuda")` | `pipe.enable_model_cpu_offload()` | `pipe.to("cpu")` |
| **torch.compile** | ✅ UNet compiled | ❌ | ❌ |
| **xFormers** | Attempted, fallback to attention slicing | Attempted, fallback to attention slicing | Attempted, fallback to attention slicing |
| **Generator device** | `"cuda"` | `"cpu"` (offload compat) | `"cpu"` |
| **Cache flush** | `torch.cuda.empty_cache()` | `torch.mps.empty_cache()` | no-op |
| **Dynamo reset** | ✅ | ❌ | ❌ |
| **FP16 variant** | ✅ | ✅ | ❌ (full precision) |

### 6.3 Why MPS Uses CPU Generator

When `enable_model_cpu_offload()` is used on MPS, some pipeline layers execute on CPU. If the `torch.Generator` is bound to `"mps"`, these CPU-bound layers fail with a device mismatch error. Binding the generator to `"cpu"` avoids this:

```python
# generate.py line 243-244
generator_device = "cpu" if device in ("cpu", "mps") else device
generator = torch.Generator(device=generator_device).manual_seed(args.seed)
```

---

## 7. Scheduler System

### 7.1 Architecture

Schedulers are swapped at runtime using diffusers' config-based construction pattern:

```python
def apply_scheduler(pipeline, scheduler_name: str):
    scheduler_cls = getattr(diffusers, scheduler_name)      # Get class from module
    config = pipeline.scheduler.config                       # Preserve existing config
    pipeline.scheduler = scheduler_cls.from_config(config)   # Construct with same config
```

This works because all diffusers schedulers accept a common config dict and extend it with scheduler-specific parameters.

### 7.2 Karras Sigmas

The default scheduler (`DPMSolverMultistepScheduler`) gets a special config override:

```python
if scheduler_name == "DPMSolverMultistepScheduler":
    config["use_karras_sigmas"] = True
```

Karras sigmas adjust the noise schedule to front-load detail in early steps, improving quality at lower step counts — important since the default is only 22 steps.

### 7.3 Validation

Scheduler names are validated by checking if the attribute exists on the `diffusers` module (`hasattr(diffusers, scheduler_name)`). The `SUPPORTED_SCHEDULERS` list at module level is for documentation and error messages, not for validation gating. This means any scheduler class in diffusers could theoretically be used — the list just documents the tested ones.

---

## 8. LoRA Integration

### 8.1 Loading

```python
def apply_lora(pipeline, lora: str | None, lora_weight: float = 0.8):
    if lora is None:
        return                                    # No-op if not requested
    pipeline.load_lora_weights(lora)              # From HF Hub or local path
    pipeline.set_adapters(["default"],             # Set weight on the default adapter
                          adapter_weights=[lora_weight])
```

### 8.2 Design Notes

- LoRA is loaded **after** the scheduler swap but **before** inference. This is intentional: LoRA modifies model weights, and the scheduler is orthogonal to weight modifications.
- The adapter name is always `"default"` — the diffusers library assigns this name when no explicit adapter name is given.
- In batch mode, per-item LoRA is supported: each item can specify `"lora"` and `"lora_weight"` in the JSON dict. Since `generate()` loads and unloads models from scratch each call (due to memory management), there is no risk of LoRA state leaking between batch items.

---

## 9. Batch Processing

### 9.1 Orchestration

`batch_generate()` is a simple loop that wraps `generate_with_retry()`:

```python
def batch_generate(prompts: list[dict], device: str, args=None) -> list[dict]:
    results = []
    for i, item in enumerate(prompts):
        batch_args = SimpleNamespace(...)   # Merge item fields with CLI args
        try:
            output_path = generate_with_retry(batch_args)
            results.append({"status": "ok", ...})
        except Exception as exc:
            results.append({"status": "error", ...})

        if i < len(prompts) - 1:           # Flush between items, not after last
            gc.collect(); cache_flush()
    return results
```

### 9.2 Argument Merging

Each batch item is merged with CLI args into a `SimpleNamespace`. The merge priority is:

| Field | Source | Notes |
|-------|--------|-------|
| `prompt` | Item JSON | Always from batch item |
| `output` | Item JSON | Always from batch item |
| `seed` | Item JSON (optional) | `None` if not in JSON |
| `negative_prompt` | Item JSON → CLI fallback | Per-item override or CLI default |
| `lora` | Item JSON → CLI fallback | Per-item override or CLI default |
| `lora_weight` | Item JSON → CLI fallback | Per-item override or CLI default |
| `steps`, `guidance`, `width`, `height`, `refine`, `scheduler` | CLI args | Not overridable per-item |

### 9.3 Error Isolation

A failed item does not abort the batch. The exception is caught, stored in the result dict, and processing continues. This is critical for batch workflows where a user might queue 10 images and leave — one OOM failure shouldn't discard the other 9.

### 9.4 Memory Flush Timing

Flushes happen **between** items, not after the last one. This is an intentional optimization: the finally block inside `generate()` already cleans up after the last item, so a redundant flush is wasteful.

---

## 10. Key Design Decisions

### DD-1: Single-File Architecture

**Decision:** Keep the entire tool in one file (`generate.py`).

**Rationale:** At ~460 lines, splitting into `cli.py`, `pipeline.py`, `memory.py`, etc. would add import complexity and make the codebase harder to navigate for a tool this size. The functions are well-named and grouped by section. If the tool grows past ~800 lines or gains multiple distinct subsystems (e.g., a server mode), a split would be warranted.

### DD-2: Safety Checker Disabled

**Decision:** `pipe.safety_checker = None` on both base and refiner.

**Rationale:** All prompts are author-controlled (blog illustrations, not user-generated content). The NSFW classifier adds ~1.5 GB of VRAM overhead and has known false positives on folk art aesthetics (bright colors, dense compositions). Disabling it is the right trade-off for this use case.

### DD-3: Sequential Model Loading in Refiner Path

**Decision:** Load base → run → delete → load refiner, rather than loading both simultaneously.

**Rationale:** Both models are ~7 GB each. Consumer GPUs (8–16 GB VRAM) cannot hold both at once. Sequential loading with latent-to-CPU transfer makes the refiner path viable on 8 GB GPUs.

### DD-4: OOM Retry with Step Halving (Not Image Resizing)

**Decision:** On OOM, reduce `--steps` rather than `--width`/`--height`.

**Rationale:** Reducing image dimensions changes the user's expectation fundamentally — a 512×512 image is not a "degraded" version of 1024×1024, it's a different product. Reducing steps preserves the image dimensions and composition while lowering quality gradually. The user can distinguish "slightly less detailed" from "completely wrong size."

### DD-5: `generate_with_retry` Uses Local Step Copy

**Decision:** `generate_with_retry()` creates a `SimpleNamespace` copy for each attempt rather than mutating `args.steps`.

**Rationale:** The caller's args object should not be modified as a side effect. If `batch_generate()` passes the same args to multiple items, mutating steps on one OOM would silently reduce steps for all subsequent items. The copy prevents this class of bug.

### DD-6: Karras Sigmas on Default Scheduler Only

**Decision:** `use_karras_sigmas = True` is only injected for `DPMSolverMultistepScheduler`, not all schedulers.

**Rationale:** Not all schedulers support Karras sigmas. Injecting it universally would cause `from_config()` errors on schedulers that don't accept that parameter. The DPM++ solver specifically benefits from Karras sigmas at low step counts.

### DD-7: `torch.compile` on CUDA Only

**Decision:** `torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=True)` is applied only when `device == "cuda"`.

**Rationale:** `torch.compile` provides 1.5–2× speedup on CUDA but is not stable on MPS (known issues with the MPS backend) and is pointless on CPU (CPU inference is already bottlenecked by compute, not dispatch overhead).

### DD-8: Batch Items Cannot Override Steps/Guidance/Dimensions

**Decision:** Only `prompt`, `output`, `seed`, `negative_prompt`, `lora`, and `lora_weight` are per-item. Steps, guidance, width, height, scheduler, and refine are global (from CLI).

**Rationale:** Changing dimensions or step counts between items would require recompiling the UNet (invalidating `torch.compile` cache) and could cause dimension-related memory spikes. Keeping these global ensures consistent memory behavior across the batch.

---

## 11. Testing Strategy

### 11.1 Overview

| Metric | Value |
|--------|-------|
| **Test files** | 12 (11 test files + 1 conftest) |
| **Test functions** | 170 (172 items with parametrize expansion) |
| **GPU required** | No — all tests run on CPU with mocked pipelines |
| **Framework** | pytest >= 7.0 |
| **Linter** | ruff >= 0.4.0 |
| **Coverage** | pytest-cov >= 4.0 |
| **Run command** | `make test` or `python -m pytest tests/ -v` |

### 11.2 Mock Strategy

The test suite never loads a real SDXL model. All pipeline behavior is mocked:

**`conftest.py` provides:**
- `MockImage` — minimal PIL Image stand-in with a `save()` method.
- `MockPipeline` — stands in for `DiffusionPipeline`. Calling it returns either a `MockImage` list (base/refiner path) or a mock latent tensor. Supports `to()`, `enable_model_cpu_offload()`, `enable_attention_slicing()`, `enable_xformers_memory_efficient_attention()`, `load_lora_weights()`, `set_adapters()`.
- `mock_args_base`, `mock_args_refine`, `mock_args_cuda`, `mock_args_cuda_refine` — pre-built args fixtures for each device/pipeline combination.

**Patching patterns:**
- `patch("generate.load_base")` — replaces model loading with MockPipeline instantiation.
- `patch("generate.load_refiner")` — same for the refiner.
- `patch("generate.generate")` — used in batch/retry tests to control success/failure.
- `patch("generate.gc")` — verifies cleanup calls are made.
- `patch("generate.torch")` — verifies device-specific cache flushes.

### 11.3 Test Coverage by Area

| File | Tests | Area |
|------|-------|------|
| `test_cli_validation.py` | 13 | Argparse types, dimension validation, negative prompt defaults |
| `test_unit_functions.py` | 31 | `get_device`, `get_dtype`, `apply_scheduler`, `apply_lora`, `validate_dimensions` |
| `test_pipeline_enhancements.py` | 20 | `_apply_performance_opts`, torch.compile, xFormers, attention slicing |
| `test_scheduler.py` | 18 | All 10 schedulers, Karras sigmas, unknown scheduler errors |
| `test_memory_cleanup.py` | 22 | Finally-block cleanup, pre-flight flush, latent CPU transfer, dynamo reset |
| `test_oom_handling.py` | 14 | OOM detection (CUDA + MPS), `OOMError` wrapping |
| `test_oom_retry.py` | 10 | `generate_with_retry` halving, floor-at-1, non-OOM passthrough |
| `test_batch_generation.py` | 17 | `batch_generate` delegation, memory flush between items, partial failure |
| `test_batch_cli.py` | 10 | `--batch-file` CLI integration, JSON parsing errors, file-not-found |
| `test_negative_prompt.py` | 7 | Default negative prompt, per-item override, empty string handling |
| `test_bug_fixes.py` | 8 | Regression tests for specific bugs fixed in past PRs |

### 11.4 TDD Workflow

Tests in this project follow a **test-first** (TDD red-green) workflow:
- Neo writes tests **before** the implementation exists. Tests initially fail.
- Trinity implements the feature to make the tests pass.
- Morpheus reviews both.

This is visible in test file headers like `test_oom_retry.py`: *"TDD Red Phase — OOM Retry Logic tests. These tests are written BEFORE the implementation exists."*

---

## 12. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `diffusers` | >= 0.21.0 | Core diffusion pipeline library. Provides `DiffusionPipeline`, all scheduler classes, and LoRA loading. |
| `transformers` | >= 4.30.0 | Text encoder models (CLIP) used by SDXL for prompt conditioning. |
| `accelerate` | >= 0.24.0 | Device placement and CPU offloading. Required by diffusers for `enable_model_cpu_offload()`. |
| `safetensors` | >= 0.3.0 | Safe tensor serialization format. Faster and safer than pickle for model weights. |
| `invisible-watermark` | >= 0.2.0 | Required by SDXL pipeline for watermark embedding (Stability AI requirement). |
| `torch` | >= 2.1.0 | Core ML framework. Provides CUDA/MPS backends, `torch.compile`, memory management APIs. |
| `Pillow` | >= 10.0.0 | PIL Image handling. Used to save generated images as PNG. |

**Dev-only dependencies:**

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | >= 7.0 | Test framework. |
| `ruff` | >= 0.4.0 | Linter and formatter. Config in `ruff.toml`. |
| `pytest-cov` | >= 4.0 | Coverage reporting. |

---

## Appendix A: Performance Optimization Details

### A.1 `_apply_performance_opts(pipe, device)`

Applied to both base and refiner pipelines after loading:

```python
def _apply_performance_opts(pipe, device: str):
    # 1. torch.compile on CUDA (1.5-2x speedup, ~30s one-time cost)
    if device == "cuda" and hasattr(torch, "compile"):
        pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=True)

    # 2. Memory-efficient attention: prefer xFormers, fall back to slicing
    if hasattr(pipe, "enable_xformers_memory_efficient_attention"):
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pipe.enable_attention_slicing()
    else:
        pipe.enable_attention_slicing()
```

**`torch.compile` details:**
- `mode="reduce-overhead"`: Minimizes CPU overhead via CUDA graphs. Best for fixed-shape workloads like diffusion (same tensor shapes every step).
- `fullgraph=True`: Compiles the entire UNet as one graph. Disables graph breaks for maximum optimization, but requires the model to be compatible (SDXL UNet is).
- ~30s one-time compilation cost on first inference. Subsequent calls reuse the compiled graph.

**Attention optimization priority:**
1. **xFormers memory-efficient attention** (if installed) — reduces peak VRAM by ~30% via a fused attention kernel.
2. **Attention slicing** (fallback) — splits attention computation into chunks. Slower than xFormers but always available.

### A.2 FP16 Model Loading

On GPU devices, the model is loaded with `variant="fp16"` which downloads pre-quantized FP16 weights instead of FP32 weights that would need to be cast at load time. This halves download size and load-time memory usage.

---

## Appendix B: File Layout

```
image-generation/
├── generate.py                    # The tool (all production code)
├── requirements.txt               # Runtime dependencies
├── requirements-dev.txt           # Dev dependencies (includes requirements.txt)
├── Makefile                       # setup, test, lint, format, clean
├── ruff.toml                      # Linter config (Python 3.10+, 120 char lines)
├── batch_blog_images.json         # Example batch file
├── batch_blog_images_v2.json      # Variant batch file
├── batch_observability_blog.json  # Another batch file
├── batch_session_storage.json     # Another batch file
├── generate_blog_images.sh        # Shell wrapper for batch generation
├── outputs/                       # Default output directory
├── prompts/
│   └── examples.md                # Style guide + curated prompts
├── tests/
│   ├── conftest.py                # MockPipeline, MockImage, shared fixtures
│   ├── test_batch_cli.py          # --batch-file CLI integration
│   ├── test_batch_generation.py   # batch_generate() unit tests
│   ├── test_bug_fixes.py          # Regression tests
│   ├── test_cli_validation.py     # Argparse validation
│   ├── test_memory_cleanup.py     # Memory management tests
│   ├── test_negative_prompt.py    # Negative prompt behavior
│   ├── test_oom_handling.py       # OOM detection + wrapping
│   ├── test_oom_retry.py          # generate_with_retry() tests
│   ├── test_pipeline_enhancements.py  # Performance opts
│   ├── test_scheduler.py          # Scheduler system tests
│   └── test_unit_functions.py     # Pure function unit tests
└── docs/
    ├── feature-specification.md   # What the tool does (user-facing)
    ├── design.md                  # How it works (this document)
    └── blog-image-generation-skill.md
```
