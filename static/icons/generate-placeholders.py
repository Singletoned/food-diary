#!/usr/bin/env python3
"""
Generate placeholder PWA icons for Chompix.
Requires: pip install pillow
"""

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow is required. Install it with: pip install pillow")
    exit(1)

# Icon sizes needed
SIZES = [72, 96, 128, 144, 152, 180, 192, 384, 512]

# Chompix theme color (Bulma turquoise)
BG_COLOR = "#00d1b2"
TEXT_COLOR = "#ffffff"

def create_icon(size):
    """Create a simple icon with the Chompix logo."""
    # Create image with background color
    img = Image.new('RGB', (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Calculate font size (roughly 40% of icon size)
    font_size = int(size * 0.4)

    # Try to use a system font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

    # Draw text centered
    text = "C"  # C for Chompix

    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Calculate position to center text
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]

    # Draw the text
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    return img

def main():
    """Generate all icon sizes."""
    print("Generating placeholder icons for Chompix PWA...")

    for size in SIZES:
        filename = f"icon-{size}x{size}.png"
        print(f"Creating {filename}...")

        img = create_icon(size)
        img.save(filename)

    print("\nDone! Icons generated:")
    for size in SIZES:
        print(f"  - icon-{size}x{size}.png")

    print("\nNote: These are placeholder icons. Consider creating custom icons")
    print("with your actual logo/design for a professional appearance.")

if __name__ == "__main__":
    main()
