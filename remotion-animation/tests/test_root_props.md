# Test Spec: Root.tsx Input Props (Issue #93)

> **Type:** Manual verification (TypeScript/React — not testable via pytest)
> **Component:** `remotion-project/src/Root.tsx`

## Bug Summary

`Root.tsx` hardcodes `durationInFrames`, `fps`, `width`, and `height` instead of
accepting them as input props from the CLI render command. This means the
`--props` JSON passed by `renderer.py` is ignored — the Composition always uses
the hardcoded defaults (150 frames, 30 fps, 1280×720).

## Expected Behavior After Fix

1. **`Root.tsx` reads `inputProps`** via `getInputProps()` from `remotion`.
2. **CLI `--props` override defaults.** When `renderer.py` passes
   `--props={"durationInFrames":300}`, the Composition uses 300 frames.
3. **Defaults still work.** If no props are passed, sensible defaults apply
   (e.g., 150 frames, 30 fps, 1280×720).

## Manual Test Cases

### TC-1: Props forwarded from CLI
- **Steps:**
  1. Run `npx remotion render src/index.ts GeneratedScene out.mp4 --props='{"durationInFrames":300}'`
  2. Inspect rendered video duration.
- **Expected:** Video is 10 seconds (300 frames / 30 fps), NOT 5 seconds (150/30).

### TC-2: Default duration when no props
- **Steps:**
  1. Run `npx remotion render src/index.ts GeneratedScene out.mp4` (no --props).
- **Expected:** Video uses default duration (150 frames = 5s at 30fps).

### TC-3: Quality preset dimensions forwarded
- **Steps:**
  1. Run with `--width=1920 --height=1080 --fps=60 --props='{"durationInFrames":60}'`
  2. Check output video metadata (e.g., `ffprobe`).
- **Expected:** Output is 1920×1080 @ 60fps, 1 second long.

### TC-4: Invalid props handled gracefully
- **Steps:**
  1. Run with `--props='{"durationInFrames":"not_a_number"}'`
- **Expected:** Remotion shows a clear error, not a cryptic crash.

### TC-5: Python renderer integration
- **Steps:**
  1. Call `remotion_gen.renderer.render_video()` with `duration_frames=300`.
  2. Verify the subprocess command includes `--props={"durationInFrames":300}`.
- **Expected:** The `--props` flag in the command matches the requested duration.

## Automated Verification (Python side)

The Python `renderer.py` already passes `--props` with `durationInFrames`.
A pytest in `test_renderer.py` can verify the subprocess command is built
correctly — but the actual TypeScript behavior requires manual or Vitest testing.
