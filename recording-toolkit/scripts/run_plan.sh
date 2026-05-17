#!/bin/bash
set -e
# Recording plan runner — executes a two-phase recording plan from a JSON config.
# Phase 1 (pre_record): runs setup commands silently, clears screen.
# Phase 2 (record): starts asciinema, auto-types demo commands with realistic delays.
# NOTE: Requires asciinema and WSL (Unix terminal). python3 required if jq not available.

show_help() {
    cat <<'EOF'
Usage: run_plan.sh <plan.json> [options]

Arguments:
  <plan.json>          Path to recording plan JSON file (required)

Options:
  --dry-run            Show what would be executed without recording
  --no-convert         Skip GIF conversion after recording
  --output <path>      Override output .cast file path
  --config <path>      Path to recording-config.json for convert settings
  --help               Show this help

Plan JSON format:
  {
    "name": "my-demo",
    "pre_record": { "commands": ["cd /path", "export VAR=val"], "clear_screen": true },
    "record": {
      "commands": [
        { "type": "command", "value": "echo hello", "wait_for_output": true, "pause_after": 1.5 },
        { "type": "pause", "duration": 1.0 }
      ],
      "typing_speed": "medium",
      "default_pause": 1.0
    },
    "output": { "subdir": "cli", "convert": { "preset": "blog-landscape" } }
  }

Typing speed presets:
  slow    — 120ms/char ±40ms
  medium  — 60ms/char  ±20ms
  fast    — 30ms/char  ±10ms

Examples:
  ./run_plan.sh recordings/plans/copilot-cli-demo.json
  ./run_plan.sh recordings/plans/copilot-cli-demo.json --dry-run
  ./run_plan.sh recordings/plans/copilot-cli-demo.json --no-convert
  ./run_plan.sh recordings/plans/copilot-cli-demo.json --output recordings/cli/my-demo.cast
EOF
    exit 0
}

# --- Argument parsing ---
PLAN_FILE=""
DRY_RUN="false"
NO_CONVERT="false"
OUTPUT_OVERRIDE=""
CONFIG_PATH=""

while [ $# -gt 0 ]; do
    case "$1" in
        --help)        show_help ;;
        --dry-run)     DRY_RUN="true"; shift ;;
        --no-convert)  NO_CONVERT="true"; shift ;;
        --output)      OUTPUT_OVERRIDE="$2"; shift 2 ;;
        --config)      CONFIG_PATH="$2"; shift 2 ;;
        -*)            echo "Error: unknown option $1"; exit 1 ;;
        *)
            if [ -z "$PLAN_FILE" ]; then
                PLAN_FILE="$1"; shift
            else
                echo "Error: unexpected argument $1"; exit 1
            fi
            ;;
    esac
done

if [ -z "$PLAN_FILE" ]; then
    echo "Error: plan.json is required"
    echo "Run with --help for usage."
    exit 1
fi

if [ ! -f "$PLAN_FILE" ]; then
    echo "Error: plan file not found: $PLAN_FILE"
    exit 1
fi

# --- JSON helpers ---
# Prefer jq; fall back to python3
json_get() {
    local file="$1" query="$2"
    if command -v jq >/dev/null 2>&1; then
        jq -r "$query // empty" "$file" 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c '
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    path = sys.argv[2].lstrip(".")
    val = data
    if path:
        for k in path.split("."):
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                sys.exit(0)
    if val is not None and not isinstance(val, (dict, list)):
        print(val)
except Exception:
    sys.exit(0)
' "$file" "$query" 2>/dev/null
    fi
}

json_get_array_length() {
    local file="$1" query="$2"
    if command -v jq >/dev/null 2>&1; then
        jq -r "($query) | length" "$file" 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c '
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    path = sys.argv[2].lstrip(".")
    val = data
    for k in path.split("."):
        val = val[k]
    print(len(val))
except Exception:
    print(0)
' "$file" "$query" 2>/dev/null
    fi
}

json_get_index() {
    local file="$1" query="$2" index="$3"
    if command -v jq >/dev/null 2>&1; then
        jq -r "(${query}[$index]) // empty" "$file" 2>/dev/null
    fi
}

json_get_index_field() {
    local file="$1" array_path="$2" index="$3" field="$4"
    if command -v jq >/dev/null 2>&1; then
        jq -r "(${array_path}[$index].${field}) // empty" "$file" 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c '
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    path = sys.argv[2].lstrip(".")
    idx = int(sys.argv[3])
    field = sys.argv[4]
    val = data
    for k in path.split("."):
        val = val[k]
    item = val[idx]
    result = item.get(field)
    if result is not None and not isinstance(result, (dict, list)):
        print(result)
except Exception:
    sys.exit(0)
' "$file" "$array_path" "$index" "$field" 2>/dev/null
    fi
}

# --- Validate dependencies ---
if [ "$DRY_RUN" = "false" ]; then
    command -v asciinema >/dev/null 2>&1 || { echo "Error: asciinema not found. Install with: pip install asciinema"; exit 1; }
fi
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required for delay calculations"; exit 1; }

# Validate jq or python3 available for JSON parsing
if ! command -v jq >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
    echo "Error: jq or python3 is required for JSON parsing"
    exit 1
fi

# --- Load plan metadata ---
PLAN_NAME=$(json_get "$PLAN_FILE" ".name")
PLAN_DESC=$(json_get "$PLAN_FILE" ".description")
OUTPUT_SUBDIR=$(json_get "$PLAN_FILE" ".output.subdir")
CONVERT_PRESET=$(json_get "$PLAN_FILE" ".output.convert.preset")
CLEAR_SCREEN=$(json_get "$PLAN_FILE" ".pre_record.clear_screen")
TYPING_SPEED=$(json_get "$PLAN_FILE" ".record.typing_speed")
DEFAULT_PAUSE=$(json_get "$PLAN_FILE" ".record.default_pause")

# Defaults
[ -z "$OUTPUT_SUBDIR" ] && OUTPUT_SUBDIR="cli"
[ -z "$TYPING_SPEED" ] && TYPING_SPEED="medium"
[ -z "$DEFAULT_PAUSE" ] && DEFAULT_PAUSE="1.0"
[ -z "$CLEAR_SCREEN" ] && CLEAR_SCREEN="false"

# --- Typing speed presets ---
case "$TYPING_SPEED" in
    slow)   CHAR_DELAY="0.12"; CHAR_VARIANCE="0.04" ;;
    medium) CHAR_DELAY="0.06"; CHAR_VARIANCE="0.02" ;;
    fast)   CHAR_DELAY="0.03"; CHAR_VARIANCE="0.01" ;;
    *)
        echo "Warning: unknown typing_speed '$TYPING_SPEED', using medium"
        CHAR_DELAY="0.06"; CHAR_VARIANCE="0.02"
        ;;
esac

# --- Locate repo root and config ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null) || REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -z "$CONFIG_PATH" ]; then
    AUTO_CONFIG="$(dirname "$SCRIPT_DIR")/recording-config.json"
    if [ -f "$AUTO_CONFIG" ]; then
        CONFIG_PATH="$AUTO_CONFIG"
    fi
fi

IDLE_LIMIT="3"
if [ -n "$CONFIG_PATH" ] && [ -f "$CONFIG_PATH" ]; then
    val=$(json_get "$CONFIG_PATH" ".defaults.idle_time_limit")
    [ -n "$val" ] && IDLE_LIMIT="$val"
fi

# --- Resolve output path ---
if [ -n "$OUTPUT_OVERRIDE" ]; then
    CAST_FILE="$OUTPUT_OVERRIDE"
else
    OUTPUT_DIR="$REPO_ROOT/recordings/$OUTPUT_SUBDIR"
    TIMESTAMP=$(date +%Y%m%d-%H%M)
    CAST_FILE="$OUTPUT_DIR/${PLAN_NAME}-${TIMESTAMP}.cast"
fi

# --- Dry run summary ---
if [ "$DRY_RUN" = "true" ]; then
    echo "=== DRY RUN: Recording Plan ==="
    echo "Plan:        ${PLAN_NAME:-<unnamed>}"
    echo "Description: ${PLAN_DESC:-<none>}"
    echo "Output:      $CAST_FILE"
    echo "Speed:       $TYPING_SPEED (${CHAR_DELAY}s/char ±${CHAR_VARIANCE}s)"
    echo ""

    echo "--- Phase 1: pre_record ---"
    PRE_COUNT=$(json_get_array_length "$PLAN_FILE" ".pre_record.commands")
    if [ -z "$PRE_COUNT" ] || [ "$PRE_COUNT" = "0" ]; then
        PRE_COUNT=0
        echo "  (no pre_record commands)"
    else
        i=0
        while [ $i -lt "$PRE_COUNT" ]; do
            CMD=$(json_get_index_field "$PLAN_FILE" ".pre_record.commands" $i "value" 2>/dev/null)
            # pre_record commands are plain strings, not objects
            if command -v jq >/dev/null 2>&1; then
                CMD=$(jq -r ".pre_record.commands[$i]" "$PLAN_FILE" 2>/dev/null)
            elif command -v python3 >/dev/null 2>&1; then
                CMD=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["pre_record"]["commands"][int(sys.argv[2])])' "$PLAN_FILE" "$i" 2>/dev/null)
            fi
            echo "  [setup] $CMD"
            i=$((i+1))
        done
    fi
    [ "$CLEAR_SCREEN" = "true" ] && echo "  [clear screen]"
    echo ""

    echo "--- Phase 2: record ---"
    REC_COUNT=$(json_get_array_length "$PLAN_FILE" ".record.commands")
    if [ -z "$REC_COUNT" ] || [ "$REC_COUNT" = "0" ]; then
        echo "  (no record commands)"
    else
        i=0
        while [ $i -lt "$REC_COUNT" ]; do
            TYPE=$(json_get_index_field "$PLAN_FILE" ".record.commands" $i "type")
            VALUE=$(json_get_index_field "$PLAN_FILE" ".record.commands" $i "value")
            DURATION=$(json_get_index_field "$PLAN_FILE" ".record.commands" $i "duration")
            PAUSE_AFTER=$(json_get_index_field "$PLAN_FILE" ".record.commands" $i "pause_after")
            case "$TYPE" in
                command) echo "  [command]  $ $VALUE  (pause_after: ${PAUSE_AFTER:-$DEFAULT_PAUSE}s)" ;;
                type)    echo "  [type]     $VALUE" ;;
                key)     echo "  [key]      $VALUE" ;;
                pause)   echo "  [pause]    ${DURATION:-1.0}s" ;;
                *)       echo "  [unknown]  type=$TYPE" ;;
            esac
            i=$((i+1))
        done
    fi

    echo ""
    if [ -n "$CONVERT_PRESET" ] && [ "$NO_CONVERT" = "false" ]; then
        echo "--- Post-record: convert ---"
        echo "  Preset: $CONVERT_PRESET"
        GIF_FILE="${CAST_FILE%.cast}.gif"
        echo "  Output: $GIF_FILE"
    fi
    echo "=== END DRY RUN ==="
    exit 0
fi

# --- Generate temp demo script ---
TEMP_SCRIPT=$(mktemp /tmp/plan_demo_XXXXXX.sh)
trap 'rm -f "$TEMP_SCRIPT"' EXIT INT TERM

cat > "$TEMP_SCRIPT" <<SCRIPT_HEADER
#!/bin/bash
# Auto-generated by run_plan.sh — do not edit

# --- Auto-type helper ---
auto_type() {
    local text="\$1"
    local char_delay="\${2:-$CHAR_DELAY}"
    local variance="\${3:-$CHAR_VARIANCE}"
    for (( i=0; i<\${#text}; i++ )); do
        char="\${text:\$i:1}"
        printf '%s' "\$char"
        sleep \$(python3 -c "import random; print(f'{max(0.01, \$char_delay + random.uniform(-\$variance, \$variance)):.3f}')")
    done
    echo  # Enter
}

wait_for_prompt() {
    sleep "\${1:-0.5}"
}

SCRIPT_HEADER

# --- Write pre_record commands ---
PRE_COUNT=$(json_get_array_length "$PLAN_FILE" ".pre_record.commands")
if [ -n "$PRE_COUNT" ] && [ "$PRE_COUNT" -gt 0 ]; then
    i=0
    while [ $i -lt "$PRE_COUNT" ]; do
        if command -v jq >/dev/null 2>&1; then
            CMD=$(jq -r ".pre_record.commands[$i]" "$PLAN_FILE" 2>/dev/null)
        elif command -v python3 >/dev/null 2>&1; then
            CMD=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["pre_record"]["commands"][int(sys.argv[2])])' "$PLAN_FILE" "$i" 2>/dev/null)
        fi
        printf '%s\n' "$CMD" >> "$TEMP_SCRIPT"
        i=$((i+1))
    done
fi

# Clear screen if requested
if [ "$CLEAR_SCREEN" = "true" ]; then
    echo "clear" >> "$TEMP_SCRIPT"
fi

# --- Write record phase commands ---
REC_COUNT=$(json_get_array_length "$PLAN_FILE" ".record.commands")
if [ -n "$REC_COUNT" ] && [ "$REC_COUNT" -gt 0 ]; then
    i=0
    while [ $i -lt "$REC_COUNT" ]; do
        TYPE=$(json_get_index_field "$PLAN_FILE" ".record.commands" $i "type")
        VALUE=$(json_get_index_field "$PLAN_FILE" ".record.commands" $i "value")
        DURATION=$(json_get_index_field "$PLAN_FILE" ".record.commands" $i "duration")
        PAUSE_AFTER=$(json_get_index_field "$PLAN_FILE" ".record.commands" $i "pause_after")
        WAIT_OUTPUT=$(json_get_index_field "$PLAN_FILE" ".record.commands" $i "wait_for_output")

        [ -z "$PAUSE_AFTER" ] && PAUSE_AFTER="$DEFAULT_PAUSE"

        case "$TYPE" in
            command)
                # Escape value for embedding in single-quoted shell string
                ESCAPED_VALUE=$(printf '%s' "$VALUE" | sed "s/'/'\\\\''/g")
                cat >> "$TEMP_SCRIPT" <<CMD_BLOCK
auto_type '$ESCAPED_VALUE' $CHAR_DELAY $CHAR_VARIANCE
CMD_BLOCK
                if [ "$WAIT_OUTPUT" = "true" ]; then
                    echo "wait_for_prompt $PAUSE_AFTER" >> "$TEMP_SCRIPT"
                else
                    echo "sleep $PAUSE_AFTER" >> "$TEMP_SCRIPT"
                fi
                ;;
            type)
                # Type characters without pressing Enter
                ESCAPED_VALUE=$(printf '%s' "$VALUE" | sed "s/'/'\\\\''/g")
                cat >> "$TEMP_SCRIPT" <<TYPE_BLOCK
# type (no Enter) — auto-type without newline
_text='$ESCAPED_VALUE'
for (( _i=0; _i<\${#_text}; _i++ )); do
    _char="\${_text:\$_i:1}"
    printf '%s' "\$_char"
    sleep \$(python3 -c "import random; print(f'{max(0.01, $CHAR_DELAY + random.uniform(-$CHAR_VARIANCE, $CHAR_VARIANCE)):.3f}')")
done
TYPE_BLOCK
                ;;
            key)
                case "$VALUE" in
                    enter)  echo 'echo' >> "$TEMP_SCRIPT" ;;
                    ctrl-c) echo 'kill -INT $$' >> "$TEMP_SCRIPT" ;;
                    ctrl-d) echo 'exit 0' >> "$TEMP_SCRIPT" ;;
                    tab)    echo 'printf "\t"' >> "$TEMP_SCRIPT" ;;
                    *)      echo "# key: $VALUE (not implemented)" >> "$TEMP_SCRIPT" ;;
                esac
                ;;
            pause)
                [ -z "$DURATION" ] && DURATION="1.0"
                echo "sleep $DURATION" >> "$TEMP_SCRIPT"
                ;;
            *)
                echo "# unknown command type: $TYPE" >> "$TEMP_SCRIPT"
                ;;
        esac
        i=$((i+1))
    done
fi

# Final hold so last output is visible before recording ends
echo "sleep 1" >> "$TEMP_SCRIPT"
chmod +x "$TEMP_SCRIPT"

# --- Create output directory ---
CAST_DIR="$(dirname "$CAST_FILE")"
mkdir -p "$CAST_DIR"

# --- Run asciinema ---
echo "Recording plan: ${PLAN_NAME:-<unnamed>}"
[ -n "$PLAN_DESC" ] && echo "Description: $PLAN_DESC"
echo "Output: $CAST_FILE"
echo ""

asciinema rec --command "bash $TEMP_SCRIPT" --idle-time-limit "$IDLE_LIMIT" "$CAST_FILE"
echo "Recording saved: $CAST_FILE"

# --- Optional GIF conversion ---
if [ -n "$CONVERT_PRESET" ] && [ "$NO_CONVERT" = "false" ]; then
    CONVERT_SCRIPT="$(dirname "$0")/convert_cast_to_gif.sh"
    if [ -f "$CONVERT_SCRIPT" ]; then
        GIF_FILE="${CAST_FILE%.cast}.gif"
        echo "Converting to GIF with preset: $CONVERT_PRESET"
        CONVERT_ARGS=("$CAST_FILE" "--preset" "$CONVERT_PRESET" "--output" "$GIF_FILE")
        [ -n "$CONFIG_PATH" ] && CONVERT_ARGS+=("--config" "$CONFIG_PATH")
        bash "$CONVERT_SCRIPT" "${CONVERT_ARGS[@]}"
        echo "GIF created: $GIF_FILE"
    else
        echo "Warning: convert_cast_to_gif.sh not found, skipping GIF conversion"
    fi
fi
