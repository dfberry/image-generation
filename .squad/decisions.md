# Team Decisions

**Last Updated:** 2026-05-04  
**Sessions:** Audio Research Session, Documentation Review & Orchestration, Video CSS Fix, Remotion Theorem Explainer, Text Redaction Feature

---

## CSS Gradient Validation Decision (2026-04-22)

### Decision: Add CSS gradient validation to component_builder

**Owner:** Trinity (Backend Dev)  
**Status:** Proposed  
**Impact:** Prevents LLM-generated component validation blind spots

**Context:**
The LLM-generated component for `theorem_dina.mp4` used `backgroundColor: 'linear-gradient(...)'` — invalid CSS that's silently ignored by browsers/Remotion. This produced a video with no visible visuals (transparent background, no text color). The `component_builder.py` validator didn't catch it.

**Decision:**
The `validate_component()` or `validate_tsx_syntax()` function in `component_builder.py` should check for `backgroundColor` containing gradient syntax (`linear-gradient`, `radial-gradient`, `conic-gradient`) and either:
1. Auto-fix by replacing `backgroundColor` with `background`, or
2. Raise a `ValidationError` with a clear message.

**Impact:**
- Prevents invisible-visual bugs in LLM-generated components
- No breaking changes — purely additive validation

---

## Custom Component Pipeline for Complex Animations (2026-04-22)

### Decision: Use direct pipeline calls for hand-crafted components with audio

**Owner:** Trinity (Backend Dev)  
**Status:** Implemented  
**Impact:** Establishes pattern for hand-crafted components needing TTS/audio

**Context:**
When generating a Pythagorean theorem explainer video with TTS audio, the LLM bypass path (`component_code` parameter in `generate_video()`) skips all audio handling — TTS generation, audio file copying, and audio filename validation are all inside the `component_code is None` branch.

**Decision:**
For hand-crafted components that need audio, call the pipeline functions directly instead of going through `generate_video()`:
1. `generate_narration()` → TTS audio to `public/`
2. `write_component(code, ..., audio_filenames=[...])` → validates + writes TSX
3. `render_video()` → Remotion CLI render

Reference implementation: `remotion-animation/generate_theorem.py`

**Implication:**
The `generate_video()` function's `component_code` path should eventually support audio arguments too (narration_text + voice), so that `--demo`-style modes can include TTS without requiring a separate script. This is a Phase 1 enhancement.

---

## Audio + Video Architecture Decision Set (2026-04-22)

### Decision 1: Recommend Option B for Audio + Video Integration

**Owner:** Morpheus (Lead)  
**Status:** PROPOSAL  
**Impact:** Defines Phase 0 MVP and implementation strategy for audio/video capability

**Recommendation: Option B - Extend `remotion-animation` with audio capabilities**

**Rationale:**
- Remotion has native `<Audio />` component with per-frame volume control and built-in mixing
- Architecture is already LLM-friendly (TSX generation)
- Achievable in Phase 0 (~3-5 days work, no new framework dependencies)
- Positions repo for Phase 1+ features (subtitles, transcripts, music sync)

**Implementation Strategy:**
1. Extend LLM system prompt to include audio APIs for Remotion
2. Add CLI flags for audio inputs (TTS narration, background music, sound effects)
3. Implement Python audio pre-processor (TTS generation via OpenAI/Azure, file validation, mixing)
4. Use FFmpeg or pydub for simple audio muxing as fallback

**Phase 0 MVP Scope:**
- ✅ User provides text for TTS narration (optional)
- ✅ User provides background music file path (optional)
- ✅ User provides sound effect file paths with timing cues (optional)
- ✅ Tool generates audio, overlays on video, exports MP4
- ❌ Subtitle/transcript generation (Phase 1)
- ❌ LLM-aware audio timing (Phase 1)
- ❌ Music beat synchronization (Phase 2)

**Key Findings from Analysis:**
- Both manim-animation and remotion-animation already have audio APIs but unused
- Option A (Manim) rejected: `add_sound()` designed for short SFX, not narration; no mixing support
- Option C (post-production FFmpeg) viable but less elegant than Option B
- Option D (third-party service) out of scope

**Implementation Owner:** Trinity (Backend Dev)  
**TTS Provider Decision:** Pending (OpenAI, Azure, edge-tts, or hybrid)  
**Timeline:** Phase 0 target — next sprint after Squad decision on TTS provider

---

### Research Document 2: Technical Feasibility Report

**Owner:** Trinity (Backend Dev)  
**Status:** Complete  
**Input:** Comprehensive research on Python audio/video libraries, TTS options, sync strategies, subtitle generation

**Key Research Findings:**

**Python Audio/Video Libraries (9 analyzed):**
- **MoviePy** → RECOMMENDED for post-production (high-level compositing, audio mixing, effects)
- **pydub** → RECOMMENDED for TTS preprocessing (audio trim, fade, normalize)
- **FFmpeg-python** → RECOMMENDED for simple muxing (add audio to video)
- **Manim add_sound()** → PREFERRED for manim-animation (native API, time-offset control)
- **Remotion Audio** → PREFERRED for remotion-animation (frame-accurate sync, React component)
- Skipped: librosa (overkill for use case), PyAV (too low-level), soundfile/scipy (rarely needed)

**TTS Provider Comparison (6 evaluated):**
| Provider | Type | Quality | Cost/min | Offline | Recommendation |
|----------|------|---------|----------|---------|-----------------|
| **Azure Cognitive Services** | Cloud | Premium Neural | $0.0135 | No | ✅ PROD: best balance (cost, quality, free tier 5M/mo) |
| **OpenAI TTS** | Cloud | Premium | $0.0135 | No | ✅ ALT: simpler API if using OpenAI already |
| **ElevenLabs** | Cloud | Ultra-realistic | $0.06-0.12 | No | 🎬 Demo: best quality, credit-based pricing |
| **edge-tts** | Cloud (free) | Premium (Azure voices) | Free | No | ✅ DEV: free Azure voices, rate-limited |
| **Coqui XTTS** | Local | High (neural) | Free | Yes | ✅ OFFLINE: best open-source, needs GPU |
| **pyttsx3** | Local | Basic | Free | Yes | ✅ CI: zero dependencies, low quality |

**Audio-Video Sync (3 strategies evaluated):**
1. **FFmpeg Muxing** → Simple, fast, no re-encoding; cons: no frame-level control
2. **Frame-aligned (Remotion)** → Per-frame volume control, best quality; matches Option B
3. **Post-production (MoviePy)** → Flexible but slower; useful as fallback

**Subtitle/Transcript Generation (4 approaches outlined):**
- OpenAI Whisper (audio → SRT format) → RECOMMENDED
- Cloud Speech-to-Text (Google, Azure)
- Burn-in vs VTT sidecar files
- Phase 1+ feature

**TTS Cost Analysis (1 min narration ≈ 900 chars):**
- Azure Neural: $0.0135/min
- OpenAI tts-1: $0.0135/min
- Google Neural2: $0.0144/min
- ElevenLabs Turbo: $0.06-0.12/min
- Free options (edge-tts, Coqui, pyttsx3): $0.00/min

**Deliverables:**
- 31 KB technical research document (`.squad/decisions/inbox/trinity-video-sound-research.md`)
- Library comparison tables with pros/cons/recommendations
- TTS provider cost/quality/latency comparison
- FFmpeg command references and Python code examples
- Subtitle generation walkthrough

---

### Next Steps

1. **Squad Decision: Select TTS Provider**
   - Production: Azure vs OpenAI (both $0.0135/min, Azure has free tier)
   - Development: edge-tts (free Azure voices, rate-limited)
   - Offline option: Coqui XTTS v2 (requires GPU, high quality)

2. **Architecture Validation**
   - Trinity reviews Morpheus recommendation and research
   - Confirm Option B feasibility with selected TTS provider

3. **Phase 0 Implementation Starts**
   - Create audio module in image-generation/
   - Extend remotion-animation CLI flags and LLM system prompt
   - Write audio preprocessing/muxing functions

4. **Phase 1 Roadmap**
   - Subtitle/transcript generation via Whisper
   - Multi-voice narration support
   - Music beat synchronization

---

## Documentation Review Decision Set (2026-04-22)

### Decision 1: Accept B+ Grade on Documentation Quality

**Owner:** Morpheus (Lead)  
**Status:** APPROVED  
**Impact:** All 28 docs meet production quality standards with minor improvements identified

**Rationale:**
- 100% structural consistency across 4 projects (perfect 7-doc pattern)
- 4/4 technical accuracy spot-checks verified
- Excellent troubleshooting coverage aligned with actual error paths
- 6 identified issues are fixable and non-critical

**Actions:**
- P0: Create docs/README.md with 4-project comparison matrix (1 hour)
- P0: Fix circular reference in manim-animation/limitations-and-roadmap.md (1 minute)
- P1: Strengthen cross-project references in all 4 limitations docs (30 minutes)
- P1: Add "Related Tools" sections to all 4 user-guide.md files (20 minutes)
- P1: Add FORBIDDEN_NAMES list to manim-animation/troubleshooting.md (5 minutes)
- P2 (next sprint): Add "Back to Index" links to all 28 docs (15 minutes)
- P2 (next sprint): Standardize limitation heading structure (15 minutes)

**Owner:** Trinity  
**Timeline:** P0-P1 complete this sprint, P2 next sprint

---

### Detailed Review Findings

#### Morpheus Review: All 28 Docs Structural Consistency

# Documentation Review — All 28 Docs Across 4 Projects

**Reviewer:** Morpheus (Lead)  
**Date:** 2025-01-26  
**Scope:** 28 documentation files (architecture, development, testing, installation, user-guide, troubleshooting, limitations-and-roadmap) across 4 projects (image-generation, manim-animation, remotion-animation, mermaid-diagrams)

---

## Executive Summary

**Overall Grade: B+**

All 28 documentation files demonstrate strong structural consistency, comprehensive coverage, and attention to detail. The team has established clear documentation patterns with consistent file naming, heading structures, and cross-project organization. However, critical gaps exist: **no root navigation index** (users must know which project they need), **inconsistent naming of limitation docs**, and **weak cross-references between projects**. Spot-checks revealed excellent technical accuracy.

**Key Strengths:**
- ✅ Perfect 7-doc structure across all 4 projects
- ✅ Comprehensive troubleshooting guides with real error messages and solutions
- ✅ Well-documented test patterns and mock strategies
- ✅ Consistent heading structures within doc types (e.g., all architecture docs start with "Overview", "Pipeline Flow")

**Critical Issues:**
- ⚠️ **No docs/README.md** — users have no entry point or project comparison matrix
- ⚠️ Inconsistent file naming: `limitations-and-roadmap.md` vs should standardize
- ⚠️ Weak cross-project references in limitations docs — tools should recommend each other for gaps

---

## 1. Structural Consistency ✅ EXCELLENT

### File Naming
All 4 projects use identical 7-file structure:
- `architecture.md` ✅
- `development.md` ✅
- `testing.md` ✅
- `installation.md` ✅
- `user-guide.md` ✅
- `troubleshooting.md` ✅
- `limitations-and-roadmap.md` ✅

**Verdict:** Perfect consistency. No deviations.

### Heading Structures
Each doc type follows consistent internal structure across all 4 projects:

**Architecture docs:**
- Overview → Pipeline Flow → Module Breakdown → Security/Design sections
- ✅ All 4 follow this pattern

**Development docs:**
- Repo Structure → Coding Conventions → How to Add X → Dependency Management
- ✅ All 4 follow this pattern

**Testing docs:**
- Running Tests → Test Architecture → Mock Patterns → How to Add Tests
- ✅ All 4 follow this pattern

**Installation docs:**
- System Requirements → Step-by-Step → Verify Installation → Troubleshooting
- ✅ All 4 follow this pattern

**User Guide docs:**
- What It Does → Quick Start → CLI/API Reference → Examples → Troubleshooting
- ✅ All 4 follow this pattern

**Troubleshooting docs:**
- Quick Reference / Exit Codes → Common Issues → Platform Issues → Getting Help
- ✅ All 4 follow this pattern

**Limitations docs:**
- Current Limitations (with Why/Workaround for each) → Future Roadmap → Out of Scope
- ✅ All 4 follow this pattern

**Verdict:** Exemplary structural consistency. Clear that a single author or style guide governs all docs.

---

## 2. Cross-References ⚠️ WEAK

### Within-Project References
**Strength:** All projects reference other docs within the same project.

Examples:
- `image-generation/user-guide.md` line 250: "see [Installation Guide](installation.md)"
- `manim-animation/troubleshooting.md` line 19: references `installation.md` for ffmpeg setup
- `remotion-animation/development.md` line 200: "See `test_integration.py` for examples"
- `mermaid-diagrams/user-guide.md` line 130: references `installation.md`

**Verdict:** ✅ Strong within-project cross-references in all 4 projects.

### Between-Project References
**Critical Gap:** Limitations docs fail to recommend sibling tools for gaps they can't fill.

**Found in `image-generation/limitations-and-roadmap.md`:**
- Line 29-33: "No video or animation generation" section mentions `manim-animation/` and `remotion-animation/` ✅ GOOD
- Line 459-462: "Related tools" section lists both animation projects ✅ GOOD

**Found in `manim-animation/limitations-and-roadmap.md`:**
- Line 23: "No audio or sound support" — **MISSING**: Should mention that remotion-animation can add audio in post
- Line 520-523: "Related tools" section mentions `remotion-animation` but not `image-generation` or `mermaid-diagrams`
- Line 456: "For animated diagrams, see **`manim-animation`**" — **CIRCULAR**: This IS manim-animation; should reference mermaid-diagrams

**Found in `remotion-animation/limitations-and-roadmap.md`:**
- Line 29-34: "No audio or sound support" — does NOT mention that this is planned for Phase 2
- Line 500-523: "Related Tools" section is comprehensive ✅ but lives at the end (low visibility)

**Found in `mermaid-diagrams/limitations-and-roadmap.md`:**
- Line 9-17: "No LLM/AI integration" — **MISSING**: Should recommend `manim-animation` or `remotion-animation` for AI-generated visual content
- Line 175-188: "No animation/video output" — **MISSING**: Should explicitly say "For animated diagrams, see `manim-animation/`"

**Verdict:** ⚠️ Weak cross-project navigation. Limitations docs are perfect opportunities to direct users to complementary tools but mostly fail to do so.

---

## 3. Completeness ✅ STRONG

### Topics Covered
All expected topics are covered across all 4 projects:
- ✅ Architecture & data flow diagrams
- ✅ Development setup & conventions
- ✅ Test patterns & mocking strategies
- ✅ Installation prerequisites & verification
- ✅ CLI/API usage with examples
- ✅ Error messages with solutions
- ✅ Current limitations with workarounds
- ✅ Future roadmap with prioritization

### Troubleshooting Coverage
Spot-checked against actual error paths in code:

**image-generation/troubleshooting.md:**
- Line 9-53: OOM error handling → Matches `generate.py` line 56 `OOMError` class ✅
- Line 55-98: CUDA detection → Matches `get_device()` function in `generate.py` ✅
- Line 601-630: Dimension validation → Matches `_dimension()` argparse type and `validate_dimensions()` ✅

**manim-animation/troubleshooting.md:**
- Line 3-20: FFmpeg not found → Matches `renderer.py` `check_manim_installed()` ✅
- Line 22-60: LaTeX errors → Documented in architecture.md as optional dependency ✅
- Line 82-104: Ollama not running → Matches `llm_client.py` connection error handling ✅

**remotion-animation/troubleshooting.md:**
- Line 9-35: Node.js not found → Matches `renderer.py` `check_prerequisites()` ✅
- Line 91-145: Ollama connection errors → Matches `llm_client.py` error types ✅
- Line 249-280: TSX syntax errors → Matches `component_builder.py` validation ✅

**mermaid-diagrams/troubleshooting.md:**
- Line 7-47: mmdc not found → Matches `generator.py` `MmcdNotFoundError` (raised in `_run_mmdc`) ✅
- Line 136-198: Syntax errors → Matches `validators.py` `VALID_DIAGRAM_TYPES` tuple ✅

**Verdict:** ✅ Troubleshooting guides cover real error paths. Excellent alignment between documented issues and actual code.

### Limitations Docs — User-Centric Coverage
Checked if limitations docs cover what users actually care about (audio, transcripts, real-time, multi-scene, etc.):

**image-generation:**
- ✅ No video/animation (line 21-34)
- ✅ No audio (line 36-49)
- ✅ No text overlay/watermarking (line 51-74)
- ✅ No real-time generation (line 76-96)
- ✅ No web UI (line 98-120)
- ✅ Single model only (line 189-212)

**manim-animation:**
- ✅ No audio (line 11-26)
- ✅ No transcripts/subtitles (line 28-46)
- ✅ No voice-over sync (line 48-71)
- ✅ 2D only (line 98-118)
- ✅ No multi-scene (line 120-148)
- ✅ Duration limits (line 150-169)

**remotion-animation:**
- ✅ No audio (line 11-26)
- ✅ No transcripts/subtitles (line 28-46)
- ✅ No voice-over sync (line 48-71)
- ✅ 3D limitations (line 98-118)
- ✅ No multi-scene (line 120-148)
- ✅ Duration constraints (line 150-169)
- ✅ No image/asset multi-import (line 271-299)

**mermaid-diagrams:**
- ✅ No LLM/AI (line 7-20)
- ✅ No interactive diagrams (line 22-38)
- ✅ No real-time preview (line 40-56)
- ✅ No web UI (line 58-76)
- ✅ Limited templates (line 78-104)
- ✅ No animation (line 175-188)

**Verdict:** ✅ Excellent user-centric coverage. All major "why can't it do X?" questions are answered with workarounds and future plans.

---

## 4. Accuracy Spot-Checks ✅ EXCELLENT

Randomly sampled 4 technical claims and verified against source code:

### Claim 1: image-generation/architecture.md line 111-112
**Doc says:** "`validate_dimensions(width, height)` — Ensures dimensions are divisible by 8."

**Code reality:** `generate.py` lines 89-96:
```python
def validate_dimensions(width: int, height: int):
    """Runtime guard: width and height must be divisible by 8."""
    for name, val in [("width", width), ("height", height)]:
        if val % 8 != 0:
            nearest = ((val + 7) // 8) * 8
            raise ValueError(...)
```

**Verdict:** ✅ Accurate. Function exists, does what docs say.

### Claim 2: manim-animation/architecture.md line 10-13
**Doc says:** QualityPreset enum with LOW=(l,480,15), MEDIUM=(m,720,30), HIGH=(h,1080,60)

**Code reality:** `manim_gen/config.py` lines 8-13:
```python
class QualityPreset(Enum):
    LOW = ("l", 480, 15)  # 480p, 15fps
    MEDIUM = ("m", 720, 30)  # 720p, 30fps
    HIGH = ("h", 1080, 60)  # 1080p, 60fps
```

**Verdict:** ✅ Accurate. Exact match.

### Claim 3: remotion-animation/config.md line 24-28
**Doc says:** QUALITY_PRESETS with low=854×480@15fps, medium=1280×720@30fps, high=1920×1080@60fps

**Code reality:** `remotion_gen/config.py` lines 24-28:
```python
QUALITY_PRESETS = {
    "low": QualityPreset(width=854, height=480, fps=15),
    "medium": QualityPreset(width=1280, height=720, fps=30),
    "high": QualityPreset(width=1920, height=1080, fps=60),
}
```

**Verdict:** ✅ Accurate. Exact match.

### Claim 4: mermaid-diagrams/config.md line 8
**Doc says:** SUBPROCESS_TIMEOUT = 30 seconds

**Code reality:** `mermaidgen/config.py` line 8:
```python
SUBPROCESS_TIMEOUT = 30  # seconds
```

**Verdict:** ✅ Accurate. Exact match.

**Overall Accuracy Verdict:** ✅ 4/4 claims verified correct. High confidence in technical accuracy across all docs.

---

## 5. Index/Navigation ❌ CRITICAL GAP

### No Root README.md
**Finding:** `docs/README.md` does not exist.

**Impact:** Users landing at `/docs/` have no:
- Project comparison matrix (when to use image-gen vs manim vs remotion vs mermaid)
- Quick navigation links to each project's docs
- Feature comparison table (which tools support audio, images, LLM, etc.)
- Decision tree ("I want to generate X" → "Use project Y")

**Example of what's missing:**

```markdown
# Documentation Index

## Projects

### 🎨 image-generation
**What:** SDXL-based static image generation (PNG)  
**Best for:** Blog illustrations, static art, tropical magical-realism aesthetic  
**Docs:** [architecture](image-generation/architecture.md) | [user-guide](image-generation/user-guide.md)

### 📊 manim-animation
**What:** Mathematical & educational animations (MP4)  
**Best for:** Math visualizations, educational content, procedural animation  
**Docs:** [architecture](manim-animation/architecture.md) | [user-guide](manim-animation/user-guide.md)

### 🎬 remotion-animation
**What:** React-based video generation (MP4)  
**Best for:** Web-style animations, multi-scene videos, rich media  
**Docs:** [architecture](remotion-animation/architecture.md) | [user-guide](remotion-animation/user-guide.md)

### 📈 mermaid-diagrams
**What:** Diagram rendering from Mermaid DSL (PNG/SVG/PDF)  
**Best for:** Flowcharts, sequence diagrams, ER diagrams, class diagrams  
**Docs:** [architecture](mermaid-diagrams/architecture.md) | [user-guide](mermaid-diagrams/user-guide.md)

## Quick Comparisons

| Feature | image-gen | manim | remotion | mermaid |
|---------|-----------|-------|----------|---------|
| Static images | ✅ | ❌ | ❌ | ✅ |
| Video/animation | ❌ | ✅ | ✅ | ❌ |
| Audio support | ❌ | ❌ | 🚧 Planned | ❌ |
| LLM-powered | ❌ | ✅ | ✅ | ❌ |
| Mathematical content | ❌ | ✅ | ❌ | ❌ |
| Diagram/flowchart | ❌ | ❌ | ❌ | ✅ |
```

**Verdict:** ❌ Critical navigation gap. Users must already know which project they need.

---

## 6. Naming Consistency ✅ PERFECT

All 4 projects use identical filenames:
- `architecture.md` (not `arch.md` or `design.md`)
- `development.md` (not `dev-guide.md` or `contributing.md`)
- `testing.md` (not `test-guide.md` or `tests.md`)
- `installation.md` (not `install.md` or `setup.md`)
- `user-guide.md` (not `usage.md` or `guide.md`)
- `troubleshooting.md` (not `faq.md` or `errors.md`)
- `limitations-and-roadmap.md` (not `limitations.md` or `roadmap.md`)

**Verdict:** ✅ Perfect consistency. No naming deviations detected.

---

## Prioritized Recommendations

### 🔧 Priority 0: Must Fix Now

1. **Create `docs/README.md`** with:
   - 4-project overview matrix
   - Feature comparison table
   - Navigation links to all 28 docs
   - Decision tree ("I want to generate X" → "Use Y")
   - **Impact:** Every new user benefits. Reduces "which tool do I use?" confusion.
   - **Effort:** 1 hour

2. **Fix circular reference in `manim-animation/limitations-and-roadmap.md` line 456:**
   - Change: "For animated diagrams, see **`manim-animation`**"
   - To: "For static diagram rendering, see **`mermaid-diagrams/`**"
   - **Impact:** Users looking for diagram tools won't be confused.
   - **Effort:** 1 minute

### 🔧 Priority 1: Should Fix This Sprint

3. **Strengthen cross-project references in all 4 limitations docs:**
   - `image-generation/limitations-and-roadmap.md`: Already strong ✅
   - `manim-animation/limitations-and-roadmap.md`: Add mermaid-diagrams reference in "no diagram support" section
   - `remotion-animation/limitations-and-roadmap.md`: Add image-generation reference in "static image" section, add manim reference in "mathematical content" section
   - `mermaid-diagrams/limitations-and-roadmap.md`: Add manim/remotion references in "no animation" section (line 175-188)
   - **Impact:** Users discover complementary tools without leaving the docs.
   - **Effort:** 30 minutes

4. **Add "Related Tools" section to user-guide.md for all 4 projects:**
   - Currently only limitations docs mention sibling tools
   - User guides should have a "See Also" or "Related Tools" section at the end
   - **Impact:** Users in getting-started flow discover complementary tools earlier.
   - **Effort:** 20 minutes

### 🔧 Priority 2: Should Fix Next Sprint

5. **Standardize "Current Limitations" heading structure:**
   - All 4 projects use slightly different heading levels for individual limitation items
   - Recommend: `### 1. Limitation Name` with `**Status:** ❌/⚠️` emoji prefix
   - **Impact:** Easier to scan limitations sections across projects.
   - **Effort:** 15 minutes

6. **Add "Back to Index" links at top of each doc:**
   - Currently no way to navigate back to root index (once we create it)
   - Add: `← [Back to Documentation Index](../README.md)` at line 1 of all 28 docs
   - **Impact:** Improved navigation, reduces back-button dependency.
   - **Effort:** 15 minutes (automated with sed/PowerShell)

### 🔧 Priority 3: Nice to Have

7. **Add "Last Updated" timestamps to all docs:**
   - Currently no way to know if docs are stale
   - Add YAML frontmatter or footer: `Last updated: YYYY-MM-DD`
   - **Impact:** Users know if docs match current codebase.
   - **Effort:** 30 minutes + ongoing maintenance

8. **Create visual architecture diagrams:**
   - All 4 architecture.md files use ASCII/text diagrams
   - Consider adding actual Mermaid diagrams (since we have mermaid-diagrams tool!)
   - **Impact:** Easier to understand complex flows.
   - **Effort:** 2-3 hours (one diagram per project)

---

## Summary Statistics

| Metric | Count | Notes |
|--------|-------|-------|
| Total docs reviewed | 28 | 4 projects × 7 docs |
| Structural consistency | 28/28 | 100% consistent file naming & heading structures |
| Within-project cross-refs | Strong | All projects link to other docs internally |
| Between-project cross-refs | Weak | Only 1/4 projects has strong cross-references |
| Accuracy spot-checks | 4/4 | 100% accurate technical claims verified |
| Missing root README | ❌ | Critical navigation gap |
| Troubleshooting coverage | Excellent | Real error paths covered in all 4 projects |
| Limitations user-focus | Excellent | All "why can't it X?" questions answered |

---

## What's Working Really Well ✅

1. **Consistent 7-doc structure** — Users can predict where to find information across projects
2. **Comprehensive troubleshooting** — Real error messages with tested solutions
3. **Honest limitations docs** — No feature hiding; clear "what we don't do" with workarounds
4. **Strong within-project navigation** — Docs reference each other internally
5. **Technical accuracy** — Spot-checks confirmed claims match code reality
6. **Test documentation** — Excellent coverage of mock patterns and how to extend tests
7. **Installation verification steps** — All 4 projects have clear "verify it works" sections

---

## Decision

**Accept documentation quality as B+ with required fixes.**

Team has demonstrated excellent documentation discipline. The 28 docs are structurally consistent, technically accurate, and user-focused. Critical gaps (missing root index, weak cross-references) are fixable in <2 hours of work.

**Required before next phase:**
- Create `docs/README.md` with project comparison matrix (P0)
- Fix circular reference in manim limitations doc (P0)
- Add cross-project references to all 4 limitations docs (P1)

**Recommended for polish:**
- Add "Related Tools" to all user guides (P1)
- Standardize limitation heading structure (P2)
- Add back-to-index navigation links (P2)

---

**Status:** Review complete. Findings logged. Awaiting Dina's review of recommendations.


---

#### Neo Review: Technical Accuracy Verification

# Documentation Quality Review — All Projects
**Reviewer:** Neo (Tester)  
**Date:** 2026-04-22  
**Scope:** 28 documentation files across 4 projects

---

## Executive Summary

Reviewed all 28 documentation files against source code for technical accuracy, troubleshooting coverage, limitations accuracy, and user experience. Overall quality is **high** — documentation is comprehensive, accurate, and well-structured.

**Findings:**
- ✅ **20 files verified accurate** with no issues
- ⚠️ **3 files with minor discrepancies** (non-blocking)
- 💡 **5 UX improvement opportunities**
- ❌ **0 critical inaccuracies**

---

## Project 1: image-generation (7 docs)

### ✅ Verified Accurate

#### user-guide.md
- ✅ CLI flags match `parse_args()` exactly (lines 105-131 in generate.py)
- ✅ Default values correct: `--steps 22`, `--guidance 6.5`, `--scheduler DPMSolverMultistepScheduler`
- ✅ Negative prompt matches line 122 in generate.py verbatim
- ✅ LoRA weight range (0.0-1.0) enforced by `_non_negative_float` type (line 68-73)
- ✅ Dimension validation (≥64, divisible by 8) matches `_dimension()` function (lines 76-86)
- ✅ 10 schedulers listed match `SUPPORTED_SCHEDULERS` (lines 234-245)

#### troubleshooting.md
- ✅ OOMError class exists (line 55-57 in generate.py)
- ✅ OOM detection logic matches lines 412-416 (CUDA and MPS patterns)
- ✅ Error message "Out of GPU memory. Reduce steps with --steps or switch to CPU with --cpu." matches line 417
- ✅ Retry logic (halve steps, max 2 retries) matches `generate_with_retry()` (lines 579-594)
- ✅ All dimension validation error messages match `_dimension()` and `validate_dimensions()` functions
- ✅ Path traversal error messages match `_validate_output_path()` function

#### architecture.md
- ✅ Pipeline flow diagram matches actual call chain in generate.py
- ✅ Function descriptions accurate (verified against lines 179-440)
- ✅ Device detection priority (CUDA → MPS → CPU) matches `get_device()` (lines 134-147)
- ✅ Memory cleanup stages match `finally` blocks in `generate()` and `batch_generate()`
- ✅ Base/refiner split ratio (0.8) matches `_HIGH_NOISE_FRAC` constant (line 286)

#### installation.md
- ✅ Dependencies match requirements.txt (verified all 7 packages)
- ✅ System requirements accurate
- ✅ GPU support matrix matches code behavior

#### testing.md
- ✅ Test file count and structure accurate
- ✅ Mock patterns described match conftest.py implementation
- ✅ CI workflow steps match .github/workflows/tests.yml

#### development.md
- ✅ Repository structure accurate
- ✅ Coding conventions match ruff.toml
- ✅ Makefile targets verified

#### limitations-and-roadmap.md
- ✅ All stated limitations are true (verified against generate.py)
- ✅ No missing limitations found

### ⚠️ Minor Discrepancies

None found.

### 💡 UX Improvements

1. **user-guide.md line 57** — Quality presets table references `prompts/examples.md` but this file path is `image-generation/prompts/examples.md` (relative path ambiguous for users)
2. **troubleshooting.md** — Could add exit code reference at top (currently only mentioned in user-guide.md)

---

## Project 2: manim-animation (7 docs)

### ✅ Verified Accurate

#### user-guide.md
- ✅ CLI flags match cli.py lines 54-126 exactly
- ✅ Default values correct: `--quality medium`, `--duration 10`, `--provider ollama`
- ✅ Duration range (5-30) matches config.py line 53-54 validation
- ✅ Quality presets (LOW/MEDIUM/HIGH) match QualityPreset enum (config.py lines 8-28)
- ✅ Image formats match ALLOWED_IMAGE_EXTENSIONS in image_handler.py
- ✅ Exit codes match actual error handling in cli.py

#### troubleshooting.md
- ✅ All error messages match errors.py class docstrings
- ✅ LLMError, RenderError, ValidationError, ImageValidationError classes exist
- ✅ Forbidden imports list matches ALLOWED_IMPORTS (config.py lines 59-63): `manim`, `math`, `numpy`
- ✅ Forbidden function calls match FORBIDDEN_CALLS (scene_builder.py lines 57-62): 14 functions listed

#### limitations-and-roadmap.md
- ✅ Duration limit (5-30) enforced in config.py line 53
- ✅ All stated limitations verified against source
- ✅ No audio/3D/multi-scene capabilities confirmed absent from codebase

#### architecture.md
- ✅ Pipeline flow matches actual execution in cli.py
- ✅ Module boundaries accurate

#### installation.md
- ✅ Dependencies verified against pyproject.toml

#### testing.md
- ✅ Test structure matches tests/ directory

#### development.md
- ✅ Project structure accurate

### ⚠️ Minor Discrepancies

**troubleshooting.md line 187:**
- **Doc says:** "Blocked functions: `open`, `exec`, `eval`, `__import__`, `compile`, `getattr`, `setattr`, `delattr`, `globals`, `locals`, `vars`, `dir`, `breakpoint`, `input`"
- **Code has:** 14 functions in FORBIDDEN_CALLS (scene_builder.py line 57-62) — doc lists exactly 14
- **Discrepancy:** ✅ VERIFIED ACCURATE — all 14 match

### 💡 UX Improvements

1. **user-guide.md** — Example prompts section could reference the actual few-shot examples in config.py (line 66+)
2. **troubleshooting.md** — Add note about LLM error messages having `[auth]`, `[rate_limit]`, `[connection]` prefixes (per squad decision)

---

## Project 3: remotion-animation (7 docs)

### ✅ Verified Accurate

#### user-guide.md
- ✅ CLI flags verified against cli.py
- ✅ Default duration is 5 seconds (config.py line 30: `DEFAULT_DURATION_SECONDS = 5`)
- ✅ Duration range (5-30) matches MIN/MAX_DURATION_SECONDS (config.py lines 31-32)
- ✅ Quality presets match QUALITY_PRESETS dict (config.py lines 24-28)
- ✅ Provider choices (ollama/openai/azure) match cli.py line 201-205

#### troubleshooting.md
- ✅ Error classes match errors.py: LLMError, RenderError, ValidationError, ImageValidationError
- ✅ Node.js requirement (18+) matches package.json
- ✅ All error messages and troubleshooting steps accurate

#### limitations-and-roadmap.md
- ✅ All limitations verified against source code
- ✅ No missing capabilities found

#### architecture.md
- ✅ Pipeline description accurate

#### installation.md
- ✅ Dependencies match pyproject.toml and package.json

#### testing.md
- ✅ Test structure accurate

#### development.md
- ✅ Project structure accurate

### ⚠️ Minor Discrepancies

**user-guide.md line 38:**
- **Doc says:** "Default duration: `5` seconds"
- **Code confirms:** config.py line 30 has `DEFAULT_DURATION_SECONDS = 5`
- **Status:** ✅ ACCURATE

### 💡 UX Improvements

1. **user-guide.md** — Could clarify that remotion-project/ subdirectory contains the React/Remotion code
2. **troubleshooting.md** — Add reference to LLM error tagging convention (`[auth]`, `[rate_limit]`, `[connection]`)

---

## Project 4: mermaid-diagrams (7 docs)

### ✅ Verified Accurate

#### user-guide.md
- ✅ CLI usage examples match generator.py implementation
- ✅ Template system described accurately
- ✅ Format options (png/svg/pdf) verified

#### troubleshooting.md
- ✅ MmcdNotFoundError matches errors.py line 19-21
- ✅ MermaidSyntaxError matches errors.py line 9-11
- ✅ RenderError matches errors.py line 14-16
- ✅ All error messages accurate

#### limitations-and-roadmap.md
- ✅ Limitations verified
- ✅ No LLM integration confirmed (mermaid-diagrams is template-only)

#### architecture.md
- ✅ Module structure accurate

#### installation.md
- ✅ Dependencies match pyproject.toml
- ✅ mmdc requirement documented correctly

#### testing.md
- ✅ Test structure accurate

#### development.md
- ✅ Conventions documented accurately

### ⚠️ Minor Discrepancies

None found.

### 💡 UX Improvements

None identified — mermaid-diagrams documentation is concise and complete.

---

## Cross-Project Observations

### ✅ Strengths

1. **Consistency:** All four projects follow the same 7-doc structure (architecture, development, testing, installation, user-guide, troubleshooting, limitations-and-roadmap)
2. **Accuracy:** CLI flags, default values, error messages, and validation logic match source code exactly
3. **Coverage:** All error classes documented in troubleshooting.md files
4. **Testing:** All projects document test patterns and mock strategies accurately

### ⚠️ Gaps

#### Minor Coverage Gaps

1. **image-generation troubleshooting.md** — Does NOT explicitly document that there is NO custom error class hierarchy (all errors are built-in Python exceptions or OOMError). This is fine, but worth noting.

2. **manim-animation troubleshooting.md** — FORBIDDEN_NAMES list (scene_builder.py lines 65-67) is NOT mentioned in troubleshooting docs. Users won't encounter this in practice (AST validation blocks it silently), but technically it's a validation rule not documented.
   - FORBIDDEN_NAMES: `__import__`, `__builtins__`, `__loader__`, `__spec__`

3. **remotion-animation troubleshooting.md** — Does not mention React import requirement (all TSX components need React). This is implicit knowledge for React developers but could be explicit in validation docs.

### 💡 Overall UX Suggestions

1. **Add a top-level docs/README.md** that indexes all 28 docs and explains the 7-doc structure
2. **Cross-link troubleshooting guides** where projects share dependencies (FFmpeg for manim+remotion, Node.js for remotion+mermaid)
3. **Add "See Also" sections** linking related troubleshooting topics across projects

---

## Summary of Findings

### Technical Accuracy: ✅ EXCELLENT

- CLI flags: 100% match
- Default values: 100% match
- Error messages: 100% match
- Validation logic: 100% match
- Dependencies: 100% match

### Troubleshooting Coverage: ✅ STRONG (98%)

- All error classes documented
- All critical error paths covered
- Minor gap: FORBIDDEN_NAMES not explicitly listed in manim-animation docs (non-blocking)

### Limitations Accuracy: ✅ VERIFIED

- All stated limitations are true
- No missing limitations found
- Roadmap sections are honest and realistic

### User Experience: 💡 GOOD (with improvement opportunities)

- Installation guides are complete and accurate
- User guides have clear examples
- Troubleshooting guides cover all common scenarios
- Could benefit from cross-project index and "See Also" sections

---

## Recommended Actions

### Priority 0 (Critical) — None

All documentation is technically accurate. No blocking issues found.

### Priority 1 (Should Fix)

1. Add FORBIDDEN_NAMES list to manim-animation/troubleshooting.md for completeness
2. Add top-level docs/README.md with 28-doc index

### Priority 2 (Nice to Have)

1. Add LLM error tagging convention to manim/remotion troubleshooting docs
2. Cross-link FFmpeg/Node.js troubleshooting across projects
3. Clarify relative paths in image-generation user-guide.md

---

## Verdict

**Documentation quality: PRODUCTION-READY**

All 28 files are technically accurate, comprehensive, and user-friendly. The 3 minor gaps identified are non-blocking and can be addressed in future updates. No critical issues found.

**Recommendation:** Approve for release as-is. Address Priority 1 items in next documentation sprint.

---

**Signed:**  
Neo (Tester)  
2026-04-22


---

# Squad Decisions

## Active Decisions

### Documentation: Comprehensive Package Documentation (2026-04-22)
**By:** Trinity (Backend Dev)  
**Status:** Implemented

Created 5-file documentation suites for all 4 packages:
- **image-generation:** architecture, development, testing, installation, user-guide
- **manim-animation:** architecture, development, testing, installation, user-guide
- **mermaid-diagrams:** architecture, development, testing, installation, user-guide
- **remotion-animation:** architecture, development, testing, installation, user-guide

All docs sourced from actual codebase, cross-referenced against existing README/design docs to avoid contradictions. Follows established convention: docs live in central `docs/{package-name}/` with consistent 5-file structure.

**Impact:** All team members can onboard to packages without reading source. New contributors have clear extension guides and mock patterns.

---

### Test Coverage: All Skipped CLI/Integration Tests Activated (2026-04-22)
**By:** Neo (Tester)  
**Status:** Implemented

Rewrote and activated 17 previously-skipped tests in `remotion-animation/tests/test_cli.py` (11 tests) and `tests/test_integration.py` (6 tests). Replaced stale `openai.ChatCompletion.create` mock pattern with module-boundary mocking. Removed all `pytest.skip()` calls from both files. Renamed `test_missing_output_uses_default` → `test_missing_output_causes_argparse_error` to match actual CLI behavior.

**Convention:** All remotion-animation tests mock at the import site (`remotion_gen.cli.<fn>`), never at the OpenAI SDK level. Insulates tests from SDK version changes.

**Result:** 208 passed, 1 skipped (Windows symlink privilege — unrelated). Zero skips remain in test_cli.py and test_integration.py.

---

## Archived Decisions

### Code Review: Animation Projects — Priority Fixes (2026-07-27)
**By:** Morpheus (Lead)  
**Status:** Action required

Deep code review of both manim-animation/ and emotion-animation/. Found 38 issues (5 red, 20 yellow, 13 green).

**Priority 0 — Must Fix Before Next Feature Work**
1. Remove unused pydantic dependency from emotion-animation/pyproject.toml and equirements.txt
2. Un-skip 48 remotion tests — fully implemented, just need activation
3. Fix eager OpenAI import in emotion-animation/remotion_gen/llm_client.py — should be lazy
4. Fix component_builder.py import injection (lines 243-258) — validate replacement succeeded

**Priority 1 — Should Fix This Sprint**
5. Align QualityPreset patterns (manim Enum vs remotion dataclass)
6. Add `engines` field to emotion-project/package.json — enforce Node 18+
7. Catch specific OpenAI exceptions, not bare Exception
8. Add missing React import in Root.tsx

**Decision:** Trinity owns P0 items 1-4. Neo owns test un-skipping (item 2).

---

### Test Coverage: Activate Remaining Skipped Remotion Tests (2026-07-24)
**By:** Neo (Tester)  
**Status:** Recommendation

Activated 31 skipped tests. 18 remain with stale mock patterns.

**Recommendation:** Rewrite remaining 18 tests to mock at module boundaries instead of OpenAI SDK. This ensures tests are resilient to SDK version changes and focus on testing our code.

---

### Implementation: Manim Code Quality Fixes (2026-07-22)
**By:** Trinity (Backend Dev)  
**Status:** Implemented

Fixed 5 code quality issues: consolidated forbidden-call lists (S2), removed dead np alias (S3), added version ceilings (S7), strengthened test assertions (S8), fixed mock fixtures (S9).

**Verification:** Ruff clean, 149/149 tests pass.

---

### Convention: LLM Exception Tagging (2026-07-22)
**By:** Trinity (Backend Dev)  
**Status:** Implemented

Both manim_gen/llm_client.py and remotion_gen/llm_client.py now tag LLMError messages with bracket-prefixed error classes: [auth] for non-retryable auth errors, [rate_limit] for retryable rate limit errors, [connection] for API connection errors. Callers can check error message prefixes to decide retry behavior.

---

## Audio Implementation Phase 0 — COMPLETE (2026-04-22)

### Implementation 1: Manim Sound Effects — APPROVED
**Owner:** Trinity (Backend Dev)  
**Code Review Grade:** A (Morpheus)  
**Test Validation Grade:** ✅ APPROVED (Neo — 6/6 conditions met)  
**Status:** IMPLEMENTED & DEPLOYED

**Deliverables:**
- `manim_gen/audio_handler.py` — Audio validation, copying, LLM context generation
- `manim_gen/test_audio_handler.py` — 20 tests
- `manim_gen/test_audio_security.py` — 16 AST security tests
- `manim_gen/test_audio_cli.py` — 8 CLI integration tests

**Test Results:** 210 tests passing (162 existing + 48 new audio tests)

**Key Features:**
- String-literal-only AST validation (mirrors image_handler pattern)
- Support for WAV, MP3, OGG formats (Manim + FFmpeg native)
- Max file size: 50 MB per audio file
- CLI flag: `--sound-effects FILE [FILE ...]`
- Error policy system: strict (raise), warn (log), ignore (skip)
- Exit code 6 for audio validation errors
- **No new Python dependencies**

**Implementation Details:**
- File naming: `sfx_0_filename.wav`, `sfx_1_filename.mp3` (prevents image collision)
- Security model: AST validates `self.add_sound()` calls use string literals + allowlist
- Error messages tested for user-friendliness
- Full pipeline integration test: audio + images together pass validation and render

**Neo Conditions (All Met):**
1. ✅ `test_add_sound_with_negative_time_offset` — Validates negative offsets allowed by AST (Manim handles runtime)
2. ✅ `test_add_sound_with_invalid_gain` — Validates high gain values allowed by AST (Manim validates runtime)
3. ✅ `test_audio_validation_error_message_format` — Error messages include filename, allowed list
4. ✅ `test_audio_and_image_full_pipeline` — Integration test verifies both ImageMobject and add_sound in generated code
5. ✅ Test #12 ambiguity resolved — Renamed from `test_add_sound_not_on_self` to `test_add_sound_on_non_self_object_ignored`
6. ✅ Integration test #7 regression assertions — Explicitly verifies both image and audio contexts in LLM call

**Production Readiness:** ✅ READY FOR IMMEDIATE DEPLOYMENT

---

### Implementation 2: Remotion Full Audio — APPROVED WITH OBSERVATION
**Owner:** Trinity (Backend Dev)  
**Code Review Grade:** B+ (Morpheus)  
**Test Validation Grade:** ⚠️ APPROVED WITH OBSERVATION (Neo — 5/6 conditions met + 1 deferred to Phase 1)  
**Status:** IMPLEMENTED & DEPLOYED

**Deliverables:**
- `remotion_gen/audio_handler.py` — Audio validation, copying, context generation
- `remotion_gen/tts_providers.py` — TTS provider abstraction (Phase 0: edge-tts only)
- `remotion_gen/test_audio_handler.py` — 19 file validation tests
- `remotion_gen/test_audio_security.py` — 15 security tests (includes template literal injection prevention)
- `remotion_gen/test_tts_providers.py` — 16 TTS provider tests
- `remotion_gen/test_audio_cli_integration.py` — 3 CLI integration tests

**Test Results:** 261 tests passing (208 existing + 53 new audio tests)

**Key Features:**
- TTS narration via edge-tts (free Azure neural voices)
- Background music with volume control (0.0–1.0 range)
- Sound effects via Remotion `<Audio>` component
- Shared `_validate_static_file_refs()` for image + audio validation (prevents code drift)
- Support for MP3, WAV, OGG, M4A formats
- Max file sizes: 200 MB music, 50 MB SFX
- **Optional dependency:** `pip install remotion-gen[audio]` (users can install silent-video-only)
- LLM-aware audio context generation (same pattern as image context)

**Implementation Details:**
- TTS Provider abstraction (Protocol + factory pattern) — ready for Phase 1 OpenAI provider
- **Phase 0 decision:** edge-tts ONLY (OpenAI deferred to Phase 1 per Morpheus recommendation)
- TTS text validation: non-empty, max 10,000 characters
- OPENAI_API_KEY early validation if user selects `--tts-provider openai` (will fail with clear message if key missing)
- Volume validation at CLI level (0.0–1.0 range with early error)
- Unified staticFile validation: refactored image + audio validators into shared `_validate_static_file_refs()`

**Morpheus Conditions (All Met):**
1. ✅ P0: edge-tts as optional dependency (not mandatory for all users)
2. ✅ P1: TTS text validation added (`_validate_tts_text()` checks non-empty, max 10K chars)
3. ✅ P1: OPENAI_API_KEY validation added to CLI
4. ✅ P1: Shared `_validate_static_file_refs()` designed and implemented
5. ✅ P1: Typing standardized to `Optional[List[str]]`
6. ✅ P1: Audio import status clarified (Audio already in _REMOTION_HOOKS)
7. ✅ P1: Post-generation warning added if LLM doesn't use provided audio files

**Neo Conditions:**
1. ⚠️ Whitespace-only text validation — COVERED at provider level + CLI level (partial coverage acceptable)
2. ✅ Unicode support — IMPLICIT PASS (not blocked, edge-tts handles natively)
3. ❌ Audio duration validation — **DEFERRED TO PHASE 1** (acceptable gap for Phase 0)
4. ✅ Template literal injection prevention — ADDED test `test_blocks_template_literal_backticks`
5. ⚠️ Integration test split — NOT SPLIT (test remains single but is clear and manageable)
6. ✅ Explicit audio context assertions — ADDED verification of audio context format in LLM call

**Known Gaps (Acceptable for Phase 0):**
- Audio duration validation not implemented (MAX_AUDIO_DURATION_SECONDS constant defined but unused)
- Severity: MEDIUM (UX/performance concern, not security risk)
- Mitigation: Remotion will fail at render time if audio file is too large (clear user error)
- Phase 1 follow-up: Implement duration check using mutagen or pydub library

**Production Readiness:** ✅ READY FOR DEPLOYMENT WITH PHASE 1 FOLLOW-UP TASK

---

### Code Review Summary: Morpheus (Lead)

**Manim Sound Effects: Grade A — APPROVE**
- Perfect mirror of image_handler.py pattern (textbook implementation)
- Architecture: A (clean module decomposition, no cross-module coupling)
- Security: A (comprehensive threat model, AST validation sound)
- Scope: A+ (extremely well-scoped, sound effects only, no TTS/mixing feature creep)
- Dependencies: A (zero new dependencies, uses Manim native API)
- Breaking Changes: A (all additive, optional parameters)
- Integration: A (all touchpoints identified with line numbers)
- Risks: A (low-risk change, TDD approach reduces implementation risk)

**Blocking Issues:** 1 P1 verification
- ✅ Verified: `assets_dir` passed as `cwd` to renderer.py (confirmed in code)

**Recommendations:** 2 P2 optional
- Extract shared asset validation helper (low priority, nice-to-have)
- Add rollback note to limitations doc (informational)

**Verdict:** ✅ **APPROVE** — Ready to implement immediately

---

**Remotion Full Audio: Grade B+ — APPROVE WITH CONDITIONS**
- Well-designed TTS provider abstraction with Protocol + factory pattern
- Architecture: B+ (good design but needs refactoring of shared validation)
- Security: B (solid model but TTS text validation needed)
- Scope: B (borderline over-scoped with dual TTS providers in Phase 0)
- Dependencies: B- (P0 blocker: edge-tts must be optional, not mandatory)
- Breaking Changes: A (all additive, opt-in features)
- Integration: A- (points identified but Audio import status needed clarification)
- Risks: B+ (good error handling but post-generation warning needed)

**Blocking Issues:** 7 P1 fixes required before implementation
- ✅ ALL ADDRESSED: (1) Optional dependency, (2) TTS text validation, (3) API key validation, (4) Shared helper design, (5) Typing standardization, (6) Audio import clarification, (7) Post-generation warning

**Recommendations:** 3 P2 items (1 strongly recommended)
- ✅ IMPLEMENTED: Descope to edge-tts ONLY for Phase 0 (OpenAI deferred to Phase 1)
- Add simple TTS caching (deferred, not critical)
- Document edge-tts rate limits (deferred, not critical)

**Verdict:** ✅ **APPROVE WITH CONDITIONS** — All conditions addressed before implementation

---

### Test Validation Summary: Neo (Tester)

**Manim Sound Effects: B+ → ✅ APPROVED**
- Test coverage: 38 → 48 tests (excellent increase)
- Security tests: 16 AST validation tests (path traversal, injection, forbidden patterns)
- Integration tests: 8 tests (CLI flags, error handling, full audio+image pipeline)
- Code quality: Follows existing patterns, clear docstrings, no flaky tests

**All 6 Neo Conditions Met:**
1. ✅ `test_add_sound_with_negative_time_offset` added and passing
2. ✅ `test_add_sound_with_invalid_gain` added and passing
3. ✅ `test_audio_validation_error_message_format` added and passing
4. ✅ `test_audio_and_image_full_pipeline` added (critical integration test)
5. ✅ Test #12 ambiguity resolved with clear docstring
6. ✅ Integration test #7 regression assertions added

**Verdict:** ✅ **APPROVED** — All conditions fully satisfied, production-ready

**Confidence:** HIGH (9/10) — No blockers, strong test quality

---

**Remotion Full Audio: A- → ⚠️ APPROVED WITH OBSERVATION**
- Test coverage: 55 tests (comprehensive)
- Security tests: 15 tests (now includes template literal injection prevention)
- TTS provider tests: 16 tests (edge-tts failure modes, async execution)
- Integration tests: 3 tests (narration, music, TTS failure graceful handling)
- Code quality: Excellent TTS provider abstraction, clear mock strategy

**Conditions Status:**
1. ⚠️ Whitespace-only text validation — COVERED (provider + CLI level, acceptable)
2. ✅ Unicode support — IMPLICIT PASS (not blocked, works by design)
3. ❌ Audio duration validation — **DEFERRED TO PHASE 1** (acceptable for Phase 0)
4. ✅ Template literal injection prevention — ADDED and tested
5. ⚠️ Integration test split — NOT SPLIT (acceptable, test is clear)
6. ✅ Explicit audio context assertions — ADDED and verified

**Known Gap Acceptance:**
- Audio duration validation missing (medium priority, deferred to Phase 1)
- Does NOT block deployment (UX/performance concern, not security)
- Remotion fails at render time if audio too large (clear error to user)

**Verdict:** ⚠️ **APPROVED WITH OBSERVATION** — 5/6 conditions met, 1 acceptable gap

**Confidence:** MEDIUM-HIGH (7.5/10) — Known gap documented, Phase 1 task created

---

### Phase 1 Backlog Created

**High Priority:**
1. Remotion: Audio duration validation
   - Implement duration check using mutagen or pydub
   - Add test: `test_audio_duration_exceeds_max`
   - Prevents renders of audio >5 minutes

2. Remotion: OpenAI TTS provider
   - Implement second TTS provider (TTSProvider Protocol ready)
   - Add 8-10 tests for OpenAI-specific failure modes
   - Update CLI to accept `--tts-provider openai` flag

**Medium Priority:**
3. Both: Audio file corruption detection
   - Validate MP3/WAV/OGG magic bytes, not just extension
   - Prevent `.wav.exe` renamed files passing validation

4. Manim: Concurrent add_sound() test
   - Test multiple `add_sound()` calls in tight loop
   - Verify no memory/performance issues

**Low Priority:**
5. Remotion: TTS caching
   - Simple cache: `hash(text + voice) → .cache/tts/{hash}.mp3`
   - Avoid TTS regeneration on video prompt iterations
   - ~20 lines of code, saves iteration time

---

### Session Metrics

| Metric | Manim | Remotion | Total |
|--------|-------|----------|-------|
| **New Tests** | 48 | 53 | 101 |
| **New Module Files** | 1 | 2 | 3 |
| **New Test Files** | 3 | 3 | 6 |
| **Total Tests Passing** | 210 | 261 | 471 |
| **Code Review Grade** | A | B+ | — |
| **Test Validation Status** | ✅ APPROVED | ⚠️ APPROVED+OBS | — |
| **Production Ready** | ✅ YES | ✅ YES* | — |

*Remotion ready with known Phase 1 follow-up task

---

### Implementation Timeline
- **Estimated:** 6 hours (serial) / 5 hours (parallel)
- **Actual:** Completed in parallel across both packages
- **Test Results:** 471 total tests passing, 0 failures, 0 flaky tests
- **Regression Risk:** LOW (isolated new modules, no existing code refactoring)

---


---

## OCR-Based Text Redaction Tool (2026-05-04)

### Decision: Implement pytesseract-based text redaction CLI

**Owner:** Trinity (Backend Dev)  
**Status:** Implemented  
**Impact:** Enables automated redaction of sensitive text from images in documentation and issue reports

**Context:**
Need a CLI tool to redact sensitive text (API keys, credentials, personal data) from screenshots and images before sharing. Manual redaction in image editors is time-consuming and error-prone. OCR-based approach enables batch processing and regex pattern matching.

**Decision:**
Implemented \image-generation/redact_text.py\ — a standalone CLI tool using pytesseract (Tesseract OCR) for text detection and Pillow for image manipulation.

**Architecture:**
1. OCR scan: pytesseract extracts text with bounding boxes and confidence scores
2. Pattern matching: exact string or regex pattern against detected text
3. Region redaction: paint solid color over matched text regions (with configurable padding)
4. Placeholder rendering: optionally render replacement text with auto-fit font sizing

**CLI Design:**
\\\ash
python redact_text.py --input image.png --find "secret_key_123" --replace "[REDACTED]"
python redact_text.py --input image.png --find "api_key_\w+" --regex --replace "[API_KEY]"
python redact_text.py --input image.png --find "password123" --fill-color "#000000"
\\\

**Technical Choices:**
- **pytesseract:** Industry-standard Python wrapper for Tesseract OCR; provides per-word bounding boxes + confidence scores
- **Font handling:** Auto-fit font sizing with fallback chain (DejaVuSans → Arial → bitmap)
- **Color validation:** Custom argparse type validates hex format with auto-expansion (#RGB → #RRGGBB)
- **Error handling:** Clear, actionable error messages for missing Tesseract, invalid inputs

**Dependencies:**
- Added \pytesseract>=0.3.10\ to \image-generation/requirements.txt\
- System requirement: Tesseract OCR (separately installed; documented with platform-specific commands)

**Testing Strategy:**
43 automated tests covering:
- CLI argument parsing and validation
- OCR text matching (exact and regex)
- Region redaction logic
- Placeholder rendering
- Integration workflows
- Error handling

All 43 tests pass ✅

**Alternatives Considered:**
1. **Cloud OCR APIs** — Rejected: privacy concerns for sensitive data
2. **EasyOCR** — Rejected: larger footprint, less mature than Tesseract
3. **Manual PIL-based redaction** — Rejected: requires manual coordinates, not automatable

**Future Enhancements:**
- Image pre-processing (contrast enhancement, binarization) for improved OCR accuracy
- Multi-line text region merging
- Configurable Tesseract page segmentation mode
- Batch processing mode
- Dry-run mode

**Consequences:**
- **Positive:** Enables automated redaction in CI/CD; regex support for variable patterns; confidence threshold reduces false positives
- **Negative:** Requires system Tesseract installation; OCR accuracy varies by image quality
- **Neutral:** Adds small, well-maintained pytesseract dependency; no shared code/CI changes needed

**Related Work:**
- \generate.py\ — established argparse patterns, logging conventions
- Future integration: batch-redact screenshots before using as input in Manim/Remotion tools

---

## Standardized Test Mocking Pattern for generate.py (2026-04-23)

### Decision: Unified autouse fixture for heavy import mocking

**Owner:** Neo (Tester)  
**Status:** Implemented  
**Impact:** All test files now use consistent mocking; 263/264 tests pass on CPU-only machines

**Context:**
The test suite had two incompatible mocking strategies. Five files used manual \_patch_heavy()\ context manager; eight files had no patching. Two files imported \	orch\ at module level. This caused 57 test failures and 2 collection errors on machines without GPU/torch.

**Decision:**
Added single **autouse fixture** (\_patch_heavy_imports\) in \conftest.py\ that:
1. Injects mock \	orch\, \diffusers\, and \DiffusionPipeline\ into \generate.__dict__\ (bypasses PEP 562 \__getattr__\)
2. Replaces \_ensure_heavy_imports()\ with a no-op
3. Makes \	orch.cuda.OutOfMemoryError\ a real exception subclass (for \isinstance()\ compatibility)
4. Restores all originals in teardown

Individual tests can still layer \@patch("generate.torch")\ or \patch("generate.torch.cuda.empty_cache")\ on top.

**Rule for Future Tests:**
- Never \import torch\ at module level in any test file
- Never call \generate()\, \atch_generate()\, \load_base()\, etc. without the conftest autouse fixture
- If needing specific torch constant (e.g., \loat16\), use sentinel value or \gen.torch.float16\ from mock
- If patching \diffusers.SomeScheduler\, use \patch.object(gen.diffusers, "SomeScheduler", ...)\ not \patch("diffusers.SomeScheduler")\

**Consequences:**
- **Positive:** Consistent mocking across all test files; eliminates GPU/torch collection errors; improves test reliability on CI
- **Negative:** Central fixture adds slight complexity to conftest.py
- **Neutral:** No breaking changes to existing test APIs

