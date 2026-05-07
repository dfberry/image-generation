# Decision: Pluggable image generation backends

**Date:** 2026-05-07
**Author:** Trinity (Backend Dev)
**PR:** #125
**Status:** Proposed

## Context

Local SDXL image generation times out on CPU-only machines (300s+). Azure OpenAI DALL-E 3 has been provisioned as an alternative. The image generation step was hardcoded to local SDXL in `ImageRenderer`.

## Decision

Introduced an `ImageGeneratorBase` ABC with a factory/registry pattern under `story_video/image_generators/`. Two implementations: `local` (existing SDXL subprocess) and `azure-dalle` (Azure OpenAI). Selected via `--image-provider` CLI flag, separate from `--provider` (which controls the LLM for scene planning).

## Key choices

1. **Separate `--image-provider` from `--provider`** — these are different concerns (image gen vs LLM planning). Avoids overloading `--provider` semantics.
2. **No silent fallback** — if Azure creds are missing, fail fast with a clear error. Matches existing renderer philosophy.
3. **Factory with lazy registry** — avoids import-time side effects, easy to extend with new backends later.

## Impact

- `ImageRenderer` now accepts an optional `image_generator` parameter
- `SceneRendererOrchestrator` passes it through
- Default is `local` — fully backward compatible
