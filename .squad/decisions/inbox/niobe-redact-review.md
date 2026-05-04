# Niobe Review: Text Redaction Tool (PR #103)

**Reviewer:** Niobe (Image Specialist)  
**Branch:** squad/text-redaction-tool  
**File:** image-generation/redact_text.py  
**Date:** 2025-01-27

## Verdict: REQUEST CHANGES

The tool is functionally sound for basic use cases, but has several image quality and format handling issues that could cause problems with the variety of generated images this repo produces.

---

## Critical Issues (Must Fix)

### 1. Color Space Handling Not Explicit
**Location:** `redact_regions()` line 271, `render_placeholder()` line 293

**Problem:** The code assumes all images are RGB. Generated images from SDXL are PNG (typically RGBA with alpha channel), but the tool doesn't explicitly handle transparency.

**Impact:**
- Hex color strings like `#FFFFFF` work for RGB, but PIL's behavior with RGBA images and hex colors is implicit
- If a generated image has transparency, the redaction fill might not behave as expected
- The fill color has no alpha component — can't do semi-transparent redactions

**Fix:**
```python
image = Image.open(image_path)
# Convert to RGB if needed, or explicitly handle RGBA
if image.mode not in ('RGB', 'RGBA'):
    image = image.convert('RGBA')
```

And update `_color_type()` to optionally support `#RRGGBBAA` format for alpha channel.

---

### 2. Image Quality Not Preserved on Save
**Location:** `main()` line 444

**Problem:** `image.save(output_path)` uses default quality settings. For JPEG, this can significantly degrade quality. For PNG, it's fine (lossless), but the code doesn't differentiate.

**Impact:**
- If someone uses this tool on JPEG blog thumbnails, quality will degrade
- No explicit format preservation — relies on file extension

**Fix:**
```python
# Preserve format and quality
original_format = Image.open(args.input).format
save_kwargs = {}
if original_format == 'JPEG':
    save_kwargs['quality'] = 95
    save_kwargs['optimize'] = True
image.save(output_path, format=original_format, **save_kwargs)
```

---

### 3. Image Opened Twice (Inefficiency)
**Location:** `find_text_regions()` line 210, `redact_regions()` line 271

**Problem:** The image is opened once for OCR, then opened again for redaction. For large images (1024×1024 SDXL outputs), this is wasteful.

**Impact:**
- Slower execution
- Higher memory footprint
- Unnecessary I/O

**Fix:** Refactor to open once, pass the Image object through the pipeline, or at minimum reuse the image from OCR in the redaction step.

---

## Moderate Issues (Should Fix)

### 4. Bitmap Font Fallback Silently Ignores font_size
**Location:** `_get_font()` line 356

**Problem:** `ImageFont.load_default()` returns a bitmap font that doesn't support sizing. If TrueType fonts aren't available, the `--font-size` argument is silently ignored.

**Impact:**
- User specifies `--font-size 24`, but gets fixed-size bitmap font with no warning (beyond the log line)
- Auto-fit logic also breaks — font stays at bitmap size regardless of region size

**Fix:** 
- Either log a more prominent warning that font sizing won't work
- Or raise an error if `--font-size` is specified but TrueType unavailable
- Or attempt to load system fonts from standard directories before falling back

---

### 5. Metadata Not Preserved
**Location:** `redact_regions()` line 271, save step

**Problem:** Image metadata (EXIF, creation date, software tags) is lost during the redaction process.

**Impact:**
- For generated images with embedded prompts or generation metadata, this is lost
- Not critical for blog post images, but nice to preserve for record-keeping

**Fix:**
```python
# Before saving
original = Image.open(args.input)
image.save(output_path, exif=original.info.get('exif'))
```

---

## Minor Issues (Nice to Have)

### 6. OCR Accuracy for Artistic Text
**OCR Approach:** pytesseract + Tesseract is reasonable, but has limitations:

- Tesseract is optimized for clean, horizontal text (documents, screenshots)
- Generated images with artistic/stylized text may have lower detection rates
- Text over complex backgrounds (tropical imagery) will struggle
- Confidence threshold of 60 is reasonable but may need tuning per image

**Not a blocker:** This is the right OCR approach for general use. For generated blog images, the text is usually overlays (clean), so this should work fine.

---

### 7. Auto-fit Algorithm Edge Cases
**Location:** `render_placeholder()` line 314-327

**Issues:**
- Very long placeholder text (e.g., `"[REDACTED-API-KEY-12345]"`) in small regions will shrink to minimum 8px, which may be unreadable
- Doesn't account for font ascenders/descenders — text might clip vertically
- Uses bbox for measurement, which is good, but doesn't validate minimum readability

**Not a blocker:** The algorithm is simple and sensible. For typical use (short placeholders like `"[REDACTED]"`), it's fine.

---

## Positive Notes

✅ **Padding logic is correct** — properly clamps to image bounds  
✅ **Confidence threshold is tunable** — good for handling OCR uncertainty  
✅ **Regex support** — flexible for pattern-based redaction  
✅ **Error handling** — graceful failures with clear messages  
✅ **CLI design** — well-structured arguments and help text  

---

## Recommendation

**Fix issues 1-3 (color space, quality, efficiency) before merging.** These affect image quality and correctness.

Issues 4-5 are "should fix" — they improve robustness but aren't blockers for blog image use cases.

Issue 6-7 are observations, not blockers.

---

**Niobe** — Image Specialist
