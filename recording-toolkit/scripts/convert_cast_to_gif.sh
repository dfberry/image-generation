#!/bin/bash
set -e
# Convert asciinema .cast to .gif using agg
# Requires: cargo install agg
# Supports config file presets and full CLI override

show_help() {
    cat <<'EOF'
Usage: convert_cast_to_gif.sh <file.cast> [options]

Options:
  --theme <name>              Color theme (dark, dracula, github-dark, github-light, monokai, nord, solarized-dark, solarized-light, gruvbox)
  --speed <n>                 Playback speed multiplier (default: 1.5)
  --font-size <n>             Font size in pixels (default: 14)
  --cols <n>                  Terminal width in columns
  --rows <n>                  Terminal height in rows
  --idle-limit <n>            Max idle time in seconds (default: 3)
  --no-loop                   Disable GIF animation loop
  --fps-cap <n>               Max frames per second (default: 30)
  --last-frame-duration <n>   Duration of last frame in seconds (default: 3)
  --watermark-text <text>     Text to overlay on GIF (requires ImageMagick)
  --orientation <preset>      Preset dimensions: landscape (120x30), portrait (40x80)
  --config <path>             Path to config JSON file
  --preset <name>             Preset name from config file
  --output <path>             Override output file path
  --help                      Show this help

Priority: CLI switches > preset > config defaults > built-in defaults

Examples:
  ./convert_cast_to_gif.sh demo.cast
  ./convert_cast_to_gif.sh demo.cast --preset blog-landscape
  ./convert_cast_to_gif.sh demo.cast --theme monokai --font-size 20 --orientation landscape
  ./convert_cast_to_gif.sh demo.cast --config ./recording-config.json --preset compact
EOF
    exit 0
}

# --- Built-in defaults ---
THEME="asciinema"
SPEED="1.5"
FONT_SIZE="14"
COLS=""
ROWS=""
IDLE_LIMIT="3"
LOOP="true"
FPS_CAP="30"
LAST_FRAME_DURATION="3"
WATERMARK_TEXT=""
ORIENTATION=""
CONFIG_PATH=""
PRESET=""
OUTPUT_FILE=""
INPUT_FILE=""
COLS_FROM_CLI="false"
ROWS_FROM_CLI="false"

# --- Parse arguments ---
while [ $# -gt 0 ]; do
    case "$1" in
        --help)            show_help ;;
        --theme)           THEME="$2"; shift 2 ;;
        --speed)           SPEED="$2"; shift 2 ;;
        --font-size)       FONT_SIZE="$2"; shift 2 ;;
        --cols)            COLS="$2"; COLS_FROM_CLI="true"; shift 2 ;;
        --rows)            ROWS="$2"; ROWS_FROM_CLI="true"; shift 2 ;;
        --idle-limit)      IDLE_LIMIT="$2"; shift 2 ;;
        --no-loop)         LOOP="false"; shift ;;
        --fps-cap)         FPS_CAP="$2"; shift 2 ;;
        --last-frame-duration) LAST_FRAME_DURATION="$2"; shift 2 ;;
        --watermark-text)  WATERMARK_TEXT="$2"; shift 2 ;;
        --orientation)     ORIENTATION="$2"; shift 2 ;;
        --config)          CONFIG_PATH="$2"; shift 2 ;;
        --preset)          PRESET="$2"; shift 2 ;;
        --output)          OUTPUT_FILE="$2"; shift 2 ;;
        -*)                echo "Error: unknown option $1"; exit 1 ;;
        *)
            if [ -z "$INPUT_FILE" ]; then
                INPUT_FILE="$1"
            else
                echo "Error: unexpected argument $1"
                exit 1
            fi
            shift ;;
    esac
done

if [ -z "$INPUT_FILE" ]; then
    echo "Error: input .cast file required."
    echo "Usage: convert_cast_to_gif.sh <file.cast> [options]"
    exit 1
fi

# Track which settings came from CLI (before config/preset override)
CLI_THEME="$THEME"
CLI_SPEED="$SPEED"
CLI_FONT_SIZE="$FONT_SIZE"
CLI_IDLE_LIMIT="$IDLE_LIMIT"
CLI_LOOP="$LOOP"
CLI_FPS_CAP="$FPS_CAP"
CLI_LAST_FRAME_DURATION="$LAST_FRAME_DURATION"
CLI_WATERMARK_TEXT="$WATERMARK_TEXT"

# Reset to built-in defaults before layering config
THEME="asciinema"
SPEED="1.5"
FONT_SIZE="14"
COLS_CFG=""
ROWS_CFG=""
IDLE_LIMIT="3"
LOOP="true"
FPS_CAP="30"
LAST_FRAME_DURATION="3"
WATERMARK_TEXT=""

# --- JSON helper (works without jq if Python3 is available) ---
json_get() {
    local file="$1" query="$2"
    if command -v jq >/dev/null 2>&1; then
        jq -r "$query // empty" "$file" 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json, sys
data = json.load(open('$file'))
keys = '''$query'''.strip('.').split('.')
val = data
for k in keys:
    if isinstance(val, dict) and k in val:
        val = val[k]
    else:
        sys.exit(0)
if val is not None and val != '':
    print(val)
" 2>/dev/null
    fi
}

# --- Load config file ---
if [ -z "$CONFIG_PATH" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    AUTO_CONFIG="$(dirname "$SCRIPT_DIR")/recording-config.json"
    if [ -f "$AUTO_CONFIG" ]; then
        CONFIG_PATH="$AUTO_CONFIG"
    fi
fi

if [ -n "$CONFIG_PATH" ] && [ -f "$CONFIG_PATH" ]; then
    val=$(json_get "$CONFIG_PATH" ".defaults.theme");              [ -n "$val" ] && THEME="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.speed");              [ -n "$val" ] && SPEED="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.font_size");          [ -n "$val" ] && FONT_SIZE="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.cols");               [ -n "$val" ] && COLS_CFG="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.rows");               [ -n "$val" ] && ROWS_CFG="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.idle_time_limit");    [ -n "$val" ] && IDLE_LIMIT="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.loop");               [ -n "$val" ] && LOOP="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.fps_cap");            [ -n "$val" ] && FPS_CAP="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.last_frame_duration");[ -n "$val" ] && LAST_FRAME_DURATION="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.watermark_text");     [ -n "$val" ] && WATERMARK_TEXT="$val"
fi

# Apply config cols/rows only if CLI didn't set them
[ "$COLS_FROM_CLI" = "false" ] && [ -n "$COLS_CFG" ] && COLS="$COLS_CFG"
[ "$ROWS_FROM_CLI" = "false" ] && [ -n "$ROWS_CFG" ] && ROWS="$ROWS_CFG"

# --- Apply preset ---
if [ -n "$PRESET" ]; then
    if [ -z "$CONFIG_PATH" ] || [ ! -f "$CONFIG_PATH" ]; then
        echo "Error: --preset requires a config file (use --config or place recording-config.json in toolkit root)"
        exit 1
    fi
    # Check preset exists
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.theme")
    if [ -z "$val" ] && [ -z "$(json_get "$CONFIG_PATH" ".presets.$PRESET.speed")" ]; then
        echo "Error: preset '$PRESET' not found in config file."
        exit 1
    fi
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.theme");     [ -n "$val" ] && THEME="$val"
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.speed");     [ -n "$val" ] && SPEED="$val"
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.font_size"); [ -n "$val" ] && FONT_SIZE="$val"
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.cols");      [ -n "$val" ] && [ "$COLS_FROM_CLI" = "false" ] && COLS="$val"
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.rows");      [ -n "$val" ] && [ "$ROWS_FROM_CLI" = "false" ] && ROWS="$val"
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.idle_time_limit");    [ -n "$val" ] && IDLE_LIMIT="$val"
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.fps_cap");            [ -n "$val" ] && FPS_CAP="$val"
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.last_frame_duration");[ -n "$val" ] && LAST_FRAME_DURATION="$val"
fi

# --- Apply CLI overrides (highest priority) ---
[ "$CLI_THEME" != "asciinema" ]    && THEME="$CLI_THEME"
[ "$CLI_SPEED" != "1.5" ]         && SPEED="$CLI_SPEED"
[ "$CLI_FONT_SIZE" != "14" ]      && FONT_SIZE="$CLI_FONT_SIZE"
[ "$CLI_IDLE_LIMIT" != "3" ]      && IDLE_LIMIT="$CLI_IDLE_LIMIT"
[ "$CLI_LOOP" = "false" ]         && LOOP="false"
[ "$CLI_FPS_CAP" != "30" ]        && FPS_CAP="$CLI_FPS_CAP"
[ "$CLI_LAST_FRAME_DURATION" != "3" ] && LAST_FRAME_DURATION="$CLI_LAST_FRAME_DURATION"
[ -n "$CLI_WATERMARK_TEXT" ]       && WATERMARK_TEXT="$CLI_WATERMARK_TEXT"

# --- Apply orientation (if no explicit cols/rows from CLI) ---
if [ -n "$ORIENTATION" ] && [ "$COLS_FROM_CLI" = "false" ] && [ "$ROWS_FROM_CLI" = "false" ]; then
    case "$ORIENTATION" in
        landscape) COLS="120"; ROWS="30" ;;
        portrait)  COLS="40";  ROWS="80" ;;
        *) echo "Error: orientation must be 'landscape' or 'portrait'"; exit 1 ;;
    esac
fi

# --- Resolve theme aliases ---
resolve_theme() {
    case "$1" in
        dark)    echo "asciinema" ;;
        light)   echo "github-light" ;;
        gruvbox) echo "gruvbox-dark" ;;
        *)
            if [ -n "$CONFIG_PATH" ] && [ -f "$CONFIG_PATH" ]; then
                val=$(json_get "$CONFIG_PATH" ".theme_aliases.$1")
                [ -n "$val" ] && echo "$val" && return
            fi
            echo "$1" ;;
    esac
}
THEME=$(resolve_theme "$THEME")

# --- Validate ---
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: file not found: $INPUT_FILE"
    exit 1
fi
command -v agg >/dev/null 2>&1 || { echo "Error: agg not found. Install with: cargo install agg"; exit 1; }

# --- Build output path ---
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="${INPUT_FILE%.cast}.gif"
fi

# --- Build agg command ---
AGG_ARGS=(
    "$INPUT_FILE" "$OUTPUT_FILE"
    --font-size "$FONT_SIZE"
    --theme "$THEME"
    --speed "$SPEED"
    --idle-time-limit "$IDLE_LIMIT"
    --fps-cap "$FPS_CAP"
    --last-frame-duration "$LAST_FRAME_DURATION"
)
[ -n "$COLS" ] && [ "$COLS" != "0" ] && AGG_ARGS+=(--cols "$COLS")
[ -n "$ROWS" ] && [ "$ROWS" != "0" ] && AGG_ARGS+=(--rows "$ROWS")
[ "$LOOP" = "false" ] && AGG_ARGS+=(--no-loop)

echo "Running: agg ${AGG_ARGS[*]}"
agg "${AGG_ARGS[@]}"
echo "Created: $OUTPUT_FILE"

# --- Watermark (optional, requires ImageMagick) ---
if [ -n "$WATERMARK_TEXT" ]; then
    if command -v magick >/dev/null 2>&1; then
        echo "Applying watermark: $WATERMARK_TEXT"
        magick "$OUTPUT_FILE" \
            -gravity SouthEast -pointsize 14 -fill "rgba(255,255,255,0.5)" \
            -annotate +10+10 "$WATERMARK_TEXT" \
            "$OUTPUT_FILE"
        echo "Watermark applied."
    else
        echo "Warning: ImageMagick (magick) not found — skipping watermark. Install from https://imagemagick.org"
    fi
fi
