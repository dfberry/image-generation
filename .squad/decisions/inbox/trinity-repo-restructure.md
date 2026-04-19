# Trinity: Repo Restructure Execution

**By:** Trinity (Backend Dev)
**Date:** 2026-04-19
**Status:** Complete
**Branch:** `squad/repo-restructure-subfolders`

---

## What Was Done

Executed Morpheus's restructure plan to move the image generation system into an `image-generation/` subfolder and create an empty `mermaid-diagrams/` folder for future use.

### Files Moved → `image-generation/`

- generate.py, generate_blog_images.sh
- prompts/, outputs/, tests/, docs/
- requirements.txt, requirements-dev.txt, requirements.lock
- ruff.toml, Makefile, _write_tests.py, CONTRIBUTING.md
- All 4 batch_*.json files
- README.md (now tool-specific)

### Files Updated

| File | Change |
|------|--------|
| `.github/workflows/tests.yml` | Added `working-directory: image-generation` to ruff, install, and test steps |
| `.gitignore` | Updated output patterns to `image-generation/outputs/*` |
| `CODEOWNERS` | Added `image-generation/` prefix to file-specific patterns |
| `image-generation/tests/conftest.py` | Added `sys.path.insert(0, ...)` for cross-directory import resolution |
| `.squad/team.md` | Updated project context to reflect multi-tool structure |
| `.squad/identity/now.md` | Updated focus area to restructure work |

### Files Created

| File | Purpose |
|------|---------|
| `README.md` (root) | Project overview pointing to tool subfolders |
| `mermaid-diagrams/README.md` | Placeholder so git tracks the empty folder |

### Files NOT Moved (by design)

- `.squad/`, `.github/` — shared infrastructure
- `.gitattributes`, `.gitignore`, `CODEOWNERS` — project-wide config
- `image-generation-improvements.md`, `performance-optimization.md` — project-level planning
- `venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` — local/transient

## Verification

- `git mv` used for all tracked files to preserve history
- `python -m pytest image-generation/tests/ -v --co` from repo root: **219 tests collected**
- 2 collection errors are pre-existing (`torch` not installed locally) — not caused by restructure
- All `from generate import ...` imports resolve via conftest.py sys.path insert

## Decisions Made

1. **CI approach:** Used `working-directory: image-generation` per-step rather than path prefixes. Keeps relative paths working naturally inside the tool folder.
2. **conftest.py sys.path:** Added explicit `sys.path.insert` pointing to parent dir. This ensures imports work whether pytest is invoked from repo root or `image-generation/`.
3. **Shell script paths:** NOT updated internally — since `generate_blog_images.sh` moved into `image-generation/` alongside `generate.py`, all its relative paths (venv activation, generate.py call) remain correct when run from that directory.
4. **Batch JSON paths:** NOT modified — they use relative `outputs/` paths which remain correct within the `image-generation/` working directory.
