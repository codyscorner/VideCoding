from PIL import Image, ImageDraw
import math

def create_biohazard_icon(size):
    """Create a biohazard icon with red symbol on black background"""
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
    leaf_radius = int(48 * scale)

    if size <= 16:
        outer_radius = max(6, outer_radius)
        inner_radius = max(2, inner_radius)
        leaf_radius = max(3, leaf_radius)

    # Draw three circles (biohazard symbol petals)
    angles = [90, 210, 330]

    for angle in angles:
        rad = math.radians(angle)
        x = center_x + outer_radius * math.cos(rad)
        y = center_y - outer_radius * math.sin(rad)

        # Draw outer circle
        draw.ellipse(
            [x - leaf_radius, y - leaf_radius, x + leaf_radius, y + leaf_radius],
            fill=dark_red, outline=None
        )

        # Draw inner circle
        inner_r = leaf_radius * 0.6
        draw.ellipse(
            [x - inner_r, y - inner_r, x + inner_r, y + inner_r],
            fill=red, outline=None
        )

        # Draw cutout towards center
        cutout_x = center_x + (outer_radius * 0.4) * math.cos(rad)
        cutout_y = center_y - (outer_radius * 0.4) * math.sin(rad)
        cutout_r = leaf_radius * 0.5
        draw.ellipse(
            [cutout_x - cutout_r, cutout_y - cutout_r,
             cutout_x + cutout_r, cutout_y + cutout_r],
            fill=black, outline=None
        )

    # Draw center circle
    draw.ellipse(
        [center_x - inner_radius, center_y - inner_radius,
         center_x + inner_radius, center_y + inner_radius],
        fill=red, outline=None
    )

    if size >= 32:
        tiny = inner_radius * 0.3
        draw.ellipse(
            [center_x - tiny, center_y - tiny,
             center_x + tiny, center_y + tiny],
            fill=dark_red, outline=None
        )

    return img

# Create icons and save as proper ICO format
print("Creating icon images...")

# Create the main sizes for Windows icons
img_256 = create_biohazard_icon(256)
img_48 = create_biohazard_icon(48)
img_32 = create_biohazard_icon(32)
img_16 = create_biohazard_icon(16)

# Save as ICO - use the standard method
print("Saving as ICO file...")
img_256.save(
    'p:/AI/VideCoding/File Rename Mover/app_icon.ico',
    format='ICO',
    sizes=[(16, 16), (32, 32), (48, 48), (256, 256)]
)

print("Icon created successfully!")
import os
size = os.path.getsize('p:/AI/VideCoding/File Rename Mover/app_icon.ico')
print(f"Icon file size: {size} bytes")
