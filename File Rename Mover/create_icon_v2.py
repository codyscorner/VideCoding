from PIL import Image, ImageDraw
import math

def create_biohazard_icon(size):
    """Create a biohazard icon with red symbol on black background"""
    # Create a new image with black background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    center_x = size // 2
    center_y = size // 2

    # Color scheme - bright red
    red = (255, 68, 68, 255)
    dark_red = (204, 51, 51, 255)
    black = (0, 0, 0, 255)

    # Scale factors based on size
    scale = size / 256.0

    outer_radius = int(96 * scale)
    inner_radius = int(32 * scale)
    circle_radius = int(24 * scale)
    leaf_radius = int(48 * scale)

    # Make sure minimum sizes for small icons
    if size <= 16:
        outer_radius = max(6, outer_radius)
        inner_radius = max(2, inner_radius)
        leaf_radius = max(3, leaf_radius)

    # Draw three circles (biohazard symbol petals)
    angles = [90, 210, 330]  # Top, bottom-left, bottom-right

    for angle in angles:
        rad = math.radians(angle)
        # Position of outer circle
        x = center_x + outer_radius * math.cos(rad)
        y = center_y - outer_radius * math.sin(rad)

        # Draw outer circle (dark red)
        draw.ellipse(
            [x - leaf_radius, y - leaf_radius, x + leaf_radius, y + leaf_radius],
            fill=dark_red, outline=None
        )

        # Draw inner circle (bright red)
        inner_r = leaf_radius * 0.6
        draw.ellipse(
            [x - inner_r, y - inner_r, x + inner_r, y + inner_r],
            fill=red, outline=None
        )

        # Draw cutout towards center (black)
        cutout_x = center_x + (outer_radius * 0.4) * math.cos(rad)
        cutout_y = center_y - (outer_radius * 0.4) * math.sin(rad)
        cutout_r = leaf_radius * 0.5
        draw.ellipse(
            [cutout_x - cutout_r, cutout_y - cutout_r,
             cutout_x + cutout_r, cutout_y + cutout_r],
            fill=black, outline=None
        )

    # Draw center circle (bright red)
    draw.ellipse(
        [center_x - inner_radius, center_y - inner_radius,
         center_x + inner_radius, center_y + inner_radius],
        fill=red, outline=None
    )

    # Draw very small center dot (dark red for detail)
    if size >= 32:
        tiny = inner_radius * 0.3
        draw.ellipse(
            [center_x - tiny, center_y - tiny,
             center_x + tiny, center_y + tiny],
            fill=dark_red, outline=None
        )

    return img

# Create different sizes
print("Creating icon images...")
icon_16 = create_biohazard_icon(16)
icon_32 = create_biohazard_icon(32)
icon_48 = create_biohazard_icon(48)
icon_64 = create_biohazard_icon(64)
icon_128 = create_biohazard_icon(128)
icon_256 = create_biohazard_icon(256)

# Save individual PNGs for reference
icon_16.save('p:/AI/VideCoding/File Rename Mover/icon_16.png')
icon_32.save('p:/AI/VideCoding/File Rename Mover/icon_32.png')
icon_48.save('p:/AI/VideCoding/File Rename Mover/icon_48.png')
icon_256.save('p:/AI/VideCoding/File Rename Mover/icon_256.png')
print("Created PNG files")

# Create ICO with all sizes - use the correct approach
# Convert all images to the same mode
icon_16_rgb = icon_16.convert('RGBA')
icon_32_rgb = icon_32.convert('RGBA')
icon_48_rgb = icon_48.convert('RGBA')
icon_64_rgb = icon_64.convert('RGBA')
icon_128_rgb = icon_128.convert('RGBA')
icon_256_rgb = icon_256.convert('RGBA')

# Save as ICO file
icon_256_rgb.save(
    'p:/AI/VideCoding/File Rename Mover/app_icon.ico',
    format='ICO',
    sizes=[
        (16, 16),
        (32, 32),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256)
    ]
)

print("Created app_icon.ico with multiple sizes")

# Verify file size
import os
file_size = os.path.getsize('p:/AI/VideCoding/File Rename Mover/app_icon.ico')
print(f"ICO file size: {file_size} bytes")
