# Test Review: text-redaction-tool (PR #103)

**Reviewer:** Neo  
**Date:** 2025-01-29  
**Branch:** squad/text-redaction-tool  
**Files Reviewed:**
- `image-generation/tests/test_redact_text.py`
- `image-generation/redact_text.py`

## Verdict: REQUEST CHANGES

The test suite has good coverage of the happy path and basic argument parsing, but has **significant gaps in error paths, edge cases, and some weak assertions** that would allow bugs to slip through.

---

## 1. Coverage Gaps

### Untested Functions
- **`_positive_int()`** (lines 52-57) — Used for `--font-size` validation, but has zero tests. Could accept 0 or negative values and we wouldn't know until runtime.
- **`_get_font()`** (lines 345-357) — Font loading with multiple fallbacks (DejaVuSans → Arial → default bitmap) never directly tested. What if all fallbacks fail?

### Untested Error Paths in `main()`
The following error returns are **not covered**:

1. **Line 381-383:** Input path is directory, not file → return 1  
   - Test `test_missing_input_returns_one` only covers missing file, not wrong type
   
2. **Line 424-425:** Exception during `redact_regions()` → return 1  
   - No test forces redaction to fail
   
3. **Line 439-440:** Exception during `render_placeholder()` → return 1  
   - No test forces placeholder rendering to fail
   
4. **Line 447-448:** Exception during `image.save()` → return 1  
   - No test forces save operation to fail (e.g., permission denied, disk full)

**Impact:** These error paths could be broken (wrong return code, wrong error message, exception leaks) and we wouldn't catch it.

---

## 2. Mock Quality Issues

### Oversimplified OCR Mocks
The `_mock_ocr_data()` helper is clean but doesn't test **defensive coding**:
- What if Tesseract returns `None` for a field?
- What if coordinates are negative?
- What if coordinates exceed image bounds?
- What if `conf` is non-numeric?

**Real-world Tesseract data is messy.** We should have at least one test with captured real OCR output to validate our assumptions.

### Missing Properties on Image Mock
Tests mock `Image.open()` but don't set `width`/`height` properties. The code reads `image.width` and `image.height` (lines 277-278), but tests never verify bounds-checking logic works correctly.

---

## 3. Edge Cases Missing

### High Priority
1. **Unicode text** — What if OCR detects "秘密", "🔑", or Arabic text? What if `--find` is Unicode?
   
2. **Case sensitivity** — Exact mode uses `search_text in text` (line 233), which is case-sensitive. Should "Secret" match "secret"? No test documents this behavior.

3. **Multi-word phrases** — Tesseract returns **word-level bounding boxes**. If searching for "api key" (two words), current logic will never match because each OCR box contains one word. This is a **potential bug** that no test catches.

4. **Invalid regex patterns** — What if `--find "(?:unclosed"` with `--regex`? Code compiles regex at line 216 with no try/except. This would crash.

5. **Negative padding** — `--padding` accepts any `int` (line 146), not constrained to positive. What happens if `--padding -10`? Lines 275-278 use `max(0, ...)` to clamp, which is correct, but **no test verifies this**.

### Medium Priority
6. **Zero-width/height regions** — What if OCR returns `width: 0` or `height: 0`?

7. **Very large images** — Performance/memory implications not tested (e.g., 8000×8000 image).

8. **Very long replacement text** — What if `--replace` is 1000+ characters?

9. **Image format compatibility** — Tests only create PNG. Code should work with JPEG, GIF, WEBP per Pillow support, but untested.

10. **Empty or tiny images** — What if image is 1×1 pixel?

---

## 4. Test Isolation

✅ **Good:** Tests use `tmp_path` fixtures correctly  
✅ **Good:** No shared state leakage detected  
⚠️ **Acceptable:** `test_pytesseract_not_installed` modifies module-level `pytesseract` but uses try/finally cleanup

---

## 5. Assertion Quality Issues

### Weak Assertions That Would Pass on Broken Code

1. **`test_first_match_only_by_default`** (lines 389-403):
   ```python
   # Comment admits: "hard to verify pixel-level without more infrastructure"
   ```
   Test doesn't actually verify only the **first** match was redacted. Would pass even if all matches were processed. This is a **critical assertion gap** for a key feature.

2. **`test_renders_text`** (lines 308-323):
   ```python
   if result.getpixel((x, y)) != (255, 255, 255):
       changed = True
   ```
   Only checks that *some* pixel changed. Doesn't verify correct text was rendered, positioned correctly, or used the right color. Could pass if garbage was drawn.

3. **`test_auto_font_size`** (lines 333-341):
   ```python
   assert result is not None
   ```
   Extremely weak. Doesn't verify font was sized, text was rendered, or anything about correctness.

**Recommendation:** These three tests need stronger assertions or should be marked as smoke tests, not behavior verification.

---

## 6. Missing Test Cases

### Required Before Approval

```python
# Error paths
def test_input_is_directory_returns_one()
def test_redaction_exception_returns_one()
def test_placeholder_rendering_exception_returns_one()
def test_image_save_exception_returns_one()

# Validators
def test_positive_int_rejects_zero()
def test_positive_int_rejects_negative()

# Edge cases
def test_invalid_regex_pattern()
def test_case_sensitive_matching()
def test_unicode_search_text()
def test_negative_padding_clamped()

# Font loading
def test_get_font_fallback_to_default()
```

### Recommended for Robustness

```python
def test_multi_word_phrase_not_matched()  # Documents current limitation
def test_zero_width_region_handled()
def test_zero_height_region_handled()
def test_ocr_data_with_negative_coords()
def test_jpeg_image_format()
```

---

## Summary

**Strengths:**
- ✅ Excellent argument parsing coverage
- ✅ Good use of fixtures and mocking
- ✅ Test organization is clean

**Blockers:**
- ❌ 4 error paths in `main()` untested (lines 381, 424, 439, 447)
- ❌ `_positive_int()` validator has zero tests
- ❌ Invalid regex would crash (no exception handling)
- ❌ Case sensitivity behavior undocumented
- ❌ Multi-word phrase matching may be broken
- ❌ Three tests have assertions too weak to catch real bugs

**Recommendation:** Add the 8 required test cases listed above before merging. The error path gaps are the highest priority—these are real code paths that will execute in production but have zero test coverage.

---

**Next Steps:**
Trinity should implement the missing tests. I'm marking this as **REQUEST CHANGES** until error path coverage is complete and assertions are strengthened.
