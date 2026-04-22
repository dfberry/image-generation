← [Back to Documentation Index](../README.md)

# Installation Guide — Manim Animation Generator

## System Requirements

| Requirement | Details |
|-------------|---------|
| **Python** | 3.10 or higher (tested on 3.10, 3.11, 3.12) |
| **FFmpeg** | Required by Manim for video encoding |
| **Ollama** | Default LLM provider — local, free, no API key |
| **Node.js** | **NOT needed** — this is a Python-only tool |
| **LaTeX** | Optional — only needed for `MathTex` (not required for `Text`-based animations) |

## Step 1: Install FFmpeg

FFmpeg is required by Manim Community Edition for rendering video files.

### macOS

```bash
brew install ffmpeg
```

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install ffmpeg
```

### Windows

1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your system PATH

### Verify FFmpeg

```bash
ffmpeg -version
```

## Step 2: Install Ollama (Default LLM Provider)

Ollama provides local LLM inference — no API key, no cloud dependency, completely free.

### macOS / Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Windows

Download from [ollama.com/download](https://ollama.com/download)

### Pull a Model

```bash
# Recommended general-purpose model
ollama pull llama3

# Alternative: code-focused model
ollama pull codellama
```

### Verify Ollama

```bash
# Start Ollama (if not already running)
ollama serve

# Test it works
ollama list
```

Ollama runs on `http://localhost:11434` by default. You can change this with the `OLLAMA_HOST` environment variable:

```bash
export OLLAMA_HOST="http://my-server:11434"
```

## Step 3: Install manim-gen

```bash
# Navigate to the manim-animation directory
cd manim-animation

# Install in editable mode (recommended for development)
pip install -e .

# Or install dependencies directly (without CLI command)
pip install -r requirements.txt
```

Editable mode (`-e .`) installs the `manim-gen` CLI command and links it to your local source. Changes to the code take effect immediately without reinstalling.

### For Development

```bash
pip install -r requirements-dev.txt
```

This adds `pytest` and `ruff` for testing and linting.

## Step 4: Verify Installation

```bash
# Check the CLI is available
manim-gen --help
```

Expected output:
```
usage: manim-gen --prompt PROMPT [OPTIONS]

Generate animated videos using AI and Manim

optional arguments:
  --prompt TEXT          Animation description
  --output PATH         Output video path
  --quality {low,medium,high}
  --duration INT        Target seconds (5-30)
  --provider {ollama,openai,azure}
  --model TEXT          Override default model
  --debug               Save intermediate scene code
  --image PATH [PATH ...] Image file(s) to include
  --image-descriptions TEXT
  --image-policy {strict,warn,ignore}
  --demo                Generate personalized demo title card
```

### Quick Smoke Test

```bash
# Generate a simple animation (requires Ollama running with llama3)
manim-gen --prompt "A blue circle appears and fades out" --quality low
```

## Optional: OpenAI Setup

If you want to use OpenAI instead of local Ollama:

```bash
export OPENAI_API_KEY="sk-..."

manim-gen --prompt "Visualize the quadratic formula" --provider openai
```

Default model: `gpt-4`. Override with `--model gpt-4o` or any model you have access to.

## Optional: Azure OpenAI Setup

```bash
export AZURE_OPENAI_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"

manim-gen --prompt "Show sine and cosine waves" --provider azure
```

All three environment variables are required for Azure. The deployment name is used as the model name.

## Optional: LaTeX (for MathTex)

LaTeX is only needed if you want to render mathematical equations using `MathTex`. The `Text` class works without LaTeX.

### macOS

```bash
brew install --cask mactex-no-gui
```

### Ubuntu / Debian

```bash
sudo apt install texlive-full
```

### Windows

Download [MiKTeX](https://miktex.org/download) or [TeX Live](https://tug.org/texlive/).

## Dependencies

### Runtime (`requirements.txt` / `pyproject.toml`)

| Package | Version | Purpose |
|---------|---------|---------|
| `manim` | `>=0.18.0,<0.20.0` | Animation rendering engine |
| `openai` | `>=1.0.0,<2.0.0` | LLM API client (used by all providers including Ollama) |

### Development (`requirements-dev.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | `>=7.0.0` | Test framework |
| `ruff` | `>=0.1.0` | Linter and formatter |

## Troubleshooting Installation

### "manim-gen: command not found"

- Ensure you ran `pip install -e .` from the `manim-animation/` directory
- Check your Python environment is activated (virtualenv/conda)
- Verify: `which manim-gen` (Unix) or `where manim-gen` (Windows)

### "manim CLI not found" (at runtime)

- Manim installs automatically with `pip install -e .` (it's in `pyproject.toml` dependencies)
- Verify: `manim --version`
- If missing: `pip install manim`

### "FFmpeg not found" (from Manim)

- Install FFmpeg (see Step 1 above)
- Verify it's on PATH: `ffmpeg -version`

### "Cannot connect to Ollama"

- Ensure Ollama is running: `ollama serve`
- Check the port: `curl http://localhost:11434/api/tags`
- If using a custom host: set `OLLAMA_HOST` env var

### "No module named 'openai'"

- The `openai` package is required even for Ollama (it uses the OpenAI-compatible API)
- Install: `pip install openai>=1.0.0`
