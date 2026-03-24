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

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
