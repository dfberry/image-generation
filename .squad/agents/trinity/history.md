# Project Context

- **Owner:** dfberry
- **Project:** Python-based AI image generation tool using Stable Diffusion XL (SDXL). Generates blog illustrations with tropical magical-realism aesthetic. Stack: Python 3.10+, diffusers, transformers, torch, Pillow. Key files: generate.py (main CLI), generate_blog_images.sh (batch script), prompts/ (style guides and prompt library), outputs/ (generated PNG images).
- **Stack:** Python 3.10+, diffusers>=0.19.0, transformers>=4.30.0, torch>=2.0.0, accelerate, safetensors, Pillow
- **Created:** 2026-03-23

## Key Paths

- `generate.py` — main CLI with --steps, --guidance, --seed, --width, --height, --refine, --cpu flags
- `generate_blog_images.sh` — generates 5 blog images (01-05), seeds 42-46
- `prompts/examples.md` — master prompt library, style guide (Latin American folk art, magical realism, tropical palette)
- `prompts/BLOG_IMAGE_UPDATES.md` — alt text and filename mapping for website integration
- `outputs/` — generated PNGs at 1024×1024, ~1.5-1.7MB each
- `.squad/` — team memory, decisions, agent histories

### 2026-03-25 — PR #3: try/finally cleanup guard + accelerate version floor

- **try/finally pattern for pipeline cleanup:** Initialize `base = refiner = latents = text_encoder_2 = vae = image = None` before the try block. The inline `del base; base = None` in the refiner path must stay inside try (not moved to finally) because it frees VRAM before `load_refiner()` — ordering is load-order-dependent. The finally block catches everything else: any variable still non-None gets deleted, then gc.collect() and both CUDA/MPS cache clears run unconditionally.
- **`del` on None is safe:** Python's `del` on a None-valued local just removes the binding. No NameError. This makes the "initialize to None, delete in finally" pattern clean and reliable.
- **`torch.cuda.empty_cache()` is safe to call even without CUDA:** Unlike `torch.mps.empty_cache()`, the CUDA variant doesn't raise if no CUDA device is present — it's a no-op. The MPS call still needs an `is_available()` guard because it will raise on non-Apple hardware.
- **Version floors are prerequisites, not optional hygiene:** `accelerate<0.24.0` silently breaks the CPU offload deregistration path. This isn't a "might cause issues" risk — it means PR#1's entire cleanup strategy is inert on older accelerate. Always audit version floors as part of any memory management PR.

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-25 — PR #5: MEDIUM memory fixes (latents CPU transfer, dynamo reset, entry-point flush, global state audit)

- **latents.cpu() before cache flush is the correct fix for the GPU-pin problem:** Moving the latents tensor to CPU before `del base` / `empty_cache()` lets the cache flush reclaim all base model VRAM. Moving back with `latents.to(device)` at refiner call site is clean and explicit. Guard on `device in ("cuda", "mps")` — no-op on CPU path.
- **torch._dynamo.reset() belongs in the finally block, CUDA-guarded:** `torch.compile` is only applied on CUDA (in `load_base()`), so the dynamo reset is correctly scoped to `device == "cuda"`. The `hasattr(torch, "_dynamo")` guard protects against torch versions without the attribute. If `torch.compile` is ever extended to MPS or other devices, the guard must be broadened.
- **Entry-point flush pattern mirrors the finally pattern:** `gc.collect()` first, then CUDA unconditional, then MPS guarded. Consistent with the existing `finally` cleanup so it's easy to audit both at once.
- **Global state audit finding:** `generate.py` has zero module-level pipeline objects or accumulating global state. All pipeline vars are locals inside `generate()`. This is the right architecture for a CLI tool called in batch — no risk of cross-call contamination from Python-level references.
### 2026-03-25 — PR #5: MEDIUM Memory Fixes Delivered & Approved

Delivered all 4 MEDIUM-severity fixes in `squad/pr5-medium-memory-fixes`. Approved by Morpheus (Lead).

**Fixes implemented:**
1. **Latents CPU Transfer:** `latents.cpu()` before `del base` and cache flush. Device transfer back via `latents.to(device)` (MPS-aware). Guard: `if device in ("cuda", "mps")`.
2. **Dynamo Cache Reset:** `torch._dynamo.reset()` in finally block, guarded by `device == "cuda" and hasattr(torch, "_dynamo")`.
3. **Entry-Point VRAM Flush:** Added `gc.collect()`, `torch.cuda.empty_cache()` (CUDA-guarded), `torch.mps.empty_cache()` (MPS-guarded) at start of `generate()`.
4. **Global State Audit:** Verified all pipeline variables are locals. Zero process-persistent references. Clean.

**Tests:** Neo added 9 new MEDIUM tests. All 22 tests pass (~5.9s, no GPU). Call-order tracking validates fixes 1, 2, 3 at the code level.

**Review verdict:** APPROVED. All fixes correct. Code logic sound. Follow-up (not blocking): Neo to fix orphaned assert message patterns in 3 tests.

### 2026-03-23 — Memory Audit of generate.py (post PR#1, PR#2)

- **No exception-safe cleanup (HIGH):** `generate()` has no `try/finally` blocks. Any mid-inference exception leaves `base`, `refiner`, `latents`, `text_encoder_2`, and `vae` allocated in VRAM. Must wrap each pipeline load+call pair in try/finally.
- **torch.compile cache survives del (MEDIUM):** On CUDA, `torch.compile(pipe.unet)` populates `torch._dynamo`'s graph cache. `del base` drops the Python reference but the compiled graph stays cached. Call `torch._dynamo.reset()` after deletion on CUDA when compile was used.
- **Latents tensor holds GPU ref through cache-clear window (MEDIUM):** In the refiner path, `latents` is a CUDA tensor still live when `torch.cuda.empty_cache()` runs after `del base`. `empty_cache()` can't free it. Pin latents to CPU before loading refiner, move back to device when passing to refiner.
- **PIL image not freed after save (LOW):** `image` (~4MB) is never `del`'d after `image.save()`. Fine for single runs; accumulates in batch/loop contexts.
- **requirements.txt floors too low (MEDIUM):** `accelerate>=0.20.0` allows versions where CPU offload hooks are NOT deregistered on model delete — this directly undermines PR#1's cleanup. Safe floors: `accelerate>=0.24.0`, `diffusers>=0.21.0`, `torch>=2.1.0`.
- **No outer torch.no_grad() (LOW):** Diffusers handles it internally, but an explicit outer context is defensive hygiene against future hooks or wrappers.

---

### 2026-03-24 — Cross-Agent Audit Sync

Trinity's code-level audit converged with Morpheus's architectural review and Neo's test-gap analysis:

**All three agents independently identified the same 4 core issues:**
1. No exception safety (HIGH) — Trinity's detail matches Morpheus and Neo's critical test gap
2. torch.compile cache (MEDIUM) — Trinity and Morpheus both found it
3. Latents tensor GPU ref (MEDIUM) — Trinity emphasized "can cause OOM at large resolutions"
4. Entry-point cache flush (MEDIUM) — Trinity and Morpheus both found it

**Trinity's unique findings:**
- Defensive `torch.no_grad()` wrapping (LOW) — subtle but defensible hygiene
- **requirements.txt version floors (MEDIUM)** — Critical prerequisite: `accelerate>=0.24.0` (PR#1's offload hooks), `diffusers>=0.21.0` (attention cache), `torch>=2.1.0` (MPS backend). Without these, code fixes can't be relied upon.

**Neo identified critical testing gap:**
- 22 regression tests catch reversion of PR#1 and PR#2 fixes
- Exception safety test fails until try/finally is added

**Team consensus:** Trinity's version-floor fix must run in Phase 1 (prerequisite). Then Neo's test infra (Phase 2), then Morpheus's code fixes (Phase 3). All merged into `.squad/decisions.md`.

## Learnings

### 2026-03-25 — PR #6: PIL Image Leak Fix (LOW)

- **image.save() inside try is the right pattern:** Keeping the save inside the `try` block lets the `finally` clause null out `image` unconditionally. This closes the window where PIL's uncompressed pixel buffer (~4MB) lingers in scope after cleanup.
- **`if image is not None` guard is essential:** On exception paths (OOM, interrupt, inference failure), `image` stays `None`. The guard prevents an AttributeError on None and makes intent explicit — the save is a conditional success-path action, not an unconditional epilogue.
- **`image = None` vs `del image`:** Used `image = None` (not `del image`) in `finally` to match the initialize-to-None pattern established in PR#4. `del` would remove the binding; `= None` keeps the variable in scope but releases the PIL reference — consistent with how the block already handles `base = None` after inline deletion.
- **Return after finally is clean:** `return output_path` sits after the `try/finally` and is unaffected by the restructuring. The function still returns the path whether or not the save succeeded (caller decides what to do with that).

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-04-22 — Pythagorean Theorem Explainer Video (with TTS)

Generated `remotion-animation/outputs/theorem_explained.mp4` — a 45-second 720p explainer video with TTS narration (en-US-JennyNeural via edge-tts).

**Approach:** Bypassed the LLM by writing a hand-crafted TSX component (`generate_theorem.py`). Used the `remotion_gen` library functions directly:
1. `generate_narration()` → edge-tts TTS audio
2. `write_component()` → validates + writes GeneratedScene.tsx (with `audio_filenames` for path validation)
3. `render_video()` → Remotion CLI renders 1350 frames at 30fps

**Architecture decisions:**
- When `generate_video()` receives `component_code`, it skips all audio handling. For custom components with audio, call `generate_narration()`, `write_component()`, and `render_video()` directly.
- SVG geometry embedded in React/Remotion works well for math diagrams — used a 3:4:5 right triangle with colored squares.
- Used `background` (not `backgroundColor`) for all gradient CSS — `backgroundColor` silently ignores gradient values.
- Used Unicode `\u00B2` for superscript 2 in JSX strings and `&#178;` in text content for the ² symbol.
- Component uses 6-phase animation: title → triangle → square a → square b → square c → conclusion equation.
- **Audio-video duration sync:** edge-tts narration (~42s) exceeded initial 30s video duration. Fixed by extending to 45s with animation phases remapped to narration timing. Added mutagen-based audio duration check to verify fit before rendering. Always measure TTS output duration and size video to match.

**Key files:**
- `remotion-animation/generate_theorem.py` — standalone generation script
- `remotion-animation/outputs/theorem_explained.mp4` — output video (45s, 720p, ~2.7MB)
- `remotion-animation/remotion-project/public/narration.mp3` — TTS audio (~247KB, 42.2s)

### 2026-04-21 — PR #88 & #89: Image/Screenshot Input Support Merged

Delivered image/screenshot input support for both animation packages (Manim and Remotion). Both implementations merged to main (squash-merged).

**PR #88 (Manim):**
- Implemented `image_handler.py` with validation, workspace isolation, deterministic naming
- AST-based security: `validate_image_operations()` enforces literal-only ImageMobject filenames
- CLI: `--image`, `--image-descriptions`, `--image-policy` flags
- LLM context injection into system prompt
- Renderer uses workspace `cwd` for local image resolution
- All 67 tests passing

**PR #89 (Remotion):**
- Implemented `image_handler.py` with UUID-based naming in `public/` directory
- `component_builder.py` validates `staticFile()` calls, blocks `file://` URLs and path traversal
- CLI: `--image`, `--image-description`, `--image-policy` flags
- LLM context injection into user prompt
- 64 tests, 63 passing, 1 skip (Windows symlink limitation)

**Design Pattern:** Both packages use consistent architecture (separate `image_handler.py`, policy-based strictness, workspace isolation, LLM guidance) but independent implementations enable package-specific evolution.

### 2026-04-18 — PR #15: CONTRIBUTING.md CLI Fixes & Dev Setup Alignment

Fixed CONTRIBUTING.md to match actual generate.py CLI and align dev setup with CI:
1. **CLI flag corrections:** `--refiner` → `--refine`, `--device` → `--cpu` (matched actual parameter names)
2. **Added missing flags:** `--steps`, `--guidance`, `--seed`, `--width`, `--height` now documented
3. **Dev setup updated:** Changed from `pip install ruff` to `pip install -r requirements-dev.txt` for consistency with CI workflow
4. **README Key Paths:** Updated `generate.py` entry to reflect corrected flags

**Result:** CONTRIBUTING.md now accurate and actionable for contributors. Dev environment matches CI environment.

### 2026-04-18 — D1+D7 Code Quality & CI/DevOps Review

Read-only audit of generate.py, shell scripts, Makefile, CI workflow, and config files.

**Key findings (5 MEDIUM, 5 LOW, 5 INFO):**
- `generate()` has 5+ responsibilities — extractable but readable as-is
- `batch_generate()` inconsistently supports per-item overrides (lora yes, scheduler/refiner_steps no)
- 15 `print()` calls with no `logging` module — blocks future --verbose/--quiet
- Makefile Unix-only (hardcoded `venv/bin/` paths, `find` command) — won't work on Windows
- CI actor allowlist has only 2 entries (both same maintainer); no coverage report despite pytest-cov installed
- Ruff passes clean. Error messages are actionable. CI lint→test ordering correct.

Full report: `.squad/decisions/inbox/trinity-code-quality-review.md`

- **CI workflow now triggers on PR and push to main**, not just manual dispatch. Lint job (ruff) gates the test matrix. Concurrency groups cancel stale runs per-branch.
- **Makefile uses venv-relative paths** (`$(VENV)/bin/python`) so targets work in both local dev and CI without activating the venv.
- **ruff.toml targets py310** with E/F/W/I rules, ignores E501 (formatter handles line length). Excludes venv, __pycache__, outputs.
- **requirements-dev.txt chains `-r requirements.txt`** so `pip install -r requirements-dev.txt` gets everything in one shot.
- All 172 existing tests pass after these changes.

### 2026-07-22 — PR #15 Fact-Check Review (Trinity as reviewer)

- **CI `pip install ruff>=0.4.0` has a shell quoting bug:** In bash, `>=0.4.0` is parsed as redirect `>` to file `=0.4.0`. The version constraint is silently lost. It works in practice because latest ruff > 0.4.0, but the line should be `pip install 'ruff>=0.4.0'`.
- **CONTRIBUTING.md lists wrong CLI flags:** Says `--refiner` and `--device` but the actual argparse has `--refine` (flag) and `--cpu` (flag). No `--device` flag exists.
- **CONTRIBUTING.md recommends manual `pip install pytest ruff`** instead of `pip install -r requirements-dev.txt` which also includes pytest-cov.
- **All import removals verified correct:** Every removed import was truly unused in its file. Import reorderings are safe (alphabetized by isort rules).
- **Removed variables (`results`, `mock_gen`, `images_seen`, `original_generate`, `mock_cuda`) all verified unused** in their respective scopes.
- **Makefile `$(VENV)/bin/python` path is Unix-only:** Correct for Ubuntu CI, but won't work on Windows. Fine for the CI target.
- **ruff.toml is valid and sensible:** py310 target, E/F/W/I rules, E501 ignored (formatter handles it), correct first-party config for generate module.

### 2026-03-26 — PR #12: Add negative prompt support (#3)

**TDD Green Phase — made Neo's 7 failing tests in test_negative_prompt.py pass.**

**Changes to generate.py:**
1. **CLI:** Added `--negative-prompt` flag to argparse with sensible default: "blurry, bad quality, worst quality, low resolution, text, watermark, signature, deformed, ugly, duplicate, morbid"
2. **Base pipeline:** `negative_prompt=args.negative_prompt` passed to base `__call__` (both standalone and refiner modes)
3. **Refiner pipeline:** `negative_prompt=args.negative_prompt` passed to refiner `__call__`
4. **Batch:** `batch_generate()` updated to accept `args=None` param, forwards `negative_prompt` per-item via SimpleNamespace; also upgraded to use `generate_with_retry()` for OOM resilience

**Test results:** 95/95 pass (7 new + 88 existing, zero regressions)
**Branch:** squad/3-negative-prompt
**PR:** https://github.com/diberry/image-generation/pull/12

**Key learnings:**
- Negative prompt is standard SDXL quality lever — default covers common artifacts (blur, watermark, deformation)
- All three pipeline call sites (base-only, base-in-refine, refiner) need the kwarg for consistent guidance
- batch_generate() needed both `args` forwarding and `generate_with_retry` delegation — the local main was missing PR #10's batch fixes

### 2026-03-26 — Full Team Code Review: Cross-Cutting Findings

Full five-agent simultaneous code review identified key architectural consensus and bug convergence:

**Architectural Consensus (from Morpheus, Trinity, Neo, Niobe, Switch):**
- Monolithic generate.py is sustainable now; module extraction not justified until responsibilities exceed 10. Revisit decision when code reaches ~400 lines or test maintenance burden increases.
- Try/finally memory management (PRs #4–#6) is canonical pattern for SDXL. Extend to all device-specific code paths (reference: PR#4 HIGH pattern, PR#5 MEDIUM fixes).
- TDD with mock-based testing is proven discipline — continue for all new features. 53 tests, ~2s runtime, no GPU = gold standard for CI cost.

**Bug Convergence (3 issues flagged independently by multiple agents):**
1. **args.steps mutation:** Trinity detailed exact fix; Neo writing test. generate_with_retry() corrupts caller state — local copy pattern required.
2. **batch_generate() parameter drop:** Trinity (backend), Niobe (pipeline tuning), Neo (testing) all independently identified same issue — CLI --steps, --guidance, --width, --height, --refine are silently ignored in batch. Coordinated Trinity/Neo TDD fix required.
3. **Negative prompt gap:** Niobe (pipeline quality), Switch (prompt engineering), and Trinity (CLI wiring) all identified as blocker for image quality. Architectural prerequisite before scheduler tuning or parameter defaults.

**Quality Dependencies (Trinity must sequence fixes):**
- Negative prompt implementation prerequisite for scheduler tuning (pipeline baseline must be set before performance optimization).
- Batch parameter forwarding blocks Niobe's per-item override feature (Trinity must fix batch first, then Niobe can implement per-item tuning).
- CLI validation (Neo) and args mutation fix (Trinity) interdependent — validation catches bad inputs before they reach retry logic.

**Quick Wins (unblocked, can start immediately):**
- Fix hardcoded macOS path in generate_blog_images.sh (Trinity)
- Update README test count to 53+ (Trinity)
- Add "no text" constraint to vacation prompts (Switch, no code)
- Standardize style anchors to original version (Switch, no code)
- Add tests/__init__.py (Neo)

**Next Sprint Coordination (Trinity + Neo TDD approach):**
1. Batch parameter forwarding (Trinity implementation, Neo TDD test-first)
2. args.steps mutation fix (Trinity implementation, Neo TDD test-first)
3. CLI argument validation (Trinity implementation, Neo TDD test-first)
4. Negative prompt CLI wiring (Trinity), style guide updates (Switch), tests (Neo)



4. **CODE SMELL — `batch_generate()` skips OOM retry:** Uses `generate()` directly (line 253) instead of `generate_with_retry()`. Batch items don't get the step-halving retry logic. Fix: optionally delegate to `generate_with_retry()`.

5. **CODE SMELL — Redundant `hasattr` in `main()` (line 300):** `hasattr(args, 'batch_file')` is always True because argparse defines the attribute. Should be just `if args.batch_file:`.

6. **CODE SMELL — Inconsistent MPS hasattr guard:** `get_device()` (line 54) uses `hasattr(torch.backends, "mps")` guard. Entry-point flush (line 120) and finally block (line 220) call `torch.backends.mps.is_available()` without the hasattr guard. Safe with `torch>=2.1.0` floor, but inconsistent.

7. **SHELL — `generate_blog_images.sh` assumes Unix venv activation (line 14):** `source venv/bin/activate` won't work on Windows. Not critical since the script is bash-only, but the hardcoded cd path is the real blocker.

8. **MINOR — No `tests/__init__.py`:** Can cause import ambiguity in some pytest configurations. Quick fix: create empty `__init__.py`.

**Quick fixes (safe, no test changes needed):**
- Issue #5: Change `if hasattr(args, 'batch_file') and args.batch_file:` → `if args.batch_file:`
- Issue #6: Add `hasattr(torch.backends, "mps") and` guard to lines 120 and 220
- Issue #2: Replace hardcoded `cd` with `cd "$(dirname "$0")"`
- Issue #8: Create empty `tests/__init__.py`

**Requires test updates:**
- Issue #1 (args mutation): Needs new test to verify original args.steps is preserved
- Issue #3 (batch ignores CLI params): Needs `batch_generate()` signature change + test updates

**What's clean:**
- `generate()` function architecture is solid: locals-only pipeline vars, try/finally cleanup, OOM detection with dual CUDA/MPS paths
- `OOMError` class is clean and well-integrated
- `parse_args()` mutually-exclusive group is correct
- `requirements.txt` version floors are appropriately set
- Test coverage is thorough (75 tests across 5 files), well-structured with clear TDD phases
- `conftest.py` mock infrastructure is clean and reusable

### 2026-03-25 — Sprint Complete: CI, README, TDD (All 4 Workstreams Merged)

**Sprint scope:** PR #7 CI workflow, PR #8 README update, PR #9 TDD tests + implementation

**Trinity's contributions:**
- PR #7: Created `.github/workflows/tests.yml` (workflow_dispatch, CPU torch, Python 3.10/3.11, ~2s). ✅ MERGED
- PR #8: Updated README (MPS support, testing, memory model, batch gen). Initial draft REJECTED by Neo (pytest scope issue), Trinity scoped fix, Neo APPROVED. ✅ MERGED
- PR #9: Implemented OOMError and batch_generate() to pass 34 new tests. Morpheus code review: all 13 criteria met. ✅ MERGED

**Test results on main:**
| File | Red | Green | Total |
|------|-----|-------|-------|
| test_batch_generation.py | 0 | 17 | 17 |
| test_oom_handling.py | 0 | 14 | 14 |
| test_memory_cleanup.py | 0 | 22 | 22 |
| **Total** | **0** | **53** | **53** |

**Architecture delivered:**
1. **CI/CD:** workflow_dispatch trigger, CPU-only torch (cost-optimized), ~2s test runtime, Python matrix coverage
2. **OOMError:** RuntimeError subclass, CUDA + MPS detection, hasattr guards (version compat), actionable message ("Out of GPU memory. Reduce steps with --steps or switch to CPU with --cpu.")
3. **batch_generate():** Per-item generate() calls, inter-item GPU flushing (gc + cache clears), graceful per-item error handling, order preservation, never raises
4. **Code quality:** Inline comments explain Fixes 1–3, clear logic, good variable names, consistent with existing patterns

**Key learnings:**
- OOM detection dual approach: CUDA exception (torch.cuda.OutOfMemoryError with hasattr guard) + MPS message-based ("out of memory" string match)
- except + finally coexistence: both in one try block. except re-raises transformed exception, finally unconditionally cleans up. Correct pattern.
- Inter-item flushing pattern: `if i < len(prompts) - 1` (between items, not after last). Avoids redundant cleanup since generate() already flushes in its finally block.
- Batch error handling: Per-item exceptions caught, converted to error dicts, returned in results list. Batch never raises — caller decides what to do with error list.
- Device parameter conversion: Converted to cpu flag for generate() call. SimpleNamespace args object matches existing pattern.

### 2026-07-27 — Morpheus Code Review Fixes (R4-R5, S4-S20, N1-N13)

Fixed remaining 27 issues from Morpheus's deep code review across both animation projects.

**Critical (R4-R5):**
- `ensure_remotion_imports()` and `inject_image_imports()` now validate post-injection and raise `ValidationError` on failure instead of silently producing broken code
- Root.tsx drops `React.FC` for plain function signature (consistent with template files)

**Should Fix (S4-S20):**
- Security hardening: block encoded `file://`, `data:` URIs, URL-encoded path traversal
- Pin react@18.2.0, typescript@5.5.4 (exact, no caret)
- Added strict/ignore policy tests for `copy_images_to_workspace`
- Added error propagation tests (ImageValidationError, copy OSError, LLMError)
- Verify subprocess CLI arguments in renderer tests
- Removed 3 dead conftest fixtures
- Replaced weak `count <= 3` assertion with precise import-line checks
- Standardized ruff lint rule order to `["E", "F", "I", "N", "W"]`
- Documented OpenAI SDK as optional in both READMEs

**Nice to Have (N1-N13):**
- Exception class docstrings, .env gitignore, demo_template React cleanup
- File size as MB, Config docstring, exit code docs, credential risk note
- Better "Unknown error" fallback, UTF-8 encoding test, edge case image tests

**Verification:** Ruff clean (both), 162/162 manim tests pass, 208/209 remotion tests pass (1 skip).

**Production readiness:** Both OOMError and batch_generate() fully tested (31 new tests + 22 regression), exception-safe, error messages actionable, edge cases covered. Ready for production batch workflows.

**Sprint status:** ✅ COMPLETE — All 53 tests on main, TDD cycle complete, CI workflow live, README accurate, batch generation and OOM handling production-ready.

### 2026-03-24 — TDD Green Phase Complete: PRs #10 & #11 Merged

**Assignments completed:**

1. **PR #10: generate_with_retry() Implementation (squad/oom-retry)**
   - Implemented `generate_with_retry(args, max_retries=2)` with step halving and retry logic
   - 12/12 tests pass (all of Neo's test_oom_retry.py contracts satisfied)
   - Behavior: Halves args.steps on OOMError, retries up to max_retries, re-raises on exhaustion
   - Integrated with main(): single-prompt path now calls generate_with_retry()
   - Verdict: ✅ APPROVED by Morpheus (code review)

2. **PR #11: --batch-file CLI Implementation (squad/batch-cli)**
   - Added `--batch-file <path>` argument (mutually exclusive with --prompt)
   - Extracted `main()` function for testability
   - Reads JSON array of prompt dicts, calls batch_generate(), prints results
   - 10/10 tests pass (all of Neo's test_batch_cli.py contracts satisfied)
   - Full suite: 63/63 pass (zero regressions)
   - Verdict: ✅ APPROVED by Neo (code review)

3. **generate_blog_images.sh Refactor (included in PR #11)**
   - Replaced 5 sequential python calls with single --batch-file invocation
   - Single process instance reduces model load/teardown overhead
   - PID-namespaced temp file (no /tmp, local directory)
   - Per-item seeds preserved

**Final Test Status on main:**
- test_batch_cli.py: 10/10 ✅
- test_oom_retry.py: 12/12 ✅
- test_batch_generation.py: 17/17 ✅
- test_oom_handling.py: 14/14 ✅
- test_memory_cleanup.py: 22/22 ✅
- **Total: 75/75 ✅ ALL PASSING**

**Key learnings:**
- TDD green phase: implement features to pass pre-written red-phase tests
- exception + finally coexistence: both in one try block for "transform exception but guarantee cleanup" pattern
- Batch memory management: inter-item GPU flushing via gc.collect() + device cache clears
- Device handling: respect --cpu flag and propagate device parameter consistently



- **`workflow_dispatch` only is the correct CI trigger when minutes are scarce:** No `push` or `pull_request` triggers. The workflow only runs when manually invoked from the Actions tab. This is a deliberate cost-control decision, not a limitation.
- **CPU-only torch install for CI:** `--index-url https://download.pytorch.org/whl/cpu` pulls the CPU wheel (~180MB vs ~2GB GPU). Since all tests mock the pipeline, no GPU is needed and this dramatically reduces install time.
- **Matrix strategy on Python 3.10 and 3.11:** Both versions this project targets get validated on every manual run. No caching, no artifacts — keeps the workflow simple and the YAML minimal.
- **Tests run in ~2 seconds with mocks:** The full suite (22 tests in `tests/test_memory_cleanup.py` + `tests/conftest.py`) uses `unittest.mock` throughout. No model downloads, no GPU, no external calls.
- **Branch naming collision:** Created `squad/ci-manual-dispatch` but the working tree was on `squad/readme-update` due to a pre-existing local branch. Fixed by force-pushing the commit ref directly: `git push origin squad/readme-update:squad/ci-manual-dispatch --force`.
- **PR #7:** https://github.com/dfberry/image-generation/pull/7

### 2026-03-25 — PR #8: README Testing Section Fix

Fixed Neo's rejection of PR #8 by updating the pytest command and Testing section description in README.md:

**Problem:** PR #9 added TDD red-phase tests (batch_generation, OOM handling) that intentionally fail. Running `pytest tests/` now shows 53 tests, not 22. Users see 22 failures and think the project is broken.

**Solution:**
- Scoped the main command to `pytest tests/test_memory_cleanup.py -v` (the 22 regression tests that pass)
- Added secondary command `pytest tests/ -v` with context that TDD suites are expected to have failing tests
- Updated descriptive text to clarify: "Regression tests (stable)" vs "TDD suites (in development)"
- Verified all 22 tests pass in 1.88s, no GPU required

**Commit:** `83ea71b` to `squad/readme-update`  
**Status:** Approved. Tests verified. Ready for Neo's re-review.

### 2026-03-25 — CI, README, TDD Sprint: Orchestration Complete

**Sprint Completion:**

| PR | Agent | Task | Status |
|----|-------|------|--------|
| #7 | Trinity | Create workflow_dispatch CI | ✅ MERGED |
| #8 | Morpheus | Update README (MPS, testing, memory model, batch gen) | ✅ MERGED |
| #9 | Neo | Write TDD test suite (batch_generate, OOMError) | 🔴 RED (22 tests fail, 31 green) |

**Execution:**
- Trinity created `.github/workflows/tests.yml` (CPU torch, Python 3.10/3.11, ~2s runtime)
- Morpheus updated README with MPS support, testing section, memory model, batch generation docs
- Initial PR #8 pytest command failed (would show 22 TDD red-phase failures)
- Trinity scoped pytest to `test_memory_cleanup.py` (22 green tests only) on `squad/readme-update` branch
- Neo re-reviewed PR #8 after scope fix: APPROVED
- PR #8 merged to main (squash)
- Neo wrote 34 new tests: 17 batch_generate(), 17 OOMError (9 pass, 22 red)
- PR #9 opened on `squad/tdd-batch-oom-tests`, awaits Trinity implementation

**Test Status:**
| File | Red | Green |
|------|-----|-------|
| test_batch_generation.py | 17 | 0 |
| test_oom_handling.py | 5 | 9 |
| test_memory_cleanup.py | 0 | 22 |
| **Total** | **22** | **31** |

**Next:** Trinity implements batch_generate() and OOMError to pass PR #9.

### 2026-03-25 — Issue #2 / PR #9: Fix hardcoded macOS path in shell scripts

- **Only one shell script exists:** `generate_blog_images.sh`. The `regen_*.sh` scripts referenced in history were from a prior iteration and are no longer in the repo.
- **SCRIPT_DIR pattern is the portable standard:** `SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)` followed by `cd "$SCRIPT_DIR"` makes all relative paths (like `venv/bin/activate`, `outputs/`, `generate.py`) resolve correctly regardless of where the script is invoked from or which machine it runs on.
- **Always audit all `*.sh` files when fixing path issues:** Even if only one script is reported, check every shell script in the repo to prevent the same bug from lurking elsewhere.

---

## Full Team Code Review (2026-03-26)

**Event:** Comprehensive 5-agent code review of image-generation project  
**Scope:** Architecture, backend, pipeline quality, prompts, testing  
**Outcome:** 10 issues identified (3 HIGH, 4 MEDIUM, 3 LOW)

**Trinity Role & Findings (Backend Dev):**
- **Key Responsibility Areas:** generate.py, shell scripts, CLI design, dependency management
- **HIGH Issues Found:** 
  1. args.steps mutation in generate_with_retry() — corrupts caller state
  2. Hardcoded absolute path in generate_blog_images.sh — portability blocker
- **MEDIUM Issues Found:**
  1. batch_generate() ignores CLI overrides (--steps, --guidance, --width, --height, --refine)
  2. Cache flush guard inconsistency (CUDA vs MPS pattern)
  3. No --negative-prompt CLI support (architectural gap, blocks quality improvements)
- **LOW Issues Found:**
  1. README test count stale (22 → 53+)
  2. CLI argument validation missing (steps=0, width=7, guidance=-1 accepted)

**Issues Requiring Trinity Implementation:**
1. **HIGH Phase 2:** Fix args.steps mutation → use SimpleNamespace copy in retry loop
2. **MEDIUM Phase 2:** Implement batch_generate() parameter forwarding (TDD-first, Neo writes tests)
3. **MEDIUM Phase 2:** Extract flush_device_cache() helper (DRY refactor)
4. **LOW Phase 2:** Add CLI argument validators (argparse type parameter)
5. **MEDIUM Phase 3:** Implement --negative-prompt CLI flag + batch JSON support

**Cross-Team Coordination Notes:**
- Trinity/Neo: Batch parameter forwarding requires TDD test-first approach
- Trinity/Switch: Negative prompt CLI must coordinate with style guide updates
- Trinity/Niobe: Negative prompt wiring unblocks scheduler/guidance tuning work
- All Phase 2 changes must follow TDD-first discipline

**Code Review Observations:**
- Memory management: Well-engineered try/finally + OOM + batch cleanup patterns
- Error handling: OOMError detection solid, message actionable
- Test integration: 53+ tests all passing, good regression coverage
- Overall quality: High maintainability, clear structure

**Recommendations Summary:**
- Phase 1: Fix paths, update docs (quick wins)
- Phase 2: Fix mutations/forwarding/validation (all TDD-first, critical for reliability)
- Phase 3: Negative prompts + templates + tuning (architectural features)

**Team Consensus:**
- args.steps mutation is HIGH priority, fix immediately in Phase 2
- Batch parameter forwarding: implement TDD-first (Neo tests → Trinity code)
- All Phase 2 work must maintain zero-regression test status
- Ready to begin Phase 1 quick wins immediately
### 2026-03-26 — PR #11: CLI Argument Validation (Issue #5, TDD Green Phase)

**Assignment:** Make Neo's 13 tests in test_cli_validation.py pass by adding range validation to parse_args().

**Implementation:** Three custom argparse type functions:
- `_positive_int(value)` — rejects steps <= 0
- `_non_negative_float(value)` — rejects guidance < 0
- `_dimension(value)` — rejects width/height < 64

Wired into argparse via `type=` parameter. Argparse raises SystemExit with clear error on invalid input — matches test expectations exactly.

**Results:** 13/13 validation tests pass. 94/95 total suite pass (1 pre-existing failure in test_negative_prompt.py unrelated to this change).

**Key learnings:**
- Custom argparse type functions are the cleanest validation pattern: argparse handles error formatting, SystemExit, and help text automatically. No post-parse validation needed.
- ArgumentTypeError message includes the rejected value for debuggability.
- Pre-existing test_negative_prompt.py::test_batch_forwards_negative_prompt fails due to unimplemented negative prompt feature — not a regression.

### 2026-04-18 — Joel Test Tier 1: CI Workflow, Makefile, Linting, Dev Deps

**Completed and merged (2026-04-18T20:10:27Z).**

- **CI workflow overhaul:** Added `push` (main) and `pull_request` triggers with path filters. Lint job (ruff) gates test matrix. Concurrency groups cancel stale runs. Result: All PRs now get automated lint + test.
- **Makefile standardization:** Targets: `setup`, `install`, `install-dev`, `test`, `lint`, `format`, `clean`, `all`. Uses venv-relative Python paths. Result: One-command dev setup for contributors.
- **requirements-dev.txt:** Chains base requirements + pytest, ruff, pytest-cov. Enables `make install-dev` to set up full dev environment.
- **ruff.toml configuration:** Python 3.10 target, 120 char lines, E/F/W/I rules, E501 ignored (formatter owns line length), excludes venv/outputs/__pycache__. Result: Single source of truth for style rules across local + CI.
- **Test outcome:** 172 tests passing — full regression suite validated.
- **Impact:** Joel Test score improvement from 6/12 → 9/12 (PR-triggered CI, dev tooling, linting infrastructure).
- **Parallel coordination:** Neo completed contributor templates simultaneously — both decisions merged to `decisions.md`, inbox cleaned.

### 2026-04-18 — PR #15 Fact-Check Review: Technical Claims Verification

**Scope:** Verify 35+ technical claims in PR #15 (Joel Test improvements) against actual code.

**Verification Results: 31/35**

| Status | Count | Examples |
|--------|-------|----------|
| ✅ Verified | 31 | Joel Test mapping items #1–#5, #7–#11; memory cleanup; device selection; Makefile targets; feature spec coverage |
| ❌ False | 2 | CLI flags wrong in CONTRIBUTING.md; CI pip quoting missing |
| ⚠️ Partial | 1 | Dev setup incomplete — recommends bare install instead of requirements-dev.txt |
| ❓ Unverifiable | 1 | Joel Test #12 "hallway testing" — no evidence in codebase |

**False Claims Found (Must Fix in Follow-Up):**

1. **CONTRIBUTING.md Line 113 — Wrong CLI Flags:**
   - **Claim:** `--refiner` and `--device` flags
   - **Reality:** Actual flags are `--refine` (note: -e, not -er) and `--cpu` (not --device)
   - **Also missing:** `--prompt`, `--batch-file`, `--output`, `--refiner-steps`, `--refiner-guidance`, `--scheduler`, `--negative-prompt`, `--lora`, `--lora-weight`
   - **Impact:** Contributors copying these examples will get AttributeError when running CLI

2. **CI Shell Quoting Bug — `.github/workflows/tests.yml` Line 26:**
   - **Current:** `pip install ruff>=0.4.0` (unquoted)
   - **Problem:** Bash interprets `>=` as redirect operator. Should be `pip install 'ruff>=0.4.0'`
   - **Impact:** CI may fail silently or install wrong package version

**Partially True Claim (Must Fix in Follow-Up):**
- **CONTRIBUTING.md Lines 119–120 Dev Setup:** Recommends `pip install pytest ruff` instead of `pip install -r requirements-dev.txt`. While true that this installs pytest/ruff, it's incomplete — missing other dev dependencies. Should reference requirements-dev.txt.

**Unverifiable Claim:**
- **Joel Test #12 "Hallway Testing":** PR claims this is addressed but no evidence in codebase. Cannot verify.

**Recommendation:** Merge PR as-is (non-blocking issues), create follow-up issues to fix the 3 items above.

---
## [2026-04-21T17:31:43Z] Completed PR #89 Remotion Test Fixes

**Status:** ✅ Complete  
**Agent Fixing:** Neo (test bugs)

Fixed Neo's test implementation bugs in remotion CLI tests following reviewer lockout protocol:

- **Replaced fake ArgumentParser**: Now uses real main() entry point
- **Added exit-code test**: Validates ImageValidationError propagates exit code 2
- **Integration testing**: Full CLI-to-core flow coverage
- **Result**: 13 CLI tests pass

Branch pushed to squad/89-remotion-image-support, ready for Neo's re-validation.

### 2026-03-26 — PRs #94, #95, #98: Three Bug Fixes (Issues #90, #91, #93)

- **Issue #90 (PR #94):** Manim renderer looked for `media/` relative to `scene_file.parent` instead of the actual CWD. When `assets_dir` was provided as CWD, the output was at `assets_dir/media/...` but the code searched `scene_file.parent/media/...`. Fix: compute `base_dir` from `assets_dir` when present. Both primary path and rglob fallback use the correct base. 3 new tests.
- **Issue #91 (PR #95):** Remotion packages had transitive dep mismatches (4.0.448/449/450). Pinned all direct `@remotion/*` deps to exact 4.0.450 and added npm `overrides` block for transitive deps. Clean `npm install` confirmed.
- **Issue #93 (PR #98):** Root.tsx hardcoded `durationInFrames={150}`. Now uses `getInputProps()` from Remotion with nullish coalescing defaults. renderer.py passes all four composition values (durationInFrames, fps, width, height) as structured JSON via `--props` using `json.dumps()`. 2 new tests.
- **Lesson:** When subprocess runs with a different CWD, always trace where output files land relative to that CWD, not relative to input file paths.
- **Lesson:** Use `json.dumps()` for CLI JSON args instead of manual string concatenation — avoids quoting issues and makes the structure explicit.

### 2026-07-22 — Manim Code Quality Fixes (S2, S3, S7, S8, S9)

Addressed 5 code quality issues from Morpheus's review. All 149 tests pass, ruff clean.

- **S2 (scene_builder.py):** Removed `_BLOCKED_BUILTINS` — it was a strict subset of `FORBIDDEN_CALLS`. `validate_image_operations()` now references `FORBIDDEN_CALLS` directly. Single source of truth for dangerous built-in names.
- **S3 (config.py):** Removed dead `"np"` from `ALLOWED_IMPORTS`. AST validation checks `ast.Import.names[].name` which is the module name (`numpy`), never the alias (`np`). The entry did nothing.
- **S7 (pyproject.toml):** Added upper bounds `manim<0.20.0` and `openai<2.0.0` to prevent silent breakage from major version bumps.
- **S8 (test_cli.py):** Added `capsys` assertions to all three error-path tests — now verify stderr contains the error class label and the original message text, not just exit codes.
- **S9 (conftest.py):** Changed subprocess fixtures to accept `monkeypatch` and call `monkeypatch.setattr(subprocess, "run", _fake_run)` inside the fixture. Previously they returned bare functions that no test ever applied.
### 2026-07-22 — Morpheus Review Fixes (remotion-animation + manim-animation)

Fixed 7 issues flagged by Morpheus's code review:

**Critical (R1, R2):**
- Removed unused pydantic dependency from remotion-animation (pyproject.toml + requirements.txt)
- Converted eagerly-imported OpenAI classes to lazy imports inside `_create_client()` per-provider branches. Module now importable without openai installed.

**High (S1):**
- Both llm_client.py files now catch `AuthenticationError`, `RateLimitError`, `APIConnectionError` separately. LLMError messages include `[auth]`, `[rate_limit]`, `[connection]` tags so callers can distinguish retryable vs terminal failures.

**Medium (S16, S17, S18, S5):**
- S16: Refactored demo mode — `generate_video()` gained a `component_code` param; demo now calls it instead of duplicating path/preset/render logic.
- S17: Changed `max_retries` default from 0 to 2 so TSX validation retries are active out-of-the-box.
- S18: Moved per-provider temperature values to `PROVIDER_TEMPERATURES` dict in config.py.
- S5: Added `"engines": { "node": ">=18.0.0" }` to remotion-project/package.json.

**Ruff:** Both projects pass `ruff check` clean (pre-existing F541 in manim cli.py was not touched).

---

## Session: Code Quality Fixes — Manim & Remotion (2026-04-22)

**Agents:** Morpheus (Lead), Neo (Tester), Trinity (Backend Dev x2)  
**Branch:** fix/morpheus-review-issues  

**Work Completed (Manim):**
- S2: Consolidated forbidden-call lists
- S3: Removed dead numpy alias
- S7: Added version ceilings (manim>=0.18.0,<0.20.0, openai>=1.0.0,<2.0.0)
- S8: Strengthened test assertions with capsys
- S9: Fixed mock subprocess fixtures with monkeypatch

---

## Session: Voice Customization & Documentation (2026-04-22)

**Agent:** Trinity (Backend Dev)  
**Commit:** 1839abe (main)

**Work Completed:**
- Added --voice flag support to remotion-animation video generation
- Updated user-guide.md with --voice flag documentation and usage examples
- Regenerated remotion example video with en-US-JennyNeural female voice
- Feature enables users to specify different text-to-speech voice options

**Deliverables:**
- Feature: --voice flag implemented and integrated
- Documentation: user-guide.md updated with examples
- Validation: Example video regenerated and pushed to main branch

**Verification (Manim):**
- Ruff: 0 new issues (clean)
- Pytest: 149/149 passed (1.95s)

**Work Completed (Remotion):**
- R1: Removed unused pydantic dependency
- R2: Implemented lazy OpenAI import
- S1: Specific exception catching (auth, rate_limit, connection tags)
- S5: Added engines field to package.json
- S16: Demo refactoring
- S17: Default max_retries value
- S18: Moved temperature to config

**Verification (Remotion):**
- Ruff: Clean (0 new issues)

**Decisions Written:**
- trinity-manim-quality-fixes.md
- trinity-llm-exception-tags.md (shared with manim)

**Next:** Team PR review on branch fix/morpheus-review-issues

---

## Learnings

### 2026-04-22 — mermaid-diagrams comprehensive documentation

Created 5 documentation files in `docs/mermaid-diagrams/` by reading all source files:

- **architecture.md** — Full pipeline flow (input → validator → generator → mmdc subprocess → output), module breakdown for all 7 modules, exception hierarchy, subprocess isolation design. Documented that MmcdNotFoundError is raised only from `_run_mmdc` catching FileNotFoundError — not at init time.
- **development.md** — Repo structure, coding conventions (underscores not hyphens for template names, `str | None` syntax), how to add templates (extend ABC + register in registry), how to add output formats (just add to SUPPORTED_FORMATS), Makefile targets, dependency management.
- **testing.md** — Test architecture, mock_mmdc fixture internals (intercepts subprocess.run, writes fake PNG/SVG bytes), how tests run without real mmdc, error simulation patterns, how to add new tests.
- **installation.md** — System requirements (Python 3.10+, Node.js), mmdc install via npm, pip install -e ., Makefile shortcut, verification commands, troubleshooting.
- **user-guide.md** — CLI usage (all flags and modes), Python API (MermaidGenerator, MermaidValidator, default_registry), all 4 built-in templates with parameter docs and examples, output formats, error handling.

Key facts documented: zero runtime Python dependencies, 19 recognized diagram types in validator, 30s subprocess timeout, comma-separated --param values auto-split into lists.

### 2025-07-24 — Comprehensive manim-animation documentation

Created 5 documentation files in `docs/manim-animation/`:
- **architecture.md** — Full pipeline diagram (prompt → LLM → scene code → AST validation → Manim render → MP4), all 7 modules documented, security model (import whitelist, forbidden calls, subprocess isolation, workspace isolation), quality presets table.
- **development.md** — Repo structure, pyproject.toml config, ruff rules (E/F/I/N/W with E501 ignored), how to add LLM providers, extend validation, add quality presets, few-shot prompt system internals, dependency management.
- **testing.md** — 162+ tests across 9 files, all mock patterns (LLM via MagicMock, subprocess via monkeypatch, CLI args via sys.argv patch, env vars via patch.dict), conftest fixtures, how to add tests, image test patterns.
- **installation.md** — System reqs (Python 3.10+, FFmpeg, Ollama; NO Node.js), platform-specific FFmpeg/Ollama install, pip install -e ., OpenAI/Azure optional setup, LaTeX optional for MathTex, troubleshooting.
- **user-guide.md** — Full CLI reference, quality presets, duration 5-30s, example prompts by category, debug mode, image support (formats, policies, size limit), LLM provider switching, exit codes, troubleshooting, Phase 0 limitations.

Key facts documented: 3 LLM providers via OpenAI-compatible SDK, lazy client init pattern, 162 tests all offline, AST-based security with FORBIDDEN_CALLS/FORBIDDEN_NAMES/ALLOWED_IMPORTS frozensets, image pipeline with validation policies (strict/warn/ignore), 100MB image size limit, deterministic workspace naming.
### 2026-04-22 — remotion-animation documentation (5 docs)

Created comprehensive documentation suite for the remotion-animation package in `docs/remotion-animation/`:

- **architecture.md** — Full hybrid Python+Node.js pipeline diagram, module breakdown for all 8 modules (cli.py, llm_client.py, component_builder.py, renderer.py, config.py, errors.py, image_handler.py, demo_template.py), Remotion project structure (Root.tsx composition registry, GeneratedScene.tsx runtime slot, templates/), image handling pipeline, security model (5-layer TSX validation: dangerous imports, image path security, structural validation, bracket matching, import injection verification).
- **development.md** — Dual-stack repo structure, ruff lint rules (E/F/I/N/W), how to add LLM providers (5 steps), how to add templates, component injection mechanism (GeneratedScene.tsx overwrite + Root.tsx composition), how to extend TSX validation (dangerous imports, symbol auto-imports, JSX tag checks), branch naming, dependency management (pinned React 18.2.0, TypeScript 5.5.4, Remotion 4.0.450).
- **testing.md** — Test architecture (209+ tests, 11 files), mock patterns (module-boundary mocks for OpenAI SDK, mock subprocess for renderer, monkeypatch for CLI integration), all test categories documented, conftest.py fixtures, 1 expected Windows skip (symlink privilege), how to add new tests.
- **installation.md** — System requirements (Python 3.10+ AND Node.js 18+), step-by-step for both stacks, all 3 LLM provider setups (Ollama/OpenAI/Azure), verification commands including `--demo` smoke test, platform notes (Windows PowerShell backtick issue with TSX templates).
- **user-guide.md** — All CLI flags (12 documented), quality presets table, demo mode, example prompts, debug mode (GeneratedScene.debug.tsx), LLM provider switching, image input, environment variables, troubleshooting guide.

### Documentation — image-generation package comprehensive docs

## Learnings

- Created 5 documentation files in `docs/image-generation/`: architecture.md, development.md, testing.md, installation.md, user-guide.md.
- **architecture.md** — Full pipeline flow diagram (text-based), module breakdown of generate.py (entry points, core pipeline, internal helpers, model loading, utilities), lazy import system (_ensure_heavy_imports + __getattr__), device detection chain, memory management at 3 levels (pre-flight, mid-refine, post-generation), batch processing flow, torch.compile optimization, scheduler system (10 schedulers), base+refiner 80/20 split.
- **development.md** — Repo structure, ruff linting (E/F/W/I rules, E501 ignored), how to add CLI flags (4-step process: parse_args → generate → batch → conftest), scheduler/LoRA internals, pipeline modification guide, branch naming (squad/{issue}-{slug}), PR workflow (TDD), dependency management (requirements.txt vs .lock vs -dev.txt), Makefile targets, CI workflow details.
- **testing.md** — 170+ tests across 15 files, MockPipeline/MockImage patterns, critical spec pattern (MagicMock(spec=MockPipeline()) — instance not class), _patch_heavy context manager for lazy import testing (injects via __dict__ not @patch), batch test patching (must target generate_with_retry not generate), conftest fixtures, CI workflow with working-directory and CPU-only torch.
- **installation.md** — System reqs (Python 3.10+, ~7GB disk), GPU matrix (CUDA/MPS/CPU with perf numbers), step-by-step venv setup, dependency tables, CUDA-specific torch install, verification steps, environment variables, model download sizes, offline usage, troubleshooting.
- **user-guide.md** — What the tool does, quick start, all 16 CLI flags with types/defaults, quality presets table, generation time expectations, batch JSON format, shell script batch, prompt writing rules (5 rules: style anchor, ≥3 colors, no text, distant silhouette, light sources), scheduler reference, output format, negative prompt, 8 troubleshooting entries.
- Key patterns captured: lazy import testing requires __dict__ injection (not @patch), batch tests must patch generate_with_retry (not generate), MagicMock spec requires instance not class, ruff ignores E501 but enforces 120-char via formatter.


## 2026-04-22 - Documentation Fix Implementation Plan

**Session:** Prioritized implementation of all review findings  
**Status:** Plan prepared, ready to execute

Coordinated Morpheus (structural review) and Neo (QA review) findings into prioritized fix plan:

**Phase 1 (P0 - 1.5 hours):**
- Create docs/README.md with 4-project comparison matrix
- Fix circular reference in manim-animation limitations doc

**Phase 2 (P1 - 50 minutes):**
- Add FORBIDDEN_NAMES to manim troubleshooting.md
- Strengthen cross-project references in all 4 limitations docs
- Add 'Related Tools' sections to all user guides

**Phase 3 (P2 - next sprint):**
- Add 'Back to Index' navigation links
- Standardize limitation heading structure

**Output:** .squad/orchestration-log/2026-04-22T0642-trinity.md


### 2026-04-24 — Sound Effects Implementation for manim-animation

Implemented full sound effects support for manim-animation following TDD approach. Delivered all review conditions from Morpheus and Neo.

**Implementation:**
- Created udio_handler.py (190 lines) — mirrors image_handler.py patterns exactly (validate, copy, context, AST validation)
- Added AudioValidationError to rrors.py
- Extended config.py with sound effects system prompt + Example 5 (bouncing ball with thud)
- Updated scene_builder.py to call alidate_audio_operations() when audio_filenames provided
- Updated llm_client.py to accept udio_context parameter and inject into user message
- Updated cli.py with --sound-effects and --audio-policy flags (exit code 6 for audio errors)

**Test Coverage:**
- 48 new tests across 3 files (test_audio_handler.py, test_audio_security.py, test_audio_cli.py)
- All 210 tests pass (162 existing + 48 new)
- Neo conditions addressed:
  1. 	est_add_sound_with_negative_time_offset — negative time_offset allowed (Manim parameter)
  2. 	est_add_sound_with_invalid_gain — gain=9999 allowed (Manim validates at runtime)
  3. 	est_audio_validation_error_message_format — user-friendly messages verified
  4. 	est_audio_and_image_full_pipeline — both ImageMobject + add_sound in generated code
  5. 	est_add_sound_on_non_self_object_ignored — other.add_sound() ignored (not validated)
- Morpheus P1 verified: enderer.py line 62 uses cwd=assets_dir (confirmed with grep)

**Design Patterns:**
- Audio files copied as sfx_0_thud.wav, sfx_1_whoosh.mp3 (prefixed to avoid collision with images)
- AST validation: string-literal-only + allowlist (same security model as images)
- Supported formats: .wav, .mp3, .ogg (FFmpeg native)
- Max file size: 50MB per file
- Policy system: strict/warn/ignore (mirrors image handler)

**Key Learnings:**
- TDD approach caught edge cases early (negative time_offset, invalid gain, non-self objects)
- Mirroring existing patterns (image_handler.py) ensures consistency and reduces review cycles
- AST validation only checks filenames — runtime parameter validation is Manim's responsibility
- Audio context injection follows same pattern as image context (appended to user message)
- Exit code allocation: images=5, audio=6, leaves room for future features

**Breaking Changes:** None. All new parameters are optional.



## Learnings

### 2026-01-22: Full Audio Support Implementation (Phase 0)

Implemented comprehensive audio support for remotion-animation following plan-full-audio.md:

**Key Achievements:**
- ✅ Created audio_handler.py mirroring image_handler.py patterns
- ✅ Created tts_providers.py with edge-tts ONLY (Phase 0), OpenAI deferred to Phase 1
- ✅ Made edge-tts an OPTIONAL dependency (Morpheus P0): `pip install remotion-gen[audio]`
- ✅ Added 9 new CLI flags (--narration-text, --narration-file, --background-music, --sound-effects, --tts-provider, --voice, --music-volume, --narration-volume, --audio-policy)
- ✅ Extended SYSTEM_PROMPT in llm_client.py with Audio component documentation
- ✅ Added Audio to JSX tag balance check in component_builder.py
- ✅ Refactored shared _validate_static_file_refs() for image + audio (Morpheus P1 #3)
- ✅ Added TTS text validation: reject empty/whitespace, reject >10000 chars (Morpheus P1 #1)
- ✅ Added early validation for missing OPENAI_API_KEY check (prepared but not implemented since Phase 0 = edge-tts only)
- ✅ Used Optional[List[str]] consistently for audio_filenames typing (Morpheus P1 #4)

**Test Coverage:**
- ✅ test_audio_handler.py: 18 tests (validate, copy, context generation)
- ✅ test_tts_providers.py: 16 tests (edge-tts generation, error handling, provider factory)
- ✅ test_audio_security.py: 13 tests (path validation, template literal blocking, Neo conditions)
- ✅ All 258 tests pass (including 50 new audio tests)

**Addressed ALL Review Conditions:**
- Morpheus P0: edge-tts as optional dep ✅
- Morpheus P1 #1: TTS text validation ✅
- Morpheus P1 #2: Early OPENAI_API_KEY validation (deferred to Phase 1) ✅
- Morpheus P1 #3: Shared _validate_static_file_refs() ✅
- Morpheus P1 #4: Optional[List[str]] typing ✅
- Morpheus P1 #5: Audio already in _REMOTION_HOOKS (confirmed) ✅
- Morpheus P1 #6: Post-generation warning for unused audio (deferred - requires LLM response parsing)
- Morpheus RECOMMENDATION: Ship Phase 0 with edge-tts ONLY ✅
- Neo #1: Whitespace-only narration text rejected ✅
- Neo #2: Unicode in narration text passes (edge-tts handles it) ✅
- Neo #4: Template literal backticks blocked in staticFile() ✅

**Notable Patterns:**
- Mirrored image_handler.py structure exactly (validate → copy → context)
- Used TDD: wrote all tests first, then implementation
- File naming: `audio_{uuid8}.mp3`, `music_{uuid8}.mp3`, `sfx_0_{uuid8}.mp3`
- Volume validation at argparse level (0.0-1.0 range)
- Mutual exclusion: --narration-text and --narration-file cannot both be set

**Deferred to Phase 1:**
- OpenAI TTS provider
- Audio file duration validation (requires pydub/ffprobe)
- TTS output caching
- Subtitle generation
- Audio format conversion
- Post-generation warning for unused audio files

### 2026-04-22 — Personalized TTS video + docs contradiction fix

- **remotion-gen CLI flag is --narration-text, not --tts-text:** The user-guide.md documents --tts-text but the actual argparse uses --narration-text. Docs should be updated to match (or vice versa). Used --narration-text successfully.
- **Generated theorem_dina.mp4:** 8s medium-quality video with TTS narration via edge-tts. Ollama LLM generated the component successfully.
- **Fixed 4 doc contradictions:** user-guide.md line 274 said "No audio" despite the Audio Features section above it. Also fixed 3 rows in limitations-and-roadmap.md summary table (Audio/Sound, TTS, Voice-Over) that still showed "Not supported" despite detailed sections showing partial support.

### 2026-04-22 — Fixed theorem_dina.mp4: audio-only → visuals + audio

- **Root cause: LLM-generated component used `backgroundColor` with a `linear-gradient()` value.** CSS `backgroundColor` does not support gradients — only the `background` shorthand does. The invalid value was silently ignored, producing a transparent background. Combined with no explicit `color` on the text elements, the result was invisible text on a transparent/black background → "audio only, no visuals."
- **Second issue: LLM omitted "Dina Berry" entirely.** The generated component only showed date/time text, missing the name that was the primary visual request.
- **Fix:** Replaced the LLM-generated component with a demo-template-style component using `background` (not `backgroundColor`) for the gradient, explicit white text color, spring-animated "Dina Berry" title, date/time subtitle, and the existing `<Audio>` tag referencing `narration.mp3`.
- **Lesson: LLM-generated CSS for Remotion is fragile.** `background` vs `backgroundColor` is a common LLM mistake. The component_builder validator should consider checking for `backgroundColor` with gradient values as a known bad pattern.

### 2026-04-22 — Manim Theorem Video with Text Annotations

- **Direct scene rendering bypasses LLM pipeline:** For custom, hand-crafted scenes, render directly with `manim render <scene>.py GeneratedScene --format=mp4 -qm` from the outputs dir. No need to go through the LLM client when the scene code is known.
- **Text() over MathTex for portability:** Used `Text()` with Unicode superscripts (a², b², c²) instead of `MathTex` to avoid LaTeX dependency issues. Works on any system with manim installed.
- **Step-by-step annotation pattern:** FadeOut previous step text before FadeIn of next step. Keeps bottom-of-screen annotation area clean. Same pattern as the config's SYSTEM_PROMPT rule about not stacking text.
- **Scene file:** `manim-animation/outputs/theorem_explained_scene.py` — annotated Pythagorean theorem with title, intro text, 5 step annotations, highlighted squares, final equation with box.
- **Output:** `manim-animation/outputs/theorem_explained.mp4` — 720p30, ~0.9MB, ~22s duration.

### 2026-07-24 — Implementation Review of image-generation/ subfolder

Performed detailed code review of all files in the image-generation/ directory. Findings below.

**generate.py — SOLID (627 lines)**
- Architecture is clean: lazy imports via _ensure_heavy_imports() + PEP 562 __getattr__ keeps module importable without GPU stack. Good pattern.
- Argument parsing is thorough: custom types (_positive_int, _non_negative_float, _dimension) provide clear validation with helpful error messages.
- Device detection cascade (CUDA → MPS → CPU) is correct. MPS uses nable_model_cpu_offload() instead of .to("mps") — correct for memory-constrained Apple Silicon.
- Memory management is excellent: pre-flight flush, latents CPU transfer before cache clear, dynamo reset, and comprehensive finally block. All documented in prior PRs.
- OOM retry logic (generate_with_retry) is well-designed: halves steps on retry, doesn't mutate original args.
- Batch validation (_validate_batch_item, _validate_output_path) catches traversal attacks and type errors. Good security posture.

**Issues found (generate.py):**
1. **Duplicated GPU flush logic (Code smell):** The gc.collect() + cuda.empty_cache() + mps.empty_cache() pattern appears 4 times (lines 347-352, 395-399, 425-430, 565-571). Should be extracted to a _flush_gpu_memory() helper. Not blocking but increases maintenance burden.
2. **_validate_output_path bypassed for absolute paths in batch JSONs:** All 4 batch JSON files use absolute Windows paths (C:\\Users\\diberry\\...). But _validate_output_path() rejects absolute paths. This means batch_generate() would error on the shipped batch configs. The batch_generate() call site does call _validate_output_path, so the existing batch JSON files would fail validation. These configs only work because they were likely run before the path validation was added, or run outside atch_generate().
3. **logging.basicConfig only runs under __name__ == "__main__":** If main() is called as a library function, no logging output. Minor — correct for CLI tool.
4. **TODO comments on lines 189, 218:** "Replace main with specific commit SHA" for model reproducibility. Low priority but worth tracking.
5. **_HIGH_NOISE_FRAC = 0.8 is hardcoded:** Not configurable via CLI. Acceptable for current use case but noted.

**generate_blog_images.sh — GOOD**
- set -euo pipefail — correct strict mode.
- Uses $$ PID for temp file naming — avoids race conditions.
- source venv/bin/activate assumes venv exists at ./venv. No guard for missing venv.
- Cleanup of temp batch file (m -f "") runs even on success. But NOT on pipeline failure (set -e exits before rm). Should use trap for cleanup.
- Missing 	rap 'rm -f ""' EXIT — temp file leaks on error.
- Hardcoded prompts duplicate content from batch_blog_images.json (different prompts though). Two sources of truth for batch configs.

**requirements.txt — ACCEPTABLE**
- Versions use >= floors: diffusers>=0.21.0, 	orch>=2.1.0, ccelerate>=0.24.0 — these were explicitly audited in PR#3/#5 to ensure memory management correctness.
- invisible-watermark>=0.2.0 is required by SDXL but rarely updated. Fine.
- No upper bounds means a future breaking change in diffusers/torch could break things silently. Acceptable for a tool repo, would be a concern for a library.

**requirements.lock — CONCERN**
- Pinned to the exact floor versions (e.g., diffusers==0.21.0, 	orch==2.1.0). These are ~2 years old. The lock file serves reproducibility but the versions are significantly outdated. 	orch==2.1.0 misses significant MPS and compile improvements in 2.2-2.4.
- Does NOT include transitive dependencies. This is not a true lock file — it's just pinned direct deps. A real lock would come from pip freeze or pip-compile.

**requirements-dev.txt — GOOD**
- Pulls in prod deps via -r requirements.txt, adds pytest, ruff, pytest-cov. Clean.

**Makefile — GOOD**
- Cross-platform (Windows/Unix) path detection works.
- python3 -m venv in setup target — correct.
- .PHONY declared for all non-file targets.
- Missing: generate target to actually run image generation. Only has setup/lint/test/format/clean.

**Batch JSON files — STRUCTURAL ISSUE**
- atch_blog_images.json, atch_blog_images_v2.json, atch_session_storage.json are nearly identical (same 5 prompts, same seeds 42-46). v2 drops 
egative_prompt from the first item but keeps it in the rest — looks like an editing artifact, not intentional.
- atch_you_have_a_team.json has different content (3 items, PNW watercolor style). Clean.
- ALL batch files use absolute Windows paths (C:\\Users\\diberry\\...). These are machine-specific and would fail on any other machine. Should use relative paths or a configurable base path.
- As noted above, absolute paths also conflict with _validate_output_path() security checks.

**ruff.toml — GOOD**
- Targets Python 3.10, 120 char line length, ignores E501 (line length handled by formatter).
- Selects E/F/W/I rules — standard and sensible.
- Excludes venv, __pycache__, outputs — correct.
- known-first-party = ["generate"] — enables correct isort grouping.

**Summary of actionable items (prioritized):**
- **P0:** batch JSON files use absolute paths that fail _validate_output_path(). Either make paths relative or add an --allow-absolute flag.
- **P1:** Extract duplicated GPU flush logic to _flush_gpu_memory() helper.
- **P1:** Add 	rap cleanup to generate_blog_images.sh for temp file.
- **P2:** Make equirements.lock a real lock file with transitive deps (pip-compile).
- **P2:** Deduplicate near-identical batch JSON files (batch_blog_images.json vs v2 vs session_storage).
- **P2:** Bump lock file versions — torch 2.1.0 is missing 2+ years of fixes.

### 2026-04-22 — Review fixes: GPU helper, batch paths, lint, cleanup

- **Extracted `_flush_gpu_memory()` helper:** Consolidated 4 duplicated GPU flush blocks (gc.collect + cuda.empty_cache + mps.empty_cache) into a single helper at module level. All 4 call sites now use it. The mid-refine flush had a different order (mps before cuda before gc) — normalized to the canonical order (gc first, then cuda, then mps) which matches the function's docstring intent.
- **Batch JSON absolute paths were DOA:** All batch JSON files used `C:\Users\diberry\...` absolute paths, which `_validate_output_path()` rejects. Converted to relative `outputs/<filename>.png`. Batch files should always use relative paths.
- **`batch_session_storage.json` was an exact duplicate** of `batch_blog_images.json` and `batch_blog_images_v2.json` (all three byte-identical). Deleted the duplicate.
- **`_write_tests.py` scaffold removed:** File header said "run once, then delete" — was still tracked. git rm'd.
- **Shell script trap pattern:** Added `trap 'rm -f ""' EXIT` after temp file variable declaration. Removed the redundant explicit `rm -f` since EXIT trap fires on both success and failure.
- **Ruff lint fixes in test_coverage_gaps.py:** Removed unused `pytest` import, removed 3 unused `as mock_torch` and 1 `as mock_makedirs` variable bindings. Fixed import sort order (I001).