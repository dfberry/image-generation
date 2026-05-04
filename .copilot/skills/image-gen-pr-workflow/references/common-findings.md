# Common Findings by Reviewer

Code examples showing typical issues found by each reviewer.

## Morpheus (Lead) — Security & Architecture

### ReDoS Risk

```python
# ❌ Bad: No validation on user regex input (ReDoS risk)
pattern = re.compile(args.redact_text)

# ✅ Good: Validate regex complexity
if len(args.redact_text) > 100:
    raise ValueError("Pattern too long (max 100 characters)")
try:
    pattern = re.compile(args.redact_text, re.TIMEOUT(1.0))
except re.error as e:
    raise ValueError(f"Invalid regex: {e}")
```

### Input Validation

```python
# ❌ Bad: No path validation
output_path = args.output

# ✅ Good: Validate output path
if not output_path.endswith(('.png', '.jpg', '.jpeg')):
    raise ValueError("Output must be PNG or JPEG")
```

### Error Handling

```python
# ❌ Bad: Generic exception
try:
    process_image(path)
except Exception:
    print("Error")

# ✅ Good: Specific exceptions with context
try:
    process_image(path)
except FileNotFoundError:
    logger.error(f"Image not found: {path}")
    raise
except PIL.UnidentifiedImageError:
    logger.error(f"Invalid image format: {path}")
    raise
```

---

## Niobe (Image Specialist) — Image Quality

### JPEG Quality

```python
# ❌ Bad: JPEG save without quality param (degrades image)
image.save(output_path, format="JPEG")

# ✅ Good: Preserve quality
image.save(output_path, format="JPEG", quality=95)
```

### Double Image Load

```python
# ❌ Bad: Double image load (inefficient)
def process_image(path):
    img1 = Image.open(path)
    width, height = img1.size
    img2 = Image.open(path)
    return img2.resize((width, height))

# ✅ Good: Single load
def process_image(path):
    img = Image.open(path)
    width, height = img.size
    return img.resize((width, height))
```

### RGBA→RGB Conversion

```python
# ❌ Bad: JPEG doesn't support RGBA, causes errors
if output_path.endswith('.jpg'):
    image.save(output_path)

# ✅ Good: Convert RGBA to RGB for JPEG
if output_path.endswith('.jpg'):
    if image.mode == 'RGBA':
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[3])
        image = rgb_image
    image.save(output_path, format="JPEG", quality=95)
```

### Font Fallback

```python
# ❌ Bad: Missing font fallback (renders as boxes)
font = ImageFont.truetype("Arial.ttf", 40)

# ✅ Good: Font fallback mechanism
try:
    font = ImageFont.truetype("Arial.ttf", 40)
except IOError:
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
    except IOError:
        font = ImageFont.load_default()
```

---

## Switch (UX/Prompt Engineer) — CLI UX

### Help Text

```python
# ❌ Bad: Help text doesn't mention related flags
parser.add_argument("--redact-text", help="Text to redact")

# ✅ Good: Cross-reference related flags
parser.add_argument("--redact-text", 
    help="Text to redact (regex pattern). Use with --replacement-text to customize replacement.")
```

### Error Messages

```python
# ❌ Bad: Generic error message (not actionable)
raise ValueError("Error processing image")

# ✅ Good: Specific, actionable error message
raise ValueError(
    f"Cannot save RGBA image as JPEG. "
    f"Use PNG format or convert to RGB first."
)
```

### Logging Levels

```python
# ❌ Bad: Wrong logging levels
logger.warning(f"Processing image: {path}")  # Should be info
logger.info(f"Failed to load font")  # Should be warning

# ✅ Good: Appropriate logging levels
logger.info(f"Processing image: {path}")
logger.warning(f"Failed to load Arial font, using fallback")
logger.debug(f"Image size: {width}x{height}")
```

### Epilog Examples

```python
# ❌ Bad: Missing examples in epilog
parser = argparse.ArgumentParser(
    description="Generate images with text"
)

# ✅ Good: Clear examples showing flag combinations
parser = argparse.ArgumentParser(
    description="Generate images with text",
    epilog="""
Examples:
  # Generate with text redaction
  python generate.py --prompt "sunset" --redact-text "watermark" --output out.png
  
  # Custom replacement text
  python generate.py --prompt "beach" --redact-text "logo" --replacement-text "[REMOVED]"
  
  # Unicode redaction
  python generate.py --prompt "city" --redact-text "秘密" --replacement-text "***"
""",
    formatter_class=argparse.RawDescriptionHelpFormatter
)
```

---

## Neo (Tester) — Test Quality

### Weak Assertions

```python
# ❌ Bad: Weak assertion
def test_redact_text():
    result = redact_text_from_image("input.png", "secret", "***", "output.png")
    assert result is not None

# ✅ Good: Specific assertion
def test_redact_text():
    result = redact_text_from_image("input.png", "secret", "***", "output.png")
    output_img = Image.open("output.png")
    assert output_img.size == (1024, 1024)
    # Verify text was actually redacted (image is blank or has replacement)
    assert output_img != Image.open("input.png")
```

### Missing Edge Cases

```python
# ❌ Bad: Missing edge cases
def test_redact_text():
    redact_text_from_image("input.png", "secret", "***", "output.png")

# ✅ Good: Edge cases covered
def test_redact_unicode():
    """Test redaction with Unicode characters"""
    redact_text_from_image("input.png", "秘密", "***", "output.png")

def test_redact_case_insensitive():
    """Test case-insensitive redaction"""
    redact_text_from_image("input.png", "(?i)secret", "***", "output.png")

def test_redact_empty_replacement():
    """Test redaction with empty replacement"""
    redact_text_from_image("input.png", "secret", "", "output.png")

def test_redact_multiline():
    """Test redaction across multiple lines"""
    redact_text_from_image("input.png", "secret.*text", "***", "output.png")

def test_redact_no_match():
    """Test when pattern doesn't match anything"""
    redact_text_from_image("input.png", "nomatch", "***", "output.png")
```

### Unrealistic Mocks

```python
# ❌ Bad: Unrealistic mock that doesn't match production
@patch('PIL.Image.open')
def test_process_image(mock_open):
    mock_img = MagicMock()
    mock_img.size = (100, 100)
    mock_open.return_value = mock_img
    # This doesn't test actual image processing

# ✅ Good: Use real images or realistic fixtures
def test_process_image():
    # Use a small test fixture image
    test_img = Image.new('RGB', (100, 100), color='red')
    test_path = "test-outputs/unit-tests/fixture.png"
    test_img.save(test_path)
    
    result = process_image(test_path)
    assert result.size == (100, 100)
    # Clean up
    os.remove(test_path)
```

### Test Independence

```python
# ❌ Bad: Tests depend on execution order
test_image = None

def test_create_image():
    global test_image
    test_image = Image.new('RGB', (100, 100))

def test_process_image():
    # Depends on test_create_image running first
    result = process_image(test_image)

# ✅ Good: Each test is independent
def test_create_image():
    test_image = Image.new('RGB', (100, 100))
    assert test_image.size == (100, 100)

def test_process_image():
    # Create its own fixture
    test_image = Image.new('RGB', (100, 100))
    result = process_image(test_image)
```

---

## Anti-Patterns Summary

### Branch & Commit
- ❌ Branch from local main (may include unpushed commits)
- ❌ Branch naming without `squad/` prefix
- ❌ Forget Co-authored-by trailer

### Review Process
- ❌ Sequential reviews (bottleneck, wastes time)
- ❌ Vague verdicts without APPROVE/REQUEST CHANGES
- ❌ Asking reviewers to fix their own findings
- ❌ Skip re-review after fixes
- ❌ Merge without all approvals (unless user override)

### Testing
- ❌ Skip tests before push
- ❌ Weak assertions (`is not None`, `in [0, 1]`)
- ❌ Missing edge cases (Unicode, empty input, invalid input)
- ❌ Unrealistic mocks
- ❌ Tests that depend on execution order

### Image Quality
- ❌ JPEG save without quality parameter
- ❌ Double image loads
- ❌ Missing RGBA→RGB conversion for JPEG
- ❌ Missing font fallback

### Security
- ❌ No regex validation (ReDoS vulnerability)
- ❌ No input length limits
- ❌ Generic exception handling

### UX/CLI
- ❌ Help text without related flag mentions
- ❌ Missing epilog examples
- ❌ Generic error messages
- ❌ Wrong logging levels
