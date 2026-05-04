#!/usr/bin/env python3
"""
Visual redaction demo script.

Uses real test images with known text regions (from regions.json) to demonstrate
redaction without requiring Tesseract OCR installation.

Generates visually clear redacted outputs to test-outputs/ directory.
"""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a font object, falling back to default if TrueType unavailable."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("Arial.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default()


def redact_region(
    image: Image.Image,
    region: dict,
    fill_color: str = "#FF6B6B",
    placeholder: str | None = None,
    padding: int = 2
) -> None:
    """
    Redact a single region in the image.
    
    Args:
        image: PIL Image to modify (in-place)
        region: Dict with 'left', 'top', 'width', 'height'
        fill_color: Hex color for redaction fill
        placeholder: Optional text to render over redaction
        padding: Extra pixels around region
    """
    draw = ImageDraw.Draw(image)
    
    # Calculate rectangle bounds with padding
    x1 = max(0, region['left'] - padding)
    y1 = max(0, region['top'] - padding)
    x2 = min(image.width, region['left'] + region['width'] + padding)
    y2 = min(image.height, region['top'] + region['height'] + padding)
    
    # Fill with solid color
    draw.rectangle([x1, y1, x2, y2], fill=fill_color)
    
    # Render placeholder text if provided
    if placeholder:
        region_width = x2 - x1
        region_height = y2 - y1
        
        # Auto-fit font size
        estimated_size = max(10, int(region_height * 0.6))
        font = get_font(estimated_size)
        
        # Shrink if text doesn't fit width
        bbox = draw.textbbox((0, 0), placeholder, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width > region_width * 0.9:
            scale = (region_width * 0.9) / text_width
            estimated_size = max(8, int(estimated_size * scale))
            font = get_font(estimated_size)
        
        # Center text in redacted region
        bbox = draw.textbbox((0, 0), placeholder, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = x1 + (region_width - text_width) // 2
        y = y1 + (region_height - text_height) // 2
        
        draw.text((x, y), placeholder, fill='white', font=font)


def find_text_region(regions: list[dict], search_text: str) -> dict | None:
    """Find region containing search text."""
    for region in regions:
        if search_text in region.get('text', ''):
            return region
    return None


def demo_api_keys(
    input_path: Path,
    output_dir: Path,
    regions: list[dict]
) -> None:
    """Demo: Redact API key from api-keys.png."""
    # Copy original as "before"
    import shutil
    shutil.copy(input_path, output_dir / "before.png")
    
    # Create redacted "after"
    img = Image.open(input_path)
    
    # Find and redact the API key
    region = find_text_region(regions, 'sk-abc123def456')
    if region:
        redact_region(img, region, fill_color="#FF6B6B", placeholder="[REDACTED_KEY]")
    
    output_path = output_dir / "after-redacted.png"
    img.save(output_path)
    print(f"✓ Created: {output_dir.name}/ (before + after)")


def demo_personal_info(
    input_path: Path,
    output_dir: Path,
    regions: list[dict]
) -> None:
    """Demo: Redact SSN from personal-info.png."""
    # Copy original as "before"
    import shutil
    shutil.copy(input_path, output_dir / "before.png")
    
    # Create redacted "after"
    img = Image.open(input_path)
    
    # Find and redact the SSN
    region = find_text_region(regions, '123-45-6789')
    if region:
        redact_region(img, region, fill_color="#FFD93D", placeholder="[SSN REMOVED]")
    
    output_path = output_dir / "after-redacted.png"
    img.save(output_path)
    print(f"✓ Created: {output_dir.name}/ (before + after)")


def demo_mixed_content(
    input_path: Path,
    output_dir: Path,
    regions: list[dict]
) -> None:
    """Demo: Redact auth token from mixed-content.png."""
    # Copy original as "before"
    import shutil
    shutil.copy(input_path, output_dir / "before.png")
    
    # Create redacted "after"
    img = Image.open(input_path)
    
    # Find and redact the token
    region = find_text_region(regions, 'ghp_xxxxxxxxxxxx')
    if region:
        redact_region(img, region, fill_color="#6BCF7F", placeholder="[TOKEN]")
    
    output_path = output_dir / "after-redacted.png"
    img.save(output_path)
    print(f"✓ Created: {output_dir.name}/ (before + after)")


def demo_watermark(
    input_path: Path,
    output_dir: Path,
    regions: list[dict]
) -> None:
    """Demo: Remove CONFIDENTIAL watermark from watermark.png."""
    # Copy original as "before"
    import shutil
    shutil.copy(input_path, output_dir / "before.png")
    
    # Create redacted "after"
    img = Image.open(input_path)
    
    # Find and redact "CONFIDENTIAL" (fill only, no replacement)
    region = find_text_region(regions, 'CONFIDENTIAL')
    if region:
        # Use lightgray to match background
        redact_region(img, region, fill_color="#D3D3D3", placeholder=None, padding=4)
    
    output_path = output_dir / "after-redacted.png"
    img.save(output_path)
    print(f"✓ Created: {output_dir.name}/ (before + after)")


def main() -> None:
    """Run all visual redaction demos."""
    script_dir = Path(__file__).parent
    test_images_dir = script_dir / "test-images"
    demos_dir = script_dir / "test-outputs" / "demos"
    regions_file = test_images_dir / "regions.json"
    
    # Verify test images exist
    if not test_images_dir.exists():
        print("❌ test-images/ directory not found")
        print("   Run: python create_test_images.py")
        return
    
    # Verify regions.json exists
    if not regions_file.exists():
        print("❌ test-images/regions.json not found")
        print("   Run: python create_test_images.py")
        return
    
    # Load regions data
    with open(regions_file, 'r') as f:
        all_regions = json.load(f)
    
    # Create demo output directories
    demos_dir.mkdir(parents=True, exist_ok=True)
    
    api_keys_dir = demos_dir / "api-keys"
    personal_info_dir = demos_dir / "personal-info"
    mixed_content_dir = demos_dir / "mixed-content"
    watermark_dir = demos_dir / "watermark"
    
    for dir_path in [api_keys_dir, personal_info_dir, mixed_content_dir, watermark_dir]:
        dir_path.mkdir(exist_ok=True)
    
    print(f"Running visual redaction demos...\n")
    
    # Run demos
    demo_api_keys(
        test_images_dir / "api-keys.png",
        api_keys_dir,
        all_regions.get("api-keys.png", [])
    )
    
    demo_personal_info(
        test_images_dir / "personal-info.png",
        personal_info_dir,
        all_regions.get("personal-info.png", [])
    )
    
    demo_mixed_content(
        test_images_dir / "mixed-content.png",
        mixed_content_dir,
        all_regions.get("mixed-content.png", [])
    )
    
    demo_watermark(
        test_images_dir / "watermark.png",
        watermark_dir,
        all_regions.get("watermark.png", [])
    )
    
    print(f"\n✅ All demos complete! Check {demos_dir}/")
    print("\nEach demo folder contains:")
    print("  • before.png — original test image")
    print("  • after-redacted.png — redacted version")
    print("\nThese outputs show visible redaction with:")
    print("  • Colored fills (not just white)")
    print("  • Placeholder text")
    print("  • Clear before/after comparison")


if __name__ == "__main__":
    main()
