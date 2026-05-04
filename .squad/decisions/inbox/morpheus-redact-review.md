# PR #103 Review: OCR Text Redaction Tool

**Reviewer:** Morpheus (Lead)  
**Date:** 2026-04-23  
**PR:** #103 (branch: squad/text-redaction-tool)  
**Verdict:** REQUEST CHANGES

---

## Executive Summary

The text redaction tool is well-architected and follows project conventions. Code quality is strong with comprehensive test coverage. However, there are **three blocking security/safety concerns** that must be addressed before merge:

1. **ReDoS vulnerability** from unvalidated regex input
2. **Missing timeout protection** for OCR operations
3. **Incomplete input sanitization** in regex mode

---

## Detailed Findings

### 1. Architecture ✅ APPROVED

**Strengths:**
- Clean separation: `find_text_regions()`, `redact_regions()`, `render_placeholder()` are well-scoped single-purpose functions
- Follows same CLI pattern as `generate.py` (argparse, custom validators, `main()` entry point)
- Standalone tool — doesn't couple to or break existing generate.py functionality
- Module structure fits the flat `image-generation/*.py` layout

**Alignment with project:**
- Matches `generate.py` conventions: argparse types (`_positive_int`, `_color_type`), lazy import pattern not needed here (PIL/pytesseract are lightweight), logging setup
- Test structure mirrors `tests/test_generate.py` (mocked heavy dependencies, parametric tests, integration coverage)

**No concerns.**

---

### 2. Code Quality ✅ STRONG (with caveats below)

**Strengths:**
- Type hints on all functions (`list[dict[str, Any]]`, `Path`, `int | None`)
- Edge case handling: confidence filtering (line 225), empty text skipped (line 225), padding clamped to image bounds (lines 275-278)
- Error handling: custom `TesseractNotInstalledError`, clear error messages with install instructions
- CLI design: good help text, examples in epilog, sensible defaults
- Test coverage: 43 tests covering CLI parsing, OCR matching, redaction, placeholder rendering, integration, error paths

**Minor observations:**
- `_get_font()` fallback (lines 345-356) is robust — tries DejaVuSans → Arial → bitmap default
- `render_placeholder()` auto-fit logic (lines 315-327) is clever but could use a docstring comment explaining the 0.6 and 0.9 magic numbers
- No docstring on `_get_font()` helper (line 345)

**No blocking issues here, but see Security section.**

---

### 3. Dependency Choice ⚠️ ACCEPTABLE (with deployment note)

**Decision: pytesseract + Tesseract OCR**

**Pros:**
- `pytesseract` is the de facto standard Python wrapper for Tesseract
- Tesseract is mature, actively maintained (Google/community)
- Good OCR quality for printed text
- No API costs or rate limits (local processing)

**Cons:**
- **System dependency:** Requires Tesseract binary installation (apt/brew/manual on Windows)
- Deployment complexity: CI/CD must install `tesseract-ocr` before running tool (not just `pip install`)
- Not pure Python — cross-platform testing burden

**Mitigation in PR:**
- ✅ `check_tesseract()` validates availability and provides install instructions
- ✅ Tests mock pytesseract so CI doesn't need Tesseract to run tests
- ✅ Docstring at top of file documents system requirements

**Recommendation:** Accept this dependency. Alternative (cloud OCR APIs like Azure Computer Vision) would add network latency, costs, and API key management. For a CLI tool, local OCR is appropriate.

**Action item for future:** Document Tesseract install in main README.md and CONTRIBUTING.md (not blocking for this PR).

---

### 4. Naming & Conventions ✅ APPROVED

**Consistency check:**
- ✅ Snake case: `redact_text.py`, `find_text_regions()`, `_color_type()`
- ✅ Private helpers prefixed with `_`: `_color_type`, `_positive_int`, `_confidence_range`, `_get_font`
- ✅ Argparse pattern matches generate.py: custom type validators, `parse_args()`, `main()`
- ✅ Logging: uses `logger = logging.getLogger(__name__)` like generate.py
- ✅ Test file: `test_redact_text.py` matches `test_*.py` pattern

**No concerns.**

---

### 5. Security 🚨 REQUEST CHANGES

#### **Issue 1: ReDoS (Regular Expression Denial of Service) — BLOCKING**

**Location:** Line 216  
**Severity:** HIGH

```python
pattern = re.compile(search_text) if is_regex else None
```

**Problem:**
User-provided regex (via `--find "..." --regex`) is compiled with no validation. Malicious regex patterns can cause catastrophic backtracking, hanging the process indefinitely.

**Example attack:**
```bash
python redact_text.py --input img.png --find "(a+)+b" --regex
# If OCR text contains "aaaaaaaaaaaaaaaaaaa" (no 'b'), regex engine hangs
```

**Fix:** Add timeout protection with `re.compile()` and wrap `pattern.search()` in a timeout guard:

```python
import re
import signal  # or use threading.Timer on Windows

def _compile_regex_safe(pattern_str: str, timeout_seconds: int = 2) -> re.Pattern:
    """Compile regex with timeout protection against ReDoS."""
    try:
        return re.compile(pattern_str)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")

def _search_with_timeout(pattern: re.Pattern, text: str, timeout_seconds: int = 2) -> bool:
    """Search with timeout to prevent ReDoS."""
    # Use threading.Timer or signal.alarm depending on OS
    # For MVP: accept risk and document, or use regex library with timeout
    return pattern.search(text) is not None
```

**Alternative (simpler):** Use the `regex` library (pip install regex) which has built-in timeout:
```python
import regex  # instead of re
pattern = regex.compile(search_text, timeout=2)  # 2-second timeout
```

**Recommendation:** Either:
1. Add `regex` library dependency and use timeout parameter, OR
2. Document in CLI help that `--regex` is for trusted input only, add try/except around `re.compile()` to catch malformed patterns, and accept ReDoS risk for MVP (with TODO comment)

**Required action:** At minimum, wrap `re.compile()` in try/except and raise user-friendly error for invalid regex.

---

#### **Issue 2: OCR Timeout Protection — BLOCKING**

**Location:** Line 213 (`pytesseract.image_to_data()`)  
**Severity:** MEDIUM

**Problem:**
OCR on large/complex images can take minutes. No timeout protection. User has no way to cancel a hung OCR operation except Ctrl+C.

**Fix:** Add timeout to pytesseract call:

```python
try:
    ocr_data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT,
        timeout=30  # 30-second timeout
    )
except RuntimeError as e:
    if "timeout" in str(e).lower():
        raise TimeoutError(f"OCR timed out after 30 seconds on {image_path}")
    raise
```

**Recommendation:** Add timeout parameter (default 30s, configurable via CLI flag `--ocr-timeout`).

---

#### **Issue 3: Path Traversal (Low Risk) — ADVISORY**

**Location:** Lines 378-383 (input file validation), line 386 (output path)  
**Severity:** LOW

**Current validation:**
```python
if not args.input.exists():
    logger.error(f"Input file not found: {args.input}")
    return 1
```

**Observation:**
- Input: Validated for existence and is_file() ✅
- Output: No validation — user can specify any writable path (could overwrite system files if run with elevated privileges)

**Risk:** Low for CLI tool (user controls both input and output). Not exploitable unless tool is wrapped in a service that passes unsanitized user input.

**Recommendation (non-blocking):** Add sanity check to warn if output path is outside current directory or input directory:

```python
if args.output:
    try:
        args.output.resolve().relative_to(Path.cwd())
    except ValueError:
        logger.warning(f"Output path is outside current directory: {args.output}")
        # Continue anyway — user may have legitimate reason
```

Not blocking for merge, but worth considering for Phase 1.

---

## Summary of Required Changes

### Blocking (P0):
1. **Wrap `re.compile()` in try/except** — raise user-friendly error for invalid regex (line 216)
2. **Add timeout to OCR call** — prevent hung processes on large images (line 213)

### Recommended (P1):
3. Document ReDoS risk in `--regex` help text: "Use trusted patterns only; complex regex may cause performance issues."
4. Add `--ocr-timeout` CLI flag (default: 30s)

### Advisory (P2):
5. Add docstring to `_get_font()` and magic number comments in `render_placeholder()`
6. Consider path traversal warning for output (non-blocking)

---

## Verdict

**REQUEST CHANGES** — address P0 security issues (regex validation, OCR timeout) before merge.

Once fixed, this is a strong addition to the toolkit. Code quality and test coverage are excellent. Architecture fits well with the existing project.

---

**Next Steps:**
1. Trinity or Neo: Implement P0 fixes
2. Morpheus: Re-review after fixes
3. Merge when security concerns resolved
