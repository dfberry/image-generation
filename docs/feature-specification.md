# Feature Specification — Image Generation CLI

> **Document type:** Feature specification (user-facing behavior)
> **Status:** Living document
> **Applies to:** `generate.py` (root module)
> **Last verified against:** commit `6c10f02` (2026-04-18)

---

## 1. Overview

### 1.1 What It Is

`generate.py` is a Python command-line tool that generates high-quality blog post illustrations using Stable Diffusion XL (SDXL). It produces PNG images from text prompts, targeting a **tropical magical-realism aesthetic** — Latin American folk art infused with warm luminosity and lush, pattern-dense compositions.

### 1.2 Who It's For

| Audience | How they use it |
|----------|----------------|
| **Blog authors** | Generate custom illustrations for posts on [dfberry.github.io](https://dfberry.github.io) without needing design tools or stock photos. |
| **Content creators** | Produce batches of thematically consistent images from a JSON manifest. |
| **Developers** | Extend the pipeline with new schedulers, LoRA adapters, or batch workflows. |

### 1.3 What It Is Not

- Not an interactive GUI or web service — it is strictly a CLI tool.
- Not a general-purpose image generator — defaults and prompt guidance are tuned for one specific visual aesthetic.
- Not a training tool — it runs inference only using pre-trained models from Hugging Face Hub.

---

## 2. User Stories / Use Cases

### UC-1: Generate a Single Illustration

> *As a blog author, I want to generate one image from a text prompt so I can illustrate a specific blog post section.*

```bash
python generate.py --prompt "Latin American folk art style, magical realism illustration of a glowing lighthouse at dusk"
```

Output: a timestamped PNG saved to `outputs/`.

### UC-2: Reproduce a Specific Image

> *As an author, I want to regenerate the exact same image I got before, so I can iterate on the surrounding content without the visual changing.*

```bash
python generate.py --prompt "..." --seed 42 --output outputs/lighthouse.png
```

Same seed + same parameters → identical output.

### UC-3: Generate a Batch of Blog Images

> *As a content creator, I want to generate 5 images for a blog post in one command, each with its own prompt and seed, so I don't have to babysit 5 separate runs.*

```bash
python generate.py --batch-file batch_blog_images.json
```

The tool processes each item sequentially, flushes GPU memory between items, and reports per-item success/failure.

### UC-4: Increase Image Quality with the Refiner

> *As an author who wants maximum quality, I want to opt into the two-stage pipeline (base + refiner) even though it uses more memory and time.*

```bash
python generate.py --prompt "..." --refine
```

### UC-5: Run on a Machine Without a GPU

> *As a developer testing the pipeline on a laptop without a discrete GPU, I want to force CPU mode so the tool doesn't crash looking for CUDA.*

```bash
python generate.py --prompt "..." --cpu
```

### UC-6: Apply a Custom LoRA Style

> *As an author, I want to load a LoRA adapter to shift the visual style (e.g., watercolor) without changing the base model.*

```bash
python generate.py --prompt "..." --lora joachim_s/aether-watercolor-and-ink-sdxl --lora-weight 0.7
```

### UC-7: Experiment with Different Schedulers

> *As a developer, I want to swap the diffusion scheduler to compare output quality and speed.*

```bash
python generate.py --prompt "..." --scheduler EulerAncestralDiscreteScheduler
```

---

## 3. Functional Requirements

### 3.1 Image Generation

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-001** | The tool SHALL generate a PNG image from a text prompt using SDXL Base 1.0. | Model: `stabilityai/stable-diffusion-xl-base-1.0` |
| **FR-002** | The tool SHALL support a two-stage pipeline (base + refiner) via the `--refine` flag. | Refiner: `stabilityai/stable-diffusion-xl-refiner-1.0` |
| **FR-003** | In refiner mode, the base model SHALL perform 80% of denoising and the refiner SHALL perform the remaining 20%. | `high_noise_frac = 0.8` |
| **FR-004** | The tool SHALL produce deterministic output when the same `--seed` is provided with identical parameters. | Generator bound to appropriate device. |
| **FR-005** | The tool SHALL support configurable inference steps for both the base (`--steps`) and refiner (`--refiner-steps`) pipelines independently. | Defaults: 22 base, 10 refiner. |
| **FR-006** | The tool SHALL support independent guidance scales for base (`--guidance`) and refiner (`--refiner-guidance`). | Defaults: 6.5 base, 5.0 refiner. |

### 3.2 Batch Processing

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-010** | The tool SHALL accept a `--batch-file` argument pointing to a JSON file containing an array of prompt dicts. | Mutually exclusive with `--prompt`. |
| **FR-011** | Each batch item SHALL be processed sequentially with GPU memory flushed between items. | `gc.collect()` + device cache clear. |
| **FR-012** | A failure on one batch item SHALL NOT abort remaining items. | Errors are captured per-item. |
| **FR-013** | Batch results SHALL be reported per-item with status `"ok"` or `"error"` and the error message if applicable. | Printed to stdout as `[ok]` / `[error]`. |
| **FR-014** | An empty batch file (`[]`) SHALL produce an empty result with no errors. | No `generate()` calls, no cleanup. |
| **FR-015** | Batch results SHALL preserve input order. | Result list index matches input list index. |

### 3.3 CLI Interface

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-020** | `--prompt` and `--batch-file` SHALL be mutually exclusive and one is required. | `argparse` mutually exclusive group. |
| **FR-021** | `--output` SHALL default to a timestamped filename in `outputs/` if not provided. | Format: `image_YYYYMMDD_HHMMSS.png`. |
| **FR-022** | `--width` and `--height` SHALL be >= 64 and divisible by 8. | Validated at parse time and at runtime (`validate_dimensions`). |
| **FR-023** | `--steps` SHALL be a positive integer (> 0). | Custom argparse type `_positive_int`. |
| **FR-024** | `--guidance` and `--refiner-guidance` SHALL be non-negative floats (>= 0). | Custom argparse type `_non_negative_float`. |
| **FR-025** | Invalid dimension values SHALL include the nearest valid value in the error message. | e.g., "got 65 (nearest valid: 72)". |

### 3.4 Device Management

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-030** | The tool SHALL auto-detect the best available device in order: CUDA → MPS → CPU. | `get_device()` function. |
| **FR-031** | `--cpu` SHALL force CPU mode regardless of available hardware. | Overrides auto-detection. |
| **FR-032** | On GPU devices, the tool SHALL use float16 precision. On CPU, float32. | `get_dtype()` function. |
| **FR-033** | On MPS (Apple Silicon), the tool SHALL enable model CPU offloading. | `pipe.enable_model_cpu_offload()`. |

### 3.5 Scheduler System

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-040** | The tool SHALL support 10 named schedulers selectable via `--scheduler`. | See §4.3 for the full list. |
| **FR-041** | An unrecognized scheduler name SHALL raise a `ValueError` listing all valid options. | Checked against `diffusers` module attributes. |
| **FR-042** | `DPMSolverMultistepScheduler` (the default) SHALL use Karras sigmas. | `config["use_karras_sigmas"] = True`. |
| **FR-043** | Scheduler swaps SHALL preserve the existing pipeline scheduler config. | `scheduler_cls.from_config(config)`. |

### 3.6 LoRA Support

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-050** | The tool SHALL load a LoRA adapter from a Hugging Face model ID or local path via `--lora`. | Uses `pipeline.load_lora_weights()`. |
| **FR-051** | `--lora-weight` SHALL control the adapter influence (default 0.8). | `pipeline.set_adapters(["default"], adapter_weights=[weight])`. |
| **FR-052** | If `--lora` is not provided, no adapter SHALL be loaded. | `apply_lora()` returns immediately when `lora is None`. |
| **FR-053** | Batch items SHALL be able to override `lora` and `lora_weight` per-item in the JSON dict. | Item-level fields take precedence over CLI defaults. |

### 3.7 OOM Recovery

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-060** | On CUDA or MPS out-of-memory errors, the tool SHALL retry with halved inference steps. | `generate_with_retry()`, up to `max_retries=2` (3 total attempts). |
| **FR-061** | Step count SHALL never go below 1 during halving. | `max(1, current_steps // 2)`. |
| **FR-062** | Non-OOM exceptions SHALL NOT trigger retry logic. | Only `OOMError` is caught; all others re-raise immediately. |
| **FR-063** | If all retries are exhausted, the final `OOMError` message SHALL include the step count of the last attempt. | Enables user to diagnose the threshold. |
| **FR-064** | A warning SHALL be printed on each retry including the new step count. | `print(f"OOM: retrying with {current_steps} steps")`. |

### 3.8 Negative Prompts

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-070** | The tool SHALL apply a default negative prompt steering away from common defects. | "blurry, bad quality, worst quality, low resolution, text, watermark, signature, deformed, ugly, duplicate, morbid". |
| **FR-071** | `--negative-prompt` SHALL allow the user to override the default. | String argument passed directly to the pipeline. |
| **FR-072** | Batch items SHALL be able to override `negative_prompt` per-item. | Falls back to CLI default if not specified in JSON. |

---

## 4. Input/Output Specifications

### 4.1 CLI Arguments

| Argument | Type | Default | Constraints | Description |
|----------|------|---------|-------------|-------------|
| `--prompt` | `str` | *(required†)* | Mutually exclusive with `--batch-file` | Text prompt for image generation |
| `--batch-file` | `PATH` | *(required†)* | Mutually exclusive with `--prompt` | JSON file with prompt array |
| `--output` | `str` | Auto-timestamped | — | Output file path |
| `--steps` | `int` | `22` | > 0 | Base inference steps |
| `--refiner-steps` | `int` | `10` | > 0 | Refiner inference steps |
| `--guidance` | `float` | `6.5` | >= 0 | Base guidance scale |
| `--refiner-guidance` | `float` | `5.0` | >= 0 | Refiner guidance scale |
| `--scheduler` | `str` | `DPMSolverMultistepScheduler` | Must be a supported name | Diffusion scheduler |
| `--width` | `int` | `1024` | >= 64, divisible by 8 | Image width in pixels |
| `--height` | `int` | `1024` | >= 64, divisible by 8 | Image height in pixels |
| `--seed` | `int` | `None` | — | Random seed for reproducibility |
| `--negative-prompt` | `str` | *(long default)* | — | Negative prompt string |
| `--refine` | flag | `False` | — | Enable base + refiner pipeline |
| `--cpu` | flag | `False` | — | Force CPU mode |
| `--lora` | `str` | `None` | — | LoRA model ID or path |
| `--lora-weight` | `float` | `0.8` | >= 0 | LoRA adapter weight |

† Exactly one of `--prompt` or `--batch-file` is required.

### 4.2 Batch File JSON Schema

```json
[
  {
    "prompt": "string (required) — the text prompt",
    "output": "string (required) — output file path",
    "seed": "integer (optional) — random seed",
    "negative_prompt": "string (optional) — overrides CLI default",
    "lora": "string (optional) — LoRA model ID or path",
    "lora_weight": "number (optional) — LoRA adapter weight"
  }
]
```

**Notes:**
- The file must contain a valid JSON array (not a JSON object).
- All other generation parameters (`steps`, `guidance`, `width`, `height`, `refine`, `scheduler`) are inherited from the CLI arguments and cannot be overridden per-item.
- Per-item `negative_prompt` falls back to the CLI `--negative-prompt` value if omitted.

### 4.3 Supported Schedulers

| Scheduler | Notes |
|-----------|-------|
| `DPMSolverMultistepScheduler` | **Default.** Uses Karras sigmas. Good quality/speed balance. |
| `EulerDiscreteScheduler` | Simple and fast. |
| `EulerAncestralDiscreteScheduler` | Stochastic variant of Euler. More variation between seeds. |
| `DDIMScheduler` | Denoising Diffusion Implicit Models. Deterministic. |
| `LMSDiscreteScheduler` | Linear multi-step. |
| `PNDMScheduler` | Pseudo-numerical methods for diffusion. |
| `UniPCMultistepScheduler` | Unified predictor-corrector. |
| `HeunDiscreteScheduler` | Second-order Heun method. |
| `KDPM2DiscreteScheduler` | DPM-Solver-2. |
| `DEISMultistepScheduler` | Diffusion exponential integrator. |

### 4.4 Output Format

| Property | Value |
|----------|-------|
| **File format** | PNG |
| **Default dimensions** | 1024 × 1024 pixels |
| **Default location** | `outputs/image_YYYYMMDD_HHMMSS.png` |
| **Batch output** | Each item specifies its own output path in the JSON. |
| **Batch console report** | `[ok] <prompt-prefix> → <path>` or `[error] <prompt-prefix> → <error-message>` |

---

## 5. Error Handling

### 5.1 Error Categories

| Error | Trigger | Behavior |
|-------|---------|----------|
| **Invalid CLI arguments** | Bad types, out-of-range values, missing required args | `argparse` exits with usage message. |
| **Invalid dimensions** | Width/height not divisible by 8 (runtime) | `ValueError` with nearest valid suggestion. |
| **Unknown scheduler** | `--scheduler` name not in `diffusers` module | `ValueError` listing all valid scheduler names. |
| **Batch file not found** | `--batch-file` path doesn't exist | Error printed to stderr, `sys.exit(1)`. |
| **Batch file invalid JSON** | File exists but content isn't valid JSON | JSON parse error printed to stderr, `sys.exit(1)`. |
| **GPU out-of-memory** | CUDA `OutOfMemoryError` or MPS "out of memory" `RuntimeError` | Wrapped as `OOMError`, triggers retry with halved steps. |
| **OOM after all retries** | All retry attempts fail with OOM | `OOMError` raised with final step count in message. |
| **Batch item failure** | Any exception during a single item's generation | Captured in result dict; remaining items continue. |

### 5.2 Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (all images generated, or batch completed with per-item reporting). |
| `1` | Fatal error: batch file not found or invalid JSON. |
| `2` | Argparse validation failure (invalid arguments). |
| Non-zero | Unhandled exception in single-prompt mode (OOM after retries, etc.). |

---

## 6. Constraints & Limitations

### 6.1 Hardware Requirements

| Requirement | Detail |
|-------------|--------|
| **VRAM (base-only)** | ~7 GB for SDXL Base at 1024×1024 with float16. |
| **VRAM (base+refiner)** | ~14 GB peak; mitigated by sequential loading with latent-to-CPU swap. |
| **CPU mode** | Functional but very slow (minutes per image vs. seconds on GPU). |
| **Disk (first run)** | ~7 GB download for base model; ~6 GB additional for refiner. |
| **Disk (cached)** | Models cached in Hugging Face Hub default cache directory (`~/.cache/huggingface/`). |

### 6.2 Known Limitations

1. **No text rendering** — SDXL cannot reliably render readable text inside images. The default negative prompt steers away from text artifacts, and the style guide explicitly prohibits text in images.
2. **Sequential batch processing** — Batch items are processed one at a time. There is no parallel inference.
3. **Single-image output** — Each prompt produces exactly one image. There is no `--num-images` flag.
4. **No img2img or inpainting** — The tool supports text-to-image only.
5. **No progress bars** — Inference progress is not displayed (no `tqdm` integration with the diffusers callback).
6. **Fixed denoising split** — The 80/20 base/refiner split is hardcoded. It is not configurable.
7. **No web UI** — CLI only.

---

## 7. Non-Functional Requirements

### 7.1 Reproducibility

| ID | Requirement |
|----|-------------|
| **NFR-001** | Given identical `--seed`, `--prompt`, `--steps`, `--guidance`, `--scheduler`, `--width`, `--height`, and hardware, the tool SHALL produce bit-identical output. |
| **NFR-002** | The random generator SHALL be bound to the correct device (`cpu` for CPU/MPS, `cuda` for CUDA) to avoid device mismatch errors. |

### 7.2 Memory Safety

| ID | Requirement |
|----|-------------|
| **NFR-010** | All GPU resources SHALL be released in a `finally` block, regardless of success or failure. |
| **NFR-011** | GPU memory SHALL be flushed before model loading (pre-flight), between pipeline stages (mid-refine), between batch items, and after generation (finally block). |
| **NFR-012** | `torch._dynamo` cache SHALL be reset after CUDA generation to prevent memory accumulation across repeated calls. |
| **NFR-013** | In refiner mode, latents SHALL be moved to CPU before freeing the base model to prevent pinned VRAM during cache flush. |

### 7.3 Performance

| ID | Requirement |
|----|-------------|
| **NFR-020** | On CUDA devices, `torch.compile` SHALL be applied to the UNet for ~1.5–2× inference speedup. |
| **NFR-021** | Memory-efficient attention SHALL be enabled: xFormers if available, otherwise attention slicing. |
| **NFR-022** | On MPS devices, model CPU offloading SHALL be used to reduce peak memory. |
| **NFR-023** | FP16 variant of model weights SHALL be loaded on GPU to halve memory footprint vs. FP32. |

### 7.4 Testability

| ID | Requirement |
|----|-------------|
| **NFR-030** | The entire test suite SHALL run without a GPU via mock-based testing. |
| **NFR-031** | Tests SHALL cover: CLI validation, memory cleanup, OOM handling, OOM retry, batch processing, scheduler swaps, LoRA loading, negative prompts, pipeline enhancements, and bug regressions. |

---

## 8. Future Considerations

These are potential improvements that are **not committed** to any timeline. They are captured here to inform future planning.

| Area | Idea | Rationale |
|------|------|-----------|
| **Parallel batch** | Process batch items in parallel on multi-GPU systems. | Reduces wall-clock time for large batches. |
| **Progress reporting** | Integrate `tqdm` or diffusers callbacks for per-step progress. | Gives users feedback during long generations. |
| **img2img mode** | Accept an input image for image-to-image generation. | Enables iterative refinement of existing illustrations. |
| **Configurable denoising split** | Make the 80/20 base/refiner ratio a CLI argument. | Lets advanced users tune quality vs. speed. |
| **SDXL Turbo / Lightning** | Support distilled SDXL variants for 1–4 step generation. | Dramatically faster generation at lower quality. |
| **JSON schema validation** | Validate batch file structure against a formal JSON Schema before processing. | Catches malformed input early with clear errors. |
| **Output metadata** | Embed generation parameters (seed, steps, prompt) in PNG EXIF/tEXt metadata. | Makes images self-documenting for reproducibility. |
| **Prompt templates** | Support prompt templates with variable substitution. | Reduces duplication in batch files. |
| **Web API wrapper** | Expose `generate()` via a FastAPI endpoint. | Enables integration with other tools. |
