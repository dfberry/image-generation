# SKILL.md — simple_config.py: User-Friendly SDXL Image Generation

**File:** `image-generation/simple_config.py`
**Repo:** `dfberry/image-generation`
**Layer:** Wrapper (translates plain-English terms → SDXL parameters → `generate.py`)

---

## When to Use

| Use `simple_config.py` when... | Use `generate.py` directly when... |
|--------------------------------|-------------------------------------|
| You want to say "production quality" instead of `--steps 35 --refine --refiner-steps 15` | You need fine-grained control over specific technical params |
| You want to say "watercolor" instead of `--lora joachim_s/aether-watercolor-and-ink-sdxl --lora-weight 0.8` + prompt tokens | You're building on top of the engine layer |
| You want to say "blog-hero" instead of `--width 1200 --height 632` | You're debugging the generation pipeline itself |
| You want batch processing with shared style/preset defaults | You know the exact params you want |

---

## Preset Table

| Preset | `--steps` | `--refine` | `--refiner-steps` | `--guidance` | CPU Time |
|--------|-----------|------------|-------------------|--------------|----------|
| `quick-draft` | 15 | off | 10 | 6.5 | ~10 min |
| `standard` | 22 | off | 10 | 6.5 | ~14 min |
| `high-quality` | 35 | off | 10 | 6.5 | ~19 min |
| `production` | 35 | **on** | **15** | 6.5 | **~28 min** |

**Default:** `standard` (matches generate.py defaults; safe to omit `--preset`).

---

## Modifier Table

Modifiers adjust parameters on top of the active preset. Use `--modifier` (repeatable).

| Modifier | Effect | Notes |
|----------|--------|-------|
| `--modifier dreamier` | guidance → 4.0 | Looser, more abstract |
| `--modifier softer` | guidance → 5.0 | Slightly loose |
| `--modifier crisper` | guidance → 7.5 | Upper safe limit for SDXL |
| `--modifier sharper` | guidance → 8.0 | ⚠️ Use with `--model precise` |
| `--modifier photorealistic` | guidance → 9.0, model → precise | Forces precise model |
| `--modifier more-detailed` | steps +10; if steps ≥ 30 → refine auto-on | Additive |
| `--modifier less-detailed` | steps −5 (floor: 10) | |
| `--modifier artistic` | model → creative | |
| `--modifier fast` | steps → 15, refine off | Override step count |

**Stacking:** Modifiers apply left-to-right. Last absolute guidance value wins.
`--modifier more-detailed --modifier crisper` → steps+10, guidance=7.5.

---

## Style Table

Styles inject prompt tokens and optionally load a LoRA.

| Style | Tokens prepended | LoRA | LoRA weight |
|-------|-----------------|------|-------------|
| `folk-art` *(default)* | `Latin American folk art style, magical realism illustration,` | none | — |
| `watercolor` | `Watercolor illustration, soft wet-on-wet washes, visible paper texture, warm muted tones, loose brushwork,` | `joachim_s/aether-watercolor-and-ink-sdxl` | 0.8 |
| `oil-painting` | (passed through as `--style oil-painting` to generate.py) | passthrough | — |
| `sketch` | (passthrough) | passthrough | — |
| `anime` | (passthrough) | passthrough | — |

**Default:** If `--style` is omitted, `folk-art` tokens are prepended automatically.
**Suppress default:** `--no-default-style` or `--style none`.

---

## Size Table

| Size | Width | Height | Aspect | Use Case |
|------|-------|--------|--------|----------|
| `square` *(default)* | 1024 | 1024 | 1:1 | SDXL native |
| `blog-hero` | 1200 | 632 | ~1.9:1 | Blog post header |
| `wide` | 1280 | 720 | 16:9 | Landscape illustrations |
| `portrait` | 768 | 1024 | 3:4 | Vertical/mobile |
| `tall` | 832 | 1216 | ~2:3 | Portrait tall |

---

## Example Commands

```bash
# Quick draft to check composition (~10 min CPU)
python simple_config.py \
  --prompt "A glowing tropical garden with magenta flowers and teal pools, warm sunset glow, no text" \
  --preset quick-draft --seed 42 --output outputs/draft/garden.png --cpu

# Production watercolor blog hero (~28 min CPU)
python simple_config.py \
  --prompt "A developer and AI agent at a glass-topped desk, soft morning light, no text" \
  --preset production --style watercolor --size blog-hero \
  --seed 52 --output outputs/hero.png --cpu

# Standard with dreamier mood modifier
python simple_config.py \
  --prompt "A team meeting around a table with glowing laptops, evening light, no text" \
  --preset standard --modifier dreamier --seed 101 --output outputs/team.png --cpu

# Stacked modifiers: more detail + crisper guidance
python simple_config.py \
  --prompt "A lone developer in a tropical office, bright cobalt blue shirt, no text" \
  --preset standard --modifier more-detailed --modifier crisper --style watercolor \
  --seed 77 --output outputs/developer.png --cpu

# Dry run to preview parameters without generating
python simple_config.py \
  --prompt "test prompt, no text" \
  --preset production --style watercolor --size blog-hero --dry-run

# Batch processing from JSON file
python simple_config.py \
  --preset production --style watercolor --size blog-hero \
  --batch-file jobs.json --dry-run
```

---

## How to Combine preset + modifier + style + size

```bash
# "High-quality dreamier watercolor landscape in blog-hero format"
python simple_config.py \
  --prompt "A misty tropical forest at dawn, warm gold shafts of light, no text" \
  --preset high-quality \
  --modifier dreamier \
  --style watercolor \
  --size blog-hero \
  --seed 88 --output outputs/forest.png --cpu
```

This resolves to:
```bash
python generate.py \
  --prompt "Watercolor illustration, soft wet-on-wet washes, ..., A misty tropical forest at dawn, ..." \
  --steps 35 --guidance 4.0 \
  --lora joachim_s/aether-watercolor-and-ink-sdxl --lora-weight 0.8 \
  --width 1200 --height 632 \
  --seed 88 --output outputs/forest.png --cpu
```

---

## `--assist` Usage

```bash
python simple_config.py --prompt "a developer working" --preset production --assist --cpu
```

**What it does:**
- Checks CLIP token count (warns at 60+, errors at 77+)
- Enforces "no text" rule (appends if missing)
- Auto-adds negative prompt for text/watermark suppression
- Suggests color specificity improvements for vague color words
- Suggests scene expansion for minimal prompts (< 8 words, no lighting cues)

**Non-interactive mode** (no TTY, Squad agent use): all safe defaults applied silently.
Interactive mode: Dina accepts/rejects each suggestion.

**With template:**
```bash
python simple_config.py --assist --template blog-hero --preset production --style watercolor --cpu
```

---

## SDXL Rules (embedded in `--assist` logic)

| Rule | Detail |
|------|--------|
| **CLIP 77-token limit** | Tokens past 77 are silently truncated. Put subjects FIRST. Style tokens go first (handled automatically). |
| **Color specificity** | "blue shirt" → unreliable. Use "bright cobalt blue shirt". Add unwanted color to negative prompt. |
| **"no text" rule** | Always include in prompt or negative prompt. SDXL hallucinates text without it. |
| **Guidance safe range** | > 7.5 causes over-saturation. Use `--model precise` if guidance > 7.5 is needed. |
| **Seed management** | Same seed + same tokens = same image. Change seed when changing prompts. |

## CPU Timing Reference

| Preset | Steps | Refine | Approx. CPU time |
|--------|-------|--------|-----------------|
| quick-draft | 15 | no | ~10 min |
| standard | 22 | no | ~14 min |
| high-quality | 35 | no | ~19 min |
| production | 35 | yes (15) | ~28 min |

---

*PRD: `projects/dina/2026-05-16T06-48-prd-wrapper-core.md`*
