# Decision: Migrate Pen-and-Ink Prompts to Canonical Aesthetic

**By:** Switch (Prompt/LLM Engineer)
**Date:** 2025-07-25
**Issue:** #28

## Context

The batch JSON files (`batch_blog_images.json`, `batch_blog_images_v2.json`, `batch_session_storage.json`) used a "pen-and-ink watercolor" aesthetic with a slate blue / warm sage / charcoal palette and white backgrounds. This style was:

- Not documented in `prompts/examples.md`
- Completely different from the canonical tropical magical-realism style
- Confusing for contributors who read the style guide then see contradicting prompts

## Decision

**Migrate** all batch file prompts to the canonical tropical magical-realism aesthetic defined in `prompts/examples.md`.

### What Changed

| Aspect | Before (pen-and-ink) | After (canonical) |
|--------|---------------------|-------------------|
| Style anchor | "Pen-and-ink illustration" | "Latin American folk art style, magical realism illustration" |
| Palette | Slate blue, warm sage, charcoal | Magenta, teal, emerald, gold, coral, amber (≥3 per prompt) |
| Background | White background | Dense tropical foliage fills negative space |
| Human figures | "A person stands" | "A distant silhouette stands" |
| Magical elements | None | Glowing objects, luminous light, magical transformations |
| Negative prompt | Non-standard (included "photorealistic, 3d render") | Project default (11 terms from style guide) |
| "No text" guard | Present | Present (preserved) |

### Why Migrate (Not Keep or Dual-Support)

1. **Single aesthetic** — the project style guide is authoritative; maintaining two styles creates confusion
2. **Undocumented** — pen-and-ink was never added to the style guide, suggesting it was experimental
3. **Topics preserved** — all 5 image concepts (lighthouses, cliffs, dock, river, cross-section) kept their meaning

## Alternatives Considered

- **Keep both styles**: Rejected — would require documenting pen-and-ink as a second aesthetic, fragmenting the visual identity
- **Delete batch files**: Rejected — the image concepts are still useful for the blog post

## Impact

- 3 batch JSON files updated (15 prompts total)
- Existing generated images will no longer match the prompts (regeneration needed)
- Seeds preserved so regeneration is reproducible
