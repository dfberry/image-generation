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

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-04-21 — PR #88 & #89 Approved & Merged

Lead review and approval of both image/screenshot input support PRs.

**PR #88 (Manim) Architecture:**
- Consistent `image_handler.py` pattern: validates, copies to workspace, injects LLM context
- AST-based security in `scene_builder.py`: enforces literal-only ImageMobject filenames
- Policy parameter (`strict`/`warn`/`ignore`) for validation strictness
- Workspace isolation prevents path traversal, deterministic naming (`image_0_filename.png`)
- 67 tests all passing

**PR #89 (Remotion) Architecture:**
- Same `image_handler.py` interface, UUID-based naming to `public/` directory
- `component_builder.py` validates `staticFile()` calls, blocks dangerous patterns
- Policy parameter matches Manim for consistent UX
- 64 tests, 63 passing, 1 skip (platform-specific)

**Design Pattern Decision:** Separate `image_handler.py` per package enables independent evolution while maintaining consistent user-facing API and security model.

**Merge Status:** Both PRs squash-merged to main. Worktrees cleaned. Ready for documentation updates and integration testing.

### 2026-07-26 — Phase 4 Codebase Review Synthesis Complete

Synthesized all 6 review reports (D1-D7) into a prioritized executive report. **58 total findings** across 7 dimensions from 4 reviewers (Trinity, Niobe, Neo, Switch, Morpheus).

**Overall grade: B-** — Core engine earns A-/B+ but documentation (D+) and prompt drift (C+) drag the score down.

**Key cross-cutting themes discovered:**
1. **Stale satellite files** — Shell script prompts, batch JSONs, README defaults, and history.md all drifted from their canonical sources. Root cause: no single-source-of-truth enforcement for shared data (prompts, CLI defaults, file listings).
2. **Input validation gaps** — Batch JSON output path traversal (D6-002), unwhitelisted scheduler instantiation (D6-003), no batch schema validation (D6-007). Multiple vectors accept untrusted input.
3. **Test infrastructure barriers** — Module-level `import diffusers` blocks test collection (9/11 modules), stale patches in test_batch_generation.py test the wrong function, no coverage reporting in CI.
4. **Human figure style violations** — 4 canonical prompts and 3 doc examples violate the silhouette/backlighting rule, producing SDXL arm/hand distortion.
5. **Supply chain risks** — Models, dependencies, and Actions all use unpinned or loosely pinned versions.

**Prioritized action items:** 7 P0 (fix now), 10 P1 (this sprint), 13 P2 (next sprint), 16 P3 (backlog).

**Top 3 fixes for immediate impact:**
1. Fix README Options table (wrong defaults, missing 7 flags) — every user affected
2. Sanitize batch JSON output paths — security vulnerability
3. Sync shell script prompts with canonical library — off-brand image generation

**Key learning:** The biggest project risk isn't code quality — it's the gap between what docs say and what code does. Establishing single-source-of-truth patterns for CLI defaults, prompt text, and file inventories would prevent most of the drift found across D4/D5/D7.

**Report written to:** `.squad/decisions/inbox/morpheus-codebase-review-synthesis.md`

### 2026-04-19 — D5 Documentation Accuracy Review Complete

Performed thorough documentation accuracy review (Phase 2). **17 findings**: 4 CRITICAL, 4 HIGH, 5 MEDIUM, 1 LOW, 3 INFO.

**Critical issues:**
- README Options table has wrong defaults (`--steps` 40→22, `--guidance` 7.5→6.5) and is missing 8 of 16 CLI flags
- README says "22 tests" but the suite has 170 test functions across 11 files
- `docs/blog-image-generation-skill.md` says Python 3.14 (impossible version; project requires 3.10+)

**Key positive findings:**
- `docs/feature-specification.md` §4.1 is the most accurate and complete CLI reference — use it as source of truth
- `docs/design.md` architecture matches code accurately (minor stale file layout entry)
- CONTRIBUTING.md §Key Details has the most accurate flag list of any doc

**Internal doc issues:**
- history.md Key Paths says `--refiner`/`--device` (actual: `--refine`/`--cpu`) and references nonexistent `regen_fix.sh`
- CONTRIBUTING.md references nonexistent `tests/test_generate.py`

**Findings written to:** `.squad/decisions/inbox/morpheus-doc-accuracy-review.md`

### 2026-04-19 — Codebase Review Plan Designed

Designed a 7-dimension, 4-phase review plan covering: Code Quality (Trinity), SDXL Pipeline & GPU Safety (Niobe), Test Coverage (Neo), Prompt Library (Switch), Documentation Accuracy (Morpheus), Security (Neo), and CI/DevOps (Trinity).

**Key inventory findings during analysis:**
- Test suite has grown to **170 tests** across 11 files (~2,700 lines) — well beyond the 22/53 documented in README
- README Options table is severely stale: missing 7 CLI flags, wrong defaults for `--steps` (40 vs 22) and `--guidance` (7.5 vs 6.5)
- CONTRIBUTING.md references nonexistent `tests/test_generate.py`
- `docs/blog-image-generation-skill.md` says Python 3.14 (should be 3.10+) and has hardcoded macOS paths
- pytest-cov is in dev dependencies but no coverage config exists
- Makefile uses Unix paths exclusively — won't work on Windows

**Execution model:** Phase 1 runs 4 agents in parallel (Trinity/Niobe/Neo/Switch). Phase 2-3 are gated sequential reviews (docs, then security). Phase 4 is synthesis. Total estimated wall clock: ~18 min.

**Proposed 3 new skills:** `codebase-review`, `test-coverage-audit`, `doc-accuracy-check` — reusable checklists for future reviews.

**Plan written to:** `.squad/decisions/inbox/morpheus-codebase-review-plan.md`

### 2026-04-18 — PR #15 Blocker Fixes & Joel Test Score Revision (9/12)

Fixed 6 blockers flagged by Neo during PR #15 review:
1. **Makefile CRLF → LF** — PowerShell byte-level write + `.gitattributes` enforcement
2. **batch_observability_blog.json removed** — File with hardcoded paths, out of scope
3. **CI shell quoting** — `pip install 'ruff>=0.4.0'` prevents bash redirect
4. **CI requirements-dev.txt** — Test job now `pip install -r requirements-dev.txt`
5. **ruff.toml clarified** — `line-length = 120` at top level, inline comment on E501 ignore
6. **Joel Test Score Revised: 9/12** — Honest reassessment: #6 (schedule) and #12 (user testing) fail; N/A items pass

**Post-fix coordination:**
- Coordinator removed stowaway batch_observability_blog_v2.json
- Re-squashed to 1 commit (6c10f02), force-pushed
- PR #15 title/description updated to 9/12

**Verification:** ruff clean, CONTRIBUTING.md and README.md now accurate. Ready for merge.

### 2026-03-27 — Joel Test Assessment (6/12)

Conducted full Joel Test evaluation. **Strengths:** Source control discipline (YES), bug-fix-first TDD culture (YES), testing infrastructure with 53+ tests in ~2s (YES). **Gaps:** CI is manual-dispatch only (no PR triggers), no Makefile/task runner, no linter/formatter/type checker, only 1 GitHub Issue ever filed despite known bugs tracked informally in .squad/decisions.md, no CONTRIBUTING.md or issue templates, no milestones/releases/changelog, no pyproject.toml. Top 4 quick wins identified: (1) add `on: pull_request` to CI, (2) add ruff linting, (3) create Makefile, (4) create issue templates. These would raise score from 6/12 to ~9/12. Assessment written to `.squad/decisions/inbox/morpheus-joel-test-assessment.md`.

### 2026-03-26 — Full Team Code Review: Cross-Cutting Findings

All five team members reviewed the project simultaneously (2026-03-26 code review). Key cross-functional insights:

**Architectural Consensus:**
- Monolithic generate.py is sustainable for now; complexity doesn't yet justify module extraction. Revisit when responsibilities exceed 10.
- Try/finally memory management (PRs #4–#6) is the correct pattern for SDXL inference. Extend to all device-specific code paths.
- TDD approach with mock-based tests is proven — continue this discipline for all new features.

**Bug Convergence — Three independent audits identified the same 3 issues:**
1. **args.steps mutation:** Trinity and Neo both flagged `generate_with_retry()` mutating caller's args. Trinity detailed the fix; Neo is writing test.
2. **batch_generate() parameter drop:** Trinity (backend), Niobe (pipeline), Neo (testing) all independently discovered batch mode ignores CLI --steps, --guidance, --width, --height, --refine. This is a coordinated team effort to fix.
3. **Negative prompt gap:** Niobe (pipeline), Switch (prompts), and Trinity all identified this as a blocker for image quality. Architectural prerequisite before scheduler tuning.

**Quality Dependencies:**
- Negative prompt must be implemented before scheduler tuning (Niobe). Quality baseline first, then performance.
- Batch parameter forwarding blocks Niobe's per-item override feature. Trinity must fix batch first.
- CLI validation (Neo) and args mutation fix (Trinity) must sequence — validation catches bad inputs before they reach retry logic.

**Unblocked Quick Wins:**
- Fix hardcoded path in generate_blog_images.sh (Trinity)
- Update README test count (Trinity)
- Add "no text" to vacation prompts (Switch)
- Standardize style anchors (Switch)
- Add tests/__init__.py (Neo)

**Next Sprint Priority (Trinity + Neo TDD):**
1. Batch parameter forwarding (coordinated Trinity/Neo)
2. args.steps mutation fix (coordinated Trinity/Neo)
3. CLI argument validation (coordinated Trinity/Neo)



### 2026-03-25 — Architecture Review: Structural Assessment

Full codebase architecture review. Reviewed: generate.py (320 lines), 6 test files (53+ tests), shell scripts, README, CI, project structure.

**Key findings (10 issues):**

- **HIGH:** Monolithic generate.py (7+ responsibilities in one file), hardcoded absolute path in generate_blog_images.sh
- **MEDIUM:** batch_generate() duplicates argparse defaults (drift risk), batch mode drops user CLI overrides (--refine, --steps, etc.), no logging (all print()), inconsistent cache-flush guard style
- **LOW/Quick wins:** README test count stale (says 22, actually 53+), orphaned docs/ file, missing tests/__init__.py

**What's working well:** Memory management (try/finally + OOM + batch flush), TDD discipline (53 tests, ~2s, no GPU), OOM retry logic, CI resource conservation, code comment traceability.

**Recommended actions:**
1. Quick wins: fix shell path, update README count, add tests/__init__.py
2. Next sprint: extract flush_device_cache() helper, pass CLI overrides to batch_generate()
3. Future: module extraction when complexity justifies it (cli.py, pipeline.py, batch.py, errors.py)

**Decision written to:** `.squad/decisions/inbox/morpheus-architecture-review.md`

### 2026-03-25 — Sprint Complete: CI, README, TDD (All 4 Workstreams Merged)

**Sprint scope:** PR #7 CI workflow, PR #8 README update, PR #9 TDD tests + implementation

**Execution summary:**
- PR #7 (Trinity): Created `.github/workflows/tests.yml` with workflow_dispatch trigger, CPU torch, Python 3.10/3.11 matrix, ~2s runtime. ✅ MERGED
- PR #8 (Trinity + Morpheus design): Updated README (MPS support, testing, memory model, batch gen). Initial REJECT (pytest command), Trinity fixed scope, Neo APPROVED. ✅ MERGED
- PR #9 (Neo test design): Wrote 34 new tests (17 batch_generate, 17 OOMError — 22 RED, 12 GREEN). ✅ MERGED
- PR #9 (Trinity implementation): Implemented OOMError and batch_generate() to pass all 53 tests. Morpheus code review: ✅ APPROVE. ✅ MERGED

**Test results on main:**
| File | Red | Green | Total |
|------|-----|-------|-------|
| test_batch_generation.py | 0 | 17 | 17 |
| test_oom_handling.py | 0 | 14 | 14 |
| test_memory_cleanup.py | 0 | 22 | 22 |
| **Total** | **0** | **53** | **53** |

**Architecture delivered:**
1. **CI Workflow:** workflow_dispatch trigger, CPU-only torch install (180MB vs 2GB), ~2s test runtime, Python 3.10/3.11 coverage
2. **Memory Management:** try/finally cleanup (PR #1–#6), inter-item GPU flushing (PR #9), exception safety guaranteed
3. **Batch Generation:** `batch_generate()` function, per-item isolation, graceful error handling, order preserved
4. **OOM Handling:** `OOMError` class (CUDA + MPS detection), actionable error messages, finally block cleanup

**Code review verdicts:**
- Morpheus (Lead): All 13 acceptance criteria met (6 OOMError, 7 batch_generate, 3 integration). APPROVE.
- Trinity: Approved README update after Neo feedback loop. Approved PR #8 pytest scope fix.
- Neo: Approved PR #8 after fix. Approved PR #9 implementation (all 53 tests pass).

**Key learnings:**
- TDD discipline validates requirements before code exists. Tests serve as executable spec and gating criterion.
- Code review is gateway: Documentation (README) must match actual behavior (pytest command, test counts, expected failures).
- Exception safety: finally block executes unconditionally. Pattern: except transforms exception, finally cleans up.
- Memory management at scale: Batch operations must flush GPU memory between items to prevent cross-item accumulation.
- Production readiness: Both OOMError and batch_generate() fully tested, exception-safe, documented. Ready for batch workflows.

**Sprint status:** ✅ COMPLETE — Main branch stable with 53 passing tests, all 4 workstreams merged, team memory updated.



### 2026-03-25 — README Updated: Reflect Memory Fixes & Features

Updated README.md to document current project state post-PR #1–#6 (all memory audit issues resolved).

**Sections added/updated:**
1. **Setup → GPU Support** — Highlighted MPS (Apple Silicon) as primary target, CUDA as supported, CPU as fallback. Clarified `--cpu` flag usage.
2. **Dependency versions** — Added explicit version floors: `torch>=2.1.0`, `diffusers>=0.21.0`, `accelerate>=0.24.0` (critical for PR #1's cleanup strategy).
3. **Usage examples** — Reorganized to show device-detection flow first, then CPU override, then refinement options.
4. **Memory Management (new section)** — Documented automatic cleanup, exception safety, batch-safety. Highlights that all 7 audit issues are fixed.
5. **Testing (new section)** — Documented 22 pytest tests, no GPU required, ~2s runtime.
6. **Batch Generation (new section)** — Added `generate_blog_images.sh` reference.

**PR #8:** https://github.com/dfberry/image-generation/pull/8

**Architecture note:** README now accurately reflects the mature memory-safe design. All device paths (MPS/CUDA/CPU) are documented as first-class citizens.

### 2026-03-25 — PR #6 Code Review: PIL Leak Fix + Test Assert Fixes

Reviewed and APPROVED `squad/pr6-pil-leak-fix` (Trinity code fix, Neo test fixes). Both changes correct.

**Change 1 (Trinity — PIL leak fix):**
- `image.save()` moved inside `try` with `if image is not None:` guard. Guard is defensively correct (not strictly required since exception path already skips save, but harmless). Happy path unchanged. `image = None` in `finally` properly releases the PIL buffer after save. `return output_path` post-`finally` still correct — `output_path` defined before `try`.
- Closes the LOW-severity PIL leak identified in the original memory audit.

**Change 2 (Neo — test assert fixes + file restoration):**
- Root bug: `mock.assert_called(), "msg"` is a tuple expression (not an assertion). The comma silently detaches the message; `assert_called()` is called as a bare expression; the message is dropped. Tests appeared to pass even if the mock was never called.
- Fix: `assert mock.called, "msg"` — proper Python assertion with message. Semantically correct.
- Neo's commit also restored `tests/test_memory_cleanup.py`, `tests/conftest.py`, and the 3 MEDIUM code fixes (entry-point flush, latents CPU transfer, dynamo reset) from PR5 — which were documented as merged but absent from main. This wider scope is justified; tests and code are tightly coupled.
- All 22 tests pass.

**Architecture note:** PR5 code changes were documented as merged but never landed in main's `generate.py`. This was a scribe/merge gap — squad decisions documented the approval but the code wasn't actually in main. PR6 closes that gap. Recommend the scribe confirm main's final state post-merge.

**Decision:** Both changes APPROVED.

### 2026-03-25 — PR #5 Code Review & Approval: Four MEDIUM Memory Fixes

Reviewed and APPROVED `squad/pr5-medium-memory-fixes` (Trinity code, Neo tests). All four MEDIUM-severity issues correctly addressed.

**Fix reviews:**
1. **Latents CPU Transfer:** Order verified. `latents.cpu()` before `del base`. Device transfer uses `latents.to(device)` (MPS-aware). Guard correct.
2. **Dynamo Cache Reset:** In finally block. Both guards present: `device == "cuda"` and `hasattr(torch, "_dynamo")`. Comment flags MPS extension risk.
3. **Entry-Point VRAM Flush:** All 3 calls present, correct order, start of generate(). Two-flush pattern (entry + finally) intentional.
4. **Global State Audit:** Manual scan confirms. All pipeline vars are locals. Zero process-persistent refs. Clean architecture.

**Test review:** All 22 tests pass. 9 new MEDIUM tests use call-order tracking. Would catch regressions on active fixes 1, 2, 3. Fix 4 verified clean by inspection.

**Non-blocking finding:** 3 tests have orphaned assert message patterns. Neo follow-up for clarity, not a correctness issue.

**Decision:** APPROVED. All fixes correct. Code logic sound. Ready to merge.

### 2026-03-25 — PR #5 Code Review: Four MEDIUM Memory Fixes

Reviewed `squad/pr5-medium-memory-fixes` (Trinity's code, Neo's tests). All four MEDIUM-severity issues correctly handled.

**Fix 1 (latents CPU transfer):** `latents.cpu()` is placed before `del base` and before the mid-refine cache flush. Order confirmed in diff. Device transfer back uses `latents.to(device)` inline — not hardcoded `"cuda"`, MPS-safe. CPU path is correctly excluded via `if device in ("cuda", "mps")` guard. The `latents` variable holds the CPU copy until finally cleans it — benign.

**Fix 2 (dynamo reset):** `torch._dynamo.reset()` is inside `finally`. Dual guard: `device == "cuda"` (matches where `torch.compile` is actually used in `load_base()`, lines 72–75) AND `hasattr(torch, "_dynamo")` (protects against old torch versions). Both guards necessary and present.

**Fix 3 (entry-point flush):** All three calls present in correct order. Placed at the very start of `generate()` before `load_base()`. Two-flush pattern (entry + finally) is deliberate and correct.

**Fix 4 (global state audit):** Verified clean. All pipeline vars are locals in `generate()`. No module-level mutable pipeline state. Clean CLI architecture.

**Tests:** All 22 pass. 9 new MEDIUM tests use call-order tracking via `side_effect + call_log`. Would catch regressions on all three active fixes.

**One code smell found:** Three tests use `mock.assert_called(), "message"` — the comma makes the message an orphaned expression (not a pytest `assert`). Tests still catch regressions but custom messages don't surface on failure. Flagged for Neo follow-up, not blocking.

**Decision:** APPROVED.

### 2026-03-25 — PR #4 Code Review: try/finally + accelerate version floor

Reviewed `squad/pr3-high-memory-fixes` (Trinity's work). Both HIGH-severity issues are correctly fixed.

**try/finally analysis:**
- All five pipeline variables (`base`, `refiner`, `latents`, `text_encoder_2`, `vae`) initialized to `None` before `try`. `finally` deletes all five unconditionally — safe even when `base=None` mid-refine.
- The inline `del base; base = None` inside the refiner path is intentional load-order management (frees VRAM before `load_refiner()`), NOT duplicate cleanup. Setting `base = None` makes the `finally` deletion a safe no-op. Pattern is correct.
- `image` is intentionally excluded from `finally` cleanup — needed for the post-finally `image.save()` call. PIL image leak (LOW) is a known open issue, out of scope here.
- `torch.cuda.empty_cache()` called unconditionally in `finally` — correct, it's a no-op without CUDA. `torch.mps.empty_cache()` guarded by `is_available()` — also correct.
- Exception propagates correctly: if an exception fires inside `try`, `finally` cleans up, then exception propagates up. `image.save()` is unreachable in the exception path.
- Happy path unchanged: try completes, finally cleans pipelines, image is still live for save.

**requirements.txt analysis:**
- `accelerate>=0.24.0` — the critical fix. Versions below 0.24.0 silently skip CPU offload hook deregistration on `del pipe`, making PR#1's entire cleanup strategy inert.
- `diffusers>=0.21.0`, `torch>=2.1.0` — appropriate tightening.
- `transformers>=4.30.0` — not changed, within scope. No known equivalent hook regression.

**Remaining open (out of scope for this PR):** torch.compile dynamo cache reset (MEDIUM), entry-point VRAM flush (MEDIUM), latents tensor CPU transfer before refiner load (MEDIUM), PIL image cleanup (LOW).

**Decision:** APPROVED.

### 2026-03-23 — Memory Audit of generate.py (post PR #1 + PR #2)

Performed architectural memory review. Five issues found that survived both merged PRs:

1. **No exception safety (HIGH):** All `del`/cache-flush/gc calls are happy-path only. A single OOM or KeyboardInterrupt during inference leaves the full pipeline in VRAM with no cleanup. The fix is `try/finally` around the pipeline section — nothing else matters until this is in place.

2. **torch.compile dynamo cache (MEDIUM):** `torch.compile` on the UNet registers a graph in torch's process-global `_dynamo`/`_inductor` caches. `del base` + `gc.collect()` + `torch.cuda.empty_cache()` do NOT clear it. The compiled graph holds closure refs to model weights, potentially blocking VRAM reclaim. Fix: `torch._dynamo.reset()` after pipeline deletion on CUDA.

3. **No VRAM flush at function entry (MEDIUM):** `generate()` loads models immediately with no prior cache flush. Fragmented VRAM from prior operations (or prior calls in library mode) can cause spurious OOM. Mirror the exit cleanup at entry.

4. **Latent tensor bridges pipeline lifetimes (LOW–MEDIUM):** In refiner mode, the `latents` tensor from base inference is alive while the refiner loads. For SDXL at 1024×1024 fp16 this is ~0.5 MB — small now, but the pattern scales with resolution/additional pipelines.

5. **PIL image not deleted after save (LOW):** 3 MB in-process; harmless in CLI mode but accumulates in batch/library mode. Consistent with the explicit-cleanup discipline already established.

**Architecture note:** `generate()` is a flat function that owns model lifecycle. It has no error boundary. The team should consider whether model load/unload should move to a context manager to make cleanup unconditional and testable.

---

### 2026-03-24 — Cross-Agent Audit Sync

Morpheus's architectural audit converged with Trinity's code-level review and Neo's test-gap analysis:

**All three agents independently identified the same 4 core issues:**
1. No exception safety (HIGH) — Morpheus detail matches Trinity and Neo's critical test gap
2. torch.compile cache (MEDIUM) — Morpheus and Trinity both found it
3. Entry-point cache flush (MEDIUM) — Morpheus and Trinity both found it  
4. Latents tensor overlap (MEDIUM) — Morpheus and Trinity both found it

**Trinity added 2 more findings:**
- Defensive `torch.no_grad()` wrapping (LOW)
- Version floor vulnerability in requirements.txt (MEDIUM, cross-cutting)

**Neo identified critical testing gap:**
- 22 mock-based regression tests needed to protect PR#1 and PR#2 fixes
- Critical gating test: exception safety cleanup (fails until try/finally is added)

**Team consensus:** Full-audit summary merged into `.squad/decisions.md`. Morpheus is architecting Phase 3 (code fixes) to follow Neo's test infrastructure (Phase 2) and Trinity's version-floor tightening (Phase 1).

### 2026-03-25 — PR #4 Code Review: try/finally + accelerate version floor

Reviewed `squad/pr3-high-memory-fixes` (Trinity's work). Both HIGH-severity issues are correctly fixed.

**try/finally analysis:**
- All five pipeline variables (`base`, `refiner`, `latents`, `text_encoder_2`, `vae`) initialized to `None` before `try`. `finally` deletes all five unconditionally — safe even when `base=None` mid-refine.
- The inline `del base; base = None` inside the refiner path is intentional load-order management (frees VRAM before `load_refiner()`), NOT duplicate cleanup. Setting `base = None` makes the `finally` deletion a safe no-op. Pattern is correct.
- `image` is intentionally excluded from `finally` cleanup — needed for the post-finally `image.save()` call. PIL image leak (LOW) is a known open issue, out of scope here.
- `torch.cuda.empty_cache()` called unconditionally in `finally` — correct, it's a no-op without CUDA. `torch.mps.empty_cache()` guarded by `is_available()` — also correct.
- Exception propagates correctly: if an exception fires inside `try`, `finally` cleans up, then exception propagates up. `image.save()` is unreachable in the exception path.
- Happy path unchanged: try completes, finally cleans pipelines, image is still live for save.

**requirements.txt analysis:**
- `accelerate>=0.24.0` — the critical fix. Versions below 0.24.0 silently skip CPU offload hook deregistration on `del pipe`, making PR#1's entire cleanup strategy inert.
- `diffusers>=0.21.0`, `torch>=2.1.0` — appropriate tightening.
- `transformers>=4.30.0` — not changed, within scope. No known equivalent hook regression.

**Remaining open (out of scope for this PR):** torch.compile dynamo cache reset (MEDIUM), entry-point VRAM flush (MEDIUM), latents tensor CPU transfer before refiner load (MEDIUM), PIL image cleanup (LOW).

**Decision:** APPROVED.

### 2026-03-25 — PR #8: README Update (MPS Support, Testing, Memory Model, Batch Gen) — MERGED

**Sprint:** CI, README, TDD Sprint

**Changes made:**
- Added MPS support section with device detection guidance
- Updated Testing section with pytest instructions and test counts (22 regression tests)
- Documented memory management model (try/finally cleanup, inter-item cache flush, exception safety)
- Added Batch Generation feature overview
- Scoped pytest command to `pytest tests/test_memory_cleanup.py -v` (22 green tests only, avoiding TDD red-phase failures)

**Review flow:**
1. Trinity reviewed PR #8: APPROVED (all technical claims verified accurate)
2. Neo reviewed PR #8: REJECTED (initial pytest command showed 22 failures from TDD red-phase tests)
3. Trinity fixed scoping on `squad/readme-update` branch (commit scoped to test_memory_cleanup.py)
4. Neo re-reviewed PR #8 after fix: APPROVED
5. PR #8 merged to main (squash)

**Status:** ✅ MERGED

**Architectural note:** README now correctly explains the memory model and batch generation as design decisions, not just features. Readers understand why `generate()` flushes GPU state and how batch workflows should manage inter-iteration cleanup.

### 2026-03-25 — PR #7 Code Review CONDITIONAL REJECT (TDD Red-Phase Tests)

**Sprint:** TDD Batch Generation + OOM Handling

**Initial Assessment:** PR #7 adds batch generation feature with TDD red-phase tests (`test_batch_generation.py` + `test_oom_handling.py`). Tests intentionally fail (TDD red phase). Running `pytest tests/ -v` runs 53 tests:
- 22 regression tests (test_memory_cleanup.py) — PASSING
- 17 batch generation tests (test_batch_generation.py) — RED (expected to fail, not yet implemented)
- 14 OOM handling tests (test_oom_handling.py) — RED (expected to fail, not yet implemented)

**Rejection Basis:** PR #7 must not land with failing tests in the `tests/` scope. Adding TDD red-phase tests to the suite breaks CI/CD. Either:
1. Scope the failing tests out of pytest's default run (e.g., move to `tests/tdd/` and exempt from `pytest tests/ -v`), OR
2. Wait for the implementation PRs to land first, so tests pass when added.

**Conditional Approval:** "After pytest scope is corrected, this PR will be APPROVED."

**Resolution:** Trinity completed TDD green phase (PR #9). All 53 tests now pass. Tested on squad/tdd-batch-oom-tests branch:

### 2026-04-18 — PR #15 Review: Joel Test Improvements (6/12 → 10/12)

Reviewed PR #15 (`squad/joel-test-improvements` → `main`). 33 files changed, 1968 insertions, 576 deletions. **Verdict: APPROVE with non-blocking items.**

**What landed well:** CI pipeline design (PR triggers + concurrency + lint gate), Makefile with correct targets, ruff.toml with sensible defaults, requirements-dev.txt with `-r requirements.txt` include, CONTRIBUTING.md with accurate project info, issue templates, CODEOWNERS. Feature spec (42 functional requirements) and design doc (674 lines) are high-quality — they document actual code behavior, not boilerplate. Lint fixes across 12 test files are clean (unused imports removed, import ordering fixed).

**Issues found (non-blocking):**
1. **Makefile is Unix-only** — hardcoded `$(VENV)/bin/python` paths won't work on Windows. Project README shows Windows venv activation, so this creates a gap. Not blocking since CI runs Linux.
2. **ruff.toml contradicts itself** — sets `line-length = 120` but then `ignore = ["E501"]` (line-too-long). Either enforce the limit or don't set it.
3. **CI doesn't use requirements-dev.txt** — the test job manually installs packages instead of `pip install -r requirements-dev.txt`. The lint job installs ruff directly. This means requirements-dev.txt and CI can drift apart.
4. **batch_observability_blog.json** snuck in — contains hardcoded Windows paths to another repo. This is user-specific working data, not project infrastructure. Should be in .gitignore or a separate PR.
5. **PR scope is large** — 33 files is a lot for one PR, but each change is small and thematically coherent (Joel Test improvements). Acceptable for infrastructure work.

**Decisions:** CI runs on PR + push to main. Ruff is the project linter/formatter. Makefile is the task runner. TDD workflow remains enforced.
```
$ python -m pytest tests/ -v 2>&1 | tail -1
============================== 53 passed in 2.45s ==============================
```

**Re-Assessment (2026-03-25):**
- Rejection condition: "pytest scope must not have failing tests" ✅ **SATISFIED** (via implementation, not structural change)
- All 53 tests passing — 22 regression + 17 batch gen + 14 OOM handling
- No test failures blocking CI
- Code changes architecturally sound: batch generation follows existing memory cleanup patterns, OOM handling properly routes exceptions

**Verdict:** ✅ **APPROVED** — PR #7 ready to merge. Rejection condition satisfied by test implementation completing green phase rather than test refactoring. Both paths lead to passing pytest scope.

### 2026-03-25 — PR #9 Code Review: OOMError + batch_generate() — APPROVE ✅

**Verdict:** ✅ **APPROVE — Merge to main**

**Sprint:** TDD Green Phase (batch generation + OOM handling)  
**Status:** All 53 tests pass

**Summary:**
Reviewed Trinity's implementation of OOMError and batch_generate() against 10-point code review checklist. All criteria met.

**OOMError (class, lines 20-22, except clause lines 197-207):**
1. ✅ Subclasses RuntimeError (line 20)
2. ✅ CUDA OOM detection: isinstance(exc, torch.cuda.OutOfMemoryError) with hasattr guard (lines 198-200)
3. ✅ MPS OOM detection: isinstance(exc, RuntimeError) and "out of memory" in str(exc).lower() (line 202)
4. ✅ finally block executes after OOM (lines 208-222 guaranteed by Python finally semantics)
5. ✅ Error message actionable: "Out of GPU memory. Reduce steps with --steps or switch to CPU with --cpu." (line 205) — mentions both --steps AND --cpu
6. ✅ Non-OOM exceptions not swallowed: bare `raise` on line 207 re-raises non-OOM exceptions

**batch_generate() (lines 227-270):**
1. ✅ Calls generate() once per item (loop lines 235-248)
2. ✅ GPU memory flush BETWEEN items: gc.collect() + torch.cuda.empty_cache() + guarded torch.mps.empty_cache() on lines 264-268, guarded by `if i < len(prompts) - 1` so flush occurs between items, not after last
3. ✅ Per-item failure graceful: try/except around generate() (lines 247-261), appends error dict with exception message, continues
4. ✅ Empty list returns [] immediately: for loop on empty list yields no iterations, no generate() or gc calls
5. ✅ Result order preserved: iterates and appends in order
6. ✅ Never raises on all-failures: all exceptions converted to error dicts in results list
7. ✅ Signature clean: `batch_generate(prompts: list[dict], device: str = "mps") -> list[dict]` matches spec

**Integration:**
8. ✅ Existing try/finally cleanup functional: all code intact (lines 137-224)
9. ✅ OOM except clause does not interfere: re-raised as OOMError (RuntimeError subclass), finally executes normally after except
10. ✅ Code readable and maintainable: inline comments explain Fixes 1–3; clear logic; good variable names

**Test Coverage:** 53 tests all passing (2.67s)
- 22 regression tests (existing memory cleanup)
- 17 batch_generate() tests (per-item call, inter-item flushing, failure handling, ordering, edge cases)
- 14 OOMError tests (CUDA OOM, MPS OOM, message content, finally cleanup, state clean after OOM)

**Quality Assessment:**
- Exception safety guaranteed (finally block unconditional)
- OOMError design correct (dual detection, version-safe guards, actionable message)
- batch_generate() contract clean (no abort on per-item failure, order preserved, never raises)
- No functional bugs found
- Code maintainable and tested

**Minor observations (non-blocking):**
- MPS cache clear in batch_generate could be device-guarded (currently just is_available()), but safe no-op on non-MPS devices
- torch.cuda.empty_cache() called unconditionally on all devices in batch, but safe no-op pattern consistent with generate() line 214

**Result:** Production-ready. Both OOMError and batch_generate() are fully implemented and tested. Ready to merge.

---

**Decision:** ✅ APPROVE — Merge to main. All tests pass, all acceptance criteria met, no bugs found, code is maintainable and production-ready.

---

### 2026-03-24 — Code Review PR #10: OOM Auto-Retry (generate_with_retry)

**Assignment:** Code review of Trinity's PR #10 (squad/oom-retry)

**Feature Reviewed:** generate_with_retry(args, max_retries=2) implementation for OOMError handling with step reduction

**Review Findings:**
1. **Correctness:** Correctly implements step halving (floor at 1), retries on OOMError, prints warnings, re-raises with context on exhaustion. Verified by 12 passing tests.
2. **Regressions:** main() logic updated correctly to dispatch to generate_with_retry for single-prompt mode while preserving batch mode path. Argument parsing ensures mutual exclusivity.
3. **Safety:** Retry loop respects existing finally cleanup in generate().
4. **Testing:** 12 tests cover all critical paths including edge cases (steps=1 floor, max_retries exhaustion).
5. **CI:** No new workflows added.

**Architectural Recommendation (Deferred):** Future work should update batch_generate() to utilize generate_with_retry() logic for consistent OOM handling across both single-prompt and batch modes. Currently batch fails immediately on OOM for a single item while single-prompt mode retries. Acceptable for this PR's scope but represents architectural inconsistency. Noted in decisions.md as future enhancement.

**Verdict:** ✅ APPROVED — Ready to merge to main

**PR Status:** ✅ MERGED to main

**Test Impact:**
- 12/12 test_oom_retry.py tests pass (all of Neo's red-phase contracts satisfied)
- Zero regressions in full test suite

---

## Full Team Code Review (2026-03-26)

**Event:** Comprehensive 5-agent code review of image-generation project  
**Scope:** Architecture, backend, pipeline quality, prompts, testing  
**Outcome:** 10 issues identified (3 HIGH, 4 MEDIUM, 3 LOW)

**Morpheus Role & Findings:**
- **Lead Responsibilities:** Architecture assessment, scope decisions, cross-team coordination
- **Key Findings:** Monolithic generate.py (7+ responsibilities), hardcoded paths, args mutation bug
- **Recommendations:** Phase 1/2/3 implementation sequence with TDD-first approach

**Cross-Cutting Observations:**
- Code quality high overall; memory management solid; TDD discipline strong
- Team strengths: Error handling, CI efficiency, test coverage (53+ tests)
- Main gaps: CLI validation, batch parameter forwarding, negative prompt support, prompt templates

**Issues Identified by Morpheus:**
1. Monolithic generate.py — 7+ responsibilities (Phase 3 consideration)
2. Hardcoded path in shell scripts — HIGH priority Phase 1
3. args.steps mutation — HIGH priority Phase 2
4. Cache guard inconsistency — MEDIUM Phase 2 (DRY refactor)
5. Batch parameter forwarding gap — MEDIUM Phase 2 (TDD-first)

**Recommended Implementation Path:**
- Phase 1: Fix paths, update docs, add __init__.py (quick wins)
- Phase 2: Fix mutations, batch forwarding, validation (TDD-first, all changes)
- Phase 3: Negative prompts, template system, quality tuning (architectural features)

**Blocking Dependencies Identified:**
- Trinity must wire --negative-prompt CLI before Switch/Niobe can finalize style guide and tuning
- Batch parameter forwarding: Neo writes tests first, Trinity implements

**Team Coordination Notes:**
- All Phase 2 work must follow TDD-first discipline
- Decisions merged to decisions.md (see Full Team Code Review section)
- Orchestration logs filed for all 5 agents (morpheus/trinity/neo/niobe/switch)
- Team ready for Phase 1 quick wins immediately

### 2026-04-18 — PR #15 Architecture Review: Joel Test Improvements

**Scope:** Comprehensive architecture review of PR #15 (squad/joel-test-improvements → main). 33 files changed, 1968 additions, 576 deletions. Claims Joel Test improvement from 6/12 → 10/12.

**What Landed Well:**
- **CI pipeline design:** PR + push triggers, lint gate, concurrency groups — eliminates manual-dispatch bottleneck
- **Makefile structure:** Correct targets (setup, test, lint, format, clean), venv-relative paths
- **ruff.toml:** Sensible defaults (Python 3.10, 120 chars, E/F/W/I rules)
- **requirements-dev.txt:** Properly chains base requirements + dev tools
- **CONTRIBUTING.md:** Accurate project setup, TDD workflow documented, PR process clear
- **Issue templates:** Bug report and feature request templates standardized
- **Feature spec (docs/feature-specification.md):** 42 functional requirements, documents actual behavior
- **Design doc (docs/design.md):** 674 lines covering architecture and implementation details
- **Lint fixes:** 12 test files cleaned (unused imports, import order fixed)

**This Establishes:**
1. CI triggers on every PR + push to main (gates on lint before tests)
2. Ruff is the project linter/formatter (single source of truth in ruff.toml)
3. Makefile is the task runner (developers run `make install-dev`, `make test`, `make lint`)
4. requirements-dev.txt separates dev dependencies from production
5. CONTRIBUTING.md + CODEOWNERS + issue templates form the onboarding path
6. docs/feature-specification.md + docs/design.md document formal spec and architecture

**Issues Found (Non-Blocking — Create Follow-Ups):**

1. **Makefile is Unix-only** — Hardcoded `$(VENV)/bin/python` paths will fail on Windows. Project README documents Windows venv activation (`call venv\Scripts\activate.bat`), so this creates a compatibility gap. Not blocking since CI runs Linux, but affects Windows contributor experience.

2. **ruff.toml self-contradiction** — Sets `line-length = 120` then immediately `ignore = ["E501"]` (line-too-long). Clarify intent: either enforce the limit or don't set it. This confusion will bite contributors who expect linting rules to match config comments.

3. **CI doesn't use requirements-dev.txt** — The test job manually installs packages (`pip install ruff pytest`) instead of sourcing `requirements-dev.txt`. This decoupling guarantees drift between local dev environment and CI over time. Single source of truth principle violated.

4. **batch_observability_blog.json stowaway** — File contains Windows-specific paths (`C:\Users\diberry\...` absolute paths). This is user-specific working data, not project infrastructure. Should either be removed from this PR or moved to .gitignore.

5. **PR scope is large but acceptable** — 33 files is significant, but changes are small and thematically coherent (all Joel Test infrastructure). This is one of few justifiable cases for large PR (infrastructure/setup work). 

**Verdict:** ✅ **APPROVE with non-blocking follow-ups**

**Implementation consensus:**
- Joel Test mapping (items #1–#5, #7–#11) is correct
- Infrastructure decisions (CI, Makefile, requirements, linting) are sound
- Documentation (spec + design) is comprehensive and accurate
- Create follow-up issues to address the 5 non-blocking items above

---



## [2026-04-21T17:31:43Z] Team Status: PR #88 & #89 Bug Fixes Complete

**Status:** Both PRs ready for re-review

Neo completed bug fixes on both PRs following reviewer lockout protocol:

### PR #88 Manim (6 bugs fixed)
- Symlink validation security contract restored
- AST security hardening (exec/eval/open/__import__)
- Error handling and caching improvements
- 139 tests pass

### PR #89 Remotion (5 bugs fixed)  
- TSX import destructuring fixed
- Path traversal hardening
- Protocol matching normalization
- 109 tests pass

### PR #89 Remotion Tests (2 bugs fixed)
- Trinity fixed Neo's test implementation
- Real CLI entry point validation
- Exit code semantics validated
- 13 CLI tests pass

All branches pushed: squad/88-manim-image-support, squad/89-remotion-image-support
Ready for Lead architecture re-review.