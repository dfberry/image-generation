---
name: "blog-image-generation"
description: "Full workflow for generating custom images for blog posts using Stable Diffusion XL, from prompt writing to placement in posts"
domain: "image-generation, blog"
confidence: "medium"
source: "manual"
tools:
  - name: "bash"
    description: "Run generation scripts and monitor output"
    when: "Executing generate_blog_images.sh and tailing logs"
  - name: "image-generation project"
    description: "Python 3.10+ + HuggingFace diffusers SDXL pipeline"
    when: "Generating images via generate.py with custom prompts"
---

## Context

When a blog post needs custom, thematic imagery aligned to the site's tropical magical-realism aesthetic. Use this skill to generate images that match the visual palette and emotional tone of the content, then integrate them into the post with proper alt text.

**When to use:**
- Creating images for a new blog post
- Updating an existing post's images to match revised content
- Adding visual break points to long-form content

**When NOT to use:**
- Existing stock images are already well-suited
- Time constraints don't allow for 20-30 minutes of generation + placement work

## Patterns

### 0. Prerequisites

**Environment setup** (one-time):
```bash
cd <project-root>
source venv/bin/activate
```

**Model weights location:**
- Cached at: `~/.cache/huggingface/hub/models--stabilityai--stable-diffusion-xl-base-1.0` (~13GB)
- Auto-downloads on first run if not present
- Device: Apple Silicon MPS (auto-detected by HuggingFace diffusers)

**Stack:**
- Python 3.10+ + HuggingFace diffusers 0.37.0 + SDXL Base 1.0

### 1. Read the Blog Post and Map Images to Sections

Before writing any prompts, read the full post and identify key thematic moments:
- Identify 4-5 natural break points (after major sections)
- Note the emotional arc and visual themes each section introduces
- For medium posts (~15-20 sections): space images evenly after sections ~3, 7, 12, 16, 18
- Each image should reinforce its section's narrative without being literal

Example mapping for a post about community resilience:
- Image 1 (after intro): Hands joining together, warmth emerging
- Image 2 (after challenges section): Storm clouds parting, light breaking through
- Image 3 (after solutions): Gardens growing, abundance emerging
- Image 4 (after lessons): Path forward, luminous energy in landscape
- Image 5 (after conclusion): Celebration, community gathering in magical light

### 2. Write Prompts and Update Examples

**Style constraints (non-negotiable):**
- **Color palette:** Deep magenta, teal, emerald green, warm gold, coral, amber — woven throughout
- **Aesthetic:** Latin American folk art, magical realism illustration
- **Mood:** Warmth, community, luminous energy, wonder
- **Resolution:** 1024×1024 (SDXL native size)
- **Restrictions:** No text in images, no Disney/IP references, no photorealism
- **No letters or text anywhere** — SDXL renders any text as garbled gibberish. If the scene calls for signage, menus, noticeboards, or labels, use "blank", "empty", or "unreadable" as modifiers. Add the explicit phrase `no letters or text anywhere` to any prompt involving signs, gates, boards, or written elements.
- **Figures and representation** — Never describe skin tone. Use these techniques so SDXL never renders identifiable features:
  - **Most reliable:** `dark silhouette figure backlit against [light source]` — backlighting forces SDXL into a true featureless silhouette. This is the safest approach.
  - **Alternative:** `figure seen from behind` — works when combined with distance or a strong focal subject (e.g., a map board) occupying the frame. Without backlighting, SDXL may still render a side/profile view with visible features.
  - **Small/distant figures:** `small lone figure in the distance` — figures at scale have no discernible features.
  - **Groups:** `diverse figures seen from behind` or `silhouetted group` — SDXL interprets loosely but tends to vary output.
  - **Avoid arm/hand action verbs** — words like `holding`, `extending`, `reaching`, `leaning`, `receiving`, `pointing` cause SDXL to render distorted or anatomically wrong arms. Instead, let props carry the action: place an object on a desk, mount a map on a board, put a key on a tray. The figure is present without needing arms described.
  - The painterly/folk-art aesthetic already stylizes human forms; leaning into silhouette abstraction sidesteps representation concerns entirely without targeting anyone.

**Prompt structure:**
Each prompt should paint a specific visual scene:
```
{Latin American magical realism illustration style}, {subject/scene}, 
{specific colors and lighting}, {mood/emotion}, 
{folk art or cultural element}, warm and luminous atmosphere, 
illustrated in rich jewel tones of {palette colors}
```

**Example prompts:**
```
Latin American magical realism illustration of hands emerging from soil, 
reaching toward the sky, woven with golden threads and emerald vines, 
teal and magenta auras surrounding them, folk art textile patterns adorning their palms, 
warm and luminous atmosphere, illustrated in rich jewel tones
```

**Update tracking:**
After writing each prompt, add it to `prompts/examples.md` in the image-generation project:
```markdown
## Blog Post: [post-title]

### Image 1: [section theme]
[Your prompt here]
- Seed: 42 (or chosen seed)
- Used in: /website/blog/media/[post-slug]/image-01.png
```

### 3. Update the Generation Script

Edit `generate_blog_images.sh` in the image-generation project:

```bash
#!/bin/bash

# Blog Post Images: [post-title]
# Usage: bash generate_blog_images.sh &
# Monitor: tail -f generation.log

python -u generate.py \
  --prompt "Latin American magical realism illustration of..." \
  --output "outputs/01.png" \
  --seed 42

python -u generate.py \
  --prompt "Latin American magical realism illustration of..." \
  --output "outputs/02.png" \
  --seed 43

# ... (continue for each image)
```

**Key flag:** Use `python -u generate.py` (unbuffered output for live logging)

### 4. Generate One at a Time — Await Approval Before Moving

Generate images **one at a time**. Do NOT bulk-generate all images then move them. The workflow is:

```
generate → show to user → await approval → move → generate next
```

**Generate command (per image):**
```bash
cd <project-root>
source venv/bin/activate
python -u generate.py \
  --prompt "..." \
  --output "outputs/NN-new.png" \
  --seed NN \
  --refine
```

- Use `--refine` for higher quality (adds ~7 min on Apple Silicon MPS with refiner)
- Save as `NN-new.png` (not `NN.png`) to avoid overwriting originals until approved
- Start seeds at 42, increment by 1 per image (42, 43, 44, ...)
- Timing: ~7 min per image with `--refine` on Apple Silicon MPS

**After generation:** Show the user the output path and await their approval before proceeding.

### 5. Move Approved Image to Blog Media Directory

**Immediately after the user approves each image**, copy it to the blog media folder with its final name. Do NOT wait until all images are done.

```bash
cp ./outputs/NN-new.png \
   <blog-repo>/website/blog/media/{post-slug}/{final-name}.png
```

**Naming convention:** `NN-descriptive-slug.png` (e.g., `01-friction-wall.png`, `02-squad-gift.png`)
- Zero-padded number + hyphen + slug describing the image content
- Final names are defined before generation begins (match what's referenced in the blog markdown)

**Example seed table:**

| # | Generate as | Move to |
|---|-------------|---------|
| 01 | `outputs/01-new.png` | `media/{post-slug}/01-friction-wall.png` |
| 02 | `outputs/02-new.png` | `media/{post-slug}/02-squad-gift.png` |
| 03 | `outputs/03-new.png` | `media/{post-slug}/03-inner-source-bridge.png` |

**Then generate the next image.** Never get ahead of user approval.

### 6. Update Alt Text in Blog Post

Each image in the Markdown/MDX should have descriptive alt text:

```markdown
![A scene of hands emerging from rich soil, reaching upward with golden light and emerald vines wrapping around them, representing how communities grow from collective action and shared roots](./media/{post-slug}/01.png)
```

**Alt text format:**
```
[What is shown in the image], representing [what it symbolizes for this post's theme]
```

**Guidelines:**
- Describe visual elements first (colors, composition, subjects)
- Second part connects it to the post's narrative
- 15-25 words typical
- Imagine reading it to someone who can't see the image

### 7. Commit Images and Updated Post

```bash
cd <blog-repo>

git add website/blog/media/{post-slug}/ website/blog/{post-filename}.md
git commit -m "Add custom SDXL images for [post-title]

Generated 5 images using Stable Diffusion XL with tropical 
magical-realism aesthetic. Images placed in sections [list sections].

Co-authored-by: Pepa <pepa@encanto>"
```

## Examples

### Complete Workflow Example

**Blog post:** "Building Community Resilience" 

**Image 1 prompt:**
```
Latin American magical realism illustration of interlocking hands in a circle,
palms glowing with warm gold and coral light, intricate folk art patterns 
flowing across skin and into the ground as roots, teal and emerald energy
spiraling upward, surrounded by luminous seed pods and woven textile designs,
painted in rich jewel tones with deep magenta shadows and golden highlights
```

**Image 2 prompt:**
```
Illustration of a garden transforming from storm to light: dark clouds breaking
apart above, revealing teal and magenta auroras, below ground roots glow with
coral and gold energy, new shoots sprouting upward with emerald leaves,
folk art motifs of protection and growth woven into the landscape,
warm luminous atmosphere suggesting hope and renewal
```

**Alt texts:**
- Image 1: "Interlocking hands glowing with warm light and folk art patterns, representing the bonds and collective strength that build resilience"
- Image 2: "Storm clouds parting above a glowing garden, representing the transition from crisis to growth and hope"

## Anti-Patterns

**❌ Don't:**
- Use generic or stock-photo-like prompts ("realistic photograph of...")
- Include text, brand logos, or Disney characters
- Use prompts with words like "sign", "label", "menu", "banner", or "banner text" without also adding `no letters or text anywhere` — SDXL will render garbled characters
- Ignore the color palette in pursuit of photorealism
- Run `nohup bash script.sh` (causes fatal errors with unbuffered I/O)
- Place images randomly; map them to narrative moments first
- Write 50+ word prompts; SDXL performs better with 15-25 words of detail
- Skip alt text or use vague descriptions ("image", "picture", "graphic")
- Commit images without updating the tracking doc (examples.md)

**❌ Avoid these prompt mistakes:**
- "Create a beautiful sunset" (vague, no style context)
- "Stable Diffusion style..." (redundant; let the aesthetic speak)
- "4k ultra HD" (ignored by SDXL; wastes tokens)
- Mixing styles: "Latin American + anime + photorealism" (confuses the model)

**⚠️ Known issues:**
- SDXL may warn about "clip_text_model" — harmless, can ignore
- First image takes longest (weights loading); subsequent images faster
- MPS device memory can spike; monitor Activity Monitor's GPU pressure
- `--seed 42` guarantees reproducibility; change seed number for variation
- Very specific real-world locations in prompts don't work well; use conceptual descriptions instead
