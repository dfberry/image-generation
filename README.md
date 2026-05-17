# Multi-Tool Media Generation Suite

This repository contains multiple media generation tools powered by AI models.

## Tools

| Tool | Description | Status |
|------|-------------|--------|
| [image-generation/](image-generation/) | Stable Diffusion XL image generation with batch processing | ✅ Active |
| [manim-animation/](manim-animation/) | AI-powered Manim animation generation → MP4 | ✅ Active |
| [remotion-animation/](remotion-animation/) | AI-powered Remotion animation generation → MP4 | ✅ Active |
| [video-stitcher/](video-stitcher/) | Stitch multiple MP4 animations into a single video | ✅ Active |
| [recording-toolkit/](recording-toolkit/) | Terminal recording → GIF with configurable themes, presets, and CLI switches | ✅ Active |
| [mermaid-diagrams/](mermaid-diagrams/) | Diagram generation from text | 🔜 Planned |

## Getting Started

See the README in each tool's folder for setup and usage instructions.

---

## Quick Start — `simple_config.py`

`simple_config.py` translates plain-English terms (presets, styles, sizes, modifiers) into SDXL parameters — so you write `--preset production --style watercolor` instead of raw `--steps 35 --refiner-steps 15 --lora ...`.

### Prerequisites

- Python 3.10+
- Install dependencies: `pip install -r image-generation/requirements-dev.txt`

### Dry run — preview parameters instantly (no generation)

```bash
cd image-generation
python simple_config.py \
  --prompt "A glowing tropical garden, warm sunset, no text" \
  --preset production --style watercolor --size blog-hero --dry-run
```

### Quick draft — fastest real generation (~10 min CPU)

```bash
python simple_config.py \
  --prompt "A glowing tropical garden with magenta flowers and teal pools, warm sunset glow, no text" \
  --preset quick-draft --seed 42 --output outputs/draft/garden.png --cpu
```

### Production blog hero — full quality watercolor (~28 min CPU)

```bash
python simple_config.py \
  --prompt "A developer and AI agent at a glass-topped desk, soft morning light, no text" \
  --preset production --style watercolor --size blog-hero \
  --seed 52 --output outputs/hero.png --cpu
```

### Key concept tables

**Presets** — quality/speed tradeoff

| Preset | Steps | Refine | CPU Time |
|--------|-------|--------|----------|
| `quick-draft` | 15 | no | ~10 min |
| `standard` *(default)* | 22 | no | ~14 min |
| `high-quality` | 35 | no | ~19 min |
| `production` | 35 | yes | ~28 min |

**Styles** — visual look

| Style | Effect |
|-------|--------|
| `folk-art` *(default)* | Latin American magical-realism tokens |
| `watercolor` | Soft washes + `aether-watercolor` LoRA |
| `oil-painting` / `sketch` / `anime` | Passthrough to generate.py |

**Sizes**

| Size | Pixels | Use Case |
|------|--------|----------|
| `square` *(default)* | 1024×1024 | SDXL native |
| `blog-hero` | 1200×632 | Blog post header |
| `wide` | 1280×720 | 16:9 landscape |
| `portrait` | 768×1024 | Vertical/mobile |
| `tall` | 832×1216 | ~2:3 tall portrait |

**Modifiers** — stack on top of any preset

| Modifier | Effect |
|----------|--------|
| `dreamier` | guidance → 4.0 (looser) |
| `softer` | guidance → 5.0 |
| `crisper` | guidance → 7.5 |
| `sharper` | guidance → 8.0 |
| `more-detailed` | steps +10; auto-enables refine when ≥ 30 |
| `less-detailed` | steps −5 (floor 10) |
| `fast` | steps → 15, refine off |
| `photorealistic` | guidance → 9.0, model → precise |
| `artistic` | model → creative |

```bash
# Stacked modifiers example
python simple_config.py \
  --prompt "A lone developer in a tropical office, bright cobalt blue shirt, no text" \
  --preset standard --modifier more-detailed --modifier crisper --style watercolor \
  --seed 77 --output outputs/developer.png --cpu
```

### LoRA management

LoRAs are registered by friendly name in `loras.json` so you can use `--lora aether-watercolor` instead of a raw HuggingFace ID.

```bash
python simple_config.py lora list
python simple_config.py lora add "ink-sketch" --id "author/ink-sketch-sdxl" --weight 0.6 --models sdxl --triggers "ink sketch style" --description "Clean ink sketch line art"
```

### Consistency controls

Use `--profile` to reuse a saved parameter set (scene, character, expression) across multiple runs, ensuring visual consistency across a blog post series. Profiles are stored in `profiles.json`.

```bash
python simple_config.py --prompt "..." --profile my-blog-series --cpu
```

### Assist mode — prompt coaching

```bash
python simple_config.py --prompt "a developer working" --preset production --assist --cpu
```

`--assist` checks CLIP token count, enforces the "no text" rule, auto-adds a negative prompt, and suggests color/scene improvements. Safe for non-interactive (Squad agent) use — applies all safe defaults silently.

### Full reference

See [`.github/skills/simple-image-config/SKILL.md`](.github/skills/simple-image-config/SKILL.md) for the complete parameter reference, LoRA composition rules, and SDXL tips.

## Development

- **CI:** GitHub Actions runs lint + tests on PRs labeled `run-ci`
- **Team docs:** `.squad/agents/` for team member charters, `.squad/decisions.md` for architecture decisions
- **Contributing:** See [image-generation/CONTRIBUTING.md](image-generation/CONTRIBUTING.md)

## License

- Model weights: [CreativeML Open RAIL++-M License](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md)
- Code: MIT
