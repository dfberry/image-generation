#!/usr/bin/env python3
"""
Text redaction tool using OCR.
Finds text in images and replaces it with solid color fill and optional placeholder text.

Requirements:
- Tesseract OCR must be installed on the system:
  - Ubuntu/Debian: apt install tesseract-ocr
  - macOS: brew install tesseract
  - Windows: https://github.com/UB-Mannheim/tesseract/wiki
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

logger = logging.getLogger(__name__)


class TesseractNotInstalledError(RuntimeError):
    """Raised when Tesseract OCR is not installed on the system."""
    pass


def _color_type(value: str) -> str:
    """Argparse type: hex color format (#RRGGBB or #RGB)."""
    if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', value):
        raise argparse.ArgumentTypeError(
            f"must be hex color format (#RRGGBB or #RGB), got {value}"
        )
    # Expand short form #RGB to #RRGGBB
    if len(value) == 4:
        return f"#{value[1]*2}{value[2]*2}{value[3]*2}"
    return value.upper()


def _positive_int(value: str) -> int:
    """Argparse type: positive integer (> 0)."""
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"must be > 0, got {value}")
    return ivalue


def _confidence_range(value: str) -> int:
    """Argparse type: confidence threshold 0-100."""
    ivalue = int(value)
    if not 0 <= ivalue <= 100:
        raise argparse.ArgumentTypeError(f"must be 0-100, got {value}")
    return ivalue


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Redact text in images using OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Redact exact match and replace with placeholder
  python redact_text.py --input image.png --find "secret_key_123" --replace "[REDACTED]"
  
  # Redact using regex pattern
  python redact_text.py --input image.png --find "api_key_\\w+" --regex --replace "[API_KEY]"
  
  # Just black out text, no replacement
  python redact_text.py --input image.png --find "password123" --fill-color "#000000"
  
  # Redact all occurrences
  python redact_text.py --input image.png --find "secret" --all --output redacted.png
  
  # Use custom confidence threshold
  python redact_text.py --input image.png --find "text" --confidence 80
        """
    )
    
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to input image (PNG/JPG)"
    )
    
    parser.add_argument(
        "--find",
        type=str,
        required=True,
        help="Text to find (exact match by default; use --regex for pattern matching)"
    )
    
    parser.add_argument(
        "--regex",
        action="store_true",
        help="Treat --find as a regex pattern"
    )
    
    parser.add_argument(
        "--replace",
        type=str,
        default=None,
        help="Placeholder text to render over redacted region (optional)"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrites input)"
    )
    
    parser.add_argument(
        "--fill-color",
        type=_color_type,
        default="#FFFFFF",
        help="Color to paint over found text (default: #FFFFFF)"
    )
    
    parser.add_argument(
        "--font-size",
        type=_positive_int,
        default=None,
        help="Font size for placeholder text (default: auto-fit)"
    )
    
    parser.add_argument(
        "--font-color",
        type=_color_type,
        default="#000000",
        help="Color for placeholder text (default: #000000)"
    )
    
    parser.add_argument(
        "--padding",
        type=int,
        default=2,
        help="Extra pixels around detected text (default: 2)"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Replace all occurrences (default: first match only)"
    )
    
    parser.add_argument(
        "--confidence",
        type=_confidence_range,
        default=60,
        help="Minimum OCR confidence threshold 0-100 (default: 60)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args(args)


def check_tesseract() -> None:
    """Verify Tesseract is installed and accessible."""
    if pytesseract is None:
        raise ImportError(
            "pytesseract is not installed. Install with: pip install pytesseract"
        )
    
    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        raise TesseractNotInstalledError(
            "Tesseract OCR is not installed on this system.\n"
            "Install instructions:\n"
            "  Ubuntu/Debian: sudo apt install tesseract-ocr\n"
            "  macOS: brew install tesseract\n"
            "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
        )


def find_text_regions(
    image: Image.Image,
    search_text: str,
    is_regex: bool,
    confidence: int
) -> list[dict[str, Any]]:
    """
    Find text regions in image using OCR.
    
    Args:
        image: PIL Image object
        search_text: Text to search for (exact or regex)
        is_regex: Whether search_text is a regex pattern
        confidence: Minimum OCR confidence threshold (0-100)
    
    Returns:
        List of bounding box dicts with keys: text, left, top, width, height, conf
    """
    # Get OCR data with bounding boxes
    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    
    regions = []
    
    # Compile regex pattern with validation
    if is_regex:
        try:
            pattern = re.compile(search_text)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{search_text}': {e}")
    else:
        pattern = None
    
    # Iterate through detected text
    n_boxes = len(ocr_data['text'])
    for i in range(n_boxes):
        text = ocr_data['text'][i].strip()
        conf = float(ocr_data['conf'][i])
        
        # Skip empty text or low confidence
        if not text or conf < confidence:
            continue
        
        # Check if text matches search criteria
        matches = False
        if is_regex:
            matches = pattern.search(text) is not None
        else:
            matches = search_text in text
        
        if matches:
            region = {
                'text': text,
                'left': ocr_data['left'][i],
                'top': ocr_data['top'][i],
                'width': ocr_data['width'][i],
                'height': ocr_data['height'][i],
                'conf': conf
            }
            regions.append(region)
            logger.debug(f"Found match: '{text}' at ({region['left']}, {region['top']}) "
                        f"with confidence {conf:.1f}%")
    
    return regions


def redact_regions(
    image: Image.Image,
    regions: list[dict[str, Any]],
    fill_color: str,
    padding: int
) -> Image.Image:
    """
    Paint over text regions with solid color.
    
    Args:
        image: PIL Image object
        regions: List of bounding box dicts
        fill_color: Hex color to fill with
        padding: Extra pixels around detected text
    
    Returns:
        Modified PIL Image
    """
    draw = ImageDraw.Draw(image)
    
    for region in regions:
        x1 = max(0, region['left'] - padding)
        y1 = max(0, region['top'] - padding)
        x2 = min(image.width, region['left'] + region['width'] + padding)
        y2 = min(image.height, region['top'] + region['height'] + padding)
        
        draw.rectangle([x1, y1, x2, y2], fill=fill_color)
        logger.debug(f"Redacted region: ({x1}, {y1}) to ({x2}, {y2})")
    
    return image


def render_placeholder(
    image: Image.Image,
    regions: list[dict[str, Any]],
    placeholder_text: str,
    font_size: int | None,
    font_color: str,
    padding: int
) -> Image.Image:
    """
    Render placeholder text over redacted regions.
    
    Args:
        image: PIL Image to draw on
        regions: List of bounding box dicts
        placeholder_text: Text to render
        font_size: Font size (None = auto-fit)
        font_color: Hex color for text
        padding: Padding used for redaction (for alignment)
    
    Returns:
        Modified PIL Image
    """
    draw = ImageDraw.Draw(image)
    
    for region in regions:
        region_width = region['width'] + 2 * padding
        region_height = region['height'] + 2 * padding
        
        # Auto-fit font size if not specified
        if font_size is None:
            # Start with height-based estimate, then refine
            estimated_size = max(10, int(region_height * 0.6))
            font = _get_font(estimated_size)
            
            # Shrink if text doesn't fit width
            bbox = draw.textbbox((0, 0), placeholder_text, font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width > region_width * 0.9:
                scale = (region_width * 0.9) / text_width
                estimated_size = max(8, int(estimated_size * scale))
                font = _get_font(estimated_size)
        else:
            font = _get_font(font_size)
        
        # Calculate centered position
        bbox = draw.textbbox((0, 0), placeholder_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = region['left'] - padding + (region_width - text_width) // 2
        y = region['top'] - padding + (region_height - text_height) // 2
        
        draw.text((x, y), placeholder_text, fill=font_color, font=font)
        logger.debug(f"Rendered '{placeholder_text}' at ({x}, {y})")
    
    return image


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a font object, falling back to default if TrueType unavailable."""
    try:
        # Try to load a standard system font
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("Arial.ttf", size)
        except (OSError, IOError):
            # Fall back to default bitmap font
            logger.warning("TrueType fonts not available, using default bitmap font")
            return ImageFont.load_default()


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = parse_args(argv)
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    
    # Check dependencies
    try:
        check_tesseract()
    except (ImportError, TesseractNotInstalledError) as e:
        logger.error(str(e))
        return 1
    
    # Validate input file
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1
    
    if not args.input.is_file():
        logger.error(f"Input path is not a file: {args.input}")
        return 1
    
    # Determine output path
    output_path = args.output if args.output else args.input
    
    logger.info(f"Processing: {args.input}")
    logger.info(f"Searching for: {args.find} {'(regex)' if args.regex else '(exact)'}")
    
    # Load and prepare image (convert RGBA to RGB if needed)
    try:
        image = Image.open(args.input)
        if image.mode == 'RGBA':
            logger.info("Converting RGBA image to RGB")
            # Create white background and paste RGBA image
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
            image = rgb_image
        elif image.mode not in ('RGB', 'L'):
            # Convert other modes to RGB
            logger.info(f"Converting {image.mode} image to RGB")
            image = image.convert('RGB')
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        return 1
    
    # Find text regions
    try:
        regions = find_text_regions(
            image,
            args.find,
            args.regex,
            args.confidence
        )
    except ValueError as e:
        # Regex validation error
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return 1
    
    if not regions:
        logger.info("No matching text found in image")
        return 0
    
    # Limit to first match if --all not specified
    if not args.all:
        logger.info(f"Redacting first match only (use --all for all {len(regions)} matches)")
        regions = regions[:1]
    else:
        logger.info(f"Redacting {len(regions)} match(es)")
    
    # Redact regions
    try:
        image = redact_regions(
            image,
            regions,
            args.fill_color,
            args.padding
        )
    except Exception as e:
        logger.error(f"Redaction failed: {e}")
        return 1
    
    # Render placeholder text if specified
    if args.replace:
        try:
            image = render_placeholder(
                image,
                regions,
                args.replace,
                args.font_size,
                args.font_color,
                args.padding
            )
        except Exception as e:
            logger.error(f"Placeholder rendering failed: {e}")
            return 1
    
    # Save result with quality preservation for JPEG
    try:
        # Detect output format and preserve JPEG quality
        output_format = output_path.suffix.lower()
        if output_format in ['.jpg', '.jpeg']:
            image.save(output_path, quality=95, optimize=True)
            logger.info(f"Saved redacted image to: {output_path} (JPEG quality=95)")
        else:
            image.save(output_path)
            logger.info(f"Saved redacted image to: {output_path}")
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
