# Text Redaction Tool

OCR-based tool that finds and redacts text in images with optional placeholder replacement.

## What It Does

Uses Tesseract OCR to detect text in images, then replaces matched text with solid color fill and optional placeholder text.

## Prerequisites

### Tesseract OCR Installation

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download and install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).

After installation, add Tesseract to your system PATH if not automatically added.

### Verify Installation

```bash
tesseract --version
```

## Installation

1. Clone the repository and navigate to `image-generation/`:
   ```bash
   cd image-generation/
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Syntax

```bash
python redact_text.py --input <image> --find <text> [options]
```

### CLI Reference

| Flag | Type | Description |
|------|------|-------------|
| `--input` | `Path` | **Required.** Input image path (PNG/JPG) |
| `--find` | `str` | **Required.** Text to find (exact match or regex pattern) |
| `--regex` | flag | Treat `--find` as a regex pattern |
| `--replace` | `str` | Placeholder text to render over redacted region (optional) |
| `--output` | `Path` | Output path (default: overwrites input) |
| `--fill-color` | `str` | Hex color to paint over text (default: `#FFFFFF`) |
| `--font-size` | `int` | Font size for placeholder text (default: auto-fit) |
| `--font-color` | `str` | Hex color for placeholder text (default: `#000000`) |
| `--padding` | `int` | Extra pixels around detected text (default: `2`) |
| `--all` | flag | Redact all occurrences (default: first match only) |
| `--confidence` | `int` | Minimum OCR confidence threshold 0-100 (default: `60`) |
| `-v`, `--verbose` | flag | Enable verbose logging |

## Examples

### 1. Redact API Key with Placeholder

Redact an exact text match and replace with `[REDACTED]`:

```bash
python redact_text.py \
  --input test-images/api-keys.png \
  --find "sk-abc123def456" \
  --replace "[REDACTED]"
```

### 2. Redact Using Regex Pattern

Use a regex pattern to match multiple formats (e.g., all tokens starting with `ghp_`):

```bash
python redact_text.py \
  --input test-images/mixed-content.png \
  --find "ghp_\w+" \
  --regex \
  --replace "[TOKEN]" \
  --output redacted-output.png
```

### 3. Black Out Passwords (No Placeholder)

Just fill the matched text with black, no placeholder:

```bash
python redact_text.py \
  --input screenshot.png \
  --find "password123" \
  --fill-color "#000000"
```

### 4. Redact All Email Addresses

Redact all occurrences of email addresses in an image:

```bash
python redact_text.py \
  --input test-images/personal-info.png \
  --find "\S+@\S+\.\S+" \
  --regex \
  --all \
  --replace "[EMAIL]"
```

### 5. Batch Redaction with Shell Loop

Redact the same text pattern across multiple images:

```bash
# Bash/macOS/Linux
for img in screenshots/*.png; do
  python redact_text.py \
    --input "$img" \
    --find "SECRET_TOKEN_\w+" \
    --regex \
    --replace "[REDACTED]" \
    --output "redacted/$(basename "$img")"
done
```

```powershell
# PowerShell/Windows
Get-ChildItem screenshots\*.png | ForEach-Object {
  python redact_text.py `
    --input $_.FullName `
    --find "SECRET_TOKEN_\w+" `
    --regex `
    --replace "[REDACTED]" `
    --output "redacted\$($_.Name)"
}
```

### 6. Custom Colors and Padding

Use custom fill color and extra padding:

```bash
python redact_text.py \
  --input image.png \
  --find "confidential" \
  --fill-color "#FF0000" \
  --font-color "#FFFFFF" \
  --replace "HIDDEN" \
  --padding 5
```

## How It Works

1. **OCR Detection**: Uses Tesseract to extract text and bounding boxes from the image
2. **Pattern Matching**: Matches detected text against search string (exact or regex)
3. **Fill Region**: Paints over matched text regions with solid color
4. **Optional Placeholder**: Renders replacement text centered in the redacted region (auto-sized or custom font size)

## Limitations

### OCR Accuracy

- OCR quality depends on image clarity, font type, contrast, and text size
- Low-resolution or stylized fonts may have lower detection rates
- For best results, use high-contrast, clear images with standard fonts

### Text Matching

- OCR detects text word-by-word; multi-word phrases are matched within individual words
- Example: `--find "secret key"` matches words containing "secret" OR "key", not the phrase "secret key"
- Use regex patterns for flexible matching across word boundaries

### Font Availability

- Placeholder rendering requires system fonts (DejaVuSans or Arial)
- If TrueType fonts are unavailable, falls back to default bitmap font (limited sizing)
- On Windows, Arial is usually available; on Linux, install `fonts-dejavu` if needed

### Confidence Threshold

- Default threshold is `60` (0-100 scale)
- Lower thresholds detect more text but may include false positives
- Higher thresholds miss low-quality text but reduce false matches
- Tune with `--confidence` if results are too aggressive or too conservative

## Test Images

The `test-images/` directory contains sample images for trying the tool:

- **`api-keys.png`** — API keys and credentials
- **`personal-info.png`** — Names, email, SSN
- **`mixed-content.png`** — Mixed safe and sensitive content
- **`watermark.png`** — Large watermark text

Generate test images with:
```bash
python create_test_images.py
```

## Troubleshooting

### `TesseractNotFoundError`

**Problem:** Tesseract is not installed or not in PATH.

**Solution:**
- Install Tesseract (see Prerequisites above)
- On Windows, add Tesseract installation directory to system PATH (e.g., `C:\Program Files\Tesseract-OCR`)

### No Text Detected

**Problem:** `No matching text found in image`

**Solution:**
- Check image quality and contrast
- Try lowering `--confidence` threshold (e.g., `--confidence 50`)
- Use `--verbose` flag to see OCR debugging output

### Font Warning: `TrueType fonts not available`

**Problem:** Placeholder text uses low-quality bitmap font.

**Solution:**
- **Linux:** `sudo apt install fonts-dejavu`
- **macOS:** DejaVu fonts should be included; otherwise install via Homebrew
- **Windows:** Arial is standard; no action needed

## License

See repository root for license information.
