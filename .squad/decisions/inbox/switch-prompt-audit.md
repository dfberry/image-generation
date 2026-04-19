# Switch — D4 Prompt Library & Style Consistency Audit

**Date:** 2026-04-16
**Author:** Switch (Prompt/LLM Engineer)
**Dimension:** D4 — Prompt Audit
**Scope:** `prompts/examples.md`, `docs/blog-image-generation-skill.md`, `generate_blog_images.sh`, `batch_blog_images.json`, `batch_blog_images_v2.json`

---

## Executive Summary

The prompt library in `prompts/examples.md` is well-structured with a comprehensive style guide, template system, and 10 canonical prompts across two series. However, **three satellite files contain stale, non-compliant prompts** that diverge significantly from the canonical versions. Additionally, a newer batch file series (`batch_blog_images*.json`) uses an entirely different aesthetic that is undocumented in the style guide. The style guide itself is internally consistent and thorough.

**Overall health:** Style guide = STRONG. Canonical prompts = GOOD. Satellite prompt copies = CRITICAL drift. Batch JSON series = undocumented style departure.

---

## Per-Prompt Pass/Fail Table

### Canonical Prompts (prompts/examples.md)

| # | Title | Style Anchor | ≥3 Palette Colors | Silhouette for Figures | No-Text Guard | 15-25 Word Detail | Pass/Fail |
|---|-------|-------------|-------------------|----------------------|---------------|-------------------|-----------|
| 01 | Friction Wall | ✅ `Latin American folk art style, magical realism illustration` | ✅ magenta, teal, emerald, amber | N/A (no figures) | ✅ `no text` | ✅ ~55 tokens total | ✅ PASS |
| 02 | Squad Gift | ⚠️ `Latin American folk art aesthetic` (not `style`) | ✅ magenta, teal, emerald, gold, amber | N/A (no figures) | ✅ `no text` | ✅ ~52 tokens | ⚠️ WARN |
| 03 | Inner Source Bridge | ✅ | ✅ gold, teal, emerald | ⚠️ "people crossing freely" — no silhouette/backlighting | ✅ `no text` | ✅ ~58 tokens | ⚠️ WARN |
| 04 | Contributor Experimentation | ✅ | ✅ teal, magenta, emerald, coral, amber | ❌ "figure gesturing" — visible figure with arm action verb | ✅ `no text` | ✅ ~60 tokens | ❌ FAIL |
| 05 | Knowledge Persistence | ✅ | ✅ emerald, teal, magenta, gold, amber | ⚠️ "figures...in faded translucent forms" — not silhouetted | ✅ `no text` | ✅ ~62 tokens | ⚠️ WARN |
| V01 | Seaplane at Dock | ✅ | ⚠️ coral, gold (only 2 canonical; "turquoise" ≈ teal but not exact name) | N/A | ✅ `no text` | ✅ ~38 tokens | ⚠️ WARN |
| V02 | Welcome Basket | ✅ | ✅ magenta, teal, gold | N/A | ✅ `no text` | ✅ ~36 tokens | ✅ PASS |
| V03 | Arched Bridge | ✅ | ⚠️ gold only (1 canonical; "turquoise" ≈ teal, "colorful" is vague) | N/A | ✅ `no text` | ✅ ~33 tokens | ⚠️ WARN |
| V04 | Guest with Maps | ✅ | ✅ gold, teal | ❌ "cheerful traveler leaning over" — visible figure + arm verb | ✅ `no text` | ✅ ~35 tokens | ❌ FAIL |
| V05 | Hotel Staff | ✅ | ✅ magenta, emerald, gold | ❌ "one passing a glowing golden key" — visible figures + arm action | ✅ `no text` | ✅ ~35 tokens | ❌ FAIL |

### Shell Script (generate_blog_images.sh) — Stale Copies

| # | Style Anchor | No-Text Guard | Matches Canonical |
|---|-------------|---------------|-------------------|
| 01 | ❌ `Latin American folk art illustration` (missing `magical realism`) | ❌ Missing | ❌ STALE |
| 02 | ❌ `Folk art illustration` (missing `Latin American` AND `magical realism`) | ❌ Missing | ❌ STALE |
| 03 | ❌ `Latin American folk art illustration` | ❌ Missing | ❌ STALE |
| 04 | ❌ `Folk art illustration` | ❌ Missing | ❌ STALE |
| 05 | ❌ `Latin American folk art illustration` | ❌ Missing | ❌ STALE |

### Batch JSON Files (batch_blog_images.json / _v2.json) — Different Aesthetic

| File | Style Anchor | Palette | No-Text Guard | Matches Style Guide |
|------|-------------|---------|---------------|---------------------|
| batch_blog_images.json (5 prompts) | ❌ `Pen-and-ink illustration` — no folk art/magical realism | ❌ slate blue, warm sage, charcoal (none from canonical palette) | ✅ "No text." | ❌ DIFFERENT AESTHETIC |
| batch_blog_images_v2.json (5 prompts) | ❌ `Pen-and-ink watercolor` — no folk art/magical realism | ❌ slate blue, warm sage, charcoal | ✅ "no text" | ❌ DIFFERENT AESTHETIC |

---

## Findings

### [PA-01] — Style Anchor Variant in Prompt 02 (Original Series)
**Severity:** MEDIUM
**File:** prompts/examples.md:197 (Prompt 02)
**Dimension:** D4
**Description:** Prompt 02 uses `Latin American folk art aesthetic` instead of the canonical `Latin American folk art style`. The style guide explicitly states the anchor must be `Latin American folk art style, magical realism illustration` — exact wording.
**Evidence:** `"...Latin American folk art aesthetic, magical realism illustration..."`
**Recommendation:** Change `aesthetic` → `style` to match the canonical anchor.

### [PA-02] — Human Figures Without Silhouette Technique (3 prompts)
**Severity:** HIGH
**File:** prompts/examples.md:203,208,365-375 (Prompts 03, 04, V04, V05)
**Dimension:** D4
**Description:** The style guide in `docs/blog-image-generation-skill.md` (lines 71-77) mandates silhouette/backlighting for human figures. Four prompts depict visible, identifiable human figures without this technique. Prompt 04 is worst — "figure gesturing" uses an arm action verb, which the guide explicitly warns against.
**Evidence:**
- Prompt 03: `"people crossing freely carrying colorful glowing lanterns"` — no silhouette
- Prompt 04: `"the figure gesturing towards the bubbles"` — arm action verb + visible figure
- V04: `"a cheerful traveler leaning over"` — arm verb + identifiable figure
- V05: `"one passing a glowing golden key and journal to a smiling newcomer"` — arm verb + identifiable faces
**Recommendation:** Rewrite these to use `dark silhouette figure backlit against [light source]` or `figure seen from behind` per the skill doc's guidance. Remove arm action verbs; let props carry the action.

### [PA-03] — Shell Script Contains Stale, Non-Compliant Prompts
**Severity:** CRITICAL
**File:** generate_blog_images.sh:22-47
**Dimension:** D4
**Description:** All 5 prompts in `generate_blog_images.sh` are pre-fix versions that lack `magical realism illustration` in the anchor and omit the `no text` constraint. The canonical prompts in `prompts/examples.md` were updated (issue #7) but the shell script was never synced. Running this script produces images with weakened aesthetic and potential text artifacts.
**Evidence:**
- Shell Prompt 01: `"Latin American folk art illustration of a brightly painted seaplane..."` (no `magical realism`, no `no text`)
- Shell Prompt 02: `"Folk art illustration of a vibrant resort..."` (missing `Latin American` entirely)
- Canonical Prompt 01: `"Latin American folk art style, magical realism illustration of a brightly painted seaplane...warm afternoon light, no text"`
**Recommendation:** Either (a) update shell script prompts to match canonical versions, or (b) migrate to `--batch-file` approach using a JSON file that references prompts from the library (single source of truth).

### [PA-04] — Batch JSON Files Use Undocumented Aesthetic
**Severity:** HIGH
**File:** batch_blog_images.json, batch_blog_images_v2.json
**Dimension:** D4
**Description:** These 10 prompts (5 per file) use a "Pen-and-ink watercolor" aesthetic with a 3-color palette (slate blue, warm sage, charcoal) — completely different from the canonical tropical magical-realism style. This aesthetic is not documented anywhere in the style guide. It's unclear if this is an intentional alternative style or drift.
**Evidence:**
- v1: `"Pen-and-ink illustration, 1200x630px, landscape orientation. Bellingham Bay at dusk..."`
- v2: `"Pen-and-ink watercolor, slate blue, warm sage, charcoal palette, white background, no text."`
- Neither uses `Latin American folk art style` or `magical realism illustration`
- Color palette: slate blue, warm sage, charcoal (zero overlap with canonical magenta/teal/emerald/gold/coral/amber)
**Recommendation:** If this is an intentional alternative style for a specific blog post, document it in `prompts/examples.md` as a named variant (e.g., "Pacific Northwest Pen-and-Ink" style) with its own palette rules. If unintentional, flag for rewrite.

### [PA-05] — Palette Color Coverage Gaps in Vacation Prompts
**Severity:** MEDIUM
**File:** prompts/examples.md:316,342 (V01, V03)
**Dimension:** D4
**Description:** Two vacation prompts use fewer than 3 canonical palette colors. V01 uses "coral" and "gold" but says "turquoise" instead of "teal." V03 only explicitly names "golden" (gold) — "turquoise" and "colorful" are vague substitutes. The style guide requires ≥3 palette colors by name.
**Evidence:**
- V01: `"coral and gold pennants...turquoise water"` — "turquoise" is close to teal but not exact
- V03: `"golden sunrise glow...bright turquoise water"` — only 1 named palette color
**Recommendation:** Replace "turquoise" with "teal" (the canonical name) in V01. Add explicit emerald/magenta/coral references to V03.

### [PA-06] — Negative Prompt Inconsistency Across Batch Files
**Severity:** MEDIUM
**File:** batch_blog_images.json vs batch_blog_images_v2.json
**Dimension:** D4
**Description:** The two batch JSON files use different negative prompt sets, and neither matches the canonical default negative prompt from `prompts/examples.md`.
**Evidence:**
- Canonical default: `"blurry, bad quality, worst quality, low resolution, text, watermark, signature, deformed, ugly, duplicate, morbid"` (11 terms)
- batch_blog_images.json: `"blurry, bad quality, text, watermark, signature, deformed, ugly, photorealistic, 3d render"` (9 terms, missing: worst quality, low resolution, duplicate, morbid; added: photorealistic, 3d render)
- batch_blog_images_v2.json: `"photorealistic, 3d render, colorful, neon, bright colors, text, words, letters, watermark, signature, blurry, deformed, ugly"` (13 terms, adds: colorful, neon, bright colors, words, letters)
**Recommendation:** If these use a different aesthetic, define a corresponding default negative prompt for that style. If they should match canonical, sync them.

### [PA-07] — Skill Doc Uses "aesthetic" Variant for Style Anchor
**Severity:** LOW
**File:** docs/blog-image-generation-skill.md:66
**Dimension:** D4
**Description:** The skill doc's "Style constraints" section says `Latin American folk art, magical realism illustration` (missing `style` keyword). This differs from the canonical anchor `Latin American folk art style, magical realism illustration` in the examples.md style guide.
**Evidence:** Line 66: `- **Aesthetic:** Latin American folk art, magical realism illustration`
**Recommendation:** Update to `Latin American folk art style, magical realism illustration` to match the canonical anchor.

### [PA-08] — Skill Doc Example Prompt Violates Style Guide
**Severity:** MEDIUM
**File:** docs/blog-image-generation-skill.md:90-94
**Dimension:** D4
**Description:** The example prompt in the skill doc uses "hands emerging from soil, reaching toward the sky" — this uses arm action verbs ("reaching") and visible hand anatomy, both explicitly warned against in the same doc's figure representation guidance (lines 71-77).
**Evidence:** `"Latin American magical realism illustration of hands emerging from soil, reaching toward the sky, woven with golden threads..."` — also uses `Latin American magical realism illustration` instead of `Latin American folk art style, magical realism illustration`
**Recommendation:** Replace with a scene that doesn't feature hands/arms, or rewrite to use backlighting. Fix anchor to canonical form.

### [PA-09] — Skill Doc "Complete Workflow" Prompts Non-Compliant
**Severity:** MEDIUM
**File:** docs/blog-image-generation-skill.md:220-237
**Dimension:** D4
**Description:** Both example prompts in the "Complete Workflow" section violate style rules: neither uses the canonical style anchor, Image 1 features "interlocking hands" with "palms glowing" (hand anatomy + visible figures), and Image 2 drops the style anchor entirely.
**Evidence:**
- Image 1: `"Latin American magical realism illustration of interlocking hands in a circle, palms glowing..."` — wrong anchor, hand anatomy
- Image 2: `"Illustration of a garden transforming from storm to light..."` — no style anchor at all, no `no text` constraint
**Recommendation:** Rewrite examples to follow the template system. Use canonical anchor and avoid hand/arm anatomy.

### [PA-10] — Style Guide Internal Consistency: Strong
**Severity:** INFO
**File:** prompts/examples.md (Style Guide sections, lines 1-178)
**Dimension:** D4
**Description:** The style guide is internally consistent: the color palette, mood/lighting rules, composition guidelines, canonical anchor requirement, "no text" rule, SDXL tips, do's/don'ts, negative prompt strategy, and template system all align without contradiction. The checklist at line 169-177 accurately reflects all stated rules.
**Evidence:** Cross-referenced all style rules against each other — no conflicts found.
**Recommendation:** No action needed. The guide is well-authored.

### [PA-11] — Anti-Pattern Examples Still Relevant
**Severity:** INFO
**File:** docs/blog-image-generation-skill.md:245-267; prompts/examples.md:86-96
**Dimension:** D4
**Description:** Anti-patterns in both files remain relevant to SDXL 1.0 behavior. The warnings about text hallucination, vague prompts, guidance > 7.5, SD 1.5 negative terms, and negating colors/objects are all current best practice.
**Evidence:** Reviewed against SDXL documentation and current model behavior.
**Recommendation:** No changes needed.

### [PA-12] — Prompt 04 (Original) Uses Arm Action Verb "gesturing"
**Severity:** HIGH
**File:** prompts/examples.md:208 (Prompt 04)
**Dimension:** D4
**Description:** The style guide in `docs/blog-image-generation-skill.md` lines 76 explicitly warns: "Avoid arm/hand action verbs — words like holding, extending, reaching, leaning, receiving, pointing cause SDXL to render distorted or anatomically wrong arms." Prompt 04 uses "gesturing," which triggers the same distortion.
**Evidence:** `"the figure gesturing towards the bubbles as if testing ideas"` — "gesturing" is an arm action verb
**Recommendation:** Rewrite: remove the figure's action; let the scene convey experimentation (e.g., `"a dark silhouette figure backlit against teal light, standing in a blooming garden surrounded by floating translucent thought bubbles..."`).

---

## Summary Statistics

| Check | Pass | Warn | Fail |
|-------|------|------|------|
| Style anchor correct | 8/10 | 1 (Prompt 02 `aesthetic`) | 1 (skill doc example) |
| ≥3 palette colors | 7/10 | 2 (V01, V03) | 1 (V03 borderline) |
| Silhouette for figures | 2/5 (figures) | 1 (Prompt 03, 05) | 3 (Prompt 04, V04, V05) |
| No-text guard | 10/10 | 0 | 0 |
| 15-25 word detail range | 10/10 | 0 | 0 |
| Style guide consistency | ✅ consistent | — | — |
| Anti-patterns relevant | ✅ current | — | — |
| Canonical palette referenced | 7/10 | 3 | — |
| Negative prompts consistent | 1/3 sets | — | 2 (batch JSONs) |

**Prompt compliance in `prompts/examples.md`:** 3 full PASS, 4 WARN, 3 FAIL out of 10 prompts.

**Satellite file compliance:**
- `generate_blog_images.sh`: 0/5 compliant (all stale)
- `batch_blog_images.json`: 0/5 compliant (different undocumented aesthetic)
- `batch_blog_images_v2.json`: 0/5 compliant (different undocumented aesthetic)
- `docs/blog-image-generation-skill.md`: 3 prompt examples, 0/3 fully compliant

---

## Priority Recommendations

1. **CRITICAL:** Sync `generate_blog_images.sh` prompts with canonical versions or eliminate duplication (PA-03)
2. **HIGH:** Rewrite figure-containing prompts to use silhouette/backlighting per style guide (PA-02, PA-12)
3. **HIGH:** Document or resolve the pen-and-ink batch file aesthetic (PA-04)
4. **MEDIUM:** Fix anchor variant in Prompt 02 and skill doc (PA-01, PA-07)
5. **MEDIUM:** Add missing palette colors to V01, V03 (PA-05)
6. **MEDIUM:** Fix skill doc example prompts (PA-08, PA-09)
7. **MEDIUM:** Standardize negative prompts across batch files (PA-06)
