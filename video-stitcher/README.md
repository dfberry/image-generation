# Video Stitcher

CLI tool to stitch multiple MP4 animations into a single video. Works with outputs from any source — just drop MP4 files into the `clips/` folder and run.

## Prerequisites

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and on PATH

## Setup

```bash
cd video-stitcher
pip install -e .
```

## Workflow

1. **Render** animations with `manim-gen`, `remotion-gen`, or any other tool
2. **Copy** the output MP4 files into the `clips/` drop folder
3. **Run** `stitch-video` — it processes everything in `clips/` alphabetically

```bash
# Copy outputs from sibling projects into the drop folder
cp ../manim-animation/outputs/intro.mp4 clips/01-intro.mp4
cp ../remotion-animation/outputs/demo.mp4 clips/02-demo.mp4
cp ../manim-animation/outputs/outro.mp4 clips/03-outro.mp4

# Stitch them all
stitch-video
```

> **Tip:** Prefix filenames with numbers (`01-`, `02-`, etc.) to control ordering.

## Usage

### Default — drop folder

```bash
stitch-video                          # reads all MP4s from clips/
stitch-video --clips-dir ./my-clips   # use a different drop folder
```

### Explicit inputs

```bash
stitch-video clip1.mp4 clip2.mp4 clip3.mp4
```

### With transitions

```bash
stitch-video --transition fade_to_black --transition-duration 1.5
```

### With quality preset

```bash
stitch-video --quality high --output outputs/final.mp4
```

### Playlist mode

Create a YAML playlist file (paths are relative to the playlist file location):

```yaml
# playlist.yaml
clips:
  - path: clips/01-intro.mp4
    title_card: "Chapter 1: Introduction"
    transition: fade_to_black
    transition_duration: 1.0
  - path: clips/02-demo.mp4
    title_card: "Chapter 2: Demo"
    transition: none
  - path: clips/03-outro.mp4
```

Run with the playlist:

```bash
stitch-video --playlist playlist.yaml --quality medium
```

JSON playlists are also supported:

```json
{
  "clips": [
    { "path": "clips/01-intro.mp4", "title_card": "Intro", "transition": "fade_to_black" },
    { "path": "clips/02-demo.mp4" }
  ]
}
```

## CLI Reference

```
stitch-video [OPTIONS] [INPUTS...]

Positional:
  INPUTS                    MP4 files to stitch (in order)

Options:
  --playlist PATH           JSON or YAML playlist file
  --clips-dir PATH          Drop folder for input clips (default: clips/)
  --output PATH             Output path (default: outputs/stitched_<timestamp>.mp4)
  --quality {low,medium,high}  Quality preset (default: medium)
  --transition {none,fade_to_black,crossfade}  Transition between clips (default: none)
  --transition-duration SEC Duration of transitions (default: 1.0)
  --debug                   Enable debug logging
```

## Quality Presets

| Preset | Resolution | FPS |
|--------|-----------|-----|
| low    | 854×480   | 15  |
| medium | 1280×720  | 30  |
| high   | 1920×1080 | 60  |

## Playlist Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | ✅ | Path to the MP4 file (relative to playlist file location) |
| `transition` | string | ❌ | `none`, `fade_to_black`, or `crossfade` (default: `none`) |
| `transition_duration` | float | ❌ | Transition duration in seconds (default: 1.0) |
| `title_card` | string | ❌ | Text to show as a title card before this clip |
| `title_duration` | float | ❌ | Title card duration in seconds (default: 3.0) |

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Input error (no clips, missing files, empty drop folder) |
| 2 | Playlist error (invalid format) |
| 3 | FFmpeg error (encoding failure) |
| 4 | Unexpected error |
