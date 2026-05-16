# LoRA Validation Log

Human review log for visual LoRA effect validation.
Each row captures one validated LoRA run against a no-LoRA baseline.

**Methodology:**
1. Generate reference image: `--preset production --style folk-art --seed 42` (no LoRA)
2. Generate comparison image: `--preset production --lora aether-watercolor --seed 42` (LoRA active)
3. Compute pHash distance between the two images
4. Assert distance ≥ 5 (LoRA has measurable visual effect)
5. Assert distance ≤ 40 (same seed/composition preserved)

---

| Date | Version | Seed | LoRA | pHash distance from baseline | Rating (1–5) | Notes | Reviewer |
|------|---------|------|------|------------------------------|-------------|-------|----------|
| (populate at ship) | v2.0 | 42 | aether-watercolor | ? | ? | (fill in at ship) | Dina |

---

## How to Add an Entry

Run the two commands, compute pHash using imagehash, then fill in the row:

```bash
# Reference (no LoRA)
python simple_config.py \
  --prompt "A developer at a standing desk, warm afternoon light, no text" \
  --preset production --style folk-art --seed 42 --cpu \
  --output test-outputs/lora-baseline-seed42.png

# Comparison (with LoRA)
python simple_config.py \
  --prompt "A developer at a standing desk, warm afternoon light, no text" \
  --preset production --lora aether-watercolor --seed 42 --cpu \
  --output test-outputs/lora-active-seed42.png
```

Then compute pHash distance:

```python
import imagehash
from PIL import Image

h1 = imagehash.phash(Image.open("test-outputs/lora-baseline-seed42.png"))
h2 = imagehash.phash(Image.open("test-outputs/lora-active-seed42.png"))
print(f"pHash distance: {h1 - h2}")
```

**Pass criteria:**
- `distance ≥ 5` — LoRA is having a visible effect
- `distance ≤ 40` — Same composition preserved (not a completely different image)
