#!/bin/bash
set -e
# One-key CLI recording
# NOTE: asciinema requires WSL on Windows.
REPO_ROOT=$(git rev-parse --show-toplevel) || { echo "Error: not in a git repository"; exit 1; }
command -v asciinema >/dev/null 2>&1 || { echo "Error: asciinema not found. Install with: pip install asciinema"; exit 1; }
mkdir -p "$REPO_ROOT/recordings/cli"
FILENAME="$REPO_ROOT/recordings/cli/$(date +%Y%m%d-%H%M).cast"
asciinema rec "$FILENAME"
