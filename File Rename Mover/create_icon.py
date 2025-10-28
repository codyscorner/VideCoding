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

    # Scale factors
    if size == 16:
        outer_radius = 6
        inner_radius = 2
        circle_radius = 1.5
        leaf_radius = 3
    elif size == 32:
        outer_radius = 12
        inner_radius = 4
        circle_radius = 3
        leaf_radius = 6
    elif size == 48:
        outer_radius = 18
        inner_radius = 6
        circle_radius = 4.5
        leaf_radius = 9
    else:  # 256
        outer_radius = 96
        inner_radius = 32
        circle_radius = 24
        leaf_radius = 48

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
            fill=dark_red
        )

        # Draw inner circle (bright red)
        inner_r = leaf_radius * 0.6
        draw.ellipse(
            [x - inner_r, y - inner_r, x + inner_r, y + inner_r],
            fill=red
        )

        # Draw cutout towards center (black)
        cutout_x = center_x + (outer_radius * 0.4) * math.cos(rad)
        cutout_y = center_y - (outer_radius * 0.4) * math.sin(rad)
        cutout_r = leaf_radius * 0.5
        draw.ellipse(
            [cutout_x - cutout_r, cutout_y - cutout_r,
             cutout_x + cutout_r, cutout_y + cutout_r],
            fill=black
        )

    # Draw center circle (bright red)
    draw.ellipse(
        [center_x - inner_radius, center_y - inner_radius,
         center_x + inner_radius, center_y + inner_radius],
        fill=red
    )

    # Draw very small center dot (dark red for detail)
    if size >= 32:
        tiny = inner_radius * 0.3
        draw.ellipse(
            [center_x - tiny, center_y - tiny,
             center_x + tiny, center_y + tiny],
            fill=dark_red
        )

    return img

# Create different sizes
sizes = [16, 32, 48, 256]
images = []

for size in sizes:
    img = create_biohazard_icon(size)
    img.save(f'p:/AI/VideCoding/File Rename Mover/icon_{size}.png')
    images.append(img)
    print(f"Created {size}x{size} icon")

# Save as ICO file with multiple sizes
images[0].save(
    'p:/AI/VideCoding/File Rename Mover/app_icon.ico',
    format='ICO',
    sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
    append_images=images[1:]
)

print("Created app_icon.ico with all sizes")
