#!/bin/bash
set -e
# Convert asciinema cast to GIF
# Requires: cargo install agg
if [ -z "$1" ]; then echo "Usage: convert_cast_to_gif.sh <file.cast>"; exit 1; fi
INPUT=$1
if [ ! -f "$INPUT" ]; then echo "Error: file not found: $INPUT"; exit 1; fi
command -v agg >/dev/null 2>&1 || { echo "Error: agg not found. Install with: cargo install agg"; exit 1; }
OUTPUT=${INPUT%.cast}.gif
agg "$INPUT" "$OUTPUT"
echo "Created: $OUTPUT"
