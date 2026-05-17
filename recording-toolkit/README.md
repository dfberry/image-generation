# Recording Toolkit

Scripts, config, and guides for creating terminal demo recordings and GIFs.

## Tools

- **[asciinema](https://asciinema.org/)** — records terminal sessions to `.cast` files
- **[agg](https://github.com/asciinema/agg)** — converts `.cast` files to animated GIFs (install: `cargo install agg`)
- **[ImageMagick](https://imagemagick.org/)** — optional, for watermark overlay

## Quick Start

```bash
# Record a terminal session (landscape, 120x30)
./scripts/record_cli.sh

# Convert to GIF with blog-friendly preset
./scripts/convert_cast_to_gif.sh recording.cast --preset blog-landscape

# Convert with custom settings
./scripts/convert_cast_to_gif.sh recording.cast --theme monokai --font-size 20 --cols 120 --rows 30
```

PowerShell equivalents:

```powershell
.\scripts\record_cli.ps1
.\scripts\convert_cast_to_gif.ps1 recording.cast -Preset blog-landscape
.\scripts\convert_cast_to_gif.ps1 recording.cast -Theme monokai -FontSize 20 -Cols 120 -Rows 30
```

## Configuration

### Priority Order

Settings are resolved in this order (highest priority first):

1. **CLI switches** — always win
2. **Preset** — from `--preset` / `-Preset`
3. **Config file defaults** — from `recording-config.json`
4. **Built-in defaults** — hardcoded in scripts

### Config File (`recording-config.json`)

The scripts auto-discover `recording-config.json` in the toolkit root directory. Override with `--config <path>`.

```json
{
  "defaults": {
    "theme": "asciinema",
    "speed": 1.5,
    "font_size": 14,
    "cols": 120,
    "rows": 30,
    "idle_time_limit": 3,
    "loop": true,
    "fps_cap": 30,
    "last_frame_duration": 3,
    "watermark_text": "",
    "output_dir": "recordings/cli"
  },
  "presets": {
    "blog-landscape": { "theme": "monokai", "speed": 1.5, "font_size": 16, "cols": 120, "rows": 30 },
    "blog-large":     { "theme": "monokai", "speed": 1.5, "font_size": 20, "cols": 100, "rows": 25 },
    "social-square":  { "theme": "dracula", "font_size": 16, "cols": 80, "rows": 40 },
    "compact":        { "theme": "nord", "font_size": 12, "cols": 80, "rows": 24, "speed": 2 }
  },
  "theme_aliases": {
    "dark": "asciinema",
    "light": "github-light",
    "gruvbox": "gruvbox-dark"
  }
}
```

### Presets

| Preset | Theme | Font | Cols × Rows | Speed | Use Case |
|--------|-------|------|-------------|-------|----------|
| `blog-landscape` | monokai | 16 | 120×30 | 1.5× | Blog posts, wide layout |
| `blog-large` | monokai | 20 | 100×25 | 1.5× | Blog posts, large text |
| `social-square` | dracula | 16 | 80×40 | 1× | Social media, square-ish |
| `compact` | nord | 12 | 80×24 | 2× | Compact demos, fast |

## Themes

Available themes (with aliases):

| Name | agg Value | Alias |
|------|-----------|-------|
| asciinema | `asciinema` | `dark` |
| dracula | `dracula` | |
| github-dark | `github-dark` | |
| github-light | `github-light` | `light` |
| monokai | `monokai` | |
| nord | `nord` | |
| solarized-dark | `solarized-dark` | |
| solarized-light | `solarized-light` | |
| gruvbox-dark | `gruvbox-dark` | `gruvbox` |

Use either the full name or alias: `--theme dark` is the same as `--theme asciinema`.

## Scripts Reference

### `convert_cast_to_gif.sh` / `convert_cast_to_gif.ps1`

Converts `.cast` files to `.gif` using agg.

| Option (bash) | Option (PS) | Default | Description |
|---------------|-------------|---------|-------------|
| `<file.cast>` | `-InputFile` | required | Input .cast file |
| `--theme` | `-Theme` | asciinema | Color theme |
| `--speed` | `-Speed` | 1.5 | Playback speed multiplier |
| `--font-size` | `-FontSize` | 14 | Font size in pixels |
| `--cols` | `-Cols` | — | Terminal width override |
| `--rows` | `-Rows` | — | Terminal height override |
| `--idle-limit` | `-IdleLimit` | 3 | Max idle time (seconds) |
| `--no-loop` | `-NoLoop` | — | Disable GIF loop |
| `--fps-cap` | `-FpsCap` | 30 | Max frames per second |
| `--last-frame-duration` | `-LastFrameDuration` | 3 | Last frame hold (seconds) |
| `--watermark-text` | `-WatermarkText` | — | Overlay text (needs ImageMagick) |
| `--orientation` | `-Orientation` | — | `landscape` (120×30) or `portrait` (40×80) |
| `--config` | `-Config` | auto | Path to config JSON |
| `--preset` | `-Preset` | — | Preset name from config |
| `--output` | `-OutputFile` | — | Override output file path |

### `record_cli.sh` / `record_cli.ps1`

Records terminal sessions using asciinema.

| Option (bash) | Option (PS) | Default | Description |
|---------------|-------------|---------|-------------|
| `--cols` | `-Cols` | 120 | Terminal width |
| `--rows` | `-Rows` | 30 | Terminal height |
| `--idle-limit` | `-IdleLimit` | 3 | Max idle time (seconds) |
| `--output-dir` | `-OutputDir` | recordings/cli | Output directory |
| `--config` | `-Config` | auto | Path to config JSON |
| `--preset` | `-Preset` | — | Preset name from config |
| `--orientation` | `-Orientation` | — | `landscape` (120×30) or `portrait` (40×80) |

## Example Workflows

### Record and convert with preset

```bash
# Record
./scripts/record_cli.sh --preset blog-landscape

# Convert the recording
./scripts/convert_cast_to_gif.sh recordings/cli/20260517-0930.cast --preset blog-landscape
```

### Record and convert with custom settings

```bash
# Record with wide terminal
./scripts/record_cli.sh --cols 140 --rows 35

# Convert with large font for readability
./scripts/convert_cast_to_gif.sh recordings/cli/20260517-0930.cast \
    --theme monokai --font-size 20 --cols 140 --rows 35 --speed 1.5
```

### Quick landscape GIF from existing recording

```bash
./scripts/convert_cast_to_gif.sh demo.cast --orientation landscape --theme dark --font-size 16
```

### Add watermark (requires ImageMagick)

```bash
./scripts/convert_cast_to_gif.sh demo.cast --preset blog-landscape --watermark-text "© Dina Berry"
```

## Notes

- **WSL on Windows**: asciinema requires a Unix terminal. On Windows, run recording scripts from WSL or use Windows Terminal with WSL.
- **Orientation**: The `--orientation` flag is a convenience shortcut. Explicit `--cols`/`--rows` always override it.
- **Config auto-discovery**: Scripts look for `recording-config.json` in the toolkit root (parent of `scripts/`) automatically.
- **Watermark**: Requires ImageMagick (`magick` command). If not installed, the GIF is created without watermark and a warning is shown.
- See `docs/` for detailed per-tool guides and `docs/azure_demo_best_practices.md` for demo structure guidance.
