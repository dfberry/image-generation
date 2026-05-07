# Story-to-Video

🎬 Orchestrate AI video generation from text stories

Story-to-Video is a Python CLI tool that takes a text story and automatically produces a multi-scene video by orchestrating existing AI video generation tools.

## Features

- **🤖 LLM-powered scene planning** - Automatically break stories into visual scenes
- **🎨 Multiple rendering styles** - Choose from image (Ken Burns), Remotion (dynamic), or Manim (diagrams)
- **🔄 Smart orchestration** - Routes each scene to the most appropriate renderer
- **📹 Automatic stitching** - Combines all scenes into a final video with transitions
- **🔍 Preflight checks** - Validates all dependencies before rendering
- **💾 Resume support** - Pick up where you left off if rendering fails
- **🎯 Flexible input** - Text files, inline prompts, or pre-structured scenes

## Installation

### Prerequisites

- Python >= 3.10
- ffmpeg
- Node.js (for Remotion renderer)
- Ollama (default LLM provider) or OpenAI/Azure API keys

### Install

```bash
cd story-to-video
pip install -r requirements.txt
pip install -e .
```

### Verify Installation

```bash
story-video doctor
```

This will check all dependencies and report any issues.

## Quick Start

### From a text file

```bash
story-video render --input examples/sample_story.txt --output my_story.mp4
```

### From an inline prompt

```bash
story-video render --prompt "A robot discovers emotions for the first time..." --output robot_story.mp4
```

### Plan only (no rendering)

```bash
story-video render --input story.txt --plan-only
```

This creates a `scenes.json` file you can edit, then render with:

```bash
story-video render --scenes story-video-outputs/runs/<your-run-id>/scenes.json
```

## Usage

### Basic Command

```bash
story-video render [OPTIONS]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input`, `-i` | Input story text file | - |
| `--prompt`, `-p` | Inline story prompt | - |
| `--scenes` | Pre-structured scenes JSON (skip LLM) | - |
| `--output`, `-o` | Output video filename | `final.mp4` |
| `--output-dir` | Base output directory for runs | `./story-video-outputs` |
| `--quality` | Video quality: low/medium/high | `medium` |
| `--scene-duration` | Target duration per scene (5-30s) | `30` |
| `--transition` | Transition style: none/fade_to_black/crossfade | `fade_to_black` |
| `--provider` | LLM provider: ollama/openai/azure | `ollama` |
| `--model` | LLM model name | `llama3.2` |
| `--style` | Visual style hint (auto/cinematic/minimal) | - |
| `--plan-only` | Only plan scenes, don't render | - |
| `--dry-run` | Show what would happen | - |
| `--continue-on-error` | Continue if a scene fails | - |
| `--resume` | Resume a failed run | - |
| `--force-renderer` | Force all scenes to use a specific renderer (image/remotion/manim) | - |
| `--renderer-strategy` | Routing strategy: auto/prefer-image/prefer-remotion | `auto` |

### Examples

**High quality with custom duration:**
```bash
story-video render \
  --input story.txt \
  --quality high \
  --scene-duration 20 \
  --transition crossfade
```

**Use OpenAI instead of Ollama:**
```bash
export OPENAI_API_KEY=sk-...
story-video render \
  --input story.txt \
  --provider openai \
  --model gpt-4o
```

**Resume a failed run:**
```bash
story-video render --resume story-video-outputs/runs/2026-05-06_143012/
```

**Cinematic style hint:**
```bash
story-video render \
  --prompt "A journey through space..." \
  --style cinematic
```

## How It Works

1. **📖 Scene Planning** - LLM analyzes the story and creates a structured scene plan with:
   - Visual style for each scene (image/remotion/manim)
   - Detailed prompts for generators
   - Scene duration and transitions
   - Narration text overlays

2. **🎨 Scene Rendering** - Each scene is routed to the appropriate renderer:
   - **Image renderer**: Generates still images with SDXL, applies Ken Burns effect + text overlay
   - **Remotion renderer**: Creates dynamic animations with Remotion framework
   - **Manim renderer**: Produces explanatory diagrams and visualizations

3. **🔗 Video Stitching** - All rendered clips are combined with transitions into the final video

## Architecture

```
story-to-video/
├── story_video/
│   ├── cli.py              # CLI entry point
│   ├── scene_planner.py    # LLM scene decomposition
│   ├── scene_renderer.py   # Renderer orchestration
│   ├── renderers/          # Renderer adapters
│   │   ├── image_renderer.py
│   │   ├── remotion_renderer.py
│   │   └── manim_renderer.py
│   ├── playlist_builder.py # YAML playlist generation
│   ├── doctor.py           # Preflight checks
│   ├── config.py           # Configuration & presets
│   └── models.py           # Pydantic data models
├── prompts/
│   └── scene_planning.md   # LLM system prompt
├── story-video-outputs/    # Default output (override with --output-dir or STORY_VIDEO_OUTPUT_DIR)
│   └── runs/               # Run directories
│       └── 2026-05-06_143012/
│           ├── story.txt
│           ├── scenes.json
│           ├── clips/
│           ├── playlist.yaml
│           ├── manifest.json
│           └── final.mp4
└── examples/
    └── sample_story.txt
```

## Output Directory Structure

Each run creates a timestamped directory in `story-video-outputs/runs/` (override with `--output-dir` or `STORY_VIDEO_OUTPUT_DIR` env var):

- `story.txt` - Copy of input story
- `scenes.json` - Structured scene plan
- `clips/` - Individual rendered scene videos
- `playlist.yaml` - Video stitcher playlist
- `manifest.json` - Complete run metadata
- `final.mp4` - Final stitched video

## Visual Styles

### Image (Ken Burns)
Best for: Atmospheric scenes, landscapes, portraits, establishing shots

- Generates high-quality still images with SDXL
- Applies slow zoom and pan (Ken Burns effect)
- Adds text overlay with narration
- Great for contemplative, mood-setting moments

### Remotion (Dynamic)
Best for: Action, motion, text animations, abstract visuals

- Uses Remotion generative animation framework
- Creates dynamic, moving content
- Good for energetic, modern styles
- Supports complex text animations

### Manim (Diagrams)
Best for: Explanations, data visualization, educational content

- Uses Manim mathematical animation engine
- Perfect for teaching and explaining concepts
- Shows processes, diagrams, and data

## LLM Providers

### Ollama (Default)
```bash
# Make sure Ollama is running
ollama serve

# Use default settings
story-video render --input story.txt
```

### OpenAI
```bash
export OPENAI_API_KEY=sk-...
story-video render --input story.txt --provider openai --model gpt-4o
```

### Azure OpenAI
```bash
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_ENDPOINT=...
story-video render --input story.txt --provider azure --model gpt-4
```

## Development

### Install dev dependencies

```bash
pip install -r requirements-dev.txt
```

### Run tests

```bash
pytest
```

### Format code

```bash
black story_video/
ruff check story_video/
```

### Type checking

```bash
mypy story_video/
```

## Troubleshooting

### "remotion-gen not found"
The tool looks for sibling directories. Ensure the repo structure is:
```
parent/
├── image-generation/
├── remotion-animation/
├── video-stitcher/
└── manim-animation/
```

### "Ollama not running"
```bash
ollama serve
```

### "ffmpeg not found"
Install ffmpeg:
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from https://ffmpeg.org/

### Rendering timeouts
Increase timeouts in `story_video/config.py` (default is 300 seconds):
```python
RENDER_TIMEOUT_IMAGE = 600  # Increase from 300 to 600 (10 minutes)
```

## Roadmap

- [ ] Parallel scene rendering (with file lock management)
- [ ] Full Manim integration with prompt-to-script generation
- [ ] Custom renderer plugins
- [ ] Audio narration with TTS
- [ ] Background music support
- [ ] Batch processing multiple stories
- [ ] Web UI

## License

MIT

## Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Add tests for new features
4. Submit a PR

## Related Projects

- [image-generation](../image-generation/) - SDXL image generation
- [remotion-animation](../remotion-animation/) - Remotion AI animations
- [video-stitcher](../video-stitcher/) - Video composition tool
- [manim-animation](../manim-animation/) - Mathematical animations
