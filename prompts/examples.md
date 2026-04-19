# Example Prompts

Curated prompts in the tropical magical-realism style for the dfberry blog post visuals.

---

## Style Guide — Tropical Magical-Realism Aesthetic

This section is the authoritative reference for every prompt written for this project. Read it before writing or editing any prompt.

### The Aesthetic: Tropical Magical-Realism

We generate illustrations that look like **hand-painted Latin American folk art infused with magical-realism elements** — everyday scenes where something luminous or impossible is happening and nobody in the scene finds it strange.

Think of it as: the warmth and pattern density of Mexican papel picado meets the quiet surrealism of Gabriel García Márquez, rendered as a painted illustration.

**Core traits:**
- **Hand-painted feel** — visible brushwork texture, flat-to-moderate depth, no photorealism
- **Magical elements treated as ordinary** — glowing scrolls, light particles, translucent figures are part of the scene, not special effects
- **Dense, lush composition** — tropical foliage fills negative space; scenes feel alive and abundant
- **Warm luminosity** — light comes from within objects (lanterns, crystals, flowers) as much as from the sky

### Color Palette

| Color | Hex (approximate) | Usage |
|-------|-------------------|-------|
| Deep magenta | `#B5179E` | Primary accent, flowers, ribbons, banners |
| Teal | `#118AB2` | Water, sky accents, cool balance |
| Emerald green | `#2D6A4F` | Foliage, vegetation, grounding element |
| Warm gold | `#E9C46A` | Light sources, keys, sacred/important objects |
| Coral | `#F4845F` | Warmth accents, secondary flowers, fabric |
| Amber | `#E76F51` | Sunset tones, lantern glow, earth tones |

**Palette rules:**
- Every image should feature **at least 3** of these colors prominently
- Gold is reserved for light sources and objects of significance (keys, scrolls, bridges)
- Magenta and teal create the primary contrast pair
- Emerald grounds the scene — it's almost always present as foliage

### Mood & Lighting

- **Mood:** Warmth, community, luminous energy, quiet wonder
- **Lighting direction:** Warm side-lighting or diffused golden light. Avoid harsh overhead or flat lighting.
- **Light sources:** Prefer diegetic light — lanterns, glowing objects, bioluminescent plants. "Warm afternoon light," "soft warm gold light," "golden sunrise glow" are reliable tokens.
- **Avoid:** Cold blue light, dramatic shadows, noir lighting, overcast grey

### Composition

- **Resolution:** 1024×1024 (SDXL native). Do not change.
- **Framing:** Slightly wider than the subject — leave room for foliage and environmental detail
- **Depth:** Moderate. We want layered scenes (foreground objects, mid-ground subject, background foliage) but not deep perspective
- **Density:** Fill the frame. Empty space feels wrong in this aesthetic — tropical plants, flowers, patterns, or light particles should occupy margins

### Canonical Style Anchor

Every prompt **must** include this exact style anchor phrase:

```
Latin American folk art style, magical realism illustration
```

This two-part anchor is non-negotiable:
- `Latin American folk art style` → triggers the hand-painted, pattern-dense, warm-palette aesthetic
- `magical realism illustration` → adds the surreal-but-ordinary quality and prevents photorealistic drift

**Do not** use shortened versions like "folk art illustration" or drop "magical realism." These weaken the aesthetic significantly — SDXL responds to both anchors together more strongly than either alone.

### The "No Text" Rule

Every prompt **must** end with `no text` as the final constraint.

SDXL frequently hallucinates text (signs, labels, watermarks) into scenes. The "no text" positive constraint combined with `text` in the negative prompt creates a double-block that is the most reliable text suppression method for SDXL.

### What SDXL Responds Well To

| Technique | Example | Why it works |
|-----------|---------|-------------|
| Specific color mentions | "deep magenta ribbons, teal water" | SDXL's CLIP encoder handles color adjective+noun pairs well |
| Named art movements | "Latin American folk art" | Strong training signal — produces coherent style |
| Lighting descriptors | "warm amber light filtering through foliage" | SDXL excels at atmospheric lighting when described precisely |
| Material textures | "weathered colorful doors," "mosaic tile floor" | Concrete nouns with texture adjectives generate rich detail |
| Emotional tone words | "sense of barrier and confusion," "playful and experimental mood" | Subtly influences composition and color temperature |
| "no text" as positive constraint | Placed at end of prompt | More reliable than only using negative prompts for text |
| Quality pair in negatives | "bad quality, worst quality" | SDXL training specifically associated these captions with low quality |

### What SDXL Responds Poorly To

| Anti-pattern | Why it fails | Do instead |
|-------------|-------------|------------|
| Negating colors ("no red") | Model attends to the noun, often produces *more* of it | Control color through positive palette tokens |
| Negating objects ("no trees") | Same attention problem — makes object more likely | Fill the scene positively instead |
| Vague style words ("nice," "pretty") | Too generic, no training signal | Use specific aesthetic vocabulary (see palette, mood sections) |
| Contradicting positive and negative | "warm gold light" + negative "gold" | SDXL can't resolve the conflict — produces muddy output |
| Over-long negative prompts (30+ terms) | Token blending kicks in, terms ignored | Keep negatives focused (our default is 11 terms) |
| SD 1.5 negative terms | "lowres, normal quality" | Different text encoder (SDXL uses OpenCLIP + CLIP). Use our default. |
| guidance > 7.5 for final output | Over-saturation, harsh edges, artifact amplification | Stay in 7.0–7.5 range for SDXL (see Parameter Recommendations) |

### Do's and Don'ts

**Do:**
- ✅ Start every prompt with the scene/subject, then layer in style, palette, mood, and constraints
- ✅ Include the canonical style anchor in every prompt (`Latin American folk art style, magical realism illustration`)
- ✅ End every prompt with `no text`
- ✅ Use at least 3 palette colors by name in every prompt
- ✅ Describe light sources and their color temperature
- ✅ Use the default negative prompt for every generation
- ✅ Test at `--steps 20 --guidance 7.0` before committing to a long generation

**Don't:**
- ❌ Drop "magical realism" from the style anchor
- ❌ Use "folk art illustration" without "Latin American" qualifier
- ❌ Forget "no text" on any prompt
- ❌ Use guidance above 7.5 — it over-saturates SDXL output
- ❌ Write prompts longer than ~75 tokens (SDXL's CLIP truncates at 77)
- ❌ Copy negative prompt strategies from SD 1.5 guides
- ❌ Leave large empty areas in composition descriptions

### Negative Prompts

Always apply the default negative prompt (see [Negative Prompts](#negative-prompts-1) below). It suppresses common SDXL artifacts that clash with our folk art aesthetic.

---

## Prompt Template System

Every prompt follows a 5-component structure. This ensures consistency across the library and makes it easy to write new prompts that match the aesthetic.

### Template Structure

```
{scene_description}, {palette_hints}, {style_anchor}, {mood_and_lighting}, {constraints}
```

| Component | What it contains | Example |
|-----------|-----------------|---------|
| **Scene description** | The subject, setting, and key objects. Be concrete and specific. | "A labyrinth of weathered colorful doors half-hidden by dense tangled vines and thorny tropical plants, each door painted in deep magenta, teal, and emerald green but locked and overgrown, narrow winding paths leading nowhere" |
| **Palette hints** | Explicit color references from our palette woven into the scene. Minimum 3 colors. | *(often embedded in scene description — "deep magenta, teal, and emerald green")* |
| **Style anchor** | The canonical style phrase. Always identical. | "Latin American folk art style, magical realism illustration" |
| **Mood and lighting** | Emotional tone + light source/quality. | "dim amber light filtering through thick foliage, sense of barrier and confusion" |
| **Constraints** | Technical constraints. Always includes "no text". | "no text" |

### Writing a New Prompt — Step by Step

1. **Start with the concept.** What does this image represent? Write a one-sentence description (this becomes the `## Prompt NN — Title` heading).

2. **Draft the scene.** Describe what a viewer sees. Use concrete nouns with texture/color adjectives. Weave in at least 3 palette colors naturally.

3. **Append the style anchor.** Copy-paste exactly: `Latin American folk art style, magical realism illustration`

4. **Add mood and lighting.** Describe the emotional feel and at least one light source with its color.

5. **End with constraints.** Always `no text`. Add scene-specific constraints if needed.

6. **Check token length.** Keep the full prompt under ~75 tokens. SDXL's CLIP encoder truncates at 77 tokens — anything beyond is ignored.

### Template Examples

**Minimal (fills all slots):**
```
A glowing tropical garden with magenta flowers and teal pools reflecting golden light, Latin American folk art style, magical realism illustration, warm sunset glow, no text
```

**Full (production quality):**
```
A labyrinth of weathered colorful doors half-hidden by dense tangled vines and thorny tropical plants, each door painted in deep magenta, teal, and emerald green but locked and overgrown, narrow winding paths leading nowhere, dim amber light filtering through thick foliage, Latin American folk art style, magical realism illustration, sense of barrier and confusion, no text
```

### Checklist for New Prompts

- [ ] Scene is concrete and specific (not abstract or vague)
- [ ] At least 3 palette colors named explicitly
- [ ] Style anchor is exact: `Latin American folk art style, magical realism illustration`
- [ ] At least one magical-realism element (glowing objects, impossible light, translucent figures, etc.)
- [ ] Light source described with color temperature
- [ ] Ends with `no text`
- [ ] Total prompt is under ~75 tokens
- [ ] Alt text written for accessibility

---

## Prompt Library

### Original Series — Abstract/Metaphorical

## Prompt 01 — Friction Wall (Cloning without context)
```
A labyrinth of weathered colorful doors half-hidden by dense tangled vines and thorny tropical plants, each door painted in deep magenta, teal, and emerald green but locked and overgrown, narrow winding paths leading nowhere, dim amber light filtering through thick foliage, Latin American folk art style, magical realism illustration, sense of barrier and confusion, no text
```
**Alt text:** A labyrinth of colorful locked doors tangled in tropical vines, representing the friction a contributor faces when cloning a repo without team context.

```bash
python generate.py --prompt "A labyrinth of weathered colorful doors half-hidden by dense tangled vines..." --refine --seed 42
```

## Prompt 02 — The Squad Gift (What travels with the code)
```
A luminous gift box overflowing with glowing scrolls, colorful ceremonial banners, and glowing memory crystals, each item radiating deep magenta, teal, emerald, and gold light, arranged on a tropical wooden table surrounded by vibrant flowers, Latin American folk art style, magical realism illustration, warm amber lighting, sense of abundant knowledge and tools ready to use, no text
```
**Alt text:** A radiant gift box overflowing with scrolls, banners, and glowing crystals, symbolizing the committed Squad directory that travels with every cloned repo—conventions, routing, history, and skills all included.

## Prompt 03 — Inner Source Bridge (Standards travel with the code)
```
A sturdy bridge woven from golden circuit patterns and luminous tropical flowers spanning between two vibrant village squares, one village on each side connected by the glowing pathway, distant silhouettes carrying colorful glowing lanterns across the bridge, deep teal and emerald green palette with warm gold accents, Latin American folk art style, magical realism illustration, birds carrying light particles between the villages, sense of effortless knowledge transfer, no text
```
**Alt text:** A luminous bridge of tropical flowers and circuit patterns connecting two team villages with distant silhouettes carrying lanterns, representing how Brady's standards and conventions automatically travel with cloned repos—contributors conform without friction.

## Prompt 04 — Contributor Experimentation (Cheap to try ideas)
```
A distant silhouette standing in a blooming tropical garden surrounded by floating translucent thought bubbles showing different colorful architectural diagrams, each bubble glowing with teal, magenta, or emerald light, lush foliage in warm coral and amber tones, Latin American folk art style, magical realism illustration, playful and experimental mood, light particles connecting the bubbles to a glowing decisions scroll in the center, no text
```
**Alt text:** A distant silhouette in a blooming garden surrounded by glowing thought bubbles showing architectural ideas, representing how a committed Squad makes experimentation cheap—test approaches against decisions.md before building.

## Prompt 05 — Knowledge Persistence (What stays when contributors leave)
```
An ancient tropical tree with massive roots and glowing amber lanterns hanging from its branches, colorful glowing memory scrolls and skill badges embedded in the bark like living artifacts, deep emerald green foliage with teal and magenta blossoms, soft warm gold light illuminating the scene, Latin American folk art style, magical realism illustration, sense of permanence and living history, figures from different eras standing around the tree in faded translucent forms showing continuity across time, no text
```
**Alt text:** An ancient tropical tree with glowing memory scrolls and skill badges embedded in its bark, representing how Squad preserves institutional knowledge—when contributors leave, their learnings stay committed in agent histories and decisions.

## Parameter Recommendations

| Use case | --steps | --guidance | --refine |
|----------|---------|------------|----------|
| Quick draft | 20 | 7.0 | no |
| Blog quality | 40 | 7.5 | yes |
| Best quality | 50 | 7.5 | yes |

> **Note on guidance scale:** SDXL's sweet spot is **7.0–7.5**. Values above 7.5 cause over-saturation, harsh edges, and artifact amplification. The previous recommendation of 8.0 for "best quality" was above this sweet spot and has been corrected. If you want more prompt adherence, increase steps rather than guidance.

---

## Negative Prompts

Negative prompts tell SDXL what to suppress during generation. They are essential for maintaining the clean, illustrative quality our tropical magical-realism aesthetic demands. Without them, SDXL tends to introduce photorealistic artifacts, text fragments, and quality degradation that break the folk art style.

### Default Negative Prompt

Use this for every generation unless you have a specific reason to customize:

```
blurry, bad quality, worst quality, low resolution, text, watermark, signature, deformed, ugly, duplicate, morbid
```

### Why Each Term Is Included

| Term | What It Prevents | Why It Matters for Our Aesthetic |
|------|-----------------|--------------------------------|
| `blurry` | Soft focus, out-of-focus areas | Folk art illustration demands crisp linework and defined shapes. Blur destroys the hand-painted feel. |
| `bad quality` | Generic quality degradation | Broad catch-all that pushes SDXL toward its higher-quality latent space. |
| `worst quality` | Severe artifacts, broken anatomy | Paired with `bad quality`, creates a two-tier quality floor. SDXL responds well to this combination. |
| `low resolution` | Pixelation, loss of fine detail | Our 1024×1024 native resolution needs full detail — especially in foliage textures and tile patterns. |
| `text` | Random letters, words, signage | SDXL frequently hallucinates text into scenes. Our prompts already include "no text" as a positive constraint; this negative reinforces it from the suppression side. |
| `watermark` | Watermark-like overlays | Training data artifacts. Shows up as semi-transparent stamps that ruin the illustration feel. |
| `signature` | Artist signature artifacts | Similar to watermark — inherited from training data. Appears as scribbles in corners. |
| `deformed` | Distorted anatomy, warped objects | People, hands, and architectural elements (bridges, doors) in our prompts need structural integrity. |
| `ugly` | Aesthetically unpleasant output | Broad suppression term. Pushes generation toward the more visually appealing region of the latent space. |
| `duplicate` | Repeated elements, clone artifacts | Prevents doubled flowers, duplicated figures, or mirrored scene elements that break composition. |
| `morbid` | Dark, disturbing imagery | Our mood is warmth and community. This prevents the model from drifting toward unsettling interpretations of words like "ancient," "faded," or "translucent forms." |

### When to Customize vs. Use the Default

**Always start with the default.** Then add scene-specific terms only when you see unwanted artifacts in test generations.

| Scenario | Action |
|----------|--------|
| Standard blog image generation | Use the default as-is |
| Prompt includes people/figures | Add: `bad hands, extra fingers, extra limbs, missing fingers` |
| Prompt includes architecture (bridges, doors, buildings) | Add: `cropped, out of frame` to keep structures complete |
| Prompt includes fine patterns (tilework, circuit patterns) | Add: `jpeg artifacts, compression artifacts` to preserve detail |
| You see photorealistic drift in outputs | Add: `photorealistic, 3d render, photograph` to reinforce the illustration style |
| You see unwanted dark mood | Add: `dark, gloomy, horror` to keep the warm folk art tone |

**Never remove** `text`, `watermark`, or `signature` from the default — these are nearly always needed for SDXL.

### SDXL-Specific Negative Prompt Tips

**What works well with SDXL:**
- **Quality pair:** `bad quality, worst quality` together is more effective than either alone. SDXL's training specifically associates these captions with low-quality images.
- **Style negation is powerful:** If output drifts photorealistic, negating `photorealistic, 3d render, photograph` is more effective than adding more positive style tokens.
- **Anatomical terms:** `deformed, extra fingers, bad hands` dramatically improves any prompt that includes human figures. Our "Knowledge Persistence" and "Hotel Staff" prompts benefit from this.
- **"no text" in positive + `text` in negative:** Double-blocking text generation from both sides is the most reliable way to prevent text artifacts in SDXL.

**What doesn't work (or backfires):**
- **Over-long negative prompts (30+ terms):** SDXL starts ignoring or blending terms. Keep the negative prompt focused — the default (11 terms) is in the sweet spot.
- **Negating colors:** Don't add `red` or `blue` to negatives to avoid certain colors. SDXL handles color negation poorly and you'll get muddy, desaturated output. Control color through the positive prompt palette instead.
- **Negating specific objects:** `no trees` or `no birds` in negatives often makes those objects *more* likely to appear (the model attends to the noun). Use composition in the positive prompt to fill the scene instead.
- **Contradicting positive tokens:** If your positive prompt says "warm gold light" don't put `gold` in the negative. SDXL can't resolve the conflict and produces unpredictable results.
- **Copying negative prompts from SD 1.5 guides:** SDXL uses a different text encoder (OpenCLIP + CLIP). Terms like `lowres, normal quality` that worked for SD 1.5 have weaker or no effect on SDXL. Stick to the terms in our default.

### Usage with generate.py

Once `--negative-prompt` is supported (see issue #3), the recommended invocation is:

```bash
python generate.py \
  --prompt "Your scene prompt here" \
  --negative-prompt "blurry, bad quality, worst quality, low resolution, text, watermark, signature, deformed, ugly, duplicate, morbid" \
  --seed 42 --refine
```

Until the flag is available, the default negative prompt should be hardcoded in the pipeline as the fallback when no `--negative-prompt` is provided.

---

---

### Vacation/Travel Series

## Blog Post: squad-inner-source — Vacation/Travel Theme (2026-03-22)

**Theme:** Open source contribution as a resort vacation. Latin American folk art style, magical realism illustration. Colors: deep magenta, teal, emerald green, warm gold, coral, amber. No text in images. People allowed.

### Image 01 — Seaplane at Tropical Dock (01-friction-wall.png)
**Concept:** First approaching an unfamiliar repo — exciting but uncertain

```
Latin American folk art style, magical realism illustration of a brightly painted seaplane gliding toward a colorful wooden dock, turquoise water below, coral and gold pennants waving from palm trees lining the pier, magenta and emerald tropical blooms along the shore, warm afternoon light, no text
```
**Seed:** 42
**Alt text:** A brightly painted seaplane gliding toward a colorful tropical dock over turquoise water with coral pennants, representing the excitement and uncertainty of approaching an unfamiliar codebase

```bash
python generate.py --prompt "Latin American folk art style, magical realism illustration of a brightly painted seaplane gliding toward a colorful wooden dock, turquoise water below, coral and gold pennants waving from palm trees lining the pier, warm afternoon light, no text" --output "outputs/01.png" --seed 42
```

### Image 02 — Welcome Basket at Resort Door (02-squad-gift.png)
**Concept:** What you get when you clone — the squad is already there waiting

```
Latin American folk art style, magical realism illustration of a vibrant resort welcome hamper overflowing with maps, golden keys, and tropical fruit at a painted hotel door, magenta and teal ribbons, luminous warm light, no text
```
**Seed:** 43
**Alt text:** A vibrant welcome hamper overflowing with maps and golden keys at a painted resort door with magenta ribbons, representing the Squad directory that greets every contributor at clone time

```bash
python generate.py --prompt "Latin American folk art style, magical realism illustration of a vibrant resort welcome hamper overflowing with maps, golden keys, and tropical fruit at a painted hotel door, magenta and teal ribbons, luminous warm light, no text" --output "outputs/02.png" --seed 43
```

### Image 03 — Arched Bridge Between Island Resorts (03-inner-source-bridge.png)
**Concept:** OSS standards and patterns travel across team boundaries

```
Latin American folk art style, magical realism illustration of an arched footbridge covered in painted flowers and folk patterns connecting two colorful resort islands over bright turquoise water, golden sunrise glow, no text
```
**Seed:** 44
**Alt text:** A flower-covered arched footbridge connecting two colorful island resorts over bright turquoise water in golden morning light, representing how the repo owner's standards and patterns travel across team and org boundaries

```bash
python generate.py --prompt "Latin American folk art style, magical realism illustration of an arched footbridge covered in painted flowers and folk patterns connecting two colorful resort islands over bright turquoise water, golden sunrise glow, no text" --output "outputs/03.png" --seed 44
```

### Image 04 — Guest in Hotel Lobby with Maps (04-contributor-success.png)
**Concept:** Validating your approach with the squad team before you build

```
Latin American folk art style, magical realism illustration of a distant silhouette of a traveler at a bright hotel lobby table covered in illustrated maps, tropical plants in terracotta pots, gold and teal tilework glowing in warm sunlight, no text
```
**Seed:** 45
**Alt text:** A distant silhouette of a traveler at a bright hotel lobby table covered in maps surrounded by tropical plants and gold tilework, representing how contributors can plan and validate their approach with the squad team before writing a line of code

```bash
python generate.py --prompt "Latin American folk art style, magical realism illustration of a distant silhouette of a traveler at a bright hotel lobby table covered in illustrated maps, tropical plants in terracotta pots, gold and teal tilework glowing in warm sunlight, no text" --output "outputs/04.png" --seed 45
```

### Image 05 — Hotel Staff Passing Knowledge (05-ceremonies-circle.png)
**Concept:** Knowledge compounds over time; what stays when contributors leave

```
Latin American folk art style, magical realism illustration of three backlit figures in hotel uniforms in a sunlit lobby, a glowing golden key and journal exchanged between them, magenta and emerald uniforms, mosaic tile floor, no text
```
**Seed:** 46
**Alt text:** Three backlit figures in hotel uniforms in a sunlit lobby with a glowing golden key and journal exchanged between them, representing how institutional knowledge is preserved and passed on rather than lost when contributors move on

```bash
python generate.py --prompt "Latin American folk art style, magical realism illustration of three backlit figures in hotel uniforms in a sunlit lobby, a glowing golden key and journal exchanged between them, magenta and emerald uniforms, mosaic tile floor, no text" --output "outputs/05.png" --seed 46
```
