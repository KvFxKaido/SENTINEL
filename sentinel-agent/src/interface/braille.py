"""
Image to Braille art converter.

Converts images to high-resolution Braille Unicode art for terminal display.
Each Braille character represents a 2x4 pixel block (8 dots).
"""

import sys
from pathlib import Path
from typing import Optional

# Braille dot positions (2 columns x 4 rows):
#   1 4
#   2 5
#   3 6
#   7 8
# Character code = 0x2800 + sum of dot values
BRAILLE_OFFSET = 0x2800
DOT_VALUES = [
    [0x01, 0x08],  # Row 0: dots 1, 4
    [0x02, 0x10],  # Row 1: dots 2, 5
    [0x04, 0x20],  # Row 2: dots 3, 6
    [0x40, 0x80],  # Row 3: dots 7, 8
]


def pixels_to_braille(block: list[list[bool]]) -> str:
    """
    Convert a 4x2 block of pixels to a Braille character.

    Args:
        block: 4 rows of 2 boolean values (True = filled)

    Returns:
        Single Braille Unicode character
    """
    code = BRAILLE_OFFSET
    for row in range(4):
        for col in range(2):
            if row < len(block) and col < len(block[row]) and block[row][col]:
                code += DOT_VALUES[row][col]
    return chr(code)


def image_to_braille(
    image_source,
    width: int = 40,
    threshold: int = 128,
    invert: bool = False,
    dither: bool = True,
) -> str:
    """
    Convert an image to Braille art.

    Args:
        image_source: Path to image file, or PIL Image object
        width: Output width in characters (height auto-calculated)
        threshold: Brightness threshold for non-dithered mode (0-255)
        invert: Invert black/white
        dither: Use Floyd-Steinberg dithering for better gradients

    Returns:
        Multi-line string of Braille characters
    """
    try:
        from PIL import Image
    except ImportError:
        return "Error: Pillow not installed. Run: pip install Pillow"

    # Load and convert to grayscale
    if isinstance(image_source, Image.Image):
        img = image_source.convert('L')
    else:
        img = Image.open(image_source).convert('L')

    # Calculate dimensions
    # Each braille char is 2 pixels wide, 4 pixels tall
    pixel_width = width * 2
    aspect_ratio = img.height / img.width
    # Terminal characters are ~2x taller than wide, and braille is 4 rows
    pixel_height = int(pixel_width * aspect_ratio * 0.5)
    # Round to multiple of 4 for clean braille blocks
    pixel_height = (pixel_height // 4) * 4

    img = img.resize((pixel_width, pixel_height), Image.Resampling.LANCZOS)

    # Convert to pixel array
    pixels = list(img.getdata())
    pixel_matrix = []
    for y in range(pixel_height):
        row = []
        for x in range(pixel_width):
            value = pixels[y * pixel_width + x]
            row.append(value)
        pixel_matrix.append(row)

    # Apply dithering if enabled
    if dither:
        pixel_matrix = floyd_steinberg_dither(pixel_matrix, pixel_width, pixel_height)

    # Convert to binary (True = filled dot)
    binary_matrix = []
    for row in pixel_matrix:
        binary_row = []
        for value in row:
            if dither:
                # Already dithered to 0 or 255
                filled = value < 128
            else:
                filled = value < threshold
            if invert:
                filled = not filled
            binary_row.append(filled)
        binary_matrix.append(binary_row)

    # Convert to braille
    lines = []
    for y in range(0, pixel_height, 4):
        line = ""
        for x in range(0, pixel_width, 2):
            # Extract 4x2 block
            block = []
            for dy in range(4):
                row = []
                for dx in range(2):
                    if y + dy < pixel_height and x + dx < pixel_width:
                        row.append(binary_matrix[y + dy][x + dx])
                    else:
                        row.append(False)
                block.append(row)
            line += pixels_to_braille(block)
        lines.append(line)

    return "\n".join(lines)


def floyd_steinberg_dither(
    pixels: list[list[int]],
    width: int,
    height: int
) -> list[list[int]]:
    """
    Apply Floyd-Steinberg dithering for better gradient representation.
    """
    # Work with floats for error diffusion
    matrix = [[float(p) for p in row] for row in pixels]

    for y in range(height):
        for x in range(width):
            old_value = matrix[y][x]
            new_value = 255.0 if old_value > 127 else 0.0
            matrix[y][x] = new_value
            error = old_value - new_value

            # Distribute error to neighbors
            if x + 1 < width:
                matrix[y][x + 1] += error * 7 / 16
            if y + 1 < height:
                if x > 0:
                    matrix[y + 1][x - 1] += error * 3 / 16
                matrix[y + 1][x] += error * 5 / 16
                if x + 1 < width:
                    matrix[y + 1][x + 1] += error * 1 / 16

    return [[int(p) for p in row] for row in matrix]


def text_to_braille_banner(
    text: str,
    font_size: int = 20,
) -> str:
    """
    Convert text to Braille art using a rendered font.

    Args:
        text: Text to render
        font_size: Size of font to render

    Returns:
        Braille art of the text
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return "Error: Pillow not installed. Run: pip install Pillow"

    # Create image with text
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    # Get text size
    dummy_img = Image.new('L', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0] + 4
    text_height = bbox[3] - bbox[1] + 4

    # Round to braille block size
    text_width = ((text_width + 1) // 2) * 2
    text_height = ((text_height + 3) // 4) * 4

    # Create and draw
    img = Image.new('L', (text_width, text_height), 255)
    draw = ImageDraw.Draw(img)
    draw.text((2, 0), text, font=font, fill=0)

    # Convert directly from PIL Image
    return image_to_braille(img, width=text_width // 2, invert=True, dither=False)


def generate_portrait(
    archetype: str = "default",
    expression: str = "neutral",
    width: int = 20,
) -> str:
    """
    Generate a portrait programmatically based on archetype.

    Args:
        archetype: Character type (scout, soldier, elder, merchant, hacker, mystic)
        expression: Facial expression (neutral, friendly, hostile, wary)
        width: Output width in braille characters

    Returns:
        Braille art portrait
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return "Error: Pillow not installed. Run: pip install Pillow"

    size = 80
    img = Image.new('L', (size, size), 255)
    draw = ImageDraw.Draw(img)

    # Base head shape varies by archetype
    if archetype == "soldier":
        # Square jaw, helmet
        draw.rectangle([15, 0, 65, 15], fill=0)  # Helmet
        draw.rectangle([12, 15, 68, 70], outline=0, width=2)  # Square head
    elif archetype == "elder":
        # Rounder, with beard
        draw.ellipse([10, 5, 70, 65], outline=0, width=2)
        # Beard
        draw.arc([15, 45, 65, 80], 0, 180, fill=0, width=2)
        draw.arc([20, 50, 60, 78], 0, 180, fill=0, width=1)
    elif archetype == "hacker":
        # Hood/hoodie outline
        draw.arc([5, -10, 75, 50], 0, 180, fill=0, width=3)
        draw.ellipse([15, 10, 65, 65], outline=0, width=2)
    elif archetype == "mystic":
        # Third eye, ethereal
        draw.ellipse([10, 10, 70, 70], outline=0, width=2)
        draw.ellipse([35, 5, 45, 15], fill=0)  # Third eye
    elif archetype == "merchant":
        # Rounder, cheerful
        draw.ellipse([8, 5, 72, 75], outline=0, width=2)
    else:
        # Default: standard oval
        draw.ellipse([10, 5, 70, 75], outline=0, width=2)

    # Eyes based on expression
    eye_y = 30
    if expression == "hostile":
        # Angry slanted eyes
        draw.polygon([(22, 28), (35, 32), (35, 38), (22, 34)], fill=0)
        draw.polygon([(58, 28), (45, 32), (45, 38), (58, 34)], fill=0)
    elif expression == "wary":
        # Narrowed eyes
        draw.ellipse([22, 30, 35, 36], fill=0)
        draw.ellipse([45, 30, 58, 36], fill=0)
    elif expression == "friendly":
        # Happy curved eyes
        draw.arc([22, 25, 35, 38], 0, 180, fill=0, width=2)
        draw.arc([45, 25, 58, 38], 0, 180, fill=0, width=2)
    else:
        # Neutral round eyes
        draw.ellipse([22, 25, 35, 38], fill=0)
        draw.ellipse([45, 25, 58, 38], fill=0)

    # Archetype-specific eye details
    if archetype == "hacker":
        # Glowing/digital look - add highlight
        draw.ellipse([26, 28, 31, 33], fill=255)
        draw.ellipse([49, 28, 54, 33], fill=255)

    # Nose
    draw.line([(40, 38), (38, 50)], fill=0, width=1)
    draw.line([(38, 50), (42, 52)], fill=0, width=1)

    # Mouth based on expression
    if expression == "hostile":
        draw.line([(28, 58), (52, 58)], fill=0, width=2)  # Stern line
    elif expression == "friendly":
        draw.arc([25, 52, 55, 68], 0, 180, fill=0, width=2)  # Smile
    elif expression == "wary":
        draw.arc([30, 55, 50, 65], 180, 360, fill=0, width=1)  # Slight frown
    else:
        draw.arc([28, 54, 52, 64], 0, 180, fill=0, width=1)  # Neutral

    # Hair/head details by archetype
    if archetype == "scout":
        # Short practical hair
        draw.arc([12, -5, 68, 35], 180, 360, fill=0, width=4)
    elif archetype == "elder":
        # Receding/thin hair
        draw.arc([20, -5, 60, 25], 180, 360, fill=0, width=1)
    elif archetype == "merchant":
        # Slicked back
        draw.arc([10, -8, 70, 30], 180, 360, fill=0, width=2)
        draw.line([(15, 10), (35, 5)], fill=0, width=1)
        draw.line([(65, 10), (45, 5)], fill=0, width=1)

    return image_to_braille(img, width=width, invert=False, dither=False)


def generate_test_portrait() -> str:
    """Generate a simple test portrait."""
    return generate_portrait("default", "neutral", 20)


def demo():
    """Demo the Braille converter."""
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    print("\n" + "=" * 50)
    print("  SENTINEL Braille Art Converter")
    print("=" * 50)

    # Show different archetypes
    archetypes = [
        ("default", "neutral", "Default"),
        ("soldier", "hostile", "Soldier (hostile)"),
        ("elder", "neutral", "Elder"),
        ("hacker", "wary", "Hacker (wary)"),
        ("merchant", "friendly", "Merchant (friendly)"),
        ("mystic", "neutral", "Mystic"),
        ("scout", "friendly", "Scout (friendly)"),
    ]

    for archetype, expression, label in archetypes:
        print(f"\n--- {label} ---\n")
        portrait = generate_portrait(archetype, expression, width=18)
        print(portrait)

    # Usage instructions
    print("\n--- Usage ---\n")
    print("From Python:")
    print('  from src.interface.braille import image_to_braille, generate_portrait')
    print('  art = image_to_braille("portrait.png", width=30)')
    print('  portrait = generate_portrait("soldier", "hostile")')
    print()
    print("Command line:")
    print('  python -m src.interface.braille <image_path> [width]')
    print()


def main():
    """CLI entry point."""
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    if len(sys.argv) < 2:
        demo()
        return

    image_path = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 40

    if not Path(image_path).exists():
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    print(image_to_braille(image_path, width=width))


if __name__ == "__main__":
    main()
