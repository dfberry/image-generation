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

**Dependency versions:** Pinned to known-good releases:
- `torch>=2.1.0`
- `diffusers>=0.21.0`
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
| `--prompt TEXT` | required | Text prompt |
| `--output PATH` | `outputs/image_{timestamp}.png` | Output file |
| `--steps INT` | 40 | Inference steps |
| `--guidance FLOAT` | 7.5 | Guidance scale |
| `--width INT` | 1024 | Image width |
| `--height INT` | 1024 | Image height |
| `--seed INT` | random | Reproducibility seed |
| `--refine` | off | Use base + refiner pipeline |
| `--cpu` | off | Force CPU mode (no GPU) |

## Memory Management

The pipeline **automatically cleans up GPU memory** after each generation:
- Models are unloaded and garbage collected
- GPU cache is flushed (`torch.cuda.empty_cache()` / `torch.mps.empty_cache()`)
- Safe for batch processing and long-running applications
- Exception-safe: cleanup runs even if generation fails

## Testing

**Regression tests (stable):** 22 pytest tests covering memory management, device handling, and error cases — all pass in ~2 seconds, no GPU required.

**TDD suites (in development):** Additional test files for features in progress (batch generation, OOM handling) are expected to have failing tests during development.

```bash
# Run the regression test suite (no GPU required)
pytest tests/test_memory_cleanup.py -v

# Run all tests including TDD in-progress suites
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
