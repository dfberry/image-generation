---
name: "test-coverage-audit"
description: "Systematic test gap analysis and quality assessment methodology"
domain: "testing"
confidence: "high"
source: "earned — developed by Neo (Tester) during D3 coverage audit"
---

## Context

Use this skill when auditing test coverage for the image-generation project, reviewing test PRs, or assessing whether a new feature has adequate test coverage. The methodology produces a function-level coverage map, identifies gaps, and evaluates test quality beyond line coverage.

This skill applies whenever:
- A PR adds new functions without corresponding tests
- Someone asks "do we have enough tests?"
- CI test counts change unexpectedly
- A bug is found that should have been caught by tests

## Patterns

### Function-Level Coverage Mapping

For every public function in `generate.py`, verify test existence:

| Function | Expected Test Coverage |
|----------|----------------------|
| `parse_args()` | All 16 CLI flags, defaults, invalid inputs |
| `_positive_int()` | Valid int, zero, negative, float string, non-numeric |
| `_non_negative_float()` | Valid float, negative, non-numeric |
| `_dimension()` | Divisible by 8, not divisible, <64, boundary values |
| `validate_dimensions()` | Valid pair, invalid width, invalid height, both invalid |
| `get_device()` | CUDA available, MPS available, CPU fallback, --cpu forced |
| `get_dtype()` | CUDA→float16, MPS→float16, CPU→float32, unknown device |
| `load_base()` | Each device path, model ID, variant, offload, compile |
| `load_refiner()` | Shared components, each device, model ID |
| `apply_scheduler()` | Valid scheduler, invalid, Karras config, config preservation |
| `apply_lora()` | None (skip), valid ID, weight setting, error handling |
| `_apply_performance_opts()` | xFormers available, fallback to attention slicing |
| `generate()` | Base-only, base+refiner, seed handling, output path, cleanup |
| `generate_with_retry()` | 0 retries, 1 retry, exhausted retries, non-OOM error |
| `batch_generate()` | Empty list, single item, multi-item, error isolation, arg forwarding |
| `main()` | Prompt mode, batch mode, file-not-found, invalid JSON |

### Test Quality Checks

Beyond coverage, verify these quality signals:

1. **Assertion correctness:** Grep for `mock.assert_called(), "msg"` — this is a silent tuple bug (always truthy). Correct: `assert mock.called, "msg"`
2. **No unconditional asserts:** Search for `assert True` or `assert False` without conditions
3. **Mock spec accuracy:** All `MagicMock(spec=...)` should match actual function signatures
4. **Behavioral verification:** Tests should verify *behavior* (return values, side effects), not just confirm mocks were called
5. **Edge case coverage:** seed=0, width=64 (minimum), empty prompt, batch with 1 item

### Collection Barrier Detection

Check if tests can be collected without the full dependency stack:

```bash
# This should work even without diffusers installed
pytest --co -q tests/
```

If modules fail to collect due to `import diffusers` at module level, this is a HIGH severity barrier. The fix is lazy imports inside functions or conditional imports with try/except.

### Coverage Measurement

```bash
# Run with coverage reporting
pytest tests/ --cov=generate --cov-report=term-missing -v

# Target: 90%+ line coverage
# Critical: No public function at 0% coverage
```

### Test Naming Convention

Tests should follow: `test_{function}_{scenario}_{expected_result}`

```python
# Good
def test_get_device_cuda_available_returns_cuda():
def test_batch_generate_empty_list_returns_empty():
def test_generate_with_retry_exhausted_raises_oom():

# Bad
def test_1():
def test_device():
def test_it_works():
```

## Examples

### Coverage gap report format

```markdown
### ❌ Gaps Identified

| Function / Area | Missing Coverage |
|----------------|-----------------|
| `_positive_int()` | No direct unit tests for edge cases (string "abc", float "1.5") |
| `parse_args()` — --seed flag | No test verifies `--seed 42` parsing or default (None) |
| `generate()` — output path | No test for auto-generated `outputs/image_{timestamp}.png` |
```

### Stale patch detection

```python
# STALE: patches wrong function name
@patch("generate.generate")  # Should be generate.generate_with_retry
def test_batch_calls_generate(mock_gen):
    ...

# Check by comparing patch target to actual call chain in source
```

## Anti-Patterns

- **Testing mocks, not behavior:** `mock.assert_called_once()` alone doesn't verify the function did the right thing. Assert return values or output state too.
- **Ignoring collection errors:** If `pytest --co` shows collection failures, those tests don't exist from CI's perspective. Fix the barrier first.
- **Coverage theater:** 100% line coverage with weak assertions is worse than 80% with strong assertions. Prioritize quality over percentage.
- **Hardcoded paths in tests:** Tests should use `tmp_path` fixture or `os.path.join()`, never `/Users/someone/...`
- **Silent tuple assertion:** `mock.assert_called_with(x), "message"` — the comma makes this a tuple expression that's always truthy. Use `assert mock.called, "message"` instead.
