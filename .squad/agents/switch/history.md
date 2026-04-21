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

### Negative Prompt Strategy Documentation (issue #3, 2026-03-26)

**What was done:** Added a comprehensive `## Negative Prompts` section to `prompts/examples.md` as part of issue #3 (negative prompt support). Also updated the Style Guide with a cross-reference to the new section.

**Section contents:**
1. **Default negative prompt** (11 terms): `blurry, bad quality, worst quality, low resolution, text, watermark, signature, deformed, ugly, duplicate, morbid`
2. **Term-by-term rationale table** — explains what each term prevents and why it matters for our tropical folk art aesthetic
3. **Customization guidelines** — when to add scene-specific negatives (people, architecture, fine patterns, photorealistic drift, dark mood) vs. using the default as-is
4. **SDXL-specific tips** — what works (quality pairs, style negation, double-blocking text) and what backfires (over-long prompts, negating colors, negating specific objects, contradicting positive tokens, SD 1.5 terms)
5. **Usage example** — shows the recommended `--negative-prompt` CLI invocation for when Trinity wires up the flag

**Key design choices:**
- Kept the default at 11 terms — SDXL's sweet spot before token blending kicks in
- `bad quality` + `worst quality` as a pair is more effective than either alone on SDXL (different training captions)
- `text` in negative + "no text" in positive = double-blocking, the most reliable text suppression for SDXL
- Explicitly warned against negating colors and specific objects — common SDXL pitfalls
- Warned against copying SD 1.5 negative prompts (different text encoder)
- `morbid` included specifically because our prompts use words like "ancient," "faded," "translucent forms" that can drift dark

**Dependency:** `generate.py` does not yet accept `--negative-prompt`. This documentation is ready for Trinity to reference when implementing the CLI flag.

### D4 Prompt Library Audit (2026-04-16)

**Scope:** Full audit of `prompts/examples.md` (10 canonical prompts + style guide), `docs/blog-image-generation-skill.md`, `generate_blog_images.sh`, and `batch_blog_images*.json` files.

**Key findings:**

1. **Style guide is solid.** The expanded guide (issue #7) is internally consistent — palette rules, anchor requirements, SDXL tips, negative prompt strategy, template system, and do's/don'ts all align. No contradictions found.

2. **3 prompts FAIL figure silhouette rule.** Prompts 04 (original), V04, and V05 use visible human figures with arm action verbs ("gesturing," "leaning over," "passing"), violating the style guide's silhouette/backlighting mandate. Prompts 03 and 05 are borderline (visible figures but no action verbs).

3. **Shell script prompts are stale (CRITICAL).** All 5 prompts in `generate_blog_images.sh` are pre-issue-#7 versions — missing `magical realism` anchor and `no text` guard. Running the script produces weaker outputs.

4. **Batch JSON files use an entirely different aesthetic.** `batch_blog_images.json` and `_v2.json` use pen-and-ink watercolor with a Pacific Northwest palette (slate blue, warm sage, charcoal) — zero overlap with the canonical tropical magical-realism style. This alternate style is undocumented.

5. **Skill doc examples don't follow the style guide.** 3 example prompts in `docs/blog-image-generation-skill.md` use wrong anchors, feature hand anatomy, and one drops the anchor entirely.

6. **Prompt 02 uses `aesthetic` instead of `style` in anchor.** Minor but violates the "exact wording" rule.

7. **Vacation prompts V01 and V03 use <3 canonical palette colors.** V03 is the worst — only "golden" is explicitly named from the palette.

**Report location:** `.squad/decisions/inbox/switch-prompt-audit.md` (12 findings, per-prompt pass/fail table, priority recommendations).

### Style Guide Expansion & Prompt Template System (issue #7, 2026-03-26)

**What was done:** Expanded `prompts/examples.md` from a 4-line style guide into a comprehensive prompt engineering reference (+272 lines). Branch: `squad/7-style-guide-templates`.

**Key deliverables:**

1. **Full style guide** — Defined the tropical magical-realism aesthetic with precision: color palette (6 colors with hex values and usage rules), mood/lighting rules (warm diegetic light, no cold blue), composition guidelines (dense, layered, 1024×1024), and the canonical style anchor requirement.

2. **SDXL-specific guidance** — Tables documenting what SDXL responds well to (specific color+noun pairs, named art movements, emotional tone words) and what fails (negating colors/objects, vague style words, guidance > 7.5, SD 1.5 negative terms). Do's and Don'ts checklist for quick reference.

3. **Prompt template system** — 5-component structure: `{scene_description}, {palette_hints}, {style_anchor}, {mood_and_lighting}, {constraints}`. Includes step-by-step writing guide, minimal and full template examples, and a validation checklist.

4. **Prompt consistency fixes:**
   - Restored `magical realism illustration` anchor to all 5 vacation prompts (had drifted to just "folk art illustration" or "Folk art illustration")
   - Added `no text` constraint to all 5 vacation prompts (was missing entirely)
   - Fixed Prompt 04's `aesthetic` → `style` for anchor consistency
   - All 10 prompts now use the canonical anchor: `Latin American folk art style, magical realism illustration`

5. **Guidance scale fix** — Changed "best quality" from 8.0 → 7.5 and "quick draft" from 7.5 → 7.0, per Niobe's pipeline review finding that SDXL's sweet spot is 7.0–7.5. Added explanatory note.

**Prompt audit result:** After changes, all 10 prompts (5 original + 5 vacation) have: canonical style anchor ✓, "no text" ✓, palette colors ✓, light source described ✓.

**Note:** Vacation prompts now have different text than what was used to generate the existing images. Regeneration with the corrected prompts will produce different outputs (different seeds may be needed to achieve comparable quality).

### Remotion LLM Prompt Engineering (issue #92)

**Problem:** llama3 8B consistently generates invalid TSX for remotion-gen: mismatched brackets in `interpolate()`, missing imports, wrong `spring()` signature (no config object).

**What was done:**

1. **System prompt rewrite (`llm_client.py`):** Replaced the soft "requirements list" prompt with a strict, structured prompt containing:
   - 9 NEVER/ALWAYS rules at the top (most impactful placement for instruction-tuned models)
   - Exact Remotion API signatures for `interpolate()`, `spring()`, `useCurrentFrame()`, `useVideoConfig()`, `Sequence`
   - Complete working example showing `spring({frame, fps})` and `interpolate()` with `{extrapolateRight: 'clamp'}` — these were the two most common failure points
   - Explicit "no markdown fences" instruction (llama3 wraps code in fences ~80% of the time despite being told not to)
   - Image-specific instructions moved to a dedicated section

2. **Temperature reduction for Ollama:** Lowered from 0.7 → 0.4 for local models. Small models need lower temperature to stay structurally sound; creativity isn't the bottleneck, correctness is.

3. **Expanded `_REMOTION_HOOKS` list:** Added 11 more symbols (`Audio`, `Video`, `OffthreadVideo`, `Series`, `Easing`, `random`, `delayRender`, `continueRender`, `Loop`, `Still`, `Composition`). `ensure_remotion_imports()` now covers the full common Remotion API.

4. **New `validate_tsx_syntax()`:** Bracket/paren/brace matching checker that strips strings, comments, and template literals before counting. Also checks for unclosed JSX tags on known Remotion components. Returns error list (empty = valid).

5. **Retry logic stub (`build_validation_error_context()` + `generate_component(validation_errors=)`):** When validation fails, the error list can be formatted and fed back to the LLM as a follow-up prompt. `generate_component()` now accepts `validation_errors` param to enable this flow. Callers can implement the retry loop.

6. **Minimum model requirements documented** in module docstring — GPT-4 class recommended, llama3 8B marginal, <7B not recommended.

**Key insight:** For small models, the single most effective prompt change was placing the working example *without* markdown fences directly in the system prompt. When the only code the model sees is raw TSX (not wrapped in fences), it's far more likely to output raw TSX.
