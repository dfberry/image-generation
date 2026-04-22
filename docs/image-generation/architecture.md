← [Back to Documentation Index](../README.md)

# Architecture — image-generation

System architecture for the SDXL image generation pipeline.

## Pipeline Flow

```
                        ┌──────────────┐
                        │  User Input  │
                        │  (CLI args)  │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  parse_args  │
                        └──────┬───────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
          ┌──────▼───────┐           ┌───────▼──────┐
          │  --prompt     │           │ --batch-file │
          │  (single)     │           │   (JSON)     │
          └──────┬───────┘           └───────┬──────┘
                 │                           │
                 │                  ┌────────▼────────┐
                 │                  │ batch_generate() │
                 │                  │  (loop + flush)  │
                 │                  └────────┬────────┘
                 │                           │
                 └─────────┬─────────────────┘
                           │
                  ┌────────▼────────┐
                  │generate_with_   │
                  │   retry()       │
                  │ (OOM fallback)  │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │   generate()    │
                  │ (main engine)   │
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐      ┌────────▼────────┐
     │  Base-Only Path  │      │ Base+Refiner    │
     │                  │      │     Path        │
     └────────┬────────┘      └────────┬────────┘
              │                        │
     ┌────────▼────────┐      ┌────────▼────────┐
     │ _load_pipeline() │      │ _load_pipeline() │
     │ _run_inference() │      │ _run_inference() │
     │                  │      │   (latent out)   │
     │   → PIL Image    │      │ free base model  │
     └────────┬────────┘      │ _run_refiner()   │
              │                │   → PIL Image    │
              │                └────────┬────────┘
              └────────┬───────────────┘
                       │
              ┌────────▼────────┐
              │  image.save()   │
              │  → PNG file     │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │ Cleanup: gc,    │
              │ empty_cache,    │
              │ dynamo.reset    │
              └─────────────────┘
```

## Module Breakdown — `generate.py`

All logic lives in a single module: `generate.py`. Functions are organized by responsibility.

### Entry Points

| Function | Purpose |
|----------|---------|
| `main()` | CLI entry point. Parses args, dispatches to single or batch path. |
| `parse_args()` | Argparse setup. Returns namespace with all CLI flags. |

### Core Pipeline

| Function | Purpose |
|----------|---------|
| `generate(args)` | Main engine. Loads model, runs inference, saves PNG, cleans up. |
| `generate_with_retry(args)` | Wraps `generate()` with OOM retry — halves steps on each retry, up to `max_retries` (default 2). |
| `batch_generate(prompts, device, args)` | Iterates a list of prompt dicts, calls `generate_with_retry()` per item, flushes GPU memory between items. |

### Internal Helpers (underscore-prefixed)

| Function | Purpose |
|----------|---------|
| `_load_pipeline(device, args)` | Loads SDXL base, applies scheduler and optional LoRA. |
| `_run_inference(pipe, args, generator, for_refiner)` | Runs base inference. When `for_refiner=True`, outputs raw latents instead of a decoded image. |
| `_run_refiner(latents, text_encoder_2, vae, device, args, generator)` | Loads SDXL refiner (sharing text encoder + VAE from base), runs refinement pass. Returns `(refiner_pipeline, image)`. |

### Model Loading

| Function | Purpose |
|----------|---------|
| `load_base(device)` | Downloads/caches SDXL Base 1.0 (~7GB), configures dtype, device placement, performance opts. |
| `load_refiner(text_encoder_2, vae, device)` | Downloads/caches SDXL Refiner 1.0, shares `text_encoder_2` and `vae` from the base to save memory. |
| `apply_scheduler(pipeline, scheduler_name)` | Swaps the pipeline's noise scheduler by name (10 supported schedulers). |
| `apply_lora(pipeline, lora, lora_weight)` | Loads LoRA weights into the pipeline if specified. |

### Utility Functions

| Function | Purpose |
|----------|---------|
| `get_device(force_cpu)` | Detects best device: CUDA → MPS → CPU. |
| `get_dtype(device)` | Returns `float16` for GPU, `float32` for CPU. |
| `_apply_performance_opts(pipe, device)` | Applies `torch.compile` (CUDA only) and memory-efficient attention. |
| `validate_dimensions(width, height)` | Ensures dimensions are divisible by 8. |
| `_validate_output_path(output)` | Security: blocks directory traversal and absolute paths. |
| `_validate_batch_item(item, index)` | Validates batch JSON schema (required keys, types, warns on unknown keys). |

## Lazy Import System

Heavy dependencies (`torch`, `diffusers`, `DiffusionPipeline`) are **not** imported at module level. This allows `import generate` to succeed without the GPU stack installed.

### How It Works

1. **`_ensure_heavy_imports()`** — Called by every function that needs torch/diffusers. Checks `globals()` and imports only if missing. If tests have patched `generate.torch` first, the guard finds it already present and skips the real import.

2. **`__getattr__(name)`** — PEP 562 module-level `__getattr__`. Lets external code (including `unittest.mock.patch`) access `generate.torch` without it being eagerly imported. Only handles `torch`, `diffusers`, and `DiffusionPipeline`.

```python
# The lazy import guard:
def _ensure_heavy_imports():
    global torch, diffusers, DiffusionPipeline
    if "torch" not in globals():
        import torch
    # ...
```

### Why This Matters

- Tests run without GPU stack installed (CI uses CPU-only torch)
- `@patch("generate.torch")` works because the patched value lands in `globals()` before the guard runs
- Module-level code (logging, argparse types, etc.) works without triggering heavy imports

## Device Detection

Priority chain in `get_device()`:

1. **`--cpu` flag** → forces CPU (overrides everything)
2. **CUDA** → `torch.cuda.is_available()` → NVIDIA GPU
3. **MPS** → `torch.backends.mps.is_available()` → Apple Silicon
4. **CPU** → fallback (slow, ~20-30min per image)

### Device-Specific Behavior

| Device | Dtype | Placement | torch.compile | Attention |
|--------|-------|-----------|---------------|-----------|
| CUDA | float16 | `pipe.to("cuda")` | Yes (reduce-overhead) | xFormers → slicing fallback |
| MPS | float16 | `enable_model_cpu_offload()` | No | xFormers → slicing fallback |
| CPU | float32 | `pipe.to("cpu")` | No | xFormers → slicing fallback |

## Memory Management

Memory is managed at three levels:

### 1. Pre-flight Flush (before loading)
```python
gc.collect()
torch.cuda.empty_cache()  # CUDA
torch.mps.empty_cache()   # MPS
```
Reclaims GPU memory from prior `generate()` calls before loading new pipelines.

### 2. Mid-Generation Cleanup (refiner path only)
When using base+refiner:
- Base model latents are moved to CPU before cache flush
- Base model is deleted (`del base`)
- GPU cache is flushed
- `gc.collect()` runs
- Then refiner loads into freed GPU memory

### 3. Post-Generation Cleanup (always runs, even on error)
In the `finally` block:
- All pipeline objects deleted (`del base, refiner, latents, text_encoder_2, vae`)
- `gc.collect()`
- GPU cache flushed (CUDA and MPS)
- `torch._dynamo.reset()` on CUDA — clears the `torch.compile` cache to prevent accumulation across repeated calls

### Batch Memory
`batch_generate()` flushes GPU memory between items (not after the last):
```python
gc.collect()
torch.cuda.empty_cache()
torch.mps.empty_cache()
```

## Batch Processing

### Single-item path
`main()` → `generate_with_retry(args)` → `generate(args)`

### Batch path
`main()` → reads JSON → `batch_generate(prompts, device, args)` → loops items → `generate_with_retry(batch_args)` per item

### Batch JSON Format
```json
[
  {
    "prompt": "Latin American folk art style, ..., no text",
    "output": "outputs/01.png",
    "seed": 42,
    "negative_prompt": "blurry, bad quality, ..."
  }
]
```

Required keys: `prompt`, `output`. Optional: `seed`, `negative_prompt`, `scheduler`, `refiner_steps`, `lora`, `lora_weight`.

### OOM Retry Logic
`generate_with_retry()` wraps `generate()`:
- On `OOMError`: halves steps (floor at 1), retries
- Up to `max_retries` (default 2) retries = 3 total attempts
- Non-OOM exceptions re-raised immediately
- Does **not** mutate `args.steps` — creates a copy per attempt

## torch.compile Optimization

Applied only on CUDA in `_apply_performance_opts()`:

```python
pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead")
```

- ~1.5-2× speedup on CUDA with torch >= 2.0
- `fullgraph=False` (default) is used — `fullgraph=True` causes compilation failures with dynamic control flow in SDXL
- One-time compilation cost (~30s) on first run
- Dynamo cache is reset in cleanup to prevent accumulation

## Scheduler System

10 supported schedulers from `diffusers`:

| Scheduler | Notes |
|-----------|-------|
| `DPMSolverMultistepScheduler` | Default. Gets Karras sigmas enabled automatically. |
| `EulerDiscreteScheduler` | Fast, popular alternative. |
| `EulerAncestralDiscreteScheduler` | Stochastic variant of Euler. |
| `DDIMScheduler` | Deterministic, good for reproducibility. |
| `LMSDiscreteScheduler` | Linear multistep. |
| `PNDMScheduler` | Pseudo-numerical. |
| `UniPCMultistepScheduler` | Fast convergence. |
| `HeunDiscreteScheduler` | Second-order Heun method. |
| `KDPM2DiscreteScheduler` | DPM-Solver variant. |
| `DEISMultistepScheduler` | Diffusion Exponential Integrator. |

The scheduler is swapped via `apply_scheduler()` which uses `scheduler_cls.from_config()` to inherit the pipeline's existing scheduler config.

## Base+Refiner Split

When `--refine` is used, the pipeline uses an 80/20 split:

- **Base model**: runs 80% of denoising steps (`denoising_end=0.8`), outputs raw latents
- **Refiner model**: runs remaining 20% (`denoising_start=0.8`), outputs final image

The refiner shares `text_encoder_2` and `vae` from the base to reduce memory usage.
