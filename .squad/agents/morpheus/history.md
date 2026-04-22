

## 2026-04-22 - Documentation Review Session

**Session:** Comprehensive review of all 28 documentation files  
**Grade:** B+ (Excellent structure, 6 fixable issues)

Conducted structural consistency review across all 4 projects. Found:
- Perfect 7-doc structure consistency (100%)
- Strong technical accuracy verified by spot-checks
- Critical navigation gap: missing docs/README.md (P0)
- Circular reference in manim limitations doc (P0)
- 4 improvement items for P1-P2 sprints

**Output:** .squad/decisions/inbox/morpheus-doc-review.md - merged to decisions.md

## 2026-07-24 - Architecture & Code Quality Review: image-generation/

**Session:** Full architecture review of `image-generation/` subfolder  
**Grade:** A- (Mature, well-tested, a few structural debts to address)

### Key Findings

**Strengths (what's working well):**
- Pipeline architecture is sound: clean separation of load → configure → infer → cleanup
- Lazy import pattern (`_ensure_heavy_imports()` + PEP 562 `__getattr__`) is elegant — lets `import generate` succeed without GPU stack
- OOM handling with retry + step halving is production-quality
- Batch processing with per-item GPU memory flushes prevents accumulation
- 170 tests across 15 files, all mock-based (no GPU needed) — excellent coverage philosophy
- Security: `_validate_output_path()` blocks directory traversal and absolute paths in batch mode
- CLI design: mutually exclusive `--prompt`/`--batch-file`, custom argparse types with helpful error messages
- Refiner pipeline correctly shares text_encoder_2 and VAE, with proper latent-to-CPU offload between stages
- Makefile is cross-platform (Windows + Unix detection)
- `prompts/examples.md` is an exceptional style guide — color palette, anti-patterns, token budget, checklist

**Issues Found (prioritized):**

| # | Severity | Finding |
|---|----------|---------|
| 1 | P1 | **2 test files import `torch` eagerly** — `test_oom_handling.py` and `test_unit_functions.py` do `import torch` at module level, causing `ModuleNotFoundError` on CPU-only dev machines without torch installed. All other test files use the lazy pattern correctly. |
| 2 | P1 | **6 ruff lint errors** in `test_coverage_gaps.py` — unused imports (`pytest`, `mock_torch`, `mock_makedirs`) and unsorted import block. Clean violations in test code. |
| 3 | P1 | **`_write_tests.py` is a scaffold leftover** — contains a raw string with test code, meant to be run once and deleted. Should be removed from tracked files. |
| 4 | P2 | **Batch JSON files use absolute Windows paths** — `batch_blog_images.json`, `batch_session_storage.json`, `batch_you_have_a_team.json` all hardcode `C:\Users\diberry\...` paths. Works for the author but breaks for any other contributor or CI. |
| 5 | P2 | **`batch_session_storage.json` is an exact duplicate** of `batch_blog_images.json` — identical content, no differentiation. Should be removed or differentiated. |
| 6 | P2 | **`requirements.lock` pins to very old versions** — `torch==2.1.0`, `diffusers==0.21.0` are from late 2023. The `requirements.txt` uses `>=` which is correct, but the lock file hasn't been refreshed. |
| 7 | P3 | **Model revision pinned to `"main"`** — both `load_base()` and `load_refiner()` use `revision="main"` with a TODO comment. For reproducibility, this should be a commit SHA. |
| 8 | P3 | **Single-file architecture** — `generate.py` at 627 lines handles CLI, validation, pipeline loading, inference, batch processing, retry logic, and cleanup. Still manageable but approaching the threshold where extraction would help. |

**Architecture Patterns Noted:**
- Lazy heavy-import guard: `_ensure_heavy_imports()` + `__getattr__` (PEP 562)
- OOM retry with exponential step reduction: `generate_with_retry()` halves steps on each retry
- Pre-flight GPU flush before pipeline loading in `generate()`
- Base→refiner handoff: latents moved to CPU during model swap to prevent VRAM pinning
- `_HIGH_NOISE_FRAC = 0.8` for 80/20 base/refiner split
- Batch validation: schema check → path security check → generation, with per-item error isolation

**Key File Paths:**
- Main CLI: `image-generation/generate.py` (627 lines, single module)
- Test suite: `image-generation/tests/` (15 files, 170 tests)
- Style guide: `image-generation/prompts/examples.md` (comprehensive)
- Design doc: `image-generation/docs/design.md` (living architecture doc)
- Batch configs: `image-generation/batch_*.json` (4 files)
- Lint config: `image-generation/ruff.toml` (E/F/W/I rules, line-length 120)

**Recommendations (ordered by impact):**
1. Fix the 2 torch-importing test files (P1 — breaks CI on CPU-only machines)
2. Clean up ruff lint errors in test_coverage_gaps.py (P1)
3. Delete `_write_tests.py` scaffold (P1)
4. Make batch JSON paths relative or parameterized (P2)
5. Refresh `requirements.lock` (P2)
6. Pin model revisions to commit SHAs (P3)
7. Future: extract `generate.py` into a package when it crosses ~800 lines (P3)
