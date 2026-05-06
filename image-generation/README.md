# image-generation

Python-based image generation using [Stable Diffusion XL Base 1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0).

## Setup

**Requirements:** Python 3.10+, ~7GB disk for model weights

**GPU Support:**
- **Apple Silicon (MPS)** — primary target, fully supported
- **NVIDIA GPU (CUDA)** — 8GB+ VRAM, fully supported
- **CPU mode** — fallback (slow), use `--cpu` flag to force

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**For reproducible builds in CI/CD**, use `requirements.lock` which pins all dependencies to exact versions:

```bash
pip install -r requirements.lock
```

**Dependency versions:** Pinned to known-good releases:
- `torch>=2.1.0`
- `diffusers>=0.30.0`
- `accelerate>=0.24.0`

## Usage

```bash
# Basic generation (MPS on Apple Silicon, CUDA on NVIDIA, CPU fallback)
python generate.py --prompt "Your prompt here"

# Force CPU mode (no GPU required)
python generate.py --prompt "Your prompt here" --cpu

# With refiner (higher quality, slower)
python generate.py --prompt "Your prompt here" --refine

# Reproducible output
python generate.py --prompt "Your prompt here" --seed 42 --refine
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt TEXT` | required | Text prompt (mutually exclusive with `--batch-file`) |
| `--batch-file PATH` | — | JSON file with list of prompt dicts for batch generation |
| `--model NAME` | — | Model to use: `creative`, `precise` (default), `balanced` |
| `--output PATH` | `outputs/image_{timestamp}.png` | Output file |
| `--steps INT` | 22 | Number of base inference steps |
| `--refiner-steps INT` | 10 | Number of refiner inference steps |
| `--guidance FLOAT` | 6.5 | Guidance scale |
| `--refiner-guidance FLOAT` | 5.0 | Guidance scale for refiner (independent from base) |
| `--scheduler TEXT` | `DPMSolverMultistepScheduler` | Scheduler class name from diffusers |
| `--width INT` | 1024 | Image width in pixels |
| `--height INT` | 1024 | Image height in pixels |
| `--seed INT` | random | Reproducibility seed |
| `--negative-prompt TEXT` | *(built-in quality filter)* | Negative prompt to suppress unwanted features |
| `--refine` | off | Use base + refiner pipeline (higher quality) |
| `--cpu` | off | Force CPU mode (no GPU) |
| `--lora TEXT` | — | LoRA model ID or path to load |
| `--lora-weight FLOAT` | 0.8 | LoRA adapter weight (0.0–1.0) |

## Multi-Model Support

Use `--model` to select a generation model:

| Name | Model | Best for |
|------|-------|----------|
| `creative` | FLUX.1-schnell | Artistic compositions, best prompt adherence |
| `precise` | SDXL Base 1.0 | Photorealistic, high detail (default) |
| `balanced` | SD3 Medium | Good balance of speed and quality |

```bash
# Artistic/creative generation
python generate.py --prompt "A magical forest" --model creative

# High-detail (default behavior)
python generate.py --prompt "A photo of a mountain" --model precise

# Balanced speed and quality
python generate.py --prompt "A sunset over the ocean" --model balanced
```

> **Note:** SD3 Medium (`balanced`) is a gated model. You must accept the license at
> https://huggingface.co/stabilityai/stable-diffusion-3-medium-diffusers and set
> `HF_TOKEN` environment variable before use. It uses the Stability AI Community License
> (non-commercial).

## Generation Time

Image generation typically takes **5–10 minutes per image** on Apple Silicon (MPS) and **2–5 minutes** on NVIDIA GPUs with 8GB+ VRAM. CPU mode is significantly slower (20–30+ minutes per image). The first image in a session takes longer due to model loading and `torch.compile` warm-up (~30s one-time cost on CUDA).

Using `--refine` roughly doubles generation time since it runs a second pass through the refiner model.

### Example Output

These blog illustrations were generated with this tool using the tropical magical-realism style from [`prompts/examples.md`](prompts/examples.md):

| Image | Prompt concept |
|-------|---------------|
| [bellingham-bay-boardwalk-fleet.png](https://github.com/dfberry/dfberry.github.io/blob/blog/draft-posts-april-17/website/blog/media/2026-04-18-observability-for-custom-copilot-agents/bellingham-bay-boardwalk-fleet.png) | Fleet of boats on Bellingham Bay |
| [cedar-tree-rings-history.png](https://github.com/dfberry/dfberry.github.io/blob/blog/draft-posts-april-17/website/blog/media/2026-04-18-observability-for-custom-copilot-agents/cedar-tree-rings-history.png) | Cedar tree rings as data history |
| [chain-lakes-trail-fork.png](https://github.com/dfberry/dfberry.github.io/blob/blog/draft-posts-april-17/website/blog/media/2026-04-18-observability-for-custom-copilot-agents/chain-lakes-trail-fork.png) | Trail fork decision point |
| [nooksack-river-sensor-stations.png](https://github.com/dfberry/dfberry.github.io/blob/blog/draft-posts-april-17/website/blog/media/2026-04-18-observability-for-custom-copilot-agents/nooksack-river-sensor-stations.png) | River sensor monitoring stations |

## Memory Management

The pipeline **automatically cleans up GPU memory** after each generation:
- Models are unloaded and garbage collected
- GPU cache is flushed (`torch.cuda.empty_cache()` / `torch.mps.empty_cache()`)
- Safe for batch processing and long-running applications
- Exception-safe: cleanup runs even if generation fails

## Testing

**170 pytest tests across 11 files** covering CLI validation, batch generation, memory management, device handling, OOM retry, scheduler selection, negative prompts, pipeline enhancements, and bug fixes — no GPU required.

```bash
pytest tests/ -v
```

## Batch Generation

```bash
# Generate blog images in sequence
bash generate_blog_images.sh
```

## Example Prompts

See [`prompts/examples.md`](prompts/examples.md) for curated tropical magical-realism prompts.

## License

- Model: [CreativeML Open RAIL++-M License](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md)
- Code: MIT
