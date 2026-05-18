# Skill: recording-toolkit

## Overview

The recording toolkit creates polished demo recordings for blog posts, social media, and documentation. It supports two recording types:

- **Terminal recording** — captures CLI sessions via asciinema, produces `.cast` → `.gif` / `.mp4`
- **Desktop recording** — captures full-screen video via mss + FFmpeg while automating VS Code and Copilot CLI via Python

Both types are driven by JSON plan files in `recordings/plans/` and share configuration via `recording-toolkit/recording-config.json`.

## When to Use Terminal Recording vs Desktop Recording

| Scenario | Use |
|----------|-----|
| Pure CLI demo (commands + output) | Terminal |
| VS Code UI interactions | Desktop |
| Copilot CLI inside VS Code terminal | Desktop |
| Mouse-driven workflows | Desktop |
| Interactive TUI in terminal | Terminal (with `interactive` command type) |
| Quick GIF for README | Terminal |
| Full developer experience video | Desktop |

## Terminal Recording (existing)

### Prerequisites

- **asciinema** — records terminal sessions
- **agg** — converts `.cast` to animated GIF (`cargo install agg`)
- **ffmpeg** — converts GIF to MP4
- **WSL** — required on Windows (asciinema needs Unix terminal)

### Quick Start

```bash
# Record a terminal session
./scripts/record_cli.sh

# Convert to GIF with preset
./scripts/convert_cast_to_gif.sh recording.cast --preset blog-landscape

# Run an automated plan
./scripts/run_plan.sh recordings/plans/copilot-cli-test.json
```

### Plan Format (Terminal)

```json
{
  "name": "my-demo",
  "pre_record": { "commands": ["cd /path", "export PS1='$ '"], "clear_screen": true },
  "record": {
    "commands": [
      { "type": "command", "value": "echo hello", "wait_for_output": true, "pause_after": 1.5 }
    ],
    "typing_speed": "medium",
    "default_pause": 1.0
  },
  "output": { "subdir": "cli", "convert": { "preset": "blog-landscape" } }
}
```

### Running a Terminal Plan

```bash
./scripts/run_plan.sh recordings/plans/copilot-cli-test.json
./scripts/run_plan.sh recordings/plans/copilot-cli-test.json --dry-run
```

## Desktop Recording (new)

### Prerequisites

```bash
# Python packages
pip install pyautogui mss opencv-python numpy

# System tools
winget install ffmpeg
winget install Microsoft.VisualStudioCode
npm install -g @github/copilot

# Verify everything
python recording-toolkit/scripts/check_prereqs.py
```

### Quick Start

```bash
# Standalone capture (5 seconds, full desktop)
python recording-toolkit/scripts/record_desktop.py --output recordings/desktop/test.mp4 --duration 5

# Dry-run (shows FFmpeg command without recording)
python recording-toolkit/scripts/record_desktop.py --output test.mp4 --dry-run

# Plan-driven recording
python recording-toolkit/scripts/demo_plan_runner.py recordings/plans/vscode-copilot-demo.json

# Via unified plan runner (auto-dispatches by type)
./scripts/run_plan.sh recordings/plans/vscode-copilot-demo.json
```

### Plan Type: `"desktop"`

Desktop plans use `"type": "desktop"` in the JSON. The plan runner auto-dispatches to `demo_plan_runner.py`.

```json
{
  "name": "vscode-copilot-demo",
  "description": "Full VS Code + Copilot CLI desktop recording",
  "type": "desktop",
  "pre_record": { "commands": ["pip install pyautogui mss numpy"] },
  "capture": { "mode": "full", "fps": 30, "resolution": [1920, 1080] },
  "steps": [
    { "action": "launch", "program": "code", "args": ["C:\\my-project"], "wait": 5 },
    { "action": "hotkey", "keys": ["ctrl", "`"], "wait": 1 },
    { "action": "type", "text": "copilot -p \"Tell me a joke\" --allow-all", "interval": 0.04 },
    { "action": "press", "key": "enter", "wait": 20 },
    { "action": "pause", "wait": 3 },
    { "action": "hotkey", "keys": ["ctrl", "d"] }
  ],
  "output": { "subdir": "desktop" }
}
```

#### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Used in output filename |
| `type` | yes | Must be `"desktop"` |
| `pre_record.commands` | no | Setup commands before recording |
| `capture.mode` | no | `"full"` (default) or `"region"` |
| `capture.fps` | no | Frames per second (default: 30) |
| `capture.resolution` | no | `[width, height]` (default: `[1920, 1080]`) |
| `capture.region` | no | `[x, y, w, h]` when mode is `"region"` |
| `steps` | yes | Array of automation steps |
| `output.subdir` | no | Output subdirectory (default: `"desktop"`) |

### Step Actions Reference

| Action | Required fields | Optional | Description |
|--------|----------------|----------|-------------|
| `launch` | `program` | `args`, `wait` | Start an application |
| `hotkey` | `keys` | `wait` | Key combination |
| `type` | `text` | `interval`, `wait` | Type text character-by-character |
| `press` | `key` | `wait` | Press a single key |
| `click` | `x`, `y` | `wait` | Left-click at coordinates |
| `right_click` | `x`, `y` | `wait` | Right-click at coordinates |
| `move` | `x`, `y` | `duration`, `wait` | Move mouse |
| `scroll` | `x`, `y`, `clicks` | `wait` | Scroll wheel |
| `pause` | — | `wait` | No-op; delay only |
| `screenshot` | — | `filename`, `wait` | Checkpoint screenshot |

### GPU Detection and Encoder Override

The recording engine probes GPU encoders at startup:

1. `h264_nvenc` (NVIDIA)
2. `h264_amf` (AMD)
3. `h264_qsv` (Intel)
4. `libx264` (CPU fallback — always available)

Override with `--encoder libx264` to force CPU encoding (useful for debugging or CI).

### Running a Desktop Plan

```bash
# Full recording
./scripts/run_plan.sh recordings/plans/vscode-copilot-demo.json

# Dry-run (no recording, no side effects)
./scripts/run_plan.sh recordings/plans/vscode-copilot-demo.json --dry-run

# PowerShell
.\scripts\run_plan.ps1 recordings\plans\vscode-copilot-demo.json
.\scripts\run_plan.ps1 recordings\plans\vscode-copilot-demo.json -DryRun
```

### Output Location

Desktop recordings are saved to `recordings/desktop/{plan-name}-{YYYYMMDD-HHmm}.mp4`.

This directory is gitignored — MP4 files are large binary artifacts.

### Troubleshooting

| Issue | Fix |
|-------|-----|
| DPI mismatch (wrong frame size) | Ensure `ctypes.windll.user32.SetProcessDPIAware()` runs first |
| FFmpeg not found | `winget install ffmpeg` and restart terminal |
| Copilot auth failure | Run `gh auth login` or set `GH_TOKEN` env var |
| Import order error | `mss` must be imported before `pyautogui` |

## Example Plans

### Terminal: `copilot-cli-test.json`

One-shot Copilot CLI demo showing `copilot -p` with a programming prompt.

### Desktop: `vscode-copilot-demo.json`

Full VS Code + Copilot CLI desktop recording — opens VS Code, toggles terminal, types a Copilot prompt, waits for response.

### Desktop: `vscode-copilot-interactive.json`

Interactive Copilot TUI session — launches `copilot` in interactive mode, types a prompt, captures the TUI response.

## Presets Reference

### Terminal Presets

| Preset | Theme | Font | Cols × Rows | Speed |
|--------|-------|------|-------------|-------|
| `blog-landscape` | monokai | 16 | 120×30 | 1.5× |
| `blog-large` | monokai | 20 | 100×25 | 1.5× |
| `social-square` | dracula | 16 | 80×40 | 1× |
| `compact` | nord | 12 | 80×24 | 2× |

### Desktop Presets

| Preset | Resolution | FPS | Encoder |
|--------|-----------|-----|---------|
| `demo-fullscreen` | 1920×1080 | 30 | auto |
| `demo-720p` | 1280×720 | 30 | auto |
| `quick-test` | 1280×720 | 15 | libx264 |
| `social-widescreen` | 1920×1080 | 24 | auto |
