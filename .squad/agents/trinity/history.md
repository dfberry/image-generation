# Project Context

- **Owner:** dfberry
- **Project:** Python-based AI image generation tool using Stable Diffusion XL (SDXL). Generates blog illustrations with tropical magical-realism aesthetic. Stack: Python 3.10+, diffusers, transformers, torch, Pillow. Key files: generate.py (main CLI), generate_blog_images.sh and regen_*.sh (batch scripts), prompts/ (style guides and prompt library), outputs/ (generated PNG images).
- **Stack:** Python 3.10+, diffusers>=0.19.0, transformers>=4.30.0, torch>=2.0.0, accelerate, safetensors, Pillow
- **Created:** 2026-03-23

## Key Paths

- `generate.py` — main CLI with --steps, --guidance, --seed, --width, --height, --refine, --cpu flags
- `generate_blog_images.sh` — generates 5 blog images (01-05), seeds 42-46
- `regen_fix.sh` — regenerates images 01, 06, 07, 08 with corrected prompts
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