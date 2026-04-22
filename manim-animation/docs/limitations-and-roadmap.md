# Limitations and Roadmap

This document outlines what Manim Animation Generator **does NOT** do (Phase 0 scope), and future opportunities for expansion.

---

## Current Limitations (Phase 0)

Manim Animation Generator is a proof-of-concept focused on fast iteration and simple animations. These limitations are intentional and define the current scope.

### No Audio/Sound Support

**Limitation**: Animations are **silent**. No background music, narration, or sound effects.

**What doesn't work**:
- Adding background music or ambient sound to animations
- Audio narration or voice-over
- Text-to-speech integration
- Sound effect triggers tied to animation events
- Audio-visual synchronization

**Why**: Sound support adds significant complexity:
- Requires audio library (librosa, pydub, etc.)
- Manim would need audio processing pipeline
- Synchronization between animation timing and audio timing is non-trivial
- Licensing/attribution for sound effects
- Would bloat the Phase 0 scope

**Workaround**:
- Generate the animation video
- Add audio separately in video editing software (ffmpeg, Adobe Premiere, DaVinci Resolve, iMovie, etc.)
- Example: `ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output.mp4`

**Future Opportunity**:
- Integrate with audio libraries (librosa for analysis, pydub for mixing)
- Support audio tracks and narration alignment
- Implement beat detection to sync animations to music
- Add audio effects timeline

---

### No Transcript/Subtitle Generation

**Limitation**: No automatic generation of subtitle files (`.srt`, `.vtt`) or caption tracks. Animations have no text accessibility layer.

**What doesn't work**:
- Generating `.srt` or `.vtt` subtitle files to accompany videos
- Automatic accessibility captions
- Transcript files describing the animation sequence
- Multi-language subtitle variants

**Why**: Requires:
- Speech-to-text if narration is involved (but we don't support narration)
- Manual scene-to-caption mapping logic
- Standardized caption format generation
- Translation services for multilingual subtitles

**Workaround**:
- Manually create subtitle files using tools like Subtitle Edit or VEED.io
- If you add narration via separate audio, use a transcription service (Whisper, Google Cloud Speech-to-Text)

**Future Opportunity**:
- Integrate speech-to-text on audio tracks (if audio support is added)
- Auto-generate `.srt` files from animation timeline
- Support multiple language subtitles with translation API
- Accessibility-first caption generation with detailed descriptions

---

### No Voice-Over Synchronization

**Limitation**: **Cannot sync animation timing to speech or narration**. Animations play at their own pace.

**What doesn't work**:
- Pausing animations to wait for specific words in narration
- Highlighting parts of the scene based on what's being spoken
- Adjusting animation speed to match voice-over pacing
- Automatic timing alignment between speech and visuals

**Why**: Requires:
- Speech-to-text analysis to detect timing of spoken phrases
- Real-time or pre-computed animation state map
- Complex orchestration between audio playback and Manim timing

**Workaround**:
- Generate animation at a fixed pace
- Generate audio separately
- Use video editing tools to manually adjust timing and alignment
- Or adjust your prompts to create animations at the expected narration speed

**Future Opportunity**:
- Implement speech-aware animation scheduling
- Parse narration timing and adjust scene animations accordingly
- Build a "animation choreographer" that takes a script and auto-times animations
- Integration with text-to-speech for deterministic timing

---

### 2D Only — No 3D or Camera Work

**Limitation**: **Animations are strictly 2D**. No 3D objects, perspective cameras, or camera movements.

**What doesn't work**:
- 3D cubes, spheres, or complex 3D shapes
- Rotating objects in 3D space (only 2D rotation in the plane)
- Camera panning, zooming, or 3D viewpoint changes
- 3D coordinate systems or 3D graphing
- Three.js integration or WebGL rendering

**Why**:
- 3D Manim requires `manimgl` (legacy ManimGL), not Manim Community Edition
- 3D rendering is much slower
- 3D prompt generation is harder for LLMs (more syntax, more spatial reasoning)
- Current scope focuses on educational 2D math/CS animations

**Workaround**:
- Use purely 2D prompts (circles, squares, lines, 2D graphs)
- For 3D visualization needs, use separate 3D tools (Blender, Cesium.js, Three.js)

**Future Opportunity**:
- Support for Manim 3D module (requires separate 3D LLM few-shot examples)
- 3D camera path generation ("camera moves from left to right")
- Integration with 3D rendering engines (Three.js for web, Blender for export)
- 3D graphing and mathematical surfaces

---

### Single Scene Only — No Multi-Scene Compositions

**Limitation**: **One animation scene per video**. Cannot compose multiple scenes, transitions between scenes, or scene sequencing.

**What doesn't work**:
- Creating a video with Scene A, then Scene B, then Scene C
- Scene transitions (fade, wipe, dissolve between scenes)
- Reusing scenes or looping scenes
- Scene branching or conditional rendering
- Shot lists or storyboarding multiple scenes

**Why**:
- Current architecture renders a single `GeneratedScene` class
- Multiple scenes require orchestration logic (scene timing, transitions)
- LLM prompts would become more complex
- Adds significant complexity to the renderer

**Workaround**:
- Create your animation in a single scene with all elements
- Generate multiple animations separately and combine them in video editing software
- Use Manim's `MovingCameraScene` or timeline techniques within a single scene

**Future Opportunity**:
- Support scene sequencing: `[Scene1(duration=5), Transition(), Scene2(duration=5)]`
- Built-in transition animations (CrossFade, Wipe, etc.)
- Scene composition pipeline for multi-part educational content
- Automatic timing and synchronization of multi-scene videos

---

### 5-30 Second Duration Limit

**Limitation**: **Enforced duration range is 5-30 seconds**. Cannot create longer or shorter videos.

**What doesn't work**:
- Animations shorter than 5 seconds
- Animations longer than 30 seconds
- Long-form educational content (tutorials, lectures)
- Extended procedural animations

**Why**:
- **5 second minimum**: Manim has rendering overhead; animations need meaningful runtime
- **30 second maximum**: LLM prompt design assumes shorter, focused scenes; longer content is harder to generate correctly
- Prevents runaway render times (30s+ renderings can take 10-15 minutes)
- Keeps the scope focused on bite-sized educational content

**Workaround**:
- Break longer content into 5-30 second chunks
- Combine multiple generated videos in post-production
- Use `--duration 5` for snappy animations, `--duration 30` for comprehensive explanations

**Future Opportunity**:
- Extend max duration to 60-120 seconds (with tuned LLM prompts)
- Long-form "chapter-based" content with automatic scene breaking
- Adaptive duration based on animation complexity
- Streaming/progressive rendering for very long videos

---

### No Audio-Reactive Animations

**Limitation**: **Animations cannot respond to or visualize audio**. Cannot create audio waveform visualizations or sound-reactive effects.

**What doesn't work**:
- Animating shapes that pulse/move with music beats
- Audio waveform or frequency spectrum visualization
- Equalizer-style animations tied to audio levels
- Sound-reactive particle systems or effects
- VJ/live-performance style visualizations

**Why**: Requires:
- Audio input processing (librosa, scipy for FFT analysis)
- Real-time or pre-computed audio features (beats, frequencies, energy)
- Mapping audio features to animation parameters
- Complex parameter synchronization

**Workaround**:
- Use dedicated audio visualization tools (Shadertoy, VVVV, Max/MSP, Processing, p5.js)
- Or generate a static animation, add audio separately, and sync manually

**Future Opportunity**:
- Integrate audio analysis libraries (librosa, essentia)
- Accept audio input and auto-generate reactive animation code
- Beat detection and beat-aligned animation keyframes
- Frequency-based shape morphing and parameter modulation
- Export audio-reactive animations for VJ/live performance use

---

### No Real-Time Preview

**Limitation**: **Cannot preview animations before full render**. Must render the entire video to see the result.

**What doesn't work**:
- Live/interactive scene editor
- Real-time preview of animation as you adjust parameters
- Scrubbing through the timeline
- Quick feedback loops while iterating

**Why**:
- Manim doesn't offer streaming/progressive rendering
- Full render is the only way to see the final output
- Real-time preview would require significant architecture changes

**Workaround**:
- Use `--debug` to save generated code and manually inspect
- Test with `--quality low` first (faster render for preview), then `--quality high` for final
- Adjust prompts iteratively based on the final rendered output

**Future Opportunity**:
- Build a web-based animator with drag-and-drop scene editor
- Integrate with Jupyter notebooks for interactive editing
- Implement lightweight preview mode (lower resolution, keyframe-only rendering)
- Add a scene code debugger/validator before rendering

---

### No Web UI — CLI Only

**Limitation**: Tool is **CLI-only**. No graphical user interface, no web dashboard, no desktop app.

**What doesn't work**:
- Clicking buttons in a browser to generate animations
- Drag-and-drop interface for scene building
- Visual prompt builder or form-based configuration
- Real-time progress tracking in a dashboard

**Why**:
- CLI is simpler to deploy and maintain
- Aligns with current developer/power-user audience
- Web UI would require frontend framework (React, Vue), backend services, deployment

**Workaround**:
- Use CLI directly from terminal
- Wrap CLI in your own web service (Python Flask, FastAPI, etc.)
- Use command-line UI tools (Typer, Click for enhanced CLI)

**Future Opportunity**:
- Build a web UI wrapper (Flask/Django backend, React/Vue frontend)
- Mobile app for prompt entry (iOS/Android)
- Jupyter notebook integration for interactive authoring
- Slack bot or Discord bot for on-demand generation
- IDE plugin (VSCode, JetBrains) for scene editing

---

### No Template Library — Hardcoded Few-Shot Examples

**Limitation**: **No reusable template library**. Animations are generated from scratch each time; no pre-built patterns or templates for common animations (graphs, org charts, timelines, etc.).

**What doesn't work**:
- Selecting a template like "timeline animation" or "bar chart"
- Reusing and customizing pre-built animation patterns
- Template marketplace or community library
- Parameterized animation templates

**Why**:
- Few-shot examples are embedded in source code (config.py)
- Would require a template storage system (database, files, or API)
- Template selection/parametrization adds UX complexity

**Workaround**:
- Craft detailed prompts describing what you want
- Store working prompts in your own file and reuse them
- Use `--image` flag to pass context (images, diagrams) that guide generation

**Future Opportunity**:
- Build a template registry (JSON/YAML files, or cloud API)
- Parameterized templates: "timeline with N events", "bar chart of X dataset"
- Community-contributed templates (GitHub, npm-style registry)
- Template DSL for describing reusable animation patterns
- One-click template customization web interface

---

### Happy Path Focus — Limited Error Recovery

**Limitation**: **Limited error recovery and retry logic**. If the LLM generates invalid code or a render fails, there's no automatic retry or correction.

**What doesn't work**:
- Automatic retry on LLM failures (rate limit, timeout, bad generation)
- Automatic code correction and re-generation
- Fallback prompts or alternative generation strategies
- Intelligent error recovery

**Why**:
- Adding retry logic and fallback strategies increases complexity
- Current focus is on the happy path (user provides good prompt → LLM generates good code → Manim renders successfully)
- Error handling is basic (fail fast with clear error messages)

**Workaround**:
- Read error messages carefully and fix the issue manually
- Rephrase your prompt based on the error
- Use `--debug` to inspect generated code
- Try a different LLM model

**Future Opportunity**:
- Implement exponential backoff retry on transient failures (network, rate limits)
- Add automatic prompt refinement if code generation fails
- Build a "code fixer" that corrects syntax/safety errors and re-renders
- Fallback prompt strategies for complex requests

---

### LLM Quality-Dependent Output

**Limitation**: **Output quality depends heavily on the LLM model and prompt clarity**. Weak models may generate mediocre or incorrect animations; unclear prompts lead to mismatched results.

**What doesn't work**:
- Guaranteed output quality regardless of model
- Sophisticated prompt engineering or optimization
- Multi-attempt generation with quality ranking
- Model-agnostic consistent output

**Why**:
- LLM quality varies significantly across models
- Ollama (default) offers lower-cost local inference but lower accuracy
- Some prompts are ambiguous or require reasoning beyond the model's capability
- No evaluation/ranking mechanism to pick the best output

**Workaround**:
- Use more capable models (OpenAI GPT-4 > Azure OpenAI > Ollama llama3 > Ollama llama2)
- Craft very clear, specific prompts
- Use `--debug` to inspect and iterate

**Future Opportunity**:
- Multi-attempt generation with quality scoring (e.g., render complexity, visual appeal)
- Prompt auto-optimization (expand vague prompts with clarifications)
- Model-specific few-shot examples and system prompts
- Evaluation framework to rank generations and learn best practices

---

### No Export to GIF or WebM — MP4 Only

**Limitation**: **Video output is MP4 only**. Cannot export to `.gif`, `.webm`, or other formats.

**What doesn't work**:
- Animated GIF output (good for social media, email)
- WebM format (modern, efficient web video codec)
- MOV or other video container formats
- Optimized formats for specific platforms

**Why**:
- Manim's default output is MP4
- Adding format conversion adds dependencies (ffmpeg, imageio-ffmpeg)
- Scope focus: get MP4 working well first

**Workaround**:
- Convert MP4 to GIF/WebM using ffmpeg:
  ```bash
  # MP4 to GIF
  ffmpeg -i video.mp4 -vf "fps=10,scale=512:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" video.gif
  
  # MP4 to WebM
  ffmpeg -i video.mp4 -c:v libvpx-vp9 -crf 30 -b:v 0 video.webm
  ```

**Future Opportunity**:
- Add `--format {mp4, gif, webm, mov, webp}` flag
- Automatic format optimization for different platforms
- Batch conversion utilities
- Format presets for social media (Instagram, Twitter, TikTok dimensions/specs)

---

### No Unsafe/Invalid Scene Code Correction

**Limitation**: **Generated code is validated but not corrected**. If the LLM generates unsafe code (forbidden imports, dangerous function calls), it's rejected; there's no automatic fix.

**What doesn't work**:
- Auto-rewriting code to remove forbidden imports
- Suggesting safe alternatives
- Gradual LLM refinement to generate safer code

**Why**:
- Automatic code rewriting is error-prone and could break functionality
- Better to fail fast and let the user iterate
- Fixes are usually context-dependent (what was the user trying to do?)

**Workaround**:
- Read the validation error
- Rephrase the prompt to avoid the forbidden operation
- Use `--image` for image operations instead of prompting the LLM to load files

**Future Opportunity**:
- Build a code optimizer that rewrites generated code safely
- Fallback prompt generator that catches safety violations and suggests alternatives
- User-facing "code advisor" that explains why code was rejected and how to fix it

---

## Future Opportunities Summary

| Opportunity | Effort | Impact | Potential Phase |
|-------------|--------|--------|-----------------|
| Audio/sound support & narration | High | High | Phase 2 |
| Transcript & subtitle generation | Medium | Medium | Phase 2 |
| Voice-over synchronization | High | High | Phase 2 |
| 3D animations & camera work | High | Medium | Phase 3 |
| Multi-scene compositions & transitions | High | Medium | Phase 2 |
| Extended duration (60s+) with auto-segmenting | Medium | Medium | Phase 1.5 |
| Audio-reactive animations | High | Medium | Phase 3 |
| Real-time preview & interactive editor | Very High | High | Phase 3 |
| Web UI & dashboard | High | High | Phase 2 |
| Template library & marketplace | High | High | Phase 2 |
| Automatic retry & error recovery | Medium | Medium | Phase 1.5 |
| Multi-attempt generation with ranking | High | Medium | Phase 2 |
| Format export (GIF, WebM, WebP) | Low | Medium | Phase 1.5 |
| Code correction & auto-fixing | Medium | Medium | Phase 2 |

---

## Recommended Phase 1.5 Tasks (Easy Wins)

These improvements could ship soon with moderate effort:

1. **Extended duration support** (up to 60 seconds)
   - Tune LLM system prompt for longer scenes
   - Test with existing infrastructure
   - Would unlock more use cases (full explanations, tutorials)

2. **Export format conversions** (GIF, WebM)
   - Wrap ffmpeg commands
   - Add `--format` flag
   - Document best practices for each format

3. **Better error recovery**
   - Implement exponential backoff for transient failures
   - Add `--retry` flag for user control
   - Track failed attempts and suggest improvements

4. **Template system** (v1 — file-based)
   - Store reusable animation prompts as YAML/JSON
   - Add `--template` flag to select and customize
   - Build community contribution workflow

---

## Recommended Phase 2 Features (More Impact)

These would significantly expand the tool's capabilities:

1. **Web UI** (most requested)
   - Simple FastAPI backend
   - React/Vue frontend
   - Real-time progress & history tracking

2. **Audio integration**
   - Narration support (TTS or user-provided audio)
   - Audio-to-text transcription
   - Auto-sync animations to speech timing

3. **Multi-scene composition**
   - Scene sequencing syntax
   - Built-in transitions
   - Automatic timing orchestration

4. **Template marketplace**
   - Community contributions
   - Versioning & discovery
   - Parameterization & customization

---

## Recommended Phase 3 Features (Ambitious)

Longer-term, transformative features:

1. **3D animations** via Manim 3D module
2. **Real-time interactive editor** with Jupyter integration
3. **Audio-reactive visualizations** (music videos, VJ tools)
4. **IDE plugins** for seamless animation authoring
5. **AI-powered prompt suggestions** (GPT refines vague user requests)

---

## Conclusion

Manim Animation Generator Phase 0 is intentionally focused: **AI-powered 2D educational animations in 5-30 seconds, generated from plain English**. Future phases will expand the tool's capabilities in audio, composition, 3D, and interactivity, unlocking new use cases for longer, richer, more interactive content.

Feedback and feature requests are welcome — please file issues or PRs to help shape the roadmap!
