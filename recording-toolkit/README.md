# Recording Toolkit

Scripts, config, and guides for creating terminal demo recordings and GIFs.

## Tools

- **[asciinema](https://asciinema.org/)** — records terminal sessions to `.cast` files
- **[agg](https://github.com/asciinema/agg)** — converts `.cast` files to animated GIFs (install: `cargo install agg`)
- **[ffmpeg](https://ffmpeg.org/)** — converts GIFs to web-optimized MP4 (install: `sudo apt-get install ffmpeg` or `winget install ffmpeg`)
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
| `--format` | `-Format` | gif | Output format: `gif` or `mp4` (MP4 requires ffmpeg) |

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

## Recording Plans

A recording plan is a JSON file that automates a two-phase recording workflow:

1. **Pre-record phase** — runs setup commands silently (install tools, cd, set env vars), then clears the screen
2. **Record phase** — starts asciinema, auto-types demo commands with realistic keystroke delays, waits for output

Plans live in `recordings/plans/`. See `recordings/plans/copilot-cli-demo.json` for a working example.

### Plan JSON Format

```json
{
  "name": "my-demo",
  "description": "Optional human-readable description",
  "pre_record": {
    "commands": [
      "cd /mnt/c/my-project",
      "export PS1='$ '"
    ],
    "clear_screen": true
  },
  "record": {
    "commands": [
      { "type": "command", "value": "gh --version", "wait_for_output": true, "pause_after": 1.5 },
      { "type": "pause",   "duration": 1.0 }
    ],
    "typing_speed": "medium",
    "default_pause": 1.0
  },
  "output": {
    "subdir": "cli",
    "convert": { "preset": "blog-landscape", "format": "both", "no_loop": true }
  }
}
```

### Plan Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Identifier used in output filename |
| `description` | no | Human-readable description |
| `pre_record.commands` | no | Shell commands run silently before recording |
| `pre_record.clear_screen` | no | If `true`, clears the terminal before recording starts |
| `record.commands` | yes | Array of command objects (see below) |
| `record.typing_speed` | no | `slow`, `medium` (default), or `fast` |
| `record.default_pause` | no | Seconds to pause after each command (default: `1.0`) |
| `output.subdir` | no | Subdirectory under `recordings/` for output (default: `cli`) |
| `output.convert.preset` | no | Auto-convert to GIF using this preset after recording |
| `output.convert.format` | no | Output format: `gif` (default), `mp4`, or `both` |
| `output.convert.no_loop` | no | If `true`, disables GIF animation looping |

### Command Types

| Type | Required Fields | Description |
|------|----------------|-------------|
| `command` | `value` | Auto-types the command, presses Enter, waits for output |
| `pause` | `duration` | Waits silently (dramatic effect, output rendering) |
| `type` | `value` | Types text without pressing Enter (partial input demos) |
| `key` | `value` | Sends a special key: `enter`, `ctrl-c`, `ctrl-d`, `tab` |

Command-type options:

| Option | Default | Description |
|--------|---------|-------------|
| `wait_for_output` | `false` | Wait after Enter for command output to render |
| `pause_after` | `default_pause` | Seconds to pause after this command |

### Typing Speed Presets

| Speed | Char delay | Variance | Use For |
|-------|------------|----------|---------|
| `slow` | 120 ms | ±40 ms | Accessibility, close-ups |
| `medium` | 60 ms | ±20 ms | Standard demos |
| `fast` | 30 ms | ±10 ms | Quick utility commands |

### Scripts

| Script | Description |
|--------|-------------|
| `scripts/run_plan.sh` | Bash runner — reads plan JSON and executes two-phase recording |
| `scripts/run_plan.ps1` | PowerShell wrapper — translates paths and calls `run_plan.sh` via WSL |

```bash
# Run a plan
./scripts/run_plan.sh recordings/plans/copilot-cli-demo.json

# Dry run — see what would execute without recording
./scripts/run_plan.sh recordings/plans/copilot-cli-demo.json --dry-run

# Skip GIF conversion
./scripts/run_plan.sh recordings/plans/copilot-cli-demo.json --no-convert

# Override output path
./scripts/run_plan.sh recordings/plans/copilot-cli-demo.json --output recordings/cli/my-demo.cast
```

PowerShell (Windows via WSL):

```powershell
.\scripts\run_plan.ps1 recordings\plans\copilot-cli-demo.json
.\scripts\run_plan.ps1 recordings\plans\copilot-cli-demo.json -DryRun
.\scripts\run_plan.ps1 recordings\plans\copilot-cli-demo.json -NoConvert
```

### Plan Workflow

```
1. Create plan JSON in recordings/plans/
2. Dry run to verify:  ./scripts/run_plan.sh <plan.json> --dry-run
3. Record:            ./scripts/run_plan.sh <plan.json>
4. GIF auto-converts if output.convert.preset is set
```

---

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

## FAQ

### Can MP4 videos loop like GIFs?

GIF has a built-in loop flag (controlled via `no_loop` in plan config). MP4 looping depends on the player — use the HTML `<video loop>` attribute for web playback. The toolkit doesn't add looping metadata to MP4 files, but any player can loop them.

### Do pre_record steps need to install all prerequisites every time?

No. WSL persists state between recordings — software installed via `apt-get` stays installed, and files created remain on disk. The `command -v tool || apt-get install tool` pattern in pre_record is idempotent: it only installs if the tool is missing. After the first run, subsequent recordings skip the install step automatically.

### Does WSL reset between recordings? Do files and software disappear?

No. WSL is a persistent Linux environment. Everything installed or created during pre_record and recording persists permanently (until manually deleted or WSL is reset with `wsl --unregister`). This means:

- Prerequisites only need to be installed once
- Test files from previous recordings persist in `/tmp/` or wherever created
- Environment variables set in pre_record persist only for that recording session (not across recordings)

### What output formats are supported?

The toolkit supports `gif`, `mp4`, or `both` via the `output.convert.format` plan field or `--format` CLI switch. GIF uses `agg` (asciinema GIF generator). MP4 converts the GIF to web-optimized MP4 via `ffmpeg` with `movflags faststart` for progressive loading. MP4 files are typically 40–60% smaller than equivalent GIFs.

### Can I record interactive programs like GitHub Copilot CLI?

The current toolkit uses auto-type + eval for non-interactive commands. Interactive programs (REPLs, Copilot CLI, etc.) that take over stdin are not yet supported. Options:

- Use `asciinema rec` directly (manual recording)
- Future: `expect`-based interactive command type is planned
