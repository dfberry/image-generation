

## 2026-04-22 - Documentation Review Session

**Session:** Comprehensive review of all 28 documentation files  
**Grade:** B+ (Excellent structure, 6 fixable issues)

Conducted structural consistency review across all 4 projects. Found:
- Perfect 7-doc structure consistency (100%)
- Strong technical accuracy verified by spot-checks
- Critical navigation gap: missing docs/README.md (P0)
- Circular reference in manim limitations doc (P0)
- 4 improvement items for P1-P2 sprints

**Output:** .squad/decisions/inbox/morpheus-doc-review.md - merged to decisions.md

## 2026-07-24 - Architecture & Code Quality Review: image-generation/

**Session:** Full architecture review of `image-generation/` subfolder  
**Grade:** A- (Mature, well-tested, a few structural debts to address)

### Key Findings

**Strengths (what's working well):**
- Pipeline architecture is sound: clean separation of load → configure → infer → cleanup
- Lazy import pattern (`_ensure_heavy_imports()` + PEP 562 `__getattr__`) is elegant — lets `import generate` succeed without GPU stack
- OOM handling with retry + step halving is production-quality
- Batch processing with per-item GPU memory flushes prevents accumulation
- 170 tests across 15 files, all mock-based (no GPU needed) — excellent coverage philosophy
- Security: `_validate_output_path()` blocks directory traversal and absolute paths in batch mode
- CLI design: mutually exclusive `--prompt`/`--batch-file`, custom argparse types with helpful error messages
- Refiner pipeline correctly shares text_encoder_2 and VAE, with proper latent-to-CPU offload between stages
- Makefile is cross-platform (Windows + Unix detection)
- `prompts/examples.md` is an exceptional style guide — color palette, anti-patterns, token budget, checklist

**Issues Found (prioritized):**

| # | Severity | Finding |
|---|----------|---------|
| 1 | P1 | **2 test files import `torch` eagerly** — `test_oom_handling.py` and `test_unit_functions.py` do `import torch` at module level, causing `ModuleNotFoundError` on CPU-only dev machines without torch installed. All other test files use the lazy pattern correctly. |
| 2 | P1 | **6 ruff lint errors** in `test_coverage_gaps.py` — unused imports (`pytest`, `mock_torch`, `mock_makedirs`) and unsorted import block. Clean violations in test code. |
| 3 | P1 | **`_write_tests.py` is a scaffold leftover** — contains a raw string with test code, meant to be run once and deleted. Should be removed from tracked files. |
| 4 | P2 | **Batch JSON files use absolute Windows paths** — `batch_blog_images.json`, `batch_session_storage.json`, `batch_you_have_a_team.json` all hardcode `C:\Users\diberry\...` paths. Works for the author but breaks for any other contributor or CI. |
| 5 | P2 | **`batch_session_storage.json` is an exact duplicate** of `batch_blog_images.json` — identical content, no differentiation. Should be removed or differentiated. |
| 6 | P2 | **`requirements.lock` pins to very old versions** — `torch==2.1.0`, `diffusers==0.21.0` are from late 2023. The `requirements.txt` uses `>=` which is correct, but the lock file hasn't been refreshed. |
| 7 | P3 | **Model revision pinned to `"main"`** — both `load_base()` and `load_refiner()` use `revision="main"` with a TODO comment. For reproducibility, this should be a commit SHA. |
| 8 | P3 | **Single-file architecture** — `generate.py` at 627 lines handles CLI, validation, pipeline loading, inference, batch processing, retry logic, and cleanup. Still manageable but approaching the threshold where extraction would help. |

**Architecture Patterns Noted:**
- Lazy heavy-import guard: `_ensure_heavy_imports()` + `__getattr__` (PEP 562)
- OOM retry with exponential step reduction: `generate_with_retry()` halves steps on each retry
- Pre-flight GPU flush before pipeline loading in `generate()`
- Base→refiner handoff: latents moved to CPU during model swap to prevent VRAM pinning
- `_HIGH_NOISE_FRAC = 0.8` for 80/20 base/refiner split
- Batch validation: schema check → path security check → generation, with per-item error isolation

**Key File Paths:**
- Main CLI: `image-generation/generate.py` (627 lines, single module)
- Test suite: `image-generation/tests/` (15 files, 170 tests)
- Style guide: `image-generation/prompts/examples.md` (comprehensive)
- Design doc: `image-generation/docs/design.md` (living architecture doc)
- Batch configs: `image-generation/batch_*.json` (4 files)
- Lint config: `image-generation/ruff.toml` (E/F/W/I rules, line-length 120)

**Recommendations (ordered by impact):**
1. Fix the 2 torch-importing test files (P1 — breaks CI on CPU-only machines)
2. Clean up ruff lint errors in test_coverage_gaps.py (P1)
3. Delete `_write_tests.py` scaffold (P1)
4. Make batch JSON paths relative or parameterized (P2)
5. Refresh `requirements.lock` (P2)
6. Pin model revisions to commit SHAs (P3)
7. Future: extract `generate.py` into a package when it crosses ~800 lines (P3)

## 2026-05-07 - Animation Alternatives Analysis for Story-to-Video (REVISED)

**Session:** Strategic analysis of animation upgrade paths for story-to-video tool  
**Output:** `.squad/decisions/inbox/morpheus-animation-alternatives.md`  
**Critical revision:** User feedback identified fatal flaw in original recommendation

### Problem Statement

Remotion renderer currently generates only geometric shapes (squares, triangles, SVG polygons) for story scenes. Need richer narrative animations that match story content — **actual characters and objects, not just pretty backgrounds with text overlays**.

### Original Error (Corrected)

**Initial recommendation (WRONG):** Generate AI backgrounds via SDXL, layer them in Remotion with text overlays and geometric shapes on top.

**Why this was wrong:** A painted magical garden background with a spinning square "cat" isn't meaningfully better. The problem isn't the background — it's that characters/objects are rendered as geometric shapes.

**User insight:** The REAL problem is rendering actual story elements (a cat, a tree, butterflies, a gate) — not backgrounds behind shapes.

### Corrected Decision: Use Image Renderer for Narrative Scenes

**Solution:** Route narrative scenes to `image_renderer.py` (NOT Remotion). The image renderer ALREADY generates complete SDXL scenes with characters/objects included, then applies Ken Burns motion.

**Key insight:** This is an "illustrated storybook" approach — each scene is ONE complete painted image (characters + background + objects) with Ken Burns pan/zoom for motion. This is what children's digital storybooks already do (Kindle, iPad), and it's proven effective.

**Evaluated 4 revised alternatives:**

1. **Option A: Illustrated Storybook (Full SDXL Scene)** ✅ PRIMARY
   - Each scene is ONE SDXL image with ALL elements (characters + objects + background)
   - Apply Ken Burns motion + text overlay
   - **This is what image_renderer.py ALREADY DOES**
   - Pro: Real objects/characters (no geometric shapes), proven stable, fast (30-60s), minimal implementation
   - Con: Limited motion (Ken Burns only, not true animation), static poses
   - **RECOMMENDED** — solves the actual problem with existing infrastructure

2. **Option B: LLM-Generated SVG Illustrations** ⚠️ COMPLEMENTARY
   - LLM generates simple SVG paths for characters/objects inline in TSX
   - Pro: Independent motion, lightweight, stylized aesthetic
   - Con: Inconsistent quality, limited complexity (simple shapes only), doesn't match painted aesthetic
   - **Use for abstract/diagrammatic scenes only** (math diagrams, data viz)

3. **Option C: Multi-Layer SDXL Sprites with Background Removal** ❌ HIGH COMPLEXITY
   - Generate characters separately, remove backgrounds with rembg, composite in Remotion
   - Pro: Characters can move independently, full SDXL quality
   - Con: Background removal artifacts, complex composition logic, 2x generation time, sprite registry needed
   - **NOT RECOMMENDED** — too much infrastructure for uncertain quality

4. **Option D: SDXL Characters on Simple Backgrounds** ❌ MIDDLE GROUND
   - Generate characters with solid backgrounds for easier chroma keying
   - Con: SDXL inconsistent at solid backgrounds, chroma key artifacts
   - **NOT RECOMMENDED** — simpler than C but still complex

### Architecture Decision (Corrected)

**Implementation: Intelligent Scene Routing**

**Current routing:** Scene `visual_style` set by LLM during planning, used as-is.

**Problem:** LLM chooses "remotion" for narrative scenes → geometric shapes.

**Solution:** Override routing based on content analysis:

```python
class SceneRendererOrchestrator:
    def _intelligent_routing(self, scene: Scene) -> str:
        """Analyze scene content to select optimal renderer."""
        # Keywords indicating narrative content → route to image renderer
        narrative_keywords = ["character", "person", "animal", "creature", "cat", "dog", 
                             "tree", "flower", "garden", "sitting", "walking", "flying"]
        
        # Keywords indicating abstract content → route to remotion renderer
        abstract_keywords = ["diagram", "chart", "equation", "theorem", "abstract", 
                            "visualization", "geometric", "mathematical"]
        
        # Default to image renderer (conservative — better for narrative)
        if any(kw in scene.prompt.lower() or kw in scene.narration.lower() 
               for kw in narrative_keywords):
            return "image"  # Full SDXL scene with characters/objects
        elif any(kw in scene.prompt.lower() or kw in scene.narration.lower() 
                 for kw in abstract_keywords):
            return "remotion"  # LLM-generated SVG diagrams
        else:
            return "image"  # Default to narrative quality
```

**Phase 1 scope (1-2 days):**
- Implement `_intelligent_routing()` in `SceneRendererOrchestrator`
- Add CLI flags: `--force-renderer`, `--renderer-strategy`
- Enhance image renderer prompts with story element extraction
- Test: narrative scenes route to image (no geometric shapes)

**Phase 2 (optional):**
- Enhanced SVG generation for Remotion (abstract scenes only)
- Better prompt engineering for SDXL action poses

**Phase 3 (only if necessary):**
- Explore multi-layer sprites if independent motion becomes critical

### Learnings (Corrected)

**Critical mistake identified:**
- I focused on "leveraging Remotion's animation capabilities" when the real need was "rendering actual story content"
- The image renderer already renders story content better than Remotion (SDXL paints complete scenes; LLM-TSX produces abstractions)
- **This wasn't an "animation problem" — it was a "content rendering problem"**

**Architecture patterns:**
- **Use the right tool for the job** — image renderer for narrative scenes (real objects), Remotion for abstract scenes (diagrams)
- **Illustrated storybook is the correct model** — industry standard for narrated visual stories, not "full animation"
- **Ken Burns provides perceived motion** — slow pan/zoom creates cinematic feel without complex animation
- **Routing logic matters** — current LLM-based routing chooses wrong renderer for narrative content

**Technical insights:**
- SDXL excels at complete scenes (characters + environment) in single image
- Trying to separate characters from backgrounds introduces complexity without clear benefit
- Ken Burns effect is proven technique for adding motion to static images (documentaries, storybooks)
- "Static pose with motion" (Ken Burns) better than "geometric animation" (spinning shapes)

**User preference:**
- Explicitly prefers "real objects" over "better animation of abstract shapes"
- Values simplicity and pragmatism (use existing tools) over new infrastructure
- Illustrated storybook aesthetic is acceptable tradeoff vs. full animation

### Key File Paths

- **Decision doc:** `.squad/decisions/inbox/morpheus-animation-alternatives.md` (revised)
- **Routing orchestrator:** `story-to-video/story_video/scene_renderer.py` (needs intelligent routing)
- **Image renderer:** `story-to-video/story_video/renderers/image_renderer.py` (ALREADY solves problem)
- **Remotion renderer:** `story-to-video/story_video/renderers/remotion_renderer.py` (for abstract scenes only)
- **SDXL pipeline:** `image-generation/generate.py` (proven, 627 lines, production-ready)
- **Style guide:** `image-generation/prompts/examples.md` (tropical magical-realism aesthetic)
