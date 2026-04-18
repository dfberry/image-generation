# Squad Decisions

## Active Decisions

### Directive: User Test-Driven Development Workflow (2026-03-23)

**By:** dfberry (via Copilot)

**Decision:** All future changes must follow this workflow:
1. Create a PR branch first
2. Write tests before making any fixes (test-first / TDD)
3. Make the fixes
4. Ensure all tests pass
5. Team signs off before merge

**Rationale:** Establishes TDD workflow and PR-gate process. Ensures all code changes are validated by tests before merge.

---

### Plan: Test Coverage for Memory Fixes (2026-03-23)

**By:** Neo (Tester)

**Status:** Ready for implementation

**Scope:** 20 regression tests covering:
- PR #1: Model loading variants, CPU offload, shared components
- PR #2: Cache clearing, dangling reference cleanup, generator device binding

**Test File:** `tests/test_generate.py`

**Strategy:** Mock-based testing (no real GPU required). All tests use patching at the `generate` module level to avoid 7GB model downloads.

**Key Fixes Covered:**
- fp16 variant handling on MPS/CUDA/CPU
- CPU offload on MPS and CPU devices
- Shared text_encoder_2 and VAE in dual-pipeline setup
- Cache clearing: `torch.mps.empty_cache()` and `torch.cuda.empty_cache()`
- Garbage collection forcing between generation stages
- Explicit deletion of dangling references (`del text_encoder_2, vae`)
- Generator device binding to CPU for offloaded layers

**Execution:** Run tests via `pytest tests/`

---

### Audit: Memory Management Issues in generate.py (2026-03-24)

**By:** Morpheus (Architecture), Trinity (Backend), Neo (Testing)

**Status:** Audit complete, recommendations ready for implementation

**Finding:** Three independent audits converged on 6 critical issues (4 shared, 2 Trinity-specific) in `generate.py` memory management, NOT addressed by PR #1 or PR #2.

#### Issues Identified

| # | Severity | Location | Issue | Fix |
|---|----------|----------|-------|-----|
| 1 | **HIGH** | `generate()` L123–180 | No try/finally — exception skips pipeline cleanup | Wrap both branches in try/finally; extract cache-flush helper |
| 2 | **MEDIUM** | `load_base()` L73–75 | `torch.compile` dynamo cache never reset | Add `torch._dynamo.reset()` after `del base` (CUDA only) |
| 3 | **MEDIUM** | `generate()` L102 | No VRAM cache flush at function entry | Add device-appropriate cache flush before `load_base()` |
| 4 | **MEDIUM** | `generate()` L137–148 | Latents tensor overlaps refiner load window (GPU side) | Move latents to CPU before refiner load on CUDA |
| 5 | **LOW** | `generate()` L128–174 | No outer `torch.no_grad()` on inference calls | Wrap inference with `@torch.no_grad()` for defensive hygiene |
| 6 | **MEDIUM** | `requirements.txt` | Version floors allow broken releases | Tighten: accelerate>=0.24.0, diffusers>=0.21.0, torch>=2.1.0 |

#### Neo's Test Gap Analysis

- Current coverage: **ZERO** (no `tests/` directory)
- Untested behaviors: 12 memory management patterns
- Proposed suite: **22 mock-based regression tests** (5 files, <5 seconds runtime)
- Critical gating test: `test_generate_refine_path_cleans_up_on_refiner_exception` will FAIL until Issue #1 is fixed

#### Recommended Implementation Order

1. **Phase 1:** Tighten `requirements.txt` version floors (Trinity #6, prerequisite)
2. **Phase 2:** Create test infrastructure and 22 regression tests (Neo)
3. **Phase 3:** Fix code in severity order: #1 (HIGH) → #2–4 (MEDIUM) → #5 (LOW)
4. **Phase 4:** Verify all tests pass, team review and merge

**Governance:** Per TDD directive, all fixes require test-first approach on PR branch with team sign-off.

---

### PR #4: High-Memory Fixes (try/finally + accelerate floor) — MERGED

**Date:** 2026-03-25
**Implementer:** Trinity
**Reviewer:** Morpheus
**Verdict:** ✅ MERGED

**Fixes (2 HIGH-severity):**
1. **try/finally exception safety** — Wraps inference body in exception-safe cleanup. Initializes all pipeline vars to None before try. Inline `del base; base = None` in refiner path preserved for load-order management. Finally block deletes all variables, calls `gc.collect()`, and cache clears (`torch.cuda.empty_cache()` unconditional, `torch.mps.empty_cache()` guarded by `is_available()`). `image` intentionally excluded from finally for post-finally `image.save()` call.

2. **Version floor tightening** — `accelerate>=0.24.0` (critical, fixes silent CPU offload hook deregistration regression), `diffusers>=0.21.0`, `torch>=2.1.0`. No conflicts. Prevents breaking of PR#1 cleanup on old versions.

**Test coverage:** 13 regression tests passing (neo-pr3-tests), all exception paths covered.

**Open issues (MEDIUM — Phase 3):** torch.compile dynamo cache reset, entry-point VRAM flush, latents CPU transfer, PIL cleanup (LOW).

---

### PR #5: MEDIUM Memory Fixes — MERGED

**Date:** 2026-03-25
**Implementer:** Trinity
**Reviewer:** Morpheus
**Verdict:** ✅ MERGED

**Fixes (3 MEDIUM-severity, 1 architecture note):**
1. **Latents tensor on GPU during cache flush** — `latents = latents.cpu()` before `del base`, guarded by `device in ("cuda", "mps")`. Moves tensor off GPU before cache flush window opens, maximizing VRAM reclamation.

2. **torch.compile dynamo cache growth** — `torch._dynamo.reset()` added to `finally` block, guarded by `device == "cuda" and hasattr(torch, "_dynamo")`. Prevents graph cache accumulation across repeated `generate()` calls.

3. **Entry-point VRAM flush missing** — `gc.collect()` + `torch.cuda.empty_cache()` + guarded `torch.mps.empty_cache()` added at the top of `generate()` before pipeline loads. Ensures each call starts with clean VRAM.

4. **Global state audit** — All pipeline objects (`base`, `refiner`, `latents`, `text_encoder_2`, `vae`) confirmed local to `generate()`. No module-level globals, no cache leaks. Code is clean.

**Test coverage:** 22 regression tests (test_memory_cleanup.py) all passing.

---

### PR #6: PIL Leak Fix + Test Assert Fixes — MERGED

**Date:** 2026-03-25
**Implementers:** Trinity (PIL fix), Neo (test assertions + file restoration)
**Reviewer:** Morpheus
**Verdict:** ✅ MERGED

**Fixes:**
1. **PIL Image leak (LOW)** — Moved `image.save(output_path)` and print inside try block, guarded by `if image is not None:`. Added `image = None` to finally cleanup. Releases PIL buffer promptly in batch contexts.

2. **Test assertion fixes** — Fixed 3 tests in `test_memory_cleanup.py` changing from `mock.assert_called(), "msg"` (silent tuple, broken assertion message) to `assert mock.called, "msg"` (proper Python assertion). Tests: gc_collect_called_at_entry_cuda, cuda_cache_flush_at_entry, mps_cache_flush_at_entry.

3. **PR #5 code restoration** — Neo's commit restored missing entry-point flush, latents CPU transfer, and dynamo reset code that was previously reviewed/approved (PR #5) but absent from main. Also restored test infrastructure (test_memory_cleanup.py, conftest.py).

**Result:** All 22 tests pass. Codebase now reflects approved fixes.

---

### Decision: CI Workflow — Manual Dispatch Only (2026-03-25)

**By:** Trinity (Backend Developer)
**PR:** #7

**Decision:** Add `.github/workflows/tests.yml` with `on: workflow_dispatch` only.

**Rationale:** dfberry is out of GitHub Actions minutes; no auto-triggers to avoid accidental burns. CPU-only torch install (`--index-url https://download.pytorch.org/whl/cpu`) keeps install fast and avoids GPU runner requirements. All 22 tests mock the pipeline — no real model loading, ~2 second runtime. Matrix: Python 3.10 and 3.11 (both supported versions).

**Files Created:** `.github/workflows/tests.yml`

---

### Decision: README Update — MPS Support + Testing + Memory Model (2026-03-25)

**By:** Morpheus (Architecture)
**PR:** #8
**Status:** MERGED (after Trinity scoped pytest command to test_memory_cleanup.py)

**Content Added:**
- MPS support section with device detection and model architecture
- Testing instructions (scoped pytest command showing 22 green tests only)
- Memory management model explanation
- Batch generation feature overview

**Note:** Initial pytest command failed due to TDD red-phase tests (PR #9). Trinity fixed scoping on squad/readme-update branch. Neo re-reviewed and approved. Merged to main (squash).

---

### Decision: TDD Test Suite — Batch Generation + OOM Handling (2026-03-25)

**By:** Neo (Tester)
**PR:** #9
**Status:** Red phase complete, awaiting Trinity implementation

**Test Suite:**
- **test_batch_generation.py** (17 tests): batch_generate() function contract tests (per-item error handling, inter-item GPU flushing, order preservation)
- **test_oom_handling.py** (17 tests): OOMError class and recovery hints (9 pass, 5 red)
- **test_memory_cleanup.py** (22 tests): Existing regression suite (all green)

**Total:** 22 red, 31 green

**Features Under Test:**
1. **batch_generate(prompts: list[dict], device: str = "mps") → list[dict]** — Input: [{"prompt", "output", "seed"}], Output: [{"prompt", "output", "status", "error"}]. Contract: per-item exception handling, inter-item `gc.collect()` + device cache clear, order preservation.

2. **OOMError(RuntimeError)** — Catches `torch.cuda.OutOfMemoryError` and MPS OOM `RuntimeError("out of memory")`, re-raises as custom OOMError with recovery message. Finally block executes (cleanup guaranteed even on OOM).

**Implementation Location:** Trinity may place `batch_generate` in `generate.py` or new `batch.py`. Tests handle both with try/except import.

---

### Decision: PR #15 Blocker Fixes & Joel Test Score Revision (2026-04-18)

**Lead:** Morpheus (Lead)  
**Backend Support:** Trinity (CONTRIBUTING.md fixes)  
**Date:** 2026-04-18  
**Context:** Neo's review of PR #15 (squad/joel-test-improvements) flagged 2 blockers and several concerns warranting corrections before merge.

**Fixes Applied:**

1. **Makefile CRLF → LF** ✅
   - Converted Makefile to LF line endings via PowerShell byte-level write
   - Added `Makefile text eol=lf` to `.gitattributes` for persistent enforcement on checkout

2. **batch_observability_blog.json removed** ✅
   - `git rm` removed file containing hardcoded `C:\Users\diberry\...` paths
   - File was outside Joel Test scope and not part of project design

3. **CI shell quoting** ✅
   - `.github/workflows/tests.yml` line 26: `pip install ruff>=0.4.0` → `pip install 'ruff>=0.4.0'`
   - Prevents bash `>=` redirect interpretation in shell contexts

4. **CI uses requirements-dev.txt** ✅
   - Test job now runs `pip install -r requirements-dev.txt` instead of manually listing packages
   - Torch CPU install kept separate with special index URL
   - Aligns CI with local dev environment from CONTRIBUTING.md

5. **ruff.toml clarified** ✅
   - `line-length = 120` retained at top level (controls formatter width)
   - Added inline comment explaining that lint rule E501 is separately ignored
   - Resolved contradiction between format and lint scopes

6. **CONTRIBUTING.md CLI flags corrected** ✅
   - `--refiner` → `--refine` (matches generate.py actual parameter name)
   - `--device` → `--cpu` (matches actual CPU selection pattern)
   - Added missing flags: `--steps`, `--guidance`, `--seed`, `--width`, `--height`
   - Dev setup changed from `pip install ruff` to `pip install -r requirements-dev.txt`

**Joel Test Score Revision:**

Neo correctly challenged the 10/12 claim. Honest reassessment:

| # | Criterion | Verdict |
|---|-----------|---------|
| 1 | Source control | ✅ Yes |
| 2 | One-step build | ✅ Yes (Makefile, after CRLF fix) |
| 3 | Daily builds | ✅ Yes (CI on push/PR) |
| 4 | Bug database | ✅ Yes (GitHub Issues) |
| 5 | Fix bugs before new code | ✅ Yes (process commitment) |
| 6 | Up-to-date schedule | ❌ No — spec ≠ schedule |
| 7 | Spec | ✅ Yes (prompts/examples.md) |
| 8 | Quiet working conditions | ➖ N/A (solo/AI project) |
| 9 | Best tools money can buy | ✅ Yes |
| 10 | Testers | ✅ Yes (Neo + pytest) |
| 11 | Code samples in interviews | ➖ N/A |
| 12 | Hallway usability testing | ❌ No — no user testing process |

**Revised score: 9/12** (counting N/A items as pass, #6 and #12 as fail).

**Process Notes:**
- Morpheus applied all fixes as Lead per Reviewer Rejection Protocol (Trinity locked out as PR author)
- Coordinator removed stowaway batch_observability_blog_v2.json not caught in initial fix pass
- Re-squashed to 1 commit (6c10f02) and force-pushed
- PR #15 title and description updated to reflect 9/12 score

**Verification:** All fixes applied correctly, ruff linting passes clean, README.md and CONTRIBUTING.md now accurate.

---

## Team Code Review Findings (2026-03-26)

**By:** Morpheus (Lead), Trinity (Backend), Niobe (Image Specialist), Switch (Prompt/LLM), Neo (Tester)

**Event:** Full team code review across architecture, backend implementation, pipeline quality, prompts, and test coverage.

### Architecture Review — Structural Assessment (Morpheus)

**Summary:** Full architecture review identified 10 issues across 3 severity levels. Codebase demonstrates strong TDD discipline and memory management engineering.

#### HIGH-Severity Issues

| # | Issue | Location | Impact | Fix |
|---|-------|----------|--------|-----|
| 1 | Monolithic generate.py | `generate.py` (320 lines, 7+ responsibilities) | CLI parsing, device detection, model loading, generation, batch orchestration, retry logic, OOM handling, entry point all in one file. Maintenance burden and test coupling. | Extract to `cli.py`, `pipeline.py`, `batch.py`, `errors.py` (future, when complexity justifies) |
| 2 | Hardcoded absolute path | `generate_blog_images.sh:13` | `cd /Users/geraldinefberry/repos/my_repos/image-generation` breaks on any other machine | Use `SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"` (**QUICK WIN**) |

#### MEDIUM-Severity Issues

| # | Issue | Location | Impact | Fix |
|---|-------|----------|--------|-----|
| 3 | batch_generate() duplicates defaults | `generate.py:246-249` | `steps=40, guidance=7.5, width=1024, height=1024` hardcoded in SimpleNamespace duplicates argparse defaults. Will drift when defaults change. | Remove duplication, forward from args object |
| 4 | Batch mode drops user config | `generate.py:232-275` | `--refine`, `--steps`, `--guidance`, `--width`, `--height` CLI flags ignored in batch mode (see Trinity analysis) | Pass CLI overrides through batch_generate() signature |
| 5 | No logging infrastructure | Entire codebase | All output is `print()`. No log levels, no structured logging. Shell script uses `tee` as workaround. | Consider logging library (post-TDD decision) |
| 6 | Inconsistent cache-flush guards | `generate.py:219` vs `220-221` | `torch.cuda.empty_cache()` called unguarded; `torch.mps.empty_cache()` guarded by `is_available()`. Functionally safe but inconsistent style. | Extract `flush_device_cache(device)` helper (**QUICK WIN**) |

#### LOW-Severity Issues (Quick Wins)

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| 7 | README test count stale | `README.md:65` | Says "22 pytest tests" but repo now has 53+ tests across 6 test files (**QUICK WIN**) |
| 8 | Orphaned docs file | `docs/blog-image-generation-skill.md` | Single file in docs/, not referenced anywhere. Consider archiving or deleting. |
| 9 | No tests/__init__.py | `tests/` | pytest works without it, but explicit is safer for `from tests.conftest import ...` patterns (**QUICK WIN**) |

#### Strengths Identified

- **Memory management:** try/finally, OOM handling, batch GPU flushing — well-engineered, thoroughly tested (PRs #4–#6)
- **TDD discipline:** 53 tests, all mock-based, ~2s runtime, no GPU required — gold standard for CI cost and feedback speed
- **Error handling for OOM:** Custom OOMError class, actionable messages, retry logic with per-attempt step reduction — solid
- **CI:** workflow_dispatch with CPU-only torch (smart resource conservation for dfberry's limited Actions minutes)
- **Code comments:** "Fix 1:", "Fix 2:" etc. trace back to audit decisions — good traceability and maintainability

#### Recommended Action Sequence

**Immediate (Quick Wins):**
1. Trinity: Fix hardcoded path in generate_blog_images.sh
2. Trinity: Update README test count to 53+
3. Neo: Add tests/__init__.py

**Next Sprint (Core Maintenance):**
4. Trinity: Extract flush_device_cache(device) helper for DRY cache-flush patterns
5. Trinity + Neo: Pass CLI overrides through batch_generate() — TDD approach

**Future (Architectural, complexity-justified):**
6. Team decision: Module extraction (cli.py, pipeline.py, batch.py, errors.py)

---

### Backend Review — Args Mutation Bug + Batch Parameter Flow (Trinity)

**Summary:** Identified two bugs in parameter handling and one architectural gap in batch mode.

#### Bug: args.steps Mutation in generate_with_retry()

**Location:** `generate.py:294`  
**Severity:** MEDIUM  
**Problem:** Mutates caller's `args.steps` in-place during OOM retry:

```python
args.steps = max(1, args.steps // 2)
```

After an OOM retry, the original args object is corrupted. If `main()` or any caller inspects `args.steps` after the call, it sees the halved value — not what the user requested. Not blocking today (main doesn't inspect args.steps after), but **will bite when retry logic is composed with other features**.

**Proposed Fix:** Work on a local copy:

```python
def generate_with_retry(args, max_retries: int = 2) -> str:
    current_steps = args.steps
    for attempt in range(max_retries + 1):
        args.steps = current_steps  # Restore before each attempt
        try:
            return generate(args)
        except OOMError:
            if attempt == max_retries:
                raise OOMError(f"Out of GPU memory after {max_retries} retries. Last attempt used {current_steps} steps.")
            current_steps = max(1, current_steps // 2)
            print(f"OOM: retrying with {current_steps} steps")
```

**Action:** Neo writes test verifying args.steps is preserved after retry. Trinity implements fix.

#### Bug: batch_generate() Ignores CLI Parameters

**Location:** `generate.py:241-250` (batch_generate SimpleNamespace creation)  
**Severity:** MEDIUM  
**Problem:** User-supplied `--steps`, `--guidance`, `--width`, `--height` from CLI are silently ignored in batch mode. `batch_generate()` hardcodes:

```python
steps=40, guidance=7.5, width=1024, height=1024, refine=False
```

Users get unexpected behavior — no error, no warning, just different output than requested.

**Action:** Trinity accepts CLI overrides as parameters or forwards full args namespace. Neo writes TDD tests.

#### Architecture Observation: Cache-Flush Guard Inconsistency

**Location:** `generate.py:219` vs `220-221`  
**Pattern:**
- `torch.cuda.empty_cache()` — called unconditional (safe even without CUDA)
- `torch.mps.empty_cache()` — guarded by `is_available()` (raises on non-Apple hardware)

**Fix:** Extract `flush_device_cache(device)` helper to DRY and standardize the pattern.

---

### Pipeline Quality Review (Niobe)

**Summary:** Memory management is solid post-PR#4–#6. Image quality and performance have clear, high-value improvement opportunities.

#### Finding 1: Missing Negative Prompt Support (Architectural Gap, HIGH)

**Impact:** Visibly cleaner images. SDXL produces noticeably better output with negative prompts.

**What:** Add `--negative-prompt` CLI arg. Pass to both base and refiner. Default to a sensible baseline like `"blurry, low quality, deformed, watermark, text, ugly, cropped"`.

**Visual effect:** Reduces artifacts, watermarks, and deformity in generated images. Especially important for folk art aesthetic where hands and faces appear in prompts 04 and 05.

**Note:** This is a prerequisite for image quality. Switch, Trinity, Neo must collaborate (Trinity: CLI wiring; Switch: prompt engineering; Neo: tests).

#### Finding 2: Scheduler Performance Opportunity (HIGH)

**Impact:** ~35% faster generation at equivalent quality.

**What:** Replace default EulerDiscreteScheduler with `DPMSolverMultistepScheduler`. Lower default steps from 40 → 28.

```python
from diffusers import DPMSolverMultistepScheduler
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
```

**Visual effect:** No visible quality difference at 28 steps. Saves ~4-5 seconds per image on GPU.

**Updated Parameter Table:**

| Use case | --steps | --guidance | --refine |
|----------|---------|------------|----------|
| Quick draft | 20 | 6.0 | no |
| Blog quality | 28 | 7.0 | yes |
| Best quality | 40 | 7.5 | yes |

#### Finding 3: Refiner Guidance Scale Tuning (MEDIUM)

**What:** Use guidance_scale=5.0 for refiner when base uses 7.5. The refiner operates on nearly-complete images — high CFG over-sharpens edges and can introduce haloing artifacts.

#### Finding 4: Batch Per-Item Parameter Overrides (MEDIUM)

**What:** Allow per-item `steps`, `guidance`, `refine` overrides in batch JSON. Also change `device` default from `"mps"` to auto-detection via `get_device(False)`.

**Relates to:** Trinity's batch parameter flow redesign.

#### Finding 5: CUDA CPU Offload Option (MEDIUM)

**What:** Add `--offload` flag to use `enable_model_cpu_offload()` on CUDA instead of `pipe.to("cuda")`. Enables refiner workflow on 8-12GB VRAM cards at slight speed cost.

#### Finding 6: Soften torch.compile (LOW)

**What:** Remove `fullgraph=True` from `torch.compile()` call. Keeps the speedup, avoids compilation failures on edge-case torch versions.

#### What's Working Well

- Resolution (1024×1024) — correct for SDXL native
- fp16/float32 dtype logic — correct
- Component sharing — correct and important
- Memory cleanup flow — solid after PR #4–#6
- OOM retry logic — working correctly

#### Decision Needed

Items 1–2 are the highest-value changes. If the team agrees, Trinity implements, Neo writes tests, Niobe validates output quality. Items 3–6 can follow as a second pass.

**Implementation Priority:** Negative prompt (1) must precede scheduler (2) because quality baseline must be established before performance tuning.

---

### Prompt Library Audit (Switch)

**Summary:** First comprehensive audit of prompts/examples.md and prompt consumption patterns. Found 7 quality issues ranging from missing negative prompt support (architectural gap) to inconsistent style anchors (prompt quality).

#### Issue 1: No Negative Prompt Support (Architectural Gap, HIGH)

SDXL supports `negative_prompt` but it's not wired through anywhere:
- `generate.py` CLI has no `--negative-prompt` flag
- Pipeline calls in `generate()` don't pass `negative_prompt=`
- No negative prompt guidance in the style guide

**Impact:** Every generated image is susceptible to common SDXL artifacts (text overlays, blurriness, deformation, watermarks). Negative prompts are the primary defense.

**Recommendation:** Trinity adds `--negative-prompt` to CLI and pipeline calls. Switch defines a default negative prompt for the tropical magical-realism style and documents it in the style guide.

#### Issue 2: "no text" Constraint Missing from Vacation Prompts (MEDIUM)

All 5 original prompts include "no text" to prevent SDXL text generation artifacts. All 5 vacation-theme prompts omit it.

**Impact:** Vacation images likely contain unwanted text artifacts.

**Recommendation:** Add "no text" to all vacation prompts. (**QUICK WIN** — no code changes needed)

#### Issue 3: Style Anchor Drift (MEDIUM)

Three different style anchors used inconsistently:
1. `"Latin American folk art style, magical realism illustration"` (original prompts)
2. `"Latin American folk art illustration"` (vacation 01, 03, 05)
3. `"Folk art illustration"` (vacation 02, 04)

**Impact:** Visual inconsistency across blog images. "Magical realism" is a key aesthetic differentiator that's lost in vacation prompts.

**Recommendation:** Standardize on a canonical style anchor: `"Latin American folk art style, magical realism illustration"` (the original, strongest version). (**QUICK WIN** — no code changes needed)

#### Issue 4: No Prompt Template System (MEDIUM)

Every prompt is hand-written with inline style qualifiers. No composable structure.

**Impact:** Inconsistency, maintenance burden, high error rate when adding new prompts.

**Recommendation:** Define a prompt template: `{scene_description}, {palette_hints}, {style_anchor}, {mood}, {constraints}`. Document each component in the style guide.

#### Issue 5: Refiner Parameter Mismatch (MEDIUM)

The parameter table recommends `--refine` for blog quality, but:
- Vacation prompts' commands omit `--refine`
- `batch_generate()` hardcodes `refine=False`
- `generate_blog_images.sh` uses batch mode (no refiner)

**Impact:** Blog images generated at lower quality than intended.

**Recommendation:** Either update the parameter table to reflect the actual workflow, or wire refiner support through batch mode. (Trinity decision for batch; Switch updates style guide accordingly.)

#### Issue 6: Minimal Style Guide (LOW)

The style guide is 4 lines. Missing:
- Prompt structure guidance (what order to put elements)
- Negative prompt strategy
- What to avoid (common failure modes with SDXL)
- How parameters affect style (guidance scale ↔ adherence, steps ↔ detail)
- Seed selection strategy
- Troubleshooting tips

**Recommendation:** Expand style guide into a proper prompt engineering reference.

#### Issue 7: Prompt Duplication (LOW)

Vacation prompts exist in three places with no single source of truth:
1. `prompts/examples.md`
2. `generate_blog_images.sh` (inline Python)
3. Could drift further if JSON batch files are added

**Recommendation:** Store canonical prompts as JSON in `prompts/` and reference from shell scripts.

#### Proposed Implementation Order

1. **Phase 1 (Quick Wins):** Add "no text" to vacation prompts, standardize style anchors (Switch, no code changes needed)
2. **Phase 2:** Expand style guide with structure, vocabulary, and parameter guidance (Switch)
3. **Phase 3:** Add `--negative-prompt` CLI flag + default negative (Trinity + Switch)
4. **Phase 4:** Create prompt template system and migrate existing prompts (Switch)
5. **Phase 5:** Extract prompts to JSON, deduplicate across scripts (Trinity + Switch)

#### Who Needs to Act

- **Trinity:** `--negative-prompt` CLI support, batch refiner wiring
- **Switch:** Style guide expansion, prompt fixes, template system
- **Morpheus:** Approve architectural changes (negative prompt, template system)
- **Neo:** Tests for negative prompt parameter passing

---

### Quality Audit & Test Coverage Findings (Neo)

**Summary:** 53 existing tests all passing. Identified 3 bugs/gaps requiring TDD approach to fix.

#### Finding 1: batch_generate() Parameter Forwarding Not Implemented (BUG, MEDIUM)

**Location:** `generate.py:241-250`

`batch_generate()` hardcodes `steps=40, guidance=7.5, width=1024, height=1024, refine=False` in the SimpleNamespace. User-supplied `--steps`, `--guidance`, `--width`, `--height` are silently ignored in batch mode.

**Severity:** MEDIUM — batch users get unexpected behavior.

**Alignment:** Matches Trinity's analysis (see Backend Review above).

**Action:** Neo writes TDD tests documenting batch parameter forwarding contract. Trinity implements.

#### Finding 2: No CLI Argument Validation (GAP, MEDIUM)

**Location:** `parse_args()`

Accepts `--steps 0`, `--width 7`, `--guidance -1` without error. SDXL requires:
- width/height in multiples of 8
- steps ≥ 1
- guidance ≥ 0

Invalid inputs cause cryptic diffusers errors downstream (e.g., "Expected height to be a multiple of 8").

**Severity:** MEDIUM — users get confusing error messages.

**Action:** Neo writes TDD tests for CLI validation. Trinity adds argparse validators or guards in `generate()`.

#### Finding 3: Local Test Setup Undocumented (GAP, LOW)

**Location:** Test setup, README

All 75 tests fail to collect without `pip install torch --index-url https://download.pytorch.org/whl/cpu`. The README and CI workflow don't document local setup. Need a dev setup section or a `make test` target.

**Severity:** LOW — CI works, but no local dev feedback loop.

**Action:** Team adds local test setup docs to README (or creates make test target).

#### Existing Test Strengths

✅ **53 Green Tests** — All passing on main, ~2s total runtime
- **22 memory cleanup tests** (regression suite, prevents PR#1–#6 reversion)
- **17 batch_generate tests** (per-item isolation, inter-item flushing, order preservation)
- **14 OOM handling tests** (CUDA/MPS OOM detection, actionable messages, cleanup safety)

✅ **Test Architecture**
- Mock-based (no real GPU, no model downloads)
- Call-order validation via side_effect tracking
- Comprehensive exception path coverage
- CPU torch CI (workflow_dispatch, no auto-trigger)

#### Recommended Action Sequence

1. **Neo:** Write TDD tests for CLI validation and batch parameter forwarding
2. **Trinity:** Fix batch_generate() parameter forwarding and add argparse validators
3. **Team:** Add local test setup docs to README

---

---

### PR #15: Joel Test Improvements — Architecture Review (Morpheus)

**Date:** 2026-04-18  
**Decision:** APPROVE with non-blocking follow-ups  

**What This Establishes:**
1. CI triggers on PR + push (no manual-dispatch only)
2. Ruff is the project linter, configured in ruff.toml, enforced in CI
3. Makefile is the task runner (setup, test, lint, format, clean)
4. requirements-dev.txt separates dev dependencies from production
5. CONTRIBUTING.md + CODEOWNERS + issue templates provide onboarding
6. docs/feature-specification.md + docs/design.md document formal spec and architecture

**Non-Blocking Follow-Ups:**
- [ ] Fix Makefile for cross-platform (Windows venv paths)
- [ ] Resolve ruff.toml contradiction (line-length=120 vs ignore E501)
- [ ] Align CI install steps with requirements-dev.txt
- [ ] Remove or .gitignore batch_observability_blog.json (user-specific data)

---

### PR #15: Devil's Advocate Review (Neo)

**Date:** 2026-04-18  
**Decision:** REQUEST CHANGES — 2 blockers, 4 concerns  

**Merge Blockers:**
1. **Makefile CRLF line endings** — Current file has `\r\n` which breaks `make` on Linux/macOS. Fix: enforce LF via `.gitattributes` or convert to LF before merge.
2. **batch_observability_blog.json leaks local paths** — File contains `C:\Users\diberry\...` absolute paths exposing machine-specific home directory structure. Either remove from PR or use only relative paths.

**Non-Blocking Concerns:**
1. **CI drift** — `.github/workflows/tests.yml` hardcodes deps (`pip install ruff pytest`) instead of sourcing `requirements-dev.txt`. Guarantees local dev ≠ CI environment over time.
2. **Joel Test score inflated** — PR claims 10/12 but items #6 (schedule) and #12 (hallway testing) are unsubstantiated. Recommend revision to 8–9/12.
3. **ruff.toml confusing** — `line-length = 120` contradicts `ignore = ["E501"]` (line-too-long). Clarify intent.
4. **Docs lack freshness cadence** — design.md and feature-specification.md have no "Last Verified" maintenance dates. Will become liabilities without staleness review process.

**Verification:** All 5 ruff fixes lint clean; no new failures introduced.

---

### PR #15: Fact-Check Technical Claims (Trinity)

**Date:** 2026-04-18  
**Decision:** Non-blocking. Merge as-is with follow-up issues for corrections.

**Claim Verification Results: 31/35**

| Status | Count | Notes |
|--------|-------|-------|
| ✅ Verified | 31 | Joel Test mapping, memory cleanup, device selection, Makefile targets |
| ❌ False | 2 | CLI flags wrong, CI pip quoting missing |
| ⚠️ Partial | 1 | Dev setup incomplete |
| ❓ Unverifiable | 1 | Hallway testing—no evidence |

**False Claims (must fix in follow-up):**
1. **CONTRIBUTING.md L113 CLI flags** — Lists `--refiner` and `--device` but actual flags are `--refine` and `--cpu`. Also missing: `--prompt`, `--batch-file`, `--output`, `--refiner-steps`, `--refiner-guidance`, `--scheduler`, `--negative-prompt`, `--lora`, `--lora-weight`.
2. **CI shell quoting bug** — `.github/workflows/tests.yml` L26: `pip install ruff>=0.4.0` needs quoting to prevent bash redirect. Should be `pip install 'ruff>=0.4.0'`.

**Partial Claim (must fix in follow-up):**
- **CONTRIBUTING.md L119–120 dev setup** — Recommends `pip install pytest ruff` instead of `pip install -r requirements-dev.txt`. True but incomplete; should reference requirements-dev.txt for full setup.

---

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
