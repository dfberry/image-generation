← [Back to Documentation Index](../README.md)

# User Guide — image-generation

Generate blog post illustrations with a tropical magical-realism aesthetic using Stable Diffusion XL.

## What This Tool Does

This is a Python CLI that uses **SDXL Base 1.0** (with optional refiner) to generate **1024×1024 PNG illustrations** in a specific art style: **tropical magical-realism** inspired by Latin American folk art. The aesthetic produces hand-painted-looking scenes with warm color palettes, dense tropical foliage, and magical-but-ordinary elements.

## Quick Start

```bash
# Activate your virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Generate a single image
python generate.py --prompt "Latin American folk art style, magical realism illustration of a glowing tropical garden with magenta flowers and teal pools, warm sunset glow, no text"

# With higher quality (base + refiner)
python generate.py --prompt "..." --refine --seed 42

# Force CPU mode (no GPU required, but slow)
python generate.py --prompt "..." --cpu
```

Output is saved to `outputs/image_{timestamp}.png` by default.

## CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--prompt TEXT` | str | *(required)* | Text prompt for image generation. Mutually exclusive with `--batch-file`. |
| `--batch-file PATH` | str | — | JSON file with list of prompt dicts for batch generation. Mutually exclusive with `--prompt`. |
| `--output PATH` | str | `outputs/image_{timestamp}.png` | Output file path. |
| `--steps INT` | int | 22 | Number of base inference steps. More steps = higher quality, slower. |
| `--refiner-steps INT` | int | 10 | Number of refiner inference steps (only used with `--refine`). |
| `--guidance FLOAT` | float | 6.5 | Guidance scale. How strongly the model follows the prompt. |
| `--refiner-guidance FLOAT` | float | 5.0 | Guidance scale for the refiner (independent from base). |
| `--scheduler TEXT` | str | `DPMSolverMultistepScheduler` | Noise scheduler algorithm. See [Schedulers](#schedulers). |
| `--width INT` | int | 1024 | Image width in pixels. Must be ≥64 and divisible by 8. |
| `--height INT` | int | 1024 | Image height in pixels. Must be ≥64 and divisible by 8. |
| `--seed INT` | int | random | Random seed for reproducible output. |
| `--negative-prompt TEXT` | str | *(built-in quality filter)* | Negative prompt to suppress unwanted features. |
| `--refine` | flag | off | Enable base + refiner pipeline for higher quality output. |
| `--cpu` | flag | off | Force CPU mode (no GPU required). |
| `--lora TEXT` | str | — | LoRA model ID or local path to load (e.g., `joachim_s/aether-watercolor-and-ink-sdxl`). |
| `--lora-weight FLOAT` | float | 0.8 | LoRA adapter weight. 0.0 = no effect, 1.0 = full effect. |

## Quality Presets

From `image-generation/prompts/examples.md`:

| Use case | --steps | --guidance | --refine |
|----------|---------|------------|----------|
| Quick draft | 20 | 7.0 | no |
| Blog quality | 40 | 7.5 | yes |
| Best quality | 50 | 7.5 | yes |

**Note on guidance scale:** SDXL's sweet spot is **7.0–7.5**. Values above 7.5 cause over-saturation and artifacts. Increase steps (not guidance) for more prompt adherence.

## Generation Time

| Device | Time per Image | With --refine |
|--------|---------------|---------------|
| NVIDIA GPU (CUDA, 8GB+) | 2–5 minutes | ~double |
| Apple Silicon (MPS) | 5–10 minutes | ~double |
| CPU | 20–30+ minutes | ~double |

The first image in a session takes longer due to:
- Model download (~7GB on first ever run)
- `torch.compile` warm-up (~30s one-time cost on CUDA)

## Batch Generation

### JSON Batch File

Create a JSON file with an array of prompt dicts:

```json
[
  {
    "prompt": "Latin American folk art style, magical realism illustration of ..., no text",
    "output": "outputs/01.png",
    "seed": 42
  },
  {
    "prompt": "Latin American folk art style, magical realism illustration of ..., no text",
    "output": "outputs/02.png",
    "seed": 43,
    "negative_prompt": "blurry, bad quality, worst quality, low resolution, text, watermark, signature, deformed, ugly, duplicate, morbid"
  }
]
```

**Required keys:** `prompt`, `output`

**Optional per-item overrides:** `seed`, `negative_prompt`, `scheduler`, `refiner_steps`, `lora`, `lora_weight`

### Running a Batch

```bash
python generate.py --batch-file my_batch.json
```

CLI flags like `--steps`, `--guidance`, `--refine` apply as defaults to all batch items. Per-item overrides in the JSON take precedence.

### Shell Script Batch

The `generate_blog_images.sh` script generates 5 blog images:

```bash
bash generate_blog_images.sh &
tail -f generation.log  # Monitor progress
```

It builds a temporary JSON prompts file and calls `generate.py --batch-file`, so all 5 images run in a single Python process with GPU memory flushed between items.

## Prompt Writing Guide

### Required Structure

Every prompt must follow this pattern:

```
{scene_description}, {palette_colors}, Latin American folk art style, magical realism illustration, {mood_and_lighting}, no text
```

### Rules

1. **Start with the canonical style anchor:**
   ```
   Latin American folk art style, magical realism illustration
   ```
   Both parts are required. Do not shorten to "folk art illustration."

2. **Include ≥3 palette colors** by name:
   - Deep magenta (`#B5179E`)
   - Teal (`#118AB2`)
   - Emerald green (`#2D6A4F`)
   - Warm gold (`#E9C46A`)
   - Coral (`#F4845F`)
   - Amber (`#E76F51`)

3. **End every prompt with `no text`** — SDXL frequently hallucinates text into scenes.

4. **Use "distant silhouette" for humans** — SDXL struggles with close-up human features. "Distant silhouette" avoids uncanny results.

5. **Describe light sources explicitly** — "warm amber light filtering through foliage," "golden sunrise glow," "soft warm gold light."

6. **Keep prompts under ~75 tokens** — SDXL's CLIP encoder truncates at 77 tokens.

### Example Prompt

```
Latin American folk art style, magical realism illustration of a distant silhouette of a traveler at a bright hotel lobby table covered in illustrated maps, tropical plants in terracotta pots, gold and teal tilework glowing in warm sunlight, no text
```

### What Works Well

- Specific color+noun pairs: "deep magenta ribbons," "teal water"
- Material textures: "weathered colorful doors," "mosaic tile floor"
- Named art movements: "Latin American folk art"
- Lighting descriptors: "warm amber light filtering through foliage"

### What to Avoid

- Negating colors ("no red") — model attends to the noun, produces more of it
- Vague style words ("nice," "pretty") — no training signal
- Guidance above 7.5 — over-saturation, harsh edges
- Prompts over 75 tokens — excess is truncated and ignored

## Schedulers

Available schedulers (pass to `--scheduler`):

| Scheduler | Use Case |
|-----------|----------|
| `DPMSolverMultistepScheduler` | Default. Fast, high quality. Gets Karras sigmas. |
| `EulerDiscreteScheduler` | Fast, popular alternative. |
| `EulerAncestralDiscreteScheduler` | Stochastic. More variation between seeds. |
| `DDIMScheduler` | Deterministic. Good for reproducibility. |
| `LMSDiscreteScheduler` | Linear multistep. |
| `PNDMScheduler` | Pseudo-numerical. |
| `UniPCMultistepScheduler` | Fast convergence. |
| `HeunDiscreteScheduler` | Second-order method. |
| `KDPM2DiscreteScheduler` | DPM-Solver variant. |
| `DEISMultistepScheduler` | Diffusion exponential integrator. |

## Output Format

- **Format:** PNG
- **Resolution:** 1024×1024 (SDXL native, configurable via `--width`/`--height`)
- **Default path:** `outputs/image_{YYYYMMDD_HHMMSS}.png`
- **Custom path:** `--output path/to/image.png`

## Negative Prompt

The default negative prompt suppresses common SDXL artifacts:

```
blurry, bad quality, worst quality, low resolution, text, watermark, signature, deformed, ugly, duplicate, morbid
```

Override with `--negative-prompt "your terms here"` or per-item in batch JSON.

## Troubleshooting

### Out of GPU Memory (OOM)

The tool automatically retries on OOM, halving steps each time (up to 2 retries). If it still fails:

```bash
# Reduce steps
python generate.py --prompt "..." --steps 15

# Switch to CPU
python generate.py --prompt "..." --cpu
```

### First Run Takes Very Long

The first run downloads ~7GB of model weights. Subsequent runs use the cached model.

### Output Image Has Text Artifacts

Ensure your prompt ends with `no text` and the negative prompt includes `text, watermark, signature`.

### Image Looks Photorealistic (Not Folk Art Style)

Ensure the prompt includes the full style anchor: `Latin American folk art style, magical realism illustration`. Both parts are required.

### Colors Look Over-Saturated

Reduce `--guidance` to 6.5–7.0. Values above 7.5 cause over-saturation with SDXL.

### Refiner Makes Image Worse

The refiner is optional. Try without `--refine` first. If using it, ensure `--refiner-guidance` is at 5.0 (default) — high values cause artifacts.

### Reproducibility

Use `--seed <number>` for reproducible output. The same seed + prompt + parameters = same image (on the same device and torch version).

### Batch Job Partially Failed

`batch_generate()` continues processing remaining items if one fails. Check the output log for per-item status (`[ok]` or `[error]`).

### Security: Path Traversal Blocked

Output paths cannot contain `..` or be absolute paths. This is intentional — see `docs/security.md`.
