# Repo Restructure Plan: Multi-Tool Architecture

**By:** Morpheus (Lead)  
**Date:** 2026-03-23  
**Status:** Ready for Implementation  
**Priority:** IMMEDIATE (blocks multi-tool expansion)

---

## Executive Summary

The repo is being restructured to support multiple tools beyond just image generation. The current flat layout must be reorganized so that:
1. Image generation system moves into `image-generation/` subfolder
2. Future tools (e.g., mermaid diagrams) get their own subfolders at root
3. Shared infrastructure (`.squad/`, `.github/`, `README.md`) remains at root

**Total path references to update: 23 files across 6 categories.**

---

## Proposed Folder Layout

```
image-generation/
├── image-generation/           [NEW SUBFOLDER]
│   ├── generate.py             [MOVE from root]
│   ├── generate_blog_images.sh [MOVE from root]
│   ├── prompts/                [MOVE from root]
│   ├── outputs/                [MOVE from root]
│   ├── tests/                  [MOVE from root]
│   ├── requirements.txt         [MOVE from root]
│   ├── requirements-dev.txt     [MOVE from root]
│   ├── requirements.lock        [MOVE from root]
│   ├── ruff.toml               [MOVE from root]
│   ├── Makefile                [MOVE from root]
│   ├── batch_*.json            [MOVE from root] (4 files)
│   ├── _write_tests.py         [MOVE from root]
│   ├── docs/                   [MOVE from root]
│   ├── CONTRIBUTING.md         [MOVE from root]
│   ├── README.md               [MOVE from root — tool-specific README]
│   └── .gitignore              [MOVE from root — tool-specific]
│
├── mermaid-diagrams/           [NEW SUBFOLDER]
│   └── (empty, ready for future diagrams)
│
├── .squad/                     [STAY at root]
├── .github/                    [STAY at root]
├── .gitattributes              [STAY at root]
├── .gitignore                  [STAY at root — project-wide]
├── CODEOWNERS                  [STAY at root — project-wide]
├── image-generation-improvements.md  [STAY at root — project-level planning]
├── performance-optimization.md      [STAY at root — project-level planning]
└── ROOT_README.md              [NEW: project-level overview]
```

---

## Rationale for File Placement

### Image-generation/ Subfolder Contents

**Reason:** Isolates image-gen tooling so future tools can coexist without namespace conflicts.

- **generate.py** — Core CLI; must move
- **generate_blog_images.sh** — Batch wrapper; must move  
- **prompts/** — Prompt library (image-gen specific); must move
- **outputs/** — Image outputs (image-gen specific); must move
- **tests/** — Test suite (image-gen specific); must move
- **requirements.txt, requirements-dev.txt, requirements.lock** — Image-gen dependencies; must move
- **ruff.toml** — Image-gen lint config (will need tool exclusions); should move or be tool-agnostic
- **Makefile** — Image-gen build tasks; should move
- **batch_*.json** — Batch configs; must move (all 4 files are image-gen configs)
- **_write_tests.py** — Test helper; must move
- **docs/** — Tool-specific documentation; should move
- **CONTRIBUTING.md** — Tool-specific development guide; should move
- **README.md** — Tool README; should move (project gets a new root README)
- **.gitignore** — Tool-specific patterns (`outputs/`, `models/`); should move

### Root-Level Files (Stay)

- **.squad/** — Cross-tool team memory and decisions; shared infrastructure
- **.github/** — CI/workflows; shared infrastructure for all tools
- **.gitattributes** — Cross-repo text handling (Makefile CRLF); shared infrastructure
- **.gitignore** — Project-wide ignore rules (`.venv/`, `.DS_Store`, IDE files); shared
- **CODEOWNERS** — Project ownership (will need updates to reference subfolder paths); shared
- **image-generation-improvements.md** — Project-level planning (not tool-specific); stays
- **performance-optimization.md** — Project-level planning (not tool-specific); stays
- **ROOT_README.md** (NEW) — Top-level tool discovery and onboarding (replaces current README at root)

---

## Breaking Path References: Complete Inventory

### Category 1: Python Imports (Test Files) — 12 files

**Impact:** Test discovery and imports will fail if tests remain at root but generate.py moves.

**Affected Files (all in `tests/`):**
1. **tests/conftest.py** — No explicit path; shared fixtures OK as-is
2. **tests/test_batch_cli.py** — `import generate` → needs sys.path adjustment or becomes `from generate import ...`
3. **tests/test_batch_generation.py** — `from generate import batch_generate` → needs sys.path
4. **tests/test_bug_fixes.py** — `from generate import ...` (3 imports) → needs sys.path
5. **tests/test_cli_validation.py** — `from generate import ...` (3 imports) → needs sys.path
6. **tests/test_coverage_gaps.py** — `import generate as gen_module` and `from generate import ...` → needs sys.path
7. **tests/test_input_validation.py** — `import generate as gen_module` and `from generate import ...` → needs sys.path
8. **tests/test_memory_cleanup.py** — `import generate as gen` → needs sys.path
9. **tests/test_negative_prompt.py** — `from generate import ...` (3 imports) → needs sys.path
10. **tests/test_oom_handling.py** — `from generate import OOMError` (2 imports) → needs sys.path
11. **tests/test_oom_retry.py** — `from generate import ...` (2 imports) → needs sys.path
12. **tests/test_pipeline_enhancements.py** — `from generate import ...` (4 imports) → needs sys.path
13. **tests/test_scheduler.py** — `from generate import ...` and `import generate as gen` (7 imports) → needs sys.path
14. **tests/test_security.py** — `from generate import batch_generate` → needs sys.path
15. **tests/test_unit_functions.py** — `import generate as gen` and `from generate import ...` (2 imports) → needs sys.path

**Fix Strategy:**
- **Option A (Preferred):** Move `tests/` into `image-generation/tests/`; pytest auto-discovers and imports work (conftest.py auto-loaded)
- **Option B:** Add sys.path manipulation in `tests/conftest.py` to resolve parent `generate` module
- **Option C:** Install `image-generation/` as an editable package; requires `setup.py` or `pyproject.toml`

**Recommendation:** **Option A.** Keeps tests co-located with code; pytest treats `tests/conftest.py` as test root.

---

### Category 2: Shell Script Path References — 1 file

**Impact:** Shell script runs generate.py from wrong location after move.

**Affected File:**
1. **generate_blog_images.sh** (line 52):
   ```bash
   python -u generate.py --batch-file "$BATCH_FILE" 2>&1 | tee -a generation.log
   ```
   **Fix:** Change to:
   ```bash
   python -u image-generation/generate.py --batch-file "$BATCH_FILE" 2>&1 | tee -a generation.log
   ```
   OR (if script moves into image-generation/):
   ```bash
   python -u generate.py --batch-file "$BATCH_FILE" 2>&1 | tee -a generation.log
   ```
   
   **Also Line 15:** Script activates venv from `venv/bin/activate`:
   ```bash
   source venv/bin/activate
   ```
   **Fix if script stays at root:** Change to:
   ```bash
   source ./image-generation/venv/bin/activate  # OR ../venv if script moves
   ```

---

### Category 3: Batch JSON Files (Output Paths) — 4 files

**Impact:** Batch JSON files contain hardcoded output paths; these will break after folder move.

**Affected Files:**
1. **batch_blog_images.json** (lines 5, 11, 17, 23, 29):
   ```json
   "output": "C:\\Users\\diberry\\project-dfb\\dfberry.github.io\\website\\blog\\media\\..."
   ```
   **Fix:** These are absolute paths to external blog directory; they don't break BUT should be updated to relative paths:
   ```json
   "output": "outputs/01.png"  # relative to image-generation/ after move
   ```

2. **batch_blog_images_v2.json** — Check for similar absolute paths (need to view)
3. **batch_session_storage.json** — Check for paths (need to view)
4. **batch_you_have_a_team.json** — Check for paths (need to view)

**Note:** These are user-configuration files; relative paths should point to `outputs/` subfolder.

---

### Category 4: CI Workflow Paths — 1 file

**Impact:** GitHub Actions CI commands will run from wrong working directory.

**Affected File:**
1. **.github/workflows/tests.yml** (lines 33, 52, 56):
   - Line 33: `ruff check .` → points to repo root; needs to check `image-generation/` specifically
   - Line 52: `pip install -r requirements-dev.txt` → points to root; needs `image-generation/requirements-dev.txt`
   - Line 56: `python -m pytest tests/ -v --cov=generate --cov-report=term-missing` → points to root `tests/`; needs `image-generation/tests/`

   **Fixes:**
   ```yaml
   - name: Run ruff
     run: ruff check image-generation/
   
   - name: Install dependencies
     run: |
       pip install torch --index-url https://download.pytorch.org/whl/cpu
       pip install -r image-generation/requirements-dev.txt
   
   - name: Run tests
     run: python -m pytest image-generation/tests/ -v --cov=image_generation.generate --cov-report=term-missing
   ```

---

### Category 5: Configuration Files — 3 files

#### 5a. Makefile (affects test, lint, format targets)

**Affected File:** `image-generation/Makefile` (after move)

**Lines 26, 29, 32, 35, 38:**
```makefile
install:
	$(PIP) install -r requirements.txt           # Line 26 — relative path OK after move

install-dev:
	$(PIP) install -r requirements-dev.txt       # Line 29 — relative path OK after move

test:
	$(PYTHON) -m pytest tests/ -v                # Line 32 — relative path OK after move

lint:
	$(PYTHON) -m ruff check .                    # Line 35 — OK (checks current dir)

format:
	$(PYTHON) -m ruff format .                   # Line 38 — OK (formats current dir)
```

**Fix:** No changes needed IF Makefile moves into `image-generation/` (relative paths work). If Makefile stays at root and must work from root, update paths:
```makefile
test:
	$(PYTHON) -m pytest image-generation/tests/ -v
```

**Recommendation:** Move Makefile into `image-generation/`; developers run `make` from that directory.

---

#### 5b. ruff.toml

**Affected File:** `image-generation/ruff.toml` (after move)

**Line 3:** `exclude = ["venv", "__pycache__", "outputs"]`

**Fix:** Paths are relative; they work after move (will exclude `image-generation/venv`, `image-generation/__pycache__`, `image-generation/outputs`). No change needed IF file moves into subfolder.

BUT, if `ruff.toml` stays at root to cover entire repo, update to:
```toml
exclude = ["venv", "__pycache__", "outputs", "image-generation/venv", "image-generation/__pycache__"]
```

**Recommendation:** Move `ruff.toml` into `image-generation/`; project-wide lint config can live at root later if needed.

---

#### 5c. .gitignore

**Current Root .gitignore (lines 25–27):**
```
outputs/*.png
outputs/*.jpg
outputs/*.webp
```

**Issue:** These patterns only work at root. After move, images go to `image-generation/outputs/`.

**Fix:** Either:
- **Option A:** Keep root `.gitignore` with updated patterns:
  ```
  image-generation/outputs/*.png
  image-generation/outputs/*.jpg
  image-generation/outputs/*.webp
  ```
- **Option B:** Move `.gitignore` into `image-generation/` with original patterns; git respects folder-level `.gitignore` files.

**Recommendation:** Keep `.gitignore` at root for project-wide patterns (venv, IDE, model weights); add `image-generation/`-specific patterns there.

---

### Category 6: Documentation & Configuration — 2 files

#### 6a. CODEOWNERS

**Affected File:** `CODEOWNERS` (stays at root)

**Current:**
```
* @dfberry
generate.py @dfberry
generate_blog_images.sh @dfberry
tests/ @dfberry
prompts/ @dfberry
```

**Fix:**
```
* @dfberry
image-generation/generate.py @dfberry
image-generation/generate_blog_images.sh @dfberry
image-generation/tests/ @dfberry
image-generation/prompts/ @dfberry
```

---

#### 6b. README.md

**Current:** Root `README.md` is tool-specific (image generation docs).

**Fix Strategy:**
1. Create **ROOT_README.md** (new file at root) with project-level overview:
   ```markdown
   # Project: Multi-Tool Media Generation Suite
   
   This repository contains multiple media generation tools.
   
   ## Tools
   
   - **image-generation/** — Stable Diffusion XL image generation with batch processing
   - **mermaid-diagrams/** — (Planned) Diagram generation from text
   
   ## Getting Started
   
   See the README in each tool's folder for setup and usage.
   
   ### Development
   
   See `.squad/agents/` for team member guidance and `.squad/decisions.md` for architecture decisions.
   ```

2. Move current `README.md` → `image-generation/README.md` (tool-specific docs)

---

### Category 7: Import Path Updates in generate.py — 1 file

**Affected File:** `generate.py` itself (path operations)

**Lines 81–82:**
```python
os.makedirs("outputs", exist_ok=True)
output_path = f"outputs/image_{timestamp}.png"
```

**Issue:** After move to `image-generation/`, these relative paths still work (they refer to `image-generation/outputs/`).

**Conclusion:** No changes needed IF paths are truly relative and move with the module.

**Check Point:** Search for any hardcoded paths like `/project-dfb/` or `~/image-gen/` — **none found in grep.**

---

## Summary: Files Requiring Changes

| # | Category | File | Change | Risk | Priority |
|---|----------|------|--------|------|----------|
| 1 | Imports | tests/*.py (15 files) | Add sys.path or move tests/ into image-generation/ | HIGH | P0 |
| 2 | Shell Script | generate_blog_images.sh | Update `python -u generate.py` → `python -u image-generation/generate.py` | MEDIUM | P0 |
| 3 | Batch Config | batch_*.json (4 files) | Review absolute paths; convert to relative if needed | LOW | P1 |
| 4 | CI/CD | .github/workflows/tests.yml | Update ruff check path, pip install path, pytest path | HIGH | P0 |
| 5 | Makefile | image-generation/Makefile (MOVE) | No internal changes; relative paths work after move | NONE | P0 (move) |
| 6 | Linter Config | image-generation/ruff.toml (MOVE) | No changes if moved; exclude patterns are relative | NONE | P0 (move) |
| 7 | .gitignore | Root .gitignore | Update to `image-generation/outputs/*.png` | LOW | P1 |
| 8 | Ownership | CODEOWNERS | Add `image-generation/` prefix to paths | TRIVIAL | P1 |
| 9 | Documentation | README.md | Create ROOT_README.md; move current to image-generation/README.md | NONE | P1 |
| 10 | generate.py | generate.py | Check for hardcoded absolute paths (NONE FOUND) | NONE | — |

---

## Implementation Order

1. **Phase 1 (Immediate — P0):**
   - Create `image-generation/` folder
   - Create `mermaid-diagrams/` folder (empty)
   - Move files into `image-generation/` (except .squad, .github, root docs)
   - Test local imports work (or add sys.path in conftest.py)

2. **Phase 2 (Day 1 — P0):**
   - Update `.github/workflows/tests.yml` paths (ruff, pip, pytest)
   - Update `generate_blog_images.sh` to call `image-generation/generate.py`
   - Test CI passes with new structure

3. **Phase 3 (Day 2 — P1):**
   - Review and update batch_*.json files (absolute paths → relative)
   - Update CODEOWNERS
   - Create ROOT_README.md; move current README to `image-generation/README.md`
   - Update `.gitignore` patterns

4. **Phase 4 (Day 3 — Verification):**
   - Dry run full workflow: `make setup install-dev test lint`
   - Verify CI/CD passes
   - Spot-check batch generation still works
   - Commit with clear message: "refactor: move image-generation into subfolder; prepare for multi-tool structure"

---

## Edge Cases & Gotchas

### Gotcha 1: pytest Discovery
- **Issue:** If `tests/` stays at root, pytest won't auto-discover `conftest.py` when generate.py moves
- **Fix:** Move `tests/` into `image-generation/` so pytest finds `image-generation/tests/conftest.py`

### Gotcha 2: Relative Paths in Batch JSON
- **Issue:** Batch JSON output paths currently use absolute Windows paths (lines in batch_blog_images.json)
- **Fix:** Convert to relative paths so users can generate anywhere: `"output": "outputs/image_$(date +%s).png"`

### Gotcha 3: Shell Script Activation
- **Issue:** `generate_blog_images.sh` activates venv from `venv/bin/activate`; path breaks after folder move
- **Fix:** Update line 15 to either move script into `image-generation/` or use `source ./image-generation/venv/bin/activate`

### Gotcha 4: GitHub Actions Working Directory
- **Issue:** CI runs from repo root; paths in workflow YAML must be absolute from root
- **Fix:** `ruff check image-generation/`, `pip install -r image-generation/requirements-dev.txt`, etc.

### Gotcha 5: CODEOWNERS Path Matching
- **Issue:** CODEOWNERS uses glob patterns; moving files requires updating patterns
- **Fix:** `image-generation/tests/` (with trailing slash for folders)

---

## Open Questions Resolved

**Q: Should Makefile move or stay at root?**  
A: **Move into `image-generation/`.** Developers run build tasks from the tool folder. If root Makefile needed later for orchestration, create a separate one.

**Q: Should conftest.py stay at root or move?**  
A: **Move into `image-generation/tests/`.** pytest auto-discovers it; test modules no longer need sys.path hacks.

**Q: Should .gitignore split into two files?**  
A: **Keep at root for project-wide patterns; add image-generation/ prefixes.** Later, if tool-specific ignores needed, create `image-generation/.gitignore`.

**Q: Do batch JSON files need updating?**  
A: **Yes.** Current absolute Windows paths will break if repo moves. Convert to relative paths in Phase 3.

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| CI tests fail after move | HIGH | Blocks merge | Test locally first; update all 3 paths in tests.yml |
| Batch generation breaks | MEDIUM | Users can't generate | Verify batch_*.json paths; test end-to-end |
| Shell script fails | MEDIUM | Blocks blog pipeline | Update generate_blog_images.sh before merge |
| Test discovery fails | HIGH | CI can't find tests | Move tests/ or add sys.path; validate with `pytest --collect-only` |
| Import errors in tests | HIGH | All 15 tests fail | Use conftest.py sys.path workaround or move tests/ |

---

## Sign-Off Checklist

Before implementation, verify:
- [ ] All 4 batch JSON files reviewed for absolute paths
- [ ] Makefile tested locally after move
- [ ] sys.path solution tested (conftest.py vs moving tests/)
- [ ] CI workflow syntax checked
- [ ] Shell script tested locally
- [ ] CODEOWNERS patterns validated
- [ ] ROOT_README.md drafted
- [ ] .gitignore patterns tested (can still ignore outputs/)

---

## Rationale

**Why now?** The project cannot scale to multiple tools with a flat root structure. Image-gen tools must be isolated so:
1. Future mermaid diagrams tool doesn't depend on image-gen infrastructure
2. Each tool can have independent CI, docs, dependencies
3. Team can add tools without repo sprawl

**Why this layout?** Standard multi-tool monorepo pattern: each tool in own folder, shared infrastructure at root, single CODEOWNERS and CI orchestration.

**Why move everything at once?** Phased moves risk intermediate states where some tests pass, some break. A coordinated move + comprehensive update is cleaner and lower risk.

