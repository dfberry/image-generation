# Switch — History

## Project Context

- **Project:** image-generation — Python CLI tool using Stable Diffusion XL (SDXL) to generate blog post illustrations with a tropical magical-realism aesthetic.
- **Stack:** Python 3.10+, diffusers, transformers, torch, Pillow
- **Owner:** dfberry
- **Key files:** prompts/examples.md (master prompt library), generate.py (consumes prompts)
- **Joined:** 2026-03-26

## Learnings

### Prompt Library Audit (2026-03-26)

**Structure:** `prompts/examples.md` is a single flat file containing a 4-line style guide, 5 original abstract prompts (metaphorical, heavily-modified), and 5 vacation-theme prompts (concrete scenes, lighter modifiers). Two distinct prompt eras coexist with overlapping numbering (01-05 each).

**Key findings from first audit:**

1. **No negative prompts anywhere.** `generate.py` doesn't accept `--negative-prompt`, and no prompt includes negative guidance. SDXL benefits significantly from negatives like "blurry, text, watermark, deformed" to suppress artifacts.

2. **"no text" constraint inconsistency.** All 5 original prompts end with "no text" (prevents SDXL text artifacts). All 5 vacation prompts omit it — likely producing unwanted text in generated images.

3. **Style anchor drift.** Original prompts use "Latin American folk art style, magical realism illustration" (two anchors). Vacation prompts drop "magical realism" and alternate between "Latin American folk art illustration" and just "Folk art illustration". This inconsistency weakens aesthetic coherence.

4. **No prompt template/composition system.** Every prompt is bespoke. Style qualifiers, palette hints, and constraints are copy-pasted inline rather than factored into a composable template (e.g., `{scene} + {style_anchor} + {palette} + {constraints}`).

5. **Style guide is minimal (4 lines).** Missing: prompt structure guidance, negative prompt strategy, what to avoid, prompt-parameter interactions, seed strategy, troubleshooting, SDXL-specific tips.

6. **Refiner mismatch.** Parameter table says "blog quality" = 40 steps + refine. But all vacation prompts and `batch_generate()` hardcode `refine=False`. The original prompts' example uses `--refine`.

7. **Prompt duplication.** Vacation prompts exist in three places: `prompts/examples.md`, `generate_blog_images.sh`, and inline in `batch_generate()` defaults. No single source of truth.

**File paths:**
- `prompts/examples.md` — master prompt library (single file, ~123 lines)
- `generate.py` — CLI; `prompt` is positional arg, no `negative_prompt` support
- `generate_blog_images.sh` — batch script with duplicated prompts
- `generate.py:batch_generate()` — hardcodes steps=40, guidance=7.5, refine=False

**Architecture decisions to propose:**
- Add negative prompt support to pipeline and CLI
- Factor style system into composable template
- Add "no text" to all prompts or make it a default constraint
- Standardize style anchors across all prompts
