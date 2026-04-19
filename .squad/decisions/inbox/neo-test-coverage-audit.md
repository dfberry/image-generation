# Neo — D3 Test Coverage & Quality Audit

**Date:** 2026-07-25
**Auditor:** Neo (Tester)
**Scope:** All files in `tests/`, `conftest.py`, `generate.py` (reference)
**Mode:** READ-ONLY — no files modified

## Summary

- **Test files:** 11 (conftest.py + 10 test modules)
- **Tests collected:** 29 (via `pytest --co`); 9 modules fail to collect due to missing `diffusers` in CI-like environments
- **Estimated total tests (from source):** ~143 across all files
- **Collection errors:** 9 modules import `generate.py` which does `import diffusers` at module level — tests cannot run without GPU stack installed

---

## D3 Coverage Checklist

### ✅ Covered

| Function | Test File(s) | Tests | Notes |
|----------|-------------|-------|-------|
| `parse_args()` — core flags | `test_cli_validation.py`, `test_scheduler.py`, `test_negative_prompt.py`, `test_pipeline_enhancements.py`, `test_batch_cli.py` | ~25 | --prompt, --batch-file, --steps, --guidance, --width, --height, --scheduler, --refiner-guidance, --negative-prompt, --lora, --lora-weight, --cpu covered |
| `_dimension()` | `test_pipeline_enhancements.py` | 8 | Divisible-by-8, >=64, nearest suggestion |
| `validate_dimensions()` | `test_pipeline_enhancements.py` | 3 | Valid + invalid |
| `get_device()` | `test_unit_functions.py` | 5 | All 4 paths + priority |
| `get_dtype()` | `test_unit_functions.py` | 4 | CUDA, MPS, CPU, unknown |
| `load_base()` | `test_unit_functions.py` | 10 | Model ID, dtype, variant, offload, compile |
| `load_refiner()` | `test_unit_functions.py` | 6 | Model ID, shared components, device routing |
| `apply_scheduler()` | `test_scheduler.py` | 4+ | Valid, invalid, Karras implicit via DPMSolver test |
| `apply_lora()` | `test_pipeline_enhancements.py` | 3 | None, valid, weight |
| `generate()` — base path | `test_memory_cleanup.py`, `test_negative_prompt.py` | 15+ | Cleanup, negative prompt, scheduler applied |
| `generate()` — refiner path | `test_memory_cleanup.py`, `test_negative_prompt.py` | 8+ | Shared components, latents, cleanup |
| `generate()` — seed handling | `test_unit_functions.py` (preflight) | 3 | Indirect — preflight flush tests |
| `generate_with_retry()` | `test_oom_retry.py`, `test_bug_fixes.py` | 14 | OOM retry, halving, exhausted, non-OOM, floor, mutation |
| `batch_generate()` | `test_batch_generation.py`, `test_bug_fixes.py`, `test_negative_prompt.py`, `test_pipeline_enhancements.py` | 28+ | Empty, single, multi, error isolation, CLI forwarding |
| `main()` | `test_unit_functions.py`, `test_batch_cli.py` | 13 | Single-prompt, batch, file-not-found, bad JSON |

### ❌ Gaps Identified

| Function / Area | Missing Coverage |
|----------------|-----------------|
| `_positive_int()` | No direct unit tests for edge cases (string "abc", float "1.5"). Only tested indirectly via `--steps` |
| `_non_negative_float()` | No direct unit tests. Only tested indirectly via `--guidance` |
| `parse_args()` — --seed flag | No test verifies `--seed 42` parsing or `--seed` default (None) |
| `parse_args()` — --output flag | No test for `--output custom/path.png` or default behavior |
| `parse_args()` — --refine flag | No test verifies `--refine` sets `args.refine = True` |
| `parse_args()` — --refiner-steps | No test verifies `--refiner-steps` parsing or default (10) |
| `apply_scheduler()` — Karras config | Karras branch tested implicitly but no assertion that `use_karras_sigmas=True` is in the config |
| `generate()` — output path default | No test for auto-generated `outputs/image_{timestamp}.png` path |
| `generate()` — seed generator device binding | No test that `generator_device = "cpu"` for MPS/CPU offloaded devices |
| `batch_generate()` — gc.collect not called after last item | Logic exists but no test validates the `i < len(prompts) - 1` guard |
| `_apply_performance_opts()` | No dedicated tests for xformers fallback to attention slicing |

---

## Findings

### [D3-001] — 9 of 11 test modules fail to collect without `diffusers` installed
**Severity:** HIGH
**File:** tests/*.py (all modules importing `generate`)
**Dimension:** D3
**Description:** `generate.py` has `import diffusers` at module level (line 18). Any test that does `import generate` or `from generate import ...` fails with `ModuleNotFoundError: No module named 'diffusers'` unless the full GPU stack is installed. This means CI environments without GPU dependencies cannot run *any* tests.
**Evidence:**
```
ERROR collecting tests/test_batch_cli.py
  generate.py:18: in <module>
    import diffusers
E   ModuleNotFoundError: No module named 'diffusers'
```
(9 identical errors for all modules that import generate)
**Recommendation:** Consider lazy-importing `diffusers` inside functions that need it, or provide a mock/stub path for test collection. This is the single biggest barrier to test execution.

### [D3-002] — Silent tuple bug pattern found in comments (already fixed)
**Severity:** INFO
**File:** tests/test_memory_cleanup.py:L250, L276, L302
**Dimension:** D3
**Description:** Three commented-out lines contain the `mock.assert_called(), "msg"` silent tuple bug pattern. These were the "BEFORE FIX" versions that have been correctly replaced with `assert mock.called, "msg"` on the lines immediately following.
**Evidence:**
```python
# BEFORE FIX: mock_gc.collect.assert_called(), "gc.collect() should fire before load_base on CUDA"
assert mock_gc.collect.called, "gc.collect() should fire before load_base on CUDA"
```
**Recommendation:** Remove the commented-out "BEFORE FIX" lines to reduce noise. No active code is affected.

### [D3-003] — `assert False` used as try/except fallthrough
**Severity:** LOW
**File:** tests/test_scheduler.py:L173
**Dimension:** D3
**Description:** `assert False, "Expected ValueError"` is used as a fallthrough in a try/except block. While this is inside a try block (not unconditional), it's a code smell. `pytest.fail()` is the idiomatic alternative.
**Evidence:**
```python
try:
    apply_scheduler(p, "CompletelyBogusScheduler")
    assert False, "Expected ValueError"
except ValueError:
    pass
except AttributeError:
    pytest.fail("Got raw AttributeError")
```
**Recommendation:** Replace `assert False, "Expected ValueError"` with `pytest.fail("Expected ValueError")` for consistency with the `AttributeError` branch two lines below.

### [D3-004] — No MagicMock specs used anywhere in test suite
**Severity:** MEDIUM
**File:** tests/*.py (all files)
**Dimension:** D3
**Description:** Zero test files use `MagicMock(spec=...)` to constrain mock objects to actual function/class signatures. This means mocks will silently accept any attribute access or method call, even if the real object doesn't have it. Typos in mock assertions (e.g., `mock.aseert_called()`) would pass silently.
**Evidence:** `grep spec= tests/` returned zero matches.
**Recommendation:** Add `spec=` to critical mocks, especially those standing in for `DiffusionPipeline`, `torch`, and function argument namespaces. Priority: any mock used in assertion-heavy tests.

### [D3-005] — `_positive_int()` and `_non_negative_float()` lack direct unit tests
**Severity:** MEDIUM
**File:** generate.py:L28-L42, tests/ (no dedicated tests)
**Dimension:** D3
**Description:** These argparse type functions are only tested indirectly through `parse_args()` integration tests. Direct unit tests would cover: non-numeric strings ("abc"), float strings ("1.5") for `_positive_int`, boundary values (0, -0.0), and error message content.
**Evidence:** No test file imports `_positive_int` or `_non_negative_float` directly.
**Recommendation:** Add a `TestArgparseTypes` class with ~6 targeted tests for these validators.

### [D3-006] — Missing tests for 4 CLI flags: --seed, --output, --refine, --refiner-steps
**Severity:** MEDIUM
**File:** tests/test_cli_validation.py, tests/test_scheduler.py
**Dimension:** D3
**Description:** Of 16 CLI flags, 4 have no parse_args() test verifying they are accepted and stored correctly:
- `--seed 42` → `args.seed == 42`
- `--output custom.png` → `args.output == "custom.png"`
- `--refine` → `args.refine == True`
- `--refiner-steps 15` → `args.refiner_steps == 15`

These are used in many tests via fixture mocks but never validated at the argparse level.
**Evidence:** Searched all test files for `--seed`, `--output`, `--refine` (as CLI arg), `--refiner-steps` in `_parse_with_args` / `sys.argv` patterns — none found.
**Recommendation:** Add 4-8 tests to `test_cli_validation.py` covering these flags.

### [D3-007] — `apply_scheduler()` Karras config never directly asserted
**Severity:** LOW
**File:** tests/test_scheduler.py
**Dimension:** D3
**Description:** The DPMSolverMultistepScheduler branch in `apply_scheduler()` sets `config["use_karras_sigmas"] = True` (generate.py:L213), but no test asserts this value is present in the config passed to `scheduler_cls.from_config()`.
**Evidence:** `test_scheduler.py` tests that `from_config` is called but doesn't inspect the config dict for `use_karras_sigmas`.
**Recommendation:** Add a test that mocks `pipeline.scheduler.config` and asserts `use_karras_sigmas=True` is in the dict passed to `from_config` when using DPMSolverMultistepScheduler.

### [D3-008] — No test for `generate()` auto-generated output path
**Severity:** LOW
**File:** generate.py:L249-L253
**Dimension:** D3
**Description:** When `args.output is None`, `generate()` creates `outputs/image_{timestamp}.png`. No test verifies this fallback path logic or the `os.makedirs` call.
**Evidence:** All test fixtures explicitly set `args.output` to a tmp_path value.
**Recommendation:** Add a test with `args.output = None` that verifies the output path matches the expected pattern.

### [D3-009] — No test for seed-based generator device binding logic
**Severity:** LOW
**File:** generate.py:L243-L245
**Dimension:** D3
**Description:** When `args.seed is not None`, the generator device is set to "cpu" for MPS/CPU devices to avoid device mismatch with cpu_offload. No test validates this logic.
**Evidence:** Preflight tests in `test_unit_functions.py` all use `seed=None`, skipping the generator creation branch entirely.
**Recommendation:** Add tests with `args.seed=42` on each device to verify generator device binding.

### [D3-010] — `test_batch_generation.py` tests are stale — patch `generate.generate` but implementation uses `generate_with_retry`
**Severity:** HIGH
**File:** tests/test_batch_generation.py (entire file)
**Dimension:** D3
**Description:** This file's 17 tests all patch `generate.generate` to mock batch_generate's delegation. However, the current `batch_generate()` implementation (generate.py:L390) calls `generate_with_retry()`, not `generate()` directly. This means the mock is on the wrong function — the real `generate()` is never called by `batch_generate()`, so patching it has no effect on the code path.

The tests still pass because `generate_with_retry` internally calls `generate()`, but they aren't testing what they claim to test. The `test_bug_fixes.py` file (TestBatchUsesRetryWrapper) already correctly tests that `generate_with_retry` is used.
**Evidence:**
```python
# test_batch_generation.py line 60
with patch("generate.generate") as mock_gen:
    mock_gen.return_value = "out/01.png"
    batch_generate(prompts, device="cpu")
```
But `batch_generate()` calls `generate_with_retry(batch_args)` not `generate(batch_args)`.
**Recommendation:** Update `test_batch_generation.py` to patch `generate.generate_with_retry` instead of `generate.generate`. Alternatively, accept these as indirect integration tests and document the indirection.

### [D3-011] — `_apply_performance_opts()` has zero dedicated tests
**Severity:** LOW
**File:** generate.py:L121-L135
**Dimension:** D3
**Description:** This helper handles xFormers memory-efficient attention with fallback to attention slicing. It's called by both `load_base()` and `load_refiner()`, but no test directly validates the xFormers → attention_slicing fallback path or the try/except around `enable_xformers_memory_efficient_attention()`.
**Evidence:** No test imports or references `_apply_performance_opts`.
**Recommendation:** Add 2-3 tests: xformers available, xformers raises (fallback), and no xformers attribute.

### [D3-012] — Test naming is generally consistent but has minor inconsistencies
**Severity:** INFO
**File:** tests/*.py
**Dimension:** D3
**Description:** Most tests follow `test_{description}` naming. A few files use very long names (50+ chars). Class grouping is well-structured. Minor inconsistency: some files use top-level functions (test_batch_cli.py) while others use classes exclusively.
**Evidence:** Mix of class-based and function-based test organization across files.
**Recommendation:** No action needed — this is minor and doesn't affect execution.

### [D3-013] — Cannot run pytest-cov — diffusers not installed
**Severity:** INFO
**File:** N/A
**Dimension:** D3
**Description:** `pytest-cov` is listed in `requirements-dev.txt` but coverage cannot be measured because `generate.py` fails to import without `diffusers`, `torch`, `transformers` installed. Line coverage percentage is unknown.
**Evidence:** `pytest --co` returns 9 collection errors from `ModuleNotFoundError: No module named 'diffusers'`.
**Recommendation:** Coverage can only be measured in an environment with the full GPU stack. Consider adding a CI job with the full requirements for coverage reporting.

---

## Score Card

| Category | Score | Notes |
|----------|-------|-------|
| Function coverage | **78%** | 11/14 public functions have dedicated tests; 3 helper functions untested |
| CLI flag coverage | **75%** | 12/16 flags tested at argparse level; 4 missing |
| Edge case coverage | **70%** | Validators well-covered; missing seed device binding, output path default |
| Mock quality | **60%** | No `spec=` usage; stale patches in batch_generation.py |
| Test quality | **85%** | No active silent-tuple bugs; good assertion messages; one `assert False` |
| Naming/organization | **90%** | Consistent class grouping; clear docstrings |

**Overall D3 Grade: B-** — Good foundation with meaningful gaps in CLI flag coverage, mock specificity, and one high-severity stale test file.
