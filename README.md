# image-generation

Python-based image generation using [Stable Diffusion XL Base 1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0).

## Setup

**Requirements:** Python 3.10+, NVIDIA GPU with 8GB+ VRAM recommended (~7GB disk for model weights)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
# Basic generation
python generate.py --prompt "Your prompt here"

# With refiner (higher quality, slower)
python generate.py --prompt "Your prompt here" --refine

# Reproducible output
python generate.py --prompt "Your prompt here" --seed 42 --refine

# Apple Silicon / CPU
python generate.py --prompt "Your prompt here" --cpu
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
| `--cpu` | off | Force CPU mode |

## Example Prompts

See [`prompts/examples.md`](prompts/examples.md) for curated tropical magical-realism prompts.

## License

- Model: [CreativeML Open RAIL++-M License](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md)
- Code: MIT
