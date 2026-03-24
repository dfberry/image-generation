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

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
