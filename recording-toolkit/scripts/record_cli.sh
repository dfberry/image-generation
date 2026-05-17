#!/bin/bash
set -e
# One-key CLI recording
# NOTE: asciinema requires WSL on Windows.
# Supports config file presets and CLI overrides for terminal dimensions.

show_help() {
    cat <<'EOF'
Usage: record_cli.sh [options]

Options:
  --cols <n>             Terminal width in columns (default: 120)
  --rows <n>             Terminal height in rows (default: 30)
  --idle-limit <n>       Max idle time in seconds (default: 3)
  --output-dir <path>    Output directory for .cast files (default: recordings/cli)
  --config <path>        Path to config JSON file
  --preset <name>        Preset name from config file
  --orientation <preset> Preset dimensions: landscape (120x30), portrait (40x80)
  --help                 Show this help

Priority: CLI switches > preset > config defaults > built-in defaults

Examples:
  ./record_cli.sh
  ./record_cli.sh --preset blog-landscape
  ./record_cli.sh --cols 100 --rows 25
  ./record_cli.sh --orientation landscape
EOF
    exit 0
}

# --- Built-in defaults ---
COLS="120"
ROWS="30"
IDLE_LIMIT="3"
OUTPUT_DIR="recordings/cli"
CONFIG_PATH=""
PRESET=""
ORIENTATION=""
COLS_FROM_CLI="false"
ROWS_FROM_CLI="false"

# --- Parse arguments ---
while [ $# -gt 0 ]; do
    case "$1" in
        --help)        show_help ;;
        --cols)        COLS="$2"; COLS_FROM_CLI="true"; shift 2 ;;
        --rows)        ROWS="$2"; ROWS_FROM_CLI="true"; shift 2 ;;
        --idle-limit)  IDLE_LIMIT="$2"; shift 2 ;;
        --output-dir)  OUTPUT_DIR="$2"; shift 2 ;;
        --config)      CONFIG_PATH="$2"; shift 2 ;;
        --preset)      PRESET="$2"; shift 2 ;;
        --orientation) ORIENTATION="$2"; shift 2 ;;
        -*)            echo "Error: unknown option $1"; exit 1 ;;
        *)             echo "Error: unexpected argument $1"; exit 1 ;;
    esac
done

# Track CLI values before config overrides
CLI_COLS="$COLS"
CLI_ROWS="$ROWS"
CLI_IDLE_LIMIT="$IDLE_LIMIT"
CLI_OUTPUT_DIR="$OUTPUT_DIR"

# Reset to built-in defaults
COLS="120"
ROWS="30"
IDLE_LIMIT="3"
OUTPUT_DIR="recordings/cli"

# --- JSON helper ---
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
    val=$(json_get "$CONFIG_PATH" ".defaults.cols");            [ -n "$val" ] && COLS="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.rows");            [ -n "$val" ] && ROWS="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.idle_time_limit"); [ -n "$val" ] && IDLE_LIMIT="$val"
    val=$(json_get "$CONFIG_PATH" ".defaults.output_dir");      [ -n "$val" ] && OUTPUT_DIR="$val"
fi

# --- Apply preset ---
if [ -n "$PRESET" ]; then
    if [ -z "$CONFIG_PATH" ] || [ ! -f "$CONFIG_PATH" ]; then
        echo "Error: --preset requires a config file"
        exit 1
    fi
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.cols");            [ -n "$val" ] && COLS="$val"
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.rows");            [ -n "$val" ] && ROWS="$val"
    val=$(json_get "$CONFIG_PATH" ".presets.$PRESET.idle_time_limit"); [ -n "$val" ] && IDLE_LIMIT="$val"
fi

# --- Apply orientation ---
if [ -n "$ORIENTATION" ] && [ "$COLS_FROM_CLI" = "false" ] && [ "$ROWS_FROM_CLI" = "false" ]; then
    case "$ORIENTATION" in
        landscape) COLS="120"; ROWS="30" ;;
        portrait)  COLS="40";  ROWS="80" ;;
        *) echo "Error: orientation must be 'landscape' or 'portrait'"; exit 1 ;;
    esac
fi

# --- Apply CLI overrides (highest priority) ---
[ "$COLS_FROM_CLI" = "true" ]      && COLS="$CLI_COLS"
[ "$ROWS_FROM_CLI" = "true" ]      && ROWS="$CLI_ROWS"
[ "$CLI_IDLE_LIMIT" != "3" ]       && IDLE_LIMIT="$CLI_IDLE_LIMIT"
[ "$CLI_OUTPUT_DIR" != "recordings/cli" ] && OUTPUT_DIR="$CLI_OUTPUT_DIR"

# --- Validate ---
REPO_ROOT=$(git rev-parse --show-toplevel) || { echo "Error: not in a git repository"; exit 1; }
command -v asciinema >/dev/null 2>&1 || { echo "Error: asciinema not found. Install with: pip install asciinema"; exit 1; }

# --- Prepare output directory ---
if [[ "$OUTPUT_DIR" = /* ]]; then
    DIR="$OUTPUT_DIR"
else
    DIR="$REPO_ROOT/$OUTPUT_DIR"
fi
mkdir -p "$DIR"

FILENAME="$DIR/$(date +%Y%m%d-%H%M).cast"

# Set terminal dimensions via environment variables
export COLUMNS="$COLS"
export LINES="$ROWS"

echo "Recording with dimensions: ${COLS}x${ROWS}, idle limit: ${IDLE_LIMIT}s"
echo "Output: $FILENAME"
echo "Press Ctrl+D or type 'exit' to stop recording."

asciinema rec --idle-time-limit "$IDLE_LIMIT" "$FILENAME"
echo "Recording saved: $FILENAME"
