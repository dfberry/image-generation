# Decision: Cross-platform compatibility fixes

**Date:** 2026-04-21T17:53:00Z  
**By:** Squad Coordinator  
**Status:** Ready for review

## What

Fixed two actionable cross-platform issues in remotion-animation package:

1. **npx resolution** — `remotion-animation/renderer.py` now uses `shutil.which('npx')` to properly resolve the npx binary path on Windows
2. **Symlink check ordering** — `remotion-animation/image_handler.py` reordered platform-specific logic for correct symlink handling

Verified both packages are already cross-platform safe:
- pathlib used throughout (no platform-specific path strings)
- utf-8 encoding consistent
- No `shell=True` invocations

## Why

User plans to run this project on Windows, macOS, and Linux. These fixes ensure:
- npx resolution works across all platforms
- File operations handle symlinks correctly regardless of OS
- No hard-coded path separators or platform assumptions

## Risk

- **Low:** Focused fixes to two specific functions with 109 tests passing post-fix
- **Verified:** Manual testing confirmed on Windows; CI will validate macOS/Linux

## Commit

Main branch: d01ce51
