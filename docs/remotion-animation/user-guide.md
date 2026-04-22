← [Back to Documentation Index](../README.md)

# remotion-animation — User Guide

## What This Tool Does

**remotion-gen** turns natural language descriptions into animated MP4 videos. You describe what you want to see, an LLM generates a Remotion React component, and Remotion renders it to video.

```
"A blue circle rotating 360 degrees"  →  circle.mp4
```

The pipeline: **your prompt → LLM → TSX component → Remotion render → MP4**

## Quick Start with Ollama

Ollama is the default provider — free, local, no API key needed.

```bash
# 1. Make sure Ollama is running with a model
ollama serve &
ollama pull llama3

# 2. Generate a video
remotion-gen --prompt "A blue circle rotating 360 degrees" --output circle.mp4
```

No LLM? Try demo mode:
```bash
remotion-gen --demo --output demo.mp4
```

## CLI Flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--prompt` | Yes* | — | Animation description (what you want to see) |
| `--output` | Yes | — | Output video path (e.g., `video.mp4`) |
| `--quality` | No | `medium` | Video quality: `low`, `medium`, or `high` |
| `--duration` | No | `5` | Video duration in seconds (5–30) |
| `--provider` | No | `ollama` | LLM provider: `ollama`, `openai`, or `azure` |
| `--model` | No | auto | Override LLM model (e.g., `codellama`, `gpt-4`) |
| `--debug` | No | off | Save generated TSX to `outputs/GeneratedScene.debug.tsx` |
| `--demo` | No | off | Generate a demo title card (bypasses LLM, no `--prompt` needed) |
| `--image` | No | — | Path to an image file to include in the animation |
| `--image-description` | No | — | Description of the image for better LLM context |
| `--image-policy` | No | `strict` | Image validation: `strict`, `warn`, or `ignore` |

*`--prompt` is required unless using `--demo`.

## Quality Presets

| Preset | Resolution | FPS | Use Case |
|--------|-----------|-----|----------|
| `low` | 854×480 | 15 | Fast previews, iteration |
| `medium` | 1280×720 | 30 | Default, good balance |
| `high` | 1920×1080 | 60 | Final output, presentations |

```bash
# Quick preview
remotion-gen --prompt "Bouncing ball" --quality low --output preview.mp4

# Production quality
remotion-gen --prompt "Bouncing ball" --quality high --duration 10 --output final.mp4
```

## Demo Mode

Generate a pre-built title card animation without any LLM:

```bash
remotion-gen --demo --output demo.mp4
```

This produces a "Dina Berry" title card with spring animations and timestamps. Useful for verifying your installation works.

## Example Prompts

```bash
# Simple shape animation
remotion-gen --prompt "A blue circle rotating 360 degrees" --output circle.mp4

# Text animation
remotion-gen --prompt "Text saying 'Hello World' fading in and out" --output fade.mp4

# Multiple elements
remotion-gen --prompt "Multiple colorful squares bouncing around" --output bounce.mp4

# Sine wave
remotion-gen --prompt "A sine wave animating across the screen, white line on dark background" --output wave.mp4

# Higher quality, longer duration
remotion-gen --prompt "A progress bar filling from 0% to 100%" \
  --quality high --duration 10 --output progress.mp4

# With an image
remotion-gen --prompt "Zoom into my screenshot with a subtle parallax effect" \
  --image screenshot.png --image-description "App dashboard" --output zoom.mp4
```

## Debug Mode

When the generated video doesn't look right, use `--debug` to inspect the generated TSX:

```bash
remotion-gen --prompt "A rotating cube" --debug --output cube.mp4
```

This saves the LLM-generated component to `outputs/GeneratedScene.debug.tsx`. Open this file to see exactly what TSX code was generated, which helps diagnose animation issues.

## LLM Provider Switching

### Ollama (default)

Local inference, no API key. Default model: `llama3`.

```bash
remotion-gen --prompt "..." --output out.mp4                    # uses ollama
remotion-gen --prompt "..." --model codellama --output out.mp4  # different model
```

Custom Ollama host:
```bash
export OLLAMA_HOST="http://my-server:11434"
```

### OpenAI

Cloud inference with GPT-4. Requires `OPENAI_API_KEY`.

```bash
export OPENAI_API_KEY="sk-..."
remotion-gen --prompt "..." --provider openai --output out.mp4
```

### Azure OpenAI

Cloud inference via Azure. Requires three environment variables.

```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_KEY="your-key"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"
remotion-gen --prompt "..." --provider azure --output out.mp4
```

## Image Input

Include an image in your animation:

```bash
remotion-gen \
  --prompt "Animate my screenshot with a zoom effect" \
  --image screenshot.png \
  --image-description "Dashboard view of the app" \
  --output animated.mp4
```

Supported formats: PNG, JPG, JPEG, WebP, GIF, SVG (max 100 MB).

The `--image-policy` flag controls validation strictness:
- `strict` (default) — rejects symlinks, unsupported formats, oversized files
- `warn` — prints warnings but continues
- `ignore` — skips validation entirely

## Output Format

All output is **H.264 MP4**. The video codec is hardcoded to `h264` for maximum compatibility.

## Environment Variables

| Variable | Provider | Description |
|----------|----------|-------------|
| `OLLAMA_HOST` | ollama | Ollama endpoint (default: `http://localhost:11434`) |
| `OPENAI_API_KEY` | openai | OpenAI API key |
| `AZURE_OPENAI_KEY` | azure | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | azure | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | azure | Azure OpenAI deployment name |

## Troubleshooting

### "Node.js not found"

Install Node.js 18+ from [nodejs.org](https://nodejs.org/).

### "Dependencies not installed"

```bash
cd remotion-project && npm install
```

### "LLM API call failed"

- **Ollama**: ensure it's running (`ollama serve`) and model is pulled (`ollama pull llama3`)
- **OpenAI**: verify `OPENAI_API_KEY` is set
- **Azure**: verify all three Azure env vars are set

### "Remotion render failed"

- Check that `remotion-project/node_modules/` exists
- Try `--debug` to inspect the generated TSX
- Common issue: LLM generates invalid TSX — try a different model or re-run

### "Component validation failed"

The generated TSX failed structural validation. The LLM may have:
- Omitted the remotion import
- Used a wrong component name (must be `GeneratedScene`)
- Produced mismatched brackets
- Imported forbidden Node.js modules

Try re-running — LLM output varies per attempt. Or use `--debug` to inspect and manually fix.

### Video is blank or has artifacts

- Use `--debug` to inspect the TSX
- Try `--quality low` for faster iteration
- Rephrase your prompt to be more specific about colors, positions, and timing

### Windows PowerShell backtick issues

PowerShell treats backtick (`` ` ``) as an escape character. If your prompt contains template literals or backticks, save it in a Python script instead:

```python
# generate.py
from remotion_gen.cli import generate_video
generate_video(prompt="A sine wave animation", output="wave.mp4")
```

## Limitations

- **5–30 second videos** — enforced by CLI
- **Single-scene compositions** — no multi-scene sequencing
- **2D animations only** — no Three.js integration
- **No audio** — video-only output
- **LLM quality varies** — smaller local models may produce invalid TSX more often; use `--debug` and retry
