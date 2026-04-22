# Orchestration Log: Trinity Audio Research

**Agent:** Trinity (Backend Dev)  
**Date:** 2026-04-22T06:58  
**Task:** Technical research on audio/video libraries, TTS, sync approaches  
**Mode:** Background  
**Status:** COMPLETE  

---

## Assignment

Provide comprehensive technical research on:
- Python audio/video libraries (MoviePy, pydub, librosa, FFmpeg, PyAV, etc.)
- TTS options (cloud providers: OpenAI, Azure, Google; local: Piper, XTTS)
- Audio-video sync strategies
- Subtitle/transcript generation approaches
- FFmpeg capabilities for audio muxing

---

## Outcome

**Key Finding:** Multiple viable integration paths exist. Recommended approach is FFmpeg-based audio muxing with cloud TTS (OpenAI/Azure) for quality + simplicity.

### Research Coverage

1. **Python Audio/Video Libraries** — 9 tools analyzed:
   - MoviePy (high-level compositing) → RECOMMENDED for post-production
   - pydub (audio manipulation) → RECOMMENDED for TTS preprocessing
   - FFmpeg-python (muxing) → RECOMMENDED for simple audio+video
   - Manim's `add_sound()` → PREFERRED for manim-animation
   - Remotion's `<Audio>` → PREFERRED for remotion-animation

2. **TTS Providers** — 6 options evaluated:
   - OpenAI TTS (best quality, 128 kbps mp3)
   - Azure Speech (enterprise, on-prem support)
   - Google Cloud TTS (cost-effective, low latency)
   - Piper (local, offline, <100MB)
   - XTTS v2 (local, multilingual, high quality)
   - ElevenLabs (voice cloning, but expensive)

3. **Audio-Video Sync** — 3 strategies documented:
   - Stream-based (audio duration detection, FFmpeg muxing)
   - Frame-aligned (Remotion's per-frame volume, Manim's time-offset)
   - Post-production (MoviePy compositing)

4. **Subtitle/Transcript** — 4 approaches outlined:
   - OpenAI Whisper (audio → SRT format)
   - Cloud Speech-to-Text (Google, Azure)
   - Burn-in vs VTT sidecar files

### Deliverable

Comprehensive technical research written to `.squad/decisions/inbox/trinity-video-sound-research.md` including:
- Detailed library comparison tables
- TTS provider analysis with pricing + latency
- Audio-video sync deep dive
- Subtitle generation walkthrough
- FFmpeg command references
- Python code examples for each approach

---

## Next Steps

- Morpheus: Finalize architecture recommendation based on research
- Squad: Select TTS provider and audio sync strategy
- Implementation: Create audio preprocessing module in image-generation/

---

**Session:** Spawned 2026-04-22 06:58 UTC  
**Logger:** Scribe
