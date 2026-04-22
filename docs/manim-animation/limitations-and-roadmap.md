← [Back to Documentation Index](../README.md)

# Manim Animation — Limitations & Roadmap

An honest assessment of what this package does NOT do today, and where it could go next.

> **Phase:** This is a Phase 0 proof-of-concept. The boundaries below are intentional for this stage.

---

## Current Limitations

### 1. Sound Effects — Phase 0 Complete

**Status:** ✅ Supported (basic sound effects only)

Sound effects can be added to animations using the `--sound-effects` flag:

```bash
manim-gen --prompt "Bouncing ball" --sound-effects beep.mp3 --output bounce.mp4
```

**Supported formats:** `.wav`, `.mp3`, `.ogg` (max 50 MB per file)

**Limitations of Phase 0:**
- **No background music** — only sound effects via `self.add_sound()`
- **No audio mixing** — single audio track only, no multi-track composition
- **No narration** — no TTS integration or voice-over support
- **No audio-reactive animations** — timing is fixed, not driven by audio cues

**Future opportunity (Phase 1):** Audio mixing, background music loops, TTS narration, audio duration detection.

### 2. No Transcript or Subtitle Generation

There is no generation of:
- `.srt` or `.vtt` caption files
- Accessibility text tracks
- Timed text metadata

**Workaround:** Manually create `.srt` files and mux with FFmpeg:
```bash
ffmpeg -i animation.mp4 -i subs.srt -c copy -c:s mov_text output.mp4
```

**Future opportunity:** Use the prompt text + animation timing to auto-generate subtitle files. An LLM could break the prompt into timed segments matching `self.play()` / `self.wait()` calls.

---

### 3. No Voice-Over Synchronization

Cannot sync animation timing to speech or narration. Animations run on fixed `self.wait()` durations, not driven by audio cues.

**Future opportunity:** Integrate a TTS engine (e.g., Azure Speech, ElevenLabs) and use word-level timestamps to drive `run_time` parameters in Manim animations.

---

### 4. 2D Only — No 3D Camera Work

All scenes use Manim's 2D `Scene` class. No support for:
- `ThreeDScene` or 3D camera movement
- 3D objects (`Surface`, `ParametricSurface`)
- Camera rotation or perspective transforms

**Why:** The LLM prompt and few-shot examples only demonstrate 2D scenes. 3D scenes require significantly more complex code that current LLMs generate less reliably.

**Future opportunity:** Add 3D few-shot examples and a `--3d` flag to switch the system prompt and base class to `ThreeDScene`.

---

### 5. Single Scene Only — No Multi-Scene Compositions

Each generation produces exactly **one scene**. There is no support for:
- Scene transitions (fade, wipe, dissolve)
- Multi-scene sequencing (intro → content → outro)
- Scene chaining or storyboard workflows

**Why:** The system prompt instructs the LLM to generate a single `GeneratedScene` class. The renderer targets exactly that class name.

**Future opportunity:** Accept a multi-part prompt (or JSON storyboard), generate multiple scenes, and concatenate with FFmpeg.

---

### 6. 5–30 Second Duration Limit

The `Config` class enforces `5 ≤ duration ≤ 30`. Attempting values outside this range raises `ValueError`.

**Why:** Short durations keep LLM-generated code manageable. Longer animations require more complex timing and animation choreography that LLMs struggle with.

**Future opportunity:** Extend to 120s for capable models, or decompose long-form content into multiple scenes.

---

### 7. No Real-Time Preview

You must render the full video to see the result. There is no:
- Live preview window
- Interactive scene editing
- Frame-by-frame stepping

**Workaround:** Use `--quality low` for fast iteration (480p, 15fps).

**Future opportunity:** Integrate Manim's `--preview` flag or add a web-based preview using Manim's WebGL renderer.

---

### 8. No Web UI — CLI Only

The only interface is the command line (`manim-gen` CLI). No web dashboard, no REST API, no GUI.

**Future opportunity:** Build a Flask/FastAPI wrapper or Gradio UI for prompt input, preview, and download.

---

### 9. No Template Library

The package uses hardcoded few-shot examples in `config.py` (`FEW_SHOT_EXAMPLES`). There is no:
- User-extensible template system
- Template marketplace or sharing
- Category-based template selection

**Future opportunity:** Create a `templates/` directory with `.py` Manim scenes organized by category (math, physics, data-viz, storytelling) that the LLM can reference.

---

### 10. Happy Path Focus — Limited Error Recovery

The current error handling is straightforward:
- LLM failures raise `LLMError` (no automatic retry)
- Validation failures raise `ValidationError` (no auto-fix)
- Render failures raise `RenderError` (no fallback)

There is no retry loop, no prompt repair, and no fallback to a simpler scene.

**Future opportunity:** Add retry with prompt refinement — if validation fails, send the error back to the LLM and ask it to fix the code.

---

### 11. LLM Quality-Dependent Output

Output quality varies significantly based on:
- Which LLM model is used (GPT-4 >> Llama3 for complex scenes)
- Prompt specificity and clarity
- Whether the animation concept maps well to Manim primitives

The package has no way to evaluate or score the quality of generated animations.

**Future opportunity:** Add a validation step that checks animation density (are there actual `self.play()` calls?), timing (does it fill the requested duration?), and visual complexity.

---

### 12. MP4 Only — No GIF or WebM Export

Output is always MP4 (H.264). No support for:
- Animated GIF (for embedding in docs/READMEs)
- WebM (for web playback)
- Image sequences (PNG frames)

**Workaround:**
```bash
# Convert to GIF
ffmpeg -i animation.mp4 -vf "fps=10,scale=480:-1" output.gif

# Convert to WebM
ffmpeg -i animation.mp4 -c:v libvpx-vp9 output.webm
```

**Future opportunity:** Add `--format` flag and post-render conversion.

---

### 13. No LLM Code Correction

If the LLM generates code that fails validation or rendering, the pipeline stops. There is no:
- Automatic retry with error feedback
- Code repair prompting
- Fallback to a simpler animation

**Future opportunity:** Implement a retry loop: on validation/render failure, send the error message back to the LLM with the original prompt and ask for a corrected version (up to N retries).

---

## Feature Roadmap

### Phase 1 — Quick Wins (Low Effort, High Value)

| Feature | Effort | Impact |
|---------|--------|--------|
| Extended duration (up to 120s) | Low | Medium |
| GIF/WebM export (`--format`) | Low | High |
| Retry with error feedback | Medium | High |
| Template library (`templates/`) | Medium | Medium |
| **Audio mixing** | Low | Medium |
| **Background music / narration** | Medium | High |

### Phase 2 — Major Capabilities

| Feature | Effort | Impact |
|---------|--------|--------|
| ~~Audio/TTS integration~~ | ~~High~~ | ~~High~~ | **[Phase 0]** |
| Subtitle generation | Medium | High |
| Multi-scene sequencing | High | High |
| Web UI (Gradio/Flask) | Medium | Medium |
| 3D scene support | High | Medium |
| **Audio-reactive keyframes** | High | Medium |

### Phase 3 — Ambitious Goals

| Feature | Effort | Impact |
|---------|--------|--------|
| Audio-reactive animations | High | Medium |
| Interactive preview | High | Medium |
| Quality scoring/evaluation | Medium | Medium |
| IDE plugin integration | High | Low |
| Voice-over synchronization | High | High |

---

## Design Philosophy

The limitations above are mostly **intentional constraints** for Phase 0:

- **Security first:** The AST validation whitelist (3 allowed imports, 12 blocked functions) is strict by design.
- **Simplicity over features:** One scene, one output, CLI-driven. No configuration sprawl.
- **LLM-agnostic:** Supports Ollama (local), OpenAI, and Azure — but doesn't depend on any specific model's capabilities.
- **Fail fast:** Errors are raised immediately with clear messages rather than silently degrading.

---

## Related Tools in This Repository

This repository contains complementary tools for different media generation needs:

- **`image-generation/`** — For static image generation using SDXL (blog illustrations, standalone artwork)
- **`remotion-animation/`** — For alternative web-based animations using React/TypeScript (creative motion graphics, interactive components)
- **`mermaid-diagrams/`** — For rendering static diagrams from Mermaid syntax (flowcharts, ER diagrams, sequences)

Each tool is independent. Combine them for comprehensive multimedia generation workflows.
