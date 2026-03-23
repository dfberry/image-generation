# Brand — History

## Project Context (seeded 2026-03-23)

- **Repo:** image-generation — SDXL image generation tool
- **Owner:** dfberry
- **Prompt skill doc:** docs/blog-image-generation-skill.md

## Learned Prompt Rules (2026-03-23)

Critical SDXL constraints discovered through empirical testing on dfberry.github.io blog images:

- **No text/letters:** Never include readable text, letters, words, signs with letters in prompts. SDXL renders them as visual noise. Use "hint of signage" or "abstract symbols" instead.
- **Backlit silhouette for people:** "dark silhouette figure backlit against [light source]" is the most reliable featureless figure technique. Avoids racial representation issues entirely.
- **No arm/hand action verbs:** holding, reaching, extending, pointing → anatomically wrong renders. Place props on surfaces instead (e.g., "map spread on table" not "figure holding a map").
- **Token limit:** SDXL CLIP truncates at 77 tokens. Put most important visual elements first.
- **Style anchor:** "tropical magical-realism style, vivid saturated colors, painterly brushwork" works well as a consistent style suffix.

## Style worked well for dfberry blog
- Tropical magical-realism
- Painterly brushwork
- Vivid saturated colors
- Dappled golden light
- No text anywhere in scene
