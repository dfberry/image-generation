← [Back to Documentation Index](../README.md)

# Installation Guide — image-generation

How to set up the image-generation tool.

## System Requirements

| Requirement | Minimum |
|-------------|---------|
| Python | 3.10+ |
| Disk space | ~7GB (for SDXL model weights, downloaded on first run) |
| RAM | 8GB+ recommended |
| OS | macOS, Linux, Windows |

## GPU Support Matrix

| Device | VRAM | Performance | Notes |
|--------|------|-------------|-------|
| **NVIDIA GPU (CUDA)** | 8GB+ | 2–5 min/image | Best performance. Gets `torch.compile` optimization. |
| **Apple Silicon (MPS)** | Unified memory | 5–10 min/image | Primary development target. Uses `enable_model_cpu_offload()`. |
| **CPU** | N/A | 20–30+ min/image | Fallback. Use `--cpu` flag. Float32 (no half-precision). |

**No GPU required for development/testing** — the test suite uses mocks and runs on CPU-only machines.

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/dfberry/image-generation.git
cd image-generation
```

The image-generation package is in the `image-generation/` subdirectory:

```bash
cd image-generation
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

```bash
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Dependencies

**For general use (minimum compatible versions):**

```bash
pip install -r requirements.txt
```

**For reproducible builds (CI/CD, exact versions):**

```bash
pip install -r requirements.lock
```

**For development (includes pytest, ruff, pytest-cov):**

```bash
pip install -r requirements-dev.txt
```

### Runtime Dependencies

| Package | Minimum Version | Purpose |
|---------|----------------|---------|
| `diffusers` | ≥0.21.0 | SDXL pipeline, schedulers |
| `transformers` | ≥4.30.0 | Text encoders (CLIP, OpenCLIP) |
| `accelerate` | ≥0.24.0 | Model loading, CPU offloading |
| `safetensors` | ≥0.3.0 | Safe model weight format |
| `invisible-watermark` | ≥0.2.0 | SDXL watermark handling |
| `torch` | ≥2.1.0 | Tensor operations, GPU support |
| `Pillow` | ≥10.0.0 | Image saving (PNG) |

### Dev Dependencies (in addition to runtime)

| Package | Minimum Version | Purpose |
|---------|----------------|---------|
| `pytest` | ≥7.0 | Test runner |
| `ruff` | ≥0.4.0 | Linter and formatter |
| `pytest-cov` | ≥4.0 | Test coverage |

### CUDA-Specific PyTorch Installation

For NVIDIA GPUs, install PyTorch with CUDA support:

```bash
# CUDA 11.8
pip install torch --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

For CPU-only (CI or machines without GPU):

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Makefile Setup (Alternative)

```bash
make setup      # Creates venv + installs dev deps
make install    # Runtime deps only
```

## Verifying Installation

### 1. Check Python Version

```bash
python --version
# Should be 3.10 or higher
```

### 2. Check Dependencies

```bash
python -c "import diffusers; print('diffusers:', diffusers.__version__)"
python -c "import torch; print('torch:', torch.__version__)"
python -c "import transformers; print('transformers:', transformers.__version__)"
```

### 3. Check GPU Detection

```bash
python -c "
import torch
print('CUDA available:', torch.cuda.is_available())
if hasattr(torch.backends, 'mps'):
    print('MPS available:', torch.backends.mps.is_available())
print('Device count:', torch.cuda.device_count() if torch.cuda.is_available() else 0)
"
```

### 4. Run Tests (No GPU Required)

```bash
python -m pytest tests/ -v
```

All 170+ tests should pass without a GPU.

### 5. Quick Generation Test (Requires GPU or Patience)

```bash
# Minimal test — CPU mode, low steps
python generate.py --prompt "test" --cpu --steps 2 --width 64 --height 64
```

This will download ~7GB of model weights on first run.

## Environment Variables

No environment variables are required for basic operation. The tool auto-detects the best available device.

### Optional Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | For LLM-powered prompt generation features (optional, not used by core pipeline) |
| `HF_HOME` | Override Hugging Face cache directory (default: `~/.cache/huggingface`) |
| `TORCH_HOME` | Override PyTorch cache directory |
| `CUDA_VISIBLE_DEVICES` | Restrict which GPUs are visible (e.g., `0` for first GPU only) |

## Model Downloads

On first run, the tool downloads SDXL model weights from Hugging Face:

| Model | Size | Downloaded When |
|-------|------|----------------|
| SDXL Base 1.0 | ~7GB | Always (on first `generate()` call) |
| SDXL Refiner 1.0 | ~6GB | Only when `--refine` is used |

Models are cached in `~/.cache/huggingface/hub/` by default.

### Offline Usage

After the first download, the tool works fully offline. Models are loaded from the local cache.

## Troubleshooting Installation

### `ModuleNotFoundError: No module named 'torch'`

Ensure you activated the virtual environment:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### `RuntimeError: Numpy is not available` (on Apple Silicon)

Install numpy compatible with ARM:
```bash
pip install numpy
```

### CUDA version mismatch

Check your CUDA version and install matching PyTorch:
```bash
nvidia-smi  # Shows CUDA version
```

### Slow model download

HuggingFace downloads can be slow. Use `HF_HUB_ENABLE_HF_TRANSFER=1` with `pip install hf-transfer` for faster downloads.
