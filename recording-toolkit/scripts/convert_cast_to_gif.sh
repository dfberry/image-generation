#!/bin/bash
# Convert asciinema cast to GIF
# Requires: agg (pip install asciinema-agg)
INPUT=$1
OUTPUT=${INPUT%.cast}.gif
agg "$INPUT" "$OUTPUT"
