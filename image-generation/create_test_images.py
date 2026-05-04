#!/usr/bin/env python3
"""
Generate test images for the text redaction tool.
Creates sample images with various types of text that can be redacted.
"""

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
            # Fall back to default bitmap font
            return ImageFont.load_default()


def create_api_keys_image(output_path: Path) -> None:
    """Create test image with API keys and credentials."""
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    font = get_font(16)
    
    lines = [
        "API_KEY=sk-abc123def456",
        "SECRET=mysecretvalue",
        "DATABASE_URL=postgres://user:pass@host/db"
    ]
    
    y_offset = 30
    for line in lines:
        draw.text((20, y_offset), line, fill='black', font=font)
        y_offset += 40
    
    img.save(output_path)
    print(f"Created: {output_path}")


def create_personal_info_image(output_path: Path) -> None:
    """Create test image with personal information."""
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    font = get_font(16)
    
    lines = [
        "Name: John Smith",
        "Email: john@example.com",
        "SSN: 123-45-6789"
    ]
    
    y_offset = 30
    for line in lines:
        draw.text((20, y_offset), line, fill='black', font=font)
        y_offset += 40
    
    img.save(output_path)
    print(f"Created: {output_path}")


def create_mixed_content_image(output_path: Path) -> None:
    """Create test image with mixed safe and sensitive content."""
    img = Image.new('RGB', (500, 250), color='white')
    draw = ImageDraw.Draw(img)
    font = get_font(16)
    
    lines = [
        "Project Status: Active",
        "Budget: $50,000",
        "Contact: admin@internal.corp",
        "Auth Token: ghp_xxxxxxxxxxxx"
    ]
    
    y_offset = 30
    for line in lines:
        draw.text((20, y_offset), line, fill='black', font=font)
        y_offset += 45
    
    img.save(output_path)
    print(f"Created: {output_path}")


def create_watermark_image(output_path: Path) -> None:
    """Create test image with watermark-style text."""
    img = Image.new('RGB', (400, 200), color='lightgray')
    draw = ImageDraw.Draw(img)
    
    # Large centered "CONFIDENTIAL"
    font_large = get_font(48)
    text_large = "CONFIDENTIAL"
    
    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text_large, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (400 - text_width) // 2
    y = (200 - text_height) // 2 - 20
    
    # Draw with semi-transparency effect (darker gray on light gray)
    draw.text((x, y), text_large, fill='darkgray', font=font_large)
    
    # Smaller "Draft v2.1" at bottom
    font_small = get_font(14)
    text_small = "Draft v2.1"
    bbox_small = draw.textbbox((0, 0), text_small, font=font_small)
    text_width_small = bbox_small[2] - bbox_small[0]
    
    x_small = (400 - text_width_small) // 2
    y_small = 170
    
    draw.text((x_small, y_small), text_small, fill='gray', font=font_small)
    
    img.save(output_path)
    print(f"Created: {output_path}")


def main() -> None:
    """Generate all test images."""
    # Create output directory
    output_dir = Path(__file__).parent / "test-images"
    output_dir.mkdir(exist_ok=True)
    print(f"Creating test images in: {output_dir}")
    
    # Generate test images
    create_api_keys_image(output_dir / "api-keys.png")
    create_personal_info_image(output_dir / "personal-info.png")
    create_mixed_content_image(output_dir / "mixed-content.png")
    create_watermark_image(output_dir / "watermark.png")
    
    print("\nTest images created successfully!")
    print("Try them with redact_text.py:")
    print("  python redact_text.py --input test-images/api-keys.png --find 'sk-abc123def456' --replace '[REDACTED]'")


if __name__ == "__main__":
    main()
