# Decision: Richer Animation Alternatives for Story-to-Video

**Date:** 2026-05-07  
**Owner:** Morpheus (Lead)  
**Status:** Proposal  
**Impact:** Defines technical approach for upgrading story-to-video from geometric shapes to narrative-quality animations

---

## Context

The `story-to-video` tool currently orchestrates multi-scene videos from text stories using three renderers:

1. **Image renderer** — Static SDXL images with Ken Burns effect + text overlay (works well, proven stable)
2. **Remotion renderer** — LLM-generated React/TSX components that currently produce only geometric shapes (squares, triangles, SVG polygons)
3. **Manim renderer** — Placeholder implementation (ffmpeg colored rectangles with text)

**Current limitation:** Remotion scenes lack narrative richness — the LLM generates geometric abstractions instead of actual story elements (characters, environments, objects).

**User request:** Explore alternatives for richer animations, with **sprite generation and management** mentioned as one candidate approach.

**Existing assets:**
- `image-generation/` tool already generates high-quality SDXL images (1024×1024) in a tropical magical-realism aesthetic
- Strong prompt engineering for consistent style (see `prompts/examples.md`)
- Ken Burns effect pipeline is production-ready

---

## Alternatives Compared

| Alternative | Visual Quality | Implementation Complexity | Runtime Performance | Asset Management | Integration Effort | Cost | Recommendation Score |
|-------------|---------------|-------------------------|---------------------|------------------|-------------------|------|---------------------|
| **1. AI Sprite System** | ⭐⭐⭐⭐ | 🔴 High | ⚠️ Medium | 🔴 Complex registry | 🔴 High | 💰💰💰 High | ❌ Not recommended |
| **2. AI Scene Backgrounds + Layers** | ⭐⭐⭐⭐⭐ | 🟢 Low | 🟢 Fast | 🟢 Minimal | 🟢 Low | 💰💰 Medium | ✅ **RECOMMENDED** |
| **3. Lottie/SVG Animations** | ⭐⭐⭐ | 🟡 Medium | 🟢 Fast | 🟡 Needs library | 🟡 Medium | 💰 Low | ⚠️ Limited scope |
| **4. Enhanced LLM TSX** | ⭐⭐ | 🟡 Medium | 🟢 Fast | 🟢 None | 🟢 Low | 💰 Low | ⚠️ Quality ceiling |
| **5. Video Diffusion Models** | ⭐⭐⭐⭐⭐ | 🔴 Very High | 🔴 Slow | 🟡 Cache needed | 🔴 High | 💰💰💰💰 Very High | ❌ Not ready |
| **6. Hybrid (Backgrounds + Lottie)** | ⭐⭐⭐⭐ | 🟡 Medium | 🟢 Fast | 🟡 Moderate | 🟡 Medium | 💰💰 Medium | ⚠️ Viable fallback |

---

## Detailed Analysis

### 1. AI Sprite System

**Concept:** Generate character/object sprites as transparent PNGs via SDXL, store in a registry with metadata, compose them in Remotion scenes using CSS transforms, parallax scrolling, and motion paths.

**Pros:**
- Reusable assets across scenes (generate once, use many times)
- Full control over composition and timing
- Consistent character appearances via prompt engineering + seed locking
- Parallax depth could look cinematic

**Cons:**
- **SDXL doesn't reliably generate transparent backgrounds** — need post-processing with background removal models (rembg, SAM, etc.)
- **Registry management is complex** — need database of sprites, tags, variants, size metadata
- **Composition logic is hard** — LLM would need to understand sprite placement, layering, z-index, motion paths
- **High upfront cost** — need to generate sprite library before first video
- **Consistency risk** — SDXL produces variation even with locked seeds, especially for character faces

**Why not recommended for Phase 1:** Too much infrastructure for uncertain visual payoff. SDXL excels at full scenes, not isolated sprites.

---

### 2. AI Scene Backgrounds + Foreground Layers ✅

**Concept:** For each story scene, generate a full background image via `image-generation/` (already proven), layer animated text/overlays on top in Remotion, apply parallax Ken Burns motion for depth.

**Pros:**
- **Leverages existing proven pipeline** — `image-generation/` is production-ready with 170 tests, OOM handling, refiner pipeline
- **Tropical magical-realism aesthetic is already defined** — color palette, lighting rules, style anchors all documented
- **Minimal new code** — extend Remotion renderer to accept `--background-image` flag, use Remotion's `<Img>` component
- **Fast generation** — SDXL base+refiner takes 30-60s per scene on GPU
- **Scales well** — can generate backgrounds in parallel before Remotion render
- **Quality upgrade is dramatic** — from geometric shapes to narrative-quality painted scenes

**Cons:**
- Still limited motion (Ken Burns + text animations) — not full character animation
- Each scene requires image generation (compute cost)

**Integration path:**
1. Extend `remotion_renderer.py` to call `image-generation/generate.py` for background
2. Update LLM system prompt to generate TSX that uses `<Img src={staticFile('background.png')} />` + text overlays + parallax motion
3. Remotion `<AbsoluteFill>` already supports layered composition
4. Use `zoompan` in TSX or pre-apply Ken Burns in Python before TSX render

**Cost:** ~$0.10-0.30 per scene for SDXL inference (assuming cloud GPU), or free on local GPU. Storage: ~2-5 MB per 1024×1024 PNG.

**Why recommended:** Highest quality-to-effort ratio. Builds on existing strengths. Achieves narrative richness without complex asset management.

---

### 3. Lottie/SVG Animations

**Concept:** Use pre-made Lottie JSON animations (or generate via LLM) for character/object motion. Embed in Remotion via `@remotion/lottie` or render externally and composite.

**Pros:**
- Vector-based, infinitely scalable
- Lottie library has thousands of free animations (LottieFiles)
- Lightweight files (10-100 KB per animation)
- Remotion has native Lottie support

**Cons:**
- **Style mismatch** — Lottie assets are generic, modern flat design, not tropical magical-realism
- **LLM can't reliably generate valid Lottie JSON** — too complex for current LLMs (nested bezier curves, timing functions)
- **Limited narrative fit** — pre-made Lottie assets are icons/loaders/transitions, not story characters
- **Curation overhead** — need to manually curate library of relevant animations

**Use case:** Good for UI embellishments (sparkles, transitions, decorative elements), not primary storytelling.

**Recommendation:** Viable as **Phase 2 enhancement** after backgrounds are working. Use for decorative accents only.

---

### 4. Enhanced LLM-Generated TSX (Current Approach Refined)

**Concept:** Keep current architecture but improve LLM prompt engineering to generate richer CSS art, SVG illustrations, or canvas-based drawings instead of simple shapes.

**Pros:**
- No new dependencies
- Leverages Remotion's full API
- Fast iteration (no image generation wait)

**Cons:**
- **Quality ceiling is low** — LLMs struggle with complex SVG paths, CSS art is limited
- **Current evidence shows this doesn't work well** — GeneratedScene.tsx produces geometric diagrams, not narrative scenes
- **CSS art is time-consuming to describe** — prompts would need to be very detailed
- **No consistency** — each generation would produce different interpretations

**Why not recommended as primary approach:** Already tested implicitly — current Remotion renderer uses this and produces geometric shapes. Upgrading prompt alone won't bridge the gap to narrative quality.

**Viable for:** Abstract/diagrammatic scenes (like the Pythagorean theorem example), not story scenes.

---

### 5. Video Diffusion Models (Stable Video Diffusion, etc.)

**Concept:** Generate short video clips per scene using AI video generation models like Stable Video Diffusion (SVD), Runway Gen-2, or similar.

**Pros:**
- **True motion** — characters/objects move naturally
- **Highest visual quality potential** — photorealistic or stylized video output
- **No composition logic needed** — prompt → video directly

**Cons:**
- **Extremely slow** — SVD takes 5-15 minutes per 2-4 second clip on GPU
- **Very expensive** — cloud APIs charge $0.50-5.00 per clip
- **Limited control** — can't reliably control motion, framing, timing
- **Consistency is hard** — maintaining character/style across scenes requires LoRA training
- **Models are experimental** — SVD, Runway, Pika are all 2023-2024 tech, still evolving

**Infrastructure requirements:**
- Separate model loading (SVD is ~15 GB)
- Different pipeline from SDXL
- Post-processing for resolution/format

**Why not recommended for Phase 1:** Too slow, too expensive, too experimental. Revisit in 2025-2026 when video diffusion matures.

---

### 6. Hybrid Approach (AI Backgrounds + Lottie Overlays)

**Concept:** Combine Option 2 (AI scene backgrounds) with Option 3 (Lottie for character/object motion).

**Pros:**
- Best of both worlds — narrative backgrounds + lightweight motion
- Lottie overlays add life without full sprite management

**Cons:**
- Complexity of managing two asset types
- Style coherence is harder (painted backgrounds + flat Lottie)

**Recommendation:** Consider for **Phase 2** after Option 2 is proven. Not worth complexity for Phase 1.

---

## CRITICAL REVISION (2026-05-07)

**User feedback:** Original recommendation (AI backgrounds + text overlays) doesn't solve the core problem. A painted magical garden with a spinning geometric square "cat" on top is NOT meaningfully better.

**The REAL problem:** How do you render actual story CHARACTERS and OBJECTS (a cat, a tree, butterflies, a garden gate) with motion — not just pretty backgrounds behind text?

---

## Revised Analysis: Four Approaches to Real Objects/Characters

### Option A: Illustrated Storybook Style (Full SDXL Scene) ✅ PRIMARY

**Concept:** Each scene is ONE complete SDXL image with ALL elements (background + characters + objects) painted into the scene. Apply Ken Burns motion + text overlay.

**KEY INSIGHT:** This is what `image_renderer.py` ALREADY DOES. It generates a full narrative scene via SDXL (including characters/objects), then applies Ken Burns effect + text overlay.

**Example scene:**
- SDXL prompt: "A tabby cat sitting under a mango tree in a tropical garden, butterflies flying around, golden light filtering through leaves, Latin American folk art style, magical realism illustration"
- Result: Complete painted scene with cat, tree, butterflies, garden — all in one 1024×1024 image
- Motion: Ken Burns slow zoom/pan across the scene
- Text: Narration overlaid at bottom

**Pros:**
- ✅ **ALREADY IMPLEMENTED** — `image_renderer.py` does this exact workflow
- ✅ Characters and objects are included in the scene (no geometric shapes)
- ✅ Proven stable (part of existing production pipeline)
- ✅ Fast generation (30-60s per scene)
- ✅ No complex composition logic
- ✅ Matches "illustrated storybook" aesthetic (painted scenes with gentle motion)

**Cons:**
- Limited motion (Ken Burns only, not "true animation")
- Characters can't move independently from background
- Static poses only (no walking, flying, etc.)

**Why this solves the problem:**
- No geometric shapes — SDXL generates actual cats, trees, butterflies painted into the scene
- "Motion" comes from Ken Burns panning/zooming, which creates cinematic feel
- Text overlay provides narration context
- This is essentially an animated picture book — industry-standard for children's stories

**Current usage:**
Looking at `scene_renderer.py`, the image renderer is ALREADY available. The issue is scenes are being routed to Remotion (geometric shapes) instead of image renderer (full narrative scenes).

---

### Option B: LLM-Generated SVG Character Illustrations ⚠️ COMPLEMENTARY

**Concept:** Have the LLM generate simple SVG illustrations of characters/objects inline in the TSX. Animate with CSS transforms.

**Example:**
```tsx
// LLM generates SVG path for a simple cat silhouette
<svg viewBox="0 0 200 200">
  <path d="M50,100 Q40,80 50,70 L60,80 Q55,85 60,90 ..." fill="#E76F51" />
  <circle cx="45" cy="75" r="3" fill="white" /> {/* eye */}
</svg>
```

**Pros:**
- Characters can move independently (CSS translate, rotate, scale)
- No background removal needed
- Lightweight (SVG paths are small)
- Stylized aesthetic (folk art illustrations)

**Cons:**
- LLM-generated SVG quality is inconsistent (can produce broken paths)
- Limited complexity (simple shapes only — stick figures, silhouettes, basic forms)
- Doesn't match painted SDXL aesthetic (vector vs. raster)
- Still requires LLM to understand scene composition

**Viable for:** Simple scenes with iconic shapes (sun, moon, house, tree silhouettes), not detailed characters.

**Recommendation:** Use as **Phase 2 enhancement** for abstract/diagrammatic scenes only. Not primary solution for narrative storytelling.

---

### Option C: Multi-Layer SDXL Sprites with Background Removal ⚠️ HIGH COMPLEXITY

**Concept:** Generate characters as separate SDXL images, remove backgrounds with rembg/SAM, composite in Remotion with motion paths.

**Workflow:**
1. Generate background: "tropical garden, no people, no animals"
2. Generate character sprite: "tabby cat sitting, white background, Latin American folk art style"
3. Run rembg to remove white background → transparent PNG
4. Composite in Remotion with CSS transforms for motion

**Pros:**
- Characters can move independently from background
- Full SDXL quality for both layers
- True parallax/depth separation

**Cons:**
- 🔴 Background removal is unreliable (rembg leaves halos, artifacts)
- 🔴 SDXL generates backgrounds even when prompted not to (inconsistent white backgrounds)
- 🔴 Character pose consistency is hard (SDXL variation even with locked seeds)
- 🔴 Complex composition logic (positioning, scaling, z-index, motion paths)
- 🔴 2x generation time (background + character separately)
- 🔴 Need sprite registry/management for reuse

**Why not recommended:** Too much infrastructure for uncertain quality. Background removal artifacts would be visible on high-quality painted backgrounds.

**Reconsider if:** Background removal models improve significantly OR SDXL adds native transparency support.

---

### Option D: SDXL Characters on Simple Backgrounds + Composition 🟡 MIDDLE GROUND

**Concept:** Generate characters with simple/solid backgrounds (easier for background removal), composite onto painted backgrounds.

**Workflow:**
1. Generate background: "tropical garden, Latin American folk art style"
2. Generate character: "tabby cat sitting, solid light blue background"
3. Use color-based chroma key (simpler than edge detection) to remove background
4. Composite in Remotion

**Pros:**
- Easier background removal (color-based keying)
- Characters can have motion paths
- Still uses SDXL quality

**Cons:**
- SDXL still inconsistent at solid backgrounds (adds texture, gradients)
- Chroma key leaves artifacts on similar colors
- Still 2x generation time
- Composition logic complexity remains

**Recommendation:** Explore only if Option A proves insufficient and Option B SVG quality is too low.

---

## REVISED RECOMMENDATION: Illustrated Storybook Style (Option A) + SVG for Simple Elements (Option B)

### Primary Approach: Use Image Renderer More Aggressively (Option A)

**Decision:** Route MORE scenes to the image renderer instead of Remotion renderer. The image renderer already generates complete narrative scenes (characters + objects + background) via SDXL, then applies Ken Burns motion.

**Implementation:**
1. **Update scene routing logic** in `scene_renderer.py`
   - Currently routes to Remotion for "dynamic" scenes
   - Change heuristic: route to image renderer for ANY scene with characters/objects
   - Reserve Remotion for abstract/diagrammatic content only (math diagrams, UI mockups, data viz)

2. **Enhance image renderer prompts**
   - Extract character/object descriptions from scene narration
   - Build comprehensive SDXL prompts that include all story elements
   - Example: "A tabby cat chasing butterflies through a tropical garden with a wooden gate, golden afternoon light, deep magenta flowers, Latin American folk art style, magical realism illustration, no text"

3. **Add composition hints to prompts**
   - Include framing guidance: "wide shot showing full garden", "close-up of cat's face"
   - Add action descriptions: "cat mid-leap", "butterflies in flight", "gate slightly open"
   - SDXL can render action in static poses effectively

**What this achieves:**
- ✅ Real characters and objects (no geometric shapes)
- ✅ Narrative quality (painted storybook aesthetic)
- ✅ Already implemented pipeline (minimal new code)
- ✅ Fast generation (30-60s per scene)
- ✅ Proven stable (image renderer has test coverage)

**What this doesn't achieve:**
- ❌ Independent character motion (cat and butterflies move together as one scene)
- ❌ Continuous animation (static poses only)

**Why this is acceptable:**
- Industry standard for digital storybooks (Kindle, iPad children's books)
- Ken Burns motion provides cinematic feel
- Narration text fills in motion context ("The cat leaps after the butterflies...")
- User expectations align with "illustrated story" not "full animation"

---

### Complementary Approach: LLM SVG for Abstract/Iconic Elements (Option B)

**Use Remotion renderer with SVG generation for:**
- Diagrams, charts, data visualizations
- Abstract concepts (emotions, ideas, forces)
- Iconic elements (sun, moon, stars, simple shapes)
- Transitions between narrative scenes

**Don't use for:** Character-driven narrative scenes (use image renderer instead)

---

### Implementation Plan (Revised)

#### Phase 1: Optimize Scene Routing (1-2 days)

**Owner:** Trinity (Backend Dev)

1. **Update `SceneRendererOrchestrator` routing logic** (story-to-video/story_video/scene_renderer.py)
   ```python
   def _select_renderer(self, scene: Scene) -> str:
       """Route scene to appropriate renderer based on content."""
       # Check for keywords indicating narrative content
       narrative_keywords = ["character", "person", "animal", "creature", "object", "setting"]
       
       # Check for abstract/diagrammatic keywords
       abstract_keywords = ["diagram", "chart", "equation", "concept", "abstract", "visualization"]
       
       # Route to image renderer for narrative scenes
       if any(kw in scene.prompt.lower() or kw in scene.narration.lower() 
              for kw in narrative_keywords):
           return "image"
       
       # Route to Remotion only for abstract/diagrammatic content
       if any(kw in scene.prompt.lower() or kw in scene.narration.lower() 
              for kw in abstract_keywords):
           return "remotion"
       
       # Default to image renderer (conservative — produces better results)
       return "image"
   ```

2. **Enhance image_renderer prompt building**
   - Add `_extract_scene_elements()` method to parse characters/objects from narration
   - Build comprehensive SDXL prompts that include all story elements
   - Add framing/composition hints based on scene context

3. **Add routing override CLI flag**
   - `--force-renderer image|remotion|manim` to override automatic routing
   - Useful for testing and user control

#### Phase 2: Enhanced SVG Generation for Remotion (Future, Optional)

Only pursue if Phase 1 proves insufficient for abstract scenes.

1. Update LLM system prompt to focus on simple SVG primitives (circles, rectangles, basic paths)
2. Add SVG validation to catch broken paths before render
3. Create template library of reliable SVG shapes the LLM can reference

#### Phase 3: Explore Multi-Layer Sprites (Only if Necessary)

Revisit Option C/D only if:
- Background removal tools improve significantly
- User explicitly needs independent character motion
- Phase 1 + Phase 2 prove inadequate

---

## Updated Rationale

**Why Option A (Illustrated Storybook) is the correct solution:**

1. **It already exists** — `image_renderer.py` generates complete narrative scenes with characters/objects included
2. **It solves the actual problem** — produces real cats, trees, butterflies (not geometric shapes)
3. **It's proven stable** — part of production pipeline with test coverage
4. **It's fast** — 30-60s per scene (same as "background only" approach)
5. **It matches user expectations** — illustrated storybooks are industry standard for narrated visual stories
6. **Ken Burns provides motion** — slow pan/zoom creates cinematic feel without complex animation

**Why my original recommendation was wrong:**

I focused on "leveraging Remotion's animation capabilities" when the real need was "rendering actual story content." The image renderer already renders story content better than Remotion ever will (because SDXL paints complete scenes, while LLM-generated TSX produces geometric abstractions).

**The key insight:**

This isn't an "animation problem" — it's a "content rendering problem." The solution isn't better animation of geometric shapes; it's using the renderer that produces actual story content (image renderer with SDXL) instead of the renderer that produces abstractions (Remotion with LLM-TSX).

**Visual upgrade path (revised):**
- **Phase 0 (current):** Geometric shapes in Remotion (WRONG RENDERER FOR THE TASK)
- **Phase 1 (this decision):** Route narrative scenes to image renderer → painted storybook with real characters/objects
- **Phase 2 (future):** Enhanced SVG for abstract/diagrammatic scenes in Remotion
- **Phase 3 (future):** Multi-layer sprites only if independent motion becomes critical

---

## Cost-Benefit Analysis (Revised)

| Approach | Visual Quality | Implementation | Runtime | Complexity | Cost | Solves "Real Objects" Problem? |
|----------|---------------|----------------|---------|------------|------|-------------------------------|
| **A: Full SDXL Scene (Storybook)** | ⭐⭐⭐⭐⭐ | 🟢 1-2 days (routing logic only) | 🟢 30-60s | 🟢 Minimal | 💰💰 Medium | ✅ YES |
| **B: LLM SVG Characters** | ⭐⭐⭐ | 🟡 3-5 days | 🟢 Fast | 🟡 Medium | 💰 Low | ⚠️ Partially (simple shapes only) |
| **C: SDXL Sprites + rembg** | ⭐⭐⭐⭐ | 🔴 7-10 days | ⚠️ 60-120s | 🔴 High | 💰💰💰 High | ✅ YES (but complex) |
| **D: Simple BG Sprites** | ⭐⭐⭐⭐ | 🔴 5-7 days | ⚠️ 60-120s | 🔴 High | 💰💰💰 High | ✅ YES (but complex) |
| **Original Rec (BG + Text)** | ⭐⭐ | 🟢 2-3 days | 🟢 40-90s | 🟡 Medium | 💰💰 Medium | ❌ NO (geometric shapes remain) |

---

## Decision Summary (Revised)

**Adopt Option A: Illustrated Storybook Style (Full SDXL Scene per Scene)**

**Primary change:** Route narrative scenes to image renderer (not Remotion renderer). The image renderer already generates complete painted scenes with characters/objects via SDXL.

**Rationale:**
- Image renderer already solves the "real objects instead of shapes" problem
- Minimal implementation (1-2 days of routing logic updates)
- Proven stable pipeline
- Matches industry standard for illustrated stories
- Fast generation (30-60s per scene)

---

## Proposed Architecture (Revised)

### Component: Enhanced Scene Routing in `scene_renderer.py`

**Current routing:** Scene visual_style is set by LLM during planning, used as-is.

**Problem:** LLM chooses "remotion" for narrative scenes → geometric shapes.

**Solution:** Override/enhance routing based on content analysis.

```python
class SceneRendererOrchestrator:
    """Routes scenes to the appropriate renderer based on content."""
    
    def render_scene(self, scene: Scene, force_renderer: str = None) -> RenderResult:
        """Route scene to the appropriate renderer."""
        # Allow CLI override
        if force_renderer:
            renderer_type = force_renderer
        else:
            renderer_type = self._intelligent_routing(scene)
        
        if renderer_type == "image":
            return self.image_renderer.render(scene)
        elif renderer_type == "remotion":
            return self.remotion_renderer.render(scene)
        elif renderer_type == "manim":
            return self.manim_renderer.render(scene)
    
    def _intelligent_routing(self, scene: Scene) -> str:
        """Analyze scene content to select optimal renderer."""
        prompt_lower = scene.prompt.lower()
        narration_lower = scene.narration.lower()
        combined = f"{prompt_lower} {narration_lower}"
        
        # Keywords indicating narrative content (use image renderer)
        narrative_keywords = [
            "character", "person", "people", "animal", "creature", 
            "cat", "dog", "bird", "tree", "flower", "garden", "house",
            "sitting", "walking", "running", "flying", "standing",
            "landscape", "environment", "setting", "scene"
        ]
        
        # Keywords indicating abstract/diagrammatic content (use remotion)
        abstract_keywords = [
            "diagram", "chart", "graph", "equation", "formula",
            "concept", "abstract", "visualization", "data",
            "geometric", "mathematical", "theorem", "shape animation"
        ]
        
        # Count keyword matches
        narrative_score = sum(1 for kw in narrative_keywords if kw in combined)
        abstract_score = sum(1 for kw in abstract_keywords if kw in combined)
        
        # Routing decision
        if abstract_score > 0 and abstract_score > narrative_score:
            return "remotion"  # Clear abstract intent
        elif narrative_score > 0:
            return "image"  # Any narrative content → full SDXL scene
        else:
            # Default to image renderer (conservative — better quality)
            return "image"
```

### Component: Enhanced Image Renderer Prompts

**Current:** Uses scene.prompt directly.

**Enhancement:** Extract story elements and build comprehensive SDXL prompts.

```python
class ImageRenderer(BaseRenderer):
    """Renders full narrative scenes with characters/objects via SDXL."""
    
    def _build_sdxl_prompt(self, scene: Scene) -> str:
        """Build comprehensive SDXL prompt including all story elements."""
        base_prompt = scene.prompt
        
        # Extract character/object mentions from narration for additional context
        # (Simple keyword extraction — LLM could enhance this in Phase 2)
        story_elements = self._extract_elements(scene.narration)
        
        # Add composition/framing hints based on scene number
        framing = self._suggest_framing(scene.scene_number, scene.duration)
        
        # Build final prompt
        prompt = f"{base_prompt}, {story_elements}, {framing}, "
        
        # Append mandatory style anchor
        prompt += (
            "Latin American folk art style, magical realism illustration, "
            "warm luminous lighting, lush tropical foliage, "
            "no text"  # Prevent SDXL from adding text to image
        )
        
        return prompt
    
    def _extract_elements(self, narration: str) -> str:
        """Extract key story elements from narration text."""
        # Simple approach: look for common action verbs and objects
        # Phase 2 could use LLM for better extraction
        elements = []
        
        if "leap" in narration.lower() or "jump" in narration.lower():
            elements.append("mid-leap")
        if "chase" in narration.lower() or "run" in narration.lower():
            elements.append("in motion")
        if "look" in narration.lower() or "gaze" in narration.lower():
            elements.append("eye contact with viewer")
        
        return ", ".join(elements) if elements else ""
    
    def _suggest_framing(self, scene_num: int, duration: float) -> str:
        """Suggest framing based on scene context."""
        # Vary framing for visual interest
        frames = [
            "wide shot showing full scene",
            "medium shot focusing on main subject",
            "close-up with shallow depth of field",
            "establishing shot with environmental context"
        ]
        return frames[scene_num % len(frames)]
```

### CLI Enhancement

```python
# story-to-video/story_video/cli.py

@click.option(
    "--force-renderer",
    type=click.Choice(["image", "remotion", "manim"], case_sensitive=False),
    help="Force all scenes to use specific renderer (overrides automatic routing)"
)
@click.option(
    "--renderer-strategy",
    type=click.Choice(["auto", "prefer-image", "prefer-remotion"], case_sensitive=False),
    default="auto",
    help="Routing strategy: auto (smart routing), prefer-image (default to image), prefer-remotion (default to remotion)"
)
def render(force_renderer, renderer_strategy, ...):
    """Render story to video."""
    # Pass to orchestrator
    orchestrator = SceneRendererOrchestrator(
        ..., 
        force_renderer=force_renderer,
        strategy=renderer_strategy
    )
```

---

## Next Steps (Revised)

### Phase 1: Intelligent Scene Routing (1-2 days)

**Owner:** Trinity (Backend Dev)

**Tasks:**
1. Implement `_intelligent_routing()` method in `SceneRendererOrchestrator`
2. Add keyword-based content analysis
3. Add CLI flags: `--force-renderer`, `--renderer-strategy`
4. Update image renderer to enhance prompts with story elements
5. Write routing tests:
   - Test: "A cat chasing butterflies" → routes to image renderer
   - Test: "Pythagorean theorem diagram" → routes to remotion renderer
   - Test: Force renderer flag overrides automatic routing

**Acceptance criteria:**
- Scenes with narrative keywords route to image renderer
- Scenes with abstract keywords route to remotion renderer
- Default routing is image renderer (conservative)
- CLI override works correctly
- Generated videos have real objects/characters (no geometric shapes for narrative scenes)

### Phase 2: Enhanced Prompt Engineering (2-3 days, Optional)

**Owner:** Trinity (Backend Dev)

**Tasks:**
1. Add LLM-based story element extraction
2. Implement framing suggestions based on scene context
3. Add action pose hints ("mid-leap", "in flight", "looking toward camera")
4. Test prompt variations for quality improvement

**Defer if:** Phase 1 prompt building produces acceptable results.

### Phase 3: SVG Enhancement for Abstract Scenes (Future)

**Owner:** Trinity (Backend Dev)

**Only pursue if:**
- Remotion renderer is still needed for abstract/diagrammatic content
- Current LLM-generated TSX is inadequate
- Phase 1 + Phase 2 are complete

---

## Risk Assessment (Revised)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Scene routing logic produces false negatives (narrative scenes routed to Remotion) | High | Medium | Add extensive keyword list, test on diverse scenes, allow CLI override |
| Image renderer Ken Burns motion feels static compared to Remotion animations | Medium | High | This is expected tradeoff — static scene with motion vs. animated shapes. User prefers real objects with less motion. |
| SDXL prompt engineering doesn't include all story elements | Medium | Medium | Start with simple keyword extraction, enhance with LLM in Phase 2 if needed |
| Users expect "true animation" (walking characters, etc.) | High | Low | Set expectations: "illustrated storybook" style, not cartoon animation. Industry standard for narrated visual stories. |
| Some scenes genuinely need Remotion (diagrams, data viz) | Low | High | Keep intelligent routing — don't force ALL scenes to image renderer. Allow both renderers to coexist. |

---

## Decision Summary (Final — Revised 2026-05-07)

**Adopt Option A: Illustrated Storybook Style (Full SDXL Scene per Scene)**

**Primary change:** Route narrative scenes to image renderer (not Remotion renderer). The image renderer already generates complete painted scenes with characters/objects via SDXL.

**Rationale:**
- ✅ Image renderer ALREADY solves the "real objects instead of shapes" problem
- ✅ Minimal implementation (1-2 days of routing logic updates)
- ✅ Proven stable pipeline (production-ready with test coverage)
- ✅ Matches industry standard for illustrated stories
- ✅ Fast generation (30-60s per scene)
- ✅ No geometric shapes — actual cats, trees, butterflies painted into complete scenes

**Implementation:** Update `SceneRendererOrchestrator` to use intelligent routing based on scene content keywords, defaulting to image renderer for narrative scenes.

**What this achieves:**
- Real characters and objects in every narrative scene (no geometric shapes)
- Painted storybook aesthetic (tropical magical-realism style)
- Fast implementation using existing proven pipeline
- Ken Burns motion provides cinematic feel

**What this doesn't provide:**
- Independent character motion (characters move with background as one scene)
- Continuous animation (static poses with camera motion)

**Why this tradeoff is acceptable:**
- Industry standard for digital illustrated storybooks (children's books, narrated stories)
- User explicitly needs "real objects" not "better animation of shapes"
- Ken Burns motion is established cinematic technique for still images
- Narrative text provides motion context ("The cat leaps...")

**Alternative approaches rejected:**
- Multi-layer sprites (Option C/D): Too complex, unreliable background removal
- LLM SVG (Option B): Limited to simple shapes, doesn't match painted aesthetic
- Original recommendation (backgrounds + text only): Doesn't solve geometric shapes problem — still has spinning squares on painted backgrounds

**Complementary approach (Phase 2):**
- Use Remotion with LLM SVG for abstract/diagrammatic scenes (math diagrams, charts, data viz)
- Keep both renderers, improve routing logic to select appropriate one per scene

---

**Next Action:** Trinity to implement intelligent scene routing in `scene_renderer.py` on branch `squad/narrative-scene-routing`
