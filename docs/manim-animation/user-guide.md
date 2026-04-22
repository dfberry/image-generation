← [Back to Documentation Index](../README.md)

# User Guide — Manim Animation Generator

## What It Does

The Manim Animation Generator (`manim-gen`) creates mathematical and educational animations from plain English descriptions. You describe what you want, and the tool:

1. Sends your prompt to an LLM (local Ollama by default, or OpenAI/Azure)
2. Receives generated Manim Python code
3. Validates the code for safety and correctness
4. Renders the animation with Manim Community Edition
5. Outputs an MP4 video

No Manim knowledge required — just describe the animation you want.

## Quick Start

### Prerequisites

- Python 3.10+, FFmpeg, and Ollama installed (see [Installation Guide](installation.md))
- An Ollama model pulled: `ollama pull llama3`

### Your First Animation

```bash
manim-gen --prompt "A blue circle rotates and transforms into a red square"
```

Output: `outputs/video_YYYYMMDD_HHMMSS.mp4`

### Demo Mode

Generate a personalized title card without writing a prompt:

```bash
manim-gen --demo
```

## CLI Reference

```
manim-gen --prompt PROMPT [OPTIONS]
```

### Required (one of)

| Flag | Description |
|------|-------------|
| `--prompt TEXT` | Description of the animation to generate |
| `--demo` | Generate a personalized demo title card (no prompt needed) |

### Optional

| Flag | Default | Description |
|------|---------|-------------|
| `--output PATH` | `outputs/video_YYYYMMDD_HHMMSS.mp4` | Output video file path |
| `--quality {low,medium,high}` | `medium` | Video quality preset |
| `--duration INT` | `10` | Target duration in seconds (5–30) |
| `--provider {ollama,openai,azure}` | `ollama` | LLM provider |
| `--model TEXT` | Provider default | Override LLM model name |
| `--debug` | Off | Save intermediate scene code for inspection |
| `--image PATH [PATH ...]` | None | Image file(s) to include in the animation |
| `--image-descriptions TEXT` | None | Descriptions of the images for LLM context |
| `--image-policy {strict,warn,ignore}` | `strict` | Image validation policy |

## Quality Presets

| Preset | Resolution | FPS | Manim Flag | Best For |
|--------|-----------|-----|------------|----------|
| `low` | 480p | 15 | `-ql` | Quick previews, testing prompts |
| `medium` | 720p | 30 | `-qm` | General use, good balance of speed and quality |
| `high` | 1080p | 60 | `-qh` | Final output, presentations, sharing |

```bash
# Quick preview
manim-gen --prompt "Show a sine wave" --quality low

# Production quality
manim-gen --prompt "Visualize matrix multiplication" --quality high --duration 20
```

## Duration

Target duration range: **5 to 30 seconds**.

The duration is passed to the LLM as context — it uses `self.play()` timing and `self.wait()` pauses to approximate the target. Actual video length may vary slightly depending on what the LLM generates.

```bash
manim-gen --prompt "Count from 1 to 10" --duration 15
```

## Example Prompts

### Simple Shapes
```bash
manim-gen --prompt "A green triangle spins 360 degrees and fades out"
manim-gen --prompt "Three circles arranged in a triangle, then they swap positions"
```

### Math & Equations
```bash
manim-gen --prompt "Write the quadratic formula and highlight each term"
manim-gen --prompt "Show the Pythagorean theorem with a right triangle diagram"
manim-gen --prompt "Graph of f(x) = sin(x) with the function label"
```

### Educational
```bash
manim-gen --prompt "Visualize bubble sort with 5 colored bars"
manim-gen --prompt "Show a binary tree being built by inserting nodes 5, 3, 7, 1, 4"
```

### Text Animations
```bash
manim-gen --prompt "Title card: 'Introduction to Calculus' with fade in and fade out"
manim-gen --prompt "Count from 1 to 5 with each number centered on screen"
```

### With Images
```bash
manim-gen --prompt "Show the screenshot sliding in from the left" --image screenshot.png
manim-gen --prompt "Compare these two diagrams side by side" --image before.png after.png --image-descriptions "Before and after optimization"
```

## LLM Provider Switching

### Ollama (Default — Local, Free)

```bash
# Uses llama3 by default
manim-gen --prompt "Draw a circle"

# Use a different local model
manim-gen --prompt "Draw a circle" --model codellama

# Custom Ollama endpoint
export OLLAMA_HOST="http://my-gpu-server:11434"
manim-gen --prompt "Draw a circle"
```

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."

manim-gen --prompt "Draw a circle" --provider openai
manim-gen --prompt "Draw a circle" --provider openai --model gpt-4o
```

### Azure OpenAI

```bash
export AZURE_OPENAI_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"

manim-gen --prompt "Draw a circle" --provider azure
```

## Using Images

You can include image files in your animation:

```bash
# Single image
manim-gen --prompt "Zoom into the diagram" --image diagram.png

# Multiple images
manim-gen --prompt "Slide show of photos" --image photo1.png photo2.jpg photo3.png

# With descriptions (helps the LLM understand what's in the images)
manim-gen --prompt "Annotate the architecture" --image arch.png --image-descriptions "System architecture diagram showing microservices"
```

### Supported Image Formats

`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp`

> **Note**: `.svg` is not supported via `--image`. Manim uses `SVGMobject` for SVGs, not `ImageMobject`.

### Image Validation Policies

| Policy | Behavior |
|--------|----------|
| `strict` (default) | Rejects bad images with an error (exit code 5) |
| `warn` | Logs a warning and skips invalid images |
| `ignore` | Silently skips invalid images |

```bash
manim-gen --prompt "Show photos" --image a.png missing.png --image-policy warn
```

### Image Size Limit

Maximum file size: **100 MB** per image.

## Debug Mode

Use `--debug` to save the intermediate Manim scene code alongside the video. This is invaluable for troubleshooting:

```bash
manim-gen --prompt "Fibonacci spiral" --debug
```

This creates:
- `outputs/video_YYYYMMDD_HHMMSS.mp4` — the rendered video
- `outputs/video_YYYYMMDD_HHMMSS_scene.py` — the generated Manim code

You can then inspect, modify, and re-render the scene code manually:

```bash
manim render outputs/video_YYYYMMDD_HHMMSS_scene.py GeneratedScene -qm
```

## Output Format

All output is **MP4 video**. Videos are saved to the `outputs/` directory by default, with timestamped filenames:

```
outputs/video_20250101_143022.mp4
```

Override with `--output`:

```bash
manim-gen --prompt "Hello world" --output my_animation.mp4
```

## Troubleshooting

### "manim CLI not found"

Manim is not installed or not on PATH.

```bash
pip install manim
# Verify
manim --version
```

### "FFmpeg not found"

FFmpeg is required by Manim for video encoding.

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Verify
ffmpeg -version
```

### "LLM API call failed"

**For Ollama (default)**:
1. Ensure Ollama is running: `ollama serve`
2. Ensure a model is available: `ollama list`
3. Pull a model if needed: `ollama pull llama3`
4. Check the endpoint: `curl http://localhost:11434/api/tags`

**For OpenAI**:
1. Check API key: `echo $OPENAI_API_KEY`
2. Verify network connectivity
3. Check for rate limits or billing issues

**For Azure**:
1. Verify all three env vars are set: `AZURE_OPENAI_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`
2. Confirm the deployment exists and is accessible

### "Generated code has syntax error"

The LLM produced invalid Python code. Try:
1. **Rephrase your prompt** — be more specific about what you want
2. **Use `--debug`** to inspect the generated code
3. **Try a different model** — `--model codellama` or `--provider openai`
4. **Simplify** — break complex animations into simpler steps

### "Validation Error: Forbidden import"

The LLM generated code with disallowed imports. Only `manim`, `math`, and `numpy` are allowed. Try rephrasing your prompt to avoid requests that need other libraries.

### "Render failed" / Manim Errors

1. Check FFmpeg is installed: `ffmpeg -version`
2. Use `--debug` to save the scene code and try rendering manually
3. Lower quality for faster iteration: `--quality low`
4. Check Manim-specific errors in the stderr output

### Video Quality Issues

- Use `--quality high` for better resolution (1080p at 60fps)
- Increase `--duration` if animations feel too fast
- Rendering time varies: 30 seconds to 2+ minutes depending on complexity and quality

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | LLM error (API failure, missing credentials) |
| `2` | Validation error (generated code failed safety checks) |
| `3` | Render error (Manim/FFmpeg failure) |
| `4` | Unexpected error |
| `5` | Image validation error (bad path, format, size) |

## Phase 0 Limitations

This is a proof-of-concept with intentional scope limits:

- **Duration**: 5–30 seconds only
- **No audio**: Visual-only animations
- **Single scene**: No multi-scene compositions
- **2D only**: No 3D camera work
- **No template system**: Few-shot examples are embedded in code
- **Happy path focus**: Basic error handling

Future phases may add template libraries, multi-scene support, audio sync, 3D animations, and a web UI.
