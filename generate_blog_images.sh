#!/bin/bash
# Blog Post Images: squad-inner-source (vacation theme)
# Usage: bash generate_blog_images.sh &
# Monitor: tail -f generation.log
#
# Approach: builds a JSON prompts file and calls generate.py once with
# --batch-file, running all 5 images in a single Python process.
# batch_generate() handles GPU memory flushes between items.
# Requires: PR #11 (--batch-file CLI flag) merged into main.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR"
source venv/bin/activate

BATCH_FILE="batch_prompts_$$.json"

# Build the JSON prompts array via Python (avoids jq dependency)
python - <<'EOF' > "$BATCH_FILE"
import json
prompts = [
    {
        "prompt": "Latin American folk art style, magical realism illustration of a brightly painted seaplane gliding toward a colorful wooden dock, turquoise water below, coral and gold pennants waving from palm trees lining the pier, warm afternoon light, no text",
        "output": "outputs/01.png",
        "seed": 42,
    },
    {
        "prompt": "Latin American folk art style, magical realism illustration of a vibrant resort welcome hamper overflowing with maps, golden keys, and tropical fruit at a painted hotel door, magenta and teal ribbons, luminous warm light, no text",
        "output": "outputs/02.png",
        "seed": 43,
    },
    {
        "prompt": "Latin American folk art style, magical realism illustration of an arched footbridge covered in painted flowers and folk patterns connecting two colorful resort islands over bright turquoise water, golden sunrise glow, no text",
        "output": "outputs/03.png",
        "seed": 44,
    },
    {
        "prompt": "Latin American folk art style, magical realism illustration of a distant silhouette of a traveler at a bright hotel lobby table covered in illustrated maps, tropical plants in terracotta pots, gold and teal tilework glowing in warm sunlight, no text",
        "output": "outputs/04.png",
        "seed": 45,
    },
    {
        "prompt": "Latin American folk art style, magical realism illustration of three backlit figures in hotel uniforms in a sunlit lobby, a glowing golden key and journal exchanged between them, magenta and emerald uniforms, mosaic tile floor, no text",
        "output": "outputs/05.png",
        "seed": 46,
    },
]
print(json.dumps(prompts, indent=2))
EOF

python -u generate.py --batch-file "$BATCH_FILE" 2>&1 | tee -a generation.log

rm -f "$BATCH_FILE"

echo "ALL IMAGES DONE" >> generation.log
