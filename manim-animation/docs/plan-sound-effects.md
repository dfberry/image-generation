# Implementation Plan: Sound Effects for manim-animation

**Author:** Trinity (Backend Dev)
**Date:** 2025-01-27
**Status:** PROPOSAL
**Scope:** Phase 0 — Sound effects only (NOT narration/TTS)

---

## 1. Feature Scope

### What This Is
Add support for Manim's native `Scene.add_sound(sound_file, time_offset=0, gain=None)` API so LLM-generated scenes can include short sound effects synced to animation events.

### What This Is NOT
- No narration / TTS
- No background music mixing
- No audio post-production (pydub, MoviePy)
- No new Python dependencies

### CLI Interface

New flag on `manim-gen`:

```
--sound-effects FILE [FILE ...]    Sound effect files (.wav, .mp3, .ogg) available to the scene
```

Example:
```bash
manim-gen \
  --prompt "A ball bounces three times with a thud each time" \
  --sound-effects thud.wav whoosh.mp3 \
  --output bounce.mp4
```

### Supported Formats
- `.wav` — uncompressed, universally supported
- `.mp3` — compressed, widely used
- `.ogg` — open format, Manim/FFmpeg native

These are the formats FFmpeg (Manim's backend) reliably handles.

### How It Works End-to-End
1. User provides `--sound-effects thud.wav whoosh.mp3`
2. CLI validates files exist, checks format/size, copies to workspace (like images)
3. LLM system prompt is extended with sound effect context: available filenames + `add_sound()` API
4. LLM generates scene code that includes `self.add_sound('thud.wav', time_offset=1.5)`
5. AST validator confirms `add_sound()` calls reference only provided files (string literals only)
6. Manim renders video with embedded audio

---

## 2. Files to Modify (with line-level detail)

### 2.1 `manim_gen/cli.py`

**Changes:**
- Add `--sound-effects` argument (lines ~128-130, after `--image-policy`)
- Thread `sound_effects` through `generate_video()` signature and body
- Add `AudioValidationError` to except chain (after `ImageValidationError`, line ~281)
- Copy audio files to workspace alongside images (lines ~180-188)
- Pass audio filenames to `build_scene()` (line ~198)
- Generate audio context for LLM prompt (line ~189-191)

**Estimated new/changed lines:** ~35

**Breaking changes:** None. New flag is optional.

### 2.2 `manim_gen/config.py`

**Changes:**
- Add `ALLOWED_AUDIO_EXTENSIONS` constant: `{".wav", ".mp3", ".ogg"}` (after line 63)
- Extend `SYSTEM_PROMPT` (lines 66-102): add section on `add_sound()` usage
- Extend `FEW_SHOT_EXAMPLES` (lines 105-178): add Example 5 showing `add_sound()`
- Add `"os"` to `ALLOWED_IMPORTS` — **NO. Not needed.** `add_sound()` is a `self.` method, no new imports required.

**Estimated new/changed lines:** ~30

**Breaking changes:** None. System prompt changes are additive.

### 2.3 `manim_gen/scene_builder.py`

**Changes:**
- Import new `validate_audio_operations` function (top of file)
- Add `audio_filenames` parameter to `build_scene()` (line 154)
- Call `validate_audio_operations()` in `build_scene()` (after line 183)

**Estimated new/changed lines:** ~8 in this file (bulk is in new `audio_handler.py`)

**Breaking changes:** `build_scene()` gets a new optional parameter. Existing callers unaffected.

### 2.4 `manim_gen/llm_client.py`

**Changes:**
- Add `audio_context` parameter to `generate_scene_code()` (line 83)
- Append audio context to user message (lines 107-111, same pattern as `image_context`)

**Estimated new/changed lines:** ~8

**Breaking changes:** None. New parameter is optional.

### 2.5 `manim_gen/renderer.py`

**Changes:** None expected. Manim's `add_sound()` is handled by Manim internally during render. The audio files just need to be in the working directory (same as images — `assets_dir` already sets `cwd`).

One verification needed: confirm `assets_dir` is passed as `cwd` to subprocess, which it already is (line 62). Audio files copied to workspace will be findable by Manim.

### 2.6 `manim_gen/errors.py`

**Changes:**
- Add `AudioValidationError` class (after `ImageValidationError`, line 48)

**Estimated new/changed lines:** ~8

---

## 3. New Files to Create

### 3.1 `manim_gen/audio_handler.py`

Sound effect file validation, copying to workspace, and LLM context generation. Mirrors `image_handler.py` pattern exactly.

**Contents:**
```python
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg"}
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50 MB per file

def validate_audio_path(audio_path, policy="strict") -> bool
def copy_audio_to_workspace(audio_paths, workspace_dir, policy="strict") -> Dict[Path, Path]
def generate_audio_context(audio_paths) -> str
def validate_audio_operations(code, allowed_filenames) -> None  # AST validation
```

**Estimated lines:** ~150

**Design notes:**
- `validate_audio_path()`: checks existence, extension, size, rejects symlinks (same as image handler)
- `copy_audio_to_workspace()`: copies as `sfx_0_thud.wav`, `sfx_1_whoosh.mp3` (prefixed to avoid collision with images)
- `generate_audio_context()`: produces LLM context block listing available sound files and `add_sound()` API
- `validate_audio_operations()`: AST walker that ensures `add_sound()` calls use string-literal filenames from the allowed set

### 3.2 `tests/test_audio_handler.py`

Unit tests for audio validation and context generation.

**Estimated lines:** ~200

### 3.3 `tests/test_audio_security.py`

Security-focused tests for AST validation of `add_sound()` calls.

**Estimated lines:** ~120

---

## 4. AST Validation Changes

### 4.1 What `add_sound()` Allows

`Scene.add_sound(sound_file, time_offset=0, gain=None)` is a method call on `self`. In generated code it appears as:

```python
self.add_sound('thud.wav', time_offset=1.5)
```

This is an `ast.Call` where `func` is `ast.Attribute(value=ast.Name(id='self'), attr='add_sound')`.

### 4.2 No Whitelist Changes Needed for `add_sound()`

`add_sound` is NOT in `FORBIDDEN_CALLS`. It's a `self.` method call, same as `self.play()` and `self.wait()`. The existing AST validation **already permits it**. No changes to `FORBIDDEN_CALLS` or `ALLOWED_IMPORTS` are needed.

### 4.3 New Validation: `validate_audio_operations()`

Mirrors `validate_image_operations()` — a new AST walker specifically for audio:

```python
def validate_audio_operations(code: str, allowed_filenames: Set[str]) -> None:
    """Ensure add_sound() calls only reference provided audio files."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Match self.add_sound(...)
        if (isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_sound"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"):

            if not node.args:
                raise ValidationError("add_sound() must have a filename argument")
            arg = node.args[0]
            if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                raise ValidationError(
                    "add_sound() filename must be a string literal"
                )
            if arg.value not in allowed_filenames:
                raise ValidationError(
                    f"add_sound() references unknown file '{arg.value}'. "
                    f"Allowed: {sorted(allowed_filenames)}"
                )
```

### 4.4 Security Analysis

**Can `add_sound()` be abused?**

| Attack Vector | Risk | Mitigation |
|---|---|---|
| Path traversal (`../../etc/passwd`) | Medium | Validate first arg is string literal AND in allowed set |
| Variable filename (`self.add_sound(user_input)`) | Medium | Require `ast.Constant` string — reject variables/expressions |
| Arbitrary file read via Manim | Low | Manim only reads audio; file must exist in cwd |
| Symlink in provided files | Low | `validate_audio_path()` rejects symlinks before copy |
| Large file DoS | Low | 50 MB size cap per file |

**Verdict:** Same security model as images. String-literal-only + allowlist = safe.

---

## 5. LLM Prompt Changes

### 5.1 System Prompt Addition (in `config.py` SYSTEM_PROMPT)

Add after the image instructions block (line ~101):

```
When sound effects are provided:
- Use `self.add_sound('filename.wav')` to play a sound at the current scene time
- Use `self.add_sound('filename.wav', time_offset=1.5)` to play after a delay relative to the current time
- Use `self.add_sound('filename.wav', gain=-3)` to adjust volume (in dB, negative = quieter)
- Only use the EXACT filenames listed — never construct paths dynamically
- Place add_sound() calls at the animation moment where the sound should start
- add_sound() does NOT pause the scene — animations continue while sound plays
```

### 5.2 Few-Shot Example Addition

Add as Example 5 in `FEW_SHOT_EXAMPLES`:

```
Example 5 - Animation with sound effects:
User: "A ball drops and bounces with a thud sound"
Available sound effects: sfx_0_thud.wav
```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        ball = Circle(radius=0.5, color=YELLOW, fill_opacity=1)
        ball.shift(UP * 3)

        # Ball falls
        self.play(ball.animate.shift(DOWN * 5), run_time=1)
        self.add_sound('sfx_0_thud.wav')

        # Bounce up
        self.play(ball.animate.shift(UP * 2), rate_func=smooth, run_time=0.5)
        # Fall again
        self.play(ball.animate.shift(DOWN * 2), run_time=0.4)
        self.add_sound('sfx_0_thud.wav', gain=-3)

        self.wait(1)
```

### 5.3 Audio Context Block

Generated by `generate_audio_context()`, injected into user message (same pattern as image context):

```
## Available Sound Effects
The following audio files are available in the working directory.
Use `self.add_sound('filename')` to play them during the scene.

| File | Format |
|------|--------|
| sfx_0_thud.wav | WAV |
| sfx_1_whoosh.mp3 | MP3 |

API: self.add_sound(sound_file, time_offset=0, gain=None)
- time_offset: seconds after current scene time to start playback
- gain: volume adjustment in dB (negative = quieter, None = original volume)
```

---

## 6. TDD Test Plan

### 6.1 Unit Tests — `tests/test_audio_handler.py`

| # | Test Name | Description |
|---|-----------|-------------|
| 1 | `test_validate_wav_file` | Valid .wav file passes validation |
| 2 | `test_validate_mp3_file` | Valid .mp3 file passes validation |
| 3 | `test_validate_ogg_file` | Valid .ogg file passes validation |
| 4 | `test_reject_unsupported_format` | .flac, .aac, .m4a rejected |
| 5 | `test_reject_nonexistent_file` | Missing file raises AudioValidationError |
| 6 | `test_reject_directory_as_audio` | Directory path rejected |
| 7 | `test_reject_symlink` | Symlink rejected before resolve |
| 8 | `test_reject_oversized_file` | File > 50 MB rejected |
| 9 | `test_warn_policy_logs_warning` | policy="warn" logs but doesn't raise |
| 10 | `test_ignore_policy_silent` | policy="ignore" skips silently |
| 11 | `test_copy_audio_to_workspace` | Files copied with sfx_ prefix |
| 12 | `test_copy_preserves_extension` | .wav stays .wav after copy |
| 13 | `test_copy_multiple_files` | Multiple files get sequential prefixes |
| 14 | `test_generate_audio_context_single` | Context block for one file |
| 15 | `test_generate_audio_context_multiple` | Context block for multiple files |
| 16 | `test_generate_audio_context_empty` | Empty list returns empty string |

### 6.2 Security Tests — `tests/test_audio_security.py`

| # | Test Name | Description |
|---|-----------|-------------|
| 1 | `test_add_sound_with_allowed_file` | `self.add_sound('sfx_0_thud.wav')` passes |
| 2 | `test_add_sound_with_unknown_file` | `self.add_sound('evil.wav')` rejected |
| 3 | `test_add_sound_with_path_traversal` | `self.add_sound('../../etc/passwd')` rejected |
| 4 | `test_add_sound_with_variable_filename` | `self.add_sound(filename)` rejected (not a literal) |
| 5 | `test_add_sound_with_fstring` | `self.add_sound(f'{name}.wav')` rejected |
| 6 | `test_add_sound_with_concatenation` | `self.add_sound('sfx' + '.wav')` rejected |
| 7 | `test_add_sound_no_args` | `self.add_sound()` rejected |
| 8 | `test_add_sound_with_time_offset` | `self.add_sound('sfx_0_thud.wav', time_offset=1.5)` passes |
| 9 | `test_add_sound_with_gain` | `self.add_sound('sfx_0_thud.wav', gain=-3)` passes |
| 10 | `test_multiple_add_sound_calls` | Multiple valid calls all pass |
| 11 | `test_mixed_valid_invalid_calls` | One bad call fails the whole validation |
| 12 | `test_add_sound_not_on_self` | `other.add_sound('f.wav')` — should this pass? (Decision: skip, not our method) |
| 13 | `test_forbidden_calls_still_blocked` | `open()`, `exec()` still rejected alongside valid `add_sound()` |

### 6.3 Integration Tests — `tests/test_audio_cli.py`

| # | Test Name | Description |
|---|-----------|-------------|
| 1 | `test_cli_sound_effects_flag_parsed` | `--sound-effects a.wav b.mp3` parsed correctly |
| 2 | `test_cli_sound_effects_missing_files` | Non-existent files produce exit code 6 |
| 3 | `test_cli_sound_effects_no_files` | `--sound-effects` with no args handled gracefully |
| 4 | `test_generate_video_with_audio` | Full pipeline with mocked LLM and renderer |
| 5 | `test_audio_context_in_llm_prompt` | Audio context is included in LLM user message |
| 6 | `test_audio_files_copied_to_workspace` | Files appear in workspace dir with sfx_ prefix |
| 7 | `test_combined_images_and_audio` | Both `--image` and `--sound-effects` work together |

### 6.4 LLM Prompt Tests — `tests/test_llm_client.py` (extend existing)

| # | Test Name | Description |
|---|-----------|-------------|
| 1 | `test_audio_context_appended_to_prompt` | audio_context appears in user message |
| 2 | `test_audio_and_image_context_both_present` | Both contexts in prompt, correct order |

---

## 7. Documentation Updates

### 7.1 `manim-animation/docs/user-guide.md`
- Add "Sound Effects" section after "Using Images"
- Document `--sound-effects` flag with examples
- List supported audio formats
- Show example prompts that reference sound effects

### 7.2 `manim-animation/docs/architecture.md`
- Update pipeline diagram to show audio path
- Add audio_handler.py to module descriptions

### 7.3 `manim-animation/docs/development.md`
- Add audio_handler.py to module list
- Document audio validation approach

### 7.4 `manim-animation/docs/testing.md`
- Add test_audio_handler.py and test_audio_security.py to test inventory
- Document audio test fixtures

### 7.5 `manim-animation/docs/troubleshooting.md`
- Add "Audio Issues" section: unsupported formats, missing files, no sound in output

### 7.6 `manim-animation/docs/limitations-and-roadmap.md`
- Update roadmap: sound effects → Phase 0 complete
- Note limitations: no mixing, no narration, SFX only

---

## 8. Implementation Order

```
Step 1: errors.py — Add AudioValidationError
         ↓
Step 2: audio_handler.py — Create new module (validate, copy, context, AST validation)
        tests/test_audio_handler.py — Unit tests (TDD: write tests first)
        tests/test_audio_security.py — Security tests (TDD: write tests first)
         ↓
Step 3: config.py — Add SYSTEM_PROMPT + FEW_SHOT_EXAMPLES changes    ←─── can parallelize
        scene_builder.py — Add audio_filenames param + validation call       with Step 3
         ↓
Step 4: llm_client.py — Add audio_context parameter
         ↓
Step 5: cli.py — Wire everything together (flag, validation, pipeline)
        tests/test_audio_cli.py — Integration tests
         ↓
Step 6: Documentation updates (all 6 docs files)
         ↓
Step 7: Manual smoke test with real audio files
```

### Parallelization Opportunities
- Steps 2 + 3 can run in parallel (no dependency between audio_handler and config/scene_builder changes)
- Step 6 (docs) can start as soon as Step 5 is code-complete
- All test files can be written before implementation (TDD)

### Estimated Total Effort
- New code: ~150 lines (audio_handler.py)
- Modified code: ~80 lines across 5 files
- Test code: ~350 lines across 3 test files
- Documentation: ~100 lines across 6 docs files
- **Total: ~680 lines, ~4-6 hours**

---

## Appendix: Manim `add_sound()` API Reference

```python
# From manim.scene.scene.Scene
def add_sound(
    self,
    sound_file: str,
    time_offset: float = 0,
    gain: float | None = None,
) -> None:
    """
    Add an audio segment to the scene at the current time.

    Parameters
    ----------
    sound_file : str
        Path to audio file (relative to scene working directory)
    time_offset : float
        Seconds after current scene time to start playback
    gain : float | None
        Volume adjustment in dB. None = original volume.
    """
```

Manim embeds audio into the final MP4 via FFmpeg during the render step. No additional post-processing needed.
