# Full Audio Support — Implementation Plan

**Author:** Trinity (Backend Dev)  
**Date:** 2026-04-22  
**Status:** PLAN  
**Depends on:** Decision Set "Audio + Video Architecture" (Option B approved)

---

## 1. Feature Scope

### CLI Flags (new)

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--narration-text` | `str` | — | Inline text for TTS narration |
| `--narration-file` | `path` | — | Text file containing narration |
| `--background-music` | `path` | — | MP3/WAV file for background music |
| `--sound-effects` | `path[]` | — | One or more SFX audio files (nargs="+") |
| `--tts-provider` | `choice` | `edge-tts` | TTS engine: `edge-tts` (free) or `openai` |
| `--voice` | `str` | provider default | Voice name (e.g. `en-US-GuyNeural`, `alloy`) |
| `--music-volume` | `float` | `0.3` | Background music volume 0.0–1.0 |
| `--narration-volume` | `float` | `1.0` | Narration volume 0.0–1.0 |
| `--audio-policy` | `choice` | `strict` | Audio file validation policy: `strict`, `warn`, `ignore` |

**Mutual exclusion:** `--narration-text` and `--narration-file` cannot both be set.

### What This Enables

- User provides narration text → TTS generates MP3 → copied to `public/` → LLM told to use `<Audio>`
- User provides background music file → validated, copied → LLM sets volume to `--music-volume`
- User provides SFX files → validated, copied → LLM uses `<Sequence>` + `<Audio>` for timing
- Volume is controlled via Remotion's `volume` prop (static float or per-frame function)

---

## 2. Files to Modify

### 2.1 `remotion_gen/cli.py` (lines ~310)

**Changes:**
- Add 9 new `argparse` arguments (lines 244–300 area, after `--image-policy`)
- Add mutual-exclusion check for `--narration-text` / `--narration-file`
- Add volume range validation (0.0–1.0)
- Update `generate_video()` signature: add `narration_text`, `narration_file`, `background_music`, `sound_effects`, `tts_provider`, `voice`, `music_volume`, `narration_volume`, `audio_policy` params
- Add "Step 0b: Handle audio input" block in `generate_video()` (after image handling), calling `audio_handler` functions
- Pass `audio_context` to `generate_component()` (like `image_context`)
- Update epilog examples with audio flags

**Estimated new code:** ~80 lines  
**Breaking changes:** None — all new params are optional with defaults

### 2.2 `remotion_gen/llm_client.py` (lines ~327)

**Changes:**
- Extend `SYSTEM_PROMPT` with `<Audio>` component documentation (after "When an image is provided:" block, ~line 46)
- Add audio API signature section covering:
  - `<Audio src={staticFile('narration.mp3')} volume={1.0} />`
  - `<Audio src={staticFile('music.mp3')} volume={0.3} loop />`
  - Per-frame volume: `volume={(f) => interpolate(f, [0, 30], [0, 1], {extrapolateRight: 'clamp'})}`
  - SFX inside `<Sequence>`: `<Sequence from={60}><Audio src={staticFile('sfx.mp3')} /></Sequence>`
- Update `generate_component()` to accept `audio_context: Optional[str]` param
- Append `audio_context` to `base_prompt` (same pattern as `image_context` at line 278)

**Estimated new code:** ~40 lines (mostly prompt text)  
**Breaking changes:** None — `audio_context` is optional

### 2.3 `remotion_gen/component_builder.py` (lines ~483)

**Changes:**
- `Audio` is already in `_REMOTION_HOOKS` (line 200) ✅ — no change needed for import fixup
- Add `"Audio"` to JSX tag balance check in `validate_tsx_syntax()` (line 181, add to list alongside `"Img"`)
- Create `validate_audio_paths()` function — same pattern as `validate_image_paths()` (line 351) but checks audio filenames
- Create `inject_audio_imports()` function — ensures `Audio` and `staticFile` are imported (mirrors `inject_image_imports()`)
- Update `write_component()` to accept `audio_filenames: Optional[list[str]]` and call audio validation/injection

**Estimated new code:** ~80 lines  
**Breaking changes:** None — new optional param

### 2.4 `remotion_gen/config.py` (lines ~43)

**Changes:**
- Add audio constants:
  - `ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}`
  - `MAX_AUDIO_SIZE = 200 * 1024 * 1024` (200 MB)
  - `MAX_AUDIO_DURATION_SECONDS = 300` (5 min)
  - `DEFAULT_TTS_PROVIDER = "edge-tts"`
  - `DEFAULT_MUSIC_VOLUME = 0.3`
  - `DEFAULT_NARRATION_VOLUME = 1.0`
  - `TTS_VOICE_DEFAULTS = {"edge-tts": "en-US-GuyNeural", "openai": "alloy"}`
  - `TTS_OUTPUT_FORMAT = "mp3"`

**Estimated new code:** ~15 lines  
**Breaking changes:** None

### 2.5 `remotion_gen/errors.py` (lines ~44)

**Changes:**
- Add `AudioValidationError(RemotionGenError)` — mirrors `ImageValidationError`
- Add `TTSError(RemotionGenError)` — TTS generation failures

**Estimated new code:** ~14 lines  
**Breaking changes:** None

### 2.6 `pyproject.toml`

**Changes:**
- Add `edge-tts>=6.1.0` to `dependencies` (base install for free TTS)
- Add optional dependency group `[project.optional-dependencies.tts]` with `openai>=1.0.0` (already present as base dep, but documents intent)
- Note: `openai` is already a base dependency, so OpenAI TTS works out of the box

**Estimated new code:** ~3 lines  
**Breaking changes:** None — edge-tts is a lightweight addition

---

## 3. New Files to Create

### 3.1 `remotion_gen/audio_handler.py` (~200 lines)

Mirrors `image_handler.py` (152 lines). Responsibilities:

```
validate_audio_path(path, policy) → Path
    - Check exists, is_file, not symlink
    - Check extension against ALLOWED_AUDIO_EXTENSIONS
    - Check file size against MAX_AUDIO_SIZE
    - Policy: strict / warn / ignore (same as image)

copy_audio_to_public(audio_path, project_root, policy, prefix="audio") → str
    - Validate, copy with sanitized name: "{prefix}_{uuid8}.mp3"
    - Return filename

generate_audio_context(audio_files: dict, music_volume, narration_volume) → str
    - Build LLM prompt context describing available audio assets
    - Keys: "narration", "music", "sfx_0", "sfx_1", ...
    - Include volume instructions
    - Include <Audio> component usage examples
```

### 3.2 `remotion_gen/tts_providers.py` (~180 lines)

Provider abstraction for TTS engines:

```python
class TTSProvider(Protocol):
    """TTS provider interface."""
    def generate(self, text: str, voice: str, output_path: Path) -> Path: ...

class EdgeTTSProvider:
    """Free TTS using edge-tts (Microsoft Azure voices via Edge)."""
    async def generate(self, text: str, voice: str, output_path: Path) -> Path:
        # Uses edge_tts.Communicate()
        # Runs async with asyncio.run()
        # Output: MP3

class OpenAITTSProvider:
    """OpenAI TTS API (tts-1 or tts-1-hd)."""
    def generate(self, text: str, voice: str, output_path: Path) -> Path:
        # Uses openai.audio.speech.create()
        # Requires OPENAI_API_KEY
        # Output: MP3

def get_tts_provider(provider_name: str) -> TTSProvider:
    """Factory function. Returns the right provider."""

def generate_narration(
    text: str,
    provider_name: str = "edge-tts",
    voice: str | None = None,
    output_dir: Path | None = None,
) -> Path:
    """High-level: text → MP3 file path."""
```

### 3.3 Test Files

| File | Lines (est.) | Tests |
|------|-------------|-------|
| `tests/test_audio_handler.py` | ~250 | 18 test cases |
| `tests/test_tts_providers.py` | ~200 | 14 test cases |
| `tests/test_audio_cli.py` | ~150 | 10 test cases |
| `tests/test_audio_security.py` | ~120 | 8 test cases |
| `tests/test_audio_integration.py` | ~100 | 5 test cases |

---

## 4. Component Builder Changes (Detail)

### 4.1 Import Fixup — Already Done ✅

`Audio` is already in `_REMOTION_HOOKS` at line 200 of `component_builder.py`. If the LLM uses `<Audio>` but forgets the import, `ensure_remotion_imports()` will auto-add it. No change needed.

### 4.2 JSX Tag Balance Check

In `validate_tsx_syntax()` at line 181, the tag list is:
```python
for tag in ["AbsoluteFill", "Sequence", "div", "Img"]:
```

**Change to:**
```python
for tag in ["AbsoluteFill", "Sequence", "div", "Img", "Audio"]:
```

This catches unclosed `<Audio>` tags in LLM-generated code.

### 4.3 Audio Path Validation (New Function)

```python
def validate_audio_paths(code: str, allowed_audio_filenames: list[str]) -> None:
```

Same security checks as `validate_image_paths()`:
- Block `file://` URLs
- Block path traversal (`../`)
- Block `data:` URIs
- Verify all `staticFile()` calls reference only allowed filenames (images OR audio)
- Reject non-literal `staticFile()` calls

**Key difference from image validation:** Multiple audio files can be allowed simultaneously (narration + music + N SFX), so `allowed_audio_filenames` is a list, not a single string.

### 4.4 `write_component()` Update

```python
def write_component(
    code: str,
    project_root: Path,
    debug: bool = False,
    image_filename: Optional[str] = None,
    audio_filenames: Optional[list[str]] = None,  # NEW
) -> Path:
```

Add audio injection + validation between image handling and `ensure_remotion_imports()`:
```python
if audio_filenames:
    code = inject_audio_imports(code, audio_filenames)
    validate_audio_paths(code, audio_filenames)
```

### 4.5 Unified `staticFile()` Validation

Refactor `validate_image_paths` and the new `validate_audio_paths` to share a common `_validate_static_file_refs(code, allowed_filenames)` helper. This prevents drift between the two validators.

---

## 5. LLM Prompt Changes

### 5.1 System Prompt Additions

Add after the "When an image is provided:" block (line 46 in `llm_client.py`):

```
When audio files are provided:
- Add Audio and staticFile to your remotion import.
- Use <Audio src={staticFile('filename.mp3')} volume={1.0} /> for narration.
- Use <Audio src={staticFile('music.mp3')} volume={0.3} loop /> for background music.
- Use <Sequence from={frameNumber}><Audio src={staticFile('sfx.mp3')} /></Sequence> for timed sound effects.
- Volume can be a number (0.0-1.0) or a callback for per-frame control:
  volume={(f) => interpolate(f, [0, 30], [0, 1], {extrapolateRight: 'clamp'})}
- Audio elements are self-closing: <Audio ... /> (not <Audio>...</Audio>).
- Do NOT import Audio from 'react' — import from 'remotion'.
```

### 5.2 Working Example Update

Add a second working example to the system prompt showing audio usage:

```tsx
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Audio, staticFile, Sequence} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const opacity = interpolate(frame, [0, 30], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a2e', justifyContent: 'center', alignItems: 'center'}}>
      <Audio src={staticFile('narration.mp3')} volume={1.0} />
      <Audio src={staticFile('music.mp3')} volume={0.3} loop />
      <Sequence from={60}>
        <Audio src={staticFile('sfx_whoosh.mp3')} volume={0.8} />
      </Sequence>
      <h1 style={{color: '#fff', fontSize: 80, opacity}}>Hello Remotion</h1>
    </AbsoluteFill>
  );
}
```

### 5.3 Audio Context Template (in `audio_handler.py`)

Generated by `generate_audio_context()` and appended to user prompt:

```
## Audio Assets Available

The following audio files have been placed in the Remotion project's public/ folder.

### Narration
- Filename: `narration_a1b2c3d4.mp3`
- Use: `<Audio src={staticFile('narration_a1b2c3d4.mp3')} volume={1.0} />`

### Background Music
- Filename: `music_e5f6g7h8.mp3`
- Use: `<Audio src={staticFile('music_e5f6g7h8.mp3')} volume={0.3} loop />`

### Sound Effects
- `sfx_0_i9j0k1l2.mp3` — Use inside <Sequence> for timed playback
- `sfx_1_m3n4o5p6.mp3`

IMPORTANT: You MUST include all provided audio files in the component.
Use staticFile('exact_filename') — do NOT use any other path.
Set narration volume to 1.0 and music volume to 0.3.
```

---

## 6. TTS Integration Design

### 6.1 Provider Abstraction

```
tts_providers.py
├── TTSProvider (Protocol)
│   └── generate(text, voice, output_path) → Path
├── EdgeTTSProvider
│   └── Uses edge-tts library (async, wraps in asyncio.run)
├── OpenAITTSProvider
│   └── Uses openai.audio.speech.create()
└── get_tts_provider(name) → TTSProvider
```

**edge-tts** (default):
- Free, uses Microsoft Azure Neural voices via Edge browser protocol
- Async API — wrap in `asyncio.run()` for sync interface
- Output: MP3 natively
- No API key needed
- Voice default: `en-US-GuyNeural`
- Rate limited but sufficient for dev/small batches

**OpenAI TTS**:
- Requires `OPENAI_API_KEY` (already used for LLM)
- Model: `tts-1` (fast) or `tts-1-hd` (quality)
- Voices: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`
- Output: MP3 via `response.stream_to_file()`
- ~$0.015/1K chars

### 6.2 Audio Format Standardization

- **All TTS output: MP3** (both providers output MP3 natively)
- **User-provided files:** Accept MP3, WAV, OGG, M4A, AAC
- **No format conversion in Phase 0** — Remotion handles all these formats natively
- Phase 1: Add optional pydub-based normalization/trimming

### 6.3 Error Handling

```python
class TTSError(RemotionGenError):
    """TTS generation failed."""

# Specific failure modes:
# - edge-tts: network timeout, rate limit, invalid voice name
# - openai: missing API key, quota exceeded, invalid voice
# - both: empty text input, output file not created
```

Error handling strategy:
1. Validate text is non-empty before calling provider
2. Catch provider-specific exceptions, wrap in `TTSError`
3. Verify output file exists and is >0 bytes after generation
4. CLI prints clear error message and exits 1 (no silent failures)

### 6.4 Caching Strategy

**Phase 0: No caching** — generate fresh each time. Rationale:
- TTS calls are fast (<5s for edge-tts, <3s for OpenAI)
- Users typically iterate on prompts, not narration
- Avoids cache invalidation complexity

**Phase 1 (future):** File-based cache keyed on `hash(text + voice + provider)`:
```
.cache/tts/{sha256_hex}.mp3
```

### 6.5 API Key Configuration

| Provider | Env Var | Required? |
|----------|---------|-----------|
| edge-tts | (none) | No — free |
| openai | `OPENAI_API_KEY` | Yes — same key used for LLM |

No new env vars needed. OpenAI TTS reuses the existing `OPENAI_API_KEY`.

---

## 7. TDD Test Plan

### 7.1 Unit Tests — `test_audio_handler.py` (18 tests)

**`TestValidateAudioPath`:**
1. `test_valid_mp3_passes` — MP3 file passes strict validation
2. `test_valid_wav_passes` — WAV file passes strict validation
3. `test_valid_ogg_passes` — OGG file passes strict validation
4. `test_valid_m4a_passes` — M4A file passes
5. `test_invalid_extension_rejected` — .exe, .txt, .py rejected (strict)
6. `test_invalid_extension_warn_mode` — bad ext prints warning, doesn't raise (warn)
7. `test_ignore_policy_skips_all` — ignore mode returns path without checks
8. `test_nonexistent_file_rejected` — missing file raises AudioValidationError
9. `test_directory_rejected` — path to directory raises error
10. `test_symlink_rejected` — symlink raises AudioValidationError
11. `test_oversized_file_rejected` — file > MAX_AUDIO_SIZE raises error
12. `test_oversized_file_warn_mode` — large file prints warning (warn)

**`TestCopyAudioToPublic`:**
13. `test_copies_with_sanitized_name` — output is `audio_{uuid}.mp3`
14. `test_creates_public_dir` — public/ created if missing
15. `test_custom_prefix` — prefix="music" → `music_{uuid}.mp3`
16. `test_source_file_untouched` — original file still exists after copy

**`TestGenerateAudioContext`:**
17. `test_narration_only_context` — context mentions narration filename and volume
18. `test_full_context` — context includes narration + music + SFX with volumes

### 7.2 Unit Tests — `test_tts_providers.py` (14 tests)

**`TestEdgeTTSProvider`:**
1. `test_generate_creates_mp3` — mock edge_tts, verify MP3 output path returned
2. `test_generate_with_custom_voice` — voice parameter passed to Communicate()
3. `test_empty_text_raises` — empty string raises TTSError
4. `test_network_error_wraps` — edge_tts exception wrapped in TTSError
5. `test_invalid_voice_raises` — nonexistent voice name raises TTSError
6. `test_output_file_created` — verify file exists after generate()

**`TestOpenAITTSProvider`:**
7. `test_generate_creates_mp3` — mock openai.audio.speech.create(), verify output
8. `test_missing_api_key_raises` — no OPENAI_API_KEY raises TTSError
9. `test_custom_voice` — voice param passed to API
10. `test_api_error_wraps` — OpenAI exception wrapped in TTSError
11. `test_empty_text_raises` — empty string raises TTSError

**`TestGetTTSProvider`:**
12. `test_edge_tts_returned` — `get_tts_provider("edge-tts")` returns EdgeTTSProvider
13. `test_openai_returned` — `get_tts_provider("openai")` returns OpenAITTSProvider
14. `test_unknown_provider_raises` — `get_tts_provider("foo")` raises TTSError

**Mock strategy:** `unittest.mock.patch` on `edge_tts.Communicate` and `openai.audio.speech.create`. No real API calls in unit tests.

### 7.3 Unit Tests — `test_audio_cli.py` (10 tests)

1. `test_narration_text_flag_accepted` — parser accepts --narration-text
2. `test_narration_file_flag_accepted` — parser accepts --narration-file
3. `test_narration_mutual_exclusion` — both flags → error
4. `test_background_music_flag` — parser accepts --background-music
5. `test_sound_effects_multiple` — --sound-effects a.mp3 b.mp3 parses as list
6. `test_tts_provider_choices` — only edge-tts and openai accepted
7. `test_voice_flag` — --voice passed through
8. `test_music_volume_range` — 0.0–1.0 accepted, outside range rejected
9. `test_narration_volume_range` — same range validation
10. `test_audio_flags_in_generate_video` — all audio params reach generate_video()

### 7.4 Security Tests — `test_audio_security.py` (8 tests)

1. `test_validate_audio_paths_blocks_file_url` — `file://` in code raises
2. `test_validate_audio_paths_blocks_path_traversal` — `../` blocked
3. `test_validate_audio_paths_blocks_data_uri` — `data:audio/` blocked
4. `test_validate_audio_paths_blocks_unknown_filename` — staticFile('evil.mp3') blocked
5. `test_validate_audio_paths_allows_known_files` — approved filenames pass
6. `test_validate_audio_paths_blocks_non_literal` — template literal in staticFile() blocked
7. `test_validate_audio_paths_blocks_encoded_traversal` — `%2E%2E%2F` blocked
8. `test_inject_audio_imports_adds_audio` — Audio import injected correctly

### 7.5 Integration Tests — `test_audio_integration.py` (5 tests)

1. `test_narration_end_to_end` — text → TTS → copy → LLM receives context → component written (mock LLM + TTS)
2. `test_music_end_to_end` — music file → copy → LLM receives context → component written
3. `test_all_audio_types` — narration + music + SFX → all copied, all in LLM context
4. `test_audio_plus_image` — both --image and --narration-text work together
5. `test_tts_failure_graceful` — TTS error raises TTSError, not unhandled exception

**Mock strategy:** Mock both LLM API and TTS API. Use `tmp_path` for project directory. Verify files in `public/`, component code references correct filenames.

### 7.6 Test Summary

| Category | Tests | Mock Strategy |
|----------|-------|---------------|
| audio_handler | 18 | Filesystem only (tmp_path) |
| tts_providers | 14 | Patch edge_tts + openai |
| audio_cli | 10 | Patch generate_video |
| audio_security | 8 | Filesystem + code validation |
| audio_integration | 5 | Patch LLM + TTS + filesystem |
| **Total** | **55** | |

---

## 8. Documentation Updates

### 8.1 Files to Update

| File | Changes |
|------|---------|
| `docs/user-guide.md` | Add "Audio Features" section: CLI flags, TTS usage, volume control, examples |
| `docs/architecture.md` | Add audio_handler.py and tts_providers.py to pipeline diagram; update data flow |
| `docs/development.md` | Add audio module development notes, TTS provider setup |
| `docs/installation.md` | Add edge-tts dependency, note optional OpenAI TTS |
| `docs/troubleshooting.md` | Add audio-specific errors: TTS failures, unsupported formats, missing API keys |
| `docs/limitations-and-roadmap.md` | Update Phase 0 scope, add Phase 1 audio features to roadmap |
| `docs/testing.md` | Document new test files, mock strategies for TTS |

### 8.2 New Sections

**user-guide.md — "Audio Features" section:**
- Adding narration (text and file input)
- Background music
- Sound effects with timing
- Volume control
- TTS provider selection
- Complete example commands

**architecture.md — Pipeline update:**
```
cli.py → [audio_handler.py + tts_providers.py] → llm_client.py → component_builder.py → renderer.py
                                                    ↑ audio_context
```

---

## 9. Implementation Order

### Phase 0: Foundation (Steps 1–4)

```
Step 1: errors.py + config.py constants
        ├── Add AudioValidationError, TTSError
        └── Add audio config constants
        Complexity: Low (~30 min)
        Dependencies: None

Step 2: audio_handler.py + test_audio_handler.py
        ├── validate_audio_path()
        ├── copy_audio_to_public()
        ├── generate_audio_context()
        └── All 18 tests (TDD: tests first)
        Complexity: Medium (~2 hours)
        Dependencies: Step 1
        Pattern: Copy image_handler.py, adapt for audio

Step 3: tts_providers.py + test_tts_providers.py    [CAN PARALLEL with Step 2]
        ├── EdgeTTSProvider
        ├── OpenAITTSProvider
        ├── get_tts_provider() factory
        ├── generate_narration() high-level API
        └── All 14 tests (TDD: tests first)
        Complexity: Medium (~2 hours)
        Dependencies: Step 1

Step 4: component_builder.py changes + test_audio_security.py
        ├── Add "Audio" to tag balance check
        ├── validate_audio_paths()
        ├── inject_audio_imports()
        ├── Refactor shared staticFile validation
        ├── Update write_component() signature
        └── All 8 security tests
        Complexity: Medium (~1.5 hours)
        Dependencies: Step 1
```

### Phase 0: Integration (Steps 5–7)

```
Step 5: llm_client.py prompt changes
        ├── Extend SYSTEM_PROMPT with Audio docs
        ├── Add audio working example
        ├── Accept audio_context parameter
        └── Verify existing LLM tests still pass
        Complexity: Low (~45 min)
        Dependencies: None (prompt-only changes)

Step 6: cli.py integration + test_audio_cli.py
        ├── Add 9 new argparse flags
        ├── Add audio processing to generate_video()
        ├── Wire audio_handler + tts_providers into pipeline
        └── All 10 CLI tests
        Complexity: Medium (~1.5 hours)
        Dependencies: Steps 2, 3, 4, 5

Step 7: Integration tests + pyproject.toml
        ├── test_audio_integration.py (5 tests)
        ├── Add edge-tts to pyproject.toml dependencies
        ├── Run full test suite — verify no regressions
        └── Manual smoke test with real TTS
        Complexity: Low (~1 hour)
        Dependencies: Step 6
```

### Phase 0: Polish (Step 8)

```
Step 8: Documentation updates
        ├── Update all 7 docs files
        └── Add audio examples
        Complexity: Low (~1 hour)
        Dependencies: Step 7
```

### Parallelization

```
Step 1 ─────┬──→ Step 2 ──┐
            ├──→ Step 3 ──├──→ Step 6 ──→ Step 7 ──→ Step 8
            └──→ Step 4 ──┘
Step 5 (independent) ─────┘
```

Steps 2, 3, 4, and 5 can all run in parallel after Step 1.

### Time Estimate

| Step | Est. Time | Cumulative |
|------|-----------|-----------|
| 1. Errors + config | 30 min | 30 min |
| 2. audio_handler (parallel) | 2 hours | — |
| 3. tts_providers (parallel) | 2 hours | — |
| 4. component_builder (parallel) | 1.5 hours | — |
| 5. LLM prompt (parallel) | 45 min | — |
| (parallel wall time) | ~2 hours | 2.5 hours |
| 6. CLI integration | 1.5 hours | 4 hours |
| 7. Integration tests | 1 hour | 5 hours |
| 8. Documentation | 1 hour | 6 hours |
| **Total** | **~6 hours** (serial) / **~5 hours** (with parallelism) |

---

## Appendix: Remotion `<Audio>` API Reference

```tsx
// Basic usage
<Audio src={staticFile('audio.mp3')} />

// With volume (0.0 to 1.0)
<Audio src={staticFile('audio.mp3')} volume={0.5} />

// Per-frame volume (fade in)
<Audio
  src={staticFile('audio.mp3')}
  volume={(f) => interpolate(f, [0, 30], [0, 1], {extrapolateRight: 'clamp'})}
/>

// Loop background music
<Audio src={staticFile('music.mp3')} volume={0.3} loop />

// Timed sound effect (starts at frame 60)
<Sequence from={60}>
  <Audio src={staticFile('whoosh.mp3')} volume={0.8} />
</Sequence>

// Multiple audio tracks (auto-mixed by Remotion)
<>
  <Audio src={staticFile('narration.mp3')} volume={1.0} />
  <Audio src={staticFile('music.mp3')} volume={0.3} loop />
</>
```

Key props: `src`, `volume`, `loop`, `startFrom`, `endAt`, `playbackRate`, `muted`.
