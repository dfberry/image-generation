← [Back to Documentation Index](../README.md)

# Limitations & Roadmap

This document outlines what **remotion-gen** does NOT currently support and planned improvements for future phases.

## Current Limitations

This is a **Phase 0 Proof of Concept** focused on core functionality. Many features are intentionally excluded to keep scope manageable.

---

### Audio & Sound

**Status:** ❌ Not supported

- **No audio tracks** — videos are silent (video-only)
- **No background music** — cannot attach audio files
- **No sound effects** — animations are mute
- **No ambient soundscapes** — no environmental audio

**Why:** Audio requires additional LLM context, Remotion audio API complexity, and sync challenges. MVP prioritizes visual animation generation.

**Use case workaround:** Export the MP4 and add audio in post-production using:
- FFmpeg: `ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac output.mp4`
- Adobe Premiere, DaVinci Resolve, or CapCut

**Roadmap:** Phase 2 — audio track support with LLM-aware timing (see [Audio Integration](#audio-integration) below).

---

### Transcripts & Subtitles

**Status:** ❌ Not supported

- **No subtitle files** (.srt, .vtt, .ass)
- **No caption generation** from video content
- **No accessibility text tracks** (TTML, WebVTT)
- **No transcript export** after rendering

**Why:** Subtitles require either manual text input or speech-to-text integration. Current scope is video-only.

**Use case workaround:** Use a separate tool to add captions:
- FFmpeg + subtitle file: `ffmpeg -i video.mp4 -vf subtitles=captions.srt output.mp4`
- YouTube auto-captions
- Adobe Premiere or CapCut

**Roadmap:** Phase 2 — caption support with optional speech-to-text (see [Subtitle Generation](#subtitle-generation) below).

---

### Voice-Over & Narration Sync

**Status:** ❌ Not supported

- **No audio narration** in generated videos
- **No voice-over timing** — can't sync animations to speech
- **No speech-to-animation** — narration doesn't drive animation timing
- **No audio-reactive keyframes** — animation duration is fixed, not responsive to audio length

**Why:** This requires:
1. Speech input (user-provided or generated via TTS)
2. LLM understanding of audio duration and sync points
3. Animation keyframe generation tied to phonemes/words
4. Complex timing logic

**Use case workaround:**
1. Generate the video silently
2. Record/generate narration separately (see [Text-to-Speech](#text-to-speech-integration) below)
3. Manually sync timing in post-production

**Roadmap:** Phase 3 — voice-over sync with speech timing analysis (see [Voice-Over Sync](#voice-over-synchronization) below).

---

### Text-to-Speech Integration

**Status:** ❌ Not supported

- **No TTS API integration** (no Azure Cognitive Services, Google Cloud Speech, etc.)
- **Cannot generate narration** from prompt text
- **No natural language to speech** pipeline
- **No voice selection** or speaker customization

**Why:** Adds dependency on TTS APIs, adds complexity, and requires sync with animation timing (not yet supported).

**Use case workaround:**
1. Generate narration manually with:
   - Google Text-to-Speech (free, high quality)
   - Azure Cognitive Services
   - ElevenLabs or similar
   - Record yourself
2. Add it to the video in post-production (see above)

**Roadmap:** Phase 2 — optional TTS integration (see [Text-to-Speech Integration](#text-to-speech-integration) below).

---

### 3D & WebGL Animations

**Status:** ❌ Not supported

- **2D animations only** — all output is flat
- **No Three.js integration** — no 3D rendering
- **No WebGL** — no GPU-accelerated 3D graphics
- **No 3D transforms** — `rotateZ` only (CSS 2D transforms work, but no 3D perspective)
- **No stereoscopic output** — no VR/3D glasses support

**Why:** Adding 3D would require:
1. Three.js or Babylon.js integration into Remotion
2. 3D scene description language (complex LLM prompting)
3. Significant performance overhead

**Use case workaround:** Use dedicated 3D animation tools:
- Blender + Remoteion composition (advanced)
- Cinema 4D
- Adobe After Effects with 3D plugins

**Roadmap:** Phase 3+ — optional Three.js composition support (see [3D Animation Support](#3d-animation-support) below).

---

### Multi-Scene Sequences

**Status:** ❌ Not supported

- **Single-scene compositions only** — one component per video
- **No scene transitions** — cut, dissolve, wipe, etc.
- **No sequential animations** — can't compose multiple shots
- **No storyboard support** — LLM generates one "shot," not a sequence

**Why:** Multi-scene requires:
1. Structured LLM output (describe each scene separately)
2. Transition/timing choreography
3. Composition scene registry updates

**Use case workaround:**
1. Generate single-scene videos separately:
   ```bash
   remotion-gen --prompt "Opening title" --output scene1.mp4
   remotion-gen --prompt "Body animation" --output scene2.mp4
   remotion-gen --prompt "Closing credits" --output scene3.mp4
   ```
2. Concatenate with FFmpeg:
   ```bash
   ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
   ```
3. Add transitions in post-production

**Roadmap:** Phase 2+ — multi-scene LLM support (see [Multi-Scene Composition](#multi-scene-composition) below).

---

### Duration Constraints

**Status:** ⚠️ Strict 5–30 second limit enforced

- **Minimum duration:** 5 seconds (Phase 0 convention)
- **Maximum duration:** 30 seconds (memory/compile time constraint)
- **No long-form content** — cannot generate feature-length videos
- **Framerate limited by duration** — high-fps preset × 30s max = ~1800 frames max

**Why:**
1. Shorter videos are safer for MVP (less chance of memory exhaustion, compilation timeout)
2. LLM token budget is finite (~2000 tokens for TSX code)
3. Rendering longer videos takes exponentially longer
4. Testing & iteration faster with short clips

**Use case workaround:** Concatenate multiple short videos (see Multi-Scene above).

**Roadmap:** Phase 1+ — support up to 120 seconds (see [Duration Extension](#duration-extension) below).

---

### Audio-Reactive Animations

**Status:** ❌ Not supported

- **No audio input analysis** — can't detect beat, tempo, frequency
- **No sound visualization** — no equalizer, waveform, or spectrum animations
- **No reactive keyframes** — animation timing is fixed, not responsive to audio input

**Why:** Requires:
1. Audio analysis (frequency decomposition, beat detection)
2. Real-time audio stream integration with Remotion
3. Keyframe generation from audio features

**Use case workaround:**
1. Manually extract audio features (music BPM, key moments)
2. Write custom Remotion component using audio features (not LLM-generated)
3. Render and validate

**Roadmap:** Phase 3+ — audio analysis & reactive animation (see [Audio-Reactive Animations](#audio-reactive-animations) below).

---

### Real-Time Preview

**Status:** ❌ Not supported

- **No preview mode** — cannot watch animation before rendering
- **No Remotion player** — must render full video to see output
- **No scrubbing/seeking** — can't jump through frames quickly
- **No live editing** — change and see updates instantly

**Why:**
1. MVP prioritizes fast iteration via CLI + file inspection
2. Preview requires UI, complex state management, live recompilation
3. Phase 0 targets developers, not designers (CLI is fine)

**Use case workaround:**
1. Use `--debug` flag to inspect generated TSX before rendering
2. Render to MP4 (takes ~30–60 seconds)
3. Watch in video player
4. Iterate prompt and re-render

**Roadmap:** Phase 2+ — web UI with Remotion player (see [Web UI](#web-ui) below).

---

### Web UI

**Status:** ❌ Not supported

- **CLI only** — no web interface, desktop app, or TUI
- **No drag-and-drop** — prompts must be text-only
- **No visual editing** — can't click on objects to edit them
- **No template gallery** — must know what to ask for

**Why:**
1. MVP targets developers who are comfortable with CLIs
2. Web UI requires frontend + backend + deployment
3. Phase 0 focused on core algorithm

**Use case workaround:** Wrap the Python API in your own web app:
```python
from remotion_gen.cli import generate_video
result = generate_video(prompt="...", output="video.mp4")
```

**Roadmap:** Phase 2+ — optional web UI (see [Web UI](#web-ui) below).

---

### Template Library

**Status:** ⚠️ Hardcoded few-shot examples only

- **No template system** — LLM doesn't have named, selectable templates
- **Few-shot examples hardcoded** in system prompt (~2 examples in the prompt)
- **No user-contributed templates** — cannot share or reuse custom templates
- **No template marketplace** — cannot browse/search templates

**Why:**
1. Manageable for MVP (templates live in code, not database)
2. LLM context window is limited (~4k tokens)
3. Template versioning & validation would add complexity

**Use case workaround:**
1. Craft detailed prompts describing desired animation
2. Save successful prompts in a local file:
   ```bash
   # prompts.txt
   A blue circle rotating 360 degrees in 5 seconds
   Colorful squares bouncing around
   Text fading in and out
   ```
3. Re-use prompts by copying from this file

**Roadmap:** Phase 1+ — template library system (see [Template System](#template-library-system) below).

---

### Image/Asset Import in Generated Scenes

**Status:** ⚠️ Limited support

**What works:**
- Single image via `--image` flag
- Image is copied to `public/` and injected into generated component
- LLM can use `staticFile()` to reference the image

**What doesn't work:**
- **Multiple images** — only one image per video
- **SVG animation** — cannot animate SVG paths or attributes
- **Lottie import** — no Lottie JSON animation support
- **Sprite sheets** — cannot slice and animate sprite maps
- **Dynamic asset loading** — all assets must be provided upfront
- **Font files** — cannot use custom fonts (system fonts only)

**Why:**
1. Image support is new (Phase 0.1 addition)
2. Multiple assets require complex LLM prompting and validation
3. SVG/Lottie require specialized rendering logic

**Use case workaround:**
1. For SVG: convert to PNG/WebP first, then use `--image`
2. For Lottie: render Lottie to MP4 separately, concatenate with FFmpeg
3. For multiple images: manually edit generated `GeneratedScene.tsx` post-render

**Roadmap:** Phase 1+ — multi-asset support (see [Asset Management](#multi-asset-support) below).

---

### Export Formats

**Status:** ⚠️ MP4 only

- **MP4 output only** (H.264 codec, AAC audio)
- **No GIF export** — cannot generate animated GIFs
- **No WebM** — no VP9/VP8 support
- **No HLS/DASH** — no streaming manifest support
- **No GIF with transparent background** (PNG sequence → GIF not supported)

**Why:**
1. MP4 is universal, efficient, and widely supported
2. GIF/WebM require additional ffmpeg flags and post-processing
3. Streaming formats require playlist generation

**Use case workaround:**
1. Use FFmpeg to convert MP4 → GIF:
   ```bash
   ffmpeg -i video.mp4 -vf "fps=10,scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" output.gif
   ```
2. Use FFmpeg to convert MP4 → WebM:
   ```bash
   ffmpeg -i video.mp4 -c:v libvpx-vp9 -b:v 1M output.webm
   ```

**Roadmap:** Phase 1+ — format options (see [Export Formats](#export-formats) below).

---

### Lottie & SVG Animation Import

**Status:** ❌ Not supported

- **No Lottie JSON import** — cannot use After Effects-exported animations
- **No SVG import** — cannot import vector graphics
- **No SVG path animation** — no morphing or path drawing
- **No dynamic SVG generation** — LLM cannot generate SVG code

**Why:**
1. Lottie requires React Lottie library integration
2. SVG rendering in React requires specialized setup
3. LLM would need to understand SVG syntax & Remotion integration
4. Increases complexity and dependency count

**Use case workaround:**
1. **Lottie:** Convert Lottie JSON to MP4 using `rive-app` or `lottie2gif` CLI tool, then concatenate
2. **SVG:** Rasterize SVG to PNG (ImageMagick `convert`) and use `--image`

**Roadmap:** Phase 2+ — Lottie & SVG support (see [Lottie & SVG Animation Import](#lottie--svg-animation-import) below).

---

### Error Handling & Resilience

**Status:** ⚠️ Happy path focus — basic error handling only

- **Limited retry logic** — LLM self-correction retries twice, then fails
- **No fallback strategies** — if LLM fails, no automatic workarounds
- **No graceful degradation** — validation errors are hard failures
- **Minimal logging** — errors are terse, debugging requires `--debug` flag
- **No checkpoint/resume** — if render fails halfway, must restart

**Why:**
1. MVP targets developers comfortable with CLIs
2. Advanced error handling adds complexity
3. Most errors are user-fixable (bad prompt, missing deps)

**Use case workaround:**
1. Use `--debug` to inspect intermediate outputs
2. Fix issues manually (edit TSX, check dependencies)
3. Re-run with adjusted prompt

**Roadmap:** Phase 1+ — enhanced error handling (see [Error Recovery](#error-recovery) below).

---

## Future Roadmap

### Phase 1 (Q2 2025)

#### Duration Extension
- Increase max duration from 30s to 120s
- Add streaming framerate options (24fps)
- Optimize compilation & memory for longer videos
- **Impact:** Enables longer narrative content, cinematic sequences

#### Template Library System
- Named templates: `--template bounce-squares`, `--template text-fade`
- User-contributed templates (JSON schema)
- Template composition: combine templates
- Version management
- **Impact:** Faster iteration, reusable patterns, community contributions

#### Multi-Asset Support
- Multiple images per video
- Font file support
- Asset inventory tracking
- **Impact:** Richer visual content, custom branding

#### Export Formats
- GIF output option
- WebM support
- MP4 preset options (codec, bitrate)
- **Impact:** Broader platform compatibility (Twitter, Discord GIFs)

#### Error Recovery
- Enhanced LLM retry with error context
- Graceful degradation (fallback animations if LLM fails)
- Detailed error messages & solutions
- **Impact:** Better user experience, fewer manual fixes needed

---

### Phase 2 (Q3–Q4 2025)

#### Text-to-Speech Integration
- Optional TTS provider (Azure Cognitive Services, Google Cloud)
- Voice selection, language support
- LLM-aware TTS duration estimation
- **Impact:** Voice-over narration capability

#### Subtitle Generation
- Auto-generate .srt/.vtt files from LLM descriptions
- Optional speech-to-text for user-provided narration
- Accessibility metadata
- **Impact:** Accessibility, cross-platform caption support

#### Multi-Scene Composition
- LLM generates scene descriptions (Title → Body → Closing)
- Automatic scene stitching with transitions
- Storyboard preview
- **Impact:** Narrative-driven content, feature-length videos

#### Web UI
- React-based dashboard
- Prompt builder with autocomplete
- Live preview (Remotion player)
- History & favorites
- **Impact:** Broader audience (designers, non-developers)

#### Lottie & SVG Animation Import
- Lottie JSON → React component conversion
- SVG path animation support
- JSON schema for custom SVG animations
- **Impact:** Integration with After Effects, design tools

---

### Phase 3 (2026+)

#### Audio Integration
- Background music from audio file
- Sound effect insertion at keyframes
- Audio mixing & mastering
- **Impact:** Full multimedia support

#### Voice-Over Synchronization
- Speech timing analysis (phoneme-level)
- Animation keyframe sync to narration
- Lip-sync for text animations
- **Impact:** Professional voice-over videos

#### Audio-Reactive Animations
- Audio beat detection
- Frequency-based keyframe generation
- Real-time audio stream integration
- Equalizer & waveform animations
- **Impact:** Music video, visualization content

#### 3D Animation Support
- Three.js integration
- 3D scene description language
- Camera control & perspective
- Lighting & materials
- **Impact:** Complex visual effects, 3D motion graphics

#### Performance Optimization
- Caching & memoization
- Parallel rendering
- GPU acceleration options
- Compile-time code generation optimization
- **Impact:** 10–50x faster rendering

---

## Out of Scope (Likely Never)

The following are considered **out of scope** for remotion-gen and will likely remain unsupported:

- **Real-time collaboration** — multi-user editing (too complex for this tool)
- **Version control/branching** — animation history management (out of MVP scope)
- **AI upscaling** — increasing MP4 resolution post-render (out of scope)
- **Interactive/branching videos** — conditional animation paths (requires UI)
- **Streaming input** — real-time event-driven animation (not a batch tool)
- **Desktop app/native UI** — web UI is enough
- **Monetization/licensing** — open-source, community-driven
- **Self-hosted deployment** — remains CLI-based, not SaaS

---

## Feedback & Contributions

We welcome feedback on these limitations and roadmap items:

1. **GitHub Issues:** Open an issue with the feature request tag
2. **Discussions:** Start a discussion in the `image-generation` repo
3. **Pull Requests:** Contribute implementations for planned features
4. **Squad System:** If you're part of the team, propose decisions in `.squad/decisions/`

---

## Related Tools in This Repository

This repository contains complementary tools for different media generation needs:

- **`image-generation/`** — For static image generation using SDXL (blog illustrations)
- **`manim-animation/`** — For mathematical animations (Manim procedurally-generated content)
- **`mermaid-diagrams/`** — For rendering static diagrams (flowcharts, ER diagrams, sequences)

Each tool serves a different purpose. Combine them for comprehensive multimedia generation workflows.

---

## Summary

| Feature | Status | Phase |
|---------|--------|-------|
| Audio/Sound | ❌ Not supported | Phase 2+ |
| Subtitles/Captions | ❌ Not supported | Phase 2 |
| Voice-Over Sync | ❌ Not supported | Phase 3 |
| Text-to-Speech | ❌ Not supported | Phase 2 |
| 3D Animations | ❌ Not supported | Phase 3+ |
| Multi-Scene | ❌ Not supported | Phase 2 |
| Duration (5–30s) | ⚠️ Limited | Phase 1 (→120s) |
| Real-Time Preview | ❌ Not supported | Phase 2 |
| Web UI | ❌ Not supported | Phase 2 |
| Template System | ⚠️ Hardcoded | Phase 1 |
| Multi-Asset | ⚠️ Limited | Phase 1 |
| Export Formats | ⚠️ MP4 only | Phase 1 |
| Lottie/SVG | ❌ Not supported | Phase 2+ |
| Audio-Reactive | ❌ Not supported | Phase 3 |
| Error Handling | ⚠️ Basic | Phase 1 |

