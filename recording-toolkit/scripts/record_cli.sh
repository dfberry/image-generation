#!/bin/bash
# One-key CLI recording
REPO_ROOT=$(git rev-parse --show-toplevel)
mkdir -p "$REPO_ROOT/recordings/cli"
FILENAME="$REPO_ROOT/recordings/cli/$(date +%Y%m%d-%H%M).cast"
asciinema rec "$FILENAME"
