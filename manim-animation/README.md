# Manim Animation Generator

AI-powered video generator that creates mathematical animations using Manim Community Edition. Describe what you want in plain English, and the tool generates the animation code and renders the video.

## What it does

This tool bridges natural language and mathematical animation:
1. You provide a text prompt describing an animation (e.g., "a blue circle morphs into a red square")
2. A local LLM (via Ollama) generates valid Manim scene code
3. Manim renders the scene to a high-quality MP4 video

Built for quick prototyping of educational math/CS visualizations with no Manim knowledge required.

## Prerequisites

- **Python 3.10+** (tested on 3.10, 3.11, 3.12)
- **FFmpeg** (required by Manim for video encoding)
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt install ffmpeg`
  - Windows: [Download from ffmpeg.org](https://ffmpeg.org/download.html)
- **Manim Community Edition** (installed via requirements.txt)
- **Ollama** (default, local inference — no API key needed)
  - Install: `curl -fsSL https://ollama.com/install.sh | sh`
  - Windows: [Download from ollama.com](https://ollama.com/download)
- **OpenAI SDK** (optional — only required for `--provider openai` or `--provider azure`)

## Installation

```bash
# Clone/navigate to this directory
cd manim-animation

# Install in editable mode (recommended for development)
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt

# For development (includes pytest, ruff)
pip install -r requirements-dev.txt
```

## Quick Start

### Using Ollama (default — local, no API key)

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3

# Generate a simple animation (default: 720p, 10 seconds)
manim-gen --prompt "A blue circle rotates and transforms into a red square"

# Use a specific local model
manim-gen --prompt "Visualize the Pythagorean theorem" --model codellama

# Custom Ollama endpoint
export OLLAMA_HOST="http://my-server:11434"
manim-gen --prompt "Sine wave animation"
```

### Alternative: Cloud LLM (OpenAI)

```bash
export OPENAI_API_KEY="sk-..."

manim-gen --prompt "A blue circle rotates and transforms into a red square" --provider openai

# High quality, longer duration
manim-gen --prompt "Visualize the Pythagorean theorem" --quality high --duration 15 --provider openai --output pythagorean.mp4
```

### Alternative: Cloud LLM (Azure OpenAI)

```bash
export AZURE_OPENAI_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://YOUR-RESOURCE.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"

manim-gen --prompt "Graph of f(x) = x^2" --provider azure
```

### Example Commands

```bash
# Simple shape animation
manim-gen --prompt "A green triangle spins and fades out" --quality low

# Math equation
manim-gen --prompt "Write the quadratic formula and highlight each term" --duration 12

# Multi-object scene
manim-gen --prompt "Three circles arranged in a triangle formation, then they swap positions"
```

## How it Works

```
User Prompt
    ↓
[LLM Client] ──→ Local LLM (Ollama) or cloud (OpenAI/Azure) generates Manim scene code
    ↓
[Scene Builder] ──→ Validates syntax, safety, structure
    ↓
[Renderer] ──→ Runs `manim render` subprocess
    ↓
MP4 Video (outputs/)
```

### Architecture

- **cli.py**: Argument parsing, main orchestration
- **llm_client.py**: Ollama/OpenAI/Azure API wrapper with few-shot examples
- **scene_builder.py**: Code extraction, AST validation, security checks
- **renderer.py**: Subprocess wrapper for `manim render` command
- **config.py**: Quality presets, system prompts, allowed imports
- **errors.py**: Custom exception types (LLMError, RenderError, ValidationError)

### Security

Generated code is validated before execution:
- **AST parsing** to check for forbidden imports (only `manim`, `math`, `numpy` allowed)
- **No file I/O** - blocks `open()`, `exec()`, `eval()`
- **Syntax check** via `compile()`
- **Class validation** - ensures `GeneratedScene` class exists

Code runs in a subprocess (Manim's CLI), isolated from the main process.

## Phase 0 Limitations

This is a proof-of-concept with intentional scope limits:
- **Duration**: 5-30 seconds only
- **No audio**: Visual-only animations
- **Single scene**: No multi-scene compositions
- **2D only**: No 3D camera work
- **Hardcoded prompts**: Few-shot examples embedded in code (no template system yet)
- **Happy path focus**: Basic error handling, not production-hardened

Future phases may add: template library, multi-scene support, audio sync, 3D animations, web UI.

## CLI Options

```
manim-gen --prompt PROMPT [OPTIONS]

Required:
  --prompt TEXT          Animation description

Optional:
  --output PATH          Output video path (default: outputs/video_YYYYMMDD_HHMMSS.mp4)
  --quality {low,medium,high}
                         Quality preset (default: medium)
                         low    = 480p @ 15fps
                         medium = 720p @ 30fps
                         high   = 1080p @ 60fps
  --duration INT         Target seconds (5-30, default: 10)
  --provider {ollama,openai,azure}
                         LLM provider (default: ollama)
  --model TEXT           Override default model (default: llama3 for Ollama, gpt-4 for OpenAI)
  --debug                Save intermediate scene code alongside video
```

## Troubleshooting

### "manim CLI not found"
- Install manim: `pip install manim`
- Check PATH: `which manim` (Unix) or `where manim` (Windows)

### "FFmpeg not found" (from Manim)
- Install FFmpeg (see Prerequisites)
- Verify: `ffmpeg -version`

### "LLM API call failed"
- For Ollama: ensure Ollama is running (`ollama serve`) and model is pulled (`ollama pull llama3`)
- For OpenAI: check API key is set: `echo $OPENAI_API_KEY`
- Verify network connection
- For Azure: confirm endpoint, key, and deployment name

### "Generated code has syntax error"
- Try rephrasing your prompt to be more specific
- Use `--debug` to inspect the generated code
- Some prompts may be too complex for the LLM - try breaking into simpler steps

### Video quality issues
- Use `--quality high` for better resolution
- Increase `--duration` if animations feel rushed
- Manim renders may take 30s-2min depending on complexity and quality

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run linter
ruff check manim_gen/

# Format code
ruff format manim_gen/

# Run tests (when Neo adds them)
pytest
```

## License

MIT (specify your license)

## Credits

- Built with [Manim Community Edition](https://www.manim.community/)
- LLM integration via [OpenAI Python SDK](https://github.com/openai/openai-python)
- Part of the `image-generation` multi-tool repository
